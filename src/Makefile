CC=cl65
CFLAGS?=-O -t cx16 -I . -I core -I ui -I scenes
# cc65's default C stack is 2 KB; with static locals the game needs a few
# dozen bytes (measured: 36 in a long game), so 1 KB leaves room for code
LDFLAGS=-Wl -D,__STACKSIZE__=0x0400
LDFLAGS+=-C feldmarschall.cfg
PYTHON=python3
SCRIPTS=../assets/scripts
GFX_ASSETS=L0TILES.BIN L0MAP.BIN L1TILES.BIN SPRITES.BIN RANKTIL.BIN RANKSPR.BIN PALETTE.BIN SPLTIL.BIN SPLMAP.BIN SPLPAL.BIN gfx.h color_profiles.h
GFX_ASSETS+=$(foreach n,1 3,F$(n)TILES.BIN F$(n)MAP.BIN)
GFX_ASSETS+=WINTIL.BIN WINMAP.BIN LOSSTIL.BIN LOSSMAP.BIN DRAWTIL.BIN DRAWMAP.BIN ENDPAL.BIN

# core: game rules and the computer player, free of graphics
# ui: VERA, the board view, the panel and other widgets
# scenes: the screens of the game, run one at a time by main.c
SRC=$(wildcard *.c core/*.c ui/*.c scenes/*.c)
ASM=$(wildcard ui/*.s scenes/*.s)
SOUND_ASSETS=$(notdir $(wildcard ../assets/sound/psg/*.ZSM)) SFX.BIN music.h sfx.h
# the computer player alone, for tools/parity.py
BRIDGE_SRC=bridge/bridge.c $(filter-out core/store.c core/presets.c,$(wildcard core/*.c))
HDR=$(filter-out gfx.h color_profiles.h app_info.h,$(wildcard *.h core/*.h ui/*.h scenes/*.h))

all: FELDMARS.PRG PLAY.BIN AI.BIN MISSION.BIN BRIDGE.PRG

FELDMARS.PRG PLAY.BIN AI.BIN MISSION.BIN &: $(SRC) $(ASM) $(HDR) $(GFX_ASSETS) $(SOUND_ASSETS) app_info.h feldmarschall.cfg vendor/zsmkit.lib vendor/zsmkit.inc
	$(CC) $(CFLAGS) -D BANKED_AI -D AI_MISSIONS $(LDFLAGS) -o FELDMARS.PRG -m FELDMARS.map -Ln FELDMARS.sym $(SRC) $(ASM) vendor/zsmkit.lib

$(SOUND_ASSETS): %: ../assets/sound/psg/%
	cp $< $@

BRIDGE.PRG: $(BRIDGE_SRC) $(wildcard core/*.h)
	$(CC) -O -t cx16 -D AI_MISSIONS -I core -o $@ $(BRIDGE_SRC)

app_info.h: FORCE ../tools/build_info.py
	$(PYTHON) ../tools/build_info.py $@

FORCE:

# every graphics resource derives from the portraits, the font and the scripts
$(GFX_ASSETS) &: app_info.h $(wildcard $(SCRIPTS)/*.py) $(wildcard ../assets/pieces/*.png) $(wildcard ../assets/font/*.png) ../assets/splash/marshal.png $(wildcard ../assets/endings/*)
	$(PYTHON) $(SCRIPTS)/build_graphics.py . ../build/preview

clean:
	rm -f *.o core/*.o ui/*.o scenes/*.o bridge/*.o *.PRG *.BIN *.ZSM *.map *.sym gfx.h color_profiles.h app_info.h music.h sfx.h

.PHONY: all clean FORCE
