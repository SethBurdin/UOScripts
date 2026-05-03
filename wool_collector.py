'''
Description: Wool Collector — complete wool-to-cloth pipeline.
    Prompts you with activity choices at startup — type a number in chat.

    Activities:
      1) Collect Wool       — finds nearby sheep, runs to each and shears with
                              a dagger or skinning knife
      2) Use Spinning Wheel — uses all raw wool in inventory on a spinning wheel
                              to produce thread, waiting between each batch
      3) Use Loom           — uses all thread in inventory on a loom to produce cloth
      4) Patrol Runebook    — recalls through rune locations searching for sheep;
                              shears all sheep at each stop before moving on
      5) Auto-Shear         — continuously watches for unshorn sheep in proximity
                              and shears them automatically; runs until stopped
      6) Bank Wool          — casts Recall from spellbook (player targets bank rune)
                              or falls back to runebook gump if no spellbook found;
                              opens bank and deposits all wool

    NOTE: Adjust WOOL_ID, YARN_ID, and CLOTH_ID below if your shard uses
    different item IDs for these resources.
'''

import time

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.items.tools import tools
from utilities.items import FindItem, MoveItem
import config
from System.Collections.Generic import List
from System import Int32

# ── Item IDs  (adjust per shard if needed) ────────────────────────────────────
WOOL_ID   = 0x0DF8   # raw wool / fleece sheared from sheep
YARN_ID   = 0x0DF9   # ball of yarn (produced by spinning wheel)
CLOTH_ID  = 0x0F9A   # bolts of cloth   (produced by loom)

# Body IDs for sheep variants (unshorn & shorn)
SHEEP_BODY_IDS = [ 0x00CF, 0x00D0 ]

# ── Prompt helper ─────────────────────────────────────────────────────────────

def Prompt( question, options, timeout = 30 ):
    '''
    Displays a numbered menu in chat and waits for the player to type a choice.
    Returns the chosen number (1-based). Defaults to 1 on timeout.
    Type only the digit in chat — e.g. just:  1
    '''
    Misc.SendMessage( '──────────────────────────────', colors[ 'cyan' ] )
    Misc.SendMessage( question, colors[ 'cyan' ] )
    for i, opt in enumerate( options, 1 ):
        Misc.SendMessage( '  %d) %s' % ( i, opt ), colors[ 'cyan' ] )
    Misc.SendMessage( 'Type your choice number in chat now.', colors[ 'cyan' ] )
    # Brief pause so the SendMessage lines settle into the journal, then clear
    # so only the player's reply is caught.
    Misc.Pause( 600 )
    Journal.Clear()
    Misc.Pause( 200 )
    Journal.Clear()
    deadline = time.time() + timeout
    while time.time() < deadline:
        for i in range( 1, len( options ) + 1 ):
            if Journal.SearchByName( str( i ), Player.Name ):
                Journal.Clear()
                Misc.Pause( 300 )
                Misc.SendMessage( '> %d) %s' % ( i, options[ i - 1 ] ), colors[ 'yellow' ] )
                return i
        Misc.Pause( 200 )
    Misc.SendMessage( 'No response — defaulting to option 1', colors[ 'yellow' ] )
    return 1


# ── Helpers ───────────────────────────────────────────────────────────────────

def GetShearTool():
    '''Returns a dagger or skinning knife from the player backpack, or None.'''
    tool = FindItem( tools[ 'dagger' ].itemID, Player.Backpack )
    if tool is None:
        tool = FindItem( tools[ 'skinning knife' ].itemID, Player.Backpack )
    return tool


def FindNearbySheep():
    '''Returns a list of all sheep within 20 tiles.'''
    sheepFilter          = Mobiles.Filter()
    sheepFilter.Enabled  = True
    sheepFilter.IsGhost  = 0
    sheepFilter.RangeMin = 0
    sheepFilter.RangeMax = 20

    bodyList = List[ Int32 ]()
    for bodyID in SHEEP_BODY_IDS:
        bodyList.Add( Int32( bodyID ) )
    sheepFilter.Bodies = bodyList

    return Mobiles.ApplyFilter( sheepFilter )


def FindNearbyUnshornSheep():
    '''Returns a list of unshorn (woolly) sheep within 20 tiles.
    Only matches body 0x00CF — shorn sheep (0x00D0) are excluded.
    '''
    sheepFilter          = Mobiles.Filter()
    sheepFilter.Enabled  = True
    sheepFilter.IsGhost  = 0
    sheepFilter.RangeMin = 0
    sheepFilter.RangeMax = 20

    bodyList = List[ Int32 ]()
    bodyList.Add( Int32( SHEEP_BODY_IDS[ 0 ] ) )   # 0x00CF — woolly only
    sheepFilter.Bodies = bodyList

    return Mobiles.ApplyFilter( sheepFilter )


def GetWoolItem():
    '''
    Finds raw wool in the player's backpack.
    If none is found, prompts the player to target the wool manually.
    Returns the wool Item, or None if cancelled / not found.
    '''
    wool = Items.FindByID( WOOL_ID, -1, Player.Backpack.Serial )
    if wool is not None:
        return wool
    Misc.SendMessage( 'No wool found in backpack. Please target the wool now...', colors[ 'yellow' ] )
    woolSerial = Target.PromptTarget( 'Target the wool to deposit' )
    if woolSerial == 0:
        return None
    return Items.FindBySerial( woolSerial )


def MoveToSheep( animal, maxRange = 1, timeoutMs = 15000 ):
    '''
    Pathfinds to within maxRange tiles of the sheep.
    Issues PathFinding.Go() once, then polls until the player arrives.
    Re-issues only if the player hasn't moved in 3 seconds (genuinely stuck).
    Returns True if close enough, False if timed out or animal gone.
    '''
    if Player.DistanceTo( animal ) <= maxRange:
        return True

    def _go():
        fresh = Mobiles.FindBySerial( animal.Serial )
        if fresh is None:
            return False
        pos = fresh.Position
        # Path to the adjacent tile nearest to the player rather than the
        # sheep's exact tile — mobiles occupy their tile so routing directly
        # to it causes the pathfinder to stall immediately.
        px, py = Player.Position.X, Player.Position.Y
        best_x, best_y = pos.X, pos.Y
        best_dist = 9999
        for dx, dy in ( (1,0), (-1,0), (0,1), (0,-1) ):
            tx, ty = pos.X + dx, pos.Y + dy
            d = abs( tx - px ) + abs( ty - py )
            if d < best_dist:
                best_dist = d
                best_x, best_y = tx, ty
        route            = PathFinding.Route()
        route.X          = best_x
        route.Y          = best_y
        route.DebugMessage = False
        route.StopIfStuck  = False
        PathFinding.Go( route )
        return True

    if not _go():
        return False

    Timer.Create( 'moveToSheep_timeout', timeoutMs )
    lastPos      = Player.Position
    stuckMs      = 0
    stuckRetries = 0
    STUCK_LIMIT  = 1500   # re-issue path after 1.5 s of no movement
    MAX_RETRIES  = 3      # give up after 3 failed re-issues (mob blocking path)
    POLL_MS      = 50

    while Timer.Check( 'moveToSheep_timeout' ):
        if Player.IsGhost:
            return False

        fresh = Mobiles.FindBySerial( animal.Serial )
        if fresh is None:
            return False
        if Player.DistanceTo( fresh ) <= maxRange:
            return True

        curPos = Player.Position
        if curPos.X == lastPos.X and curPos.Y == lastPos.Y:
            stuckMs += POLL_MS
            if stuckMs >= STUCK_LIMIT:
                stuckMs = 0
                stuckRetries += 1
                if stuckRetries >= MAX_RETRIES:
                    return False   # path is permanently blocked (mob on route)
                if not _go():
                    return False
        else:
            stuckMs      = 0
            stuckRetries = 0
            lastPos      = curPos

        Misc.Pause( POLL_MS )

    fresh = Mobiles.FindBySerial( animal.Serial )
    return fresh is not None and Player.DistanceTo( fresh ) <= maxRange + 1


# ── Activity 1: Collect Wool ──────────────────────────────────────────────────

def CollectWool():
    '''
    Shears every nearby sheep using a dagger or skinning knife.
    Skips sheep that have already been sheared this run.
    '''
    tool = GetShearTool()
    if tool is None:
        Misc.SendMessage( 'No dagger or skinning knife found in your backpack!', colors[ 'red' ] )
        return

    sheep = FindNearbySheep()
    if len( sheep ) == 0:
        Misc.SendMessage( 'No sheep found within range.', colors[ 'yellow' ] )
        return

    Misc.SendMessage( 'Found %d sheep. Shearing...' % len( sheep ), colors[ 'green' ] )

    shearedSerials = set()
    for animal in sheep:
        fresh = Mobiles.FindBySerial( animal.Serial )
        if fresh is None or fresh.Serial in shearedSerials:
            continue

        if Player.DistanceTo( fresh ) > 1:
            Misc.SendMessage( 'Moving to sheep...', colors[ 'cyan' ] )
            if not MoveToSheep( fresh ):
                Misc.SendMessage( 'Could not reach sheep — skipping.', colors[ 'yellow' ] )
                continue

        Journal.Clear()
        Items.UseItem( tool )
        Target.WaitForTarget( 3000, False )
        Target.TargetExecute( fresh )

        # Wait for shear result or timeout
        Timer.Create( 'shear_timeout', 1000 )
        while Timer.Check( 'shear_timeout' ):
            if ( Journal.Search( 'You place' ) or
                 Journal.SearchByType( 'already shorn', 'Regular' ) or
                 Journal.SearchByType( 'wool',         'Regular' ) ):
                break
            Misc.Pause( 100 )

        shearedSerials.add( fresh.Serial )
        Misc.Pause( config.dragDelayMilliseconds )

    wool = Items.FindByID( WOOL_ID, -1, Player.Backpack.Serial )
    woolCount = wool.Amount if wool is not None else 0
    Misc.SendMessage( 'Done shearing! Wool in inventory: %d.' % woolCount, colors[ 'green' ] )


# ── Activity 2: Use Spinning Wheel ────────────────────────────────────────────

def PromptSpinningWheels():
    '''
    Prompts the player to target spinning wheels one at a time.
    Target yourself to finish adding wheels and return the list of serials.
    '''
    wheels = []
    Misc.SendMessage( 'Target each spinning wheel, then target YOURSELF when done.', colors[ 'cyan' ] )
    while True:
        serial = Target.PromptTarget( 'Target spinning wheel #%d  (target yourself to finish)' % ( len( wheels ) + 1 ) )
        if serial == 0:
            Misc.SendMessage( 'No target — stopping wheel selection.', colors[ 'yellow' ] )
            break
        if serial == Player.Serial:
            Misc.SendMessage( 'Done selecting wheels. %d wheel(s) registered.' % len( wheels ), colors[ 'green' ] )
            break
        if serial in wheels:
            Misc.SendMessage( 'That wheel is already added, skipping.', colors[ 'yellow' ] )
            continue
        wheels.append( serial )
        Misc.SendMessage( 'Wheel #%d added (0x%08X). Target another or target yourself to finish.' % ( len( wheels ), serial ), colors[ 'cyan' ] )
    return wheels


def UseSpinningWheel():
    '''
    Spins all raw wool in inventory into thread using one or more spinning wheels.
    Prompts the player to target each wheel; target yourself to finish adding wheels.
    Cycles through wheels round-robin until all wool is spun.
    '''
    if Items.FindByID( WOOL_ID, -1, Player.Backpack.Serial ) is None:
        Misc.SendMessage( 'No wool in your inventory!', colors[ 'red' ] )
        return

    wheels = PromptSpinningWheels()
    if not wheels:
        Misc.SendMessage( 'No wheels selected. Aborting.', colors[ 'red' ] )
        return

    Misc.SendMessage( 'Spinning wool into thread across %d wheel(s)...' % len( wheels ), colors[ 'green' ] )

    while True:
        # Feed one wool to each wheel in rapid succession, then wait 3 s for
        # all wheels to finish their animation before the next round.
        fed = 0
        for wheelSerial in wheels:
            woolItem = Items.FindByID( WOOL_ID, -1, Player.Backpack.Serial )
            if woolItem is None:
                break
            Items.UseItem( woolItem )
            Target.WaitForTarget( 3000, False )
            Target.TargetExecute( wheelSerial )
            Misc.Pause( 800 )
            fed += 1

        if fed == 0:
            break

        # Wait for the first completion message from any wheel, then proceed.
        # Fall back to 8 s timeout if no message arrives.
        Journal.Clear()
        Timer.Create( 'spin_timeout', 8000 )
        while Timer.Check( 'spin_timeout' ):
            if ( Journal.Search( 'You add' ) or
                 Journal.Search( 'thread' ) or
                 Journal.Search( 'You spin' ) or
                 Journal.Search( 'You place' ) or
                 Journal.Search( 'balls of yarn' ) or
                 Journal.Search( 'yarn' ) ):
                break
            Misc.Pause( 100 )

    yarn = Items.FindByID( YARN_ID, -1, Player.Backpack.Serial )
    yarnCount = yarn.Amount if yarn is not None else 0
    Misc.SendMessage( 'Done spinning! Balls of yarn in inventory: %d.' % yarnCount, colors[ 'green' ] )


# ── Activity 3: Use Loom ──────────────────────────────────────────────────────

def UseLoom():
    '''
    Weaves all balls of yarn in inventory into cloth on a loom.
    Continues until no yarn remains.
    '''
    Misc.SendMessage( 'Target a ball of yarn in your backpack...', colors[ 'cyan' ] )
    yarnSerial = Target.PromptTarget( 'Target a ball of yarn in your backpack' )
    if yarnSerial == 0:
        Misc.SendMessage( 'No target selected. Aborting.', colors[ 'red' ] )
        return
    yarnSample = Items.FindBySerial( yarnSerial )
    if yarnSample is None:
        Misc.SendMessage( 'Could not find that item. Aborting.', colors[ 'red' ] )
        return
    yarnItemID = yarnSample.ItemID
    Misc.SendMessage( 'Yarn item ID detected: 0x%04X' % yarnItemID, colors[ 'cyan' ] )

    Misc.SendMessage( 'Target the loom...', colors[ 'cyan' ] )
    loomSerial = Target.PromptTarget( 'Target the loom' )
    if loomSerial == 0:
        Misc.SendMessage( 'No target selected. Aborting.', colors[ 'red' ] )
        return

    Misc.SendMessage( 'Weaving thread into cloth...', colors[ 'green' ] )

    while True:
        yarnItem = Items.FindByID( yarnItemID, -1, Player.Backpack.Serial )
        if yarnItem is None:
            break

        Journal.Clear()
        Items.UseItem( yarnItem )
        Target.WaitForTarget( 3000, False )
        Target.TargetExecute( loomSerial )
        Misc.Pause( 500 )

        # Wait for the loom to finish weaving before the next use
        Timer.Create( 'loom_timeout', 1200 )
        while Timer.Check( 'loom_timeout' ):
            if ( Journal.SearchByType( 'You weave', 'Regular' ) or
                 Journal.SearchByType( 'cloth',     'Regular' ) or
                 Journal.SearchByType( 'You roll',  'Regular' ) or
                 Journal.SearchByType( 'bolt',      'Regular' ) ):
                break
            Misc.Pause( 50 )

        Misc.Pause( 300 )

    cloth = Items.FindByID( CLOTH_ID, -1, Player.Backpack.Serial )
    clothCount = cloth.Amount if cloth is not None else 0
    Misc.SendMessage( 'Done weaving! Cloth in inventory: %d.' % clothCount, colors[ 'green' ] )


# ── Runebook gump constants ──────────────────────────────────────────────────
RUNEBOOK_GUMP_ID  = 1431013363
RUNEBOOK_ITEM_ID  = 0x22C5
RECALL_CAST_DELAY = 3000   # ms to wait after casting Recall for travel to complete


def GetRuneNames( runebook ):
    '''
    Opens the runebook gump and reads the rune names from the line list.
    Returns a list of non-empty rune name strings.
    '''
    Items.UseItem( runebook )
    Misc.Pause( config.dragDelayMilliseconds )
    Gumps.WaitForGump( RUNEBOOK_GUMP_ID, 5000 )

    lineList = Gumps.LastGumpGetLineList()
    # Strip the 3 header lines
    lineList = lineList[ 3 : ]

    # Skip past 'Set default' / 'Drop rune' entries and the two charge count lines
    endIdx = 0
    for line in lineList:
        if line in ( 'Set default', 'Drop rune' ):
            endIdx += 1
        else:
            break
    endIdx += 2   # charge count + max charge

    runeNames = lineList[ endIdx : endIdx + 16 ]
    runeNames = [ n for n in runeNames if n != 'Empty' and n.strip() != '' ]

    # Close the gump
    Gumps.SendAction( RUNEBOOK_GUMP_ID, 0 )
    return runeNames


def RecallToRune( runebook, runeIndex ):
    '''
    Opens the runebook and recalls to the rune at the given 0-based index.
    Waits for travel to complete.
    '''
    Items.UseItem( runebook )
    
    Gumps.WaitForGump( RUNEBOOK_GUMP_ID, 5000 )
    Misc.Pause( 200 )

    # Rune recall buttons: 5, 11, 17, 23 ... (5 + index * 6)
    Gumps.SendAction( RUNEBOOK_GUMP_ID, 5 + runeIndex * 6 )
    Misc.Pause( RECALL_CAST_DELAY )


def PatrolRunebook():
    '''
    Prompts to select a runebook, then presents its rune list as a menu so
    the player can pick which runes to patrol.  Recalls to each chosen rune,
    shears all nearby sheep, then continues to the next stop.
    '''
    tool = GetShearTool()
    if tool is None:
        Misc.SendMessage( 'No dagger or skinning knife found in your backpack!', colors[ 'red' ] )
        return

    # ── Select runebook ───────────────────────────────────────────────────────
    Misc.SendMessage( 'Target your runebook...', colors[ 'cyan' ] )
    rbSerial = Target.PromptTarget( 'Target the runebook to patrol' )
    runebook  = Items.FindBySerial( rbSerial )
    if runebook is None or runebook.ItemID != RUNEBOOK_ITEM_ID:
        Misc.SendMessage( 'That is not a runebook!', colors[ 'red' ] )
        return

    # ── Read rune names ───────────────────────────────────────────────────────
    Misc.SendMessage( 'Reading runebook...', colors[ 'cyan' ] )
    runeNames = GetRuneNames( runebook )
    if len( runeNames ) == 0:
        Misc.SendMessage( 'Runebook has no runes!', colors[ 'red' ] )
        return

    # ── Ask player which runes to visit ───────────────────────────────────────
    runeOptions = runeNames + [ 'ALL runes' ]
    runeChoice  = Prompt( 'SELECT RUNE(S) TO PATROL:', runeOptions )

    if runeChoice == len( runeOptions ):
        # Last option = all runes
        indicesToVisit = list( range( len( runeNames ) ) )
    else:
        indicesToVisit = [ runeChoice - 1 ]

    Misc.SendMessage( 'Patrolling %d rune(s)...' % len( indicesToVisit ), colors[ 'green' ] )

    # ── Patrol loop ───────────────────────────────────────────────────────────
    for idx in indicesToVisit:
        runeName = runeNames[ idx ]
        Misc.SendMessage( 'Recalling to: %s' % runeName, colors[ 'cyan' ] )
        RecallToRune( runebook, idx )

        # Re-fetch tool in case it broke during a previous shear
        tool = GetShearTool()
        if tool is None:
            Misc.SendMessage( 'No shearing tool left!', colors[ 'red' ] )
            return

        sheep = FindNearbySheep()
        if len( sheep ) == 0:
            Misc.SendMessage( 'No sheep at %s — moving on.' % runeName, colors[ 'yellow' ] )
            continue

        Misc.SendMessage( 'Found %d sheep at %s. Shearing...' % ( len( sheep ), runeName ), colors[ 'green' ] )
        shearedSerials = set()
        for animal in sheep:
            fresh = Mobiles.FindBySerial( animal.Serial )
            if fresh is None or fresh.Serial in shearedSerials:
                continue

            if Player.DistanceTo( fresh ) > 1:
                if not MoveToSheep( fresh ):
                    Misc.SendMessage( 'Could not reach sheep — skipping.', colors[ 'yellow' ] )
                    continue

            Journal.Clear()
            Items.UseItem( tool )
            Target.WaitForTarget( 3000, False )
            Target.TargetExecute( fresh )

            Timer.Create( 'shear_timeout', 5000 )
            while Timer.Check( 'shear_timeout' ):
                if ( Journal.SearchByType( 'You shear',     'Regular' ) or
                     Journal.SearchByType( 'already shorn', 'Regular' ) or
                     Journal.SearchByType( 'wool',          'Regular' ) ):
                    break
                Misc.Pause( 100 )

            shearedSerials.add( fresh.Serial )
            Misc.Pause( config.dragDelayMilliseconds )

    wool = Items.FindByID( WOOL_ID, -1, Player.Backpack.Serial )
    woolCount = wool.Amount if wool is not None else 0
    Misc.SendMessage( 'Patrol complete! Wool in inventory: %d.' % woolCount, colors[ 'green' ] )


# ── Activity 5: Auto-Shear ──────────────────────────────────────────────────

def AutoShear():
    '''
    Continuously watches the surrounding area for unshorn sheep (body 0x00CF).
    Moves to and shears any found within range, then pauses before scanning again.
    Runs until the player dies or the script is stopped.
    '''
    tool = GetShearTool()
    if tool is None:
        Misc.SendMessage( 'No dagger or skinning knife found in your backpack!', colors[ 'red' ] )
        return

    Misc.SendMessage( 'Auto-Shear started. Watching for woolly sheep nearby...', colors[ 'green' ] )

    while not Player.IsGhost:
        tool = GetShearTool()
        if tool is None:
            Misc.SendMessage( 'No shearing tool left — stopping Auto-Shear.', colors[ 'red' ] )
            return

        sheep = FindNearbyUnshornSheep()

        if len( sheep ) > 0:
            Misc.SendMessage( 'Found %d unshorn sheep — shearing.' % len( sheep ), colors[ 'cyan' ] )
            shearedThisCycle = set()

            for animal in sheep:
                fresh = Mobiles.FindBySerial( animal.Serial )
                if fresh is None or fresh.Serial in shearedThisCycle:
                    continue

                if Player.DistanceTo( fresh ) > 1:
                    if not MoveToSheep( fresh ):
                        continue

                Journal.Clear()
                Items.UseItem( tool )
                Target.WaitForTarget( 3000, False )
                Target.TargetExecute( fresh )

                Timer.Create( 'shear_timeout', 5000 )
                while Timer.Check( 'shear_timeout' ):
                    if ( Journal.SearchByType( 'You shear',     'Regular' ) or
                         Journal.SearchByType( 'already shorn', 'Regular' ) or
                         Journal.SearchByType( 'wool',          'Regular' ) ):
                        break
                    Misc.Pause( 100 )

                shearedThisCycle.add( fresh.Serial )
                Misc.Pause( config.dragDelayMilliseconds )

        # Pause before the next proximity scan
        Misc.Pause( 3000 )

    Misc.SendMessage( 'Auto-Shear stopped (player is a ghost).', colors[ 'yellow' ] )


# ── Activity 6: Bank Wool ─────────────────────────────────────────────────────

def BankWool():
    '''
    Deposits all raw wool into the bank box.
    Casts Recall targeting a runebook found in the player's backpack, which
    travels to that runebook's default rune (set to the bank).
    If no runebook is found in the backpack, prompts the player to target one.
    '''
    wool = GetWoolItem()
    if wool is None:
        Misc.SendMessage( 'No wool to deposit. Aborting.', colors[ 'red' ] )
        return

    # Find the runebook to use as the Recall target (default rune = bank)
    runebook = Items.FindByID( RUNEBOOK_ITEM_ID, -1, Player.Backpack.Serial )
    if runebook is None:
        Misc.SendMessage( 'No runebook in backpack. Target your runebook...', colors[ 'cyan' ] )
        rbSerial = Target.PromptTarget( 'Target the runebook with your bank rune set as default' )
        runebook  = Items.FindBySerial( rbSerial )
        if runebook is None or runebook.ItemID != RUNEBOOK_ITEM_ID:
            Misc.SendMessage( 'That is not a runebook!', colors[ 'red' ] )
            return

    # Cast Recall and target the runebook — UO uses its default rune
    Misc.SendMessage( 'Recalling to bank...', colors[ 'cyan' ] )
   
    Spells.CastMagery( "Recall" )
    Target.WaitForTarget( 4000)
    Target.TargetExecute( runebook.Serial )
    # if not Target.WaitForTarget( 5000, False ):
    #     Misc.SendMessage( 'Recall failed — no spellbook, mana, or reagents?', colors[ 'red' ] )
    #     return
    # Target.TargetExecute( runebook.Serial )
    Misc.Pause( RECALL_CAST_DELAY )

    # Open the bank box
    Journal.Clear()
    Player.ChatSay( colors[ 'cyan' ], 'bank' )
    Timer.Create( 'bank_open_timeout', 5000 )
    while Timer.Check( 'bank_open_timeout' ):
        if Player.Bank is not None:
            break
        Misc.Pause( 150 )

    if Player.Bank is None:
        Misc.SendMessage( 'Could not open bank. Are you near a banker?', colors[ 'red' ] )
        return

    Misc.Pause( 500 )

    # Deposit all wool stacks (there may be more than one)
    totalDeposited = 0
    while True:
        wool = Items.FindByID( WOOL_ID, -1, Player.Backpack.Serial )
        if wool is None:
            break
        stackAmount = wool.Amount
        MoveItem( Items, Misc, wool, Player.Bank )
        totalDeposited += stackAmount

    if totalDeposited > 0:
        Misc.SendMessage( 'Deposited %d wool into bank.' % totalDeposited, colors[ 'green' ] )
    else:
        Misc.SendMessage( 'No wool found in backpack to deposit.', colors[ 'yellow' ] )


# ── Main ──────────────────────────────────────────────────────────────────────

choice = Prompt(
    'WOOL COLLECTOR — Choose activity:',
    [
        'Collect Wool  (shear nearby sheep with dagger / skinning knife)',
        'Use Spinning Wheel  (spin wool into thread)',
        'Use Loom  (weave thread into cloth)',
        'Patrol Runebook  (recall between rune locations to find and shear sheep)',
        'Auto-Shear  (continuously shear woolly sheep in proximity)',
        'Bank Wool  (recall to bank and deposit wool)',
    ]
)

if choice == 1:
    CollectWool()
elif choice == 2:
    UseSpinningWheel()
elif choice == 3:
    UseLoom()
elif choice == 4:
    PatrolRunebook()
elif choice == 5:
    AutoShear()
elif choice == 6:
    BankWool()
