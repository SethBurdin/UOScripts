# extraction_looter/inspect_items.py
# Item classification helpers for the extraction looter.
#
# Functions:
#   is_leather(item)  -> bool   item is a raw hide or cut leather
#   is_magical(item)  -> bool   item has magic properties (via GetPropStringList)

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.items.cloth import cloth

# Raw hides (0x1079) and cut leather (0x1081)
HIDE_ITEM_IDS = [
    cloth['piles of hides'].itemID,
    cloth['pieces of leather'].itemID,
]

# Dragon scales — treated as leather-type resources
SCALE_ITEM_IDS = [0x26B4, 0x26B5, 0x26B6, 0x26B7, 0x26B8, 0x26B9]

LEATHER_ITEM_IDS = set(HIDE_ITEM_IDS + SCALE_ITEM_IDS)


def is_leather(item):
    """Return True if item is a hide, cut leather, or dragon scale."""
    return item.ItemID in LEATHER_ITEM_IDS


def is_magical(item):
    """
    Return True if item has any magic properties beyond its base name line.
    Uses GetPropStringList — a prop list with more than 1 entry means the
    server sent actual magic stats (matches ELoot behavior).

    Input:
        item  -- Item object

    Returns:
        bool
    """
    Items.SingleClick(item)
    Misc.Pause(500)
    Items.WaitForProps(item, 2000)
    props = Items.GetPropStringList(item.Serial)
    if not props:
        return False
    return len(props) > 1
