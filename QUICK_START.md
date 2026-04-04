# 🚀 Quick Start Guide - Enhanced Pylance for Razor Enhanced

## Copy-Paste This Into Any Script

```python
if False:  # IDE only - never runs in Razor Enhanced
    from razorenhanced_stubs import *

# Your code here - now with full autocomplete!
```

## What You Get

### Type This → See This

```python
Mobiles. 
# ↓ Shows:
# • ApplyFilter(filter: Filter) -> List[Mobile]
# • FindBySerial(serial: int) -> Mobile
# • Select(mobiles: List[Mobile], selector: str) -> Mobile
# • UseMobile(serial: int | Mobile) -> None
# • Message, GetPropValue, WaitForProps, and more!
```

```python
mobile.
# ↓ Shows all properties:
# • Name: str
# • Serial: int
# • Hits, HitsMax, Mana, ManaMax, Stam, StamMax: int
# • Notoriety: int (1-7)
# • Poisoned, Paralized, WarMode: bool
# • Position: Point3D
# • Backpack, Quiver, Mount: Item
# ...and 30+ more!
```

```python
filter = Mobiles.Filter()
filter.
# ↓ Shows all options:
# • Enabled: bool
# • RangeMax, RangeMin: float
# • Notorieties: List[byte] (use .Add() or .AddRange())
# • Bodies, Graphics, Hues, Serials: List[int]
# • CheckLineOfSight, CheckIgnoreObject: bool
# • Poisoned, Paralized, Warmode, Female: int (-1/0/1)
# • IsHuman, IsGhost: int
# ...and 15+ more!
```

## Common Patterns

### Find Hostile Enemy
```python
if False: from razorenhanced_stubs import *

filter = Mobiles.Filter()
filter.Enabled = True
filter.RangeMax = 12
filter.Notorieties.Add(6)  # Red/hostile
enemies = Mobiles.ApplyFilter(filter)
if enemies.Count > 0:
    target = Mobiles.Select(enemies, 'Nearest')
    Player.Attack(target)
```

### Check Pet Health
```python
if False: from razorenhanced_stubs import *

filter = Mobiles.Filter()
filter.RangeMax = 12
filter.Notorieties.Add(2)  # Green/friend
pets = Mobiles.ApplyFilter(filter)

for pet in pets:
    health_pct = (pet.Hits / pet.HitsMax * 100) if pet.HitsMax > 0 else 0
    if health_pct < 50:
        Misc.SendMessage(f"{pet.Name} low health!", 33)
```

### Find Specific Mobile
```python
if False: from razorenhanced_stubs import *

mobile = Mobiles.FindBySerial(0x00012345)
if mobile:
    print(f"{mobile.Name}: {mobile.Hits}/{mobile.HitsMax} HP")
    print(f"Distance: {mobile.DistanceTo(Player)}")
    if mobile.Poisoned:
        print("Poisoned!")
```

## Quick Reference

### Notoriety Values
```
1 = Blue (innocent)
2 = Green (friend/pet)
3 = Gray (neutral)
4 = Gray (criminal)
5 = Orange (enemy)
6 = Red (hostile)
7 = Yellow (invulnerable)
```

### Selectors
```
'Nearest'   - Closest mobile
'Farthest'  - Furthest mobile
'Weakest'   - Lowest current HP
'Strongest' - Highest current HP
```

### Status Filter Values
```
-1 = Any
 0 = No/False
 1 = Yes/True
```

### Equipment Layers
```
'RightHand', 'LeftHand', 'Shoes', 'Pants', 'Shirt',
'Head', 'Gloves', 'Ring', 'Neck', 'Waist',
'InnerTorso', 'Bracelet', 'MiddleTorso', 'Earrings',
'Arms', 'Cloak', 'OuterTorso', 'OuterLegs', 'InnerLegs'
```

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Force autocomplete | `Ctrl+Space` |
| Parameter hints | `Ctrl+Shift+Space` |
| Go to definition | `F12` |
| Peek definition | `Alt+F12` |
| Show all references | `Shift+F12` |
| Reload VS Code | `Ctrl+Shift+P` → "Reload" |

## Files Created

```
✅ stubs/Mobiles.pyi (13KB) - Comprehensive API
✅ stubs/System.pyi (3.3KB) - Enhanced .NET types
✅ stubs/MOBILES_GUIDE.md - Complete reference
✅ .vscode/settings.json - Pylance config
✅ pyrightconfig.json - Type checking
✅ README_ENHANCED_INTELLISENSE.md - Full guide
✅ _demo_enhanced_intellisense.py - Examples
✅ .venv/ with autopep8, typing-extensions
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No autocomplete | Add `if False: from razorenhanced_stubs import *` |
| Still no autocomplete | Reload window: `Ctrl+Shift+P` → "Reload Window" |
| Pylance not active | Check bottom-right status bar for "Python" |
| Wrong interpreter | `Ctrl+Shift+P` → "Select Interpreter" → Choose `.venv` |

## Documentation

1. **SETUP_COMPLETE.md** - What was done
2. **README_ENHANCED_INTELLISENSE.md** - Complete guide
3. **stubs/MOBILES_GUIDE.md** - API reference with examples
4. **_demo_enhanced_intellisense.py** - Interactive demos

## Remember!

```python
# Add this to EVERY script you want IntelliSense in:
if False:
    from razorenhanced_stubs import *
```

The `if False:` ensures it **never runs** in Razor Enhanced, only Pylance reads it!

---

## 🎯 That's It!

**You're ready to code with full IntelliSense!**

Type `Mobiles.`, press `Ctrl+Space`, and watch the magic happen! ✨

---

**Quick Test:**
1. Create new file
2. Add: `if False: from razorenhanced_stubs import *`
3. Type: `filter = Mobiles.Filter()`
4. Type: `filter.` then `Ctrl+Space`
5. See all 25+ options! 🎉
