import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors

enemy = Target.GetTargetFromList( 'enemy' )
if enemy != None:
    if Target.HasTarget():
        Target.TargetExecute( enemy )
    else:
        Player.Attack( enemy )
        
    Target.SetLast( enemy )
else:
    Player.HeadMessage( colors[ 'red' ], 'No enemies nearby!' )

Misc.Pause( 100 )
