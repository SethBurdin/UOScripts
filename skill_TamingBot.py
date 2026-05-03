'''
Description: Combined taming bot with interactive setup.
    Prompts you with numbered choices at startup — type 1, 2, or 3 in chat.

    Modes:
      1) Record Waypoints  — walk your route to save a patrol path to a JSON file
      2) Kirin/Unicorn     — patrol Ilshenar kirin/unicorn spawn, tame and purge via paragons
      3) General Taming    — patrol any route, tame skill-appropriate animals
                             (training loop: tame → release → kill, stops at skill cap)
'''

import json
import os
import time

from glossary.colors import colors
from utilities.mobiles import GetEmptyMobileList
from Scripts import config
from System.Collections.Generic import List
from System import Int32, Byte

SKIP                = object()
alreadyTamedSerials = set()

# ── Prompt helper ──────────────────────────────────────────────────────────────

def Prompt( question, options, timeout = 30 ):
    '''
    Displays a question and numbered options in the chat log.
    Waits up to `timeout` seconds for the player to type a number in chat.
    Returns the chosen number (1-based). Defaults to 1 on timeout.
    NOTE: type only the digit — e.g. just:  1
    '''
    Misc.SendMessage( '──────────────────────────────', colors[ 'cyan' ] )
    Misc.SendMessage( question, colors[ 'cyan' ] )
    for i, opt in enumerate( options, 1 ):
        Misc.SendMessage( '  %d) %s' % ( i, opt ), colors[ 'cyan' ] )
    Misc.SendMessage( 'Type your choice number in chat now.', colors[ 'cyan' ] )
    # Brief pause so the above SendMessage lines settle into the journal,
    # then clear so we only catch the player's reply.
    Misc.Pause( 600 )
    Journal.Clear()
    # Extra clear after a brief pause — SendMessage output is async and may
    # arrive in the journal slightly after the first Clear(), causing
    # Journal.Search() to false-positive on the option numbers in the text.
    Misc.Pause( 200 )
    Journal.Clear()
    deadline = time.time() + timeout
    while time.time() < deadline:
        for i in range( 1, len( options ) + 1 ):
            # SearchByName limits matching to the player's own speech so
            # system messages / SendMessage output never trigger a false hit.
            if Journal.SearchByName( str( i ), Player.Name ):
                Journal.Clear()
                Misc.Pause( 300 )
                Misc.SendMessage( '> %d) %s' % ( i, options[ i - 1 ] ), colors[ 'yellow' ] )
                return i
        Misc.Pause( 200 )
    Misc.SendMessage( 'No response — defaulting to option 1', colors[ 'yellow' ] )
    return 1

# ── Mode & file constants ──────────────────────────────────────────────────────

MODE_RECORD  = 1
MODE_KIRIN   = 2
MODE_GENERAL = 3

KIRIN_WAYPOINTS   = 'waypoints_KirinTaming.json'
GENERAL_WAYPOINTS = 'waypoints_random.json'

# ── Step 1: choose mode ────────────────────────────────────────────────────────

mode = Prompt(
    'SELECT MODE:',
    [
        'Record waypoints  (walk a route to save a patrol path)',
        'Kirin / Unicorn taming  (Ilshenar spawn, paragon purge)',
        'General animal taming  (training: tame → release → kill)',
    ]
)

# ══════════════════════════════════════════════════════════════════════════════
# RECORD MODE
# ══════════════════════════════════════════════════════════════════════════════

if mode == MODE_RECORD:
    file_choice = Prompt(
        'Save waypoints to:',
        [ KIRIN_WAYPOINTS, GENERAL_WAYPOINTS ]
    )
    outputFile = os.path.join(
        os.path.dirname( __file__ ),
        KIRIN_WAYPOINTS if file_choice == 1 else GENERAL_WAYPOINTS
    )
    recordIntervalTiles = 5
    pts   = []
    lastX = lastY = None

    Misc.SendMessage( 'Recording started. Walk your route. Stop this script when done.', colors[ 'cyan' ] )
    Misc.SendMessage( 'Saving to: %s' % outputFile, colors[ 'cyan' ] )

    while not Player.IsGhost:
        x, y = Player.Position.X, Player.Position.Y
        if lastX is None or abs( x - lastX ) + abs( y - lastY ) >= recordIntervalTiles:
            pts.append( [ x, y ] )
            lastX, lastY = x, y
            with open( outputFile, 'w' ) as fh:
                json.dump( pts, fh, indent = 4 )
            Misc.SendMessage( 'Waypoint %d: (%d, %d)' % ( len( pts ), x, y ), colors[ 'cyan' ] )
        Misc.Pause( 250 )

    Misc.SendMessage( 'Saved %d waypoints to %s' % ( len( pts ), outputFile ), colors[ 'cyan' ] )

# ══════════════════════════════════════════════════════════════════════════════
# TAMING MODES  (Kirin or General)
# ══════════════════════════════════════════════════════════════════════════════

else:
    # ── Step 2: waypoints file ─────────────────────────────────────────────────
    file_choice = Prompt(
        'Which waypoints file to patrol?',
        [ KIRIN_WAYPOINTS, GENERAL_WAYPOINTS ]
    )
    waypointsFile = os.path.join(
        os.path.dirname( __file__ ),
        KIRIN_WAYPOINTS if file_choice == 1 else GENERAL_WAYPOINTS
    )

    # Auto-detect baseline follower count from current character state.
    # After taming one animal the follower count rises above this and the
    # purge loop triggers automatically.
    baseFollowers = Player.Followers
    Misc.SendMessage(
        'Base followers auto-set to %d (your current follower count).' % baseFollowers,
        colors[ 'cyan' ]
    )

    # ── Step 3: post-tame action ───────────────────────────────────────────────
    tameAction = Prompt(
        'How should tamed animals be handled?',
        [
            'Release and kill with pet',
            'Rename and release  (no kill)',
            'Release and player attack',
            'Release and kill with magery  (not yet implemented)',
        ]
    )

    # Paragon/blocker handling mirrors the tame action choice:
    # "player attack" (3) → player fights paragons too; all others → pets.
    playerAttacksMobs = ( tameAction == 3 )

    # ── Shared helpers ─────────────────────────────────────────────────────────

    def WalkTo( x, y ):
        route              = PathFinding.Route()
        route.X            = x
        route.Y            = y
        route.DebugMessage = False
        route.StopIfStuck  = True
        return PathFinding.Go( route )

    def NearestWaypointIndex( waypoints ):
        nearest, nearestDist = 0, 9999
        for i, pt in enumerate( waypoints ):
            d = abs( Player.Position.X - pt[ 0 ] ) + abs( Player.Position.Y - pt[ 1 ] )
            if d < nearestDist:
                nearestDist = d
                nearest     = i
        return nearest, nearestDist

    def MoveToAnimal( animal, maxRange = 2 ):
        if Player.DistanceTo( animal ) <= maxRange:
            return True
        WalkTo( animal.Position.X, animal.Position.Y )
        return Player.DistanceTo( animal ) <= maxRange + 2

    def PetsAreNear( maxDist = 6 ):
        f          = Mobiles.Filter()
        f.Enabled  = True
        f.Friend   = True
        f.RangeMin = 0
        f.RangeMax = maxDist
        return len( Mobiles.ApplyFilter( f ) ) >= Player.Followers

    def AttackWithPlayer( target ):
        Misc.SendMessage( 'Attacking: %s' % target.Name, colors[ 'red' ] )
        MoveToAnimal( target, maxRange = 1 )
        fresh = Mobiles.FindBySerial( target.Serial )
        if fresh is None:
            return
        Player.Attack( fresh )
        while Mobiles.FindBySerial( target.Serial ) is not None and not Player.IsGhost:
            Misc.Pause( 500 )

    def AttackWithPets( target ):
        Misc.SendMessage( 'All kill: %s' % target.Name, colors[ 'cyan' ] )
        dist = Player.DistanceTo( target )
        if dist < 6:
            dx  = Player.Position.X - target.Position.X
            dy  = Player.Position.Y - target.Position.Y
            mag = max( abs( dx ), abs( dy ) )
            if mag > 0:
                WalkTo(
                    target.Position.X + int( dx * 7 / mag ),
                    target.Position.Y + int( dy * 7 / mag )
                )
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
        while Player.Followers > baseFollowers and not Player.IsGhost:
            if Mobiles.FindBySerial( target.Serial ) is None:
                break
            Misc.Pause( 1000 )

    def HandleParagon( paragon ):
        if playerAttacksMobs:
            AttackWithPlayer( paragon )
        else:
            AttackWithPets( paragon )

    def TameAnimal( animal ):
        global alreadyTamedSerials
        followersBeforeTame = Player.Followers
        Misc.SendMessage( 'Taming: %s' % animal.Name, colors[ 'cyan' ] )

        for attempt in range( 3 ):
            if MoveToAnimal( animal ):
                break
            Misc.SendMessage( 'Cannot reach (attempt %d/3) — retrying' % ( attempt + 1 ), colors[ 'red' ] )
            Misc.Pause( 500 )
        else:
            Misc.SendMessage( 'Unreachable after 3 attempts — attacking to clear', colors[ 'red' ] )
            fresh = Mobiles.FindBySerial( animal.Serial )
            if fresh is not None:
                AttackWithPlayer( fresh )
            alreadyTamedSerials.add( animal.Serial )
            return SKIP

        while not Player.IsGhost:
            # Follower count is the most reliable success signal — check before
            # clearing the journal so a late tame isn't missed.
            if Player.Followers > followersBeforeTame:
                alreadyTamedSerials.add( animal.Serial )
                Misc.SendMessage( 'Tamed (via follower count): %s' % animal.Name, colors[ 'cyan' ] )
                return True

            current = Mobiles.FindBySerial( animal.Serial )
            if current is None:
                return SKIP

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
            resolved     = False
            while ( time.time() - attemptStart ) < 13.0:
                if Player.Followers > followersBeforeTame:
                    alreadyTamedSerials.add( animal.Serial )
                    Misc.SendMessage( 'Tamed: %s' % animal.Name, colors[ 'cyan' ] )
                    return True

                fresh = Mobiles.FindBySerial( animal.Serial )
                if fresh is None:
                    return SKIP

                if Player.DistanceTo( fresh ) > 2:
                    MoveToAnimal( fresh )

                if Journal.Search( 'It seems to accept you as master.' ):
                    alreadyTamedSerials.add( animal.Serial )
                    Misc.SendMessage( 'Tamed: %s' % animal.Name, colors[ 'cyan' ] )
                    return True

                if Journal.Search( 'That animal looks tame already.' ):
                    alreadyTamedSerials.add( animal.Serial )
                    Misc.IgnoreObject( animal )
                    return SKIP

                if ( Journal.Search( 'You have no chance of taming this creature' ) or
                     Journal.Search( 'This animal has had too many owners' ) ):
                    return SKIP

                if ( Journal.Search( 'You see no animal there to tame.' ) or
                     Journal.Search( "You've been interrupted." ) or
                     Journal.Search( 'You do not have a clear path to the animal' ) or
                     Journal.Search( 'You fail to tame the creature.' ) ):
                    resolved = True
                    break

                Misc.Pause( 100 )

            if not resolved:
                Misc.SendMessage( 'No journal resolution — retrying skill', colors[ 'cyan' ] )

        return False

    def LoadWaypoints():
        if not os.path.exists( waypointsFile ):
            Misc.SendMessage( 'Waypoints file not found: %s' % waypointsFile, colors[ 'red' ] )
            return None
        with open( waypointsFile, 'r' ) as fh:
            data = json.load( fh )
        if not data:
            Misc.SendMessage( 'Waypoints file is empty', colors[ 'red' ] )
            return None
        Misc.SendMessage( 'Loaded %d waypoints from %s' % ( len( data ), os.path.basename( waypointsFile ) ) )
        return data

    # ── Kirin/Unicorn-specific ──────────────────────────────────────────────────

    if mode == MODE_KIRIN:
        KIRIN_BODY        = 0x0084
        UNICORN_BODY      = 0x007A
        paragonSerials    = set()
        notParagonSerials = set()

        def IsParagon( mobile ):
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
            f          = Mobiles.Filter()
            f.Enabled  = True
            f.IsGhost  = 0
            f.RangeMin = 0
            f.RangeMax = 20
            bl         = List[ Int32 ]()
            bl.Add( Int32( KIRIN_BODY ) )
            bl.Add( Int32( UNICORN_BODY ) )
            f.Bodies   = bl
            nearest, nearestDist = None, 9999
            for m in Mobiles.ApplyFilter( f ):
                if IsParagon( m ):
                    d = Player.DistanceTo( m )
                    if d < nearestDist:
                        nearestDist = d
                        nearest     = m
            return nearest

        def FindTameable():
            f          = Mobiles.Filter()
            f.Enabled  = True
            f.IsGhost  = 0
            f.RangeMin = 0
            f.RangeMax = 12
            bl         = List[ Int32 ]()
            bl.Add( Int32( KIRIN_BODY ) )
            bl.Add( Int32( UNICORN_BODY ) )
            f.Bodies   = bl
            result     = GetEmptyMobileList( Mobiles )
            for m in Mobiles.ApplyFilter( f ):
                if m.Notoriety == 1 and m.Serial not in alreadyTamedSerials and not IsParagon( m ):
                    result.Add( m )
            if len( result ) == 0: return None
            if len( result ) == 1: return result[ 0 ]
            return Mobiles.Select( result, 'Nearest' )

    # ── General-specific ───────────────────────────────────────────────────────

    else:
        from glossary import tameables
        try:
            _tameables_path = os.path.join(
                os.path.dirname( os.path.abspath( __file__ ) ), 'glossary', 'tameables.py'
            )
            exec( open( _tameables_path ).read(), tameables.__dict__ )
        except Exception as _e:
            Misc.SendMessage( '[WARNING] tameables reload failed: %s' % _e, 1100 )

        minimumTamingDifficulty = 0

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
            skill   = Player.GetSkillValue( 'Animal Taming' )
            blueIDs = tameables.GetBlueSpawningBodyIDsForPlayerSkill( skill, minimumTamingDifficulty )
            nots    = List[ Byte ]()
            nots.Add( Byte( 3 ) )
            if blueIDs:
                nots.Add( Byte( 1 ) )
            f                   = Mobiles.Filter()
            f.Enabled           = True
            f.Bodies            = tameables.GetAnimalIDsForPlayerSkill( skill, minimumTamingDifficulty )
            f.Notorieties       = nots
            f.RangeMin          = 0
            f.RangeMax          = 20
            f.IsHuman           = 0
            f.IsGhost           = 0
            f.CheckIgnoreObject = True
            nearest, nearestDist = None, 9999
            for m in Mobiles.ApplyFilter( f ):
                if IsParagon( m ):
                    d = Player.DistanceTo( m )
                    if d < nearestDist:
                        nearestDist = d
                        nearest     = m
            return nearest

        def FindTameable():
            skill      = Player.GetSkillValue( 'Animal Taming' )
            blueIDs    = tameables.GetBlueSpawningBodyIDsForPlayerSkill( skill, minimumTamingDifficulty )
            validPairs = tameables.GetValidAnimalPairsForPlayerSkill( skill, minimumTamingDifficulty )
            validNames = tameables.GetValidAnimalNamesForPlayerSkill( skill, minimumTamingDifficulty )
            nots       = List[ Byte ]()
            nots.Add( Byte( 3 ) )
            if blueIDs:
                nots.Add( Byte( 1 ) )
            f                   = Mobiles.Filter()
            f.Enabled           = True
            f.Bodies            = tameables.GetAnimalIDsForPlayerSkill( skill, minimumTamingDifficulty )
            f.Notorieties       = nots
            f.RangeMin          = 0
            f.RangeMax          = 12
            f.IsHuman           = 0
            f.IsGhost           = 0
            f.CheckIgnoreObject = True
            result = GetEmptyMobileList( Mobiles )
            for m in Mobiles.ApplyFilter( f ):
                if m.Serial in alreadyTamedSerials:
                    continue
                if not ( m.Notoriety == 3 or ( m.Notoriety == 1 and m.Body in blueIDs ) ):
                    continue
                if IsParagon( m ):
                    continue
                name = m.Name.lower()
                for pfx in ( 'an ', 'a ' ):
                    if name.startswith( pfx ):
                        name = name[ len( pfx ): ]
                        break
                if ( m.Body, m.Color ) in validPairs and name in validNames:
                    result.Add( m )
            if len( result ) == 0: return None
            if len( result ) == 1: return result[ 0 ]
            return Mobiles.Select( result, 'Nearest' )

    # ── Shared post-tame action ────────────────────────────────────────────────
    renameTamedAnimalsTo = 'wardoc'

    def _ReleaseAnimal( animal ):
        '''Release the pet via context menu. Returns refreshed mobile, or None on failure.'''
        fresh = Mobiles.FindBySerial( animal.Serial )
        if fresh is None:
            return None
        Misc.SendMessage( 'Releasing: %s' % fresh.Name, colors[ 'cyan' ] )
        Misc.WaitForContext( fresh.Serial, 2000 )
        Misc.ContextReply( fresh.Serial, 9 )
        if Gumps.WaitForGump( 3432224886, 5000 ):
            Gumps.SendAction( 3432224886, 2 )
            Misc.Pause( 1500 )
            return Mobiles.FindBySerial( animal.Serial )
        Misc.SendMessage( 'Release gump not shown', colors[ 'red' ] )
        return None

    def PostTameAction( animal ):
        if tameAction == 2:
            # Rename then release, no kill
            fresh = Mobiles.FindBySerial( animal.Serial )
            if fresh is None:
                return
            if fresh.Name != renameTamedAnimalsTo:
                Misc.SendMessage( 'Renaming: %s → %s' % ( fresh.Name, renameTamedAnimalsTo ), colors[ 'cyan' ] )
                Misc.PetRename( fresh, renameTamedAnimalsTo )
                Misc.Pause( 1000 )
            _ReleaseAnimal( animal )

        elif tameAction == 4:
            Misc.SendMessage( 'Magery kill not yet implemented — releasing only.', colors[ 'red' ] )
            _ReleaseAnimal( animal )

        else:
            # tameAction 1 = pet kill,  tameAction 3 = player attack
            fresh = _ReleaseAnimal( animal )
            if fresh is None:
                return
            Misc.SendMessage( 'Killing released: %s' % fresh.Name, colors[ 'cyan' ] )
            if tameAction == 3:
                MoveToAnimal( fresh, maxRange = 1 )
                fcheck = Mobiles.FindBySerial( fresh.Serial )
                if fcheck:
                    Player.Attack( fcheck )
                    while Mobiles.FindBySerial( fresh.Serial ) is not None and not Player.IsGhost:
                        Misc.Pause( 500 )
            else:
                # tameAction == 1: pet kill
                dist = Player.DistanceTo( fresh )
                if dist < 6:
                    dx  = Player.Position.X - fresh.Position.X
                    dy  = Player.Position.Y - fresh.Position.Y
                    mag = max( abs( dx ), abs( dy ) )
                    if mag > 0:
                        WalkTo(
                            Player.Position.X + int( dx * 7 / mag ),
                            Player.Position.Y + int( dy * 7 / mag )
                        )
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
                while Mobiles.FindBySerial( fresh.Serial ) is not None and not Player.IsGhost:
                    Misc.Pause( 1000 )

    # ── Patrol loop (shared) ────────────────────────────────────────────────────

    waypoints = LoadWaypoints()
    if waypoints is None:
        Misc.SendMessage( 'Cannot start — no waypoints loaded.', colors[ 'red' ] )
    else:
        waypointIndex, nearestDist = NearestWaypointIndex( waypoints )

        if nearestDist > 150:
            Misc.SendMessage(
                'ERROR: nearest waypoint is %d tiles away — wrong map or not at spawn. '
                'Gate / recall to the correct location first.' % nearestDist,
                colors[ 'red' ]
            )
        else:
            label      = 'Kirin/Unicorn' if mode == MODE_KIRIN else 'General Taming'
            attackName = 'player attack' if playerAttacksMobs else 'pet purge'
            Misc.SendMessage(
                '%s patrol started. Attack: %s. Base followers: %d. '
                'Nearest waypoint: %d (dist %d).' % (
                    label, attackName, baseFollowers, waypointIndex, nearestDist ),
                colors[ 'cyan' ]
            )

            while not Player.IsGhost:
                # General mode stops at skill cap
                if mode == MODE_GENERAL:
                    skill = Player.GetRealSkillValue( 'Animal Taming' )
                    cap   = Player.GetSkillCap( 'Animal Taming' )
                    if skill >= cap:
                        Misc.SendMessage( 'Animal Taming at cap (%.1f/%.1f) — done.' % ( skill, cap ), colors[ 'cyan' ] )
                        break

                # ── Priority 1: purge excess followers ───────────────────────
                if Player.Followers > baseFollowers:
                    paragon = FindParagon()
                    if paragon is not None:
                        HandleParagon( paragon )
                        waypointIndex, _ = NearestWaypointIndex( waypoints )
                        continue
                    # No paragon in range yet — fall through to walk toward one

                # ── Priority 2: tame (only when at baseline) ─────────────────
                if Player.Followers <= baseFollowers:
                    tameable = FindTameable()
                    if tameable is not None:
                        result = TameAnimal( tameable )
                        Journal.Clear()
                        if result is True:
                            PostTameAction( tameable )
                            Misc.Pause( 500 )
                            continue
                        if result is SKIP:
                            alreadyTamedSerials.add( tameable.Serial )
                            Misc.Pause( 500 )
                            continue
                        # False = transient failure — fall through to walk one step
                        Misc.Pause( 300 )

                # ── Priority 3: walk one waypoint step ───────────────────────
                x, y = waypoints[ waypointIndex ]
                if abs( Player.Position.X - x ) + abs( Player.Position.Y - y ) > 2:
                    WalkTo( x, y )
                waypointIndex = ( waypointIndex + 1 ) % len( waypoints )
                Misc.Pause( 200 )

            Misc.SendMessage( 'Patrol ended.', colors[ 'cyan' ] )
