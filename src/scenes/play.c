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
#include "store.h"
#include "boardview.h"
#include "dialog.h"
#include "drag.h"
#include "panel.h"
#include "video.h"
#include "sound.h"
#include "button.h"

/* The gateways in play_bank.s select this bank before every public call. */
#pragma code-name ("PLAYCODE")
#pragma rodata-name ("PLAYRODATA")
#define play_enter play_enter_banked
#define play_demo play_demo_banked
#define play_position play_position_banked
#define play_load play_load_banked
#define play_resume play_resume_banked
#define play_update play_update_banked

#if TRAY_SLOTS != ARMY_SIZE
#error A saved game keeps one tray byte per piece of an army
#endif

// states of a turn
#define RED_TURN        0           // waiting for the player to pick up a piece
#define RED_DRAG        1           // the player drags a piece
#define BLUE_THINK      2           // a short pause before Blue moves
#define BLUE_SLIDE      3           // Blue's piece slides to its destination
#define BATTLE          4           // both combatants are shown face up
#define FALLING         5           // the loser flies off: Blue's to the tray
#define RESCUE          7
#define GAME_OVER       6
#define PAUSED          8           // the game menu covers the board

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
#define DRAWN           3           // neither army can move

#define STALE           0xFE        // forces the next mark() to redraw

// the game menu and the result of a game: a plate centred over the board
#define PAUSE_W         40
#define PAUSE_H         23
#define PAUSE_COL       ((BOARD_X + BOARD_SIZE * SQUARE / 2) / 8 - PAUSE_W / 2)
#define PAUSE_ROW       ((BOARD_Y + BOARD_SIZE * SQUARE / 2) / 8 - 19 / 2)
#define PAUSE_ENTRY_COL (PAUSE_COL + 11)
#define PAUSE_ENTRY_ROW (PAUSE_ROW + 7)
#define PAUSE_PITCH     3
#define PAUSE_ENTRIES   3
#define GAME_MENU_W     34
#define GAME_MENU_H     30
#define GAME_MENU_COL   10
#define GAME_MENU_ROW   12
#define GAME_ENTRY_COL  14
#define GAME_ENTRY_ROW  19
#define GAME_ENTRY_W    26
#define GAME_PITCH      4
#define GAME_STATUS     40
#define PAUSE_STATUS    (PAUSE_ROW + 21)
#define PAUSE_RESUME    0
#define PAUSE_SAVE      1
#define PAUSE_QUIT      2
#define OVER_NEW        0
#define OVER_BOARD      1
#define OVER_MENU       2

static uint8_t state, timer, winner;
static uint8_t demo;                // both armies controlled by the AI
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

static uint8_t truth[SQUARES];      // truth while either AI looks at its view
static uint8_t saved_tray[TRAY_SLOTS];
static uint8_t arrival = NOWHERE, rescue_type;
static void finish_turn(void);

static uint8_t menu_wanted;         // Escape was pressed; open the menu when the turn allows
static uint8_t paused_state, pause_choice, plate_count;
static uint8_t pause_pending = 0xFF, press_timer;
static uint8_t result_shown;        // the result plate covers the board
static uint8_t result_art;          // dedicated illustrated result is loaded
static uint8_t saved[GAME_EXTRA];   // the scene's part of a saved game: tray, turn, side

#pragma rodata-name ("RODATA")
static const char* const pause_entries[PAUSE_ENTRIES + 2] = {
    "RESUME",
    "SAVE GAME",
    "QUIT TO MENU",
    "",
    "",
};
static const uint8_t demo_actions[4] = {0, 3, 4, 2};
static const char* const over_entries[PAUSE_ENTRIES] = {
    "NEW GAME",
    "VIEW THE BOARD",
    "MAIN MENU",
};
#pragma rodata-name ("PLAYRODATA")
static const char* const* entries = pause_entries;

/**
 * @brief Let the computer choose a move from its own knowledge
 *
 * Enemy pieces it has not seen become PIECE_UNKNOWN for the length
 * of the call; only disclosed casualty ranks are passed to the AI.
 */
static void computer_think(void) {

    memcpy(truth, board, SQUARES);
    ai_mask(blue ? CELL_BLUE : 0);
    ai_move(blue ? CELL_BLUE : 0, rules_known_lost[blue ? 0 : 1], &move_from, &move_to);
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
    if(demo) panel_info(blue ? "BLUE COMPUTER" : "RED COMPUTER", blue ? TEXT_DEEP_BLUE : TEXT_DEEP_RED, line);
    else if(blue) panel_info("OPPONENT IS THINKING", TEXT_DEEP_BLUE, line);
    else panel_info("YOUR TURN", TEXT_DEEP_RED, line);
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
    if(d == PIECE_UNKNOWN) {
        strcpy(line, piece_names[a]);
        strcat(line, outcome == BATTLE_ATTACKER ? " DEFEATS THE DEFENDER" :
                     outcome == BATTLE_DEFENDER ? " FALLS TO THE DEFENDER" : " AND THE DEFENDER FALL");
        return;
    }
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

static void move_bar(void) {
    panel_bar(demo ? "DEMO - COMPUTER VS COMPUTER" : "MOVE ONE OF YOUR PIECES", "");
    video_text(2, 58, "[MENU]", TEXT_BROWN);
}

static void result_open(void);
static void result_board(void);

static void game_over(void) {
    state = GAME_OVER;
    sound_result(winner);
    mark(NOWHERE);
    view_show_all = 1;              // Blue's army turns face up
    result_board();
    result_open();
}

/**
 * @brief End the game if the side to move cannot move
 *
 * It loses, unless the other side cannot move either: then it is a draw.
 */
static uint8_t stuck(void) {
    if(rules_has_move(blue)) return 0;
    if(!rules_has_move(!blue)) {
        winner = DRAWN;
        reason = "NEITHER ARMY CAN MOVE";
    } else {
        winner = blue ? RED_WINS : BLUE_WINS;
        reason = demo ? (blue ? "BLUE HAS NO MOVES LEFT" : "RED HAS NO MOVES LEFT") :
                       blue ? "OPPONENT HAS NO MOVES LEFT" : "YOU HAVE NO MOVES LEFT";
    }
    game_over();
    return 1;
}

static void next_turn(void) {
    if(winner != NOBODY) {
        game_over();
        return;
    }
    blue ^= 1;
    if(!blue) turn++;
    if(stuck()) return;
    show_turn();
    if(blue || demo) {
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
        if(game_rules & RULE_SILENT) {
            for(f->slot=0; f->slot<TRAY_SLOTS && tray[f->slot] != CELL_EMPTY; f->slot++);
        } else f->slot = panel_tray_home(cell);
        f->x1 = panel_slot_x(f->slot);
        f->y1 = panel_slot_y(f->slot);
    } else {
        f->slot = NOWHERE;
        f->x1 = x;
        f->y1 = BELOW_SCREEN;
    }
    video_sprite_token(sprite, (!demo && (cell & CELL_BLUE) && !(cell & CELL_REVEALED)) ? TOKEN_HIDDEN : PIECE_TYPE(cell), (cell & CELL_BLUE) ? ARMY_BLUE : ARMY_RED);
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
            tray[f->slot] = ((f->cell & CELL_REVEALED) ? PIECE_TYPE(f->cell) : PIECE_UNKNOWN) | CELL_BLUE;
            panel_tray_slot(f->slot);
        }
    }
    finish_turn();
}

/**
 * @brief Carry out the move from move_from to move_to on the board
 *
 * After a battle the winner takes or keeps its square, and the losers
 * fall: the attacker from where it stands, the defender from its square.
 */
static void complete(void) {
    uint8_t a = board[move_from], d = board[move_to];
    uint8_t outcome = rules_apply(move_from, move_to);

    arrival = (outcome == BATTLE_QUIET || outcome == BATTLE_ATTACKER) ? move_to : NOWHERE;
    if(rules_flag_arrived(move_to)) {
        winner = (a & CELL_BLUE) ? BLUE_WINS : RED_WINS;
        reason = demo ? (winner == RED_WINS ? "RED FLAG REACHED THE BLUE BACK ROW" : "BLUE FLAG REACHED THE RED BACK ROW") :
                        winner == RED_WINS ? "YOUR FLAG REACHED THE ENEMY BACK ROW" : "ENEMY FLAG REACHED YOUR BACK ROW";
    }
    if(outcome == BATTLE_QUIET) {
        sound_sfx(PIECE_TYPE(a) == PIECE_SCOUT &&
                  move_to != move_from+1 && move_from != move_to+1 &&
                  move_to != move_from+10 && move_from != move_to+10 ? SFX_SCOUT :
                  (a & CELL_BLUE) ? SFX_MOVE_CPU : SFX_MOVE);
        drag_end();
        view_square(move_from);
        view_square(move_to);
        finish_turn();
        return;
    }
    if(PIECE_TYPE(d) == PIECE_FLAG) {
        winner = (a & CELL_BLUE) ? BLUE_WINS : RED_WINS;
        reason = demo ? (winner == RED_WINS ? "RED CAPTURED THE BLUE FLAG" : "BLUE CAPTURED THE RED FLAG") :
                        winner == RED_WINS ? "YOU CAPTURED THE ENEMY FLAG" : "OPPONENT CAPTURED YOUR FLAG";
    } else {
        sound_sfx(PIECE_TYPE(d) == PIECE_BOMB ?
                  (PIECE_TYPE(a) == PIECE_MINER ? SFX_DEFUSE : SFX_BOMB) :
                  (PIECE_TYPE(a) == PIECE_SPY && PIECE_TYPE(d) == PIECE_MARSHAL && outcome == BATTLE_ATTACKER) ? SFX_SPY :
                  outcome == BATTLE_BOTH ? SFX_BATTLE_TIE :
                  ((outcome == BATTLE_ATTACKER) != !!(a & CELL_BLUE)) ? SFX_BATTLE_WON : SFX_BATTLE_LOST);
    }
    flight_count = 0;
    switch(outcome) {
        case BATTLE_ATTACKER:
            drag_end();
            fall(SPRITE_FALL, d, view_x(move_to), view_y(move_to));
            break;
        case BATTLE_DEFENDER:
            fall(SPRITE_DRAG, a, clash_x, clash_y);
            break;
        default:
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
 * A quiet move completes at once. An attack reveals allowed ranks: the
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
    rules_reveal_battle(move_from, to);
    sound_sfx(SFX_ATTACK);
    a = board[move_from];
    d = board[to];
    // the attacker, face up, stands against the defender on its side
    clash_x = view_x(to) + clash(SQUARE_COL(move_from), SQUARE_COL(to));
    clash_y = view_y(to) + clash(SQUARE_ROW(move_from), SQUARE_ROW(to));
    video_sprite_token(SPRITE_DRAG, PIECE_TYPE(a), (a & CELL_BLUE) ? ARMY_BLUE : ARMY_RED);
    drag_place(clash_x, clash_y);
    if(demo || !(d & CELL_BLUE) || (d & CELL_REVEALED)) view_square_open(to);
    else view_square(to);
    outcome = rules_battle(PIECE_TYPE(a), PIECE_TYPE(d));
    battle_text(PIECE_TYPE(a), (!demo && (d & CELL_BLUE) && !(d & CELL_REVEALED)) ? PIECE_UNKNOWN : PIECE_TYPE(d), outcome);
    if(a & CELL_BLUE) panel_battle(demo ? "BLUE ATTACKS" : "OPPONENT ATTACKS", PIECE_TYPE(d), PIECE_TYPE(a), line);
    else panel_battle(demo ? "RED ATTACKS" : "YOU ATTACK", PIECE_TYPE(a), (demo || (d & CELL_REVEALED)) ? PIECE_TYPE(d) : TOKEN_HIDDEN, line);
    video_text(2, 58, "[MENU]", TEXT_BROWN);
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
    if(input.pointer_active && (input.pressed & BUTTON_LEFT) && red_movable(sq)) {
        target_count = rules_targets(sq, targets);
        for(i=0; i<target_count; i++) {
            if(board[targets[i]] == CELL_EMPTY) view_marker(targets[i]);
        }
        move_from = sq;
        sound_sfx(SFX_PICKUP);
        view_empty(move_from);
        drag_begin(view_token(board[move_from]), ARMY_RED,
                   view_x(move_from), view_y(move_from), input.x, input.y);
        marked = STALE;
        state = RED_DRAG;
    }
}

/**
 * @brief Return the lifted piece to its square; Red picks again
 */
static void put_back(void) {
    sound_sfx(SFX_CANCEL);
    drag_end();
    view_square(move_from);
    mark(NOWHERE);
    marked = STALE;
    state = RED_TURN;
}

static void red_drag(void) {
    uint8_t sq;

    drag_follow(input.x, input.y);
    sq = view_at(drag_cx, drag_cy);
    if(!is_target(sq)) sq = NOWHERE;
    mark(sq);
    if(input.buttons & BUTTON_LEFT) return;
    clear_markers();
    if(sq == NOWHERE) put_back();   // not a legal move
    else start_move(sq);
}

static void blue_slide(void) {
    int16_t x0 = view_x(move_from), y0 = view_y(move_from);

    timer++;
    drag_place(x0 + (view_x(move_to) - x0) * (int16_t)timer / SLIDE_FRAMES,
               y0 + (view_y(move_to) - y0) * (int16_t)timer / SLIDE_FRAMES);
    if(timer == SLIDE_FRAMES) start_move(move_to);
}

/* Temporarily use the tray for the player's casualties during a rescue. */
static void rescue_close(void) {
    uint8_t sq;
    for(sq=0; sq<SQUARES; sq++) if(board_home(sq, 0)) view_square(sq);
    memcpy(tray, saved_tray, sizeof(saved_tray));
    panel_tray_draw();
    move_bar();
    next_turn();
}

static void rescue_update(void) {
    uint8_t slot, sq, type;
    if(input.key == KEY_RETURN || input.key == KEY_ESCAPE ||
       (input.pointer_active && (input.pressed & BUTTON_LEFT) && button_hit(45, 54, "SKIP", input.x, input.y))) {
        rescue_close(); return;
    }
    type = piece_rank_key(input.key);
    if(type < PIECE_TYPES && rules_lost[0][type]) rescue_type = type;
    if(input.pointer_active && (input.pressed & BUTTON_LEFT)) {
        slot = panel_slot_at(input.x, input.y);
        if(slot != NOWHERE && IS_PIECE(tray[slot]) && PIECE_TYPE(tray[slot]) < PIECE_BOMB) rescue_type = PIECE_TYPE(tray[slot]);
        sq = view_at(input.x, input.y);
        if(rescue_type != NOWHERE && sq != NOWHERE && rules_rescue(arrival, rescue_type, sq)) {
            view_square(sq);
            rescue_close();
            return;
        }
    }
    if(rescue_type != NOWHERE) {
        panel_selected(rescue_type);
        panel_bar("CHOOSE AN EMPTY HOME SQUARE", "SELECT ANOTHER CASUALTY TO CHANGE");
        button_draw(45, 54, "SKIP", BUTTON_NORMAL);
    }
}

static void finish_turn(void) {
    uint8_t type, sq, i, k, known;
    if(winner != NOBODY || arrival == NOWHERE || !rules_can_rescue(arrival)) { next_turn(); return; }
    if(blue || demo) {
        /* Restore the strongest available casualty near the front. */
        for(type=0; type<PIECE_BOMB && !rules_lost[blue][type]; type++);
        for(sq=ARMY_SIZE; sq>0; sq--) {
            k = blue ? sq-1 : SQUARES-sq;
            if(board[k] != CELL_EMPTY) continue;
            known = rules_known_lost[blue][type] != 0;
            if(rules_rescue(arrival, type, k)) {
                for(i=0; blue && i<TRAY_SLOTS; i++) {
                    if(tray[i] == ((known ? type : PIECE_UNKNOWN) | CELL_BLUE)) {
                        tray[i] = CELL_EMPTY;
                        panel_tray_slot(i);
                        break;
                    }
                }
                view_square(k);
                panel_bar(demo ? (blue ? "BLUE RESCUES A CAPTURED PIECE" : "RED RESCUES A CAPTURED PIECE") : "OPPONENT RESCUES A CAPTURED PIECE", "A REINFORCEMENT RETURNS TO THE ENEMY HOME ROWS");
            }
            break;
        }
        next_turn();
        return;
    }
    memcpy(saved_tray, tray, sizeof(saved_tray));
    panel_tray_clear();
    i = 0;
    for(type=0; type<PIECE_TYPES; type++) {
        for(k=0; k<piece_counts[type]; k++) tray[i++] = (type < PIECE_BOMB && k < rules_lost[0][type]) ? type : CELL_EMPTY;
    }
    panel_tray_draw();
    for(sq=RED_HOME0; sq<SQUARES; sq++) if(board[sq] == CELL_EMPTY) view_marker(sq);
    panel_info("RESCUE A PIECE", TEXT_DEEP_RED, "OPTIONAL REINFORCEMENT");
    panel_clear_selected();
    panel_bar("CHOOSE A CASUALTY TO RETURN", "PLACE IT ON AN EMPTY HOME SQUARE");
    button_draw(45, 54, "SKIP", BUTTON_NORMAL);
    rescue_type = NOWHERE;
    state = RESCUE;
}

/* ------------------------------------------------------------ game menu */

#pragma code-name ("CODE")
#pragma rodata-name ("RODATA")
static const char* pause_label(uint8_t i) {
    if(entries == pause_entries) {
        if(demo) i = demo_actions[i];
        if(i == 3) return sound_music_enabled ? "MUSIC ON " : "MUSIC OFF";
        if(i == 4) return sound_effects_enabled ? "SOUND EFFECTS ON " : "SOUND EFFECTS OFF";
    }
    return entries[i];
}

static void pause_draw_entry(uint8_t i) {
    uint8_t row = GAME_ENTRY_ROW + i * GAME_PITCH;
    button_draw_width(GAME_ENTRY_COL, row, GAME_ENTRY_W, pause_label(i),
                      i == pause_pending ? BUTTON_PRESSED : i == pause_choice ? BUTTON_HOVER : BUTTON_NORMAL);
    if(i == pause_choice) video_text_plate(GAME_ENTRY_COL+1, row+1, ">", TEXT_DEEP_RED);
}

/* Keep menu rendering in main RAM; the animated play bank is nearly full. */
static void pause_draw(void) {
    uint8_t i, row;
    if(result_art) {
        for(i=0; i<plate_count; i++) {
            row = 46 + i * PAUSE_PITCH;
            video_text(26, row, i == pause_choice ? ">" : " ", TEXT_RESULT_GOLD);
            video_text(28, row, over_entries[i], i == pause_choice ? TEXT_RESULT_GOLD : TEXT_RESULT_IVORY);
        }
        return;
    }
    if(entries == pause_entries) {
        for(i=0; i<plate_count; i++) pause_draw_entry(i);
        return;
    }
    for(i=0; i<plate_count; i++) {
        row = PAUSE_ENTRY_ROW + i * PAUSE_PITCH;
        video_text_plate(PAUSE_ENTRY_COL - 2, row, i == pause_choice ? ">" : " ", TEXT_DEEP_RED);
        video_text_plate(PAUSE_ENTRY_COL, row, pause_label(i), i == pause_choice ? TEXT_DEEP_RED : TEXT_INK);
    }
}
#pragma code-name ("PLAYCODE")
#pragma rodata-name ("PLAYRODATA")

/**
 * @brief Open the plate with `list` as its entries and `title` on top
 */
#pragma code-name ("CODE")
static void plate_open(const char* const* list, const char* title, uint8_t color) {
    entries = list;
    plate_count = list == pause_entries ? (demo ? 4 : 5) : 3;
    pause_choice = 0;
    if(list == pause_entries) {
        dialog_plate(GAME_MENU_COL, GAME_MENU_ROW, GAME_MENU_W, GAME_MENU_H);
        dialog_title(GAME_MENU_COL, GAME_MENU_ROW+2, GAME_MENU_W, 2);
        dialog_rule(GAME_ENTRY_COL, GAME_MENU_ROW+5, GAME_ENTRY_W);
        pause_draw();
        return;
    }
    dialog_plate(PAUSE_COL, PAUSE_ROW, PAUSE_W, PAUSE_H);
    dialog_centred(PAUSE_COL, PAUSE_W, PAUSE_ROW + 3, title, color);
    pause_draw();
}

/**
 * @brief The entry under the pointer, or PAUSE_ENTRIES if none
 */
#pragma code-name ("PLAYCODE")
static uint8_t pause_entry_at(int16_t x, int16_t y) {
    uint8_t i;
    int16_t top;

    if(result_art) {
        if(x < 200 || x >= 440) return plate_count;
        for(i=0; i<plate_count; i++) {
            top = (46 + i * PAUSE_PITCH) * 8;
            if(y >= top - 8 && y < top + 16) return i;
        }
        return plate_count;
    }
    if(entries == pause_entries) {
        if(x < GAME_ENTRY_COL*8 || x >= (GAME_ENTRY_COL+GAME_ENTRY_W)*8) return plate_count;
        for(i=0; i<plate_count; i++) {
            top = (GAME_ENTRY_ROW + i*GAME_PITCH)*8;
            if(y >= top && y < top+BUTTON_HEIGHT*8) return i;
        }
        return plate_count;
    }
    if(x < PAUSE_COL * 8 || x >= (PAUSE_COL + PAUSE_W) * 8) return plate_count;
    for(i=0; i<plate_count; i++) {
        top = (PAUSE_ENTRY_ROW + i * PAUSE_PITCH) * 8;
        if(y >= top - 8 && y < top + 16) return i;
    }
    return plate_count;
}

/**
 * @brief Open the game menu; the game stands still until it closes
 *
 * Only between turns (Red to pick a piece, or Blue about to think), so a
 * saved game never holds a move half done.
 */
static void pause_open(void) {
    sound_sfx(SFX_DIALOG);
    menu_wanted = 0;
    pause_pending = 0xFF;
    paused_state = state;
    state = PAUSED;
    mark(NOWHERE);
    plate_open(pause_entries, "GAME MENU", TEXT_UI_RED);
    panel_bar("GAME PAUSED", "CHOOSE AN OPTION");
}

static void result_board(void) {
    view_board();
    panel_tray_draw();
    strcpy(line, "TURN ");
    strcat(line, panel_number(turn));
    panel_info(demo ? (winner == RED_WINS ? "RED WINS" : winner == BLUE_WINS ? "BLUE WINS" : "DRAW") :
               winner == RED_WINS ? "YOU WIN" : winner == BLUE_WINS ? "OPPONENT WINS" : "DRAW",
               winner == RED_WINS ? TEXT_DEEP_RED : winner == BLUE_WINS ? TEXT_DEEP_BLUE : TEXT_BROWN, line);
    panel_clear_selected();
}

/* Restore the chosen field and palette before any other scene uses them. */
static void result_restore(void) {
    if(result_art) {
        video_result_restore();
        result_art = 0;
    }
}

/* A black result screen, with native-resolution artwork and live controls. */
static void result_open(void) {
    result_shown = 1;
    plate_count = 3;
    pause_choice = 0;
    result_art = video_result(winner);
    if(result_art) {
        strcpy(line, demo ? (winner == RED_WINS ? "RED WINS - TURN " : winner == BLUE_WINS ? "BLUE WINS - TURN " : "DRAW - TURN ") : "CAMPAIGN ENDED - TURN ");
        strcat(line, panel_number(turn));
        video_text((80 - strlen(line)) / 2, 12, line, TEXT_RESULT_SLATE);
        video_text((80 - strlen(reason)) / 2, 42, reason, TEXT_RESULT_IVORY);
        pause_draw();
        video_show();
        return;
    }
    /* Missing illustration files still leave the original result usable. */
    video_result_restore();
    result_board();
    plate_open(over_entries, winner == RED_WINS ? "VICTORY" : winner == BLUE_WINS ? "DEFEAT" : "DRAW",
               winner == BLUE_WINS ? TEXT_DEEP_BLUE : TEXT_UI_RED);
    dialog_centred(PAUSE_COL, PAUSE_W, PAUSE_ROW + 5, reason, TEXT_INK);
    panel_bar("GAME OVER", "CHOOSE AN OPTION");
    video_show();
}

static void result_close(void) {
    result_shown = 0;
    result_restore();
    result_board();
    panel_bar("REVIEW THE FINAL POSITION", reason);
    button_draw(43, 54, "RESULT", BUTTON_NORMAL);
    video_show();
}

static void pause_close(void) {
    view_board();                   // the plate covered part of the board
    state = paused_state;
    marked = STALE;
    move_bar();
}

static void pause_save(void) {
    if(demo) return;
    memcpy(saved, tray, TRAY_SLOTS);
    saved[TRAY_SLOTS] = (uint8_t)turn;
    saved[TRAY_SLOTS + 1] = turn >> 8;
    saved[TRAY_SLOTS + 2] = blue | 0x40 | (ai_difficulty << 1);
    video_text_plate(GAME_MENU_COL + 1, GAME_STATUS, "                                ", TEXT_INK);
    if(store_game_write(saved)) {
        sound_sfx(SFX_SAVE);
        dialog_centred(GAME_MENU_COL, GAME_MENU_W, GAME_STATUS, "GAME SAVED", TEXT_BROWN);
    } else {
        sound_sfx(SFX_ERROR);
        dialog_centred(GAME_MENU_COL, GAME_MENU_W, GAME_STATUS, "SAVING FAILED: CHECK THE DISK", TEXT_DEEP_RED);
    }
}

/**
 * @brief The entry chosen on the plate this frame, or PAUSE_ENTRIES
 *
 * @param escape the entry that Escape chooses
 */
static uint8_t plate_pick(uint8_t escape) {
    uint8_t hover = pause_entry_at(input.x, input.y), old = pause_choice, pick = plate_count;

    if(input.pointer_active && hover < plate_count) {
        pause_choice = hover;
        if(input.pressed & BUTTON_LEFT) pick = hover;
    }
    switch(input.key) {
        case KEY_ESCAPE: pick = escape; break;
        case KEY_RETURN: pick = pause_choice; break;
        case KEY_UP:     if(pause_choice > 0) pause_choice--; break;
        case KEY_DOWN:   if(pause_choice < plate_count - 1) pause_choice++; break;
    }
    if(input.key >= '1' && input.key < '1' + plate_count) pick = input.key - '1';
    if(pick < plate_count) pause_choice = pick;
    if(pick < plate_count) sound_sfx(input.key == KEY_ESCAPE ? SFX_MENU_BACK : SFX_MENU_SELECT);
    else if(pause_choice != old) sound_sfx(SFX_MENU_MOVE);
    if(pause_choice != old) {
        if(entries == pause_entries) { pause_draw_entry(old); pause_draw_entry(pause_choice); }
        else pause_draw();
    }
    return pick;
}

static uint8_t pause_update(void) {
    uint8_t pick;
    if(pause_pending != 0xFF) {
        if(--press_timer) return SCENE_STAY;
        pick = pause_pending;
        pause_pending = 0xFF;
        pause_draw_entry(pick);
    } else {
        pick = plate_pick(PAUSE_RESUME);
        if(pick >= plate_count) return SCENE_STAY;
        pause_pending = pick;
        press_timer = 4;
        pause_draw_entry(pick);
        return SCENE_STAY;
    }
    if(demo) pick = demo_actions[pick];
    switch(pick) {
        case PAUSE_RESUME: pause_close(); break;
        case PAUSE_SAVE:   pause_save(); break;
        case 3:            sound_toggle_music(); pause_draw_entry(pause_choice); break;
        case 4:            sound_toggle_effects(); pause_draw_entry(pause_choice); break;
        case PAUSE_QUIT:   return SCENE_MENU;
    }
    return SCENE_STAY;
}

static uint8_t over_update(void) {
    uint8_t pick = plate_count;

    if(result_shown) pick = plate_pick(OVER_MENU);
    else if(input.key == ' ' || (input.pressed & BUTTON_LEFT)) result_open();
    else if(input.key == KEY_RETURN) pick = OVER_NEW;
    else if(input.key == KEY_ESCAPE) pick = OVER_MENU;
    switch(pick) {
        case OVER_NEW:   result_restore(); video_show(); return demo ? SCENE_DEMO : SCENE_GAME_SETTINGS;
        case OVER_BOARD: result_close(); break;
        case OVER_MENU:  result_restore(); video_show(); return SCENE_MENU;
    }
    return SCENE_STAY;
}

/* ------------------------------------------------------------ scene */

/**
 * @brief Show the board and start the turn of the side to move
 */
static void begin(void) {
    view_show_all = demo;
    view_board();
    panel_tray_draw();
    move_bar();
    panel_selected(CELL_EMPTY);
    winner = NOBODY;
    arrival = NOWHERE;
    target_count = 0;
    menu_wanted = 0;
    ai_reset();
    marked = STALE;
    if(blue || demo) {
        state = BLUE_THINK;
        timer = THINK_FRAMES;
    } else {
        state = RED_TURN;
    }
    if(!stuck()) show_turn();       // a loaded position may already be over
}

static void new_game(void) {
    board_clear();
    setup_ai(1);
    if(demo) setup_ai(0);
    else setup_load();
    panel_tray_fallen(1);
    rules_reset();
    turn = 1;
    blue = 0;
    begin();
}

void play_enter(void) {
    demo = 0;
    new_game();
}

void play_demo(void) {
    demo = 1;
    new_game();
}

void play_position(uint8_t blue_moves) {
    uint8_t army, type;

    rules_reset();
    for(army=0; army<2; army++) {
        for(type=0; type<PIECE_TYPES; type++) {
            rules_lost[army][type] = rules_known_lost[army][type] = piece_counts[type] - board_count(type, army);
        }
    }
    panel_tray_fallen(1);
    memcpy(saved, tray, TRAY_SLOTS);
    saved[TRAY_SLOTS] = 1;
    saved[TRAY_SLOTS + 1] = 0;
    saved[TRAY_SLOTS + 2] = blue_moves;
}

uint8_t play_load(void) {
    return store_game_read(saved);
}

void play_resume(void) {
    memcpy(tray, saved, TRAY_SLOTS);
    turn = saved[TRAY_SLOTS] | (saved[TRAY_SLOTS + 1] << 8);
    blue = saved[TRAY_SLOTS + 2] & 1;
    demo = (saved[TRAY_SLOTS + 2] & 0x80) != 0;
    ai_difficulty = (saved[TRAY_SLOTS + 2] & 0x40) ? (saved[TRAY_SLOTS + 2] >> 1) & 3 : AI_NORMAL;
    if(ai_difficulty >= AI_LEVELS) ai_difficulty = AI_NORMAL;
    begin();
}

uint8_t play_update(void) {
    if(state == PAUSED) return pause_update();
    if(state == GAME_OVER) return over_update();
    if(input.key == KEY_ESCAPE ||
       (input.pointer_active && (input.pressed & BUTTON_LEFT) &&
        state != RESCUE && input.x >= 8 && input.x < 72 && input.y >= 464 && input.y < 476)) {
        if(state == RED_DRAG) {
            clear_markers();
            put_back();
        }
        if(state != RESCUE) menu_wanted = 1;   // there, Escape skips the rescue
    }
    if(menu_wanted && (state == RED_TURN || state == BLUE_THINK)) {
        pause_open();
        return SCENE_STAY;
    }
    switch(state) {
        case RESCUE:
            rescue_update();
            break;
        case RED_TURN:
            red_turn();
            break;
        case RED_DRAG:
            red_drag();
            break;
        case BLUE_THINK:
            if(--timer == 0) {
                computer_think();
                view_empty(move_from);
                drag_begin(view_token(board[move_from]), blue ? ARMY_BLUE : ARMY_RED,
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
    }
    return SCENE_STAY;
}
