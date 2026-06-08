# Benchmark Index Data Prepare Report

Decision: `index_only_complete`

## Coverage

- Requested range: `2017-01-01` to `2026-05-31`
- Resolved trading range: `2017-01-03` to `2026-05-29`
- Resolved sessions: `2281`
- Index rows: `6843`
- Index failures: `0`

## Index Series

- index_alias=csi300, name=沪深300指数, instrument=SH000300, source_function=stock_zh_index_daily, source_symbol=sh000300, first_date=2017-01-03, last_date=2026-05-29, row_count=2281, missing_calendar_dates=0, nullable_volume_rows=0, nullable_money_rows=2281
- index_alias=chinext_index, name=创业板指数, instrument=SZ399006, source_function=stock_zh_index_daily, source_symbol=sz399006, first_date=2017-01-03, last_date=2026-05-29, row_count=2281, missing_calendar_dates=0, nullable_volume_rows=0, nullable_money_rows=2281
- index_alias=all_a, name=全A指数 / 中证全指, instrument=SH000985, source_function=stock_zh_index_daily_tx, source_symbol=sh000985, first_date=2017-01-03, last_date=2026-05-29, row_count=2281, missing_calendar_dates=0, nullable_volume_rows=0, nullable_money_rows=2281

## Index Qlib Provider Check

- status=passed, instrument=SH000300, fields=$open|$high|$low|$close|$volume|$money, rows=2281, ohlc_non_null_rows=2281, volume_nullable_rows=0, money_nullable_rows=2281
- status=passed, instrument=SH000985, fields=$open|$high|$low|$close|$volume|$money, rows=2281, ohlc_non_null_rows=2281, volume_nullable_rows=0, money_nullable_rows=2281
- status=passed, instrument=SZ399006, fields=$open|$high|$low|$close|$volume|$money, rows=2281, ohlc_non_null_rows=2281, volume_nullable_rows=0, money_nullable_rows=2281
