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

#include <string.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "play.h"
#include "scene.h"
#include "board.h"
#include "rules.h"
#include "setup.h"
#include "ai.h"
#include "boardview.h"
#include "drag.h"
#include "panel.h"
#include "video.h"

// states of a turn
#define RED_TURN        0           // waiting for the player to pick up a piece
#define RED_DRAG        1           // the player drags a piece
#define BLUE_THINK      2           // a short pause before Blue moves
#define BLUE_SLIDE      3           // Blue's piece slides to its destination
#define BATTLE          4           // both combatants are shown face up
#define FALLING         5           // the loser flies off: Blue's to the tray
#define GAME_OVER       6

#define THINK_FRAMES    20
#define SLIDE_FRAMES    18
#define BATTLE_FRAMES   70
#define FALL_FRAMES     30
#define CLASH           24          // an attacker overlaps the defender this far
#define FALL_ARC        28          // how high a falling piece is thrown
#define BELOW_SCREEN    488         // where Red's fallen pieces drop out of sight

#define NOBODY          0
#define RED_WINS        1
#define BLUE_WINS       2

#define STALE           0xFE        // forces the next mark() to redraw

static uint8_t state, timer, winner;
static uint8_t blue;                // Blue is to move
static uint16_t turn;
static uint8_t move_from, move_to;
static uint8_t targets[MAX_TARGETS], target_count;
static uint8_t marked;
static const char* reason;
static char line[40];
static int16_t clash_x, clash_y;    // where the attacker stands in a battle

/* a piece that lost a battle, on its way off the board */
typedef struct {
    uint8_t sprite;                 // SPRITE_DRAG or SPRITE_FALL
    uint8_t cell;
    uint8_t slot;                   // its tray compartment, or NOWHERE for Red
    int16_t x0, y0, x1, y1;
} flight_t;

static flight_t flights[2];
static uint8_t flight_count;

static uint8_t truth[SQUARES];      // the board, while Blue looks at its view
static uint8_t red_lost[PIECE_TYPES];

/**
 * @brief Let Blue choose a move from what Blue knows
 *
 * Red's pieces that Blue has not seen become PIECE_UNKNOWN for the length
 * of the call; Red's captured pieces are public knowledge.
 */
static void blue_think(void) {
    uint8_t sq, cell, type;

    for(type=0; type<PIECE_TYPES; type++) red_lost[type] = piece_counts[type] - board_count(type, 0);
    memcpy(truth, board, SQUARES);
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell) && !(cell & (CELL_BLUE | CELL_REVEALED))) {
            board[sq] = (cell & ~CELL_TYPE) | PIECE_UNKNOWN;
        }
    }
    ai_move(CELL_BLUE, red_lost, &move_from, &move_to);
    memcpy(board, truth, SQUARES);
}

static void mark(uint8_t sq) {
    if(sq == marked) return;
    marked = sq;
    if(sq == NOWHERE) video_cursor_hide();
    else video_cursor(view_x(sq), view_y(sq));
}

static void show_turn(void) {
    strcpy(line, "TURN ");
    strcat(line, panel_number(turn));
    if(blue) panel_info("BLUE IS THINKING", TEXT_DEEP_BLUE, line);
    else panel_info("RED TO MOVE", TEXT_DEEP_RED, line);
}

/**
 * @brief Whether a red piece stands on sq and can move
 */
static uint8_t red_movable(uint8_t sq) {
    if(sq == NOWHERE || !IS_PIECE(board[sq]) || (board[sq] & CELL_BLUE)) return 0;
    return rules_targets(sq, targets) != 0;
}

static uint8_t is_target(uint8_t sq) {
    uint8_t i;

    for(i=0; i<target_count; i++) {
        if(targets[i] == sq) return 1;
    }
    return 0;
}

static void clear_markers(void) {
    uint8_t i;

    for(i=0; i<target_count; i++) view_square(targets[i]);
    target_count = 0;
}

static void battle_text(uint8_t a, uint8_t d, uint8_t outcome) {
    if(d == PIECE_FLAG) {
        strcpy(line, piece_names[a]);
        strcat(line, " CAPTURES THE FLAG");
    } else if(d == PIECE_BOMB) {
        if(outcome == BATTLE_ATTACKER) {
            strcpy(line, "MINER DEFUSES A BOMB");
        } else {
            strcpy(line, piece_names[a]);
            strcat(line, " HITS A BOMB");
        }
    } else {
        strcpy(line, piece_names[a]);
        strcat(line, outcome == BATTLE_ATTACKER ? " DEFEATS " :
                     outcome == BATTLE_DEFENDER ? " FALLS TO " : " AND ");
        strcat(line, piece_names[d]);
        if(outcome == BATTLE_BOTH) strcat(line, " FALL");
    }
}

static void game_over(void) {
    state = GAME_OVER;
    mark(NOWHERE);
    view_show_all = 1;              // Blue's army turns face up
    view_board();
    strcpy(line, "TURN ");
    strcat(line, panel_number(turn));
    if(winner == RED_WINS) panel_info("RED WINS", TEXT_DEEP_RED, line);
    else panel_info("BLUE WINS", TEXT_DEEP_BLUE, line);
    panel_clear_selected();
    panel_bar(reason, "RETURN: PLAY AGAIN   ESCAPE: MENU");
}

static void next_turn(void) {
    if(winner != NOBODY) {
        game_over();
        return;
    }
    blue ^= 1;
    if(!blue) turn++;
    if(!rules_has_move(blue)) {
        winner = blue ? RED_WINS : BLUE_WINS;
        reason = blue ? "BLUE HAS NO MOVES LEFT" : "YOU HAVE NO MOVES LEFT";
        game_over();
        return;
    }
    show_turn();
    if(blue) {
        state = BLUE_THINK;
        timer = THINK_FRAMES;
        mark(NOWHERE);
    } else {
        state = RED_TURN;
        marked = STALE;
    }
}

/**
 * @brief Send a losing piece off the board, starting at (x, y)
 *
 * A blue piece flies to its compartment in the tray; a red one is thrown
 * up and drops below the screen.
 */
static void fall(uint8_t sprite, uint8_t cell, int16_t x, int16_t y) {
    flight_t* f = &flights[flight_count++];

    f->sprite = sprite;
    f->cell = cell;
    f->x0 = x;
    f->y0 = y;
    if(cell & CELL_BLUE) {
        f->slot = panel_tray_home(cell);
        f->x1 = panel_slot_x(f->slot);
        f->y1 = panel_slot_y(f->slot);
    } else {
        f->slot = NOWHERE;
        f->x1 = x;
        f->y1 = BELOW_SCREEN;
    }
    video_sprite_token(sprite, PIECE_TYPE(cell), (cell & CELL_BLUE) ? ARMY_BLUE : ARMY_RED);
    video_sprite_move(sprite, x, y);
}

/**
 * @brief Move the fallen pieces along their arcs; land them when done
 */
static void falling(void) {
    flight_t* f;
    uint8_t i;
    int16_t t = ++timer, x, y;

    for(i=0; i<flight_count; i++) {
        f = &flights[i];
        x = f->x0 + (f->x1 - f->x0) * t / FALL_FRAMES;
        y = f->y0 + (f->y1 - f->y0) * t / FALL_FRAMES;
        y -= FALL_ARC * 4 * t * (FALL_FRAMES - t) / (FALL_FRAMES * FALL_FRAMES);
        video_sprite_move(f->sprite, x, y);
    }
    if(timer < FALL_FRAMES) return;
    for(i=0; i<flight_count; i++) {
        f = &flights[i];
        video_sprite_hide(f->sprite);
        if(f->slot != NOWHERE) {
            tray[f->slot] = PIECE_TYPE(f->cell) | CELL_BLUE;
            panel_tray_slot(f->slot);
        }
    }
    next_turn();
}

/**
 * @brief Carry out the move from move_from to move_to on the board
 *
 * After a battle the winner takes or keeps its square, and the losers
 * fall: the attacker from where it stands, the defender from its square.
 */
static void complete(void) {
    uint8_t a = board[move_from], d = board[move_to];
    int8_t rows, cols;

    rules_record(move_from, move_to);

    if(d == CELL_EMPTY) {
        rows = SQUARE_ROW(move_from) - SQUARE_ROW(move_to);
        cols = SQUARE_COL(move_from) - SQUARE_COL(move_to);
        if(rows > 1 || rows < -1 || cols > 1 || cols < -1) a |= CELL_REVEALED;  // only a scout goes further
        board[move_to] = a | CELL_MOVED;
        board[move_from] = CELL_EMPTY;
        drag_end();
        view_square(move_from);
        view_square(move_to);
        next_turn();
        return;
    }
    if(PIECE_TYPE(d) == PIECE_FLAG) {
        winner = (a & CELL_BLUE) ? BLUE_WINS : RED_WINS;
        reason = winner == RED_WINS ? "YOU CAPTURED THE BLUE FLAG" : "BLUE CAPTURED YOUR FLAG";
    }
    flight_count = 0;
    switch(rules_battle(PIECE_TYPE(a), PIECE_TYPE(d))) {
        case BATTLE_ATTACKER:
            board[move_to] = a | CELL_MOVED;
            board[move_from] = CELL_EMPTY;
            drag_end();
            fall(SPRITE_FALL, d, view_x(move_to), view_y(move_to));
            break;
        case BATTLE_DEFENDER:
            board[move_from] = CELL_EMPTY;
            fall(SPRITE_DRAG, a, clash_x, clash_y);
            break;
        default:
            board[move_from] = board[move_to] = CELL_EMPTY;
            fall(SPRITE_DRAG, a, clash_x, clash_y);
            fall(SPRITE_FALL, d, view_x(move_to), view_y(move_to));
    }
    view_square(move_from);
    view_square(move_to);
    state = FALLING;
    timer = 0;
}

/**
 * @brief Offset of an attacker from the defender along one axis
 */
static int16_t clash(uint8_t from, uint8_t to) {
    if(from < to) return -CLASH;
    if(from > to) return CLASH;
    return 0;
}

/**
 * @brief Start the move of the lifted piece on move_from to `to`
 *
 * A quiet move completes at once. An attack reveals both pieces: the
 * attacker stands against the defender while the message bar tells the
 * outcome.
 */
static void start_move(uint8_t to) {
    uint8_t a, d, outcome;

    move_to = to;
    mark(NOWHERE);
    if(board[to] == CELL_EMPTY) {
        complete();
        return;
    }
    board[move_from] |= CELL_REVEALED;
    board[to] |= CELL_REVEALED;
    a = board[move_from];
    d = board[to];
    // the attacker, face up, stands against the defender on its side
    clash_x = view_x(to) + clash(SQUARE_COL(move_from), SQUARE_COL(to));
    clash_y = view_y(to) + clash(SQUARE_ROW(move_from), SQUARE_ROW(to));
    video_sprite_token(SPRITE_DRAG, PIECE_TYPE(a), (a & CELL_BLUE) ? ARMY_BLUE : ARMY_RED);
    drag_place(clash_x, clash_y);
    view_square_open(to);
    outcome = rules_battle(PIECE_TYPE(a), PIECE_TYPE(d));
    battle_text(PIECE_TYPE(a), PIECE_TYPE(d), outcome);
    if(a & CELL_BLUE) panel_battle("BLUE ATTACKS", PIECE_TYPE(d), PIECE_TYPE(a), line);
    else panel_battle("RED ATTACKS", PIECE_TYPE(a), PIECE_TYPE(d), line);
    state = BATTLE;
    timer = BATTLE_FRAMES;
}

static void red_turn(void) {
    uint8_t i, sq = view_at(input.x, input.y);

    if(sq != marked) {
        mark(red_movable(sq) ? sq : NOWHERE);   // brackets only on pieces that can move
        marked = sq;                            // but name whatever is under the pointer
        panel_selected(sq == NOWHERE ? CELL_EMPTY : board[sq]);
    }
    if((input.pressed & BUTTON_LEFT) && red_movable(sq)) {
        target_count = rules_targets(sq, targets);
        for(i=0; i<target_count; i++) {
            if(board[targets[i]] == CELL_EMPTY) view_marker(targets[i]);
        }
        move_from = sq;
        view_empty(move_from);
        drag_begin(view_token(board[move_from]), ARMY_RED,
                   view_x(move_from), view_y(move_from), input.x, input.y);
        marked = STALE;
        state = RED_DRAG;
    }
}

static void red_drag(void) {
    uint8_t sq;

    drag_follow(input.x, input.y);
    sq = view_at(drag_cx, drag_cy);
    if(!is_target(sq)) sq = NOWHERE;
    mark(sq);
    if(input.buttons & BUTTON_LEFT) return;
    clear_markers();
    if(sq == NOWHERE) {             // not a legal move: put the piece back
        drag_end();
        view_square(move_from);
        mark(NOWHERE);
        marked = STALE;
        state = RED_TURN;
    } else {
        start_move(sq);
    }
}

static void blue_slide(void) {
    int16_t x0 = view_x(move_from), y0 = view_y(move_from);

    timer++;
    drag_place(x0 + (view_x(move_to) - x0) * (int16_t)timer / SLIDE_FRAMES,
               y0 + (view_y(move_to) - y0) * (int16_t)timer / SLIDE_FRAMES);
    if(timer == SLIDE_FRAMES) start_move(move_to);
}

void play_enter(void) {
    board_clear();
    setup_random(1);
    if(setup_complete()) setup_load();
    else setup_random(0);
    view_show_all = 0;
    view_board();
    panel_tray_fallen(1);
    panel_tray_draw();
    panel_bar("YOUR MOVE: DRAG ONE OF YOUR PIECES", "ESCAPE: MENU");
    panel_selected(CELL_EMPTY);
    winner = NOBODY;
    target_count = 0;
    ai_reset();
    rules_reset();
    turn = 1;
    blue = 0;
    marked = STALE;
    state = RED_TURN;
    show_turn();
}

uint8_t play_update(void) {
    if(input.key == KEY_ESCAPE) return SCENE_MENU;
    switch(state) {
        case RED_TURN:
            red_turn();
            break;
        case RED_DRAG:
            red_drag();
            break;
        case BLUE_THINK:
            if(--timer == 0) {
                blue_think();
                view_empty(move_from);
                drag_begin(view_token(board[move_from]), ARMY_BLUE,
                           view_x(move_from), view_y(move_from), 0, 0);
                state = BLUE_SLIDE;
            }
            break;
        case BLUE_SLIDE:
            blue_slide();
            break;
        case BATTLE:
            if(--timer == 0) complete();
            break;
        case FALLING:
            falling();
            break;
        default:
            if(input.key == KEY_RETURN) return SCENE_PLAY;
    }
    return SCENE_STAY;
}
