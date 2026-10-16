"""Build a private diagnostic observer and verify its choices against the release.

This is not a selectable policy and never overwrites the registered executable.
"""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT, get_policy
from feldmarschall import Engine
from tournament_store import Tournament, replay
from test_information_parent_parity import public_events


def main():
    spec = get_policy('production-fortress-template-q24-cache-v1-normal')
    out = ROOT/'build/ai-release-observer'
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-observer-') as temporary:
        source = Path(temporary)
        with zipfile.ZipFile(ROOT/spec['archive']) as archive:
            archive.extractall(source)
        engine = source/'src/native/engine.c'
        text = engine.read_text()
        needle = '} else if(!strcmp(command, "seed")) {'
        assert text.count(needle) == 1
        addition = ('} else if(!strcmp(command, "fixture-rng")) {'
                    ' printf("rng %u\\n",random_current());fflush(stdout);'
                    ' } else if(!strcmp(command, "fixture-cache")) {'
                    ' printf("cache %u\\n",ai_template_test_cache_hit());fflush(stdout); '+needle)
        engine.write_text(text.replace(needle, addition))
        (out/'probe-engine.c').write_text(engine.read_text())
        command = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-Wno-format-overflow',
                   '-Isrc/core', '-DAI_TEST', '-DAI_DIAGNOSTICS']
        command += ['-D'+flag for flag in spec['defines']]
        command += ['-o', str(out/'observer'), *spec['sources']]
        subprocess.run(command, cwd=source, check=True, capture_output=True)
    with Tournament(ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour') as saved:
        game = saved.game(9)
    states, _ = replay(game)
    events = public_events(game, states)
    records = []
    for side in (0, 1):
        paths = [ROOT/'build/ai-catalog'/spec['id']/'engine', out/'observer']
        bots = [Engine(shlex.quote(str(path))) for path in paths]
        try:
            for bot in bots:
                commands = ['new '+('red', 'blue')[side], 'rules 0', 'difficulty normal',
                            'seed 71943', 'setup '+game[('red_setup', 'blue_setup')[side]]]
                for command in commands:
                    bot.send(command)
            for ply, event in enumerate(events[:160]):
                if ply % 2 == side:
                    moves = [bot.ask('go', 'move') for bot in bots]
                    assert moves[0] == moves[1], (side, ply, moves)
                    records.append(dict(side=side, ply=ply, move=moves[0]))
                for bot in bots:
                    bot.send(event)
        finally:
            for bot in bots:
                bot.close()
    receipt = dict(passed=True, scope='Private read-only diagnostics; frozen candidate source '
                   'and unchanged policy defines plus AI_TEST/AI_DIAGNOSTICS. Not a strength policy.',
                   frozen_policy=spec, source_sha256=spec['source_sha256'],
                   observer_sha256=hashlib.sha256((out/'observer').read_bytes()).hexdigest(),
                   probe_source_sha256=hashlib.sha256((out/'probe-engine.c').read_bytes()).hexdigest(),
                   choices=records)
    (out/'qualification.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Matched observer choices:', len(records), flush=True)


if __name__ == '__main__':
    main()
