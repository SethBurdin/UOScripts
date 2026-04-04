"""Razor Enhanced Target API Type Stubs"""

from typing import Optional

def WaitForTarget(delay: int, useLastTarget: bool = False) -> bool:
    """Wait for target cursor to appear"""
    ...

def TargetExecute(serial: int) -> None:
    """Execute target on a serial"""
    ...

def TargetExecuteRelative(serial: int, distance: int) -> None:
    """Execute target at relative location"""
    ...

def Cancel() -> None:
    """Cancel current target"""
    ...

def Self() -> None:
    """Target self"""
    ...

def Last() -> None:
    """Target last target"""
    ...

def SetLast(serial: int) -> None:
    """Set last target"""
    ...

def GetLast() -> int:
    """Get last target serial"""
    ...

def GetLastAttack() -> int:
    """Get last attack target serial"""
    ...

def SetLastTarget(serial: int) -> None:
    """Set last target"""
    ...

def Attack(serial: int) -> None:
    """Attack a mobile"""
    ...

def AttackLast() -> None:
    """Attack last target"""
    ...

def GetTarget() -> Optional[int]:
    """Get current target serial"""
    ...

def TargetResource(serial: int, resourceID: int) -> None:
    """Target a resource type"""
    ...

def ClearQueue() -> None:
    """Clear target queue"""
    ...

def PromptTarget() -> int:
    """Prompt for target and return serial"""
    ...

def PromptTargetCancel() -> None:
    """Cancel prompt target"""
    ...

def PromptGroundTarget() -> tuple:
    """Prompt for ground target and return (x, y, z, graphic)"""
    ...

def HasTarget() -> bool:
    """Check if target cursor is active"""
    ...

def ClearLastandQueue() -> None:
    """Clear last target and queue"""
    ...
