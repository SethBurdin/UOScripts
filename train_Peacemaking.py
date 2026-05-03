'''
Author: TheWarDoctor95
Other Contributors:
Last Contribution By: TheWarDoctor95 - March 23, 2019

Description: Uses the Peacemaking skill on the player to train Peacemaking to GM
'''

peacemakingTimerMilliseconds = 10200

from System.Collections.Generic import List
from glossary.items.instruments import FindInstrument
from glossary.enemies import GetEnemyNotorieties, GetEnemies
from Scripts import config


'''
Author: TheWarDoctor95
Other Contributors:
Last Contribution By: TheWarDoctor95 - March 14, 2019

Description: Uses the instruments from the player's backpack to train Musicianship to GM
'''

musichianshipTimerMilliseconds = 6500

# def FindItem( itemsToLookFor, items ):
#     '''
#     Recursively looks through a container for any items in the provided list
#     Returns the first item found from the list
#     '''
#     # Iterate through each item in the given list
#     for item in items:
#         if item.ItemID in itemsToLookFor:
#             return item
#         elif item.IsContainer:
#             # If the list of items contains a container, look in that container for the item too
#             itemToReturn = FindItem( itemsToLookFor, item.Contains )
#             if itemToReturn != None:
#                 return itemToReturn
#     return None

def PickInstrument():
    '''Returns an instrument from the backpack, or None.'''
    return FindInstrument( Player.Backpack )


def UseInstrumentTarget( instrument, target ):
    '''
    Fires the Discordance skill. Handles the "What instrument shall you play?"
    selection prompt if it appears.  Returns the instrument still in use, or
    None if no instrument is available.
    '''
    Journal.Clear()
    Player.UseSkill( 'Discordance' )
    Misc.Pause( config.journalEntryDelayMilliseconds )

    if Journal.Search( 'What instrument shall you play?' ):
        instrument = PickInstrument()
        if instrument is None:
            Target.Cancel()
            Misc.SendMessage( 'Ran out of instruments!', colors[ 'red' ] )
            return None
        Target.WaitForTarget( 2000, True )
        Target.TargetExecute( instrument.Serial )

    Target.WaitForTarget( 2000, True )
    Target.TargetExecute( target )
    return instrument


def TrainPeacemaking():
    '''
    Trains Peacemaking to GM.
    Tracks the current instrument and automatically switches to a fresh one
    if it breaks mid-training, stopping gracefully when none remain.
    '''
    global peacemakingTimerMilliseconds

    if Player.GetRealSkillValue( 'Peacemaking' ) == Player.GetSkillCap( 'Peacemaking' ):
        Misc.SendMessage( 'Peacemaking is already at cap!', 65 )
        return

    instrument = PickInstrument()
    UseInstrumentTarget( instrument, Player.Serial )
    if instrument is None:
        Misc.SendMessage( 'No instrument found in backpack!', 1100 )
        return

    Misc.SendMessage( 'Training Peacemaking with: %s' % instrument.Name, 65 )

    # Initialize skill timers
    Timer.Create( 'peacemakingTimer', 1 )

    # Initialize the journal
    Journal.Clear()
    Misc.ClearIgnore()

    while not Player.IsGhost and Player.GetRealSkillValue( 'Peacemaking' ) < Player.GetSkillCap( 'Peacemaking' ):
        if not Timer.Check( 'peacemakingTimer' ):
            # Check whether the current instrument still exists (it may have broken)
            instrument = Items.FindBySerial( instrument.Serial )
            if instrument is None:
                instrument = FindInstrument()
                if instrument is None:
                    Misc.SendMessage( 'Ran out of instruments — stopping.', 1100 )
                    return
                Misc.SendMessage( 'Instrument broke — now using: %s' % instrument.Name, 65 )

            # Clear any previously selected target and the target queue
            Target.ClearLastandQueue()
            Misc.Pause( config.targetClearDelayMilliseconds )

            Player.UseSkill( 'Peacemaking' )
            Misc.Pause( config.journalEntryDelayMilliseconds )

            # If UO asks which instrument to use, supply the current one
            if Journal.SearchByType( 'What instrument shall you play?', 'Regular' ):
                Target.WaitForTarget( 2000, True )
                # Target.TargetExecute( instrument )
                instrument = PickInstrument()
                UseInstrumentTarget( instrument, Player.Serial )
                if instrument is None:
                    Misc.SendMessage( 'No instrument found in backpack!', 1100 )
                    return

            Target.WaitForTarget( 2000, True )
            Target.TargetExecute( Player.Serial )

            Misc.Pause( config.journalEntryDelayMilliseconds )

            if ( Journal.SearchByType( 'You play hypnotic music, calming your target.', 'Regular' ) or
                    Journal.SearchByType( 'You play your hypnotic music, stopping the battle.', 'Regular' ) or
                    Journal.SearchByType( 'You attempt to calm everyone, but fail.', 'Regular' ) or
                    Journal.SearchByType( 'You play hypnotic music, but there is nothing in range for you to calm.', 'Regular' ) or
                    Journal.SearchByType( 'You attempt to calm your target, but fail.', 'Regular' ) ):
                Timer.Create( 'peacemakingTimer', peacemakingTimerMilliseconds )
            else:
                # Skill use wasn't recognised — wait the bard cooldown before retrying
                # to avoid spamming the server. Adjust musichianshipTimerMilliseconds at
                # the top of the file if your shard has a different cooldown.
                Timer.Create( 'peacemakingTimer', musichianshipTimerMilliseconds )

            Journal.Clear()

        Misc.Pause( 50 )

# Start Peacemaking training
TrainPeacemaking()
