# ─────────────────────────────────────────────────────────────────────────────
# LumberJack.py
# Lumberjacking automation for Razor Enhanced.
#
# Features:
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

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
class cfg:
    weight_split_threshold = 369   # split logs when weight reaches this
    weight_go_home         = 376   # recall home when weight reaches this

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
HATCHET_IDS = [0x0F43, 0x0F3F, 0x143E]   # hatchets / axes for chopping
LOG_ID      = 0x1BDD                      # raw logs in backpack
RUNEBOOK_ID = 0x22C5                      # runebook graphic ID


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
def split_logs():
    log("Splitting logs into boards...")
    passes = 0
    logs = find_logs()
    while logs is not None:
        axe = find_axe()
        if axe is None:
            log("No axe in backpack – cannot split logs.", 0x25)
            break
        prev_serial = logs.Serial
        Target.ClearQueue()
        Items.UseItem(axe)
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(logs.Serial)
        Misc.Pause(cfg.pause_after_split)
        passes += 1
        logs = find_logs()
        # If the same serial is still present the server rejected the attempt
        if logs is not None and logs.Serial == prev_serial:
            log("Log split did not consume stack – stopping split.", 0x3B)
            break
    log("Split complete (%d pass(es))." % passes)


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
    """Take one walk step toward (tx, ty). Returns True if already adjacent or there."""
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


def walk_adjacent_to(tx, ty):
    """
    Walk to any tile adjacent to (tx, ty).
    The tree tile itself is impassable, so we stand next to it.
    Returns True when we are within 1 tile of the target.
    """
    max_steps = 30
    for _ in range(max_steps):
        pos = Player.Position
        if abs(pos.X - tx) <= 1 and abs(pos.Y - ty) <= 1:
            return True
        _step_toward(tx, ty)
    log("Could not reach adjacent tile for (%d,%d) in %d steps." % (tx, ty, max_steps), 0x25)
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
# Home recall — finds runebook by item ID, uses gump slot 1 (button 90)
# ─────────────────────────────────────────────────────────────────────────────
def go_home():
    if Player.Backpack is None:
        log("Backpack unavailable – cannot go home.", 0x25)
        return

    runebook = Items.FindByID(RUNEBOOK_ID, -1, Player.Backpack.Serial)
    if runebook is None:
        log("No runebook in backpack – cannot go home.", 0x25)
        return

    log("Recalling home via runebook...")
    Items.UseItem(runebook)
    if not Gumps.WaitForGump(89, 5000):
        log("Runebook gump did not open.", 0x25)
        return
    Misc.Pause(300)
    # Button 90 = recall rune slot 1.  Change if your home rune is in a
    # different slot (slots are numbered 1-16, button = 89 + slot_number).
    Gumps.SendAction(89, 90)
    Misc.Pause(3000)
    log("Arrived home.")


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────
def run_lumberjack_loop():
    pos = Player.Position
    log("=== Lumberjacking started at (%d, %d, %d) ===" % (pos.X, pos.Y, pos.Z), 0x0481)
    log("Say 'quit' in chat to stop at any time.", 0x0481)
    Journal.Clear()
    depleted_trees = set()

    while True:

        # ── War-mode kill switch ─────────────────────────────────────────────
        if Player.WarMode:
            log("War mode detected – stopping.", 0x25)
            break

        # ── Chat quit command ─────────────────────────────────────────────────
        if Journal.Search("quit"):
            Journal.Clear()
            log("Quit received – stopping.", 0x026C)
            break

        weight = Player.Weight

        # ── Full pack: split then go home ────────────────────────────────────
        if weight >= cfg.weight_go_home:
            log("Weight %d – splitting logs then recalling home." % weight, 0x25)
            split_logs()
            go_home()
            Player.ChatSay(690, "britain moongate")
            log("Stopping after home recall.", 0x026C)
            break

        # ── Getting heavy: split logs to free weight ─────────────────────────
        if weight >= cfg.weight_split_threshold:
            log("Weight %d – splitting logs." % weight, 0x25)
            split_logs()
            Misc.Pause(cfg.loop_delay)
            continue

        # ── Find nearest tree ────────────────────────────────────────────────
        tree = find_nearby_tree(depleted_trees)
        if tree is None:
            log("No tree found within radius %d. Stopping." % cfg.search_radius, 0x25)
            break
        tx, ty, tz, tile_id = tree
        log("Tree at (%d,%d) tile=0x%04X Z=%d – walking there." % (tx, ty, tile_id, tz), 0x3B)

        # ── Walk adjacent to the tree tile ──────────────────────────────────
        if not walk_adjacent_to(tx, ty):
            log("Could not reach tree – stopping.", 0x25)
            break

        # ── Chop until tree is depleted ──────────────────────────────────────
        log("Chopping tree at (%d,%d)..." % (tx, ty), 0x3B)
        bad_position_count = 0
        while True:
            if Player.WarMode:
                log("War mode – stopping.", 0x25)
                return
            if Journal.Search("quit"):
                log("Quit received – stopping.", 0x026C)
                return

            weight = Player.Weight
            if weight >= cfg.weight_go_home:
                log("Weight %d – splitting then going home." % weight, 0x25)
                split_logs()
                go_home()
                Player.ChatSay(690, "britain moongate")
                log("Stopping after home recall.", 0x026C)
                return
            if weight >= cfg.weight_split_threshold:
                split_logs()

            result = chop_once(tx, ty, tz, tile_id)
            log("chop result: %s" % result, 0x3B)

            if result == "no_tool":
                return
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
                split_logs()
                depleted_trees.add((tx, ty))
                break   # back to outer loop to find another tree
            elif result == "pack_full":
                split_logs()
            # 'ok' → keep chopping same tree

        Misc.Pause(cfg.loop_delay)


def main():
    log("=== Lumberjack Script ===", 0x0481)
    run_lumberjack_loop()


main()
