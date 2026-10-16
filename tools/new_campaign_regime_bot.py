"""Forget only own square goals after public hard rejection of all templates."""
import argparse
from pathlib import Path

from campaign_native_template import NativeTemplateBot


class RegimeResetBot(NativeTemplateBot):
    def __init__(self,observer,difficulty='normal',model=None):
        if difficulty!='normal':raise ValueError('regime reset requires Classic Normal')
        super().__init__(observer,difficulty,model=model)
        self.had_templates=True;self.regime_pending=False;self.regime_fired=False
        self.regime_event=None

    def observe(self,words):
        if words and words[0]=='rules' and words[1:]!=['0']:
            raise ValueError('regime reset requires Classic rules')
        result=super().observe(words)
        if not words:return result
        if words[0]=='new':
            self.had_templates=True;self.regime_pending=False;self.regime_fired=False;self.regime_event=None
        elif words[0] in ('moved','battle'):
            # A discrete hard compatibility test, not a small floating weight
            # threshold, ensures that posterior rounding cannot trigger reset.
            known={origin:rank for (owner,origin),rank in self.model.known.items() if owner!=self.model.army}
            moved={origin for owner,origin in self.model.moved if owner!=self.model.army}
            compatible=any(all(template[o]==r for o,r in known.items()) and
                           all(template[o]<10 for o in moved) for template in self.model.templates)
            if self.had_templates and not compatible and not self.regime_fired:
                self.regime_pending=True;self.regime_event=' '.join(words)
            self.had_templates=compatible
        return result

    def choose(self):
        fired_now=self.regime_pending
        if fired_now:
            self.observer.ask('goal-regime-reset','goal-regime-resetok')
            self.regime_pending=False;self.regime_fired=True
        move=super().choose()
        self.last_report['belief_regime_reset']=dict(fired_now=fired_now,fired_this_game=self.regime_fired,
                                                    public_event=self.regime_event)
        return move


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=('normal',),default='normal')
    parser.add_argument('--belief-regime-reset',action='store_true',required=True)
    args=parser.parse_args()
    RegimeResetBot(args.observer,args.difficulty).run()


if __name__=='__main__':main()
