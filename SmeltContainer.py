
from Scripts import config
from glossary.items.ores import ores
from glossary.crafting.blacksmithing import blacksmithTools, FindBlacksmithTool, blacksmithCraftables
from glossary.colors import colors
from utilities.items import FindItem, FindNumberOfItems, MoveItem


def SmeltItems( itemID ):
    '''
    Smelts all items in the player's backpack that match the item ID given
    Returns True if all items were smelted successfully, False if not all the items were smelted
    '''

    tool = FindBlacksmithTool( Player.Backpack )
    if tool == None:
        Player.HeadMessage( colors[ 'red' ], 'Ran out of tools!' )
        return False

    itemToSmelt = FindItem( itemID, Player.Backpack )
    while itemToSmelt != None and tool != None:
        # Make sure the tool isn't broken. If it is broken, this will return None
        tool = Items.FindBySerial( tool.Serial )
        if tool == None:
           tool = FindBlacksmithTool( Player.Backpack )
           if tool == None:
               Player.HeadMessage( colors[ 'red' ], 'Ran out of tools!' )
               return False

        Items.UseItem( tool )
        Gumps.WaitForGump( 949095101, 2000 )
        Gumps.SendAction( 949095101, 14 )

        Target.WaitForTarget( 2000, True )
        Target.TargetExecute( itemToSmelt.Serial )

        # Wait for the smelting to finish
        Misc.Pause( 1000 )

        # Close the Blacksmithing gump
        Gumps.WaitForGump( 949095101, 2000 )
        Gumps.SendAction( 949095101, 0 )

        itemToSmelt = FindItem( itemID, Player.Backpack )
        
SmeltItems( 0x0F61 )
Items.UseItemByID(0x0FBB,0x0000)
