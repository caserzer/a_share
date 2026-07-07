# Tushare DC Yearly Board Snapshot

## Files

- `combined/dc_index_yearly_first_open.csv`: yearly first-open-day board lists/status.
- `combined/dc_member_yearly_first_open.csv`: yearly first-open-day board constituents.
- `by_year/<year>/`: per-year board and per-board member source files.
- `metadata/year_first_trade_dates.csv`: first open trading day used for each year.
- `metadata/classification_year_snapshot_mapping.csv`: classification year to source snapshot mapping.
- `metadata/call_manifest.csv`: every Tushare call and cache hit.
- `metadata/dataset_summary.csv`: grouped status and row totals.

## Interpretation

- Source APIs: Tushare `dc_index` and `dc_member` for Eastmoney concept boards.
- Years before 2025 are explicitly backfilled from the 2025 first-open TuShare DC snapshot.
- 2025 uses the 2025 first-open snapshot; 2026 uses the 2026 first-open snapshot.
- Effective policy: each mapped snapshot is recorded as that calendar year's board-classification contract.
- Pre-2025 rows are a fixed taxonomy proxy, not historical PIT membership evidence.

## Row Counts

- board_rows: `7769`
- member_rows: `751970`

## Year Coverage

| classification_year | classification_first_open_trade_date | source_snapshot_year | source_snapshot_trade_date | snapshot_policy | board_rows | member_rows | boards_with_members |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2010 | 20100104 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2011 | 20110104 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2012 | 20120104 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2013 | 20130104 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2014 | 20140102 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2015 | 20150105 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2016 | 20160104 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2017 | 20170103 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2018 | 20180102 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2019 | 20190102 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2020 | 20200102 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2021 | 20210104 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2022 | 20220104 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2023 | 20230103 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2024 | 20240102 | 2025 | 20250102 | pre_2025_backfilled_from_2025_snapshot | 458 | 43468 | 314 |
| 2025 | 20250102 | 2025 | 20250102 | exact_year_first_open_snapshot | 458 | 43468 | 314 |
| 2026 | 20260105 | 2026 | 20260105 | exact_year_first_open_snapshot | 441 | 56482 | 441 |
