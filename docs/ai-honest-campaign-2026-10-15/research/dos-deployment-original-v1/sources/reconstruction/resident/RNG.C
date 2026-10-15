#include "RNG.H"

#define RNG_STATE_LO 0x3544
#define RNG_STATE_HI 0x3546

static unsigned int state_word(unsigned int address)
{
    return *(volatile unsigned int *)address;
}

static void set_state_word(unsigned int address, unsigned int value)
{
    *(volatile unsigned int *)address = value;
}

/* resident:0C06D..0C07E, caller-clean far routine. */
void far rng_seed16(unsigned int seed)
{
    set_state_word(RNG_STATE_HI, 0);
    set_state_word(RNG_STATE_LO, seed);
}

/* resident:0C07E..0C0A6 (40 bytes). This is modulo-2^32 recurrence, with
 * the low 15 bits of the updated high word returned in AX. */
unsigned int far rng_next(void)
{
    unsigned long state = ((unsigned long)state_word(RNG_STATE_HI) << 16) |
                          state_word(RNG_STATE_LO);
    state = state * 0x015a4e35UL + 1UL;
    set_state_word(RNG_STATE_HI, (unsigned int)(state >> 16));
    set_state_word(RNG_STATE_LO, (unsigned int)state);
    return (unsigned int)((state >> 16) & 0x7fffUL);
}
