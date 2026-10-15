"""New template driver against the immutable v3 opt-in native observer."""
import copy
import shlex
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

from ai_registry import ROOT,build_policy,get_policy
from campaign_native_template import NativeTemplateBot
from campaign_native_beliefs import ONE
from feldmarschall import COUNTS,Engine,LAKES,setup_squares,valid_setup,square_name
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay

POLICY='student-counts-belief-objectives-v3-normal'

class AlterPublicNibbles:
    def __init__(self,engine,alter=False):self.engine=engine;self.alter=alter;self.calls=[]
    def send(self,line):self.calls.append(line);return self.engine.send(line)
    def ask(self,line,prefix):
        self.calls.append(line);result=self.engine.ask(line,prefix)
        if line=='public' and self.alter:
            army,board,lost,shuttle=result.split();cells=list(bytes.fromhex(board))
            for sq,c in enumerate(cells):
                if c<254 and bool(c&16)!=bool(int(army)) and not c&32:cells[sq]=(c&240)|(sq%12)
            return ' '.join((army,bytes(cells).hex(),lost,shuttle))
        return result
    def close(self):self.engine.close()

class NativeTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        program,_=build_policy(POLICY);cls.observer=program.parent/'observer'
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as saved:cls.game=saved.game(9)
        states,_=replay(cls.game);cls.events=public_events(cls.game,states)
    def bot(self,army,alter=False,bare=False):
        observer=AlterPublicNibbles(Engine(shlex.quote(str(self.observer))),alter)
        bot=NativeTemplateBot(observer)
        for command in ('new '+('red','blue')[army],'rules 0','seed 1729'):
            bot.observe(command.split())
        setup=bot.observe(['setup'] if bare else ['setup',self.game[('red_setup','blue_setup')[army]]])
        return bot,observer,setup
    def verify_inventory(self,report):
        q=report['q12'];remaining=report['remaining']
        self.assertEqual(sum(q['flag']),remaining[11]*ONE);self.assertEqual(sum(q['bomb']),remaining[10]*ONE)
        self.assertTrue(all(f+b+m==ONE for f,b,m in zip(q['flag'],q['bomb'],q['mobile'])))
        for row in report['marginals'].values():self.assertAlmostEqual(sum(row),1.,places=11)
        for rank in range(12):self.assertAlmostEqual(sum(row[rank] for row in report['marginals'].values()),remaining[rank],places=10)
        self.assertAlmostEqual(sum(report['component_posterior']['template_probabilities'])+report['component_posterior']['background_probability'],1.)
    def test_real_history_both_sides_private_nibbles_packets_and_choices(self):
        for army in (0,1):
            bots=[self.bot(army,alter)[0] for alter in (False,True)]
            try:
                for ply in range(81):
                    if ply in (0,20,40,80):
                        reports=[]
                        for bot in bots:
                            self.assertIsNotNone(bot.choose());self.verify_inventory(bot.last_report)
                            report=copy.deepcopy(bot.last_report);report.pop('elapsed_seconds');reports.append(report)
                        self.assertEqual(*reports)
                    if ply<80:
                        for bot in bots:bot.observe(self.events[ply].split())
            finally:
                for bot in bots:bot.close()
    def test_generated_own_setup_and_reset(self):
        for army in (0,1):
            bot,observer,setup=self.bot(army,bare=True)
            try:
                self.assertTrue(valid_setup(setup));self.assertEqual(sum(owner==army for owner,_ in bot.model.known),40)
                first=bot.choose();self.assertIsNotNone(first);self.verify_inventory(bot.last_report)
                bot.observe(['new',('red','blue')[army]])
                self.assertIsNone(bot.last_report);self.assertEqual(bot.model.known,{})
                state=bytes.fromhex(observer.ask('strategy','strategy'));self.assertEqual(state[-401:],bytes(401))
                bot.observe(['seed','1729']);self.assertEqual(bot.observe(['setup']),setup)
                self.assertEqual(bot.choose(),first)
            finally:bot.close()
    def test_no_external_model_and_one_native_go(self):
        bot,observer,_=self.bot(0)
        try:
            bot.choose();self.assertEqual(sum(call=='go' for call in observer.calls),1)
            self.assertTrue(observer.calls[-2].startswith('belief-priors '));self.assertEqual(observer.calls[-1],'go')
            self.assertFalse(any(call.startswith(('search ','opponent-setup ')) for call in observer.calls))
            self.assertIn('exchangeable mobile',bot.last_report['native_approximation'])
            before=list(observer.calls)
            with self.assertRaises(ValueError):bot.observe(['opponent-setup',self.game['blue_setup']])
            self.assertEqual(observer.calls,before)
        finally:bot.close()
    def test_publicly_deduced_adjacent_flag_win_both_sides(self):
        # Public-consistent late position: all other enemy original identities
        # were revealed, leaving the sole concealed slot logically the Flag.
        for army in (0,1):
            bot,observer,_=self.bot(army)
            try:
                enemy=1-army;target=setup_squares(enemy)[0];scout=setup_squares(enemy)[1]
                source=target+(10 if army==0 else -10);ownflag=setup_squares(army)[-1]
                cells=[254 if sq in LAKES else 255 for sq in range(100)]
                cells[source]=army*16|1|64;cells[ownflag]=army*16|11
                cells[target]=enemy*16|12;cells[scout]=enemy*16|32|8
                lost=list(COUNTS);lost[11]-=1;lost[8]-=1
                remaining=list(COUNTS);remaining[11]-=1;remaining[8]-=1
                original=[11,8]+[rank for rank,count in enumerate(remaining) for _ in range(count)]
                bot.model.known={(enemy,o):rank for o,rank in enumerate(original) if o}
                bot.model.known[army,0]=1;bot.model.known[army,39]=11
                bot.model.tokens={source:(army,0),ownflag:(army,39),target:(enemy,0),scout:(enemy,1)}
                bot.model.moved={(army,0)};bot.model.lost=lost
                observer.send(f'position {army} {bytes(lost).hex()} {bytes(cells).hex()} ffffffff0000')
                self.assertEqual(bot.choose(),(source,target));self.verify_inventory(bot.last_report)
                self.assertEqual(bot.last_report['q12']['flag'][target],ONE)
            finally:bot.close()

    def test_existing_v3_native_driver_remains_byte_identical(self):
        spec=get_policy(POLICY)
        with zipfile.ZipFile(ROOT/spec['archive']) as archive:
            self.assertEqual(archive.read('tools/campaign_native_beliefs.py'),
                             (ROOT/'tools/campaign_native_beliefs.py').read_bytes())

    def test_entrypoint_protocol_bare_setup(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/campaign_native_template.py'),'--observer',str(self.observer)],
            input='feldmarschall\nnew red\nrules 0\nseed 1990\nsetup\nisready\ngo\nquit\n',
            text=True,capture_output=True,check=True,timeout=15)
        self.assertIn('readyok',result.stdout)
        self.assertTrue(any(line.startswith('setup ') and valid_setup(line.split()[1]) for line in result.stdout.splitlines()))
        self.assertTrue(any(line.startswith('move ') for line in result.stdout.splitlines()))

if __name__=='__main__':unittest.main()
