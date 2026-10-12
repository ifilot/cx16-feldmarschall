#include <cbm.h>
#include <cx16.h>
#include <string.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "colors.h"
#include "color_profiles.h"
#include "gfx.h"
#include "pieces.h"
#include "video.h"

#if FIELD_PROFILE_COUNT != FIELD_PROFILES || ARMY_PROFILE_COUNT != ARMY_PROFILES
#error Appearance profile counts must match generated profiles
#endif

uint8_t colors_field;
uint8_t colors_armies;
static uint8_t settings[8];

static const char* const ranking_names[RANKING_COUNT] = {
    "CLASSIC (MARSHAL 1)", "MODERN (MARSHAL 10)",
};

static uint8_t drive_ok(void) {
    uint8_t status[2], ok;
    if(cbm_open(15, 8, 15, "")) {
        cbm_close(15);
        return 0;
    }
    ok = cbm_read(15, status, 2) == 2 && status[0] == '0' && status[1] == '0';
    while(cbm_read(15, status, 1) == 1 && status[0] != 13);
    cbm_close(15);
    return ok;
}

const char* colors_name(uint8_t group, uint8_t profile) {
    if(group == 0) return field_names[profile];
    if(group == 1) return army_names[profile];
    return ranking_names[profile];
}

uint8_t colors_count(uint8_t group) {
    if(group == 0) return FIELD_PROFILES;
    if(group == 1) return ARMY_PROFILES;
    return RANKING_COUNT;
}

uint8_t colors_current(uint8_t group) {
    if(group == 0) return colors_field;
    if(group == 1) return colors_armies;
    return piece_ranking;
}

uint8_t colors_select(uint8_t group, uint8_t profile) {
    uint8_t old;

    if(group >= GROUPS || profile >= colors_count(group)) return 0;
    if(profile == colors_current(group)) return 1;
    if(group == 2) {
        // the tokens carry their numbers: load the artwork of the other numbering
        old = piece_ranking;
        piece_ranking = profile;
        if(video_ranks()) return 1;
        piece_ranking = old;
        video_ranks();
        return 0;
    }
    if(group == 0) {
        if(field_art[profile] != field_art[colors_field] && !video_field(field_art[profile])) {
            video_field(field_art[colors_field]);
            return 0;
        }
        colors_field = profile;
    } else {
        colors_armies = profile;
    }
    colors_apply();
    return 1;
}

/* Restore the selected field and palette after the campaign menu. */
uint8_t colors_restore_field(void) {
    colors_apply();
    return video_restore_game_tiles() && video_field(field_art[colors_field]);
}

void colors_apply(void) {
    uint8_t row, index;
    uint16_t value;
    const uint16_t* field = field_profiles[colors_field];
    const uint16_t* pieces = army_profiles[colors_armies];
    const uint16_t* ui = field_profiles[0];

    VERA.control = 0;
    VERA.address = (uint16_t)VRAM_PALETTE;
    VERA.address_hi = 0x11;
    for(row=0; row<16; row++) {
        for(index=0; index<16; index++) {
            value = (row == 1 || row == 2) ? pieces[index] :
                    (row == PALETTE_FIELD ? field[index] : ui[index]);
            if(row == 2 && (index == 12 || index == 13)) value = pieces[index + 2];
            if(index == 1) {
                if(row == 3) value = ui[5];
                else if(row == 4) value = pieces[13];
                else if(row == 5) value = pieces[15];
                else if(row == TEXT_UI_RED) value = ui[13];
            }
            VERA.data0 = (uint8_t)value;
            VERA.data0 = value >> 8;
        }
    }
}

uint8_t colors_init(void) {
    uint8_t total = 0;
    int got;
    colors_field = colors_armies = 0;
    piece_ranking = RANKING_CLASSIC;
    // Startup can leave this logical channel open; reclaim it before reading.
    cbm_close(4);
    if(!cbm_open(4, 8, 4, "COLORS.DAT,S,R")) {
        while(total < sizeof(settings) &&
              (got = cbm_read(4, settings + total, sizeof(settings) - total)) > 0) total += got;
    }
    cbm_close(4);
    drive_ok();
    if(total == 8 && !memcmp(settings, "CLR6", 4) &&
       settings[4] < FIELD_PROFILES && settings[5] < ARMY_PROFILES && settings[6] < RANKING_COUNT &&
       settings[7] == (uint8_t)(0xA5 ^ settings[4] ^ settings[5] ^ settings[6])) {
        colors_field = settings[4];
        colors_armies = settings[5];
        piece_ranking = settings[6];
    } else if(total == 7 && !memcmp(settings, "CLR5", 4) &&
       settings[4] < FIELD_PROFILES && settings[5] < ARMY_PROFILES &&
       settings[6] == (uint8_t)(0xA5 ^ settings[4] ^ settings[5])) {
        colors_field = settings[4];
        colors_armies = settings[5];
    } else if(total == 7 && !memcmp(settings, "CLR4", 4) &&
              settings[4] < 6 && settings[5] < 3 &&
              settings[6] == (uint8_t)(0xA5 ^ settings[4] ^ settings[5])) {
        // Retain paper/campaign choices; removed motifs become polished tiles.
        colors_field = settings[4] < 3 ? settings[4] : 3;
        colors_armies = settings[5];
    } else if(total == 7 && !memcmp(settings, "CLR3", 4) &&
              settings[4] < 5 && settings[5] < 3 &&
              settings[6] == (uint8_t)(0xA5 ^ settings[4] ^ settings[5])) {
        // Retain campaign choices; paper and removed surfaces migrate to paper.
        colors_field = settings[4] < 2 ? settings[4] : 2;
        colors_armies = settings[5];
    } else if(total == 8 && !memcmp(settings, "CLR2", 4) &&
       settings[4] < 5 && settings[5] < 3 &&
       settings[6] < 4 &&
       settings[7] == (uint8_t)(0xA5 ^ settings[4] ^ settings[5] ^ settings[6])) {
        colors_field = settings[4] < 2 ? settings[4] : 2;
        colors_armies = settings[5];
    } else if(total == 7 && !memcmp(settings, "CLR1", 4) &&
              settings[4] < 6 && settings[5] < 6 &&
              settings[6] == (uint8_t)(0xA5 ^ settings[4] ^ settings[5])) {
        // Preserve retained choices from the earlier six-palette release.
        colors_field = settings[4] < 2 ? settings[4] : 0;
        if(settings[5] == 4) colors_armies = 1;
        else if(settings[5] == 2) colors_armies = 2;
    }
    if(field_art[colors_field] && !video_field(field_art[colors_field])) return 0;
    if(piece_ranking != RANKING_CLASSIC && !video_ranks()) return 0;
    colors_apply();
    return 1;
}

uint8_t colors_save(void) {
    uint8_t ok;
    memcpy(settings, "CLR6", 4);
    settings[4] = colors_field;
    settings[5] = colors_armies;
    settings[6] = piece_ranking;
    settings[7] = 0xA5 ^ colors_field ^ colors_armies ^ piece_ranking;
    if(cbm_open(4, 8, 4, "@:COLORS.DAT,S,W")) {
        cbm_close(4);
        drive_ok();
        return 0;
    }
    ok = cbm_write(4, settings, 8) == 8;
    cbm_close(4);
    return drive_ok() && ok;
}
