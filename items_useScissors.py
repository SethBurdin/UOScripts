import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.tools import tools
from utilities.items import FindItem
from glossary.colors import colors

scissors = FindItem( tools[ 'scissors' ].itemID, Player.Backpack )

if scissors != None:
    Items.UseItem( scissors )
else:
    Player.HeadMessage( 'You don\'t have scissors!' )

Misc.Pause( 50 )
