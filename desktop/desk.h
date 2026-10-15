#pragma once
#include "classic.h"
#include <QMainWindow>
#include <QJsonObject>
#include <QPixmap>
#include <QProcess>
#include <QSqlDatabase>
#include <functional>
#include <memory>

class QComboBox;
class QLabel;
class QListWidget;
class QProgressBar;
class QPushButton;
class QSlider;
class QSpinBox;
class QTableWidget;
class QTimer;
class QCloseEvent;

struct Match {
    int id = 0, pair = 0, plies = 0;
    QString family, red, blue, result, reason;
};
struct Replay {
    std::vector<Classic::Position> frames;
    std::vector<Classic::Move> moves;
    QStringList events;
};
class TournamentFile {
    QString connection;
    QSqlDatabase db;
public:
    QJsonObject metadata;
    std::vector<Match> games;
    explicit TournamentFile(const QString &path);
    ~TournamentFile();
    Replay replay(int id) const;
};
class Board : public QWidget {
    QPixmap terrain;
    std::array<std::array<QPixmap, 13>, 2> tokens;
protected:
    void paintEvent(QPaintEvent *) override;
public:
    Classic::Position position;
    Classic::Move lastMove{-1,-1};
    int perspective = -1;
    explicit Board(QWidget *parent = nullptr);
    QSize sizeHint() const override { return {520, 520}; }
};
class Desk : public QMainWindow {
    QString root, python, worker;
    std::unique_ptr<TournamentFile> tournament;
    Replay current;
    QComboBox *first, *second, *filter, *perspective;
    QSpinBox *rounds, *seed, *threads;
    QPushButton *start;
    QLabel *summary, *breakdown, *matchTitle, *plyLabel;
    QProgressBar *progress;
    QTableWidget *table;
    QListWidget *events;
    QSlider *slider;
    QTimer *timer;
    Board *board;
    QProcess *process = nullptr;
    QByteArray pendingOutput, log;
    QString pendingPath;
    bool smoke = false;
    void populate();
    void selectMatch();
    void displayPly(int ply);
    void processOutput();
    void reportError(const QString &message);
protected:
    void closeEvent(QCloseEvent *) override;
public:
    std::function<void(bool)> finished;
    Desk(QString project, QString pythonProgram, QString workerProgram);
    void openTournament(const QString &path);
    void startRun(const QString &path, int maxPlies = 1000);
    void startSmoke(const QString &path);
    bool verifySmoke();
};
