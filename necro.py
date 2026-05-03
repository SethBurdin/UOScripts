#rand = 0x0007F232
#frand = 0x00055BB5
#frand = 0x00017148
from glossary.colors import colors
 
#frand = Target.PromptTarget(, 0x0000)

while not Player.IsGhost:
    if Player.Mana > 21:
        if Player.GetRealSkillValue( 'Necromancy' ) < 56.0:
            Spells.CastNecro("Wraith Form")
            Misc.Pause(3500)
        elif Player.GetRealSkillValue( 'Necromancy' ) < 74.0:
            Player.HeadMessage(colors[ 'red' ],'hey yall')
            Spells.CastNecro("Horrific Beast")
            Misc.Pause(3500)
        elif Player.GetRealSkillValue( 'Necromancy' ) < 80.0:
            Spells.CastNecro("Lich Form")
            Misc.Pause(3500)
        elif Player.GetRealSkillValue( 'Necromancy' ) < 85.0:
            Spells.CastNecro("Vampiric Embrace")
            Misc.Pause(3500)
   
    elif Player.Mana <= 20:
        Player.UseSkill('meditation')
        Misc.Pause(12000)
        
        