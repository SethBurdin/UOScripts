'''
util_buy_regs.py

Scans nearby human NPCs and buys reagents using the RE BuyAgent.
Filters by name so only mage/alchemist vendors are targeted.

Setup (one-time, in the RE client):
    Agents tab  Buy  configure the list with the 8 magery regs and quantities.

Usage:
    1. Recall / gate to a mage shop.
    2. Run this script.
'''

from Scripts.glossary.colors import colors

#  Config 
VENDOR_RANGE         = 11       # tile radius to scan for NPCs
VENDOR_NAME_FILTER   = []       # only buy from NPCs whose name contains one of
                                #   these strings (case-insensitive).
                                #   Empty list = buy from ALL human NPCs in range.
                                #   Example: ['mage', 'alchemist']

# Context-menu index for "Buy" by vendor name keyword.
# Mage/alchemist vendors have a Train option: Train=0, Buy=1
# Scribe/provisioner vendors have no Train:   Buy=0
# Add keywords matching your scroll vendor's NPC name to route them to index 0.
VENDOR_BUY_INDEX     = {
    'default'     : 1,   # mage, etc. (have Train option — Buy is index 1)
    'alchemist'   : 4,   # Buy is the 5th option (index 4)
    'scribe'      : 0,   # no Train option — Buy is index 0
    'provisioner' : 0,
    'akbaar'      : 0,   # blank scroll vendor
}

CONTEXT_WAIT_MS      = 3000     # ms to wait for context menu to appear
BUY_WAIT_MS          = 5000     # ms for BuyAgent to fill and confirm the gump
STEP_DIR             = 'East'   # direction to step on startup to clear arrival tile
                                # Note: vendors beyond ~3 tiles won't respond to clicks;
                                #   recall rune should land you roughly central in the shop

#  Helpers 

def FindVendors():
    f          = Mobiles.Filter()
    f.Enabled  = True
    f.IsGhost  = False
    f.IsHuman  = 1
    f.RangeMax = VENDOR_RANGE
    found      = Mobiles.ApplyFilter( f )
    candidates = [ m for m in found if m.Serial != Player.Serial ]

    if VENDOR_NAME_FILTER:
        candidates = [
            m for m in candidates
            if any( keyword.lower() in m.Name.lower() for keyword in VENDOR_NAME_FILTER )
        ]

    return candidates


def CloseCurrentGump():
    '''Uses CloseGump (escape/X) rather than SendAction so no button is pressed.
    Safe on buy gumps, BOD gumps, and anything else.'''
    gump_id = int( Gumps.CurrentGump() )
    if gump_id != 0:
        Gumps.CloseGump( gump_id )
        Misc.Pause( 400 )


def GetBuyIndex( vendor_name ):
    '''Returns the correct context-menu index for this vendor based on its name.'''
    lower = vendor_name.lower()
    for keyword, index in VENDOR_BUY_INDEX.items():
        if keyword != 'default' and keyword in lower:
            return index
    return VENDOR_BUY_INDEX.get( 'default', 1 )


BOD_KEYWORDS = ( 'bulk order', 'bulk', 'order deed', 'accept' )

def IsGumpBOD():
    '''Returns True if the currently open gump looks like a Bulk Order gump.'''
    lines = Gumps.LastGumpGetLineList()
    if not lines:
        return False
    joined = ' '.join( str(l).lower() for l in lines )
    return any( kw in joined for kw in BOD_KEYWORDS )


def TryContextIndex( vendor, index ):
    '''
    Open context menu, reply with index, pause briefly, then inspect the gump.
    Returns True if the buy gump opened (not a BOD and not empty).
    Leaves the gump open so BuyAgent can fill it — caller must wait for BuyAgent.
    '''
    BuyAgent.Enable()
    Mobiles.UseMobile( vendor )

    if not Misc.WaitForContext( vendor.Serial, CONTEXT_WAIT_MS ):
        BuyAgent.Disable()
        return False

    Misc.ContextReply( vendor.Serial, index )
    Misc.Pause( 800 )   # short pause — enough for gump to appear, not too long

    if not Gumps.HasGump():
        # BuyAgent already closed it (nothing to buy or instant process)
        BuyAgent.Disable()
        return True     # treat as success — gump came and went

    # Debug: dump gump lines so we can verify exact item names for BuyAgent config
    lines = Gumps.LastGumpGetLineList()
    if lines:
        Misc.SendMessage( '  [Gump lines from %s:]' % vendor.Name, colors[ 'cyan' ] )
        for line in lines:
            s = str( line ).strip()
            if s:
                Misc.SendMessage( '    %s' % s, colors[ 'cyan' ] )

    if IsGumpBOD():
        BuyAgent.Disable()
        Misc.SendMessage( '  Index %d opened BOD — closing.' % index, colors[ 'yellow' ] )
        CloseCurrentGump()
        return False

    # Buy gump is open — leave BuyAgent enabled so it fills quantities
    return True


def BuyFrom( vendor ):
    Misc.SendMessage(
        'Buying from: %s (0x%08X)' % ( vendor.Name, vendor.Serial ),
        colors[ 'yellow' ]
    )

    CloseCurrentGump()

    # Try index 1 first (vendors with Train), fall back to 0 (no Train)
    buy_index = GetBuyIndex( vendor.Name )
    fallback   = 0 if buy_index == 1 else 1

    for idx in ( buy_index, fallback ):
        if TryContextIndex( vendor, idx ):
            # Good gump is open (or already processed) — wait for BuyAgent to finish
            Misc.Pause( BUY_WAIT_MS )
            still_open = int( Gumps.CurrentGump() ) != 0
            BuyAgent.Disable()
            if still_open:
                Misc.SendMessage( '  Out of stock or BuyAgent list mismatch: %s.' % vendor.Name, colors[ 'yellow' ] )
                CloseCurrentGump()
            else:
                Misc.SendMessage( '  Done: %s (index %d).' % ( vendor.Name, idx ), colors[ 'green' ] )
                # Update cached index for next run
                if idx != buy_index:
                    lower = vendor.Name.lower()
                    VENDOR_BUY_INDEX[ lower ] = idx
                    Misc.SendMessage( '  Tip: add "%s": %d to VENDOR_BUY_INDEX.' % ( lower, idx ), colors[ 'cyan' ] )
            return

    Misc.SendMessage( '  Could not open buy gump for %s.' % vendor.Name, colors[ 'red' ] )


#  Entry point 

Player.Walk( STEP_DIR )
Misc.Pause( 400 )

vendors = FindVendors()

if not vendors:
    Misc.SendMessage(
        'No vendors found within %d tiles%s.' % (
            VENDOR_RANGE,
            (' matching %s' % VENDOR_NAME_FILTER) if VENDOR_NAME_FILTER else ''
        ),
        colors[ 'red' ]
    )
else:
    Misc.SendMessage(
        'Found %d vendor(s)  starting buy loop.' % len( vendors ),
        colors[ 'cyan' ]
    )

    for vendor in vendors:
        BuyFrom( vendor )
        Misc.Pause( 500 )

    Misc.SendMessage( 'Buy run complete.', colors[ 'green' ] )
