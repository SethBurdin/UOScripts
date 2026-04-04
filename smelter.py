

Items.UseItemByID(0x0FBB,0x0000)
#Misc.Pause(500)
#Gumps.WaitForGump(949095101, 1000)
#Gumps.SendAction(949095101, 14)
#Target.TargetExecute(Items.FindByID(0x1439,0x0000,0x401DF062,0,False))
#

#itemToSmelt.numerables = Items.Filter( Items.GetImage(0x1439,0x0000), 0x401DF062 )
#itemToSmelt.List = Items.Container.ItemID(0x0E76)

# def getitems():
#     itemToSmelt = ()
#     try:
#         itemToSmelt = Items.FindByID(0x1439,0x0000,0x401DF062,0,False)
#         return itemToSmelt
#     catch:
#         itemToSmelt = Items.FindByID(0x1441,0x0000,0x401DF062,0,False)
#         return itemToSmelt

itemToSmelt = ()
itemToSmelt2 = ()
# itemToSmelt.Filter1 =  "0x1439"
# itemToSmelt2.Filter2 =  "0x1441"
itemToSmelt =  Items.FindByID(0x1439,0x0000,0x401DF062,0,False)
itemToSmelt2 =  Items.FindByID(0x1441,0x0000,0x401DF062,0,False)


while itemToSmelt != None and itemToSmelt2 != None:
    
        Target.WaitForTarget(1000, False)
        Gumps.SendAction(949095101, 14)
        Gumps.WaitForGump(949095101, 1000)
        Target.TargetExecute(itemToSmelt)
        Misc.SendMessage(len(itemToSmelt))
    # elif len(itemToSmelt2) > 0:
    #     Target.WaitForTarget(1000, False)
    #     Gumps.SendAction(949095101, 14)
    #     Gumps.WaitForGump(949095101, 1000)
    #     Target.TargetExecute(itemToSmelt)
    #     Misc.SendMessage(len(itemToSmelt))
        

# Target.TargetExecute(itemToSmelt)
#     elif itemToSmelt = itemToSmelt = Items.FindByID(itemToSmelt.Filter1,0x0000,0x401DF062,0,False):
#         return itemToSmelt





# Target.WaitForTarget(1000, False)
# Gumps.SendAction(949095101, 14)
# Gumps.WaitForGump(949095101, 1000

# Target.TargetExecute(itemToSmelt)

    



#itemToSmelt()
#for smeltme in itemToSmelt:
#    Target.WaitForTarget(10000, False)
#    Gumps.SendAction(949095101, 14)
#    Target.TargetExecute(smeltme)
#
                    
                   # filter = itemID.Filter()
#                    filter.Enabled = True
#                    filter.OnGround = True
#                    filter.Movable = True
#                    filter.RangeMax = 3
#                    filter.IsCorpse = True


#Items.FindByID(itemid,color,container,range,considerIgnoreList)
#maulfromtype = Items.FindByID(0x401DF062,0x0000,0x40783510,2,considerIgnoreList)
#Target.GetTargetFromList(maulfromtype)
#for object in Items.FindByID(0x143B,0x0000,0x401DF062,2,considerIgnoreList):
#    try:
#        Misc.SendMessage(object)
#        Gumps.SendAction(949095101, 14)
##        Target.WaitForTarget(10000, False)
##        Target.TargetExecute(object)
#
#
#Target.WaitForTarget(10000, False)
#Gumps.SendAction(949095101, 14)
#Target.TargetExecute(Items.FindByID(0x143B,0x0000,0x401DF062,2,considerIgnoreList))
#Target.WaitForTarget(10000, False)
#Target.TargetExecute(0x402CF923)
#
#Gumps.WaitForGump(949095101, 10000)
#Gumps.SendAction(949095101, 14)