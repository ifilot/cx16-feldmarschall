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

#include "deploy.h"
#include "deploy_dialog.h"
#include "scene.h"
#include "board.h"
#include "setup.h"
#include "boardview.h"
#include "button.h"
#include "drag.h"
#include "sound.h"
#include "panel.h"
#include "video.h"

/*
 * A spot is a board square (0-99) or a tray compartment (its index | SPOT_TRAY).
 */
#define SPOT_TRAY       0x80
#define STALE           0xFE        // forces the next mark() to redraw

// the buttons of the message bar
#define BUTTON_NEW      0
#define BUTTON_LOAD     1
#define BUTTON_SAVE     2
#define BUTTON_RANDOM   3
#define BUTTON_START    4
#define BUTTONS         5
#define BUTTON_COL0     2
#define BUTTON_GAP      2

static const char* labels[BUTTONS] = {"NEW", "LOAD", "SAVE", "RANDOM", "START"};
static const uint8_t keys[BUTTONS] = {'N', 'L', 'S', 'R', KEY_RETURN};

static uint8_t in_dialog;          // the button whose dialog is open, or 0
static uint8_t for_play;           // deployment before a match, rather than setup management
static uint8_t held;                // the piece being dragged, or CELL_EMPTY
static uint8_t from;                // the spot it was picked up from
static uint8_t marked;              // the spot the brackets mark
static uint8_t hovered;             // the button under the pointer, or NOWHERE
static char line[24];

/* ------------------------------------------------------------ spots */

static uint8_t spot_at(int16_t x, int16_t y) {
    uint8_t spot = view_at(x, y);

    if(spot != NOWHERE) return spot;
    spot = panel_slot_at(x, y);
    return spot == NOWHERE ? NOWHERE : (spot | SPOT_TRAY);
}

static int16_t spot_x(uint8_t spot) {
    return (spot & SPOT_TRAY) ? panel_slot_x(spot & ~SPOT_TRAY) : view_x(spot);
}

static int16_t spot_y(uint8_t spot) {
    return (spot & SPOT_TRAY) ? panel_slot_y(spot & ~SPOT_TRAY) : view_y(spot);
}

static uint8_t spot_cell(uint8_t spot) {
    return (spot & SPOT_TRAY) ? tray[spot & ~SPOT_TRAY] : board[spot];
}

/**
 * @brief Whether the piece on a spot can be picked up
 */
static uint8_t movable(uint8_t spot) {
    if(spot == NOWHERE || !IS_PIECE(spot_cell(spot))) return 0;
    return (spot & SPOT_TRAY) || board_home(spot, 0);
}

/**
 * @brief Where the held piece would land with its centre at (x, y)
 */
static uint8_t drop_target(int16_t x, int16_t y) {
    uint8_t spot = spot_at(x, y);

    if(spot == NOWHERE) return NOWHERE;
    if(spot & SPOT_TRAY) return SPOT_TRAY | panel_tray_home(held);
    return board_home(spot, 0) ? spot : NOWHERE;
}

static void mark(uint8_t spot) {
    if(spot == marked) return;
    marked = spot;
    if(spot == NOWHERE) video_cursor_hide();
    else video_cursor(spot_x(spot), spot_y(spot));
}

/* ------------------------------------------------------------ panel */

static uint8_t complete(void) {
    return !panel_tray_count();
}

static uint8_t enabled(uint8_t button) {
    if(button == BUTTON_START && !for_play) return 1; // Back never needs a complete army
    return (button != BUTTON_SAVE && button != BUTTON_START) || complete();
}

static uint8_t button_col(uint8_t button) {
    uint8_t i, col = BUTTON_COL0;

    for(i=0; i<button; i++) col += button_width(labels[i]) + BUTTON_GAP;
    return col;
}

static void draw_button(uint8_t button) {
    button_draw(button_col(button), BAR_ROW0, labels[button],
                !enabled(button) ? BUTTON_DISABLED :
                button == hovered ? BUTTON_HOVER : BUTTON_NORMAL);
}

static void draw_buttons(void) {
    uint8_t i;

    panel_bar("", "");
    for(i=0; i<BUTTONS; i++) draw_button(i);
}

static uint8_t button_at(int16_t x, int16_t y) {
    uint8_t i;

    for(i=0; i<BUTTONS; i++) {
        if(button_hit(button_col(i), BAR_ROW0, labels[i], x, y)) return i;
    }
    return NOWHERE;
}

static void status(void) {
    uint8_t n = panel_tray_count();

    if(n) {
        strcpy(line, panel_number(n));
        strcat(line, " TO PLACE");
        panel_info(for_play ? "DEPLOY YOUR ARMY" : "MANAGE SETUPS", TEXT_DEEP_RED, line);
    } else {
        panel_info(for_play ? "READY TO PLAY" : "SETUP COMPLETE", TEXT_DEEP_RED,
                   deployment_name[0] ? deployment_name : "ALL 40 PLACED");
    }
}

/**
 * @brief The deployment changed by hand: it no longer matches a saved one
 */
static void edited(void) {
    deployment_name[0] = 0;
    deployment_slot = NOWHERE;
}

/**
 * @brief Redraw everything after the board changed as a whole
 */
static void show(void) {
    view_board();
    panel_tray_reserve();
    panel_tray_draw();
    status();
    draw_buttons();
    setup_store();
    marked = STALE;
}

/* ------------------------------------------------------------ dragging */

static void pick_up(uint8_t spot) {
    sound_sfx(SFX_PICKUP);
    if(spot & SPOT_TRAY) {
        held = panel_tray_take(spot & ~SPOT_TRAY);
    } else {
        held = board[spot];
        board[spot] = CELL_EMPTY;
        view_square(spot);
    }
    from = spot;
    drag_begin(PIECE_TYPE(held), ARMY_RED, spot_x(spot), spot_y(spot), input.x, input.y);
    panel_selected(held);
}

static void drop(uint8_t target) {
    uint8_t occupant, was_complete = complete();

    sound_sfx(target == NOWHERE || target == from ? SFX_CANCEL :
              target & SPOT_TRAY ? SFX_TRAY : SFX_DROP);
    if(target == NOWHERE) target = from;            // back where it came from
    if(target != from) edited();
    if(target & SPOT_TRAY) {
        panel_tray_put(held);
    } else {
        occupant = board[target];
        board[target] = held;
        view_square(target);
        if(occupant != CELL_EMPTY) {                // swap with the piece there
            if(from & SPOT_TRAY) {
                panel_tray_put(occupant);
            } else {
                board[from] = occupant;
                view_square(from);
            }
        }
    }
    held = CELL_EMPTY;
    drag_end();
    setup_store();
    status();
    if(complete() != was_complete) {                // SAVE and START change
        draw_button(BUTTON_SAVE);
        draw_button(BUTTON_START);
    }
}

/* ------------------------------------------------------------ actions */

static uint8_t act(uint8_t button) {
    if(!enabled(button)) { sound_sfx(SFX_ERROR); return SCENE_STAY; }
    switch(button) {
        case BUTTON_NEW:
            sound_sfx(SFX_MENU_SELECT);
            edited();
            memset(board + RED_HOME0, CELL_EMPTY, ARMY_SIZE);
            show();
            break;
        case BUTTON_RANDOM:
            sound_sfx(SFX_RANDOM);
            edited();
            setup_random(0);
            show();
            break;
        case BUTTON_LOAD:
        case BUTTON_SAVE:
            mark(NOWHERE);
            panel_selected(CELL_EMPTY);
            in_dialog = button;
            if(button == BUTTON_LOAD) dialog_load_open();
            else dialog_save_open();
            break;
        case BUTTON_START:
            return for_play ? SCENE_PLAY : SCENE_MENU;
    }
    return SCENE_STAY;
}

static void close_dialog(uint8_t result) {
    uint8_t saved = in_dialog == BUTTON_SAVE && result == DIALOG_DONE;

    in_dialog = 0;
    hovered = NOWHERE;
    show();                                         // the plate covered Blue's half
    if(saved) {
        if(dialog_saved) panel_info("SETUP SAVED", TEXT_DEEP_RED, deployment_name);
        else panel_info("SAVING FAILED", TEXT_DEEP_RED, "CHECK THE DISK");
    }
}

void deploy_enter(uint8_t playing) {
    for_play = playing;
    labels[BUTTON_START] = for_play ? "START" : "BACK";
    view_show_all = 0;
    board_clear();
    if(for_play) setup_ai(1);       // show the opponent only when preparing a match
    setup_load();                   // and whatever the player deployed before
    store_read();                   // the player's saved deployments
    held = CELL_EMPTY;
    hovered = NOWHERE;
    in_dialog = 0;
    show();
    panel_selected(CELL_EMPTY);
}

uint8_t deploy_update(void) {
    uint8_t spot, button, result, key = input.key;

    if(in_dialog) {
        result = dialog_update();
        if(result != DIALOG_OPEN) close_dialog(result);
        return SCENE_STAY;
    }
    if(held != CELL_EMPTY) {
        drag_follow(input.x, input.y);
        spot = drop_target(drag_cx, drag_cy);
        mark(spot);
        if(!(input.buttons & BUTTON_LEFT)) {
            drop(spot);
            marked = STALE;                         // refresh the hover mark
        }
        return SCENE_STAY;
    }

    if(key == KEY_ESCAPE) {
        sound_sfx(SFX_MENU_BACK);
        return for_play ? SCENE_GAME_SETTINGS : SCENE_MENU;
    }
    if(key >= 0xC1 && key <= 0xDA) key -= 0x80;    // shifted letters
    for(button=0; button<BUTTONS; button++) {
        if(key && key == keys[button]) return act(button);
    }
    button = button_at(input.x, input.y);
    if(button != hovered) {
        spot = hovered;
        hovered = button;
        if(spot != NOWHERE) draw_button(spot);
        if(button != NOWHERE) draw_button(button);
    }
    if(input.pointer_active && (input.pressed & BUTTON_LEFT) && button != NOWHERE) return act(button);

    spot = spot_at(input.x, input.y);
    if(!movable(spot)) spot = NOWHERE;
    if(spot != marked) {
        mark(spot);
        panel_selected(spot == NOWHERE ? CELL_EMPTY : spot_cell(spot));
    }
    if(input.pointer_active && (input.pressed & BUTTON_LEFT) && spot != NOWHERE) pick_up(spot);
    return SCENE_STAY;
}
