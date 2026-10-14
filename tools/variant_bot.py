"""Variant-aware public-information random and greedy protocol opponents."""
import argparse
from pathlib import Path
import random
import sys

from feldmarschall import ROOT, GLYPHS, VALUES, random_setup, square_name
from variant_rules import VariantPosition


class VariantBot:
    def __init__(self, kind, library):
        self.kind=kind;self.library=library;self.rng=random.Random(1);self.army=0
        self.position=VariantPosition(library=library)

    def choose(self):
        moves=self.position.moves(self.army)
        if not moves or self.kind=='random': return self.rng.choice(moves) if moves else None
        cells=self.position.cells
        def target(move):return cells[move[1]]
        def loss(move):
            d=target(move)
            return d<254 and d&15<12 and self.position.outcome(cells[move[0]]&15,d&15)!=0
        safe=[m for m in moves if not loss(m)] or moves
        wins=[m for m in safe if target(m)<254 and target(m)&15<12]
        if wins:return max(wins,key=lambda m:(VALUES[target(m)&15],self.rng.random()))
        probes=[m for m in safe if target(m)<254 and cells[m[0]]&15 in (6,7,8)]
        if probes and self.rng.random()<.5:return self.rng.choice(probes)
        ahead=[m for m in safe if target(m)==255 and (m[1]//10<m[0]//10 if not self.army else m[1]//10>m[0]//10)]
        return self.rng.choice(ahead or safe)

    def run(self):
        for line in sys.stdin:
            words=line.split()
            if not words:continue
            command=words[0]
            if command=='feldmarschall':print('id name variant-'+self.kind+'\nok',flush=True)
            elif command=='isready':print('readyok',flush=True)
            elif command=='seed':self.rng.seed(int(words[1]))
            elif command=='rules':self.position=VariantPosition(int(words[1]),self.library)
            elif command=='new':
                self.army=int(words[1]=='blue');self.position=VariantPosition(self.position.rules,self.library)
                self.position.place(1-self.army,'?'*40,known=False)
            elif command=='setup':
                glyphs=words[1] if len(words)>1 else random_setup(self.rng)
                self.position.place(self.army,glyphs)
                if len(words)==1:print('setup '+glyphs,flush=True)
            elif command=='go':
                move=self.choose();print('move '+' '.join(map(square_name,move)) if move else 'move none',flush=True)
            elif command in ('moved','combat','reinforce'):self.position.observe(line)
            elif command=='view':print('view '+self.position.view(self.army),flush=True)
            elif command=='quit':break
            else:print('error unknown command',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind',choices=('random','greedy'))
    parser.add_argument('--rules-library',type=Path,default=ROOT/'build/librules-variant.so')
    parser.add_argument('--difficulty',default='normal')
    args=parser.parse_args();VariantBot(args.kind,args.rules_library).run()
