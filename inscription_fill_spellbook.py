# Progress tracking file
import os
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), 'inscription_progress.txt')

# Progress tracking helpers
def save_progress(index):
    try:
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(index))
    except Exception as e:
        log("[DEBUG] Could not save progress: {}".format(e), 0x25)

def load_progress():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return int(f.read())
    except:
        return 0
# ─────────────────────────────────────────────────────────────────────────────
# inscription_fill_spellbook.py
# ─────────────────────────────────────────────────────────────────────────────
# Two modes, chosen at startup via a numbered chat prompt:
#
#   1) CRAFT — craft 1 of every magery scroll, move each one to the scroll chest
#   2) FILL  — drag scrolls from the scroll chest into a targeted spellbook
#
# No spellbook-content detection is attempted — FILL simply tries to add every
# scroll from the chest.  Duplicates are harmlessly rejected by the server.
#
# Craft-success detection uses a mana comparison: if mana drops after the gump
# click the server accepted and consumed the inscription attempt; if mana is
# unchanged the craft failed (missing reagents / blank scrolls / etc.).
#
# Config: set cfg.scroll_container_serial once your scroll chest is placed.
#
# Gump NOTE:
#   Left  panel  (circles): 1, 8, 15, 22, 29, 36, 43, 50
#   Right panel  (spells):  2, 9, 16, 23, 30, 37, 44, 51
#   Adjust CIRCLE_BTNS / SPELL_BTN_FIRST / SPELL_BTN_STEP if your shard
#   uses a different button layout.
# ─────────────────────────────────────────────────────────────────────────────

# IDE IntelliSense only – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

import datetime
import os
import time
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import FindItem as _FindItem
# Import canonical gump menu mapping

# Mapping of magery circle to the top menu button for that circle in the inscription gump
# Use this to ensure the script navigates to the correct circle before selecting a spell
CIRCLE_TOP_MENU_BUTTONS = {
    1: 1,    # Circle 1 (top menu button)
    2: 8,    # Circle 2
    3: 15,   # Circle 3
    4: 22,   # Circle 4
    5: 29,   # Circle 5
    6: 36,   # Circle 6
    7: 43,   # Circle 7
    8: 50,   # Circle 8
}

# Mapping from magery circle to group menu button (1-2, 3-4, 5-6, 7-8)
MAGERY_GROUP_MENU_BUTTONS = {
    1: 1, 2: 1,      # First - Second Circle
    3: 8, 4: 8,      # Third - Fourth Circle
    5: 15, 6: 15,    # Fifth - Sixth Circle
    7: 22, 8: 22,    # Seventh - Eighth Circle
}

# Minimal robust magery inscription loop for your shard's gump structure
# Assumes: SPELL_TO_BUTTON and GROUP_MENU_BUTTONS are defined as per your logs

# Mapping from magery circle to group menu button (update if needed)
GROUP_MENU_BUTTONS = {
    1: 1,  2: 1,       # First - Second Circle
    3: 8,  4: 8,       # Third - Fourth Circle
    5: 15, 6: 15,      # Fifth - Sixth Circle
    7: 22, 8: 22,      # Seventh - Eighth Circle
}

# List of circles in order (top-down)
CIRCLES = [8, 7, 6, 5, 4, 3, 2, 1]

# Example: magery_spells_by_circle = {circle: [spell names in order]}
magery_spells_by_circle = {
    8: ["Earthquake", "Energy Vortex", "Resurrection", "Summon Air Elemental", "Summon Daemon", "Summon Earth Elemental", "Summon Fire Elemental", "Summon Water Elemental"],
    7: ["Chain Lightning", "Energy Field", "Flamestrike", "Gate Travel", "Mana Vampire", "Mass Dispel", "Meteor Swarm", "Polymorph"],
    6: ["Dispel", "Energy Bolt", "Explosion", "Invisibility", "Mark", "Mass Curse", "Paralyze Field", "Reveal"],
    5: ["Blade Spirits", "Dispel Field", "Incognito", "Magic Reflection", "Mind Blast", "Paralyze", "Poison Field", "Summon Creature"],
    4: ["Arch Cure", "Arch Protection", "Curse", "Fire Field", "Greater Heal", "Lightning", "Mana Drain", "Recall"],
    3: ["Bless", "Fireball", "Magic Lock", "Poison", "Telekinesis", "Teleport", "Unlock", "Wall of Stone"],
    2: ["Agility", "Cunning", "Cure", "Harm", "Magic Trap", "Magic Untrap", "Protection", "Strength"],
    1: ["Reactive Armor", "Clumsy", "Create Food", "Feeblemind", "Heal", "Magic Arrow", "Night Sight", "Weaken"],
}

# ─────────────────────────────────────────────────────────────────────────────
# Config — edit this block
# ─────────────────────────────────────────────────────────────────────────────
class cfg:
    # ── Debugging ───────────────────────────────────────────────────────────
    DEBUG = False  # Set to True to log every action
    # ── Scroll chest ──────────────────────────────────────────────────────────
    # Serial of the container used as the scroll depot:
    #   CRAFT mode  → crafted scrolls are moved HERE after each successful craft
    #   FILL  mode  → scrolls are pulled FROM HERE into the target spellbook
    # Set this once your chest is placed.  e.g.  scroll_container_serial = 0x4012ABCD
    scroll_container_serial = 0x400F3F52

    # ── Timing (milliseconds) ─────────────────────────────────────────────────
    craft_delay        = 4000   # wait after clicking a spell button to craft
    gump_open_delay    = 5000   # timeout waiting for the crafting gump
    item_move_delay    = 2000   # pause between Items.Move calls
    circle_switch_ms   = 1200   # pause after switching circles in the craft gump
    action_pause_ms    = 800    # general inter-action breathing room
    post_craft_settle  = 1200   # extra pause before searching for crafted scroll

    # ── Mana management ───────────────────────────────────────────────────────
    meditate_threshold = 40     # meditate when mana falls below this value
    meditate_poll_ms   = 500    # polling interval while waiting for mana
    mana_wait_timeout  = 90000  # max ms to wait for full mana (90 s)

    # ── Logging ───────────────────────────────────────────────────────────────
    log_file = os.path.join(os.path.dirname(__file__), 'inscription_fill_spellbook.log')


# ─────────────────────────────────────────────────────────────────────────────
# Item IDs
# ─────────────────────────────────────────────────────────────────────────────

# Scribe's pen (inscription tool).  0x0FBF is standard; some shards use 0x0FBE.
SCRIBE_PEN_IDS  = [0x0FBF, 0x0FBE]

# Spellbook graphic IDs.
SPELLBOOK_IDS   = {0x0EFA, 0x0EFF}

# Blank scroll.
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


# Gump button mapping (inferred from macro recording)
# Allow multiple gump IDs for shard compatibility
CRAFT_GUMP_IDS = [2653346093]  # Only use gump IDs from your export
CRAFT_GUMP_ID = CRAFT_GUMP_IDS[0]  # Use the first as the default



# Unified mapping: (Spell Name, Button ID, Scroll Item ID, [Reagents])
MAGERY_GUMP_MAP = {
    1: [
        ("Reactive Armor", 19, 0x1F2D, [REAGENT['GA'], REAGENT['SS'], REAGENT['SA']]),
        ("Clumsy", 20, 0x1F2E, [REAGENT['BM'], REAGENT['NS']]),
        ("Create Food", 21, 0x1F2F, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR']]),
        ("Feeblemind", 22, 0x1F30, [REAGENT['GI'], REAGENT['NS']]),
        ("Heal", 23, 0x1F31, [REAGENT['GA'], REAGENT['GI'], REAGENT['SS']]),
        ("Magic Arrow", 24, 0x1F32, [REAGENT['SA']]),
        ("Night Sight", 25, 0x1F33, [REAGENT['SS'], REAGENT['SA']]),
        ("Weaken", 26, 0x1F34, [REAGENT['GA'], REAGENT['NS']]),
    ],
    2: [
        ("Agility", 27, 0x1F35, [REAGENT['BM'], REAGENT['MR']]),
        ("Cunning", 28, 0x1F36, [REAGENT['MR'], REAGENT['NS']]),
        ("Cure", 31, 0x1F37, [REAGENT['GA'], REAGENT['GI']]),
        ("Harm", 32, 0x1F38, [REAGENT['NS'], REAGENT['SS']]),
        ("Magic Trap", 33, 0x1F39, [REAGENT['GA'], REAGENT['SS'], REAGENT['SA']]),
        ("Magic Untrap", 34, 0x1F3A, [REAGENT['BM'], REAGENT['SA']]),
        ("Protection", 35, 0x1F3B, [REAGENT['GA'], REAGENT['GI'], REAGENT['SA']]),
        ("Strength", 36, 0x1F3C, [REAGENT['MR'], REAGENT['NS']]),
    ],
    3: [
        ("Bless", 19, 0x1F3D, [REAGENT['GA'], REAGENT['MR']]),
        ("Fireball", 20, 0x1F3E, [REAGENT['BP']]),
        ("Magic Lock", 21, 0x1F3F, [REAGENT['BM'], REAGENT['GA'], REAGENT['SA']]),
        ("Poison", 22, 0x1F40, [REAGENT['NS']]),
        ("Telekinesis", 23, 0x1F41, [REAGENT['BM'], REAGENT['MR']]),
        ("Teleport", 24, 0x1F42, [REAGENT['BM'], REAGENT['MR']]),
        ("Unlock", 25, 0x1F43, [REAGENT['BM'], REAGENT['SA']]),
        ("Wall of Stone", 26, 0x1F44, [REAGENT['BM'], REAGENT['GA']]),
    ],
    4: [
        ("Arch Cure", 27, 0x1F45, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR']]),
        ("Arch Protection", 28, 0x1F46, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR'], REAGENT['SA']]),
        ("Curse", 31, 0x1F47, [REAGENT['GA'], REAGENT['NS'], REAGENT['SA']]),
        ("Fire Field", 32, 0x1F48, [REAGENT['BP'], REAGENT['SS'], REAGENT['SA']]),
        ("Greater Heal", 33, 0x1F49, [REAGENT['GA'], REAGENT['GI'], REAGENT['MR'], REAGENT['SS']]),
        ("Lightning", 34, 0x1F4A, [REAGENT['MR'], REAGENT['SA']]),
        ("Mana Drain", 35, 0x1F4B, [REAGENT['BP'], REAGENT['MR'], REAGENT['SS']]),
        ("Recall", 36, 0x1F4C, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR']]),
    ],
    5: [
        ("Blade Spirits", 19, 0x1F4D, [REAGENT['BP'], REAGENT['MR'], REAGENT['NS']]),
        ("Dispel Field", 20, 0x1F4E, [REAGENT['BP'], REAGENT['GA'], REAGENT['SS'], REAGENT['SA']]),
        ("Incognito", 21, 0x1F4F, [REAGENT['BM'], REAGENT['GA'], REAGENT['NS']]),
        ("Magic Reflection", 22, 0x1F50, [REAGENT['GA'], REAGENT['MR'], REAGENT['SS']]),
        ("Mind Blast", 23, 0x1F51, [REAGENT['BP'], REAGENT['MR'], REAGENT['NS'], REAGENT['SA']]),
        ("Paralyze", 24, 0x1F52, [REAGENT['GA'], REAGENT['MR'], REAGENT['SS']]),
        ("Poison Field", 25, 0x1F53, [REAGENT['BP'], REAGENT['NS'], REAGENT['SS']]),
        ("Summon Creature", 26, 0x1F54, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
    ],
    6: [
        ("Dispel", 27, 0x1F55, [REAGENT['GA'], REAGENT['MR'], REAGENT['SA']]),
        ("Energy Bolt", 28, 0x1F56, [REAGENT['BP'], REAGENT['NS']]),
        ("Explosion", 31, 0x1F57, [REAGENT['BM'], REAGENT['MR']]),
        ("Invisibility", 32, 0x1F58, [REAGENT['BM'], REAGENT['NS']]),
        ("Mark", 33, 0x1F59, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR']]),
        ("Mass Curse", 34, 0x1F5A, [REAGENT['GA'], REAGENT['MR'], REAGENT['NS'], REAGENT['SA']]),
        ("Paralyze Field", 35, 0x1F5B, [REAGENT['BP'], REAGENT['GI'], REAGENT['SS']]),
        ("Reveal", 36, 0x1F5C, [REAGENT['BM'], REAGENT['SA']]),
    ],
    7: [
        ("Chain Lightning", 19, 0x1F5D, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR'], REAGENT['SA']]),
        ("Energy Field", 20, 0x1F5E, [REAGENT['BP'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
        ("Flamestrike", 21, 0x1F5F, [REAGENT['SS'], REAGENT['SA']]),
        ("Gate Travel", 22, 0x1F60, [REAGENT['BP'], REAGENT['MR'], REAGENT['SA']]),
        ("Mana Vampire", 23, 0x1F61, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
        ("Mass Dispel", 24, 0x1F62, [REAGENT['BP'], REAGENT['GA'], REAGENT['MR'], REAGENT['SA']]),
        ("Meteor Swarm", 25, 0x1F63, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
        ("Polymorph", 26, 0x1F64, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
    ],
    8: [
        ("Earthquake", 27, 0x1F65, [REAGENT['BM'], REAGENT['GI'], REAGENT['MR'], REAGENT['SA']]),
        ("Energy Vortex", 28, 0x1F66, [REAGENT['BP'], REAGENT['BM'], REAGENT['MR'], REAGENT['NS']]),
        ("Resurrection", 31, 0x1F67, [REAGENT['BM'], REAGENT['GA'], REAGENT['GI']]),
        ("Summon Air Elemental", 32, 0x1F68, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
        ("Summon Daemon", 33, 0x1F69, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
        ("Summon Earth Elemental", 34, 0x1F6A, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
        ("Summon Fire Elemental", 35, 0x1F6B, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS'], REAGENT['SA']]),
        ("Summon Water Elemental", 36, 0x1F6C, [REAGENT['BM'], REAGENT['MR'], REAGENT['SS']]),
    ],
}

# Button 0 = Exit the crafting gump.
GUMP_BTN_EXIT = 0


# ─────────────────────────────────────────────────────────────────────────────
# Magery scroll data
# ─────────────────────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────────────────────
# Spellweaving scroll data (stub)
# ─────────────────────────────────────────────────────────────────────────────
SPELLWEAVING_SCROLLS = []   # Spellweaving not implemented in this script


# Fast lookup: spell name (lowercase) -> scroll item ID, using MAGERY_GUMP_MAP
_SPELL_NAME_TO_ID = {}
for circle_spells in MAGERY_GUMP_MAP.values():
    for name, btn, sid, _ in circle_spells:
        _SPELL_NAME_TO_ID[name.lower()] = sid

# Set of all magery scroll item IDs — used to identify crafted scrolls in the backpack
SCROLL_IDS = frozenset(sid for spells in MAGERY_GUMP_MAP.values() for _, _, sid, _ in spells)


# ─────────────────────────────────────────────────────────────────────────────
# Pen-wore-out journal phrases — still needed to handle tool breakage.
TOOL_WORN_PHRASES = [
    "You have worn out your tool",
    "worn out your",
]


# ─────────────────────────────────────────────────────────────────────────────
# Startup prompt  (borrowed from skill_TamingBot.py)
# ─────────────────────────────────────────────────────────────────────────────

def Prompt(question, options, timeout=30):
    """
    Displays numbered options in chat and waits up to `timeout` seconds for
    the player to type one of the option numbers (just the digit, e.g. "1").
    Returns the 1-based choice; defaults to 1 on timeout.
    """
    CYAN   = 0x59
    YELLOW = 0x35
    Misc.SendMessage('──────────────────────────────', CYAN)
    Misc.SendMessage(question, CYAN)
    for i, opt in enumerate(options, 1):
        Misc.SendMessage('  %d) %s' % (i, opt), CYAN)
    Misc.SendMessage('Type your choice number in chat now.', CYAN)
    # Pause so the SendMessage lines settle into the journal, then clear so
    # only the player's reply triggers a match.
    Misc.Pause(600)
    Journal.Clear()
    Misc.Pause(200)
    Journal.Clear()
    deadline = time.time() + timeout
    while time.time() < deadline:
        for i in range(1, len(options) + 1):
            if Journal.SearchByName(str(i), Player.Name):
                Journal.Clear()
                Misc.Pause(300)
                Misc.SendMessage('> %d) %s' % (i, options[i - 1]), YELLOW)
                return i
        Misc.Pause(200)
    Misc.SendMessage('No response — defaulting to option 1', YELLOW)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def log(msg, color=0x3F):
    if getattr(cfg, "DEBUG", False):
        Misc.SendMessage("[DEBUG] %s" % msg, 0x5A)
    else:
        Misc.SendMessage("[INSCRIBE] %s" % msg, color)
    log_file = getattr(cfg, "log_file", None)
    if log_file:
        try:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, 'a', encoding='utf-8') as _lf:
                _lf.write("%s  %s\n" % (ts, msg))
        except Exception as _e:
            Misc.SendMessage("[INSCRIBE] log write failed: %s" % _e, 0x25)


def is_connected():
    try:
        return Player.Connected
    except AttributeError:
        return Player.Serial != 0


def journal_contains_any(phrases):
    for phrase in phrases:
        if Journal.Search(phrase):
            return True
    return False


def find_inscription_tool(extra_container=None):
    """Returns the first inscription pen found.
    Searches extra_container (e.g. the scroll chest) first, then the backpack.
    """
    search_serials = []
    if extra_container is not None:
        search_serials.append(extra_container.Serial)
    search_serials.append(Player.Backpack.Serial)

    for serial in search_serials:
        for pen_id in SCRIBE_PEN_IDS:
            item = Items.FindByID(pen_id, -1, serial)
            if item is not None:
                return item
    return None


def get_scroll_container():
    """
    Fetches the scroll chest and opens it so Razor Enhanced caches its contents.
    Falls back to a target prompt if the serial is unset or the chest is out of range.
    Returns the Item object, or None on failure.
    """
    chest = None

    if cfg.scroll_container_serial is not None:
        chest = Items.FindBySerial(cfg.scroll_container_serial)
        if chest is None:
            log("Scroll chest (0x%X) not found — prompting for target." % cfg.scroll_container_serial, 0x25)

    if chest is None:
        log("Target your scroll chest now.")
        serial = Target.PromptTarget("Target the scroll chest")
        if serial == 0 or serial == Player.Serial:
            log("Cancelled.", 0x25)
            return None
        chest = Items.FindBySerial(serial)
        if chest is None:
            log("Could not find targeted item.", 0x25)
            return None
        cfg.scroll_container_serial = serial
        log("Scroll chest set to 0x%X (%s)." % (serial, chest.Name))

    Items.UseItem(chest)
    Misc.Pause(1500)
    return Items.FindBySerial(cfg.scroll_container_serial)


def meditate_until_full():
    """Meditates until mana is fully restored (or the timeout elapses)."""
    if Player.Mana >= Player.ManaMax:
        return
    log("Mana %d/%d — meditating..." % (Player.Mana, Player.ManaMax), 0x35)
    Player.UseSkill("Meditation")
    waited = 0
    while Player.Mana < Player.ManaMax and waited < cfg.mana_wait_timeout:
        if not is_connected():
            log("Disconnected during meditation. Stopping.", 0x25)
            return
        Misc.Pause(cfg.meditate_poll_ms)
        waited += cfg.meditate_poll_ms
    log("Mana restored: %d/%d" % (Player.Mana, Player.ManaMax), 0x40)


def transfer_scrolls_to_chest(chest):
    """
    Scans the top level of the backpack for any magery scroll and moves each
    one to the scroll chest.  Returns the count of scrolls moved.
    """
    items = list(Player.Backpack.Contains)
    moved = 0
    for item in items:
        if not is_connected():
            log("Disconnected during scroll transfer. Stopping.", 0x25)
            return moved
        if item.ItemID not in SCROLL_IDS:
            continue
        Items.Move(item, chest, item.Amount)
        Misc.Pause(cfg.item_move_delay)
        log("Transferred '%s' to chest." % item.Name, 0x40)
        moved += 1
    return moved


# ─────────────────────────────────────────────────────────────────────────────
# Gump management
# ─────────────────────────────────────────────────────────────────────────────

def open_craft_gump(tool):
    """Uses the inscription pen and waits for the crafting gump."""
    # Allow any known/allowed gump ID, warn if new but do not abort
    Journal.Clear()
    Items.UseItem(tool)
    if Gumps.WaitForGump(CRAFT_GUMP_ID, cfg.gump_open_delay):
        actual_id = int(Gumps.CurrentGump())
        if actual_id not in CRAFT_GUMP_IDS:
            log("[WARN] Gump ID %d not in allowed list %s. Proceeding, but consider adding it to CRAFT_GUMP_IDS for your shard." % (actual_id, CRAFT_GUMP_IDS), 0x35)
        return True
    if Gumps.HasGump():
        actual_id = int(Gumps.CurrentGump())
        if actual_id not in CRAFT_GUMP_IDS:
            log("[WARN] Unexpected gump ID %d (allowed: %s). Proceeding, but consider adding it to CRAFT_GUMP_IDS for your shard." % (actual_id, CRAFT_GUMP_IDS), 0x35)
        return True
    log("Crafting gump did not open. Check that this is the right tool.", 0x25)
    return False


def close_craft_gump():
    Gumps.SendAction(CRAFT_GUMP_ID, GUMP_BTN_EXIT)
    Misc.Pause(cfg.action_pause_ms)


# ─────────────────────────────────────────────────────────────────────────────
# Scroll crafting — mana-drop success detection
# ─────────────────────────────────────────────────────────────────────────────

def craft_one_scroll(spell_name, circle, spell_btn, current_circle):
    """
    Navigates to the correct circle group if needed, then clicks the spell button.
    Returns ("crafted" | "no_gump", new_current_circle).
    """
    target_group = (circle - 1) // 2
    current_group = -1 if current_circle is None else (current_circle - 1) // 2

    if target_group != current_group:
        nav_btn = GROUP_MENU_BUTTONS[circle]
        if cfg.DEBUG:
            log("[CRAFT] Switching to group for circle {} (nav btn {})".format(circle, nav_btn), 0x5A)
        Gumps.SendAction(CRAFT_GUMP_ID, nav_btn)
        if not Gumps.WaitForGump(CRAFT_GUMP_ID, cfg.circle_switch_ms):
            return "no_gump", current_circle
        Misc.Pause(cfg.action_pause_ms)

    Gumps.SendAction(CRAFT_GUMP_ID, spell_btn)
    Gumps.WaitForGump(CRAFT_GUMP_ID, 3000)

    return "crafted", circle


# ─────────────────────────────────────────────────────────────────────────────
# Mode 1 — CRAFT
# ─────────────────────────────────────────────────────────────────────────────

def mode_craft(start_index=0):
    """
    Crafts 1 of every magery scroll and moves each one to the scroll chest.

    Each spell button in the crafting gump is clicked.  After each attempt the
    backpack is checked for the newly created scroll — if found it is moved to
    cfg.scroll_container_serial.  No mana comparison is used.
    """
    log("[CRAFT] Starting mode_craft()", 0x5A) if cfg.DEBUG else None
    chest = get_scroll_container()
    if chest is None:
        return

    log("[CRAFT] Looking for inscription tool", 0x5A) if cfg.DEBUG else None
    tool = find_inscription_tool(chest)
    if tool is None:
        log("No inscription pen found in chest or backpack. Stopping.", 0x25)
        return



    if Player.Mana < getattr(cfg, "meditate_threshold", 40):
        log("[CRAFT] Meditating before starting", 0x5A) if cfg.DEBUG else None
        meditate_until_full()


    log("[CRAFT] Opening crafting gump", 0x5A) if cfg.DEBUG else None
    if not open_craft_gump(tool):
        return
    # Wait 400ms after gump opens before crafting to avoid disconnects
    Misc.Pause(400)

    current_circle = None
    gump_open      = True
    crafted = failed = 0


    # Try to import the spell button mapping robustly for Razor Enhanced/IronPython
    import sys
    import os
    mapping_path = os.path.dirname(os.path.abspath(__file__))
    if mapping_path not in sys.path:
        sys.path.append(mapping_path)
    try:
        from spell_button_mapping import SPELL_TO_BUTTON
    except ImportError:
        # Fallback: try execfile (IronPython only)
        try:
            execfile(os.path.join(mapping_path, 'spell_button_mapping.py'))
        except Exception as e:
            raise ImportError('Could not import or exec spell_button_mapping.py: %s' % e)

    # Build a flat spell list in gump order (circle 1 to 8, in order)
    flat_spell_data = []  # (circle, spell_name, scroll_id, reagents)
    for circle in range(1, 9):
        for entry in magery_spells_by_circle[circle]:
            # Find scroll_id and reagents from MAGERY_GUMP_MAP
            for tup in MAGERY_GUMP_MAP[circle]:
                if tup[0] == entry:
                    flat_spell_data.append((circle, entry, tup[2], tup[3]))
                    break

    total = len(flat_spell_data)
    for i in range(start_index, total):
        if not is_connected():
            log("Disconnected. Stopping.", 0x25)
            save_progress(i)
            return
        circle, spell_name, scroll_id, _reagents = flat_spell_data[i]
        spell_btn = SPELL_TO_BUTTON.get(spell_name)
        if spell_btn is None:
            log("[CRAFT] No button mapping for {}! Skipping.".format(spell_name), 0x25)
            continue
        if cfg.DEBUG:
            log("[CRAFT] Crafting {} (circle {})".format(spell_name, circle), 0x5A)

        # ── Mana gate: close gump, meditate, reopen ───────────────────────────
        if Player.Mana < getattr(cfg, "meditate_threshold", 40):
            log("[CRAFT] Meditating (low mana)", 0x5A) if cfg.DEBUG else None
            if gump_open:
                close_craft_gump()
                gump_open = False
            meditate_until_full()
            tool = find_inscription_tool(chest)
            if tool is None:
                log("No inscription pen after meditation. Stopping.", 0x25)
                break
            if not open_craft_gump(tool):
                break
            gump_open      = True
            current_circle = None

        # ── Attempt the craft ─────────────────────────────────────────────────
        if cfg.DEBUG:
            log("[CRAFT] Sending gump action for {}".format(spell_name), 0x5A)
        result, current_circle = craft_one_scroll(
            spell_name, circle, spell_btn, current_circle
        )

        if result == "no_gump":
            if cfg.DEBUG:
                log("[CRAFT] Gump closed unexpectedly after {}".format(spell_name), 0x5A)
            gump_open = False
            save_progress(i)  # Save progress on failure
            if journal_contains_any(TOOL_WORN_PHRASES):
                log("Scribe's pen wore out — finding a replacement...", 0x35)
                # The craft that broke the pen may have succeeded; check backpack.
                Misc.Pause(cfg.post_craft_settle)
                scroll = _FindItem(scroll_id, Player.Backpack)
                if scroll is not None:
                    Items.Move(scroll, chest, 1)
                    Misc.Pause(cfg.item_move_delay)
                    Items.WaitForContents(chest, 1500)
                    chest_count = len([i for i in chest.Contains if i.ItemID == scroll_id])
                    log("Crafted '%s' → chest (pen change)  [%d in chest]." % (spell_name, chest_count), 0x40)
                    crafted += 1
                tool = find_inscription_tool(chest)
                if tool is None:
                    log("No more pens in backpack. Stopping.", 0x25)
                    break
                if not open_craft_gump(tool):
                    break
                gump_open      = True
                current_circle = None
                continue
            log("Crafting gump closed unexpectedly. Stopping.", 0x25)
            break

        # Scroll in backpack = craft succeeded; (moving to chest is disabled)
        Misc.Pause(cfg.post_craft_settle)
        if cfg.DEBUG:
            log("[CRAFT] Post-craft settle for {}".format(spell_name), 0x5A)
        scroll = _FindItem(scroll_id, Player.Backpack)
        if scroll is not None:
            crafted += 1
            if cfg.DEBUG:
                log("[CRAFT] Success: {} crafted".format(spell_name), 0x5A)
            # Items.Move(scroll, chest, 1)
            # Misc.Pause(cfg.item_move_delay)
            # Items.WaitForContents(chest, 1500)
            # chest_count = len([i for i in chest.Contains if i.ItemID == scroll_id])
            log("Crafted '%s' (left in backpack)." % (spell_name), 0x40)
        else:
            failed += 1
            if cfg.DEBUG:
                log("[CRAFT] Fail: {} not found after craft".format(spell_name), 0x5A)
            log("'%s': scroll not found after craft — reagents/blanks missing or skill fail." % spell_name, 0x35)
        save_progress(i + 1)  # Save progress after each attempt

    if gump_open:
        log("[CRAFT] Closing crafting gump", 0x5A) if cfg.DEBUG else None
        close_craft_gump()

    save_progress(0)

    log("Transferring scrolls to chest...", 0x40)
    transferred = transfer_scrolls_to_chest(chest)
    log("CRAFT done.  Crafted: %d   Failed: %d   Transferred: %d" % (crafted, failed, transferred), 0x40)


# ─────────────────────────────────────────────────────────────────────────────
# Mode 2 — FILL
# ─────────────────────────────────────────────────────────────────────────────

def mode_fill():
    """
    Drags scrolls from the scroll chest into a targeted spellbook.

    No spell detection is attempted — every scroll in MAGERY_GUMP_MAP is looked
    up in the chest and dragged to the book.  Duplicates are harmlessly
    rejected by the server, so it is safe to run multiple times.
    """
    chest = get_scroll_container()
    if chest is None:
        return

    log("Target the spellbook to fill...", 0x53)
    dest_serial = Target.PromptTarget("Select destination spellbook:", 0x004F)
    if dest_serial is None:
        log("No target selected. Stopping.", 0x25)
        return

    dest = Items.FindBySerial(dest_serial)
    if dest is None or dest.ItemID not in SPELLBOOK_IDS:
        log("Target is not a recognised spellbook. Stopping.", 0x25)
        return

    log("Filling spellbook 0x%X from chest 0x%X..." % (dest.Serial, chest.Serial), 0x40)


    moved = missing = 0
    # Use the new mapping for all circles, reversed order
    reversed_spells = []
    for circle in range(8, 0, -1):
        for entry in MAGERY_GUMP_MAP.get(circle, []):
            spell_name, btn_id, scroll_id, reagents = entry
            reversed_spells.append((circle, spell_name, btn_id, scroll_id, reagents))

    for circle, spell_name, btn_id, scroll_id, _reagents in reversed_spells:
        if not is_connected():
            log("Disconnected. Stopping.", 0x25)
            return
        scroll = _FindItem(scroll_id, chest)
        if scroll is not None:
            Items.Move(scroll, dest, 1)
            Misc.Pause(cfg.item_move_delay)
            log("Added '%s' -> spellbook." % spell_name, 0x40)
            moved += 1
        else:
            Misc.Pause(300)
            log("'%s' (0x%04X) not in chest." % (spell_name, scroll_id), 0x35)
            missing += 1

    log("FILL done.  Added: %d   Missing from chest: %d" % (moved, missing), 0x40)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if getattr(cfg, "log_file", None):
        try:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(cfg.log_file, 'a', encoding='utf-8') as _lf:
                _lf.write("\n" + "=" * 60 + "\n")
                _lf.write("  RUN START  %s\n" % ts)
                _lf.write("=" * 60 + "\n")
        except Exception:
            pass

    choice = Prompt(
        "INSCRIPTION — SELECT MODE:",
        [
            "CRAFT — craft 1 of every magery scroll → scroll chest",
            "FILL  — move scrolls from chest → targeted spellbook",
        ]
    )

    if choice == 1:
        # Build a flat reversed spell list for progress tracking
        reversed_spells = []
        for circle in range(8, 0, -1):
            for entry in MAGERY_GUMP_MAP.get(circle, []):
                spell_name, btn_id, scroll_id, reagents = entry
                reversed_spells.append((circle, spell_name, btn_id, scroll_id, reagents))
        total = len(reversed_spells)
        last_index = load_progress()
        if last_index > 0 and last_index < total:
            resume_choice = Prompt(
                "Resume from last craft attempt? (Last index: {} / {})".format(last_index+1, total),
                [
                    "Yes, resume from spell {}".format(reversed_spells[last_index][1]),
                    "No, start from the beginning"
                ]
            )
            if resume_choice == 1:
                mode_craft(start_index=last_index)
                return
            else:
                save_progress(0)
                mode_craft(start_index=0)
                return
        else:
            mode_craft(start_index=0)
    else:
        mode_fill()


main()
