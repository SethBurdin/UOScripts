# extraction_looter/loot_util.py
# Collect lootable items from an open corpse based on the configured loot mode.
#
# Functions:
#   collect_from_corpse(corpse, mode)  -> list[Item]
#     mode: 'leather' | 'magic' | 'both'

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.colors import colors
from extraction_looter.inspect_items import is_leather, is_magical

_TAG = '[loot]'


def _log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def collect_from_corpse(corpse, mode):
    """
    Iterate corpse.Contains and return all items that match the loot mode.
    The corpse must already be open (open_corpse called) before this is called.

    Input:
        corpse -- Item object (already opened)
        mode   -- str: 'leather', 'magic', or 'both'

    Returns:
        list of Item objects to transfer
    """
    contents = list(corpse.Contains) if corpse.Contains else []
    if not contents:
        _log("Corpse 0x%X is empty." % corpse.Serial, colors['yellow'])
        return []

    result = []
    for item in contents:
        want_leather = mode in ('leather', 'both') and is_leather(item)
        want_magic   = mode in ('magic',   'both') and not is_leather(item) and is_magical(item)
        if want_leather or want_magic:
            tag = 'leather' if want_leather else 'magic'
            _log("  [%s] %s (0x%04X) x%d" % (tag, item.Name, item.ItemID, item.Amount))
            result.append(item)

    return result
