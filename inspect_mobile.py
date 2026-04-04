'''
Debug script to inspect a mobile's properties
Target a mobile and it will print all information about it
'''

# Prompt to target a mobile
Misc.SendMessage('Target a mobile to inspect...', 68)
mobile = Target.PromptTarget('Select mobile to inspect')

if mobile:
    # Find the actual mobile object
    mob = Mobiles.FindBySerial(mobile)
    
    if mob:
        Misc.SendMessage('=== MOBILE INFO ===', 88)
        Misc.SendMessage('Serial: 0x%08X' % mob.Serial, 68)
        Misc.SendMessage('Name: %s' % mob.Name, 68)
        Misc.SendMessage('MobileID/Body: 0x%04X' % mob.MobileID, 68)
        Misc.SendMessage('Notoriety: %i' % mob.Notoriety, 68)
        Misc.SendMessage('Hits: %i/%i' % (mob.Hits, mob.HitsMax), 68)
        Misc.SendMessage('Position: X=%i Y=%i Z=%i' % (mob.Position.X, mob.Position.Y, mob.Position.Z), 68)
        Misc.SendMessage('Distance: %i' % Player.DistanceTo(mob), 68)
        Misc.SendMessage('WarMode: %s' % mob.WarMode, 68)
        Misc.SendMessage('Poisoned: %s' % mob.Poisoned, 68)
        Misc.SendMessage('Paralized: %s' % mob.Paralized, 68)
        Misc.SendMessage('IsGhost: %s' % mob.IsGhost, 68)
        Misc.SendMessage('IsHuman: %s' % mob.IsHuman, 68)
        Misc.SendMessage('Visible: %s' % mob.Visible, 68)
        Misc.SendMessage('Color: 0x%04X' % mob.Color, 68)
        
        # Wait for and display properties
        Misc.SendMessage('=== PROPERTIES ===', 88)
        if Mobiles.WaitForProps(mob.Serial, 2000):
            props = Mobiles.GetPropStringList(mob.Serial)
            if props:
                for i, prop in enumerate(props):
                    Misc.SendMessage('[%i] %s' % (i, prop), 68)
            else:
                Misc.SendMessage('No properties returned', 33)
        else:
            Misc.SendMessage('Properties timed out', 33)
        
        # Check if it has certain keywords in properties
        Misc.SendMessage('=== PROPERTY CHECKS ===', 88)
        if props:
            playerNameFound = any(Player.Name in prop for prop in props)
            tameFound = any('tame' in prop.lower() for prop in props)
            bondedFound = any('bonded' in prop.lower() for prop in props)
            happyFound = any('happy' in prop.lower() for prop in props)
            
            Misc.SendMessage('Player name found: %s' % playerNameFound, 68)
            Misc.SendMessage('Tame found: %s' % tameFound, 68)
            Misc.SendMessage('Bonded found: %s' % bondedFound, 68)
            Misc.SendMessage('Happy found: %s' % happyFound, 68)
        
        Misc.SendMessage('=== DONE ===', 88)
    else:
        Misc.SendMessage('Could not find mobile!', 33)
else:
    Misc.SendMessage('No target selected', 33)
