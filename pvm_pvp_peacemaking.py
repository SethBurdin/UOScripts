'''
Description: Uses the Peacemaking skill on nearby enemies.
    • Automatically selects an instrument if one is needed
    • Targets enemies in priority order:
        1. Paragons
        2. Enemies actively in War Mode (overworld only)
        3. Any other enemy
    • Tracks successfully peaced enemies and skips them until they
      resume fighting (WarMode) or die
'''

## Script options ##
showTargets = True
## End of script options ##

from Scripts.glossary.items.instruments import FindInstrument
from Scripts.glossary.enemies import GetEnemyNotorieties, GetEnemies
from Scripts.utilities.mobiles import GetEmptyMobileList
from Scripts.glossary.colors import colors
from Scripts import config

enemiesPeacedSharedValue = 'enemiesPeaced'

# Journal phrases (verified from train_Peacemaking.py)
PHRASE_COOLDOWN    = 'You must wait a few moments to use another skill.'
PHRASE_INSTRUMENT  = 'What instrument shall you play?'
PHRASE_SUCCESS_1   = 'You play hypnotic music, calming your target.'
PHRASE_SUCCESS_2   = 'You play your hypnotic music, stopping the battle.'
PHRASE_FAIL_1      = 'You attempt to calm your target, but fail.'
PHRASE_FAIL_2      = 'You attempt to calm everyone, but fail.'
PHRASE_NO_TARGET   = 'Target cannot be seen'

# Timing
SKILL_COOLDOWN_MS   = 10200  # wait after skill fires (success or fail)
COOLDOWN_RETRY_MS   = 2000   # wait when skill is still on cooldown
NO_ENEMIES_RETRY_MS = 2000   # wait when no enemies are in range


def CheckPlayerInDungeon( Player ):
    '''
    Uses the Player's X and Y coordinates to determine if they are in a dungeon.
    '''
    if Player.Position.X < 5120:
        return False
    if Player.Position.Y < 2305:
        return True
    if Player.Position.X > 6140:
        return True
    return False


def SelectEnemyToPeace( enemies ):
    '''
    Selects the nearest enemy who hasn't already been successfully peaced.
    Previously-peaced enemies are skipped unless they've resumed war mode or died.
    '''
    # ── Load and verify currently-peaced enemies ─────────────────────────────
    peacedSerials = []
    if Misc.CheckSharedValue( enemiesPeacedSharedValue ):
        stored = Misc.ReadSharedValue( enemiesPeacedSharedValue )
        verified = []
        for serialStr in stored.split( ',' ):
            mob = Mobiles.FindBySerial( int( serialStr ) )
            if mob is not None and not mob.WarMode:
                # Still alive and still peaced — keep skipping
                verified.append( serialStr )
                peacedSerials.append( int( serialStr ) )
            # else: dead or resumed fighting — drop from list

        if verified:
            Misc.SetSharedValue( enemiesPeacedSharedValue, ','.join( verified ) )
        else:
            Misc.RemoveSharedValue( enemiesPeacedSharedValue )

    # ── Build candidate list (exclude already-peaced) ─────────────────────────
    candidates = [ e for e in enemies if e.Serial not in peacedSerials ]
    if not candidates:
        candidates = list( enemies )   # all peaced — reset and retry all

    # ── Priority: paragons first ──────────────────────────────────────────────
    paragons = [ e for e in candidates if e.Color == 1157 ]
    if paragons:
        paragonList = GetEmptyMobileList( Mobiles )
        for p in paragons:
            paragonList.Add( p )
        return Mobiles.Select( paragonList, 'Nearest' )

    # ── Priority: war-mode enemies when in overworld ──────────────────────────
    if not CheckPlayerInDungeon( Player ):
        warMode = [ e for e in candidates if e.WarMode ]
        if warMode:
            warList = GetEmptyMobileList( Mobiles )
            for e in warMode:
                warList.Add( e )
            return Mobiles.Select( warList, 'Nearest' )

    candidateList = GetEmptyMobileList( Mobiles )
    for e in candidates:
        candidateList.Add( e )
    return Mobiles.Select( candidateList, 'Nearest' )


def PeaceEnemy():
    '''
    Attempts to peace one enemy per call. Handles instrument prompts,
    cooldown detection, and tracks successfully peaced targets.
    '''
    global showTargets

    Misc.ClearIgnore()

    peaceAttemptCompleted = False

    while not peaceAttemptCompleted:
        enemies = GetEnemies( Mobiles, 0, 12, GetEnemyNotorieties(), IgnorePartyMembers = True )

        if enemies is None or len( enemies ) == 0:
            Misc.SendMessage( 'No enemies to peace!', colors[ 'red' ] )
            return 'no_enemies'

        Target.ClearLastandQueue()
        Misc.Pause( config.targetClearDelayMilliseconds )

        Journal.Clear()
        Player.UseSkill( 'Peacemaking' )
        Misc.Pause( config.journalEntryDelayMilliseconds )

        # ── Cooldown check ────────────────────────────────────────────────────
        if Journal.SearchByType( PHRASE_COOLDOWN, 'Regular' ):
            Journal.Clear()
            return 'cooldown'

        # ── Instrument selection prompt ───────────────────────────────────────
        if Journal.SearchByType( PHRASE_INSTRUMENT, 'Regular' ):
            instrument = FindInstrument( Player.Backpack )
            if instrument is None:
                Misc.SendMessage( 'No instrument to peace with!', colors[ 'red' ] )
                return 'no_instrument'
            Target.WaitForTarget( 2000, True )
            Target.TargetExecute( instrument )

        # ── Target selection ──────────────────────────────────────────────────
        Target.WaitForTarget( 2000, True )
        enemy = SelectEnemyToPeace( enemies )
        Target.TargetExecute( enemy )

        Misc.Pause( config.journalEntryDelayMilliseconds )

        # ── Cannot see target → ignore and retry ─────────────────────────────
        if Journal.SearchByType( PHRASE_NO_TARGET, 'Regular' ):
            if showTargets:
                Mobiles.Message( enemy, colors[ 'red' ], 'Cannot be seen' )
            Misc.IgnoreObject( enemy )
            Journal.Clear()
            Misc.Pause( 1000 )
            continue

        # ── Success → track peaced enemy ─────────────────────────────────────
        result = 'failed'
        if ( Journal.SearchByType( PHRASE_SUCCESS_1, 'Regular' ) or
                Journal.SearchByType( PHRASE_SUCCESS_2, 'Regular' ) ):
            result = 'success'
            if showTargets:
                Mobiles.Message( enemy, colors[ 'cyan' ], 'Peaced' )
            serialStr = str( enemy.Serial )
            if Misc.CheckSharedValue( enemiesPeacedSharedValue ):
                existing = Misc.ReadSharedValue( enemiesPeacedSharedValue )
                Misc.SetSharedValue( enemiesPeacedSharedValue, existing + ',' + serialStr )
            else:
                Misc.SetSharedValue( enemiesPeacedSharedValue, serialStr )

        # ── Failure → just move on (don't track, retry next call) ────────────
        elif ( Journal.SearchByType( PHRASE_FAIL_1, 'Regular' ) or
                Journal.SearchByType( PHRASE_FAIL_2, 'Regular' ) ):
            if showTargets:
                Mobiles.Message( enemy, colors[ 'red' ], 'Peace failed' )

        Journal.Clear()
        peaceAttemptCompleted = True

    return result


# ─── Main loop ────────────────────────────────────────────────────────────────
Misc.SendMessage( 'Peacemaking started — press Stop Script to end.', colors[ 'cyan' ] )
Timer.Create( 'peacemakingTimer', 1 )   # start expired so first attempt fires immediately

while not Player.IsGhost:
    if not Timer.Check( 'peacemakingTimer' ):
        status = PeaceEnemy()

        if status == 'no_instrument':
            Misc.SendMessage( 'Stopping – no instrument available.', colors[ 'red' ] )
            break
        elif status in ( 'success', 'failed' ):
            Timer.Create( 'peacemakingTimer', SKILL_COOLDOWN_MS )
        elif status == 'cooldown':
            Timer.Create( 'peacemakingTimer', COOLDOWN_RETRY_MS )
        elif status == 'no_enemies':
            Timer.Create( 'peacemakingTimer', NO_ENEMIES_RETRY_MS )

    Misc.Pause( 50 )

Misc.SendMessage( 'Peacemaking stopped.', colors[ 'red' ] )
