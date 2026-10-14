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

#ifndef _AI_H
#define _AI_H

#include <stdint.h>

#define AI_EASY   0
#define AI_NORMAL 1
#define AI_HARD   2
#define AI_LEVELS 3
extern uint8_t ai_difficulty;
extern const char* const ai_level_names[AI_LEVELS];

/* Replace every undisclosed enemy rank, including Spy/Marshal/Flag, in place. */
void ai_mask(uint8_t army);

/**
 * @brief Choose a move for one army, from what that army knows
 *
 * The board must hold the army's view: its own pieces, and the enemy's
 * pieces with their true type only once revealed (CELL_REVEALED); every
 * other enemy piece has type PIECE_UNKNOWN. The caller keeps the truth.
 *
 * Single-move tactical evaluation with persistent per-piece objectives and
 * breadth-first routes around lakes and occupied squares. Hidden attacks use
 * remaining-rank counts and movement evidence; undisclosed ranks stay unknown.
 * Resulting occupancy is checked for adjacent and long-range scout danger,
 * immediate flag defence, and immediate victories. Specialist values depend
 * on remaining enemy ranks. Small random adjustments vary similar choices.
 * Easy simplifies planning and varies scores more; Normal uses this evaluator.
 * Hard checks the best material reply to six shortlisted moves, weighting
 * concealed combat outcomes. All levels receive the same masked information.
 *
 * @param army CELL_BLUE for Blue, 0 for Red
 * @param lost the enemy's captured pieces, per type
 * @param from set to the square of the piece to move (NOWHERE if none)
 * @param to   set to its destination
 */
void ai_move(uint8_t army, const uint8_t* lost, uint8_t* from, uint8_t* to);

/**
 * @brief Forget goals and both armies' move histories (at the start of a game)
 */
void ai_reset(void);

#ifdef AI_TEST
#define AI_TEST_STATE_SIZE 204
void ai_test_save(uint8_t* out);
void ai_test_load(const uint8_t* in);
#endif

#ifdef AI_TRACE
/* supplied by a test build: called with the score of every candidate move */
void ai_trace(uint8_t from, uint8_t to, int16_t score);
#endif

#endif
