#ifndef AI_MISSION_H
#define AI_MISSION_H
#include <stdint.h>

/* One shared flag-approach mission, rebuilt from the permitted view each turn. */
void ai_mission_reset(void);
void ai_mission_begin(uint8_t army);
int16_t ai_mission_score(uint8_t from, uint8_t to);
#ifdef AI_TEST
void ai_mission_save(uint8_t* out);
void ai_mission_load(const uint8_t* in);
uint8_t ai_mission_test_target(uint8_t army);
#ifdef AI_MISSION_PROGRESS
uint8_t ai_mission_test_stalled(uint8_t army);
#endif
#endif
#endif
