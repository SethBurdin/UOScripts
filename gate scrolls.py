

if Player.Mana < 40:
    Player.UseSkill('Meditation')
    Misc.Pause(9600)
    Player.UseSkill('Meditation')
    Misc.Pause(7600)
    while Player.Mana < 110:
        Misc.Pause(5000)

elif Player.Mana > 60:
    Items.UseItemByID(0x0FBF,0x0000)
    Misc.Pause(700)
    Gumps.WaitForGump(949095101, 10000)
    Gumps.SendAction(949095101, 23)
    Misc.Pause(700)
   
else:
    Misc.Pause(6000)
    