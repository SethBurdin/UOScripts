import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
if _d not in sys.path:
    sys.path.insert(0, _d)

if Player.Name == 'TheWarMage':
    Misc.SetSharedValue( 'reagentsBag', 0x4014BC93 )
elif Player.Name == 'TheWarPhysician':
    Misc.SetSharedValue( 'reagentsBag', 0x42BB620D )
elif Player.Name == 'TheWarMapper':
    Misc.SetSharedValue( 'beetle', 0x001D9588 )
    Misc.SetSharedValue( 'reagentsBag', 0x40C364B9 )
    Misc.SetSharedValue( 'weaponsBag', 0x40260558 )
    Misc.SetSharedValue( 'armorBag', 0x4077E0EF )
    Misc.SetSharedValue( 'gemsBag', 0x435B14F2 )
    Misc.SetSharedValue( 'scrollsBag', 0x435A85AC )
elif Player.Name == 'TombRaider':
    Misc.SetSharedValue( 'reagentsBag', 0x402916FB )
