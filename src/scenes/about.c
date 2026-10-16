#include <ascii_charmap.h>
#pragma static-locals (on)

#include "about.h"
#include "app_info.h"
#include "scene.h"
#include "board.h"
#include "boardview.h"
#include "button.h"
#include "dialog.h"
#include "panel.h"
#include "video.h"

#define PLATE_COL 3
#define PLATE_ROW 12
#define PLATE_W 48
#define PLATE_H 32
#define BACK_COL (PLATE_COL + PLATE_W / 2 - 4)
#define BACK_ROW (PLATE_ROW + 27)

static uint8_t hovered;

static void info(uint8_t row, const char* label, const char* value) {
    dialog_centred(PLATE_COL, PLATE_W, row, label, TEXT_BROWN);
    dialog_centred(PLATE_COL, PLATE_W, row + 2, value, TEXT_INK);
}

void about_enter(void) {
    board_clear();
    view_board();
    panel_tray_clear();
    panel_tray_draw();
    panel_info("ABOUT", TEXT_BROWN, APP_NAME);
    panel_clear_selected();
    dialog_plate(PLATE_COL, PLATE_ROW, PLATE_W, PLATE_H);
    dialog_centred(PLATE_COL, PLATE_W, PLATE_ROW + 3, APP_NAME, TEXT_INK);
    dialog_centred(PLATE_COL, PLATE_W, PLATE_ROW + 5, "COMMANDER X16", TEXT_BROWN);
    info(PLATE_ROW + 8, "AUTHOR", APP_AUTHOR);
    info(PLATE_ROW + 13, "GITHUB REPOSITORY", APP_REPOSITORY);
    info(PLATE_ROW + 18, "VERSION", APP_VERSION);
    info(PLATE_ROW + 23, "COMPILATION DATE", APP_COMPILED);
    hovered = 0;
    button_draw(BACK_COL, BACK_ROW, "BACK", BUTTON_NORMAL);
    panel_bar("", "");
}

uint8_t about_update(void) {
    uint8_t hover = button_hit(BACK_COL, BACK_ROW, "BACK", input.x, input.y);
    if(hover != hovered) {
        hovered = hover;
        button_draw(BACK_COL, BACK_ROW, "BACK", hover ? BUTTON_HOVER : BUTTON_NORMAL);
    }
    if(input.key == KEY_RETURN || input.key == KEY_ESCAPE || (input.pointer_active && hover && (input.pressed & BUTTON_LEFT))) {
        return SCENE_MENU;
    }
    return SCENE_STAY;
}
