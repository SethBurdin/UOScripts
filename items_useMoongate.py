import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.moongates import FindMoongates

moongates = FindMoongates( Items )
if len( moongates ) > 0:
    moongate = Items.Select( moongates, 'Nearest' )
    Items.UseItem( moongate )

    Gumps.WaitForGump( 3716879466, 2000 )
    Gumps.SendAction( 3716879466, 1 )
