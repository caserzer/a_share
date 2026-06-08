# Data Prepare Final Report

Decision: `full_run_complete`

## Coverage

- Requested range: `2017-01-01` to `2026-05-31`
- Resolved trading range: `2017-01-03` to `2026-05-29`
- Resolved sessions: `2281`
- Selected instruments: `4915`
- Candidate before status rows: `475227`
- Raw membership rows: `471140`
- Executable membership rows: `470682`
- Qlib interval rows: `5697`
- Instrument failures: `318`

## Status Policy

- Shenzhen ST handling uses dated `stock_info_sz_change_name` rows.
- Shanghai ST handling removes the whole asset when `stock_info_change_name`
  ever returns an ST-marked name.
- Suspension handling for membership rows is derived from daily bar presence;
  rows without same-day raw/QFQ bars cannot enter market-cap membership.

## Qlib Provider Check

- status=passed, sample_instruments=SH600000|SH600009|SH600010|SH600011|SH600015, fields=$open|$high|$low|$close|$volume|$money|$turnover_rate|$factor, rows=11405, non_null_rows=11385
