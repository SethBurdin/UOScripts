# Gatekeeper System — Requirements

## Overview
Three scripts work together over party chat to coordinate player extraction via Gate Travel.

1. **`util_runebook_explorer.py`** — Standalone tool: opens a runebook gump, dumps all rune data, and saves it to a JSON file keyed by runebook serial. Run this first to build the location database.
2. **`util_gatekeeper.py`** — Listens to party chat, selects the nearest rune to a requester's coordinates, casts Gate Travel, rezzes and heals ghosts on request, and manages its own mana via meditation.
3. **`util_extractor.py`** — Broadcasts the player's current tile coordinates over party chat as a `gate` command so the gatekeeper can open a gate to their location.

---

## Runebook Data

Rune data is parsed from the runebook gump at runtime. The gump exposes text pairs: rune name followed by its coordinate string (degree-minute notation, e.g. `47o 17'N, 139o 46'W`). The explorer script converts these strings to tile X/Y at parse time and stores both the friendly name and tile coordinates in JSON, keyed by runebook serial.

Gump sequence reference: `0x138e`. The gump exposes rune name and coordinate text one entry at a time. All pages of a runebook must be iterated to capture all runes (up to 16 per book).

---

## Party Chat Protocol

All commands are sent over party chat. The gatekeeper trusts all party members equally — no authorization list.

| Command | Sender | Meaning |
|---|---|---|
| `gate <X> <Y>` | Extractor / player | Open a gate to the rune nearest to tile X, Y |
| `gate <name>` | Player | Open a gate to the rune whose name partially matches `<name>` (case-insensitive) |
| `need rez` | Player | Cast Resurrection on the sender's ghost, then heal to full |

The extractor script broadcasts the player's current tile coordinates as `gate <X> <Y>`.

---

## Gate Travel Logic

- Parse incoming `gate` command: if the argument is two integers treat as tile X/Y; otherwise treat as a partial rune name match.
- For coordinate-based requests: convert rune coordinate strings to tile X/Y and select the rune with the smallest Euclidean distance to the requester.
- If the nearest rune is fewer than 3 screens away (~48 tiles), gate to it anyway and notify the party with the rune's friendly name.
- Cast `Gate Travel` (Magery), target the chosen rune in the runebook, wait for the moongate to appear, then `Items.UseItem` the gate.
- All runes are assumed to be on the gatekeeper's current facet — no cross-facet collision handling.

---

## Rez + Heal Logic

- Trigger: party chat message containing `need rez` (case-insensitive).
- Cast `Resurrection` (Magery) on the nearest ghost in range.
- Wait for the target to accept the resurrection (confirm `isGhost == False`) before proceeding.
- Cast `Heal` / `Greater Heal` (Magery) in a loop until `mobile.Hits >= mobile.HitsMax`.
- No movement — gatekeeper stays in place. Runebooks are locked down in the house.
- After rez+heal: no automatic gate. Player sends a `gate` command if they need one.

---

## Mana Management

- Before each action (Gate Travel or Rez) check current mana against the spell cost.
- If mana is sufficient: perform the action, then begin meditating afterward.
- If mana is insufficient: notify party chat once ("Gatekeeper low mana, meditating."), meditate until sufficient, then perform the action.

---

## Runebook Explorer (`util_runebook_explorer.py`)

Standalone, run once per runebook (or whenever runes change). Opens the runebook gump, iterates all pages, extracts name + coordinate pairs, converts coordinates to tile X/Y, and writes/merges the result into `runebook_locations.json` keyed by runebook serial. Targeting: runtime target cursor — script prompts the player to click the runebook.

---

## Open Questions

**1 — Runebook gump paging mechanics**
Does the gump expose a "next page" button we can click programmatically, or does paging require sending a specific button ID? This determines how the explorer iterates beyond the first 8 runes.

**2 — Rez trigger phrase**
Using `need rez` (case-insensitive) as the keyword. Confirm this is acceptable, or specify an alternative (e.g. `[REZ]`). case can always be ignored. let's change this to jsut rez no brackets.


**3 — Extractor Z coordinate**
The extractor will broadcast `gate <X> <Y>`. Should it include Z as well (`gate <X> <Y> <Z>`)? Relevant for dungeon levels where surface and underground share the same X/Y.