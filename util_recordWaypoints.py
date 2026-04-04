'''
Description: Records player waypoints to a JSON file as you walk a route.
    Run this script, walk your patrol loop, then stop the script.
    The saved file can be loaded by skill_KirinTaming.py (or any patrol script).

Usage:
    - Set outputFile to the path where you want waypoints saved.
    - Set recordIntervalTiles to how many tiles you must move before a new
      waypoint is recorded (prevents duplicate points when standing still).
    - Walk your route and stop the script when done.
'''

import json
import os

outputFile = os.path.join( os.path.dirname( __file__ ), 'waypoints_random.json' )
recordIntervalTiles = 5  # minimum tile distance from last recorded point before saving a new one

waypoints = []
lastX = None
lastY = None

Misc.SendMessage( 'Waypoint recorder started. Walk your route and stop the script when done.' )
Misc.SendMessage( 'Saving to: %s' % outputFile )

while not Player.IsGhost:
    x = Player.Position.X
    y = Player.Position.Y

    if lastX is None or abs( x - lastX ) + abs( y - lastY ) >= recordIntervalTiles:
        waypoints.append( [ x, y ] )
        lastX = x
        lastY = y
        with open( outputFile, 'w' ) as f:
            json.dump( waypoints, f, indent=4 )
        Misc.SendMessage( 'Waypoint %d recorded: (%d, %d)' % ( len( waypoints ), x, y ) )

    Misc.Pause( 250 )

# Script was stopped — write the file
if len( waypoints ) > 0:
    with open( outputFile, 'w' ) as f:
        json.dump( waypoints, f, indent=4 )
    Misc.SendMessage( 'Saved %d waypoints to %s' % ( len( waypoints ), outputFile ) )
else:
    Misc.SendMessage( 'No waypoints recorded.' )
