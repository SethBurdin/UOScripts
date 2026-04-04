'''
Description: Patrols a recorded waypoint route, taming animals along the way.
    Loads waypoints from waypoints_routes.json (active route).
    Tames any skill-appropriate animal found while patrolling.
    When followers > baseFollowers, hunts for a paragon to purge pets against before taming more.

Usage:
    - Set playerAttacksMobs = True  to have the PLAYER directly attack mobs to clear them.
    - Set playerAttacksMobs = False to use ALL KILL (pets attack the paragon).
    - Change the active route in waypoints_routes.json to switch patrol areas.
'''

import json
import os
import time

from Scripts.glossary import tameables
# Razor Enhanced caches module objects across script runs — re-execute from disk
# so that all helper functions (including GetBlueSpawningBodyIDsForPlayerSkill) are current.
try:
    _tameables_path = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), 'glossary', 'tameables.py' )
    exec( open( _tameables_path ).read(), tameables.__dict__ )
except Exception as _reload_err:
    Misc.SendMessage( '[PATROL] WARNING: tameables reload failed: %s' % str( _reload_err ), 1100 )

from Scripts.glossary.colors import colors
from Scripts.utilities.mobiles import GetEmptyMobileList
from Scripts import config
from System.Collections.Generic import List
from System import Byte

# ── Configuration ─────────────────────────────────────────────────────────────
# True  = player directly attacks enemy mobs with their weapon
# False = player issues 'all kill' to send pets at the paragon
playerAttacksMobs = False

# How many followers the player normally runs with (combat pets, etc.).
# Only trigger the paragon purge loop when followers EXCEED this baseline,
# meaning a new animal was just tamed.
baseFollowers = 3

# Minimum taming difficulty for animals to consider. Raise to skip easy animals.
minimumTamingDifficulty = 0

# Set to True to print diagnostic info: nearby mobiles, body IDs, and why they
# pass or fail the filter. Turn off once things are working.
debugMode = False
# ──────────────────────────────────────────────────────────────────────────────

waypointsFile  = os.path.join( os.path.dirname( __file__ ), 'waypoints_random.json' )
alreadyTamedSerials = set()
    
# Sentinel returned by TameAnimal when the animal should be permanently skipped
# (already tamed, too many owners, no taming chance).
# Plain False means a transient failure (out of range, interrupted) — retry later.
SKIP = object()

# ── Route helpers ──────────────────────────────────────────────────────────────

def LoadWaypoints():
    if not os.path.exists( waypointsFile ):
        Misc.SendMessage( 'Waypoints file not found: %s' % waypointsFile, colors[ 'red' ] )
        return None
    with open( waypointsFile, 'r' ) as f:
        data = json.load( f )
    if not data:
        Misc.SendMessage( 'Waypoints file is empty', colors[ 'red' ] )
        return None
    Misc.SendMessage( 'Loaded %d waypoints from %s.' % ( len( data ), waypointsFile ) )
    return data

def NearestWaypointIndex( waypoints ):
    nearest, nearestDist = 0, 9999
    for i, point in enumerate( waypoints ):
        dist = abs( Player.Position.X - point[0] ) + abs( Player.Position.Y - point[1] )
        if dist < nearestDist:
            nearestDist = dist
            nearest = i
    return nearest

def WalkTo( x, y ):
    route = PathFinding.Route()
    route.X = x
    route.Y = y
    route.DebugMessage = False
    route.StopIfStuck = True
    return PathFinding.Go( route )

# ── Mobile helpers ─────────────────────────────────────────────────────────────

def IsParagon( mobile ):
    Mobiles.WaitForProps( mobile.Serial, 1000 )
    props = Mobiles.GetPropStringList( mobile.Serial )
    if props is None:
        return False
    for prop in props:
        if 'paragon' in prop.lower():
            return True
    return False

def FindParagon():
    effectiveSkill      = Player.GetSkillValue( 'Animal Taming' )
    blueSpawningBodyIDs = tameables.GetBlueSpawningBodyIDsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    wildNotorieties     = List[Byte]()
    wildNotorieties.Add( Byte( 3 ) )
    if blueSpawningBodyIDs:
        wildNotorieties.Add( Byte( 1 ) )

    f = Mobiles.Filter()
    f.Enabled           = True
    f.Bodies            = tameables.GetAnimalIDsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    f.Notorieties       = wildNotorieties
    f.RangeMin          = 0
    f.RangeMax          = 20
    f.IsHuman           = 0
    f.IsGhost           = 0
    f.CheckIgnoreObject = True
    candidates = Mobiles.ApplyFilter( f )

    nearest, nearestDist = None, 9999
    for m in candidates:
        if IsParagon( m ):
            dist = Player.DistanceTo( m )
            if dist < nearestDist:
                nearestDist = dist
                nearest = m
    return nearest

def FindTameable():
    effectiveSkill      = Player.GetSkillValue( 'Animal Taming' )
    blueSpawningBodyIDs = tameables.GetBlueSpawningBodyIDsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    wildNotorieties     = List[Byte]()
    wildNotorieties.Add( Byte( 3 ) )
    if blueSpawningBodyIDs:
        wildNotorieties.Add( Byte( 1 ) )

    animalFilter                   = Mobiles.Filter()
    animalFilter.Enabled           = True
    animalFilter.Bodies            = tameables.GetAnimalIDsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    animalFilter.Notorieties       = wildNotorieties
    animalFilter.RangeMin          = 0
    animalFilter.RangeMax          = 12
    animalFilter.IsHuman           = 0
    animalFilter.IsGhost           = 0
    animalFilter.CheckIgnoreObject = True
    candidates = Mobiles.ApplyFilter( animalFilter )

    validPairs = tameables.GetValidAnimalPairsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    validNames = tameables.GetValidAnimalNamesForPlayerSkill( effectiveSkill, minimumTamingDifficulty )

    if debugMode:
        Misc.SendMessage( '[debug] effectiveSkill=%.1f candidates=%d' % ( effectiveSkill, len( candidates ) ), colors[ 'yellow' ] )
        # Raw scan: all non-human, non-ghost grey/blue mobiles in range 12
        rawFilter         = Mobiles.Filter()
        rawFilter.Enabled = True
        rawFilter.RangeMin = 0
        rawFilter.RangeMax = 12
        rawFilter.IsHuman  = 0
        rawFilter.IsGhost  = 0
        for m in Mobiles.ApplyFilter( rawFilter ):
            if m.Notoriety not in ( 1, 3 ):
                continue
            mobileName = m.Name.lower()
            for prefix in ( 'an ', 'a ' ):
                if mobileName.startswith( prefix ):
                    mobileName = mobileName[ len( prefix ): ]
                    break
            inBodies   = m.Body in list( animalFilter.Bodies )
            pairOk     = ( m.Body, m.Color ) in validPairs
            nameOk     = mobileName in validNames
            Misc.SendMessage(
                '[debug] %s body=0x%04X color=0x%04X not=%d inFilter=%s pair=%s name=%s' % (
                    m.Name, m.Body, m.Color, m.Notoriety, inBodies, pairOk, nameOk ),
                colors[ 'yellow' ] )

    filteredList = GetEmptyMobileList( Mobiles )
    for m in candidates:
        if m.Serial in alreadyTamedSerials:
            continue
        notorietyOk = ( m.Notoriety == 3 or
                        ( m.Notoriety == 1 and m.Body in blueSpawningBodyIDs ) )
        if not notorietyOk:
            continue
        if IsParagon( m ):
            continue
        pairOk   = ( m.Body, m.Color ) in validPairs
        mobileName = m.Name.lower()
        for prefix in ( 'an ', 'a ' ):
            if mobileName.startswith( prefix ):
                mobileName = mobileName[ len( prefix ): ]
                break
        nameOk = mobileName in validNames
        if pairOk and nameOk:
            filteredList.Add( m )

    if len( filteredList ) == 0:
        return None
    if len( filteredList ) == 1:
        return filteredList[ 0 ]
    return Mobiles.Select( filteredList, 'Nearest' )

def MoveToAnimal( animal, maxRange = 2 ):
    if Player.DistanceTo( animal ) <= maxRange:
        return True
    WalkTo( animal.Position.X, animal.Position.Y )
    return Player.DistanceTo( animal ) <= maxRange + 2

def PetsAreNear( maxDist = 6 ):
    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.RangeMin = 0
    f.RangeMax = maxDist
    return len( Mobiles.ApplyFilter( f ) ) >= Player.Followers

# ── Combat helpers ─────────────────────────────────────────────────────────────

def AttackWithPlayer( target ):
    '''Player directly attacks the target and waits until it is dead.'''
    Misc.SendMessage( 'Attacking: %s' % target.Name, colors[ 'red' ] )
    MoveToAnimal( target, maxRange = 1 )
    fresh = Mobiles.FindBySerial( target.Serial )
    if fresh is None:
        return
    Player.Attack( fresh )
    while Mobiles.FindBySerial( target.Serial ) is not None and not Player.IsGhost:
        Misc.Pause( 500 )

def AttackWithPets( target ):
    '''Backs away and issues all kill against the target, then waits for fight to end.'''
    Misc.SendMessage( 'Sending pets — all kill: %s' % target.Name, colors[ 'cyan' ] )
    dist = Player.DistanceTo( target )
    if dist < 6:
        dx = Player.Position.X - target.Position.X
        dy = Player.Position.Y - target.Position.Y
        mag = max( abs( dx ), abs( dy ) )
        if mag > 0:
            WalkTo( target.Position.X + int( dx * 7 / mag ),
                    target.Position.Y + int( dy * 7 / mag ) )

    # Wait for pets to catch up before commanding
    Timer.Create( 'petWait', 10000 )
    while Timer.Check( 'petWait' ):
        if Player.Followers <= baseFollowers:
            return
        if PetsAreNear():
            break
        Misc.Pause( 500 )

    fresh = Mobiles.FindBySerial( target.Serial )
    if fresh is None:
        return
    Player.ChatSay( 690, 'all kill' )
    Target.WaitForTarget( 2000, True )
    Target.TargetExecute( fresh )

def HandleParagon( paragon ):
    if playerAttacksMobs:
        AttackWithPlayer( paragon )
    else:
        AttackWithPets( paragon )
        # Wait until the fight resolves before continuing
        while Player.Followers > baseFollowers and not Player.IsGhost:
            if Mobiles.FindBySerial( paragon.Serial ) is None:
                break
            Misc.Pause( 1000 )

# ── Taming ─────────────────────────────────────────────────────────────────────

def ReleaseAndKill( animal ):
    '''Release the freshly-tamed animal, then kill it with pets or player.'''
    fresh = Mobiles.FindBySerial( animal.Serial )
    if fresh is None:
        return

    Misc.SendMessage( 'Releasing: %s' % fresh.Name, colors[ 'cyan' ] )
    Misc.WaitForContext( fresh.Serial, 2000 )
    Misc.ContextReply( fresh.Serial, 9 )
    releaseGump = Gumps.WaitForGump( 3432224886, 5000 )
    if releaseGump:
        Gumps.SendAction( 3432224886, 2 )
        Misc.Pause( 1500 )  # wait for release to register server-side
    else:
        Misc.SendMessage( 'Release gump did not appear — skipping kill', colors[ 'red' ] )
        return

    fresh = Mobiles.FindBySerial( animal.Serial )
    if fresh is None:
        return

    Misc.SendMessage( 'Killing released: %s' % fresh.Name, colors[ 'cyan' ] )
    if playerAttacksMobs:
        MoveToAnimal( fresh, maxRange = 1 )
        fcheck = Mobiles.FindBySerial( fresh.Serial )
        if fcheck:
            Player.Attack( fcheck )
            while Mobiles.FindBySerial( fresh.Serial ) is not None and not Player.IsGhost:
                Misc.Pause( 500 )
    else:
        # Back away so combat pets have room
        dist = Player.DistanceTo( fresh )
        if dist < 6:
            dx  = Player.Position.X - fresh.Position.X
            dy  = Player.Position.Y - fresh.Position.Y
            mag = max( abs( dx ), abs( dy ) )
            if mag > 0:
                WalkTo( Player.Position.X + int( dx * 7 / mag ),
                        Player.Position.Y + int( dy * 7 / mag ) )
        # Wait for combat pets to catch up
        Timer.Create( 'releaseKillWait', 8000 )
        while Timer.Check( 'releaseKillWait' ):
            if PetsAreNear():
                break
            Misc.Pause( 500 )
        fcheck = Mobiles.FindBySerial( fresh.Serial )
        if fcheck is None:
            return
        Player.ChatSay( 690, 'all kill' )
        Target.WaitForTarget( 2000, True )
        Target.TargetExecute( fcheck )
        # Wait for kill
        while Mobiles.FindBySerial( fresh.Serial ) is not None and not Player.IsGhost:
            Misc.Pause( 1000 )

def TameAnimal( animal ):
    global alreadyTamedSerials
    followersBeforeTame = Player.Followers
    Misc.SendMessage( 'Taming: %s' % animal.Name, colors[ 'cyan' ] )

    # Try up to 3 times to close the gap, approaching from our current position
    # each time.  If still out of range, the mob is stuck behind terrain — kill
    # it so it clears itself rather than blocking the loop indefinitely.
    for attempt in range( 3 ):
        if MoveToAnimal( animal ):
            break
        Misc.SendMessage( 'Cannot reach animal (attempt %d/3) — trying again' % ( attempt + 1 ), colors[ 'red' ] )
        Misc.Pause( 500 )
    else:
        Misc.SendMessage( 'Animal unreachable after 3 attempts — attacking to clear', colors[ 'red' ] )
        fresh = Mobiles.FindBySerial( animal.Serial )
        if fresh is not None:
            AttackWithPlayer( fresh )
        alreadyTamedSerials.add( animal.Serial )
        return SKIP

    while not Player.IsGhost:
        current = Mobiles.FindBySerial( animal.Serial )
        if current is None:
            return SKIP  # gone — no point retrying

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
            Misc.Pause( 1000 )
            continue

        attemptStart = time.time()
        resolved = False
        while ( time.time() - attemptStart ) < 12.0:
            fresh = Mobiles.FindBySerial( animal.Serial )
            if fresh is None:
                return SKIP

            if Player.DistanceTo( fresh ) > 2:
                MoveToAnimal( fresh )

            if Journal.Search( 'It seems to accept you as master.' ) or Player.Followers > followersBeforeTame:
                alreadyTamedSerials.add( animal.Serial )
                Misc.SendMessage( 'Tamed: %s' % animal.Name, colors[ 'cyan' ] )
                return True

            if Journal.Search( 'That animal looks tame already.' ):
                alreadyTamedSerials.add( animal.Serial )
                Misc.IgnoreObject( animal )
                return SKIP  # permanent: it's tamed

            if ( Journal.Search( 'You have no chance of taming this creature' ) or
                 Journal.Search( 'This animal has had too many owners' ) ):
                resolved = True
                return SKIP  # permanent: skill too low or animal exhausted

            if ( Journal.Search( 'You see no animal there to tame.' ) or
                 Journal.Search( 'You\'ve been interrupted.' ) or
                 Journal.Search( 'You do not have a clear path to the animal' ) or
                 Journal.Search( 'You fail to tame the creature.' ) ):
                resolved = True
                break  # transient: retry skill

            Misc.Pause( 100 )

        if not resolved:
            Misc.SendMessage( 'No journal resolution — retrying skill', colors[ 'cyan' ] )

    return False

# ── Main patrol loop ───────────────────────────────────────────────────────────

def Patrol():
    waypoints = LoadWaypoints()
    if waypoints is None:
        return

    waypointIndex = NearestWaypointIndex( waypoints )
    mode = 'player attack' if playerAttacksMobs else 'pet purge'
    skill = Player.GetRealSkillValue( 'Animal Taming' )
    cap   = Player.GetSkillCap( 'Animal Taming' )
    Misc.SendMessage( 'Patrol started at waypoint %d. Mode: %s. Taming %.1f/%.1f.' % ( waypointIndex, mode, skill, cap ) )

    if skill >= cap:
        Misc.SendMessage( 'Animal Taming is already at cap (%.1f/%.1f) — nothing to do.' % ( skill, cap ), colors[ 'red' ] )
        return

    while not Player.IsGhost and Player.GetRealSkillValue( 'Animal Taming' ) < Player.GetSkillCap( 'Animal Taming' ):
        # ── Priority 1: purge excess followers ───────────────────────────────
        if Player.Followers > baseFollowers:
            Misc.SendMessage( '[patrol] followers=%d (base=%d) — hunting paragon' % ( Player.Followers, baseFollowers ), colors[ 'cyan' ] )
            paragon = FindParagon()
            if paragon is not None:
                HandleParagon( paragon )
                waypointIndex = NearestWaypointIndex( waypoints )
            continue

        # ── Priority 2: tame any animal in range ─────────────────────────────
        tameable = FindTameable()
        if tameable is not None:
            result = TameAnimal( tameable )
            if result is True:
                ReleaseAndKill( tameable )
            elif result is SKIP:
                alreadyTamedSerials.add( tameable.Serial )
            # False (transient failure) — do NOT blacklist; will retry when in range again
            Journal.Clear()
            Misc.Pause( 500 )
            continue

        # ── Priority 3: walk one waypoint step ───────────────────────────────
        x, y = waypoints[ waypointIndex ]
        if abs( Player.Position.X - x ) <= 1 and abs( Player.Position.Y - y ) <= 1:
            waypointIndex = ( waypointIndex + 1 ) % len( waypoints )
            continue

        Misc.SendMessage( '[patrol] walking to waypoint %d' % waypointIndex, colors[ 'cyan' ] )
        WalkTo( x, y )

        # After each walk step, loop back to check for animals before advancing.
        # Only advance the waypoint if we actually arrived (or if truly unreachable
        # after a second attempt), so animals spotted en route are handled first.
        if abs( Player.Position.X - x ) <= 2 and abs( Player.Position.Y - y ) <= 2:
            waypointIndex = ( waypointIndex + 1 ) % len( waypoints )
        else:
            Misc.SendMessage( '[patrol] could not reach waypoint %d — scanning for animals then retrying' % waypointIndex, colors[ 'red' ] )

        Misc.Pause( 100 )

    Misc.SendMessage( 'Patrol ended.', colors[ 'cyan' ] )

Patrol()
