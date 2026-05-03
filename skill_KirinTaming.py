'''
Description: Patrols the Kirin/Unicorn spawn area in Ilshenar,
    roaming between waypoints looking for mobs to tame.
    Waypoints are loaded from waypoints_KirinTaming.json (use util_recordWaypoints.py to create it).
'''

import json
import os

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.enemies import GetEnemies
from utilities.mobiles import GetEmptyMobileList
import config
from System.Collections.Generic import List
from System import Int32

# Body IDs for ki-rin and unicorn (both spawn blue/notoriety 1)
KIRIN_BODY    = 0x0084
UNICORN_BODY  = 0x007A

# ── Configuration ─────────────────────────────────────────────────────────────
# Followers the character normally runs with (combat pets, etc.).
# Purge loop only triggers when followers EXCEED this baseline.
baseFollowers = 1

# Maximum follower slots — purge loop also triggers when at or above this cap.
followerCap = 5
# ──────────────────────────────────────────────────────────────────────────────

# Serials already tamed this session — don't re-tame released animals
alreadyTamedSerials = set()

# Serials confirmed as paragons — skip WaitForProps on repeated scans
paragonSerials = set()

# Serials confirmed as NOT paragons — skip WaitForProps on repeated scans.
# Safe to cache permanently: a mob's paragon status is fixed at spawn and a
# fresh spawn will have a new serial, so stale entries are harmless.
notParagonSerials = set()

# Sentinel returned by TameAnimal for permanent failures (already tamed, no chance, gone).
# Plain False = transient failure (interrupted, path blocked) — retry later.
SKIP = object()

def IsParagon( mobile ):
    '''
    Returns True if the mobile has the [paragon] property.
    Caches both positive and negative results so repeated scans across the
    same kirins/unicorns in range never call WaitForProps more than once per serial.
    '''
    if mobile.Serial in paragonSerials:
        return True
    if mobile.Serial in notParagonSerials:
        return False
    Mobiles.WaitForProps( mobile.Serial, 1000 )
    props = Mobiles.GetPropStringList( mobile.Serial )
    if props is None:
        notParagonSerials.add( mobile.Serial )
        return False
    for prop in props:
        if 'paragon' in prop.lower():
            paragonSerials.add( mobile.Serial )
            return True
    notParagonSerials.add( mobile.Serial )
    return False

def FindParagon():
    '''
    Finds the nearest paragon ki-rin or unicorn within range.
    Scans by body ID because paragons on this shard remain blue (notoriety 1)
    and are invisible to GetEnemies which only returns hostile notorieties.
    Returns the mobile or None.
    '''
    animalFilter = Mobiles.Filter()
    animalFilter.Enabled  = True
    animalFilter.IsGhost  = 0
    animalFilter.RangeMin = 0
    animalFilter.RangeMax = 20
    bodyList = List[Int32]()
    bodyList.Add( Int32( KIRIN_BODY ) )
    bodyList.Add( Int32( UNICORN_BODY ) )
    animalFilter.Bodies = bodyList
    candidates = Mobiles.ApplyFilter( animalFilter )

    nearest = None
    nearestDist = 9999
    for m in candidates:
        if IsParagon( m ):
            dist = Player.DistanceTo( m )
            if dist < nearestDist:
                nearestDist = dist
                nearest = m
    return nearest

def SlotsFull():
    '''Returns True when follower slots are at or above the cap.'''
    return Player.Followers >= followerCap

def PetsAreNear( maxDist = 6 ):
    '''Returns True if all pets are within maxDist tiles of the player.'''
    petFilter = Mobiles.Filter()
    petFilter.Enabled  = True
    petFilter.Friend   = True
    petFilter.RangeMin = 0
    petFilter.RangeMax = maxDist
    nearbyFriends = Mobiles.ApplyFilter( petFilter )
    return len( nearbyFriends ) >= Player.Followers

def AttackParagonWithPets( paragon ):
    '''Backs away and issues all kill against the paragon, then waits for fight to end.'''
    Misc.SendMessage( 'Paragon found — all kill: %s' % paragon.Name, colors[ 'cyan' ] )

    dist = Player.DistanceTo( paragon )
    if dist < 6:
        dx  = Player.Position.X - paragon.Position.X
        dy  = Player.Position.Y - paragon.Position.Y
        mag = max( abs( dx ), abs( dy ) )
        if mag > 0:
            WalkTo( paragon.Position.X + int( dx * 7 / mag ),
                    paragon.Position.Y + int( dy * 7 / mag ) )

    # Wait for pets to catch up before commanding
    Timer.Create( 'petWait', 10000 )
    while Timer.Check( 'petWait' ):
        if Player.Followers <= baseFollowers:
            return
        if PetsAreNear():
            break
        Misc.Pause( 500 )

    fresh = Mobiles.FindBySerial( paragon.Serial )
    if fresh is None:
        return

    Misc.SendMessage( 'Pets ready — all kill!', colors[ 'cyan' ] )
    Player.ChatSay( 690, 'all kill' )
    Target.WaitForTarget( 4000, False )
    Target.TargetExecute( fresh )

    # Cast Invisibility on ourselves while the pets fight
    Spells.CastMagery( 'Invisibility' )
    Target.WaitForTarget( 4000, False )
    Target.TargetExecute( Player.Serial )

    # Wait until the fight resolves before returning to patrol
    while Player.Followers > baseFollowers and not Player.IsGhost:
        if Mobiles.FindBySerial( paragon.Serial ) is None:
            break
        Misc.Pause( 1000 )

waypointsFile = os.path.join( os.path.dirname( __file__ ), 'waypoints_KirinTaming.json' )

def LoadWaypoints():
    if not os.path.exists( waypointsFile ):
        Misc.SendMessage( 'Waypoints file not found: %s' % waypointsFile, colors[ 'red' ] )
        Misc.SendMessage( 'Run util_recordWaypoints.py first to create it.', colors[ 'red' ] )
        return None
    with open( waypointsFile, 'r' ) as f:
        data = json.load( f )
    Misc.SendMessage( 'Loaded %d waypoints.' % len( data ) )
    return data

def FindTameable():
    '''
    Finds the nearest untamed ki-rin or unicorn within range.
    Both spawn blue (notoriety 1) so we filter by body ID, not notoriety.
    Returns the mobile or None.
    '''
    animalFilter = Mobiles.Filter()
    animalFilter.Enabled   = True
    animalFilter.IsGhost   = 0
    animalFilter.RangeMin  = 0
    animalFilter.RangeMax  = 12
    bodyList = List[Int32]()
    bodyList.Add( Int32( KIRIN_BODY ) )
    bodyList.Add( Int32( UNICORN_BODY ) )
    animalFilter.Bodies    = bodyList
    candidates = Mobiles.ApplyFilter( animalFilter )

    # Exclude paragons, already-tamed (notoriety != 1 means owned), and session-tracked serials
    filteredList = GetEmptyMobileList( Mobiles )
    for m in candidates:
        if m.Notoriety == 1 and m.Serial not in alreadyTamedSerials and not IsParagon( m ):
            filteredList.Add( m )

    if len( filteredList ) == 0:
        return None
    if len( filteredList ) == 1:
        return filteredList[ 0 ]
    return Mobiles.Select( filteredList, 'Nearest' )

def MoveToAnimal( animal, maxRange = 2 ):
    '''
    Pathfinds to within maxRange tiles of the animal.
    Returns True if close enough, False if unable to reach.
    '''
    if Player.DistanceTo( animal ) <= maxRange:
        return True

    pos = animal.Position
    reached = WalkTo( pos.X, pos.Y )
    if not reached:
        # PathFinding couldn't get there exactly — check if we're close enough anyway
        return Player.DistanceTo( animal ) <= maxRange + 2
    return Player.DistanceTo( animal ) <= maxRange + 2

def TameAnimal( animal ):
    '''
    Moves close to the animal then attempts to tame it, retrying until
    successful, the animal is gone, or it proves untameable.
    Returns True if tamed successfully, False otherwise.
    '''
    global alreadyTamedSerials

    followersBeforeTame = Player.Followers
    Misc.SendMessage( 'Attempting to tame: %s' % animal.Name, colors[ 'cyan' ] )
    Mobiles.Message( animal, colors[ 'cyan' ], 'Taming...' )

    # Move into range before starting
    if not MoveToAnimal( animal ):
        Misc.SendMessage( 'Cannot reach animal to tame — will retry later', colors[ 'red' ] )
        return False  # transient: may be reachable from another position

    while not Player.IsGhost:
        # Check FIRST: if followers increased since we started, a previous attempt
        # succeeded but the journal poll timed out and missed the message.
        # Return True immediately rather than clearing the journal and retrying.
        if Player.Followers > followersBeforeTame:
            alreadyTamedSerials.add( animal.Serial )
            Misc.SendMessage( 'Tamed (detected via follower count): %s' % animal.Name, colors[ 'cyan' ] )
            Player.ChatSay( 690, 'all follow me' )
            return True

        # Re-fetch so we always have a fresh reference
        current = Mobiles.FindBySerial( animal.Serial )
        if current is None:
            Misc.SendMessage( 'Animal gone before tame attempt', colors[ 'red' ] )
            return SKIP  # permanent: it's gone

        Target.ClearLastandQueue()
        Misc.Pause( config.targetClearDelayMilliseconds )
        Journal.Clear()

        Player.UseSkill( 'Animal Taming' )
        Target.WaitForTarget( 3000, True )
        Target.TargetExecute( current )
        Misc.Pause( config.journalEntryDelayMilliseconds )

        if Journal.Search( 'You must wait a few moments to use another skill.' ):
            Misc.Pause( 2000 )
            continue

        if not Journal.Search( 'Tame which animal?' ):
            # Skill not ready yet or interaction failed — short wait and retry
            Misc.Pause( 1000 )
            continue

        # Tame attempt is in progress — poll journal until it resolves.
        # 60-second window: kirins are high-difficulty and can resist many times.
        import time
        attemptStartTime = time.time()
        tameResolved = False
        while ( time.time() - attemptStartTime ) < 13.0:
            # Follower count is the most reliable success signal — check it first
            if Player.Followers > followersBeforeTame:
                alreadyTamedSerials.add( animal.Serial )
                Misc.SendMessage( 'Tamed: %s' % animal.Name, colors[ 'cyan' ] )
                Mobiles.Message( animal, colors[ 'cyan' ], 'TAMED!' )
                Player.ChatSay( 690, 'all follow me' )
                return True

            freshAnimal = Mobiles.FindBySerial( animal.Serial )
            if freshAnimal is None:
                Misc.SendMessage( 'Animal disappeared during tame attempt', colors[ 'red' ] )
                return SKIP

            # Follow the animal if it has moved out of range
            if Player.DistanceTo( freshAnimal ) > 2:
                MoveToAnimal( freshAnimal )

            if Journal.Search( 'It seems to accept you as master.' ):
                alreadyTamedSerials.add( animal.Serial )
                Misc.SendMessage( 'Tamed: %s' % animal.Name, colors[ 'cyan' ] )
                Mobiles.Message( animal, colors[ 'cyan' ], 'TAMED!' )
                Player.ChatSay( 690, 'all follow me' )
                return True

            if Journal.Search( 'That animal looks tame already.' ):
                Misc.SendMessage( 'Animal already tamed — ignoring %s' % animal.Name, colors[ 'red' ] )
                alreadyTamedSerials.add( animal.Serial )
                Misc.IgnoreObject( animal )
                return SKIP  # permanent

            if ( Journal.Search( 'You have no chance of taming this creature' ) or
                 Journal.Search( 'This animal has had too many owners' ) ):
                tameResolved = True
                return SKIP  # permanent

            if ( Journal.Search( 'You see no animal there to tame.' ) or
                 Journal.Search( 'You\'ve been interrupted.' ) or
                 Journal.Search( 'You do not have a clear path to the animal' ) or
                 Journal.Search( 'You fail to tame the creature.' ) ):
                tameResolved = True
                break  # transient — break inner loop, retry skill

            Misc.Pause( 100 )

        if not tameResolved:
            Misc.SendMessage( 'No journal resolution after 60s — retrying skill', colors[ 'cyan' ] )
        # Loop back to top — follower check will catch a late success before
        # Journal.Clear() wipes the evidence.

def WalkTo( x, y ):
    '''
    Pathfinds to the given coordinates.
    Returns True if destination was reached, False if stuck.
    '''
    route = PathFinding.Route()
    route.X = x
    route.Y = y
    route.DebugMessage = False
    route.StopIfStuck = True
    return PathFinding.Go( route )

def NearestWaypointIndex( waypoints ):
    '''Returns the index of the waypoint closest to the player's current position.'''
    nearest = 0
    nearestDist = 9999
    for i, point in enumerate( waypoints ):
        dist = abs( Player.Position.X - point[0] ) + abs( Player.Position.Y - point[1] )
        if dist < nearestDist:
            nearestDist = dist
            nearest = i
    return nearest, nearestDist

def PatrolLoop():
    '''
    Continuously walks between waypoints looking for Kirins and Unicorns.
    When follower slots are full, hunts for a paragon to use pets against.
    '''
    waypoints = LoadWaypoints()
    if waypoints is None:
        return

    waypointIndex, nearestDist = NearestWaypointIndex( waypoints )

    # PathFinding.Go has a hard range limit (~200 tiles). If the player is further
    # away than that from the entire route, every WalkTo call silently fails and
    # the player stands still forever.  Abort early with a clear message.
    if nearestDist > 150:
        Misc.SendMessage( 'ERROR: Nearest waypoint is %d tiles away (idx %d, pos %d,%d).' % (
            nearestDist, waypointIndex,
            Player.Position.X, Player.Position.Y ), colors[ 'red' ] )
        Misc.SendMessage( 'You are on the wrong map or too far from the spawn. Gate/recall to the kirin area first.', colors[ 'red' ] )
        return

    Misc.SendMessage( 'Starting patrol at waypoint %d (dist %d).' % ( waypointIndex, nearestDist ), colors[ 'cyan' ] )

    # If we're resuming mid-session with pets already out, go straight to purge loop
    if Player.Followers > baseFollowers:
        Misc.SendMessage( 'Starting with %d followers (base %d) — entering purge loop first' % ( Player.Followers, baseFollowers ), colors[ 'cyan' ] )

    while not Player.IsGhost:
        # ── Priority 1: purge excess followers ───────────────────────────────
        if Player.Followers > baseFollowers:
            Misc.SendMessage( '[P1] followers=%d base=%d — scanning for paragon' % ( Player.Followers, baseFollowers ), colors[ 'yellow' ] )
            paragon = FindParagon()
            if paragon != None:
                AttackParagonWithPets( paragon )  # blocks until fight resolves
                waypointIndex, _ = NearestWaypointIndex( waypoints )
                continue
            Misc.SendMessage( '[P1] no paragon found — falling through to walk', colors[ 'yellow' ] )
            # No paragon in scan range yet — fall through to waypoint walking to go find one

        # ── Priority 2: tame any animal in range ─────────────────────────────
        if Player.Followers <= baseFollowers:
            tameable = FindTameable()
            if tameable != None:
                Misc.SendMessage( '[P2] taming: %s serial=%d' % ( tameable.Name, tameable.Serial ), colors[ 'yellow' ] )
                result = TameAnimal( tameable )
                Journal.Clear()
                if result is SKIP:
                    alreadyTamedSerials.add( tameable.Serial )
                    Misc.Pause( 500 )
                    continue
                if result is True:
                    Misc.Pause( 500 )
                    continue
                # False = transient failure — fall through to walk one step
                Misc.Pause( 300 )
            else:
                Misc.SendMessage( '[P2] no tameable in range', colors[ 'yellow' ] )

        # ── Priority 3: walk one waypoint step ───────────────────────────────
        x, y = waypoints[ waypointIndex ]
        dist = abs( Player.Position.X - x ) + abs( Player.Position.Y - y )

        Misc.SendMessage( '[P3] pos=(%d,%d) target=(%d,%d) idx=%d dist=%d' % ( Player.Position.X, Player.Position.Y, x, y, waypointIndex, dist ), colors[ 'yellow' ] )

        if dist > 2:
            WalkTo( x, y )

        waypointIndex = ( waypointIndex + 1 ) % len( waypoints )

        Misc.Pause( 200 )

PatrolLoop()
