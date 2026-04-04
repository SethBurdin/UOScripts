# Razor Enhanced Python Type Stubs

This directory contains Python type stub files (`.pyi`) for the Razor Enhanced API. These stubs provide IntelliSense, autocomplete, and type checking support in VS Code with Pylance.

## Purpose

Razor Enhanced uses IronPython and injects its API modules (Player, Mobiles, Items, etc.) as **global variables** at runtime. Pylance can't see them during editing and shows "undefined" errors. These stub files solve that problem by defining the API interfaces.

## Quick Start - Two Options

### Option 1: Add IntelliSense Import (Recommended)

Add this at the top of your scripts:

```python
# IntelliSense support - won't execute at runtime
try:
    from razorenhanced_stubs import *
except:
    pass

# Now write your script with full autocomplete!
if Player.Mana > 50:
    Player.UseSkill('Meditation')
```

The `try/except` ensures it only runs during IDE analysis, not in Razor Enhanced.

### Option 2: Just Accept the Warnings

The stubs are configured - you can ignore Pylance's "not defined" warnings. Your scripts will still work perfectly in Razor Enhanced since it provides these as runtime globals.

## Included Modules

- **Player.pyi** - Player character (Mana, Hits, Position, Backpack, Walk, etc.)
- **Mobiles.pyi** - Mobiles/NPCs (Filter, FindBySerial, UseMobile, etc.)
- **Items.pyi** - Items (FindByID, UseItem, Move, etc.)
- **Misc.pyi** - Utilities (Pause, SendMessage, ClearIgnore, etc.)
- **Target.pyi** - Targeting (TargetExecute, Attack, WaitForTarget, etc.)
- **Spells.pyi** - Spell casting (CastMagery, CastChivalry, etc.)
- **Journal.pyi** - Journal/chat (Search, WaitJournal, Clear, etc.)
- **Gumps.pyi** - UI interaction (WaitForGump, SendAction, etc.)
- **Timer.pyi** - Timers (Create, Check, Close, etc.)
- **System.pyi** - .NET types (Byte, List, etc.)

## Benefits

✅ Autocomplete for Player, Mobiles, Items, Misc, etc.  
✅ Hover documentation for methods and properties  
✅ Type hints for function parameters  
✅ Better code navigation  
✅ Catch typos before runtime

## Configuration Files

These files make it work:

- `.vscode/settings.json` - Adds stubs to `python.analysis.extraPaths`
- `pyrightconfig.json` - Configures stub path and Python version
- `razorenhanced_stubs.py` - Import helper for IntelliSense

## Understanding the Setup

**The Problem**: Razor Enhanced uses IronPython and provides modules like `Player`, `Mobiles`, etc. as runtime globals. They don't exist as importable Python files, so Pylance can't find them.

**The Solution**: Type stub files (`.pyi`) define what these modules look like, and VS Code is configured to read them. This gives you IDE features without changing how scripts run in Razor Enhanced.

## Adding Missing APIs

If you use a Razor Enhanced API method not defined in the stubs, add it to the appropriate `.pyi` file:

```python
# In stubs/Player.pyi, add:
def YourMethodName(param: str) -> None:
    """Description of what it does"""
    ...
```

## References

- [Razor Enhanced API Docs](http://razorenhanced.net/)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Python Stub Files](https://mypy.readthedocs.io/en/stable/stubs.html)
