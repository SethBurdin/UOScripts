import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import myItem

gems = {
    'amber': myItem(
        name = 'amber',
        itemID = 0x0F25,
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'amethyst': myItem(
        name = 'amethyst',
        itemID = 0x0F16,
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'citrine': myItem(
        name = 'citrine',
        itemID = 0x0F15,
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'diamond': myItem(
        name = 'diamond',
        itemID = 0x0F26,
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'emerald': myItem(
        name = 'emerald',
        itemID = 0x0F10,
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'rubies': myItem(
        name = 'rubies',
        itemID = 0x0F13,
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'sapphire': myItem(
        name = 'sapphire',
        itemID = 0x0F11,  # confirmed in-game (standard 0x0F19 is wrong on this shard)
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'star sapphire': myItem(
        name = 'star sapphire',
        itemID = 0x0F0F,  # confirmed in-game (standard 0x0F21 is wrong on this shard)
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    ),
    'tourmaline': myItem(
        name = 'tourmaline',
        itemID = 0x0F18,  # confirmed in-game (standard 0x0F2D is wrong on this shard)
        color = 0x0000,
        category = 'gem',
        weight = 0.1
    )
}
