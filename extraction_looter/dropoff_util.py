# dropoff_util.py
# Drop-off and item-sorting routines.
# All serials, positions, and thresholds live in the CONFIG section below.
#
# Public API:
#   run_dropoff()           -- full routine: gold → walk → sort items
#   drop_gold()             -- deposit gold only
#   drop_items()            -- sort backpack items only (must be at DROPOFF_POS)
#   classify_item(item)     -- returns container serial for an item, or None (→ overflow)
#   transfer_sorted(item)   -- classify + move with overflow fallback

if False:
    from razorenhanced_stubs import *

import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glossary.colors import colors
from extraction_looter.nav import load_waypoints, walk_waypoints

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG — edit here to adjust serials, positions, and thresholds
# ═══════════════════════════════════════════════════════════════════════════════

# ── Positions (fallbacks when waypoint file is absent) ────────────────────────
DROPOFF_POS = (917, 401, -86)   # walk here before sorting items
GOLD_POS    = (916, 410, -88)   # walk here, step north, then drop gold

# ── Waypoints ─────────────────────────────────────────────────────────────────
DROPOFF_WAYPOINTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'waypoints', 'dropoff.json'
)

# ── Primary containers ────────────────────────────────────────────────────────
LEATHER_BOX_SERIAL = 0x40040A7E  # leather, scales, imbueing ingredients
GEMS_SERIAL        = 0x400AF658  # gems — nested inside LEATHER_BOX (parent opens first)
GOLD_SERIAL        = 0x400B404A  # gold

# ── Exceptional find containers ───────────────────────────────────────────────
LUCK_SERIAL   = 0x40004EDE  # luck > LUCK_THRESHOLD
STATS_SERIAL  = 0x40004F05  # any stat > STAT_THRESHOLD
SKILLS_SERIAL = 0x40004E1F  # SKILL_COUNT_MIN+ skills each >= SKILL_THRESHOLD
MAGIC_SERIAL  = 0x40004E42  # faster casting / FCR / lower reagent cost / lower mana cost

# ── Overflow containers (tried in order when primary is full) ─────────────────
OVERFLOW_SERIALS = [0x400FDCEF, 0x400B4046, 0x400FD2AB, 0x400FDCA9]

# ── Exceptional thresholds ────────────────────────────────────────────────────
LUCK_THRESHOLD  = 149  # flag if luck exceeds this
STAT_THRESHOLD  = 9    # flag if any single stat bonus exceeds this
SKILL_THRESHOLD = 15   # minimum skill bonus value to count
SKILL_COUNT_MIN = 2    # minimum number of qualifying skills to flag

# ── Item IDs ──────────────────────────────────────────────────────────────────
GOLD_ID = 0x0EED

LEATHER_IDS = {0x1079, 0x1081}  # raw hides, cut leather

SCALE_IDS = {0x26B4, 0x26B5, 0x26B6, 0x26B7, 0x26B8, 0x26B9}  # dragon scales

GEM_IDS = {
    0x0F26,  # diamond
    0x0F25,  # amber
    0x0F0F,  # star sapphire
    0x0F10,  # emerald
    0x0F15,  # citrine
    0x0F11,  # sapphire
    0x0F13,  # ruby
    0x0F18,  # tourmaline
    0x0F16,  # amethyst
}

LEATHER_BOX_IDS = LEATHER_IDS | SCALE_IDS  # all go to LEATHER_BOX_SERIAL

# ── Magic property keywords (any match → MAGIC_SERIAL) ────────────────────────
MAGIC_KEYWORDS = {
    'faster casting',
    'faster cast recovery',
    'lower reagent cost',
    'lower mana cost',
}

# ── Stat property keywords ────────────────────────────────────────────────────
STAT_KEYWORDS = {
    'strength bonus',
    'dexterity bonus',
    'intelligence bonus',
}

# ── UO skill names (appear in item property lines) ────────────────────────────
SKILL_NAMES = {
    'alchemy', 'anatomy', 'animal lore', 'animal taming', 'archery',
    'arms lore', 'begging', 'blacksmithing', 'bowcraft', 'fletching',
    'bushido', 'camping', 'carpentry', 'cartography', 'chivalry',
    'cooking', 'detecting hidden', 'discordance', 'evaluating intelligence',
    'fencing', 'fishing', 'focus', 'forensic evaluation', 'healing',
    'herding', 'hiding', 'imbuing', 'inscription', 'item identification',
    'lockpicking', 'lumberjacking', 'mace fighting', 'magery', 'meditation',
    'mining', 'musicianship', 'mysticism', 'necromancy', 'ninjitsu',
    'parrying', 'peacemaking', 'poisoning', 'provocation', 'remove trap',
    'resisting spells', 'snooping', 'spirit speak', 'stealing', 'stealth',
    'swordsmanship', 'tactics', 'tailoring', 'taste identification',
    'tinkering', 'tracking', 'veterinary', 'wrestling',
}

# ── Timing ────────────────────────────────────────────────────────────────────
PROP_PAUSE_MS = 500
MOVE_PAUSE_MS = 1200

# ═══════════════════════════════════════════════════════════════════════════════
# INTERNALS
# ═══════════════════════════════════════════════════════════════════════════════

_TAG = '[dropoff]'
_overflow_index = 0   # advances permanently when a container fills up


def _log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def _walk_to(x, y):
    route              = PathFinding.Route()
    route.X            = x
    route.Y            = y
    route.DebugMessage = False
    route.StopIfStuck  = True
    PathFinding.Go(route)


def _get_props(item):
    """Return lowercase property strings for item, fetching from server if needed."""
    Items.SingleClick(item)
    Misc.Pause(PROP_PAUSE_MS)
    Items.WaitForProps(item, 2000)
    return [p.lower() for p in (Items.GetPropStringList(item.Serial) or [])]


def _first_number(text):
    """Extract the first integer from a string, or None."""
    m = re.search(r'\d+', text)
    return int(m.group()) if m else None


def _open_container(serial):
    """Open a container by serial and wait for contents."""
    container = Items.FindBySerial(serial)
    if container is None:
        _log("Container 0x%X not in range." % serial, colors['yellow'])
        return False
    Items.UseItem(container)
    Items.WaitForContents(serial, 3000)
    Misc.Pause(600)
    return True


def _move_item(item, container_serial):
    """
    Move item to container. Returns True if it landed there, False if rejected.
    """
    container = Items.FindBySerial(container_serial)
    if container is None:
        return False
    Items.Move(item, container, item.Amount)
    Misc.Pause(MOVE_PAUSE_MS)
    found = Items.FindBySerial(item.Serial)
    if found is None:
        return True   # stacked/consumed
    return found.Container == container_serial


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def classify_item(item):
    """
    Return the container serial this item belongs in, or None (→ overflow).

    Classification order:
      1. Gems         → GEMS_SERIAL
      2. Leather/scales → LEATHER_BOX_SERIAL
      3. Luck > LUCK_THRESHOLD          → LUCK_SERIAL
      4. Any stat > STAT_THRESHOLD      → STATS_SERIAL
      5. SKILL_COUNT_MIN+ skills >= SKILL_THRESHOLD → SKILLS_SERIAL
      6. Magic props (FC/FCR/LRC/LMC)  → MAGIC_SERIAL
      7. No match                       → None
    """
    if item.ItemID in GEM_IDS:
        return GEMS_SERIAL
    if item.ItemID in LEATHER_BOX_IDS:
        return LEATHER_BOX_SERIAL

    props = _get_props(item)

    # Luck
    for p in props:
        if 'luck' in p:
            n = _first_number(p)
            if n and n > LUCK_THRESHOLD:
                return LUCK_SERIAL

    # Stats
    for p in props:
        for kw in STAT_KEYWORDS:
            if kw in p:
                n = _first_number(p)
                if n and n > STAT_THRESHOLD:
                    return STATS_SERIAL

    # Skills
    skill_count = 0
    for p in props:
        for skill in SKILL_NAMES:
            if skill in p:
                n = _first_number(p)
                if n and n >= SKILL_THRESHOLD:
                    skill_count += 1
                break
    if skill_count >= SKILL_COUNT_MIN:
        return SKILLS_SERIAL

    # Magic
    for p in props:
        for kw in MAGIC_KEYWORDS:
            if kw in p:
                return MAGIC_SERIAL

    return None


def transfer_sorted(item):
    """
    Classify item and move it to the right container.
    If the primary is full, falls back to OVERFLOW_SERIALS starting from
    _overflow_index.  _overflow_index advances permanently when a container
    fills so already-full containers are never retried.
    Returns True if item was placed somewhere.
    """
    global _overflow_index

    primary = classify_item(item)

    if primary is not None:
        if _move_item(item, primary):
            return True
        _log("Primary 0x%X full — routing to overflow." % primary, colors['yellow'])

    while _overflow_index < len(OVERFLOW_SERIALS):
        serial = OVERFLOW_SERIALS[_overflow_index]
        if _move_item(item, serial):
            return True
        _log("Overflow 0x%X full — advancing." % serial, colors['yellow'])
        _overflow_index += 1

    _log("All overflow containers full — %s left in backpack." % item.Name, colors['red'])
    return False


def drop_gold():
    """Walk to gold position, step north, deposit all gold from backpack."""
    gold = Items.FindByID(GOLD_ID, -1, Player.Backpack.Serial)
    if gold is None:
        return

    _log("Walking to gold drop-off...")
    waypoints = load_waypoints(DROPOFF_WAYPOINTS_PATH)
    if waypoints:
        _walk_to(waypoints[0][0], waypoints[0][1])
    else:
        _walk_to(GOLD_POS[0], GOLD_POS[1])
    Player.Walk('North')
    Misc.Pause(600)

    moved = 0
    while True:
        gold = Items.FindByID(GOLD_ID, -1, Player.Backpack.Serial)
        if gold is None:
            break
        if not _move_item(gold, GOLD_SERIAL):
            _log("Gold transfer rejected.", colors['red'])
            break
        moved += gold.Amount

    if moved:
        _log("Deposited %d gold." % moved, colors['green'])


def drop_items():
    """
    Walk to DROPOFF_POS, open the leather box (and gems inside), then sort
    every non-gold item from the player's backpack into its container.
    """
    _log("Walking to drop-off position...")
    waypoints = load_waypoints(DROPOFF_WAYPOINTS_PATH)
    if waypoints:
        walk_waypoints(waypoints)
    else:
        _walk_to(DROPOFF_POS[0], DROPOFF_POS[1])
    Misc.Pause(1000)

    # Open leather box then gems (gems are nested inside leather box)
    _open_container(LEATHER_BOX_SERIAL)
    _open_container(GEMS_SERIAL)

    items = list(Player.Backpack.Contains or [])
    for item in items:
        if item.ItemID == GOLD_ID:
            continue   # gold handled separately by drop_gold()
        transfer_sorted(item)

    _log("Item sort complete.", colors['green'])


def unload_beetle_to_containers(beetle_pack):
    """
    Walk to the drop-off position and sort every item in the beetle's backpack
    directly into the appropriate storage containers — no player backpack intermediary.
    Gold goes to GOLD_SERIAL; everything else is classified via transfer_sorted.
    """
    # Must be on foot: mounted player can't access the beetle pack, and pathfinding
    # through doors fails more often while mounted.
    if Player.Mount is not None:
        _log("Dismounting before dropoff...", colors['cyan'])
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)

    _log("Walking to drop-off position...")
    waypoints = load_waypoints(DROPOFF_WAYPOINTS_PATH)
    if waypoints:
        walk_waypoints(waypoints)
    else:
        _walk_to(DROPOFF_POS[0], DROPOFF_POS[1])
    Misc.Pause(1000)

    _open_container(LEATHER_BOX_SERIAL)
    _open_container(GEMS_SERIAL)

    Items.UseItem(beetle_pack)
    Items.WaitForContents(beetle_pack.Serial, 3000)
    Misc.Pause(600)

    contents = list(beetle_pack.Contains or [])
    if not contents:
        _log("Beetle pack already empty.", colors['cyan'])
        return

    _log("Sorting %d item(s) from beetle..." % len(contents), colors['cyan'])
    for item in contents:
        if item.ItemID == GOLD_ID:
            _move_item(item, GOLD_SERIAL)
        else:
            transfer_sorted(item)

    _log("Beetle unloaded.", colors['green'])


def run_dropoff():
    """Full drop-off: deposit gold, then walk to sort position and sort items."""
    _log("Drop-off started.")
    drop_gold()
    drop_items()
    _log("Drop-off done.", colors['green'])
