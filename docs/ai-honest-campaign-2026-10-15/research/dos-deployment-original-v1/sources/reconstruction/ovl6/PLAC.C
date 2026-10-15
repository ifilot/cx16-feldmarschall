#include "PLAC.H"
#include "SETUP.H"
#include "SEARCH.H"

unsigned int far rng_next(void);

#define CELL 0x3e9e
#define MARK 0x3ea1
#define ROW_STEP 72
#define COL_STEP 6
#define READ_WORD(a) (*(volatile int *)(unsigned int)(a))
#define WRITE_WORD(a,v) (READ_WORD(a) = (v))
#define READ_BYTE(a) (*(volatile unsigned char *)(unsigned int)(a))
#define WRITE_BYTE(a,v) (READ_BYTE(a) = (unsigned char)(v))

static unsigned int cell(int row, int col)
{
    return (unsigned int)(CELL + row * ROW_STEP + col * COL_STEP);
}

static int value_at(int row, int col)
{
    return READ_WORD(cell(row, col));
}

static void put_value(int row, int col, int value)
{
    WRITE_WORD(cell(row, col), value);
}

static void put_clear(int row, int col, int value)
{
    put_value(row, col, value);
    WRITE_BYTE(cell(row, col) + 3, 0);
}

static int blocked_shape(int col, int row)
{
    int north = row - 1;
    int south = row + 1;
    int west = col - 1;
    int east = col + 1;
    int north_blocked = north < 1 || value_at(north, col) == 11;
    int south_blocked = south > 4 ?
        (col == 3 || col == 4 || col == 7 || col == 8) :
        value_at(south, col) == 11;
    int west_blocked = west < 1 || value_at(row, west) == 11;
    int east_blocked = east >= 11 || value_at(row, east) == 11;
    return north_blocked && south_blocked && west_blocked && east_blocked;
}

/* The helper at 09A1 is retained as a narrow original-call boundary in the
 * raw fixture; this C body follows its four independent word probes. */
int pascal far placement_shape_test(int col, int row)
{
    return blocked_shape(col, row);
}

static void opening_table_layout(int phase)
{
    unsigned int start = 0x190eU;
    unsigned int table;
    unsigned int r, c;
    int which;
    int reverse;

    if (phase <= 3)
        which = (int)(rng_next() % 4U) + 4;
    else
        which = (int)(rng_next() % 4U);
    table = start + (unsigned int)(which * 40);
    reverse = (rng_next() % 2U) != 0;
    for (r = 1; r <= 4; ++r) {
        for (c = 1; c <= 10; ++c) {
            unsigned int col = reverse ? 11U - c : c;
            put_clear((int)r, (int)col, READ_BYTE(table++));
        }
    }
}

/* ovl6:0C7B..1D1A, 4255-byte no-argument far routine. */
void far placement_driver(void)
{
    int phase = READ_WORD(0x3e90);
    int start_row, start_col, initial_row, row, col;
    int direction, rank_value, local_count;
    unsigned char count[12] = {1, 1, 1, 2, 3, 4, 4, 4, 5, 8, 1, 6};
    int rank8_cols[20];
    int rank8_count = 0;
    int chosen, second, distance, target_row, target_col;
    int output[2];
    int i, r, c, rank, mode4;

    if (phase == 5) {
        if (rng_next() % 5U != 0) {
            opening_table_layout(phase);
            return;
        }
    } else if (phase == 4) {
        if (rng_next() % 5U == 0) {
            opening_table_layout(phase);
            return;
        }
    } else if (phase == 3) {
        if (rng_next() % 5U != 0) {
            opening_table_layout(phase);
            return;
        }
    }

    if (phase < 3) {
        WRITE_WORD(0x5e8a, 0);
    } else if (rng_next() % 5U == 0) {
        WRITE_WORD(0x5e8a, 1);
    } else {
        WRITE_WORD(0x5e8a, 0);
    }

    initial_row = (rng_next() % 5U == 0 && phase < 3) ? 2 : 1;
    if (initial_row == 1) {
        start_row = 1;
        target_row = 10;
    } else {
        start_row = 2;
        target_row = 9;
    }
    search_and_clear_marker(initial_row, start_row, target_row, output);
    row = output[0];
    col = output[1];
    put_value(row, col, 0);
    start_col = col;
    start_row = row;

    if (row == 1) {
        if (col == 1 || col == 10) {
            direction = col == 1 ? 1 : -1;
            if (rng_next() % 5U == 1) {
                put_clear(row + 1, col, 11);
                put_clear(row, col + direction, 11);
                rank_value = (int)(rng_next() % 2U) + 5;
                --count[rank_value];
                put_clear(row + 1, col + direction, rank_value);
                rank_value = (int)(rng_next() % 2U) + 5;
                --count[rank_value];
                put_clear(row, col + 2 * direction, rank_value);
                count[11] -= 2;
            } else {
                put_clear(row + 2, col, 11);
                put_clear(row + 1, col + direction, 11);
                put_clear(row, col + 2 * direction, 11);
                rank_value = (int)(rng_next() % 2U) + 5;
                --count[rank_value];
                put_clear(row + 1, col, rank_value);
                rank_value = (int)(rng_next() % 2U) + 5;
                --count[rank_value];
                put_clear(row, col + direction, rank_value);
                count[11] -= 3;
            }
        } else {
            put_clear(row + 1, col, 11);
            put_clear(row, col + 1, 11);
            put_clear(row, col - 1, 11);
            rank_value = (int)(rng_next() % 2U) + 5;
            --count[rank_value];
            put_clear(2, col - 1, rank_value);
            rank_value = (int)(rng_next() % 2U) + 5;
            --count[rank_value];
            put_clear(2, col + 1, rank_value);
            count[11] -= 3;
        }
    } else {
        put_clear(row - 1, col, 11);
        put_clear(row + 1, col, 11);
        count[11] -= 2;
        if (col > 1) {
            rank_value = (int)(rng_next() % 2U) + 5;
            --count[rank_value];
            put_clear(row - 1, col - 1, rank_value);
            rank_value = (int)(rng_next() % 2U) + 6;
            --count[rank_value];
            put_clear(row + 1, col - 1, rank_value);
            --count[11];
            put_clear(row, col - 1, 11);
        }
        if (col < 10) {
            rank_value = (int)(rng_next() % 2U) + 6;
            --count[rank_value];
            put_clear(row - 1, col + 1, rank_value);
            rank_value = (int)(rng_next() % 2U) + 5;
            --count[rank_value];
            put_clear(row + 1, col + 1, rank_value);
            --count[11];
            put_clear(row, col + 1, 11);
        }
    }

    setup_marked_cell(8, 1);
    setup_marked_cell(8, 1);
    setup_marked_cell(8, 2);
    setup_marked_cell(8, 3);
    setup_marked_cell(8, (int)(rng_next() % 2U) + 2);
    count[8] -= 5;

    for (r = 2; r <= 3; ++r)
        for (c = 1; c <= 10; ++c)
            if (READ_BYTE(cell((int)r, (int)c) + 3) == 0 &&
                value_at((int)r, (int)c) == 8)
                rank8_cols[rank8_count++] = (int)c;

    chosen = (int)(rng_next() % (unsigned int)rank8_count);
    chosen = rank8_cols[chosen];
    distance = 0;
    while (rank8_count != 0) {
        --rank8_count;
        i = rank8_cols[rank8_count] - chosen;
        if (i < 0) i = -i;
        if (distance < i) {
            distance = i;
            second = rank8_cols[rank8_count];
        }
    }

    target_row = (READ_BYTE(0x3f31 + chosen * 6) == 0 &&
                  READ_WORD(0x3f2e + chosen * 6) == 8) ? 3 : 4;
    col = chosen;
    if (target_row == 4) {
        while (col < 3 || col > 8 || col == 5 || col == 6 ||
               READ_BYTE(0x3fc1 + col * 6) == 0) {
            if (++col > 10) col = 1;
        }
        if (READ_WORD(0x3f76 + chosen * 6) == 8 &&
            READ_BYTE(0x3f79 + col * 6) != 0) {
            WRITE_WORD(0x3f76 + chosen * 6, 9);
            WRITE_BYTE(0x3f79 + chosen * 6, 1);
            WRITE_WORD(0x3f76 + col * 6, 8);
            WRITE_BYTE(0x3f79 + col * 6, 0);
        }
    }
    target_col = col;
    put_clear(target_row, col, 1);

    local_count = (READ_BYTE(0x3f31 + second * 6) == 0 &&
                   READ_WORD(0x3f2e + second * 6) == 8) ? 3 : 4;
    col = second;
    if (local_count == 4) {
        for (;;) {
            /* The original overwrites its chosen-column local with the first
             * destination column before applying this separation test. */
            i = col - target_col;
            if (i < 0) i = -i;
            if (i > 1 && col > 2 && col < 9 && col != 5 && col != 6 &&
                READ_BYTE(0x3fc1 + col * 6) != 0)
                break;
            if (++col > 10) col = 1;
        }
        if (READ_WORD(0x3f76 + second * 6) == 8 &&
            READ_BYTE(0x3f79 + col * 6) != 0) {
            WRITE_WORD(0x3f76 + second * 6, 9);
            WRITE_BYTE(0x3f79 + second * 6, 1);
            WRITE_WORD(0x3f76 + col * 6, 8);
            WRITE_BYTE(0x3f79 + col * 6, 0);
        }
    }
    put_clear(local_count, col, 2);

    for (i = count[11]; i != 0; --i)
        setup_marked_cell(11, (int)(rng_next() % 3U) + 1);
    setup_marked_cell(10, 2);

    for (i = 0; i < 2; ++i)
        setup_marked_cell(3, i == 0 ? 2 : 4);

    mode4 = 0;
    for (i = 0; i < count[4]; ++i) {
        if (mode4 == 0) {
            rank = (int)(rng_next() % 4U) + 1;
            if (rank == 4) mode4 = 1;
        } else {
            rank = (int)(rng_next() % 2U) + 2;
        }
        setup_marked_cell(4, rank);
    }

    for (i = 0; i < count[5]; ++i) {
        rank = (int)(rng_next() % 2U) + 2;
        if (rank < 3) rank = (int)(rng_next() % 3U) + 2;
        setup_marked_cell(5, rank);
    }
    for (i = 0; i < count[6]; ++i)
        setup_marked_cell(6, (int)(rng_next() % 3U) + 2);
    for (i = 0; i < count[7]; ++i)
        setup_marked_cell(7, (int)(rng_next() % 3U) + 2);

    for (i = 0; i < count[9]; ++i) {
        search_and_clear_marker(1, 1, 10, output);
        put_value(output[0], output[1], 9);
    }

    /* The final scan tests whether each occupied square has a neighboring
     * occupied square with a clear shape. It relocates values 6 or 9 to an
     * empty square containing 6 or 9 in the observed pattern. */
    for (r = 1; r <= 4; ++r) {
        for (c = 1; c <= 10; ++c) {
            int v = value_at((int)r, (int)c);
            int dr = (int)r - start_row;
            int dc = (int)c - start_col;
            if (v <= 0 || !((v < 6) || v == 8 || v == 10))
                continue;
            if (((dc < 0 ? -dc : dc) == 1 && dr == 0) ||
                (dc == 0 && (dr < 0 ? -dr : dr) == 1))
                continue;
            if (!placement_shape_test((int)c, (int)r))
                continue;
            dr = (int)r - start_row;
            dc = (int)c - start_col;
            if (dr < 0) dr = -dr;
            if (dc < 0) dc = -dc;
            distance = (dr == 1 || dc == 1) ? 6 : 9;
            target_row = 1;
            target_col = 1;
            while (target_row < 5 &&
                   (value_at(target_row, target_col) != distance ||
                    placement_shape_test(target_col, target_row))) {
                if (++target_col > 10) {
                    target_col = 1;
                    ++target_row;
                }
            }
            if (target_row < 5) {
                put_value((int)target_row, (int)target_col, v);
                put_value((int)r, (int)c, distance);
            }
        }
    }
}
