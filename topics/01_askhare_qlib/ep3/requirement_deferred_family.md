# EP3 Deferred Family Requirement

> Requirement id: `ep3_deferred_family_failure_lookalike_audit`
> Status: implementation-ready requirement
> Scope: EP3 deferred-family audit after P0 engineering-baseline no-go and P0.5 diagnostic
> Upstream P0 authority: `ep3/engineering_baseline/outputs/manifests/ep3_engineering_baseline_manifest.json`
> Upstream P0.5 authority: `ep3/outputs/p0_5_anchor_failure_diagnostic/manifests/p0_5_anchor_failure_diagnostic_manifest.json`

## 1. Background And Problem Chain

EP3 的初始目标是寻找 winner formation anchor，而不是继续修 EP2
continuation filter。EP3 engineering baseline 预注册并实现了两个 primary
anchor family：

```text
A. pullback_hold_restrengthen
C. second_breakout
```

Engineering baseline 的结果不是 validator 失败，而是研究假设失败：

| Family | P0 status | Passed gates | Failed gates | Lifecycle recall | Validation raw trigger rate | Validation H20 eligible trigger rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `pullback_hold_restrengthen` | `failed_trigger_budget` | 7 | 8 | 0.3445945946 | 0.1697761194 | 0.1436567164 |
| `second_breakout` | `failed_trigger_budget` | 9 | 6 | 0.4611486486 | 0.1305970149 | 0.1194029851 |

Interpretation:

```text
winner lifecycle 中确实能观察到 A/C 类 anchor；
但 A/C 没有转化成足够多、足够稳定、相对 matched baseline 有正 lift 的
forward-audit executable events。
```

P0.5 diagnostic 进一步确认：

| Finding | `pullback_hold_restrengthen` | `second_breakout` |
| --- | ---: | ---: |
| validation H20 mean diff vs matched-delay | -0.0208543 | -0.0076565 |
| validation H20 p05 diff vs matched-delay | -0.0157375 | -0.0409269 |
| robustness H20 mean diff vs matched-delay | 0.0160850 | -0.0100071 |
| robustness H20 p05 diff vs matched-delay | -0.0052283 | -0.0436761 |
| validation matched-delay underperformance rate | 0.630137 | 0.492063 |
| robustness matched-delay underperformance rate | 0.385965 | 0.614035 |

P0.5 hypothesis audit result:

```text
h1_formula_too_narrow: rejected for both A/C
h2_window_position_problem: rejected for both A/C
h3_ep2_reference_pollution: rejected for both A/C
h4_matched_baseline_too_strong_or_anchor_no_lift: supported for both A/C
h5_tail_risk_not_trigger_rate_is_core_failure: supported for both A/C
```

The important negative result is:

```text
There is no validation-positive and robustness-not-collapsed partition that can
justify P0.6 partition-freeze or formula-repair work for A/C.
```

The only validation interpretable partition that reached trigger rate >= 0.20
was:

```text
family = second_breakout
axis = ret_60d_bucket
bucket = 4
trigger_rate = 0.237624
mean_diff_vs_matched_delay = -0.014381
p05_diff_vs_matched_delay = -0.054878
```

So the failure is not simply "too few triggers". The only sufficiently frequent
partition still fails matched-delay lift and tail.

P0.5 final decision:

| Scope | Family | Decision |
| --- | --- | --- |
| family | `pullback_hold_restrengthen` | `stop_current_family` |
| family | `second_breakout` | `stop_current_family` |
| overall | `all` | `write_deferred_family_requirement` |

This requirement follows that decision. It does not attempt to rescue A/C. It
starts a new deferred-family audit centered on:

```text
failed_lookalike_avoidance
```

Reason:

```text
EP3 lifecycle profile contains 773 train-split winner episodes with
anchor_family_id = failed_lookalike_avoidance.
```

This means the next useful question is not "can we slightly repair A/C?" but:

```text
Can we mechanically distinguish true winner formation from failed lookalike
states before forward-audit failure, using only observable data as of the
signal date?
```

## 2. Phase Boundary

This phase is not P1. It is a deferred-family audit / requirement bridge.

Allowed:

- derive observable failure-lookalike diagnostics from frozen EP3 P0 and P0.5
  outputs;
- define candidate observable conditions for `failed_lookalike_avoidance`;
- build forward-audit event panels and matched baselines for the deferred
  family;
- compare the deferred family against A/C failure rows, matched-delay baseline,
  same-instrument nonanchor baseline, industry baseline, and all-launch direct
  baseline;
- produce a go/no-go recommendation for a later P0.6 requirement only.

Forbidden:

- no model training;
- no validation-selected threshold;
- no robustness-selected threshold;
- no portfolio backtest;
- no production signal;
- no P1 candidate output;
- no reuse of EP2 R02 / R03 / R05 selection artifacts;
- no modification of EP3 P0 or P0.5 frozen artifacts;
- no treating A/C stopped families as active strategy candidates.

Validation and robustness may only be used to evaluate frozen train-derived or
config-static partitions.

## 3. Research Question

Primary research question:

```text
Do observable failed-lookalike avoidance states explain why A/C winner-like
anchors fail, and can they define a deferred family with better H20 forward
audit behavior than A/C and matched baselines?
```

Sub-questions:

1. Are P0 A/C failed forward-audit events concentrated in observable
   failure-lookalike states?
2. Do true winner episodes pass through failed-lookalike states, and if so what
   later observable transition separates recovery from persistent failure?
3. Can an observable avoidance / recovery condition produce enough trigger coverage while
   improving H20 mean, p05, MAE, winner capture, and instrument-year stability?
4. Is the effect stable in validation and robustness without selecting buckets
   from validation or robustness?

## 4. Canonical Inputs

This phase must use only the following inputs:

| Input | Path | Role |
| --- | --- | --- |
| EP3 P0 manifest | `ep3/engineering_baseline/outputs/manifests/ep3_engineering_baseline_manifest.json` | frozen upstream authority |
| EP3 P0 winner labels | `ep3/engineering_baseline/outputs/cache/ep3_winner_label_panel.parquet` | label and horizon eligibility |
| EP3 P0 candidate anchors | `ep3/engineering_baseline/outputs/cache/ep3_candidate_anchor_panel.parquet` | stopped A/C anchor reference |
| EP3 P0 matched baselines | `ep3/engineering_baseline/outputs/cache/ep3_matched_baseline_panel.parquet` | baseline comparators |
| EP3 P0 lifecycle profile | `ep3/engineering_baseline/outputs/reports/ep3_winner_lifecycle_profile.csv` | deferred-family lifecycle source |
| EP3 P0 gate audit | `ep3/engineering_baseline/outputs/reports/ep3_gate_audit.csv` | P0 no-go evidence |
| EP3 P0 anchor metrics | `ep3/engineering_baseline/outputs/reports/ep3_anchor_vs_matched_baseline.csv` | P0 forward-audit reference |
| EP3 P0 anchor windows | `ep3/engineering_baseline/outputs/reports/ep3_anchor_window_freeze.csv` | reference windows |
| EP3 P0 bucket freeze | `ep3/engineering_baseline/outputs/reports/ep3_matched_control_bucket_freeze.csv` | train-frozen money / vol20 / ret60 buckets |
| EP3 P0.5 manifest | `ep3/outputs/p0_5_anchor_failure_diagnostic/manifests/p0_5_anchor_failure_diagnostic_manifest.json` | diagnostic authority |
| P0.5 anchor diagnostic panel | `ep3/outputs/p0_5_anchor_failure_diagnostic/cache/p0_5_anchor_event_diagnostic_panel.parquet` | A/C failure diagnostics |
| P0.5 baseline diagnostic panel | `ep3/outputs/p0_5_anchor_failure_diagnostic/cache/p0_5_baseline_event_diagnostic_panel.parquet` | matched baseline diagnostics |
| P0.5 hypothesis audit | `ep3/outputs/p0_5_anchor_failure_diagnostic/reports/p0_5_hypothesis_audit.csv` | decision context |
| P0.5 stop/continue decision | `ep3/outputs/p0_5_anchor_failure_diagnostic/reports/p0_5_stop_continue_decision.csv` | required transition authority |
| EP2 launch pool | `ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet` | denominator only |
| Local PIT Qlib provider | `data/qlib/cn_data_pit` | observable formula fields only |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | trading-day distances |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | industry decomposition |

Forbidden inputs:

- EP2 R02 threshold artifacts;
- EP2 R03 confirmed pool;
- EP2 R05 policy outputs;
- BaseRate row-level cache;
- Explore9 / Explore10 row-level outputs;
- any new Tushare / AkShare fetch.

## 5. Required Config

The implementation must add:

```text
ep3/configs/deferred_family_failure_lookalike_audit.yaml
```

Minimum config:

```yaml
phase: ep3_deferred_family_failure_lookalike_audit
output_root: ep3/outputs/deferred_family_failure_lookalike_audit

upstream_ep3_p0:
  manifest: ep3/engineering_baseline/outputs/manifests/ep3_engineering_baseline_manifest.json
  winner_label_panel: ep3/engineering_baseline/outputs/cache/ep3_winner_label_panel.parquet
  candidate_anchor_panel: ep3/engineering_baseline/outputs/cache/ep3_candidate_anchor_panel.parquet
  matched_baseline_panel: ep3/engineering_baseline/outputs/cache/ep3_matched_baseline_panel.parquet
  lifecycle_profile: ep3/engineering_baseline/outputs/reports/ep3_winner_lifecycle_profile.csv
  gate_audit: ep3/engineering_baseline/outputs/reports/ep3_gate_audit.csv
  anchor_vs_matched_baseline: ep3/engineering_baseline/outputs/reports/ep3_anchor_vs_matched_baseline.csv
  anchor_window_freeze: ep3/engineering_baseline/outputs/reports/ep3_anchor_window_freeze.csv
  matched_control_bucket_freeze: ep3/engineering_baseline/outputs/reports/ep3_matched_control_bucket_freeze.csv

upstream_ep3_p0_5:
  manifest: ep3/outputs/p0_5_anchor_failure_diagnostic/manifests/p0_5_anchor_failure_diagnostic_manifest.json
  anchor_event_diagnostic_panel: ep3/outputs/p0_5_anchor_failure_diagnostic/cache/p0_5_anchor_event_diagnostic_panel.parquet
  baseline_event_diagnostic_panel: ep3/outputs/p0_5_anchor_failure_diagnostic/cache/p0_5_baseline_event_diagnostic_panel.parquet
  hypothesis_audit: ep3/outputs/p0_5_anchor_failure_diagnostic/reports/p0_5_hypothesis_audit.csv
  stop_continue_decision: ep3/outputs/p0_5_anchor_failure_diagnostic/reports/p0_5_stop_continue_decision.csv

denominator_inputs:
  ep2_launch_pool: ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet

data_sources:
  qlib_provider_uri: data/qlib/cn_data_pit
  pit_qlib_instrument_universe_path: data/universe/pit_qlib_instrument_universe.csv
  trading_calendar_path: data/qlib/cn_data_pit/calendars/day.txt
  pit_industry_path: data/targets/pit_industry_membership.csv

split:
  train_start: "2017-07-04"
  train_end: "2021-12-31"
  validation_start: "2022-01-01"
  validation_end: "2023-12-31"
  robustness_start: "2024-01-01"
  robustness_end: "2025-12-31"

deferred_family_scope:
  primary_deferred_family: failed_lookalike_avoidance
  primary_event_type: recovery_after_failed_lookalike
  stopped_primary_families:
    - pullback_hold_restrengthen
    - second_breakout
  decision_source_required: write_deferred_family_requirement
  primary_horizon: H20
  sensitivity_horizons:
    - H10
    - H60
  derive_bins_from_split: train
  selection_from_validation_or_robustness_allowed: false

observable_failure_lookalike_rules:
  post_reference_observation_days: [1, 60]
  max_recovery_after_failure_days: 20
  max_ac_attribution_lookback_days: 20
  min_reference_acceleration_return_60d: 0.12
  min_reference_money_multiple_ma20: 2.0
  min_reference_money_cny: 50000000
  max_failed_followthrough_return_from_reference_close: 0.06
  min_recovery_return_from_reference_close: 0.00
  max_pullback_hold_failure_atr_multiple: 2.0
  max_consolidation_drawdown_from_reference_close: 0.15
  require_next_open_executable: true

diagnostic_bins:
  event_count_min_for_interpretation: 20
  instrument_year_count_min_for_interpretation: 10
  validation_min_unique_instrument_year_count_for_gate: 25
  min_train_recovery_rows_for_delay_freeze: 20
  trigger_rate_reference_bands: [0.0, 0.05, 0.10, 0.15, 0.20, 1.50]
  failure_margin_quantiles: [0.0, 0.25, 0.5, 0.75, 1.0]
  reference_age_days: [0, 5, 10, 20, 40, 60]

baseline_matching:
  donor_stock_day_source: ep3_winner_label_panel
  max_same_instrument_distance_days: 20
  max_industry_distance_days: 20
  control_replacement_allowed: false
  exclude_dates_within_primary_deferred_event_days: 5

gates:
  min_validation_trigger_rate_per_launch_episode: 0.10
  min_validation_h20_mean_diff_vs_matched_delay: 0.0
  min_validation_h20_p05_diff_vs_matched_delay: -0.003
  max_validation_h20_mae_worsening_vs_matched_delay: 0.005
  min_validation_instrument_year_positive_rate_diff: 0.0
  max_validation_top1_instrument_year_pnl_share: 0.20
  max_validation_top5_instrument_exposure_share: 0.50
  min_robustness_h20_mean_diff_vs_matched_delay: -0.001
  min_robustness_h20_p05_diff_vs_matched_delay: -0.005
```

Any additional config fields must preserve the no-selection and no-promotion
constraints.

## 6. Observable Deferred-Family Definition

The deferred family must be implemented as an observable diagnostic family:

```text
anchor_family_id = failed_lookalike_avoidance
```

This family does not mean "buy failed lookalikes". It means:

```text
detect observable states where A/C-like winner formation is likely false,
then test whether a later observable recovery / avoidance transition explains
P0 failure and creates a cleaner forward-audit family.
```

The lifecycle count of 773 train winner episodes is source evidence only. It is
not a forward-audit denominator, not a trigger count, and not pass evidence.
Forward-audit evidence must be rebuilt from observable event rows.

### 6.1 Forward-Audit Universe

Forward-audit scan universe:

```text
canonical EP2 launch episodes from
ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet
```

Canonical EP2 launch episode row:

```text
sort by launch_episode_id ascending, signal_date ascending;
drop_duplicates(launch_episode_id, keep = first).
```

For every canonical launch episode:

```text
reference_acceleration_date = canonical launch signal_date
reference_execution_date = canonical launch execution_date
instrument = canonical launch instrument
split = split(reference_acceleration_date)
```

Candidate scan dates:

```text
all PIT trading dates for the same instrument where:
  trading_day_distance(reference_acceleration_date, candidate_date)
    is between
    config.observable_failure_lookalike_rules.post_reference_observation_days
    inclusive;
  candidate_date split equals reference split;
  all formula inputs use only data <= candidate_date;
  execution uses next-open only.
```

Rows outside train / validation / robustness may be retained in cache as
`out_of_scope`, but cannot contribute to reports, gates, or decisions.

### 6.2 Event Types

The implementation must construct three event types:

```text
failure_lookalike_state
recovery_after_failed_lookalike
clean_avoidance_state
```

Only `recovery_after_failed_lookalike` is a primary forward-audit numerator.
`failure_lookalike_state` and `clean_avoidance_state` are diagnostic-only and
cannot by themselves support freeze / promotion decisions.

Event-type to `avoidance_status` mapping:

| `event_type` | `avoidance_status` | Decision use |
| --- | --- | --- |
| `failure_lookalike_state` | `persistent_failure` | diagnostic-only |
| `recovery_after_failed_lookalike` | `recovered_after_failure` | primary forward-audit numerator after dedupe |
| `clean_avoidance_state` | `clean_avoidance` | diagnostic-only |

### 6.3 Failure-Lookalike State

A `failure_lookalike_state` row exists when, as of `signal_date`, the row
resembles an A-like or C-like winner formation setup but fails exactly one
required confirmation condition.

Required observable fields:

| Field | Description |
| --- | --- |
| `reference_acceleration_date` | prior observable acceleration date |
| `signal_date` | close-derived signal date |
| `execution_date` | next trading day |
| `failure_condition_id` | the single failed confirmation condition |
| `failure_margin_value` | signed distance to the failed condition threshold |
| `lookalike_source_family` | A-like or C-like source condition |
| `is_executable_next_open` | next-open executable flag |

Allowed `failure_condition_id` values:

```text
pullback_window_failure
pullback_depth_failure
pullback_atr_floor_failure
restrengthen_failure
second_breakout_gap_failure
second_breakout_consolidation_failure
second_breakout_return_failure
second_breakout_liquidity_failure
```

Failure-condition contract:

```text
condition_margin_value >= 0 means the condition passes.
condition_margin_value < 0 means the condition fails.
failure_margin_value is the failed condition's signed margin on the failure
state date.
repaired_failure_margin_value is the same condition's signed margin on the
recovery date.
```

For composite conditions, the condition margin is the minimum of all component
margins. A row is a valid `failure_lookalike_state` only when exactly one
condition margin is `< 0` and every other source-family condition margin is
`>= 0`.

The formula implementation must persist:

```text
reports/deferred_family_formula_dictionary.csv
```

and every event row's `source_formula_hash` must equal the canonical hash of the
formula-dictionary rows used for that `lookalike_source_family` and
`failure_condition_id`. For `failure_condition_id = none`, hash all dictionary
rows for the row's `lookalike_source_family`.

Observable A-like condition table:

| `failure_condition_id` | Pass predicate | Signed margin |
| --- | --- | --- |
| `pullback_window_failure` | `trading_days_between(a, p)` is inside the P0 train-frozen `pullback_hold_restrengthen` window | `min(days - frozen_window_low, frozen_window_high - days)` |
| `pullback_depth_failure` | `pullback_depth = 1 - low[p] / close[a]` is between `0.04` and `0.18` inclusive | `min(pullback_depth - 0.04, 0.18 - pullback_depth)` |
| `pullback_atr_floor_failure` | `low[p] >= close[a] - 2.0 * atr20[a]` | `(low[p] - (close[a] - 2.0 * atr20[a])) / close[a]` |
| `restrengthen_failure` | `t > p`, `trading_days_between(p, t) <= 5`, `close[t] >= max(high, 5 trading days ending p)`, `close[t] > close[t-1]`, and `money[t] >= money_ma20[t]` | minimum of the five component margins: `trading_days_between(p,t) - 1`, `5 - trading_days_between(p,t)`, `close[t] / max(high_5_ending_p) - 1`, `close[t] / close[t-1] - 1`, `money[t] / money_ma20[t] - 1` |

Observable C-like condition table:

| `failure_condition_id` | Pass predicate | Signed margin |
| --- | --- | --- |
| `second_breakout_gap_failure` | `trading_days_between(a, t)` is inside the P0 train-frozen `second_breakout` window and `>= 3` | `min(days - frozen_window_low, frozen_window_high - days, days - 3)` |
| `second_breakout_consolidation_failure` | `min(low, interval [a+1, t-1]) >= close[a] * (1 - 0.15)` | `(min_interval_low - close[a] * 0.85) / close[a]` |
| `second_breakout_return_failure` | `close[t] >= max(high, interval [a+1, t-1])` and `close[t] / close[a] - 1 >= 0.06` | `min(close[t] / interval_high - 1, close[t] / close[a] - 1 - 0.06)` |
| `second_breakout_liquidity_failure` | `money[t] >= 2.0 * money_ma20[t]` and `money[t] >= 50,000,000` | `min(money[t] / (2.0 * money_ma20[t]) - 1, money[t] / 50,000,000 - 1)` |

Candidate tuple rules:

```text
A-like tuple = (reference_acceleration_date a, pullback_low_date p,
  candidate signal_date t).
C-like tuple = (reference_acceleration_date a, candidate signal_date t).

For A-like rows on the same instrument + canonical launch episode + t:
  evaluate every p where a < p < t and t - p is between 1 and 5 trading days;
  keep tuples with exactly one failed condition;
  choose the tuple with the largest failure_margin_value;
  tie-break by earliest p, then lexicographic failure_condition_id.

For C-like rows on the same instrument + canonical launch episode + t:
  evaluate the single interval [a+1, t-1].
```

Rows with missing `atr20`, `money_ma20`, prior close, interval high/low, or
split-contained calendar distance must be retained in
`cache/deferred_family_formula_diagnostic_panel.parquet` with
`formula_availability_status = unavailable`, but cannot become event-panel rows.

### 6.4 Recovery-After-Failed-Lookalike Event

A `recovery_after_failed_lookalike` row exists when a prior
`failure_lookalike_state` for the same canonical launch episode is followed by
an observable recovery transition.

Recovery transition rule:

```text
For a failure_lookalike_state at date f:
  scan dates r where:
    r > f;
    trading_day_distance(f, r) is between 1 and
      config.observable_failure_lookalike_rules.max_recovery_after_failure_days;
    r remains inside the same split;
    next-open execution is available if require_next_open_executable = true.

  A recovery date r is valid only if:
    the previously failed condition now passes;
    all other A-like or C-like source-family confirmation conditions still pass;
    close[r] >= close[reference_acceleration_date]
      * (1 + min_recovery_return_from_reference_close);
    money[r] >= money_ma20[r] when money_ma20 is available.

  signal_date = earliest valid r.
```

If multiple failure states can map to the same recovery date, tie-break by:

1. earliest `failure_state_date`;
2. largest absolute repaired `failure_margin_value`;
3. lexicographic `failure_condition_id`;
4. lexicographic deterministic event id.

### 6.5 Clean-Avoidance State

A `clean_avoidance_state` row exists when a candidate scan date passes all
A-like or C-like source-family confirmation conditions without any prior
same-launch `failure_lookalike_state` in the configured scan window.

This row class is diagnostic-only. It is used to compare whether recovery after
failure is different from simply observing a clean A/C-like state. It cannot be
used as the primary forward-audit numerator in this requirement.

### 6.6 Dedupe And Primary Event Rule

Primary deferred event rows:

```text
event_type = recovery_after_failed_lookalike
avoidance_status = recovered_after_failure
is_executable_next_open = true
dedupe_rank_within_launch_episode = 1
eligible_for_primary_gate = true for primary H20 gates
```

Dedupe key:

```text
split + launch_episode_id + lookalike_source_family
```

Dedupe order:

1. earliest recovery signal date;
2. earliest failure state date;
3. largest repaired failure margin;
4. lexicographic failure condition id;
5. deterministic event id.

Trigger numerator:

```text
count primary deferred event rows after dedupe.
```

Trigger denominator:

```text
distinct canonical EP2 launch_episode_id in the same split.
```

### 6.7 Formula Source Families

A-like source family conditions must mirror the P0
`pullback_hold_restrengthen` observable conditions, but the row is classified by
which condition fails or later recovers.

C-like source family conditions must mirror the P0 `second_breakout`
observable conditions, but the row is classified by which condition fails or
later recovers.

The implementation must not change P0 A/C membership. These formulas are
recomputed only to build the deferred-family diagnostic event panel.

The implementation must not simply reuse the stopped A/C events. It must build
a separate deferred-family panel that records:

```text
candidate observable A/C-like state from canonical EP2 launch universe
  + failure-lookalike state diagnostics
  + recovery / clean-avoidance status
  + next-open execution
  + H20/H10/H60 forward audit
```

## 7. Required Stage Order

The runner must execute these stages and write:

```text
reports/deferred_family_stage_order_audit.csv
```

Stages:

1. upstream authority check for EP3 P0 and P0.5;
2. transition-decision validation from P0.5;
3. train-only lifecycle deferred-family source audit;
4. observable failure-lookalike formula dictionary and formula precompute;
5. train-only diagnostic bin freeze;
6. deferred-family event panel construction;
7. matched baseline construction;
8. forward-audit metric computation;
9. failure-attribution and A/C comparison;
10. gate audit, decision report, and manifest.

Stages 1-5 must not use validation or robustness forward outcomes.

## 8. Required Outputs

All outputs must live under:

```text
ep3/outputs/deferred_family_failure_lookalike_audit/
```

Required cache:

```text
cache/deferred_family_event_panel.parquet
cache/deferred_family_matched_baseline_panel.parquet
cache/deferred_family_formula_diagnostic_panel.parquet
```

Required reports:

```text
reports/deferred_family_upstream_authority.csv
reports/deferred_family_stage_order_audit.csv
reports/deferred_family_transition_audit.csv
reports/deferred_family_lifecycle_source_audit.csv
reports/deferred_family_formula_dictionary.csv
reports/deferred_family_diagnostic_bin_freeze.csv
reports/deferred_family_event_summary.csv
reports/deferred_family_trigger_decomposition.csv
reports/deferred_family_matched_lift.csv
reports/deferred_family_tail_risk.csv
reports/deferred_family_ac_failure_attribution.csv
reports/deferred_family_sensitivity_horizon_audit.csv
reports/deferred_family_gate_audit.csv
reports/deferred_family_decision.csv
reports/deferred_family_report.md
manifests/deferred_family_manifest.json
```

### 8.1 Required Report Row Grains

`reports/deferred_family_stage_order_audit.csv`:

```text
one row per executed stage
primary_key = stage_id
```

Required fields:

```text
stage_id
stage_name
stage_order
started_at_utc
finished_at_utc
input_artifact_hashes
output_artifact_hashes
stage_status
```

`reports/deferred_family_upstream_authority.csv`:

```text
one row per upstream artifact or authority source
primary_key = authority_check_id
```

Required fields:

```text
authority_check_id
authority_type
artifact_path
required_hash
observed_hash
required_validation_status
observed_validation_status
authority_status
```

Allowed `authority_type` values:

```text
p0_manifest
p0_5_manifest
p0_artifact
p0_5_artifact
qlib_pit_directory
ep2_launch_pool_reference
```

`reports/deferred_family_transition_audit.csv`:

```text
one row per upstream transition condition
primary_key = transition_check_id
```

Required fields:

```text
transition_check_id
source_report
required_value
observed_value
transition_status
```

It must include checks that both A/C family rows are `stop_current_family` and
the overall P0.5 decision is `write_deferred_family_requirement`.

`reports/deferred_family_formula_dictionary.csv`:

```text
one row per lookalike_source_family + failure_condition_id + formula_component_id
primary_key = lookalike_source_family + failure_condition_id + formula_component_id
```

Required fields:

```text
lookalike_source_family
failure_condition_id
formula_component_id
predicate_text
signed_margin_formula_text
required_input_fields
lookback_rule
parameter_source
parameter_value
formula_hash
dictionary_row_hash
```

The canonical `source_formula_hash` used in cache rows is the hash of all
dictionary rows for the corresponding `lookalike_source_family` and
`failure_condition_id`, sorted by `formula_component_id`. For
`failure_condition_id = none`, hash all dictionary rows for the
`lookalike_source_family`.

`reports/deferred_family_lifecycle_source_audit.csv`:

```text
one row per split + anchor_family_id + lifecycle_stage_id
primary_key = split + anchor_family_id + lifecycle_stage_id
```

Required fields:

```text
split
anchor_family_id
lifecycle_stage_id
winner_episode_count
source_upstream_artifact
source_upstream_hash
lifecycle_source_status
```

`reports/deferred_family_diagnostic_bin_freeze.csv`:

```text
one row per freeze_id
primary_key = freeze_id
```

Required fields:

```text
freeze_id
freeze_type
lookalike_source_family
diagnostic_axis
bin_edges
train_source_row_count
train_source_instrument_year_count
freeze_status
parameter_hash
row_hash
```

Allowed `freeze_type` values:

```text
failure_margin_quantile
reference_age_days
money_bucket_copy_from_p0
vol20_bucket_copy_from_p0
ret_60d_bucket_copy_from_p0
train_median_recovery_delay_days
```

If `freeze_type = train_median_recovery_delay_days` and train primary recovery
rows for a `lookalike_source_family` are below
`diagnostic_bins.min_train_recovery_rows_for_delay_freeze`, `freeze_status` must
be `insufficient_train_rows`, the median value must be blank, and all
`matched_delay_baseline` rows for that family must be `unmatched`.

`reports/deferred_family_event_summary.csv`:

```text
one row per split + lookalike_source_family + event_type + avoidance_status
primary_key = split + lookalike_source_family + event_type + avoidance_status
```

Required fields:

```text
split
anchor_family_id
lookalike_source_family
event_type
avoidance_status
event_count
primary_forward_audit_event_count
gate_eligible_h20_event_count
unique_launch_episode_count
unique_instrument_count
unique_instrument_year_count
unavailable_formula_row_count
event_summary_status
```

`reports/deferred_family_trigger_decomposition.csv`:

```text
one row per split + diagnostic_axis + diagnostic_bucket + trigger_rate_type
primary_key = split + anchor_family_id + event_type + diagnostic_axis +
  diagnostic_bucket + trigger_rate_type
```

Required fields:

```text
split
anchor_family_id
event_type
diagnostic_axis
diagnostic_bucket
predeclared_partition_id
trigger_rate_type
event_count
canonical_launch_episode_count
trigger_rate_per_launch_episode
unique_instrument_count
unique_instrument_year_count
trigger_rate_band
interpretation_status
```

`trigger_rate_type` must include:

```text
raw_recovery_event
gate_eligible_h20_recovery_event
diagnostic_failure_state
diagnostic_clean_avoidance_state
```

Only `gate_eligible_h20_recovery_event` can be used in gates.

`reports/deferred_family_matched_lift.csv`:

```text
one row per split + baseline_id + diagnostic_axis + diagnostic_bucket +
diagnostic_bucket_source
primary_key = split + anchor_family_id + baseline_id + diagnostic_axis +
  diagnostic_bucket + diagnostic_bucket_source
```

Required fields:

```text
split
anchor_family_id
baseline_id
diagnostic_axis
diagnostic_bucket
predeclared_partition_id
diagnostic_bucket_source
anchor_event_count
baseline_event_count
unique_instrument_year_count
anchor_mean_after_cost_return_H20
baseline_mean_after_cost_return_H20
mean_diff_vs_baseline
anchor_p05_after_cost_return_H20
baseline_p05_after_cost_return_H20
p05_diff_vs_baseline
anchor_max_adverse_excursion_mean_H20
baseline_max_adverse_excursion_mean_H20
mae_worsening_vs_baseline
anchor_instrument_year_positive_rate
baseline_instrument_year_positive_rate
instrument_year_positive_rate_diff
interpretation_status
```

`reports/deferred_family_tail_risk.csv`:

```text
same row grain as deferred_family_matched_lift.csv
```

Required fields:

```text
split
anchor_family_id
baseline_id
diagnostic_axis
diagnostic_bucket
diagnostic_bucket_source
anchor_event_count
baseline_event_count
anchor_p05_after_cost_return_H20
baseline_p05_after_cost_return_H20
p05_diff_vs_baseline
anchor_max_adverse_excursion_mean_H20
baseline_max_adverse_excursion_mean_H20
mae_worsening_vs_baseline
top1_instrument_year_pnl_share
top5_instrument_exposure_share
interpretation_status
```

`reports/deferred_family_sensitivity_horizon_audit.csv`:

```text
one row per split + baseline_id + horizon + diagnostic_axis + diagnostic_bucket
primary_key = split + baseline_id + horizon + diagnostic_axis + diagnostic_bucket
```

Required fields:

```text
split
anchor_family_id
baseline_id
horizon
diagnostic_axis
diagnostic_bucket
anchor_event_count
baseline_event_count
anchor_mean_after_cost_return
baseline_mean_after_cost_return
mean_diff_vs_baseline
anchor_p05_after_cost_return
baseline_p05_after_cost_return
p05_diff_vs_baseline
sensitivity_only
interpretation_status
```

Allowed `horizon` values are `H10` and `H60`. `sensitivity_only` must always be
`true`.

`reports/deferred_family_gate_audit.csv`:

```text
one row per gate_name
```

Required fields:

```text
gate_name
gate_value
threshold
comparison
gate_passed
failure_status_if_failed
gate_source_report
```

`reports/deferred_family_decision.csv`:

```text
exactly one row
```

Required fields:

```text
recommended_decision
decision_rule_status
supporting_gate_names
primary_evidence_report
validation_trigger_rate_per_launch_episode
validation_unique_instrument_year_count
validation_mean_diff_vs_matched_delay
validation_p05_diff_vs_matched_delay
robustness_mean_diff_vs_matched_delay
robustness_p05_diff_vs_matched_delay
decision_rationale
```

`reports/deferred_family_report.md` must contain, in this order:

```text
1. final decision;
2. upstream P0/P0.5 problem chain;
3. trigger decomposition summary;
4. recovery-vs-baseline lift summary;
5. tail and concentration summary;
6. A/C failure attribution summary;
7. sensitivity-only H10/H60 summary;
8. validator status and manifest hash summary.
```

`manifests/deferred_family_manifest.json`:

```text
exactly one JSON object
```

Required top-level fields:

```text
requirement_id
run_id
config_path
config_hash
validation_status
upstream_authority_hashes
artifact_hashes
stage_order_hash
formula_dictionary_hash
created_at_utc
```

`artifact_hashes` must include every required cache, report, and manifest child
artifact except the manifest itself.

## 9. Event Panel Schema

`cache/deferred_family_event_panel.parquet` row grain:

```text
one row per instrument + signal_date + deferred_family_event_id
primary_key = deferred_family_event_id
```

Required fields:

| Field | Description |
| --- | --- |
| `deferred_family_event_id` | deterministic id |
| `anchor_family_id` | must be `failed_lookalike_avoidance` |
| `launch_episode_id` | canonical EP2 launch episode id |
| `instrument` | instrument |
| `signal_date` | close-derived signal date |
| `execution_date` | next-open execution date |
| `split` | train / validation / robustness / out_of_scope |
| `event_type` | `failure_lookalike_state` / `recovery_after_failed_lookalike` / `clean_avoidance_state` |
| `is_primary_forward_audit_event` | true only for deduped recovery rows |
| `dedupe_rank_within_launch_episode` | rank by the dedupe rule in section 6.6 |
| `reference_acceleration_date` | observable reference date |
| `reference_age_days` | trading days from reference to signal |
| `failure_state_date` | failure state date for recovery rows, else blank |
| `recovery_signal_date` | recovery signal date for recovery rows, else blank |
| `lookalike_source_family` | A-like / C-like |
| `failure_condition_id` | single failed condition or `none` |
| `failure_margin_value` | numeric signed margin |
| `repaired_failure_margin_value` | repaired margin on recovery date when applicable |
| `failure_margin_bucket` | train-frozen bucket |
| `avoidance_status` | `recovered_after_failure` / `persistent_failure` / `clean_avoidance` |
| `is_executable_next_open` | execution flag |
| `blocked_buy_reason` | blocked reason |
| `eligible_for_primary_gate` | H20 complete and split-contained |
| `winner_50h120` | label join |
| `winner_100h240` | label join |
| `money_bucket` | copied from P0 train-frozen bucket logic |
| `vol20_bucket` | copied from P0 train-frozen bucket logic |
| `ret_60d_bucket` | copied from P0 train-frozen bucket logic |
| `industry_bucket` | PIT industry at signal date |
| `year_bucket` | signal year |
| `after_cost_return_H10` | H10 return |
| `max_adverse_excursion_H10` | H10 MAE |
| `after_cost_return_H20` | H20 return |
| `max_adverse_excursion_H20` | H20 MAE |
| `after_cost_return_H60` | H60 return |
| `max_adverse_excursion_H60` | H60 MAE |
| `source_formula_hash` | observable formula hash |
| `row_hash` | deterministic row hash |

Forbidden fields:

```text
selected_for_p1
strategy_signal
production_signal
validation_selected_threshold
robustness_selected_threshold
```

`cache/deferred_family_formula_diagnostic_panel.parquet` row grain:

```text
one row per canonical launch episode + lookalike_source_family +
candidate signal_date + candidate tuple id
primary_key = formula_diagnostic_row_id
```

Required fields:

| Field | Description |
| --- | --- |
| `formula_diagnostic_row_id` | deterministic id |
| `launch_episode_id` | canonical EP2 launch episode id |
| `instrument` | instrument |
| `split` | train / validation / robustness / out_of_scope |
| `lookalike_source_family` | A-like / C-like |
| `reference_acceleration_date` | observable reference date |
| `candidate_signal_date` | candidate close-derived signal date |
| `candidate_pullback_low_date` | A-like tuple pullback date, else blank |
| `failure_condition_id` | failed condition or `none` |
| `failed_condition_count` | number of failed source-family conditions |
| `condition_margin_json` | deterministic JSON map of condition id to signed margin |
| `formula_availability_status` | available / unavailable |
| `unavailable_reason` | blank when available |
| `is_failure_lookalike_state_candidate` | true only when exactly one condition fails |
| `source_formula_hash` | hash from formula dictionary |
| `row_hash` | deterministic row hash |

This panel may include validation and robustness rows because the formulas are
predeclared, but stage 5 bin edges, delay medians, and any threshold freezes must
use only rows with `split = train`.

## 10. Matched Baselines

Required baselines:

```text
matched_delay_baseline
same_instrument_nonanchor_baseline
industry_matched_baseline
all_launch_direct_baseline
stopped_ac_anchor_baseline
```

Baseline roles:

| Baseline | Role |
| --- | --- |
| `matched_delay_baseline` | same event delayed by train-frozen delay rule |
| `same_instrument_nonanchor_baseline` | same instrument non-deferred-family executable date |
| `industry_matched_baseline` | same split / industry / bucket executable control |
| `all_launch_direct_baseline` | broad EP2 launch reference only |
| `stopped_ac_anchor_baseline` | P0 stopped A/C events, diagnostic comparator only |

`stopped_ac_anchor_baseline` must not be used as a denominator source or
promotion source. It is used only to ask:

```text
Does the deferred family explain what was wrong with A/C?
```

Baseline construction rules:

```text
Anchor side for pairwise baselines:
  only primary deferred event rows:
    event_type = recovery_after_failed_lookalike;
    is_primary_forward_audit_event = true;
    eligible_for_primary_gate = true.

matched_delay_baseline:
  derive train_median_recovery_delay_days from train primary deferred rows:
    trading_day_distance(failure_state_date, signal_date).
  median is an integer lower median:
    sort delay days ascending and choose index floor((n - 1) / 2).
  freeze one median per lookalike_source_family in
    reports/deferred_family_diagnostic_bin_freeze.csv.
  if train primary recovery rows for that lookalike_source_family are below
    diagnostic_bins.min_train_recovery_rows_for_delay_freeze:
      write freeze_status = insufficient_train_rows;
      mark every matched_delay_baseline row for that family as unmatched;
      fail matched-delay lift gates with failure_status_if_failed =
        insufficient_train_recovery_rows.
  baseline signal date =
    add train_median_recovery_delay_days to the anchor signal_date.
  if the date is missing, outside split, non-executable, overlaps a primary
    deferred-family event for the same instrument within +/-5 trading days,
    or has no H20 horizon,
    mark match_status as unmatched and exclude from paired lift denominator.

same_instrument_nonanchor_baseline:
  donor source =
    ep3/engineering_baseline/outputs/cache/ep3_winner_label_panel.parquet
    joined to PIT Qlib OHLCV / execution fields as of the donor signal_date;
  same instrument, same split, executable, H20-eligible PIT stock-day;
  not a deferred-family event;
  not an EP3 P0 A/C candidate anchor on the same date;
  not within +/-5 trading days of any primary deferred-family event for the
    same instrument;
  absolute trading-day distance to anchor signal_date <=
    baseline_matching.max_same_instrument_distance_days;
  minimum absolute trading-day distance to anchor signal_date;
  tie-break by earlier date, then lexicographic event id.
  if no donor remains, write one unmatched row with
    match_reason = no_same_instrument_nonanchor_donor.

industry_matched_baseline:
  donor source =
    ep3/engineering_baseline/outputs/cache/ep3_winner_label_panel.parquet
    joined to PIT Qlib OHLCV / execution fields and PIT industry as of the
    donor signal_date;
  same split, same PIT industry, same money_bucket / vol20_bucket /
    ret_60d_bucket when available;
  executable and H20-eligible;
  not the same instrument;
  not a deferred-family event;
  not an EP3 P0 A/C candidate anchor on the same date;
  absolute trading-day distance to anchor signal_date <=
    baseline_matching.max_industry_distance_days;
  minimum absolute trading-day distance to anchor signal_date;
  tie-break by earlier date, then instrument, then event id.
  if no donor remains, write one unmatched row with
    match_reason = no_industry_matched_donor.

all_launch_direct_baseline:
  all executable canonical EP2 launch rows in the same split;
  report-only broad comparator;
  cannot be decomposed by failure_margin_bucket or recovery-specific fields.

stopped_ac_anchor_baseline:
  P0.5 A/C anchor diagnostic rows where primary_diagnostic_eligible = true and
  eligible_for_primary_gate = true;
  report-only comparator;
  cannot be used as trigger denominator, matched-control donor, or promotion
  evidence.
```

Pairwise control replacement policy:

```text
Process primary deferred events sorted by:
  split, lookalike_source_family, signal_date, instrument,
  deferred_family_event_id.

For same_instrument_nonanchor_baseline and industry_matched_baseline:
  if baseline_matching.control_replacement_allowed = false, a donor stock-day
  can be matched to at most one primary deferred event per baseline_id and split.
  Once selected, it is unavailable to later primary events in the sorted order.
```

`cache/deferred_family_matched_baseline_panel.parquet` row grain:

```text
one row per baseline_event_id
primary_key = baseline_event_id
```

For pairwise baselines, `baseline_event_id` must be deterministic from
`deferred_family_event_id + baseline_id + donor signal_date + donor instrument`.
For broad report-only baselines such as `all_launch_direct_baseline`,
`deferred_family_event_id` must be `all_context`.

Required fields:

| Field | Description |
| --- | --- |
| `baseline_event_id` | deterministic id |
| `deferred_family_event_id` | linked primary deferred event id when pairwise |
| `baseline_id` | baseline comparator id |
| `lookalike_source_family` | linked primary deferred source family or `all` |
| `donor_source_table` | exact donor source table |
| `instrument` | baseline instrument |
| `signal_date` | baseline signal date |
| `execution_date` | baseline execution date |
| `split` | split |
| `match_status` | matched / unmatched |
| `match_reason` | deterministic reason |
| `trading_day_distance_to_anchor` | signed distance from anchor signal date to baseline signal date when pairwise |
| `replacement_sequence_rank` | deterministic selection order rank |
| `diagnostic_bucket_source` | linked_deferred_event / baseline_event / stopped_ac_event |
| `eligible_for_primary_gate` | H20 complete and split-contained |
| `after_cost_return_H10` | H10 return |
| `max_adverse_excursion_H10` | H10 MAE |
| `after_cost_return_H20` | H20 return |
| `max_adverse_excursion_H20` | H20 MAE |
| `after_cost_return_H60` | H60 return |
| `max_adverse_excursion_H60` | H60 MAE |
| `row_hash` | deterministic row hash |

## 11. Primary Metrics

Primary horizon:

```text
H20
```

Required metrics by split and baseline:

```text
event_count
trigger_rate_per_launch_episode
unique_instrument_count
unique_instrument_year_count
mean_after_cost_return_H20
p05_after_cost_return_H20
max_adverse_excursion_mean_H20
winner_capture_rate_50h120
instrument_year_positive_rate
top1_instrument_year_pnl_share
top5_instrument_exposure_share
mean_diff_vs_matched_delay
p05_diff_vs_matched_delay
mae_worsening_vs_matched_delay
instrument_year_positive_rate_diff
```

Sensitivity horizons:

```text
H10
H60
```

Sensitivity rows are report-only and cannot drive decisions.

## 12. A/C Failure Attribution

The implementation must write:

```text
reports/deferred_family_ac_failure_attribution.csv
```

This report must join P0.5 A/C anchor rows to deferred-family diagnostics by:

```text
instrument
signal_date or nearest same-instrument prior observable failure-lookalike state
same split
```

Join rule:

```text
Source A/C rows:
  p0_5_anchor_event_diagnostic_panel rows where:
    split in {validation, robustness};
    anchor_family_id in stopped_primary_families;
    primary_diagnostic_eligible = true;
    eligible_for_primary_gate = true;
    after_cost_return_H20 is present.

Candidate deferred rows:
  deferred_family_event_panel rows where:
    split equals A/C split;
    instrument equals A/C instrument;
    event_type in {
      failure_lookalike_state,
      recovery_after_failed_lookalike,
      clean_avoidance_state
    };
    signal_date <= A/C signal_date;
    trading_day_distance(signal_date, A/C signal_date)
      <= max_ac_attribution_lookback_days from config.

Tie-break:
  1. exact same signal_date;
  2. minimum trading-day distance to A/C signal_date;
  3. prefer recovery_after_failed_lookalike over failure_lookalike_state over
     clean_avoidance_state;
  4. same launch_episode_id if available;
  5. lexicographic deferred_family_event_id.

If no candidate row exists, attribution_bucket = no_deferred_match.
```

Allowed attribution buckets:

```text
recovered_after_failure
persistent_failure
clean_avoidance
no_deferred_match
```

Required questions:

1. What share of failed A/C validation rows were in `persistent_failure` state?
2. What share of A/C tail rows were in `persistent_failure` state?
3. Do A/C rows outside `persistent_failure` have materially better H20 lift?
4. Is this relationship stable in robustness?

Row grain:

```text
one row per split + stopped_ac_family_id + attribution_bucket
primary_key = split + stopped_ac_family_id + attribution_bucket
```

Required fields:

| Field | Description |
| --- | --- |
| `split` | split |
| `stopped_ac_family_id` | A/C family |
| `attribution_bucket` | recovered_after_failure / persistent_failure / clean_avoidance / no_deferred_match |
| `ac_event_count` | A/C event count |
| `ac_mean_after_cost_return_H20` | A/C mean |
| `ac_p05_after_cost_return_H20` | A/C p05 |
| `ac_mae_mean_H20` | A/C MAE |
| `matched_delay_mean_diff` | A/C vs matched-delay |
| `tail_event_share` | bottom-5pct A/C event share |
| `winner_capture_rate_50h120` | winner capture |
| `interpretation_status` | interpretable / too_sparse |

## 13. Gates

This phase can produce only one of these decisions:

```text
stop_deferred_family
write_p0_6_deferred_family_freeze_requirement
write_p0_6_deferred_family_formula_refinement_requirement
```

It cannot produce:

```text
write_p1_validation_requirement
strategy_candidate
production_signal
```

P1 may be considered only after a separate P0.6 requirement freezes the
deferred-family formula or partition without using validation / robustness for
selection.

Gate pass for `write_p0_6_deferred_family_freeze_requirement` requires:

- validation trigger rate >= `0.10`;
- validation unique instrument-year count >= `25`;
- validation H20 mean diff vs matched-delay > `0`;
- validation H20 p05 diff vs matched-delay >= `-0.003`;
- validation MAE worsening vs matched-delay <= `0.005`;
- validation instrument-year positive-rate diff >= `0`;
- validation top1 instrument-year PnL share <= `0.20`;
- validation top5 instrument exposure share <= `0.50`;
- robustness H20 mean diff vs matched-delay >= `-0.001`;
- robustness H20 p05 diff vs matched-delay >= `-0.005`;
- robustness trigger rate does not collapse below half the validation trigger
  rate;
- no validation or robustness selected threshold is used.

The 0.10 trigger floor is a P0.6 bridge threshold for this narrower deferred
family, not a replacement for the original EP3 P0 primary-family 0.20 trigger
budget. It can justify only a later P0.6 freeze requirement, and only when all
matched-lift, tail, breadth, and robustness gates above pass.

Gate pass for
`write_p0_6_deferred_family_formula_refinement_requirement` requires:

- lifecycle source count in train remains >= `20`;
- validation sample is interpretable;
- no freeze-eligible formula passes;
- `persistent_failure` attribution explains at least 50% of A/C tail rows in
  validation and at least 30% in robustness;
- matched-lift failure is not worse than stopped A/C aggregate.

Otherwise:

```text
stop_deferred_family
```

## 14. Validator Requirements

The validator must fail on:

- missing required P0 or P0.5 upstream artifacts;
- P0 or P0.5 manifest not `validation_status = passed`;
- P0.5 stop/continue decision not equal to `write_deferred_family_requirement`
  on the overall row;
- any modified P0 or P0.5 frozen artifact hash;
- outputs outside `ep3/outputs/deferred_family_failure_lookalike_audit/`;
- use of forbidden EP2 R02 / R03 / R05 artifacts;
- any model training artifact;
- any validation-selected or robustness-selected threshold;
- duplicate event-panel primary key;
- primary forward-audit numerator containing any event_type other than
  `recovery_after_failed_lookalike`;
- `failure_lookalike_state` or `clean_avoidance_state` used as freeze or
  promotion evidence;
- event rows not derived from canonical EP2 launch episodes;
- invalid dedupe rank for primary deferred events;
- missing required cache/report fields;
- missing `deferred_family_formula_dictionary.csv` or formula dictionary hash
  mismatch;
- event row `source_formula_hash` not matching the canonical dictionary hash;
- duplicate report rows under declared row grain;
- using validation or robustness outcomes to derive bins;
- using validation or robustness rows to derive
  `train_median_recovery_delay_days`;
- matched-delay baseline available despite insufficient train recovery rows;
- baseline donor row not sourced from the declared donor table;
- baseline donor replacement used when
  `baseline_matching.control_replacement_allowed = false`;
- baseline donor outside the configured max distance window;
- H10/H60 sensitivity used in decision;
- missing A/C failure attribution report;
- A/C attribution join exceeding configured lookback or violating tie-break;
- missing `stopped_ac_anchor_baseline`;
- `stopped_ac_anchor_baseline` used as denominator or promotion evidence;
- `all_launch_direct_baseline` decomposed by recovery-specific fields;
- any P1 / strategy / production signal field;
- decision rule mismatch;
- manifest hash mismatch.

## 15. Required Commands

```bash
uv run python ep3/scripts/run_deferred_family_failure_lookalike_audit.py \
  --config ep3/configs/deferred_family_failure_lookalike_audit.yaml

uv run python ep3/scripts/validate_deferred_family_failure_lookalike_audit.py \
  --config ep3/configs/deferred_family_failure_lookalike_audit.yaml

uv run python -m py_compile \
  ep3/scripts/run_deferred_family_failure_lookalike_audit.py \
  ep3/scripts/validate_deferred_family_failure_lookalike_audit.py \
  ep3/scripts/deferred_family_common.py
```

## 16. Completion Criteria

Implementation success:

```text
validator passes;
all required cache, report, and manifest artifacts exist;
P0 and P0.5 frozen artifacts are unchanged;
overall P0.5 transition decision is reproduced;
no validation / robustness outcome is used to select formulas, thresholds, or
partitions;
no P1 candidate is emitted.
```

Research success:

```text
The report explains whether failed_lookalike_avoidance is a viable deferred
family for a later P0.6 freeze/refinement requirement, or whether EP3 should
stop this deferred branch as well.
```

This requirement intentionally follows the negative evidence from EP3 P0 and
P0.5. It is not a retry of A/C and not a promotion to P1.
