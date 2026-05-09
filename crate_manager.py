"""
crate_manager.py
Standalone validation for auto-cycling output containers in train_Carpentry.py.

When the output box fills up (125 items), this module:
  1. Detects the failed transfer via journal
  2. Crafts a large crate with the carpentry tool
  3. Places it on the ground at the player's feet
  4. Returns the new crate as the active output container

Run main() directly to validate each step before wiring into the trainer.
"""

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.crafting.carpentry import FindCarpentryTool, carpentryCraftables

# ── Config ────────────────────────────────────────────────────────────────────
BOARD_IDS      = [0x1BD7, 0x1BDD]
MOVE_PAUSE_MS  = 1200
GUMP_TIMEOUT   = 5000

TOO_MANY_PHRASES = [
    "That container cannot hold any more items",
    "That container cannot hold more weight",
    "Your backpack cannot hold that",
    "There is not enough room",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg, color=None):
    Misc.SendMessage('[crate-mgr] ' + msg, color or colors['cyan'])


def _journal_too_many():
    return any(Journal.Search(p) for p in TOO_MANY_PHRASES)


def _board_count():
    total = 0
    for bid in BOARD_IDS:
        stack = Items.FindByID(bid, -1, Player.Backpack.Serial)
        if stack is not None:
            total += stack.Amount
    return total


# ── Core functions ────────────────────────────────────────────────────────────

def transfer(item, dest):
    """
    Move item to dest. Returns True on success, False if dest is full.
    Clears the journal immediately before the move so only the move result
    is checked — prevents stale messages from causing false positives.
    """
    Journal.Clear()
    Items.Move(item, dest, item.Amount)
    Misc.Pause(MOVE_PAUSE_MS)
    return not _journal_too_many()


def craft_crate():
    """
    Craft one large crate using the carpentry tool in the player's backpack.
    Returns the new Item object, or None on failure.
    """
    tool = FindCarpentryTool(Player.Backpack)
    if tool is None:
        log("No carpentry tool in backpack.", colors['red'])
        return None

    spec     = carpentryCraftables['large crate']
    boards   = spec.resourcesNeeded.get('boards', 0)
    if _board_count() < boards:
        log("Need %d boards to craft a crate (%d available)." % (boards, _board_count()), colors['red'])
        return None

    gump_id = spec.gumpPath[0].gumpID
    before  = {item.Serial for item in (Player.Backpack.Contains or [])}

    # Open the carpentry gump
    Items.UseItem(tool)
    if not Gumps.WaitForGump(gump_id, GUMP_TIMEOUT):
        log("Carpentry gump did not open.", colors['red'])
        return None

    Misc.Pause(500)

    # Navigate to Containers → large crate
    Gumps.SendAction(spec.gumpPath[0].gumpID, spec.gumpPath[0].buttonID)
    for path in spec.gumpPath[1:]:
        Gumps.WaitForGump(path.gumpID, 3000)
        Misc.Pause(500)
        Gumps.SendAction(path.gumpID, path.buttonID)

    # Wait for craft to complete, then close without triggering Make Last
    Gumps.WaitForGump(gump_id, GUMP_TIMEOUT)
    Misc.Pause(800)
    Gumps.CloseGump(gump_id)
    Misc.Pause(600)

    # Find the new item in the backpack
    for item in (Player.Backpack.Contains or []):
        if item.Serial not in before:
            log("Crafted: %s (0x%X)" % (item.Name, item.Serial), colors['cyan'])
            return item

    log("No new item found in backpack after crafting.", colors['red'])
    return None


def place_on_ground(item):
    """
    Drop item one tile east of the player at the player's current elevation.
    Offsetting ensures the crate doesn't land under the player's feet,
    and using Player.Position.Z places it on the correct floor (including upper stories).
    Returns the Item now on the ground, or None if it can't be located.
    """
    pos    = Player.Position
    serial = item.Serial
    Items.MoveOnGround(item, 1, pos.X + 1, pos.Y, pos.Z)
    Misc.Pause(MOVE_PAUSE_MS)
    placed = Items.FindBySerial(serial)
    if placed is None:
        log("Cannot locate item 0x%X after placing on ground." % serial, colors['red'])
        return None
    log("Placed at (%d, %d, %d)." % (placed.Position.X, placed.Position.Y, placed.Position.Z))
    return placed


def make_new_output():
    """
    Full cycle: craft a crate, place it on the ground, return it as the new output.
    Returns the new Item, or None on unrecoverable failure.
    """
    log("Output full — creating new crate...", colors['yellow'])
    crate = craft_crate()
    if crate is None:
        return None
    placed = place_on_ground(crate)
    if placed is None:
        return None
    log("New output ready: 0x%X" % placed.Serial, colors['cyan'])
    return placed


def transfer_with_fallback(item, output_box):
    """
    Move item to output_box. If the box is full, auto-create a new crate on the ground
    and transfer there instead.

    Returns the (possibly new) output box Item, or None on unrecoverable failure.
    Intended to replace bare Items.Move calls in the trainer once validated.
    """
    if transfer(item, output_box):
        return output_box

    log("Output box 0x%X is full." % output_box.Serial, colors['yellow'])
    new_box = make_new_output()
    if new_box is None:
        return None
    if not transfer(item, new_box):
        log("New crate is also full or inaccessible.", colors['red'])
        return None
    return new_box


# ── Standalone validation ─────────────────────────────────────────────────────

def main():
    log("=== crate_manager validation ===", colors['cyan'])

    # Step 1: target an existing output box
    log("Target the current output box.", colors['cyan'])
    serial = Target.PromptTarget("Target the output box:")
    if not serial:
        log("Cancelled.", colors['red'])
        return
    output_box = Items.FindBySerial(serial)
    if output_box is None:
        log("Item 0x%X not found." % serial, colors['red'])
        return
    log("Output box: %s (0x%X)" % (output_box.Name, output_box.Serial))

    # Step 2: attempt transfer of a board stack to test detection
    board = None
    for bid in BOARD_IDS:
        board = Items.FindByID(bid, -1, Player.Backpack.Serial)
        if board is not None:
            break

    if board is None:
        log("No boards in backpack — skipping transfer detection test.", colors['yellow'])
    else:
        log("Testing transfer to output box...", colors['cyan'])
        if transfer(board, output_box):
            log("Transfer OK — box not yet full.", colors['cyan'])
        else:
            log("Transfer FAILED — box full. Running overflow cycle...", colors['yellow'])
            output_box = make_new_output()
            if output_box is None:
                log("Overflow cycle FAILED.", colors['red'])
                return
            log("Overflow cycle passed. New box: 0x%X" % output_box.Serial, colors['cyan'])

    # Step 3: isolated craft test
    log("Testing craft_crate()...", colors['cyan'])
    crate = craft_crate()
    if crate is None:
        log("craft_crate FAILED.", colors['red'])
        return
    log("craft_crate passed: %s (0x%X)" % (crate.Name, crate.Serial), colors['cyan'])

    # Step 4: isolated place test
    log("Testing place_on_ground()...", colors['cyan'])
    placed = place_on_ground(crate)
    if placed is None:
        log("place_on_ground FAILED.", colors['red'])
        return
    log("place_on_ground passed: 0x%X at (%d,%d,%d)" % (
        placed.Serial, placed.Position.X, placed.Position.Y, placed.Position.Z), colors['cyan'])

    log("=== All validation steps passed ===", colors['cyan'])


if __name__ == '__main__':
    main()
