# stack_gold.py
# Consolidates gold stacks in a container into piles of 60,000.
# Each pass picks the largest partial stack as destination and the smallest
# partial stack as source, filling until only one partial remains.

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors

GOLD_ID    = 0x0EED
GOLD_MAX   = 60000
PAUSE_MOVE = 800


def log(msg, color=None):
    Misc.SendMessage('[stack-gold] ' + msg, color or colors['cyan'])


def stack_gold(container):
    Items.UseItem(container)
    Items.WaitForContents(container, 3000)
    Misc.Pause(500)

    moves = 0
    while True:
        stacks = sorted(
            [i for i in (container.Contains or []) if i.ItemID == GOLD_ID],
            key=lambda s: s.Amount
        )

        if len(stacks) < 2:
            break

        # Destination: the largest partial stack (has the most room to fill)
        dest = next((s for s in reversed(stacks) if s.Amount < GOLD_MAX), None)
        if dest is None:
            break  # every stack is already at 60k

        # Source: the smallest partial stack that isn't the destination
        src = next((s for s in stacks if s.Serial != dest.Serial and s.Amount < GOLD_MAX), None)
        if src is None:
            break  # only one partial stack remains — nothing left to merge

        amount = min(src.Amount, GOLD_MAX - dest.Amount)
        Items.Move(src, dest, amount)
        Misc.Pause(PAUSE_MOVE)
        moves += 1

    stacks = [i for i in (container.Contains or []) if i.ItemID == GOLD_ID]
    total  = sum(s.Amount for s in stacks)
    log('Done. %d move(s), %d stack(s), %d total gold.' % (moves, len(stacks), total))


log('Target the container to stack gold in.')
serial = Target.PromptTarget('Target the container:')
if serial and serial != 0:
    box = Items.FindBySerial(serial)
    if box is None:
        log('Container not found.', colors['red'])
    else:
        stack_gold(box)
