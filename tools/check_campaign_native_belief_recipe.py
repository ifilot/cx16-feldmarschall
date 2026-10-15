"""Qualify an unpublished native-belief recipe in a minimal portable runtime."""
import copy
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
from unittest.mock import patch
import zipfile

from ai_registry import ROOT,build_native_beliefs,get_policy
from feldmarschall import Engine
from information_strategy_cycle import digest
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


def check():
    with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:game=saved.game(9)
    states,_=replay(game);events=public_events(game,states)
    reports=[]
    for mode in ('counts','joint'):
        original=get_policy(f'student-{mode}-belief-objectives-v2-normal')
        spec=copy.deepcopy(original);spec['defines'].append('AI_DIAGNOSTICS')
        spec['id']=f'provisional-{mode}-beliefs-v3-normal'
        with tempfile.TemporaryDirectory(prefix='qualify-native-beliefs-') as tmp:
            source=Path(tmp)/'source';source.mkdir();runtime=Path(tmp)/'runtime';runtime.mkdir()
            with zipfile.ZipFile(ROOT/original['archive']) as archive:archive.extractall(source)
            program=runtime/'engine'
            command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow',
                     f'-DFELDMARSCHALL_AI_ID="{spec["id"]}"','-Isrc/core','-o',str(program),
                     *['-D'+define for define in spec['defines']],*spec['sources']]
            subprocess.run(command,cwd=source,check=True,capture_output=True)
            files=build_native_beliefs(source,runtime,program,spec)
            identity=subprocess.run([str(program),'--identity'],cwd=tmp,capture_output=True,text=True,check=True)
            assert identity.stdout.strip()==spec['id']
            cases=[]
            for army in (0,1):
                with patch('feldmarschall.ROOT',Path(tmp)):bot=Engine(shlex.quote(str(program)))
                try:
                    setup=game[('red_setup','blue_setup')[army]]
                    for line in ['new '+('red','blue')[army],'rules 0','seed 1729','setup '+setup]:bot.send(line)
                    initial=bot.ask('go','move');assert len(initial.split())==2
                    for event in events[:80]:bot.send(event)
                    later=bot.ask('go','move');assert len(later.split())==2
                    public=bot.ask('public','public').split();assert int(public[0])==army
                    for cell in bytes.fromhex(public[1]):
                        if cell<254 and bool(cell&16)!=bool(army) and not cell&32:assert cell&15==12
                    for line in ['new '+('red','blue')[army],'seed 1729','setup '+setup]:bot.send(line)
                    assert bot.ask('go','move')==initial
                    bot.send('new '+('red','blue')[army]);bot.send('seed 1729')
                    generated=bot.ask('setup','setup');assert len(generated)==40
                    assert len(bot.ask('go','move').split())==2
                    cases.append(dict(army=army,initial=initial,after80=later,reset_repeats=True,bare_setup_passed=True))
                finally:bot.close()
            reports.append(dict(mode=mode,provisional_identity=spec['id'],registered=False,
                source_archive_sha256=original['source_sha256'],defines=spec['defines'],cases=cases,
                minimal_runtime_sha256={name:digest(runtime/name) for name in files}))
    return dict(passed=True,scope='Unpublished v2+AI_DIAGNOSTICS recipe, fresh compiled native observer and frozen minimal runtime/model; process cwd outside checkout.',
                test_source_sha256=digest(Path(__file__)),recipes=reports)


if __name__=='__main__':
    report=check()
    directory=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-15-native-belief-objectives-v2'
    (directory/'provisional-v3-portable-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
