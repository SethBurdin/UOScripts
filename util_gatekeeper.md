# Gatekeeper System — Requirements

## Overview
Three scripts work together over party chat to coordinate player extraction via Gate Travel.

1. **`util_runebook_explorer.py`** — Standalone tool: scans one or more runebooks in a single session, merging all rune data into a single `runebook_locations.json` file keyed by runebook serial. Re-run whenever runes change.
2. **`util_gatekeeper.py`** — Listens to party chat, selects the nearest rune to a requester's coordinates, casts Gate Travel, rezzes and heals ghosts on request, and manages its own mana via meditation.
3. **`util_extractor.py`** — One-shot script. Reads the player's current tile coordinates once and broadcasts a single `gate <X> <Y>` command over party chat, then exits.

---

## Runebook Data

Rune data is stored in a single static file: `runebook_locations.json`, located in the script folder. The explorer script populates this file and can be re-run any time runes change.

File structure — top-level dict keyed by serial hex string, each entry contains the book's metadata and its rune list:
```json
{
  "last_updated": "2026-04-04T11:34:43",
  "runebooks": {
    "0x4002D1D9": {
      "serial_hex": "0x4002D1D9",
      "serial_dec": 1073926617,
      "name": "Runebook",
      "charges": 0,
      "max_charges": 18,
      "runes": [
        { "slot": 0, "name": "bank", "coordinate": "83o 13'S, 152o 47'E", "has_location": true, "gate_button": 98 }
      ]
    }
  }
}
```

The gatekeeper loads this file once at startup and flattens all runes across all books into a single searchable list. Each rune retains its source `serial_hex` so the gatekeeper can open the correct book before firing the gate button.

---

## Party Chat Protocol

All commands are sent over party chat. The gatekeeper trusts all party members equally — no authorization list.

| Command | Sender | Meaning |
|---|---|---|
| `gate <X> <Y>` | Extractor | Open a gate to the rune nearest to tile X, Y (broadcast once by the extractor then script exits) |
| `gate <name>` | Player | Open a gate to the rune whose name partially matches `<name>` (case-insensitive) |
| `rez` | Player | Cast Resurrection on the sender's ghost, then heal to full |

---

## Gate Travel Logic

- Parse incoming `gate` command: if the argument is two integers treat as tile X/Y; otherwise treat as a partial rune name match.
- For coordinate-based requests: convert rune coordinate strings to tile X/Y and select the rune with the smallest Euclidean distance to the requester.
- If the nearest rune is fewer than 3 screens away (~48 tiles), gate to it anyway and notify the party with the rune's friendly name.
- Look up the rune's source book serial in `runebook_locations.json`, open that book with `Items.FindBySerial` + `Items.UseItem`, then fire `Gumps.SendAction(89, gate_button)`. Wait for the moongate to appear, then `Items.UseItem` the gate.
- On successful gate: broadcast in party chat `Gate opened to <rune friendly name>`.
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

## Extractor (`util_extractor.py`)

One-shot, run when the player needs a gate. Reads `Player.Position` (X, Y), broadcasts `gate <X> <Y>` in party chat, and exits. No looping. No runebook knowledge — coordinate-to-rune resolution is entirely the gatekeeper's responsibility.

---

## Resolved Decisions

- **Runebook gump ID**: `89` (confirmed — buttons 102, 103, 104 observed for gate actions; exact stride TBD from `util_runebook_explorer.py` JSON output)
- **Rez trigger phrase**: `rez` (case-insensitive, no brackets)
- **Extractor command format**: `gate <X> <Y>` — extractor broadcasts raw tile coordinates once and exits. The gatekeeper resolves the nearest rune internally. Players can also type `gate <partial-name>` manually in party chat.