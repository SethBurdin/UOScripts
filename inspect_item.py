'''
Item Inspector
Target any item to dump its properties to the system message log and to a log
file.  Container contents are listed recursively one level deep.
'''

try:
    from razorenhanced_stubs import *
except:
    pass

import datetime
import os

# ─── Config ───────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(
    os.path.expanduser('~'),
    'OneDrive', 'Documents',
    'ClassicUOLauncher-win-x64-release', 'ClassicUO',
    'data', 'plugins', 'scripts',
    'inspect_item.txt'
)

# ─── Helpers ──────────────────────────────────────────────────────────────────
_log_lines = []

def say(msg, color=68):
    Misc.SendMessage(msg, color)
    _log_lines.append(msg)

def flush_log():
    try:
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('\n' + '=' * 60 + '\n')
            f.write('  ITEM INSPECT  %s\n' % ts)
            f.write('=' * 60 + '\n')
            for line in _log_lines:
                f.write(line + '\n')
        Misc.SendMessage('[inspect_item] logged to %s' % LOG_FILE, 0x40)
    except Exception as e:
        Misc.SendMessage('[inspect_item] log write failed: %s' % e, 0x25)

# ─── Item inspection ──────────────────────────────────────────────────────────

def inspect_item(item, indent=''):
    """Print all known fields for an Item object."""
    say('%s─── 0x%08X ───────────────────────' % (indent, item.Serial), 88)
    say('%sSerial:    0x%08X  (%i)' % (indent, item.Serial, item.Serial))
    say('%sItemID:    0x%04X  (%i)' % (indent, item.ItemID, item.ItemID))
    say('%sName:      %s' % (indent, item.Name))
    say('%sColor/Hue: 0x%04X  (%i)' % (indent, item.Color, item.Color))
    say('%sAmount:    %i' % (indent, item.Amount))
    say('%sWeight:    %s' % (indent, item.Weight))
    say('%sMovable:   %s' % (indent, item.Movable))
    say('%sVisible:   %s' % (indent, item.Visible))
    pos = item.Position
    if item.Container and item.Container != -1:
        parent = Items.FindBySerial(item.Container)
        if parent is not None:
            ppos = parent.Position
            say('%sContainer: 0x%08X  (parent at X=%i Y=%i Z=%i)' % (indent, item.Container, ppos.X, ppos.Y, ppos.Z), 33)
            say('%sDistance:  %i tiles (to parent container)' % (indent, Player.DistanceTo(parent)))
        else:
            say('%sContainer: 0x%08X  (parent not found)' % (indent, item.Container), 33)
        say('%sSlot pos:  X=%i Y=%i (gump pixel offset, not world coords)' % (indent, pos.X, pos.Y))
    else:
        say('%sPosition:  X=%i Y=%i Z=%i Map=%s' % (indent, pos.X, pos.Y, pos.Z, Player.Map))
        say('%sDistance:  %i tiles' % (indent, Player.DistanceTo(item)))

    # ── Open parent container so client loads item data ───────────────────────
    if item.Container and item.Container != -1:
        parent = Items.FindBySerial(item.Container)
        if parent is not None:
            Items.UseItem(parent)
            Misc.Pause(1500)

    # ── Tooltip properties ────────────────────────────────────────────────────
    say('%s--- Properties ---' % indent, 0x53)
    props = None
    Items.SingleClick(item)
    Misc.Pause(1000)
    Items.WaitForProps(item, 5000)
    props = Items.GetPropStringList(item.Serial)
    if props:
        for i, p in enumerate(props):
            say('%s  [%i] %s' % (indent, i, p))
    else:
        say('%s  (no properties returned)' % indent, 33)

    # ── If it's a container, list contents ────────────────────────────────────
    if item.IsContainer:
        Items.UseItem(item)
        Misc.Pause(1200)
        contents = item.Contains
        if contents:
            say('%s--- Contents (%i items) ---' % (indent, len(contents)), 0x53)
            for child in contents:
                say('%s  0x%08X  ItemID=0x%04X  Name=%s  Amount=%i' % (
                    indent, child.Serial, child.ItemID, child.Name, child.Amount))
        else:
            say('%s  (container is empty)' % indent, 33)

    # ── Static tile info at same tile ──────────────────────────────────────────
    say('%s--- Statics at tile X=%i Y=%i ---' % (indent, pos.X, pos.Y), 0x53)
    try:
        statics = Statics.GetStaticsTileInfo(pos.X, pos.Y, Player.Map)
        if statics:
            for s in statics:
                say('%s  StaticID=0x%04X  Z=%i' % (indent, s.StaticID, s.StaticZ))
        else:
            say('%s  (no statics at this tile)' % indent, 33)
    except Exception as ex:
        say('%s  (statics lookup failed: %s)' % (indent, ex), 33)


# ─── Entry point ──────────────────────────────────────────────────────────────

Misc.SendMessage('=== Item Inspector === Target an item...', 88)

serial = Target.PromptTarget('Select an item to inspect')
if not serial:
    Misc.SendMessage('No target selected.', 33)
else:
    item = Items.FindBySerial(serial)
    if item is None:
        Misc.SendMessage('Item 0x%08X not found.' % serial, 33)
    else:
        inspect_item(item)
        flush_log()
