# Engine protocol

The referee (`tools/arena.py`) plays games between programs that speak this
protocol. A program reads one command per line on standard input and writes
its replies on standard output, one per line, flushing after each. The
game's own computer player speaks it as `build/feldmarschall-engine` (`make
native`); `tools/bots.py` shows how a program in another language joins in.

Feldmarschall is a game of hidden information, so the referee keeps the true
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

Native builds with `AI_DIAGNOSTICS` also support `public`, returning the army,
masked board, disclosed enemy casualties and two-square state as hex strings.
After `go`, `played <from> <to>` acknowledges a different legal action with
`playedok`, correcting the proposal's goal transfer and backtracking caches.
It does not move a board piece: send the ordinary `moved` or `battle`
notification afterward. This supports forced public-history diagnostics and
desktop teacher adapters; production builds omit these commands.

| Command | Reply | Meaning |
| --- | --- | --- |
| `feldmarschall` | `id name …`, `id author …`, `ok` | Sent once at start; the referee waits for `ok`. |
| `isready` | `readyok` | Synchronise. |
| `difficulty <level>` | | Choose `easy`, `normal` or `hard`; also available as `--difficulty LEVEL` at launch. |
| `seed <n>` | | Seed the engine's random choices (for reproducible games). |
| `rules <mask>` | | Select optional rules, 0–63; preserved by `new`. |
| `new red` / `new blue` | | Start a game playing this army. The enemy's 40 pieces stand unknown on its home rows. |
| `setup <40 glyphs>` | | The engine's deployment, chosen by the referee. |
| `setup` | `setup <40 glyphs>` | The engine chooses its own deployment. |
| `go` | `move <from> <to>` or `move none` | The engine's turn. |
| `moved <from> <to>` | | A quiet move by either army, including the engine's own. |
| `battle <from> <to> <attacker> <defender>` | | An attack by either army, with both ranks revealed. |
| `combat <from> <to> <attacker> <defender-or-?> <outcome>` | | Variant observation: only permitted ranks and an observable result, `A`, `D` or `X`. |
| `reinforce <trigger> <destination> <rank-or-?> <visible>` | | A rescue; rank is private to its owner unless `visible` is 1. |
| `view` | `view <army> <board> <enemy-known-lost> <own-lost> <rescues> <shuttle>` | Audit the native or variant bot's permitted state; byte arrays are hexadecimal. |
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

## Optional rules and public observations

`tools/arena.py --rules MASK` and `tools/benchmark_ai.py --rules MASK` use the
game's C rules through `build/librules-variant.so` (`make native-variant-rules`).
Mask 0 selects the same referee for a Classic cross-check. Omitting `--rules`
retains the historical Classic referee and `battle` notifications.

| Bit | Option |
| --- | --- |
| 1 | Attacker wins equal ranks |
| 2 | Silent Defense |
| 4 | Bombs explode, removing both pieces except when defused by a Miner |
| 8 | Bombs may move quietly; an undefused Bomb also explodes |
| 16 | Flags may move quietly and win on reaching the enemy back row |
| 32 | Rescue |

Moving Bombs and Flags cannot attack. Silent Defense leaves the defender's rank
undisclosed unless a Scout attacked or the rank was already revealed. Both
players receive the same `combat` event. `A` means the attacker survives, `D`
means the defender survives, and `X` means both fall. The owner already knows
its own defender's rank, even when the event contains `?`. For example,
`combat a4 a5 5 ? D` removes the Captain without revealing the surviving defender.
The receiver must use the supplied public outcome rather than requesting the
hidden rank to resolve combat.

Rescue follows an eligible surviving mover's arrival at the enemy back row,
once per arriving piece and at most twice per army. Scouts, Bombs and Flags
cannot trigger it. The referee uses the X16 demo policy for both armies:
restore the strongest available ordinary casualty into the first vacant home
square, scanning Blue 39 down to 0 or Red 60 up to 99. Failed attacks do not
create an arrival or offer a rescue to the defender.

The owner receives the returning rank in `reinforce`; its opponent receives
`?` unless a previously disclosed casualty makes the returning rank public.
`visible=0` preserves the owner's private rank without marking it revealed.
Own casualties, disclosed enemy casualties and public rescue counters update
with these events. The native AI can therefore use legitimate own rescue
opportunities without receiving the opponent's private casualty inventory.

The audited referee compares both `view` replies with the permitted true-state
projection after every turn and at the end. Board and casualty fields contain
100, 12 and 12 bytes; rescue counters contain two bytes. The six shuttle bytes
are Red/Blue source, Red/Blue destination, then Red/Blue count. Unused
coordinates for a zero count are `ff`. `view` is a native testing command;
it is not an X16 game command or a source of extra enemy information.

Use `tools/variant_bot.py greedy` or `random` with this referee. These opponents
use masked boards and the same C move/battle rules. The historical
`tools/bots.py` opponents retain their Classic protocol.

## An example

```
> feldmarschall
< id name cx16-feldmarschall
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

`build/feldmarschall-engine` also answers `think <army> <seed> <lost> <view> [repetitions]`:
the move it would choose from a raw **masked army view**, given as hexadecimal bytes in
the encoding of `src/core` (`board.h`, `pieces.h`), with fresh random state.
It replies `best <from> <to>` as square numbers 0–99 (rank 10 first). The
parity test (`tools/parity.py`) sends the same positions to `BRIDGE.PRG`
on the X16 and checks that both builds choose the same moves. With the
environment variable `FELDMARSCHALL_TRACE` set, and the engine compiled with
`-DAI_TRACE`, `think` first lists every candidate move with its score.

The optional repetition count (1–255, default 1) repeats evaluation of the same
view without resetting AI state between calls. It is a diagnostic for persistent
state, not a game simulation. `tools/parity.py --repetitions 129` exercises
saturated quiet-turn pressure on native and X16 builds.

`rules <0..63>` selects the bitmask from `src/core/rules.h` before a `think`
request (the default is classic rules). The native information ledger honours
Silent Defense when resolving referee battles: an undisclosed defender and
its casualty rank stay unknown, unless a Scout or earlier revelation permits
disclosure. The match referee currently benchmarks classic rules only; it does
not implement the game's rescue or moving-flag victory flow.

The X16 mailbox carries difficulty at `$0476` and the rules mask at `$0477`.
For example, `python3 tools/parity.py --difficulty hard --rules 63` checks
matching native/X16 decisions with every variant enabled. Level selection is
preserved by `new`, `think`, and AI history resets.

## Original DOS reference extension

Only policies explicitly registered with `driver=msdos1990` receive
`opponent-setup <40 glyphs>` after their ordinary `setup`. This supplies the
physical board expected by the original software, including its privileged
rank access. Standard Feldmarschall policies never receive this extension.
DOS public notifications are followed by `isready` / `readyok` so an original
execution error is recorded at the event that triggers it. Such failures are
unscored schema-2 tournament records, not draws or losses. Terminal Flag
captures end the match before further AI notification is necessary.
