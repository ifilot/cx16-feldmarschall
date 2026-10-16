# AI development direction

- Focus new AI development and strength evaluation on Classic rules. Optional
  rule research is deferred unless the user explicitly requests it.
- Prefer experiments that test a clear strategic idea over small score tweaks.
  Explain the idea, expected behavior, comparison and result in ordinary language.
- Give each selectable policy an immutable, descriptive ID and version. Register
  its source snapshot, build recipe, difficulty and model before running a saved
  tournament. Never silently change an existing ID; create a new version instead.
- Preserve accepted and rejected policies and their evidence. Use fresh seeds for
  final validation; do not tune on a validation cohort.
- Use the Classic tournament runner and Qt6 companion for new reviewable matches.
  Preserve the game's artwork, colors and board orientation in the companion.

# Production AI boundary

- Continue AI experiments in the separate `feldmarschall-ai` repository. This
  repository owns the rules, interface, artwork and production integration.
- Import a specific qualified release with `tools/ai_release.py`; do not edit
  the vendored AI/model files or silently change the installed release ID.
- Keep release integrity, rules, hidden-information and X16 lifecycle/packaging
  checks here. Detailed research evidence and saved tournaments live with the
  research repository; `docs/ai-release.md` records the installed release.
