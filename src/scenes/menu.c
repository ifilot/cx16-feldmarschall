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
#include "button.h"
#include "panel.h"
#include "play.h"
#include "video.h"
#include "sound.h"

// the plate, in tiles, centred over the board
#define PLATE_W         34
#define PLATE_H         32
#define PLATE_COL       ((BOARD_X + BOARD_SIZE * SQUARE / 2) / 8 - PLATE_W / 2)
#define PLATE_ROW       ((BOARD_Y + BOARD_SIZE * SQUARE / 2) / 8 - PLATE_H / 2)
#define ENTRY_COL       (PLATE_COL + 4)
#define ENTRY_ROW0      (PLATE_ROW + 7)
#define ENTRY_W         (PLATE_W - 8)
#define ENTRY_PITCH     4
#define ENTRIES         6

static const char* const entries[ENTRIES] = {
    "SETUPS",
    "SKIRMISH",
    "LOAD GAME",
    "OPTIONS",
    "ABOUT",
    "DEMO",
};
static const uint8_t scenes[ENTRIES] = {SCENE_DEPLOY, SCENE_GAME_SETTINGS, SCENE_RESUME, SCENE_OPTIONS, SCENE_ABOUT, SCENE_DEMO};

static uint8_t choice, pending = 0xFF, press_timer;

// typing DEV swaps the entries for the developer scenarios (dev.h)
static const char secret[] = "DEV";
static uint8_t typed, dev;
static const char* const* list = entries;
static uint8_t count = ENTRIES;

static void draw_entry(uint8_t i) {
    uint8_t row = ENTRY_ROW0 + i * ENTRY_PITCH;
    button_draw_width(ENTRY_COL, row, ENTRY_W, list[i],
                      i == pending ? BUTTON_PRESSED : i == choice ? BUTTON_HOVER : BUTTON_NORMAL);
    if(i == choice) video_text_plate(ENTRY_COL + 1, row + 1, ">", TEXT_DEEP_RED);
}

static void draw_entries(void) {
    uint8_t i;
    for(i=0; i<count; i++) draw_entry(i);
}

/**
 * @brief The entry under the pointer, or ENTRIES if none
 */
static uint8_t entry_at(int16_t x, int16_t y) {
    uint8_t i;
    int16_t top;

    if(x < ENTRY_COL * 8 || x >= (ENTRY_COL + ENTRY_W) * 8) return count;
    for(i=0; i<count; i++) {
        top = (ENTRY_ROW0 + i * ENTRY_PITCH) * 8;
        if(y >= top && y < top + BUTTON_HEIGHT * 8) return i;
    }
    return count;
}

void menu_enter(void) {
    pending = 0xFF;
    list = dev ? dev_names : entries;
    count = dev ? DEV_SCENARIOS : ENTRIES;
    if(choice >= count) choice = 0;
    board_clear();
    view_board();
    dialog_plate(PLATE_COL, PLATE_ROW, PLATE_W, PLATE_H);
    if(dev) dialog_centred(PLATE_COL + 3, PLATE_W - 6, PLATE_ROW + 3, "DEVELOPER SCENARIOS", TEXT_UI_RED);
    else dialog_title(PLATE_COL + 3, PLATE_ROW + 2, PLATE_W - 6, 0);
    dialog_rule(ENTRY_COL, PLATE_ROW + 5, ENTRY_W);
    draw_entries();
    panel_tray_clear();
    panel_tray_draw();
    panel_clear_selected();
    if(dev) {
        panel_info("DEVELOPER", TEXT_DEEP_RED, "TEST SCENARIOS");
        panel_bar("CHOOSE A SCENARIO", "");
    } else {
        panel_info("", TEXT_DEEP_RED, "");
        panel_bar("CHOOSE AN OPTION", "");
    }
}

/**
 * @brief The scene of an entry; a saved game must be read first
 */
static uint8_t entry_scene(uint8_t entry) {
    sound_sfx(SFX_MENU_SELECT);
    if(dev) return dev_start(entry);
    if(scenes[entry] != SCENE_RESUME || play_load()) return scenes[entry];
    panel_info("NO SAVED GAME", TEXT_DEEP_RED, "SAVE FROM THE GAME MENU");
    sound_sfx(SFX_ERROR);
    return SCENE_STAY;
}

static uint8_t press_entry(uint8_t entry) {
    uint8_t old = choice;
    pending = choice = entry;
    press_timer = 6;
    if(old != choice) draw_entry(old);
    draw_entry(choice);
    return SCENE_STAY;
}

uint8_t menu_update(void) {
    uint8_t hover = entry_at(input.x, input.y), old = choice, key = input.key;

    if(pending != 0xFF) {
        if(--press_timer) return SCENE_STAY;
        hover = pending;
        pending = 0xFF;
        draw_entry(hover);
        return entry_scene(hover);
    }
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
        sound_sfx(SFX_MENU_BACK);
        dev = 0;
        menu_enter();
        return SCENE_STAY;
    }
    if(input.pointer_active && hover < count) {
        if(input.pressed & BUTTON_LEFT) return press_entry(hover);
        choice = hover;
    }
    switch(key) {
        case KEY_RETURN: return press_entry(choice);
        case KEY_UP:     if(choice > 0) choice--; break;
        case KEY_DOWN:   if(choice < count - 1) choice++; break;
    }
    if(key >= '1' && key < '1' + count) return press_entry(key - '1');
    if(choice != old) { sound_sfx(SFX_MENU_MOVE); draw_entry(old); draw_entry(choice); }
    return SCENE_STAY;
}
