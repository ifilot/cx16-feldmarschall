# Frozen comparison opponent

`ai_v020.c` is the exact pre-upgrade `src/core/ai.c`, preserved for repeatable
comparisons. Do not update it when changing the current AI. `make
native-baseline` compiles it against the same native protocol and rules as the
current engine; `make benchmark-ai` compares the two with side-swapped pairs.

`ai_planned.c` freezes the stronger planned evaluator before speed work and
difficulty levels. `make compare-ai` compares complete games against it,
including persistent goals and histories; `make bridge-planned` builds its
X16 mailbox program for measurements on the same positions.
