# extraction_looter/extraction_looter.py
# Automated leather and loot extraction script.
#
# Flow:
#   1. Prompt for farm rune name.
#   2. Prompt player to target the pack beetle.
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
from extraction_looter.stealth      import threat_nearby, handle_threat
from extraction_looter.corpse_util  import (scan_nearby_corpses, open_corpse,
                                            skin_corpse, find_skinning_tool,
                                            cut_hides_in_backpack)
from extraction_looter.loot_util    import collect_from_corpse
from extraction_looter.containers_util import transfer_to_beetle, drop_on_ground
from extraction_looter.inspect_items   import is_leather

# ─── Config ───────────────────────────────────────────────────────────────────

# 'leather' — only hides and cut leather
# 'magic'   — only items with magical properties
# 'both'    — leather and magic items
LOOT_MODE = 'both'

# When True: run until the beetle is full, then return home and stop.
# When False: run indefinitely until killed manually.
LOOT_UNTIL_FULL = True

# Set True if a waypoints.json exists in this folder for the farm zone.
# When False the script loots from the recall landing spot.
USE_WAYPOINTS = True

HOME_RUNEBOOK_NAME = 'home'

HOSTILE_RANGE     = 10      # tiles — threat detection radius
THREAT_POLL_MS    = 2000    # ms between hostile re-checks while hiding
THREAT_TIMEOUT_MS = 60000   # ms before aborting due to persistent threat

SCAN_RANGE        = 2       # corpse scan radius (tiles)
IDLE_WAIT_MS      = 2000    # ms to wait between scans when no corpses found

SCISSORS_ID       = 0x0F9F  # scissors for cutting raw hides

# Farm locations shown in the startup prompt (rune names must match the runebook)
FARM_LOCATIONS = [
    'ww',        # Wind Wyrms
    'iceogre',   # Ice Ogre Lords
    'demons',    # Demons
    'ogrelords', # Ogre Lords
    'liches',    # Liches
    'balron',    # Balrons
    'ancient',   # Ancient Wyrms
    'titans',    # Titans
]

_WAYPOINTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'waypoints.json')

_TAG = '[extractor]'

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)

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


def _prompt_beetle():
    """Ask player to target the pack beetle. Returns Mobile or None."""
    log("Target your pack beetle:", colors['cyan'])
    serial = Target.PromptTarget("Click your pack beetle:")
    if not serial:
        log("No beetle selected — aborting.", colors['red'])
        return None
    beetle = Mobiles.FindBySerial(int(serial))
    if beetle is None:
        log("Beetle mobile not found (0x%X) — is it in range?" % int(serial), colors['red'])
        return None
    log("Beetle locked: %s (0x%X)." % (beetle.Name, beetle.Serial), colors['green'])
    return beetle


def _get_beetle_pack(beetle):
    """Open beetle and return its backpack Item, or None."""
    Mobiles.UseMobile(beetle.Serial)
    Misc.Pause(1500)
    pack = beetle.Backpack
    if pack is None:
        log("Beetle backpack not accessible.", colors['red'])
    return pack

# ─── Extract loop ─────────────────────────────────────────────────────────────

def _process_corpses(beetle_pack, tool, scissors):
    """
    Scan, skin, loot, and transfer all nearby corpses.

    Returns:
        beetle_full -- bool  True if a transfer was rejected (beetle pack full)
    """
    corpses = scan_nearby_corpses(SCAN_RANGE)
    if not corpses:
        return False

    beetle_full = False

    for corpse in corpses:
        if beetle_full and LOOT_UNTIL_FULL:
            break

        # Skin first so hides appear on the corpse
        skin_corpse(corpse, tool)

        # Cut any raw hides that landed in the backpack
        if scissors is not None:
            cut_hides_in_backpack(scissors)

        # Open the corpse and collect items per loot mode
        if not open_corpse(corpse):
            log("Could not open corpse 0x%X." % corpse.Serial, colors['yellow'])
            continue

        items = collect_from_corpse(corpse, LOOT_MODE)
        for item in items:
            moved, full = transfer_to_beetle(item, beetle_pack)
            if full:
                beetle_full = True
                if is_leather(item):
                    # Drop leather on the ground; don't leave it behind
                    drop_on_ground(item)
                if LOOT_UNTIL_FULL:
                    log("Beetle full — finishing current corpse then returning home.",
                        colors['yellow'])
                    break

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
    scissors = Items.FindByID(SCISSORS_ID, -1, Player.Backpack.Serial)

    if tool is None:
        log("No skinning knife or dagger in backpack — leather will not be processed.",
            colors['yellow'])
    if scissors is None:
        log("No scissors in backpack — raw hides will not be cut.", colors['yellow'])

    no_corpse_ticks = 0

    while not Player.IsGhost:
        # ── Threat check ─────────────────────────────────────────────────────
        if threat_nearby(HOSTILE_RANGE):
            cleared = handle_threat(beetle.Serial, THREAT_POLL_MS, THREAT_TIMEOUT_MS)
            if not cleared:
                return 'threat_timeout'
            # Refresh tool/scissors after hiding (they should still be in backpack)
            tool     = find_skinning_tool()
            scissors = Items.FindByID(SCISSORS_ID, -1, Player.Backpack.Serial)

        # ── Process corpses ──────────────────────────────────────────────────
        beetle_full = _process_corpses(beetle_pack, tool, scissors)

        if beetle_full and LOOT_UNTIL_FULL:
            return 'beetle_full'

        # ── Idle if no corpses ───────────────────────────────────────────────
        corpses = scan_nearby_corpses(SCAN_RANGE)
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


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    global USE_WAYPOINTS

    # ── Location prompt ───────────────────────────────────────────────────────
    farm_rune = _prompt_farm_location()
    if farm_rune is None:
        return

    log("Target: %s" % farm_rune, colors['cyan'])

    # ── Beetle selection ──────────────────────────────────────────────────────
    beetle = _prompt_beetle()
    if beetle is None:
        return

    # ── Load waypoints ────────────────────────────────────────────────────────
    waypoints = None
    if USE_WAYPOINTS:
        waypoints = load_waypoints(_WAYPOINTS_FILE)
        if waypoints is None:
            log("No waypoints.json — looting from recall spot.", colors['yellow'])
            USE_WAYPOINTS = False

    # ── Travel to farm ────────────────────────────────────────────────────────
    if not recall_to_farm(farm_rune, HOME_RUNEBOOK_NAME):
        log("Failed to recall to farm — stopping.", colors['red'])
        return

    if USE_WAYPOINTS and waypoints:
        start_idx, dist = nearest_waypoint_index(waypoints)
        log("Walking to loot zone (%d waypoints)..." % len(waypoints), colors['cyan'])
        walk_waypoints(waypoints, start_idx)

    # ── Open beetle pack ──────────────────────────────────────────────────────
    beetle_pack = _get_beetle_pack(beetle)
    if beetle_pack is None:
        return

    # ── Extraction loop ───────────────────────────────────────────────────────
    log("Extraction started. LOOT_MODE=%s  LOOT_UNTIL_FULL=%s" % (LOOT_MODE, LOOT_UNTIL_FULL),
        colors['cyan'])

    reason = _extract_loop(beetle, beetle_pack, waypoints)

    if reason == 'ghost':
        log("Player is a ghost — stopping.", colors['red'])
        return

    if reason == 'threat_timeout':
        log("Threat timeout — returning home.", colors['red'])

    # ── Return home ───────────────────────────────────────────────────────────
    if USE_WAYPOINTS and waypoints:
        log("Walking reverse waypoints home...", colors['cyan'])
        # Reverse the list and start from the waypoint nearest to current position
        reversed_wps  = list(reversed(waypoints))
        start_idx, _  = nearest_waypoint_index(reversed_wps)
        walk_waypoints(reversed_wps, start_idx)

    recall_home(HOME_RUNEBOOK_NAME)
    log("Done.", colors['green'])


main()
