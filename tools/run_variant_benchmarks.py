"""Run predeclared, matched variant leagues for Normal and Hard."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from feldmarschall import ROOT

RULES=[1,2,4,8,16,32,3,10,48,63,0]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--rounds',type=int,default=10)
    parser.add_argument('--seed-offset',type=int,required=True)
    parser.add_argument('--phase',choices=('diagnostic','validation'),required=True)
    parser.add_argument('--rules',type=int,nargs='+',default=RULES)
    parser.add_argument('--jobs',type=int,default=4)
    args=parser.parse_args()
    if args.rounds<1 or any(r not in range(64) for r in args.rules):parser.error('positive rounds and valid rules required')
    programs=['feldmarschall-engine','feldmarschall-ai-v020','feldmarschall-ai-planned','feldmarschall-ai-adaptive-progress','librules-variant.so']
    identities={name:hashlib.sha256((ROOT/'build'/name).read_bytes()).hexdigest() for name in programs}
    logic_names=['tools/'+name for name in ['variant_arena.py','variant_rules.py','variant_bot.py','arena.py','feldmarschall.py','benchmark_ai.py','run_variant_benchmarks.py']]
    logic_names+=['src/native/engine.c','src/core/rules.c','src/core/board.c','src/core/pieces.c',
                  'src/core/ai.c','src/core/ai_mission.c','src/core/ai_memory.c','src/core/ai_student.c',
                  'src/core/ai_student_model_production.h','Makefile']
    logic={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in logic_names}
    args.out.mkdir(parents=True,exist_ok=False)
    plan={'schema':1,'rules':args.rules,'difficulties':['normal','hard'],'rounds_per_family':args.rounds,
          'seed_offset':args.seed_offset,'phase':args.phase,'program_sha256':identities,'logic_sha256':logic,
          'scope':'Seven equally weighted layout families, five fixed opponents, both engine sides; same deployments/seeds across all conditions',
          'rescue_policy':'Both armies restore strongest available casualty in first frontmost vacant home square, matching X16 demo',
          'command':sys.argv}
    (args.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    for rules in args.rules:
        for level in ('normal','hard'):
            for name,digest in identities.items():
                if hashlib.sha256((ROOT/'build'/name).read_bytes()).hexdigest()!=digest:raise ValueError('program changed during validation: '+name)
            for path,digest in logic.items():
                if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('referee or policy source changed during validation: '+path)
            name=f'rules-{rules:02d}-{level}'
            command=[sys.executable,str(ROOT/'tools/benchmark_ai.py'),'--league','--suite','broad','--rules',str(rules),
                     '--difficulty',level,'--rounds',str(args.rounds),'--jobs',str(args.jobs),'--record-moves',
                     '--phase',args.phase,'--seed-offset',str(args.seed_offset),'--strategy','production-variant-league',
                     '--out',str(args.out/name)]
            print('Starting '+name,flush=True)
            with (args.out/(name+'.log')).open('w') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            report=json.loads((args.out/name/'summary.json').read_text())
            stats=[value['overall'] for value in report['comparisons'].values()]
            print(f"Completed {name}: {sum(s['games'] for s in stats)} games; score {sum(s['score'] for s in stats)/len(stats):.2%}",flush=True)


if __name__=='__main__':main()
