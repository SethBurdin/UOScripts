'''
Pirate Hunter Navigator
    Polls player position and calls out compass heading + distance in game chat.

    Sextant coordinates are converted using the same shard-calibrated constants
    as util_gatekeeper.py  (SHARD_X/Y_ORIGIN and SHARD_X/Y_SCALE).

    Coordinate string format: "157o 24'S, 2o 6'W"  (lowercase 'o' for degree)
'''

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import math
import re
from glossary.colors import colors

# ── Shard-calibrated sextant constants (same as util_gatekeeper.py) ─────────────
SHARD_X_ORIGIN = 1323
SHARD_Y_ORIGIN = 1624
SHARD_X_SCALE  = 14.213   # tiles per degree longitude  (E = +x)
SHARD_Y_SCALE  = 11.380   # tiles per degree latitude   (S = +y)

MAP_WIDTH  = 7168
MAP_HEIGHT = 4096


def CoordToTile( coord_str ):
    if not coord_str or coord_str.strip() == 'Nowhere':
        return None
    m = re.match( r"(\d+)o\s+(\d+)'([NS]),\s+(\d+)o\s+(\d+)'([EW])", coord_str.strip() )
    if not m:
        return None
    lat = int( m.group(1) ) + int( m.group(2) ) / 60.0
    lon = int( m.group(4) ) + int( m.group(5) ) / 60.0
    if m.group(3) == 'N':
        lat = -lat
    if m.group(6) == 'W':
        lon = -lon
    x = int( SHARD_X_ORIGIN + SHARD_X_SCALE * lon + 0.5 )
    y = int( SHARD_Y_ORIGIN + SHARD_Y_SCALE * lat + 0.5 )
    return (
        max( 0, min( MAP_WIDTH  - 1, x ) ),
        max( 0, min( MAP_HEIGHT - 1, y ) ),
    )


# ── Target list ──────────────────────────────────────────────────────────────────
TARGETS = [
    { "name": "Dread Pirate O'Shaughnessy",  "xy": CoordToTile("160o 34'N, 5o 53'W") },
    { "name": "Bren (Merchant Sinker)",       "xy": CoordToTile("125o 35'N, 9o 16'W") },
]

ACTIVE_TARGET = 0

POLL_MS       = 6000
ARRIVED_TILES = 30


# ── Navigation helpers ───────────────────────────────────────────────────────────

# 8-point compass indices: N=0, NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7
_COMPASS = [ 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW' ]

def BearingDeg( px, py, tx, ty ):
    return math.degrees( math.atan2( tx - px, -( ty - py ) ) ) % 360

def CompassIdx( bearing_deg ):
    return int( ( bearing_deg + 22.5 ) / 45 ) % 8

def TileDistance( px, py, tx, ty ):
    return int( math.sqrt( ( tx - px ) ** 2 + ( ty - py ) ** 2 ) )


# ── Main ─────────────────────────────────────────────────────────────────────────

def Main():
    if not TARGETS:
        Misc.SendMessage( '[NavComp] No targets defined.', colors['red'] )
        return

    target = TARGETS[ ACTIVE_TARGET ]
    name   = target['name']
    xy     = target['xy']

    if xy is None:
        Misc.SendMessage( '[NavComp] Could not parse coordinates for: %s' % name, colors['red'] )
        return

    tx, ty = xy
    Misc.SendMessage(
        '[NavComp] Hunting %s — tile (%d, %d)' % ( name, tx, ty ),
        colors['orange']
    )

    while True:
        Misc.Pause( POLL_MS )

        px = Player.Position.X
        py = Player.Position.Y

        dist = TileDistance( px, py, tx, ty )

        if dist <= ARRIVED_TILES:
            Player.ChatSay( colors['green'], 'We have reached %s!' % name )
            break

        desired_idx = CompassIdx( BearingDeg( px, py, tx, ty ) )
        Player.ChatSay( colors['yellow'], 'Head %s — %d tiles' % ( _COMPASS[ desired_idx ], dist ) )


Main()
