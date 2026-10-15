/* Same fixed midgame and full production policy, with/without the opt-in risk.
 * A timing fixture, never a saved tournament or a strength claim. */
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "../src/core/ai.c"

int main(void) {
    static const uint8_t own_squares[]={55,64,75,80,81,83,84,85,87,88,89,90,91,92,93,95,96,97,98,99};
    static const uint8_t own_ranks[]={0,1,2,2,3,3,3,4,4,4,5,5,6,7,7,8,8,9,10,11};
    static const uint8_t enemy_squares[]={45,54,65,59,35,34,25,24,15,14,5,4,0,1,10,11,20,21,30};
    static const uint8_t remaining[]={1,1,1,1,2,2,2,2,3,1,2,1};
    uint8_t saved[SQUARES],lost[PIECE_TYPES],from,to;
    unsigned i,enabled=0;
    clock_t start;
    volatile unsigned long checksum=0;
#ifdef AI_EXACT_CONTACT_RISK
    enabled=1;
#endif
    board_clear(); game_rules=0; ai_difficulty=AI_NORMAL;
    for(i=0;i<sizeof(own_squares);i++) board[own_squares[i]]=own_ranks[i];
    for(i=0;i<sizeof(enemy_squares);i++)
        board[enemy_squares[i]]=PIECE_UNKNOWN|CELL_BLUE|(i<12 ? CELL_MOVED : 0);
    for(i=0;i<PIECE_TYPES;i++) lost[i]=piece_counts[i]-remaining[i];
    memcpy(saved,board,SQUARES);
    start=clock();
    for(i=0;i<1000;i++) {
        memcpy(board,saved,SQUARES); rules_reset(); ai_reset(); random_seed(121);
        ai_move(0,lost,&from,&to); checksum+=(unsigned long)from*100+to;
    }
    printf("{\"enabled\":%u,\"decisions\":1000,\"seconds\":%.6f,\"checksum\":%lu}\n",
           enabled,(double)(clock()-start)/CLOCKS_PER_SEC,checksum);
    return 0;
}
