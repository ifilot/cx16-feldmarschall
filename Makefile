EMU ?= $(abspath ../x16-emulator/build/x16emu)
ROM ?= $(abspath $(firstword $(wildcard ../emulator/rom.bin ../emulator-win/rom.bin) ../emulator/rom.bin))
EMU_FLAGS ?= -scale 2

.PHONY: all run dist site test-dist test-colors test-flow test-variants screenshot check autoplay native rating parity clean

all:
	$(MAKE) -C src

# build/dist/FELDMARSCHALL.ZIP: the runtime files only, ready for an SD card
dist: all
	python3 tools/distribute.py

# build/site: the game in the browser, as published on GitHub Pages
site: dist
	python3 tools/build_site.py

# boot the distribution through AUTOBOOT.X16 and check that it loaded
test-dist: dist
	python3 tools/test_dist.py

test-colors: all
	python3 tools/test_colors.py

test-flow: all
	python3 tools/test_flow.py

test-variants: all
	python3 tools/test_variants.py

run: all
	cd src && "$(EMU)" -rom "$(ROM)" -prg FELDMARS.PRG -run $(EMU_FLAGS)

screenshot: all
	python3 tools/screenshot.py --emu "$(EMU)" --rom "$(ROM)" --keys "shot:docs/splash.png Return wait:120 move:150,236 wait:3 shot:docs/menu.png 1 wait:20 N wait:5 shot:docs/board-layout.png drag:452,172,196,356 drag:492,172,236,356 move:533,412 down move:300,322 wait:3 shot:docs/deploy-drag.png up wait:3 L wait:5 move:96,108 wait:5 shot:docs/deploy-load.png down wait:2 up wait:5 S wait:5 $(foreach i,1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16,Backspace) M Y Space F O R T wait:3 shot:docs/deploy-save.png Escape wait:5" --out build/screenshot.png
	python3 tools/autoplay.py --emu "$(EMU)" --rom "$(ROM)" --turns 14 --seed 3 --out docs/play.png

# the computer player as a native program speaking docs/protocol.md
HOSTCC ?= gcc
CORE_NATIVE = $(addprefix src/core/,pieces.c board.c rules.c setup.c random.c ai.c)

native: build/feldmarschall-engine

build/feldmarschall-engine: src/native/engine.c $(CORE_NATIVE) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -Isrc/core -o $@ src/native/engine.c $(CORE_NATIVE)

# Elo ratings of the computer player against the baseline bots
ROUNDS ?= 100
rating: native
	rm -f build/results.jsonl
	python3 tools/arena.py --rounds $(ROUNDS) --engine ai=build/feldmarschall-engine \
		--engine greedy="python3 tools/bots.py greedy" --engine random="python3 tools/bots.py random"
	python3 tools/rating.py

# the X16 build chooses the same moves as the native build
parity: all native
	python3 tools/parity.py --emu "$(EMU)" --rom "$(ROM)" --positions 500

# the built-in deployments are legal armies, and the rules behave
check: build/rules-test
	python3 tools/check_presets.py
	build/rules-test

build/rules-test: tests/rules_test.c src/core/rules.c src/core/board.c src/core/pieces.c src/core/ai.c src/core/random.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Isrc/core -o $@ tests/rules_test.c \
		src/core/rules.c src/core/board.c src/core/pieces.c src/core/ai.c src/core/random.c

# a long game of random red moves against the computer
autoplay: all
	python3 tools/autoplay.py --emu "$(EMU)" --rom "$(ROM)" --turns 150

clean:
	$(MAKE) -C src clean
	rm -rf build tools/__pycache__ assets/scripts/__pycache__
