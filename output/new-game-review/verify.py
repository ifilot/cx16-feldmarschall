"""Verify the revised menu image against the actual game palette and tile budget."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'assets/scripts'))
from game_menu_art import MENU_PALETTE
from layout import L1_PIECES

path = ROOT / 'marshals-orders-prussian-v2.png'
palette = {
    tuple(((value >> shift) & 15) * 17 for shift in (8, 4, 0))
    for value in MENU_PALETTE
}
background = (187, 187, 170)
with Image.open(path) as image:
    assert image.size == (640, 480), image.size
    assert image.convert('RGBA').getchannel('A').getextrema() == (255, 255)
    pixels = np.asarray(image.convert('RGB'))
    counts = image.convert('RGB').getcolors(640 * 480)
    colors = {rgb for count, rgb in counts}
    assert 1 < len(colors) <= 16, len(colors)
    assert colors <= palette, colors - palette
    assert all(channel % 17 == 0 for rgb in colors for channel in rgb)
    assert (pixels[136:336] == background).all(), 'center background changed'
    assert (pixels[416:480] == background).all(), 'footer background changed'
    tiles = pixels.reshape(60, 8, 80, 8, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 192)
    tile_count = len(np.unique(tiles, axis=0))
    capacity = 1024 + (1024 - L1_PIECES)
    assert tile_count <= capacity, (tile_count, capacity)
report = {
    'file': path.name, 'width': 640, 'height': 480,
    'unique_pixel_colors': len(colors), 'maximum_colors': 16,
    'existing_menu_palette_only': True, 'opaque': True,
    'vera_12_bit_exact': True, 'fixed_background': '#BBBBAA',
    'center_y136_to335_uniform': True, 'footer_y416_to479_uniform': True,
    'unique_8x8_artwork_tiles': tile_count, 'available_artwork_tiles': capacity,
    'fits_existing_menu_tile_budget': True,
    'palette_pixel_counts': {'#%02X%02X%02X' % rgb: count for count, rgb in sorted(counts)},
    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
}
(ROOT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
