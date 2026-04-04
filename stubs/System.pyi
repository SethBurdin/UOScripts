""".NET System Types for IronPython"""

from typing import TypeVar, Generic, overload

T = TypeVar('T')

class Byte:
    """System.Byte type (0-255)"""
    def __init__(self, value: int): ...
    def __int__(self) -> int: ...
    def __repr__(self) -> str: ...

class UInt16:
    """System.UInt16 type (0-65535)"""
    def __init__(self, value: int): ...
    def __int__(self) -> int: ...
    def __repr__(self) -> str: ...

class UInt32:
    """System.UInt32 type (0-4294967295)"""
    def __init__(self, value: int): ...
    def __int__(self) -> int: ...
    def __repr__(self) -> str: ...

class Int32:
    """System.Int32 type"""
    def __init__(self, value: int): ...
    def __int__(self) -> int: ...
    def __repr__(self) -> str: ...

class String(str):
    """System.String type"""
    pass

class Collections:
    """System.Collections namespace"""
    
    class Generic:
        """System.Collections.Generic namespace"""
        
        class List(Generic[T]):
            """Generic list type compatible with IronPython
            
            Usage:
                from System.Collections.Generic import List
                mobiles = List[Mobile]()
                mobiles.Add(mobile)
            """
            def __init__(self): ...
            
            def Add(self, item: T) -> None:
                """Add an item to the list"""
                ...
            
            def AddRange(self, items) -> None:
                """Add multiple items to the list"""
                ...
            
            def Remove(self, item: T) -> bool:
                """Remove an item from the list. Returns True if found"""
                ...
            
            def RemoveAt(self, index: int) -> None:
                """Remove item at specific index"""
                ...
            
            def Clear(self) -> None:
                """Remove all items from the list"""
                ...
            
            def Contains(self, item: T) -> bool:
                """Check if list contains an item"""
                ...
            
            def IndexOf(self, item: T) -> int:
                """Get index of item, or -1 if not found"""
                ...
            
            def Insert(self, index: int, item: T) -> None:
                """Insert item at specific index"""
                ...
            
            @property
            def Count(self) -> int:
                """Get number of items in list"""
                ...
            
            def __getitem__(self, index: int) -> T: ...
            def __setitem__(self, index: int, value: T) -> None: ...
            def __iter__(self): ...
            def __len__(self) -> int: ...
            def __contains__(self, item: T) -> bool: ...

class DateTime:
    """System.DateTime type"""
    Year: int
    Month: int
    Day: int
    Hour: int
    Minute: int
    Second: int
    
    @staticmethod
    def Now() -> "DateTime":
        """Get current date and time"""
        ...
    
    def ToString(self) -> str:
        """Convert to string"""
        ...

__all__ = [
    'Byte',
    'UInt16', 
    'UInt32',
    'Int32',
    'String',
    'Collections',
    'DateTime',
]
