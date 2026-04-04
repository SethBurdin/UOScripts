
while not Player.IsGhost:
    if Player.Mana > 20:
        Gumps.WaitForGump(949095101, 2000)
        Gumps.SendAction(949095101, 21)
        Gumps.WaitForGump(949095101, 2000)
        if not Gumps.IsValid(949095101):
            Items.UseItemByID(0x0FBF,0x0000)
            Misc.Pause(1900)
   
    elif Player.Mana <= 20:
        Player.UseSkill('meditation')
        Misc.Pause(19000)
        Player.UseSkill('meditation')
        Misc.Pause(19000)
    
