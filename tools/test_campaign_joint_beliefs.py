"""Exact enumerable posterior and real public-history tests for joint setups."""
import itertools
import json
import math
import random
import shlex
import unittest

from ai_registry import ROOT,build_policy
from campaign_joint_beliefs import JointSetupBeliefs,neighbors,subset_sum
from feldmarschall import COUNTS,Engine,GLYPHS,square_name
from tournament_store import Tournament,replay
from test_information_parent_parity import public_events

MODEL=ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'


class JointPosteriorTests(unittest.TestCase):
    def test_subset_sum_matches_exhaustive_enumeration(self):
        for theta in (-2.,0.,1.5):
            for n in range(1,9):
                for adjacent in range(n+1):
                    for count in range(n+1):
                        exact=sum(math.exp(theta*sum(i<adjacent for i in subset))
                                  for subset in itertools.combinations(range(n),count))
                        self.assertAlmostEqual(subset_sum(adjacent,n,count,theta),exact,places=8)

    def small_exact(self):
        model=JointSetupBeliefs.load(MODEL)
        sites={20,21,22,23,30,31,32,33};fixed={19,39}
        exact={}
        for flag in sites:
            for bombs in itertools.combinations(sorted(sites-{flag}),4):
                allbombs=set(bombs)|fixed
                for style in range(2):
                    theta=model.theta[style]
                    exact[style,flag,bombs]=(model.weights[style]*model.phi[style][flag//10]/10*
                        math.exp(theta*len(neighbors(flag)&allbombs))/subset_sum(len(neighbors(flag)),39,6,theta))
        total=sum(exact.values());exact={key:p/total for key,p in exact.items()}
        return model,sites,fixed,exact

    def test_flag_style_posterior_matches_enumerated_joint_assignments(self):
        model,sites,fixed,exact=self.small_exact()
        items,weights=model.conditional(sites,sites,fixed);total=sum(weights)
        for item,weight in zip(items,weights):
            expected=sum(p for key,p in exact.items() if key[:2]==item)
            self.assertAlmostEqual(weight/total,expected,places=12)

    def test_draw_matches_enumerated_flag_and_bomb_marginals(self):
        model,sites,fixed,exact=self.small_exact();rng=random.Random(48711)
        prepared=model.conditional(sites,sites,fixed);flagcounts=dict.fromkeys(sites,0);bombcounts=dict.fromkeys(sites,0)
        for _ in range(24000):
            style,flag,bombs=model.draw_immobiles(sites,sites,fixed,rng,prepared)
            self.assertNotIn(flag,bombs);self.assertEqual(len(bombs),4)
            flagcounts[flag]+=1
            for site in bombs:bombcounts[site]+=1
        for site in sites:
            flag_expected=sum(p for (_,flag,_),p in exact.items() if flag==site)
            bomb_expected=sum(p for (_,_,bombs),p in exact.items() if site in bombs)
            self.assertAlmostEqual(flagcounts[site]/24000,flag_expected,delta=.012)
            self.assertAlmostEqual(bombcounts[site]/24000,bomb_expected,delta=.012)


class PublicHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy('teacher-context-v1-normal');cls.observer=program.parent/'observer'
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:
            for row in saved.games():
                if row['result']=='error':continue
                game=saved.game(row['id']);states,_=replay(game)
                death=next((ply for ply,(src,dst) in enumerate(game['moves'])
                            if states[ply][dst] and states[ply][dst][1]==10 and
                            states[ply+1][dst] and states[ply+1][dst][0]!=states[ply][dst][0]),None)
                if death is not None and death<220:
                    cls.game=game;cls.states=states;cls.death=death;break
            else:raise AssertionError('development evidence needs a publicly captured Bomb')

    def initialize(self,army):
        model=JointSetupBeliefs.load(MODEL);observer=Engine(shlex.quote(str(self.observer)))
        for line in ('new '+('red','blue')[army],'rules 0','setup '+self.game[('red_setup','blue_setup')[army]]):
            model.observe(line.split());observer.send(line)
        return model,observer

    def root(self,model,observer,army):
        armytext,board,lost,_=observer.ask('public','public').split();self.assertEqual(int(armytext),army)
        cells=list(bytes.fromhex(board));lost=list(bytes.fromhex(lost))
        histories={sq:list(map(int,observer.ask('memory '+square_name(sq),'history').split()))
                   for sq,cell in enumerate(cells) if cell<254 and bool(cell&16)!=bool(army) and not cell&32}
        return cells,lost,histories

    def test_real_history_counts_masks_hidden_nibbles_and_captured_bomb_retention(self):
        for army in (0,1):
            model,observer=self.initialize(army)
            try:
                events=public_events(self.game,self.states)
                for ply in range(self.death+2):
                    if ply%20==0 or ply==self.death+1:
                        cells,lost,histories=self.root(model,observer,army)
                        draws=model.sample_worlds(cells,lost,histories,random.Random(883),army,8)
                        mutated=cells[:]
                        for sq in histories:mutated[sq]=(mutated[sq]&240)|(sq%12)
                        self.assertEqual(draws,model.sample_worlds(mutated,lost,histories,random.Random(883),army,8))
                        for world,weight in draws:
                            inventory=lost[:]
                            for sq,cell in enumerate(cells):
                                if cell>=254 or bool(cell&16)==bool(army):self.assertEqual(world[sq],cell)
                                else:
                                    inventory[world[sq]&15]+=1
                                    if cell&32:self.assertEqual(world[sq],cell)
                            self.assertEqual(inventory,COUNTS)
                            for sq,h in histories.items():self.assertTrue(h[-1]&(1<<(world[sq]&15)))
                            self.assertGreater(weight,0)
                    if ply<=self.death:
                        model.observe(events[ply].split());observer.send(events[ply])
                src,dst=self.game['moves'][self.death];owner=self.states[self.death][dst][0]
                if owner!=army:
                    deadbombs=[token for token,rank in model.known.items() if token[0]!=army and rank==10 and token not in model.tokens.values()]
                    self.assertTrue(deadbombs);self.assertGreater(model.lost[10],0)
                model.observe(['new',('red','blue')[army]])
                self.assertEqual(model.lost,[0]*12);self.assertEqual(model.known,{})
            finally:observer.close()

    def test_opponent_setup_and_contradictory_public_events_rejected(self):
        model,_=self.initialize(0)
        # Close this test's real observer immediately: only public memory is used.
        _.close()
        with self.assertRaisesRegex(ValueError,'rejects opponent setup'):model.observe(['opponent-setup',self.game['blue_setup']])
        before=(dict(model.tokens),dict(model.known),model.plies)
        with self.assertRaises(ValueError):model.observe(['battle','a4','a3','F','1'])
        self.assertEqual((model.tokens,model.known,model.plies),before)
        with self.assertRaisesRegex(ValueError,'Classic'):model.observe(['rules','1'])


if __name__=='__main__':unittest.main()
