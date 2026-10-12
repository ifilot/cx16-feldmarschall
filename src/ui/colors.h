#ifndef _COLORS_H
#define _COLORS_H

#include <stdint.h>

#define FIELD_PROFILE_COUNT 4
#define ARMY_PROFILE_COUNT 6

extern uint8_t colors_field;
extern uint8_t colors_armies;

uint8_t colors_init(void);
void colors_apply(void);
uint8_t colors_restore_field(void);
uint8_t colors_save(void);
const char* colors_name(uint8_t group, uint8_t profile);
uint8_t colors_count(uint8_t group);
uint8_t colors_current(uint8_t group);
uint8_t colors_select(uint8_t group, uint8_t profile);

#endif
