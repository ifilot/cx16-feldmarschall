"""Qt6 Classic tournament desk. Run with Python + PySide6, Pillow and NumPy."""
import argparse
import json
from pathlib import Path
import sys

try:
    from PySide6.QtCore import QProcess, QRectF, QSize, Qt, QTimer
    from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout,
        QHBoxLayout, QHeaderView, QLabel, QListWidget, QMainWindow,
        QMessageBox, QProgressBar, QPushButton, QSlider, QSpinBox, QSplitter,
        QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
except ImportError:
    raise SystemExit('Qt6 is required: python -m pip install -r requirements-desktop.txt')

from ai_registry import ROOT, catalog
from tournament_store import Tournament, replay

STYLE = '''
QWidget { background: #888877; color: #111111; font-size: 13px; }
QLabel#masthead { font-family: serif; font-size: 25px; font-weight: bold; }
QMainWindow { background: #111111; }
QPushButton, QComboBox, QSpinBox, QLineEdit { background: #bbbbaa;
    border: 2px outset #eeddBB; padding: 6px; }
QPushButton:pressed { border-style: inset; background: #ccaa77; }
QPushButton:disabled { color: #666655; }
QTableWidget, QListWidget { background: #ccbbaa; alternate-background-color: #bbaa88;
    selection-background-color: #eebb44; selection-color: #111111; }
QHeaderView::section { background: #998855; padding: 5px; border: 1px solid #665533; }
QSlider::groove:horizontal { background: #665533; height: 5px; }
QSlider::handle:horizontal { background: #eebb44; width: 14px; margin: -5px 0; }
QProgressBar { border: 1px solid #665533; text-align: center; }
QProgressBar::chunk { background: #778844; }
'''


def pixmap(indices, colors, transparent=False):
    import numpy as np
    from palette import rgb
    rgba = np.empty((*indices.shape, 4), dtype=np.uint8)
    for i in range(16):
        rgba[indices == i] = (*rgb(i, colors), 0 if transparent and i == 0 else 255)
    image = QImage(rgba.data, rgba.shape[1], rgba.shape[0], rgba.strides[0], QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(image)


class Board(QWidget):
    def __init__(self):
        super().__init__()
        sys.path.insert(0, str(ROOT / 'assets/scripts'))
        from palette import RGB12, row_colors
        from pieces import build_tokens
        from terrain import generate
        self.background = pixmap(generate(), RGB12)
        tokens = build_tokens('classic')
        self.tokens = [[pixmap(t, row_colors(army + 1), True) for t in tokens] for army in range(2)]
        self.cells = [None] * 100
        self.last_move = None
        self.perspective = -1
        self.setMinimumSize(360, 360)

    def sizeHint(self):
        return QSize(540, 540)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        size = min(self.width(), self.height()) - 36
        painter.translate((self.width() - size) / 2, (self.height() - size) / 2)
        scale = size / 400
        painter.scale(scale, scale)
        painter.drawPixmap(0, 0, self.background)
        painter.setPen(QPen(QColor('#111111'), 0.8))
        for i in range(11):
            painter.drawLine(i * 40, 0, i * 40, 400)
            painter.drawLine(0, i * 40, 400, i * 40)
        for sq, cell in enumerate(self.cells):
            if cell:
                army, rank, moved, revealed = cell
                shown = rank if self.perspective in (-1, army) or revealed else 12
                painter.drawPixmap((sq % 10) * 40, (sq // 10) * 40, self.tokens[army][shown])
        if self.last_move:
            painter.setPen(QPen(QColor('#eebb44'), 2))
            for sq in self.last_move:
                painter.drawRect(QRectF(sq % 10 * 40 + 1, sq // 10 * 40 + 1, 38, 38))
        painter.setFont(QFont('serif', 9))
        painter.setPen(QColor('#111111'))
        for i in range(10):
            painter.drawText(QRectF(i * 40, 401, 40, 16), Qt.AlignmentFlag.AlignCenter, 'abcdefghij'[i])
            painter.drawText(QRectF(-22, i * 40, 20, 40), Qt.AlignmentFlag.AlignCenter, str(10 - i))


class Desk(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Feldmarschall — Classic Tournament Desk')
        self.resize(1380, 870)
        self.tournament = None
        self.states, self.moves = [], []
        self.process = None
        self.pending_path = None
        self.output = ''
        self.timer = QTimer(self)
        self.timer.setInterval(350)
        self.timer.timeout.connect(lambda: self.seek(self.slider.value() + 1))
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        title = QLabel('FELDMARSCHALL   /   TOURNAMENT DESK')
        title.setObjectName('masthead')
        title.setFont(QFont('serif', 23, QFont.Weight.Bold))
        outer.addWidget(title)
        subtitle = QLabel('Classic rules · paired games · named, preserved AI versions')
        outer.addWidget(subtitle)
        controls = QHBoxLayout()
        self.first, self.second = QComboBox(), QComboBox()
        for policy in catalog():
            label = f'{policy["name"]}  —  {policy["id"]} [{policy["status"]}]'
            for combo in (self.first, self.second):
                combo.addItem(label, policy['id'])
                combo.setItemData(combo.count() - 1, policy['description'], Qt.ItemDataRole.ToolTipRole)
        self.first.setCurrentIndex(max(0, self.first.findData('student-guard-v1-normal')))
        self.second.setCurrentIndex(max(0, self.second.findData('missions-v1-normal')))
        self.rounds = QSpinBox()
        self.rounds.setRange(1, 100000)
        self.rounds.setValue(10)
        self.seed = QSpinBox()
        self.seed.setRange(1, 2147483647)
        self.seed.setValue(1)
        self.start = QPushButton('Run tournament…')
        self.start.clicked.connect(self.start_tournament)
        open_button = QPushButton('Open…')
        open_button.clicked.connect(self.open_dialog)
        for label, widget in (('AI A', self.first), ('AI B', self.second), ('Rounds / family', self.rounds), ('Seed', self.seed)):
            box = QVBoxLayout()
            box.addWidget(QLabel(label))
            box.addWidget(widget)
            controls.addLayout(box, 1 if widget in (self.first, self.second) else 0)
        controls.addWidget(self.start)
        controls.addWidget(open_button)
        outer.addLayout(controls)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        outer.addWidget(self.progress)
        self.summary = QLabel('Open a tournament to review it, or choose two AI versions and run a new one.')
        self.summary.setWordWrap(True)
        outer.addWidget(self.summary)
        self.breakdown = QLabel('')
        self.breakdown.setWordWrap(True)
        outer.addWidget(self.breakdown)
        splitter = QSplitter()
        outer.addWidget(splitter, 1)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.filter = QComboBox()
        self.filter.addItems(['All matches', 'Decisive matches', 'Draws', 'Reached move limit'])
        self.filter.currentIndexChanged.connect(self.populate)
        left_layout.addWidget(self.filter)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Match', 'Layout', 'Red', 'Blue', 'Result', 'Plies'])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.select_match)
        left_layout.addWidget(self.table)
        splitter.addWidget(left)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.match_title = QLabel('Match replay')
        self.match_title.setWordWrap(True)
        right_layout.addWidget(self.match_title)
        self.perspective = QComboBox()
        self.perspective.addItems(['Both armies revealed', 'Red’s view', 'Blue’s view'])
        self.perspective.currentIndexChanged.connect(self.change_view)
        right_layout.addWidget(self.perspective)
        self.board = Board()
        right_layout.addWidget(self.board, 1)
        navigation = QHBoxLayout()
        for label, callback in [('Start', lambda: self.seek(0)), ('Previous', lambda: self.seek(self.slider.value() - 1)),
                                 ('Play / pause', self.toggle_play), ('Next', lambda: self.seek(self.slider.value() + 1)),
                                 ('End', lambda: self.seek(self.slider.maximum()))]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            navigation.addWidget(button)
        right_layout.addLayout(navigation)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self.display_ply)
        right_layout.addWidget(self.slider)
        self.ply_label = QLabel('No match selected')
        right_layout.addWidget(self.ply_label)
        splitter.addWidget(right)
        self.events = QListWidget()
        self.events.currentRowChanged.connect(lambda row: self.seek(row + 1) if row >= 0 else None)
        splitter.addWidget(self.events)
        splitter.setSizes([440, 640, 260])

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open tournament', str(ROOT / 'build/tournaments'), 'Feldmarschall tournaments (*.fmtour)')
        if path:
            self.load(path)

    def load(self, path):
        try:
            replacement = Tournament(path)
            metadata, summary = replacement.metadata(), replacement.summary()
            if metadata['rules'] != 'classic':
                replacement.close()
                raise ValueError('Only Classic tournaments are supported')
        except Exception as error:
            QMessageBox.critical(self, 'Cannot open tournament', str(error))
            return
        self.timer.stop()
        if self.tournament:
            self.tournament.close()
        self.tournament = replacement
        standings = []
        for identity, result in summary['standings'].items():
            score = f'{100 * result["score"]:.1f}%' if result['score'] is not None else '—'
            standings.append(f'{identity}: {score} ({result["wins"]} W / {result["draws"]} D / {result["losses"]} L)')
        self.summary.setText(f'{Path(path).name} · {summary["status"]} · {summary["games"]}/{metadata["planned_games"]} games\n' + '\n'.join(standings))
        self.summary.setToolTip(json.dumps(metadata, indent=2))
        family_lines = ['Scores by layout family (win = 1; draw = ½):']
        for family, scores in summary['families'].items():
            family_lines.append(family + ': ' + ', '.join(f'{identity} {100 * score:.1f}%' for identity, score in scores.items()))
        family_lines.append('Endings: ' + ', '.join(f'{reason}: {count}' for reason, count in summary['endings'].items()))
        family_lines.append(f'Average length: {summary["average_plies"]:.1f} plies')
        self.summary.setToolTip('\n'.join(family_lines) + '\n\n' + json.dumps(metadata, indent=2))
        family_scores = []
        for family, scores in summary['families'].items():
            family_scores.append(f'{family}: ' + ' / '.join(f'{score * 100:.1f}%' for score in scores.values()))
        self.breakdown.setText('Scores by layout, in the AI order above: ' + ' · '.join(family_scores) +
                               '\nEndings: ' + ', '.join(f'{reason}: {count}' for reason, count in summary['endings'].items()) +
                               f' · Average length: {summary["average_plies"]:.1f} plies')
        if not self.process or self.process.state() == QProcess.ProcessState.NotRunning:
            self.progress.setRange(0, metadata['planned_games'])
            self.progress.setValue(summary['games'])
        self.populate()

    def populate(self):
        if not self.tournament:
            return
        self.timer.stop()
        games = self.tournament.games()
        mode = self.filter.currentIndex()
        games = [g for g in games if mode == 0 or mode == 1 and g['result'] != 'draw'
                 or mode == 2 and g['result'] == 'draw' or mode == 3 and g['reason'] == 'ply limit']
        self.table.blockSignals(True)
        self.table.setRowCount(len(games))
        for row, game in enumerate(games):
            for col, value in enumerate((game['id'], game['family'], game['red'], game['blue'], game['result'], game['plies'])):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, game['id'])
                item.setToolTip(f'Pair {game["pair_id"]} · {game["reason"]} · seed {game["seed"]}')
                self.table.setItem(row, col, item)
        self.table.blockSignals(False)
        if games:
            self.table.selectRow(0)
        else:
            self.states, self.moves = [], []
            self.events.clear()
            self.board.cells = [None] * 100
            self.board.last_move = None
            self.board.update()
            self.slider.setRange(0, 0)
            self.match_title.setText('No matches in this selection')
            self.ply_label.setText('No match selected')

    def select_match(self):
        items = self.table.selectedItems()
        if not items or not self.tournament:
            return
        self.timer.stop()
        try:
            game = self.tournament.game(items[0].data(Qt.ItemDataRole.UserRole))
            self.states, events = replay(game)
        except Exception as error:
            QMessageBox.critical(self, 'Cannot replay match', str(error))
            return
        self.moves = game['moves']
        self.match_title.setText(f'Match {game["id"]} · pair {game["pair_id"]} · {game["family"]}\n'
                                f'Red: {game["red"]}\nBlue: {game["blue"]}\n'
                                f'{game["result"].title()} · {game["reason"]}')
        self.events.blockSignals(True)
        self.events.clear()
        self.events.addItems(events)
        self.events.blockSignals(False)
        self.slider.setRange(0, len(self.moves))
        self.seek(0)

    def change_view(self, index):
        self.board.perspective = index - 1
        self.board.update()

    def seek(self, ply):
        self.slider.setValue(max(0, min(ply, self.slider.maximum())))
        self.display_ply(self.slider.value())

    def display_ply(self, ply):
        if not self.states:
            return
        self.board.cells = self.states[ply]
        self.board.last_move = self.moves[ply - 1] if ply else None
        self.board.update()
        self.ply_label.setText(f'Ply {ply} / {len(self.moves)}' + (' · starting position' if not ply else ''))
        self.events.blockSignals(True)
        self.events.setCurrentRow(ply - 1)
        self.events.blockSignals(False)
        if ply == len(self.moves):
            self.timer.stop()

    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
        elif self.states:
            if self.slider.value() == self.slider.maximum():
                self.seek(0)
            self.timer.start()

    def start_tournament(self):
        if self.first.currentData() == self.second.currentData():
            QMessageBox.information(self, 'Choose opponents', 'Choose two different AI versions.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save new tournament', str(ROOT / 'build/tournaments/new.fmtour'), 'Feldmarschall tournaments (*.fmtour)')
        if not path:
            return
        if not path.endswith('.fmtour'):
            path += '.fmtour'
        if Path(path).exists():
            QMessageBox.information(self, 'Existing tournament', 'Choose a new filename; existing tournaments are preserved.')
            return
        self.pending_path, self.output = path, ''
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.process_output)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.start.setEnabled(False)
        self.progress.setRange(0, self.rounds.value() * 14)
        self.progress.setValue(0)
        self.summary.setText('Building selected AI versions and running Classic matches…')
        self.process.start(sys.executable, [str(ROOT / 'tools/tournament.py'), 'run', self.first.currentData(),
                           self.second.currentData(), '--out', path, '--rounds', str(self.rounds.value()),
                           '--seed', str(self.seed.value())])

    def process_output(self):
        self.output += bytes(self.process.readAllStandardOutput()).decode(errors='replace')
        for line in self.output.splitlines():
            try:
                event = json.loads(line)
                if event.get('event') == 'progress':
                    self.progress.setValue(event['completed'])
            except (ValueError, AttributeError):
                pass

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.start.setEnabled(True)
            QMessageBox.critical(self, 'Cannot start tournament', self.process.errorString())

    def process_finished(self, code, status):
        self.process_output()
        self.start.setEnabled(True)
        if code:
            QMessageBox.critical(self, 'Tournament stopped', self.output[-4000:])
        if Path(self.pending_path).exists():
            self.load(self.pending_path)

    def closeEvent(self, event):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, 'Tournament running', 'Let the current tournament finish before closing the desk.')
            event.ignore()
            return
        self.timer.stop()
        if self.tournament:
            self.tournament.close()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tournament', nargs='?', type=Path)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    desk = Desk()
    if args.tournament:
        desk.load(args.tournament)
    desk.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
