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
#include "scene.h"
#include "board.h"
#include "boardview.h"
#include "dialog.h"
#include "panel.h"
#include "video.h"

// the plate, in tiles, centred over the board
#define PLATE_W         34
#define PLATE_H         14
#define PLATE_COL       ((BOARD_X + BOARD_SIZE * SQUARE / 2) / 8 - PLATE_W / 2)
#define PLATE_ROW       ((BOARD_Y + BOARD_SIZE * SQUARE / 2) / 8 - PLATE_H / 2)
#define ENTRY_COL       (PLATE_COL + 4)
#define ENTRY_ROW0      (PLATE_ROW + 6)
#define ENTRY_PITCH     3
#define ENTRIES         2

static const char* const entries[ENTRIES] = {
    "1  DEPLOY YOUR ARMY",
    "2  PLAY AGAINST THE COMPUTER",
};
static const uint8_t scenes[ENTRIES] = {SCENE_DEPLOY, SCENE_PLAY};

static uint8_t choice;

static void draw_entries(void) {
    uint8_t i, row;

    for(i=0; i<ENTRIES; i++) {
        row = ENTRY_ROW0 + i * ENTRY_PITCH;
        video_text_plate(ENTRY_COL - 2, row, i == choice ? ">" : " ", TEXT_DEEP_RED);
        video_text_plate(ENTRY_COL, row, entries[i], i == choice ? TEXT_DEEP_RED : TEXT_INK);
    }
}

/**
 * @brief The entry under the pointer, or ENTRIES if none
 */
static uint8_t entry_at(int16_t x, int16_t y) {
    uint8_t i;
    int16_t top;

    if(x < PLATE_COL * 8 || x >= (PLATE_COL + PLATE_W) * 8) return ENTRIES;
    for(i=0; i<ENTRIES; i++) {
        top = (ENTRY_ROW0 + i * ENTRY_PITCH) * 8;
        if(y >= top - 8 && y < top + 16) return i;
    }
    return ENTRIES;
}

void menu_enter(void) {
    board_clear();
    view_board();
    dialog_plate(PLATE_COL, PLATE_ROW, PLATE_W, PLATE_H);
    dialog_centred(PLATE_COL, PLATE_W, PLATE_ROW + 3, "CHOOSE A SCENE", TEXT_BROWN);
    draw_entries();
    panel_tray_clear();
    panel_tray_draw();
    panel_info("WELCOME", TEXT_DEEP_RED, "MAIN MENU");
    panel_clear_selected();
    panel_bar("CLICK A SCENE, OR PRESS 1 OR 2", "ESCAPE RETURNS HERE FROM ANY SCENE");
}

uint8_t menu_update(void) {
    uint8_t hover = entry_at(input.x, input.y), old = choice;

    if(hover < ENTRIES) {
        choice = hover;
        if(input.pressed & BUTTON_LEFT) return scenes[choice];
    }
    switch(input.key) {
        case '1':        return scenes[0];
        case '2':        return scenes[1];
        case KEY_RETURN: return scenes[choice];
        case KEY_UP:     if(choice > 0) choice--; break;
        case KEY_DOWN:   if(choice < ENTRIES - 1) choice++; break;
    }
    if(choice != old) draw_entries();
    return SCENE_STAY;
}
