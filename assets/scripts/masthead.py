"""Render the Fraktur masthead of the title plate to assets/font/masthead.png.

    python3 masthead.py UnifrakturMaguntia-Book.ttf

The masthead is set in UnifrakturMaguntia (SIL Open Font License,
https://github.com/google/fonts/tree/main/ofl/unifrakturmaguntia), a
Fraktur after the German book faces of the late 18th century. Blackletter
was never set in capitals, so the word is in mixed case.

This is not part of the build: the PNG is committed, and build_graphics.py
only reads it, so the pixels can be touched up by hand. The word is drawn
eight times oversize, box-filtered to screen size and thresholded; the PNG
is 1 bit deep (white = ink) and cropped to the letters.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WORD = 'Feldmarschall'
MAX_W, MAX_H = 190, 32              # inside the 200 x 40 title plate
SUPERSAMPLE = 8
THRESHOLD = 110                     # of 255 coverage

OUT = Path(__file__).resolve().parents[1] / 'font/masthead.png'


def render(path, word=WORD):
    ss = SUPERSAMPLE
    for size in range(60 * ss, 4 * ss, -ss // 4):       # largest size that fits
        font = ImageFont.truetype(str(path), size)
        left, top, right, bottom = font.getbbox(word)
        if right - left <= MAX_W * ss and bottom - top <= MAX_H * ss:
            break
    w, h = (right - left) // ss + 2, (bottom - top) // ss + 2
    big = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(big).text((ss - left, ss - top), word, 255, font=font)
    mask = np.asarray(big.resize((w, h), Image.BOX)) > THRESHOLD
    ys, xs = np.nonzero(mask)
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def main():
    mask = render(sys.argv[1])
    Image.fromarray(mask).save(OUT)
    print(f'{OUT.name}: {mask.shape[1]} x {mask.shape[0]}')


if __name__ == '__main__':
    main()
