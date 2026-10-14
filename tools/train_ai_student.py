"""Fit an integer capture-correction tree from public states and sampled-world search."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import zipfile

from feldmarschall import ROOT, COUNTS, GLYPHS, UNKNOWN, Engine, battle, square_name

FEATURES = ['actor_rank','target_rank','capture','distance','actor_disclosed','target_moved',
            'target_disclosed','adjacent_disclosed_threats','own_flag_distance','target_observed_moves',
            'target_approach_rank','target_retreat_rank','target_candidate_count','actor_observed_moves',
            'enemy_back_row_distance','adjacent_threats_with_friendly_recapture']


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sample_world(cells, lost, histories, rng, own):
    """Uniform assignments for ordinary moved/all-rank masks; constrained fallback
    rejection for narrower candidate sets. No referee board or setup is read."""
    remaining = [count-n for count,n in zip(COUNTS,lost)]
    slots = []
    for sq,cell in enumerate(cells):
        if cell >= 254 or bool(cell&16)==bool(own): continue
        if cell&32: remaining[cell&15]-=1
        else: slots.append(sq)
    if min(remaining)<0 or sum(remaining)!=len(slots): raise ValueError('inconsistent public inventory')
    slots.sort(key=lambda sq: histories[sq][-1].bit_count())
    for _ in range(500):
        counts=remaining[:];world=cells[:];weight=1.0
        for sq in slots:
            state=histories[sq];mask=state[-1]
            options=[rank for rank,n in enumerate(counts) if mask&(1<<rank) for _ in range(n)]
            if not options: break
            rank=rng.choice(options);counts[rank]-=1;world[sq]=(world[sq]&240)|rank
            approach,retreat=state[8],state[9]
            factor=1+int(approach<12 and battle(rank,approach)=='attacker')+int(retreat<12 and battle(retreat,rank)=='attacker')
            weight*=factor
        else: return world,weight
    raise ValueError('could not sample a consistent assignment')


def vectors(engine, record, cold):
    info=record['input']
    engine.send(f"features {info['army']} {info['enemy_lost_hex']} {info['board_hex']} {int(cold)}")
    found={}
    while True:
        line=engine.read()
        if line=='features_done': return found
        if line.startswith('error'): raise ValueError(line)
        fields=line.split()
        if fields[0]=='feature':
            values=list(map(int,fields[1:]));found[tuple(values[:2])]=values[2:]


def label(job):
    record, engine_path, teacher_path, samples, seed = job
    engine=Engine('FELDMARSCHALL_TRACE=1 '+shlex.quote(str(engine_path)))
    teacher=subprocess.Popen([str(teacher_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
    try:
        info=record['input'];army=info['army'];cells=list(bytes.fromhex(info['board_hex']))
        engine.send('new '+('red','blue')[army])
        # Dummy private setup: history recording ignores private identities;
        # features later receive only this player's legitimate masked root view.
        engine.send('setup '+''.join(g*n for g,n in zip(GLYPHS,COUNTS)))
        for event in record['public_history']: engine.send(event)
        full=vectors(engine,record,False)
        if set(full)!={tuple(move) for move in record['legal_moves']}: raise ValueError('public legal moves differ')
        histories={sq:list(map(int,engine.ask('memory '+square_name(sq),'history').split()))
                   for sq,cell in enumerate(cells) if cell<254 and bool(cell&16)!=bool(army) and not cell&32}
        cold=vectors(engine,record,True)
        engine.send(f"think {army} {seed%65535+1} {info['enemy_lost_hex']} {info['board_hex']}")
        credit={}
        while True:
            line=engine.read()
            if line.startswith('best '): break
            if line.startswith('error'): raise ValueError(line)
            parts=line.split()
            if parts[0]=='credit': credit[tuple(map(int,parts[1:3]))]=int(parts[3])
        captures=[move for move,features in full.items() if features[2]]
        totals={move:[0.0,0.0] for move in captures}
        rng=random.Random(seed);weights=[];nodes=0
        shuttle=info['shuttle']
        state=bytes([(shuttle[str(a)][index] if shuttle[str(a)][index] is not None else 255)
                     for index in range(3) for a in (0,1)]).hex()
        for _ in range(samples):
            world,weight=sample_world(cells,list(bytes.fromhex(info['enemy_lost_hex'])),histories,rng,army)
            teacher.stdin.write(f'search {army} 3 {bytes(world).hex()} {state}\n');teacher.stdin.flush()
            scores={}
            while True:
                line=teacher.stdout.readline().strip()
                if not line: raise ValueError('teacher stopped')
                parts=line.split()
                if parts[0]=='done': nodes+=int(parts[1]);stand_pat=int(parts[2]);break
                if parts[0]=='error': raise ValueError(line)
                if parts[0]=='action': scores[tuple(map(int,parts[1:3]))]=(int(parts[3]),int(parts[4]))
            if set(scores)!=set(full): raise ValueError('sampled world changes root legal actions')
            weights.append(weight)
            for move in captures:
                future,immediate=scores[move]
                correction=future-immediate-stand_pat+credit.get(move,0)
                totals[move][0]+=weight*correction;totals[move][1]+=correction
        group=f"{record['source']['group']}:{record['source']['seed']}"
        validation=int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%5==0
        rows=[]
        for move in captures:
            for index,feature_set in enumerate((full,cold)):
                target=totals[move][index]/(sum(weights) if index==0 else samples)
                rows.append({'position':record['id'],'split_group':group,'validation':validation,
                             'history':'full' if index==0 else 'cold','move':move,'features':feature_set[move],
                             'target':max(-192,min(192,round(target)))})
        return {'id':record['id'],'rows':rows,'nodes':nodes,
                'effective_samples':sum(weights)**2/sum(w*w for w in weights)}
    finally:
        engine.close();teacher.stdin.close();teacher.wait(timeout=10);teacher.stdout.close()


def fit(rows, depth=4, minimum=24):
    nodes=[]
    def build(selected, level):
        index=len(nodes);mean=round(sum(row['target'] for row in selected)/len(selected))
        nodes.append({'feature':255,'threshold':0,'left':0,'right':0,'value':mean})
        if level==depth or len(selected)<minimum*2: return index
        best=None
        for feature in range(len(selected[0]['features'])):
            ordered=sorted(selected,key=lambda row:row['features'][feature])
            total=sum(row['target'] for row in ordered);total2=sum(row['target']**2 for row in ordered)
            left=left2=0
            for cut in range(1,len(ordered)):
                y=ordered[cut-1]['target'];left+=y;left2+=y*y
                if cut<minimum or len(ordered)-cut<minimum or ordered[cut-1]['features'][feature]==ordered[cut]['features'][feature]: continue
                error=left2-left*left/cut+(total2-left2)-(total-left)**2/(len(ordered)-cut)
                option=(error,feature,ordered[cut-1]['features'][feature],cut)
                if best is None or option<best[:4]: best=(*option,ordered)
        if best is None: return index
        error,feature,threshold,cut,ordered=best
        baseline=sum((row['target']-mean)**2 for row in selected)
        if error>=baseline: return index
        left=build(ordered[:cut],level+1);right=build(ordered[cut:],level+1)
        nodes[index]={'feature':feature,'threshold':threshold,'left':left,'right':right,'value':0}
        return index
    build(rows,0)
    return nodes


def predict(nodes, features):
    node=0
    while nodes[node]['feature']!=255:
        item=nodes[node];node=item['left'] if features[item['feature']]<=item['threshold'] else item['right']
    return nodes[node]['value']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,default=ROOT/'docs/ai-diagnostics/positions-20261014.zip')
    parser.add_argument('--positions',type=int,default=512)
    parser.add_argument('--samples',type=int,default=16)
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--seed',type=int,default=20261014)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if min(args.positions,args.samples,args.jobs)<1: parser.error('positions, samples and jobs must be positive')
    args.out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(args.corpus) as archive:
        records=[json.loads(line) for line in archive.read('positions.jsonl').splitlines()]
    eligible=[]
    for record in records:
        cells=bytes.fromhex(record['input']['board_hex'])
        if any(cells[to]<254 for _,to in record['legal_moves']): eligible.append(record)
    eligible.sort(key=lambda record:hashlib.sha256((str(args.seed)+record['id']).encode()).hexdigest())
    selected=eligible[:args.positions]
    if not selected: raise ValueError('no tactical positions')
    selected=[{'id':record['id'],'input':record['input'],'public_history':record['public_history'],
               'legal_moves':record['legal_moves'],'source':{key:record['source'][key] for key in ('group','seed')}}
              for record in selected]
    (args.out/'public_inputs.jsonl').write_text(''.join(json.dumps(record)+'\n' for record in selected))
    with zipfile.ZipFile(args.out/'sources.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        for directory in ('src','tests','tools'):
            for path in (ROOT/directory).rglob('*'):
                if path.suffix in ('.c','.h','.s','.cfg','.py'): archive.write(path,str(path.relative_to(ROOT)))
        for name in ('Makefile','src/Makefile'):archive.write(ROOT/name,name)
    (args.out/'engines').mkdir()
    for name in ['feldmarschall-engine-features','feldmarschall-teacher']:
        shutil.copy2(ROOT/'build'/name,args.out/'engines'/name)
    engine=(args.out/'engines/feldmarschall-engine-features').resolve()
    teacher=(args.out/'engines/feldmarschall-teacher').resolve()
    jobs=[(record,engine,teacher,args.samples,args.seed+int(record['id'][:8],16)) for record in selected]
    rows=[];nodes_searched=0;effective=[]
    with (args.out/'labels.jsonl').open('w') as output,ProcessPoolExecutor(args.jobs) as pool:
        for i,result in enumerate(pool.map(label,jobs),1):
            rows.extend(result['rows']);nodes_searched+=result['nodes'];effective.append(result['effective_samples'])
            for row in result['rows']: output.write(json.dumps(row)+'\n')
            if i%25==0 or i==len(jobs): print(f'{i}/{len(jobs)} positions, {len(rows)} labels',flush=True)
    training=[row for row in rows if not row['validation']];validation=[row for row in rows if row['validation']]
    if not training or not validation: raise ValueError('empty grouped train/validation partition')
    tree=fit(training)
    report={'schema':1,'features':FEATURES,'nodes':tree,'node_bytes':len(tree)*6,'positions':len(selected),
            'samples_per_position':args.samples,'teacher_depth':3,'teacher_beam':8,'teacher_nodes':nodes_searched,
            'training_rows':len(training),'validation_rows':len(validation),
            'validation_mae':sum(abs(predict(tree,row['features'])-row['target']) for row in validation)/len(validation),
            'zero_correction_validation_mae':sum(abs(row['target']) for row in validation)/len(validation),
            'mean_effective_samples':sum(effective)/len(effective),'corpus_sha256':sha(args.corpus),
            'labels_sha256':sha(args.out/'labels.jsonl'),'command':sys.argv,
            'engine_sha256':{'features':sha(engine),'teacher':sha(teacher)},
            'source_archive_sha256':sha(args.out/'sources.zip'),
            'limitations':'Determinized beam minimax is approximate and permits strategy fusion; teacher labels are not independently proven optimal. Split groups share layout family and game seed; cold-history rows stay in their full-history group.'}
    (args.out/'model.json').write_text(json.dumps(report,indent=2)+'\n')
    header='/* Generated by train_ai_student.py; model SHA is recorded with the experiment. */\nstatic const student_node_t student_nodes[] = {\n'
    for node in tree: header+='    {%d,%d,%d,%d,%d},\n'%tuple(node[k] for k in ['feature','threshold','left','right','value'])
    (args.out/'ai_student_model.h').write_text(header+'};\n')
    print(json.dumps({key:report[key] for key in ['positions','node_bytes','training_rows','validation_rows','validation_mae','zero_correction_validation_mae','teacher_nodes']}))


if __name__=='__main__': main()
