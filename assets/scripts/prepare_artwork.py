"""Convert the four selected high-resolution sources to native 320x192 panels.

Use --check to verify that the current installed assets match their sources.
Normal builds use the committed native assets and do not need this step.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    colors = np.array(json.loads((ASSETS/'endings/palette.json').read_text()), dtype=np.uint8)
    assert colors.shape == (16, 3) and not (colors % 17).any()
    palette = Image.new('P', (1, 1))
    palette.putpalette(colors.flatten().tolist())
    for name in ('title', 'victory', 'defeat', 'draw'):
        source = ASSETS/'artwork-source'/f'{name}.png'
        target = ASSETS/'splash/marshal.png' if name == 'title' else ASSETS/'endings'/f'{name}.png'
        with Image.open(source) as image:
            image = image.convert('RGB')
            image.thumbnail((320, 192), Image.Resampling.LANCZOS)
            canvas = Image.new('RGB', (320, 192), (0, 0, 0))
            canvas.paste(image, ((320-image.width)//2, (192-image.height)//2))
        panel = canvas.quantize(palette=palette, dither=Image.Dither.NONE)
        assert panel.size == (320, 192) and np.asarray(panel).max() < 16
        if args.check:
            with Image.open(target) as installed:
                assert installed.size == panel.size
                assert installed.convert('RGB').tobytes() == panel.convert('RGB').tobytes(), f'{target}: source/export mismatch'
        else:
            panel.save(target, bits=4)
        print(f'{name}: native 320x192, <=16 VERA colors, {"matches installed asset" if args.check else "exported"}')


if __name__ == '__main__':
    main()
