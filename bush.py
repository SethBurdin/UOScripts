

if Player.Mana > 10:
    Player.UseSkill('hiding')
    Misc.Pause(12000)
    Player.UseSkill('stealth')
    Misc.Pause(1500)
    #Player.Walk("East")
    Spells.CastNinjitsu("Shadowjump")
    Target.WaitForTarget(10000, False)
    Target.TargetExecute(3503, 2569 ,14)
    Misc.Pause(9500)
    Player.UseSkill('hiding')
    Misc.Pause(12000)
    Player.UseSkill('stealth')
    Misc.Pause(1500)
    #Player.Walk("East")
    Spells.CastNinjitsu("Shadowjump")
    Target.WaitForTarget(10000, False)
    Target.TargetExecute(3499, 2572 ,14)
else:
    Player.UseSkill('meditation')
    Misc.Pause(7000)