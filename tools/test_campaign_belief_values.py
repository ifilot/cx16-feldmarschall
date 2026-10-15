"""Exact enumeration, frozen-C gain parity and honest input invariance."""
import itertools
import copy
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
import zipfile

from ai_registry import ROOT,get_policy
from campaign_belief_values import adjustments,gain,immobile_marginals,native_expected,root_marginals,worths
from campaign_joint_beliefs import JointSetupBeliefs,neighbors,subset_sum
from feldmarschall import COUNTS,GLYPHS,LAKES,setup_squares

MODEL=ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'


def small_root(moved=True):
    model=JointSetupBeliefs.load(MODEL)
    own=''.join(glyph*count for glyph,count in zip(GLYPHS,COUNTS))
    model.observe(['new','red']);model.observe(['setup',own])
    sites={19,20,21,22,30,31,32}
    unknown_ranks=[0,1,8,9,10,10,11]
    other=COUNTS[:]
    for rank in unknown_ranks:other[rank]-=1
    known=[rank for rank,count in enumerate(other) for _ in range(count)]
    cells=[254 if square in LAKES else 255 for square in range(100)]
    for square,glyph in zip(setup_squares(0),own):cells[square]=GLYPHS.index(glyph)
    histories={};index=0
    for origin,square in enumerate(setup_squares(1)):
        if origin in sites:
            cells[square]=16|12
            mask=1023 if moved and origin==19 else 4095
            if mask==1023:
                cells[square]|=64;model.moved.add((1,origin))
            histories[square]=[square,origin,square,square,16,int(mask==1023),0,12,12,12,mask]
        else:
            rank=known[index];index+=1;cells[square]=16|32|rank;model.known[1,origin]=rank
    return model,cells,[0]*12,histories,sites


class BeliefCaptureValues(unittest.TestCase):
    def test_exact_immobile_marginals_match_enumerated_joint_assignments(self):
        model=JointSetupBeliefs.load(MODEL);sites={20,21,22,23,30,31,32,33};fixed={19,39}
        result=immobile_marginals(model,sites,sites,fixed)
        weights=[]
        for flag in sites:
            for bombs in itertools.combinations(sorted(sites-{flag}),4):
                for style in range(2):
                    theta=model.theta[style]
                    weight=(model.weights[style]*model.phi[style][flag//10]/10*
                        math.exp(theta*len(neighbors(flag)&(set(bombs)|fixed)))/subset_sum(len(neighbors(flag)),39,6,theta))
                    weights.append((flag,bombs,weight))
        mass=sum(w for _,_,w in weights)
        for site in sites:
            self.assertAlmostEqual(result[site][0],sum(w for f,_,w in weights if f==site)/mass,places=12)
            self.assertAlmostEqual(result[site][1],sum(w for _,bombs,w in weights if site in bombs)/mass,places=12)
        self.assertAlmostEqual(sum(row[0] for row in result.values()),1)
        self.assertAlmostEqual(sum(row[1] for row in result.values()),4)

    def test_joint_mobile_rank_marginals_match_full_assignment_enumeration(self):
        model,cells,lost,histories,sites=small_root()
        result,remaining=root_marginals(cells,0,lost,histories,model,'joint')
        fixed={origin for (army,origin),rank in model.known.items() if army==1 and rank==10}
        immobile=sites-{19};weights=[]
        for flag in immobile:
            for bombs in itertools.combinations(sorted(immobile-{flag}),2):
                available=sorted(sites-{flag}-set(bombs))
                for ranks in itertools.permutations((0,1,8,9)):
                    assignment=dict(zip(available,ranks));assignment[flag]=11
                    assignment.update({origin:10 for origin in bombs})
                    for style in range(2):
                        theta=model.theta[style]
                        weight=(model.weights[style]*model.phi[style][flag//10]/10*
                            math.exp(theta*len(neighbors(flag)&(set(bombs)|fixed)))/subset_sum(len(neighbors(flag)),39,6,theta))
                        weights.append((assignment,weight))
        mass=sum(weight for _,weight in weights)
        for origin in sites:
            square=setup_squares(1)[origin]
            for rank in range(12):
                expected=sum(weight for assignment,weight in weights if assignment[origin]==rank)/mass
                self.assertAlmostEqual(result[square][rank],expected,places=11)
        self.assertEqual(result[setup_squares(1)[19]][10:],[0.,0.])

    def test_counts_control_preserves_inventory_and_matches_uniform_joint_prior(self):
        model,cells,lost,histories,_=small_root()
        uniform=JointSetupBeliefs(dict(schema=model.document['schema'],weights=[.5,.5],
                                      phi=[[.25]*4,[.25]*4],theta=[0.,0.]))
        uniform.army=model.army;uniform.tokens=model.tokens;uniform.known=model.known;uniform.lost=model.lost
        counts,remaining=root_marginals(cells,0,lost,histories,mode='counts')
        joint,_=root_marginals(cells,0,lost,histories,uniform,'joint')
        for square,row in counts.items():
            self.assertAlmostEqual(sum(row),1)
            for a,b in zip(row,joint[square]):self.assertAlmostEqual(a,b)
        for rank in range(12):self.assertAlmostEqual(sum(row[rank] for row in counts.values()),remaining[rank])

    def test_hidden_nibbles_rng_and_public_model_state_are_unchanged(self):
        model,cells,lost,histories,_=small_root()
        before=copy.deepcopy(model.__dict__)
        random_before=random.getstate()
        first=root_marginals(cells,0,lost,histories,model)
        mutated=cells[:]
        for square in histories:mutated[square]=(mutated[square]&240)|(square%12)
        self.assertEqual(first,root_marginals(mutated,0,lost,histories,model))
        self.assertEqual(before,model.__dict__)
        self.assertEqual(random_before,random.getstate())

    def test_capture_adjustment_leaves_quiet_known_and_forced_wins_unchanged(self):
        model,cells,lost,histories,sites=small_root()
        unknown=setup_squares(1)[20];known=next(square for square,cell in enumerate(cells) if cell<254 and cell&16 and cell&32)
        scores={(60,40):12,(60,known):99,(60,unknown):5,(61,unknown):30000}
        values,report=adjustments(cells,0,lost,histories,scores,model,'joint')
        self.assertEqual(set(values),{(60,unknown)})
        self.assertFalse(report['behavioral_reweighting'])
        self.assertTrue(math.isfinite(values[60,unknown]))

    def test_dynamic_specialist_values_and_flag_win_match_classic_native(self):
        live=worths([0]*12);dead=[0]*12;dead[0]=1;dead[10]=6
        late=worths(dead)
        self.assertEqual((live[7],live[9]),(40,100))
        self.assertEqual((late[7],late[9]),(25,15))
        self.assertEqual(gain(9,0,live),400)
        self.assertEqual(gain(7,10,live),20)
        self.assertEqual(gain(0,0,live),0)
        self.assertEqual(gain(8,11,live),2000)
        self.assertEqual(native_expected(8,False,[1]+[0]*11,live),-10)


class FrozenNativeExpected(unittest.TestCase):
    def test_python_native_expected_matches_original_frozen_c(self):
        policy=get_policy('student-guard-v1-normal')
        with tempfile.TemporaryDirectory(prefix='belief-native-gain-') as temporary:
            temporary=Path(temporary)
            with zipfile.ZipFile(ROOT/policy['archive']) as archive:archive.extractall(temporary)
            (temporary/'probe.c').write_text('#include <stdio.h>\n#include <stdlib.h>\n#include "src/core/ai.c"\n'
                'int main(void){unsigned a,i;char losthex[25],cells[201],byte[3]={0};uint8_t lost[12];'
                'game_rules=0;while(scanf("%u %24s %200s",&a,losthex,cells)==3){own=a?CELL_BLUE:0;'
                'for(i=0;i<12;i++){byte[0]=losthex[2*i];byte[1]=losthex[2*i+1];lost[i]=strtoul(byte,0,16);}'
                'for(i=0;i<100;i++){byte[0]=cells[2*i];byte[1]=cells[2*i+1];board[i]=strtoul(byte,0,16);}'
                'survey(lost);for(i=0;i<10;i++)printf("%d %d ",expected(i,0),expected(i,1));puts("");}return 0;}')
            executable=temporary/'probe'
            command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-I.','-Isrc/core','-o',str(executable)]
            command+=['-D'+define for define in policy['defines']]
            command+=['probe.c']+[name for name in policy['sources'][1:] if name!='src/core/ai.c']
            subprocess.run(command,cwd=temporary,capture_output=True,check=True)
            rng=random.Random(2393001);payload=[];expected=[]
            for _ in range(80):
                model,cells,lost,histories,_=small_root(moved=bool(rng.randrange(2)))
                # Disclosed casualties change both count priors and dynamic
                # values; remove chosen visible enemy cells accordingly.
                for square,cell in enumerate(cells):
                    if cell<254 and cell&16 and cell&32 and rng.random()<.25:
                        lost[cell&15]+=1;cells[square]=255
                remaining=[count-number for count,number in zip(COUNTS,lost)]
                for cell in cells:
                    if cell<254 and cell&16 and cell&32:remaining[cell&15]-=1
                worth=worths(lost)
                expected.append([native_expected(rank,moved,remaining,worth) for rank in range(10) for moved in (False,True)])
                payload.append('0 '+bytes(lost).hex()+' '+bytes(cells).hex()+'\n')
            result=subprocess.run([str(executable)],input=''.join(payload),capture_output=True,text=True,check=True)
            self.assertEqual(expected,[list(map(int,line.split())) for line in result.stdout.splitlines()])


if __name__=='__main__':unittest.main()
