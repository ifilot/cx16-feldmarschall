"""Render the splash footer with the game's existing Kakuro 8x8 bitmap font.

Usage: python3 assets/scripts/splash_footer.py INPUT.png OUTPUT.png
The illustration and border outside the footer's inner rectangle are unchanged.
"""
import sys

import numpy as np
from PIL import Image

from bitmap_font import draw_text, text_width
from splash import SPLASH_COLORS

TEXT = 'ENTER to continue'
FOOTER = (48, 451, 592, 473)
TEXT_X = (640 - text_width(TEXT)) // 2
TEXT_Y = 457


def render_footer(source):
    if source.size != (640, 480):
        raise ValueError('splash must be 640x480')
    pixels = np.asarray(source.convert('RGB'))
    matches = (pixels[:, :, None, :] == SPLASH_COLORS).all(axis=3)
    if not matches.any(axis=2).all():
        raise ValueError('splash must use the ink/slate/gold/red palette')
    indices = matches.argmax(axis=2).astype(np.uint8)
    x0, y0, x1, y1 = FOOTER
    indices[y0:y1, x0:x1] = 0
    draw_text(indices, TEXT_X, TEXT_Y, TEXT, colour=2)
    image = Image.fromarray(indices, 'P')
    image.putpalette(SPLASH_COLORS.flatten().tolist() + [0] * (768 - 12))
    return image


if __name__ == '__main__':
    with Image.open(sys.argv[1]) as source:
        image = render_footer(source)
    image.save(sys.argv[2], bits=2)
