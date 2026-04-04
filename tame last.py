

target = Target.PromptTarget('who to tame?', 0x0000)

while not Player.IsGhost and not Player.Poisoned and not Player.WarMode :
    Player.UseSkill("Animal Taming")
    Target.WaitForTarget(10000, False)
    Target.TargetExecute(target)
    Misc.Pause(100)
    
    