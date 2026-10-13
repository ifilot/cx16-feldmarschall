"""Preview all army palettes using the actual shared token artwork."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'assets/scripts'))
from color_profiles import ARMIES  # noqa: E402
from palette import pil_palette, row_colors  # noqa: E402
from pieces import build_tokens  # noqa: E402


def main():
    out = ROOT / 'build/preview/style-studies'
    out.mkdir(parents=True, exist_ok=True)
    template = Image.fromarray(np.hstack(build_tokens()), 'P')
    width = template.width
    overview = Image.new('RGB', (width * 2 + 24, len(ARMIES) * 70 + 8), '#202020')
    labels = ImageDraw.Draw(overview)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    for i, (slug, name, colors) in enumerate(ARMIES):
        y = 8 + i * 70
        labels.text((8, y), name, font=font, fill='#eeeecc')
        pair = Image.new('RGB', (width * 2 + 8, 40))
        for army in (1, 2):
            strip = template.copy()
            strip.putpalette(pil_palette(row_colors(army, pieces=colors)))
            x = (army - 1) * (width + 8)
            pair.paste(strip.convert('RGB'), (x, 0))
            overview.paste(strip.convert('RGB'), (8 + x, y + 24))
        pair.save(out / f'army-{slug}.png')
    overview.save(out / 'armies.png')
    print(f'Army comparisons: {out / "armies.png"}')


if __name__ == '__main__':
    main()
