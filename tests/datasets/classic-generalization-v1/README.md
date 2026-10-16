# Classic generalization setup suite v1

This frozen corpus tests whether an honest move policy transfers beyond the
1990 DOS formation patterns. It contains **1,920 paired records and 3,840
distinct armies**, with the full Classic inventory and initial legal moves for
both colors. Each record supplies a physical Red army A and Blue army B. Run
both policy assignments on those same armies and move seed.

| Partition | Families | Pairs per family | Armies | Purpose |
|---|---:|---:|---:|---|
| `development` | 6 | 64 | 768 | Explore ideas and tune |
| `seed-validation` | Same 6 | 128 | 1,536 | Fresh layouts from familiar generators |
| `generator-holdout` | 6 different | 128 | 1,536 | Transfer to unseen generator families |

Development families are uniform shuffles, rear Bomb shells, exposed rear
Flags, forward Flags, one decoy fortress, and scattered guards. The first five
reuse existing stress generators; scattered guards allows a Flag anywhere
with zero to two adjacent Bombs.

Held-out families are:

- `interior-shell-v1`: Flag in either middle deployment row; variable guards.
- `flank-flag-v1`: Flag in either two outer files, at any depth.
- `double-decoy-v1`: two mobile pieces enclosed by rear Bomb shells; Flag ahead.
- `front-fence-v1`: all six Bombs in the front row, with at least two exit lanes open.
- `mobile-squads-v1`: randomly placed Flag/Bombs with mobile ranks grouped along
  a randomized serpentine path.
- `lane-vanguard-v1`: four Scouts and two Miners on the six forward exit squares;
  Flag in the rear half, with variable guards.

These are deliberately different synthetic challenges, not a claim about the
distribution of human play. Some are weak deployments. Report each family
separately as well as the equally weighted aggregate. A corpus of deployments
does not replace testing against several different honest move policies.

All three partitions exclude exact copies and horizontal reflections of every
other stored army. Each army also differs in at least 12 of its 40 squares from
each reference DOS template and native preset, including their reflections.
This excludes near copies of those fixed references, not every historical
random setup. `coverage.json` records Flag depth, file, adjacent Bomb guards and
minimum reference distance for every family and partition.

`manifest.json` pins the literal input files, reference formations, generator
source and supporting source snapshots by SHA-256. Do not edit or regenerate
this version. A changed corpus or generator needs a new version ID and directory.
The builder refuses to overwrite a directory. The reproduction recipe is:

```sh
python3 tools/setup_dataset.py build /tmp/classic-generalization-reproduction \
  --id classic-generalization-v1 --seed 2026101601 \
  --development-pairs 64 --validation-pairs 128
python3 tools/setup_dataset.py verify tests/datasets/classic-generalization-v1
make test-setup-dataset
```

Exact reproduction requires the pinned sources and compatible Python random
implementation. Loading this corpus runs no generator: the saved armies are the
authoritative inputs. Its generation seed is independent of each tournament's
move seed; knowing the move seed cannot regenerate an enemy deployment.

Use the [Classic tournament instructions](../../../docs/tournament-desk.md)
to select a partition. The complete corpus and exact selected record IDs travel
inside each saved `.fmtour`; verification checks the actual armies, family,
move seed and policy assignment against that frozen schedule. Honest policies
receive their usual protocol observations, never the dataset or opponent setup.

Freeze immutable policy IDs and the comparison plan **before** either validation
partition. Use development only for debugging. Validation outcomes may be used
to accept or reject a previously specified hypothesis; if used to choose or tune
the next policy, those records become development evidence and a new final
holdout is required. Public files cannot enforce this separation. Changing only
the move seed does not create new deployment validation data.
