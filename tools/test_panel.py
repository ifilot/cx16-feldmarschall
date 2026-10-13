"""Battle-panel pieces have transparent grid edges in both rank numberings."""
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from distribute import runtime_files
from test_colors import ROOT, start, choose
from test_variants import position, drag


def square(data, offset):
    packed = np.frombuffer(data[offset:offset + 25 * 32], dtype=np.uint8)
    pixels = np.empty(packed.size * 2, dtype=np.uint8)
    pixels[::2], pixels[1::2] = packed >> 4, packed & 15
    return pixels.reshape(5, 5, 8, 8).transpose(0, 2, 1, 3).reshape(40, 40)


def assets():
    classic = (ROOT / 'src/L1TILES.BIN').read_bytes()
    modern = (ROOT / 'src/RANKTIL.BIN').read_bytes()
    assert len(classic) // 32 <= 1024
    assert 0x10000 + len(classic) <= 0x18000, 'tiles overlap sprites'
    for data, first in ((classic, 206), (modern, 0)):
        for piece in range(13):
            board = square(data, (first + piece * 25) * 32)
            panel = square(data, (first + 13 * 25 + piece * 25) * 32)
            assert np.all(board[0] != 0) and np.all(board[:, 0] != 0), 'board grid missing'
            assert not np.any(panel[0]) and not np.any(panel[:, 0]), 'panel contains a grid line'
            assert np.array_equal(board[1:, 1:], panel[1:, 1:]), 'piece artwork changed'


def main():
    assets()
    with tempfile.TemporaryDirectory(prefix='feldmarschall-panel-') as tmp:
        directory = Path(tmp)
        for name in runtime_files():
            shutil.copyfile(ROOT / 'src' / name, directory / name)
        session = start(directory)
        try:
            for rank in ('classic', 'modern'):
                if rank == 'modern':
                    choose(session, '4')
                    choose(session, 'Tab')
                    choose(session, 'Tab')
                    choose(session, '2')
                    choose(session, 'Escape')
                choose(session, '2')
                choose(session, 'Return')
                choose(session, 'R')
                choose(session, 'Return')
                position(session, {60: 6, 50: 0x17})
                drag(session, 60, 50, wait=10)
                path = ROOT / f'build/test-shots/panel-{rank}.png'
                session.shot(path)
                with Image.open(path) as screen, Image.open(ROOT / 'build/preview/layer0.png') as backdrop:
                    screen, backdrop = screen.convert('RGB'), backdrop.convert('RGB')
                    for x in (37 * 8, 46 * 8):
                        for region in ((x, 432, x + 1, 472), (x, 432, x + 40, 433)):
                            assert screen.crop(region).tobytes() == backdrop.crop(region).tobytes(), 'grid edge remains visible in battle panel'
                # Finish the battle, then quit before changing rank numbering.
                session.emu.advance(320)
                choose(session, 'Escape')
                choose(session, '3')
            print('panel: all 13 tokens in both rank numberings retain board grids and render clean panel edges; VRAM fits: ok')
        finally:
            session.emu.close()


if __name__ == '__main__':
    main()
