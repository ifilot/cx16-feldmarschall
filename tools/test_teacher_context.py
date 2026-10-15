"""Behavioral checks for permitted strategic-state transfer into sampled rollouts."""
import json
from pathlib import Path
import random
import subprocess
import unittest

from ai_registry import ROOT, build_policy
from feldmarschall import LAKES, Position, random_setup
from teacher_bot import TeacherBot
from train_ai_student import sample_world


class ContextTeacher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        executable, _ = build_policy('teacher-context-v1-normal')
        cls.observer = executable.parent/'observer'
        cls.teacher = executable.parent/'teacher'

    def audit(self, cells, army, shuttle, state):
        result = subprocess.run([str(self.teacher), '--strategic','--context','--audit'],
            input=f'search {army} 4 {bytes(cells).hex()} {shuttle} {state}\n', text=True,
            capture_output=True, check=True)
        self.assertNotIn('error', result.stdout)
        return [line.split() for line in result.stdout.splitlines() if line.startswith('decision ')]

    def test_full_history_is_loaded_before_hypothetical_root_decisions(self):
        cases=[json.loads(line) for line in (ROOT/'docs/ai-cycle-2026-10-15/public-cases.jsonl').read_text().splitlines()]
        case=next(c for c in cases if c['id']=='fdbb0ffe28b02d232e02')
        bot=TeacherBot(self.observer,self.teacher,samples=1,depth=4,blend='correction',strategic=True,context=True)
        try:
            army=case['input']['army']; bot.observer.send('new '+('red','blue')[army])
            bot.observer.send('setup '+case['own_initial_setup'])
            for ply,event in enumerate(case['public_history']):
                if ply%2==army:
                    bot.observer.ask('go','move'); bot.observer.ask('played '+' '.join(event.split()[1:3]),'playedok')
                bot.observer.send(event)
            side,board,lost,shuttle=bot.observer.ask('public','public').split()
            self.assertEqual(board,case['input']['board_hex'])
            state=bot.observer.ask('strategy','strategy'); raw=bytes.fromhex(state)
            self.assertTrue(any(x != 255 for x in raw[army*100:(army+1)*100]))
            cells=list(bytes.fromhex(board))
            histories={sq:list(map(int,bot.observer.ask('memory '+__import__('feldmarschall').square_name(sq),'history').split()))
                       for sq,cell in enumerate(cells) if cell<254 and bool(cell&16)!=bool(army) and not cell&32}
            world,_=sample_world(cells,list(bytes.fromhex(lost)),histories,random.Random(15),army)
            decisions=self.audit(world,army,shuttle,state)
            roots=[d for d in decisions if int(d[1])==army and d[2]=='1' and d[5]=='-']
            self.assertGreater(len(roots),0)
            expected=raw[army*100:(army+1)*100]+bytes(raw[i+army] for i in range(200,210,2))
            for row in roots: self.assertEqual(bytes.fromhex(row[8]),expected)
        finally: bot.close()

    def test_policy_information_invariance_under_private_world_permutations(self):
        rng=random.Random(15015); position=Position()
        for side in (0,1): position.place(side,random_setup(rng))
        cells=[254 if sq in LAKES else 255 if c is None else c[1]|(16 if c[0] else 0)
               for sq,c in enumerate(position.cells)]
        bot=TeacherBot(self.observer,self.teacher,samples=1,context=True)
        try:
            bot.observer.send('new red'); bot.observer.send('setup '+''.join('123456789SBF'[position.cells[sq][1]] for sq in __import__('feldmarschall').setup_squares(0)))
            state=bot.observer.ask('strategy','strategy')
            changed=cells[:]
            flag=next(sq for sq,c in enumerate(cells) if c<254 and c&16 and c&15==11)
            bomb=next(sq for sq,c in enumerate(cells) if c<254 and c&16 and c&15==10)
            changed[flag],changed[bomb]=changed[bomb],changed[flag]
            decisions={}; matches=futures=0
            for row in self.audit(cells,0,'ffffffff0000',state)+self.audit(changed,0,'ffffffff0000',state):
                key=tuple(row[i] for i in (1,2,4,5,7)); action=tuple(row[i] for i in (3,6,8,9,10))
                if key in decisions:
                    self.assertEqual(decisions[key],action); matches+=1; futures+=row[5]!='-'
                decisions[key]=action
                army=int(row[1])
                self.assertTrue(all(c&15==12 for c in bytes.fromhex(row[6]) if c<254 and bool(c&16)!=bool(army) and not c&32))
            self.assertGreater(matches,10); self.assertGreater(futures,0)
        finally: bot.close()


if __name__=='__main__': unittest.main()
