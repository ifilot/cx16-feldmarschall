#include <ascii_charmap.h>
#pragma static-locals (on)
#include "game_settings.h"
#include "ai.h"
#include "scene.h"
#include "rules.h"
#include "dialog.h"
#include "button.h"
#include "video.h"
#include "sound.h"
#include "colors.h"
#include "board.h"
#include "boardview.h"
#include "panel.h"

#define FIRST 20
#define PITCH 4
#define LABEL_COL 12
#define STATE_COL 38
#define DETAIL_COL 54
#define DETAIL_ROW 18
#define DETAIL_WIDTH 25
#define BACK_COL 9
#define CLASSIC_COL 21
#define NEXT_COL 33
#define BUTTON_ROW 44
#define LEVEL_COL (DETAIL_COL + 2)
#define LEVEL_ROW 44
#define LEVEL_WIDTH 12

static uint8_t choice, hovered, pressed = 0xFF, press_timer;
static const char* const names[6] = {
    "ATTACKER'S ADVANTAGE", "SILENT DEFENSE", "EXPLODING BOMBS",
    "MOVING BOMBS", "MOVING FLAG", "RESCUE"
};
static const char* const details[6][6] = {
    {"WHEN EQUAL RANKS MEET,", "THE ATTACKER SURVIVES.", "", "OTHER BATTLES FOLLOW", "NORMAL RANK ORDER.", ""},
    {"DEFENDING RANKS STAY", "SECRET.", "", "SCOUTS REVEAL THEM.", "RANKS ALREADY SEEN", "REMAIN KNOWN."},
    {"THE BOMB AND ITS", "ATTACKER BOTH FALL.", "", "MINERS STILL DEFUSE", "BOMBS AND SURVIVE.", ""},
    {"BOMBS MAY MOVE ONE", "SQUARE, NEVER ATTACK.", "", "ALSO ENABLES", "EXPLODING BOMBS.", ""},
    {"THE FLAG MAY MOVE ONE", "SQUARE, NEVER ATTACK.", "", "REACH THE ENEMY'S", "BACK ROW WITH YOUR", "FLAG TO WIN."},
    {"REACH THE ENEMY'S", "BACK ROW TO RESTORE", "A FALLEN PIECE.", "TWO RESCUES PER ARMY.", "SCOUTS CANNOT RESCUE.", "BOMBS CANNOT RETURN."}
};
static const uint8_t button_cols[3] = {BACK_COL, CLASSIC_COL, NEXT_COL};
static const char* const button_names[3] = {"BACK", "CLASSIC", "CONTINUE"};

static uint8_t button_at(void) {
    uint8_t i;
    if(input.x >= LEVEL_COL*8 && input.x < (LEVEL_COL+LEVEL_WIDTH)*8 &&
       input.y >= LEVEL_ROW*8 && input.y < (LEVEL_ROW+BUTTON_HEIGHT)*8) return 3;
    for(i=0; i<3; i++) {
        if(button_hit(button_cols[i], BUTTON_ROW, button_names[i], input.x, input.y)) return i;
    }
    return 0xFF;
}

static void draw_level(void) {
    video_text_plate(LEVEL_COL, LEVEL_ROW-2, "DIFFICULTY", TEXT_UI_RED);
    button_draw_width(LEVEL_COL, LEVEL_ROW, LEVEL_WIDTH, ai_level_names[ai_difficulty],
                      pressed >= 9 && pressed != 0xFF ? BUTTON_PRESSED : hovered == 3 ? BUTTON_HOVER : BUTTON_NORMAL);
}

static void draw_buttons(void) {
    uint8_t i;
    for(i=0; i<3; i++) {
        button_draw(button_cols[i], BUTTON_ROW, button_names[i],
                    pressed == 6+i ? BUTTON_PRESSED : hovered == i ? BUTTON_HOVER : BUTTON_NORMAL);
        if(hovered == i) video_text_plate(button_cols[i] + 2, BUTTON_ROW + 1, button_names[i], TEXT_UI_RED);
    }
    draw_level();
}

static void draw(void) {
    uint8_t i, row;
    for(i=0; i<6; i++) {
        row = FIRST + i * PITCH;
        video_text_plate(LABEL_COL - 1, row, i == choice ? ">" : " ", TEXT_UI_RED);
        video_text_plate(LABEL_COL, row, names[i], i == choice ? TEXT_UI_RED : TEXT_INK);
        button_toggle(STATE_COL, row - 1, game_rules & (1 << i));
    }
    dialog_plate(DETAIL_COL, DETAIL_ROW, DETAIL_WIDTH, 41);
    dialog_centred(DETAIL_COL, DETAIL_WIDTH, DETAIL_ROW + 3, names[choice], TEXT_UI_RED);
    for(i=0; i<6; i++) {
        video_text_plate(DETAIL_COL + 2, DETAIL_ROW + 7 + i * 3, details[choice][i], TEXT_INK);
    }
    draw_level();
}

static void toggle(uint8_t i) {
    sound_sfx(SFX_MENU_SELECT);
    game_rules ^= 1 << i;
    if(i == 3 && (game_rules & RULE_MOVING_BOMBS)) game_rules |= RULE_EXPLODING;
    if(i == 2 && !(game_rules & RULE_EXPLODING)) game_rules &= ~RULE_MOVING_BOMBS;
    choice = i;
    draw();
}

void game_settings_enter(void) {
    pressed = 0xFF;
    board_clear();
    view_board();
    panel_tray_clear();
    panel_tray_draw();
    panel_info("NEW GAME", TEXT_DEEP_RED, "CHOOSE YOUR RULES");
    panel_clear_selected();
    panel_bar("CHOOSE YOUR RULES, THEN CONTINUE", "");
    dialog_plate(6, 9, 42, 39);
    dialog_title(9, 12, 36, 1);
    dialog_rule(10, 16, 33);
    hovered = 0xFF;
    draw();
    draw_buttons();
}

static uint8_t press(uint8_t item) {
    if(item < 6) { toggle(item); return SCENE_STAY; }
    pressed = item;
    press_timer = 6;
    draw();
    draw_buttons();
    return SCENE_STAY;
}

uint8_t game_settings_update(void) {
    uint8_t i, old = choice, hover = button_at(), key = input.key;
    if(pressed != 0xFF) {
        if(--press_timer) return SCENE_STAY;
        i = pressed;
        pressed = 0xFF;
        if(i < 6) toggle(i);
        else if(i == 6) { sound_sfx(SFX_MENU_BACK); return SCENE_MENU; }
        else if(i == 8) { sound_sfx(SFX_MENU_SELECT); return SCENE_PREPARE; }
        else if(i >= 9) { ai_difficulty = (ai_difficulty + (i == 9 ? 1 : 2)) % AI_LEVELS; sound_sfx(SFX_MENU_SELECT); }
        else { game_rules = 0; sound_sfx(SFX_MENU_SELECT); draw(); }
        draw_buttons();
        return SCENE_STAY;
    }
    if(key >= 0xC1 && key <= 0xDA) key -= 0x80;
    if(key == KEY_ESCAPE) { sound_sfx(SFX_MENU_BACK); return SCENE_MENU; }
    if(key == KEY_RETURN) return press(8);
    if(key == KEY_RIGHT) return press(9);
    if(key == KEY_LEFT) return press(10);
    if(key >= '1' && key <= '6') return press(key - '1');
    if(key == ' ') return press(choice);
    if(key == 'C' || key == 'c') return press(7);
    if(key == KEY_UP && choice) choice--;
    if(key == KEY_DOWN && choice < 5) choice++;
    if(input.key) hover = 0xFF;
    if(hover != hovered) { hovered = hover; draw_buttons(); }
    if(input.pointer_active && (input.pressed & BUTTON_LEFT) && hover < 4) return press(hover == 3 ? 9 : 6+hover);
    if(input.pointer_active && input.x >= 80 && input.x < 344) {
        for(i=0; i<6; i++) {
            if(input.y >= (FIRST + i * PITCH - 1) * 8 && input.y < (FIRST + i * PITCH + 2) * 8) {
                choice = i;
                if(input.pressed & BUTTON_LEFT) return press(i);
            }
        }
    }
    if(choice != old) { sound_sfx(SFX_MENU_MOVE); draw(); }
    return SCENE_STAY;
}
