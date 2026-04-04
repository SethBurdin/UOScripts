"""Razor Enhanced Gumps API Type Stubs"""

from typing import List, Optional

class GumpData:
    """Represents gump data"""
    Serial: int
    GumpID: int
    X: int
    Y: int
    
def WaitForGump(gumpID: int, delay: int) -> bool:
    """Wait for a specific gump to appear"""
    ...

def SendAction(gumpID: int, buttonID: int) -> None:
    """Send a button press action to a gump"""
    ...

def SendAdvanced(gumpSerial: int, gumpID: int, buttonID: int, switches: List[int], entries: List[tuple]) -> None:
    """Send advanced gump response with switches and text entries"""
    ...

def CloseGump(gumpID: int) -> None:
    """Close a gump"""
    ...

def ResetGump() -> None:
    """Reset gump tracking"""
    ...

def HasGump() -> bool:
    """Check if any gump is open"""
    ...

def CurrentGump() -> int:
    """Get current gump ID"""
    ...

def LastGumpSerial() -> int:
    """Get serial of last gump"""
    ...

def LastGumpID() -> int:
    """Get ID of last gump"""
    ...

def LastGumpGetLine(lineNumber: int) -> str:
    """Get a line of text from last gump"""
    ...

def LastGumpTextEntry(entryID: int, text: str) -> None:
    """Set text entry value for last gump"""
    ...

def LastGumpGetLineList() -> List[str]:
    """Get all lines from last gump"""
    ...
