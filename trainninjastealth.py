## Check Ishidden

def SafeLocation():
    Player.PathFindTo(Location)

def getMana():
    Misc.Pause(8500)
    Player.UseSkill('Meditation')
    Misc.Pause(10000)
    Misc.Pause(500)
    
def checkHiding():
    if Player.Mana < 14:
        if not Player.BuffsExist( 'Hiding' ):
            Misc.Pause(500)
            Player.UseSkill('Hiding')
            Misc.Pause(11500)
            if not Player.BuffsExist( 'Stealth' ):
               Player.UseSkill("Stealth")
               Misc.Pause(500)
        elif not Player.BuffsExist( 'Stealth' ):
               Player.UseSkill("Stealth")
               Misc.Pause(500)
           
        
def learnNinja():
    if Player.Mana > 15:
        Spells.CastNinjitsu("Shadowjump")
        Target.WaitForTarget(2000, False)
        Target.TargetExecute(3501, 2570 ,14)
        Misc.Pause(3500)
        Spells.CastNinjitsu("Shadowjump")
        Target.WaitForTarget(2000, False)
        Target.TargetExecute(3498, 2574 ,14)
        Misc.Pause(3500)
        Spells.CastNinjitsu("Shadowjump")
        Target.WaitForTarget(2000, False)
        Target.TargetExecute(3496, 2573 ,14)
        Misc.Pause(3500)
        Spells.CastNinjitsu("Shadowjump")
        Target.WaitForTarget(2000, False)
        Target.TargetExecute(3497, 2573 ,14)
        Misc.Pause(3500)
    else:
        getMana()

        
while Player.GetSkillValue('Stealth') < 100:
    getMana()
    checkHiding()
    learnNinja()       
#
#while Player.GetSkillValue('Stealth') < 100:
#    if Player.Mana < 10:
#        Misc.Pause(8500)
#        Player.UseSkill('Meditation')
#        Misc.Pause(10000)
#        Player.Walk('north' , True)
#   
#    elif Player.BuffsExist( 'Hiding' ):
#        Player.UseSkill('Hiding')
#        Misc.Pause(1500)
#        Player.Walk('north' , True)
#        if not Player.BuffsExist( 'Stealth' ):
#            Player.Walk('north' , True)
#            Player.ToggleAlwaysRun()
#    else:
#        Spells.CastNinjitsu("Shadowjump")
#        Target.WaitForTarget(2000, False)
#        Target.TargetExecute(3501, 2570 ,14)
#        Misc.Pause(2500)
#        #Player.Wa
#        if not Player.BuffsExist( 'Hiding' ):
#            Player.UseSkill('Hiding')
#            Misc.Pause(2500)
#        else:
#            Spells.CastNinjitsu("Shadowjump")
#            Target.WaitForTarget(2000, False)
#            Target.TargetExecute(3498, 2574 ,14)
#            Misc.Pause(2500)
#
#
    
   