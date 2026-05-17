'''
General-purpose gump dumper — navigation-aware mode.

Usage:
  1. Run the script
  2. Target the item that opens the gump (e.g., smith's hammer, sewing kit)
  3. Script opens the gump fresh before each probe so it always starts
     from the top level — no getting lost inside a sub-category.
  4. Check gump_logs/ for the output file.

Config:
  PROBE_START    — first button ID to probe
  PROBE_END      — last button ID to probe
  PROBE_STEP     — step between probes (7 = category-spaced for crafting gumps,
                   1 = every button for fine-grained mapping within a category)
  PROBE_DELAY_MS — ms to wait after clicking each button
'''

import os, datetime

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gump_logs')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

PROBE_START    = 1
PROBE_END      = 100
PROBE_STEP     = 7      # use 1 for fine-grained item mapping within a single category
PROBE_DELAY_MS = 600


def current_lines():
    return list(Gumps.LastGumpGetLineList() or [])


def write_lines(f, lines, indent='  '):
    if lines:
        for i, line in enumerate(lines):
            f.write('%sline %3d: %s\n' % (indent, i, line))
    else:
        f.write('%s(no lines)\n' % indent)


def open_gump(tool_serial, expected_gid):
    if Gumps.HasGump() and Gumps.CurrentGump() == expected_gid:
        return True
    for _ in range(3):
        Items.UseItem(tool_serial)
        Misc.Pause(2000)
        if Gumps.HasGump() and Gumps.CurrentGump() == expected_gid:
            return True
        Misc.Pause(500)
    return False


# ── Prompt for tool ───────────────────────────────────────────────────────────

Misc.SendMessage('[gump-dump] Target the item that opens the gump:', 68)
_serial = Target.PromptTarget('Target the item that opens the gump:')
if not _serial or _serial == 0:
    Misc.SendMessage('[gump-dump] Cancelled.', 33)
    raise SystemExit

tool_serial = int(_serial)
tool_item = Items.FindBySerial(tool_serial)
tool_name = tool_item.Name if tool_item else ('0x%X' % tool_serial)
tool_slug = tool_name.lower().replace(' ', '_').replace("'", '').replace('"', '')

Misc.SendMessage('[gump-dump] Opening gump via %s...' % tool_name, 68)

Items.UseItem(tool_serial)
Misc.Pause(2000)

if not Gumps.HasGump():
    Misc.SendMessage('[gump-dump] Gump did not open — check the targeted item.', 33)
    raise SystemExit

gid = Gumps.CurrentGump()
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
log_path = os.path.join(OUTPUT_DIR, '%s_0x%X_%s.txt' % (tool_slug, gid, timestamp))
initial_lines = current_lines()

Misc.SendMessage('[gump-dump] Gump 0x%X — probing buttons %d-%d step %d...' % (
    gid, PROBE_START, PROBE_END, PROBE_STEP), 68)

# ── Probe ─────────────────────────────────────────────────────────────────────

with open(log_path, 'w', encoding='utf-8') as f:
    f.write('Gump ID : %d  (0x%X)\n' % (gid, gid))
    f.write('Captured: %s\n' % datetime.datetime.now())
    f.write('Tool    : %s (0x%X)\n' % (tool_name, tool_serial))
    f.write('Probe   : buttons %d-%d step %d\n' % (PROBE_START, PROBE_END, PROBE_STEP))

    f.write('\n=== INITIAL PAGE ===\n')
    write_lines(f, initial_lines)
    f.flush()

    f.write('\n=== BUTTON PROBE (only buttons that change content are shown) ===\n')
    f.flush()

    for btn in range(PROBE_START, PROBE_END + 1, PROBE_STEP):
        # Re-open fresh before each probe so we always start from the top-level page
        if not open_gump(tool_serial, gid):
            f.write('\n[could not reopen gump before button %d — stopping]\n' % btn)
            Misc.SendMessage('[gump-dump] Could not reopen gump — stopping.', 33)
            break

        Misc.Pause(300)
        before = current_lines()

        Gumps.SendAction(gid, btn)
        Misc.Pause(PROBE_DELAY_MS)

        if not Gumps.HasGump():
            Misc.Pause(1000)

        if not Gumps.HasGump():
            f.write('\n  [button %d — closed the gump]\n' % btn)
            continue

        after = current_lines()
        if after != before:
            f.write('\n  [button %d]\n' % btn)
            write_lines(f, after, indent='    ')
            f.flush()

Misc.SendMessage('[gump-dump] Done — %s' % log_path, 68)
