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

#ifndef _DEPLOY_DIALOG_H
#define _DEPLOY_DIALOG_H

#include <stdint.h>
#include "store.h"

#define DIALOG_OPEN         0
#define DIALOG_DONE         1
#define DIALOG_CANCELLED    2

/* the deployment on Red's rows: its name ("" if none) and its slot (or NOWHERE) */
extern char deployment_name[NAME_LENGTH + 1];
extern uint8_t deployment_slot;

/* set when a save dialog finishes: whether the drive accepted the file */
extern uint8_t dialog_saved;

/**
 * @brief Open the list of deployments: ten built-in ones and the player's
 *
 * The slots come from the store, which deploy_enter() reads from disk.
 * Hovering (or the arrow keys) previews a deployment on Red's rows; a click
 * or Return takes it. Escape, or a click outside the plate, puts back what
 * was there.
 */
void dialog_load_open(void);

/**
 * @brief Open the save dialog: a name to type and one of ten slots
 *
 * Return or the SAVE button keeps the deployment in the slot and writes
 * DEPLOY.DAT; Escape or CANCEL closes the dialog.
 */
void dialog_save_open(void);

/**
 * @brief Handle the input of a frame while a dialog is open
 *
 * @return DIALOG_OPEN, or how the dialog closed
 */
uint8_t dialog_update(void);

#endif
