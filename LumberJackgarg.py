
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import FindItem, FindNumberOfItems, MoveItem
from glossary.colors import colors
from glossary.items.wood import wood
from Scripts import config

global chopped
chopped = False


def getloc():
    global a
    global b
    global c
    a = Player.Position.X - 1
    b = Player.Position.Y - 1
    c = Player.Position.Z

# def putAway():
    # if Player.Position.X = "74o 0" + "'n" and Player.Position.Y =  "40o 59" + "'w":


def ChopItems(itemID):
    '''
    Smelts all items in the player's backpack that match the item ID given
    Returns True if all items were smelted successfully, False if not all the items were smelted
    '''
    try:
        chopped = True
        itemTochop = FindItem(0x1BDD, Player.Backpack)
        while not itemTochop == None:
            Items.UseItem(0x40128A64)
            Target.WaitForTarget(2000, True)
            itemTochop = FindItem(0x1BDD, Player.Backpack)
            # for log in itemTochop:
            Target.TargetExecute(itemTochop.Serial)
            Misc.Pause(1000)
        while itemTochop == None:
            # chopped = True
            break

    except:
        Misc.SendMessage("No more choppin")
        itemTochop = None


def treeinspector():
    global sourceBoxItem
    sourceBoxItem = Target.PromptTarget(
        'Select container to move items out of')
    # sourceBoxItem = Items.FindBySerial( sourceBox )
    # item.Hue ==


def alltrees():
    try:
        Target.TargetExecute(a, b, c, 0x12C2)
    except:
        Items.UseItemByID(0x0F43, 0x0000)
        Target.TargetExecute(a, b, c, 0x0CD0)
    try:
        Items.UseItemByID(0x0F43, 0x0000)
        Target.TargetExecute(a, b, c, 0x0CDD)
    except:
        Items.UseItemByID(0x0F43, 0x0000)
        Target.TargetExecute(a, b, c, 0x0CDE)


def goHome():
    # Record of Axin Recalling Home
    Items.UseItem(0x401DE817)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 76)
    Misc.Pause(2000)
    # Items.UseItem(0x408457F5)
    Organizer.RunOnce('gather', 0x40123471, 0x408457F5, 250)
    Misc.Pause(1000)
    Items.UseItem(0x401DE817)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 77)


def lj():
    Items.UseItem(0x40128A64)
    Misc.Pause(2200)


def lf():
    Journal.Clear()
    # chopped = False
    while Player.Weight < 400:
        lj()
    while Player.Weight > 401:
        # chopped = True
        Misc.SendMessage("Start Log chop")
        try:
            chopped = True
            itemTochop = FindItem(0x1BDD, Player.Backpack)
            ChopItems(itemTochop)
            Misc.Pause(500)
            # chopped = True
            break

        except:
            Misc.SendMessage(Exception)
            Misc.SendMessage("No more choppin")
            Misc.Pause(1000)
    while Player.Weight > 401 and chopped == True:
        goHome()
        chopped = False
        Misc.Pause(1000)
        Player.ChatSay(690, "britain moongate")
        return
        # break


while not Player.WarMode:
    lf()
