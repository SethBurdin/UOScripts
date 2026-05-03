# spell_button_id_resolver.py
# Utility to resolve the button ID for a spell in the inscription gump, given the flat spell list order and base button ID.

def get_spell_button_id(spell_name, spell_list, base_id=19):
    """
    Returns the button ID for a spell, given the flat spell list and base button ID.
    :param spell_name: Name of the spell (string)
    :param spell_list: List of all spell names in gump order (list of strings)
    :param base_id: The button ID of the first spell (default 19)
    :return: Button ID (int) or None if not found
    """
    try:
        idx = spell_list.index(spell_name)
        return base_id + idx
    except ValueError:
        return None

# Example usage:
# FLAT_SPELL_LIST = [
#     "Reactive Armor", "Clumsy", "Create Food", ... "Summon Water Elemental"
# ]
# button_id = get_spell_button_id("Summon Fire Elemental", FLAT_SPELL_LIST)
# print(button_id)
