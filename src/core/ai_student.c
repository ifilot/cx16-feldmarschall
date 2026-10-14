/* Integer features shared by offline fitting and the bank-24 runtime. */
#if defined(AI_STUDENT) || defined(AI_FEATURE_TRACE)
#pragma static-locals (on)
#include "ai_student.h"
#include "ai_memory.h"
#include "ai.h"
#include "board.h"
#include "rules.h"
#ifndef AI_MEMORY
#error Student features require AI_MEMORY
#endif
#ifdef BANKED_AI
#pragma code-name ("MISSIONCODE")
#pragma rodata-name ("MISSIONRODATA")
#pragma bss-name ("MISSIONBSS")
#endif
static uint8_t own, flag;
static uint8_t distance(uint8_t a,uint8_t b) {
    return (a/10>b/10?a/10-b/10:b/10-a/10)+(a%10>b%10?a%10-b%10:b%10-a%10);
}
void ai_student_begin(uint8_t army) {
    uint8_t sq;
    own=army; flag=NOWHERE; ai_memory_sync();
    for(sq=0;sq<SQUARES;sq++) if(IS_PIECE(board[sq]) && (board[sq]&CELL_BLUE)==own && PIECE_TYPE(board[sq])==PIECE_FLAG) flag=sq;
}
uint8_t ai_student_feature(uint8_t from,uint8_t to,uint8_t feature) {
    uint8_t cell=board[to], rank=PIECE_TYPE(board[from]), id, sq, count=0, dir, enemy_rank, friend_sq, j;
    static const int8_t step[4]={-10,1,10,-1};
    const ai_piece_history_t* history;
    uint16_t mask;
    id=ai_memory_identity(feature==13?from:to); history=ai_memory_history(id);
    switch(feature) {
        case 0: return rank;
        case 1: return !IS_PIECE(cell)?13:(cell&CELL_REVEALED)?PIECE_TYPE(cell):12;
        case 2: return IS_PIECE(cell);
        case 3: return distance(from,to);
        case 4: return !!(board[from]&CELL_REVEALED);
        case 5: return IS_PIECE(cell) && !!(cell&CELL_MOVED);
        case 6: return IS_PIECE(cell) && !!(cell&CELL_REVEALED);
        case 8: return flag==NOWHERE?255:distance(to,flag);
        case 9: case 13: return history?history->moves:0;
        case 10: return history?history->approach_rank:PIECE_UNKNOWN;
        case 11: return history?history->retreat_rank:PIECE_UNKNOWN;
        case 12:
            if(!history) return 0;
            mask=history->candidates; while(mask) {count+=mask&1;mask>>=1;} return count;
        case 14: return own?9-to/10:to/10;
    }
    /* 7: disclosed threats adjacent to the destination. 15: those threats
     * that a nearby friendly piece could recapture. Exclude the vacated source. */
    for(dir=0;dir<4;dir++) {
        sq=to+step[dir];
        if(sq>=SQUARES || sq==from || distance(to,sq)!=1) continue;
        cell=board[sq];
        if(!IS_PIECE(cell) || (cell&CELL_BLUE)==own || !(cell&CELL_REVEALED)) continue;
        enemy_rank=PIECE_TYPE(cell);
        if(enemy_rank>=PIECE_BOMB || rules_battle(enemy_rank,rank)==BATTLE_DEFENDER) continue;
        if(feature==7) {count++;continue;}
        if(feature!=15) continue;
        for(j=0;j<4;j++) {
            friend_sq=to+step[j];
            if(friend_sq>=SQUARES || friend_sq==from || distance(to,friend_sq)!=1) continue;
            cell=board[friend_sq];
            if(IS_PIECE(cell) && (cell&CELL_BLUE)==own &&
               rules_battle(PIECE_TYPE(cell),enemy_rank)==BATTLE_ATTACKER) {count++;break;}
        }
    }
    return count;
}
#ifdef AI_STUDENT
typedef struct {uint8_t feature,threshold,left,right;int16_t value;} student_node_t;
#include "ai_student_model.h"
int16_t ai_student_score(uint8_t from,uint8_t to) {
    uint8_t node=0;
    if(game_rules || ai_difficulty!=AI_NORMAL || !IS_PIECE(board[to])) return 0;
    while(student_nodes[node].feature!=255)
        node=ai_student_feature(from,to,student_nodes[node].feature)<=student_nodes[node].threshold?
             student_nodes[node].left:student_nodes[node].right;
    return student_nodes[node].value;
}
#endif
#endif
