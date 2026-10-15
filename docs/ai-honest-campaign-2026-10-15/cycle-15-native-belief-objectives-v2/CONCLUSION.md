# Cycle 15: second frozen recipe fails portable preflight

Version2 added AI_TEST, but public, played and belief-priors also require the outer AI_DIAGNOSTICS guard. The full copied runtime still rejects its first public query. The incomplete diagnosis and failed portable suite are preserved in checks.log. No tournament ran and no strength result is claimed.

The unchanged v2 recipes remain preserved. Version3 adds AI_DIAGNOSTICS after an exact provisional build from the v2 frozen sources passes an isolated driver/model/history test. Registration now checks the public-board, memory and prior compile flags for new native-belief recipes. The models and decision mechanism are unchanged.
