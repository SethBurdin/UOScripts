pen = Items.FindByID(0x0FBF, -1, Player.Backpack.Serial)  # scribe's pen / pen and ink

if not pen:
    Misc.SendMessage("No scribe pen found.", 33)
    raise SystemExit

Items.UseItem(pen)

import os
import datetime

# Use a relative path for the output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'gump_logs')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

LOG_FILE = "gump_log_full.txt"


def log_gump_state(prefix=""):
    gump_id = Gumps.CurrentGump()
    if gump_id == 0:
        Misc.SendMessage("No gump open.")
        return
    gump_buttons = Gumps.GetButtons(gump_id)
    gump_texts = Gumps.GetTexts(gump_id)
    with open(LOG_FILE, "a") as f:
        f.write("\n==== {} {} ====".format(prefix, datetime.datetime.now()))
        f.write("\nGump ID: {} (hex: 0x{:X})\n".format(gump_id, gump_id))
        f.write("Button IDs and Texts:\n")
        for btn_id in gump_buttons:
            label = gump_texts.get(btn_id, "") if isinstance(gump_texts, dict) else ""
            f.write("  Button {}: {}\n".format(btn_id, label))
        f.write("All Texts:\n")
        for t in gump_texts.values() if isinstance(gump_texts, dict) else gump_texts:
            f.write("  {}\n".format(t))
        f.write("\n")

# New function: logs before and after a button press, waits for gump response
def log_gump_action(gump_id, button_id, prefix=""):
    log_gump_state(prefix + " BEFORE")
    Gumps.SendAction(gump_id, button_id)
    # Wait for a new gump (ID must change)
    old_id = gump_id
    timeout = 5000
    interval = 50
    waited = 0
    while waited < timeout:
        Misc.Pause(interval)
        new_id = Gumps.CurrentGump()
        if new_id != 0 and new_id != old_id:
            break
        waited += interval
    log_gump_state(prefix + " AFTER")


# Example usage:
# log_gump_action(CRAFT_GUMP_ID, group_btn, "GROUP SELECT")
# log_gump_action(CRAFT_GUMP_ID, spell_btn, "SPELL SELECT")

# You can still call log_gump_state() at any point to capture the current gump state.

if Gumps.WaitForGump(0, 5000):
    gid = Gumps.CurrentGump()
    gump_serial = Gumps.LastGumpSerial() if hasattr(Gumps, 'LastGumpSerial') else None
    gump_id = Gumps.LastGumpID() if hasattr(Gumps, 'LastGumpID') else None

    log_filename = 'gump_log_{}.txt'.format(datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    log_path = os.path.join(OUTPUT_DIR, log_filename)
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("Current Gump ID: {}\n".format(gid))
        if gump_serial is not None:
            f.write("Last Gump Serial: {}\n".format(gump_serial))
        if gump_id is not None:
            f.write("Last Gump ID: {}\n".format(gump_id))
        f.write("---- TEXT ----\n")
        for line in Gumps.LastGumpGetLineList():
            f.write(line + '\n')
        f.write("---- BUTTON IDS (attempted 0-100) ----\n")
        for btn in range(0, 101):
            try:
                text = Gumps.LastGumpGetLine(btn)
                if text:
                    f.write("Button {}: {}\n".format(btn, text))
            except Exception:
                continue
    Misc.SendMessage("Gump log written to {}".format(log_path), 68)
else:
    Misc.SendMessage("No gump opened.", 33)