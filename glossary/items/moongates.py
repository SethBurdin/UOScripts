import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import myItem
from System.Collections.Generic import List
from System import Int32

moongates = {
    'blue moongate': myItem( 'blue moongate', 0x0F6C, 0x0000, 'moongate', None )
}

def FindMoongates( Items ):
    '''
    Finds a moongate that the player can use
    '''
    global moongates

    moongateIDs = [ moongates[ moongate ].itemID for moongate in moongates ]

    moongateFilter = Items.Filter()
    moongateFilter.OnGround = 1
    moongateFilter.RangeMin = 0
    moongateFilter.RangeMax = 1
    moongateFilter.Movable = False
    moongateFilter.Graphics = List[Int32]( moongateIDs )

    return Items.ApplyFilter( moongateFilter )
