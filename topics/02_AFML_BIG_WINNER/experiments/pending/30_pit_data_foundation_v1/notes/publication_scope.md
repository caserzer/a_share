# EP30 publication scope — 2026-10-22

This commit publishes the EP30 source, tests, schemas, configuration, reports,
reproduction instructions and public audit records accumulated through D2-v5,
together with the three topic/experiment/research-log index updates. GOAL.md was
already committed and remains unchanged. EP01–EP29 research is unchanged.

The public CSV/JSON/JSONL records contain coverage, conflicts, source hashes,
disclosure indexes, reviewed facts, candidate extraction diagnostics and collection
receipts. They are audit records, not the underlying daily price or model panels.
The compressed CSV contains field/security/year coverage counts. Existing
hash-bearing artifacts retain their exact bytes; historical release manifests are
historical snapshots and are not rewritten as current-tree manifests.

Original HTTP/TCP bodies, PDFs, OCR images/models, vendor packages, full Parquet
price/label/bridge tables and immutable private releases remain outside Git under
`~/.cache/a_share/ep30_d2/`. Public access is not a raw-data redistribution license.
Absolute local paths in receipts identify evidence locations and do not make those
files available from a clone. Local bytecode and test caches are excluded.

The current D2-v5 release is
`9ba9324e4ff8f3a5db14c03893d76c77097855d3f83e9dde2b476f2760aec72e`.
Its 6,309,144 records include 6,007,218 known price-inferred records; the three
requested policies share one forward-adjusted price proxy and are not independent
samples. Original strict results remain preserved. Cross-provider qfq differences
for 24 securities are flagged. Historical eligibility, actual execution/terminal
wealth and complete financial vintages retain their separate limitations.

Pre-publication checks: 97 tests passed; the existing frozen-code offline replay
matched all columns of 5,846 Parquet products / 17,377,955 rows and seven audit CSVs.
The original 8,052 v4 release files and 7,064 protected prior files passed their
recorded checks. These data checks are preserved rather than rerun against live
providers during publication. `outputs/publication/file_manifest.json` records
the exact files in the publication closure, excluding its own self-reference.
