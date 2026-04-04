""".NET System namespace stub"""

from typing import TypeVar, Generic, overload

T = TypeVar('T')

# System.Byte
class Byte:
    """System.Byte type (8-bit unsigned integer)"""
    def __init__(self, value: int): ...
    def __int__(self) -> int: ...
    def __str__(self) -> str: ...
