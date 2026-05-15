import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utilities.gumps import GumpSelection
from glossary.items.tools import tools
from utilities.items import FindItem

tailoringTools = [ tools[ 'sewing kit' ] ]

def FindTailoringTool( container ):
    '''
    Searches for a blacksmithing tool in the specified container
    '''

    # Find the tool to craft with
    for tool in tailoringTools:
        tool = FindItem( tool.itemID, container )
        if tool != None:
            return tool


class TailoringCraftable:
    name = None
    itemID = None
    retainsMark = None
    retainsColor = None
    minSkill = None
    resourcesNeeded = None
    gumpPath = None

    def __init__ ( self, name, itemID, retainsMark, retainsColor, minSkill, resourcesNeeded, gumpPath ):
        self.name = name
        self.itemID = itemID
        self.retainsMark = retainsMark
        self.retainsColor = retainsColor
        self.minSkill = minSkill
        self.resourcesNeeded = resourcesNeeded
        self.gumpPath = gumpPath


tailoringCraftables = {
    ### Hats: Gump Button 8 ###
    'skullcap': TailoringCraftable(
        name = 'skullcap',
        itemID = 0x1544,
        retainsMark = True,
        retainsColor = True,
        minSkill = 0.0,
        resourcesNeeded = { 'cloth': 2 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 2 ) )
    ),
    'bandana': TailoringCraftable(
        name = 'bandana',
        itemID = 0x1540,
        retainsMark = True,
        retainsColor = True,
        minSkill = 0.0,
        resourcesNeeded = { 'cloth': 2 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 9 ) )
    ),
    'floppy hat': TailoringCraftable(
        name = 'floppy hat',
        itemID = 0x1713,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'cloth': 11 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 16 ) )
    ),
    'cap': TailoringCraftable(
        name = 'cap',
        itemID = 0x1715,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'cloth': 11 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 23 ) )
    ),
    'wide-brim hat': TailoringCraftable(
        name = 'wide-brim hat',
        itemID = 0x1714,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'cloth': 12 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 30 ) )
    ),
    'straw hat': TailoringCraftable(
        name = 'straw hat',
        itemID = 0x1717,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'cloth': 10 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 37 ) )
    ),
    'tall straw hat': TailoringCraftable(
        name = 'tall straw hat',
        itemID = 0x1716,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.7,
        resourcesNeeded = { 'cloth': 13 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 44 ) )
    ),
    'wizard''s hat': TailoringCraftable(
        name = 'wizard''s hat',
        itemID = 0x1718,
        retainsMark = True,
        retainsColor = True,
        minSkill = 7.2,
        resourcesNeeded = { 'cloth': 15 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 51 ) )
    ),
    'bonnet': TailoringCraftable(
        name = 'bonnet',
        itemID = 0x1719,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'cloth': 11 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 58 ) )
    ),
    'feathered hat': TailoringCraftable(
        name = 'feathered hat',
        itemID = 0x171A,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'cloth': 12 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 65 ) )
    ),
    'tricorne hat': TailoringCraftable(
        name = 'tricorne hat',
        itemID = 0x171B,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'cloth': 12 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 72 ) )
    ),
    'jester hat': TailoringCraftable(
        name = 'jester hat',
        itemID = 0x171C,
        retainsMark = True,
        retainsColor = True,
        minSkill = 7.2,
        resourcesNeeded = { 'cloth': 15 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 79 ) )
    ),


    ### Shirts: Gump Button 8 ###
    'doublet': TailoringCraftable(
        name = 'doublet',
        itemID = 0x1F7B,
        retainsMark = True,
        retainsColor = True,
        minSkill = 0.0,
        resourcesNeeded = { 'cloth': 8 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 2 ) )
    ),
    'shirt': TailoringCraftable(
        name = 'shirt',
        itemID = 0x1517,
        retainsMark = True,
        retainsColor = True,
        minSkill = 20.7,
        resourcesNeeded = { 'cloth': 8 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 9 ) )
    ),
    'fancy shirt': TailoringCraftable(
        name = 'fancy shirt',
        itemID = 0x1EFD,
        retainsMark = True,
        retainsColor = True,
        minSkill = 24.8,
        resourcesNeeded = { 'cloth': 8 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 16 ) )
    ),
    'tunic': TailoringCraftable(
        name = 'tunic',
        itemID = 0x1FA1,
        retainsMark = True,
        retainsColor = True,
        minSkill = 0.0,
        resourcesNeeded = { 'cloth': 12 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 23 ) )
    ),
    'surcoat': TailoringCraftable(
        name = 'surcoat',
        itemID = 0x1FFD,
        retainsMark = True,
        retainsColor = True,
        minSkill = 8.2,
        resourcesNeeded = { 'cloth': 14 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 30 ) )
    ),
    'plain dress': TailoringCraftable(
        name = 'plain dress',
        itemID = 0x1F01,
        retainsMark = True,
        retainsColor = True,
        minSkill = 12.4,
        resourcesNeeded = { 'cloth': 10 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 37 ) )
    ),
    'fancy dress': TailoringCraftable(
        name = 'fancy dress',
        itemID = 0x1F00,
        retainsMark = True,
        retainsColor = True,
        minSkill = 33.1,
        resourcesNeeded = { 'cloth': 12 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 44 ) )
    ),
    'cloak': TailoringCraftable(
        name = 'cloak',
        itemID = 0x1515,
        retainsMark = True,
        retainsColor = True,
        minSkill = 41.4,
        resourcesNeeded = { 'cloth': 14 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 51 ) )
    ),
    'robe': TailoringCraftable(
        name = 'robe',
        itemID = 0x1F03,
        retainsMark = True,
        retainsColor = True,
        minSkill = 53.9,
        resourcesNeeded = { 'cloth': 16 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 58 ) )
    ),
    'jester suit': TailoringCraftable(
        name = 'jester suit',
        itemID = 0x1F9F,
        retainsMark = True,
        retainsColor = True,
        minSkill = 8.2,
        resourcesNeeded = { 'cloth': 24 },
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 65 ) )
    ),


    ### Pants: Gump Button 15 ###
    'short pants': TailoringCraftable(
        name = 'short pants',
        itemID = 0x152E,
        retainsMark = True,
        retainsColor = True,
        minSkill = 24.8,
        resourcesNeeded = { 'cloth': 6 },
        gumpPath = ( GumpSelection( 2653346093, 15 ), GumpSelection( 2653346093, 2 ) )
    ),
    'long pants': TailoringCraftable(
        name = 'long pants',
        itemID = 0x1539,
        retainsMark = True,
        retainsColor = True,
        minSkill = 24.8,
        resourcesNeeded = { 'cloth': 8 },
        gumpPath = ( GumpSelection( 2653346093, 15 ), GumpSelection( 2653346093, 9 ) )
    ),
    'kilt': TailoringCraftable(
        name = 'kilt',
        itemID = 0x1537,
        retainsMark = True,
        retainsColor = True,
        minSkill = 20.7,
        resourcesNeeded = { 'cloth': 8 },
        gumpPath = ( GumpSelection( 2653346093, 15 ), GumpSelection( 2653346093, 16 ) )
    ),
    'skirt': TailoringCraftable(
        name = 'skirt',
        itemID = 0x1516,
        retainsMark = True,
        retainsColor = True,
        minSkill = 29.0,
        resourcesNeeded = { 'cloth': 10 },
        gumpPath = ( GumpSelection( 2653346093, 15 ), GumpSelection( 2653346093, 23 ) )
    ),


    ### Miscellaneous: Gump Button 22 ###
    'body sash': TailoringCraftable(
        name = 'body sash',
        itemID = 0x1541,
        retainsMark = True,
        retainsColor = True,
        minSkill = 4.1,
        resourcesNeeded = { 'cloth': 4 },
        gumpPath = ( GumpSelection( 2653346093, 22 ), GumpSelection( 2653346093, 2 ) )
    ),
    'half apron': TailoringCraftable(
        name = 'half apron',
        itemID = 0x153B,
        retainsMark = True,
        retainsColor = True,
        minSkill = 20.7,
        resourcesNeeded = { 'cloth': 6 },
        gumpPath = ( GumpSelection( 2653346093, 22 ), GumpSelection( 2653346093, 9 ) )
    ),
    'full apron': TailoringCraftable(
        name = 'full apron',
        itemID = 0x153D,
        retainsMark = True,
        retainsColor = True,
        minSkill = 29.0,
        resourcesNeeded = { 'cloth': 10 },
        gumpPath = ( GumpSelection( 2653346093, 22 ), GumpSelection( 2653346093, 16 ) )
    ),
    'oil cloth': TailoringCraftable(
        name = 'oil cloth',
        itemID = 0x175D,
        retainsMark = True,
        retainsColor = True,
        minSkill = 74.6,
        resourcesNeeded = { 'cloth': 1 },
        gumpPath = ( GumpSelection( 2653346093, 22 ), GumpSelection( 2653346093, 23 ) )
    ),


    ### Footwear: Gump Button 29 ###
    'sandals': TailoringCraftable(
        name = 'sandals',
        itemID = 0x170D,
        retainsMark = True,
        retainsColor = True,
        minSkill = 12.4,
        resourcesNeeded = { 'leather': 4 },
        gumpPath = ( GumpSelection( 2653346093, 29 ), GumpSelection( 2653346093, 2 ) )
    ),
    'shoes': TailoringCraftable(
        name = 'shoes',
        itemID = 0x170F,
        retainsMark = True,
        retainsColor = True,
        minSkill = 16.5,
        resourcesNeeded = { 'leather': 6 },
        gumpPath = ( GumpSelection( 2653346093, 29 ), GumpSelection( 2653346093, 9 ) )
    ),
    'boots': TailoringCraftable(
        name = 'boots',
        itemID = 0x170B,
        retainsMark = True,
        retainsColor = True,
        minSkill = 33.1,
        resourcesNeeded = { 'leather': 8 },
        gumpPath = ( GumpSelection( 2653346093, 29 ), GumpSelection( 2653346093, 16 ) )
    ),
    'thigh boots': TailoringCraftable(
        name = 'thigh boots',
        itemID = 0x1711,
        retainsMark = True,
        retainsColor = True,
        minSkill = 41.4,
        resourcesNeeded = { 'leather': 10 },
        gumpPath = ( GumpSelection( 2653346093, 29 ), GumpSelection( 2653346093, 23 ) )
    ),


    ### Leather Armor: Gump Button 36 ###
    'leather gorget': TailoringCraftable(
        name = 'leather gorget',
        itemID = 0x13C7,
        retainsMark = True,
        retainsColor = True,
        minSkill = 53.9,
        resourcesNeeded = { 'leather': 4 },
        gumpPath = ( GumpSelection( 2653346093, 36 ), GumpSelection( 2653346093, 2 ) )
    ),
    'leather cap': TailoringCraftable(
        name = 'leather cap',
        itemID = 0x1DB9,
        retainsMark = True,
        retainsColor = True,
        minSkill = 6.2,
        resourcesNeeded = { 'leather': 2 },
        gumpPath = ( GumpSelection( 2653346093, 36 ), GumpSelection( 2653346093, 9 ) )
    ),
    'leather gloves': TailoringCraftable(
        name = 'leather gloves',
        itemID = 0x13C6,
        retainsMark = True,
        retainsColor = True,
        minSkill = 51.8,
        resourcesNeeded = { 'leather': 3 },
        gumpPath = ( GumpSelection( 2653346093, 36 ), GumpSelection( 2653346093, 16 ) )
    ),
    'leather sleeves': TailoringCraftable(
        name = 'leather sleeves',
        itemID = 0x13CD,
        retainsMark = True,
        retainsColor = True,
        minSkill = 53.9,
        resourcesNeeded = { 'leather': 8 },
        gumpPath = ( GumpSelection( 2653346093, 36 ), GumpSelection( 2653346093, 23 ) )
    ),
    'leather leggings': TailoringCraftable(
        name = 'leather leggings',
        itemID = 0x13CB,
        retainsMark = True,
        retainsColor = True,
        minSkill = 66.3,
        resourcesNeeded = { 'leather': 10 },
        gumpPath = ( GumpSelection( 2653346093, 36 ), GumpSelection( 2653346093, 30 ) )
    ),
    'leather tunic': TailoringCraftable(
        name = 'leather tunic',
        itemID = 0x13CC,
        retainsMark = True,
        retainsColor = True,
        minSkill = 70.5,
        resourcesNeeded = { 'leather': 12 },
        gumpPath = ( GumpSelection( 2653346093, 36 ), GumpSelection( 2653346093, 37 ) )
    ),


    ### Studded Armor: Gump Button 43 ###
    'studded gorget': TailoringCraftable(
        name = 'studded gorget',
        itemID = 0x13D6,
        retainsMark = True,
        retainsColor = True,
        minSkill = 78.8,
        resourcesNeeded = { 'leather': 6 },
        gumpPath = ( GumpSelection( 2653346093, 43 ), GumpSelection( 2653346093, 2 ) )
    ),
    'studded cap': TailoringCraftable(
        name = 'studded cap',
        itemID = 0x1DB9,
        retainsMark = True,
        retainsColor = True,
        minSkill = 80.9,
        resourcesNeeded = { 'leather': 4 },
        gumpPath = ( GumpSelection( 2653346093, 43 ), GumpSelection( 2653346093, 9 ) )
    ),
    'studded gloves': TailoringCraftable(
        name = 'studded gloves',
        itemID = 0x13D5,
        retainsMark = True,
        retainsColor = True,
        minSkill = 82.9,
        resourcesNeeded = { 'leather': 8 },
        gumpPath = ( GumpSelection( 2653346093, 43 ), GumpSelection( 2653346093, 16 ) )
    ),
    'studded sleeves': TailoringCraftable(
        name = 'studded sleeves',
        itemID = 0x13DC,
        retainsMark = True,
        retainsColor = True,
        minSkill = 87.1,
        resourcesNeeded = { 'leather': 10 },
        gumpPath = ( GumpSelection( 2653346093, 43 ), GumpSelection( 2653346093, 23 ) )
    ),
    'studded leggings': TailoringCraftable(
        name = 'studded leggings',
        itemID = 0x13DA,
        retainsMark = True,
        retainsColor = True,
        minSkill = 91.2,
        resourcesNeeded = { 'leather': 12 },
        gumpPath = ( GumpSelection( 2653346093, 43 ), GumpSelection( 2653346093, 30 ) )
    ),
    'studded tunic': TailoringCraftable(
        name = 'studded tunic',
        itemID = 0x13DB,
        retainsMark = True,
        retainsColor = True,
        minSkill = 94.0,
        resourcesNeeded = { 'leather': 14 },
        gumpPath = ( GumpSelection( 2653346093, 43 ), GumpSelection( 2653346093, 37 ) )
    ),


    ### Female Armor: Gump Button 50 ###
    'leather shorts': TailoringCraftable(
        name = 'leather shorts',
        itemID = 0x1C00,
        retainsMark = True,
        retainsColor = True,
        minSkill = 62.2,
        resourcesNeeded = { 'leather': 8 },
        gumpPath = ( GumpSelection( 2653346093, 50 ), GumpSelection( 2653346093, 2 ) )
    ),
    'leather skirt': TailoringCraftable(
        name = 'leather skirt',
        itemID = 0x1C08,
        retainsMark = True,
        retainsColor = True,
        minSkill = 58.0,
        resourcesNeeded = { 'leather': 6 },
        gumpPath = ( GumpSelection( 2653346093, 50 ), GumpSelection( 2653346093, 9 ) )
    ),
    'leather bustier': TailoringCraftable(
        name = 'leather bustier',
        itemID = 0x1C0A,
        retainsMark = True,
        retainsColor = True,
        minSkill = 58.0,
        resourcesNeeded = { 'leather': 6 },
        gumpPath = ( GumpSelection( 2653346093, 50 ), GumpSelection( 2653346093, 16 ) )
    ),
    'studded bustier': TailoringCraftable(
        name = 'studded bustier',
        itemID = 0x1C0C,
        retainsMark = True,
        retainsColor = True,
        minSkill = 82.9,
        resourcesNeeded = { 'leather': 8 },
        gumpPath = ( GumpSelection( 2653346093, 50 ), GumpSelection( 2653346093, 23 ) )
    ),
    'female leather armor': TailoringCraftable(
        name = 'female leather armor',
        itemID = 0x1C06,
        retainsMark = True,
        retainsColor = True,
        minSkill = 62.2,
        resourcesNeeded = { 'leather': 8 },
        gumpPath = ( GumpSelection( 2653346093, 50 ), GumpSelection( 2653346093, 30 ) )
    ),
    'studded armor': TailoringCraftable(
        name = 'studded armor',
        itemID = 0x1C02,
        retainsMark = True,
        retainsColor = True,
        minSkill = 87.1,
        resourcesNeeded = { 'leather': 10 },
        gumpPath = ( GumpSelection( 2653346093, 50 ), GumpSelection( 2653346093, 37 ) )
    ),
    'studded hiro sode': TailoringCraftable(
        name = 'studded hiro sode',
        itemID = 0x277F,
        retainsMark = True,
        retainsColor = True,
        minSkill = 107.5,
        resourcesNeeded = { 'leather': 8 },
        gumpPath = ( GumpSelection( 2653346093, 50 ), GumpSelection( 2653346093, 51 ) )
    ),


    ### Bone Armor: Gump Button 57 ###
    'bone helmet': TailoringCraftable(
        name = 'bone helmet',
        itemID = 0x1451,
        retainsMark = True,
        retainsColor = True,
        minSkill = 85.0,
        resourcesNeeded = { 'leather': 4, 'bones': 2 },
        gumpPath = ( GumpSelection( 2653346093, 57 ), GumpSelection( 2653346093, 2 ) )
    ),
    'bone gloves': TailoringCraftable(
        name = 'bone gloves',
        itemID = 0x1450,
        retainsMark = True,
        retainsColor = True,
        minSkill = 89.0,
        resourcesNeeded = { 'leather': 6, 'bones': 2 },
        gumpPath = ( GumpSelection( 2653346093, 57 ), GumpSelection( 2653346093, 9 ) )
    ),
    'bone arms': TailoringCraftable(
        name = 'bone arms',
        itemID = 0x144E,
        retainsMark = True,
        retainsColor = True,
        minSkill = 92.0,
        resourcesNeeded = { 'leather': 8, 'bones': 4 },
        gumpPath = ( GumpSelection( 2653346093, 57 ), GumpSelection( 2653346093, 16 ) )
    ),
    'bone leggings': TailoringCraftable(
        name = 'bone leggings',
        itemID = 0x1452,
        retainsMark = True,
        retainsColor = True,
        minSkill = 95.0,
        resourcesNeeded = { 'leather': 10, 'bones': 6 },
        gumpPath = ( GumpSelection( 2653346093, 57 ), GumpSelection( 2653346093, 23 ) )
    ),
    'bone armor': TailoringCraftable(
        name = 'bone armor',
        itemID = 0x144F,
        retainsMark = True,
        retainsColor = True,
        minSkill = 96.0,
        resourcesNeeded = { 'leather': 12, 'bones': 10 },
        gumpPath = ( GumpSelection( 2653346093, 57 ), GumpSelection( 2653346093, 30 ) )
    ),
    'orc helm': TailoringCraftable(
        name = 'orc helm',
        itemID = 0x1F0B,
        retainsMark = True,
        retainsColor = True,
        minSkill = 90.0,
        resourcesNeeded = { 'leather': 6, 'bones': 4 },
        gumpPath = ( GumpSelection( 2653346093, 57 ), GumpSelection( 2653346093, 37 ) )
    ),


    ### Tribal Mask: Hats (button 8) → item button 128 ###
    'tribal mask': TailoringCraftable(
        name = 'tribal mask',
        itemID = 0x1549,
        retainsMark = True,
        retainsColor = True,
        minSkill = 100.0,
        resourcesNeeded = { 'cloth': 4 },  # TODO: verify — likely 'combined cloth' once item ID known
        gumpPath = ( GumpSelection( 2653346093, 8 ), GumpSelection( 2653346093, 128 ) )
    ),


    ### Materials category: Gump Button 1 ###
    'combined cloth': TailoringCraftable(
        name = 'combined cloth',
        itemID = 0x1767,
        retainsMark = False,
        retainsColor = False,
        minSkill = 0.0,
        resourcesNeeded = { 'cloth': 4 },  # TODO: verify how many cut cloth per combined cloth
        gumpPath = ( GumpSelection( 2653346093, 1 ), GumpSelection( 2653346093, 9 ) )
    ),
}
