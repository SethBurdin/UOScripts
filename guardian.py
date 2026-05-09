# guardian.py
# Keeps your pet close and on guard. Heals or cures the pet when needed.
# Every CHECK_INTERVAL ms: checks pet health/poison, then checks distance.
# If pet is too far, calls it back and waits up to FOLLOW_MAX_CHECKS x FOLLOW_CHECK_INTERVAL ms.

if False:
    from razorenhanced_stubs import *

import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from glossary.colors import colors
from glossary.runebook_handler import find_runebook_by_label, travel_to_runebook, travel_to_named_rune

# ─── Config ───────────────────────────────────────────────────────────────────
PET_FOLLOW_RANGE     = 1      # tiles — beyond this the pet is recalled
HEALTH_THRESHOLD     = 0.60   # heal/cure when pet HP ratio drops below this
GUARD_HEALTH_THRESHOLD = 0.70 # say "all guard me" when pet HP ratio drops below this
CHECK_INTERVAL        = 1500  # ms between main loop ticks
FOLLOW_CHECK_INTERVAL = 4000  # ms between "all follow me" repeats while waiting for pet
FOLLOW_MAX_CHECKS     = 3     # max polls waiting for pet to arrive (total wait = FOLLOW_CHECK_INTERVAL * FOLLOW_MAX_CHECKS)
PET_SCAN_RANGE        = 30    # tile radius to search for a friendly mobile
GUARD_BREAK_DISTANCE  = 1    # tiles player must move from guard origin before pet is immediately recalled

# Pet context menu entry indices (right-click the pet)
PET_CMD_FOLLOW = 2   # "Command: Follow"
PET_CMD_GUARD  = 3   # "Command: Guard"

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
    # gems
    0x0F26,   # diamond
    0x0F25,   # amber
    0x0F0F,   # star sapphire
    0x0F10,   # emerald
    0x0F15,   # citrine
    0x0F11,   # sapphire
    0x0F13,   # ruby
    0x0F18,   # tourmaline
    0x0F16,   # amethyst
]

# Auto-bank gold
WEIGHT_BANK_THRESHOLD = 0.90        # recall home when weight ratio >= this
GOLD_DEST_SERIAL      = config.quick_dropbox
HOME_RUNEBOOK_NAME    = "home"      # label on the runebook item (case-insensitive)
FARM_RUNE_NAME        = "ww"        # label of the rune to return to after banking (case-insensitive)
RECALL_SETTLE_DELAY   = 2000        # ms to wait after recall lands

GOLD_ITEM_ID = 0x0EED

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guardian_stats.json")

# ─── Session gold tracking ────────────────────────────────────────────────────

_pet_serial    = None
_session_start = None
_session_gold  = 0


def _append_gold_stat(gold_this_trip):
    global _session_gold
    _session_gold += gold_this_trip
    elapsed = time.time() - _session_start
    gph = int(_session_gold / elapsed * 3600) if elapsed > 0 else 0
    entry = {
        "rune":          FARM_RUNE_NAME,
        "time":          time.strftime("%Y-%m-%d %H:%M:%S"),
        "gold_per_hour": gph,
    }
    try:
        with open(STATS_FILE, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = []
    data.append(entry)
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log("Gold/hr: %d  (session: %d gold, %.1f min)" % (gph, _session_gold, elapsed / 60), colors['cyan'])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[guardian] " + msg, color)


def _pet_cmd(serial, entry, target_serial=None):
    """Issue a pet command silently via the context menu.
    Pass target_serial for commands that open a target cursor (e.g. Follow)."""
    if Misc.WaitForContext(serial, 2000):
        Misc.ContextReply(serial, entry)
        if target_serial is not None:
            if Target.WaitForTarget(3000, False):
                Target.TargetExecute(target_serial)
    Misc.Pause(400)


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
    return total


def do_banking(rb):
    """Travel home, deposit everything, then return to the farm rune."""
    if not travel_to_runebook(rb, RECALL_SETTLE_DELAY):
        log("Failed to travel home — banking aborted.", colors['red'])
        return False
    gold = transfer_gold()
    transfer_loot_to_chest()
    if gold and _session_start is not None:
        _append_gold_stat(gold)
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


def discover_pet():
    """Mount-test nearby non-human mobiles to lock in the pet serial."""
    global _pet_serial

    # Already mounted — dismount first so the pet appears in the mobile list,
    # then fall through to the scan loop to capture the correct Mobile serial.
    if Player.Mount is not None:
        log("Already mounted — dismounting before scan.", colors['cyan'])
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(2000)

    log("Scanning for mountable pet within %d tiles..." % PET_SCAN_RANGE, colors['cyan'])
    f = Mobiles.Filter()
    f.Enabled  = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial or mob.IsHuman:
            continue
        log("Trying %s (0x%X)..." % (mob.Name, mob.Serial), colors['yellow'])
        Mobiles.UseMobile(mob.Serial)
        Misc.Pause(1500)
        # Player.Mount is an Item whose serial may differ from the Mobile serial,
        # so just confirm something was mounted rather than comparing serials.
        if Player.Mount is not None:
            _pet_serial = mob.Serial
            log("Pet locked: %s (0x%X) — dismounting." % (mob.Name, _pet_serial), colors['cyan'])
            Mobiles.UseMobile(Player.Serial)
            Misc.Pause(1500)
            return True

    log("No mountable non-human pet found nearby.", colors['red'])
    return False


def find_pet():
    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    nearest, nearestDist = None, 9999
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        if _pet_serial is not None:
            if mob.Serial == _pet_serial:
                return mob
        else:
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


def guard_pet_if_low(pet):
    if pet.HitsMax == 0:
        return
    if float(pet.Hits) / pet.HitsMax < GUARD_HEALTH_THRESHOLD:
        log("%s HP low (%.0f%%) — guard x3" % (
            pet.Name, float(pet.Hits) / pet.HitsMax * 100), colors['yellow'])
        for _ in range(3):
            _pet_cmd(pet.Serial, PET_CMD_GUARD)
            Misc.Pause(400)


def check_pet_health(pet):
    if pet.HitsMax == 0:
        return
    hp_ratio = float(pet.Hits) / pet.HitsMax
    if Player.Name.lower() == 'kspot':
        return
    if pet.Poisoned and hp_ratio < HEALTH_THRESHOLD:
        cure_pet(pet)
    elif hp_ratio < HEALTH_THRESHOLD:
        heal_pet(pet)


def recall_pet(pet):
    log("Pet too far (%d tiles) — recalling." % Player.DistanceTo(pet), colors['yellow'])
    for i in range(FOLLOW_MAX_CHECKS):
        _pet_cmd(pet.Serial, PET_CMD_FOLLOW, Player.Serial)
        Misc.Pause(FOLLOW_CHECK_INTERVAL)
        fresh = find_pet()
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
    global _session_start, _session_gold
    _session_start = time.time()
    _session_gold  = 0
    log("Guardian started.", colors['cyan'])

    if not discover_pet():
        log("Pet discovery failed — stopping.", colors['red'])
        return

    is_guarding = False
    guard_pos   = None  # player tile when "all guard me" was last issued

    Journal.Clear()
    log("Say 'bank' to deposit and stop.", colors['cyan'])

    while not Player.IsGhost:
        if Journal.Search(Player.Name + ": bank"):
            Journal.Clear()
            log("Bank command — depositing and stopping.", colors['yellow'])
            rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
            if rb is not None:
                do_banking(rb)
            log("Done. Script stopped.", colors['cyan'])
            break

        bank_gold_if_heavy()

        pet = find_pet()

        # Break guard the moment the player moves far enough from the guard origin.
        if is_guarding and guard_pos is not None:
            pos = Player.Position
            if max(abs(pos.X - guard_pos[0]), abs(pos.Y - guard_pos[1])) > GUARD_BREAK_DISTANCE:
                is_guarding = False
                guard_pos   = None
                if pet is not None:
                    _pet_cmd(pet.Serial, PET_CMD_FOLLOW, Player.Serial)

        if pet is None:
            log("No pet found.", colors['yellow'])
            is_guarding = False
            guard_pos   = None
            Misc.Pause(CHECK_INTERVAL)
            continue

        guard_pet_if_low(pet)
        check_pet_health(pet)

        if Player.DistanceTo(pet) > PET_FOLLOW_RANGE:
            is_guarding = False
            guard_pos   = None
            arrived = recall_pet(pet)
            if not arrived:
                # Pet may have settled just outside PET_FOLLOW_RANGE (UO natural follow
                # distance is ~2 tiles). Refresh and fall through to guard if close enough.
                fresh = find_pet()
                if fresh is None or Player.DistanceTo(fresh) > PET_FOLLOW_RANGE + 1:
                    Misc.Pause(CHECK_INTERVAL)
                    continue
                pet = fresh

        if not is_guarding:
            pos = Player.Position
            _pet_cmd(pet.Serial, PET_CMD_GUARD)
            is_guarding = True
            guard_pos   = (pos.X, pos.Y)

        Misc.Pause(CHECK_INTERVAL)


main()
