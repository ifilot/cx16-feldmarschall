The fully implemented objective bridge activates materially on the fixed old DOS
screening histories: **29 of 356 sampled native choices change (8.15%)**, across
48 prespecified games covering both colors. At least one actor's goal changes in
210 roots (59.0%); 641 of 4,188 actor plans change their target (15.3%). Red has
17 changed choices in 176 roots; Blue has 12 in 180. These are forced historical
prefix comparisons, not new game results or 356 independent observations.

All 13,040 intervening baseline/candidate native choices matched their respective
frozen launchers. Every bot first executes its complete native decision, then
corrects to the actual saved move before receiving the public event. Thus the
comparison retains full persistent goal history rather than reconstructing a
stateless proxy. Native goal traces use an unchanged source build from the
registered candidate archive with only `AI_TRACE` added. Runtime-helper hashes
also equal that archive. No current tournament or final-validation trajectory was
read; the input is C21's old screening cohort, with its exact hash in the result.

Mean host wall time per sampled choose is **1.74 ms baseline versus 3.10 ms
candidate**. Preparation excluding the native go wait averages 1.60 versus 2.95
ms; native go wait averages 0.138 versus 0.156 ms. The added work is mainly Python
expectation preparation and protocol transfer. Timing includes interpreter,
pipe/OS delays and concurrent host load; no target timing follows. The candidate
sends 4,013 more command bytes per turn (the 4,000 hex characters plus protocol
verb/newline). Its explicit native additions remain a 2,000-byte expectation
table and larger input buffer; CX16 fit is unqualified.

The audit supplies a meaningful mechanism test for the ongoing prespecified
strength screen. It does not establish that changed goals are better, that source
inference generalizes, or that the route planner converts those goals into wins.
No parameters, gates or candidate source changed after inspecting these roots.

Evidence: `RUNTIME-PROTOCOL.json`, `audit_runtime.py`, `runtime-result.json`,
`runtime.log`, `runtime-helper-binding.json`. The full audit took 110.3 host seconds.
