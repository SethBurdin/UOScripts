'''
Interactive gump mapper — open any gump and navigate freely.
Every time the gump content changes a new step is logged.

Usage:
  1. Run the script
  2. Open any gump (sewing kit, runebook, vendor, etc.)
  3. Click through the menus at your own pace
  4. Close the gump (or let the idle timeout fire) to finish
  5. Check gump_logs/ for the output — each step shows the full line list
     so you can see exactly what page each button leads to
'''

import os, datetime

if False:
    from razorenhanced_stubs import *

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gump_logs')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

POLL_MS       = 150    # how often to check for gump changes
IDLE_TIMEOUT  = 20000  # ms — stop if no gump activity for this long


def _lines():
    return list(Gumps.LastGumpGetLineList() or [])


def _write_step(f, step_label, lines):
    f.write('\n=== %s ===\n' % step_label)
    if lines:
        for i, line in enumerate(lines):
            f.write('  line %3d: %s\n' % (i, line))
    else:
        f.write('  (no lines)\n')
    f.flush()


# ── Wait for player to open a gump ───────────────────────────────────────────

Misc.SendMessage('[gump-map] Open any gump to start recording...', 68)
Timer.Create('gmap_idle', IDLE_TIMEOUT)

while not Gumps.HasGump():
    if not Timer.Check('gmap_idle'):
        Misc.SendMessage('[gump-map] No gump opened — exiting.', 33)
        raise SystemExit
    Misc.Pause(POLL_MS)

# ── Set up log file ───────────────────────────────────────────────────────────

gid       = int(Gumps.CurrentGump())
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_path  = os.path.join(OUTPUT_DIR, 'gump_map_0x%X_%s.txt' % (gid, timestamp))

Misc.SendMessage('[gump-map] Recording gump 0x%X — navigate freely.' % gid, 68)
Misc.SendMessage('[gump-map] Log: %s' % log_path, 68)

prev_lines = _lines()
step       = 0

with open(log_path, 'w', encoding='utf-8') as f:
    f.write('Gump    : %d (0x%X)\n' % (gid, gid))
    f.write('Started : %s\n' % datetime.datetime.now())

    _write_step(f, 'STEP 0 — initial', prev_lines)
    Timer.Create('gmap_idle', IDLE_TIMEOUT)

    while True:
        Misc.Pause(POLL_MS)

        if not Gumps.HasGump():
            f.write('\n--- [gump closed] ---\n')
            f.flush()
            Misc.SendMessage('[gump-map] Gump closed. Waiting for next gump...', 68)
            Timer.Create('gmap_idle', IDLE_TIMEOUT)

            while not Gumps.HasGump():
                if not Timer.Check('gmap_idle'):
                    f.write('\n[idle timeout — done]\n')
                    Misc.SendMessage('[gump-map] Done — %s' % log_path, 68)
                    raise SystemExit
                Misc.Pause(POLL_MS)

            new_gid = int(Gumps.CurrentGump())
            if new_gid != gid:
                f.write('\n--- [new gump 0x%X] ---\n' % new_gid)
                f.flush()
                gid = new_gid

            prev_lines = _lines()
            step += 1
            _write_step(f, 'STEP %d — after reopen' % step, prev_lines)
            Timer.Create('gmap_idle', IDLE_TIMEOUT)
            continue

        curr_lines = _lines()
        if curr_lines != prev_lines:
            step += 1
            _write_step(f, 'STEP %d' % step, curr_lines)
            Misc.SendMessage('[gump-map] Step %d recorded.' % step, 68)
            prev_lines = curr_lines
            Timer.Create('gmap_idle', IDLE_TIMEOUT)
