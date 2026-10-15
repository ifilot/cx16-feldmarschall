"""Independent read-only qualification of the explicit rotated setup mode."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zlib

from ai_registry import ROOT
from audit_policy_setups import audit as audit_policy
from campaign_dos_setup_runtime import audit_original_setups
from msdos1990 import OriginalAI
from tournament_store import Tournament, mirror_setup, replay, verify


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    folder=ROOT/'docs/ai-honest-campaign-2026-10-15/research/dos-deployment-original-v1'
    destination=folder/'rotated-mode-smoke-audit.json'
    if destination.exists():
        raise ValueError('preserve existing audit')
    old_expected={'python':'ea5b2afe59aeb1ad0a5c2c301dbbb7650f5b8883b153d8ac9eb6b5de6e4f5b98',
                  'openmp':'33ac0a130bcf2f27deba8f3c29a417d219f43d2d85809df9bb38996e9801c012'}
    reports={}; all_games={}
    with tempfile.TemporaryDirectory(prefix='dos-rotated-independent-') as temp:
        request=Path(temp)/'game.json'
        for backend in ('python','openmp'):
            path=Path('/tmp/original-dos-rotated-'+backend+'.fmtour')
            before=digest(path)
            summary=verify(path)
            owner_audit=audit_policy(path)
            original_audit=audit_original_setups(path)
            with Tournament(path) as tournament:
                metadata=tournament.metadata()
                games=[tournament.game(row['id']) for row in tournament.games()]
                def document(key):
                    row=tournament.db.execute('SELECT data FROM artifacts WHERE sha256=?',(metadata[key],)).fetchone()
                    return json.loads(zlib.decompress(row['data']))
                record=document('setup_records_sha256')['records'][0]
                originals=document('original_dos_setup_records_sha256')['records']
            assert metadata['setup_mode']=='policy-owned-rotated-v1'
            assert len(games)==2 and all(g['plies']==40 and g['result']!='error' for g in games)
            owner=record['owner_setup']; opponent=record['opponent_setup']
            assert (games[0]['red_setup'],games[0]['blue_setup'])==(owner,opponent)
            assert (games[1]['red_setup'],games[1]['blue_setup'])==(mirror_setup(opponent),mirror_setup(owner))
            raw_b=next(row for row in originals if row['slot']=='B')
            assert raw_b['setup']==opponent
            native_states=0; orientations=[]
            for game,side in zip(games,(1,0)):
                ai=OriginalAI(ROOT/'ai/msdos1990',side,[game['red_setup'],game['blue_setup']],seed=19,level=3)
                physical=[ai.cpu.word(0x3e9e+72*r+6*c) for r in range(1,5) for c in range(1,11)]
                assert physical==raw_b['audit']['physical_ranks']
                orientations.append(dict(game_id=game['id'],dos_side=('red','blue')[side],
                    differing_local_rank_cells=0,local_physical_ranks=physical))
                request.write_text(json.dumps(game))
                result=subprocess.run([str(ROOT/'build/desktop/feldmarschall-tournament-worker'),'--replay',str(request)],
                    capture_output=True,text=True,check=True,timeout=30)
                states=json.loads(result.stdout)['states']
                assert states==replay(game)[0]
                native_states+=len(states)
            screenshot=folder/('independent-rotated-'+backend+'-smoke.png')
            qt=subprocess.run([str(ROOT/'build/desktop/feldmarschall-desk'),'--capture-review',str(path),
                '--match',str(games[1]['id']),'--ply','40','--screenshot',str(screenshot)],
                env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),capture_output=True,text=True,check=True,timeout=30)
            assert digest(path)==before
            old=Path('/tmp/original-dos-family-'+backend+'.fmtour')
            assert digest(old)==old_expected[backend]
            with Tournament(old) as tournament:
                old_first=tournament.game(tournament.games()[0]['id'])
            assert old_first==games[0]
            reports[backend]=dict(path=str(path),sha256=before,summary=summary,
                setup_mode=metadata['setup_mode'],native_states_compared=native_states,
                python_and_native_every_state_identical=True,owner_setup_audit=owner_audit,
                original_setup_audit=original_audit,dos_local_orientations=orientations,
                screenshot=str(screenshot.relative_to(ROOT)),qt_stdout=qt.stdout,qt_stderr=qt.stderr,
                setup_source_sha256=metadata['setup_source_sha256'],
                mirror_helper_source_frozen='tournament_store.py' in metadata['setup_source_sha256'],
                old_smoke_sha256=old_expected[backend],old_smoke_unchanged=True,
                first_orientation_matches_old_trace=True)
            all_games[backend]=games
    assert all_games['python']==all_games['openmp']
    result=dict(schema='dos-rotated-smoke-independent-audit-v1',strength_evidence=False,
        seed=2399871,max_plies=40,backends_game_records_identical=True,reports=reports,
        conclusion='Both side orientations preserve the exact original generated DOS-local army. Frozen setup reruns, Python/native every-state replay and Qt review pass. Move RNG remains independently reseeded, as explicitly recorded by the runner.',
        source_sha256={name:digest(ROOT/name) for name in ('tools/audit_campaign_dos_rotated_smoke.py',
            'tools/tournament.py','tools/tournament_store.py','tools/campaign_dos_setup_runtime.py')})
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(reports={key:dict(states=row['native_states_compared'],mirror_helper_source_frozen=row['mirror_helper_source_frozen']) for key,row in reports.items()},identical_backends=True)))
    return result


if __name__=='__main__':
    run()
