"""Isolate the mobile-rank expectation without changing immobile information."""
import unittest
from campaign_mobile_capture import adjustments,cdiv

class MobileCaptureTests(unittest.TestCase):
    def fixture(self,army=0,moved=False):
        cells=[255]*100;cells[0]=army*16|11;cells[22]=army*16|4;cells[23]=(1-army)*16|12|(64 if moved else 0)
        remaining=[1,0,0,0,0,0,1,0,0,0,0,0]
        row=[.5,0,0,0,0,0,.5,0,0,0,0,0]
        return cells,remaining,row
    def call(self,cells,remaining,row,scores=None,credit=None,army=0,flag=None,bomb=None):
        return adjustments(cells,army,[0]*12,remaining,{23:row},flag or [0]*100,bomb or [0]*100,scores or {(22,23):0},credit or {(22,23):0})
    def test_exchangeable_mobile_posterior_is_exact_zero_for_all_attackers_and_sides(self):
        for army in (0,1):
            for moved in (False,True):
                for rank in range(10):
                    cells,remaining,row=self.fixture(army,moved);cells[22]=army*16|rank
                    self.assertEqual(self.call(cells,remaining,row,army=army)[0][22,23],0)
    def test_same_immobile_masses_isolate_mobile_identity(self):
        cells,remaining,row=self.fixture();f=[0]*100;b=[0]*100;f[23]=512;b[23]=1024
        row=[0]*12;row[6]=.625;row[10]=.25;row[11]=.125
        delta,report=self.call(cells,remaining,row,flag=f,bomb=b)
        self.assertGreater(delta[22,23],0)
        before=report['captures'][0]['original_capture_gain'];after=report['captures'][0]['replacement_capture_gain']
        self.assertEqual(before,cdiv(512*2000*2+1024*(-45)*2+2560*(-45+15),4096*2))
        self.assertEqual(after,cdiv(512*2000+1024*(-45)+2560*15,4096))
    def test_hidden_nibbles_never_change_scores(self):
        for army in (0,1):
            cells,remaining,row=self.fixture(army);row=[0]*12;row[6]=1
            expected=self.call(cells,remaining,row,army=army)
            for hidden in range(12):
                cells[23]=(cells[23]&240)|hidden
                self.assertEqual(self.call(cells,remaining,row,army=army),expected)
    def test_near_flag_bonus_threshold_is_recomputed_with_native_danger_credit(self):
        cells,remaining,row=self.fixture();cells[0]=255;cells[24]=11
        row=[0]*12;row[6]=1
        delta,report=self.call(cells,remaining,row,credit={(22,23):10})
        entry=report['captures'][0]
        self.assertEqual((entry['bonus_before'],entry['bonus_after']),(0,40))
        self.assertEqual(delta[22,23],entry['replacement_capture_gain']-entry['original_capture_gain']+40)
    def test_quiet_and_disclosed_moves_keep_scores_and_missing_credit_fails(self):
        cells,remaining,row=self.fixture();scores={(22,23):0,(22,12):5}
        delta,_=self.call(cells,remaining,row,scores=scores);self.assertEqual(delta[22,12],0)
        cells[23]|=32
        self.assertEqual(self.call(cells,remaining,row,scores=scores)[0],dict.fromkeys(scores,0))
        cells[23]&=~32
        with self.assertRaises(ValueError):adjustments(cells,0,[0]*12,remaining,{23:row},[0]*100,[0]*100,scores,{})

    def test_existing_probe_bonus_precedes_near_flag_threshold(self):
        cells,remaining,row=self.fixture();cells[0]=255;cells[24]=11;cells[22]=6
        row=[0]*12;row[0]=1
        delta,report=self.call(cells,remaining,row)
        entry=report['captures'][0]
        self.assertEqual(entry['original_capture_gain'],-7)
        self.assertEqual(entry['replacement_capture_gain'],-15)
        self.assertEqual((entry['bonus_before'],entry['bonus_after']),(40,0))
        self.assertEqual(delta[22,23],-48)

if __name__=='__main__':unittest.main()
