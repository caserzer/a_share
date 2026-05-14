# EP4 Requirement 02.1: Prior Probability Diagnostic For R03 Preparation V1

## 1. Requirement Metadata

- Requirement id: `ep4_r02_1_prior_probability_diagnostic_v1`
- Short name: `r02_1_prior_probability_diagnostic_v1`
- Status: exploratory diagnostic requirement, not experiment
- Owner workflow: EP4
- Upstream discussion: `ep4/discussion3.md`
- Upstream path-analysis requirement: `ep4/requirement_02_family_signal_120d_path_query_v1.md`
- Upstream precision requirement: `ep4/requirement_02_family_precision_forward_return_stats_v1.md`
- Required output root: `ep4/outputs/r02_1_prior_probability_diagnostic_v1/`
- Required config path: `ep4/configs/r02_1_prior_probability_diagnostic_v1.yaml`
- Required runner path: `ep4/scripts/run_r02_1_prior_probability_diagnostic.py`
- Required validator path: `ep4/scripts/validate_r02_1_prior_probability_diagnostic.py`
- Date: 2026-05-14

## 2. Purpose

本需求只做 R03 requirement 之前的先验概率探查。它回答：

```text
在 R02 已冻结的 7 个 family 信号上，
不同 single family、same-day bundle、same-day family count、split / year / context bucket
对应的 good / bad / neutral path 先验比例是多少？

这些先验比例、样本量和 split 稳定性是否足以支撑后续 R03 staged evidence + 1R build-budget requirement？
```

本需求不是 R03 实验，不做 staged build，不做交易策略，不做仓位模拟，不选择最终 candidate set，也不冻结任何 R03 参数。

它的唯一目标是生成 R03 requirement 的输入证据：

```text
prior denominators
posterior diagnostic tables
bundle sparsity audit
fresh-evidence offset distribution
split stability diagnostics
```

如果本需求发现 bundle 样本过稀、split drift 过大、fresh evidence 主要出现在 T+30 之后，后续 R03 requirement 必须据此收窄或重写。

## 3. Hard Scope

允许：

- 使用 R02 已冻结的 7 个 single family 信号；
- 使用 R02 path-analysis 中已定义的 next-open entry 和 120D path metric 口径；
- 在 action-time eligible stock-day / seed episode / signal event 粒度上统计先验比例；
- 计算 mutually exclusive 的 `good_path` / `bad_path` / `neutral_path` 标签；
- 统计 same-day bundle、same-day family count、single family、split、year、context bucket 的 posterior diagnostic；
- 统计 fresh evidence 在 seed 后 T+3..T+30 内的首次出现 offset；
- 输出样本量、coverage、censoring、split stability 和 bucket fallback audit。

禁止：

- 搜索新的技术指标、阈值、窗口或 family；
- 根据本需求输出选择最终 R03 candidate set；
- 根据 validation / robustness 结果调参、合并 bucket 或改变标签定义；
- 训练模型；
- 做 staged build、portfolio simulation、回测或交易执行实验；
- 输出 buy / sell / add / reduce action；
- 生成 1R 风险预算映射表；
- 把任一 prior / posterior 表解释为可交易信号、R03-ready 信号或策略验证结果；
- 使用 big-winner window coverage 作为先验分母；
- 引入新的在线数据抓取。

## 4. Frozen Signal Universe

信号 universe 固定为 R02 path-analysis requirement 的 7 个 single family。每个 family 的公式指标必须逐字冻结：

| family_id | signal_id | condition_group_id | frozen formula / indicators |
|:--|:--|:--|:--|
| `momentum_rps` | `single_momentum_rps` | `momentum_rps__and3__68b32373ce93` | `roc5_r02 >= 0.05 AND rps5_r02 >= 0.8 AND rps10_r02 >= 0.5` |
| `oscillator` | `single_oscillator` | `oscillator__and4__95dbd99ae828` | `kdj_k5_r02 >= 60 AND cci5_r02 >= 100 AND kdj_k10_r02 >= 55 AND cci10_r02 >= 150` |
| `price_trend` | `single_price_trend` | `price_trend__and3__6030760ed19f` | `close_over_ma5_r02 >= 0.03 AND ema_slope5_r02 >= 0.0 AND close_over_ma10_r02 >= 0.03` |
| `pullback_drawdown` | `single_pullback_drawdown` | `pullback_drawdown__and3__11795aa42e45` | `pullback_depth5_r02 >= -0.05 AND rebound_from_low5_r02 >= 0.05 AND days_since_high10_r02 <= 5` |
| `range_breakout` | `single_range_breakout` | `range_breakout__and3__00e51295d9c3` | `range_position5_r02 >= 0.9 AND new_high_flag10_r02 == 1.0 AND range_position10_r02 >= 0.7` |
| `volatility_band` | `single_volatility_band` | `volatility_band__and4__ef9c875dde10` | `boll_pct_b5_r02 >= 0.8 AND boll_width5_r02 >= 1.0 AND boll_width10_r02 >= 1.0 AND price_channel_position10_r02 >= 0.8` |
| `volume_money` | `single_volume_money` | `volume_money__and4__4eb7a99e922f` | `volume_ratio5_r02 >= 1.5 AND money_zscore5_r02 >= 2.0 AND money_price_coherence5_r02 == 1.0 AND money_price_coherence10_r02 == 1.0` |

实现必须从 `ep4/configs/r02_family_signal_120d_path_query_v1.yaml` 或等价 manifest 中读取并校验这些 frozen condition group 和公式指标。

Validator 必须 fail closed：

- 任一 `family_id` / `signal_id` / `condition_group_id` 不等于上表；
- 任一 formula 使用了上表之外的新指标、新阈值或新窗口；
- 任一 formula 与 R02 path-analysis config / manifest 中记录的公式不一致；
- 实现从 review composite 反推、扩展或重写 single family 公式。

4 个 review composite 只允许作为 comparison rows 或 lineage reference，不得作为新的 family 定义来源，也不得扩展组合集合。

## 5. Required Inputs

主输入必须来自本地已有 artifact：

- R02 path-analysis output root: `ep4/outputs/r02_family_signal_120d_path_query_v1/`
- R02 per-signal raw path CSVs: `reports/signals/*_120d_path.csv`
- R02 per-signal episode audit CSVs: `reports/episode_signals/*_episode_audit.csv`
- R02 path-analysis manifest and validation manifest
- R02 family precision background prior panel, if available:
  `ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_background_prior_panel.parquet`
- R02 eligible-day density panel:
  `ep4/outputs/r02_big_winner_coverage_ratio_search_v1/cache/r02_eligible_day_density_panel.parquet`
- Local PIT OHLCV / amount data only if the implementation must compute background action-time path labels not already materialized.

No new online fetch is allowed.

## 6. Analysis Grain

本需求必须输出以下 grain。

### 6.1 Signal Event Grain

```text
instrument_id
trade_date
family_id
signal_id
```

This grain is used for single-family prior diagnostics.

### 6.2 Same-Day Bundle Grain

```text
instrument_id
trade_date
same_day_bundle_key
```

`same_day_bundle_key` is the deterministic sorted set of all frozen family ids triggered on the same `instrument_id, trade_date`.

Example:

```text
momentum_rps|oscillator|volume_money
```

The same-day bundle is one evidence object. It must not be decomposed as independent probabilities.

### 6.3 Same-Day Family Count Grain

```text
instrument_id
trade_date
same_day_family_count
```

`same_day_family_count` is an integer from 0 to 7.

Rows with count 0 are required for global action-time prior if a background action-time denominator is materialized. If count 0 cannot be fully labeled under the same executable path convention, the report must mark global action-time prior as unavailable and explain why.

### 6.4 Seed Episode Grain

Seed episode grain is used only for fresh-evidence offset diagnostics.

```text
seed_episode_id
instrument_id
seed_trade_date
seed_same_day_bundle_key
```

Default episode construction:

```text
seed starts on the first trade_date with any frozen family trigger
episode build window = seed_trade_date + 0 .. seed_trade_date + 30 trading days
new seed for the same instrument is allowed only after the previous build window ends
```

This is an exploratory diagnostic episode, not a trading episode.

### 6.5 Context Bucket Grain

`context_bucket` is required because discussion3's R03 v1 sketch depends on direct posterior tables, not naive LR multiplication.

V1 context buckets must be deterministic and must use only fields observable no later than the diagnostic entry anchor:

```text
split
year
same_day_family_count
same_day_bundle_key
entry_risk_pct_bucket, if EV_R inputs are available at next-open entry time
```

Optional context fields are allowed only when they are already present in local PIT artifacts and are observable on or before `trade_date`:

```text
market_regime_bucket
liquidity_bucket
recent_extension_bucket
```

If optional context fields are unavailable, the runner must not synthesize them from future path outcomes. It must mark:

```text
context_field_status = unavailable_missing_pit_feature
```

Default V1 `context_bucket_id`:

```text
bundle=<same_day_bundle_key>|split=<split>|year=<year>|family_count=<same_day_family_count>|risk=<entry_risk_pct_bucket_or_na>
```

This bucket is a diagnostic grouping key only. It must not be used to tune validation buckets or freeze R03 thresholds.

If `same_day_bundle_key` is removed from a bucket because of sample sparsity, that row is no longer a primary direct-posterior bucket. It must be marked as fallback:

```text
fallback_level in {same_day_family_count, single_family, global_action_time_prior}
```

## 7. Entry And Path Anchor

All labels that require executable path data must reuse R02 path-analysis conventions:

```text
entry_date = first executable next-open date after trade_date
entry_price = next executable open
path horizon = 120 trading days after entry
max gain price = high
max loss price = low
max drawdown policy = prior_peak_only
```

The runner must record whether a label was read from existing R02 path CSVs or computed from PIT OHLCV.

If a row lacks executable next-open entry or enough forward bars, it must not silently enter a prior denominator.

## 8. Mutually Exclusive Path Labels

The primary label is mutually exclusive:

```text
bad_path
good_path
neutral_path
censored_or_invalid
```

The label priority is fixed:

```text
1. if entry invalid or required forward path unavailable:
     label = censored_or_invalid

2. else if bad condition is true:
     label = bad_path

3. else if good condition is true:
     label = good_path

4. else:
     label = neutral_path
```

Headline posterior rates must use only rows where:

```text
label in {bad_path, good_path, neutral_path}
```

and must report:

```text
censored_or_invalid_count
censored_or_invalid_rate
```

### 8.1 Bad Path Definition

Primary v1 bad condition:

```text
early_failure_flag == true
OR first_minus5_offset <= 10
OR max_loss_before_first_plus10 <= -0.06
```

All three fields must use the R02 path-analysis definitions.

### 8.2 Good Path Definition

Primary v1 good condition:

```text
hit_plus10_before_minus5 == true
OR path_quality_flag in {clean_continuation, tradable_continuation}
```

Good is evaluated only after bad priority has been checked. A row that satisfies both bad and good conditions must be labeled `bad_path`.

### 8.3 Neutral Path Definition

`neutral_path` means:

```text
not bad_path
not good_path
not censored_or_invalid
```

Neutral is not a success label. It is the residual path class for ambiguous or insufficiently directional outcomes.

## 9. Required Prior Metrics

For every required grouping, compute:

```text
row_count
label_denominator_count
good_count
bad_count
neutral_count
censored_or_invalid_count
P_good = good_count / label_denominator_count
P_bad = bad_count / label_denominator_count
P_neutral = neutral_count / label_denominator_count
P_good + P_bad + P_neutral
EV_R_diagnostic
sample_sufficiency_status
```

`P_good + P_bad + P_neutral` must equal 1 within numerical tolerance for every row with nonzero label denominator.

### 9.1 EV_R Diagnostic

This requirement is not a trading experiment, but it may compute a descriptive `EV_R_diagnostic` using a fixed R-unit convention.

Default:

```text
initial_stop = closest valid stop below entry among:
  signal_day_low
  prior_10d_low
  prior_20d_low

initial_risk_pct = (entry_price - initial_stop) / entry_price
eligible_R = 0.02 <= initial_risk_pct <= 0.12
terminal_return_pct = close_return_t20
unit_return_R = terminal_return_pct / initial_risk_pct
```

`EV_R_diagnostic` is a short-horizon risk-budget diagnostic using T+20 close return. It must be reported as `EV_R_t20_diagnostic` in output tables if the implementation includes multiple EV horizons. It is not a 120D terminal EV and must not be described as the 120D path payoff.

Rows without valid `initial_risk_pct` stay in count / posterior tables but are excluded from `EV_R_diagnostic` denominator and must be audited.

If required fields are not available, `EV_R_diagnostic` may be omitted only if the manifest records `ev_r_status = unavailable_missing_inputs`.

Required audit output:

```text
reports/r02_1_ev_r_input_audit.csv
```

Required fields:

```text
field_name
required_for_ev_r
source_table_or_file
source_column
availability_status
missing_reason
affected_row_count
usable_row_count
```

Allowed `availability_status`:

```text
available
available_partial
missing
not_required_when_ev_r_disabled
```

If `EV_R_diagnostic` is unavailable, `r02_1_r03_input_readiness.csv` must mark every readiness scope that depends on risk-budget design as:

```text
ev_r_ready = blocked_missing_ev_r
primary_blocker = blocked_missing_ev_r
```

In that case the report must state that this diagnostic is insufficient to launch a risk-budget R03 requirement until EV_R inputs are materialized.

## 10. Required Grouping Tables

### 10.1 Global Action-Time Prior

Output:

```text
reports/r02_1_global_action_time_prior.csv
```

Required rows:

```text
all
split
year
split x year
```

If count-0 background rows cannot be labeled under the same path convention, this table must still exist and explicitly mark:

```text
global_prior_status = unavailable_background_path_not_materialized
```

In that case `r02_1_r03_input_readiness.csv` must mark every scope that depends on action-time background priors as:

```text
global_prior_ready = blocked_missing_denominator
primary_blocker = blocked_missing_denominator
```

If a stricter blocker already applies, `blocked_missing_denominator` may be recorded as `secondary_blocker`, but it must not be omitted.

### 10.2 Single Family Prior

Output:

```text
reports/r02_1_single_family_prior.csv
```

Required grouping:

```text
family_id
signal_id
split
year
```

### 10.3 Same-Day Bundle Prior

Output:

```text
reports/r02_1_same_day_bundle_prior.csv
```

Required grouping:

```text
same_day_bundle_key
same_day_family_count
split
year
```

The table must include:

```text
bundle_family_ids
same_day_family_count
is_review_composite_bundle
review_composite_signal_id_if_any
```

### 10.4 Same-Day Family Count Prior

Output:

```text
reports/r02_1_same_day_family_count_prior.csv
```

Required grouping:

```text
same_day_family_count
split
year
```

This is the primary table for checking whether same-day confluence increases early failure.

### 10.5 Bucket Fallback Audit

Output:

```text
reports/r02_1_bucket_fallback_audit.csv
```

For every posterior bucket, report:

```text
original_bucket_key
original_sample_count
fallback_level
fallback_bucket_key
fallback_sample_count
fallback_reason
```

Allowed fallback levels:

```text
same_day_bundle_key
same_day_family_count
single_family
global_action_time_prior
unusable_too_sparse
```

This audit is descriptive only and must not be used to tune validation buckets.

### 10.6 Context Bucket Prior

Output:

```text
reports/r02_1_context_bucket_prior.csv
```

Required grouping:

```text
context_bucket_id
same_day_bundle_key
split
year
same_day_family_count
entry_risk_pct_bucket
```

Required fields:

```text
context_bucket_definition
context_source_fields
context_field_status
row_count
label_denominator_count
P_good
P_bad
P_neutral
EV_R_diagnostic
sample_sufficiency_status
fallback_level
```

This table is the primary input for deciding whether a future R03 direct-posterior-table design is feasible. It is not a posterior gate and must not contain staged-build actions.

### 10.7 Survival Checkpoint Prior

Output:

```text
reports/r02_1_survival_checkpoint_prior.csv
```

Purpose:

```text
Estimate whether "survival then step-up" already explains most path improvement,
so a future staged posterior design must prove incremental value over baseline_3.
```

Required checkpoints:

```text
T+3
T+5
T+10
```

Default survival definition at checkpoint `k`:

```text
entry_valid == true
available_forward_trading_days >= k
no first_minus5_offset <= k
no first_close_minus5_offset <= k, if first_close_minus5_offset is available
```

Required grouping:

```text
checkpoint
same_day_bundle_key
same_day_family_count
context_bucket_id
split
year
```

Required fields:

```text
checkpoint
survival_definition_version
pre_checkpoint_row_count
survivor_count
survivor_rate
survivor_label_denominator_count
survivor_P_good
survivor_P_bad
survivor_P_neutral
survivor_EV_R_diagnostic
non_survivor_count
non_survivor_label_denominator_count
non_survivor_P_good
non_survivor_P_bad
non_survivor_P_neutral
non_survivor_EV_R_diagnostic
survival_lift_good_vs_pre_checkpoint
survival_lift_bad_vs_pre_checkpoint
sample_sufficiency_status
```

This table is still a prior diagnostic. It must not simulate adding risk after survival.

### 10.8 Fresh Evidence Prior

Output:

```text
reports/r02_1_fresh_evidence_prior.csv
```

Purpose:

```text
Estimate whether fresh evidence after seed changes good / bad / neutral path odds,
not only when fresh evidence appears.
```

Required grouping:

```text
fresh_evidence_status
fresh_family_id
fresh_offset_bucket
seed_same_day_bundle_key
seed_same_day_family_count
seed_pre_fresh_state
survival_checkpoint_state
split
year
```

`seed_label` is the final path label and must not be used as a posterior conditioning key in this table. It may appear only in row-level offset distribution or descriptive cross-tabs. Conditioning on final `seed_label` would make `P_good` / `P_bad` tautological and is forbidden.

Fresh evidence rows must use deterministic sentinels:

```text
fresh_evidence_status = found_within_t3_t30 | none_within_t3_t30 | seed_failed_before_t3 | seed_failed_before_fresh | ambiguous_same_offset | censored_before_t30
fresh_family_id = <family_id> | none | censored
fresh_offset_bucket = T3_T5 | T6_T10 | T11_T20 | T21_T30 | none | censored
```

Rows with `fresh_evidence_status = none_within_t3_t30` must set:

```text
fresh_family_id = none
fresh_offset_bucket = none
seed_pre_fresh_state = no_fresh_observed
```

Rows with `fresh_evidence_status = seed_failed_before_t3` must set:

```text
fresh_family_id = none
fresh_offset_bucket = none
seed_pre_fresh_state = failed_before_t3
```

Rows with `fresh_evidence_status = seed_failed_before_fresh` must set:

```text
fresh_family_id = none
fresh_offset_bucket = none
seed_pre_fresh_state = failed_before_fresh
```

Failure status definitions:

```text
seed_failed_before_t3 =
  the seed breaches the observable failure rule before offset T+3,
  before any eligible fresh evidence can be considered.

seed_failed_before_fresh =
  the seed breaches the observable failure rule at offset >= T+3 and <= T+30,
  before any eligible different-family fresh evidence appears.
```

Rows with `fresh_evidence_status = censored_before_t30` must set:

```text
fresh_family_id = censored
fresh_offset_bucket = censored
seed_pre_fresh_state = censored_before_fresh
```

Rows with `fresh_evidence_status = ambiguous_same_offset` must retain the candidate `fresh_family_id` and `fresh_offset_bucket`, set `seed_pre_fresh_state = ambiguous_same_offset`, and be excluded from posterior denominators.

Status mapping must be one-to-one:

```text
fresh_evidence_status = found_within_t3_t30      -> seed_pre_fresh_state = alive_before_fresh
fresh_evidence_status = none_within_t3_t30       -> seed_pre_fresh_state = no_fresh_observed
fresh_evidence_status = seed_failed_before_t3    -> seed_pre_fresh_state = failed_before_t3
fresh_evidence_status = seed_failed_before_fresh -> seed_pre_fresh_state = failed_before_fresh
fresh_evidence_status = ambiguous_same_offset    -> seed_pre_fresh_state = ambiguous_same_offset
fresh_evidence_status = censored_before_t30      -> seed_pre_fresh_state = censored_before_fresh
```

Allowed `seed_pre_fresh_state`:

```text
alive_before_fresh
failed_before_t3
failed_before_fresh
censored_before_fresh
no_fresh_observed
ambiguous_same_offset
```

Allowed `survival_checkpoint_state`:

```text
survived_t3
survived_t5
survived_t10
not_survived_t3
not_survived_t5
not_survived_t10
censored_before_checkpoint
```

`survival_checkpoint_state` must be resolved as follows:

```text
For found fresh evidence:
  use the latest configured checkpoint in {T+3, T+5, T+10} with checkpoint_offset <= fresh_offset.

For no-fresh rows:
  use the T+10 checkpoint state if the row is observable through T+30.

For seed_failed_before_t3 rows:
  use not_survived_t3.

For seed_failed_before_fresh rows:
  use the earliest configured checkpoint in {T+3, T+5, T+10} with checkpoint_offset >= failure_offset.
  If failure_offset > T+10 and <= T+30, use survived_t10.

For rows censored before T+30:
  use censored_before_checkpoint when the relevant checkpoint cannot be observed.
```

The implementation must not choose the checkpoint after inspecting the final 120D outcome. If a future version needs one row per checkpoint, it must write a separate table; v1 uses exactly one resolved `survival_checkpoint_state` per `fresh_evidence_prior.csv` row.

Default `fresh_offset_bucket`:

```text
T3_T5
T6_T10
T11_T20
T21_T30
none
censored
```

Required fields:

```text
row_count
label_denominator_count
posterior_denominator_policy
P_good
P_bad
P_neutral
EV_R_diagnostic
fresh_before_observable_failure_rate
fresh_without_prior_observable_failure_rate
median_fresh_offset
sample_sufficiency_status
```

Rows with no fresh evidence must remain in this table under `fresh_evidence_status = none_within_t3_t30`. Otherwise the diagnostic would overstate the value of fresh evidence by conditioning only on found cases.

Posterior denominator policy:

| fresh_evidence_status | posterior_denominator_policy | enters `label_denominator_count`? |
|:--|:--|:--|
| `found_within_t3_t30` | `include_labeled` | yes |
| `none_within_t3_t30` | `include_labeled` | yes |
| `seed_failed_before_t3` | `include_labeled` | yes |
| `seed_failed_before_fresh` | `include_labeled` | yes |
| `ambiguous_same_offset` | `audit_only_exclude` | no |
| `censored_before_t30` | `censored_exclude` | no |

Rows excluded by this policy must still contribute to `row_count` and to explicit audit / censoring counts, but must not contribute to `P_good`, `P_bad`, `P_neutral`, or `EV_R_diagnostic`.

`fresh_before_observable_failure_rate` and `fresh_without_prior_observable_failure_rate` must be computed from row-level `fresh_vs_observable_failure_state` using only rows where `fresh_evidence_status = found_within_t3_t30` or `ambiguous_same_offset`. Their denominator is rows with a numeric `fresh_offset`. They must not use final `bad_path`, `good_path`, or any post-fresh 120D outcome.

Row-level `fresh_vs_observable_failure_state` is defined as:

```text
before_observable_failure = fresh_offset is numeric and fresh_offset < observable_failure_offset
after_observable_failure = fresh_offset is numeric and fresh_offset > observable_failure_offset
no_observable_failure = fresh_offset is numeric and observable_failure_offset is none
ambiguous_same_offset = fresh_offset == observable_failure_offset
not_applicable = fresh_offset is none or censored
```

Rate numerators:

```text
fresh_before_observable_failure_rate numerator =
  count(fresh_vs_observable_failure_state == before_observable_failure)

fresh_without_prior_observable_failure_rate numerator =
  count(fresh_vs_observable_failure_state in {before_observable_failure, no_observable_failure})
```

`observable_failure_offset` is the earliest available offset among:

```text
first_minus5_offset
first_close_minus5_offset, if available
configured observable stop breach offset, if stop-breach offsets are available
```

Fresh evidence validity must be determined only from information observable before the candidate fresh evidence date. A seed is considered failed before a candidate fresh offset `f` only if one of the following is true:

```text
first_minus5_offset < f
first_close_minus5_offset < f, if available
configured observable stop breach offset < f, if stop-breach offsets are available
```

Same-offset policy:

```text
If first_minus5_offset == f, first_close_minus5_offset == f, or stop_breach_offset == f,
the row must not be treated as clean alive-before-fresh because daily bars cannot
prove intraday order.

Default classification:
  seed_pre_fresh_state = ambiguous_same_offset
  exclude from fresh-evidence posterior denominator
  include in row_count and audit counts
```

`ambiguous_same_offset` is an audit-only state. It must not contribute to `P_good`, `P_bad`, `P_neutral`, or `EV_R_diagnostic` in `fresh_evidence_prior.csv`.

The implementation must not use final `bad_path`, `good_path`, max drawdown over the full horizon, or any post-fresh outcome to decide whether fresh evidence is valid.

### 10.9 R03 Input Readiness

Output:

```text
reports/r02_1_r03_input_readiness.csv
```

This is a machine-readable bridge from this exploratory diagnostic to the future R03 requirement.

Required fields:

```text
readiness_scope
global_prior_ready
single_family_prior_ready
same_day_bundle_prior_ready
context_bucket_prior_ready
survival_checkpoint_prior_ready
fresh_evidence_prior_ready
ev_r_ready
split_stability_ready
recommended_r03_bucket_grain
recommended_build_window_status
primary_blocker
secondary_blocker
required_next_action
```

Allowed readiness values:

```text
ready
limited_use_coarser_bucket
blocked_missing_denominator
blocked_sparse_bucket
blocked_unstable_split
blocked_missing_ev_r
blocked_missing_fresh_evidence
```

Allowed `recommended_r03_bucket_grain` values:

```text
same_day_bundle_context
same_day_family_count_context
single_family_context
global_prior_only
not_ready
```

Allowed `recommended_build_window_status` values:

```text
build_window_t30_supported
build_window_needs_retest
blocked_missing_fresh_distribution
blocked_missing_survival_prior
not_ready
```

This file must not recommend a trading strategy. It only states whether the next requirement can be written and at what bucket grain.

## 11. Fresh Evidence Offset Diagnostic

Output:

```text
reports/r02_1_fresh_evidence_offset_distribution.csv
```

Fresh evidence v1 definition:

```text
fresh_evidence_after_seed =
  a different family from the seed same-day bundle
  triggers for the first time
  at offset >= 3 trading days
  and offset <= 30 trading days
  while the seed episode has not failed
```

Required fields:

```text
seed_episode_id
instrument_id
seed_trade_date
seed_split
seed_same_day_bundle_key
seed_same_day_family_count
seed_label
fresh_family_id
fresh_signal_date
fresh_offset
seed_failure_offset
seed_failure_offset_bucket
fresh_vs_observable_failure_state
fresh_evidence_status
seed_pre_fresh_state
posterior_denominator_policy
```

Allowed `fresh_evidence_status`:

```text
found_within_t3_t30
none_within_t3_t30
seed_failed_before_t3
seed_failed_before_fresh
ambiguous_same_offset
censored_before_t30
```

The status and sentinel values must be consistent with Section 10.8. `ambiguous_same_offset` rows are retained for audit and offset distribution but must not enter the fresh-evidence posterior denominator.

The offset distribution must retain rows where the seed failed before fresh evidence appeared. Those rows are required to measure whether staged evidence is delayed beyond the early-failure window.

Row-level sentinel policy:

| fresh_evidence_status | fresh_signal_date | fresh_offset | fresh_family_id | fresh_offset_bucket |
|:--|:--|:--|:--|:--|
| `found_within_t3_t30` | actual date | numeric offset | actual family id | bucket from numeric offset |
| `ambiguous_same_offset` | actual date | numeric offset | actual family id | bucket from numeric offset |
| `none_within_t3_t30` | `none` | `none` | `none` | `none` |
| `seed_failed_before_t3` | `none` | `none` | `none` | `none` |
| `seed_failed_before_fresh` | `none` | `none` | `none` | `none` |
| `censored_before_t30` | `censored` | `censored` | `censored` | `censored` |

For failed rows, `seed_failure_offset` must be the first observable failure offset used by Section 10.8. For non-failed rows, use `seed_failure_offset = none`. `seed_failure_offset_bucket` must use deterministic buckets configured in YAML, with a required `none` bucket.

The report must also include grouped distributions by:

```text
seed_label
seed_same_day_family_count
fresh_family_id
split
year
```

## 12. Split Stability Diagnostics

Output:

```text
reports/r02_1_split_stability_diagnostics.csv
```

For each eligible grouping table and bucket:

```text
grouping_type
grouping_key
train_P_good
validation_P_good
robustness_P_good
train_P_bad
validation_P_bad
robustness_P_bad
train_EV_R_diagnostic
validation_EV_R_diagnostic
robustness_EV_R_diagnostic
max_abs_P_good_drift
max_abs_P_bad_drift
stability_status
```

Required `grouping_type` coverage:

```text
single_family_prior
same_day_bundle_prior
same_day_family_count_prior
context_bucket_prior
survival_checkpoint_prior
fresh_evidence_prior
```

If a table is unavailable or only report-only because of missing denominator, the stability output must still include a row with `stability_status = missing_split` or `insufficient_sample` and the relevant blocker in `grouping_key`.

Allowed `stability_status`:

```text
stable_enough_for_requirement_input
unstable_do_not_freeze
insufficient_sample
missing_split
```

This status is advisory for R03 requirement drafting. It is not a promotion gate and must not select a final strategy.

## 13. Sample Sufficiency Rules

Default thresholds:

```text
N_min_bucket = 200
N_min_split_bucket = 80
N_min_ev_r = 80
```

Allowed `sample_sufficiency_status`:

```text
sufficient
thin_bucket_report_only
too_sparse_use_fallback
unusable
```

All thresholds must be configured in YAML and recorded in the manifest.

## 14. Required Report

Output:

```text
reports/r02_1_prior_probability_diagnostic_report.md
```

The report must be concise and must cover:

1. whether global action-time prior was available under the same path label convention;
2. single family prior ranking by `P_bad`, `P_good`, and `EV_R_diagnostic`;
3. same-day bundle sparsity and which buckets fall back;
4. same-day family count vs `P_bad` and `P_good`;
5. context bucket posterior availability and whether optional context fields were unavailable;
6. survival checkpoint prior and whether baseline_3 is likely to be a strong control;
7. fresh evidence offset distribution and fresh evidence posterior;
8. whether T+30 is empirically plausible;
9. split stability issues;
10. machine-readable R03 input readiness and whether R03 staged build requirement can be drafted as direct posterior-table v1, or whether bucket sparsity requires a coarser design.

The report must explicitly state:

```text
This is an exploratory prior diagnostic, not an entry strategy, not a staged-build experiment, and not R03 validation.
```

## 15. Required Manifest

Output:

```text
manifests/r02_1_prior_probability_diagnostic_manifest.json
```

Required manifest fields:

```text
phase
requirement_path
config_path
config_hash
output_root
upstream_path_query_manifest_path
upstream_path_query_manifest_hash
upstream_precision_manifest_path
upstream_precision_manifest_hash
frozen_family_ids
label_definition_version
label_priority_order
entry_anchor
path_metric_source
sample_sufficiency_thresholds
global_action_time_prior_status
ev_r_status
ev_r_input_audit_path
context_bucket_status
survival_checkpoint_status
fresh_evidence_prior_status
r03_input_readiness_path
row_counts_by_table
validation_status
artifact_hash
```

## 16. Validation Requirements

Validator must fail closed if:

- any required output file is missing;
- frozen family ids differ from Section 4;
- label classes are not mutually exclusive;
- any posterior table row has `P_good + P_bad + P_neutral != 1` beyond tolerance when denominator > 0;
- `censored_or_invalid` rows enter headline posterior denominators;
- validation / robustness data is used to alter bucket definitions or label rules;
- same-day bundle key ordering is nondeterministic;
- context bucket ids are nondeterministic or use future path outcome fields;
- a primary context posterior row omits `same_day_bundle_key` without being marked as fallback;
- fresh evidence includes a family already present in the seed same-day bundle;
- rows with `fresh_evidence_status in {found_within_t3_t30, ambiguous_same_offset}` have non-numeric `fresh_offset` or `fresh_offset < 3` or `fresh_offset > 30`;
- rows with `fresh_evidence_status in {none_within_t3_t30, seed_failed_before_t3, seed_failed_before_fresh}` do not use `fresh_signal_date = none` and `fresh_offset = none`;
- rows with `fresh_evidence_status = censored_before_t30` do not use `fresh_signal_date = censored` and `fresh_offset = censored`;
- no-fresh rows do not use `fresh_family_id = none` and `fresh_offset_bucket = none`;
- seed-failed rows do not use `fresh_family_id = none`, `fresh_offset_bucket = none`, and the matching failed `seed_pre_fresh_state`;
- seed-failed rows in `r02_1_fresh_evidence_offset_distribution.csv` omit `seed_failure_offset`;
- censored fresh-evidence rows do not use `fresh_family_id = censored` and `fresh_offset_bucket = censored`;
- outputs contain the deprecated field name `fresh_before_bad_path_flag`, `fresh_before_bad_path_rate`, or `fresh_before_observable_failure_flag`;
- `fresh_vs_observable_failure_state`, `fresh_before_observable_failure_rate`, or `fresh_without_prior_observable_failure_rate` uses final path labels instead of observable failure offsets;
- `fresh_vs_observable_failure_state = no_observable_failure` is collapsed into `after_observable_failure` or otherwise counted as a false fresh-before-failure row;
- `fresh_evidence_prior.csv` uses final `seed_label` as a posterior grouping key;
- `fresh_evidence_prior.csv` omits `posterior_denominator_policy` or includes excluded status rows in `label_denominator_count`;
- fresh evidence validity uses final `bad_path`, `good_path`, max drawdown over the full horizon, or any post-fresh outcome;
- same-offset failure / fresh evidence rows enter fresh-evidence posterior denominators instead of `ambiguous_same_offset` audit handling;
- `fresh_evidence_prior.csv` has more than one resolved `survival_checkpoint_state` per grouping row or uses a checkpoint selected from final 120D outcome;
- required survival checkpoint rows are missing for T+3, T+5, or T+10;
- survival checkpoint rows omit non-survivor count, denominator, neutral rate, or EV_R fields;
- `fresh_evidence_prior.csv` omits rows with no fresh evidence;
- `r02_1_ev_r_input_audit.csv` is missing or omits required EV_R fields and availability statuses;
- global action-time prior is unavailable but `r02_1_r03_input_readiness.csv` does not mark `blocked_missing_denominator`;
- `r02_1_r03_input_readiness.csv` is missing or contains values outside the allowed readiness enum;
- `recommended_r03_bucket_grain` or `recommended_build_window_status` contains values outside the allowed enum;
- `EV_R_diagnostic` is unavailable but `r02_1_r03_input_readiness.csv` does not mark `blocked_missing_ev_r`;
- output report uses language implying entry strategy, R03 validation, production signal, or trading recommendation;
- manifest does not record upstream hashes and label definition version.

## 17. Non-Goals

This requirement must not answer:

```text
应该买哪只股票？
应该什么时候加仓？
1R 应该如何最终分配？
哪个 family 是最终 R03 candidate？
staged build 是否优于 full entry？
```

Those questions belong to a future R03 staged evidence risk-budget requirement, if this prior diagnostic shows enough denominator quality and split stability to justify it.
