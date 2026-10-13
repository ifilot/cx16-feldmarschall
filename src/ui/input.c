#include <cbm.h>
#pragma static-locals (on)
#include "input.h"
#include "scene.h"

#define MOUSE_X (*(volatile int16_t*)0x02)
#define MOUSE_Y (*(volatile int16_t*)0x04)

uint8_t pad_low, pad_high, pad_present;
extern void __fastcall__ input_poll_pad(uint8_t port);
static uint8_t mouse_buttons, previous_pad;

void input_read(void) {
    int16_t previous_x = input.x, previous_y = input.y;
    uint8_t low = 0, high = 0, port, step, fresh;
    asm("ldx #2");
    asm("jsr $FF6B");
    asm("sta %v", mouse_buttons);
    input.x = MOUSE_X;
    input.y = MOUSE_Y;
    input.key = cbm_k_getin();
    for(port=1; port<=4; port++) {
        input_poll_pad(port);
        if(!pad_present) {
            low |= (uint8_t)~pad_low;
            high |= (uint8_t)~pad_high;
        }
    }
    /* A held is exactly a held left mouse button. X offers fine positioning,
     * Y faster travel. Disconnected controllers contribute no held buttons. */
    step = high & 0x40 ? 1 : low & 0x40 ? 8 : 4;
    if(low & 1) input.x += step;
    if(low & 2) input.x -= step;
    if(low & 4) input.y += step;
    if(low & 8) input.y -= step;
    if(low & 15) {
        if(input.x < 0) input.x = 0;
        if(input.x > 639) input.x = 639;
        if(input.y < 0) input.y = 0;
        if(input.y > 479) input.y = 479;
        MOUSE_X = input.x;
        MOUSE_Y = input.y;
        asm("ldx #2");
        asm("lda #12");            // extapi mouse_set_position (ROM R47+)
        asm("jsr $FEAB");
    }
    fresh = low & (uint8_t)~previous_pad;
    previous_pad = low;
    if(!input.key) {
        if(fresh & 0xA0) input.key = KEY_ESCAPE;  // B / Select
        else if(fresh & 0x10) input.key = KEY_RETURN; // Start, once per press
    }
    if(high & 0x80) mouse_buttons |= BUTTON_LEFT;
    input.pressed = mouse_buttons & (uint8_t)~input.buttons;
    input.buttons = mouse_buttons;
    input.pointer_active = !input.key &&
        (input.x != previous_x || input.y != previous_y || input.pressed);
    input.frame++;
}
