'''
Author: Aga - original author of the uosteam script
Other Contributors: TheWarDoctor95 - converted to Razor Enhanced script
Last Contribution By: TheWarDoctor95 - March 19, 2019

Description: Tames nearby animals to train Animal Taming to GM
'''

## Script options ##
# Increment this whenever you make a change - if the wrong version prints at startup, remove/re-add the script in Razor
SCRIPT_VERSION = '2026-03-17-b'
# Change to the name that you want to rename the tamed animals to
renameTamedAnimalsTo = 'aaa'
# Pets listed here will NEVER be released by the script, no matter what.
# Add the names of any pets you want to keep safe (bonded pets, friends, etc.)
protectedPetNames = [
    'Magmaguard', 'Saphira', 'Your Worst Nightmare',
    'Murder Pony', 'Toothless',
]
# Add any name of pets to ignore (won't be targeted for taming)
petsToIgnore = [
    renameTamedAnimalsTo,
] + protectedPetNames
# Change to the number of followers you'd like to keep.
# The script will auto-release the most recently tamed animal if the follower number exceeds this number
# Some animals have a follower count greater than one, which may cause them to be released if this number is not set high enough
numberOfFollowersToKeep = 0
# Set to the maximum number of times to attempt to tame a single animal. 0 == attempt until tamed
maximumTameAttempts = 0
# Set the minimum taming difficulty to use when finding animals to tame
minimumTamingDifficulty = 31
# Set this to how you would like to heal your character if they take damage
# Options are:
# 'Healing' = use bandages
# 'Magery' = uses the Heal and Greater Heal ability depending on how much health is missing
# 'None' = do not auto-heal
healUsing = 'None'
# True or False to use Peacemaking if needed
enablePeacemaking = False
# True or False to track the animal being tamed
enableFollowAnimal = True
# Path to a shared file for coordinating targets between multiple Razor Enhanced clients.
# Both clients must use the same path. Set to None to disable multi-client coordination.
SHARED_CLAIMS_FILE = r'C:\Users\sethb\apps\razor-enhanced\taming_shared_claims.txt'
# How long (seconds) before a claim in the shared file is considered stale/expired.
# Set higher than your longest possible taming attempt.
SHARED_CLAIM_EXPIRY_SECONDS = 120
# Change depending on the latency to your UO shard
journalEntryDelayMilliseconds = 100
targetClearDelayMilliseconds = 100
# How long (seconds) to wait for a single tame attempt to resolve via journal before giving up.
# This prevents tameOngoing from getting stuck if the server drops a resolution message.
# Set higher than the longest possible server response delay on your shard.
TAME_ATTEMPT_TIMEOUT_SECONDS = 60

# Import Razor Enhanced API types for IntelliSense (won't execute at runtime)
try:
    from razorenhanced_stubs import *
except:
    pass  # Razor Enhanced provides these as runtime globals

from Scripts.glossary import items
from Scripts.glossary.enemies import GetEnemyNotorieties
from Scripts.glossary import spells
from Scripts.glossary import tameables
# Razor Enhanced caches module objects across script runs with its own loader.
# Re-execute tameables.py directly into the cached module's namespace so that
# all animal definitions and helper functions are always current from disk.
import os as _os
try:
    _tameables_path = _os.path.join( _os.path.dirname( _os.path.abspath( __file__ ) ), 'glossary', 'tameables.py' )
    exec( open( _tameables_path ).read(), tameables.__dict__ )
except Exception as _reload_err:
    Misc.SendMessage( '[TAMING] WARNING: tameables reload failed: %s' % str( _reload_err ), 1100 )

from System.Collections.Generic import List
from System import Byte
import time

noAnimalsToTrainTimerMilliseconds = 10000

# Tracks serials of animals tamed this session so we never re-tame a released pet
alreadyTamedSerials = set()
# Serials of pets already following the player when the script starts - never release these
preExistingPetSerials = set()
playerStuckTimerMilliseconds = 5000
catchUpToAnimalTimerMilliseconds = 20000
peacemakingTimerMilliseconds = 10000
bandageTimerMilliseconds = 5000


def _ReadSharedClaims():
    '''Returns serials blocked for this client: active claims (C) and permanently tamed (T) by any client.'''
    if SHARED_CLAIMS_FILE is None:
        return set()
    try:
        now = time.time()
        blocked = set()
        with open( SHARED_CLAIMS_FILE, 'r' ) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split( ',' )
                if len( parts ) == 3:
                    record_type = parts[0]
                    serial = int( parts[1] )
                    if record_type == 'T':
                        blocked.add( serial )  # tamed records never expire
                    elif record_type == 'C':
                        timestamp = float( parts[2] )
                        if now - timestamp < SHARED_CLAIM_EXPIRY_SECONDS:
                            blocked.add( serial )
        return blocked
    except:
        return set()


def _ClaimAnimal( serial ):
    '''Write a short-lived active claim so other clients skip this animal while we tame it.'''
    if SHARED_CLAIMS_FILE is None:
        return
    try:
        with open( SHARED_CLAIMS_FILE, 'a' ) as f:
            f.write( 'C,%d,%.2f\n' % ( serial, time.time() ) )
    except:
        pass


def _MarkTamed( serial ):
    '''Permanently record this serial as tamed so other clients never re-tame it.'''
    if SHARED_CLAIMS_FILE is None:
        return
    try:
        with open( SHARED_CLAIMS_FILE, 'a' ) as f:
            f.write( 'T,%d,0\n' % serial )
    except:
        pass


def _UnclaimAnimal( serial ):
    '''No-op: C claims expire automatically by timestamp. Never rewrite the file to avoid wiping T records.'''
    pass


def FindAnimalToTame():
    '''
    Finds the nearest tameable animal nearby that is appropriate for the player's current skill level
    '''
    global renameTamedAnimalsTo
    global minimumTamingDifficulty
    global alreadyTamedSerials
    global preExistingPetSerials

    # Use effective skill (real + items such as jewelry) so boosted players see the correct animals
    playerTamingSkill = Player.GetSkillValue( 'Animal Taming' )

    # Gray (3) is the default notoriety for wild, untamed animals.
    # Some tameables (ki-rin, etc.) spawn blue (1) and stay blue even when wild, so we
    # extend the filter to include blue only for those specific body IDs.
    blueSpawningBodyIDs = tameables.GetBlueSpawningBodyIDsForPlayerSkill( playerTamingSkill, minimumTamingDifficulty )
    wildAnimalNotorieties = List[Byte]()
    wildAnimalNotorieties.Add( Byte( 3 ) )  # Gray/neutral - wild/untamed animals
    if blueSpawningBodyIDs:
        wildAnimalNotorieties.Add( Byte( 1 ) )  # Blue - for blue-spawning tameables like ki-rin

    animalFilter = Mobiles.Filter()
    animalFilter.Enabled = True
    animalFilter.Bodies = tameables.GetAnimalIDsForPlayerSkill( playerTamingSkill, minimumTamingDifficulty )
    animalFilter.Notorieties = wildAnimalNotorieties
    animalFilter.RangeMin = 0
    animalFilter.RangeMax = 12
    animalFilter.IsHuman = 0
    animalFilter.IsGhost = 0
    animalFilter.CheckIgnoreObject = True

    tameableMobiles = Mobiles.ApplyFilter( animalFilter )

    # Exclude animals that are already tamed or in the ignore list
    # Check for "tameable" property to determine if still untamed
    # Double-check notoriety directly on each mobile (notoriety 3 = gray/wild; 1 = blue/tamed)
    # The filter above should handle this, but we verify in case the filter is not 100% reliable
    sharedClaims = _ReadSharedClaims()
    # Build precise (body, color) and name sets to post-filter animals whose body ID is shared
    # by multiple species at different skill ranges (e.g. cat/hellcat share 0x00C9;
    # polar bear/rideable polar bear share 0x00D5 and the same color).
    validAnimalPairs = tameables.GetValidAnimalPairsForPlayerSkill( playerTamingSkill, minimumTamingDifficulty )
    validAnimalNames = tameables.GetValidAnimalNamesForPlayerSkill( playerTamingSkill, minimumTamingDifficulty )
    tameableMobilesTemp = tameableMobiles[:]
    for tameableMobile in tameableMobiles:
        mobileBodyColorPair = ( tameableMobile.Body, tameableMobile.Color )
        pairIsValid = mobileBodyColorPair in validAnimalPairs
        # Only apply the name check when the (body, color) pair is shared between species so that
        # an exact-color mismatch (cat vs hellcat) and a name mismatch (polar bear vs rideable polar
        # bear) are both caught.  If in-game names include a leading article ("a polar bear"),
        # strip it before comparing.
        mobileName = tameableMobile.Name.lower()
        for prefix in ( 'an ', 'a ' ):
            if mobileName.startswith( prefix ):
                mobileName = mobileName[ len( prefix ): ]
                break
        nameIsValid = mobileName in validAnimalNames
        # Allow notoriety 3 (gray/wild) always; allow notoriety 1 (blue) only for body IDs that
        # are known to spawn blue naturally - this prevents targeting tamed pets of other players
        # whose body IDs happen to overlap. If we do accidentally target a tamed pet, the server
        # will respond with 'That animal looks tame already' which is caught and handled.
        notorietyOk = ( tameableMobile.Notoriety == 3 or
                        ( tameableMobile.Notoriety == 1 and tameableMobile.Body in blueSpawningBodyIDs ) )
        # A grey animal carrying the rename tag was previously tamed+released (by this script or
        # another player running the same script). Its name is artificial, not a species name, so
        # the name-based checks below must not exclude it.
        wasRenamedAndReleased = ( tameableMobile.Notoriety == 3 and
                                  tameableMobile.Name == renameTamedAnimalsTo )
        if ( ( tameableMobile.Name in petsToIgnore and not wasRenamedAndReleased ) or
                not notorietyOk or
                tameableMobile.Serial in alreadyTamedSerials or
                tameableMobile.Serial in preExistingPetSerials or
                tameableMobile.Serial in sharedClaims or
                not pairIsValid or
                ( not nameIsValid and not wasRenamedAndReleased ) ):
            tameableMobilesTemp.Remove( tameableMobile )

    tameableMobiles = tameableMobilesTemp

    if len( tameableMobiles ) == 0:
        return None
    elif len( tameableMobiles ) == 1:
        return tameableMobiles[ 0 ]
    else:
        return Mobiles.Select( tameableMobiles, 'Nearest' )


def PlayerWalk( direction ):
    '''
    Moves the player in the specified direction
    '''

    playerPosition = Player.Position
    if Player.Direction == direction:
        Player.Walk( direction )
    else:
        Player.Walk( direction )
        Player.Walk( direction )
    return


def FollowMobile( mobile, maxDistanceToMobile = 2, startPlayerStuckTimer = False ):
    '''
    Uses the X and Y coordinates of the animal and player to follow the animal around the map
    Returns True if player is not stuck, False if player is stuck
    '''

    if not Timer.Check( 'catchUpToAnimalTimer' ):
        return False

    mobilePosition = mobile.Position
    playerPosition = Player.Position
    directionToWalk = ''
    if mobilePosition.X > playerPosition.X and mobilePosition.Y > playerPosition.Y:
        directionToWalk = 'Down'
    if mobilePosition.X < playerPosition.X and mobilePosition.Y > playerPosition.Y:
        directionToWalk = 'Left'
    if mobilePosition.X > playerPosition.X and mobilePosition.Y < playerPosition.Y:
        directionToWalk = 'Right'
    if mobilePosition.X < playerPosition.X and mobilePosition.Y < playerPosition.Y:
        directionToWalk = 'Up'
    if mobilePosition.X > playerPosition.X and mobilePosition.Y == playerPosition.Y:
        directionToWalk = 'East'
    if mobilePosition.X < playerPosition.X and mobilePosition.Y == playerPosition.Y:
        directionToWalk = 'West'
    if mobilePosition.X == playerPosition.X and mobilePosition.Y > playerPosition.Y:
        directionToWalk = 'South'
    if mobilePosition.X == playerPosition.X and mobilePosition.Y < playerPosition.Y:
        directionToWalk = 'North'

    if startPlayerStuckTimer:
        Timer.Create( 'playerStuckTimer', playerStuckTimerMilliseconds )

    playerPosition = Player.Position
    PlayerWalk( directionToWalk )

    newPlayerPosition = Player.Position
    if playerPosition == newPlayerPosition and not Timer.Check( 'playerStuckTimer' ):
        # Player has been stuck in the same position for a while, try to find them a way out of the stuck position
        if Player.Direction == 'Up':
            for i in range ( 5 ):
                Player.Walk( 'Down' )
        elif Player.Direction == 'Down':
            for i in range( 5 ):
                Player.Walk( 'Up' )
        elif Player.Direction == 'Right':
            for i in range( 5 ):
                Player.Walk( 'Left' )
        elif Player.Direction == 'Left':
            for i in range( 5 ):
                Player.Walk( 'Right' )
        Timer.Create( 'playerStuckTimer', playerStuckTimerMilliseconds )
    elif playerPosition != newPlayerPosition:
        Timer.Create( 'playerStuckTimer', playerStuckTimerMilliseconds )

    if Player.DistanceTo( mobile ) > maxDistanceToMobile:
        # This pause may need further tuning
        # Don't want to create a ton of infinite calls if the player is stuck, but also don't want to not be able to catch up to animals
        Misc.Pause( 100 )
        FollowMobile( mobile, maxDistanceToMobile )

    return True


def TrainAnimalTaming():
    '''
    Trains Animal Taming to GM
    '''

    # User variables
    global renameTamedAnimalsTo
    global numberOfFollowersToKeep
    global maximumTameAttempts
    global enablePeacemaking
    global enableFollowAnimal
    global journalEntryDelayMilliseconds
    global targetClearDelayMilliseconds

    # Script variables
    global noAnimalsToTrainTimerMilliseconds
    global playerStuckTimerMilliseconds
    global catchUpToAnimalTimerMilliseconds
    global peacemakingTimerMilliseconds
    global bandageTimerMilliseconds

    # Show startup message
    currentSkill = Player.GetRealSkillValue( 'Animal Taming' )
    effectiveSkill = Player.GetSkillValue( 'Animal Taming' )
    skillCap = Player.GetSkillCap( 'Animal Taming' )
    Misc.SendMessage( '=== ANIMAL TAMING TRAINER STARTED (v%s) ===' % SCRIPT_VERSION, 88 )
    Misc.SendMessage( 'Current Skill: %.1f / %.1f' % (currentSkill, skillCap), 68 )
    if effectiveSkill != currentSkill:
        Misc.SendMessage( 'Effective Skill (with items): %.1f' % effectiveSkill, 68 )
    Misc.SendMessage( 'Minimum Difficulty: %i' % minimumTamingDifficulty, 68 )
    Mobiles.Message( Player.Serial, 88, 'Taming: %.1f (Min Diff: %i)' % (currentSkill, minimumTamingDifficulty) )
    # Log which animals qualify for current effective skill level
    qualifiedBodyIDs = tameables.GetAnimalIDsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    qualifiedNames = [ name for name, a in tameables.animals.items() if a != None and a.mobileID in list( qualifiedBodyIDs ) ]
    if len( qualifiedNames ) == 0:
        Misc.SendMessage( '[TAMING] WARNING: No animals qualify for skill %.1f (min difficulty %i)! Raise skill or lower minimumTamingDifficulty.' % (currentSkill, minimumTamingDifficulty), 1100 )
    else:
        Misc.SendMessage( '[TAMING] %i animal type(s) qualify: %s' % ( len( qualifiedNames ), ', '.join( qualifiedNames[:10] ) ), 68 )
    # Debug: show body IDs in filter and valid (body,color) pairs so mismatches are visible
    Misc.SendMessage( '[TAMING] Body IDs in filter: %s' % ', '.join( [ hex(int(b)) for b in qualifiedBodyIDs ] ), 68 )
    _dbgPairs = tameables.GetValidAnimalPairsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    _dbgBlue  = tameables.GetBlueSpawningBodyIDsForPlayerSkill( effectiveSkill, minimumTamingDifficulty )
    Misc.SendMessage( '[TAMING] Valid (body,color) pairs: %s' % ', '.join( [ '(%s,%s)' % (hex(int(p[0])),hex(int(p[1]))) for p in _dbgPairs ] ), 68 )
    Misc.SendMessage( '[TAMING] Blue-spawning body IDs: %s' % ', '.join( [ hex(int(b)) for b in _dbgBlue ] ), 68 )

    # Initialize variables
    animalBeingTamed = None
    tameHandled = False
    tameOngoing = False
    timesTried = 0
    bandageBeingApplied = False
    followersBeforeTame = Player.Followers
    animalInitialNotoriety = 3  # assume gray until we select a target
    tameAttemptStartTime = 0.0  # set when tameOngoing becomes True, used for timeout

    # Record serials of any pets already following at startup so we never accidentally release them.
    # Use skill=200/minDiff=0 to get ALL blue-spawning body IDs so we never mistake a wild ki-rin
    # (or any other blue-spawning tameable) for a pre-existing pet.
    global preExistingPetSerials
    _allBlueBodyIDs = tameables.GetBlueSpawningBodyIDsForPlayerSkill( 200, 0 )
    preExistingFilter = Mobiles.Filter()
    preExistingFilter.Enabled = True
    preExistingFilter.IsHuman = 0
    preExistingFilter.IsGhost = 0
    preExistingFilter.RangeMin = 0
    preExistingFilter.RangeMax = 30
    for m in Mobiles.ApplyFilter( preExistingFilter ):
        if m.Notoriety == 1 and m.Serial != Player.Serial and int( m.Body ) not in _allBlueBodyIDs:
            preExistingPetSerials.add( m.Serial )
    if len( preExistingPetSerials ) > 0:
        Misc.SendMessage( '[TAMING] Protecting %i pre-existing pet(s) from release' % len( preExistingPetSerials ), 88 )

    # Initialize skill timers
    if enablePeacemaking:
        Timer.Create( 'peacemakingTimer', 1 )

    if healUsing == 'Healing':
        Timer.Create( 'bandageTimer', 1 )
    elif healUsing == 'Magery':
        Timer.Create( 'healSpellTimer', 1 )

    # Initialize the journal and ignore object list
    Journal.Clear()
    Misc.ClearIgnore()

    # Toggle war mode to make sure the player isn't going to kill the animal being tamed
    Player.SetWarMode( True )
    Player.SetWarMode( False )

    while not Player.IsGhost:
        if Player.Followers >= 5:
            Misc.SendMessage( '[TAMING] WARNING: Follower cap reached (%i/5). Stopping script.' % Player.Followers, 1100 )
            break

        if animalBeingTamed != None and Mobiles.FindBySerial( animalBeingTamed.Serial ) == None:
            Misc.SendMessage( 'Animal was killed or disappeared' )
            _UnclaimAnimal( animalBeingTamed.Serial )
            animalBeingTamed = None

        if not maximumTameAttempts == 0 and timesTried > maximumTameAttempts:
            Mobiles.Message( animalBeingTamed, 1100, 'Tried more than %i times to tame. Ignoring animal' % maximumTameAttempts )
            Misc.IgnoreObject( animalBeingTamed )
            _UnclaimAnimal( animalBeingTamed.Serial )
            animalBeingTamed = None
            timesTried = 0

        if Player.Hits != Player.HitsMax:
            if healUsing != 'None':
                if healUsing == 'Healing' and not Timer.Check( 'bandageTimer' ):
                    # Clear any previously selected target and the target queue
                    Target.ClearLastandQueue()
                    # Wait for the target to finish clearing
                    Misc.Pause( targetClearDelayMilliseconds )

                    bandage = items.FindBandage()
                    Items.UseItem( bandage )
                    Target.TargetExecute( Player.Self )

                    Timer.Create( 'bandageTimer', bandageTimerMilliseconds )
                elif healUsing == 'Magery':
                    if ( Player.MaxHits - Player.Hits ) > 30:
                        Spells.CastMagery( 'Greater Heal' )
                        Timer.Create( 'healSpellTimer', spells.spells[ 'Greater Heal' ].delayInMs )
                    else:
                        Spells.CastMagery( 'Heal' )
                        Timer.Create( 'healSpellTimer', spells. spell[ 'Heal' ].delayInMs )

            if enablePeacemaking:
                enemyFilter = Mobiles.Filter()
                enemyFilter.Enabled = True
                enemyFilter.CheckIgnoreObject = False
                enemyFilter.Notorieties = GetEnemyNotorieties()
                enemyFilter.RangeMin = 0
                enemyFilter.RangeMax = 12
                enemies = Mobiles.ApplyFilter( enemyFilter )

                enemyAtWar = False
                enemyToPutToPeace = None
                for enemy in enemies:
                    if enemy.WarMode:
                        enemyAtWar = True
                        enemyToPutToPeace = enemy
                        break

                Timer.Create( 'peacemakingTimer', 1 )
                while enemyAtWar:
                    if not Timer.Check( 'peacemakingTimer' ):
                        # Clear any previously selected target and the target queue
                        Target.ClearLastandQueue()
                        # Wait for the target to finish clearing
                        Misc.Pause( targetClearDelayMilliseconds )

                        Player.UseSkill( 'Peacemaking' )
                        # Wait for journal entry to come up
                        Misc.Pause( journalEntryDelayMilliseconds )
                        if Journal.SearchByType( 'What instrument shall you play?', 'Regular' ):
                            instrument = items.FindInstrument( Player.Backpack.Contains )
                            if instrument == None:
                                Misc.Message( 'No instruments to peacemake with.', 1100 )
                                break
                            else:
                                Target.WaitForTarget( 2000, True )
                                Target.TargetExecute( instrument.Serial )

                        if Journal.SearchByType( 'Whom do you wish to calm?', 'Regular' ):
                            Target.WaitForTarget( 2000, True )
                            Target.TargetExecute( enemyToPutToPeace )
                        Timer.Create( 'peacemakingTimer', peacemakingTimerMilliseconds )

                    enemyAtWar = False
                    enemyToPutToPeace = None
                    for enemy in enemies:
                        if enemy.WarMode:
                            enemyAtWar = True
                            enemyToPutToPeace = enemy
                            break

                    # Wait a little bit so that the while loop doesn't consume as much CPU
                    Misc.Pause( 50 )

                if Player.WarMode:
                    Player.SetWarMode( False )

        # If there is no animal being tamed, try to find an animal to tame
        if animalBeingTamed == None:
            animalBeingTamed = FindAnimalToTame()
            if animalBeingTamed == None:
                # No animals in the area. Pause for a while so that this is constantly running until something is available to tame
                Misc.Pause( 1000 )
                continue
            else:
                Mobiles.Message( animalBeingTamed, 90, 'Targeting: %s' % animalBeingTamed.Name )
                _ClaimAnimal( animalBeingTamed.Serial )
        
        # Check if animal is close enough to tame
        maxDistanceToTarget = 5
        if not tameOngoing:
            maxDistanceToTarget = 2
        #if Player.DistanceTo( animalBeingTamed ) > 12:
        if Player.DistanceTo( animalBeingTamed ) > 30:
            Misc.SendMessage( 'Animal moved too far away, ignoring for now', 1100  )
            _UnclaimAnimal( animalBeingTamed.Serial )
            animalBeingTamed = None
            continue
        elif animalBeingTamed != None and Player.DistanceTo( animalBeingTamed ) > maxDistanceToTarget:
            if enableFollowAnimal:
                Timer.Create( 'catchUpToAnimalTimer', catchUpToAnimalTimerMilliseconds )
                playerStuck = not FollowMobile( animalBeingTamed, maxDistanceToTarget, True )
                if playerStuck:
                    Misc.SendMessage( 'Player stuck, stopping script', 1100 )
                    _UnclaimAnimal( animalBeingTamed.Serial )
                    return
            else:
                Mobiles.Message( animalBeingTamed, 34, 'Not close enough!' )

        # Tame the animal if a tame is not currently being attempted
        if not tameOngoing:
            Mobiles.Message( animalBeingTamed, 68, 'Taming...' )
            # Clear any previously selected target and the target queue
            Target.ClearLastandQueue()
            Misc.Pause( targetClearDelayMilliseconds )

            # Snapshot follower count and initial notoriety before skill use
            followersBeforeTame = Player.Followers
            animalInitialNotoriety = animalBeingTamed.Notoriety
            # Clear journal right before skill use so we get a clean read
            Journal.Clear()
            Player.UseSkill( 'Animal Taming' )
            Target.WaitForTarget( 3000, True )
            Target.TargetExecute( animalBeingTamed )
            # Give the server a moment to respond
            Misc.Pause( journalEntryDelayMilliseconds )

            # Server-enforced skill cooldown - back off and retry next loop
            if Journal.Search( 'You must wait a few moments to use another skill.' ):
                Journal.Clear()
                Misc.Pause( 2000 )
                continue

            # Check if taming was triggered by looking for the prompt
            if Journal.Search( 'Tame which animal?' ):
                timesTried += 1
                tameOngoing = True
                tameAttemptStartTime = time.time()
                Misc.SendMessage( '[TAMING] Taming attempt #%i started' % timesTried, 88 )
            else:
                # Skill blocked for another reason - back off briefly
                Misc.Pause( 500 )
                continue

        if tameOngoing:
            # Refresh mobile reference so we read current server state, not a stale cached object
            freshAnimal = Mobiles.FindBySerial( animalBeingTamed.Serial )
            if freshAnimal is None:
                Misc.SendMessage( '[TAMING] Animal disappeared during tame', 1100 )
                _UnclaimAnimal( animalBeingTamed.Serial )
                animalBeingTamed = None
                tameOngoing = False
                continue

            # For gray-spawning animals: if notoriety changed away from gray during our attempt,
            # another player tamed it before the journal told us. Abort and ignore the animal.
            # Guard: if WE just tamed it the journal will contain the success message and/or
            # our follower count will have increased -- don't treat that as a steal.
            weJustTamed = Journal.Search( 'It seems to accept you as master.' ) or ( Player.Followers > followersBeforeTame )
            if not weJustTamed and animalInitialNotoriety == 3 and freshAnimal.Notoriety != 3:
                Misc.SendMessage( '[TAMING] Animal notoriety changed to %i mid-attempt - another player tamed it, ignoring' % freshAnimal.Notoriety, 1100 )
                alreadyTamedSerials.add( animalBeingTamed.Serial )
                Misc.IgnoreObject( animalBeingTamed )
                _UnclaimAnimal( animalBeingTamed.Serial )
                Journal.Clear()
                animalBeingTamed = None
                tameOngoing = False
                continue

            # Timeout: if the journal has not resolved this attempt within TAME_ATTEMPT_TIMEOUT_SECONDS
            # the server likely dropped the result. Reset so the skill can be used again.
            if time.time() - tameAttemptStartTime > TAME_ATTEMPT_TIMEOUT_SECONDS:
                Misc.SendMessage( '[TAMING] Tame attempt timed out after %is with no journal resolution - resetting' % TAME_ATTEMPT_TIMEOUT_SECONDS, 1100 )
                tameOngoing = False
                tameAttemptStartTime = 0.0
                Journal.Clear()
                continue

            # Show status above player head every 8 seconds
            if not Timer.Check( 'tamingProgressMessageTimer' ):
                Mobiles.Message( Player.Serial, 68, 'Taming in progress...' )
                Timer.Create( 'tamingProgressMessageTimer', 8000 )

            # Three independent success signals - any one is enough:
            #   1. Journal text  (type-agnostic - works regardless of 'Regular' vs 'System' message type)
            #   2. Notoriety     (animal flips to blue/1 when tamed - only valid if it started gray)
            #   3. Follower count (Player.Followers increases when a pet is gained)
            animalTamedByJournal = Journal.Search( 'It seems to accept you as master.' )
            # Skip notoriety check for animals that spawn blue (e.g. kirin, unicorn) - they're
            # already notoriety 1 before taming, so a value of 1 is not a tame signal for them.
            animalTamedByNotoriety = ( freshAnimal.Notoriety == 1 and animalInitialNotoriety != 1 )
            animalTamedByFollowers = ( Player.Followers > followersBeforeTame )
            detectedBy = []
            if animalTamedByJournal:   detectedBy.append( 'journal' )
            if animalTamedByNotoriety: detectedBy.append( 'notoriety=%i' % freshAnimal.Notoriety )
            if animalTamedByFollowers: detectedBy.append( 'followers %i->%i' % ( followersBeforeTame, Player.Followers ) )
            if detectedBy:
                Misc.SendMessage( '[TAMING] Tame detected via: %s' % ', '.join( detectedBy ), 68 )
            if animalTamedByJournal or animalTamedByNotoriety or animalTamedByFollowers:
                tamedSerial = animalBeingTamed.Serial
                alreadyTamedSerials.add( tamedSerial )
                _MarkTamed( tamedSerial )  # tell other clients this animal is done
                Misc.SendMessage( '[TAMING] TAMED! followers=%i keepLimit=%i' % (Player.Followers, numberOfFollowersToKeep), 88 )
                Mobiles.Message( animalBeingTamed, 68, 'TAMED!' )
                if animalBeingTamed.Name != renameTamedAnimalsTo:
                    Misc.PetRename( animalBeingTamed, renameTamedAnimalsTo )
                else:
                    Misc.SendMessage( '[TAMING] Pet already named "%s"' % renameTamedAnimalsTo, 68 )
                # Wait for the server to register both the rename and the new follower count
                Misc.Pause( 2000 )
                tamedMobile = Mobiles.FindBySerial( tamedSerial )
                # Verify the rename actually took effect; retry once if not
                if tamedMobile != None and tamedMobile.Name != renameTamedAnimalsTo:
                    Misc.SendMessage( '[TAMING] Rename pending (still "%s"), retrying...' % tamedMobile.Name, 1100 )
                    Misc.PetRename( tamedMobile, renameTamedAnimalsTo )
                    Misc.Pause( 1500 )
                    tamedMobile = Mobiles.FindBySerial( tamedSerial )
                    if tamedMobile != None and tamedMobile.Name == renameTamedAnimalsTo:
                        Misc.SendMessage( '[TAMING] Renamed to "%s" (retry succeeded)' % renameTamedAnimalsTo, 68 )
                    else:
                        Misc.SendMessage( '[TAMING] WARNING: Could not confirm rename to "%s"' % renameTamedAnimalsTo, 1100 )
                elif tamedMobile != None:
                    Misc.SendMessage( '[TAMING] Renamed to "%s"' % renameTamedAnimalsTo, 68 )
                tamedName = tamedMobile.Name if tamedMobile != None else ''
                isProtected = ( tamedName in protectedPetNames ) or ( tamedSerial in preExistingPetSerials )
                if isProtected:
                    Misc.SendMessage( '[TAMING] Keeping protected pet: %s' % tamedName, 88 )
                elif Player.Followers > numberOfFollowersToKeep:
                    Misc.SendMessage( '[TAMING] Releasing pet (followers: %i > %i)' % (Player.Followers, numberOfFollowersToKeep), 68 )
                    Misc.WaitForContext( tamedSerial, 2000 )
                    Misc.ContextReply( tamedSerial, 9 )
                    releaseGump = Gumps.WaitForGump( 3432224886, 10000 )
                    if releaseGump:
                        Gumps.SendAction( 3432224886, 2 )
                    else:
                        Misc.SendMessage( '[TAMING] WARNING: Release gump did not appear', 1100 )
                else:
                    Misc.SendMessage( '[TAMING] Keeping pet (followers: %i <= %i)' % (Player.Followers, numberOfFollowersToKeep), 68 )
                Misc.IgnoreObject( animalBeingTamed )
                _UnclaimAnimal( animalBeingTamed.Serial )
                Journal.Clear()
                animalBeingTamed = None
                timesTried = 0
                tameOngoing = False
                tameHandled = False
                continue
            elif Journal.Search( 'You fail to tame the creature.' ):
                # One attempt failed - allow skill re-use next loop
                tameHandled = True
            elif ( Journal.Search( 'That is too far away.' ) or
                    Journal.Search( 'You are too far away to continue taming' ) or
                    Journal.Search( 'Someone else is already taming this' ) ):
                _UnclaimAnimal( animalBeingTamed.Serial )
                animalBeingTamed = None
                timesTried = 0
                tameHandled = True
            elif ( Journal.Search( 'You have no chance of taming this creature' ) or
                    Journal.Search( 'Target cannot be seen' ) or
                    Journal.Search( 'This animal has had too many owners and is too upset for you to tame' ) or
                    Journal.Search( 'That animal looks tame already' ) or
                    Journal.Search( 'You do not have a clear path to the animal you are taming' ) ):
                Misc.IgnoreObject( animalBeingTamed )
                _UnclaimAnimal( animalBeingTamed.Serial )
                animalBeingTamed = None
                timesTried = 0
                tameHandled = True

            if tameHandled:
                Journal.Clear()
                tameHandled = False
                tameOngoing = False

        # Wait a little bit so that the while loop doesn't consume as much CPU
        Misc.Pause( 250 )

# Start Animal Taming with proper cleanup on exit
try:
    TrainAnimalTaming()
finally:
    # Clean up targeting system to prevent broken cursor after script stops
    Target.Cancel()
    Target.ClearQueue()
    Target.ClearLastandQueue()
    Misc.SendMessage('[TAMING] Script stopped - targeting system cleaned up', 68)
