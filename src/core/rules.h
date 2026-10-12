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
#include "board.h"

/* Optional Masters rules, all off for a classic game. */
#define RULE_ATTACKER_WINS  0x01
#define RULE_SILENT         0x02
#define RULE_EXPLODING      0x04
#define RULE_MOVING_BOMBS   0x08
#define RULE_MOVING_FLAG    0x10
#define RULE_RESCUE         0x20
extern uint8_t game_rules;
extern uint8_t rules_lost[2][PIECE_TYPES];
extern uint8_t rules_known_lost[2][PIECE_TYPES];
extern uint8_t rules_rescues[2];

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
 * move only when their variants are enabled, and cannot attack. Lakes and
 * pieces block a move; other pieces may attack an enemy.
 * A move that would break the two-squares rule is left out.
 *
 * @param out room for MAX_TARGETS squares
 * @return number of squares in `out`
 */
uint8_t rules_targets(uint8_t sq, uint8_t* out);

/**
 * @brief Reset move history, casualties and rescue limits, preserving options
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
 * The lower rank number wins; ties follow the selected option. A miner defuses a
 * bomb; other attackers die and may also destroy it. The spy defeats the marshal
 * when it attacks, and loses every other battle. Any attacker captures
 * the flag.
 */
uint8_t rules_battle(uint8_t attacker, uint8_t defender);

/* Reveal only information allowed by the selected rules. */
uint8_t rules_reveal_defender(uint8_t attacker);
void rules_reveal_battle(uint8_t from, uint8_t to);

/* Apply a legal move, including captures and rescue identity tracking.
 * Returns a battle outcome, or BATTLE_QUIET. */
#define BATTLE_QUIET 3
uint8_t rules_apply(uint8_t from, uint8_t to);
/* A moving flag has reached the enemy's back row. */
uint8_t rules_flag_arrived(uint8_t sq);
/* Rescue is optional, once per arriving piece and twice per army. */
uint8_t rules_can_rescue(uint8_t sq);
uint8_t rules_rescue(uint8_t sq, uint8_t type, uint8_t destination);

/*
 * Everything the rules keep about a game in progress, for a saved game:
 * the options, casualties, rescues and the two-squares history.
 */
#define RULES_STATE_SIZE    (1 + 4 * PIECE_TYPES + 2 + SQUARES + 6)
void rules_state_save(uint8_t* out);
void rules_state_load(const uint8_t* in);

#endif
