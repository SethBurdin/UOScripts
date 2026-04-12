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
from Scripts.utilities.items import FindItem as _FindItem

# ─────────────────────────────────────────────────────────────────────────────
# Config — edit this block
# ─────────────────────────────────────────────────────────────────────────────
class cfg:
    # ── Scroll chest ──────────────────────────────────────────────────────────
    # Serial of the container used as the scroll depot:
    #   CRAFT mode  → crafted scrolls are moved HERE after each successful craft
    #   FILL  mode  → scrolls are pulled FROM HERE into the target spellbook
    # Set this once your chest is placed.  e.g.  scroll_container_serial = 0x4012ABCD
    scroll_container_serial = 0x400F3F52

    # ── Timing (milliseconds) ─────────────────────────────────────────────────
    craft_delay        = 4000   # wait after clicking a spell button to craft
    gump_open_delay    = 3000   # timeout waiting for the crafting gump
    item_move_delay    = 2000   # pause between Items.Move calls
    circle_switch_ms   = 1200   # pause after switching circles in the craft gump
    action_pause_ms    = 800    # general inter-action breathing room
    post_craft_settle  = 1200   # extra pause before searching for crafted scroll

    # ── Mana management ───────────────────────────────────────────────────────
    meditate_threshold = 40     # meditate when mana falls below this value
    meditate_poll_ms   = 500    # polling interval while waiting for mana
    mana_wait_timeout  = 90000  # max ms to wait for full mana (90 s)

    # ── Logging ───────────────────────────────────────────────────────────────
    log_file = r'C:\Users\sethb\apps\razor-enhanced\inscription_fill_spellbook.log'


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

# Fast lookup: spell name (lowercase) -> scroll item ID.
# Used when checking a real spellbook via item properties.
_SPELL_NAME_TO_ID = {name.lower(): sid for name, _c, sid, _r in MAGERY_SCROLLS}


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
    Misc.SendMessage("[INSCRIBE] %s" % msg, color)
    if cfg.log_file:
        try:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(cfg.log_file, 'a', encoding='utf-8') as _lf:
                _lf.write("%s  %s\n" % (ts, msg))
        except Exception as _e:
            Misc.SendMessage("[INSCRIBE] log write failed: %s" % _e, 0x25)


def journal_contains_any(phrases):
    for phrase in phrases:
        if Journal.Search(phrase):
            return True
    return False


def find_inscription_tool():
    """Returns the first inscription pen in the backpack, or None."""
    for pen_id in SCRIBE_PEN_IDS:
        item = Items.FindByID(pen_id, -1, Player.Backpack.Serial)
        if item is not None:
            return item
    return None


def get_scroll_container():
    """
    Fetches the scroll chest and opens it so Razor Enhanced caches its contents.
    Returns the Item object, or None on failure.
    """
    if cfg.scroll_container_serial is None:
        log("cfg.scroll_container_serial is not set — edit the script.", 0x25)
        return None
    chest = Items.FindBySerial(cfg.scroll_container_serial)
    if chest is None:
        log("Scroll chest (0x%X) not found. Are you in range?" % cfg.scroll_container_serial, 0x25)
        return None
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
        Misc.Pause(cfg.meditate_poll_ms)
        waited += cfg.meditate_poll_ms
    log("Mana restored: %d/%d" % (Player.Mana, Player.ManaMax), 0x40)


# ─────────────────────────────────────────────────────────────────────────────
# Gump management
# ─────────────────────────────────────────────────────────────────────────────

def open_craft_gump(tool):
    """Uses the inscription pen and waits for the crafting gump."""
    global CRAFT_GUMP_ID
    Journal.Clear()
    Items.UseItem(tool)
    if Gumps.WaitForGump(CRAFT_GUMP_ID, cfg.gump_open_delay):
        return True
    if Gumps.HasGump():
        actual_id = int(Gumps.CurrentGump())
        log("Gump ID %d detected (expected %d) — updating." % (actual_id, CRAFT_GUMP_ID), 0x53)
        CRAFT_GUMP_ID = actual_id
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
    Clicks the gump to craft one scroll.

    Success is determined by mana comparison: if Player.Mana drops after the
    craft click, the server consumed mana and accepted the inscription attempt.
    No journal parsing is needed or used.

    Returns ("success" | "fail" | "no_gump", new_current_circle).
    """
    if circle != current_circle:
        Gumps.SendAction(CRAFT_GUMP_ID, CIRCLE_BTNS[circle])
        Misc.Pause(cfg.circle_switch_ms)
        current_circle = circle

    Misc.Pause(cfg.action_pause_ms)
    mana_before = Player.Mana
    Gumps.SendAction(CRAFT_GUMP_ID, spell_btn)
    Misc.Pause(cfg.craft_delay)

    if not Gumps.HasGump():
        return "no_gump", current_circle

    if Player.Mana < mana_before:
        return "success", current_circle

    log("'%s': mana %d→%d (no drop) — craft failed." % (spell_name, mana_before, Player.Mana), 0x35)
    return "fail", current_circle


# ─────────────────────────────────────────────────────────────────────────────
# Mode 1 — CRAFT
# ─────────────────────────────────────────────────────────────────────────────

def mode_craft():
    """
    Crafts 1 of every magery scroll and moves each one to the scroll chest.

    Each spell button in the crafting gump is clicked.  After each attempt the
    backpack is checked for the newly created scroll — if found it is moved to
    cfg.scroll_container_serial.  No mana comparison is used.
    """
    chest = get_scroll_container()
    if chest is None:
        return

    tool = find_inscription_tool()
    if tool is None:
        log("No inscription pen found in backpack. Stopping.", 0x25)
        return

    # Pre-compute the right-panel gump button for each spell (0-based slot
    # within its circle maps to a fixed button index).
    circle_slot = {}
    for circle_num in range(1, 9):
        for slot, entry in enumerate(s for s in MAGERY_SCROLLS if s[1] == circle_num):
            circle_slot[entry[0]] = slot

    if Player.Mana < cfg.meditate_threshold:
        meditate_until_full()

    if not open_craft_gump(tool):
        return

    current_circle = None
    gump_open      = True
    crafted = failed = 0

    for spell_name, circle, scroll_id, _reagents in MAGERY_SCROLLS:
        spell_btn = SPELL_BTN_FIRST + circle_slot[spell_name] * SPELL_BTN_STEP

        # ── Mana gate: close gump, meditate, reopen ───────────────────────────
        if Player.Mana < cfg.meditate_threshold:
            if gump_open:
                close_craft_gump()
                gump_open = False
            meditate_until_full()
            tool = find_inscription_tool()
            if tool is None:
                log("No inscription pen after meditation. Stopping.", 0x25)
                break
            if not open_craft_gump(tool):
                break
            gump_open      = True
            current_circle = None

        # ── Attempt the craft ─────────────────────────────────────────────────
        result, current_circle = craft_one_scroll(
            spell_name, circle, spell_btn, current_circle
        )

        if result == "no_gump":
            gump_open = False
            if journal_contains_any(TOOL_WORN_PHRASES):
                log("Scribe's pen wore out — finding a replacement...", 0x35)
                # The craft that broke the pen may have succeeded; check backpack.
                Misc.Pause(cfg.post_craft_settle)
                scroll = _FindItem(scroll_id, Player.Backpack)
                if scroll is not None:
                    Items.Move(scroll, chest, 1)
                    Misc.Pause(cfg.item_move_delay)
                    log("Crafted '%s' → chest (pen change)." % spell_name, 0x40)
                    crafted += 1
                tool = find_inscription_tool()
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

        # result == "ok" — check backpack; presence of scroll confirms success.
        Misc.Pause(cfg.post_craft_settle)
        scroll = _FindItem(scroll_id, Player.Backpack)
        if scroll is not None:
            crafted += 1
            Items.Move(scroll, chest, 1)
            Misc.Pause(cfg.item_move_delay)
            log("Crafted '%s' -> chest." % spell_name, 0x40)
        else:
            failed += 1
            log("'%s': scroll not found after craft — reagents/blanks missing or skill fail." % spell_name, 0x35)

    if gump_open:
        close_craft_gump()

    log("CRAFT done.  Crafted: %d   Failed: %d" % (crafted, failed), 0x40)


# ─────────────────────────────────────────────────────────────────────────────
# Mode 2 — FILL
# ─────────────────────────────────────────────────────────────────────────────

def mode_fill():
    """
    Drags scrolls from the scroll chest into a targeted spellbook.

    No spell detection is attempted — every scroll in MAGERY_SCROLLS is looked
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
    for spell_name, _circle, scroll_id, _reagents in MAGERY_SCROLLS:
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
    if cfg.log_file:
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
        mode_craft()
    else:
        mode_fill()


main()
