"""Public reply selection, branch restoration, backwards parity and root safety."""
import json
import os
import random
import subprocess
import unittest
from pathlib import Path

from ai_registry import ROOT, build_policy
from feldmarschall import GLYPHS, LAKES, Position, random_setup
from teacher_bot import TeacherBot
import test_teacher_context as previous


def results(text):
    return [line for line in text.splitlines() if line.startswith(('action ','done '))]


class ReplyTeacher(previous.ContextTeacher):
    @classmethod
    def setUpClass(cls):
        control,_=build_policy('teacher-context-v1-normal')
        cls.control=control.parent/'teacher';cls.observer=control.parent/'observer'
        if os.environ.get('REPLY_TEACHER'):
            cls.teacher=Path(os.environ['REPLY_TEACHER']).resolve()
        else:
            candidate,_=build_policy('teacher-replies-v1-normal')
            cls.teacher=candidate.parent/'teacher'

    def search(self,cells,army,shuttle,state,replies=3,reverse=False,audit=False,control=False):
        command=[str(self.control if control else self.teacher),'--strategic','--context']
        if not control:command+=['--replies',str(replies)]
        if reverse:command+=['--reverse-replies']
        if audit:command+=['--audit']
        result=subprocess.run(command,input=f'search {army} 4 {bytes(cells).hex()} {shuttle} {state}\n',
                              capture_output=True,text=True,check=True)
        self.assertNotIn('error',result.stdout)
        return result.stdout

    def audit(self,cells,army,shuttle,state):
        return [line.split() for line in self.search(cells,army,shuttle,state,audit=True).splitlines() if line.startswith('decision ')]

    def fixture(self,seed=17,army=0):
        rng=random.Random(seed);position=Position();setups=[random_setup(rng) for _ in (0,1)]
        for side in (0,1):position.place(side,setups[side])
        cells=[254 if sq in LAKES else 255 if cell is None else cell[1]|(16 if cell[0] else 0)
               for sq,cell in enumerate(position.cells)]
        bot=TeacherBot(self.observer,self.teacher,samples=1,context=True,replies=3)
        try:
            bot.observer.send('new '+('red','blue')[army]);bot.observer.send('setup '+setups[army])
            state=bot.observer.ask('strategy','strategy')
        finally:bot.close()
        return position,cells,state

    def test_one_reply_matches_frozen_control_exactly(self):
        for army in (0,1):
            for seed in (17,45,914):
                _,cells,state=self.fixture(seed,army)
                self.assertEqual(results(self.search(cells,army,'ffffffff0000',state,replies=1)),
                                 results(self.search(cells,army,'ffffffff0000',state,control=True)))

    def test_reverse_order_restores_state_and_all_root_actions_remain_legal(self):
        for army in (0,1):
            position,cells,state=self.fixture(45,army)
            forward=self.search(cells,army,'ffffffff0000',state)
            backward=self.search(cells,army,'ffffffff0000',state,reverse=True)
            self.assertEqual(results(forward),results(backward))
            self.assertEqual({tuple(map(int,line.split()[1:3])) for line in forward.splitlines() if line.startswith('action ')},set(position.moves(army)))
            self.assertEqual(forward,self.search(cells,army,'ffffffff0000',state))

    def test_reply_membership_and_weights_depend_only_on_mover_information(self):
        _,cells,state=self.fixture(45)
        changed=cells[:]
        # Alter ROOT's concealed ranks, which the replying opponent cannot see.
        # Altering the opponent's own ranks would change its permitted view.
        flag=next(sq for sq,c in enumerate(cells) if c<254 and not c&16 and c&15==11)
        bomb=next(sq for sq,c in enumerate(cells) if c<254 and not c&16 and c&15==10)
        changed[flag],changed[bomb]=changed[bomb],changed[flag]
        selections={};matched=multiple=0
        for world in (cells,changed):
            decision=None
            for line in self.search(world,0,'ffffffff0000',state,audit=True).splitlines():
                row=line.split()
                if row[0]=='decision':decision=row
                elif row[0]=='replies':
                    self.assertIsNotNone(decision)
                    key=tuple(decision[i] for i in (1,2,3,4,5,6,7,8))
                    if key in selections:self.assertEqual(selections[key],row);matched+=1
                    selections[key]=row
                    count=int(row[1]);self.assertLessEqual(count,3);self.assertGreater(count,0)
                    entries=[tuple(map(int,row[i:i+4])) for i in range(2,len(row),4)]
                    self.assertEqual(len(entries),count)
                    for _,_,score,weight in entries:self.assertEqual(weight,33-(entries[0][2]-score));self.assertGreater(weight,0)
                    multiple+=count>1
        self.assertGreater(matched,5);self.assertGreater(multiple,0)

    def test_immediate_known_flag_capture_retains_priority(self):
        cells=[254 if sq in LAKES else 255 for sq in range(100)]
        for sq,cell in {60:8,99:11,50:11|16|32,0:0|16|32}.items():cells[sq]=cell
        bot=TeacherBot(self.observer,self.teacher,samples=2,depth=4,blend='correction',strategic=True,context=True,replies=3)
        try:
            lost=bytes(n-int(rank in (0,11)) for rank,n in enumerate(__import__('feldmarschall').COUNTS)).hex()
            bot.observer.ask(f'position 0 {lost} {bytes(cells).hex()} ffffffff0000','positionok')
            self.assertEqual(bot.choose(),(60,50))
        finally:bot.close()


if __name__=='__main__':unittest.main()
