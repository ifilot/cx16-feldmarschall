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

#ifndef _STORE_H
#define _STORE_H

#include <stdint.h>

#define STORE_SLOTS         10
#define NAME_LENGTH         16

/**
 * @brief Read the player's deployments from DEPLOY.DAT
 *
 * A missing or damaged file leaves every slot empty.
 *
 * @return 1 if the file was read
 */
uint8_t store_read(void);

/**
 * @brief Write all slots to DEPLOY.DAT, replacing the file
 *
 * @return 1 if the drive reports success
 */
uint8_t store_write(void);

uint8_t store_used(uint8_t slot);

/**
 * @brief The name in a slot (valid until the next call)
 */
const char* store_name(uint8_t slot);

/**
 * @brief Put the deployment of a slot on Red's home rows
 */
void store_load(uint8_t slot);

/**
 * @brief Keep Red's home rows in a slot under a name (in memory; see store_write)
 */
void store_save(uint8_t slot, const char* name);

#endif
