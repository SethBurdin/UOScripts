'''
util_buy_regs.py

Walks to each nearby mage/alchemist vendor, says "vendor buy",
lets the RE BuyAgent fill the gump, then transfers purchased
reagents to the pack beetle.

Setup (one-time, in the RE client):
    Agents tab > Buy > configure the list with the 8 magery regs and quantities.

Beetle detection is automatic — no friending required.
    Scans nearby mobiles for body type 0x0317 (giant/pack beetle).
    Set BEETLE_SERIAL to pin a specific beetle; leave 0 to auto-detect.
'''

from Scripts.glossary.colors import colors

#  Config
VENDOR_RANGE       = 11     # tile radius to scan for NPCs
VENDOR_NAME_FILTER = []     # filter by NPC name keywords (empty = all humans)
VENDOR_REACH       = 2      # tiles — how close we need to be before speaking
WALK_TIMEOUT_MS    = 10000  # ms to wait for pathfinding to complete
BUY_WAIT_MS        = 5000   # ms for BuyAgent to fill and confirm the gump
BEETLE_SERIAL      = 0      # pin to a specific beetle serial (0 = auto-detect)
BEETLE_RANGE       = 15     # tile radius to scan for the pack beetle
BEETLE_BODY        = 0x0317 # giant beetle body ID (from glossary/tameables.py)

REG_ITEM_IDS = frozenset([
    0x0F7A,  # Black Pearl
    0x0F7B,  # Blood Moss
    0x0F83,  # Garlic
    0x0F84,  # Ginseng
    0x0F86,  # Mandrake Root
    0x0F85,  # Nightshade
    0x0F8D,  # Spider's Silk
    0x0FA9,  # Sulfurous Ash
])

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
            if any( kw.lower() in m.Name.lower() for kw in VENDOR_NAME_FILTER )
        ]
    return candidates


def CloseCurrentGump():
    gump_id = int( Gumps.CurrentGump() )
    if gump_id != 0:
        Gumps.CloseGump( gump_id )
        Misc.Pause( 400 )


def WalkTo( vendor ):
    '''Pathfinds to within VENDOR_REACH tiles of vendor. Returns True on success.'''
    pos = vendor.Position
    Player.PathFindTo( pos.X, pos.Y, pos.Z )
    elapsed = 0
    while elapsed < WALK_TIMEOUT_MS:
        dx = abs( Player.Position.X - pos.X )
        dy = abs( Player.Position.Y - pos.Y )
        if dx <= VENDOR_REACH and dy <= VENDOR_REACH:
            return True
        Misc.Pause( 200 )
        elapsed += 200
    return False


def FindBeetle():
    '''Locates the nearest pack beetle by body type — no friend flag required.
    Falls back to BEETLE_SERIAL if set.'''
    if BEETLE_SERIAL:
        return Mobiles.FindBySerial( BEETLE_SERIAL )
    f          = Mobiles.Filter()
    f.Enabled  = True
    f.IsGhost  = False
    f.IsHuman  = -1
    f.RangeMax = BEETLE_RANGE
    found      = Mobiles.ApplyFilter( f )
    candidates = [ m for m in found if m.Body == BEETLE_BODY ]
    if not candidates:
        return None
    def dist( m ):
        dx = Player.Position.X - m.Position.X
        dy = Player.Position.Y - m.Position.Y
        return dx * dx + dy * dy
    return min( candidates, key=dist )


def TransferToBeetle():
    '''Moves all reagents from backpack into the beetle's pack.'''
    beetle = FindBeetle()
    if not beetle:
        Misc.SendMessage( 'No pack beetle found nearby.', colors[ 'red' ] )
        return
    pack = beetle.Backpack
    if not pack:
        Misc.SendMessage( 'Beetle has no accessible backpack.', colors[ 'red' ] )
        return
    moved = 0
    for item in list( Player.Backpack.Contains ):
        if item.ItemID in REG_ITEM_IDS:
            Items.Move( item, pack, item.Amount )
            Misc.Pause( 600 )
            moved += 1
    if moved:
        Misc.SendMessage( 'Transferred %d reg stack(s) to beetle.' % moved, colors[ 'green' ] )


def BuyFrom( vendor ):
    Misc.SendMessage(
        'Buying from: %s (0x%08X)' % ( vendor.Name, vendor.Serial ),
        colors[ 'yellow' ]
    )

    CloseCurrentGump()

    if not WalkTo( vendor ):
        Misc.SendMessage( '  Could not reach %s — skipping.' % vendor.Name, colors[ 'red' ] )
        return

    BuyAgent.Enable()
    Player.ChatSay( 'vendor buy' )
    Misc.Pause( BUY_WAIT_MS )

    still_open = int( Gumps.CurrentGump() ) != 0
    BuyAgent.Disable()

    if still_open:
        Misc.SendMessage( '  Out of stock or BuyAgent mismatch: %s.' % vendor.Name, colors[ 'yellow' ] )
        CloseCurrentGump()
    else:
        Misc.SendMessage( '  Done: %s.' % vendor.Name, colors[ 'green' ] )

    TransferToBeetle()


#  Entry point

vendors = FindVendors()

if not vendors:
    Misc.SendMessage(
        'No vendors found within %d tiles%s.' % (
            VENDOR_RANGE,
            ( ' matching %s' % VENDOR_NAME_FILTER ) if VENDOR_NAME_FILTER else ''
        ),
        colors[ 'red' ]
    )
else:
    Misc.SendMessage(
        'Found %d vendor(s) — starting buy loop.' % len( vendors ),
        colors[ 'cyan' ]
    )
    for vendor in vendors:
        BuyFrom( vendor )
        Misc.Pause( 500 )

    Misc.SendMessage( 'Buy run complete.', colors[ 'green' ] )
