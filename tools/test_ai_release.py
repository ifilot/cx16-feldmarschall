"""Production deployment compatibility against the frozen pre-release source."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseDeployment(unittest.TestCase):
    def test_normal_fortress_and_other_modes_preserve_boards_and_rng(self):
        with tempfile.TemporaryDirectory(prefix='ai-release-deployment-') as temporary:
            work = Path(temporary)
            fixture = work/'fixture.c'
            fixture.write_text(r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ai.h"
#include "board.h"
#include "rules.h"
#include "random.h"
void setup_previous(uint8_t blue);
void setup_fortress(uint8_t blue);
void setup_release(uint8_t blue);
static unsigned long comparisons;
static void check(uint16_t seed, uint8_t blue, uint8_t level, uint8_t rules) {
    uint8_t expected[100]; uint16_t next;
    ai_difficulty=level; game_rules=rules;
    board_clear(); random_seed(seed);
    if(level==AI_NORMAL && !rules) setup_fortress(blue); else setup_previous(blue);
    memcpy(expected,board,100);next=random_next();
    board_clear(); random_seed(seed); setup_release(blue);
    assert(memcmp(expected,board,100)==0);assert(random_next()==next);comparisons++;
}
int main(void) {
    unsigned long seed; uint8_t blue,level,rules;
    static const uint16_t seeds[]={1,17,791,65535,14457,31996,32510,48509,49023};
    unsigned i;
    for(level=0;level<3;level++) for(blue=0;blue<2;blue++)
        for(seed=1;seed<=65535;seed++) check((uint16_t)seed,blue,level,0);
    for(rules=1;rules<64;rules++) for(level=0;level<3;level++)
        for(blue=0;blue<2;blue++) for(i=0;i<sizeof(seeds)/sizeof(seeds[0]);i++)
            check(seeds[i],blue,level,rules);
    printf("%lu exact board/RNG comparisons passed\n",comparisons);return 0;
}
''')
            common = ['gcc', '-O2', '-std=c99', '-Wno-unknown-pragmas',
                      '-I'+str(ROOT/'src/core')]
            objects = []
            for name, source, flags in (
                ('previous', ROOT/'tests/baselines/ai_deploy_pre_release.c', []),
                ('fortress', ROOT/'tests/baselines/ai_deploy_pre_release.c', ['AI_DEPLOY_FORTRESS_ONLY']),
                ('release', ROOT/'src/core/ai_deploy.c', ['AI_DEPLOY_FORTRESS_NORMAL'])):
                obj = work/(name+'.o')
                subprocess.run(common+['-Dsetup_ai=setup_'+name]+['-D'+f for f in flags]+
                               ['-c', str(source), '-o', str(obj)], check=True, capture_output=True)
                objects.append(str(obj))
            subprocess.run(common+[str(fixture), *objects]+[str(ROOT/'src/core'/name) for name in
                           ('pieces.c', 'board.c', 'rules.c', 'random.c', 'setup.c', 'ai_level.c')]+
                           ['-o', str(work/'test')], check=True, capture_output=True)
            result = subprocess.run([str(work/'test')], check=True, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), '396612 exact board/RNG comparisons passed')


if __name__ == '__main__':
    unittest.main()
