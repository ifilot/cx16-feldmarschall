"""Historical own-deployment associations; these are not setup causal effects.

Both armies were drawn from the same family. Outcomes can reflect opponent
layouts, family, side and policy interactions. Feature groups are descriptive
development evidence only and cannot establish a new deployment's strength.
"""
from collections import Counter,deque
import hashlib
import json

from ai_registry import ROOT
from feldmarschall import valid_setup
from tournament_store import Tournament


def features(setup):
    if not valid_setup(setup):raise ValueError('legal Classic own setup required')
    flag=setup.index('F');row,column=divmod(flag,10)
    adjacent=[]
    # Normalized rows0..3 run front to back. A square immediately in front of
    # row0 is a real open board square, while behind row3 is the board edge.
    for target in (flag-10,flag+10,flag-1 if column else None,flag+1 if column<9 else None):
        if target is not None and (target!=flag+10 or row<3):adjacent.append(target)
    bombs=sum(0<=target<40 and setup[target]=='B' for target in adjacent)
    miners=[index for index,glyph in enumerate(setup) if glyph=='8']
    def exits(start):
        queue=deque([start]);seen={start}
        while queue:
            square=queue.popleft()
            if square//10==0:return True
            r,c=divmod(square,10)
            for target in (square-10 if r else -1,square+10 if r<3 else -1,
                           square-1 if c else -1,square+1 if c<9 else -1):
                if target<0 or target in seen or setup[target] in 'BF':continue
                seen.add(target);queue.append(target)
        return False
    return dict(flag_back_row=row==3,flag_corner=row==3 and column in (0,9),
        adjacent_flag_bombs=bombs,fully_bomb_screened_flag=bombs==len(adjacent),
        front_row_miners=sum(index<10 for index in miners),
        miners_with_permanent_front_access=sum(exits(index) for index in miners),
        any_front_miner=any(index<10 for index in miners))


def table(rows):
    scored=[row for row in rows if row['score'] is not None]
    return dict(attempts=len(rows),scored=len(scored),errors=len(rows)-len(scored),
        score=sum(row['score'] for row in scored)/len(scored) if scored else None,
        wins=sum(row['score']==1 for row in scored),draws=sum(row['score']==.5 for row in scored),
        losses=sum(row['score']==0 for row in scored))


def run():
    paths=[ROOT/'docs/ai-restrained-search-2026-10-15/development.fmtour',
           ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour']
    records=[];sources=[]
    for path in paths:
        with Tournament(path) as tournament:
            metadata=tournament.metadata()
            assert metadata['status']=='complete' and metadata['rules']=='classic'
            assert {p['policy']['id'] for p in metadata['participants']}=={
                'teacher-context-v1-normal','msdos-1990-v2-normal'}
            sources.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),seed=metadata['seed']))
            for row in tournament.games():
                game=tournament.game(row['id']);side=0 if game['red']=='teacher-context-v1-normal' else 1
                own=game[('red_setup','blue_setup')[side]]
                enemy=game[('blue_setup','red_setup')[side]]
                score=None if game['result']=='error' else .5 if game['result']=='draw' else float(game['result']==('red','blue')[side])
                records.append(dict(source=str(path.relative_to(ROOT)),game=game['id'],pair=game['pair_id'],
                    family=game['family'],army=side,score=score,features=features(own),
                    opponent_features=features(enemy)))
    feature_tables={}
    for feature in records[0]['features']:
        groups=sorted({row['features'][feature] for row in records})
        feature_tables[feature]={str(group):table([row for row in records if row['features'][feature]==group])
                                 for group in groups}
    within_family={}
    for feature in ('fully_bomb_screened_flag','flag_back_row','any_front_miner'):
        within_family[feature]={}
        for family in sorted({row['family'] for row in records}):
            subset=[row for row in records if row['family']==family]
            within_family[feature][family]={str(group):table([row for row in subset if row['features'][feature]==group])
                                            for group in (False,True)}
    result=dict(kind='historical-development-own-deployment-associations',causal_effect_evidence=False,
        warning='Both armies share the named generated family; associations can reflect opponent setups and family. No policy-owned deployment was tested here. No campaign validation data is used.',
        sources=sources,overall=table(records),by_family={family:table([r for r in records if r['family']==family])
            for family in sorted({r['family'] for r in records})},by_own_feature=feature_tables,
        within_family_binary_features=within_family,records=records)
    destination=ROOT/'docs/ai-honest-campaign-2026-10-15/research/horizon/deployment-associations.json'
    assert not destination.exists(),'preserve historical association report'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('overall','by_family','by_own_feature')},indent=2))


if __name__=='__main__':run()
