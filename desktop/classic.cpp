#include "classic.h"
#include <algorithm>
#include <stdexcept>

namespace Classic {
bool lake(int sq) { return sq == 42 || sq == 43 || sq == 52 || sq == 53 || sq == 46 || sq == 47 || sq == 56 || sq == 57; }
QString squareName(int sq) {
    return QString(QChar('a' + sq % 10)) + QString::number(10 - sq / 10);
}
int parseSquare(const QString &name) {
    if (name.size() < 2 || name.size() > 3) return -1;
    int col = name[0].unicode() - 'a';
    bool ok;
    int row = name.mid(1).toInt(&ok);
    if (!ok || col < 0 || col > 9 || row < 1 || row > 10) return -1;
    int sq = (10 - row) * 10 + col;
    return squareName(sq) == name ? sq : -1;
}
int battle(int a, int d) {
    if (d == Flag) return 0;
    if (d == Bomb) return a == Miner ? 0 : 1;
    if (a == Spy && d == 0) return 0;
    if (a == d) return 2;
    return a < d ? 0 : 1;
}
void Position::place(int army, const QString &setup) {
    constexpr std::array<int, 12> counts{1,1,2,3,4,4,4,5,8,1,6,1};
    if (army < 0 || army > 1 || setup.size() != 40) throw std::runtime_error("Invalid starting army");
    for (int rank = 0; rank < 12; ++rank)
        if (setup.count(Glyphs[rank]) != counts[rank]) throw std::runtime_error("Invalid piece inventory");
    for (int i = 0; i < 40; ++i) {
        int row = army == 1 ? 3 - i / 10 : 6 + i / 10;
        cells[row * 10 + i % 10] = {army, int(Glyphs.indexOf(setup[i])), false, false};
    }
}
std::vector<Move> Position::moves(int army) const {
    std::vector<Move> result;
    constexpr int dc[]{0,1,0,-1}, dr[]{-1,0,1,0};
    const auto &history = shuttle.at(army);
    for (int from = 0; from < 100; ++from) {
        const auto &piece = cells[from];
        if (piece.army != army || piece.rank == Bomb || piece.rank == Flag) continue;
        int banned = from == history.to && history.count >= 5 ? history.from : -1;
        for (int direction = 0; direction < 4; ++direction) {
            int col = from % 10, row = from / 10;
            while (true) {
                col += dc[direction]; row += dr[direction];
                if (col < 0 || col > 9 || row < 0 || row > 9) break;
                int to = row * 10 + col;
                if (lake(to)) break;
                const auto &other = cells[to];
                if (!other.occupied()) {
                    if (to != banned) result.emplace_back(from, to);
                    if (piece.rank == Scout) continue;
                } else if (other.army != army && to != banned) result.emplace_back(from, to);
                break;
            }
        }
    }
    return result;
}
bool Position::legal(Move move, int army) const {
    auto candidates = moves(army);
    return std::find(candidates.begin(), candidates.end(), move) != candidates.end();
}
QString Position::apply(Move move) {
    auto [from, to] = move;
    if (from < 0 || from >= 100 || to < 0 || to >= 100 || !cells[from].occupied())
        throw std::runtime_error("Invalid move coordinates");
    Cell a = cells[from], d = cells[to];
    auto &history = shuttle[a.army];
    history.count = history.count && from == history.to && to == history.from ? history.count + 1 : 1;
    history.from = from; history.to = to;
    a.moved = true;
    cells[from] = {};
    QString squares = squareName(from) + " " + squareName(to);
    if (!d.occupied()) {
        if (std::abs(from / 10 - to / 10) + std::abs(from % 10 - to % 10) > 1) a.revealed = true;
        cells[to] = a;
        return "moved " + squares;
    }
    a.revealed = d.revealed = true;
    int outcome = battle(a.rank, d.rank);
    cells[to] = outcome == 0 ? a : outcome == 1 ? d : Cell{};
    return "battle " + squares + " " + Glyphs[a.rank] + " " + Glyphs[d.rank];
}
QJsonArray Position::json() const {
    QJsonArray board;
    for (const auto &cell : cells) {
        if (cell.occupied()) board.append(QJsonArray{cell.army, cell.rank, cell.moved, cell.revealed});
        else board.append(QJsonValue());
    }
    return board;
}
void Position::load(const QJsonArray &board) {
    if (board.size() != 100) throw std::runtime_error("Board must have 100 squares");
    for (int sq = 0; sq < 100; ++sq) {
        auto a = board[sq].toArray();
        if (board[sq].isNull()) cells[sq] = {};
        else if (a.size() == 4 && a[0].toInt(-1) >= 0 && a[0].toInt() <= 1 && a[1].toInt(-1) >= 0 && a[1].toInt() <= 11)
            cells[sq] = {a[0].toInt(), a[1].toInt(), a[2].toBool(), a[3].toBool()};
        else throw std::runtime_error("Invalid piece record");
    }
}
}
