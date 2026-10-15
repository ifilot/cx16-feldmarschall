"""Flag-only overlay must not reveal Spy, even through changed hidden ranks."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from ai_registry import ROOT, build_policy
from feldmarschall import GLYPHS, LAKES, Position, square_name
from teacher_bot import TeacherBot
from tournament import run
from tournament_store import Tournament, verify

FLAG='teacher-context-flag-diagnostic-v1-normal'
BASE='teacher-context-v1-normal'


class FlagOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program,_=build_policy(FLAG)
        with Tournament(ROOT/'docs/ai-vs-msdos-2026-10-15/teacher-context-v1-normal.fmtour') as t:
            cls.game=t.game(9)

    def initialize(self,side,game=None):
        game=game or self.game
        bot=TeacherBot(self.program.parent/'observer',self.program.parent/'teacher',samples=8,depth=4,
                       blend='correction',strategic=True,context=True,diagnostic_truth=True,diagnostic_knowledge='flag')
        bot.rng.seed(233)
        for line in ('new '+('red','blue')[side],'setup '+game[('red_setup','blue_setup')[side]],
                     'opponent-setup '+game[('blue_setup','red_setup')[side]]):self.send(bot,line)
        return bot

    def send(self,bot,line):
        bot.diagnostic_event(line.split())
        if not line.startswith('opponent-setup'):bot.observer.send(line)

    def assert_mask(self,bot,side):
        cells=bytes.fromhex(bot.last_report['board_hex'])
        for sq,cell in enumerate(bot.truth.cells):
            if cell is None:
                self.assertEqual(cells[sq],254 if sq in LAKES else 255)
            elif cell[0]==side:
                self.assertEqual(cells[sq]&15,cell[1])
                self.assertEqual(bool(cells[sq]&32),bool(cell[3]))
            elif cell[1]==11 or cell[3]:
                self.assertEqual(cells[sq]&15,cell[1]);self.assertTrue(cells[sq]&32)
            else:
                self.assertEqual(cells[sq]&15,12);self.assertFalse(cells[sq]&32)

    def test_only_flag_is_known_initially_both_sides(self):
        for side in (0,1):
            bot=self.initialize(side)
            try:
                bot.choose();self.assert_mask(bot,side)
                cells=bytes.fromhex(bot.last_report['board_hex'])
                known=[cells[sq]&15 for sq,c in enumerate(bot.truth.cells) if c and c[0]!=side and cells[sq]&32]
                self.assertEqual(known,[11])
                spy=next(sq for sq,c in enumerate(bot.truth.cells) if c and c[0]!=side and c[1]==9)
                self.assertEqual(cells[spy]&15,12)
                self.assertEqual(bot.last_report['information_model'],'diagnostic-flag')
            finally:bot.close()

    def test_flag_command_absent_from_ordinary_observer(self):
        from feldmarschall import Engine
        import shlex
        executable,_=build_policy(BASE)
        engine=Engine(shlex.quote(str(executable.parent/'observer')))
        try:
            engine.send('new red');engine.send('setup '+self.game['red_setup'])
            with self.assertRaisesRegex(RuntimeError,'unknown command'):
                engine.ask('diagnostic-flag '+'ff'*100,'diagnostic-truthok')
            _,board,_,_=engine.ask('public','public').split()
            self.assertTrue(all(c&15==12 for c in bytes.fromhex(board) if c<254 and c&16))
        finally:engine.close()

    def test_spy_and_other_hidden_rank_permutations_do_not_change_choices(self):
        for side in (0,1):
            reports=[]
            for swap in (False,True):
                game=dict(self.game)
                key=('blue_setup','red_setup')[side]
                if swap:
                    setup=list(game[key]);a,b=setup.index('S'),setup.index('1')
                    setup[a],setup[b]=setup[b],setup[a];game[key]=''.join(setup)
                bot=self.initialize(side,game)
                try:bot.choose();reports.append(bot.last_report)
                finally:bot.close()
            self.assertEqual(reports[0],reports[1])

    def test_public_history_stays_correct_and_new_game_resets(self):
        for side in (0,1):
            bot=self.initialize(side)
            try:
                for ply,(src,dst) in enumerate(self.game['moves'][:120]):
                    if ply % 20==0:bot.choose();self.assert_mask(bot,side)
                    names=square_name(src)+' '+square_name(dst)
                    a,d=bot.truth.cells[src],bot.truth.cells[dst]
                    line=('moved '+names if d is None else 'battle '+names+' '+GLYPHS[a[1]]+' '+GLYPHS[d[1]])
                    self.send(bot,line)
                self.assertEqual(bot.truth_plies,120)
                self.send(bot,'new '+('blue','red')[side])
                self.assertIsNone(bot.truth);self.assertEqual(bot.truth_plies,0)
            finally:bot.close()

    def test_python_native_and_reused_processes_agree(self):
        with tempfile.TemporaryDirectory() as temp:
            paths=[]
            for label,backend,reuse in (('python','python',None),('native','openmp',False),('pool','openmp',True)):
                path=Path(temp)/(label+'.fmtour');paths.append(path)
                with contextlib.redirect_stdout(io.StringIO()):
                    run(FLAG,BASE,path,rounds=1,seed=2069001,jobs=1,families=['uniform'],
                        max_plies=40,backend=backend,reuse_processes=reuse)
                self.assertEqual(verify(path)['errors'],0)
            with Tournament(paths[0]) as old:
                for path in paths[1:]:
                    with Tournament(path) as new:
                        for row in old.games():self.assertEqual(old.game(row['id']),new.game(row['id']))


if __name__=='__main__':unittest.main()
