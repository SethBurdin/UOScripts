import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if False:
    from razorenhanced_stubs import *

from utilities.mobiles import GetEmptyMobileList
from glossary.colors import colors
from glossary.enemies import GetFriendlyNotorieties

# ── Config ────────────────────────────────────────────────────────────────────
SCAN_RANGE           = 8    # tile radius to scan for friends
BLESS_DURATION_SEC   = 120  # seconds before re-blessing a target
RENEWAL_DURATION_SEC = 120  # seconds before re-casting Gift of Renewal

# ── Skill detection (evaluated once at start) ─────────────────────────────────
_has_mysticism    = Player.GetSkillValue('Mysticism') > 0
_has_spellweaving = Player.GetSkillValue('Spell Weaving') > 0
_can_bless        = Player.GetSkillValue('Evaluating Intelligence') >= 50

# ── Timing trackers ───────────────────────────────────────────────────────────
_bless_times   = {}   # { serial: timestamp of last bless cast }
_renewal_times = {}   # { serial: timestamp of last Gift of Renewal cast }

def _is_blessed(mob):
    return time.time() - _bless_times.get(mob.Serial, 0) < BLESS_DURATION_SEC

def _has_renewal(mob):
    return time.time() - _renewal_times.get(mob.Serial, 0) < RENEWAL_DURATION_SEC


# ── Safe targeting ───────────────────────────────────────────────────────────
# Razor's "Friend" list is a manually curated whitelist — it says nothing about
# a mobile's current in-game notoriety. A listed friend can still be flagged
# gray/attackable or criminal (e.g. they hit something they shouldn't have),
# and casting a beneficial spell on a gray/criminal target flags the caster
# gray too. So candidates are filtered by notoriety at scan time, AND
# re-checked immediately before each TargetExecute since notoriety can change
# during the ~1.5-2s spell cast.

def _safe_to_help(serial):
    if serial == Player.Serial:
        return True
    mob = Mobiles.FindBySerial(serial)
    return mob is not None and mob.Notoriety in (1, 2, 7)  # innocent, ally, npc

def _execute_safe_target(serial, name):
    """Call after Target.WaitForTarget() succeeds. Executes the target only if
    still safe to help; otherwise cancels the cursor and returns False."""
    if _safe_to_help(serial):
        Target.TargetExecute(serial)
        return True
    Target.Cancel()
    Player.HeadMessage(colors['yellow'], 'Skipped %s — flagged gray/criminal' % name)
    return False


# ── Friend scan ───────────────────────────────────────────────────────────────

def _get_friends():
    """Returns living (non-ghost) friendly mobiles within range that are
    currently safe to cast beneficial spells on."""
    f = Mobiles.Filter()
    f.IsGhost      = 0
    f.Friend       = 1
    f.RangeMin     = 0
    f.RangeMax     = SCAN_RANGE
    f.Notorieties  = GetFriendlyNotorieties()
    result = GetEmptyMobileList(Mobiles)
    result.AddRange(Mobiles.ApplyFilter(f))
    return result

def _get_ghosts():
    """Returns friendly ghosts within range that are currently safe to
    resurrect (see _safe_to_help)."""
    f = Mobiles.Filter()
    f.IsGhost      = 1
    f.Friend       = 1
    f.RangeMin     = 0
    f.RangeMax     = 2
    f.Notorieties  = GetFriendlyNotorieties()
    result = GetEmptyMobileList(Mobiles)
    result.AddRange(Mobiles.ApplyFilter(f))
    return result


# ── Resurrect ────────────────────────────────────────────────────────────────

def ResurrectGhosts():
    """Cast Resurrection on each friendly ghost in range.
    Returns True if at least one cast was made."""
    ghosts = _get_ghosts()
    if len(ghosts) == 0:
        return False
    for ghost in ghosts:
        Player.HeadMessage(colors['cyan'], 'Resurrecting %s' % ghost.Name)
        Spells.CastMagery('Resurrection')
        if Target.WaitForTarget(5000, False):
            _execute_safe_target(ghost.Serial, ghost.Name)
        Misc.Pause(2000)
    return True


# ── Heal / cure ───────────────────────────────────────────────────────────────

def _cast_heal_cure(serial, name):
    """Cast the best available heal+cure spell at the given serial."""
    if _has_mysticism:
        # Cleansing Winds heals and cures in one cast
        Spells.CastMysticism('Cleansing Winds')
        if Target.WaitForTarget(5000, False):
            _execute_safe_target(serial, name)
        Misc.Pause(1700)
    else:
        Spells.CastMagery('Greater Heal')
        if Target.WaitForTarget(5000, False):
            _execute_safe_target(serial, name)
        Misc.Pause(1700)

def _cast_cure(serial, name):
    """Cast the best available cure at the given serial."""
    if _has_mysticism:
        Spells.CastMysticism('Cleansing Winds')
        if Target.WaitForTarget(5000, False):
            _execute_safe_target(serial, name)
        Misc.Pause(1700)
    else:
        Spells.CastMagery('Arch Cure')
        if Target.WaitForTarget(4000, False):
            _execute_safe_target(serial, name)
        Misc.Pause(1500)

def HealPets():
    """Priority 1 — cure any poisoned target (self first, then lowest-HP friend).
       Priority 2 — heal the lowest-HP target among self + friends.
       Returns True if a spell was cast."""
    friends = _get_friends()

    # Priority 1: poisoned targets — self first, then friends
    if Player.Poisoned:
        Player.HeadMessage(colors['cyan'], 'Curing self (%d%%)' % (
            int(float(Player.Hits) / Player.HitsMax * 100)))
        _cast_cure(Player.Serial, 'self')
        return True

    poisoned_friends = [m for m in friends if m.Poisoned]
    if poisoned_friends:
        target = min(poisoned_friends, key=lambda m: m.Hits)
        Player.HeadMessage(colors['cyan'], 'Curing %s (%d%%)' % (
            target.Name, int(float(target.Hits) / target.HitsMax * 100)))
        _cast_cure(target.Serial, target.Name)
        return True

    # Priority 2: heal lowest-HP target among self + friends
    candidates = list(friends)
    if Player.HitsMax > 0 and Player.Hits < Player.HitsMax:
        candidates.append(Player)

    damaged = [m for m in candidates if m.HitsMax > 0 and m.Hits < m.HitsMax]
    if damaged:
        target = min(damaged, key=lambda m: float(m.Hits) / m.HitsMax)
        name = 'self' if target.Serial == Player.Serial else target.Name
        Player.HeadMessage(colors['cyan'], 'Healing %s (%d%%)' % (
            name, int(float(target.Hits) / target.HitsMax * 100)))
        serial = Player.Serial if target.Serial == Player.Serial else target.Serial
        _cast_heal_cure(serial, name)
        return True

    return False


# ── Gift of Renewal ───────────────────────────────────────────────────────────

def GiftOfRenewalFriends():
    """Cast Gift of Renewal on friends who haven't had it within RENEWAL_DURATION_SEC."""
    if not _has_spellweaving:
        return
    for mob in _get_friends():
        if not _has_renewal(mob):
            Player.HeadMessage(colors['cyan'], 'Gift of Renewal on %s' % mob.Name)
            Spells.CastSpellweaving('Gift Of Renewal')
            if Target.WaitForTarget(5000, False):
                if _execute_safe_target(mob.Serial, mob.Name):
                    _renewal_times[mob.Serial] = time.time()
            Misc.Pause(1700)


# ── Bless ─────────────────────────────────────────────────────────────────────

def BlessFriends():
    """Bless any friend who hasn't been blessed within BLESS_DURATION_SEC.
    Skipped if Evaluating Intelligence is below 50."""
    if not _can_bless:
        return
    for mob in _get_friends():
        if not _is_blessed(mob):
            Player.HeadMessage(colors['cyan'], 'Blessing %s' % mob.Name)
            Spells.CastMagery('Bless')
            if Target.WaitForTarget(5000, False):
                if _execute_safe_target(mob.Serial, mob.Name):
                    _bless_times[mob.Serial] = time.time()
            Misc.Pause(1700)


# ── Main loop ─────────────────────────────────────────────────────────────────

while not Player.IsGhost:
    if not ResurrectGhosts():
        if not HealPets():
            GiftOfRenewalFriends()
            BlessFriends()
    Misc.Pause(150)
