# Independent four-execution interaction analysis

The frozen factorial protocol remains unchanged. Run the helper only after all
four planned tournaments are complete. It reads SQLite directly in read-only
mode and pins every input file, protocol and helper by SHA256; it does not replay
or rerun any game. Existing cycle audits remain responsible for legal trajectories
and executable provenance. The helper additionally pins recorded source/runtime
receipts and requires one unchanged frozen DOS opponent in all four executions.

Supply `--protocol FACTORIAL-PROTOCOL.json`, `--output factorial-result.json`, and
each of these options followed by its tournament path and immutable policy ID:

- `--book-base`: C110 `student-fortress-template-flag-bomb-v1-normal`.
- `--book-guard`: C110 `student-fortress-inner-guard-template-v1-normal`.
- `--native-base`: C114 `student-fortress-deployment-v1-normal`.
- `--native-guard`: C114 `student-fortress-inner-guard-v1-normal`.

The helper requires four distinct physical execution files and four policy IDs;
reusing a control or copying its evidence into multiple cells is rejected. Every
planned pair and both candidate colors must exist, including error prefixes.
Game IDs, pair IDs, families, move seeds and the opponent armies must match across
all four cells. Within each placement level, the book/native own armies must be
identical. Placement levels must differ. Each side-swapped pair must follow the
declared rotated-owned-setup contract. Rules, move limits and cohort metadata
must agree.

The interaction is `(book_guard-book_base)-(native_guard-native_base)`, computed
first for each common complete eight-game block, then averaged. The interval uses
20,000 paired bootstrap replicates of these common four-arm blocks, with fixed
analysis RNG seed3110114. It never subtracts means from different complete-case
cohorts. Report this exploratory interval separately from the two prespecified
within-study primary comparisons.

All128plannedpairs also receive finite-cohort interaction bounds: each unscored
error game independently takes any score in [0,1], with its sign propagated
through the four-arm contrast. Those bounds use the full planned denominator,
are not confidence intervals, and make no missing-at-random assumption.

`tools/test_new_campaign_inner_guard_factorial.py` has ten synthetic SQL tests:
constant interaction/oracle interval, side-pair averaging, common-four-arm
complete cases, all-error bounds, missing pairs, unmatched seeds/opponent armies,
within-placement own-army mismatch, reused controls and incomplete inputs.
No C110/C114 outcomes were inspected while writing or qualifying the helper.
