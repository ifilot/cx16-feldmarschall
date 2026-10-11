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

#include <string.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "deploy_dialog.h"
#include "scene.h"
#include "board.h"
#include "presets.h"
#include "boardview.h"
#include "button.h"
#include "dialog.h"
#include "panel.h"
#include "video.h"

// the plate covers Blue's half of the board, so Red's rows stay in view
#define PLATE_COL       3
#define PLATE_ROW       3
#define PLATE_W         48
#define PLATE_H         28
#define TITLE_ROW       (PLATE_ROW + 2)

// the load list: built-in deployments left, the player's right
#define LIST_HEAD_ROW   (PLATE_ROW + 4)
#define LIST_ROW0       (PLATE_ROW + 6)
#define LIST_PITCH      2
#define LIST_LEFT       (PLATE_COL + 4)     // text column; the marker is two to the left
#define LIST_RIGHT      (PLATE_COL + 28)
#define ENTRIES         (PRESETS + STORE_SLOTS)

// the save dialog: a name field, two columns of five slots and two buttons
#define NAME_ROW        (PLATE_ROW + 5)
#define NAME_COL        (PLATE_COL + 10)
#define SLOT_HEAD_ROW   (PLATE_ROW + 8)
#define SLOT_ROW0       (PLATE_ROW + 10)
#define SLOT_ROWS       5
#define BUTTON_ROW      (PLATE_ROW + 21)
#define SAVE_COL        (PLATE_COL + 14)
#define CANCEL_COL      (SAVE_COL + 10)

#define KEY_DELETE      0x14
#define KEY_LEFT        0x9D
#define KEY_RIGHT       0x1D

char deployment_name[NAME_LENGTH + 1];
uint8_t deployment_slot = NOWHERE;
uint8_t dialog_saved;

static uint8_t saving;              // the save dialog, rather than the list
static uint8_t choice;              // highlighted entry or slot, or NOWHERE
static uint8_t hover_button;
static uint8_t original[ARMY_SIZE]; // Red's rows when the list opened
static char name[NAME_LENGTH + 1];
static char line[24];

/* ------------------------------------------------------------ shared */

static uint8_t inside_plate(int16_t x, int16_t y) {
    return x >= PLATE_COL * 8 && x < (PLATE_COL + PLATE_W) * 8 &&
           y >= PLATE_ROW * 8 && y < (PLATE_ROW + PLATE_H) * 8;
}

/**
 * @brief Index of the entry under the pointer in a two-column list
 *
 * @param rows entries per column
 */
static uint8_t entry_at(uint8_t row0, uint8_t rows, uint8_t left, uint8_t right) {
    int16_t x = input.x, y = input.y, top;
    uint8_t i, column;

    if(x >= (left - 2) * 8 && x < (right - 2) * 8) column = 0;
    else if(x >= (right - 2) * 8 && x < (PLATE_COL + PLATE_W - 1) * 8) column = 1;
    else return NOWHERE;
    for(i=0; i<rows; i++) {
        top = (row0 + i * LIST_PITCH) * 8;
        if(y >= top - 4 && y < top + 12) return column * rows + i;
    }
    return NOWHERE;
}

/**
 * @brief Draw one list line: a marker, then the text in ink or deep red
 */
static void entry(uint8_t col, uint8_t row, const char* text, uint8_t chosen, uint8_t dim) {
    video_text_plate(col - 2, row, chosen ? ">" : " ", TEXT_DEEP_RED);
    video_text_plate(col, row, "                   ", TEXT_INK);
    video_text_plate(col, row, text, dim ? TEXT_BROWN : chosen ? TEXT_DEEP_RED : TEXT_INK);
}

static void plate(const char* title) {
    dialog_plate(PLATE_COL, PLATE_ROW, PLATE_W, PLATE_H);
    dialog_centred(PLATE_COL, PLATE_W, TITLE_ROW, title, TEXT_BROWN);
}

static void show_red_rows(void) {
    uint8_t sq;

    for(sq=RED_HOME0; sq<SQUARES; sq++) view_square(sq);
    panel_tray_reserve();
    panel_tray_draw();
}

/* ------------------------------------------------------------ load */

static void draw_list_entry(uint8_t i) {
    uint8_t col = i < PRESETS ? LIST_LEFT : LIST_RIGHT;
    uint8_t row = LIST_ROW0 + (i % PRESETS) * LIST_PITCH;

    if(i < PRESETS) {
        entry(col, row, preset_names[i], i == choice, 0);
    } else if(store_used(i - PRESETS)) {
        entry(col, row, store_name(i - PRESETS), i == choice, 0);
    } else {
        entry(col, row, "(EMPTY)", 0, 1);
    }
}

static uint8_t list_usable(uint8_t i) {
    return i < PRESETS || store_used(i - PRESETS);
}

/**
 * @brief Highlight an entry and preview its deployment on Red's rows
 */
static void list_choose(uint8_t i) {
    uint8_t old = choice;

    if(i == choice || !list_usable(i)) return;
    choice = i;
    if(old != NOWHERE) draw_list_entry(old);
    draw_list_entry(i);
    if(i < PRESETS) {
        preset_load(i);
        panel_info("PREVIEW", TEXT_DEEP_RED, preset_names[i]);
    } else {
        store_load(i - PRESETS);
        panel_info("PREVIEW", TEXT_DEEP_RED, store_name(i - PRESETS));
    }
    show_red_rows();
}

void dialog_load_open(void) {
    uint8_t i;

    saving = 0;
    choice = NOWHERE;
    memcpy(original, board + RED_HOME0, ARMY_SIZE);
    plate("LOAD A DEPLOYMENT");
    video_text_plate(LIST_LEFT, LIST_HEAD_ROW, "CLASSIC", TEXT_BROWN);
    video_text_plate(LIST_RIGHT, LIST_HEAD_ROW, "YOURS", TEXT_BROWN);
    for(i=0; i<ENTRIES; i++) draw_list_entry(i);
    panel_bar("POINT AT A DEPLOYMENT TO TRY IT, CLICK TO TAKE IT",
              "ESCAPE OR A CLICK OUTSIDE: CANCEL");
}

static uint8_t list_update(void) {
    uint8_t i = entry_at(LIST_ROW0, PRESETS, LIST_LEFT, LIST_RIGHT);

    if(i != NOWHERE) list_choose(i);
    if(input.pressed & BUTTON_LEFT) {
        if(i != NOWHERE && list_usable(i)) input.key = KEY_RETURN;
        else if(!inside_plate(input.x, input.y)) input.key = KEY_ESCAPE;
    }
    switch(input.key) {
        case KEY_RETURN:
            if(choice == NOWHERE) break;
            if(choice < PRESETS) {
                strcpy(deployment_name, preset_names[choice]);
                deployment_slot = NOWHERE;
            } else {
                strcpy(deployment_name, store_name(choice - PRESETS));
                deployment_slot = choice - PRESETS;
            }
            return DIALOG_DONE;
        case KEY_ESCAPE:
            memcpy(board + RED_HOME0, original, ARMY_SIZE);
            show_red_rows();
            return DIALOG_CANCELLED;
        case KEY_UP:
            i = choice == NOWHERE ? 0 : choice;
            do { i = (i % PRESETS) ? i - 1 : i + PRESETS - 1; } while(!list_usable(i));
            list_choose(i);
            break;
        case KEY_DOWN:
            i = choice == NOWHERE ? PRESETS - 1 : choice;
            do { i = (i % PRESETS == PRESETS - 1) ? i + 1 - PRESETS : i + 1; } while(!list_usable(i));
            list_choose(i);
            break;
        case KEY_LEFT:
        case KEY_RIGHT:
            if(choice != NOWHERE && list_usable((choice + PRESETS) % ENTRIES)) {
                list_choose((choice + PRESETS) % ENTRIES);
            }
            break;
    }
    return DIALOG_OPEN;
}

/* ------------------------------------------------------------ save */

static void draw_name(void) {
    uint8_t n = strlen(name);

    memcpy(line, name, n);
    line[n] = '_';                              // the cursor
    memset(line + n + 1, ' ', NAME_LENGTH - n);
    line[NAME_LENGTH + 1] = 0;
    video_text_plate(NAME_COL, NAME_ROW, line, TEXT_DEEP_RED);
}

static void draw_slot(uint8_t slot) {
    uint8_t col = slot < SLOT_ROWS ? LIST_LEFT : LIST_RIGHT;
    uint8_t row = SLOT_ROW0 + (slot % SLOT_ROWS) * LIST_PITCH;

    line[0] = slot == 9 ? '1' : ' ';
    line[1] = slot == 9 ? '0' : '1' + slot;
    line[2] = ' ';
    if(store_used(slot)) strcpy(line + 3, store_name(slot));
    else strcpy(line + 3, "(EMPTY)");
    entry(col, row, line, slot == choice, 0);
}

static void draw_save_buttons(void) {
    button_draw(SAVE_COL, BUTTON_ROW, "SAVE", hover_button == 0 ? BUTTON_HOVER : BUTTON_NORMAL);
    button_draw(CANCEL_COL, BUTTON_ROW, "CANCEL", hover_button == 1 ? BUTTON_HOVER : BUTTON_NORMAL);
}

static void slot_choose(uint8_t slot) {
    uint8_t old = choice;

    if(slot == choice) return;
    choice = slot;
    draw_slot(old);
    draw_slot(slot);
}

void dialog_save_open(void) {
    uint8_t slot;

    saving = 1;
    hover_button = NOWHERE;
    strcpy(name, deployment_name);
    // the slot this deployment came from, else the first free one
    choice = deployment_slot;
    for(slot=0; choice == NOWHERE && slot<STORE_SLOTS; slot++) {
        if(!store_used(slot)) choice = slot;
    }
    if(choice == NOWHERE) choice = 0;
    plate("SAVE THIS DEPLOYMENT");
    video_text_plate(LIST_LEFT, NAME_ROW, "NAME", TEXT_BROWN);
    video_text_plate(LIST_LEFT, SLOT_HEAD_ROW, "SLOT", TEXT_BROWN);
    draw_name();
    for(slot=0; slot<STORE_SLOTS; slot++) draw_slot(slot);
    draw_save_buttons();
    panel_bar("TYPE A NAME AND CHOOSE A SLOT", "RETURN: SAVE   ESCAPE: CANCEL");
}

static uint8_t save(void) {
    uint8_t n;

    if(!name[0]) {                              // an unnamed deployment
        strcpy(name, "DEPLOYMENT ");
        n = strlen(name);
        if(choice == 9) name[n++] = '1';
        name[n++] = choice == 9 ? '0' : '1' + choice;
        name[n] = 0;
    }
    store_save(choice, name);
    dialog_saved = store_write();
    strcpy(deployment_name, name);
    deployment_slot = choice;
    return DIALOG_DONE;
}

static uint8_t save_update(void) {
    uint8_t slot, button, n = strlen(name), c = input.key;

    slot = entry_at(SLOT_ROW0, SLOT_ROWS, LIST_LEFT, LIST_RIGHT);
    button = button_hit(SAVE_COL, BUTTON_ROW, "SAVE", input.x, input.y) ? 0 :
             button_hit(CANCEL_COL, BUTTON_ROW, "CANCEL", input.x, input.y) ? 1 : NOWHERE;
    if(button != hover_button) {
        hover_button = button;
        draw_save_buttons();
    }
    if(input.pressed & BUTTON_LEFT) {
        if(slot != NOWHERE) slot_choose(slot);
        else if(button == 0) c = KEY_RETURN;
        else if(button == 1 || !inside_plate(input.x, input.y)) c = KEY_ESCAPE;
    }
    if(c >= 0xC1 && c <= 0xDA) c -= 0x80;           // shifted letters
    if(c == KEY_RETURN) return save();
    if(c == KEY_ESCAPE) return DIALOG_CANCELLED;
    if(c == KEY_DELETE && n) {
        name[n - 1] = 0;
        draw_name();
    } else if(n < NAME_LENGTH && ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
                                  c == ' ' || c == '-')) {
        name[n] = c;
        name[n + 1] = 0;
        draw_name();
    } else if(c == KEY_UP && choice % SLOT_ROWS) {
        slot_choose(choice - 1);
    } else if(c == KEY_DOWN && choice % SLOT_ROWS < SLOT_ROWS - 1) {
        slot_choose(choice + 1);
    } else if(c == KEY_LEFT || c == KEY_RIGHT) {
        slot_choose((choice + SLOT_ROWS) % STORE_SLOTS);
    }
    return DIALOG_OPEN;
}

uint8_t dialog_update(void) {
    return saving ? save_update() : list_update();
}
