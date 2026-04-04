"""Scripts.glossary.tameables module stub"""

from typing import Any, List, Set, Tuple

def GetAnimalIDsAtOrOverTamingDifficulty(difficulty: int) -> List[int]:
    """Get list of animal IDs at or above the given taming difficulty"""
    ...

def GetAnimalIDsForPlayerSkill(playerTamingSkill: float, minimumTamingDifficulty: int = 0) -> List[int]:
    """Get list of animal body IDs appropriate for the player's current skill level"""
    ...

def GetValidAnimalPairsForPlayerSkill(playerTamingSkill: float, minimumTamingDifficulty: int = 0) -> Set[Tuple[int, int]]:
    """Get set of (mobileID, color) tuples for animals valid at the given skill level"""
    ...

def GetValidAnimalNamesForPlayerSkill(playerTamingSkill: float, minimumTamingDifficulty: int = 0) -> Set[str]:
    """Get set of lowercase animal names valid at the given skill level"""
    ...

def GetBlueSpawningBodyIDsForPlayerSkill(playerTamingSkill: float, minimumTamingDifficulty: int = 0) -> Set[int]:
    """Get set of body IDs for animals that spawn blue (notoriety 1) and are valid at the given skill level"""
    ...

# Add tameable animal definitions as needed
