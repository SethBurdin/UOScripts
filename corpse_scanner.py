'''
Corpse Scanner - Auto Mode
--------------------------
Runs continuously as a background script.
Whenever a new corpse appears within range it is automatically opened,
each item's properties are fetched, and a floating label is shown above
every item directly inside the corpse container.

Color coding:
  Green  (88)  = great  -- slayer, Vanquishing/Power, hit spells, Indestructible
  Yellow (53)  = good   -- resists, bonuses, spell channeling, accuracy
  Red    (33)  = bad    -- cursed, brittle, antique, no drop
  White  (0)   = unremarkable (label still shown so you see the item name)

Configuration is at the top of the file.
'''

try:
    from razorenhanced_stubs import *
except:
    pass

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Range in tiles to watch for new corpses
SCAN_RANGE = 3

# ms to wait between full scan passes
SCAN_INTERVAL_MS = 500

# ms to wait for a corpse's contents to load after opening it
CONTENTS_TIMEOUT_MS = 2500

# ms to wait for a single item's properties to load
PROP_TIMEOUT_MS = 2000

# ms pause between labelling each item (keeps floating text readable)
LABEL_PAUSE_MS = 100

# Hues for each tier
HUE_GREAT  = 88
HUE_GOOD   = 53
HUE_NORMAL = 0
HUE_BAD    = 33

# Keywords -> bright green
GREAT_KEYWORDS = [
    'vanquishing', 'power', 'force', 'ruin',
    'repond', 'silver', 'undead', 'daemon', 'demon', 'exorcism',
    'dragon', 'reptile', 'reptilian', 'arachnid', 'scorpion', 'spider', 'terathan',
    'fey', 'elemental', 'air', 'vacuum', 'blood', 'earth',
    'fire', 'flame', 'poison', 'snow', 'summer', 'water',
    'goblin', 'orc', 'ogre', 'troll',
    'indestructible', 'invulnerability',
    'hit lightning', 'hit fireball', 'hit magic arrow', 'hit harm',
    'hit area', 'hit dispel',
    'supremely accurate', 'exceedingly accurate',
]

# Keywords -> yellow
GOOD_KEYWORDS = [
    'eminently accurate', 'surpassingly accurate',
    'exceptional',
    'fortified', 'substantial', 'massive',
    'slayer', 'bane',
    'mage weapon', 'spell channeling',
    'lower reagent cost', 'lower mana cost', 'faster casting',
    'faster cast recovery', 'mana regeneration', 'hit point regeneration',
    'stamina regeneration', 'luck',
    'strength bonus', 'dexterity bonus', 'intelligence bonus',
    'night sight', 'balanced', 'velocity',
    'crushing blow', 'armor ignore', 'whirlwind', 'bleed attack',
    'mortal strike', 'paralyzing blow',
    'defense chance', 'hit chance', 'swing speed increase',
    'damage increase', 'spell damage increase',
    'physical resist', 'fire resist', 'cold resist', 'poison resist', 'energy resist',
    'enhance potions', 'reflect physical damage',
    'self repair', 'durability',
]

# Keywords -> red
BAD_KEYWORDS = [
    'cursed', 'antique', 'no drop', 'brittle',
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _classify(props):
    '''Return (hue, short_summary) for a list of property strings.'''
    if not props:
        return HUE_NORMAL, ''

    joined = '\n'.join(props).lower()
    hits = []
    hue = HUE_NORMAL

    for kw in BAD_KEYWORDS:
        if kw in joined:
            hits.append(kw.title())
            hue = HUE_BAD

    for kw in GREAT_KEYWORDS:
        if kw in joined:
            label = kw.title()
            if label not in hits:
                hits.append(label)
            if hue != HUE_BAD:
                hue = HUE_GREAT

    for kw in GOOD_KEYWORDS:
        if kw in joined:
            label = kw.title()
            if label not in hits:
                hits.append(label)
                if hue == HUE_NORMAL:
                    hue = HUE_GOOD

    summary = ' | '.join(hits[:3])
    if len(hits) > 3:
        summary += ' (+%i)' % (len(hits) - 3)
    return hue, summary


def _item_display_name(item, props):
    if props and props[0].strip():
        return props[0].strip()
    return item.Name or ('0x%04X' % item.ItemID)


def _scan_corpse(corpse):
    '''Open a corpse, fetch properties for every item, float labels.'''
    Items.UseItem(corpse.Serial)
    Items.WaitForContents(corpse.Serial, CONTENTS_TIMEOUT_MS)
    Misc.Pause(200)

    contents = corpse.Contains
    if not contents or len(contents) == 0:
        return

    Misc.SendMessage('[SCAN] Corpse 0x%X — %i item(s)' % (corpse.Serial, len(contents)), 68)

    for item in contents:
        Items.WaitForProps(item.Serial, PROP_TIMEOUT_MS)
        props = Items.GetPropStringList(item.Serial)

        hue, summary = _classify(props)
        name = _item_display_name(item, props)

        if item.Amount > 1:
            label = '%s x%i' % (name, item.Amount)
        else:
            label = name

        if summary:
            label = '%s: %s' % (label, summary)

        Items.Message(item.Serial, hue, label)

        # Only print noteworthy items to journal to keep it clean
        if hue in (HUE_GREAT, HUE_GOOD, HUE_BAD):
            Misc.SendMessage('[SCAN]  %s' % label, hue)

        if LABEL_PAUSE_MS > 0:
            Misc.Pause(LABEL_PAUSE_MS)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

Misc.SendMessage('[SCAN] Corpse scanner started (range: %i tiles). Stop the script to exit.' % SCAN_RANGE, 88)

scannedSerials = set()

while True:
    corpseFilter = Items.Filter()
    corpseFilter.Enabled = True
    corpseFilter.IsCorpse = 1
    corpseFilter.RangeMin = 0
    corpseFilter.RangeMax = SCAN_RANGE

    for corpse in Items.ApplyFilter(corpseFilter):
        if corpse.Serial not in scannedSerials:
            scannedSerials.add(corpse.Serial)
            try:
                _scan_corpse(corpse)
            except:
                pass  # don't let a single bad corpse kill the loop

    Misc.Pause(SCAN_INTERVAL_MS)

