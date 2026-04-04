"""Razor Enhanced Player API Type Stubs"""

from typing import Optional

class Position:
    """Player position information"""
    X: int
    Y: int
    Z: int

class Container:
    """Container object (like backpack)"""
    Serial: int
    Contains: list

# Player properties
Name: str
Serial: int
Position: Position
Hits: int
HitsMax: int
MaxHits: int
Mana: int
ManaMax: int
MaxMana: int
Stamina: int
StaminaMax: int
MaxStamina: int
Mount: int | None
Backpack: Container
Weight: int
MaxWeight: int
Gold: int
Followers: int
FollowersMax: int
FireResist: int
ColdResist: int
PoisonResist: int
EnergyResist: int
Luck: int
TithingPoints: int
StatCap: int
Str: int
Dex: int
Int: int
AR: int
SpellDamageIncrease: int

# Player methods
def GetSkillValue(skillName: str) -> float:
    """Get the current skill value for a skill"""
    ...

def GetSkillCap(skillName: str) -> float:
    """Get the skill cap for a skill"""
    ...

def UseSkill(skillName: str) -> None:
    """Use a skill by name"""
    ...

def SetSkillStatus(skillName: str, status: str) -> None:
    """Set skill lock status: 'up', 'down', 'locked'"""
    ...

def HeadMessage(color: int, message: str) -> None:
    """Display a message above the player's head"""
    ...

def ChatSay(hue: int, message: str) -> None:
    """Send a message to chat"""
    ...

def ChatParty(message: str) -> None:
    """Send a message to party chat"""
    ...

def ChatGuild(message: str) -> None:
    """Send a message to guild chat"""
    ...

def ChatAlliance(message: str) -> None:
    """Send a message to alliance chat"""
    ...

def GetItemOnLayer(layerName: str) -> int:
    """Get the serial of an item on a specific layer"""
    ...

def DistanceTo(mobile_or_item) -> int:
    """Get distance to a mobile or item"""
    ...

def InRangeMobile(serial: int, distance: int) -> bool:
    """Check if a mobile is in range"""
    ...

def InRangeItem(serial: int, distance: int) -> bool:
    """Check if an item is in range"""
    ...

def CheckLayer(layerName: str) -> bool:
    """Check if a layer has an item equipped"""
    ...

def IsGhost() -> bool:
    """Check if player is dead"""
    ...

def Poisoned() -> bool:
    """Check if player is poisoned"""
    ...

def Paralized() -> bool:
    """Check if player is paralyzed"""
    ...

def YellowHits() -> bool:
    """Check if player has yellow hits"""
    ...

def Walk(direction: str) -> None:
    """Walk in a direction: 'Up', 'Down', 'Left', 'Right', 'North', 'South', 'East', 'West'"""
    ...

def Run(direction: str) -> None:
    """Run in a direction"""
    ...

def SetWarMode(warmode: bool) -> None:
    """Set war mode on/off"""
    ...

def IsGhost() -> bool:
    """Check if player is a ghost (dead)"""
    ...

def GetRealSkillValue(skillName: str) -> float:
    """Get real skill value (not buffed)"""
    ...

def Direction() -> str:
    """Get player direction"""
    ...

Direction: str  # Player direction property
Self: int  # Player's own serial number
WarMode: bool  # Whether player is in war mode
