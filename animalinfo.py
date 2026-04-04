from Scripts.glossary import items
from Scripts.glossary.enemies import GetEnemyNotorieties
from Scripts.glossary import spells
from Scripts.glossary import tameables
from System.Collections.Generic import List
from System import Byte

minimumTamingDifficulty = 31
# Set this to how you would like to heal your character if they take damage
# Options are:
# 'Healing' = use bandages
# 'Magery' = uses the Heal and Greater Heal ability depending on how much health is missing
# 'None' = do not auto-heal
healUsing = 'None'
# True or False to use Peacemaking if needed
enablePeacemaking = False
# True or False to track the animal being tamed
enableFollowAnimal = True
# Change depending on the latency to your UO shard
journalEntryDelayMilliseconds = 100
targetClearDelayMilliseconds = 100




noAnimalsToTrainTimerMilliseconds = 10000
playerStuckTimerMilliseconds = 5000
catchUpToAnimalTimerMilliseconds = 20000
animalTamingTimerMilliseconds = 13000
peacemakingTimerMilliseconds = 10000
bandageTimerMilliseconds = 5000


def FindAnimalToTame():
    '''
    Finds the nearest tameable animal nearby
    '''
    global renameTamedAnimalsTo
    global minimumTamingDifficulty

    animalFilter = Mobiles.Filter()
    animalFilter.Enabled = True
    animalFilter.Bodies = tameables.GetAnimalIDsAtOrOverTamingDifficulty( minimumTamingDifficulty )
    animalFilter.RangeMin = 0
    animalFilter.RangeMax = 12
    animalFilter.IsHuman = 0
    animalFilter.IsGhost = 0
    animalFilter.CheckIgnoreObject = True

    tameableMobiles = Mobiles.ApplyFilter( animalFilter )

    # Exclude animals that have already been tamed by this player
    tameableMobilesTemp = tameableMobiles[:]
    for tameableMobile in tameableMobiles:
        if tameableMobile.Name in petsToIgnore:
            tameableMobilesTemp.Remove( tameableMobile )

    tameableMobiles = tameableMobilesTemp

    if len( tameableMobiles ) == 0:
        return None
    elif len( tameableMobiles ) == 1:
        return tameableMobiles[ 0 ]
    else:
        return Mobiles.Select( tameableMobiles, 'Nearest' )



def GetAnimalInfo():
    '''
    Trains Animal Taming to GM
    '''

    # User variables
    global renameTamedAnimalsTo
    global numberOfFollowersToKeep
    global maximumTameAttempts
    global enablePeacemaking
    global enableFollowAnimal
    global journalEntryDelayMilliseconds
    global targetClearDelayMilliseconds

    # Script variables
    global noAnimalsToTrainTimerMilliseconds
    global playerStuckTimerMilliseconds
    global catchUpToAnimalTimerMilliseconds
    global animalTamingTimerMilliseconds
    global peacemakingTimerMilliseconds
    global bandageTimerMilliseconds



    # Initialize variables
    animalBeingTamed = None
    tameHandled = False
    tameOngoing = False
    timesTried = 0
    bandageBeingApplied = False
    target = Target.PromptTarget('getit','FF0000')
    # If a target is selected, return the target
    if target:
        print(f'Target selected: {target}')
        return target
    else:
        print('No target selected.')
        return None

GetAnimalInfo()