import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors
 
#frand = Target.PromptTarget(, 0x0000)

while not Player.IsGhost:
    if Player.Mana > 21:
        if Player.GetRealSkillValue( 'Chivalry' ) < 50.0:
            Spells.CastChivalry("Divine Fury")
            Misc.Pause(3500)
        elif Player.GetRealSkillValue( 'Chivalry' ) < 95.1:
            Player.HeadMessage(colors[ 'red' ],'hey yall')
            Spells.CastChivalry("Enemy of One")
            Misc.Pause(3500)
        elif Player.GetRealSkillValue( 'Chivalry' ) < 98.0:
            Spells.CastChivalry("Lich Form")
            Misc.Pause(3500)
        elif Player.GetRealSkillValue( 'Chivalry' ) < 99.0:
            Spells.CastChivalry("Vampiric Embrace")
            Misc.Pause(3500)
   
    elif Player.Mana <= 20:
        Player.UseSkill('meditation')
        Misc.Pause(12000)
        