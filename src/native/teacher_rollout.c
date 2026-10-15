/* Desktop teacher: exhaustive shared root actions, then policies restricted to
 * each mover's information. Complete boards are sampled worlds, not referee input. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ai.h"
#include "board.h"
#include "rules.h"
#include "random.h"
#ifdef AI_MEMORY
#include "ai_memory.h"
#endif

#define WIN 20000
typedef struct { uint8_t cells[SQUARES], rules[RULES_STATE_SIZE], ai[AI_TEST_STATE_SIZE]; } state_t;
typedef struct { uint8_t from, to; } move_t;
static const int value[PIECE_TYPES] = {400,200,100,75,45,30,15,40,10,100,20,1000};
static uint8_t root;
static unsigned long nodes;
static int strategic;
static int audit;
#ifdef AI_ROLLOUT_CONTEXT
static int contextual;
static uint8_t root_context[AI_TEST_STATE_SIZE];
#endif
static uint16_t policy_random[2];
static uint8_t initial_view[2][SQUARES], trajectory[65];
static unsigned trajectory_length, phase;
#ifdef AI_REPLY_BRANCHES
#ifndef AI_TRACE
#error Reply branching requires masked-policy score tracing
#endif
#define MAX_REPLIES 3
#define REPLY_GAP 32
static unsigned reply_limit = 1, collected;
static int collecting, reverse_replies;
static move_t replies[MAX_REPLIES];
static int16_t reply_scores[MAX_REPLIES];
/* ai_move invokes this with its masked board. Branch membership and weights
 * depend only on that mover's scores, never a branch's hypothetical payoff. */
void ai_trace(uint8_t from, uint8_t to, int16_t score) {
    unsigned i, at;
    if(!collecting) return;
    for(at=0; at<collected && score<=reply_scores[at]; at++);
    if(at==MAX_REPLIES) return;
    if(collected<MAX_REPLIES) collected++;
    for(i=collected-1; i>at; i--) {replies[i]=replies[i-1];reply_scores[i]=reply_scores[i-1];}
    replies[at]=(move_t){from,to};reply_scores[at]=score;
}
void ai_trace_plan(uint8_t from, uint8_t goal, uint8_t previous, uint8_t steps, int16_t score) {
    (void)from;(void)goal;(void)previous;(void)steps;(void)score;
}
#endif

static void save(state_t* state) {
    memcpy(state->cells, board, SQUARES); rules_state_save(state->rules); ai_test_save(state->ai);
}
static void restore(const state_t* state) {
    memcpy(board, state->cells, SQUARES); rules_state_load(state->rules); ai_test_load(state->ai);
}
static int material(void) {
    int score = 0;
    unsigned sq;
    for(sq=0; sq<SQUARES; sq++) if(IS_PIECE(board[sq]))
        score += (!!(board[sq]&CELL_BLUE)==root ? 1 : -1) * value[PIECE_TYPE(board[sq])];
    return score;
}
static int pursuit(uint8_t army) {
    uint8_t distance[SQUARES], queue[SQUARES], flag = NOWHERE, sq, head=0, tail=0, nb;
    unsigned i, pass;
    int best=100;
    static const int step[4]={-10,1,10,-1};
    /* Evaluate hypothetical progress toward the sampled flag. This shaping is
     * averaged across worlds; it is never passed into a mover's policy. */
    for(sq=0; sq<SQUARES; sq++) if(IS_PIECE(board[sq]) && !!(board[sq]&CELL_BLUE)!=army && PIECE_TYPE(board[sq])==PIECE_FLAG) flag=sq;
    if(flag==NOWHERE) return 400;
    for(pass=0; pass<2; pass++) {
        memset(distance,NOWHERE,sizeof(distance));head=0;tail=0;
        distance[flag]=0;queue[tail++]=flag;
        while(head<tail) {
            sq=queue[head++];
            for(i=0;i<4;i++) {
                int target=(int)sq+step[i];
                if(target<0 || target>=100 || (i==1 && sq%10==9) || (i==3 && sq%10==0)) continue;
                nb=(uint8_t)target;
                if(board[nb]==CELL_LAKE || distance[nb]!=NOWHERE) continue;
                if(IS_PIECE(board[nb]) && PIECE_TYPE(board[nb])>=PIECE_BOMB && nb!=flag &&
                   (!!(board[nb]&CELL_BLUE)==army || !pass || PIECE_TYPE(board[nb])!=PIECE_BOMB)) continue;
                distance[nb]=distance[sq]+1;queue[tail++]=nb;
            }
        }
        for(sq=0;sq<SQUARES;sq++) if(IS_PIECE(board[sq]) && !!(board[sq]&CELL_BLUE)==army &&
           PIECE_TYPE(board[sq])<PIECE_BOMB && (!pass || PIECE_TYPE(board[sq])==PIECE_MINER) && distance[sq]<best) best=distance[sq];
    }
    return -4*best;
}
static int utility(void) {
    return material() + (strategic ? pursuit(root)-pursuit(1-root) : 0);
}
static unsigned moves(uint8_t army, move_t* out) {
    unsigned count=0, sq, i;
    uint8_t targets[MAX_TARGETS], n;
    for(sq=0;sq<SQUARES;sq++) if(IS_PIECE(board[sq]) && !!(board[sq]&CELL_BLUE)==army) {
        n=rules_targets(sq,targets);
        for(i=0;i<n;i++) out[count++]=(move_t){(uint8_t)sq,targets[i]};
    }
    return count;
}
static void policy_move(uint8_t army,uint8_t* from,uint8_t* to) {
    uint8_t truth[SQUARES];
    unsigned i;
    memcpy(truth,board,SQUARES);ai_mask(army ? CELL_BLUE : 0);
    if(audit) {
        uint8_t ai_state[AI_TEST_STATE_SIZE],rule_state[RULES_STATE_SIZE];
        ai_test_save(ai_state);rules_state_save(rule_state);
        printf("decision %u %u %u ",army,phase,policy_random[army]);
        for(i=0;i<SQUARES;i++) printf("%02x",initial_view[army][i]);
        putchar(' ');
        if(!trajectory_length) putchar('-');
        for(i=0;i<trajectory_length;i++) printf("%02x",trajectory[i]);
        putchar(' ');
        for(i=0;i<SQUARES;i++) printf("%02x",board[i]);
        putchar(' ');
        for(i=0;i<RULES_STATE_SIZE;i++) printf("%02x",rule_state[i]);
        putchar(' ');
        for(i=army*SQUARES;i<(army+1)*SQUARES;i++) printf("%02x",ai_state[i]);
        for(i=200;i<210;i+=2) printf("%02x",ai_state[i+army]);
        putchar(' ');
    }
    random_seed(policy_random[army]);
    ai_move(army ? CELL_BLUE : 0,rules_known_lost[1-army],from,to);
    policy_random[army]=random_current();
    if(audit) printf("%u %u\n",*from,*to);
    memcpy(board,truth,SQUARES);nodes++;
}
static void record_action(uint8_t from,uint8_t to) {
    uint8_t attacking=IS_PIECE(board[to]);
    int distance=abs((int)(from/10)-(int)(to/10))+abs((int)(from%10)-(int)(to%10));
    if(trajectory_length+5>sizeof(trajectory)) exit(3);
    trajectory[trajectory_length++]=from;trajectory[trajectory_length++]=to;
    trajectory[trajectory_length++]=attacking || distance>1 ? PIECE_TYPE(board[from]) : 255;
    trajectory[trajectory_length++]=attacking ? PIECE_TYPE(board[to]) : 255;
    trajectory[trajectory_length++]=attacking ? rules_battle(PIECE_TYPE(board[from]),PIECE_TYPE(board[to])) : BATTLE_QUIET;
#ifdef AI_MEMORY
    /* Classic combat makes both participating ranks public. Quiet movement
     * only updates public movement/encounter records, never private identities. */
    ai_memory_observe(from, to, attacking ? rules_battle(PIECE_TYPE(board[from]), PIECE_TYPE(board[to])) : AI_MEMORY_QUIET);
#endif
}
static int rollout(uint8_t army, unsigned depth) {
    uint8_t from, to;
    unsigned turn;
    for(turn=0;turn<depth;turn++,army=1-army) {
        if(!rules_has_move(army ? CELL_BLUE : 0)) {
            if(!rules_has_move(army ? 0 : CELL_BLUE)) return 0;
            return army==root ? -WIN : WIN;
        }
        policy_move(army,&from,&to);
        if(from==NOWHERE) { fputs("illegal rollout no move\n",stderr);exit(2); }
        if(IS_PIECE(board[to]) && PIECE_TYPE(board[to])==PIECE_FLAG) return army==root ? WIN : -WIN;
        record_action(from,to);
        rules_apply(from,to);
    }
    return utility();
}
#ifdef AI_REPLY_BRANCHES
static int reply_rollout(uint8_t army, unsigned depth) {
    state_t before;
    uint16_t streams[2];
    uint8_t public_path[sizeof(trajectory)], from, to;
    unsigned length, count, i, index, weight, total=0;
    move_t options[MAX_REPLIES];
    int16_t scores[MAX_REPLIES];
    long sum=0;
    int future;
    if(reply_limit==1 || !depth || !rules_has_move(army ? CELL_BLUE : 0)) return rollout(army,depth);
    save(&before);memcpy(streams,policy_random,sizeof(streams));
    length=trajectory_length;memcpy(public_path,trajectory,sizeof(public_path));
    collected=0;collecting=1;policy_move(army,&from,&to);collecting=0;
    count=collected<reply_limit ? collected : reply_limit;
    if(!count || replies[0].from!=from || replies[0].to!=to) {
        fputs("reply shortlist does not match masked policy\n",stderr);exit(2);
    }
    memcpy(options,replies,sizeof(options));memcpy(scores,reply_scores,sizeof(scores));
    for(i=0; i<count && scores[0]-scores[i]<=REPLY_GAP; i++);
    count=i;
    if(audit) {
        printf("replies %u",count);
        for(i=0;i<count;i++) printf(" %u %u %d %u",options[i].from,options[i].to,scores[i],REPLY_GAP+1-(scores[0]-scores[i]));
        putchar('\n');
    }
    for(i=0;i<count;i++) {
        index=reverse_replies ? count-1-i : i;
        restore(&before);memcpy(policy_random,streams,sizeof(streams));
        trajectory_length=length;memcpy(trajectory,public_path,sizeof(public_path));
        /* Rebuild diagnostic pre-transfer goals after restoring each branch;
         * another branch's continuation can have overwritten that scratch. */
        policy_move(army,&from,&to);
        ai_diagnostic_choice(army ? CELL_BLUE : 0,options[index].from,options[index].to);
        weight=REPLY_GAP+1-(scores[0]-scores[index]);
        if(IS_PIECE(board[options[index].to]) && PIECE_TYPE(board[options[index].to])==PIECE_FLAG)
            future=army==root ? WIN : -WIN;
        else {
            record_action(options[index].from,options[index].to);
            rules_apply(options[index].from,options[index].to);
            future=rollout(1-army,depth-1);
        }
        sum+=(long)weight*future;total+=weight;
    }
    return (int)(sum/(long)total);
}
#else
#define reply_rollout rollout
#endif
static int hex(const char* text, uint8_t* output, unsigned count) {
    unsigned i, value;
    if(strlen(text)!=count*2) return 0;
    for(i=0;i<count;i++) {
        char byte[3]={text[2*i],text[2*i+1],0}, *end;
        value=(unsigned)strtoul(byte,&end,16);
        if(end!=byte+2 || value>255) return 0;
        output[i]=(uint8_t)value;
    }
    return 1;
}
int main(int argc,char** argv) {
    char line[2*AI_TEST_STATE_SIZE+512], cells[201], shuttle[13];
    int consumed;
    unsigned army, depth, sq, rank, owner, i, n;
    uint8_t counts[2][PIECE_TYPES], history[6], rules[RULES_STATE_SIZE];
    move_t options[2000];state_t state;
    int initial, immediate, future, reference, valid;
    uint8_t proposal_from,proposal_to;
    for(i=1;i<(unsigned)argc;i++) {
        if(!strcmp(argv[i],"--strategic")) strategic=1;
        else if(!strcmp(argv[i],"--audit")) audit=1;
#ifdef AI_REPLY_BRANCHES
        else if(!strcmp(argv[i],"--reverse-replies")) reverse_replies=1;
        else if(!strcmp(argv[i],"--replies") && i+1<(unsigned)argc) {
            reply_limit=(unsigned)atoi(argv[++i]);
            if(reply_limit<1 || reply_limit>MAX_REPLIES) return 2;
        }
#endif
#ifdef AI_ROLLOUT_CONTEXT
        else if(!strcmp(argv[i],"--context")) contextual=1;
#endif
        else return 2;
    }
    ai_difficulty=AI_NORMAL;
    while(fgets(line,sizeof(line),stdin)) {
        line[strcspn(line,"\r\n")]=0;
        consumed=0;
        if(sscanf(line,"search %u %u %200s %12s %n",&army,&depth,cells,shuttle,&consumed)!=4 || army>1 || depth<1 || depth>12 ||
           !hex(cells,board,SQUARES) || !hex(shuttle,history,6)) {puts("error search");fflush(stdout);continue;}
#ifdef AI_ROLLOUT_CONTEXT
        if(contextual && (!consumed || !hex(line+consumed,root_context,AI_TEST_STATE_SIZE))) {
            puts("error context");fflush(stdout);continue;
        }
#endif
        memset(counts,0,sizeof(counts));
        for(sq=0;sq<SQUARES;sq++) if(IS_PIECE(board[sq])) {
            rank=PIECE_TYPE(board[sq]);if(rank>=PIECE_TYPES) break;
            counts[!!(board[sq]&CELL_BLUE)][rank]++;
        }
        if(sq<SQUARES) {puts("error incomplete world");fflush(stdout);continue;}
        root=(uint8_t)army;game_rules=0;rules_reset();ai_reset();
        valid=counts[0][PIECE_FLAG]==1 && counts[1][PIECE_FLAG]==1;
        for(owner=0;owner<2;owner++) for(rank=0;rank<PIECE_TYPES;rank++) {
            if(counts[owner][rank]>piece_counts[rank]) valid=0;
            rules_lost[owner][rank]=rules_known_lost[owner][rank]=piece_counts[rank]-counts[owner][rank];
        }
        if(!valid) {puts("error inventory");fflush(stdout);continue;}
        rules_state_save(rules);memcpy(rules+RULES_STATE_SIZE-6,history,6);rules_state_load(rules);
#ifdef AI_ROLLOUT_CONTEXT
        if(contextual) ai_test_load(root_context);
#endif
        initial=utility();save(&state);n=moves(root,options);nodes=0;
        for(owner=0;owner<2;owner++) for(sq=0;sq<SQUARES;sq++) {
            uint8_t cell=board[sq];
            initial_view[owner][sq]=IS_PIECE(cell) && !!(cell&CELL_BLUE)!=owner && !(cell&CELL_REVEALED) ?
                (cell&~CELL_TYPE)|PIECE_UNKNOWN : cell;
        }
        phase=0;trajectory_length=0;
        policy_random[0]=1;policy_random[1]=2;
        reference=reply_rollout(1-root,depth-1)-initial;restore(&state);
        for(i=0;i<n;i++) {
            phase=1;trajectory_length=0;
            policy_random[0]=1;policy_random[1]=2;
            policy_move(root,&proposal_from,&proposal_to);
            ai_diagnostic_choice(root ? CELL_BLUE : 0,options[i].from,options[i].to);
            if(IS_PIECE(board[options[i].to]) && PIECE_TYPE(board[options[i].to])==PIECE_FLAG) immediate=future=WIN-initial;
            else {
                int before=material();
                record_action(options[i].from,options[i].to);
                rules_apply(options[i].from,options[i].to);
                immediate=material()-before;
                future=reply_rollout(1-root,depth-1)-initial;
            }
            restore(&state);
            printf("action %u %u %d %d\n",options[i].from,options[i].to,future,immediate);
        }
        printf("done %lu %d\n",nodes,reference);fflush(stdout);
    }
    return 0;
}
