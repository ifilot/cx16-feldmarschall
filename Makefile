EMU ?= $(abspath ../x16-emulator/build/x16emu)
ROM ?= $(abspath $(firstword $(wildcard ../emulator/rom.bin ../emulator-win/rom.bin) ../emulator/rom.bin))
EMU_FLAGS ?= -scale 2

.PHONY: all run screenshot check autoplay clean

all:
	$(MAKE) -C src

run: all
	cd src && "$(EMU)" -rom "$(ROM)" -prg STRATEGO.PRG -run $(EMU_FLAGS)

screenshot: all
	python3 tools/screenshot.py --emu "$(EMU)" --rom "$(ROM)" --keys "move:150,236 wait:3 shot:docs/menu.png 1 wait:20 N wait:5 shot:docs/board-layout.png drag:452,172,196,356 drag:492,172,236,356 move:533,412 down move:300,322 wait:3 shot:docs/deploy-drag.png up wait:3 L wait:5 move:96,108 wait:5 shot:docs/deploy-load.png down wait:2 up wait:5 S wait:5 $(foreach i,1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16,Backspace) M Y Space F O R T wait:3 shot:docs/deploy-save.png Escape wait:5" --out build/screenshot.png
	python3 tools/autoplay.py --emu "$(EMU)" --rom "$(ROM)" --turns 14 --seed 3 --out docs/play.png

# the built-in deployments are legal armies
check:
	python3 tools/check_presets.py

# a long game of random red moves against the computer
autoplay: all
	python3 tools/autoplay.py --emu "$(EMU)" --rom "$(ROM)" --turns 150

clean:
	$(MAKE) -C src clean
	rm -rf build tools/__pycache__ assets/scripts/__pycache__
