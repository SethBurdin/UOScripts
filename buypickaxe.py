


def getPickAxes:
    Items.UseItem(0x4052B274)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 56)
    Misc.Pause(4000)
    Misc.WaitForContext(0x00004B30, 10000)
    Misc.ContextReply(0x00004B30, 1)
    Misc.Pause(3000)
    Items.UseItem(0x4052B274)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 55)
    
getPickAxes()

