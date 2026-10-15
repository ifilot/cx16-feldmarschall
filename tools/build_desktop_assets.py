"""Embed the game's Classic artwork in the native Qt6 executable."""
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'assets/scripts'))
from palette import RGB12, pil_palette, row_colors
from pieces import build_tokens
from terrain import generate


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    board = Image.fromarray(generate(), 'P')
    board.putpalette(pil_palette(RGB12))
    board.convert('RGB').save(destination / 'board.png')
    names = ['board.png']
    tokens = build_tokens('classic')
    for army in range(2):
        for rank, indices in enumerate(tokens):
            token = Image.fromarray(indices, 'P')
            token.putpalette(pil_palette(row_colors(army + 1)))
            token.info['transparency'] = 0
            name = f'token-{army}-{rank}.png'
            token.convert('RGBA').save(destination / name)
            names.append(name)
    (destination / 'assets.qrc').write_text('<RCC><qresource prefix="/game">\n' +
        '\n'.join(f'<file>{name}</file>' for name in names) + '\n</qresource></RCC>\n')


if __name__ == '__main__':
    main()
