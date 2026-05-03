'''
Author: TheWarDoctor95
Other Contributors:
Last Contribution By: TheWarDoctor95 - March 23, 2019

Description: Uses the instruments from the player's backpack and the selected or
    auto-selected target to train Provocation to its cap
'''

autoSelectTarget = True
provocationTimerMilliseconds = 10200

from Scripts import config
# from glossary.items.instruments import FindInstrument
from glossary.colors import colors
from glossary.enemies import GetEnemies

def FindItem( itemsToLookFor, items ):
    '''
    Recursively looks through a container for any items in the provided list
    Returns the first item found from the list
    '''
    # Iterate through each item in the given list
    for item in items:
        if item.ItemID in itemsToLookFor:
            return item
        elif item.IsContainer:
            # If the list of items contains a container, look in that container for the item too
            itemToReturn = FindItem( itemsToLookFor, item.Contains )
            if itemToReturn != None:
                return itemToReturn
    return None


def FindInstrument():
    '''
    Uses FindItem to find an instrument in the player's backpack
    Returns the first instrument found
    '''
    instruments = [
        0xe9c,  # Drum
        0x2805,  # Flute
        0xeb3,  # Lute

        # Harps
        0xeb2,  # Lap Harp
        0xeb1,  # Standing Harp

        # Tambourines
        0xe9e,  # Tambourine
        0xe9d   # Tambourine with red tassle
    ]

    instrument = FindItem( instruments, Player.Backpack.Contains )
    return instrument

def TrainProvocation():
    '''
    Trains Provocation by using the instruments in the player's bag
    Transitions to a new instrument if the one being used runs out of uses
    '''
    global autoSelectTarget
    global provocationTimerMilliseconds
    global instrument

    Misc.SendMessage( 'Training with: %s' % instrument )
    Timer.Create( 'provocationTimer', 1 )

    provocationTarget = None
    provocationTarget2 = None
    while instrument != None and Player.GetSkillValue( 'Provocation' ) < 100 and not Player.IsGhost:
        if autoSelectTarget:
            if provocationTarget == None or provocationTarget2 == None:
                enemies = GetEnemies( Mobiles, 0, 8 )
                provocationTarget = Mobiles.Select( enemies, 'Nearest' )
                if provocationTarget != None:
                    enemies.Remove( provocationTarget )
                    provocationTarget2 = Mobiles.Select( enemies, 'Nearest' )
                else:
                    provocationTarget2 = None
            else:
                if Mobiles.FindBySerial( provocationTarget.Serial ) == None:
                    provocationTarget = None
                if Mobiles.FindBySerial( provocationTarget2.Serial ) == None:
                    provocationTarget2 = None
        else:
            if provocationTarget == None:
                provocationTarget = Target.PromptTarget( 'Select first target to provoke' )
                provocationTarget = Mobiles.FindBySerial( provocationTarget )
                if provocationTarget != None:
                    Mobiles.Message( provocationTarget, colors[ 'cyan' ], 'Provo target 1' )
            if provocationTarget2 == None:
                provocationTarget2 = Target.PromptTarget( 'Select second target to provoke onto' )
                provocationTarget2 = Mobiles.FindBySerial( provocationTarget2 )
                if provocationTarget2 != None:
                    Mobiles.Message( provocationTarget2, colors[ 'cyan' ], 'Provo target 2' )
            
        if provocationTarget == None or provocationTarget2 == None:
            Misc.Pause( 100 )
            continue

        if not Timer.Check( 'provocationTimer' ):
            Journal.Clear()
            Player.UseSkill( 'Provocation' )
            Misc.Pause( config.journalEntryDelayMilliseconds )
            if Journal.Search( 'What instrument shall you play?' ):
                # Instrument either broke or hasn't been selected
                instrument = FindInstrument()
                if instrument == None:
                    # No more instruments, stop the provo attempt
                    Target.Cancel()

                    Misc.SendMessage( 'Ran out of instruments to train with', colors[ 'red' ] )
                    return
                else:
                    Target.WaitForTarget( 2000, True )
                    Target.TargetExecute( instrument.Serial )

            Target.WaitForTarget( 2000, True )
            Target.TargetExecute( provocationTarget )
            Target.WaitForTarget( 2000, True )
            Target.TargetExecute( provocationTarget2 )
            Target.SetLast( provocationTarget )

            Timer.Create( 'provocationTimer', provocationTimerMilliseconds )

        # Wait a little bit so that the while loop doesn't consume as much CPU
        Misc.Pause( 50 )

# Start Training
instrument = FindInstrument()

if instrument == None:
    Player.HeadMessage( colors[ 'red' ], 'No instrument found' )
else:
    TrainProvocation()
