This folder will contain the logic and inner works of a script using Iron Python and Razor Enahnced Client to provide the following functionalites:
1. Prompt for location to extract similar to Guardian's current working.
2. The ability to use a waypoint.json config to get to destination.
3. Logic to hide when an enemy is present. hostile mob 10 tiles away.
4. Mount management, if hidden character to remain mounted.
5. Corpse discover similar to loot all script.
6. Skin and processes corpses' leather similar to skinning where it cuts the piece of leather.
7. transfer items that do not need to be processed directly to beetle backpack.
8. Transfer failure detection. No message is generated, but genenerally when the beetle if full the transfers just seem like they aren't working.
9. Drop stacks of leather on ground if the beetle is full.
10. an extraction routine, if a waypoint is used to navigate to the loot area it should use the inverse waypoint and recall home once player reaches desired coorinates.

We're going to shift the existing paradigm for this project. Instead of having everything directly in script, we'll isolate functionalities to functions within a given file similar to our runebook util. Those functions should call out there inputs parameters and what it's returning.


I've reviewed extraction_looter/project.md, DESIGN_PRACTICES.md, guardian.md, loot_all.md, util.skinning.md, and the existing waypoints JSON files. The scope is clear at a high level — here are the specific things I'd want to nail down before writing any code:

1. Navigation flow (points 1 + 2)

Guardian prompts for a rune name, then gates/recalls there. The waypoints JSONs are just [[x,y]] patrol coordinates. Are these two separate phases — recall to the area first (via runebook), then walk the waypoint loop? Or does the waypoint handle everything (player walks there manually then the loop starts)?
We'll want to recall to destination rune and determine if we need to walk to a loot location to get to the corpses. It might sense to have a config to map the locations and whether or not they need to walk to a destination.

And for multiple locations: is the plan one waypoints file per farming spot (e.g. waypoints_ww.json), with the startup prompt selecting which to load? Or some other structure?
For now let's leverage a single loot destination.

2. Hide behavior (point 3)

When a hostile appears within 10 tiles — use the Hide skill? Cast Invisibility? Both? And after hiding, does the script: (a) pause and poll until the hostile leaves range before resuming patrol, (b) keep moving along waypoints while hidden, or (c) something else? start casting invis stop any loot actions, and mount. let's just use magery.

3. Looting scope (points 5 + 6)

Is this script exclusively for leather extraction (skin → collect hides → cut to leather → transfer), or should it also loot magical items off corpses the way loot_all.md describes? Or both?
Let's configure an option for both.

4. Beetle full behavior (points 8 + 9)

When the beetle is detected full and leather is dropped on the ground — does the script keep running (process more corpses, keep dropping), or stop and alert the player to deal with inventory?
We will only drop the leather. Once there is no corpses or leather to deal with the script should fire the signal to return home. No other items should be dealt with if the transfer are failing. trainer_carpentery has the transfer failure logic.

5. Skinning reuse

skinning.py already implements scan → skin → transfer. Should the new module import/call logic from it, or does the function-based refactor mean rewriting those pieces as importable functions inside extraction_looter/?
Every piece of that files implementation is directly applicable to this script.

6. File structure

What's the intended layout within extraction_looter/? Something like main.py + nav.py + stealth.py + corpse.py + transfer.py? Or one file with sections?
the main script is extraction_looter.
the loot specific elements should live in loot_util
the hiding should be based on a skill check. magery > 65 should invis. Hiding is used if hiding > 70
corpse_util should hold the logic of interacting with the corpse.
inspect_items holds the logic for dealing with knowing what items to grab.
let's make a containers_util to hold the transfer between various containers.
