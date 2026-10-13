"""Build the sixteen-color startup screen as one exact VERA tile layer.

Native 320x192 artwork sits within algorithmic beveled frames. Typography
and the version/date footer are generated from the current build metadata.
"""
from pathlib import Path

import numpy as np
from PIL import Image
from bitmap_font import draw_text, text_width
from endings import COLORS
import layout as L

def render_splash(version, compiled):
    assets = Path(__file__).resolve().parents[1]
    source = assets / 'splash/marshal.png'
    with Image.open(source) as image:
        if image.size != (320, 192):
            raise ValueError('splash artwork must be 320x192')
        pixels = np.asarray(image.convert('RGB'))
    matches = (pixels[:, :, None, :] == COLORS).all(axis=3)
    if not matches.any(axis=2).all() or (COLORS % 17).any():
        raise ValueError('splash must use the sixteen VERA-exact palette colors')
    screen = np.zeros((480, 640), np.uint8)
    screen[144:336, 160:480] = matches.argmax(axis=2)
    for left, top, right, bottom in ((4, 4, 635, 475), (152, 136, 487, 343),
                                    (156, 140, 483, 339)):
        screen[top, left:right+1] = screen[bottom, left:right+1] = 2
        screen[top:bottom+1, left] = screen[top:bottom+1, right] = 2
        screen[bottom-1, left+1:right] = 1
        screen[top+1:bottom, right-1] = 1
    with Image.open(assets / 'font/masthead.png') as image:
        title = np.asarray(image.convert('1')).repeat(2, 0).repeat(2, 1)
    h, w = title.shape
    x, y = (640-w)//2, 48
    screen[y+1:y+h+1, x+1:x+w+1][title] = 1
    screen[y:y+h, x:x+w][title] = 2
    for text, y, color in (('A GAME OF HIDDEN ARMIES', 120, 14),
                          ('ENTER to continue', 376, 2),
                          (f'{version} / COMPILED {compiled}', 408, 8)):
        draw_text(screen, (640-text_width(text))//2, y, text, color)
    return screen


def build_splash(version, compiled):
    screen = render_splash(version, compiled)
    tiles = screen.reshape(60, 8, 80, 8).swapaxes(1, 2).reshape(-1, 64)
    unique, inverse = np.unique(tiles, axis=0, return_inverse=True)
    if len(unique) > 1024:
        raise ValueError(f'splash needs {len(unique)} tiles; VERA allows 1024')
    assert not unique[0].any()
    packed = ((unique[:, 0::2] << 4) | unique[:, 1::2]).tobytes()
    tilemap = np.zeros((64, 128), dtype='<u2')
    tilemap[:60, :80] = inverse.reshape(60, 80)
    # Verify exact reconstruction from the packed 4-bpp bytes.
    encoded = np.frombuffer(packed, np.uint8).reshape(-1, 32)
    decoded = np.empty((len(unique), 64), np.uint8)
    decoded[:, 0::2], decoded[:, 1::2] = encoded >> 4, encoded & 15
    rebuilt = decoded[tilemap[:60, :80]].reshape(60, 80, 8, 8).swapaxes(1, 2).reshape(480, 640)
    assert np.array_equal(rebuilt, screen)
    palette = bytes(value for r, g, b in COLORS.tolist()
                    for value in ((g//17 << 4) | b//17, r//17))
    print(f'splash: {len(unique)}/1024 exact 4-bpp tiles; {len(packed)+tilemap.nbytes+len(palette)} VRAM bytes')
    return {
        'SPLTIL.BIN': (L.VRAM_L0_TILES, packed),
        'SPLMAP.BIN': (L.VRAM_L0_MAP, tilemap.tobytes()),
        'SPLPAL.BIN': (L.VRAM_PALETTE, palette),
    }


def save_preview(path, version, compiled):
    image = Image.fromarray(render_splash(version, compiled), 'P')
    image.putpalette(COLORS.flatten().tolist())
    image.save(path, bits=4)
