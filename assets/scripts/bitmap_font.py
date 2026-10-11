"""Kakuro's native 8x8 pixel font (ASCII 32..127), drawn in palette INK.

`assets/font/kakuro-ui.png` is copied from Ivo Filot's cx16-kakuro
(GPL-3.0-or-later). Glyphs occupy the left 7 columns and lower 7 rows of
their cell; the alpha mask uses Kakuro's >150 cutoff.
"""
from pathlib import Path

import numpy as np
from PIL import Image

from palette import INK

ASSETS = Path(__file__).resolve().parents[1]
with Image.open(ASSETS / 'font/kakuro-ui.png') as source:
    if source.size != (128, 48):
        raise ValueError('Bitmap font must contain ASCII 32..127 in 8x8 cells')
    MASK = np.asarray(source.convert('RGBA'))[:, :, 3] > 150


def glyph8(code):
    """8x8 array: INK where the glyph is set, 0 elsewhere."""
    code = code if 32 <= code <= 127 else ord('?')
    slot = code - 32
    return MASK[slot // 16 * 8:slot // 16 * 8 + 8,
                slot % 16 * 8:slot % 16 * 8 + 8].astype(np.uint8) * INK


def draw_text(image, x, y, string, colour, scale=1, tracking=0):
    """Draw `string` with its cell's top-left at (x, y) on an index image."""
    for char in string:
        g = glyph8(ord(char)).repeat(scale, 0).repeat(scale, 1)
        region = image[y:y + g.shape[0], x:x + g.shape[1]]
        region[g != 0] = colour
        x += 8 * scale + tracking


def text_width(string, scale=1, tracking=0):
    return len(string) * (8 * scale + tracking) - tracking
