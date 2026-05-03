# click_all_items_in_container.py
# Razor Enhanced Python script
# Clicks every item in a targeted container and prints the name of each item.

def click_all_items(container):
    Items.UseItem(container)
    Items.WaitForContents(container, 3000)
    Misc.Pause(1200)
    contents = list(container.Contains) if container.Contains else []
    for item in contents:
        Items.SingleClick(item)
        Misc.Pause(400)
        Misc.SendMessage(f"Clicked: {item.Name}", 0x3F)

def main():
    serial = Target.PromptTarget("Target the container to click through:")
    container = Items.FindBySerial(serial)
    if not container:
        Misc.SendMessage("Container not found.", 33)
        return
    click_all_items(container)

main()
