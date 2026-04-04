

while Player.Mana > 20:

    Misc.Pause(2000)
    Player.UseSkill("Poisoning")
    Target.WaitForTarget(10000, False)
    Target.TargetExecute(0x40217915)
    Target.WaitForTarget(10000, False)
    Target.TargetExecute(0x409BBC92)

    Items.UseItem(0x40984B7C)
    Misc.Pause(9000)
    











