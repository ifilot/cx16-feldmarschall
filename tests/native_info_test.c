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
    uint8_t state[RULES_STATE_SIZE];
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

    game_rules=RULE_SILENT|RULE_RESCUE;
    position(PIECE_MINER);
    combat(50,60,PIECE_MINER,-1,BATTLE_DEFENDER);
    CHECK(board[60]==PIECE_UNKNOWN, "public outcome never imports an undisclosed defender rank");
    CHECK(rules_lost[1][PIECE_MINER]==1, "own casualties are available for rescue planning");
    CHECK(rules_known_lost[1][PIECE_MINER]==1, "an attacking casualty is public");
    board[99]=PIECE_CAPTAIN|CELL_BLUE;
    CHECK(reinforce(99,39,PIECE_MINER,1), "own public rescue is accepted");
    CHECK(rules_lost[1][PIECE_MINER]==0 && rules_rescues[1]==1, "rescue consumes own casualty and allowance");

    new_game(1);board_clear();board[60]=PIECE_UNKNOWN;board[50]=PIECE_MINER|CELL_BLUE;
    combat(60,50,PIECE_MARSHAL,-1,BATTLE_ATTACKER);
    CHECK(rules_lost[1][PIECE_MINER]==1 && !rules_known_lost[1][PIECE_MINER], "hidden own defender stays a private casualty");
    board[99]=PIECE_CAPTAIN|CELL_BLUE;
    CHECK(reinforce(99,39,PIECE_MINER,0), "private own rescue supplies legitimate own rank");
    CHECK(board[39]==(PIECE_MINER|CELL_BLUE), "private rescue is not marked revealed");
    rules_record(99,98);moved(99,98);rules_state_save(state);
    CHECK(state[51+98]==1 && !state[51+99], "quiet moves preserve a piece's used rescue identity");
    board[97]=PIECE_UNKNOWN;
    rules_record(98,97);combat(98,97,PIECE_CAPTAIN,-1,BATTLE_ATTACKER);rules_state_save(state);
    CHECK(state[51+97]==1 && !state[51+98], "attacks preserve a piece's used rescue identity");
    new_game(0);board_clear();board[99]=PIECE_UNKNOWN|CELL_BLUE;
    CHECK(reinforce(99,39,-1,0), "opposing private rescue remains unknown");
    CHECK(board[39]==(PIECE_UNKNOWN|CELL_BLUE), "opponent receives no private rescued rank");
    printf("native information: %s\n", failures ? "FAILED" : "all disclosure/casualty checks passed");
    return failures != 0;
}
