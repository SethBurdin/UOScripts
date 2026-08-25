# farm_megascorp.py
# Pet-kill farming at Megascorp dungeon with pack beetle gold collection.
#
# Flow:
#   1. Detect pack beetle (body-ID scan, mining.py style). A non-beetle pet is
#      still used as mount and fighter, but never receives gold — see step 6.
#   2. If the beetle already holds gold, recall home and deposit it first.
#   3. The beetle is also the combat pet — lock its serial directly.
#   4. Mount beetle, recall to 'megascorp' rune in the home runebook.
#   5. Dismount, walk scorp_door waypoints → use dungeon door → walk scorp_dungeon waypoints.
#   6. Kill loop: send pet to kill enemies; walk to each corpse, loot gold → beetle,
#      then return to staging position (last point of scorp_dungeon waypoints).
#      Exits when a gold transfer is rejected (beetle full) or the beetle
#      holds GOLD_BANK_THRESHOLD (60k) gold. Without a beetle, gold stays in
#      the player's backpack and the run exits at TRANSFER_WEIGHT_THRESHOLD.
#   7. Walk scorp_exit waypoints to the recall point.
#   8. Mount beetle, recall home, unload beetle to containers.

if False:
    from razorenhanced_stubs import *

import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.runebook_handler import find_runebook_by_label, travel_to_named_rune
from glossary.enemies import GetEnemies
from extraction_looter.corpse_util import (scan_nearby_corpses, walk_to_corpse,
                                           open_corpse)
import config
from extraction_looter.containers_util import transfer_to_beetle
from extraction_looter.nav import (load_waypoints, walk_waypoints,
                                   nearest_waypoint_index, recall_home)
from extraction_looter.stealth import mount_beetle

# ─── Config ───────────────────────────────────────────────────────────────────

MEGASCORP_RUNEBOOK_NAME = 'home'       # runebook label that holds the megascorp rune
MEGASCORP_RUNE_NAME     = 'megascorp'  # rune name inside that runebook
HOME_RUNEBOOK_NAME      = 'home'
HOME_RUNE_NAME          = 'new home'
RECALL_SETTLE_DELAY     = 2000         # ms to wait after each recall

# Serial of the dungeon entrance door (double-click to open)
DOOR_SERIAL   = 0x4001A734
DOOR_WAIT_MS  = 1500   # ms to wait after using the door before walking onward

PACK_BEETLE_BODY  = 0x0317   # body ID of the pack beetle
BEETLE_SCAN_RANGE = 10       # tile radius for beetle detection
PET_SCAN_RANGE    = 30       # tile radius for combat pet detection
ENEMY_SCAN_RANGE  = 12       # tile radius to scan for enemies
CORPSE_SCAN_RANGE = 12       # tile radius to scan for corpses
CHECK_INTERVAL    = 1500     # ms between main loop ticks
IDLE_WAIT_MS      = 2000     # ms to wait when no corpses found

GOLD_ITEM_ID     = 0x0EED
GOLD_DEST_SERIAL = config.quick_dropbox   # house container to deposit gold into
GOLD_BANK_THRESHOLD = 60000   # head home to deposit once the beetle holds this much gold

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local', 'guardian_stats.json')
os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

KILL_COOLDOWN_SEC = 8   # minimum seconds between kill commands for the same enemy

# Pet care thresholds
HEALTH_THRESHOLD          = 0.85
FAST_HEAL_THRESHOLD       = 0.50   # cast 2x heals back-to-back below this
CRITICAL_HEALTH_THRESHOLD = 0.40   # cast 3x heals back-to-back below this
VET_THRESHOLD             = 0.75

BEETLE_TRANSFER_RANGE = 3   # tiles — beetle must be this close for Items.Move to succeed
BANDAGE_ITEM_ID           = 0x0E21
BANDAGE_APPLY_MS          = 4000
MAGERY_MIN_SKILL  = 30.0
VET_MIN_SKILL     = 30.0
CHIV_MIN_SKILL    = 30.0
RANGED_MIN_SKILL  = 30.0

COMBAT_MANA_FLOOR = 0.30   # minimum mana ratio to cast combat/chiv spells
MANA_REGEN_TARGET = 0.90   # throttle combat spells until this ratio when mana is low

PLAYER_HEALTH_THRESHOLD = 0.85   # heal self when player HP drops below this
INVIS_BEFORE_HEAL       = True   # cast Invisibility before healing self
INVIS_SETTLE_MS         = 3000   # ms to wait after Invis before healing

TRANSFER_WEIGHT_THRESHOLD = 0.80   # only transfer gold to beetle when player weight is above this ratio

HEAL_CAST_RANGE      = 10   # tiles — max range for targeted healing spells
RECALL_FOLLOW_CHECKS = 3    # "all follow me" attempts before giving up on recall
RECALL_FOLLOW_MS     = 2000 # ms to wait between follow attempts

RETREAT_TRIGGER_RANGE = 4   # tiles — retreat when an enemy is this close to the player
RETREAT_STEPS         = 4   # max tiles to step away from a close enemy

PET_FOLLOW_RANGE      = 1     # tiles — beyond this the pet is leashed back
PET_LEASH_RANGE       = 7     # tiles — trigger leash recall when pet exceeds this (well inside HEAL_CAST_RANGE)
FOLLOW_CHECK_INTERVAL = 2000  # ms to wait after "all follow me" before checking distance
FOLLOW_MAX_CHECKS     = 3     # max polls before giving up on the leash recall

WHISPER_ENABLED      = True
WHISPER_INTERVAL_SEC = 1800

_WAYPOINTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'extraction_looter', 'waypoints')

WP_DOOR    = os.path.join(_WAYPOINTS_DIR, 'scorp_door.json')
WP_DUNGEON = os.path.join(_WAYPOINTS_DIR, 'scorp_dungeon.json')
WP_EXIT    = os.path.join(_WAYPOINTS_DIR, 'scorp_exit.json')

# ─── Runtime state ────────────────────────────────────────────────────────────

_pet_serial    = None
_kill_times    = {}
_skip_serials  = set()
_last_whisper  = 0.0
_has_magery       = False
_has_vet          = False
_has_chiv         = False
_has_ranged       = False
_attacking_serial = None
_session_start = None
_session_gold  = 0

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg, color=colors['cyan']):
    Misc.SendMessage('[megascorp] ' + msg, color)


def _append_gold_stat(gold_this_trip):
    global _session_gold
    _session_gold += gold_this_trip
    elapsed = time.time() - _session_start
    gph = int(_session_gold / elapsed * 3600) if elapsed > 0 else 0
    entry = {
        'player':        Player.Name,
        'rune':          MEGASCORP_RUNE_NAME,
        'time':          time.strftime('%Y-%m-%d %H:%M:%S'),
        'gold_per_hour': gph,
    }
    try:
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = []
    data.append(entry)
    with open(STATS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    log("Gold/hr: %d  (session: %d gold, %.1f min)" % (gph, _session_gold, elapsed / 60), colors['cyan'])

# ─── Navigation helpers ───────────────────────────────────────────────────────

def _dismount():
    if Player.Mount is not None:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)


def _walk_to(x, y):
    route              = PathFinding.Route()
    route.X            = x
    route.Y            = y
    route.DebugMessage = False
    route.StopIfStuck  = True
    PathFinding.Go(route)

# ─── Beetle discovery ─────────────────────────────────────────────────────────

def _find_beetle():
    """Dismount, then scan for pack beetle by body ID (mining.py style).
    Body ID alone identifies the beetle — the Backpack layer is often not
    cached until the pack has been opened, so requiring it here makes
    detection fail at script start. Pack access is verified afterward by
    _get_beetle_pack.

    Returns (mob, is_beetle). The fallback mob is only a mount and combat pet:
    a non-beetle body has no pack we can rely on, so gold is never handed to it
    — the run banks at TRANSFER_WEIGHT_THRESHOLD instead."""
    _dismount()

    for attempt in range(3):
        filt          = Mobiles.Filter()
        filt.Enabled  = True
        filt.RangeMax = BEETLE_SCAN_RANGE
        filt.IsHuman  = False
        mobs = Mobiles.ApplyFilter(filt)

        for mob in mobs:
            if mob.Serial == Player.Serial or mob.IsHuman:
                continue
            if mob.Body == PACK_BEETLE_BODY:
                log("Pack beetle found: %s (0x%X)." % (mob.Name, mob.Serial), colors['green'])
                return mob, True

        for mob in mobs:
            if mob.Serial == Player.Serial or mob.IsHuman:
                continue
            if mob.Backpack is not None:
                log("Non-beetle pet (fallback): %s (0x%X, body 0x%X) — gold stays on "
                    "the player and banks at %.0f%% weight." % (
                        mob.Name, mob.Serial, mob.Body, TRANSFER_WEIGHT_THRESHOLD * 100),
                    colors['yellow'])
                return mob, False

        log("No pack animal yet (scan %d/3) — retrying..." % (attempt + 1), colors['yellow'])
        Misc.Pause(1000)

    log("No pack animal found within %d tiles." % BEETLE_SCAN_RANGE, colors['red'])
    return None, False


def _open_container_retry(container_serial, attempts=6):
    """Open a container, retrying on rate-limit or if contents never arrive.
    Same pattern as bank_gold.py — a single UseItem right after a dismount or
    recall frequently misses the contents packet."""
    for attempt in range(1, attempts + 1):
        Journal.Clear()
        Items.UseItem(container_serial)
        Misc.Pause(900)
        if Journal.Search("You must wait"):
            log("Rate-limited opening container (attempt %d) — waiting..." % attempt, colors['yellow'])
            Misc.Pause(2000)
            continue
        if Items.WaitForContents(container_serial, 3000):
            Misc.Pause(300)
            return True
        log("Contents not received (attempt %d) — retrying..." % attempt, colors['yellow'])
        Misc.Pause(1000)
    log("Could not load container contents (0x%X)." % container_serial, colors['red'])
    return False


def _get_beetle_pack(beetle):
    pack = beetle.Backpack
    if pack is None:
        log("Beetle has no accessible backpack.", colors['red'])
        return None
    if not _open_container_retry(pack.Serial):
        return None
    return pack


def _beetle_gold_total(pack_serial):
    total = 0
    for item in Items.FindAllByID(GOLD_ITEM_ID, -1, pack_serial, -1):
        total += item.Amount
    return total


def _weight_heavy():
    """Player weight at or above the transfer threshold. Only consulted when
    there is no pack beetle to offload into — then it's the signal to bank."""
    if Player.MaxWeight == 0:
        return False
    return float(Player.Weight) / Player.MaxWeight >= TRANSFER_WEIGHT_THRESHOLD

# ─── Combat pet discovery ─────────────────────────────────────────────────────

def _lock_combat_pet(beetle):
    """The beetle IS the combat pet in this script — it hauls the gold and
    does the fighting. Lock its serial directly; no scanning or prompting."""
    global _pet_serial
    _pet_serial = beetle.Serial
    log("Combat pet is the beetle: %s (0x%X)." % (beetle.Name, beetle.Serial), colors['cyan'])

# ─── Pet care ─────────────────────────────────────────────────────────────────

def _find_pet():
    # Serial lookup first — the pet is the beetle, so the serial is always
    # known and this avoids depending on the Razor friends list.
    if _pet_serial is not None:
        mob = Mobiles.FindBySerial(_pet_serial)
        if mob is not None:
            return mob
    f          = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    nearest, nearest_dist = None, 9999
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        d = Player.DistanceTo(mob)
        if d < nearest_dist:
            nearest_dist = d
            nearest = mob
    return nearest


def _recall_pet_if_needed(pet):
    """Leash: if the pet has wandered beyond PET_LEASH_RANGE, issue 'all follow me'
    and poll until it returns. Guard is ALWAYS re-issued afterward — previously it
    was skipped when the pet took longer than one poll to return, leaving the pet
    in follow mode (trailing the player but not defending) for a long stretch.
    Returns (fresh_pet, was_recalled). Caller skips new kill orders when was_recalled is True."""
    if Player.DistanceTo(pet) <= PET_LEASH_RANGE:
        return pet, False
    log("Pet too far (%d tiles) — recalling." % Player.DistanceTo(pet), colors['yellow'])
    for _ in range(FOLLOW_MAX_CHECKS):
        Player.ChatSay("all follow me")
        Misc.Pause(FOLLOW_CHECK_INTERVAL)
        fresh = _find_pet()
        if fresh is not None:
            pet = fresh
        if Player.DistanceTo(pet) <= PET_LEASH_RANGE:
            break
    # 'all guard me' both pulls the pet to the player and restores guard mode,
    # so issue it even if the pet is still on its way.
    Player.ChatSay("all guard me")
    log("Guard re-issued after recall (pet at %d tiles)." % Player.DistanceTo(pet), colors['cyan'])
    return pet, True


def _ensure_pet_in_heal_range(pet):
    """Call pet back with 'all follow me' if it is outside HEAL_CAST_RANGE.
    Returns the refreshed pet reference (or the original if recall fails)."""
    if Player.DistanceTo(pet) <= HEAL_CAST_RANGE:
        return pet
    log("Pet too far to heal (%d tiles) — recalling." % Player.DistanceTo(pet), colors['yellow'])
    for _ in range(RECALL_FOLLOW_CHECKS):
        Player.ChatSay("all follow me")
        Misc.Pause(RECALL_FOLLOW_MS)
        fresh = _find_pet()
        if fresh is not None:
            pet = fresh
        if Player.DistanceTo(pet) <= HEAL_CAST_RANGE:
            log("Pet returned — re-guarding and resuming heal.", colors['cyan'])
            Player.ChatSay("all guard me")
            return pet
    log("Pet did not return to heal range — skipping heal.", colors['yellow'])
    return pet


def _cast_pet_heal(kind, spell_name, pet_serial):
    """Cast a targeted heal/cure, only targeting once the cursor actually
    appears. A cast rejected mid-recovery produces no cursor — wait out the
    recovery and retry instead of losing the cast. (Fixed-pause chaining
    fired follow-up heals before recovery finished, so the 2x/3x heals
    silently never happened.)"""
    for _ in range(3):
        if kind == 'magery':
            Spells.CastMagery(spell_name)
        else:
            Spells.CastChivalry(spell_name)
        if Target.WaitForTarget(4000, False):
            Target.TargetExecute(pet_serial)
            Misc.Pause(1200)
            return True
        Misc.Pause(800)   # no cursor — still recovering; wait and retry
    log("%s never got a target cursor — skipping." % spell_name, colors['yellow'])
    return False


def _ensure_pet_guarding():
    """Pull the pet to the player and put it in guard mode, verifying range.
    Used when entering the dungeon — the walk in can leave the pet behind if
    it wasn't in follow mode."""
    pet = _find_pet()
    if pet is None:
        log("No pet found to guard.", colors['yellow'])
        return
    for _ in range(RECALL_FOLLOW_CHECKS):
        if Player.DistanceTo(pet) <= PET_LEASH_RANGE:
            break
        log("Pet %d tiles away — calling it in before guard." % Player.DistanceTo(pet), colors['yellow'])
        Player.ChatSay("all follow me")
        Misc.Pause(RECALL_FOLLOW_MS)
        pet = _find_pet() or pet
    Player.ChatSay("all guard me")
    log("Guard active — pet at %d tiles." % Player.DistanceTo(pet), colors['cyan'])


def _check_pet_health(pet):
    if pet.HitsMax == 0:
        return
    hp_ratio = float(pet.Hits) / pet.HitsMax

    needs_care = (
        (pet.Poisoned or hp_ratio < HEALTH_THRESHOLD) and (_has_magery or _has_chiv)
        or (hp_ratio < VET_THRESHOLD and _has_vet)
    )
    if needs_care:
        pet = _ensure_pet_in_heal_range(pet)
        if Player.DistanceTo(pet) > HEAL_CAST_RANGE:
            return  # still out of range after recall attempts

    if pet.Poisoned and hp_ratio < HEALTH_THRESHOLD and _has_magery:
        log("Curing %s." % pet.Name, colors['cyan'])
        _cast_pet_heal('magery', 'Arch Cure', pet.Serial)

    if hp_ratio < CRITICAL_HEALTH_THRESHOLD:
        if _has_magery:
            log("HP critical (%.0f%%) — 3x healing %s." % (hp_ratio * 100, pet.Name), colors['red'])
            for _ in range(3):
                _cast_pet_heal('magery', 'Greater Heal', pet.Serial)
        elif _has_chiv:
            log("HP critical (%.0f%%) — Close Wounds x3 on %s." % (hp_ratio * 100, pet.Name), colors['red'])
            for _ in range(3):
                _cast_pet_heal('chiv', 'Close Wounds', pet.Serial)
    elif hp_ratio < FAST_HEAL_THRESHOLD:
        if _has_magery:
            log("HP low (%.0f%%) — 2x healing %s." % (hp_ratio * 100, pet.Name), colors['yellow'])
            for _ in range(2):
                _cast_pet_heal('magery', 'Greater Heal', pet.Serial)
        elif _has_chiv:
            log("HP low (%.0f%%) — Close Wounds x2 on %s." % (hp_ratio * 100, pet.Name), colors['yellow'])
            for _ in range(2):
                _cast_pet_heal('chiv', 'Close Wounds', pet.Serial)
    elif hp_ratio < HEALTH_THRESHOLD:
        if _has_magery:
            log("Healing %s." % pet.Name, colors['cyan'])
            _cast_pet_heal('magery', 'Greater Heal', pet.Serial)
        elif _has_chiv:
            log("Close Wounds on %s." % pet.Name, colors['cyan'])
            _cast_pet_heal('chiv', 'Close Wounds', pet.Serial)

    if hp_ratio < VET_THRESHOLD and _has_vet and not Player.BuffsExist('Healing'):
        bandage = Items.FindByID(BANDAGE_ITEM_ID, -1, Player.Backpack.Serial)
        if bandage is not None:
            log("Bandaging %s." % pet.Name, colors['cyan'])
            Items.UseItem(bandage.Serial)
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(pet.Serial)
            Misc.Pause(BANDAGE_APPLY_MS)


def _cast_animal_whispering(pet):
    global _last_whisper
    if not WHISPER_ENABLED or time.time() - _last_whisper < WHISPER_INTERVAL_SEC:
        return
    log("Casting Animal Whispering on %s." % pet.Name, colors['cyan'])
    Spells.Cast("Whispering")
    if Target.WaitForTarget(4000, False):
        Target.TargetExecute(pet.Serial)
    _last_whisper = time.time()


def check_player_health():
    if Player.HitsMax == 0:
        return
    hp_ratio = float(Player.Hits) / Player.HitsMax
    if hp_ratio >= PLAYER_HEALTH_THRESHOLD:
        return
    log("Player HP low (%.0f%%) — healing self." % (hp_ratio * 100), colors['red'])
    if _has_magery:
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
    elif _has_chiv:
        for _ in range(10):
            if Player.Hits >= Player.HitsMax:
                break
            Spells.CastChivalry('Close Wounds')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(Player.Serial)
            Misc.Pause(1200)
        log("Player healed.", colors['green'])


def player_attack_enemy(enemy):
    global _attacking_serial
    if not _has_ranged or enemy is None:
        return
    if _attacking_serial != enemy.Serial:
        log("Attacking %s." % enemy.Name, colors['yellow'])
        _attacking_serial = enemy.Serial
    Player.Attack(enemy.Serial)



def _retreat_from(enemy):
    """Step away from an enemy that spawned close to the player, one tile at a
    time along the dominant axis away from it. Stops early once the enemy is
    outside RETREAT_TRIGGER_RANGE or disappears."""
    for _ in range(RETREAT_STEPS):
        mob = Mobiles.FindBySerial(enemy.Serial)
        if mob is None:
            return
        if Player.DistanceTo(mob) > RETREAT_TRIGGER_RANGE:
            return
        dx = Player.Position.X - mob.Position.X
        dy = Player.Position.Y - mob.Position.Y
        if abs(dx) >= abs(dy):
            direction = 'East' if dx >= 0 else 'West'
        else:
            direction = 'South' if dy >= 0 else 'North'
        Player.Walk(direction)
        Misc.Pause(300)


def _send_kill(target_serial):
    """Point pet at a specific target, then immediately re-issue guard so it stays
    near the player and doesn't chase the target across the dungeon."""
    Journal.Clear()
    Player.ChatSay("all kill")
    Misc.Pause(300)
    if not Target.WaitForTarget(2000, False):
        Player.ChatSay("all guard me")
        return False
    Target.TargetExecute(target_serial)
    Misc.Pause(400)
    if Journal.Search("Target cannot be seen."):
        log("Target cannot be seen — skipping 0x%X." % target_serial, colors['yellow'])
        _skip_serials.add(target_serial)
        Player.ChatSay("all guard me")
        return False
    Player.ChatSay("all guard me")
    _kill_times[target_serial] = time.time()
    return True


def _detect_skills():
    global _has_magery, _has_vet, _has_chiv, _has_ranged
    archery  = Player.GetSkillValue('Archery')
    throwing = Player.GetSkillValue('Throwing')
    _has_magery = Player.GetSkillValue('Magery')     >= MAGERY_MIN_SKILL
    _has_vet    = Player.GetSkillValue('Veterinary') >= VET_MIN_SKILL
    _has_chiv   = Player.GetSkillValue('Chivalry')   >= CHIV_MIN_SKILL
    _has_ranged = archery >= RANGED_MIN_SKILL or throwing >= RANGED_MIN_SKILL
    if _has_magery:
        log("Magery %.1f — will use magery heals." % Player.GetSkillValue('Magery'), colors['cyan'])
    if _has_chiv:
        log("Chivalry %.1f — will use Enemy of One + Divine Fury." % Player.GetSkillValue('Chivalry'), colors['cyan'])
        if not _has_magery:
            log("  No Magery — using Close Wounds for pet healing.", colors['cyan'])
    if _has_ranged:
        skill_name = 'Archery' if archery >= throwing else 'Throwing'
        log("%s %.1f — will auto-attack enemies." % (skill_name, max(archery, throwing)), colors['cyan'])
    if _has_vet:
        log("Veterinary %.1f — will bandage pet." % Player.GetSkillValue('Veterinary'), colors['cyan'])

def apply_chiv_buffs():
    if not _has_chiv:
        return
    if Player.ManaMax == 0:
        return
    if float(Player.Mana) / Player.ManaMax < COMBAT_MANA_FLOOR:
        return
    if not Player.BuffsExist('Enemy of One'):
        log("Casting Enemy of One.", colors['cyan'])
        Spells.CastChivalry("Enemy of One")
        Misc.Pause(1500)
    if not Player.BuffsExist('Divine Fury'):
        log("Casting Divine Fury.", colors['cyan'])
        Spells.CastChivalry("Divine Fury")
        Misc.Pause(1500)


def _apply_death_ray(enemy):
    if Player.BuffsExist('Death Ray', False):
        return
    if Player.ManaMax == 0:
        return
    if float(Player.Mana) / Player.ManaMax < COMBAT_MANA_FLOOR:
        return
    log("Casting Death Ray on %s." % enemy.Name, colors['red'])
    Spells.CastMastery('Death Ray')
    if Target.WaitForTarget(5000, False):
        Target.TargetExecute(enemy.Serial)
    Misc.Pause(500)


# ─── Drop-off helpers ────────────────────────────────────────────────────────

def _walk_to_drop():
    for direction in ('East', 'North', 'West'):
        Player.Walk(direction)
        Misc.Pause(600)


def _guard_then_mount(beetle_serial):
    """Say 'all guard me' half a second before mounting so the combat pet
    re-anchors to the player right as we mount up."""
    Player.ChatSay("all guard me")
    Misc.Pause(500)
    mount_beetle(beetle_serial)


def _ensure_beetle_nearby(beetle_serial):
    """Call beetle back and poll until it is within BEETLE_TRANSFER_RANGE tiles."""
    beetle = Mobiles.FindBySerial(beetle_serial)
    if beetle is not None and Player.DistanceTo(beetle) <= BEETLE_TRANSFER_RANGE:
        return
    log("Beetle out of range — recalling.", colors['yellow'])
    for _ in range(6):
        Player.ChatSay("all follow me")
        Misc.Pause(1500)
        beetle = Mobiles.FindBySerial(beetle_serial)
        if beetle is not None and Player.DistanceTo(beetle) <= BEETLE_TRANSFER_RANGE:
            log("Beetle in range.", colors['cyan'])
            return
    log("Beetle did not return in time — proceeding anyway.", colors['yellow'])


def _drop_beetle_loot(beetle_serial):
    """Walk to the drop box (while mounted so the beetle arrives with us), then unload."""
    _walk_to_drop()   # beetle is our mount — it arrives at the drop position with us
    _dismount()       # beetle is now on the ground right at the drop box
    Misc.Pause(800)

    mob = Mobiles.FindBySerial(beetle_serial)
    if mob is None or mob.Backpack is None:
        log("Beetle (0x%X) not accessible for unloading." % beetle_serial, colors['red'])
        return
    pack = mob.Backpack

    # Open beetle pack first to load its contents into the client cache
    if not _open_container_retry(pack.Serial):
        return

    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Drop box (0x%X) not found." % GOLD_DEST_SERIAL, colors['red'])
        return
    # Open destination so the server registers it as an active container
    if not _open_container_retry(dest.Serial):
        return

    # Re-fetch the pack after contents arrive so .Contains is populated
    pack = Items.FindBySerial(pack.Serial)
    if pack is None:
        log("Beetle pack vanished after opening.", colors['red'])
        return

    total_gold = 0
    for item in list(pack.Contains or []):
        before_serial = item.Serial
        before_amount = item.Amount
        for attempt in range(1, 4):
            Journal.Clear()
            Items.Move(item, dest, item.Amount)
            Misc.Pause(1200)
            if Journal.Search("You must wait"):
                log("Rate-limited — waiting...", colors['yellow'])
                Misc.Pause(2000)
                continue
            # If the item (by ID+serial) is still in the beetle pack, dest is full
            still_in_pack = Items.FindByID(item.ItemID, -1, pack.Serial)
            if still_in_pack is not None and still_in_pack.Serial == before_serial:
                log("Drop box full — stopping transfer.", colors['yellow'])
                if total_gold:
                    _append_gold_stat(total_gold)
                return
            # Item left the pack — moved successfully
            if item.ItemID == GOLD_ITEM_ID:
                total_gold += before_amount
            break

    if total_gold:
        _append_gold_stat(total_gold)
    log("Beetle unloaded — %d gold deposited." % total_gold, colors['green'])


def _drop_player_gold():
    """Walk to the drop box and deposit gold from the player's own backpack.
    Used when the pet is not a pack beetle: the gold was never handed off, so
    it comes home on us instead."""
    _walk_to_drop()
    _dismount()
    Misc.Pause(800)

    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Drop box (0x%X) not found." % GOLD_DEST_SERIAL, colors['red'])
        return
    if not _open_container_retry(dest.Serial):
        return

    total = 0
    gold  = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
    while gold is not None:
        amount = gold.Amount
        Items.Move(gold, dest, amount)
        Misc.Pause(1200)
        # Same serial still in our pack means the move was rejected
        still = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
        if still is not None and still.Serial == gold.Serial:
            log("Drop box full — stopping transfer.", colors['yellow'])
            break
        total += amount
        gold = still

    if total:
        _append_gold_stat(total)
    log("Deposited %d gold from backpack." % total, colors['green'])


def _startup_deposit_if_needed(beetle_serial, beetle_pack):
    """Check beetle pack at script start; if it has gold, deposit before heading out.
    Recalls home first — _walk_to_drop assumes the home recall landing tile, so
    depositing from an arbitrary start position never reached the drop box."""
    total = _beetle_gold_total(beetle_pack.Serial)
    if total <= 0:
        log("Beetle pack empty — no startup deposit needed.", colors['green'])
        return
    log("Beetle has %d leftover gold — recalling home to deposit." % total, colors['yellow'])
    _guard_then_mount(beetle_serial)
    recall_home(HOME_RUNEBOOK_NAME, HOME_RUNE_NAME, RECALL_SETTLE_DELAY)
    _drop_beetle_loot(beetle_serial)


# ─── Kill + gold loot loop ────────────────────────────────────────────────────

def _kill_loot_loop(beetle_serial, beetle_pack, staging_x, staging_y):
    """
    Send pet to kill enemies; walk to each corpse, loot gold to beetle,
    then return to (staging_x, staging_y) between corpses.

    beetle_pack is None when the pet is not a pack beetle — gold then stays in
    the player's backpack and the run ends at TRANSFER_WEIGHT_THRESHOLD.

    Exits when beetle is genuinely full (transfer fails even after beetle is
    recalled), when the beetle holds GOLD_BANK_THRESHOLD gold, when the player
    is too heavy to keep carrying gold, or when player dies.

    Returns: 'beetle_full' | 'gold_target' | 'weight_full' | 'ghost' | 'disconnected'
    """
    looted = set()

    while Player.Connected and not Player.IsGhost:
        # ── Pet + player care ─────────────────────────────────────────────────
        pet = _find_pet()
        if pet is not None:
            pet, _ = _recall_pet_if_needed(pet)
            _check_pet_health(pet)
            _cast_animal_whispering(pet)
        check_player_health()

        # ── Engage + combat buffs ─────────────────────────────────────────────
        enemies = [e for e in GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE)
                   if e.Serial not in _skip_serials]
        if enemies:
            nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
            spawned_close = Player.DistanceTo(nearest) <= RETREAT_TRIGGER_RANGE
            if spawned_close:
                log("Enemy %s is %d tiles from us — stepping away." % (
                    nearest.Name, Player.DistanceTo(nearest)), colors['yellow'])
                _retreat_from(nearest)
            if pet is not None and (spawned_close or
                    time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC):
                log("Enemy: %s — sending pet." % nearest.Name, colors['red'])
                _send_kill(nearest.Serial)  # issues "all kill" then "all guard me"
            apply_chiv_buffs()
            if Player.BuffsExist('EnchantedSummoning'):
                _apply_death_ray(nearest)
            else:
                player_attack_enemy(nearest)

        # ── Loot gold from new corpses ────────────────────────────────────────
        corpses = [c for c in scan_nearby_corpses(CORPSE_SCAN_RANGE)
                   if int(c.Serial) not in looted]

        if corpses:
            # Phase 1 — collect gold from all corpses into player backpack
            for corpse in corpses:
                walk_to_corpse(corpse)
                if open_corpse(corpse):
                    for item in list(corpse.Contains or []):
                        if item.ItemID != GOLD_ITEM_ID:
                            continue
                        Items.Move(item, Player.Backpack, item.Amount)
                        Misc.Pause(800)
                        log("Picked up %d gold." % item.Amount, colors['green'])
                looted.add(int(corpse.Serial))

            # Phase 2 — return to staging, then transfer gold backpack → beetle
            log("Returning to staging position.", colors['cyan'])
            _walk_to(staging_x, staging_y)
            check_player_health()

            if beetle_pack is None:
                # No pack beetle — nothing to hand the gold to, so we carry it
                # and head home once it gets heavy.
                if _weight_heavy():
                    log("Weight at %.0f%% and no pack beetle — heading home to deposit." % (
                        float(Player.Weight) / Player.MaxWeight * 100), colors['yellow'])
                    return 'weight_full'
                Misc.Pause(CHECK_INTERVAL)
                continue

            _ensure_beetle_nearby(beetle_serial)
            gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
            while gold is not None:
                _, full = transfer_to_beetle(gold, beetle_pack)
                if full:
                    log("Beetle full — exiting dungeon.", colors['yellow'])
                    return 'beetle_full'
                gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)

            total = _beetle_gold_total(beetle_pack.Serial)
            if total >= GOLD_BANK_THRESHOLD:
                log("Beetle holds %d gold (>= %d) — heading home to deposit." % (
                    total, GOLD_BANK_THRESHOLD), colors['yellow'])
                return 'gold_target'
        else:
            Misc.Pause(IDLE_WAIT_MS)

        Misc.Pause(CHECK_INTERVAL)

    if Player.IsGhost:
        return 'ghost'
    return 'disconnected'

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    global _session_start, _session_gold, _kill_times, _skip_serials, _attacking_serial, _pet_serial

    while Player.Connected and not Player.IsGhost:
        _session_start    = time.time()
        _session_gold     = 0
        _kill_times       = {}
        _skip_serials     = set()
        _attacking_serial = None
        _pet_serial       = None

        # ── Beetle detection ─────────────────────────────────────────────────
        beetle, is_beetle = _find_beetle()
        if beetle is None:
            break

        beetle_pack = None
        if is_beetle:
            beetle_pack = _get_beetle_pack(beetle)
            if beetle_pack is None:
                break

            # ── Startup: deposit any leftover beetle gold before heading out ──
            _startup_deposit_if_needed(beetle.Serial, beetle_pack)

        # ── Combat pet + skill detection ─────────────────────────────────────
        _lock_combat_pet(beetle)
        _detect_skills()

        # ── Recall to megascorp ──────────────────────────────────────────────
        rb = find_runebook_by_label(MEGASCORP_RUNEBOOK_NAME)
        if rb is None:
            log("Runebook '%s' not found — stopping." % MEGASCORP_RUNEBOOK_NAME, colors['red'])
            break

        _guard_then_mount(beetle.Serial)
        log("Recalling to '%s'..." % MEGASCORP_RUNE_NAME, colors['cyan'])
        if not travel_to_named_rune(rb, MEGASCORP_RUNE_NAME, RECALL_SETTLE_DELAY):
            log("Failed to recall to '%s' — stopping." % MEGASCORP_RUNE_NAME, colors['red'])
            break
        _dismount()
        # Beetle must tail us through the door and dungeon walk
        Player.ChatSay("all follow me")
        Misc.Pause(500)

        # ── Walk to dungeon door ─────────────────────────────────────────────
        wps_door = load_waypoints(WP_DOOR) if os.path.exists(WP_DOOR) else None
        if wps_door:
            log("Walking scorp_door waypoints (%d points)..." % len(wps_door), colors['cyan'])
            start_idx, _ = nearest_waypoint_index(wps_door)
            walk_waypoints(wps_door, start_idx)
        else:
            log("No waypoints_scorp_door.json found — skipping door walk.", colors['yellow'])

        # ── Use dungeon door ─────────────────────────────────────────────────
        log("Using dungeon door (0x%X)..." % DOOR_SERIAL, colors['cyan'])
        Items.UseItem(DOOR_SERIAL)
        Misc.Pause(DOOR_WAIT_MS)

        # ── Walk into dungeon kill zone ──────────────────────────────────────
        wps_dungeon = load_waypoints(WP_DUNGEON) if os.path.exists(WP_DUNGEON) else None
        if wps_dungeon:
            log("Walking scorp_dungeon waypoints (%d points)..." % len(wps_dungeon), colors['cyan'])
            start_idx, _ = nearest_waypoint_index(wps_dungeon)
            walk_waypoints(wps_dungeon, start_idx)
            staging_x, staging_y = wps_dungeon[-1][0], wps_dungeon[-1][1]
            log("Staging position: (%d, %d)." % (staging_x, staging_y), colors['cyan'])
        else:
            log("No waypoints_scorp_dungeon.json — using current position as staging.", colors['yellow'])
            staging_x = Player.Position.X
            staging_y = Player.Position.Y

        # ── Initial guard (verify the beetle made it to staging) ─────────────
        _ensure_pet_guarding()

        # ── Kill + gold loot loop ─────────────────────────────────────────────
        reason = _kill_loot_loop(beetle.Serial, beetle_pack, staging_x, staging_y)

        if reason == 'ghost':
            log("Player died — stopping.", colors['red'])
            break

        # ── Exit dungeon via scorp_exit waypoints ─────────────────────────────
        wps_exit = load_waypoints(WP_EXIT) if os.path.exists(WP_EXIT) else None
        if wps_exit:
            log("Walking scorp_exit waypoints (%d points)..." % len(wps_exit), colors['cyan'])
            start_idx, _ = nearest_waypoint_index(wps_exit)
            walk_waypoints(wps_exit, start_idx)
        else:
            log("No waypoints_scorp_exit.json — skipping exit walk.", colors['yellow'])

        # ── Recall home (mounted so beetle travels with us) ───────────────────
        log("Recalling beetle before mounting...", colors['cyan'])
        Player.ChatSay("all follow me")
        Misc.Pause(2000)
        _guard_then_mount(beetle.Serial)
        log("Recalling home...", colors['cyan'])
        recall_home(HOME_RUNEBOOK_NAME, HOME_RUNE_NAME, RECALL_SETTLE_DELAY)

        # ── Unload to drop box (still mounted; dismount at destination) ───────
        if is_beetle:
            _drop_beetle_loot(beetle.Serial)
        else:
            _drop_player_gold()

        log("Run complete — restarting.", colors['green'])
        Misc.Pause(2000)


main()
