'''
Description: Bank Gold — recalls home, pulls up to 180k gold from the storage
    container into the player's backpack, recalls to the bank rune, then transfers
    the gold from the backpack into the nearby pack beetle.
'''

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
from glossary.runebook_handler import (
    find_runebook_by_label, find_runes_matching,
    travel_to_slot, RUNEBOOK_ITEM_ID,
)

GOLD_ID         = 0x0EED
DEST_SERIAL     = 0x400B404A
GOLD_TARGET     = 180000
RECALL_DELAY    = 3000
HOME_RUNE_NAME  = 'new home'   # name of the home rune inside the 'Home' runebook
BANK_RUNE_NAME  = 'bank'   # name of the bank rune inside the 'Home' runebook


def FindPackBeetle():
    filt          = Mobiles.Filter()
    filt.RangeMax = 10
    filt.IsHuman  = False
    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial:
            continue
        if mob.Backpack is not None:
            return mob
    return None


def _action_wait_blocked():
    return Journal.Search('You must wait')


def _open_container(container):
    '''Open a container, retrying on rate-limit or if contents never arrive.'''
    for attempt in range(1, 7):
        Journal.Clear()
        Items.UseItem(container)
        Misc.Pause(900)
        if _action_wait_blocked():
            Misc.SendMessage('[bank] Rate-limited (attempt %d) — waiting...' % attempt, colors['yellow'])
            Misc.Pause(2000)
            continue
        if Items.WaitForContents(container, 3000):
            Misc.Pause(300)
            return True
        Misc.SendMessage('[bank] Contents not received (attempt %d) — retrying...' % attempt, colors['yellow'])
        Misc.Pause(1000)
    Misc.SendMessage('[bank] Could not load container contents.', colors['red'])
    return False



def BankGold():
    # ── 1. Locate beetle ─────────────────────────────────────────────────────
    beetle = FindPackBeetle()
    if beetle is None:
        Misc.SendMessage('No pack beetle found within 10 tiles.', colors['red'])
        return
    beetle_serial = beetle.Serial
    Misc.SendMessage('Found beetle: %s (0x%X).' % (beetle.Name, beetle.Serial), colors['cyan'])

    # ── 2. Find Home runebook ─────────────────────────────────────────────────
    runebook = find_runebook_by_label('Home')
    if runebook is None:
        Misc.SendMessage("No runebook labeled 'Home' found — target one manually.", colors['yellow'])
        rb_serial = Target.PromptTarget('Target the Home runebook:')
        runebook  = Items.FindBySerial(rb_serial)
        if runebook is None or runebook.ItemID != RUNEBOOK_ITEM_ID:
            Misc.SendMessage('That is not a runebook.', colors['red'])
            return

    # ── 3. Recall home ───────────────────────────────────────────────────────
    home_spots = find_runes_matching(runebook, HOME_RUNE_NAME)
    if not home_spots:
        Misc.SendMessage("No rune named '%s' in Home runebook." % HOME_RUNE_NAME, colors['red'])
        return
    home_slot = home_spots[0][0]
    Misc.SendMessage('Recalling home (slot %d)...' % home_slot, colors['cyan'])
    if not travel_to_slot(runebook, home_slot, RECALL_DELAY):
        Misc.SendMessage('Travel to home failed.', colors['red'])
        return

    for _ in range(2):
        Player.Walk('North')
        Misc.Pause(400)

    # ── 4. Find beetle, open its pack first, then open chest as active container
    # Opening beetle first loads its serial into the client cache.
    # Opening the chest second makes it the active container so moves out of it work.
    # This avoids staging gold through the player's backpack (no weight limit hit).
    beetle = Mobiles.FindBySerial(beetle_serial)
    if beetle is None or beetle.Backpack is None:
        Misc.SendMessage('Beetle not found.', colors['red'])
        return

    if not _open_container(beetle.Backpack):
        return

    dest = Items.FindBySerial(DEST_SERIAL)
    if dest is None:
        Misc.SendMessage('Storage container (0x%X) not in range.' % DEST_SERIAL, colors['red'])
        return

    if not _open_container(dest):
        return

    # ── 5. Move gold directly from chest into beetle ──────────────────────────
    pulled = 0
    while pulled < GOLD_TARGET:
        gold = Items.FindByID(GOLD_ID, -1, DEST_SERIAL)
        if gold is None:
            break
        want          = min(gold.Amount, GOLD_TARGET - pulled)
        before_amount = gold.Amount
        Misc.SendMessage('[bank] Moving %d gold to beetle...' % want, colors['cyan'])
        actually_moved = 0
        for attempt in range(1, 7):
            Journal.Clear()
            Items.Move(gold, beetle.Backpack, want)
            Misc.Pause(900)
            if _action_wait_blocked():
                Misc.SendMessage('[bank] Move rate-limited (attempt %d) — waiting...' % attempt, colors['yellow'])
                Misc.Pause(2000)
                continue
            # Check if the same serial is still sitting in the chest.
            # FindBySerial would also find the gold in the beetle's pack —
            # FindByID restricted to DEST_SERIAL only matches if it's still there.
            still_in_chest = Items.FindByID(GOLD_ID, -1, DEST_SERIAL)
            if still_in_chest is not None and still_in_chest.Serial == gold.Serial:
                actually_moved = before_amount - still_in_chest.Amount
            else:
                actually_moved = want  # stack left the chest entirely
            break
        if actually_moved <= 0:
            Misc.SendMessage('[bank] Move rejected (beetle full or out of range?) — stopping.', colors['red'])
            break
        pulled += actually_moved
        Misc.SendMessage('[bank] Moved %d (total %d / %d).' % (actually_moved, pulled, GOLD_TARGET), colors['cyan'])

    if pulled == 0:
        Misc.SendMessage('No gold moved.', colors['yellow'])
        return
    Misc.SendMessage('Loaded %d gold into beetle.' % pulled, colors['cyan'])

    # ── 6. Look up bank slot and recall ──────────────────────────────────────
    runebook = find_runebook_by_label('Home')
    if runebook is None:
        Misc.SendMessage("Lost 'Home' runebook.", colors['red'])
        return

    bank_spots = find_runes_matching(runebook, BANK_RUNE_NAME)
    if not bank_spots:
        Misc.SendMessage("No rune named '%s' in Home runebook." % BANK_RUNE_NAME, colors['red'])
        return
    bank_slot = bank_spots[0][0]

    Misc.SendMessage('Recalling to bank (slot %d)...' % bank_slot, colors['cyan'])
    if not travel_to_slot(runebook, bank_slot, RECALL_DELAY):
        Misc.SendMessage('Travel to bank failed.', colors['red'])
        return

    # ── 7. Open bank box ──────────────────────────────────────────────────────
    Player.ChatSay(colors['cyan'], 'bank')
    Misc.Pause(2000)

    bank_box = Player.Bank
    if bank_box is None:
        Misc.SendMessage('Bank box did not open.', colors['red'])
        return

    # ── 8. Reacquire beetle and deposit gold ──────────────────────────────────
    beetle = Mobiles.FindBySerial(beetle_serial)
    if beetle is None or beetle.Backpack is None:
        Misc.SendMessage('Beetle not found at bank.', colors['red'])
        return

    if not _open_container(beetle.Backpack):
        return

    deposited = 0
    while True:
        gold = Items.FindByID(GOLD_ID, -1, beetle.Backpack.Serial)
        if gold is None:
            break
        want          = gold.Amount
        before_amount = gold.Amount
        Misc.SendMessage('[bank] Depositing %d gold...' % want, colors['cyan'])
        actually_deposited = 0
        for attempt in range(1, 7):
            Journal.Clear()
            Items.Move(gold, bank_box, want)
            Misc.Pause(900)
            if _action_wait_blocked():
                Misc.SendMessage('[bank] Deposit rate-limited (attempt %d) — waiting...' % attempt, colors['yellow'])
                Misc.Pause(2000)
                continue
            still_in_beetle = Items.FindByID(GOLD_ID, -1, beetle.Backpack.Serial)
            if still_in_beetle is not None and still_in_beetle.Serial == gold.Serial:
                actually_deposited = before_amount - still_in_beetle.Amount
            else:
                actually_deposited = want
            break
        if actually_deposited <= 0:
            Misc.SendMessage('[bank] Deposit rejected — stopping.', colors['red'])
            break
        deposited += actually_deposited
        Misc.SendMessage('[bank] Deposited %d (total %d / %d).' % (actually_deposited, deposited, pulled), colors['cyan'])

    Misc.SendMessage('Done — banked %d gold.' % deposited, colors['green'])


BankGold()
