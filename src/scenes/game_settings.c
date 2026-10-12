#include <ascii_charmap.h>
#pragma static-locals (on)
#include "game_settings.h"
#include "scene.h"
#include "rules.h"
#include "dialog.h"
#include "button.h"
#include "video.h"
#include "colors.h"

#define FIRST 20
#define PITCH 4
#define LABEL_COL 12
#define STATE_COL 38
#define DETAIL_COL 45
#define DETAIL_ROW 18
#define DETAIL_WIDTH 29
#define BACK_COL 10
#define CLASSIC_COL 30
#define NEXT_COL 56
#define BUTTON_ROW 52

static uint8_t choice, hovered;
static int16_t last_x, last_y;
static const char* const names[6] = {
    "1  ATTACKER'S ADVANTAGE", "2  SILENT DEFENSE", "3  EXPLODING BOMBS",
    "4  MOVING BOMBS", "5  MOVING FLAG", "6  RESCUE"
};
static const char* const details[6][6] = {
    {"WHEN EQUAL RANKS MEET,", "THE ATTACKER SURVIVES.", "", "OTHER BATTLES FOLLOW", "THE NORMAL RANK ORDER.", ""},
    {"THE DEFENDER'S RANK", "STAYS SECRET.", "", "SCOUT ATTACKS REVEAL IT.", "RANKS ALREADY SEEN", "REMAIN KNOWN."},
    {"THE BOMB AND ITS", "ATTACKER BOTH FALL.", "", "A MINER STILL DEFUSES", "THE BOMB AND SURVIVES.", ""},
    {"BOMBS MAY MOVE ONE", "SQUARE, BUT NEVER ATTACK.", "", "THIS ALSO ENABLES", "EXPLODING BOMBS.", ""},
    {"THE FLAG MAY MOVE ONE", "SQUARE, BUT NEVER ATTACK.", "", "REACH THE ENEMY BACK", "ROW WITH YOUR FLAG", "TO WIN THE GAME."},
    {"REACH THE ENEMY BACK ROW", "TO RESTORE A CASUALTY.", "TWO RESCUES PER ARMY;", "ONCE PER ARRIVING PIECE.", "SCOUTS CANNOT RESCUE.", "BOMBS CANNOT RETURN."}
};
static const uint8_t button_cols[3] = {BACK_COL, CLASSIC_COL, NEXT_COL};
static const char* const button_names[3] = {"BACK", "CLASSIC RULES", "CONTINUE"};

static uint8_t button_at(void) {
    uint8_t i;
    for(i=0; i<3; i++) {
        if(button_hit(button_cols[i], BUTTON_ROW, button_names[i], input.x, input.y)) return i;
    }
    return 0xFF;
}

static void draw_buttons(void) {
    uint8_t i;
    for(i=0; i<3; i++) {
        button_draw(button_cols[i], BUTTON_ROW, button_names[i],
                    hovered == i ? BUTTON_HOVER : BUTTON_NORMAL);
        if(hovered == i) video_text_plate(button_cols[i] + 2, BUTTON_ROW + 1, button_names[i], TEXT_UI_RED);
    }
}

static void draw(void) {
    uint8_t i, row;
    for(i=0; i<6; i++) {
        row = FIRST + i * PITCH;
        video_text_plate(LABEL_COL - 2, row, i == choice ? ">" : " ", TEXT_UI_RED);
        video_text_plate(LABEL_COL, row, names[i], i == choice ? TEXT_UI_RED : TEXT_INK);
        video_text_plate(STATE_COL, row, (game_rules & (1 << i)) ? "ON " : "OFF", TEXT_UI_RED);
    }
    dialog_plate(DETAIL_COL, DETAIL_ROW, DETAIL_WIDTH, 24);
    dialog_centred(DETAIL_COL, DETAIL_WIDTH, DETAIL_ROW + 3, names[choice] + 3, TEXT_UI_RED);
    for(i=0; i<6; i++) {
        video_text_plate(DETAIL_COL + 2, DETAIL_ROW + 7 + i * 3, details[choice][i], TEXT_INK);
    }
}

static void toggle(uint8_t i) {
    game_rules ^= 1 << i;
    if(i == 3 && (game_rules & RULE_MOVING_BOMBS)) game_rules |= RULE_EXPLODING;
    if(i == 2 && !(game_rules & RULE_EXPLODING)) game_rules &= ~RULE_MOVING_BOMBS;
    choice = i;
    draw();
}

void game_settings_enter(void) {
    if(!video_campaign_menu()) {
        colors_restore_field();
        dialog_plate(0, 0, 80, 60);
        dialog_centred(0, 80, 7, "NEW GAME", TEXT_UI_RED);
        dialog_centred(0, 80, 10, "ARTWORK UNAVAILABLE", TEXT_UI_RED);
    }
    dialog_centred(0, 80, 58, "1-6 / SPACE: TOGGLE   ENTER: CONTINUE", TEXT_INK);
    hovered = button_at();
    last_x = input.x;
    last_y = input.y;
    draw();
    draw_buttons();
}

uint8_t game_settings_update(void) {
    uint8_t i, old = choice, hover = button_at(), key = input.key;
    if(key >= 0xC1 && key <= 0xDA) key -= 0x80;
    if(key == KEY_ESCAPE) return SCENE_MENU;
    if(key == KEY_RETURN) return SCENE_PREPARE;
    if(key >= '1' && key <= '6') toggle(key - '1');
    if(key == ' ') toggle(choice);
    if(key == 'C' || key == 'c') { game_rules = 0; draw(); }
    if(key == KEY_UP && choice) choice--;
    if(key == KEY_DOWN && choice < 5) choice++;
    if(hover != hovered) { hovered = hover; draw_buttons(); }
    if(input.pressed & BUTTON_LEFT) {
        if(hover == 0) return SCENE_MENU;
        if(hover == 2) return SCENE_PREPARE;
        if(hover == 1) { game_rules = 0; draw(); }
    }
    if(input.x != last_x || input.y != last_y || input.pressed) {
        if(input.x >= (LABEL_COL - 2) * 8 && input.x < (STATE_COL + 3) * 8) {
            for(i=0; i<6; i++) {
                if(input.y >= (FIRST + i * PITCH) * 8 - 8 && input.y < (FIRST + i * PITCH) * 8 + 16) {
                    choice = i;
                    if(input.pressed & BUTTON_LEFT) toggle(i);
                }
            }
        }
    }
    last_x = input.x; last_y = input.y;
    if(choice != old) draw();
    return SCENE_STAY;
}
