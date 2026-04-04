""".NET System.Collections.Generic namespace stub"""

from typing import TypeVar, Generic as PyGeneric, Iterator, overload

T = TypeVar('T')

class List(PyGeneric[T]):
    """System.Collections.Generic.List<T>"""
    
    @overload
    def __init__(self) -> None: ...
    
    @overload
    def __init__(self, capacity: int) -> None: ...

    def __init__(self, capacity: int = 0) -> None: ...
    
    def Add(self, item: T) -> None:
        """Add an item to the list"""
        ...
    
    def Remove(self, item: T) -> bool:
        """Remove an item from the list"""
        ...
    
    def Clear(self) -> None:
        """Clear all items from the list"""
        ...
    
    def Contains(self, item: T) -> bool:
        """Check if item is in the list"""
        ...
    
    @property
    def Count(self) -> int:
        """Get the count of items"""
        ...
    
    def __getitem__(self, index: int) -> T: ...
    def __setitem__(self, index: int, value: T) -> None: ...
    def __iter__(self) -> Iterator[T]: ...
    def __len__(self) -> int: ...
