/* Validated Classic deployment mixtures. Data and work live in mission bank 24. */
#pragma static-locals (on)
#include "setup.h"
#include "board.h"
#include "rules.h"
#include "random.h"
#include "ai.h"

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
    army = blue ? CELL_BLUE : 0;
    for(i=0; i<ARMY_SIZE; i++) {
        sq = blue ? (3 - i / BOARD_SIZE) * BOARD_SIZE + i % BOARD_SIZE : RED_HOME0 + i;
        board[sq] = layouts[layout][i] | army;
    }
}
