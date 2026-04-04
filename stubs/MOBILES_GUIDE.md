# Mobiles API - Enhanced IntelliSense Guide

This guide covers the comprehensive type stubs for the Mobiles API, which now provides full autocomplete and type hints for all mobile-related functionality in Razor Enhanced.

## What's New - Enhanced Edition

The `Mobiles.pyi` stub file has been completely rewritten to include:

✅ All 40+ Mobile properties with descriptions and types
✅ All Mobiles module methods with overloads for int/Mobile parameters  
✅ Complete Mobiles.Filter class with all 25+ filter properties
✅ Mobiles.TrackingInfo class  
✅ Full documentation for notoriety values, selectors, and more
✅ Proper typing for System.Collections.Generic.List integration

## Quick Start

Add this to the top of your script:

```python
if False:  # IDE only - never runs in Razor Enhanced
    from razorenhanced_stubs import *
```

Now you get full IntelliSense for all Mobiles functionality!

## Mobile Object Properties

### Core Identity
```python
mobile.Serial       # int - Unique serial number
mobile.Name         # str - Name of the mobile
mobile.MobileID     # int - Type/appearance ID (also: Body, ItemID, Graphics)
mobile.Notoriety    # int - 1-7 (see notoriety guide below)
```

### Stats & Health
```python
mobile.Hits         # int - Current HP
mobile.HitsMax      # int - Maximum HP
mobile.Mana         # int - Current mana
mobile.ManaMax      # int - Maximum mana  
mobile.Stam         # int - Current stamina
mobile.StamMax      # int - Maximum stamina
```

### Status Flags
```python
mobile.Poisoned     # bool - Is poisoned?
mobile.Paralized    # bool - Is paralyzed?
mobile.YellowHits   # bool - Yellow healthbar?
mobile.WarMode      # bool - In war mode?
mobile.Visible      # bool - Is visible?
mobile.Flying       # bool - Is flying (Gargoyle)?
mobile.IsGhost      # bool - Is a ghost?
mobile.IsHuman      # bool - Has human body?
```

### Visual & Location
```python
mobile.Color        # int - Color/hue
mobile.Direction    # str - Direction facing
mobile.Position     # Point3D - X, Y, Z coordinates
mobile.Map          # int - Current map/facet
mobile.Female       # bool - Is female?
```

### Equipment & Items
```python
mobile.Backpack     # Item - Backpack (or None)
mobile.Quiver       # Item - Quiver (or None)
mobile.Mount        # Item - Mount layer item (or None)
mobile.Contains     # List[Item] - Items in paperdoll
```

### Properties & Metadata
```python
mobile.Properties   # List[Property] - All tooltip properties
mobile.PropsUpdated # bool - Are properties loaded?
mobile.Fame         # int - Fame (0-3)
mobile.Karma        # int - Karma (-5 to 5)
mobile.KarmaTitle   # str - Title from server
mobile.InParty      # bool - In your party?
mobile.CanRename    # bool - Can be renamed? (pets, etc)
```

### Methods
```python
mobile.DistanceTo(other_mobile)     # Get distance to another mobile
mobile.GetItemOnLayer('RightHand')  # Get item on specific layer
mobile.UpdateKarma()                # Update fame/karma (costly!)
```

## Mobiles Module Functions

### Finding Mobiles

```python
# Find by serial
mobile = Mobiles.FindBySerial(0x00012345)

# Find with filter
filter = Mobiles.Filter()
filter.RangeMax = 12
filter.Notorieties.Add(6)  # Hostile
enemies = Mobiles.ApplyFilter(filter)

# Select from list
nearest = Mobiles.Select(enemies, 'Nearest')
# Selectors: 'Nearest', 'Farthest', 'Weakest', 'Strongest'
```

### Interacting with Mobiles

```python
# Use/double-click
Mobiles.UseMobile(mobile.Serial)
Mobiles.UseMobile(mobile)  # Also accepts Mobile object

# Single click
Mobiles.SingleClick(mobile.Serial)

# Display message above mobile
Mobiles.Message(mobile.Serial, 33, "Hello!", wait=True)
```

### Properties & Context

```python
# Get property value
damage = Mobiles.GetPropValue(mobile, "Damage")

# Get all properties as strings
props = Mobiles.GetPropStringList(mobile.Serial)

# Wait for properties to load
if Mobiles.WaitForProps(mobile.Serial, 2000):
    # Properties loaded within 2 seconds
    print("Props loaded!")

# Wait for stats to update
if Mobiles.WaitForStats(mobile.Serial, 1000):
    print(f"HP: {mobile.Hits}/{mobile.HitsMax}")

# Check context menu
entry_id = Mobiles.ContextExist(mobile, "Guard Me", showContext=False)
if entry_id >= 0:
    print(f"'Guard Me' is at index {entry_id}")
```

### Targeting & Tracking

```python
# Get saved targeting filter
filter = Mobiles.GetTargetingFilter("MyHostiles")
enemies = Mobiles.ApplyFilter(filter)

# Get tracking info
tracking = Mobiles.GetTrackingInfo()
if tracking:
    print(f"Tracking: {tracking.serial} at ({tracking.x}, {tracking.y})")
```

## Mobiles.Filter - Complete Guide

The Filter class has 25+ properties for precise mobile filtering:

### Basic Filters

```python
filter = Mobiles.Filter()
filter.Enabled = True  # Must be True or filter does nothing!
filter.Name = "Orc"    # Filter by name (partial match)
```

### Range Filters

```python
filter.RangeMin = 2    # At least 2 tiles away
filter.RangeMax = 12   # At most 12 tiles away
filter.ZLevelMin = -5  # Minimum Z level
filter.ZLevelMax = 5   # Maximum Z level
filter.CheckLineOfSight = True  # Only visible mobiles
```

### ID & List Filters

```python
# Filter by MobileID/Body
filter.Bodies.Add(0x01)  # Add single ID
filter.Bodies.AddRange([0x02, 0x03, 0x04])  # Add multiple

# Filter by Graphics ID
filter.Graphics.Add(0x0190)  # Human male

# Filter by Color/Hue
filter.Hues.Add(0x0000)  # Black
filter.Hues.AddRange([0x0021, 0x0022])

# Filter by specific serials
filter.Serials.Add(0x00012345)
```

### Notoriety Filter

```python
# Notoriety values:
# 1 = Blue (innocent)
# 2 = Green (friend)
# 3 = Gray (neutral/attackable)
# 4 = Gray (criminal)
# 5 = Orange (enemy)
# 6 = Red (hostile/murderer)
# 7 = Yellow (invulnerable)

filter.Notorieties.Add(6)  # Red only
filter.Notorieties.AddRange([5, 6])  # Orange and red
```

### Status Filters

All status filters use: `-1` = any, `0` = no, `1` = yes

```python
filter.Poisoned = 1    # Only poisoned mobiles
filter.Paralized = 0   # Only non-paralyzed
filter.Warmode = 1     # Only in war mode
filter.Female = 1      # Only female mobiles
filter.Friend = 1      # Only friends
filter.Blessed = 0     # Only non-blessed
```

### Type Filters

```python
filter.IsGhost = 1     # Only ghosts (IDs: 402, 403, 607, 608, 694, 695, 970)
filter.IsHuman = 1     # Only humans (183, 184, 185, 186, 400, 401, etc.)
```

### Special Filters

```python
filter.CheckIgnoreObject = True  # Exclude mobiles on ignore list
filter.IgnorePets = False        # Exclude pets (default: True includes pets)
```

## Complete Examples

### Example 1: Find & Attack Nearest Hostile

```python
if False:
    from razorenhanced_stubs import *

def find_and_attack_hostile():
    # Create filter for nearby hostiles
    filter = Mobiles.Filter()
    filter.Enabled = True
    filter.RangeMax = 12
    filter.Notorieties.Add(6)  # Red/hostile
    filter.Notorieties.Add(5)  # Orange/enemy
    filter.CheckLineOfSight = True
    filter.CheckIgnoreObject = True
    
    # Find all matching mobiles
    enemies = Mobiles.ApplyFilter(filter)
    
    if enemies.Count > 0:
        # Select nearest
        target = Mobiles.Select(enemies, 'Nearest')
        
        if target:
            # Display info
            Misc.SendMessage(f"Attacking: {target.Name}", 33)
            Misc.SendMessage(f"HP: {target.Hits}/{target.HitsMax}", 33)
            
            # Attack
            Player.Attack(target)
            return True
    
    return False

# Use it
if find_and_attack_hostile():
    Misc.SendMessage("Enemy engaged!", 33)
else:
    Misc.SendMessage("No enemies found", 88)
```

### Example 2: Monitor Pet Health

```python
if False:
    from razorenhanced_stubs import *

def check_pets():
    # Find all friendly mobiles nearby
    filter = Mobiles.Filter()
    filter.Enabled = True
    filter.RangeMax = 12
    filter.Notorieties.Add(2)  # Green/friend (pets)
    filter.CheckLineOfSight = True
    
    pets = Mobiles.ApplyFilter(filter)
    
    low_health_pets = []
    
    for pet in pets:
        if pet.HitsMax > 0:
            health_percent = (pet.Hits / pet.HitsMax) * 100
            
            if health_percent < 60:
                low_health_pets.append({
                    'name': pet.Name,
                    'percent': health_percent,
                    'serial': pet.Serial,
                    'mobile': pet
                })
    
    # Sort by health (lowest first)
    low_health_pets.sort(key=lambda x: x['percent'])
    
    # Return worst pet
    if low_health_pets:
        return low_health_pets[0]['mobile']
    
    return None

# Use it
injured_pet = check_pets()
if injured_pet:
    Misc.SendMessage(f"{injured_pet.Name} needs healing!", 33)
    # Cast Greater Heal on pet
    Spells.CastMagery('Greater Heal')
    Target.WaitForTarget(2000)
    Target.TargetExecute(injured_pet.Serial)
```

### Example 3: Complex Filtering

```python
if False:
    from razorenhanced_stubs import *

def find_specific_target():
    """Find poisoned human enemies in war mode within 8 tiles"""
    
    filter = Mobiles.Filter()
    filter.Enabled = True
    
    # Range
    filter.RangeMax = 8
    
    # Must be enemy
    filter.Notorieties.AddRange([3, 4, 5, 6])  # Gray, crim, enemy, hostile
    
    # Must be human
    filter.IsHuman = 1
    
    # Must be poisoned
    filter.Poisoned = 1
    
    # Must be in war mode
    filter.Warmode = 1
    
    # Must be visible
    filter.CheckLineOfSight = True
    
    # Don't include pets
    filter.IgnorePets = False
    
    targets = Mobiles.ApplyFilter(filter)
    
    if targets.Count > 0:
        # Select weakest (lowest current HP)
        weakest = Mobiles.Select(targets, 'Weakest')
        return weakest
    
    return None

target = find_specific_target()
if target:
    Misc.SendMessage(f"Found poisoned human: {target.Name} ({target.Hits} HP)", 33)
```

### Example 4: Equipment Check

```python
if False:
    from razorenhanced_stubs import *

def check_enemy_equipment(mobile):
    """Check what a mobile is wielding"""
    
    # Wait for properties to load
    if not Mobiles.WaitForProps(mobile.Serial, 2000):
        return None
    
    # Check right hand (weapon)
    weapon = mobile.GetItemOnLayer('RightHand')
    
    # Check left hand (shield/weapon)
    shield = mobile.GetItemOnLayer('LeftHand')
    
    # Check armor
    armor_layers = ['Head', 'Chest', 'Arms', 'Gloves', 'Legs', 'Neck']
    armor_count = 0
    
    for layer in armor_layers:
        item = mobile.GetItemOnLayer(layer)
        if item:
            armor_count += 1
    
    return {
        'has_weapon': weapon is not None,
        'has_shield': shield is not None,
        'armor_pieces': armor_count,
        'backpack': mobile.Backpack is not None
    }

# Use it
enemy = Mobiles.FindBySerial(0x00012345)
if enemy:
    equipment = check_enemy_equipment(enemy)
    if equipment:
        Misc.SendMessage(f"Enemy has {equipment['armor_pieces']} armor pieces", 88)
```

## Notoriety Quick Reference

| Value | Color | Meaning |
|-------|-------|---------|
| 1 | Blue | Innocent |
| 2 | Green | Friend/Pet |
| 3 | Gray | Neutral/Attackable |
| 4 | Gray | Criminal |
| 5 | Orange | Enemy (Guild/Faction) |
| 6 | Red | Hostile/Murderer |
| 7 | Yellow | Invulnerable |

## Layer Names Reference

Valid layer names for `GetItemOnLayer()`:

- `RightHand` - Weapon in right hand
- `LeftHand` - Shield or weapon in left hand
- `Shoes` - Footwear
- `Pants` - Leg armor/clothing
- `Shirt` - Chest clothing
- `Head` - Helmet/hat
- `Gloves` - Gloves/gauntlets
- `Ring` - Ring
- `Neck` - Necklace/gorget
- `Waist` - Belt
- `InnerTorso` - Underwear chest
- `Bracelet` - Bracelet
- `MiddleTorso` - Tunic/chest armor
- `Earrings` - Earrings
- `Arms` - Arm armor/sleeves
- `Cloak` - Cloak/cape
- `OuterTorso` - Outer chest armor
- `OuterLegs` - Outer leg armor
- `InnerLegs` - Inner leg armor/clothing

## Tips & Best Practices

### 1. Always Enable Filters
```python
filter = Mobiles.Filter()
filter.Enabled = True  # Required! Default is True, but be explicit
```

### 2. Use CheckIgnoreObject to Avoid Repeat Checks
```python
filter.CheckIgnoreObject = True  # Skip mobiles on ignore list
Mobiles.IgnoreObject(mobile.Serial)  # Add to ignore list
```

### 3. Check Count Before Accessing
```python
mobiles = Mobiles.ApplyFilter(filter)
if mobiles.Count > 0:  # Always check!
    target = Mobiles.Select(mobiles, 'Nearest')
```

### 4. Wait for Props When Needed
```python
# Properties may not be loaded immediately
if Mobiles.WaitForProps(mobile.Serial, 2000):
    props = mobile.Properties
    # Now safe to use properties
```

### 5. Use Overloads
```python
# Both work - Pylance knows both!
Mobiles.UseMobile(0x00012345)  # By serial
Mobiles.UseMobile(mobile)      # By object
```

### 6. Combine Multiple Notorieties
```python
# Find any attackable target
filter.Notorieties.AddRange([3, 4, 5, 6])  # Gray, crim, enemy, hostile
```

### 7. Use Line of Sight for Combat
```python
filter.CheckLineOfSight = True  # Only targets you can actually see/hit
```

## Troubleshooting

### Autocomplete Not Showing?

1. Make sure you added the import:
   ```python
   if False:
       from razorenhanced_stubs import *
   ```

2. Reload VS Code (Ctrl+Shift+P → "Reload Window")

3. Check that Pylance is active (look for "Python" in status bar)

### Filter Not Finding Anything?

1. Check `filter.Enabled = True`
2. Try removing constraints one at a time
3. Test with just `RangeMax` first
4. Make sure `RangeMax` is adequate (try 20+ for testing)

### Properties Showing as None?

Use `WaitForProps()` first:
```python
if Mobiles.WaitForProps(mobile.Serial, 2000):
    # Now properties should be loaded
    print(mobile.Properties)
```

---

**Now you have comprehensive IntelliSense for the entire Mobiles API!** Type `Mobiles.` or `mobile.` and see all available options with full documentation.
