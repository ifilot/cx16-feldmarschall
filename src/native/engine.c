/**************************************************************************
 *                                                                        *
 *   Author: Ivo Filot <ivo@ivofilot.nl>                                  *
 *                                                                        *
 *   CX16-FELDMARSCHALL is free software:                                 *
 *   you can redistribute it and/or modify it under the terms of the      *
 *   GNU General Public License as published by the Free Software         *
 *   Foundation, either version 3 of the License, or (at your option)     *
 *   any later version.                                                   *
 *                                                                        *
 *   CX16-FELDMARSCHALL is distributed in the hope that it will be        *
 *   useful, but WITHOUT ANY WARRANTY; without even the implied           *
 *   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     *
 *   See the GNU General Public License for more details.                 *
 *                                                                        *
 *   You should have received a copy of the GNU General Public License    *
 *   along with this program.  If not, see http://www.gnu.org/licenses/.  *
 *                                                                        *
 **************************************************************************/

/*
 * The game's computer player as a native program, for testing and rating.
 *
 * It speaks a line-based protocol on stdin/stdout (see docs/protocol.md).
 * A referee (tools/arena.py) holds the true position; the engine keeps only
 * what its own army may know: its pieces, and the enemy's pieces as
 * PIECE_UNKNOWN until a battle or a long scout move reveals them.
 *
 * Built from the same src/core files as the X16 game; tools/parity.py
 * checks that both builds choose the same moves.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "board.h"
#include "rules.h"
#include "setup.h"
#include "random.h"
#include "ai.h"
#if defined(AI_TEST) && defined(AI_MISSIONS)
#include "ai_mission.h"
#endif
#if defined(AI_FEATURE_TRACE) || defined(AI_STUDENT)
#include "ai_student.h"
#endif

static uint8_t own;                         // CELL_BLUE or 0
static int tracing;                         // "think" prints every candidate
#ifdef AI_TRAINING
void ai_trace_training(uint8_t from, uint8_t to, int16_t capture_credit) {
    if(tracing == 1) printf("credit %u %u %d\n", from, to, capture_credit);
}
#endif

void ai_trace(uint8_t from, uint8_t to, int16_t score) {
    if(tracing == 1) printf("candidate %d %d %d\n", from, to, score);
    else if(tracing == 2) fprintf(stderr, "candidate %u %u %d rank=%u target=%u\n", from, to, score, PIECE_TYPE(board[from]), board[to]);
}
void ai_trace_plan(uint8_t from, uint8_t goal, uint8_t previous, uint8_t steps, int16_t utility) {
    if(tracing == 2) fprintf(stderr, "plan %u goal=%u previous=%u steps=%u utility=%d\n", from, goal, previous, steps, utility);
}
static uint8_t enemy_lost[PIECE_TYPES];

static void reply(const char* text) {
    puts(text);
    fflush(stdout);
}

/**
 * @brief Square from its name: a column a-j and a rank 1-10 (rank 1 is Red's back row)
 */
static uint8_t square(const char* name) {
    int col, rank;

    if(!name || name[0] < 'a' || name[0] > 'j') return NOWHERE;
    col = name[0] - 'a';
    rank = atoi(name + 1);
    if(rank < 1 || rank > BOARD_SIZE) return NOWHERE;
    return (BOARD_SIZE - rank) * BOARD_SIZE + col;
}

static void square_name(uint8_t sq, char* out) {
    sprintf(out, "%c%d", 'a' + SQUARE_COL(sq), BOARD_SIZE - SQUARE_ROW(sq));
}

static int type_of(char glyph) {
    const char* p = strchr(piece_glyphs, glyph);
    return glyph && p ? (int)(p - piece_glyphs) : -1;
}

/**
 * @brief The board square of the n-th piece of a deployment string
 *
 * Deployments list an army's front row first, columns a to j.
 */
static uint8_t setup_square(uint8_t blue, uint8_t n) {
    uint8_t row = n / BOARD_SIZE;
    return (blue ? SETUP_ROWS - 1 - row : BOARD_SIZE - SETUP_ROWS + row) * BOARD_SIZE + n % BOARD_SIZE;
}

static void new_game(uint8_t blue) {
    uint8_t n;

    own = blue ? CELL_BLUE : 0;
    board_clear();
    for(n=0; n<ARMY_SIZE; n++) {             // the enemy: 40 unknown pieces
        board[setup_square(!blue, n)] = PIECE_UNKNOWN | (blue ? 0 : CELL_BLUE);
    }
    memset(enemy_lost, 0, sizeof(enemy_lost));
    ai_reset();
    rules_reset();
}

static int place(const char* glyphs) {
    uint8_t n;
    int type;

    if(!glyphs || strlen(glyphs) != ARMY_SIZE) return 0;
    for(n=0; n<ARMY_SIZE; n++) {
        type = type_of(glyphs[n]);
        if(type < 0) return 0;
        board[setup_square(own, n)] = type | own;
    }
    return 1;
}

static void choose_setup(void) {
    char text[ARMY_SIZE + 8];
    uint8_t n;

    setup_random(own != 0);
    strcpy(text, "setup ");
    for(n=0; n<ARMY_SIZE; n++) text[6 + n] = piece_glyphs[PIECE_TYPE(board[setup_square(own, n)])];
    text[6 + ARMY_SIZE] = 0;
    reply(text);
}

static void go(void) {
    char text[24], a[8], b[8];
    uint8_t from, to;

    ai_move(own, enemy_lost, &from, &to);
    if(tracing == 2) fprintf(stderr, "chosen %u %u\n", from, to);
    if(from == NOWHERE) {
        reply("move none");
        return;
    }
    square_name(from, a);
    square_name(to, b);
    sprintf(text, "move %s %s", a, b);
    reply(text);
}

#ifdef AI_MEMORY
static void memory(uint8_t sq) {
    char text[128];
    uint8_t id;
    const ai_piece_history_t* piece;
    ai_memory_sync(); id = ai_memory_identity(sq); piece = ai_memory_history(id);
    if(!piece) { reply("history none"); return; }
    sprintf(text, "history %u %u %u %u %u %u %u %u %u %u %u", sq, id,
            piece->origin, piece->square, piece->owner, piece->moves, piece->battles,
            piece->known_rank, piece->approach_rank, piece->retreat_rank, piece->candidates);
    reply(text);
}
#endif

static void remove_piece(uint8_t sq) {
    uint8_t cell = board[sq];

    if(IS_PIECE(cell) && PIECE_TYPE(cell)<PIECE_TYPES) {
        uint8_t army=(cell&CELL_BLUE)?1:0;
        rules_lost[army][PIECE_TYPE(cell)]++;
        if(cell&CELL_REVEALED) rules_known_lost[army][PIECE_TYPE(cell)]++;
    }
    if(IS_PIECE(cell) && (cell & CELL_BLUE) != own && (cell & CELL_REVEALED))
        enemy_lost[PIECE_TYPE(cell)]++;
    board[sq] = CELL_EMPTY;
}

static void public_identity(uint8_t from, uint8_t to, uint8_t outcome) {
    uint8_t state[RULES_STATE_SIZE];
    uint8_t* identities=state+1+4*PIECE_TYPES+2;
    rules_state_save(state);
    if(outcome==BATTLE_ATTACKER || outcome==BATTLE_QUIET) identities[to]=identities[from];
    else if(outcome==BATTLE_BOTH) identities[to]=0;
    identities[from]=0;
    rules_state_load(state);
}

/**
 * @brief A quiet move by either army; a move over several squares shows a scout
 */
static void moved(uint8_t from, uint8_t to) {
    uint8_t cell = board[from];
    int rows = SQUARE_ROW(from) - SQUARE_ROW(to), cols = SQUARE_COL(from) - SQUARE_COL(to);
#ifdef AI_MEMORY
    ai_memory_observe(from, to, AI_MEMORY_QUIET);
#endif

    public_identity(from,to,BATTLE_QUIET);
    if(rows > 1 || rows < -1 || cols > 1 || cols < -1) {
        cell = (cell & ~CELL_TYPE) | PIECE_SCOUT | CELL_REVEALED;
    }
    board[to] = cell | CELL_MOVED;
    board[from] = CELL_EMPTY;
}

/**
 * @brief Resolve referee combat, disclosing ranks only when the rules allow it
 */
static void battle(uint8_t from, uint8_t to, int attacker, int defender) {
    uint8_t a = (board[from] & ~CELL_TYPE) | attacker | CELL_REVEALED | CELL_MOVED;
    uint8_t d = board[to];
    if(rules_reveal_defender(attacker)) d = (d & ~CELL_TYPE) | defender | CELL_REVEALED;

    board[from] = a;
    board[to] = d;
#ifdef AI_MEMORY
    ai_memory_observe(from, to, rules_battle(attacker, defender));
#endif
    switch(rules_battle(attacker, defender)) {
        case BATTLE_ATTACKER:
            remove_piece(to);
            board[to] = a;
            board[from] = CELL_EMPTY;
            break;
        case BATTLE_DEFENDER:
            remove_piece(from);
            break;
        default:
            remove_piece(from);
            remove_piece(to);
    }
}

/* Only observable ranks and the observable outcome cross the protocol. */
static void combat(uint8_t from,uint8_t to,uint8_t attacker,int defender,uint8_t outcome) {
    uint8_t a=(board[from]&~CELL_TYPE)|attacker|CELL_REVEALED;
    uint8_t d=board[to];
    if(defender>=0) d=(d&~CELL_TYPE)|defender|CELL_REVEALED;
    board[from]=a;board[to]=d;
#ifdef AI_MEMORY
    ai_memory_observe(from,to,outcome);
#endif
    public_identity(from,to,outcome);
    if(outcome!=BATTLE_ATTACKER) remove_piece(from);
    if(outcome!=BATTLE_DEFENDER) remove_piece(to);
    if(outcome==BATTLE_ATTACKER) board[to]=a|CELL_MOVED;
    board[from]=CELL_EMPTY;
}

static int reinforce(uint8_t trigger,uint8_t destination,int rank,uint8_t visible) {
    uint8_t owner,army,state[RULES_STATE_SIZE];
    if(trigger>=SQUARES || destination>=SQUARES || !IS_PIECE(board[trigger]) ||
       board[destination]!=CELL_EMPTY || rank>=PIECE_BOMB || (visible && rank<0)) return 0;
    owner=board[trigger]&CELL_BLUE;army=owner?1:0;
    if(!board_home(destination,army) || (owner==own && rank<0)) return 0;
    board[destination]=owner|(rank<0?PIECE_UNKNOWN:rank)|(visible?CELL_REVEALED:0);
    rules_rescues[army]++;
    if(rank>=0) {
        if(rules_lost[army][rank]) rules_lost[army][rank]--;
        if(visible && rules_known_lost[army][rank]) rules_known_lost[army][rank]--;
        if(owner!=own && visible && enemy_lost[rank]) enemy_lost[rank]--;
    }
    rules_state_save(state);state[1+4*PIECE_TYPES+2+trigger]=1;
    state[1+4*PIECE_TYPES+2+destination]=0;rules_state_load(state);
    return 1;
}

static void view(void) {
    uint8_t i,state[RULES_STATE_SIZE];
    ai_mask(own);rules_state_save(state);
    for(i=0;i<2;i++) if(!state[RULES_STATE_SIZE-2+i])
        state[RULES_STATE_SIZE-6+i]=state[RULES_STATE_SIZE-4+i]=255;
    printf("view %u ",own?1:0);
    for(i=0;i<SQUARES;i++) printf("%02x",board[i]);
    putchar(' ');
    for(i=0;i<PIECE_TYPES;i++) printf("%02x",enemy_lost[i]);
    putchar(' ');
    for(i=0;i<PIECE_TYPES;i++) printf("%02x",rules_lost[own?1:0][i]);
    putchar(' ');
    printf("%02x%02x ",rules_rescues[0],rules_rescues[1]);
    for(i=RULES_STATE_SIZE-6;i<RULES_STATE_SIZE;i++) printf("%02x",state[i]);
    putchar('\n');fflush(stdout);
}

static int hex(const char* text, uint8_t* out, int n) {
    int i;
    unsigned value;

    if(!text || (int)strlen(text) != 2 * n) return 0;
    for(i=0; i<n; i++) {
        if(sscanf(text + 2 * i, "%2x", &value) != 1) return 0;
        out[i] = value;
    }
    return 1;
}

#ifdef AI_FEATURE_TRACE
static void features(char* args) {
    char* army=strtok(args," ");
    char* lost=strtok(NULL," ");
    char* cells=strtok(NULL," ");
    char* cold=strtok(NULL," ");
    uint8_t sq,n,i,k,targets[MAX_TARGETS];
    if(!army || !hex(lost,enemy_lost,PIECE_TYPES) || !hex(cells,board,SQUARES)) {reply("error features");return;}
    own=atoi(army)?CELL_BLUE:0;
    if(cold && atoi(cold)) ai_memory_reset();
#ifdef AI_STUDENT_CONTEXT
    ai_student_inventory(enemy_lost);
#endif
    ai_student_begin(own);
    for(sq=0;sq<SQUARES;sq++) {
        if(!IS_PIECE(board[sq]) || (board[sq]&CELL_BLUE)!=own) continue;
        n=rules_targets(sq,targets);
        for(i=0;i<n;i++) {
            printf("feature %u %u",sq,targets[i]);
            for(k=0;k<AI_STUDENT_FEATURES;k++) printf(" %u",ai_student_feature(sq,targets[i],k));
            puts("");
        }
    }
    reply("features_done");
}
#endif

/**
 * @brief think <army> <seed> <lost: 24 hex digits> <board: 200 hex digits>
 *
 * Choose a move for a raw view, from a fresh state (no previous move);
 * the reply is "best <from> <to>" as square numbers 0-99 (255: none).
 */
static void think(char* args) {
    char text[24];
    char* army = strtok(args, " ");
    char* seed = strtok(NULL, " ");
    char* lost = strtok(NULL, " ");
    char* view = strtok(NULL, " ");
    char* repeat = strtok(NULL, " ");
    uint8_t from, to;
    int repetitions = repeat ? atoi(repeat) : 1;

    if(!army || !seed || repetitions < 1 || repetitions > 255 || !hex(lost, enemy_lost, PIECE_TYPES) || !hex(view, board, SQUARES)) {
        reply("error think");
        return;
    }
    own = atoi(army) ? CELL_BLUE : 0;
    random_seed(atoi(seed));
    ai_reset();
    rules_reset();
    tracing = getenv("FELDMARSCHALL_TRACE") != NULL;
    while(repetitions--) ai_move(own, enemy_lost, &from, &to);
    tracing = 0;
    sprintf(text, "best %d %d", from, to);
    reply(text);
}

static int difficulty(const char* name) {
    if(name && !strcmp(name, "easy")) ai_difficulty = AI_EASY;
    else if(name && !strcmp(name, "normal")) ai_difficulty = AI_NORMAL;
    else if(name && !strcmp(name, "hard")) ai_difficulty = AI_HARD;
    else return 0;
    return 1;
}

int main(int argc, char** argv) {
#ifdef FELDMARSCHALL_AI_ID
    if(argc == 2 && !strcmp(argv[1], "--identity")) {
        puts(FELDMARSCHALL_AI_ID);
        return 0;
    }
#endif
    char line[512], *command, *args;
    uint8_t from, to;
    int attacker, defender;

    if(argc != 1 && (argc != 3 || strcmp(argv[1], "--difficulty") || !difficulty(argv[2]))) {
        fputs("usage: feldmarschall-engine [--difficulty easy|normal|hard]\n", stderr);
        return 2;
    }
    random_seed(1);
    new_game(0);
    while(fgets(line, sizeof(line), stdin)) {
        line[strcspn(line, "\r\n")] = 0;
        command = strtok(line, " ");
        args = strtok(NULL, "");
        if(!command) continue;
        if(!strcmp(command, "feldmarschall")) {
            reply("id name cx16-feldmarschall");
            reply("id author Ivo Filot");
            reply("ok");
        } else if(!strcmp(command, "isready")) {
            reply("readyok");
        } else if(!strcmp(command, "seed")) {
            random_seed(args ? atoi(args) : 1);
        } else if(!strcmp(command, "rules")) {
            if(args && atoi(args) >= 0 && atoi(args) < 64) game_rules = atoi(args);
            else reply("error rules");
        } else if(!strcmp(command, "difficulty")) {
            if(!difficulty(args)) reply("error difficulty");
        } else if(!strcmp(command, "new")) {
            new_game(args && !strcmp(args, "blue"));
        } else if(!strcmp(command, "setup")) {
            if(args) {
                if(!place(args)) reply("error setup");
            } else {
                choose_setup();
            }
        }
#if defined(AI_TEST) && defined(AI_MISSIONS)
        else if(!strcmp(command, "guarded")) {
            from=square(strtok(args," "));to=square(strtok(NULL," "));
            if(from==NOWHERE || to==NOWHERE) reply("error squares");
            else {
                printf("guarded %u\n",ai_mission_training_guarded(from,to));
                fflush(stdout);
            }
        }
#endif
#ifdef AI_DIAGNOSTICS
        else if(!strcmp(command, "strategy")) {
#ifdef AI_TEST
            uint8_t state[AI_TEST_STATE_SIZE];
            unsigned index;
            ai_test_save(state);
            fputs("strategy ", stdout);
            for(index=0; index<AI_TEST_STATE_SIZE; index++) printf("%02x", state[index]);
            putchar('\n'); fflush(stdout);
#else
            reply("error strategy requires AI_TEST");
#endif
        }
#ifdef AI_DIAGNOSTIC_TRUTH
        /* Desktop ablation only. Compiled out of ordinary observers and game
         * engines; retain public movement flags and our own disclosure state. */
        else if(!strcmp(command, "diagnostic-truth") || !strcmp(command, "diagnostic-flag-spy") ||
                !strcmp(command, "diagnostic-flag")) {
            uint8_t truth[SQUARES], i;
            int all = !strcmp(command, "diagnostic-truth");
            int spy = !strcmp(command, "diagnostic-flag-spy");
            int valid = hex(args, truth, SQUARES);
            for(i=0; valid && i<SQUARES; i++) {
                if(IS_PIECE(board[i]) != IS_PIECE(truth[i])) valid=0;
                else if(IS_PIECE(board[i])) {
                    if((board[i]&CELL_BLUE)!=(truth[i]&CELL_BLUE) || PIECE_TYPE(truth[i])>=PIECE_TYPES ||
                       ((board[i]&CELL_BLUE)==own && PIECE_TYPE(board[i])!=PIECE_TYPE(truth[i]))) valid=0;
                } else if(board[i]!=truth[i]) valid=0;
            }
            if(!valid) {reply("error diagnostic truth mismatch");continue;}
            for(i=0; i<SQUARES; i++) if(IS_PIECE(board[i]) && (board[i]&CELL_BLUE)!=own &&
                    (all || PIECE_TYPE(truth[i])==PIECE_FLAG || (spy && PIECE_TYPE(truth[i])==PIECE_SPY)))
                board[i]=(board[i]&~CELL_TYPE)|PIECE_TYPE(truth[i])|CELL_REVEALED;
            reply("diagnostic-truthok");
        }
#endif
        else if(!strcmp(command, "position")) {
            char* army=strtok(args," ");char* lost=strtok(NULL," ");
            char* cells=strtok(NULL," ");char* history=strtok(NULL," ");
            uint8_t state[RULES_STATE_SIZE], shuttles[6];
            if(!army || !hex(lost,enemy_lost,PIECE_TYPES) || !hex(cells,board,SQUARES) ||
               !hex(history,shuttles,6)) {reply("error position");continue;}
            own=atoi(army) ? CELL_BLUE : 0;ai_mask(own);ai_reset();rules_reset();
            rules_state_save(state);memcpy(state+RULES_STATE_SIZE-6,shuttles,6);rules_state_load(state);
            reply("positionok");
        }
        else if(!strcmp(command, "ranked")) {
            tracing=1; go(); tracing=0;
        }
        else if(!strcmp(command, "played")) {
            uint8_t options[MAX_TARGETS], n, i;
            from = square(strtok(args, " ")); to = square(strtok(NULL, " "));
            if(from >= SQUARES || to >= SQUARES || !IS_PIECE(board[from]) ||
               (board[from] & CELL_BLUE) != own) { reply("error played"); continue; }
            n = rules_targets(from, options);
            for(i=0; i<n && options[i] != to; i++) {}
            if(i == n) { reply("error played"); continue; }
            ai_diagnostic_choice(own, from, to);
            reply("playedok");
        }
        else if(!strcmp(command, "public")) {
            uint8_t i, state[RULES_STATE_SIZE];
            rules_state_save(state);
            printf("public %u ", own ? 1 : 0);
            for(i=0; i<SQUARES; i++) printf("%02x", board[i]);
            putchar(' ');
            for(i=0; i<PIECE_TYPES; i++) printf("%02x", enemy_lost[i]);
            putchar(' ');
            for(i=RULES_STATE_SIZE-6; i<RULES_STATE_SIZE; i++) printf("%02x", state[i]);
            putchar('\n'); fflush(stdout);
        }
#endif
        else if(!strcmp(command, "go")) {
            go();
#ifdef AI_STUDENT
        } else if(!strcmp(command, "student")) {
            from=square(strtok(args," "));to=square(strtok(NULL," "));
            if(from==NOWHERE || to==NOWHERE) reply("error squares");
            else {
#ifdef AI_STUDENT_CONTEXT
                ai_student_inventory(enemy_lost);
#endif
                ai_student_begin(own);printf("learned %d\n",ai_student_score(from,to));fflush(stdout);
            }
#endif
#ifdef AI_MEMORY
        } else if(!strcmp(command, "memory")) {
            from = square(args);
            if(from == NOWHERE) reply("error square");
            else memory(from);
#endif
        } else if(!strcmp(command, "moved") || !strcmp(command, "battle")) {
            from = square(strtok(args, " "));
            to = square(strtok(NULL, " "));
            if(from == NOWHERE || to == NOWHERE) {
                reply("error squares");
            } else if(command[0] == 'm') {
                rules_record(from, to);
                moved(from, to);
            } else {
                args = strtok(NULL, " ");
                attacker = type_of(args ? args[0] : 0);
                args = strtok(NULL, " ");
                defender = type_of(args ? args[0] : 0);
                if(attacker < 0 || defender < 0) {
                    reply("error ranks");
                } else {
                    rules_record(from, to);
                    battle(from, to, attacker, defender);
                }
            }
        } else if(!strcmp(command, "combat")) {
            char ag, dg, result;
            char first[8],second[8];
            if(!args || sscanf(args,"%7s %7s %c %c %c",first,second,&ag,&dg,&result)!=5 ||
               (from=square(first))==NOWHERE || (to=square(second))==NOWHERE ||
               (attacker=type_of(ag))<0 || (dg!='?' && type_of(dg)<0) ||
               !strchr("ADX",result) || !IS_PIECE(board[from]) || !IS_PIECE(board[to])) reply("error combat");
            else {
                rules_record(from,to);
                combat(from,to,attacker,type_of(dg),result=='A'?BATTLE_ATTACKER:result=='D'?BATTLE_DEFENDER:BATTLE_BOTH);
            }
        } else if(!strcmp(command, "reinforce")) {
            char rank;unsigned visible;char first[8],second[8];
            if(!args || sscanf(args,"%7s %7s %c %u",first,second,&rank,&visible)!=4 || visible>1 ||
               (rank!='?' && type_of(rank)<0) ||
               !reinforce(square(first),square(second),type_of(rank),visible)) reply("error reinforce");
        } else if(!strcmp(command, "view")) {
            view();
        } else if(!strcmp(command, "think")) {
            think(args);
#ifdef AI_FEATURE_TRACE
        } else if(!strcmp(command, "features")) {
            features(args);
#endif
#ifdef AI_TRACE
        } else if(!strcmp(command, "trace")) {
            tracing = args && !strcmp(args, "on") ? 2 : 0;
#endif
        } else if(!strcmp(command, "quit")) {
            break;
        } else {
            reply("error unknown command");
        }
    }
    return 0;
}
