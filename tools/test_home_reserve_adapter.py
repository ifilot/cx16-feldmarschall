"""Native score traces and actual-choice history must survive public correction."""
import unittest
from campaign_native_template import NativeTemplateBot
from feldmarschall import square_name
from test_campaign_home_reserve import fixture,encode

class Observer:
    def __init__(self,scores,selected):
        self.commands=[]
        self.lines=[f'candidate {a} {b} {score}' for (a,b),score in scores.items()]
        self.lines.append('move '+' '.join(map(square_name,selected)))
    def send(self,line):self.commands.append(line)
    def read(self):return self.lines.pop(0)
    def ask(self,line,prefix):
        self.commands.append(line)
        if prefix!='playedok':raise AssertionError(prefix)
        return ''

class HomeAdapterTests(unittest.TestCase):
    def test_override_commits_actual_choice_once_without_a_second_search(self):
        position=fixture();scores={m:100 if m==(22,23) else 0 for m in position.moves(0)}
        observer=Observer(scores,(22,23));bot=NativeTemplateBot(observer,home_interceptor=True)
        cells,shuttle=encode(position)
        move,report=bot.select_home_interceptor(cells,0,[0]*12,{},shuttle)
        self.assertTrue(report['overridden']);self.assertIn(move,report['repair_moves'])
        self.assertEqual(observer.commands,['difficulty normal','ranked','played '+' '.join(map(square_name,move))])
        self.assertFalse(observer.lines)

    def test_valid_native_choice_preserves_tie_and_native_history(self):
        position=fixture();scores={m:0 for m in position.moves(0)}
        observer=Observer(scores,(22,12));bot=NativeTemplateBot(observer,home_interceptor=True)
        cells,shuttle=encode(position)
        move,report=bot.select_home_interceptor(cells,0,[0]*12,{},shuttle)
        self.assertEqual(move,(22,12));self.assertFalse(report['overridden'])
        self.assertEqual(observer.commands,['difficulty normal','ranked'])

    def test_missing_trace_fails_instead_of_silently_disabling_strategy(self):
        observer=Observer({},(22,23));bot=NativeTemplateBot(observer,home_interceptor=True)
        cells,shuttle=encode(fixture())
        with self.assertRaisesRegex(ValueError,'absent from candidate trace'):
            bot.select_home_interceptor(cells,0,[0]*12,{},shuttle)

    def test_adapter_rejects_nonclassic_or_other_difficulties(self):
        observer=Observer({},(22,23))
        with self.assertRaises(ValueError):NativeTemplateBot(observer,'hard',home_interceptor=True)
        bot=NativeTemplateBot(observer,home_interceptor=True)
        with self.assertRaises(ValueError):bot.observe(['rules','1'])

if __name__=='__main__':unittest.main()
