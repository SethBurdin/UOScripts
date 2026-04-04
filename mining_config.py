# ─────────────────────────────────────────────────────────────────────────────
# mining_config.py
# Configuration for the mining automation script (mining.py).
# Edit these values to tune the script's behaviour without touching the logic.
# ─────────────────────────────────────────────────────────────────────────────

# Player weight threshold (stones).  Once the player hits this limit, all ore
# is transferred to the pack animal before mining continues.
weight_transfer_threshold = 400

# Ore units to process per smelt pass.  The smelt loop retries until all ore
# is gone, so this effectively limits how much the server must handle at once.
smelt_batch_size = 20

# ── Timing ───────────────────────────────────────────────────────────────────

# Pause (ms) after each mine swing – covers animation + server round-trip.
pause_after_mine = 1600

# Pause (ms) after each smelt operation.
pause_after_smelt = 1200

# Pause (ms) after each Items.Move call when transferring ore to the mount.
pause_after_transfer = 700

# Small pause (ms) at the bottom of every main loop iteration.
loop_delay = 100

# ── Directions ───────────────────────────────────────────────────────────────
# The script tries these (dx, dy) offsets from Player.Position in order when
# the current tile has no ore or cannot be mined.  It stops and reports when
# every direction has been exhausted consecutively.
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
