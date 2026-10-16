"""One native move with an explicit public capture or quiet-contact scope."""
import argparse
import hashlib
from pathlib import Path
import time
from campaign_native_template import NativeTemplateBot
from campaign_native_beliefs import quantize
from campaign_mobile_capture import adjustments,quiet_adjustments,fork_selection,_fork_public_key
from feldmarschall import parse_square,square_name,battle

class MobileCaptureBot(NativeTemplateBot):
    def __init__(self,observer,difficulty='normal',adjustment_scope='captures'):
        if adjustment_scope not in ('captures','quiet-occupancy','quiet-mobile','quiet-fork'):raise ValueError('valid adjustment scope required')
        self.adjustment_scope=adjustment_scope
        self._fork_plan=None;self._fork_discard_reason=None
        if difficulty!='normal':raise ValueError('mobile capture experiment requires Classic Normal')
        super().__init__(observer,difficulty)
    def observe(self,words):
        if words and words[0]=='rules' and words[1:]!=['0']:raise ValueError('Classic rules required')
        if self.adjustment_scope=='quiet-fork':self._fork_event(words)
        return super().observe(words)
    def choose(self):
        started=time.perf_counter()
        army_text,board,lost,shuttle=self.observer.ask('public','public').split()
        army=int(army_text);cells=list(bytes.fromhex(board));lost_counts=list(bytes.fromhex(lost))
        if self.model.army!=army:raise ValueError('native observer differs from public model side')
        cells=[(c&240)|12 if c<254 and bool(c&16)!=bool(army) and not c&32 else c for c in cells]
        histories={sq:list(map(int,self.observer.ask('memory '+square_name(sq),'history').split()))
                   for sq,c in enumerate(cells) if c<254 and bool(c&16)!=bool(army) and not c&32}
        marginals,remaining=self.model.rank_marginals(cells,army,lost_counts,histories)
        flag,bomb,mobile,packet=quantize(marginals,remaining)
        self.observer.ask('belief-priors '+packet,'belief-priorsok')
        self.observer.send('ranked');scores={};credit={}
        while True:
            line=self.observer.read();words=line.split()
            if words and words[0]=='error':raise RuntimeError(line)
            if words and words[0] in ('candidate','credit'):
                if len(words)!=4:raise ValueError('invalid scored trace')
                source,target,value=map(int,words[1:]);column=scores if words[0]=='candidate' else credit
                if (source,target) in column:raise ValueError('duplicate trace')
                column[source,target]=value
            elif words and words[0]=='move':
                parent=None if words[1:]==['none'] else tuple(map(parse_square,words[1:]));break
        if parent is None:
            if self.adjustment_scope=='quiet-fork':self._fork_plan=None;self._fork_discard_reason=None
            if scores:raise ValueError('no move with nonempty native scores')
            mode='template-mobile-captures' if self.adjustment_scope=='captures' else 'template-'+self.adjustment_scope
            self.last_report=dict(mode=mode,selected=None);return None
        if parent not in scores or any(move not in credit and score<30000 for move,score in scores.items()):
            raise ValueError('complete native scores and nonterminal danger credits required')
        if self.adjustment_scope=='quiet-fork':
            selected,report=self._select_fork(cells,army,lost_counts,remaining,scores,parent,shuttle)
        elif self.adjustment_scope=='captures':
            delta,report=adjustments(cells,army,lost_counts,remaining,marginals,flag,bomb,scores,credit)
        else:
            delta,report=quiet_adjustments(cells,army,lost_counts,remaining,marginals,flag,bomb,scores,self.adjustment_scope)
        if self.adjustment_scope!='quiet-fork':
            selected=max(scores,key=lambda move:(scores[move]+delta[move],move==parent))
        if selected!=parent:self.observer.ask('played '+' '.join(map(square_name,selected)),'playedok')
        _,posterior=self.model.posterior()
        self.last_report=dict(mode='template-mobile-captures',army=army,public_board_hex=bytes(cells).hex(),lost_hex=lost,
            remaining=remaining,marginals=marginals,q12=dict(flag=flag,bomb=bomb,mobile=mobile),component_posterior=posterior,
            packet_sha256=hashlib.sha256(packet.encode()).hexdigest(),native_selected=parent,selected=selected,
            overridden=selected!=parent,capture_adjustment=report,elapsed_seconds=time.perf_counter()-started)
        if self.adjustment_scope!='captures':
            self.last_report['mode']='template-'+self.adjustment_scope
            self.last_report['quiet_adjustment']=self.last_report.pop('capture_adjustment')
        return selected

    def _fork_event(self,words):
        if not words:return
        command=words[0]
        if command in ('new','rules','custom','position','setup','seed'):
            self._fork_plan=None;self._fork_discard_reason=None;return
        if command=='played':
            if self._fork_plan is not None:
                self._fork_plan=None;self._fork_discard_reason='actual-history-correction'
            return
        if command not in ('moved','battle')or self._fork_plan is None:return
        plan=self._fork_plan;stage=plan['stage'];own_turn=self.model.plies%2==self.model.army
        move=tuple(map(parse_square,words[1:3]))
        if stage=='own-move'and own_turn and command=='moved'and move==plan['first_move']:
            plan['stage']='enemy-move'
        elif stage=='enemy-move'and not own_turn:
            plan['stage']='ready'
        else:
            self._fork_plan=None;self._fork_discard_reason='unexpected-public-history'

    def _select_fork(self,cells,army,lost,remaining,scores,parent,shuttle):
        """One transient public response plan; all native search already ran."""
        wins=[move for move,score in scores.items()if score>=30000]
        if wins:
            self._fork_plan=None;self._fork_discard_reason=None
            selected=parent if parent in wins else max(wins,key=lambda move:scores[move])
            return selected,dict(version='public-quiet-fork-v1',phase='terminal',reason='immediate-native-flag-win')
        if self._fork_plan is not None:
            plan=self._fork_plan;self._fork_plan=None
            if plan['stage']!='ready':
                return parent,dict(version='public-quiet-fork-v1',phase='fallback',reason='missing-expected-public-events')
            key=_fork_public_key(cells,army,lost,remaining,shuttle)
            witness=plan['states'].get(key)
            if (witness is None or witness not in scores or cells[witness[1]]>=254 or
                bool(cells[witness[1]]&16)==bool(army) or not cells[witness[1]]&32 or
                battle(cells[witness[0]]&15,cells[witness[1]]&15)!='attacker'):
                return parent,dict(version='public-quiet-fork-v1',phase='fallback',reason='unmatched-or-illegal-public-witness')
            return witness,dict(version='public-quiet-fork-v1',phase='followup',reason='execute-certified-public-capture',
                witness_executed=True,root_bound=plan['bound'],public_key_sha256=hashlib.sha256(key.encode()).hexdigest())
        if self._fork_discard_reason is not None:
            reason=self._fork_discard_reason;self._fork_discard_reason=None
            return parent,dict(version='public-quiet-fork-v1',phase='fallback',reason=reason)
        selected,report=fork_selection(cells,army,lost,remaining,scores,parent,shuttle)
        states=report.pop('witness_plan',{});report['witness_states']=len(states);report['phase']='root'
        if selected!=parent and states:
            self._fork_plan=dict(first_move=selected,stage='own-move',states=states,bound=report['selected_bound'])
        return selected,report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observer',type=Path,required=True)
    parser.add_argument('--difficulty',choices=['normal'],default='normal')
    parser.add_argument('--mobile-captures',action='store_true',required=True)
    parser.add_argument('--adjustment-scope',choices=['captures','quiet-occupancy','quiet-mobile','quiet-fork'],default='captures')
    args=parser.parse_args();MobileCaptureBot(args.observer,args.difficulty,args.adjustment_scope).run()

if __name__=='__main__':main()
