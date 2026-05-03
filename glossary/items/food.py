import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import myItem

food = {
    'dragon fruit': myItem(
        name = 'dragon fruit',
        itemID = 0x0C65,
        color = 0x0494,
        category = 'food',
        weight = 1
    ),
    'muffins': myItem(
        name = 'muffins',
        itemID = 0x09EB,
        color = 0x0000,
        category = 'food',
        weight = 1
    )
}
