# ---------------------------------------------------------------------------
# trainer_tailoring.py
# Automatically crafts the most skill-efficient tailor item for the player's
# current skill level.  Pulls materials from a dedicated chest, opens the
# sewing kit gump, and navigates to the correct craft button.
# ---------------------------------------------------------------------------

# IDE IntelliSense only — never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

import datetime
import os

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.crafting.tailoring import tailoringCraftables
from glossary.items.cloth import cloth

# ---------------------------------------------------------------------------
# Config — edit this block
# ---------------------------------------------------------------------------

MATERIALS_CHEST_SERIAL = 0x400ADEF7  # serial of the chest holding cloth/leather
SEWING_KIT_ID          = 0x0F9D     # item type ID for sewing kit
LOG_FILE               = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trainer_tailoring.log')

CRAFT_GUMP_ID   = 949095101
GUMP_WAIT_MS    = 5000   # ms to wait for the sewing kit gump to open
CRAFT_WAIT_MS   = 3000   # ms to wait after clicking the craft button
ACTION_DELAY_MS = 900    # ms between general actions
SKILL_CAP       = 100.0  # stop training at this skill value
SCISSORS_ID     = 0x0F9F  # item type ID for scissors
FORCE_CLOAK_UNTIL = 53.0  # craft cloaks exclusively until this skill level

# How many units of material to pull from chest per trip
PULL_AMOUNT = 100

# Item IDs for the raw materials used by tailoringCraftables
MATERIAL_IDS = {
    'cloth':   cloth['cut cloth'].itemID,       # 0x1767
    'leather': cloth['pieces of leather'].itemID, # 0x1081
}

# Set of item IDs that were crafted by tailoring — used for recycling
_TAILORING_ITEM_IDS = set(item.itemID for item in tailoringCraftables.values() if item.itemID is not None)

# ---------------------------------------------------------------------------
# Inline logger
# ---------------------------------------------------------------------------

_COLORS = {'info': 90, 'ok': 65, 'warn': 52, 'error': 1100}

def log(msg, level='info'):
    Misc.SendMessage('[TAILOR] %s' % msg, _COLORS.get(level, 90))
    if LOG_FILE:
        try:
            ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(LOG_FILE, 'a', encoding='utf-8') as _lf:
                _lf.write('%s  [%-5s] %s\n' % (ts, level.upper(), msg))
        except Exception as _e:
            Misc.SendMessage('[TAILOR] log write failed: %s' % _e, 1100)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pick_best_item(skill):
    '''
    Picks the cheapest craftable item in the active gain window.

    Standard RunUO formula:  chance = (skill - (minSkill - 25)) / 50
      - skill < minSkill          -> cannot attempt (locked)
      - skill in [minSkill, minSkill+12.5] -> 50-75% success, active gain window
      - skill > minSkill + 25     -> 100% success, gains effectively stop

    Strategy:
      1. If FORCE_CLOAK_UNTIL is set and skill < that threshold, always craft cloak.
      2. Must be unlocked: skill >= minSkill
      3. Prefer items still in the gain window: skill <= minSkill + 12.5
      4. Among those, pick the one with the lowest material cost (least waste per attempt)
      5. If nothing is in the window (skill outpaced all items), fall back to
         the highest-minSkill item we can still craft.
    '''
    if FORCE_CLOAK_UNTIL is not None and skill < FORCE_CLOAK_UNTIL:
        cloak = tailoringCraftables.get('cloak')
        if cloak is not None and cloak.minSkill <= skill:
            return cloak
    GAIN_WINDOW = 12.5  # skill points above minSkill where gains are still good

    craftable_items = [item for item in tailoringCraftables.values() if item.minSkill <= skill]
    if not craftable_items:
        return None

    in_window = [item for item in craftable_items if skill <= item.minSkill + GAIN_WINDOW]

    if in_window:
        # Cheapest material cost within the gain window
        return min(in_window, key=lambda item: list(item.resourcesNeeded.values())[0])
    else:
        # All craftable items are "too easy" — pick hardest available as fallback
        return max(craftable_items, key=lambda item: item.minSkill)


def recycle_crafted_items():
    '''
    Uses scissors on every crafted tailoring item in the backpack to cut them
    back into raw materials.  Returns the number of items recycled.
    '''
    scissors = Items.FindByID(SCISSORS_ID, -1, Player.Backpack.Serial)
    if scissors is None:
        log('No scissors (0x%04X) in backpack — cannot recycle.' % SCISSORS_ID, 'error')
        return 0

    recycled = 0
    for item_id in _TAILORING_ITEM_IDS:
        while True:
            item = Items.FindByID(item_id, -1, Player.Backpack.Serial)
            if item is None:
                break
            Items.UseItem(scissors)
            if not Target.WaitForTarget(3000):
                log('Target prompt did not appear during recycle.', 'warn')
                break
            Target.TargetExecute(item.Serial)
            Misc.Pause(ACTION_DELAY_MS)
            recycled += 1

    log('Recycled %d item(s). Weight now %d/%d.' % (recycled, Player.Weight, Player.MaxWeight), 'ok')
    return recycled


def recycle_if_overweight():
    '''Recycles crafted items when the player is overweight.'''
    if Player.Weight <= Player.MaxWeight:
        return
    log('Overweight (%d/%d) — recycling crafted items.' % (Player.Weight, Player.MaxWeight), 'warn')
    recycle_crafted_items()


def count_in_backpack(item_id):
    '''Returns total count of item_id in the player backpack (all nested containers).'''
    return Items.ContainerCount(Player.Backpack.Serial, item_id, -1, True)


def pull_materials_from_chest(resource_key, amount_needed):
    '''
    Ensures at least `amount_needed` of the given resource key are in the
    player's backpack, pulling from the materials chest if necessary.
    Returns True if the backpack has enough afterward, False otherwise.
    '''
    if MATERIALS_CHEST_SERIAL is None:
        log('MATERIALS_CHEST_SERIAL is not set — edit the script.', 'error')
        return False

    item_id = MATERIAL_IDS.get(resource_key)
    if item_id is None:
        log('Unknown resource key: %s' % resource_key, 'error')
        return False

    have = count_in_backpack(item_id)
    if have >= amount_needed:
        return True

    need = amount_needed - have
    log('Need %d more %s — pulling from chest.' % (need, resource_key), 'info')

    chest = Items.FindBySerial(MATERIALS_CHEST_SERIAL)
    if chest is None:
        log('Materials chest (0x%X) not found. Are you in range?' % MATERIALS_CHEST_SERIAL, 'error')
        return False

    Items.UseItem(chest)
    Items.WaitForContents(chest.Serial, 3000)
    Misc.Pause(ACTION_DELAY_MS)

    mat = Items.FindByID(item_id, -1, chest.Serial)
    if mat is None:
        log('No %s found in chest.' % resource_key, 'error')
        return False

    move_qty = min(need, mat.Amount)
    Items.Move(mat, Player.Backpack.Serial, move_qty)
    Misc.Pause(ACTION_DELAY_MS)

    have_after = count_in_backpack(item_id)
    if have_after >= amount_needed:
        log('Materials ready: %d %s in pack.' % (have_after, resource_key), 'ok')
        return True

    log('Not enough %s: need %d, have %d.' % (resource_key, amount_needed, have_after), 'warn')
    return False


def craft_item(tool, craftable):
    '''
    Opens the sewing kit gump and navigates to the given craftable.
    Returns True if the gump was reached and the craft button clicked.
    '''
    Items.UseItem(tool)

    # Poll for any gump — captures the real ID regardless of what CRAFT_GUMP_ID is set to
    waited = 0
    while not Gumps.HasGump() and waited < GUMP_WAIT_MS:
        Misc.Pause(200)
        waited += 200

    if not Gumps.HasGump():
        log('Sewing kit gump did not open.', 'error')
        return False

    actual_id = int(Gumps.CurrentGump())
    if actual_id != CRAFT_GUMP_ID:
        log('Gump ID mismatch: expected %d, got %d. Update CRAFT_GUMP_ID to %d.' % (CRAFT_GUMP_ID, actual_id, actual_id), 'warn')

    for step in craftable.gumpPath:
        Gumps.SendAction(actual_id, step.buttonID)
        Misc.Pause(ACTION_DELAY_MS)
        # Wait for gump to re-render after each nav click (except last)
        if step is not craftable.gumpPath[-1]:
            waited = 0
            while not Gumps.HasGump() and waited < GUMP_WAIT_MS:
                Misc.Pause(200)
                waited += 200
            actual_id = int(Gumps.CurrentGump())

    Misc.Pause(CRAFT_WAIT_MS)
    return True


# ---------------------------------------------------------------------------
# Main — training loop
# ---------------------------------------------------------------------------

log('Starting tailoring trainer (target: %.1f).' % SKILL_CAP, 'info')

crafts     = 0
last_item  = None

while True:
    skill = Player.GetSkillValue('Tailoring')

    if skill >= SKILL_CAP:
        log('Skill cap %.1f reached (current: %.1f) — done.' % (SKILL_CAP, skill), 'ok')
        break

    tool = Items.FindByID(SEWING_KIT_ID, -1, Player.Backpack.Serial)
    if tool is None:
        log('No sewing kit (0x%04X) in backpack — stopping.' % SEWING_KIT_ID, 'error')
        break

    craftable = pick_best_item(skill)
    if craftable is None:
        log('No craftable item for skill %.1f — stopping.' % skill, 'error')
        break

    if craftable.name != last_item:
        log('Skill %.1f — now crafting: %s (minSkill %.1f)' % (skill, craftable.name, craftable.minSkill), 'ok')
        last_item = craftable.name

    resource_key  = list(craftable.resourcesNeeded.keys())[0]
    amount_needed = craftable.resourcesNeeded[resource_key]

    if not pull_materials_from_chest(resource_key, amount_needed):
        log('Out of %s — recycling crafted items and retrying.' % resource_key, 'warn')
        if recycle_crafted_items() == 0 or not pull_materials_from_chest(resource_key, amount_needed):
            log('Still out of %s after recycling — stopping.' % resource_key, 'error')
            break

    if not craft_item(tool, craftable):
        log('Craft failed — stopping.', 'error')
        break

    crafts += 1
    recycle_if_overweight()

log('Session complete. Crafts this run: %d. Final skill: %.1f.' % (crafts, Player.GetSkillValue('Tailoring')), 'info')
