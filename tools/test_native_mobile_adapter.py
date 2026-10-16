"""Real native trace edge cases for the public mobile-capture bridge."""
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

class NativeMobileAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='mobile-adapter-');cls.observer=Path(cls.tmp.name)/'observer'
        spec=get_policy('student-template-flag-bomb-v1-normal')
        subprocess.run(['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Isrc/core',*['-D'+v for v in spec['defines']+['AI_TRACE','AI_TRAINING']],'-o',str(cls.observer),*spec['sources']],cwd=ROOT,check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_actual_known_flag_win_has_no_credit_but_remains_selected(self):
        bot=MobileCaptureBot(self.observer);bot.model=PublicTerminalModel()
        try:
            cells=[254 if sq in LAKES else 255 for sq in range(100)]
            cells[0]=11;cells[22]=4;cells[23]=16|32|11
            lost=COUNTS[:];lost[11]=0
            line='position 0 '+bytes(lost).hex()+' '+bytes(cells).hex()+' ffffffff0000'
            bot.observer.ask(line,'positionok')
            self.assertEqual(bot.choose(),(22,23))
            self.assertFalse(bot.last_report['overridden'])
        finally:bot.close()

if __name__=='__main__':unittest.main()
