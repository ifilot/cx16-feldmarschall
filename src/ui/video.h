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

#ifndef _VIDEO_H
#define _VIDEO_H

#include <stdint.h>
#include "gfx.h"

// Palette offsets: classic UI 0, armies 1-2, text 3-5, field 6.
#define TEXT_INK            0
#define TEXT_BROWN          3
#define TEXT_DEEP_RED       4
#define TEXT_DEEP_BLUE      5
#define TEXT_UI_RED         8       // fixed classic deep red, independent of armies
#define TEXT_RESULT_GOLD    10
#define TEXT_RESULT_SLATE   11
#define TEXT_RESULT_IVORY   12

// token palettes
#define ARMY_RED            1
#define ARMY_BLUE           2

/**
 * @brief Load all graphics into VRAM and configure both tile layers
 *
 * The display stays blank while loading; call video_show() when the
 * screen has been drawn.
 *
 * @return 1 on success, 0 when a resource could not be loaded
 */
uint8_t video_init(void);

/* Show the sixteen-color tiled startup screen, with no mouse pointer. */
uint8_t video_splash(void);
uint8_t video_field(uint8_t artwork);

uint8_t video_restore_game_tiles(void);
/* Dedicated result backdrop; outcome 1=victory, 2=defeat, 3=draw. */
uint8_t video_result(uint8_t outcome);
uint8_t video_result_restore(void);

/**
 * @brief Load the token artwork (tiles and lifted sprites) whose rank
 *        numbers follow piece_ranking
 */
uint8_t video_ranks(void);

void video_show(void);

void video_clear_layer1(void);

/**
 * @brief Draw a string on layer 1 at a tile position
 */
void video_text(uint8_t col, uint8_t row, const char* s, uint8_t color);

/**
 * @brief Draw a string on a plate (glyphs with the plate's light grey behind)
 */
void video_text_plate(uint8_t col, uint8_t row, const char* s, uint8_t color);

/**
 * @brief Put a single layer-1 tile (palette row 0)
 */
void video_tile(uint8_t col, uint8_t row, uint16_t tile);

/**
 * @brief Put a row of w layer-1 tiles: first, then w-2 middle, then last
 */
void video_tile_row(uint8_t col, uint8_t row, uint8_t w,
                    uint8_t first, uint8_t middle, uint8_t last);

/**
 * @brief Draw a token (5x5 tiles) at a tile position
 *
 * @param piece token number: a piece type, or TOKEN_HIDDEN for its back
 * @param army  ARMY_RED or ARMY_BLUE
 */
void video_token(uint8_t col, uint8_t row, uint8_t piece, uint8_t army);
/* Piece artwork without board grid edges, for the battle panel. */
void video_token_plain(uint8_t col, uint8_t row, uint8_t piece, uint8_t army);

/**
 * @brief Draw the grid of an empty board square (board coordinates)
 */
void video_empty_square(uint8_t bx, uint8_t by);

/**
 * @brief Show a move-target dot in the centre of a board square
 */
void video_marker(uint8_t bx, uint8_t by);

/**
 * @brief Clear a block of layer 1, showing layer 0 underneath
 */
void video_clear_block(uint8_t col, uint8_t row, uint8_t w, uint8_t h);

/**
 * @brief Place the selection brackets around the 40x40 square at (x, y)
 */
void video_cursor(int16_t x, int16_t y);

void video_cursor_hide(void);

/**
 * @brief Show a token lifted off the board, with a shadow, on sprite n
 *        (SPRITE_DRAG or SPRITE_FALL); it stays hidden until moved
 */
void video_sprite_token(uint8_t n, uint8_t piece, uint8_t army);

/**
 * @brief Move a token sprite; (x, y) is its square's top-left corner
 */
void video_sprite_move(uint8_t n, int16_t x, int16_t y);

void video_sprite_hide(uint8_t n);

#endif
