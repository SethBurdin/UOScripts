import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.items import myItem

wood = {
    # Weights are set to None since the weight varies depending on the player's mining skill
    'log': myItem('log', 0x1BDD, 0x0000, 'log', None)


}
