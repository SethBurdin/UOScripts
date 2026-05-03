import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import myItem

deeds = {
    'bank check': myItem(
        name = 'bank check',
        itemID = 0x14F0,
        color = 0x0034,
        category = 'deed',
        weight = 1 ),
    'power scroll': myItem(
        name = 'power scroll',
        itemID = 0x14F0,
        color = 0x0481,
        category = 'deed',
        weight = 1
    )
}
