"""Calculate setup gains with shared-opponent layout blocks kept together."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from optimize_ai_deployments import delta


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    games=[json.loads(line) for line in (args.run/'games.jsonl').read_text().splitlines()]
    portfolio=json.loads((args.run/'portfolio.json').read_text())
    from optimize_ai_deployments import identity
    names=[identity(setup) for setup in portfolio['selected']]+['preset-control']
    report={name:{control:delta(games,name,control) for control in ('preset-control','random-control') if control!=name} for name in names}
    filename=args.run/'deployment-block-analysis.json'
    filename.write_text(json.dumps(report,indent=2)+'\n')
    with zipfile.ZipFile(args.run/'analysis-sources.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (Path(__file__),Path(__file__).with_name('optimize_ai_deployments.py')):archive.write(path,path.name)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
