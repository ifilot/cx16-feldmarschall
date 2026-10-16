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

#include "panel.h"
#include "board.h"
#include "boardview.h"
#include "video.h"

#define PLATE_TEXT_COLS (PLATE_COLS - 2)
#define BAR_COLS        52

uint8_t tray[TRAY_SLOTS];

static char buffer[16];

/**
 * @brief Centre a string within the panel's plates, clearing the line first
 */
static void text_centred(uint8_t row, const char* s, uint8_t color) {
    video_clear_block(PLATE_COL0 + 1, row, PLATE_TEXT_COLS, 1);
    video_text(PLATE_COL0 + ((PLATE_COLS - strlen(s)) >> 1), row, s, color);
}

const char* panel_number(uint16_t n) {
    char* p = buffer + sizeof(buffer) - 1;

    *p = 0;
    do {
        *--p = '0' + n % 10;
        n /= 10;
    } while(n);
    return p;
}

void panel_info(const char* status, uint8_t color, const char* detail) {
    text_centred(INFO_ROW0, status, color);
    text_centred(INFO_ROW1, detail, TEXT_INK);
}

void panel_selected(uint8_t cell) {
    uint8_t type = PIECE_TYPE(cell);

    text_centred(INFO_ROW2, "SELECTED", TEXT_BROWN);
    if(!IS_PIECE(cell)) {
        text_centred(INFO_ROW3, "-", TEXT_BROWN);
    } else if(view_token(cell) == TOKEN_HIDDEN) {
        text_centred(INFO_ROW3, "UNKNOWN", TEXT_DEEP_BLUE);
    } else {
        if(type < PIECE_BOMB) {             // "9  SCOUT"; bombs and flags have no rank
            strcpy(buffer, piece_rank(type));
            strcat(buffer, "  ");
            strcat(buffer, piece_names[type]);
        } else {
            strcpy(buffer, piece_names[type]);
        }
        text_centred(INFO_ROW3, buffer, (cell & CELL_BLUE) ? TEXT_DEEP_BLUE : TEXT_DEEP_RED);
    }
}

void panel_clear_selected(void) {
    video_clear_block(PLATE_COL0 + 1, INFO_ROW2, PLATE_TEXT_COLS, 1);
    video_clear_block(PLATE_COL0 + 1, INFO_ROW3, PLATE_TEXT_COLS, 1);
}

void panel_tray_reserve(void) {
    uint8_t type, k, left, i = 0;

    for(type=0; type<PIECE_TYPES; type++) {
        left = piece_counts[type] - board_count(type, 0);
        for(k=0; k<piece_counts[type]; k++) {
            tray[i++] = k < left ? type : CELL_EMPTY;
        }
    }
}

void panel_tray_fallen(uint8_t blue) {
    uint8_t type, k, lost, i = 0;

    for(type=0; type<PIECE_TYPES; type++) {
        lost = piece_counts[type] - board_count(type, blue);
        for(k=0; k<piece_counts[type]; k++) {
            tray[i++] = k < lost ? (type | (blue ? CELL_BLUE : 0)) : CELL_EMPTY;
        }
    }
}

void panel_tray_clear(void) {
    uint8_t i;

    for(i=0; i<TRAY_SLOTS; i++) tray[i] = CELL_EMPTY;
}

void panel_tray_slot(uint8_t i) {
    uint8_t col, row, cell = tray[i];

    col = TRAY_COL0 + (i % TRAY_COLS) * SQUARE_TILES;
    row = TRAY_ROW0 + (i / TRAY_COLS) * SQUARE_TILES;
    if(cell == CELL_EMPTY) {
        video_clear_block(col, row, SQUARE_TILES, SQUARE_TILES);
    } else {                                // fallen pieces are always revealed
        video_token(col, row, PIECE_TYPE(cell), (cell & CELL_BLUE) ? ARMY_BLUE : ARMY_RED);
    }
}

void panel_tray_draw(void) {
    uint8_t i;

    for(i=0; i<TRAY_SLOTS; i++) panel_tray_slot(i);
}

uint8_t panel_tray_take(uint8_t i) {
    uint8_t cell = tray[i];

    tray[i] = CELL_EMPTY;
    panel_tray_slot(i);
    return cell;
}

uint8_t panel_tray_home(uint8_t cell) {
    uint8_t type, i = 0;

    for(type=0; type<PIECE_TYPE(cell); type++) i += piece_counts[type];
    while(tray[i] != CELL_EMPTY) i++;
    return i;
}

void panel_tray_put(uint8_t cell) {
    uint8_t i = panel_tray_home(cell);

    tray[i] = cell;
    panel_tray_slot(i);
}

uint8_t panel_tray_count(void) {
    uint8_t i, n = 0;

    for(i=0; i<TRAY_SLOTS; i++) n += tray[i] != CELL_EMPTY;
    return n;
}

uint8_t panel_slot_at(int16_t x, int16_t y) {
    int16_t col, row;

    if(x < TRAY_X || y < TRAY_Y) return NOWHERE;
    col = (x - TRAY_X) / SQUARE;
    row = (y - TRAY_Y) / SQUARE;
    if(col >= TRAY_COLS || row >= TRAY_ROWS) return NOWHERE;
    return row * TRAY_COLS + col;
}

int16_t panel_slot_x(uint8_t i) {
    return TRAY_X + (i % TRAY_COLS) * SQUARE;
}

int16_t panel_slot_y(uint8_t i) {
    return TRAY_Y + (i / TRAY_COLS) * SQUARE;
}

void panel_bar(const char* line0, const char* line1) {
    video_clear_block(1, BAR_PIECE_ROW, BAR_COLS, SQUARE_TILES);
    video_text(BAR_TEXT_COL, BAR_ROW0, line0, TEXT_BROWN);
    video_text(BAR_TEXT_COL, BAR_ROW1, line1, TEXT_INK);
}

void panel_battle(const char* heading, uint8_t red_piece, uint8_t blue_piece,
                  const char* result) {
    panel_bar(heading, result);
    video_token_plain(BAR_COL_RED, BAR_PIECE_ROW, red_piece, ARMY_RED);
    video_text(BAR_COL_VS, BAR_PIECE_ROW + 2, "VS", TEXT_INK);
    video_token_plain(BAR_COL_BLUE, BAR_PIECE_ROW, blue_piece, ARMY_BLUE);
}
