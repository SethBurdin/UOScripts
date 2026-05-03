import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import FindItem, FindNumberOfItems, MoveItem
from Scripts import config
from glossary.colors import colors
from glossary.items.ores import ores
# global ores

# global oretype


def smeltOre():
    for ore in ores:
        try:
            oretype = FindItem(ores[ore].itemID, Player.Backpack)
            orenum = FindNumberOfItems(
                ores[ore].itemID, Player.Backpack, ores[ore].color)
            # if orenum > 2:
            Items.UseItem(oretype)
            Target.WaitForTarget(600, False)
            Target.TargetExecute(0x0000E89B)
            Misc.Pause(600)
            oretype = None

        except:
            # oretype = None
            Player.HeadMessage(colors['red'], 'Excepted out of smeltOre')
            # print()
            # return

        # Feature request inspect count of oretype before attempting to melt if less than 4 none it.
    # if oretype == None and Player.MaxWeight - Player.Weight < 25:
    #     gateHome()
    #     Misc.Pause(3000)
    #     transferIngots()
    #     Misc.Pause(9000)
    #     transferIngots()
    #     Misc.Pause(3000)


def checkWeight():
    if Player.Weight <= Player.MaxWeight:
        pickaxe = FindItem(0x0E86, Player.Backpack)
        if pickaxe == None:
            Player.HeadMessage(colors['red'], 'You\'re out of pickaxes!')
            Misc.Pause(600)
            gateHome()

            # getPickaxes()
    # elif Player.Weight > Player.MaxWeight:
    #      smeltOre()


def castGate():
    Items.UseItem(0x401DE6F5)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 114)
    Misc.Pause(4500)


def gateHome():
    castGate()
    if Player.Mana < Player.ManaMax:
        gateFilter = Items.Filter()
        gateFilter.RangeMin = 0
        gateFilter.RangeMax = 1

        UseIt = Items.ApplyFilter(gateFilter)
        for items in UseIt:
            Items.UseItem(items)
    else:
        castGate()


def transferIngots():
    Organizer.RunOnce('mining', 0x402E4297, 0x408457F5, 900)
    Misc.Pause(9000)
    # gotoNextMingLoc()


def gotoNextMingLoc():
    Player.ChatSay(690, "all guard me")
    Player.ChatSay(690, "all guard me")
    Items.UseItem(0x401DE6F5)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 55)
    Misc.Pause(1500)
    # Feature Request 001 ## Add Support to run through pages of runebook.
    Mobiles.UseMobile(0x0002F08F)


def getPickaxes():
    Items.UseItem(0x401DE6F5)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 56)
    Misc.Pause(4000)
    Misc.WaitForContext(0x00004B30, 10000)
    Misc.ContextReply(0x00004B30, 1)
    Misc.Pause(3000)
    Items.UseItem(0x4052B274)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 55)


def mine():
    Journal.Clear()
    if Player.Weight < 477:
        SafePlace = {}
        SafePlace = Player.Position
        # global a, b, c
        a = Player.Position.X - 1
        b = Player.Position.Y
        c = Player.Position.Z
        Items.UseItemByID(0x0E86, 0x0000)
        Target.WaitForTarget(1000, True)
        Target.TargetExecute(a, b, c, 0x0000)
        Misc.Pause(1800)
        Misc.SendMessage(Player.Position)
    elif Player.Weight >= 477:
        smeltOre()


while not Player.WarMode:

    if Player.Weight < Player.MaxWeight or not Journal.SearchByName('There is no metal here to mine.', 'System'):
        checkWeight()
        mine()
    else:
        # Player.Weight > Player.MaxWeight:
        # smeltOre()
        gateHome()
        break
