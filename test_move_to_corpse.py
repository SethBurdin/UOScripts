# test_move_to_corpse.py
# Standalone corpse-finder and walker.
# Scans FIND_RANGE tiles for corpses, walks to the nearest one,
# then confirms we're within LOOT_RANGE before stopping.

if False:
    from razorenhanced_stubs import *

import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors

FIND_RANGE = 12   # scan radius to discover corpses
LOOT_RANGE = 2    # target proximity before we consider ourselves "there"

_TAG = '[corpse_walk]'


def log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def _tile_dist(corpse):
    return math.sqrt(
        (corpse.Position.X - Player.Position.X) ** 2 +
        (corpse.Position.Y - Player.Position.Y) ** 2
    )


def _walk_to(x, y):
    route              = PathFinding.Route()
    route.X            = x
    route.Y            = y
    route.DebugMessage = False
    route.StopIfStuck  = True
    return PathFinding.Go(route)


def scan_corpses(max_range):
    f          = Items.Filter()
    f.Enabled  = True
    f.IsCorpse = 1
    f.RangeMin = 0
    f.RangeMax = max_range
    return list(Items.ApplyFilter(f))


def nearest_corpse(corpses):
    return min(corpses, key=_tile_dist)


def move_to_corpse():
    log("Scanning %d tiles for corpses..." % FIND_RANGE)
    corpses = scan_corpses(FIND_RANGE)

    if not corpses:
        log("No corpses found.", colors['yellow'])
        return False

    log("Found %d corpse(s)." % len(corpses))
    target = nearest_corpse(corpses)
    d = _tile_dist(target)
    log("Nearest: %s (0x%X) at (%d, %d) — %.1f tiles." % (
        target.Name, target.Serial,
        target.Position.X, target.Position.Y, d))

    if d <= LOOT_RANGE:
        log("Already in loot range.", colors['green'])
        return True

    log("Walking...")
    _walk_to(target.Position.X, target.Position.Y)

    d_after = _tile_dist(target)
    if d_after <= LOOT_RANGE:
        log("Arrived — %.1f tiles from corpse." % d_after, colors['green'])
        return True

    log("Stopped %.1f tiles away — may be stuck or blocked." % d_after, colors['yellow'])
    return False


move_to_corpse()
