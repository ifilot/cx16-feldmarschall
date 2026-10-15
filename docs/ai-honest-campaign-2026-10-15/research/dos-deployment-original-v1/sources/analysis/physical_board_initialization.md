# Physical-board initialization

BINIT.C reconstructs overlay6:1D1A..1DDD (195 bytes) and
1DDD..1F52 (373 bytes), with original module/offset provenance retained.
The first function is far cdecl with no arguments. The second is far Pascal
with one word argument, whose low byte controls the optional lower template.

1D1A marks physical rows1..4, columns1..10 available and sets their owner byte
to1 before calling the randomized0C7B setup driver. After that call it writes
eight words of11 to each of three128-byte banks beginning at DS55FD. Their
full purpose remains unresolved; retained bytes surrounding them are tested.

1DDD resets every padded12-by-12 cell: owner0, rank9, availability1 and
field+4 equal to1. Field+1 is preserved. It calls1D1A, then checks the forty
top cells. Any remaining nonzero availability marker restarts the entire
initialization, including0C7B and the three bank resets. There is no retry
limit in the original or reconstructed function.

Once top placement succeeds, it clears cell+4 at rows5/6, columns3/4/7/8,
exactly the standard lake coordinates. This strongly suggests a traversability
field, but its movement consumers still need direct tracing. If the argument's
low byte is nonzero, the function calls032F, which writes32 lower-board rank
words. It then sets owner0 and field+4=1 for every lower square, marking them
occupied only in the nonzero-low-byte case. With a zero low byte, their rank
words remain placeholder9 and their markers remain available.

The resulting fixed lower arrangement, using numeric ranks, is:

| Physical row | Columns1 through10 |
| --- | --- |
| 7 | 9,6,7,9,3,2,9,6,9,5 |
| 8 | 7,8,1,8,9,9,5,8,9,11 |
| 9 | 4,9,11,10,5,11,6,7,11,4 |
| 10 | 11,6,8,5,7,8,3,11,4,0 |

The unmodified193-byte032F leaf supplies32 assignments; the other eight
squares retain rank9 from initialization. Its rank multiset is a complete
40-piece arrangement: 0:1,1:1,2:1,3:2,4:3,5:4,6:4,7:4,8:5,9:8,10:1,11:6.
The actual table above should be checked against its pinned instructions;
these numeric ranks use the separately verified game rank-name mapping.

Run `python3 scripts/verify_ovl6_board_init.py` and add `--template` for the
composition with exact raw032F versus ENUM.C. Each checks66 cases spanning
three byte patterns, no/one/two failed placement attempts, first/last missing
top squares, and flags0/1/2/-1/0100/0101/7F00. Every byte of DS3E00..59FF is
compared, including the three banks. Full watched-memory snapshots at each
callback entry also match, preserving ordering and retry effects. The fixture
reserves7000h DGROUP before C globals and checks far-heap snapshot aliases.
Linked original bodies retain all non-call bytes and the internal1E54 call;
the two external calls and their far-tail stub targets are checked, including
MZ segment relocations and equivalent segment:offset aliases.

0C7B remains a deterministic controlled placement boundary in both variants.
The ordinary variant controls032F too, using an observer that changes lower
fields to verify later overwrites. The template variant runs the independent
original193-byte leaf and the recovered C leaf. These are scoped initializer
comparisons, not observations of ordinary game startup or integrated gameplay.
