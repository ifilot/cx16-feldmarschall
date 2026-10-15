#pragma once
#include <QJsonArray>
#include <QString>
#include <array>
#include <utility>
#include <vector>

namespace Classic {
constexpr int Scout = 8, Miner = 7, Spy = 9, Bomb = 10, Flag = 11;
inline const QString Glyphs = QStringLiteral("123456789SBF");
using Move = std::pair<int, int>;
struct Cell {
    int army = -1, rank = -1;
    bool moved = false, revealed = false;
    bool occupied() const { return army >= 0; }
};
struct Shuttle { int from = -1, to = -1, count = 0; };
struct Position {
    std::array<Cell, 100> cells{};
    std::array<Shuttle, 2> shuttle{};
    void place(int army, const QString &setup);
    std::vector<Move> moves(int army) const;
    bool legal(Move move, int army) const;
    QString apply(Move move);
    QJsonArray json() const;
    void load(const QJsonArray &board);
};
bool lake(int square);
QString squareName(int square);
int parseSquare(const QString &name);
int battle(int attacker, int defender); // 0 attacker, 1 defender, 2 both
}
