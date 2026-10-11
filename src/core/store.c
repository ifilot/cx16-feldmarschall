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

#include <cbm.h>
#include <string.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "store.h"
#include "board.h"

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

static uint8_t file[FILE_SIZE];
static char name[NAME_LENGTH + 1];

static uint8_t* slot_data(uint8_t slot) {
    return file + HEADER + slot * SLOT_SIZE;
}

static uint16_t checksum(void) {
    uint16_t value = 0x5713, i;

    for(i=0; i<BODY; i++) value = (value << 5) ^ (value >> 11) ^ file[i];
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

uint8_t store_read(void) {
    uint16_t total = 0;
    int got;
    uint8_t ok;

    if(!cbm_open(CHANNEL, 8, CHANNEL, "DEPLOY.DAT,S,R")) {
        while(total < FILE_SIZE && (got = cbm_read(CHANNEL, file + total, FILE_SIZE - total)) > 0) {
            total += got;
        }
    }
    cbm_close(CHANNEL);
    drive_ok();                                 // clears "file not found"
    ok = total == FILE_SIZE && !memcmp(file, MAGIC, HEADER) &&
         checksum() == (file[BODY] | (file[BODY + 1] << 8));
    if(!ok) memset(file, 0, FILE_SIZE);
    return ok;
}

uint8_t store_write(void) {
    uint16_t sum;
    uint8_t ok;

    memcpy(file, MAGIC, HEADER);
    sum = checksum();
    file[BODY] = (uint8_t)sum;
    file[BODY + 1] = sum >> 8;
    if(cbm_open(CHANNEL, 8, CHANNEL, "@:DEPLOY.DAT,S,W")) {
        cbm_close(CHANNEL);
        return 0;
    }
    ok = cbm_write(CHANNEL, file, FILE_SIZE) == FILE_SIZE;
    cbm_close(CHANNEL);
    return drive_ok() && ok;
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
