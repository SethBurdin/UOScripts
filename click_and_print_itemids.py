# click_and_print_itemids.py
# Clicks every item in a targeted container and prints name, ItemID, and serial.

def click_all_items(container):
    Items.UseItem(container)
    Items.WaitForContents(container, 3000)
    Misc.Pause(1200)
    contents = list(container.Contains) if container.Contains else []
    for item in contents:
        Items.SingleClick(item)
        Misc.Pause(400)
        # Print all available info for debugging
        Misc.SendMessage(
            f"Clicked: {item.Name} | ItemID: 0x{item.ItemID:04X} ({item.ItemID}) | Serial: 0x{item.Serial:X} | Hue: 0x{item.Color:04X}",
            0x3F
        )
        # Try to print tooltip property lines as well
        Items.WaitForProps(item, 2000)
        props = Items.GetPropStringList(item.Serial)
        if props:
            for p in props:
                Misc.SendMessage(f"  Prop: {p}", 0x48)


def main():
    serial = Target.PromptTarget("Target the container to click through:")
    container = Items.FindBySerial(serial)
    if not container:
        Misc.SendMessage("Container not found.", 33)
        return
    click_all_items(container)

main()
