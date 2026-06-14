# extraction_looter/detect_enemy.py
# Standalone loop: polls for hostile mobiles within HOSTILE_RANGE tiles and
# hides (Invisibility or Hiding skill) + mounts the beetle when a threat appears.
# Skill selection: Magery > 65 -> cast Invisibility; Hiding > 70 -> use Hiding.

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.colors import colors
from extraction_looter.stealth import threat_nearby, handle_threat

HOSTILE_RANGE     = 12      # tiles — matches detect_enemy intent (project.md: 12)
POLL_MS           = 1000    # ms between threat checks when clear
THREAT_POLL_MS    = 2000    # ms between re-checks while hiding
THREAT_TIMEOUT_MS = 120000  # ms before giving up on a persistent threat

PACK_BEETLE_BODY  = 0x0317
BEETLE_SCAN_RANGE = 10

_TAG = '[detect_enemy]'


def _log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def _find_beetle_serial():
    """
    Scan for a pack beetle and return its serial, or None.
    Body-ID match first; falls back to any non-human with a backpack.
    """
    filt          = Mobiles.Filter()
    filt.RangeMax = BEETLE_SCAN_RANGE
    filt.IsHuman  = False

    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial:
            continue
        if mob.Body == PACK_BEETLE_BODY and mob.Backpack is not None:
            _log("Beetle found: %s (0x%X)." % (mob.Name, mob.Serial), colors['green'])
            return mob.Serial

    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial:
            continue
        if mob.Backpack is not None:
            _log("Pack animal found (fallback): %s (0x%X)." % (mob.Name, mob.Serial),
                 colors['green'])
            return mob.Serial

    _log("No pack beetle found — will hide without mounting.", colors['yellow'])
    return None


def main():
    beetle_serial = _find_beetle_serial()

    _log("Monitoring for hostiles within %d tiles. Press Stop to exit." % HOSTILE_RANGE,
         colors['cyan'])

    while not Player.IsGhost:
        if threat_nearby(HOSTILE_RANGE):
            handle_threat(beetle_serial, THREAT_POLL_MS, THREAT_TIMEOUT_MS)
        else:
            Misc.Pause(POLL_MS)

    _log("Player is a ghost — stopping.", colors['red'])


main()
