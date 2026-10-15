/* Compile this public-board fixture with and without AI_TASK_ASSIGNMENT. */
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "../src/core/ai.c"
static unsigned checks, failures;
static uint32_t candidate_hash,capture_hash;
void ai_trace(uint8_t from,uint8_t to,int16_t score_value) {
    candidate_hash=candidate_hash*16777619u+from*100u+to+(uint16_t)score_value*10000u;
    if(board[to]!=CELL_EMPTY) capture_hash=capture_hash*16777619u+from*100u+to+(uint16_t)score_value*10000u;
}
void ai_trace_plan(uint8_t from,uint8_t goal,uint8_t previous,uint8_t steps,int16_t utility) {
    (void)from;(void)goal;(void)previous;(void)steps;(void)utility;
}
#define EXPECT(c) do { checks++; if(!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c); failures++; } } while(0)
static void fresh(unsigned seed, unsigned nibble, unsigned scenario, unsigned level) {
    uint8_t sq;
    candidate_hash=capture_hash=0;board_clear();rules_reset();ai_reset();game_rules=0;ai_difficulty=level;random_seed(seed);
    for(sq=0;sq<40;sq++) if(sq!=30 && sq!=35) board[sq]=CELL_BLUE|nibble;
    board[40]=CELL_BLUE|CELL_REVEALED|PIECE_COLONEL;
    board[65]=CELL_BLUE|CELL_REVEALED|PIECE_SERGEANT;
    board[84]=PIECE_GENERAL;board[85]=PIECE_MAJOR;board[64]=PIECE_BOMB;board[90]=PIECE_FLAG;
    goals[0][84]=goals[0][85]=65;
    if(scenario==1) board[40]=CELL_BLUE|nibble; /* No uncovered disclosed objective. */
    if(scenario==2) board[40]=CELL_BLUE|CELL_REVEALED|PIECE_GENERAL; /* Equal trade forbidden. */
    if(scenario==3) { board[84]=PIECE_MINER; board[40]=CELL_BLUE|CELL_REVEALED|PIECE_SCOUT; }
    if(scenario==4) { board[40]=CELL_BLUE|CELL_REVEALED|PIECE_FLAG; board[41]=PIECE_GENERAL; }
    if(scenario==5) { board[80]=CELL_BLUE|CELL_REVEALED|PIECE_SERGEANT;board[81]=PIECE_GENERAL; }
    if(scenario==6) game_rules=RULE_MOVING_BOMBS;
}
static void quiet(uint8_t from,uint8_t to) {
    uint8_t destinations[MAX_TARGETS],n,i;
    n=rules_targets(from,destinations);for(i=0;i<n && destinations[i]!=to;i++);EXPECT(i<n);
    rules_record(from,to);ai_memory_observe(from,to,AI_MEMORY_QUIET);
    board[to]=board[from]|CELL_MOVED;board[from]=CELL_EMPTY;
}
int main(void) {
    uint8_t lost[12]={0},f,t,firstf,firstt,oldg,newg;
    unsigned seed,scenario,rank,level,iterations=1000;clock_t start;unsigned long sink=0;
    for(scenario=0;scenario<7;scenario++) for(level=0;level<3;level++) for(rank=0;rank<12;rank++) {
        fresh(12,rank,scenario,level); ai_move(0,lost,&f,&t);
#ifdef AI_TASK_ASSIGNMENT
        if(!scenario && level==AI_NORMAL) {
            EXPECT(task_reassigned_from==84 && task_reassigned_to==40);
            EXPECT(task_base_utility[0]==26 && task_base_utility[1]==29);
            EXPECT(task_utility[0][task_column[40]]==25);
            EXPECT(diagnostic_goals[84]==40 && diagnostic_goals[85]==65);
        }
        if(scenario==1 || scenario==2 || scenario==3) EXPECT(task_reassigned_from==NOWHERE);
#endif
        if(scenario==4) EXPECT(t==40); /* Immediate disclosed flag win. */
        if(scenario==5) EXPECT(f==81 && t==80); /* Existing one-ply flag defence. */
        printf("case %u %u %u %u %u %u %u %lu %lu\n",scenario,level,rank,f,t,diagnostic_goals[84],diagnostic_goals[85],(unsigned long)candidate_hash,(unsigned long)capture_hash);
    }
    fresh(12,PIECE_UNKNOWN,0,AI_NORMAL);ai_move(0,lost,&f,&t);firstf=f;firstt=t;
    oldg=diagnostic_goals[84];EXPECT(f==84 && t==74);
    ai_diagnostic_choice(0,f,t);quiet(f,t);quiet(39,49);ai_move(0,lost,&f,&t);newg=diagnostic_goals[74];
#ifdef AI_TASK_ASSIGNMENT
    EXPECT(f==74 && t==73 && oldg==40 && newg==40);
#else
    EXPECT(f==85 && t==75 && oldg==65 && newg==65);
#endif
    printf("prefix %u %u %u %u %u %u\n",firstf,firstt,f,t,oldg,newg);
    start=clock();for(seed=0;seed<iterations;seed++) {fresh(seed+1,PIECE_UNKNOWN,0,AI_NORMAL);ai_move(0,lost,&f,&t);sink+=f+t;}
    printf("cost %.9f %lu\n",(double)(clock()-start)/CLOCKS_PER_SEC/iterations,sink);
    printf("checks %u %u\n",checks,failures);return failures?1:0;
}
