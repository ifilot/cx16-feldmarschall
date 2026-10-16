#ifndef AI_TEMPLATE_H
#define AI_TEMPLATE_H
#include <stdint.h>
#ifdef __CC65__
#define AI_TEMPLATE_FAST __fastcall__
#else
#define AI_TEMPLATE_FAST
#endif

#ifdef AI_TEMPLATE_PRIOR_Q24
typedef union {
    uint8_t history[80];
    int16_t row[100];
} ai_template_transfer_t;
extern ai_template_transfer_t ai_template_transfer;
extern uint8_t ai_template_owner, ai_template_valid;
enum { AI_TEMPLATE_DISABLED, AI_TEMPLATE_HISTORY, AI_TEMPLATE_PUBLIC,
       AI_TEMPLATE_QUANTIZATION, AI_TEMPLATE_READY };
extern uint8_t ai_template_status;
void AI_TEMPLATE_FAST ai_template_begin(uint8_t owner);
void AI_TEMPLATE_FAST ai_template_actor(uint8_t rank);
/* Disable origin inference after a loaded/custom position; never invent history. */
void ai_template_forget(void);
/* Establish origins on a complete deployment before any first disclosure. */
void ai_template_start(void);
uint8_t AI_TEMPLATE_FAST ai_template_export(uint8_t owner);
uint8_t ai_template_build(void);
void AI_TEMPLATE_FAST ai_template_copy(uint8_t rank);
#if defined(AI_TEST) && !defined(BANKED_AI)
const uint16_t* ai_template_test_flags(void);
const uint16_t* ai_template_test_bombs(void);
uint32_t ai_template_test_evidence(void);
uint8_t ai_template_test_mask(void);
uint8_t ai_template_test_rank(uint8_t table,uint8_t origin);
int16_t ai_template_test_cache(uint8_t rank,uint8_t origin);
#endif
#endif
#endif
