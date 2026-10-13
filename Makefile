EMU ?= $(abspath ../x16-emulator/build/x16emu)
ROM ?= $(abspath $(firstword $(wildcard ../emulator/rom.bin ../emulator-win/rom.bin) ../emulator/rom.bin))
EMU_FLAGS ?= -scale 2 -joy1

.PHONY: all run dist site test-dist test-colors test-flow test-variants test-endings test-sound test-controls test-demo test-panel test-menus screenshots check autoplay native rating parity clean

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

# every way a game ends, through the developer scenarios (type DEV at the menu)
test-endings: all
	python3 tools/test_endings.py

test-sound: all
	python3 tools/test_sound.py

test-menus: all
	python3 tools/test_menus.py

test-panel: all
	python3 tools/test_panel.py

test-demo: all
	python3 tools/test_demo.py

test-controls: all
	python3 tools/test_controls.py

run: all
	cd src && "$(EMU)" -rom "$(ROM)" -prg FELDMARS.PRG -run $(EMU_FLAGS)

# regenerate every screenshot in docs/; About shows the date of the last commit
screenshots: export SOURCE_DATE_EPOCH := $(shell git log -1 --format=%ct 2>/dev/null)
screenshots: all
	python3 tools/screenshots.py --emu "$(EMU)" --rom "$(ROM)"

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
