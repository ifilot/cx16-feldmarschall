"""Procedural battlefield terrain for the 400x400 board (palette indices).

Inspired by the 1990 Accolade Stratego map: open sand with dunes, olive grass,
clumps of trees that thicken towards the edges, and a river that runs from
edge to edge through the two lakes. The lakes fill their 2x2 squares, so the
impassable water is always obvious; the river follows the line between rows
5 and 6 and only borders squares.

The result is deterministic for a given seed.
"""
import numpy as np
from PIL import Image

from layout import BOARD_PX, LAKES, SQUARE
from palette import (BLUE, BROWN, CREAM, DEEP, FOREST, KHAKI, OLIVE, SAND,
                     WATER_LIGHT)

BAYER4 = np.array([[0, 8, 2, 10],
                   [12, 4, 14, 6],
                   [3, 11, 1, 9],
                   [15, 7, 13, 5]], np.float32) / 16 + 1 / 32


def value_noise(rng, size, cell):
    """Smooth noise in [0, 1) with features of about `cell` pixels."""
    n = size // cell + 3
    grid = Image.fromarray(rng.random((n, n)).astype(np.float32), 'F')
    big = np.asarray(grid.resize((n * cell, n * cell), Image.BICUBIC))
    o = cell // 2
    return np.clip(big[o:o + size, o:o + size], 0, 1)


def fbm(rng, size, cells, weights):
    total = sum(w * value_noise(rng, size, c) for c, w in zip(cells, weights))
    return total / sum(weights)


def dither(size):
    reps = size // 4 + 1
    return np.tile(BAYER4, (reps, reps))[:size, :size]


def dilate(mask, r):
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


def water_mask(rng, size):
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    wobble = value_noise(rng, size, 12) - 0.5
    water = np.zeros((size, size), bool)
    for col, row in LAKES:
        cx = col * SQUARE + SQUARE - 0.5
        cy = row * SQUARE + SQUARE - 0.5
        r = SQUARE - 5 + wobble * 6
        shape = (np.abs(xx - cx) / r) ** 3 + (np.abs(yy - cy) / r) ** 3
        water |= shape <= 1
    # the river: a meandering band on the line between the two middle rows
    x = np.arange(size, dtype=np.float32)
    centre = size / 2 + 3.5 * np.sin(x / 21) + 2 * np.sin(x / 8.5 + 1.3)
    half = 2.2 + 1.2 * value_noise(rng, size, 20)[0]
    water |= np.abs(yy - centre[None, :]) <= half[None, :]
    return water


def generate(seed=1990):
    rng = np.random.default_rng(seed)
    size = BOARD_PX
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    bayer = dither(size)

    water = water_mask(rng, size)
    shore = dilate(water, 2) & ~water
    near_water = dilate(water, 10) & ~water

    # vegetation density: noise, denser towards the edges and along the banks
    edge = np.minimum(np.minimum(xx, size - 1 - xx), np.minimum(yy, size - 1 - yy))
    veg = fbm(rng, size, (90, 40, 16), (0.55, 0.3, 0.15))
    veg += 0.22 * np.clip(1 - edge / 70, 0, 1) + 0.1 * near_water
    forest = veg > 0.66
    grass = (veg > 0.56 + 0.06 * bayer) & ~forest

    # sand with dunes: dither light sand into khaki along slow bands
    dunes = fbm(rng, size, (50, 18, 6), (0.5, 0.3, 0.2))
    out = np.where(dunes + 0.35 * bayer > 0.72, KHAKI, SAND).astype(np.uint8)
    speck = rng.random((size, size))
    out[speck < 0.012] = BROWN
    out[(speck > 0.996) & (out == SAND)] = CREAM

    # grass: olive with darker tufts
    out[grass] = OLIVE
    out[grass & (speck < 0.18)] = FOREST
    out[grass & (speck > 0.95)] = KHAKI

    # forest floor, then tree canopies drawn back to front
    out[forest] = DEEP
    trees = []
    for _ in range(2600):
        x, y = rng.integers(0, size, 2)
        if forest[y, x] or (grass[y, x] and rng.random() < 0.08):
            trees.append((y, x, int(rng.integers(3, 6))))
    for y, x, r in sorted(trees):
        y0, y1 = max(0, y - r), min(size, y + r + 1)
        x0, x1 = max(0, x - r), min(size, x + r + 1)
        dy = yy[y0:y1, x0:x1] - y
        dx = xx[y0:y1, x0:x1] - x
        disc = dx * dx + dy * dy <= r * r + 1
        region = out[y0:y1, x0:x1]
        region[disc] = FOREST
        region[disc & (dx + dy < -r * 0.7)] = OLIVE
        region[disc & (dx + dy > r * 0.9)] = DEEP
        # a dark shadow to the lower right of each crown
        sy, sx = y0 + 1, x0 + 1
        shadow = out[sy:y1 + 1, sx:x1 + 1]
        ring = (dx * dx + dy * dy > r * r + 1) & (dx * dx + dy * dy <= (r + 1) ** 2)
        ring = ring[:shadow.shape[0], :shadow.shape[1]]
        shadow[ring & (shadow != FOREST) & (shadow != OLIVE)] = DEEP

    # water: deep centre, light shallows along the banks, ripples
    out[shore] = np.where(bayer[shore] < 0.5, BROWN, KHAKI)
    out[water] = BLUE                       # the blue army's colour
    shallows = water & dilate(~water, 2)
    out[shallows] = WATER_LIGHT
    ripples = water & ~shallows & (rng.random((size, size)) < 0.02)
    for y, x in zip(*np.nonzero(ripples)):
        out[y, x:x + 3][water[y, x:x + 3] & ~shallows[y, x:x + 3]] = WATER_LIGHT
    return out
