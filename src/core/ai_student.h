#ifndef AI_STUDENT_H
#define AI_STUDENT_H
#include <stdint.h>
#ifdef AI_STUDENT_CONTEXT
#define AI_STUDENT_FEATURES 21
void ai_student_inventory(const uint8_t* lost);
#else
#define AI_STUDENT_FEATURES 16
#endif
void ai_student_begin(uint8_t army);
uint8_t ai_student_feature(uint8_t from, uint8_t to, uint8_t feature);
int16_t ai_student_score(uint8_t from, uint8_t to);
#endif
