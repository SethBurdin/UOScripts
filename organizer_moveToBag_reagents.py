import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import FindItem, MoveItem
from glossary.items.reagents import reagents
import config

reagentsBagSharedValue = 'reagentsBag'

if not Misc.CheckSharedValue( reagentsBagSharedValue ):
    reagentsBag = Target.PromptTarget( 'Select bag to move the reagents into' )
    Misc.SetSharedValue( reagentsBagSharedValue, reagentsBag )

reagentsBag = Misc.ReadSharedValue( reagentsBagSharedValue )
if reagentsBag == None or Items.FindBySerial( reagentsBag ) == None:
    Player.HeadMessage( 'Can\'t find reagents bag! Clearing stored bag, please run again' )
    Misc.RemoveSharedValue( reagentsBagSharedValue )
    Stop

reagentsBag = Items.FindBySerial( reagentsBag )

def MoveReagentsToBag():
    for reagent in reagents:
        reagentItemID = reagents[ reagent ].itemID
        reagentStack = FindItem( reagentItemID, Player.Backpack, ignoreContainer = [ reagentsBag.Serial ] )
        while reagentStack != None:
            MoveItem( Items, Misc, reagentStack, reagentsBag )
            reagentStack = FindItem( reagentItemID, Player.Backpack, ignoreContainer = [ reagentsBag.Serial ] )

MoveReagentsToBag()
