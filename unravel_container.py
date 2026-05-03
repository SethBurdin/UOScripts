# unravel_container.py
# Move all items from a pack beetle into a target box, unravel the box via
# Imbuing when player weight exceeds the threshold, then repeat until the
# beetle is empty.
#
# Flow:
#   1. Auto-detect pack beetle (fallback: target prompt).
#   2. Prompt player to target the unravel box.
#   3. Loop:
#        a. Move items from beetle → box one at a time.
#        b. Stop when player weight > WEIGHT_THRESHOLD (or beetle empties).
#        c. Unravel the box via Imbuing skill.
#        d. Repeat until beetle is empty.

# IDE IntelliSense support – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

# ─── Config ───────────────────────────────────────────────────────────────────
WEIGHT_THRESHOLD     = 400    # stones – unravel when player exceeds this
PAUSE_BETWEEN_MOVES  = 2000   # ms – between Items.Move calls
PAUSE_OPEN_CONTAINER = 1200   # ms – after opening a container
PAUSE_AFTER_UNRAVEL  = 1500   # ms – let server process the unravel

# ─── Imbuing gump IDs (from imbue container.py) ──────────────────────────────
IMBUING_GUMP_ID  = 0x5b394d53   # verified via Gump Inspector
UNRAVEL_BTN      = 10011       # "Unravel Container" button in imbuing gump
CONFIRM_GUMP_ID  = 0x7f3111a7   # verified via Gump Inspector
CONFIRM_BTN      = 1


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[unravel] " + msg, color)


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


def unravel_box(box_serial):
    """
    Trigger Imbuing → Unravel Container on the given box.
    Returns True on success, False if any step failed.
    """
    Journal.Clear()

    Player.UseSkill('Imbuing')
    if not Gumps.WaitForGump(IMBUING_GUMP_ID, 5000):
        log("Imbuing gump timed out – skill on cooldown?", 0x25)
        return False

    Gumps.SendAction(IMBUING_GUMP_ID, UNRAVEL_BTN)
    Target.WaitForTarget(5000, False)
    Target.TargetExecute(box_serial)

    if not Gumps.WaitForGump(CONFIRM_GUMP_ID, 5000):
        log("Confirm gump timed out – unravel may have failed.", 0x25)
        if Gumps.WaitForGump(IMBUING_GUMP_ID, 1000):
            Gumps.CloseGump(IMBUING_GUMP_ID)
        return False

    Gumps.SendAction(CONFIRM_GUMP_ID, CONFIRM_BTN)
    Misc.Pause(PAUSE_AFTER_UNRAVEL)

    # Close imbuing menu if it reopened after the unravel
    if Gumps.WaitForGump(IMBUING_GUMP_ID, 1000):
        Gumps.CloseGump(IMBUING_GUMP_ID)

    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # ── Step 1: find beetle ───────────────────────────────────────────────────
    beetle = find_pack_animal()
    if beetle is not None:
        log("Beetle auto-detected: %s (0x%X)" % (beetle.Name, beetle.Serial))
    else:
        log("No follower with backpack nearby – target your pack beetle.")
        beetle_serial = Target.PromptTarget("Target your pack beetle")
        if beetle_serial == 0 or beetle_serial == Player.Serial:
            log("Cancelled.", 0x25)
            return
        beetle = Mobiles.FindBySerial(beetle_serial)
        if beetle is None or beetle.Backpack is None:
            log("Invalid target – no backpack found.", 0x25)
            return
        log("Beetle: %s (0x%X)" % (beetle.Name, beetle.Serial))

    # ── Step 2: target the unravel box ───────────────────────────────────────
    log("Target the unravel box.")
    box_serial = Target.PromptTarget("Target the unravel box")
    if box_serial == 0 or box_serial == Player.Serial:
        log("Cancelled.", 0x25)
        return
    box = Items.FindBySerial(box_serial)
    if box is None:
        log("Could not find that container.", 0x25)
        return
    log("Box: %s (0x%X)" % (box.Name, box_serial))

    # ── Step 3: transfer → unravel loop ──────────────────────────────────────
    round_num = 0
    while True:
        # Refresh beetle backpack contents
        Items.UseItem(beetle.Backpack)
        Items.WaitForContents(beetle.Backpack, 3000)
        Misc.Pause(PAUSE_OPEN_CONTAINER)

        contents = list(beetle.Backpack.Contains) if beetle.Backpack.Contains else []
        if not contents:
            log("Beetle is empty – all done.")
            break

        round_num += 1
        log("Round %i – %i item(s) on beetle, player weight %d/%d stones."
            % (round_num, len(contents), Player.Weight, Player.MaxWeight))

        # Move items one at a time; stop when weight threshold is hit
        for item in contents:
            Items.Move(item, box, item.Amount)
            Misc.Pause(PAUSE_BETWEEN_MOVES)
            if Player.Weight > WEIGHT_THRESHOLD:
                log("Weight %d/%d – triggering unravel."
                    % (Player.Weight, Player.MaxWeight))
                break

        # Unravel the box (converts items → lighter magical residue)
        log("Unraveling box...")
        if not unravel_box(box_serial):
            log("Unravel failed – stopping.", 0x25)
            break

    log("Complete.")


main()
