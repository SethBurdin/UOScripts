
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.ores import ores 
from glossary.items.ingots import ingots
from glossary.colors import colors
import config
from utilities.items import FindItem, FindNumberOfItems, MoveItem


HomeBox = '0x400A0BCD'

def transferIgnots():
    for ingot in ingots:
        ingotStack = FindItem( ingots[ ingot ].itemID, Player.Backpack, ingots[ ingot ].color )
        amountBeforeMove = FindNumberOfItems( ingots [ingot].itemID, Player.Backpack, ingots[ ingot ].color )
        MoveItem( Items, Misc, ingotStack, 0x400A0BCD, 1 )
        ingotStack = Items.FindBySerial( ingotStack.Serial )
        amountInBag = FindNumberOfItems( ingots[ ingot ].itemID, Player.Backpack, ingots[ ingot ].color )
        while amountInBag != amountBeforeMove:
                amountBeforeMove = amountInBag
                Misc.SendMessage( '%s' % ingotStack )
                MoveItem( Items, Misc, ingotStack, 0x400A0BCD, 1 )
                ingotStack = Items.FindBySerial( ingotStack.Serial )
                amountInBag = FindNumberOfItems( ingots[ ingot ].itemID, Player.Backpack, ingots[ ingot ].color )
    
while not Player.WarMode:
    transferIgnots()