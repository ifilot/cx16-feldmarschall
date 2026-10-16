# Preserve deployment treatments in frozen-corpus tests

`dataset_role="opponent-only-v1"` supplies only selected record **Army B** as the
opponent. It requires `setup_mode="policy-owned-rotated-v1"`. The first policy
still generates its own army through the existing frozen setup-selection
protocol; Army A never enters either game. Both armies reflect in their local
front-first encoding when the owner plays Blue, preserving physical rotation.

This enables a frozen deployment candidate and reference to face the exact same
held-out opponent layouts without forcing away their own deployment difference.
The role is explicit and versioned. Default `referee-v1` still requires referee
setups and uses both A and B exactly as before. Old saved referee tournaments
without a role field remain readable as `referee-v1`. Ambiguous combinations
fail before output creation or policy builds.

The saved tournament embeds the unchanged corpus, selected record identities,
role, contract and current selector source. Verification checks stable game IDs,
participant order, family, move seed, and corpus B against both the actual
opponent and the independent owned-setup record, including Blue-owner reflection.
Forging the owned record and both game halves together cannot replace corpus B.
Existing owner transcript, whitelist, selection-seed and paired-rotation checks
remain in force. No corpus metadata or enemy setup is passed to an honest policy.

Campaign plans add `"role": "opponent-only-v1"` inside their existing `dataset`
object and declare `"setup_mode": "policy-owned-rotated-v1"`. The campaign runner
passes both through and compares common opponent layouts across candidate arms,
allowing their own armies to differ. Formal selection and stopping rules must be
frozen before validation play. See [CLI examples](../../../tournament-desk.md).

Checks retained here:

- `dataset-checks.log`: seven tests, including identical Python/OpenMP games,
  complete native/Python replay, portability after hiding the source dataset,
  combined record/game forgery rejection, illegal role/mode rejection, legacy
  role-less compatibility and unchanged full-corpus validity.
- `campaign-runner-checks.log`: eight tests, including a full frozen campaign
  integration with 24 tiny **development-only** attempts, replay and Qt6 captures.
- `tournament-regression.log`: nine existing tournament tests pass. Its deliberate
  compiler-error fixture confirms failed builds are rejected rather than published.

Fixtures and smoke games are infrastructure checks, not strength evidence. Both
official validation partitions remained unplayed during this qualification.
Subsequent predeclared cycles 112 and 113 used generator-holdout B offsets 0–31
and 32–63 respectively. Their separate evidence and the
[usage ledger](VALIDATION-USAGE.json) describe that consumption; it is not part
of the plumbing checks. No production corpus, stored
army, generator family or immutable v1 source snapshot was edited or regenerated.
Only temporary unit fixtures were generated. The explicit opponent-only role is
an evaluation capability, not a new AI policy or a promotion result.

The Qt6 companion now labels opponent-only suites as policy-owned armies versus
frozen opponent armies. Its board graphics, colors and orientation are unchanged.
`qt-build.log` and `qt-test.log` retain the successful desktop rebuild and native
tournament CTest check (1/1 passed).
