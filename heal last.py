healem = Target.PromptTarget("Who to heal?",0x0000)

while not Player.IsGhost:
    if Player.Mana > 30:
        Spells.Cast("Greater Heal")
        Target.WaitForTarget(3000,False)
        Target.TargetExecute(healem)
       
        Misc.Pause(1300)
        elif Player.Mana < 10:
        Player.EquipItem(0x404A5110)
        Misc.Pause(5000)
        elif Player.Mana < 30:
            Player.UseSkill('meditation')
            Misc.Pause(11000)