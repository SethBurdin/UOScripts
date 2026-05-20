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
    weight_headroom           = 50    # transfer when Player.Weight >= Player.MaxWeight - this value
    smelt_batch_size          = 20    # ore units per smelt pass (unused in loop; server handles stacks)
    pause_after_mine          = 1600  # ms – mine swing + server round-trip
    pause_after_smelt         = 1500  # ms – after each smelt operation
    pause_after_transfer      = 1000  # ms – between each Items.Move / MoveOnGround call
    pause_after_drop_settle   = 2500  # ms – wait after all ore is on ground before smelting
    loop_delay                = 100   # ms – bottom of every main loop iteration
    max_silent_ok             = 2     # rotate direction after this many swings with no journal response

    travel_method    = 'gate'  # 'gate' or 'recall'
    bank_rune_slot   = None    # runebook slot (0-15) for bank; None = use default rune
    mine_rune_slot   = None    # runebook slot (0-15) to return to after banking; None = stop at bank

    # Body graphic IDs — verify with Object Inspector if your shard differs.
    pack_beetle_body   = 0x00EF     # giant/pack beetle
    fire_beetle_body   = 0x00A9     # fire beetle (acts as mobile forge)

    # Optional hardcoded serials — set these to skip the mobile scan entirely.
    # Useful when auto-detect is unreliable (e.g. beetle is out of scan range).
    fire_beetle_serial = None
    pack_beetle_serial = None
    locked_pet = None

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

    home_container_serial = None  # resolved at runtime from config.quick_dropbox
    home_forge_serial     = 0x400750FE
    pickaxe_box_serial    = 0x4005AA6E  # serial of the box at home holding spare pickaxes

    # Auto mode
    auto_mining_rune_filter = 'Mining Spot'  # partial match (case-insensitive) for runes to visit
    auto_home_runebook      = 'home'         # label of the runebook to gate home when overweight
    auto_mining_runebook    = 'mining'       # label of the runebook containing mining spots;
                                             # None = first runebook found in backpack

# ── Journal signals ───────────────────────────────────────────────────────────
# Partial strings – Journal.Search does a substring match (case-sensitive).
JOURNAL_NO_ORE     = ["There is no metal here to mine",
                      "no metal here to mine", "no Metal here to mine",
                      "no ore here to mine",   "no Ore here to mine",
                      "There is no metal",     "There is no ore",
                      "find no ore",           "find no metal"]
JOURNAL_CANT_MINE  = ["can't mine there", "cannot be seen",
                       "That is not accessable", "blocked"]
JOURNAL_PACK_FULL  = "Your backpack is full"
# Broad fragments present in any shard's "you got ore" message.
# If your shard uses different text, add a fragment here.
JOURNAL_ORE_SUCCESS = ["backpack", "put", "ore"]

# Human-readable direction labels (aligned with cfg.mining_directions order)
DIR_LABELS = ["West", "East", "North", "South", "NW", "NE", "SW", "SE"]

# ── Item IDs ─────────────────────────────────────────────────────────────────
PICKAXE_ID  = 0x0E86   # pickaxe (double-click to mine)
# HATCHET_ID  = 0x0F43   # hatchet — verify with Object Inspector if wrong
MINING_TOOL_IDS = [PICKAXE_ID]
# Raw ore – all four pile graphic IDs; hue distinguishes the metal type.
# 0x19B7/0x19B8 = standard piles; 0x19B9/0x19BA = alternate graphics some shards use.
ORE_IDS    = [0x19B7, 0x19B8, 0x19B9, 0x19BA]
INGOT_IDS  = [0x1BF2, 0x1BEF, 0x1BE0, 0x1BE1, 0x1BE8, 0x1BE9, 0x1BEA, 0x1BEB,
              0x1BEC, 0x1BED, 0x1BEE, 0x1BE2, 0x1BE3, 0x1BE4, 0x1BE5, 0x1BE6,
              0x1BE7]
# Forge object IDs (player-placed and built-in map forges)
FORGE_IDS  = [0x0FB1, 0x0FAF, 0x0FAD, 0x0FAE, 0x0FB0, 0x2DD8]

RUNEBOOK_ITEM_ID    = 0x22C5
TINKER_TOOL_IDS     = [0x1EBC, 0x1EB8]  # tinker's tools, tool kit
TINKERING_GUMP_ID   = 2653346093  # confirmed via macro (same as carpentry gump)
PICKAXE_ITEM_BTN    = 114         # confirmed via macro — no category step needed
PICKAXE_INGOT_COST  = 4
GATE_TRAVEL_DELAY   = 4000   # ms to wait for gate to open / travel to complete
RECALL_TRAVEL_DELAY = 2000   # ms to wait after recall lands
RUNEBOOK_GUMP_ID    = 89
GATE_BUTTON_BASE    = 100    # confirmed: gump button = 100 + slot_index (0-based)


# ── Session state (persists for the life of this script run) ──────────────────
forge_serial         = None
mount_serial         = None
pack_beetle_serial   = None
fire_beetle_serial   = None
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
    """Return the first mining tool (pickaxe or hatchet) found in the player's backpack."""
    for tid in MINING_TOOL_IDS:
        tool = Items.FindByID(tid, -1, Player.Backpack.Serial)
        if tool is not None:
            return tool
    return None


def find_forge_nearby(search_range=4):
    """Scan the area for a forge and return its serial, or None."""
    for fid in FORGE_IDS:
        forge = Items.FindByID(fid, -1, -1, search_range)
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

def push_ore_to_inventory():
    """
    Move all ore from the player's backpack into the pack animal's backpack.
    Returns 'ok', 'none' (no pack animal found), or 'full' (pack animal backpack is full).
    """
    global pack_beetle_serial
    if pack_beetle_serial is None:
        find_beetles()
    if pack_beetle_serial is None:
        log("No pack animal – cannot push ore.", 0x25)
        return 'none'
    mob = Mobiles.FindBySerial(pack_beetle_serial)
    if mob is None or mob.Backpack is None:
        log("Pack animal (0x%X) not accessible." % pack_beetle_serial, 0x25)
        pack_beetle_serial = None
        return 'none'
    pushed = 0
    for oid in ORE_IDS:
        ore = Items.FindByID(oid, -1, Player.Backpack.Serial)
        while ore is not None:
            prev_serial = ore.Serial
            Items.Move(ore, mob.Backpack, ore.Amount)
            Misc.Pause(cfg.pause_after_transfer)
            ore_after = Items.FindByID(oid, -1, Player.Backpack.Serial)
            if ore_after is not None and ore_after.Serial == prev_serial:
                log("%s's pack is full after %d stack(s)." % (mob.Name, pushed), 0x25)
                return 'full'
            pushed += 1
            ore = Items.FindByID(oid, -1, Player.Backpack.Serial)
    if pushed:
        log("Pushed %d stack(s) to %s." % (pushed, mob.Name))
    else:
        log("No ore in backpack to push.", 0x3B)
    return 'ok'


PACK_FULL_PHRASES = [
    "That container cannot hold more items",
    "That container cannot hold any more items",
    "That container cannot hold more weight",
    "Your backpack cannot hold that",
    "There is not enough room",
]

SMELT_FAIL_PHRASES = [
    "not enough metal",   "Not enough metal",
    "no metal",           "No metal",
    "cannot smelt",       "Cannot smelt",
    "you have no metal",  "You have no metal",
    "there is not",       "There is not",
    "not enough ore",     "Not enough ore",
    "too few",            "Too few",
]

def _try_discard_ore(serial):
    """
    Try to move an unsmelttable ore stack out of the backpack.
    Returns True if the stack is gone, False if it is still in the backpack
    (e.g. indoors where ground placement is blocked).
    """
    ore = Items.FindBySerial(serial)
    if ore is None:
        return True
    pos = Player.Position
    Items.MoveOnGround(ore, ore.Amount, pos.X, pos.Y, pos.Z)
    Misc.Pause(cfg.pause_after_transfer)
    return Items.FindBySerial(serial) is None


def smelt_from_backpack(container_serial=None):
    """Smelt every ore stack in container_serial (defaults to player backpack). Returns count."""
    if container_serial is None:
        container_serial = Player.Backpack.Serial
    count = 0
    Journal.Clear()
    for oid in ORE_IDS:
        ore = Items.FindByID(oid, -1, container_serial)
        while ore is not None:
            prev_serial = ore.Serial
            Items.UseItem(ore)
            Target.WaitForTarget(3000, False)
            Target.TargetExecute(forge_serial)
            Misc.Pause(cfg.pause_after_smelt)

            failed = False
            for phrase in SMELT_FAIL_PHRASES:
                if Journal.Search(phrase):
                    log("Skipping stack (0x%08X) – %s" % (prev_serial, phrase), 0x3B)
                    failed = True
                    break
            Journal.Clear()

            if failed:
                if container_serial == Player.Backpack.Serial:
                    if not _try_discard_ore(prev_serial):
                        log("Cannot discard stack 0x%08X – skipping ore type." % prev_serial, 0x3B)
                        break
                    ore = Items.FindByID(oid, -1, container_serial)
                else:
                    break  # can't drop from a remote container; skip this ore type
                continue

            count += 1
            ore = Items.FindByID(oid, -1, container_serial)
            if ore is not None and ore.Serial == prev_serial:
                log("Ore unchanged after smelt – skipping ore type.", 0x3B)
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
    if pack_beetle_serial is not None:
        pull_ore_to_backpack(pack_beetle_serial, "pack beetle")

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
# Beetle detection
# ─────────────────────────────────────────────────────────────────────────────
def find_beetles():
    """
    Locate a pack animal and/or fire beetle.
    Priority:
      1. Body-ID scan for fire beetle (0x00A9) and pack beetle (0x00EF).
      2. If no pack found by body ID, fall back to find_pack_animal() which
         accepts any follower with a backpack regardless of body type.
    Returns (pack_mobile_or_None, fire_mobile_or_None).
    """
    global pack_beetle_serial, fire_beetle_serial

    pack = None
    fire = None

    # ── Body-ID scan ──────────────────────────────────────────────────────────
    filt = Mobiles.Filter()
    filt.RangeMax = 10
    filt.IsHuman  = False
    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial:
            continue
        if mob.Body == cfg.fire_beetle_body:
            fire = mob
            fire_beetle_serial = mob.Serial
        elif mob.Body == cfg.pack_beetle_body:
            pack = mob
            pack_beetle_serial = mob.Serial

    # ── Fallback: any nearby non-human with a backpack (skip fire beetle) ────────
    if pack is None:
        mob = find_pack_animal()
        if mob is not None and mob.Serial != fire_beetle_serial:
            pack = mob
            pack_beetle_serial = mob.Serial

    if pack is not None:
        log("Pack animal: %s (0x%X)" % (pack.Name, pack.Serial), 0x3B)
    if fire is not None:
        log("Fire beetle: %s (0x%X)" % (fire.Name, fire.Serial), 0x3B)
    if pack is None and fire is None:
        log("No pack animal or fire beetle detected.", 0x25)

    return pack, fire


def smelt_with_fire_beetle(fire_beetle):
    """Smelt all ore in the player's backpack using the fire beetle as a mobile forge."""
    global forge_serial
    log("Smelting with fire beetle (0x%X)..." % fire_beetle.Serial)
    prev_forge   = forge_serial
    forge_serial = fire_beetle.Serial
    try:
        smelt_from_backpack()
    finally:
        forge_serial = prev_forge


def try_craft_pickaxe():
    """
    Attempt to craft a pickaxe via tinkering if:
      - Tinkering skill > 50
      - A tinker's tool is in the backpack
      - At least 4 ingots are in the backpack
      - TINKERING_GUMP_ID is configured
    Returns True if a new pickaxe is now in the backpack.
    """
    if Player.GetSkillValue('Tinkering') <= 50:
        log("Tinkering %.1f <= 50 – cannot craft pickaxe." % Player.GetSkillValue('Tinkering'), 0x25)
        return False

    tinker_tool = None
    for tid in TINKER_TOOL_IDS:
        tinker_tool = Items.FindByID(tid, -1, Player.Backpack.Serial)
        if tinker_tool is not None:
            break
    if tinker_tool is None:
        log("No tinker's tools in backpack.", 0x25)
        return False

    ingot_count = 0
    for iid in INGOT_IDS:
        stack = Items.FindByID(iid, -1, Player.Backpack.Serial)
        if stack is not None:
            ingot_count += stack.Amount

    # Ingots are usually on the pack beetle after a transfer — pull just enough to craft.
    if ingot_count < PICKAXE_INGOT_COST:
        needed = PICKAXE_INGOT_COST - ingot_count
        source = None
        if mount_serial is not None:
            source = Mobiles.FindBySerial(mount_serial)
        if source is None:
            source = find_pack_animal()
        if source is not None and source.Backpack is not None:
            Items.UseItem(source.Backpack)
            Items.WaitForContents(source.Backpack, 3000)
            Misc.Pause(400)
            for iid in INGOT_IDS:
                if needed <= 0:
                    break
                stack = Items.FindByID(iid, -1, source.Backpack.Serial)
                if stack is not None:
                    pull = min(stack.Amount, needed)
                    Items.Move(stack, Player.Backpack, pull)
                    Misc.Pause(cfg.pause_after_transfer)
                    ingot_count += pull
                    needed -= pull

    if ingot_count < PICKAXE_INGOT_COST:
        log("Not enough ingots (%d / %d) to craft pickaxe." % (ingot_count, PICKAXE_INGOT_COST), 0x25)
        return False

    log("Crafting pickaxe (Tinkering %.1f)..." % Player.GetSkillValue('Tinkering'))
    before = {item.Serial for item in (Player.Backpack.Contains or [])}

    Items.UseItem(tinker_tool)
    Misc.Pause(800)

    if not Gumps.WaitForGump(TINKERING_GUMP_ID, 5000):
        log("Tinkering gump did not open.", 0x25)
        return False

    Misc.Pause(500)
    Gumps.SendAction(TINKERING_GUMP_ID, PICKAXE_ITEM_BTN)
    Gumps.WaitForGump(TINKERING_GUMP_ID, 5000)
    Gumps.SendAction(TINKERING_GUMP_ID, 0)
    Misc.Pause(600)

    for item in (Player.Backpack.Contains or []):
        if item.Serial not in before and item.ItemID in MINING_TOOL_IDS:
            log("Tool crafted: %s (0x%X)." % (item.Name, item.Serial))
            return True

    log("Tool craft failed – check PICKAXE_ITEM_BTN (%d) for this shard." % PICKAXE_ITEM_BTN, 0x25)
    return False


def _remount_if_needed():
    """Remount on the pack/fire beetle if the player is currently dismounted."""
    if Player.Mount is not None:
        return
    if pack_beetle_serial is None and fire_beetle_serial is None:
        find_beetles()
    remount_serial = pack_beetle_serial or fire_beetle_serial
    if remount_serial is not None:
        log("Remounting...", 0x3B)
        Mobiles.UseMobile(remount_serial)
        Misc.Pause(1500)



def handle_overweight():
    """
    1. Try pack-beetle transfer first (offloads ore).
    2. If still overweight after transfer, smelt with fire beetle or forge.
    Returns True if weight is now under threshold; False triggers a bank run.
    """
    global fire_beetle_serial, pack_beetle_serial

    was_mounted = Player.Mount is not None
    if was_mounted:
        log("Dismounting to scan for beetles...", 0x3B)
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)

    pack, fire = find_beetles()

    if pack_beetle_serial is not None:
        push_ore_to_inventory()

    if Player.Weight >= Player.MaxWeight - cfg.weight_headroom:
        if fire is not None:
            smelt_with_fire_beetle(fire)
        else:
            smelt_ore()

    remount_target = pack or fire
    if was_mounted and remount_target is not None:
        Mobiles.UseMobile(remount_target.Serial)
        Misc.Pause(1500)

    return Player.Weight < Player.MaxWeight - cfg.weight_headroom


# ─────────────────────────────────────────────────────────────────────────────
# Pack-animal transfer
# ─────────────────────────────────────────────────────────────────────────────

def find_pack_animal():
    """
    Auto-detect a pack animal by scanning nearby non-human mobiles for one that has
    a backpack. Friend filter is intentionally omitted — it matches Razor's friends
    list, not UO followers, and would exclude pack animals not manually listed there.
    Any non-human mobile with a backpack in range is a pack animal.
    Returns the Mobile, or None if none found.
    """
    global mount_serial

    filter = Mobiles.Filter()
    filter.RangeMax   = 5
    filter.IsHuman    = False
    nearby = Mobiles.ApplyFilter(filter)
    for mob in nearby:
        if mob.Serial == Player.Serial:
            continue
        if mob.Backpack is not None:
            mount_serial = mob.Serial
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
        Target.Cancel()
        Target.ClearQueue()
        Misc.Pause(250)      # let cancel propagate before sending a new use-item packet
        Items.UseItem(tool)
        if not Target.WaitForTarget(3000, False):
            log("Target cursor never appeared – treating as cant_mine.", 0x3B)
            Target.Cancel()  # clean up if cursor arrived late
            return False
        Target.TargetExecute(tx, ty, tz, tile_id)
        Misc.Pause(cfg.pause_after_mine)
        return not Journal.Search("cannot be seen")

    # ── Use cached tile info if available ─────────────────────────────────────
    if (dx, dy) in _tile_cache:
        tz, tile_id = _tile_cache[(dx, dy)]
        if not _swing(tz, tile_id):
            del _tile_cache[(dx, dy)]   # cached tile no longer valid — clear it
            return "cant_mine"
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
    if any(Journal.Search(p) for p in JOURNAL_NO_ORE):
        return "no_ore"
    for phrase in JOURNAL_CANT_MINE:
        if Journal.Search(phrase):
            log("Journal matched cant_mine phrase: '%s'" % phrase, 0x3B)
            return "cant_mine"
    if Journal.Search(JOURNAL_PACK_FULL):
        return "pack_full"
    return "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Travel helpers
# ─────────────────────────────────────────────────────────────────────────────

MOONGATE_ID = 0x0F6C


def _wait_for_mana_drop(mana_before, timeout_ms=3000):
    """Return True if Player.Mana drops below mana_before within timeout_ms."""
    Timer.Create("mana_drop", timeout_ms)
    while Timer.Check("mana_drop"):
        if Player.Mana < mana_before:
            return True
        Misc.Pause(50)
    return False


def _find_or_prompt_runebook():
    """Return a runebook from the player's backpack, prompting if not found."""
    rb = Items.FindByID(RUNEBOOK_ITEM_ID, -1, Player.Backpack.Serial)
    if rb is not None:
        return rb
    log("No runebook in backpack – target it now...", 0x25)
    rb_serial = Target.PromptTarget("Target the runebook:")
    rb = Items.FindBySerial(rb_serial)
    if rb is None or rb.ItemID != RUNEBOOK_ITEM_ID:
        log("That is not a runebook.", 0x25)
        return None
    return rb


def travel_via_gate(runebook, slot=None):
    """
    Travel via Gate Travel.
    slot=None  – cast spell and target the runebook directly (uses its default rune).
    slot=int   – open the runebook gump and click the Gate button for that slot
                 (button ID = GATE_BUTTON_BASE + slot, confirmed via util_runebook_explorer).
    Returns True if the gate was found and stepped through.
    """
    mana_before = Player.Mana
    Journal.Clear()

    if slot is None:
        Spells.CastMagery("Gate Travel")
        if not Target.WaitForTarget(4000, False):
            log("Gate Travel: target cursor never appeared.", 0x25)
            return False
        Target.TargetExecute(runebook.Serial)
    else:
        Items.UseItem(runebook)
        Misc.Pause(500)
        if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
            log("Gate Travel: runebook gump did not open.", 0x25)
            return False
        Gumps.SendAction(RUNEBOOK_GUMP_ID, GATE_BUTTON_BASE + slot)

    if not _wait_for_mana_drop(mana_before):
        log("Gate Travel: mana did not drop – fizzled or missing reagents.", 0x25)
        return False

    gate = None
    Timer.Create("gate_find", 5000)
    while Timer.Check("gate_find"):
        gate = Items.FindByID(MOONGATE_ID, -1, -1, 3)
        if gate is not None:
            break
        Misc.Pause(200)

    if gate is None:
        log("Gate opened but no moongate found nearby.", 0x25)
        return False

    log("Stepping through gate (0x%X)..." % gate.Serial)
    Items.UseItem(gate)
    Misc.Pause(GATE_TRAVEL_DELAY)
    return True


def travel_via_recall(runebook, slot=None):
    """
    Travel via Recall spell.
    Targets the runebook directly (uses its default rune).
    Slot-specific recall button IDs are not yet confirmed — run util_runebook_explorer.py
    to find them, then implement slot support here.
    """
    if slot is not None:
        log("Slot-specific recall not yet confirmed – using default rune.", 0x3B)
    mana_before = Player.Mana
    Journal.Clear()
    Spells.CastMagery("Recall")
    if not Target.WaitForTarget(4000, False):
        log("Recall: target cursor never appeared.", 0x25)
        return False
    Target.TargetExecute(runebook.Serial)
    if not _wait_for_mana_drop(mana_before):
        log("Recall: mana did not drop – fizzled.", 0x25)
        return False
    Misc.Pause(RECALL_TRAVEL_DELAY)
    log("Recall complete.")
    return True


def travel_to(runebook, slot=None):
    """Dispatch to gate or recall based on cfg.travel_method."""
    if cfg.travel_method == 'recall':
        return travel_via_recall(runebook, slot)
    return travel_via_gate(runebook, slot)


# ─────────────────────────────────────────────────────────────────────────────
# Banking
# ─────────────────────────────────────────────────────────────────────────────

def _deposit_stacks(source_serial, item_ids, dest, label):
    """Move every matching stack from source_serial into dest. Returns total amount."""
    total = 0
    for iid in item_ids:
        stack = Items.FindByID(iid, -1, source_serial)
        while stack is not None:
            total += stack.Amount
            Items.Move(stack, dest, stack.Amount)
            Misc.Pause(cfg.pause_after_transfer)
            stack = Items.FindByID(iid, -1, source_serial)
    if total:
        log("Deposited %d %s." % (total, label))
    return total

## Needs support for rune named bank.
def bank_ingots():
    """
    Full bank-run sequence:
      1. Gate to bank.
      2. Deposit backpack ingots.
      3. Unload pack beetle (ore + ingots) if present.
      4. Smelt remaining backpack ore at bank (fire beetle or forge).
      5. Deposit freshly smelted ingots and any leftover ore.
      6. Gate back to mine.
    Returns True if mining can resume, False if no mine rune configured or travel failed.
    """
    pack, fire = find_beetles()

    runebook = _find_or_prompt_runebook()
    if runebook is None:
        return False

    # ── Gate to bank ──────────────────────────────────────────────────────────
    _remount_if_needed()
    log("Traveling to bank (slot %s)..." % str(cfg.bank_rune_slot))
    if not travel_to(runebook, cfg.bank_rune_slot):
        log("Failed to travel to bank – aborting.", 0x25)
        return False

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
        return False

    Misc.Pause(500)

    dest = Items.FindBySerial(_config.quick_dropbox)
    if dest is None:
        log("House container (0x%X) not found – cannot deposit." % _config.quick_dropbox, 0x25)
        return False

    # ── Craft pickaxe if needed (while ingots are still in backpack) ─────────
    if get_tool() is None:
        log("No mining tool — attempting to craft pickaxe before depositing ingots.")
        try_craft_pickaxe()

    # ── Deposit backpack ingots ───────────────────────────────────────────────
    _deposit_stacks(Player.Backpack.Serial, INGOT_IDS, dest, "ingots")

    # ── Unload pack beetle ────────────────────────────────────────────────────
    if pack is not None:
        was_mounted = Player.Mount is not None
        if was_mounted:
            Mobiles.UseMobile(Player.Serial)
            Misc.Pause(1500)

        beetle = Mobiles.FindBySerial(pack.Serial)
        if beetle is not None and beetle.Backpack is not None:
            _deposit_stacks(beetle.Backpack.Serial, ORE_IDS,   dest, "ore from beetle")
            _deposit_stacks(beetle.Backpack.Serial, INGOT_IDS, dest, "ingots from beetle")
        else:
            log("Could not access pack beetle at home.", 0x25)

        if was_mounted:
            Mobiles.UseMobile(pack.Serial)
            Misc.Pause(1500)

    # ── Smelt remaining backpack ore ──────────────────────────────────────────
    # Fire beetle travels with the player so it works at home.
    # smelt_from_backpack() targets forge_serial (the mine forge) which is out of
    # range at home and would silently fail — skip it without a fire beetle.
    if fire is not None:
        log("Smelting backpack ore with fire beetle...")
        smelt_with_fire_beetle(fire)

    # ── Deposit smelted ingots and leftover ore ───────────────────────────────
    _deposit_stacks(Player.Backpack.Serial, INGOT_IDS, dest, "ingots after smelt")
    _deposit_stacks(Player.Backpack.Serial, ORE_IDS,   dest, "remaining ore")

    # ── Return to mine ────────────────────────────────────────────────────────
    if cfg.mine_rune_slot is None:
        log("No mine rune configured – stopping at bank.", 0x3B)
        return False

    _remount_if_needed()
    log("Returning to mine (slot %d)..." % cfg.mine_rune_slot)
    if not travel_to(runebook, cfg.mine_rune_slot):
        log("Failed to return to mine – stopping.", 0x25)
        return False

    log("Back at mine – resuming.", 0x3F)
    return True


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
    global mount_serial, forge_serial, pack_beetle_serial, fire_beetle_serial

    num_dirs     = len(cfg.mining_directions)
    dir_index    = 0
    consec_fails = 0
    silent_count = 0   # consecutive swings with no journal response

    if Player.Mount is not None:
        log("Mounted – dismounting before mining.", 0x3B)
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)

    _tile_cache.clear()
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
            if not bank_ingots():
                log("Bank complete – stopping.", 0x026C)
                break
            log("Bank complete – resuming mining.", 0x3F)
            Journal.Clear()

        # ── Weight threshold check ────────────────────────────────────────────
        if not smelting_in_progress and Player.Weight >= Player.MaxWeight - cfg.weight_headroom:
            log("Weight %d / %d – acting on beetle type."
                % (Player.Weight, Player.MaxWeight), 0x25)
            if pack_beetle_serial:
                _push_result = push_ore_to_inventory()
                if _push_result == 'full':
                    log("Pack animal full – going home to smelt.", 0x25)
                    _home_deposit()
                    break
                elif _push_result == 'none':
                    log("Pack animal not reachable – clearing serial.", 0x25)
                    pack_beetle_serial = None
            if not handle_overweight():
                log("Still overweight after smelt/transfer – attempting bank run.", 0x25)
                if not bank_ingots():
                    log("Bank run complete – stopping.", 0x026C)
                    break
                log("Returned from bank – resuming mining.", 0x3F)
                Journal.Clear()

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
            if try_craft_pickaxe():
                continue
            log("Craft failed – trying pickaxe box at home.", 0x25)
            grab_pickaxe_from_box()  # goes home, deposits, grabs pickaxe if available
            break  # player is now at home; restart script to resume

        # ── Evaluate journal ──────────────────────────────────────────────────
        status = read_journal_status()
        log("Journal status: %s" % status, 0x3B)

        if status in ("no_ore", "cant_mine"):
            if status == "no_ore":
                Player.HeadMessage(0x25, "No metal – moving on")
            consec_fails += 1
            silent_count  = 0
            dir_index     = (dir_index + 1) % num_dirs
            dx2, dy2      = cfg.mining_directions[dir_index]
            log("Spot unmineable (%s). Rotating to direction %d / %d  (dx=%+d, dy=%+d)."
                % (status, dir_index + 1, num_dirs, dx2, dy2), 0x25)
            if consec_fails >= num_dirs:
                log("All %d directions exhausted – waiting for player to move." % num_dirs, 0x25)
                consec_fails = 0
                dir_index    = 0

        elif status == "pack_full":
            if smelting_in_progress:
                pass  # already smelting – ignore pack_full signal mid-smelt
            else:
                log("Backpack full – acting on beetle type.", 0x25)
                if not handle_overweight():
                    log("Still overweight after action – stopping.", 0x25)
                    break
            consec_fails = 0

        else:
            if any(Journal.Search(p) for p in JOURNAL_ORE_SUCCESS):
                consec_fails = 0
                silent_count = 0
            else:
                silent_count += 1
                log("Silent swing %d/%d – no journal response." % (silent_count, cfg.max_silent_ok), 0x3B)
                if silent_count >= cfg.max_silent_ok:
                    log("Rotating after %d silent swings." % silent_count, 0x25)
                    _tile_cache.pop((dx, dy), None)
                    consec_fails += 1
                    dir_index    = (dir_index + 1) % num_dirs
                    silent_count = 0
                else:
                    consec_fails = 0

        Misc.Pause(cfg.loop_delay)


import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import config as _config
from glossary.runebook_handler import (
    find_runebook_by_label, find_runes_matching, travel_to_slot, travel_to_runebook
)


# ─────────────────────────────────────────────────────────────────────────────
# Mode selection
# ─────────────────────────────────────────────────────────────────────────────

def select_mode():
    """Show a 10-second prompt. Player types '1' for auto, timeout = manual."""
    log("Type '1' in chat for auto mode. Manual mode starts in 10 seconds...", 0x0481)
    log("Type '2' in chat for Manual Mode. Manual mode starts in 10 seconds...", 0x0481)
    Player.HeadMessage(0x0481, "1 = Auto  |  Manual in 10s")
    Journal.Clear()
    Timer.Create("mode_select", 10000)
    while Timer.Check("mode_select"):
        if Journal.SearchByType("1", "Regular"):
            Journal.Clear()
            log("Auto mode.", 0x0481)
            return 'auto'
        if Journal.SearchByType("2", "Regular"):
            Journal.Clear()
            log("Manual mode.", 0x0481)
            return 'manual'
        Misc.Pause(200)
    log("Manual mode.", 0x0481)
    return 'manual'


# ─────────────────────────────────────────────────────────────────────────────
# Auto mode helpers
# ─────────────────────────────────────────────────────────────────────────────

def _find_mining_runebook():
    """Return (runebook, spots) so the gump is only opened once."""
    if cfg.auto_mining_runebook is not None:
        rb = find_runebook_by_label(cfg.auto_mining_runebook)
        if rb is None:
            log("No runebook labeled '%s' found in backpack." % cfg.auto_mining_runebook, 0x25)
            return None, []
        spots = find_runes_matching(rb, cfg.auto_mining_rune_filter)
        if not spots:
            log("Runebook '%s' found but no runes match filter '%s'." % (cfg.auto_mining_runebook, cfg.auto_mining_rune_filter), 0x25)
            return None, []
        return rb, spots
    for item in Player.Backpack.Contains:
        if item.ItemID == RUNEBOOK_ITEM_ID:
            spots = find_runes_matching(item, cfg.auto_mining_rune_filter)
            if spots:
                log("Mining runebook: %s (0x%X), %d spot(s)." % (item.Name, item.Serial, len(spots)))
                return item, spots
    log("No runebook with '%s' runes found in backpack." % cfg.auto_mining_rune_filter, 0x25)
    return None, []


def auto_mine_spot(home_rb):
    """
    Mine all 8 directions at the current location until exhausted.
    Gates home via home_rb if overweight, returning False so the caller knows
    the player relocated. Returns True when the spot is normally exhausted.
    """
    global pack_beetle_serial, fire_beetle_serial
    if Player.Mount is not None:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)

    _tile_cache.clear()
    pos = Player.Position
    log("Auto-mining at (%d, %d)." % (pos.X, pos.Y))
    Journal.Clear()

    num_dirs     = len(cfg.mining_directions)
    dir_index    = 0
    consec_fails = 0
    silent_count = 0

    while consec_fails < num_dirs:
        if Player.Weight >= Player.MaxWeight - cfg.weight_headroom:
            log("Overweight – acting on beetle type.", 0x25)
            if pack_beetle_serial is None and fire_beetle_serial is None:
                find_beetles()
            if pack_beetle_serial:
                _push_result = push_ore_to_inventory()
                if _push_result == 'full':
                    log("Pack animal full – going home to smelt.", 0x25)
                    _home_deposit()
                    return False
                elif _push_result == 'none':
                    log("Pack animal not reachable – clearing serial.", 0x25)
                    pack_beetle_serial = None
            if not handle_overweight():
                log("Still overweight after smelt – running bank run.", 0x25)
                returned = bank_ingots()
                if not returned:
                    _remount_if_needed()
                    travel_to_runebook(home_rb, 2000)
                    return False
                # bank_ingots returned us to the mine rune — resume this spot
                Journal.Clear()

        dx, dy = cfg.mining_directions[dir_index]
        result  = mine_at(dx, dy)
        if result == 'no_tool':
            if try_craft_pickaxe():
                continue
            log("Craft failed – going home for pickaxes.", 0x25)
            if not grab_pickaxe_from_box():
                log("No pickaxes available — stopping.", 0x25)
                return None   # sentinel: stop run_auto_mode entirely
            return False  # got pickaxes — run_auto_mode will re-navigate

        status = read_journal_status()
        log("Journal status: %s" % status, 0x3B)
        if status == 'no_ore':
            log("No metal at this spot – moving to next rune.", 0x25)
            return True
        elif status == 'cant_mine':
            consec_fails += 1
            silent_count  = 0
            dir_index = (dir_index + 1) % num_dirs
            log("Direction blocked – trying %d/%d." % (dir_index + 1, num_dirs), 0x25)
        elif status == 'pack_full':
            log("Pack full — gating home.", 0x25)
            _remount_if_needed()
            travel_to_runebook(home_rb, 2000)
            return False
        else:
            if any(Journal.Search(p) for p in JOURNAL_ORE_SUCCESS):
                consec_fails = 0
                silent_count = 0
            else:
                silent_count += 1
                log("Silent swing %d/%d." % (silent_count, cfg.max_silent_ok), 0x3B)
                if silent_count >= cfg.max_silent_ok:
                    log("Rotating after silent swings.", 0x25)
                    _tile_cache.pop((dx, dy), None)
                    consec_fails += 1
                    dir_index    = (dir_index + 1) % num_dirs
                    silent_count = 0

        Misc.Pause(cfg.loop_delay)

    log("Spot exhausted – all directions blocked.")
    return True


def run_auto_mode():
    while True:
        mining_rb, spots = _find_mining_runebook()
        if mining_rb is None:
            return

        home_rb = find_runebook_by_label(cfg.auto_home_runebook)
        if home_rb is None:
            log("No runebook labeled '%s' in backpack." % cfg.auto_home_runebook, 0x25)
            return

        log("%d mining spot(s) found. Starting cycle..." % len(spots), 0x0481)

        for slot, name in spots:
            _remount_if_needed()
            if _count_tools() == 0:
                log("No pickaxes — stopping.", 0x25)
                return
            log("Traveling to %s (slot %d)..." % (name, slot))
            if not travel_to_slot(mining_rb, slot, 2000):
                log("Travel failed — skipping %s." % name, 0x25)
                continue

            result = auto_mine_spot(home_rb)
            if result is None:
                return   # no pickaxes — stop entirely

            # After each spot, check if the beetle has ore OR the drop box has ore to smelt.
            # Do this whether the spot finished normally (True) or we already went home (False).
            beetle_has_ore = False
            if pack_beetle_serial is not None:
                mob = Mobiles.FindBySerial(pack_beetle_serial)
                if mob is not None and mob.Backpack is not None:
                    beetle_has_ore = any(
                        Items.FindByID(oid, -1, mob.Backpack.Serial) is not None
                        for oid in ORE_IDS
                    )

            if beetle_has_ore or Player.Weight >= Player.MaxWeight - cfg.weight_headroom:
                log("Offloading beetle and smelting drop box before next spot.", 0x026C)
                _home_deposit()
                mining_rb, spots = _find_mining_runebook()
                home_rb = find_runebook_by_label(cfg.auto_home_runebook)
                if mining_rb is None or home_rb is None:
                    log("Lost runebooks after gating home — stopping.", 0x25)
                    return
            elif not result:
                # Went home mid-cycle for another reason — re-acquire runebooks
                mining_rb, spots = _find_mining_runebook()
                home_rb = find_runebook_by_label(cfg.auto_home_runebook)
                if mining_rb is None or home_rb is None:
                    log("Lost runebooks after gating home — stopping.", 0x25)
                    return

        log("=== Cycle complete — heading home and repeating ===", 0x026C)
        finish()


# ─────────────────────────────────────────────────────────────────────────────
# Exit sequence
# ─────────────────────────────────────────────────────────────────────────────

def _home_deposit():
    """
    Ensure player is home, dump everything to the drop box, smelt all ore in the box,
    deposit resulting ingots, then top up pickaxes to 4.
    Skips travel if the drop box is already in range (player is already home).
    Returns True if home was reached (deposit attempted regardless of container availability).
    """
    global forge_serial

    # ── Travel home only if drop box is out of range ──────────────────────────
    dest = Items.FindBySerial(_config.quick_dropbox)
    if dest is None:
        home_rb = find_runebook_by_label(cfg.auto_home_runebook)
        if home_rb is None:
            log("No home runebook – cannot go home.", 0x25)
            return False
        _remount_if_needed()
        log("Heading home...", 0x026C)
        if not travel_to_runebook(home_rb, RECALL_TRAVEL_DELAY):
            log("Could not travel home.", 0x25)
            return False
        for _ in range(2):
            Player.Walk('Right')
            Misc.Pause(400)
        for _ in range(2):
            Player.Walk('Up')
            Misc.Pause(400)
        dest = Items.FindBySerial(_config.quick_dropbox)

    if Player.Mount is not None:
        Mobiles.UseMobile(Player.Serial)
        Misc.Pause(1500)
    pack, fire = find_beetles()

    if dest is None:
        log("Drop container (0x%X) not found." % _config.quick_dropbox, 0x25)
    else:
        # ── Step 1: player ore + ingots → drop box ────────────────────────────
        _deposit_stacks(Player.Backpack.Serial, ORE_IDS,   dest, "ore")
        _deposit_stacks(Player.Backpack.Serial, INGOT_IDS, dest, "ingots")

        # ── Step 2: beetle ore + ingots → drop box ────────────────────────────
        if pack is not None and pack.Backpack is not None:
            Items.UseItem(pack.Backpack)
            Items.WaitForContents(pack.Backpack, 3000)
            Misc.Pause(1200)
            _deposit_stacks(pack.Backpack.Serial, ORE_IDS,   dest, "ore from beetle")
            _deposit_stacks(pack.Backpack.Serial, INGOT_IDS, dest, "ingots from beetle")

        # ── Step 3: smelt all ore in drop box ─────────────────────────────────
        smelt_forge = None
        if fire is not None:
            smelt_forge = fire.Serial
        if smelt_forge is None and cfg.home_forge_serial is not None:
            smelt_forge = cfg.home_forge_serial
        if smelt_forge is None:
            smelt_forge = find_forge_nearby(search_range=10)

        if smelt_forge is not None:
            prev_forge   = forge_serial
            forge_serial = smelt_forge
            Items.UseItem(dest)
            Items.WaitForContents(dest, 3000)
            Misc.Pause(1200)
            total_smelted = smelt_from_backpack(dest.Serial)
            forge_serial = prev_forge
            if total_smelted:
                log("Smelted %d stack(s) from drop box." % total_smelted)
            # ── Step 4: deposit ingots produced by smelt ──────────────────────
            _deposit_stacks(Player.Backpack.Serial, INGOT_IDS, dest, "ingots (post-smelt)")
        else:
            log("No forge available — ore left in drop box for manual smelt.", 0x3B)

    # ── Step 5: top up pickaxes to 4 ─────────────────────────────────────────
    need = max(0, 4 - _count_tools())
    if need > 0 and cfg.pickaxe_box_serial is not None:
        log("Topping up pickaxes (%d needed)..." % need, 0x3B)
        _grab_pickaxes_from_box(need)

    return True


def _count_tools():
    """Count total mining tools in the player's backpack."""
    count = 0
    for tid in MINING_TOOL_IDS:
        count += Items.ContainerCount(Player.Backpack.Serial, tid, -1)
    return count


def _grab_pickaxes_from_box(needed):
    """
    Open cfg.pickaxe_box_serial and pull up to `needed` pickaxes into the backpack.
    Assumes the player is already at home and the box is in range.
    Returns the number grabbed, or -1 if the box could not be found.
    """
    if cfg.pickaxe_box_serial is None:
        log("No pickaxe box serial configured (cfg.pickaxe_box_serial).", 0x25)
        return -1
    if Gumps.HasGump():
        Misc.Pause(1200)
    box = Items.FindBySerial(cfg.pickaxe_box_serial)
    if box is None:
        Misc.Pause(1000)
        box = Items.FindBySerial(cfg.pickaxe_box_serial)
    if box is None:
        log("Pickaxe box (0x%X) not found." % cfg.pickaxe_box_serial, 0x25)
        return -1
    Items.UseItem(box.Serial)
    Items.WaitForContents(box, 3000)
    Misc.Pause(600)
    grabbed = 0
    for tid in MINING_TOOL_IDS:
        if grabbed >= needed:
            break
        tool = Items.FindByID(tid, -1, box.Serial)
        while tool is not None and grabbed < needed:
            take = min(tool.Amount, needed - grabbed)
            Items.Move(tool, Player.Backpack, take)
            Misc.Pause(cfg.pause_after_transfer)
            grabbed += take
            tool = Items.FindByID(tid, -1, box.Serial)
    if grabbed:
        log("Grabbed %d pickaxe(s) from box." % grabbed)
    else:
        log("No pickaxes in box (0x%X)." % cfg.pickaxe_box_serial, 0x25)
    return grabbed


def grab_pickaxe_from_box():
    """
    Travel home, deposit, smelt, and top up pickaxes via _home_deposit().
    Returns True if the player now has at least one pickaxe.
    """
    if cfg.pickaxe_box_serial is None:
        log("No pickaxe box serial configured (cfg.pickaxe_box_serial).", 0x25)
        return False
    if not _home_deposit():
        return False
    return _count_tools() > 0


def finish():
    """Gate home, smelt, deposit all ingots and ore."""
    if _home_deposit():
        log("Done.", 0x026C)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log("=== Mining Script ===", 0x0481)
    mode = select_mode()

    if mode == 'manual':
        pack, _ = find_beetles()
        player_has_ore = any(Items.FindByID(oid, -1, Player.Backpack.Serial) is not None for oid in ORE_IDS)
        needs_deposit  = player_has_ore or Player.Weight >= Player.MaxWeight - cfg.weight_headroom
        if not needs_deposit and pack is not None and pack.Backpack is not None:
            Items.UseItem(pack.Backpack)
            Items.WaitForContents(pack.Backpack, 3000)
            Misc.Pause(1200)
            if any(Items.FindByID(oid, -1, pack.Backpack.Serial) is not None for oid in ORE_IDS):
                needs_deposit = True
        if needs_deposit:
            log("Starting with ore or overweight – depositing before mining.", 0x3B)
            _home_deposit()
        run_mining_loop()
    else:
        # Auto mode: always home-deposit first (location check + deposit + smelt + pickaxes).
        log("Heading home to deposit and prepare...", 0x026C)
        _home_deposit()
        run_auto_mode()


main()


    