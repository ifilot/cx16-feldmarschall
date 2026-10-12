"""The 16-colour 'field campaign' palette shared by every asset.

VERA stores 12-bit colours, so every channel is a single hex digit. Index 0
is transparent on both layers and for sprites; where nothing opaque is left,
VERA shows colour 0 itself. Layer 0 therefore paints the neutral stone of the
frame and panel with index 0, while pieces and text (layer 1) can't use it.
That is why the drawable ink lives at index 1.

The UI uses classic palette row 0, armies use rows 1 and 2, text uses rows
3-5, and the board uses row 6. Field choices never recolor the UI.
"""

STONE = 0          # frame and panel (layer 0 only: index 0 is transparent)
INK = 1            # outlines, grid lines, portrait background
CREAM = 2          # faces, plumes, bevel light
SAND = 3           # light sand, skin shade
KHAKI = 4          # dark sand
BROWN = 5          # dirt, shore, stone shadow
GOLD = 6           # selection, move dots, crest
OLIVE = 7          # grass, canopy highlight
FOREST = 8         # tree canopy
DEEP = 9           # canopy shadow, forest floor
WATER_LIGHT = 10   # shallows, ripples
LIGHT = 11         # light grey plates and tray
RED = 12           # red army
DEEP_RED = 13
BLUE = 14          # blue army (also via palette row 1), deep water
DEEP_BLUE = 15

RGB12 = [
    0x887,  # 0 stone
    0x111,  # 1 ink
    0xEDB,  # 2 cream
    0xCA7,  # 3 sand
    0x985,  # 4 khaki
    0x653,  # 5 brown
    0xEB4,  # 6 gold
    0x784,  # 7 olive
    0x463,  # 8 forest
    0x231,  # 9 deep green
    0x8BD,  # 10 water light
    0xBBA,  # 11 light grey
    0xB32,  # 12 red
    0x611,  # 13 deep red
    0x36B,  # 14 blue
    0x124,  # 15 deep blue
]

# palette row used to draw red-army artwork in blue
BLUE_ROW = 2


def rgb(index, colors=RGB12):
    """Return the 24-bit colour of a palette index."""
    value = colors[index]
    return (((value >> 8) & 15) * 17, ((value >> 4) & 15) * 17, (value & 15) * 17)


def pil_palette(colors=RGB12):
    """Palette list for PIL 'P' images (unused entries are black)."""
    flat = []
    for i in range(len(colors)):
        flat.extend(rgb(i, colors))
    return flat + [0] * (768 - len(flat))


def row_colors(row, field=None, pieces=None):
    """Classic UI row 0, armies 1-2, text 3-5, selected field row 6."""
    field = RGB12 if field is None else field
    pieces = RGB12 if pieces is None else pieces
    colors = (pieces if row in (1, 2) else field if row == 6 else RGB12).copy()
    if row == 2:
        colors[RED], colors[DEEP_RED] = pieces[BLUE], pieces[DEEP_BLUE]
    elif row == 3:
        colors[INK] = RGB12[BROWN]
    elif row == 4:
        colors[INK] = pieces[DEEP_RED]
    elif row == 5:
        colors[INK] = pieces[DEEP_BLUE]
    elif row == 8:
        colors[INK] = RGB12[DEEP_RED]
    return colors


def vera_palette(field=None, pieces=None):
    """All 256 VERA palette entries (512 bytes, little-endian GGGGBBBB/----RRRR)."""
    out = bytearray()
    for row in range(16):
        for value in row_colors(row, field, pieces):
            out += bytes([value & 0xFF, value >> 8])
    return bytes(out)
