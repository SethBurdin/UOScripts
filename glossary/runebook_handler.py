
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
SACRED_JOURNEY_CONFIRMED   = False # Set True once SACRED_JOURNEY_BUTTON_BASE is verified

# ─── Skill thresholds ─────────────────────────────────────────────────────────
RECALL_MAGERY_MIN    = 30   # Magery required to use Recall
GATE_MAGERY_MIN      = 90   # Magery required to use Gate (also requires overweight)
SACRED_JOURNEY_MIN   = 30   # Chivalry required to use Sacred Journey

GATE_ITEM_ID         = 0x0F6C  # Moongate portal spawned by Gate Travel spell
GATE_SCAN_RANGE      = 3       # tiles to search for the gate after casting
GATE_ENTER_TIMEOUT   = 5000    # ms to wait for the gate to appear

_GUMP_LABELS = {
    "rename book", "charges", "max charges",
    "drop rune", "set default", "recall", "gate travel", "sacred journey",
}


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


def _ensure_runebook_open(runebook):
    """Always open a fresh runebook gump. Returns True on success.
    Never reuses an existing open gump — the server may have already closed it,
    and sending SendAction on a server-closed gump causes a disconnect."""
    Items.UseItem(runebook)
    Misc.Pause(300)
    if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
        _log("Runebook gump did not open.", 33)
        return False
    return True


def _open_and_find_slot(runebook, rune_name):
    """Ensure the runebook gump is open and return the slot index for rune_name, or None."""
    if not _ensure_runebook_open(runebook):
        return None
    lines = Gumps.LastGumpGetLineList()
    slot = _slot_from_lines(lines, rune_name)
    if slot is None:
        _log("Rune '%s' not found. Lines: %s" % (rune_name, lines), 33)
        # Do NOT send any gump action here — unknown buttons can drop runes.
    return slot


def _wait_for_mana_drop(mana_before, timeout_ms=6000):
    Timer.Create("rb_mana_wait", timeout_ms)
    while Timer.Check("rb_mana_wait"):
        if Player.Mana < mana_before:
            return True
        Misc.Pause(50)
    return False


def _snapshot_nearby_gate():
    """Return the serial of any gate portal already in scan range, or None."""
    gate = Items.FindByID(GATE_ITEM_ID, -1, -1, GATE_SCAN_RANGE)
    return gate.Serial if gate is not None else None


def _enter_nearby_gate(exclude_serial=None):
    """Wait for a new gate portal to appear nearby and step through it. Returns True if entered."""
    Timer.Create("rb_gate_enter", GATE_ENTER_TIMEOUT)
    while Timer.Check("rb_gate_enter"):
        gate = Items.FindByID(GATE_ITEM_ID, -1, -1, GATE_SCAN_RANGE)
        if gate is not None and gate.Serial != exclude_serial:
            Items.UseItem(gate)
            Misc.Pause(600)
            return True
        Misc.Pause(100)
    _log("No new gate portal found within %d tiles after %dms." % (GATE_SCAN_RANGE, GATE_ENTER_TIMEOUT), 33)
    return False


# ─── Public API ───────────────────────────────────────────────────────────────

def find_runebook_by_label(label):
    """
    Return the first runebook in the player's backpack whose tooltip contains label
    (case-insensitive). Checks ALL runebooks, not just the first found.
    Returns None if not found.
    """
    if Player.Backpack is None:
        return None
    target = label.strip().lower()
    for item in (Player.Backpack.Contains or []):
        if item.ItemID != RUNEBOOK_ITEM_ID:
            continue
        props = Items.GetPropStringList(item.Serial) or []
        if any(target in p.strip().lower() for p in props):
            return item
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

    if chiv > SACRED_JOURNEY_MIN and SACRED_JOURNEY_CONFIRMED:
        spell = 'Sacred Journey'
    elif overweight and magery > GATE_MAGERY_MIN:
        spell = 'Gate Travel'
    elif magery > RECALL_MAGERY_MIN:
        spell = 'Recall'
    else:
        _log("Cannot travel: Magery %.1f and Chivalry %.1f both below thresholds." % (magery, chiv), 33)
        return False

    _log("Casting %s at runebook." % spell)
    existing_gate = _snapshot_nearby_gate() if spell == 'Gate Travel' else None
    mana_before = Player.Mana
    Spells.CastMagery(spell)
    if not Target.WaitForTarget(4000, False):
        _log("%s: target cursor never appeared." % spell, 33)
        return False
    Target.TargetExecute(runebook.Serial)
    if not _wait_for_mana_drop(mana_before):
        _log("%s fizzled — mana did not drop." % spell, 33)
        return False
    if spell == 'Gate Travel':
        if not _enter_nearby_gate(existing_gate):
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

    if chiv > SACRED_JOURNEY_MIN and SACRED_JOURNEY_CONFIRMED:
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
# LastGumpGetLine(n) is POSITIONAL — it returns line n from the full text dump,
# not button-associated text. Rune names sit at the END of that dump (~indices 85-100
# for a full 16-slot book). _extract_rune_block finds them by locating the last
# contiguous run of ≤16 name-like entries.

def _extract_rune_block(lines, book_name=''):
    """
    Extract rune names from the gump line list.

    The gump text includes the runebook's own name before the rune entries.
    Pass book_name (lowercase) to exclude it so slot indices stay correct.
    Coordinate strings start with digits and are skipped automatically.
    """
    candidates = []
    for line in lines:
        entry = line.strip()
        if not entry:
            continue
        if entry[0].isdigit():
            continue
        if entry.lower() in _GUMP_LABELS:
            continue
        if book_name and entry.lower() == book_name:
            continue
        candidates.append(entry)
        if len(candidates) == 16:
            break
    return [(i, name) for i, name in enumerate(candidates)]


def get_runebook_runes(runebook):
    """
    Open the runebook gump, extract all rune names and their slot indices.
    The gump is left open — the next travel call will open a fresh one.
    Returns [(slot, name), ...] for all occupied slots (0-based).
    """
    Items.UseItem(runebook)
    if not Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
        _log("Runebook gump timed out.", 33)
        return []
    lines = Gumps.LastGumpGetLineList()
    props = Items.GetPropStringList(runebook.Serial) or []
    book_name = props[0].strip().lower() if props else ''
    runes = _extract_rune_block(lines, book_name)
    _log("Parsed %d rune(s): %s" % (len(runes), [n for _, n in runes]))
    return runes


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

    if chiv > SACRED_JOURNEY_MIN and SACRED_JOURNEY_CONFIRMED:
        button_base = SACRED_JOURNEY_BUTTON_BASE
        needs_mana  = False
    elif overweight and magery > GATE_MAGERY_MIN:
        button_base = GATE_BUTTON_BASE
        needs_mana  = True
    elif magery > RECALL_MAGERY_MIN:
        button_base = RECALL_BUTTON_BASE
        needs_mana  = True
    else:
        # Consume a runebook charge directly — no spell skill or reagents required.
        _log("No spell skills — consuming runebook charge (slot %d)." % slot)
        button_base = RECALL_BUTTON_BASE
        needs_mana  = False

    if not _ensure_runebook_open(runebook):
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

    Explicitly closes any lingering runebook gump before opening the target book.
    Without this, WaitForGump returns immediately on a stale gump from a
    previously opened book (same gump ID 89), causing the button to fire on
    the wrong book's slot.
    """
    if isinstance(book, int):
        book = Items.FindBySerial(book)
    if book is None:
        _log("Runebook not found.", 33)
        return False
    if Gumps.HasGump():
        Gumps.SendAction(RUNEBOOK_GUMP_ID, 0)
        Misc.Pause(400)
    Items.UseItem(book)
    Misc.Pause(300)
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
    existing_gate = _snapshot_nearby_gate()
    mana_before = Player.Mana
    Gumps.SendAction(RUNEBOOK_GUMP_ID, GATE_BUTTON_BASE + slot)
    if not _wait_for_mana_drop(mana_before):
        _log("Gate fizzled — mana did not drop.", 33)
        return False
    if not _enter_nearby_gate(existing_gate):
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
