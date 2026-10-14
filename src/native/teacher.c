/* Desktop-only three-ply tactical teacher. Each input is a sampled consistent
 * complete world, never a referee's concealed truth. Root actions are exhaustive;
 * later actions use a material-ordered beam, including quiet evasions. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "board.h"
#include "rules.h"

#define BEAM 8
#define WIN 20000
static const int16_t value[PIECE_TYPES] = {400,200,100,75,45,30,15,25,10,100,20,1000};
static int16_t worth[2][PIECE_TYPES];
static uint8_t root;
static unsigned long nodes;
typedef struct { uint8_t from, to; int score; } move_t;
typedef struct { uint8_t cells[SQUARES], rules[RULES_STATE_SIZE]; } state_t;

static void save(state_t* state) { memcpy(state->cells, board, SQUARES); rules_state_save(state->rules); }
static void restore(const state_t* state) { memcpy(board, state->cells, SQUARES); rules_state_load(state->rules); }
static int material(void) {
    int score = 0;
    uint8_t sq, owner;
    for(sq=0; sq<SQUARES; sq++) if(IS_PIECE(board[sq])) {
        owner = !!(board[sq] & CELL_BLUE);
        score += (owner == root ? 1 : -1) * worth[owner][PIECE_TYPE(board[sq])];
    }
    return score;
}
static unsigned moves(uint8_t army, move_t* out) {
    uint8_t sq, target[MAX_TARGETS], n, i, rank, other;
    unsigned count = 0;
    int score;
    for(sq=0; sq<SQUARES; sq++) {
        if(!IS_PIECE(board[sq]) || !!(board[sq] & CELL_BLUE) != army) continue;
        rank = PIECE_TYPE(board[sq]); n = rules_targets(sq, target);
        for(i=0; i<n; i++) {
            score = 0;
            if(IS_PIECE(board[target[i]])) {
                other = PIECE_TYPE(board[target[i]]);
                if(other == PIECE_FLAG) score = WIN;
                else switch(rules_battle(rank, other)) {
                    case BATTLE_ATTACKER: score = worth[1-army][other]; break;
                    case BATTLE_DEFENDER: score = -worth[army][rank]; break;
                    default: score = worth[1-army][other] - worth[army][rank];
                }
            }
            out[count++] = (move_t){sq, target[i], score};
        }
    }
    return count;
}
static int compare(const void* a, const void* b) { return ((const move_t*)b)->score - ((const move_t*)a)->score; }
static int search(uint8_t army, unsigned depth, int alpha, int beta) {
    move_t options[2000];
    state_t state;
    unsigned n, i, limit;
    int score, best = army == root ? -30000 : 30000;
    nodes++;
    if(!depth) return material();
    n = moves(army, options);
    if(!n) {
        if(!rules_has_move(1-army)) return 0;
        return army == root ? -WIN : WIN;
    }
    qsort(options, n, sizeof(move_t), compare);
    limit = n < BEAM ? n : BEAM;
    save(&state);
    for(i=0; i<limit; i++) {
        if(IS_PIECE(board[options[i].to]) && PIECE_TYPE(board[options[i].to]) == PIECE_FLAG)
            score = army == root ? WIN : -WIN;
        else {
            rules_apply(options[i].from, options[i].to);
            score = search(1-army, depth-1, alpha, beta);
            restore(&state);
        }
        if(army == root) { if(score > best) best = score; if(best > alpha) alpha = best; }
        else { if(score < best) best = score; if(best < beta) beta = best; }
        if(alpha >= beta) break;
    }
    return best;
}

static int hex(const char* text, uint8_t* out, unsigned n) {
    unsigned i, byte;
    if(strlen(text) != n*2) return 0;
    for(i=0; i<n; i++) { if(sscanf(text+2*i,"%2x",&byte)!=1) return 0; out[i]=byte; }
    return 1;
}
int main(void) {
    char line[512], cells[201], shuttle[13];
    unsigned army, depth, n, i;
    uint8_t owner, rank, sq, counts[2][PIECE_TYPES], state_bytes[RULES_STATE_SIZE], history[6];
    int initial, immediate, future, stand_pat;
    move_t options[2000];
    state_t state;
    while(fgets(line,sizeof(line),stdin)) {
        if(sscanf(line,"search %u %u %200s %12s",&army,&depth,cells,shuttle)!=4 || army>1 || depth<1 || depth>3) {
            puts("error search"); fflush(stdout); continue;
        }
        if(!hex(cells,board,SQUARES) || !hex(shuttle,history,6)) { puts("error hex"); fflush(stdout); continue; }
        memset(counts,0,sizeof(counts));
        for(sq=0; sq<SQUARES; sq++) if(IS_PIECE(board[sq])) {
            rank=PIECE_TYPE(board[sq]); if(rank>=PIECE_TYPES) break;
            counts[!!(board[sq]&CELL_BLUE)][rank]++;
        }
        if(sq<SQUARES) { puts("error incomplete world"); fflush(stdout); continue; }
        root=army; game_rules=0; rules_reset();
        rules_state_save(state_bytes); memcpy(state_bytes+RULES_STATE_SIZE-6,history,6); rules_state_load(state_bytes);
        for(owner=0; owner<2; owner++) {
            memcpy(worth[owner],value,sizeof(value));
            if(counts[1-owner][PIECE_BOMB]) worth[owner][PIECE_MINER]=40;
            if(!counts[1-owner][PIECE_MARSHAL]) worth[owner][PIECE_SPY]=15;
        }
        initial=material(); save(&state); n=moves(root,options); nodes=0;
        stand_pat=search(1-root,depth-1,-30000,30000)-initial;
        restore(&state);
        for(i=0; i<n; i++) {
            if(IS_PIECE(board[options[i].to]) && PIECE_TYPE(board[options[i].to])==PIECE_FLAG) immediate=future=WIN-initial;
            else {
                rules_apply(options[i].from,options[i].to);
                immediate=material()-initial;
                future=search(1-root,depth-1,-30000,30000)-initial;
                restore(&state);
            }
            printf("action %u %u %d %d\n",options[i].from,options[i].to,future,immediate);
        }
        printf("done %lu %d\n",nodes,stand_pat); fflush(stdout);
    }
    return 0;
}
