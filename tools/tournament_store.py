"""Version 1 .fmtour files: indexed SQLite, compressed two-byte move records."""
from collections import Counter
import json
from pathlib import Path
import sqlite3
import zlib

from feldmarschall import BLUE, FLAG, GLYPHS, RED, Position, square_name, valid_setup

SCHEMA = 1


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
                PRAGMA user_version=1;
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
        elif self.db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA:
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
        policies = self.metadata()['participants']
        standings = {}
        for policy in policies:
            identity = policy['policy']['id']
            wins = sum(g['result'] == ('red' if g['red'] == identity else 'blue') for g in games)
            draws = sum(g['result'] == 'draw' for g in games)
            losses = len(games) - wins - draws
            standings[identity] = dict(wins=wins, draws=draws, losses=losses,
                                       score=(wins + draws / 2) / len(games) if games else None)
        families = {}
        for family in sorted({g['family'] for g in games}):
            subset = [g for g in games if g['family'] == family]
            families[family] = {}
            for identity in standings:
                points = [0.5 if g['result'] == 'draw' else
                          float(g['result'] == ('red' if g['red'] == identity else 'blue')) for g in subset]
                families[family][identity] = sum(points) / len(points)
        return dict(status=self.metadata()['status'], games=len(games), standings=standings,
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
        for row in tournament.db.execute('SELECT * FROM artifacts'):
            if hashlib.sha256(zlib.decompress(row['data'])).hexdigest() != row['sha256']:
                raise ValueError('Artifact hash mismatch')
            artifacts.add(row['sha256'])
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
        pairs = {}
        for row in tournament.games():
            game = tournament.game(row['id'])
            replay(game)
            if {game['red'], game['blue']} != identities:
                raise ValueError('Unknown game participant')
            if game['plies'] > metadata['max_plies'] or (game['reason'] == 'ply limit' and game['plies'] != metadata['max_plies']):
                raise ValueError('Incorrect move limit')
            pairs.setdefault(game['pair_id'], []).append(game)
        for pair in pairs.values():
            if len(pair) != 2:
                if metadata['status'] == 'complete':
                    raise ValueError('Incomplete paired round')
                continue
            a, b = pair
            if (a['red'] != b['blue'] or a['blue'] != b['red'] or
                    any(a[key] != b[key] for key in ('family', 'seed', 'red_setup', 'blue_setup'))):
                raise ValueError('Mismatched paired round')
        if metadata['status'] == 'complete' and len(tournament.games()) != metadata['planned_games']:
            raise ValueError('Incomplete tournament')
        return tournament.summary()
