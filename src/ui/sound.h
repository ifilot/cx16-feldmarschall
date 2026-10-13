#ifndef _SOUND_H
#define _SOUND_H

#include <stdint.h>
#include "sfx.h"

/* ZSMKit: bank 1; effects: bank 2; songs: banks 3..21; play: 22; AI: 23. */
#define PLAY_BANK 22
uint8_t sound_init(void);
void sound_scene(uint8_t scene);
void sound_result(uint8_t winner);
void __fastcall__ sound_sfx(uint16_t offset);
void sound_toggle_music(void);
void sound_toggle_effects(void);
extern uint8_t sound_music_enabled;
extern uint8_t sound_effects_enabled;
extern uint8_t sound_ready;
extern uint8_t sound_music_bank;
extern uint16_t sound_last_sfx;

#endif
