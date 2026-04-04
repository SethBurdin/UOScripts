
while not Player.IsGhost:
    if Player.Mana > 20:
        Spells.CastSpellweaving("Essence of Wind")
#        Target.WaitForTarget(10000, False)
#        Target.TargetExecute(0x17148)
        Misc.Pause(3500)
        
    elif Player.Mana <= 20:
        Player.UseSkill('meditation')
        Misc.Pause(12000)
        Player.UseSkill('meditation')
        Misc.Pause(12000)
        Player.UseSkill('meditation')
        Misc.Pause(12000)