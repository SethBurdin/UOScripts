import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import MoveItem

item = Player.GetItemOnLayer( 'LeftHand' )
if item != None:
    MoveItem( Items, Misc, item, Player.Backpack )

item = Player.GetItemOnLayer( 'RightHand' )
if item != None:
    MoveItem( Items, Misc, item, Player.Backpack )
