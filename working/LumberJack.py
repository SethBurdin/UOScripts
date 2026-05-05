# ─────────────────────────────────────────────────────────────────────────────
# LumberJack.py
# Lumberjacking automation for Razor Enhanced.
#
# Features:
#   - Three modes controlled by cfg.mode:
#       "chop"      – stationary: chop all trees near starting position then stop.
#       "record"    – waypoint recorder: say "wp" to stamp current position,
#                     say "done" to save and exit.
#       "waypoints" – follow lumberjackwaypoint.json, chop trees at each stop,
#                     loop back to start (set cfg.waypoint_loop = False for one pass).
#   - Chops trees at adjacent tiles; cycles through all (offset × tile-ID)
#     combinations so the player does not have to move.
#   - Monitors journal for no-tree / pack-full signals.
#   - Splits logs into boards once weight climbs past a configurable threshold.
#   - Recalls home via runebook when pack weight hits the carry limit.
#   - Say "quit" in chat to stop at any time.
#
# Config: edit the `cfg` class at the top of this file.
# ─────────────────────────────────────────────────────────────────────────────

import datetime
import json
import os

# IDE IntelliSense only – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

LOG_FILE = os.path.join(
    os.path.expanduser("~"),
    "OneDrive", "Documents",
    "ClassicUOLauncher-win-x64-release", "ClassicUO",
    "data", "plugins", "scripts",
    "lumberjack.txt",
)

WAYPOINT_FILE = "lumberjackwaypoint.json"

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
class cfg:
    # ── Mode ──────────────────────────────────────────────────────────────────
    # "chop"      – stationary mode (original behavior)
    # "record"    – record waypoints; say "wp" to stamp, "done" to save & exit
    # "waypoints" – walk lumberjackwaypoint.json route and chop along the way
    mode          = "chop"
    waypoint_loop = True     # loop continuously when mode = "waypoints"

    # ── Weight threshold ─────────────────────────────────────────────────────
    transfer_margin      = 10   # transfer to beetle when within this many stones of Player.MaxWeight

    # ── Recall thresholds ────────────────────────────────────────────────────
    min_chivalry_recall  = 30   # minimum Chivalry to use Sacred Journey (checked first)
    min_magery_recall    = 45   # minimum Magery to use Recall (fallback if Chivalry too low)

    # ── Home container ───────────────────────────────────────────────────────
    # Set to the serial of your secure chest to skip the auto-scan entirely.
    # Find it with Object Inspector then paste the hex value here.
    home_container_serial = 0x400B404A

    # ── Startup run to chop site ─────────────────────────────────────────────
    # After depositing at home, run this route before scanning for trees.
    # Set run_to_site = False to skip entirely (e.g. in waypoint mode).
    run_to_site     = True
    run_west_steps  = 5
    run_nw_steps    = 30
    beetle_serial          = 0x00003012   # serial of your pack beetle

    # ── Timing ───────────────────────────────────────────────────────────────
    pause_after_chop  = 2200   # ms – swing + server tick
    pause_after_split = 1200   # ms – after each log-split pass
    loop_delay        = 200    # ms – bottom of every main loop iteration
    walk_pause        = 400    # ms – pause between each walk step
    search_radius     = 10     # tiles to scan around player for a tree

    # Tree static graphic IDs — used to recognize tree tiles via statics probe.
    # ALL statics found during a scan are logged to lumberjack.txt so you can
    # add any missing IDs for your shard.
    # Source: RunUO/ServUO Lumberjacking.cs (complete set).
    tree_tile_ids = [
        # Standard deciduous / pine trees
        0x0CCA, 0x0CCB, 0x0CCC, 0x0CCD, 0x0CCE, 0x0CCF,
        0x0CD0, 0x0CD3, 0x0CD4, 0x0CD6, 0x0CDA, 0x0CDB, 0x0CDC,
        0x0CDD, 0x0CDE, 0x0CDF, 0x0CE0, 0x0CE3, 0x0CE6,
        0x0CE9, 0x0CEB, 0x0CEE, 0x0CF1, 0x0CF4, 0x0CF5,
        0x0CF6, 0x0CF7, 0x0CF8, 0x0CF9, 0x0CFA, 0x0CFB,
        0x0CFC, 0x0D04,
        # Jungle / ML trees
        0x12B6, 0x12B7, 0x12B8, 0x12B9, 0x12BA, 0x12BB,
        0x12BC, 0x12BD, 0x12BE, 0x12BF, 0x12C0, 0x12C1, 0x12C2,
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Item IDs
# ─────────────────────────────────────────────────────────────────────────────
HATCHET_IDS      = [0x0F43, 0x0F3F, 0x143E]   # hatchets / axes for chopping
LOG_ID           = 0x1BDD                      # used by find_logs() for splitting
RUNEBOOK_ID      = 0x22C5                      # runebook graphic ID
RUNEBOOK_NAME    = "home"                      # name of the runebook to recall from
RUNEBOOK_GUMP_ID = 0x59                        # verify with Gump Inspector if recall fails
RECALL_RUNE_BTN  = 1                           # rune slot button (1 = first slot)

# All log and board types to transfer to the beetle.
# Items.FindByID uses color=-1 (any hue), so hue variants are caught automatically.
# Add shard-specific IDs here if your server uses distinct item IDs for special woods.
LOG_IDS = [
    0x1BDD,   # regular / oak / ash / yew / heartwood / bloodwood / frostwood logs
]
BOARD_IDS = [
    0x1BD7,   # regular / oak / ash / yew / heartwood / bloodwood / frostwood boards
]

# Common secure container graphic IDs scanned when depositing at home.
# Add any shard-specific chest/crate IDs here.
CONTAINER_IDS = [
    0x0E40, 0x0E41, 0x0E42, 0x0E43,   # metal and wooden chests
    0x0E7C, 0x0E7D, 0x0E7E, 0x0E80,   # crates and large chests
    0x09AA,                             # strongbox
    0x0E84, 0x0E85,                    # armoires
]

# Session-cached serial of the home storage container (set on first use).
_home_container_serial = None


# ─────────────────────────────────────────────────────────────────────────────
# Journal signals (substring matches)
# ─────────────────────────────────────────────────────────────────────────────
# NOTE: "You hack at the tree" is a SERVER SUCCESS message (skill-fail on a
# valid tree target).  Do NOT put it here — it should be treated as 'ok'.
JOURNAL_NO_TREE = [
    "not accessible",
    "cannot be seen",
    "That is not",
    "no tree",
    "not enough wood",
    "You can't chop",
    "can't reach",
]
JOURNAL_BAD_POSITION = [
    "can't use your axe",
    "not facing",
]
JOURNAL_PACK_FULL = ["Your backpack", "you cannot carry", "not enough room"]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def log(msg, color=0x3F):
    Misc.SendMessage("[LUMBER] %s" % msg, color)
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        with open(LOG_FILE, "a") as _f:
            _f.write("%s %s\n" % (ts, msg))
    except Exception:
        pass


def find_axe():
    # Check equipped layers first.
    for layer in ("RightHand", "LeftHand"):
        item = Player.GetItemOnLayer(layer)
        if item is not None and item.ItemID in HATCHET_IDS:
            return item
    # Fall back to backpack.
    if Player.Backpack is None:
        return None
    for hid in HATCHET_IDS:
        tool = Items.FindByID(hid, -1, Player.Backpack.Serial)
        if tool is not None:
            return tool
    return None


def find_logs():
    if Player.Backpack is None:
        return None
    return Items.FindByID(LOG_ID, -1, Player.Backpack.Serial)


# ─────────────────────────────────────────────────────────────────────────────
# Log splitting — double-click axe, target logs
# ─────────────────────────────────────────────────────────────────────────────
def _count_logs():
    """Sum the amount of every log stack in the backpack."""
    bp = Player.Backpack
    if bp is None:
        return 0
    total = 0
    for item in bp.Contains:
        if item.ItemID == LOG_ID:
            total += item.Amount
    return total


def _count_wood():
    """Sum every log and board stack in the backpack."""
    bp = Player.Backpack
    if bp is None:
        return 0
    ids = set(LOG_IDS + BOARD_IDS)
    return sum(item.Amount for item in bp.Contains if item.ItemID in ids)


def split_logs():
    log("Splitting logs into boards...")
    passes = 0
    max_passes = 15
    while passes < max_passes:
        logs = find_logs()
        if logs is None:
            break
        axe = find_axe()
        if axe is None:
            log("No axe in backpack – cannot split logs.", 0x25)
            break
        before = _count_logs()
        Target.ClearQueue()
        Items.UseItem(axe)
        if not Target.WaitForTarget(3000, False):
            log("No target cursor after axe use – aborting split.", 0x3B)
            break
        Target.TargetExecute(logs.Serial)
        Misc.Pause(cfg.pause_after_split)
        passes += 1
        if _count_logs() >= before:
            log("Log count unchanged after split – server rejected or no logs left.", 0x3B)
            break
    log("Split complete (%d pass(es))." % passes)


# ─────────────────────────────────────────────────────────────────────────────
# Pack beetle — find and transfer wood
# ─────────────────────────────────────────────────────────────────────────────
def find_beetle():
    # Always look up by serial — Player.Mount returns an int in IronPython,
    # not a Mobile object, so we cannot use it to access Backpack.
    beetle = Mobiles.FindBySerial(cfg.beetle_serial)
    if beetle is None:
        log("Pack beetle not found (serial=0x%X)." % cfg.beetle_serial, 0x25)
    return beetle


def transfer_wood_to_beetle(beetle):
    bp = Player.Backpack
    if bp is None:
        return

    log("Player.Mount=%s — dismounting." % Player.Mount, 0x3B)
    Mobiles.UseMobile(Player.Serial)
    Misc.Pause(1500)

    if beetle is None:
        beetle = find_beetle()
    if beetle is None:
        log("Beetle not found after dismount – cannot transfer.", 0x25)
        Mobiles.UseMobile(cfg.beetle_serial)
        Misc.Pause(1200)
        return

    beetle_pack = beetle.Backpack
    if beetle_pack is None:
        log("Beetle backpack not accessible (out of range?).", 0x25)
        Mobiles.UseMobile(cfg.beetle_serial)
        Misc.Pause(1200)
        return

    moved = 0
    beetle_full = False
    for id_list in (LOG_IDS, BOARD_IDS):
        if beetle_full:
            break
        for item_id in id_list:
            if beetle_full:
                break
            safety = 0
            while safety < 50:
                item = Items.FindByID(item_id, -1, bp.Serial)
                if item is None:
                    break
                before = _count_wood()
                Items.Move(item, beetle_pack, item.Amount)
                Misc.Pause(800)
                if _count_wood() >= before:
                    log("Wood count unchanged – beetle pack full.", 0x25)
                    beetle_full = True
                    break
                moved += 1
                safety += 1

    if moved:
        log("Transferred %d stack(s) of wood to beetle." % moved, 0x3B)
    elif not beetle_full:
        log("No wood found to transfer.", 0x3B)

    Mobiles.UseMobile(beetle.Serial)
    Misc.Pause(1200)
    return moved, beetle_full



def split_and_transfer(beetle):
    if find_logs() is not None:
        split_logs()
    return transfer_wood_to_beetle(beetle)   # returns (moved, beetle_full)


# ─────────────────────────────────────────────────────────────────────────────
# Tree detection — scan radius around player for a tree static
# ─────────────────────────────────────────────────────────────────────────────
def find_nearby_tree(depleted=None):
    """
    Scan tiles within cfg.search_radius of the player.
    Logs EVERY static ID found so you can identify unlisted tree tiles.
    Skips tiles in the depleted set (set of (tx,ty) tuples).
    Returns (tx, ty, tz, tile_id) of the nearest matching tree, or None.
    """
    pos = Player.Position
    tree_set = set(cfg.tree_tile_ids)
    skip = depleted or set()
    best = None
    best_dist = 9999
    r = cfg.search_radius
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            tx = pos.X + dx
            ty = pos.Y + dy
            if (tx, ty) in skip:
                continue
            try:
                statics = Statics.GetStaticsTileInfo(tx, ty, Player.Map)
            except Exception:
                continue
            for tile in statics:
                log("  scan (%d,%d) ID=0x%04X Z=%d" % (tx, ty, tile.StaticID, tile.StaticZ), 0x3B)
                if tile.StaticID in tree_set:
                    dist = abs(dx) + abs(dy)
                    if dist < best_dist:
                        best_dist = dist
                        best = (tx, ty, tile.StaticZ, tile.StaticID)
    return best


# ─────────────────────────────────────────────────────────────────────────────
# Movement — walk player to a target tile
# ─────────────────────────────────────────────────────────────────────────────
def _step_toward(tx, ty):
    """Take one walk step toward (tx, ty). Returns True if already there."""
    pos = Player.Position
    dx = tx - pos.X
    dy = ty - pos.Y
    if dx == 0 and dy == 0:
        return True
    sx = 0 if dx == 0 else (1 if dx > 0 else -1)
    sy = 0 if dy == 0 else (1 if dy > 0 else -1)
    # UO axis: X+ = East, Y+ = South
    dir_map = {
        ( 0, -1): "North",
        ( 1, -1): "Northeast",
        ( 1,  0): "East",
        ( 1,  1): "Southeast",
        ( 0,  1): "South",
        (-1,  1): "Southwest",
        (-1,  0): "West",
        (-1, -1): "Northwest",
    }
    direction = dir_map.get((sx, sy), "North")
    Player.Walk(direction)
    Misc.Pause(cfg.walk_pause)
    return False


def _try_unstick(goal_x, goal_y):
    """
    Try stepping perpendicular to the goal to break free from a blocked tile
    (e.g. a tree static sitting directly between player and destination).
    Tries clockwise then counter-clockwise 90° relative to the current heading.
    """
    pos = Player.Position
    dx = goal_x - pos.X
    dy = goal_y - pos.Y
    dir_map = {
        ( 0, -1): "North",    ( 1, -1): "Northeast", ( 1,  0): "East",
        ( 1,  1): "Southeast",( 0,  1): "South",     (-1,  1): "Southwest",
        (-1,  0): "West",     (-1, -1): "Northwest",
    }
    for pdx, pdy in [(dy, -dx), (-dy, dx)]:
        sx = 1 if pdx > 0 else (-1 if pdx < 0 else 0)
        sy = 1 if pdy > 0 else (-1 if pdy < 0 else 0)
        if sx == 0 and sy == 0:
            continue
        direction = dir_map.get((sx, sy))
        if not direction:
            continue
        for _ in range(2):
            Player.Walk(direction)
            Misc.Pause(cfg.walk_pause)
        new_pos = Player.Position
        if new_pos.X != pos.X or new_pos.Y != pos.Y:
            # Cleared the obstacle — take 2 steps toward goal so we don't
            # immediately collide with the same tree again on the next iteration.
            _step_toward(goal_x, goal_y)
            _step_toward(goal_x, goal_y)
            return


def walk_adjacent_to(tx, ty):
    """
    Walk to any tile adjacent to (tx, ty).
    The tree tile itself is impassable, so we stand next to it.
    Returns True when we are within 1 tile of the target.
    Includes stuck detection: after 2 consecutive non-moving steps,
    tries a perpendicular nudge to route around blocking tree tiles.
    """
    max_steps = 40
    stuck = 0
    for _ in range(max_steps):
        pos = Player.Position
        if abs(pos.X - tx) <= 1 and abs(pos.Y - ty) <= 1:
            return True
        prev = (pos.X, pos.Y)
        _step_toward(tx, ty)
        new_pos = Player.Position
        if (new_pos.X, new_pos.Y) == prev:
            stuck += 1
            if stuck >= 2:
                _try_unstick(tx, ty)
                stuck = 0
        else:
            stuck = 0
    log("Could not reach adjacent tile for (%d,%d) in %d steps." % (tx, ty, max_steps), 0x25)
    return False


def walk_to(tx, ty):
    """
    Walk to the exact tile (tx, ty).  Used to reach waypoints.
    Step budget scales with Manhattan distance so long walks don't fail early.
    Includes the same stuck detection as walk_adjacent_to.
    """
    pos = Player.Position
    dist = abs(tx - pos.X) + abs(ty - pos.Y)
    max_steps = max(dist * 3, 30)
    stuck = 0
    for _ in range(max_steps):
        pos = Player.Position
        if pos.X == tx and pos.Y == ty:
            return True
        prev = (pos.X, pos.Y)
        _step_toward(tx, ty)
        new_pos = Player.Position
        if (new_pos.X, new_pos.Y) == prev:
            stuck += 1
            if stuck >= 2:
                _try_unstick(tx, ty)
                stuck = 0
        else:
            stuck = 0
    log("Could not reach (%d,%d) in %d steps." % (tx, ty, max_steps), 0x25)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Tree chopping — stand on tree tile, chop until server says depleted
# ─────────────────────────────────────────────────────────────────────────────
def chop_once(tx, ty, tz, tile_id):
    """
    Swing axe at the tile (tx, ty, tz, tile_id).
    Returns 'ok', 'no_tree', 'pack_full', or 'no_tool'.
    """
    axe = find_axe()
    if axe is None:
        log("No axe found!", 0x25)
        return "no_tool"

    Journal.Clear()
    Target.ClearQueue()
    Items.UseItem(axe)
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(tx, ty, tz, tile_id)
    Misc.Pause(cfg.pause_after_chop)

    for phrase in JOURNAL_PACK_FULL:
        if Journal.Search(phrase):
            return "pack_full"
    for phrase in JOURNAL_BAD_POSITION:
        if Journal.Search(phrase):
            return "bad_position"
    for phrase in JOURNAL_NO_TREE:
        if Journal.Search(phrase):
            return "no_tree"
    return "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Core chopping loop — exhaust all trees near current position
# ─────────────────────────────────────────────────────────────────────────────
def chop_nearby_trees(beetle):
    """
    Find and chop every tree within cfg.search_radius of the current position.
    Returns when the local area is exhausted or an exit condition is met.
    Return values: "done", "go_home", "quit", "no_tool"
    """
    depleted_trees = set()

    while True:
        if Player.WarMode:
            log("War mode detected – stopping.", 0x25)
            return "quit"
        if Journal.Search("quit"):
            Journal.Clear()
            log("Quit received – stopping.", 0x026C)
            return "quit"

        weight = Player.Weight
        threshold = Player.MaxWeight - cfg.transfer_margin

        if weight >= threshold:
            log("Weight %d/%d – transferring to beetle." % (weight, Player.MaxWeight), 0x25)
            _, beetle_full = split_and_transfer(beetle)
            if beetle_full:
                log("Beetle full – recalling home.", 0x25)
                go_home()
                deposit_wood_to_container()

                log("Stopping after home recall.", 0x026C)
                return "go_home"
            Misc.Pause(cfg.loop_delay)
            continue

        tree = find_nearby_tree(depleted_trees)
        if tree is None:
            log("No tree found within radius %d." % cfg.search_radius, 0x3B)
            return "done"

        tx, ty, tz, tile_id = tree
        log("Tree at (%d,%d) tile=0x%04X Z=%d – walking there." % (tx, ty, tile_id, tz), 0x3B)

        if not walk_adjacent_to(tx, ty):
            # Can't reach this tree — mark it and look for the next one.
            depleted_trees.add((tx, ty))
            continue

        log("Chopping tree at (%d,%d)..." % (tx, ty), 0x3B)
        bad_position_count = 0

        while True:
            if Player.WarMode:
                log("War mode – stopping.", 0x25)
                return "quit"
            if Journal.Search("quit"):
                log("Quit received – stopping.", 0x026C)
                return "quit"

            weight = Player.Weight
            threshold = Player.MaxWeight - cfg.transfer_margin
            if weight >= threshold:
                log("Weight %d/%d – transferring to beetle." % (weight, Player.MaxWeight), 0x25)
                _, beetle_full = split_and_transfer(beetle)
                if beetle_full:
                    log("Beetle full – recalling home.", 0x25)
                    go_home()
                    deposit_wood_to_container()
                    log("Stopping after home recall.", 0x026C)
                    return "go_home"

            result = chop_once(tx, ty, tz, tile_id)
            log("chop result: %s" % result, 0x3B)

            if result == "no_tool":
                return "no_tool"
            elif result == "bad_position":
                bad_position_count += 1
                log("Bad position for tree (%d,%d) – re-walking (attempt %d)." % (tx, ty, bad_position_count), 0x3B)
                if bad_position_count >= 3:
                    log("Cannot reach a valid chop position – skipping tree.", 0x25)
                    depleted_trees.add((tx, ty))
                    break
                walk_adjacent_to(tx, ty)
            elif result == "no_tree":
                log("Tree depleted at (%d,%d) – splitting logs before moving on." % (tx, ty), 0x3B)
                split_and_transfer(beetle)
                depleted_trees.add((tx, ty))
                break   # back to outer loop to find another tree
            elif result == "pack_full":
                split_and_transfer(beetle)
            # 'ok' → keep chopping same tree

        Misc.Pause(cfg.loop_delay)


# ─────────────────────────────────────────────────────────────────────────────
# Home container deposit
# ─────────────────────────────────────────────────────────────────────────────
def find_home_container():
    """
    Find the home storage container, in priority order:
      1. cfg.home_container_serial  (hardcoded — most reliable)
      2. Session cache from a previous successful scan
      3. Auto-scan CONTAINER_IDS within 2 tiles
    Returns None and logs a warning if nothing is found.
    """
    global _home_container_serial

    if cfg.home_container_serial is not None:
        c = Items.FindBySerial(cfg.home_container_serial)
        if c is not None:
            return c
        log("cfg.home_container_serial 0x%X not found – falling back to scan." % cfg.home_container_serial, 0x25)

    if _home_container_serial is not None:
        c = Items.FindBySerial(_home_container_serial)
        if c is not None:
            return c

    scan_range = 5
    for cid in CONTAINER_IDS:
        c = Items.FindByID(cid, -1, -1, scan_range)
        if c is not None:
            _home_container_serial = c.Serial
            log("Home container auto-detected: 0x%X (ID=0x%04X)." % (c.Serial, cid), 0x3B)
            return c

    # Nothing matched — log all ground items nearby so the right ID can be identified.
    log("No container found within %d tiles. Logging nearby ground items:" % scan_range, 0x25)
    filt = Items.Filter()
    filt.RangeMax = scan_range
    filt.OnGround = True
    for item in Items.ApplyFilter(filt):
        log("  0x%X  ID=0x%04X  '%s'" % (item.Serial, item.ItemID, item.Name or ""), 0x3B)
    log("Add the matching ID to CONTAINER_IDS or set cfg.home_container_serial.", 0x25)
    return None


def deposit_wood_to_container():
    """
    Dismount, transfer all logs and boards from the beetle and the player's
    backpack into the home storage container, then remount.
    """
    container = find_home_container()
    if container is None:
        log("No home container available – skipping deposit.", 0x25)
        return

    mounted = Player.Mount is not None
    if mounted:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)

    beetle = find_beetle()
    moved  = 0

    sources = []
    if beetle is not None and beetle.Backpack is not None:
        sources.append(("beetle", beetle.Backpack.Serial))
    if Player.Backpack is not None:
        sources.append(("backpack", Player.Backpack.Serial))

    for _, source_serial in sources:
        for id_list in (LOG_IDS, BOARD_IDS):
            for item_id in id_list:
                safety = 0
                while safety < 50:
                    item = Items.FindByID(item_id, -1, source_serial)
                    if item is None:
                        break
                    Items.Move(item, container, item.Amount)
                    Misc.Pause(800)
                    moved += 1
                    safety += 1

    log("Deposited %d stack(s) to home container." % moved if moved else "Nothing to deposit.", 0x3B)

    if mounted and beetle is not None:
        Mobiles.UseMobile(beetle.Serial)
        Misc.Pause(1200)


# ─────────────────────────────────────────────────────────────────────────────
# Home recall — Sacred Journey / Recall targeting runebook named "home"
# ─────────────────────────────────────────────────────────────────────────────
def find_runebook_home():
    """
    Return the runebook named RUNEBOOK_NAME ('home') if found, otherwise
    return the first runebook in the backpack. Returns None if none exist.
    """
    bp = Player.Backpack
    if bp is None:
        return None
    first = None
    for item in bp.Contains:
        if item.ItemID != RUNEBOOK_ID:
            continue
        Items.WaitForProps(item.Serial, 1000)
        if first is None:
            first = item
        if RUNEBOOK_NAME.lower() in (item.Name or '').lower():
            log("Found runebook '%s' (0x%X)." % (item.Name, item.Serial), 0x3B)
            return item
    if first is not None:
        log("No runebook named '%s' – using first found: '%s' (0x%X)." % (
            RUNEBOOK_NAME, first.Name or "unnamed", first.Serial), 0x3B)
    return first


def ensure_mounted():
    """Mount the beetle before recall if not already mounted."""
    if Player.Mount is not None:
        return True
    log("Mounting beetle before recall...", 0x3B)
    Mobiles.UseMobile(cfg.beetle_serial)
    Misc.Pause(1500)
    return True


def go_home():
    chiv   = Player.GetSkillValue("Chivalry")
    magery = Player.GetSkillValue("Magery")
    log("go_home: Chivalry=%.1f  Magery=%.1f" % (chiv, magery), 0x3B)

    use_chivalry = chiv >= cfg.min_chivalry_recall
    use_magery   = magery >= cfg.min_magery_recall

    if use_chivalry:
        spell_label = "Sacred Journey (Chivalry %.1f)" % chiv
    elif use_magery:
        spell_label = "Recall (Magery %.1f)" % magery
    else:
        log("Neither Chivalry (%.1f) nor Magery (%.1f) meets the recall threshold." % (chiv, magery), 0x25)
        return

    ensure_mounted()

    runebook = find_runebook_home()
    if runebook is None:
        log("No runebook found in backpack – cannot recall.", 0x25)
        return

    log("Casting %s → targeting '%s'..." % (spell_label, runebook.Name or "unnamed"))
    Target.ClearQueue()
    if use_chivalry:
        Spells.CastChivalry("Sacred Journey")
    else:
        Spells.CastMagery("Recall")

    log("Waiting for target cursor...", 0x3B)
    if not Target.WaitForTarget(6000, False):
        log("Target cursor timed out – spell may have fizzled.", 0x25)
        return

    log("Targeting runebook (0x%X)..." % runebook.Serial, 0x3B)
    Target.TargetExecute(runebook.Serial)
    Misc.Pause(800)

    # If the runebook has a default rune set, the shard auto-recalls on target
    # with no gump. If a gump does open (non-default runebook), click the slot.
    if Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 3000):
        log("Clicking rune slot %d..." % RECALL_RUNE_BTN, 0x3B)
        Gumps.SendAction(RUNEBOOK_GUMP_ID, RECALL_RUNE_BTN)
    else:
        log("Default rune used – auto-recalled.", 0x3B)

    Misc.Pause(3000)
    log("Arrived home.")


# ─────────────────────────────────────────────────────────────────────────────
# Waypoint file I/O
# ─────────────────────────────────────────────────────────────────────────────
def load_waypoints():
    """Load [[X, Y], ...] from WAYPOINT_FILE. Returns empty list if missing."""
    try:
        with open(WAYPOINT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_waypoints(pts):
    """Write [[X, Y], ...] to WAYPOINT_FILE."""
    with open(WAYPOINT_FILE, "w") as f:
        json.dump(pts, f, indent=4)


# ─────────────────────────────────────────────────────────────────────────────
# Waypoint recorder
# ─────────────────────────────────────────────────────────────────────────────
def record_waypoints():
    """
    Interactive recorder.  Walk to each spot you want to chop and say:
      "wp"    – stamp current (X, Y) position as a waypoint
      "clear" – discard all recorded waypoints and start over
      "done"  – save lumberjackwaypoint.json and exit
    """
    pts = load_waypoints()
    log("=== Waypoint Recorder ===", 0x0481)
    log("Say 'wp' to stamp position, 'clear' to reset, 'done' to save.", 0x0481)
    log("%d existing waypoint(s) loaded from %s." % (len(pts), WAYPOINT_FILE), 0x0481)
    Journal.Clear()

    while True:
        Misc.Pause(200)

        if Journal.Search("done"):
            Journal.Clear()
            save_waypoints(pts)
            log("Saved %d waypoint(s) to %s." % (len(pts), WAYPOINT_FILE), 0x0481)
            break

        if Journal.Search("clear"):
            Journal.Clear()
            pts = []
            log("Cleared all waypoints.", 0x25)
            continue

        if Journal.Search("wp"):
            Journal.Clear()
            pos = Player.Position
            pts.append([pos.X, pos.Y])
            log("Waypoint %d recorded: (%d, %d)" % (len(pts), pos.X, pos.Y), 0x0481)


# ─────────────────────────────────────────────────────────────────────────────
# Waypoint chopping loop
# ─────────────────────────────────────────────────────────────────────────────
def run_waypoint_loop():
    """
    Load lumberjackwaypoint.json, walk to each waypoint in order, and chop
    all trees within cfg.search_radius before advancing to the next stop.
    Loops continuously when cfg.waypoint_loop = True.
    """
    waypoints = load_waypoints()
    if not waypoints:
        log("No waypoints found in %s – stopping." % WAYPOINT_FILE, 0x25)
        log("Run with cfg.mode = 'record' to create a route.", 0x25)
        return

    log("=== Waypoint Lumberjacking: %d waypoints ===" % len(waypoints), 0x0481)
    log("Say 'quit' in chat to stop at any time.", 0x0481)
    Journal.Clear()
    if not _startup_transfer():
        return
    wp_index = 0

    while True:
        if Player.WarMode:
            log("War mode detected – stopping.", 0x25)
            break
        if Journal.Search("quit"):
            Journal.Clear()
            log("Quit received – stopping.", 0x026C)
            break

        wp = waypoints[wp_index]
        tx, ty = wp[0], wp[1]
        log("=== Waypoint %d/%d → (%d, %d) ===" % (wp_index + 1, len(waypoints), tx, ty), 0x0481)

        if walk_to(tx, ty):
            result = chop_nearby_trees(None)
            if result in ("quit", "no_tool", "go_home"):
                break
        else:
            log("Could not reach waypoint %d – skipping." % (wp_index + 1), 0x25)

        wp_index += 1

        if wp_index >= len(waypoints):
            log("Completed full waypoint loop.", 0x0481)
            if not cfg.waypoint_loop:
                log("waypoint_loop=False – stopping after one pass.", 0x0481)
                break
            wp_index = 0
            log("Looping back to waypoint 1.", 0x0481)

        Misc.Pause(cfg.loop_delay)


# ─────────────────────────────────────────────────────────────────────────────
# Stationary main loop (original behavior)
# ─────────────────────────────────────────────────────────────────────────────
def _run_to_chop_site():
    """Run west then northwest to reach the chop site from home."""
    log("Running to chop site (%dW then %dNW)..." % (cfg.run_west_steps, cfg.run_nw_steps), 0x3B)
    for _ in range(cfg.run_west_steps):
        Player.Run("West")
        Misc.Pause(cfg.walk_pause)
    for _ in range(cfg.run_nw_steps):
        Player.Run("Northwest")
        Misc.Pause(cfg.walk_pause)
    log("Arrived at chop site.", 0x3B)


def _startup_transfer():
    """
    Transfer any wood to the beetle at script start.
    Returns True if chopping should proceed, False if the beetle was full
    and the player has been sent home (script should stop).
    """
    log("Startup transfer – clearing any wood before chopping.", 0x3B)
    _, beetle_full = split_and_transfer(None)
    if beetle_full:
        log("Beetle full at startup – recalling home to deposit.", 0x25)
        go_home()
        deposit_wood_to_container()
        Player.ChatSay(690, "britain moongate")
        return False
    return True


def run_lumberjack_loop():
    pos = Player.Position
    log("=== Lumberjacking started at (%d, %d, %d) ===" % (pos.X, pos.Y, pos.Z), 0x0481)
    log("Say 'quit' in chat to stop at any time.", 0x0481)
    Journal.Clear()
    if not _startup_transfer():
        return
    if cfg.run_to_site:
        _run_to_chop_site()
    chop_nearby_trees(None)   # beetle lookup happens after dismount inside transfer


def main():
    log("=== Lumberjack Script (mode=%s) ===" % cfg.mode, 0x0481)
    if cfg.mode == "record":
        record_waypoints()
    elif cfg.mode == "waypoints":
        run_waypoint_loop()
    else:
        run_lumberjack_loop()


main()
