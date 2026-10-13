#include <ascii_charmap.h>
#pragma static-locals (on)

#include "options.h"
#include "scene.h"
#include "board.h"
#include "boardview.h"
#include "button.h"
#include "colors.h"
#include "dialog.h"
#include "panel.h"
#include "video.h"
#include "sound.h"

#define COL (TRAY_COL0 + 3)
#define FIELD_ROW (TRAY_ROW0 + 3)
#define ARMY_ROW (TRAY_ROW0 + 14)
#define RANK_ROW (TRAY_ROW0 + 29)
#define BACK_ROW (TRAY_ROW0 + 34)
#define KEY_TAB 0x09

static uint8_t focus, dirty, back_hover;

static const uint8_t rows[GROUPS] = {FIELD_ROW, ARMY_ROW, RANK_ROW};
static const char* const headings[GROUPS] = {"FIELD", "ARMY COLORS", "RANK NUMBERS"};

static void draw_profiles(void) {
    uint8_t group, i, row, selected;
    for(group=0; group<GROUPS; group++) {
        video_text_plate(COL - 2, rows[group] - 2, focus == group ? ">" : " ", TEXT_BROWN);
        video_text_plate(COL, rows[group] - 2, headings[group], TEXT_BROWN);
        selected = colors_current(group);
        for(i=0; i<colors_count(group); i++) {
            row = rows[group] + i * 2;
            video_text_plate(COL - 2, row, selected == i ? "*" : " ", TEXT_BROWN);
            video_text_plate(COL, row, "                     ", TEXT_INK);
            video_text_plate(COL, row, colors_name(group, i), selected == i ? TEXT_BROWN : TEXT_INK);
        }
    }
    video_clear_block(PLATE_COL0 + 1, INFO_ROW2, PLATE_COLS - 2, 1);
    video_clear_block(PLATE_COL0 + 1, INFO_ROW3, PLATE_COLS - 2, 1);
    video_text(PLATE_COL0 + 1, INFO_ROW2, colors_name(0, colors_field), TEXT_BROWN);
    video_text(PLATE_COL0 + 1, INFO_ROW3, colors_name(1, colors_armies), TEXT_INK);
}

static void select_profile(uint8_t profile) {
    uint8_t old = colors_current(focus);
    if(old != profile) {
        sound_sfx(SFX_MENU_SELECT);
        if(!colors_select(focus, profile)) {
            sound_sfx(SFX_ERROR);
            panel_info("ARTWORK LOAD FAILED", TEXT_BROWN, "CHECK THE DISK");
            return;
        }
        dirty = 1;
    }
    draw_profiles();
}

void options_enter(void) {
    uint8_t i, col;
    board_clear();
    view_board();
    // All thirteen token designs in both palettes, including hidden backs.
    for(i=0; i<TOKENS; i++) {
        col = BOARD_X / 8 + (i % BOARD_SIZE) * SQUARE_TILES;
        video_token(col, BOARD_Y / 8 + (i / BOARD_SIZE) * SQUARE_TILES, i, ARMY_BLUE);
        video_token(col, BOARD_Y / 8 + (8 + i / BOARD_SIZE) * SQUARE_TILES, i, ARMY_RED);
    }
    focus = dirty = back_hover = 0;
    panel_tray_clear();
    dialog_plate(TRAY_COL0, TRAY_ROW0, TRAY_COLS * SQUARE_TILES, TRAY_ROWS * SQUARE_TILES);
    panel_info("APPEARANCE OPTIONS", TEXT_BROWN, "LIVE PREVIEW");
    draw_profiles();
    button_draw(COL, BACK_ROW, "BACK", BUTTON_NORMAL);
    panel_bar("", "");
    video_text_plate(2, 55, "CLICK A PROFILE TO PREVIEW", TEXT_INK);
}

uint8_t options_update(void) {
    uint8_t group, i, row, selected, hover, old_focus = focus;
    if(input.pointer_active) {
        if(input.x >= (COL - 2) * 8 && input.x < (TRAY_COL0 + TRAY_COLS * SQUARE_TILES - 1) * 8) {
            for(group=0; group<GROUPS; group++) {
                for(i=0; i<colors_count(group); i++) {
                    row = rows[group] + i * 2;
                    if(input.y >= row * 8 - 4 && input.y < row * 8 + 12) {
                        focus = group;
                        if(input.pressed & BUTTON_LEFT) select_profile(i);
                    }
                }
            }
        }
    }
    hover = button_hit(COL, BACK_ROW, "BACK", input.x, input.y);
    if(hover != back_hover) {
        back_hover = hover;
        button_draw(COL, BACK_ROW, "BACK", hover ? BUTTON_HOVER : BUTTON_NORMAL);
    }
    selected = colors_current(focus);
    switch(input.key) {
        case KEY_TAB: focus = (focus + 1) % GROUPS; break;
        case KEY_UP: if(selected > 0) select_profile(selected - 1); break;
        case KEY_DOWN: if(selected + 1 < colors_count(focus)) select_profile(selected + 1); break;
        default:
            if(input.key >= '1' && input.key < '1' + colors_count(focus)) select_profile(input.key - '1');
            break;
    }
    if(focus != old_focus) draw_profiles();
    if(focus != old_focus) sound_sfx(SFX_MENU_MOVE);
    if(input.key == KEY_RETURN || input.key == KEY_ESCAPE || (input.pointer_active && hover && (input.pressed & BUTTON_LEFT))) {
        sound_sfx(SFX_MENU_BACK);
        if(dirty && !colors_save()) {
            dirty = 0;
            panel_info("SAVING FAILED", TEXT_BROWN, "ACTIVE THIS SESSION");
            panel_bar("SETTINGS COULD NOT BE SAVED TO DISK", "CHANGES ARE ACTIVE THIS SESSION");
            return SCENE_STAY;
        }
        return SCENE_MENU;
    }
    return SCENE_STAY;
}
