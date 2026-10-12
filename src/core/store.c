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

#include <cbm.h>
#include <string.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "store.h"
#include "board.h"
#include "rules.h"

/*
 * DEPLOY.DAT: an 8-byte header, then per slot a name of NAME_LENGTH bytes
 * (zero padded; empty for an unused slot) and the 40 piece types of Red's
 * home rows, front row first, then a 16-bit checksum.
 */
#define MAGIC           "STRDEP01"
#define HEADER          8
#define SLOT_SIZE       (NAME_LENGTH + ARMY_SIZE)
#define BODY            (HEADER + STORE_SLOTS * SLOT_SIZE)
#define FILE_SIZE       (BODY + 2)
#define CHANNEL         3

/*
 * GAME.DAT: an 8-byte header, the board, the rules' state, the play
 * scene's bytes, then a 16-bit checksum.
 */
#define GAME_MAGIC      "STRGAM01"
#define GAME_BOARD      HEADER
#define GAME_RULES      (GAME_BOARD + SQUARES)
#define GAME_SCENE      (GAME_RULES + RULES_STATE_SIZE)
#define GAME_BODY       (GAME_SCENE + GAME_EXTRA)
#define GAME_SIZE       (GAME_BODY + 2)

static uint8_t file[FILE_SIZE];
static uint8_t game[GAME_SIZE];
static char name[NAME_LENGTH + 1];

static uint8_t* slot_data(uint8_t slot) {
    return file + HEADER + slot * SLOT_SIZE;
}

static uint16_t checksum(const uint8_t* data, uint16_t size) {
    uint16_t value = 0x5713, i;

    for(i=0; i<size; i++) value = (value << 5) ^ (value >> 11) ^ data[i];
    return value;
}

/**
 * @brief Read and clear the drive's status: 1 if it reports "00, OK"
 */
static uint8_t drive_ok(void) {
    uint8_t status[2], ok;

    if(cbm_open(15, 8, 15, "")) {
        cbm_close(15);
        return 0;
    }
    ok = cbm_read(15, status, 2) == 2 && status[0] == '0' && status[1] == '0';
    while(cbm_read(15, status, 1) == 1 && status[0] != 13);
    cbm_close(15);
    return ok;
}

/**
 * @brief Read a whole file with a header and a checksum after `body` bytes
 *
 * @return 1 if the file has the size, the header and the checksum expected
 */
static uint8_t read_file(const char* path, const char* magic, uint8_t* data, uint16_t body) {
    uint16_t total = 0;
    int got;

    if(!cbm_open(CHANNEL, 8, CHANNEL, path)) {
        while(total < body + 2 && (got = cbm_read(CHANNEL, data + total, body + 2 - total)) > 0) {
            total += got;
        }
    }
    cbm_close(CHANNEL);
    drive_ok();                                 // clears "file not found"
    return total == body + 2 && !memcmp(data, magic, HEADER) &&
           checksum(data, body) == (data[body] | (data[body + 1] << 8));
}

/**
 * @brief Write a header, `body` bytes and their checksum to a file
 *
 * @return 1 if the drive reports success
 */
static uint8_t write_file(const char* path, const char* magic, uint8_t* data, uint16_t body) {
    uint16_t sum;
    uint8_t ok;

    memcpy(data, magic, HEADER);
    sum = checksum(data, body);
    data[body] = (uint8_t)sum;
    data[body + 1] = sum >> 8;
    if(cbm_open(CHANNEL, 8, CHANNEL, path)) {
        cbm_close(CHANNEL);
        return 0;
    }
    ok = cbm_write(CHANNEL, data, body + 2) == body + 2;
    cbm_close(CHANNEL);
    return drive_ok() && ok;
}

uint8_t store_read(void) {
    uint8_t ok = read_file("DEPLOY.DAT,S,R", MAGIC, file, BODY);

    if(!ok) memset(file, 0, FILE_SIZE);
    return ok;
}

uint8_t store_write(void) {
    return write_file("@:DEPLOY.DAT,S,W", MAGIC, file, BODY);
}

uint8_t store_used(uint8_t slot) {
    return slot_data(slot)[0] != 0;
}

const char* store_name(uint8_t slot) {
    memcpy(name, slot_data(slot), NAME_LENGTH);
    name[NAME_LENGTH] = 0;
    return name;
}

void store_load(uint8_t slot) {
    memcpy(board + RED_HOME0, slot_data(slot) + NAME_LENGTH, ARMY_SIZE);
}

void store_save(uint8_t slot, const char* text) {
    uint8_t* data = slot_data(slot);

    memset(data, 0, NAME_LENGTH);
    strncpy((char*)data, text, NAME_LENGTH);
    memcpy(data + NAME_LENGTH, board + RED_HOME0, ARMY_SIZE);
}

uint8_t store_game_write(const uint8_t* extra) {
    memcpy(game + GAME_BOARD, board, SQUARES);
    rules_state_save(game + GAME_RULES);
    memcpy(game + GAME_SCENE, extra, GAME_EXTRA);
    return write_file("@:GAME.DAT,S,W", GAME_MAGIC, game, GAME_BODY);
}

uint8_t store_game_read(uint8_t* extra) {
    if(!read_file("GAME.DAT,S,R", GAME_MAGIC, game, GAME_BODY)) return 0;
    memcpy(board, game + GAME_BOARD, SQUARES);
    rules_state_load(game + GAME_RULES);
    memcpy(extra, game + GAME_SCENE, GAME_EXTRA);
    return 1;
}
