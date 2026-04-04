
global a, b, c
map = Target.PromptTarget('What treasure you lookin for?',0x0000)

def findIt():
    a = Player.Position.X -1 
    b = Player.Position.Y
    c = Player.Position.Z

    Items.UseItemByID(0x0F39,0x0000)
    Target.WaitForTarget(1000, False)
    Target.TargetExecute(map)
    Target.WaitForTarget(1000, False)
    Target.TargetExecute(a, b ,c)
    Misc.SendMessage(Player.Position)
    #Target.TargetExecute(a,b,c, 0x0000)
    Misc.Pause(1000)
    
while not Player.IsGhost:
       findIt()
Items.UseItem(0x4010C54C)
Items.UseItem(0x4010C54C)
Items.UseItem(0x4010C54C)