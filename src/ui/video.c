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

#include <cx16.h>
#include <cbm.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "video.h"
#include "colors.h"

#define SPRITE_ATTR     0xFC00      // in VRAM bank 1
#define SPRITE_16X16    0x50        // size byte: height and width codes
#define SPRITE_64X64    0xF0
#define AUTO_INC_1      0x10
#define LAYER_CONFIG    0x62        // 128x64 map, 4 bpp tiles
#define BOARD_COL0      (BOARD_X / 8)
#define BOARD_ROW0      (BOARD_Y / 8)

/**
 * @brief Point data port 0 at an entry of a 128-column map
 */
static void map_address(uint32_t map, uint8_t col, uint8_t row) {
    VERA.control = 0;
    VERA.address = (uint16_t)map + ((uint16_t)row << 8) + (col << 1);
    VERA.address_hi = AUTO_INC_1 | (uint8_t)(map >> 16);
}

static void sprite_image(uint8_t n, uint32_t addr, uint8_t size);
static void sprite_place(uint8_t n, int16_t x, int16_t y, uint8_t z);

/**
 * @brief Load a headerless file straight into VRAM
 */
static uint8_t load_vram(const char* name, uint32_t addr) {
    cbm_k_setnam(name);
    cbm_k_setlfs(0, 8, 2);
    return cbm_k_load(2 + (uint8_t)(addr >> 16), (uint16_t)addr) != 0;
}

uint8_t video_field(uint8_t artwork) {
    uint8_t display, ok;
    VERA.control = 0;
    display = VERA.display.video;
    VERA.display.video &= ~0x10;
    switch(artwork) {
        case 1: ok = load_vram("F1TILES.BIN", VRAM_L0_TILES) && load_vram("F1MAP.BIN", VRAM_L0_MAP); break;
        case 3: ok = load_vram("F3TILES.BIN", VRAM_L0_TILES) && load_vram("F3MAP.BIN", VRAM_L0_MAP); break;
        default: ok = load_vram("L0TILES.BIN", VRAM_L0_TILES) && load_vram("L0MAP.BIN", VRAM_L0_MAP); break;
    }
    VERA.control = 0;
    VERA.display.video = display;
    return ok;
}

/* A dedicated illustrated backdrop; text and controls stay on layer 1. */
uint8_t video_campaign_menu(void) {
    uint8_t display, ok;
    VERA.control = 0;
    display = VERA.display.video;
    VERA.display.video &= ~0x10;
    ok = load_vram("MNTILES.BIN", VRAM_L0_TILES) &&
         load_vram("MNMAP.BIN", VRAM_L0_MAP) &&
         load_vram("MNL1TIL.BIN", VRAM_L1_TILES) &&
         load_vram("MN1MAP.BIN", VRAM_L1_MAP) &&
         load_vram("MNPAL.BIN", VRAM_PALETTE + 7 * 32);
    VERA.control = 0;
    VERA.display.video = display;
    return ok;
}

uint8_t video_restore_game_tiles(void) {
    return load_vram("L1TILES.BIN", VRAM_L1_TILES);
}

/**
 * @brief Enable the KERNAL mouse driver for the 640x480 screen
 *
 * The game may be started from any screen mode, e.g. 40x30 text after a
 * SCREEN command. screen_mode switches the KERNAL to mode 0 first (80x60
 * text on a 640x480 screen) so that its state matches the game's screen;
 * mouse_config then gets the pointer range explicitly, in 8 pixel units.
 * The driver writes its own pointer image to VRAM; the graphics loaded
 * afterwards may overwrite it, so video_init points sprite 0 at our
 * pointer instead.
 */
static void mouse_init(void) {
    asm("lda #0");                  // mode 0: 80x60 text, 640x480
    asm("clc");                     // set the mode
    asm("jsr $FF5F");               // screen_mode
    asm("lda #1");                  // show the pointer
    asm("ldx #80");                 // range: 80 x 60 cells of 8 pixels
    asm("ldy #60");
    asm("jsr $FF68");               // mouse_config
}

uint8_t video_splash(void) {
    mouse_init();
    VERA.control = 0;
    VERA.display.video &= 0x8F;
    VERA.display.hscale = 128;
    VERA.display.vscale = 128;
    VERA.display.border = 0;
    if(!load_vram("SPLASH0.BIN", 0x00000UL) ||
       !load_vram("SPLASH1.BIN", 0x09600UL) ||
       !load_vram("SPLPAL.BIN", VRAM_PALETTE)) return 0;

    VERA.layer0.config = 0x05;      // bitmap mode, 2 bits per pixel
    VERA.layer0.tilebase = 0x01;    // base $00000, 640 pixels per row
    VERA.layer0.hscroll = 0;
    VERA.layer0.vscroll = 0;        // palette offset 0
    VERA.display.video |= 0x10;    // layer 0 only
    return 1;
}

uint8_t video_init(void) {
    mouse_init();
    VERA.control = 0;
    VERA.display.video &= 0x8F;             // all layers off while loading
    VERA.display.hscale = 128;              // 640x480
    VERA.display.vscale = 128;
    VERA.display.border = 0;

    if(!load_vram("L0TILES.BIN", VRAM_L0_TILES) ||
       !load_vram("L0MAP.BIN", VRAM_L0_MAP) ||
       !load_vram("L1TILES.BIN", VRAM_L1_TILES) ||
       !load_vram("SPRITES.BIN", VRAM_SPRITES) ||
       !load_vram("PALETTE.BIN", VRAM_PALETTE)) {
        return 0;
    }

    VERA.layer0.config = LAYER_CONFIG;
    VERA.layer0.mapbase = VRAM_L0_MAP >> 9;
    VERA.layer0.tilebase = VRAM_L0_TILES >> 9;
    VERA.layer0.hscroll = 0;
    VERA.layer0.vscroll = 0;

    VERA.layer1.config = LAYER_CONFIG;
    VERA.layer1.mapbase = VRAM_L1_MAP >> 9;
    VERA.layer1.tilebase = VRAM_L1_TILES >> 9;
    VERA.layer1.hscroll = 0;
    VERA.layer1.vscroll = 0;

    // the KERNAL keeps moving sprite 0; only its image changes
    sprite_image(SPRITE_POINTER, VRAM_POINTER, SPRITE_16X16);
    sprite_image(SPRITE_CURSOR, VRAM_CURSOR, SPRITE_64X64);
    video_cursor_hide();
    video_sprite_hide(SPRITE_DRAG);
    video_sprite_hide(SPRITE_FALL);

    video_clear_layer1();
    return colors_init();
}

void video_show(void) {
    VERA.control = 0;
    VERA.display.video |= 0x70;             // layer 0, layer 1 and sprites
}

void video_clear_layer1(void) {
    map_address(VRAM_L1_MAP, 0, 0);
    /* 64 pages of 256 bytes; VERA auto-increments after every store. */
    asm("lda #0");
    asm("ldx #64");
page:
    asm("ldy #0");
byte:
    asm("sta $9F23");
    asm("iny");
    asm("bne %g", byte);
    asm("dex");
    asm("bne %g", page);
}

static void text(uint8_t col, uint8_t row, const char* s, uint8_t color, uint16_t font) {
    uint16_t tile;
    uint8_t c;

    color <<= 4;
    map_address(VRAM_L1_MAP, col, row);
    while((c = *s++)) {
        if(c < 32 || c > 127) c = ' ';
        tile = font - 32 + c;
        VERA.data0 = (uint8_t)tile;
        VERA.data0 = (uint8_t)(tile >> 8) | color;
    }
}

void video_text(uint8_t col, uint8_t row, const char* s, uint8_t color) {
    text(col, row, s, color, L1_FONT);
}

void video_text_plate(uint8_t col, uint8_t row, const char* s, uint8_t color) {
    text(col, row, s, color, L1_FONT_PLATE);
}

void video_tile_row(uint8_t col, uint8_t row, uint8_t w,
                    uint8_t first, uint8_t middle, uint8_t last) {
    map_address(VRAM_L1_MAP, col, row);
    VERA.data0 = first;
    VERA.data0 = 0;
    for(w -= 2; w; w--) {
        VERA.data0 = middle;
        VERA.data0 = 0;
    }
    VERA.data0 = last;
    VERA.data0 = 0;
}

void video_tile(uint8_t col, uint8_t row, uint16_t tile) {
    map_address(VRAM_L1_MAP, col, row);
    VERA.data0 = (uint8_t)tile;
    VERA.data0 = (uint8_t)(tile >> 8);
}

void video_token(uint8_t col, uint8_t row, uint8_t piece, uint8_t army) {
    uint16_t tile = L1_PIECES + piece * (SQUARE_TILES * SQUARE_TILES);
    uint8_t x, y, attr;

    for(y=0; y<SQUARE_TILES; y++) {
        map_address(VRAM_L1_MAP, col, row + y);
        for(x=0; x<SQUARE_TILES; x++) {
            attr = (uint8_t)(tile >> 8) | (army << 4);
            VERA.data0 = (uint8_t)tile;
            VERA.data0 = attr;
            tile++;
        }
    }
}

void video_empty_square(uint8_t bx, uint8_t by) {
    uint8_t x, y, col = BOARD_COL0 + bx * SQUARE_TILES, row = BOARD_ROW0 + by * SQUARE_TILES;

    map_address(VRAM_L1_MAP, col, row);
    VERA.data0 = L1_GRID_CORNER;
    VERA.data0 = PALETTE_FIELD << 4;
    for(x=1; x<SQUARE_TILES; x++) {
        VERA.data0 = L1_GRID_TOP;
        VERA.data0 = PALETTE_FIELD << 4;
    }
    for(y=1; y<SQUARE_TILES; y++) {
        map_address(VRAM_L1_MAP, col, row + y);
        VERA.data0 = L1_GRID_LEFT;
        VERA.data0 = PALETTE_FIELD << 4;
        for(x=1; x<SQUARE_TILES; x++) {
            VERA.data0 = L1_EMPTY;
            VERA.data0 = 0;
        }
    }
}

void video_marker(uint8_t bx, uint8_t by) {
    map_address(VRAM_L1_MAP, BOARD_COL0 + bx * SQUARE_TILES + SQUARE_TILES / 2,
                BOARD_ROW0 + by * SQUARE_TILES + SQUARE_TILES / 2);
    VERA.data0 = L1_MARKER;
    VERA.data0 = 0;
}

void video_clear_block(uint8_t col, uint8_t row, uint8_t w, uint8_t h) {
    uint8_t x, y;

    for(y=0; y<h; y++) {
        map_address(VRAM_L1_MAP, col, row + y);
        for(x=0; x<w; x++) {
            VERA.data0 = 0;
            VERA.data0 = 0;
        }
    }
}

/**
 * @brief Set a sprite's image: 4 bpp data at addr, size and palette byte
 */
static void sprite_image(uint8_t n, uint32_t addr, uint8_t size) {
    VERA.control = 0;
    VERA.address = SPRITE_ATTR + (n << 3);
    VERA.address_hi = AUTO_INC_1 | 1;
    VERA.data0 = (uint8_t)(addr >> 5);
    VERA.data0 = (uint8_t)(addr >> 13);
    VERA.address = SPRITE_ATTR + (n << 3) + 7;
    VERA.data0 = size;
}

/**
 * @brief Move a sprite; z = 0 hides it, 3 shows it in front of both layers
 */
static void sprite_place(uint8_t n, int16_t x, int16_t y, uint8_t z) {
    VERA.control = 0;
    VERA.address = SPRITE_ATTR + (n << 3) + 2;
    VERA.address_hi = AUTO_INC_1 | 1;
    VERA.data0 = (uint8_t)x;
    VERA.data0 = (uint8_t)(x >> 8) & 3;     // 10-bit coordinates wrap at the left edge
    VERA.data0 = (uint8_t)y;
    VERA.data0 = (uint8_t)(y >> 8) & 3;
    VERA.data0 = z << 2;
}

void video_cursor(int16_t x, int16_t y) {
    sprite_place(SPRITE_CURSOR, x - CURSOR_OFFSET, y - CURSOR_OFFSET, 3);
}

void video_cursor_hide(void) {
    sprite_place(SPRITE_CURSOR, 0, 0, 0);
}

void video_sprite_token(uint8_t n, uint8_t piece, uint8_t army) {
    sprite_image(n, VRAM_TOKEN_SPRITES + ((uint32_t)piece << 11), SPRITE_64X64 | army);
}

void video_sprite_move(uint8_t n, int16_t x, int16_t y) {
    sprite_place(n, x, y, 3);
}

void video_sprite_hide(uint8_t n) {
    sprite_place(n, 0, 0, 0);
}
