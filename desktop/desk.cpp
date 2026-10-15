#include "desk.h"
#include <QCloseEvent>
#include <QComboBox>
#include <QDir>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QFont>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QListWidget>
#include <QMessageBox>
#include <QPainter>
#include <QProgressBar>
#include <QPushButton>
#include <QSignalBlocker>
#include <QSlider>
#include <QSpinBox>
#include <QSplitter>
#include <QSqlError>
#include <QSqlQuery>
#include <QTableWidget>
#include <QThread>
#include <QTimer>
#include <QUuid>
#include <QVBoxLayout>
#include <algorithm>
#include <stdexcept>
#include <zlib.h>

static void require(bool ok, const QString &message) {
    if (!ok) throw std::runtime_error(message.toStdString());
}
TournamentFile::TournamentFile(const QString &path) {
    connection = QUuid::createUuid().toString();
    db = QSqlDatabase::addDatabase("QSQLITE", connection);
    db.setConnectOptions("QSQLITE_OPEN_READONLY");
    db.setDatabaseName(path);
    try {
        require(db.open(), db.lastError().text());
        QSqlQuery query(db);
        require(query.exec("PRAGMA user_version") && query.next() &&
                (query.value(0).toInt() == 1 || query.value(0).toInt() == 2), "Unsupported tournament format");
        require(query.exec("SELECT key,value FROM metadata"), query.lastError().text());
        while (query.next()) {
            QJsonParseError error;
            auto value = QJsonDocument::fromJson("[" + query.value(1).toByteArray() + "]", &error).array();
            require(error.error == QJsonParseError::NoError && value.size() == 1, "Invalid tournament metadata");
            metadata[query.value(0).toString()] = value[0];
        }
        require(metadata["rules"] == "classic", "Only Classic tournaments are supported");
        require(metadata["participants"].toArray().size() == 2, "Tournament must have two participants");
        require(query.exec("SELECT id,pair_id,family,red,blue,result,reason,plies FROM games ORDER BY id"), query.lastError().text());
        while (query.next()) games.push_back({query.value(0).toInt(), query.value(1).toInt(), query.value(7).toInt(),
                query.value(2).toString(), query.value(3).toString(), query.value(4).toString(), query.value(5).toString(), query.value(6).toString()});
    } catch (...) {
        db.close(); db = {}; QSqlDatabase::removeDatabase(connection); throw;
    }
}
TournamentFile::~TournamentFile() {
    db.close(); db = {}; QSqlDatabase::removeDatabase(connection);
}
Replay TournamentFile::replay(int id) const {
    QSqlQuery query(db);
    query.prepare("SELECT red_setup,blue_setup,plies,moves,result,reason FROM games WHERE id=?");
    query.addBindValue(id);
    require(query.exec() && query.next(), "Match could not be read");
    int plies = query.value(2).toInt();
    require(plies >= 0 && plies <= metadata["max_plies"].toInt(), "Invalid trace length");
    auto compressed = query.value(3).toByteArray();
    QByteArray raw(std::max(1, plies * 2), '\0');
    uLongf length = raw.size();
    require(uncompress(reinterpret_cast<Bytef *>(raw.data()), &length,
                       reinterpret_cast<const Bytef *>(compressed.constData()), compressed.size()) == Z_OK &&
                       length == uLongf(plies * 2), "Corrupt compressed move trace");
    Classic::Position position;
    position.place(0, query.value(0).toString()); position.place(1, query.value(1).toString());
    Replay replay; replay.frames.push_back(position);
    bool flagCaptured = false;
    for (int ply = 0; ply < plies; ++ply) {
        Classic::Move move{static_cast<unsigned char>(raw[ply * 2]), static_cast<unsigned char>(raw[ply * 2 + 1])};
        require(!flagCaptured && position.legal(move, ply % 2), QString("Illegal recorded move at ply %1").arg(ply + 1));
        const auto attacker = position.cells[move.first], defender = position.cells[move.second];
        QString event = QString("%1  %2  %3 → %4").arg(ply + 1).arg(ply % 2 == 0 ? "Red" : "Blue")
                .arg(Classic::squareName(move.first), Classic::squareName(move.second));
        if (defender.occupied()) event += QString("  %1 × %2").arg(Classic::Glyphs[attacker.rank], Classic::Glyphs[defender.rank]);
        flagCaptured = defender.rank == Classic::Flag;
        position.apply(move); replay.moves.push_back(move); replay.frames.push_back(position); replay.events.append(event);
    }
    auto result = query.value(4).toString(), reason = query.value(5).toString();
    int side = plies % 2;
    if (result == "error") require(!flagCaptured && reason.startsWith("engine error: "), "Invalid unscored error record");
    else if (flagCaptured) require(reason == "flag" && result == (side == 1 ? "red" : "blue"), "Incorrect flag result");
    else if (position.moves(side).empty()) {
        bool otherMoves = !position.moves(1 - side).empty();
        require(reason == (otherMoves ? "no moves" : "neither can move") &&
                result == (otherMoves ? side == 0 ? "blue" : "red" : "draw"), "Incorrect no-move result");
    } else require(reason == "ply limit" && result == "draw" && plies == metadata["max_plies"].toInt(), "Incorrect move-limit result");
    return replay;
}

Board::Board(QWidget *parent) : QWidget(parent), terrain(":/game/board.png") {
    setMinimumSize(340, 340);
    require(!terrain.isNull(), "Embedded board artwork is missing");
    for (int army = 0; army < 2; ++army)
        for (int rank = 0; rank < 13; ++rank) {
            tokens[army][rank].load(QString(":/game/token-%1-%2.png").arg(army).arg(rank));
            require(!tokens[army][rank].isNull(), "Embedded piece artwork is missing");
        }
}
void Board::paintEvent(QPaintEvent *) {
    QPainter p(this);
    p.setRenderHint(QPainter::SmoothPixmapTransform, false);
    int size = std::min(width(), height()) - 38;
    p.translate((width() - size) / 2.0, (height() - size) / 2.0); p.scale(size / 400.0, size / 400.0);
    p.drawPixmap(0, 0, terrain);
    p.setPen(QPen(QColor("#111111"), 0.8));
    for (int i = 0; i <= 10; ++i) { p.drawLine(i * 40, 0, i * 40, 400); p.drawLine(0, i * 40, 400, i * 40); }
    for (int sq = 0; sq < 100; ++sq) {
        const auto &cell = position.cells[sq];
        if (!cell.occupied()) continue;
        int shown = perspective < 0 || cell.army == perspective || cell.revealed ? cell.rank : 12;
        p.drawPixmap(sq % 10 * 40, sq / 10 * 40, tokens[cell.army][shown]);
    }
    p.setPen(QPen(QColor("#eebb44"), 2));
    if (lastMove.first >= 0) for (int sq : {lastMove.first, lastMove.second}) p.drawRect(sq % 10 * 40 + 1, sq / 10 * 40 + 1, 38, 38);
    p.setPen(QColor("#111111")); p.setFont(QFont("serif", 9));
    for (int i = 0; i < 10; ++i) {
        p.drawText(QRectF(i * 40, 401, 40, 16), Qt::AlignCenter, QString(QChar('a' + i)));
        p.drawText(QRectF(-24, i * 40, 22, 40), Qt::AlignCenter, QString::number(10 - i));
    }
}

Desk::Desk(QString project, QString pythonProgram, QString workerProgram)
    : root(std::move(project)), python(std::move(pythonProgram)), worker(std::move(workerProgram)) {
    setWindowTitle("Feldmarschall — Classic Tournament Desk"); resize(1440, 960);
    setStyleSheet(R"(
        QWidget { background: #888877; color: #111111; font-size: 13px; }
        QLabel#masthead { font-family: serif; font-size: 25px; font-weight: bold; }
        QPushButton,QComboBox,QSpinBox { background:#bbbbaa; border:2px outset #eeddbb; padding:5px; }
        QPushButton:pressed { border-style:inset; background:#ccaa77; }
        QPushButton:disabled { color:#666655; }
        QTableWidget,QListWidget { background:#ccbbaa; alternate-background-color:#bbaa88;
            selection-background-color:#eebb44; selection-color:#111111; }
        QHeaderView::section { background:#998855; padding:5px; border:1px solid #665533; }
        QProgressBar { border:1px solid #665533; text-align:center; }
        QProgressBar::chunk { background:#778844; }
        QSlider::groove:horizontal { background:#665533; height:5px; }
        QSlider::handle:horizontal { background:#eebb44; width:14px; margin:-5px 0; }
    )");
    auto *central = new QWidget(this); setCentralWidget(central); auto *layout = new QVBoxLayout(central);
    auto *title = new QLabel("FELDMARSCHALL  /  TOURNAMENT DESK"); title->setObjectName("masthead"); layout->addWidget(title);
    layout->addWidget(new QLabel("Classic rules · preserved AI versions · parallel tournaments"));
    auto *controls = new QHBoxLayout(); layout->addLayout(controls);
    first = new QComboBox(); second = new QComboBox();
    QFile registry(root + "/ai/registry.json"); require(registry.open(QIODevice::ReadOnly), "Cannot read AI catalog; select the project with --project");
    for (auto entry : QJsonDocument::fromJson(registry.readAll()).object()["policies"].toArray()) {
        auto policy = entry.toObject();
        auto label = policy["name"].toString() + " — " + policy["id"].toString() + " [" + policy["status"].toString() + "]";
        for (auto *combo : {first, second}) {
            combo->addItem(label, policy["id"].toString());
            combo->setItemData(combo->count() - 1, policy["description"].toString(), Qt::ToolTipRole);
        }
    }
    require(first->count() > 1, "At least two registered policies are required");
    first->setCurrentIndex(std::max(0, first->findData("student-guard-v1-normal")));
    second->setCurrentIndex(std::max(0, second->findData("missions-v1-normal")));
    rounds = new QSpinBox(); rounds->setRange(1, 100000); rounds->setValue(10);
    seed = new QSpinBox(); seed->setRange(1, 2147483647); seed->setValue(1);
    threads = new QSpinBox(); threads->setRange(1, std::max(1, QThread::idealThreadCount()));
    bool envOk; int requested = qEnvironmentVariable("OMP_NUM_THREADS").section(',', 0, 0).toInt(&envOk);
    threads->setValue(envOk && requested > 0 ? requested : std::min(4, threads->maximum()));
    threads->setToolTip("Independent matches evaluated simultaneously");
    for (auto control : {std::pair<QString,QWidget*>{"AI A",first}, {"AI B",second}, {"Rounds / family",rounds}, {"Seed",seed}, {"Workers",threads}}) {
        auto *column = new QVBoxLayout(); column->addWidget(new QLabel(control.first)); column->addWidget(control.second);
        controls->addLayout(column, control.second == first || control.second == second ? 1 : 0);
    }
    start = new QPushButton("Run tournament…"); auto *open = new QPushButton("Open…"); controls->addWidget(start); controls->addWidget(open);
    connect(start, &QPushButton::clicked, this, [this] {
        auto path = QFileDialog::getSaveFileName(this, "Save new tournament", root + "/build/tournaments/new.fmtour", "Tournaments (*.fmtour)");
        if (!path.isEmpty()) { if (!path.endsWith(".fmtour")) path += ".fmtour"; startRun(path); }
    });
    connect(open, &QPushButton::clicked, this, [this] {
        auto path = QFileDialog::getOpenFileName(this, "Open tournament", root + "/build/tournaments", "Tournaments (*.fmtour)");
        if (!path.isEmpty()) try { openTournament(path); } catch (const std::exception &e) { reportError(e.what()); }
    });
    progress = new QProgressBar(); progress->setRange(0, 1); progress->setValue(0); layout->addWidget(progress);
    summary = new QLabel("Choose two AI versions to run a tournament, or open a saved tournament."); summary->setWordWrap(true); layout->addWidget(summary);
    breakdown = new QLabel(); breakdown->setWordWrap(true); layout->addWidget(breakdown);
    auto *splitter = new QSplitter(); layout->addWidget(splitter, 1);
    auto *left = new QWidget(); auto *leftLayout = new QVBoxLayout(left);
    filter = new QComboBox(); filter->addItems({"All matches","Decisive matches","Draws","Reached move limit","Engine errors"}); leftLayout->addWidget(filter);
    connect(filter, &QComboBox::currentIndexChanged, this, [this] { populate(); });
    table = new QTableWidget(0, 6); table->setHorizontalHeaderLabels({"Match","Layout","Red","Blue","Result","Plies"});
    table->setSelectionBehavior(QAbstractItemView::SelectRows); table->setSelectionMode(QAbstractItemView::SingleSelection);
    table->setEditTriggers(QAbstractItemView::NoEditTriggers); table->setAlternatingRowColors(true);
    table->horizontalHeader()->setSectionResizeMode(QHeaderView::ResizeToContents); leftLayout->addWidget(table);
    connect(table, &QTableWidget::itemSelectionChanged, this, [this] { selectMatch(); }); splitter->addWidget(left);
    auto *right = new QWidget(); auto *rightLayout = new QVBoxLayout(right);
    matchTitle = new QLabel("Match replay"); matchTitle->setWordWrap(true); rightLayout->addWidget(matchTitle);
    perspective = new QComboBox(); perspective->addItems({"Both armies revealed","Red’s view","Blue’s view"}); rightLayout->addWidget(perspective);
    board = new Board(); rightLayout->addWidget(board, 1);
    connect(perspective, &QComboBox::currentIndexChanged, this, [this](int index) { board->perspective = index - 1; board->update(); });
    auto *navigation = new QHBoxLayout(); rightLayout->addLayout(navigation);
    slider = new QSlider(Qt::Horizontal); slider->setRange(0, 0); timer = new QTimer(this); timer->setInterval(350);
    auto addButton = [&](const QString &text, std::function<void()> action) {
        auto *button = new QPushButton(text); connect(button, &QPushButton::clicked, this, action); navigation->addWidget(button);
    };
    addButton("Start", [this] { slider->setValue(0); });
    addButton("Previous", [this] { slider->setValue(slider->value() - 1); });
    addButton("Play / pause", [this] {
        if (timer->isActive()) timer->stop();
        else if (!current.frames.empty()) { if (slider->value() == slider->maximum()) slider->setValue(0); timer->start(); }
    });
    addButton("Next", [this] { slider->setValue(slider->value() + 1); });
    addButton("End", [this] { slider->setValue(slider->maximum()); });
    connect(timer, &QTimer::timeout, this, [this] { slider->setValue(slider->value() + 1); });
    connect(slider, &QSlider::valueChanged, this, [this](int ply) { displayPly(ply); });
    rightLayout->addWidget(slider); plyLabel = new QLabel("No match selected"); rightLayout->addWidget(plyLabel); splitter->addWidget(right);
    events = new QListWidget(); splitter->addWidget(events); splitter->setSizes({430, 650, 260});
    connect(events, &QListWidget::currentRowChanged, this, [this](int row) { if (row >= 0) slider->setValue(row + 1); });
}

void Desk::openTournament(const QString &path) {
    auto replacement = std::make_unique<TournamentFile>(path);
    timer->stop(); tournament = std::move(replacement);
    auto participants = tournament->metadata["participants"].toArray();
    QStringList lines{QString("%1 · %2 · %3 / %4 games").arg(QFileInfo(path).fileName(), tournament->metadata["status"].toString())
            .arg(tournament->games.size()).arg(tournament->metadata["planned_games"].toInt())};
    if (tournament->metadata["setup_mode"].toString() == "policy-owned")
        lines.append(QString("Deployment comparison: %1 chooses its army; armies follow players across sides.")
                     .arg(tournament->metadata["setup_owner"].toString()));
    QMap<QString, std::array<double, 2>> families; QMap<QString, int> endings; double totalPlies = 0;
    for (int n = 0; n < 2; ++n) {
        QString id = participants[n].toObject()["policy"].toObject()["id"].toString();
        int wins = 0, draws = 0, scored = 0;
        for (const auto &game : tournament->games) {
            if (n == 0) { ++endings[game.result == "error" ? "engine error" : game.reason]; totalPlies += game.plies; }
            if (game.result == "error") continue;
            ++scored;
            bool won = game.result == (game.red == id ? "red" : "blue");
            wins += won; draws += game.result == "draw";
            families[game.family][n] += won ? 1 : game.result == "draw" ? 0.5 : 0;
        }
        QString score = scored == 0 ? "—" : QString::number((wins + draws * 0.5) * 100 / scored, 'f', 1) + '%';
        lines.append(QString("%1: %2 (%3 W / %4 D / %5 L)").arg(id, score).arg(wins).arg(draws).arg(scored - wins - draws));
    }
    const auto errors = std::count_if(tournament->games.begin(), tournament->games.end(), [](const Match &g) { return g.result == "error"; });
    if (errors) lines.append(QString("%1 unscored engine errors; excluded from win rates.").arg(errors));
    for (const auto &participant : participants)
        if (participant.toObject()["policy"].toObject()["information_model"].toString() == "diagnostic-full-enemy-ranks")
            lines.append("DIAGNOSTIC ONLY: teacher knows all surviving enemy ranks; unsuitable for normal play.");
        else if (participant.toObject()["policy"].toObject()["information_model"].toString() == "diagnostic-flag-spy")
            lines.append("DIAGNOSTIC ONLY: teacher knows the enemy Flag and Spy; unsuitable for normal play.");
        else if (participant.toObject()["policy"].toObject()["information_model"].toString() == "diagnostic-flag")
            lines.append("DIAGNOSTIC ONLY: teacher knows the enemy Flag; Spy and other concealed ranks stay hidden.");
    for (const auto &participant : participants)
        if (participant.toObject()["policy"].toObject()["driver"].toString() == "msdos1990") {
            lines.append("MS-DOS 1990 uses its original access to hidden enemy ranks.");
            break;
        }
    summary->setText(lines.join('\n')); summary->setToolTip(QString::fromUtf8(QJsonDocument(tournament->metadata).toJson()));
    summary->setMinimumHeight(summary->fontMetrics().lineSpacing() * lines.size() + 8);
    QStringList scores, reasons;
    for (auto it = families.cbegin(); it != families.cend(); ++it) {
        int count = int(std::count_if(tournament->games.begin(), tournament->games.end(), [&](const Match &g) { return g.family == it.key() && g.result != "error"; }));
        scores.append(QString("%1: %2% / %3%").arg(it.key()).arg(it.value()[0] * 100 / count, 0, 'f', 1).arg(it.value()[1] * 100 / count, 0, 'f', 1));
    }
    for (auto it = endings.cbegin(); it != endings.cend(); ++it) reasons.append(it.key() + ": " + QString::number(it.value()));
    breakdown->setText("Scores by layout, in AI order above: " + scores.join(" · ") + "\nEndings: " + reasons.join(", ") +
        QString(" · Average length: %1 plies").arg(tournament->games.empty() ? 0 : totalPlies / tournament->games.size(), 0, 'f', 1));
    breakdown->setMinimumHeight(breakdown->fontMetrics().lineSpacing() * 3 + 8);
    progress->setRange(0, tournament->metadata["planned_games"].toInt()); progress->setValue(int(tournament->games.size()));
    populate();
}
void Desk::populate() {
    if (!tournament) return;
    timer->stop(); QSignalBlocker block(table); table->setRowCount(0);
    int mode = filter->currentIndex();
    for (const auto &g : tournament->games) {
        if ((mode == 1 && g.result != "red" && g.result != "blue") || (mode == 2 && g.result != "draw") || (mode == 3 && g.reason != "ply limit") || (mode == 4 && g.result != "error")) continue;
        int row = table->rowCount(); table->insertRow(row);
        QStringList values{QString::number(g.id), g.family, g.red, g.blue, g.result, QString::number(g.plies)};
        for (int col = 0; col < 6; ++col) {
            auto *item = new QTableWidgetItem(values[col]); item->setData(Qt::UserRole, g.id);
            item->setToolTip(QString("Pair %1 · %2").arg(g.pair).arg(g.reason)); table->setItem(row, col, item);
        }
    }
    block.unblock();
    if (table->rowCount()) { table->selectRow(0); }
    else {
        current = {}; QSignalBlocker eventsBlock(events); events->clear(); slider->setRange(0, 0);
        board->position = {}; board->lastMove = {-1,-1}; board->update();
        matchTitle->setText("No matches in this selection"); plyLabel->setText("No match selected");
    }
}
void Desk::selectMatch() {
    if (!tournament || table->selectedItems().isEmpty()) return;
    timer->stop(); int id = table->selectedItems().first()->data(Qt::UserRole).toInt();
    try {
        auto replacement = tournament->replay(id); current = std::move(replacement);
        auto game = std::find_if(tournament->games.begin(), tournament->games.end(), [id](const Match &g) { return g.id == id; });
        matchTitle->setText(QString("Match %1 · pair %2 · %3\nRed: %4\nBlue: %5\n%6 · %7")
            .arg(id).arg(game->pair).arg(game->family, game->red, game->blue, game->result, game->reason));
        QSignalBlocker block(events); events->clear(); events->addItems(current.events);
        slider->setRange(0, int(current.moves.size())); slider->setValue(0); displayPly(0);
    } catch (const std::exception &error) { current = {}; reportError(error.what()); }
}
void Desk::displayPly(int ply) {
    if (current.frames.empty() || ply < 0 || ply >= int(current.frames.size())) return;
    board->position = current.frames[ply]; board->lastMove = ply ? current.moves[ply - 1] : Classic::Move{-1,-1}; board->update();
    plyLabel->setText(QString("Ply %1 / %2").arg(ply).arg(current.moves.size()));
    QSignalBlocker block(events); events->setCurrentRow(ply - 1);
    if (ply == slider->maximum()) timer->stop();
}
void Desk::reportError(const QString &message) {
    if (smoke) { qWarning().noquote() << message; }
    else QMessageBox::critical(this, "Tournament desk", message);
}
void Desk::startRun(const QString &path, int maxPlies) {
    if (process && process->state() != QProcess::NotRunning) return;
    if (first->currentData() == second->currentData()) { reportError("Choose two different AI versions."); if (smoke && finished) finished(false); return; }
    if (QFileInfo::exists(path)) { reportError("Choose a new filename; existing tournaments are preserved."); if (smoke && finished) finished(false); return; }
    if (!QFileInfo::exists(worker)) { reportError("The native tournament worker is missing. Build the desktop targets first."); if (smoke && finished) finished(false); return; }
    if (process) process->deleteLater();
    process = new QProcess(this); pendingOutput.clear(); log.clear(); pendingPath = path;
    process->setWorkingDirectory(root); process->setProcessChannelMode(QProcess::MergedChannels);
    connect(process, &QProcess::readyReadStandardOutput, this, [this] { processOutput(); });
    connect(process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error == QProcess::FailedToStart) { start->setEnabled(true); reportError(process->errorString()); if (finished) finished(false); }
    });
    connect(process, &QProcess::finished, this, [this](int code, QProcess::ExitStatus exitStatus) {
        processOutput(); start->setEnabled(true); bool ok = code == 0 && exitStatus == QProcess::NormalExit;
        if (!ok) reportError(QString::fromUtf8(log.right(4000)));
        if (QFileInfo::exists(pendingPath)) try { openTournament(pendingPath); } catch (const std::exception &e) { ok = false; reportError(e.what()); }
        if (finished) finished(ok);
    });
    start->setEnabled(false); progress->setRange(0, rounds->value() * 14); progress->setValue(0);
    summary->setText("Preparing selected AIs and running Classic matches…"); breakdown->clear();
    process->start(python, {root + "/tools/tournament.py", "run", first->currentData().toString(), second->currentData().toString(),
        "--out", QFileInfo(path).absoluteFilePath(), "--rounds", QString::number(rounds->value()), "--seed", QString::number(seed->value()),
        "--jobs", QString::number(threads->value()), "--max-plies", QString::number(maxPlies), "--backend", "openmp", "--worker", worker});
}
void Desk::processOutput() {
    auto data = process->readAllStandardOutput(); pendingOutput += data; log += data;
    if (log.size() > 16000) log = log.right(16000);
    while (true) {
        auto end = pendingOutput.indexOf('\n'); if (end < 0) break;
        auto line = pendingOutput.left(end); pendingOutput.remove(0, end + 1);
        auto event = QJsonDocument::fromJson(line).object();
        if (event["event"] == "progress") progress->setValue(event["completed"].toInt());
    }
}
void Desk::startSmoke(const QString &path) {
    smoke = true; rounds->setValue(1); threads->setValue(std::min(4, threads->maximum()));
    first->setCurrentIndex(first->findData("original-v1")); second->setCurrentIndex(second->findData("missions-v1-normal"));
    startRun(path, 160);
}
bool Desk::verifySmoke() {
    if (!tournament || tournament->games.size() != 14 || table->rowCount() != 14 || current.frames.empty()) return false;
    for (const auto &g : tournament->games) tournament->replay(g.id);
    slider->setValue(1); if (board->lastMove.first < 0 || slider->value() != 1) return false;
    perspective->setCurrentIndex(1); if (board->perspective != 0) return false;
    perspective->setCurrentIndex(2); if (board->perspective != 1) return false;
    filter->setCurrentIndex(2);
    auto draws = std::count_if(tournament->games.begin(), tournament->games.end(), [](const Match &g) { return g.result == "draw"; });
    if (table->rowCount() != draws) return false;
    filter->setCurrentIndex(0); table->selectRow(1);
    if (!matchTitle->text().startsWith("Match 2 ")) return false;
    perspective->setCurrentIndex(0); slider->setValue(std::min(60, slider->maximum()));
    return true;
}
void Desk::captureReview(int match, int ply, int view) {
    for (int row = 0; row < table->rowCount(); ++row) {
        if (table->item(row, 0)->data(Qt::UserRole).toInt() != match) continue;
        table->selectRow(row);
        perspective->setCurrentIndex(view);
        slider->setValue(std::max(0, std::min(ply, slider->maximum())));
        return;
    }
    throw std::runtime_error("Requested review match is missing");
}
void Desk::closeEvent(QCloseEvent *event) {
    if (process && process->state() != QProcess::NotRunning) { reportError("Let the current tournament finish before closing the desk."); event->ignore(); return; }
    timer->stop(); event->accept();
}
