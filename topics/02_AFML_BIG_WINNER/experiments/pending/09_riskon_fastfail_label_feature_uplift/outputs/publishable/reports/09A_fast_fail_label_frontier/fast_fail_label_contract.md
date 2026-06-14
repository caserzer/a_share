# 09A Fast-Fail Label Contract

- selected_fast_fail_10_label: `break_swing_low_20;fixed_mae10_neg_12`
- event_binding_primary_fast_fail_label: `break_swing_low_20`
- selected_cost_bad_10_20_target: `selected_fast_fail_10_label OR frozen_event_false_repair_20d_label`
- selected_cost_bad_10_20_target label_t1_date: 20D cost horizon end date, used for purged CV / embargo / uniqueness.
- same-bar tie handling: first daily row whose `low <= barrier` is the touch row; if no touch inside 10D, label is false.
- selected_fast_fail_touch_pos: absolute row index in the instrument daily price file; do not use it as horizon offset.
- selected_fast_fail_touch_offset_sessions: trading-session offset from trade_time to first touch; no touch / not evaluable is -1.
- false-repair component: frozen upstream `event_false_repair_20d_label`; 09A does not redefine it.
- winner_readout_label: `event_big_winner_120d_label`; super/near winner labels are sensitivity only.
- winner_censoring_status: mapped from `candidate_outcome_120d_status`.
- existing `failure_10_label` is preserved as incumbent baseline and is never overwritten.

## Candidate Label Definitions

| label_id | mechanism | t0 | trade_time | fast_fail_t1 | price_field | adjustment_policy | barrier | censoring |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| incumbent_failure_10_label | incumbent_fixed_mae10 | event_t0_date | trade_open_date/open | upstream failure_10 t1 | upstream | upstream 08 label contract | upstream failure_10_label | failure_10_complete=false -> not_evaluable |
| fixed_mae10_neg_05 | fixed_mae10 | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 -0.0500) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| fixed_mae10_neg_06 | fixed_mae10 | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 -0.0600) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| fixed_mae10_neg_08 | fixed_mae10 | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 -0.0800) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| fixed_mae10_neg_10 | fixed_mae10 | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 -0.1000) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| fixed_mae10_neg_12 | fixed_mae10 | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 -0.1200) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| vol_sigma20_1_0 | vol_scaled | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 - 1.00 * trailing_sigma20) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| vol_sigma20_1_5 | vol_scaled | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 - 1.50 * trailing_sigma20) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| vol_sigma20_2_0 | vol_scaled | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price * (1 - 2.00 * trailing_sigma20) | missing path / incomplete 10D / missing barrier -> not_evaluable |
| atr14_1_5 | atr_scaled | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price - 1.50 * trailing_ATR14 | missing path / incomplete 10D / missing barrier -> not_evaluable |
| atr14_2_0 | atr_scaled | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | trade_open_price - 2.00 * trailing_ATR14 | missing path / incomplete 10D / missing barrier -> not_evaluable |
| break_event_low | structural | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | event_t0_date low | missing path / incomplete 10D / missing barrier -> not_evaluable |
| break_swing_low_20 | structural | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | prior 20D swing low before trade_time | missing path / incomplete 10D / missing barrier -> not_evaluable |
| break_ema20 | structural | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | EMA20 computed before trade_time | missing path / incomplete 10D / missing barrier -> not_evaluable |
| break_ema60 | structural | event_t0_date | trade_open_date/open | trade_open_date + 9 trading sessions | low touch | qfq_daily_csv_factor_column | EMA60 computed before trade_time | missing path / incomplete 10D / missing barrier -> not_evaluable |

## Winner Censoring Mapping

| upstream candidate_outcome_120d_status | winner_censoring_status |
| --- | --- |
| not_missing | complete |
| censored_incomplete_horizon | incomplete_120d |
| non_executable_next_open | non_executable |
| missing / unknown | not_evaluable |
