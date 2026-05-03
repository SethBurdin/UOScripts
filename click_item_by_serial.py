# click_item_by_serial.py
# Clicks (single-clicks) a specific item by serial, for debugging or tooltip purposes.

# Set the serial of the item you want to click (replace with your actual serial)
ITEM_SERIAL_TO_CLICK = 0x401070AE  # Example serial from your screenshot

def main():
    item = Items.FindBySerial(ITEM_SERIAL_TO_CLICK)
    if not item:
        Misc.SendMessage(f"Item 0x{ITEM_SERIAL_TO_CLICK:X} not found.", 33)
        return
    Items.SingleClick(item)
    Misc.Pause(400)
    Misc.SendMessage(f"Single-clicked item 0x{ITEM_SERIAL_TO_CLICK:X} ({item.Name})", 0x40)

main()
