"""Operational error attribution using metadata only; never reads game moves."""
import collections
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/ai-honest-campaign-2026-10-15'
ILLEGAL = 'engine error: AI produced an illegal move'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(path):
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    metadata = {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM metadata')}
    receipt = metadata['worker_build']
    bindings = {}
    for name, expected in [('referee/openmp-worker', metadata['worker_sha256']),
                           ('referee/worker-sources.zip', metadata['worker_source_sha256'])]:
        stored_sha, packed = db.execute('SELECT sha256,data FROM artifacts WHERE name=?', (name,)).fetchone()
        data = zlib.decompress(packed)
        assert sha(data) == expected == stored_sha
        bindings[name] = expected
        if name.endswith('.zip'):
            archive = data
    assert receipt['executable_sha256'] == metadata['worker_sha256']
    assert receipt['source_archive_sha256'] == metadata['worker_source_sha256']
    source = zipfile.ZipFile(io.BytesIO(archive)).read('desktop/worker.cpp')
    assert sha(source) == receipt['source_sha256']['desktop/worker.cpp']
    assert source == (ROOT / 'desktop/worker.cpp').read_bytes()
    text = source.decode()
    # Reviewed frozen play() control flow: one append and side change per completed move.
    play = text[text.index('static QJsonObject play('):text.index('static QJsonObject replay(')]
    assert 'int side = 0, winner = -1;' in play
    assert play.count('trace.append(') == play.count('side = 1 - side;') == 1
    assert play.index('engines[side]->ask("go", "move")') < play.index('throw std::runtime_error("AI produced an illegal move")') < play.index('trace.append(') < play.index('side = 1 - side;')
    assert '{"plies", trace.size()}' in play
    bindings['desktop/worker.cpp'] = sha(source)
    reasons = dict(db.execute("SELECT reason,COUNT(*) FROM games WHERE result='error' GROUP BY reason"))
    # Deliberately excludes IDs, seeds, setups, moves, and any positions.
    rows = db.execute("SELECT red,blue,plies,reason FROM games WHERE result='error' AND reason=?", (ILLEGAL,)).fetchall()
    actors = collections.Counter()
    classifications = []
    for red, blue, plies, reason in rows:
        assert plies >= 0 and reason == ILLEGAL
        actor = (red, blue)[plies % 2]
        actors[actor] += 1
        classifications.append(dict(red=red, blue=blue, completed_plies=plies,
                                    actor=actor, actor_color=('red', 'blue')[plies % 2]))
    db.close()
    return dict(file=str(path.relative_to(ROOT)), bindings=bindings,
                reasons=reasons, illegal_actors=dict(actors), illegal_records=classifications)


if __name__ == '__main__':
    files = []
    for cycle in ('cycle-41-fortress-template-validation', 'cycle-42-template-q24-native-dos-screen'):
        files.extend(inspect(p) for p in sorted((BASE / cycle).glob('*.fmtour')))
    print(json.dumps(dict(scope='Metadata-only operational diagnosis; no moves, setups or positions read; no policy tuning.',
                          method='Frozen worker starts Red; illegal check precedes append; stored plies counts completed moves; actor is Red for even plies and Blue for odd plies.',
                          files=files), indent=2))
