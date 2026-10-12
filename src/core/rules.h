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

#ifndef _RULES_H
#define _RULES_H

#include <stdint.h>

#define MAX_TARGETS         20      // a scout reaches at most 18 squares

/*
 * The two-squares rule (ISF): a piece may not move more than TWO_SQUARES
 * times in a row between the same two squares, whatever the opponent does;
 * attacks count too. Some box rules allow only three.
 */
#define TWO_SQUARES         5

// battle outcomes
#define BATTLE_ATTACKER     0       // the attacker wins and takes the square
#define BATTLE_DEFENDER     1       // the attacker is removed
#define BATTLE_BOTH         2       // equal ranks: both are removed

/**
 * @brief The squares the piece on `sq` can move to or attack
 *
 * Pieces move one square up, down, left or right; scouts any distance in a
 * straight line, and may strike at the end of that line. Bombs and flags
 * never move. Lakes and pieces block a move; an enemy piece can be attacked.
 * A move that would break the two-squares rule is left out.
 *
 * @param out room for MAX_TARGETS squares
 * @return number of squares in `out`
 */
uint8_t rules_targets(uint8_t sq, uint8_t* out);

/**
 * @brief Forget the moves made so far (at the start of a game)
 */
void rules_reset(void);

/**
 * @brief Note a move for the two-squares rule; call it for every move,
 *        quiet or attack, while the piece still stands on `from`
 */
void rules_record(uint8_t from, uint8_t to);

/**
 * @brief Whether an army has any legal move left
 */
uint8_t rules_has_move(uint8_t blue);

/**
 * @brief Who wins when a piece of one type attacks a piece of another
 *
 * The lower rank number wins and equal ranks both fall. A miner defuses a
 * bomb, which defeats every other attacker. The spy defeats the marshal
 * when it attacks, and loses every other battle. Any attacker captures
 * the flag.
 */
uint8_t rules_battle(uint8_t attacker, uint8_t defender);

#endif
