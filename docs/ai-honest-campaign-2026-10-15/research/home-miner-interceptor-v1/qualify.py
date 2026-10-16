"""Exclude immediate disclosed guard losses from geometric reserve opportunities."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from preflight import Position,clone,reserve,battle
OUT=Path(__file__).resolve().parent


def decode(row):
    p=Position()
    for sq,c in enumerate(bytes.fromhex(row['public_board_hex'])):
        if c<254:p.cells[sq]=[(c>>4)&1,c&15,bool(c&64),bool(c&32)]
    raw=bytes.fromhex(row['shuttle_hex'])
    p.shuttle={a:tuple(None if raw[2*i+a]==255 else raw[2*i+a]for i in range(3))for a in(0,1)}
    return p


def safe_reserve(p,army,entries,rank):
    threats={dst for src,dst in p.moves(1-army)if p.cells[src][3]and p.cells[src][1]<10 and p.cells[dst]and p.cells[dst][0]==army and battle(p.cells[src][1],p.cells[dst][1])!='defender'}
    coverage=reserve(p,army,entries,rank)
    guards={b:[s for s in positions if s not in threats]for b,positions in coverage['guards'].items()}
    return dict(covered=all(guards.values()),guards=guards,threatened_own_squares=sorted(threats))


def main():
    source=OUT/'result.json';data=json.loads(source.read_text());roots={(r['game'],r['ply']):r for r in data['screened_known_Miner_roots']};rows=[]
    for old in data['opportunities']:
        r=roots[old['game'],old['ply']];p=decode(r);army=r['army'];rank=old['max_guard_rank']
        before=safe_reserve(p,army,r['entries'],rank)
        q=clone(p);q.move(*old['selected']);after=safe_reserve(q,army,r['entries'],rank)
        if after['covered']:continue
        alternatives=[]
        for candidate in old['known_safe_cover_moves']:
            q=clone(p);q.move(*candidate['move']);coverage=safe_reserve(q,army,r['entries'],rank)
            if coverage['covered']:alternatives.append(candidate['move'])
        if alternatives:
            rows.append(dict(old,kind='maintain'if before['covered']else'restore',
                safe_cover_alternatives=alternatives,safe_before=before,safe_after=after))
    summary={}
    for rank in(6,7):
        subset=[r for r in rows if r['max_guard_rank']==rank]
        summary[str(rank)]=dict(roots=len(subset),games=len({r['game']for r in subset}),kinds=dict(Counter(r['kind']for r in subset)),
            distance_buckets=dict(Counter(str(r['min_Miner_distance'])for r in subset)),
            C10_duplicate_roots=sum(r['C10_selected_demoted']for r in subset),
            maintain_games=len({r['game']for r in subset if r['kind']=='maintain'}),
            maintain_nonC10_loss_records=[r for r in subset if r['kind']=='maintain'and r['eventual_own_Flag_loss']and not r['C10_selected_demoted']],
            distance3to6_nonC10_loss_games=len({r['game']for r in subset if r['eventual_own_Flag_loss']and not r['C10_selected_demoted']and r['min_Miner_distance']is not None and 3<=r['min_Miner_distance']<=6}))
    document=dict(kind='public-guard-survival-qualified-home-reserve-preflight',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        qualification='Every currently necessary guard must avoid a next-turn legal capture/exchange by any disclosed enemy after the quiet alternative; uncertainty remains deferred to tactical policy. This is a conservative preflight filter, not complete safety.',
        summary=summary,opportunities=rows,source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'qualified.json').write_text(json.dumps(document,indent=2)+'\n');print(json.dumps({k:{f:v for f,v in s.items()if f!='maintain_nonC10_loss_records'}for k,s in summary.items()},indent=2))


if __name__=='__main__':main()
