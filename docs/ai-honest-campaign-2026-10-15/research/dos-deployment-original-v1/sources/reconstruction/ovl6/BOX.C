#include "BOX.H"

#define CELL_WORD_BASE 0x3e9e
#define ROW_STRIDE 72
#define COL_STRIDE 6

static int cell_word(int row, int col)
{
    unsigned int offset = (unsigned int)(CELL_WORD_BASE +
                                         row * ROW_STRIDE + col * COL_STRIDE);
    return *(volatile int *)offset;
}

/* ovl6:0650..0736 (230 bytes). Arguments are Pascal ordered as
 * (row1, row2, col1, col2). If row1 > row2, it swaps only the row arguments.
 * It then scans rows inclusively and columns in the supplied direction.
 * For each byte at3EA1+72*row+6*col that is zero, add11 minus the word at
 * 3E9E+72*row+6*col when that word is signed-positive and below11.
 * This describes observed instructions;
 * it does not assert a game meaning for the word. */
int pascal far sum_board_words_in_box(int row1, int row2,
                                      int col1, int col2)
{
    int total = 0;
    int row, col;

    if (row1 > row2) {
        int swap = row1;
        row1 = row2;
        row2 = swap;
    }

    for (row = row1; row <= row2; ++row) {
        for (col = col1; col <= col2; ++col) {
            if (*(volatile unsigned char *)(CELL_WORD_BASE + row * ROW_STRIDE +
                                            col * COL_STRIDE + 3) == 0) {
                int value = cell_word(row, col);
                if (value > 0 && value < 11)
                    total += 11 - value;
            }
        }
    }
    return total;
}
