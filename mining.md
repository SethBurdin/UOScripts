Feature:
Check player location.
Journal checks to see if either..
    1. There is no metal to mine here. Stop Mining
    2. Backpack full
    3. You can't mine there signal to change the minng direction of the player.

Existing scripts references:
    Mine to the left.py
        a: This script just mines relative of player location. If entering a cave this functionality does not work properly.
        b. Use this logic in conjuction with the journal search to check multiple directions around the player for viable mining location.
        c. If it's possible for the script to detect minable rock let's implement that.
    Ultamite Mining 
        a: (Check the player wait and stop mining until transfer to mount's inventory is complete.)
        b: When smelting grab chunks of 20 ore at a time to smelt.
        c. Ensure we can either detect a forge or prompt player to select forge.
        d. This script was used to work with a fire beetle, I don't have one so just be aware some of the functionality in this script is either not working or not applicaple. Do some external validations to implement a solution.

As in our taming bot script, we want to use a prompt and journal search to control what the player wants to do. Transfering items to the pack should happen when the palyer exceeds 400 stones.

Create a separate config file that will hold the options we will be defining through this script.

v2. Will contain some options to recall or gate to specific rune slots in a runebook.
    -configurable option to recall or gate.
    - checks to ensure gate is successful.
