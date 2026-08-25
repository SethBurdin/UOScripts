# explorer_followbob.py
# Variant of explorer.py: instead of the player driving movement, the player
# auto-follows a named character (default "Bob") around the dungeon while the
# same pet-leash/kill, heal, and combat-assist logic from explorer.py runs.
# Change FOLLOW_NAME below to follow someone else.
#
# NOTE: since the player is no longer walked manually, weapon-skill melee
# attacks only land when the leader (or a retreat step / the pet's fight)
# happens to bring the player into striking range — magery/chivalry/pet
# damage still work at range regardless. Following pauses automatically
# while an enemy is on top of the player, so it won't drag you out of a
# fight the pet is already in.
#
# Startup (all answered in game chat, except the two clicks):
#   1. Say a name for the location — only used to tag the gold/hr stats entry.
#   2. Say 1 (leash: pet guards you, fights what reaches you) or
#      2 (kill: pet is sent at the nearest enemy in scan range).
#   3. Click Bob (the character to follow) when prompted.
#   4. Click your pet when prompted.
#
# Say 'bank' (normal or party chat — party members can trigger it too) to
# recall home, deposit gold/loot, log gold/hr to local/guardian_stats.json,
# and stop.  Hitting the weight threshold banks-and-stops the same way, since
# deep dungeon spots usually can't be recalled back into.
#
# Exception: if the clicked pet is a pack beetle (body 0x0317) the weight
# threshold offloads gold into its pack and the run continues; that gold is
# deposited on the next bank run. Any other pet has no container, so gold
# never gets handed to it — the threshold just banks.

if False:
    from razorenhanced_stubs import *

import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from glossary.colors import colors
from glossary.enemies import GetEnemies, GetFriendlyNotorieties
from glossary.runebook_handler import find_runebook_by_label, travel_to_named_rune
from utilities.mobiles import GetEmptyMobileList
from extraction_looter.containers_util import transfer_to_beetle

# ─── Config ───────────────────────────────────────────────────────────────────
CHECK_INTERVAL       = 1500   # ms between main loop ticks
PET_FOLLOW_RANGE     = 4      # tiles — beyond this the pet is called back
FOLLOW_CMD_COOLDOWN  = 4.0    # seconds between repeated "all follow me"
GUARD_CMD_COOLDOWN   = 8.0    # seconds between repeated "all guard me" (leash mode)
ENEMY_SCAN_RANGE     = 12     # tile radius to scan for hostiles each tick
GUARD_TRIGGER_RANGE  = 2      # enemy-to-player distance that counts as "on us"
KILL_ENGAGE_RANGE    = 1      # Chebyshev pet-to-enemy distance = engaged
KILL_COOLDOWN_SEC    = 8      # min seconds between kill commands per enemy
RETREAT_TRIGGER_RANGE = 4     # tiles — step away when an enemy spawns this close to the player
RETREAT_STEPS         = 4     # max tiles to step away from a close enemy

FRIEND_SCAN_RANGE    = 8      # tile radius for heal/cure candidates
RES_SCAN_RANGE       = 2      # tile radius for resurrecting player ghosts
CLOSE_WOUNDS_RANGE   = 2      # Close Wounds only reaches 2 tiles
BANDAGE_RANGE        = 2      # max tiles to attempt a vet bandage

# Health thresholds (ratios)
HEALTH_THRESHOLD          = 0.85   # heal below this
CRITICAL_HEALTH_THRESHOLD = 0.40   # self-heal loops until safe below this
VET_THRESHOLD             = 0.75   # bandage pet below this

# Skill minimums
CHIV_MIN_SKILL        = 30.0
MAGERY_MIN_SKILL      = 30.0
EBOLT_MIN_MAGERY      = 60.0   # Energy Bolt is 6th circle
RES_MIN_MAGERY        = 76.0   # Resurrection is 8th circle
WEAPON_MIN_SKILL      = 30.0   # any of sword/mace/fencing/wrestling/archery/throwing
MEDITATION_MIN_SKILL  = 30.0
VET_MIN_SKILL         = 30.0

MEDITATION_COOLDOWN_SEC = 11.0
COMBAT_MANA_FLOOR       = 0.30   # cast offensive/buff spells above this if player can meditate
MANA_REGEN_TARGET       = 0.90   # without meditation, throttle offense until this mana ratio

BANDAGE_ITEM_ID        = 0x0E21
BANDAGE_APPLY_MS       = 4000
BANDAGE_RESTOCK_TARGET = 100

# Animal Whispering mastery spell
WHISPER_ENABLED      = True
WHISPER_INTERVAL_SEC = 1800

# Banking (same house setup as guardian.py)
WEIGHT_BANK_THRESHOLD = 0.90
GOLD_DEST_SERIAL      = config.quick_dropbox
PACK_BEETLE_BODY      = 0x0317   # only this body has a pack we can offload gold into
BEETLE_OFFLOAD_RANGE  = 3        # tiles — beetle must be this close for Items.Move to succeed
BEETLE_RECALL_MS      = 2000     # ms to wait after "all follow me" when the beetle is too far
HOME_RUNEBOOK_NAME    = "home"
HOME_RUNE_NAME        = "new home"
RECALL_SETTLE_DELAY   = 2000
GOLD_ITEM_ID          = 0x0EED

TRANSFER_ITEMS = [
    0x1079,   # hides
    0x26B4, 0x26B5, 0x26B6, 0x26B7, 0x26B8, 0x26B9,   # scales
    0x14EB, 0x14EC,                                    # treasure maps
    0x423A,   # alchemy reagents (hue distinguishes variant)
    0x0F26, 0x0F25, 0x0F0F, 0x0F10, 0x0F15, 0x0F11, 0x0F13, 0x0F18, 0x0F16,  # gems
]

# Follow-the-leader (this variant only)
FOLLOW_NAME              = "bob"  # case-insensitive; change to follow someone else
FOLLOW_RANGE             = 3      # tiles — stop pathing once this close to the leader
FOLLOW_LOST_RANGE        = 30     # tiles — max distance the leader can be and still be tracked
FOLLOW_PATH_TIMEOUT_MS   = 6000   # overall ms bound per follow attempt (lets stuck-retries run)
FOLLOW_POLL_MS           = 100    # ms between position checks while pathing
FOLLOW_STUCK_LIMIT_MS    = 1200   # ms with no movement before treating the path as stuck
FOLLOW_MAX_RETRIES       = 2      # re-issue the path this many times before giving up
FOLLOW_LOST_SIGHT_GRACE_MS = 3000 # ms to tolerate the leader being unresolvable, as long as we're still moving
FOLLOW_GIVEUP_COOLDOWN_SEC = 5.0  # after giving up, stop trying to path to the leader for this long
FOLLOW_WARN_INTERVAL_SEC = 10.0   # seconds between "leader not found" log spam

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local/guardian_stats.json")
os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

# ─── State ────────────────────────────────────────────────────────────────────
_pet_serial      = None
_pet_is_beetle   = False   # True only when the locked pet's body is PACK_BEETLE_BODY
_leader_serial   = None
_session_start   = None
_session_gold    = 0
_location_label  = "explorer"
_kill_mode       = 'leash'

_has_chiv        = False
_has_magery      = False
_has_ebolt       = False
_has_res         = False
_has_weapon      = False
_has_meditation  = False
_has_vet         = False

_last_follow_cmd  = 0.0
_last_guard_cmd   = 0.0
_last_whisper     = 0.0
_last_med_attempt = 0.0
_last_leader_warn = 0.0
_last_follow_giveup = 0.0  # throttles re-attempts after a path to the leader failed/stalled
_kill_times       = {}     # { enemy_serial: timestamp } — throttle repeated kill commands
_skip_serials     = set()  # enemies that returned "Target cannot be seen."
_attacking_serial = None
_kill_target      = None   # serial the pet was last sent to kill; guard is re-issued when it dies


def log(msg, color=68):
    Misc.SendMessage("[explorer-bob] " + msg, color)


# ─── Safe targeting ───────────────────────────────────────────────────────────
# Notoriety is checked at scan time AND re-checked right before every
# TargetExecute, since flags can change during the ~2s a spell takes to cast.
# Beneficial casts on gray/criminal targets flag the caster; offensive casts
# on blues make the caster a criminal — both directions are guarded.

def _safe_to_help(serial):
    if serial == Player.Serial:
        return True
    mob = Mobiles.FindBySerial(serial)
    return mob is not None and mob.Notoriety in (1, 2, 7)  # innocent, ally, npc


def _is_re_friend(serial):
    """True if serial is on RazorEnhanced's client-side Friends list. Rechecked
    at attack time (not just when GetEnemies scans) as a defense-in-depth
    guard — the friends list itself doesn't change mid-fight, but this keeps
    the guarantee local to the targeting function instead of trusting every
    caller to have filtered through GetEnemies first."""
    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.RangeMin = 0
    f.RangeMax = ENEMY_SCAN_RANGE
    return any(m.Serial == serial for m in Mobiles.ApplyFilter(f))


def _safe_to_attack(serial):
    if serial == Player.Serial or serial == _pet_serial:
        return False
    mob = Mobiles.FindBySerial(serial)
    if mob is None or mob.InParty:
        return False
    if mob.Notoriety == 2:   # ally/guilded — never attack guildmates
        return False
    if _is_re_friend(serial):
        return False
    return mob.Notoriety in (3, 4, 5, 6)  # attackable, criminal, enemy, murderer


def _execute_beneficial(serial, name):
    """Call after Target.WaitForTarget() succeeds. Fires only if still safe."""
    if _safe_to_help(serial):
        Target.TargetExecute(serial)
        return True
    Target.Cancel()
    log("Skipped %s — flagged gray/criminal." % name, colors['yellow'])
    return False


def _execute_offensive(serial, name):
    """Call after Target.WaitForTarget() succeeds. Fires only if still hostile."""
    if _safe_to_attack(serial):
        Target.TargetExecute(serial)
        return True
    Target.Cancel()
    log("Skipped attack on %s — no longer a valid enemy." % name, colors['yellow'])
    return False


def _clear_stale_target():
    """Cancel any leftover targeting cursor before triggering an action that
    will pop its own. Without this, a cursor left open by a timed-out
    WaitForTarget() — most often the pet's "all kill" cursor arriving after
    its own wait gave up — sits there until the *next* unrelated action calls
    WaitForTarget(), which sees a cursor already active and returns
    immediately. That action then fires TargetExecute() on its own serial
    against the stale cursor's intent — e.g. a heal's friendly serial
    completing a dangling kill order and sending the pet after a party
    member. Call this right before every Spells.Cast*/Items.UseItem/"all
    kill" that is followed by a WaitForTarget()."""
    if Target.HasTarget():
        Target.Cancel()


# ─── Skill detection ──────────────────────────────────────────────────────────

def _detect_skills():
    global _has_chiv, _has_magery, _has_ebolt, _has_res
    global _has_weapon, _has_meditation, _has_vet

    chiv       = Player.GetSkillValue('Chivalry')
    magery     = Player.GetSkillValue('Magery')
    meditation = Player.GetSkillValue('Meditation')
    vet        = Player.GetSkillValue('Veterinary')
    weapon     = max(
        Player.GetSkillValue('Swordsmanship'),
        Player.GetSkillValue('Mace Fighting'),
        Player.GetSkillValue('Fencing'),
        Player.GetSkillValue('Wrestling'),
        Player.GetSkillValue('Archery'),
        Player.GetSkillValue('Throwing'),
    )

    _has_chiv       = chiv >= CHIV_MIN_SKILL
    _has_magery     = magery >= MAGERY_MIN_SKILL
    _has_ebolt      = magery >= EBOLT_MIN_MAGERY
    _has_res        = magery >= RES_MIN_MAGERY
    _has_weapon     = weapon >= WEAPON_MIN_SKILL
    _has_meditation = meditation >= MEDITATION_MIN_SKILL
    _has_vet        = vet >= VET_MIN_SKILL

    if _has_magery:
        log("Magery %.1f — magery heals/cures%s%s." % (
            magery,
            ", Energy Bolt" if _has_ebolt else "",
            ", Resurrection" if _has_res else ""), colors['cyan'])
    if _has_chiv:
        log("Chivalry %.1f — Enemy of One + Divine Fury%s." % (
            chiv, "" if _has_magery else ", Close Wounds for heals"), colors['cyan'])
    if _has_weapon:
        log("Weapon skill %.1f — will auto-attack engaged enemies." % weapon, colors['cyan'])
    if _has_vet:
        log("Veterinary %.1f — bandaging pet below %.0f%% HP." % (
            vet, VET_THRESHOLD * 100), colors['cyan'])
    if _has_meditation:
        log("Meditation %.1f — meditating for mana recovery." % meditation, colors['cyan'])
    elif _has_magery or _has_chiv:
        log("No Meditation — throttling offense until %.0f%% mana." % (
            MANA_REGEN_TARGET * 100), colors['cyan'])
    if not (_has_magery or _has_chiv or _has_vet):
        log("No healing skill found — running combat/leash assist only.", colors['yellow'])


def _mana_ok_for_offense():
    if Player.ManaMax == 0:
        return False
    threshold = COMBAT_MANA_FLOOR if _has_meditation else MANA_REGEN_TARGET
    return float(Player.Mana) / Player.ManaMax >= threshold


# ─── Startup prompts ──────────────────────────────────────────────────────────

def _prompt_location():
    """Capture a free-text location label from the player's own chat.
    Only used to tag the stats entry; defaults to 'explorer' on timeout."""
    log("Say a name for this location (30s, stats label only)...", colors['cyan'])
    Misc.Pause(400)
    Journal.Clear()
    prefix = Player.Name + ": "
    deadline = time.time() + 30
    while time.time() < deadline:
        for line in (Journal.GetTextByType('Regular') or []):
            text = line.strip()
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
            if text and text.lower() != Player.Name.lower():
                Journal.Clear()
                return text
        Misc.Pause(200)
    log("No name given — logging stats as 'explorer'.", colors['yellow'])
    return "explorer"


def _prompt_kill_mode():
    log("Pet mode — say the number:", colors['cyan'])
    log("  1) Leash  (pet guards you, fights what reaches you)", colors['cyan'])
    log("  2) Kill   (pet is sent at the nearest enemy)", colors['cyan'])
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


def _classify_pet(mob):
    """Record whether the locked pet is a pack beetle. Body ID alone decides —
    the Backpack layer is often not cached until the pack has been opened, so
    testing mob.Backpack here would mislabel a real beetle as container-less.
    Any other body (dragon, mare, ...) has no pack, so gold stays on us and the
    weight threshold banks instead."""
    global _pet_is_beetle
    _pet_is_beetle = mob.Body == PACK_BEETLE_BODY
    if _pet_is_beetle:
        log("Pet is a pack beetle — gold will offload to its pack when heavy.",
            colors['green'])
    else:
        log("Pet body 0x%X is not a pack beetle — no pack to offload into; "
            "will bank at %.0f%% weight." % (mob.Body, WEIGHT_BANK_THRESHOLD * 100),
            colors['yellow'])


def discover_pet():
    """Explorer can start mid-dungeon, so no mount-testing random mobiles —
    the player clicks the pet directly, with a nearest-friend fallback."""
    global _pet_serial
    log("Click your pet...", colors['cyan'])
    serial = Target.PromptTarget("Click your pet:")
    if serial and serial != 0:
        mob = Mobiles.FindBySerial(serial)
        if mob is not None and not mob.IsHuman and mob.Serial != Player.Serial:
            _pet_serial = mob.Serial
            log("Pet locked: %s (0x%X)" % (mob.Name, _pet_serial), colors['cyan'])
            _classify_pet(mob)
            return True
        log("That target isn't a usable pet.", colors['yellow'])

    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = ENEMY_SCAN_RANGE
    nearest, nearest_dist = None, 9999
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        d = Player.DistanceTo(mob)
        if d < nearest_dist:
            nearest, nearest_dist = mob, d
    if nearest is not None:
        _pet_serial = nearest.Serial
        log("Pet locked from friend list: %s (0x%X)" % (nearest.Name, _pet_serial), colors['cyan'])
        _classify_pet(nearest)
        return True
    return False


def find_pet():
    if _pet_serial is None:
        return None
    mob = Mobiles.FindBySerial(_pet_serial)
    if mob is not None and Player.DistanceTo(mob) <= ENEMY_SCAN_RANGE * 2:
        return mob
    return None


# ─── Leader discovery / following ─────────────────────────────────────────────

def _scan_for_leader():
    """Name match (case-insensitive) among nearby mobiles."""
    f = Mobiles.Filter()
    f.Enabled  = True
    f.RangeMin = 0
    f.RangeMax = FOLLOW_LOST_RANGE
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        if mob.Name and mob.Name.strip().lower() == FOLLOW_NAME.lower():
            return mob
    return None


def discover_leader():
    """Locks onto the character to follow. Click them when prompted; if the
    prompt times out (or the target isn't right), falls back to a name scan
    of nearby mobiles."""
    global _leader_serial
    log("Click %s (the character to follow)..." % FOLLOW_NAME, colors['cyan'])
    serial = Target.PromptTarget("Click %s:" % FOLLOW_NAME)
    if serial and serial != 0:
        mob = Mobiles.FindBySerial(serial)
        if mob is not None and mob.Serial != Player.Serial:
            _leader_serial = mob.Serial
            log("Following: %s (0x%X)" % (mob.Name, _leader_serial), colors['cyan'])
            return True
        log("That target isn't valid.", colors['yellow'])

    mob = _scan_for_leader()
    if mob is not None:
        _leader_serial = mob.Serial
        log("Found %s nearby by name: 0x%X" % (mob.Name, _leader_serial), colors['cyan'])
        return True
    return False


def find_leader():
    """Fetches the leader by serial. No distance gate here — RazorEnhanced's
    own object cache already drops mobiles once they're truly out of range,
    so an extra fixed-tile cutoff on top of that only meant giving up on a
    leader who was simply sprinting ahead but still tracked client-side."""
    if _leader_serial is None:
        return None
    return Mobiles.FindBySerial(_leader_serial)


def _walk_to_mobile(mobile, max_range):
    """Pathfinds toward a mobile without stalling — routes to the nearest
    adjacent tile rather than the mobile's own tile, since a mobile occupies
    its tile and PathFinding.Go stalls immediately if routed straight at it
    (same fix used in wool_collector.py's MoveToSheep).

    Detects being stuck (no movement for FOLLOW_STUCK_LIMIT_MS) and re-issues
    the path up to FOLLOW_MAX_RETRIES times before giving up, all bounded by
    FOLLOW_PATH_TIMEOUT_MS overall. Returns True once within max_range, False
    if it gave up, the leader stayed unresolvable past FOLLOW_LOST_SIGHT_GRACE_MS,
    or the player died/disconnected — callers should back off rather than call
    this again immediately.

    A leader who sprints out of the client's sight range makes
    Mobiles.FindBySerial() return None even though they haven't actually
    "disappeared" — they're just temporarily out of view. That's tolerated as
    long as the player's own position keeps changing (i.e. we're still
    walking the last route toward their last-known spot); only a leader
    that's unresolvable *and* our own movement has stalled counts as lost."""
    if Player.DistanceTo(mobile) <= max_range:
        return True

    def _go(pos):
        px, py = Player.Position.X, Player.Position.Y
        best_x, best_y, best_dist = pos.X, pos.Y, 9999
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            tx, ty = pos.X + dx, pos.Y + dy
            d = abs(tx - px) + abs(ty - py)
            if d < best_dist:
                best_dist = d
                best_x, best_y = tx, ty
        route = PathFinding.Route()
        route.X = best_x
        route.Y = best_y
        route.DebugMessage = False
        route.StopIfStuck = True
        PathFinding.Go(route)

    fresh = Mobiles.FindBySerial(mobile.Serial)
    if fresh is None:
        return False
    _go(fresh.Position)

    deadline      = time.time() + FOLLOW_PATH_TIMEOUT_MS / 1000.0
    last_pos      = Player.Position
    stuck_ms      = 0
    stuck_retries = 0
    lost_ms       = 0   # how long the leader has been unresolvable

    while time.time() < deadline:
        if not Player.Connected or Player.IsGhost:
            return False

        fresh   = Mobiles.FindBySerial(mobile.Serial)
        cur_pos = Player.Position
        moved   = cur_pos.X != last_pos.X or cur_pos.Y != last_pos.Y

        if fresh is None:
            # Out of sight, not necessarily gone — keep going as long as we're
            # still making our own progress toward their last-known position.
            if moved:
                lost_ms  = 0
                last_pos = cur_pos
            else:
                lost_ms += FOLLOW_POLL_MS
                if lost_ms >= FOLLOW_LOST_SIGHT_GRACE_MS:
                    return False
            Misc.Pause(FOLLOW_POLL_MS)
            continue

        lost_ms = 0
        if Player.DistanceTo(fresh) <= max_range:
            return True

        if moved:
            stuck_ms      = 0
            stuck_retries = 0
            last_pos      = cur_pos
        else:
            stuck_ms += FOLLOW_POLL_MS
            if stuck_ms >= FOLLOW_STUCK_LIMIT_MS:
                stuck_ms = 0
                stuck_retries += 1
                if stuck_retries >= FOLLOW_MAX_RETRIES:
                    return False   # path is genuinely blocked — let the caller back off
                _go(fresh.Position)

        Misc.Pause(FOLLOW_POLL_MS)

    fresh = Mobiles.FindBySerial(mobile.Serial)
    return fresh is not None and Player.DistanceTo(fresh) <= max_range


def follow_leader(leader, pet, enemies):
    """Keeps the player near the leader by pathfinding toward them each tick.
    Paused whenever the player is in range of the fight (same check
    player_combat uses to engage), so it doesn't drag the player off
    mid-combat. If the path to the leader is genuinely blocked, backs off for
    FOLLOW_GIVEUP_COOLDOWN_SEC instead of hammering pathfinding every tick —
    that repeated-retry loop is what looked like a lockup. A failed attempt
    also triggers a fresh name-scan for the leader: find_leader() only
    reacquires when the tracked serial goes completely unresolvable, but a
    stuck path more often means the cached mobile is still "found" — just
    behind something, or its last-known position is stale — so re-scanning
    here can pick up a fresher/reachable reference."""
    global _last_leader_warn, _last_follow_giveup, _leader_serial

    if _player_engaged(pet, enemies):
        return

    if leader is None:
        if time.time() - _last_leader_warn > FOLLOW_WARN_INTERVAL_SEC:
            log("%s not in range — holding position." % FOLLOW_NAME, colors['yellow'])
            _last_leader_warn = time.time()
        return

    if Player.DistanceTo(leader) <= FOLLOW_RANGE:
        return

    if time.time() - _last_follow_giveup < FOLLOW_GIVEUP_COOLDOWN_SEC:
        return

    if not _walk_to_mobile(leader, FOLLOW_RANGE):
        log("Can't reach %s — waiting %.0fs before retrying." % (
            FOLLOW_NAME, FOLLOW_GIVEUP_COOLDOWN_SEC), colors['yellow'])
        _last_follow_giveup = time.time()
        rescanned = _scan_for_leader()
        if rescanned is not None and rescanned.Serial != leader.Serial:
            log("Reacquired %s at a different mobile — will retry with that one." % FOLLOW_NAME, colors['cyan'])
            _leader_serial = rescanned.Serial


# ─── Friend / ghost scans ─────────────────────────────────────────────────────

def _get_friends():
    """Living friendly mobiles in range that are safe to cast beneficial spells
    on. IsGhost=0 means a dead pet or player can never appear here."""
    f = Mobiles.Filter()
    f.Enabled     = True
    f.IsGhost     = 0
    f.Friend      = 1
    f.RangeMin    = 0
    f.RangeMax    = FRIEND_SCAN_RANGE
    f.Notorieties = GetFriendlyNotorieties()
    result = GetEmptyMobileList(Mobiles)
    result.AddRange(Mobiles.ApplyFilter(f))
    return [m for m in result if m.Serial != Player.Serial]


def _get_player_ghosts():
    """Dead PLAYERS in resurrect range. IsHuman=1 keeps dead pets out —
    Resurrection can't res a pet, and we never target ghosts otherwise."""
    f = Mobiles.Filter()
    f.Enabled     = True
    f.IsGhost     = 1
    f.IsHuman     = 1
    f.RangeMin    = 0
    f.RangeMax    = RES_SCAN_RANGE
    f.Notorieties = GetFriendlyNotorieties()
    result = GetEmptyMobileList(Mobiles)
    result.AddRange(Mobiles.ApplyFilter(f))
    return [m for m in result if m.Serial != Player.Serial]


# ─── Healing / care ───────────────────────────────────────────────────────────

def _heal_range():
    """How far the available heal actually reaches."""
    return FRIEND_SCAN_RANGE if _has_magery else CLOSE_WOUNDS_RANGE


def _in_heal_range(serial):
    if serial == Player.Serial:
        return True
    mob = Mobiles.FindBySerial(serial)
    return mob is not None and Player.DistanceTo(mob) <= _heal_range()


def _cast_heal(serial, name):
    if not _in_heal_range(serial):
        return
    _clear_stale_target()
    if _has_magery:
        Spells.CastMagery('Greater Heal')
    elif _has_chiv:
        Spells.CastChivalry('Close Wounds')
    else:
        return
    if Target.WaitForTarget(4000, False):
        _execute_beneficial(serial, name)
    Misc.Pause(1200)


def _cast_cure(serial, name):
    if not _has_magery:
        return
    _clear_stale_target()
    Spells.CastMagery('Arch Cure')
    if Target.WaitForTarget(4000, False):
        _execute_beneficial(serial, name)
    Misc.Pause(1200)


def resurrect_ghosts():
    """Res friendly player ghosts in range — only if the player actually can."""
    if not _has_res:
        return False
    ghosts = _get_player_ghosts()
    if not ghosts:
        return False
    ghost = ghosts[0]
    log("Resurrecting %s." % ghost.Name, colors['cyan'])
    _clear_stale_target()
    Spells.CastMagery('Resurrection')
    if Target.WaitForTarget(5000, False):
        _execute_beneficial(ghost.Serial, ghost.Name)
    Misc.Pause(2000)
    return True


def bandage_pet(pet):
    """Vet bandage runs alongside spell heals — it doesn't block casting."""
    if not _has_vet or pet is None or pet.HitsMax == 0:
        return
    if Player.DistanceTo(pet) > BANDAGE_RANGE:
        return
    if float(pet.Hits) / pet.HitsMax >= VET_THRESHOLD:
        return
    if Player.BuffsExist('Healing'):
        return
    bandage = Items.FindByID(BANDAGE_ITEM_ID, -1, Player.Backpack.Serial)
    if bandage is None:
        return
    log("Bandaging %s." % pet.Name, colors['cyan'])
    _clear_stale_target()
    Items.UseItem(bandage.Serial)
    if Target.WaitForTarget(3000, False):
        _execute_beneficial(pet.Serial, pet.Name)


def care_cycle(pet):
    """One beneficial cast per tick, by priority:
      1. self critical      → heal until above critical
      2. self poisoned      → cure
      3. player ghost + res → resurrect
      4. poisoned friend/pet → cure
      5. lowest-HP among self, pet, friends below threshold → heal
    Returns True if a cast was made."""
    if not (_has_magery or _has_chiv):
        bandage_pet(pet)
        return False

    if Player.HitsMax > 0:
        hp_ratio = float(Player.Hits) / Player.HitsMax
        if hp_ratio < CRITICAL_HEALTH_THRESHOLD:
            log("Player HP critical (%.0f%%) — emergency self-heal." % (hp_ratio * 100), colors['red'])
            while Player.Connected and not Player.IsGhost and \
                    float(Player.Hits) / Player.HitsMax < HEALTH_THRESHOLD:
                if Player.Poisoned:
                    _cast_cure(Player.Serial, 'self')
                _cast_heal(Player.Serial, 'self')
            return True
        if Player.Poisoned:
            log("Curing self.", colors['cyan'])
            _cast_cure(Player.Serial, 'self')
            return True

    if resurrect_ghosts():
        return True

    candidates = _get_friends()
    if pet is not None and not pet.IsGhost and all(m.Serial != pet.Serial for m in candidates):
        candidates.append(pet)

    bandage_pet(pet)

    poisoned = [m for m in candidates
                if m.Poisoned and Player.DistanceTo(m) <= FRIEND_SCAN_RANGE]
    if poisoned and _has_magery:
        target = min(poisoned, key=lambda m: m.Hits)
        log("Curing %s." % target.Name, colors['cyan'])
        _cast_cure(target.Serial, target.Name)
        return True

    damaged = [m for m in candidates
               if m.HitsMax > 0 and float(m.Hits) / m.HitsMax < HEALTH_THRESHOLD
               and Player.DistanceTo(m) <= _heal_range()]
    if Player.HitsMax > 0 and float(Player.Hits) / Player.HitsMax < HEALTH_THRESHOLD:
        damaged.append(Player)
    if damaged:
        target = min(damaged, key=lambda m: float(m.Hits) / m.HitsMax)
        name = 'self' if target.Serial == Player.Serial else target.Name
        log("Healing %s (%.0f%%)." % (
            name, float(target.Hits) / target.HitsMax * 100), colors['cyan'])
        _cast_heal(target.Serial, name)
        return True

    return False


def cast_animal_whispering(pet):
    global _last_whisper
    if not WHISPER_ENABLED or pet is None:
        return
    if time.time() - _last_whisper < WHISPER_INTERVAL_SEC:
        return
    log("Casting Animal Whispering on %s." % pet.Name, colors['cyan'])
    _clear_stale_target()
    Spells.Cast("Whispering")
    if Target.WaitForTarget(4000, False):
        _execute_beneficial(pet.Serial, pet.Name)
    _last_whisper = time.time()


# ─── Pet management ───────────────────────────────────────────────────────────

def _say_follow():
    global _last_follow_cmd
    if time.time() - _last_follow_cmd < FOLLOW_CMD_COOLDOWN:
        return
    Player.ChatSay("all follow me")
    _last_follow_cmd = time.time()


def _say_guard(force=False):
    global _last_guard_cmd
    if not force and time.time() - _last_guard_cmd < GUARD_CMD_COOLDOWN:
        return
    Player.ChatSay("all guard me")
    _last_guard_cmd = time.time()


def _reguard_if_kill_done():
    """Once the pet's kill target is dead or gone, put the pet straight back on
    guard (cooldown bypassed). Runs every tick in both modes — every 'all kill'
    is always followed by an 'all guard me' when the fight ends."""
    global _kill_target
    if _kill_target is None:
        return
    mob = Mobiles.FindBySerial(_kill_target)
    if mob is None or mob.IsGhost:
        log("Kill target down — pet back to guard.", colors['cyan'])
        _kill_target = None
        _say_guard(force=True)


def _retreat_from(enemy):
    """Step away from an enemy that spawned close to the player, one tile at a
    time along the dominant axis away from it. Stops early once the enemy is
    outside RETREAT_TRIGGER_RANGE or disappears."""
    for _ in range(RETREAT_STEPS):
        mob = Mobiles.FindBySerial(enemy.Serial)
        if mob is None:
            return
        if Player.DistanceTo(mob) > RETREAT_TRIGGER_RANGE:
            return
        dx = Player.Position.X - mob.Position.X
        dy = Player.Position.Y - mob.Position.Y
        if abs(dx) >= abs(dy):
            direction = 'East' if dx >= 0 else 'West'
        else:
            direction = 'South' if dy >= 0 else 'North'
        Player.Walk(direction)
        Misc.Pause(300)


def _send_kill(target_serial):
    global _kill_target
    Journal.Clear()
    _clear_stale_target()
    Player.ChatSay("all kill")
    Misc.Pause(300)
    if not Target.WaitForTarget(2000, False):
        # No cursor showed up in time — cancel rather than leave it dangling
        # for a later heal/cure to accidentally consume, and don't book this
        # as a kill that was actually sent.
        Target.Cancel()
        return False
    if not _safe_to_attack(target_serial):
        Target.Cancel()
        return False
    Target.TargetExecute(target_serial)
    Misc.Pause(600)
    if Journal.Search("Target cannot be seen."):
        log("Target cannot be seen — skipping 0x%X." % target_serial, colors['yellow'])
        _skip_serials.add(target_serial)
        return False
    _kill_times[target_serial] = time.time()
    _kill_target = target_serial
    # Guard immediately after the kill order — the pet still attacks the tagged
    # target but stays anchored to the player instead of chasing off-leash.
    _say_guard(force=True)
    return True


def manage_pet(pet, enemies):
    """Leash + engagement, non-blocking — the player never stops moving.

    Leash mode: pet stays on guard; kill is only issued for enemies that
    close to GUARD_TRIGGER_RANGE. Kill mode: nearest enemy in scan range
    gets the pet sent at it."""
    too_far = Player.DistanceTo(pet) > PET_FOLLOW_RANGE

    if too_far:
        # Guard already recalls the pet after a finished kill; only chase
        # with "follow" when the pet is off-leash without a kill in progress.
        if _kill_target is None:
            _say_follow()
        return

    if not enemies:
        if _kill_mode == 'leash':
            _say_guard()
        return

    nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
    engage = (_kill_mode == 'kill'
              or Player.DistanceTo(nearest) <= GUARD_TRIGGER_RANGE)
    if engage and time.time() - _kill_times.get(nearest.Serial, 0) >= KILL_COOLDOWN_SEC:
        log("Enemy: %s — sending pet to kill." % nearest.Name, colors['red'])
        _send_kill(nearest.Serial)


# ─── Player combat ────────────────────────────────────────────────────────────

def apply_chiv_buffs():
    if not _has_chiv or not _mana_ok_for_offense():
        return
    if not Player.BuffsExist('Enemy of One'):
        log("Casting Enemy of One.", colors['cyan'])
        Spells.CastChivalry("Enemy of One")
        Misc.Pause(1500)
    if not Player.BuffsExist('Divine Fury'):
        log("Casting Divine Fury.", colors['cyan'])
        Spells.CastChivalry("Divine Fury")
        Misc.Pause(1500)


def cast_energy_bolt(enemy):
    if not _has_ebolt or not _mana_ok_for_offense():
        return
    log("Energy Bolt → %s." % enemy.Name, colors['red'])
    _clear_stale_target()
    Spells.CastMagery('Energy Bolt')
    if Target.WaitForTarget(4000, False):
        _execute_offensive(enemy.Serial, enemy.Name)
    Misc.Pause(600)


def _player_engaged(pet, enemies):
    """True once the fight is actually joined — pet engaged with the nearest
    enemy, or that enemy is on the player. Shared by player_combat (to decide
    whether to attack) and follow_leader (to decide whether to hold position
    instead of walking toward the leader)."""
    if not enemies:
        return False
    nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
    pet_engaged = pet is not None and max(
        abs(pet.Position.X - nearest.Position.X),
        abs(pet.Position.Y - nearest.Position.Y),
    ) <= KILL_ENGAGE_RANGE + 2
    return pet_engaged or Player.DistanceTo(nearest) <= GUARD_TRIGGER_RANGE


def player_combat(pet, enemies):
    """Attack/cast only once the fight is actually joined — pet engaged or the
    enemy is on the player — so ranged attacks don't pull fresh aggro."""
    global _attacking_serial
    if not enemies:
        _attacking_serial = None
        return
    nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
    if not _player_engaged(pet, enemies):
        return
    if not _safe_to_attack(nearest.Serial):
        return

    apply_chiv_buffs()
    if _has_weapon:
        if _attacking_serial != nearest.Serial:
            log("Attacking %s." % nearest.Name, colors['yellow'])
            _attacking_serial = nearest.Serial
        Player.Attack(nearest.Serial)
    cast_energy_bolt(nearest)


def manage_mana():
    global _last_med_attempt
    if not _has_meditation or Player.ManaMax == 0:
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


# ─── Banking ──────────────────────────────────────────────────────────────────

def _append_gold_stat(gold_this_trip):
    global _session_gold
    _session_gold += gold_this_trip
    elapsed = time.time() - _session_start
    gph = int(_session_gold / elapsed * 3600) if elapsed > 0 else 0
    entry = {
        "player":        Player.Name,
        "rune":          _location_label,
        "time":          time.strftime("%Y-%m-%d %H:%M:%S"),
        "gold_per_hour": gph,
        "script":        "explorer_followbob",
    }
    try:
        with open(STATS_FILE, "r") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = []
    data.append(entry)
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log("Gold/hr: %d  (session: %d gold, %.1f min)" % (
        gph, _session_gold, elapsed / 60), colors['cyan'])


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
        log("Gold destination (0x%X) not found." % GOLD_DEST_SERIAL, colors['red'])
        return 0
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


def unload_beetle_gold():
    """Deposit gold parked in the beetle's pack into the drop box. No-op for a
    non-beetle pet (nothing was ever put there) or when the beetle didn't make
    the trip home — in that case the gold stays safe in its pack until the next
    bank run, so this only warns."""
    if not _pet_is_beetle:
        return 0

    pet = find_pet()
    if pet is None:
        log("Beetle not here — its gold stays in the pack.", colors['yellow'])
        return 0

    dest = Items.FindBySerial(GOLD_DEST_SERIAL)
    if dest is None:
        log("Gold destination (0x%X) not found — beetle not unloaded." % GOLD_DEST_SERIAL,
            colors['red'])
        return 0

    pack = _get_pet_pack(pet)
    if pack is None:
        log("Beetle pack not accessible — beetle not unloaded.", colors['yellow'])
        return 0

    total = 0
    gold  = Items.FindByID(GOLD_ITEM_ID, -1, pack.Serial)
    while gold is not None:
        amount = gold.Amount
        Items.Move(gold, dest, amount)
        Misc.Pause(800)
        # Still in the pack with the same serial means the move was rejected
        still = Items.FindByID(GOLD_ITEM_ID, -1, pack.Serial)
        if still is not None and still.Serial == gold.Serial:
            log("Gold move from beetle rejected — stopping unload.", colors['yellow'])
            break
        total += amount
        gold = still
    if total:
        log("Deposited %d gold from the beetle." % total, colors['cyan'])
    return total


def _restock_bandages():
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
    log("Restocking %d bandages." % to_take, colors['cyan'])
    Items.Move(in_box, Player.Backpack, to_take)
    Misc.Pause(800)


def _walk_to_drop():
    for direction in ('East', 'North', 'West'):
        Player.Walk(direction)
        Misc.Pause(600)


def do_banking():
    """Travel home, deposit everything, log stats. The script stops after —
    deep dungeon spots usually can't be recalled back into."""
    rb = find_runebook_by_label(HOME_RUNEBOOK_NAME)
    if rb is None:
        log("No runebook named '%s' in backpack — cannot bank." % HOME_RUNEBOOK_NAME, colors['red'])
        return False
    if not travel_to_named_rune(rb, HOME_RUNE_NAME, RECALL_SETTLE_DELAY):
        log("Failed to travel home — banking aborted.", colors['red'])
        return False
    _walk_to_drop()
    gold = transfer_gold()
    gold += unload_beetle_gold()
    transfer_loot_to_chest()
    _restock_bandages()
    if gold:
        _append_gold_stat(gold)
    return True


def _bank_requested():
    """'bank' from the player's own regular chat, or from anyone in party chat."""
    if Journal.Search(Player.Name + ": bank"):
        return True
    if Journal.SearchByType("bank", "Party"):
        return True
    return False


def _weight_heavy():
    if Player.MaxWeight == 0:
        return False
    return float(Player.Weight) / Player.MaxWeight >= WEIGHT_BANK_THRESHOLD


def _get_pet_pack(pet):
    """Open the pet's pack and return it. Only meaningful for a pack beetle;
    the pack must be opened before Items.Move into it will land."""
    pack = pet.Backpack
    if pack is None:
        return None
    Items.UseItem(pack)
    Items.WaitForContents(pack.Serial, 3000)
    Misc.Pause(600)
    return pack


def offload_gold_to_pet():
    """Move all backpack gold into the pet's pack so the run can continue past
    the weight threshold. Only ever runs for a pack beetle — every other pet
    body has no container, and dropping gold on a container-less pet silently
    fails (or worse, drops it on the ground).

    Returns True if gold moved and we're back under the weight threshold."""
    if not _pet_is_beetle:
        return False

    pet = find_pet()
    if pet is None:
        log("Beetle not in range to offload gold.", colors['yellow'])
        return False

    if Player.DistanceTo(pet) > BEETLE_OFFLOAD_RANGE:
        Player.ChatSay("all follow me")
        Misc.Pause(BEETLE_RECALL_MS)
        pet = find_pet()
        if pet is None or Player.DistanceTo(pet) > BEETLE_OFFLOAD_RANGE:
            log("Beetle too far to offload gold — banking instead.", colors['yellow'])
            return False

    pack = _get_pet_pack(pet)
    if pack is None:
        log("Beetle pack not accessible — banking instead.", colors['yellow'])
        return False

    moved = 0
    gold  = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)
    while gold is not None:
        amount = gold.Amount
        _, full = transfer_to_beetle(gold, pack)
        if full:
            log("Beetle pack full — banking instead.", colors['yellow'])
            break
        moved += amount
        gold = Items.FindByID(GOLD_ITEM_ID, -1, Player.Backpack.Serial)

    if moved:
        log("Offloaded %d gold to the beetle." % moved, colors['green'])
    return moved > 0 and not _weight_heavy()


# ─── Main ─────────────────────────────────────────────────────────────────────

def shutdown():
    if Player.IsGhost:
        log("Explorer stopped — player died.", colors['red'])
    elif not Player.Connected:
        log("Explorer stopped — disconnected.", colors['red'])
    else:
        log("Explorer stopped.", colors['cyan'])
    if Player.Connected and not Player.IsGhost:
        Player.ChatSay("all guard me")


def main():
    global _session_start, _session_gold, _location_label, _kill_mode, _leader_serial
    _session_start = time.time()
    _session_gold  = 0

    _location_label = _prompt_location()
    log("Location: %s" % _location_label, colors['cyan'])

    _kill_mode = _prompt_kill_mode()
    log("Pet mode: %s" % _kill_mode, colors['cyan'])

    if not discover_leader():
        log("%s not found — stopping." % FOLLOW_NAME, colors['red'])
        return

    if not discover_pet():
        log("No pet found — stopping.", colors['red'])
        return

    _detect_skills()

    if find_runebook_by_label(HOME_RUNEBOOK_NAME) is None:
        log("Warning: no '%s' runebook in backpack — 'bank' will fail." % HOME_RUNEBOOK_NAME, colors['yellow'])

    log("Explorer started (mode=%s). Following %s — I'll keep up and fight." % (
        _kill_mode, FOLLOW_NAME), colors['cyan'])
    log("Say 'bank' (self or party chat) to deposit and stop.", colors['cyan'])
    Journal.Clear()
    Player.ChatSay("all follow me")

    try:
        while Player.Connected and not Player.IsGhost:
            if _bank_requested():
                Journal.Clear()
                log("Bank command — heading home.", colors['yellow'])
                do_banking()
                break

            if _weight_heavy():
                # A pack beetle can take the gold and keep us out here; any
                # other pet has no container, so the only option is to bank.
                if offload_gold_to_pet():
                    log("Weight relieved by the beetle — continuing.", colors['green'])
                else:
                    log("Weight at %.0f%% — banking and stopping." % (
                        float(Player.Weight) / Player.MaxWeight * 100), colors['yellow'])
                    do_banking()
                    break

            pet = find_pet()
            if pet is None:
                log("Pet not in range.", colors['yellow'])

            leader = find_leader()
            if leader is None:
                # Try a name-based reacquire — the leader may just have moved
                # out of tracking range and come back, or been re-logged.
                reacquired = _scan_for_leader()
                if reacquired is not None:
                    _leader_serial = reacquired.Serial
                    leader = reacquired

            # Runs even when the pet is out of detection range — that's exactly
            # when it's off on a kill and needs the guard recall.
            _reguard_if_kill_done()

            care_cycle(pet)
            cast_animal_whispering(pet)

            enemies = [e for e in GetEnemies(Mobiles, 0, ENEMY_SCAN_RANGE)
                       if e.Serial not in _skip_serials]

            # Enemy spawned on top of us — step away, then immediately re-tag
            # so the pet intercepts (bypasses the kill cooldown).
            if enemies:
                nearest = min(enemies, key=lambda e: Player.DistanceTo(e))
                if Player.DistanceTo(nearest) <= RETREAT_TRIGGER_RANGE:
                    log("Enemy %s is %d tiles from us — stepping away." % (
                        nearest.Name, Player.DistanceTo(nearest)), colors['yellow'])
                    _retreat_from(nearest)
                    if pet is not None:
                        _send_kill(nearest.Serial)

            if pet is not None:
                manage_pet(pet, enemies)
            player_combat(pet, enemies)

            manage_mana()
            follow_leader(leader, pet, enemies)
            Misc.Pause(CHECK_INTERVAL)
    finally:
        shutdown()


main()
