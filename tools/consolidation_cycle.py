"""Frozen release-port validation, separate from completed research campaigns."""
from pathlib import Path
import new_campaign_cycle as cycle

cycle.BASE = Path(__file__).resolve().parents[1]/'docs/ai-consolidation'

if __name__ == '__main__':
    cycle.main()
