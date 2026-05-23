# guardian.py
# Keeps your pet close and on guard. Heals or cures the pet when needed.
# Every CHECK_INTERVAL ms: checks pet health/poison, then checks distance.
# If pet is too far, calls it back and waits up to FOLLOW_MAX_CHECKS x FOLLOW_CHECK_INTERVAL ms.

if False:
    from razorenhanced_stubs import *

import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from glossary.colors import colors
from glossary.runebook_handler import find_runebook_by_label, travel_to_runebook, travel_to_named_rune
from glossary.enemies import GetEnemies

# ─── Config ───────────────────────────────────────────────────────────────────
PET_FOLLOW_RANGE     = 1      # tiles — beyond this the pet is recalled
HEALTH_THRESHOLD          = 0.85   # heal/cure when pet HP ratio drops below this
CRITICAL_HEALTH_THRESHOLD = 0.40   # cast heals back-to-back when below this
GUARD_HEALTH_THRESHOLD    = 0.90   # say "all guard me" when pet HP ratio drops below this
CHECK_INTERVAL        = 1500  # ms between main loop ticks
FOLLOW_CHECK_INTERVAL = 4000  # ms between "all follow me" repeats while waiting for pet
FOLLOW_MAX_CHECKS     = 3     # max polls waiting for pet to arrive (total wait = FOLLOW_CHECK_INTERVAL * FOLLOW_MAX_CHECKS)
PET_SCAN_RANGE        = 30     # tile radius to search for a friendly mobile
GUARD_BREAK_DISTANCE  = 1    # tiles player must move from guard origin before pet is immediately recalled

ENEMY_SCAN_RANGE    = 12   # tile radius to scan for hostile mobs each tick
KILL_ENGAGE_RANGE   = 1    # Chebyshev pet-to-enemy distance that triggers recall phase
GUARD_TRIGGER_RANGE = 2    # enemy-to-player distance that triggers "all guard"
HUNT_GUARD_TIMEOUT  = 12   # seconds to wait in phase 3 for enemy to close

# Animal Whispering mastery spell
WHISPER_ENABLED      = True
WHISPER_INTERVAL_SEC = 1800  # seconds between casts (30 min)

# Pet context menu entry indices (right-click the pet)
PET_CMD_FOLLOW = 2   # "Command: Follow"
PET_CMD_GUARD  = 3   # "Command: Guard"
PET_CMD_KILL   = 4   # "Command: Kill" — if mobs aren't attacked, verify index with gump_dump.py

# Items auto-looted by Razor's AutoLoot agent that should be transferred to the
# storage chest on each banking trip. Add/remove item IDs to match your AutoLoot list.
TRANSFER_ITEMS = [
    0x1079,   # hides
    0x26B4,   # red scales
    0x26B5,   # yellow scales
    0x26B6,   # black scales
    0x26B7,   # green scales
    0x26B8,   # white scales
    0x26B9,   # blue scales
    0x14EB,   # treasure map
    0x14EC,   # treasure map (decoded)
    # alchemy reagents (all share ItemID 0x423A, hue distinguishes variant)
    0x423A,   # potash / black powder / charcoal / saltpeter
    # gems
    0x0F26,   # diamond
    0x0F25,   # amber
    0x0F0F,   # star sapphire
    0x0F10,   # emerald
    0x0F15,   # citrine
    0x0F11,   # sapphire
    0x0F13,   # ruby
    0x0F18,   # tourmaline
    0x0F16,   # amethyst
]

# Auto-bank gold
WEIGHT_BANK_THRESHOLD = 0.90        # recall home when weight ratio >= this
GOLD_DEST_SERIAL      = config.quick_dropbox
HOME_RUNEBOOK_NAME    = "home"      # label on the runebook item (case-insensitive)
FARM_RUNE_NAME        = None        # set at runtime via prompt
RECALL_SETTLE_DELAY   = 2000        # ms to wait after recall lands

# Known farm locations — shown as suggestions in the startup prompt.
# The rune name must match the label on the rune in the runebook (case-insensitive).
FARM_LOCATIONS = [
    'ww',        # Wind Wyrms
    'iceogre',   # Ice Ogre Lords
    'demons',    # Demons
    'ogrelords', # Ogre Lords
    'liches',    # Liches
    'balron',    # Balrons
    'ancient',   # Ancient Wyrms
    'titans',    # Titans
    'cavetroll', # Cave Trolls
]

GOLD_ITEM_ID = 0x0EED

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local/guardian_stats.json")
os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

# ─── Session gold tracking ────────────────────────────────────────────────────

_pet_serial      = None
_session_start   = None
_session_gold    = 0
_last_whisper    = 0.0
_kill_times      = {}   # { enemy_serial: timestamp } — throttle repeated kill commands

KILL_COOLDOWN_SEC = 8   # minimum seconds between kill commands for the same enemy


def _append_gold_stat(gold_this_trip):
    global _session_gold
    _session_gold += gold_this_trip
    elapsed = time.time() - _session_start
    gph = int(_session_gold / elapsed * 3600) if elapsed > 0 else 0
    entry = {
        "player":        Player.Name,
        "rune":          FARM_RUNE_NAME,
        "time":          time.strftime("%Y-%m-%d %H:%M:%S"),
        "gold_per_hour": gph,
    }
    try:
        with open(STATS_FILE, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = []
    data.append(entry)
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log("Gold/hr: %d  (session: %d gold, %.1f min)" % (gph, _session_gold, elapsed / 60), colors['cyan'])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[guardian] " + msg, color)


def _pet_cmd(serial, entry, target_serial=None):
    """Issue a pet command silently via the context menu.
    Pass target_serial for commands that open a target cursor (e.g. Follow)."""
    if Misc.WaitForContext(serial, 2000):
        Misc.ContextReply(serial, entry)
        if target_serial is not None:
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(target_serial)
    Misc.Pause(400)


# ─── Auto-bank gold ───────────────────────────────────────────────────────────


def transfer_loot_to_chest():
    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Storage chest (0x%X) not found — skipping loot transfer." % GOLD_DEST_SERIAL, colors['red'])
        return
    for item_id in TRANSFER_ITEMS:
        item = Items.FindByID(item_id, -1, Player.Backpack.Serial)
        while item is not None:
            Items.Move(item, dest, item.Amount)
            Misc.Pause(800)
            item = Items.FindByID(item_id, -1, Player.Backpack.Serial)


def transfer_gold():
    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Gold destination (0x%X) not found — set GOLD_DEST_SERIAL in config." % GOLD_DEST_SERIAL, colors['red'])
        return
    total = 0
    gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
    while gold is not None:
        total += gold.Amount
        Items.Move(gold, dest, gold.Amount)
        Misc.Pause(800)
        gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
    if total:
        log("Deposited %d gold into 0x%X." % (total, GOLD_DEST_SERIAL), colors['cyan'])
    else:
        log("No gold to deposit.", colors['yellow'])
    return total


def _walk_to_drop():
    """Step east → north → west to reach the drop-off container."""
    for direction in ('East', 'North', 'West'):
        Player.Walk(direction)
        Misc.Pause(600)


def do_banking(rb):
    """Travel home, deposit everything, then return to the farm rune."""
    if not travel_to_runebook(rb, RECALL_SETTLE_DELAY):
        log("Failed to travel home — banking aborted.", colors['red'])
        return False
    _walk_to_drop()
    gold = transfer_gold()
    transfer_loot_to_chest()
    if gold and _session_start is not None:
        _append_gold_stat(gold)
    return True


def bank_gold_if_heavy():
    if Player.MaxWeight == 0:
        return
    ratio = float(Player.Weight) / Player.MaxWeight
    if ratio < WEIGHT_BANK_THRESHOLD:
        return

    log("Weight at %.0f%% — banking." % (ratio * 100), colors['yellow'])

    rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
    if rb is None:
        log("No runebook named '%s' in backpack — cannot bank." % HOME_RUNEBOOK_NAME, colors['red'])
        return

    if do_banking(rb):
        travel_to_named_rune(rb, FARM_RUNE_NAME, RECALL_SETTLE_DELAY)
        Player.ChatSay("all guard me")


def discover_pet():
    """Mount-test nearby non-human mobiles to lock in the pet serial."""
    global _pet_serial

    # Already mounted — dismount first so the pet appears in the mobile list,
    # then fall through to the scan loop to capture the correct Mobile serial.
    if Player.Mount is not None:
        log("Already mounted — dismounting before scan.", colors['cyan'])
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(2000)

    log("Scanning for mountable pet within %d tiles..." % PET_SCAN_RANGE, colors['cyan'])
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
        # Player.Mount is an Item whose serial may differ from the Mobile serial,
        # so just confirm something was mounted rather than comparing serials.
        if Player.Mount is not None:
            _pet_serial = mob.Serial
            log("Pet locked: %s (0x%X) — dismounting." % (mob.Name, _pet_serial), colors['cyan'])
            Mobiles.UseMobile(Player.Serial)
            Misc.Pause(1500)
            return True

    log("No mountable non-human pet found — target your pet manually.", colors['yellow'])
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


def shutdown():
    """Called on every script exit — guard pet then recall home."""
    log("Shutting down — returning home.", colors['cyan'])
    if not Player.IsGhost:
        Player.ChatSay("all guard me")
        rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
        if rb is not None and travel_to_runebook(rb, RECALL_SETTLE_DELAY):
            for direction in ('East', 'North', 'West', 'West'):
                Player.Walk(direction)
                Misc.Pause(600)
    log("Guardian stopped.", colors['cyan'])


def hunt_cycle(pet, enemy_serial):
    """Send pet to kill an enemy, recall when engaged, guard when enemy closes.

    Phase 1 — watch until pet is within KILL_ENGAGE_RANGE of the enemy (or enemy dies).
    Phase 2 — recall pet using existing leash loop.
    Phase 3 — issue guard once enemy closes to GUARD_TRIGGER_RANGE; timeout after HUNT_GUARD_TIMEOUT s.

    Returns True if guard was issued, False otherwise.
    """
    # ── Phase 1: engagement watch ──────────────────────────────────────────────
    log("Hunting — waiting for pet to engage...", colors['yellow'])
    prev_enemy_dist  = None
    phase1_deadline  = time.time() + 30  # give up if pet never closes on enemy
    while not Player.IsGhost and time.time() < phase1_deadline:
        check_pet_health(pet)
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
        enemy = Mobiles.FindBySerial(enemy_serial)
        if enemy is None:
            log("Enemy defeated.", colors['green'])
            return False  # enemy gone, no guard cycle needed
        curr_enemy_dist = Player.DistanceTo(enemy)
        if prev_enemy_dist is not None and curr_enemy_dist > prev_enemy_dist + 3:
            log("Enemy fleeing — re-tagging and recalling.", colors['yellow'])
            Player.ChatSay("all kill")
            Misc.Pause(300)
            if Target.WaitForTarget(2000, False):
                Target.TargetExecute(enemy_serial)
            Player.ChatSay("all follow me")
            break  # pet tagged and recalled; enemy will follow via aggro
        prev_enemy_dist = curr_enemy_dist
        pet_to_enemy = max(
            abs(pet.Position.X - enemy.Position.X),
            abs(pet.Position.Y - enemy.Position.Y),
        )
        if pet_to_enemy <= KILL_ENGAGE_RANGE:
            log("Pet engaged — recalling.", colors['yellow'])
            break
        Misc.Pause(CHECK_INTERVAL)

    # ── Phase 2: rapid recall (1s poll — much tighter than the 4s leash loop) ──
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

    # ── Phase 3: guard when enemy closes ──────────────────────────────────────
    log("Waiting for enemy to close (guard trigger = %d tiles)..." % GUARD_TRIGGER_RANGE, colors['yellow'])
    deadline = time.time() + HUNT_GUARD_TIMEOUT
    while time.time() < deadline and not Player.IsGhost:
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
        enemy = Mobiles.FindBySerial(enemy_serial)
        if enemy is None or Player.DistanceTo(enemy) <= GUARD_TRIGGER_RANGE:
            if pet is not None:
                _pet_cmd(pet.Serial, PET_CMD_GUARD)
            log("Guard issued — enemy in range.", colors['cyan'])
            return True
        Misc.Pause(500)

    log("Hunt guard timeout — resuming normal loop.", colors['yellow'])
    return False


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    global _session_start, _session_gold, FARM_RUNE_NAME
    _session_start = time.time()
    _session_gold  = 0

    # ── Location prompt ───────────────────────────────────────────────────────
    Misc.SendMessage('[guardian] Farm location — say the number:', colors['cyan'])
    for i, loc in enumerate(FARM_LOCATIONS):
        Misc.SendMessage('[guardian]   %d) %s' % (i + 1, loc), colors['cyan'])
    Misc.Pause(600)
    Journal.Clear()
    Misc.Pause(200)
    Journal.Clear()

    chosen = None
    deadline = time.time() + 30
    while time.time() < deadline and chosen is None:
        for i, loc in enumerate(FARM_LOCATIONS):
            if Journal.SearchByName(str(i + 1), Player.Name):
                chosen = loc
                break
        Misc.Pause(200)

    if chosen is None:
        log("No location selected (30s timeout) — stopping.", colors['red'])
        return
    Journal.Clear()
    FARM_RUNE_NAME = chosen
    log("Target: %s" % FARM_RUNE_NAME, colors['cyan'])

    # ── Pet discovery (before recall so mount is confirmed at the house) ─────
    if not discover_pet():
        log("Pet discovery failed — stopping.", colors['red'])
        return

    # ── Recall from house to farm location ────────────────────────────────────
    rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
    if rb is None:
        log("Runebook '%s' not found in backpack — stopping." % HOME_RUNEBOOK_NAME, colors['red'])
        return
    log("Recalling to '%s'..." % FARM_RUNE_NAME, colors['cyan'])
    if not travel_to_named_rune(rb, FARM_RUNE_NAME, RECALL_SETTLE_DELAY):
        log("Failed to recall to '%s' — stopping." % FARM_RUNE_NAME, colors['red'])
        return

    log("Guardian started.", colors['cyan'])

    is_guarding = False
    is_hunting  = False
    guard_pos   = None  # player tile when "all guard me" was last issued

    # Default to guard immediately so the pet is already protecting on script start.
    # Voice command works at any distance (covers drop-off / resume scenarios).
    if find_pet() is not None:
        Player.ChatSay("all guard me")
        is_guarding = True
        guard_pos   = (Player.Position.X, Player.Position.Y)
        log("Default guard active.", colors['cyan'])

    Journal.Clear()
    log("Say 'bank' to deposit and stop.", colors['cyan'])

    try:
        while not Player.IsGhost:
            if Journal.Search(Player.Name + ": bank"):
                Journal.Clear()
                log("Bank command — depositing and stopping.", colors['yellow'])
                rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
                if rb is not None:
                    do_banking(rb)
                break

            bank_gold_if_heavy()

            pet = find_pet()

            # Break guard when the player moves far enough from the guard origin.
            # Suppressed while enemies are adjacent — combat movement would otherwise
            # trigger "all follow me" every tick and cause a kill/follow spam loop.
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
            cast_animal_whispering(pet)

            # ── Recall if too far (skipped while guarding — pet drifts naturally) ──
            if not is_guarding and Player.DistanceTo(pet) > PET_FOLLOW_RANGE:
                guard_pos = None
                arrived   = recall_pet(pet)
                if not arrived:
                    fresh = find_pet()
                    if fresh is None or Player.DistanceTo(fresh) > PET_FOLLOW_RANGE + 1:
                        Misc.Pause(CHECK_INTERVAL)
                        continue
                    pet = fresh

            # ── Enemy scan → kill, or guard if clear ──────────────────────────
            # Guard and kill are mutually exclusive each tick: issuing both back-to-back
            # on the same pet causes the second context-menu call to silently fail.
            enemies = [] if is_hunting else list(GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE))

            if enemies:
                nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
                if Player.DistanceTo(nearest) <= GUARD_TRIGGER_RANGE:
                    # Enemy already on us — engage and guard in place (no pull cycle).
                    # Issue kill once per cooldown — prevents spam when guard breaks
                    # during combat movement and the branch re-fires every tick.
                    if time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC:
                        log("Enemy on us: %s — engaging in place." % nearest.Name, colors['yellow'])
                        Player.ChatSay("all kill")
                        Misc.Pause(300)
                        if Target.WaitForTarget(2000, False):
                            Target.TargetExecute(nearest.Serial)
                        _kill_times[nearest.Serial] = time.time()
                    if not is_guarding:
                        is_guarding = True
                        guard_pos   = (Player.Position.X, Player.Position.Y)
                else:
                    # Enemy at range — send pet to intercept and draw it back.
                    log("Enemy: %s — sending pet to kill." % nearest.Name, colors['red'])
                    Player.ChatSay("all kill")
                    Misc.Pause(300)
                    if Target.WaitForTarget(2000, False):
                        Target.TargetExecute(nearest.Serial)
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

    finally:
        shutdown()


main()
