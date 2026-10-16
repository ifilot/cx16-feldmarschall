"""Real native adapter qualification for mutually exclusive quiet scopes."""
from pathlib import Path
import subprocess,tempfile,unittest
from ai_registry import ROOT,get_policy
from campaign_native_mobile import MobileCaptureBot
from feldmarschall import COUNTS,LAKES

class PublicTerminalModel:
    army=0
    def rank_marginals(self,cells,army,lost,histories):
        assert not histories
        return {},[0]*12
    def posterior(self):return [1.],{'fixture':'fully disclosed terminal position'}

class QuietMobileAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='quiet-mobile-adapter-');cls.observer=Path(cls.tmp.name)/'observer'
        spec=get_policy('student-template-flag-bomb-v1-normal')
        subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Isrc/core',*['-D'+v for v in spec['defines']+['AI_TRACE','AI_TRAINING']],'-o',str(cls.observer),*spec['sources']],cwd=ROOT,check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_real_terminal_flag_scores_preserved_in_every_scope(self):
        for scope in('captures','quiet-occupancy','quiet-mobile'):
            bot=MobileCaptureBot(self.observer,adjustment_scope=scope);bot.model=PublicTerminalModel()
            try:
                cells=[254 if sq in LAKES else 255 for sq in range(100)]
                cells[0]=11;cells[22]=4;cells[23]=16|32|11
                lost=COUNTS[:];lost[11]=0
                bot.observer.ask('position 0 '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000','positionok')
                self.assertEqual(bot.choose(),(22,23));self.assertFalse(bot.last_report['overridden'])
                if scope!='captures':self.assertNotIn('capture_adjustment',bot.last_report)
            finally:bot.close()
    def test_real_no_moves_keeps_scope_and_has_no_candidate_override(self):
        for scope in('captures','quiet-occupancy','quiet-mobile'):
            bot=MobileCaptureBot(self.observer,adjustment_scope=scope);bot.model=PublicTerminalModel()
            try:
                cells=[254 if sq in LAKES else 255 for sq in range(100)];cells[0]=11;cells[99]=16|32|11
                lost=COUNTS[:];lost[11]=0
                bot.observer.ask('position 0 '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000','positionok')
                self.assertIsNone(bot.choose());self.assertEqual(bot.last_report['selected'],None)
                self.assertEqual(bot.last_report['mode'],'template-mobile-captures' if scope=='captures' else 'template-'+scope)
            finally:bot.close()
    def test_scopes_are_classic_normal_and_opt_in(self):
        for scope in('quiet-occupancy','quiet-mobile'):
            bot=MobileCaptureBot(self.observer,adjustment_scope=scope)
            try:
                with self.assertRaises(ValueError):bot.observe(['rules','1'])
            finally:bot.close()
        with self.assertRaises(ValueError):MobileCaptureBot(self.observer,adjustment_scope='all')
        with self.assertRaises(ValueError):MobileCaptureBot(self.observer,difficulty='hard')
    def test_cold_both_sides_mask_private_nibbles_and_no_captures_changed(self):
        from feldmarschall import presets
        own_setup=presets()[0][1]
        for army in(0,1):
            for scope in('quiet-occupancy','quiet-mobile'):
                bot=MobileCaptureBot(self.observer,adjustment_scope=scope)
                try:
                    for line in('new '+('red','blue')[army],'rules 0','seed 2699531','setup '+own_setup):bot.observe(line.split())
                    move=bot.choose();report=bot.last_report
                    self.assertIsNotNone(move);self.assertEqual(report['army'],army)
                    for cell in bytes.fromhex(report['public_board_hex']):
                        if cell<254 and bool(cell&16)!=bool(army)and not cell&32:self.assertEqual(cell&15,12)
                    public=bytes.fromhex(report['public_board_hex'])
                    self.assertTrue(all(public[row['move'][1]]==255 for row in report['quiet_adjustment']['quiet']))
                    self.assertEqual(bool(public[move[0]]&16),bool(army))
                finally:bot.close()

if __name__=='__main__':unittest.main()
