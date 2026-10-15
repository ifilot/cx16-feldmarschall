# Original DOS deployment audit

The original Colonel setup differs substantially from the seven referee layout families used in earlier matches. Its first original RNG draw normally selects one of four fixed armies, with optional horizontal reflection. Its remaining procedural branch also builds a Bomb barrier around the Flag. The earlier 53.9% aggregate against referee-selected DOS armies does not establish a win against the original game's default deployments.

The generator runs unchanged overlay 6 instructions, including both branches, in a separate Unicorn CPU. It needs only a private RNG state and difficulty. Its complete 18,432-byte output matches a retained original-game startup capture exactly. Seven tests cover that capture, all eight Colonel template/reflection choices, procedural placement, all five difficulties, inventory, determinism, corrupted assets and portable archive execution. No match was played for this audit.

`audit.json` records addresses, scope and results; `tables.json` contains the original tables and canonical Colonel strings. `sources/` retains twelve primary source/report files from commit `306e3cb757137f3c28d1224ee3d2c4570f412509`, with Git blob identities verified in `source-review.json`. `import.json` pins the original overlay and startup captures.

`generator-assets.zip` is a portable verified asset bundle. After extracting it, call `generate_setup(directory, private_32bit_seed, level=3)` from `tools/campaign_dos_deployment.py`. It returns the canonical army and deterministic audit, including the RNG state before and after placement. Canonical armies list front to back, preserving columns in the original top/Blue orientation.

The setup seed must remain private and independent of any seed supplied to an honest player. The interactive original game continues with the advanced RNG state; the existing move adapter independently reseeds its move engine. A benchmark using the generator with that adapter must disclose this boundary.

`tools/campaign_dos_setup_runtime.py` freezes a private JSON worker, its generator/CPU sources, original assets and the exact Unicorn runtime into tournament artifacts before generating armies. Its auditor reproduces the armies using those embedded files and binds them to the saved game setups. The helper does not change the tournament runner or register a policy.
