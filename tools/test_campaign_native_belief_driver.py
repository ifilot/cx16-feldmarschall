"""Mock-native mechanism tests: public events, bounded Q12 and one go only."""
import copy
import io
import unittest
from unittest.mock import patch

from ai_registry import ROOT
from campaign_joint_beliefs import JointSetupBeliefs
from campaign_native_beliefs import NativeBeliefBot,quantize,ONE
from feldmarschall import COUNTS,GLYPHS,LAKES,battle,parse_square,setup_squares

MODEL=ROOT/'ai/models/joint-flag-bomb-beliefs-v1.json'
SETUP=''.join(g*n for g,n in zip(GLYPHS,COUNTS))


class MockObserver:
    def __init__(self,mutate=False):
        self.calls=[];self.mutate=mutate;self.closed=False
    def send(self,line):
        self.calls.append(('send',line));words=line.split()
        if words[0]=='new':
            self.army=int(words[1]=='blue');self.lost=[0]*12;self.cells=[254 if sq in LAKES else 255 for sq in range(100)];self.histories={}
            for owner in (0,1):
                for sq in setup_squares(owner):
                    self.cells[sq]=16*owner|12
                    self.histories[sq]=[sq,sq,sq,sq,16*owner,0,0,12,12,12,4095]
        elif words[0]=='setup':
            for sq,g in zip(setup_squares(self.army),words[1]):self.cells[sq]=16*self.army|GLYPHS.index(g)
        elif words[0] in ('moved','battle'):
            src,dst=map(parse_square,words[1:3]);actor=self.cells[src];history=self.histories.pop(src)
            history[3]=dst;history[5]+=1;history[-1]=1023
            if words[0]=='moved':self.cells[dst]=actor|64;self.histories[dst]=history
            else:
                attacker,defender=(GLYPHS.index(g) for g in words[3:]);outcome=battle(attacker,defender)
                target=self.cells[dst]
                if bool(actor&16)!=bool(self.army) and outcome!='attacker':self.lost[attacker]+=1
                if bool(target&16)!=bool(self.army) and outcome!='defender':self.lost[defender]+=1
                if outcome=='attacker':self.cells[dst]=(actor&240)|32|attacker;self.histories[dst]=history
                elif outcome=='defender':self.cells[dst]=(target&240)|32|defender
                else:self.cells[dst]=255;self.histories.pop(dst,None)
            self.cells[src]=255
    def ask(self,line,prefix):
        self.calls.append(('ask',line))
        if line=='setup':
            self.send('setup '+SETUP);return SETUP
        if line=='public':
            cells=self.cells[:]
            if self.mutate:
                for sq,cell in enumerate(cells):
                    if cell<254 and bool(cell&16)!=bool(self.army) and not cell&32:cells[sq]=(cell&240)|(sq%12)
            return f'{self.army} {bytes(cells).hex()} {bytes(self.lost).hex()} ffffffffffff'
        if line.startswith('memory '):return ' '.join(map(str,self.histories[parse_square(line.split()[1])]))
        if line.startswith('belief-priors '):
            packet=line.split()[1];assert len(packet)==800;values=[int(packet[i:i+4],16) for i in range(0,800,4)]
            assert all(f+b<=4096 for f,b in zip(values[:100],values[100:]));return ''
        if line=='go':return 'a4 a5'
        if line.startswith('played '):return ''
        if line=='isready':return ''
        raise AssertionError('unexpected native request '+line)
    def close(self):self.closed=True


class NativeBeliefTests(unittest.TestCase):
    def create(self,mode='joint',mutate=False,bare=False):
        observer=MockObserver(mutate);bot=NativeBeliefBot(observer,MODEL,mode)
        bot.observe(['new','red']);bot.observe(['setup'] if bare else ['setup',SETUP])
        return bot,observer

    def test_one_public_posterior_packet_then_native_go_without_rollouts(self):
        for mode in ('counts','joint'):
            bot,observer=self.create(mode)
            self.assertEqual(bot.choose(),(60,50))
            requests=[line for method,line in observer.calls if method=='ask']
            self.assertTrue(requests[-2].startswith('belief-priors '));self.assertEqual(requests[-1],'go')
            self.assertEqual(sum(line=='go' for line in requests),1)
            self.assertFalse(any('search ' in line for line in requests))
            q=bot.last_report['q12'];self.assertEqual(sum(q['flag']),ONE);self.assertEqual(sum(q['bomb']),6*ONE)
            self.assertTrue(all(f+b+m==ONE for f,b,m in zip(q['flag'],q['bomb'],q['mobile'])))
            for sq in setup_squares(0):self.assertEqual(q['flag'][sq]+q['bomb'][sq],0)

    def test_controlled_rounding_preserves_exact_mass_when_no_mobile_rank_remains(self):
        marginals={sq:[0.]*10+[6/7,1/7] for sq in range(7)}
        remaining=[0]*10+[6,1]
        flag,bomb,mobile,packet=quantize(marginals,remaining)
        self.assertEqual(sum(flag),ONE);self.assertEqual(sum(bomb),6*ONE)
        self.assertEqual(mobile[:7],[0]*7);self.assertEqual(len(packet),800)
        for sq in range(7):
            self.assertLess(abs(flag[sq]/ONE-1/7),1/ONE)
            self.assertLess(abs(bomb[sq]/ONE-6/7),1/ONE)

    def test_bare_setup_is_recorded_as_own_private_setup(self):
        bot,observer=self.create(bare=True)
        self.assertEqual(bot.model.known[(0,0)],0)
        self.assertEqual(sum(owner==0 for owner,_ in bot.model.known),40)
        self.assertFalse(any(owner==1 for owner,_ in bot.model.known))
        bot.choose()

    def test_actual_public_events_and_played_confirmation_are_forwarded(self):
        bot,observer=self.create()
        for words in [['moved','a4','a5'],['moved','a7','a6'],['battle','a5','a6','1','2']]:bot.observe(words)
        self.assertEqual(bot.model.plies,3);self.assertEqual(bot.model.lost[1],1)
        self.assertEqual(bot.model.known[(1,0)],1)
        bot.observe(['played','a6','b6'])
        self.assertEqual(bot.model.plies,3)
        self.assertIn(('ask','played a6 b6'),observer.calls)
        bot.choose();self.assertEqual(bot.last_report['remaining'][1],0)

    def test_concealed_nibbles_cannot_change_decision_packet_or_report(self):
        for mode in ('counts','joint'):
            reports=[]
            for mutate in (False,True):
                bot,_=self.create(mode,mutate)
                bot.observe(['moved','a4','a5']);bot.observe(['moved','a7','a6']);bot.choose()
                report=copy.deepcopy(bot.last_report);report.pop('elapsed_seconds');reports.append(report)
            self.assertEqual(reports[0],reports[1])

    def test_private_setups_and_optional_rules_are_rejected_before_forwarding(self):
        bot,observer=self.create();before=list(observer.calls)
        with self.assertRaisesRegex(ValueError,'rejects opponent setup'):bot.observe(['opponent-setup',SETUP])
        with self.assertRaisesRegex(ValueError,'Classic'):bot.observe(['rules','1'])
        self.assertEqual(before,observer.calls)

    def test_protocol_bare_setup_and_new_reset(self):
        bot,observer=self.create()
        commands='new red\nsetup\ngo\nnew blue\nsetup\nisready\nquit\n'
        with patch('sys.stdin',io.StringIO(commands)),patch('sys.stdout',new_callable=io.StringIO) as output:bot.run()
        self.assertIn('setup '+SETUP,output.getvalue());self.assertIn('move a4 a5',output.getvalue())
        self.assertTrue(observer.closed);self.assertEqual(bot.model.army,1);self.assertEqual(bot.model.plies,0)


if __name__=='__main__':unittest.main()
