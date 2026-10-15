#include "SEARCH.H"

#define MARKER_BASE 0x3ea1
#define ROW_STRIDE 72
#define COL_STRIDE 6

static int marker_at(int row, int col)
{
    return *(volatile unsigned char *)(MARKER_BASE + row * ROW_STRIDE +
                                       col * COL_STRIDE) != 0;
}

/* ovl6:03F0..0650 (608 bytes). The C07E random routine is kept as an
 * explicit boundary. Tests inject the same nonnegative AX result into both
 * original instructions and C; no random-number algorithm is inferred. */
void pascal far search_and_clear_marker(int initial_row, int endpoint_a,
                                        int endpoint_b, int *output)
{
    int lower = endpoint_a;
    int upper = endpoint_b;
    int center, found, row, right, left, checked_total, row_attempt;
    unsigned int random_word;

    if (lower > upper) {
        int swap = lower;
        lower = upper;
        upper = swap;
    }

    output[0] = initial_row;
    random_word = ovl6_random_word();
    center = lower + (int)(random_word % (unsigned int)(upper - lower + 1));
    output[1] = center;
    found = marker_at(output[0], output[1]);

    row = initial_row;
    row_attempt = 0;
    while (!found && row_attempt < 4) {
        int checked_inside = 0;
        checked_total = 0;
        right = center;
        left = center;
        while (!found && checked_inside < upper - lower + 1) {
            if (right == center) {
                if (marker_at(row, center)) {
                    output[0] = row;
                    output[1] = center;
                    found = 1;
                }
                ++checked_inside;
                ++checked_total;
            }
            ++right;
            if (!found && right <= upper) {
                if (marker_at(row, right)) {
                    output[0] = row;
                    output[1] = right;
                    found = 1;
                }
                ++checked_inside;
                ++checked_total;
            }
            --left;
            if (!found && left >= lower) {
                if (marker_at(row, left)) {
                    output[0] = row;
                    output[1] = left;
                    found = 1;
                }
                ++checked_inside;
                ++checked_total;
            }
        }

        /* Outside the endpoint interval, alternate toward the board edges. */
        while (!found && checked_total < 10) {
            ++right;
            if (right <= 10) {
                if (marker_at(row, right)) {
                    output[0] = row;
                    output[1] = right;
                    found = 1;
                }
                ++checked_total;
            }
            --left;
            if (!found && left >= 1) {
                if (marker_at(row, left)) {
                    output[0] = row;
                    output[1] = left;
                    found = 1;
                }
                ++checked_total;
            }
        }

        ++row_attempt;
        ++row;
        if (row > 4) row = 1;
    }

    if (output[0] <= 0 || output[0] >= 5 ||
        output[1] <= 0 || output[1] >= 11 ||
        !marker_at(output[0], output[1])) {
        output[0] = 0;
        output[1] = 0;
    } else {
        *(volatile unsigned char *)(MARKER_BASE + output[0] * ROW_STRIDE +
                                    output[1] * COL_STRIDE) = 0;
    }
}
