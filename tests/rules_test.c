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

    printf("rules: %s\n", failures ? "FAILED" : "all tests passed");
    return failures != 0;
}
