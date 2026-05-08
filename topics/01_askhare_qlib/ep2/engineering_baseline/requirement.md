# EP2 Engineering Baseline Requirement

## 1. Purpose

EP2 的正式研究对象是 **low-turnover launch exposure timing**，不是旧语义里的 single entry confirmation。

在进入正式 requirement、模型训练、hazard model 或任何 EP2-3 之前，必须先完成一个可复现的工程基座。这个基座只回答四件事：

1. frozen launch / observation pool 是否可以被机械生成；
2. PIT 输入、as-of、next-open execution 是否可审计；
3. confirm label / future path 是否可以按固定合同计算；
4. no-model exposure timing schedules 是否可以在同一执行状态机下公平比较。

本文件是 EP2-0 engineering baseline 的实现合同。完成本文件以前，不允许开始模型训练、feature search、模型阈值选择、portfolio selection 或 EP2-3。EP2-0 只允许执行本文件预注册的 label sweep 与 no-model baseline sweep。

## 2. Non-Goals

本阶段明确不做：

- 不训练 LGBM / hazard / ranking / classifier；
- 不新增 P1 candidate；
- 不做组合层与 BaseRate 年化收益直接比较；
- 不基于 no-model baseline 结果反复修改 launch detector；
- 不基于 2024 / 2025 robustness 年份选择 primary label；
- 不在 label sweep 以外进行任何事后 threshold 调整；
- 不把 Explore9 / Explore10 的 cache 输出作为权威输入。

## 3. Canonical Inputs

所有输入必须来自项目 canonical `data/` 目录。禁止从 Explore9 / Explore10 / BaseRate output cache 读取基础数据。

最低输入合同：

| Input | Required path | Role |
| --- | --- | --- |
| Qlib PIT provider | `data/qlib/cn_data_pit` | daily OHLCV / money / calendar |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` | launch pool eligibility |
| PIT qlib instrument map | `data/universe/pit_qlib_instrument_universe.csv` | code / instrument audit |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | concentration / industry audit |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | next trading day resolution |
| Qlib PIT instrument file | `data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt` | provider universe validation |
| Price adjustment mode | Qlib PIT adjusted OHLC fields with `factor` audit | adjustment consistency audit |

实现时如果路径名不同，必须在 `ep2/engineering_baseline/config.yaml` 中显式列出，并写入 manifest。不得在脚本里硬编码隐式 fallback。

最低 config key：

```yaml
data_sources:
  qlib_provider_uri: data/qlib/cn_data_pit
  pit_universe_path: data/universe/pit_mcap500_mainboard_daily.csv
  pit_qlib_instrument_universe_path: data/universe/pit_qlib_instrument_universe.csv
  pit_industry_path: data/targets/pit_industry_membership.csv
  trading_calendar_path: data/qlib/cn_data_pit/calendars/day.txt
  qlib_instrument_path: data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt
input_contract:
  required_min_date: 2017-07-04
  required_max_date: 2025-12-31
  required_universe_name: pit_mcap500_mainboard
output_root: ep2/engineering_baseline/outputs
launch_detector:
  version: EP2_LAUNCH_DETECTOR_V0
  price_breakout_lookback_days: 60
  price_breakout_min_return: 0.12
  money_ma_lookback_days: 20
  money_multiple_min: 2.0
  money_min_cny: 50000000
  min_history_days: 80
  episode_merge_gap_days: 20
  episode_end_after_no_signal_days: 20
execution:
  signal_date_rule: close_derived_signal_date
  decision_date_rule: same_as_signal_date_after_close
  execution_date_rule: next_trading_day(signal_date)
  blocked_execution_reasons:
    - missing_open
    - zero_volume
    - zero_money
    - limit_up_inferred
    - limit_down_inferred
    - not_universe_member
    - missing_calendar_next_day
    - missing_price_row
  limit_inference_pct:
    mainboard_default: 0.095
cost_model:
  cost_profile: base
  commission_bps_buy: 10
  commission_bps_sell: 10
  stamp_tax_bps_sell: 50
  slippage_bps_buy: 20
  slippage_bps_sell: 20
  min_commission_cny: null
  derived_buy_cost_bps: 30
  derived_sell_cost_bps: 80
probe_grid:
  max_probe_window: 10
  max_missed_gain: 0.08
  pre_probe_fast_fail_drawdown: 0.06
label_sweep:
  selection_scope_start: 2017-01-01
  selection_scope_end: 2023-12-31
  horizons: [5, 10, 20]
  upside_targets: [0.08, 0.10, 0.12, 0.15]
  drawdown_barriers: [0.04, 0.06, 0.08]
  same_day_policies:
    - conservative_fail
    - drop_ambiguous
    - target_first_optimistic
schedule_defaults:
  primary_H: 10
  probe_weight: 0.30
  full_weight: 1.00
  canonical_fast_fail_drawdown: 0.06
  natural_exit: next_open_after_H_trading_days
  fixed_delay_exact_day_only: true
  blocked_exit_retry:
    retry_until_executed: true
    max_retry_trading_days: 5
    if_still_blocked: mark_terminal_blocked_exit
    terminal_price_policy: last_available_close_for_audit_only
big_winner:
  primary:
    label_id: launch_big_winner_50h120
    horizon_days: 120
    upside_target: 0.50
  sensitivity:
    label_id: launch_big_winner_100h240
    horizon_days: 240
    upside_target: 1.00
baserate_reference:
  daily_baserate_turnover_proxy: 49.6886819783705
  turnover_proxy_unit: annualized
  source: BaseRate topk_50_dropout_5_daily base turnover_annualized
  source_path: BaseRate/outputs/alpha158_lgbm_oos/reports/base_rate_trade_summary_by_fold.csv
  source_hash: 72195c709fe306759d4776449045de0181adb417fa5aa3482a09175fc1b75593
  use: threshold_reference_only
required_schedules:
  buy_all_on_launch_hold_to_H:
    action: direct_exposure
    date_rule: launch_effective_date
    target_weight: 1.00
    fast_fail_enabled: false
  buy_all_on_launch_with_same_fast_fail:
    action: direct_exposure
    date_rule: launch_effective_date
    target_weight: 1.00
    fast_fail_enabled: true
  fixed_delay_1d:
    action: probe_entry
    date_rule: launch_effective_date + 1 trading day
    target_weight: 1.00
  fixed_delay_3d:
    action: probe_entry
    date_rule: launch_effective_date + 3 trading days
    target_weight: 1.00
  fixed_delay_5d:
    action: probe_entry
    date_rule: launch_effective_date + 5 trading days
    target_weight: 1.00
  fixed_delay_10d:
    action: probe_entry
    date_rule: launch_effective_date + 10 trading days
    target_weight: 1.00
  random_probe_within_launch_window:
    action: probe_entry
    date_rule: random_valid_probe_day
    target_weight: 1.00
  staged_buy_all:
    probe_date_rule: launch_effective_date
    probe_weight: 0.30
    confirm_add_date_rule: launch_effective_date + 3 trading days
    confirm_add_condition: none
    full_weight: 1.00
  probe_then_naive_add:
    probe_date_rule: launch_effective_date
    probe_weight: 0.30
    confirm_add_date_rule: launch_effective_date + 10 trading days
    confirm_add_condition: no_fast_fail
    full_weight: 1.00
  probe_with_simple_stop:
    probe_date_rule: launch_effective_date
    probe_weight: 0.30
    confirm_add_enabled: false
random_baseline:
  random_seed: 20260508
  n_repeats: 100
```

## 4. Output Layout

所有 EP2-0 输出只允许写到：

```text
ep2/engineering_baseline/outputs/
```

推荐目录：

```text
ep2/engineering_baseline/outputs/
  cache/
  reports/
  manifests/
```

row-level cache 写入 `cache/`。人工评审用 CSV / JSON / Markdown 写入 `reports/` 或 `manifests/`。

`config.yaml` 本身不是输出，但必须被 `ep2_required_artifact_authority.csv` 作为 `input_config` 记录，并参与 `ep2_engineering_baseline_manifest.json` 的 hash。

Cost model 必须以组件为权威口径。`derived_buy_cost_bps` 和 `derived_sell_cost_bps` 只能由组件计算：

```text
derived_buy_cost_bps =
  commission_bps_buy + slippage_bps_buy

derived_sell_cost_bps =
  commission_bps_sell + stamp_tax_bps_sell + slippage_bps_sell
```

所有 manifest / report 必须同时记录组件和 derived total。不得只记录 buy / sell total，否则 EP2 无法和 BaseRate after-cost 口径对齐。

`baserate_reference.daily_baserate_turnover_proxy` 是冻结的 read-only scalar，只能用于 `turnover_reduction_vs_daily_baserate` gate。它来自 BaseRate report summary / CSV report，不得读取 BaseRate cache，不得参与 launch signal、label、schedule selection 或任何数据 join。

## 5. Basic Launch Detector V0 Contract

EP2-0 使用一个保守、机械、可复现的 basic detector 来 freeze launch / observation pool。这个 detector 不是 alpha 结论，也不是后续可调参对象；它只是 EP2 exposure timing 的固定 denominator。

### 5.1 Detector formula

`EP2_LAUNCH_DETECTOR_V0` 只使用 `signal_date` 收盘时已经可见的数据：

```text
universe_ok =
  instrument is member of data/universe/pit_mcap500_mainboard_daily.csv on signal_date

history_ok =
  count_valid_close_rows(instrument, signal_date - 80 trading days, signal_date) >= 80

price_breakout =
  close[signal_date] / rolling_min(close, 60 trading days ending signal_date - 1) - 1 >= 0.12
  and close[signal_date] >= rolling_max(close, 60 trading days ending signal_date - 1)

money_surge =
  money[signal_date] >= 2.0 * mean(money, 20 trading days ending signal_date - 1)
  and money[signal_date] >= 50,000,000

basic_launch_signal =
  universe_ok
  and history_ok
  and price_breakout
  and money_surge
  and close[signal_date] is not null
  and money[signal_date] > 0
  and volume[signal_date] > 0
```

As-of rules:

- `close[signal_date]`, `money[signal_date]`, and `volume[signal_date]` are allowed because launch signal is close-derived after the close;
- all rolling reference windows must end at `signal_date - 1`;
- `open/high/low/close/volume/money` on `execution_date` are forbidden as detector inputs;
- universe and industry joins must use rows whose `date <= signal_date`, selecting the latest row for `(instrument, signal_date)` if the source is not fully daily.

### 5.2 Episode lifecycle

Episode construction is deterministic:

```text
episode starts at first basic_launch_signal after no active episode
same instrument signals within episode_merge_gap_days = 20 are merged into the active episode
episode_end_signal_date = last signal_date in episode + episode_end_after_no_signal_days
new signal after episode_end_signal_date starts a new episode
duplicate same instrument + same signal_date rows are dropped after deterministic sort by detector_id
```

Reset / end reasons must use this enum:

```text
new_basic_launch_signal
merged_within_gap
ended_after_no_signal_gap
non_executable_all_events
duplicate_dropped
```

The default detector dictionary must contain exactly one enabled detector row for V0:

```text
detector_family = price_breakout_money_surge
detector_id = EP2_LAUNCH_DETECTOR_V0_PRICE60_MONEY20
lookback_days = 80
threshold_config_key = launch_detector
lifecycle_role = start
enabled = true
```

## 6. Launch Detector Version Contract

### 6.1 Required manifest

每次 freeze pool 必须输出：

```text
ep2_pool_freeze_manifest.json
```

最低字段：

```json
{
  "launch_detector_version": "EP2_LAUNCH_DETECTOR_V0",
  "launch_detector_config_hash": "<sha256_of_canonical_launch_detector_config>",
  "universe_source": "data/universe/pit_mcap500_mainboard_daily.csv",
  "industry_source": "data/targets/pit_industry_membership.csv",
  "provider_uri": "data/qlib/cn_data_pit",
  "config_path": "ep2/engineering_baseline/config.yaml",
  "output_root": "ep2/engineering_baseline/outputs",
  "price_adjustment_mode": "qlib_pit_adjusted_ohlc_with_factor_audit",
  "episode_reset_rule": "merge_same_instrument_signals_within_20_trading_days",
  "episode_merge_gap_days": 20,
  "cost_profile": "base",
  "cost_components": {
    "commission_bps_buy": 10,
    "commission_bps_sell": 10,
    "stamp_tax_bps_sell": 50,
    "slippage_bps_buy": 20,
    "slippage_bps_sell": 20,
    "min_commission_cny": null
  },
  "derived_buy_cost_bps": 30,
  "derived_sell_cost_bps": 80,
  "baserate_reference": {
    "daily_baserate_turnover_proxy": 49.6886819783705,
    "turnover_proxy_unit": "annualized",
    "source": "BaseRate topk_50_dropout_5_daily base turnover_annualized",
    "source_path": "BaseRate/outputs/alpha158_lgbm_oos/reports/base_rate_trade_summary_by_fold.csv",
    "source_hash": "72195c709fe306759d4776449045de0181adb417fa5aa3482a09175fc1b75593",
    "use": "threshold_reference_only"
  },
  "signal_date_rule": "close_derived_signal_date",
  "decision_date_rule": "same_as_signal_date_after_close",
  "execution_date_rule": "next_trading_day(signal_date)",
  "generated_at": "<iso8601_timestamp>",
  "row_count": 0,
  "episode_count": 0
}
```

`launch_detector_config_hash` 必须由 detector config 的 canonical JSON 序列化结果计算。只要 detector formula、threshold、lookback、universe、industry、reset 或 merge 规则变化，hash 必须变化。

### 6.2 Required detector dictionary

必须输出：

```text
ep2_launch_detector_dictionary.csv
```

最低字段：

| Column | Meaning |
| --- | --- |
| `detector_family` | detector family name |
| `detector_id` | unique detector id |
| `formula_text` | human-readable mechanical formula |
| `required_fields` | semicolon-separated input fields |
| `lookback_days` | required lookback |
| `threshold_config_key` | config key used by threshold |
| `feature_asof_rule` | as-of rule for every required field |
| `lifecycle_role` | start / reset / merge / end / audit |
| `enabled` | boolean |

没有这个 dictionary，不允许生成 frozen pool。

## 7. Frozen Pool Hard Schema

必须输出：

```text
ep2_launch_observation_pool.parquet
ep2_launch_episode_dictionary.csv
ep2_pool_frequency_audit.csv
```

### 7.1 `ep2_launch_observation_pool.parquet`

最低字段：

| Column | Required rule |
| --- | --- |
| `launch_episode_id` | stable episode id, deterministic from detector version + instrument + episode start |
| `instrument` | Qlib instrument code |
| `signal_date` | close-derived launch signal date |
| `asof_date` | latest information date allowed for signal generation |
| `decision_date` | decision timestamp date, normally same as `signal_date` after close |
| `execution_date` | next trading day after `signal_date` |
| `execution_price_reference` | open price on `execution_date` if executable |
| `launch_effective_date` | first executable next-open date of the episode |
| `launch_detector_family` | detector family |
| `launch_detector_id` | detector id |
| `launch_event_rank_within_episode` | 1-based event order inside episode |
| `episode_start_signal_date` | first signal date of the episode |
| `episode_end_signal_date` | mechanically assigned end signal date |
| `episode_reset_reason` | reset / end reason |
| `universe_member_asof_signal_date` | PIT universe membership used at `signal_date` |
| `industry_asof_signal_date` | PIT industry used at `signal_date` |
| `is_executable_next_open` | boolean execution eligibility |
| `blocked_execution_reason` | empty if executable, otherwise normalized reason |
| `is_buy_executable_next_open` | boolean buy eligibility at next open |
| `is_sell_executable_next_open` | boolean sell eligibility at next open |
| `blocked_buy_reason` | empty if buy executable, otherwise normalized reason |
| `blocked_sell_reason` | empty if sell executable, otherwise normalized reason |
| `source_price_adjustment_mode` | adjustment mode used by all prices |

`launch_effective_date` 必须等于该 episode 的 first executable `execution_date`。如果一个 episode 没有任何 executable event，`launch_effective_date` 为空，且该 episode 只能进入 pool audit，不能进入 candidate probe grid。

`is_executable_next_open` and `blocked_execution_reason` are retained as backward-compatible summary fields and must equal `is_buy_executable_next_open and is_sell_executable_next_open` unless a row has direction-specific limit blocking. The simulator must use action direction:

```text
buy / add blocked if blocked_buy_reason is non-empty
sell / exit blocked if blocked_sell_reason is non-empty
limit_up_inferred blocks buy but does not block sell
limit_down_inferred blocks sell but does not block buy
missing_open / zero_volume / zero_money / missing_price_row block both directions
not_universe_member blocks opening new exposure, but does not block reducing or exiting an existing exposure
```

The no-model simulator must not silently rediscover these rules with a different口径.

### 7.2 `ep2_launch_episode_dictionary.csv`

最低字段：

| Column | Required rule |
| --- | --- |
| `launch_episode_id` | stable id |
| `instrument` | Qlib instrument code |
| `episode_start_signal_date` | start date |
| `episode_first_execution_date` | first next-open execution date |
| `launch_effective_date` | same as `episode_first_execution_date` |
| `episode_end_signal_date` | end date |
| `episode_reset_reason` | end / reset reason |
| `event_count` | launch event count in episode |
| `executable_event_count` | next-open executable count |
| `launch_detector_version` | detector version |
| `launch_detector_config_hash` | detector config hash |

### 7.3 Execution block reasons

`blocked_execution_reason` 必须使用固定枚举：

```text
missing_open
zero_volume
zero_money
limit_up_inferred
limit_down_inferred
not_universe_member
missing_calendar_next_day
missing_price_row
direction_specific_block
other
```

Direction-specific block fields must use the same enum. `blocked_execution_reason` should contain `blocked_buy_reason` when both directions are blocked by the same reason; otherwise it must be `direction_specific_block`.

## 8. Date, Execution, and Label Window Contract

EP2 使用 close-derived signal + next-open execution。

必须写死：

```text
signal_date = close-derived launch / confirmation / fail signal date
asof_date = signal_date
decision_date = signal_date after close
execution_date = next_trading_day(signal_date)
execution_price = open[execution_date]
label_path_start = execution_date
label_path_includes_execution_date_high_low = true
```

含义：

- 从 `execution_date` open 买入后，`execution_date` 当天 high / low / close 已经是持仓后的路径；
- label window 不能错误地从 `execution_date + 1` 开始；
- `execution_date` open 可以作为执行价；
- `execution_date` high / low / close / volume / money 不得作为 predictive signal feature；
- launch / probe / confirm / fail signal 的 feature-asof 只能到 `signal_date` close。

必须输出：

```text
ep2_pit_input_audit.csv
ep2_feature_asof_audit.csv
ep2_execution_block_audit.csv
```

`ep2_pit_input_audit.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `input_name` | qlib_provider / pit_universe / pit_industry / calendar / qlib_instrument |
| `input_path` | project-relative path |
| `exists` | boolean |
| `row_count` | row count if tabular |
| `min_date` | earliest date if available |
| `max_date` | latest date if available |
| `instrument_count` | unique instruments if available |
| `required_min_date` | required start date |
| `required_max_date` | required end date |
| `date_coverage_pass` | boolean |
| `instrument_join_pass` | boolean |
| `content_hash` | file or directory content hash |
| `violation_reason` | empty if pass |

`ep2_feature_asof_audit.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `feature_name` | feature / detector field |
| `source_field` | raw input |
| `feature_asof_rule` | date rule |
| `max_allowed_date_relation` | must be `<= signal_date` |
| `uses_execution_date_intraday` | boolean, must be false for predictive fields |
| `violation_count` | count |

`ep2_execution_block_audit.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `blocked_execution_reason` | normalized reason |
| `trade_direction` | buy / sell / both |
| `row_count` | count |
| `episode_count` | unique episodes |
| `row_share` | share of pool rows |
| `episode_share` | share of episodes |

## 9. Candidate Probe Grid Contract

所有 label sweep、random baseline、fixed delay baseline、schedule simulator 必须共享同一个 candidate probe grid。

必须输出：

```text
ep2_candidate_probe_grid.parquet
```

最低字段：

| Column | Required rule |
| --- | --- |
| `launch_episode_id` | episode id |
| `instrument` | instrument |
| `probe_signal_date` | candidate close-derived probe signal date |
| `probe_execution_date` | next trading day after `probe_signal_date` |
| `probe_execution_price_reference` | open price on `probe_execution_date` if executable |
| `launch_effective_date` | first executable next-open date of the episode |
| `days_from_launch_execution` | trading-day distance from first launch execution |
| `max_probe_window` | configured max probe window |
| `max_missed_gain` | configured missed-gain ceiling |
| `is_within_allowed_probe_window` | boolean |
| `is_executable_next_open` | boolean |
| `blocked_execution_reason` | normalized reason |
| `is_buy_executable_next_open` | boolean |
| `blocked_buy_reason` | normalized buy block reason |
| `pre_probe_fast_fail_from_launch_reference` | boolean path invalidation before this candidate, if configured |
| `episode_already_terminal_before_probe` | boolean |
| `missed_gain_to_probe` | gain from launch execution reference to probe execution reference |
| `is_valid_probe_candidate` | final boolean |

Candidate rule:

```text
valid probe day =
  trading day within [launch_effective_date, launch_effective_date + max_probe_window]
  and next-open buy executable
  and no episode terminal state before this probe day
  and no configured pre-probe fast-fail from launch reference
  and missed_gain_to_probe <= max_missed_gain
```

如果同一 episode 多天满足模型或 rule threshold，schedule 只能使用 earliest valid day。禁止用后段确认日补票。

注意：candidate grid 的 `pre_probe_fast_fail_from_launch_reference` 只用于 probe 前的路径失效审计。schedule 执行后的 `fast_fail_exit` 必须由 no-model state machine 根据 actual exposure price 单独计算，不能复用 candidate grid 的字段。

Fixed-delay schedules use exact-day-only behavior:

```text
fixed_delay_exact_day_only = true
if configured target probe day is not a valid probe candidate:
  schedule episode = no_probe
```

No main baseline may roll forward from a blocked fixed-delay day to the next valid day. Any next-valid-day variant must be named separately as sensitivity, for example `fixed_delay_5d_next_valid_sensitivity`.

## 10. Label Sweep and Freeze Candidate Contract

EP2-0 只输出 label freeze candidate，不自动选择 primary label。

必须输出：

```text
ep2_path_label_panel.parquet
ep2_label_sweep_grid.csv
ep2_label_freeze_candidate.csv
```

`ep2_path_label_panel.parquet` 是 row-level label 审计依据，最低字段：

| Column | Meaning |
| --- | --- |
| `label_id` | deterministic label id |
| `launch_episode_id` | episode id |
| `instrument` | instrument |
| `probe_signal_date` | candidate probe signal date |
| `probe_execution_date` | candidate probe execution date |
| `horizon` | label horizon |
| `upside` | upside target |
| `drawdown` | drawdown barrier |
| `same_day_policy` | ambiguity policy |
| `path_start_date` | must equal `probe_execution_date` |
| `first_target_date` | first target hit date |
| `first_drawdown_date` | first drawdown hit date |
| `same_day_ambiguous` | boolean |
| `label_value` | 1 success, 0 fail, null if dropped |
| `after_cost_return_to_exit` | path return under the label exit rule |

### 10.1 Sweep grid

`ep2_label_sweep_grid.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `label_id` | deterministic label id |
| `horizon` | 5d / 10d / 20d |
| `upside` | upside target |
| `drawdown` | drawdown barrier |
| `same_day_policy` | ambiguity policy |
| `candidate_positive_rate` | candidate-row success rate |
| `episode_any_positive_rate` | share of episodes with at least one positive valid candidate |
| `episode_first_valid_positive_rate` | share of episodes whose first valid candidate is positive |
| `episode_weighted_positive_rate` | episode-equal weighted candidate success rate |
| `event_count` | valid candidate count |
| `episode_count` | unique episode count |
| `year_count` | number of years represented |
| `top1_instrument_year_positive_share` | concentration |
| `same_day_ambiguity_rate` | ambiguity share |
| `median_after_cost_return` | median next-open executable after-cost return |

Supported `same_day_policy` values:

```text
conservative_fail
drop_ambiguous
target_first_optimistic
```

Primary selection scope must be fixed to:

```text
selection_scope = 2017_2023_core_research_years
```

2024 / 2025 can only be robustness years. They must not be used to choose label thresholds.

### 10.2 Freeze candidate

`ep2_label_freeze_candidate.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `label_id` | deterministic label id |
| `selection_scope` | must be `2017_2023_core_research_years` |
| `selection_reason` | short text |
| `passed_candidate_base_rate_gate` | boolean |
| `passed_episode_base_rate_gate` | boolean |
| `passed_ambiguity_gate` | boolean |
| `passed_concentration_gate` | boolean |
| `frozen_for_ep2_2` | boolean |

Gate defaults:

```yaml
label_sweep:
  candidate_positive_rate_min: 0.20
  candidate_positive_rate_max: 0.55
  episode_positive_rate_min: 0.20
  episode_positive_rate_max: 0.55
  max_same_day_ambiguity_rate: 0.20
  max_top1_instrument_year_positive_share: 0.10
```

Primary label freeze 必须同时通过 candidate-level base rate gate、episode-level base rate gate、same-day ambiguity gate 和 instrument-year concentration gate。如果 primary label 后续被重挑，必须视为 EP2 研究重启，不能只重跑局部结果。

## 11. Unified No-Model Schedule State Machine

所有 no-model baseline 必须走同一状态机，不能每个 baseline 各写一套执行逻辑。

状态：

```text
no_exposure
partial_exposure
full_exposure
exited
```

动作：

```text
direct_exposure -> full_exposure
probe_entry -> partial_exposure
confirm_add -> full_exposure
fast_fail_exit -> exited
natural_exit -> exited
blocked_action -> state unchanged
```

`direct_exposure` 只允许用于 required buy-all baseline；所有 staged schedules 必须使用 `probe_entry` / `confirm_add`。

每个 schedule 只能通过 config 填入 date rule、condition、target weight、fast-fail、natural-exit，不允许改状态机代码口径。

同一 signal date 上多个动作同时触发时，必须使用固定优先级：

```text
fast_fail_exit
natural_exit
confirm_add
probe_entry
direct_exposure
```

执行顺序固定为 sell / exit before buy / add。blocked sell 保持原持仓；blocked buy / add 的未成交 notional 保留为 cash。

Blocked exit retry is mandatory for `fast_fail_exit` and `natural_exit`:

```text
if exit is blocked:
  keep actual exposure unchanged
  retry exit at each next trading day open
  stop retry after max_retry_trading_days = 5
  if still blocked: state = exited only for evaluation, exit_status = terminal_blocked_exit
  terminal_price_policy = last_available_close_for_audit_only
```

`terminal_price_policy` is only an audit valuation policy. It must be reported separately and must not be presented as an executable fill.

示例：

```yaml
schedule_id: probe_with_simple_stop
probe:
  date_rule: launch_effective_date
  target_weight: 0.30
confirm_add:
  date_rule: launch_effective_date + 10 trading days
  condition: none
  target_weight: 1.00
fast_fail:
  rule: drawdown_from_exposure_price <= -0.06
  exit_price: next_open_after_signal
natural_exit:
  if: no_confirm_add_and_no_fast_fail_exit
  exit: next_open_after_H_trading_days
```

Default natural exit:

```yaml
default_natural_exit:
  if: no_confirm_add and no_fast_fail_exit
  exit: next_open_after_H_trading_days
```

其中 `H` 必须与 primary label horizon 对齐。10d primary label 使用 H=10d；20d sensitivity 使用 H=20d。

## 12. Required No-Model Baselines

最低 required baselines：

```yaml
required_baseline:
  - buy_all_on_launch_hold_to_H
  - buy_all_on_launch_with_same_fast_fail
  - fixed_delay_1d
  - fixed_delay_3d
  - fixed_delay_5d
  - fixed_delay_10d
  - random_probe_within_launch_window
  - staged_buy_all
  - probe_then_naive_add
  - probe_with_simple_stop
```

两个 buy-all baseline 不能 optional：

| Baseline | Question |
| --- | --- |
| `buy_all_on_launch_hold_to_H` | 分阶段 exposure 是否优于看到 launch 就全买 |
| `buy_all_on_launch_with_same_fast_fail` | 分阶段 sizing 是否优于全仓 + 同样 fast-fail |

如果 schedule 只跑赢 `buy_all_on_launch_hold_to_H`，但跑不赢 `buy_all_on_launch_with_same_fast_fail`，结论必须写成：价值主要来自 stop，不是 exposure timing。

buy-all baseline 配置必须使用 `direct_exposure`：

```yaml
buy_all_on_launch_hold_to_H:
  direct_exposure:
    date_rule: launch_effective_date
    target_weight: 1.00
  natural_exit:
    exit: next_open_after_H_trading_days
buy_all_on_launch_with_same_fast_fail:
  direct_exposure:
    date_rule: launch_effective_date
    target_weight: 1.00
  fast_fail:
    rule: canonical_fast_fail_drawdown
  natural_exit:
    exit: next_open_after_H_trading_days
```

`canonical_fast_fail_drawdown` 固定为 `drawdown_from_exposure_price <= -0.06`，从实际成交的 first exposure price 起算。两个 buy-all baseline 必须只生成一次，不允许针对每个 schedule 生成不同版本。

全部 required schedules 必须按 §3 `required_schedules` 的配置生成：

| Schedule | Exposure rule | Exit rule |
| --- | --- | --- |
| `buy_all_on_launch_hold_to_H` | `direct_exposure` 100% at `launch_effective_date` | natural exit only |
| `buy_all_on_launch_with_same_fast_fail` | `direct_exposure` 100% at `launch_effective_date` | canonical fast-fail or natural exit |
| `fixed_delay_1d` | `probe_entry` 100% at `launch_effective_date + 1 trading day` | canonical fast-fail or natural exit |
| `fixed_delay_3d` | `probe_entry` 100% at `launch_effective_date + 3 trading days` | canonical fast-fail or natural exit |
| `fixed_delay_5d` | `probe_entry` 100% at `launch_effective_date + 5 trading days` | canonical fast-fail or natural exit |
| `fixed_delay_10d` | `probe_entry` 100% at `launch_effective_date + 10 trading days` | canonical fast-fail or natural exit |
| `random_probe_within_launch_window` | `probe_entry` 100% on one random valid probe day | canonical fast-fail or natural exit |
| `staged_buy_all` | 30% probe at launch, unconditional add to 100% after 3 trading days | canonical fast-fail or natural exit |
| `probe_then_naive_add` | 30% probe at launch, add to 100% after 10 trading days if no fast-fail | canonical fast-fail or natural exit |
| `probe_with_simple_stop` | 30% probe at launch, no confirm add | canonical fast-fail or natural exit |

For all schedules, `natural_exit` is measured from the first executed exposure date, not from `signal_date`. If the first exposure is blocked and never fills, the episode is counted as `no_exposure`.

## 13. Random Baseline Contract

必须固定 random baseline 的 seed、重复次数、matching 维度。

```yaml
random_probe_within_launch_window:
  random_seed: 20260508
  n_repeats: 100
  sample_unit: launch_episode
  match_by:
    - launch_episode
    - allowed_probe_window
    - executable_day_count
  output:
    - random_mean
    - random_std
    - random_p05
    - random_p50
    - random_p95
```

random baseline 必须使用：

- same frozen pool；
- same candidate probe grid；
- same next-open execution；
- same cost model；
- same fast-fail rule；
- same natural exit；
- same blocked execution logic；
- same H horizon。

random sampling 只能从 `is_valid_probe_candidate = true` 的 candidate grid 中抽样。若某 episode 没有 valid candidate，该 episode 在 random baseline 中记为 `no_probe`，不能从 invalid date 补样。

不允许只做一次 random draw。`ep2_no_model_baseline_comparison.csv` 必须同时报告每个 schedule 相对 random distribution 的 p05 / p50 / p95 位置。

## 14. Simulator Row-Level Artifacts

必须输出：

```text
ep2_schedule_action_panel.parquet
ep2_exposure_daily_panel.parquet
ep2_no_model_baseline_results.csv
ep2_no_model_baseline_comparison.csv
ep2_no_model_baseline_gate.csv
```

### 14.1 `ep2_schedule_action_panel.parquet`

最低字段：

| Column | Meaning |
| --- | --- |
| `schedule_id` | schedule id |
| `launch_episode_id` | episode id |
| `instrument` | instrument |
| `signal_date` | close-derived action signal date |
| `decision_date` | decision date |
| `execution_date` | next-open execution date |
| `action_type` | normalized action enum |
| `state_before` | state before action |
| `state_after` | state after action |
| `target_weight_before` | before action |
| `target_weight_after` | after action |
| `order_notional` | normalized notional |
| `execution_price` | next-open price |
| `is_executed` | boolean |
| `blocked_reason` | normalized reason |
| `commission_cost` | commission component |
| `stamp_tax_cost` | sell stamp-tax component |
| `slippage_cost` | slippage component |
| `cost` | total execution cost |
| `cash_weight` | cash after action |
| `exit_retry_count` | retry count for blocked exit actions |
| `exit_status` | normal_exit / retry_exit / terminal_blocked_exit / not_exit |
| `terminal_price_policy` | empty unless terminal blocked exit audit valuation is used |

`action_type` 允许值必须固定为：

```text
direct_exposure
probe_entry
confirm_add
fast_fail_exit
natural_exit
blocked_action
```

### 14.2 `ep2_exposure_daily_panel.parquet`

最低字段：

| Column | Meaning |
| --- | --- |
| `date` | trading date |
| `schedule_id` | schedule id |
| `launch_episode_id` | episode id |
| `instrument` | instrument |
| `state` | exposure state |
| `target_weight` | target exposure |
| `actual_weight` | executed exposure |
| `cash_weight` | residual cash |
| `daily_return_gross` | gross return |
| `daily_return_net` | after-cost return |
| `cum_return_gross` | cumulative gross |
| `cum_return_net` | cumulative net |

## 15. Metrics and Gate Formulas

### 15.1 Big-winner coverage definition

Primary big-winner definition:

```text
launch_big_winner_50h120 =
  max(high over [launch_effective_date, launch_effective_date + 119 trading days])
  / launch_execution_price - 1 >= 0.50

first_50pct_target_date =
  first date in that window where high / launch_execution_price - 1 >= 0.50

schedule_big_winner_capture =
  launch_big_winner_50h120 = true
  and schedule obtains positive actual exposure before or on first_50pct_target_date
  and schedule is not fully exited before first_50pct_target_date

big_winner_capture_rate =
  captured_big_winner_episode_count / launch_big_winner_episode_count
```

Sensitivity:

```text
big_winner_100h240_capture_rate uses upside_target = 1.00 and horizon_days = 240
```

This is episode capture, not profit capture. Reports may add realized return diagnostics, but `big_winner_coverage_loss_vs_buy_all` must use episode capture.

### 15.2 Baseline result schema

`ep2_no_model_baseline_results.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `schedule_id` | schedule |
| `episode_count` | unique episodes |
| `episode_with_any_exposure_count` | episodes with positive actual exposure |
| `no_probe_count` | episodes without probe / direct exposure |
| `no_probe_rate` | no-probe share |
| `probe_rate` | episodes with probe |
| `confirm_add_rate` | episodes with confirm add |
| `fast_fail_exit_rate` | episodes fast-failed |
| `natural_exit_rate` | episodes naturally exited |
| `blocked_buy_rate` | blocked buy / add action rate |
| `blocked_sell_rate` | blocked sell / exit action rate |
| `blocked_exit_retry_rate` | episodes with at least one blocked exit retry |
| `blocked_exit_retry_count` | total blocked exit retries |
| `terminal_blocked_exit_rate` | episodes terminal due to blocked exit retry exhaustion |
| `blocked_exit_return_impact` | terminal-blocked audit valuation impact |
| `mean_cash_weight` | average daily cash weight |
| `cash_drag` | return impact from unfilled cash exposure |
| `natural_exit_return` | mean natural-exit net return |
| `natural_exit_median_days` | median days to natural exit |
| `mean_days_to_first_exposure` | mean days from launch effective date to first exposure |
| `mean_after_cost_return` | mean net return |
| `median_after_cost_return` | median net return |
| `p05_after_cost_return` | lower tail net return |
| `p95_after_cost_return` | upper tail net return |
| `big_winner_capture_rate` | share of launch-pool big winners captured |
| `big_winner_100h240_capture_rate` | sensitivity capture rate |
| `missed_gain_to_exposure_median` | median missed gain |
| `turnover_proxy` | normalized turnover |
| `top1_instrument_year_exposure_share` | concentration |
| `top5_instrument_exposure_share` | concentration |

Gate defaults:

```yaml
timing_gate:
  min_after_cost_lift_vs_random: 1.05
  max_big_winner_coverage_loss_vs_buy_all: 0.20
  max_median_missed_gain_to_exposure: 0.08
  max_top1_instrument_year_exposure_share: 0.10
  max_top5_instrument_exposure_share: 0.35
  min_turnover_reduction_vs_daily_baserate: 0.50
```

Required formulas:

```text
after_cost_lift_vs_random =
  schedule_mean_after_cost_return / random_mean_after_cost_return
  when random_mean_after_cost_return > 0

after_cost_diff_vs_random =
  schedule_mean_after_cost_return - random_mean_after_cost_return

big_winner_coverage_loss_vs_buy_all =
  1 - schedule_big_winner_capture_rate / buy_all_big_winner_capture_rate

turnover_reduction_vs_daily_baserate =
  1 - schedule_turnover_proxy / daily_baserate_turnover_proxy
```

`daily_baserate_turnover_proxy` must come from `baserate_reference.daily_baserate_turnover_proxy` in `config.yaml`. `ep2_engineering_baseline_manifest.json` must record `baserate_reference.source`, `source_path`, `source_hash`, and `use = threshold_reference_only`.

如果 `random_mean_after_cost_return <= 0`，`after_cost_lift_vs_random` 不得作为唯一 gate，必须同时报告 `after_cost_diff_vs_random` 和 random percentile comparison。

`ep2_no_model_baseline_comparison.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `schedule_id` | schedule under evaluation |
| `comparison_id` | random / buy_all_hold_to_H / buy_all_same_fast_fail |
| `comparison_schedule_id` | concrete baseline schedule |
| `mean_after_cost_return_diff` | schedule minus comparison |
| `median_after_cost_return_diff` | schedule minus comparison |
| `after_cost_lift` | ratio when denominator is positive |
| `random_p05` | random distribution p05, null for non-random comparison |
| `random_p50` | random distribution p50, null for non-random comparison |
| `random_p95` | random distribution p95, null for non-random comparison |
| `schedule_random_percentile` | percentile rank, null for non-random comparison |
| `big_winner_coverage_loss` | loss versus comparison |
| `turnover_reduction` | reduction versus comparison |

`ep2_no_model_baseline_gate.csv` 必须逐 schedule 输出每个 gate 的 pass/fail 与失败原因。最低字段：

| Column | Meaning |
| --- | --- |
| `schedule_id` | schedule under evaluation |
| `gate_name` | gate id |
| `gate_value` | observed value |
| `threshold_value` | required threshold |
| `comparison_id` | comparison used by this gate |
| `passed` | boolean |
| `failure_reason` | empty if pass |
| `is_hard_stop` | boolean |

## 16. Artifact Authority and Engineering Manifest

必须输出：

```text
ep2_engineering_baseline_manifest.json
ep2_required_artifact_authority.csv
ep2_threshold_config_consistency_audit.csv
```

### 16.1 Required artifact authority

`ep2_required_artifact_authority.csv` 至少列出：

```text
ep2_engineering_baseline_manifest.json
ep2_launch_observation_pool.parquet
ep2_launch_episode_dictionary.csv
ep2_pool_freeze_manifest.json
ep2_launch_detector_dictionary.csv
ep2_pool_frequency_audit.csv
ep2_pit_input_audit.csv
ep2_feature_asof_audit.csv
ep2_execution_block_audit.csv
ep2_candidate_probe_grid.parquet
ep2_path_label_panel.parquet
ep2_label_sweep_grid.csv
ep2_label_freeze_candidate.csv
ep2_schedule_action_panel.parquet
ep2_exposure_daily_panel.parquet
ep2_no_model_baseline_results.csv
ep2_no_model_baseline_comparison.csv
ep2_no_model_baseline_gate.csv
ep2_threshold_config_consistency_audit.csv
config.yaml
```

最低字段：

| Column | Meaning |
| --- | --- |
| `artifact_name` | file name |
| `artifact_path` | relative path from project root; output artifacts must live under `ep2/engineering_baseline/outputs/` |
| `authority_role` | input_config / cache / report / manifest / audit |
| `producer_command` | command that generates it |
| `schema_version` | schema version |
| `required_for_requirement` | boolean |
| `row_count` | row count if tabular |
| `content_hash` | file content hash |

### 16.2 Threshold consistency audit

`ep2_threshold_config_consistency_audit.csv` 最低字段：

| Column | Meaning |
| --- | --- |
| `config_key` | threshold key |
| `config_value` | value |
| `used_by_artifacts` | semicolon-separated artifact list |
| `expected_value` | expected frozen value |
| `is_consistent` | boolean |
| `violation_reason` | empty if pass |

## 17. Commands

最低命令面：

```text
python ep2/engineering_baseline/scripts/build_launch_pool.py --config ep2/engineering_baseline/config.yaml
python ep2/engineering_baseline/scripts/audit_ep2_pit_inputs.py --config ep2/engineering_baseline/config.yaml
python ep2/engineering_baseline/scripts/sweep_confirm_labels.py --config ep2/engineering_baseline/config.yaml
python ep2/engineering_baseline/scripts/run_no_model_baselines.py --config ep2/engineering_baseline/config.yaml
python ep2/engineering_baseline/scripts/validate_engineering_baseline.py --config ep2/engineering_baseline/config.yaml
```

`validate_engineering_baseline.py` 必须检查：

- required artifact 全部存在；
- hard schema columns 全部存在；
- manifest hash 与 config 一致；
- `config.yaml` 被 artifact authority 记录为 `input_config`；
- `ep2_pit_input_audit.csv` 中所有 required inputs 的 `exists/date_coverage_pass/instrument_join_pass` 均为 true；
- cost model derived totals equal component sums；
- buy / sell executable fields exist and limit-up / limit-down direction rules are respected；
- blocked exit retry rows obey `max_retry_trading_days = 5` and terminal blocked exits are reported separately；
- fixed-delay schedules use exact-day-only no-probe behavior when the target day is not a valid candidate；
- frozen pool 的 `execution_date = next_trading_day(signal_date)`；
- episode dictionary 的 `launch_effective_date = episode_first_execution_date`；
- label window 从 `execution_date` 开始；
- `ep2_path_label_panel.parquet.path_start_date = probe_execution_date`；
- predictive feature 不使用 execution date intraday fields；
- random baseline repeat count 达到 `n_repeats`；
- random baseline 只从 valid probe candidates 抽样；
- required buy-all baselines 不缺失；
- buy-all baselines 使用 `direct_exposure`；
- `ep2_label_freeze_candidate.csv` 没有使用 2024 / 2025 选择 threshold；
- label sweep includes candidate-level and episode-level positive rates；
- big-winner capture fields use `launch_big_winner_50h120` and exposure-before-target definitions；
- `baserate_reference` is read-only threshold metadata and no BaseRate cache is read；
- no-model schedule 全部使用统一状态机输出 row-level ledger；
- 同日动作冲突按固定优先级处理。

## 18. Stop / Proceed Rules

### 18.1 Hard stop

出现任一情况必须停止，不进入正式 EP2 requirement：

1. launch detector dictionary 缺失或 detector config hash 不可复现；
2. frozen pool hard schema 缺字段；
3. buy / sell direction-specific execution fields 未在 pool 层固定；
4. date contract 存在 off-by-one 或 execution-date intraday leakage；
5. cost model 只记录 total bps，未记录组件；
6. blocked exit retry / terminal blocked exit 未定义或未审计；
7. label sweep candidate-level 或 episode-level base rate 全部落在不可学区间之外；
8. same-day ambiguity rate 超过 gate 且无法解释；
9. big-winner capture 没有按 episode-level exposure-before-target 定义；
10. no-model schedule 完全跑不赢 same-pool random exposure；
11. no-model schedule 跑不赢任一 required buy-all baseline；
12. 需要重定义 launch detector 或重挑 label 才能让结果成立。

### 18.2 Proceed to formal requirement

仅当以下条件全部满足，才允许产出正式 EP2 requirement：

1. `ep2_engineering_baseline_manifest.json` 完整；
2. `ep2_required_artifact_authority.csv` 完整；
3. pool / PIT / feature-asof / execution audits 通过；
4. label freeze candidate 至少有一个 `frozen_for_ep2_2 = true`；
5. no-model baseline gate 对至少一个 schedule 全部通过；
6. buy-all fair baselines 与 random baseline 均已生成并进入 comparison；
7. 所有输出可由固定 config 和命令重跑得到。
