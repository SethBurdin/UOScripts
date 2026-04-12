# inscription_fill_spellbook.py — Implementation Reference

## Overview

A Razor Enhanced script for automating magery scroll production and spellbook filling in Ultima Online. On startup, the player selects one of two modes via a numbered in-game chat prompt:

| Mode | Description |
|------|-------------|
| **CRAFT** | Opens the inscription crafting gump and crafts one of every magery scroll (all 64 spells across 8 circles), depositing each into a designated scroll chest. |
| **FILL** | Pulls scrolls from the scroll chest and drags them into a player-targeted spellbook. |

---

## Configuration (`cfg` class)

All tunable settings live in the `cfg` class at the top of the file. Edit once before running.

| Setting | Default | Purpose |
|---------|---------|---------|
| `scroll_container_serial` | `None` | Serial of the scroll chest (required — set this) |
| `craft_delay` | `3500 ms` | Wait after clicking a spell button in the gump |
| `gump_open_delay` | `3000 ms` | Timeout waiting for the crafting gump to appear |
| `item_move_delay` | `1000 ms` | Pause between `Items.Move` calls |
| `circle_switch_ms` | `800 ms` | Pause after switching circles in the gump |
| `action_pause_ms` | `500 ms` | General inter-action breathing room |
| `post_craft_settle` | `800 ms` | Extra pause before searching for a freshly crafted scroll |
| `meditate_threshold` | `40` | Mana level that triggers a meditation break |
| `meditate_poll_ms` | `500 ms` | Polling interval while waiting for mana to refill |
| `mana_wait_timeout` | `90000 ms` | Maximum time to wait for full mana before giving up |
| `log_file` | (hardcoded path) | Path to an append-only log file; set to `None` to disable |

---

## Item ID Constants

| Constant | Value(s) | Description |
|----------|----------|-------------|
| `SCRIBE_PEN_IDS` | `0x0FBF`, `0x0FBE` | Inscription pen graphic IDs |
| `SPELLBOOK_IDS` | `0x0EFA`, `0x0EFF` | Valid spellbook graphic IDs |
| `BLANK_SCROLL_ID` | `0x0E34` | Blank scroll graphic ID |
| `REAGENT` dict | — | Maps 2-letter abbreviations to reagent item IDs (BP, BM, GA, GI, MR, NS, SS, SA) |

---

## Gump Navigation

The inscription crafting gump uses a fixed button layout shared by all RunUO/ServUO crafting skills (`CRAFT_GUMP_ID = 949095101`).

- **Circle buttons** (left panel): `1, 8, 15, 22, 29, 36, 43, 50` — one per circle, pattern `1 + (circle - 1) * 7`.
- **Spell buttons** (right panel): `2, 9, 16, 23, 30, ...` — pattern `2 + slot * 7` (slot is 0-based position within the circle).
- **Exit button**: `0`.

The gump ID is self-healing: if the actual gump ID differs from the expected constant, the script detects and updates `CRAFT_GUMP_ID` automatically.

---

## Scroll Data (`MAGERY_SCROLLS`)

A list of 64 tuples, one per magery spell, in gump slot order within each circle:

```
(spell_name, circle, scroll_item_id, [reagent_item_ids])
```

Circles 1–8, 8 spells each. Reagent lists match standard UO requirements. A parallel dict `_SPELL_NAME_TO_ID` provides fast name→item-ID lookups.

A stub list `SPELLWEAVING_SCROLLS` exists for future shard-specific spellweaving support.

---

## Helper Functions

### `Prompt(question, options, timeout=30)`
Displays numbered choices in cyan chat text, then polls the journal for the player to type a digit. Returns the 1-based selection; defaults to `1` on timeout.

### `log(msg, color)`
Prints a `[INSCRIBE]` prefixed message in-game and appends a timestamped line to `cfg.log_file`.

### `journal_contains_any(phrases)`
Returns `True` if any of the given strings appear in the current journal buffer.

### `find_inscription_tool()`
Searches the player's backpack for any item matching `SCRIBE_PEN_IDS`. Returns the first match or `None`.

### `get_scroll_container()`
Looks up the chest by `cfg.scroll_container_serial`, opens it (so RE caches its contents), and returns the `Item` object.

### `meditate_until_full()`
Activates the Meditation skill and polls `Player.Mana` until fully restored or `mana_wait_timeout` elapses.

---

## Gump Management

### `open_craft_gump(tool)`
Uses the inscription pen, waits for the crafting gump via `Gumps.WaitForGump`, and auto-corrects `CRAFT_GUMP_ID` if the actual ID differs.

### `close_craft_gump()`
Sends gump button `0` (Exit).

---

## Craft Success Detection

### `craft_one_scroll(spell_name, circle, spell_btn, current_circle)`

1. Switches circles if needed (sending the circle button + `circle_switch_ms` pause).
2. Records `mana_before`.
3. Sends the spell button and waits `craft_delay` ms.
4. **Success condition:** `Player.Mana < mana_before` — the server consumed mana, confirming acceptance.
5. **Fail condition:** mana unchanged — reagents/blank scrolls missing or skill check failed.
6. Returns a status string (`"success"`, `"fail"`, `"no_gump"`) and the updated `current_circle`.

No journal text parsing is used for success detection.

---

## Mode 1 — `mode_craft()`

**Flow:**

1. Open the scroll chest and find an inscription pen.
2. Pre-compute each spell's right-panel button index from its 0-based slot within its circle.
3. Iterate `MAGERY_SCROLLS` in order:
   - If mana is below `meditate_threshold`: close the gump → meditate → reopen the gump.
   - Call `craft_one_scroll(...)`.
   - On **`"success"`**: search the backpack for the scroll (`_FindItem`) and move it to the chest.
   - On **`"fail"`**: increment fail counter and continue.
   - On **`"no_gump"`**: check for tool-wore-out journal message. If the pen broke, grab the crafted scroll (if present), find a replacement pen, and reopen the gump. Otherwise stop.
4. Close the gump and log totals.

**Pen breakage handling:** When the gump closes unexpectedly, the script checks the journal for worn-out phrases, recovers the scroll that was in-flight, equips a new pen from the backpack, and continues without losing the craft.

---

## Mode 2 — `mode_fill()`

**Flow:**

1. Open the scroll chest.
2. Prompt the player to target a spellbook (validated against `SPELLBOOK_IDS`).
3. Iterate `MAGERY_SCROLLS`; for each spell:
   - Search the chest with `_FindItem(scroll_id, chest)`.
   - If found, `Items.Move` it to the spellbook and pause.
   - If not found, log a warning.
4. Log totals (added / missing).

No spell-content detection is performed. The server silently rejects duplicate spells, so the operation is safe to repeat.

---

## Entry Point (`main()`)

1. Writes a run-start header to the log file.
2. Calls `Prompt(...)` to select CRAFT (1) or FILL (2).
3. Dispatches to `mode_craft()` or `mode_fill()`.
4. Calls `main()` at module level — Razor Enhanced executes scripts as top-level code.

---

## Logging

All log entries are written to both in-game chat (`Misc.SendMessage`) and an append-only file at `cfg.log_file`. Each file line is prefixed with a `YYYY-MM-DD HH:MM:SS` timestamp. Run boundaries are marked with a `===` header block.

---

## Known Limitations / Extension Points

- `SPELLWEAVING_SCROLLS` is an empty stub — populate it per-shard following the same tuple schema.
- `cfg.scroll_container_serial` must be set manually before running.
- Gump button constants (`CIRCLE_BTNS`, `SPELL_BTN_FIRST`, `SPELL_BTN_STEP`) may need adjustment for non-RunUO shards.
- CRAFT mode does not verify reagent quantities before attempting; failed crafts are silently counted.
