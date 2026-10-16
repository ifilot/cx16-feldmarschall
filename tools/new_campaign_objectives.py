"""Frozen-source transformation for a goal-only public mobile-belief experiment.

This module never edits working core files. Its patch is applied to an extracted
policy archive before registration. Runtime helpers are embedded into the frozen
existing template adapter, so the usual portable native-template build suffices.
"""
from pathlib import Path


def goal_values(cells,army,lost,remaining,marginals,flag,bomb):
    import math
    from campaign_belief_values import gain,worths,native_expected
    worth=worths(lost);h=sum(remaining[:10]);values=[[0]*100 for _ in range(10)]
    def trunc(value):
        nearest=round(value)
        return nearest if abs(value-nearest)<1e-9 else math.trunc(value)
    for rank in range(10):
        mobile_sum=sum(n*gain(rank,r,worth) for r,n in enumerate(remaining[:10]))
        for sq,row in marginals.items():
            cell=cells[sq]
            if cell>=254 or bool(cell&16)==bool(army) or cell&32:
                raise ValueError('only public concealed enemy marginals accepted')
            f,b=(0,0) if cell&64 else (flag[sq],bomb[sq]);m=4096-f-b
            immobile=f*2000+b*gain(rank,10,worth)
            baseline=(native_expected(rank,True,remaining,worth) if cell&64 else
                      ((immobile*h+m*mobile_sum)//(4096*h) if immobile*h+m*mobile_sum>=0 else
                       -(-(immobile*h+m*mobile_sum)//(4096*h))) if h else
                      trunc(immobile/4096) if not m else native_expected(rank,False,remaining,worth))
            mass=sum(row[:10]);conditional=sum(p*gain(rank,r,worth)for r,p in enumerate(row[:10]))/mass if mass else mobile_sum/h if h else 0
            # Preserve exact integer baseline when the conditional reduces to
            # exchangeability; floating cancellation must not invent a change.
            replacement=baseline if not h or abs(conditional-mobile_sum/h)<1e-9 else trunc((immobile+m*conditional)/4096)
            if not -400<=replacement<=2000:raise ValueError('goal expectation outside combat range')
            values[rank][sq]=replacement
    return values


def goal_packet(values):
    if len(values)!=10 or any(len(row)!=100 for row in values):raise ValueError('ten full actor rows required')
    if any(type(v)is not int or not -400<=v<=2000 for row in values for v in row):raise ValueError('bounded signed expectations required')
    return ''.join(f'{v&65535:04x}'for row in values for v in row)


def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('source anchor absent or ambiguous: '+old[:100])
    return text.replace(old,new)


def patch_sources(root):
    """Apply once to frozen AI_BELIEF_PRIORS native-template source tree."""
    root=Path(root);path=root/'src/core/ai.c';text=path.read_text()
    text=replace_once(text,'static uint8_t belief_owner;', '''static uint8_t belief_owner;
static uint8_t goal_owner;
static int16_t goal_expected[10][SQUARES];
uint8_t ai_goal_priors_set(uint8_t army,const int16_t* values) {
    unsigned i;
    if((army!=0 && army!=CELL_BLUE) || belief_owner!=(army|1)) return 0;
    for(i=0;i<10*SQUARES;i++) if(values[i]<-400 || values[i]>2000) return 0;
    memcpy(goal_expected,values,sizeof(goal_expected));goal_owner=army|1;return 1;
}
void ai_goal_priors_clear(void) {goal_owner=0;}''')
    text=replace_once(text,'    belief_owner=army|1;','    belief_owner=army|1;goal_owner=0;')
    text=replace_once(text,'    belief_owner=0;','    belief_owner=0;goal_owner=0;')
    anchor='        g = cell & CELL_REVEALED ? gain(a, PIECE_TYPE(cell)) : expected_at(a,sq);'
    text=replace_once(text,anchor,anchor+'''
#ifdef AI_BELIEF_PRIORS
        /* Objective-only: captures continue through unchanged expected_at(). */
        if(!game_rules && ai_difficulty==AI_NORMAL && goal_owner==(own|1) &&
           !(cell&CELL_REVEALED) && a<PIECE_BOMB) g=goal_expected[a][sq];
#endif''')
    path.write_text(text)
    path=root/'src/core/ai.h';text=path.read_text()
    text+='\n#ifdef AI_BELIEF_PRIORS\nuint8_t ai_goal_priors_set(uint8_t army,const int16_t* values);\n#endif\n';path.write_text(text)
    path=root/'src/native/engine.c';text=path.read_text()
    text=replace_once(text,'    char line[1024], *command, *args;','    char line[8192], *command, *args;')
    anchor='        } else if(!strcmp(command, "isready")) {'
    text=replace_once(text,anchor,'''        }
#ifdef AI_BELIEF_PRIORS
        else if(!strcmp(command,"goal-priors")) {
            int16_t values[1000];unsigned i,j,value;int valid=1;
            if(!args || strlen(args)!=4000) {reply("error goal-priors");continue;}
            for(i=0;i<1000 && valid;i++) {
                value=0;
                for(j=0;j<4;j++) {
                    unsigned char c=args[4*i+j];unsigned digit;
                    if(c>='0'&&c<='9')digit=c-'0';
                    else if(c>='a'&&c<='f')digit=c-'a'+10;
                    else {valid=0;break;}
                    value=(value<<4)|digit;
                }
                values[i]=value<32768?(int16_t)value:(int16_t)((int)value-65536);
            }
            reply(valid && ai_goal_priors_set(own,values)?"goal-priorsok":"error goal-priors");
        }
#endif
        else if(!strcmp(command, "isready")) {''')
    path.write_text(text)
    text=replace_once(text,'            from = square(strtok(args, " "));\n            to = square(strtok(NULL, " "));\n            if(from == NOWHERE || to == NOWHERE) {', '''#ifdef AI_BELIEF_PRIORS
            ai_goal_priors_clear();
#endif
            from = square(strtok(args, " "));
            to = square(strtok(NULL, " "));
            if(from == NOWHERE || to == NOWHERE) {''')
    path.write_text(text)
    path=root/'tools/campaign_native_template.py';text=path.read_text()
    # Embed the audited helpers rather than adding an undeclared runtime file.
    import inspect
    text=replace_once(text,'class NativeTemplateBot(NativeBeliefBot):',inspect.getsource(goal_values)+'\n\n'+inspect.getsource(goal_packet)+'\n\nclass NativeTemplateBot(NativeBeliefBot):')
    text=replace_once(text,"        self.observer.ask('belief-priors '+packet,'belief-priorsok')", "        self.observer.ask('belief-priors '+packet,'belief-priorsok')\n        goals=goal_values(cells,army,lost_counts,remaining,marginals,flag,bomb)\n        self.observer.ask('goal-priors '+goal_packet(goals),'goal-priorsok')")
    text=replace_once(text,"native_approximation='Only Flag/Bomb marginals; exchangeable mobile ranks discard template mobile-rank correlations.'", "native_approximation='Full conditional mobile beliefs in plan only; original capture expectations and danger retained.'")
    text=replace_once(text,"    parser.add_argument('--home-interceptor',action='store_true')", "    parser.add_argument('--home-interceptor',action='store_true')\n    parser.add_argument('--mobile-goals',action='store_true',required=True)")
    path.write_text(text)


def materialize(root):
    import shutil,tempfile
    root=Path(root)
    with tempfile.TemporaryDirectory(prefix='objective-source-') as directory:
        target=Path(directory)
        for name in ('src/core/ai.c','src/core/ai.h','src/native/engine.c','tools/campaign_native_template.py'):
            (target/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(root/name,target/name)
        patch_sources(target)
        outputs={
            'src/core/ai.c':'tools/new_campaign_objectives_ai.c',
            'src/native/engine.c':'tools/new_campaign_objectives_engine.c',
            'tools/campaign_native_template.py':'tools/new_campaign_objectives_bot.py'}
        for source,destination in outputs.items():
            text=(target/source).read_text()
            if source=='src/native/engine.c':text=text.replace('#include "ai.h"','#include "ai.h"\nuint8_t ai_goal_priors_set(uint8_t army,const int16_t* values);\nvoid ai_goal_priors_clear(void);')
            (root/destination).write_text(text)
    return list(outputs.values())


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--materialize',action='store_true')
    args=parser.parse_args()
    materialize(args.source) if args.materialize else patch_sources(args.source)
