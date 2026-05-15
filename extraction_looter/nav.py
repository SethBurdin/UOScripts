# extraction_looter/nav.py
# Navigation helpers: runebook recall and waypoint walking.
#
# Functions:
#   recall_to_farm(farm_rune, home_runebook_name, settle_delay)  -> bool
#   recall_home(home_runebook_name, settle_delay)                -> bool
#   load_waypoints(path)                                         -> list or None
#   nearest_waypoint_index(waypoints)                            -> (int, int)
#   walk_waypoints(waypoints, start_index)                       -> None

if False:
    from razorenhanced_stubs import *

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.colors import colors
from glossary.runebook_handler import find_runebook_by_label, travel_to_named_rune, travel_to_runebook

MAX_WAYPOINT_DISTANCE = 150   # abort if nearest waypoint is farther than this

_TAG = '[nav]'


def _log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def _walk_to(x, y):
    """
    Pathfind to (x, y) using PathFinding.Go.
    Returns True if destination was reached, False if stuck.
    """
    route              = PathFinding.Route()
    route.X            = x
    route.Y            = y
    route.DebugMessage = False
    route.StopIfStuck  = True
    return PathFinding.Go(route)


def load_waypoints(path):
    """
    Load a [[x,y], ...] waypoints JSON file.

    Input:
        path -- absolute file path

    Returns:
        list of [x, y] pairs, or None on failure
    """
    if not os.path.exists(path):
        _log("Waypoints file not found: %s" % path, colors['red'])
        return None
    with open(path, 'r') as f:
        data = json.load(f)
    _log("Loaded %d waypoints from %s." % (len(data), os.path.basename(path)))
    return data


def nearest_waypoint_index(waypoints):
    """
    Return the index and distance of the waypoint closest to the player.

    Input:
        waypoints -- list of [x, y]

    Returns:
        (index, distance)  both int
    """
    nearest      = 0
    nearest_dist = 9999
    for i, point in enumerate(waypoints):
        dist = abs(Player.Position.X - point[0]) + abs(Player.Position.Y - point[1])
        if dist < nearest_dist:
            nearest_dist = dist
            nearest      = i
    return nearest, nearest_dist


def walk_waypoints(waypoints, start_index=None):
    """
    Walk every waypoint in waypoints starting from start_index (forward order).
    If start_index is None, find the nearest waypoint first.

    PathFinding.Go has a hard range limit (~200 tiles). If the nearest waypoint
    is more than MAX_WAYPOINT_DISTANCE tiles away the function aborts early.

    Input:
        waypoints   -- list of [x, y]
        start_index -- int or None
    """
    if start_index is None:
        start_index, dist = nearest_waypoint_index(waypoints)
        if dist > MAX_WAYPOINT_DISTANCE:
            _log("Nearest waypoint is %d tiles away — too far, aborting walk." % dist, colors['red'])
            return

    _log("Walking %d waypoints (starting at index %d)." % (len(waypoints), start_index))
    for i in range(start_index, len(waypoints)):
        x, y = waypoints[i]
        if not _walk_to(x, y):
            _log("Stuck at waypoint %d (%d, %d) — continuing." % (i, x, y), colors['yellow'])


def recall_to_farm(farm_rune, home_runebook_name, settle_delay=2000):
    """
    Find the home runebook and recall to the named farm rune.

    Input:
        farm_rune          -- str, rune name in the runebook
        home_runebook_name -- str, label on the runebook item
        settle_delay       -- int, ms to wait after landing

    Returns:
        bool  True on success
    """
    rb = find_runebook_by_label(home_runebook_name)
    if rb is None:
        _log("Runebook '%s' not found in backpack." % home_runebook_name, colors['red'])
        return False
    _log("Recalling to '%s'..." % farm_rune)
    return travel_to_named_rune(rb, farm_rune, settle_delay)


def recall_home(home_runebook_name, settle_delay=2000):
    """
    Find the home runebook and recall to its default rune.

    Input:
        home_runebook_name -- str, label on the runebook item
        settle_delay       -- int, ms to wait after landing

    Returns:
        bool  True on success
    """
    rb = find_runebook_by_label(home_runebook_name)
    if rb is None:
        _log("Runebook '%s' not found in backpack." % home_runebook_name, colors['red'])
        return False
    _log("Recalling home...")
    return travel_to_runebook(rb, settle_delay)
