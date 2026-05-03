Player.UseSkill('Imbuing')
Gumps.WaitForGump(0x5b394d53, 10000)   # Imbuing menu
Gumps.SendAction(0x5b394d53, 10011)    # Unravel Container
Target.WaitForTarget(10000, False)
Target.TargetExecute(0x4027E2DB)
Gumps.WaitForGump(0x7f3111a7, 10000)   # Confirm dialog
Gumps.SendAction(0x7f3111a7, 1)