'''
Quick test to check if an animal has the "tameable" property
Target an animal to see its properties
'''

Misc.SendMessage('=== TAMEABLE CHECK TEST ===', 88)
Misc.SendMessage('Target an animal to check...', 68)

mobile = Target.PromptTarget('Select animal to check')

if mobile:
    mob = Mobiles.FindBySerial(mobile)
    
    if mob:
        Misc.SendMessage('--- Mobile: %s ---' % mob.Name, 88)
        Misc.SendMessage('Notoriety: %i' % mob.Notoriety, 68)
        
        # Wait for and get properties
        Misc.SendMessage('Loading properties...', 68)
        if Mobiles.WaitForProps(mob.Serial, 2000):
            props = Mobiles.GetPropStringList(mob.Serial)
            if props:
                Misc.SendMessage('Properties found: %i' % len(props), 88)
                for i, prop in enumerate(props):
                    Misc.SendMessage('[%i] %s' % (i, prop), 68)
                    
                # Check for tameable
                isTameable = False
                for prop in props:
                    if 'tameable' in prop.lower():
                        isTameable = True
                        Misc.SendMessage('>>> FOUND TAMEABLE PROPERTY <<<', 88)
                        break
                
                if not isTameable:
                    Misc.SendMessage('>>> NO TAMEABLE PROPERTY (already tamed or not tameable) <<<', 33)
            else:
                Misc.SendMessage('No properties returned!', 33)
        else:
            Misc.SendMessage('Properties timed out!', 33)
    else:
        Misc.SendMessage('Could not find mobile!', 33)
else:
    Misc.SendMessage('No target selected', 33)

Misc.SendMessage('=== TEST COMPLETE ===', 88)
