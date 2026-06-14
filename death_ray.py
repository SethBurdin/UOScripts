if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.enemies import GetEnemyNotorieties, GetEnemies
from glossary.colors import colors

CAST_RANGE    = 10
CAST_WAIT_MS  = 5000
RETRY_PAUSE   = 500

def nearest_enemy():
    enemies = GetEnemies(Mobiles, 0, CAST_RANGE, GetEnemyNotorieties())
    if len(enemies) == 0:
        return None
    return enemies[0] if len(enemies) == 1 else Mobiles.Select(enemies, 'Nearest')

def main():
    if Player.BuffsExist('Death Ray', False):
        Misc.SendMessage('[death_ray] Buff active — nothing to do.', colors['green'])
        Misc.Pause(3000)
        return

    target = nearest_enemy()
    if target is None:
        Misc.SendMessage('[death_ray] No enemies in range.', colors['yellow'])
        Misc.Pause(3000)
        return

    Misc.SendMessage('[death_ray] Casting Death Ray on %s...' % target.Name, colors['cyan'])

    while not Player.BuffsExist('Death Ray', False):
        target = nearest_enemy()
        if target is None:
            Misc.SendMessage('[death_ray] No enemies in range — stopping.', colors['yellow'])
            Misc.Pause(3000)
            return

        Spells.CastMastery('Death Ray')
        Target.WaitForTarget(CAST_WAIT_MS, False)
        Target.TargetExecute(target)
        Misc.Pause(RETRY_PAUSE)

    Misc.SendMessage('[death_ray] Death Ray buff applied.', colors['green'])

main()
