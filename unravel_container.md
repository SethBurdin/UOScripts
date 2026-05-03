We need to make a script that will grab the items off a beetle and add it to a prompted box, then we will use the imbueing skill to unravel container for said both.

---

## Questions before building

**1. Which items move from the beetle?**
a
- a) All items in the beetle's backpack
- b) Only magical items (same check as loot_all.py — skip gems/gold/non-magic)

**2. Beetle detection**
a then fallback to b
- a) Auto-detect nearest follower with a backpack (same as loot_all.py)
- b) Prompt player to target the beetle

**3. The "prompted box" — one target or two?**
The existing `imbue container.py` targets a container and unravels everything in it.

Unravelling can be done in bulk so let's set it up to stop once the player weighs over 400 and unravel container at that time.
- a) One prompt: target a box → move beetle items into it → immediately unravel it
- b) Two prompts: target the beetle, then target the destination/unravel box separately

**4. After unraveling, what happens to the box?**
If there is more items on the beetle continue the transfer unravel. don't worry about whats left in the box
- a) Leave it as-is (it'll be empty after unravel)
- b) Script should loop — keep unraveling until beetle is empty (multiple batches)
