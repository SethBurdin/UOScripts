"""Razor Enhanced Mobiles API Type Stubs"""

from typing import List, Optional

class Mobile:
    """Represents a mobile entity"""
    Serial: int
    Name: str
    Position: "Position"
    Hits: int
    HitsMax: int
    Mana: int
    ManaMax: int
    Stamina: int
    StaminaMax: int
    Notoriety: int
    Body: int
    Color: int
    Direction: str
    Poisoned: bool
    Paralized: bool
    YellowHits: bool
    Female: bool
    Warmode: bool
    Backpack: "Container"
    Flying: bool
    PropsUpdated: bool
    
    def DistanceTo(self, mobile_or_item) -> int: ...

class Position:
    X: int
    Y: int
    Z: int

class Container:
    Serial: int
    Contains: list

class MobileFilter:
    """Filter for finding mobiles"""
    Enabled: bool
    RangeMin: int
    RangeMax: int
    Notorieties: List[int]
    Bodies: List[int]
    Name: str
    Serials: List[int]
    CheckLineOfSight: bool
    CheckIgnoreObject: bool
    Friend: int
    Paralized: int
    Poisoned: int
    Female: int
    Warmode: int

def Filter() -> MobileFilter:
    """Create a new mobile filter"""
    ...

def ApplyFilter(filter: MobileFilter) -> List[Mobile]:
    """Apply a filter and return matching mobiles"""
    ...

def FindBySerial(serial: int) -> Optional[Mobile]:
    """Find a mobile by serial number"""
    ...

def Select(mobiles: List[Mobile], selector: str) -> Optional[Mobile]:
    """Select a mobile from list using selector: 'Nearest', 'Farthest', 'Weakest', 'Strongest'"""
    ...

def UseMobile(serial: int) -> None:
    """Use/double-click a mobile"""
    ...

def SingleClick(serial: int) -> None:
    """Single click a mobile"""
    ...

def ContextMenu(serial: int, entry: int) -> None:
    """Use a context menu entry on a mobile"""
    ...

def GetPropValue(serial: int, propName: str) -> str:
    """Get a property value from a mobile"""
    ...

def GetPropStringByIndex(serial: int, index: int) -> str:
    """Get a property string by index"""
    ...

def GetPropStringList(serial: int) -> List[str]:
    """Get all property strings for a mobile"""
    ...

def WaitForProps(serial: int, delay: int) -> None:
    """Wait for mobile properties to load"""
    ...

def Message(serial: int, hue: int, message: str) -> None:
    """Display a message above a mobile"""
    ...

def IgnoreObject(serial: int) -> None:
    """Add a mobile to the ignore list"""
    ...
