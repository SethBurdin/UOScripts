# Enhanced Pylance Support for Razor Enhanced

This directory has been configured with **comprehensive IntelliSense support** for Razor Enhanced Python scripting! 🎉

## What's Been Enhanced

### ✅ Complete Type Stubs
- **Full Mobiles API** with all 40+ Mobile properties, 25+ Filter properties, and all methods
- **System types** for .NET interop (UInt16, UInt32, Byte, List, etc.)
- **Player, Items, Misc, Target, Spells, Journal, Gumps, Timer** modules
- Proper type hints with `@overload` for flexible parameters
- Comprehensive documentation on every property and method

### ✅ Optimized VS Code Configuration
- Pylance set to "basic" type checking (helpful without being annoying)
- Stub path configured for automatic discovery
- Inlay hints enabled for better code understanding
- Autocomplete optimized for Razor Enhanced patterns

### ✅ Development Tools
- Python virtual environment (`.venv`) with dev packages
- autopep8 for code formatting
- typing-extensions for advanced type hints
- Latest pip for package management

## Quick Start - Get IntelliSense in 10 Seconds

### Option 1: Use `if False:` (Recommended)

Add this at the top of ANY script:

```python
if False:  # IDE only - never runs in Razor Enhanced
    from razorenhanced_stubs import *

# Your code here - now with full autocomplete!
filter = Mobiles.Filter()
filter.RangeMax = 12  # Type 'filter.' to see all 25+ options!
```

The `if False:` ensures this import **never executes** in Razor Enhanced, but Pylance still reads it for IntelliSense.

### Option 2: Runtime-Safe Import

```python
try:
    from razorenhanced_stubs import *
except:
    pass  # Razor Enhanced provides these as globals
```

Both work identically - use whichever you prefer!

## What You Get

### 🎯 Autocomplete Everywhere

Type these and watch the magic:

- **`Mobiles.`** - See all methods (ApplyFilter, FindBySerial, Select, UseMobile, etc.)
- **`mobile.`** - See all properties (Name, Hits, Mana, Notoriety, Poisoned, WarMode, Position, etc.)
- **`filter.`** - See all filter options (RangeMax, Notorieties, Bodies, CheckLineOfSight, etc.)
- **`Player.`** - All player properties and methods
- **`Items.`** - All item operations
- **`Misc.`** - Utility functions

### 📋 Parameter Hints

Know exactly what to pass:

```python
Mobiles.Message(serial: int, hue: int, message: str, wait: bool = True)
                 └─ Shows types for every parameter!
```

### 📚 Hover Documentation

Hover over any property/method to see:
- What it does
- Parameter types
- Return type
- Valid values (for notoriety, selectors, etc.)

### ⚠️ Smart Warnings

Get helpful hints without false errors:
- Type mismatches shown as "information" (not errors)
- No complaints about IronPython patterns
- Reports actual issues while ignoring framework quirks

## Examples

### Find Hostile Enemies with Full Autocomplete

```python
if False:
    from razorenhanced_stubs import *

def find_enemy():
    filter = Mobiles.Filter()
    filter.Enabled = True
    filter.RangeMax = 12
    filter.Notorieties.Add(6)  # Red/hostile - autocomplete shows .Add()!
    filter.CheckLineOfSight = True
    
    enemies = Mobiles.ApplyFilter(filter)  # Autocomplete knows return type!
    
    if enemies.Count > 0:
        target = Mobiles.Select(enemies, 'Nearest')  # Autocomplete shows selectors!
        if target:
            # All these properties have autocomplete:
            print(f"Target: {target.Name}")
            print(f"HP: {target.Hits}/{target.HitsMax}")
            print(f"Distance: {target.DistanceTo(Player)}")
            Player.Attack(target)
            return True
    return False

find_enemy()
```

### Monitor Pet Health

```python
if False:
    from razorenhanced_stubs import *

filter = Mobiles.Filter()
filter.Enabled = True
filter.RangeMax = 12
filter.Notorieties.Add(2)  # Green/friend

pets = Mobiles.ApplyFilter(filter)

for pet in pets:
    # Autocomplete on every property!
    health_pct = (pet.Hits / pet.HitsMax * 100) if pet.HitsMax > 0 else 0
    
    if health_pct < 50:
        Misc.SendMessage(f"{pet.Name} needs healing: {health_pct:.0f}%", 33)
        
    if pet.Poisoned:
        Misc.SendMessage(f"{pet.Name} is poisoned!", 33)
```

## File Structure

```
Scripts/
├── .venv/                          # Python virtual environment
├── .vscode/
│   └── settings.json              # Pylance configuration ✨ Enhanced
├── stubs/                         # Type stub files
│   ├── Mobiles.pyi               # ✨ FULLY ENHANCED - 500+ lines!
│   ├── System.pyi                # ✨ Enhanced with .NET types
│   ├── Player.pyi
│   ├── Items.pyi
│   ├── Misc.pyi
│   ├── Target.pyi
│   ├── Spells.pyi
│   ├── Journal.pyi
│   ├── Gumps.pyi
│   ├── Timer.pyi
│   ├── __init__.pyi
│   ├── py.typed                  # ✨ NEW - Marks typed package
│   ├── README.md                 # Stub documentation
│   └── MOBILES_GUIDE.md          # ✨ NEW - Complete Mobiles reference
├── pyrightconfig.json            # ✨ Enhanced - Basic type checking
├── razorenhanced_stubs.py        # ✨ Enhanced - Import helper
├── _demo_enhanced_intellisense.py # ✨ NEW - Interactive demo
└── [your scripts here]
```

## Key Files Explained

### `stubs/Mobiles.pyi` - The Star of the Show ⭐
- **500+ lines** of comprehensive type definitions
- All Mobile properties with descriptions
- All Mobiles.Filter properties  
- All module methods with overloads
- Includes notoriety guide, selector options, layer names
- Full documentation on every item

### `.vscode/settings.json`
- Pylance configured for "basic" type checking
- Inlay hints enabled
- Stub paths configured
- Diagnostic severity optimized for Razor Enhanced

### `pyrightconfig.json`
- Python 2.7 compatibility (for IronPython)
- Stub path set
- Error reporting tuned for helpful feedback without noise

### `razorenhanced_stubs.py`
- Import helper for easy IntelliSense
- TYPE_CHECKING block ensures IDE-only imports
- Re-exports common types for convenience

## Testing Your Setup

### 1. Create a Test Script

```python
if False:
    from razorenhanced_stubs import *

# Type this and watch autocomplete:
filter = Mobiles.
#                ^ Put cursor here and press Ctrl+Space
```

You should see a popup with all Mobiles methods!

### 2. Test Mobile Properties

```python
if False:
    from razorenhanced_stubs import *

mobiles = Mobiles.ApplyFilter(Mobiles.Filter())
if mobiles.Count > 0:
    m = mobiles[0]
    m.
#     ^ Put cursor here and press Ctrl+Space
```

You should see Name, Hits, Mana, Notoriety, and 40+ more properties!

### 3. Test Parameter Hints

```python
if False:
    from razorenhanced_stubs import *

Mobiles.Message(
#               ^ Start typing here and see parameter hints
```

You should see: `(serial: int, hue: int, message: str, wait: bool = True)`

## Troubleshooting

### Autocomplete Not Working?

1. **Check the import is present:**
   ```python
   if False:
       from razorenhanced_stubs import *
   ```

2. **Reload VS Code:**
   - Press `Ctrl+Shift+P`
   - Type "Reload Window"
   - Press Enter

3. **Verify Pylance is active:**
   - Look at the bottom-right of VS Code
   - Should see "Python" with a version number

4. **Check Python interpreter:**
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose the one with `.venv`

5. **Force autocomplete:**
   - Press `Ctrl+Space` to manually trigger

### Still Having Issues?

Check these files:
- `.vscode/settings.json` - Should have `"python.languageServer": "Pylance"`
- `pyrightconfig.json` - Should have `"stubPath": "stubs"`
- `stubs/Mobiles.pyi` - Should exist and be ~500 lines
- `stubs/py.typed` - Should exist (even if empty-ish)

## Advanced Usage

### Custom Type Hints in Your Scripts

You can add type hints to your own functions:

```python
if False:
    from razorenhanced_stubs import *
    from typing import Optional

def find_nearest_enemy() -> Optional[Mobile]:
    """Find nearest hostile mobile"""
    filter = Mobiles.Filter()
    filter.Enabled = True
    filter.RangeMax = 12
    filter.Notorieties.Add(6)
    
    enemies = Mobiles.ApplyFilter(filter)
    if enemies.Count > 0:
        return Mobiles.Select(enemies, 'Nearest')
    return None

# Pylance knows this returns Optional[Mobile]!
enemy = find_nearest_enemy()
if enemy:
    enemy.  # <- Autocomplete works here too!
```

### Type Checking from Command Line

You can run type checking from the terminal:

```bash
# Activate venv
.\.venv\Scripts\Activate.ps1

# Install pyright
pip install pyright

# Check a script
pyright your_script.py
```

### Stricter Type Checking

Edit `pyrightconfig.json` and change:

```json
"typeCheckingMode": "strict"
```

This will show more type warnings (may flag valid IronPython patterns).

## Documentation

### Comprehensive Guides
- **[stubs/MOBILES_GUIDE.md](stubs/MOBILES_GUIDE.md)** - Complete Mobiles API reference with examples
- **[stubs/README.md](stubs/README.md)** - General stub file documentation

### Demo Scripts  
- **[_demo_enhanced_intellisense.py](_demo_enhanced_intellisense.py)** - Interactive examples

### External Resources
- [Razor Enhanced Official Docs](http://razorenhanced.net/)
- [Python Type Hints - PEP 484](https://peps.python.org/pep-0484/)
- [Pylance Documentation](https://github.com/microsoft/pylance-release)

## What Packages Are Installed?

Your `.venv` includes:
- **pip** (26.0.1) - Package manager
- **autopep8** (2.3.2) - Code formatter
- **pycodestyle** (2.14.0) - Style checker (used by autopep8)
- **typing-extensions** (4.15.0) - Advanced type hint support

## Contributing & Extending

### Adding Missing APIs

If Razor Enhanced adds new features, update the stubs:

1. Open the appropriate `.pyi` file (e.g., `stubs/Mobiles.pyi`)
2. Add the new method/property following the existing pattern
3. Include type hints and documentation
4. Reload VS Code

Example:
```python
def NewMethod(param1: str, param2: int) -> bool:
    """Description of what it does
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Description of return value
    """
    ...
```

### Improving Type Hints

If you find better types for existing definitions, please update them!

## FAQ

**Q: Will this break my existing scripts?**  
A: No! The `if False:` or `try/except` ensures imports never run in Razor Enhanced.

**Q: Do I need to add the import to every script?**  
A: Only if you want IntelliSense in that script. It's completely optional.

**Q: Can I use this with other Razor Enhanced scripts from the internet?**  
A: Yes! Just add the import line to any script and get instant IntelliSense.

**Q: Does this work with IronPython 2.7?**  
A: Yes! The configuration is set for Python 2.7 compatibility.

**Q: Will this slow down Razor Enhanced?**  
A: No! The imports only exist for Pylance (the IDE), never at runtime.

**Q: Can I package this with my scripts?**  
A: Yes! Share your `stubs/` directory and configuration files.

## Credits

- **Razor Enhanced** - Amazing UO assistant
- **Microsoft Pylance** - Powerful Python language server
- **VS Code** - Best editor for Python development

---

## 🎉 Enjoy Your Enhanced Coding Experience!

You now have **professional-grade IntelliSense** for Razor Enhanced scripting. Type faster, make fewer mistakes, and discover APIs you didn't know existed!

**Happy scripting!** 🐍⚔️🏰

---

**Setup Date:** March 2026  
**Python Version:** 2.7 (IronPython compatible)  
**VS Code Extension:** Pylance  
**Type Checking:** Basic (balanced)
