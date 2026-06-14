# extraction_looter/corpse_util.py
# Corpse scanning and skinning logic, adapted from skinning.py as importable functions.
#
# Functions:
#   scan_nearby_corpses(scan_range)  -> list[Item]   skinnable creature corpses
#   nearest_corpse(corpses)          -> Item          closest corpse to player
#   walk_to_corpse(corpse)           -> None          pathfind to corpse position
#   open_corpse(corpse)              -> bool          open and wait for contents
#   skin_corpse(corpse, tool)        -> bool          skin and confirm

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.items.tools import tools
from glossary.colors import colors
from utilities.items import FindItem

SKIN_WAIT_MS      = 900    # ms after skinning tool use
ACTION_DELAY_MS   = 1200   # general action cooldown

SKINNING_TOOL_IDS = [
    tools['skinning knife'].itemID,
    tools['dagger'].itemID,
]

CANT_SKIN_PHRASES = [
    'you cannot',
    'nothing to skin',
    'already been skinned',
    'cannot skin',
]

_TAG = '[corpse]'


def _log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def _is_humanoid_corpse(corpse):
    name = (corpse.Name or '').lower()
    return 'body of' in name or 'remains of' in name


def find_skinning_tool():
    """
    Return the first skinning knife or dagger in the player's backpack, or None.

    Returns:
        Item or None
    """
    for tool_id in SKINNING_TOOL_IDS:
        tool = FindItem(tool_id, Player.Backpack)
        if tool is not None:
            return tool
    return None


def scan_nearby_corpses(scan_range):
    """
    Find all skinnable creature corpses within scan_range tiles.
    Humanoid corpses (players/NPCs) are silently skipped.

    Input:
        scan_range -- int, tile radius

    Returns:
        list of Item objects (skinnable creature corpses)
    """
    f          = Items.Filter()
    f.Enabled  = True
    f.IsCorpse = 1
    f.RangeMin = 0
    f.RangeMax = scan_range

    result = []
    for corpse in Items.ApplyFilter(f):
        if _is_humanoid_corpse(corpse):
            continue
        result.append(corpse)

    return result


def nearest_corpse(corpses):
    """Return the corpse closest to the player from a list."""
    def _dist(c):
        return abs(c.Position.X - Player.Position.X) + abs(c.Position.Y - Player.Position.Y)
    return min(corpses, key=_dist)


def walk_to_corpse(corpse):
    """Pathfind to the corpse's tile. No-op if already adjacent."""
    dx = abs(corpse.Position.X - Player.Position.X)
    dy = abs(corpse.Position.Y - Player.Position.Y)
    if dx <= 1 and dy <= 1:
        _log('Already adjacent to "%s" (0x%X).' % (corpse.Name, corpse.Serial))
        return
    _log('Walking to "%s" (0x%X) at (%d, %d)...' % (
        corpse.Name, corpse.Serial, corpse.Position.X, corpse.Position.Y))
    route              = PathFinding.Route()
    route.X            = corpse.Position.X
    route.Y            = corpse.Position.Y
    route.DebugMessage = False
    route.StopIfStuck  = True
    PathFinding.Go(route)
    _log('Arrived at "%s".' % corpse.Name)


def open_corpse(corpse):
    """
    Open a corpse and wait for the server to populate its contents.
    Must be called before reading corpse.Contains.

    Input:
        corpse -- Item object

    Returns:
        bool  True if contents are available
    """
    _log('Opening corpse "%s" (0x%X)...' % (corpse.Name, corpse.Serial))
    for attempt in range(5):
        Journal.Clear()
        Items.UseItem(corpse.Serial)
        Misc.Pause(1500)
        if not Journal.Search("You must wait to perform another action."):
            break
        _log('Server busy on open — retry %d/5.' % (attempt + 1), colors['yellow'])
        Misc.Pause(ACTION_DELAY_MS)
    has_contents = corpse.Contains is not None
    return has_contents


def skin_corpse(corpse, tool):
    """
    Use tool on corpse and verify the server accepted the action.

    Input:
        corpse -- Item object
        tool   -- Item object (skinning knife or dagger)

    Returns:
        bool  True if skinning succeeded (no rejection phrase in journal)
    """
    _log('Skinning "%s" (0x%X) — clearing journal...' % (corpse.Name, corpse.Serial))
    Journal.Clear()
    _log('Using skinning tool (0x%X)...' % tool.Serial)
    Items.UseItem(tool.Serial)
    _log('Waiting for target cursor...')
    if not Target.WaitForTarget(3000, False):
        _log("Target cursor never appeared for 0x%X — skipping." % corpse.Serial, colors['yellow'])
        return False

    _log('Targeting corpse 0x%X...' % corpse.Serial)
    Target.TargetExecute(corpse.Serial)
    _log('Waiting %dms for skin action to complete...' % SKIN_WAIT_MS)
    Misc.Pause(SKIN_WAIT_MS)

    for phrase in CANT_SKIN_PHRASES:
        if Journal.Search(phrase):
            _log('Cannot skin "%s": %s' % (corpse.Name, phrase), colors['yellow'])
            return False

    _log('Skinned "%s" (0x%X).' % (corpse.Name, corpse.Serial), colors['green'])
    return True


SCISSORS_ID = 0x0F9F


def find_scissors():
    """Return scissors from the player's backpack, or None."""
    return Items.FindByID(SCISSORS_ID, -1, Player.Backpack.Serial)


def cut_hides_in_backpack(scissors):
    """
    Use scissors on every raw hide stack in the player's backpack.
    Raw hides (0x1079) become cut leather (0x1081) after cutting.
    Call this before transferring to the beetle so only cut leather is stored.

    Retries on "You must wait" server rejection to avoid action queuing.

    Input:
        scissors -- Item object
    """
    raw_hide_id = 0x1079
    _log('Testing if findbyid is an action')
    hide = Items.FindByID(raw_hide_id, -1, Player.Backpack.Serial)
    _log('server action>?')
    hide = Items.FindByID(raw_hide_id, -1, Player.Backpack.Serial)

    while hide is not None:
        _log('Cutting %dx raw hide (0x%X) with scissors...' % (hide.Amount, hide.Serial))
        for attempt in range(5):
            Journal.Clear()
            _log('Using scissors (0x%X), attempt %d/5...' % (scissors.Serial, attempt + 1))
            Items.UseItem(scissors.Serial)
            _log('Waiting for target cursor...')
            if not Target.WaitForTarget(3000, False):
                _log("Cut hides: target cursor never appeared.", colors['yellow'])
                return
            _log('Targeting hide stack 0x%X...' % hide.Serial)
            Target.TargetExecute(hide.Serial)
            _log('Waiting %dms for cut action...' % ACTION_DELAY_MS)
            Misc.Pause(ACTION_DELAY_MS)
            if not Journal.Search("You must wait to perform another action."):
                _log('Cut succeeded.', colors['green'])
                break
            _log("Server busy — retry cut %d/5." % (attempt + 1), colors['yellow'])
            Misc.Pause(ACTION_DELAY_MS)
        hide = Items.FindByID(raw_hide_id, -1, Player.Backpack.Serial)
