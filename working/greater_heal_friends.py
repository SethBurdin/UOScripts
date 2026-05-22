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
    """Priority 1 — cure any poisoned friend.
       Priority 2 — heal the lowest-HP friend.
       Returns True if a spell was cast."""
    friends = _get_friends()
    if len(friends) == 0:
        return False

    # Priority 1: poisoned targets
    poisoned = [m for m in friends if m.Poisoned]
    if poisoned:
        target = min(poisoned, key=lambda m: m.Hits)
        Player.HeadMessage(colors['cyan'], 'Curing %s (%d%%)' % (
            target.Name, int(float(target.Hits) / target.HitsMax * 100)))
        Spells.CastMagery('Arch Cure')
        if Target.WaitForTarget(4000, False):
            Target.TargetExecute(target)
        Misc.Pause(1500)
        return True

    # Priority 2: damaged targets
    damaged = [m for m in friends if m.HitsMax > 0 and m.Hits < m.HitsMax]
    if damaged:
        target = min(damaged, key=lambda m: float(m.Hits) / m.HitsMax)
        Player.HeadMessage(colors['cyan'], 'Healing %s (%d%%)' % (
            target.Name, int(float(target.Hits) / target.HitsMax * 100)))
        Spells.CastMagery('Greater Heal')
        if Target.WaitForTarget(5000, False):
            Target.TargetExecute(target)
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
