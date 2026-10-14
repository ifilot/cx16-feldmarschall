# Mission diagnostics and isolated strategy experiments

14 October 2026

The focused evaluation set contains 18 positions from distinct games: nine Normal and nine Hard, covering all seven broad layout families. It supplies permitted views, public histories, legal alternatives and two controls with permanent direct flag-route obstruction. Seven isolated policy versions were tested in 3,920 fresh development games; none earned promotion. Production retains the validated mission policy and varied deployments.

## Information and interpretation

Cases contain the AI's legitimate own ranks and initial setup, its masked view, disclosed casualties, repetition state and public events. Analysis reads these permitted fields only. Source identities and selection categories are diagnostic metadata, never teacher or student features. In particular, the decoy category was selected retrospectively using referee labels; the AI is not expected to recognize a concealed flag's actual location.

Alternative moves are legal hypotheses with public reasons, not best-move labels. A route calculation removes mobile blockers and treats concealed ranks optimistically. A route can therefore exist without a safe or winning continuation. For permanence checks, opposing Miners are allowed to remove our bombs. The two blockage controls still cannot reach any public flag candidate through permanent Classic barriers. This proves direct flag-route obstruction, not an inevitable game result; winning by immobilizing the opponent is a separate question.

The evaluation replays public histories and consumes each policy's decisions, then forces the recorded actions. A diagnostic acknowledgment corrects goal transfers and backtracking to the actions actually executed. Board views, disclosed inventories and two-square state match every selected root. These are forced-history comparisons, not exact historical policy replays or outcome counterfactuals. Early reports that retained proposal caches are preserved separately; the final reports use executed-action caches.

## Cases and useful alternatives

In the boards below, O identifies the AI's own army, E the opposing army, ? a concealed enemy rank, ## a lake and .. an empty square. Rank glyphs use Classic numbering. Each alternative states its purpose and any disclosed risk; concealed reply risk and flag defence still need tactical analysis.

### Case 1e4cbbffa46c3aaa5156

Normal as Blue; stationary blockage control; historical move e3 to f3.

Control for direct flag-route obstruction; legal quiet moves cannot by themselves remove the permanent barriers.

Public flag candidates: a1. Distinct last 40 own moves: 12. Permanent direct flag-route blockage: yes.

- e3 to e2: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- e3 to e4: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- e3 to d3: redirect the same specialist or actor; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  .. .. .. .. .. .. .. .. OB OF
 9  .. .. .. .. .. .. .. .. .. OB
 8  .. .. .. .. E1 .. .. .. OB ..
 7  .. .. .. .. .. E8 .. .. .. ..
 6  .. .. ## ## OS .. ## ## .. ..
 5  .. .. ## ## .. E4 ## ## .. ..
 4  .. .. .. .. .. E? .. .. .. EB
 3  .. .. .. .. O4 .. .. .. .. ..
 2  EB .. .. EB .. O1 .. .. .. EB
 1  E? EB .. .. EB .. .. .. .. ..
```

### Case 3cf28491e8c9bf1a53c1

Normal as Red; stationary blockage control; historical move d3 to c3.

Control for direct flag-route obstruction; legal quiet moves cannot by themselves remove the permanent barriers.

Public flag candidates: d10. Distinct last 40 own moves: 12. Permanent direct flag-route blockage: yes.

- d3 to d4: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- d3 to d2: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- d3 to e3: redirect the same specialist or actor; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  O5 .. EB E? EB .. .. EB .. O4
 9  .. EB .. EB .. .. .. EB .. ..
 8  .. O6 .. O3 .. .. .. .. .. O6
 7  .. .. .. .. .. .. .. .. .. ..
 6  .. .. ## ## O4 .. ## ## .. ..
 5  .. .. ## ## O6 .. ## ## .. ..
 4  .. O3 .. .. .. .. .. .. .. ..
 3  .. .. .. O2 .. .. .. .. .. ..
 2  E? .. .. .. .. OB .. OB .. ..
 1  .. .. .. OB .. OB OF O7 OB ..
```

### Case 3939484e0d87cfb07f6b

Hard as Blue; rear guard decoy; historical move e3 to e2.

Compare continuing to mine a rear guard with investigating another lane. A known bomb is useful route evidence only under an explicit hypothesis about what it protects.

Public flag candidates: j3, d1, e1, j1. Distinct last 40 own moves: 33. Permanent direct flag-route blockage: no.

- e3 to f3: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- e3 to e4: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- h2 to j2: avoid repeating one of the last 40 own moves; investigate a concealed defender.

```text
    a  b  c  d  e  f  g  h  i  j
10  OB .. .. .. .. .. OB O6 OB ..
 9  .. .. .. .. .. .. .. OB O5 O5
 8  OF O4 .. .. .. E9 OB .. OB O9
 7  O7 O6 O8 .. .. .. .. .. O8 ..
 6  O1 O9 ## ## .. .. ## ## .. E4
 5  .. O3 ## ## .. .. ## ## E? E?
 4  .. .. E? .. .. .. E? .. E? ..
 3  .. .. E1 .. O8 .. E? .. .. E?
 2  .. .. .. E? EB .. .. O9 .. E?
 1  .. .. .. E? E? EB .. .. .. E?
```

### Case 7ea6ea8294493d79c3b0

Hard as Blue; rear guard decoy; historical move i3 to i2.

Compare continuing to mine a rear guard with investigating another lane. A known bomb is useful route evidence only under an explicit hypothesis about what it protects.

Public flag candidates: c4, d4, d2, g2, a1, f1, g1, h1. Distinct last 40 own moves: 24. Permanent direct flag-route blockage: no.

- i3 to j3: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- i3 to i4: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- a10 to d10: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  O9 .. .. .. OB O5 OB .. .. ..
 9  O6 O4 O6 O5 O9 OB OB .. .. ..
 8  O9 O5 O4 O4 OB .. .. .. .. ..
 7  O3 O8 OF O1 OB O8 O8 .. .. ..
 6  O7 .. ## ## E? .. ## ## .. O2
 5  .. E5 ## ## E? E6 ## ## .. OS
 4  E? E? E? E? E9 E5 E? E9 .. ..
 3  E? E? E? E? E? E? E? .. O8 ..
 2  .. .. .. E? E? .. E? E5 EB ..
 1  E? .. .. .. .. E? E? E? .. E?
```

### Case 0098726d54c2d21be9c2

Normal as Blue; rear guard decoy; historical move d2 to d1.

Compare continuing to mine a rear guard with investigating another lane. A known bomb is useful route evidence only under an explicit hypothesis about what it protects.

Public flag candidates: h4, f3, h3, f2, h2, j2, f1, i1, j1. Distinct last 40 own moves: 25. Permanent direct flag-route blockage: no.

- d2 to c2: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- d2 to e2: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- d2 to d3: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  .. .. .. OF O9 O7 O4 O9 O6 O4
 9  .. .. .. .. .. O9 O7 O7 OB O5
 8  O8 .. O8 O3 O5 O9 O6 O1 OB O6
 7  .. .. OB OB OS OB O9 O8 O8 OB
 6  .. .. ## ## E? E? ## ## E? E?
 5  .. .. ## ## E? E? ## ## E? E?
 4  .. O4 .. .. .. E? E? E? E9 ..
 3  .. O5 O7 .. E9 E? E? E? .. ..
 2  .. .. .. O8 .. E? E? E? .. E?
 1  .. .. .. EB .. E? .. .. E? E?
```

### Case 0991d1c02757b784eaa3

Normal as Blue; rear guard decoy; historical move i1 to h1.

Compare continuing to mine a rear guard with investigating another lane. A known bomb is useful route evidence only under an explicit hypothesis about what it protects.

Public flag candidates: b3, a2, b2, a1, b1, d1. Distinct last 40 own moves: 11. Permanent direct flag-route blockage: no.

- i1 to j1: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- g9 to g8: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- b8 to b7: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  O6 OB O7 OF OB .. .. E8 .. ..
 9  O4 O8 OB .. OB .. O6 .. .. ..
 8  O3 OS .. .. .. .. .. .. .. ..
 7  O1 .. O4 .. .. .. .. .. .. ..
 6  .. E? ## ## O6 E4 ## ## .. ..
 5  E? .. ## ## .. .. ## ## .. ..
 4  .. .. .. .. E? .. .. E? .. ..
 3  .. E? .. E? .. E? E? .. E6 ..
 2  E? E? E? .. .. E? .. .. .. ..
 1  E? E? .. E? .. .. .. EB O8 ..
```

### Case 0f3c7933a57838f33c60

Hard as Red; quiet repetition; historical move f4 to e4.

Compare the recurring move with a different legal advance or investigation. Novelty alone is not evidence of safety or progress.

Public flag candidates: e10, f10, g10, j10, i9, a8, c8, a7, c7, d7. Distinct last 40 own moves: 4. Permanent direct flag-route blockage: no.

- f4 to g4: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- f4 to f3: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- a5 to a6: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  .. .. .. .. E? E? E? .. .. E?
 9  .. E? E? E? .. EB .. .. E? ..
 8  E? E? E? E? .. .. E? .. .. ..
 7  E? E? E? E? E? E? E? .. .. E9
 6  .. .. ## ## E6 .. ## ## E? E9
 5  O8 O5 ## ## .. O7 ## ## E? E?
 4  OS O1 O9 O8 .. O4 .. O4 .. E?
 3  OF O9 O5 OB .. .. .. .. E6 ..
 2  O4 .. O7 O6 .. OB .. O5 OB OB
 1  .. .. O7 O6 OB O8 OB O9 O2 O9
```

### Case 90050a5d0eb6b0df3820

Hard as Red; quiet repetition; historical move j4 to f4.

Compare the recurring move with a different legal advance or investigation. Novelty alone is not evidence of safety or progress.

Public flag candidates: f10, g10, h10, i10, f9, h9, e7. Distinct last 40 own moves: 12. Permanent direct flag-route blockage: no.

- j4 to j6: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- j4 to j5: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- j4 to h4: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  .. .. .. .. EB E? E? E? E? ..
 9  .. .. .. .. .. E? .. E? .. ..
 8  .. .. .. .. .. .. .. .. .. ..
 7  .. E9 .. .. E? E? E4 E? .. O4
 6  E? .. ## ## .. E? ## ## .. ..
 5  .. O5 ## ## O7 .. ## ## O4 ..
 4  .. .. .. .. OB .. .. .. .. O9
 3  .. .. .. .. .. O5 .. OF .. ..
 2  E? E9 OB .. OB O6 .. O8 OB ..
 1  E9 E9 E1 OB O9 OB O7 O8 .. O8
```

### Case 0474eb39a879dab456e0

Normal as Blue; quiet repetition; historical move f8 to b8.

Compare the recurring move with a different legal advance or investigation. Novelty alone is not evidence of safety or progress.

Public flag candidates: i4, f3, h3, e2, j2, h1. Distinct last 40 own moves: 12. Permanent direct flag-route blockage: no.

- f8 to f6: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; investigate a concealed defender.
- f8 to f7: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- f8 to c8: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  E? .. .. O8 OB .. .. .. .. OB
 9  .. O2 O7 .. .. .. O7 .. .. ..
 8  OB .. .. .. .. O9 O3 OB OF O8
 7  .. .. OB OB O6 .. O6 OS O5 O7
 6  .. .. ## ## .. E? ## ## .. O4
 5  .. O4 ## ## E5 E? ## ## E3 ..
 4  .. .. EB E? E? E? E? E? E? E?
 3  O7 .. E? E? .. E? E? E? E? E?
 2  .. .. .. .. E? .. .. E? E? E?
 1  .. .. .. .. .. EB E? E? .. ..
```

### Case 0886fae9245ce2dfcf93

Normal as Red; quiet repetition; historical move f2 to f3.

Compare the recurring move with a different legal advance or investigation. Novelty alone is not evidence of safety or progress.

Public flag candidates: c10, d9. Distinct last 40 own moves: 4. Permanent direct flag-route blockage: no.

- f2 to e2: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- d2 to d3: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- a6 to b6: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  .. .. E? .. .. .. .. .. .. ..
 9  .. .. .. E? .. .. EB .. .. ..
 8  .. .. .. .. .. E? .. .. E1 ..
 7  EB E? E? E? E? .. E? EB .. E?
 6  O5 .. ## ## E9 E? ## ## O5 ..
 5  O6 .. ## ## E6 E8 ## ## .. ..
 4  .. E2 .. O7 OB .. O4 .. .. ..
 3  .. .. O8 .. .. .. .. OB .. ..
 2  .. .. .. O1 .. O7 OB .. .. ..
 1  .. .. OF O6 .. O7 OB OB .. ..
```

### Case 7144e4f3a39b735acc97

Hard as Blue; ineffective miner approach; historical move b9 to c9.

Review whether the Miner has a useful next job, needs support, or should be redirected. Preserve access to remaining bomb-clearing jobs.

Public flag candidates: c4, d4, g4, b3, j3, e2, d1, e1, f1, j1. Distinct last 40 own moves: 20. Permanent direct flag-route blockage: no.

- b9 to a9: redirect the same specialist or actor; keep the piece instead of this turn's capture attempt.
- b9 to b10: redirect the same specialist or actor; keep the piece instead of this turn's capture attempt.
- d9 to d10: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  OB .. .. .. .. .. OB O6 OB ..
 9  .. O8 .. O9 .. O4 OS OB O5 O5
 8  OF O3 O9 O4 O7 O1 OB O9 OB O9
 7  O2 O9 O6 O8 O9 O9 O4 O3 O8 ..
 6  O8 O8 ## ## .. O5 ## ## .. E4
 5  .. O5 ## ## E2 .. ## ## E? E?
 4  E3 EB E? E? E? E? E? E? E5 E?
 3  E? E? E? E? E? E? E? E? E? E?
 2  E? E? E9 E? E? E? .. .. E? E?
 1  .. .. .. E? E? E? .. .. .. E?
```

### Case 7e7c6c55df8c4e30c598

Hard as Blue; ineffective miner approach; historical move b8 to c8.

Review whether the Miner has a useful next job, needs support, or should be redirected. Preserve access to remaining bomb-clearing jobs.

Public flag candidates: b4, c4, d4, g4, h4, e3, b2, a1, b1, c1. Distinct last 40 own moves: 24. Permanent direct flag-route blockage: no.

- b8 to b9: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- c9 to c8: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- b6 to b5: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  OB .. .. .. .. OB O4 OB .. ..
 9  OB .. O2 .. O8 .. OB .. .. ..
 8  OS O8 .. O9 O6 O5 O1 O7 O5 OF
 7  OB O3 O9 O3 O6 O9 O9 O4 O7 O5
 6  .. O8 ## ## .. O7 ## ## .. O8
 5  E? .. ## ## E3 .. ## ## E2 ..
 4  E? E? E? E? EB E8 E? E? E? E?
 3  E? E? E? E? E? E? E? E9 E? E?
 2  .. E? E? .. E? .. E? .. .. ..
 1  E? E? E? .. .. .. .. .. E? ..
```

### Case 21792bb126a13a828843

Hard as Red; ineffective miner approach; historical move b4 to b3.

Review whether the Miner has a useful next job, needs support, or should be redirected. Preserve access to remaining bomb-clearing jobs.

Public flag candidates: c10, i10, h9, f8, g7, h7, j7. Distinct last 40 own moves: 24. Permanent direct flag-route blockage: no.

- a5 to a6: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- e5 to e6: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- i5 to i6: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  .. .. E? .. .. .. .. .. E? ..
 9  E? .. .. .. .. .. .. E? .. E?
 8  EB E9 E? E? E? E? E? E? .. E?
 7  E? E3 E? E? E? E5 E? E? E? E?
 6  .. .. ## ## .. E? ## ## .. E?
 5  O6 O6 ## ## O4 .. ## ## O1 ..
 4  O8 O8 OB O8 O3 O5 O4 O8 O5 OB
 3  O9 .. .. O4 O9 O9 OS O3 O5 O6
 2  .. .. .. .. OB .. .. .. .. OB
 1  .. OB OF .. .. .. .. .. OB O9
```

### Case 2cc8fbe45d39505511ef

Hard as Blue; ineffective miner approach; historical move h10 to i10.

Review whether the Miner has a useful next job, needs support, or should be redirected. Preserve access to remaining bomb-clearing jobs.

Public flag candidates: c4, d4, g4, h4, a3, b3, c3, d3, g3, f1, i1. Distinct last 40 own moves: 12. Permanent direct flag-route blockage: no.

- h10 to g10: redirect the same specialist or actor; keep the piece instead of this turn's capture attempt.
- f6 to f5: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- h9 to g9: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  .. .. .. OB O7 OF .. O8 .. ..
 9  .. OB .. OB OB O3 .. O4 O6 O9
 8  O8 O7 O6 O4 OS O4 O5 O5 O7 O3
 7  O7 O9 O8 O9 O5 O8 O9 OB O8 OB
 6  O9 O5 ## ## .. O1 ## ## .. ..
 5  O9 O2 ## ## E3 .. ## ## E6 E?
 4  EB EB E? E? E? E? E? E? E? E?
 3  E? E? E? E? E? E? E? E? E? E?
 2  E? E? E? E? E? E? E? E? E? E?
 1  E? .. E? .. E? E? E? .. E? ..
```

### Case 30fa875d74699f2dc18b

Normal as Blue; disclosed specialist loss; historical move e7 to e6.

Compare a disclosed losing Scout attack with another action. A Scout may remain exposed after waiting; avoid assuming every sacrifice is unnecessary.

Public flag candidates: g4, a3, f2, d1, e1, f1, g1. Distinct last 40 own moves: 31. Permanent direct flag-route blockage: no.

- e9 to d9: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- e9 to f9: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- b8 to a8: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  O9 OB .. .. .. OB O6 OB .. ..
 9  OB .. .. .. O6 .. OB .. .. OB
 8  .. O1 O8 OF O9 O4 .. .. O8 ..
 7  O3 O5 O7 O9 O9 O5 O5 .. .. O8
 6  O5 .. ## ## E3 .. ## ## E3 ..
 5  .. E1 ## ## .. .. ## ## .. E2
 4  E6 E? E9 EB E? E? E? E? .. ..
 3  E? .. E5 E? E? E? .. .. .. E9
 2  .. .. .. E? .. E? .. .. .. ..
 1  .. .. .. E? E? E? E? .. .. ..
```

### Case 3fb869f69b31dc24f363

Normal as Blue; disclosed specialist loss; historical move f9 to f6.

Compare a disclosed losing Scout attack with another action. A Scout may remain exposed after waiting; avoid assuming every sacrifice is unnecessary.

Public flag candidates: d4, a3, d3, i3, a2, d1, e1, f1, j1. Distinct last 40 own moves: 24. Permanent direct flag-route blockage: no.

- f9 to f8: redirect the same specialist or actor; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- f9 to f7: redirect the same specialist or actor; avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt; disclosed immediate recapture threats remain at f6.
- g10 to h10: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  O7 O5 O1 OB O8 OB O8 .. .. ..
 9  O7 O4 O9 O9 OB O9 OB O6 O5 O4
 8  OF O3 O9 OS O6 .. O5 O9 O6 O7
 7  .. .. O8 OB O5 .. .. O8 .. OB
 6  E4 E1 ## ## .. E3 ## ## E2 ..
 5  E? E? ## ## E? .. ## ## E? E?
 4  .. E? E? E? E? .. E? E? E? E?
 3  E? E? E? E? E9 .. .. .. E? E?
 2  E? .. E? .. EB .. .. .. .. ..
 1  .. .. .. E? E? E? .. .. .. E?
```

### Case 06f5dcf6b19bc1231069

Normal as Blue; disclosed specialist loss; historical move e8 to e6.

Compare a disclosed losing Scout attack with another action. A Scout may remain exposed after waiting; avoid assuming every sacrifice is unnecessary.

Public flag candidates: c4, g4, h4, c3, e3, g3, h3, j3, c2, e2, g2, h2, i2, j2, a1, c1, e1, g1, h1, i1, j1. Distinct last 40 own moves: 24. Permanent direct flag-route blockage: no.

- d10 to e10: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- g10 to f10: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.
- i9 to j9: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  OB O4 O1 O5 .. .. O2 O3 OF ..
 9  OB O3 O9 OB O5 O8 O5 O6 O6 ..
 8  .. OB O4 O8 O9 O9 O8 O8 O8 ..
 7  OS .. O9 O7 .. OB O6 O4 OB O7
 6  .. E2 ## ## E1 E? ## ## .. O5
 5  E7 E9 ## ## E? E? ## ## E3 ..
 4  E? .. E? E? .. .. E? E? .. EB
 3  E? .. E? .. E? E? E? E? .. E?
 2  .. E? E? E? E? E? E? E? E? E?
 1  E? .. E? .. E? .. E? E? E? E?
```

### Case 174c2ee5d1b237385032

Hard as Blue; disclosed specialist loss; historical move a6 to a5.

Compare a disclosed losing Scout attack with another action. A Scout may remain exposed after waiting; avoid assuming every sacrifice is unnecessary.

Public flag candidates: c4, d4, e4, f4, g4, h4, a3, c3, d3, e3, f3, g3, h3, a2, d2, e2, f2, g2, a1, e1, f1, g1, h1, j1. Distinct last 40 own moves: 26. Permanent direct flag-route blockage: no.

- b6 to b5: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- e6 to e5: avoid repeating one of the last 40 own moves; advance toward opposing deployment rows; keep the piece instead of this turn's capture attempt.
- a10 to b10: avoid repeating one of the last 40 own moves; keep the piece instead of this turn's capture attempt.

```text
    a  b  c  d  e  f  g  h  i  j
10  O3 .. OB O9 .. O9 O9 OB .. ..
 9  OB O7 O2 O7 O9 O9 O5 OB O7 O5
 8  .. O8 O4 O6 O1 O9 O4 O8 O6 O3
 7  .. OB O8 O9 O7 OB O6 OF O8 OS
 6  O9 O4 ## ## O8 .. ## ## .. O6
 5  E9 .. ## ## .. .. ## ## E? ..
 4  EB E? E? E? E? E? E? E? E1 E?
 3  E? E? E? E? E? E? E? E? E? E?
 2  E? .. E? E? E? E? E? .. E? ..
 1  E? .. .. E? E? E? E? E? .. E?
```

## Isolated development results

Each version played 280 games on each level against the frozen mission baseline, with all seven layout families and swapped sides. Scores are development results. Promotion requires both useful diagnostic behavior and a reliable independent strength gain; the tested versions did not pass that gate.

| Experiment | Normal score and paired 95% interval | Hard score and paired 95% interval |
| --- | --- | --- |
| Goal-based progress decay | 50.0% (50.0 to 50.0) | 50.2% (48.9 to 51.4) |
| Job-based progress decay | 50.0% (50.0 to 50.0) | 50.4% (50.0 to 51.1) |
| Adjacent flag-candidate evidence | 50.0% (47.9 to 52.1) | 48.0% (45.7 to 50.2) |
| Last-Miner preservation | 49.3% (47.1 to 51.4) | 48.9% (47.1 to 50.7) |
| Disclosed threat escort | 50.4% (50.0 to 51.1) | 50.4% (49.3 to 51.8) |
| Scarce-Scout preservation | 50.4% (49.3 to 51.8) | 48.9% (47.5 to 50.0) |
| Uncompensated Scout-loss penalty | 49.6% (48.2 to 51.1) | 49.6% (48.9 to 50.0) |

Goal-based decay tracks remaining route length and occupied corridor squares, removes persistence preference after 12 unchanged calls and suppresses the mission bonus after 24. Job-based decay prevents alternating between a guard and its adjacent suspected flag from resetting the same first-obstacle job. Counters reset on public material changes or actual route improvement and saturate at 255.

The evidence rule stops treating an isolated rear bomb as flag-fortification evidence when no adjacent public flag candidate remains. Miner preservation recruits another suitable attacker or investigator while the last Miner is needed for a disclosed bomb. Escort assigns an available winning attacker against a disclosed threat beside a bomb before committing the Miner. All remain opt-in experiments.

The scarce-Scout version applied a penalty only with two or fewer Scouts remaining. The broader Scout-loss version penalizes uncompensated losses against disclosed defenders while concealed ranks remain, leaving equal trades unchanged. It avoids three known losing Scout attacks in the final diagnostic set, choosing three curated alternatives, but scored 49.6% on both levels. This is a concrete diagnostic symptom reduction that failed the game-strength gate.

The final evidence experiment changes three roots, including one quiet-repetition case; no winning continuation is established by those substitutions. Job progress, Miner preservation and escort change none of these 18 roots. Useful controlled fixtures do not establish population-wide strength.

## Verification and retained evidence

All five current experimental build targets pass tactical, public-information and all-64-rule fairness tests. Job-progress snapshots cover both armies, corridor clearing, leader advancement, material changes, saturation and restoration, including compatibility with the opt-in tracker and sector-memory state. Address and undefined-behavior sanitizers pass the combined state test. An initial goal-progress snapshot reserved two unwritten bytes, causing state-comparison failures; the size was corrected before any strength run.

Production builds omit every new policy macro. Current production matches the frozen mission policy on 1,672 Normal and 1,809 Hard decisions across six games each. The native diagnostic commands and their goal-history acknowledgment are also excluded from production.

`cases.jsonl` and `manifest.json` retain the fixed evaluation set and generator identities. The evidence ZIP contains the generator, validator, evaluation script, native programs, final diagnostic reports, earlier diagnostic reports, current sources and check logs. Fourteen benchmark archives retain full source/program snapshots, deployments, seeds, moves, results and explicit rejection decisions in the experiment ledger.

## Reproduction

```sh
make test-ai-mission-cases test-ai-diagnostic-history
make native-mission-diagnostics native-mission-progress native-mission-evidence native-mission-preserve native-mission-escort native-mission-scout-value
make test-ai-mission-progress test-ai-mission-evidence test-ai-mission-preserve test-ai-mission-escort test-ai-mission-scout-value
python3 tools/evaluate_ai_mission_cases.py docs/ai-mission-cases/cases.jsonl --candidate build/feldmarschall-engine-mission-progress --out NEW_DIAGNOSTIC_DIRECTORY
python3 tools/benchmark_ai.py --missions --suite broad --candidate-engine build/feldmarschall-engine-mission-progress --candidate-source src/core/ai_mission.c --strategy mission-job-progress --difficulty normal --rounds 20 --record-moves --seed-offset NEW_OFFSET --out NEW_RUN_DIRECTORY
python3 tools/verify_ai_archives.py
```

Use the archived sources/programs to reproduce earlier policy versions. Current `AI_MISSION_PROGRESS` is job-based and current `AI_MISSION_SCOUT_VALUE` is the uncompensated-loss version. Existing corpus and run directories are immutable; choose new output directories and fresh seeds.

## Remaining promotion gate and teacher work

The focused diagnostic set is complete. A further strategic policy with both diagnostic improvement and independently established game strength remains outstanding. No new mission policy was accepted, so none is awaiting X16 promotion. The next research stage is to evaluate the existing desktop teacher against the mission policy, compare an information-set-aware successor and cover quiet strategy, decoys and sparse endgames. A stronger teacher, a new independently evaluated student and optional-variant strength benchmarks are still required by the full cycle.
