# Engine protocol

The referee (`tools/arena.py`) plays games between programs that speak this
protocol. A program reads one command per line on standard input and writes
its replies on standard output, one per line, flushing after each. The
game's own computer player speaks it as `build/stratego-engine` (`make
native`); `tools/bots.py` shows how a program in another language joins in.

Stratego is a game of hidden information, so the referee keeps the true
position. An engine only learns what its army may know: its own pieces,
the moves of both armies, and the ranks revealed in battles.

## Conventions

* **Squares** are a column `a`–`j` and a rank `1`–`10`, as engraved on the
  board: rank 1 is Red's back row, rank 10 is Blue's. The lakes are c5, d5,
  c6, d6, g5, h5, g6 and h6.
* **Ranks** are single glyphs: `1` Marshal, `2` General, `3` Colonel,
  `4` Major, `5` Captain, `6` Lieutenant, `7` Sergeant, `8` Miner,
  `9` Scout, `S` Spy, `B` Bomb and `F` Flag.
* **A deployment** is 40 glyphs: the army's front row first (rank 4 for
  Red, rank 7 for Blue), then the rows behind it, each from column a to j.
  It holds 1, 1, 2, 3, 4, 4, 4, 5, 8, 1, 6 and 1 pieces of the ranks above.

## Commands

| Command | Reply | Meaning |
| --- | --- | --- |
| `stratego` | `id name …`, `id author …`, `ok` | Sent once at start; the referee waits for `ok`. |
| `isready` | `readyok` | Synchronise. |
| `seed <n>` | | Seed the engine's random choices (for reproducible games). |
| `new red` / `new blue` | | Start a game playing this army. The enemy's 40 pieces stand unknown on its home rows. |
| `setup <40 glyphs>` | | The engine's deployment, chosen by the referee. |
| `setup` | `setup <40 glyphs>` | The engine chooses its own deployment. |
| `go` | `move <from> <to>` or `move none` | The engine's turn. |
| `moved <from> <to>` | | A quiet move by either army, including the engine's own. |
| `battle <from> <to> <attacker> <defender>` | | An attack by either army, with both ranks revealed. |
| `quit` | | End the program. |

An unknown command or malformed argument may be answered with a line that
starts with `error`.

After every move, both engines hear what happened, the mover included:
`moved d4 d5` or `battle d4 d5 7 9`. The outcome of a battle follows from
the two ranks:

* The lower rank number wins; equal ranks both fall.
* A Miner defuses a Bomb, which defeats every other attacker.
* The Spy defeats the Marshal when it attacks, and loses every other battle.
* Any attacker captures the Flag, which ends the game.

The winner of an attack takes the square; a Bomb or other defender that
wins stays put. Both pieces in a battle are revealed and stay known to both
players. A piece that moves more than one square is a Scout, and is known
as one from then on.

## Moves and the end of a game

Pieces move one square up, down, left or right, onto an empty square or an
enemy piece, never into a lake. Scouts move any distance in a straight line
over empty squares and may attack the first enemy piece on that line. Bombs
and Flags never move. Red moves first.

**The two-squares rule:** a piece may not move more than five times in a
row between the same two squares, whatever the opponent does; attacks
count too. Another move of the same army ends the series. A Scout may
still move past the square it is barred from.

A game ends when a Flag is captured, when the army to move has no legal
move (it loses), or as a draw after the referee's ply limit
(`--max-plies`, 1000 by default). A move that is not legal loses the game.
The "more-squares rule" against chasing a piece endlessly is not enforced.

## An example

```
> stratego
< id name cx16-stratego
< id author Ivo Filot
< ok
> seed 7
> new red
> setup 94959969496271358975B869753SB8FB8B748B6B
> go
< move <from> <to>
> moved i4 i5
> moved b7 b6
> go
< move <from> <to>
> battle i5 i6 4 8
```

Lines marked `>` go to the engine, `<` come back. The referee answers
every `go` by telling both engines what happened; here Red's Major moves
from i4 to i5 and later defeats a Blue Miner on i6.

## Testing commands

`build/stratego-engine` also answers `think <army> <seed> <lost> <view>`:
the move it would choose from a raw position, given as hexadecimal bytes in
the encoding of `src/core` (`board.h`, `pieces.h`), with fresh random state.
It replies `best <from> <to>` as square numbers 0–99 (rank 10 first). The
parity test (`tools/parity.py`) sends the same positions to `BRIDGE.PRG`
on the X16 and checks that both builds choose the same moves. With the
environment variable `STRATEGO_TRACE` set, and the engine compiled with
`-DAI_TRACE`, `think` first lists every candidate move with its score.
