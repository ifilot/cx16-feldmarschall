EMU ?= $(abspath ../x16-emulator/build/x16emu)
ROM ?= $(abspath $(firstword $(wildcard ../emulator/rom.bin ../emulator-win/rom.bin) ../emulator/rom.bin))
EMU_FLAGS ?= -scale 2 -joy1

.PHONY: all run dist site test-dist test-colors test-flow test-variants test-endings test-sound test-controls test-demo test-panel test-menus screenshots check test-ai test-ai-levels autoplay native clean

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

# The game consumes one qualified release. Research and tournaments live in
# the independent feldmarschall-ai repository.
PYTHON ?= python3
HOSTCC ?= gcc
AI_ID := $(shell $(PYTHON) -c 'import json; print(json.load(open("ai-release/manifest.json"))["id"])')
AI_NATIVE_FLAGS := $(shell $(PYTHON) -c 'import json; print(" ".join("-D"+f for f in json.load(open("ai-release/manifest.json"))["policy"]["defines"]))')
CORE = $(addprefix src/core/,pieces.c board.c rules.c setup.c random.c ai_deploy.c ai.c ai_level.c ai_mission.c ai_memory.c ai_student.c ai_template.c)
NATIVE_FLAGS = -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow $(AI_NATIVE_FLAGS) -Isrc/core

.PHONY: native check test-ai test-ai-levels test-ai-release verify-ai-release clean
verify-ai-release:
	$(PYTHON) tools/ai_release.py verify
native: verify-ai-release build/feldmarschall-engine
build/feldmarschall-engine: Makefile src/native/engine.c $(CORE) $(wildcard src/core/*.h) ai-release/manifest.json
	mkdir -p build
	$(HOSTCC) $(NATIVE_FLAGS) -DFELDMARSCHALL_AI_ID='"$(AI_ID)"' -o $@ src/native/engine.c $(CORE)

check: verify-ai-release build/rules-test build/native-info-test
	$(PYTHON) tools/check_presets.py
	build/rules-test
	build/native-info-test
	$(PYTHON) tools/test_ai_release.py
	$(PYTHON) tools/test_ai_release_import.py

test-ai test-ai-release: verify-ai-release
	$(PYTHON) tools/test_ai_release.py
	$(PYTHON) tools/test_ai_release_import.py

test-ai-levels: all
	$(PYTHON) tools/test_ai_levels.py

build/native-info-test: Makefile tests/native_info_test.c src/native/engine.c $(CORE) $(wildcard src/core/*.h) ai-release/manifest.json
	mkdir -p build
	$(HOSTCC) $(NATIVE_FLAGS) -o $@ tests/native_info_test.c $(CORE)
build/rules-test: Makefile tests/rules_test.c src/core/rules.c src/core/board.c src/core/pieces.c src/core/ai.c src/core/ai_level.c src/core/random.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Isrc/core -o $@ tests/rules_test.c src/core/rules.c src/core/board.c src/core/pieces.c src/core/ai.c src/core/ai_level.c src/core/random.c

autoplay: all
	$(PYTHON) tools/autoplay.py --emu "$(EMU)" --rom "$(ROM)" --turns 150
clean:
	$(MAKE) -C src clean
	rm -rf build tools/__pycache__ assets/scripts/__pycache__
