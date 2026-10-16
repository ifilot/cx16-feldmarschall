# Compact honest back-row prior, version 1

This opt-in Classic Normal policy tests a minimal source-informed prior that fits the CX16. The unchanged DOS setup routine places its Flag in its back row. We assign 99% population mass to uniform legal armies with that constraint and retain a 1% uniform tail. No enemy setup, private rank, seed or actual Flag location is supplied. Public movement and disclosures remove impossible sites.

For U remaining undisclosed unmoved pieces and R compatible back-row sites, the Flag weights are 397 on that row and 1 elsewhere, normalized by U+396R. Remaining Bomb counts determine conditional Bomb risk. Integer evaluation rounds twice and differs by at most three gain points from the exact rational reference in the tested fixtures; it is a separate policy from the Python Q12 implementation.

Three mechanical tests pass, including both-side private-rank invariance, rational-value comparisons, and unchanged fallback difficulties/rules. Full production links pass. The candidate leaves 97 bytes in the AI bank and 41 bytes below the reserved 1,024-byte main stack. The default feature-disabled PRG and AI/MISSION banks match the preserved production baseline byte for byte. The candidate adds 528 MAIN code bytes and 16 MAIN storage bytes while saving 52 AI code bytes. The narrow remaining margin limits further additions.

Actual banked execution matched the native engine for all 80 tested public-history turns, including subsequent RNG behavior. Maximum decision duration was 34 emulator frames and at least 996 bytes of stack canary remained untouched. An independent agent reviewed the public-information calculation, denominators, signed arithmetic, color rotation, bank access and compile guards, and reran the three tests without finding a blocker.

On 18 fixed public screening views, simulated 65C02 paired evaluation adds an average 416,576 cycles (about 52 ms at an assumed 8 MHz; range 120,987–904,551 cycles). All 36 baseline/candidate native-versus-simulator move/RNG checks match. This flat-memory measurement excludes bank gateway timing and is not a strength test. The separate banked run covers execution through the real gateway.

The first cost harness accidentally emitted eleven temporary simulator objects beside source files. Its artifacts and exact generated-object hashes are preserved in initial-cost-isolation-error. Only those generated objects were removed. The corrected harness copies all source inputs to a temporary directory, reran successfully, and verifies every workspace src file unchanged. No authored source or game binary was changed by that measurement.

No playing-strength result or promotion is claimed here. Fresh frozen DOS and honest-opponent comparisons follow separately. See target-audit.json, cycles.json, banked-student-decisions.json and their logs for authoritative evidence.
