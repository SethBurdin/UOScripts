# extraction_looter/extraction_looter.py
# Automated leather and loot extraction script.
#
# Flow:
#   1. Prompt for farm rune name.
#   2. Auto-detect the pack beetle (body-ID scan, then any non-human with a backpack).
#   3. Recall to farm location via runebook.
#   4. Optionally walk waypoints to the loot zone.
#   5. Loop: detect threats, find corpses, skin, loot, transfer to beetle.
#      - If beetle full: drop leather on ground; return home when zone is clear.
#   6. Walk waypoints in reverse back to the recall point.
#   7. Recall home.

if False:
    from razorenhanced_stubs import *

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.colors import colors
from extraction_looter.nav          import (load_waypoints, walk_waypoints,
                                            nearest_waypoint_index,
                                            recall_to_farm, recall_home)
from extraction_looter.stealth      import threat_nearby, handle_threat, hide_and_mount, mount_beetle
from extraction_looter.corpse_util  import (scan_nearby_corpses, nearest_corpse,
                                            walk_to_corpse, open_corpse,
                                            skin_corpse, find_skinning_tool,
                                            find_scissors, cut_hides_in_backpack)
from extraction_looter.loot_util    import collect_from_corpse
from extraction_looter.containers_util import transfer_to_beetle, drop_on_ground
from extraction_looter.dropoff_util    import unload_beetle_to_containers
from extraction_looter.inspect_items   import LEATHER_ITEM_IDS
# ─── Config ───────────────────────────────────────────────────────────────────

# 'leather' — only hides and cut leather
# 'magic'   — only items with magical properties
# 'both'    — leather and magic items
LOOT_MODE = 'both'

# When True: run until the beetle is full, then return home and stop.
# When False: run indefinitely until killed manually.
LOOT_UNTIL_FULL = True

HOME_RUNEBOOK_NAME = 'home'        # label on the runebook item in backpack
HOME_RUNE_NAME     = 'new home'    # name of the home rune inside that runebook
FARM_RUNEBOOK_NAME = 'home'        # label of the backpack runebook that holds farm runes

HOSTILE_RANGE     = 10      # tiles — threat detection radius (overridden per-location below)
THREAT_POLL_MS    = 2000    # ms between hostile re-checks while hiding
THREAT_TIMEOUT_MS = 60000   # ms before aborting due to persistent threat

CORPSE_FIND_RANGE = 12      # scan radius to discover corpses and walk to them
SCAN_RANGE        = 2       # proximity required to open/loot a corpse
IDLE_WAIT_MS      = 2000    # ms to wait between scans when no corpses found

PACK_BEETLE_BODY  = 0x0317  # confirmed body ID for this shard's pack beetle
BEETLE_SCAN_RANGE = 10      # tile radius for auto-detect

# Farm locations shown in the startup prompt (rune names must match the runebook)
FARM_LOCATIONS = [
    'ww',             # Wind Wyrms
    'iceogre',        # Ice Ogre Lords
    'demons',         # Demons
    'ogrelords',      # Ogre Lords
    'liches',         # Liches
    'balron',         # Balrons
    'ancient',        # Ancient Wyrms
    'titans',         # Titans
    'greater dragon', # Greater Dragons
]

# Per-location hostile range overrides (tiles). Falls back to HOSTILE_RANGE if absent.
LOCATION_HOSTILE_RANGE = {
    'greater dragon': 7,
}

# Per-location body ID filters for threat detection. None means any hostile mob.
LOCATION_THREAT_BODY_IDS = {
    'greater dragon': [0x000C, 0x003B],
}

# Per-location flag: stay mounted between corpses; dismount only to actively loot.
LOCATION_STAY_MOUNTED = {
    'greater dragon': True,
}

THREAT_BODY_IDS = None   # set at runtime by main() after farm location is chosen
STAY_MOUNTED    = False  # set at runtime by main() after farm location is chosen

_WAYPOINTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'waypoints')

_TAG = '[extractor]'

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def _party_dropoff_requested():
    """Return True if any recent journal entry contains 'dropoff' (party command)."""
    return Journal.Search('dropoff')

# ─── Startup helpers ──────────────────────────────────────────────────────────

def _prompt_farm_location():
    """Show location list, wait up to 30s for the player to say a number."""
    log("Farm location — say the number:", colors['cyan'])
    for i, loc in enumerate(FARM_LOCATIONS):
        log("  %d) %s" % (i + 1, loc), colors['cyan'])
    Misc.Pause(600)
    Journal.Clear()
    Misc.Pause(200)
    Journal.Clear()

    deadline = time.time() + 30
    while time.time() < deadline:
        for i, loc in enumerate(FARM_LOCATIONS):
            if Journal.SearchByName(str(i + 1), Player.Name):
                Journal.Clear()
                return loc
        Misc.Pause(200)

    log("No location selected (30s timeout).", colors['red'])
    return None


def _dismount():
    """Dismount the player if currently mounted. No-op if already on foot."""
    if Player.Mount is not None:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)


def _find_beetle():
    """
    Auto-detect the pack beetle. Dismounts first so the beetle appears in the
    mobile list, then returns it. Player is left dismounted — ready to loot.

      1. Body-ID scan for PACK_BEETLE_BODY (0x0317).
      2. Fallback: any nearby non-human mobile with a backpack.

    Returns Mobile or None.
    """
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
            log("Pack animal found (fallback): %s (0x%X)." % (mob.Name, mob.Serial),
                colors['green'])
            return mob

    log("No pack animal detected within %d tiles." % BEETLE_SCAN_RANGE, colors['red'])
    return None



def _get_beetle_pack(beetle):
    """
    Open the beetle's backpack and return the pack Item.
    Player must be dismounted before calling (beetle is not in mobile list when mounted).
    Uses Items.UseItem on the pack directly — no Mobiles.UseMobile needed.
    """
    pack = beetle.Backpack
    if pack is None:
        log("Beetle has no accessible backpack.", colors['red'])
        return None
    Items.UseItem(pack)
    Items.WaitForContents(pack.Serial, 3000)
    Misc.Pause(600)
    return pack

# ─── Extract loop ─────────────────────────────────────────────────────────────

RAW_HIDE_ID    = 0x1079   # raw hides — need scissors before transferring
CUT_LEATHER_ID = 0x1081   # pieces of leather produced after cutting raw hides


def _process_corpses(beetle_pack, beetle_serial, tool, scissors, looted):
    """
    Scan, skin, loot, and transfer all nearby corpses.

    Leather flow: corpse → player backpack → cut with scissors → beetle
    Magic item flow: corpse → beetle directly

    looted: set of int serials already processed — updated in place, skipped on scan.

    Returns:
        beetle_full -- bool  True if a transfer was rejected (beetle pack full)
    """
    corpses = [c for c in scan_nearby_corpses(CORPSE_FIND_RANGE)
               if int(c.Serial) not in looted]
    if not corpses:
        return False

    beetle_full = False

    for corpse in corpses:
        if beetle_full and LOOT_UNTIL_FULL:
            break

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            return beetle_full

        walk_to_corpse(corpse)

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            return beetle_full

        # Dismount only when we're about to actively loot
        if STAY_MOUNTED:
            _dismount()

        # Skin first so hides appear on the corpse
        skin_corpse(corpse, tool)
        Misc.Pause(800)  # extra buffer so action cooldown clears before opening

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            return beetle_full  # handle_threat will remount

        # Open corpse and collect items per loot mode
        if not open_corpse(corpse):
            log("Could not open corpse 0x%X." % corpse.Serial, colors['yellow'])
            looted.add(int(corpse.Serial))
            if STAY_MOUNTED:
                mount_beetle(beetle_serial)
            continue

        items = collect_from_corpse(corpse, LOOT_MODE)

        # Stage 1 — only raw hides need cutting; everything else goes straight to beetle
        for item in items:
            if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
                return beetle_full
            if item.ItemID == RAW_HIDE_ID:
                Journal.Clear()
                Items.Move(item, Player.Backpack, item.Amount)
                Misc.Pause(1200)
                if Journal.Search("You must wait to perform another action."):
                    log("Server busy on hide move — action delay too short.", colors['yellow'])
                    Misc.Pause(900)
            else:
                moved, full = transfer_to_beetle(item, beetle_pack)
                if full:
                    beetle_full = True
                    if LOOT_UNTIL_FULL:
                        break

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            return beetle_full

        # Stage 2 — cut all raw hides now in the backpack
        if scissors is not None:
            cut_hides_in_backpack(scissors)

        # Stage 3 — transfer cut leather from backpack to beetle
        leather = Items.FindByID(CUT_LEATHER_ID, -1, Player.Backpack.Serial)
        while leather is not None:
            if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
                return beetle_full
            moved, full = transfer_to_beetle(leather, beetle_pack)
            if full:
                beetle_full = True
                drop_on_ground(leather)
                if LOOT_UNTIL_FULL:
                    log("Beetle full — returning home.", colors['yellow'])
                    break
            leather = Items.FindByID(CUT_LEATHER_ID, -1, Player.Backpack.Serial)

        looted.add(int(corpse.Serial))
        if STAY_MOUNTED:
            mount_beetle(beetle_serial)

    return beetle_full


def _extract_loop(beetle, beetle_pack, waypoints):
    """
    Main extraction loop. Runs until:
      - beetle is full (if LOOT_UNTIL_FULL), or
      - a threat times out, or
      - Player.IsGhost

    Returns:
        'beetle_full' | 'threat_timeout' | 'ghost'
    """
    tool     = find_skinning_tool()
    scissors = find_scissors()

    if tool is None:
        log("No skinning knife or dagger in backpack — leather will not be processed.",
            colors['yellow'])
    if scissors is None:
        log("No scissors in backpack — raw hides will not be cut before transfer.",
            colors['yellow'])

    no_corpse_ticks = 0
    looted          = set()

    while not Player.IsGhost:
        # ── Party dropoff command ─────────────────────────────────────────────
        if _party_dropoff_requested():
            log("Party requested dropoff — returning home.", colors['yellow'])
            Journal.Clear()
            return 'party_dropoff'

        # ── Threat check ─────────────────────────────────────────────────────
        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            cleared = handle_threat(beetle.Serial, THREAT_POLL_MS, THREAT_TIMEOUT_MS, THREAT_BODY_IDS)
            if not cleared:
                return 'threat_timeout'
            if not STAY_MOUNTED:
                _dismount()
            tool     = find_skinning_tool()
            scissors = find_scissors()

        # ── Process corpses ──────────────────────────────────────────────────
        beetle_full = _process_corpses(beetle_pack, beetle.Serial, tool, scissors, looted)

        if beetle_full and LOOT_UNTIL_FULL:
            return 'beetle_full'

        # ── Idle if no corpses ───────────────────────────────────────────────
        corpses = [c for c in scan_nearby_corpses(CORPSE_FIND_RANGE)
                   if int(c.Serial) not in looted]
        if not corpses:
            no_corpse_ticks += 1
            if LOOT_UNTIL_FULL and no_corpse_ticks >= 3:
                log("No corpses found after 3 passes — zone clear, returning home.",
                    colors['cyan'])
                return 'beetle_full'   # treat clear zone as done
            Misc.Pause(IDLE_WAIT_MS)
        else:
            no_corpse_ticks = 0

    return 'ghost'


# ─── Manual loot loop ─────────────────────────────────────────────────────────

def _manual_loot_loop(beetle, beetle_pack):
    """
    Scan nearby corpses and move all contents directly to the beetle pack.
    Hides and mounts on threat; dismounts when clear to resume looting.
    No filtering, no skinning — grabs everything. Runs until stopped or ghost.
    """
    log("Manual loot mode active. Press Stop to exit.", colors['cyan'])
    looted     = set()   # int serials — avoids IronPython Int32/int hash mismatch
    area_clear = False   # True once we've hidden+mounted after clearing an area

    while not Player.IsGhost:
        # ── Party dropoff command ─────────────────────────────────────────────
        if _party_dropoff_requested():
            log("Party requested dropoff — returning home.", colors['yellow'])
            Journal.Clear()
            return 'party_dropoff'

        # ── Threat check ─────────────────────────────────────────────────────
        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            area_clear = False
            cleared = handle_threat(beetle.Serial, THREAT_POLL_MS, THREAT_TIMEOUT_MS, THREAT_BODY_IDS)
            if not cleared:
                log("Threat timeout — stopping.", colors['red'])
                return None
            _dismount()
            continue

        # ── Loot corpses ─────────────────────────────────────────────────────
        corpses = [c for c in scan_nearby_corpses(CORPSE_FIND_RANGE)
                   if int(c.Serial) not in looted]
        if not corpses:
            if not area_clear:
                hide_and_mount(beetle.Serial)
                area_clear = True
            Misc.Pause(IDLE_WAIT_MS)
            continue

        area_clear = False
        _dismount()   # only dismount when there are corpses to loot

        for corpse in corpses:
            if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
                break
            walk_to_corpse(corpse)
            if not open_corpse(corpse):
                log("Could not open corpse 0x%X." % corpse.Serial, colors['yellow'])
                looted.add(int(corpse.Serial))
                continue

            contents = list(corpse.Contains) if corpse.Contains else []
            if not contents:
                looted.add(int(corpse.Serial))
                continue

            threat_interrupted = False
            for item in contents:
                if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
                    threat_interrupted = True
                    break
                _, full = transfer_to_beetle(item, beetle_pack)
                if full:
                    log("Beetle full — stopping manual loot.", colors['yellow'])
                    return

            if not threat_interrupted:
                looted.add(int(corpse.Serial))

    log("Player is a ghost — stopping.", colors['red'])
    return None


def _skinning_loop(beetle, beetle_pack):
    """
    Skin each nearby corpse and transfer only leather/scales to the beetle.
    No magic item checking — fast, ID-only filtering.
    """
    log("Skinning mode active. Press Stop to exit.", colors['cyan'])
    tool     = find_skinning_tool()
    scissors = find_scissors()
    if tool is None:
        log("No skinning knife or dagger — skins will not be collected.", colors['yellow'])

    looted     = set()
    area_clear = False

    while not Player.IsGhost:
        # ── Party dropoff command ─────────────────────────────────────────────
        if _party_dropoff_requested():
            log("Party requested dropoff — returning home.", colors['yellow'])
            Journal.Clear()
            return

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            area_clear = False
            cleared = handle_threat(beetle.Serial, THREAT_POLL_MS, THREAT_TIMEOUT_MS, THREAT_BODY_IDS)
            if not cleared:
                log("Threat timeout — stopping.", colors['red'])
                return
            _dismount()
            tool     = find_skinning_tool()
            scissors = find_scissors()
            continue

        corpses = [c for c in scan_nearby_corpses(CORPSE_FIND_RANGE)
                   if int(c.Serial) not in looted]
        if not corpses:
            if not area_clear:
                hide_and_mount(beetle.Serial)
                area_clear = True
            Misc.Pause(IDLE_WAIT_MS)
            continue

        area_clear = False
        _dismount()

        corpse = nearest_corpse(corpses)
        walk_to_corpse(corpse)

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            log("Threat after walk — aborting corpse, handling threat.", colors['yellow'])
            continue

        skin_corpse(corpse, tool)
        Misc.Pause(800)  # extra buffer so action cooldown clears before opening

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            log("Threat after skin — aborting corpse, handling threat.", colors['yellow'])
            continue

        if not open_corpse(corpse):
            looted.add(int(corpse.Serial))
            continue

        Misc.Pause(500)  # clear action timer from open_corpse before first item move

        contents = list(corpse.Contains) if corpse.Contains else []
        if not contents:
            looted.add(int(corpse.Serial))
            continue

        # Stage 1 — raw hides go to backpack for cutting; scales/cut leather straight to beetle
        log("Stage 1: moving leather items from corpse to backpack/beetle...", colors['cyan'])
        threat_interrupted = False
        for item in list(contents):
            if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
                log("Threat during stage 1 — aborting loot.", colors['yellow'])
                threat_interrupted = True
                break
            if item.ItemID not in LEATHER_ITEM_IDS:
                continue
            if item.ItemID == RAW_HIDE_ID:
                log("Moving %dx raw hide (0x%X) → backpack..." % (item.Amount, item.Serial))
                if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
                    log("Threat during hide move — aborting.", colors['yellow'])
                    threat_interrupted = True
                    break
                Journal.Clear()
                Items.Move(item, Player.Backpack, item.Amount)
                Misc.Pause(1200)
                if Journal.Search("You must wait to perform another action."):
                    log("Action timer still active — waiting before retry.", colors['yellow'])
                    Misc.Pause(1500)
                    Journal.Clear()
                    Items.Move(item, Player.Backpack, item.Amount)
                    Misc.Pause(1200)
            else:
                log("Moving %dx %s (0x%X) → beetle..." % (item.Amount, item.Name, item.Serial))
                _, full = transfer_to_beetle(item, beetle_pack)
                if full:
                    log("Beetle full — stopping.", colors['yellow'])
                    return

        if threat_interrupted:
            continue

        # Stage 2 — cut all raw hides now in the backpack
        log("Stage 2: cutting raw hides in backpack...", colors['cyan'])
        if scissors is not None:
            cut_hides_in_backpack(scissors)
        else:
            log("No scissors — skipping cut.", colors['yellow'])

        if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
            log("Threat after stage 2 — deferring beetle transfer.", colors['yellow'])
            continue

        # Stage 3 — transfer cut leather from backpack to beetle
        log("Stage 3: transferring cut leather to beetle...", colors['cyan'])
        leather = Items.FindByID(CUT_LEATHER_ID, -1, Player.Backpack.Serial)
        while leather is not None:
            if threat_nearby(HOSTILE_RANGE, THREAT_BODY_IDS):
                log("Threat during stage 3 — deferring remaining leather.", colors['yellow'])
                break
            _, full = transfer_to_beetle(leather, beetle_pack)
            if full:
                log("Beetle full — stopping.", colors['yellow'])
                return
            leather = Items.FindByID(CUT_LEATHER_ID, -1, Player.Backpack.Serial)

        looted.add(int(corpse.Serial))

    log("Player is a ghost — stopping.", colors['red'])


def _prompt_mode():
    """Ask the player to choose a mode. Returns 'extract', 'manual', or 'skinning'."""
    log("Mode — say the number:", colors['cyan'])
    log("  1) Extract   (recall + full loop)", colors['cyan'])
    log("  2) Manual    (loot all → beetle, here)", colors['cyan'])
    log("  3) Skinning  (leather/scales only, here)", colors['cyan'])
    Misc.Pause(400)
    Journal.Clear()

    deadline = time.time() + 30
    while time.time() < deadline:
        if Journal.SearchByName('1', Player.Name):
            Journal.Clear()
            return 'extract'
        if Journal.SearchByName('2', Player.Name):
            Journal.Clear()
            return 'manual'
        if Journal.SearchByName('3', Player.Name):
            Journal.Clear()
            return 'skinning'
        Misc.Pause(200)

    log("No mode selected (30s timeout).", colors['red'])
    return None


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    global HOSTILE_RANGE, THREAT_BODY_IDS, STAY_MOUNTED

    # ── Mode prompt ───────────────────────────────────────────────────────────
    mode = _prompt_mode()
    if mode is None:
        return

    # ── Beetle detection (shared) ─────────────────────────────────────────────
    beetle = _find_beetle()
    if beetle is None:
        return

    beetle_pack = _get_beetle_pack(beetle)
    if beetle_pack is None:
        return

    # ── Manual / skinning modes ───────────────────────────────────────────────
    if mode == 'manual':
        reason = _manual_loot_loop(beetle, beetle_pack)
        if reason == 'party_dropoff':
            recall_home(HOME_RUNEBOOK_NAME, HOME_RUNE_NAME)
            unload_beetle_to_containers(beetle_pack)
        return

    if mode == 'skinning':
        farm_rune = _prompt_farm_location()
        if farm_rune is None:
            return
        HOSTILE_RANGE    = LOCATION_HOSTILE_RANGE.get(farm_rune, HOSTILE_RANGE)
        THREAT_BODY_IDS  = LOCATION_THREAT_BODY_IDS.get(farm_rune, None)
        STAY_MOUNTED     = LOCATION_STAY_MOUNTED.get(farm_rune, False)
        mount_beetle(beetle.Serial)
        if not recall_to_farm(farm_rune, FARM_RUNEBOOK_NAME):
            log("Failed to recall to farm — stopping.", colors['red'])
            return
        _skinning_loop(beetle, beetle_pack)
        recall_home(HOME_RUNEBOOK_NAME, HOME_RUNE_NAME)
        unload_beetle_to_containers(beetle_pack)
        return

    # ── Extract mode ──────────────────────────────────────────────────────────
    farm_rune = _prompt_farm_location()
    if farm_rune is None:
        return

    HOSTILE_RANGE   = LOCATION_HOSTILE_RANGE.get(farm_rune, HOSTILE_RANGE)
    THREAT_BODY_IDS = LOCATION_THREAT_BODY_IDS.get(farm_rune, None)
    STAY_MOUNTED    = LOCATION_STAY_MOUNTED.get(farm_rune, False)
    log("Target: %s  (hostile range: %d tiles)." % (farm_rune, HOSTILE_RANGE), colors['cyan'])

    # ── Recall to farm ────────────────────────────────────────────────────────
    mount_beetle(beetle.Serial)
    if not recall_to_farm(farm_rune, FARM_RUNEBOOK_NAME):
        log("Failed to recall to farm — stopping.", colors['red'])
        return

    # ── Walk waypoints to loot zone ───────────────────────────────────────────
    waypoints_file = os.path.join(_WAYPOINTS_DIR, 'waypoints_%s.json' % farm_rune)
    waypoints = load_waypoints(waypoints_file) if os.path.exists(waypoints_file) else None
    if waypoints is None:
        log("No waypoints_%s.json — looting from recall spot." % farm_rune, colors['cyan'])

    if waypoints:
        start_idx, dist = nearest_waypoint_index(waypoints)
        log("Walking to loot zone (%d waypoints)..." % len(waypoints), colors['cyan'])
        walk_waypoints(waypoints, start_idx)

    if not STAY_MOUNTED:
        _dismount()

    # ── Extraction loop ───────────────────────────────────────────────────────
    log("Extraction started. LOOT_MODE=%s  LOOT_UNTIL_FULL=%s" % (LOOT_MODE, LOOT_UNTIL_FULL),
        colors['cyan'])

    reason = _extract_loop(beetle, beetle_pack, waypoints)

    if reason == 'ghost':
        log("Player is a ghost — stopping.", colors['red'])
        return

    if reason == 'threat_timeout':
        log("Threat timeout — returning home.", colors['red'])

    # ── Return home via Home runebook ─────────────────────────────────────────
    if waypoints:
        log("Walking reverse waypoints back...", colors['cyan'])
        reversed_wps = list(reversed(waypoints))
        start_idx, _ = nearest_waypoint_index(reversed_wps)
        walk_waypoints(reversed_wps, start_idx)

    recall_home(HOME_RUNEBOOK_NAME, HOME_RUNE_NAME)
    unload_beetle_to_containers(beetle_pack)
    log("Done.", colors['green'])


main()
