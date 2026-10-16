"""Independent C native-threat oracle; no repository source edits."""
import ctypes as C
import random
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
from campaign_belief_values import worths
from feldmarschall import COUNTS,LAKES
import test_compact_backrow as compact
FLAGS,SOURCES=compact.FLAGS,compact.SOURCES
from risk import threat,quiet_corrections


class NativeRiskOracle(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='public-contact-risk-');p=Path(cls.tmp.name)
  core=p/'core';shutil.copytree(ROOT/'src/core',core)
  with(core/'ai.c').open('a')as f:f.write('\nint16_t research_threat(uint8_t army,const uint8_t*lost,uint8_t rank,uint8_t square){own=army;survey(lost);return threat(square,rank);}\n')
  out=p/'oracle.so'
  subprocess.run(['gcc','-O2','-shared','-fPIC','-std=c99','-Wno-unknown-pragmas','-I'+str(core),'-DAI_TEST',*['-D'+f for f in FLAGS],'-o',str(out),*[str(core/(name+'.c'))for name in SOURCES]],check=True,capture_output=True)
  cls.lib=C.CDLL(str(out));cls.board=(C.c_uint8*100).in_dll(cls.lib,'board')
  cls.lib.research_threat.argtypes=[C.c_uint8,C.POINTER(C.c_uint8),C.c_uint8,C.c_uint8];cls.lib.research_threat.restype=C.c_int16
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def native(self,cells,army,lost,rank,square):
  self.board[:]=cells;return self.lib.research_threat(army*16,(C.c_uint8*12)(*lost),rank,square)
 def test_actual_c_matches_both_sides_all_ranks_and_hidden_nibbles(self):
  helper=compact.CompactBackrowTests('runTest');checked=0
  for army in(0,1):
   for seed in range(12):
    cells,lost=helper.fixture(army,2496000+seed);remaining=helper.hidden(cells,army,lost)
    squares=random.Random(seed).sample([s for s in range(100)if s not in LAKES],12)
    for rank in range(10):
     for square in squares:
      self.assertEqual(threat(cells,army,lost,remaining,rank,square),self.native(cells,army,lost,rank,square));checked+=1
    for nibble in range(12):
     mutated=[(c&240)|nibble if c<254 and bool(c&16)!=bool(army)and not c&32 else c for c in cells]
     self.assertEqual(threat(mutated,army,lost,remaining,0,40),self.native(mutated,army,lost,0,40))
  self.assertEqual(checked,2880)
 def test_source_vacancy_reveals_a_known_scout_ray(self):
  cells=[254 if s in LAKES else 255 for s in range(100)];cells[50]=9;cells[80]=16|32|8;cells[0]=16|32|11;cells[99]=11
  lost=COUNTS[:];lost[8]-=1;lost[11]-=1;remaining=[0]*12
  self.assertEqual(threat(cells,0,lost,remaining,9,40),0)
  after=cells[:];after[50]=255;after[40]=9|64
  expected=worths(lost)[9]
  self.assertEqual(threat(after,0,lost,remaining,9,40),expected)
  self.assertEqual(self.native(after,0,lost,9,40),expected)
 def test_occupancy_control_and_mobile_detail_are_separate(self):
  cells=[255]*100;cells[55]=4;cells[54]=16|12
  remaining=[1,0,0,0,0,0,1,0,0,0,0,0];lost=[0]*12
  flags=[0]*100;bombs=[0]*100;flags[54]=1024;bombs[54]=1024
  rows={54:[.5,0,0,0,0,0,.5,0,0,0,0,0]}
  a=threat(cells,0,lost,remaining,4,55)
  b=threat(cells,0,lost,remaining,4,55,'occupancy',rows,flags,bombs)
  c=threat(cells,0,lost,remaining,4,55,'mobile',rows,flags,bombs)
  self.assertEqual((a,b,c),(11,11,11))
  rows[54]=[0]*12;rows[54][6]=.5;rows[54][10]=.5
  self.assertEqual(threat(cells,0,lost,remaining,4,55,'mobile',rows,flags,bombs),0)
  flags[54]=bombs[54]=0
  self.assertEqual(threat(cells,0,lost,remaining,4,55,'occupancy',rows,flags,bombs),22)
 def test_capture_channel_zero_and_exchangeable_mobile_matches_occupancy(self):
  cells=[254 if s in LAKES else 255 for s in range(100)];cells[60]=4;cells[50]=16|12
  lost=[0]*12;remaining=[1,0,0,0,0,0,1,0,0,0,0,0]
  marginals={50:[.5,0,0,0,0,0,.5,0,0,0,0,0]}
  flag=[0]*100;bomb=[0]*100
  moves=[(60,61),(60,50)]
  rows=quiet_corrections(cells,0,lost,remaining,marginals,flag,bomb,moves)
  self.assertFalse(rows[0]['capture']);self.assertEqual(rows[0]['mobile_vs_occupancy_delta'],0)
  self.assertTrue(rows[1]['capture']);self.assertEqual(rows[1]['mobile_delta'],0)



if __name__=='__main__':unittest.main()
