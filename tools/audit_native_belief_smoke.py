"""Audit the two-game native-belief DOS smoke, full replays and public views."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

from ai_registry import ROOT,build_policy,get_policy,receives_opponent_setup
from feldmarschall import COUNTS,Engine,LAKES
from information_strategy_cycle import digest
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay,verify

POLICY='student-joint-belief-objectives-v3-normal'
DIRECTORY=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-16-native-belief-objectives-v3'


def audit():
    path=DIRECTORY/'smoke.fmtour';summary=verify(path)
    assert summary['status']=='complete' and summary['games']==2 and summary['errors']==0
    policy=get_policy(POLICY);assert not receives_opponent_setup(policy)
    program,receipt=build_policy(POLICY);native_states=public_states=concealed_checks=0;rows=[]
    with Tournament(path) as saved,tempfile.TemporaryDirectory(prefix='audit-native-smoke-') as tmp:
        metadata=saved.metadata()
        assert metadata['families']==['uniform'] and metadata['rounds']==1 and metadata['seed']==2399981
        assert metadata['backend']=='openmp' and metadata['rules']=='classic' and metadata['max_plies']==1000
        assert [p['policy']['id'] for p in metadata['participants']]==[POLICY,'msdos-1990-v2-normal']
        games=[saved.game(row['id']) for row in saved.games()]
        for game in games:
            states,_=replay(game);request=Path(tmp)/'game.json';request.write_text(json.dumps(game))
            result=subprocess.run([str(ROOT/'build/desktop/feldmarschall-tournament-worker'),'--replay',str(request)],
                capture_output=True,text=True,check=True,timeout=30)
            assert json.loads(result.stdout)['states']==states;native_states+=len(states)
            army=int(game['blue']==POLICY);bot=Engine(shlex.quote(str(program)))
            try:
                for command in ['new '+('red','blue')[army],'rules 0','difficulty normal',
                                'setup '+game[('red_setup','blue_setup')[army]]]:bot.send(command)
                events=public_events(game,states)
                for ply,state in enumerate(states):
                    side,board,lost,_=bot.ask('public','public').split();assert int(side)==army
                    cells=list(bytes.fromhex(board));expected_lost=COUNTS[:]
                    for square,actual in enumerate(state):
                        if actual is None:assert cells[square]==(254 if square in LAKES else 255)
                        else:
                            owner,rank,moved,revealed=actual
                            assert bool(cells[square]&16)==bool(owner)
                            if owner!=army:expected_lost[rank]-=1
                            permitted=owner==army or revealed
                            assert cells[square]&15==(rank if permitted else 12)
                            assert bool(cells[square]&32)==bool(revealed)
                            if not permitted:concealed_checks+=1
                    assert bytes(expected_lost).hex()==lost;public_states+=1
                    if ply<len(events):bot.send(events[ply])
            finally:bot.close()
            rows.append(dict(id=game['id'],army=army,plies=game['plies'],result=game['result'],reason=game['reason']))
        chosen=next((g for g in games if g['result']==('red' if g['red']==POLICY else 'blue')),games[0])
        capture=subprocess.run([str(ROOT/'build/desktop/feldmarschall-desk'),'--capture-review',str(path),
            '--match',str(chosen['id']),'--ply',str(chosen['plies']),'--screenshot',str(DIRECTORY/'smoke.png')],
            env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),capture_output=True,text=True,timeout=30)
        (DIRECTORY/'smoke-review.log').write_text(capture.stdout+capture.stderr);capture.check_returncode()
    return dict(passed=True,kind='Runtime smoke only; two games are not strength evidence.',summary=summary,games=rows,
        native_replayed_states=native_states,frozen_runtime_public_states_checked=public_states,
        concealed_enemy_rank_nibbles_checked=concealed_checks,receives_opponent_setup=False,
        tournament_sha256=digest(path),screenshot_sha256=digest(DIRECTORY/'smoke.png'),
        policy_source_sha256=policy['source_sha256'],runtime_sha256=receipt['runtime_sha256'],
        audit_source_sha256=digest(Path(__file__)))


if __name__=='__main__':
    result=audit();(DIRECTORY/'smoke-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
