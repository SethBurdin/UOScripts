"""Razor Enhanced Spells API Type Stubs"""

# Magery
def CastMagery(spellName: str) -> None:
    """Cast a magery spell by name"""
    ...

# Necromancy
def CastNecro(spellName: str) -> None:
    """Cast a necromancy spell by name"""
    ...

# Chivalry
def CastChivalry(spellName: str) -> None:
    """Cast a chivalry spell by name"""
    ...

# Bushido
def CastBushido(spellName: str) -> None:
    """Cast a bushido spell by name"""
    ...

# Ninjitsu
def CastNinjitsu(spellName: str) -> None:
    """Cast a ninjitsu spell by name"""
    ...

# Spellweaving
def CastSpellweaving(spellName: str) -> None:
    """Cast a spellweaving spell by name"""
    ...

# Mysticism
def CastMysticism(spellName: str) -> None:
    """Cast a mysticism spell by name"""
    ...

# Mastery
def CastMastery(spellName: str) -> None:
    """Cast a mastery spell by name"""
    ...

# General spell functions
def Cast(spellID: int) -> None:
    """Cast a spell by ID"""
    ...

def CastOnTarget(spellName: str, serial: int) -> None:
    """Cast a spell and target a serial"""
    ...

def Interrupt() -> None:
    """Interrupt current spell casting"""
    ...

def GetLastCastTime() -> int:
    """Get time since last spell cast in milliseconds"""
    ...
