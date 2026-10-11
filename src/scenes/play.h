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

#ifndef _PLAY_H
#define _PLAY_H

#include <stdint.h>

/**
 * @brief A game against the computer
 *
 * Red (the player) uses the setup built in the deployment scene, or a
 * random one if that is incomplete; Blue deploys at random. Red moves by
 * dragging a piece: gold dots show where it can go, and dropping it on an
 * enemy attacks. Both pieces in a battle are shown face up; a blue
 * survivor then turns face down again, so the player has to remember it
 * (Blue keeps track of the red pieces it has seen). The loser flies off
 * the board: Blue's into its own
 * compartment of the tray, which thus shows what Blue has lost, and Red's
 * below the screen. Blue's moves slide across the board. Capturing the
 * flag, or leaving the opponent without a move, wins. Return plays again.
 */
void play_enter(void);

uint8_t play_update(void);

#endif
