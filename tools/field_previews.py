"""Render the available field choices from the built game's exact pixel artwork."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'assets/scripts'))
from color_profiles import FIELDS  # noqa: E402
from layout import BOARD_X, BOARD_Y, BOARD_PX, SQUARE  # noqa: E402
from palette import pil_palette, rgb  # noqa: E402


def main():
    out = ROOT / 'output/style-studies'
    out.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    columns = 2 if len(FIELDS) <= 4 else 3
    rows = (len(FIELDS) + columns - 1) // columns
    overview = Image.new('RGB', (8 + columns * 408, 8 + rows * 430), '#202020')
    labels = ImageDraw.Draw(overview)
    for i, (slug, name, colors, art) in enumerate(FIELDS):
        source = ROOT / 'build/preview' / (f'field-art-{art}.png' if art else 'layer0.png')
        with Image.open(source) as image:
            image.putpalette(pil_palette())
            full = image.convert('RGB')
            board = image.crop((BOARD_X, BOARD_Y, BOARD_X + BOARD_PX,
                                BOARD_Y + BOARD_PX))
            board.putpalette(pil_palette(colors))
            board = board.convert('RGB')
            full.paste(board, (BOARD_X, BOARD_Y))
            full.save(out / f'field-{slug}.png')
        grid = ImageDraw.Draw(board)
        for position in range(0, BOARD_PX, SQUARE):
            grid.line((position, 0, position, BOARD_PX - 1), fill=rgb(1, colors))
            grid.line((0, position, BOARD_PX - 1, position), fill=rgb(1, colors))
        x, y = 8 + (i % columns) * 408, 8 + (i // columns) * 430
        labels.text((x + 4, y), name, font=font, fill='#eeeecc')
        overview.paste(board, (x, y + 26))
    overview.save(out / 'fields.png')
    print(f'Field comparisons: {out / "fields.png"}')


if __name__ == '__main__':
    main()
