#ifndef AI_MEMORY_H
#define AI_MEMORY_H
#include <stdint.h>

/* Public history only: own private ranks are deliberately excluded too.
 * Query routines reside in bank 24 on X16; observe has a gateway, and reset
 * runs through the existing mission reset. */
#if defined(BANKED_AI) && !defined(AI_MISSIONS)
#error Banked AI_MEMORY requires AI_MISSIONS
#endif
#define AI_MEMORY_PIECES 84 /* eighty initial pieces plus four possible rescues */
#ifdef AI_TEMPLATE_PRIOR_Q24
#define AI_MEMORY_STATE_SIZE 942
#else
#define AI_MEMORY_STATE_SIZE 941
#endif
#define AI_MEMORY_QUIET 3
typedef struct {
    uint8_t origin, square, owner, moves, battles, known_rank;
    uint8_t approach_rank, retreat_rank;
    uint16_t candidates;
} ai_piece_history_t;

void ai_memory_reset(void);
/* Call after public battle disclosure, BEFORE changing either board square. */
void ai_memory_observe(uint8_t from, uint8_t to, uint8_t outcome);
void ai_memory_sync(void);
uint8_t ai_memory_identity(uint8_t square);
const ai_piece_history_t* ai_memory_history(uint8_t identity);
/* Unnormalized uncertain weight; positive priors remain possible despite bluffing. */
uint16_t ai_memory_weight(uint8_t square, uint8_t rank, const uint8_t* prior);
#ifdef AI_TEST
void ai_memory_save(uint8_t* out);
void ai_memory_load(const uint8_t* in);
#endif
#endif
