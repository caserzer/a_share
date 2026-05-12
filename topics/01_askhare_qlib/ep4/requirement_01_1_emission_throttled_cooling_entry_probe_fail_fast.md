# EP4 Requirement 01.1：Emission-Throttled Seed + Cooling Entry + Probe + Fail-Fast

> Requirement id: `ep4_r01_1_emission_throttled_cooling_entry_probe_fail_fast`
> Status: implementation-ready requirement draft
> Scope: EP4-R01.1，只修复 R01 V2 暴露出的两个硬伤：`seed-day density` 过高与 `T+1 open` 即时买入过热。R01.1 固定 raw seed 为 R01 V2 五条件，不训练模型、不引入加仓、不引入 ATR/state/trailing exit，只增加 deterministic seed emission throttle 与 deterministic cooling entry。
> Upstream requirement: `ep4/requirement_01_high_recall_probe_fail_fast_v2.md`
> Upstream report: `ep4/outputs/r01_high_recall_probe_fail_fast_v2_money_rps5_boll20_high10_seed/reports/r01_final_report.md`
> Date: 2026-05-12

---

## 0. R01.1 One-Line Definition

R01.1 的核心变更只有两条：

```text
raw seed 仍使用 R01 V2 五条件；
但同一 instrument 在 20 trading days 内只允许发射一次 emitted seed；
emitted seed 后先观察 T+1 是否立刻结构失败；
若 T+1 未失败，则 T+2 open 买入 0.25R probe。
```

R01.1 不解决加仓，不解决动态退出，不解决组合 sizing。它只验证：

```text
在不重新训练、不重新调阈值、不增加复杂过滤器的情况下，
通过 seed emission throttle + cooling entry，
是否可以同时修复：
1. seed-day density 过高；
2. T+1 open 即时买入相对 matched-delay 过热；
同时保留 R01 V2 已经出现的 recall-cost 正向证据。
```

---

## 1. Background and Motivation

R01 V2 最终决策为：

```text
stop_ep4_r01_path
```

R01 V2 失败原因不是 recall-cost 失败，也不是 deterministic fail-fast 成本控制失败，而是：

```text
1. train / validation 的 seed-day density 超过 V2 下调后的日级密度上限；
2. validation 的 1-day matched-delay no-harm 失败，说明 T+1 open 即时买入仍有追高劣势；
3. matched-random baseline 仍不可靠，但在 V2 中已经降为 audit-only，不作为 hard gate。
```

R01 V2 同时给出以下正向证据：

```text
validation recall: EP2 10.76% -> candidate 24.68%
robustness recall: EP2 19.50% -> candidate 31.12%
validation net added big winner: +27
validation incremental loss per added winner: 3.42R <= 5R
validation incremental exposure days per added winner: 215.78 <= 250
fail-fast vs no-fail-fast:
  validation failed-seed average loss reduced by 0.0896R
  median holding days reduced from 22 to 11
```

因此，R01.1 的研究结论假设是：

```text
R01 V2 的方向没有被证伪；
但当前 raw seed 发射过密，且 T+1 open entry 过早。
```

R01.1 不允许把 R01 V2 的 stop decision 解释为：

```text
seed 完全无效；
fail-fast 完全无效；
可以直接进入 R02；
可以通过训练模型绕过 R01 hard gates。
```

---

## 2. Phase Boundary

R01.1 继承 R01 V2 的 phase boundary。完成本 requirement 以前，不允许：

- 训练 entry / ranking / fail-fast / continuation / exit 模型；
- 使用 Label B 训练 Early Failure Detector；
- 引入 staged add / confirm add / scale-in；
- 引入 ATR trailing stop、state stop、profit giveback 或复杂 dynamic exit；
- 做 portfolio optimizer、行业风险预算、主题集中度控制或 capital allocation；
- 用 validation / robustness 结果反向选择 seed 阈值、emission window、cooling rule、fail-fast 规则、exit horizon 或 recall gate；
- 用 `future_50h120` 直接训练 entry 模型；
- 使用 VCP / continuous confirmation audit 结果反向修改 main seed；
- 宣称 R01.1 是完整可交易策略。

Allowed use:

```text
train split:
  只允许冻结 matched-control bucket edges 和明确列出的 audit bin edges。

validation / robustness:
  只报告冻结规则的结果，不能重新选阈值、窗口、entry 规则或 gate。
```

R01.1 可以报告 VCP、continuous confirmation、Label A、Label B、Label D 的 audit 切片，但这些 label / audit 只能用于解释，不得用于训练或阈值选择。

---

## 3. Upstream Facts To Preserve

### 3.1 EP2 Facts

R01.1 必须继续使用 EP2 frozen launch detector 作为 bridge baseline / control：

```yaml
launch_detector_version: EP2_LAUNCH_DETECTOR_V0
detector_id: EP2_LAUNCH_DETECTOR_V0_PRICE60_MONEY20
detector_family: price_breakout_money_surge
primary_label_id: confirm_h10_u10_d06_conservative_fail
baseline_schedule_id: probe_with_simple_stop
```

EP2 的作用：

```text
1. 提供 seed density / episode density / recall / recall-cost 的 baseline；
2. 防止 R01.1 只是在一个更窄、更精的 sleeve 上声称 high-recall 成功；
3. 保持 EP4 与 EP2 engineering baseline 的可比性。
```

### 3.2 EP3 Facts

EP3 已经证明：

```text
trigger rate 不等于 payoff edge；
形态 recall 不等于 forward lift；
matched-delay baseline 和 tail risk 必须作为主验证对象。
```

因此，R01.1 的任何 go decision 必须同时报告：

```text
seed density / universe coverage
matched-delay same-fail-fast no-harm
p05 / tail no-harm
recall-cost trade-off
fail-fast false-reject / missed-failure audit
raw_seed -> emitted_seed -> cooling_qualified_probe 的 recall waterfall
```

### 3.3 R01 V2 Facts

R01.1 必须继承 R01 V2 的以下事实：

```text
raw seed 五条件已有稳定 recall 增量；
deterministic fail-fast 相比 no-fail-fast 有成本控制价值；
T+10 entry-price trigger 是重要成本控制补丁；
但 raw seed-day density 超 cap，且 T+1 open entry 偏早。
```

---

## 4. Canonical Inputs

R01.1 只能使用 R01 V2 已允许的 canonical inputs，并增加 R01 V2 输出作为上游 audit / comparison source。

| Input | Required path | Role |
|:--|:--|:--|
| EP4 discussion | `ep4/discussion.md` | requirement 背景和阶段边界 |
| R01 V2 requirement | `ep4/requirement_01_high_recall_probe_fail_fast_v2.md` | inherited rule authority |
| R01 V2 final report | `ep4/outputs/r01_high_recall_probe_fail_fast_v2_money_rps5_boll20_high10_seed/reports/r01_final_report.md` | upstream failure inheritance |
| R01 V2 manifest | `ep4/outputs/r01_high_recall_probe_fail_fast_v2_money_rps5_boll20_high10_seed/manifests/r01_run_manifest.json` | upstream effective windows / reproducibility |
| EP2 engineering baseline manifest | `ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json` | EP2 frozen authority |
| EP2 engineering baseline config | `ep2/engineering_baseline/config.yaml` | cost model / execution convention source |
| EP2 launch observation pool | `ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet` | EP2 detector baseline / bridge denominator |
| Local PIT Qlib OHLCV provider | `data/qlib/cn_data_pit` | R01.1 seed / execution / forward audit |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | trading-day horizon |
| PIT daily universe membership | `data/universe/pit_mcap500_mainboard_daily.csv` | point-in-time tradable denominator |
| PIT qlib instrument map | `data/universe/pit_qlib_instrument_universe.csv` | instrument-code mapping and provider audit |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | audit-only industry decomposition |
| Qlib PIT instrument file | `data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt` | provider instrument-date coverage authority |

Forbidden inputs:

- EP2 R02 / R03 / R04 / R05 model, schedule, holding policy outputs；
- EP3 candidate anchor / rolling state action outputs as seed inputs；
- Explore9 / Explore10 row-level outputs；
- any new Tushare / AkShare fetch；
- any manual survivor list or ex-post stock list；
- any validation-selected seed, VCP, confirmation, entry-timing threshold。

Hard rule:

```text
R01.1 的 big-winner denominator 必须从 PIT universe + local PIT OHLCV 重新构造；
不得使用 survivor-biased ex-post list。
```

---

## 5. Required Config

Implementation must add:

```text
ep4/configs/r01_1_emission_throttled_cooling_entry_probe_fail_fast.yaml
```

Minimum required config:

```yaml
phase: ep4_r01_1_emission_throttled_cooling_entry_probe_fail_fast
requirement_path: ep4/requirement_01_1_emission_throttled_cooling_entry_probe_fail_fast.md
output_root: ep4/outputs/r01_1_emission_throttled_cooling_entry_probe_fail_fast

split:
  train_start: "2017-07-04"
  train_end: "2021-12-31"
  validation_start: "2022-01-01"
  validation_end: "2023-12-31"
  robustness_start: "2024-01-01"
  robustness_end: "2025-12-31"
  split_date_field: emitted_signal_date
  effective_reference_window_policy: min(split_end, data_max_date_minus_forward_horizon)
  manifest_must_record_effective_reference_windows: true

big_winner_reference:
  primary_id: big_winner_50h120_close_confirmed
  forward_horizon_trading_days: 120
  return_threshold: 0.50
  entry_price_reference: next_open
  peak_price_reference: max_close
  dedupe_gap_trading_days: 120
  eligible_requires_full_forward_window: true
  secondary_bridge_ids:
    - ep2_launch_pool_big_winner_50h120

raw_seed_rules:
  raw_seed_id: ep4_r01_v2_raw_money_rps5_boll20_high10_seed
  formula_id: money_ratio20_gt_1_0_and_money_ratio5_gt_2_0_and_rps5_gt_50_and_boll20_pct_b_gt_1_0_and_close_near_high10_gt_0
  money_activity:
    money_ratio20:
      denominator: prior_20_trading_day_mean_money
      threshold: 1.0
      comparison: ">"
    money_ratio5:
      denominator: prior_5_trading_day_mean_money
      threshold: 2.0
      comparison: ">"
  relative_strength:
    lookback_trading_days: 5
    cross_section_percentile_threshold: 0.50
    comparison: ">"
  price_structure:
    bollinger_pct_b:
      window: 20
      threshold: 1.0
      comparison: ">"
    close_near_high10:
      rolling_high_window: 10
      operational_rule: close_T >= max(close, T-10..T-1)
  structural_reference_fields:
    seed_day_low_rule: low_on_raw_signal_date
    pivot_low_10d_rule: min_low_over_raw_signal_date_minus_10_to_minus_1
    breakout_reference_rule: max_close_over_raw_signal_date_minus_10_to_minus_1

emission:
  emitted_seed_id: ep4_r01_1_emitted_seed_20d_from_r01_v2_raw_seed
  source_raw_seed_id: ep4_r01_v2_raw_money_rps5_boll20_high10_seed
  throttle_policy: first_raw_seed_then_suppress_same_instrument_for_20_trading_days
  throttle_window_trading_days: 20
  recursive_emission_order: instrument_full_history_chronological
  split_boundary_reset_allowed: false
  split_assignment_field_after_emission: emitted_signal_date
  suppress_window_inclusive_rule: suppress_raw_seed_dates_in_T_plus_1_through_T_plus_20
  allow_next_emission_from: T_plus_21_or_later
  carry_structural_references_from: emitted_raw_seed_date
  raw_seed_density_report_only: true

cooling_entry:
  entry_family_id: cooling_observation_day_then_t2_open_entry
  emitted_signal_date: T
  cooling_observation_date: next_trading_day_after_T
  entry_date: second_trading_day_after_T
  entry_price: open_on_entry_date
  cancel_probe_if_cooling_day_any_true:
    - cooling_close_below_seed_day_low
    - cooling_close_below_breakout_reference
    - cooling_close_below_pivot_low_10d
  cooling_same_day_ambiguity_policy: conservative_cancel
  cancelled_probe_status: cancelled_by_cooling_failure
  buy_block_action: reject_probe_after_cooling
  sell_block_action: retry_next_executable_open_until_terminal
  max_exit_retry_trading_days: 20

probe:
  initial_probe_risk_budget_r: 0.25
  no_add_allowed: true
  no_portfolio_sizing_allowed: true

risk_normalization:
  unit: episode_normalized_full_R
  initial_structural_stop_candidates:
    - seed_day_low
    - breakout_reference
    - pivot_low_10d
  initial_structural_stop_rule: closest_valid_stop_below_entry
  min_initial_risk_pct: 0.02
  max_initial_risk_pct: 0.12
  if_no_valid_initial_stop: reject_probe_after_cooling
  return_r_formula: initial_probe_risk_budget_r * after_cost_return_pct / initial_risk_pct

fail_fast:
  family_id: deterministic_structure_fail_fast_v0_entry_relative
  max_fail_fast_window_trading_days: 10
  natural_exit_horizon_trading_days: 20
  window_anchor: entry_date
  triggers:
    - close_below_seed_day_low
    - close_below_breakout_reference
    - close_below_pivot_low_10d
    - entry_relative_day_10_close_below_entry_price
  exit_rule: next_open_after_trigger
  same_day_trigger_policy: conservative_fail

seed_density_caps:
  max_candidate_emitted_seed_day_rate: 0.045
  max_candidate_emitted_seed_day_rate_vs_ep2_multiple: 2.7
  max_candidate_probe_entry_day_rate: 0.045
  max_candidate_probe_entry_day_rate_vs_ep2_multiple: 2.7
  max_candidate_episode_rate_vs_ep2_multiple: 3.0
  preferred_seed_day_rate_vs_ep2_multiple_report_only: 2.5
  min_unique_instrument_years_validation: 80

seed_recall:
  primary_recall_lookback_days: 20
  primary_recall_forward_days: 0
  primary_recall_window_id: primary_-20_0
  headline_recall_basis: cooling_qualified_executable_probe_episode
  diagnostic_recall_bases:
    - raw_seed_stock_day
    - emitted_seed_episode_pre_cooling
    - cooling_qualified_probe_episode
    - fail_fast_survived_probe_episode

baselines:
  - same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted
  - same_cooling_qualified_seed_t1_open_same_fail_fast_h20
  - same_cooling_qualified_seed_t3_open_same_fail_fast_h20
  - same_cooling_qualified_seed_no_fail_fast_hold_h20
  - same_cooling_qualified_seed_t1_open_no_fail_fast_h20
  - same_cooling_qualified_seed_t3_open_no_fail_fast_h20
  - r01_v2_raw_seed_t1_open_bridge
  - ep2_detector_probe_with_simple_stop_bridge
  - matched_random_same_density_same_fail_fast_h20_report_only
  - matched_random_same_density_no_fail_fast_h20_report_only

matched_random:
  bucket_edges_source_split: train
  bucket_fields:
    - split
    - industry_bucket
    - liquidity_bucket
    - volatility_bucket
    - calendar_year
  exclude_candidate_ep4_seed_stock_days: true
  sampling_replacement_policy: no_replacement
  validation_bucket_shortfall_fail_threshold: 0.20
  random_seed: 20260512

risk_pct_quintile_cost_control:
  quintile_edge_source_split: train
  quintile_field: initial_risk_pct
  min_validation_rows_per_quintile: 30
  min_sufficient_validation_quintiles: 3
  max_failed_seed_average_loss_r_diff_vs_no_fail_fast: 0.0
  min_p05_return_r_diff_vs_no_fail_fast: -0.03

selection_policy:
  seed_threshold_policy: literal_frozen_constants_from_config
  emission_window_policy: literal_frozen_20_trading_days
  cooling_entry_policy: literal_frozen_t1_observe_t2_open
  validation_threshold_selection_allowed: false
  robustness_threshold_selection_allowed: false

recall_cost_gate:
  max_incremental_loss_r_per_added_big_winner_vs_ep2: 5.0
  max_incremental_exposure_days_per_added_big_winner_vs_ep2: 250
  robustness_max_incremental_loss_r_per_added_big_winner_vs_ep2: 7.5
  robustness_max_incremental_exposure_days_per_added_big_winner_vs_ep2: 375
```

---

## 6. Big-Winner Reference Set Contract

R01.1 must reconstruct the primary big-winner reference set independently, using the same R01 V2 definition.

### 6.1 Primary Reference

```text
primary_id = big_winner_50h120_close_confirmed
```

Definition:

```text
For each PIT-tradable instrument-date t:
  entry_price = next_open(t)
  forward_peak = max(close over next 120 trading days)
  forward_return = forward_peak / entry_price - 1
  positive if forward_return >= 0.50
```

Reference date rule:

```text
reference_date = first eligible date t in a deduped positive run.
If several consecutive dates satisfy forward_return >= 0.50 for the same instrument,
keep only the earliest eligible t, then suppress the next 120 trading days for that instrument.
```

Effective reference window:

```text
effective_reference_end = min(configured_split_end, data_max_date - 120 trading days)
```

`r01_1_run_manifest.json` must record configured windows, effective windows, data max date, and forward-window availability.

### 6.2 Bridge Reference

```text
bridge_id = ep2_launch_pool_big_winner_50h120
```

The bridge reference is used only for comparability with EP2 frozen launch pool. It must not replace the primary PIT denominator.

---

## 7. Seed Contract

R01.1 has three seed layers:

```text
raw_seed -> emitted_seed -> cooling_qualified_probe
```

Headline gates must clearly state which layer they use.

### 7.1 Baseline Seed：EP2 Detector Bridge

```text
seed_family_id = ep2_launch_detector_v0_bridge
```

EP2 bridge provides seed density baseline, episode density baseline, primary / bridge recall baseline, and recall-cost denominator.

### 7.2 Raw Seed：R01 V2 Five-Condition Seed

```text
raw_seed_family_id = ep4_r01_v2_raw_money_rps5_boll20_high10_seed
```

R01.1 raw seed is exactly R01 V2 candidate seed:

```text
money_ratio20_T > 1.0
AND money_ratio5_T > 2.0
AND rps5_T > 0.50
AND boll20_pct_b_T > 1.0
AND close_T >= max(close, T-10..T-1)
AND hard_tradability_filters pass
```

Structural references carried from raw seed date `T`:

```text
seed_day_low = low_T
pivot_low_10d = min(low, T-10..T-1)
breakout_reference = max(close, T-10..T-1)
```

No additional hard seed filter is allowed in R01.1.

### 7.3 Emitted Seed：20D Instrument-Level Emission Throttle

```text
emitted_seed_family_id = ep4_r01_1_emitted_seed_20d_from_r01_v2_raw_seed
```

Deterministic rule:

```text
For each instrument independently:
  sort all raw seed dates across the full configured history in chronological order
  emit the first raw seed date T
  suppress all raw seed dates from T+1 through T+20 trading days
  next emission can occur only on T+21 or later
  repeat until the end of available data
```

Important:

```text
The emission process is recursive and must be evaluated chronologically.
The throttle state must not reset at train / validation / robustness split boundaries.
Split assignment happens only after full-history emission, using emitted_signal_date.
It must not look forward to future returns, future raw seed quality, future reference events, or validation outcomes.
```

Required audit fields:

```text
raw_seed_count
emitted_seed_count
suppressed_raw_seed_count
suppressed_raw_seed_share
suppressed_raw_seed_by_instrument/year/industry/liquidity_bucket/volatility_bucket
raw_to_emitted_lost_primary_capture_count
raw_to_emitted_added_primary_capture_count
raw_to_emitted_net_capture_count
split_boundary_suppressed_raw_seed_count
```

### 7.4 Cooling-Qualified Probe

For each emitted seed date `T`:

```text
cooling_observation_date = T+1 trading day
entry_date = T+2 trading day
entry_price = open(entry_date)
```

Cancel the probe if any of the following is true on the cooling observation date:

```text
close(T+1) < seed_day_low
close(T+1) < breakout_reference
close(T+1) < pivot_low_10d
```

If cooling is cancelled:

```text
row remains in emitted seed audit；
row is not an executable probe；
row does not enter main probe simulation；
row must be counted in cooling_cancelled_count；
row must be evaluated for cooling_cancelled_big_winner_capture_loss。
```

If not cancelled:

```text
attempt entry at T+2 open；
if T+2 open is buy-blocked, reject probe after cooling；
if entry succeeds, row becomes a cooling-qualified executable probe episode。
```

### 7.5 Episode Dedup Rule

Emission throttle controls raw seed stock-day over-emission before episode construction. Episode dedup groups emitted seeds into seed episodes for simulation and recall.

Default episode rule:

```text
Because emission already suppresses same-instrument raw seeds from T+1 through T+20,
R01.1 default treats each emitted seed as one seed episode.

seed_episode_id = instrument + emitted_signal_date
episode start = emitted_signal_date
episode effective entry = emitted seed's cooling-qualified T+2 open if executable
episode end = natural exit / fail-fast exit / rejected-probe terminal status
```

Re-entry rule:

```text
There is no within-episode re-entry in R01.1.
Any later same-instrument emitted seed has a different seed_episode_id by construction
because it can occur only on T+21 or later.
If an implementation creates merged episodes, the validator must fail closed.
```

---

## 8. Density Denominator and Density Metrics

R01.1 reports three density layers:

```text
raw_seed_day_rate
emitted_seed_day_rate
cooling_qualified_probe_entry_day_rate
```

### 8.1 Eligible Stock-Day Denominator

```text
eligible_stock_day =
  PIT universe member on signal date
  and required rolling history for raw seed formula exists
  and required structural references exist
  and not suspended_or_dirty_bar
```

For cooling-qualified probe density, additionally require:

```text
cooling_observation_date exists
entry_date exists
T+2 open is available
```

### 8.2 Hard Density Gates

All must pass in train and validation. Robustness is evaluated under robustness no-harm gates.

```yaml
candidate_emitted_seed_day_rate_train: <= min(0.045, 2.7 * ep2_seed_day_rate_train)
candidate_emitted_seed_day_rate_validation: <= min(0.045, 2.7 * ep2_seed_day_rate_validation)
candidate_probe_entry_day_rate_train: <= min(0.045, 2.7 * ep2_seed_day_rate_train)
candidate_probe_entry_day_rate_validation: <= min(0.045, 2.7 * ep2_seed_day_rate_validation)
candidate_emitted_seed_episode_rate_train: <= 3.0 * ep2_seed_episode_rate_train
candidate_emitted_seed_episode_rate_validation: <= 3.0 * ep2_seed_episode_rate_validation
candidate_probe_entry_episode_rate_train: <= 3.0 * ep2_seed_episode_rate_train
candidate_probe_entry_episode_rate_validation: <= 3.0 * ep2_seed_episode_rate_validation
validation_unique_instrument_years: >= 80
top1_instrument_year_probe_entry_share_validation: <= 0.05
```

Report-only preferred target:

```yaml
preferred_probe_entry_day_rate_vs_ep2_multiple: <= 2.5
```

The preferred target cannot determine go / stop by itself.

### 8.3 Count-vs-EP2 High-Recall Preconditions

R01.1 cannot claim high-recall path if the candidate is narrower than EP2 on either executable stock-day count or executable episode count.

Required high-recall preconditions:

```yaml
candidate_probe_entry_day_count_vs_ep2_ratio_validation: >= 1.0
candidate_probe_entry_episode_count_vs_ep2_ratio_validation: >= 1.0
```

If either precondition fails but cost-control improves, the decision may be:

```text
archive_cost_control_sleeve_no_r02
```

but not:

```text
go_to_r02
```

---

## 9. Probe and Fail-Fast Contract

### 9.1 Probe

Only initial probe is allowed:

```text
initial_probe_risk_budget = 0.25R
entry = T+2 open after emitted seed T, conditional on cooling pass
```

R unit:

```text
initial_structural_stop =
  closest valid stop below entry among:
    seed_day_low
    breakout_reference
    pivot_low_10d

initial_risk_pct =
  (entry_price - initial_structural_stop) / entry_price

return_r =
  initial_probe_risk_budget_r * after_cost_return_pct / initial_risk_pct
```

Risk bounds:

```text
2% <= initial_risk_pct <= 12%
```

If no valid stop exists or risk distance is outside bounds:

```text
reject_probe_after_cooling
```

### 9.2 Deterministic Fail-Fast

Fail-fast is entry-relative, not raw-signal-relative.

Let:

```text
T = emitted signal date
C = cooling observation date = T+1
E = entry date = T+2
```

Within the first 10 entry-relative trading days after entry, including the entry date close:

```text
E_day_1 = close on E
E_day_10 = close on the 10th trading day from E
```

Exit at next executable open if any trigger occurs:

```text
1. close < seed_day_low
2. close < breakout_reference
3. close < pivot_low_10d
4. on E_day_10 only: close < entry_price
```

Natural exit:

```text
If no fail-fast trigger occurs, exit at next executable open after H20 entry-relative trading days.
```

Execution realism:

```text
buy blocked at T+2 open:
  reject probe after cooling;
  keep row in rejected-probe audit.

sell blocked at fail-fast or natural-exit next open:
  retry at next executable open;
  keep blocked days in holding-days and exposure-days;
  after max_exit_retry_trading_days, mark terminal_blocked_exit.
```

---

## 10. Baseline Contract

R01.1 must include the following baselines.

| Baseline id | Population | Entry rule | Fail-fast | Purpose |
|:--|:--|:--|:--|:--|
| `same_cooling_qualified_seed_no_fail_fast_hold_h20` | same cooling-qualified probe rows | T+2 open | no | isolate fail-fast increment |
| `same_cooling_qualified_seed_t1_open_same_fail_fast_h20` | same cooling-qualified probe rows | T+1 open | yes, same carried refs | same-sample counterfactual for cooling entry timing |
| `same_cooling_qualified_seed_t3_open_same_fail_fast_h20` | same cooling-qualified probe rows | T+3 open | yes, same carried refs | matched-delay no-harm after cooling |
| `same_cooling_qualified_seed_t1_open_no_fail_fast_h20` | same cooling-qualified probe rows | T+1 open | no | audit-only |
| `same_cooling_qualified_seed_t3_open_no_fail_fast_h20` | same cooling-qualified probe rows | T+3 open | no | audit-only |
| `same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted` | all emitted seeds before cooling cancel | T+1 open | yes | executable total-effect bridge vs no cooling |
| `r01_v2_raw_seed_t1_open_bridge` | R01 V2 raw seed where reproducible | T+1 open | R01 V2 | upstream failure inheritance |
| `ep2_detector_probe_with_simple_stop_bridge` | EP2 detector bridge | EP2 schedule | EP2 stop | EP2 control |
| `matched_random_same_density_same_fail_fast_h20_report_only` | matched random pseudo-events | matched entry | same deterministic | audit-only |
| `matched_random_same_density_no_fail_fast_h20_report_only` | matched random pseudo-events | matched entry | no | audit-only |

### 10.1 Matched-Delay Structural Reference Policy

For T+1 / T+3 baselines on the same cooling-qualified rows:

```text
Use original emitted seed structural references:
  seed_day_low
  breakout_reference
  pivot_low_10d

Only entry_date and entry_price are shifted.
Do not recompute a fresh breakout, pivot, or seed-day low after the shifted entry date.
```

If no valid stop or risk distance outside `[2%, 12%]`:

```text
mark baseline row as ineligible
do not silently drop
```

Important:

```text
same_cooling_qualified_seed_t1_open_same_fail_fast_h20 is a same-sample counterfactual.
It conditions on the fact that the row later passed T+1 cooling and was executable at T+2.
It is not a standalone executable strategy and must not be used alone to claim total entry improvement.

same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted is the executable total-effect bridge.
It includes emitted seeds before cooling cancellation and is required to show whether
cooling + T+2 entry improves the full emitted-seed sleeve relative to immediate T+1 entry.
```

### 10.2 Matched-Delay Reliability

Required diagnostics:

```text
shift_period_return_pct = shifted_entry_price / candidate_entry_price - 1
matched_delay_ineligible_rate by shift_period_return_pct quintile and top_20pct_delay_return bucket
```

Reliability fails if top delay-return quintile has both:

```text
top_quintile_ineligible_rate >= 2.0 * all_delay_ineligible_rate
and top_quintile_ineligible_rate >= 0.20
```

Matched-delay reliability is a hard gate for same-fail-fast T+3 comparison.

### 10.3 Matched-Random Baseline

Matched-random remains audit-only in R01.1. It must be fully materialized and reported, but:

```text
matched-random evidence cannot make R01.1 pass；
matched-random evidence cannot make R01.1 fail。
```

Matched-random construction must be mechanical:

```text
bucket_edges_source = train split only
bucket_fields:
  - split
  - industry_bucket
  - liquidity_bucket
  - volatility_bucket
  - calendar_year
target_density = candidate cooling-qualified probe entry density by bucket
sampling_universe =
  PIT eligible stock-days in the same bucket
  excluding all EP4 raw_seed / emitted_seed / cooling-qualified candidate stock-days
  excluding rows without matched entry / forward / structural-reference availability
replacement_policy = no_replacement
capacity_shortfall_policy =
  keep available rows only
  record random_capacity_shortfall = requested_count - sampled_count
  set random_baseline_reliability_status = failed if any validation bucket shortfall share > 20%
random_seed = fixed in config and manifest
```

Required matched-random fields:

```text
random_signal_date
random_entry_date
random_bucket_id
random_requested_count
random_sampled_count
random_capacity_shortfall
random_sampling_replacement_policy
random_baseline_reliability_status
primary_metric_eligible_baseline_event
baseline_failed_seed_primary
```

---

## 11. Recall Contract

R01.1 must report recall at four layers.

| Recall basis | Definition | Gate use |
|:--|:--|:--|
| `raw_seed_primary_recall` | raw R01 V2 stock-day / episode recall before emission | report-only |
| `emitted_seed_primary_recall_pre_cooling` | emitted seed recall before cooling cancellation | report-only / waterfall |
| `cooling_qualified_probe_primary_recall` | cooling-passed and executable probe episode recall | headline recall gate |
| `fail_fast_survived_probe_primary_recall` | captured reference events for which at least one capturing probe survives fail-fast through H20 natural exit | recall no-harm gate |

Primary recall window:

```text
seed / probe is counted as captured if the relevant episode starts within:
  [reference_date - 20 trading days, reference_date]
```

Execution timing audit:

```text
R01.1 primary recall remains seed-start recall, not executed-entry-before-reference recall.
Because cooling entry buys at T+2 open, a seed with episode start on reference_date
can be counted as seed recall while its entry occurs after the reference date.

The implementation must therefore report:
  entry_after_reference_count
  entry_after_reference_share
  captured_reference_count_with_entry_on_or_before_reference
  captured_reference_count_with_entry_after_reference

These fields are audit-only and cannot change primary recall,
but the final report must not describe post-reference entries as pre-reference executable capture.
```

Sensitivity windows, report-only:

```text
[-20, +10]
[-10, +5]
[-20, +20]
```

Late captures rule:

```text
episodes starting after reference_date do not contribute to:
  primary recall numerator
  added_capture_vs_ep2_count
  recall_cost_score
```

### 11.1 Recall Waterfall

The final report must include:

```text
raw_seed_captured_reference_count
emitted_seed_pre_cooling_captured_reference_count
cooling_qualified_probe_captured_reference_count
fail_fast_survived_captured_reference_count

raw_to_emitted_capture_loss
emitted_to_cooling_capture_loss
cooling_to_fail_fast_survival_loss
```

Hard recall no-harm gates:

```yaml
cooling_qualified_probe_primary_recall_diff_vs_ep2_detector: >= -0.05
cooling_qualified_probe_bridge_recall_diff_vs_ep2_detector: >= -0.05
emitted_to_cooling_recall_loss_rate: <= 0.15
fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast: <= 0.15
```

Formula:

```text
emitted_to_cooling_recall_loss_rate =
  1 - cooling_qualified_probe_captured_reference_count
      / max(1, emitted_seed_pre_cooling_captured_reference_count)
```

---

## 12. Cost and Payoff Metrics

R01.1 does not use AUC as a primary metric.

### 12.1 Failed Seed Definition

Headline failed seed:

```text
failed_seed_primary =
  executable cooling-qualified probe episode
  that does not capture any primary big-winner reference event
  under the primary recall window [-20, 0],
  and primary_metric_eligible_seed_episode = true.
```

Rows with incomplete forward window:

```text
primary_metric_eligible_seed_episode = false
failed_seed_primary = not_applicable
```

### 12.2 Required Cost Metrics

- `failed_seed_average_loss_r`
- `failed_seed_median_loss_r`
- `failed_seed_p05_return_r`
- `failed_seed_median_holding_days`
- `exposure_days_per_probe_episode`
- `loss_r_per_captured_big_winner_seed`
- `exposure_days_per_captured_big_winner_seed`
- `incremental_loss_r_per_added_big_winner_vs_ep2`
- `incremental_exposure_days_per_added_big_winner_vs_ep2`
- `cooling_cancelled_count`
- `cooling_cancelled_big_winner_capture_loss_count`
- `cooling_cancelled_failed_seed_avoidance_count`

### 12.3 Required Payoff Shape Metrics

- `mean_return_r`
- `median_return_r`
- `p05_return_r`
- `p95_return_r`
- `payoff_skew`
- `positive_return_rate`
- `right_tail_contribution_share`
- `return_r_diff_vs_r01_v2_raw_bridge`
- `failed_loss_r_diff_vs_r01_v2_raw_bridge`

### 12.4 Risk-Pct Quintile Cost-Control Contract

`risk_pct_quintile_cost_control_status` is a hard validation gate and must be reproducible.

Construction:

```text
quintile_edge_source = train split cooling-qualified candidate probes
quintile_field = initial_risk_pct
quintile_edges are frozen from train and applied unchanged to validation / robustness
rows with initial_risk_pct outside [2%, 12%] are ineligible probes, not quintile members
```

Validation pass rule:

```text
For each validation risk_pct quintile with >= 30 primary_metric_eligible_seed_episode rows:
  failed_seed_average_loss_r_diff_vs_same_cooling_qualified_seed_no_fail_fast <= 0
  and p05_return_r_diff_vs_same_cooling_qualified_seed_no_fail_fast >= -0.03

For quintiles with < 30 eligible rows:
  mark risk_pct_quintile_sample_status = insufficient
  exclude from hard pass / fail aggregation
  report row count and metrics anyway

risk_pct_quintile_cost_control_status = passed only if:
  all sufficient validation quintiles pass
  and at least 3 validation quintiles are sufficient
```

Required output fields:

```text
risk_pct_quintile
risk_pct_quintile_edge_low
risk_pct_quintile_edge_high
eligible_probe_count
failed_seed_average_loss_r_diff_vs_no_fail_fast
p05_return_r_diff_vs_no_fail_fast
risk_pct_quintile_sample_status
risk_pct_quintile_pass_status
```

---

## 13. Report-Only Diagnostics

### 13.1 VCP / Volatility Compression Audit

VCP is not part of the R01.1 main seed.

R01.1 must report:

```text
boll20_width_asof_t_minus_1
boll20_width_ratio_vs_60d_median
atr20_pct_asof_t_minus_1
atr20_pct_ratio_vs_60d_mean
vcp_boll_width_bucket
vcp_atr_compression_bucket
```

By bucket, report:

```text
raw_seed_count
emitted_seed_count
cooling_qualified_probe_count
primary_recall
failed_seed_average_loss_r
p05_return_r
matched_delay_t3_mean_diff
cooling_cancel_rate
false_reject_winner_rate
```

Hard boundary:

```text
VCP audit cannot change the R01.1 main seed, cannot create a pass, and cannot create a stop.
```

### 13.2 Continuous Confirmation Audit

R01.1 must report but not gate:

```text
cooling_close_above_breakout_reference
cooling_close_above_ma5
two_of_three_closes_above_breakout_reference_over_T_minus_1_to_T_plus_1
two_of_three_closes_above_ma5_over_T_minus_1_to_T_plus_1
```

### 13.3 T+10 False-Reject Audit

R01.1 must continue to report:

```text
false_reject_winner =
  probe episode exited by deterministic fail-fast
  and still linked to a primary big-winner reference event

missed_failure =
  probe episode not exited by deterministic fail-fast
  and failed_seed_primary = true
  and H20 after-cost return < 0
```

Additional R01.1 fields:

```text
false_reject_trigger_type
t10_only_false_reject_winner
post_exit_5d_recovery_above_entry
post_exit_10d_recovery_above_entry
post_exit_20d_recovery_above_entry
post_exit_max_drawdown_20d
post_exit_max_favorable_return_20d
```

### 13.4 Cooling Cancellation Audit

Required:

```text
cooling_cancelled_count
cooling_cancelled_rate
cooling_cancel_reason_distribution
cooling_cancelled_primary_big_winner_capture_loss_count
cooling_cancelled_lost_reference_ids
cooling_cancelled_h20_counterfactual_return_r
cooling_cancelled_counterfactual_failed_seed_loss_avoided
```

---

## 14. Proceed / Stop Gates

R01.1 decision must be reproducible from the allowed decision set. It must not output vague labels such as `promising`.

### 14.1 Hard Fail Gates

Any failure -> `stop_ep4_r01_1_path` unless explicitly mapped to archive.

```yaml
authority_inputs_status: passed
r01_v2_inheritance_status: passed
raw_seed_formula_status: exact_r01_v2_formula
emission_rule_status: deterministic_20d_no_validation_selection
cooling_entry_rule_status: deterministic_t1_observe_t2_open_no_validation_selection
tradability_filter_status: passed
validation_threshold_selection_status: no_selection_from_validation
candidate_emitted_seed_day_rate_train: <= min(0.045, 2.7 * ep2_seed_day_rate_train)
candidate_emitted_seed_day_rate_validation: <= min(0.045, 2.7 * ep2_seed_day_rate_validation)
candidate_probe_entry_day_rate_train: <= min(0.045, 2.7 * ep2_seed_day_rate_train)
candidate_probe_entry_day_rate_validation: <= min(0.045, 2.7 * ep2_seed_day_rate_validation)
candidate_emitted_seed_episode_rate_train: <= 3.0 * ep2_seed_episode_rate_train
candidate_emitted_seed_episode_rate_validation: <= 3.0 * ep2_seed_episode_rate_validation
candidate_probe_entry_episode_rate_train: <= 3.0 * ep2_seed_episode_rate_train
candidate_probe_entry_episode_rate_validation: <= 3.0 * ep2_seed_episode_rate_validation
validation_unique_instrument_years: >= 80
top1_instrument_year_probe_entry_share_validation: <= 0.05
```

### 14.2 Recall No-Harm Gates

All must pass:

```yaml
cooling_qualified_probe_primary_recall_diff_vs_ep2_detector: >= -0.05
cooling_qualified_probe_bridge_recall_diff_vs_ep2_detector: >= -0.05
emitted_to_cooling_recall_loss_rate: <= 0.15
fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast: <= 0.15
```

Recommended but report-only:

```yaml
validation_primary_recall_preferred_minimum: >= 0.22
```

### 14.3 Cost-Control Gates

All must pass in validation:

```yaml
failed_seed_average_loss_r_diff_vs_same_cooling_qualified_seed_no_fail_fast: < 0
failed_seed_median_holding_days_diff_vs_same_cooling_qualified_seed_no_fail_fast: < 0
p05_return_r_diff_vs_same_cooling_qualified_seed_no_fail_fast: >= -0.02
loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector: <= 0
risk_pct_quintile_cost_control_status: passed
```

### 14.4 Entry Timing Repair Gates

R01.1 exists to repair entry timing. Therefore all must pass in validation:

```yaml
total_effect_failed_seed_average_loss_r_diff_vs_same_emitted_seed_t1_open_same_fail_fast_all_emitted: <= 0
total_effect_p05_return_r_diff_vs_same_emitted_seed_t1_open_same_fail_fast_all_emitted: >= -0.02
mean_return_r_diff_vs_same_cooling_qualified_seed_t3_open_same_fail_fast: >= -0.0055
p05_return_r_diff_vs_same_cooling_qualified_seed_t3_open_same_fail_fast: >= -0.02
matched_delay_t3_reliability_status: passed
```

Same-sample T+1 diagnostics are required but report-only:

```yaml
same_sample_failed_seed_average_loss_r_diff_vs_same_cooling_qualified_seed_t1_open_same_fail_fast: report_only
same_sample_p05_return_r_diff_vs_same_cooling_qualified_seed_t1_open_same_fail_fast: report_only
```

Interpretation:

```text
R01.1 does not need to prove T+2 open has positive alpha over all alternatives,
but it must show:
1. cooling + T+2 entry does not worsen the full emitted-seed sleeve vs immediate T+1 entry；
2. T+2 entry is not materially worse than waiting one additional day to T+3。

The same-cooling-qualified T+1 comparison is diagnostic only because it conditions
on later T+1 close cooling survival and therefore is not a standalone executable strategy.
```

### 14.5 Recall-Cost Trade-Off Gate

Validation gates:

```yaml
net_added_capture_vs_ep2_count: > 0
incremental_loss_r_per_added_big_winner_vs_ep2: <= 5.0
incremental_exposure_days_per_added_big_winner_vs_ep2: <= 250
```

Robustness gates:

```yaml
robustness_net_added_capture_vs_ep2_count: > 0
robustness_incremental_loss_r_per_added_big_winner_vs_ep2: <= 7.5
robustness_incremental_exposure_days_per_added_big_winner_vs_ep2: <= 375
```

Robustness recall-cost failure mapping:

```text
If validation recall-cost gates pass but any robustness recall-cost gate fails:
  decision cannot be go_to_r02.

If robustness no-harm gates still pass and validation cost-control / entry-timing gates pass:
  decision = go_to_r02_with_robustness_warning
  only when robustness_net_added_capture_vs_ep2_count >= 0
  and robustness incremental loss / exposure are no worse than 1.25x the robustness thresholds.

If robustness_net_added_capture_vs_ep2_count < 0
or robustness incremental loss / exposure are worse than 1.25x the robustness thresholds:
  decision = stop_ep4_r01_1_path
```

### 14.6 Robustness No-Harm Gates

Robustness must not show severe degradation:

```yaml
robustness_cooling_qualified_probe_primary_recall_diff_vs_ep2_detector: >= -0.10
robustness_failed_seed_average_loss_r_diff_vs_no_fail_fast: <= 0
robustness_p05_return_r_diff_vs_no_fail_fast: >= -0.03
robustness_entry_timing_t3_p05_diff: >= -0.03
robustness_seed_density_cap_status: report_and_warn_if_failed
```

If validation passes but robustness is directionally weaker while still within these no-harm bounds:

```text
decision = go_to_r02_with_robustness_warning only if the robustness recall-cost
failure mapping in Section 14.5 also permits warning.
```

### 14.7 Decision Matrix

| Gate subset | `go_to_r02` | `go_to_r02_with_robustness_warning` | `archive_cost_control_sleeve_no_r02` | `stop_ep4_r01_1_path` |
|:--|:--|:--|:--|:--|
| Hard fail gates | required | required | required except high-recall count preconditions | fail if required hard gate fails |
| Count-vs-EP2 high-recall preconditions | required | required | not required | stop high-recall claim if failed |
| Recall no-harm | required | required | archive threshold required | fail if below required threshold |
| Cost-control | required | required | required | fail if cost-control fails |
| Entry timing repair | required | required | p05 / loss repair required | fail if materially worse |
| Recall-cost trade-off | required | required | not required | fail high-recall claim if absent |
| Robustness no-harm | required | required with warning | required no severe degradation | fail if severe degradation |
| VCP / confirmation audit | report-only | report-only | report-only | cannot determine decision |
| Matched-random reliability | report-only | report-only | report-only | cannot determine decision |

Allowed decisions:

```text
go_to_r02
go_to_r02_with_robustness_warning
archive_cost_control_sleeve_no_r02
stop_ep4_r01_1_path
```

### 14.8 Archive Decision Contract

`archive_cost_control_sleeve_no_r02` is allowed only when R01.1 fails as a high-recall bridge
but still proves a bounded cost-control sleeve worth recording.

All archive conditions must hold:

```yaml
authority_inputs_status: passed
r01_v2_inheritance_status: passed
raw_seed_formula_status: exact_r01_v2_formula
emission_rule_status: deterministic_20d_no_validation_selection
cooling_entry_rule_status: deterministic_t1_observe_t2_open_no_validation_selection
validation_threshold_selection_status: no_selection_from_validation
tradability_filter_status: passed
validation_unique_instrument_years: >= 80
cost_control_gates_status: passed
entry_timing_total_effect_gate_status: passed
robustness_no_harm_status: passed
cooling_qualified_probe_primary_recall_diff_vs_ep2_detector: >= -0.15
cooling_qualified_probe_bridge_recall_diff_vs_ep2_detector: >= -0.15
```

At least one high-recall bridge condition must fail:

```yaml
candidate_probe_entry_day_count_vs_ep2_ratio_validation: < 1.0
or candidate_probe_entry_episode_count_vs_ep2_ratio_validation: < 1.0
or net_added_capture_vs_ep2_count: <= 0
or cooling_qualified_probe_primary_recall_diff_vs_ep2_detector: < -0.05
```

Archive is forbidden and decision must be `stop_ep4_r01_1_path` if any of the following is true:

```yaml
cost_control_gates_status: failed
entry_timing_total_effect_gate_status: failed
robustness_no_harm_status: failed
emitted_to_cooling_recall_loss_rate: > 0.30
fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast: > 0.30
```

---

## 15. Required Artifacts

Implementation must write all artifacts under:

```text
ep4/outputs/r01_1_emission_throttled_cooling_entry_probe_fail_fast/
```

### 15.1 Manifest

```text
manifests/r01_1_run_manifest.json
```

Required fields:

```text
phase
requirement_id
config_hash
git_commit_if_available
data_max_date
configured_split_windows
effective_reference_windows
raw_seed_formula_id
emission_rule_id
cooling_entry_rule_id
fail_fast_family_id
cost_model_source
selection_policy_status
final_decision
```

### 15.2 Seed Panels

```text
cache/r01_1_raw_seed_panel.parquet
cache/r01_1_emitted_seed_panel.parquet
cache/r01_1_cooling_entry_panel.parquet
```

Required columns include:

```text
instrument
raw_signal_date
emitted_signal_date
cooling_observation_date
entry_date
raw_seed_flag
emitted_seed_flag
emission_suppressed
suppressed_by_emitted_seed_id
cooling_cancelled
cooling_cancel_reason
entry_buy_executable
seed_day_low
breakout_reference
pivot_low_10d
money_ratio20
money_ratio5
rps5
boll20_pct_b
close_near_high10
split
```

### 15.3 Simulation Panels

```text
cache/r01_1_probe_simulation_panel.parquet
cache/r01_1_baseline_simulation_panel.parquet
```

Required candidate simulation columns:

```text
simulation_id
seed_episode_id
emitted_seed_id
instrument
emitted_signal_date
cooling_observation_date
entry_date
entry_price
initial_probe_risk_budget_r
initial_structural_stop
initial_risk_pct
exit_trigger_type
exit_signal_date
exit_execution_date
exit_price
sell_blocked_day_count
terminal_blocked_exit
gross_return_pct
after_cost_return_pct
return_r
loss_r
holding_days
exposure_days
primary_metric_eligible_seed_episode
captures_primary_big_winner
captured_reference_event_id
entry_after_reference
entry_after_reference_days
failed_seed_primary
failed_seed_label_a_h10_u1_5
failed_seed_label_a_h20_u2_0
failed_seed_h20_negative
failed_seed_fail_fast_triggered
split
```

Required baseline simulation columns:

```text
baseline_id
baseline_event_id
source_candidate_seed_episode_id
instrument
signal_date
entry_date
entry_price
initial_structural_stop
initial_risk_pct
baseline_entry_shift_trading_days
baseline_ineligible
baseline_ineligible_reason
primary_metric_eligible_baseline_event
baseline_captures_primary_big_winner
baseline_captured_reference_event_id
baseline_failed_seed_primary
exit_trigger_type
exit_signal_date
exit_execution_date
exit_price
sell_blocked_day_count
terminal_blocked_exit
gross_return_pct
after_cost_return_pct
return_r
loss_r
holding_days
exposure_days
split
```

Baseline eligibility rule:

```text
primary_metric_eligible_baseline_event must use the same effective_reference_end
and forward-window availability policy as primary_metric_eligible_seed_episode.
Ineligible baseline rows must remain materialized and must not be silently dropped
from denominator, reliability, or gate diagnostics.
```

### 15.4 Reports

Required reports:

```text
reports/r01_1_final_report.md
reports/r01_1_gate_audit.csv
reports/r01_1_density_audit.csv
reports/r01_1_raw_to_emitted_waterfall.csv
reports/r01_1_cooling_entry_waterfall.csv
reports/r01_1_recall_bridge.csv
reports/r01_1_entry_after_reference_audit.csv
reports/r01_1_recall_cost_tradeoff.csv
reports/r01_1_fail_fast_attribution.csv
reports/r01_1_false_reject_missed_failure_audit.csv
reports/r01_1_entry_timing_audit.csv
reports/r01_1_r_unit_distribution_audit.csv
reports/r01_1_risk_pct_quintile_cost_control.csv
reports/r01_1_baseline_eligibility_audit.csv
reports/r01_1_vcp_audit.csv
reports/r01_1_confirmation_audit.csv
reports/r01_1_matched_delay_reliability_audit.csv
reports/r01_1_matched_random_reliability_audit.csv
reports/r01_1_archive_decision_audit.csv
reports/r01_1_counterfactual_failure_inheritance.csv
```

### 15.5 Final Report Required Sections

`r01_1_final_report.md` must include:

1. R01.1 phase boundary；
2. upstream R01 V2 failure inheritance；
3. raw seed formula and proof it matches R01 V2；
4. emission throttle definition and density waterfall；
5. cooling entry definition and cancellation waterfall；
6. big-winner reference set definition and effective windows；
7. primary / bridge recall by raw, emitted, cooling-qualified, fail-fast-survived layers；
8. entry-after-reference audit and why primary recall is seed-start recall；
9. density denominators and EP2 comparison；
10. risk normalization and R-unit distribution；
11. fail-fast vs no-fail-fast attribution；
12. entry timing repair evidence vs T+1 and T+3；
13. recall-cost trade-off vs EP2；
14. VCP audit and why it is not used as a hard gate；
15. continuous confirmation audit and why it is not used as a hard gate；
16. matched-delay and matched-random evidence；
17. allowed decision and full gate evidence；
18. archive decision audit if high-recall bridge fails but cost-control passes；
19. what R02 is allowed to assume if R01.1 passes；
20. what R02 is not allowed to assume；
21. if stopped, counterfactual failure inheritance and next proposed repair。

---

## 16. Validator Contract

Implementation must add:

```text
ep4/scripts/run_r01_1_emission_throttled_cooling_entry_probe_fail_fast.py
ep4/scripts/validate_r01_1_emission_throttled_cooling_entry_probe_fail_fast.py
```

Validation command:

```bash
uv run python ep4/scripts/validate_r01_1_emission_throttled_cooling_entry_probe_fail_fast.py
```

Validator must fail closed if:

- any canonical input is missing；
- R01 V2 requirement / report / manifest cannot be read；
- EP2 manifest / config / launch pool cannot be read；
- PIT universe is not point-in-time daily membership with `date` and `instrument`；
- raw seed formula differs from R01 V2 five-condition formula；
- emission throttle is not exactly deterministic 20D recursive same-instrument emission；
- emission throttle resets at train / validation / robustness split boundaries；
- emitted seeds are merged into multi-emission seed episodes instead of one emitted seed per episode；
- cooling entry is not exactly T+1 observe / T+2 open；
- cooling cancellation uses any condition not listed in config；
- fail-fast includes trained model output；
- fail-fast is not entry-relative；
- `entry_relative_day_10_close_below_entry_price` is missing or signal-relative instead of entry-relative；
- probe includes add, scale-in, portfolio sizing, ATR trailing stop, state stop, or profit giveback；
- validation / robustness is used for threshold selection；
- primary reference set is empty；
- effective reference windows are missing；
- primary recall or failed-seed gates include rows after effective reference end；
- entry-after-reference audit fields are missing or post-reference entries are described as pre-reference executable capture；
- raw / emitted / cooling-qualified recall layers are not separately reported；
- density caps are evaluated on raw seed only and not on emitted / probe-entry layers；
- train and validation emitted / probe-entry day-rate and episode-rate gates are not all evaluated；
- emitted or probe-entry density denominators cannot be reproduced；
- candidate is not compared to EP2 detector；
- count-vs-EP2 preconditions are ignored when claiming high-recall pass；
- cooling-cancelled rows are silently dropped；
- same-sample T+1 counterfactual is reported as a standalone executable strategy；
- same-sample T+1 counterfactual is used as the primary hard entry-timing gate instead of the full emitted-sleeve total-effect bridge；
- total-effect bridge `same_emitted_seed_t1_open_same_fail_fast_h20_all_emitted` is missing from entry-timing evidence；
- T+1 / T+3 matched baselines recompute fresh structural references；
- matched-delay ineligible rows are silently dropped；
- matched-random audit baselines are missing；
- matched-random sampling universe, bucket edges, candidate-stock-day exclusion, no-replacement policy, or capacity shortfall fields are missing；
- baseline eligibility fields are missing or use a different effective-reference policy from candidate eligibility；
- risk_pct_quintile_cost_control_status is missing, uses validation-selected edges, or lacks sufficient-quintile sample checks；
- archive decision is emitted without satisfying the explicit archive decision contract；
- robustness recall-cost failure is mapped to `go_to_r02` instead of warning or stop under the explicit failure mapping；
- VCP or continuous confirmation audit changes any main seed, entry, gate, or decision；
- `loss_r` is signed instead of positive magnitude；
- required report-only diagnostics are missing；
- final decision is not exactly one of the allowed decision labels。

---

## 17. R02 Handoff Contract

If R01.1 decision is:

```text
go_to_r02
```

or:

```text
go_to_r02_with_robustness_warning
```

then R02 may assume only:

```text
1. raw seed formula is frozen；
2. emission-throttled seed is frozen；
3. cooling entry is frozen；
4. small probe observation right has controlled failed-seed cost；
5. deterministic fail-fast is fixed；
6. R01.1 survived cooling-qualified probe episodes can be used as the only R02 continuation / add eligibility universe。
```

R02 may not assume:

```text
1. R01.1 seed is a profitable standalone strategy；
2. R01.1 fail-fast is optimal；
3. T+10 false rejects are solved；
4. VCP has proven hard-gate value；
5. continuous confirmation has proven hard-gate value；
6. surviving episodes are worth adding；
7. ATR stop or state stop has proven value；
8. portfolio-level risk budget is solved。
```

If R01.1 decision is:

```text
archive_cost_control_sleeve_no_r02
```

or:

```text
stop_ep4_r01_1_path
```

R02 must not start unless a new requirement explicitly changes the EP4 direction.

---

## 18. Summary

R01.1 的正确名字不是：

```text
better entry model
```

也不是：

```text
VCP seed optimization
```

而是：

```text
Emission-Throttled Cooling Probe Cost-Control
```

它只证明一个问题：

```text
在 R01 V2 raw seed 已经有 recall-cost 正向证据但未通过 hard gates 的前提下，
用 deterministic emission throttle 降低 seed-day density，
用 deterministic cooling entry 修复 T+1 open 追高，
是否能让“买右尾观察权”这件事达到 R01 可进入 R02 的标准。
```

通过标准不是 AUC，不是更高 precision，也不是单纯 recall。

通过标准是：

```text
raw seed 不变；
emission 和 cooling 都无 validation selection；
density 过关；
entry timing 不再明显早；
recall 不被明显伤害；
fail-fast 成本控制仍成立；
每新增 / 保留一个 big-winner observation right 的试错成本仍可解释；
R02 handoff 只使用 survived cooling-qualified probe episodes。
```
