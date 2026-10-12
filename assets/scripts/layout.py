"""Screen geometry of the playing field (640x480), shared with the C code.

Both tile layers use 8x8 tiles at 4 bpp on a 128x64 map.

Layer 0 holds the static artwork: the terrain map, the stone frame with its
coordinates, the message bar and the side panel with its tray. Layer 1 holds
everything that changes: the grid, the pieces, move markers and text. The
grid lives on layer 1 so that the terrain tiles stay free of lines and every
piece can carry its own grid edge.

    +--------------------------+ +-----------+
    | frame, 12 px rails       | | title     |
    |   +------------------+   | | info      |
    |   | board 400 x 400  |   | | tray      |
    |   +------------------+   | |  5 x 8    |
    +--------------------------+ |  tokens   |
    | message bar              | |           |
    +--------------------------+ +-----------+
"""

# 10x10 board of 40-pixel squares (5x5 tiles per square)
BOARD_X, BOARD_Y = 16, 16
SQUARE = 40
SQUARE_TILES = SQUARE // 8
BOARD_SIZE = 10
BOARD_PX = SQUARE * BOARD_SIZE

# stone frame around the board, carrying the coordinates (inclusive bounds)
FRAME = 12
FRAME_X0, FRAME_Y0 = BOARD_X - FRAME, BOARD_Y - FRAME
FRAME_X1, FRAME_Y1 = BOARD_X + BOARD_PX + FRAME - 1, BOARD_Y + BOARD_PX + FRAME - 1

# the two 2x2 lakes (columns, rows counted from the top-left square)
LAKES = [(2, 4), (6, 4)]

# each army deploys on its four home rows; Red's are the bottom four
SETUP_ROWS = 4

# a dragged token's shadow falls this many pixels to the lower right
LIFT_SHADOW = 5

# message bar under the frame, with a recessed plate one token high
BAR_X0, BAR_Y0, BAR_X1, BAR_Y1 = FRAME_X0, FRAME_Y1 + 1, FRAME_X1, 475
BAR_PLATE = (8, 432, 423, 471)
BAR_ROWS = (55, 57)                  # two text rows
BAR_TEXT_COL = 2
BAR_PIECE_ROW = 54                   # 40x40 tokens, 5 tile rows
BAR_COL_RED, BAR_COL_VS, BAR_COL_BLUE = 37, 43, 46

# side panel; its plates span the full inner width, like the tray
PANEL_X0, PANEL_Y0, PANEL_X1, PANEL_Y1 = FRAME_X1 + 1, 4, 635, 475
INNER_X0, INNER_X1 = PANEL_X0 + 4, PANEL_X1 - 4
PLATES = {                           # (y0, y1), inclusive
    'title': (8, 47),
    'info': (56, 143),
}
INFO_ROWS = (9, 11, 13, 15)          # status, detail, "SELECTED", piece

# the tray: one compartment per piece of an army, 5 across and 8 down
TRAY_X, TRAY_Y = INNER_X0, 152
TRAY_COLS, TRAY_ROWS = 5, 8

# Pieces, strongest first (classic European numbering: 1 = Marshal).
# (file label in the Napoleonic sheet, rank glyph, name, count per army)
# The token numbers follow this order, which src/core/pieces.h repeats.
PIECES = [
    ('red1', '1', 'MARSHAL', 1),
    ('red2', '2', 'GENERAL', 1),
    ('red3', '3', 'COLONEL', 2),
    ('red4', '4', 'MAJOR', 3),
    ('red5', '5', 'CAPTAIN', 4),
    ('red6', '6', 'LIEUTENANT', 4),
    ('red7', '7', 'SERGEANT', 4),
    ('red8', '8', 'MINER', 5),
    ('red9', '9', 'SCOUT', 8),
    ('reds', 'S', 'SPY', 1),
    ('redb', 'B', 'BOMB', 6),
    ('redf', 'F', 'FLAG', 1),
]
TOKEN_HIDDEN = len(PIECES)           # token back, shown for unknown pieces
TOKENS = TOKEN_HIDDEN + 1

# The Napoleonic portrait sheet: two rows of six framed cards. Card interiors, inset
# by two pixels from the grey frames: column x0 values, one width, and per
# row (y0, height).
SHEET_ORDER = ['red1', 'red2', 'red3', 'red4', 'red5', 'red6',
               'red7', 'red8', 'red9', 'redb', 'redf', 'reds']
SHEET_CARD_X = (23, 262, 501, 739, 978, 1217)
SHEET_CARD_W = 208
SHEET_CARD_ROWS = ((203, 268), (561, 280))

# Layer-1 tile numbering
L1_EMPTY = 0                         # fully transparent
L1_GRID_CORNER = 1                   # top and left grid line
L1_GRID_TOP = 2
L1_GRID_LEFT = 3
L1_MARKER = 4                        # move target dot (centre tile of a square)
L1_PLATE = 5                         # 9 tiles of a floating plate: corners, edges, fill
L1_FONT = L1_PLATE + 9               # ASCII 32..127, one tile per glyph, transparent
L1_FONT_PLATE = L1_FONT + 96         # the same glyphs on the plate's light grey
L1_PIECES = L1_FONT_PLATE + 96       # 13 tokens x 25 tiles

# VRAM map. No loaded file may end exactly on a 64 KB boundary: cbm_k_load
# then returns end address $0000, which cannot be told from a failed load.
VRAM_L0_TILES = 0x00000              # up to 1024 tiles (32 KB)
VRAM_L0_MAP = 0x08000                # 128 x 64 entries
VRAM_L1_MAP = 0x0C000                # 128 x 64 entries, built at run time
VRAM_L1_TILES = 0x10000
VRAM_SPRITES = 0x18000               # SPRITES.BIN, all sprite images:
VRAM_TOKEN_SPRITES = VRAM_SPRITES    # 13 lifted tokens, 64x64 (2 KB) each
VRAM_CURSOR = 0x1E800                # 64x64 selection brackets
VRAM_POINTER = 0x1F000               # 16x16 mouse pointer
VRAM_PALETTE = 0x1FA00

# sprite numbers; at equal depth a lower number is drawn in front
SPRITE_POINTER, SPRITE_DRAG, SPRITE_CURSOR = 0, 1, 2
SPRITE_FALL = 3                      # a second token, for a defender that falls

# terrain tiles kept after vector quantisation of the board artwork
TERRAIN_TILES = 720
