def gateHome():
    Items.UseItem(0x4052B274)
    Gumps.WaitForGump(89, 10000)
    Gumps.SendAction(89, 104)
    Misc.Pause(8500)
    
    gateFilter = Items.Filter()
    gateFilter.RangeMin = 0
    gateFilter.RangeMax = 1
    
    UseIt = Items.ApplyFilter( gateFilter )
    for items in UseIt:
        Items.UseItem(items)
        
    
gateHome()
    