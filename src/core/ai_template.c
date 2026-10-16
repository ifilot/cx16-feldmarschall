/* Fixed public Colonel-template mixture; opt-in Q24 numerical research policy. */
#include "ai_template.h"
#ifdef AI_TEMPLATE_PRIOR_Q24
#pragma static-locals (on)
#include <string.h>
#include "ai_template.h"
#include "ai.h"
#include "ai_memory.h"
#include "board.h"
#include "rules.h"

/* These bytes remain in MAIN while any executable RAM bank is selected. */
ai_template_transfer_t ai_template_transfer;
uint8_t ai_template_owner, ai_template_valid;
uint8_t ai_template_status;
#ifndef BANKED_AI
void ai_template_start(void) { ai_memory_sync(); }
#endif

void AI_TEMPLATE_FAST ai_template_begin(uint8_t owner) {
    ai_template_valid=0;
    ai_template_status=AI_TEMPLATE_DISABLED;
    if(game_rules || ai_difficulty!=AI_NORMAL) return;
    ai_template_owner=owner;
    ai_template_status=AI_TEMPLATE_HISTORY;
    if(ai_template_export(owner)) ai_template_valid=ai_template_build();
}
void AI_TEMPLATE_FAST ai_template_actor(uint8_t rank) {
    if(ai_template_valid) ai_template_copy(rank);
}

#ifdef BANKED_AI
#pragma code-name ("BELIEFCODE")
#pragma rodata-name ("BELIEFRODATA")
#pragma bss-name ("BELIEFBSS")
#define ai_template_build ai_template_build_banked
#define ai_template_copy ai_template_copy_banked
#ifdef AI_TEMPLATE_PRIOR_Q24_CACHE
#define ai_template_cache_reset ai_template_cache_reset_banked
#endif
#endif
#define ONE 16777216L
#define Q12 4096u
static const int16_t values[12]={400,200,100,75,45,30,15,25,10,100,20,1000};
static const uint8_t templates[8][40]={
    {3,4,1,5,2,3,8,6,5,8,6,10,9,6,7,0,7,4,10,5,10,4,8,5,8,10,4,8,2,10,8,8,7,6,7,3,8,7,10,11},
    {8,5,6,8,3,2,5,1,4,3,5,10,4,7,0,7,6,9,10,6,10,2,8,4,10,8,5,8,4,10,11,10,7,8,3,7,6,7,8,8},
    {3,4,8,5,3,2,8,1,5,8,6,10,4,8,0,7,9,7,6,5,10,4,8,5,7,8,4,10,2,10,8,7,6,7,8,3,10,11,10,6},
    {8,5,1,8,2,3,5,8,4,3,5,6,7,9,7,0,8,4,10,6,10,2,10,4,8,7,5,8,4,10,6,10,11,10,3,8,7,6,7,8},
    {4,8,5,8,3,2,8,4,8,3,6,2,9,6,1,7,6,7,5,8,10,6,5,4,10,3,10,0,4,10,8,7,8,7,8,10,11,10,7,5},
    {3,8,4,8,2,3,8,5,8,4,8,5,7,6,7,1,6,9,2,6,10,4,0,10,3,10,4,5,6,10,5,7,10,11,10,8,7,8,7,8},
    {4,8,5,8,3,2,8,4,8,3,6,2,4,10,7,0,6,9,1,8,10,5,7,5,8,6,10,4,7,10,8,7,8,7,3,10,11,10,6,5},
    {3,8,4,8,2,3,8,5,8,4,8,1,9,6,0,7,10,4,2,6,10,7,4,10,6,8,5,7,5,10,5,6,10,11,10,3,7,8,7,8},
};
static uint8_t history[80], known[12], remaining[12], flags_at[40], bombs_at[40];
static uint8_t allowed, compatible, unknown_unmoved, hidden_mobile;
static uint16_t flag_q[40], bomb_q[40], flag_remainder[40], bomb_remainder[40];
static uint8_t increments[40], capacity[40];
static int16_t cache[12][40], worth[12];
static int32_t evidence, background;
#ifdef AI_TEMPLATE_PRIOR_Q24_CACHE
/* Key bit64 represents dead origins; source history byte remains unchanged. */
static uint8_t cache_key[40], cache_owner, cache_marshal_lost, cache_bombs_lost;
static uint8_t cache_valid, cache_hit;
void ai_template_cache_reset(void) { cache_valid=cache_hit=0; }
#endif

/* Binary fixed-point division, avoiding an unavailable 64-bit intermediate. */
static int32_t fraction(int32_t numerator,int32_t denominator) {
    int32_t result=0;
    uint8_t bit;
    if(!denominator || numerator>=denominator) return ONE;
    for(bit=0;bit<24;bit++) {
        numerator<<=1; result<<=1;
        if(numerator>=denominator) {numerator-=denominator;result++;}
    }
    return result;
}

static uint8_t collect(void) {
    uint8_t i,r,t,cell,seen[12],total=0,moved=0,known_total=0,mobile=33,n;
    memcpy(history,ai_template_transfer.history,80);
    memset(known,0,sizeof(known));memset(seen,0,sizeof(seen));
    allowed=255;unknown_unmoved=hidden_mobile=0;
    for(i=0;i<40;i++) {
        r=history[i]&15;
        if(r<12) {known[r]++;known_total++;if(r<10)mobile--;}
        else if(history[i]&128) moved++;
        else if(history[40+i]!=NOWHERE) unknown_unmoved++;
        for(t=0;t<8;t++) if((allowed&((uint8_t)1<<t)) &&
            ((r<12 && templates[t][i]!=r) || ((history[i]&128) && templates[t][i]>=10)))
                allowed&=~((uint8_t)1<<t);
    }
    for(i=0;i<100;i++) {
        cell=board[i];
        if(IS_PIECE(cell) && (cell&CELL_BLUE)!=ai_template_owner && (cell&CELL_REVEALED)) {
            r=PIECE_TYPE(cell);if(r>=12)return 0;seen[r]++;
        }
    }
    for(r=0;r<12;r++) {
        if(known[r]>piece_counts[r] || known[r]!=seen[r]+rules_known_lost[ai_template_owner?0:1][r])return 0;
        remaining[r]=piece_counts[r]-known[r];
        if(r<10)hidden_mobile+=remaining[r];
    }
    if(moved>hidden_mobile || remaining[10]+remaining[11]>unknown_unmoved)return 0;
    evidence=ONE;
    /* Any fixed order gives the same exact rational; Q24 floors are explicit. */
    for(r=0;r<12;r++)for(n=0;n<known[r];n++) {
        evidence=evidence*(int32_t)(piece_counts[r]-n)/(40-total);total++;
    }
    for(n=0;n<moved;n++)evidence=evidence*(int32_t)(mobile-n)/(40-known_total-n);
    compatible=0;for(t=0;t<8;t++)if(allowed&((uint8_t)1<<t))compatible++;
    background=compatible?fraction(2L*evidence,(int32_t)compatible*ONE+2L*evidence):ONE;
    return 1;
}

/* Two-column maximum-remainder rounding. Each B augmentation can displace
 * one selected F to another row, preserving feasibility and exact inventory. */
static uint8_t quantize(void) {
    uint8_t i,t,need_f,need_b,best,destination,chosen_to,cf,cb;
    uint16_t sum_f=0,sum_b=0;
    int32_t tf,tb,per;
    int32_t best_gain,gain;
    per=compatible?(ONE-background)/compatible:0;
    memset(increments,0,sizeof(increments));
    for(i=0;i<40;i++) {
        tf=tb=0;cf=cb=0;
        if((history[i]&15)>=12 && !(history[i]&128) && history[40+i]!=NOWHERE) {
            for(t=0;t<8;t++)if(allowed&((uint8_t)1<<t)) {
                if(templates[t][i]==11)cf++;
                if(templates[t][i]==10)cb++;
            }
            tf=(int32_t)cf*per+background*remaining[11]/unknown_unmoved;
            tb=(int32_t)cb*per+background*remaining[10]/unknown_unmoved;
        }
        flags_at[i]=tf!=0;bombs_at[i]=tb!=0;
        flag_q[i]=tf>>12;bomb_q[i]=tb>>12;
        flag_remainder[i]=tf&4095;bomb_remainder[i]=tb&4095;
        sum_f+=flag_q[i];sum_b+=bomb_q[i];
        capacity[i]=(Q12-flag_q[i]-bomb_q[i])>=2?2:(uint8_t)(Q12-flag_q[i]-bomb_q[i]);
    }
    if(sum_f>(uint16_t)remaining[11]*Q12 || sum_b>(uint16_t)remaining[10]*Q12)return 0;
    if((uint16_t)remaining[11]*Q12-sum_f>40 || (uint16_t)remaining[10]*Q12-sum_b>40)return 0;
    need_f=(uint16_t)remaining[11]*Q12-sum_f;need_b=(uint16_t)remaining[10]*Q12-sum_b;
    while(need_f--) {
        best=NOWHERE;best_gain=-2147483647L;
        for(i=0;i<40;i++)if(flags_at[i] && !(increments[i]&1) && capacity[i] &&
            (int32_t)flag_remainder[i]>best_gain) {best=i;best_gain=flag_remainder[i];}
        if(best==NOWHERE)return 0;
        increments[best]|=1;capacity[best]--;
    }
    while(need_b--) {
        best=chosen_to=NOWHERE;best_gain=-2147483647L;
        for(i=0;i<40;i++)if(bombs_at[i] && !(increments[i]&2)) {
            if(capacity[i]) {
                gain=bomb_remainder[i];
                if(gain>best_gain) {best=i;chosen_to=NOWHERE;best_gain=gain;}
            } else if(increments[i]&1) {
                destination=NOWHERE;
                for(t=0;t<40;t++)if(t!=i && flags_at[t] && !(increments[t]&1) && capacity[t] &&
                    (destination==NOWHERE || flag_remainder[t]>flag_remainder[destination]))destination=t;
                if(destination!=NOWHERE) {
                    gain=(int32_t)bomb_remainder[i]-flag_remainder[i]+flag_remainder[destination];
                    if(gain>best_gain) {best=i;chosen_to=destination;best_gain=gain;}
                }
            }
        }
        if(best==NOWHERE)return 0;
        if(chosen_to!=NOWHERE) {
            increments[best]&=~1;capacity[best]++;
            increments[chosen_to]|=1;capacity[chosen_to]--;
        }
        increments[best]|=2;capacity[best]--;
    }
    for(i=0;i<40;i++) {flag_q[i]+=!!(increments[i]&1);bomb_q[i]+=!!(increments[i]&2);}
    return 1;
}

static int16_t gain(uint8_t a,uint8_t d) {
    uint8_t outcome;
    if(d==11)return 2000;
    outcome=rules_battle(a,d);
    return outcome==BATTLE_ATTACKER?worth[d]:outcome==BATTLE_DEFENDER?-worth[a]:worth[d]-worth[a];
}
uint8_t ai_template_build(void) {
    uint8_t a,r,i;
    int32_t mobile_gain,immobile,numerator,denominator;
    ai_template_status=AI_TEMPLATE_PUBLIC;
    #ifdef AI_TEMPLATE_PRIOR_Q24_CACHE
    cache_hit=0;
    #endif
    if(!collect())return 0;
#ifdef AI_TEMPLATE_PRIOR_Q24_CACHE
    if(cache_valid && cache_owner==ai_template_owner &&
       cache_marshal_lost==rules_known_lost[ai_template_owner?0:1][0] &&
       cache_bombs_lost==rules_known_lost[ai_template_owner?0:1][10]) {
        for(i=0;i<40;i++)if(cache_key[i]!=(history[i]|(history[40+i]==NOWHERE?64:0)))break;
        if(i==40) {cache_hit=1;ai_template_status=AI_TEMPLATE_READY;return 1;}
    }
    cache_valid=0;
#endif
    ai_template_status=AI_TEMPLATE_QUANTIZATION;
    if(!quantize())return 0;
    memcpy(worth,values,sizeof(worth));
    if(piece_counts[10]>rules_known_lost[ai_template_owner?0:1][10])worth[7]=40;
    if(piece_counts[0]==rules_known_lost[ai_template_owner?0:1][0])worth[9]=15;
    for(a=0;a<12;a++) {
        mobile_gain=0;for(r=0;r<10;r++)mobile_gain+=(int32_t)remaining[r]*gain(a,r);
        for(i=0;i<40;i++) {
            immobile=(int32_t)flag_q[i]*2000L+(int32_t)bomb_q[i]*gain(a,10);
            if(!hidden_mobile) {numerator=immobile;denominator=Q12;}
            else {
                numerator=immobile*(int32_t)hidden_mobile+(int32_t)(Q12-flag_q[i]-bomb_q[i])*mobile_gain;
                denominator=(int32_t)Q12*hidden_mobile;
            }
            /* cc65 can propagate unsigned small-factor arithmetic into long
             * division. Divide a nonnegative magnitude, then restore sign;
             * this also keeps negative constant divisions truncating to zero. */
            if(numerator<0)cache[a][i]=-(int16_t)((-numerator)/denominator);
            else cache[a][i]=numerator/denominator;
        }
    }
#ifdef AI_TEMPLATE_PRIOR_Q24_CACHE
    for(i=0;i<40;i++)cache_key[i]=history[i]|(history[40+i]==NOWHERE?64:0);
    cache_owner=ai_template_owner;
    cache_marshal_lost=rules_known_lost[ai_template_owner?0:1][0];
    cache_bombs_lost=rules_known_lost[ai_template_owner?0:1][10];
    cache_valid=1;
#endif
    ai_template_status=AI_TEMPLATE_READY;
    return 1;
}
void AI_TEMPLATE_FAST ai_template_copy(uint8_t rank) {
    uint8_t i,square;
    memset(ai_template_transfer.row,0,200);
    for(i=0;i<40;i++) {
        square=history[40+i];
        if(square<100 && (history[i]&15)>=12 && !(history[i]&128))ai_template_transfer.row[square]=cache[rank][i];
    }
}
#if defined(AI_TEST) && !defined(BANKED_AI)
const uint16_t* ai_template_test_flags(void) {return flag_q;}
const uint16_t* ai_template_test_bombs(void) {return bomb_q;}
uint32_t ai_template_test_evidence(void) {return evidence;}
uint8_t ai_template_test_mask(void) {return allowed;}
uint8_t ai_template_test_rank(uint8_t table,uint8_t origin) {return templates[table][origin];}
int16_t ai_template_test_cache(uint8_t rank,uint8_t origin) {return cache[rank][origin];}
#ifdef AI_TEMPLATE_PRIOR_Q24_CACHE
uint8_t ai_template_test_cache_hit(void) {return cache_hit;}
void ai_template_test_cache_poison(void) {memset(cache_key,165,40);cache_valid=cache_hit=cache_owner=cache_marshal_lost=cache_bombs_lost=165;}
#endif
#endif
#endif
