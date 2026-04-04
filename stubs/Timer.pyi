"""Razor Enhanced Timer API Type Stubs"""

def Create(name: str, duration: int) -> None:
    """Create a timer with name and duration in milliseconds"""
    ...

def Check(name: str) -> bool:
    """Check if a timer has expired"""
    ...

def Close(name: str) -> None:
    """Close/remove a timer"""
    ...

def Pause(name: str, pause: bool) -> None:
    """Pause or unpause a timer"""
    ...

def Exists(name: str) -> bool:
    """Check if a timer exists"""
    ...

def Running(name: str) -> bool:
    """Check if a timer is running"""
    ...
