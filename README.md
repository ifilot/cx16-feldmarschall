# CX16-FELDMARSCHALL

[![build](https://github.com/ifilot/cx16-feldmarschall/actions/workflows/build.yml/badge.svg)](https://github.com/ifilot/cx16-feldmarschall/actions/workflows/build.yml)
[![GitHub Pages](https://github.com/ifilot/cx16-feldmarschall/actions/workflows/pages.yml/badge.svg)](https://ifilot.github.io/cx16-feldmarschall/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

**[Play it in your browser](https://ifilot.github.io/cx16-feldmarschall/)**, or
download `FELDMARSCHALL.ZIP` from the
[releases](https://github.com/ifilot/cx16-feldmarschall/releases).

Feldmarschall is a Stratego-style game for the **Commander X16**, with a
look inspired by Accolade’s 1990 game. Command an army of 40 pieces, discover
your opponent’s hidden ranks and capture their flag.

![Playing against the computer](docs/play.png)

## Contents

- [Getting started](#getting-started)
- [Controls](#controls)
- [Preparing your army](#preparing-your-army)
- [Playing and winning](#playing-and-winning)
- [Optional rules](#optional-rules)
- [Saving and loading](#saving-and-loading)
- [Appearance and sound](#appearance-and-sound)
- [Demo](#demo)
- [Building from source](#building-from-source)
- [Credits and license](#credits-and-license)

## Getting started

Play in your browser using the link above, or download and extract
`FELDMARSCHALL.ZIP`. Keep all the extracted game files together.

On a **Commander X16**, copy the package contents to the root of your SD card
to start automatically through `AUTOBOOT.X16`. You can also load and run
`FELDMARS.PRG` yourself. Use ROM R47 or later for gamepad support.

In the **desktop X16 emulator**, open `FELDMARS.PRG` from the extracted game
folder, or run this command from that folder:

```sh
x16emu -prg FELDMARS.PRG -run
```

Press **Enter** at the title screen. To play your first match:

1. Choose **Skirmish**.
2. Choose a difficulty. Leave the optional rules off for a Classic game.
3. Choose **Continue**, then **Random** to place your army.
4. Choose **Start** and drag a piece to make your first move.

The main menu also offers **Setups** to prepare armies, **Load game**,
**Options**, **About**, **Demo** and **Exit**. Exit returns to the command line.

## Controls

| Action | Mouse | Keyboard / gamepad |
| --- | --- | --- |
| Choose a menu item | Click | Arrow keys, then Enter; number shortcuts also work |
| Move or place a piece | Drag and release | Gamepad D-pad moves the pointer; hold A to drag |
| Go back or pause a match | Click Back or Menu | Escape; gamepad B or Select |
| Confirm | Click the button | Enter; gamepad Start |

Gamepads on ports 1–4 share the pointer. Hold **X** for fine movement or **Y**
for faster movement. In the desktop emulator, enable the controller port
(for example, with `-joy1`).

## Preparing your army

You play from the bottom of the board, normally as Red. Place all 40 pieces
on your four home rows. Drag pieces from the tray, swap two pieces by dropping
one onto the other, or drag a piece back to the tray.

| Button | Key | What it does |
| --- | --- | --- |
| New | N | Return every piece to the tray |
| Load | L | Choose a built-in or saved setup |
| Save | S | Name your complete setup and save it in one of ten slots |
| Random | R | Place the whole army, with a guarded flag |
| Start / Back | Enter | Start the match, or leave the Setups screen |

There are ten built-in setups to try. In the Load list, point at a name or
use the arrow keys to preview it. Click or press Enter to accept; Escape
cancels. Saving to an occupied slot replaces its previous setup.

**Start** and **Save** require a complete army. A layout prepared in **Setups**
is kept for your next Skirmish.

## Playing and winning

Drag one of your pieces to move it. Gold dots show empty squares it can
reach; drop it onto an enemy piece to attack. The computer then takes its turn.

- Pieces move one square horizontally or vertically. They cannot enter lakes
  or jump over other pieces.
- Scouts can move and attack any distance along a clear straight line.
- Bombs and flags stay in place.
- The stronger rank wins a battle. Equal ranks both fall.
- A Miner defeats a Bomb; every other attacker loses to it.
- A Spy defeats a Marshal when the Spy attacks. It loses when attacked by
  the Marshal and against other moving ranks.
- A piece may move between the same two squares at most five times in a row.

By default, **1 is the Marshal**, the strongest rank, and **9 is the Scout**.
The Spy is **S**. Options also offers modern numbering, from **1 Spy** to
**10 Marshal**.

Enemy ranks are hidden until battle. Surviving enemies turn face down again,
so remember what you have seen. The tray shows captured enemy pieces.
The computer also remembers revealed pieces and uses public clues; it does
not receive your hidden ranks or setup. Choose Easy, Normal or Hard in the
new-game settings. See the [AI release report](docs/ai-release.md) for details.

**Capture the enemy flag or leave the enemy without a legal move to win.**
If neither army can move after a battle, the game is a draw. The result screen
lets you start again, inspect the revealed board or return to the main menu.

## Optional rules

Before a Skirmish, click a rule or press **1–6** to toggle it. Choose
**Classic** (or press **C**) to turn all variants off.

| Rule | Change |
| --- | --- |
| Attacker's Advantage | The attacker survives when equal ranks meet. |
| Silent Defense | A defender’s rank stays secret unless a Scout attacks it. Ranks already revealed remain known. |
| Exploding Bombs | A Bomb and its attacker both fall, unless a Miner defuses it. |
| Moving Bombs | Bombs can move one square but cannot attack. Also enables Exploding Bombs. |
| Moving Flag | Flags can move one square but cannot attack. Moving your flag to the enemy back row also wins. |
| Rescue | Reach the enemy back row to return a captured piece to an empty home square. Each army gets two rescues; each rescuing piece can rescue once. Scouts cannot rescue, and Bombs cannot return. |

When offered a rescue, choose a casualty from the tray, then an empty square
in your home rows. Enter or Escape skips it.

## Saving and loading

Press **Escape** or choose **Menu** during a match. Choose **Save game** to
store the current game, then use **Load game** from the main menu to resume it.
There is one saved-game slot; saving again replaces it. If you pause during
a computer move or battle, the menu opens when that move finishes.

The game stores these files in its game folder:

| File | Contents |
| --- | --- |
| `GAME.DAT` | Your saved match |
| `DEPLOY.DAT` | Your named army setups |
| `COLORS.DAT` | Your appearance settings |

Keep these files when updating the game. **Quit to menu** does not save your
match automatically.

## Appearance and sound

Choose **Options** to change the battlefield, army colors and rank numbering.
Click to preview a choice, or use **Tab** to switch groups and the arrow keys
to select. Enter, Escape or Back saves your preferences.

To toggle **Music** and **Sound effects** separately, open the in-game Menu.
These sound choices last for the current session.

## Demo

Choose **Demo** to watch two computer armies play automatically. They start
with fresh random setups that differ from each other. All pieces are visible
to you; each computer still plays with hidden enemy ranks.

Escape or Menu pauses the demo. You can resume, change sound settings or
return to the main menu. Demos preserve your prepared army and saved game.
Choose **New game** on the result screen to watch another battle.

## Building from source

You need **cc65**, **GNU make 4.3+**, and **Python 3** with **Pillow** and **NumPy**.

```sh
make          # Build the game
make run      # Launch the sibling ../x16-emulator checkout
make dist     # Create build/dist/FELDMARSCHALL.ZIP
make check    # Run rules and AI release checks (also requires GCC)
```

## Credits and license

- **UnifrakturMaguntia** and **Caladea Bold** fonts, under the SIL Open Font License.
- Audio playback by [ZSMKit](https://github.com/mooinglemur/zsmkit), by
  mooinglemur, under the MIT license included in `src/vendor/zsmkit.inc`.

Feldmarschall is free software under **GPL-3.0-or-later**. See [LICENSE](LICENSE).
