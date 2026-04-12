'''
Description: Extractor -- one-shot helper for players who need a gate.
    Reads the player's current tile coordinates and broadcasts a single
    "gate <X> <Y>" command over party chat, then exits immediately.

    The gatekeeper (util_gatekeeper.py) receives the command, resolves
    the nearest rune, and opens the gate.  This script does not need to
    know anything about runebooks.

    Usage:
        Stand anywhere on the map and run this script once.
        The gatekeeper will open a gate to the nearest rune.
'''

x = Player.Position.X
y = Player.Position.Y

Player.ChatParty('gate %d %d' % (x, y))
