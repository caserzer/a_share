# EP4 Requirement 01 V3：Post30 Profile Seed + Probe + Fail-Fast

> Requirement id: `ep4_r01_high_recall_probe_fail_fast_v3_post30_profile_seed`
> Status: implementation-ready requirement
> Scope: EP4-R01 V3，只把 post-reference candidate entry seed 固定为 `close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60`，重新验证 reference 后 T+0..T+30 executable entry capture 和 deterministic fail-fast 成本控制
> Authoritative discussion: `ep4/discussion.md`
> Date: 2026-05-12

V3 note:

```text
This is a frozen-seed rerun of R01. All phase boundaries, execution rules,
probe sizing, execution conventions, and validator fail-closed behavior remain
inherited from R01 unless explicitly overridden below. V3 explicitly overrides
the candidate seed with the frozen T+0..T+30 post-reference big-winner profile
condition found by `r01_big_winner_post30_indicator_search_v1`, keeps the T+10
entry-price fail-fast trigger, and keeps matched-random baselines as audit-only
diagnostics.
```

---

## 1. Purpose

EP4 的研究问题已经从“提前预测 120 日涨 50%”改成“经营右尾 episode”。V3 明确不再追求在 launch day / reference_date 之前捕捉 winner。它只验证一个更后置、更可执行的最小命题：

```text
在 canonical big-winner reference_date 之后的 T+0..T+30 内，
如果同一股票出现 frozen post30 profile seed，
是否可以用小 probe 仓位和 deterministic fail-fast，
以可接受失败成本捕捉已经进入右尾展开期的 entry opportunity？
```

R01 不是完整策略，不证明加仓，不证明动态退出，也不证明组合层收益。它只回答：

```text
reference 后确认型 entry capture 是否足够可执行、足够低成本。
```

如果 V3 不能成立，EP4 不应把 post-reference profile seed 交给 R02 做持有、加仓或动态管理；因为后续动作都建立在“reference 后 entry capture 成本可控且不显著劣于 EP2 control”的前提上。

---

## 2. Phase Boundary

R01 必须保持最小自由度。完成本 requirement 以前，不允许：

- 训练 entry / ranking / fail-fast / continuation / exit 模型；
- 使用 Label B 训练 Early Failure Detector；
- 引入 staged add / confirm add / scale-in；
- 引入 ATR trailing stop、state stop、profit giveback 或复杂 dynamic exit；
- 做 portfolio optimizer、行业风险预算、主题集中度控制或 capital allocation；
- 用 validation / robustness 结果反向选择 seed 阈值、fail-fast 规则、exit horizon 或 recall gate；
- 用 `future_50h120` 直接训练 entry 模型；
- 宣称 R01 是可交易策略。

Allowed use:

```text
train split:
  冻结 seed 规则、density 上限、deterministic fail-fast 规则和 baseline 构造。

validation / robustness:
  只报告冻结规则的结果，不能重新选阈值。
```

R01 可以报告 Label A / Label B / Label D 的 audit 切片，但这些 label 只能用于解释，不得用于训练或阈值选择。

V3 seed provenance caveat:

```text
The frozen V3 seed comes from a post-reference T+0..T+30 profile search. That
search proves only that the condition frequently co-occurs after canonical
big-winner reference dates. It does not prove that the report artifact itself is
an executable signal source. R01 V3 must therefore rebuild the frozen condition
from PIT daily bars and validate it under the executable T+0..T+30 entry capture,
density, matched-delay, and fail-fast gates. The final report must separate
post30 profile-search provenance from actual primary executable entry capture
under `[reference_date + 1, reference_date + 30]`.
```

---

## 3. Upstream Facts To Preserve

R01 必须继承 EP2 / EP3 已经证明和失败的边界。

### 3.1 EP2 Facts

EP2 已经冻结一个可复现 launch observation pool：

```yaml
launch_detector_version: EP2_LAUNCH_DETECTOR_V0
detector_id: EP2_LAUNCH_DETECTOR_V0_PRICE60_MONEY20
detector_family: price_breakout_money_surge
primary_label_id: confirm_h10_u10_d06_conservative_fail
baseline_schedule_id: probe_with_simple_stop
```

R01 必须把 `EP2_LAUNCH_DETECTOR_V0` 作为 baseline / control，而不是默认替换它。

EP2 的意义：

```text
broad launch detector + short-horizon probe timing 在短周期 exposure timing 上成立；
但它没有证明 long-horizon winner holding 或右尾 episode 管理成立。
```

### 3.2 EP3 Facts

EP3 证明 lifecycle / anchor 形态不能只看 trigger rate 或 recall：

```text
形态 recall 不等于 forward lift；
trigger rate 不等于 payoff edge；
matched-delay baseline 和 tail risk 必须作为主验证对象。
```

因此，R01 的任何 post-reference entry capture 结论都必须同时报告：

```text
matched-delay baseline diff
matched-random baseline diff as audit-only diagnostic evidence
p05 / tail no-harm
seed density / universe coverage
```

---

## 4. Canonical Inputs

R01 的实现只能使用以下输入。

| Input | Required path | Role |
|:--|:--|:--|
| EP4 discussion | `ep4/discussion.md` | requirement 背景和阶段边界 |
| EP2 engineering baseline manifest | `ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json` | EP2 frozen authority |
| EP2 engineering baseline config | `ep2/engineering_baseline/config.yaml` | cost model / execution convention source |
| EP2 launch observation pool | `ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet` | EP2 detector baseline / bridge denominator |
| EP2 launch episode dictionary | `ep2/engineering_baseline/outputs/reports/ep2_launch_episode_dictionary.csv` | EP2 episode semantics |
| EP2 label freeze candidate | `ep2/engineering_baseline/outputs/reports/ep2_label_freeze_candidate.csv` | Label A bridge audit |
| EP2 baseline freeze audit | `ep2/outputs/requirement_01_label_and_baseline_freeze/reports/requirement_01_baseline_freeze_audit.csv` | `probe_with_simple_stop` reference |
| Local PIT Qlib OHLCV provider | `data/qlib/cn_data_pit` | R01 seed / execution / forward audit |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | trading-day horizon |
| PIT daily universe membership | `data/universe/pit_mcap500_mainboard_daily.csv` | point-in-time tradable denominator |
| PIT qlib instrument map | `data/universe/pit_qlib_instrument_universe.csv` | instrument-code mapping and provider audit |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | audit-only industry decomposition |
| Qlib PIT instrument file | `data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt` | provider instrument-date coverage authority |

Seed provenance artifact, not an execution input:

```text
ep4/outputs/r01_big_winner_post30_indicator_search_v1/reports/post30_condition_search_v1_report.md
```

The implementation may cite this artifact to explain why the V3 seed was frozen,
but it must not read the post30 row-level outputs during the R01 V3 run, tune any
threshold, or use post-reference coverage as a substitute for executable primary
recall.

Seed provenance leakage caveat:

```text
The current post30 search artifact selected the V3 seed from all canonical R01
primary winners across train, validation, and robustness splits. Therefore V3 is
not a clean OOS validation of seed discovery. It is a hypothesis-confirmation
rerun of a frozen all-split-discovered post-reference profile. Unless a future
requirement proves the same seed was selected using train-only discovery, V3
cannot output `go_to_r02` or `go_to_r02_with_robustness_warning`.
```

Forbidden inputs:

- EP2 R02 / R03 / R04 / R05 model, schedule, holding policy outputs；
- EP3 candidate anchor / rolling state action outputs as seed inputs；
- Explore9 / Explore10 row-level outputs；
- any new Tushare / AkShare fetch；
- any manual survivor list or ex-post stock list。

Hard rule:

```text
R01 的 big-winner denominator 必须从 PIT universe + local PIT OHLCV 重新构造；
不得使用 survivor-biased ex-post list。
```

---

## 5. Required Config

The implementation must add:

```text
ep4/configs/r01_high_recall_probe_fail_fast_v3.yaml
```

Minimum required config:

```yaml
phase: ep4_r01_high_recall_probe_fail_fast_v3_post30_profile_seed
requirement_path: ep4/requirement_01_high_recall_probe_fail_fast_v3.md
output_root: ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed

upstream_ep2:
  manifest: ep2/engineering_baseline/outputs/manifests/ep2_engineering_baseline_manifest.json
  config: ep2/engineering_baseline/config.yaml
  launch_pool: ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet
  episode_dictionary: ep2/engineering_baseline/outputs/reports/ep2_launch_episode_dictionary.csv
  label_freeze_candidate: ep2/engineering_baseline/outputs/reports/ep2_label_freeze_candidate.csv
  baseline_freeze_audit: ep2/outputs/requirement_01_label_and_baseline_freeze/reports/requirement_01_baseline_freeze_audit.csv

data_sources:
  qlib_provider_uri: data/qlib/cn_data_pit
  trading_calendar_path: data/qlib/cn_data_pit/calendars/day.txt
  pit_universe_path: data/universe/pit_mcap500_mainboard_daily.csv
  pit_qlib_instrument_universe_path: data/universe/pit_qlib_instrument_universe.csv
  pit_industry_path: data/targets/pit_industry_membership.csv
  qlib_instrument_path: data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt

split:
  train_start: "2017-07-04"
  train_end: "2021-12-31"
  validation_start: "2022-01-01"
  validation_end: "2023-12-31"
  robustness_start: "2024-01-01"
  robustness_end: "2025-12-31"
  split_date_field: signal_date
  gate_split_date_field: entry_execution_date
  effective_reference_window_policy: min(split_end_minus_primary_entry_capture_window_minus_probe_observation_window, data_max_date_minus_max_forward_or_probe_window)
  manifest_must_record_effective_reference_windows: true
  split_boundary_policy:
    seed_formula_split_field: signal_date
    headline_gate_split_field: entry_execution_date
    require_terminal_exit_within_configured_split_for_headline_gates: true
    cross_split_execution_rows: report_only
    max_probe_observation_horizon_trading_days: natural_exit_horizon_plus_max_exit_retry

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

density_denominator:
  seed_day_denominator: pit_executable_stock_days
  seed_episode_denominator: eligible_instrument_years
  eligible_stock_day_requires:
    - pit_universe_member
    - next_open_buy_executable
    - has_required_history_for_seed_formula
    - not_suspended_or_dirty_bar
  eligible_instrument_year_requires_min_stock_days: 120

seed_recall:
  primary_recall_lookback_days: 0
  primary_recall_forward_days: 30
  primary_recall_window_id: primary_0_30

entry_capture:
  primary_entry_capture_window_id: primary_entry_1_30
  schema_compat_recall_window_id: primary_0_30
  schema_compat_fields_are_not_prelaunch_recall: true
  schema_compat_seed_recall_fields_must_use_entry_execution_date: true
  primary_capture_timestamp_field: entry_execution_date
  primary_gate_must_not_use_signal_date: true
  seed_recall_fields_forbidden_timestamp_fields:
    - signal_date
    - episode_start_signal_date
  baseline_capture_timestamp_fields:
    matched_delay: baseline_entry_execution_date
    ep2_bridge: ep2_bridge_entry_execution_date
  headline_gate_requires_terminal_exit_within_split: true

capture_time_basis:
  primary_capture_basis: entry_execution_date
  signal_capture_basis: report_only
  entry_rule: next_open_after_signal
  primary_entry_capture_window:
    start_offset_from_reference_trading_days: 1
    end_offset_from_reference_trading_days: 30
  implied_signal_window:
    start_offset_from_reference_trading_days: 0
    end_offset_from_reference_trading_days: 29
  signal_only_not_entry_within_window_must_report: true

seed_provenance_gate:
  discovery_artifact: ep4/outputs/r01_big_winner_post30_indicator_search_v1/reports/post30_condition_search_v1_report.md
  discovery_scope: all_splits
  validation_oos_clean: false
  discovery_scope_must_be_train_only_for_go_to_r02: true
  if_discovery_scope_not_train_only:
    max_research_decision: go_to_oos_retest_required
    allow_decisions:
      - go_to_oos_retest_required
      - archive_hypothesis_no_r02
      - stop_ep4_r01_path
  final_report_must_state_oos_status: true

density_provenance:
  post30_search_eligible_day_density: 0.0791
  r01_full_universe_seed_day_density: computed_in_r01_v3_run
  denominator_comparison_policy: report_separately_do_not_compare_as_same_denominator

seed_rules:
  baseline_seed_id: ep2_launch_detector_v0_bridge
  candidate_seed_id: ep4_post30_profile_high5_volume_rps_seed_v0
  candidate_seed_formula_id: close_near_high5_gt_0pct_and_vol_ratio10_gt_1_2_and_vol_ratio3_gt_1_2_and_rps5_gt_60
  candidate_seed_components_v3:
    volume_activity:
      vol_ratio10:
        denominator: prior_10_trading_day_mean_volume
        threshold: 1.2
        comparison: ">"
      vol_ratio3:
        denominator: prior_3_trading_day_mean_volume
        threshold: 1.2
        comparison: ">"
    relative_strength:
      lookback_trading_days: 5
      cross_section_percentile_threshold: 0.60
      comparison: ">"
    price_structure:
      close_near_high5:
        rolling_close_high_window: 5
        threshold: 0.0
        operational_rule: close_T >= max(close, T-5..T-1)
    hard_filter_allowed: true
    structural_reference_fields:
      seed_day_low_rule: low_on_signal_date
      pivot_low_10d_rule: min_low_over_signal_date_minus_10_to_minus_1
      breakout_reference_rule: prior_5_trading_day_close_high
      rolling_windows_end: signal_date_minus_1
      invalid_if_reference_not_below_entry: true
  hard_tradability_filters:
    require_pit_universe_member: true
    require_next_open_buy_executable: true
    exclude_st_or_delist_risk: true
    exclude_suspended_or_dirty_bar: true
    exclude_limit_up_unbuyable_next_open: true

seed_density_caps:
  # V3 lowers the inherited R01 seed-day cap by 10%:
  #   max_candidate_seed_day_rate: 0.05 -> 0.045
  #   max_candidate_seed_day_rate_vs_ep2_multiple: 3.0 -> 2.7
  # Episode-density cap remains unchanged.
  max_candidate_seed_day_rate: 0.045
  max_candidate_seed_day_rate_vs_ep2_multiple: 2.7
  max_candidate_episode_rate_vs_ep2_multiple: 3.0
  min_unique_instrument_years_validation: 80

probe:
  entry_rule: next_open_after_signal
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
  if_no_valid_initial_stop: reject_seed_episode
  return_r_formula: initial_probe_risk_budget_r * after_cost_return_pct / initial_risk_pct

execution:
  entry_price: next_open_after_signal
  exit_price: next_open_after_exit_signal
  buy_block_action: reject_seed_episode
  sell_block_action: retry_next_executable_open_until_terminal
  max_exit_retry_trading_days: 20
  terminal_exit_policy: mark_terminal_blocked_and_exit_at_first_executable_open
  cost_model_source: ep2/engineering_baseline/config.yaml
  required_cost_fields:
    - commission_bps
    - stamp_tax_bps
    - slippage_bps
    - buy_block_reason
    - sell_block_reason

fail_fast:
  family_id: deterministic_structure_fail_fast_v0
  max_fail_fast_window_trading_days: 10
  natural_exit_horizon_trading_days: 20
  triggers:
    - close_below_seed_day_low
    - close_below_breakout_reference
    - close_below_pivot_low_10d
    - t10_close_below_entry_price
  exit_rule: next_open_after_trigger
  same_day_trigger_policy: conservative_fail

baselines:
  - same_seed_no_fail_fast_hold_h20
  - same_seed_matched_delay_1d_same_fail_fast_h20
  - same_seed_matched_delay_3d_same_fail_fast_h20
  - same_seed_matched_delay_1d_no_fail_fast_h20
  - same_seed_matched_delay_3d_no_fail_fast_h20
  - matched_random_same_density_same_fail_fast_h20
  - matched_random_same_density_no_fail_fast_h20
  - ep2_detector_probe_with_simple_stop_bridge

matched_controls:
  bucket_freeze_split: train
  bucket_freeze_output: ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed/reports/r01_matched_control_bucket_freeze.csv
  liquidity_field: money_20d_median_asof
  volatility_field: atr20_pct_asof
  bucket_quantiles: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
  missing_bucket_policy: explicit_missing_bucket
  min_train_rows_per_bucket: 30
  random_replicates_per_split: 100
  random_min_split_eligible_rate: 0.80
  random_min_bucket_eligible_rate: 0.60
  random_bucket_min_sampled_events_for_audit: 30
  random_exclude_candidate_seed_stock_days: true
  random_sampling_replacement_policy: without_replacement_within_replicate
  random_capacity_shortfall_policy: report_random_baseline_reliability_only
  matched_delay_gate_variants:
    - same_fail_fast
  matched_delay_audit_variants:
    - no_fail_fast

label_a_atr:
  atr_window: 20
  rolling_windows_end: signal_date_minus_1
  true_range_formula: max(high_low, high_prev_close_abs, low_prev_close_abs)
  entry_price_reference: next_open
  same_day_policy: conservative_fail

selection_policy:
  seed_threshold_policy: literal_frozen_constants_from_config
  train_derived_values_allowed:
    - matched_control_bucket_edges
  validation_threshold_selection_allowed: false
  robustness_threshold_selection_allowed: false

recall_cost_gate:
  max_incremental_loss_r_per_added_big_winner_vs_ep2: 5.0
  max_incremental_exposure_days_per_added_big_winner_vs_ep2: 250
  robustness_max_incremental_loss_r_per_added_big_winner_vs_ep2: 7.5
  robustness_max_incremental_exposure_days_per_added_big_winner_vs_ep2: 375
```

The exact seed thresholds above are frozen literal constants for R01. Train split may be used only to derive matched-control bucket edges and other explicitly named audit bin edges. It must not be used to tune seed thresholds, fail-fast thresholds, exit horizon, density caps, recall gates, or recall-cost gates. If implementation finds a required field unavailable, the run must fail closed and update this requirement before changing the formula.

Two boundaries are intentional:

```text
1. V3 is not "EP2 detector + extra hard RS filter".
   The hard `rps5_T > 0.60` condition is allowed only because it is part of the
   frozen post30 profile seed selected before this R01 V3 run. It must be
   treated as a literal seed component, not as a validation-selected ranking or
   tunable precision filter.

2. R01 reports `return_r` / `loss_r` in episode-normalized full-R units.
   It does not allocate portfolio capital, but it must still define how price
   returns translate into comparable risk units.
```

---

## 6. Big-Winner Reference Set Contract

R01 必须先构造独立的 big-winner reference set，然后才能谈 post-reference entry capture。

### 6.1 Primary Reference

Primary denominator:

```text
big_winner_50h120_close_confirmed
```

定义：

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

If several consecutive dates satisfy forward_return >= 0.50 for the same
instrument, keep only the earliest eligible t, then suppress the next
120 trading days for that instrument.
```

This means R01 measures whether seed episodes appear around the first date from which the later right-tail move became forward-observable under the frozen denominator. It is not anchored to the peak date, target-confirmed date, or an ex-post manually selected launch date.

Hard trading caveat:

```text
reference_date is an ex-post evaluation anchor, not an observable trading state.
The executable signal is the candidate seed itself. The system must scan the
full PIT universe daily for the frozen V3 seed and must not use knowledge that a
stock is inside T+0..T+30 after a canonical reference_date at trading time.
The final report must avoid phrasing such as "buy after reference_date" unless
it is explicitly labelled as retrospective evaluation language.
```

Eligibility:

- `t` 必须在 PIT universe 中；
- `next_open(t)` 必须可买；
- 必须有完整 120 trading-day forward window；
- 停牌、脏 bar、不可复权数据异常必须剔除；
- 同一 instrument 的 positive reference date 按 `dedupe_gap_trading_days = 120` 去重，只保留每段 run 的第一个 reference date。

Effective reference window:

```text
effective_reference_end =
  min(configured_split_end
        - 30 trading days
        - max_probe_observation_horizon_trading_days,
      data_max_date
        - max(120 trading days,
              30 trading days + max_probe_observation_horizon_trading_days))

effective_primary_seed_end =
  effective_reference_end + 30 trading days

effective_gate_entry_end =
  min(effective_primary_seed_end,
      configured_split_end - max_probe_observation_horizon_trading_days)
```

`max_probe_observation_horizon_trading_days` is the maximum trading-day path
needed to observe the R01 probe outcome without crossing the split boundary:

```text
natural_exit_horizon_trading_days + max_exit_retry_trading_days
```

因此 robustness 配置期虽然写到 `2025-12-31`，但主 reference 的实际可用结束日必须由当前本地数据的最大日期、完整 120D forward label window、完整 T+0..T+30 primary entry-capture window、以及完整 probe observation path 共同决定。`r01_run_manifest.json` 必须记录 train / validation / robustness 的 configured window、effective reference window、`effective_primary_seed_end`、`effective_gate_entry_end`、以及 `max_probe_observation_horizon_trading_days`。

Split execution boundary:

```text
signal_date assigns the seed formula row and any signal-time rolling feature.
entry_execution_date assigns headline capture / cost gate split membership.

For a row to enter headline gate metrics:
  entry_execution_date <= effective_gate_entry_end
  and terminal_exit_date <= configured_split_end
  and terminal_exit_date <= data_max_date

Rows whose executable path crosses the configured split boundary are valid
execution diagnostics, but must be marked:
  split_boundary_status = cross_split_execution_report_only
  primary_metric_eligible_seed_episode = false
```

Primary-metric eligibility:

```text
primary_metric_eligible_seed_episode =
  entry_execution_date <= effective_gate_entry_end
  and terminal_exit_date <= configured_split_end
  and terminal_exit_date <= data_max_date
```

All headline metrics that depend on primary 120 trading-day reference labels
must use only `primary_metric_eligible_seed_episode = true` rows:

- primary / bridge post-reference entry capture；
- `failed_seed_primary`；
- capture-cost trade-off；
- fail-fast false-reject / missed-failure audit when the error definition uses
  primary big-winner capture；
- all proceed / stop gates that reference the above metrics。

Boundary policy:

```text
For failed_seed_primary gates:
  include executable seed episodes with entry_execution_date <= effective_gate_entry_end
  and terminal_exit_date <= configured_split_end.

For executable seed episodes with:
  effective_gate_entry_end < entry_execution_date <= effective_primary_seed_end

  do not include them in headline primary capture / cost gates even if they are
  linked to an included effective primary reference event. Mark:
    primary_metric_eligible_seed_episode = false
    boundary_status = cross_split_execution_report_only
    failed_seed_primary = not_applicable
```

Seed episodes after `effective_primary_seed_end` are still valid for execution,
density, tradability, H20 cost, and report-only path diagnostics, but they must
not enter primary-reference entry capture, primary failed-seed gates, or
capture-cost gates. This prevents incomplete 120-day forward windows, incomplete
T+30 capture windows, or split-tail unlabelled later references from being
counted as failed post-reference entry attempts.

### 6.2 Bridge Reference

Bridge denominator:

```text
ep2_launch_pool_big_winner_50h120
```

用途：

```text
只用于和 EP2 frozen launch pool 对齐，不得替代 primary reference。
```

R01 report 必须同时给出：

- primary PIT big-winner post-reference entry capture；
- EP2 launch-pool bridge capture under the same T+0..T+30 window；
- 二者的重合、漏捕和新增捕获分析。

---

## 7. Seed Contract

R01 必须同时构造两个 seed family。

### 7.1 Baseline Seed：EP2 Detector Bridge

```text
seed_family_id = ep2_launch_detector_v0_bridge
```

来源：

```text
ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet
```

作用：

- 作为 EP2 baseline / control；
- 提供 seed density、episode density、T+0..T+30 big-winner capture 的参照；
- 提供 `probe_with_simple_stop` bridge baseline。

### 7.2 Candidate Seed：Post30 High5 + Volume + RPS5 Seed

```text
seed_family_id = ep4_post30_profile_high5_volume_rps_seed_v0
```

V3 freezes the candidate seed as:

```text
close_near_high5_gt_0pct
AND vol_ratio10_gt_1_2
AND vol_ratio3_gt_1_2
AND rps5_gt_60
```

Operational formula on signal date `T`:

```text
close_near_high5_T = close_T >= max(close, T-5..T-1)
vol_ratio10_T      = volume_T / mean(volume, T-10..T-1)
vol_ratio3_T       = volume_T / mean(volume, T-3..T-1)
rps5_T             = percentile_rank(close_T / close_T-5 - 1)
                     within same-date PIT signal-close rank universe

candidate_seed_T =
  close_T >= max(close, T-5..T-1)
  and vol_ratio10_T > 1.2
  and vol_ratio3_T > 1.2
  and rps5_T > 0.60
  and hard_tradability_filters pass
```

RPS rank denominator:

```text
rps5_rank_universe =
  same-date PIT universe members with valid close_T and close_T-5,
  excluding suspended_or_dirty_bar rows known at signal close.

The RPS denominator must not require next_open_buy_executable and must not use
T+1 open state. Next-open buyability is an execution eligibility filter applied
after the seed formula is computed, not a relative-strength rank input.
```

The seed uses the prior 5-trading-day close high as the structural breakout
reference. For V3:

```text
seed_day_low = low_T
pivot_low_10d = min(low, T-10..T-1)
breakout_reference = max(close, T-5..T-1)
```

Fail-fast still uses the existing deterministic structure rule. The
implementation may use the explicitly defined 5-day close-high reference, but
must not introduce any additional structural reference not listed above.

V3 seed provenance:

```text
This condition was selected from the audit-only
`r01_big_winner_post30_indicator_search_v1` result:

same instrument satisfies condition at least once during T+0..T+30
coverage = 797 / 845 canonical R01 primary big winners = 94.32%
eligible-day density = 7.91%
median earliest hit offset = 8 trading days after reference_date
```

This provenance must be reported as post-reference profile evidence only. It is
not allowed to replace the executable R01 primary entry-capture computation, and
it must not be used to justify a `go_to_r02` decision unless the frozen V3 seed
is shown to have been discovered from train split only and then rebuilt from PIT
daily bars. For the current `all_splits` discovery artifact, a successful V3 run
can at most produce `go_to_oos_retest_required`.

Density provenance caveat:

```text
post30_search_eligible_day_density = 7.91%
R01_full_universe_seed_day_density = computed independently in the V3 run

These two density fields must be reported separately. The post30 search density
must not be described as "low density" under the R01 4.5% hard cap unless the
independently computed R01_full_universe_seed_day_density also passes that cap.
```

R01 V3 的 candidate seed 不要求是 EP2 detector 的 strict superset，也不要求 seed-day / episode count 宽于 EP2。V3 的比较对象不是“谁更早 launch”，而是“reference 后 T+0..T+30 的 executable capture 是否增加且成本可控”：

```text
新增 post-reference capture 的成本必须单独报告；
relative strength is an explicitly frozen hard condition in V3, not a learned
or validation-selected threshold.
```

如果实现后发现 V3 candidate seed 的 seed-day count 或 episode count 低于 EP2 detector，这本身不是 hard stop。报告必须如实说明 V3 是更后置的 post-reference entry family，不能把它表述为更宽的 launch detector。

R01 允许 candidate seed 比 EP2 detector 宽，但必须满足 V3 density 对偶约束。
The active V3 hard cap is:

```text
candidate_seed_day_rate <= min(4.5%, 2.7 * ep2_seed_day_rate)
candidate_episode_rate <= 3.0 * ep2_episode_rate
```

如果 candidate seed 因过宽触发 density cap，R01 不能通过，即使 recall 很高。

### 7.3 Density Denominator

R01 的 density 指标必须使用冻结分母，不能由实现自行解释。

Stock-day denominator:

```text
eligible_stock_day =
  PIT universe member on signal_date
  and next_open_buy_executable = true
  and has required rolling history for all seed formula fields
  and not suspended_or_dirty_bar

seed_day_rate =
  executable_seed_stock_day_count
  / eligible_stock_day_count
```

Episode denominator:

```text
eligible_instrument_year =
  instrument-year with at least 120 eligible_stock_days in the split

seed_episode_rate =
  seed_episode_count
  / eligible_instrument_year_count
```

EP2 ratio:

```text
seed_day_count_vs_ep2_ratio =
  candidate_executable_seed_stock_day_count
  / max(1, ep2_executable_seed_stock_day_count)

seed_episode_count_vs_ep2_ratio =
  candidate_seed_episode_count
  / max(1, ep2_seed_episode_count)
```

All density metrics must be reported by split. The validator must fail if any density denominator is zero in train / validation / robustness.

### 7.4 Structural Reference Fields

R01 must materialize the structural references used by both `R` normalization and fail-fast.

As-of rule:

```text
All rolling references end at signal_date - 1.
Only seed_day_low uses signal_date data because entry is next open after signal.
```

For `close_near_high5_gt_0pct`:

```text
rolling_close_high5_asof = max(close over previous 5 trading days ending signal_date - 1)
component_trigger_threshold = rolling_close_high5_asof
breakout_reference = rolling_close_high5_asof
```

Common references:

```text
seed_day_low = low on signal_date
pivot_low_10d = min(low over previous 10 trading days ending signal_date - 1)
```

V3 has exactly one price-structure component. `price_structure_component` must be
`close_near_high5_gt_0pct` for every candidate seed row. If any candidate stop
reference is not strictly below `entry_price`, that reference is invalid for
`initial_structural_stop`.

### 7.5 Episode Dedup Rule

Seed 必须从 stock-day 转成 episode。

Default episode rule:

```text
同一 instrument 连续 seed 之间 gap <= 20 trading days 视为同一 seed episode；
episode start = 第一个 seed signal_date；
episode effective entry = episode start 的 next-open；
episode end = 连续 20 trading days 无新 seed 后结束。
```

Re-entry rule:

```text
If an episode exits by fail-fast before its episode end, later seed signals
from the same instrument inside the same seed_episode_id are suppressed.
They must not open a new probe and must be counted as suppressed_reentry_count.
```

This prevents churn inside one unresolved seed episode from diluting failed-seed cost. A new probe is allowed only after the deduped seed episode has ended and a later seed starts a new `seed_episode_id`.

R01 的主指标必须以 episode 为主，stock-day 结果只能作为 audit。

---

## 8. Probe and Fail-Fast Contract

### 8.1 Probe

R01 只允许初始 probe：

```text
initial_probe_risk_budget = 0.25R
entry = next_open_after_signal
```

`0.25R` 是每 episode 的归一化风险预算，用于比较失败成本，不是组合层实际仓位。R01 不允许加仓，也不允许把多个 episode 的风险预算做组合优化。

R unit 定义：

```text
entry_price = next_open_after_signal
initial_structural_stop = closest valid stop below entry among:
  seed_day_low
  breakout_reference
  pivot_low_10d

initial_risk_pct = (entry_price - initial_structural_stop) / entry_price

episode_return_r =
  initial_probe_risk_budget_r
  * after_cost_return_pct
  / initial_risk_pct
```

Valid risk-distance bounds:

```text
2% <= initial_risk_pct <= 12%
```

如果没有有效 initial structural stop，或 stop distance 不在范围内，该 seed episode 必须标记为 `risk_distance_ineligible`，不得进入主模拟。这样 R01 的 `failed_seed_average_loss_r`、`p05_return_r` 和 recall-cost 指标都有统一单位。

Sign convention:

```text
return_r is signed:
  positive = gain
  negative = loss

loss_r is positive magnitude:
  loss_r = max(0, -return_r)
```

All metrics named `loss_r` use positive magnitude. Therefore `*_loss_r_diff_vs_* < 0` means the candidate has lower loss magnitude than the baseline.

### 8.2 Deterministic Fail-Fast

R01 的 fail-fast 必须是确定性规则，不能训练模型。

Primary fail-fast rule:

```text
With `T = signal_date` and entry at `T+1 open`, within the first 10
signal-relative trading days after the signal (`T+1` through `T+10`),
exit at next open if any trigger occurs:

1. close < seed_day_low
2. close < breakout_reference
3. close < pivot_low_10d
4. on T+10 only: close < entry_price
```

Natural exit:

```text
If no fail-fast trigger occurs, exit at next open after H20.
```

Execution realism:

```text
buy blocked at next open:
  reject seed episode from executable main simulation;
  keep it in rejected-seed audit.

sell blocked at fail-fast or natural-exit next open:
  retry at the next executable open;
  keep blocked days in holding-days and exposure-days;
  after max_exit_retry_trading_days, mark terminal_blocked_exit.
```

Cost model:

```text
inherit EP2 engineering-baseline cost components;
apply the same cost model to candidate, no-fail-fast, matched-delay,
matched-random, and EP2 bridge baselines.
```

Same-day ambiguity:

```text
如果同一天同时触发上行确认和失败条件，按 conservative_fail 处理。
```

### 8.3 Label B Boundary

Label B 可以作为 audit label：

```text
这个 deterministic fail-fast 是否覆盖了大多数早期失败路径？
```

但 R01 不允许：

- 用 Label B 训练模型；
- 用 Label B 选择 fail-fast 阈值；
- 用 Label B 过滤 entry；
- 在 validation / robustness 上重新定义失败结构。

训练式 Early Failure Detector 只能放到 R01.5 或 R02 之后。

---

## 9. Label Bridge Contract

R01 必须报告 Label A 与 EP2 fixed-percent label 的 bridge。

### 9.1 EP2 Fixed-Percent Label

Reference label:

```text
confirm_h10_u10_d06_conservative_fail
```

用途：

```text
与 EP2 R01 / R02 / R03 的 confirm-validity 口径保持可比。
```

### 9.2 EP4 ATR-Normalized Label A

Audit label:

```text
seed_quality_triple_barrier_atr_h10_u1_5_d1_0
seed_quality_triple_barrier_atr_h20_u2_0_d1_0
```

ATR formula:

```text
prev_close = close on previous trading day
true_range =
  max(
    high - low,
    abs(high - prev_close),
    abs(low - prev_close)
  )

atr20_asof =
  mean(true_range over previous 20 trading days ending signal_date - 1)

atr20_pct_asof = atr20_asof / close(signal_date)
```

Triple-barrier construction:

```text
entry_price = next_open_after_signal
upper_barrier = entry_price + upper_atr_multiple * atr20_asof
lower_barrier = entry_price - lower_atr_multiple * atr20_asof
vertical_barrier = H10 or H20 trading days after entry
same_day_policy = conservative_fail
```

用途：

```text
观察 ATR-normalized seed quality 是否比固定百分比更稳定。
```

Hard boundary:

```text
Label A bridge is audit-only in R01.
R01 的 seed / fail-fast / exit rule 不得由 Label A validation 表现重选。
```

---

## 10. Baseline Contract

R01 至少要和以下 baseline 对照。

| Baseline id | 说明 | 目的 |
|:--|:--|:--|
| `same_seed_no_fail_fast_hold_h20` | 同一 wide seed，直接持有到 H20 | 隔离 fail-fast 增量 |
| `same_seed_matched_delay_1d_same_fail_fast_h20` | 同一 seed 延迟 1 日进入，使用同一 fail-fast | matched-delay gate control |
| `same_seed_matched_delay_3d_same_fail_fast_h20` | 同一 seed 延迟 3 日进入，使用同一 fail-fast | matched-delay gate control |
| `same_seed_matched_delay_1d_no_fail_fast_h20` | 同一 seed 延迟 1 日进入，无 fail-fast | audit-only |
| `same_seed_matched_delay_3d_no_fail_fast_h20` | 同一 seed 延迟 3 日进入，无 fail-fast | audit-only |
| `matched_random_same_density_same_fail_fast_h20` | 同 split / industry / liquidity bucket 随机同密度事件，使用同一 fail-fast | audit-only diagnostic |
| `matched_random_same_density_no_fail_fast_h20` | 同 split / industry / liquidity bucket 随机同密度事件，无 fail-fast | audit-only |
| `ep2_detector_probe_with_simple_stop_bridge` | EP2 detector + frozen simple stop | EP2 bridge control |

EP2 bridge post-reference capture must be evaluated using the EP2 bridge
actual executable entry date under `[reference_date + 1, reference_date + 30]`,
not EP2 `signal_date`, detector date, or episode start. EP2 is a bridge/control
baseline, not a same-family post-reference seed.

Matched-delay baseline 要求：

```text
同一 instrument；
同一 seed episode；
entry date 延后 N trading days；
gate control 必须保持 same fail-fast、next-open execution、H20 natural exit、cost model 一致；
no-fail-fast delay 只能作为 audit；
如果延迟 entry 不可执行，则标记为 ineligible，不得静默丢弃。
```

Matched-delay structural reference policy:

```text
Use original seed episode structural references:
  original seed_day_low
  original breakout_reference
  original pivot_low_10d
  original price_structure_component

Only entry_date and entry_price are shifted.

For delayed entry:
  delayed_initial_structural_stop =
    closest valid original stop below delayed_entry_price

  delayed_initial_risk_pct =
    (delayed_entry_price - delayed_initial_structural_stop)
    / delayed_entry_price

If no original stop is strictly below delayed_entry_price,
or delayed_initial_risk_pct is outside [2%, 12%],
mark the delayed baseline row as ineligible.
```

This keeps matched-delay as an entry-timing control. It must not re-compute a fresh breakout or pivot structure after seeing the delayed date.

Matched-delay capture timing is also part of the control. For all
matched-delay baselines, primary capture must be evaluated using
`baseline_entry_execution_date` under the same executable entry-capture window
`[reference_date + 1, reference_date + 30]`. The carried candidate episode
eligibility may be used only for boundary eligibility and split eligibility;
it must not be used as the matched-delay capture timestamp.

Matched-delay ineligible bias audit:

```text
delay_period_return_pct =
  delayed_entry_price / original_entry_price - 1

matched_delay_ineligible_rate must be reported by:
  delay_period_return_pct quintile
  top_20pct_delay_return bucket
```

If delayed ineligible rows concentrate in the top delay-return bucket, the matched-delay alpha comparison is not reliable. The report must flag `matched_delay_reliability_status = failed` when the top delay-return quintile has both:

```text
top_quintile_ineligible_rate >= 2.0 * all_delay_ineligible_rate
and top_quintile_ineligible_rate >= 0.20
```

This reliability flag does not reselect the seed; it only prevents a biased matched-delay comparison from being used as positive evidence.

Matched-random baseline 要求：

```text
按 split、year、industry、liquidity bucket、volatility bucket 匹配；
事件密度与 candidate seed 在同 split 内一致；
same-fail-fast random 必须保持 same fail-fast、next-open execution、H20 natural exit、cost model 一致；
no-fail-fast random 只能作为 audit；
每个 split 至少生成 100 次 random replicate；
报告 mean / p05 / p50 / p95。
```

V3 diagnostic override:

```text
matched-random baselines are audit-only.
They must be fully materialized and reported, but no matched-random metric or
random_baseline_reliability_status may be used as a hard proceed / stop gate.
```

Matched bucket freeze:

```text
Bucket edges must be derived only from train split.
Required output:
  r01_matched_control_bucket_freeze.csv

liquidity bucket:
  money_20d_median_asof, rolling window ending signal_date - 1

volatility bucket:
  atr20_pct_asof from Label A ATR formula

bucket quantiles:
  [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

missing values:
  explicit_missing_bucket
```

Validation / robustness must apply the frozen train bucket edges. If a bucket has fewer than `min_train_rows_per_bucket` train rows, it must be merged with the nearest adjacent bucket before validation / robustness are evaluated.

Matched-random pseudo-event structural reference policy:

```text
For each candidate seed episode in a replicate:
  sample one PIT-executable random stock-day from the same:
    split
    year
    industry bucket
    liquidity bucket
    volatility bucket

  exclude all stock-days that are candidate EP4 seed stock-days in the same
  split, whether or not they belong to the carried candidate episode.

  carry over the candidate episode's price_structure_component
  only as the pseudo-event reference formula selector.

  random_signal_date = sampled stock-day
  random_entry_date = next_open_after_random_signal_date
```

Sampling policy:

```text
Within each replicate and matched bucket, sample without replacement from the
candidate-excluded random pool.

If a matched bucket does not have enough candidate-excluded stock-days to
sample the required pseudo-events without replacement, mark:
  random_capacity_shortfall = true
  random_baseline_reliability_status = failed as audit-only diagnostic

Do not silently fall back to replacement sampling, looser buckets, or seed-day
contamination.
```

Random pseudo-events do not need to satisfy the EP4 seed trigger. They are control events, not seed events. However, same-fail-fast random controls must generate deterministic structural references:

```text
For V3:
  random_breakout_reference =
    max(close over previous 5 trading days ending random_signal_date - 1)

random_seed_day_low =
  low on random_signal_date

random_pivot_low_10d =
  min(low over previous 10 trading days ending random_signal_date - 1)

random_initial_structural_stop =
  closest valid random stop below random_entry_price among:
    random_seed_day_low
    random_breakout_reference
    random_pivot_low_10d
```

If a random pseudo-event lacks required history, is not executable, or has no valid stop below entry within the `[2%, 12%]` risk-distance bounds, mark it as ineligible. Random ineligible rows must remain in `r01_baseline_simulation_panel.parquet` and must be counted in baseline eligibility diagnostics.

---

## 11. Metrics

R01 不使用 AUC 作为主指标。

Failed seed primary definition:

```text
failed_seed_primary =
  executable seed episode that does not capture any primary big-winner
  reference event under the primary executable entry-capture window
  [reference_date + 1, reference_date + 30],
  and primary_metric_eligible_seed_episode = true.
```

V3 interpretation:

```text
`failed_seed_primary` does not mean "failed to predict before launch".
It means an executable post-reference candidate entry that was not linked to
any canonical primary big-winner reference inside the executable
`[reference_date + 1, reference_date + 30]` entry-capture window. Headline cost
metrics therefore measure the cost of non-capturing post-reference entry
attempts, not the cost of pre-launch observation rights.
```

Rows with `primary_metric_eligible_seed_episode = false` must have
`failed_seed_primary = null` / `not_applicable` and must be excluded from all
headline failed-seed gates. They may still report H20 return, fail-fast trigger,
holding days, exposure days, and execution cost diagnostics.

Baseline failed-seed primary definition:

```text
baseline_failed_seed_primary =
  executable matched-delay or matched-random baseline row that does not capture
  any primary big-winner reference event under the same primary entry-capture window
  [reference_date + 1, reference_date + 30], and
  primary_metric_eligible_baseline_event = true.
```

For matched-delay rows, `primary_metric_eligible_baseline_event` inherits the
carried candidate seed episode's primary eligibility. For matched-random rows,
it is based on `random_entry_date <= effective_gate_entry_end`,
`terminal_exit_date <= configured_split_end`, and
`terminal_exit_date <= data_max_date` for that split.
Rows that are not primary-metric eligible must not enter matched-random
`failed_seed_average_loss_r` gates or p50 random baseline failed-loss
comparisons.

For matched-delay rows, capture must be evaluated with
`baseline_entry_execution_date`; for matched-random rows, capture must be
evaluated with the random baseline executable entry date. Candidate
`entry_execution_date` may not be reused as the baseline capture timestamp.

Required audit definitions:

```text
failed_seed_label_a_h10_u1_5 = executable seed episode whose H10 / +1.5ATR / -1.0ATR Label A is negative;
failed_seed_label_a_h20_u2_0 = executable seed episode whose H20 / +2.0ATR / -1.0ATR Label A is negative;
failed_seed_h20_negative = executable seed episode whose H20 after-cost return < 0;
failed_seed_fail_fast_triggered = executable seed episode exited by fail-fast.
```

All `failed_seed_*` headline cost gates use `failed_seed_primary`. The other definitions are report-only diagnostics.

### 11.1 Post-Reference Entry Capture Metrics

Required:

- `primary_big_winner_seed_recall`
- `bridge_ep2_big_winner_seed_recall`
- `seed_recall_diff_vs_ep2_detector`
- `primary_post_reference_entry_capture`
- `bridge_post_reference_entry_capture`
- `capture_diff_vs_ep2_detector`
- `big_winner_reference_count`
- `captured_big_winner_count`
- `missed_big_winner_count`
- `added_capture_vs_ep2_count`
- `lost_capture_vs_ep2_count`
- `net_added_capture_vs_ep2_count`
- `post_reference_capture_0_to_10_count`
- `signal_capture_count`
- `entry_capture_count`
- `signal_only_not_entry_within_window_count`

Primary entry-capture window:

```text
seed is counted as primary captured only if:
  entry_execution_date in
    [reference_date + 1 trading day, reference_date + 30 trading days]

Because entry = next_open_after_signal, the implied primary signal window is:
  signal_date in
    [reference_date, reference_date + 29 trading days]
```

Metric naming note:

```text
Fields that keep `seed_recall` or `primary_big_winner_seed_recall` in their
names are retained for compatibility with the shared R01 artifact schema. In
V3 they must be interpreted as post-reference T+0..T+30 executable entry
capture based on `entry_execution_date`, not pre-reference launch recall and not
signal-date-only capture.

Any schema-compatible `seed_recall` field in config, panels, gate audit, or
final report must bind to `entry_execution_date`. It must not use `signal_date`,
`episode_start_signal_date`, or the seed episode start as its timestamp basis.
```

The report must also show sensitivity windows:

```text
[0, +10]
[0, +20]
[0, +60]
```

Sensitivity windows are audit-only.

Post-reference capture subset rule:

```text
seed episodes whose entry_execution_date is in
[reference_date + 1 trading day, reference_date + 30 trading days]
contribute to:
  primary_big_winner_seed_recall
  added_capture_vs_ep2_count
  recall_cost_score
```

Counting grain rule:

```text
cost metrics:
  dedupe by executable seed episode.
  Each executable seed episode contributes at most one `return_r` / `loss_r`
  observation to candidate cost metrics and failed-seed cost gates.

capture metrics:
  dedupe by unique primary reference event.
  A primary reference event is counted at most once per population
  (candidate, EP2 bridge, matched-delay, matched-random replicate), even if
  multiple executable seed episodes capture it.

seed-to-reference multiplicity:
  If one executable seed episode links to multiple primary reference events,
  its `return_r` / `loss_r` is counted once in episode-level cost metrics.
  It may mark multiple unique reference events as captured, but it must not
  duplicate `loss_r`, exposure days, holding days, or failed-seed rows across
  those reference links.
```

`post_reference_capture_0_to_10_count` is a report-only subset of the primary
entry-capture numerator. It helps show whether executable entry happens
immediately after the reference date or only after delayed trend confirmation,
but it does not add a separate numerator on top of primary entry capture.

Signal-date audit:

```text
signal_capture_count =
  references with at least one candidate signal_date in [reference_date, reference_date + 29]

entry_capture_count =
  references with at least one candidate entry_execution_date in [reference_date + 1, reference_date + 30]

signal_only_not_entry_within_window_count =
  references or seed episodes where signal_date is in the implied signal window
  but entry_execution_date falls outside the primary entry-capture window

Primary gates must use entry_capture_count, not signal_capture_count.
```

### 11.2 Cost Metrics

Required:

- `failed_seed_average_loss_r`
- `failed_seed_median_loss_r`
- `failed_seed_p05_return_r`
- `failed_seed_median_holding_days`
- `exposure_days_per_seed_episode`
- `loss_r_per_captured_big_winner_seed`
- `exposure_days_per_captured_big_winner_seed`
- `incremental_loss_r_per_added_big_winner_vs_ep2`
- `incremental_exposure_days_per_added_big_winner_vs_ep2`

### 11.3 Payoff Shape Metrics

Required:

- `mean_return_r`
- `median_return_r`
- `p05_return_r`
- `p95_return_r`
- `payoff_skew`
- `positive_return_rate`
- `right_tail_contribution_share`

### 11.4 Density and Tradability Metrics

Required:

- `seed_day_rate`
- `seed_episode_rate`
- `seed_day_count_vs_ep2_ratio`
- `seed_episode_count_vs_ep2_ratio`
- `seed_day_rate_vs_ep2_multiple`
- `seed_episode_rate_vs_ep2_multiple`
- `unique_instrument_count`
- `unique_instrument_year_count`
- `top1_instrument_year_seed_share`
- `top5_instrument_seed_share`
- `suppressed_reentry_count`
- `next_open_buy_executable_rate`
- `limit_up_unbuyable_reject_count`
- `risk_distance_ineligible_count`
- `sell_blocked_exit_count`
- `terminal_blocked_exit_count`

### 11.5 Required Report-Only Diagnostics

The following diagnostics are required for interpretation but must not be used to re-select seed thresholds, fail-fast rules, density caps, or R01 gates.

Density cap tightness:

```text
seed_day_cap_utilization =
  candidate_seed_day_rate / min(0.045, 2.7 * ep2_seed_day_rate)

seed_episode_cap_utilization =
  candidate_seed_episode_rate / (3.0 * ep2_seed_episode_rate)
```

If candidate density exceeds the cap, R01 still fails. The diagnostic must describe where the excess density comes from by split / year / industry / liquidity bucket / volatility bucket, but it must not trim seeds or choose a narrower rule.

Fail-fast error audit:

```text
false_reject_winner =
  candidate seed episode exited by deterministic fail-fast
  and still linked to a primary big-winner reference event

missed_failure =
  candidate seed episode not exited by deterministic fail-fast
  and failed_seed_primary = true
  and H20 after-cost return < 0
```

Matched-random health audit:

```text
bucket_random_eligible_rate =
  eligible matched-random pseudo-events
  / sampled matched-random pseudo-events

random_loss_distribution =
  loss_r distribution by split / bucket / replicate statistic
```

Matched-random reliability:

```text
random_baseline_reliability_status is an audit-only diagnostic. It should be
reported as passed only if:
  split-level bucket_random_eligible_rate >= 0.80
  and every split / industry / liquidity / volatility bucket with
      sampled_random_event_count >= 30 has bucket_random_eligible_rate >= 0.60
  and all 100 random replicates are materialized for each split.
```

If `random_baseline_reliability_status` fails in validation, matched-random p50
cannot be used as positive supporting evidence. In V3, this status does not
force `stop_ep4_r01_path` by itself because the random baseline is not a hard
gate. The final report must instead state that matched-random comparison is
unreliable and cannot support a go decision.

R-unit distribution audit:

```text
initial_risk_pct distribution:
  p01 / p05 / p25 / median / p75 / p95 / p99

return_r outlier audit:
  p01 / p99
  top loss contributors
  share of extreme return_r rows with initial_risk_pct near 2% floor

cost-control by initial_risk_pct quintile:
  freeze candidate validation quintile edges
  report failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast
  within each quintile
```

Probe risk-budget sensitivity is report-only and linear:

```text
For probe budgets [0.10R, 0.25R, 0.50R],
rescale return_r and loss_r from the same simulated price path.
Do not rerun seed, fail-fast, or baseline selection.
```

---

## 12. Proceed / Stop Gates

R01 的结论必须来自冻结的 allowed decision set，不能输出模糊的 “promising”。

### 12.1 Hard Fail Gates

Any one fails -> `stop_ep4_r01_path`:

```yaml
authority_inputs_status: passed
seed_density_cap_status: passed
tradability_filter_status: passed
validation_threshold_selection_status: no_selection_from_validation
candidate_seed_day_rate: <= min(0.045, 2.7 * ep2_seed_day_rate)
candidate_seed_episode_rate: <= 3.0 * ep2_episode_rate
validation_unique_instrument_years: >= 80
top1_instrument_year_seed_share_validation: <= 0.05
```

Candidate seed-day / episode counts below EP2 detector are not hard-stop conditions. In V3 they are density diagnostics only, because the candidate family is a post-reference entry profile rather than a replacement launch detector. The run cannot claim to be a broader launch seed, but it can still pass if post-reference capture and cost gates pass.

### 12.2 Capture No-Harm Gates

All must pass:

```yaml
primary_big_winner_seed_recall_diff_vs_ep2_detector: >= -0.05
bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector: >= -0.05
fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast: <= 0.15
```

Interpretation:

```text
R01 允许 fail-fast 提前退出一部分最终 winner，
但不能让 survived post-reference big-winner entry capture 损失超过 15%。
```

Formula:

```text
no_fail_fast_captured_reference_count =
  unique primary reference events captured by executable candidate seed episodes
  under the primary executable entry-capture window
  [reference_date + 1, reference_date + 30] in same_seed_no_fail_fast_hold_h20

fail_fast_survived_captured_reference_count =
  unique primary reference events for which at least one capturing candidate
  seed episode remains non-fail-fast-exited through its H20 natural exit
  under the R01 deterministic fail-fast process

fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast =
  1
  - fail_fast_survived_captured_reference_count
    / max(1, no_fail_fast_captured_reference_count)
```

If `no_fail_fast_captured_reference_count = 0`, the metric is reportable but the recall no-harm gate cannot pass.

### 12.3 Cost-Control Gates

All must pass in validation split:

```yaml
failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast: < 0
failed_seed_median_holding_days_diff_vs_same_seed_no_fail_fast: < 0
p05_return_r_diff_vs_same_seed_no_fail_fast: >= -0.02
loss_r_per_captured_big_winner_seed_diff_vs_ep2_detector: <= 0
risk_pct_quintile_cost_control_status: passed
```

`risk_pct_quintile_cost_control_status` is passed only if every validation `initial_risk_pct` quintile with at least 30 `failed_seed_primary` candidate rows satisfies:

```text
failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast <= 0
```

Quintiles below 30 rows are report-only and must be named in `r01_r_unit_distribution_audit.csv`. This guards against an apparent R-unit cost improvement that is actually caused by a shifted stop-distance distribution.

### 12.4 Matched Baseline Gates

All must pass:

```yaml
mean_return_r_diff_vs_matched_delay_same_fail_fast_1d: >= -0.0055
mean_return_r_diff_vs_matched_delay_same_fail_fast_3d: >= -0.005
p05_return_r_diff_vs_matched_delay_same_fail_fast_min: >= -0.02
matched_delay_reliability_status: passed
```

V3 lowers the 1-day matched-delay no-harm threshold by 10% from `-0.005` to
`-0.0055`. The 3-day matched-delay and p05 thresholds remain unchanged.

These are no-harm timing controls, not alpha gates. Strict `mean_return_r_diff_vs_matched_delay_same_fail_fast_* >= 0` must be reported as descriptive evidence, but R01 cannot stop solely because a wider seed lacks positive entry-timing alpha after fail-fast.

V3 matched-random override:

```yaml
failed_seed_average_loss_r_diff_vs_matched_random_same_fail_fast_p50: report_only
random_baseline_reliability_status: report_only
```

Matched-random evidence cannot make R01 pass and cannot make R01 fail. If the
random baseline is unreliable, the report must explicitly mark the comparison
as unusable for positive evidence.

### 12.5 Capture-Cost Trade-Off Gate

Primary scalar:

```text
candidate_total_failed_loss_r =
  sum(loss_r over unique candidate executable seed episodes
      where failed_seed_primary = true)

ep2_total_failed_loss_r =
  sum(loss_r over unique EP2 bridge executable baseline episodes
      where baseline_failed_seed_primary = true)

incremental_abs_failed_loss_r_vs_ep2 =
  max(0, candidate_total_failed_loss_r - ep2_total_failed_loss_r)

added_capture_vs_ep2_count =
  count(unique primary reference events captured by candidate seed
        under primary [reference_date + 1, reference_date + 30] entry-capture window)
  - count(unique primary reference events captured by both candidate seed
          and EP2 bridge under primary [reference_date + 1, reference_date + 30] entry-capture window)

lost_capture_vs_ep2_count =
  count(unique primary reference events captured by EP2 bridge
        under primary [reference_date + 1, reference_date + 30] entry-capture window)
  - count(unique primary reference events captured by both candidate seed
          and EP2 bridge under primary [reference_date + 1, reference_date + 30] entry-capture window)

net_added_capture_vs_ep2_count =
  added_capture_vs_ep2_count - lost_capture_vs_ep2_count

recall_cost_score =
  net_added_capture_vs_ep2_count
  / max(1.0, incremental_abs_failed_loss_r_vs_ep2)

incremental_loss_r_per_added_big_winner_vs_ep2 =
  incremental_abs_failed_loss_r_vs_ep2
  / max(1, net_added_capture_vs_ep2_count)
```

R01 V3 passes the post-reference capture evidence threshold only if:

```yaml
added_capture_vs_ep2_count_validation: > 0
candidate_captured_reference_count_validation: >= ep2_captured_reference_count_validation
added_capture_vs_ep2_count_validation: > lost_capture_vs_ep2_count_validation
recall_cost_score_validation: > 0
incremental_loss_r_per_added_big_winner_vs_ep2_validation: <= 5.0
incremental_exposure_days_per_added_big_winner_vs_ep2_validation: <= 250
```

The `recall_cost_score_validation > 0` condition only proves that net added capture exists. It is not sufficient evidence that post-reference entry attempts are cheap, and under non-train-only discovery it is not sufficient evidence for `go_to_r02`. The net-capture and explicit upper bounds above are hard R01 gates and must be read from frozen report fields / `recall_cost_gate` in config, recorded in `r01_gate_audit.csv`, and changed only by updating this requirement.

If `added_capture_vs_ep2_count_validation <= 0` or `added_capture_vs_ep2_count_validation <= lost_capture_vs_ep2_count_validation`, candidate seed cannot produce `go_to_oos_retest_required`. It can only produce an archive decision if the archive gate subset in §12.8 passes:

```yaml
decision: archive_cost_control_sleeve_no_r02
failed_seed_average_loss_r_diff_vs_ep2_detector: < 0
primary_big_winner_seed_recall_diff_vs_ep2_detector: >= -0.02
```

This prevents the weak conclusion:

```text
post-reference capture 持平 + cost 略降 = 自动通过。
```

### 12.6 Robustness No-Harm Gate

R01 cannot go to R02 if validation passes but robustness reverses the core conclusion.

Required robustness conditions:

```yaml
robustness_primary_big_winner_seed_recall_diff_vs_ep2_detector: >= -0.10
robustness_failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast: <= 0
robustness_p05_return_r_diff_vs_matched_delay_same_fail_fast_min: >= -0.03
robustness_recall_cost_score_status: finite_or_not_applicable
robustness_incremental_loss_r_per_added_big_winner_vs_ep2: <= 7.5 when added_capture_vs_ep2_count_robustness > 0
robustness_incremental_exposure_days_per_added_big_winner_vs_ep2: <= 375 when added_capture_vs_ep2_count_robustness > 0
```

Robustness does not need to add new primary captures versus EP2. A validation-supported post-reference capture path may still proceed with `go_to_r02_with_robustness_warning` when robustness has no added capture, as long as all robustness no-harm conditions above pass and the final report explicitly labels the missing robustness added-capture evidence as an upstream R02 caveat.

If any robustness no-harm condition fails, the decision must be:

```text
stop_ep4_r01_path
```

If validation passes, robustness is directionally weaker but still inside all no-harm bounds, and the seed provenance OOS gate in §12.7 permits R02, the report must label the result:

```text
go_to_r02_with_robustness_warning
```

This warning status allows R02 design work only when §12.7 permits R02. If
discovery is not train-only, the same metric pattern can at most produce
`go_to_oos_retest_required`. R02 must keep R01 robustness weakness as an
explicit upstream caveat whenever R02 is eventually allowed.

### 12.7 Seed Provenance OOS Gate

V3 cannot claim strict validation / robustness OOS evidence unless seed
discovery was train-only.

```yaml
seed_discovery_scope_validation: train_only_required_for_go_to_r02
current_seed_discovery_scope: all_splits
current_validation_oos_clean: false
```

Decision implication:

```text
If discovery_scope != train_only:
  go_to_r02: forbidden
  go_to_r02_with_robustness_warning: forbidden

  if all post-reference capture, density, cost-control, matched-delay,
  robustness no-harm, and structural validator gates pass:
    decision = go_to_oos_retest_required

  otherwise if archive-hypothesis thresholds pass:
    decision = archive_hypothesis_no_r02

  otherwise:
    decision = stop_ep4_r01_path
```

`go_to_oos_retest_required` means V3 produced a useful hypothesis under a
known all-split discovery lineage. It authorizes only a future train-only or
future-period OOS retest requirement. It does not authorize R02.

### 12.8 Decision Matrix

The final decision must be reproducible from this matrix. A gate marked `required` must pass. A gate marked `report_only` must be reported but cannot determine that decision.

| Gate subset | `go_to_r02` | `go_to_r02_with_robustness_warning` | `go_to_oos_retest_required` | `archive_hypothesis_no_r02` | `archive_cost_control_sleeve_no_r02` | `stop_ep4_r01_path` |
|:--|:--|:--|:--|:--|:--|:--|
| §12.1 hard fail gates | required | required | required | required | required | fail if any hard gate fails |
| §12.7 seed provenance OOS gate | train_only required | train_only required | allowed when not train_only | required not train_only | train_only or not_train_only allowed | stop if provenance missing |
| EP2 count ratio diagnostics | report_only | report_only | report_only | report_only | report_only | never a standalone stop gate |
| §12.2 capture no-harm | required | required | required | archive-hypothesis threshold required | archive threshold required | fail if below required threshold |
| §12.3 cost-control vs no-fail-fast | required | required | required | required | required | fail if cost-control fails |
| §12.4 matched baseline no-harm | required for matched-delay; matched-random report_only | required for matched-delay; matched-random report_only | required for matched-delay; matched-random report_only | matched-delay p05 / reliability required; matched-random report_only | matched-delay p05 / reliability required; matched-random report_only | fail if required matched-delay no-harm fails |
| §12.5 added capture / bounded capture-cost score | required | required | required | not required | not required | fail if post-reference capture path is claimed without it |
| §12.6 robustness no-harm | required, no material warning | required, warning carried | required, warning carried | required no severe degradation | required no severe degradation | fail if severe degradation |

Archive-specific thresholds:

```yaml
archive_primary_big_winner_seed_recall_diff_vs_ep2_detector: >= -0.02
archive_bridge_ep2_big_winner_seed_recall_diff_vs_ep2_detector: >= -0.02
archive_failed_seed_average_loss_r_diff_vs_ep2_detector: < 0
archive_failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast: < 0
archive_p05_return_r_diff_vs_same_seed_no_fail_fast: >= -0.02
archive_p05_return_r_diff_vs_matched_delay_same_fail_fast_min: >= -0.03
archive_matched_delay_reliability_status: passed
archive_random_baseline_reliability_status: report_only
archive_robustness_primary_big_winner_seed_recall_diff_vs_ep2_detector: >= -0.10
archive_robustness_failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast: <= 0
```

Archive is intentionally stricter on capture no-harm (`-0.02`) because it does not earn the right to proceed through additional primary captures. It is a preserved cost-control sleeve, not a post-reference capture success.

Archive-hypothesis thresholds:

```yaml
archive_hypothesis_primary_entry_capture_diff_vs_ep2_detector: >= -0.05
archive_hypothesis_failed_seed_average_loss_r_diff_vs_same_seed_no_fail_fast: < 0
archive_hypothesis_matched_delay_reliability_status: passed
archive_hypothesis_oos_clean_status: false
archive_hypothesis_report_must_state: all_split_discovery_not_oos
```

`archive_hypothesis_no_r02` preserves a potentially useful post-reference
entry hypothesis but explicitly blocks R02 until train-only or future-period OOS
retest exists.

### 12.9 Allowed Decisions

The final decision must be exactly one of:

| Decision | Meaning |
|:--|:--|
| `go_to_r02` | post-reference capture path passes validation and robustness no-harm |
| `go_to_r02_with_robustness_warning` | validation passes, robustness no-harm passes but weakens materially |
| `go_to_oos_retest_required` | all-split-discovered V3 hypothesis passes structural gates, but OOS-clean discovery is missing |
| `archive_hypothesis_no_r02` | useful all-split-discovered hypothesis evidence exists, but no OOS-clean proceed right |
| `archive_cost_control_sleeve_no_r02` | cost improves without added post-reference capture; do not start R02 |
| `stop_ep4_r01_path` | R01 path fails |

### 12.10 Counterfactual Failure Inheritance

If final decision is `stop_ep4_r01_path`, the report must include a report-only section:

```text
counterfactual_failure_inheritance
```

This section is not allowed to change the R01 decision. It exists only to preserve useful failure evidence for future research.

Required counterfactual diagnostics:

```text
1. conservative_fail sensitivity:
   describe whether same-day ambiguity materially affects fail-fast exits
   and Label A bridge results.

2. tail no-harm sensitivity:
   describe whether p05 no-harm failures are small threshold misses
   or large tail-risk failures.

3. density cap sensitivity:
   describe whether cap failure comes from broad market density
   or concentration in specific year / industry / bucket groups.

4. fail-fast window timing:
   report trigger-day distribution inside the 10-day window,
   and descriptive counts for trigger_day <= 8 and trigger_day in [9, 12]
   without changing the R01 primary fail-fast rule.
```

The section must label every row / table as:

```text
report_only_not_decision_changing
```

---

## 13. Required Outputs

The implementation must write:

```text
ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed/
  cache/
    r01_big_winner_reference_panel.parquet
    r01_seed_event_panel.parquet
    r01_seed_episode_panel.parquet
    r01_probe_simulation_panel.parquet
    r01_baseline_simulation_panel.parquet
  reports/
    r01_upstream_authority.csv
    r01_big_winner_reference_audit.csv
    r01_seed_density_audit.csv
    r01_density_cap_tightness_audit.csv
    r01_seed_recall_audit.csv
    r01_label_bridge_audit.csv
    r01_fail_fast_path_audit.csv
    r01_fail_fast_error_audit.csv
    r01_matched_control_bucket_freeze.csv
    r01_random_baseline_health_audit.csv
    r01_r_unit_distribution_audit.csv
    r01_baseline_diff_audit.csv
    r01_matched_delay_ineligible_audit.csv
    r01_recall_cost_tradeoff.csv
    r01_counterfactual_failure_inheritance.csv
    r01_gate_audit.csv
    r01_final_report.md
  manifests/
    r01_run_manifest.json
```

`r01_run_manifest.json` must include:

```text
configured_train_window
configured_validation_window
configured_robustness_window
effective_train_reference_window
effective_validation_reference_window
effective_robustness_reference_window
effective_train_primary_seed_end
effective_validation_primary_seed_end
effective_robustness_primary_seed_end
effective_train_gate_entry_end
effective_validation_gate_entry_end
effective_robustness_gate_entry_end
max_probe_observation_horizon_trading_days
split_boundary_policy
primary_capture_basis
signal_capture_basis
seed_discovery_artifact
seed_discovery_scope
validation_oos_clean
post30_search_eligible_day_density
r01_full_universe_seed_day_density_by_split
data_max_date
data_max_date_minus_forward_horizon
```

### 13.1 `r01_gate_audit.csv`

Required columns:

| Column | Description |
|:--|:--|
| `gate_id` | gate identifier |
| `split` | train / validation / robustness |
| `metric_name` | metric checked |
| `metric_value` | observed value |
| `threshold` | required threshold |
| `comparison` | `>=`, `<=`, `<`, `>` |
| `status` | passed / failed |
| `is_hard_gate` | boolean |
| `failure_reason` | required if failed |

### 13.2 `r01_matched_control_bucket_freeze.csv`

Required columns:

| Column | Description |
|:--|:--|
| `bucket_field` | `money_20d_median_asof` / `atr20_pct_asof` |
| `bucket_id` | frozen bucket id |
| `quantile_low` | train quantile lower edge |
| `quantile_high` | train quantile upper edge |
| `value_low` | frozen numeric lower edge |
| `value_high` | frozen numeric upper edge |
| `train_row_count` | train rows before merge |
| `merged_bucket_id` | final bucket after low-count merge |
| `missing_bucket` | boolean |
| `status` | passed / failed |

### 13.3 `r01_density_cap_tightness_audit.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `year` | calendar year or `all` |
| `industry` | PIT industry or `all` |
| `liquidity_bucket` | frozen liquidity bucket or `all` |
| `volatility_bucket` | frozen volatility bucket or `all` |
| `candidate_seed_day_rate` | candidate seed-day density |
| `candidate_seed_episode_rate` | candidate episode density |
| `seed_day_cap` | active seed-day cap |
| `seed_episode_cap` | active episode cap |
| `seed_day_cap_utilization` | rate divided by cap |
| `seed_episode_cap_utilization` | rate divided by cap |
| `cap_violation_flag` | boolean |
| `forward_return_p50` | descriptive forward return median for the bucket |
| `failed_seed_average_loss_r` | descriptive failed-seed loss |
| `audit_only_status` | report_only |

`forward_return_p50` is a future-label descriptive audit field. It must not be
used to derive bucket edges, merge sparse buckets, set density caps, set
reliability status, choose thresholds, or change any final decision.

### 13.4 `r01_fail_fast_error_audit.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `error_type` | false_reject_winner / missed_failure |
| `seed_episode_id` | seed episode id |
| `instrument` | instrument |
| `episode_start_signal_date` | seed episode start |
| `exit_trigger_type` | fail-fast trigger or none |
| `exit_signal_date` | fail-fast signal date if any |
| `h20_after_cost_return` | H20 return under no-fail-fast reference |
| `return_r` | R01 process signed return |
| `loss_r` | positive loss magnitude |
| `captured_reference_event_id` | primary reference id if any |
| `price_structure_component` | seed component |
| `initial_risk_pct` | initial structural risk distance |
| `audit_only_status` | report_only |

### 13.5 `r01_random_baseline_health_audit.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `baseline_id` | random baseline id |
| `replicate_stat` | mean / p05 / p50 / p95 |
| `industry` | PIT industry or `all` |
| `liquidity_bucket` | frozen liquidity bucket or `all` |
| `volatility_bucket` | frozen volatility bucket or `all` |
| `sampled_random_event_count` | sampled pseudo-events |
| `eligible_random_event_count` | eligible pseudo-events |
| `bucket_random_eligible_rate` | eligible / sampled |
| `random_replicate_count` | materialized replicate count for the split / bucket |
| `random_excluded_candidate_seed_day_count` | candidate seed stock-days excluded from random pool |
| `random_capacity_shortfall` | boolean shortfall under without-replacement sampling |
| `random_sampling_replacement_policy` | must be `without_replacement_within_replicate` |
| `random_baseline_reliability_status` | passed / failed |
| `failed_seed_average_loss_r` | random failed-seed loss |
| `p05_return_r` | random p05 return |
| `p50_return_r` | random median return |
| `p95_return_r` | random p95 return |
| `audit_only_status` | report_only |

### 13.6 `r01_r_unit_distribution_audit.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `population` | candidate / ep2_bridge / matched_delay / matched_random |
| `probe_r_budget` | 0.10 / 0.25 / 0.50 |
| `initial_risk_pct_p01` | p01 initial risk distance |
| `initial_risk_pct_p05` | p05 initial risk distance |
| `initial_risk_pct_p25` | p25 initial risk distance |
| `initial_risk_pct_median` | median initial risk distance |
| `initial_risk_pct_p75` | p75 initial risk distance |
| `initial_risk_pct_p95` | p95 initial risk distance |
| `initial_risk_pct_p99` | p99 initial risk distance |
| `return_r_p01` | p01 signed return in R |
| `return_r_p99` | p99 signed return in R |
| `loss_r_top1_share` | largest loss contribution share |
| `loss_r_top5_share` | top five loss contribution share |
| `near_risk_floor_extreme_loss_share` | share of extreme losses near 2% floor |
| `risk_distance_ineligible_count` | rejected by risk distance |
| `initial_risk_pct_quintile` | validation quintile id or `all` |
| `quintile_failed_seed_count` | failed-seed rows in quintile |
| `quintile_failed_seed_average_loss_r` | candidate failed-seed loss in quintile |
| `quintile_baseline_failed_seed_average_loss_r` | no-fail-fast baseline loss in quintile |
| `quintile_loss_r_diff_vs_same_seed_no_fail_fast` | candidate minus no-fail-fast loss in quintile |
| `risk_pct_quintile_cost_control_status` | passed / failed / report_only_insufficient_rows |
| `audit_only_status` | report_only |

### 13.7 `r01_baseline_diff_audit.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `baseline_id` | compared baseline |
| `baseline_role` | gate / audit |
| `metric_name` | metric being compared |
| `candidate_value` | R01 candidate value |
| `baseline_value` | baseline value |
| `diff_value` | candidate minus baseline |
| `random_replicate_stat` | mean / p05 / p50 / p95 / not_random |
| `comparison` | gate comparison when applicable |
| `threshold` | gate threshold when applicable |
| `status` | passed / failed / report_only |

### 13.8 `r01_matched_delay_ineligible_audit.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `delay_days` | 1 / 3 |
| `delay_period_return_bucket` | quintile id or top_20pct_delay_return |
| `candidate_row_count` | rows eligible before delay eligibility check |
| `matched_delay_ineligible_count` | delayed rows marked ineligible |
| `matched_delay_ineligible_rate` | ineligible / candidate rows |
| `all_delay_ineligible_rate` | split-level ineligible rate |
| `top_quintile_ineligible_rate` | top delay-return quintile ineligible rate |
| `matched_delay_reliability_status` | passed / failed |
| `audit_only_status` | report_only |

### 13.9 `r01_recall_cost_tradeoff.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `candidate_total_failed_loss_r` | sum positive loss magnitude over unique candidate executable seed episodes where `failed_seed_primary = true` |
| `ep2_total_failed_loss_r` | sum positive loss magnitude over unique EP2 bridge executable baseline episodes where `baseline_failed_seed_primary = true` |
| `incremental_abs_failed_loss_r_vs_ep2` | `max(0, candidate - ep2)` |
| `candidate_captured_reference_count` | unique primary references captured by candidate under executable entry window `[reference_date + 1, reference_date + 30]` |
| `ep2_captured_reference_count` | unique primary references captured by EP2 bridge actual executable entry date under `[reference_date + 1, reference_date + 30]` |
| `overlap_captured_reference_count` | unique primary references captured by both under executable entry window `[reference_date + 1, reference_date + 30]` |
| `added_capture_vs_ep2_count` | candidate-only captured primary references under executable entry window `[reference_date + 1, reference_date + 30]` |
| `lost_capture_vs_ep2_count` | EP2-only captured primary references under executable entry window `[reference_date + 1, reference_date + 30]` |
| `net_added_capture_vs_ep2_count` | added minus lost captured primary references |
| `post_reference_capture_0_to_10_count` | subset of primary captures whose first capture is in T+0..T+10; report-only diagnostic |
| `signal_capture_count` | report-only references captured by implied signal window |
| `entry_capture_count` | primary references captured by executable entry window |
| `signal_only_not_entry_within_window_count` | signal-window captures whose entry is outside primary entry window |
| `capture_time_basis` | must be `entry_execution_date` for primary gates |
| `seed_discovery_scope` | train_only / train_validation / all_splits |
| `validation_oos_clean` | boolean |
| `recall_cost_score` | net added capture divided by incremental failed loss |
| `incremental_loss_r_per_added_big_winner_vs_ep2` | incremental failed loss per net added capture |
| `incremental_exposure_days_per_added_big_winner_vs_ep2` | incremental exposure days per net added capture |
| `max_allowed_incremental_loss_r_per_added_big_winner_vs_ep2` | frozen R01 gate threshold |
| `max_allowed_incremental_exposure_days_per_added_big_winner_vs_ep2` | frozen R01 gate threshold |
| `decision_support_status` | passed / failed / report_only |

### 13.10 `r01_counterfactual_failure_inheritance.csv`

Required columns:

| Column | Description |
|:--|:--|
| `split` | train / validation / robustness |
| `counterfactual_family` | conservative_fail / p05_no_harm / density_cap / fail_fast_window |
| `counterfactual_variant` | descriptive variant id |
| `primary_decision` | frozen R01 decision |
| `decision_change_allowed` | must be false |
| `metric_name` | metric being described |
| `primary_value` | value under frozen R01 contract |
| `counterfactual_value` | descriptive counterfactual value |
| `diff_value` | counterfactual minus primary |
| `affected_episode_count` | number of affected episodes |
| `affected_reference_count` | number of affected primary references |
| `dominant_year` | year with largest contribution, or `none` |
| `dominant_industry` | industry with largest contribution, or `none` |
| `dominant_bucket` | liquidity / volatility bucket with largest contribution, or `none` |
| `inheritance_note` | concise interpretation for future research |
| `audit_only_status` | must be `report_only_not_decision_changing` |

### 13.11 Core Panel Schemas

`r01_big_winner_reference_panel.parquet`

Grain:

```text
one row per deduped primary big-winner reference event
```

Required columns:

```text
reference_event_id
instrument
reference_date
entry_price_next_open
forward_horizon_trading_days
forward_peak_close
forward_peak_date
forward_return
dedupe_gap_trading_days
split
eligibility_status
ineligibility_reason
```

`r01_seed_event_panel.parquet`

Grain:

```text
one row per executable or rejected seed stock-day before episode dedup
```

Required columns:

```text
seed_event_id
seed_family_id
instrument
signal_date
split
close
money
price_structure_component
close_near_high5_gt_0pct_triggered
rolling_close_high5_asof
component_trigger_threshold
breakout_reference
vol_ratio10
vol_ratio3
rps5
money_20d_median_asof
atr20_asof
atr20_pct_asof
pit_universe_member
next_open_buy_executable
buy_block_reason
hard_filter_status
reject_reason
```

`r01_seed_episode_panel.parquet`

Grain:

```text
one row per seed_family_id + instrument + seed_episode_id
```

Required columns:

```text
seed_episode_id
seed_family_id
instrument
episode_start_signal_date
episode_effective_entry_date
entry_execution_date
episode_end_signal_date
split
terminal_exit_date
split_boundary_status
first_seed_event_id
seed_event_count
suppressed_reentry_count
entry_price
price_structure_component
seed_day_low
breakout_reference
pivot_low_10d
initial_structural_stop
initial_risk_pct
risk_distance_status
executable_status
episode_reject_reason
primary_metric_eligible_seed_episode
boundary_status
captures_primary_big_winner
captured_reference_event_id
capture_window_id
capture_time_basis
entry_capture_window_status
captures_ep2_bridge_big_winner
```

`r01_probe_simulation_panel.parquet`

Grain:

```text
one row per executable seed episode under the candidate R01 probe process
```

Required columns:

```text
simulation_id
seed_episode_id
seed_family_id
instrument
entry_date
entry_execution_date
entry_price
initial_probe_risk_budget_r
initial_structural_stop
initial_risk_pct
exit_trigger_type
exit_signal_date
exit_execution_date
terminal_exit_date
exit_price
sell_blocked_day_count
terminal_blocked_exit
split_boundary_status
gross_return_pct
after_cost_return_pct
return_r
loss_r
holding_days
exposure_days
primary_metric_eligible_seed_episode
failed_seed_primary
failed_seed_label_a_h10_u1_5
failed_seed_label_a_h20_u2_0
failed_seed_h20_negative
failed_seed_fail_fast_triggered
split
```

`r01_baseline_simulation_panel.parquet`

Grain:

```text
one row per baseline_id + seed_episode_id or random_event_id + replicate_id
```

Required columns:

```text
baseline_simulation_id
baseline_id
replicate_id
matched_control_type
fail_fast_policy
structural_reference_policy
carried_price_structure_component
carried_seed_episode_id
seed_episode_id
random_event_id
instrument
signal_date
random_signal_date
entry_date
entry_execution_date
candidate_entry_execution_date
baseline_entry_execution_date
ep2_bridge_entry_execution_date
capture_timestamp_used
entry_price
seed_day_low
breakout_reference
pivot_low_10d
initial_structural_stop
initial_risk_pct
delay_days
delay_period_return_pct
delay_period_return_bucket
matched_delay_reliability_status
random_excluded_candidate_seed_day
random_capacity_shortfall
random_sampling_replacement_policy
random_baseline_reliability_status
primary_metric_eligible_baseline_event
boundary_status
captures_primary_big_winner
captured_reference_event_id
capture_window_id
capture_time_basis
entry_capture_window_status
baseline_failed_seed_primary
exit_date
exit_execution_date
terminal_exit_date
exit_price
split_boundary_status
eligibility_status
ineligibility_reason
gross_return_pct
after_cost_return_pct
return_r
loss_r
holding_days
exposure_days
split
match_year
match_industry
match_liquidity_bucket
match_volatility_bucket
```

### 13.12 `r01_final_report.md`

Report must include:

1. R01 phase boundary；
2. upstream authority status；
3. big-winner reference set definition, effective reference windows, and counts；
4. density denominator and EP2 detector vs EP4 wide seed density；
5. density cap tightness and cap-violation descriptive diagnostics；
6. structural reference and `R` normalization audit；
7. `initial_risk_pct` distribution, quintile cost-control, and `return_r` outlier audit；
8. primary and bridge post-reference entry capture, with T+0..T+10 timing decomposition separated from post30 provenance evidence；
9. fail-fast vs no-fail-fast attribution；
10. fail-fast false-reject / missed-failure audit；
11. captured post-reference entry cost, including `loss_r_per_captured_big_winner_seed` and `exposure_days_per_captured_big_winner_seed`；
12. matched-delay same-fail-fast / matched-random baseline diffs, including matched-delay ineligible bias audit and matched-random reliability；
13. matched-control bucket freeze and random baseline health summary；
14. bounded capture-cost trade-off, including both score and max cost / exposure gates；
15. signal-date vs entry-date capture audit, including `signal_only_not_entry_within_window_count`；
16. seed provenance OOS status and the decision cap caused by all-split discovery；
17. post30 search density vs R01 full-universe density, reported as separate denominators；
18. allowed decision and gate evidence；
19. if decision is `stop_ep4_r01_path`, counterfactual failure inheritance；
20. V3 post30 provenance caveat and ex-post reference-date caveat, explicitly separated from executable primary entry capture；
21. what R02 is allowed to assume if R01 passes。

---

## 14. Runner And Validator

The implementation must reuse or extend the shared R01 runner / validator:

```text
ep4/scripts/run_r01_high_recall_probe_fail_fast.py
ep4/scripts/validate_r01_high_recall_probe_fail_fast.py
```

Run commands:

```bash
uv run python ep4/scripts/run_r01_high_recall_probe_fail_fast.py \
  --config ep4/configs/r01_high_recall_probe_fail_fast_v3.yaml
```

Validation command:

```bash
uv run python ep4/scripts/validate_r01_high_recall_probe_fail_fast.py \
  --config ep4/configs/r01_high_recall_probe_fail_fast_v3.yaml
```

The validator must fail closed if:

- any canonical input is missing；
- EP2 manifest, EP2 config, or frozen launch pool cannot be read；
- `pit_universe_path` is not a point-in-time daily membership table with `date` and `instrument` columns；
- `pit_qlib_instrument_universe_path` is used as the tradable denominator instead of as an instrument map / audit input；
- primary big-winner reference set is empty；
- effective reference windows or `effective_primary_seed_end` are missing from `r01_run_manifest.json`；
- `effective_gate_entry_end`, `max_probe_observation_horizon_trading_days`, or
  split-boundary status fields are missing from manifest / panels；
- headline capture, cost, fail-fast, or proceed / stop gates include rows whose
  terminal executable path crosses the configured split boundary；
- primary-reference entry capture uses `signal_date` / `episode_start_signal_date` instead of `entry_execution_date` as the primary gate basis；
- any schema-compatible `seed_recall` / `primary_big_winner_seed_recall` field
  in V3 uses `signal_date`, `episode_start_signal_date`, or seed episode start
  instead of `entry_execution_date` as its timestamp basis；
- primary entry capture includes entries outside `[reference_date + 1, reference_date + 30]`；
- signal-window captures are not separately reported from entry-window captures；
- primary-reference entry capture, `failed_seed_primary`, capture-cost gates, or primary-reference fail-fast error audits include seed episodes after `effective_gate_entry_end`；
- seed episodes with `effective_gate_entry_end < entry_execution_date <= effective_primary_seed_end` are counted in headline primary metrics instead of report-only split-boundary diagnostics；
- `primary_metric_eligible_seed_episode` / `primary_metric_eligible_baseline_event` cannot be reproduced from entry execution dates, terminal exit dates, signal dates, and effective reference windows；
- `reference_date` is described as an observable trading state rather than an ex-post evaluation anchor；
- density denominators cannot be reproduced from panel fields；
- seed density caps are missing or not evaluated；
- V3 seed-day cap is not exactly `min(0.045, 2.7 * ep2_seed_day_rate)`；
- post30 search eligible-day density and R01 full-universe seed-day density are missing, merged into one field, or compared as the same denominator；
- candidate seed is not compared against EP2 detector；
- seed provenance fields (`discovery_artifact`, `discovery_scope`, `validation_oos_clean`) are missing from config, manifest, gate audit, or final report；
- `discovery_scope != train_only` and report decision is `go_to_r02` or `go_to_r02_with_robustness_warning`；
- candidate seed formula is not exactly
  `close_near_high5_gt_0pct AND vol_ratio10_gt_1_2 AND vol_ratio3_gt_1_2 AND rps5_gt_60`；
- `vol_ratio10` / `vol_ratio3` use money, current-day-inclusive denominators,
  adjusted future data, or any window other than prior 10 / prior 3 trading days；
- `close_near_high5_gt_0pct` uses high price, a current-day-inclusive rolling
  reference, or any window other than the prior 5 trading-day close high；
- `rps5` rank denominator uses `next_open_buy_executable`, T+1 open state, or any
  universe other than same-date PIT signal-close rank universe；
- candidate seed uses any relative-strength hard filter other than the frozen
  `rps5_T > 0.60` condition in §7.2；
- candidate seed stock-day or episode count is below EP2 detector and the report still claims V3 is a broader launch detector；
- top instrument-year seed concentration gates are missing；
- structural reference fields are missing or use rolling windows that include signal_date when forbidden；
- `initial_risk_pct` / `return_r` cannot be reproduced from panel fields；
- any `loss_r` metric is signed instead of positive magnitude；
- cost metrics duplicate one executable seed episode's `return_r`, `loss_r`,
  exposure days, holding days, or failed-seed row because it links to multiple
  primary reference events；
- capture metrics count seed-reference links instead of unique primary
  reference events per population；
- blocked buy / blocked sell / retry states are not materialized；
- fail-fast includes any trained model output；
- R01 includes add / ATR stop / state stop / portfolio sizing fields；
- validation or robustness is used for threshold selection；
- `forward_return_p50` or any other future-label audit field is used to derive
  bucket edges, merge buckets, set caps, set reliability status, choose
  thresholds, or change final decision；
- same-fail-fast matched-delay baseline is missing；
- matched-random audit baselines are missing from required report artifacts；
- matched-delay same-fail-fast baselines recompute fresh structural references instead of carrying original seed references；
- matched-delay primary capture uses candidate `entry_execution_date`,
  `signal_date`, or episode start instead of `baseline_entry_execution_date`；
- EP2 bridge primary capture uses EP2 `signal_date`, detector date, or episode
  start instead of the EP2 bridge actual executable entry date；
- baseline panel lacks `candidate_entry_execution_date`,
  `baseline_entry_execution_date`, `ep2_bridge_entry_execution_date`, or
  `capture_timestamp_used` fields needed to reproduce baseline capture timing；
- matched-delay ineligible rows are missing, silently dropped, or lack delay-return-bucket reliability diagnostics；
- matched-random same-fail-fast baselines do not materialize pseudo-event structural references；
- matched-random ineligible pseudo-events are silently dropped instead of reported；
- matched-random bucket freeze is missing or uses validation / robustness rows to derive edges；
- matched-random pseudo-events include candidate EP4 seed stock-days or use replacement sampling；
- matched-random capacity shortfall is missing from `random_baseline_reliability_status` diagnostics；
- matched-random reliability status is missing from reports or is used as a hard proceed / stop gate；
- matched-random failed-seed loss diagnostics lack baseline-side `captures_primary_big_winner` / `baseline_failed_seed_primary` fields or use candidate failed rows as the random baseline population；
- matched-random rows do not materialize `signal_date` / `random_signal_date` needed to reproduce primary reference capture and primary-metric eligibility；
- required report-only diagnostic artifacts are missing or have non-report-only selection effects；
- `r01_counterfactual_failure_inheritance.csv` is used to change the R01 decision or any gate；
- `r01_final_report.md` omits captured post-reference entry cost discussion；
- `r01_final_report.md` counts `post_reference_capture_0_to_10_count` as an
  additional numerator on top of primary executable entry capture or recall-cost
  score；
- `r01_final_report.md` presents post30 T+0..T+30 profile coverage as executable
  primary entry capture or as decision-changing evidence；
- `fail_fast_survived_big_winner_recall_loss_vs_same_seed_no_fail_fast` cannot be reproduced from captured reference counts；
- `recall_cost_score` cannot be reproduced from `r01_recall_cost_tradeoff.csv` fields；
- net capture fields (`lost_capture_vs_ep2_count` / `net_added_capture_vs_ep2_count`) are missing or ignored by the post-reference capture gate；
- bounded recall-cost thresholds are missing from config, not reported in `r01_gate_audit.csv`, or ignored by `go_to_r02` / `go_to_r02_with_robustness_warning`；
- `failed_seed_label_a` appears as an ambiguous field instead of explicit H10/H20 Label A fields；
- fail-fast-exited episodes allow re-entry before deduped episode end without recording `suppressed_reentry_count`；
- Label A ATR audit cannot reproduce `atr20_asof` from required true-range formula；
- required report or core panel schemas are missing any required column；
- any hard fail gate fails；
- final decision cannot be reproduced from the §12.8 decision matrix；
- report decision is not exactly one of:
  `go_to_r02`,
  `go_to_r02_with_robustness_warning`,
  `go_to_oos_retest_required`,
  `archive_hypothesis_no_r02`,
  `archive_cost_control_sleeve_no_r02`,
  `stop_ep4_r01_path`。

---

## 15. R02 Handoff Contract

If R01 decision is `go_to_r02` or `go_to_r02_with_robustness_warning`, R02 may assume only:

```text
1. EP4 V3 post-reference entry seed has a frozen, tradable, density-bounded definition；
2. small probe post-reference entry attempts have controlled failed-entry cost；
3. deterministic fail-fast is fixed；
4. R01 V3 survived entries can be used as the only R02 post-reference hold / add-after-confirmation eligibility universe。
```

R02 may not assume:

```text
1. R01 V3 post-reference seed is already profitable as a standalone strategy；
2. R01 fail-fast is optimal；
3. surviving post-reference entries are worth adding；
4. ATR stop or state stop has any proven value；
5. portfolio-level risk budget is solved。
```

If R01 decision is `go_to_r02_with_robustness_warning`, R02 must carry the warning into its upstream caveat section and cannot loosen R01 gates to hide the weakness.

R02 must also add a first-class section:

```text
upstream_r01_robustness_warning
```

This section must list:

```text
1. which R01 robustness metrics weakened;
2. whether weakness concentrates by year / industry / liquidity bucket / volatility bucket;
3. which R01 diagnostics are relevant to the weakness;
4. how R02 will report validation and robustness separately.
```

R02 is not allowed to treat validation-only hold / add-after-confirmation lift as sufficient if the R01 warning was caused by robustness degradation in the same split / industry / bucket family.

External validity caveat:

```text
R01 evidence is limited to the frozen validation period and 2024-2025 robustness period.
It does not prove stability under future market-style breaks such as strong
regulatory shifts, persistent liquidity contraction, or a materially different
theme concentration regime.
```

If R01 decision is `archive_cost_control_sleeve_no_r02` or `stop_ep4_r01_path`, R02 must not start unless a new requirement explicitly changes the EP4 direction.

---

## 16. Summary

R01 V3 的正确名字不是 `Probe-Observe-Scale`，也不是 pre-launch high-recall seed，而是：

```text
Post-Reference Entry Capture Cost-Control
```

它只证明一个问题：

```text
reference_date 后 T+0..T+30 post30 profile seed
+ 小 probe + deterministic fail-fast
是否能以足够低的失败成本捕捉已经进入右尾展开期的 entry。
```

通过标准不是 AUC，不是 trigger rate，也不是单纯 recall。

通过标准是：

```text
post-reference capture 有可冻结分母；
seed 宽度有 density 上限；
fail-fast 有清楚 attribution；
matched baseline 下成本改善成立；
每新增 / 保留一个 post-reference big-winner capture 的试错成本可解释；
没有提前引入加仓、动态止损或组合层自由度。
```
