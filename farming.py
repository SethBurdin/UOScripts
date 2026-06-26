# farming.py
# Stand-in-place farming loop. Discovers the pet automatically (no prompts),
# then loops: heal/cure pet, scan for enemies, send pet to tag and pull mobs
# back to the player, guard when clear.

if False:
    from razorenhanced_stubs import *

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.enemies import GetEnemies

# ─── Config ───────────────────────────────────────────────────────────────────
PET_FOLLOW_RANGE          = 1
HEALTH_THRESHOLD          = 0.85
CRITICAL_HEALTH_THRESHOLD = 0.40
GUARD_HEALTH_THRESHOLD    = 0.90
CHECK_INTERVAL            = 1500
FOLLOW_CHECK_INTERVAL     = 4000
FOLLOW_MAX_CHECKS         = 3
PET_SCAN_RANGE            = 30
GUARD_BREAK_DISTANCE      = 1

ENEMY_SCAN_RANGE    = 12
KILL_ENGAGE_RANGE   = 1
GUARD_TRIGGER_RANGE = 2
HUNT_GUARD_TIMEOUT  = 12

WHISPER_ENABLED      = True
WHISPER_INTERVAL_SEC = 1800

PLAYER_HEALTH_THRESHOLD = 0.85
INVIS_BEFORE_HEAL       = True
INVIS_SETTLE_MS         = 3000

PET_CMD_FOLLOW = 2
PET_CMD_GUARD  = 3
PET_CMD_KILL   = 4

KILL_COOLDOWN_SEC = 8

_pet_serial    = None
_last_whisper  = 0.0
_kill_times    = {}
_skip_serials  = set()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[farming] " + msg, color)


def _pet_cmd(serial, entry, target_serial=None):
    if Misc.WaitForContext(serial, 2000):
        Misc.ContextReply(serial, entry)
        if target_serial is not None:
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(target_serial)
    Misc.Pause(400)


def _send_kill(target_serial):
    """Issue 'all kill' on a target. Returns False and adds the serial to
    _skip_serials if the server replies 'Target cannot be seen.'"""
    Journal.Clear()
    Player.ChatSay("all kill")
    Misc.Pause(300)
    if Target.WaitForTarget(2000, False):
        Target.TargetExecute(target_serial)
    Misc.Pause(600)
    if Journal.Search("Target cannot be seen."):
        log("Target cannot be seen — skipping 0x%X." % target_serial, colors['yellow'])
        _skip_serials.add(target_serial)
        return False
    _kill_times[target_serial] = time.time()
    return True


def discover_pet():
    global _pet_serial

    if Player.Mount is not None:
        log("Dismounting before scan.", colors['cyan'])
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(2000)

    log("Scanning for pet within %d tiles..." % PET_SCAN_RANGE, colors['cyan'])
    f = Mobiles.Filter()
    f.Enabled  = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial or mob.IsHuman:
            continue
        log("Trying %s (0x%X)..." % (mob.Name, mob.Serial), colors['yellow'])
        Mobiles.UseMobile(mob.Serial)
        Misc.Pause(1500)
        if Player.Mount is not None:
            _pet_serial = mob.Serial
            log("Pet locked: %s (0x%X) — dismounting." % (mob.Name, _pet_serial), colors['cyan'])
            Mobiles.UseMobile(Player.Serial)
            Misc.Pause(1500)
            return True

    log("No mountable pet found — click your pet manually.", colors['yellow'])
    serial = Target.PromptTarget("Click your pet:")
    if serial and serial != 0:
        _pet_serial = serial
        mob  = Mobiles.FindBySerial(serial)
        name = mob.Name if mob is not None else ('0x%X' % serial)
        log("Pet locked via prompt: %s (0x%X)" % (name, serial), colors['cyan'])
        return True
    return False


def find_pet():
    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    nearest, nearestDist = None, 9999
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        if _pet_serial is not None:
            if mob.Serial == _pet_serial:
                return mob
        else:
            d = Player.DistanceTo(mob)
            if d < nearestDist:
                nearestDist = d
                nearest = mob
    return nearest


def heal_pet(pet):
    log("HP low — healing %s" % pet.Name, colors['cyan'])
    Spells.CastMagery('Greater Heal')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def heal_pet_critical(pet):
    log("HP critical (%.0f%%) — rapid healing %s" % (
        float(pet.Hits) / pet.HitsMax * 100, pet.Name), colors['red'])
    for _ in range(3):
        Spells.CastMagery('Greater Heal')
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(pet.Serial)
        Misc.Pause(800)


def cure_pet(pet):
    log("Poisoned — curing %s" % pet.Name, colors['cyan'])
    Spells.CastMagery('Arch Cure')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def cast_animal_whispering(pet):
    global _last_whisper
    if not WHISPER_ENABLED:
        return
    if time.time() - _last_whisper < WHISPER_INTERVAL_SEC:
        return
    log("Casting Animal Whispering on %s." % pet.Name, colors['cyan'])
    Spells.Cast("Whispering")
    if Target.WaitForTarget(4000, False):
        Target.TargetExecute(pet.Serial)
    _last_whisper = time.time()


def guard_pet_if_low(pet):
    if pet.HitsMax == 0:
        return
    if float(pet.Hits) / pet.HitsMax < GUARD_HEALTH_THRESHOLD:
        log("%s HP low (%.0f%%) — guard x3" % (
            pet.Name, float(pet.Hits) / pet.HitsMax * 100), colors['yellow'])
        for _ in range(3):
            _pet_cmd(pet.Serial, PET_CMD_GUARD)
            Misc.Pause(400)


def check_pet_health(pet):
    if pet.HitsMax == 0:
        return
    hp_ratio = float(pet.Hits) / pet.HitsMax
    if pet.Poisoned and hp_ratio < HEALTH_THRESHOLD:
        cure_pet(pet)
    if hp_ratio < CRITICAL_HEALTH_THRESHOLD:
        heal_pet_critical(pet)
    elif hp_ratio < HEALTH_THRESHOLD:
        heal_pet(pet)


def check_player_health():
    if Player.HitsMax == 0:
        return
    hp_ratio = float(Player.Hits) / Player.HitsMax
    if hp_ratio >= PLAYER_HEALTH_THRESHOLD:
        return
    log("Player HP low (%.0f%%) — healing self." % (hp_ratio * 100), colors['red'])
    if INVIS_BEFORE_HEAL:
        Spells.CastMagery('Invisibility')
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(Player.Serial)
        Misc.Pause(INVIS_SETTLE_MS)
    while Player.Hits < Player.HitsMax:
        if Player.Poisoned:
            Spells.CastMagery('Arch Cure')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(Player.Serial)
            Misc.Pause(1200)
        Spells.CastMagery('Greater Heal')
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(Player.Serial)
        Misc.Pause(1200)
    log("Player healed to full.", colors['green'])


def recall_pet(pet):
    log("Pet too far (%d tiles) — recalling." % Player.DistanceTo(pet), colors['yellow'])
    for i in range(FOLLOW_MAX_CHECKS):
        Player.ChatSay("all follow me")
        Misc.Pause(FOLLOW_CHECK_INTERVAL)
        fresh = find_pet()
        if fresh is None:
            log("Pet disappeared during recall.", colors['red'])
            return False
        if Player.DistanceTo(fresh) <= PET_FOLLOW_RANGE:
            return True
        log("Waiting for pet... check %d/%d" % (i + 1, FOLLOW_MAX_CHECKS), colors['yellow'])
    log("Pet did not return after %d checks." % FOLLOW_MAX_CHECKS, colors['red'])
    return False


def hunt_cycle(pet, enemy_serial):
    """Tag the enemy, pull pet back, guard when the mob closes on the player."""
    log("Hunting — waiting for pet to engage...", colors['yellow'])
    prev_enemy_dist = None
    phase1_deadline = time.time() + 30
    while not Player.IsGhost and time.time() < phase1_deadline:
        check_pet_health(pet)
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
        enemy = Mobiles.FindBySerial(enemy_serial)
        if enemy is None:
            log("Enemy defeated.", colors['green'])
            return False
        curr_enemy_dist = Player.DistanceTo(enemy)
        if prev_enemy_dist is not None and curr_enemy_dist > prev_enemy_dist + 3:
            log("Enemy fleeing — re-tagging and recalling.", colors['yellow'])
            if not _send_kill(enemy_serial):
                return False
            Player.ChatSay("all follow me")
            break
        prev_enemy_dist = curr_enemy_dist
        pet_to_enemy = max(
            abs(pet.Position.X - enemy.Position.X),
            abs(pet.Position.Y - enemy.Position.Y),
        )
        if pet_to_enemy <= KILL_ENGAGE_RANGE:
            log("Pet engaged — recalling.", colors['yellow'])
            break
        Misc.Pause(CHECK_INTERVAL)

    log("Recalling pet after engagement.", colors['yellow'])
    for i in range(10):
        if i % 3 == 0:
            Player.ChatSay("all follow me")
        Misc.Pause(1000)
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
            if Player.DistanceTo(pet) <= PET_FOLLOW_RANGE:
                break

    log("Waiting for mob to close (guard trigger = %d tiles)..." % GUARD_TRIGGER_RANGE, colors['yellow'])
    deadline = time.time() + HUNT_GUARD_TIMEOUT
    while time.time() < deadline and not Player.IsGhost:
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
        enemy = Mobiles.FindBySerial(enemy_serial)
        if enemy is None or Player.DistanceTo(enemy) <= GUARD_TRIGGER_RANGE:
            if pet is not None:
                _pet_cmd(pet.Serial, PET_CMD_GUARD)
            log("Guard issued — mob in range.", colors['cyan'])
            return True
        Misc.Pause(500)

    log("Hunt timeout — resuming loop.", colors['yellow'])
    return False


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    if not discover_pet():
        return

    log("Farming started. Say 'stop' to quit.", colors['cyan'])

    is_guarding = False
    is_hunting  = False
    guard_pos   = None

    pet = find_pet()
    if pet is not None:
        Player.ChatSay("all guard me")
        is_guarding = True
        guard_pos   = (Player.Position.X, Player.Position.Y)

    Journal.Clear()

    while not Player.IsGhost:
        if Journal.SearchByName("stop", Player.Name):
            Journal.Clear()
            log("Stop command — exiting.", colors['yellow'])
            break

        pet = find_pet()

        close_combat = len(GetEnemies(Mobiles, 0, GUARD_TRIGGER_RANGE)) > 0
        if is_guarding and guard_pos is not None and not close_combat:
            pos = Player.Position
            if max(abs(pos.X - guard_pos[0]), abs(pos.Y - guard_pos[1])) > GUARD_BREAK_DISTANCE:
                is_guarding = False
                guard_pos   = None
                Player.ChatSay("all follow me")

        if pet is None:
            log("No pet found.", colors['yellow'])
            is_guarding = False
            guard_pos   = None
            Misc.Pause(CHECK_INTERVAL)
            continue

        guard_pet_if_low(pet)
        check_pet_health(pet)
        check_player_health()
        cast_animal_whispering(pet)

        if not is_guarding and Player.DistanceTo(pet) > PET_FOLLOW_RANGE:
            guard_pos = None
            arrived   = recall_pet(pet)
            if not arrived:
                fresh = find_pet()
                if fresh is None or Player.DistanceTo(fresh) > PET_FOLLOW_RANGE + 1:
                    Misc.Pause(CHECK_INTERVAL)
                    continue
                pet = fresh

        enemies = ([] if is_hunting
                   else [e for e in GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE)
                         if e.Serial not in _skip_serials])

        if enemies:
            nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
            if Player.DistanceTo(nearest) <= GUARD_TRIGGER_RANGE:
                if time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC:
                    log("Enemy on us: %s — engaging in place." % nearest.Name, colors['yellow'])
                    _send_kill(nearest.Serial)
                if not is_guarding:
                    is_guarding = True
                    guard_pos   = (Player.Position.X, Player.Position.Y)
            else:
                log("Enemy: %s — sending pet to tag." % nearest.Name, colors['red'])
                if not _send_kill(nearest.Serial):
                    Misc.Pause(CHECK_INTERVAL)
                    continue
                is_guarding = False
                guard_pos   = None
                is_hunting  = True
                did_guard   = hunt_cycle(pet, nearest.Serial)
                is_hunting  = False
                pet         = find_pet() or pet
                if did_guard:
                    is_guarding = True
                    guard_pos   = (Player.Position.X, Player.Position.Y)
                else:
                    is_guarding = False
                    guard_pos   = None
                Misc.Pause(CHECK_INTERVAL)
                continue

        if not is_guarding:
            pos = Player.Position
            _pet_cmd(pet.Serial, PET_CMD_GUARD)
            is_guarding = True
            guard_pos   = (pos.X, pos.Y)

        Misc.Pause(CHECK_INTERVAL)

    log("Farming stopped.", colors['cyan'])


main()
