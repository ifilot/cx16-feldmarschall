"""Controlled 65C02/native decision parity and cost on public screening views."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from ai_registry import ROOT
from analyze_template_conversion import POLICY, SOURCE
from campaign_template_beliefs import TemplateMixtureBeliefs
from feldmarschall import LAKES
from test_compact_backrow import FLAGS, SOURCES
from test_information_parent_parity import public_events
from tournament_store import Tournament, replay

OUT = ROOT/'docs/ai-honest-campaign-2026-10-15/research/compact-backrow-native-v1'

HARNESS = '''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ai.h"
#include "board.h"
#include "random.h"
#include "rules.h"
@@FIXTURES@@
int main(int argc,char**argv) {
    unsigned fixture=argc>1?atoi(argv[1]):0;
    uint8_t from,to;
    if(fixture>=sizeof(armies)) return 2;
    memcpy(board,views[fixture],100);
    game_rules=0;ai_difficulty=AI_NORMAL;rules_reset();ai_reset();random_seed(32199);
    ai_move(armies[fixture],losses[fixture],&from,&to);
    printf("%u %u %u\\n",(unsigned)from,(unsigned)to,(unsigned)random_next());
    return 0;
}
'''


def main():
    assert not (OUT/'cycles.json').exists()
    source_before = {str(p.relative_to(ROOT/'src')): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (ROOT/'src').rglob('*') if p.is_file()}
    views = []
    with Tournament(SOURCE) as saved:
        for army in (0, 1):
            rows = [row for row in saved.games() if row[('red', 'blue')[army]] == POLICY and row['plies'] > 240][:3]
            assert len(rows) == 3
            for row in rows:
                game = saved.game(row['id'])
                states, _ = replay(game)
                events = public_events(game, states)
                model = TemplateMixtureBeliefs()
                model.observe(['new', ('red', 'blue')[army]])
                model.observe(['setup', game[('red_setup', 'blue_setup')[army]]])
                for ply, event in enumerate(events[:202]):
                    if ply in (army, 80+army, 200+army):
                        cells = [254 if sq in LAKES else 255 if c is None else
                                 c[0]*16 | (c[1] if c[0] == army or c[3] else 12) | int(c[2])*64 | int(c[3])*32
                                 for sq, c in enumerate(states[ply])]
                        views.append(dict(game=game['id'], ply=ply, army=army*16, cells=cells, lost=model.lost[:]))
                    model.observe(event.split())
    assert len(views) == 18
    fixtures = 'static const unsigned char views[18][100]={'+','.join('{'+','.join(map(str, v['cells']))+'}' for v in views)+'};\n'
    fixtures += 'static const unsigned char losses[18][12]={'+','.join('{'+','.join(map(str, v['lost']))+'}' for v in views)+'};\n'
    fixtures += 'static const unsigned char armies[18]={'+','.join(str(v['army']) for v in views)+'};\n'
    records = []
    commands = []
    with tempfile.TemporaryDirectory(prefix='compact-backrow-cycle-cost-') as tmp:
        temp = Path(tmp)
        (temp/'harness.c').write_text(HARNESS.replace('@@FIXTURES@@', fixtures))
        (OUT/'cost-fixtures.json').write_text(json.dumps(views, indent=2)+'\n')
        (OUT/'cost-harness.c').write_bytes((temp/'harness.c').read_bytes())
        shutil.copytree(ROOT/'src/core', temp/'core', ignore=shutil.ignore_patterns('*.o', '*.s'))
        for variant, extra in [('baseline', []), ('compact', ['AI_BACKROW_PRIOR'])]:
            flags = ['-D'+f for f in FLAGS+extra]
            sim = temp/(variant+'.sim')
            native = temp/(variant+'.native')
            # cl65 puts intermediate objects beside its source inputs.
            core = [str(temp/'core'/f'{s}.c') for s in SOURCES]
            for command in [
                ['cl65', '-O', '-t', 'sim65c02', '-I', str(temp/'core'), *flags, '-o', str(sim), str(temp/'harness.c'), *core],
                ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas', '-I', str(temp/'core'), *flags, '-o', str(native), str(temp/'harness.c'), *core]]:
                result = subprocess.run(command, cwd=temp, capture_output=True, text=True)
                commands.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
                assert result.returncode == 0, result.stderr
            for index, view in enumerate(views):
                a = subprocess.run(['sim65', '-c', str(sim), str(index)], cwd=temp, capture_output=True, text=True, check=True)
                b = subprocess.run([str(native), str(index)], cwd=temp, capture_output=True, text=True, check=True)
                output = a.stdout+a.stderr
                cycles = re.search(r'(\d+)\s+cycles', output, re.I)
                assert cycles, output
                move = re.search(r'^(\d+ \d+ \d+)$', output, re.M)
                assert move and move[1] == b.stdout.strip(), (variant, index, output, b.stdout)
                records.append(dict(variant=variant, index=index, game=view['game'], ply=view['ply'],
                                    army=view['army'], cycles=int(cycles[1]), native_sim_move_rng=move[1]))
    deltas = [records[18+i]['cycles']-records[i]['cycles'] for i in range(18)]
    assert source_before == {str(p.relative_to(ROOT/'src')): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (ROOT/'src').rglob('*') if p.is_file()}
    report = dict(scope='18fixed public screening views, fresh AI history/reset per view. Actual C evaluator; simulated65C02 flat memory. Not a strength test or bank-switch timing measurement.',workspace_src_unchanged=True,
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  ai_source_sha256=hashlib.sha256((ROOT/'src/core/ai.c').read_bytes()).hexdigest(),
                  native_sim_decision_and_rng_matches=36, commands=commands, records=records,
                  mean_added_cycles=sum(deltas)/len(deltas), minimum_added_cycles=min(deltas), maximum_added_cycles=max(deltas),
                  mean_added_ms_at_assumed_8MHz=sum(deltas)/len(deltas)/8000,
                  caveat='Cycle totals include common fixture loading, resets, printing and RNG read. Paired differences isolate changed execution on identical public views, but different selected moves can change internal work. Real banked execution is separately checked.')
    (OUT/'cycles.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('records', 'commands')}, indent=2))


if __name__ == '__main__':
    main()
