# AkShare Board Full Dump

- generated_at_utc: `2026-07-06T13:03:07Z`
- status: `partial_cache`
- note: Eastmoney and some THS endpoints started returning remote disconnect / parser errors during collection; this directory preserves completed cached CSVs and local manifests.

## Files

- `lists/`: cached provider board lists.
- `by_board/`: per-board CSVs that were successfully fetched before endpoint failures.
- `combined/`: concatenated CSVs rebuilt from existing `by_board/` files without network access.
- `metadata/cache_inventory.csv`: one row per cached `by_board` file.
- `metadata/cache_summary.csv`: grouped cache coverage summary.
- `metadata/call_manifest_checkpoint.csv`: latest interrupted/resume run checkpoint.
- `metadata/run_config.json`: latest full-dump run configuration.

## Board Lists

- `eastmoney_concept_board_list.csv`: 495 rows
- `eastmoney_industry_board_list.csv`: 496 rows
- `ths_concept_board_list.csv`: 374 rows
- `ths_industry_board_list.csv`: 90 rows

## Cached Dataset Coverage

- `eastmoney_industry_current_membership`: files=390, rows=12278
- `ths_industry_current_info`: files=15, rows=150
- `ths_industry_historical_index_ohlcv`: files=4, rows=14449, date_range=2007-08-01..2026-07-03

## PIT Boundary

- Eastmoney constituent files are current snapshots only and have no effective dates.
- THS constituent endpoints are not available in AkShare 1.18.10.
- Historical board-index OHLCV files are board/concept index histories, not historical stock membership.
- These files support source availability diagnostics and snapshot archiving, but cannot alone prove PIT industry/concept membership.
