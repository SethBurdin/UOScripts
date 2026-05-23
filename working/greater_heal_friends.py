import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if False:
    from razorenhanced_stubs import *

from utilities.mobiles import GetEmptyMobileList
from glossary.colors import colors

# ── Config ────────────────────────────────────────────────────────────────────
SCAN_RANGE        = 8     # tile radius to scan for friends
BLESS_DURATION_SEC = 120  # seconds before re-blessing a target

# ── Bless timing tracker ──────────────────────────────────────────────────────
_bless_times = {}   # { serial: timestamp of last bless cast }

def _is_blessed(mob):
    return time.time() - _bless_times.get(mob.Serial, 0) < BLESS_DURATION_SEC


# ── Friend scan ───────────────────────────────────────────────────────────────

def _get_friends():
    """Returns living (non-ghost) friendly mobiles within range."""
    f = Mobiles.Filter()
    f.IsGhost  = 0
    f.Friend   = 1
    f.RangeMin = 0
    f.RangeMax = SCAN_RANGE
    result = GetEmptyMobileList(Mobiles)
    result.AddRange(Mobiles.ApplyFilter(f))
    return result

def _get_ghosts():
    """Returns friendly ghosts within range."""
    f = Mobiles.Filter()
    f.IsGhost  = 1
    f.Friend   = 1
    f.RangeMin = 0
    f.RangeMax = SCAN_RANGE
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
            Target.TargetExecute(ghost)
        Misc.Pause(2000)
    return True


# ── Heal / cure ───────────────────────────────────────────────────────────────

def HealPets():
    """Priority 1 — cure any poisoned target (self first, then lowest-HP friend).
       Priority 2 — heal the lowest-HP target among self + friends.
       Returns True if a spell was cast."""
    friends = _get_friends()

    # Priority 1: poisoned targets — self first, then friends
    if Player.Poisoned:
        Player.HeadMessage(colors['cyan'], 'Curing self (%d%%)' % (
            int(float(Player.Hits) / Player.HitsMax * 100)))
        Spells.CastMagery('Arch Cure')
        if Target.WaitForTarget(4000, False):
            Target.TargetExecute(Player.Serial)
        Misc.Pause(1500)
        return True

    poisoned_friends = [m for m in friends if m.Poisoned]
    if poisoned_friends:
        target = min(poisoned_friends, key=lambda m: m.Hits)
        Player.HeadMessage(colors['cyan'], 'Curing %s (%d%%)' % (
            target.Name, int(float(target.Hits) / target.HitsMax * 100)))
        Spells.CastMagery('Arch Cure')
        if Target.WaitForTarget(4000, False):
            Target.TargetExecute(target)
        Misc.Pause(1500)
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
        Spells.CastMagery('Greater Heal')
        serial = Player.Serial if target.Serial == Player.Serial else target.Serial
        if Target.WaitForTarget(5000, False):
            Target.TargetExecute(serial)
        Misc.Pause(1700)
        return True

    return False


# ── Bless ─────────────────────────────────────────────────────────────────────

def BlessFriends():
    """Bless any friend who hasn't been blessed within BLESS_DURATION_SEC."""
    for mob in _get_friends():
        if not _is_blessed(mob):
            Player.HeadMessage(colors['cyan'], 'Blessing %s' % mob.Name)
            Spells.CastMagery('Bless')
            if Target.WaitForTarget(5000, False):
                Target.TargetExecute(mob)
            _bless_times[mob.Serial] = time.time()
            Misc.Pause(1700)


# ── Main loop ─────────────────────────────────────────────────────────────────

while not Player.IsGhost:
    if not ResurrectGhosts():
        if not HealPets():
            BlessFriends()
    Misc.Pause(150)
