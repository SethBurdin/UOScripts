import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.moongates import FindMoongates
if Player.Name == 'Dextin Martin':
    Items.UseItem( 0x4052B274 )
    elif Player.Name == 'Flyintamez':
    Items.UseItem( 0x419880D0 )

Gumps.WaitForGump( 1431013363, 2000 )
Misc.Pause( 100 )
Gumps.SendAction( 1431013363, 6 )

moongates = FindMoongates( Items )
while len( moongates ) == 0:
    Misc.Pause( 20 )
    moongates = FindMoongates( Items )

Items.UseItem( moongates[ 0 ] )
Gumps.WaitForGump( 3716879466, 2000 )
Gumps.SendAction( 3716879466, 1 )
