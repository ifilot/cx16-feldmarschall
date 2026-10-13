"""Render committed serif menu headings; normal builds read the resulting PNGs.

Caladea Bold (Carolina Giovagnoli, Andres Torresi and Huerta Tipografia,
SIL Open Font License 1.1). Supply a local Caladea-Bold.ttf to regenerate.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def main():
    font = ImageFont.truetype(sys.argv[1], 24 * 4)
    for name, text in (('main-menu', 'Main Menu'), ('new-game-title', 'New Game'), ('game-menu', 'Game Menu')):
        box = font.getbbox(text)
        source = Image.new('L', (box[2] - box[0], box[3] - box[1]))
        ImageDraw.Draw(source).text((-box[0], -box[1]), text, font=font, fill=255)
        source.thumbnail((140 * 4, 20 * 4))
        source = source.resize((source.width // 4, source.height // 4), Image.Resampling.BOX)
        target = Image.new('1', (144, 24))
        target.paste(source.point(lambda v: 255 if v >= 110 else 0).convert('1'),
                     ((144-source.width)//2, (24-source.height)//2))
        target.save(Path(__file__).resolve().parents[1] / 'font' / f'{name}.png')


if __name__ == '__main__':
    main()
