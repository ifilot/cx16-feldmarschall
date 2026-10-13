"""Exact native-resolution result panels, framed on a black 640x480 screen.

Selected candidates: win 3, loss 2, tie 1. Each uses <=16 VERA-exact colors.
Layer 0 contains the artwork, frame and heading; controls use existing fonts
on layer 1. Only one outcome is resident at a time, in the game's L0 region.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from bitmap_font import draw_text, text_width
import layout as L

ASSETS = Path(__file__).resolve().parents[1] / 'endings'
COLORS = np.array(json.loads((ASSETS / 'palette.json').read_text()), np.uint8)
ART_ROW = 9
OUTCOMES = [('victory', 'WIN', 'VICTORY', 'THE FIELD IS YOURS'),
            ('defeat', 'LOSS', 'DEFEAT', 'THE ARMY MUST REGROUP'),
            ('draw', 'DRAW', 'DRAW', 'NEITHER STANDARD FALLS')]


def background(name, title, subtitle):
    with Image.open(ASSETS / (name + '.png')) as source:
        if source.size != (320, 192):
            raise ValueError(f'{name}: artwork must be 320x192')
        rgb = np.asarray(source.convert('RGB'))
    matches = (rgb[:, :, None, :] == COLORS).all(axis=3)
    if len(COLORS) != 16 or (COLORS % 17).any() or not matches.any(axis=2).all():
        raise ValueError(f'{name}: artwork must use the sixteen VERA-exact colors')
    image = np.zeros((480, 640), np.uint8)
    image[120:312, 160:480] = matches.argmax(axis=2)
    for left, top, right, bottom in ((152, 112, 487, 319), (156, 116, 483, 315)):
        image[top, left:right+1] = image[bottom, left:right+1] = 2
        image[top:bottom+1, left] = image[top:bottom+1, right] = 2
        image[bottom-1, left+1:right] = 1
        image[top+1:bottom, right-1] = 1
    draw_text(image, (640-text_width(title, scale=2))//2, 64, title, 2, scale=2)
    draw_text(image, (640-text_width(subtitle))//2, 88, subtitle, 14)
    return image


def build_endings():
    files = {}
    for name, prefix, title, subtitle in OUTCOMES:
        image = background(name, title, subtitle)
        tiles = image.reshape(60, 8, 80, 8).swapaxes(1, 2).reshape(-1, 64)
        unique, inverse = np.unique(tiles, axis=0, return_inverse=True)
        if len(unique) > 1024:
            raise ValueError(f'{name}: {len(unique)} tiles exceeds VERA layer limit')
        assert not unique[0].any(), 'tile zero must be black'
        tilemap = np.zeros((64, 128), dtype='<u2')
        tilemap[:60, :80] = inverse.reshape(60, 80) | (ART_ROW << 12)
        packed = ((unique[:, 0::2] << 4) | unique[:, 1::2]).tobytes()
        # Decode the actual bytes independently to check lossless tile packing.
        encoded = np.frombuffer(packed, np.uint8).reshape(-1, 32)
        decoded = np.empty((len(unique), 64), np.uint8)
        decoded[:, 0::2], decoded[:, 1::2] = encoded >> 4, encoded & 15
        actual_map = np.frombuffer(tilemap.tobytes(), '<u2').reshape(64, 128)
        rebuilt = decoded[actual_map[:60, :80] & 1023].reshape(60, 80, 8, 8).swapaxes(1, 2).reshape(480, 640)
        assert np.array_equal(rebuilt, image)
        files[prefix+'TIL.BIN'] = (L.VRAM_L0_TILES, packed)
        files[prefix+'MAP.BIN'] = (L.VRAM_L0_MAP, tilemap.tobytes())
        print(f'{name}: {len(unique)}/1024 exact 4-bpp tiles, {len(packed)+tilemap.nbytes} bytes with map')
    # Rows 9..12: artwork, gold font, slate font, ivory font. Glyph ink is 1.
    palettes = [COLORS]
    for index in (2, 8, 14):
        palette = COLORS.copy()
        palette[1] = COLORS[index]
        palettes.append(palette)
    data = bytes(value for palette in palettes for r, g, b in palette.tolist()
                 for value in ((g//17 << 4) | b//17, r//17))
    files['ENDPAL.BIN'] = (L.VRAM_PALETTE + ART_ROW*32, data)
    return files


def save_previews(directory):
    for name, _, title, subtitle in OUTCOMES:
        image = Image.fromarray(background(name, title, subtitle), 'P')
        image.putpalette(COLORS.flatten().tolist())
        image.save(directory / ('ending-'+name+'.png'), bits=4)
