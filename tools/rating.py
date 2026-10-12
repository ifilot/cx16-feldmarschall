"""Elo ratings from arena results (build/results.jsonl).

Usage:
  python3 tools/rating.py [--results build/results.jsonl] [--anchor random]

Fits a Bradley-Terry model by maximum likelihood (draws count as half a
win for each side) and reports ratings on the Elo scale: a 100-point gap
means the stronger engine scores about 64%. Ratings are relative to the pool
of engines played, so the anchor (by default the random bot) is fixed at 0.
The interval is a 95% interval from the curvature of the likelihood.
"""
import argparse
import json
import math
from collections import defaultdict

from feldmarschall import ROOT

ELO = 400 / math.log(10)


def fit(games, iterations=2000):
    wins = defaultdict(float)                 # points scored
    played = defaultdict(float)               # games between each pair
    players = set()
    for g in games:
        a, b = g['red'], g['blue']
        players |= {a, b}
        played[a, b] += 1
        played[b, a] += 1
        if g['winner'] is None:
            wins[a] += 0.5
            wins[b] += 0.5
        else:
            wins[g['winner']] += 1
    players = sorted(players)
    # minorisation-maximisation (Hunter 2004), with one virtual draw against
    # a player of strength 1 so that unbeaten or winless engines stay finite
    strength = {p: 1.0 for p in players}
    for _ in range(iterations):
        for p in players:
            denominator = sum(played[p, q] / (strength[p] + strength[q]) for q in players if q != p)
            strength[p] = (wins[p] + 0.5) / (denominator + 1 / (strength[p] + 1))
        scale = math.exp(sum(math.log(s) for s in strength.values()) / len(players))
        strength = {p: s / scale for p, s in strength.items()}
    return players, strength, wins, played


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', default=str(ROOT / 'build/results.jsonl'))
    parser.add_argument('--anchor', default='random')
    args = parser.parse_args()

    games = [json.loads(line) for line in open(args.results) if line.strip()]
    players, strength, wins, played = fit(games)
    anchor = ELO * math.log(strength[args.anchor]) if args.anchor in strength else 0
    print(f'{len(games)} games, {len(players)} engines; {args.anchor} = 0\n')
    print(f'{"engine":12s} {"elo":>6s} {"95%":>6s} {"games":>6s} {"score":>6s}')
    for p in sorted(players, key=lambda p: -strength[p]):
        n = sum(played[p, q] for q in players if q != p)
        information = sum(played[p, q] * strength[p] * strength[q] / (strength[p] + strength[q]) ** 2
                          for q in players if q != p)
        error = 1.96 * ELO / math.sqrt(information) if information else float('inf')
        elo = ELO * math.log(strength[p]) - anchor
        print(f'{p:12s} {elo:6.0f} {"±%d" % error:>6s} {int(n):6d} {100 * wins[p] / n:5.1f}%')
    reasons = defaultdict(int)
    for g in games:
        reasons['illegal move' if g['reason'].startswith('illegal') else g['reason']] += 1
    print('\nendings: ' + ', '.join(f'{k} {v}' for k, v in sorted(reasons.items())))


if __name__ == '__main__':
    main()
