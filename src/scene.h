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

#ifndef _SCENE_H
#define _SCENE_H

#include <stdint.h>

/*
 * The program is a sequence of scenes. Each scene has an enter function,
 * which draws it from scratch, and an update function, which main() calls
 * once per frame and which returns the scene to switch to, or SCENE_STAY.
 * Before entering a scene, main() clears layer 1 and hides the sprites;
 * layer 0 (terrain, frame and panel) is shared by all scenes. By
 * convention Escape returns to the menu, unless a dialog is open.
 */
#define SCENE_MENU      0
#define SCENE_DEPLOY    1
#define SCENE_PLAY      2
#define SCENE_OPTIONS   3
#define SCENE_PREPARE   4
#define SCENE_ABOUT     5
#define SCENE_GAME_SETTINGS 6
#define SCENE_STAY      0xFF

#define BUTTON_LEFT     0x01

#define KEY_RETURN      0x0D
#define KEY_ESCAPE      0x1B
#define KEY_UP          0x91
#define KEY_DOWN        0x11

/* the input of the current frame, read by main() before each update */
typedef struct {
    int16_t x, y;           // mouse pointer
    uint8_t buttons;        // buttons held
    uint8_t pressed;        // buttons pressed since the previous frame
    uint8_t key;            // key typed this frame, or 0
    uint16_t frame;         // frames since start
} input_t;

extern input_t input;

#endif
