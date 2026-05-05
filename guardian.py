# guardian.py
# Keeps your pet close and on guard. Heals or cures the pet when needed.
# Every CHECK_INTERVAL ms: checks pet health/poison, then checks distance.
# If pet is too far, calls it back and waits up to FOLLOW_MAX_CHECKS x FOLLOW_CHECK_INTERVAL ms.

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors

# ─── Config ───────────────────────────────────────────────────────────────────
PET_FOLLOW_RANGE     = 2      # tiles — beyond this the pet is recalled
HEALTH_THRESHOLD     = 0.90   # heal/cure when pet HP ratio drops below this
CHECK_INTERVAL        = 1500  # ms between main loop ticks
FOLLOW_CHECK_INTERVAL = 1500  # ms between "all follow me" repeats while waiting for pet
FOLLOW_MAX_CHECKS     = 1     # max polls waiting for pet to arrive (total wait = FOLLOW_CHECK_INTERVAL * FOLLOW_MAX_CHECKS)
PET_SCAN_RANGE        = 30    # tile radius to search for a friendly mobile
GUARD_BREAK_DISTANCE  = 4     # tiles player must move from guard origin before pet is immediately recalled

# Auto-bank gold
WEIGHT_BANK_THRESHOLD = 0.90        # recall home when weight ratio >= this
GOLD_DEST_SERIAL      = 0x400B404A  # serial of the container to deposit gold into — EDIT THIS
HOME_RUNEBOOK_NAME    = "home"      # label on the runebook item (case-insensitive)
FARM_RUNE_NAME        = "ww"        # label of the rune to return to after banking (case-insensitive)
RECALL_SETTLE_DELAY   = 2000        # ms to wait after recall lands

RUNEBOOK_ITEM_ID   = 0x22C5
GOLD_ITEM_ID       = 0x0EED
RUNEBOOK_GUMP_ID   = 89
RECALL_BUTTON_BASE = 50   # confirmed: recall slot N = 50 + N  (macro: slot0=50, slot1=51, slot12=62, slot13=63)
GATE_BUTTON_BASE   = 100  # confirmed: gate slot N = 100 + N


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[guardian] " + msg, color)


# ─── Auto-bank gold ───────────────────────────────────────────────────────────

def find_home_runebook():
    rb = Items.FindByID(RUNEBOOK_ITEM_ID, -1, Player.Backpack.Serial)
    if rb is None:
        return None
    props = Items.GetPropStringList(rb.Serial) or []
    if any(p.strip().lower() == HOME_RUNEBOOK_NAME for p in props):
        return rb
    return None


def recall_to_named_rune(runebook, rune_name):
    """
    Open the runebook gump, locate rune_name in the text list, then recall using
    the confirmed fixed formula: button = 50 + absolute_slot_index.

    LastGumpGetLineList returns all gump text elements (labels, charges, page tabs,
    rune names, etc.) not just rune names. The rune names form a contiguous block;
    we find the target and walk backward through that block to determine its
    0-based slot index within the 16-slot runebook.
    """
    Items.UseItem(runebook)
    if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
        log("Runebook gump did not open.", colors['red'])
        return False

    lines = Gumps.LastGumpGetLineList()
    target = rune_name.strip().lower()

    target_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            target_idx = i
            break

    if target_idx is None:
        log("Rune '%s' not found. Lines: %s" % (rune_name, lines), colors['red'])
        # Do NOT send any gump action here — unknown buttons can drop runes.
        return False

    # Walk backward through the rune name block to count its 0-based slot index.
    # Stop at empty strings, digit-only entries (page tabs), or known fixed gump labels.
    _GUMP_LABELS = {"rename book", "charges", "max charges"}
    slot = 0
    i = target_idx - 1
    while i >= 0:
        entry = lines[i].strip()
        if not entry or entry.isdigit() or entry.lower() in _GUMP_LABELS:
            break
        slot += 1
        i -= 1

    button_id = RECALL_BUTTON_BASE + slot
    log("Recalling to '%s' (slot %d → button %d)." % (rune_name, slot, button_id), colors['cyan'])
    Gumps.SendAction(RUNEBOOK_GUMP_ID, button_id)
    Misc.Pause(RECALL_SETTLE_DELAY)
    return True


def transfer_gold():
    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Gold destination (0x%X) not found — set GOLD_DEST_SERIAL in config." % GOLD_DEST_SERIAL, colors['red'])
        return
    total = 0
    gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
    while gold is not None:
        total += gold.Amount
        Items.Move(gold, dest, gold.Amount)
        Misc.Pause(800)
        gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
    if total:
        log("Deposited %d gold into 0x%X." % (total, GOLD_DEST_SERIAL), colors['cyan'])
    else:
        log("No gold to deposit.", colors['yellow'])


def bank_gold_if_heavy():
    if Player.MaxWeight == 0:
        return
    ratio = float(Player.Weight) / Player.MaxWeight
    if ratio < WEIGHT_BANK_THRESHOLD:
        return

    log("Weight at %.0f%% — recalling home to deposit gold." % (ratio * 100), colors['yellow'])

    rb = find_home_runebook()
    if rb is None:
        log("No runebook named '%s' in backpack — cannot bank." % HOME_RUNEBOOK_NAME, colors['red'])
        return

    mana_before = Player.Mana
    Journal.Clear()
    Spells.CastMagery("Recall")
    if not Target.WaitForTarget(4000, False):
        log("Recall: target cursor never appeared.", colors['red'])
        return
    Target.TargetExecute(rb.Serial)

    Timer.Create("recall_mana", 3000)
    while Timer.Check("recall_mana"):
        if Player.Mana < mana_before:
            break
        Misc.Pause(50)

    Misc.Pause(RECALL_SETTLE_DELAY)
    transfer_gold()
    recall_to_named_rune(rb, FARM_RUNE_NAME)


def find_pet():
    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    candidates = Mobiles.ApplyFilter(f)
    nearest     = None
    nearestDist = 9999
    for mob in candidates:
        if mob.Serial == Player.Serial:
            continue
        d = Player.DistanceTo(mob)
        if d < nearestDist:
            nearestDist = d
            nearest = mob
    return nearest


def heal_pet(pet):
    log("HP low — healing %s" % pet.Name, colors['cyan'])
    Spells.CastMagery('Greater Heal')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def cure_pet(pet):
    log("Poisoned — curing %s" % pet.Name, colors['cyan'])
    Spells.CastMagery('Arch Cure')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def check_pet_health(pet):
    if Player.Name.lower() == 'kspot':
        return
    if pet.HitsMax == 0:
        return
    hp_ratio = float(pet.Hits) / pet.HitsMax
    if pet.Poisoned and hp_ratio < HEALTH_THRESHOLD:
        cure_pet(pet)
    elif hp_ratio < HEALTH_THRESHOLD:
        heal_pet(pet)


def recall_pet(pet):
    log("Pet too far (%d tiles) — all follow me" % Player.DistanceTo(pet), colors['yellow'])
    for i in range(FOLLOW_MAX_CHECKS):
        Player.ChatSay(690, 'all follow me')
        Misc.Pause(FOLLOW_CHECK_INTERVAL)
        fresh = Mobiles.FindBySerial(pet.Serial)
        if fresh is None:
            log("Pet disappeared during recall.", colors['red'])
            return False
        if Player.DistanceTo(fresh) <= PET_FOLLOW_RANGE:
            return True
        log("Waiting for pet... check %d/%d" % (i + 1, FOLLOW_MAX_CHECKS), colors['yellow'])
    log("Pet did not return after %d checks." % FOLLOW_MAX_CHECKS, colors['red'])
    return False


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    log("Guardian started.", colors['cyan'])
    is_guarding = False
    guard_pos   = None  # player tile when "all guard me" was last issued

    while not Player.IsGhost:
        bank_gold_if_heavy()

        # Break guard the moment the player moves far enough from the guard origin.
        # This fires "all follow me" immediately rather than waiting for the pet
        # distance check, which is what lets the pet kill mobs before being recalled.
        if is_guarding and guard_pos is not None:
            pos = Player.Position
            if max(abs(pos.X - guard_pos[0]), abs(pos.Y - guard_pos[1])) > GUARD_BREAK_DISTANCE:
                is_guarding = False
                guard_pos   = None
                Player.ChatSay(690, 'all follow me')

        pet = find_pet()
        if pet is None:
            log("No pet found — calling out...", colors['yellow'])
            is_guarding = False
            guard_pos   = None
            Player.ChatSay(690, 'all follow me')
            Misc.Pause(CHECK_INTERVAL)
            continue

        check_pet_health(pet)

        if Player.DistanceTo(pet) > PET_FOLLOW_RANGE:
            is_guarding = False
            guard_pos   = None
            arrived = recall_pet(pet)
            if not arrived:
                Misc.Pause(CHECK_INTERVAL)
                continue

        if not is_guarding:
            pos = Player.Position
            Player.ChatSay(690, 'all guard me')
            is_guarding = True
            guard_pos   = (pos.X, pos.Y)

        Misc.Pause(CHECK_INTERVAL)


main()
