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
from glossary.runebook_handler import (
    find_runebook_by_label, travel_to_named_rune,
    arrived_at, walk_steps,
)
from glossary.enemies import GetEnemies
from extraction_looter.corpse_util import scan_nearby_corpses, nearest_corpse, walk_to_corpse

# ─── Config ───────────────────────────────────────────────────────────────────
PET_FOLLOW_RANGE     = 1      # tiles — beyond this the pet is recalled
HEALTH_THRESHOLD          = 0.85   # heal/cure when pet HP ratio drops below this
CRITICAL_HEALTH_THRESHOLD = 0.40   # cast heals back-to-back when below this
GUARD_HEALTH_THRESHOLD    = 0.90   # say "all guard me" when pet HP ratio drops below this
CHECK_INTERVAL        = 1500  # ms between main loop ticks
FOLLOW_CHECK_INTERVAL = 4000  # ms between "all follow me" repeats while waiting for pet
FOLLOW_MAX_CHECKS     = 3     # max polls waiting for pet to arrive (total wait = FOLLOW_CHECK_INTERVAL * FOLLOW_MAX_CHECKS)
PET_SCAN_RANGE        = 30     # tile radius to search for a friendly mobile
GUARD_BREAK_DISTANCE  = 1    # tiles player must move from guard origin before pet is immediately recalled

ENEMY_SCAN_RANGE    = 12   # tile radius to scan for hostile mobs each tick
KILL_ENGAGE_RANGE   = 1    # Chebyshev pet-to-enemy distance that triggers recall phase
GUARD_TRIGGER_RANGE = 2    # enemy-to-player distance that triggers "all guard"
HUNT_GUARD_TIMEOUT  = 12   # seconds to wait in phase 3 for enemy to close
CORPSE_SCAN_RANGE   = 12   # tile radius to scan for corpses (kill mode)

# Player self-heal
PLAYER_HEALTH_THRESHOLD = 0.85   # heal when player HP ratio drops below this
INVIS_BEFORE_HEAL       = True   # cast Invisibility before healing
INVIS_SETTLE_MS         = 3000   # ms to wait after Invis before healing

# Animal Whispering mastery spell
WHISPER_ENABLED      = True
WHISPER_INTERVAL_SEC = 1800  # seconds between casts (30 min)

# Player combat assist
CHIV_MIN_SKILL       = 30.0   # minimum Chivalry to use combat spells
RANGED_MIN_SKILL     = 30.0   # minimum Archery/Throwing to auto-attack
MEDITATION_MIN_SKILL     = 30.0   # minimum Meditation to use the skill
MEDITATION_COOLDOWN_SEC  = 11.0   # UO skill cooldown between attempts
MAGERY_MIN_SKILL     = 30.0   # minimum Magery to use magery spells
VET_MIN_SKILL        = 30.0   # minimum Veterinary to use bandages on pet
VET_THRESHOLD        = 0.75   # bandage pet when HP ratio drops below this
BANDAGE_ITEM_ID      = 0x0E21 # clean bandages
BANDAGE_APPLY_MS     = 4000   # ms to wait for bandage application
BANDAGE_RESTOCK_TARGET = 100  # top up to this many bandages on each banking trip
COMBAT_MANA_FLOOR    = 0.30   # cast combat buffs above this if player can meditate
MANA_REGEN_TARGET    = 0.90   # throttle combat spells until this mana ratio if no meditation

# Pet context menu entry indices (right-click the pet)
PET_CMD_FOLLOW = 2   # "Command: Follow"
PET_CMD_GUARD  = 3   # "Command: Guard"
PET_CMD_KILL   = 4   # "Command: Kill" — if mobs aren't attacked, verify index with gump_dump.py

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
    # alchemy reagents (all share ItemID 0x423A, hue distinguishes variant)
    0x423A,   # potash / black powder / charcoal / saltpeter
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
HOME_RUNEBOOK_NAME    = "home"       # label on the runebook item (case-insensitive)
HOME_RUNE_NAME        = "new home"  # name of the home rune inside that runebook
FARM_RUNE_NAME        = None        # set at runtime via prompt
RECALL_SETTLE_DELAY   = 2000        # ms to wait after recall lands

# Known farm locations — shown as suggestions in the startup prompt.
# The rune name must match the label on the rune in the runebook (case-insensitive).
FARM_LOCATIONS = [
    'ww',        # Wind Wyrms
    'iceogre',   # Ice Ogre Lords
    'demons',    # Demons
    'ogrelords', # Ogre Lords
    'liches',    # Liches
    'balron',    # Balrons
    'ancient',   # Ancient Wyrms
    'titans',    # Titans
    'cavetroll', # Cave Trolls
]

# ─── Farm landing position ────────────────────────────────────────────────────
# After recalling to the farm rune the player steps off the landing tile before
# the guardian loop starts.  Fill in TRANSFER_FROM_POS once you recall there and
# note Player.Position — the script will warn if the landing is wrong.
#
# TRANSFER_FROM_STEPS: default is one tile north.
# If the tile north is blocked at your rune, use ['East', 'North'] instead.
TRANSFER_FROM_POS   = None        # TODO: (x, y) — set from rune landing coords
TRANSFER_FROM_STEPS = ['North']   # movement after landing; change per location if needed

GOLD_ITEM_ID = 0x0EED

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local/guardian_stats.json")
os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

# ─── Session gold tracking ────────────────────────────────────────────────────

_pet_serial      = None
_session_start   = None
_session_gold    = 0
_last_whisper    = 0.0
_last_med_attempt = 0.0
_kill_times      = {}   # { enemy_serial: timestamp } — throttle repeated kill commands
_skip_serials    = set()  # enemies that returned "Target cannot be seen."
_kill_mode       = 'leash'  # set at runtime via prompt
_has_chiv        = False
_has_ranged      = False
_has_meditation  = False
_has_magery      = False
_has_vet         = False
_attacking_serial = None

KILL_COOLDOWN_SEC = 8   # minimum seconds between kill commands for the same enemy


def _append_gold_stat(gold_this_trip):
    global _session_gold
    _session_gold += gold_this_trip
    elapsed = time.time() - _session_start
    gph = int(_session_gold / elapsed * 3600) if elapsed > 0 else 0
    entry = {
        "player":        Player.Name,
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
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(target_serial)
    Misc.Pause(400)


def _send_kill(target_serial):
    """Issue 'all kill' on a target. Returns False and adds the serial to
    _skip_serials if the server replies 'Target cannot be seen.'"""
    Journal.Clear()
    Player.ChatSay("all kill")
    Misc.Pause(300)
    if Target.WaitForTarget(2000, False):
        Target.TargetExecute(target_serial)
    Misc.Pause(600)
    if Journal.Search("Target cannot be seen."):
        log("Target cannot be seen — skipping 0x%X." % target_serial, colors['yellow'])
        _skip_serials.add(target_serial)
        return False
    _kill_times[target_serial] = time.time()
    return True


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


def _restock_bandages():
    """Pull bandages from the drop-off box until we have BANDAGE_RESTOCK_TARGET."""
    if not _has_vet:
        return
    in_pack = Items.FindByID(BANDAGE_ITEM_ID, -1, Player.Backpack.Serial)
    current = in_pack.Amount if in_pack is not None else 0
    needed  = BANDAGE_RESTOCK_TARGET - current
    if needed <= 0:
        return
    in_box = Items.FindByID(BANDAGE_ITEM_ID, -1, GOLD_DEST_SERIAL)
    if in_box is None:
        log("No bandages in drop-off box — skipping restock.", colors['yellow'])
        return
    to_take = min(needed, in_box.Amount)
    log("Restocking %d bandages (have %d, want %d)." % (
        to_take, current, BANDAGE_RESTOCK_TARGET), colors['cyan'])
    Items.Move(in_box, Player.Backpack, to_take)
    Misc.Pause(800)


def _walk_to_drop():
    """Step east → north → west to reach the drop-off container."""
    for direction in ('East', 'North', 'West'):
        Player.Walk(direction)
        Misc.Pause(600)


def do_banking(rb):
    """Travel home, deposit everything, then return to the farm rune."""
    if not travel_to_named_rune(rb, HOME_RUNE_NAME, RECALL_SETTLE_DELAY):
        log("Failed to travel home — banking aborted.", colors['red'])
        return False
    _walk_to_drop()
    gold = transfer_gold()
    transfer_loot_to_chest()
    _restock_bandages()
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
        Player.ChatSay("all guard me")


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

    log("No mountable non-human pet found — target your pet manually.", colors['yellow'])
    serial = Target.PromptTarget("Click your pet:")
    if serial and serial != 0:
        _pet_serial = serial
        mob  = Mobiles.FindBySerial(serial)
        name = mob.Name if mob is not None else ('0x%X' % serial)
        log("Pet locked via prompt: %s (0x%X)" % (name, serial), colors['cyan'])
        return True
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


def heal_pet_critical(pet):
    log("HP critical (%.0f%%) — rapid healing %s" % (
        float(pet.Hits) / pet.HitsMax * 100, pet.Name), colors['red'])
    for _ in range(3):
        Spells.CastMagery('Greater Heal')
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(pet.Serial)
        Misc.Pause(800)


def cure_pet(pet):
    log("Poisoned — curing %s" % pet.Name, colors['cyan'])
    Spells.CastMagery('Arch Cure')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def heal_pet_chiv(pet):
    log("HP low — Close Wounds on %s" % pet.Name, colors['cyan'])
    Spells.CastChivalry('Close Wounds')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def bandage_pet(pet):
    if not _has_vet:
        return
    if Player.BuffsExist('Healing'):
        return
    bandage = Items.FindByID(BANDAGE_ITEM_ID, -1, Player.Backpack.Serial)
    if bandage is None:
        return
    log("Bandaging %s." % pet.Name, colors['cyan'])
    Items.UseItem(bandage.Serial)
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(BANDAGE_APPLY_MS)


def cast_animal_whispering(pet):
    global _last_whisper
    if not WHISPER_ENABLED:
        return
    if time.time() - _last_whisper < WHISPER_INTERVAL_SEC:
        return
    log("Casting Animal Whispering on %s." % pet.Name, colors['cyan'])
    Spells.Cast("Whispering")
    if Target.WaitForTarget(4000, False):
        Target.TargetExecute(pet.Serial)
    _last_whisper = time.time()


def _detect_combat_skills():
    global _has_chiv, _has_ranged, _has_meditation, _has_magery, _has_vet
    chiv = Player.GetSkillValue('Chivalry')
    archery = Player.GetSkillValue('Archery')
    throwing = Player.GetSkillValue('Throwing')
    meditation = Player.GetSkillValue('Meditation')
    magery = Player.GetSkillValue('Magery')
    vet = Player.GetSkillValue('Veterinary')

    _has_chiv = chiv >= CHIV_MIN_SKILL
    _has_ranged = archery >= RANGED_MIN_SKILL or throwing >= RANGED_MIN_SKILL
    _has_meditation = meditation >= MEDITATION_MIN_SKILL
    _has_magery = magery >= MAGERY_MIN_SKILL
    _has_vet = vet >= VET_MIN_SKILL

    if _has_magery:
        log("Magery %.1f — will use magery heals." % magery, colors['cyan'])
    if _has_chiv:
        log("Chivalry %.1f — will use Enemy of One + Divine Fury." % chiv, colors['cyan'])
        if not _has_magery:
            log("  No Magery — using Close Wounds for healing.", colors['cyan'])
    if _has_vet:
        log("Veterinary %.1f — will bandage pet at %.0f%% HP." % (
            vet, VET_THRESHOLD * 100), colors['cyan'])
    if _has_ranged:
        skill_name = 'Archery' if archery >= throwing else 'Throwing'
        log("%s %.1f — will auto-attack after engagement." % (
            skill_name, max(archery, throwing)), colors['cyan'])
    if _has_meditation:
        log("Meditation %.1f — will meditate for mana recovery." % meditation, colors['cyan'])
    else:
        log("No Meditation — throttling combat spells until %.0f%% mana." % (
            MANA_REGEN_TARGET * 100), colors['cyan'])


def apply_chiv_buffs():
    if not _has_chiv:
        return
    if Player.ManaMax == 0:
        return
    mana_ratio = float(Player.Mana) / Player.ManaMax
    threshold = COMBAT_MANA_FLOOR if _has_meditation else MANA_REGEN_TARGET
    if mana_ratio < threshold:
        return
    if not Player.BuffsExist('Enemy of One'):
        log("Casting Enemy of One.", colors['cyan'])
        Spells.CastChivalry("Enemy of One")
        Misc.Pause(1500)
    if not Player.BuffsExist('Divine Fury'):
        log("Casting Divine Fury.", colors['cyan'])
        Spells.CastChivalry("Divine Fury")
        Misc.Pause(1500)


def player_attack_enemy(enemy):
    global _attacking_serial
    if not _has_ranged or enemy is None:
        return
    if _attacking_serial != enemy.Serial:
        log("Attacking %s." % enemy.Name, colors['yellow'])
        _attacking_serial = enemy.Serial
    Player.Attack(enemy.Serial)


def _apply_death_ray(enemy):
    """Cast Death Ray if not already active and mana allows."""
    if Player.BuffsExist('Death Ray', False):
        return
    if Player.ManaMax == 0:
        return
    mana_ratio = float(Player.Mana) / Player.ManaMax
    threshold = COMBAT_MANA_FLOOR if _has_meditation else MANA_REGEN_TARGET
    if mana_ratio < threshold:
        return
    log("Casting Death Ray on %s." % enemy.Name, colors['red'])
    Spells.CastMastery('Death Ray')
    if Target.WaitForTarget(5000, False):
        Target.TargetExecute(enemy.Serial)
    Misc.Pause(500)


def mastery_attack(enemy):
    """Player combat action for the current tick, routed by active mastery buff."""
    if enemy is None:
        return
    if Player.BuffsExist('EnchantedSummoning'):
        _apply_death_ray(enemy)
    else:
        player_attack_enemy(enemy)


def manage_mana():
    """Activate Meditation when idle and mana is low.

    Called at the END of each tick so healing/combat actions for that tick have
    already fired.  Guards against three sources of spam/cancellation:
      1. Buff already active  — nothing to do, regen is running.
      2. Enemies in range     — any follow-up combat action would cancel it.
      3. Skill cooldown       — UO enforces ~11 s between attempts; we mirror
                                that with _last_med_attempt so we don't spam the
                                server on failed skill checks.
    """
    global _last_med_attempt
    if not _has_meditation:
        return
    if Player.ManaMax == 0:
        return
    if float(Player.Mana) / Player.ManaMax >= MANA_REGEN_TARGET:
        return
    if Player.BuffsExist('Meditation'):
        return
    if GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE):
        return
    if time.time() - _last_med_attempt < MEDITATION_COOLDOWN_SEC:
        return
    _last_med_attempt = time.time()
    log("Mana %.0f%% — meditating." % (
        float(Player.Mana) / Player.ManaMax * 100), colors['cyan'])
    Player.UseSkill('Meditation')


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

    if pet.Poisoned and hp_ratio < HEALTH_THRESHOLD:
        if _has_magery:
            cure_pet(pet)

    if hp_ratio < CRITICAL_HEALTH_THRESHOLD:
        if _has_magery:
            heal_pet_critical(pet)
        elif _has_chiv:
            heal_pet_chiv(pet)
    elif hp_ratio < HEALTH_THRESHOLD:
        if _has_magery:
            heal_pet(pet)
        elif _has_chiv:
            heal_pet_chiv(pet)

    if hp_ratio < VET_THRESHOLD:
        bandage_pet(pet)


def check_player_health():
    if Player.HitsMax == 0:
        return
    hp_ratio = float(Player.Hits) / Player.HitsMax
    if hp_ratio >= PLAYER_HEALTH_THRESHOLD:
        return
    log("Player HP low (%.0f%%) — healing self." % (hp_ratio * 100), colors['red'])

    if _has_magery:
        if INVIS_BEFORE_HEAL:
            Spells.CastMagery('Invisibility')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(Player.Serial)
            Misc.Pause(INVIS_SETTLE_MS)
        while Player.Hits < Player.HitsMax:
            if Player.Poisoned:
                Spells.CastMagery('Arch Cure')
                Target.WaitForTarget(3000, False)
                Target.TargetExecute(Player.Serial)
                Misc.Pause(1200)
            Spells.CastMagery('Greater Heal')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(Player.Serial)
            Misc.Pause(1200)
        log("Player healed to full.", colors['green'])
    elif _has_chiv:
        for _ in range(10):
            if Player.Hits >= Player.HitsMax:
                break
            Spells.CastChivalry('Close Wounds')
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(Player.Serial)
            Misc.Pause(1200)
        log("Player healed.", colors['green'])


def recall_pet(pet):
    log("Pet too far (%d tiles) — recalling." % Player.DistanceTo(pet), colors['yellow'])
    for i in range(FOLLOW_MAX_CHECKS):
        Player.ChatSay("all follow me")
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


def shutdown():
    if Player.IsGhost:
        log("Guardian stopped — player died.", colors['red'])
    elif not Player.Connected:
        log("Guardian stopped — disconnected.", colors['red'])
    else:
        log("Guardian stopped.", colors['cyan'])
    if not Player.IsGhost:
        Player.ChatSay("all guard me")


def hunt_cycle(pet, enemy_serial):
    """Send pet to kill an enemy, recall when engaged, guard when enemy closes.

    Phase 1 — watch until pet is within KILL_ENGAGE_RANGE of the enemy (or enemy dies).
    Phase 2 — recall pet using existing leash loop.
    Phase 3 — issue guard once enemy closes to GUARD_TRIGGER_RANGE; timeout after HUNT_GUARD_TIMEOUT s.

    Returns True if guard was issued, False otherwise.
    """
    # ── Phase 1: engagement watch ──────────────────────────────────────────────
    log("Hunting — waiting for pet to engage...", colors['yellow'])
    prev_enemy_dist  = None
    phase1_deadline  = time.time() + 30  # give up if pet never closes on enemy
    while Player.Connected and not Player.IsGhost and time.time() < phase1_deadline:
        check_pet_health(pet)
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
        enemy = Mobiles.FindBySerial(enemy_serial)
        if enemy is None:
            log("Enemy defeated.", colors['green'])
            return False  # enemy gone, no guard cycle needed
        curr_enemy_dist = Player.DistanceTo(enemy)
        if prev_enemy_dist is not None and curr_enemy_dist > prev_enemy_dist + 3:
            log("Enemy fleeing — re-tagging and recalling.", colors['yellow'])
            if not _send_kill(enemy_serial):
                return False
            Player.ChatSay("all follow me")
            break
        prev_enemy_dist = curr_enemy_dist
        pet_to_enemy = max(
            abs(pet.Position.X - enemy.Position.X),
            abs(pet.Position.Y - enemy.Position.Y),
        )
        if pet_to_enemy <= KILL_ENGAGE_RANGE:
            log("Pet engaged — recalling.", colors['yellow'])
            break
        Misc.Pause(CHECK_INTERVAL)

    # ── Phase 2: rapid recall (1s poll — much tighter than the 4s leash loop) ──
    log("Recalling pet after engagement.", colors['yellow'])
    for i in range(10):
        if i % 3 == 0:
            Player.ChatSay("all follow me")
        Misc.Pause(1000)
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
            if Player.DistanceTo(pet) <= PET_FOLLOW_RANGE:
                break

    # ── Phase 3: guard when enemy closes ──────────────────────────────────────
    log("Waiting for enemy to close (guard trigger = %d tiles)..." % GUARD_TRIGGER_RANGE, colors['yellow'])
    deadline = time.time() + HUNT_GUARD_TIMEOUT
    while time.time() < deadline and Player.Connected and not Player.IsGhost:
        fresh = find_pet()
        if fresh is not None:
            pet = fresh
        enemy = Mobiles.FindBySerial(enemy_serial)
        if enemy is None or Player.DistanceTo(enemy) <= GUARD_TRIGGER_RANGE:
            if pet is not None:
                _pet_cmd(pet.Serial, PET_CMD_GUARD)
            log("Guard issued — enemy in range.", colors['cyan'])
            return True
        Misc.Pause(500)

    log("Hunt guard timeout — resuming normal loop.", colors['yellow'])
    return False


def _prompt_kill_mode():
    """Ask the player to choose leash or kill mode. Returns 'leash' or 'kill'."""
    log("Kill mode — say the number:", colors['cyan'])
    log("  1) Leash  (tag, recall pet, guard when mob closes)", colors['cyan'])
    log("  2) Kill   (send pet to kill, walk to corpses)", colors['cyan'])
    Misc.Pause(400)
    Journal.Clear()

    deadline = time.time() + 30
    while time.time() < deadline:
        if Journal.SearchByName('1', Player.Name):
            Journal.Clear()
            return 'leash'
        if Journal.SearchByName('2', Player.Name):
            Journal.Clear()
            return 'kill'
        Misc.Pause(200)

    log("No mode selected (30s timeout) — defaulting to leash.", colors['yellow'])
    return 'leash'


def _kill_mode_loop():
    """Kill mode: send pet to kill targets, walk to corpses as they spawn."""
    looted = set()

    while Player.Connected and not Player.IsGhost:
        if Journal.Search(Player.Name + ": bank"):
            Journal.Clear()
            log("Bank command — depositing and stopping.", colors['yellow'])
            rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
            if rb is not None:
                do_banking(rb)
            return

        bank_gold_if_heavy()

        pet = find_pet()
        if pet is None:
            log("No pet found.", colors['yellow'])
            Misc.Pause(CHECK_INTERVAL)
            continue

        check_pet_health(pet)
        check_player_health()
        cast_animal_whispering(pet)

        enemies = [e for e in GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE)
                   if e.Serial not in _skip_serials]
        if enemies:
            nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
            if time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC:
                log("Enemy: %s — sending pet to kill." % nearest.Name, colors['red'])
                _send_kill(nearest.Serial)
            pet_to_enemy = max(
                abs(pet.Position.X - nearest.Position.X),
                abs(pet.Position.Y - nearest.Position.Y),
            )
            if pet_to_enemy <= KILL_ENGAGE_RANGE + 2:
                apply_chiv_buffs()
                mastery_attack(nearest)

        corpses = [c for c in scan_nearby_corpses(CORPSE_SCAN_RANGE)
                   if int(c.Serial) not in looted]
        if corpses:
            corpse = nearest_corpse(corpses)
            walk_to_corpse(corpse)
            looted.add(int(corpse.Serial))
            Misc.Pause(6000)
            rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
            if rb is not None:
                log("Recalling back to farm.", colors['cyan'])
                travel_to_named_rune(rb, FARM_RUNE_NAME, RECALL_SETTLE_DELAY)
                walk_steps(TRANSFER_FROM_STEPS)

        manage_mana()
        Misc.Pause(CHECK_INTERVAL)


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    global _session_start, _session_gold, FARM_RUNE_NAME, _kill_mode
    _session_start = time.time()
    _session_gold  = 0

    # ── Location prompt ───────────────────────────────────────────────────────
    Misc.SendMessage('[guardian] Farm location — say the number:', colors['cyan'])
    for i, loc in enumerate(FARM_LOCATIONS):
        Misc.SendMessage('[guardian]   %d) %s' % (i + 1, loc), colors['cyan'])
    Misc.Pause(600)
    Journal.Clear()
    Misc.Pause(200)
    Journal.Clear()

    chosen = None
    deadline = time.time() + 30
    while time.time() < deadline and chosen is None:
        for i, loc in enumerate(FARM_LOCATIONS):
            if Journal.SearchByName(str(i + 1), Player.Name):
                chosen = loc
                break
        Misc.Pause(200)

    if chosen is None:
        log("No location selected (30s timeout) — stopping.", colors['red'])
        return
    Journal.Clear()
    FARM_RUNE_NAME = chosen
    log("Target: %s" % FARM_RUNE_NAME, colors['cyan'])

    # ── Kill mode prompt ──────────────────────────────────────────────────────
    _kill_mode = _prompt_kill_mode()
    log("Kill mode: %s" % _kill_mode, colors['cyan'])

    # ── Pet discovery (before recall so mount is confirmed at the house) ─────
    if not discover_pet():
        log("Pet discovery failed — stopping.", colors['red'])
        return

    _detect_combat_skills()

    # ── Recall from house to farm location ────────────────────────────────────
    rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
    if rb is None:
        log("Runebook '%s' not found in backpack — stopping." % HOME_RUNEBOOK_NAME, colors['red'])
        return
    log("Recalling to '%s'..." % FARM_RUNE_NAME, colors['cyan'])
    if not travel_to_named_rune(rb, FARM_RUNE_NAME, RECALL_SETTLE_DELAY):
        log("Failed to recall to '%s' — stopping." % FARM_RUNE_NAME, colors['red'])
        return

    walk_steps(TRANSFER_FROM_STEPS)

    if TRANSFER_FROM_POS is not None:
        if not arrived_at(*TRANSFER_FROM_POS):
            log("Location check failed — expected %s, got (%d, %d)." % (
                TRANSFER_FROM_POS, Player.Position.X, Player.Position.Y), colors['red'])

    log("Guardian started (mode=%s)." % _kill_mode, colors['cyan'])
    Journal.Clear()
    log("Say 'bank' to deposit and stop.", colors['cyan'])

    try:
        if _kill_mode == 'kill':
            _kill_mode_loop()
            return

        is_guarding = False
        is_hunting  = False
        guard_pos   = None

        if find_pet() is not None:
            Player.ChatSay("all guard me")
            is_guarding = True
            guard_pos   = (Player.Position.X, Player.Position.Y)
            log("Default guard active.", colors['cyan'])

        while Player.Connected and not Player.IsGhost:
            if Journal.Search(Player.Name + ": bank"):
                Journal.Clear()
                log("Bank command — depositing and stopping.", colors['yellow'])
                rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
                if rb is not None:
                    do_banking(rb)
                break

            bank_gold_if_heavy()

            pet = find_pet()

            # Break guard when the player moves far enough from the guard origin.
            # Suppressed while enemies are adjacent — combat movement would otherwise
            # trigger "all follow me" every tick and cause a kill/follow spam loop.
            close_combat = len(GetEnemies(Mobiles, 0, GUARD_TRIGGER_RANGE)) > 0
            if is_guarding and guard_pos is not None and not close_combat:
                pos = Player.Position
                if max(abs(pos.X - guard_pos[0]), abs(pos.Y - guard_pos[1])) > GUARD_BREAK_DISTANCE:
                    is_guarding = False
                    guard_pos   = None
                    Player.ChatSay("all follow me")

            if pet is None:
                log("No pet found.", colors['yellow'])
                is_guarding = False
                guard_pos   = None
                Misc.Pause(CHECK_INTERVAL)
                continue

            guard_pet_if_low(pet)
            check_pet_health(pet)
            check_player_health()
            cast_animal_whispering(pet)

            # ── Recall if too far (skipped while guarding — pet drifts naturally) ──
            if not is_guarding and Player.DistanceTo(pet) > PET_FOLLOW_RANGE:
                guard_pos = None
                arrived   = recall_pet(pet)
                if not arrived:
                    fresh = find_pet()
                    if fresh is None or Player.DistanceTo(fresh) > PET_FOLLOW_RANGE + 1:
                        Misc.Pause(CHECK_INTERVAL)
                        continue
                    pet = fresh

            # ── Enemy scan → kill, or guard if clear ──────────────────────────
            # Guard and kill are mutually exclusive each tick: issuing both back-to-back
            # on the same pet causes the second context-menu call to silently fail.
            enemies = ([] if is_hunting
                       else [e for e in GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE)
                             if e.Serial not in _skip_serials])

            if enemies:
                nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
                if Player.DistanceTo(nearest) <= GUARD_TRIGGER_RANGE:
                    if time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC:
                        log("Enemy on us: %s — engaging in place." % nearest.Name, colors['yellow'])
                        _send_kill(nearest.Serial)
                    apply_chiv_buffs()
                    mastery_attack(nearest)
                    if not is_guarding:
                        is_guarding = True
                        guard_pos   = (Player.Position.X, Player.Position.Y)
                else:
                    log("Enemy: %s — sending pet to kill." % nearest.Name, colors['red'])
                    if not _send_kill(nearest.Serial):
                        Misc.Pause(CHECK_INTERVAL)
                        continue
                    is_guarding = False
                    guard_pos   = None
                    is_hunting  = True
                    did_guard   = hunt_cycle(pet, nearest.Serial)
                    is_hunting  = False
                    pet         = find_pet() or pet
                    if did_guard:
                        is_guarding = True
                        guard_pos   = (Player.Position.X, Player.Position.Y)
                        enemy = Mobiles.FindBySerial(nearest.Serial)
                        if enemy is not None:
                            apply_chiv_buffs()
                            mastery_attack(enemy)
                    else:
                        is_guarding = False
                        guard_pos   = None
                    Misc.Pause(CHECK_INTERVAL)
                    continue

            if not is_guarding:
                pos = Player.Position
                _pet_cmd(pet.Serial, PET_CMD_GUARD)
                is_guarding = True
                guard_pos   = (pos.X, pos.Y)

            manage_mana()
            Misc.Pause(CHECK_INTERVAL)

    finally:
        shutdown()


main()
