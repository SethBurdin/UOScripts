We want to create a script that can grab the items on a corpse and transfer it to a beetle. The Mining script is already familar with transfer to the beetle. 

The eloot script should have some references to find the items on a corpse, but we haven't actually successfully looted so make few assumptions.

We want to grab any magical item and load it into our beetle.

---

## Questions before building

**1. What makes an item "magical"?**
We made a script that can inspect the properties of an item i dont remember the name, but inspect_item i think it is that worked. Lesser magic item, artifact, etc are the properties we want. Please lookup the full list.


- a) Has any magic property in `GetPropStringList` (e.g. Damage Increase, Hit Chance, etc.) — reliable but requires fetching props for every item
- b) Non-default hue (hue != 0) — faster, but misses some named items
- c) Both: hue check first, then property fetch as fallback

**2. Loop behavior**
b is fine.

- a) Loop continuously, watching for new corpses as they appear (like mining.py)
- b) Run once on the nearest corpse, then exit

**3. Items to skip**
b
- a) Skip gold and stackables/consumables — only take wearable gear
- b) Take everything that passes the magical check, no exclusions

**4. Beetle detection**
b
- a) Auto-detect the nearest follower with a backpack (same as mining.py)
- b) Prompt the player to target the beetle once at startup