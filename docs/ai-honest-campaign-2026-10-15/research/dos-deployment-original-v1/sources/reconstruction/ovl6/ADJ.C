#include "ADJ.H"

#define CELL_WORD_BASE 0x3e9e
#define CELL_MARK_BASE 0x3ea1
#define ROW_STRIDE 72
#define COL_STRIDE 6

static int matches(int row, int col, int value)
{
    unsigned int offset = (unsigned int)(CELL_WORD_BASE +
                                         row * ROW_STRIDE + col * COL_STRIDE);
    unsigned int marker = (unsigned int)(CELL_MARK_BASE +
                                         row * ROW_STRIDE + col * COL_STRIDE);

    if (*(volatile unsigned char *)marker != 0)
        return 0;
    return *(volatile int *)offset == value;
}

/* This follows the eight explicit neighbor probes at ovl6:0736..09A1.
 * The asymmetric bounds and mode test are retained literally; no board
 * interpretation is inferred from them. */
int pascal far count_adjacent_matching_cells(int col, int row,
                                              int value, int mode)
{
    int count = 0;

    if (row - 1 > 0 && matches(row - 1, col, value))
        ++count;
    if (mode == 0 && col - 1 > 0 &&
        matches(row - 1, col - 1, value))
        ++count;
    if (mode == 0 && col + 1 < 11 &&
        matches(row - 1, col + 1, value))
        ++count;

    if (col - 1 > 0 && matches(row, col - 1, value))
        ++count;
    if (col + 1 < 11 && matches(row, col + 1, value))
        ++count;

    if (row + 1 < 5 && matches(row + 1, col, value))
        ++count;
    if (mode == 0 && col + 1 < 11 &&
        matches(row + 1, col + 1, value))
        ++count;
    if (mode == 0 && col - 1 > 0 &&
        matches(row + 1, col - 1, value))
        ++count;

    return count;
}
