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
#ifdef AI_MEMORY
#include "ai_memory.h"
#endif

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
 * Normal and Hard share an evidence-driven miner approach mission, assigning
 * route clearing, reconnaissance and attacks to supporting pieces.
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
#ifdef AI_DIAGNOSTICS
/* Correct a diagnostic proposal to the move actually executed in a forced history. */
void ai_diagnostic_choice(uint8_t army, uint8_t from, uint8_t to);
#endif

#ifdef AI_TEST
#define AI_TEST_STATE_SIZE 208
#ifdef AI_MISSIONS
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE 210
#ifdef AI_MISSION_PROGRESS
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE 218
#endif
#ifdef AI_SECTOR_MEMORY
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE 230
#ifdef AI_MISSION_PROGRESS
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE 238
#endif
#endif
#endif
void ai_test_save(uint8_t* out);
#ifdef AI_MEMORY
#include "ai_memory.h"
#if defined(AI_MISSIONS) && defined(AI_MISSION_PROGRESS) && defined(AI_SECTOR_MEMORY)
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE (238 + AI_MEMORY_STATE_SIZE)
#elif defined(AI_MISSIONS) && defined(AI_MISSION_PROGRESS)
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE (218 + AI_MEMORY_STATE_SIZE)
#elif defined(AI_MISSIONS) && defined(AI_SECTOR_MEMORY)
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE (230 + AI_MEMORY_STATE_SIZE)
#elif defined(AI_MISSIONS)
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE (210 + AI_MEMORY_STATE_SIZE)
#else
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE (208 + AI_MEMORY_STATE_SIZE)
#endif
#endif
void ai_test_load(const uint8_t* in);
#ifdef AI_LINKED_SCOUTING
uint8_t ai_test_linked_information(uint8_t square);
#endif
#ifdef AI_PLAN_CYCLE
/* Two seven-byte public mission-progress records, before the memory snapshot. */
#define AI_PLAN_STATE_SIZE 14
enum { AI_TEST_PRE_PLAN_SIZE = AI_TEST_STATE_SIZE };
#undef AI_TEST_STATE_SIZE
#define AI_TEST_STATE_SIZE (AI_TEST_PRE_PLAN_SIZE + AI_PLAN_STATE_SIZE)
#endif
uint8_t ai_test_quiet(uint8_t army);
#ifdef AI_OCCUPANCY_BELIEFS
int16_t ai_test_expected(uint8_t rank, uint8_t moved);
#endif
#ifdef AI_PURPOSEFUL_PROBES
uint8_t ai_test_discovery(uint8_t square);
#endif
#ifdef AI_LOCAL_EXCHANGES
int16_t ai_test_reply(uint8_t from, uint8_t to);
#endif
#endif

#ifdef AI_TRACE
#ifdef AI_TRAINING
void ai_trace_training(uint8_t from, uint8_t to, int16_t capture_credit);
#endif
/* supplied by a test build: called with the score of every candidate move */
void ai_trace(uint8_t from, uint8_t to, int16_t score);
void ai_trace_plan(uint8_t from, uint8_t goal, uint8_t previous, uint8_t steps, int16_t utility);
#endif

#endif
