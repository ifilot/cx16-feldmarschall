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

#ifndef _DEPLOY_H
#define _DEPLOY_H

#include <stdint.h>

/**
 * @brief The player builds a setup: Red's 40 pieces start in the tray and
 *        are dragged onto rows 1-4
 *
 * Press on a piece in the tray, or on a red piece already deployed, to pick
 * it up; release over one of Red's home squares to put it there. Dropping
 * on another red piece swaps the two. Releasing over the tray returns the
 * piece to its compartment; anywhere else, it goes back where it came from.
 *
 * The buttons in the message bar (or their keys) start a blank deployment
 * (N), load one of ten built-in or ten saved deployments (L), save the
 * deployment under a name (S), deploy at random (R) and start the game
 * (Return). Saving and starting need all 40 pieces on the board. The
 * deployment is kept when leaving the scene; Escape returns to the menu.
 */
void deploy_enter(void);

uint8_t deploy_update(void);

#endif
