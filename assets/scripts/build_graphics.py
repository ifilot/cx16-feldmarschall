"""Build every graphics resource of the playing field.

    python3 build_graphics.py OUTDIR [PREVIEWDIR]

writes to OUTDIR
    L0TILES.BIN   layer-0 tiles (terrain, frame, panel), 4 bpp
    L0MAP.BIN     layer-0 map, 128 x 60 entries
    L1TILES.BIN   layer-1 tiles (grid, marker, font, piece tokens), 4 bpp
    SPRITES.BIN   64x64 selection cursor, 4 bpp
    PALETTE.BIN   256 VERA palette entries
    gfx.h         geometry, VRAM map and tile numbers for the C code
    color_profiles.h  selectable field and army palettes for the C code
and, with PREVIEWDIR, PNG previews of layer 0 and of the token sheet.

All files are headerless: the game loads them with cbm_k_load into VRAM.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import layout as L
from bitmap_font import draw_text, glyph8
from palette import (BROWN, CREAM, DEEP_RED, GOLD, INK, LIGHT, STONE,
                     pil_palette, vera_palette)
from pieces import build_tokens
from terrain import generate
from splash import build_splash
from game_menu_art import background as menu_background, MENU_PALETTE, MENU_PALETTE_ROW, palette_bytes as menu_palette
from color_profiles import c_header as profiles_header

W, H = 640, 480
MAP_W = 128                         # map entries per row in VRAM
MAP_ROWS = H // 8

# the title plate's masthead (see masthead.py), True where the letters are
with Image.open(Path(__file__).resolve().parents[1] / 'font/masthead.png') as source:
    MASTHEAD = np.asarray(source.convert('1'))


# ---------------------------------------------------------------- layer 0

# "10" for the 12-pixel rail, narrower than two font glyphs
TEN = ['.#...###.',
       '##..##.##',
       '.#..##.##',
       '.#..##.##',
       '.#..##.##',
       '.#..##.##',
       '###..###.']


def box(img, x0, y0, x1, y1, colour):
    img[y0:y1 + 1, x0:x1 + 1] = colour


def outline(img, x0, y0, x1, y1, colour):
    img[y0, x0:x1 + 1] = colour
    img[y1, x0:x1 + 1] = colour
    img[y0:y1 + 1, x0] = colour
    img[y0:y1 + 1, x1] = colour


def raised(img, x0, y0, x1, y1):
    """A flat stone slab: ink outline, light upper and dark lower bevel."""
    box(img, x0, y0, x1, y1, STONE)
    outline(img, x0, y0, x1, y1, INK)
    img[y0 + 1, x0 + 1:x1] = CREAM
    img[y0 + 1:y1, x0 + 1] = CREAM
    img[y1 - 1, x0 + 1:x1] = BROWN
    img[y0 + 2:y1, x1 - 1] = BROWN


def recessed(img, x0, y0, x1, y1):
    """A light grey plate sunk into the stone: shadow above, lit lip below."""
    box(img, x0, y0, x1, y1, LIGHT)
    img[y0, x0:x1 + 1] = INK
    img[y0:y1 + 1, x0] = INK
    img[y1, x0 + 1:x1 + 1] = CREAM
    img[y0 + 1:y1 + 1, x1] = CREAM


def engrave(img, x, y, text, colour=INK, light=CREAM, scale=1):
    """Text cut into stone: dark letters with a lit lower-right edge."""
    draw_text(img, x + scale, y + scale, text, light, scale)
    draw_text(img, x, y, text, colour, scale)


def engrave_mask(img, x, y, rows, colour=INK, light=CREAM):
    mask = np.array([[ch == '#' for ch in row] for row in rows])
    img[y + 1:y + 1 + mask.shape[0], x + 1:x + 1 + mask.shape[1]][mask] = light
    img[y:y + mask.shape[0], x:x + mask.shape[1]][mask] = colour


def draw_frame(img):
    """Stone frame with the board coordinates on the bottom and left rails."""
    raised(img, L.FRAME_X0, L.FRAME_Y0, L.FRAME_X1, L.FRAME_Y1)
    # the board is recessed: shadow on the inner top/left edge, a closing
    # ink line where the board's last row and column have no grid edge
    x0, y0 = L.BOARD_X, L.BOARD_Y
    x1, y1 = x0 + L.BOARD_PX, y0 + L.BOARD_PX
    img[y0 - 1, x0 - 1:x1 + 1] = BROWN
    img[y0 - 1:y1 + 1, x0 - 1] = BROWN
    img[y1, x0:x1 + 1] = INK
    img[y0:y1 + 1, x1] = INK
    img[y1 + 1, x0:x1 + 2] = CREAM
    img[y0:y1 + 2, x1 + 1] = CREAM
    # coordinates: A-J below the board, 10-1 beside it
    rail_y = y1 + 1                                 # glyph rows 1..7 of the cell
    for c in range(L.BOARD_SIZE):
        engrave(img, x0 + c * L.SQUARE + 17, rail_y, chr(65 + c))
    for r in range(L.BOARD_SIZE):
        y = y0 + r * L.SQUARE + 16
        if r == 0:
            engrave_mask(img, L.FRAME_X0 + 2, y + 1, TEN)
        else:
            engrave(img, L.FRAME_X0 + 3, y, str(L.BOARD_SIZE - r))


def draw_bar(img):
    raised(img, L.BAR_X0, L.BAR_Y0, L.BAR_X1, L.BAR_Y1)
    recessed(img, *L.BAR_PLATE)


def draw_panel(img):
    raised(img, L.PANEL_X0, L.PANEL_Y0, L.PANEL_X1, L.PANEL_Y1)
    x0, x1 = L.INNER_X0, L.INNER_X1
    for y0, y1 in L.PLATES.values():
        recessed(img, x0, y0, x1, y1)

    # the Fraktur masthead in the deep red of red text, cut into the plate
    # like the engraved lettering: a lit edge to the lower right
    ty0, ty1 = L.PLATES['title']
    h, w = MASTHEAD.shape
    tx, ty = (x0 + x1 + 1 - w) // 2, (ty0 + ty1 + 1 - h) // 2
    img[ty + 1:ty + 1 + h, tx + 1:tx + 1 + w][MASTHEAD] = CREAM
    img[ty:ty + h, tx:tx + w][MASTHEAD] = DEEP_RED

    # a rule between the status lines and the selected piece
    iy0, _ = L.PLATES['info']
    rule = L.INFO_ROWS[2] * 8 - 5
    img[rule, x0 + 6:x1 - 5] = BROWN

    # the tray: a compartment for every piece, edged like the board grid
    tw, th = L.TRAY_COLS * L.SQUARE, L.TRAY_ROWS * L.SQUARE
    recessed(img, L.TRAY_X, L.TRAY_Y, L.TRAY_X + tw - 1, L.TRAY_Y + th - 1)
    for row in range(L.TRAY_ROWS):
        for col in range(L.TRAY_COLS):
            sx, sy = L.TRAY_X + col * L.SQUARE, L.TRAY_Y + row * L.SQUARE
            img[sy, sx:sx + L.SQUARE] = INK
            img[sy:sy + L.SQUARE, sx] = INK
            p0, p1 = 3, L.SQUARE - 4                # the empty pocket
            img[sy + p0, sx + p0:sx + p1 + 1] = STONE
            img[sy + p0:sy + p1 + 1, sx + p0] = STONE
            img[sy + p1, sx + p0 + 1:sx + p1 + 1] = CREAM
            img[sy + p0 + 1:sy + p1 + 1, sx + p1] = CREAM


def build_layer0(seed=1990, style=0):
    img = np.full((H, W), INK, np.uint8)    # dark margins around the slabs
    draw_frame(img)
    draw_bar(img)
    draw_panel(img)
    terrain = generate(seed, style)
    img[L.BOARD_Y:L.BOARD_Y + L.BOARD_PX, L.BOARD_X:L.BOARD_X + L.BOARD_PX] = terrain
    return img


# --------------------------------------------------------- tile reduction

def split_tiles(img):
    """(rows, cols, 64) array of 8x8 tiles in raster order."""
    h, w = img.shape
    return img.reshape(h // 8, 8, w // 8, 8).swapaxes(1, 2).reshape(h // 8, w // 8, 64)


def quantise_tiles(tiles, k, rng, iterations=12, palette=None):
    """Replace a set of tiles by at most k of its members (k-means medoids).

    Tiles are compared as RGB images. Each cluster is represented by the
    member nearest its centroid, so every kept tile is genuine artwork in
    the exact palette.
    """
    unique, inverse = np.unique(tiles, axis=0, return_inverse=True)
    inverse = inverse.ravel()
    if len(unique) <= k:
        return unique[inverse]
    colors = pil_palette() if palette is None else palette
    lut = np.array([colors[i * 3:i * 3 + 3] for i in range(16)], np.float32)
    vec = lut[unique].reshape(len(unique), -1)
    weight = np.bincount(inverse, minlength=len(unique)).astype(np.float32)
    # k-means++ seeding
    centres = [vec[rng.integers(len(vec))]]
    d2 = ((vec - centres[0]) ** 2).sum(1)
    for _ in range(1, k):
        p = d2 * weight
        centres.append(vec[rng.choice(len(vec), p=p / p.sum())])
        d2 = np.minimum(d2, ((vec - centres[-1]) ** 2).sum(1))
    centres = np.array(centres)
    sq = (vec ** 2).sum(1)
    for _ in range(iterations):
        dist = sq[:, None] - 2 * vec @ centres.T + (centres ** 2).sum(1)[None]
        label = dist.argmin(1)
        for c in range(k):
            members = label == c
            if members.any():
                centres[c] = np.average(vec[members], axis=0, weights=weight[members])
    dist = sq[:, None] - 2 * vec @ centres.T + (centres ** 2).sum(1)[None]
    label = dist.argmin(1)
    medoid = {}
    for c in np.unique(label):
        members = np.flatnonzero(label == c)
        medoid[c] = members[dist[members, c].argmin()]
    chosen = np.array([medoid[c] for c in label])
    return unique[chosen][inverse]


def pack_layer0(img, rng):
    """Quantise the board's terrain, then deduplicate all layer-0 tiles."""
    tiles = split_tiles(img)
    r0, c0 = L.BOARD_Y // 8, L.BOARD_X // 8
    n = L.BOARD_PX // 8
    board = tiles[r0:r0 + n, c0:c0 + n].reshape(-1, 64)
    tiles[r0:r0 + n, c0:c0 + n] = quantise_tiles(board, L.TERRAIN_TILES, rng).reshape(n, n, 64)
    flat = tiles.reshape(-1, 64)
    unique, inverse = np.unique(flat, axis=0, return_inverse=True)
    if len(unique) > 1024:
        raise ValueError(f'layer 0 needs {len(unique)} tiles; VERA allows 1024')
    tilemap = inverse.reshape(tiles.shape[:2])
    rebuilt = unique[tilemap].reshape(H // 8, W // 8, 8, 8).swapaxes(1, 2).reshape(H, W)
    return unique, tilemap, rebuilt


def tile_bytes(tiles):
    """4 bpp tile data: two pixels per byte, the left pixel in the high nibble."""
    t = np.asarray(tiles, np.uint8).reshape(-1, 32, 2)
    return ((t[:, :, 0] << 4) | t[:, :, 1]).astype(np.uint8).tobytes()


def map_bytes(tilemap):
    """128-column map rows of (tile low, tile high | palette offset) entries."""
    out = bytearray()
    for y, row in enumerate(tilemap):
        entries = np.zeros(MAP_W, np.uint16)
        entries[:len(row)] = row
        if L.BOARD_Y // 8 <= y < (L.BOARD_Y + L.BOARD_PX) // 8:
            first = L.BOARD_X // 8
            entries[first:first + L.BOARD_PX // 8] |= L.FIELD_PALETTE << 12
        out += entries.astype('<u2').tobytes()
    return bytes(out)


# ---------------------------------------------------------------- layer 1

def square_tiles(square):
    """The 25 tiles of a 40x40 square, row by row."""
    return list(split_tiles(square).reshape(-1, 64))


def plate_tile(row, col):
    """One of the 3x3 tiles of a floating plate (0 = first, 1 = middle, 2 = last).

    Light grey with an ink outline, lit on its upper and left edges, shaded
    on the lower and right, and with clipped outer corners.
    """
    t = np.full((8, 8), LIGHT, np.uint8)
    if row == 0:
        t[1, :] = CREAM
    if col == 0:
        t[:, 1] = CREAM
    if row == 2:
        t[6, :] = BROWN
    if col == 2:
        t[:, 6] = BROWN
    if row == 0:
        t[0, :] = INK
    if col == 0:
        t[:, 0] = INK
    if row == 2:
        t[7, :] = INK
    if col == 2:
        t[:, 7] = INK
    if row != 1 and col != 1:
        t[7 if row else 0, 7 if col else 0] = 0
    return t


def build_layer1(tokens):
    tiles = [np.zeros(64, np.uint8)]                    # L1_EMPTY
    corner = np.zeros((8, 8), np.uint8)
    corner[0, :] = INK
    corner[:, 0] = INK
    top = np.zeros((8, 8), np.uint8)
    top[0, :] = INK
    left = np.zeros((8, 8), np.uint8)
    left[:, 0] = INK
    marker = np.zeros((8, 8), np.uint8)
    marker[1:7, 2:6] = INK
    marker[2:6, 1:7] = INK
    marker[2:6, 2:6] = GOLD
    marker[2, 2] = marker[2, 5] = marker[5, 2] = marker[5, 5] = INK
    marker[2:4, 2:4][np.array([[1, 0], [0, 0]], bool)] = INK
    marker[2, 3] = CREAM
    tiles += [corner.ravel(), top.ravel(), left.ravel(), marker.ravel()]
    assert len(tiles) == L.L1_PLATE
    tiles += [plate_tile(i // 3, i % 3).ravel() for i in range(9)]
    assert len(tiles) == L.L1_FONT
    tiles += [glyph8(code).ravel() for code in range(32, 128)]
    assert len(tiles) == L.L1_FONT_PLATE
    tiles += [np.where(glyph8(code) != 0, INK, LIGHT).ravel() for code in range(32, 128)]
    assert len(tiles) == L.L1_PIECES
    for square in tokens:
        square = square.copy()          # a token on the board carries its grid edge
        square[0, :] = INK
        square[:, 0] = INK
        tiles += square_tiles(square)
    if len(tiles) > 1024:
        raise ValueError(f'layer 1 needs {len(tiles)} tiles; VERA allows 1024')
    return np.array(tiles)


def build_cursor():
    """64x64 sprite: gold corner brackets around a square placed at (12, 12)."""
    s = np.zeros((64, 64), np.uint8)
    a0, a1 = 12 - 3, 12 + L.SQUARE + 2          # bracket outer bounds
    arm = 11

    def bracket(colour, grow):
        for (cx, cy, sx, sy) in ((a0, a0, 1, 1), (a1, a0, -1, 1), (a0, a1, 1, -1), (a1, a1, -1, -1)):
            for i in range(-grow, arm + grow):
                for t in range(-grow, 3 + grow):
                    s[cy + sy * t, cx + sx * i] = colour
                    s[cy + sy * i, cx + sx * t] = colour

    bracket(INK, 1)
    bracket(GOLD, 0)
    return s


def lifted(square):
    """64x64 sprite of a token picked up: a dithered shadow falls behind it."""
    s = np.zeros((64, 64), np.uint8)
    yy, xx = np.mgrid[0:L.SQUARE, 0:L.SQUARE]
    foot = (square != 0) & ((yy + xx) % 2 == 0)
    d = L.LIFT_SHADOW
    s[d:d + L.SQUARE, d:d + L.SQUARE][foot] = INK
    s[:L.SQUARE, :L.SQUARE][square != 0] = square[square != 0]
    return s


POINTER = """
1...............
11..............
1c1.............
1cc1............
1ccc1...........
1cccc1..........
1ccccc1.........
1cccccc1........
1ccccccc1.......
1cccccccc1......
1ccccc11111.....
1cc1cc1.........
1c1.1cc1........
11..1cc1........
1....1cc1.......
.....1111.......
"""


def build_pointer():
    rows = POINTER.strip().splitlines()
    return np.array([[{'.': 0, '1': INK, 'c': CREAM}[ch] for ch in row] for row in rows],
                    np.uint8)


def build_sprites(tokens):
    """SPRITES.BIN: the lifted tokens, the brackets and the pointer, back to back."""
    data = b''.join(tile_bytes(lifted(square)) for square in tokens)
    assert L.VRAM_TOKEN_SPRITES + len(data) == L.VRAM_CURSOR
    data += tile_bytes(build_cursor())
    assert L.VRAM_SPRITES + len(data) == L.VRAM_POINTER
    return data + tile_bytes(build_pointer())


# ---------------------------------------------------------------- output

def c_header(layer0_count, layer1_count):
    consts = [
        ('BOARD_X', L.BOARD_X), ('BOARD_Y', L.BOARD_Y), ('SQUARE', L.SQUARE),
        ('PALETTE_FIELD', L.FIELD_PALETTE),
        ('SQUARE_TILES', L.SQUARE_TILES),
        ('INFO_ROW0', L.INFO_ROWS[0]), ('INFO_ROW1', L.INFO_ROWS[1]),
        ('INFO_ROW2', L.INFO_ROWS[2]), ('INFO_ROW3', L.INFO_ROWS[3]),
        ('PLATE_COL0', L.INNER_X0 // 8), ('PLATE_COLS', (L.INNER_X1 + 1 - L.INNER_X0) // 8),
        ('TRAY_COL0', L.TRAY_X // 8), ('TRAY_ROW0', L.TRAY_Y // 8),
        ('TRAY_X', L.TRAY_X), ('TRAY_Y', L.TRAY_Y),
        ('TRAY_COLS', L.TRAY_COLS), ('TRAY_ROWS', L.TRAY_ROWS),
        ('BAR_ROW0', L.BAR_ROWS[0]), ('BAR_ROW1', L.BAR_ROWS[1]),
        ('BAR_TEXT_COL', L.BAR_TEXT_COL), ('BAR_PIECE_ROW', L.BAR_PIECE_ROW),
        ('BAR_COL_RED', L.BAR_COL_RED), ('BAR_COL_VS', L.BAR_COL_VS),
        ('BAR_COL_BLUE', L.BAR_COL_BLUE),
        ('L1_EMPTY', L.L1_EMPTY), ('L1_GRID_CORNER', L.L1_GRID_CORNER),
        ('L1_GRID_TOP', L.L1_GRID_TOP), ('L1_GRID_LEFT', L.L1_GRID_LEFT),
        ('L1_MARKER', L.L1_MARKER), ('L1_PLATE', L.L1_PLATE), ('L1_FONT', L.L1_FONT),
        ('L1_FONT_PLATE', L.L1_FONT_PLATE), ('L1_PIECES', L.L1_PIECES),
        ('TOKENS', L.TOKENS), ('TOKEN_HIDDEN', L.TOKEN_HIDDEN),
        ('L0_TILE_COUNT', layer0_count), ('L1_TILE_COUNT', layer1_count),
        ('CURSOR_OFFSET', 12),
        ('SPRITE_POINTER', L.SPRITE_POINTER), ('SPRITE_DRAG', L.SPRITE_DRAG),
        ('SPRITE_CURSOR', L.SPRITE_CURSOR), ('SPRITE_FALL', L.SPRITE_FALL),
    ]
    vram = [('VRAM_L0_TILES', L.VRAM_L0_TILES), ('VRAM_L0_MAP', L.VRAM_L0_MAP),
            ('VRAM_L1_MAP', L.VRAM_L1_MAP), ('VRAM_L1_TILES', L.VRAM_L1_TILES),
            ('VRAM_SPRITES', L.VRAM_SPRITES), ('VRAM_TOKEN_SPRITES', L.VRAM_TOKEN_SPRITES),
            ('VRAM_CURSOR', L.VRAM_CURSOR), ('VRAM_POINTER', L.VRAM_POINTER),
            ('VRAM_PALETTE', L.VRAM_PALETTE)]
    lines = ['/* Generated by assets/scripts/build_graphics.py - do not edit. */',
             '#ifndef _GFX_H', '#define _GFX_H', '']
    lines += [f'#define {name:<20} {value}' for name, value in consts]
    lines += [f'#define {name:<20} 0x{value:05X}UL' for name, value in vram]
    lines += ['', '#endif', '']
    return '\n'.join(lines)


def check_end(name, addr, size):
    if (addr + size) % 0x10000 == 0:
        raise ValueError(f'{name} would end on a 64 KB boundary')


def save_png(path, img):
    im = Image.fromarray(img, 'P')
    im.putpalette(pil_palette())
    im.save(path)


def main():
    out = Path(sys.argv[1])
    preview = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(16)

    layer0 = build_layer0()
    l0_tiles, l0_map, rebuilt = pack_layer0(layer0, rng)
    tokens = build_tokens()
    l1_tiles = build_layer1(tokens)
    files = {
        'L0TILES.BIN': (L.VRAM_L0_TILES, tile_bytes(l0_tiles)),
        'L0MAP.BIN': (L.VRAM_L0_MAP, map_bytes(l0_map)),
        'L1TILES.BIN': (L.VRAM_L1_TILES, tile_bytes(l1_tiles)),
        'SPRITES.BIN': (L.VRAM_SPRITES, build_sprites(tokens)),
        'PALETTE.BIN': (L.VRAM_PALETTE, vera_palette()),
    }
    files.update(build_splash())
    menu = menu_background()
    menu_flat = split_tiles(menu).reshape(-1, 64)
    unique, inverse, counts = np.unique(menu_flat, axis=0, return_inverse=True, return_counts=True)
    # Preserve every artwork tile exactly. The menu does not need piece tokens,
    # so layer 1 can use the remaining space after its fonts and widgets.
    menu_capacity = 1024 + (1024 - L.L1_PIECES)
    if len(unique) > menu_capacity:
        raise ValueError(f'menu needs {len(unique)} exact tiles; the two layers allow {menu_capacity}')
    order = np.argsort(-counts, kind='stable')
    primary, overlay = order[:1024], order[1024:]
    primary_lookup = np.full(len(unique), -1, np.int32)
    primary_lookup[primary] = np.arange(len(primary))
    overlay_lookup = np.zeros(len(unique), np.uint16)
    overlay_lookup[overlay] = np.arange(len(overlay)) + L.L1_PIECES
    blank_id = np.flatnonzero((unique == LIGHT).all(axis=1))[0]
    blank_tile = primary_lookup[blank_id]
    assert blank_tile >= 0, 'blank UI surface must be in layer 0'
    menu_map = np.full((MAP_ROWS, MAP_W), blank_tile | (MENU_PALETTE_ROW << 12), np.uint16)
    menu_overlay = np.zeros((MAP_ROWS, MAP_W), np.uint16)
    in_primary = primary_lookup[inverse] >= 0
    menu_map[:, :W // 8] = np.where(in_primary, primary_lookup[inverse], blank_tile).reshape(MAP_ROWS, W // 8) | (MENU_PALETTE_ROW << 12)
    menu_overlay[:, :W // 8] = np.where(in_primary, 0, overlay_lookup[inverse] | (MENU_PALETTE_ROW << 12)).reshape(MAP_ROWS, W // 8)
    menu_l1_tiles = np.concatenate((l1_tiles[:L.L1_PIECES], unique[overlay]))
    assert len(primary) <= 1024 and len(menu_l1_tiles) <= 1024
    files['MNTILES.BIN'] = (L.VRAM_L0_TILES, tile_bytes(unique[primary]))
    files['MNMAP.BIN'] = (L.VRAM_L0_MAP, menu_map.astype('<u2').tobytes())
    files['MNL1TIL.BIN'] = (L.VRAM_L1_TILES, tile_bytes(menu_l1_tiles))
    files['MN1MAP.BIN'] = (L.VRAM_L1_MAP, menu_overlay.astype('<u2').tobytes())
    files['MNPAL.BIN'] = (L.VRAM_PALETTE + MENU_PALETTE_ROW * 32, menu_palette())
    print(f'campaign menu: {len(unique)} exact artwork tiles; layer 0 {len(primary)}/1024, layer 1 {len(menu_l1_tiles)}/1024')
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        menu_preview = Image.fromarray(menu, 'P')
        menu_preview.putpalette(pil_palette(MENU_PALETTE))
        menu_preview.save(preview / 'new-game-art.png')
    for style in (1, 3):
        field_tiles, field_map, field_preview = pack_layer0(
            build_layer0(style=style), np.random.default_rng(16))
        files[f'F{style}TILES.BIN'] = (L.VRAM_L0_TILES, tile_bytes(field_tiles))
        files[f'F{style}MAP.BIN'] = (L.VRAM_L0_MAP, map_bytes(field_map))
        if preview:
            preview.mkdir(parents=True, exist_ok=True)
            save_png(preview / f'field-art-{style}.png', field_preview)
    for name, (addr, data) in files.items():
        check_end(name, addr, len(data))
        (out / name).write_bytes(data)
    (out / 'gfx.h').write_text(c_header(len(l0_tiles), len(l1_tiles)))
    (out / 'color_profiles.h').write_text(profiles_header())
    print(f'layer 0: {len(l0_tiles)} tiles, layer 1: {len(l1_tiles)} tiles')

    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        save_png(preview / 'layer0.png', rebuilt)
        save_png(preview / 'layer0-exact.png', layer0)
        sheet = np.hstack(tokens)
        save_png(preview / 'tokens.png', sheet)


if __name__ == '__main__':
    main()
