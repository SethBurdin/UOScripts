global ores
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.items.ores import ores
from glossary.colors import colors
import config
from utilities.items import FindItem, FindNumberOfItems, MoveItem


global oretype
global orecolor

def smeltOre():
      for ore in ores:
          oretype = FindItem( ores[ ore ].itemID, Player.Backpack )
          Journal.Clear()
          while oretype != None and Journal.SearchByName( 'there is not enough metal-bearing ore in this pile to make an ingot.', 'System' ):
            Items.UseItem( oretype )
            Target.WaitForTarget(2000,False)
           
            Target.TargetExecute(0x0000E89B)
            Misc.Pause(1500)
            oretype = FindItem( ores[ ore ].itemID, Player.Backpack )

#            
#def gateHome():
#    Items.UseItem(0x4052B274)
#    Gumps.WaitForGump(89, 10000)
#    Gumps.SendAction(89, 104)
#    Misc.Pause(2500)
#
#    Items.UseItemByID(0x0F6C,0x0000)
#    transferIgnots()
#
#    
#def transferIgnots():
#    Organizer.RunOnce('mining',0x402E4297,0x400A0BCD,900)            
#            
            
while not Player.WarMode:
    smeltOre()
 #   gateHome()
