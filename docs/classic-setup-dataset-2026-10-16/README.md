# Classic setup generalization corpus: integration evidence

The [frozen v1 corpus](../../tests/datasets/classic-generalization-v1/README.md)
adds 3,840 distinct armies in 1,920 paired records. Development has 384 pairs;
fresh-layout validation and held-out-generator validation each have 768 pairs.
The partitions contain no duplicate or horizontally reflected army. Every army
has the legal Classic inventory, initial mobility for either color, and at least
12 changed squares relative to each fixed DOS template/native preset reference.

The hypothesis this enables is: **a strategic improvement should survive both
fresh deployments and a change of deployment generator, against multiple honest
opponent styles**. Compare with the frozen baseline on the same paired records
and move seeds. Inspect individual family results before interpreting an aggregate.
The corpus supplies evaluation inputs; it introduces no policy change.

The runner accepts `--dataset`, `--dataset-split` and `--dataset-offset`. It freezes
the complete corpus and selected record IDs into each tournament. The verifier
checks both legal replay and the exact planned armies, seed, family and policy
assignment. Qt6 identifies the dataset and partition while preserving the game's
artwork, colors and orientation. Existing tournament options and old saved files
continue to work.

The [saved development smoke](development-smoke.fmtour) uses existing immutable
IDs `student-guard-v1-normal` and `original-v1`, one paired record per development
family, seed 2026101607, four OpenMP workers and an 80-ply limit:

```sh
python3 tools/tournament.py run student-guard-v1-normal original-v1 \
  --dataset tests/datasets/classic-generalization-v1 \
  --dataset-split development --rounds 1 --seed 2026101607 \
  --max-plies 80 --backend openmp --jobs 4 \
  --out build/tournaments/setup-development-smoke.fmtour
```

All 12 smoke games completed without engine errors. Both policies scored 50%,
with eight move-limit draws; this short run supports **no strength conclusion**.
The Python verifier passed, and independent native replay matched every one of
666 positions. See the [summary](development-smoke-summary.json),
[verification](development-smoke-verification.json),
[native state audit](native-replay-verification.json) and
[Qt6 review](development-review.png) (match 1, ply 40, Red's view).

Checks passed on 16 October 2026:

- `python3 tools/test_setup_dataset.py`: six tests covering the full corpus,
  deterministic reproduction, generator constraints, partition separation,
  tampering, portable verification, and identical Python/OpenMP games.
- `python3 tools/test_tournaments.py`: nine existing tournament tests.
- `python3 tools/test_benchmark_setups.py`: two existing generator tests.
- `python3 tools/test_campaign_setup_store.py`: eight existing setup-store tests.
- `make desktop-build` and `QT_QPA_PLATFORM=offscreen ctest --test-dir build/desktop --output-on-failure`.
- `git diff --check`.

Neither validation partition was played for this integration. Inspecting legal
inventories and coverage does not evaluate candidate performance. Freeze the
next strategic hypothesis and policy IDs before using validation. If its layouts
or results guide later tuning, retire that cohort from final validation and
create a new version. These synthetic families broaden the test, but do not
establish coverage of all human strategies or an honest-AI ceiling.
