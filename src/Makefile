CC=cl65
CFLAGS?=-O -t cx16 -I . -I core -I ui -I scenes
PYTHON=python3
SCRIPTS=../assets/scripts
GFX_ASSETS=L0TILES.BIN L0MAP.BIN L1TILES.BIN SPRITES.BIN PALETTE.BIN gfx.h

# core: game rules and the computer player, free of graphics
# ui: VERA, the board view, the panel and other widgets
# scenes: the screens of the game, run one at a time by main.c
SRC=$(wildcard *.c core/*.c ui/*.c scenes/*.c)
HDR=$(filter-out gfx.h,$(wildcard *.h core/*.h ui/*.h scenes/*.h))

all: STRATEGO.PRG

STRATEGO.PRG: $(SRC) $(HDR) $(GFX_ASSETS)
	$(CC) $(CFLAGS) -o $@ -m STRATEGO.map -Ln STRATEGO.sym $(SRC)

# every graphics resource derives from the portrait sheet, the font and the scripts
$(GFX_ASSETS) &: $(wildcard $(SCRIPTS)/*.py) $(wildcard ../assets/pieces/*.png) $(wildcard ../assets/font/*.png)
	$(PYTHON) $(SCRIPTS)/build_graphics.py . ../build/preview

clean:
	rm -f *.o core/*.o ui/*.o scenes/*.o *.PRG *.BIN *.map *.sym gfx.h

.PHONY: all clean
