"""Read-only DOS-local orientation proof and independent 40-ply smoke replay."""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile

from ai_registry import ROOT
from audit_policy_setups import audit as audit_policy
from campaign_dos_deployment import generate_setup
from campaign_dos_setup_runtime import audit_original_setups
from feldmarschall import random_setup
from msdos1990 import OriginalAI
from tournament_store import Tournament,replay,verify


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def mirror(setup):return ''.join(setup[i:i+10][::-1] for i in range(0,40,10))


def run():
    folder=ROOT/'docs/ai-honest-campaign-2026-10-15/research/dos-deployment-original-v1'
    destination=folder/'orientation-and-smoke-audit.json'
    if destination.exists():raise ValueError('preserve original audit evidence')
    generated,source=generate_setup(ROOT/'ai/msdos1990',4,3,folder)
    assert source['branch']=='original-procedural'
    other=random_setup(random.Random(847001));orientation=[]
    for side,applied in ((1,generated),(0,generated),(0,mirror(generated))):
        setups=[other,other];setups[side]=applied
        ai=OriginalAI(ROOT/'ai/msdos1990',side,setups,seed=19,level=3)
        physical=[ai.cpu.word(0x3e9e+72*r+6*c) for r in range(1,5) for c in range(1,11)]
        orientation.append(dict(dos_side=('red','blue')[side],applied='reflected' if applied!=generated else 'same-canonical',
            differing_own_rank_cells=sum(a!=b for a,b in zip(physical,source['physical_ranks'])),
            local_physical_ranks=physical))
    assert [row['differing_own_rank_cells']==0 for row in orientation]==[True,False,True]
    reports={};games_by_backend={}
    with tempfile.TemporaryDirectory(prefix='dos-smoke-independent-') as temporary:
        request=Path(temporary)/'game.json'
        for backend in ('python','openmp'):
            path=Path('/tmp/original-dos-family-'+backend+'.fmtour')
            before=digest(path);summary=verify(path)
            original_audit=audit_original_setups(path);own_audit=audit_policy(path)
            with Tournament(path) as tournament:
                metadata=tournament.metadata();games=[tournament.game(row['id']) for row in tournament.games()]
            native_states=0
            for game in games:
                request.write_text(json.dumps(game))
                result=subprocess.run([str(ROOT/'build/desktop/feldmarschall-tournament-worker'),'--replay',str(request)],
                                      capture_output=True,text=True,check=True,timeout=30)
                states=json.loads(result.stdout)['states'];assert states==replay(game)[0]
                native_states+=len(states)
            screenshot=folder/('independent-'+backend+'-smoke.png')
            qt=subprocess.run([str(ROOT/'build/desktop/feldmarschall-desk'),'--capture-review',str(path),
                '--match',str(games[0]['id']),'--ply',str(games[0]['plies']),'--screenshot',str(screenshot)],
                env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),capture_output=True,text=True,check=True,timeout=30)
            assert digest(path)==before
            reports[backend]=dict(path=str(path),sha256=before,games=len(games),plies=[game['plies'] for game in games],
                native_states_compared=native_states,python_and_native_every_state_identical=True,
                original_setup_audit=original_audit,own_setup_audit=own_audit,qt_screenshot=str(screenshot.relative_to(ROOT)),
                qt_stdout=qt.stdout,qt_stderr=qt.stderr,summary=summary,
                setup_mode=metadata['setup_mode'],original_boundary=metadata['original_dos_setup_boundary'])
            games_by_backend[backend]=games
    assert games_by_backend['python']==games_by_backend['openmp']
    result=dict(schema='dos-original-orientation-independent-audit-v1',strength_evidence=False,
        orientation_fixture=dict(seed=4,level=3,branch=source['branch'],canonical_setup=generated,reflected_setup=mirror(generated),
            observations=orientation,
            conclusion='Same canonical string gives the exact generated own physical ranks only for Blue. Red needs each10-glyph row reflected. This is exact seeded-array evidence; full population reflection symmetry is not claimed.'),
        primary_code=dict(canonical_conversion='tools/campaign_dos_deployment.py: generate_setup returns physical rows4..1, cols1..10',
            placement='tools/feldmarschall.py: setup_squares reverses row order for Blue but retains columns for both armies',
            dos_local='tools/msdos1990.py: OriginalAI.local returns square for Blue and99-square for Red',
            original_procedural='sources/reconstruction/ovl6/PLAC.C and SEARCH.C preserve increasing-column/fallback scans and do not add a final random reflection'),
        current_mode='policy-owned keeps exactly the same canonical string per participant across colors; it is therefore a side-reflected original-generator benchmark, plus independently reseeded move RNG.',
        explicit_future_mode='policy-owned-rotated-v1: first(ownerRed=o,DOSBlue=b); swapped(DOSRed=mirror(b),ownerBlue=mirror(o)). This rotates both armies180 degrees while preserving the generated DOS-local own array and honest owner relative deployment.',
        referee_future='An explicit original-DOS-local orientation/family can reflect generatedslotA before placing it Red, leaveB Blue, and retain fixed physical armies under policy swap. Audit must transform raw generator records according to the declared orientation.',
        reports=reports,backends_game_records_identical=True,
        source_sha256={name:digest(ROOT/name) for name in ('tools/tournament.py','tools/feldmarschall.py','tools/msdos1990.py','tools/campaign_dos_deployment.py','tools/campaign_dos_setup_runtime.py')})
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(orientation=orientation,smokes={name:dict(games=row['games'],states=row['native_states_compared']) for name,row in reports.items()},identical_backends=True),indent=2))
    return result


if __name__=='__main__':run()
