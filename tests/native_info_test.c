/* Exercise the native protocol's information bookkeeping directly. */
#define main engine_program_main
#include "../src/native/engine.c"
#undef main

static int failures;
#define CHECK(c, message) do { if(!(c)) { fprintf(stderr, "FAIL: %s\n", message); failures++; } } while(0)

static void position(uint8_t attacker) {
    new_game(1);
    board_clear();
    board[50] = attacker | CELL_BLUE;
    board[60] = PIECE_UNKNOWN;
}

int main(void) {
    game_rules = RULE_SILENT;
    position(PIECE_MARSHAL);
    battle(50, 60, PIECE_MARSHAL, PIECE_MINER);
    CHECK(enemy_lost[PIECE_MINER] == 0, "undisclosed defeated defenders do not enter the known casualty ledger");
    CHECK(board[60] == (PIECE_MARSHAL | CELL_BLUE | CELL_REVEALED | CELL_MOVED), "attacking marshal becomes publicly known");

    position(PIECE_MINER);
    battle(50, 60, PIECE_MINER, PIECE_GENERAL);
    CHECK(board[60] == PIECE_UNKNOWN, "unrevealed winning defender stays unknown");

    position(PIECE_SCOUT);
    battle(50, 60, PIECE_SCOUT, PIECE_MINER);
    CHECK(board[60] == (PIECE_MINER | CELL_REVEALED), "scout discloses a defender even under Silent Defense");
    board[50] = PIECE_MARSHAL | CELL_BLUE;
    battle(50, 60, PIECE_MARSHAL, PIECE_MINER);
    CHECK(enemy_lost[PIECE_MINER] == 1, "previously revealed defenders remain known casualties");

    position(PIECE_GENERAL);
    battle(60, 50, PIECE_MARSHAL, PIECE_GENERAL);
    CHECK(board[50] == (PIECE_MARSHAL | CELL_REVEALED | CELL_MOVED), "enemy attacker discloses its rank");

    new_game(1);
    moved(60, 50);
    CHECK(PIECE_TYPE(board[50]) == PIECE_UNKNOWN && !(board[50] & CELL_REVEALED), "one step does not reveal a rank");
    moved(50, 20);
    CHECK(PIECE_TYPE(board[20]) == PIECE_SCOUT && (board[20] & CELL_REVEALED), "long move publicly identifies a scout");

    game_rules = 0;
    position(PIECE_MARSHAL);
    battle(50, 60, PIECE_MARSHAL, PIECE_MINER);
    CHECK(enemy_lost[PIECE_MINER] == 1, "classic revealed casualties still count normally");
    printf("native information: %s\n", failures ? "FAILED" : "all disclosure/casualty checks passed");
    return failures != 0;
}
