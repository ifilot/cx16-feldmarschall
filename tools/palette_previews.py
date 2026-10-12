"""Generate exact palette swaps of the game screenshot and VERA palettes.

Run: python3 tools/palette_previews.py
The installed game palette is unchanged. Each option uses the same sixteen
indices and the same army/text palette-row remapping as the game.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'assets/scripts'))
from palette import RGB12, rgb, vera_palette  # noqa: E402


from color_profiles import SCHEMES  # noqa: E402


def encode_palette(colors):
    return vera_palette(colors, colors)


def source_indices(source):
    with Image.open(source) as image:
        pixels = np.asarray(image.convert('RGB'))
    base = np.array([rgb(i) for i in range(16)], dtype=np.uint8)
    matches = (pixels[:, :, None, :] == base).all(axis=3)
    if not matches.any(axis=2).all():
        raise ValueError(f'{source} contains colors outside the game palette')
    return matches.argmax(axis=2).astype(np.uint8)


def main():
    destination = ROOT / 'output/palette-studies'
    destination.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'docs/play.png'
    indices = source_indices(source)
    assert indices.shape == (480, 640)
    assert encode_palette(RGB12) == vera_palette()
    tiles = [('Current: red / blue', Image.open(source).convert('RGB'))]
    metadata = []
    for slug, title, description, colors in SCHEMES:
        values = np.array([rgb(i, colors) for i in range(16)], dtype=np.uint8)
        pixels = values[indices]
        preview = Image.fromarray(pixels)
        preview.save(destination / f'{slug}.png')
        # Verify the output is an exact color substitution for every pixel.
        with Image.open(destination / f'{slug}.png') as saved:
            assert np.array_equal(np.asarray(saved.convert('RGB')), values[indices])
            assert len(saved.getcolors(256)) <= 16
        assert len(np.unique(pixels.reshape(-1, 3), axis=0)) == 16
        packed = encode_palette(colors)
        assert len(packed) == 512
        (destination / f'{slug}.BIN').write_bytes(packed)
        tiles.append((title, preview))
        metadata.append({'name': title, 'description': description,
                         'preview': f'{slug}.png', 'palette_file': f'{slug}.BIN',
                         'rgb12': [f'{color:03X}' for color in colors],
                         'army_a': [f'{colors[i]:03X}' for i in (12, 13)],
                         'army_b': [f'{colors[i]:03X}' for i in (14, 15)]})
    (destination / 'palettes.json').write_text(json.dumps(metadata, indent=2) + '\n')
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    overview = Image.new('RGB', (1304, 1560), '#202020')
    draw = ImageDraw.Draw(overview)
    for i, (title, preview) in enumerate(tiles):
        x, y = 8 + (i % 2) * 648, 8 + (i // 2) * 520
        draw.text((x + 8, y + 4), title, font=font, fill='#eeeecc')
        overview.paste(preview, (x, y + 32))
    overview.save(destination / 'comparison.png')
    print(f'Five exact 640x480 palette swaps, VERA palettes and comparison: {destination}')


if __name__ == '__main__':
    main()
