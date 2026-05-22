'''
Pirate Hunter
    Opens the tracking gump (Monsters category). While the results list is
    visible the player clicks their quarry — the arrow appears in-game.
    The script reads the gump text to find matching nearby mobiles and locks
    onto the closest one. Every POLL_MS the bearing and distance are announced
    to the party via Player.ChatSay with a random pirate-flavoured message.
'''

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import math
import time
import random
from glossary.colors import colors

# ── Tracking gump constants (confirmed from train_Tracking.py) ───────────────
TRACKING_GUMP   = 2976808305
MONSTERS_BTN    = 4
DISMISS_BTN     = 0

# ── Tuning ────────────────────────────────────────────────────────────────────
POLL_MS         = 8000   # ms between direction callouts
GUMP_SELECT_SEC = 20     # seconds to wait for the player to pick from the gump
MOB_SCAN_RANGE  = 30     # tile radius when matching gump names to serials

# ── 8-point compass ───────────────────────────────────────────────────────────
_COMPASS = ['North', 'Northeast', 'East', 'Southeast',
            'South', 'Southwest', 'West', 'Northwest']

# ── Pirate callouts — {name}, {dir}, {dist} filled at runtime ────────────────
CALLOUTS = [
    "Arr! {name} spotted to the {dir} — {dist} tiles, lads!",
    "Shiver me timbers — {name} be {dist} tiles to the {dir}!",
    "All hands! Head {dir}, {dist} tiles to {name}!",
    "Hoist the Jolly Roger — {dist} tiles to the {dir}, that be {name}!",
    "By Davy Jones — {name}, {dist} tiles to the {dir}!",
    "Yo ho ho! {name} be {dist} tiles {dir}, don't lose 'em!",
    "{name} runs {dir} — {dist} tiles, give chase!",
    "No quarter! {name} — {dir}, {dist} tiles, close the gap!",
]

IDLE = [
    "Arr, lost sight of the quarry...",
    "Keep yer eyes peeled, the mark has gone to ground.",
    "Where'd that scallywag go?",
    "The seas be quiet... scan the horizon.",
    "Splice the mainbrace and stay sharp.",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compass(px, py, tx, ty):
    bearing = math.degrees(math.atan2(tx - px, -(ty - py))) % 360
    return _COMPASS[int((bearing + 22.5) / 45) % 8]

def _dist(px, py, tx, ty):
    return int(math.sqrt((tx - px) ** 2 + (ty - py) ** 2))


# ── Target acquisition ────────────────────────────────────────────────────────

def AcquireTarget():
    """Open tracking gump, read the results list, wait for the player to click
    their quarry (arrow appears in-game), then lock onto the closest mobile
    whose name matches anything from the gump text."""
    Misc.SendMessage('[Pirate Hunter] Opening tracking — click yer quarry from the list.', colors['cyan'])

    Player.UseSkill('Tracking')
    if not Gumps.WaitForGump(TRACKING_GUMP, 5000):
        Misc.SendMessage('[Pirate Hunter] Tracking gump did not open.', colors['red'])
        return None, None

    Gumps.SendAction(TRACKING_GUMP, MONSTERS_BTN)
    if not Gumps.WaitForGump(TRACKING_GUMP, 3000):
        Misc.SendMessage('[Pirate Hunter] No monsters in range.', colors['yellow'])
        return None, None

    # Capture gump text NOW while the results are visible
    gump_lines = [l.strip().lower() for l in Gumps.LastGumpGetLineList() if l.strip()]

    # Wait for player to click a mob (gump closes when they do)
    deadline = time.time() + GUMP_SELECT_SEC
    while time.time() < deadline and Gumps.HasGump():
        Misc.Pause(300)
    if Gumps.HasGump():
        Gumps.SendAction(TRACKING_GUMP, DISMISS_BTN)

    # Match gump names against nearby mobiles — lock the closest match
    px, py = Player.Position.X, Player.Position.Y
    f = Mobiles.Filter()
    f.Enabled  = True
    f.RangeMax = MOB_SCAN_RANGE
    candidates = [
        m for m in Mobiles.ApplyFilter(f)
        if any((m.Name or '').lower() in line or line in (m.Name or '').lower()
               for line in gump_lines)
    ]

    if candidates:
        mob = min(candidates, key=lambda m: _dist(px, py, m.Position.X, m.Position.Y))
        Misc.SendMessage('[Pirate Hunter] Locked on: %s' % mob.Name, colors['cyan'])
        return mob.Serial, mob.Name

    Misc.SendMessage('[Pirate Hunter] Could not match a target — click yer mark manually.', colors['yellow'])
    serial = Target.PromptTarget('Click your quarry:')
    if serial:
        mob  = Mobiles.FindBySerial(serial)
        name = mob.Name if mob else ('0x%X' % serial)
        Misc.SendMessage('[Pirate Hunter] Locked on: %s' % name, colors['cyan'])
        return serial, name

    return None, None


# ── Main ──────────────────────────────────────────────────────────────────────

def Main():
    serial, name = AcquireTarget()
    if not serial:
        Misc.SendMessage('[Pirate Hunter] No target — stopping.', colors['red'])
        return

    while not Player.IsGhost:
        mob = Mobiles.FindBySerial(serial)

        if mob:
            px   = Player.Position.X
            py   = Player.Position.Y
            dir  = _compass(px, py, mob.Position.X, mob.Position.Y)
            dist = _dist(px, py, mob.Position.X, mob.Position.Y)
            msg  = random.choice(CALLOUTS).format(name=name, dir=dir, dist=dist)
            Player.ChatSay(colors['yellow'], msg)
        else:
            Player.ChatSay(colors['cyan'], random.choice(IDLE))

        Misc.Pause(POLL_MS)


Main()
