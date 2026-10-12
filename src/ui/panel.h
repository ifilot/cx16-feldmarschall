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

#ifndef _PANEL_H
#define _PANEL_H

#include <stdint.h>
#include "gfx.h"

#define TRAY_SLOTS      (TRAY_COLS * TRAY_ROWS)

/* tray compartments, filled row by row; each holds a board cell value */
extern uint8_t tray[TRAY_SLOTS];

/**
 * @brief Status lines of the info plate, e.g. "RED TO MOVE" and "TURN 23"
 */
void panel_info(const char* status, uint8_t color, const char* detail);

/**
 * @brief Name the selected piece (a cell value) in the info plate
 *
 * Blue's unrevealed pieces are named UNKNOWN.
 */
void panel_selected(uint8_t cell);

/**
 * @brief Clear the lower half of the info plate
 */
void panel_clear_selected(void);

/**
 * @brief Fill the tray with Red's pieces that are not yet on the board
 *
 * The tray keeps every piece in a fixed compartment, strongest first, so
 * a deployed piece leaves its compartment empty.
 */
void panel_tray_reserve(void);

/**
 * @brief Fill the tray with the pieces an army has lost
 *
 * Every piece of the army keeps its compartment, strongest first: a fallen
 * piece shows face up, a piece still on the board leaves it empty.
 */
void panel_tray_fallen(uint8_t blue);

/**
 * @brief Empty every compartment (without drawing)
 */
void panel_tray_clear(void);

void panel_tray_draw(void);

/**
 * @brief Redraw one tray compartment
 */
void panel_tray_slot(uint8_t i);

/**
 * @brief Take the piece out of a compartment, leaving it empty
 */
uint8_t panel_tray_take(uint8_t i);

/**
 * @brief The compartment a piece returns to: the first empty one of its rank
 */
uint8_t panel_tray_home(uint8_t cell);

/**
 * @brief Put a piece back in its home compartment
 */
void panel_tray_put(uint8_t cell);

/**
 * @brief Number of pieces in the tray
 */
uint8_t panel_tray_count(void);

/**
 * @brief The tray compartment under a screen pixel, or NOWHERE
 */
uint8_t panel_slot_at(int16_t x, int16_t y);

/**
 * @brief Top-left screen pixel of a tray compartment
 */
int16_t panel_slot_x(uint8_t i);
int16_t panel_slot_y(uint8_t i);

/**
 * @brief Two lines of text in the message bar (brown, then ink)
 */
void panel_bar(const char* line0, const char* line1);

/**
 * @brief A battle in the message bar: both tokens and the outcome
 *
 * @param heading    e.g. "RED ATTACKS"
 * @param red_piece  piece type of the red combatant
 * @param blue_piece piece type of the blue combatant
 */
void panel_battle(const char* heading, uint8_t red_piece, uint8_t blue_piece,
                  const char* result);

/**
 * @brief Decimal string of a number (valid until the next call)
 */
const char* panel_number(uint16_t n);

#endif
