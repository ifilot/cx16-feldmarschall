# Independent honest head-to-head validation

Prepared only. No games have started. Three frozen direct comparisons, each with 100 paired rounds across seven Classic setup families (1,400 games), use fresh seeds 2250001, 2260001 and 2270001.

Review plan.json before running. Existing policy source archives and catalog identities are fixed; no new policy is registered. The run action freezes analysis sources before the first game, then uses the Classic runner and Python/native/Qt6 replay checks. Failed files and error prefixes remain preserved.

Run when resources are available: `python3 tools/campaign_honest_heads.py run`. Results report candidate scores and paired intervals relative to 50%. These tests alone cannot justify promotion; independent DOS validation remains required.
