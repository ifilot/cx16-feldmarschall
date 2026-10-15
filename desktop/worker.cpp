// Each OpenMP iteration owns its board, RNG-seeded engine processes and trace.
// No mutable game state is shared between matches or inside a legacy evaluator.
#include "classic.h"
#include <QCoreApplication>
#include <QElapsedTimer>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <atomic>
#include <algorithm>
#include <csignal>
#include <iostream>
#include <memory>
#include <omp.h>
#include <stdexcept>

static_assert(std::atomic<bool>::is_always_lock_free, "Signal cancellation requires lock-free atomic flags");
static std::atomic<bool> interrupted{false};
static void stopWorker(int) { interrupted.store(true, std::memory_order_relaxed); }

static void emitJson(const QJsonObject &value) {
    auto line = QJsonDocument(value).toJson(QJsonDocument::Compact);
    std::cout << line.constData() << std::endl;
}
static QJsonObject readObject(const QString &path) {
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) throw std::runtime_error(file.errorString().toStdString());
    QJsonParseError error;
    auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) throw std::runtime_error("Invalid JSON plan");
    return document.object();
}
class Engine {
    QProcess process;
    int timeout;
public:
    Engine(const QJsonArray &command, int deadline) : timeout(deadline) {
        if (command.isEmpty()) throw std::runtime_error("Empty engine command");
        QStringList arguments;
        for (int i = 1; i < command.size(); ++i) arguments.append(command[i].toString());
        process.setProcessChannelMode(QProcess::SeparateChannels);
        process.start(command[0].toString(), arguments);
        if (!process.waitForStarted(timeout)) throw std::runtime_error(process.errorString().toStdString());
        ask("feldmarschall", "ok");
    }
    ~Engine() {
        if (process.state() != QProcess::NotRunning) {
            process.write("quit\n");
            if (!process.waitForFinished(1000)) {
                process.kill(); process.waitForFinished(1000);
            }
        }
    }
    void send(const QString &line) {
        auto data = (line + '\n').toUtf8();
        if (process.write(data) != data.size()) throw std::runtime_error("Cannot write engine command");
    }
    QString ask(const QString &line, const QString &prefix) {
        send(line);
        QElapsedTimer clock; clock.start();
        while (true) {
            if (interrupted) throw std::runtime_error("Tournament interrupted");
            while (process.canReadLine()) {
                auto answer = QString::fromUtf8(process.readLine()).trimmed();
                if (answer == prefix || answer.startsWith(prefix + ' ')) return answer.mid(prefix.size()).trimmed();
                if (answer.startsWith("error")) throw std::runtime_error(answer.toStdString());
            }
            int remaining = timeout - int(clock.elapsed());
            if (remaining <= 0) throw std::runtime_error("Engine response timed out");
            if (!process.waitForReadyRead(std::min(remaining, 250))) {
                if (process.canReadLine()) continue;
                if (process.state() != QProcess::NotRunning) continue;
                auto detail = QString::fromUtf8(process.readAllStandardError()).right(800);
                throw std::runtime_error(("Engine stopped or response timed out: " + detail).toStdString());
            }
        }
    }
};

static QJsonObject play(const QJsonObject &job, int timeout) {
    auto names = job["names"].toArray(), commands = job["commands"].toArray(), setups = job["setups"].toArray();
    if (names.size() != 2 || commands.size() != 2 || setups.size() != 2 ||
            job["max_plies"].toInt() < 1 || job["seed"].toInt() < 1)
        throw std::runtime_error("Invalid match plan");
    Classic::Position truth;
    std::array<std::unique_ptr<Engine>, 2> engines;
    for (int army = 0; army < 2; ++army) {
        truth.place(army, setups[army].toString());
        engines[army] = std::make_unique<Engine>(commands[army].toArray(), timeout);
        engines[army]->send("seed " + QString::number(job["seed"].toInt() * 2 + army + 1));
        engines[army]->send(army == 0 ? "new red" : "new blue");
        engines[army]->send("setup " + setups[army].toString());
    }
    int side = 0, winner = -1;
    QString reason;
    QJsonArray trace;
    while (true) {
        auto legal = truth.moves(side);
        if (legal.empty()) {
            if (!truth.moves(1 - side).empty()) { winner = 1 - side; reason = "no moves"; }
            else reason = "neither can move";
            break;
        }
        if (trace.size() >= job["max_plies"].toInt()) { reason = "ply limit"; break; }
        auto answer = engines[side]->ask("go", "move").simplified().split(' ');
        Classic::Move move{-1, -1};
        if (answer.size() == 2) move = {Classic::parseSquare(answer[0]), Classic::parseSquare(answer[1])};
        if (std::find(legal.begin(), legal.end(), move) == legal.end()) throw std::runtime_error("AI produced an illegal move");
        bool capturedFlag = truth.cells[move.second].rank == Classic::Flag;
        auto notification = truth.apply(move);
        trace.append(QJsonArray{move.first, move.second});
        for (auto &engine : engines) engine->send(notification);
        if (capturedFlag) { winner = side; reason = "flag"; break; }
        side = 1 - side;
    }
    return {{"red", names[0]}, {"blue", names[1]}, {"seed", job["seed"]},
            {"winner", winner < 0 ? QJsonValue() : names[winner]},
            {"result", winner < 0 ? "draw" : winner == 0 ? "red" : "blue"},
            {"reason", reason}, {"plies", trace.size()}, {"moves", trace}};
}

static QJsonObject replay(const QJsonObject &game) {
    Classic::Position board;
    board.place(0, game["red_setup"].toString()); board.place(1, game["blue_setup"].toString());
    QJsonArray states{board.json()}, legal;
    int side = 0;
    bool terminal = false;
    for (auto entry : game["moves"].toArray()) {
        auto pair = entry.toArray();
        if (pair.size() != 2) throw std::runtime_error("Invalid recorded move");
        Classic::Move move{pair[0].toInt(-1), pair[1].toInt(-1)};
        if (terminal || !board.legal(move, side)) throw std::runtime_error("Illegal recorded move");
        terminal = board.cells[move.second].rank == Classic::Flag;
        board.apply(move); states.append(board.json()); side = 1 - side;
    }
    for (auto [from, to] : board.moves(side)) legal.append(QJsonArray{from, to});
    return {{"states", states}, {"legal", legal}};
}

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    std::signal(SIGINT, stopWorker); std::signal(SIGTERM, stopWorker);
    try {
        auto args = app.arguments();
        if (args.size() == 2 && args[1] == "--info") {
            emitJson({{"backend", "openmp"}, {"referee", "classic-openmp-v1"}, {"qt", qVersion()},
                      {"openmp", _OPENMP}, {"max_threads", omp_get_max_threads()}});
            return 0;
        }
        if (args.size() == 3 && args[1] == "--replay") { emitJson(replay(readObject(args[2]))); return 0; }
        if (args.size() == 3 && args[1] == "--probe") {
            auto request = readObject(args[2]); Classic::Position board; board.load(request["cells"].toArray());
            auto histories = request["shuttle"].toArray();
            for (int side = 0; side < histories.size() && side < 2; ++side) {
                auto h = histories[side].toArray();
                if (h.size() == 3) board.shuttle[side] = {h[0].toInt(-1), h[1].toInt(-1), h[2].toInt()};
            }
            QJsonArray moves;
            for (auto [from, to] : board.moves(request["side"].toInt())) moves.append(QJsonArray{from, to});
            emitJson({{"moves", moves}}); return 0;
        }
        if (args.size() != 2) throw std::runtime_error("Usage: feldmarschall-tournament-worker PLAN.json | --info | --replay GAME.json");
        auto plan = readObject(args[1]);
        const auto jobs = plan["jobs"].toArray();
        int threads = plan["threads"].toInt(omp_get_max_threads());
        int timeout = plan["timeout_ms"].toInt(60000);
        if (threads < 1 || timeout < 1 || jobs.isEmpty()) throw std::runtime_error("Invalid worker settings");
        omp_set_dynamic(0);
        std::atomic<bool> failed{false};
        int completed = 0;
        int actualThreads = 0;
        #pragma omp parallel num_threads(threads)
        {
            #pragma omp single
            { actualThreads = omp_get_num_threads();
              emitJson({{"event", "backend"}, {"backend", "openmp"}, {"threads", actualThreads}, {"openmp", _OPENMP}}); }
            #pragma omp for schedule(dynamic, 1)
            for (int index = 0; index < jobs.size(); ++index) {
                if (failed.load() || interrupted) continue;
                try {
                    const auto job = jobs[index].toObject();
                    auto game = play(job, timeout);
                    #pragma omp critical(output)
                    { emitJson({{"event", "game"}, {"index", index}, {"completed", ++completed},
                                {"total", jobs.size()}, {"game", game}}); }
                } catch (const std::exception &error) {
                    failed.store(true);
                    #pragma omp critical(output)
                    { emitJson({{"event", "error"}, {"index", index}, {"message", QString::fromUtf8(error.what())}}); }
                }
            }
        }
        return failed || interrupted ? 1 : 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << std::endl; return 1;
    }
}
