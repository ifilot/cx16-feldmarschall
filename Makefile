EMU ?= $(abspath ../x16-emulator/build/x16emu)
ROM ?= $(abspath $(firstword $(wildcard ../emulator/rom.bin ../emulator-win/rom.bin) ../emulator/rom.bin))
EMU_FLAGS ?= -scale 2 -joy1

.PHONY: all run dist site test-dist test-colors test-flow test-variants test-endings test-sound test-controls test-demo test-panel test-menus screenshots check test-ai test-ai-levels benchmark-ai benchmark-ai-levels autoplay native native-baseline native-planned compare-ai bridge-planned rating parity clean

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
CORE_NATIVE = $(addprefix src/core/,pieces.c board.c rules.c setup.c random.c ai.c ai_level.c ai_deploy.c)
CORE_MISSIONS = $(CORE_NATIVE) src/core/ai_mission.c
CORE_MEMORY = $(CORE_MISSIONS) src/core/ai_memory.c
CORE_PRODUCTION = $(CORE_MEMORY) src/core/ai_student.c
AI_PRODUCTION_FLAGS = -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_STUDENT_PRODUCTION -DAI_STUDENT_COOP_GUARD

.PHONY: native-teacher-rollout native-teacher-observer
.PHONY: native-student-v2 test-ai-student-v2
AI_STUDENT_V2_DIR ?= build/ai-student/rollout-v2-r1
native-student-v2: build/feldmarschall-engine-student-v2
build/feldmarschall-engine-student-v2: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_V2_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -I$(AI_STUDENT_V2_DIR) -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c
test-ai-student-v2: build/ai-student-v2-test
	build/ai-student-v2-test
build/ai-student-v2-test: tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_V2_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -I$(AI_STUDENT_V2_DIR) -Isrc/core -o $@ tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c
.PHONY: native-student-v2-diagnostics native-student-v3 test-ai-student-v3
.PHONY: native-student-quiet-guard test-ai-student-quiet-guard
native-student-quiet-guard: build/feldmarschall-student-quiet-guard
build/feldmarschall-student-quiet-guard: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_V2_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_STUDENT_QUIET_LIMIT=0 -DAI_DIAGNOSTICS -I$(AI_STUDENT_V2_DIR) -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c
test-ai-student-quiet-guard: build/ai-student-quiet-guard-test
	build/ai-student-quiet-guard-test
build/ai-student-quiet-guard-test: tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_V2_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_STUDENT_QUIET_LIMIT=0 -I$(AI_STUDENT_V2_DIR) -Isrc/core -o $@ tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c
native-student-v2-diagnostics: build/feldmarschall-student-v2-diagnostics
build/feldmarschall-student-v2-diagnostics: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_V2_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_DIAGNOSTICS -I$(AI_STUDENT_V2_DIR) -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c
AI_STUDENT_V3_DIR ?= build/ai-student/balanced-context-v3
.PHONY: native-student-coop-guard test-ai-student-coop-guard
AI_STUDENT_BALANCED_DIR ?= build/ai-student/balanced-v2
native-student-coop-guard: build/feldmarschall-student-coop-guard
build/feldmarschall-student-coop-guard: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_BALANCED_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_STUDENT_COOP_GUARD -DAI_DIAGNOSTICS -I$(AI_STUDENT_BALANCED_DIR) -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c
test-ai-student-coop-guard: build/ai-student-coop-guard-test
	build/ai-student-coop-guard-test
build/ai-student-coop-guard-test: tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_BALANCED_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_STUDENT_COOP_GUARD -I$(AI_STUDENT_BALANCED_DIR) -Isrc/core -o $@ tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c
native-student-v3: build/feldmarschall-engine-student-v3
build/feldmarschall-engine-student-v3: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_V3_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_STUDENT_CONTEXT -I$(AI_STUDENT_V3_DIR) -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c
test-ai-student-v3: build/ai-student-v3-test
	build/ai-student-v3-test
build/ai-student-v3-test: tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h) $(AI_STUDENT_V3_DIR)/ai_student_model_v2.h
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_STUDENT_V2 -DAI_STUDENT_CONTEXT -I$(AI_STUDENT_V3_DIR) -Isrc/core -o $@ tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c
.PHONY: test-teacher-rollout
.PHONY: test-teacher-student-inputs
.PHONY: test-teacher-corpus test-student-context
test-teacher-corpus:
	python3 tools/test_teacher_corpus.py
test-student-context: native-teacher-rollout native-teacher-observer native-teacher-observer-context
	python3 tools/test_student_context.py
test-teacher-student-inputs: native-teacher-rollout native-teacher-observer
	python3 tools/test_teacher_student_inputs.py
test-teacher-rollout: native-teacher-rollout native-teacher-observer
	python3 tools/test_teacher_rollout.py
native-teacher-rollout: build/feldmarschall-teacher-rollout
build/feldmarschall-teacher-rollout: src/native/teacher_rollout.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_DIAGNOSTICS -Isrc/core -o $@ src/native/teacher_rollout.c $(CORE_MISSIONS)
native-teacher-observer: build/feldmarschall-teacher-observer
build/feldmarschall-teacher-observer: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_DIAGNOSTICS -DAI_TRACE -DAI_TRAINING -DAI_FEATURE_TRACE -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c

.PHONY: native-teacher-observer-context
native-teacher-observer-context: build/feldmarschall-teacher-observer-context
build/feldmarschall-teacher-observer-context: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_DIAGNOSTICS -DAI_TRACE -DAI_TRAINING -DAI_FEATURE_TRACE -DAI_STUDENT_CONTEXT -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c

.PHONY: native-mission-progress test-ai-mission-progress
.PHONY: test-ai-diagnostic-history
test-ai-diagnostic-history: build/ai-diagnostic-history-test
	build/ai-diagnostic-history-test
build/ai-diagnostic-history-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_DIAGNOSTICS -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)
.PHONY: test-ai-mission-cases
test-ai-mission-cases:
	python3 tools/test_ai_mission_cases.py docs/ai-mission-cases
native-mission-progress: build/feldmarschall-engine-mission-progress
build/feldmarschall-engine-mission-progress: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_DIAGNOSTICS -DAI_MISSION_PROGRESS -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)
.PHONY: native-mission-diagnostics
native-mission-diagnostics: build/feldmarschall-engine-mission-diagnostics
build/feldmarschall-engine-mission-diagnostics: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_DIAGNOSTICS -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)
test-ai-mission-progress: build/ai-mission-progress-test
	build/ai-mission-progress-test
build/ai-mission-progress-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MISSION_PROGRESS -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

.PHONY: native-mission-evidence test-ai-mission-evidence
native-mission-evidence: build/feldmarschall-engine-mission-evidence
build/feldmarschall-engine-mission-evidence: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_DIAGNOSTICS -DAI_MISSION_EVIDENCE -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)
test-ai-mission-evidence: build/ai-mission-evidence-test
	build/ai-mission-evidence-test
build/ai-mission-evidence-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MISSION_EVIDENCE -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

.PHONY: native-mission-preserve native-mission-escort test-ai-mission-preserve test-ai-mission-escort
.PHONY: native-mission-scout-value test-ai-mission-scout-value
native-mission-scout-value: build/feldmarschall-engine-mission-scout-value
build/feldmarschall-engine-mission-scout-value: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_DIAGNOSTICS -DAI_MISSION_SCOUT_VALUE -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)
test-ai-mission-scout-value: build/ai-mission-scout-value-test
	build/ai-mission-scout-value-test
build/ai-mission-scout-value-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MISSION_SCOUT_VALUE -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)
native-mission-preserve: build/feldmarschall-engine-mission-preserve
native-mission-escort: build/feldmarschall-engine-mission-escort
build/feldmarschall-engine-mission-preserve: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_DIAGNOSTICS -DAI_MISSION_PRESERVE -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)
build/feldmarschall-engine-mission-escort: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_DIAGNOSTICS -DAI_MISSION_ESCORT -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)
test-ai-mission-preserve: build/ai-mission-preserve-test
	build/ai-mission-preserve-test
test-ai-mission-escort: build/ai-mission-escort-test
	build/ai-mission-escort-test
build/ai-mission-preserve-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MISSION_PRESERVE -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)
build/ai-mission-escort-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MISSION_ESCORT -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

.PHONY: native-student test-ai-student native-student-features
native-student: build/feldmarschall-engine-student
native-student-features: build/feldmarschall-engine-student-features
build/feldmarschall-engine-student-features: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -DAI_FEATURE_TRACE -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c
test-ai-student: build/ai-student-test
	build/ai-student-test
build/feldmarschall-engine-student: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c
build/ai-student-test: tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MEMORY -DAI_STUDENT -Isrc/core -o $@ tests/ai_test.c $(CORE_MEMORY) src/core/ai_student.c

.PHONY: native-teacher native-features test-ai-teacher
test-ai-teacher: native-teacher native-features
	python3 tools/test_ai_teacher.py
native-teacher: build/feldmarschall-teacher
native-features: build/feldmarschall-engine-features
build/feldmarschall-teacher: src/native/teacher.c src/core/pieces.c src/core/board.c src/core/rules.c src/core/random.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Isrc/core -o $@ src/native/teacher.c src/core/pieces.c src/core/board.c src/core/rules.c src/core/random.c
build/feldmarschall-engine-features: src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_MISSIONS -DAI_MEMORY -DAI_TRACE -DAI_TRAINING -DAI_FEATURE_TRACE -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY) src/core/ai_student.c

.PHONY: native-memory test-ai-memory
native-memory: build/feldmarschall-engine-memory
test-ai-memory: build/ai-memory-test build/ai-memory-fair-test
	build/ai-memory-test
	build/ai-memory-fair-test

build/feldmarschall-engine-memory: src/native/engine.c $(CORE_MEMORY) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_MEMORY -Isrc/core -o $@ src/native/engine.c $(CORE_MEMORY)

build/ai-memory-test: tests/ai_memory_test.c $(CORE_MEMORY) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MEMORY -Isrc/core -o $@ tests/ai_memory_test.c $(CORE_MEMORY)

build/ai-memory-fair-test: tests/ai_test.c $(CORE_MEMORY) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_MEMORY -Isrc/core -o $@ tests/ai_test.c $(CORE_MEMORY)

.PHONY: native-inference test-ai-inference
native-inference: build/feldmarschall-engine-inference
test-ai-inference: build/ai-inference-test
	build/ai-inference-test

build/feldmarschall-engine-inference: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_OCCUPANCY_BELIEFS -DAI_PURPOSEFUL_PROBES -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)

build/ai-inference-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_OCCUPANCY_BELIEFS -DAI_PURPOSEFUL_PROBES -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

.PHONY: native-beliefs test-ai-beliefs
native-beliefs: build/feldmarschall-engine-beliefs
test-ai-beliefs: build/ai-beliefs-test
	build/ai-beliefs-test

build/feldmarschall-engine-beliefs: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_OCCUPANCY_BELIEFS -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)

build/ai-beliefs-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_OCCUPANCY_BELIEFS -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

.PHONY: native-probes test-ai-probes
native-probes: build/feldmarschall-engine-probes
test-ai-probes: build/ai-probes-test
	build/ai-probes-test

build/feldmarschall-engine-probes: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_PURPOSEFUL_PROBES -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)

build/ai-probes-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_PURPOSEFUL_PROBES -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

.PHONY: native-exchanges test-ai-exchanges
native-exchanges: build/feldmarschall-engine-exchanges
test-ai-exchanges: build/ai-exchanges-test
	build/ai-exchanges-test

build/feldmarschall-engine-exchanges: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_LOCAL_EXCHANGES -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)

build/ai-exchanges-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_LOCAL_EXCHANGES -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

.PHONY: native-sector native-capability test-ai-sector test-ai-capability
native-sector: build/feldmarschall-engine-sector
native-capability: build/feldmarschall-engine-capability

build/feldmarschall-engine-sector: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_SECTOR_MEMORY -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)

build/feldmarschall-engine-capability: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -DAI_CAPABILITY_VALUES -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)

test-ai-sector: build/ai-sector-test
	build/ai-sector-test
test-ai-capability: build/ai-capability-test
	build/ai-capability-test

build/ai-sector-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_SECTOR_MEMORY -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

build/ai-capability-test: tests/ai_test.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST -DAI_MISSIONS -DAI_CAPABILITY_VALUES -Isrc/core -o $@ tests/ai_test.c $(CORE_MISSIONS)

native: build/feldmarschall-engine

.PHONY: native-missions test-ai-missions
native-missions: build/feldmarschall-engine-missions

build/feldmarschall-engine-missions: src/native/engine.c $(CORE_NATIVE) src/core/ai_mission.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -Isrc/core -o $@ src/native/engine.c $(CORE_NATIVE) src/core/ai_mission.c

test-ai-missions: all build/ai-mission-test
	build/ai-mission-test
	python3 tools/test_ai_missions.py

build/ai-mission-test: tests/ai_test.c $(CORE_NATIVE) src/core/ai_mission.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_MISSIONS -DAI_TEST -Isrc/core -o $@ tests/ai_test.c $(CORE_NATIVE) src/core/ai_mission.c

native-trace: build/feldmarschall-engine-trace

build/feldmarschall-engine-trace: src/native/engine.c $(CORE_MISSIONS) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_TRACE -DAI_MISSIONS -Isrc/core -o $@ src/native/engine.c $(CORE_MISSIONS)

# Frozen three-level milestone before endgame improvements.
native-milestone: build/feldmarschall-ai-20261014

build/feldmarschall-ai-20261014: src/native/engine.c tests/baselines/ai_levels_20261014.c tests/baselines/ai_level_20261014.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -Isrc/core -o $@ src/native/engine.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) tests/baselines/ai_levels_20261014.c tests/baselines/ai_level_20261014.c

.PHONY: native-milestone native-trace benchmark-ai-progress
.PHONY: native-progress-baseline
native-progress-baseline: build/feldmarschall-ai-normal-progress

build/feldmarschall-ai-normal-progress: src/native/engine.c tests/baselines/ai_normal_progress_20261014.c tests/baselines/ai_level_20261014.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -Isrc/core -o $@ src/native/engine.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) tests/baselines/ai_normal_progress_20261014.c tests/baselines/ai_level_20261014.c

.PHONY: native-adaptive-baseline
native-adaptive-baseline: build/feldmarschall-ai-adaptive-progress

build/feldmarschall-ai-adaptive-progress: src/native/engine.c tests/baselines/ai_adaptive_progress_20261014.c tests/baselines/ai_level_20261014.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -Isrc/core -o $@ src/native/engine.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) tests/baselines/ai_adaptive_progress_20261014.c tests/baselines/ai_level_20261014.c

.PHONY: native-coordinated-baseline
native-coordinated-baseline: build/feldmarschall-ai-coordinated

build/feldmarschall-ai-coordinated: src/native/engine.c tests/baselines/ai_coordinated_20261014.c tests/baselines/ai_mission_20261014.c tests/baselines/ai_level_20261014.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -DAI_MISSIONS -Isrc/core -o $@ src/native/engine.c $(filter-out src/core/ai.c src/core/ai_level.c,$(CORE_NATIVE)) tests/baselines/ai_coordinated_20261014.c tests/baselines/ai_mission_20261014.c tests/baselines/ai_level_20261014.c

benchmark-ai-progress: native native-coordinated-baseline
	python3 tools/benchmark_ai.py --missions $(AI_BENCHMARK_FLAGS)

build/feldmarschall-engine: src/native/engine.c $(CORE_PRODUCTION) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow $(AI_PRODUCTION_FLAGS) -Isrc/core -o $@ src/native/engine.c $(CORE_PRODUCTION)

# Previous planned evaluator, used to prove Normal optimizations preserve choices.
native-planned: build/feldmarschall-ai-planned

build/feldmarschall-ai-planned: src/native/engine.c tests/baselines/ai_planned.c $(filter-out src/core/ai.c,$(CORE_NATIVE)) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -Isrc/core -o $@ src/native/engine.c $(filter-out src/core/ai.c,$(CORE_NATIVE)) tests/baselines/ai_planned.c

bridge-planned: build/BRIDGE-PLANNED.PRG

build/BRIDGE-PLANNED.PRG: src/bridge/bridge.c tests/baselines/ai_planned.c $(filter-out src/core/ai.c,$(CORE_NATIVE)) $(wildcard src/core/*.h)
	mkdir -p build
	cl65 -O -t cx16 -Isrc/core -o $@ src/bridge/bridge.c $(filter-out src/core/ai.c,$(CORE_NATIVE)) tests/baselines/ai_planned.c

compare-ai: native native-planned
	python3 tools/compare_ai.py

# Frozen pre-upgrade implementation, compiled with the same rules and host flags.
native-baseline: build/feldmarschall-ai-v020

build/feldmarschall-ai-v020: src/native/engine.c tests/baselines/ai_v020.c $(filter-out src/core/ai.c,$(CORE_NATIVE)) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow -Isrc/core -o $@ src/native/engine.c $(filter-out src/core/ai.c,$(CORE_NATIVE)) tests/baselines/ai_v020.c

test-ai: build/ai-test
	build/ai-test

build/ai-test: tests/ai_test.c $(CORE_PRODUCTION) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -DAI_TEST $(AI_PRODUCTION_FLAGS) -Isrc/core -o $@ tests/ai_test.c $(CORE_PRODUCTION)

test-ai-levels: all
	python3 tools/test_ai_levels.py

benchmark-ai-levels: native
	python3 tools/benchmark_ai.py --levels --rounds 200 $(AI_BENCHMARK_FLAGS)

# Independent, paired comparisons against the frozen v0.2.0 AI.
benchmark-ai: native native-baseline
	python3 tools/benchmark_ai.py $(AI_BENCHMARK_FLAGS)

.PHONY: test-ai-benchmark benchmark-ai-broad test-ai-diagnostics verify-ai-archives
test-ai-benchmark:
	python3 tools/test_benchmark_setups.py

benchmark-ai-broad: native native-baseline native-planned native-adaptive-baseline test-ai-benchmark
	python3 tools/benchmark_ai.py --suite broad --league --record-moves $(AI_BENCHMARK_FLAGS)

test-ai-diagnostics:
	python3 tools/test_ai_diagnostics.py docs/ai-diagnostics/positions-20261014.zip

verify-ai-archives:
	python3 tools/verify_ai_archives.py

.PHONY: test-ai-deployments optimize-ai-deployments
.PHONY: test-ai-selection test-ai-selection-banked benchmark-ai-selection
test-ai-selection:
	python3 tools/test_ai_selection.py
test-ai-selection-banked: all
	python3 tools/test_ai_selection_banked.py
benchmark-ai-selection: native native-coordinated-baseline native-baseline native-planned native-adaptive-baseline test-ai-selection
	python3 tools/benchmark_ai_selection.py $(AI_SELECTION_FLAGS)
test-ai-deployments:
	python3 tools/test_ai_deployments.py
optimize-ai-deployments: native native-coordinated-baseline native-baseline native-planned native-adaptive-baseline test-ai-deployments
	python3 tools/optimize_ai_deployments.py --out build/ai-deployments/search $(AI_DEPLOYMENT_FLAGS)

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
check: build/rules-test build/ai-test build/native-info-test
	python3 tools/check_presets.py
	build/rules-test
	build/ai-test
	build/native-info-test

build/native-info-test: tests/native_info_test.c src/native/engine.c $(CORE_PRODUCTION) $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Wno-format-overflow $(AI_PRODUCTION_FLAGS) -Isrc/core -o $@ tests/native_info_test.c $(CORE_PRODUCTION)

build/rules-test: tests/rules_test.c src/core/rules.c src/core/board.c src/core/pieces.c src/core/ai.c src/core/ai_level.c src/core/random.c $(wildcard src/core/*.h)
	mkdir -p build
	$(HOSTCC) -O2 -std=c99 -Wall -Wno-unknown-pragmas -Isrc/core -o $@ tests/rules_test.c \
		src/core/rules.c src/core/board.c src/core/pieces.c src/core/ai.c src/core/ai_level.c src/core/random.c

# a long game of random red moves against the computer
autoplay: all
	python3 tools/autoplay.py --emu "$(EMU)" --rom "$(ROM)" --turns 150

clean:
	$(MAKE) -C src clean
	rm -rf build tools/__pycache__ assets/scripts/__pycache__
