"""Original DOS deployment through unmodified overlay6 machine instructions.

This research generator uses no opponent setup and performs no move selection.
The caller must keep its deployment RNG seed private from the honest opponent.
Returning a setup to the existing DOS adapter does NOT carry the resulting RNG
state into play: that adapter separately seeds its move engine. Report that
benchmark boundary until a separately registered continuation version exists.
"""
import hashlib
from pathlib import Path
import struct

from feldmarschall import GLYPHS, valid_setup
from msdos1990 import OriginalCPU, LOAD, OVERLAY, FELD_RANK

SOURCE_COMMIT = '306e3cb757137f3c28d1224ee3d2c4570f412509'
EXPECTED = {
    'resident-image.bin':'cd8c40e2f305f2bd3656b35aa31e7baa55535db19b745e307d98e43d7ca1904f',
    'mz-header.bin':'99beff6347a4c55c8c8fa50a71c76cc6e424d7445e7eefff3c9532f031a90a99',
    'ovl6.cod':'51276baf4fc81a427731c3bdfc6f519c30659f27892bb7d8bd6d0b6e6d87c4b8',
    'ovl6.rel':'c1635b9e54df94ef9f13f5e4d2298a24522590bf4c4e77414abd32a86f61cd3e',
}
ORIGINAL_COUNTS = (1,1,1,2,3,4,4,4,5,8,1,6)
TEMPLATE_OFFSET = 0x190e
RNG_MULTIPLIER = 0x015a4e35


def rng_next(state):
    state = (state*RNG_MULTIPLIER+1)&0xffffffff
    return state,(state>>16)&0x7fff


def load_assets(source_assets, setup_assets=None):
    """Verify the fixed original assets; never modify them or their manifest."""
    source_assets = Path(source_assets)
    setup_assets = source_assets if setup_assets is None else Path(setup_assets)
    data = {}
    for name,sha in EXPECTED.items():
        path = (setup_assets if name.startswith('ovl6.') else source_assets)/name
        contents = path.read_bytes()
        if hashlib.sha256(contents).hexdigest() != sha:
            raise ValueError('original deployment asset integrity failure: '+name)
        data[name] = contents
    return data


def templates(source_assets, setup_assets=None):
    """Eight original 40-byte rank layouts from resident DS:190E..1A4D."""
    resident = load_assets(source_assets,setup_assets)['resident-image.bin']
    offset = 0x1fe5*16+TEMPLATE_OFFSET
    rows = [list(resident[offset+40*i:offset+40*(i+1)]) for i in range(8)]
    if any(len(row)!=40 or any(row.count(rank)!=count for rank,count in enumerate(ORIGINAL_COUNTS)) for row in rows):
        raise ValueError('original opening table inventory invalid')
    return rows


def _cpu(source_assets, data):
    # The existing CPU supplies the exact resident relocation/real-mode ABI.
    # Its overlay5 image is replaced only inside this fresh SETUP-only address
    # space; no OriginalAI or move-engine instance is touched.
    cpu = OriginalCPU(source_assets)
    overlay = bytearray(data['ovl6.cod']); relocations = data['ovl6.rel']
    count = struct.unpack_from('<H',relocations)[0]
    if len(relocations) != 2+4*count:
        raise ValueError('invalid original setup relocation table')
    for index in range(count):
        offset,segment = struct.unpack_from('<HH',relocations,2+4*index)
        if segment != 0x0d90 or offset+2 > len(overlay):
            raise ValueError('unsupported original setup relocation')
        value = struct.unpack_from('<H',overlay,offset)[0]
        struct.pack_into('<H',overlay,offset,(value+LOAD)&65535)
    cpu.uc.mem_write(OVERLAY*16,bytes(overlay))
    return cpu


def generate_setup(source_assets, seed, level=3, setup_assets=None):
    """Return (front-first 40-glyph army, private audit) from an exact RNG state.

    `seed` is a 32-bit resident RNG state, not a public game/move seed. Original
    computer physical rows1..4 are back→front; the returned canonical string
    reverses rows, retaining columns1..10 (the original top/Blue orientation).
    Horizontal reflection belongs to the original randomized generator itself.
    """
    if type(seed) is not int or not 0<=seed<=0xffffffff:
        raise ValueError('private unsigned32 deployment RNG state required')
    if type(level) is not int or not 1<=level<=5:
        raise ValueError('original difficulty1..5 required')
    data = load_assets(source_assets,setup_assets)
    cpu = _cpu(source_assets,data)
    cpu.put_word(0x3e90,level)
    cpu.put_word(0x3544,seed&65535); cpu.put_word(0x3546,seed>>16)
    # Original far-Pascal initializer; low argument byte0 skips the HUMAN
    # lower-board template. Original computer placement always runs first.
    cpu.call(0x1ddd,(0,))
    ranks = []
    for row in range(1,5):
        for col in range(1,11):
            cell = cpu.read(0x3e9c+72*row+6*col,6)
            rank = struct.unpack_from('<H',cell,2)[0]
            if cell[0]!=1 or cell[5]!=0 or rank>=12:
                raise ValueError('original deployment returned an empty/invalid own square')
            ranks.append(rank)
    if any(ranks.count(rank)!=count for rank,count in enumerate(ORIGINAL_COUNTS)):
        raise ValueError('original deployment returned an invalid inventory')
    setup = ''.join(GLYPHS[FELD_RANK[rank]] for row in range(3,-1,-1) for rank in ranks[10*row:10*(row+1)])
    if not valid_setup(setup):
        raise ValueError('original deployment is not a legal Classic army')
    post_rng = cpu.word(0x3544)|(cpu.word(0x3546)<<16)
    state,first = rng_next(seed)
    table_branch = (level in (3,5) and first%5!=0) or (level==4 and first%5==0)
    table_index = mirrored = None
    if table_branch:
        state,which = rng_next(state); state,mirror = rng_next(state)
        table_index = which%4+(4 if level<=3 else 0)
        mirrored = bool(mirror%2)
    return setup,dict(source_commit=SOURCE_COMMIT,level=level,pre_rng_state=seed,post_rng_state=post_rng,
        physical_ranks=ranks,branch='original-template' if table_branch else 'original-procedural',
        template_index=table_index,mirrored=mirrored,
        assets_sha256=EXPECTED.copy(),table_bytes_sha256=hashlib.sha256(
            data['resident-image.bin'][0x1fe5*16+TEMPLATE_OFFSET:0x1fe5*16+TEMPLATE_OFFSET+320]).hexdigest(),
        execution='Unchanged overlay6:1DDD ->1D1A ->0C7B, original helpers and resident RNG; no UI or enemy setup.',
        canonical_orientation='front-first physical rows4..1, columns1..10; original computer top/Blue',
        move_rng_boundary='Existing DOS adapter reseeds move AI independently; post-deployment RNG is returned but not installed by this generator.')
