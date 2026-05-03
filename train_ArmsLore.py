'''
Author: TheWarDoctor95
Other Contributors:
Last Contribution By: TheWarDoctor95 - May 30, 2019

Description: Uses the selected target to train Arms Lore to its cap
'''

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors

armsLoreTimerMilliseconds = 1200

# Select what to run Arms Lore on
armsLoreTarget = Target.PromptTarget( 'Select item to train on' )

def TrainArmsLore():
    '''
    Trains Arms Lore with the selected target
    '''
    global armsLoreTarget

    Timer.Create( 'armsLoreTimer', 1 )

    while not Player.IsGhost and Player.GetRealSkillValue( 'Arms Lore' ) < Player.GetSkillCap( 'Arms Lore' ):
        if not Timer.Check( 'armsLoreTimer' ):
            Player.UseSkill( 'Arms Lore' )
            Target.WaitForTarget( 2000, False )
            Target.TargetExecute( armsLoreTarget )
            Timer.Create( 'armsLoreTimer', armsLoreTimerMilliseconds )

    if Player.GetRealSkillValue( 'Arms Lore' ) >= Player.GetSkillCap( 'Arms Lore' ):
        Player.HeadMessage( colors[ 'green' ], 'Arms Lore training complete!' )

# Start Training
TrainArmsLore()
