"""Compile the approved Marshal's Orders background for VERA layer 0.

The source is artwork only; the C scene supplies all live menu controls.
Its fixed palette occupies row 7 while the settings screen is open.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from palette import LIGHT, pil_palette

MENU_PALETTE = [
    0xBBA, 0x111, 0xEDB, 0xCA7, 0x985, 0x653, 0xEB4, 0x445,
    0x667, 0x899, 0xAA9, 0xBBA, 0x333, 0x554, 0xDDD, 0xEEE,
]
MENU_PALETTE_ROW = 7


def background():
    source = Path(__file__).resolve().parents[1] / 'menu/marshals-orders.png'
    with Image.open(source) as im:
        pixels = np.asarray(im.convert('RGB').resize((640, 480), Image.Resampling.BOX), dtype=np.int32)
    colors = np.array(pil_palette(MENU_PALETTE)[:48], dtype=np.int32).reshape(16, 3)
    distance = ((pixels[:, :, None, :] - colors[None, None, :, :]) ** 2).sum(axis=3)
    # VERA treats pixel index 0 as transparent, even with palette offset 7.
    # Use the identical opaque background color at index 11 instead.
    distance[:, :, 0] = np.iinfo(np.int32).max
    image = distance.argmin(axis=2).astype(np.uint8)
    # Flat live UI surfaces match the game's native text and plate tiles.
    image[136:336, :] = LIGHT
    image[416:, :] = LIGHT
    return image


def palette_bytes():
    return b''.join(bytes((color & 255, color >> 8)) for color in MENU_PALETTE)
