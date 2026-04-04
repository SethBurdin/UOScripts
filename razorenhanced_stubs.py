"""
Razor Enhanced API Import Helper - Enhanced Edition

Import this at the top of your scripts to get full IntelliSense support in VS Code.
These imports won't be executed at runtime because Razor Enhanced injects
these modules as globals, but they help Pylance understand your code.

Usage:
    # Add at the top of any script for IntelliSense:
    if False:  # IDE only, never runs
        from razorenhanced_stubs import *

Alternative (runtime-safe):
    try:
        from razorenhanced_stubs import *
    except:
        pass  # Razor Enhanced provides these as globals at runtime

The 'if False:' approach is preferred because it's clearer that it's IDE-only.
"""

# This will never actually run in Razor Enhanced, but Pylance will read it
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type checking only - these imports help IDEs understand the code
    # Import all Razor Enhanced API modules
    import Player as Player
    import Mobiles as Mobiles
    import Items as Items
    import Misc as Misc
    import Target as Target
    import Spells as Spells
    import Journal as Journal
    import Gumps as Gumps
    import Timer as Timer
    
    # Import commonly used System types
    from System import Byte, UInt16, UInt32, Int32, String
    from System.Collections.Generic import List
    
    # Re-export specific classes for easier access
    from Mobiles import Mobile, Filter as MobileFilter
    from Items import Item
    
    __all__ = [
        # API Modules
        'Player',
        'Mobiles',
        'Items',
        'Misc',
        'Target',
        'Spells',
        'Journal',
        'Gumps',
        'Timer',
        # System Types
        'Byte',
        'UInt16',
        'UInt32',
        'Int32',
        'String',
        'List',
        # Commonly Used Classes
        'Mobile',
        'MobileFilter',
        'Item',
    ]
