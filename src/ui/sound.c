#include <cbm.h>
#include <cx16.h>
#include <ascii_charmap.h>
#pragma static-locals (on)

#include "sound.h"
#include "music.h"
#include "scene.h"
#define RAM_BANK (*(volatile uint8_t*)0x00)

#if MUSIC_LAST_BANK >= PLAY_BANK
#error Music overlaps the banked play scene; update PLAY_BANK and play_bank.s
#endif

uint8_t sound_music_enabled = 1;
uint8_t sound_effects_enabled = 1;
uint8_t sound_ready;
uint8_t sound_music_bank;
uint16_t sound_last_sfx;
static uint8_t game_track;
static uint8_t next_track;
static const uint8_t game_banks[] = {MUSIC_GAME_BANK, MUSIC_GAME2_BANK,
                                    MUSIC_GAME3_BANK, MUSIC_GAME4_BANK};
static const char* const files[] = {"TITLE.ZSM", "DEPLOY.ZSM", "GAME.ZSM", "GAME2.ZSM",
                                    "GAME3.ZSM", "GAME4.ZSM", "VICTORY.ZSM", "DEFEAT.ZSM"};
static const uint8_t banks[] = {MUSIC_TITLE_BANK, MUSIC_DEPLOY_BANK, MUSIC_GAME_BANK,
    MUSIC_GAME2_BANK, MUSIC_GAME3_BANK, MUSIC_GAME4_BANK, MUSIC_VICTORY_BANK, MUSIC_DEFEAT_BANK};

extern void sound_engine_init(void);
extern void __fastcall__ sound_music(uint8_t bank);
extern void sound_stop(void);
extern void sound_stop_music(void);
extern void sound_stop_effects(void);

static uint8_t load_banked(const char* name, uint8_t bank) {
    uint8_t previous = RAM_BANK, ok;
    RAM_BANK = bank;
    cbm_k_setnam(name);
    cbm_k_setlfs(0, 8, 2);
    /* LOAD's carry is the error indication. cc65's cbm_k_load returns an
     * address even on some X16 errors, so a nonzero end address is insufficient. */
    asm("lda #0");
    asm("ldx #0");
    asm("ldy #$A0");
    asm("jsr $FFD5");
    asm("lda #0");
    asm("rol a");
    asm("eor #1");
    asm("sta %v", ok);
    RAM_BANK = previous;
    return ok;
}

static void music(uint8_t bank) {
    if(bank == sound_music_bank) return;
    sound_music_bank = bank;
    if(sound_ready && sound_music_enabled) {
        sound_stop_music();
        if(bank) sound_music(bank);
    }
}

uint8_t sound_init(void) {
    uint8_t i;
    /* This bank contains executable game code and is required even if audio fails. */
    if(!load_banked("PLAY.BIN", PLAY_BANK) || !load_banked("AI.BIN", 23)) return 0;
    if(!load_banked("SFX.BIN", 2)) { sound_music_enabled = sound_effects_enabled = 0; return 1; }
    for(i=0; i<8; i++) if(!load_banked(files[i], banks[i])) { sound_music_enabled = sound_effects_enabled = 0; return 1; }
    sound_engine_init();
    sound_ready = 1;
    music(MUSIC_TITLE_BANK);
    return 1;
}

void sound_scene(uint8_t scene) {
    if(scene == SCENE_PLAY || scene == SCENE_DEMO) {
        game_track = game_banks[next_track];
        next_track = (next_track + 1) & 3;
        music(game_track);
        sound_sfx(SFX_START);
    } else if(scene == SCENE_RESUME) {
        if(!game_track) game_track = MUSIC_GAME_BANK;
        music(game_track);
    } else music(scene == SCENE_DEPLOY || scene == SCENE_PREPARE ||
                 scene == SCENE_GAME_SETTINGS ? MUSIC_DEPLOY_BANK : MUSIC_TITLE_BANK);
}

void sound_result(uint8_t winner) {
    if(sound_ready) sound_stop();
    music(winner == 1 ? MUSIC_VICTORY_BANK : winner == 2 ? MUSIC_DEFEAT_BANK : 0);
    if(winner == 3) sound_sfx(SFX_BATTLE_TIE);
}

void sound_toggle_music(void) {
    if(!sound_ready) return;
    sound_music_enabled = !sound_music_enabled;
    if(sound_music_enabled) {
        if(sound_music_bank) sound_music(sound_music_bank);
    } else sound_stop_music();
}

void sound_toggle_effects(void) {
    if(!sound_ready) return;
    sound_effects_enabled = !sound_effects_enabled;
    if(!sound_effects_enabled) sound_stop_effects();
}
