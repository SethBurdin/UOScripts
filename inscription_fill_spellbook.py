# ─────────────────────────────────────────────────────────────────────────────
# inscription_fill_spellbook.py
# ─────────────────────────────────────────────────────────────────────────────
# Automates filling a spellbook or container with inscribed scrolls.
#
# Features:
#   - Prompts the player to target a destination (spellbook or container).
#   - Scans the destination to determine which scrolls are already present.
#   - Optionally pulls blank scrolls and reagents from a configured source chest.
#   - Navigates the inscription crafting gump to craft each missing scroll.
#   - Meditates automatically when mana drops below the configured threshold.
#   - Moves each completed scroll into the destination as it is created.
#   - Supports Magery (all 8 circles, 64 spells) and a Spellweaving stub.
#
# Config: edit the `cfg` class near the top of this file.
#
# Gump NOTE:
#   Uses the standard RunUO/ServUO crafting gump (ID 949095101).
#   Circles are treated as top-level categories.  Button layout:
#     Left  panel  (circles): 1, 8, 15, 22, 29, 36, 43, 50
#     Right panel  (spells):  2, 9, 16, 23, 30, 37, 44, 51
#   Adjust CIRCLE_BTNS / SPELL_BTN_FIRST / SPELL_BTN_STEP if your shard
#   uses a different layout.
# ─────────────────────────────────────────────────────────────────────────────

# IDE IntelliSense only – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
class cfg:
    # Crafting skill mode: "magery"  |  "spellweaving"
    mode = "magery"

    # ---- Timing (milliseconds) ----
    craft_delay       = 2000   # wait after clicking a spell button to craft
    gump_open_delay   = 1500   # timeout while waiting for the crafting gump
    item_move_delay   = 700    # pause between Items.Move calls
    meditate_poll_ms  = 500    # polling interval while waiting for mana
    circle_switch_ms  = 500    # pause after clicking a circle (category) button

    # ---- Mana management ----
    meditate_threshold = 40     # meditate when mana falls below this value
    mana_wait_timeout  = 90000  # max ms to wait for full mana (90 s)

    # ---- Source container for materials (optional) ----
    # Set to the integer serial of a chest / bag that holds blank scrolls
    # and reagents.  Set to None to skip the material-pull step.
    material_source_serial = None

    # ---- Spell filter (optional) ----
    # Restrict crafting to a specific subset of spells.
    # Example: spell_filter = ["Heal", "Cure", "Mark", "Recall"]
    # Set to None to craft all spells for the chosen mode.
    spell_filter = None


# ─────────────────────────────────────────────────────────────────────────────
# Item IDs
# ─────────────────────────────────────────────────────────────────────────────

# Scribe's pen (inscription tool).  0x0FBF is standard; some shards use 0x0FBE.
SCRIBE_PEN_IDS  = [0x0FBF, 0x0FBE]

# Spellbook graphic – used to distinguish a spellbook from a generic container.
SPELLBOOK_IDS   = [0x0EFA]

# Blank scroll – one required per inscription attempt.
BLANK_SCROLL_ID = 0x0E34

# ─── Reagent item IDs ────────────────────────────────────────────────────────
# Abbreviated keys match the standard UO reagent names.
REAGENT = {
    'BP': 0x0F7A,   # Black Pearl
    'BM': 0x0F7B,   # Blood Moss
    'GA': 0x0F84,   # Garlic
    'GI': 0x0F85,   # Ginseng
    'MR': 0x0F86,   # Mandrake Root
    'NS': 0x0F88,   # Nightshade
    'SS': 0x0F8D,   # Spider's Silk
    'SA': 0x0F8C,   # Sulfurous Ash
}


# ─────────────────────────────────────────────────────────────────────────────
# Crafting gump navigation constants
# ─────────────────────────────────────────────────────────────────────────────
CRAFT_GUMP_ID = 949095101   # Shared by all RE crafting skills (RunUO/ServUO)

# Circle category buttons (left panel).  Pattern: 1 + (circle - 1) * 7.
CIRCLE_BTNS = {1: 1, 2: 8, 3: 15, 4: 22, 5: 29, 6: 36, 7: 43, 8: 50}

# Spell item buttons on the right panel.  Pattern: 2 + slot * 7.
SPELL_BTN_FIRST = 2
SPELL_BTN_STEP  = 7

# Button 0 = Exit the crafting gump.
GUMP_BTN_EXIT = 0


# ─────────────────────────────────────────────────────────────────────────────
# Magery scroll data
# ─────────────────────────────────────────────────────────────────────────────
# Each entry: (spell_name, circle, scroll_item_id, [reagent_item_ids])
# Order within each circle matches the gump slot order (slot 0–7).
# Reagent lists follow standard UO spell requirements.
MAGERY_SCROLLS = [
    # ── Circle 1 ──────────────────────────────────────────────────────────────
    ("Clumsy",           1, 0x1F2E, [REAGENT['BM'], REAGENT['NS']]),
    ("Create Food",      1, 0x1F2F, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR']]),
    ("Feeblemind",       1, 0x1F30, [REAGENT['GI'], REAGENT['NS']]),
    ("Heal",             1, 0x1F31, [REAGENT['GA'], REAGENT['GI'], REAGENT['SS']]),
    ("Magic Arrow",      1, 0x1F32, [REAGENT['SA']]),
    ("Night Sight",      1, 0x1F33, [REAGENT['SS'], REAGENT['SA']]),
    ("Reactive Armor",   1, 0x1F2D, [REAGENT['GA'], REAGENT['SS'], REAGENT['SA']]),
    ("Weaken",           1, 0x1F34, [REAGENT['GA'], REAGENT['NS']]),

    # ── Circle 2 ──────────────────────────────────────────────────────────────
    ("Agility",          2, 0x1F35, [REAGENT['BM'], REAGENT['MR']]),
    ("Cunning",          2, 0x1F36, [REAGENT['MR'], REAGENT['NS']]),
    ("Cure",             2, 0x1F37, [REAGENT['GA'], REAGENT['GI']]),
    ("Harm",             2, 0x1F38, [REAGENT['NS'], REAGENT['SS']]),
    ("Magic Trap",       2, 0x1F39, [REAGENT['GA'], REAGENT['SS'], REAGENT['SA']]),
    ("Magic Untrap",     2, 0x1F3A, [REAGENT['BM'], REAGENT['SA']]),
    ("Protection",       2, 0x1F3B, [REAGENT['GA'], REAGENT['GI'], REAGENT['SA']]),
    ("Strength",         2, 0x1F3C, [REAGENT['MR'], REAGENT['NS']]),

    # ── Circle 3 ──────────────────────────────────────────────────────────────
    ("Bless",            3, 0x1F3D, [REAGENT['GA'], REAGENT['MR']]),
    ("Fireball",         3, 0x1F3E, [REAGENT['BP']]),
    ("Magic Lock",       3, 0x1F3F, [REAGENT['BM'], REAGENT['GA'], REAGENT['SA']]),
    ("Poison",           3, 0x1F40, [REAGENT['NS']]),
    ("Telekinesis",      3, 0x1F41, [REAGENT['BM'], REAGENT['MR']]),
    ("Teleport",         3, 0x1F42, [REAGENT['BM'], REAGENT['MR']]),
    ("Unlock",           3, 0x1F43, [REAGENT['BM'], REAGENT['SA']]),
    ("Wall of Stone",    3, 0x1F44, [REAGENT['BM'], REAGENT['GA']]),

    # ── Circle 4 ──────────────────────────────────────────────────────────────
    ("Arch Cure",        4, 0x1F45, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR']]),
    ("Arch Protection",  4, 0x1F46, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR'], REAGENT['SA']]),
    ("Curse",            4, 0x1F47, [REAGENT['GA'], REAGENT['NS'], REAGENT['SA']]),
    ("Fire Field",       4, 0x1F48, [REAGENT['BP'], REAGENT['SS'], REAGENT['SA']]),
    ("Greater Heal",     4, 0x1F49, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR'], REAGENT['SS']]),
    ("Lightning",        4, 0x1F4A, [REAGENT['MR'], REAGENT['SA']]),
    ("Mana Drain",       4, 0x1F4B, [REAGENT['BP'], REAGENT['MR'], REAGENT['SS']]),
    ("Recall",           4, 0x1F4C, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR']]),

    # ── Circle 5 ──────────────────────────────────────────────────────────────
    ("Blade Spirits",    5, 0x1F4D, [REAGENT['BP'], REAGENT['MR'], REAGENT['NS']]),
    ("Dispel Field",     5, 0x1F4E, [REAGENT['BP'], REAGENT['GA'], REAGENT['SS'], REAGENT['SA']]),
    ("Incognito",        5, 0x1F4F, [REAGENT['BM'], REAGENT['GA'], REAGENT['NS']]),
    ("Magic Reflection", 5, 0x1F50, [REAGENT['GA'], REAGENT['MR'], REAGENT['SS']]),
    ("Mind Blast",       5, 0x1F51, [REAGENT['BP'], REAGENT['MR'], REAGENT['NS'], REAGENT['SA']]),
    ("Paralyze",         5, 0x1F52, [REAGENT['GA'], REAGENT['MR'], REAGENT['SS']]),
    ("Poison Field",     5, 0x1F53, [REAGENT['BP'], REAGENT['NS'], REAGENT['SS']]),
    ("Summon Creature",  5, 0x1F54, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),

    # ── Circle 6 ──────────────────────────────────────────────────────────────
    ("Dispel",           6, 0x1F55, [REAGENT['GA'], REAGENT['MR'], REAGENT['SA']]),
    ("Energy Bolt",      6, 0x1F56, [REAGENT['BP'], REAGENT['NS']]),
    ("Explosion",        6, 0x1F57, [REAGENT['BM'], REAGENT['MR']]),
    ("Invisibility",     6, 0x1F58, [REAGENT['BM'], REAGENT['NS']]),
    ("Mark",             6, 0x1F59, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR']]),
    ("Mass Curse",       6, 0x1F5A, [REAGENT['GA'], REAGENT['MR'], REAGENT['NS'], REAGENT['SA']]),
    ("Paralyze Field",   6, 0x1F5B, [REAGENT['BP'], REAGENT['GI'], REAGENT['SS']]),
    ("Reveal",           6, 0x1F5C, [REAGENT['BM'], REAGENT['SA']]),

    # ── Circle 7 ──────────────────────────────────────────────────────────────
    ("Chain Lightning",  7, 0x1F5D, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR'], REAGENT['SA']]),
    ("Energy Field",     7, 0x1F5E, [REAGENT['BP'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
    ("Flamestrike",      7, 0x1F5F, [REAGENT['SS'], REAGENT['SA']]),
    ("Gate Travel",      7, 0x1F60, [REAGENT['BP'], REAGENT['MR'], REAGENT['SA']]),
    ("Mana Vampire",     7, 0x1F61, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
    ("Mass Dispel",      7, 0x1F62, [REAGENT['BP'], REAGENT['GA'], REAGENT['MR'], REAGENT['SA']]),
    ("Meteor Swarm",     7, 0x1F63, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
    ("Polymorph",        7, 0x1F64, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),

    # ── Circle 8 ──────────────────────────────────────────────────────────────
    ("Earthquake",             8, 0x1F65, [REAGENT['BM'], REAGENT['GI'], REAGENT['MR'], REAGENT['SA']]),
    ("Energy Vortex",          8, 0x1F66, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR'], REAGENT['NS']]),
    ("Resurrection",           8, 0x1F67, [REAGENT['BM'], REAGENT['GA'], REAGENT['GI']]),
    ("Summon Air Elemental",   8, 0x1F68, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
    ("Summon Daemon",          8, 0x1F69, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
    ("Summon Earth Elemental", 8, 0x1F6A, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
    ("Summon Fire Elemental",  8, 0x1F6B, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
    ("Summon Water Elemental", 8, 0x1F6C, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
]


# ─────────────────────────────────────────────────────────────────────────────
# Spellweaving scroll data (stub)
# ─────────────────────────────────────────────────────────────────────────────
# Spellweaving scroll IDs, reagent requirements, and gump button paths vary
# widely by shard implementation.  Populate this list following the same
# tuple schema: (spell_name, circle, scroll_item_id, [reagent_item_ids]).
# Double-check circle_button and spell_button values for your server before
# enabling cfg.mode = "spellweaving".
SPELLWEAVING_SCROLLS = []   # TODO: populate per shard


# ─────────────────────────────────────────────────────────────────────────────
# Journal result phrases
# ─────────────────────────────────────────────────────────────────────────────
CRAFT_SUCCESS_PHRASES = [
    "You create the scroll",
    "You inscribe",
    "You create the item",
]

CRAFT_FAIL_PHRASES = [
    "failed to create",
    "You don't have enough",
    "not enough",
    "insufficient",
    "You lack",
    "You do not have",
    "That item cannot",
    "no blank scrolls",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def log(msg, color=0x3F):
    Misc.SendMessage("[INSCRIBE] %s" % msg, color)


def journal_contains_any(phrases):
    for phrase in phrases:
        if Journal.Search(phrase):
            return True
    return False


def find_inscription_tool():
    """Returns the first inscription pen in the player backpack, or None."""
    for pen_id in SCRIBE_PEN_IDS:
        item = Items.FindByID(pen_id, -1, Player.Backpack.Serial)
        if item is not None:
            return item
    return None


def get_existing_scroll_ids(dest):
    """Returns a set of scroll ItemIDs already inside dest.Contains."""
    try:
        return set(item.ItemID for item in dest.Contains)
    except Exception:
        return set()


def meditate_until_full():
    """Triggers Meditation and waits until mana is fully restored."""
    if Player.Mana >= Player.ManaMax:
        return
    log("Mana %d/%d — meditating..." % (Player.Mana, Player.ManaMax), 0x35)
    Journal.Clear()
    # Player.UseSkill is the RE API call.  Some shards may need Misc.UseSkill.
    Player.UseSkill("Meditation")
    waited = 0
    while Player.Mana < Player.ManaMax and waited < cfg.mana_wait_timeout:
        Misc.Pause(cfg.meditate_poll_ms)
        waited += cfg.meditate_poll_ms
    log("Mana restored: %d/%d" % (Player.Mana, Player.ManaMax), 0x40)


# ─────────────────────────────────────────────────────────────────────────────
# Material calculation and pulling
# ─────────────────────────────────────────────────────────────────────────────

def calculate_materials(needed_scrolls):
    """
    Returns (blank_count, reagent_map) for all scrolls to be crafted.
    reagent_map = { reagent_item_id: total_count_needed }
    """
    blank_count = len(needed_scrolls)
    reagent_map = {}
    for _name, _circle, _sid, reagents in needed_scrolls:
        for rid in reagents:
            reagent_map[rid] = reagent_map.get(rid, 0) + 1
    return blank_count, reagent_map


def pull_materials(source_serial, blank_count, reagent_map):
    """Moves blank scrolls and reagents from the source container to backpack."""
    source = Items.FindBySerial(source_serial)
    if source is None:
        log("Material source container not found (serial 0x%X). Skipping pull." % source_serial, 0x25)
        return

    bp = Player.Backpack

    # ── Pull blank scrolls ────────────────────────────────────────────────────
    needed_blanks = blank_count
    for item in list(source.Contains):
        if item.ItemID != BLANK_SCROLL_ID or needed_blanks <= 0:
            continue
        pull = min(item.Amount, needed_blanks)
        Items.Move(item, bp, pull)
        Misc.Pause(cfg.item_move_delay)
        needed_blanks -= pull

    if needed_blanks > 0:
        log("Warning: short %d blank scroll(s) in source." % needed_blanks, 0x25)

    # ── Pull reagents ─────────────────────────────────────────────────────────
    for rid, amount in reagent_map.items():
        needed = amount
        for item in list(source.Contains):
            if item.ItemID != rid or needed <= 0:
                continue
            pull = min(item.Amount, needed)
            Items.Move(item, bp, pull)
            Misc.Pause(cfg.item_move_delay)
            needed -= pull
        if needed > 0:
            log("Warning: short %d of reagent 0x%04X." % (needed, rid), 0x25)

    log("Material pull complete.", 0x40)


# ─────────────────────────────────────────────────────────────────────────────
# Gump management
# ─────────────────────────────────────────────────────────────────────────────

def open_craft_gump(tool):
    """Double-clicks the inscription pen and waits for the crafting gump."""
    Journal.Clear()
    Items.UseItem(tool)
    if Gumps.WaitForGump(CRAFT_GUMP_ID, cfg.gump_open_delay):
        return True
    log("Crafting gump did not open. Check that this is the right tool.", 0x25)
    return False


def close_craft_gump():
    """Closes the crafting gump via the Exit button."""
    Gumps.SendAction(CRAFT_GUMP_ID, GUMP_BTN_EXIT)
    Misc.Pause(300)


# ─────────────────────────────────────────────────────────────────────────────
# Scroll crafting
# ─────────────────────────────────────────────────────────────────────────────

def _build_craft_plan(source_list, needed_scrolls):
    """
    Pre-computes the right-panel button ID for each scroll that needs crafting.

    Returns a list of tuples:
        (spell_name, circle, scroll_id, spell_gump_btn)
    """
    # Build per-circle slot lookup: spell_name -> slot index (0-based)
    circle_slot = {}
    for circle_num in range(1, 9):
        for slot, entry in enumerate(s for s in source_list if s[1] == circle_num):
            circle_slot[entry[0]] = slot

    plan = []
    for spell_name, circle, scroll_id, _reagents in needed_scrolls:
        slot     = circle_slot.get(spell_name, 0)
        gump_btn = SPELL_BTN_FIRST + slot * SPELL_BTN_STEP
        plan.append((spell_name, circle, scroll_id, gump_btn))
    return plan


def craft_one_scroll(spell_name, circle, spell_btn, current_circle):
    """
    Issues the gump clicks to craft one scroll.

    Returns (result_str, current_circle_after):
        result_str: "success" | "fail" | "no_gump"
    """
    # Switch to the correct circle if the gump isn't already on it
    if circle != current_circle:
        Gumps.SendAction(CRAFT_GUMP_ID, CIRCLE_BTNS[circle])
        Misc.Pause(cfg.circle_switch_ms)
        current_circle = circle

    # Click the spell slot to begin crafting
    Journal.Clear()
    Gumps.SendAction(CRAFT_GUMP_ID, spell_btn)
    Misc.Pause(cfg.craft_delay)

    # Confirm the gump is still open
    if not Gumps.HasGump():
        return "no_gump", current_circle

    if journal_contains_any(CRAFT_FAIL_PHRASES):
        log("Craft failed for '%s'. Check reagents / blanks / mana." % spell_name, 0x25)
        return "fail", current_circle

    # Treat as success if success phrase found, or if no failure phrase found
    # (some servers don't print explicit success messages).
    return "success", current_circle


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── 1. Find the inscription pen ───────────────────────────────────────────
    tool = find_inscription_tool()
    if tool is None:
        log("No inscription pen found in backpack. Stopping.", 0x25)
        return

    # ── 2. Prompt for destination ─────────────────────────────────────────────
    log("Target the spellbook or container to fill...", 0x53)
    dest_serial = Target.PromptTarget("Select destination spellbook or container:", 0x004F)
    if dest_serial is None:
        log("No target selected. Stopping.", 0x25)
        return

    dest = Items.FindBySerial(dest_serial)
    if dest is None:
        log("Could not locate targeted item. Stopping.", 0x25)
        return

    is_spellbook = dest.ItemID in SPELLBOOK_IDS
    dest_label   = "spellbook" if is_spellbook else "container"
    log("Destination: %s (serial 0x%X)." % (dest_label, dest.Serial), 0x40)

    # ── 3. Select the scroll data for the configured mode ─────────────────────
    source_list = MAGERY_SCROLLS if cfg.mode == "magery" else SPELLWEAVING_SCROLLS
    if not source_list:
        log("No scroll data available for mode '%s'. Stopping." % cfg.mode, 0x25)
        return

    # Apply optional spell filter
    if cfg.spell_filter is not None:
        filter_set  = set(cfg.spell_filter)
        source_list = [s for s in source_list if s[0] in filter_set]

    # ── 4. Determine which scrolls are still missing from the destination ──────
    existing_ids = get_existing_scroll_ids(dest)
    needed       = [s for s in source_list if s[2] not in existing_ids]

    if not needed:
        log("Destination already contains all requested scrolls. Done.", 0x40)
        return

    log("Need to craft %d scroll(s)." % len(needed), 0x40)

    # ── 5. Pull materials from source chest (if configured) ───────────────────
    if cfg.material_source_serial:
        blank_count, reagent_map = calculate_materials(needed)
        log("Pulling %d blank scroll(s) and reagents from source..." % blank_count, 0x40)
        pull_materials(cfg.material_source_serial, blank_count, reagent_map)
        Misc.Pause(1000)

    # ── 6. Meditate to full before starting if mana is low ────────────────────
    if Player.Mana < cfg.meditate_threshold:
        meditate_until_full()

    # ── 7. Pre-compute gump buttons for the craft plan ────────────────────────
    craft_plan = _build_craft_plan(source_list, needed)

    # ── 8. Open the crafting gump ─────────────────────────────────────────────
    tool = find_inscription_tool()   # refresh reference in case it moved
    if tool is None:
        log("Inscription pen not found. Stopping.", 0x25)
        return

    if not open_craft_gump(tool):
        return

    # ── 9. Craft each scroll ──────────────────────────────────────────────────
    current_circle = None   # tracks which circle the gump is currently showing
    crafted = 0
    failed  = 0

    for spell_name, circle, scroll_id, spell_btn in craft_plan:

        # ── Mana check: close gump, meditate, reopen ──────────────────────────
        if Player.Mana < cfg.meditate_threshold:
            close_craft_gump()
            meditate_until_full()

            # Refresh the pen reference – it may have been used up
            tool = find_inscription_tool()
            if tool is None:
                log("Ran out of inscription pens. Stopping.", 0x25)
                break

            if not open_craft_gump(tool):
                break

            current_circle = None   # gump reopened; circle state is unknown

        # ── Attempt the craft ─────────────────────────────────────────────────
        result, current_circle = craft_one_scroll(
            spell_name, circle, spell_btn, current_circle
        )

        if result == "no_gump":
            log("Crafting gump closed unexpectedly. Stopping.", 0x25)
            break

        if result == "success":
            crafted += 1
            # Find the freshly crafted scroll in the backpack and send to dest
            scroll = Items.FindByID(scroll_id, -1, Player.Backpack.Serial)
            if scroll is not None:
                Items.Move(scroll, dest, 1)
                Misc.Pause(cfg.item_move_delay)
                log("Crafted '%s' → %s." % (spell_name, dest_label), 0x40)
            else:
                log("Scroll for '%s' not found in backpack after craft." % spell_name, 0x35)
        else:
            failed += 1

    # ── 10. Close the gump and report ─────────────────────────────────────────
    close_craft_gump()
    log("Done.  Crafted: %d   Failed: %d" % (crafted, failed), 0x40)


# ─────────────────────────────────────────────────────────────────────────────
main()
