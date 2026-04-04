# ─────────────────────────────────────────────────────────────────────────────
# mining.py
# Full mining automation script for Razor Enhanced.
#
# Features:
#   - Monitors journal for "no ore", "can't mine", and "pack full" signals.
#   - Cycles through 8 directions around the player when a spot is blocked.
#   - Transfers ore to a pack animal once the player exceeds the weight limit.
#   - Smelts ore in batches using a detected or player-selected forge.
#   - Command prompt menu on launch: mine | smelt | mount | forge | quit
#
# Config: edit the `cfg` class near the top of this file (or mining_config.py for reference).
# ─────────────────────────────────────────────────────────────────────────────

# IDE IntelliSense support – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

# ─────────────────────────────────────────────────────────────────────────────
# Config  (mirrors mining_config.py – edit here or in that file, keep in sync)
# ─────────────────────────────────────────────────────────────────────────────
class cfg:
    weight_transfer_threshold = 400   # stones before transferring ore to mount
    smelt_batch_size          = 20    # ore units per smelt pass (unused in loop; server handles stacks)
    pause_after_mine          = 1600  # ms – mine swing + server round-trip
    pause_after_smelt         = 1500  # ms – after each smelt operation
    pause_after_transfer      = 1000  # ms – between each Items.Move / MoveOnGround call
    pause_after_drop_settle   = 2500  # ms – wait after all ore is on ground before smelting
    loop_delay                = 100   # ms – bottom of every main loop iteration
    mining_directions = [
        (-1,  0),   # west
        ( 1,  0),   # east
        ( 0, -1),   # north
        ( 0,  1),   # south
        (-1, -1),   # northwest
        ( 1, -1),   # northeast
        (-1,  1),   # southwest
        ( 1,  1),   # southeast
    ]

# ── Journal signals ───────────────────────────────────────────────────────────
# Partial strings – Journal.Search does a substring match (case-sensitive).
JOURNAL_NO_ORE     = "no metal here to mine"
JOURNAL_CANT_MINE  = ["can't mine there", "cannot be seen",
                       "That is not accessable", "blocked"]
JOURNAL_PACK_FULL  = "Your backpack is full"

# Human-readable direction labels (aligned with cfg.mining_directions order)
DIR_LABELS = ["West", "East", "North", "South", "NW", "NE", "SW", "SE"]

# ── Item IDs ─────────────────────────────────────────────────────────────────
PICKAXE_ID = 0x0E86   # pickaxe (double-click to mine)
# Raw ore – all four pile graphic IDs; hue distinguishes the metal type.
# 0x19B7/0x19B8 = standard piles; 0x19B9/0x19BA = alternate graphics some shards use.
ORE_IDS    = [0x19B7, 0x19B8, 0x19B9, 0x19BA]
INGOT_IDS  = [0x1BF2, 0x1BEF, 0x1BE0, 0x1BE1, 0x1BE8, 0x1BE9, 0x1BEA, 0x1BEB,
              0x1BEC, 0x1BED, 0x1BEE, 0x1BE2, 0x1BE3, 0x1BE4, 0x1BE5, 0x1BE6,
              0x1BE7]
# Forge object IDs (player-placed and built-in map forges)
FORGE_IDS  = [0x0FB1, 0x0FAF, 0x0FAD, 0x0FAE, 0x0FB0]

RUNEBOOK_ITEM_ID  = 0x22C5
GATE_TRAVEL_DELAY = 4000   # ms to wait for gate to open / travel to complete

# ── Session state (persists for the life of this script run) ──────────────────
forge_serial         = None
mount_serial         = None
smelting_in_progress = False
# Maps (dx, dy) -> (tz, tile_id) after the first successful swing per direction.
# Cleared automatically if the cached values stop working (player moved).
_tile_cache = {}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def log(msg, color=0x3F):
    Misc.SendMessage("[MINING] %s" % msg, color)


def get_tool():
    """Return the first pickaxe found in the player's backpack."""
    return Items.FindByID(PICKAXE_ID, -1, Player.Backpack.Serial)


def find_forge_nearby():
    """Scan the immediate area for a forge and return its serial, or None."""
    for fid in FORGE_IDS:
        forge = Items.FindByID(fid, -1, -1, 4)
        if forge is not None:
            return forge.Serial
    return None


def ensure_forge():
    """Guarantee forge_serial is set, prompting the player if auto-detect fails."""
    global forge_serial
    if forge_serial is not None:
        return True
    found = find_forge_nearby()
    if found is not None:
        forge_serial = found
        log("Forge auto-detected (serial 0x%X)." % forge_serial)
        return True
    log("No forge found nearby. Please click on one.", 0x25)
    forge_serial = Target.PromptTarget("Select the forge to smelt at:")
    return forge_serial is not None


def find_ore_in_backpack():
    """Return the first ore stack in the player's backpack, or None."""
    for oid in ORE_IDS:
        ore = Items.FindByID(oid, -1, Player.Backpack.Serial)
        if ore is not None:
            return ore
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Smelting
# ─────────────────────────────────────────────────────────────────────────────

def pull_ore_to_backpack(source_serial, source_label):
    """
    Move all ore from source_serial into the player's backpack.
    The player's own backpack is always accessible for UseItem, so smelting
    from it never triggers 'That is not accessible'.
    """
    pulled = 0
    for oid in ORE_IDS:
        ore = Items.FindByID(oid, -1, source_serial)
        while ore is not None:
            Items.Move(ore, Player.Backpack, ore.Amount)
            Misc.Pause(cfg.pause_after_transfer)
            pulled += 1
            ore = Items.FindByID(oid, -1, source_serial)
    if pulled:
        log("Pulled %d stack(s) from %s into backpack." % (pulled, source_label))
    else:
        log("No ore in %s." % source_label, 0x3B)
    return pulled


SMELT_FAIL_PHRASES = [
    "not enough metal",
    "no metal",
    "cannot smelt",
    "you have no metal",
    "there is not",
]

def smelt_from_backpack():
    """Smelt every ore stack currently in the player's backpack. Returns count."""
    count = 0
    Journal.Clear()
    for oid in ORE_IDS:
        ore = Items.FindByID(oid, -1, Player.Backpack.Serial)
        while ore is not None:
            prev_serial = ore.Serial
            Items.UseItem(ore)
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(forge_serial)
            Misc.Pause(cfg.pause_after_smelt)
            # If the server says there's not enough ore in this stack, skip it
            # rather than looping forever on a stack we can't smelt.
            failed = False
            for phrase in SMELT_FAIL_PHRASES:
                if Journal.Search(phrase):
                    log("Skipping stack (0x%08X) – %s" % (prev_serial, phrase), 0x3B)
                    failed = True
                    break
            Journal.Clear()
            if failed:
                break
            count += 1
            ore = Items.FindByID(oid, -1, Player.Backpack.Serial)
            # If the same item is still there, the smelt silently failed – bail out
            if ore is not None and ore.Serial == prev_serial:
                log("Ore unchanged after smelt attempt – skipping stack.", 0x3B)
                break
    return count


def smelt_ore():
    """
    Smelt all ore without exceeding player weight:
      1. Smelt whatever is already in the player's backpack.
      2. Pull one stack at a time from the pack animal and smelt immediately –
         the pack never accumulates more than one extra stack so weight stays low.
    """
    global smelting_in_progress
    smelting_in_progress = True
    try:
        _smelt_ore_impl()
    finally:
        smelting_in_progress = False


def _smelt_ore_impl():
    if not ensure_forge():
        log("Smelt aborted – no forge available.", 0x25)
        return

    global mount_serial

    # ── Smelt player backpack first ───────────────────────────────────────────
    log("Smelting player backpack...")
    smelt_from_backpack()

    # ── Smelt animal pack one stack at a time ─────────────────────────────────
    mount = None
    if mount_serial is not None:
        mount = Mobiles.FindBySerial(mount_serial)
    if mount is None:
        mount = find_pack_animal()
        if mount is not None:
            mount_serial = mount.Serial

    if mount is not None and mount.Backpack is not None:
        Items.UseItem(mount.Backpack)
        Items.WaitForContents(mount.Backpack, 3000)
        Misc.Pause(cfg.pause_after_transfer)
        log("Smelting %s's ore one stack at a time..." % mount.Name)
        for oid in ORE_IDS:
            ore = Items.FindByID(oid, -1, mount.Backpack.Serial)
            while ore is not None:
                # ore.Weight is the total stack weight; divide to get per-unit.
                # Fall back to 2 (standard UO ore) if the stack is empty/corrupt.
                per_unit = (float(ore.Weight) / ore.Amount) if ore.Amount > 0 else 2.0
                can_carry = Player.MaxWeight - Player.Weight
                if can_carry <= 0:
                    log("Player at max weight – smelting backpack before pulling more.", 0x25)
                    smelt_from_backpack()
                    can_carry = Player.MaxWeight - Player.Weight
                if can_carry <= 0:
                    log("Still at max weight after smelt – aborting animal smelt.", 0x25)
                    return
                amount = min(ore.Amount, max(1, int(can_carry / per_unit)))
                Items.Move(ore, Player.Backpack, amount)
                Misc.Pause(cfg.pause_after_transfer)
                smelt_from_backpack()
                ore = Items.FindByID(oid, -1, mount.Backpack.Serial)
    else:
        log("No pack animal nearby – smelted player backpack only.", 0x25)

    log("Smelt complete.")


# ─────────────────────────────────────────────────────────────────────────────
# Pack-animal transfer
# ─────────────────────────────────────────────────────────────────────────────

def find_pack_animal():
    """
    Auto-detect a pack animal by scanning nearby followers for one that has
    a container (backpack). Returns the Mobile, or None if none found.
    """
    filter = Mobiles.Filter()
    filter.RangeMax   = 3
    filter.IsHuman    = False
    filter.Friend     = True   # followers / pets only
    nearby = Mobiles.ApplyFilter(filter)
    for mob in nearby:
        if mob.Serial == Player.Serial:
            continue
        if mob.Backpack is not None:
            return mob
    return None


def transfer_to_mount():
    """
    Move all ore from the player's backpack into the pack animal's backpack.
    Auto-detects the nearest follower with a backpack; caches the serial so it
    only scans once per session.  Falls back gracefully if none is found.
    Returns True on success, False if no usable mount is available.
    """
    global mount_serial

    mount = None
    if mount_serial is not None:
        mount = Mobiles.FindBySerial(mount_serial)

    if mount is None:
        mount = find_pack_animal()
        if mount is not None:
            mount_serial = mount.Serial
            log("Pack animal auto-detected: %s (0x%X)." % (mount.Name, mount_serial))
        else:
            log("No pack animal found nearby.", 0x25)
            return False

    log("Transferring ore – pausing mining until transfer completes...")

    mount_full = False
    for oid in ORE_IDS:
        if mount_full:
            break
        ore = Items.FindByID(oid, -1, Player.Backpack.Serial)
        while ore is not None:
            pre_count = Items.FindByID(oid, -1, mount.Backpack.Serial)
            pre_amount = pre_count.Amount if pre_count is not None else 0

            Items.Move(ore, mount.Backpack, ore.Amount)
            Misc.Pause(cfg.pause_after_transfer)

            # Check whether the item actually moved by comparing ore still in player pack
            ore_after = Items.FindByID(oid, -1, Player.Backpack.Serial)
            if ore_after is not None and ore_after.Serial == ore.Serial:
                # Serial unchanged – server rejected the move; mount pack is likely full
                log("Pack animal's backpack appears full – stopping transfer.", 0x25)
                mount_full = True
                break

            ore = ore_after

    if mount_full:
        log("Transfer incomplete – mount pack full. Weight: %d / %d stones."
            % (Player.Weight, Player.MaxWeight), 0x25)
        return False

    log("Transfer complete. Weight: %d / %d stones." % (Player.Weight, Player.MaxWeight))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Mining
# ─────────────────────────────────────────────────────────────────────────────

def mine_at(dx, dy):
    """
    Swing the mining tool at (Player.X + dx, Player.Y + dy, Player.Z).
    Returns 'ok' after swinging, or 'no_tool' if no pickaxe is found.
    """
    tool = get_tool()
    if tool is None:
        log("No pickaxe found in backpack!", 0x25)
        return "no_tool"

    global _tile_cache
    pos = Player.Position
    tx, ty = pos.X + dx, pos.Y + dy

    def _swing(tz, tile_id):
        Journal.Clear()
        Items.UseItem(tool)
        Target.WaitForTarget(3000, False)
        Target.TargetExecute(tx, ty, tz, tile_id)
        Misc.Pause(cfg.pause_after_mine)
        return not Journal.Search("cannot be seen")

    # ── Use cached tile info if available ─────────────────────────────────────
    if (dx, dy) in _tile_cache:
        tz, tile_id = _tile_cache[(dx, dy)]
        _swing(tz, tile_id)
        return "ok"

    # ── First attempt: land tile (works outdoors) ─────────────────────────────
    if _swing(pos.Z, 0x0000):
        _tile_cache[(dx, dy)] = (pos.Z, 0x0000)
        return "ok"

    # ── Cave fallback: look up the static tile ────────────────────────────────
    log("Land tile not visible – probing static for cave floor...", 0x3B)
    statics = Statics.GetStaticsTileInfo(tx, ty, Player.Map)
    if not statics or len(statics) == 0:
        log("No static tile at (%d,%d) – unreachable." % (tx, ty), 0x25)
        return "cant_mine"

    tile    = statics[0]
    tz      = tile.StaticZ
    tile_id = tile.StaticID
    if _swing(tz, tile_id):
        _tile_cache[(dx, dy)] = (tz, tile_id)
        log("Cached cave tile (%+d,%+d) Z=%d ID=0x%04X" % (dx, dy, tz, tile_id), 0x3B)
        return "ok"

    log("Both land and static swing failed for (%d,%d).", 0x25)
    return "cant_mine"


def read_journal_status():
    """
    Return a string describing the most recent mining outcome:
      'no_ore'    – tile has no minable metal
      'cant_mine' – tile cannot be mined (wall, water, etc.)
      'pack_full' – player's backpack is full
      'ok'        – no problem signal detected
    """
    if Journal.Search(JOURNAL_NO_ORE):
        return "no_ore"
    for phrase in JOURNAL_CANT_MINE:
        if Journal.Search(phrase):
            log("Journal matched cant_mine phrase: '%s'" % phrase, 0x3B)
            return "cant_mine"
    if Journal.Search(JOURNAL_PACK_FULL):
        return "pack_full"
    return "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Banking
# ─────────────────────────────────────────────────────────────────────────────

MOONGATE_ID = 0x0F6C

def bank_ingots():
    """
    Cast Gate Travel on the runebook (uses its default rune = bank), step
    through the moongate, say 'bank' to open the box, deposit all ingots.
    """
    # ── Find runebook ─────────────────────────────────────────────────────────
    runebook = Items.FindByID(RUNEBOOK_ITEM_ID, -1, Player.Backpack.Serial)
    if runebook is None:
        log("No runebook in backpack – target it now...", 0x25)
        rb_serial = Target.PromptTarget("Target the runebook with your bank rune set as default")
        runebook  = Items.FindBySerial(rb_serial)
        if runebook is None or runebook.ItemID != RUNEBOOK_ITEM_ID:
            log("That is not a runebook – banking aborted.", 0x25)
            return

    # ── Cast Gate Travel targeting the runebook ───────────────────────────────
    log("Casting Gate Travel to bank...")
    Journal.Clear()
    Spells.CastMagery("Gate Travel")
    Target.WaitForTarget(4000, False)
    Target.TargetExecute(runebook.Serial)

    # Wait for the server confirmation phrase before searching for the gate
    Timer.Create("gate_cast_timeout", 6000)
    while Timer.Check("gate_cast_timeout"):
        if Journal.Search("You open a magical gate"):
            log("Gate opened successfully.")
            break
        Misc.Pause(100)
    else:
        log("Gate Travel confirmation not seen – spell may have failed.", 0x25)
        return

    Misc.Pause(500)   # brief settle so the gate item spawns

    # ── Find the moongate and step through ────────────────────────────────────
    log("Looking for moongate...")
    gate = None
    Timer.Create("gate_find_timeout", 4000)
    while Timer.Check("gate_find_timeout"):
        gate = Items.FindByID(MOONGATE_ID, -1, -1, 3)
        if gate is not None:
            break
        Misc.Pause(200)

    if gate is None:
        log("No moongate found within 3 tiles – cannot step through.", 0x25)
        return

    log("Stepping through gate (serial 0x%X)..." % gate.Serial)
    Items.UseItem(gate)
    Misc.Pause(GATE_TRAVEL_DELAY)

    # ── Open bank ─────────────────────────────────────────────────────────────
    Journal.Clear()
    Player.ChatSay(0x3F, "bank")
    Timer.Create("bank_open_timeout", 6000)
    while Timer.Check("bank_open_timeout"):
        if Player.Bank is not None:
            break
        Misc.Pause(200)

    if Player.Bank is None:
        log("Could not open bank – are you near a banker?", 0x25)
        return

    Misc.Pause(500)

    # ── Deposit all ingots ────────────────────────────────────────────────────
    total = 0
    for iid in INGOT_IDS:
        stack = Items.FindByID(iid, -1, Player.Backpack.Serial)
        while stack is not None:
            total += stack.Amount
            Items.Move(stack, Player.Bank, stack.Amount)
            Misc.Pause(cfg.pause_after_transfer)
            stack = Items.FindByID(iid, -1, Player.Backpack.Serial)

    if total:
        log("Deposited %d ingots into bank." % total)
    else:
        log("No ingots found to deposit.", 0x3B)


def check_loop_command():
    """
    Check whether the player has typed a control command in chat.
    Called once per loop iteration — does NOT clear the journal.
    Returns a command string if found, otherwise None.
      'quit'  – stop mining
      'smelt' – smelt both packs then resume
      'mount' – reset pack animal cache then resume
      'forge' – re-prompt for forge then resume
      'bank'  – gate to bank runebook default rune, deposit ingots, return
    """
    for cmd in ("quit", "smelt", "mount", "forge", "bank"):
        if Journal.Search(cmd):
            Journal.Clear()
            return cmd
    return None


def run_mining_loop():
    """
    Main loop:
      1. Check for in-chat commands (quit / smelt / mount / forge).
      2. Check player weight; transfer to mount if over threshold.
      3. Mine the current direction.
      4. Evaluate journal; rotate direction on failure; smelt / transfer on full.
      5. Reset the consecutive-fail counter after any successful mine.
    """
    global mount_serial, forge_serial

    num_dirs     = len(cfg.mining_directions)
    dir_index    = 0
    consec_fails = 0

    pos = Player.Position
    log("Mining started at (%d, %d, %d)." % (pos.X, pos.Y, pos.Z))
    log("Say: 'quit' to stop | 'smelt' to smelt | 'mount' to reset animal | 'forge' to reset forge | 'bank' to bank ingots", 0x0481)
    Journal.Clear()

    while True:

        # ── In-loop chat command check ───────────────────────────────────────
        cmd = check_loop_command()
        if cmd == "quit":
            log("Quit received – stopping.", 0x026C)
            break
        elif cmd == "smelt":
            smelt_ore()
            log("Smelt complete – stopping.", 0x026C)
            break
        elif cmd == "mount":
            mount_serial = None   # clear cache so next transfer re-detects
            log("Pack animal cache cleared – will re-detect on next transfer.", 0x3F)
            Journal.Clear()
        elif cmd == "forge":
            forge_serial = None
            ensure_forge()
            Journal.Clear()
        elif cmd == "bank":
            bank_ingots()
            log("Bank complete – stopping.", 0x026C)
            break

        # ── Weight threshold check ────────────────────────────────────────────
        if not smelting_in_progress and Player.Weight >= cfg.weight_transfer_threshold:
            log("Weight %d / %d – transferring ore to pack animal."
                % (Player.Weight, Player.MaxWeight), 0x25)
            if not transfer_to_mount():
                log("Mount pack full or unavailable – smelting to free space.", 0x25)
                smelt_ore()
                if Player.Weight >= cfg.weight_transfer_threshold:
                    log("Still overweight after smelt – stopping.", 0x25)
                    break

        # ── Mine current direction ────────────────────────────────────────────
        dx, dy    = cfg.mining_directions[dir_index]
        pos       = Player.Position
        label     = DIR_LABELS[dir_index] if dir_index < len(DIR_LABELS) else str(dir_index)
        tx, ty    = pos.X + dx, pos.Y + dy
        log("Swinging %s → target (%d, %d, %d)  [dir %d/%d]"
            % (label, tx, ty, pos.Z, dir_index + 1, num_dirs))        # Head message appears above the character so you can see direction in-world.
        Player.HeadMessage(0x3F, "Mining %s" % label)
        mine_result = mine_at(dx, dy)
        if mine_result == "no_tool":
            log("Stopping – no mining tool found.")
            break

        # ── Evaluate journal ──────────────────────────────────────────────────
        status = read_journal_status()
        log("Journal status: %s" % status, 0x3B)

        if status in ("no_ore", "cant_mine"):
            consec_fails += 1
            dir_index     = (dir_index + 1) % num_dirs
            dx2, dy2      = cfg.mining_directions[dir_index]
            log("Spot unmineable (%s). Rotating to direction %d / %d  (dx=%+d, dy=%+d)."
                % (status, dir_index + 1, num_dirs, dx2, dy2), 0x25)
            if consec_fails >= num_dirs:
                log("All %d directions exhausted with no ore. Stopping." % num_dirs, 0x25)
                break

        elif status == "pack_full":
            if smelting_in_progress:
                pass  # already smelting – ignore pack_full signal mid-smelt
            else:
                log("Backpack full – transferring ore to pack animal.", 0x25)
                if not transfer_to_mount():
                    log("Mount pack full or unavailable – smelting to free space.", 0x25)
                    smelt_ore()
                    if Player.Weight >= cfg.weight_transfer_threshold:
                        log("Still overweight after smelt – stopping.", 0x25)
                        break
            consec_fails = 0

        else:
            consec_fails = 0   # successful mine – reset the rotation counter

        Misc.Pause(cfg.loop_delay)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point – start mining immediately
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log("=== Mining Script ===", 0x0481)
    run_mining_loop()


main()


    