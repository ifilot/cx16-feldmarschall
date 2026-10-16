"""Compare real native decisions on fixed historical SCREEN public prefixes."""
import json
from pathlib import Path

from campaign_native_template import NativeTemplateBot
from campaign_native_beliefs import quantize
from new_campaign_information_background import MissedCaptureRankBeliefs
from feldmarschall import Engine,parse_square,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/ai-honest-campaign-2026-10-15/cycle-39-quiet-contact-dos-screen/student-template-flag-bomb-v1-normal.fmtour'


class RankedObserver:
    def __init__(self,path):self.engine=Engine(str(path));self.scores={}
    def ask(self,command,prefix):
        if command!='go':return self.engine.ask(command,prefix)
        self.engine.send('ranked');self.scores={}
        while True:
            line=self.engine.read();words=line.split()
            if words[0]=='candidate':self.scores[int(words[1]),int(words[2])]=int(words[3])
            elif words[0]=='move':return ' '.join(words[1:])
            elif words[0]=='error':raise ValueError(line)
    def send(self,*args):return self.engine.send(*args)
    def close(self):self.engine.close()


def main():
    observer=ROOT/'build/ai-catalog/student-fortress-template-flag-bomb-v1-normal/observer'
    records=[]
    with Tournament(SOURCE) as tour:
        for row in list(tour.games())[:100]:
            if row['result']=='error':continue
            game=tour.game(row['id']);states,_=replay(game);events=public_events(game,states)
            for army in (0,1):
                views=[RankedObserver(observer),RankedObserver(observer)]
                bots=[NativeTemplateBot(views[0]),NativeTemplateBot(views[1],model=MissedCaptureRankBeliefs())]
                try:
                    for bot in bots:
                        for cmd in ['new '+('red','blue')[army],'rules 0','seed '+str(game['seed']),
                                    'setup '+game[('red_setup','blue_setup')[army]]]:bot.observe(cmd.split())
                    for ply,event in enumerate(events):
                        model=bots[1].model
                        if ply%2==army and model.miss:
                            owner,board,lost,shuttle=views[1].ask('public','public').split()
                            cells=list(bytes.fromhex(board));lost=list(bytes.fromhex(lost))
                            histories={sq:list(map(int,views[1].ask('memory '+square_name(sq),'history').split()))
                                for sq,c in enumerate(cells) if c<254 and bool(c&16)!=bool(army) and not c&32}
                            marg=[bot.model.rank_marginals(cells,army,lost,histories) for bot in bots]
                            packets=[quantize(*item)[3] for item in marg]
                            if packets[0]!=packets[1]:
                                moves=[bot.choose() for bot in bots]
                                changed=[dict(move=list(m),before=score,after=views[1].scores[m])
                                    for m,score in views[0].scores.items() if views[1].scores[m]!=score]
                                records.append(dict(game=game['id'],army=army,ply=ply,
                                    moves=moves,scalar_trace_available=bool(views[0].scores) and bool(views[1].scores),
                                    changed_native_scores=changed if views[0].scores and views[1].scores else None,
                                    observation=model.miss.copy()))
                                break
                        for bot in bots:bot.observe(event.split())
                finally:
                    for bot in bots:bot.close()
                if len(records)>=40:break
            if len(records)>=40:break
    doc=dict(kind='public-prefix-native-component-fixture',source=str(SOURCE.relative_to(ROOT)),
        selection='First eligible changed-Q12 decision per side history in first100 screening games; cap40',
        records=records,roots=len(records),armies=sorted({r['army'] for r in records}),
        changed_selected_moves=sum(r['moves'][0]!=r['moves'][1] for r in records),
        roots_with_scalar_trace=sum(r['scalar_trace_available'] for r in records),
        roots_without_scalar_trace=sum(not r['scalar_trace_available'] for r in records),
        roots_with_changed_observed_native_scores=sum(bool(r['changed_native_scores']) for r in records),
        limitation='Fresh native processes ingest actual own setup and public prefix; no native go calls before selected root. Component behavior, not persistent-policy strength.')
    target=ROOT/'docs/ai-honest-campaign-2026-10-16/research/information/native-fixture.json'
    target.write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps({k:v for k,v in doc.items() if k!='records'}))


if __name__=='__main__':main()
