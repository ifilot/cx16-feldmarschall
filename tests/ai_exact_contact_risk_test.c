/* Inspect the private probability helper without changing the game's API. */
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "../src/core/ai.c"

static unsigned checks, failures;
#define EXPECT(c) do { checks++; if(!(c)) { \
    fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c); failures++; } } while(0)

static void test_fresh(void) {
    uint8_t a,d;
    board_clear(); rules_reset(); ai_reset(); game_rules=0; own=0;
    memset(hidden,0,sizeof(hidden)); memset(risk,0,sizeof(risk));
    memcpy(worth,value,sizeof(worth));
    for(a=0;a<PIECE_TYPES;a++) for(d=0;d<PIECE_TYPES;d++)
        combat_result[a][d]=rules_battle(a,d);
}

int main(int argc,char** argv) {
    unsigned a,u,count,t,rank,kind_value;
    uint8_t kind[4];
    uint8_t lost[PIECE_TYPES], from, to, reference_from=NOWHERE, reference_to=NOWHERE;
    uint32_t p;
    int16_t expected;
    clock_t start;
    volatile uint32_t sink=0;
    test_fresh();
    if(argc>1 && !strcmp(argv[1],"prob")) {
        while(scanf("%u %u",&a,&u)==2) {
            hidden_mobile=0; exact_hidden_unmoved=(uint8_t)u;
            for(t=0;t<PIECE_TYPES;t++) {
                if(scanf("%u",&rank)!=1) return 2;
                hidden[t]=(uint8_t)rank;
                if(t<PIECE_BOMB) hidden_mobile+=hidden[t];
            }
            if(scanf("%u",&count)!=1 || count>4) return 2;
            for(t=0;t<count;t++) {
                if(scanf("%u",&kind_value)!=1) return 2;
                kind[t]=(uint8_t)kind_value;
            }
            p=exact_contact_probability((uint8_t)a,(uint8_t)count,kind);
            printf("%lu\n",(unsigned long)p);
        }
        return 0;
    }
    hidden[PIECE_SPY]=1; hidden[PIECE_SCOUT]=2; hidden[PIECE_BOMB]=1;
    hidden_mobile=3; exact_hidden_unmoved=2;
    kind[0]=2; kind[1]=2;
    p=exact_contact_probability(PIECE_MARSHAL,2,kind);
    EXPECT(p>=CONTACT_ONE*2/3-2 && p<=CONTACT_ONE*2/3+2);
    kind[0]=0;
    p=exact_contact_probability(PIECE_MARSHAL,1,kind);
    EXPECT(p>=CONTACT_ONE/6-2 && p<=CONTACT_ONE/6+2);
    kind[0]=3;
    p=exact_contact_probability(PIECE_SPY,1,kind);
    EXPECT(p>=CONTACT_ONE*2/3-2 && p<=CONTACT_ONE*2/3+2);
    EXPECT(exact_contact_probability(PIECE_MARSHAL,1,kind)==0);
    board[55]=PIECE_MARSHAL;
    board[54]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
    board[65]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
    expected=threat(55,PIECE_MARSHAL);
    EXPECT(expected==267);
    for(rank=0;rank<PIECE_TYPES;rank++) {
        board[54]=rank|CELL_BLUE|CELL_MOVED;
        EXPECT(threat(55,PIECE_MARSHAL)==expected);
    }
    /* The inventory belongs to the root, not speculative surviving occupancy. */
    board[0]=PIECE_UNKNOWN|CELL_BLUE;
    EXPECT(threat(55,PIECE_MARSHAL)==expected);
    board[0]=CELL_EMPTY;
    EXPECT(threat(55,PIECE_MARSHAL)==expected);
    /* Equal disclosed rank has zero net exchange loss. */
    board[54]=PIECE_MARSHAL|CELL_BLUE|CELL_REVEALED;
    board[65]=CELL_EMPTY;
    EXPECT(threat(55,PIECE_MARSHAL)==0);
    board[54]=PIECE_SPY|CELL_BLUE|CELL_REVEALED;
    EXPECT(threat(55,PIECE_MARSHAL)==400);
    /* Long concealed Scout rays threaten Spy, and friendly blockers stop them. */
    board[54]=CELL_EMPTY; board[5]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
    EXPECT(threat(55,PIECE_SPY)==67);
    board[45]=PIECE_MARSHAL;
    EXPECT(threat(55,PIECE_SPY)==0);
    board[45]=CELL_EMPTY; board[5]=PIECE_SCOUT|CELL_BLUE|CELL_REVEALED;
    EXPECT(threat(55,PIECE_SPY)==100);
    /* Opt-in research applies only to Classic. */
    game_rules=RULE_MOVING_BOMBS;
    board[5]=PIECE_UNKNOWN|CELL_BLUE|CELL_MOVED;
    EXPECT(threat(55,PIECE_SPY)==0);
    game_rules=0;
    /* Entire normal decisions, not only the probability helper, must ignore
     * concealed physical rank bits. Root inventory comes from public losses. */
    for(rank=0;rank<PIECE_TYPES;rank++) {
        test_fresh(); ai_difficulty=AI_NORMAL;
        memcpy(lost,piece_counts,sizeof(lost));
        lost[PIECE_SPY]--; lost[PIECE_SCOUT]-=2; lost[PIECE_BOMB]--; lost[PIECE_FLAG]--;
        board[55]=PIECE_MARSHAL; board[95]=PIECE_FLAG;
        board[54]=rank|CELL_BLUE|CELL_MOVED;
        board[65]=rank|CELL_BLUE|CELL_MOVED;
        board[0]=rank|CELL_BLUE; board[1]=rank|CELL_BLUE; board[2]=rank|CELL_BLUE;
        random_seed(251); ai_move(0,lost,&from,&to);
        if(!rank) {reference_from=from;reference_to=to;}
        EXPECT(from==reference_from && to==reference_to);
    }
    test_fresh();
    /* At most15subsets per call, no world sampling or heap allocation. */
    kind[0]=kind[1]=kind[2]=kind[3]=2;
    hidden[PIECE_SCOUT]=8; hidden[PIECE_SPY]=1; hidden[PIECE_MARSHAL]=1;
    hidden[PIECE_BOMB]=1;
    hidden_mobile=10; exact_hidden_unmoved=1;
    start=clock();
    for(t=0;t<200000;t++) {
        kind[0]=(t&1) ? 2 : 0;
        sink+=exact_contact_probability((uint8_t)(t%10),4,kind);
    }
    printf("{\"passed\":%s,\"checks\":%u,\"failures\":%u,\"benchmark_calls\":200000,\"seconds\":%.6f,\"sink\":%lu}\n",
           failures?"false":"true",checks,failures,(double)(clock()-start)/CLOCKS_PER_SEC,(unsigned long)sink);
    return failures!=0;
}
