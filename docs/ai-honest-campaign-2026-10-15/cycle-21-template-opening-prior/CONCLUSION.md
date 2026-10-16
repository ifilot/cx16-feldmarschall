# Cycle 21: public formation recognition improves honest play

Recognizing plausible original DOS formations from public evidence substantially improved both the native policy and the teacher on this screening cohort. Native Flag/Bomb template beliefs scored 37.98%, compared with 14.86% for its counts-only control and 14.05% for its existing move policy. Template-sampled teacher worlds scored 26.11%, compared with 7.87% for uniform worlds and 9.17% for the original teacher. Both improved candidates remain below 50% against the DOS opponent.

The source-informed prior uses eight original Colonel templates with total mass 80%, plus a 20% uniform legal-army background. Public moves and disclosed ranks eliminate inconsistent formations and update the mixture. The background is an explicit approximation to the original procedural branch, rather than its exact distribution. Our policies see their own army and public events only; the original DOS opponent retains its registered information advantage. The native policy applies public Flag/Bomb marginals to persistent goals and capture expectations; the teacher samples correlated complete worlds. Merely replacing count conditioning or importance weights without the formation prior did not show a clear gain.

Each of six arms attempted 400 Classic games on 200 matched pairs against original machine-code-generated DOS armies. All arms use the already-existing CX16 validated own deployment mixture; selecting that mixture through the native protocol repairs the previous benchmark setup mismatch. Both sides rotate 180 degrees, preserving the exact original DOS-local army. Private setup seeds and enemy armies are withheld from honest policies and matched across arms.

| Policy | W / D / L | Unscored errors | Score |
|---|---:|---:|---:|
| student-validated-deployment-v1-normal | 40 / 24 / 306 | 30 | 14.05% |
| student-validated-counts-v1-normal | 40 / 30 / 300 | 30 | 14.86% |
| student-template-flag-bomb-v1-normal | 110 / 74 / 203 | 13 | 37.98% |
| teacher-validated-deployment-v1-normal | 27 / 12 / 321 | 40 | 9.17% |
| teacher-validated-uniform-v1-normal | 22 / 13 / 327 | 38 | 7.87% |
| teacher-template-opening-v1-normal | 75 / 50 / 258 | 17 | 26.11% |

The preregistered contrasts use complete matched pairs and a paired bootstrap. Intervals are percentage points. The 95% intervals are exploratory; the retained 98.3333% intervals do not control multiplicity across all six contrasts. No familywise strength claim is made. Fresh-seed C26 single-contrast validation is queued; screening and campaign selection still require independent validation.

| Contrast | Complete pairs | Effect | 95% interval | 98.3333% interval |
|---|---:|---:|---:|---:|
| Native template minus Native counts | 164 | +23.93 | [+17.68, +30.18] | [+16.31, +31.55] |
| Native counts minus Native original | 165 | +0.76 | [-2.42, +3.94] | [-3.03, +4.70] |
| Native template minus Native original | 161 | +23.60 | [+18.01, +29.19] | [+16.77, +30.28] |
| Teacher template minus Teacher uniform | 159 | +18.24 | [+12.89, +23.58] | [+11.95, +24.69] |
| Teacher uniform minus Teacher original | 153 | -0.49 | [-3.59, +2.61] | [-4.25, +3.27] |
| Teacher template minus Teacher original | 156 | +16.99 | [+11.38, +22.44] | [+10.26, +23.56] |

All 168 error-game prefixes remain preserved and unscored in official standings. Assigning each missing outcome any score in [0,1] gives finite-cohort effect bounds of [+15.50, +26.25] points for native template minus counts and [+8.38, +22.13] for teacher template minus uniform. These are missing-outcome bounds, not confidence intervals. Complete-pair direction diagnostics also favor template beliefs: native 90 positive/23 negative/51 tied (exact two-sided sign p=1.49e-10), teacher 78/16/65 (p=5.78e-11). They concern directions rather than a mean-effect null, and are unadjusted across the campaign. All contrasts and their error bounds are retained in result.json and error-sensitivity.json.

Recorded batch execution was 273.95 seconds for the original native policy, 269.76 for counts, 305.09 for native templates, 395.10 for the original teacher, 510.47 for uniform teacher worlds and 668.47 for template teacher worlds. Native templates used about 13% more batch wall time than counts; teacher templates about 31% more than uniform worlds. These are total-run timings affected by game lengths and load, not controlled per-decision benchmarks.

This is desktop evidence. A full CX16 link with the native belief-prior interface overflows the AI bank by 1,198 bytes: approximately 820 extra code bytes and 423 extra BSS bytes against 45 bytes of existing free space. The native prototype therefore still needs memory/layout engineering before a target port. The full driver also maintains its public belief model in Python. The target-fit evidence is preserved under ../research/native-belief-target-fit/. No desktop strength result establishes target readiness.

The original deployment generator includes its unchanged template and procedural branches at level3. Original asset/runtime hashes and private setup requests are frozen and reproduced by independent audits. The DOS move adapter separately reseeds move RNG rather than continuing the original interactive game’s post-deployment state; this boundary remains explicit. The evidence concerns this opponent and deployment distribution, and the approximate background prior may generalize poorly to other formations. The selected source prior is honest knowledge of the opponent’s algorithm, not observation of its actual hidden army.

All 2,400 games receive Python and native every-state replay and Qt captures; frozen owner and original generator setup audits and exact registered runtime rebuilds are retained. No production policy, source snapshot, model or registered ID is changed. No promotion follows this screening result. Fresh-seed original-DOS validation and honest-opponent generality tests are needed before a broader claim.
