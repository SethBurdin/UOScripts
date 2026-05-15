# extraction_looter/stealth.py
# Threat detection and hide/invis handling.
#
# Functions:
#   threat_nearby(hostile_range)             -> bool
#   handle_threat(beetle_serial,
#                 poll_ms, timeout_ms)       -> bool  (True = clear, False = timed out)

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.colors import colors
from glossary.enemies import GetEnemyNotorieties, GetEnemies

MAGERY_INVIS_THRESHOLD = 65   # cast Invisibility if Magery exceeds this
HIDING_THRESHOLD       = 70   # use Hide skill if Hiding exceeds this (fallback)

_TAG = '[stealth]'


def _log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def threat_nearby(hostile_range):
    """
    Return True if any hostile mobile is within hostile_range tiles.

    Input:
        hostile_range -- int, tile radius

    Returns:
        bool
    """
    enemies = GetEnemies(Mobiles, minRange=0, maxRange=hostile_range,
                         notorieties=GetEnemyNotorieties())
    return len(enemies) > 0


def _cast_invis():
    """Cast Invisibility on self. Returns True if mana dropped (spell fired)."""
    mana_before = Player.Mana
    Spells.CastMagery("Invisibility")
    if not Target.WaitForTarget(4000, False):
        _log("Invisibility: target cursor never appeared.", colors['yellow'])
        return False
    Target.TargetExecute(Player)
    # Poll for mana drop to confirm spell fired
    Timer.Create("invis_mana", 4000)
    while Timer.Check("invis_mana"):
        if Player.Mana < mana_before:
            return True
        Misc.Pause(50)
    _log("Invisibility fizzled — mana did not drop.", colors['yellow'])
    return False


def _use_hide():
    """Use the Hiding skill. Returns immediately (no confirmation check)."""
    Misc.UseSkill("Hiding")
    Misc.Pause(1000)


def _mount(beetle_serial):
    """Mount the beetle so the character stays mounted while hidden."""
    if beetle_serial is None:
        return
    if Player.Mount is not None:
        return   # already mounted
    beetle = Mobiles.FindBySerial(beetle_serial)
    if beetle is None:
        _log("Beetle not in range — cannot mount.", colors['yellow'])
        return
    Mobiles.UseMobile(beetle_serial)
    Misc.Pause(1500)


def handle_threat(beetle_serial, poll_ms, timeout_ms):
    """
    React to a nearby threat:
      1. Cast Invisibility (if Magery > threshold), else use Hiding skill.
      2. Mount the beetle.
      3. Poll every poll_ms ms until no hostiles remain or timeout_ms elapses.

    Input:
        beetle_serial -- int, serial of the pack beetle mobile (may be None)
        poll_ms       -- int, ms between hostile re-checks
        timeout_ms    -- int, ms before giving up

    Returns:
        True  if threat cleared within timeout
        False if timeout elapsed (caller should return home)
    """
    magery = Player.GetSkillValue("Magery")
    hiding = Player.GetSkillValue("Hiding")

    if magery > MAGERY_INVIS_THRESHOLD:
        _log("Threat detected — casting Invisibility (Magery %.1f)." % magery, colors['yellow'])
        _cast_invis()
    elif hiding > HIDING_THRESHOLD:
        _log("Threat detected — using Hiding (Hiding %.1f)." % hiding, colors['yellow'])
        _use_hide()
    else:
        _log("Threat detected — no hide skill available, mounting only.", colors['red'])

    _mount(beetle_serial)

    elapsed = 0
    while elapsed < timeout_ms:
        Misc.Pause(poll_ms)
        elapsed += poll_ms
        if not threat_nearby(20):   # wider check when polling to avoid premature resume
            _log("Threat cleared — resuming.", colors['green'])
            return True
        _log("Threat still present (%ds / %ds)." % (elapsed // 1000, timeout_ms // 1000),
             colors['yellow'])

    _log("Threat timeout — returning home.", colors['red'])
    return False
