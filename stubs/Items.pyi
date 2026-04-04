"""Razor Enhanced Items API Type Stubs"""

from typing import List, Optional

class Item:
    """Represents an item"""
    Serial: int
    ItemID: int
    Hue: int
    Color: int
    Amount: int
    Position: "Position"
    Container: int
    RootContainer: int
    Name: str
    Direction: str
    Movable: bool
    Visible: bool
    IsCorpse: bool
    IsDoor: bool
    Layer: str
    Contains: List["Item"]
    PropsUpdated: bool
    
    def DistanceTo(self, mobile_or_item) -> int: ...

class Position:
    X: int
    Y: int
    Z: int

class ItemFilter:
    """Filter for finding items"""
    Enabled: bool
    RangeMin: int
    RangeMax: int
    Graphics: List[int]
    Colors: List[int]
    Name: str
    Serials: List[int]
    CheckIgnoreObject: bool
    Movable: int
    IsCorpse: int
    OnGround: int

def Filter() -> ItemFilter:
    """Create a new item filter"""
    ...

def ApplyFilter(filter: ItemFilter) -> List[Item]:
    """Apply a filter and return matching items"""
    ...

def FindBySerial(serial: int) -> Optional[Item]:
    """Find an item by serial number"""
    ...

def FindByID(itemID: int, color: int, container: int, recursive: bool = False) -> Optional[Item]:
    """Find an item by ID and optional color in a container"""
    ...

def BackpackCount(itemID: int, color: int = -1) -> int:
    """Count items in backpack"""
    ...

def ContainerCount(container: int, itemID: int, color: int, recursive: bool = False) -> int:
    """Count items in a container"""
    ...

def Select(items: List[Item], selector: str) -> Optional[Item]:
    """Select an item from list using selector: 'Nearest', 'Farthest', 'Random'"""
    ...

def UseItem(serial: int) -> None:
    """Use/double-click an item"""
    ...

def SingleClick(serial: int) -> None:
    """Single click an item"""
    ...

def WaitForContents(container: int, delay: int) -> None:
    """Wait for container contents to load"""
    ...

def WaitForProps(serial: int, delay: int) -> None:
    """Wait for item properties to load"""
    ...

def UseItemByID(itemID: int, color: int = -1) -> None:
    """Use an item by ID from backpack"""
    ...

def Move(serial: int, container: int, amount: int, x: int = -1, y: int = -1) -> None:
    """Move an item to a container or location"""
    ...

def MoveOnGround(serial: int, amount: int, x: int, y: int, z: int) -> None:
    """Move an item to a ground location"""
    ...

def Drop(serial: int, x: int, y: int, z: int) -> None:
    """Drop an item at a location"""
    ...

def DropItemGroundSelf(serial: int, amount: int) -> None:
    """Drop item on ground at player location"""
    ...

def Equip(serial: int, layer: str) -> None:
    """Equip an item to a layer"""
    ...

def SetColor(itemID: int, color: int) -> None:
    """Set the color for finding items"""
    ...

def Message(serial: int, hue: int, message: str) -> None:
    """Display a message above an item"""
    ...

def Hide(serial: int) -> None:
    """Hide an item (client-side only)"""
    ...

def ContextMenu(serial: int, entry: int) -> None:
    """Use a context menu entry on an item"""
    ...

def GetPropValue(serial: int, propName: str) -> str:
    """Get a property value from an item"""
    ...

def GetPropStringByIndex(serial: int, index: int) -> str:
    """Get a property string by index"""
    ...

def GetPropStringList(serial: int) -> List[str]:
    """Get all property strings for an item"""
    ...

def Lift(serial: int, amount: int) -> None:
    """Lift an item"""
    ...
