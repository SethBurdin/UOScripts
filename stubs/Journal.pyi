"""Razor Enhanced Journal API Type Stubs"""

from typing import List

class JournalEntry:
    """Represents a journal entry"""
    Text: str
    Color: int
    Serial: int
    Name: str
    Timestamp: str

def GetJournalEntry(index: int) -> JournalEntry:
    """Get a journal entry by index"""
    ...

def GetTextByColor(color: int) -> str:
    """Get journal text by color"""
    ...

def GetTextByName(name: str) -> str:
    """Get journal text by speaker name"""
    ...

def GetLineText(index: int) -> str:
    """Get journal line text by index"""
    ...

def Search(text: str) -> bool:
    """Search for text in journal"""
    ...

def SearchByColor(text: str, color: int) -> bool:
    """Search for text with specific color"""
    ...

def SearchByName(text: str, name: str) -> bool:
    """Search for text by speaker name"""
    ...

def SearchByType(text: str, entryType: str) -> bool:
    """Search for text by type"""
    ...

def WaitJournal(text: str, delay: int) -> bool:
    """Wait for text to appear in journal"""
    ...

def GetLineCount() -> int:
    """Get total number of journal lines"""
    ...

def Clear() -> None:
    """Clear the journal"""
    ...
