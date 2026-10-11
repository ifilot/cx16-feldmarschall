/**************************************************************************
 *                                                                        *
 *   Author: Ivo Filot <ivo@ivofilot.nl>                                  *
 *                                                                        *
 *   CX16-STRATEGO is free software:                                      *
 *   you can redistribute it and/or modify it under the terms of the      *
 *   GNU General Public License as published by the Free Software         *
 *   Foundation, either version 3 of the License, or (at your option)     *
 *   any later version.                                                   *
 *                                                                        *
 *   CX16-STRATEGO is distributed in the hope that it will be useful,     *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty          *
 *   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.              *
 *   See the GNU General Public License for more details.                 *
 *                                                                        *
 *   You should have received a copy of the GNU General Public License    *
 *   along with this program.  If not, see http://www.gnu.org/licenses/.  *
 *                                                                        *
 **************************************************************************/

/*
 * The game's computer player as a native program, for testing and rating.
 *
 * It speaks a line-based protocol on stdin/stdout (see docs/protocol.md).
 * A referee (tools/arena.py) holds the true position; the engine keeps only
 * what its own army may know: its pieces, and the enemy's pieces as
 * PIECE_UNKNOWN until a battle or a long scout move reveals them.
 *
 * Built from the same src/core files as the X16 game; tools/parity.py
 * checks that both builds choose the same moves.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "board.h"
#include "rules.h"
#include "setup.h"
#include "random.h"
#include "ai.h"

static uint8_t own;                         // CELL_BLUE or 0
static int tracing;                         // "think" prints every candidate

void ai_trace(uint8_t from, uint8_t to, int16_t score) {
    if(tracing) printf("candidate %d %d %d\n", from, to, score);
}
static uint8_t enemy_lost[PIECE_TYPES];

static void reply(const char* text) {
    puts(text);
    fflush(stdout);
}

/**
 * @brief Square from its name: a column a-j and a rank 1-10 (rank 1 is Red's back row)
 */
static uint8_t square(const char* name) {
    int col, rank;

    if(!name || name[0] < 'a' || name[0] > 'j') return NOWHERE;
    col = name[0] - 'a';
    rank = atoi(name + 1);
    if(rank < 1 || rank > BOARD_SIZE) return NOWHERE;
    return (BOARD_SIZE - rank) * BOARD_SIZE + col;
}

static void square_name(uint8_t sq, char* out) {
    sprintf(out, "%c%d", 'a' + SQUARE_COL(sq), BOARD_SIZE - SQUARE_ROW(sq));
}

static int type_of(char glyph) {
    const char* p = strchr(piece_glyphs, glyph);
    return glyph && p ? (int)(p - piece_glyphs) : -1;
}

/**
 * @brief The board square of the n-th piece of a deployment string
 *
 * Deployments list an army's front row first, columns a to j.
 */
static uint8_t setup_square(uint8_t blue, uint8_t n) {
    uint8_t row = n / BOARD_SIZE;
    return (blue ? SETUP_ROWS - 1 - row : BOARD_SIZE - SETUP_ROWS + row) * BOARD_SIZE + n % BOARD_SIZE;
}

static void new_game(uint8_t blue) {
    uint8_t n;

    own = blue ? CELL_BLUE : 0;
    board_clear();
    for(n=0; n<ARMY_SIZE; n++) {             // the enemy: 40 unknown pieces
        board[setup_square(!blue, n)] = PIECE_UNKNOWN | (blue ? 0 : CELL_BLUE);
    }
    memset(enemy_lost, 0, sizeof(enemy_lost));
    ai_reset();
    rules_reset();
}

static int place(const char* glyphs) {
    uint8_t n;
    int type;

    if(!glyphs || strlen(glyphs) != ARMY_SIZE) return 0;
    for(n=0; n<ARMY_SIZE; n++) {
        type = type_of(glyphs[n]);
        if(type < 0) return 0;
        board[setup_square(own, n)] = type | own;
    }
    return 1;
}

static void choose_setup(void) {
    char text[ARMY_SIZE + 8];
    uint8_t n;

    setup_random(own != 0);
    strcpy(text, "setup ");
    for(n=0; n<ARMY_SIZE; n++) text[6 + n] = piece_glyphs[PIECE_TYPE(board[setup_square(own, n)])];
    text[6 + ARMY_SIZE] = 0;
    reply(text);
}

static void go(void) {
    char text[24], a[8], b[8];
    uint8_t from, to;

    ai_move(own, enemy_lost, &from, &to);
    if(from == NOWHERE) {
        reply("move none");
        return;
    }
    square_name(from, a);
    square_name(to, b);
    sprintf(text, "move %s %s", a, b);
    reply(text);
}

static void remove_piece(uint8_t sq) {
    uint8_t cell = board[sq];

    if(IS_PIECE(cell) && (cell & CELL_BLUE) != own) enemy_lost[PIECE_TYPE(cell)]++;
    board[sq] = CELL_EMPTY;
}

/**
 * @brief A quiet move by either army; a move over several squares shows a scout
 */
static void moved(uint8_t from, uint8_t to) {
    uint8_t cell = board[from];
    int rows = SQUARE_ROW(from) - SQUARE_ROW(to), cols = SQUARE_COL(from) - SQUARE_COL(to);

    if(rows > 1 || rows < -1 || cols > 1 || cols < -1) {
        cell = (cell & ~CELL_TYPE) | PIECE_SCOUT | CELL_REVEALED;
    }
    board[to] = cell | CELL_MOVED;
    board[from] = CELL_EMPTY;
}

/**
 * @brief A battle by either army: both ranks become known, the losers leave
 */
static void battle(uint8_t from, uint8_t to, int attacker, int defender) {
    uint8_t a = (board[from] & ~CELL_TYPE) | attacker | CELL_REVEALED | CELL_MOVED;
    uint8_t d = (board[to] & ~CELL_TYPE) | defender | CELL_REVEALED;

    board[from] = a;
    board[to] = d;
    switch(rules_battle(attacker, defender)) {
        case BATTLE_ATTACKER:
            remove_piece(to);
            board[to] = a;
            board[from] = CELL_EMPTY;
            break;
        case BATTLE_DEFENDER:
            remove_piece(from);
            break;
        default:
            remove_piece(from);
            remove_piece(to);
    }
}

static int hex(const char* text, uint8_t* out, int n) {
    int i;
    unsigned value;

    if(!text || (int)strlen(text) != 2 * n) return 0;
    for(i=0; i<n; i++) {
        if(sscanf(text + 2 * i, "%2x", &value) != 1) return 0;
        out[i] = value;
    }
    return 1;
}

/**
 * @brief think <army> <seed> <lost: 24 hex digits> <board: 200 hex digits>
 *
 * Choose a move for a raw view, from a fresh state (no previous move);
 * the reply is "best <from> <to>" as square numbers 0-99 (255: none).
 */
static void think(char* args) {
    char text[24];
    char* army = strtok(args, " ");
    char* seed = strtok(NULL, " ");
    char* lost = strtok(NULL, " ");
    char* view = strtok(NULL, " ");
    uint8_t from, to;

    if(!army || !seed || !hex(lost, enemy_lost, PIECE_TYPES) || !hex(view, board, SQUARES)) {
        reply("error think");
        return;
    }
    own = atoi(army) ? CELL_BLUE : 0;
    random_seed(atoi(seed));
    ai_reset();
    rules_reset();
    tracing = getenv("STRATEGO_TRACE") != NULL;
    ai_move(own, enemy_lost, &from, &to);
    tracing = 0;
    sprintf(text, "best %d %d", from, to);
    reply(text);
}

int main(void) {
    char line[512], *command, *args;
    uint8_t from, to;
    int attacker, defender;

    random_seed(1);
    new_game(0);
    while(fgets(line, sizeof(line), stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        command = strtok(line, " ");
        args = strtok(NULL, "");
        if(!command) continue;
        if(!strcmp(command, "stratego")) {
            reply("id name cx16-stratego");
            reply("id author Ivo Filot");
            reply("ok");
        } else if(!strcmp(command, "isready")) {
            reply("readyok");
        } else if(!strcmp(command, "seed")) {
            random_seed(args ? atoi(args) : 1);
        } else if(!strcmp(command, "new")) {
            new_game(args && !strcmp(args, "blue"));
        } else if(!strcmp(command, "setup")) {
            if(args) {
                if(!place(args)) reply("error setup");
            } else {
                choose_setup();
            }
        } else if(!strcmp(command, "go")) {
            go();
        } else if(!strcmp(command, "moved") || !strcmp(command, "battle")) {
            from = square(strtok(args, " "));
            to = square(strtok(NULL, " "));
            if(from == NOWHERE || to == NOWHERE) {
                reply("error squares");
            } else if(command[0] == 'm') {
                rules_record(from, to);
                moved(from, to);
            } else {
                args = strtok(NULL, " ");
                attacker = type_of(args ? args[0] : 0);
                args = strtok(NULL, " ");
                defender = type_of(args ? args[0] : 0);
                if(attacker < 0 || defender < 0) {
                    reply("error ranks");
                } else {
                    rules_record(from, to);
                    battle(from, to, attacker, defender);
                }
            }
        } else if(!strcmp(command, "think")) {
            think(args);
        } else if(!strcmp(command, "quit")) {
            break;
        } else {
            reply("error unknown command");
        }
    }
    return 0;
}
