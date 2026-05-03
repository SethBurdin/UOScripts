# unravel_inventory.py
# Unravel every item in the player's backpack one at a time using the Imbuing skill.
# Skips containers (sub-bags) and gold — attempts everything else and lets the
# server reject non-magical items naturally.

# IDE IntelliSense support – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

# ─── Config ───────────────────────────────────────────────────────────────────
DEBUG = True          # set False to silence verbose step logs

UNRAVEL_ITEM_BTN    = 10010   # verified via Gump Inspector
IMBUING_GUMP_ID     = 0x5b394d53   # verified via Gump Inspector
CONFIRM_GUMP_ID     = 0x7f3111a7   # verified via Gump Inspector
CONFIRM_BTN         = 1

# Exact server message phrases (case-sensitive substring match)
PHRASE_SKILL_LOW    = "not high enough to magically unravel"
PHRASE_NOT_MAGICAL  = "cannot magically unravel"
PHRASE_PACK_FULL    = "Your backpack is full"  # confirmed phrase (see mining.py)

PAUSE_BETWEEN_ITEMS  = 300    # ms – between each unravel attempt
PAUSE_OPEN_CONTAINER = 1200   # ms – after opening a container before reading contents

SKIP_IDS = {
    0x0EED,   # gold coins
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[unravel_inv] " + msg, color)

def dlog(msg):
    """Debug-only log — only prints when DEBUG = True."""
    if DEBUG:
        Misc.SendMessage("[unravel_inv:dbg] " + msg, 0x3F)


def unravel_item(item, too_low_box):
    """
    Unravel a single item via Imbuing. Returns True if the gump sequence
    completed, False if a gump timed out (skill not ready, etc.).
    If the server says skill is not high enough, moves the item to too_low_box.
    """
    PHRASE_BLESSED = "You cannot unravel the magic of a blessed item."
    Journal.Clear()
    dlog("UseSkill Imbuing...")
    Player.UseSkill('Imbuing')
    if not Gumps.WaitForGump(IMBUING_GUMP_ID, 5000):
        log("Imbuing gump timed out – skill on cooldown?", 0x25)
        return False
    dlog("Imbuing gump open. Sending Unravel Item btn (%d)..." % UNRAVEL_ITEM_BTN)

    Gumps.SendAction(IMBUING_GUMP_ID, UNRAVEL_ITEM_BTN)
    dlog("Waiting for target cursor...")
    Target.WaitForTarget(5000, False)
    dlog("Targeting item serial 0x%X..." % item.Serial)
    Target.TargetExecute(item.Serial)

    # Give server time to send journal feedback
    Misc.Pause(800)
    dlog("Checking journal for server response...")

    # ── Dump raw journal lines so exact server text is visible ────────────────
    if DEBUG:
        for entry in Journal.GetTextByType("Regular"):
            dlog("  journal: %s" % entry)

    # ── Case: blessed item (skip) ────────────────────────────────────────────
    if Journal.Search(PHRASE_BLESSED):
        log("  BLESSED ITEM: %s (skipped)" % item.Name, 0x25)
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return True

    # ── Case 1: skill too low ─────────────────────────────────────────────────
    if Journal.Search(PHRASE_SKILL_LOW):
        log("  SKILL TOO LOW: %s" % item.Name, 0x25)
        dlog("  -> closing imbuing gump and moving to box")
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        if too_low_box is not None:
            Items.Move(item, too_low_box, item.Amount)
            Misc.Pause(2000)
            dlog("  -> moved to box 0x%X" % too_low_box.Serial)
        else:
            dlog("  -> no box set, item left in place")
        return True

    # ── Case 2: not a magical item ────────────────────────────────────────────
    if Journal.Search(PHRASE_NOT_MAGICAL):
        dlog("  not magical — skipping")
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return True

    # ── Case 3: confirm gump appeared — proceed with unravel ─────────────────
    # NOTE: the server shows the confirm gump FIRST, then sends the "skill too
    # low" journal message only after the confirm button is clicked.  So we must
    # send confirm and then re-check the journal before declaring success.
    dlog("  no journal rejection — waiting for confirm gump...")
    if Gumps.WaitForGump(CONFIRM_GUMP_ID, 2000):
        dlog("  confirm gump present — sending confirm")
        Journal.Clear()
        Gumps.SendAction(CONFIRM_GUMP_ID, CONFIRM_BTN)
        Misc.Pause(800)   # wait for server to respond to the confirm

        if DEBUG:
            for entry in Journal.GetTextByType("Regular"):
                dlog("  post-confirm journal: %s" % entry)

        if Journal.Search(PHRASE_SKILL_LOW):
            log("  SKILL TOO LOW (post-confirm): %s" % item.Name, 0x25)
            if Gumps.HasGump():
                Gumps.CloseGump()
                Misc.Pause(400)
            if too_low_box is not None:
                Items.Move(item, too_low_box, item.Amount)
                Misc.Pause(2000)
                dlog("  -> moved to box 0x%X" % too_low_box.Serial)
            else:
                dlog("  -> no box set, item left in place")
            return True

        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        dlog("  unravelled OK")
        return True

    # ── Case 4: nothing matched — move to box as fallback ─────────────────────
    log("  NO RESPONSE MATCHED for %s -> box" % item.Name, 0x25)
    dlog("  (check journal dump above to see exact server message)")
    if Gumps.HasGump():
        Gumps.CloseGump()
        Misc.Pause(400)
    if too_low_box is not None:
        Items.Move(item, too_low_box, item.Amount)
        Misc.Pause(2000)
        dlog("  -> moved to box 0x%X" % too_low_box.Serial)

    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def prompt_too_low_box():
    """
    Ask the player to target a box for items that cannot be unraveled due to
    insufficient Imbuing skill.  Returns the Item, or None if skipped.
    """
    log("Target a box for 'skill too low' items (or press Escape to skip).", 0x53)
    serial = Target.PromptTarget("Target box for items your skill is too low to unravel:")
    if not serial or serial == 0:
        log("No box selected – skill-too-low items will be skipped.", 0x3F)
        return None
    box = Items.FindBySerial(serial)
    if box is None:
        log("Could not find targeted item.", 0x25)
        return None
    log("Too-low box: %s (0x%X)" % (box.Name, box.Serial))
    return box


def find_pack_animal():
    """Auto-detect a nearby follower with a backpack. Returns the Mobile or None."""
    f = Mobiles.Filter()
    f.RangeMax = 3
    f.IsHuman  = False
    f.Friend   = True
    nearby = Mobiles.ApplyFilter(f)
    for mob in nearby:
        if mob.Serial == Player.Serial:
            continue
        if mob.Backpack is not None:
            return mob
    return None


def transfer_beetle_to_backpack():
    """
    Move all items from a pack beetle into the player's backpack.
    Auto-detects the beetle; falls back to a target prompt.
    Returns True if transfer completed (or beetle was empty), False if cancelled.
    """
    beetle = find_pack_animal()
    if beetle is None:
        log("No pack animal nearby – skipping beetle transfer.", 0x3F)
        return True
    log("Beetle auto-detected: %s (0x%X)" % (beetle.Name, beetle.Serial))


    # Pre-transfer: wait for client to be ready if busy
    busy_waits = 0
    while Journal.Search('You must wait to perform another action.') and busy_waits < 10:
        dlog('Client busy before transfer, waiting...')
        Misc.Pause(1200)
        busy_waits += 1
        Journal.Clear()
    if busy_waits >= 10:
        log('Client remained busy too long, skipping beetle transfer.', 0x25)
        return False

    Items.UseItem(beetle.Backpack)
    Items.WaitForContents(beetle.Backpack, 3000)
    Misc.Pause(PAUSE_OPEN_CONTAINER)

    contents = list(beetle.Backpack.Contains) if beetle.Backpack.Contains else []
    dlog("Beetle contents: %d items detected." % len(contents))
    for c in contents:
        dlog("  - %s (0x%04X) x%d | IsContainer=%s" % (c.Name, c.ItemID, c.Amount, c.IsContainer))
    if not contents:
        log("Beetle backpack is empty – nothing to transfer.")
        return True

    to_move = [item for item in contents if not item.IsContainer]
    skipped = len(contents) - len(to_move)
    log("Transferring %i item(s) from beetle to backpack%s..." % (
        len(to_move), (" (%d containers skipped)" % skipped) if skipped else ""))
    moved = 0
    for item in to_move:
        dlog("  Attempting move: %s (0x%04X) x%d" % (item.Name, item.ItemID, item.Amount))
        retries = 0
        while retries < 5:
            Journal.Clear()
            dlog("    Move attempt %d for %s" % (retries + 1, item.Name))
            Items.Move(item, Player.Backpack, item.Amount)
            Misc.Pause(PAUSE_BETWEEN_ITEMS * 6)
            if Journal.Search(PHRASE_PACK_FULL):
                log("Backpack is full – stopping transfer after %d item(s). %d remain in beetle."
                    % (moved, len(to_move) - moved), 0x25)
                return False
            # Handle 'You must wait to perform another action'
            if Journal.Search('You must wait to perform another action.'):
                dlog('  client busy, waiting and retrying...')
                Misc.Pause(1200)
                retries += 1
                continue
            break
        else:
            log("Failed to move %s after several retries, skipping." % item.Name, 0x25)
            continue
        moved += 1

    log("Transfer complete (%d item(s) moved)." % moved)
    return True


def main():
    bp = Player.Backpack
    if bp is None:
        log("No backpack found.", 0x25)
        return

    too_low_box = prompt_too_low_box()

    # Transfer items from pack beetle into backpack before unravelling
    if not transfer_beetle_to_backpack():
        return

    # Open backpack and get a snapshot of its contents
    Items.UseItem(bp)
    Items.WaitForContents(bp, 3000)
    Misc.Pause(1200)

    targets = [i for i in (bp.Contains or []) if not i.IsContainer and i.ItemID not in SKIP_IDS]
    if not targets:
        log("Backpack is empty.", 0x25)
        return

    log("Attempting %d item(s)..." % len(targets))
    success = 0
    for i, item in enumerate(targets):
        log("  [%d/%d] %s (0x%04X)" % (i + 1, len(targets), item.Name, item.ItemID))
        if not unravel_item(item, too_low_box):
            log("Stopping – gump sequence failed.", 0x25)
            break
        Misc.Pause(PAUSE_BETWEEN_ITEMS)
        success += 1

    log("Done – attempted %d item(s)." % success)


main()
