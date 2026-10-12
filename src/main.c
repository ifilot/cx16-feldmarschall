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
#include <stdio.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "scene.h"
#include "video.h"
#include "menu.h"
#include "deploy.h"
#include "play.h"
#include "options.h"
#include "about.h"
#include "game_settings.h"
#include "colors.h"
#include "random.h"

// KERNAL mouse_get stores the pointer position in r0 (x) and r1 (y)
#define MOUSE_X     (*(volatile int16_t*)0x02)
#define MOUSE_Y     (*(volatile int16_t*)0x04)

input_t input;

static uint8_t scene;
static uint8_t buttons;

/**
 * @brief Wait for the next 60 Hz jiffy
 *
 * Replaces cc65's waitvsync, which (in cc65 2.19) polls the jiffy counter
 * through the pre-R39 memory map and never returns on current ROMs.
 */
static uint8_t jiffy;
static void wait_frame(void) {
    asm("jsr $FFDE");               // RDTIM: A = low byte of the jiffy clock
    asm("sta %v", jiffy);
wait:
    asm("jsr $FFDE");
    asm("cmp %v", jiffy);
    asm("beq %g", wait);
}

static void read_input(void) {
    asm("ldx #2");
    asm("jsr $FF6B");               // mouse_get
    asm("sta %v", buttons);
    input.x = MOUSE_X;
    input.y = MOUSE_Y;
    input.pressed = buttons & ~input.buttons;
    input.buttons = buttons;
    input.key = cbm_k_getin();
    input.frame++;
}

static void enter(uint8_t next) {
    video_cursor_hide();
    video_sprite_hide(SPRITE_DRAG);
    video_sprite_hide(SPRITE_FALL);
    video_clear_layer1();
    if(scene == SCENE_GAME_SETTINGS && next != SCENE_GAME_SETTINGS) colors_restore_field();
    random_seed(input.frame);       // the player's timing seeds the dice
    scene = next;
    switch(scene) {
        case SCENE_DEPLOY: deploy_enter(0); break;
        case SCENE_PREPARE: deploy_enter(1); break;
        case SCENE_PLAY:   play_enter(); break;
        case SCENE_OPTIONS: options_enter(); break;
        case SCENE_ABOUT: about_enter(); break;
        case SCENE_GAME_SETTINGS: game_settings_enter(); break;
        default:           menu_enter(); break;
    }
}

void main(void) {
    uint8_t next;

    if(!video_splash()) {
        puts("could not load the splash screen");
        return;
    }
    do {
        wait_frame();
        read_input();
    } while(input.key != KEY_RETURN);

    if(!video_init()) {
        puts("could not load the graphics");
        return;
    }
    enter(SCENE_MENU);
    video_show();

    for(;;) {
        wait_frame();
        read_input();
        switch(scene) {
            case SCENE_DEPLOY: next = deploy_update(); break;
            case SCENE_PREPARE: next = deploy_update(); break;
            case SCENE_PLAY:   next = play_update(); break;
            case SCENE_OPTIONS: next = options_update(); break;
            case SCENE_ABOUT: next = about_update(); break;
            case SCENE_GAME_SETTINGS: next = game_settings_update(); break;
            default:           next = menu_update(); break;
        }
        if(next != SCENE_STAY) enter(next);
    }
}
