# Cycle 13: frozen recipe fails portable preflight

Both native belief v1 recipes compile, but omit AI_TEST, which enables public board queries used by the adapter. A copied runtime outside the checkout rejects its first public request. The failed portable test is preserved in checks.log. No saved tournament ran and no strength result is claimed.

The frozen source archives, recipes and IDs remain unchanged. Cycle15 creates v2 IDs with AI_TEST enabled; driver logic, core belief mechanism and frozen setup model are unchanged. Core, mock-driver and protocol mechanism tests passed before the portable recipe test exposed the omitted build flag.
