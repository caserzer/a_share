# EP3 P0.5 Diagnostic Requirement

> Requirement id: `ep3_p0_5_anchor_failure_diagnostic`
> Status: implementation-ready requirement
> Scope: EP3-P0.5 audit-only diagnosis after engineering baseline no-go
> Authoritative upstream: `ep3/engineering_baseline/requirement.md`
> Required upstream manifest: `ep3/engineering_baseline/outputs/manifests/ep3_engineering_baseline_manifest.json`

## 1. Purpose

EP3-P0 工程基座已经完成并通过 validator，但两个 primary anchor family 都不能进入 EP3-P1：

```text
pullback_hold_restrengthen: no-go / failed_trigger_budget
second_breakout: no-go / failed_trigger_budget
```

P0.5 的目标不是修正 gate 让它通过，也不是开始训练模型。P0.5 只回答一个诊断问题：

```text
当前 A/C anchor 失败，是因为 anchor idea 本身无效，
还是因为 P0 formula 太窄、window / path state 切分太粗、
EP2 launch reference 太弱、或 matched baseline 暴露了可反证失败？
```

本阶段输出的是 diagnostic conclusion，不是 strategy candidate。

## 2. Phase Boundary

P0.5 必须保持 audit-only。完成本 requirement 以前，不允许：

- 训练 entry / ranking / continuation / filter 模型；
- 输出 P1 candidate、strategy candidate、portfolio candidate 或 production signal；
- 用 validation / robustness 选择阈值、窗口、baseline、horizon 或 anchor variant；
- 修改 EP3-P0 工程基座的 frozen artifacts；
- 放宽 P0 trigger budget、matched baseline、tail risk 或 concentration gate；
- 将 deferred anchor family 当成可交易 family 实现；
- 做 full portfolio backtest；
- 宣称任何 anchor 可交易。

Allowed use:

```text
train split:
  derive diagnostic bins and mechanically pre-registered audit partitions only.

validation / robustness:
  report frozen diagnostic partitions only.
  may falsify or support a hypothesis, but cannot select parameters.
```

## 3. Upstream Facts To Preserve

The implementation must read the current EP3-P0 outputs and reproduce these status facts in the P0.5 report:

| Field | pullback_hold_restrengthen | second_breakout |
| --- | ---: | ---: |
| `ep3_p1_decision_status` | `failed_trigger_budget` | `failed_trigger_budget` |
| `passed_gate_count` | 7 | 9 |
| `failed_gate_count` | 8 | 6 |
| `lifecycle_anchor_recall` | 0.3445945946 | 0.4611486486 |
| `validation_raw_trigger_rate_per_launch_episode` | 0.1697761194 | 0.1305970149 |
| `validation_gate_eligible_h20_trigger_rate_per_launch_episode` | 0.1436567164 | 0.1194029851 |
| `validation_h20_mean_diff_vs_matched_delay` | -0.0221847264 | -0.0087519487 |
| `validation_h20_p05_diff_vs_matched_delay` | -0.0152458398 | -0.0407600111 |

Interpretation boundary:

```text
lifecycle recall passed.
forward-audit promotion failed.
Therefore P0.5 focuses on why observable winner-like stages do not translate
into enough executable, matched-baseline-positive forward-audit events.
```

Trigger-rate terminology:

```text
raw_trigger_rate_per_launch_episode:
  from ep3_anchor_trigger_budget_audit.csv.
  numerator = executable primary anchor trigger count.
  denominator = distinct canonical EP2 launch episodes in the same split.

gate_eligible_h20_trigger_rate_per_launch_episode:
  from ep3_anchor_vs_matched_baseline.csv where
    baseline_id = anchor and horizon_id = H20.
  numerator = anchor rows that satisfy executable, dedupe, label horizon,
              and split-containment eligibility.
  denominator = distinct canonical EP2 launch episodes in the same split.
```

## 4. Canonical Inputs

P0.5 must use only these inputs:

| Input | Required path | Role |
| --- | --- | --- |
| EP3 P0 manifest | `ep3/engineering_baseline/outputs/manifests/ep3_engineering_baseline_manifest.json` | frozen upstream authority |
| EP3 winner labels | `ep3/engineering_baseline/outputs/cache/ep3_winner_label_panel.parquet` | labels and horizon eligibility |
| EP3 candidate anchors | `ep3/engineering_baseline/outputs/cache/ep3_candidate_anchor_panel.parquet` | primary A/C anchor events |
| EP3 matched baselines | `ep3/engineering_baseline/outputs/cache/ep3_matched_baseline_panel.parquet` | matched baseline events |
| EP3 lifecycle profile | `ep3/engineering_baseline/outputs/reports/ep3_winner_lifecycle_profile.csv` | winner-only lifecycle explanation |
| EP3 gate audit | `ep3/engineering_baseline/outputs/reports/ep3_gate_audit.csv` | upstream gate status |
| EP3 anchor metrics | `ep3/engineering_baseline/outputs/reports/ep3_anchor_vs_matched_baseline.csv` | upstream forward-audit metrics |
| EP3 sensitivity horizon audit | `ep3/engineering_baseline/outputs/reports/ep3_sensitivity_horizon_audit.csv` | upstream H10/H60 report-only sensitivity reference |
| EP3 anchor windows | `ep3/engineering_baseline/outputs/reports/ep3_anchor_window_freeze.csv` | frozen train-derived windows |
| EP3 matched-control buckets | `ep3/engineering_baseline/outputs/reports/ep3_matched_control_bucket_freeze.csv` | frozen train-derived money / vol20 / ret60 bucket edges |
| EP3 trigger budget audit | `ep3/engineering_baseline/outputs/reports/ep3_anchor_trigger_budget_audit.csv` | raw trigger budget reference |
| EP2 launch pool | `ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet` | denominator universe for trigger decomposition only |
| Local PIT Qlib OHLCV provider | `data/qlib/cn_data_pit` | formula-diagnostic fields only, using data `<= signal_date` |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` | trading-day distance calculation |
| PIT industry membership | `data/targets/pit_industry_membership.csv` | industry/year decomposition only |

Forbidden inputs:

- EP2 R02 threshold artifacts;
- EP2 R03 confirmed pool;
- EP2 R05 holding policy outputs;
- BaseRate row-level cache;
- Explore9 / Explore10 row-level outputs;
- any new Tushare / AkShare fetch.

EP2 launch pool is allowed only for denominator construction:

```text
allowed fields:
  launch_episode_id
  instrument
  signal_date
  execution_date
  is_buy_executable_next_open
  is_executable_next_open
  blocked_buy_reason
  blocked_execution_reason
  industry_asof_signal_date

forbidden use:
  no EP2 R02/R03/R05 fields;
  no EP2 label or schedule outputs;
  no selection or promotion.
```

The implementation must write a first-class upstream authority file:

```text
reports/p0_5_upstream_authority.csv
```

Required fields:

| Field | Description |
| --- | --- |
| `artifact_name` | upstream artifact id |
| `path` | required upstream path |
| `role` | frozen input role |
| `exists` | boolean |
| `upstream_manifest_hash` | hash recorded by upstream manifest when available |
| `live_content_hash` | hash computed at P0.5 run time |
| `hash_match` | true if manifest hash and live hash agree, or explicit `not_in_manifest` for allowed extra input |
| `authority_status` | passed / failed |

Authority matching rule:

```text
For EP3-P0 artifacts:
  normalize path relative to topic root;
  first match upstream manifest artifact_authority by path;
  if path is absent, match by artifact_name;
  if both are absent, authority_status = failed.

For allowed non-EP3-P0 inputs:
  EP2 launch pool, local PIT Qlib OHLCV provider, trading calendar, PIT Qlib
  instrument universe, and PIT industry membership may use
  upstream_manifest_hash = not_in_manifest;
  hash_match = not_in_manifest;
  authority_status = passed only if the file or directory exists and
  live_content_hash is non-empty.

Directory live_content_hash rule:
  For any allowed directory input, compute a deterministic recursive directory
  hash. Include only regular files under the configured directory whose
  relative POSIX path starts with one of:
    calendars/
    instruments/
    features/
  Exclude __pycache__, .DS_Store, temporary files ending in .tmp, and hidden
  editor swap files.
  Sort included relative POSIX paths lexicographically. For each included file,
  hash raw bytes with SHA256 and append:
    relative_path + "\0" + file_size_bytes + "\0" + file_sha256 + "\n"
  to the directory manifest string. The directory live_content_hash is the
  SHA256 of that UTF-8 manifest string. The validator must fail if the included
  file set is empty or if any included file cannot be read.
```

## 5. Required Config

The implementation must add:

```text
ep3/configs/p0_5_anchor_failure_diagnostic.yaml
```

Minimum required config:

```yaml
phase: ep3_p0_5_anchor_failure_diagnostic
output_root: ep3/outputs/p0_5_anchor_failure_diagnostic

upstream_ep3_p0:
  manifest: ep3/engineering_baseline/outputs/manifests/ep3_engineering_baseline_manifest.json
  winner_label_panel: ep3/engineering_baseline/outputs/cache/ep3_winner_label_panel.parquet
  candidate_anchor_panel: ep3/engineering_baseline/outputs/cache/ep3_candidate_anchor_panel.parquet
  matched_baseline_panel: ep3/engineering_baseline/outputs/cache/ep3_matched_baseline_panel.parquet
  lifecycle_profile: ep3/engineering_baseline/outputs/reports/ep3_winner_lifecycle_profile.csv
  gate_audit: ep3/engineering_baseline/outputs/reports/ep3_gate_audit.csv
  anchor_vs_matched_baseline: ep3/engineering_baseline/outputs/reports/ep3_anchor_vs_matched_baseline.csv
  sensitivity_horizon_audit: ep3/engineering_baseline/outputs/reports/ep3_sensitivity_horizon_audit.csv
  anchor_window_freeze: ep3/engineering_baseline/outputs/reports/ep3_anchor_window_freeze.csv
  matched_control_bucket_freeze: ep3/engineering_baseline/outputs/reports/ep3_matched_control_bucket_freeze.csv
  trigger_budget_audit: ep3/engineering_baseline/outputs/reports/ep3_anchor_trigger_budget_audit.csv

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
  split_date_field: signal_date

diagnostic_scope:
  anchor_families:
    - pullback_hold_restrengthen
    - second_breakout
  primary_horizon: H20
  sensitivity_horizons:
    - H10
    - H60
  derive_bins_from_split: train
  apply_bins_to_splits:
    - train
    - validation
    - robustness
  primary_report_splits:
    - train
    - validation
    - robustness
  cache_passthrough_splits:
    - out_of_scope
  selection_from_validation_or_robustness_allowed: false

diagnostic_bins:
  reference_age_days: [0, 5, 10, 20, 40, 60]
  anchor_window_position_quantiles: [0.0, 0.25, 0.5, 0.75, 1.0]
  formula_margin_quantiles: [0.0, 0.25, 0.5, 0.75, 1.0]
  second_breakout_gap_days: [3, 10, 20, 40, 60]
  trigger_rate_reference_bands: [0.0, 0.05, 0.10, 0.15, 0.20, 1.50]
  event_count_min_for_interpretation: 20
  instrument_year_count_min_for_interpretation: 10

hypotheses:
  h1_formula_too_narrow:
    diagnostic_only: true
  h2_window_position_problem:
    diagnostic_only: true
  h3_ep2_reference_pollution:
    diagnostic_only: true
  h4_matched_baseline_too_strong_or_anchor_no_lift:
    diagnostic_only: true
  h5_tail_risk_not_trigger_rate_is_core_failure:
    diagnostic_only: true
```

Any added fields must preserve the no-selection and no-promotion constraints.

Diagnostic-bin source semantics:

```text
reference_age_days:
  bin_source_split = config_static.
  bin_method = config_edges.

year_bucket / executable_status:
  bin_source_split = config_static.
  bin_method = categorical.

industry_bucket:
  bin_source_split = config_static.
  bin_method = categorical.
  categories come from PIT industry membership values, not from outcome rows.

anchor_window_position_quantiles:
  bin_source_split = train.
  bin_method = quantile.
  train rows may come only from primary family anchor rows with signal_date,
  execution_date, and reference_acceleration_date present.

pullback_depth_band:
  bin_source_split = train.
  bin_method = quantile.
  quantile_edges_config = diagnostic_bins.formula_margin_quantiles.
  source_field_name = pullback_depth_from_acceleration_close.
  train rows may come only from primary_diagnostic_eligible
  pullback_hold_restrengthen anchor rows.

second_breakout_return_band:
  bin_source_split = train.
  bin_method = quantile.
  quantile_edges_config = diagnostic_bins.formula_margin_quantiles.
  source_field_name = second_breakout_return_from_first_close.
  train rows may come only from primary_diagnostic_eligible second_breakout
  anchor rows.

second_breakout_consolidation_drawdown_band:
  bin_source_split = train.
  bin_method = quantile.
  quantile_edges_config = diagnostic_bins.formula_margin_quantiles.
  source_field_name = second_breakout_consolidation_drawdown_from_first_close.
  train rows may come only from primary_diagnostic_eligible second_breakout
  anchor rows.

second_breakout_gap_band:
  bin_source_split = config_static.
  bin_method = config_edges.
  source_field_name = second_breakout_gap_days.
  edges come from diagnostic_bins.second_breakout_gap_days.

money_bucket / vol20_bucket / ret_60d_bucket:
  bin_source_split = upstream_p0_train_frozen.
  bin_method = copied_from_p0.
  source artifact must be
    ep3/engineering_baseline/outputs/reports/ep3_matched_control_bucket_freeze.csv.
  P0.5 must not recompute these edges from validation or robustness rows.

trigger_rate_reference_bands:
  bin_source_split = config_static.
  bin_method = config_edges.
  used only to populate trigger_rate_band in p0_5_trigger_decomposition.csv
  after trigger_rate_per_launch_episode is computed. It must not be used to
  choose, rank, or promote any partition.
```

Split-scope rule:

```text
Diagnostic cache files must preserve all upstream EP3-P0 rows, including rows
whose upstream split is out_of_scope.

Primary diagnostic reports, hypothesis decisions, trigger denominators, and
stop / continue decisions may use only rows with split in:
  train, validation, robustness.

out_of_scope rows are audit passthrough rows only. They must not contribute to
trigger rates, matched-lift metrics, tail metrics, concentration metrics,
hypothesis support, or stop / continue decisions.
```

## 6. Stage Order

The runner must execute these stages and write `p0_5_stage_order_audit.csv`:

1. upstream artifact authority check;
2. upstream no-go reproduction;
3. formula diagnostic precompute and train-only diagnostic bin freeze;
4. anchor and baseline event enrichment using frozen bins;
5. trigger budget decomposition;
6. matched-baseline lift decomposition;
7. tail-risk and failure-lookalike decomposition;
8. lifecycle-vs-forward translation audit;
9. conclusion and stop/continue decision;
10. manifest and validator.

Stages 1-3 must not use validation / robustness outcome values to derive
bins, thresholds, labels, or partitions.

Stage 3 may precompute only as-of diagnostic values needed to freeze bins:

```text
Allowed stage-3 precompute:
  primary_diagnostic_eligible from upstream split, required-date presence, and
  configured scope rules;
  anchor_window_position_ratio from upstream reference acceleration date,
  signal_date, and frozen P0 anchor window;
  pullback_depth_from_acceleration_close, second_breakout_gap_days,
  second_breakout_return_from_first_close, and
  second_breakout_consolidation_drawdown_from_first_close from PIT price rows
  visible at or before signal_date;
  copied P0 money_bucket / vol20_bucket / ret_60d_bucket boundaries.

Forbidden stage-3 precompute:
  validation or robustness forward returns;
  validation or robustness winner outcomes;
  validation or robustness matched-baseline lift;
  any best-bucket, best-partition, or promotion decision.
```

Train-quantile bins must be frozen after the allowed precompute and before
stage 4 applies the frozen buckets to validation and robustness rows.

`p0_5_stage_order_audit.csv` required fields:

| Field | Description |
| --- | --- |
| `stage_order` | integer 1-10 |
| `stage_name` | required stage name |
| `completed_at` | ISO timestamp |
| `validation_outcomes_used_by_stage` | false for stages 1-3 |
| `robustness_outcomes_used_by_stage` | false for stages 1-3 |
| `frozen_artifact_written` | artifact written at stage |
| `artifact_hash_after_stage` | hash after stage completion |

## 7. Diagnostic Questions

P0.5 must answer each question with evidence:

### 7.1 Is trigger budget failure caused by formula narrowness?

For each family and split, decompose trigger rate by:

- anchor window position bucket;
- reference acceleration age bucket;
- family-specific formula margin bucket;
- year;
- industry;
- train-frozen matched bucket;
- executable vs blocked next-open status.

`label_join_status` may be reported only as a numerator-row distribution copied
from upstream anchor / baseline event panels. It must not be used as a
bucket-level launch-denominator axis, because non-trigger EP2 launch episodes do
not have an upstream label join row.

Anchor-window position measure:

```text
For each anchor-family event:
  anchor_window_measure_days =
    trading_day_distance(reference_acceleration_date, signal_date).

  frozen_window_low / frozen_window_high =
    values for the same anchor_family_id from ep3_anchor_window_freeze.csv.

  anchor_window_position_ratio =
    0.0 if frozen_window_high == frozen_window_low,
    else (anchor_window_measure_days - frozen_window_low)
         / (frozen_window_high - frozen_window_low).

Bucket derivation:
  Use only train-split upstream candidate anchor rows where:
    anchor_family_id is primary,
    dedupe_rank_within_reference_event = 1,
    reference_acceleration_date is present,
    signal_date is present.

  Do not use winner labels, H20/H10/H60 returns, matched-baseline outcomes,
  validation outcomes, or robustness outcomes to derive bucket edges.

  For each anchor_family_id, compute quantile edges from
  anchor_window_position_ratio using config
  diagnostic_bins.anchor_window_position_quantiles, freeze them in
  p0_5_diagnostic_bin_freeze.csv, and apply the same frozen edges to train,
  validation, and robustness.
```

Formula-specific observable diagnostics are required and must be recomputed from
the local PIT Qlib OHLCV provider using only rows with `date <= signal_date`.
They are diagnostic-only fields and must not change P0 anchor membership:

```text
For pullback_hold_restrengthen rows:
  reference acceleration date a = reference_acceleration_date.
  signal date t = signal_date.
  candidate pullback low p =
    lowest low[p] after a and before or on t that satisfies the P0 pullback
    window, drawdown, and ATR floor conditions from the EP3-P0 requirement;
    tie-break by earliest p.
  pullback_depth_from_acceleration_close =
    low[p] / close[a] - 1.
  pullback_depth_band =
    train-frozen bin from p0_5_diagnostic_bin_freeze.csv.

For second_breakout rows:
  reference acceleration date a = reference_acceleration_date.
  signal date t = signal_date.
  second_breakout_gap_days = trading_day_distance(a, t).
  second_breakout_return_from_first_close =
    close[t] / close[a] - 1.
  second_breakout_consolidation_drawdown_from_first_close =
    min(low, interval [a+1, t-1]) / close[a] - 1;
    if the interval is empty, set unavailable.
  second_breakout_gap_band =
    config-static bin from diagnostic_bins.second_breakout_gap_days.
  second_breakout_return_band and second_breakout_consolidation_drawdown_band =
    train-frozen bins from p0_5_diagnostic_bin_freeze.csv.

If any required price row is missing, set formula_diagnostic_status =
missing_price_row and set all formula-specific fields for that row to
unavailable. Formula-specific diagnostics must not read execution_date OHLCV
except for execution audit fields copied from P0.
```

Formula diagnostic status mapping:

```text
For anchor rows whose anchor_family_id is not in
diagnostic_scope.anchor_families:
  formula_diagnostic_status = not_applicable;
  all formula-specific diagnostic fields and bands = unavailable;
  primary_diagnostic_eligible = false.

For configured primary-family anchor rows:
  missing_reference_date if signal_date or reference_acceleration_date is
  missing;
  missing_price_row if required dates are present but any required PIT OHLCV
  row needed by the family formula is unavailable;
  available only when the family-specific formula fields required by the row
  are computed and the corresponding frozen/config bucket is assigned. For the
  documented second_breakout empty-interval consolidation case, the
  consolidation fields may remain unavailable while formula_diagnostic_status
  remains available.

For pullback_hold_restrengthen rows with formula_diagnostic_status = available:
  pullback_depth_from_acceleration_close and pullback_depth_band must be
  populated;
  all second_breakout_* diagnostic fields and bands must be unavailable.

For second_breakout rows with formula_diagnostic_status = available:
  second_breakout_gap_days, second_breakout_gap_band,
  second_breakout_return_from_first_close, second_breakout_return_band,
  second_breakout_consolidation_drawdown_from_first_close, and
  second_breakout_consolidation_drawdown_band must be populated unless the
  documented empty-interval consolidation rule sets the consolidation fields to
  unavailable;
  all pullback_* diagnostic fields and bands must be unavailable.
```

Denominator construction is required and must be written to:

```text
reports/p0_5_trigger_denominator_panel.csv
```

Denominator row grain:

```text
one row per distinct canonical EP2 launch episode used by EP3-P0 in the same split
primary_key = split + launch_episode_id
```

Canonical EP2 launch episode row:

```text
source = ep2/engineering_baseline/outputs/cache/ep2_launch_observation_pool.parquet
construction = sort by launch_episode_id ascending, signal_date ascending;
               then drop_duplicates(launch_episode_id, keep = first).

The denominator split, launch_signal_date, launch_execution_date, execution
status, blocked reason, industry, and year must all be taken from this
canonical row. Later rows from the same launch_episode_id must not move the
episode across splits or buckets.
```

Required reconciliation:

```text
For each split:
  count distinct launch_episode_id in p0_5_trigger_denominator_panel.csv
  must equal ep3_anchor_trigger_budget_audit.csv.ep2_launch_episode_count.

If ep3_anchor_trigger_budget_audit.csv has one row per split + anchor_family_id:
  the same split-level denominator count must match every primary-family row
  in that split.
```

The reconciliation must be written to:

```text
reports/p0_5_trigger_denominator_reconciliation.csv
```

Required reconciliation fields:

| Field | Description |
| --- | --- |
| `split` | train / validation / robustness |
| `anchor_family_id` | primary family row from upstream trigger budget audit |
| `p0_5_denominator_launch_episode_count` | distinct launch episodes in `p0_5_trigger_denominator_panel.csv` for the split |
| `upstream_ep2_launch_episode_count` | `ep2_launch_episode_count` from `ep3_anchor_trigger_budget_audit.csv` |
| `count_diff` | P0.5 denominator count minus upstream count |
| `denominator_reconciliation_status` | passed / failed |

Required denominator fields:

| Field | Description |
| --- | --- |
| `split` | split by canonical EP2 launch signal date |
| `launch_episode_id` | EP2 launch episode id |
| `instrument` | EP2 launch instrument |
| `launch_signal_date` | canonical EP2 launch signal date |
| `launch_execution_date` | canonical EP2 next-open execution date |
| `launch_is_executable_next_open` | executable flag |
| `executable_status` | `executable` if `launch_is_executable_next_open = true`, else `blocked` |
| `blocked_buy_reason` | blocked reason if any |
| `industry_bucket` | PIT or EP2 industry as of launch signal date |
| `year_bucket` | launch signal year |
| `money_bucket` | deterministically joined from upstream EP3 anchor / matched-baseline frozen bucket when available, else `unbucketed` |
| `vol20_bucket` | deterministically joined from upstream EP3 anchor / matched-baseline frozen bucket when available, else `unbucketed` |
| `ret_60d_bucket` | deterministically joined from upstream EP3 anchor / matched-baseline frozen bucket when available, else `unbucketed` |
| `denominator_source` | `ep2_launch_pool` |

Bucket join rule for `money_bucket`, `vol20_bucket`, and `ret_60d_bucket`:

```text
source rows:
  union of upstream EP3 candidate anchor rows and matched-baseline rows
  in the same split with a non-null frozen bucket for the requested field.

source_signal_date:
  anchor signal date for anchor rows;
  baseline signal date for matched-baseline rows.

source_event_id:
  anchor_event_id for anchor rows;
  baseline_event_id for matched-baseline rows.

source_type:
  anchor for candidate anchor rows;
  matched_baseline for matched-baseline rows.

tie break:
  1. same instrument and source_signal_date = launch_signal_date;
  2. same instrument with minimum absolute calendar-day distance;
  3. earlier source_signal_date;
  4. lexicographic source_type + ":" + source_event_id.

If no same-instrument source row exists in the same split:
  bucket = unbucketed.

This join is diagnostic-only and must not change trigger numerator membership,
launch denominator membership, split assignment, gate status, or any upstream P0
artifact.
```

For bucket-level trigger rates:

```text
Split-level numerator reproduction:
  report split is the upstream anchor event split.
  raw anchor numerator rows =
    upstream candidate anchor rows where:
      split = report split,
      anchor_family_id = report family,
      dedupe_rank_within_reference_event = 1,
      is_executable_next_open = true.

  gate_eligible_h20 numerator rows =
    raw anchor numerator rows where eligible_for_primary_gate = true.

  For every split + anchor_family_id + trigger_rate_type:
    the split-level raw numerator must reproduce
    ep3_anchor_trigger_budget_audit.csv.anchor_trigger_count;
    the gate_eligible_h20 numerator must reproduce
    ep3_anchor_vs_matched_baseline.csv.event_count where
    baseline_id = anchor and horizon_id = H20.

Denominator split rule:
  denominator rows are always canonical EP2 launch rows whose canonical launch
  split equals the report split.

Cross-split reference rule:
  For every numerator row, join anchor_trigger_rate_denominator_id to the
  canonical EP2 launch denominator panel and compute canonical_launch_split.

  If canonical_launch_split != anchor event split:
    cross_split_reference_status = cross_split_reference;
  else:
    cross_split_reference_status = same_split_reference.

diagnostic_axis in {year_bucket, industry_bucket, executable_status, money_bucket, vol20_bucket, ret_60d_bucket}:
  denominator = count distinct launch_episode_id in the same split and bucket.
  numerator bucket = bucket from the joined canonical denominator row only when
  canonical_launch_split = report split.
  numerator rows whose canonical_launch_split differs from report split must be
  assigned diagnostic_bucket = cross_split_reference and
  denominator_scope = split_level.

diagnostic_axis in {
  anchor_window_position_bucket,
  reference_age_bucket,
  pullback_depth_band,
  second_breakout_gap_band,
  second_breakout_return_band,
  second_breakout_consolidation_drawdown_band
}:
  denominator = count distinct launch_episode_id in the same split.
  numerator bucket = bucket from the anchor event diagnostic panel.
  bucket-level denominator fields must be marked denominator_scope = split_level,
  because non-trigger launch episodes have no anchor-window, reference-age, or
  formula-specific bucket.

Required aggregate trigger rows:
  For every split + anchor_family_id + trigger_rate_type, emit
  diagnostic_axis = all and diagnostic_bucket = all.
  predeclared_partition_id = not_applicable.
  denominator_scope = split_level.
  numerator and denominator must equal the split-level reproduction counts.
```

Required output:

```text
reports/p0_5_trigger_decomposition.csv
```

Required fields:

| Field | Description |
| --- | --- |
| `split` | train / validation / robustness |
| `anchor_family_id` | primary family |
| `diagnostic_axis` | decomposition axis |
| `diagnostic_bucket` | bucket id |
| `predeclared_partition_id` | id from `p0_5_diagnostic_bin_freeze.csv` or `not_applicable` for cross_split_reference / aggregate rows |
| `trigger_rate_type` | raw / gate_eligible_h20 |
| `numerator_split_rule` | anchor_event_split |
| `denominator_split_rule` | canonical_launch_split |
| `numerator_bucket_source` | canonical_denominator_row / anchor_event / cross_split_reference |
| `anchor_trigger_count` | event count |
| `upstream_anchor_trigger_count` | upstream split-level numerator count for reproduction |
| `cross_split_reference_count` | numerator rows whose canonical launch split differs from report split |
| `ep2_launch_episode_count` | denominator |
| `denominator_scope` | bucket_level / split_level |
| `trigger_rate_per_launch_episode` | count / denominator |
| `trigger_rate_band` | config-static band from trigger_rate_reference_bands, display-only |
| `trigger_rate_gap_to_min_budget` | `0.20 - trigger_rate` |
| `unique_instrument_count` | breadth |
| `unique_instrument_year_count` | breadth |
| `trigger_count_reproduction_status` | passed / failed |
| `interpretation_status` | interpretable / too_sparse |

### 7.2 Does lifecycle recall fail to translate into forward audit?

Compare train lifecycle occurrence against forward-audit executable events:

```text
lifecycle_anchor_recall
forward_executable_anchor_rate
gate_eligible_anchor_rate
winner_capture_rate_50h120
```

Required output:

```text
reports/p0_5_lifecycle_forward_translation.csv
```

Row grain:

```text
one row per split + anchor_family_id + translation_metric_id
where split in {train, validation, robustness}.
primary_key = split + anchor_family_id + translation_metric_id
```

Lifecycle-forward translation metrics are independent diagnostic rates, not a
mutually exclusive waterfall. Counts must not be subtracted from one another
unless they share the same explicit row universe and denominator.

Required metric ids and denominator rules:

```text
canonical_launch_denominator:
  distinct canonical EP2 launch episodes in the same split.

deduped_anchor_candidate_count:
  upstream candidate anchor rows with:
    split = row split,
    anchor_family_id = row anchor_family_id,
    dedupe_rank_within_reference_event = 1.

forward_executable_anchor_count:
  deduped anchor candidate rows where is_executable_next_open = true.

forward_gate_eligible_anchor_count:
  deduped anchor candidate rows where:
    is_executable_next_open = true,
    eligible_for_primary_gate = true.

lifecycle_anchor_recall:
  metric_value copied from upstream lifecycle gate value for the family.
  metric_source = ep3_gate_audit.csv.

forward_executable_anchor_rate:
  numerator = forward_executable_anchor_count.
  denominator = canonical_launch_denominator.

forward_gate_eligible_anchor_rate:
  numerator = forward_gate_eligible_anchor_count.
  denominator = canonical_launch_denominator.

execution_block_rate:
  numerator = deduped anchor candidate rows where is_executable_next_open = false.
  denominator = deduped_anchor_candidate_count.

label_horizon_ineligible_rate:
  numerator = deduped executable anchor rows where eligible_for_primary_gate = false.
  denominator = forward_executable_anchor_count.

matched_delay_underperformance_rate:
  numerator = gate-eligible anchor rows whose paired matched_delay_baseline H20
              return exists and whose H20 return is <= matched_delay_baseline H20 return.
  denominator = gate-eligible anchor rows with paired matched_delay_baseline H20 return.

winner_capture_rate_50h120:
  numerator = gate-eligible anchor rows where winner_50h120 = true.
  denominator = forward_gate_eligible_anchor_count.

trigger_budget_shortfall_rate:
  numerator = max(0, 0.20 - forward_executable_anchor_rate).
  denominator = 1.0.
```

Pairing rule for `matched_delay_underperformance_rate`:

```text
Anchor side:
  p0_5_anchor_event_diagnostic_panel rows where:
    split = row split,
    anchor_family_id = row anchor_family_id,
    primary_diagnostic_eligible = true,
    eligible_for_primary_gate = true.

Matched-delay side:
  p0_5_baseline_event_diagnostic_panel rows where:
    baseline_id = matched_delay_baseline,
    anchor_event_id equals the anchor-side anchor_event_id,
    primary_diagnostic_eligible = true,
    eligible_for_primary_gate = true,
    after_cost_return_H20 is non-null.

The pair uses the wide H20 return field `after_cost_return_H20`.
Each anchor_event_id may join to at most one matched_delay_baseline row.
Duplicate matched-delay rows for the same anchor_event_id, unavailable
matched-delay rows, or missing H20 return values are excluded from the
denominator and must be counted in a diagnostic field named
matched_delay_pair_exclusion_count.
```

Minimum required fields:

| Field | Description |
| --- | --- |
| `anchor_family_id` | family |
| `split` | split |
| `translation_metric_id` | required metric id |
| `metric_source` | source artifact or diagnostic panel |
| `lifecycle_anchor_recall` | upstream family-level lifecycle gate value from `ep3_gate_audit.csv`, repeated on split rows |
| `canonical_launch_denominator` | canonical EP2 launch denominator |
| `deduped_anchor_candidate_count` | deduped candidate count |
| `forward_executable_anchor_count` | executable A/C events |
| `forward_gate_eligible_anchor_count` | primary metric eligible events |
| `matched_delay_pair_exclusion_count` | excluded matched-delay pairs for `matched_delay_underperformance_rate` |
| `metric_numerator` | numerator for the metric |
| `metric_denominator` | denominator for the metric |
| `metric_value` | numerator / denominator, or copied upstream value |
| `metric_interpretation` | short diagnostic interpretation |

### 7.3 Is matched-delay baseline exposing no lift?

For every family / split / diagnostic bucket / diagnostic bucket source,
compare anchor H20 against these required pairwise baselines:

- `matched_delay_baseline`;
- `same_instrument_nonanchor_baseline`;
- `industry_matched_baseline`;
- `failed_lookalike_baseline`.

Also emit the required non-pairwise comparator:

- `all_launch_direct_baseline`, report-only, only on the allowed non-pairwise
  axes below.

Diagnostic-axis applicability:

```text
pairwise baselines:
  matched_delay_baseline
  same_instrument_nonanchor_baseline
  industry_matched_baseline
  failed_lookalike_baseline

allowed axes for pairwise baselines:
  all
  anchor_window_position_bucket
  reference_age_bucket
  pullback_depth_band
  second_breakout_gap_band
  second_breakout_return_band
  second_breakout_consolidation_drawdown_band
  year_bucket
  industry_bucket
  money_bucket
  vol20_bucket
  ret_60d_bucket

non-pairwise baseline:
  all_launch_direct_baseline

allowed axes for non-pairwise baseline:
  all
  year_bucket
  industry_bucket

forbidden non-pairwise axes:
  anchor_window_position_bucket
  reference_age_bucket
  pullback_depth_band
  second_breakout_gap_band
  second_breakout_return_band
  second_breakout_consolidation_drawdown_band
  money_bucket
  vol20_bucket
  ret_60d_bucket
```

Pairwise diagnostic bucket attribution:

```text
For matched_delay_baseline, same_instrument_nonanchor_baseline, and
industry_matched_baseline:
  diagnostic_axis buckets must be anchor-side buckets inherited from the
  linked anchor_event_id.

For failed_lookalike_baseline:
  if anchor_event_id is non-empty, diagnostic_axis buckets must be inherited
  from the linked anchor_event_id;
  if anchor_event_id is empty, the row may contribute only to
  failed-lookalike baseline diagnostics with diagnostic_bucket_source =
  baseline_event, and anchor_event_count must be 0 for that bucket row.

For all pairwise matched-lift rows:
  diagnostic_bucket_source must be one of:
    linked_anchor,
    baseline_event.

For required family-level aggregate rows:
  diagnostic_axis = all;
  diagnostic_bucket = all;
  predeclared_partition_id = not_applicable;
  diagnostic_bucket_source = linked_anchor for linked pairwise baselines;
  diagnostic_bucket_source = baseline_event for all_launch_direct_baseline.
  For failed_lookalike_baseline, emit separate aggregate rows for linked_anchor
  and baseline_event if both source types are present.
  Aggregate rows are report-only and must not be named as
  predeclared_partition_id in a stop / continue decision.

For decision or hypothesis evidence based on matched_delay_baseline, the
matched-lift row must have diagnostic_bucket_source = linked_anchor. Rows with
diagnostic_bucket_source = baseline_event are diagnostic-only and cannot support
h1/h2 partition evidence, robustness_not_collapsed, or
write_p0_6_partition_freeze_requirement.

Validation must fail if a matched-lift row mixes anchor-side buckets and
baseline/control-side buckets without declaring diagnostic_bucket_source.
```

Required output:

```text
reports/p0_5_matched_lift_decomposition.csv
```

`reports/p0_5_matched_lift_decomposition.csv` row grain:

```text
one row per split + anchor_family_id + diagnostic_axis + diagnostic_bucket +
diagnostic_bucket_source + baseline_id, using only allowed baseline-axis
combinations from section 7.3.
```

Required fields:

| Field | Description |
| --- | --- |
| `split` | train / validation / robustness |
| `anchor_family_id` | family |
| `diagnostic_axis` | decomposition axis |
| `diagnostic_bucket` | bucket |
| `predeclared_partition_id` | id from `p0_5_diagnostic_bin_freeze.csv` or `not_applicable` for aggregate rows |
| `diagnostic_bucket_source` | linked_anchor / baseline_event |
| `baseline_id` | baseline comparator |
| `anchor_event_count` | count |
| `baseline_event_count` | count |
| `unique_instrument_year_count` | breadth for interpretation and decision rules |
| `anchor_mean_after_cost_return_H20` | anchor mean |
| `baseline_mean_after_cost_return_H20` | baseline mean |
| `mean_diff_vs_baseline` | anchor - baseline |
| `anchor_p05_after_cost_return_H20` | anchor p05 |
| `baseline_p05_after_cost_return_H20` | baseline p05 |
| `p05_diff_vs_baseline` | anchor - baseline |
| `anchor_instrument_year_positive_rate` | anchor stability |
| `baseline_instrument_year_positive_rate` | baseline stability |
| `interpretation_status` | interpretable / too_sparse |

### 7.4 Is tail risk the real blocking issue?

For each family and split, decompose:

- H20 p05;
- H20 max adverse excursion;
- failed-lookalike rate;
- top1 instrument-year PnL share;
- top5 instrument exposure share.

Required output:

```text
reports/p0_5_tail_failure_decomposition.csv
```

### 7.5 Are failures concentrated in years, industries, or instruments?

The implementation must produce concentration audit tables:

```text
reports/p0_5_year_industry_concentration.csv
reports/p0_5_instrument_concentration.csv
```

These reports must distinguish:

```text
event concentration
positive PnL concentration
negative tail concentration
winner capture concentration
```

## 8. Diagnostic Variants

P0.5 must compute the required diagnostic-only variants below, but must not
promote them.

Allowed variants:

| Variant family | Allowed use |
| --- | --- |
| `anchor_window_position_bucket` | diagnose early/middle/late anchor window behavior |
| `reference_age_bucket` | diagnose age from reference acceleration to anchor |
| `pullback_depth_band` | diagnose whether pullback drawdown band is too strict or too loose |
| `second_breakout_gap_band` | diagnose gap between first and second breakout |
| `second_breakout_return_band` | diagnose whether second-breakout return threshold is too strict |
| `second_breakout_consolidation_drawdown_band` | diagnose whether consolidation drawdown threshold is too strict |
| `money_bucket` | diagnose liquidity state |
| `vol20_bucket` | diagnose volatility state |
| `ret_60d_bucket` | diagnose pre-anchor momentum state |
| `industry_bucket` | concentration and stability only |
| `year_bucket` | regime drift only |

Forbidden variant behavior:

- no validation-selected best bucket;
- no robustness-selected best bucket;
- no new anchor family implementation;
- no new executable signal table;
- no row promoted to P1 candidate;
- no changing P0 anchor formulas or P0 output files.

## 9. Outputs

All outputs must live under:

```text
ep3/outputs/p0_5_anchor_failure_diagnostic/
```

Required reports:

```text
reports/p0_5_upstream_reproduction.csv
reports/p0_5_upstream_authority.csv
reports/p0_5_stage_order_audit.csv
reports/p0_5_diagnostic_bin_freeze.csv
reports/p0_5_trigger_denominator_panel.csv
reports/p0_5_trigger_denominator_reconciliation.csv
reports/p0_5_trigger_decomposition.csv
reports/p0_5_lifecycle_forward_translation.csv
reports/p0_5_matched_lift_decomposition.csv
reports/p0_5_sensitivity_horizon_audit.csv
reports/p0_5_tail_failure_decomposition.csv
reports/p0_5_year_industry_concentration.csv
reports/p0_5_instrument_concentration.csv
reports/p0_5_hypothesis_audit.csv
reports/p0_5_stop_continue_decision.csv
reports/p0_5_diagnostic_report.md
```

### 9.0 Additional Required Report Schemas

The following required reports are not fully specified elsewhere in this
document and must use these minimum schemas.

`reports/p0_5_upstream_reproduction.csv` row grain:

```text
one row per primary anchor family
primary_key = anchor_family_id
```

Required fields:

| Field | Description |
| --- | --- |
| `anchor_family_id` | primary family |
| `upstream_ep3_p1_decision_status` | decision status reproduced from upstream P0 |
| `reproduced_ep3_p1_decision_status` | status computed by P0.5 from frozen upstream artifacts |
| `upstream_passed_gate_count` | count from upstream gate audit |
| `reproduced_passed_gate_count` | P0.5 recomputed passed-gate count |
| `upstream_failed_gate_count` | count from upstream gate audit |
| `reproduced_failed_gate_count` | P0.5 recomputed failed-gate count |
| `validation_raw_trigger_rate_per_launch_episode` | from `ep3_anchor_trigger_budget_audit.csv` |
| `validation_gate_eligible_h20_trigger_rate_per_launch_episode` | from `ep3_anchor_vs_matched_baseline.csv` where `baseline_id = anchor` and `horizon_id = H20` |
| `validation_h20_mean_diff_vs_matched_delay` | anchor H20 mean minus matched-delay H20 mean |
| `validation_h20_p05_diff_vs_matched_delay` | anchor H20 p05 minus matched-delay H20 p05 |
| `reproduction_status` | passed / failed |

`reports/p0_5_diagnostic_bin_freeze.csv` row grain:

```text
one row per predeclared diagnostic partition:
  anchor_family_id + diagnostic_axis + diagnostic_bucket.

For family-specific axes, anchor_family_id must be the primary family.
For global axes, anchor_family_id must be all.
```

Required fields:

| Field | Description |
| --- | --- |
| `predeclared_partition_id` | deterministic id for anchor_family_id + diagnostic_axis + diagnostic_bucket |
| `anchor_family_id` | primary family or `all` |
| `diagnostic_axis` | axis name |
| `diagnostic_bucket` | frozen bucket id |
| `bin_source_split` | train / config_static / upstream_p0_train_frozen |
| `bin_method` | quantile / config_edges / copied_from_p0 / categorical |
| `source_upstream_artifact` | upstream artifact path for copied bins, else blank |
| `source_upstream_hash` | live hash of source_upstream_artifact for copied bins, else blank |
| `source_field_name` | copied upstream field name or source metric name |
| `bin_edges_json` | serialized edges or category list |
| `bucket_lower_bound` | numeric lower bound when applicable, else blank |
| `bucket_upper_bound` | numeric upper bound when applicable, else blank |
| `bucket_inclusive_rule` | left_closed_right_open / closed / categorical |
| `train_observation_count` | train rows used to derive the bin; copied from source artifact when bin_source_split = upstream_p0_train_frozen; 0 for config-static bins |
| `validation_outcomes_used` | must be false |
| `robustness_outcomes_used` | must be false |
| `frozen_before_validation` | must be true |
| `bin_hash` | deterministic hash of axis, source, method, and edges |

Copied-bin validation rules:

```text
If bin_source_split = upstream_p0_train_frozen:
  bin_method must be copied_from_p0;
  source_upstream_artifact and source_upstream_hash must be non-empty;
  source_upstream_artifact must equal the configured
    upstream_ep3_p0.matched_control_bucket_freeze path;
  live source_upstream_hash must match p0_5_upstream_authority.csv;
  diagnostic_axis must be one of:
    money_bucket,
    vol20_bucket,
    ret_60d_bucket.
```

`reports/p0_5_sensitivity_horizon_audit.csv` row grain:

```text
one row per split + anchor_family_id + horizon_id + diagnostic_axis +
diagnostic_bucket + diagnostic_bucket_source + baseline_id, using only allowed
baseline-axis combinations from section 7.3.
```

Required rows:

```text
For every row in p0_5_matched_lift_decomposition.csv where
diagnostic_axis / diagnostic_bucket / diagnostic_bucket_source / baseline_id is
allowed by section 7.3, emit one sensitivity row for each configured
diagnostic_scope.sensitivity_horizons value.

For aggregate rows where diagnostic_axis = all and diagnostic_bucket = all,
source-specific sensitivity rows with diagnostic_bucket_source in
{linked_anchor, baseline_event} must set
upstream_aggregate_reproduction_status = not_applicable.

Additionally, emit one blended aggregate reproduction row for every
split + anchor_family_id + baseline_id + horizon_id present in
ep3_sensitivity_horizon_audit.csv:
  diagnostic_axis = all;
  diagnostic_bucket = all;
  predeclared_partition_id = not_applicable;
  diagnostic_bucket_source = all_sources.
The all_sources row combines linked_anchor and baseline_event rows for the same
split, family, baseline, and horizon, and must reproduce
ep3_sensitivity_horizon_audit.csv. For baselines that have only one source type,
all_sources may equal the single available source. all_sources rows are allowed
only in p0_5_sensitivity_horizon_audit.csv aggregate reproduction rows.
```

Required fields:

| Field | Description |
| --- | --- |
| `split` | train / validation / robustness |
| `anchor_family_id` | primary family |
| `horizon_id` | H10 / H60 from configured sensitivity_horizons |
| `diagnostic_axis` | decomposition axis |
| `diagnostic_bucket` | bucket id |
| `predeclared_partition_id` | id from `p0_5_diagnostic_bin_freeze.csv` or `not_applicable` for aggregate rows |
| `diagnostic_bucket_source` | linked_anchor / baseline_event / all_sources for aggregate sensitivity reproduction only |
| `baseline_id` | comparator baseline |
| `anchor_event_count` | anchor event count with horizon return available |
| `baseline_event_count` | baseline event count with horizon return available |
| `anchor_mean_after_cost_return` | anchor mean for horizon_id |
| `baseline_mean_after_cost_return` | baseline mean for horizon_id |
| `mean_diff_vs_baseline` | anchor - baseline for horizon_id |
| `anchor_p05_after_cost_return` | anchor p05 for horizon_id |
| `baseline_p05_after_cost_return` | baseline p05 for horizon_id |
| `p05_diff_vs_baseline` | anchor p05 minus baseline p05 for horizon_id |
| `anchor_max_adverse_excursion_mean` | anchor mean MAE for horizon_id |
| `baseline_max_adverse_excursion_mean` | baseline mean MAE for horizon_id |
| `upstream_aggregate_reproduction_status` | passed / failed / not_applicable |
| `sensitivity_decision_use_allowed` | must be false |
| `interpretation_status` | report_only / too_sparse |

Sensitivity metric source rule:

```text
For horizon_id = H10:
  use after_cost_return_H10 and max_adverse_excursion_H10 from
  p0_5_anchor_event_diagnostic_panel and p0_5_baseline_event_diagnostic_panel.

For horizon_id = H60:
  use after_cost_return_H60 and max_adverse_excursion_H60 from
  p0_5_anchor_event_diagnostic_panel and p0_5_baseline_event_diagnostic_panel.

anchor_event_count and baseline_event_count count rows with the required
horizon return and MAE fields present. Rows missing either horizon field are
excluded from the corresponding sensitivity metric denominator and count.
```

Sensitivity rows are report-only. They must not be used in
`p0_5_hypothesis_audit.csv`, `p0_5_stop_continue_decision.csv`, partition
selection, threshold selection, or P1/P0.6 promotion.

`reports/p0_5_tail_failure_decomposition.csv` row grain:

```text
one row per split + anchor_family_id + diagnostic_axis + diagnostic_bucket +
diagnostic_bucket_source + baseline_id, using only allowed baseline-axis
combinations from section 7.3.
```

Required fields:

| Field | Description |
| --- | --- |
| `split` | train / validation / robustness |
| `anchor_family_id` | primary family |
| `diagnostic_axis` | decomposition axis |
| `diagnostic_bucket` | bucket id |
| `predeclared_partition_id` | id from `p0_5_diagnostic_bin_freeze.csv` or `not_applicable` for aggregate rows |
| `diagnostic_bucket_source` | linked_anchor / baseline_event |
| `baseline_id` | comparator baseline |
| `anchor_event_count` | anchor event count |
| `baseline_event_count` | baseline event count |
| `failed_lookalike_baseline_event_count` | count of eligible failed-lookalike baseline rows in the same bucket/source |
| `unique_instrument_year_count` | breadth for interpretation and decision rules |
| `anchor_p05_after_cost_return_H20` | anchor H20 p05 |
| `baseline_p05_after_cost_return_H20` | baseline H20 p05 |
| `p05_diff_vs_baseline` | anchor p05 minus baseline p05 |
| `anchor_max_adverse_excursion_mean_H20` | anchor H20 mean MAE |
| `baseline_max_adverse_excursion_mean_H20` | baseline H20 mean MAE |
| `mae_worsening_vs_baseline` | positive amount by which anchor MAE is worse than baseline MAE |
| `failed_lookalike_rate` | failed-lookalike share for the bucket |
| `top1_instrument_year_pnl_share` | concentration metric |
| `top1_threshold` | threshold from `ep3_gate_audit.csv` for the same split / family gate |
| `top1_threshold_status` | passed / failed / not_applicable |
| `top5_instrument_exposure_share` | concentration metric |
| `top5_threshold` | threshold from `ep3_gate_audit.csv` for the same split / family gate |
| `top5_threshold_status` | passed / failed / not_applicable |
| `interpretation_status` | interpretable / too_sparse |

Tail metric formulas:

```text
mae_worsening_vs_baseline =
  max(
    0,
    baseline_max_adverse_excursion_mean_H20
      - anchor_max_adverse_excursion_mean_H20
  ).

This matches the EP3-P0 gate convention where max adverse excursion is a
negative-return-style measure and a more negative anchor value is worse.

failed_lookalike_rate =
  failed_lookalike_baseline_event_count
  / (anchor_event_count + failed_lookalike_baseline_event_count).

For a bucket row, failed_lookalike_baseline_event_count is the count of
primary_diagnostic_eligible `failed_lookalike_baseline` rows in the same split,
anchor_family_id, diagnostic_axis, diagnostic_bucket, and
diagnostic_bucket_source. For aggregate rows, use diagnostic_axis = all and
diagnostic_bucket = all.
When baseline_id = failed_lookalike_baseline, this count must equal
baseline_event_count. For other baseline_id values, it is still populated from
the failed-lookalike rows in the same bucket so the rate is comparable across
tail rows.

top1_instrument_year_pnl_share:
  group anchor-side primary_diagnostic_eligible rows in the bucket by
  instrument + signal year;
  sum after_cost_return_H20 by instrument-year;
  use max(positive instrument-year sum) / sum(positive instrument-year sums);
  if no positive instrument-year sum exists, set 0.

top5_instrument_exposure_share:
  count anchor-side primary_diagnostic_eligible rows in the bucket by
  instrument;
  use top five instrument counts / anchor_event_count.

top1_threshold and top5_threshold must be copied from `ep3_gate_audit.csv`
using gate names:
  {split}_top1_instrument_year_pnl_share
  {split}_top5_instrument_exposure_share
where split is validation or robustness. For train rows set threshold_status =
not_applicable.
```

`reports/p0_5_year_industry_concentration.csv` row grain:

```text
one row per split + anchor_family_id + concentration_axis + concentration_bucket
where concentration_axis in {year_bucket, industry_bucket}.
```

Concentration row universe and denominator rules:

```text
source rows:
  p0_5_anchor_event_diagnostic_panel rows where:
    split in {train, validation, robustness};
    anchor_family_id is a primary family;
    primary_diagnostic_eligible = true;
    eligible_for_primary_gate = true;
    after_cost_return_H20 is present.

family_split_event_denominator:
  count source rows for the same split + anchor_family_id.

bucket_event_count:
  count source rows in the same split + anchor_family_id and concentration
  bucket.

event_share:
  bucket_event_count / family_split_event_denominator.

positive_pnl_event_count:
  count source rows in the bucket where after_cost_return_H20 > 0.

positive_pnl_share:
  positive_pnl_event_count / family_split_positive_pnl_event_count, where
  family_split_positive_pnl_event_count is the count of source rows in the same
  split + anchor_family_id where after_cost_return_H20 > 0.

negative_tail_event_count:
  compute the family/split H20 bottom-5pct threshold over source rows only;
  count source rows in the bucket where after_cost_return_H20 is <= that
  threshold.

family_split_negative_tail_event_count:
  count source rows in the same split + anchor_family_id where
  after_cost_return_H20 is <= the family/split H20 bottom-5pct threshold.

negative_tail_share:
  negative_tail_event_count / family_split_negative_tail_event_count.

winner_capture_event_count:
  count source rows in the bucket where winner_50h120 = true.

family_split_winner_capture_event_count:
  count source rows in the same split + anchor_family_id where
  winner_50h120 = true.

winner_capture_share:
  winner_capture_event_count / family_split_winner_capture_event_count.

If any share denominator is 0, set the corresponding share to 0 and
interpretation_status = too_sparse for that row.
```

Required fields:

| Field | Description |
| --- | --- |
| `split` | train / validation / robustness |
| `anchor_family_id` | primary family |
| `concentration_axis` | year_bucket / industry_bucket |
| `concentration_bucket` | year or industry bucket |
| `event_count` | anchor event count |
| `event_share` | bucket event share within family and split |
| `positive_pnl_event_count` | count with H20 after-cost return > 0 |
| `positive_pnl_share` | positive PnL share within family and split |
| `negative_tail_event_count` | count in bottom 5% H20 after-cost return within family and split |
| `negative_tail_share` | negative-tail share within family and split |
| `winner_capture_event_count` | count with `winner_50h120 = true` |
| `winner_capture_share` | winner-capture share within family and split |
| `interpretation_status` | interpretable / too_sparse |

`reports/p0_5_instrument_concentration.csv` row grain:

```text
one row per split + anchor_family_id + instrument.
```

Required fields:

| Field | Description |
| --- | --- |
| `split` | train / validation / robustness |
| `anchor_family_id` | primary family |
| `instrument` | instrument |
| `event_count` | anchor event count |
| `event_share` | instrument event share within family and split |
| `positive_pnl_event_count` | count with H20 after-cost return > 0 |
| `positive_pnl_share` | positive PnL share within family and split |
| `negative_tail_event_count` | count in bottom 5% H20 after-cost return within family and split |
| `negative_tail_share` | negative-tail share within family and split |
| `winner_capture_event_count` | count with `winner_50h120 = true` |
| `winner_capture_share` | winner-capture share within family and split |
| `pnl_sum_after_cost_H20` | summed H20 after-cost return |
| `pnl_share_after_cost_H20` | share of total family/split H20 PnL contribution |
| `instrument_year_count` | unique instrument-year count represented by the row |
| `interpretation_status` | interpretable / too_sparse |

For `p0_5_instrument_concentration.csv`, use the same source rows and count
share denominators as `p0_5_year_industry_concentration.csv`. Additionally:

```text
pnl_sum_after_cost_H20:
  sum after_cost_return_H20 for source rows in the instrument row.

pnl_share_after_cost_H20:
  pnl_sum_after_cost_H20 / family_split_pnl_sum_after_cost_H20, where
  family_split_pnl_sum_after_cost_H20 is the sum of after_cost_return_H20 over
  all source rows in the same split + anchor_family_id.

If family_split_pnl_sum_after_cost_H20 = 0, set pnl_share_after_cost_H20 = 0 and
interpretation_status = too_sparse.
```

`reports/p0_5_diagnostic_report.md` must include these sections:

```text
upstream authority and reproduction status;
trigger denominator reconciliation;
trigger-budget decomposition;
matched-lift decomposition;
H10/H60 sensitivity audit;
tail and concentration findings;
hypothesis audit;
stop / continue decision.
```

Required cache:

```text
cache/p0_5_anchor_event_diagnostic_panel.parquet
cache/p0_5_baseline_event_diagnostic_panel.parquet
```

### 9.1 Anchor Event Diagnostic Panel

`cache/p0_5_anchor_event_diagnostic_panel.parquet` row grain:

```text
one row per upstream EP3-P0 candidate anchor event
primary_key = anchor_event_id
```

Required fields:

| Field | Description |
| --- | --- |
| `anchor_event_id` | copied from P0 candidate anchor panel |
| `anchor_family_id` | primary family |
| `instrument` | instrument |
| `signal_date` | close-derived signal date |
| `execution_date` | next-open execution date |
| `split` | train / validation / robustness / out_of_scope |
| `primary_diagnostic_eligible` | true only when split is train / validation / robustness and required dates are present |
| `primary_diagnostic_eligibility_reason` | eligible / out_of_scope / missing_required_date / missing_linked_anchor / invalid_baseline_scope |
| `source_upstream_artifact` | `ep3_candidate_anchor_panel.parquet` |
| `source_upstream_hash` | upstream artifact hash used in this run |
| `is_executable_next_open` | copied from P0 |
| `eligible_for_primary_gate` | copied from P0 |
| `label_join_status` | copied from P0 |
| `dedupe_rank_within_reference_event` | copied from P0 |
| `reference_acceleration_event_id` | copied from P0 |
| `reference_acceleration_date` | copied from P0 |
| `reference_age_days` | trading days from reference acceleration to signal |
| `anchor_window_position_ratio` | normalized position in frozen anchor window |
| `anchor_window_position_bucket` | train-derived bucket |
| `reference_age_bucket` | config-defined bucket |
| `formula_diagnostic_status` | available / not_applicable / missing_price_row / missing_reference_date |
| `pullback_depth_from_acceleration_close` | pullback formula diagnostic, else unavailable |
| `pullback_depth_band` | train-derived bucket for pullback depth, else unavailable |
| `second_breakout_gap_days` | trading days from reference acceleration to second breakout, else unavailable |
| `second_breakout_gap_band` | config-defined bucket for second breakout gap, else unavailable |
| `second_breakout_return_from_first_close` | second-breakout return diagnostic, else unavailable |
| `second_breakout_return_band` | train-derived bucket for second-breakout return, else unavailable |
| `second_breakout_consolidation_drawdown_from_first_close` | interval min-low drawdown diagnostic, else unavailable |
| `second_breakout_consolidation_drawdown_band` | train-derived bucket for consolidation drawdown, else unavailable |
| `money_bucket` | copied from P0 matched-control bucket inputs |
| `vol20_bucket` | copied from P0 matched-control bucket inputs |
| `ret_60d_bucket` | copied from P0 matched-control bucket inputs |
| `industry_bucket` | PIT industry at signal date |
| `year_bucket` | signal year |
| `exit_date_H10` | copied from P0 anchor event |
| `after_cost_return_H10` | copied from P0 anchor event |
| `max_adverse_excursion_H10` | copied from P0 anchor event |
| `after_cost_return_H20` | copied from P0 anchor event |
| `max_adverse_excursion_H20` | copied from P0 anchor event |
| `exit_date_H60` | copied from P0 anchor event |
| `after_cost_return_H60` | copied from P0 anchor event |
| `max_adverse_excursion_H60` | copied from P0 anchor event |
| `winner_50h120` | copied from P0 label join |
| `winner_100h240` | copied from P0 label join |
| `diagnostic_panel_hash` | row-level hash |

Forbidden fields:

```text
selected_for_p1
strategy_signal
production_signal
validation_selected_bucket
robustness_selected_bucket
```

### 9.2 Baseline Event Diagnostic Panel

`cache/p0_5_baseline_event_diagnostic_panel.parquet` row grain:

```text
one row per upstream EP3-P0 matched baseline event
primary_key = baseline_event_id
```

Required fields:

| Field | Description |
| --- | --- |
| `baseline_event_id` | copied from P0 matched baseline panel |
| `anchor_event_id` | linked anchor id when available |
| `anchor_family_id` | linked family |
| `baseline_id` | baseline comparator |
| `instrument` | baseline instrument |
| `signal_date` | baseline signal date |
| `execution_date` | next-open execution date |
| `split` | train / validation / robustness / out_of_scope |
| `primary_diagnostic_eligible` | true only when split is train / validation / robustness and required dates are present |
| `primary_diagnostic_eligibility_reason` | eligible / out_of_scope / missing_required_date / missing_linked_anchor / invalid_baseline_scope |
| `source_upstream_artifact` | `ep3_matched_baseline_panel.parquet` |
| `source_upstream_hash` | upstream artifact hash used in this run |
| `match_status` | copied from P0 |
| `matched_control_bucket_id` | copied from P0 |
| `delay_repair_flag` | copied from P0 |
| `control_shortfall_flag` | copied from P0 |
| `eligible_for_primary_gate` | copied from P0 |
| `label_join_status` | copied from P0 |
| `reference_acceleration_event_id` | copied from P0 |
| `reference_acceleration_date` | copied from P0 when available |
| `reference_age_days` | trading days from reference acceleration to baseline signal when available |
| `anchor_window_position_ratio` | linked anchor ratio or baseline-event ratio for unlinked failed lookalikes |
| `reference_age_bucket` | inherited from linked anchor, or recomputed for unlinked failed lookalikes |
| `anchor_window_position_bucket` | inherited from linked anchor when pairwise, or recomputed for unlinked failed lookalikes |
| `pullback_depth_band` | inherited from linked anchor when applicable, or `unbucketed` |
| `second_breakout_gap_band` | inherited from linked anchor when applicable, or `unbucketed` |
| `second_breakout_return_band` | inherited from linked anchor when applicable, or `unbucketed` |
| `second_breakout_consolidation_drawdown_band` | inherited from linked anchor when applicable, or `unbucketed` |
| `diagnostic_bucket_source` | linked_anchor / baseline_event / unbucketed |
| `money_bucket` | inherited from linked anchor for pairwise rows; `unbucketed` for all-launch rows; baseline-event bucket only for unlinked failed lookalikes |
| `vol20_bucket` | inherited from linked anchor for pairwise rows; `unbucketed` for all-launch rows; baseline-event bucket only for unlinked failed lookalikes |
| `ret_60d_bucket` | inherited from linked anchor for pairwise rows; `unbucketed` for all-launch rows; baseline-event bucket only for unlinked failed lookalikes |
| `industry_bucket` | PIT industry at baseline signal date |
| `year_bucket` | signal year |
| `exit_date_H10` | copied from P0 baseline event |
| `after_cost_return_H10` | copied from P0 baseline event |
| `max_adverse_excursion_H10` | copied from P0 baseline event |
| `after_cost_return_H20` | copied from P0 baseline event |
| `max_adverse_excursion_H20` | copied from P0 baseline event |
| `exit_date_H60` | copied from P0 baseline event |
| `after_cost_return_H60` | copied from P0 baseline event |
| `max_adverse_excursion_H60` | copied from P0 baseline event |
| `winner_50h120` | copied from P0 label join |
| `winner_100h240` | copied from P0 label join |
| `diagnostic_panel_hash` | row-level hash |

For non-pairwise `all_launch_direct_baseline`, linked-anchor fields may be empty but `baseline_id`, `instrument`, `signal_date`, `split`, H20 return fields, and label eligibility fields are still required.
`reference_age_bucket`, `anchor_window_position_bucket`, and formula-specific buckets must be empty for `all_launch_direct_baseline`.
`money_bucket`, `vol20_bucket`, and `ret_60d_bucket` must be `unbucketed` for `all_launch_direct_baseline`, because upstream all-launch rows do not carry matched-control bucket state.
Any report row that attempts to decompose `all_launch_direct_baseline` by `anchor_window_position_bucket`, `reference_age_bucket`, formula-specific buckets, `money_bucket`, `vol20_bucket`, or `ret_60d_bucket` must fail validation.

`primary_diagnostic_eligible` required-date rules:

```text
The field is a diagnostic row-usability flag, not a replacement for
eligible_for_primary_gate.

Anchor rows:
  primary_diagnostic_eligible = true only if:
    split in {train, validation, robustness};
    anchor_family_id is a primary family;
    signal_date is present;
    execution_date is present;
    reference_acceleration_date is present.

Pairwise baseline rows with a linked anchor_event_id:
  applies to:
    matched_delay_baseline,
    same_instrument_nonanchor_baseline,
    industry_matched_baseline,
    failed_lookalike_baseline.
  primary_diagnostic_eligible = true only if:
    split in {train, validation, robustness};
    signal_date is present;
    execution_date is present;
    linked anchor_event_id exists in p0_5_anchor_event_diagnostic_panel;
    linked anchor row has primary_diagnostic_eligible = true.

Unlinked failed_lookalike_baseline rows:
  primary_diagnostic_eligible = true only if:
    split in {train, validation, robustness};
    signal_date is present;
    execution_date is present;
    reference_acceleration_date is present.

all_launch_direct_baseline rows:
  primary_diagnostic_eligible = true only if:
    split in {train, validation, robustness};
    signal_date is present;
    execution_date is present.
  These rows still must keep anchor-window, reference-age, money, vol20, and
  ret_60d buckets empty or unbucketed as specified above.

All out_of_scope rows must set primary_diagnostic_eligible = false even when
dates are present.
```

Unavailable-field policy:

```text
For any diagnostic cache row where primary_diagnostic_eligible = false, or where
signal_date / execution_date is missing:
  date-derived diagnostic fields must be set to unavailable:
    industry_bucket
    year_bucket
    reference_age_days
    anchor_window_position_ratio
    reference_age_bucket
    anchor_window_position_bucket
    pullback_depth_from_acceleration_close
    pullback_depth_band
    second_breakout_gap_days
    second_breakout_gap_band
    second_breakout_return_from_first_close
    second_breakout_return_band
    second_breakout_consolidation_drawdown_from_first_close
    second_breakout_consolidation_drawdown_band

  pairwise-bucket fields must be set to unbucketed unless they are directly
  copied from a linked primary_diagnostic_eligible anchor row:
    money_bucket
    vol20_bucket
    ret_60d_bucket

  diagnostic_bucket_source must be unavailable unless the row is an eligible
  linked-anchor pairwise row or an eligible unlinked failed-lookalike row.

Unavailable rows are cache passthrough rows only and must not contribute to any
primary report denominator, numerator, hypothesis support, or decision rule.
```

Required manifest:

```text
manifests/p0_5_anchor_failure_diagnostic_manifest.json
```

## 10. Hypothesis Audit

`p0_5_hypothesis_audit.csv` row grain:

```text
one row per primary anchor family + hypothesis_id
primary_key = anchor_family_id + hypothesis_id
```

| Field | Description |
| --- | --- |
| `anchor_family_id` | primary family |
| `hypothesis_id` | h1-h5 |
| `hypothesis_text` | diagnostic question |
| `evidence_summary` | short evidence |
| `support_status` | supported / rejected / inconclusive |
| `support_rule_id` | deterministic rule id from the table below |
| `support_rule_status` | passed / failed / inconclusive |
| `support_rule_metrics_json` | serialized metric values used by the support rule |
| `primary_evidence_report` | report path |
| `can_justify_p1` | must be false in P0.5 |
| `requires_new_requirement` | true if follow-up coding is needed |

Interpretation rules:

```text
supported does not mean tradable.
supported does not mean P1 candidate.
supported only means the next requirement can be written around this failure mode.
```

Support-status calculation:

```text
support_status must be derived mechanically from support_rule_status:
  passed -> supported
  failed -> rejected
  inconclusive -> inconclusive

Common interpretable partition:
  A trigger partition is interpretable only when:
    p0_5_trigger_decomposition.interpretation_status = interpretable;
    anchor_trigger_count >= diagnostic_bins.event_count_min_for_interpretation;
    unique_instrument_year_count >=
      diagnostic_bins.instrument_year_count_min_for_interpretation.
  A matched-lift or tail partition is interpretable only when:
    interpretation_status = interpretable;
    anchor_event_count >= diagnostic_bins.event_count_min_for_interpretation;
    unique_instrument_year_count >=
      diagnostic_bins.instrument_year_count_min_for_interpretation.

validation_positive_partition:
  same split + anchor_family_id + diagnostic_axis + diagnostic_bucket +
  predeclared_partition_id appears in:
    p0_5_trigger_decomposition.csv with trigger_rate_type = gate_eligible_h20;
    p0_5_matched_lift_decomposition.csv with
      baseline_id = matched_delay_baseline and
      diagnostic_bucket_source = linked_anchor.
  The trigger row must be interpretable and have
    trigger_rate_per_launch_episode >= 0.20.
  The matched-lift row must be interpretable and have:
    mean_diff_vs_baseline > 0;
    p05_diff_vs_baseline >= -0.003.

robustness_not_collapsed:
  the same predeclared_partition_id is present in robustness matched-lift rows
  against matched_delay_baseline with diagnostic_bucket_source = linked_anchor
  and:
    interpretation_status = interpretable;
    mean_diff_vs_baseline >= -0.001 against matched_delay_baseline;
    p05_diff_vs_baseline >= -0.005 against matched_delay_baseline.

h1_formula_too_narrow:
  passed if validation_positive_partition and robustness_not_collapsed exist
  for an axis in:
    pullback_depth_band,
    second_breakout_return_band,
    second_breakout_consolidation_drawdown_band.

h2_window_position_problem:
  passed if validation_positive_partition and robustness_not_collapsed exist
  for an axis in:
    anchor_window_position_bucket,
    reference_age_bucket,
    second_breakout_gap_band.

h3_ep2_reference_pollution:
  passed if validation aggregate p0_5_trigger_decomposition.csv rows
  (diagnostic_axis = all, diagnostic_bucket = all) have
  cross_split_reference_count / anchor_trigger_count >= 0.10
  in either raw or gate_eligible_h20 trigger_rate_type, and the same aggregate
  ratio is not lower than 0.05 in robustness.
  If anchor_trigger_count is 0 in either split, support_rule_status is
  inconclusive.

h4_matched_baseline_too_strong_or_anchor_no_lift:
  passed if both validation and robustness show at least one of:
    aggregate matched-lift row where diagnostic_axis = all,
      baseline_id = matched_delay_baseline, and mean_diff_vs_baseline <= 0;
    aggregate matched-lift row where diagnostic_axis = all,
      baseline_id = matched_delay_baseline, and p05_diff_vs_baseline < -0.003;
    lifecycle-forward translation row where
      translation_metric_id = matched_delay_underperformance_rate and
      metric_value >= 0.50.

h5_tail_risk_not_trigger_rate_is_core_failure:
  passed if validation and robustness aggregate tail rows where
  diagnostic_axis = all and baseline_id = matched_delay_baseline show either:
    p05_diff_vs_baseline < -0.003;
    mae_worsening_vs_baseline > 0.005;
    top1_threshold_status = failed;
    top5_threshold_status = failed.

If validation has enough rows for a rule but robustness is too sparse, set
support_rule_status = inconclusive. If validation is too sparse, set
support_rule_status = inconclusive. If validation is interpretable and the
rule condition is false, set support_rule_status = failed.
```

## 11. Stop / Continue Decision

`p0_5_stop_continue_decision.csv` must contain exactly one row per anchor family plus one overall row.

Decision-partition definitions:

```text
decision-eligible partition:
  a non-aggregate predeclared_partition_id where:
    diagnostic_axis in {
      anchor_window_position_bucket,
      reference_age_bucket,
      pullback_depth_band,
      second_breakout_gap_band,
      second_breakout_return_band,
      second_breakout_consolidation_drawdown_band,
      money_bucket,
      vol20_bucket,
      ret_60d_bucket
    };
    predeclared_partition_id != not_applicable;
    the same split + anchor_family_id + diagnostic_axis + diagnostic_bucket +
      predeclared_partition_id exists in p0_5_trigger_decomposition.csv with
      trigger_rate_type = gate_eligible_h20;
    the same key exists in p0_5_matched_lift_decomposition.csv with
      baseline_id = matched_delay_baseline and
      diagnostic_bucket_source = linked_anchor.

  baseline_event diagnostic_bucket_source rows are excluded from
  decision-eligible partitions, validation_interpretable_partition_count, and
  robustness_interpretable_partition_count.

validation_interpretable_partition_count:
  count distinct decision-eligible partitions in validation where both the
  trigger row and matched-lift row satisfy the Common interpretable partition
  rules in section 10.

robustness_interpretable_partition_count:
  same count in robustness.

partition_freeze_rule_status:
  passed only when the decision row names exactly one decision-eligible
  partition and that same predeclared_partition_id satisfies the
  write_p0_6_partition_freeze_requirement rule below.

robustness_collapse_status:
  for a named predeclared_partition_id, passed only if robustness_not_collapsed
  from section 10 is true for that same partition;
  failed if a named partition does not satisfy robustness_not_collapsed;
  not_applicable when no partition is named.

family_stop_required:
  true only when any stop_current_family required condition below is true;
  false for family rows otherwise;
  not_applicable for the overall row.

formula_repair_rule_status:
  passed only when the write_p0_6_formula_repair_requirement rule below is
  satisfied for the family row; failed for family rows otherwise; not_applicable
  for the overall row.

deferred_family_rule_status:
  passed only when the write_deferred_family_requirement rule below is
  satisfied for the overall row; failed for the overall row otherwise;
  not_applicable for family rows.

For decision fields, predeclared_partition_source must be copied from
p0_5_diagnostic_bin_freeze.csv.bin_source_split and mapped as:
  train -> train_frozen;
  config_static -> config_static;
  upstream_p0_train_frozen -> upstream_p0_train_frozen.
```

Required fields:

| Field | Description |
| --- | --- |
| `decision_scope` | `family` or `overall` |
| `anchor_family_id` | primary family, or `all` for the overall row |
| `recommended_decision` | one allowed decision |
| `decision_precedence_rank` | integer rank from the precedence table below |
| `supporting_hypothesis_ids` | `;`-separated hypothesis ids |
| `primary_evidence_report` | report path containing the primary evidence |
| `validation_interpretable_partition_count` | count of validation partitions marked interpretable |
| `robustness_interpretable_partition_count` | count of robustness partitions marked interpretable |
| `predeclared_partition_id` | train-frozen partition id used for the decision, or blank when not applicable |
| `predeclared_partition_source` | train_frozen / config_static / upstream_p0_train_frozen / not_applicable |
| `validation_partition_trigger_rate_per_launch_episode` | trigger rate for the predeclared partition, or blank when not applicable |
| `validation_partition_unique_instrument_year_count` | breadth for the predeclared partition, or blank when not applicable |
| `validation_partition_mean_diff_vs_matched_delay` | matched-delay mean lift for the predeclared partition, or blank when not applicable |
| `validation_partition_p05_diff_vs_matched_delay` | matched-delay p05 lift for the predeclared partition, or blank when not applicable |
| `robustness_collapse_status` | passed / failed / not_applicable |
| `family_stop_required` | true / false / not_applicable |
| `partition_freeze_rule_status` | passed / failed / not_applicable |
| `formula_repair_rule_status` | passed / failed / not_applicable |
| `deferred_family_rule_status` | passed / failed / not_applicable |
| `decision_rule_status` | passed / failed |
| `decision_rationale` | short text |

Allowed decisions:

```text
stop_current_family
write_p0_6_partition_freeze_requirement
write_p0_6_formula_repair_requirement
write_deferred_family_requirement
```

Decision rules:

```text
Decision scope constraint:
  family rows may use only:
    stop_current_family,
    write_p0_6_partition_freeze_requirement,
    write_p0_6_formula_repair_requirement.
  the overall row may use:
    stop_current_family,
    write_deferred_family_requirement,
    write_p0_6_partition_freeze_requirement,
    write_p0_6_formula_repair_requirement.

write_p0_6_partition_freeze_requirement is allowed if:
  the decision row names exactly one decision-eligible predeclared_partition_id
  from p0_5_diagnostic_bin_freeze.csv,
  the same predeclared partition is interpretable in validation and robustness,
  validation_partition_trigger_rate_per_launch_episode >= 0.20,
  validation_partition_unique_instrument_year_count >= 25,
  validation_partition_mean_diff_vs_matched_delay > 0,
  validation_partition_p05_diff_vs_matched_delay >= -0.003,
  robustness does not collapse for that same predeclared partition,
  and P0.6 will freeze that partition before any P1 validation.

write_p0_6_formula_repair_requirement is allowed if:
  lifecycle_anchor_recall gate is passed in upstream ep3_gate_audit.csv for the family,
  no partition satisfies write_p0_6_partition_freeze_requirement,
  no stop_current_family required condition is true,
  and at least one repair hypothesis for that family is supported:
    h1_formula_too_narrow,
    h2_window_position_problem,
    h3_ep2_reference_pollution.

write_deferred_family_requirement is allowed if:
  decision_scope = overall,
  all family rows have recommended_decision = stop_current_family,
  no primary family has supported h1/h2/h3,
  at least one primary family has upstream lifecycle_anchor_recall gate passed,
  and ep3_winner_lifecycle_profile.csv contains at least one non-empty,
  non-primary anchor_family_id with split = train and distinct
  winner_episode_id count >= diagnostic_bins.event_count_min_for_interpretation.

stop_current_family is required if:
  validation_interpretable_partition_count = 0,
  or robustness_interpretable_partition_count = 0,
  or h4_matched_baseline_too_strong_or_anchor_no_lift is supported for that family,
  or h5_tail_risk_not_trigger_rate_is_core_failure is supported for that family.
```

Family-row decision precedence, where lower rank wins:

```text
1 stop_current_family
2 write_p0_6_formula_repair_requirement
3 write_p0_6_partition_freeze_requirement
```

Overall-row decision rule:

```text
If deferred_family_rule_status = passed, the overall row must use
write_deferred_family_requirement with decision_precedence_rank = 2.

Otherwise, the overall decision must equal the highest-precedence decision
implied by the family-level rows.
```

P0.5 cannot output `write_p1_validation_requirement`. If P0.5 finds strong frozen-partition evidence, the only allowed continuation is `write_p0_6_partition_freeze_requirement`; P1 can be considered only after a separate P0.6 requirement freezes the partition without reusing validation or robustness for selection.

## 12. Validator Requirements

The implementation must add:

```text
ep3/scripts/validate_p0_5_anchor_failure_diagnostic.py
```

The validator must fail on:

- missing required upstream P0 artifacts;
- upstream P0 manifest not `validation_status = passed`;
- missing or failed `p0_5_upstream_authority.csv`;
- upstream manifest hash and live artifact hash mismatch for any frozen P0 input;
- invalid or non-deterministic directory live_content_hash for allowed directory inputs;
- missing `p0_5_trigger_denominator_panel.csv`;
- missing `p0_5_trigger_denominator_reconciliation.csv`;
- duplicate denominator primary key in `p0_5_trigger_denominator_panel.csv`;
- denominator panel not constructed from the canonical first EP2 launch episode row;
- denominator launch-episode count mismatch against `ep3_anchor_trigger_budget_audit.csv.ep2_launch_episode_count`;
- `out_of_scope` rows used in any primary diagnostic report, hypothesis support row, trigger denominator, or stop / continue decision;
- split-level trigger numerator mismatch against `ep3_anchor_trigger_budget_audit.csv.anchor_trigger_count`;
- missing or invalid cross-split trigger-reference accounting in `p0_5_trigger_decomposition.csv`;
- bucket-level trigger decomposition denominator not following the required `denominator_scope` rules;
- missing or invalid `trigger_rate_band` assignment from config-static `trigger_rate_reference_bands`;
- `label_join_status` used as a bucket-level launch-denominator axis;
- `gate_eligible_h20` trigger rate not reproduced from `ep3_anchor_vs_matched_baseline.csv` with `baseline_id = anchor` and `horizon_id = H20`;
- missing or invalid matched-delay pair join for `matched_delay_underperformance_rate`;
- duplicate matched-delay pair for the same `anchor_event_id` not excluded and counted in `matched_delay_pair_exclusion_count`;
- upstream no-go reproduction mismatch;
- P0.5 output written outside `ep3/outputs/p0_5_anchor_failure_diagnostic/`;
- validation / robustness outcomes used to derive bins or partitions;
- any `can_justify_p1 = true` in `p0_5_hypothesis_audit.csv`;
- any P1 candidate / strategy candidate / production signal output;
- any `write_p1_validation_requirement` decision;
- any validation-selected or robustness-selected best bucket / best partition field;
- any stop / continue decision row whose partition fields do not reference a train-frozen, upstream-P0-train-frozen, or config-static predeclared partition;
- copied P0 diagnostic bins without `bin_source_split = upstream_p0_train_frozen`, `bin_method = copied_from_p0`, or matching source artifact hash;
- missing or invalid `anchor_window_position_ratio` formula;
- missing or invalid formula-specific diagnostic fields or bins for primary anchor rows;
- missing or invalid `primary_diagnostic_eligible` or `primary_diagnostic_eligibility_reason` according to the required-date rules;
- missing or invalid `p0_5_lifecycle_forward_translation.csv` independent metric denominator fields;
- missing or invalid family-level `p0_5_hypothesis_audit.csv` row grain or support-rule computation;
- missing or invalid tail metric formulas, MAE-worsening sign, or concentration threshold joins;
- missing or invalid decision-eligible partition counts;
- missing or invalid pairwise `diagnostic_bucket_source`;
- any decision or hypothesis partition evidence using matched-lift rows where
  diagnostic_bucket_source is not linked_anchor;
- duplicate matched-lift or tail-failure report row under the declared row grain;
- missing or invalid `p0_5_sensitivity_horizon_audit.csv`, failed all_sources
  aggregate reproduction against upstream `ep3_sensitivity_horizon_audit.csv`,
  or any sensitivity row with `sensitivity_decision_use_allowed != false`;
- any `diagnostic_bucket_source = all_sources` row outside aggregate
  `p0_5_sensitivity_horizon_audit.csv` reproduction rows;
- any H10/H60 sensitivity metric used in hypothesis support, stop / continue
  decisions, partition selection, or promotion;
- missing or invalid `failed_lookalike_baseline_event_count` or
  `failed_lookalike_rate` formula;
- missing H10/H60 return or MAE fields in required diagnostic cache schemas;
- concentration report row universe or share denominator not following the
  required source-row rules;
- missing or invalid `formula_diagnostic_status` mapping;
- unavailable date-derived diagnostic fields not set to `unavailable` for non-primary or missing-date cache rows;
- any `all_launch_direct_baseline` row decomposed by `anchor_window_position_bucket`, `reference_age_bucket`, formula-specific buckets, `money_bucket`, `vol20_bucket`, or `ret_60d_bucket`;
- any `all_launch_direct_baseline` diagnostic panel row with formula-specific bucket fields not empty or unavailable;
- any `all_launch_direct_baseline` diagnostic panel row with `money_bucket`, `vol20_bucket`, or `ret_60d_bucket` not equal to `unbucketed`;
- any modified EP3-P0 engineering baseline output;
- missing required diagnostic reports;
- missing required report schema fields;
- missing required diagnostic cache fields or primary-key duplicate rows;
- empty `artifact_hash_after_stage`;
- decision rule mismatch in `p0_5_stop_continue_decision.csv`;
- manifest hash mismatch.

## 13. Required Commands

```bash
uv run python ep3/scripts/run_p0_5_anchor_failure_diagnostic.py \
  --config ep3/configs/p0_5_anchor_failure_diagnostic.yaml

uv run python ep3/scripts/validate_p0_5_anchor_failure_diagnostic.py \
  --config ep3/configs/p0_5_anchor_failure_diagnostic.yaml

uv run python -m py_compile \
  ep3/scripts/run_p0_5_anchor_failure_diagnostic.py \
  ep3/scripts/validate_p0_5_anchor_failure_diagnostic.py
```

## 14. Completion Criteria

Implementation success:

```text
validator passes;
all required reports, cache files, and manifest exist;
upstream P0 no-go status is reproduced exactly;
diagnostic bins come only from allowed frozen sources: train, config_static, or
upstream_p0_train_frozen;
no validation or robustness outcome is used to derive bins or partitions;
no P1 candidate is emitted.
```

Research success:

```text
P0.5 produces a clear stop / continue decision:
  either stop A/C,
  write a P0.6 partition-freeze requirement,
  write a narrower P0.6 formula-repair requirement,
  or move to a deferred-family requirement.
```

This requirement is intentionally a diagnostic bridge. It is not a strategy requirement.
