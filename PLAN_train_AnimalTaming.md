# Implementation Plan: `train_AnimalTaming.py`

---

## Feature Tracker

### 1. Track Already-Tamed Animals (Skip Re-Taming)

**Status:** Working

**What it does:**
When a tame succeeds, the animal's serial is added to `alreadyTamedSerials` (a `set()`). `FindAnimalToTame()` filters out any mobile whose serial is in that set.

Pre-existing pets (already following at script startup) are recorded in `preExistingPetSerials` and also excluded from targeting.

**Current issue:**
- `alreadyTamedSerials` is **session-only** — it resets every time the script is restarted.
- Animals that are **released** and then walk back into range will have the same serial, so they will be skipped correctly *within that session*.
- If the script restarts mid-session (crash, re-add), previously-released animals are forgotten and could be re-tamed.

**Proposed fix:**
- Consider writing `alreadyTamedSerials` to a temp file on disk between script runs so it persists across restarts.
- Alternatively, rely on the `Misc.IgnoreObject()` call that already fires after taming — **Razor Enhanced's ignore list is persistent within the client session**, so serials added via `IgnoreObject` survive script restarts as long as Razor Enhanced is open. Confirm whether this is sufficient.

---

### 2. Automatic Target Acquisition

**Status:** Working

**What it does:**
`FindAnimalToTame()` uses `Mobiles.Filter` with:
- `tameables.GetAnimalIDsForPlayerSkill()` to get body IDs scaled to current skill
- Notoriety filter = `[3]` (gray/wild only)
- Range 0–12 tiles
- `CheckIgnoreObject = True` to skip `IgnoreObject`-flagged mobiles

After filter, it double-checks notoriety, name against `petsToIgnore`, and serial against tracked sets. Returns the nearest qualifying animal via `Mobiles.Select( tameableMobiles, 'Nearest' )`.

**Current issue:**
- The notoriety filter (`3` = gray) may not reliably exclude tamed animals in all server configurations. Some servers keep tamed animals gray until they fully bond.
- `tameables.GetAnimalIDsForPlayerSkill()` uses the `tameables` glossary — the animal list there may be incomplete or have wrong difficulty values.
- The `minimumTamingDifficulty` config value can cause zero qualifying animals if set too high for the skill level — there is a warning printed at startup for this.

**TODO:**
- [ ] Verify `tameables.animals` has complete and correct difficulty data for the animals present at your taming location.
- [ ] Test the notoriety filter behavior on your specific shard — tamed animals on some shards may still appear gray briefly.
- [ ] Consider adding a `maximumTamingDifficulty` config to narrow the skill window and avoid wasting time on too-hard animals.

---

### 3. Rename Once Tamed

**Status:** Working

**What it does:**
On a successful tame (`'It seems to accept you as master.'`), the script calls:
```python
if animalBeingTamed.Name != renameTamedAnimalsTo:
    Misc.PetRename( animalBeingTamed, renameTamedAnimalsTo )
```
The target rename string is configured via:
```python
renameTamedAnimalsTo = 'aaa'
```

**Why the name check matters:**
`petsToIgnore` includes `renameTamedAnimalsTo`, so any already-renamed animal will be automatically skipped by `FindAnimalToTame()`. This is the primary defense against re-taming released pets that are still in range.

**What was improved:**
- After calling `Misc.PetRename`, the script now waits for the existing `Misc.Pause(2000)` (which also covers follower count registration), then reads the mobile's name back from the server via `Mobiles.FindBySerial`.
- If the name hasn't changed, it retries once with a fresh `Misc.PetRename` + 1500ms pause and logs the outcome.
- A `WARNING` message is sent if the name still doesn't match after retry, making silent failures visible.

**Remaining issue:**
- `Misc.PetRename` may open a gump confirmation on some shards. If it does, neither the first attempt nor the retry will succeed until dismissed. This would show up clearly as the repeated `WARNING` in the log.

**TODO:**
- [ ] Test on your shard and watch the `[TAMING]` log messages to confirm rename succeeds on the first attempt.
- [ ] If you see repeated `Rename pending` warnings, the shard requires a gump — at that point add `Gumps.WaitForGump` + `Gumps.SendAction` handling after each `Misc.PetRename` call.

---

### 4. Release Once Tamed

**Status:** Untested — next to verify

**What it does:**
After taming and renaming, the script checks follower count:
```python
if Player.Followers > numberOfFollowersToKeep:
    Misc.WaitForContext( tamedSerial, 2000 )
    Misc.ContextReply( tamedSerial, 9 )          # opens "Release" context menu option
    Gumps.WaitForGump( 2426193729, 10000 )       # waits for the confirm dialog
    Gumps.SendAction( 2426193729, 2 )            # clicks "Yes"
```

`protectedPetNames` and `preExistingPetSerials` are checked before releasing — matching animals are kept regardless of follower count.

**Current issues:**
- **Context menu option index `9` is hardcoded.** The index of "Release" in the context menu varies by server version. If the index is wrong, nothing happens and the pet is silently kept.
- **Gump ID `2426193729` is hardcoded.** If the server sends a different release confirmation gump, this will time out silently.
- **Follower count timing:** `Misc.Pause( 2000 )` is used to wait for the server to register the new follower, but this may not be long enough on high-latency shards. If followers haven't updated yet, the release check fires with a stale count and the pet may be kept when it should be released.

**TODO:**
- [ ] Verify context menu index `9` is correct for "Release" on your shard — use the `inspect_mobile.py` or `inspect_mobile2.py` script to check context menu entries for a pet.
- [ ] Verify gump ID `2426193729` matches your server's release confirmation dialog.
- [ ] Consider increasing `Misc.Pause` before the follower check, or polling `Player.Followers` in a short loop until it changes.

---

## Config Reference

| Variable | Default | Purpose |
|---|---|---|
| `renameTamedAnimalsTo` | `'aaa'` | Name to give each tamed animal |
| `protectedPetNames` | `[...]` | Named pets that are never released |
| `petsToIgnore` | includes rename target + protected names | Names never targeted for taming |
| `numberOfFollowersToKeep` | `1` | Max followers before releasing |
| `maximumTameAttempts` | `0` (unlimited) | Max tries per animal before ignoring |
| `minimumTamingDifficulty` | `31` | Minimum animal difficulty to target |
| `healUsing` | `'None'` | `'Healing'`, `'Magery'`, or `'None'` |
| `enablePeacemaking` | `False` | Auto-peacemake aggressive animals |
| `enableFollowAnimal` | `True` | Walk toward target if too far |

---

## Open Questions

- What taming location / animal types are being used? Confirming the `tameables.animals` data is correct for those mobs will validate auto-targeting.
- Does your shard require a gump confirmation for pet renames?
- What is the usual latency? `journalEntryDelayMilliseconds = 100` and the `Misc.Pause( 2000 )` post-tame check may need upward adjustment on higher-latency shards.
