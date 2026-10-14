#ifndef AI_STUDENT_H
#define AI_STUDENT_H
#include <stdint.h>
#define AI_STUDENT_FEATURES 16
void ai_student_begin(uint8_t army);
uint8_t ai_student_feature(uint8_t from, uint8_t to, uint8_t feature);
int16_t ai_student_score(uint8_t from, uint8_t to);
#endif
