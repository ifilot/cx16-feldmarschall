"""Public native belief objectives: quiet routing, fixed-point gain and state."""
import ctypes
from fractions import Fraction
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
import zipfile

from ai_registry import ROOT,get_policy
from campaign_belief_values import root_marginals,gain,worths
from feldmarschall import COUNTS,LAKES
from test_campaign_belief_values import small_root

U8=ctypes.c_uint8
U16=ctypes.c_uint16


class NativeBeliefObjectives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='feld-native-beliefs-')
        cls.folder=Path(cls.temp.name)
        cls.policy=get_policy('student-guard-v1-normal')
        with zipfile.ZipFile(ROOT/cls.policy['archive']) as archive:archive.extractall(cls.folder)
        for name in ('src/core/ai.c','src/core/ai.h'):
            (cls.folder/name).write_bytes((ROOT/name).read_bytes())
        (cls.folder/'probe.c').write_text('#include "src/core/ai.c"\n'
            'void fixture(uint8_t army,const uint8_t*cells,const uint8_t*lost,uint8_t difficulty,uint8_t rules){'
            'unsigned i;memcpy(board,cells,100);game_rules=rules;rules_reset();ai_reset();own=army;'
            'ai_difficulty=difficulty;random_seed(1);survey(lost);'
            'for(i=0;i<12;i++){attack[i][0]=expected(i,0);attack[i][1]=expected(i,1);}}\n'
            'int belief_expected(unsigned rank,unsigned square){return expected_at(rank,square);}\n'
            'int base_expected(unsigned rank,unsigned moved){return expected(rank,moved);}\n'
            'int objective(unsigned square){return plan(square);}\n'
            'void choose(const uint8_t*lost,uint8_t*from,uint8_t*to){ai_move(own,lost,from,to);}\n'
            'unsigned state_size(void){return AI_TEST_STATE_SIZE;}\n'
            'unsigned prior_offset(void){return AI_TEST_PRIOR_OFFSET;}\n'
            'void board_copy(uint8_t*out){memcpy(out,board,100);}\n')
        command=['gcc','-O2','-shared','-fPIC','-std=c99','-Wno-unknown-pragmas','-I.','-Isrc/core',
                 '-DAI_BELIEF_PRIORS','-DAI_TEST','-o',str(cls.folder/'probe.so')]
        command+=['-D'+define for define in cls.policy['defines']]
        command+=['probe.c']+[name for name in cls.policy['sources'][1:] if name!='src/core/ai.c']
        subprocess.run(command,cwd=cls.folder,check=True,capture_output=True)
        cls.lib=ctypes.CDLL(str(cls.folder/'probe.so'))
        cls.lib.fixture.argtypes=[U8,ctypes.POINTER(U8),ctypes.POINTER(U8),U8,U8]
        cls.lib.ai_belief_priors_set.argtypes=[U8,ctypes.POINTER(U16),ctypes.POINTER(U16)]
        cls.lib.ai_belief_priors_set.restype=U8
        cls.lib.ai_belief_priors_valid.restype=U8
        cls.lib.ai_test_save.argtypes=[ctypes.POINTER(U8)];cls.lib.ai_test_load.argtypes=[ctypes.POINTER(U8)]
        cls.lib.choose.argtypes=[ctypes.POINTER(U8),ctypes.POINTER(U8),ctypes.POINTER(U8)]

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def initialize(self,cells,lost,army=0,difficulty=1,rules=0):
        self.cells=(U8*100)(*cells);self.lost=(U8*12)(*lost)
        self.lib.fixture(army,self.cells,self.lost,difficulty,rules)

    def set_priors(self,flag,bomb,army=0):
        return self.lib.ai_belief_priors_set(army,(U16*100)(*flag),(U16*100)(*bomb))

    def state(self):
        state=(U8*self.lib.state_size())();self.lib.ai_test_save(state);return bytes(state)

    def choose(self):
        src,dst=U8(),U8();self.lib.choose(self.lost,ctypes.byref(src),ctypes.byref(dst));return src.value,dst.value

    def routing_fixture(self):
        cells=[254 if square in LAKES else 255 for square in range(100)]
        for square,cell in {84:0,74:10,99:11,30:16|12,39:16|12,20:16|32|8}.items():cells[square]=cell
        lost=COUNTS[:]
        for rank in (8,10,11):lost[rank]-=1
        flag,bomb=[0]*100,[0]*100;flag[39]=4096;bomb[30]=4096
        return cells,lost,flag,bomb

    def test_probabilities_change_persistent_goal_and_quiet_move_without_disclosure(self):
        cells,lost,flag,bomb=self.routing_fixture()
        self.initialize(cells,lost)
        self.assertEqual(self.lib.objective(84),30)
        self.assertEqual(self.choose(),(84,83))
        self.initialize(cells,lost);self.assertEqual(self.set_priors(flag,bomb),1)
        self.assertEqual(self.lib.objective(84),39)
        self.assertEqual(self.choose(),(84,85))
        current=(U8*100)();self.lib.board_copy(current)
        self.assertEqual(bytes(current),bytes(cells))

    def test_counts_and_joint_fixed_point_expectations_match_exact_rational_means(self):
        model,cells,lost,histories,_=small_root()
        for mode in ('counts','joint'):
            probabilities,remaining=root_marginals(cells,0,lost,histories,model,mode)
            flag,bomb=[0]*100,[0]*100
            for square,row in probabilities.items():
                flag[square]=round(row[11]*4096)
                bomb[square]=min(4096-flag[square],round(row[10]*4096))
            self.initialize(cells,lost);self.assertEqual(self.set_priors(flag,bomb),1)
            worth=worths(lost);mobile=sum(remaining[:10])
            for square in histories:
                for rank in range(10):
                    if cells[square]&64:expected=self.lib.base_expected(rank,1)
                    else:
                        expected=(Fraction(flag[square]*2000+bomb[square]*gain(rank,10,worth),4096)+
                            Fraction(4096-flag[square]-bomb[square],4096*mobile)*
                            sum(remaining[r]*gain(rank,r,worth) for r in range(10)))
                        expected=int(expected)
                    self.assertEqual(self.lib.belief_expected(rank,square),expected)

    def test_invalid_setter_is_transactional_and_reset_clears_all_prior_state(self):
        cells,lost,flag,bomb=self.routing_fixture();self.initialize(cells,lost)
        self.assertEqual(self.set_priors(flag,bomb),1);before=self.state()
        for bad_flag,bad_bomb,army in (([65535]*100,bomb,0),(flag,[4096]*100,0),(flag,bomb,1)):
            self.assertEqual(self.set_priors(bad_flag,bad_bomb,army),0);self.assertEqual(self.state(),before)
        self.assertEqual(self.lib.ai_belief_priors_set(0,None,None),0);self.assertEqual(self.state(),before)
        self.lib.ai_reset();self.assertEqual(self.lib.ai_belief_priors_valid(),0)
        self.assertEqual(self.state()[self.lib.prior_offset():],bytes(401))

    def test_save_load_restores_prior_owner_arrays_and_original_memory(self):
        model,cells,lost,_,_=small_root();self.initialize(cells,lost)
        flag,bomb=[0]*100,[0]*100;flag[10]=800;bomb[10]=1600
        self.assertEqual(self.set_priors(flag,bomb),1)
        self.choose();before=self.state()
        self.lib.ai_belief_priors_clear();self.choose()
        self.lib.ai_test_load((U8*len(before))(*before))
        self.assertEqual(self.state(),before)
        self.assertEqual(len(before)-self.lib.prior_offset(),401)

    def test_wrong_army_easy_and_hard_ignore_priors(self):
        cells,lost,flag,bomb=self.routing_fixture()
        for difficulty,owner in ((1,16),(0,0),(2,0)):
            self.initialize(cells,lost,difficulty=difficulty)
            self.assertEqual(self.set_priors(flag,bomb,owner),1)
            self.assertEqual(self.lib.belief_expected(0,39),self.lib.base_expected(0,0))

    def test_concealed_rank_nibble_permutations_cannot_change_goals_scores_or_move(self):
        cells,lost,flag,bomb=self.routing_fixture();results=[]
        for a,b in ((12,12),(0,11),(9,10),(11,0)):
            changed=cells[:];changed[30]=16|a;changed[39]=16|b
            self.initialize(changed,lost);self.set_priors(flag,bomb)
            results.append((self.lib.objective(84),self.lib.belief_expected(0,30),self.lib.belief_expected(0,39),self.choose()))
        self.assertTrue(all(row==results[0] for row in results))

    def test_default_macro_off_binary_matches_immutable_original_core(self):
        # Compile the original frozen source and the source with opt-in guards
        # under the exact same old build recipe; default policies cannot drift.
        with tempfile.TemporaryDirectory(prefix='native-belief-default-') as temp:
            temp=Path(temp);hashes=[]
            for name,current in (('original',False),('guarded',True)):
                folder=temp/name;folder.mkdir()
                with zipfile.ZipFile(ROOT/self.policy['archive']) as archive:archive.extractall(folder)
                if current:
                    for source in ('src/core/ai.c','src/core/ai.h'):(folder/source).write_bytes((ROOT/source).read_bytes())
                program=folder/'engine'
                command=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow',
                    '-DFELDMARSCHALL_AI_ID="student-guard-v1-normal"','-Isrc/core','-o',str(program)]
                command+=['-D'+define for define in self.policy['defines']]+self.policy['sources']
                subprocess.run(command,cwd=folder,check=True,capture_output=True)
                hashes.append(program.read_bytes())
            self.assertEqual(hashes[0],hashes[1])


if __name__=='__main__':unittest.main()
