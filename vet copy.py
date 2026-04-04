from Scripts.utilities.items import FindItem
from Scripts.glossary.colors import colors
from System.Collections.Generic import List

if Misc.ShardName() == 'UO Evolution':
    petsToCheck = [
        0x00037C0A, # Horse
        0x00041BDC # Zazzy
    ]
else:
    petsToCheck = [
        0x00037C0A, # Horse
        0x00041BDC # Zazzy
    ]

#for pet in petsToCheck:
#    Timer.Create( 'distanceTimer%s' % pet, 1 )

def TestBandagesApplying():
    # Fetch the Journal entries (oldest to newest)
    regularText = Journal.GetTextByType( 'Regular' )

    # Reverse the Journal entries so that we read from newest to oldest
    regularText.Reverse()

    # Read back until the bandages were started to see if they have finished applying
    for line in regularText[ 0 : len( regularText ) ]:
        if line == 'You begin applying the bandages.':
            break
        if ( line == 'You finish applying the bandages.' or
                line == 'You heal what little damage your patient had.' or
                line == 'You did not stay close enough to heal your patient!' or
                line == 'You apply the bandages, but they barely help.' or
                line == 'That being is not damaged!' or
                line == 'You fail to resurrect the creature.' or
                line == 'You are able to resurrect your patient.' or
                line == 'You have cured the target of all poisons!' or
                line == 'That is too far away.' ):
            return False
    return True


# def WaitForBandagesToApply():
#     bandageDone = False
#     secondsCounter = 0
#     while TestBandagesApplying():
#         Misc.Pause( 300 )
#         secondsCounter += 1
#         Misc.SendMessage( '%i seconds since bandage started' % ( secondsCounter ) )
#     return


def HealPets():
    global petsToCheck
    
    
    petFilter = Mobiles.Filter()
    petFilter.IsGhost = 0
    petFilter.Friend = 1
    petFilter.RangeMin = 0
    petFilter.RangeMax = 8
    
    pets = Mobiles.ApplyFilter( petFilter )
    
    if len( pets ) == 0:
        return
    
    petToHeal = Mobiles.Select( pets, 'Weakest' )
    
    if petToHeal.Hits == petToHeal.HitsMax :
        petFilter.Poisoned = 1
        pets = Mobiles.ApplyFilter( petFilter )
        if len( pets ) == 0:
            return
        else:
            petToHeal = Mobiles.Select( pets, 'Weakest' )
    if not petToHeal.Poisoned:
        Spells.CastMagery("Greater Heal")
        Target.WaitForTarget( 5000, False )
        Target.TargetExecute( petToHeal )
        Player.HeadMessage( colors[ 'cyan' ], 'Healing %s (currently %i%% health)' % ( petToHeal.Name, ( float( petToHeal.Hits ) / float( petToHeal.HitsMax ) * 100 ) ) )
        Misc.Pause( 1700 )
    elif petToHeal.Poisoned:
        Spells.CastMagery("Arch Cure")
        Target.WaitForTarget( 4000, False )
        Target.TargetExecute( petToHeal )
        Player.HeadMessage( colors[ 'cyan' ], 'Curing %s (currently %i%% health)' % ( petToHeal.Name, ( float( petToHeal.Hits ) / float( petToHeal.HitsMax ) * 100 ) ) )
        Misc.Pause( 1500 )
        
        
         

    # WaitForBandagesToApply()
    return


while not Player.IsGhost:
    HealPets()
    Misc.Pause( 150 )
