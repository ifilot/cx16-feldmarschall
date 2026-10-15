"""Public recurrence escape v1: short-term memory across alternating actors.

Motivation: the existing single-move backtrack cost cannot recognize loops
formed by alternating two friendly pieces. The mechanism is inspired by the
short-term memory/diversification principle in Glover, Tabu Search Part I
(1989), https://doi.org/10.1287/ijoc.1.3.190 . It is a bounded game policy
experiment, not a claim that optimization tabu-search results prove game strength.

One instance belongs to one game and side. Call reset() on every new game.
Only call adjustments once per actual decision, never for hypothetical worlds.
"""
from collections import Counter, deque

VERSION = 'public-recurrence-escape-v1'
SETTINGS = dict(window=32, quiet_decisions=16, recurring_root_visits=3,
                recurring_destination_visits=2, aspiration_margin=32,
                recurrence_penalty=24)


def _own_key(cells, army):
    return tuple((sq, cell & 15) for sq, cell in enumerate(cells)
                 if cell < 254 and bool(cell & 16) == bool(army))


def _progress_key(cells, army):
    # A capture or a new rank disclosure is irreversible public progress.
    # Position changes of disclosed enemies do not erase recurrence memory.
    return (sum(cell < 254 for cell in cells),
            tuple(sorted(cell & 15 for cell in cells if cell < 254
                         and bool(cell & 16) != bool(army) and cell & 32)))


class RecurrenceEscape:
    def __init__(self):
        self.reset()

    def reset(self):
        self.history = deque(maxlen=SETTINGS['window'])
        self.progress = None
        self.quiet = 0
        self.last_report = {}

    def adjustments(self, cells, army, lost, histories, moves):
        """Penalize a repeatedly visited own formation when an alternative exists.

        A repeated formation alone never suffices: sixteen quiet decisions and
        three visits to the current formation are required, plus a less-visited
        quiet continuation within 32 native points of the best existing move.
        Captures, immediate wins and all tactical scores otherwise stay intact.
        Enemy concealed rank bits, lost counts, histories and setups are unused.
        """
        if len(cells) != 100 or army not in (0, 1):
            raise ValueError('expected 100 public cells and army 0 or 1')
        progress = _progress_key(cells, army)
        if progress != self.progress:
            self.history.clear()
            self.quiet = 0
            self.progress = progress
        else:
            self.quiet += 1
        root = _own_key(cells, army)
        self.history.append(root)
        counts = Counter(self.history)
        result = dict.fromkeys(moves, 0.0)
        self.last_report = dict(quiet_decisions=self.quiet, root_visits=counts[root],
                                active=False, novel_alternatives=0, penalized_moves=0)
        if (not moves or self.quiet < SETTINGS['quiet_decisions']
                or counts[root] < SETTINGS['recurring_root_visits']
                or max(moves.values()) >= 30000):
            return result
        visits = {}
        for move in moves:
            src, dst = move
            if cells[dst] != 255 or cells[src] >= 254:
                continue
            after = list(cells)
            after[dst], after[src] = after[src], 255
            visits[move] = counts[_own_key(after, army)]
        best = max(moves.values())
        novel = [move for move, n in visits.items()
                 if n < SETTINGS['recurring_destination_visits']
                 and moves[move] >= best - SETTINGS['aspiration_margin']]
        if not novel:
            return result
        for move, n in visits.items():
            if n >= SETTINGS['recurring_destination_visits']:
                result[move] = -float(SETTINGS['recurrence_penalty'])
        self.last_report.update(active=True, novel_alternatives=len(novel),
                                penalized_moves=sum(bool(v) for v in result.values()))
        return result
