
# glossary/skills.py
# Confirmed UO skill name strings for use with Player skill API calls.
#
# Usage:
#   from glossary.skills import skills
#   cap = Player.GetSkillCap(skills['Tailoring'])
#
# Player skill API (all take the skill name string as argument):
#   Player.GetSkillValue(name)      -> float  current effective value (0.0–120.0)
#   Player.GetRealSkillValue(name)  -> float  base value without temporary buffs
#   Player.GetSkillCap(name)        -> float  per-skill cap (100 default, up to 120 with power scrolls)

skills = {
    # ── Combat ───────────────────────────────────────────────────────────────
    'Anatomy':          'Anatomy',
    'Arms Lore':        'Arms Lore',
    'Archery':          'Archery',
    'Bushido':          'Bushido',
    'Chivalry':         'Chivalry',
    'Fencing':          'Fencing',
    'Healing':          'Healing',
    'Mace Fighting':    'Mace Fighting',
    'Ninjitsu':         'Ninjitsu',
    'Parrying':         'Parrying',
    'Swordsmanship':    'Swordsmanship',
    'Tactics':          'Tactics',
    'Wrestling':        'Wrestling',

    # ── Magic ─────────────────────────────────────────────────────────────────
    'Evaluate Intelligence': 'Evaluate Intelligence',
    'Focus':            'Focus',
    'Magery':           'Magery',
    'Meditation':       'Meditation',
    'Mysticism':        'Mysticism',
    'Necromancy':       'Necromancy',
    'Spellweaving':     'Spellweaving',
    'Spirit Speak':     'Spirit Speak',

    # ── Stealth / Rogue ───────────────────────────────────────────────────────
    'Detecting Hidden': 'Detecting Hidden',
    'Hiding':           'Hiding',
    'Ninjitsu':         'Ninjitsu',
    'Poisoning':        'Poisoning',
    'Remove Trap':      'Remove Trap',
    'Snooping':         'Snooping',
    'Stealing':         'Stealing',
    'Stealth':          'Stealth',

    # ── Crafting ──────────────────────────────────────────────────────────────
    'Blacksmith':       'Blacksmith',
    'Carpentry':        'Carpentry',
    'Cartography':      'Cartography',
    'Cooking':          'Cooking',
    'Fletching':        'Fletching',
    'Inscription':      'Inscription',
    'Tailoring':        'Tailoring',
    'Tinkering':        'Tinkering',

    # ── Gathering ─────────────────────────────────────────────────────────────
    'Fishing':          'Fishing',
    'Lumberjacking':    'Lumberjacking',
    'Mining':           'Mining',

    # ── Lore / Knowledge ──────────────────────────────────────────────────────
    'Alchemy':          'Alchemy',
    'Animal Lore':      'Animal Lore',
    'Animal Taming':    'Animal Taming',
    'Discordance':      'Discordance',
    'Forensic Evaluation': 'Forensic Evaluation',
    'Herding':          'Herding',
    'Item ID':          'Item ID',
    'Peacemaking':      'Peacemaking',
    'Provocation':      'Provocation',
    'Tracking':         'Tracking',
    'Veterinary':       'Veterinary',
}
