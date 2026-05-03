'''
Description: Runebook explorer -- opens a runebook gump, parses its rune data,
    and saves a structured JSON file keyed by runebook serial.

    Produces: runebook_<serial>.json with rune names, coordinates, and the
    Gate Travel button ID for each slot.  Used to build the gatekeeper
    location database.

    Usage:
        1. Stand near the runebook.
        2. Run this script.
        3. Click the runebook when the target cursor appears.
        4. Inspect runebook_<serial>.json.

    Gump structure (GroupID 89, 115 lines for a 16-rune book):
        Line 0         : "Rename book"
        Lines 1-N      : button labels per slot (5 per filled, 3 per empty)
        Lines N+0..N+3 : "Charges", "Max Charges", current_charges, max_charges
        Lines N+4..N+19: 16 rune names in slot order ("Empty" for unused)
        Lines N+20+    : name+coord pairs (2 lines per filled, 1 "Empty" per unused)

    Gate Travel button formula (confirmed from in-game tests):
        button = 100 + slot_index  (0-based)
        slot 0 -> 100, slot 4 -> 104, slot 6 -> 106
    NOTE: if you scanned books before this was confirmed, re-run the explorer
    to regenerate runebook_locations.json with correct gate_button values.
'''

import json
import os
import datetime

from glossary.colors import colors

RUNEBOOK_ITEM_ID = 0x22C5
RUNEBOOK_GUMP_ID = 89
GATE_BUTTON_BASE = 100  # confirmed: button = 100 + slot_index (0-based)
RUNE_SLOTS       = 16

OUTPUT_DIR      = os.path.dirname( __file__ )
LOCATIONS_FILE  = os.path.join( OUTPUT_DIR, 'runebook_locations.json' )


def LoadLocations():
    '''Load existing runebook_locations.json, or return an empty structure.'''
    if os.path.exists( LOCATIONS_FILE ):
        with open( LOCATIONS_FILE, 'r' ) as f:
            return json.load( f )
    return { 'last_updated': '', 'runebooks': {} }


def SaveLocations( data ):
    data[ 'last_updated' ] = datetime.datetime.now().strftime( '%Y-%m-%dT%H:%M:%S' )
    with open( LOCATIONS_FILE, 'w' ) as f:
        json.dump( data, f, indent=2 )


def ParseRunebookLines( lines ):
    '''
    Parses the flat gump line list into structured rune records.
    Returns (current_charges, max_charges, runes) or None on failure.

    Rune names are guaranteed unique on the real runebook, so we use
    a simple dict keyed by name for the final output.
    '''
    # Anchor on "Charges" -- appears after all the per-slot button labels.
    # Using a dynamic search handles books with different numbers of filled slots.
    charges_idx = None
    for i, line in enumerate( lines ):
        if line == 'Charges':
            charges_idx = i
            break

    if charges_idx is None:
        Misc.SendMessage( 'Could not find "Charges" anchor -- unexpected gump structure.', colors[ 'red' ] )
        return None

    try:
        current_charges = int( lines[ charges_idx + 2 ] )
        max_charges     = int( lines[ charges_idx + 3 ] )
    except ( IndexError, ValueError ):
        Misc.SendMessage( 'Could not parse charge counts.', colors[ 'red' ] )
        return None

    # 16 rune names follow the 4 charge lines, positional (index == slot).
    name_start = charges_idx + 4
    name_list  = lines[ name_start : name_start + RUNE_SLOTS ]

    # Name+coord pairs section immediately follows the 16 names.
    # Filled slot : two lines -- name, coordinate string
    # Empty slot  : one line  -- "Empty"
    pair_idx = name_start + RUNE_SLOTS
    runes    = []

    for slot_idx in range( RUNE_SLOTS ):
        gate_button = GATE_BUTTON_BASE + slot_idx

        if pair_idx >= len( lines ):
            break

        pair_line = lines[ pair_idx ]

        if pair_line == 'Empty':
            pair_idx += 1
            # Skip unused slots entirely -- gatekeeper only needs filled runes.
        else:
            coord_line   = lines[ pair_idx + 1 ] if ( pair_idx + 1 ) < len( lines ) else ''
            has_location = ( coord_line != 'Nowhere' and coord_line.strip() != '' )
            runes.append( {
                'slot'        : slot_idx,
                'name'        : pair_line,
                'coordinate'  : coord_line if has_location else None,
                'has_location': has_location,
                'gate_button' : gate_button,
            } )
            pair_idx += 2

    return current_charges, max_charges, runes


def DumpRunebook():
    # ── 1. Target ─────────────────────────────────────────────────────────────
    Misc.SendMessage( 'Click the runebook to inspect...', colors[ 'cyan' ] )
    serial = Target.PromptTarget( 'Select a runebook' )
    if serial == 0 or serial == -1:
        Misc.SendMessage( 'No target selected -- aborting.', colors[ 'red' ] )
        return

    item = Items.FindBySerial( serial )
    if item is None:
        Misc.SendMessage( 'Item not found in range -- aborting.', colors[ 'red' ] )
        return

    if item.ItemID != RUNEBOOK_ITEM_ID:
        Misc.SendMessage( 'Not a runebook (ItemID 0x%04X).' % item.ItemID, colors[ 'red' ] )
        return

    # ── 2. Open gump ──────────────────────────────────────────────────────────
    Items.UseItem( item )
    Misc.Pause( 800 )

    if not Gumps.WaitForGump( RUNEBOOK_GUMP_ID, 5000 ):
        Misc.SendMessage( 'Gump %d did not appear (CurrentGump=%d).' % (
            RUNEBOOK_GUMP_ID, int( Gumps.CurrentGump() ) ), colors[ 'red' ] )
        return

    # ── 3. Capture lines ──────────────────────────────────────────────────────
    raw_lines = Gumps.LastGumpGetLineList()
    lines     = list( raw_lines ) if raw_lines else []
    Misc.SendMessage( 'Captured %d lines.' % len( lines ), colors[ 'cyan' ] )

    # ── 4. Close gump ─────────────────────────────────────────────────────────
    Gumps.CloseGump( RUNEBOOK_GUMP_ID )
    Misc.Pause( 300 )

    # ── 5. Parse ──────────────────────────────────────────────────────────────
    result = ParseRunebookLines( lines )
    if result is None:
        return
    current_charges, max_charges, runes = result

    Misc.SendMessage( 'Found %d runes (%d with locations):' % (
        len( runes ), sum( 1 for r in runes if r[ 'has_location' ] ) ), colors[ 'cyan' ] )
    for r in runes:
        Misc.SendMessage( '  [slot %2d  btn %3d]  %-20s  %s' % (
            r[ 'slot' ], r[ 'gate_button' ], r[ 'name' ],
            r[ 'coordinate' ] if r[ 'has_location' ] else '(no location)' ), colors[ 'yellow' ] )

    # ── 6. Merge into runebook_locations.json ────────────────────────────────
    serial_key = '0x%08X' % int( serial )
    locations  = LoadLocations()

    locations[ 'runebooks' ][ serial_key ] = {
        'serial_hex'         : serial_key,
        'serial_dec'         : int( serial ),
        'name'               : item.Name,
        'charges'            : current_charges,
        'max_charges'        : max_charges,
        'gate_button_formula': 'button = %d + slot_index' % GATE_BUTTON_BASE,
        'runes'              : runes,
    }

    SaveLocations( locations )
    book_count = len( locations[ 'runebooks' ] )
    Misc.SendMessage( 'Saved %s -> runebook_locations.json (%d book(s) total).' % (
        serial_key, book_count ), colors[ 'green' ] )
    return True


def Main():
    locations = LoadLocations()
    existing  = len( locations[ 'runebooks' ] )
    if existing:
        Misc.SendMessage( 'Loaded existing runebook_locations.json (%d book(s)).' % existing, colors[ 'cyan' ] )
    else:
        Misc.SendMessage( 'No existing runebook_locations.json -- starting fresh.', colors[ 'cyan' ] )

    Misc.SendMessage( 'Target runebooks one at a time. Cancel (Escape) when done.', colors[ 'cyan' ] )
    scanned = 0
    while True:
        added = DumpRunebook()
        if added:
            scanned += 1
        else:
            # DumpRunebook returns None on cancel or error -- stop looping on cancel
            break

    Misc.SendMessage( 'Done. Scanned %d book(s) this session.' % scanned, colors[ 'green' ] )


Main()
