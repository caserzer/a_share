# EP4 需求 03c: Price-Aware Kth-Fresh 与 Family-Set Pooling 诊断 V1

## 1. 需求元信息

- 需求 id: `ep4_r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1`
- 简称: `r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1`
- 状态: 可实现的诊断型需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion3.md`
- 上游 R03b 需求: `ep4/requirement_03b_signal_sequence_big_winner_path_diagnostic_v1.md`
- 上游 R03b 输出: `ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/`
- 上游 path-query 需求: `ep4/requirement_02_family_signal_120d_path_query_v1.md`
- 上游 precision 需求: `ep4/requirement_02_family_precision_forward_return_stats_v1.md`
- 必需输出根目录: `ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/`
- 必需 config 路径: `ep4/configs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r03c_price_aware_kth_fresh_family_set_pooling_diagnostic.py`
- 必需 validator 路径: `ep4/scripts/validate_r03c_price_aware_kth_fresh_family_set_pooling_diagnostic.py`
- 日期: 2026-05-16

## 2. 实验目的

R03b 已经证明：seed signal 之后，如果后续不同 family 的 fresh signal 陆续出现，`P_good / P_bad` 的 path label 变化很强，`big_winner_forward_h120_close_anchor` 的变化存在但弱于 path label。同时 R03b 也暴露两个问题：

1. `fresh_count_bucket` 是粗粒度统计，可能掩盖了第几个 fresh step 和出现时间的差异。
2. 完整 sequence pattern 太稀疏，很多高表现行落在 `other_sparse_patterns`，需要 family-set 层面的 pooling。

本需求在 R03b 基础上新增第三个维度：等待 fresh signal 出现期间，股票价格可能已经明显抬升。因此 R03c 不只问“fresh signal 出现后 big-winner / path 概率是否提高”，还必须问：

```text
等待后续 fresh signal 的过程中，价格已经涨了多少？
如果等到第 k 个 fresh signal 后才行动，后续 path 是否仍有足够空间？
```

R03c 必须同时回答三个主问题：

1. `kth_fresh_step_bucket + kth_fresh_offset_bucket` 是否比单纯 `fresh_count_bucket` 更有解释力？
2. 是否存在 unordered family-set 层面的可复用 grouping，而不是稀疏的完整 ordered sequence pattern？
3. 上述 fresh-step / family-set 的解释力，在加入 `wait_return_to_fresh_entry` 后是否仍然成立，还是主要来自已经涨高后的 late confirmation？

本实验是 price-aware sequence diagnostic，不是交易规则，不是加仓规则，不是 position sizing 实验。

## 3. 实验边界

允许：

- 复用 R03b 的 seed episode、sequence step、checkpoint state 和 big-winner/path label 定义。
- 重新加载 R02 path-query per-signal CSV，用 fresh signal 当日的 next-open `entry_price` 和 120D path metrics 作为 fresh-anchor path 来源。
- 重新加载 R02 precision action-time panel，用 `close_t`、`next_open_t1`、close-anchor / next-open h120 labels 做 action-time price 与 label audit。
- 对每个 clean primary fresh step 计算 seed entry 到 fresh entry 的等待收益。
- 分别统计 seed-anchor outcome 和 fresh-anchor outcome。
- 比较 `fresh_count_bucket`、`kth_fresh_step_bucket + offset_bucket`、`kth_fresh_step_bucket + offset_bucket + wait_return_bucket` 的描述性解释力。
- 构造 unordered family-set pooling key，并按 split 报告 denominator、big-winner、path 和 price movement。
- 把 train、validation、robustness、all 四个 split 全部输出；`all` 只能描述，不得用于选择。

禁止：

- 不得输出 production signal、entry rule、add-position rule、reduce rule、stop rule、position size 或 R03 risk-budget allocation。
- 不得用 validation / robustness outcome 选择 family set、offset bucket、price bucket 或 pooling level。
- 不得用 `big_winner`、`good_path`、`bad_path`、future return、max gain、max drawdown 来构造 fresh-step membership、family-set key 或 sparse bucket collapse。
- 不得把 `P_good / P_bad` 解读为 `P(big winner | signal)`。
- 不得把 fresh-anchor h120 big-winner rate 和 seed-anchor h120 big-winner rate 混成同一个指标。
- 不得用 checkpoint 之后才出现的 signal 构造 checkpoint-observable family-set。
- 不得在 same-offset multi-family step 内施加任意 family 顺序。
- 不得把 same-family repeat 计入 distinct-family fresh evidence。
- 不得只保留已经出现 fresh signal 的样本而删除 no-fresh 或 failed-before-fresh rows。
- 不得在线抓取数据。

## 4. 必需输入产物

所有输入必须来自本地 artifact。

R03b 主输入：

```text
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/manifests/r03b_signal_sequence_big_winner_path_manifest.json
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/manifests/r03b_signal_sequence_big_winner_path_validation.json
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_seed_episode_panel.parquet
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_sequence_step_panel.parquet
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_checkpoint_state_panel.parquet
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_signal_timeline_panel.parquet
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/reports/r03b_checkpoint_fresh_count_summary.csv
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/reports/r03b_kth_fresh_summary.csv
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/reports/r03b_sequence_pattern_summary.csv
```

R03b cache panels 是 R03c sequence 构造的权威来源。R03b summary CSVs 只能用于 lineage / reconciliation / report cross-check，不得作为 row-level membership、kth fresh 派生或 family-set pooling 的权威来源。

R02 path-query price/path 输入：

```text
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_manifest.json
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_validation.json
ep4/outputs/r02_family_signal_120d_path_query_v1/reports/signals/*_120d_path.csv
```

runner 默认只能加载下面 7 个 frozen single-family signal 输出：

```text
single_momentum_rps
single_oscillator
single_price_trend
single_pullback_drawdown
single_range_breakout
single_volatility_band
single_volume_money
```

R02 precision action-time 输入：

```text
ep4/outputs/r02_family_precision_forward_return_stats_v1/manifests/r02_family_precision_forward_return_stats_manifest.json
ep4/outputs/r02_family_precision_forward_return_stats_v1/manifests/r02_family_precision_forward_return_stats_validation.json
ep4/outputs/r02_family_precision_forward_return_stats_v1/cache/r02_family_action_time_panel.parquet
```

runner 必须校验：

```text
r03b_signal_sequence_big_winner_path_validation.json.validation_status == passed
r02_family_signal_120d_path_query_validation.json.validation_status == passed
r02_family_precision_forward_return_stats_validation.json.validation_status == passed
```

如果任一必需 validation 未通过或缺失，runner 不得继续生成 headline tables。最终 decision 必须为：

```text
blocked_missing_required_input
blocked_upstream_validation_failed
```

## 5. 输出目录结构

runner 必须写出：

```text
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/
  cache/
    r03c_fresh_step_price_panel.parquet
    r03c_checkpoint_price_state_panel.parquet
    r03c_family_set_pooling_panel.parquet
  reports/
    r03c_input_readiness_audit.csv
    r03c_price_reconciliation_audit.csv
    r03c_wait_price_movement_summary.csv
    r03c_fresh_count_price_conditioned_summary.csv
    r03c_kth_offset_price_summary.csv
    r03c_grouping_explanatory_power_comparison.csv
    r03c_family_set_pooling_summary.csv
    r03c_family_set_split_stability_audit.csv
    r03c_seed_vs_fresh_anchor_outcome_audit.csv
    r03c_survival_price_bias_audit.csv
    r03c_price_aware_pooling_final_report.md
    r03c_price_aware_pooling_validation_audit.csv
  manifests/
    r03c_price_aware_kth_fresh_family_set_pooling_manifest.json
    r03c_price_aware_kth_fresh_family_set_pooling_validation.json
```

## 6. 核心粒度

R03c 有三个核心 panel。

### 6.1 Fresh Step Price Panel

`r03c_fresh_step_price_panel.parquet` 是最重要的 row-level panel。粒度固定为：

```text
one row per clean primary fresh step
```

clean primary fresh step 必须继承 R03b 定义：

```text
included_in_primary_fresh_count == true
step_status in {fresh_distinct_family_step, same_offset_multi_family_step}
3 <= step_offset <= 30
step_offset < observable_failure_offset, if observable_failure_offset exists
step_offset != observable_failure_offset
```

`kth_fresh_step_index_raw` 必须由每个 `seed_episode_id` 内的 clean primary fresh steps 按 `step_offset`、`step_signal_date` 排序后重新派生：

```text
kth_fresh_step_index_raw = 1, 2, 3, ...
```

summary 层必须另行派生：

```text
kth_fresh_step_bucket =
  "1" if kth_fresh_step_index_raw == 1
  "2" if kth_fresh_step_index_raw == 2
  "3" if kth_fresh_step_index_raw == 3
  "4plus" if kth_fresh_step_index_raw >= 4
```

实现不得把 R03b 的 `sequence_step_index` 当成 kth fresh index，因为 `sequence_step_index` 还包含 T+1/T+2、same-family repeat、after-failure、ambiguous 等非 primary fresh rows。

必需 id / sequence fields：

```text
seed_episode_id
instrument_id
split
seed_trade_date
seed_family_set
seed_same_day_family_count
seed_entry_date
seed_entry_price
step_signal_date
step_offset
kth_fresh_step_index_raw
kth_fresh_step_bucket
kth_fresh_offset_bucket
added_family_set
added_family_count
cumulative_distinct_family_set_after_step
cumulative_distinct_family_count_after_step
is_same_offset_multi_family_step
```

`kth_fresh_offset_bucket` 固定为：

```text
t3_t5
t6_t10
t11_t20
t21_t30
```

### 6.2 Checkpoint Price State Panel

`r03c_checkpoint_price_state_panel.parquet` 粒度固定为：

```text
one row per seed_episode_id x checkpoint
```

它继承 R03b checkpoint rows，并新增 checkpoint-observable price/family-set state。必需字段：

```text
seed_episode_id
instrument_id
split
checkpoint
checkpoint_offset
checkpoint_state
at_risk_at_checkpoint
fresh_distinct_family_count_before_or_at_checkpoint
fresh_distinct_family_count_bucket
kth_fresh_reached_before_or_at_checkpoint
fresh_family_set_before_or_at_checkpoint
cumulative_family_set_before_or_at_checkpoint
latest_clean_fresh_step_offset_before_or_at_checkpoint
latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint
latest_clean_fresh_kth_fresh_offset_bucket_before_or_at_checkpoint
latest_clean_fresh_entry_date_before_or_at_checkpoint
latest_clean_fresh_entry_price_before_or_at_checkpoint
wait_return_to_latest_fresh_entry_before_or_at_checkpoint
wait_return_bucket_before_or_at_checkpoint
```

如果 checkpoint 前没有 clean primary fresh step：

```text
fresh_family_set_before_or_at_checkpoint = none
cumulative_family_set_before_or_at_checkpoint = seed_family_set
latest_clean_fresh_* = null
latest_clean_fresh_kth_fresh_step_bucket_before_or_at_checkpoint = no_fresh
latest_clean_fresh_kth_fresh_offset_bucket_before_or_at_checkpoint = no_fresh
wait_return_bucket_before_or_at_checkpoint = no_fresh
```

Checkpoint panel 不得使用 checkpoint 之后的 signals 或 price fields。

### 6.3 Family Set Pooling Panel

`r03c_family_set_pooling_panel.parquet` 粒度为：

```text
one row per fresh step x pooling level
```

必需字段：

```text
seed_episode_id
instrument_id
split
pooling_level
pooling_key
pooling_key_family_count
kth_fresh_step_bucket
kth_fresh_offset_bucket
wait_return_bucket
added_family_set
cumulative_distinct_family_set_after_step
```

允许的 `pooling_level`：

```text
fresh_added_family_set
cumulative_family_set_after_step
family_presence_signature
```

`fresh_added_family_set`：

```text
pooling_key = sorted added_family_set joined by "|"
```

`cumulative_family_set_after_step`：

```text
pooling_key = sorted seed_family_set plus all clean primary fresh families through this step
```

`family_presence_signature`：

```text
source_family_set = cumulative_distinct_family_set_after_step

pooling_key =
  contains_momentum_rps={0/1}|
  contains_oscillator={0/1}|
  contains_price_trend={0/1}|
  contains_pullback_drawdown={0/1}|
  contains_range_breakout={0/1}|
  contains_volatility_band={0/1}|
  contains_volume_money={0/1}
```

`family_presence_signature` 必须基于 `cumulative_distinct_family_set_after_step`，不得基于 `added_family_set`。否则它会和 `fresh_added_family_set` 的语义重叠，无法回答 cumulative family-set pooling 问题。

R03c V1 不启用 `family_role_set`。当前 7 个 frozen family 如果一一映射到 7 个 role，并不会降低维度，反而会让读者误以为已经做了经济角色抽象。后续如果扩展 family universe，可以另开需求定义 outcome-blind role taxonomy。

## 7. Price Movement 定义

R03c 必须明确区分 seed entry、fresh signal close、fresh entry 三个价格锚点。

### 7.1 Seed Entry

Seed entry 继承 R03b seed panel：

```text
seed_entry_date
seed_entry_price
```

这是 seed signal 完整可观察后的 next-open executable price。

### 7.2 Fresh Signal Close

Fresh signal close price 来自 R02 precision action-time panel：

```text
fresh_signal_close_price = close_t at (instrument_id, step_signal_date, added family condition row)
```

precision panel 的行级定位必须使用下面过滤条件：

```text
instrument_id == step.instrument_id
trade_date == step.step_signal_date
family_id in added_family_set
signal_occurs == true
```

在当前 frozen family universe 中，每个 added family 预期只有一个 matched precision row。若同一个 `(instrument_id, trade_date, family_id)` 匹配多个 `condition_group_id`：

```text
if close_t / next_open_t1 / complete_h120_flag / h120 label fields are identical across matched rows:
  keep one deterministic row after sorting by condition_group_id
else:
  fail closed with blocked_price_reconciliation_failed
```

如果某个 added family 没有 matched precision row，runner 必须 fail closed。`r03c_price_reconciliation_audit.csv` 必须报告 matched precision row count 和 condition-group uniqueness status。

如果 same-offset multi-family step 有多个 added families，则这些 precision rows 的下面字段必须一致；否则 runner 必须 fail closed：

```text
close_t
next_open_t1
complete_h120_flag
forward_close_peak_h120_return_from_close
big_winner_forward_from_signal_close
forward_close_peak_h120_return_from_next_open
big_winner_forward_from_next_open
```

数值字段一致性使用第 7.3 节相同的 `numeric_consistency_tolerance = 1e-10`；布尔字段必须完全一致。

必需字段：

```text
fresh_signal_close_price
wait_return_to_fresh_signal_close =
  fresh_signal_close_price / seed_entry_price - 1
```

这个字段回答：fresh signal 出现并可被收盘后观察到时，价格相对 seed entry 已经变化多少。

### 7.3 Fresh Entry

Fresh entry price 来自 R02 path-query CSV 对应 fresh signal row：

```text
fresh_entry_date
fresh_entry_price
fresh_entry_valid
```

如果 same-offset multi-family step 有多个 added families，则这些 rows 的下面字段必须一致：

```text
fresh_entry_date
fresh_entry_price
fresh_entry_valid
path_complete_120d
available_forward_trading_days
max_gain_120d
max_drawdown_120d
close_return_t20
close_return_t60
close_return_t120
first_minus5_offset
first_close_minus5_offset
hit_plus10_before_minus5
max_loss_before_first_plus10
path_quality_flag
early_failure_flag
```

数值字段一致性使用绝对误差容忍：

```text
numeric_consistency_tolerance = 1e-10
```

布尔、日期、枚举字段必须完全一致。如果不一致，runner 必须 fail closed，并写入 `r03c_price_reconciliation_audit.csv`。实现不得对同一 same-offset multi-family step 的 per-family path fields 任意 pick first。

必需字段：

```text
wait_return_to_fresh_entry =
  fresh_entry_price / seed_entry_price - 1
```

这是 headline wait-cost metric。所有 price-conditioned summary 必须优先使用 `wait_return_to_fresh_entry`。

### 7.4 Wait Return Buckets

fresh-step rows 的 `wait_return_bucket` 固定为：

```text
down_or_flat: wait_return_to_fresh_entry <= 0
up_0_5pct: 0 < wait_return_to_fresh_entry <= 0.05
up_5_10pct: 0.05 < wait_return_to_fresh_entry <= 0.10
up_10_20pct: 0.10 < wait_return_to_fresh_entry <= 0.20
up_gt_20pct: wait_return_to_fresh_entry > 0.20
missing_or_invalid: missing fresh_entry_price or invalid seed_entry_price
```

`missing_or_invalid` rows 必须保留在 row-level panels 和 summary tables 中。对 price-conditioned explanatory-power parent 来说，它们必须作为独立 bucket 留在 parent denominator 中，除非具体 outcome 在数学上不可计算。实现不得在计算 lift 或 denominator share 前静默删除 `missing_or_invalid` rows。

checkpoint rows 的 `wait_return_bucket_before_or_at_checkpoint` 额外允许：

```text
no_fresh: no clean primary fresh step is observable before or at checkpoint
```

`no_fresh` 只能用于 checkpoint-level summaries，不得出现在 `r03c_fresh_step_price_panel.parquet`。

Report headline 必须至少显示：

```text
wait_return_to_fresh_entry_p25
wait_return_to_fresh_entry_p50
wait_return_to_fresh_entry_p75
pct_wait_up_gt_5pct
pct_wait_up_gt_10pct
pct_wait_up_gt_20pct
```

## 8. Fresh-Anchor Path 与 Outcome 定义

R03c 必须同时保留 seed-anchor outcome 和 fresh-anchor outcome。

### 8.1 Seed-Anchor Outcome

Seed-anchor fields 直接继承 R03b seed panel：

```text
complete_h120_close_anchor_flag
big_winner_forward_h120_close_anchor
forward_close_peak_h120_return_from_seed_close
big_winner_forward_h120_next_open_anchor
label
```

这些字段回答：

```text
这个 seed episode 最终是否成为 seed-anchor big winner？
```

### 8.2 Fresh-Anchor Outcome

Fresh-anchor fields 来自 fresh signal 对应的 R02 path-query CSV 和 precision panel：

```text
fresh_complete_h120_close_anchor_flag
fresh_big_winner_forward_h120_close_anchor
fresh_forward_close_peak_h120_return_from_signal_close
fresh_forward_close_peak_h120_return_from_next_open
fresh_big_winner_forward_h120_next_open_anchor
fresh_entry_date
fresh_entry_price
fresh_entry_valid
fresh_path_complete_120d
fresh_available_forward_trading_days
fresh_max_gain_120d
fresh_max_drawdown_120d
fresh_close_return_t20
fresh_close_return_t60
fresh_close_return_t120
fresh_first_minus5_offset
fresh_first_close_minus5_offset
fresh_hit_plus10_before_minus5
fresh_max_loss_before_first_plus10
fresh_path_quality_flag
fresh_early_failure_flag
fresh_path_label
```

R03c 字段与上游字段的映射固定如下：

| R03c field | source artifact | source column | anchor |
|:--|:--|:--|:--|
| `fresh_complete_h120_close_anchor_flag` | R02 precision action-time panel | `complete_h120_flag` | close_t |
| `fresh_forward_close_peak_h120_return_from_signal_close` | R02 precision action-time panel | `forward_close_peak_h120_return_from_close` | close_t |
| `fresh_big_winner_forward_h120_close_anchor` | R02 precision action-time panel | `big_winner_forward_from_signal_close` | close_t |
| `fresh_forward_close_peak_h120_return_from_next_open` | R02 precision action-time panel | `forward_close_peak_h120_return_from_next_open` | next_open_t1 |
| `fresh_big_winner_forward_h120_next_open_anchor` | R02 precision action-time panel | `big_winner_forward_from_next_open` | next_open_t1 |
| `fresh_entry_date` | R02 path-query CSV | `entry_date` | next_open_t1 executable entry |
| `fresh_entry_price` | R02 path-query CSV | `entry_price` | next_open_t1 executable entry |
| `fresh_entry_valid` | R02 path-query CSV | `entry_valid` | next_open_t1 executable entry |
| `fresh_path_complete_120d` | R02 path-query CSV | `path_complete_120d` | next_open_t1 executable entry |
| `fresh_available_forward_trading_days` | R02 path-query CSV | `available_forward_trading_days` | next_open_t1 executable entry |
| `fresh_max_gain_120d` | R02 path-query CSV | `max_gain_120d` | entry_price |
| `fresh_max_drawdown_120d` | R02 path-query CSV | `max_drawdown_120d` | entry_price |
| `fresh_close_return_t20` | R02 path-query CSV | `close_return_t20` | entry_price |
| `fresh_close_return_t60` | R02 path-query CSV | `close_return_t60` | entry_price |
| `fresh_close_return_t120` | R02 path-query CSV | `close_return_t120` | entry_price |
| `fresh_first_minus5_offset` | R02 path-query CSV | `first_minus5_offset` | entry_price |
| `fresh_first_close_minus5_offset` | R02 path-query CSV | `first_close_minus5_offset` | entry_price |
| `fresh_hit_plus10_before_minus5` | R02 path-query CSV | `hit_plus10_before_minus5` | entry_price |
| `fresh_max_loss_before_first_plus10` | R02 path-query CSV | `max_loss_before_first_plus10` | entry_price |
| `fresh_path_quality_flag` | R02 path-query CSV | `path_quality_flag` | entry_price |
| `fresh_early_failure_flag` | R02 path-query CSV | `early_failure_flag` | entry_price |

Headline policy 固定为：

```text
fresh_anchor_big_winner headline = close-anchor fresh_big_winner_forward_h120_close_anchor
fresh_anchor_path headline = entry-anchored fresh_path_label and fresh path metrics from R02 path-query CSV
fresh_big_winner_forward_h120_next_open_anchor = audit-only compatibility label
```

因此，`fresh_big_winner_forward_h120_close_anchor` 与 `fresh_close_return_t20` 属于不同 price anchor；报告必须明确这一点，不得把两者混成同一个可执行收益口径。

Fresh-anchor big-winner thresholds 继承 R02 precision / R03b 定义，并必须显式计算为：

```text
fresh_big_winner_forward_h120_close_anchor =
  fresh_forward_close_peak_h120_return_from_signal_close >= 0.50

fresh_big_winner_forward_h120_next_open_anchor =
  fresh_forward_close_peak_h120_return_from_next_open >= 0.50
```

阈值一致性检查只对 `fresh_complete_h120_close_anchor_flag == true` 且对应 return field 非空的 rows 执行。Incomplete h120 rows 不进入 fresh-anchor big-winner denominator。如果 precision panel 中布尔 label 与上述 return threshold 不一致，runner 必须 fail closed 并写入 price reconciliation audit。

Fresh-anchor `fresh_path_label` 使用与 R03b 相同优先级：

```text
1. if fresh_entry invalid or required forward path unavailable:
     fresh_path_label = censored_or_invalid
2. else if fresh bad condition is true:
     fresh_path_label = bad_path
3. else if fresh good condition is true:
     fresh_path_label = good_path
4. else:
     fresh_path_label = neutral_path
```

Fresh bad condition：

```text
fresh_early_failure_flag == true
OR fresh_first_minus5_offset <= 10
OR fresh_max_loss_before_first_plus10 <= -0.06
```

Fresh good condition：

```text
fresh_hit_plus10_before_minus5 == true
OR fresh_path_quality_flag in {clean_continuation, tradable_continuation}
```

这些阈值不是 R03c 的自由参数。`fresh_first_minus5_offset <= 10`、`fresh_max_loss_before_first_plus10 <= -0.06`、`fresh_hit_plus10_before_minus5` 和 `{clean_continuation, tradable_continuation}` 继承 R03b path label 定义，并来自 R02 path-query 的 entry-anchored fields。

R02 path-query 允许的 `path_quality_flag` 取值集合固定为：

```text
clean_continuation
tradable_continuation
mixed
transient_spike
whipsaw_after_profit
late_drawdown
severe_drawdown
early_failure
incomplete
```

如果出现上述集合之外的 `fresh_path_quality_flag`，runner 必须 fail closed。

### 8.3 Price-Adjusted Opportunity Fields

R03c 必须输出下面 audit fields：

```text
fresh_max_gain_120d_from_seed_entry_reference =
  (1 + wait_return_to_fresh_entry) * (1 + fresh_max_gain_120d) - 1

fresh_close_return_t20_from_seed_entry_reference =
  (1 + wait_return_to_fresh_entry) * (1 + fresh_close_return_t20) - 1

wait_cost_to_remaining_max_gain_ratio =
  wait_return_to_fresh_entry / fresh_max_gain_120d
  only when fresh_max_gain_120d > 0
```

这些字段只能用于解释价格已经移动了多少，以及 fresh entry 后还剩多少空间。它们不得被解释为实际持仓收益，因为等待 fresh signal 的策略在等待期间并未持仓。

`wait_cost_to_remaining_max_gain_ratio` 是 audit-only 字段，禁止作为：

```text
outcome_family
bucket_outcome_value
grouping key
family-set selection key
explanatory-power lift input
```

## 9. Headline Summaries

所有 headline summaries 必须输出：

```text
split
fresh_step_count, when grain is fresh-step based
seed_episode_count, when grain is checkpoint or seed based
unique_seed_episode_count
unique_instrument_count, when grain is fresh-step or pooling based
unique_step_signal_date_count, when grain is fresh-step or pooling based
seed_anchor_big_winner_denominator
seed_anchor_big_winner_count
seed_anchor_big_winner_rate
fresh_anchor_big_winner_denominator, when applicable
fresh_anchor_big_winner_count, when applicable
fresh_anchor_big_winner_rate, when applicable
seed_path_denominator
seed_P_good
seed_P_bad
fresh_path_denominator, when applicable
fresh_P_good, when applicable
fresh_P_bad, when applicable
wait_return_to_fresh_entry_p25
wait_return_to_fresh_entry_p50
wait_return_to_fresh_entry_p75
pct_wait_up_gt_5pct
pct_wait_up_gt_10pct
pct_wait_up_gt_20pct
sample_sufficiency_status
```

所有 seed-anchor metrics 必须以 group 内去重后的 `seed_episode_id` 为分母。也就是说，同一个 seed 在 fresh-step / pooling panel 中出现多行时，计算 `seed_anchor_big_winner_rate`、`seed_P_good`、`seed_P_bad` 只能计一次。

所有 fresh-anchor metrics 必须以 group 内 fresh-step rows 为分母。`fresh_step_count` 和 `unique_seed_episode_count` 必须同时报告，避免把“更多 fresh steps 的 episode”误读成“更多独立 seed episodes”。

所有 fresh-step / pooling based summaries 必须同时报告 `unique_instrument_count` 和 `unique_step_signal_date_count`，用于暴露同一行情阶段或同一股票聚集导致的有效独立观测不足。

checkpoint-level summaries 使用 `seed_episode_id x checkpoint` 为 row 粒度；同一个 checkpoint bucket 内每个 seed 只能计一次。fresh-anchor fields 在 checkpoint 前没有 clean fresh step 的 rows 中必须为 null / not_applicable，不得把 seed-anchor label 填入 fresh-anchor fields。

可信区间默认沿用 R03b / R03a convention：

```text
alpha_source = Jeffreys_prior
credible_interval_level = 0.90
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

这些阈值只影响 report label，不能用于生产规则选择。

## 10. 必需诊断表

### 10.1 Input Readiness Audit

`reports/r03c_input_readiness_audit.csv`

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

### 10.2 Price Reconciliation Audit

`reports/r03c_price_reconciliation_audit.csv`

必需字段：

```text
split
seed_episode_id
instrument_id
step_signal_date
step_offset
added_family_set
added_family_count
matched_path_row_count
matched_precision_row_count
matched_precision_condition_group_count
precision_condition_group_uniqueness_status
precision_label_fields_consistent
fresh_signal_close_price_consistent
fresh_entry_date_consistent
fresh_entry_price_consistent
fresh_path_fields_consistent
reconciliation_status
failure_reason
```

任何 clean primary fresh step 无法唯一映射到 path-query / precision action-time rows，runner 必须 fail closed。

### 10.3 Wait Price Movement Summary

`reports/r03c_wait_price_movement_summary.csv`

粒度：

```text
split
kth_fresh_step_bucket
kth_fresh_offset_bucket
```

这个表只回答价格移动，不直接回答 outcome。

必需字段：

```text
fresh_step_count
unique_seed_episode_count
unique_instrument_count
unique_step_signal_date_count
wait_return_to_fresh_signal_close_p25
wait_return_to_fresh_signal_close_p50
wait_return_to_fresh_signal_close_p75
wait_return_to_fresh_entry_p25
wait_return_to_fresh_entry_p50
wait_return_to_fresh_entry_p75
pct_wait_down_or_flat
pct_wait_up_0_5pct
pct_wait_up_5_10pct
pct_wait_up_10_20pct
pct_wait_up_gt_20pct
sample_sufficiency_status
```

### 10.4 Fresh-Count Price-Conditioned Summary

`reports/r03c_fresh_count_price_conditioned_summary.csv`

粒度：

```text
split
checkpoint
fresh_distinct_family_count_bucket
wait_return_bucket_before_or_at_checkpoint
```

这个表回答：

```text
在同一个 checkpoint 和 fresh_count bucket 下，
等待到 latest clean fresh entry 时价格已经涨了多少，
以及该 price bucket 下 seed-anchor outcome 是否仍然不同？
```

如果 checkpoint 前没有 clean fresh step，`wait_return_bucket_before_or_at_checkpoint = no_fresh`。

这个表的 primary outcome 是 seed-anchor outcome。fresh-anchor outcome 只允许在 checkpoint 前存在 latest clean fresh step 时，使用该 latest clean fresh step 的 fresh-anchor fields；`no_fresh` rows 的 fresh-anchor fields 必须为 null / not_applicable。

### 10.5 Kth + Offset Price Summary

`reports/r03c_kth_offset_price_summary.csv`

粒度：

```text
split
kth_fresh_step_bucket
kth_fresh_offset_bucket
wait_return_bucket
added_family_count_bucket
```

这个表是 R03c 第一主轴，必须直接回答：

```text
kth_fresh_step_bucket + offset_bucket 是否比单纯 fresh_count 更有解释力？
价格等待成本加入后，这个解释力是否还存在？
```

必需字段除第 9 节 headline metrics 外，还必须包含：

```text
fresh_close_return_t20_p50
fresh_close_return_t60_p50
fresh_close_return_t120_p50
fresh_max_gain_120d_p50
fresh_max_drawdown_120d_p50
fresh_early_failure_rate
fresh_hit_plus10_before_minus5_rate
fresh_path_quality_clean_or_tradable_rate
unique_seed_episode_count
unique_instrument_count
unique_step_signal_date_count
```

`added_family_count_bucket` 固定为：

```text
1
2plus
```

### 10.6 Grouping Explanatory Power Comparison

`reports/r03c_grouping_explanatory_power_comparison.csv`

粒度：

```text
split
grouping_scheme
outcome_family
```

允许的 `grouping_scheme`：

```text
checkpoint_fresh_count
checkpoint_latest_kth_offset
checkpoint_latest_kth_offset_wait_bucket
kth_offset
kth_offset_wait_bucket
family_set_pooling
family_set_pooling_wait_bucket
```

允许的 `outcome_family`：

```text
seed_anchor_big_winner
seed_path_good_bad
fresh_anchor_big_winner
fresh_path_good_bad
```

必需字段：

```text
evaluated_row_count
evaluated_bucket_count
sufficient_bucket_count
thin_or_sparse_bucket_count
weighted_abs_lift_vs_parent
max_positive_lift_vs_parent
max_negative_lift_vs_parent
direction_consistent_bucket_count
direction_inconsistent_bucket_count
price_bucket_coverage_rate
interpretation_status
```

`weighted_abs_lift_vs_parent` 定义：

```text
sum(bucket_denominator * abs(bucket_outcome_value - parent_outcome_value)) / sum(bucket_denominator)
```

`outcome_family` 必须先映射成一个 scalar outcome value：

```text
seed_anchor_big_winner:
  outcome_value = seed_anchor_big_winner_rate

fresh_anchor_big_winner:
  outcome_value = fresh_anchor_big_winner_rate

seed_path_good_bad:
  outcome_value = seed_P_good - seed_P_bad

fresh_path_good_bad:
  outcome_value = fresh_P_good - fresh_P_bad
```

`parent_outcome_value` 必须在同一个 split、同一个 outcome_family、同一个 comparable denominator 内计算。不同 `grouping_scheme` 的 parent 不得跨 row grain 混用：

```text
checkpoint_fresh_count:
  parent = same split + same checkpoint + all fresh_count buckets
  row grain = seed_episode_id x checkpoint
  fresh-anchor outcome 在 no_fresh rows 中必须为 not_applicable

checkpoint_latest_kth_offset:
  parent = same split + same checkpoint + all latest kth/offset buckets
  row grain = seed_episode_id x checkpoint
  grouping key = latest clean fresh step's kth_fresh_step_bucket + kth_fresh_offset_bucket before or at checkpoint
  no clean fresh before checkpoint = no_fresh

checkpoint_latest_kth_offset_wait_bucket:
  parent = same split + same checkpoint + same latest kth/offset bucket
  row grain = seed_episode_id x checkpoint
  grouping key = latest kth/offset bucket + wait_return_bucket_before_or_at_checkpoint
  no clean fresh before checkpoint = no_fresh

kth_offset:
  parent = same split + all clean primary fresh steps
  row grain = fresh_step

kth_offset_wait_bucket:
  parent = same split + same kth_fresh_step_bucket + kth_fresh_offset_bucket
  row grain = fresh_step

family_set_pooling:
  parent = same split + same pooling_level
  row grain = fresh_step x pooling_level

family_set_pooling_wait_bucket:
  parent = same split + same pooling_level + same wait_return_bucket
  row grain = fresh_step x pooling_level
```

对 path outcome families，`bucket_outcome_value` 必须使用 `P_good - P_bad`，不能只用 `P_good`。报告可以分别展示 `P_good` 和 `P_bad`，但 explanatory-power comparison 每个 `outcome_family` 只能使用一个 scalar outcome value。

不同 row grain 的 `grouping_scheme` 之间不得直接比较 `weighted_abs_lift_vs_parent` 的绝对大小。回答 “kth/offset 是否比 fresh_count 更有解释力” 时，必须使用 checkpoint-aligned schemes：

```text
checkpoint_fresh_count
checkpoint_latest_kth_offset
checkpoint_latest_kth_offset_wait_bucket
```

fresh-step grain 的 `kth_offset` / `kth_offset_wait_bucket` 只能说明 fresh-step 内部结构，不能直接和 checkpoint fresh-count 的 lift 数值比较。

`interpretation_status` 只能是：

```text
descriptive_more_informative_than_fresh_count
descriptive_similar_to_fresh_count
descriptive_weaker_than_fresh_count
insufficient_denominator
unstable_across_splits
```

该表不得输出 pass/fail production status。它只用于回答 grouping 的描述性解释力。

### 10.7 Family-Set Pooling Summary

`reports/r03c_family_set_pooling_summary.csv`

粒度：

```text
split
pooling_level
pooling_key
kth_fresh_step_bucket
kth_fresh_offset_bucket
wait_return_bucket
```

这个表是 R03c 第二主轴，必须回答：

```text
是否存在 family-set 层面的可复用 grouping，
而不是依赖稀疏完整 sequence pattern？
```

必需字段除第 9 节 headline metrics 外，还必须包含：

```text
pooling_key_family_count
fresh_step_count
seed_episode_count
unique_instrument_count
unique_step_signal_date_count
split_denominator_share
fresh_anchor_path_quality_clean_or_tradable_rate
fresh_anchor_early_failure_rate
split_stability_status
```

`split_stability_status` 必须使用第 10.8 节同一组 stability status：

```text
stable_descriptive
direction_only
price_unstable
denominator_thin
split_missing
unstable
```

pooling summary 的 sparse handling 只能根据 denominator 执行，不能根据 outcome 执行。默认规则：

```text
if exact pooling_key has fresh_step_count >= N_min_family_set_exact in each of train, validation, robustness:
  keep exact pooling_key
else:
  keep exact pooling_key in the summary
  mark sample_sufficiency_status != sufficient
  set split_stability_status = denominator_thin or split_missing
```

默认：

```text
N_min_family_set_exact = 50
```

不允许把低表现 family-set 合并成一个 bucket、高表现 family-set 合并成另一个 bucket。不允许按 outcome 构造 `other_good_patterns`、`other_bad_patterns` 或类似桶。所有 sparse handling 必须 outcome-blind；如果实现额外输出 `other_sparse_family_sets`，只能作为 audit-only，并且不得进入 headline lift / stability 判断。

### 10.8 Family-Set Split Stability Audit

`reports/r03c_family_set_split_stability_audit.csv`

粒度：

```text
pooling_level
pooling_key
kth_fresh_step_bucket
kth_fresh_offset_bucket
wait_return_bucket
```

必需字段：

```text
train_fresh_step_count
validation_fresh_step_count
robustness_fresh_step_count
train_seed_anchor_big_winner_rate
validation_seed_anchor_big_winner_rate
robustness_seed_anchor_big_winner_rate
train_seed_P_good
validation_seed_P_good
robustness_seed_P_good
train_seed_P_bad
validation_seed_P_bad
robustness_seed_P_bad
train_wait_return_p50
validation_wait_return_p50
robustness_wait_return_p50
denominator_stability_status
direction_stability_status
price_stability_status
overall_stability_status
```

允许的 stability status：

```text
stable_descriptive
direction_only
price_unstable
denominator_thin
split_missing
unstable
```

该 audit 不能用于 freeze rule，只能说明是否值得进入后续 formal validation protocol。

### 10.9 Seed vs Fresh Anchor Outcome Audit

`reports/r03c_seed_vs_fresh_anchor_outcome_audit.csv`

粒度：

```text
split
kth_fresh_step_bucket
kth_fresh_offset_bucket
wait_return_bucket
```

必需字段：

```text
fresh_step_count
unique_seed_episode_count
unique_instrument_count
unique_step_signal_date_count
seed_anchor_big_winner_rate
fresh_anchor_big_winner_rate
seed_P_good
seed_P_bad
fresh_P_good
fresh_P_bad
seed_to_fresh_big_winner_rate_gap
seed_to_fresh_P_good_gap
seed_to_fresh_P_bad_gap
interpretation_note_code
```

允许的 `interpretation_note_code`：

```text
fresh_anchor_remaining_opportunity_stronger
seed_anchor_only_stronger
both_strong
path_only_not_big_winner
price_cost_high_confirmation_only
insufficient_denominator
```

该表必须在报告中明确说明：fresh-anchor label 的 horizon 从 fresh signal date 开始，不能直接替代 seed-anchor label。

### 10.10 Survival Price Bias Audit

`reports/r03c_survival_price_bias_audit.csv`

粒度：

```text
split
```

必需字段：

```text
seed_episode_count
failed_before_t3
failed_t3_to_t5
failed_t6_to_t10
failed_t11_to_t20
failed_t21_to_t30
failed_before_first_clean_fresh_count
no_clean_fresh_episode_count
first_clean_fresh_episode_count
survived_t30_no_fresh
survived_t30_with_fresh
first_clean_fresh_wait_return_p25
first_clean_fresh_wait_return_p50
first_clean_fresh_wait_return_p75
first_clean_fresh_wait_up_gt_10pct_rate
first_clean_fresh_wait_up_gt_20pct_rate
```

Failure buckets 必须直接使用 R03b seed panel 的 `observable_failure_offset` 字段，且区间固定为：

```text
failed_before_t3:
  observable_failure_offset < 3

failed_t3_to_t5:
  3 <= observable_failure_offset <= 5

failed_t6_to_t10:
  6 <= observable_failure_offset <= 10

failed_t11_to_t20:
  11 <= observable_failure_offset <= 20

failed_t21_to_t30:
  21 <= observable_failure_offset <= 30
```

如果 `observable_failure_offset` 为空，则该 seed 不进入 failure bucket。`failed_before_first_clean_fresh_count` 必须使用同一个 `observable_failure_offset` 与每个 seed 的 first clean primary fresh step offset 比较；如果没有 clean primary fresh step 且 `observable_failure_offset` 非空，也计入该字段。

这个 audit 用于防止把 “没有等到 fresh signal” 错误解释为 signal 缺失。许多 seed 是先发生 observable failure，才没有机会进入 fresh-step price panel。R03c final report 必须把该表和 price-conditioned summaries 一起解释。

### 10.11 Validation Audit

`reports/r03c_price_aware_pooling_validation_audit.csv`

粒度：

```text
one row per validation check
```

必需字段：

```text
check_id
check_category
status
severity
failure_reason
affected_rows
artifact_path
```

允许的 `status`：

```text
passed
failed
skipped_not_applicable
```

允许的 `severity`：

```text
info
warning
error
fatal
```

如果任一 `severity in {error, fatal}` 的 check 失败，manifest 中的 final decision 不得为 `descriptive_price_aware_pooling_diagnostic_complete`。

## 11. Split 策略

所有 headline tables 必须报告：

```text
train
validation
robustness
all
```

`all` row 只能 descriptive。任何比较 `kth_offset` 是否优于 `fresh_count` 的判断，必须至少分别展示 validation 和 robustness，不得只用 all-split。

本需求不训练模型，不冻结候选规则，因此不存在 train-frozen gate。所有结论必须标记为：

```text
descriptive_only
```

## 12. 未来函数与偏差控制

validator 遇到下面情况必须 fail closed：

- Fresh-step membership 使用 outcome、future price、fresh-anchor path、seed-anchor path 或 big-winner label。
- `kth_fresh_step_index_raw` 或 `kth_fresh_step_bucket` 与 R03b clean primary fresh step 顺序不一致。
- `offset_bucket` 使用非交易日 offset 或与 R03b `step_offset` 不一致。
- Same-offset multi-family step 被拆成多个有顺序的 family step。
- Same-family repeat 进入 distinct-family fresh evidence。
- Checkpoint price state 缺少 latest clean fresh kth/offset bucket 字段，或 no-fresh rows 未填 `no_fresh`。
- Checkpoint price state 使用 checkpoint 之后的 signal 或 price。
- Price buckets 使用 fresh-entry 之后的 forward path 信息。
- `missing_or_invalid` wait-return rows 在 row-level panel、summary 或 parent denominator 中被静默删除。
- Family-set pooling key 使用 ordered sequence pattern。
- `family_presence_signature` 不是基于 `cumulative_distinct_family_set_after_step` 构造。
- `family_role_set` 出现在 R03c V1 output 中。
- Sparse family-set collapse 使用 outcome metrics。
- Fresh-anchor field mapping 没有按第 8.2 节映射到明确 source column 和 anchor。
- Precision panel join 没有过滤 `signal_occurs == true`，或同一 `(instrument_id, trade_date, family_id)` 多 condition rows 的 label/price fields 不一致后仍继续运行。
- Same-offset multi-family step 的 fresh path fields 不一致后仍继续运行。
- Fresh-anchor and seed-anchor outcome denominators 被混用。
- Report 把 fresh-anchor big-winner rate 描述成 seed-anchor big-winner precision。
- `P_good / P_bad` 被描述成 big-winner probability。
- `wait_cost_to_remaining_max_gain_ratio` 被用于 outcome value、grouping key、selection key 或 explanatory-power lift。
- 不同 row grain 的 grouping schemes 被直接比较 lift 绝对值。
- No-fresh checkpoint rows 被删除。
- Failed-before-fresh rows 没有进入 audit。
- `r03c_survival_price_bias_audit.csv` 缺失，或其 seed_episode_count 与 R03b seed panel 不一致。
- `r03c_price_aware_pooling_validation_audit.csv` 缺失或缺少 required schema fields。
- 任一 headline summary 缺少 wait-return distribution。
- 任一 required output 缺少 `sample_sufficiency_status`。
- 使用 validation / robustness outcome 选择 grouping、bucket 或 family set。

## 13. Decision 语义

允许的 final decisions：

```text
descriptive_price_aware_pooling_diagnostic_complete
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_price_reconciliation_failed
blocked_denominator_unusable
invalid_requirement_violation
```

`blocked_denominator_unusable` 的触发条件固定为：

```text
all-split clean_primary_fresh_step_count < N_min_too_sparse
OR all-split fresh_anchor_big_winner_denominator < N_min_too_sparse
OR all-split fresh_path_denominator < N_min_too_sparse
OR R03b seed panel seed_episode_count != R03c derived seed_episode_count
OR any required split in {train, validation, robustness} has zero seed episodes
```

这些是 execution / denominator validity checks，不是 research pass/fail gate。

预期成功状态：

```text
descriptive_price_aware_pooling_diagnostic_complete
```

这个状态只表示 price-aware kth-fresh / family-set pooling diagnostic 已生成并通过 schema / leakage validation。它不表示任何信号、family-set 或 entry timing 已经验证。

## 14. 最终报告要求

`reports/r03c_price_aware_pooling_final_report.md` 必须使用中文，并回答：

1. R03b 的 fresh-count lift 在加入等待价格变化后是否仍然成立？
2. 等待第 1 / 第 2 / 第 3 / 第 4plus 个 fresh step 时，`wait_return_to_fresh_entry` 的中位数和分布是多少？
3. 在 checkpoint-aligned grain 下，`latest kth_fresh_step_bucket + offset_bucket` 是否比单纯 `fresh_count_bucket` 更能解释 seed-anchor big-winner 和 seed path label？
4. 价格已经上涨 `>10%` 或 `>20%` 的 fresh-step bucket 是否只是 late confirmation？
5. 哪些 unordered family-set pooling key 有足够 denominator？
6. 哪些 family-set 在 validation / robustness 中方向一致？
7. family-set 的效果是否依赖过高的 wait-return bucket？
8. seed-anchor outcome 和 fresh-anchor outcome 是否一致，还是出现 seed-anchor 强但 fresh-anchor 剩余空间不足？
9. 是否值得进入下一阶段 formal validation protocol？

报告必须包含硬性警告：

```text
本诊断明确区分 seed-anchor big-winner、fresh-anchor big-winner 和 path labels。
P_good / P_bad 不得解读为 P(big winner | signal)。
fresh-anchor outcome 不能替代 seed-anchor outcome。
不同 row grain 的 explanatory-power lift 不得直接比较。
```

报告还必须包含：

```text
本实验不产出 production signal。
本实验不产出 entry rule。
本实验不产出 position size。
本实验不产出 R03 risk-budget allocation。
```

## 15. 实现检查清单

- [ ] 读取并校验 R03b manifest 和 validation status。
- [ ] 读取并校验 R02 path-query manifest 和 validation status。
- [ ] 读取并校验 R02 precision manifest 和 validation status。
- [ ] 加载 R03b seed episode panel、sequence step panel、checkpoint state panel 和 timeline panel。
- [ ] 只加载 7 个 frozen single-family path CSVs。
- [ ] 为每个 clean primary fresh step 唯一映射 path-query rows 和 precision rows。
- [ ] 按第 8.2 节实现 fresh-anchor field mapping，并校验 source column / anchor。
- [ ] 使用 `signal_occurs == true` 和 `(instrument_id, trade_date, family_id)` join precision rows。
- [ ] 校验 same-offset multi-family step 的 price/path/outcome fields 一致。
- [ ] 写出 price reconciliation audit。
- [ ] 构造 `r03c_fresh_step_price_panel.parquet`。
- [ ] 构造 `r03c_checkpoint_price_state_panel.parquet`。
- [ ] 在 checkpoint panel 中写出 latest clean fresh kth/offset buckets。
- [ ] 构造 `r03c_family_set_pooling_panel.parquet`。
- [ ] 确认 `family_presence_signature` 基于 `cumulative_distinct_family_set_after_step`。
- [ ] 计算 seed entry 到 fresh signal close 的 price movement。
- [ ] 计算 seed entry 到 fresh entry 的 headline wait-return。
- [ ] 计算 wait-return buckets。
- [ ] 计算 fresh-anchor path labels。
- [ ] 分开统计 seed-anchor outcome 和 fresh-anchor outcome。
- [ ] 写出 wait price movement summary。
- [ ] 写出 fresh-count price-conditioned summary。
- [ ] 写出 kth-offset price summary。
- [ ] 写出 grouping explanatory power comparison。
- [ ] 写出 family-set pooling summary。
- [ ] 写出 family-set split stability audit。
- [ ] 写出 seed-vs-fresh anchor outcome audit。
- [ ] 写出 survival price bias audit。
- [ ] 写出 validation audit。
- [ ] 校验 missing_or_invalid wait-return rows 没有被静默删除。
- [ ] 校验 `family_role_set` 未进入 R03c V1 outputs。
- [ ] 校验 no leakage、denominator consistency、anchor separation 和 report language。
- [ ] 写出中文 final report。
- [ ] 写出 manifest 和 validation JSON。
