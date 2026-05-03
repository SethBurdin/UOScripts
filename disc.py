from glossary import items
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.enemies import GetEnemyNotorieties
from glossary import spells
from glossary import tameables
from System.Collections.Generic import List
from System import Byte



from xmlrpc.client import Boolean
'''
Author: TheWarDoctor95
Other Contributors:
Last Contribution By: TheWarDoctor95 - March 23, 2019

Description: Uses the instruments from the player's backpack and the selected or
    auto-selected target to train Discordance to its cap
'''

autoSelectTarget = True
discordTimerMilliseconds = 10200
animalBeingTamed = None
tameHandled = False
tameOngoing = False
timesTried = 0
bandageBeingApplied = False


from Scripts import config
from glossary.items.instruments import FindInstrument
from glossary.colors import colors
from glossary.enemies import GetEnemies



def TrainDiscordance():
    '''
    Trains Musicianship by using the instruments in the player's bag
    Transitions to a new instrument if the one being used runs out of uses
    '''
    global autoSelectTarget
    global discordTimerMilliseconds

    Timer.Create( 'discordTimer', 1 )

    instrument = FindInstrument( Player.Backpack )
    if instrument == None:
        Misc.SendMessage( 'No instruments to train with', colors[ 'red' ] )
        return
    
    discordTarget = None
    while instrument != None and Player.GetSkillValue( 'Discordance' ) < 100 and not Player.IsGhost:
        if discordTarget == None:
            if autoSelectTarget:
                enemies = GetEnemies( Mobiles, 0, 8 )
                #discordTarget = Mobiles.Select( enemies, 'Nearest' )
                discordTarget = Mobiles.Select( enemies, 'Next' )
                
            else:
                discordTarget = Target.PromptTarget( 'Select target to train provo on' )
                discordTarget = Mobiles.FindBySerial( discordTarget )
            
            if discordTarget != None:
                Mobiles.Message( discordTarget, colors[ 'cyan' ], 'Selected for discord training' )
        else:
            discordTarget = Mobiles.FindBySerial( discordTarget.Serial )
            
        if autoSelectTarget and discordTarget == None: 
            Misc.Pause( 100 )
            continue

        if not Timer.Check( 'discordTimer' ):
            Journal.Clear()
            Player.UseSkill( 'Discordance' )
            
            Misc.Pause( config.journalEntryDelayMilliseconds )
            
            if Journal.Search( 'What instrument shall you play?' ):
                # Instrument either broke or hasn't been selected
                instrument = FindInstrument( Player.Backpack )
                if instrument == None:
                    # No more instruments, stop the provo attempt
                    Target.Cancel()

                    Misc.SendMessage( 'Ran out of instruments to train with', colors[ 'red' ] )
                    return
                else:
                    Target.WaitForTarget( 2000, True )
                    Target.TargetExecute( instrument.Serial )

            Target.WaitForTarget( 2000, True )
            Target.TargetExecute( discordTarget )
            discordTarget = None
            Misc.Pause( 1500 )
            #Player.Attack( discordTarget )
            #

            Timer.Create( 'discordTimer', discordTimerMilliseconds )

        # Wait a little bit so that the while loop doesn't consume as much CPU
        Misc.Pause( 500 )

# Start Training

TrainDiscordance()