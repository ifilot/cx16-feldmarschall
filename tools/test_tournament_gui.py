"""Offscreen Qt6 integration: run a tournament, browse it, step and mask a board."""
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

from tournament_gui import QApplication, Desk, QFileDialog, QProcess, STYLE
from tournament_store import Tournament, verify


def main():
    app = QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    desk = Desk()
    desk.show()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'gui.fmtour'
        desk.first.setCurrentIndex(desk.first.findData('original-v1'))
        desk.second.setCurrentIndex(desk.second.findData('missions-v1-normal'))
        desk.rounds.setValue(1)
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(path), '')):
            desk.start_tournament()
        deadline = time.monotonic() + 55
        while desk.process.state() != QProcess.ProcessState.NotRunning and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        assert desk.process.state() == QProcess.ProcessState.NotRunning, 'GUI tournament timed out'
        assert desk.start.isEnabled(), desk.output
        assert path.exists(), desk.output
        assert verify(path)['games'] == 14
        assert desk.table.rowCount() == 14
        assert desk.slider.maximum() > 0
        desk.seek(1)
        assert desk.slider.value() == 1 and desk.board.last_move
        desk.perspective.setCurrentIndex(1)
        assert desk.board.perspective == 0
        desk.perspective.setCurrentIndex(2)
        assert desk.board.perspective == 1
        desk.seek(desk.slider.maximum())
        assert not desk.timer.isActive()
        desk.filter.setCurrentIndex(2)
        with Tournament(path) as tournament:
            assert desk.table.rowCount() == sum(g['result'] == 'draw' for g in tournament.games())
        desk.filter.setCurrentIndex(0)
        desk.table.selectRow(1)
        assert 'Match 2' in desk.match_title.text()
        desk.seek(min(60, desk.slider.maximum()))
        app.processEvents()
        destination = Path('build/tournament-desk.png')
        destination.parent.mkdir(exist_ok=True)
        assert desk.grab().save(str(destination))
        desk.close()
    print('Qt6: tournament launch, 14 games, reopen, filtering, individual replay, perspectives and navigation passed')


if __name__ == '__main__':
    main()
