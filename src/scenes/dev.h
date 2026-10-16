#ifndef _DEV_H
#define _DEV_H

#include <stdint.h>

/*
 * Developer scenarios: positions that put a game straight into a situation
 * worth testing, mostly the ways a game ends. Typing DEV at the main menu
 * lists them there (see menu.c); tools/test_endings.py plays them.
 */
#define DEV_SCENARIOS   6

extern const char* const dev_names[DEV_SCENARIOS];

/**
 * @brief Set up scenario n on the board
 *
 * @return the scene that plays it
 */
uint8_t dev_start(uint8_t n);

#endif
