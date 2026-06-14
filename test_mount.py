# test_mount.py
# Standalone mount/dismount tester.
# Tries several API approaches in sequence and reports what works.
# Run this while standing next to the pack beetle.

if False:
    from razorenhanced_stubs import *

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glossary.colors import colors

BEETLE_BODY   = 0x00EF
SCAN_RANGE    = 10
PAUSE_MS      = 2000

_TAG = '[mount_test]'


def log(msg, color=colors['cyan']):
    Misc.SendMessage(_TAG + ' ' + msg, color)


def find_beetle():
    filt          = Mobiles.Filter()
    filt.Enabled  = True
    filt.RangeMax = SCAN_RANGE
    filt.IsHuman  = False
    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial:
            continue
        if mob.Body == BEETLE_BODY and mob.Backpack is not None:
            log("Body-ID: %s (0x%X)" % (mob.Name, mob.Serial), colors['green'])
            return mob
    for mob in Mobiles.ApplyFilter(filt):
        if mob.Serial == Player.Serial:
            continue
        if mob.Backpack is not None:
            log("Fallback: %s (0x%X)" % (mob.Name, mob.Serial), colors['green'])
            return mob
    log("No pack animal found.", colors['red'])
    return None


def dismount():
    if Player.Mount is None:
        log("Already on foot.", colors['yellow'])
        return True
    log("Dismounting via UseMobile(Player.Serial)...")
    Mobiles.UseMobile(Player.Serial)
    Misc.Pause(PAUSE_MS)
    if Player.Mount is None:
        log("Dismount OK.", colors['green'])
        return True
    log("Dismount FAILED.", colors['red'])
    return False


def try_mount(serial):
    """Try every known approach until one confirms Player.Mount is set."""
    if Player.Mount is not None:
        log("Already mounted.", colors['yellow'])
        return

    approaches = [
        ("Mobiles.UseMobile(serial)",
         lambda s: Mobiles.UseMobile(s)),
        ("Mobiles.UseMobile(int(serial))",
         lambda s: Mobiles.UseMobile(int(s))),
        ("Misc.UseContextMenu(serial, 'Mount', 2000)",
         lambda s: Misc.UseContextMenu(s, "Mount", 2000)),
        ("Misc.UseContextMenu(int(serial), 'Mount', 2000)",
         lambda s: Misc.UseContextMenu(int(s), "Mount", 2000)),
        ("Misc.UseContextMenu(serial, 'Ride', 2000)",
         lambda s: Misc.UseContextMenu(s, "Ride", 2000)),
        ("Misc.UseContextMenu(int(serial), 'Ride', 2000)",
         lambda s: Misc.UseContextMenu(int(s), "Ride", 2000)),
        ("Misc.UseContextMenu(serial, 2, 2000)",
         lambda s: Misc.UseContextMenu(s, 2, 2000)),
        ("Misc.UseContextMenu(serial, 1, 2000)",
         lambda s: Misc.UseContextMenu(s, 1, 2000)),
    ]

    for label, fn in approaches:
        log("Trying: %s" % label)
        try:
            fn(serial)
            Misc.Pause(PAUSE_MS)
            if Player.Mount is not None:
                log("SUCCESS: %s" % label, colors['green'])
                return
            log("No mount confirmed.", colors['yellow'])
        except Exception as e:
            log("Error: %s" % str(e), colors['red'])

        # Dismount between attempts so next attempt starts from foot
        if Player.Mount is not None:
            Mobiles.UseMobile(Player.Serial)
            Misc.Pause(1000)

    log("All approaches failed — mount stays unsolved.", colors['red'])


def main():
    log("=== Mount test starting ===")
    log("Mounted: %s" % (Player.Mount is not None))

    if not dismount():
        return

    beetle = find_beetle()
    if beetle is None:
        return

    try_mount(beetle.Serial)

    dismount()
    log("=== Done ===")


main()
