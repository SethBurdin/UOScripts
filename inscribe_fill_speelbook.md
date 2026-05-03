Script used to pull the materials to fill an order in use with inscription skill.




Make sure the player uses a new tool.

Prompt Target to select either a container or spellbook to fill.

Create an order to fill that we can use either a list or dict of what scrolls we need to create.

Infer the order to fill on what spells to mats to pull to the player's inventory.
Create Option for Magery
Create Option for Spellweaving

Mana effeciencies:
    Have the player begin meditating at 40 mana and wait until back to max mana.

General flow: 
    0. Prompt Target to select either a container or spellbook to fill.
    1. Use inscription tool
    2. Use menu prompts to decide what needs to be crafted to fill a given book.  all the spells needed fill a book (or fill as they are crafted)
    3. Validation that the scroll is created successfully.
    4. Depending on decision 2 drag the spells to the spellbook.
    5. Stop script.

