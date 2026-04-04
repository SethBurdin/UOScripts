target = Target.PromptTarget('What you want to disarm',0x0000)

while target != None:
    
    Player.UseSkill("Remove Trap")
    Target.WaitForTarget(10000, False)
    Target.TargetExecute(target)
    Misc.Pause(10000)