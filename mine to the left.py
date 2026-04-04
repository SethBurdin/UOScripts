
SafePlace = {}
SafePlace = Player.Position
global a, b, c




a = Player.Position.X -1 
b = Player.Position.Y
c = Player.Position.Z


Items.UseItemByID(0x0E86,0x0000)
Target.WaitForTarget(1000,True)

#Target.TargetExecuteRelative(Player.Position, -1)
Target.TargetExecute(a,b,c, 0x0000)
Misc.Pause(1500)
Misc.SendMessage(Player.Position)