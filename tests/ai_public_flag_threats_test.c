/* Standalone mechanism test: include the translation unit to inspect its
 * private threat counter without adding a diagnostic API to the game. */
#include <stdio.h>
#include <string.h>
#include "../src/core/ai.c"

static int failures;
static unsigned checks;
#define EXPECT(c) do { checks++; if(!(c)) { \
    fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c); failures++; } } while(0)

static void fresh_test(void) {
    board_clear(); rules_reset(); ai_reset(); game_rules=0;
    own=0; flag_square=91; board[91]=PIECE_FLAG;
}

int main(void) {
    unsigned rank, enabled=0, defended=0, seeds=32, seed, invariant_choices=0;
    uint8_t from, to, lost[PIECE_TYPES];
#ifdef AI_PUBLIC_FLAG_THREATS
    enabled=1;
#endif
    fresh_test(); board[90]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
    EXPECT(flag_threats()==enabled);
    fresh_test(); board[90]=PIECE_UNKNOWN|CELL_BLUE;
    EXPECT(flag_threats()==0);
    fresh_test(); board[90]=PIECE_SCOUT|CELL_BLUE|CELL_REVEALED;
    EXPECT(flag_threats()==1);
    fresh_test(); board[90]=PIECE_BOMB|CELL_BLUE|CELL_REVEALED;
    EXPECT(flag_threats()==0);
    for(rank=0;rank<PIECE_TYPES;rank++) {
        fresh_test(); board[90]=rank|CELL_BLUE|CELL_MOVED;
        EXPECT(flag_threats()==enabled);
    }
    fresh_test(); board[91]=CELL_EMPTY; own=CELL_BLUE;
    flag_square=8; board[8]=PIECE_FLAG|CELL_BLUE;
    board[9]=PIECE_UNKNOWN|CELL_MOVED;
    EXPECT(flag_threats()==enabled);
    fresh_test(); board[1]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
    EXPECT(flag_threats()==0);
    board[1]=PIECE_SCOUT|CELL_BLUE|CELL_REVEALED;
    EXPECT(flag_threats()==1);
    fresh_test(); board[90]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
    game_rules=RULE_MOVING_BOMBS;
    EXPECT(flag_threats()==0);
    for(rank=1;rank<=seeds;rank++) {
        fresh_test(); memset(lost,0,sizeof(lost)); ai_difficulty=AI_NORMAL;
        board[80]=PIECE_MARSHAL;
        board[90]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
        board[70]=PIECE_GENERAL|CELL_BLUE|CELL_REVEALED;
        random_seed(rank); ai_move(0,lost,&from,&to);
        defended += from==80 && to==90;
    }
    for(rank=0;rank<PIECE_TYPES;rank++) for(seed=1;seed<=seeds;seed++) {
        fresh_test(); memset(lost,0,sizeof(lost)); ai_difficulty=AI_NORMAL;
        board[80]=PIECE_MARSHAL;
        board[90]=rank|CELL_BLUE|CELL_MOVED; /* Concealed bits have no authority. */
        board[70]=PIECE_GENERAL|CELL_BLUE|CELL_REVEALED;
        random_seed(seed); ai_move(0,lost,&from,&to);
        EXPECT(from==80 && to==(enabled ? 90 : 70));
        invariant_choices++;
    }
    /* The intervention must change a responsible choice, not merely a count.
     * The default's exact behavior is recorded beside this guarded result. */
    if(enabled) EXPECT(defended==seeds);
    printf("{\"enabled\":%u,\"checks\":%u,\"failures\":%d,\"defended\":%u,\"seeds\":%u,\"concealed_nibble_choice_checks\":%u}\n",
           enabled,checks,failures,defended,seeds,invariant_choices);
    return failures!=0;
}
