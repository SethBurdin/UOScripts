# unravel_box_props.py
# Unravels every item in a source container. Items outside skill range are moved to a reject container.

if False:
    from razorenhanced_stubs import *

# ─── Config ────────────────────────────────────────────────────────────────
DEBUG = True
UNRAVEL_ITEM_BTN     = 10010
IMBUING_GUMP_ID      = 0x5b394d53
CONFIRM_GUMP_ID      = 0x7f3111a7
CONFIRM_BTN          = 1
PHRASE_SKILL_LOW     = "not high enough to magically unravel"
PHRASE_NOT_MAGICAL   = "cannot magically unravel"
PHRASE_BLESSED       = "You cannot unravel the magic of a blessed item."
PHRASE_NOT_BACKPACK  = "must be in your backpack"
PAUSE_BETWEEN_ITEMS  = 300
SKIP_IDS             = {0x0EED}  # gold coins


def log(msg, color=68):
    Misc.SendMessage("[unravel_box_props] " + msg, color)

def dlog(msg):
    if DEBUG:
        Misc.SendMessage("[unravel_box_props:dbg] " + msg, 0x3F)


def prompt_container(prompt_text):
    log(prompt_text, 0x53)
    serial = Target.PromptTarget(prompt_text)
    if not serial or serial == 0:
        log("No container selected.", 0x25)
        return None
    box = Items.FindBySerial(serial)
    if box is None:
        log("Could not find targeted item.", 0x25)
        return None
    log("Selected: %s (0x%X)" % (box.Name, box.Serial))
    return box


def move_to_backpack(item):
    bp = Player.Backpack
    retries = 0
    while retries < 5:
        Journal.Clear()
        Items.Move(item, bp, item.Amount)
        Misc.Pause(PAUSE_BETWEEN_ITEMS * 6)   # 1800 ms — same as beetle transfer
        if Journal.Search('You must wait to perform another action.'):
            dlog('  client busy, retrying...')
            Misc.Pause(1200)
            retries += 1
            continue
        found = Items.FindBySerial(item.Serial)
        if found is None:
            log("  %s vanished during move." % item.Name, 0x25)
            return False
        if found.Container == bp.Serial:
            return True
        dlog('  %s not in backpack yet (attempt %d) — retrying...' % (item.Name, retries + 1))
        retries += 1
    log("  FAILED to move %s to backpack after retries — skipping." % item.Name, 0x25)
    return False


def move_to_reject(item, reject_box):
    Items.Move(item, reject_box, item.Amount)
    Misc.Pause(1200)
    log("  Moved %s to reject box." % item.Name, 0x25)


# Returns: "ok", "skill_low", "not_magical", "blessed", "no_response"
def unravel_item(item):
    Journal.Clear()
    dlog("UseSkill Imbuing...")
    Player.UseSkill('Imbuing')
    if not Gumps.WaitForGump(IMBUING_GUMP_ID, 5000):
        log("Imbuing gump timed out – skill on cooldown?", 0x25)
        return "no_response"
    dlog("Sending Unravel Item btn (%d)..." % UNRAVEL_ITEM_BTN)
    Gumps.SendAction(IMBUING_GUMP_ID, UNRAVEL_ITEM_BTN)
    Target.WaitForTarget(5000, False)
    dlog("Targeting item 0x%X..." % item.Serial)
    Target.TargetExecute(item.Serial)
    Misc.Pause(800)
    if DEBUG:
        for entry in Journal.GetTextByType("Regular"):
            dlog("  journal: %s" % entry)
    if Journal.Search(PHRASE_NOT_BACKPACK):
        log("  NOT IN BACKPACK: %s (move failed server-side)" % item.Name, 0x25)
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return "not_in_backpack"
    if Journal.Search(PHRASE_BLESSED):
        log("  BLESSED: %s (skipped)" % item.Name, 0x25)
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return "blessed"
    if Journal.Search(PHRASE_SKILL_LOW):
        log("  SKILL TOO LOW: %s" % item.Name, 0x25)
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return "skill_low"
    if Journal.Search(PHRASE_NOT_MAGICAL):
        dlog("  not magical — skipping")
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        return "not_magical"
    dlog("  waiting for confirm gump...")
    if Gumps.WaitForGump(CONFIRM_GUMP_ID, 2000):
        dlog("  confirming...")
        Journal.Clear()
        Gumps.SendAction(CONFIRM_GUMP_ID, CONFIRM_BTN)
        Misc.Pause(800)
        if DEBUG:
            for entry in Journal.GetTextByType("Regular"):
                dlog("  post-confirm journal: %s" % entry)
        if Journal.Search(PHRASE_SKILL_LOW):
            log("  SKILL TOO LOW (post-confirm): %s" % item.Name, 0x25)
            if Gumps.HasGump():
                Gumps.CloseGump()
                Misc.Pause(400)
            return "skill_low"
        if Gumps.HasGump():
            Gumps.CloseGump()
            Misc.Pause(400)
        dlog("  unravelled OK")
        return "ok"
    log("  NO RESPONSE for %s" % item.Name, 0x25)
    if Gumps.HasGump():
        Gumps.CloseGump()
        Misc.Pause(400)
    return "no_response"


def main():
    source = prompt_container("Target the container to unravel from:")
    if source is None:
        return
    reject = prompt_container("Target the reject container (for items outside skill range):")
    if reject is None:
        return

    Items.UseItem(source)
    Items.WaitForContents(source, 3000)
    Misc.Pause(1200)

    contents = [i for i in (source.Contains or []) if not i.IsContainer and i.ItemID not in SKIP_IDS]
    if not contents:
        log("Container is empty.", 0x25)
        return

    log("Processing %d item(s)..." % len(contents))
    counts = {"ok": 0, "skill_low": 0, "not_magical": 0, "blessed": 0, "no_response": 0, "not_in_backpack": 0}

    for item in contents:
        if not move_to_backpack(item):
            continue
        result = unravel_item(item)
        counts[result] = counts.get(result, 0) + 1
        if result == "skill_low":
            move_to_reject(item, reject)
        elif result in ("not_magical", "blessed", "no_response", "not_in_backpack"):
            Items.Move(item, source, item.Amount)
            Misc.Pause(1200)
        Misc.Pause(PAUSE_BETWEEN_ITEMS)

    log("Done — unravelled: %d, skill_low (moved): %d, not magical: %d, blessed: %d" % (
        counts["ok"], counts["skill_low"], counts["not_magical"], counts["blessed"]))


main()
