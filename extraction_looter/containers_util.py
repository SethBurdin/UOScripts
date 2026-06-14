# extraction_looter/containers_util.py
# Container transfer helpers: move items to the beetle pack or drop on the ground.
#
# Functions:
#   transfer_to_beetle(item, beetle_pack)  -> (bool moved, bool beetle_full)
#   drop_on_ground(item)                   -> None

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.colors import colors

MOVE_PAUSE_MS  = 1200   # ms after Items.Move — server needs this; skipping causes silent failures
DROP_PAUSE_MS  = 1000   # ms after Items.MoveOnGround
MAX_RETRIES    = 3       # retry attempts on "You must wait" server rejection

_TAG = '[containers]'


def _log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def transfer_to_beetle(item, beetle_pack):
    """
    Move item to beetle_pack.  Detects beetle-full condition by checking
    whether the item's container serial changed after the move.

    Retries up to MAX_RETRIES times on server-busy rejection.

    Input:
        item        -- Item object to transfer
        beetle_pack -- Item object (beetle's backpack)

    Returns:
        (moved, beetle_full)
          moved       -- True if item landed in beetle_pack
          beetle_full -- True if server rejected the move (pack full / weight)
    """
    for attempt in range(MAX_RETRIES):
        _log('Moving %dx %s (0x%X) → beetle, attempt %d/%d...' % (
            item.Amount, item.Name, item.Serial, attempt + 1, MAX_RETRIES))
        Journal.Clear()
        Items.Move(item, beetle_pack, item.Amount)
        _log('Waiting %dms after Items.Move...' % MOVE_PAUSE_MS)
        Misc.Pause(MOVE_PAUSE_MS)

        if Journal.Search("You must wait to perform another action."):
            _log("Server busy — retry %d/%d." % (attempt + 1, MAX_RETRIES), colors['yellow'])
            Misc.Pause(MOVE_PAUSE_MS)
            continue

        found = Items.FindBySerial(item.Serial)
        if found is None:
            # Item consumed or stacked — treat as success
            return True, False
        if found.Container == beetle_pack.Serial:
            return True, False

        # Item did not move — beetle is full or move was rejected
        _log("Transfer failed (attempt %d) — beetle may be full." % (attempt + 1), colors['yellow'])
        return False, True

    _log("Transfer failed after %d retries." % MAX_RETRIES, colors['red'])
    return False, True


def drop_on_ground(item):
    """
    Drop item at the player's current feet.

    Input:
        item -- Item object
    """
    pos = Player.Position
    _log('Dropping %dx %s (0x%X) on ground at (%d, %d)...' % (
        item.Amount, item.Name, item.Serial, pos.X, pos.Y))
    Items.MoveOnGround(item, item.Amount, pos.X, pos.Y, pos.Z)
    Misc.Pause(DROP_PAUSE_MS)
    _log("Dropped %dx %s on ground." % (item.Amount, item.Name), colors['yellow'])
