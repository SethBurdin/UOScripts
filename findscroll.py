# findscroll.py
# Razor Enhanced script to list all items in a targeted vendor container, print their names/serials, and optionally move a chosen item to the top layer.

# IDE IntelliSense only – never executes inside Razor Enhanced
if False:
    from razorenhanced_stubs import *

def log(msg, color=68):
    Misc.SendMessage("[findscroll] " + msg, color)

# Set this to the serial of the container you want to inspect (from your macro)
HARDCODED_CONTAINER_SERIAL = 0x000049F1

def main():
    log("Using hardcoded container serial: 0x%X" % HARDCODED_CONTAINER_SERIAL, 0x53)
    container = Items.FindBySerial(HARDCODED_CONTAINER_SERIAL)
    if container is None:
        log("Could not find targeted container.", 0x25)
        return
    Items.UseItem(container)
    Items.WaitForContents(container, 3000)
    Misc.Pause(1200)
    contents = list(container.Contains) if container.Contains else []
    if not contents:
        log("Container is empty.", 0x25)
        return
    log(f"Found {len(contents)} items in container:", 0x40)
    for idx, item in enumerate(contents):
        Misc.SendMessage(f"[{idx+1}] {item.Name} (0x{item.ItemID:04X}) x{item.Amount} Serial: 0x{item.Serial:X}", 0x3F)
    log("Type the number of the item to move to the top layer, or 0 to skip.", 0x53)
    choice = Misc.ReadSharedValue("findscroll_choice") if Misc.CheckSharedValue("findscroll_choice") else None
    if choice is None:
        choice = Misc.InputBox("Enter item number to move (0 to skip):")
        try:
            choice = int(choice)
        except:
            log("Invalid input. Stopping.", 0x25)
            return
        Misc.SetSharedValue("findscroll_choice", choice)
    if choice and 1 <= choice <= len(contents):
        item = contents[choice-1]
        log(f"Moving {item.Name} (0x{item.ItemID:04X}) to top layer...", 0x40)
        Items.Move(item, container, item.Amount)
        Misc.Pause(1200)
        log("Move complete. You can now easily target this item for purchase or further action.", 0x40)
    else:
        log("No item moved.", 0x3F)

main()
