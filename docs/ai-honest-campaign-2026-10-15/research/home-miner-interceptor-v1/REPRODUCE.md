Run the tests from the repository root:

```sh
python3 -m unittest discover -s docs/ai-honest-campaign-2026-10-15/research/home-miner-interceptor-v1 -p 'test_preflight.py' -v
```

The largest JSON evidence is stored with deterministic, lossless gzip. `ARCHIVES.json` records uncompressed sizes and SHA-256 hashes. To inspect it, use Python's `gzip.open`, or decompress to a temporary location. To rerun the analyzers at their original paths, decompress `result.json.gz` to `result.json` in this directory, then run `qualify.py` or `deadlines.py`. `preflight.py` reconstructs that input from the pinned C21 tournament; `qualify.py` and `deadlines.py` read it. They use current imported referee/public-guard helpers, whose audit-time hashes are recorded in `SOURCES.json`.

`deadlines-v1-original.py` and `deadlines-v1-invalid.json.gz` are archival bug evidence, not the accepted analyzer or conclusion. Do not combine their counts with revision 2.

`mechanical-fixture.json` preserves the public board, exact legal reply certificates and successful alternative. `PROPOSAL.json` specifies the prospective public contract and unresolved limitations. There is no registered policy or runtime implementation in this directory.
