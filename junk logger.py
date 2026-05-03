
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.ores import wood 

from glossary.colors import colors
import config
from utilities.items import FindItem, FindNumberOfItems, MoveItem





HomeBox = '0x400A0BCD'

def transferLogs():
    for log in logs:
        Items.UseItem(0x40502AAC)
        Target.WaitForTarget(10000, False)
        Target.
        logStack = FindItem( logs[ log ].itemID, Player.Backpack, logs[ log ].color )
        amountBeforeMove = FindNumberOfItems( logs [log].itemID, Player.Backpack, logs[ log ].color )
        MoveItem( Items, Misc, logStack, 0x400A0BCD, 1 )
        logStack = Items.FindBySerial( logStack.Serial )
        amountInBag = FindNumberOfItems( logs[ log ].itemID, Player.Backpack, logs[ log ].color )
        while amountInBag != amountBeforeMove:
                amountBeforeMove = amountInBag
                Misc.SendMessage( '%s' % logStack )
                MoveItem( Items, Misc, logStack, 0x400A0BCD, 1 )
                logStack = Items.FindBySerial( logStack.Serial )
                amountInBag = FindNumberOfItems( logs[ log ].itemID, Player.Backpack, logs[ log ].color )
    
while not Player.WarMode:
    transferLogs()