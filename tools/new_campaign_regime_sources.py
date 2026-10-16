"""Create dedicated native sources; shared core files remain untouched."""
from pathlib import Path


def materialize(root):
    root=Path(root)
    path=root/'src/core/ai.c';text=path.read_text()
    anchor='static uint8_t goals[2][SQUARES];'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'''
#ifdef AI_BELIEF_PRIORS
uint8_t ai_belief_regime_reset(uint8_t army) {
    if((army!=0 && army!=CELL_BLUE) || game_rules || ai_difficulty!=AI_NORMAL) return 0;
    memset(goals[army ? 1 : 0],NOWHERE,SQUARES);
    return 1;
}
#endif''')
    (root/'tools/new_campaign_regime_ai.c').write_text(text)
    text=(root/'src/native/engine.c').read_text()
    anchor='#include "ai.h"'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n#ifdef AI_BELIEF_PRIORS\nuint8_t ai_belief_regime_reset(uint8_t army);\n#endif')
    anchor='        else if(!strcmp(command, "belief-priors")) {'
    assert text.count(anchor)==1
    text=text.replace(anchor,'''        else if(!strcmp(command,"goal-regime-reset")) {
            reply(!args && ai_belief_regime_reset(own) ? "goal-regime-resetok" : "error goal-regime-reset");
        }
'''+anchor)
    (root/'tools/new_campaign_regime_engine.c').write_text(text)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    materialize(parser.parse_args().root)
