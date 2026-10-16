"""Public hard-regime change, isolated goals API and persistent-policy checks."""
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from ai_registry import ROOT,build_policy,get_policy
from campaign_native_template import NativeTemplateBot
from new_campaign_regime_bot import RegimeResetBot
from feldmarschall import Engine
from test_campaign_native_template import AlterPublicNibbles
from test_information_parent_parity import public_events
from tournament_store import Tournament,replay


class RegimeQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='regime-qualification-');cls.directory=Path(cls.temp.name)
        p=get_policy('student-fortress-template-flag-bomb-v1-normal');cls.policy=p
        cls.common=['gcc','-O2','-std=c99','-Wno-unknown-pragmas','-Wno-format-overflow','-Isrc/core',*['-D'+d for d in p['defines']]]
        replacement={'src/core/ai.c':'tools/new_campaign_regime_ai.c','src/native/engine.c':'tools/new_campaign_regime_engine.c'}
        cls.observer=cls.directory/'observer'
        subprocess.run([*cls.common,'-o',str(cls.observer),*[replacement.get(s,s) for s in p['sources']]],cwd=ROOT,check=True)
        program,_=build_policy(p['id']);cls.baseline=program.parent/'observer'
        with Tournament(ROOT/'docs/ai-calibrated-beliefs-2026-10-15/development.fmtour') as t:cls.game=t.game(9)
        states,_=replay(cls.game);cls.events=public_events(cls.game,states)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def bot(self,kind,army,alter=False,observer=None):
        wrapper=AlterPublicNibbles(Engine(shlex.quote(str(observer or self.observer))),alter)
        bot=kind(wrapper)
        for line in ('new '+('red','blue')[army],'rules 0','seed 7231','setup '+self.game[('red_setup','blue_setup')[army]]):bot.observe(line.split())
        return bot,wrapper

    def test_native_api_clears_only_selected_goals_preserves_rng_and_other_state(self):
        source=self.directory/'api.c'
        source.write_text('#include <assert.h>\n#include "'+str(ROOT/'tools/new_campaign_regime_ai.c')+'"\n'+r'''
int main(void) {
    unsigned army,i; uint16_t rng;
    game_rules=0;ai_difficulty=AI_NORMAL;
    for(army=0;army<2;army++) {
        memset(goals[0],7,SQUARES);memset(goals[1],9,SQUARES);
        last_from[0]=31;last_from[1]=41;last_to[0]=32;last_to[1]=42;
        quiet_turns[0]=11;quiet_turns[1]=12;previous_count[0]=13;previous_count[1]=14;
        risk[0]=123;worth[0]=321;random_seed(7231);rng=random_current();
        assert(ai_belief_regime_reset(army ? CELL_BLUE : 0));
        for(i=0;i<SQUARES;i++) {
            assert(goals[army][i]==NOWHERE);
            assert(goals[1-army][i]==(army ? 7 : 9));
        }
        assert(last_from[0]==31 && last_from[1]==41 && last_to[0]==32 && last_to[1]==42);
        assert(quiet_turns[0]==11 && quiet_turns[1]==12 && previous_count[0]==13 && previous_count[1]==14);
        assert(risk[0]==123 && worth[0]==321 && random_current()==rng);
    }
    memset(goals,7,sizeof(goals));assert(!ai_belief_regime_reset(1));
    game_rules=1;assert(!ai_belief_regime_reset(0));game_rules=0;
    ai_difficulty=AI_HARD;assert(!ai_belief_regime_reset(0));
    for(i=0;i<sizeof(goals);i++)assert(((uint8_t*)goals)[i]==7);
    return 0;
}
''')
        links=[s for s in self.policy['sources'] if s not in ('src/core/ai.c','src/native/engine.c')]
        exe=self.directory/'api'
        subprocess.run([*self.common,'-o',str(exe),str(source),*links],cwd=ROOT,check=True)
        subprocess.run([str(exe)],check=True)

    def test_default_off_matches_frozen_observer_both_colors(self):
        for army in (0,1):
            pairs=[self.bot(NativeTemplateBot,army,observer=observer) for observer in (self.baseline,self.observer)]
            try:
                for ply in range(100):
                    if ply%2==army:self.assertEqual(pairs[0][0].choose(),pairs[1][0].choose())
                    for bot,_ in pairs:bot.observe(self.events[ply].split())
            finally:
                for bot,_ in pairs:bot.close()

    def test_before_elimination_parity_then_exactly_one_reset_and_one_go_both_colors(self):
        fired=[]
        for army in (0,1):
            base,_=self.bot(NativeTemplateBot,army)
            pairs=[self.bot(RegimeResetBot,army,alter) for alter in (False,True)]
            try:
                for ply in range(120):
                    if ply%2==army:
                        expected=base.choose();choices=[]
                        for bot,wrapper in pairs:
                            was_fired=bot.regime_fired;pending=bot.regime_pending
                            before=len(wrapper.calls);choices.append(bot.choose());calls=wrapper.calls[before:]
                            self.assertEqual(calls.count('go'),1)
                            self.assertEqual(calls.count('goal-regime-reset'),int(pending))
                            if not was_fired and not pending:self.assertEqual(choices[-1],expected)
                            self.assertFalse(any(c.startswith(('opponent-setup','search ')) for c in calls))
                        self.assertEqual(*choices)
                    for bot,_ in pairs:bot.observe(self.events[ply].split())
                    base.observe(self.events[ply].split())
                for bot,wrapper in pairs:
                    self.assertTrue(bot.regime_fired)
                    self.assertEqual(wrapper.calls.count('goal-regime-reset'),1)
                    self.assertEqual(sum(bot.model.posterior()[0][:-1]),0.)
                    fired.append(bot.regime_event)
                    bot.observe(['new',('red','blue')[army]])
                    self.assertFalse(bot.regime_fired);self.assertFalse(bot.regime_pending);self.assertTrue(bot.had_templates)
            finally:
                base.close()
                for bot,_ in pairs:bot.close()
        print('Public hard-elimination fixtures:',fired)

    def test_api_rejects_arguments(self):
        bot,wrapper=self.bot(RegimeResetBot,0)
        try:
            with self.assertRaises(RuntimeError):wrapper.ask('goal-regime-reset extra','goal-regime-resetok')
        finally:bot.close()


if __name__=='__main__':unittest.main()
