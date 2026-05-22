'''
Author: TheWarDoctor95
Other Contributors:
Last Contribution By: TheWarDoctor95 - April 26, 2019

Description: Trains Blacksmithy to its cap
'''

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.crafting.blacksmithing import FindBlacksmithTool, blacksmithCraftables
from glossary.crafting.tinkering import FindTinkeringTool
from glossary.colors import colors
from utilities.items import FindItem, FindNumberOfItems
from utilities.gumps import GumpSelection

BLACKSMITH_GUMP_ID   = 2653346093   # confirmed from gump log (0x9e26d92d)
MAKE_LAST_BTN        = 21           # confirmed from macro recording
SMELT_BTN            = 14           # confirmed from smelt macro recording

# Smith's hammer via tinkering — confirmed from macro recording
HAMMER_ITEM_ID       = 0x13E3
HAMMER_CRAFT_GUMP_ID = 2653346093
HAMMER_CRAFT_PATH    = (
    GumpSelection(2653346093, 15),  # Tools category
    GumpSelection(2653346093, 93),  # smith's hammer
)

INGOT_ID      = 0x1BF2
PAUSE_MOVE    = 1200
LOW_INGOTS    = 30    # pull from materials box when backpack drops below this
REFILL_INGOTS = 150   # how many ingots to pull each refill

RESOURCE_FAIL_PHRASES = [
    'You do not have sufficient',
    'not enough',
    'insufficient',
    'You do not have the',
]

_tools_box     = None  # set at runtime via prompt
_materials_box = None  # set at runtime via prompt


def _prompt_container(label):
    Misc.SendMessage('[smith] Target the %s:' % label, colors['cyan'])
    serial = Target.PromptTarget('Target the %s:' % label)
    if not serial or serial == 0:
        return None
    box = Items.FindBySerial(int(serial))
    if box is None:
        Misc.SendMessage('[smith] Could not find that container.', colors['red'])
    return box


def prompt_tools_box():
    global _tools_box
    _tools_box = _prompt_container('TOOLS container (smith\'s hammers)')
    return _tools_box


def prompt_materials_box():
    global _materials_box
    _materials_box = _prompt_container('MATERIALS container (ingots)')
    return _materials_box


def transfer_colored_ingots_to_box():
    """Move any non-plain-iron ingots (hue != 0) from backpack to _materials_box."""
    if _materials_box is None:
        return
    moved = 0
    stack = Items.FindByID(INGOT_ID, -1, Player.Backpack.Serial)
    while stack is not None:
        if stack.Hue != 0:
            Items.Move(stack, _materials_box, stack.Amount)
            Misc.Pause(PAUSE_MOVE)
            moved += stack.Amount
        stack = Items.FindByID(INGOT_ID, -1, Player.Backpack.Serial)
        if stack is not None and stack.Hue == 0:
            break
    if moved:
        Misc.SendMessage('[smith] Moved %d colored ingot(s) to materials box.' % moved, colors['cyan'])


def pull_ingots(amount_needed):
    """Pull ingots from _materials_box into backpack until we have enough."""
    if _materials_box is None:
        Misc.SendMessage('[smith] pull_ingots: no materials box set.', colors['red'])
        return
    Items.UseItem(_materials_box.Serial)
    Items.WaitForContents(_materials_box, 3000)
    Misc.Pause(600)
    have = FindNumberOfItems(INGOT_ID, Player.Backpack)[INGOT_ID]
    stack = Items.FindByID(INGOT_ID, 0x0000, _materials_box.Serial)
    while stack is not None and have < amount_needed:
        pull = min(stack.Amount, amount_needed - have)
        Items.Move(stack, Player.Backpack, pull)
        Misc.Pause(PAUSE_MOVE)
        have = FindNumberOfItems(INGOT_ID, Player.Backpack)[INGOT_ID]
        stack = Items.FindByID(INGOT_ID, 0x0000, _materials_box.Serial)
    Misc.SendMessage('[smith] Backpack: %d iron ingots.' % have, colors['cyan'])


def get_smith_tool():
    """Return a blacksmithing tool from backpack, pulling from _tools_box or crafting if needed."""
    tool = FindBlacksmithTool(Player.Backpack)
    if tool is not None:
        return tool

    if _tools_box is not None:
        for attempt in range(1, 4):
            Journal.Clear()
            Items.UseItem(_tools_box)
            Items.WaitForContents(_tools_box, 3000)
            Misc.Pause(600)
            if not Journal.Search('You must wait'):
                break
            Misc.SendMessage('[smith] Server busy – retry %d/3.' % attempt, colors['yellow'])
            Misc.Pause(1500)
        spare = FindBlacksmithTool(_tools_box)
        if spare is not None:
            Items.Move(spare, Player.Backpack, 1)
            Misc.Pause(PAUSE_MOVE)
            return FindBlacksmithTool(Player.Backpack)
        Misc.SendMessage('[smith] Tools box empty — crafting a hammer.', colors['yellow'])

    return craft_smith_hammer()


def craft_smith_hammer():
    """Craft a smith's hammer using tinker's tools via the tinkering gump."""
    tinkering_tool = FindTinkeringTool(Player.Backpack)
    if tinkering_tool is None and _tools_box is not None:
        Items.UseItem(_tools_box)
        Items.WaitForContents(_tools_box, 3000)
        Misc.Pause(600)
        tinkering_tool = FindTinkeringTool(_tools_box)
        if tinkering_tool is not None:
            Items.Move(tinkering_tool, Player.Backpack, 1)
            Misc.Pause(PAUSE_MOVE)
            tinkering_tool = FindTinkeringTool(Player.Backpack)
    if tinkering_tool is None:
        Misc.SendMessage('[smith] No tinker\'s tools found — cannot craft hammer.', colors['red'])
        return None

    # Close any open gump (e.g. blacksmithing gump still open) before switching to tinkering
    if Gumps.HasGump():
        Gumps.SendAction(int(Gumps.CurrentGump()), 0)
        Misc.Pause(600)

    Misc.SendMessage('[smith] Crafting smith\'s hammer...', colors['cyan'])
    before = {item.Serial for item in (Player.Backpack.Contains or [])}
    Items.UseItem(tinkering_tool.Serial)
    for _ in range(50):
        if Gumps.HasGump():
            break
        Misc.Pause(100)
    else:
        Misc.SendMessage('[smith] Tinkering gump did not open.', colors['red'])
        return None
    tinkering_gump_id = Gumps.CurrentGump()
    Misc.SendMessage('[smith] Tinkering gump ID: %s' % tinkering_gump_id, colors['cyan'])
    Misc.Pause(300)
    for i, step in enumerate(HAMMER_CRAFT_PATH):
        Gumps.SendAction(tinkering_gump_id, step.buttonID)
        if i < len(HAMMER_CRAFT_PATH) - 1:
            Misc.Pause(500)
    Misc.Pause(1000)

    for item in (Player.Backpack.Contains or []):
        if item.Serial not in before and item.ItemID == HAMMER_ITEM_ID:
            Misc.SendMessage('[smith] Crafted hammer: %s.' % item.Name, colors['green'])
            return item

    Misc.SendMessage('[smith] Hammer craft did not produce expected item.', colors['red'])
    return None


def _open_smelt_gump(tool):
    """Open the blacksmithing gump with retry for tool recharge. Returns True on success."""
    for _ in range(5):
        Journal.Clear()
        Items.UseItem(tool.Serial)
        if Gumps.WaitForGump(BLACKSMITH_GUMP_ID, 3000):
            return True
        if Journal.Search('You must wait'):
            Misc.Pause(2000)
        else:
            break
    Misc.SendMessage('[smith] Smelt gump did not open.', colors['red'])
    return False


def SmeltItems(itemID):
    if SMELT_BTN is None:
        return True  # button not yet confirmed — skip silently

    tool = get_smith_tool()
    if tool is None:
        Misc.SendMessage('[smith] Ran out of tools!', colors['red'])
        return False

    itemToSmelt = FindItem(itemID, Player.Backpack)
    if itemToSmelt is None:
        Misc.SendMessage('[smith] SmeltItems: nothing found with itemID 0x%X' % itemID, colors['yellow'])
        return True

    # Close any open gump so the smelt gump opens in a clean state
    if Gumps.HasGump():
        Gumps.SendAction(BLACKSMITH_GUMP_ID, 0)
        Misc.Pause(500)

    if not _open_smelt_gump(tool):
        return False

    while itemToSmelt is not None:
        tool = Items.FindBySerial(tool.Serial)
        if tool is None:
            tool = get_smith_tool()
            if tool is None:
                Misc.SendMessage('[smith] Ran out of tools!', colors['red'])
                return False

        # Re-open if the gump closed between smelt actions
        if not Gumps.HasGump():
            if not _open_smelt_gump(tool):
                return False

        Target.Cancel()
        Misc.Pause(200)
        Gumps.SendAction(BLACKSMITH_GUMP_ID, SMELT_BTN)
        if not Target.WaitForTarget(3000, False):
            Misc.SendMessage('[smith] Smelt target cursor did not appear.', colors['yellow'])
            break
        Target.TargetExecute(itemToSmelt.Serial)
        Misc.Pause(1200)

        itemToSmelt = FindItem(itemID, Player.Backpack)

    return True


def TrainBlacksmithing():
    if Player.GetRealSkillValue('Blacksmith') == Player.GetSkillCap('Blacksmith'):
        Player.HeadMessage(colors['green'], 'Your Blacksmithy is already at its skill cap!')
        return

    tool = get_smith_tool()
    if tool is None:
        Misc.SendMessage('[smith] No tools found and could not craft one — stopping.', colors['red'])
        return

    Timer.Create('smith_msg', 1)
    while not Player.IsGhost and Player.GetRealSkillValue('Blacksmith') < Player.GetSkillCap('Blacksmith'):
        tool = Items.FindBySerial(tool.Serial)
        if tool is None:
            tool = get_smith_tool()
            if tool is None:
                Misc.SendMessage('[smith] Ran out of tools and could not replenish — stopping.', colors['red'])
                break

        skill = Player.GetRealSkillValue('Blacksmith')
        if skill < 40.0:
            Player.HeadMessage(colors['red'], 'Use gold to train with an NPC')
            break
        elif skill < 45.0:
            recommended = 'mace'
        elif skill < 50.0:
            recommended = 'maul'
        elif skill < 55.0:
            recommended = 'cutlass'
        elif skill < 80.0:
            recommended = 'war hammer'
        elif skill < 90.0:
            recommended = 'platemail gorget'
        else:
            recommended = 'soul glaive'

        item_info = blacksmithCraftables[recommended]
        if not Timer.Check('smith_msg'):
            Misc.SendMessage('[smith] %.1f skill — make: %s' % (skill, recommended), colors['cyan'])
            Player.HeadMessage(colors['cyan'], recommended)
            Timer.Create('smith_msg', 15000)

        if item_info.itemID is not None and Player.Weight >= Player.MaxWeight - 30:
            Misc.SendMessage('[smith] Backpack heavy — smelting before next craft.', colors['yellow'])
            if Gumps.HasGump():
                Gumps.SendAction(BLACKSMITH_GUMP_ID, 0)
                Misc.Pause(500)
            SmeltItems(item_info.itemID)
            continue

        if FindNumberOfItems(INGOT_ID, Player.Backpack)[INGOT_ID] < LOW_INGOTS:
            Misc.SendMessage('[smith] Ingots low — pulling from materials box.', colors['yellow'])
            pull_ingots(REFILL_INGOTS)

        # Open the gump only when it isn't already open
        if not Gumps.HasGump():
            for _ in range(5):
                Journal.Clear()
                Items.UseItem(tool.Serial)
                if Gumps.WaitForGump(BLACKSMITH_GUMP_ID, 3000):
                    break
                if Journal.Search('You must wait'):
                    Misc.Pause(2000)
                else:
                    break
            if not Gumps.HasGump():
                Misc.SendMessage('[smith] Crafting gump did not open — stopping.', colors['red'])
                return

        Journal.Clear()
        before = Items.ContainerCount(Player.Backpack.Serial, item_info.itemID, -1)
        for i, step in enumerate(item_info.gumpPath):
            Gumps.SendAction(step.gumpID, step.buttonID)
            if i < len(item_info.gumpPath) - 1:
                Misc.Pause(500)
        Misc.Pause(1000)

        after = Items.ContainerCount(Player.Backpack.Serial, item_info.itemID, -1)
        if after <= before:
            if (Journal.Search('cannot hold more weight') or
                    Journal.Search('cannot hold more items') or
                    Journal.Search('cannot hold any more') or
                    Player.Weight >= Player.MaxWeight - 5):
                Misc.SendMessage('[smith] Backpack overweight — smelting.', colors['yellow'])
                SmeltItems(item_info.itemID)
                continue
            Misc.SendMessage('[smith] Could not craft %s — check resources.' % recommended, colors['yellow'])
            Player.HeadMessage(colors['yellow'], 'craft failed: ' + recommended)
            Misc.Pause(4000)
            continue

        gump_lines = [str(l).lower() for l in (Gumps.LastGumpGetLineList() or [])]

        if any('you have worn out your tool' in l for l in gump_lines):
            Misc.SendMessage('[smith] Tool worn out — replacing.', colors['yellow'])
            Gumps.SendAction(BLACKSMITH_GUMP_ID, 0)
            Misc.Pause(500)
            tool = get_smith_tool()
            if tool is None:
                break

        if any(any(p.lower() in l for p in RESOURCE_FAIL_PHRASES) for l in gump_lines):
            Misc.SendMessage('[smith] Out of resources — pulling from materials box.', colors['yellow'])
            pull_ingots(50)
            if FindNumberOfItems(INGOT_ID, Player.Backpack)[INGOT_ID] < item_info.resourcesNeeded.get('ingots', 0):
                Misc.SendMessage('[smith] Materials box empty — stopping.', colors['red'])
                return
            continue

# Start Blacksmithing training
prompt_tools_box()
prompt_materials_box()
transfer_colored_ingots_to_box()
TrainBlacksmithing()
