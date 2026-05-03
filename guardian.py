# guardian.py
# Keeps your pet close and on guard. Heals or cures the pet when needed.
# Every CHECK_INTERVAL ms: checks pet health/poison, then checks distance.
# If pet is too far, calls it back and waits up to FOLLOW_MAX_CHECKS x FOLLOW_CHECK_INTERVAL ms.

if False:
    from razorenhanced_stubs import *

from Scripts.glossary.colors import colors

# ─── Config ───────────────────────────────────────────────────────────────────
PET_FOLLOW_RANGE     = 2      # tiles — beyond this the pet is recalled
HEALTH_THRESHOLD     = 0.90   # heal/cure when pet HP ratio drops below this
CHECK_INTERVAL       = 5000   # ms between main loop ticks
FOLLOW_CHECK_INTERVAL = 3000  # ms between checks after "all follow me"
FOLLOW_MAX_CHECKS    = 3      # max polls waiting for pet to arrive
PET_SCAN_RANGE       = 30     # tile radius to search for a friendly mobile


# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, color=68):
    Misc.SendMessage("[guardian] " + msg, color)


def find_pet():
    f = Mobiles.Filter()
    f.Enabled  = True
    f.Friend   = True
    f.RangeMin = 0
    f.RangeMax = PET_SCAN_RANGE
    candidates = Mobiles.ApplyFilter(f)
    nearest     = None
    nearestDist = 9999
    for mob in candidates:
        if mob.Serial == Player.Serial:
            continue
        d = Player.DistanceTo(mob)
        if d < nearestDist:
            nearestDist = d
            nearest = mob
    return nearest


def heal_pet(pet):
    log("HP low — healing %s" % pet.Name, colors['cyan'])
    Spells.CastMagery('Greater Heal')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def cure_pet(pet):
    log("Poisoned — curing %s" % pet.Name, colors['cyan'])
    Spells.CastMagery('Arch Cure')
    Target.WaitForTarget(3000, False)
    Target.TargetExecute(pet.Serial)
    Misc.Pause(1200)


def check_pet_health(pet):
    hp_ratio = float(pet.Hits) / max(pet.HitsMax, 1)
    if pet.Poisoned and hp_ratio < HEALTH_THRESHOLD:
        cure_pet(pet)
    elif hp_ratio < HEALTH_THRESHOLD:
        heal_pet(pet)


def recall_pet(pet):
    log("Pet too far (%d tiles) — all follow me" % Player.DistanceTo(pet), colors['yellow'])
    Player.ChatSay(690, 'all follow me')
    for i in range(FOLLOW_MAX_CHECKS):
        Misc.Pause(FOLLOW_CHECK_INTERVAL)
        fresh = Mobiles.FindBySerial(pet.Serial)
        if fresh is None:
            log("Pet disappeared during recall.", colors['red'])
            return False
        if Player.DistanceTo(fresh) <= PET_FOLLOW_RANGE:
            return True
        log("Waiting for pet... check %d/%d" % (i + 1, FOLLOW_MAX_CHECKS), colors['yellow'])
    log("Pet did not return after %d checks." % FOLLOW_MAX_CHECKS, colors['red'])
    return False


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    log("Guardian started.", colors['cyan'])
    while not Player.IsGhost:
        pet = find_pet()
        if pet is None:
            log("No pet found — waiting...", colors['yellow'])
            Misc.Pause(CHECK_INTERVAL)
            continue

        check_pet_health(pet)

        if Player.DistanceTo(pet) > PET_FOLLOW_RANGE:
            arrived = recall_pet(pet)
            if not arrived:
                Misc.Pause(CHECK_INTERVAL)
                continue

        Player.ChatSay(690, 'all guard me')
        Misc.Pause(CHECK_INTERVAL)


main()
