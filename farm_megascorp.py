# farm_megascorp.py
# Pet-kill farming at Megascorp dungeon with pack beetle gold collection.
#
# Flow:
#   1. Detect pack beetle (body-ID scan).
#   2. Detect combat pet (mount-test, skips beetle).
#   3. Mount beetle, recall to 'megascorp' rune in the home runebook.
#   4. Dismount, walk scorp_door waypoints → use dungeon door → walk scorp_dungeon waypoints.
#   5. Kill loop: send pet to kill enemies; walk to each corpse, loot gold → beetle,
#      then return to staging position (last point of scorp_dungeon waypoints).
#      Exits when a gold transfer is rejected (beetle full).
#   6. Walk scorp_exit waypoints to the recall point.
#   7. Mount beetle, recall home, unload beetle to containers.

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
    """Dismount, then scan for pack beetle by body ID with backpack fallback."""
    _dismount()

    filt          = Mobiles.Filter()
    filt.Enabled  = True
    filt.RangeMax = BEETLE_SCAN_RANGE
    filt.IsHuman  = False

    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial or mob.IsHuman:
            continue
        if mob.Body == PACK_BEETLE_BODY and mob.Backpack is not None:
            log("Pack beetle found: %s (0x%X)." % (mob.Name, mob.Serial), colors['green'])
            return mob

    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial or mob.IsHuman:
            continue
        if mob.Backpack is not None:
            log("Pack animal (fallback): %s (0x%X)." % (mob.Name, mob.Serial), colors['green'])
            return mob

    log("No pack animal found within %d tiles." % BEETLE_SCAN_RANGE, colors['red'])
    return None


def _get_beetle_pack(beetle):
    pack = beetle.Backpack
    if pack is None:
        log("Beetle has no accessible backpack.", colors['red'])
        return None
    Items.UseItem(pack)
    Items.WaitForContents(pack.Serial, 3000)
    Misc.Pause(600)
    return pack

# ─── Combat pet discovery ─────────────────────────────────────────────────────

def _discover_combat_pet(beetle_serial):
    """Mount-test nearby non-human mobiles (skipping the beetle) to lock in
    the combat pet serial. Falls back to manual targeting."""
    global _pet_serial

    _dismount()

    log("Scanning for combat pet within %d tiles..." % PET_SCAN_RANGE, colors['cyan'])
    f          = Mobiles.Filter()
    f.Enabled  = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE

    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial in (Player.Serial, beetle_serial) or mob.IsHuman:
            continue
        log("Trying %s (0x%X)..." % (mob.Name, mob.Serial), colors['yellow'])
        Mobiles.UseMobile(mob.Serial)
        Misc.Pause(1500)
        if Player.Mount is not None:
            _pet_serial = mob.Serial
            log("Combat pet locked: %s (0x%X) — dismounting." % (mob.Name, _pet_serial), colors['cyan'])
            _dismount()
            return True

    log("No mountable combat pet found — click your pet.", colors['yellow'])
    serial = Target.PromptTarget("Click your combat pet:")
    if serial and serial != 0:
        _pet_serial = serial
        mob  = Mobiles.FindBySerial(serial)
        name = mob.Name if mob is not None else ('0x%X' % serial)
        log("Combat pet locked via prompt: %s (0x%X)." % (name, serial), colors['cyan'])
        return True
    return False

# ─── Pet care ─────────────────────────────────────────────────────────────────

def _find_pet():
    f          = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        if _pet_serial is not None and mob.Serial == _pet_serial:
            return mob
    nearest, nearest_dist = None, 9999
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        d = Player.DistanceTo(mob)
        if d < nearest_dist:
            nearest_dist = d
            nearest = mob
    return nearest


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
            log("Pet returned — resuming heal.", colors['cyan'])
            return pet
    log("Pet did not return to heal range — skipping heal.", colors['yellow'])
    return pet


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
        Spells.CastMagery('Arch Cure')
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(pet.Serial)
        Misc.Pause(1200)

    if hp_ratio < CRITICAL_HEALTH_THRESHOLD:
        if _has_magery:
            log("HP critical (%.0f%%) — 3x healing %s." % (hp_ratio * 100, pet.Name), colors['red'])
            for _ in range(3):
                Spells.CastMagery('Greater Heal')
                Target.WaitForTarget(3000, False)
                Target.TargetExecute(pet.Serial)
                Misc.Pause(800)
        elif _has_chiv:
            log("HP critical (%.0f%%) — Close Wounds x3 on %s." % (hp_ratio * 100, pet.Name), colors['red'])
            for _ in range(3):
                Spells.CastChivalry('Close Wounds')
                Target.WaitForTarget(3000, False)
                Target.TargetExecute(pet.Serial)
                Misc.Pause(800)
    elif hp_ratio < FAST_HEAL_THRESHOLD:
        if _has_magery:
            log("HP low (%.0f%%) — 2x healing %s." % (hp_ratio * 100, pet.Name), colors['yellow'])
            for _ in range(2):
                Spells.CastMagery('Greater Heal')
                Target.WaitForTarget(3000, False)
                Target.TargetExecute(pet.Serial)
                Misc.Pause(800)
        elif _has_chiv:
            log("HP low (%.0f%%) — Close Wounds x2 on %s." % (hp_ratio * 100, pet.Name), colors['yellow'])
            for _ in range(2):
                Spells.CastChivalry('Close Wounds')
                Target.WaitForTarget(3000, False)
                Target.TargetExecute(pet.Serial)
                Misc.Pause(800)
    elif hp_ratio < HEALTH_THRESHOLD:
        if _has_magery:
            log("Healing %s." % pet.Name, colors['cyan'])
            Spells.CastMagery('Greater Heal')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(pet.Serial)
            Misc.Pause(1200)
        elif _has_chiv:
            log("Close Wounds on %s." % pet.Name, colors['cyan'])
            Spells.CastChivalry('Close Wounds')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(pet.Serial)
            Misc.Pause(1200)

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


def _send_kill(target_serial):
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


def _ensure_beetle_nearby(beetle_serial):
    """Call beetle back if it has drifted out of item-transfer range."""
    beetle = Mobiles.FindBySerial(beetle_serial)
    if beetle is not None and Player.DistanceTo(beetle) <= BEETLE_TRANSFER_RANGE:
        return
    log("Beetle out of range — recalling.", colors['yellow'])
    Player.ChatSay("all follow me")
    Misc.Pause(2000)


def _drop_beetle_loot(beetle_pack):
    """Walk to the drop box and move all beetle contents into it."""
    _dismount()
    _walk_to_drop()
    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Drop box (0x%X) not found." % GOLD_DEST_SERIAL, colors['red'])
        return
    Items.UseItem(beetle_pack)
    Items.WaitForContents(beetle_pack.Serial, 3000)
    Misc.Pause(600)
    total_gold = 0
    for item in list(beetle_pack.Contains or []):
        if item.ItemID == GOLD_ITEM_ID:
            total_gold += item.Amount
        Items.Move(item, dest, item.Amount)
        Misc.Pause(800)
    if total_gold:
        _append_gold_stat(total_gold)
    log("Beetle unloaded.", colors['green'])


# ─── Kill + gold loot loop ────────────────────────────────────────────────────

def _kill_loot_loop(beetle_serial, beetle_pack, staging_x, staging_y):
    """
    Send pet to kill enemies; walk to each corpse, loot gold to beetle,
    then return to (staging_x, staging_y) between corpses.

    Exits when beetle is genuinely full (transfer fails even after beetle is recalled),
    or when player dies.

    Returns: 'beetle_full' | 'ghost' | 'disconnected'
    """
    looted = set()

    while Player.Connected and not Player.IsGhost:
        # ── Pet + player care ─────────────────────────────────────────────────
        pet = _find_pet()
        if pet is not None:
            _check_pet_health(pet)
            _cast_animal_whispering(pet)
        check_player_health()

        # ── Send pet to kill nearest enemy; apply combat buffs ────────────────
        enemies = [e for e in GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE)
                   if e.Serial not in _skip_serials]
        if enemies:
            nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
            if time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC:
                log("Enemy: %s — sending pet." % nearest.Name, colors['red'])
                _send_kill(nearest.Serial)
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
            if Player.MaxWeight > 0 and float(Player.Weight) / Player.MaxWeight < TRANSFER_WEIGHT_THRESHOLD:
                log("Weight %.0f%% — holding gold in pack, will transfer when heavier." % (
                    float(Player.Weight) / Player.MaxWeight * 100), colors['yellow'])
            else:
                _ensure_beetle_nearby(beetle_serial)
                gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
                while gold is not None:
                    _, full = transfer_to_beetle(gold, beetle_pack)
                    if full:
                        log("Beetle full — exiting dungeon.", colors['yellow'])
                        return 'beetle_full'
                    gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
        else:
            Misc.Pause(IDLE_WAIT_MS)

        Misc.Pause(CHECK_INTERVAL)

    if Player.IsGhost:
        return 'ghost'
    return 'disconnected'

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    global _session_start, _session_gold
    _session_start = time.time()
    _session_gold  = 0

    # ── Beetle detection ─────────────────────────────────────────────────────
    beetle = _find_beetle()
    if beetle is None:
        return
    beetle_pack = _get_beetle_pack(beetle)
    if beetle_pack is None:
        return

    # ── Combat pet detection ─────────────────────────────────────────────────
    if not _discover_combat_pet(beetle.Serial):
        log("Combat pet detection failed — stopping.", colors['red'])
        return

    _detect_skills()

    # ── Recall to megascorp ──────────────────────────────────────────────────
    rb = find_runebook_by_label(MEGASCORP_RUNEBOOK_NAME)
    if rb is None:
        log("Runebook '%s' not found — stopping." % MEGASCORP_RUNEBOOK_NAME, colors['red'])
        return

    mount_beetle(beetle.Serial)
    log("Recalling to '%s'..." % MEGASCORP_RUNE_NAME, colors['cyan'])
    if not travel_to_named_rune(rb, MEGASCORP_RUNE_NAME, RECALL_SETTLE_DELAY):
        log("Failed to recall to '%s' — stopping." % MEGASCORP_RUNE_NAME, colors['red'])
        return
    _dismount()

    # ── Walk to dungeon door ─────────────────────────────────────────────────
    wps_door = load_waypoints(WP_DOOR) if os.path.exists(WP_DOOR) else None
    if wps_door:
        log("Walking scorp_door waypoints (%d points)..." % len(wps_door), colors['cyan'])
        start_idx, _ = nearest_waypoint_index(wps_door)
        walk_waypoints(wps_door, start_idx)
    else:
        log("No waypoints_scorp_door.json found — skipping door walk.", colors['yellow'])

    # ── Use dungeon door ─────────────────────────────────────────────────────
    log("Using dungeon door (0x%X)..." % DOOR_SERIAL, colors['cyan'])
    Items.UseItem(DOOR_SERIAL)
    Misc.Pause(DOOR_WAIT_MS)

    # ── Walk into dungeon kill zone ──────────────────────────────────────────
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

    # ── Initial guard ─────────────────────────────────────────────────────────
    if _find_pet() is not None:
        Player.ChatSay("all guard me")
        log("Guard active — starting kill loop.", colors['cyan'])

    # ── Kill + gold loot loop ─────────────────────────────────────────────────
    reason = _kill_loot_loop(beetle.Serial, beetle_pack, staging_x, staging_y)

    if reason == 'ghost':
        log("Player died — stopping.", colors['red'])
        return

    # ── Exit dungeon via scorp_exit waypoints ─────────────────────────────────
    wps_exit = load_waypoints(WP_EXIT) if os.path.exists(WP_EXIT) else None
    if wps_exit:
        log("Walking scorp_exit waypoints (%d points)..." % len(wps_exit), colors['cyan'])
        start_idx, _ = nearest_waypoint_index(wps_exit)
        walk_waypoints(wps_exit, start_idx)
    else:
        log("No waypoints_scorp_exit.json — skipping exit walk.", colors['yellow'])

    # ── Recall home ───────────────────────────────────────────────────────────
    log("Recalling beetle before mounting...", colors['cyan'])
    Player.ChatSay("all follow me")
    Misc.Pause(2000)
    mount_beetle(beetle.Serial)
    log("Recalling home...", colors['cyan'])
    recall_home(HOME_RUNEBOOK_NAME, HOME_RUNE_NAME, RECALL_SETTLE_DELAY)

    # ── Unload beetle to drop box ─────────────────────────────────────────────
    _drop_beetle_loot(beetle_pack)

    log("Done.", colors['green'])


main()
