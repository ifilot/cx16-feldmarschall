"""Analytic kernels, full public marginals and both-side observer contracts."""
import itertools
import json
import math
import os
from pathlib import Path
import shlex
import unittest

from campaign_procedural_beliefs import (BackrowModel,Geometry,StructuralModel,
                                       ProceduralTemplateBeliefs)
from campaign_template_beliefs import TemplateMixtureBeliefs,background_log_evidence
from feldmarschall import Engine,square_name

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'ai/models/dos-procedural-background-v1.json'
OBSERVER=Path(os.environ.get('FELD_PROCEDURAL_OBSERVER',ROOT/'build/ai-catalog/student-template-flag-bomb-v1-normal/observer'))
OWN='94959969496271358975B869753SB8FB8B748B6B'


def public_inputs(observer):
    army,board,lost,_=observer.ask('public','public').split();army=int(army);cells=list(bytes.fromhex(board))
    histories={sq:list(map(int,observer.ask('memory '+square_name(sq),'history').split()))
               for sq,c in enumerate(cells)if c<254 and bool(c&16)!=bool(army)and not c&32}
    return cells,army,list(bytes.fromhex(lost)),histories


class AnalyticKernels(unittest.TestCase):
    def test_uniform_geometry_matches_exact_rank_enumeration(self):
        counts=[1,1,1,1];worlds=list(itertools.permutations(range(4)))
        model=StructuralModel(counts,[Geometry(s,frozenset(),frozenset(),1.)for s in range(4)])
        for slots in((),(0,),(0,1)):
            for ranks in itertools.product(range(4),repeat=len(slots)):
                known=dict(zip(slots,ranks))
                for bits in range(16):
                    moved={s for s in range(4)if bits>>s&1};p=model.predict(known,moved)
                    selected=[w for w in worlds if all(w[o]==r for o,r in known.items())and all(w[o]<2 for o in moved)]
                    self.assertEqual(math.isfinite(p['log_evidence']),bool(selected))
                    if not selected:continue
                    self.assertAlmostEqual(p['log_evidence'],background_log_evidence(known,moved,counts,2))
                    for s in range(4):
                        self.assertAlmostEqual(p['flag'][s],sum(w[s]==3 for w in selected)/len(selected))
                        self.assertAlmostEqual(p['bomb'][s],sum(w[s]==2 for w in selected)/len(selected))

    def test_backrow_evidence_and_bombs_against_exhaustive_small_model(self):
        counts=[1,1,1,1];worlds=[w for w in itertools.permutations(range(4))if w.index(3)in(2,3)]
        model=BackrowModel(counts,flag_sites=(2,3))
        for slots in((),(0,),(0,1),(2,)):
            for ranks in itertools.product(range(4),repeat=len(slots)):
                known=dict(zip(slots,ranks))
                for bits in range(16):
                    moved={s for s in range(4)if bits>>s&1};p=model.predict(known,moved)
                    selected=[w for w in worlds if all(w[o]==r for o,r in known.items())and all(w[o]<2 for o in moved)]
                    self.assertEqual(math.isfinite(p['log_evidence']),bool(selected))
                    if not selected:continue
                    self.assertAlmostEqual(math.exp(p['log_evidence']),len(selected)/len(worlds))
                    for s in range(4):
                        self.assertAlmostEqual(p['flag'][s],sum(w[s]==3 for w in selected)/len(selected))
                        self.assertAlmostEqual(p['bomb'][s],sum(w[s]==2 for w in selected)/len(selected))

    def test_structured_weighted_fixed_screen_matches_enumeration(self):
        counts=[2,1,2,1];weights=[1.,.4,2.,.8,3.,.5]
        model=StructuralModel(counts,[Geometry(5,frozenset({4}),frozenset({0}),1.)],weights)
        worlds=[]
        for word in set(itertools.permutations([0,0,1,2,2,3])):
            if word[5]==3 and word[4]==2 and word[0]<2:
                worlds.append((word,math.prod(weights[s]for s,r in enumerate(word)if r==2 and s!=4)))
        total=sum(p for _,p in worlds)
        for known,moved in[({},set()),({1:2},{0}),({0:0,2:1},{3}),({4:0},set())]:
            selected=[(word,p)for word,p in worlds if all(word[o]==r for o,r in known.items())and all(word[o]<2 for o in moved)]
            result=model.predict(known,moved)
            if not selected:self.assertFalse(math.isfinite(result['log_evidence']));continue
            mass=sum(p for _,p in selected);self.assertAlmostEqual(math.exp(result['log_evidence']),mass/total)
            for s in range(6):self.assertAlmostEqual(result['bomb'][s],sum(p for word,p in selected if word[s]==2)/mass)


@unittest.skipUnless(OBSERVER.exists(),'requires preserved opt-in belief observer')
class PublicMarginals(unittest.TestCase):
    def setUp(self):
        self.observer=Engine(shlex.quote(str(OBSERVER)))
        self.model=ProceduralTemplateBeliefs.load(MODEL)

    def tearDown(self):self.observer.close()

    def setup(self,side):
        for event in(['new',side],['rules','0'],['seed','39117'],['setup',OWN]):self.observe(event)
        self.observer.ask('isready','readyok')

    def observe(self,event):
        self.model.observe(event);self.observer.send(' '.join(event))

    def assert_inventory(self):
        inputs=public_inputs(self.observer);marginals,remaining=self.model.rank_marginals(*inputs)
        for sq,row in marginals.items():
            self.assertAlmostEqual(sum(row),1.)
            if inputs[3][sq][-1]==1023:self.assertEqual(row[10:],[0.,0.])
        for rank,n in enumerate(remaining):self.assertAlmostEqual(sum(row[rank]for row in marginals.values()),n)
        weights,report=self.model.posterior();self.assertAlmostEqual(sum(weights),1.)
        self.assertAlmostEqual(sum(report['component_probabilities']),1.)
        self.assertAlmostEqual(sum(report['template_probabilities'])+report['background_probability'],1.)
        return inputs,marginals,remaining

    def test_both_sides_full_inventory_masks_and_hidden_nibbles(self):
        for side in('red','blue'):
            self.setup(side);inputs,reference,remaining=self.assert_inventory()
            cells,army,lost,histories=inputs
            for rank in range(12):
                mutated=[(c&240)|rank if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in cells]
                self.assertEqual(self.model.rank_marginals(mutated,army,lost,histories),(reference,remaining))
            for sq,row in reference.items():
                if histories[sq][-1]==1023:self.assertEqual(row[10:], [0.,0.])

    def test_captured_public_rank_retained_and_cache_reuses_enemy_origin_facts(self):
        self.setup('blue')
        events=[['moved','a4','a5'],['battle','a7','a5','9','4'],['moved','a5','a4'],['battle','j7','j4','9','9']]
        for event in events:self.observe(event);self.assert_inventory()
        self.assertEqual(self.model.known[0,9],8);self.assertNotIn((0,9),self.model.tokens.values())
        self.assertEqual(self.model.lost[8],1)
        before=self.model.cache_misses
        self.model.posterior();self.model.posterior();self.assertEqual(self.model.cache_misses,before)
        # Next enemy first move adds a new origin; a subsequent known move of
        # that same enemy does not change the original-origin public evidence.
        self.observe(['moved','b4','b5']);self.assert_inventory()
        misses=self.model.cache_misses
        self.observe(['moved','b7','b6']);self.assert_inventory() # own quiet move
        self.assertEqual(self.model.cache_misses,misses)
        self.observe(['moved','b5','b4']);self.assert_inventory()
        self.assertEqual(self.model.cache_misses,misses)

    def test_uniform_epsilon_reproduces_old_model_and_backrow_is_opt_in(self):
        self.setup('red');inputs=public_inputs(self.observer)
        data=json.loads(MODEL.read_text());data['epsilon']=1.
        uniform=ProceduralTemplateBeliefs(data);old=TemplateMixtureBeliefs()
        for model in(uniform,old):model.observe(['new','red']);model.observe(['setup',OWN])
        a,ra=uniform.rank_marginals(*inputs);b,rb=old.rank_marginals(*inputs)
        self.assertEqual(ra,rb)
        for sq in a:
            for x,y in zip(a[sq],b[sq]):self.assertAlmostEqual(x,y)
        data=json.loads(MODEL.read_text());data['background_kind']='backrow';data.pop('row_weights')
        backrow=ProceduralTemplateBeliefs(data)
        backrow.observe(['new','red']);backrow.observe(['setup',OWN])
        result,remaining=backrow.rank_marginals(*inputs)
        for rank,n in enumerate(remaining):self.assertAlmostEqual(sum(row[rank]for row in result.values()),n)
        self.assertEqual(backrow.posterior()[1]['background_kind'],'backrow')

    def test_unknown_evidence_falls_back_to_positive_uniform_support(self):
        self.setup('blue')
        # First red piece reveals an off-backrowFlag by losing its defender in
        # a battle. Hard tracker must accept it; source components assign0 but
        # uniform support keeps the posterior valid. Use an initial ownScout
        # attack on a concealed Flag at original enemyfronta4.
        self.observe(['moved','b4','b5'])
        self.observe(['battle','a7','a4','9','F'])
        inputs,marginals,remaining=self.assert_inventory()
        weights,_=self.model.posterior();self.assertEqual(weights[-1],1.)
        self.assertEqual(sum(weights[:-1]),0.)
        self.assertEqual(remaining[11],0)

    def test_native_only_sampler_fails_explicitly(self):
        with self.assertRaises(NotImplementedError):self.model.sample_worlds(None)




@unittest.skipUnless(OBSERVER.exists(),'requires preserved opt-in belief observer')
class NativeProceduralDriver(unittest.TestCase):
    def make_bot(self,army,alter=False):
        from campaign_native_template import NativeTemplateBot
        from test_campaign_native_template import AlterPublicNibbles
        observer=AlterPublicNibbles(Engine(shlex.quote(str(OBSERVER))),alter)
        bot=NativeTemplateBot(observer,model=ProceduralTemplateBeliefs.load(MODEL))
        for event in(['new',('red','blue')[army]],['rules','0'],['seed','1729'],['setup',OWN]):bot.observe(event)
        return bot,observer

    def check_inventory(self,report):
        q=report['q12'];remaining=report['remaining']
        self.assertEqual(sum(q['flag']),4096*remaining[11]);self.assertEqual(sum(q['bomb']),4096*remaining[10])
        self.assertTrue(all(f+b+m==4096 for f,b,m in zip(q['flag'],q['bomb'],q['mobile'])))
        self.assertAlmostEqual(sum(report['component_posterior']['component_probabilities']),1.)

    def test_real_public_history_both_sides_secret_packets_and_native_choices(self):
        import copy
        from tournament_store import Tournament,replay
        from test_information_parent_parity import public_events
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour')as saved:game=saved.game(9)
        states,_=replay(game);events=public_events(game,states)
        for army in(0,1):
            bots=[]
            for alter in(False,True):
                bot,_=self.make_bot(army,alter)
                bot.observe(['new',('red','blue')[army]]);bot.observe(['seed','1729'])
                bot.observe(['setup',game[('red_setup','blue_setup')[army]]]);bots.append(bot)
            try:
                for ply in range(81):
                    if ply in(0,20,40,80):
                        reports=[]
                        for bot in bots:
                            self.assertIsNotNone(bot.choose());self.check_inventory(bot.last_report)
                            report=copy.deepcopy(bot.last_report);report.pop('elapsed_seconds');reports.append(report)
                        self.assertEqual(*reports)
                    if ply<80:
                        for bot in bots:bot.observe(events[ply].split())
            finally:
                for bot in bots:bot.close()

    def test_deduced_adjacent_flag_win_and_reset_both_sides(self):
        from feldmarschall import COUNTS,LAKES,setup_squares
        for army in(0,1):
            bot,observer=self.make_bot(army)
            try:
                enemy=1-army;target=setup_squares(enemy)[0];scout=setup_squares(enemy)[1]
                source=target+(10 if army==0 else-10);ownflag=setup_squares(army)[-1]
                cells=[254 if sq in LAKES else 255 for sq in range(100)]
                cells[source]=army*16|1|64;cells[ownflag]=army*16|11
                cells[target]=enemy*16|12;cells[scout]=enemy*16|32|8
                lost=list(COUNTS);lost[11]-=1;lost[8]-=1
                rem=list(COUNTS);rem[11]-=1;rem[8]-=1
                original=[11,8]+[rank for rank,n in enumerate(rem)for _ in range(n)]
                bot.model.known={(enemy,o):rank for o,rank in enumerate(original)if o}
                bot.model.known[army,0]=1;bot.model.known[army,39]=11
                bot.model.tokens={source:(army,0),ownflag:(army,39),target:(enemy,0),scout:(enemy,1)}
                bot.model.moved={(army,0)};bot.model.lost=lost
                observer.send(f'position {army} {bytes(lost).hex()} {bytes(cells).hex()} ffffffff0000')
                self.assertEqual(bot.choose(),(source,target));self.check_inventory(bot.last_report)
                bot.observe(['new',('red','blue')[army]])
                self.assertEqual(bot.model.known,{})
                self.assertEqual(bot.model.cache_misses,0)
                self.assertIsNone(bot.last_report)
            finally:bot.close()


if __name__=='__main__':unittest.main()
