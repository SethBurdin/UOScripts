For this script we want to create a script that will help us farm and collect the loot of mobs. 

I think the simplest approach will be to do a check to see if our pet is near us say every 5 seconds.

If the pet is further than2 tiles we want hte player to say all follow me, then once the pet is next to the player let's say we check up to 3 times every 3 seconds, once the pet is next to the player we want to say all guard me.

Additionally if our pet drops below 90% health we want to heal hit and if it's poisoned below 90% we want to cast arch cure then proceed. Not sure if it's possible to set a different timer for this functionality but it can be nested in the pet_distance_from_player functionality.