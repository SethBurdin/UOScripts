target = Target.PromptTarget('Who to tame?',0x0000)

while not Player.IsGhost:
    if Player.Hits > 50:
        Player.UseSkill("Animal Taming")
        Target.WaitForTarget(2000, False)
        Target.TargetExecute(target)
        Misc.Pause(100)