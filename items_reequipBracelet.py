'''
Description: Repeatedly removes the bracelet and puts it back on.
    Useful for triggering on-equip effects (e.g. mana regeneration resets).
'''

from utilities.items import MoveItem
from glossary.colors import colors
from Scripts import config

while not Player.IsGhost:
    bracelet = Player.GetItemOnLayer( 'Bracelet' )

    if bracelet == None:
        Misc.SendMessage( 'No bracelet equipped', colors[ 'red' ] )
        break

    MoveItem( Items, Misc, bracelet, Player.Backpack )
    Misc.Pause( 4000 )
    Player.EquipItem( bracelet.Serial )
    Misc.Pause( 4000 )
