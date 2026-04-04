# Taming Scripts

Three scripts work together to automate animal taming patrols.

---

## 1. `util_recordKirinWaypoint.py` — Waypoint Recorder (Kirin)

Records your movement as a series of waypoints saved to `waypoints_KirinTaming.json`.

**Usage:**
1. Gate/recall to the Ilshenar kirin/unicorn spawn area
2. Run the script
3. Walk your patrol loop
4. Stop the script — waypoints are saved automatically

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `outputFile` | `waypoints_KirinTaming.json` (same folder as script) | Where waypoints are saved |
| `recordIntervalTiles` | `5` | Minimum tile distance moved before a new point is recorded |

**Notes:**
- Writes incrementally while running — stopping mid-route still saves what was recorded
- Output file is read directly by `skill_KirinTaming.py`
- Must be run on the **correct map/facet** — coordinates are not facet-aware; recording on Trammel when the spawn is in Ilshenar will produce unusable waypoints

---

## 2. `util_recordWaypoints.py` — Waypoint Recorder (General)

Same recorder as above but for use with `util_patrolWaypoints.py`.

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `outputFile` | `waypoints_random.json` (same folder as script) | Change this to match the filename set in `util_patrolWaypoints.py` |
| `recordIntervalTiles` | `5` | Minimum tile distance before recording a new point |

---

## 3. `skill_KirinTaming.py` — Kirin / Unicorn Patrol Bot

Patrols the Ilshenar kirin/unicorn spawn, taming every ki-rin and unicorn found. When follower slots fill up, finds a **paragon** variant and kills it with pets to free a slot.

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `baseFollowers` | `1` | Follower count the character normally runs with. Purge triggers when followers exceed this. |
| `followerCap` | `5` | Maximum follower slots available. |

**Waypoints file:** `waypoints_KirinTaming.json` (same folder as script) — record with `util_recordKirinWaypoint.py`.

**Patrol loop priority (per iteration):**

| Priority | Condition | Action |
|---|---|---|
| 1 — Purge | `Followers > baseFollowers` | Find nearest paragon kirin/unicorn within 20 tiles → back away 7 tiles → all kill with pets → block until dead |
| 2 — Tame | `Followers <= baseFollowers` | Find nearest untamed kirin/unicorn within 12 tiles → tame it |
| 3 — Walk | No animal in range | Walk to next waypoint, advance index |

**Taming behaviour:**
- Retries the skill on each resist (`You fail to tame the creature.`)
- Follows the animal if it moves out of range during taming
- Detects tame success via follower count increase (catches cases where the journal message is missed)
- 13-second poll window per attempt before retrying the skill
- Permanently skips: already tamed, too many owners, no taming chance, animal vanished
- Transient failures (path blocked, interrupted) fall through to walk one step before retrying

**Paragon detection caching:**
- First scan of each kirin costs 1 second (`WaitForProps`)
- Both paragon and non-paragon results are cached by serial — subsequent scans are instant
- Cache is safe to keep permanently: paragon status is fixed at spawn; new spawns get new serials

**Safety checks:**
- Aborts with a clear error message if the nearest waypoint is more than 150 tiles away (wrong map or wrong facet)
- Prints starting waypoint index and distance on launch

---

## 4. `util_patrolWaypoints.py` — General Purpose Patrol Bot

Patrols any recorded route, taming any skill-appropriate animal found. Intended for general skill training across multiple animal types.

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `playerAttacksMobs` | `False` | `True` = player directly attacks paragons; `False` = sends pets with all kill |
| `baseFollowers` | `3` | Follower count baseline; purge triggers above this |
| `minimumTamingDifficulty` | `0` | Skip animals below this taming difficulty (raise to avoid trivial animals) |
| `debugMode` | `False` | Print body IDs, colors, and filter results for every nearby mobile — useful for diagnosing why an animal is being skipped |
| `waypointsFile` | `waypoints_random.json` (same folder) | Path to the waypoints JSON file to patrol |

**Patrol loop priority (per iteration):**

| Priority | Condition | Action |
|---|---|---|
| 1 — Purge | `Followers > baseFollowers` | Find nearest paragon of a tameable body type within 20 tiles → attack with player or pets → block until dead |
| 2 — Tame | `Followers <= baseFollowers` | Find nearest skill-appropriate animal within 12 tiles → tame → release → kill with pets/player |
| 3 — Walk | No animal in range | Walk to next waypoint, advance index |

**Key differences from `skill_KirinTaming.py`:**
- Uses the `tameables` module to dynamically match animals appropriate for the player's current skill level — works across all animal types, not just kirins/unicorns
- After a successful tame, **releases** the animal via context menu gump and then **kills** it (skill training loop — tame → release → kill → repeat)
- `playerAttacksMobs` mode available for characters without combat pets
- `debugMode` prints detailed filter diagnostics per mobile for troubleshooting skipped animals
- Stops automatically when Animal Taming reaches skill cap

**Unreachable animal handling:**
- Tries `MoveToAnimal` up to 3 times before giving up
- If still unreachable after 3 attempts, attacks the animal directly to clear it (prevents the loop from stalling indefinitely on terrain-blocked mobs)

**Taming behaviour:**
- Same journal polling and follower-count detection as `skill_KirinTaming.py`
- Detects `You fail to tame the creature.` to immediately retry the skill on each resist
- Transient failures are not blacklisted — animal will be retried on the next pass

---

## Shared Concepts

### SKIP vs False return from `TameAnimal`

| Return | Meaning | Patrol loop behaviour |
|---|---|---|
| `True` | Tamed successfully | Proceed to release/kill (patrol) or continue (kirin) |
| `SKIP` | Permanent failure — gone, already tamed, no chance, too many owners | Add serial to `alreadyTamedSerials`, never target again this session |
| `False` | Transient failure — path blocked, interrupted | Do NOT blacklist; walk one step and retry on next pass |

### Waypoint file format

Plain JSON array of `[x, y]` pairs:

```json
[
    [1620, 1185],
    [1625, 1190],
    [1630, 1195]
]
```

### Map coordinate ranges

| Map | X range | Y range |
|---|---|---|
| Trammel / Felucca | 0 – 7167 | 0 – 4095 |
| Ilshenar | 0 – 2303 | 0 – 1599 |
| Malas | 0 – 2047 | 0 – 2047 |
| Tokuno | 0 – 1447 | 0 – 1447 |

Razor Enhanced's `Player.Position.X/Y` returns coordinates in the current map's space. **Always record waypoints on the same map/facet where the script will run.**
