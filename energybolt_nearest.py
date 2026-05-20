if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.enemies import GetEnemyNotorieties, GetEnemies

CAST_RANGE = 10

enemies = GetEnemies( Mobiles, 0, CAST_RANGE, GetEnemyNotorieties() )

if len( enemies ) == 0:
    Misc.SendMessage( 'No enemies in casting range.' )
else:
    target = enemies[ 0 ] if len( enemies ) == 1 else Mobiles.Select( enemies, 'Nearest' )
    Spells.CastMagery( 'Energy Bolt' )
    Target.WaitForTarget( 2000, False )
    Target.TargetExecute( target )
