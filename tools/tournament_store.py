"""Version 2 .fmtour files: compressed moves and explicitly unscored engine errors.

Version 1 remains readable. Version 2 adds result='error'; these legal trace
prefixes are never counted as wins, losses or draws.
"""
from collections import Counter
import json
from pathlib import Path
import sqlite3
import zlib

from feldmarschall import BLUE, FLAG, GLYPHS, RED, Position, square_name, valid_setup

SCHEMA = 2


def mirror_setup(setup):
    """Reflect columns within each front-first row; an involution on armies."""
    if not isinstance(setup,str) or not valid_setup(setup):
        raise ValueError('valid Classic army required for row reflection')
    return ''.join(setup[index:index+10][::-1] for index in range(0,40,10))


class Tournament:
    def __init__(self, path, create=False, metadata=None):
        self.path = Path(path)
        if create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation prevents accidental replacement of existing evidence.
            with self.path.open('xb'):
                pass
        self.db = sqlite3.connect(self.path.resolve().as_uri() + ('?mode=rw' if create else '?mode=ro'), uri=True)
        self.db.row_factory = sqlite3.Row
        if create:
            self.db.executescript('''
                PRAGMA user_version=2;
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE artifacts (sha256 TEXT PRIMARY KEY, name TEXT, data BLOB NOT NULL);
                CREATE TABLE games (
                    id INTEGER PRIMARY KEY, pair_id INTEGER NOT NULL, family TEXT NOT NULL,
                    red TEXT NOT NULL, blue TEXT NOT NULL, seed INTEGER NOT NULL,
                    red_setup TEXT NOT NULL, blue_setup TEXT NOT NULL,
                    result TEXT NOT NULL, reason TEXT NOT NULL, plies INTEGER NOT NULL,
                    moves BLOB NOT NULL);
                CREATE INDEX games_pair ON games(pair_id);
                CREATE INDEX games_result ON games(result, reason);
            ''')
            self.set_metadata(dict(metadata or {}, schema=SCHEMA, rules='classic', status='running'))
        elif self.db.execute('PRAGMA user_version').fetchone()[0] not in (1, SCHEMA):
            self.close()
            raise ValueError('Unsupported tournament file version')

    def set_metadata(self, items):
        with self.db:
            self.db.executemany('INSERT OR REPLACE INTO metadata VALUES (?, ?)',
                                [(key, json.dumps(value)) for key, value in items.items()])

    def metadata(self):
        return {row['key']: json.loads(row['value']) for row in self.db.execute('SELECT * FROM metadata')}

    def artifact(self, name, data):
        import hashlib
        sha = hashlib.sha256(data).hexdigest()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?)', (sha, name, zlib.compress(data, 9)))
        return sha

    def add_game(self, game, pair_id, family, setups, game_id=None):
        moves = game['moves']
        if len(moves) != game['plies'] or any(not 0 <= sq < 100 for move in moves for sq in move):
            raise ValueError('Invalid move trace')
        packed = zlib.compress(bytes(sq for move in moves for sq in move), 9)
        with self.db:
            self.db.execute('''INSERT INTO games
                (id,pair_id,family,red,blue,seed,red_setup,blue_setup,result,reason,plies,moves)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (game_id, pair_id, family, game['red'], game['blue'], game['seed'], *setups,
                 game['result'], game['reason'], game['plies'], packed))

    def games(self):
        return [dict(row) for row in self.db.execute('SELECT id,pair_id,family,red,blue,seed,result,reason,plies FROM games ORDER BY id')]

    def game(self, identity):
        row = self.db.execute('SELECT * FROM games WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise ValueError(f'No match {identity}')
        game = dict(row)
        raw = zlib.decompress(game['moves'])
        if len(raw) != game['plies'] * 2 or any(sq >= 100 for sq in raw):
            raise ValueError('Corrupt move trace')
        game['moves'] = list(zip(raw[::2], raw[1::2]))
        return game

    def summary(self):
        games = self.games()
        scored = [g for g in games if g['result'] != 'error']
        policies = self.metadata()['participants']
        standings = {}
        for policy in policies:
            identity = policy['policy']['id']
            wins = sum(g['result'] == ('red' if g['red'] == identity else 'blue') for g in scored)
            draws = sum(g['result'] == 'draw' for g in scored)
            losses = len(scored) - wins - draws
            standings[identity] = dict(wins=wins, draws=draws, losses=losses,
                                       score=(wins + draws / 2) / len(scored) if scored else None)
        families = {}
        for family in sorted({g['family'] for g in scored}):
            subset = [g for g in scored if g['family'] == family]
            families[family] = {}
            for identity in standings:
                points = [0.5 if g['result'] == 'draw' else
                          float(g['result'] == ('red' if g['red'] == identity else 'blue')) for g in subset]
                families[family][identity] = sum(points) / len(points)
        return dict(status=self.metadata()['status'], games=len(games), scored_games=len(scored),
                    errors=len(games)-len(scored), standings=standings,
                    average_plies=sum(g['plies'] for g in games) / len(games) if games else 0,
                    families=families, endings=dict(Counter(g['reason'] for g in games)))

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def replay(game):
    """Return positions and readable events, validating every recorded Classic move."""
    position = Position()
    for army, key in ((RED, 'red_setup'), (BLUE, 'blue_setup')):
        if not valid_setup(game[key]):
            raise ValueError('Invalid starting army')
        position.place(army, game[key])
    states = [[cell.copy() if cell else None for cell in position.cells]]
    events = []
    flag_taken = False
    for ply, (src, dst) in enumerate(game['moves']):
        if flag_taken or (src, dst) not in position.moves(ply % 2):
            raise ValueError(f'Illegal recorded move at ply {ply + 1}')
        attacker, defender = position.cells[src], position.cells[dst]
        label = f'{ply + 1:4d}  {"Red" if ply % 2 == 0 else "Blue"}  {square_name(src)} → {square_name(dst)}'
        if defender:
            flag_taken = defender[1] == FLAG
            label += f'  {GLYPHS[attacker[1]]} × {GLYPHS[defender[1]]}'
            position.fight(src, dst, attacker[1], defender[1])
        else:
            position.move(src, dst)
        events.append(label)
        states.append([cell.copy() if cell else None for cell in position.cells])
    side = len(game['moves']) % 2
    if game['result'] == 'error':
        if not game['reason'].startswith('engine error: ') or flag_taken:
            raise ValueError('Invalid unscored engine-error record')
        return states, events
    if flag_taken:
        expected = 'red' if (len(game['moves']) - 1) % 2 == RED else 'blue'
        if game['reason'] != 'flag' or game['result'] != expected:
            raise ValueError('Incorrect flag-capture result')
    elif not position.moves(side):
        expected = ('blue' if side == RED else 'red') if position.moves(1 - side) else 'draw'
        reason = 'no moves' if expected != 'draw' else 'neither can move'
        if game['reason'] != reason or game['result'] != expected:
            raise ValueError('Incorrect blocked-army result')
    elif game['reason'] != 'ply limit' or game['result'] != 'draw':
        raise ValueError('Recorded ending does not match the position')
    return states, events


def verify(path):
    import hashlib
    with Tournament(path) as tournament:
        metadata = tournament.metadata()
        if metadata['rules'] != 'classic':
            raise ValueError('Only Classic is supported')
        artifacts = set()
        artifact_rows = {}
        for row in tournament.db.execute('SELECT * FROM artifacts'):
            if hashlib.sha256(zlib.decompress(row['data'])).hexdigest() != row['sha256']:
                raise ValueError('Artifact hash mismatch')
            artifacts.add(row['sha256'])
            artifact_rows[row['sha256']] = row
        identities = set()
        for participant in metadata['participants']:
            identities.add(participant['policy']['id'])
            if participant['policy']['source_sha256'] not in artifacts or any(
                    sha not in artifacts for sha in participant['runtime_sha256'].values()):
                raise ValueError('Missing participant sources or runtime')
        if any(sha not in artifacts for sha in metadata.get('referee_sha256', {}).values()):
            raise ValueError('Missing referee source')
        for key in ('worker_sha256', 'worker_source_sha256'):
            if key in metadata and metadata[key] not in artifacts:
                raise ValueError('Missing native worker executable or source archive')
        setup_mode = metadata.get('setup_mode', 'referee')
        if setup_mode not in ('referee', 'policy-owned', 'policy-owned-rotated-v1'):
            raise ValueError('Unknown tournament setup mode')
        setup_records = {}
        setup_owner = None
        if setup_mode in ('policy-owned', 'policy-owned-rotated-v1'):
            setup_owner = metadata.get('setup_owner')
            if (setup_owner not in identities or len(identities) != 2 or
                    setup_owner != metadata['participants'][0]['policy']['id']):
                raise ValueError('Invalid policy-owned setup owner')
            artifact_sha = metadata.get('setup_records_sha256')
            artifact_name = metadata.get('setup_records_artifact')
            if artifact_sha not in artifact_rows or artifact_name != 'setup/policy-owned-v1.json':
                raise ValueError('Missing policy-owned setup artifact')
            artifact = artifact_rows[artifact_sha]
            if artifact['name'] != artifact_name:
                raise ValueError('Policy-owned setup artifact name mismatch')
            try:
                setup_document = json.loads(zlib.decompress(artifact['data']))
            except (ValueError, TypeError) as error:
                raise ValueError('Invalid policy-owned setup artifact') from error
            if (not isinstance(setup_document, dict) or
                    setup_document.get('schema') != 'classic-policy-owned-setups-v1' or
                    setup_document.get('owner') != setup_owner or
                    setup_document.get('opponent') not in identities - {setup_owner} or
                    not isinstance(setup_document.get('records'), list)):
                raise ValueError('Invalid policy-owned setup artifact ownership or schema')
            for record in setup_document['records']:
                if (not isinstance(record, dict) or
                        any(type(record.get(key)) is not int or record[key] < 1
                            for key in ('pair_id', 'move_seed', 'setup_seed')) or
                        record.get('family') not in metadata['families'] or
                        not isinstance(record.get('owner_setup'), str) or not valid_setup(record['owner_setup']) or
                        not isinstance(record.get('opponent_setup'), str) or not valid_setup(record['opponent_setup'])):
                    raise ValueError('Invalid policy-owned setup record')
                if record['pair_id'] in setup_records:
                    raise ValueError('Duplicate policy-owned setup pair')
                if record['setup_seed'] != ((record['move_seed'] * 109 + 0x5e7a) % 65535) + 1:
                    raise ValueError('Policy-owned setup seed does not match move seed')
                if 'protocol' in record:
                    expected_protocol = ['feldmarschall', 'new red', 'rules 0',
                        'difficulty ' + metadata['participants'][0]['policy']['difficulty'],
                        'seed ' + str(record['setup_seed']), 'setup', 'quit']
                    if record['protocol'] != expected_protocol:
                        raise ValueError('Invalid policy-owned setup selection protocol')
                if 'stdout' in record:
                    if not isinstance(record['stdout'], str):
                        raise ValueError('Invalid policy-owned setup transcript')
                    responses = [line[6:].strip() for line in record['stdout'].splitlines()
                                 if line.startswith('setup ')]
                    if responses != [record['owner_setup']]:
                        raise ValueError('Policy-owned setup transcript response mismatch')
                setup_records[record['pair_id']] = record
            if metadata['status'] == 'complete' and len(setup_records) * 2 != metadata['planned_games']:
                raise ValueError('Incomplete policy-owned setup records')
        pairs = {}
        for row in tournament.games():
            game = tournament.game(row['id'])
            replay(game)
            if {game['red'], game['blue']} != identities:
                raise ValueError('Unknown game participant')
            if game['plies'] > metadata['max_plies'] or (game['reason'] == 'ply limit' and game['plies'] != metadata['max_plies']):
                raise ValueError('Incorrect move limit')
            if setup_mode in ('policy-owned', 'policy-owned-rotated-v1'):
                record = setup_records.get(game['pair_id'])
                if record is None or game['family'] != record['family'] or game['seed'] != record['move_seed']:
                    raise ValueError('Game does not match policy-owned setup record')
                owned = game['red_setup'] if game['red'] == setup_owner else game['blue_setup']
                opponent = game['blue_setup'] if game['red'] == setup_owner else game['red_setup']
                expected_owned, expected_opponent = record['owner_setup'], record['opponent_setup']
                if setup_mode == 'policy-owned-rotated-v1' and game['blue'] == setup_owner:
                    expected_owned, expected_opponent = mirror_setup(expected_owned), mirror_setup(expected_opponent)
                if owned != expected_owned or opponent != expected_opponent:
                    raise ValueError('Game army does not match policy-owned setup artifact')
            pairs.setdefault(game['pair_id'], []).append(game)
        for pair in pairs.values():
            if len(pair) != 2:
                if metadata['status'] == 'complete':
                    raise ValueError('Incomplete paired round')
                continue
            a, b = pair
            if (a['red'] != b['blue'] or a['blue'] != b['red'] or
                    any(a[key] != b[key] for key in ('family', 'seed')) or
                    (setup_mode == 'referee' and any(a[key] != b[key] for key in ('red_setup', 'blue_setup'))) or
                    (setup_mode == 'policy-owned' and
                     (a['red_setup'] != b['blue_setup'] or a['blue_setup'] != b['red_setup'])) or
                    (setup_mode == 'policy-owned-rotated-v1' and
                     (a['red_setup'] != mirror_setup(b['blue_setup']) or
                      a['blue_setup'] != mirror_setup(b['red_setup'])))):
                raise ValueError('Mismatched paired round')
        if metadata['status'] == 'complete' and len(tournament.games()) != metadata['planned_games']:
            raise ValueError('Incomplete tournament')
        return tournament.summary()
