/* Validated Classic deployment mixtures. Data and work live in mission bank 24. */
#pragma static-locals (on)
#include "setup.h"
#include "board.h"
#include "rules.h"
#include "random.h"
#include "ai.h"

#if defined(AI_DEPLOY_DOUBLE_SHELL) && !defined(AI_DEPLOY_FORTRESS_ONLY)
#error AI_DEPLOY_DOUBLE_SHELL requires the matched AI_DEPLOY_FORTRESS_ONLY control
#endif
#if defined(AI_DEPLOY_FORTRESS_NORMAL) && defined(AI_DEPLOY_FORTRESS_ONLY)
#error Select the Normal-only release deployment or the historical all-level policy
#endif

#ifdef BANKED_AI
#pragma code-name ("MISSIONCODE")
#pragma rodata-name ("MISSIONRODATA")
#pragma bss-name ("MISSIONBSS")
#define setup_ai setup_ai_banked
#ifdef AI_MEMORY
/* Already in bank 24: avoid nesting the gateway's saved-bank slot. */
#define setup_random setup_random_banked
#endif
#endif

/* Front row first, columns a-j: Fortress, Evolved 2, Evolved 3. */
static const uint8_t layouts[3][ARMY_SIZE] = {
    {8,3,8,4,8,8,5,8,3,8,5,1,6,0,2,4,7,8,6,4,10,7,5,8,6,4,2,9,10,7,11,10,7,10,6,3,7,10,5,10},
    {8,10,8,4,8,8,5,8,3,8,5,1,6,9,2,8,7,8,6,4,10,7,5,4,6,4,2,0,10,7,11,10,7,10,6,3,7,3,5,10},
    {0,9,1,8,8,8,4,8,5,8,5,7,2,7,3,6,8,4,7,3,6,10,4,10,5,2,6,10,8,4,7,7,10,11,10,5,3,10,8,6}
};

void setup_ai(uint8_t blue) {
    uint16_t draw;
    uint8_t ticket, layout, i, sq, army;
    if(game_rules || ai_difficulty == AI_EASY || ai_difficulty >= AI_LEVELS) {
        setup_random(blue);
        return;
    }
    /* random_next has 65,535 nonzero outputs; reject the last five so
     * each of the ten tickets has exactly the same probability. */
    do { draw = random_next(); } while(draw > 65530u);
    ticket = (uint8_t)((draw - 1u) % 10u);
    layout = ticket < (ai_difficulty == AI_HARD ? 4 : 5) ? 0 : ticket < 9 ? 1 : 2;
#ifdef AI_DEPLOY_FORTRESS_ONLY
    /* Retain the same RNG draw as the validated mixture in both arms. */
    layout = 0;
#endif
#ifdef AI_DEPLOY_FORTRESS_NORMAL
    /* Release integration: preserve the historical Easy/Hard setup policies. */
    if(ai_difficulty == AI_NORMAL) layout = 0;
#endif
    army = blue ? CELL_BLUE : 0;
    for(i=0; i<ARMY_SIZE; i++) {
        sq = blue ? (3 - i / BOARD_SIZE) * BOARD_SIZE + i % BOARD_SIZE : RED_HOME0 + i;
        board[sq] = layouts[layout][i] | army;
    }
#ifdef AI_DEPLOY_DOUBLE_SHELL
    /* Own coordinates: a3<->i2, b2<->d1, c1<->h1. The Flag at a1
     * has disjoint inner {a2,b1} and outer {a3,b2,c1} Bomb cuts.
     * Three fixed swaps; no opponent input or extra RNG draw. */
#define DEPLOY_SQUARE(n) (blue ? (3 - (n) / BOARD_SIZE) * BOARD_SIZE + (n) % BOARD_SIZE : RED_HOME0 + (n))
#define DEPLOY_SWAP(a,b) do { i = board[DEPLOY_SQUARE(a)]; board[DEPLOY_SQUARE(a)] = board[DEPLOY_SQUARE(b)]; board[DEPLOY_SQUARE(b)] = i; } while(0)
    DEPLOY_SWAP(10,28);
    DEPLOY_SWAP(21,33);
    DEPLOY_SWAP(32,37);
#undef DEPLOY_SWAP
#undef DEPLOY_SQUARE
#endif
}
