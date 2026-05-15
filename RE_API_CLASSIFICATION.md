# Razor Enhanced API — Classification & Patterns Guide

A reference for the scripting patterns used throughout this project.  
Organized by API class, interaction category, and common idioms seen in scripts like `mining.py`, `inscription_fill_spellbook.py`, and others.

---

## Table of Contents

1. [How RE Scripts Work](#how-re-scripts-work)
2. [API Class Reference](#api-class-reference)
   - [Player](#player)
   - [Items](#items)
   - [Mobiles](#mobiles)
   - [Target](#target)
   - [Gumps](#gumps)
   - [Journal](#journal)
   - [Misc](#misc)
   - [Spells](#spells)
   - [Timer](#timer)
   - [Statics](#statics)
3. [Interaction Categories](#interaction-categories)
   - [Category 1 — Item Manipulation](#category-1--item-manipulation)
   - [Category 2 — Targeting](#category-2--targeting)
   - [Category 3 — Gump Navigation (Crafting)](#category-3--gump-navigation-crafting)
   - [Category 4 — Journal Polling](#category-4--journal-polling)
   - [Category 5 — Player State & Skills](#category-5--player-state--skills)
   - [Category 6 — Spell Casting](#category-6--spell-casting)
   - [Category 7 — Timing & Loop Control](#category-7--timing--loop-control)
   - [Category 8 — World / Map Lookup](#category-8--world--map-lookup)
   - [Category 9 — Party Chat Command Dispatch](#category-9--party-chat-command-dispatch)
   - [Category 9 — Party Chat Command Dispatch](#category-9--party-chat-command-dispatch)
4. [Crafting Gump Layout](#crafting-gump-layout)
5. [Known Item IDs Cheat Sheet](#known-item-ids-cheat-sheet)
6. [Common Gotchas](#common-gotchas)

---

## How RE Scripts Work

Razor Enhanced executes `.py` files as **IronPython 2.7** scripts.  The engine injects the following globals at runtime — they do **not** need to be imported:

| Global | Type | Purpose |
|--------|------|---------|
| `Player` | PlayerData | Local player's character |
| `Items` | ItemsAPI | Find, move, equip, use items |
| `Mobiles` | MobilesAPI | Find and inspect mobiles (NPCs, monsters, players) |
| `Target` | TargetAPI | Target cursor management |
| `Gumps` | GumpsAPI | Interact with server-sent gumps |
| `Journal` | JournalAPI | Read the UO text journal |
| `Misc` | MiscAPI | Utility functions (pause, send message, use skill) |
| `Spells` | SpellsAPI | Cast spells by name |
| `Timer` | TimerAPI | Tick-based timers |
| `Statics` | StaticsAPI | Query map tile/static data |

> For IDE IntelliSense add `if False: from razorenhanced_stubs import *` at the top of any script.

---

## API Class Reference

### Player

Represents the local character.  Properties are read-only; methods trigger actions.

```python
# ── Common properties ──────────────────────────────────────────────────────
Player.Serial       # unique serial (int)
Player.Name         # character name (str)
Player.Backpack     # Item object — the player's main pack
Player.X, Player.Y, Player.Z  # world position
Player.Hits, Player.HitsMax   # current / max HP
Player.Mana, Player.ManaMax   # current / max mana
Player.Stam, Player.StamMax   # current / max stamina
Player.Weight, Player.MaxWeight
Player.GetSkillValue("Inscription")     # current effective value (0.0–120.0)
Player.GetRealSkillValue("Inscription") # base value without temporary buffs
Player.GetSkillCap("Inscription")       # per-skill cap; 100 default, up to 120 with power scrolls

# ── Actions ────────────────────────────────────────────────────────────────
Player.UseSkill("Meditation")   # trigger a skill use (meditation, etc.)
Player.HeadMessage(color, msg)  # display overhead message above character
Player.ChatSay(color, msg)      # say something in public chat
Player.ChatParty(msg)           # send a message to party chat (no color arg)
Player.IsGhost                  # bool — is the player a ghost?
Player.Position.X, Player.Position.Y, Player.Position.Z   # current tile
```

---

### Items

Find, inspect, move, equip, and use any in-world item.

```python
# ── Finding ────────────────────────────────────────────────────────────────
item = Items.FindByID(itemID, color, containerSerial)
# color  = -1  to ignore color
# containerSerial = Player.Backpack.Serial  or  mobile.Backpack.Serial
# containerSerial = -1  to search all visible items in the world (range-based)

item = Items.FindBySerial(serial)   # exact serial lookup

# ── Item properties ────────────────────────────────────────────────────────
item.Serial, item.ItemID, item.Hue (int)
item.Amount         # stack size
item.Weight         # weight of the stack
item.IsContainer    # bool
item.Contains       # list[Item] — children for containers
item.Name           # display name

# ── Moving ─────────────────────────────────────────────────────────────────
Items.Move(item, destContainer, amount)
# destContainer can be an Item or a serial int
# amount = -1 moves the whole stack

# ── Using ──────────────────────────────────────────────────────────────────
Items.UseItem(item)             # double-click
Items.UseItemByID(itemID)       # double-click by graphic ID (first found)

# ── Equipping ─────────────────────────────────────────────────────────────
Items.Equip(item)
Items.Unequip(layer)            # layer = "MainHand", "Ring", etc.
```

---

### Mobiles

Find and inspect characters (NPCs, monsters, other players).

```python
mobile = Mobiles.FindBySerial(serial)
IsGhost          # bool — is a ghost?
mobile.IsHuman          # bool — humanoid body?
mobile.Backpack         # Item — their pack (if accessible)
mobile.X, mobile.Y, mobile.Z

# ── Filter-based search ────────────────────────────────────────────────────
mf = Mobiles.Filter()
mf.Enabled   = True
mf.RangeMax  = 10
mf.IsHuman   = 1        # 1 = only humans, 0 = exclude humans
mf.IsGhost   = 1        # 1 = only ghosts (body IDs 402,403,607,608,694,695,970)
mf.Friend    = 1        # 1 = friends only
list_of_mobs = Mobiles.ApplyFilter(mf)

nearest = Mobiles.Select(list_of_mobs, 'Nearest')   # also: Farthest, Weakest, Strongest───────────────────────────────────────
mf = Mobiles.Filter()
mf.Enabled   = True
mf.RangeMax  = 10
mf.IsHuman   = 1        # 1 = only humans, 0 = exclude humans
mf.IsGhost   = 1        # 1 = only ghosts (body IDs 402,403,607,608,694,695,970)
mf.Friend    = 1        # 1 = friends only
list_of_mobs = Mobiles.ApplyFilter(mf)

nearest = Mobiles.Select(list_of_mobs, 'Nearest')   # also: Farthest, Weakest, Strongest
```

---

### Target

Manage the UO target cursor, including prompting the user to click something.

```python
# ── Player-prompted targeting ──────────────────────────────────────────────
serial = Target.PromptTarget("Click the item or mobile")
# Blocks until the player clicks. Returns the serial (int) of the selection,
# or None if cancelled., noWarn)   # noWarn=True suppresses cursor flash
Target.WaitForTarget(timeoutMs)           # same, noWarn defaults to False
Target.Cancel()                           # cancel an active target prompt

# ── Targeting a mobile directly ──────────────────────────────────────────
Target.WaitForTarget(4000, False)
Target.TargetExecute(some_mobile)         # pass Mobile object directly

# ── Scripted targeting (no player interaction) ─────────────────────────────
Target.TargetExecute(x, y, z, tile_id)    # target a map tile directly
Target.SetLast(serial)                     # pre-set the last-used target
Target.Last()                              # returns last targeted serial

# ── Waiting for the cursor ─────────────────────────────────────────────────
Target.WaitForTarget(timeoutMs, noWarn)   # noWarn=True suppresses cursor flash
Target.WaitForTarget(timeoutMs)           # same, noWarn defaults to False
Target.Cancel()                           # cancel an active target prompt

# ── Targeting a mobile directly ──────────────────────────────────────────
Target.WaitForTarget(4000, False)
Target.TargetExecute(some_mobile)         # pass Mobile object directly
```

---

### Gumps

Read and interact with server-sent gumps (dialogs, menus, crafting windows).

```python
# ── Waiting for a gump to appear ──────────────────────────────────────────
found = Gumps.WaitForGump(gumpID, timeoutMs)   # returns bool

# ── Checking if a gump is open ────────────────────────────────────────────
is_open = Gumps.HasGump()           # any gump open?

# ── Interacting ───────────────────────────────────────────────────────────
Gumps.SendAction(gumpID, buttonID)  # click 

current_id = Gumps.CurrentGump()    # returns gump ID of the most recent gump (.NET Int32)
                                    # always cast: int(Gumps.CurrentGump()) before json/math
Gumps.CloseGump(gumpID)             # close a gump by ID
lines = Gumps.LastGumpGetLineList() # List[str] of all text lines on the current gump

# ── Runebook gump ──────────────────────────────────────────────────────────
# GroupID 89 (confirmed on OSI-derivative shards).
# Gate Travel button formula: button = BASE + slot_index  (0-based, 16 slots)
#   BASE is SHARD-SPECIFIC -- must be determined by in-game testing.
#   98 is NOT safe to assume; confirmed 100 on the shard used in this project.
# Line structure (115 lines for a full 16-rune book):
#   Lines 0..charges_anchor-1 : button labels
#   "Charges" anchor        : search dynamically with enumerate()
#   anchor+2, anchor+3      : current_charges, max_charges  (as strings)
#   anchor+4..anchor+19     : 16 rune names positional ("Empty" for unused)
#   anchor+20+              : name+coord pairs (2 lines per filled, 1 "Empty" per unused)
# Gumps.LastGumpSerial() and Gumps.LastGumpID() do NOT exist at runtime -- use CurrentGump().

# Advanced: click a button with switch states and text entry
Gumps.SendAdvancedAction(
    gumpID,
    buttonID,
    switches=[],          # list of int switch IDs to toggle ON
    textEntries=[(idx, "text")]   # list of (field_index, value) tuples
)

# ── Reading gump data ──────────────────────────────────────────────────────
gd = Gumps.GetGumpData(gumpID)
gd.buttonid      # last button pressed
found = Journal.SearchByType("phrase", "Regular")  # filter by entry type
                                     # types: "Regular", "System", "Label"

count = Journal.GetLineCount()       # total lines in current buffer (int)
entry = Journal.GetJournalEntry(i)   # entry object at 0-based index i
                                     # entry.Text (str), entry.Name (str, speaker)
lines = Journal.GetTextByType("Regular")   # List[str] of matching lines

# ── Common usage pattern ───────────────────────────────────────────────────
Journal.Clear()
# ... trigger action that produces a journal message ...
Misc.Pause(500)
if Journal.Search("You fail"):
    # handle failure
```

> `Journal.Search` is **case-sensitive** and does a substring match.
> `Journal.GetJournalEntry` may return `None` -- always null-check.
> Party chat entries appear in the regular journal with `entry.Name` set to the speaker's name.
```

---

### Journal

Read text that has been printed to the UO client journal (chat, system messages).

```python
Journal.Clear()                      # clear the journal buffer (reset baseline)
found = Journal.Search("phrase")     # True if "phrase" appears anywhere in buffer
found = Journal.SearchByName("Jake", "phrase")  # from a specific speaker
found = Journal.SearchByType("phrase", "Regular")  # filter by entry type
                                     # types: "Regular", "System", "Label"

# ⚠ Journal.GetLineCount() does NOT exist at runtime (stub only) -- AttributeError.
# ⚠ Journal.GetJournalEntry(i) IGNORES the index argument at runtime.
#   It always returns the full List[JournalEntry] regardless of what i you pass.
#   Correct pattern:
entries = Journal.GetJournalEntry(0)   # returns List[JournalEntry] (index is ignored)
if entries:
    for entry in entries:
        # entry.Text (str), entry.Name (str, speaker name or '' for system/echo)
        pass

lines = Journal.GetTextByType("Regular")   # List[str] of matching lines

# ── Common usage pattern ───────────────────────────────────────────────────
Journal.Clear()
# ... trigger action that produces a journal message ...
Misc.Pause(500)
if Journal.Search("You fail"):
    # handle failure
```

> `Journal.Search` is **case-sensitive** and does a substring match.
> Party chat entries appear in the regular journal with `entry.Name` set to the speaker's name.
> Own `Player.ChatParty()` echoes arrive with an **empty** `entry.Name` -- not the player's name.
> Always guard with `if not entry.Name or entry.Name.lower() == Player.Name.lower(): continue`.

---

### Misc

Catch-all utility functions for timing, messaging, and skill use.

```python
Misc.Pause(milliseconds)            # sleep (blocks the script)
Misc.SendMessage("text", color)     # prints a colored message to the client

Misc.UseSkill("Meditation")         # alternative to Player.UseSkill
Misc.UseSkill("Stealth")

Misc.Beep()                         # audible alert
```

---

### Spells

Cast spells by name.  RE handles the targeting cursor automatically if needed.

```python
Spells.CastMagery("Gate Travel")
Spells.CastMagery("Recall")
Spells.CastChivalry("Consecrate Weapon")
Spells.CastNecro("Animate Dead")
Spells.CastMysticism("Rising Colossus")
Spells.CastSpellweaving("Arcane Circle")

# These return immediately — wait for the target cursor with:
Target.WaitForTarget(3000)
# Then target something:
Target.TargetExecute(x, y, z, tile_id)
# OR target an item/mobile:
Target.SetLast(serial)
```

---

### Timer

Tick-based helpers for non-blocking cooldown tracking.

```python
t = Timer.Create()
t.Start()
elapsed_ms = t.ElapsedMs
t.Stop()
# Useful when you need to know if N ms have passed without blocking with Pause.
```

---

### Statics

Query land tiles and static objects at a given world coordinate.

```python
tile_list = Statics.GetStaticsTileInfo(x, y, map_index)
# Returns a list of StaticTileInfo objects:
#   .StaticID   (int) — graphic ID of the static tile
#   .StaticZ    (int) — Z coordinate of the tile
#   .Hue        (int)
# map_index: 0 = Felucca/Trammel, 1 = Trammel, 2 = Ilshenar, etc.

# ── Example: find the first static tile at a coordinate ───────────────────
statics = Statics.GetStaticsTileInfo(x, y, 0)
if statics and len(statics) > 0:
    tz      = statics[0].StaticZ
    tile_id = statics[0].StaticID
```

> `Map.GetTileInfo` does **not** exist in Razor Enhanced.  Use `Statics` instead.

---

## Interaction Categories

The patterns below classify the *types* of interactions seen across the scripts in this project.

---

### Category 1 — Item Manipulation

Used in: `mining.py`, `inscription_fill_spellbook.py`, `organizer_*.py`, `items_*.py`

| Operation | RE API | Notes |
|-----------|--------|-------|
| Find in backpack | `Items.FindByID(id, -1, Player.Backpack.Serial)` | -1 ignores hue |
| Find on ground (within range) | `Items.FindByID(id, -1, -1, range)` | last param = tile range |
| Move item to container | `Items.Move(item, destContainer, amount)` | always `Misc.Pause(700)` after |
| Use/double-click | `Items.UseItem(item)` | triggers contextual action |
| Iterate container contents | `for item in container.Contains:` | shallow; sub-bags need recursion |

**Batch-move pattern** (safe weight-aware pull):
```python
per_unit = float(ore.Weight) / ore.Amount          # weight per single unit
can_take = int((Player.MaxWeight - Player.Weight) / per_unit)
pull     = min(ore.Amount, can_take)
Items.Move(ore, Player.Backpack, pull)
Misc.Pause(700)
```

---

### Category 2 — Targeting

Used in: `resource_smelting.py`, `inscription_fill_spellbook.py`, `mining.py`

| Goal | Pattern |
|------|---------|
| Prompt the player to click anything | `serial = Target.PromptTarget("message")` |
| Target a world tile programmatically | `Target.TargetExecute(x, y, z, tile_id)` |
| Target an item/mobile by serial | `Target.SetLast(serial)` then action |
| Wait for target cursor to appear | `Target.WaitForTarget(3000)` |

**PromptTarget idiom**:
```python
serial = Target.PromptTarget("Click your reagent chest")
if serial is None:
    return          # player cancelled
container = Items.FindBySerial(serial)
```

---

### Category 3 — Gump Navigation (Crafting)

Used in: `inscription_fill_spellbook.py`, `resource_smelting.py`, `glossary/crafting/*.py`

All crafting skills share **gump ID `949095101`** in standard RunUO/ServUO builds.

**Standard two-click craft pattern**:
```python
Items.UseItem(tool)                              # open the crafting menu
Gumps.WaitForGump(949095101, 2000)              # wait for it to appear
Gumps.SendAction(949095101, category_button)    # select the category/circle
Misc.Pause(500)
Gumps.SendAction(949095101, item_button)        # craft the item
Misc.Pause(craft_delay)
```

**Button layout** (applies to smithing, tailoring, inscription, etc.):

```
Left panel (categories):  1,  8, 15, 22, 29, 36, 43, 50 ...  (stride = 7)
Right panel (items):      2,  9, 16, 23, 30, 37, 44, 51 ...  (stride = 7)
Special buttons:
  Exit          = 0
  Make Last     = 7
  Toggle Mark   = 49  (some menus only)
```

**Determining the right-side button for a specific item**:
```python
slot     = index_of_item_in_its_category   # 0-based
item_btn = 2 + slot * 7
```

---

### Category 4 — Journal Polling

Used in: `mining.py`, `inscription_fill_spellbook.py`, `resource_smelting.py`

**Primary pattern**:
```python
Journal.Clear()
# ... trigger action ...
Misc.Pause(reaction_time_ms)
if Journal.Search("success phrase"):
    # handle success
elif Journal.Search("failure phrase"):
    # handle failure
```

**Key rules**:
- Always `Journal.Clear()` *before* the action, not after.
- `Journal.Search` is case-sensitive substring match.
- Keep the phrase list as a constant for easy maintenance:
  ```python
  FAIL_PHRASES = ["not enough", "You lack", "failed to create"]
  def journal_fails():
      return any(Journal.Search(p) for p in FAIL_PHRASES)
  ```

---

### Category 5 — Player State & Skills

Used in: `mining.py` (mana-free), `inscription_fill_spellbook.py`, `HEAL SELF MED.py`

| Check | Code |
|-------|------|
| Current mana | `Player.Mana` |
| Max mana | `Player.ManaMax` |
| Current weight | `Player.Weight` |
| Max weight | `Player.MaxWeight` |
| Over-weight check | `Player.Weight >= Player.MaxWeight - buffer` |
| Trigger meditation | `Player.UseSkill("Meditation")` |
| Current skill value | `Player.GetSkillValue("Inscription")` |
| Base value (no buffs) | `Player.GetRealSkillValue("Inscription")` |
| Per-skill cap | `Player.GetSkillCap("Inscription")` |

**Meditate-to-full pattern**:
```python
if Player.Mana < THRESHOLD:
    Player.UseSkill("Meditation")
    while Player.Mana < Player.ManaMax:
        Misc.Pause(500)
```

---

### Category 6 — Spell Casting

Used in: `mining.py` (Gate Travel), `cast_Teleport.py`, `cast_EnergyBolt.py`

```python
# 1. Cast the spell
Spells.CastMagery("Gate Travel")

# 2. Wait for the target cursor
Target.WaitForTarget(3000)

# 3. Supply the target
Target.TargetExecute(x, y, z, 0)          # tile
# OR
Target.SetLast(runebook_serial)            # item
```

**Gate Travel + runebook pattern** (from `mining.py`):
```python
Spells.CastMagery("Gate Travel")
Target.WaitForTarget(3000)
Target.SetLast(runebook_serial)
Misc.Pause(4000)   # wait for the gate to open
gate = Items.FindByID(0x0F6C, -1, -1, 3)  # find moongate
if gate:
    Items.UseItem(gate)
```

---

### Category 7 — Timing & Loop Control

Used in: all long-running scripts

```python
# Fixed pause — blocks execution
Misc.Pause(1600)

# Polling loop with timeout
deadline = 30000
elapsed  = 0
while not condition and elapsed < deadline:
    Misc.Pause(200)
    elapsed += 200

# Journal-driven event wait
Journal.Clear()
trigger_action()
deadline = 5000
elapsed  = 0
while not Journal.Search("expected message") and elapsed < deadline:
    Misc.Pause(200)
    elapsed += 200
```

**Chat-command interrupt pattern** (from `mining.py`):
```python
def check_loop_command():
    for cmd in ["quit", "smelt", "bank", "mount", "forge"]:
        if Journal.Search(cmd):
            return cmd
    return None

# Inside main loop:
cmd = check_loop_command()
if cmd == "quit":
    break
```

---

### Category 8 — World / Map Lookup

Used in: `mining.py`

```python
statics = Statics.GetStaticsTileInfo(tx, ty, 0)

if statics and len(statics) > 0:
    tz, tile_id = statics[0].StaticZ, statics[0].StaticID
    Target.TargetExecute(tx, ty, tz, tile_id)
else:
    # Fall back to land tile (outdoor mining)
    Target.TargetExecute(tx, ty, Player.Z, 0x0000)
```

**Two-pass mining targeting** (cave vs. outdoor):
1. Try land tile first (`tile_id = 0x0000`, `z = Player.Z`).
2. If the server replies "cannot be seen", probe `Statics` for the actual cave floor tile.
3. Cache `(tz, tile_id)` per direction so subsequent swings skip the probe.

---

### Category 9 — Party Chat Command Dispatch

Used in: `util_gatekeeper.py`

Party chat messages appear in the journal like any other speech.  `Journal.GetJournalEntry(0)` returns the **full** `List[JournalEntry]` at runtime (the index argument is ignored). `Journal.GetLineCount()` does **not** exist at runtime -- do not use a watermark approach. Instead, call `Journal.Clear()` at the end of each poll cycle.

**Working poll pattern** (confirmed at runtime):
```python
Journal.Clear()   # clear at startup

while not Player.IsGhost:
    entries = Journal.GetJournalEntry(0)   # always returns full List[JournalEntry]
    found_cmd = None
    found_arg = None
    if entries:
        for entry in entries:
            # Own ChatParty echoes have empty Name; other players always have Name set.
            if not entry.Name or entry.Name.lower() == Player.Name.lower():
                continue
            cmd = entry.Text.strip().lower()
            if cmd.startswith('gate '):
                found_cmd = 'gate'
                found_arg = cmd[5:].strip()
                break   # one command per cycle
            elif cmd == 'rez':
                found_cmd = 'rez'
                break
    Journal.Clear()   # consume; prevents replay on next cycle
    if found_cmd == 'gate' and found_arg:
        HandleGate(found_arg)
    elif found_cmd == 'rez':
        HandleRez()
    Misc.Pause(300)
```

**CRITICAL -- reply message must not start with a command prefix**:
```python
# BAD  -- 'Gate opened to bank.' starts with 'gate ', causing self-trigger next cycle
Player.ChatParty('Gate opened to bank.')

# GOOD -- prefix with 'Gatekeeper:' so it splits past the command keyword
Player.ChatParty('Gatekeeper: opened gate to bank.')
```

**Sending party chat**:
```python
Player.ChatParty('Gatekeeper: online.')   # no color argument
```

**Ghost filter for rez target**:
```python
ghostFilter          = Mobiles.Filter()
ghostFilter.Enabled  = True
ghostFilter.IsGhost  = 1
ghostFilter.IsHuman  = 1
ghostFilter.RangeMax = 5
ghosts = Mobiles.ApplyFilter(ghostFilter)
if ghosts and len(ghosts) > 0:
    ghost = Mobiles.Select(ghosts, 'Nearest')
    Spells.CastMagery('Resurrection')
    Target.WaitForTarget(4000, False)
    Target.TargetExecute(ghost)
    # wait for accept
    waited = 0
    while ghost.IsGhost and waited < 30000:
        Misc.Pause(500)
        waited += 500
```

**IronPython / .NET integer gotcha**:
```python
# Gumps.CurrentGump() and Target.PromptTarget() return .NET Int32.
# Python's json module cannot serialize them -- always cast first:
serial_int = int(Target.PromptTarget('Click runebook'))
gump_int   = int(Gumps.CurrentGump())
```

---

## Crafting Gump Layout

```
┌─────────────────────────────────────────────┐
│  [CATEGORY 1]  btn 1   │  Item A  btn 2      │
│  [CATEGORY 2]  btn 8   │  Item B  btn 9      │
│  [CATEGORY 3]  btn 15  │  Item C  btn 16     │
│  [CATEGORY 4]  btn 22  │  Item D  btn 23     │
│  [CATEGORY 5]  btn 29  │  Item E  btn 30     │
│  [CATEGORY 6]  btn 36  │  Item F  btn 37     │
│  [CATEGORY 7]  btn 43  │  Item G  btn 44     │
│  [CATEGORY 8]  btn 50  │  Item H  btn 51     │
│  ─────────────────────────────────────────── │
│  [Make Last]   btn 7   │  [Exit]  btn 0      │
└─────────────────────────────────────────────┘
   Gump ID: 949095101  (all standard crafting skills)
```

For **inscription** the categories are the 8 magic circles; items are the spells within each circle, listed in their UO spell order (same order used by `MAGERY_SCROLLS` in `inscription_fill_spellbook.py`).

---

## Known Item IDs Cheat Sheet

| Item | Graphic IDs |
|------|-------------|
| Scribe's Pen (inscription tool) | `0x0FBF`, `0x0FBE` |
| Spellbook | `0x0EFA` |
| Blank Scroll | `0x0E34` |
| Pickaxe | `0x0E85`, `0x0E86` |
| Raw Ore piles | `0x19B7`, `0x19B8`, `0x19B9`, `0x19BA` |
| Moongate | `0x0F6C` |
| Runebook | `0x22C5` |
| Forge tiles | `0x0FAD`, `0x0FAE`, `0x0FAF`, `0x0FB0`, `0x0FB1` |
| **Reagents** | |
| Black Pearl | `0x0F7A` |
| Blood Moss | `0x0F7B` |
| Garlic | `0x0F84` |
| Ginseng | `0x0F85` |
| Mandrake Root | `0x0F86` |
| Nightshade | `0x0F88` |
| Spider's Silk | `0x0F8D` |
| Sulfurous Ash | `0x0F8C` |

> Spell scroll IDs follow the pattern `0x1F2D`–`0x1F6C` (64 scrolls, Circles 1–8).  
> The complete mapping is in `glossary/items/spellScrolls.py` and inlined in `inscription_fill_spellbook.py`.

---

## Common Gotchas

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `AttributeError: Map` | `Map` global does not exist in RE | Use `Statics.GetStaticsTileInfo` |
| `AttributeError: DropItemOnGround` | That method does not exist | Use `Items.Move(item, bag, amount)` |
| Smelt / craft loops forever | Server sends "not enough metal" but script never exits | Add fail-phrase check + serial-unchanged bail |
| Weight overflows when pulling from animal | Using `item.Weight` (stack total) instead of per-unit | `per_unit = float(ore.Weight) / ore.Amount` |
| Gump navigation clicks wrong spell | Category panel remembered from previous session | Track `current_circle` variable; reset to `None` on gump reopen |
| `Target.PromptTarget` returns None | Player cancelled or timeout | Guard with `if serial is None: return` |
| Meditation ignored | Gump closed mid-cast / skill not on cooldown | Close gump first; call `Player.UseSkill("Meditation")` only after |
| Spellbook `Contains` is empty | Spellbook stores spells as flags, not scroll items | Craft all scrolls when target is a spellbook; skip the existing-check or test per shard |
| Journal.Search misses a message | Phrase case mismatch or journal was not cleared | Always `Journal.Clear()` before the action; match exact server phrasing |
| `json.dump` raises `TypeError` on serial / gump ID | RE returns `.NET Int32`, not Python `int` | Wrap with `int()`: `int(Target.PromptTarget(...))`, `int(Gumps.CurrentGump())` |
| `AttributeError: LastGumpSerial` or `LastGumpID` | Those methods exist in the stubs but not at runtime | Use `Gumps.CurrentGump()` instead |
| Party chat command re-triggers own handler | Own `ChatParty()` echoes arrive with **empty** `entry.Name`, not the player's name | Guard: `if not entry.Name or entry.Name.lower() == Player.Name.lower(): continue` |
| Party chat reply triggers the same handler (e.g. "Gate opened to bank.") | Reply string starts with a command keyword -- parsed as a new command next cycle | Prefix replies: `'Gatekeeper: opened gate to bank.'` -- the `': '` split in `NormalizeText` strips the prefix, leaving a non-command string |
| `AttributeError: Journal` object has no attribute `GetLineCount` | `Journal.GetLineCount()` exists in stubs but **does not exist at runtime** | Remove all uses; use `Journal.Clear()` + `Journal.GetJournalEntry(0)` instead |
| `Journal.GetJournalEntry(i)` returns a list, not a single entry | The index argument is **ignored at runtime**; always returns full `List[JournalEntry]` | Call as `entries = Journal.GetJournalEntry(0)` then `for entry in entries:` |
| Runebook gate button fires wrong rune (off by N slots) | `GATE_BUTTON_BASE` constant is shard-specific and must be calibrated | Test slot 0 in-game; if it fires the wrong rune, adjust the base. This shard uses 100 (not 98). |
| Sextant-to-tile conversion sends extractor to wrong rune | Generic `MAP_WIDTH / 360` formula does not match this shard's projection | Calibrate from two known rune tiles; derive `X_ORIGIN`, `X_SCALE`, `Y_ORIGIN`, `Y_SCALE` constants instead of using MAP_WIDTH/HEIGHT ratios |
| `Mobiles.ApplyFilter` returns no ghosts | Default filter has `IsGhost = 0` (exclude ghosts) | Explicitly set `mf.IsGhost = 1` |
