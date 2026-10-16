"""Frozen release-port validation, separate from completed research campaigns."""
from pathlib import Path
import new_campaign_cycle as cycle

cycle.BASE = Path(__file__).resolve().parents[1]/'docs/ai-consolidation'
campaign_overview = cycle.overview


def overview():
    campaign_overview()
    path = cycle.BASE/'OVERVIEW.md'
    path.write_text(path.read_text().replace('# Two-hour honest Classic AI campaign',
                    '# Frozen AI release-port validation', 1))


cycle.overview = overview

if __name__ == '__main__':
    cycle.main()
