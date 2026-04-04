"""
Razor Enhanced Global API for type checking.

This file makes all Razor Enhanced API modules available as builtins
so Pylance recognizes them when used without imports.
"""

# Import all stub modules to make them available
import Player
import Mobiles
import Items
import Misc
import Target
import Spells
import Journal
import Gumps

# Also export System types
from System import Byte
from System.Collections.Generic import List

__all__ = [
    'Player',
    'Mobiles', 
    'Items',
    'Misc',
    'Target',
    'Spells',
    'Journal',
    'Gumps',
    'Byte',
    'List',
]
