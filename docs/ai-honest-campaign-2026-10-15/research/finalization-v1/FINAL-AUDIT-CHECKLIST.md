# Final audit checklist — pending final reconciliation

This is a checklist, not a completion claim. Root must fill the terminal counts,
commit references, remaining work and clock evidence after all launched work is
settled. Evidence commands below are for finalization; they have not all been run
by this document's author.

The [original campaign objective](../../README.md) sets an eight-hour interval:
**2026-10-15 20:44:38 UTC through 2026-10-16 04:44:38 UTC**. Record both the
deadline check and the actual final audit time; if any launched fixed sample is
still running at the deadline, report that explicitly and finish its audit rather
than calling the campaign complete or silently truncating it.

| Requirement | Evidence / final action | Terminal state |
| --- | --- | --- |
| Eight-hour work interval | Record clock timestamp and elapsed time against the UTC interval above. Distinguish research cutoff from later completion of already-launched fixed samples. | Pending root entry |
| Three assisting agents | Preserve task/turn evidence and concrete contributions from `campaign_search`, `campaign_sampling`, and `campaign_strategy`; list representative committed research, independent reviews and cycle handoffs. Agent count alone does not establish useful work. | Pending root reconciliation |
| Classic research direction | Check every launched plan's rules/referee, distinct strategic hypothesis and public-information contract. Optional-rule strength research requires explicit user authorization. | Pending final audit |
| Honest candidate inputs | Own full army is legitimate; enemy data must come from public movement, disclosure, captures/counts or a frozen population model. No actual enemy setup, private setup seed or concealed referee rank enters decisions. Offline truth labels must remain separate. | Pending final source/recipe review |
| Cheap, distinct mechanisms | Link rationale, expected behavior, mechanism tests, comparison and plain-language conclusion. Distinguish predictive/component evidence, tactical material certificates, desktop strength and target engineering. Do not present repeated score tweaks or rare opportunities as established gains. | Pending overview reconciliation |
| Immutable preregistration | Each selectable ID pins version, source archive, build recipe, model, difficulty and public contract before its first saved match. Keep registration timestamps and frozen metadata; retain corrected/rejected preflights under their original identities. | Pending final artifact audit |
| Completed fixed samples | Every launched arm has exactly the prespecified attempt count, retained errors, complete reports, replay receipts and terminal audit. No favorable partial sample, dropped failure or replacement seed. List registrations with zero games separately. | Pending: record all running/saved cohorts |
| Classic Qt6 review artifacts | Preserve `.fmtour`, every-state Python/native replay verification and Qt6 `.png` capture per arm, with frozen referee/worker provenance. Preserve artwork, colors and orientation. | Pending final artifact audit |
| Setup population/orientation | Separate seven-family stress tests from original-DOS template/procedural generation; referee-fixed, policy-owned and rotated modes are distinct. Verify own-setup and original-generator transcripts where applicable. Retain move-RNG reseeding boundary. | Pending final artifact audit |
| Statistics and failures | Check score = wins + half draws, paired denominators, planned confidence family, missing-score bounds and failure attribution. Confidence intervals and finite missing-outcome bounds answer different questions. Inconclusive comparisons do not establish equivalence. | Pending independent aggregate review |
| Fresh validation | Validation uses unchanged frozen policies and prespecified fresh seeds. No validation-trajectory tuning. Screening, same-cohort expansions, shared prospective controls and independent validation remain explicitly distinguished. | Pending final conclusion review |
| Shared-control accounting | Check declared source/copy equality, registration/prospective epoch, complete metadata and full-game hash binding. Count comparison appearances separately from unique physical attempts/errors. A shared control is not an independent replication. | Pending final accounting |
| Preservation and commits | Preserve accepted/rejected/deferred hypotheses, original failures and corrections; bind final conclusions/logs/artifacts in manifests. Record a commit for each completed cycle and update cumulative overview to the same audited terminal state. | Pending root commit inventory |
| Production/target claims | Separate frozen desktop policies from default-off Q24/cache prototypes; report actual target recipe, memory fit and whole-turn cost limitations. No production promotion or AI ceiling claim without its separate evidence. | Pending final narrative review |

## Evidence commands and paths

From repository root, the retained-receipt accounting audit is:

```sh
python3 tools/audit_honest_campaign.py --require-settled-matches --output /tmp/honest-campaign-final-audit.json
```

This does not run new games. The strict flag rejects saved cohorts still missing
completed audited results. Preserve its final output under this directory after
root checks it; report completed cycles, comparison appearances, unique physical
attempts/errors, pending registrations and preflight rejections separately.

For a completed cycle, its owner runs the reproducible cycle audit before sealing
its manifest:

```sh
python3 tools/campaign_cycle.py audit --directory docs/ai-honest-campaign-2026-10-15/CYCLE-DIRECTORY
```

That command can rebuild runtimes and write audit evidence; coordinate ownership.
Independent reviewers should read final `plan.json`, `frozen-policies.json`,
`registration.json`, `result.json`, `error-sensitivity.json`, `audit.json`,
`CONCLUSION.md`, reports and manifest without inspecting validation trajectories.
Manifest formats include both flat SHA values and `{bytes, sha256}` entries;
verify the actual schema, exclude the manifest's own hash, and check every entry.

Use `git log --oneline -- docs/ai-honest-campaign-2026-10-15` and
`git status --short` for root's final commit/working-tree reconciliation. Check
[OVERVIEW.md](../../OVERVIEW.md) against all final result files and conclusions;
do not rank percentages across incompatible setup/opponent populations.
[HONEST-NEXT-STEPS.md](../../HONEST-NEXT-STEPS.md) separates confirmed progress
from proposals. [The error-actor diagnostic](../terminal-error-actors-v1/README.md)
documents C41/C42 DOS-side failures using frozen worker source and metadata only;
it does not identify the underlying cause of illegal returns.

## C39 audit preflight

[C39](../../cycle-39-quiet-contact-dos-screen/plan.json) prespecifies three arms,
1,000 attempts per arm / 500 paired rounds, seed `2490001`, original-DOS armies,
Classic, policy-owned rotated setups and a 1,000-ply limit. Its three contrasts
are occupancy minus baseline, mobile minus occupancy, and mobile minus baseline;
**98.3333% intervals** are the planned three-contrast family qualification.
The occupancy arm isolates mobile occupancy mass; the mobile arm additionally
uses per-piece conditional mobile capabilities. They retain MAX contact
aggregation and unchanged capture scores. The quiet correction is a score
component bridge, not full nonlinear reevaluation or a safety proof.

Before release, confirm all 3,000 attempts and three reports/captures, portable
scope qualification, exact frozen runtime rebuilds, actual-history/one-search
checks, own/original setup audits, all retained errors, finite sensitivity bounds,
aggregate/conclusion agreement and final manifest. At checklist creation, C39's
final result/audit was still pending; no outcome is inferred here.

## Root's final entries

- Deadline check (UTC), elapsed time, and any later audit completion: **pending**.
- Completed cycles / unique executed games / comparison appearances / errors: **pending**.
- Running or saved-but-unaudited cohorts and explicit disposition: **pending**.
- Three-agent contribution references and independent review clearances: **pending**.
- Per-cycle commits, overview commit, final manifest/audit hashes: **pending**.
- Confirmed findings, rejected/deferred ideas and remaining limitations: **pending**.

Until these entries and the strict settled-match audit are complete, the overall
campaign remains pending final reconciliation.
