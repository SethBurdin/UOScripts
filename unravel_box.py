# unravel_box.py
# Unravels items from a specified container, only attempting items that match the player's Imbuing skill level.
# Skips containers, gold, and items the player cannot unravel due to skill restrictions.

if False:
    from razorenhanced_stubs import *

# ─── Config ────────────────────────────────────────────────────────────────
DEBUG = True
UNRAVEL_ITEM_BTN    = 10010
IMBUING_GUMP_ID     = 0x5b394d53
CONFIRM_GUMP_ID     = 0x7f3111a7
CONFIRM_BTN         = 1
PHRASE_SKILL_LOW    = "not high enough to magically unravel"
PHRASE_NOT_MAGICAL  = "cannot magically unravel"
PAUSE_BETWEEN_ITEMS = 300
PAUSE_AFTER_UNRAVEL = 200
PAUSE_OPEN_CONTAINER = 1200
SKIP_IDS = {0x0EED}  # gold coins

# Item rarity label → minimum Imbuing skill required to attempt unravel.
# Regular magic items yield Magical Residue (no skill gate on OSI).
# Artifacts yield Enchanted Essence (≥45) or Relic Fragment (≥90).
UNRAVEL_PROP_SKILL = {
    "Lesser Magic Item":  0,     # Magical Residue — no skill gate
    "Minor Magic Item":   50,     # Magical Residue
    "Magic Item":         60,     # Magical Residue
    "Greater Magic Item": 70,     # Magical Residue
    "Major Magic Item":   80,     # Magical Residue
    "Lesser Artifact":   85.0,   # Enchanted Essence — requires 45 Imbuing
    "Artifact":          90.0,   # Relic Fragment — requires 90 Imbuing
    "Greater Artifact":  90.0,   # Relic Fragment
}


def log(msg, color=68):
    Misc.SendMessage("[unravel_box] " + msg, color)

def dlog(msg):
    if DEBUG:
        Misc.SendMessage("[unravel_box:dbg] " + msg, 0x3F)


def get_item_unravel_skill(item):
    Items.SingleClick(item)
    Misc.Pause(500)
    Items.WaitForProps(item, 2000)
    props = Items.GetPropStringList(item.Serial)
    if not props:
        dlog("  no props returned for %s (0x%04X)" % (item.Name, item.ItemID))
        return None
    dlog("  props for %s: %s" % (item.Name, " | ".join(str(p) for p in props)))
    for line in props:
        for key, skill in UNRAVEL_PROP_SKILL.items():
            if key.lower() in line.lower():
                dlog("  -> matched '%s' (req %.1f)" % (key, skill))
                return skill
    dlog("  -> no tier matched")
    return None


def filter_items_by_skill(items, skill):
    eligible = []
    for item in items:
        req = get_item_unravel_skill(item)
        if req is None or skill >= req:
            eligible.append(item)
    return eligible


def prompt_source_box():
    log("Target the container to unravel from.", 0x53)
    serial = Target.PromptTarget("Target the container to unravel from:")
    if not serial or serial == 0:
        log("No container selected.", 0x25)
        return None
    box = Items.FindBySerial(serial)
    if box is None:
        log("Could not find targeted item.", 0x25)
        return None
    log("Source box: %s (0x%X)" % (box.Name, box.Serial))
    return box


def unravel_item(item):
    PHRASE_BLESSED = "You cannot unravel the magic of a blessed item."
    Journal.Clear()
    dlog("UseSkill Imbuing...")
    Player.UseSkill('Imbuing')
    if not Gumps.WaitForGump(IMBUING_GUMP_ID, 5000):
        log("Imbuing gump timed out – skill on cooldown?", 0x25)
        return False
    dlog("Imbuing gump open. Sending Unravel Item btn (%d)..." % UNRAVEL_ITEM_BTN)
    Gumps.SendAction(IMBUING_GUMP_ID, UNRAVEL_ITEM_BTN)
    dlog("Waiting for target cursor...")
    Target.WaitForTarget(5000, False)
    dlog("Targeting item serial 0x%X..." % item.Serial)
    Target.TargetExecute(item.Serial)
    Misc.Pause(800)
    dlog("Checking journal for server response...")
    if DEBUG:
        for entry in Journal.GetTextByType("Regular"):
            dlog("  journal: %s" % entry)
    if Journal.Search(PHRASE_BLESSED):
        log("  BLESSED ITEM: %s (skipped)" % item.Name, 0x25)
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return True
    if Journal.Search(PHRASE_SKILL_LOW):
        log("  SKILL TOO LOW: %s (skipped)" % item.Name, 0x25)
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return True
    if Journal.Search(PHRASE_NOT_MAGICAL):
        dlog("  not magical — skipping")
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return True
    dlog("  no journal rejection — waiting for confirm gump...")
    if Gumps.WaitForGump(CONFIRM_GUMP_ID, 2000):
        dlog("  confirm gump present — sending confirm")
        Journal.Clear()
        Gumps.SendAction(CONFIRM_GUMP_ID, CONFIRM_BTN)
        Misc.Pause(800)
        if DEBUG:
            for entry in Journal.GetTextByType("Regular"):
                dlog("  post-confirm journal: %s" % entry)
        if Journal.Search(PHRASE_SKILL_LOW):
            log("  SKILL TOO LOW (post-confirm): %s (skipped)" % item.Name, 0x25)
            if Gumps.HasGump():
                Gumps.CloseGump()
                Misc.Pause(400)
            return True
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        dlog("  unravelled OK")
        return True
    log("  NO RESPONSE MATCHED for %s (skipped)" % item.Name, 0x25)
    dlog("  (check journal dump above to see exact server message)")
    if Gumps.HasGump():
        Gumps.CloseGump()
        Misc.Pause(400)
    return True


def main():
    box = prompt_source_box()
    if box is None:
        return

    Items.UseItem(box)
    Items.WaitForContents(box, 3000)
    Misc.Pause(PAUSE_OPEN_CONTAINER)
    contents = list(box.Contains) if box.Contains else []
    if not contents:
        log("Container is empty.", 0x25)
        return
    skill = Player.GetSkillValue("Imbuing")
    log("Your Imbuing skill: %s" % skill)
    candidates = [item for item in contents if not item.IsContainer and item.ItemID not in SKIP_IDS]
    targets = filter_items_by_skill(candidates, skill)
    log("Found %i eligible item(s) to unravel (%i skipped)." % (len(targets), len(contents) - len(targets)))
    success = 0
    for i, item in enumerate(targets):
        log("  [%i/%i] %s (0x%04X)" % (i + 1, len(targets), item.Name, item.ItemID))
        Items.Move(item, Player.Backpack, item.Amount)
        Misc.Pause(1200)
        if unravel_item(item):
            success += 1
        Misc.Pause(PAUSE_BETWEEN_ITEMS)
    log("Done – attempted %i item(s)." % success)


main()
