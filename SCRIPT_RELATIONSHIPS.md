# Script Relationships

This document describes how the scripts in this repository call and depend on each other.

---

## Architecture Overview

The repo is structured around a layered system. The root folder doubles as a `Scripts` Python package (how Razor Enhanced exposes it). Scripts fall into two categories:

1. **Entry-point macros** — standalone scripts run directly from the Razor Enhanced script panel
2. **Shared libraries** — modules in `glossary/` and `utilities/` imported by entry-point macros

```
Entry-point macros (root *.py)
         │
         ├── imports from ──► glossary/        (game data: colors, items, spells, enemies)
         │                         └── imports from ──► utilities/items.py
         │
         ├── imports from ──► utilities/        (helpers: items, mobiles, gumps)
         │                         └── imports from ──► config.py
         │
         ├── imports from ──► config.py         (tuning constants)
         │
         └── calls at runtime ──► other macros  (via Misc.ScriptRun)
```

---

## Shared Libraries

### `config.py`
Defines global timing constants: `journalEntryDelayMilliseconds`, `targetClearDelayMilliseconds`, `dragDelayMilliseconds`.

**Imported by:** `utilities/items.py` (and transitively everything it supports), plus directly by `disc.py`, `items_copyRuneBook.py`, `items_moveOnToStack.py`, `items_moveToNewContainer.py`, `junk logger.py`, `LumberJack.py`, `LumberJackgarg.py`, `organizer_moveToBag_reagents.py`, `organizer_restock_reagents_50.py`, `pvm_pvp_provocation.py`, `resource_itemIdentification.py`, `resource_smelting.py`, `resource_treasureChestPuller.py`, `skill_Fishing.py`, `skill_Lockpicking.py`, `SmeltContainer.py`, `smeltatest.py`, `train_Blacksmithy.py`, `train_Fishing.py`, `train_Healing.py` (via `Scripts.config`), `train_Magery.py`, `train_Peacemaking.py`, `train_Provocation.py`, `train_Veterinary.py` (via `Scripts.config`), `transferignots.py`, `ultimatemining.py`

---

### `utilities/` — Helper Functions

#### `utilities/items.py`
The most widely imported module. Provides:
- `myItem` class — base item data container
- `FindItem(itemID, container, color, ignoreContainer)` — recursive container search
- `FindNumberOfItems(itemID, container, color)` — count items recursively
- `MoveItem(Items, Misc, item, dest, amount)` — wraps `Items.Move` with a configured pause

**Imports:** `config.py`

**Imported by:**
- Almost all `glossary/items/*.py` modules (for `myItem`)
- `heal human.py`, `items_depositIntoBank.py`, `items_moveToNewContainer.py`, `items_unequipHands.py`, `items_useDagger.py`, `items_useFishingPole.py`, `items_useScissors.py`, `items_useSkinningKnife.py`
- `junk logger.py`, `LumberJack.py`, `LumberJackgarg.py`, `organizer_BODsIntoBooks.py`, `organizer_moveToBag_reagents.py`, `organizer_restock_reagents_50.py`, `organizer_spellScrolls.py`
- `pvm_pvp_healPets.py`, `resource_distributeTreasureMapLoot.py`, `resource_itemIdentification.py`, `resource_treasureChestPuller.py`
- `skill_Fishing.py`, `skill_Lockpicking.py`, `skill_Mining.py`, `SmeltContainer.py`, `smeltatest.py`
- `train_Blacksmithy.py`, `train_Carpentry.py`, `train_Cartography.py`, `train_Fishing.py`, `train_Lockpicking.py`, `train_Magery.py`, `train_Veterinary.py`
- `transferignots.py`, `ultimatemining.py`, `vet copy.py`
- All `glossary/crafting/*.py` modules

#### `utilities/mobiles.py`
Provides `GetEmptyMobileList` for building target lists.

**Imported by:** `pvm_pvp_attack_simple.py`, `pvm_pvp_provocation.py`

#### `utilities/gumps.py`
Provides `GumpSelection` for interacting with crafting gump menus.

**Imported by:** `glossary/crafting/blacksmithing.py`, `glossary/crafting/carpentry.py`, `glossary/crafting/cartography.py`, `glossary/crafting/tailoring.py`, `glossary/crafting/tinkering.py`

---

### `glossary/` — Game Data

#### `glossary/colors.py`
Color constants used for journal message filtering and visual feedback.

**Imported by:** nearly every entry-point macro, plus `glossary/crafting/*.py`

#### `glossary/enemies.py`
Provides `GetEnemies()` and `GetEnemyNotorieties()` — returns lists of hostile mobiles by notoriety.

**Imports:** `System.Collections.Generic.List`, `System.Byte`

**Imported by:** `animalinfo.py`, `disc.py`, `pvm_pvp_attack_simple.py`, `pvm_pvp_provocation.py`, `pvm_pvp_zombieland.py`, `taming.py`, `train_AnimalTaming.py`, `train_Peacemaking.py`, `train_Provocation.py`

#### `glossary/spells.py`
Spell data dictionary (maps spell names to reagent requirements, etc.).

**Imports:** `glossary/items/reagents.py`

**Imported by:** `animalinfo.py`, `disc.py`, `organizer_spellScrolls.py`, `taming.py`, `train_AnimalTaming.py`, `train_Magery.py`

#### `glossary/tameables.py`
List of tameable creature types and their stats.

**Imports:** `System.Collections.Generic.List`, `System.Int32`

**Imported by:** `animalinfo.py`, `disc.py`, `taming.py`, `train_AnimalTaming.py`

#### `glossary/gumps.py`
Gump interaction helpers (separate from `utilities/gumps.py`).

#### `glossary/razorEnhancedClassMasterSingleton.py`
Singleton wrapper for Razor Enhanced API class instances.

---

### `glossary/items/` — Item Data Modules

Each module defines a dictionary (or class instances) of in-game item IDs and properties. Most only import `myItem` from `utilities/items.py`.

| Module | Exports | Also imports |
|---|---|---|
| `armor.py` | `armor` dict | `utilities/items.myItem` |
| `bodyParts.py` | body part items | `utilities/items.myItem` |
| `cloth.py` | cloth items | `utilities/items.myItem` |
| `clothing.py` | `clothingInTreasureChests` | `utilities/items.myItem` |
| `containers.py` | `FindHatch`, `FindTrashBarrel` | `utilities/items.myItem`, `System` |
| `decorations.py` | decoration items | `utilities/items.myItem` |
| `deeds.py` | deed items | `utilities/items.myItem` |
| `food.py` | food items | `utilities/items.myItem` |
| `furniture.py` | furniture items | `utilities/items` |
| `gems.py` | `gems` dict | `utilities/items.myItem` |
| `healing.py` | healing items, `FindBandage` | `utilities/items.myItem`, `FindItem` |
| `ingots.py` | `ingots` dict | `utilities/items.myItem` |
| `instruments.py` | instrument items, `FindInstrument` | `utilities/items.myItem`, `FindItem` |
| `miscellaneous.py` | `miscellaneous` dict | `utilities/items.myItem` |
| `moongates.py` | `FindMoongates` | `utilities/items.myItem` |
| `ores.py` | `ores`, `wood` dicts | `utilities/items.myItem` |
| `potions.py` | `potions` dict | `utilities/items.myItem` |
| `reagents.py` | `reagents` dict | `utilities/items.myItem` |
| `shields.py` | `shields` dict | `utilities/items.myItem` |
| `spellScrolls.py` | `spellScrolls` dict | `utilities/items.myItem` |
| `statuettes.py` | statuette items | *(unknown)* |
| `tools.py` | `tools` dict, `FindItem` re-export | `utilities/items.myItem`, `FindItem` |
| `weapons.py` | `weapons` dict | `glossary/items/tools.py`, `utilities/items.myItem` |
| `wood.py` | `wood` dict | *(likely `utilities/items.myItem`)* |

---

### `glossary/crafting/` — Crafting System

Each crafting module wraps the game's crafting gump for a specific skill.

#### `glossary/crafting/craftable.py`
Base `Craftable` class used by carpentry and tinkering.

**Imported by:** `glossary/crafting/carpentry.py`, `glossary/crafting/tinkering.py`

#### `glossary/crafting/blacksmithing.py`
Exports `blacksmithTools`, `FindBlacksmithTool`, `blacksmithCraftables`.

**Imports:** `utilities/gumps.GumpSelection`, `glossary/items/tools.tools`, `utilities/items.FindItem`

**Imported by:** `SmeltContainer.py`, `train_Blacksmithy.py`

#### `glossary/crafting/carpentry.py`
Exports `FindCarpentryTool`, `carpentryCraftables`.

**Imports:** `glossary/crafting/craftable.Craftable`, `glossary/items/tools.tools`, `utilities/gumps.GumpSelection`, `utilities/items.FindItem`

**Imported by:** `train_Carpentry.py`

#### `glossary/crafting/cartography.py`
Exports `cartographyTools`, `cartographyCraftables`.

**Imports:** `utilities/gumps.GumpSelection`, `glossary/items/tools.tools`

**Imported by:** `train_Cartography.py`

#### `glossary/crafting/tailoring.py`
**Imports:** `utilities/gumps.GumpSelection`, `glossary/items/tools.tools`, `utilities/items.FindItem`

#### `glossary/crafting/tinkering.py`
**Imports:** `glossary/crafting/craftable.Craftable`, `glossary/items/tools.tools`, `utilities/gumps.GumpSelection`, `utilities/items.FindItem`

---

## Entry-Point Macros

### Runtime Script Calls (`Misc.ScriptRun`)

These scripts launch other scripts at runtime using Razor Enhanced's `Misc.ScriptRun()`:

| Caller | Calls | Condition |
|---|---|---|
| `resource_treasureChestPuller.py` | `recall_home_Spell.py` | After finishing or on failure |
| `skill_Fishing.py` | `cast_EnergyBolt.py` | When a sea monster attacks |
| `train_Fishing.py` | `cast_EnergyBolt.py` | When a sea monster attacks |

---

### Scripts Using Shared Libraries

#### Combat / PvM / PvP
| Script | Imports from |
|---|---|
| `pvm_pvp_attack_simple.py` | `glossary/enemies`, `utilities/mobiles`, `glossary/colors` |
| `pvm_pvp_attack_list_enemy.py` | `glossary/colors` |
| `pvm_pvp_provocation.py` | `glossary/items/instruments`, `glossary/enemies`, `utilities/mobiles`, `glossary/colors`, `config` |
| `pvm_pvp_healPets.py` | `utilities/items`, `glossary/colors` |
| `pvm_pvp_zombieland.py` | `glossary/enemies` |
| `cast_EnergyBolt.py` | *(none — Razor Enhanced API only)* |
| `cast_Teleport.py` | *(none — Razor Enhanced API only)* |

#### Skills — Training Scripts
| Script | Imports from |
|---|---|
| `train_Anatomy.py` | `glossary/colors` |
| `train_AnimalLore.py` | `glossary/colors` |
| `train_AnimalTaming.py` | `glossary/items`, `glossary/enemies`, `glossary/spells`, `glossary/tameables` |
| `train_ArmsLore.py` | `glossary/colors` |
| `train_Blacksmithy.py` | `config`, `glossary/items/ores`, `glossary/crafting/blacksmithing`, `glossary/colors`, `utilities/items` |
| `train_Carpentry.py` | `glossary/colors`, `glossary/crafting/carpentry`, `glossary/items/containers`, `utilities/items` |
| `train_Cartography.py` | `glossary/items/containers`, `glossary/items/miscellaneous`, `glossary/crafting/cartography`, `glossary/colors`, `utilities/items` |
| `train_Fishing.py` | `config`, `glossary/colors`, `glossary/items/containers`, `glossary/items/tools`, `utilities/items` |
| `train_Healing.py` | `config`, `glossary/items` (FindBandage), `glossary/colors` |
| `train_Hiding.py` | `glossary/colors` |
| `train_ItemIdentification.py` | `glossary/colors` |
| `train_Lockpicking.py` | `glossary/colors`, `glossary/items/tools`, `utilities/items` |
| `train_Magery.py` | `glossary/spells`, `utilities/items`, `glossary/colors` |
| `train_Musicianship.py` | *(none)* |
| `train_Peacemaking.py` | `glossary/enemies`, `config` |
| `train_Provocation.py` | `config`, `glossary/items/instruments`, `glossary/colors`, `glossary/enemies` |
| `train_Snooping.py` | *(none)* |
| `train_SpiritSpeak.py` | `glossary/colors` |
| `train_Stealth.py` | *(none)* |
| `train_Tracking.py` | `glossary/colors` |
| `train_Veterinary.py` | `config`, `glossary/items` (FindBandage), `glossary/colors` |

#### Skills — Active Skill Scripts
| Script | Imports from |
|---|---|
| `skill_Fishing.py` | `config`, `glossary/colors`, `glossary/items/containers`, `glossary/items/tools`, `utilities/items` |
| `skill_Lockpicking.py` | `config`, `glossary/colors`, `glossary/items/tools`, `utilities/items` |
| `skill_Mining.py` | `utilities/items`, `glossary/items/ores`, `glossary/colors` |
| `skill_AnimalTaming.py` | *(none)* |
| `skill_Snooping.py` | *(none)* |
| `disc.py` | `glossary/items`, `glossary/enemies`, `glossary/spells`, `glossary/tameables`, `config`, `glossary/items/instruments`, `glossary/colors` |
| `taming.py` | `glossary/items`, `glossary/enemies`, `glossary/spells`, `glossary/tameables` |
| `animalinfo.py` | `glossary/items`, `glossary/enemies`, `glossary/spells`, `glossary/tameables` |
| `chiv.py` | `glossary/colors` |
| `necro.py` | `glossary/colors` |

#### Items / Inventory
| Script | Imports from |
|---|---|
| `items_copyRuneBook.py` | `config`, `glossary/colors`, `utilities/items` |
| `items_depositIntoBank.py` | `glossary/items/miscellaneous`, `glossary/items/ingots`, `glossary/colors`, `utilities/items` |
| `items_moveOnToStack.py` | `config`, `glossary/colors` |
| `items_moveToNewContainer.py` | `utilities/items`, `config` |
| `items_unequipHands.py` | `utilities/items` |
| `items_useBandages_self.py` | `glossary/colors` |
| `items_useDagger.py` | `glossary/items/tools`, `utilities/items`, `glossary/colors` |
| `items_useFishingPole.py` | `glossary/items/tools`, `utilities/items` |
| `items_useFishingPole_cast.py` | `glossary/items/tools` |
| `items_useMoongate.py` | `glossary/items/moongates` |
| `items_useScissors.py` | `glossary/items/tools`, `utilities/items`, `glossary/colors` |
| `items_useSextant.py` | *(none)* |
| `items_useSkinningKnife.py` | `glossary/items/tools`, `utilities/items`, `glossary/colors` |

#### Organizers
| Script | Imports from |
|---|---|
| `organizer_bagPosition_gems.py` | `glossary/items/gems` |
| `organizer_bagPosition_reagents.py` | *(none)* |
| `organizer_bagPosition_tools.py` | *(none)* |
| `organizer_BODsIntoBooks.py` | `utilities/items` |
| `organizer_maps_addToDaviesLocker.py` | *(none)* |
| `organizer_moveToBag_reagents.py` | `utilities/items`, `glossary/items/reagents`, `config` |
| `organizer_restock_reagents_50.py` | `utilities/items`, `glossary/items/reagents`, `glossary/colors`, `config` |
| `organizer_spellScrolls.py` | `glossary/spells`, `glossary/items/spellScrolls`, `utilities/items` |
| `organizer_treasureMaps.py` | *(none)* |

#### Resources / Crafting
| Script | Imports from |
|---|---|
| `LumberJack.py` | `utilities/items`, `glossary/colors`, `glossary/items/wood`, `config` |
| `LumberJackgarg.py` | `utilities/items`, `glossary/colors`, `glossary/items/wood`, `config` |
| `junk logger.py` | `glossary/items/ores` (wood), `glossary/colors`, `config`, `utilities/items` |
| `SmeltContainer.py` | `config`, `glossary/items/ores`, `glossary/crafting/blacksmithing`, `glossary/colors`, `utilities/items` |
| `smeltatest.py` | `glossary/items/ores`, `glossary/colors`, `config`, `utilities/items` |
| `resource_smelting.py` | `glossary/items/ores`, `glossary/colors`, `config` |
| `resource_distributeTreasureMapLoot.py` | `glossary/items/armor`, `glossary/items/gems`, `glossary/items/miscellaneous`, `glossary/items/shields`, `glossary/items/spellScrolls`, `glossary/items/weapons`, `utilities/items`, `glossary/colors` |
| `resource_itemIdentification.py` | `glossary/items/armor`, `glossary/items/shields`, `glossary/items/weapons`, `utilities/items`, `glossary/colors`, `config` |
| `resource_treasureChestPuller.py` | `config`, `glossary/items/armor`, `glossary/items/clothing`, `glossary/items/gems`, `glossary/items/reagents`, `glossary/items/shields`, `glossary/items/spellScrolls`, `glossary/items/weapons`, `utilities/items`, `glossary/colors` |
| `transferignots.py` | `glossary/items/ores`, `glossary/items/ingots`, `glossary/colors`, `config`, `utilities/items` |
| `ultimatemining.py` | `utilities/items`, `config`, `glossary/colors`, `glossary/items/ores` |
| `bank_check_ingots.py` | *(none)* |
| `buypickaxe.py` | *(none)* |

#### Travel / Gate Scripts
| Script | Imports from |
|---|---|
| `_gate_home.py` | `glossary/items/moongates` |
| `_gate_bank.py` | *(none)* |
| `GateHome.py` | *(none)* |
| `gate scrolls.py` | *(none)* |
| `recall_home_Scroll.py` | *(none)* |
| `recall_home_Spell.py` | *(none)* |
| `makerecalls.py` | *(none)* |

#### Healing / Character
| Script | Imports from |
|---|---|
| `heal human.py` | `utilities/items`, `glossary/colors` |
| `heal frand.py` | *(none)* |
| `heal last.py` | *(none)* |
| `HEAL SELF MED.py` | *(none)* |
| `vet copy.py` | `utilities/items`, `glossary/colors` |
| `AutoChivalry.py` | *(none)* |
| `chivin.py` | *(none)* |
| `myst.py` | *(none)* |
| `poisoning.py` | *(none)* |
| `posioning.py` | *(none — duplicate/typo of poisoning.py)* |
| `trainninjastealth.py` | *(none)* |
| `trainspellweave.py` | *(none)* |

#### Utility / Standalone
| Script | Imports from |
|---|---|
| `misc_current_position.py` | *(none)* |
| `inspect_mobile.py` | *(none)* |
| `inspect_mobile2.py` | *(none)* |
| `player_say_bank.py` | *(none)* |
| `player_say_vendorSell.py` | *(none)* |
| `disarm.py` | *(none)* |
| `detect.py` | *(none)* |
| `mirror.py` | *(none)* |
| `music.py` | *(none)* |
| `bush.py` | *(none)* |
| `lasttame.py` | *(none)* |
| `tame last.py` | *(none)* |
| `ELoot.py` | `.NET` assemblies via `clr` only (no project imports) |
| `treasure.py` | *(none)* |
| `_startup.py` | *(none)* |

#### Special
| Script | Purpose |
|---|---|
| `razorenhanced_stubs.py` | Type stub imports for IDE IntelliSense; not a runnable macro |
| `test_tameable_check.py` | Developer test script |
| `New Macro 01.macro` | Raw Razor Enhanced macro (not Python) |

---

## Dependency Graph Summary

```
config.py
└── utilities/items.py
        └── glossary/items/*.py   (most item data modules)
                └── glossary/spells.py
                        └── glossary/items/reagents.py

utilities/gumps.py
        └── glossary/crafting/*.py
                └── glossary/crafting/craftable.py (base class)

glossary/colors.py           (leaf — no project imports)
glossary/enemies.py          (leaf — only System imports)
glossary/tameables.py        (leaf — only System imports)
utilities/mobiles.py         (leaf — no project imports shown)

Entry-point macros import from the above layers.
```

Runtime orchestration (via `Misc.ScriptRun`):

```
resource_treasureChestPuller.py ──► recall_home_Spell.py
skill_Fishing.py                ──► cast_EnergyBolt.py
train_Fishing.py                ──► cast_EnergyBolt.py
```
