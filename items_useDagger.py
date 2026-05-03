import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.tools import tools
from utilities.items import FindItem
from glossary.colors import colors

dagger = FindItem( tools[ 'dagger' ].itemID, Player.Backpack )

if dagger != None:
    Items.UseItem( dagger )
else:
    Player.HeadMessage( 'You don\'t have a dagger!' )

Misc.Pause( 50 )
