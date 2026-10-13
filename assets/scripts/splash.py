"""Encode the selected 640x480 four-color splash for VERA bitmap mode.

Two headerless chunks keep each KERNAL load below 64 KB. Four pixels are
packed per byte, leftmost first, without changing any artwork pixels.
"""
from pathlib import Path

import numpy as np
from PIL import Image

SPLASH_COLORS = np.array([(17, 17, 17), (68, 85, 85),
                          (221, 187, 102), (187, 51, 34)], dtype=np.uint8)


def build_splash():
    source = Path(__file__).resolve().parents[1] / 'splash/feldmarschall.png'
    with Image.open(source) as image:
        if image.size != (640, 480):
            raise ValueError('splash must be 640x480')
        pixels = np.asarray(image.convert('RGB'))
    colors = SPLASH_COLORS
    matches = (pixels[:, :, None, :] == colors).all(axis=3)
    if not matches.any(axis=2).all() or len(np.unique(pixels.reshape(-1, 3), axis=0)) != 4:
        raise ValueError('splash must use exactly the four ink/slate/gold/red palette colors')
    indices = matches.argmax(axis=2).astype(np.uint8).reshape(-1, 4)
    packed = ((indices[:, 0] << 6) | (indices[:, 1] << 4) |
              (indices[:, 2] << 2) | indices[:, 3]).tobytes()
    palette = bytearray()
    for red, green, blue in colors.tolist():
        palette.extend([(green // 17 << 4) | blue // 17, red // 17])
    return {
        'SPLASH0.BIN': (0x00000, packed[:38400]),
        'SPLASH1.BIN': (0x09600, packed[38400:]),
        'SPLPAL.BIN': (0x1FA00, bytes(palette)),
    }
