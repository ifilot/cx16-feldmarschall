"""Check actual decoded pixels, dimensions, opacity and X16 palette precision."""
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
EXPECTED = {(17, 17, 17), (68, 85, 85), (221, 187, 102), (187, 51, 34)}
report = []
for path in sorted(ROOT.glob('[0-9][0-9]-*.png')):
    with Image.open(path) as image:
        assert image.size == (640, 480), (path.name, image.size)
        assert image.convert('RGBA').getchannel('A').getextrema() == (255, 255)
        counts = image.convert('RGB').getcolors(maxcolors=640 * 480)
        colors = {rgb for count, rgb in counts}
        assert len(colors) == 4, (path.name, len(colors))
        assert colors == EXPECTED, (path.name, colors)
        assert all(channel % 17 == 0 for rgb in colors for channel in rgb)
        if path.stem in ('01-the-marshal-v3', '01-the-marshal-v4', '01-the-marshal-v5', '01-the-marshal-frame'):
            with Image.open(ROOT / 'source/collar-mask.png') as mask:
                assert all(rgb != (187, 51, 34) or allowed == 255
                           for rgb, allowed in zip(image.convert('RGB').getdata(), mask.convert('L').getdata())), 'red outside standing collar'
        entry = {
            'file': path.name, 'width': 640, 'height': 480,
            'unique_pixel_colors': len(colors), 'opaque': True,
            'vera_12_bit_exact': True,
            'palette_pixel_counts': {
                '#%02X%02X%02X' % rgb: count for count, rgb in sorted(counts)
            },
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        report.append(entry)
        if path.stem in ('01-the-marshal-v3', '01-the-marshal-v4', '01-the-marshal-v5', '01-the-marshal-frame'):
            entry['red_confined_to_standing_collar'] = True
        print(f'{path.name}: PASS — 640x480, exactly 4 colors, opaque, VERA-exact')
(ROOT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
