"""Draw a one-pixel gold frame and mirrored pixel ornaments on the splash.

Usage: python3 assets/scripts/splash_frame.py INPUT.png OUTPUT.png
Only the outer frame and four corner boxes are touched.
"""
import sys

import numpy as np
from PIL import Image

from splash import SPLASH_COLORS


def render_frame(source):
    if source.size != (640, 480):
        raise ValueError('splash must be 640x480')
    pixels = np.asarray(source.convert('RGB'))
    matches = (pixels[:, :, None, :] == SPLASH_COLORS).all(axis=3)
    if not matches.any(axis=2).all():
        raise ValueError('splash must use the existing four-color palette')
    indices = matches.argmax(axis=2).astype(np.uint8)
    # Erase only the old frame and corner ornaments, in palette ink.
    indices[:5, :] = indices[474:, :] = 0
    indices[:, :5] = indices[:, 635:] = 0
    for x0, y0, x1, y1 in ((5,5,22,23), (617,5,635,23),
                          (5,456,22,474), (617,456,635,474)):
        indices[y0:y1, x0:x1] = 0
    indices[4, 4:636] = indices[474, 4:636] = 2
    indices[4:475, 4] = indices[4:475, 635] = 2
    # One small ornament: three square loops connected around a diamond.
    ornament = np.zeros((16,16), dtype=bool)
    for x, y in ((1,1), (10,1), (1,10)):
        ornament[y, x:x+4] = ornament[y+3, x:x+4] = True
        ornament[y:y+4, x] = ornament[y:y+4, x+3] = True
    for x, y in ((7,5),(8,6),(9,7),(8,8),(7,9),(6,8),(5,7),(6,6),
                 (5,4),(6,5),(10,5),(9,6),(5,10),(6,9)):
        ornament[y,x] = True
    for x, y, motif in ((6,6,ornament), (618,6,ornament[:,::-1]),
                       (6,457,ornament[::-1,:]), (618,457,ornament[::-1,::-1])):
        indices[y:y+16, x:x+16][motif] = 2
    image = Image.fromarray(indices, 'P')
    image.putpalette(SPLASH_COLORS.flatten().tolist() + [0] * (768-12))
    return image


if __name__ == '__main__':
    with Image.open(sys.argv[1]) as source:
        image = render_frame(source)
    image.save(sys.argv[2], bits=2)
