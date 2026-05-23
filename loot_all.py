# loot_all.py
# Loot magical items from all nearby corpses and transfer them to a pack beetle.
#
# Flow:
#   1. Auto-detect a nearby follower with a backpack; fall back to target prompt.
#   2. Find all corpses within CORPSE_RANGE tiles, sorted nearest-first.
#   3. For each corpse: open it, enumerate contents.
#   4. Fetch properties for each item and check for magic quality tier keywords.
#   5. Move every magical item (and gems) to the beetle's backpack.

# IDE IntelliSense support – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

# ─── Magic quality tier strings ───────────────────────────────────────────────
# These are the tooltip property lines UO uses to mark an item's magic intensity.
# All comparisons are case-insensitive substring checks.
MAGIC_QUALITY_KEYWORDS = [
    "lesser magic item",
    "magic item",           # also matches "lesser/greater/major magic item"
    "greater magic item",
    "major magic item",
    "legendary magic item",
    "minor artifact",
    "major artifact",
    "legendary artifact",
    "artifact",             # catches any remaining artifact label
]

# ─── Gem item IDs (from glossary/items/gems.py) ──────────────────────────────
GEM_IDS = {
    0x0F25,  # amber
    0x0F16,  # amethyst
    0x0F15,  # citrine
    0x0F26,  # diamond
    0x0F10,  # emerald
    0x0F13,  # rubies
    0x0F11,  # sapphire          (confirmed in-game: 0x0F11)
    0x0F0F,  # star sapphire     (confirmed in-game: 0x0F0F)
    0x0F18,  # tourmaline        (confirmed in-game: 0x0F18)
}

# ─── Delays ───────────────────────────────────────────────────────────────────
CORPSE_RANGE          = 2     # tiles – how far to scan for corpses
PAUSE_OPEN_CONTAINER  = 1200   # ms – after UseItem on a container before reading .Contains
PAUSE_BETWEEN_MOVES   = 1000   # ms – between Items.Move calls (safe per API notes)
PAUSE_AFTER_SINGLECLICK = 800  # ms – after SingleClick before WaitForProps


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[loot_all] " + msg, color)


def is_magical(item):
    """
    Return True if the item's tooltip contains a recognised magic quality string.
    The corpse must already be open before calling this.
    """
    Items.SingleClick(item)
    Misc.Pause(PAUSE_AFTER_SINGLECLICK)
    Items.WaitForProps(item, 5000)
    props = Items.GetPropStringList(item.Serial)
    if not props:
        return False
    for line in props:
        lower = line.lower()
        for keyword in MAGIC_QUALITY_KEYWORDS:
            if keyword in lower:
                return True
    return False


def find_pack_animal():
    """
    Auto-detect a nearby follower with a backpack (i.e. a pack beetle).
    Returns the Mobile, or None if none found.
    """
    f = Mobiles.Filter()
    f.Enabled  = True
    f.RangeMax = 10
    f.IsHuman  = False
    f.Friend   = True   # followers / pets only
    nearby = Mobiles.ApplyFilter(f)
    for mob in nearby:
        if mob.Serial == Player.Serial:
            continue
        if mob.Backpack is not None:
            return mob
    return None


def find_all_corpses():
    """Return all corpses on the ground within CORPSE_RANGE tiles, sorted nearest-first."""
    f = Items.Filter()
    f.Enabled  = True
    f.OnGround = True
    f.Movable  = False
    f.RangeMax = CORPSE_RANGE
    f.IsCorpse = True
    corpses = Items.ApplyFilter(f)
    if not corpses:
        return []
    return sorted(corpses, key=lambda c: Player.DistanceTo(c))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    # ── Step 1: find the beetle (auto-detect, then prompt as fallback) ────────
    beetle = find_pack_animal()
    if beetle is not None:
        log("Pack beetle auto-detected: %s (0x%X)" % (beetle.Name, beetle.Serial))
    else:
        log("No follower with backpack nearby – target your pack beetle.")
        beetle_serial = Target.PromptTarget("Target your pack beetle")

        if beetle_serial == 0:
            log("Cancelled.", 0x25)
            return
        if beetle_serial == Player.Serial:
            log("You targeted yourself – cancelled.", 0x25)
            return

        beetle = Mobiles.FindBySerial(beetle_serial)
        if beetle is None:
            log("Could not find that mobile.", 0x25)
            return
        if beetle.Backpack is None:
            log("%s has no backpack – is it a pack beetle?" % beetle.Name, 0x25)
            return

        log("Beetle: %s (0x%X)" % (beetle.Name, beetle.Serial))

    # ── Step 2: find all corpses ──────────────────────────────────────────────
    corpses = find_all_corpses()
    if not corpses:
        log("No corpses found within %i tiles." % CORPSE_RANGE, 0x25)
        return

    log("Found %i corpse(s) – looting..." % len(corpses))
    total_moved = 0

    for corpse_idx, corpse in enumerate(corpses):
        log("[%i/%i] Corpse at X=%i Y=%i Z=%i" % (
            corpse_idx + 1, len(corpses),
            corpse.Position.X, corpse.Position.Y, corpse.Position.Z))

        # ── Step 3: open corpse and read contents ─────────────────────────────
        Items.UseItem(corpse)
        Items.WaitForContents(corpse, 3000)
        Misc.Pause(PAUSE_OPEN_CONTAINER)

        contents = corpse.Contains
        if not contents:
            log("  (empty)")
            continue

        log("  %i item(s) – checking for magic..." % len(contents))

        # Snapshot the list; items disappear from .Contains as they are moved.
        item_list = list(contents)

        # ── Steps 4 & 5: check each item and loot magical or gem items ────────
        moved = 0
        for item in item_list:
            if item.ItemID in GEM_IDS:
                log("    LOOT (gem)   %s (0x%04X)" % (item.Name, item.ItemID), 0x48)
                Items.Move(item, beetle.Backpack, item.Amount)
                Misc.Pause(PAUSE_BETWEEN_MOVES)
                moved += 1
            elif is_magical(item):
                log("    LOOT (magic) %s (0x%04X)" % (item.Name, item.ItemID), 88)
                Items.Move(item, beetle.Backpack, item.Amount)
                Misc.Pause(PAUSE_BETWEEN_MOVES)
                moved += 1
            else:
                log("    skip  %s (0x%04X)" % (item.Name, item.ItemID), 0x3F)

        log("  %i item(s) moved from this corpse." % moved)
        total_moved += moved

    log("Done – %i total item(s) moved to %s." % (total_moved, beetle.Name))


main()
