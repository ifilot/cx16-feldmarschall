"""Public-event and analytic-oracle tests for the opt-in Q24 target prototype."""
import ctypes as C
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from campaign_template_beliefs import TEMPLATES,TemplateMixtureBeliefs
from test_campaign_template_beliefs import public_inputs
from campaign_native_beliefs import quantize
from feldmarschall import COUNTS,GLYPHS,LAKES,Position,setup_squares,square_name,random_setup

ROOT=Path(__file__).resolve().parents[1]


class TargetTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='template-target-test-')
        directory=Path(cls.temp.name)
        wrapper=directory/'wrapper.c'
        wrapper.write_text('''#include "ai_template.h"\n#include "ai_memory.h"\n#include "ai.h"\n#include "rules.h"\nvoid fixture_reset(void){rules_reset();ai_memory_reset();ai_difficulty=AI_NORMAL;ai_template_valid=0;}\nvoid fixture_infer(unsigned char owner){ai_memory_sync();ai_template_begin(owner);}\n''')
        command=['cc','-shared','-fPIC','-O2','-std=c99','-Wall','-Wno-unknown-pragmas','-DAI_TEMPLATE_PRIOR_Q24','-DAI_MEMORY','-DAI_TEST','-I'+str(ROOT/'src/core'),'-o',str(directory/'test.so'),str(wrapper)]
        command += [str(ROOT/'src/core'/n) for n in ('ai_template.c','ai_memory.c','ai_level.c','board.c','pieces.c','rules.c')]
        subprocess.run(command,check=True,capture_output=True,text=True)
        cls.lib=C.CDLL(str(directory/'test.so'))
        cls.board=(C.c_uint8*100).in_dll(cls.lib,'board')
        cls.status=C.c_uint8.in_dll(cls.lib,'ai_template_status')
        cls.valid=C.c_uint8.in_dll(cls.lib,'ai_template_valid')
        for n in ('ai_template_test_flags','ai_template_test_bombs'):getattr(cls.lib,n).restype=C.POINTER(C.c_uint16)
        cls.lib.ai_template_test_evidence.restype=C.c_uint32
        cls.lib.ai_template_test_mask.restype=C.c_uint8
        cls.lib.ai_template_test_rank.argtypes=[C.c_uint8,C.c_uint8]
        cls.records=[]

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def initialize(self,setups,initialize=True):
        self.position=Position()
        for army,setup in enumerate(setups):self.position.place(army,setup)
        self.models=[]
        for army in (0,1):
            m=TemplateMixtureBeliefs();m.observe(['new',('red','blue')[army]]);m.observe(['setup',setups[army]]);self.models.append(m)
        self.lib.fixture_reset()
        C.c_uint8.in_dll(self.lib,'game_rules').value=0
        self.write_board()
        if initialize:self.lib.ai_template_start()

    def write_board(self):
        for sq,cell in enumerate(self.position.cells):
            self.board[sq]=254 if sq in LAKES else 255 if cell is None else cell[0]*16+cell[1]+64*cell[2]+32*cell[3]

    def infer(self,army,mutate=None):
        original=list(self.board)
        for sq,value in enumerate(original):
            if value<254 and bool(value&16)!=bool(army) and not value&32:
                self.board[sq]=(value&240)|(12 if mutate is None else mutate(sq))
        self.lib.fixture_infer(army*16)
        status=self.status.value
        result=None
        if self.valid.value:
            result=([self.lib.ai_template_test_flags()[i] for i in range(40)],
                    [self.lib.ai_template_test_bombs()[i] for i in range(40)])
        for sq,value in enumerate(original):self.board[sq]=value
        return status,result

    def check_oracle(self,army):
        status,arrays=self.infer(army);self.assertEqual(status,4)
        m=self.models[army];cells,lost,h=public_inputs(m);p,remaining=m.rank_marginals(cells,army,lost,h)
        py=quantize(p,remaining)
        mask=sum(1<<i for i,w in enumerate(m.posterior()[0][:-1]) if w>0)
        self.assertEqual(self.lib.ai_template_test_mask(),mask)
        true_e=math.exp(m.posterior()[1]['background_log_evidence'])
        self.assertLessEqual(abs(self.lib.ai_template_test_evidence()/2**24-true_e),40/2**24+1e-12)
        flags,bombs=arrays
        self.assertEqual(sum(flags),remaining[11]*4096);self.assertEqual(sum(bombs),remaining[10]*4096)
        self.assertTrue(all(0<=f+b<=4096 for f,b in zip(flags,bombs)))
        delta=0
        for origin,start in enumerate(setup_squares(1-army)):
            squares=[sq for sq,token in m.tokens.items() if token==(1-army,origin)]
            if not squares:continue
            sq=squares[0]
            delta=max(delta,abs(flags[origin]-py[0][sq]),abs(bombs[origin]-py[1][sq]))
        self.assertLessEqual(delta,1)
        self.records.append(dict(army=army,mask=mask,max_q12_delta=delta,status=status))
        # Exact native gain oracle after the deliberate Q12 quantization.
        worth=[400,200,100,75,45,30,15,25,10,100,20,1000]
        if lost[10]<6:worth[7]=40
        if lost[0]==1:worth[9]=15
        def gain(a,d):
            if d==11:return 2000
            if d==10:return worth[d] if a==7 else -worth[a]
            if a==9 and d==0:return worth[d]
            if a==d:return 0
            return worth[d] if a<d else -worth[a]
        H=sum(remaining[:10])
        for a in range(10):
            self.lib.ai_template_actor(a)
            row=(C.c_int16*100).in_dll(self.lib,'ai_template_transfer')
            for origin in range(40):
                token=(1-army,origin)
                squares=[sq for sq,t in m.tokens.items() if t==token]
                if not squares or token in m.known or token in m.moved:continue
                sq=squares[0];f,b=flags[origin],bombs[origin]
                immobile=f*2000+b*gain(a,10)
                numerator=immobile*H+(4096-f-b)*sum(n*gain(a,r) for r,n in enumerate(remaining[:10])) if H else immobile
                denominator=4096*H if H else 4096
                expected=(abs(numerator)//denominator)*(1 if numerator>=0 else -1)
                self.assertEqual(row[sq],expected)

    def move(self,src,dst):
        attacker=self.position.cells[src];defender=self.position.cells[dst]
        if defender:
            words=['battle',square_name(src),square_name(dst),GLYPHS[attacker[1]],GLYPHS[defender[1]]]
            self.position.fight(src,dst,attacker[1],defender[1])
        else:
            words=['moved',square_name(src),square_name(dst)];self.position.move(src,dst)
        self.lib.rules_apply(src,dst)
        for m in self.models:m.observe(words)
        expected=[254 if sq in LAKES else 255 if cell is None else cell[0]*16+cell[1]+64*cell[2]+32*cell[3] for sq,cell in enumerate(self.position.cells)]
        self.assertEqual(list(self.board),expected)

    def test_all_template_constants_both_orientations_and_hidden_nibbles(self):
        for t,setup in enumerate(TEMPLATES):
            self.assertEqual([self.lib.ai_template_test_rank(t,i) for i in range(40)],[GLYPHS.index(g) for g in setup])
            self.initialize([setup,TEMPLATES[t^1]])
            for army in (0,1):
                self.check_oracle(army)
                normal=self.infer(army)
                self.assertEqual(normal,self.infer(army,lambda sq:(sq*7+t)%16))

    def test_first_blue_choice_after_opponent_quiet_long_scout_and_capture(self):
        setup='9'+''.join(g*n for g,n in zip(GLYPHS,COUNTS))
        setup=setup[:1]+setup[1:].replace('9','',1)
        for dst in (50,40,30):
            self.initialize([setup,TEMPLATES[0]])
            self.move(60,dst)
            self.check_oracle(1)
            if dst!=50:self.assertEqual(self.models[1].known[0,0],8)

    def test_public_legal_games_capture_origins_and_no_quantization_fallback(self):
        rng=random.Random(740019)
        for number in range(4):
            self.initialize([random_setup(rng),TEMPLATES[number]])
            for ply in range(120):
                legal=self.position.moves(ply%2)
                if not legal:break
                captures=[m for m in legal if self.position.cells[m[1]]]
                self.move(*rng.choice(captures or legal))
                for army in (0,1):self.check_oracle(army)

    def test_late_reset_forget_and_memory_save_load_validity(self):
        self.initialize([TEMPLATES[0],TEMPLATES[1]])
        state=(C.c_uint8*942)();self.lib.ai_memory_save(state)
        self.lib.ai_template_forget();self.assertEqual(self.infer(0)[0],1)
        self.lib.ai_memory_load(state);self.check_oracle(0)
        legal=self.position.moves(0);self.move(*legal[0]);self.lib.ai_memory_reset()
        self.assertEqual(self.infer(1)[0],1)
        self.initialize([TEMPLATES[0],TEMPLATES[1]])
        self.lib.ai_template_forget();self.assertEqual(self.infer(0)[0],1)

    def test_immobile_only_background_rounding_and_negative_truncation(self):
        # A hard-public-evidence snapshot: every mobile origin has been seen,
        # seven immobile origins remain concealed. This forces F/B row conflicts.
        self.initialize([random_setup(random.Random(817)),random_setup(random.Random(818))])
        for army in (0,1):
            for origin,sq in enumerate(setup_squares(army)):
                rank=self.position.cells[sq][1]
                if rank<10:
                    self.position.cells[sq][3]=True
                    for model in self.models:model.known[army,origin]=rank
        self.write_board()
        for army in (0,1):self.check_oracle(army)

    def test_missing_initial_capture_history_and_nonclassic_disable(self):
        setup='9'+''.join(g*n for g,n in zip(GLYPHS,COUNTS))
        setup=setup[:1]+setup[1:].replace('9','',1)
        self.initialize([setup,TEMPLATES[0]],initialize=False)
        self.move(60,30)
        self.assertEqual(self.infer(1)[0],1)
        self.initialize([setup,TEMPLATES[0]])
        C.c_uint8.in_dll(self.lib,'game_rules').value=1
        self.assertEqual(self.infer(1)[0],0)


if __name__=='__main__':unittest.main()
