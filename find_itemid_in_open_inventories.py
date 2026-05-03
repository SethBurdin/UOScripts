# find_itemid_in_open_inventories.py
# Razor Enhanced Python script
# Target any open container (including vendor bags if possible) and list all items by ItemID, hue, and serial.

vendor_container_serial = Target.PromptTarget("Target the vendor or player container/bag:")
vendor_container = Items.FindBySerial(vendor_container_serial)

if not vendor_container:
    Misc.SendMessage("Container not found.", 33)
else:
    Items.WaitForContents(vendor_container, 3000)
    Misc.Pause(1200)
    # Find all items in this container and all loaded subcontainers
    items = Items.FindAllByID(-1, -1, vendor_container.Serial, -1)
    if not items:
        Misc.SendMessage("No items found in container.", 33)
    else:
        Misc.SendMessage(f"Found {len(items)} items:", 0x40)
        for item in items:
            Misc.SendMessage(
                f"{item.Name} | ID: 0x{item.ItemID:04X} | Hue: 0x{item.Color:04X} | Serial: 0x{item.Serial:X}",
                68
            )
