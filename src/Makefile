CC=cl65
CFLAGS?=-O -t cx16 -I . -I core -I ui -I scenes
PYTHON=python3
SCRIPTS=../assets/scripts
GFX_ASSETS=L0TILES.BIN L0MAP.BIN L1TILES.BIN SPRITES.BIN PALETTE.BIN MNTILES.BIN MNMAP.BIN MNL1TIL.BIN MN1MAP.BIN MNPAL.BIN SPLASH0.BIN SPLASH1.BIN SPLPAL.BIN gfx.h color_profiles.h
GFX_ASSETS+=$(foreach n,1 3,F$(n)TILES.BIN F$(n)MAP.BIN)

# core: game rules and the computer player, free of graphics
# ui: VERA, the board view, the panel and other widgets
# scenes: the screens of the game, run one at a time by main.c
SRC=$(wildcard *.c core/*.c ui/*.c scenes/*.c)
# the computer player alone, for tools/parity.py
BRIDGE_SRC=bridge/bridge.c $(filter-out core/store.c core/presets.c,$(wildcard core/*.c))
HDR=$(filter-out gfx.h color_profiles.h app_info.h,$(wildcard *.h core/*.h ui/*.h scenes/*.h))

all: FELDMARS.PRG BRIDGE.PRG

FELDMARS.PRG: $(SRC) $(HDR) $(GFX_ASSETS) app_info.h
	$(CC) $(CFLAGS) -o $@ -m FELDMARS.map -Ln FELDMARS.sym $(SRC)

BRIDGE.PRG: $(BRIDGE_SRC) $(wildcard core/*.h)
	$(CC) -O -t cx16 -I core -o $@ $(BRIDGE_SRC)

app_info.h: FORCE ../tools/build_info.py
	$(PYTHON) ../tools/build_info.py $@

FORCE:

# every graphics resource derives from the portraits, the font and the scripts
$(GFX_ASSETS) &: $(wildcard $(SCRIPTS)/*.py) $(wildcard ../assets/pieces/*.png) $(wildcard ../assets/font/*.png) ../assets/splash/feldmarschall.png $(wildcard ../assets/menu/*.png)
	$(PYTHON) $(SCRIPTS)/build_graphics.py . ../build/preview

clean:
	rm -f *.o core/*.o ui/*.o scenes/*.o bridge/*.o *.PRG *.BIN *.map *.sym gfx.h color_profiles.h app_info.h

.PHONY: all clean FORCE
