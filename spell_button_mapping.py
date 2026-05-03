# spell_button_mapping.py
# Auto-generated mapping of magery spell names to inscription gump button numbers for your shard.
# Use this mapping in your inscription automation scripts to ensure correct button presses.

SPELL_TO_BUTTON = {
    # Circle 1
    "Reactive Armor": 2,
    "Clumsy": 9,
    "Create Food": 16,
    "Feeblemind": 23,
    "Heal": 30,
    "Magic Arrow": 37,
    "Night Sight": 44,
    "Weaken": 51,
    # Circle 2
    "Agility": 58,
    "Cunning": 65,
    "Cure": 72,
    "Harm": 79,
    "Magic Trap": 86,
    "Magic Untrap": 93,
    "Protection": 100,
    "Strength": 107,
    # Circle 3  (navigate to Third-Fourth group first, then same slot buttons as circles 1-2)
    "Bless": 2,
    "Fireball": 9,
    "Magic Lock": 16,
    "Poison": 23,
    "Telekinesis": 30,
    "Teleport": 37,
    "Unlock": 44,
    "Wall of Stone": 51,
    # Circle 4
    "Arch Cure": 58,
    "Arch Protection": 65,
    "Curse": 72,
    "Fire Field": 79,
    "Greater Heal": 86,
    "Lightning": 93,
    "Mana Drain": 100,
    "Recall": 107,
    # Circle 5  (navigate to Fifth-Sixth group first)
    "Blade Spirits": 2,
    "Dispel Field": 9,
    "Incognito": 16,
    "Magic Reflection": 23,
    "Mind Blast": 30,
    "Paralyze": 37,
    "Poison Field": 44,
    "Summon Creature": 51,
    # Circle 6
    "Dispel": 58,
    "Energy Bolt": 65,
    "Explosion": 72,
    "Invisibility": 79,
    "Mark": 86,
    "Mass Curse": 93,
    "Paralyze Field": 100,
    "Reveal": 107,
    # Circle 7  (navigate to Seventh-Eighth group first)
    "Chain Lightning": 2,
    "Energy Field": 9,
    "Flamestrike": 16,
    "Gate Travel": 23,
    "Mana Vampire": 30,
    "Mass Dispel": 37,
    "Meteor Swarm": 44,
    "Polymorph": 51,
    # Circle 8
    "Earthquake": 58,
    "Energy Vortex": 65,
    "Resurrection": 72,
    "Summon Air Elemental": 79,
    "Summon Daemon": 86,
    "Summon Earth Elemental": 93,
    "Summon Fire Elemental": 100,
    "Summon Water Elemental": 107,
}

# Mapping of magery circle to the top menu button for that circle in the inscription gump
# Use this to ensure the script navigates to the correct circle before selecting a spell
CIRCLE_TOP_MENU_BUTTONS = {
    1: 1,    # Circle 1 (top menu button)
    2: 8,    # Circle 2
    3: 15,   # Circle 3
    4: 22,   # Circle 4
    5: 29,   # Circle 5
    6: 36,   # Circle 6
    7: 43,   # Circle 7
    8: 50,   # Circle 8
}

# Gump button mapping (inferred from macro recording)
# Allow multiple gump IDs for shard compatibility
CRAFT_GUMP_IDS = [0x9e26d92d]  # Only use gump IDs from your export
CRAFT_GUMP_ID = CRAFT_GUMP_IDS[0]  # Use the first as the default
