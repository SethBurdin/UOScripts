"""Razor Enhanced Misc API Type Stubs"""

from typing import List, Tuple, Optional

def Pause(milliseconds: int) -> None:
    """Pause script execution for specified milliseconds"""
    ...

def SendMessage(message: str, hue: int = 945) -> None:
    """Send a message to the game window"""
    ...

def ScriptRun(scriptName: str) -> None:
    """Run another script"""
    ...

def ScriptStop(scriptName: str) -> None:
    """Stop a running script"""
    ...

def ScriptStatus(scriptName: str) -> bool:
    """Check if a script is running"""
    ...

def Beep() -> None:
    """Play a beep sound"""
    ...

def Distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """Calculate distance between two points"""
    ...

def ShardName() -> str:
    """Get the shard name"""
    ...

def CheckSharedValue(name: str) -> bool:
    """Check if a shared value exists"""
    ...

def GetSharedValue(name: str) -> object:
    """Get a shared value"""
    ...

def SetSharedValue(name: str, value: object) -> None:
    """Set a shared value"""
    ...

def RemoveSharedValue(name: str) -> None:
    """Remove a shared value"""
    ...

def ReadSharedValue(name: str) -> object:
    """Read a shared value (same as GetSharedValue)"""
    ...

def ClearShared() -> None:
    """Clear all shared values"""
    ...

def CurrentScriptDirectory() -> str:
    """Get the current script directory"""
    ...

def ResponsePrompt(prompt: str) -> None:
    """Respond to a prompt"""
    ...

def WaitForContext(serial: int, delay: int) -> bool:
    """Wait for context menu"""
    ...

def ContextReply(serial: int, entry: int) -> None:
    """Reply to context menu"""
    ...

def CloseMenu() -> None:
    """Close current menu"""
    ...

def WaitForMenu(delay: int) -> bool:
    """Wait for menu to appear"""
    ...

def MenuResponse(gumpValue: int, index: int = 0) -> None:
    """Respond to a menu"""
    ...

def Resync() -> None:
    """Force a resync"""
    ...

def UseContextMenu(serial: int, entry: int) -> None:
    """Use a context menu entry"""
    ...

def WaitForTarget(delay: int) -> bool:
    """Wait for a target cursor"""
    ...

def NoOperation() -> None:
    """Send a no-op packet"""
    ...

def ClearIgnore() -> None:
    """Clear the ignore list"""
    ...

def IgnoreObject(serial: int) -> None:
    """Add object to ignore list"""
    ...

def Message(message: str, hue: int = 945) -> None:
    """Display a message (same as SendMessage)"""
    ...

def PetRename(serial: int, name: str) -> None:
    """Rename a pet"""
    ...
