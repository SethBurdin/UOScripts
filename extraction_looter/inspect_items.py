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
    Return True if the item's tooltip shows an artifact rarity line —
    'Lesser Artifact' or higher (Artifact, Greater/Major/Legendary Artifact).

    Plain magic-item tiers (Lesser/Minor/Greater/Major Magic Item) and
    mundane items with extra prop lines (durability, weight, requirements)
    are ignored — counting prop lines looted non-magical gear.

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
    for line in props:
        if 'artifact' in line.lower():
            return True
    return False
