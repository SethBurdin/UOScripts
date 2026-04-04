'''
Mobile Inspector v2
Prompts the player to target a mobile, then displays all relevant data both
above the mobile/player and in the system message log.

Especially useful for diagnosing the taming script - checks notoriety,
tameable/tamed status, and all tooltip properties.
'''

try:
    from razorenhanced_stubs import *
except:
    pass

NOTORIETY_NAMES = {
    1: 'Innocent (Blue)',
    2: 'Friend/Ally (Green)',
    3: 'Gray/Neutral (Wild)',
    4: 'Criminal (Gray)',
    5: 'Enemy (Orange)',
    6: 'Murderer (Red)',
    7: 'NPC (???)',
}

def color_for_notoriety( n ):
    return { 1: 68, 2: 88, 3: 33, 4: 33, 5: 1100, 6: 1100, 7: 68 }.get( n, 68 )

# ---- Prompt for target ----
Misc.SendMessage( '=== Mobile Inspector === Target a mobile...', 88 )
Mobiles.Message( Player.Serial, 88, 'Target a mobile...' )

serial = Target.PromptTarget( 'Select a mobile to inspect' )
if not serial:
    Misc.SendMessage( 'No target selected.', 33 )
else:
    mob = Mobiles.FindBySerial( serial )
    if mob is None:
        Misc.SendMessage( 'Could not find mobile (0x%08X)' % serial, 33 )
    else:
        notorietyName = NOTORIETY_NAMES.get( mob.Notoriety, 'Unknown (%i)' % mob.Notoriety )
        notorietyColor = color_for_notoriety( mob.Notoriety )

        # ---- System log output ----
        Misc.SendMessage( '==============================', 88 )
        Misc.SendMessage( '  MOBILE INSPECTOR RESULTS', 88 )
        Misc.SendMessage( '==============================', 88 )
        Misc.SendMessage( 'Name:       %s' % mob.Name, 68 )
        Misc.SendMessage( 'Serial:     0x%08X' % mob.Serial, 68 )
        Misc.SendMessage( 'Body/ID:    0x%03X (%i)' % ( mob.MobileID, mob.MobileID ), 68 )
        Misc.SendMessage( 'Notoriety:  %i - %s' % ( mob.Notoriety, notorietyName ), notorietyColor )
        Misc.SendMessage( 'Hits:       %i / %i' % ( mob.Hits, mob.HitsMax ), 68 )
        Misc.SendMessage( 'Distance:   %i tiles' % Player.DistanceTo( mob ), 68 )
        Misc.SendMessage( 'Position:   X=%i Y=%i Z=%i' % ( mob.Position.X, mob.Position.Y, mob.Position.Z ), 68 )
        Misc.SendMessage( 'WarMode:    %s' % mob.WarMode, 68 )
        Misc.SendMessage( 'Poisoned:   %s' % mob.Poisoned, 68 )

        # ---- Notoriety summary visible above the mob ----
        Mobiles.Message( mob.Serial, notorietyColor, '[%i] %s' % ( mob.Notoriety, notorietyName ) )

        # ---- Fetch tooltip properties ----
        Misc.SendMessage( '--- Properties ---', 88 )
        Mobiles.WaitForProps( mob.Serial, 2000 )
        props = Mobiles.GetPropStringList( mob.Serial )

        isTameable = False
        isBonded   = False
        ownerFound = False

        if props and len( props ) > 0:
            for i, prop in enumerate( props ):
                Misc.SendMessage( '  [%i] %s' % ( i, prop ), 68 )
                pl = prop.lower()
                if 'tameable' in pl:
                    isTameable = True
                if 'bonded' in pl:
                    isBonded = True
                if Player.Name.lower() in pl:
                    ownerFound = True
        else:
            Misc.SendMessage( '  (no properties returned)', 33 )

        # ---- Key findings ----
        Misc.SendMessage( '--- Key Findings ---', 88 )
        Misc.SendMessage( 'Has "tameable" prop:  %s' % isTameable, 88 if isTameable else 33 )
        Misc.SendMessage( 'Has "bonded" prop:    %s' % isBonded, 88 if isBonded else 68 )
        Misc.SendMessage( 'Your name in props:   %s' % ownerFound, 88 if ownerFound else 68 )

        # ---- Taming script diagnosis ----
        Misc.SendMessage( '--- Taming Script Diagnosis ---', 88 )
        if mob.Notoriety == 3 and isTameable:
            Misc.SendMessage( 'VALID TARGET: Gray + tameable = wild animal, script SHOULD target this.', 88 )
            Mobiles.Message( mob.Serial, 88, 'VALID: Wild & tameable' )
        elif mob.Notoriety == 3 and not isTameable:
            Misc.SendMessage( 'GRAY but NO tameable prop - may already be tamed/abandoned or props not loaded.', 1100 )
            Mobiles.Message( mob.Serial, 1100, 'Gray but no tameable prop!' )
        elif mob.Notoriety != 3:
            Misc.SendMessage( 'NOT GRAY (notoriety=%i) - script will skip this mobile.' % mob.Notoriety, 33 )
            Mobiles.Message( mob.Serial, 33, 'Skipped: not gray (notoriety=%i)' % mob.Notoriety )

        Misc.SendMessage( '==============================', 88 )
        Mobiles.Message( Player.Serial, 88, 'Inspection complete - see log' )
