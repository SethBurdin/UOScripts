'''
Trains Carpentry to its skill cap.

Board supply:   pulls REFILL_BOARDS boards from the supply box when the player
                drops below LOW_BOARDS.
Output:         after each craft, the item type is discovered from the backpack
                diff and moved to the output box by ItemID — no hardcoded IDs,
                no full-inventory scan.  Resets automatically when the skill
                tier changes to a new item.
'''

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.crafting.carpentry import FindCarpentryTool, carpentryCraftables
from utilities.items import FindNumberOfItems
from crate_manager import make_new_output

# ── Config ────────────────────────────────────────────────────────────────────
LOW_BOARDS    = 50     # pull more boards when player has fewer than this
REFILL_BOARDS = 200    # how many boards to pull each time
PAUSE_MOVE    = 1200   # ms between Items.Move calls
WEIGHT_BUFFER = 50     # stones below MaxWeight to trigger offload

BOARD_IDS     = [0x1BD7, 0x1BDD]   # plain boards, hue 0 only
MAKE_LAST_BTN = None               # set once known (record a macro pressing Make Last)

# Known item IDs per craft tier.  None = unknown, discovered after first craft.
# Verify with Object Inspector and fill in any that are still None.
TIER_ITEM_IDS = {
    'ballot box':    None,
    'wooden shield': 0x1B7A,
    'bokuto':        None,
    'quarter staff': 0x0E89,
    'gnarled staff': 0x13F8,
}

TOO_MANY_PHRASES = [
    "That container cannot hold any more items",
    "That container cannot hold more weight",
    "Your backpack cannot hold that",
    "There is not enough room",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg, color=None):
    Misc.SendMessage('[carpentry] ' + msg, color or colors['cyan'])


def prompt_container(msg):
    log(msg)
    serial = Target.PromptTarget(msg)
    if not serial or serial == 0:
        return None
    box = Items.FindBySerial(serial)
    if box is None:
        log('Could not find that item.', colors['red'])
    return box


def count_boards():
    total = 0
    for bid in BOARD_IDS:
        total += FindNumberOfItems(bid, Player.Backpack, 0x0000)[bid]
    return total


def journal_too_many():
    return any(Journal.Search(p) for p in TOO_MANY_PHRASES)


def pull_boards(boards_box):
    """Pull up to REFILL_BOARDS plain boards from boards_box into backpack.
    Returns True on success, False if backpack became full mid-pull."""
    remaining = REFILL_BOARDS
    for bid in BOARD_IDS:
        if remaining <= 0:
            break
        stack = Items.FindByID(bid, 0, boards_box.Serial)
        while stack is not None and remaining > 0:
            Journal.Clear()  # clear immediately before the move so only the move result is checked
            Items.Move(stack, Player.Backpack, min(stack.Amount, remaining))
            Misc.Pause(PAUSE_MOVE)
            if journal_too_many():
                return False
            remaining -= min(stack.Amount, remaining)
            stack = Items.FindByID(bid, 0, boards_box.Serial)
    return True


def dump_to_output(output_box, item_id):
    """Move all items of item_id from backpack to output_box.
    If the box fills up, makes one attempt to craft and place a new crate.
    Falls back to dropping on the ground if that also fails.
    Returns (count_moved, current_output_box) — output_box may have changed."""
    if item_id is None:
        return 0, output_box
    moved = 0
    crafted = Items.FindByID(item_id, -1, Player.Backpack.Serial)
    while crafted is not None:
        Journal.Clear()
        Items.Move(crafted, output_box, crafted.Amount)
        Misc.Pause(PAUSE_MOVE)
        if journal_too_many():
            new_box = make_new_output()
            if new_box is not None:
                output_box = new_box
                Journal.Clear()
                Items.Move(crafted, output_box, crafted.Amount)
                Misc.Pause(PAUSE_MOVE)
            if new_box is None or journal_too_many():
                log('Dropping on ground.', colors['red'])
                pos = Player.Position
                Items.MoveOnGround(crafted, crafted.Amount, pos.X + 1, pos.Y, pos.Z)
                Misc.Pause(PAUSE_MOVE)
        moved += 1
        crafted = Items.FindByID(item_id, -1, Player.Backpack.Serial)
    if moved:
        log('Cleared %d item(s).' % moved)
    return moved, output_box


# ── Main training loop ────────────────────────────────────────────────────────

def TrainCarpentry(boards_box, output_box):
    skill = Player.GetRealSkillValue('Carpentry')
    cap   = Player.GetSkillCap('Carpentry')
    log('Carpentry %.1f / %.1f' % (skill, cap))

    if skill >= cap:
        log('Already at skill cap – nothing to do.')
        return

    tool = FindCarpentryTool(Player.Backpack)
    if tool is None:
        log('No carpentry tool found in backpack – stopping.', colors['red'])
        return

    log('Tool: %s (0x%X)' % (tool.Name, tool.Serial))

    current_item_name = None   # name of the item we are currently crafting
    current_item_id   = None   # ItemID discovered after first successful craft

    # ── Startup cleanup ───────────────────────────────────────────────────────
    Items.UseItem(boards_box)
    Items.WaitForContents(boards_box, 3000)
    Misc.Pause(500)
    Items.UseItem(Player.Backpack)
    Items.WaitForContents(Player.Backpack, 3000)
    Misc.Pause(500)
    known_ids = {iid for iid in TIER_ITEM_IDS.values() if iid is not None}
    to_clear = [i for i in (Player.Backpack.Contains or []) if i.ItemID in known_ids]
    if to_clear:
        log('Clearing %d leftover crafted item(s) from previous run.' % len(to_clear))
        for item in to_clear:
            Journal.Clear()
            Items.Move(item, output_box, item.Amount)
            Misc.Pause(PAUSE_MOVE)
            if journal_too_many():
                pos = Player.Position
                Items.MoveOnGround(item, item.Amount, pos.X, pos.Y, pos.Z)
                Misc.Pause(PAUSE_MOVE)

    Journal.Clear()

    while not Player.IsGhost and Player.GetRealSkillValue('Carpentry') < Player.GetSkillCap('Carpentry'):

        # ── Refresh tool ──────────────────────────────────────────────────────
        tool = Items.FindBySerial(tool.Serial)
        if tool is None:
            tool = FindCarpentryTool(Player.Backpack)
            if tool is None:
                log('Ran out of tools – stopping.', colors['red'])
                break

        # ── Weight check ──────────────────────────────────────────────────────
        if Player.Weight >= Player.MaxWeight - WEIGHT_BUFFER:
            log('Heavy (%d/%d) – offloading.' % (Player.Weight, Player.MaxWeight), colors['yellow'])
            _, output_box = dump_to_output(output_box, current_item_id)

        # ── Board supply check ────────────────────────────────────────────────
        boards = count_boards()
        if boards < LOW_BOARDS:
            log('Boards low (%d) – pulling %d.' % (boards, REFILL_BOARDS))
            if not pull_boards(boards_box):
                log('Backpack full during pull – offloading first.', colors['yellow'])
                _, output_box = dump_to_output(output_box, current_item_id)
                if not pull_boards(boards_box):
                    log('Still cannot pull boards – stopping.', colors['red'])
                    break

        # ── Select item to craft ──────────────────────────────────────────────
        skill = Player.GetRealSkillValue('Carpentry')
        if skill < 40.0:
            log('Skill below 40 – use an NPC trainer first.', colors['red'])
            break
        elif skill < 65.0:
            itemToCraft = carpentryCraftables['ballot box']   # TODO: record gump path
        elif skill < 72.0:
            itemToCraft = carpentryCraftables['wooden shield']
        elif skill < 79.0:
            itemToCraft = carpentryCraftables['bokuto']        # TODO: record gump path
        elif skill < 90.0:
            itemToCraft = carpentryCraftables['quarter staff']
        else:
            itemToCraft = carpentryCraftables['gnarled staff']

        # Reset discovered ID when tier changes
        if itemToCraft.name != current_item_name:
            log('Tier: %s' % itemToCraft.name)
            current_item_name = itemToCraft.name
            current_item_id   = TIER_ITEM_IDS.get(itemToCraft.name)

        if count_boards() < itemToCraft.resourcesNeeded.get('boards', 0):
            log('Not enough boards for %s – stopping.' % itemToCraft.name, colors['red'])
            break

        # ── Craft ─────────────────────────────────────────────────────────────
        before = {item.Serial for item in (Player.Backpack.Contains or [])}

        expected_gump = itemToCraft.gumpPath[0].gumpID
        item_btn      = itemToCraft.gumpPath[-1]

        if Gumps.HasGump() and Gumps.CurrentGump() == expected_gump:
            # Gump is still open on the items page from the previous craft — send item button directly.
            Journal.Clear()
            Gumps.SendAction(item_btn.gumpID, item_btn.buttonID)
        else:
            # Gump is closed — open the tool and navigate fully.
            gump_opened = False
            for attempt in range(3):
                Journal.Clear()
                Items.UseItem(tool)
                Misc.Pause(200)
                if Journal.Search('You must wait to perform another action'):
                    log('Server busy – retrying (%d/3).' % (attempt + 1), colors['yellow'])
                    Misc.Pause(1500)
                    continue
                if Gumps.CurrentGump() == expected_gump or Gumps.WaitForGump(expected_gump, 3000):
                    gump_opened = True
                    break
                Misc.Pause(1000)

            if not gump_opened:
                actual = Gumps.CurrentGump()
                log('Gump never opened (expected %d, got %d).' % (expected_gump, actual), colors['red'])
                if Gumps.HasGump():
                    Gumps.CloseGump(actual)
                continue

            Misc.Pause(1000)
            if MAKE_LAST_BTN is not None and current_item_id is not None:
                Gumps.SendAction(expected_gump, MAKE_LAST_BTN)
            else:
                Gumps.SendAction(itemToCraft.gumpPath[0].gumpID, itemToCraft.gumpPath[0].buttonID)
                for path in itemToCraft.gumpPath[1:]:
                    Gumps.WaitForGump(path.gumpID, 3000)
                    Misc.Pause(1000)
                    Gumps.SendAction(path.gumpID, path.buttonID)

        # Wait for craft result — leave gump open on items page for the next craft.
        # Do NOT send button 0: on this gump it hits MAKE LAST, repeating the previous item.
        Gumps.WaitForGump(expected_gump, 5000)
        Misc.Pause(1000)
        Journal.Clear()  # discard late-arriving craft messages before next board pull

        # ── Discover crafted item type from backpack diff ─────────────────────
        if current_item_id is None:
            for item in (Player.Backpack.Contains or []):
                if item.Serial not in before and item.ItemID not in BOARD_IDS:
                    current_item_id = item.ItemID
                    TIER_ITEM_IDS[current_item_name] = current_item_id
                    log('Discovered item type: 0x%04X (%s)' % (current_item_id, current_item_name))
                    break

    _, output_box = dump_to_output(output_box, current_item_id)
    log('Done. Carpentry: %.1f / %.1f' % (
        Player.GetRealSkillValue('Carpentry'), Player.GetSkillCap('Carpentry')))


# ── Entry point ───────────────────────────────────────────────────────────────

boards_box = prompt_container('Target the BOARDS supply container:')
if boards_box is not None:
    output_box = prompt_container('Target the OUTPUT container (for crafted items):')
    if output_box is not None:
        TrainCarpentry(boards_box, output_box)
