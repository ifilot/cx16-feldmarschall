/* Tactical regressions and legal, non-mutating decisions across rule variants. */
#include <stdio.h>
#include <string.h>
#include "ai.h"
#include "board.h"
#include "rules.h"
#include "setup.h"
#include "random.h"
#ifdef AI_MISSIONS
#include "ai_mission.h"
#endif

static int failures;
#define CHECK(c, message) do { if(!(c)) { printf("FAIL level %u move %u->%u: %s\n", ai_difficulty, from, to, message); failures++; } } while(0)
static uint8_t lost[PIECE_TYPES], from, to;

static void fresh(void) {
    board_clear(); rules_reset(); ai_reset(); game_rules = 0;
    memcpy(lost, piece_counts, sizeof(lost));
}

static void decide(uint16_t seed) {
    random_seed(seed);
    ai_move(0, lost, &from, &to);
}

static void scout_long_range(void) {
    static const uint8_t sources[] = {80, 10, 81, 88};
    static const uint8_t destinations[] = {10, 80, 88, 81};
    uint8_t side, direction, i, n, targets[MAX_TARGETS], reachable;
    uint16_t seed;
    for(side=0; side<2; side++) for(direction=0; direction<4; direction++) {
        fresh();
        board[sources[direction]] = PIECE_SCOUT | (side ? CELL_BLUE : 0);
        board[99] = PIECE_FLAG | (side ? CELL_BLUE : 0);
        board[destinations[direction]] = PIECE_FLAG | CELL_REVEALED | (side ? 0 : CELL_BLUE);
        board[9] = PIECE_SPY | CELL_REVEALED | (side ? 0 : CELL_BLUE);
        lost[PIECE_FLAG]--; lost[PIECE_SPY]--;
        n = rules_targets(sources[direction], targets);
        reachable = 0;
        for(i=0; i<n; i++) if(targets[i] == destinations[direction]) reachable = 1;
        CHECK(reachable, "scout can attack a distant enemy along a clear row or column");
        for(seed=1; seed<=32; seed++) {
            ai_reset(); random_seed(seed);
            ai_move(side ? CELL_BLUE : 0, lost, &from, &to);
            CHECK(from == sources[direction] && to == destinations[direction],
                  "scout chooses a long-range flag capture on either army and every difficulty");
        }
    }
}

static void tactical(void) {
    uint16_t seed;
    for(seed=1; seed<=32; seed++) {
        fresh();
        board[60] = PIECE_SCOUT; board[50] = PIECE_FLAG | CELL_BLUE | CELL_REVEALED;
        board[70] = PIECE_MARSHAL; board[71] = PIECE_GENERAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_FLAG]--; lost[PIECE_GENERAL]--;
        decide(seed);
        CHECK(from == 60 && to == 50, "capture flag before material or positional improvements");

        fresh();
        board[60] = PIECE_SPY; board[50] = PIECE_MARSHAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_MARSHAL]--;
        decide(seed);
        CHECK(from == 60 && to == 50, "spy takes revealed marshal");

        fresh();
        board[60] = PIECE_MINER; board[50] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_BOMB]--;
        decide(seed);
        CHECK(ai_difficulty == AI_EASY || (from == 60 && to == 50), "miner clears known bomb");

        fresh();
        board[65] = PIECE_SPY; board[5] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--;
        decide(seed);
        CHECK(ai_difficulty == AI_EASY || (from == 65 && (to == 64 || to == 66)), "spy leaves an unobstructed scout ray");

        fresh();
        /* Going sideways is the shortest usable path around the west lake. */
        board[62] = PIECE_MARSHAL; board[32] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--;
        decide(seed);
        CHECK(ai_difficulty == AI_EASY || (from == 62 && to == 61), "route follows the passage around a lake");

        fresh();
        /* Taking the general would vacate the only blocker on the flag ray. */
        board[65] = PIECE_MARSHAL; board[95] = PIECE_FLAG;
        board[5] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        board[64] = PIECE_GENERAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--; lost[PIECE_GENERAL]--;
        decide(seed);
        CHECK(from == 65 && (to == 55 || (ai_difficulty == AI_EASY && to == 75)), "keep a scout ray to our flag blocked instead of taking material");

        fresh();
        board[80] = PIECE_MARSHAL; board[91] = PIECE_FLAG;
        board[90] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        board[70] = PIECE_GENERAL | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT]--; lost[PIECE_GENERAL]--;
        decide(seed);
        CHECK(from == 80 && to == 90, "respond to an immediate threat beside our flag");
    }
}

static unsigned private_inventory_checks;
#ifdef AI_LINKED_SCOUTING
static void linked_scouting(void) {
    uint8_t side, target, scout, ally;
    for(side=0; side<2; side++) {
        fresh(); ai_difficulty = AI_NORMAL;
        target = side ? 49 : 50; scout = side ? 39 : 60; ally = side ? 48 : 51;
        board[scout] = PIECE_SCOUT | (side ? CELL_BLUE : 0);
        board[ally] = PIECE_GENERAL | (side ? CELL_BLUE : 0);
        board[target] = PIECE_UNKNOWN | (side ? 0 : CELL_BLUE);
        board[side ? 99 : 0] = board[side ? 98 : 1] = PIECE_UNKNOWN | (side ? 0 : CELL_BLUE);
        lost[PIECE_MARSHAL]--; lost[PIECE_COLONEL] -= 2;
        random_seed(1); ai_move(side ? CELL_BLUE : 0, lost, &from, &to);
        CHECK(ai_test_linked_information(target) == 66, "cost information by a legal ally's attack-or-abstain decision on both armies");
        board[ally] = CELL_EMPTY; board[side ? 38 : 61] = PIECE_GENERAL | (side ? CELL_BLUE : 0);
        random_seed(1); ai_move(side ? CELL_BLUE : 0, lost, &from, &to);
        CHECK(ai_test_linked_information(target) == 0, "nearby pieces without a legal follow-up attack buy no information");
        board[side ? 38 : 61] = CELL_EMPTY; board[ally] = PIECE_GENERAL | (side ? CELL_BLUE : 0);
        board[target] = PIECE_COLONEL | CELL_REVEALED | (side ? 0 : CELL_BLUE);
        random_seed(1); ai_move(side ? CELL_BLUE : 0, lost, &from, &to);
        CHECK(ai_test_linked_information(target) == 0, "a disclosed rank needs no information credit");
    }
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT; board[51] = PIECE_GENERAL;
    board[50] = PIECE_UNKNOWN | CELL_BLUE;
    lost[PIECE_MARSHAL]--;
    decide(1);
    CHECK(ai_test_linked_information(50) == 0, "certain losing follow-up buys no information");
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT; board[51] = PIECE_MARSHAL;
    board[50] = PIECE_UNKNOWN | CELL_BLUE;
    lost[PIECE_SERGEANT]--; lost[PIECE_BOMB] -= 6;
    decide(1);
    CHECK(ai_test_linked_information(50) == 0, "information worth less than the Scout does not justify a probe");
    board[50] |= CELL_MOVED;
    decide(1);
    CHECK(ai_test_linked_information(50) == 0, "movement excludes bombs so a certain winning follow-up needs no probe");
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT; board[51] = PIECE_GENERAL;
    board[50] = PIECE_COLONEL | CELL_BLUE | CELL_REVEALED;
    lost[PIECE_COLONEL]--;
    decide(1);
    CHECK(from == 51 && to == 50, "a favourable disclosure is exploited by the intended beneficiary");
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT; board[51] = PIECE_GENERAL;
    board[50] = PIECE_MARSHAL | CELL_BLUE | CELL_REVEALED;
    lost[PIECE_MARSHAL]--;
    decide(1);
    CHECK(!(from == 51 && to == 50), "an unfavourable disclosure prevents the beneficiary's losing attack");
}
#endif
#ifdef AI_OCCUPANCY_BELIEFS
static void occupancy_beliefs(void) {
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT; board[61] = PIECE_MINER;
    board[50] = PIECE_UNKNOWN | CELL_BLUE;
    board[0] = PIECE_UNKNOWN | CELL_BLUE | CELL_MOVED;
    lost[PIECE_SCOUT]--; lost[PIECE_BOMB]--;
    decide(1);
    CHECK(ai_test_expected(PIECE_SCOUT, 0) == -10, "the only moved unknown consumes the remaining mobile rank");
    CHECK(ai_test_expected(PIECE_MINER, 0) == 20, "the unmoved unknown must be the remaining bomb");
    CHECK(ai_test_expected(PIECE_SCOUT, 1) == 0, "moved unknown remains a scout in this inventory");
    board[0] &= ~CELL_MOVED; decide(1);
    CHECK(ai_test_expected(PIECE_SCOUT, 0) == -5, "without movement evidence both assignments are possible");
    board[0] |= CELL_MOVED; game_rules = RULE_MOVING_BOMBS; decide(1);
    CHECK(ai_test_expected(PIECE_SCOUT, 0) == 5 && ai_test_expected(PIECE_SCOUT, 1) == 5,
          "moving bombs remain possible, with the variant's mutual destruction payoff");
}
#endif
#ifdef AI_PURPOSEFUL_PROBES
static void probes(void) {
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT; board[61] = PIECE_GENERAL; board[99] = PIECE_FLAG;
    board[50] = board[0] = PIECE_UNKNOWN | CELL_BLUE;
    lost[PIECE_MARSHAL]--; lost[PIECE_SCOUT]--;
    decide(1);
    CHECK(ai_test_discovery(50) > 0, "value information that changes a nearby general's attack decision");
    CHECK(ai_test_discovery(0) == 0, "avoid rewarding information with no nearby beneficiary");
    board[50] = PIECE_MARSHAL | CELL_BLUE | CELL_REVEALED;
    decide(1);
    CHECK(ai_test_discovery(50) == 0, "a disclosed rank needs no reconnaissance");
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT; board[61] = PIECE_GENERAL;
    board[50] = PIECE_UNKNOWN | CELL_BLUE;
    lost[PIECE_SCOUT]--;
    decide(1);
    CHECK(ai_test_discovery(50) == 0, "certain winning matchup needs no information bonus");
}
#endif
#ifdef AI_LOCAL_EXCHANGES
static void exchanges(void) {
    uint8_t before[SQUARES];
    fresh(); ai_difficulty = AI_HARD;
    board[60] = PIECE_GENERAL; board[51] = PIECE_SPY; board[99] = PIECE_FLAG;
    board[50] = PIECE_CAPTAIN | CELL_BLUE | CELL_REVEALED;
    board[40] = PIECE_MARSHAL | CELL_BLUE | CELL_REVEALED;
    lost[PIECE_CAPTAIN]--; lost[PIECE_MARSHAL]--;
    decide(1); memcpy(before, board, sizeof(before));
    CHECK(ai_test_reply(60, 50) == 0, "recognize the spy recapture after a marshal takes our general");
    CHECK(!memcmp(before, board, sizeof(before)), "exchange search restores every hypothetical square");
    board[51] = CELL_EMPTY; decide(1);
    CHECK(ai_test_reply(60, 50) > 0, "charge for the general when no recapture exists");
}
#endif
#ifdef AI_SECTOR_MEMORY
static void sector_memory(void) {
    uint8_t state[AI_TEST_STATE_SIZE];
    fresh(); ai_difficulty = AI_NORMAL;
    board[20] = PIECE_MINER; board[99] = PIECE_FLAG;
    board[0] = PIECE_UNKNOWN | CELL_BLUE;
    board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
    lost[PIECE_FLAG]--; lost[PIECE_BOMB]--;
    decide(1);
    CHECK(ai_mission_test_target(0) == 10, "start by clearing a disclosed guard");
    ai_test_save(state);
    board[10] = PIECE_MINER | CELL_MOVED; board[20] = CELL_EMPTY;
    lost[PIECE_BOMB]++;
    decide(1);
    CHECK(ai_mission_test_target(0) == 0, "remember flag-sector evidence after its guard is removed");
    ai_reset(); ai_test_load(state);
    decide(1);
    CHECK(ai_mission_test_target(0) == 0, "restore sector hypotheses in an AI snapshot");
    board[0] = CELL_EMPTY;
    decide(1);
    CHECK(ai_mission_test_target(0) == NOWHERE, "discard a contradicted sector hypothesis");
}
#endif
#ifdef AI_MISSIONS
static void missions(void) {
    uint16_t seed;
    uint8_t level;
    for(level=AI_NORMAL; level<=AI_HARD; level++) for(seed=1; seed<=32; seed++) {
        ai_difficulty = level; fresh();
        board[60] = PIECE_MINER; board[50] = PIECE_MAJOR; board[99] = PIECE_FLAG;
        board[0] = PIECE_FLAG | CELL_BLUE | CELL_REVEALED;
        board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_FLAG]--; lost[PIECE_BOMB]--;
        decide(seed);
        CHECK(from == 50 && to == 51, "move a blocker off the miner corridor");

        fresh();
        board[60] = PIECE_MINER; board[61] = PIECE_SCOUT; board[99] = PIECE_FLAG;
        board[0] = PIECE_FLAG | CELL_BLUE | CELL_REVEALED;
        board[1] = board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
        board[40] = board[39] = PIECE_UNKNOWN | CELL_BLUE;
        lost[PIECE_FLAG]--; lost[PIECE_BOMB] -= 3; lost[PIECE_SCOUT]--;
        decide(seed);
        CHECK(from == 61 && to == 41, "scout investigates a blocker before sending the miner");
    }
}
#endif
#ifdef AI_PLAN_CYCLE
static void plan_cycle(void) {
    uint8_t turn, initial;
    uint8_t snapshot[AI_TEST_STATE_SIZE];
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_MINER; board[61] = PIECE_SCOUT; board[99] = PIECE_FLAG;
    board[0] = board[19] = PIECE_UNKNOWN | CELL_BLUE;
    board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
    ai_mission_begin(0); initial = ai_mission_test_target(0);
    CHECK(initial == 10, "plan starts with observable fortification evidence");
    ai_test_save(snapshot);
    for(turn=0; turn<8; turn++) ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == 19, "stalled work opens an investigation in another area");
    ai_test_load(snapshot);
    for(turn=0; turn<8; turn++) ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == 19, "reconsideration history survives a public AI snapshot");
    board[0] = PIECE_FLAG | CELL_BLUE | CELL_REVEALED;
    ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == 0, "a disclosed flag overrides speculative-sector cooldown");
    ai_reset(); board[10] = CELL_EMPTY; board[0] = PIECE_UNKNOWN | CELL_BLUE;
    ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == NOWHERE, "new unsupported guesses do not start a mission");
}
#endif
static void progress_state(void) {
    uint8_t state[AI_TEST_STATE_SIZE];
    unsigned turn;
    fresh(); ai_difficulty = AI_NORMAL;
    board[60] = PIECE_SCOUT | CELL_REVEALED;
    board[99] = PIECE_FLAG | CELL_REVEALED;
    board[30] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
    board[0] = PIECE_FLAG | CELL_BLUE | CELL_REVEALED;
    lost[PIECE_SCOUT]--; lost[PIECE_FLAG]--;
    for(turn=0; turn<140; turn++) decide(1);
    CHECK(ai_test_quiet(0) == 128, "quiet-turn pressure saturates without wrapping");
    ai_move(CELL_BLUE, lost, &from, &to);
    ai_move(CELL_BLUE, lost, &from, &to);
    CHECK(ai_test_quiet(CELL_BLUE) == 1 && ai_test_quiet(0) == 128,
          "armies keep independent progress counters");
    ai_test_save(state); ai_reset();
    CHECK(ai_test_quiet(0) == 0, "new game clears progress pressure");
    ai_test_load(state);
    CHECK(ai_test_quiet(0) == 128 && ai_test_quiet(CELL_BLUE) == 1,
          "fairness snapshots restore progress pressure");
    board[30] = CELL_EMPTY; lost[PIECE_SCOUT]++;
    decide(1);
    CHECK(ai_test_quiet(0) == 0, "capture resets progress pressure");
}
static uint16_t secret_ranks_checked;

static void reply_tactic(void) {
    uint16_t seed;
    uint8_t level, normal_captures = 0;
    for(seed=1; seed<=32; seed++) for(level=AI_NORMAL; level<=AI_HARD; level++) {
        ai_difficulty = level; fresh();
        board[60] = PIECE_MARSHAL; board[80] = PIECE_SPY; board[99] = PIECE_FLAG;
        board[40] = board[61] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
        lost[PIECE_SCOUT] -= 2;
        decide(seed);
        if(level == AI_NORMAL && from == 60 && to == 61) normal_captures++;
        CHECK(level != AI_HARD || !(from == 60 && to == 61),
              "Hard checks the reply exposing its spy before taking a scout");
    }
    CHECK(normal_captures > 0, "reply fixture distinguishes Hard from Normal despite score jitter");
}

/* Shuffle identities separately among unmoved and moved concealed pieces,
 * keeping every public bit and the rank inventory unchanged. */
static void shuffle_hidden(uint8_t army, uint8_t moved) {
    uint8_t slots[SQUARES], count = 0, sq, cell, i, a, b, type;
    for(sq=0; sq<SQUARES; sq++) {
        cell = board[sq];
        if(IS_PIECE(cell) && (cell & CELL_BLUE) != army && !(cell & CELL_REVEALED) &&
           !!(cell & CELL_MOVED) == moved) slots[count++] = sq;
    }
    for(i=0; i<count/2; i++) {
        a = slots[i]; b = slots[count-1-i]; type = PIECE_TYPE(board[a]);
        if(type != PIECE_TYPE(board[b])) secret_ranks_checked |= (1 << type) | (1 << PIECE_TYPE(board[b]));
        board[a] = (board[a] & ~CELL_TYPE) | PIECE_TYPE(board[b]);
        board[b] = (board[b] & ~CELL_TYPE) | type;
    }
}

static unsigned fair_decisions;
static void fair_decide(uint8_t army, uint8_t* observed, uint16_t seed) {
    uint8_t truth[SQUARES], view[SQUARES], before[AI_TEST_STATE_SIZE], after[AI_TEST_STATE_SIZE], other[AI_TEST_STATE_SIZE];
    uint8_t first_from, first_to, enemy = army ? 0 : 1, sq, t, cell;
    uint8_t secret_lost[PIECE_TYPES];
    uint16_t next;
    memcpy(truth, board, SQUARES);
    ai_test_save(before);
    ai_mask(army);
    memcpy(view, board, SQUARES);
    random_seed(seed);
    ai_move(army, observed, &first_from, &first_to);
    next = random_next();
    ai_test_save(after);
    CHECK(!memcmp(view, board, SQUARES), "AI restores its view after hypothetical checks");
    memcpy(board, truth, SQUARES);
    shuffle_hidden(army, 0); shuffle_hidden(army, 1);
    memcpy(secret_lost, rules_lost[enemy], sizeof(secret_lost));
    if(game_rules & RULE_SILENT) {
        /* Exchange an undisclosed casualty with an unmoved hidden piece.
         * This changes the true remaining inventory, but not public knowledge. */
        for(t=0; t<PIECE_TYPES; t++) {
            if(t == PIECE_FLAG || rules_lost[enemy][t] <= rules_known_lost[enemy][t]) continue;
            for(sq=0; sq<SQUARES; sq++) {
                cell = board[sq];
                if(IS_PIECE(cell) && (cell & CELL_BLUE) != army &&
                   !(cell & (CELL_REVEALED | CELL_MOVED)) && PIECE_TYPE(cell) != PIECE_FLAG && PIECE_TYPE(cell) != t) {
                    rules_lost[enemy][t]--;
                    rules_lost[enemy][PIECE_TYPE(cell)]++;
                    board[sq] = (cell & ~CELL_TYPE) | t;
                    private_inventory_checks++;
                    break;
                }
            }
            break;
        }
    }
    ai_mask(army);
    CHECK(!memcmp(view, board, SQUARES), "all secret permutations produce the same public view");
    ai_test_load(before); random_seed(seed);
    ai_move(army, observed, &from, &to);
    ai_test_save(other);
    CHECK(from == first_from && to == first_to, "secret identities cannot change a decision at any difficulty");
    CHECK(next == random_next() && !memcmp(after, other, sizeof(after)),
          "secret identities cannot change random consumption, goals or histories");
    CHECK(!memcmp(view, board, SQUARES), "comparison restores its public board");
    memcpy(board, truth, SQUARES);
    memcpy(rules_lost[enemy], secret_lost, sizeof(secret_lost));
    ai_test_load(after);
    fair_decisions++;
}

static void variants(void) {
    uint8_t mask, turn, army, options[MAX_TARGETS], n, i;
    uint8_t observed[PIECE_TYPES];
    for(mask=0; mask<64; mask++) {
        fresh(); game_rules = mask; random_seed(1234 + mask);
        setup_random(0); setup_random(1);
        for(turn=0; turn<80; turn++) {
            army = turn & 1 ? CELL_BLUE : 0;
            memcpy(observed, rules_known_lost[army ? 0 : 1], sizeof(observed));
            fair_decide(army, observed, (uint16_t)mask*100 + turn + 1);
            if(from == NOWHERE) {
                CHECK(!rules_has_move(army != 0), "no move only when that side is stuck");
                break;
            }
            CHECK(from < SQUARES && to < SQUARES && (board[from] & CELL_BLUE) == army,
                  "AI selects its own piece");
            n = rules_targets(from, options);
            for(i=0; i<n && options[i] != to; i++) {}
            CHECK(i < n, "chosen move is legal under current combined variants and repetition state");
            if(i == n) break;
            if(PIECE_TYPE(board[to]) == PIECE_FLAG && IS_PIECE(board[to])) break;
            rules_apply(from, to);
            if(rules_flag_arrived(to)) break;
        }
    }
}

#ifdef AI_MISSION_PROGRESS
static void mission_progress_state(void) {
    uint8_t i, saved[AI_TEST_STATE_SIZE];
    fresh(); ai_difficulty = AI_NORMAL;
    board[30] = PIECE_MINER; board[20] = PIECE_CAPTAIN;
    board[99] = PIECE_FLAG;
    board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
    board[9] = PIECE_UNKNOWN | CELL_BLUE;
    ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) == 0, "a new mission starts with no stall debt");
    for(i=0; i<30; i++) ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) == 30, "unchanged route work accumulates stall debt");
    CHECK(ai_mission_score(20, 21) == 0, "an unproductive clearing job loses its mission bonus");
    ai_test_save(saved);
    ai_mission_begin(CELL_BLUE);
    CHECK(ai_mission_test_stalled(0) == 30 && ai_mission_test_stalled(CELL_BLUE) == 0,
          "armies keep independent mission progress");
    board[21] = board[20]; board[20] = CELL_EMPTY;
    ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) == 0, "clearing a corridor blocker is measurable progress");
    board[20] = board[21]; board[21] = CELL_EMPTY;
    ai_test_load(saved); ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) == 31, "snapshots restore unproductive mission history");
    board[20] = board[30]; board[30] = CELL_EMPTY;
    board[21] = PIECE_CAPTAIN;
    ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) == 0, "leader route progress resets stall debt");
    for(i=0; i<250; i++) ai_mission_begin(0);
    for(i=0; i<20; i++) ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) == 255, "mission progress counters saturate");
    board[9] = CELL_EMPTY;
    ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) == 0, "a public piece-count change restarts route assessment");
    board[10] = CELL_EMPTY;
    ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == NOWHERE && ai_mission_test_stalled(0) == 0,
          "contradicted or removed fortification evidence cancels the mission");
    fresh(); board[20] = PIECE_MINER; board[99] = PIECE_FLAG;
    board[0] = PIECE_UNKNOWN | CELL_BLUE;
    board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
    for(i=0; i<50; i++) ai_mission_begin(0);
    CHECK(ai_mission_test_stalled(0) >= 24 && ai_mission_score(20, 10) == 0,
          "alternating guard and flag hypotheses cannot reset an unchanged cooperation job");
}
#endif

#ifdef AI_MISSION_EVIDENCE
static void mission_evidence(void) {
    fresh(); ai_difficulty = AI_NORMAL;
    board[20] = PIECE_MINER; board[99] = PIECE_FLAG;
    board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
    board[0] = PIECE_UNKNOWN | CELL_BLUE;
    ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == 10, "an adjacent public flag candidate supports a guard mission");
    board[0] |= CELL_MOVED;
    ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == NOWHERE, "public movement contradicts a stationary guarded flag");
    board[0] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
    ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) == NOWHERE, "a disclosed mobile decoy cancels speculative guard mining");
    game_rules = RULE_MOVING_FLAG;
    board[0] = PIECE_UNKNOWN | CELL_BLUE | CELL_MOVED;
    ai_mission_begin(0);
    CHECK(ai_mission_test_target(0) != NOWHERE, "a moved concealed flag remains possible under moving flag rules");
}
#endif

#ifdef AI_MISSION_PRESERVE
static void mission_preserve(void) {
    fresh(); ai_difficulty = AI_NORMAL;
    board[30] = PIECE_MINER; board[21] = PIECE_SERGEANT;
    board[99] = PIECE_FLAG;
    board[0] = PIECE_UNKNOWN | CELL_BLUE;
    board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
    board[20] = PIECE_UNKNOWN | CELL_BLUE;
    ai_mission_begin(0);
    CHECK(ai_mission_score(21, 20) > 0 && ai_mission_score(30, 20) == 0,
          "probe a route blocker with another piece while retaining the last miner");
    board[20] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
    ai_mission_begin(0);
    CHECK(ai_mission_score(21, 20) > 0 && ai_mission_score(30, 20) == 0,
          "use a suitable support attacker instead of spending the last miner");
}
#endif

#ifdef AI_MISSION_ESCORT
static void mission_escort(void) {
    fresh(); ai_difficulty = AI_NORMAL;
    board[20] = PIECE_MINER; board[12] = PIECE_MAJOR;
    board[99] = PIECE_FLAG;
    board[0] = PIECE_UNKNOWN | CELL_BLUE;
    board[10] = PIECE_BOMB | CELL_BLUE | CELL_REVEALED;
    board[11] = PIECE_CAPTAIN | CELL_BLUE | CELL_REVEALED;
    ai_mission_begin(0);
    CHECK(ai_mission_score(12, 11) > 0 && ai_mission_score(20, 10) == 0,
          "assign support to remove a disclosed recapture threat beside a bomb");
    board[11] = CELL_EMPTY;
    ai_mission_begin(0);
    CHECK(ai_mission_score(20, 10) > 0,
          "resume the miner's guard capture after the threat is removed");
}
#endif

#ifdef AI_MISSION_SCOUT_VALUE
static void mission_scout_value(void) {
    fresh(); ai_difficulty = AI_NORMAL;
    board[20] = PIECE_SCOUT; board[99] = PIECE_FLAG;
    board[10] = PIECE_CAPTAIN | CELL_BLUE | CELL_REVEALED;
    board[0] = PIECE_UNKNOWN | CELL_BLUE;
    ai_mission_begin(0);
    CHECK(ai_mission_score(20, 10) == -24, "a scout should not buy already disclosed information by dying");
    board[0] = PIECE_FLAG | CELL_BLUE | CELL_REVEALED;
    ai_mission_begin(0);
    CHECK(ai_mission_score(20, 10) == 0, "no reconnaissance scarcity penalty when all enemies are disclosed");
    board[0] = PIECE_UNKNOWN | CELL_BLUE;
    board[21] = board[22] = PIECE_SCOUT;
    ai_mission_begin(0);
    CHECK(ai_mission_score(20, 10) == -24, "uninformative known losses remain costly with multiple scouts");
    board[10] = PIECE_SCOUT | CELL_BLUE | CELL_REVEALED;
    ai_mission_begin(0);
    CHECK(ai_mission_score(20, 10) == 0, "an equal trade removes an opposing piece and is not an uncompensated loss");
}
#endif

#ifdef AI_DIAGNOSTICS
static void diagnostic_history(void) {
    uint8_t side, a, b, actual, target, proposal_goal;
    uint8_t before[AI_TEST_STATE_SIZE], after[AI_TEST_STATE_SIZE];
    for(side=0; side<2; side++) {
        fresh(); ai_difficulty = AI_NORMAL;
        a = side ? 39 : 60; b = side ? 38 : 61;
        board[a] = PIECE_MARSHAL | (side ? CELL_BLUE : 0);
        board[b] = PIECE_SERGEANT | (side ? CELL_BLUE : 0);
        board[side ? 0 : 99] = PIECE_FLAG | (side ? CELL_BLUE : 0);
        board[side ? 49 : 50] = PIECE_SCOUT | CELL_REVEALED | (side ? 0 : CELL_BLUE);
        board[side ? 99 : 0] = PIECE_FLAG | CELL_REVEALED | (side ? 0 : CELL_BLUE);
        lost[PIECE_FLAG]--; lost[PIECE_SCOUT]--;
        random_seed(1); ai_move(side ? CELL_BLUE : 0, lost, &from, &to);
        CHECK(from == a || from == b, "diagnostic fixture selects a mobile actor");
        ai_test_save(before);
        ai_diagnostic_choice(side ? CELL_BLUE : 0, from, to);
        ai_test_save(after);
        CHECK(!memcmp(before, after, sizeof(before)), "acknowledging the proposed move preserves every cache");
        proposal_goal = before[side*SQUARES + to];
        actual = from == a ? b : a;
        target = side ? actual-10 : actual+10;
        ai_diagnostic_choice(side ? CELL_BLUE : 0, actual, target);
        ai_test_save(after);
        CHECK(after[side*SQUARES + from] == proposal_goal && after[side*SQUARES + to] == NOWHERE,
              "a forced history undoes the proposal's speculative goal transfer");
        CHECK(after[200 + side] == actual && after[202 + side] == target &&
              after[side*SQUARES + actual] == NOWHERE && after[side*SQUARES + target] == before[side*SQUARES + actual],
              "goal and backtrack caches follow the actually executed move on both armies");
    }
}
#endif

int main(void) {
#ifdef AI_LINKED_SCOUTING
    linked_scouting();
#endif
#ifdef AI_PLAN_CYCLE
    plan_cycle();
#endif
#ifdef AI_DIAGNOSTICS
    diagnostic_history();
#endif
#ifdef AI_MISSION_SCOUT_VALUE
    mission_scout_value();
#endif
#ifdef AI_MISSION_PRESERVE
    mission_preserve();
#endif
#ifdef AI_MISSION_ESCORT
    mission_escort();
#endif
#ifdef AI_MISSION_EVIDENCE
    mission_evidence();
#endif
#ifdef AI_MISSION_PROGRESS
    mission_progress_state();
#endif
#ifdef AI_OCCUPANCY_BELIEFS
    occupancy_beliefs();
#endif
#ifdef AI_PURPOSEFUL_PROBES
    probes();
#endif
#ifdef AI_LOCAL_EXCHANGES
    exchanges();
#endif
#ifdef AI_SECTOR_MEMORY
    sector_memory();
#endif
    uint8_t level;
    for(level=0; level<AI_LEVELS; level++) {
        ai_difficulty = level;
        scout_long_range();
        tactical();
        variants();
    }
    reply_tactic();
#ifdef AI_MISSIONS
    missions();
#endif
    progress_state();
    CHECK(private_inventory_checks > 0, "silent casualties were tested with different true rank inventories");
    CHECK((secret_ranks_checked & ((1 << PIECE_SPY) | (1 << PIECE_MARSHAL) | (1 << PIECE_FLAG))) ==
          ((1 << PIECE_SPY) | (1 << PIECE_MARSHAL) | (1 << PIECE_FLAG)), "Spy, Marshal and Flag identities were each permuted");
    printf("AI: %s; %u hidden-permutation decisions across all levels and 64 rule combinations\n", failures ? "FAILED" : "passed", fair_decisions);
    printf("%u Silent Defense private-inventory comparisons; Spy, Marshal and Flag included\n", private_inventory_checks);
    return failures != 0;
}
