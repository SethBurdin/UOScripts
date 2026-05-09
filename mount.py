# mount.py
# Disables war mode then mounts the nearest friendly non-human mobile.

if False:
    from razorenhanced_stubs import *

Player.SetWarMode(False)
Misc.Pause(400)

if Player.Mount is not None:
    Misc.SendMessage('[mount] Already mounted.', 88)
else:
    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.IsHuman  = False
    f.RangeMin = 0
    f.RangeMax = 5

    nearest, nearest_dist = None, 9999
    for mob in Mobiles.ApplyFilter(f):
        if mob.Serial == Player.Serial:
            continue
        d = Player.DistanceTo(mob)
        if d < nearest_dist:
            nearest_dist = d
            nearest = mob

    if nearest is None:
        Misc.SendMessage('[mount] No friendly non-human found within 5 tiles.', 38)
    else:
        Mobiles.UseMobile(nearest.Serial)
