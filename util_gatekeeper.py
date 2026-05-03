'''
Description: Gatekeeper -- runs on the gatekeeper character next to locked-down runebooks.
    Listens to party chat for commands:

      gate <X> <Y>   Open a gate to the rune nearest to tile X, Y
                     (broadcast by util_extractor.py)
      gate <name>    Open a gate to the rune whose name partially matches <name>
                     (case-insensitive; typed manually in party chat)
      rez            Rez and heal the nearest human ghost in range

    Prerequisites:
        1. Run util_runebook_explorer.py to populate runebook_locations.json.
        2. Stand the gatekeeper character next to (or near) the runebooks.
        3. Run this script.
        4. Other party members run util_extractor.py or type commands manually.

    Coordinate conversion uses UO Map 0 (Trammel/Felucca, 7168x4096).
    Accuracy is sufficient for nearest-rune selection.  Adjust MAP_WIDTH /
    MAP_HEIGHT below if your shard uses a different map size.

    Journal watermark approach: the script never calls Journal.Clear() after
    startup.  A line-count watermark tracks which entries have been processed,
    so commands that arrive during a gate or rez operation are handled on the
    next poll cycle without being lost.
'''

import json
import os
import re
import math

from Scripts.glossary.colors import colors

# ── Config ──────────────────────────────────────────────────────────────────────
LOCATIONS_FILE   = os.path.join( os.path.dirname( __file__ ), 'runebook_locations.json' )
RUNEBOOK_GUMP_ID = 89
POLL_MS          = 300   # main-loop poll interval (ms)
PARTY_CHAT_TYPE  = 'Party'   # Journal entry Type for party chat; set '' to disable filter

# Mana costs -- tune per shard
MANA_GATE        = 40    # Gate Travel  (Circle 7)
MANA_REZ         = 16    # Resurrection (Circle 5)
MANA_GREAT_HEAL  = 11    # Greater Heal (Circle 4)
MANA_HEAL        = 4     # Heal         (Circle 2)

# Timing
GATE_WAIT_MS     = 3000   # wait after pressing gate button before checking journal
SPELL_TARGET_MS  = 4000   # Target.WaitForTarget timeout
HEAL_WAIT_MS     = 2000   # pause between heal casts
REZ_ACCEPT_MS    = 30000  # max time to wait for the ghost to accept rez
MEDITATE_POLL_MS = 500
MEDITATE_MAX_MS  = 120000

# Map bounds for tile clamping
MAP_WIDTH  = 7168
MAP_HEIGHT = 4096

# Shard-calibrated sextant→tile constants.
# Derived from two confirmed rune positions:
#   Bank  83°13'S 152°47'E → tile (3493, 2571)
#   Shame  5°16'N  57°01'W → tile (512,  1564)
SHARD_X_ORIGIN = 1323    # tile x at 0° lon
SHARD_Y_ORIGIN = 1624    # tile y at 0° lat
SHARD_X_SCALE  = 14.213  # tiles per degree longitude  (E = +x)
SHARD_Y_SCALE  = 11.380  # tiles per degree latitude   (S = +y)


# ── Coordinate helpers ──────────────────────────────────────────────────────────

def CoordToTile( coord_str ):
    '''
    Convert a UO sextant coordinate string to approximate tile (x, y).
    Example: "47o 17'N, 139o 46'W" -> (801, 972)
    Returns (x, y) tuple or None if the string cannot be parsed or is "Nowhere".
    Uses shard-calibrated constants (SHARD_X/Y_ORIGIN / SCALE) rather than
    the generic MAP_WIDTH/360 formula which does not match this shard.
    '''
    if not coord_str or coord_str.strip() == 'Nowhere':
        return None
    m = re.match( r"(\d+)o\s+(\d+)'([NS]),\s+(\d+)o\s+(\d+)'([EW])", coord_str.strip() )
    if not m:
        return None
    lat = int( m.group(1) ) + int( m.group(2) ) / 60.0
    lon = int( m.group(4) ) + int( m.group(5) ) / 60.0
    if m.group(3) == 'N':
        lat = -lat
    if m.group(6) == 'W':
        lon = -lon
    x = int( SHARD_X_ORIGIN + SHARD_X_SCALE * lon + 0.5 )
    y = int( SHARD_Y_ORIGIN + SHARD_Y_SCALE * lat + 0.5 )
    return ( max( 0, min( MAP_WIDTH  - 1, x ) ),
             max( 0, min( MAP_HEIGHT - 1, y ) ) )


# ── Data loading ────────────────────────────────────────────────────────────────

def LoadRunes():
    '''
    Load runebook_locations.json and return a flat list of rune dicts.
    Each entry has: slot, name, gate_button, serial_dec, book_name, tile_xy.
    Skips runes where has_location is false (no marked position).
    '''
    if not os.path.exists( LOCATIONS_FILE ):
        Misc.SendMessage(
            'runebook_locations.json not found -- run util_runebook_explorer.py first.',
            colors['red']
        )
        return []
    try:
        with open( LOCATIONS_FILE, 'r' ) as f:
            data = json.load( f )
    except Exception as e:
        Misc.SendMessage( 'Failed to load runebook_locations.json: %s' % str(e), colors['red'] )
        return []

    runes = []
    for serial_hex, book in data.get( 'runebooks', {} ).items():
        serial_dec = book.get( 'serial_dec', int( serial_hex, 16 ) )
        book_name  = book.get( 'name', serial_hex )
        for rune in book.get( 'runes', [] ):
            if not rune.get( 'has_location' ):
                continue
            runes.append( {
                'slot'        : rune['slot'],
                'name'        : rune['name'],
                'gate_button' : rune['gate_button'],
                'serial_dec'  : serial_dec,
                'book_name'   : book_name,
                'tile_xy'     : CoordToTile( rune.get( 'coordinate', '' ) ),
            } )
    return runes


# ── Rune selection ──────────────────────────────────────────────────────────────

def FindRuneByCoord( runes, tx, ty ):
    '''Return the rune whose tile_xy is closest to (tx, ty), or None.'''
    scored = []
    for rune in runes:
        xy = rune.get( 'tile_xy' )
        if xy is None:
            Misc.SendMessage(
                '  (no tile) %s -- coordinate could not be parsed' % rune['name'],
                colors['red']
            )
            continue
        d = math.sqrt( ( tx - xy[0] ) ** 2 + ( ty - xy[1] ) ** 2 )
        scored.append( ( d, rune ) )

    if not scored:
        return None

    scored.sort( key=lambda pair: pair[0] )
    # Print the top 3 candidates so the user can verify the math
    for d, rune in scored[:3]:
        Misc.SendMessage(
            '  dist %6.0f  tile %-20s  %s' % ( d, str( rune['tile_xy'] ), rune['name'] ),
            colors['yellow']
        )
    return scored[0][1]


def FindRuneByName( runes, partial ):
    '''Return the first rune whose name contains partial (case-insensitive), or None.'''
    partial_lower = partial.lower()
    for rune in runes:
        if partial_lower in rune['name'].lower():
            return rune
    return None


# 3-tile gate-casting rotation.
# After a gate is opened it occupies the caster's tile, blocking a second
# cast from the same spot.  Cycling through these (dx, dy) offsets from the
# gatekeeper's starting position lets successive gates be cast immediately.
# Layout (viewed from above, runebook container to the North):
#   West tile (-1,0) | Center (0,0) | East tile (+1,0)
GATE_OFFSETS = [ (0, 0), (-1, 0), (1, 0) ]


# ── Mana management ─────────────────────────────────────────────────────────────

def MeditateToMana( min_mana ):
    if Player.Mana >= min_mana:
        return
    Player.UseSkill( 'Meditation' )
    waited = 0
    while Player.Mana < min_mana and waited < MEDITATE_MAX_MS:
        Misc.Pause( MEDITATE_POLL_MS )
        waited += MEDITATE_POLL_MS


def EnsureMana( min_mana ):
    '''If mana is below min_mana, notify party and meditate until sufficient.'''
    if Player.Mana >= min_mana:
        return
    Player.ChatParty( 'Gatekeeper: low mana, meditating.' )
    Misc.SendMessage(
        'Low mana (%d/%d) -- meditating to %d.' % ( Player.Mana, Player.ManaMax, min_mana ),
        colors['yellow']
    )
    MeditateToMana( min_mana )


def StepToGateTile( base_x, base_y, dx ):
    '''
    Walk to (base_x + dx, base_y) if not already there.
    dx is -1 (west), 0 (center), or +1 (east).
    '''
    target_x = base_x + dx
    if Player.Position.X == target_x:
        return
    direction = 'East' if target_x > Player.Position.X else 'West'
    Player.Walk( direction )
    Misc.Pause( 400 )   # let server confirm the step


# ── Gate travel ─────────────────────────────────────────────────────────────────

def HandleGate( runes, arg, base_pos, gate_idx ):
    '''
    arg is everything after "gate " -- either "X Y" (tile coords) or a partial rune name.
    Attempts to open the book to the chosen rune and cast Gate Travel.
    base_pos : (base_x, base_y) captured at startup.
    gate_idx : mutable list [int] -- current rotation slot; advanced after each cast.
    '''
    # Resolve the rune
    rune  = None
    parts = arg.split()
    if len( parts ) == 2:
        try:
            tx, ty = int( parts[0] ), int( parts[1] )
            Misc.SendMessage(
                'Coord lookup: player tile (%d, %d).' % ( tx, ty ),
                colors['yellow']
            )
            rune = FindRuneByCoord( runes, tx, ty )
        except ValueError:
            pass
    if rune is None:
        rune = FindRuneByName( runes, arg )

    if rune is None:
        Misc.SendMessage( 'No rune matched: %s' % arg, colors['red'] )
        Player.ChatParty( 'Gatekeeper: no rune found for "%s".' % arg )
        return

    tile_info = str( rune['tile_xy'] ) if rune['tile_xy'] else 'no tile'
    Misc.SendMessage(
        'Gating to %s (slot %d, btn %d, rune tile %s).' % (
            rune['name'], rune['slot'], rune['gate_button'], tile_info ),
        colors['cyan']
    )

    EnsureMana( MANA_GATE )

    # Step to the next rotation tile so the previous gate doesn't block this cast
    base_x, base_y = base_pos
    dx = GATE_OFFSETS[ gate_idx[0] ][0]
    StepToGateTile( base_x, base_y, dx )

    # Find and open the runebook
    book = Items.FindBySerial( rune['serial_dec'] )
    if book is None:
        Misc.SendMessage( 'Runebook 0x%08X not found.' % rune['serial_dec'], colors['red'] )
        Player.ChatParty( 'Gatekeeper: runebook not in range.' )
        return

    Items.UseItem( book )
    if not Gumps.WaitForGump( RUNEBOOK_GUMP_ID, 5000 ):
        Misc.SendMessage( 'Runebook gump timed out.', colors['red'] )
        Player.ChatParty( 'Gatekeeper: could not open runebook.' )
        return

    # Clear journal, press gate button, then check for confirmation message
    Journal.Clear()
    Gumps.SendAction( RUNEBOOK_GUMP_ID, rune['gate_button'] )
    Misc.Pause( GATE_WAIT_MS )

    gate_confirmed = Journal.Search( 'You open a magical gate' )

    if gate_confirmed:
        Misc.SendMessage( 'Gate confirmed: %s.' % rune['name'], colors['green'] )
    else:
        # Notify regardless -- shard message wording may differ
        Misc.SendMessage( 'Gate command sent for %s (no journal confirmation).' % rune['name'], colors['yellow'] )

    Player.ChatParty( 'Gatekeeper: opened gate to %s.' % rune['name'] )

    # Advance rotation for the next cast
    gate_idx[0] = ( gate_idx[0] + 1 ) % len( GATE_OFFSETS )

    MeditateToMana( Player.ManaMax )


# ── Rez + heal ──────────────────────────────────────────────────────────────────

def HandleRez():
    '''Find the nearest human ghost in range, resurrect, then heal to full.'''
    ghost_filter          = Mobiles.Filter()
    ghost_filter.Enabled  = True
    ghost_filter.IsGhost  = 1
    ghost_filter.IsHuman  = 1
    ghost_filter.RangeMax = 5

    ghosts = Mobiles.ApplyFilter( ghost_filter )
    if not ghosts or len( ghosts ) == 0:
        Misc.SendMessage( 'No ghost in range 5.', colors['yellow'] )
        Player.ChatParty( 'Gatekeeper: no ghost in range.' )
        return

    ghost = Mobiles.Select( ghosts, 'Nearest' )
    Misc.SendMessage( 'Rezzing %s.' % ghost.Name, colors['cyan'] )

    EnsureMana( MANA_REZ )

    Spells.CastMagery( 'Resurrection' )
    Target.WaitForTarget( SPELL_TARGET_MS, False )
    Target.TargetExecute( ghost )

    # Re-fetch each tick so IsGhost reflects current server state
    waited   = 0
    accepted = False
    while waited < REZ_ACCEPT_MS:
        Misc.Pause( 500 )
        waited += 500
        fresh = Mobiles.FindBySerial( ghost.Serial )
        if fresh is None or not fresh.IsGhost:
            accepted = True
            break

    if not accepted:
        Misc.SendMessage( 'Rez not accepted by %s.' % ghost.Name, colors['yellow'] )
        Player.ChatParty( 'Gatekeeper: rez not accepted by %s.' % ghost.Name )
        return

    Misc.SendMessage( '%s accepted rez -- healing.' % ghost.Name, colors['cyan'] )

    # Heal loop -- up to 20 casts to avoid infinite loops
    for _ in range( 20 ):
        target = Mobiles.FindBySerial( ghost.Serial )
        if target is None or target.Hits >= target.HitsMax:
            break
        if ( target.HitsMax - target.Hits ) > 30:
            EnsureMana( MANA_GREAT_HEAL )
            Spells.CastMagery( 'Greater Heal' )
        else:
            EnsureMana( MANA_HEAL )
            Spells.CastMagery( 'Heal' )
        Target.WaitForTarget( SPELL_TARGET_MS, False )
        Target.TargetExecute( target )
        Misc.Pause( HEAL_WAIT_MS )

    Misc.SendMessage( 'Done healing %s.' % ghost.Name, colors['green'] )
    Player.ChatParty( '%s is up and healed.' % ghost.Name )
    MeditateToMana( Player.ManaMax )


def HandleHeal():
    '''Find the nearest living human in range and heal them to full.'''
    heal_filter          = Mobiles.Filter()
    heal_filter.Enabled  = True
    heal_filter.IsGhost  = 0
    heal_filter.IsHuman  = 1
    heal_filter.RangeMax = 5

    targets = Mobiles.ApplyFilter( heal_filter )
    # Exclude the gatekeeper themselves
    targets = [ m for m in targets if m.Serial != Player.Serial ] if targets else []
    if not targets or len( targets ) == 0:
        Misc.SendMessage( 'No player in range 5 to heal.', colors['yellow'] )
        Player.ChatParty( 'Gatekeeper: no one in range to heal.' )
        return

    target = Mobiles.Select( targets, 'Nearest' )
    Misc.SendMessage( 'Healing %s.' % target.Name, colors['cyan'] )

    for _ in range( 20 ):
        t = Mobiles.FindBySerial( target.Serial )
        if t is None or t.Hits >= t.HitsMax:
            break
        if ( t.HitsMax - t.Hits ) > 30:
            EnsureMana( MANA_GREAT_HEAL )
            Spells.CastMagery( 'Greater Heal' )
        else:
            EnsureMana( MANA_HEAL )
            Spells.CastMagery( 'Heal' )
        Target.WaitForTarget( SPELL_TARGET_MS, False )
        Target.TargetExecute( t )
        Misc.Pause( HEAL_WAIT_MS )

    Misc.SendMessage( 'Done healing %s.' % target.Name, colors['green'] )
    Player.ChatParty( 'Gatekeeper: %s is healed.' % target.Name )
    MeditateToMana( Player.ManaMax )


# ── Text normalization ───────────────────────────────────────────────────────────

def NormalizeText( raw ):
    '''
    Lowercase, strip whitespace.
    Strips a "Name: " speaker prefix if the journal entry includes it inline.
    '''
    text = raw.strip().lower()
    if ': ' in text:
        text = text.split( ': ', 1 )[1].strip()
    return text


# ── Main loop ────────────────────────────────────────────────────────────────────

def Main():
    runes = LoadRunes()
    if not runes:
        return

    book_count = len( set( r['serial_dec'] for r in runes ) )
    Misc.SendMessage(
        'Gatekeeper online -- %d runes across %d book(s).' % ( len( runes ), book_count ),
        colors['green']
    )
    Player.ChatParty( 'Gatekeeper online.' )

    # Snapshot starting position for gate-tile rotation
    base_pos = ( Player.Position.X, Player.Position.Y )
    gate_idx  = [0]   # mutable so HandleGate can advance it (IronPython 2 compat)

    # Discard pre-existing entries; watermark advances so entries are never re-read
    Journal.Clear()
    journal_idx = 0

    while not Player.IsGhost:
        found_cmd  = None
        found_arg  = None
        new_entries = Journal.GetJournalEntry( journal_idx )
        if new_entries:
            journal_idx += len( new_entries )
            for entry in new_entries:
                if not entry.Name or entry.Name.lower() == Player.Name.lower():
                    continue
                if PARTY_CHAT_TYPE and entry.Type != PARTY_CHAT_TYPE:
                    continue
                cmd = NormalizeText( entry.Text )
                if cmd.startswith( 'gate ' ):
                    arg = cmd[ 5: ].strip()
                    if arg:
                        found_cmd = 'gate'
                        found_arg = arg
                    break
                elif cmd == 'rez':
                    found_cmd = 'rez'
                    break
                elif cmd == 'heal':
                    found_cmd = 'heal'
                    break

        if found_cmd == 'gate' and found_arg:
            HandleGate( runes, found_arg, base_pos, gate_idx )
        elif found_cmd == 'rez':
            HandleRez()
        elif found_cmd == 'heal':
            HandleHeal()

        Misc.Pause( POLL_MS )

    Misc.SendMessage( 'Gatekeeper stopped: you are a ghost.', colors['red'] )
    Player.ChatParty( 'Gatekeeper offline.' )


Main()
