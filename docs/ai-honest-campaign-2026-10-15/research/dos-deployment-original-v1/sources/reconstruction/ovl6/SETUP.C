#include "SETUP.H"
#include "BOX.H"
#include "ADJ.H"
#include "SEARCH.H"

unsigned int far rng_next(void);

#define CELL_BASE 0x3e9e
#define MARK_BASE 0x3ea1
#define ROW_STRIDE 72
#define COL_STRIDE 6

static void set_word(int row, int col, int value)
{
    unsigned int at = (unsigned int)(CELL_BASE + row * ROW_STRIDE + col * COL_STRIDE);
    *(volatile int *)at = value;
}

static int marked(int row, int col)
{
    unsigned int at = (unsigned int)(MARK_BASE + row * ROW_STRIDE + col * COL_STRIDE);
    return *(volatile unsigned char *)at != 0;
}

static void clear_mark(int row, int col)
{
    unsigned int at = (unsigned int)(MARK_BASE + row * ROW_STRIDE + col * COL_STRIDE);
    *(volatile unsigned char *)at = 0;
}

unsigned int far ovl6_random_word(void)
{
    return rng_next();
}

/* ovl6:0AD2..0C7B (425 bytes), far Pascal (value,row), RETF 4.
 * The input roles describe observed data use, not piece/game roles. */
void pascal far setup_marked_cell(int value, int row)
{
    int box_a = sum_board_words_in_box(1, 4, 1, 5);
    int box_b = sum_board_words_in_box(1, 4, 6, 10);
    int candidate_count = 0;
    int phase = 0;
    unsigned char candidates[16];
    int col;
    int chosen_col;

    while (1) {
        int mode = phase > 1 ? 1 : 0;
        for (col = 1; col <= 10; ++col) {
            int axial_11;
            int other_adjacent;
            int reject;

            if (!marked(row, col))
                continue;

            axial_11 = count_adjacent_matching_cells(col, row, 11, 1);
            other_adjacent = count_adjacent_matching_cells(col, row, value, mode);
            reject = other_adjacent != 0;
            if (!reject && value == 11 && row == 1 && (col == 1 || col == 10))
                reject = 1;
            if (axial_11 != 0 && value >= 8)
                continue;

            if (phase <= 2) {
                if (box_a < box_b) {
                    if (col >= 6)
                        continue;
                } else {
                    if (box_a <= box_b || col <= 5)
                        continue;
                }
            }

            if (!reject && candidate_count < 16)
                candidates[candidate_count++] = (unsigned char)col;
        }

        if (candidate_count != 0)
            break;
        ++phase;
        if (phase >= 4)
            break;
    }

    if (candidate_count == 0) {
        int output[2];
        search_and_clear_marker(row, 1, 10, output);
        row = output[0];
        chosen_col = output[1];
    } else {
        unsigned int pick = rng_next() % (unsigned int)candidate_count;
        chosen_col = candidates[pick];
    }

    set_word(row, chosen_col, value);
    clear_mark(row, chosen_col);
}
