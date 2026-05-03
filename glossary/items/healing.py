import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import myItem, FindItem

healing = {
    'bandage': myItem( 'bandage', 0x0E21, 0x0000, 'healing', 0.1 ),
    'healingPotion': None,
    'greaterHealingPotion': None,
}

def FindBandage( container ):
    '''
    Uses FindItem to look through the player's backpack for a bandage
    '''
    global healing

    return FindItem( healing[ 'bandage' ].itemID, container )
