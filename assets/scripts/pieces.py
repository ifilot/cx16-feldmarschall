"""Piece tokens (40x40, one board square) built from the portrait sheet.

Each card of `assets/pieces/red-sheet.png` is reduced to a 30-pixel portrait
in the shared palette and set into a token seen from above: an ink outline,
a bevelled army-coloured rim, the portrait on a deep army-coloured ground,
and the rank in the top-left corner (not on bombs and flags). Tokens have no
grid edge; the board tiles add it (see build_graphics.py), the drag sprites
do not.

All tokens are drawn in red; palette row 1 shows the same tiles in blue.
"""
from pathlib import Path

import numpy as np
from PIL import Image

from bitmap_font import glyph8
from layout import (PIECES, SHEET_CARD_ROWS, SHEET_CARD_W, SHEET_CARD_X,
                    SHEET_ORDER, SQUARE)
from palette import (BROWN, CREAM, DEEP_RED, GOLD, INK, KHAKI, RED, SAND,
                     rgb)

ASSETS = Path(__file__).resolve().parents[1]

# token geometry inside the square (inclusive pixel bounds)
TOKEN0, TOKEN1 = 2, 37              # ink outline
WINDOW0, WINDOW1 = 5, 34            # portrait window, 30 x 30
RANK_X, RANK_Y = 6, 4               # 8x8 rank glyph cell (glyph rows 1-7)
FIGURE_SHIFT = 4                    # ranked figures sit right of centre

# portrait colours: the sheet's own tones mapped onto the palette
PORTRAIT_INKS = [INK, CREAM, SAND, KHAKI, BROWN, GOLD, RED, DEEP_RED]
CARD_GROUND = np.array([26, 27, 26])


def load_cards():
    """Return {label: RGB array} for the twelve cards of the sheet."""
    with Image.open(ASSETS / 'pieces/red-sheet.png') as sheet:
        rgb_sheet = np.asarray(sheet.convert("RGB")).astype(np.int32)
    cards = {}
    for i, label in enumerate(SHEET_ORDER):
        x = SHEET_CARD_X[i % 6]
        y, h = SHEET_CARD_ROWS[i // 6]
        cards[label] = rgb_sheet[y:y + h, x:x + SHEET_CARD_W]
    return cards


def classify(card):
    """Map card pixels to palette indices; the card ground becomes -1.

    The ground (#1A1B1A) and the black outlines (#060303) are both nearly
    black, so they are separated here at full resolution, before reduction.
    """
    ground = np.abs(card - CARD_GROUND).sum(axis=2) <= 9
    colors = np.array([rgb(i) for i in PORTRAIT_INKS], np.int32)
    dist = ((card[:, :, None, :] - colors[None, None]) ** 2).sum(axis=3)
    out = np.array(PORTRAIT_INKS)[dist.argmin(axis=2)]
    out[ground] = -1
    return out


def content_box(indices):
    """Bounding box of the figure (non-ground pixels), ignoring stray specks."""
    figure = indices >= 0
    rows = np.flatnonzero(figure.sum(axis=1) > 3)
    cols = np.flatnonzero(figure.sum(axis=0) > 3)
    return cols[0], rows[0], cols[-1] + 1, rows[-1] + 1


def reduce(indices, rows, cols):
    """Majority vote of palette indices over a rows x cols grid of blocks.

    Outline ink wins a block when it covers 40% of it, which keeps the
    contours closed at this small scale.
    """
    h, w = indices.shape
    out = np.full((rows, cols), -1, np.int16)
    for oy in range(rows):
        y0, y1 = oy * h // rows, max(oy * h // rows + 1, (oy + 1) * h // rows)
        for ox in range(cols):
            x0, x1 = ox * w // cols, max(ox * w // cols + 1, (ox + 1) * w // cols)
            block = indices[y0:y1, x0:x1].ravel()
            values, counts = np.unique(block, return_counts=True)
            share = dict(zip(values.tolist(), counts.tolist()))
            if share.get(INK, 0) * 5 >= block.size * 2:
                out[oy, ox] = INK
            else:
                out[oy, ox] = values[counts.argmax()]
    return out


def portrait(card, shift):
    """A 30x30 portrait (palette indices, -1 = ground).

    The figure fills the window's height. Its horizontal centre of mass sits
    `shift` pixels right of the window centre; ranked pieces use this to
    leave the top-left corner free for the rank.
    """
    size = WINDOW1 - WINDOW0 + 1
    indices = classify(card)
    x0, y0, x1, y1 = content_box(indices)
    cols = max(1, round((x1 - x0) * size / (y1 - y0)))
    figure = reduce(indices[y0:y1, x0:x1], size, cols)
    mass = (figure >= 0).sum(axis=0)
    centre = (mass * np.arange(cols)).sum() / mass.sum()
    left = round((size - 1) / 2 + shift - centre)
    out = np.full((size, size), -1, np.int16)
    for x in range(cols):
        if 0 <= left + x < size:
            out[:, left + x] = figure[:, x]
    return out


def token(face=None, rank=None):
    """A 40x40 square (palette indices, 0 = transparent) with a token on it.

    `face` is a 30x30 portrait; without one the token shows its back.
    """
    sq = np.zeros((SQUARE, SQUARE), np.uint8)
    t0, t1 = TOKEN0, TOKEN1
    # drop shadow, then outline and bevelled rim
    sq[t0 + 2:t1 + 2, t0 + 2:t1 + 2] = INK
    sq[t0:t1 + 1, t0:t1 + 1] = INK
    sq[t0 + 1:t1, t0 + 1:t1] = DEEP_RED
    sq[t0 + 1:t1 - 1, t0 + 1:t1 - 1] = RED
    w0, w1 = WINDOW0, WINDOW1
    sq[w0 - 1:w1 + 1, w0 - 1:w1 + 1] = DEEP_RED
    sq[w0:w1 + 1, w0:w1 + 1] = DEEP_RED
    sq[w0 - 1, w0 - 1:w1 + 1] = INK          # recessed window: dark top/left edge
    sq[w0 - 1:w1 + 1, w0 - 1] = INK
    if face is None:
        draw_crest(sq)
    else:
        window = sq[w0:w1 + 1, w0:w1 + 1]
        window[face >= 0] = face[face >= 0]
    if rank is not None:
        # cream rank with an ink shadow in the window's free top-left corner
        glyph = glyph8(ord(rank)) != 0
        x, y = RANK_X, RANK_Y
        sq[y + 1:y + 9, x + 1:x + 9][glyph] = INK
        sq[y:y + 8, x:x + 8][glyph] = CREAM
    return sq


CREST = [
    '...........',
    '.#########.',
    '.#ooooooo#.',
    '.#ooo#ooo#.',
    '.#oo###oo#.',
    '.#ooo#ooo#.',
    '.#o#####o#.',
    '.#ooo#ooo#.',
    '.#ooo#ooo#.',
    '..#oo#oo#..',
    '...#ooo#...',
    '....#o#....',
    '.....#.....',
]


def draw_crest(sq):
    """Token back: a gold-rimmed shield with a cross, centred in the window."""
    h, w = len(CREST), len(CREST[0])
    y0 = (WINDOW0 + WINDOW1 + 1 - h) // 2
    x0 = (WINDOW0 + WINDOW1 + 1 - w) // 2
    for y, line in enumerate(CREST):
        for x, ch in enumerate(line):
            if ch == '#':
                sq[y0 + y, x0 + x] = GOLD
            elif ch == 'o':
                sq[y0 + y, x0 + x] = RED
    # a faint frame of studs around the shield
    for i in range(WINDOW0 + 2, WINDOW1 - 1, 4):
        for a, b in ((WINDOW0 + 2, i), (WINDOW1 - 2, i), (i, WINDOW0 + 2), (i, WINDOW1 - 2)):
            sq[a, b] = BROWN


def build_tokens():
    """Return the 13 token squares: the twelve ranks in PIECES order, then the back."""
    cards = load_cards()
    tokens = []
    for label, rank, _, _ in PIECES:
        ranked = rank.isdigit() or rank == 'S'      # bombs and flags show no rank
        face = portrait(cards[label], FIGURE_SHIFT if ranked else 0)
        tokens.append(token(face, rank if ranked else None))
    tokens.append(token())
    return tokens
