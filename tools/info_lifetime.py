"""Classic pilot: preserve expendable pieces for a later *new* disclosure.

Frozen v1 design, not tuned on strength games. This is a bounded opportunity
cost added to the Context Teacher's final native-scale scores, never a veto.
It deliberately gives no speculative information reward: the earlier linked
scouting experiment often lost its useful continuation after the enemy reply.

Only public input is accepted by the API. Enemy ranks without CELL_REVEALED
are ignored even if an accidentally unmasked byte contains a physical rank.
"""

SETTINGS = {
    'version': 1,
    'expendable_ranks': (6, 8),  # Sergeant, Scout; preserve Miners and Spy roles.
    'known_losing_attack_cost': 32,
    'new_disclosed_exposure_cost': 16,
    'tactical_exceptions': 'bounded cost; immediate victory unchanged',
}


def _piece(cell):
    return cell < 254


def _adjacent(a, b):
    return abs(a % 10 - b % 10) + abs(a // 10 - b // 10) == 1


def _wins(attacker, defender):
    if defender == 11:
        return True
    if defender == 10:
        return attacker == 7
    if attacker == 9 and defender == 0:
        return True
    return attacker < defender


def _known_enemy(cell, army):
    return (_piece(cell) and bool(cell & 16) != bool(army)
            and bool(cell & 32) and (cell & 15) < 12)


def adjustments(cells, army, lost, histories, moves):
    """Return additive scores by move using only the current public position.

    ``lost`` and ``histories`` share the common strategy interface but are not
    needed here. Concealed attacks receive no penalty: even a losing probe can
    buy a new rank. Known wins/exchanges and already endangered origins receive
    no penalty either. The maximum cost is 32; a stronger tactical preference
    can therefore still justify losing a Scout or Sergeant.
    """
    if len(cells) != 100 or army not in (0, 1):
        raise ValueError('expected 100 public cells and army 0 or 1')
    result = {}
    for move in moves:
        src, dst = move
        actor, target = cells[src], cells[dst]
        rank = actor & 15
        penalty = 0
        if (_piece(actor) and bool(actor & 16) == bool(army)
                and rank in SETTINGS['expendable_ranks']):
            if _known_enemy(target, army):
                # Combat is attacker-asymmetric for Spy/Marshal and Miner/Bomb.
                # For our ranks, loss means the rank cannot win or exchange.
                if rank != (target & 15) and not _wins(rank, target & 15):
                    penalty = SETTINGS['known_losing_attack_cost']
            elif target == 255:
                # All disclosed pieces capable of beating Scout/Sergeant move
                # one square, so adjacency exactly describes their attack reach.
                for sq, enemy in enumerate(cells):
                    enemy_rank = enemy & 15
                    if (_known_enemy(enemy, army) and enemy_rank < 10
                            and _wins(enemy_rank, rank)
                            and _adjacent(sq, dst) and not _adjacent(sq, src)):
                        penalty = SETTINGS['new_disclosed_exposure_cost']
                        break
        result[move] = -penalty if moves[move] < 30000 else 0
    return result
