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

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.runebook_handler import find_runebook_by_label, travel_to_named_rune
from glossary.enemies import GetEnemies
from extraction_looter.corpse_util import (scan_nearby_corpses, walk_to_corpse,
                                           open_corpse)
from extraction_looter.containers_util import transfer_to_beetle
from extraction_looter.nav import (load_waypoints, walk_waypoints,
                                   nearest_waypoint_index, recall_home)
from extraction_looter.dropoff_util import unload_beetle_to_containers
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

GOLD_ITEM_ID = 0x0EED

KILL_COOLDOWN_SEC = 8   # minimum seconds between kill commands for the same enemy

# Pet care thresholds
HEALTH_THRESHOLD          = 0.85
CRITICAL_HEALTH_THRESHOLD = 0.40
VET_THRESHOLD             = 0.75
BANDAGE_ITEM_ID           = 0x0E21
BANDAGE_APPLY_MS          = 4000
MAGERY_MIN_SKILL          = 30.0
VET_MIN_SKILL             = 30.0

WHISPER_ENABLED      = True
WHISPER_INTERVAL_SEC = 1800

_WAYPOINTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'extraction_looter', 'waypoints')

WP_DOOR    = os.path.join(_WAYPOINTS_DIR, 'scorp_door.json')
WP_DUNGEON = os.path.join(_WAYPOINTS_DIR, 'scorp_dungeon.json')
WP_EXIT    = os.path.join(_WAYPOINTS_DIR, 'scorp_exit.json')

# ─── Runtime state ────────────────────────────────────────────────────────────

_pet_serial   = None
_kill_times   = {}
_skip_serials = set()
_last_whisper = 0.0
_has_magery   = False
_has_vet      = False

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg, color=colors['cyan']):
    Misc.SendMessage('[megascorp] ' + msg, color)

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


def _check_pet_health(pet):
    if pet.HitsMax == 0:
        return
    hp_ratio = float(pet.Hits) / pet.HitsMax

    if pet.Poisoned and hp_ratio < HEALTH_THRESHOLD and _has_magery:
        log("Curing %s." % pet.Name, colors['cyan'])
        Spells.CastMagery('Arch Cure')
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(pet.Serial)
        Misc.Pause(1200)

    if hp_ratio < CRITICAL_HEALTH_THRESHOLD and _has_magery:
        log("HP critical (%.0f%%) — rapid healing %s." % (hp_ratio * 100, pet.Name), colors['red'])
        for _ in range(3):
            Spells.CastMagery('Greater Heal')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(pet.Serial)
            Misc.Pause(800)
    elif hp_ratio < HEALTH_THRESHOLD and _has_magery:
        log("Healing %s." % pet.Name, colors['cyan'])
        Spells.CastMagery('Greater Heal')
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
    global _has_magery, _has_vet
    _has_magery = Player.GetSkillValue('Magery') >= MAGERY_MIN_SKILL
    _has_vet    = Player.GetSkillValue('Veterinary') >= VET_MIN_SKILL
    if _has_magery:
        log("Magery detected — will cast heals/cures on pet.", colors['cyan'])
    if _has_vet:
        log("Veterinary detected — will bandage pet.", colors['cyan'])

# ─── Kill + gold loot loop ────────────────────────────────────────────────────

def _kill_loot_loop(beetle_pack, staging_x, staging_y):
    """
    Send pet to kill enemies; walk to each corpse, loot gold to beetle,
    then return to (staging_x, staging_y) between corpses.

    Exits when a gold transfer is rejected (beetle full), or when player dies.

    Returns: 'beetle_full' | 'ghost' | 'disconnected'
    """
    looted = set()

    while Player.Connected and not Player.IsGhost:
        # ── Pet care ──────────────────────────────────────────────────────────
        pet = _find_pet()
        if pet is not None:
            _check_pet_health(pet)
            _cast_animal_whispering(pet)

        # ── Send pet to kill nearest enemy ────────────────────────────────────
        enemies = [e for e in GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE)
                   if e.Serial not in _skip_serials]
        if enemies:
            nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
            if time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC:
                log("Enemy: %s — sending pet." % nearest.Name, colors['red'])
                _send_kill(nearest.Serial)

        # ── Loot gold from new corpses ────────────────────────────────────────
        corpses = [c for c in scan_nearby_corpses(CORPSE_SCAN_RANGE)
                   if int(c.Serial) not in looted]

        if corpses:
            for corpse in corpses:
                walk_to_corpse(corpse)
                if open_corpse(corpse):
                    for item in list(corpse.Contains or []):
                        if item.ItemID != GOLD_ITEM_ID:
                            continue
                        moved, full = transfer_to_beetle(item, beetle_pack)
                        if moved:
                            log("Transferred %d gold to beetle." % item.Amount, colors['green'])
                        if full:
                            log("Beetle full — exiting dungeon.", colors['yellow'])
                            return 'beetle_full'
                looted.add(int(corpse.Serial))

                # Return to staging position after each corpse
                log("Returning to staging position.", colors['cyan'])
                _walk_to(staging_x, staging_y)
        else:
            Misc.Pause(IDLE_WAIT_MS)

        Misc.Pause(CHECK_INTERVAL)

    if Player.IsGhost:
        return 'ghost'
    return 'disconnected'

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
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
    reason = _kill_loot_loop(beetle_pack, staging_x, staging_y)

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
    mount_beetle(beetle.Serial)
    log("Recalling home...", colors['cyan'])
    recall_home(HOME_RUNEBOOK_NAME, HOME_RUNE_NAME, RECALL_SETTLE_DELAY)

    # ── Unload beetle ─────────────────────────────────────────────────────────
    log("Unloading beetle...", colors['cyan'])
    unload_beetle_to_containers(beetle_pack)

    log("Done.", colors['green'])


main()
