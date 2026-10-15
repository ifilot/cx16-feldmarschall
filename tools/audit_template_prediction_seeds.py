"""Ensure research draws overlap no saved game or private deployment RNG seed.

Only seed fields are retained from setup artifacts; no tournament results,
armies or validation prediction evidence are inspected by this audit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import zlib

ROOT=Path(__file__).resolve().parents[1]


def audit(source):
    data=json.loads(source.read_text());research=set(data['private_research_seeds'])
    names=subprocess.run(['rg','--files','-g','*.fmtour'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
    game_seeds=set();deployment_seeds=set();metadata_seeds=set();artifacts=0
    for name in names:
        db=sqlite3.connect((ROOT/name).resolve().as_uri()+'?mode=ro',uri=True)
        try:
            game_seeds.update(row[0] for row in db.execute('SELECT DISTINCT seed FROM games'))
            for key,value in db.execute('SELECT key,value FROM metadata'):
                if 'seed' in key:
                    number=json.loads(value)
                    if type(number) is int:metadata_seeds.add(number)
            for packed, in db.execute("SELECT data FROM artifacts WHERE name IN ('setup/original-dos-records-v1.json','setup/policy-owned-v1.json')"):
                artifacts+=1
                for record in json.loads(zlib.decompress(packed))['records']:
                    deployment_seeds.update(record[key] for key in ('private_seed','setup_seed','move_seed') if key in record)
        finally:db.close()
    overlap=research&(game_seeds|deployment_seeds|metadata_seeds)
    assert not overlap, sorted(overlap)
    return dict(kind='research-private-seed-isolation-audit',passed=True,research_armies=len(research),
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),saved_tournaments=len(names),
                saved_game_seed_count=len(game_seeds),saved_deployment_seed_count=len(deployment_seeds),
                metadata_seed_count=len(metadata_seeds),setup_artifacts_checked=artifacts,overlap_count=0,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise FileExistsError('Preserve prior isolation evidence')
    args.out.write_text(json.dumps(audit(args.source),indent=2)+'\n')
