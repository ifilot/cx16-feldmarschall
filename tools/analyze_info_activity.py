"""Descriptive public-disclosure activity from recorded Classic games.

Physical ranks are used only to replay outcomes, never to select a move.
Deaths without disclosure are descriptive counts, not evidence of a mistake:
screening, tempo, defense and already useful surviving pieces also have value.
"""
from feldmarschall import FLAG, Position, battle, valid_setup


WEAK = (5, 6, 8)
COUNTERS = ('unit_appearances', 'casualties', 'zero_disclosure_casualties',
            'known_enemy_terminal_deaths', 'concealed_enemy_attacks',
            'surviving_target_disclosures', 'new_enemy_disclosures',
            'known_losing_attack_deaths', 'probe_next_turn_reached',
            'probe_target_survived_reply', 'favorable_followup_available',
            'favorable_followup_taken')


def analyze_events(position, moves, side):
    """Replay legal events in a copy of ``position`` and return one side's counts.

    Each physical piece keeps its starting-square identity after moving.
    Disclosures belong to the participating weak unit, including a previously
    concealed attacker that kills it. Terminal-battle disclosure is credited
    before classifying a casualty's lifetime.
    """
    if side not in (0, 1):
        raise ValueError('side must be 0 or 1')
    source = position
    position = Position()
    position.cells = [cell.copy() if cell else None for cell in source.cells]
    position.shuttle = dict(source.shuttle)
    ids = {sq: sq for sq, cell in enumerate(position.cells) if cell}
    own = {identity: position.cells[sq][1] for sq, identity in ids.items()
           if position.cells[sq][0] == side}
    learned = {identity: set() for identity in own}
    by_rank = {str(rank): dict.fromkeys(COUNTERS, 0) for rank in WEAK}
    for rank in own.values():
        if rank in WEAK:
            by_rank[str(rank)]['unit_appearances'] += 1
    own_moves = weak_moves = miners_lost = 0
    flag_taken = False
    pending_probes = []
    for ply, (src, dst) in enumerate(moves):
        if flag_taken or (src, dst) not in position.moves(ply % 2):
            raise ValueError(f'illegal activity event at ply {ply + 1}')
        attacker, defender = position.cells[src], position.cells[dst]
        attacker_id = ids[src]
        if attacker[0] == side and pending_probes:
            # Evaluate only the recorded next own turn, after the actual reply.
            # Physical identities follow retreats; no capture is forced, and
            # winning combat is not a claim that the subsequent position is safe.
            legal = position.moves(side)
            for target_id, prober_rank in pending_probes:
                probe = by_rank[str(prober_rank)]
                probe['probe_next_turn_reached'] += 1
                target_sq = next((sq for sq, identity in ids.items()
                                  if identity == target_id), None)
                if target_sq is None:
                    continue
                probe['probe_target_survived_reply'] += 1
                target = position.cells[target_sq]
                favorable = {move for move in legal if move[1] == target_sq
                             and position.cells[move[0]][1] != 8
                             and battle(position.cells[move[0]][1], target[1]) == 'attacker'}
                probe['favorable_followup_available'] += bool(favorable)
                probe['favorable_followup_taken'] += (src, dst) in favorable
            pending_probes.clear()
        if attacker[0] == side:
            own_moves += 1
            weak_moves += attacker[1] in WEAK
        if defender is None:
            position.move(src, dst)
            ids[dst] = ids.pop(src)
            continue
        defender_id = ids[dst]
        ours_attacking = attacker[0] == side
        ours = attacker if ours_attacking else defender
        enemy = defender if ours_attacking else attacker
        ours_id = attacker_id if ours_attacking else defender_id
        enemy_id = defender_id if ours_attacking else attacker_id
        rank = ours[1]
        known_enemy = bool(enemy[3])
        counter = by_rank.get(str(rank))
        if counter is not None:
            if ours_attacking and not known_enemy:
                counter['concealed_enemy_attacks'] += 1
            if not known_enemy:
                learned[ours_id].add(enemy_id)
                counter['new_enemy_disclosures'] += 1
        flag_taken = defender[1] == FLAG
        outcome, _ = position.fight(src, dst, attacker[1], defender[1])
        ours_died = outcome in (('defender', 'both') if ours_attacking else ('attacker', 'both'))
        enemy_survived = outcome == ('defender' if ours_attacking else 'attacker')
        if counter is not None:
            if ours_attacking and not known_enemy and enemy_survived:
                counter['surviving_target_disclosures'] += 1
                pending_probes.append((enemy_id, rank))
            if ours_died:
                counter['casualties'] += 1
                counter['zero_disclosure_casualties'] += not learned[ours_id]
                counter['known_enemy_terminal_deaths'] += known_enemy
                if ours_attacking and known_enemy and outcome == 'defender':
                    counter['known_losing_attack_deaths'] += 1
        if ours_died and rank == 7:
            miners_lost += 1
        ids.pop(src)
        ids.pop(dst)
        if outcome == 'attacker':
            ids[dst] = attacker_id
        elif outcome == 'defender':
            ids[dst] = defender_id
    totals = {key: sum(row[key] for row in by_rank.values()) for key in COUNTERS}
    return {'by_rank': by_rank, 'weak': totals, 'miners_lost': miners_lost,
            'plies': len(moves), 'own_moves': own_moves, 'own_weak_moves': weak_moves,
            'description': 'No-disclosure deaths are descriptive, not proof of a mistake.'}


def activity(game, policy):
    """Analyze a full ``Tournament.game`` record for a participating policy."""
    sides = [army for army, key in enumerate(('red', 'blue')) if game[key] == policy]
    if len(sides) != 1:
        raise ValueError('policy must occur exactly once in game')
    position = Position()
    for army, key in enumerate(('red_setup', 'blue_setup')):
        if not valid_setup(game[key]):
            raise ValueError('invalid activity setup')
        position.place(army, game[key])
    result = analyze_events(position, game['moves'], sides[0])
    error = game['result'] == 'error'
    result.update(policy=policy, side=sides[0], appearances=1,
                  scored_games=int(not error), error_prefixes=int(error),
                  game_id=game.get('id'), seed=game.get('seed'),
                  pair_id=game.get('pair_id'), family=game.get('family'))
    return result
