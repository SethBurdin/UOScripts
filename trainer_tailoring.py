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

MATERIALS_CHEST_SERIAL = 0x40040A7E  # serial of the chest holding cloth/leather
TOOLS_BOX_SERIAL       = 0x400EC30D           # serial of the box holding spare sewing kits; None = disable
SEWING_KIT_ID          = 0x0F9D     # item type ID for sewing kit
LOG_FILE               = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local', 'trainer_tailoring.log')
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

CRAFT_GUMP_ID         = 2653346093
GUMP_WAIT_MS          = 2500   # ms to wait for the sewing kit gump to open
CRAFT_WAIT_MS         = 1000   # ms to wait after clicking the craft button
ACTION_DELAY_MS       = 900    # ms between general actions
SKILL_CAP             = None   # set at runtime from Player.GetSkillCap
SCISSORS_ID           = 0x0F9F  # item type ID for scissors
FORCE_CLOAK_UNTIL     = 53.0  # craft cloaks exclusively until this skill level
WEIGHT_PULL_THRESHOLD = 0.2   # pull a full PULL_AMOUNT batch when below this weight fraction

# How many units of material to pull from chest per batch restock
PULL_AMOUNT = 100

CRAFT_FAIL_PHRASES = [
    'You do not have sufficient',
    'not enough',
    'insufficient',
]

# Cloth bolt IDs — verify with Object Inspector if your shard differs
CLOTH_BOLT_IDS = [0x0F95]  # bolt of cloth (confirmed via Object Inspector)

# Raw hide ID — cut with scissors to produce pieces of leather (0x1081)
HIDE_IDS = [0x1079]  # piles of hides, color 0x0000

# Item IDs for the raw materials used by tailoringCraftables
MATERIAL_IDS = {
    'cloth':   cloth['cut cloth'].itemID,       # 0x1767
    'leather': cloth['pieces of leather'].itemID, # 0x1081
}

# Set of item IDs that were crafted by tailoring — used for recycling.
# Raw material IDs are excluded so the recycler never cuts up cloth/leather needed for crafting.
_MATERIAL_ID_SET = set(MATERIAL_IDS.values())
_TAILORING_ITEM_IDS = set(
    item.itemID for item in tailoringCraftables.values()
    if item.itemID is not None and item.itemID not in _MATERIAL_ID_SET
)

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
    GAIN_WINDOW = 7.5   # skill points above minSkill where gains are still good (Outlands formula)

    craftable_items = [
        item for item in tailoringCraftables.values()
        if item.minSkill <= skill
        and all(k in MATERIAL_IDS for k in item.resourcesNeeded)
    ]
    if not craftable_items:
        return None

    in_window = [item for item in craftable_items if skill <= item.minSkill + GAIN_WINDOW]

    if in_window:
        # Hardest item in the gain window (highest minSkill), cheapest cost as tiebreaker
        best_skill = max(item.minSkill for item in in_window)
        candidates = [item for item in in_window if item.minSkill == best_skill]
        return min(candidates, key=lambda item: sum(item.resourcesNeeded.values()))
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
    if Gumps.HasGump():
        Misc.Pause(1200)
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


def count_in_backpack(item_id, color=-1):
    '''Returns total count of item_id in the player backpack (all nested containers).'''
    return Items.ContainerCount(Player.Backpack.Serial, item_id, color, True)


def _cut_cloth_bolts():
    '''Use scissors on every cloth bolt in the backpack to produce cut cloth.'''
    scissors = Items.FindByID(SCISSORS_ID, -1, Player.Backpack.Serial)
    if scissors is None:
        return
    if Gumps.HasGump():
        Misc.Pause(1200)
    for bolt_id in CLOTH_BOLT_IDS:
        bolt = Items.FindByID(bolt_id, -1, Player.Backpack.Serial)
        while bolt is not None:
            Items.UseItem(scissors)
            if not Target.WaitForTarget(3000):
                log('Target prompt did not appear while cutting cloth.', 'warn')
                return
            Target.TargetExecute(bolt.Serial)
            Misc.Pause(ACTION_DELAY_MS)
            bolt = Items.FindByID(bolt_id, -1, Player.Backpack.Serial)


def _cut_hides():
    '''Use scissors on every pile of hides (0x1079) in the backpack to produce leather (0x1081).'''
    scissors = Items.FindByID(SCISSORS_ID, -1, Player.Backpack.Serial)
    if scissors is None:
        return
    if Gumps.HasGump():
        Misc.Pause(1200)
    for hide_id in HIDE_IDS:
        hide = Items.FindByID(hide_id, -1, Player.Backpack.Serial)
        while hide is not None:
            Items.UseItem(scissors)
            if not Target.WaitForTarget(3000):
                log('Target prompt did not appear while cutting hides.', 'warn')
                return
            Target.TargetExecute(hide.Serial)
            Misc.Pause(ACTION_DELAY_MS)
            hide = Items.FindByID(hide_id, -1, Player.Backpack.Serial)


def _make_combined_cloth():
    '''Combine all available cut cloth into combined cloth via the Materials gump.'''
    craftable = tailoringCraftables.get('combined cloth')
    if craftable is None:
        return
    log('Combining cut cloth...', 'info')
    tool = get_sewing_kit()
    if tool is not None:
        craft_item(tool, craftable)
    # Navigate to Hats so the next craft_item call starts on the right tab
    if Gumps.HasGump() and int(Gumps.CurrentGump()) == CRAFT_GUMP_ID:
        Gumps.SendAction(CRAFT_GUMP_ID, 8)
        Misc.Pause(1500)


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

    # For leather, only count normal (color 0x0000) to avoid colored grades fooling the check
    leather_color = 0x0000 if resource_key == 'leather' else -1
    have = count_in_backpack(item_id, leather_color)
    if have >= amount_needed:
        return True

    log('Need %d more %s — pulling from chest.' % (amount_needed - have, resource_key), 'info')

    if resource_key == 'cloth':
        for bolt_id in CLOTH_BOLT_IDS:
            bolt = Items.FindByID(bolt_id, -1, MATERIALS_CHEST_SERIAL)
            if bolt is not None:
                Items.Move(bolt, Player.Backpack, min(4, bolt.Amount))
                Misc.Pause(ACTION_DELAY_MS)
                break
        _cut_cloth_bolts()
        _make_combined_cloth()
    elif resource_key == 'leather':
        pulled = False
        for hide_id in HIDE_IDS:
            hide = Items.FindByID(hide_id, 0x0000, MATERIALS_CHEST_SERIAL)
            if hide is not None:
                Misc.Pause(ACTION_DELAY_MS)
                Items.Move(hide, Player.Backpack, min(PULL_AMOUNT // 2, hide.Amount))
                Misc.Pause(ACTION_DELAY_MS)
                _cut_hides()
                pulled = True
                break
        if not pulled:
            # Chest has pre-cut leather — pull it directly
            mat = Items.FindByID(item_id, 0x0000, MATERIALS_CHEST_SERIAL)
            if mat is None:
                log('No leather or hides found in chest.', 'error')
                return False
            Misc.Pause(ACTION_DELAY_MS)
            Items.Move(mat, Player.Backpack, min(PULL_AMOUNT, mat.Amount))
            Misc.Pause(ACTION_DELAY_MS)
    else:
        mat = Items.FindByID(item_id, -1, MATERIALS_CHEST_SERIAL)
        if mat is None:
            log('No %s found in chest.' % resource_key, 'error')
            return False
        Items.Move(mat, Player.Backpack, min(amount_needed - have, mat.Amount))
        Misc.Pause(ACTION_DELAY_MS)

    have_after = count_in_backpack(item_id, leather_color)
    if have_after >= amount_needed:
        log('Materials ready: %d %s in pack.' % (have_after, resource_key), 'ok')
        return True

    log('Not enough %s: need %d, have %d.' % (resource_key, amount_needed, have_after), 'warn')
    return False


def get_sewing_kit():
    '''
    Returns a sewing kit from the backpack, pulling one from TOOLS_BOX_SERIAL if needed.
    '''
    kit = Items.FindByID(SEWING_KIT_ID, -1, Player.Backpack.Serial)
    if kit is not None:
        return kit
    if TOOLS_BOX_SERIAL is None:
        return None
    box = Items.FindBySerial(TOOLS_BOX_SERIAL)
    if box is None:
        log('Tools box (0x%X) not found.' % TOOLS_BOX_SERIAL, 'error')
        return None
    if Gumps.HasGump():
        Misc.Pause(1200)
    Items.UseItem(box)
    Items.WaitForContents(box, 3000)
    Misc.Pause(600)
    spare = Items.FindByID(SEWING_KIT_ID, -1, TOOLS_BOX_SERIAL)
    if spare is None:
        log('No sewing kits in tools box (0x%X).' % TOOLS_BOX_SERIAL, 'error')
        return None
    for _ in range(3):
        Items.Move(spare, Player.Backpack, 1)
        Misc.Pause(ACTION_DELAY_MS)
        kit = Items.FindByID(SEWING_KIT_ID, -1, Player.Backpack.Serial)
        if kit is not None:
            return kit
        Misc.Pause(2000)  # server may be busy ("you must wait") — give it a moment
        spare = Items.FindByID(SEWING_KIT_ID, -1, TOOLS_BOX_SERIAL)
        if spare is None:
            log('No sewing kits in tools box (0x%X).' % TOOLS_BOX_SERIAL, 'error')
            return None
    return None


def craft_item(tool, craftable):
    '''
    Opens the sewing kit gump and navigates to the given craftable.
    Returns True if the craft button was clicked successfully.
    '''
    expected_gump = craftable.gumpPath[0].gumpID

    if not (Gumps.HasGump() and int(Gumps.CurrentGump()) == expected_gump):
        Items.UseItem(tool)
        if not Gumps.WaitForGump(expected_gump, GUMP_WAIT_MS):
            log('Sewing kit gump did not open.', 'error')
            return False

    Journal.Clear()
    for i, step in enumerate(craftable.gumpPath):
        Gumps.SendAction(step.gumpID, step.buttonID)
        if i < len(craftable.gumpPath) - 1:
            Misc.Pause(1200)  # fixed pause — avoids stale WaitForGump events from prior craft

    Gumps.WaitForGump(expected_gump, CRAFT_WAIT_MS)
    Misc.Pause(1000)

    lines = Gumps.LastGumpGetLineList() or []
    for line in lines:
        if any(phrase.lower() in line.lower() for phrase in CRAFT_FAIL_PHRASES):
            log('Craft failed: %s' % line.strip(), 'warn')
            return False

    return True


# ---------------------------------------------------------------------------
# Main — training loop
# ---------------------------------------------------------------------------

SKILL_CAP  = Player.GetSkillCap('Tailoring')
log('Starting tailoring trainer (target: %.1f).' % SKILL_CAP, 'info')

# Open chest once so FindByID can read its contents without reopening each pull
_chest = Items.FindBySerial(MATERIALS_CHEST_SERIAL)
if _chest is None:
    log('Materials chest (0x%X) not found — are you in range?' % MATERIALS_CHEST_SERIAL, 'error')
else:
    Items.UseItem(_chest)
    Items.WaitForContents(_chest, 3000)
    Misc.Pause(600)

crafts      = 0
last_item   = None
consec_fail = 0

while True:
    skill = Player.GetSkillValue('Tailoring')

    if skill >= SKILL_CAP:
        log('Skill cap %.1f reached (current: %.1f) — done.' % (SKILL_CAP, skill), 'ok')
        break

    tool = get_sewing_kit()
    if tool is None:
        log('No sewing kit available — stopping.' , 'error')
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

    # Recycle any finished crafted items before pulling more materials
    if any(Items.FindByID(iid, -1, Player.Backpack.Serial) is not None for iid in _TAILORING_ITEM_IDS):
        recycle_crafted_items()

    # Batch restock when pack is light enough to carry more
    if Player.MaxWeight > 0 and float(Player.Weight) / Player.MaxWeight < WEIGHT_PULL_THRESHOLD:
        pull_materials_from_chest(resource_key, PULL_AMOUNT)

    if not pull_materials_from_chest(resource_key, amount_needed):
        log('Out of %s — recycling crafted items and retrying.' % resource_key, 'warn')
        if recycle_crafted_items() == 0 or not pull_materials_from_chest(resource_key, amount_needed):
            log('Still out of %s after recycling — stopping.' % resource_key, 'error')
            break

    if not craft_item(tool, craftable):
        consec_fail += 1
        if consec_fail >= 3:
            log('3 consecutive craft failures — stopping to prevent loop.', 'error')
            break
        log('Craft failed — restocking %s.' % resource_key, 'warn')
        pull_materials_from_chest(resource_key, amount_needed)
        continue

    consec_fail = 0
    crafts += 1
    recycle_if_overweight()

log('Session complete. Crafts this run: %d. Final skill: %.1f.' % (crafts, Player.GetSkillValue('Tailoring')), 'info')
