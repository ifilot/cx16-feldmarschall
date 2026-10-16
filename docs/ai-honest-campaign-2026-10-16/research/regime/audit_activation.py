"""Full forced-prefix mechanism audit on a frozen, old development screen."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shlex
import sys
import time

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(ROOT/'tools'))
from ai_registry import build_policy,get_policy
from campaign_native_template import NativeTemplateBot
from new_campaign_regime_bot import RegimeResetBot
from feldmarschall import Engine,parse_square,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def move(text):return None if text=='none' else tuple(map(parse_square,text.split()))


class Measured:
    def __init__(self,engine):self.engine=engine;self.go_calls=0;self.reset_calls=0
    def send(self,line):return self.engine.send(line)
    def ask(self,line,prefix):
        self.go_calls+=line=='go';self.reset_calls+=line=='goal-regime-reset'
        return self.engine.ask(line,prefix)
    def close(self):self.engine.close()


def run():
    protocol=json.loads((HERE/'ACTIVATION-PROTOCOL.json').read_text())
    assert sha(__file__)==protocol['auditor_sha256']
    cohort=ROOT/protocol['history'];assert sha(cohort)==protocol['history_sha256']
    specs=[get_policy(protocol[k]) for k in ('reference','candidate')]
    assert specs==protocol['frozen_policies']
    builds=[build_policy(p['id']) for p in specs]
    for source in ('campaign_native_template.py','new_campaign_regime_bot.py'):
        assert sha(ROOT/'tools'/source)==sha(builds[1][0].parent/source)
    records=[];counts=Counter();started=time.perf_counter()
    with Tournament(cohort) as store:
        for identity in protocol['game_ids']:
            game=store.game(identity);states,_=replay(game);events=public_events(game,states)
            for army in (0,1):
                bots=[];launchers=[]
                for kind,(executable,receipt) in zip((NativeTemplateBot,RegimeResetBot),builds):
                    bots.append(kind(Measured(Engine(shlex.quote(str(executable.parent/'observer'))))))
                    launchers.append(Engine(shlex.quote(str(executable))))
                choose_seconds=[0.,0.];observe_seconds=[0.,0.];choices=0;changed=0;first=None;gate=None
                try:
                    for line in ('new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),
                                 'setup '+game[('red_setup','blue_setup')[army]]):
                        for bot in bots:bot.observe(line.split())
                        for launcher in launchers:launcher.send(line)
                    for ply,event in enumerate(events):
                        if ply%2==army:
                            choices+=1;selected=[None,None]
                            for n in ((0,1) if (identity+army+choices)%2 else (1,0)):
                                expected=move(launchers[n].ask('go','move'));bot=bots[n]
                                before=bot.observer.go_calls;tick=time.perf_counter();selected[n]=bot.choose()
                                choose_seconds[n]+=time.perf_counter()-tick
                                assert bot.observer.go_calls-before==1
                                assert selected[n]==expected,(identity,army,ply,n,'registered launcher mismatch')
                                counts['registered_launcher_choice_parity']+=1
                            if bots[1].last_report['belief_regime_reset']['fired_now']:
                                assert gate is None
                                gate=dict(ply=ply,own_decision=choices,public_event=bots[1].regime_event)
                            if selected[0]!=selected[1]:
                                changed+=1
                                if first is None:first=dict(ply=ply,own_decision=choices,
                                    baseline_move=selected[0],candidate_move=selected[1],
                                    reset_already_fired=bots[1].regime_fired)
                            actual=tuple(game['moves'][ply])
                            for n,bot in enumerate(bots):
                                if selected[n]!=actual:
                                    line='played '+' '.join(map(square_name,actual))
                                    launchers[n].ask(line,'playedok');bot.observe(line.split())
                                    counts['forced_played_corrections_'+('baseline','candidate')[n]]+=1
                        for n in ((0,1) if (identity+army+ply)%2 else (1,0)):
                            tick=time.perf_counter();bots[n].observe(event.split())
                            observe_seconds[n]+=time.perf_counter()-tick
                            launchers[n].send(event)
                    resets=bots[1].observer.reset_calls
                    assert resets<=1 and resets==int(gate is not None)
                    row=dict(game=identity,army=army,saved_plies=game['plies'],own_decisions=choices,
                        gate=gate,first_changed_choice=first,changed_choices=changed,
                        reset_calls=resets,choose_seconds=dict(zip(('baseline','candidate'),choose_seconds)),
                        public_observe_seconds=dict(zip(('baseline','candidate'),observe_seconds)))
                    records.append(row);counts['side_histories']+=1;counts['own_decisions']+=choices
                    counts['histories_with_gate']+=gate is not None
                    counts['histories_with_changed_choice']+=first is not None
                    counts['changed_choices']+=changed
                finally:
                    for bot in bots:bot.close()
                    for launcher in launchers:launcher.close()
            if identity%5==0:print(json.dumps(dict(counts,elapsed_seconds=time.perf_counter()-started)),flush=True)
    def mean(kind,key):return sum(r[key][kind] for r in records)/counts['own_decisions']
    costs={kind:dict(mean_choose_seconds=mean(kind,'choose_seconds'),
                     mean_public_observe_seconds_per_own_decision=mean(kind,'public_observe_seconds'))
           for kind in ('baseline','candidate')}
    additional=sum(costs['candidate'].values())-sum(costs['baseline'].values())
    result=dict(kind='public-regime-reset-old-screen-activation-v1',strength_evidence=False,
        protocol_sha256=sha(HERE/'ACTIVATION-PROTOCOL.json'),history_sha256=sha(cohort),
        counts=dict(counts),host_seconds=time.perf_counter()-started,costs=costs,
        mean_additional_choose_and_public_observe_seconds_per_own_decision=additional,
        interpretation='All own decisions were executed through complete forced old screening histories. Each adapter matched its registered frozen launcher at every decision and corrected divergent chosen moves to the saved actual move. First changed choices are mechanism evidence; later changed choices are correlated consequences, not independent roots. Timings are host wall time under concurrent load, not CX16 timing. No strength games or validation layouts were used.',
        records=records)
    (HERE/'activation-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))


if __name__=='__main__':run()
