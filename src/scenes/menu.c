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

#include <ascii_charmap.h>
#pragma static-locals (on)

#include "menu.h"
#include "dev.h"
#include "scene.h"
#include "board.h"
#include "boardview.h"
#include "dialog.h"
#include "panel.h"
#include "play.h"
#include "video.h"

// the plate, in tiles, centred over the board
#define PLATE_W         34
#define PLATE_H         23
#define PLATE_COL       ((BOARD_X + BOARD_SIZE * SQUARE / 2) / 8 - PLATE_W / 2)
#define PLATE_ROW       ((BOARD_Y + BOARD_SIZE * SQUARE / 2) / 8 - PLATE_H / 2)
#define ENTRY_COL       (PLATE_COL + 4)
#define ENTRY_ROW0      (PLATE_ROW + 6)
#define ENTRY_PITCH     3
#define ENTRIES         5

static const char* const entries[ENTRIES] = {
    "1  MANAGE SETUPS",
    "2  PLAY AGAINST THE COMPUTER",
    "3  CONTINUE SAVED GAME",
    "4  OPTIONS",
    "5  ABOUT",
};
static const uint8_t scenes[ENTRIES] = {SCENE_DEPLOY, SCENE_GAME_SETTINGS, SCENE_RESUME, SCENE_OPTIONS, SCENE_ABOUT};

static uint8_t choice;

// typing DEV swaps the entries for the developer scenarios (dev.h)
static const char secret[] = "DEV";
static uint8_t typed, dev;
static const char* const* list = entries;
static uint8_t count = ENTRIES;

static void draw_entries(void) {
    uint8_t i, row;

    for(i=0; i<count; i++) {
        row = ENTRY_ROW0 + i * ENTRY_PITCH;
        video_text_plate(ENTRY_COL - 2, row, i == choice ? ">" : " ", TEXT_DEEP_RED);
        video_text_plate(ENTRY_COL, row, list[i], i == choice ? TEXT_DEEP_RED : TEXT_INK);
    }
}

/**
 * @brief The entry under the pointer, or ENTRIES if none
 */
static uint8_t entry_at(int16_t x, int16_t y) {
    uint8_t i;
    int16_t top;

    if(x < PLATE_COL * 8 || x >= (PLATE_COL + PLATE_W) * 8) return count;
    for(i=0; i<count; i++) {
        top = (ENTRY_ROW0 + i * ENTRY_PITCH) * 8;
        if(y >= top - 8 && y < top + 16) return i;
    }
    return count;
}

void menu_enter(void) {
    list = dev ? dev_names : entries;
    count = dev ? DEV_SCENARIOS : ENTRIES;
    if(choice >= count) choice = 0;
    board_clear();
    view_board();
    dialog_plate(PLATE_COL, PLATE_ROW, PLATE_W, PLATE_H);
    dialog_centred(PLATE_COL, PLATE_W, PLATE_ROW + 3, dev ? "DEVELOPER SCENARIOS" : "MAIN MENU", TEXT_UI_RED);
    draw_entries();
    panel_tray_clear();
    panel_tray_draw();
    panel_clear_selected();
    if(dev) {
        panel_info("DEVELOPER", TEXT_DEEP_RED, "TEST SCENARIOS");
        panel_bar("CLICK A SCENARIO, OR PRESS 1 TO 6", "ESCAPE: MAIN MENU");
    } else {
        panel_info("WELCOME", TEXT_DEEP_RED, "MAIN MENU");
        panel_bar("CLICK AN OPTION, OR PRESS 1 TO 5", "ESCAPE: RETURN TO MENU");
    }
}

/**
 * @brief The scene of an entry; a saved game must be read first
 */
static uint8_t entry_scene(uint8_t entry) {
    if(dev) return dev_start(entry);
    if(scenes[entry] != SCENE_RESUME || play_load()) return scenes[entry];
    panel_info("NO SAVED GAME", TEXT_DEEP_RED, "SAVE FROM THE GAME MENU");
    return SCENE_STAY;
}

uint8_t menu_update(void) {
    uint8_t hover = entry_at(input.x, input.y), old = choice, key = input.key;

    if(key >= 0xC1 && key <= 0xDA) key -= 0x80;    // shifted letters
    if(key == secret[typed]) {
        if(++typed == sizeof(secret) - 1) {
            typed = 0;
            dev ^= 1;
            menu_enter();
            return SCENE_STAY;
        }
    } else if(key) typed = key == secret[0];
    if(key == KEY_ESCAPE && dev) {
        dev = 0;
        menu_enter();
        return SCENE_STAY;
    }
    if(hover < count) {
        choice = hover;
        if(input.pressed & BUTTON_LEFT) return entry_scene(choice);
    }
    switch(key) {
        case KEY_RETURN: return entry_scene(choice);
        case KEY_UP:     if(choice > 0) choice--; break;
        case KEY_DOWN:   if(choice < count - 1) choice++; break;
    }
    if(key >= '1' && key < '1' + count) return entry_scene(key - '1');
    if(choice != old) draw_entries();
    return SCENE_STAY;
}
