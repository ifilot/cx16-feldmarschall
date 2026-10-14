"""Check optimizations against the frozen planned AI, including persistent state."""
import argparse
from feldmarschall import BLUE, RED, ROOT, Engine, GLYPHS, Position, new_rng, parse_square, random_setup, square_name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--games', type=int, default=30)
    parser.add_argument('--baseline', default=str(ROOT / 'build/feldmarschall-ai-planned'))
    parser.add_argument('--difficulty', choices=('easy', 'normal', 'hard'), default='normal',
                        help='level for both engines; use the three-level milestone for Easy/Hard')
    args = parser.parse_args()
    rng, decisions = new_rng(1234567), 0
    for game in range(args.games):
        truth, engines = Position(), []
        try:
            for army in (RED, BLUE):
                setup = random_setup(rng)
                truth.place(army, setup)
                pair = [Engine(str(ROOT / 'build/feldmarschall-engine') + ' --difficulty ' + args.difficulty, 'optimized'),
                        Engine(args.baseline + ' --difficulty ' + args.difficulty, 'baseline')]
                engines.append(pair)
                seed = rng.randrange(1, 65536)
                for engine in pair:
                    engine.send(f'seed {seed}')
                    engine.send('new ' + ('red', 'blue')[army])
                    engine.send('setup ' + setup)
            for ply in range(1000):
                army = ply % 2
                if not truth.moves(army):
                    break
                answers = [engine.ask('go', 'move') for engine in engines[army]]
                if answers[0] != answers[1]:
                    raise SystemExit(f'game {game}, ply {ply}: {answers}')
                decisions += 1
                src, dst = map(parse_square, answers[0].split())
                assert (src, dst) in truth.moves(army)
                finished = False
                if truth.cells[dst] is None:
                    truth.move(src, dst)
                    notification = f'moved {square_name(src)} {square_name(dst)}'
                else:
                    a, d = truth.cells[src][1], truth.cells[dst][1]
                    finished = d == 11
                    truth.fight(src, dst, a, d)
                    notification = f'battle {square_name(src)} {square_name(dst)} {GLYPHS[a]} {GLYPHS[d]}'
                for pair in engines:
                    for engine in pair:
                        engine.send(notification)
                if finished:
                    break
        finally:
            for pair in engines:
                for engine in pair:
                    engine.close()
    print(f'{args.games} games, {decisions} decisions: identical moves, including both armies\' goals and histories')


if __name__ == '__main__':
    main()
