/* Stable public identities, certain rank constraints, and soft encounter evidence. */
#ifdef AI_MEMORY
#pragma static-locals (on)
#include <string.h>
#include "ai_memory.h"
#include "board.h"
#include "rules.h"
#ifdef AI_TEMPLATE_PRIOR_Q24
#include "ai_template.h"
#endif
#ifdef BANKED_AI
#pragma code-name ("MISSIONCODE")
#pragma rodata-name ("MISSIONRODATA")
#pragma bss-name ("MISSIONBSS")
#define ai_memory_reset ai_memory_reset_banked
#define ai_memory_observe ai_memory_observe_banked
#ifdef AI_TEMPLATE_PRIOR_Q24
#define ai_template_export ai_template_export_banked
#define ai_template_forget ai_template_forget_banked
#endif
#endif

static uint8_t identities[SQUARES], count;
static ai_piece_history_t pieces[AI_MEMORY_PIECES];
#ifdef AI_TEMPLATE_PRIOR_Q24
/* 0 awaits the first public snapshot; 1 valid opening; 2 unavailable history. */
static uint8_t template_history_valid;
#endif

static uint16_t mobile_mask(void) {
    uint16_t mask = 0x03ff;
    if(game_rules & RULE_MOVING_BOMBS) mask |= (uint16_t)1 << PIECE_BOMB;
    if(game_rules & RULE_MOVING_FLAG) mask |= (uint16_t)1 << PIECE_FLAG;
    return mask;
}

static void disclose(ai_piece_history_t* piece, uint8_t cell) {
    uint8_t rank;
    if(cell & CELL_MOVED) piece->candidates &= mobile_mask();
    if(cell & CELL_REVEALED) {
        rank = PIECE_TYPE(cell);
        if(rank < PIECE_TYPES) {
            piece->known_rank = rank;
            piece->candidates = (uint16_t)1 << rank;
        }
    }
}

void ai_memory_reset(void) {
    memset(identities, NOWHERE, sizeof(identities));
    memset(pieces, 0, sizeof(pieces));
    count = 0;
#ifdef AI_TEMPLATE_PRIOR_Q24
    template_history_valid=0;
#endif
}

void ai_memory_sync(void) {
    uint8_t sq, id, cell;
    ai_piece_history_t* piece;
#ifdef AI_TEMPLATE_PRIOR_Q24
    if(!template_history_valid) {
        uint8_t red=0,blue=0;
        template_history_valid=2;
        for(sq=0;sq<SQUARES;sq++) {
            cell=board[sq];
            if(!IS_PIECE(cell))continue;
            if((cell&(CELL_MOVED|CELL_REVEALED)) || !board_home(sq,cell&CELL_BLUE))break;
            if(cell&CELL_BLUE)blue++;else red++;
        }
        if(sq==SQUARES && red==40 && blue==40)template_history_valid=1;
    }
#endif
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq]; id = identities[sq];
        if(id != NOWHERE && (!IS_PIECE(cell) || pieces[id].owner != (cell & CELL_BLUE))) {
            pieces[id].square = NOWHERE; identities[sq] = NOWHERE; id = NOWHERE;
        }
        if(!IS_PIECE(cell)) continue;
        if(id == NOWHERE) {
            if(count >= AI_MEMORY_PIECES) continue;
            id = count++; identities[sq] = id; piece = &pieces[id];
            piece->origin = piece->square = sq;
            piece->owner = cell & CELL_BLUE;
            piece->known_rank = piece->approach_rank = piece->retreat_rank = PIECE_UNKNOWN;
            piece->candidates = 0x0fff;
        }
        disclose(&pieces[id], cell);
    }
}

static uint8_t separation(uint8_t a, uint8_t b) {
    return (a/10 > b/10 ? a/10-b/10 : b/10-a/10) +
           (a%10 > b%10 ? a%10-b%10 : b%10-a%10);
}

void ai_memory_observe(uint8_t from, uint8_t to, uint8_t outcome) {
    uint8_t id, other, sq, cell, rank, before, after;
    uint16_t possible = 0;
    ai_piece_history_t* moving;
    ai_piece_history_t* defender;
    ai_memory_sync();
    id = identities[from]; other = identities[to];
    if(id == NOWHERE) return;
    moving = &pieces[id];
    if(moving->moves < 255) moving->moves++;
    moving->candidates &= mobile_mask();
    if(separation(from, to) > 1) {
        moving->known_rank = PIECE_SCOUT;
        moving->candidates = (uint16_t)1 << PIECE_SCOUT;
    }
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(!IS_PIECE(cell) || (cell & CELL_BLUE) == moving->owner ||
           !(cell & CELL_REVEALED) || PIECE_TYPE(cell) >= PIECE_TYPES) continue;
        before = separation(from, sq); after = separation(to, sq);
        if(before > 1 && after == 1) moving->approach_rank = PIECE_TYPE(cell);
        if(before == 1 && after > 1) moving->retreat_rank = PIECE_TYPE(cell);
    }
    if(other != NOWHERE && outcome != AI_MEMORY_QUIET) {
        defender = &pieces[other];
        if(moving->battles < 255) moving->battles++;
        if(defender->battles < 255) defender->battles++;
        /* Attacker ranks are always public after combat. Silent defenders may
         * stay unknown, but the observed outcome legitimately constrains them. */
        rank = PIECE_TYPE(board[from]);
        if(rank < PIECE_TYPES) {
            moving->known_rank = rank; moving->candidates = (uint16_t)1 << rank;
            for(sq=0; sq<PIECE_TYPES; sq++)
                if(rules_battle(rank, sq) == outcome) possible |= (uint16_t)1 << sq;
            defender->candidates &= possible;
            for(sq=0; sq<PIECE_TYPES; sq++)
                if(defender->candidates == ((uint16_t)1 << sq)) defender->known_rank = sq;
        }
        if(outcome != BATTLE_DEFENDER) defender->square = NOWHERE;
    }
    identities[from] = NOWHERE;
    if(outcome == BATTLE_DEFENDER || outcome == BATTLE_BOTH) moving->square = NOWHERE;
    else { moving->square = to; identities[to] = id; }
    if(outcome == BATTLE_BOTH) identities[to] = NOWHERE;
}

uint8_t ai_memory_identity(uint8_t square) {
    return square < SQUARES ? identities[square] : NOWHERE;
}

const ai_piece_history_t* ai_memory_history(uint8_t identity) {
    return identity < count ? &pieces[identity] : 0;
}

#ifdef AI_TEMPLATE_PRIOR_Q24
void ai_template_forget(void) { template_history_valid=2; }
uint8_t AI_TEMPLATE_FAST ai_template_export(uint8_t owner) {
    uint8_t id,n=0,index;
    const ai_piece_history_t* piece;
    if(template_history_valid!=1)return 0;
    for(id=0;id<count;id++) {
        piece=&pieces[id];if(piece->owner==owner)continue;
        if(piece->origin>=60)index=piece->origin-60;
        else if(piece->origin<40)index=(3-piece->origin/10)*10+piece->origin%10;
        else return 0;
        ai_template_transfer.history[index]=piece->known_rank|(piece->moves?128:0);
        ai_template_transfer.history[40+index]=piece->square;n++;
    }
    return n==40;
}
#endif

uint16_t ai_memory_weight(uint8_t square, uint8_t rank, const uint8_t* prior) {
    uint8_t id = ai_memory_identity(square), factor = 1;
    const ai_piece_history_t* piece;
    if(id == NOWHERE || rank >= PIECE_TYPES) return 0;
    piece = &pieces[id];
    if(!(piece->candidates & ((uint16_t)1 << rank))) return 0;
    if(piece->known_rank != PIECE_UNKNOWN) return 1;
    if(piece->approach_rank < PIECE_TYPES && rules_battle(rank, piece->approach_rank) == BATTLE_ATTACKER) factor++;
    if(piece->retreat_rank < PIECE_TYPES && rules_battle(piece->retreat_rank, rank) == BATTLE_ATTACKER) factor++;
    return (uint16_t)prior[rank] * factor;
}

#ifdef AI_TEST
void ai_memory_save(uint8_t* out) {
    memcpy(out, identities, SQUARES);
    memcpy(out+SQUARES, pieces, sizeof(pieces));
    out[SQUARES+sizeof(pieces)] = count;
#ifdef AI_TEMPLATE_PRIOR_Q24
    out[SQUARES+sizeof(pieces)+1]=template_history_valid;
#endif
}
void ai_memory_load(const uint8_t* in) {
    memcpy(identities, in, SQUARES);
    memcpy(pieces, in+SQUARES, sizeof(pieces));
    count = in[SQUARES+sizeof(pieces)];
#ifdef AI_TEMPLATE_PRIOR_Q24
    template_history_valid=in[SQUARES+sizeof(pieces)+1];
#endif
}
#endif
#endif
