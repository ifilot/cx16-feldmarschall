/**************************************************************************
 *                                                                        *
 *   Author: Ivo Filot <ivo@ivofilot.nl>                                  *
 *                                                                        *
 *   CX16-FELDMARSCHALL is free software:                                 *
 *   you can redistribute it and/or modify it under the terms of the      *
 *   GNU General Public License as published by the Free Software         *
 *   Foundation, either version 3 of the License, or (at your option)     *
 *   any later version.                                                   *
 *                                                                        *
 *   CX16-FELDMARSCHALL is distributed in the hope that it will be        *
 *   useful, but WITHOUT ANY WARRANTY; without even the implied           *
 *   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     *
 *   See the GNU General Public License for more details.                 *
 *                                                                        *
 *   You should have received a copy of the GNU General Public License    *
 *   along with this program.  If not, see http://www.gnu.org/licenses/.  *
 *                                                                        *
 **************************************************************************/

#ifndef _BOARD_H
#define _BOARD_H

#include <stdint.h>
#include "pieces.h"

/*
 * The board is a flat array of 100 squares, row by row from the top: Blue
 * deploys on rows 0-3, Red (the player) on rows 6-9. On screen, row 0 is
 * labelled 10 and column 0 is labelled A.
 */
#define BOARD_SIZE          10
#define SQUARES             (BOARD_SIZE * BOARD_SIZE)
#define SETUP_ROWS          4
#define BLUE_HOME0          0
#define RED_HOME0           ((BOARD_SIZE - SETUP_ROWS) * BOARD_SIZE)
#define NOWHERE             0xFF

#define SQUARE_COL(sq)      ((sq) % BOARD_SIZE)
#define SQUARE_ROW(sq)      ((sq) / BOARD_SIZE)

extern uint8_t board[SQUARES];

/**
 * @brief Empty the board, leaving only the two lakes
 */
void board_clear(void);

/**
 * @brief Count the pieces of one type an army has on the board
 */
uint8_t board_count(uint8_t type, uint8_t blue);

/**
 * @brief Whether a square lies in an army's home rows
 */
uint8_t board_home(uint8_t sq, uint8_t blue);

#endif
