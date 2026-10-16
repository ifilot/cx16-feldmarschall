"""Check supplied PSG streams and actual banked ZSMKit playback in the game.

Exercises the title loop across bank boundaries, mute/re-enable, scene music,
effects, one-shot endings and silent fallback when an audio file is missing.
Runs in temporary runtime directories, preserving player saves.
"""
import re
import shutil
import tempfile
from pathlib import Path

from distribute import runtime_files
from test_colors import ROOT, start, choose
from test_flow import symbol, text
from test_variants import drag, position, new_match

PSG = 0x1F9C0


def decode(data, allowed_mask):
    assert data[:3] == b'zm\x01' and len(data) >= 17
    loop = int.from_bytes(data[3:6], 'little')
    mask = int.from_bytes(data[10:12], 'little')
    assert mask and not mask & ~allowed_mask
    assert data[6:10] == bytes(4), 'only PSG music is expected'
    assert int.from_bytes(data[12:14], 'little') == 60
    frames, loop_tick, pos = [[]], None, 16
    while True:
        if pos == loop:
            loop_tick = len(frames)-1
        command = data[pos]
        pos += 1
        if command < 64:
            assert allowed_mask & (1 << (command//4))
            frames[-1].append((command, data[pos]))
            pos += 1
        elif command == 64:
            count = data[pos] & 63
            pos += 1+count
        elif command == 128:
            break
        elif command > 128:
            frames.extend([] for _ in range(command & 127))
        else:
            raise AssertionError('unexpected FM commands')
        assert pos < len(data)
    assert not loop or loop_tick is not None
    if not frames[-1]:
        frames.pop()
    return frames, loop_tick, pos


def value(session, name, length=1):
    data = session.emu.read_memory(symbol(name), length)
    return int.from_bytes(data, 'little')


def registers(session):
    return session.emu.read_memory(PSG, 64, space='vram')


def sounding(state, first=0, last=16):
    return any(state[voice*4+2] & 63 for voice in range(first, last))


def bank_file(session, file, bank):
    data = (ROOT / 'src' / file).read_bytes()
    for offset in range(0, len(data), 8192):
        expected = data[offset:offset+8192]
        actual = session.emu.read_memory(0, len(expected), space='banked_ram', bank=bank+offset//8192)
        assert actual == expected, f'{file}: wrong banked data at bank {bank+offset//8192}'


def title_loop(session):
    # Restart the title through the actual sound toggle, then compare hardware
    # registers with decoded supplied music for longer than a complete loop.
    session.emu.request('breakpoint', address=symbol('sound_scene'))
    choose(session, '4')
    caller_bank = session.emu.read_memory(0, 1)
    session.emu.request('breakpoint', action='remove', address=symbol('sound_scene'))
    session.emu.advance(180)
    assert text(session, 55, 0, 53) == 'CLICK A PROFILE TO PREVIEW'
    choose(session, 'S')
    assert value(session, 'sound_music_enabled') == 1, 'appearance still toggles sound'
    choose(session, 'Escape')
    choose(session, '6')
    choose(session, 'Escape')
    choose(session, '2')
    assert value(session, 'sound_music_enabled') == 0 and not sounding(registers(session)), (value(session, 'sound_music_enabled'), text(session, 21, 7, 40), text(session, 28, 7, 40))
    choose(session, '2')
    # Capture the hardware immediately before the title starts. A pressed
    # button now animates first; unrelated old frequency values may change
    # while the game track resumes, even on voices the title never uses.
    entry = symbol('sound_music')
    session.emu.request('breakpoint', address=entry)
    session.emu.request('key', key='4', down=True)
    assert session.emu.advance(180)['reason'] == 'breakpoint'
    session.emu.request('key', key='4', down=False)
    initial = registers(session)
    session.emu.request('breakpoint', action='remove', address=entry)
    session.emu.advance(3)
    frames, loop, _ = decode((ROOT / 'src/TITLE.ZSM').read_bytes(), 0x0FFF)
    assert loop is not None and (ROOT / 'src/TITLE.ZSM').stat().st_size > 16384
    ref, state, tick = [], bytearray(initial), 0
    for _ in range(len(frames)+160):
        if tick == len(frames):
            tick = loop
        for register, byte in frames[tick]:
            state[register] = byte
        ref.append(bytes(state[:48]))
        tick += 1
    assert value(session, 'sound_music_enabled') == 1
    actual = registers(session)[:48]
    cursor = next(i for i in range(30) if ref[i] == actual)
    transients = consecutive = 0
    for frame in range(len(frames)+60):
        session.emu.advance(1)
        actual = registers(session)[:48]
        order = [cursor+1, cursor+2, cursor]+list(range(cursor+3, cursor+7))
        match = next((i for i in order if i < len(ref) and actual == ref[i]), None)
        if match is None:
            # ZSMKit v1 can split a dense tick at the loop point over two
            # frames; use the same bounded allowance as its upstream verifier.
            transients += 1
            consecutive += 1
            assert transients <= 4 and consecutive <= 2, f'title playback diverged at frame {frame}, reference tick {cursor}'
            continue
        consecutive = 0
        cursor = match
    assert cursor >= len(frames), 'title loop was not reached'
    print(f'title: {cursor} reference ticks checked across banks and loop ({transients} split-tick samples)')
    # A short effect must use voices 12..15 and leave the music running.
    session.press('Up')
    assert value(session, 'sound_last_sfx', 2) == SFX['MENU_MOVE']
    assert sounding(registers(session), 12, 16), 'menu sound never reached the PSG'
    assert sounding(registers(session), 0, 12), 'effect interrupted background music'
    session.emu.advance(30)
    assert not sounding(registers(session), 12, 16), 'effect failed to stop'
    return caller_bank


def independent_audio(session):
    choose(session, '6')
    choose(session, 'Escape')
    choose(session, '3')  # effects off, music on
    assert value(session, 'sound_effects_enabled') == 0
    assert value(session, 'sound_music_enabled') == 1
    assert sounding(registers(session), 0, 12)
    session.press('Down')
    assert not sounding(registers(session), 12, 16)
    choose(session, '2')  # both off
    assert value(session, 'sound_music_enabled') == 0
    assert not sounding(registers(session))
    choose(session, '3')  # effects only
    session.press('Up')
    assert value(session, 'sound_music_enabled') == 0
    assert sounding(registers(session), 12, 16)
    assert not sounding(registers(session), 0, 12)
    session.press('2')  # music on; current effect keeps playing
    session.emu.advance(2)  # allow the first PSG tick after the press animation
    assert value(session, 'sound_music_enabled') == 1
    assert value(session, 'sound_effects_enabled') == 1
    assert sounding(registers(session), 0, 12)
    assert sounding(registers(session), 12, 16)
    choose(session, '4')


def battle_effects(session):
    # Restore the normal menu after developer result scenarios.
    choose(session, 'Escape')
    for effect, attacker, defender in (('BOMB', 0, 0x1A), ('DEFUSE', 7, 0x1A),
                                       ('SPY', 9, 0x10), ('BATTLE_WON', 0, 0x16),
                                       ('BATTLE_LOST', 6, 0x10), ('BATTLE_TIE', 6, 0x16)):
        new_match(session, '')  # Classic rules, with ordinary equal-rank ties.
        position(session, {60: attacker, 50: defender})
        drag(session, 60, 50, wait=5)
        assert value(session, 'sound_last_sfx', 2) == SFX['ATTACK']
        session.emu.advance(70)  # Outcome sounds play as the loser starts falling.
        assert value(session, 'sound_last_sfx', 2) == SFX[effect], f'{effect}: wrong battle sound'
        heard = sounding(registers(session), 12, 16)
        # Defuse deliberately has rests between its snips; sample a window.
        for _ in range(20):
            if heard:
                break
            session.emu.advance(1)
            heard = sounding(registers(session), 12, 16)
        assert heard, f'{effect}: PSG effect voices are silent'
        session.emu.advance(320)
    new_match(session, '')
    position(session, {60: 8})
    drag(session, 60, 20, wait=5)
    assert value(session, 'sound_last_sfx', 2) == SFX['SCOUT']
    session.emu.advance(320)
    new_match(session, '')
    position(session, {60: 6, 9: 0x16})
    drag(session, 60, 50, wait=5)
    assert value(session, 'sound_last_sfx', 2) == SFX['MOVE']
    session.emu.advance(60)
    assert value(session, 'sound_last_sfx', 2) == SFX['MOVE_CPU']


SFX = {name: int(offset, 16) for name, offset in re.findall(
    r'#define SFX_(\w+)\s+0x([0-9A-Fa-f]+)', (ROOT / 'assets/sound/psg/sfx.h').read_text())
    if not name.startswith('BANK_')}


def main():
    music_header = (ROOT / 'src/music.h').read_text()
    songs = {name: int(bank) for name, bank in re.findall(r'#define MUSIC_(\w+)_BANK\s+(\d+)', music_header)}
    songs.pop('FIRST', None)
    songs.pop('LAST', None)
    for name in songs:
        data = (ROOT / 'src' / (name+'.ZSM')).read_bytes()
        _, loop, used = decode(data, 0x0FFF)
        assert used == len(data)
        assert (loop is None) == (name in ('VICTORY', 'DEFEAT'))
    blob = (ROOT / 'src/SFX.BIN').read_bytes()
    assert len(blob) <= 8192
    for offset in SFX.values():
        _, loop, _ = decode(blob[offset:], 0xF000)
        assert loop is None
    with tempfile.TemporaryDirectory(prefix='feldmarschall-sound-') as tmp:
        directory = Path(tmp)
        for file in runtime_files():
            shutil.copyfile(ROOT / 'src' / file, directory / file)
        session = start(directory)
        try:
            assert value(session, 'sound_ready') == 1
            assert value(session, 'sound_music_bank') == songs['TITLE']
            for name, bank in songs.items():
                bank_file(session, name+'.ZSM', bank)
            bank_file(session, 'SFX.BIN', 2)
            bank_file(session, 'PLAY.BIN', 22)
            bank_file(session, 'AI.BIN', 23)
            bank_file(session, 'MISSION.BIN', 24)
            caller_bank = title_loop(session)
            independent_audio(session)
            choose(session, '1')
            assert value(session, 'sound_music_bank') == songs['DEPLOY']
            choose(session, 'R')
            assert value(session, 'sound_last_sfx', 2) == SFX['RANDOM']
            choose(session, 'Escape')
            for key in 'DEV':
                session.press(key)
            session.emu.advance(30)
            for key, move, outcome in (('1', None, 'DEFEAT'), ('2', (64, 54), 'VICTORY'),
                                        ('3', (64, 54), 'DRAW')):
                choose(session, key)
                if move:
                    drag(session, *move, wait=400)
                else:
                    session.emu.advance(400)
                assert value(session, 'sound_music_bank') == (0 if outcome == 'DRAW' else songs[outcome]), (key, outcome, value(session, 'sound_music_bank'), text(session, 9), text(session, 42, 20, 40))
                session.emu.advance(500)
                assert not sounding(registers(session)), f'{outcome}: result did not fall silent'
                choose(session, '2')
                assert not sounding(registers(session), 0, 12), 'viewing final board restarted music'
                # Inspect at the unbanked scene boundary, rather than sampling
                # during an IRQ that legitimately selects the sound state bank.
                session.emu.request('breakpoint', address=symbol('sound_scene'))
                choose(session, 'Escape')
                assert session.emu.read_memory(0, 1) == caller_bank, 'scene gateway leaked its RAM bank'
                session.emu.request('breakpoint', action='remove', address=symbol('sound_scene'))
                session.emu.advance(180)
                assert value(session, 'sound_music_bank') == songs['TITLE']
            battle_effects(session)
        finally:
            session.close()
        # Optional audio failure must not prevent loading the mandatory code banks.
        (directory / 'SFX.BIN').unlink()
        session = start(directory)
        try:
            assert value(session, 'sound_ready') == 0 and text(session, 55, 0, 53) == 'CHOOSE AN OPTION', f"missing audio: ready={value(session, 'sound_ready')}, menu={text(session, 11)!r}"
            for key in 'DEV':
                session.press(key)
            choose(session, '1')
            session.emu.advance(400)
            assert text(session, 42, 20, 40) == 'YOU HAVE NO MOVES LEFT'
        finally:
            session.close()
    print('sound: all assets/banks verified, reference-checked PSG title loop, battle effects, mute, scene music, one-shot results and silent fallback passed')


if __name__ == '__main__':
    main()
