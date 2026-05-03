'''
Skinning Script
---------------
Runs with the player mounted on a pack beetle.
Scans nearby corpses, skins them, and transfers the leather to the beetle.

Step 1  - Scan corpses, determine which are skinnable.
Step 2  - Use skinning knife / dagger to skin each corpse.
Step 3  - Identify the player's pack beetle.
Step 4  - Transfer leather from each corpse to the beetle.
'''

try:
    from razorenhanced_stubs import *
except:
    pass

from System.Collections.Generic import List
from System import Int32
from Scripts.glossary.items.tools import tools
from Scripts.glossary.items.cloth import cloth
from Scripts.utilities.items import FindItem

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCAN_RANGE        = 3     # tiles from player to check for corpses
SCAN_INTERVAL_MS  = 500   # ms between scan passes (used in future loop)
ACTION_DELAY_MS   = 900   # ms delay between all actions
SKIN_WAIT_MS      = 2500  # ms to wait after using the skinning tool
MOVE_PAUSE_MS     = ACTION_DELAY_MS  # ms between each item move to the beetle

DEBUG = True

# Body ID for giant beetle (pack mount)
BEETLE_BODY_ID   = 0x0317
BEETLE_SERIAL    = 0x0000476D

# Item IDs for hides / leather that appear on / from a corpse
HIDE_ITEM_IDS = [
    cloth['piles of hides'].itemID,    # 0x1079  raw hides on corpse
    cloth['pieces of leather'].itemID, # 0x1081  cut leather after skinning
]

# Dragon scale IDs — confirm against in-game SingleClick if wrong on this shard
SCALE_ITEM_IDS = [0x26B4, 0x26B5, 0x26B6, 0x26B7, 0x26B8, 0x26B9]

RESOURCE_ITEM_IDS = set(HIDE_ITEM_IDS + SCALE_ITEM_IDS)

# ---------------------------------------------------------------------------
# Logging helper (inline — avoids module import issues in IronPython)
# ---------------------------------------------------------------------------

_HUE = {'info': 90, 'ok': 65, 'warn': 52, 'error': 1100}  # cyan/green/yellow/red

def log(msg, level='info'):
    if DEBUG:
        Misc.SendMessage('[SKIN] ' + str(msg), _HUE.get(level, 90))

# Accept either a skinning knife or a dagger
SKINNING_TOOL_IDS = [
    tools['skinning knife'].itemID,
    tools['dagger'].itemID,
]

# Journal fragments that mean the corpse cannot be skinned
CANT_SKIN_JOURNAL = [
    'you cannot',
    'nothing to skin',
    'already been skinned',
    'cannot skin',
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_skinning_tool():
    '''Return the first usable skinning tool in the backpack, or None.'''
    for tool_id in SKINNING_TOOL_IDS:
        tool = FindItem(tool_id, Player.Backpack)
        if tool is not None:
            return tool
    return None


def _is_humanoid_corpse(corpse):
    '''
    Best-effort check: return True if the corpse looks like a player / NPC
    human corpse that cannot be skinned.

    Player corpses are typically named "the body of <name>" or
    "the remains of <name>".  Creature corpses are usually just
    "a corpse" or carry the creature's name without those prefixes.
    '''
    name = (corpse.Name or '').lower()
    if 'body of'    in name: return True
    if 'remains of' in name: return True
    return False


# ---------------------------------------------------------------------------
# Step 1 - Scan corpses
# ---------------------------------------------------------------------------

def scan_nearby_corpses(scan_range=SCAN_RANGE):
    '''
    Find all corpses within *scan_range* tiles and classify each as
    skinnable or not.

    Returns:
        skinnable  -- list of Item objects that look like creature corpses
        skippable  -- list of Item objects that look like human/player corpses
    '''
    corpse_filter          = Items.Filter()
    corpse_filter.Enabled  = True
    corpse_filter.IsCorpse = 1
    corpse_filter.RangeMin = 0
    corpse_filter.RangeMax = scan_range

    all_corpses = Items.ApplyFilter(corpse_filter)

    skinnable = []
    skippable = []

    for corpse in all_corpses:
        name = corpse.Name or '(unnamed)'

        # Fetch properties so we can log richer info
        Items.WaitForProps(corpse.Serial, 1500)
        props = Items.GetPropStringList(corpse.Serial) or []
        prop_summary = ' | '.join(props[:3]) if props else '(no props)'

        if _is_humanoid_corpse(corpse):
            skippable.append(corpse)
            log('Skip  (human): "%s" serial=0x%X  props: %s'
                     % (name, corpse.Serial, prop_summary), 'warn')
        else:
            skinnable.append(corpse)
            log('Found (creature): "%s" serial=0x%X  props: %s'
                   % (name, corpse.Serial, prop_summary), 'ok')

    log('Scan complete — %i skinnable, %i skipped  (range=%i)'
             % (len(skinnable), len(skippable), scan_range))

    return skinnable, skippable


# ---------------------------------------------------------------------------
# Step 2 - Skin a corpse
# ---------------------------------------------------------------------------

def skin_corpse(tool, corpse):
    '''
    Use *tool* on *corpse*.  Returns True if skinning produced resources,
    False if the server rejected the action (already skinned, wrong corpse, etc.).
    '''
    Journal.Clear()

    Items.UseItem(tool.Serial)
    if not Target.WaitForTarget(3000, False):
        log('Target cursor never appeared for corpse 0x%X — skipping.' % corpse.Serial, 'warn')
        return False

    Target.TargetExecute(corpse.Serial)

    # Give the server time to respond and send journal feedback
    Misc.Pause(SKIN_WAIT_MS)

    for phrase in CANT_SKIN_JOURNAL:
        if Journal.Search(phrase):
            log('Cannot skin "%s" (journal: "%s").' % (corpse.Name, phrase), 'warn')
            return False

    log('Skinned "%s" (serial=0x%X).' % (corpse.Name, corpse.Serial), 'ok')
    return True


# ---------------------------------------------------------------------------
# Step 3 - Identify the pack beetle
# ---------------------------------------------------------------------------

def find_beetle():
    '''Returns the Mobile object for the player's pack beetle using the hardcoded serial.'''
    beetle = Mobiles.FindBySerial(BEETLE_SERIAL)
    if beetle is None:
        log('Beetle not found (serial=0x%X). Is it in range?' % BEETLE_SERIAL, 'error')
        return None
    log('Beetle: "%s" serial=0x%X' % (beetle.Name, beetle.Serial), 'ok')
    return beetle


# ---------------------------------------------------------------------------
# Step 4 - Transfer leather from corpse to beetle
# ---------------------------------------------------------------------------

def transfer_resources(corpse, beetle):
    '''
    Dismounts, moves all hides and dragon scales from *corpse* to the beetle,
    then remounts.  Returns the total number of stacks moved.
    '''
    mounted = Player.Mount is not None
    if mounted:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(ACTION_DELAY_MS)

    Items.UseItem(corpse.Serial)
    Items.WaitForContents(corpse.Serial, 2500)
    Misc.Pause(ACTION_DELAY_MS)

    moved = 0
    for item in list(corpse.Contains):
        if item.ItemID in RESOURCE_ITEM_IDS:
            log('Moving %ix %s (0x%04X) to beetle.' % (item.Amount, item.Name, item.ItemID))
            Items.Move(item, beetle.Serial, 0)
            Misc.Pause(MOVE_PAUSE_MS)
            moved += 1

    if moved == 0:
        log('No hides or scales on corpse 0x%X after skinning.' % corpse.Serial, 'warn')
    else:
        log('%i stack(s) transferred to beetle.' % moved, 'ok')

    if mounted:
        Mobiles.UseMobile(beetle.Serial)
        Misc.Pause(ACTION_DELAY_MS)

    return moved


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

log('Script started.')

tool = _find_skinning_tool()

if tool is None:
    log('No skinning knife or dagger found in backpack — aborting.', 'error')
else:
    log('Skinning tool ready: 0x%04X  serial=0x%X' % (tool.ItemID, tool.Serial), 'ok')

    # Dismount first so the beetle is visible as a nearby mobile
    if Player.Mount is not None:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(ACTION_DELAY_MS)

    beetle = find_beetle()
    if beetle is None:
        log('No pack beetle found — aborting.', 'error')
    else:
        skinnable, skippable = scan_nearby_corpses()

        if not skinnable:
            log('No skinnable corpses in range.', 'warn')
        else:
            log('%i corpse(s) queued for skinning.' % len(skinnable), 'ok')

            for corpse in skinnable:
                if skin_corpse(tool, corpse):
                    transfer_resources(corpse, beetle)
