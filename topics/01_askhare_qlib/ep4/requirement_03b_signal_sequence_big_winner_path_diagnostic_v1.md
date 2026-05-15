# EP4 需求 03b: 信号序列 Big-Winner 与路径诊断 V1

## 1. 需求元信息

- 需求 id: `ep4_r03b_signal_sequence_big_winner_path_diagnostic_v1`
- 简称: `r03b_signal_sequence_big_winner_path_diagnostic_v1`
- 状态: 可实现的诊断型需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion3.md`
- 上游修正版报告: `ep4/outputs/r03a_probability_survival_step_feasibility_v1/reports/r03a_probability_survival_step_feasibility_report.md`
- 上游 path-query 需求: `ep4/requirement_02_family_signal_120d_path_query_v1.md`
- 上游 precision 需求: `ep4/requirement_02_family_precision_forward_return_stats_v1.md`
- 必需输出根目录: `ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/`
- 必需 config 路径: `ep4/configs/r03b_signal_sequence_big_winner_path_diagnostic_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r03b_signal_sequence_big_winner_path_diagnostic.py`
- 必需 validator 路径: `ep4/scripts/validate_r03b_signal_sequence_big_winner_path_diagnostic.py`
- 日期: 2026-05-15

## 2. 实验目的

R03a 已经说明：把 `P_good / P_bad` 当成 `big winner` 的替代指标，会导致错误结论。R03b 不再继续回答 probability-bucket / survival-step feasibility 问题，而是收缩成一个更基础的信号序列诊断：

```text
一个 seed signal 出现之后，
如果后续不同 family 的 signal 逐个出现，
在相同的可观察 survival 状态下，
下面三类概率是否发生变化？

1. future big winner
2. good_path
3. bad_path
```

本需求是信号序列 / 到达概率诊断，不是 risk-budget 实验，也不是生产候选信号搜索。

本实验必须回答：

1. `fresh_distinct_family_count` 增加后，`big_winner_forward_h120` rate 是否提高？
2. 同一个序列状态下，`P_good` 是否提高，`P_bad` 是否下降？
3. 这些变化在控制 `survived_t3`、`survived_t5`、`survived_t10`、`survived_t20`、`survived_t30` 后是否仍然存在？
4. 表面改善是否只是 survivor bias：弱 episode 先失败，所以没有机会等到后续信号？
5. 哪些序列 pattern 有足够分母，值得后续单独研究？

## 3. 实验边界

允许：

- 从 R02 frozen family signal 120D path-query 输出重建 seed episode panel。
- 为每个 seed episode 重建 seed 之后的有序 family-signal 时间线。
- 用 close-anchor primary label 和 next-open compatibility label 统计 `big_winner_forward_h120`。
- 把 canonical R01/R02 reference-event overlap 作为 audit-only label 输出。
- 复用 R02 path labels：`good_path`、`bad_path`、`neutral_path`、`censored_or_invalid`，但只能作为 secondary outcome。
- 所有 sequence metric 必须按当时可观察的 survival state 分层。
- 必须保留 no-fresh rows、fresh 出现前已失败 rows、censored rows，并分别进入明确的分母 / audit bucket。
- 必须分别输出 train、validation、robustness 和 all-split 描述性表。
- 必须输出 sequence pattern、fresh-count、kth-fresh、per-offset hazard 诊断。

禁止：

- 不得从 validation / robustness outcome 中选择生产候选、gate、threshold、family subset 或 sequence pattern。
- 不得用 `P_good / P_bad` 替代 big-winner precision。
- 不得推导 1R sizing、position size、add/reduce action 或 portfolio allocation。
- 不得使用 future label、big-winner reference event 或 120D path outcome 来判断 fresh signal 是否有效。
- 不得从分母中删除 no-fresh rows。
- 不得只在 fresh evidence 已出现的样本上做条件统计。
- 不得用 first-fresh offset distribution 证明 T+11..T+30 的后段 fresh signal 无效。
- 不得对同一 post-seed 日期出现的多个 family 强行施加任意顺序。
- Primary sequence count 中不得把 same-family repeated trigger 计为新的 distinct-family fresh evidence。
- 不得把 review composite signals 当成独立 fresh-family evidence，除非后续需求显式启用。
- 不得在线抓取数据。

## 4. 必需输入产物

所有输入必须来自本地 artifact。

R02 path-query 主输入：

```text
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_manifest.json
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_validation.json
ep4/outputs/r02_family_signal_120d_path_query_v1/reports/signals/*_120d_path.csv
```

runner 默认只能加载下面 7 个 frozen single-family signal 输出。除非 config 显式列出允许的 signal id，否则不得加载其它 signal：

```text
single_momentum_rps
single_oscillator
single_price_trend
single_pullback_drawdown
single_range_breakout
single_volatility_band
single_volume_money
```

Big-winner / calendar 输入：

```text
ep4/outputs/r02_big_winner_coverage_ratio_search_v1/manifests/r02_big_winner_coverage_manifest.json
ep4/outputs/r02_big_winner_coverage_ratio_search_v1/cache/r02_big_winner_reference_events.parquet
ep4/outputs/r02_big_winner_coverage_ratio_search_v1/cache/r02_eligible_day_density_panel.parquet
```

Close-anchor precision 权威输入：

```text
ep4/outputs/r02_family_precision_forward_return_stats_v1/manifests/r02_family_precision_forward_return_stats_manifest.json
ep4/outputs/r02_family_precision_forward_return_stats_v1/manifests/r02_family_precision_forward_return_stats_validation.json
ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet
```

`r02_family_action_time_panel.parquet` 是 close-anchor / next-open h120 big-winner labels 的权威来源。如果 precision panel 可用，R03b 不得从 path-query CSV 临时重建 close-anchor label。

runner 必须读取并校验所有必需 manifest / validation JSON：

```text
r02_family_signal_120d_path_query_validation.json.validation_status == passed
r02_family_precision_forward_return_stats_validation.json.validation_status == passed
r02_big_winner_coverage_manifest.json exists and is readable
r02_big_winner_reference_events.parquet exists and is readable
r02_eligible_day_density_panel.parquet exists and is readable
```

如果任一必需 validation 未通过或缺失，runner 不得继续构造 sequence panel，最终 decision 必须为 `blocked_upstream_validation_failed` 或 `blocked_missing_required_input`。

可选 lineage 输入：

```text
ep4/outputs/r03a_probability_survival_step_feasibility_v1/cache/r03a_episode_first_trigger_panel.parquet
ep4/outputs/r03a_probability_survival_step_feasibility_v1/reports/r03a_probability_survival_step_feasibility_report.md
```

可选 lineage 输入只能用于 reconciliation。它们不是 sequence 构造或 big-winner label 的权威来源。

## 5. 输出目录结构

runner 必须写出：

```text
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/
  cache/
    r03b_seed_episode_panel.parquet
    r03b_signal_timeline_panel.parquet
    r03b_sequence_step_panel.parquet
    r03b_checkpoint_state_panel.parquet
    r03b_offset_hazard_panel.parquet
  reports/
    r03b_input_readiness_audit.csv
    r03b_input_reconciliation_audit.csv
    r03b_seed_episode_label_summary.csv
    r03b_checkpoint_fresh_count_summary.csv
    r03b_kth_fresh_summary.csv
    r03b_sequence_pattern_summary.csv
    r03b_offset_hazard_summary.csv
    r03b_survival_bias_audit.csv
    r03b_same_offset_multi_family_audit.csv
    r03b_same_family_repeat_audit.csv
    r03b_big_winner_label_audit.csv
    r03b_sequence_big_winner_path_final_report.md
    r03b_signal_sequence_big_winner_path_validation_audit.csv
  manifests/
    r03b_signal_sequence_big_winner_path_manifest.json
    r03b_signal_sequence_big_winner_path_validation.json
```

## 6. Seed Episode 构造

Seed episode 的粒度固定为 deterministic episode-first-trigger。

R03b 使用两个上游权威：

- R02 path-query signal CSVs 是 path labels 和 seed path fields 的权威来源。
- R02 family precision action-time panel 是 close-anchor / next-open big-winner labels 与 action-time signal occurrence reconciliation 的权威来源。

R02 path-query signal CSVs 不包含 `condition_group_id`。runner 必须先从 precision action-time panel 构造 frozen single-family condition dictionary：

```text
family_id -> condition_group_id
```

该映射必须满足：

```text
每个 frozen family_id 只有一个 condition_group_id
condition_group_id 在 precision panel 中存在
signal_occurs 至少出现一次
```

如果任一 frozen family 找不到唯一 condition-group 映射，runner 必须 fail closed。

runner 对 path-query rows 必须派生：

```text
condition_group_id = frozen_condition_dictionary[family_id]
```

之后再按下面字段对齐两套来源：

```text
instrument_id
signal_date = trade_date
family_id
condition_group_id
```

precision panel 侧只允许使用：

```text
signal_occurs = true
```

如果某个 signal occurrence 只存在于一套权威来源中，runner 必须保留到 input reconciliation audit，并 fail closed。此时不得生成 headline sequence denominators，最终 decision 必须为 `blocked_input_reconciliation_failed`。

输入 signal rows 必须包含：

```text
signal_id
family_id
instrument_id
signal_date
split
entry_date
entry_price
entry_valid
path_complete_120d
available_forward_trading_days
first_minus5_offset
first_close_minus5_offset, if available
hit_plus10_before_minus5
max_loss_before_first_plus10
max_gain_120d
max_drawdown_120d
close_return_t20
close_return_t60
close_return_t120
path_quality_flag
early_failure_flag
```

`condition_group_id` 是 runner 派生字段，不是 path CSV 原始必需字段。`r03b_input_reconciliation_audit.csv` 必须至少报告：

```text
family_id
condition_group_id
path_signal_count
precision_signal_occurs_count
matched_signal_count
path_only_count
precision_only_count
reconciliation_status
```

完成 frozen signal 过滤、condition-group 派生、input reconciliation 之后，同一 `instrument_id`、同一 `signal_date` 上的不同 family signals 才能组成一个 same-day signal event：

```text
same_day_family_set = sorted distinct family_id values
same_day_family_count = count(same_day_family_set)
same_day_bundle_key = "|".join(same_day_family_set)
```

Seed episode 规则：

```text
for each instrument_id 按 signal_date 排序:
  在不属于 active seed build window 的第一个 same-day signal event 创建 seed
  seed_trade_date = same-day signal date
  seed_family_set = same_day_family_set
  seed_same_day_family_count = same_day_family_count
  seed_same_day_bundle_key = same_day_bundle_key
  seed_row_for_scalar_fields = same-day rows 按 family_id、signal_id 排序后的第一行
  seed_entry_date = seed_row_for_scalar_fields 的 entry_date
  seed_entry_price = seed_row_for_scalar_fields 的 entry_price
  active build window = seed_trade_date through seed_trade_date + 30 个交易日
```

`seed_episode_id` 必须确定性生成：

```text
seed_episode_id = sha1_hex(
  instrument_id + "|" + YYYY-MM-DD(seed_trade_date) + "|" + seed_same_day_bundle_key
)[:16]
```

如果 seed date 上多个 family rows 的下面字段不一致，runner 必须 fail closed：

```text
entry_date
entry_price
split
entry_valid
path_complete_120d
available_forward_trading_days
first_minus5_offset
first_close_minus5_offset
hit_plus10_before_minus5
max_loss_before_first_plus10
max_gain_120d
max_drawdown_120d
close_return_t20
close_return_t60
close_return_t120
path_quality_flag
early_failure_flag
```

这些字段不得用于决定 seed membership 或 sequence membership；只能在 seed event 已经由 `instrument_id + signal_date` 确定之后，用于 fail-closed consistency audit。

Active build window 内的新 seed 是禁止的。它们必须被归入当前 seed 的 timeline signals，或者按第 7 节作为 same-family repeats 忽略。

## 7. Seed 之后的信号时间线

对每个 seed episode，重建 post-seed signals：

```text
sequence_window_start = seed_trade_date + 1 trading day
sequence_window_end = seed_trade_date + 30 trading days
```

Primary fresh evidence window：

```text
fresh_offset >= 3 trading days
fresh_offset <= 30 trading days
```

`T+1` 和 `T+2` 出现的后续 family signals 必须保留在 timeline 中，`step_status = outside_primary_fresh_window`。它们不得进入 primary fresh counts、checkpoint fresh-count buckets 或 kth-fresh summaries。

runner 必须生成 `r03b_signal_timeline_panel.parquet`，粒度为：

```text
seed_episode_id
instrument_id
signal_date
offset_from_seed
family_id
signal_id
condition_group_id
```

runner 必须生成 `r03b_sequence_step_panel.parquet`，粒度为：

```text
seed_episode_id
sequence_step_index
step_signal_date
step_offset
added_family_set
added_family_count
cumulative_distinct_family_set
cumulative_distinct_family_count
is_same_offset_multi_family_step
step_status
```

允许的 `step_status`：

```text
seed_same_day
fresh_distinct_family_step
same_family_repeat_audit_only
same_offset_multi_family_step
outside_primary_fresh_window
after_observable_failure
censored_before_step
ambiguous_same_offset
```

规则：

- 已经在 `seed_family_set` 中出现过的 family，不计入新的 distinct-family fresh evidence。
- Same-family repeated triggers 必须保留到 `r03b_same_family_repeat_audit.csv`，但不得进入 primary fresh counts。
- 同一 post-seed date 上出现多个新 family 时，只形成一个 `sequence_step_index`，并记录 `added_family_count > 1`。
- 如果该 same-offset step 落在 primary fresh evidence window 内且发生在 observable failure 之前，它仍然是 primary fresh step；它一次性增加多个 `cumulative_distinct_family_count`，但不得拆成多个有顺序的 family step。
- 实现不得在 `added_family_set` 内施加任意顺序。
- Observable failure 之后出现的 signals 保留到 timeline audit，但不得进入 clean pre-failure fresh 分母。
- 如果 fresh signal 的 `step_offset` 等于 `observable_failure_offset`，runner 不得假设日内先后顺序；该 step 必须标记为 `ambiguous_same_offset`，不得进入 clean pre-failure fresh counts、checkpoint fresh-count buckets 或 kth-fresh summaries。

## 8. Observable Failure 与 Survival State

Observable failure 必须先于 sequence outcome measurement 计算。

Primary observable failure offset：

```text
observable_failure_offset =
  min(
    first_minus5_offset,
    first_close_minus5_offset if available
  )
```

如果两个字段都不可用，则使用 `none`。

Checkpoint grid：

```text
checkpoints = {T+3, T+5, T+10, T+20, T+30}
```

对每个 seed 和 checkpoint，写出 `r03b_checkpoint_state_panel.parquet`：

```text
seed_episode_id
checkpoint
checkpoint_offset
checkpoint_state
fresh_distinct_family_count_before_or_at_checkpoint
fresh_distinct_family_count_bucket
cumulative_distinct_family_count_before_or_at_checkpoint
kth_fresh_reached_before_or_at_checkpoint
fresh_family_sequence_before_or_at_checkpoint
failed_before_checkpoint
censored_before_checkpoint
at_risk_at_checkpoint
```

允许的 `checkpoint_state`：

```text
survived_no_fresh
survived_with_fresh
failed_before_checkpoint
censored_before_checkpoint
ambiguous_same_offset
```

`at_risk_at_checkpoint = true` 的条件：

```text
entry is valid
available forward path is complete through checkpoint
observable_failure_offset is none or observable_failure_offset > checkpoint_offset
```

Checkpoint 前已经 failure 的 rows 必须保留在 checkpoint panel 中。它们不进入 clean survivor-conditioned posterior denominator，但必须进入 survival-bias audits。

Checkpoint 的 fresh count 只统计 primary fresh evidence window 内、且 checkpoint 前可观察的 distinct-family evidence：

```text
3 <= fresh_offset <= checkpoint_offset
fresh signal happens before observable_failure_offset, if failure exists
fresh_offset != observable_failure_offset
```

`T+1/T+2` signals、observable failure 之后的 signals、与 observable failure 同 offset 的 ambiguous signals、same-family repeats 都不得进入 `fresh_distinct_family_count_before_or_at_checkpoint`。

## 9. Outcome Label 定义

R03b 必须分开报告 big-winner outcomes 和 path outcomes。

### 9.1 主 Big-Winner Label

主 big-winner label 使用 family precision requirement 中的 close-anchor statistical definition。字段值必须从 `r02_family_action_time_panel.parquet` 按 `(instrument_id, seed_trade_date)` 读取。读取时优先使用 seed 当日对应 seed family rows，且这些 rows 必须满足 `signal_occurs = true`：

```text
seed_close_price = close(instrument_id, seed_trade_date)
forward_close_peak_h120 =
  max(close over seed_trade_date + 1 through seed_trade_date + 120 trading days)

big_winner_forward_h120_close_anchor =
  forward_close_peak_h120 / seed_close_price - 1 >= 0.50
```

这是 post-close 统计 label，不得描述成 intraday 可执行入场 precision。

必需字段：

```text
complete_h120_close_anchor_flag
forward_close_peak_h120_return_from_seed_close
big_winner_forward_h120_close_anchor
```

映射规则：

```text
complete_h120_close_anchor_flag = complete_h120_flag
forward_close_peak_h120_return_from_seed_close = forward_close_peak_h120_return_from_close
big_winner_forward_h120_close_anchor = big_winner_forward_from_signal_close
```

如果同一个 `(instrument_id, seed_trade_date)` 下存在多个 seed condition-group rows，则这三个 close-anchor fields 必须完全一致。如果不一致，runner 必须 fail closed，因为 big-winner label 已经不再是 row-independent action-time outcome。

### 9.2 Next-Open 兼容 Big-Winner Label

runner 还必须从同一个 precision panel 输出 next-open 兼容 label：

```text
forward_close_peak_h120_return_from_seed_next_open =
  max(close over 120 trading days after seed_entry_date) / seed_entry_price - 1

big_winner_forward_h120_next_open_anchor =
  forward_close_peak_h120_return_from_seed_next_open >= 0.50
```

这是 executable-timing 兼容视图。除非最终报告明确把它作为 secondary table，否则只能 audit-only。

映射规则：

```text
forward_close_peak_h120_return_from_seed_next_open =
  forward_close_peak_h120_return_from_next_open
big_winner_forward_h120_next_open_anchor =
  big_winner_forward_from_next_open
```

### 9.3 Canonical Reference Event Audit

为了和 R02 coverage search 保持连续性，报告 canonical reference overlap：

```text
canonical_ref_after_seed_within_30td =
  same instrument has canonical reference_date in [seed_trade_date, seed_trade_date + 30 trading days]

canonical_ref_after_seed_within_120td =
  same instrument has canonical reference_date in [seed_trade_date, seed_trade_date + 120 trading days]

seed_inside_canonical_ref_t0_t30_window =
  same instrument has canonical reference_date <= seed_trade_date <= profile_window_end
```

这些都是 audit labels。它们不得替代 primary close-anchor `big_winner_forward_h120_close_anchor` label。

### 9.4 Path Labels

Path labels 必须单独保留：

```text
bad_path
good_path
neutral_path
censored_or_invalid
```

R03b 继承 R03a / R02.1 的 label 优先级：

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

`bad_path` 固定条件：

```text
early_failure_flag == true
OR first_minus5_offset <= 10
OR max_loss_before_first_plus10 <= -0.06
```

`good_path` 固定条件：

```text
hit_plus10_before_minus5 == true
OR path_quality_flag in {clean_continuation, tradable_continuation}
```

如果同一样本同时满足 bad 和 good，必须按优先级标记为 `bad_path`。

最终报告必须明确写出：

```text
P_good / P_bad 是 path-label 概率。
它们不是 P(big winner | signal)。
```

## 10. 核心分母定义

R03b 有四组 denominator。它们不得混用。

### 10.1 Seed Denominator

所有 deterministic seed episodes：

```text
seed_episode_denominator
```

用于初始样本、no-fresh rate、failed-before-fresh rate。

### 10.2 Big-Winner Label Denominator

只包含 close-anchor h120 forward window 完整的 seeds：

```text
big_winner_label_denominator =
  count(seed episodes where complete_h120_close_anchor_flag = true)
```

用于 `big_winner_rate_close_anchor`。

### 10.3 Path Label Denominator

只包含：

```text
{good_path, bad_path, neutral_path}
```

用于：

```text
P_good
P_bad
P_neutral
```

### 10.4 Survivor-Conditioned Sequence Denominator

用于 checkpoint-conditioned comparisons：

```text
checkpoint_sequence_denominator =
  count(seed episodes where at_risk_at_checkpoint = true)
```

Checkpoint 前已经 failure 的 rows 必须进入 survival-bias audits，不得静默消失。

## 11. 必需指标

下面规则适用于 outcome posterior summary tables，包括：

```text
r03b_seed_episode_label_summary.csv
r03b_checkpoint_fresh_count_summary.csv
r03b_kth_fresh_summary.csv
r03b_sequence_pattern_summary.csv
```

这些表都必须报告：

```text
split
year, when applicable
conditioning_state
conditioning_key, e.g. fresh_count_bucket / kth_fresh_step_index / sequence_pattern
seed_episode_count
big_winner_label_denominator
big_winner_count_close_anchor
big_winner_rate_close_anchor
big_winner_rate_close_anchor_lower
big_winner_rate_close_anchor_upper
path_label_denominator
good_count
bad_count
neutral_count
P_good
P_bad
P_neutral
P_good_lower
P_good_upper
P_bad_lower
P_bad_upper
censored_or_invalid_count
failed_before_condition_count
sample_sufficiency_status
```

`r03b_offset_hazard_summary.csv` 只衡量 signal arrival hazard，不属于 outcome posterior summary table，不要求报告 `big_winner_rate_close_anchor` 或 `P_good / P_bad`。

可信区间默认沿用 R03a 的 posterior convention，除非 config 显式修改：

```text
alpha_source = Jeffreys_prior
ci = 90%
```

允许的 `sample_sufficiency_status`：

```text
sufficient
thin_report_only
too_sparse_report_only
unusable
```

默认阈值：

```text
N_min_sufficient = 200
N_min_thin = 50
N_min_too_sparse = 10
```

这些阈值只是 report labels，不能用于选择 production gate。

## 12. 必需诊断表

### 12.0 Input Readiness Audit

`reports/r03b_input_readiness_audit.csv`

必需字段：

```text
artifact_role
artifact_path
exists
validation_status
row_count, when applicable
readiness_status
failure_reason
```

这个 audit 必须覆盖所有必需输入，以及实际加载的 7 个 frozen single-family path CSVs。

### 12.1 Seed Episode Label Summary

`reports/r03b_seed_episode_label_summary.csv`

粒度：

```text
split
```

必需字段：

```text
seed_episode_count
conditioning_state
conditioning_key
big_winner_label_denominator
big_winner_count_close_anchor
big_winner_rate_close_anchor
big_winner_rate_close_anchor_lower
big_winner_rate_close_anchor_upper
path_label_denominator
good_count
bad_count
neutral_count
P_good
P_bad
P_neutral
P_good_lower
P_good_upper
P_bad_lower
P_bad_upper
censored_or_invalid_count
no_fresh_episode_count
fresh_episode_count
failed_before_first_primary_fresh_count
failed_before_condition_count
sample_sufficiency_status
```

这个表只给出 seed-level base rate。它不得按 fresh evidence 过滤样本。

Seed base row 固定使用：

```text
conditioning_state = seed_base
conditioning_key = seed_base
failed_before_condition_count = 0
```

其中：

```text
fresh_episode_count =
  seed episodes with at least one clean primary fresh step before observable failure

no_fresh_episode_count =
  seed episodes with zero clean primary fresh steps before observable failure

failed_before_first_primary_fresh_count =
  seed episodes where observable failure happens before the first clean primary fresh step,
  including no-clean-primary-fresh episodes only when observable failure exists
```

### 12.2 Checkpoint Fresh-Count Summary

`reports/r03b_checkpoint_fresh_count_summary.csv`

粒度：

```text
split
checkpoint
fresh_distinct_family_count_bucket
```

必需 fresh count buckets：

```text
0
1
2
3plus
```

这个表回答：

```text
在同一个 observable checkpoint 下，
post-seed distinct-family signals 更多时，
big_winner_rate、P_good、P_bad 是否变化？
```

比较必须在同一个 checkpoint 内进行。例如，`T+10 fresh_count=2` 可以和 `T+10 fresh_count=0` 比较，但不能和 unconditioned T0 比较。

### 12.3 Kth Fresh Step Summary

`reports/r03b_kth_fresh_summary.csv`

粒度：

```text
split
kth_fresh_step_index
kth_fresh_status
kth_fresh_offset_bucket
kth_fresh_added_family_key
kth_fresh_added_family_count
pre_kth_step_survival_state
```

必需 `kth_fresh_step_index`：

```text
1
2
3
4plus
```

这个表回答：

```text
第 1 / 第 2 / 第 3 个 primary fresh step 是否携带不同信息？
```

如果同一个 offset 出现多个新 family，必须作为一个 `kth_fresh_step` 处理：

```text
kth_fresh_added_family_key = sorted added_family_set joined by "|"
kth_fresh_added_family_count = len(added_family_set)
```

不得把 same-offset multi-family step 拆成有顺序的第 1 / 第 2 个 family。

没有达到 kth fresh step 的 rows 必须保留为：

```text
kth_fresh_status = not_reached
kth_fresh_offset_bucket = not_reached
kth_fresh_added_family_key = not_reached
kth_fresh_added_family_count = 0
```

### 12.4 Sequence Pattern Summary

`reports/r03b_sequence_pattern_summary.csv`

粒度：

```text
split
sequence_pattern
sequence_pattern_truncated
sequence_depth
checkpoint
```

`sequence_pattern` 必须是 checkpoint-observable pattern：

```text
only include primary fresh steps where step_offset <= checkpoint_offset
only include steps before observable_failure_offset, if failure exists
```

不得在 `T+3/T+5/T+10/T+20` 的 pattern row 中使用 checkpoint 之后才出现的 T+30 内 signals。完整 T+30 pattern 只能在 `checkpoint = T+30` 或 audit-only full-window 字段中报告。

Pattern 示例：

```text
seed_only
seed:momentum_rps -> fresh:volume_money
seed:multi_family_bundle -> fresh:price_trend
seed:range_breakout -> fresh:volume_money -> fresh:momentum_rps
```

如果 unique patterns 过多，runner 必须：

```text
keep top_k_patterns_by_denominator = 50
collapse the rest into other_sparse_patterns
```

Collapse 必须在读取 outcome metrics 之前发生。

### 12.5 Offset Hazard Summary

`reports/r03b_offset_hazard_summary.csv`

粒度：

```text
split
offset
fresh_family_id
kth_fresh_step_index
```

必需字段：

```text
at_risk_episode_count
fresh_event_count
fresh_hazard_rate
failed_before_offset_count
censored_before_offset_count
```

这个表只衡量 signal arrival hazard。不得使用最终 big-winner 或 path labels。

### 12.6 Survival Bias Audit

`reports/r03b_survival_bias_audit.csv`

必需比较：

```text
failed_before_t3
failed_t3_to_t5
failed_t6_to_t10
failed_t11_to_t20
failed_t21_to_t30
survived_t30_no_fresh
survived_t30_with_fresh
```

该 audit 必须说明：有多少 episode 因为先失败，所以根本没有机会累积后续 signals。

### 12.7 Audit-Only Tables

`reports/r03b_same_offset_multi_family_audit.csv` 必须至少包含：

```text
split
seed_episode_id
instrument_id
step_signal_date
step_offset
added_family_set
added_family_count
step_status
included_in_primary_fresh_count
```

`reports/r03b_same_family_repeat_audit.csv` 必须至少包含：

```text
split
seed_episode_id
instrument_id
signal_date
offset_from_seed
family_id
signal_id
repeat_reason
included_in_primary_fresh_count
```

`reports/r03b_big_winner_label_audit.csv` 必须至少包含：

```text
split
seed_episode_id
instrument_id
seed_trade_date
seed_family_set
seed_condition_group_set
complete_h120_close_anchor_flag
big_winner_forward_h120_close_anchor
big_winner_forward_h120_next_open_anchor
canonical_ref_after_seed_within_30td
canonical_ref_after_seed_within_120td
label_consistency_status
```

## 13. Split 策略

所有 headline tables 必须报告：

```text
train
validation
robustness
all
```

`all` row 只能 descriptive，不得驱动 selection。

R03b 不训练模型，也不选择 candidate，因此没有 train-frozen gate。所有结论必须标记为：

```text
descriptive_only
```

除非后续 requirement 单独创建 validation protocol。

最终报告必须避免以下措辞：

```text
passed signal
validated entry
production gate
add position
buy signal
1R sizing
```

## 14. 未来函数与偏差控制

validator 遇到下面情况必须 fail closed：

- Signal sequence membership / order / count construction 使用 `big_winner`、`good_path`、`bad_path`、forward return、max gain 或 max drawdown。seed event 已固定之后的 fail-closed consistency audit 除外。
- Checkpoint summaries 缺少 no-fresh rows。
- Checkpoint 前失败的 rows 未计入 `r03b_survival_bias_audit.csv` 就被静默删除。
- 报告 `P_good / P_bad` 时没有同时报告 `big_winner_rate_close_anchor`。
- 把 `P_good / P_bad` 描述成 big-winner precision。
- 使用 canonical reference-event overlap 作为 primary big-winner label。
- Same-family repeat triggers 进入 primary `fresh_distinct_family_count`。
- `T+1/T+2` signals 进入 primary fresh counts、checkpoint fresh-count buckets 或 kth-fresh summaries。
- Observable failure 之后的 signals 进入 clean pre-failure fresh denominator。
- 与 observable failure 同 offset 的 ambiguous signals 进入 clean pre-failure fresh denominator。
- 同一 offset 的多个 families 被任意排序。
- Same-offset multi-family step 被拆成多个有顺序的 kth fresh family。
- Sequence pattern collapse 使用 outcome metrics。
- `condition_group_id` 不是从 frozen precision panel dictionary 唯一派生，或派生失败后继续运行。
- input reconciliation 发现 path-only 或 precision-only signal occurrence 后仍继续生成 headline sequence denominators。
- 使用 validation / robustness outcomes 选择 sequence patterns、checkpoints 或 families。
- seed episode 被计入与 `seed_trade_date` 不一致的 split。
- Incomplete h120 rows 进入 `big_winner_rate_close_anchor`。
- Censored path labels 进入 `P_good / P_bad / P_neutral` denominator。
- 任一 output 缺少 `sample_sufficiency_status`。

## 15. Decision 语义

允许的 final decisions：

```text
descriptive_sequence_diagnostic_complete
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_input_reconciliation_failed
blocked_label_denominator_unusable
blocked_sequence_denominator_unusable
invalid_requirement_violation
```

预期成功状态：

```text
descriptive_sequence_diagnostic_complete
```

这个状态不表示 signal 已验证。它只表示 diagnostic tables 已生成，并通过 schema / leakage validation。

## 16. 最终报告要求

`reports/r03b_sequence_big_winner_path_final_report.md` 必须使用中文，并回答：

1. 各 split 有多少 seed episodes？
2. 不考虑 fresh signals 前，base `big_winner_rate_close_anchor`、`P_good`、`P_bad` 是多少？
3. 在每个 checkpoint 下，更高的 `fresh_distinct_family_count` 是否改变 `big_winner_rate_close_anchor`？
4. 同样的 fresh count 增加，是否也让 `P_good / P_bad` 朝同方向变化？
5. 表面改善是否可以由 survival bias 解释？
6. 哪些 sequence patterns 有足够 denominator？
7. 哪些 sequence patterns 太稀疏，不得 promotion？
8. Canonical reference-event overlap 和 close-anchor big-winner label 是否给出同样结论？
9. 如果需要下一步实验，推荐做什么？

报告必须包含硬性警告：

```text
本诊断明确区分 big-winner labels 和 path labels。
P_good / P_bad 不得解读为 P(big winner | signal)。
```

报告还必须包含：

```text
本实验不产出 production signal。
本实验不产出 position size。
本实验不产出 R03 risk-budget allocation。
```

## 17. 实现检查清单

- [ ] 读取并校验 R02 path-query manifest 和 validation status。
- [ ] 只加载 7 个 frozen single-family path CSVs。
- [ ] 写出 path-query 与 precision panel 的 input reconciliation audit。
- [ ] 从 precision panel 唯一派生 frozen `family_id -> condition_group_id` dictionary。
- [ ] 构造 deterministic same-day signal event panel。
- [ ] 构造 deterministic seed episode panel。
- [ ] 构造 T+1..T+30 的 post-seed signal timeline。
- [ ] 构造 T+3..T+30 的 primary fresh distinct-family steps。
- [ ] 保留 same-family repeats 为 audit-only。
- [ ] 保留 same-offset multi-family steps，不做任意排序。
- [ ] 计算 close-anchor h120 big-winner label。
- [ ] 计算 next-open h120 big-winner compatibility label。
- [ ] 计算 canonical reference-event overlap audit labels。
- [ ] 将 path labels 与 big-winner labels 分开计算。
- [ ] 写出 seed episode label summary。
- [ ] 写出 checkpoint fresh-count summary。
- [ ] 写出 kth-fresh step summary。
- [ ] 写出 sequence-pattern summary。
- [ ] 写出 offset hazard summary。
- [ ] 写出 survival-bias audit。
- [ ] 写出 same-offset multi-family、same-family repeat 和 big-winner label audit。
- [ ] 校验 denominators、leakage controls 和 report language。
- [ ] 写出 manifest 和 validation JSON。
