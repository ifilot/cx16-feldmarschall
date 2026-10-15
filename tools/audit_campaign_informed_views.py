"""Reconstruct every informed-opponent audit view from sampled public history.

The privileged values in this checker belong to the sampled hypothetical army,
not the real opponent setup. They verify isolation; they never choose a move.
"""
import hashlib
import json
from pathlib import Path
import random
import subprocess
import tempfile
import zipfile

from ai_registry import ROOT,build_policy,get_policy
from feldmarschall import Engine,battle,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay
from train_ai_student import sample_world


def view(cells,army,root):
    result=[]
    for cell in cells:
        informed=(cell<254 and army!=root and bool(cell&16)==bool(root) and cell&15 in (9,11))
        if informed:cell|=32
        elif cell<254 and bool(cell&16)!=bool(army) and not cell&32:cell=(cell&~15)|12
        result.append(cell)
    return bytes(result)


def observed_world(initial,path):
    cells=list(initial)
    for index in range(0,len(path),5):
        src,dst,attacker,defender,outcome=path[index:index+5]
        a,d=cells[src],cells[dst]
        assert a<254
        distance=abs(src//10-dst//10)+abs(src%10-dst%10)
        assert attacker==((a&15) if d<254 or distance>1 else 255)
        assert defender==((d&15) if d<254 else 255)
        if d<254:
            expected={'attacker':0,'defender':1,'both':2}[battle(a&15,d&15)]
            a|=32;d|=32
        else:
            expected=3
            if distance>1:a|=32
        assert outcome==expected
        cells[src]=255
        cells[dst]=a|64 if outcome in (0,3) else 255 if outcome==2 else d
    return cells


def run():
    folder=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon'
    destination=folder/'informed-opponent-view-audit.json'
    assert not destination.exists(),'preserve completed audit'
    mechanism_path=folder/'informed-opponent-mechanism.json'
    mechanism=json.loads(mechanism_path.read_text())
    source=ROOT/mechanism['source']
    targets={}
    for row in mechanism['roots']:
        targets.setdefault((row['game'],row['army']),{})[row['ply']]=row['public_sha256']
    policy=get_policy('teacher-context-v1-normal')
    executable,_=build_policy(policy['id'])
    counts=dict(roots=0,worlds=0,decisions=0,root_decisions=0,opponent_decisions=0,
                public_trajectory_events=0,opponent_private_flag_spy_grants=0)
    checksum=hashlib.sha256()
    with tempfile.TemporaryDirectory(prefix='informed-history-audit-') as temp:
        temp=Path(temp)
        with zipfile.ZipFile(ROOT/policy['archive']) as archive:archive.extractall(temp/'source')
        (temp/'source/src/native/teacher_rollout.c').write_bytes((ROOT/'src/native/teacher_rollout.c').read_bytes())
        program=temp/'teacher'
        command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Isrc/core','-o',str(program)]
        command+=['-D'+define for define in policy['teacher_defines']+['AI_ROLLOUT_INFORMED_OPPONENT']]
        command+=policy['teacher_sources']
        subprocess.run(command,cwd=temp/'source',capture_output=True,check=True)
        teacher=subprocess.Popen([str(program),'--audit','--strategic','--context'],stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,text=True,bufsize=1)
        observer=Engine(str(executable.parent/'observer'))
        try:
            with Tournament(source) as tournament:
                for game_id,root in sorted(targets):
                    game=tournament.game(game_id);states,_=replay(game);events=public_events(game,states)
                    seed=game['seed']*2+root+1;rng=random.Random(seed)
                    for command in ('new '+('red','blue')[root],'rules 0','difficulty normal',
                                    'seed '+str(seed),'setup '+game[('red_setup','blue_setup')[root]]):observer.send(command)
                    selected=targets[(game_id,root)]
                    for ply,event in enumerate(events[:max(selected)+1]):
                        if ply%2==root:
                            if ply in selected:
                                public=observer.ask('public','public')
                                assert hashlib.sha256(public.encode()).hexdigest()==selected[ply]
                                _,board,lost,shuttle=public.split();cells=list(bytes.fromhex(board))
                                histories={sq:list(map(int,observer.ask('memory '+square_name(sq),'history').split()))
                                    for sq,cell in enumerate(cells) if cell<254 and bool(cell&16)!=bool(root) and not cell&32}
                                context=observer.ask('strategy','strategy')
                                for sample in range(8):
                                    world,_=sample_world(cells,list(bytes.fromhex(lost)),histories,rng,root)
                                    teacher.stdin.write(f'search {root} 4 {bytes(world).hex()} {shuttle} {context}\n');teacher.stdin.flush()
                                    while True:
                                        line=teacher.stdout.readline();words=line.split()
                                        assert words,'native audit stopped'
                                        assert words[0]!='error',words
                                        if words[0]=='done':break
                                        if words[0]!='decision':continue
                                        army=int(words[1]);path=b'' if words[5]=='-' else bytes.fromhex(words[5])
                                        expected=view(observed_world(world,path),army,root)
                                        assert bytes.fromhex(words[4])==view(world,army,root)
                                        assert bytes.fromhex(words[6])==expected
                                        counts['decisions']+=1
                                        counts['root_decisions' if army==root else 'opponent_decisions']+=1
                                        counts['public_trajectory_events']+=len(path)//5
                                        if army!=root:
                                            counts['opponent_private_flag_spy_grants']+=sum(
                                                cell<254 and bool(cell&16)==bool(root) and cell&15 in (9,11) and not cell&32
                                                for cell in observed_world(world,path))
                                        checksum.update(line.encode())
                                    counts['worlds']+=1
                                counts['roots']+=1
                                print('Audited historical informed views',counts['roots'],'/ 140',flush=True)
                            observer.ask('go','move')
                            observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
                        observer.send(event)
        finally:
            observer.close();teacher.stdin.close();teacher.wait(timeout=10);teacher.stdout.close()
        runtime=hashlib.sha256(program.read_bytes()).hexdigest()
    result=dict(passed=True,kind='historical-informational-view-reconstruction',counts=counts,
        compared='Every actual initial and decision board equals sampled world after exactly its public trajectory, masked for actor; only opponent gets root-owned Flag/Spy.',
        fake_public_disclosures=False,real_opponent_setup_received=False,
        mechanism_sha256=hashlib.sha256(mechanism_path.read_bytes()).hexdigest(),
        native_runtime_sha256=runtime,audit_rows_sha256=checksum.hexdigest())
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':run()
