
# glossary/runebook_handler.py
# Reusable runebook travel utilities.
#
# Usage from any script:
#   from glossary.runebook_handler import find_runebook_by_label, travel_to_named_rune
#
#   rb = find_runebook_by_label("home")
#   travel_to_named_rune(rb, "ww")

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Confirmed button bases (via macro recordings in Examples/debug2.macro) ──
RUNEBOOK_GUMP_ID           = 89
RUNEBOOK_ITEM_ID           = 0x22C5
RECALL_BUTTON_BASE         = 50   # slot N → button 50 + N
GATE_BUTTON_BASE           = 100  # slot N → button 100 + N
SACRED_JOURNEY_BUTTON_BASE = 150  # UNCONFIRMED — record a macro of Sacred Journey
                                   # from a runebook and check the button ID

# ─── Skill thresholds ─────────────────────────────────────────────────────────
RECALL_MAGERY_MIN    = 30   # Magery required to use Recall
GATE_MAGERY_MIN      = 90   # Magery required to use Gate (also requires overweight)
SACRED_JOURNEY_MIN   = 30   # Chivalry required to use Sacred Journey

_GUMP_LABELS = {"rename book", "charges", "max charges"}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _log(msg, color=68):
    Misc.SendMessage("[runebook] " + msg, color)


def _slot_from_lines(lines, rune_name):
    """
    Find rune_name in gump text lines and return its 0-based absolute slot index.
    LastGumpGetLineList includes all gump text elements, not just rune names.
    Rune names form a contiguous block — walk backward from the match to count position.
    Returns None if not found.
    """
    target = rune_name.strip().lower()
    target_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            target_idx = i
            break
    if target_idx is None:
        return None
    slot = 0
    i = target_idx - 1
    while i >= 0:
        entry = lines[i].strip()
        if not entry or entry.isdigit() or entry.lower() in _GUMP_LABELS:
            break
        slot += 1
        i -= 1
    return slot


def _open_and_find_slot(runebook, rune_name):
    """Open the runebook gump and return the slot index for rune_name, or None."""
    Items.UseItem(runebook)
    if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
        _log("Runebook gump did not open.", 33)
        return None
    lines = Gumps.LastGumpGetLineList()
    slot = _slot_from_lines(lines, rune_name)
    if slot is None:
        _log("Rune '%s' not found. Lines: %s" % (rune_name, lines), 33)
        # Do NOT send any gump action here — unknown buttons can drop runes.
    return slot


def _wait_for_mana_drop(mana_before, timeout_ms=3000):
    Timer.Create("rb_mana_wait", timeout_ms)
    while Timer.Check("rb_mana_wait"):
        if Player.Mana < mana_before:
            return True
        Misc.Pause(50)
    return False


# ─── Public API ───────────────────────────────────────────────────────────────

def find_runebook_by_label(label):
    """
    Return the first runebook in the player's backpack whose tooltip contains label
    (case-insensitive). Returns None if not found.
    """
    rb = Items.FindByID(RUNEBOOK_ITEM_ID, -1, Player.Backpack.Serial)
    if rb is None:
        return None
    props = Items.GetPropStringList(rb.Serial) or []
    if any(p.strip().lower() == label.strip().lower() for p in props):
        return rb
    return None


def travel_to_runebook(runebook, settle_delay=2000):
    """
    Travel to the runebook's default rune by casting directly at the item.
    Uses the same skill-priority logic as travel_to_named_rune but targets
    the runebook rather than navigating the gump — simpler when you just want
    the default rune (e.g. recalling home).

    Priority: Chivalry > SACRED_JOURNEY_MIN → Sacred Journey
              Overweight AND Magery > GATE_MAGERY_MIN → Gate
              Magery > RECALL_MAGERY_MIN → Recall
    """
    chiv       = Player.GetSkillValue('Chivalry')
    magery     = Player.GetSkillValue('Magery')
    overweight = Player.Weight >= Player.MaxWeight

    if chiv > SACRED_JOURNEY_MIN:
        spell = 'Sacred Journey'
    elif overweight and magery > GATE_MAGERY_MIN:
        spell = 'Gate Travel'
    elif magery > RECALL_MAGERY_MIN:
        spell = 'Recall'
    else:
        _log("Cannot travel: Magery %.1f and Chivalry %.1f both below thresholds." % (magery, chiv), 33)
        return False

    _log("Casting %s at runebook." % spell)
    mana_before = Player.Mana
    Spells.CastMagery(spell)
    if not Target.WaitForTarget(4000, False):
        _log("%s: target cursor never appeared." % spell, 33)
        return False
    Target.TargetExecute(runebook.Serial)
    if not _wait_for_mana_drop(mana_before):
        _log("%s fizzled — mana did not drop." % spell, 33)
        return False
    Misc.Pause(settle_delay)
    return True


def travel_to_named_rune(runebook, rune_name, settle_delay=2000):
    """
    Travel to rune_name using the best method available for the player's skills.

    Priority:
      1. Chivalry > SACRED_JOURNEY_MIN  → Sacred Journey (uses tithing, no reagents)
      2. Overweight AND Magery > GATE_MAGERY_MIN  → Gate Travel
      3. Magery > RECALL_MAGERY_MIN  → Recall
      4. None of the above  → log and return False

    Returns True on successful travel, False otherwise.
    """
    chiv       = Player.GetSkillValue('Chivalry')
    magery     = Player.GetSkillValue('Magery')
    overweight = Player.Weight >= Player.MaxWeight

    if chiv > SACRED_JOURNEY_MIN:
        _log("Using Sacred Journey (Chiv %.1f)." % chiv)
        return _sacred_journey(runebook, rune_name, settle_delay)
    elif overweight and magery > GATE_MAGERY_MIN:
        _log("Using Gate Travel (overweight, Magery %.1f)." % magery)
        return _gate(runebook, rune_name, settle_delay)
    elif magery > RECALL_MAGERY_MIN:
        _log("Using Recall (Magery %.1f)." % magery)
        return _recall(runebook, rune_name, settle_delay)
    else:
        _log("Cannot travel: Magery %.1f and Chivalry %.1f both below thresholds." % (magery, chiv), 33)
        return False


# ─── Rune enumeration ────────────────────────────────────────────────────────

def _extract_rune_block(lines):
    """
    Find the rune name block inside the full gump line list.
    The block is the last contiguous run of non-empty, non-digit, non-label entries
    with at most 16 items (one per runebook slot).
    Returns [(slot, name), ...] with slot as 0-based position in the block.
    """
    runs = []
    current = []
    for line in lines:
        entry = line.strip()
        if entry and not entry.isdigit() and entry.lower() not in _GUMP_LABELS:
            current.append(entry)
        else:
            if current:
                runs.append(list(current))
                current = []
    if current:
        runs.append(current)
    for run in reversed(runs):
        if len(run) <= 16:
            return [(i, name) for i, name in enumerate(run)]
    return []


def get_runebook_runes(runebook):
    """
    Open the runebook gump, read all rune names with their slot indices, then close.
    Returns [(slot, name), ...] for all occupied rune slots (0-based).
    """
    Items.UseItem(runebook)
    if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
        _log("Runebook gump timed out.", 33)
        return []
    lines = Gumps.LastGumpGetLineList()
    Gumps.SendAction(RUNEBOOK_GUMP_ID, 0)  # close gump
    return _extract_rune_block(lines)


def find_runes_matching(runebook, partial):
    """Return all (slot, name) where name contains partial (case-insensitive)."""
    return [(slot, name) for slot, name in get_runebook_runes(runebook)
            if partial.lower() in name.lower()]


def travel_to_slot(runebook, slot, settle_delay=2000):
    """
    Travel to a specific runebook slot using the best available skill method.
    Uses the same skill-priority logic as travel_to_named_rune.
    """
    chiv       = Player.GetSkillValue('Chivalry')
    magery     = Player.GetSkillValue('Magery')
    overweight = Player.Weight >= Player.MaxWeight

    if chiv > SACRED_JOURNEY_MIN:
        button_base = SACRED_JOURNEY_BUTTON_BASE
        needs_mana  = False
    elif overweight and magery > GATE_MAGERY_MIN:
        button_base = GATE_BUTTON_BASE
        needs_mana  = True
    elif magery > RECALL_MAGERY_MIN:
        button_base = RECALL_BUTTON_BASE
        needs_mana  = True
    else:
        _log("Cannot travel: skills too low.", 33)
        return False

    Items.UseItem(runebook)
    if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
        _log("Runebook gump timed out.", 33)
        return False

    mana_before = Player.Mana
    Gumps.SendAction(RUNEBOOK_GUMP_ID, button_base + slot)
    if needs_mana and not _wait_for_mana_drop(mana_before):
        _log("Travel fizzled — mana did not drop.", 33)
        return False
    Misc.Pause(settle_delay)
    return True


# ─── Direct gate by pre-known button ─────────────────────────────────────────

def gate_via_book(book, button_id, settle_delay=3000):
    """
    Open a runebook and fire a specific gate button.
    Use this when the button ID is already known (e.g. from exported JSON data).
    book may be an Item object or an integer serial.
    Returns True if the gump opened and the action was sent, False otherwise.
    """
    if isinstance(book, int):
        book = Items.FindBySerial(book)
    if book is None:
        _log("Runebook not found.", 33)
        return False
    Items.UseItem(book)
    if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
        _log("Runebook gump timed out.", 33)
        return False
    Gumps.SendAction(RUNEBOOK_GUMP_ID, button_id)
    Misc.Pause(settle_delay)
    return True


# ─── Travel method implementations ───────────────────────────────────────────

def _recall(runebook, rune_name, settle_delay):
    slot = _open_and_find_slot(runebook, rune_name)
    if slot is None:
        return False
    mana_before = Player.Mana
    Gumps.SendAction(RUNEBOOK_GUMP_ID, RECALL_BUTTON_BASE + slot)
    if not _wait_for_mana_drop(mana_before):
        _log("Recall fizzled — mana did not drop.", 33)
        return False
    Misc.Pause(settle_delay)
    return True


def _gate(runebook, rune_name, settle_delay):
    slot = _open_and_find_slot(runebook, rune_name)
    if slot is None:
        return False
    mana_before = Player.Mana
    Gumps.SendAction(RUNEBOOK_GUMP_ID, GATE_BUTTON_BASE + slot)
    if not _wait_for_mana_drop(mana_before):
        _log("Gate fizzled — mana did not drop.", 33)
        return False
    Misc.Pause(settle_delay)
    return True


def _sacred_journey(runebook, rune_name, settle_delay):
    slot = _open_and_find_slot(runebook, rune_name)
    if slot is None:
        return False
    # SACRED_JOURNEY_BUTTON_BASE is unconfirmed.
    # Record a macro: open runebook → click Sacred Journey for any rune → check button ID.
    # Then update SACRED_JOURNEY_BUTTON_BASE at the top of this file.
    Gumps.SendAction(RUNEBOOK_GUMP_ID, SACRED_JOURNEY_BUTTON_BASE + slot)
    Misc.Pause(settle_delay)
    return True
