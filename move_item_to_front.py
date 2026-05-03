# move_item_to_front.py
# Attempts to move a specific item (by serial) to the front/top of a targeted container.

# Set the serial of the item you want to move (replace with your actual serial)
ITEM_SERIAL_TO_MOVE = 0x400C1CCF  # Serial for mythical scroll of Animal Taming (115 Skill)

def main():
    container_serial = Target.PromptTarget("Target the container to move the item into (usually the same bag):")
    container = Items.FindBySerial(container_serial)
    if not container:
        Misc.SendMessage("Container not found.", 33)
        return
    item = Items.FindBySerial(ITEM_SERIAL_TO_MOVE)
    if not item:
        Misc.SendMessage(f"Item 0x{ITEM_SERIAL_TO_MOVE:X} not found.", 33)
        return
    # Single-click the item for tooltip/confirmation only
    Items.SingleClick(item)
    Misc.Pause(400)
    Misc.SendMessage(f"Single-clicked item 0x{ITEM_SERIAL_TO_MOVE:X} ({item.Name})", 0x40)
    Player.ChatSay("vendor buy")
    Target.WaitForTarget(3000)
    Target.TargetExecute(item.Serial)

    # Move the mouse cursor to the item's gump position (if available)
    pos = item.Position
    if pos:
        x = pos.X
        y = pos.Y
        Misc.SendMessage(f"Item gump position: X={x} Y={y} (move your mouse here in the container window)", 0x40)
        Misc.SendMessage(f"TIP: In most bags, (0,0) is the top-left. Try moving your mouse to X={x}, Y={y} inside the bag to find the scroll.", 0x44)
    else:
        Misc.SendMessage("Item position not available.", 33)

main()
