# Razor Enhanced Script Design Practices

Patterns and conventions that have been confirmed to work in this codebase.
Reference this before writing new scripts.

---

## 1. Portability — Making Scripts Run From Anywhere

Razor Enhanced does not guarantee the scripts directory is on `sys.path`.
Add this block at the top of **every script that imports from `glossary/` or `utilities/`**,
before any local imports:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

This makes the script's own directory the first search path regardless of how
RE launched it or where it is installed on the target machine.
`_startup.py` also sets this, but per-script insertion is the reliable guarantee.

---

## 2. Reading Item Properties

`GetProperties()` is an **Item-only** method — it does not exist on `Mobile`.
Calling it on a mobile will raise `AttributeError`.

**Correct pattern (items only):**

```python
Items.SingleClick(item)          # ask the server to send prop data
Misc.Pause(500)                  # let the server respond
Items.WaitForProps(item, 2000)   # block until props arrive (or timeout)
props = Items.GetPropStringList(item.Serial)  # list of strings, one per tooltip line
```

`props` is a list of strings. Each string is one line of the item tooltip:

```python
for line in props:
    if "Artifact" in line:
        # handle artifact
```

`props` is `None` if the server never sent the data — always guard:

```python
if not props:
    return None
```

**Reading mobile attributes** — use the object's direct properties instead:

```python
mob.Hits       mob.HitsMax    mob.Stamina   mob.Mana
mob.Poisoned   mob.IsGhost    mob.WarMode   mob.Name
mob.Body       mob.Serial     mob.Backpack
Player.GetSkillValue("Imbuing")   # skill as float
```

---

## 3. Runebook Slot Navigation

Confirmed from `util_runebook_explorer.py` — run it to inspect any runebook.

| Constant | Value | Notes |
|---|---|---|
| `RUNEBOOK_ITEM_ID` | `0x22C5` | ItemID of a runebook |
| `RUNEBOOK_GUMP_ID` | `89` | GroupID of the runebook gump |
| Gate button per slot | `100 + slot_index` | 0-based; slot 0 → 100, slot 3 → 103 |
| Recall button per slot | TBD | Not yet confirmed — use explorer to verify |

**Opening the gump and clicking a slot's Gate button:**

```python
Items.UseItem(runebook)
Misc.Pause(500)
if Gumps.WaitForGump(RUNEBOOK_GUMP_ID, 5000):
    gate_button = 100 + slot_index   # 0-based
    Gumps.SendAction(RUNEBOOK_GUMP_ID, gate_button)
```

**Casting Gate Travel / Recall directly to the default rune** (no gump needed):

```python
# Gate Travel to default rune
Spells.CastMagery("Gate Travel")
Target.WaitForTarget(4000, False)
Target.TargetExecute(runebook.Serial)

# Recall to default rune
Spells.CastMagery("Recall")
Target.WaitForTarget(4000, False)
Target.TargetExecute(runebook.Serial)
```

**Confirming a spell was cast (mana drop check):**

```python
mana_before = Player.Mana
# ... cast and target ...
# Poll until mana drops (spell actually fired) or timeout
Timer.Create("mana_check", 3000)
while Timer.Check("mana_check"):
    if Player.Mana < mana_before:
        break   # confirmed
    Misc.Pause(50)
```

Prefer mana drop as the **primary** confirmation. Journal messages vary by shard.

---

## 4. Transferring Items to Containers

### Move to a container

```python
Items.Move(item, destination_container, item.Amount)
Misc.Pause(1200)   # required — server needs time; skipping causes silent failures
```

`destination_container` can be any Item with a backpack (e.g. `Player.Backpack`,
`mount.Backpack`, or any targeted box).

### Move to ground at player's feet

```python
pos = Player.Position
Items.MoveOnGround(item, item.Amount, pos.X, pos.Y, pos.Z)
Misc.Pause(1000)
```

Use this to discard items that cannot be smelted, banked, or stacked, so they
don't keep the player overweight.

### Opening a container before reading its contents

Always open and wait before iterating `.Contains`:

```python
Items.UseItem(container)
Items.WaitForContents(container, 3000)
Misc.Pause(1200)
contents = list(container.Contains) if container.Contains else []
```

Skipping `WaitForContents` causes `.Contains` to return stale or empty data.

### Detecting a failed move

Compare the item's container serial after the move:

```python
Items.Move(item, destination, item.Amount)
Misc.Pause(1200)
found = Items.FindBySerial(item.Serial)
if found is not None and found.Container != destination.Serial:
    # server rejected the move (destination full, weight, etc.)
```

### Retry pattern for busy client

The server can reject moves with "You must wait to perform another action."
Check for it and retry:

```python
for attempt in range(5):
    Journal.Clear()
    Items.Move(item, destination, item.Amount)
    Misc.Pause(1200)
    if not Journal.Search("You must wait to perform another action."):
        break
    Misc.Pause(1200)   # extra cooldown before retry
```

---

## 5. Mobile Scanning — Type Safety

`Mobiles.ApplyFilter()` returns a .NET `List[Mobile]` in most RE builds, but some
builds return a plain Python `list`. `Mobiles.Select()` **requires** the .NET type
and raises `TypeError: expected List[Mobile], got list` if given a Python list.

**Safe pattern — always wrap with `GetEmptyMobileList` + `AddRange`:**

```python
from utilities.mobiles import GetEmptyMobileList

raw  = Mobiles.ApplyFilter(my_filter)
safe = GetEmptyMobileList(Mobiles)
safe.AddRange(raw)

nearest = Mobiles.Select(safe, 'Nearest')
weakest = Mobiles.Select(safe, 'Weakest')
```

`GetEmptyMobileList` creates an empty .NET `List[Mobile]` by applying a
never-matching filter, guaranteeing the right type for all RE versions.

Do **not** filter with a list comprehension and then pass to `Mobiles.Select`:

```python
# WRONG — comprehension produces Python list
pets = [m for m in Mobiles.ApplyFilter(f) if not m.IsGhost]
Mobiles.Select(pets, 'Weakest')   # TypeError
```

Instead use `Filter` properties to do the filtering server-side:

```python
f = Mobiles.Filter()
f.IsGhost  = 0      # 0 = not ghost, 1 = ghost, -1 = either
f.Friend   = True   # followers/pets only
f.RangeMax = 8
```

---

## 6. Gump Interaction

```python
# Wait for a specific gump (returns True if it appeared)
if Gumps.WaitForGump(GUMP_ID, 5000):
    Gumps.SendAction(GUMP_ID, BUTTON_ID)

# Check without blocking
if Gumps.HasGump():
    Gumps.CloseGump()

# Read all text lines from last gump
lines = list(Gumps.LastGumpGetLineList())
```

Gump IDs and button IDs must be discovered with the in-game **Gump Inspector**.
Always document discovered values with a `# verified via Gump Inspector` comment.

---

## 7. Journal-Based Feedback

```python
Journal.Clear()          # clear before an action so old lines don't match
# ... do action ...
Misc.Pause(800)          # give server time to send response

if Journal.Search("some phrase"):   # substring, case-sensitive
    ...

# Dump all recent lines (debugging)
for line in Journal.GetTextByType("Regular"):
    Misc.SendMessage(line, 0x3F)
```

Journal messages vary by shard. Keep phrase constants at the top of the script
and comment which shard they were confirmed on if relevant.

---

## 8. Import Conventions

```python
# ── Always at the very top of any script with local imports ──────────────────
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── IDE IntelliSense support — never runs inside RE ───────────────────────────
if False:
    from razorenhanced_stubs import *

# ── Local imports ─────────────────────────────────────────────────────────────
from glossary.colors import colors
from glossary.enemies import GetEnemies, GetEnemyNotorieties
from utilities.mobiles import GetEmptyMobileList
from utilities.items import FindItem
```

Never use `from Scripts.glossary.x import ...` or `from Scripts import config`.
The `Scripts.` prefix only works when the repo is a subdirectory named `Scripts`
inside the RE install directory — it breaks when scripts are run from any other path.
