# guardian.py
# Keeps your pet close and on guard. Heals or cures the pet when needed.
# Every CHECK_INTERVAL ms: checks pet health/poison, then checks distance.
# If pet is too far, calls it back and waits up to FOLLOW_MAX_CHECKS x FOLLOW_CHECK_INTERVAL ms.

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from glossary.colors import colors
from glossary.runebook_handler import find_runebook_by_label, travel_to_runebook, travel_to_named_rune

# ─── Config ───────────────────────────────────────────────────────────────────
PET_FOLLOW_RANGE     = 2      # tiles — beyond this the pet is recalled
HEALTH_THRESHOLD     = 0.90   # heal/cure when pet HP ratio drops below this
CHECK_INTERVAL        = 1500  # ms between main loop ticks
FOLLOW_CHECK_INTERVAL = 4000  # ms between "all follow me" repeats while waiting for pet
FOLLOW_MAX_CHECKS     = 3     # max polls waiting for pet to arrive (total wait = FOLLOW_CHECK_INTERVAL * FOLLOW_MAX_CHECKS)
PET_SCAN_RANGE        = 30    # tile radius to search for a friendly mobile
GUARD_BREAK_DISTANCE  = 2    # tiles player must move from guard origin before pet is immediately recalled

# Items auto-looted by Razor's AutoLoot agent that should be transferred to the
# storage chest on each banking trip. Add/remove item IDs to match your AutoLoot list.
TRANSFER_ITEMS = [
    0x1079,   # hides
    0x26B4,   # red scales
    0x26B5,   # yellow scales
    0x26B6,   # black scales
    0x26B7,   # green scales
    0x26B8,   # white scales
    0x26B9,   # blue scales
    0x14EB,   # treasure map
    0x14EC,   # treasure map (decoded)
]

# Auto-bank gold
WEIGHT_BANK_THRESHOLD = 0.90        # recall home when weight ratio >= this
GOLD_DEST_SERIAL      = config.quick_dropbox
HOME_RUNEBOOK_NAME    = "home"      # label on the runebook item (case-insensitive)
FARM_RUNE_NAME        = "ww"        # label of the rune to return to after banking (case-insensitive)
RECALL_SETTLE_DELAY   = 2000        # ms to wait after recall lands

GOLD_ITEM_ID = 0x0EED


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[guardian] " + msg, color)


# ─── Auto-bank gold ───────────────────────────────────────────────────────────


def transfer_loot_to_chest():
    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Storage chest (0x%X) not found — skipping loot transfer." % GOLD_DEST_SERIAL, colors['red'])
        return
    for item_id in TRANSFER_ITEMS:
        item = Items.FindByID(item_id, -1, Player.Backpack.Serial)
        while item is not None:
            Items.Move(item, dest, item.Amount)
            Misc.Pause(800)
            item = Items.FindByID(item_id, -1, Player.Backpack.Serial)


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


def do_banking(rb):
    """Travel home, deposit everything, then return to the farm rune."""
    if not travel_to_runebook(rb, RECALL_SETTLE_DELAY):
        log("Failed to travel home — banking aborted.", colors['red'])
        return False
    transfer_gold()
    transfer_loot_to_chest()
    return True


def bank_gold_if_heavy():
    if Player.MaxWeight == 0:
        return
    ratio = float(Player.Weight) / Player.MaxWeight
    if ratio < WEIGHT_BANK_THRESHOLD:
        return

    log("Weight at %.0f%% — banking." % (ratio * 100), colors['yellow'])

    rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
    if rb is None:
        log("No runebook named '%s' in backpack — cannot bank." % HOME_RUNEBOOK_NAME, colors['red'])
        return

    if do_banking(rb):
        travel_to_named_rune(rb, FARM_RUNE_NAME, RECALL_SETTLE_DELAY)


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

    Journal.Clear()
    log("Say 'bank' to deposit and stop.", colors['cyan'])

    while not Player.IsGhost:
        if Journal.Search("bank"):
            Journal.Clear()
            log("Bank command — depositing and stopping.", colors['yellow'])
            rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
            if rb is not None:
                do_banking(rb)
            log("Done. Script stopped.", colors['cyan'])
            break

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
