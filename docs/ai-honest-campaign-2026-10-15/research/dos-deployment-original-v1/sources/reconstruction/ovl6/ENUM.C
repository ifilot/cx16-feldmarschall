#include "ENUM.H"

#define CELL_ROW_STRIDE 72
#define CELL_COL_STRIDE 6
#define CELL_OCCUPIED 0x3ea1
#define CELL_SIDE     0x3e9c
#define CELL_KIND     0x3e9e

/* ovl6:005A..013B (225 bytes). The only external operation is the INT 3Fh
 * dispatch to ovl1:A733, represented here by the explicit callback boundary. */
void far enumerate_drawable_cells(void)
{
    int row, col;

    for (row = 1; row <= 10; ++row) {
        for (col = 1; col <= 10; ++col) {
            unsigned offset = row * CELL_ROW_STRIDE + col * CELL_COL_STRIDE;
            int kind;
            int row_coordinate, col_coordinate;
            unsigned char selector;

            if (*(unsigned char *)(CELL_OCCUPIED + offset) != 0)
                continue;
            if (*(unsigned char *)(CELL_SIDE + offset) == 0)
                continue;

            selector = *(unsigned char *)0x65de;
            kind = *(int *)(CELL_KIND + offset);
            if (selector != 0) {
                row_coordinate = 26 + 43 * (row - 1);
                col_coordinate = 11 + 43 * (col - 1);
            } else {
                row_coordinate = 6 + 19 * (row - 1);
                col_coordinate = 5 + 20 * (col - 1);
            }
            ovl1_a733_callback(1, row_coordinate, col_coordinate, kind);
        }
    }
}

/* ovl6:013B..032F (500 bytes; exclusive end). RETF 4; Pascal order is
 * (column, slot), so [BP+8] selects a column and [BP+6] is the slot. */
int pascal far write_or_read_slot_word(int column, int slot)
{
    unsigned short offset = (unsigned short)(0x541b + column * 30 + slot * 6);
    int value;

    switch (column) {
    case 0:
        if (slot == 0) *(int *)offset = 10;
        else if (slot > 0 && slot < 4) *(int *)offset = slot;
        else if (slot == 4) *(int *)offset = 3;
        break;
    case 2:
        if (slot >= 0 && slot < 3) *(int *)offset = 4;
        else if (slot >= 3 && slot < 5) *(int *)offset = 5;
        break;
    case 4:
        if (slot >= 0 && slot < 2) *(int *)offset = 5;
        else if (slot >= 2 && slot < 5) *(int *)offset = 6;
        break;
    case 6:
        *(int *)offset = (slot == 0) ? 6 : 7;
        break;
    case 8:
        *(int *)offset = 8;
        break;
    case 10:
        *(int *)offset = 9;
        break;
    case 12:
        if (slot >= 0 && slot < 3) *(int *)offset = 9;
        else *(int *)offset = 11;
        break;
    case 14:
        *(int *)offset = (slot == 4) ? 0 : 11;
        break;
    default:
        *(int *)offset = 12;
        break;
    }

    value = *(int *)offset;
    return value;
}

/* ovl6:032F..03F0 (193 bytes). */
void far initialize_slot_words(void)
{
    static const unsigned int offsets[] = {
        0x00,0x06,0x12,0x18,0x24,0x30,0x42,0x48,0x4e,0x54,
        0x66,0x6c,0x78,0x8a,0x96,0x9c,0xa2,0xa8,0xae,0xb4,
        0xba,0xc0,0xd2,0xd8,0xde,0xe4,0xea,0xf0,0xf6,0xfc,
        0x102,0x108
    };
    static const int values[] = {
        6,7,3,2,6,5,7,8,1,8,5,8,11,4,11,10,5,11,6,7,
        11,4,11,6,8,5,7,8,3,11,4,0
    };
    int i;
    for (i = 0; i < 32; ++i)
        *(int *)(0x40a2 + offsets[i]) = values[i];
}
