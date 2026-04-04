

while not Player.IsGhost:
    if Player.Mana > 50 and Player.GetRealSkillValue("Mysticism") < 20:
        Spells.CastMysticism("Healing Stone")
        Misc.Pause(5000)
    elif Player.Mana > 50 and Player.GetRealSkillValue("Mysticism") > 20 and  Player.GetRealSkillValue("Mysticism") < 40:
        Spells.CastMysticism("Sleep")
        Target.WaitForTarget(10000, False)
        Target.TargetExecute(0x3DB70)
        Misc.Pause(1500)
    elif Player.Mana > 50 and Player.GetRealSkillValue("Mysticism") > 20 and  Player.GetRealSkillValue("Mysticism") < 62:
        Spells.CastMysticism("Stone Form")
        Misc.Pause(4500)
    elif Player.Mana > 50 and Player.GetRealSkillValue("Mysticism") > 62.3  and  Player.GetRealSkillValue("Mysticism") < 91:
        Spells.CastMysticism("Clensing Winds")
        Target.WaitForTarget(10000, False)
        Target.TargetExecute(0x3DB70)
        Misc.Pause(1500)
    elif Player.Mana > 50 and Player.GetRealSkillValue("Mysticism") > 91:
        Spells.CastMysticism("Nether Cyclone")
        Target.WaitForTarget(10000, False)
        Target.TargetExecute(0x3DB70)
        Misc.Pause(1500)
    else:
        Player.UseSkill("Meditation")
        Misc.Pause(5000)

