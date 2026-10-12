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

/*
 * Native tests of src/core/rules.c: the two-squares rule. Run by `make test`.
 */
#include <stdio.h>

#include "board.h"
#include "rules.h"
#include "ai.h"
#include "random.h"

static int failures;

#define CHECK(condition, what) do { \
    if(!(condition)) { printf("FAIL: %s\n", what); failures++; } \
} while(0)

static uint8_t can(uint8_t from, uint8_t to) {
    uint8_t targets[MAX_TARGETS], n = rules_targets(from, targets), i;

    for(i=0; i<n; i++) if(targets[i] == to) return 1;
    return 0;
}

/* make a move on the board, as the game does: record it, then move */
static void move(uint8_t from, uint8_t to) {
    rules_record(from, to);
    board[to] = board[from] | CELL_MOVED;
    board[from] = CELL_EMPTY;
}

#define A4 60
#define A5 50
#define B4 61
#define J10 9
#define J9 19

static void setup(void) {
    board_clear();
    rules_reset();
    board[A4] = PIECE_SERGEANT;
    board[B4] = PIECE_MINER;
    board[J10] = PIECE_SCOUT | CELL_BLUE;
}

static void variants(void) {
    uint8_t mask, a, d, outcome, from, to, i;
    uint8_t lost[PIECE_TYPES] = {0};
    /* Test precedence across all 64 combinations, not only isolated toggles. */
    for(mask=0; mask<64; mask++) {
        game_rules = mask;
        for(a=0; a<PIECE_BOMB; a++) {
            for(d=0; d<PIECE_TYPES; d++) {
                if(d == PIECE_FLAG) outcome = BATTLE_ATTACKER;
                else if(d == PIECE_BOMB) outcome = a == PIECE_MINER ? BATTLE_ATTACKER :
                    (mask & (RULE_EXPLODING | RULE_MOVING_BOMBS)) ? BATTLE_BOTH : BATTLE_DEFENDER;
                else if(a == PIECE_SPY && d == PIECE_MARSHAL) outcome = BATTLE_ATTACKER;
                else if(a == d) outcome = (mask & RULE_ATTACKER_WINS) ? BATTLE_ATTACKER : BATTLE_BOTH;
                else outcome = a < d ? BATTLE_ATTACKER : BATTLE_DEFENDER;
                CHECK(rules_battle(a, d) == outcome, "combined combat options preserve rank and specialist precedence");
            }
        }
    }
    game_rules = RULE_MOVING_BOMBS | RULE_MOVING_FLAG;
    board_clear(); rules_reset();
    board[60] = PIECE_BOMB; board[61] = PIECE_FLAG; board[50] = PIECE_SCOUT | CELL_BLUE;
    CHECK(can(60, 70) && !can(60, 50), "moving bomb moves but cannot attack");
    CHECK(can(61, 51) && !can(61, 60), "moving flag cannot enter an occupied square");
    board[51] = PIECE_SCOUT | CELL_BLUE;
    CHECK(!can(61, 51), "moving flag cannot attack");
    game_rules = 0;
    CHECK(!can(60, 70) && !can(61, 71), "classic bombs and flags remain stationary");

    game_rules = RULE_SILENT;
    board_clear(); rules_reset();
    board[60] = PIECE_MARSHAL; board[50] = PIECE_SERGEANT | CELL_BLUE;
    CHECK(rules_apply(60, 50) == BATTLE_ATTACKER, "silent defense still resolves combat");
    CHECK(rules_lost[1][PIECE_SERGEANT] == 1 && rules_known_lost[1][PIECE_SERGEANT] == 0,
          "a hidden defeated defender does not disclose its casualty rank");
    CHECK(board[50] & CELL_REVEALED, "attacker discloses its rank");
    board[60] = PIECE_SCOUT; board[61] = PIECE_MINER | CELL_BLUE;
    rules_apply(60, 61);
    CHECK(board[61] & CELL_REVEALED, "Scout forces defender disclosure even in silent defense");
    board[70] = PIECE_MINER | CELL_BLUE; board[71] = PIECE_GENERAL;
    rules_apply(70, 71);
    CHECK(!(board[71] & CELL_REVEALED), "computer cannot learn an unrevealed winning defender");
    game_rules = RULE_EXPLODING;
    board[80] = PIECE_GENERAL; board[81] = PIECE_BOMB | CELL_BLUE;
    CHECK(rules_apply(80, 81) == BATTLE_BOTH && board[80] == CELL_EMPTY && board[81] == CELL_EMPTY,
          "exploding bomb removes both actual board pieces");

    game_rules = RULE_RESCUE;
    board_clear(); rules_reset();
    board[10] = PIECE_CAPTAIN; board[11] = PIECE_SCOUT;
    rules_lost[0][PIECE_MARSHAL] = 2; rules_lost[0][PIECE_BOMB] = 1;
    rules_apply(10, 0);
    CHECK(rules_can_rescue(0), "arriving at enemy back row offers rescue");
    CHECK(!rules_rescue(0, PIECE_BOMB, 60), "bomb cannot be rescued");
    CHECK(!rules_rescue(0, PIECE_MARSHAL, 50), "reinforcement must return to home rows");
    board[60] = PIECE_FLAG;
    CHECK(!rules_rescue(0, PIECE_MARSHAL, 60), "rescue cannot overwrite a piece");
    CHECK(rules_rescue(0, PIECE_MARSHAL, 61), "player can choose a captured rank and vacant home square");
    CHECK(PIECE_TYPE(board[61]) == PIECE_MARSHAL && rules_lost[0][PIECE_MARSHAL] == 1,
          "rescue consumes a casualty and restores exactly one piece");
    rules_apply(0, 10); rules_apply(10, 0);
    CHECK(!rules_can_rescue(0), "same surviving piece cannot rescue twice after moving away and back");
    rules_apply(11, 1);
    CHECK(!rules_can_rescue(1), "Scout cannot perform rescue");
    board[2] = PIECE_MINER;
    CHECK(rules_rescue(2, PIECE_MARSHAL, 62), "a second distinct piece can rescue");
    rules_lost[0][PIECE_MARSHAL] = 1; board[3] = PIECE_GENERAL;
    CHECK(!rules_can_rescue(3), "each army has a limit of two rescues");
    board[99] = PIECE_GENERAL | CELL_BLUE; rules_lost[1][PIECE_MINER] = 1;
    CHECK(rules_rescue(99, PIECE_MINER, 30), "computer has independent rescue allowance and mirrored home rows");
    CHECK(board[30] == (PIECE_MINER | CELL_BLUE), "hidden casualty returns without disclosure");
    rules_reset();
    CHECK(rules_rescues[0] == 0 && rules_lost[1][PIECE_MINER] == 0, "new match resets casualties and rescue limits");
    CHECK(game_rules == RULE_RESCUE, "new match preserves chosen rules");

    game_rules = RULE_MOVING_FLAG;
    board_clear(); rules_reset();
    board[10] = PIECE_FLAG; rules_apply(10, 0);
    CHECK(rules_flag_arrived(0), "player flag wins on enemy back row");
    board[89] = PIECE_FLAG | CELL_BLUE; rules_apply(89, 99);
    CHECK(rules_flag_arrived(99), "computer flag wins on player back row");
    game_rules = 0;
    CHECK(!rules_flag_arrived(0), "classic flag cannot win by reaching a row");

    game_rules = RULE_MOVING_FLAG | RULE_MOVING_BOMBS;
    board_clear(); rules_reset(); ai_reset(); random_seed(1);
    board[89] = PIECE_FLAG | CELL_BLUE; board[30] = PIECE_BOMB | CELL_BLUE;
    board[60] = PIECE_FLAG;
    ai_move(CELL_BLUE, lost, &from, &to);
    CHECK(from == 89 && to == 99, "computer recognizes moving-flag immediate victory");
    for(i=0; i<12; i++) lost[i] = 0;
    game_rules = 0;
}

int main(void) {
    uint8_t i, sq;

    // five moves back and forth are fine, the sixth is refused
    setup();
    for(i=0; i<5; i++) {
        sq = i % 2 ? A5 : A4;
        CHECK(can(sq, i % 2 ? A4 : A5), "back-and-forth moves 1-5 are allowed");
        move(sq, i % 2 ? A4 : A5);
        // the opponent's moves do not interrupt the count
        move(i % 2 ? J9 : J10, i % 2 ? J10 : J9);
    }
    CHECK(board[A5] == PIECE_SERGEANT + CELL_MOVED, "the sergeant ended on a5");
    CHECK(!can(A5, A4), "a sixth move back to a4 is refused");
    CHECK(can(A5, 40), "the sergeant may still move on to a6");
    CHECK(!can(J9, J10), "the opponent's scout, which also shuttled five times, is bound too");

    // moving another piece in between starts the count afresh
    setup();
    for(i=0; i<4; i++) move(i % 2 ? A5 : A4, i % 2 ? A4 : A5);
    move(B4, 51);
    move(A4, A5);
    CHECK(can(A5, A4), "another piece's move resets the count");

    // a scout may not shuttle either, but may pass the banned square
    board_clear();
    rules_reset();
    board[A4] = PIECE_SCOUT;
    for(i=0; i<5; i++) move(i % 2 ? 40 : A4, i % 2 ? A4 : 40);
    CHECK(!can(40, A4), "a scout's sixth move back is refused");
    CHECK(can(40, 70), "but it may move past the banned square");

    // attacks count as moves
    board_clear();
    rules_reset();
    board[A4] = PIECE_MARSHAL;
    for(i=0; i<4; i++) move(i % 2 ? A5 : A4, i % 2 ? A4 : A5);
    move(A4, A5);
    board[A4] = PIECE_SCOUT | CELL_BLUE;    // an enemy steps in behind
    CHECK(!can(A5, A4), "attacking back counts as the sixth move");

    variants();
    printf("rules: %s\n", failures ? "FAILED" : "all tests passed");
    return failures != 0;
}
