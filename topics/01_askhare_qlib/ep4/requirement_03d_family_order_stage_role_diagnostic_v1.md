# EP4 需求 03d: Family 出现顺序与 Stage Role 诊断 V1

## 1. 需求元信息

- 需求 id: `ep4_r03d_family_order_stage_role_diagnostic_v1`
- 简称: `r03d_family_order_stage_role_diagnostic_v1`
- 状态: 可实现的诊断型需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion3.md`
- 上游 R03b 需求: `ep4/requirement_03b_signal_sequence_big_winner_path_diagnostic_v1.md`
- 上游 R03c 需求: `ep4/requirement_03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1.md`
- 上游 R03b 输出: `ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/`
- 上游 R03c 输出: `ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/`
- 必需输出根目录: `ep4/outputs/r03d_family_order_stage_role_diagnostic_v1/`
- 必需 config 路径: `ep4/configs/r03d_family_order_stage_role_diagnostic_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r03d_family_order_stage_role_diagnostic.py`
- 必需 validator 路径: `ep4/scripts/validate_r03d_family_order_stage_role_diagnostic.py`
- 日期: 2026-05-16

## 2. 实验目的

R02/R02.1 的 single-family prior 显示 7 个 family 的 `P_good / P_bad` 有层级差异：

```text
range_breakout / volume_money / oscillator 相对更稳；
momentum_rps / price_trend / pullback_drawdown 更像 survival 后的 continuation / winner-capture evidence。
```

R03b 证明 fresh-count 与 seed-anchor path label 有强相关，但 big winner 结构较弱且存在 survival conditioning。R03c 进一步证明：

1. kth fresh step 与 offset 在 checkpoint-aligned 口径下没有明显超过 fresh-count。
2. fresh-anchor big winner 在 kth 维度上基本不改善。
3. unordered family-set pooling 在当前粒度下 denominator 过稀，不能支持稳定复用结论。

因此 R03d 不再继续挖完整 sequence pattern，也不把 fresh accumulation 解释为 entry / add signal。R03d 的目标收窄为：

```text
7 个 family 在出现顺序和 episode stage 上，是否存在稳定的 stage role？
```

必须回答的问题：

1. 哪些 family 更适合出现在 seed / early stage？
2. 哪些 family 更常在 survived 之后出现，且是否仍有 fresh-anchor 增量？
3. ordered family information 是否超过 unordered family presence、fresh-count、kth-offset 和 price-state baseline？
4. 如果某些 pair 或 family position 看起来有效，是顺序本身有效，还是只是 family set、survival 或已发生涨幅的代理？

本实验是 diagnostic，不是交易规则，不是加仓规则，不是 position sizing 实验。

## 3. 核心判断原则

R03d 必须区分三类信息：

| 信息类型 | 可以说明什么 | 不能说明什么 |
|:--|:--|:--|
| seed-anchor outcome 改善 | 该 family/order 更常出现在成功 episode 中 | 不能证明在该 step 新入场有 edge |
| fresh-anchor outcome 改善 | 该 step 之后的剩余路径更好 | 仍不能直接等同可交易 entry rule |
| price-state / wait-return 改善 | episode 已经 survive 或涨过 | 不能单独解释为 family 顺序 edge |

只有当 ordered family feature 在控制下列 baseline 后仍有稳定 lift，才允许称为“顺序增量信息”：

```text
fresh_count
kth_fresh_step_index + offset_bucket
wait_return_bucket / price_state
unordered family_presence_signature
last_added_family
seed_family_set
```

否则只能描述为：

```text
stage role proxy
survival proxy
price-state proxy
unordered family-set effect
```

R03d 的首要反事实不是“某个 ordered pattern 出现后结果如何”，而是：

```text
在相同 prefix / fresh_count / offset / price-state 下，
ordered family feature 是否比不使用 order 的 baseline 多解释 outcome？
```

因此所有 headline finding 必须同时报告：

```text
raw ordered result
parent baseline result
lift vs parent
denominator cost
split stability
```

## 4. 实验边界

允许：

- 复用 R03b seed episode、sequence step、signal timeline、path label 和 big-winner label。
- 复用 R03c fresh-step price panel、wait-return、fresh-anchor path outcome 和 price-state buckets。
- 对 7 个 frozen single-family signal 统计 family 出现位置、pair order、prefix transition、stage role。
- 同时报告 seed-anchor 与 fresh-anchor outcome。
- 按 train、validation、robustness、all 输出；`all` 只能描述，不得用于选择。
- 对同一 offset 的 multi-family step 使用 unordered set，不得强行排序。
- 把 no-fresh / failed-before-fresh episode 保留在 survival 与 denominator audit 中。

禁止：

- 不得输出 production signal、entry rule、add-position rule、reduce rule、stop rule、position size 或 risk-budget allocation。
- 不得把 seed-anchor improvement 解释为 fresh step 之后的新入场 edge。
- 不得用未来 outcome 构造 sequence bucket、family role、sparse collapse 或 stage label。
- 不得在 same-offset multi-family step 内施加任意 family 顺序。
- 不得把 same-family repeat 计入 distinct-family order progression。
- 不得只统计实际出现的 ordered pattern 而忽略“可出现但未出现”的 denominator。
- 不得用 validation / robustness outcome 选择 family、pair、prefix 或 bucket。
- 不得在线抓取数据。

## 5. 必需输入产物

所有输入必须来自本地 artifact。

R03b 主输入：

```text
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/manifests/r03b_signal_sequence_big_winner_path_manifest.json
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/manifests/r03b_signal_sequence_big_winner_path_validation.json
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_seed_episode_panel.parquet
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_sequence_step_panel.parquet
ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/cache/r03b_signal_timeline_panel.parquet
```

R03c 主输入：

```text
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/manifests/r03c_price_aware_kth_fresh_family_set_pooling_manifest.json
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/manifests/r03c_price_aware_kth_fresh_family_set_pooling_validation.json
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/cache/r03c_fresh_step_price_panel.parquet
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/cache/r03c_checkpoint_price_state_panel.parquet
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/reports/r03c_grouping_explanatory_power_comparison.csv
ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/reports/r03c_survival_price_bias_audit.csv
```

runner 必须校验：

```text
r03b_signal_sequence_big_winner_path_validation.json.validation_status == passed
r03c_price_aware_kth_fresh_family_set_pooling_validation.json.validation_status == passed
```

如果任一必需 validation 未通过或缺失，runner 不得继续生成 headline tables。最终 decision 必须为：

```text
blocked_missing_required_input
blocked_upstream_validation_failed
```

## 6. 输出目录结构

runner 必须写出：

```text
ep4/outputs/r03d_family_order_stage_role_diagnostic_v1/
  cache/
    r03d_family_order_step_panel.parquet
    r03d_order_transition_candidate_panel.parquet
    r03d_pair_order_panel.parquet
    r03d_stage_role_panel.parquet
  reports/
    r03d_input_readiness_audit.csv
    r03d_family_position_summary.csv
    r03d_stage_role_summary.csv
    r03d_next_family_given_prefix_summary.csv
    r03d_pair_order_asymmetry_summary.csv
    r03d_last_added_family_price_conditioned_summary.csv
    r03d_order_explanatory_power_comparison.csv
    r03d_order_split_stability_audit.csv
    r03d_denominator_and_survival_audit.csv
    r03d_family_order_stage_role_final_report.md
    r03d_family_order_stage_role_validation_audit.csv
  manifests/
    r03d_family_order_stage_role_manifest.json
    r03d_family_order_stage_role_validation.json
```

## 7. Family Universe 与规范化

R03d 只允许使用下面 7 个 family：

```text
range_breakout
volume_money
oscillator
volatility_band
pullback_drawdown
momentum_rps
price_trend
```

所有 family-set 字段必须规范化为：

```text
sorted unique family names joined by "|"
```

空集合使用：

```text
none
```

same-offset multi-family step 必须保留为 unordered set。例如：

```text
added_family_set = "range_breakout|volume_money"
added_family_count = 2
```

不得拆成两个有先后顺序的 row。

上游 R03b/R03c 已使用短 family 名称，不带 `single_` 前缀。runner 必须在读取输入时校验所有 family token 均属于上述 7-family universe；如果出现 `single_range_breakout` 等带前缀名称，必须 fail closed，不得静默改名。

## 8. 上游字段映射

R03d 不得重新解释 R03b/R03c 字段。下表是强制字段 lineage。

| R03d 字段 | 上游 panel | 上游字段 | 说明 |
|:--|:--|:--|:--|
| `seed_episode_id` | R03c fresh step / R03b seed | `seed_episode_id` | episode 主键 |
| `seed_trade_date` | R03c fresh step / R03b seed | `seed_trade_date` | seed signal date |
| `seed_family_set` | R03c fresh step / R03b seed | `seed_family_set` | seed same-day unordered family set |
| `seed_same_day_family_count` | R03c fresh step / R03b seed | `seed_same_day_family_count` | seed family count |
| `seed_entry_date` | R03c fresh step / R03b seed | `seed_entry_date` | seed next-open entry date |
| `seed_entry_price` | R03c fresh step / R03b seed | `seed_entry_price` | seed next-open entry price |
| `observable_failure_offset` | R03c fresh step / R03b seed | `observable_failure_offset` | R03b failure offset |
| `step_signal_date` | R03c fresh step | `step_signal_date` | clean primary fresh step date |
| `step_offset` | R03c fresh step | `step_offset` | trading-day offset from seed |
| `added_family_set` | R03c fresh step | `added_family_set` | unordered family set added at step |
| `kth_fresh_step_index_raw` | R03c fresh step | `kth_fresh_step_index_raw` | R03c recomputed kth clean fresh index |
| `kth_fresh_step_bucket` | R03c fresh step | `kth_fresh_step_bucket` | `1/2/3/4plus` |
| `kth_fresh_offset_bucket` | R03c fresh step | `kth_fresh_offset_bucket` | `t3_t5/t6_t10/t11_t20/t21_t30` |
| `wait_return_to_fresh_entry` | R03c fresh step | `wait_return_to_fresh_entry` | seed entry to fresh entry return |
| `wait_return_bucket` | R03c fresh step | `wait_return_bucket` | R03c bucket; inherited as price-state default |
| `seed_anchor_big_winner` | R03c fresh step / R03b seed | `seed_anchor_big_winner` / `big_winner_forward_h120_close_anchor` | close-anchor seed big-winner label |
| `seed_complete_h120_close_anchor_flag` | R03c fresh step / R03b seed | `seed_complete_h120_close_anchor_flag` / `complete_h120_close_anchor_flag` | seed close-anchor completeness |
| `seed_path_label` | R03c fresh step / R03b seed | `seed_path_label` / `label` | `good_path/bad_path/neutral_path/censored_or_invalid` |
| `fresh_anchor_big_winner` | R03c fresh step | `fresh_big_winner_forward_h120_close_anchor` | close-anchor fresh step big-winner label |
| `fresh_complete_h120_close_anchor_flag` | R03c fresh step | `fresh_complete_h120_close_anchor_flag` | fresh close-anchor completeness |
| `fresh_path_label` | R03c fresh step | `fresh_path_label` | fresh step path label |
| `fresh_max_gain_120d` | R03c fresh step | `fresh_max_gain_120d` | fresh next-open anchored path metric |
| `fresh_max_drawdown_120d` | R03c fresh step | `fresh_max_drawdown_120d` | fresh next-open anchored path metric |
| `fresh_close_return_t20/t60/t120` | R03c fresh step | `fresh_close_return_t20/t60/t120` | fresh next-open anchored path metric |

如果 R03c fresh step 中某个 mapped 字段缺失，runner 必须 fail closed：

```text
blocked_missing_required_input
```

## 9. 核心 Panel

### 9.1 Family Order Step Panel

`r03d_family_order_step_panel.parquet` 粒度固定为：

```text
one row per clean primary fresh step from R03c fresh step price panel
```

必须继承 R03c 中的 clean primary fresh step 定义与字段，不得重新放宽：

```text
included_in_primary_fresh_count == true
step_status in {fresh_distinct_family_step, same_offset_multi_family_step}
3 <= step_offset <= 30
step_offset < observable_failure_offset, if observable_failure_offset exists
```

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

必须新增的 order / stage fields：

```text
family_presence_signature_before_step
family_presence_signature_after_step
new_family_stage_position
stage_position_bucket
last_added_family_set
last_added_family_count
first_added_family_set
prefix_family_set_before_step
prefix_family_count_before_step
is_seed_family_reappearing
is_new_distinct_family_step
is_single_family_step
is_multi_family_step
```

字段定义：

```text
family_presence_signature_before_step = seed_family_set union all clean primary fresh added_family_set before this step
family_presence_signature_after_step = family_presence_signature_before_step union added_family_set
new_family_stage_position = cumulative_distinct_family_count_after_step
first_added_family_set = added_family_set from the first clean primary fresh step in the episode
last_added_family_set = added_family_set for the current step
is_seed_family_reappearing = added_family_set intersects seed_family_set
is_new_distinct_family_step = added_family_set has at least one token not in family_presence_signature_before_step
is_single_family_step = added_family_count == 1
is_multi_family_step = added_family_count > 1
stage_position_bucket =
  "seed" for seed rows only in stage-role panel
  "fresh_1" if kth_fresh_step_index_raw == 1
  "fresh_2" if kth_fresh_step_index_raw == 2
  "fresh_3" if kth_fresh_step_index_raw == 3
  "fresh_4plus" if kth_fresh_step_index_raw >= 4
```

R03d step panel 只包含 fresh rows；seed rows 必须在 `r03d_stage_role_panel.parquet` 中另行构造。

不得把未来才知道的 `suffix_family_set_after_step`、future max gain、future drawdown 或 future label 放入 step panel 的 grouping key。R03d 不要求输出 suffix 字段。

### 9.2 Order Transition Candidate Panel

`r03d_order_transition_candidate_panel.parquet` 用于解决“只统计实际出现 pattern”的选择偏差。粒度固定为：

```text
one row per alive episode x prefix_state x candidate_next_family
```

这里的 `alive episode` 是 prefix-observable 语义：

```text
prefix_step_index = 0:
  所有 seed episodes 都必须纳入，即使之后 failed before first clean fresh。

prefix_step_index >= 1:
  只纳入已经实际出现该 clean primary fresh prefix step 的 episode；
  R03c 已保证该 prefix step 在 observable failure 之前。
```

prefix state 必须覆盖：

```text
prefix_step_index = 0:
  seed state before any clean primary fresh step

prefix_step_index = k:
  state immediately after the kth clean primary fresh step, for k >= 1
```

对每个 prefix state 构造候选集合：

```text
candidate_next_family in 7-family universe - family_presence_signature_before_step
```

如果 `7-family universe - family_presence_signature_before_step` 为空，则该 prefix 为 exhausted prefix，不输出 candidate rows，但必须在 denominator audit 中计入 `exhausted_prefix_count`。

`family_presence_signature_before_step` 在 `prefix_step_index = 0` 时等于 `seed_family_set`；在 `prefix_step_index >= 1` 时等于第 k 个 clean primary fresh step 之后的 cumulative family set。

prefix state 的终止规则：

```text
如果存在下一根 clean primary fresh step:
  next_step = first clean primary fresh step after prefix
否则:
  next_step = null
  terminal_after_prefix = true
```

即使 episode 没有任何 clean primary fresh step，也必须输出 `prefix_step_index = 0` 的 candidate rows。

必需字段：

```text
seed_episode_id
instrument_id
split
prefix_step_index
prefix_signal_date
prefix_offset
prefix_offset_bucket
prefix_family_set
prefix_family_count
candidate_next_family
candidate_family_count_at_prefix
candidate_weight
candidate_occurs_at_next_step
candidate_occurs_within_next_5td
candidate_occurs_within_next_10td
terminal_after_prefix
terminal_reason
next_step_signal_date
next_step_offset
next_step_added_family_set
fresh_count_so_far
wait_return_bucket
price_state_bucket
seed_complete_h120_close_anchor_flag
seed_anchor_big_winner
seed_path_label
next_step_fresh_complete_h120_close_anchor_flag
next_step_fresh_anchor_big_winner
next_step_fresh_path_label
candidate_fresh_complete_h120_close_anchor_flag
candidate_fresh_anchor_big_winner
candidate_fresh_path_label
```

`candidate_occurs_at_next_step` 定义为：

```text
candidate_next_family is in next_step_added_family_set
```

`candidate_family_count_at_prefix` 与 `candidate_weight` 定义：

```text
candidate_family_count_at_prefix = count(7-family universe - prefix_family_set)
candidate_weight = 1 / candidate_family_count_at_prefix
```

同一 `seed_episode_id x prefix_step_index` 下所有 candidate rows 的 `candidate_weight` 合计必须为 1。所有 transition-candidate grain 的 occurrence rate、next-step outcome rate 和 explanatory-power lift 都必须使用 `candidate_weight`，避免同一 next-step outcome 被候选 family 数量重复放大。

`candidate_occurs_within_next_5td / 10td` 定义：

```text
candidate_next_family appears in any later clean primary fresh added_family_set
where 0 < later_step_offset - prefix_offset <= 5 or <= 10
```

如果 `prefix_step_index = 0`，则：

```text
prefix_signal_date = seed_trade_date
prefix_offset = 0
prefix_offset_bucket = "seed"
fresh_count_so_far = 0
wait_return_bucket = "seed_anchor"
price_state_bucket = "seed_anchor"
```

如果 `prefix_step_index >= 1`，则 prefix fields 来自对应第 k 个 clean primary fresh step：

```text
prefix_signal_date = step_signal_date
prefix_offset = step_offset
prefix_offset_bucket = kth_fresh_offset_bucket
fresh_count_so_far = kth_fresh_step_index_raw
wait_return_bucket = R03c wait_return_bucket at prefix step
price_state_bucket = wait_return_bucket
```

如果 episode 在 prefix 后没有下一根 clean primary fresh step，则仍需保留 candidate rows，并设置：

```text
candidate_occurs_at_next_step = false
next_step_signal_date = null
next-step fresh-anchor outcome fields = null
candidate fresh-anchor outcome fields = null
terminal_after_prefix = true
```

`terminal_reason` 取值：

```text
no_clean_fresh
no_more_clean_fresh_before_t30
failed_before_next_clean_fresh
complete_after_prefix
```

如果 `candidate_occurs_at_next_step == false` 但存在其他 family 的下一根 clean primary fresh step，则：

```text
next_step_fresh_anchor_big_winner = next step 的 fresh-anchor outcome
next_step_fresh_path_label = next step 的 fresh-anchor path label
candidate_fresh_anchor_big_winner = null
candidate_fresh_path_label = null
```

如果 `candidate_occurs_at_next_step == true`，则：

```text
candidate_fresh_anchor_big_winner = next_step_fresh_anchor_big_winner
candidate_fresh_path_label = next_step_fresh_path_label
candidate_fresh_complete_h120_close_anchor_flag = next_step_fresh_complete_h120_close_anchor_flag
```

`next_step_*` 字段表示“下一根实际 fresh step 的 outcome”。`candidate_*` 字段只在 candidate family 实际出现在下一根 clean primary fresh step 时有意义。final report 不得把 non-occurrence row 的 `next_step_*` outcome 解读为 candidate family 自身 outcome。

这样才能比较“出现某个 next family”和“没有出现”的差异。

### 9.3 Pair Order Panel

`r03d_pair_order_panel.parquet` 用于 pair order asymmetry。粒度固定为：

```text
one row per seed_episode_id x unordered_family_pair
```

只考虑在 seed 或 clean primary fresh progression 中都曾出现过的两个 family。必需字段：

```text
seed_episode_id
instrument_id
split
family_a
family_b
unordered_pair_key
pair_order_key
family_a_first_stage
family_b_first_stage
family_a_first_offset
family_b_first_offset
same_offset_pair_flag
pair_order_observable
pair_completion_offset
pair_completion_wait_return_bucket
seed_complete_h120_close_anchor_flag
seed_anchor_big_winner
seed_path_label
pair_completion_fresh_complete_h120_close_anchor_flag
pair_completion_fresh_anchor_big_winner
pair_completion_fresh_path_label
```

`family_a` 与 `family_b` 必须按 family name 字典序确定：

```text
family_a < family_b
unordered_pair_key = family_a + "|" + family_b
```

`pair_order_key` 定义：

```text
"A_before_B" if family_a_first_offset < family_b_first_offset
"B_before_A" if family_b_first_offset < family_a_first_offset
"same_offset_unordered" if family_a_first_offset == family_b_first_offset
```

same-offset pair 不得归入任一方向，只能单独报告。

pair order panel 是 completed-pair conditional panel，只能回答“两个 family 都出现时，先后顺序是否有差异”。它不能回答“某个 pair 是否会出现”，也不能替代 transition candidate denominator。

### 9.4 Stage Role Panel

`r03d_stage_role_panel.parquet` 粒度固定为：

```text
one row per seed_episode_id x family
```

每个 family 在一个 seed episode 中最多出现一次，取首次出现的 stage：

```text
seed
fresh_1
fresh_2
fresh_3
fresh_4plus
not_observed
```

必需字段：

```text
seed_episode_id
instrument_id
split
family
first_observed_stage
first_observed_offset
first_observed_signal_date
first_observed_as_seed
first_observed_as_fresh
first_observed_after_wait_return_bucket
first_observed_price_state_bucket
first_observed_wait_return_to_entry
seed_complete_h120_close_anchor_flag
seed_anchor_big_winner
seed_path_label
fresh_complete_h120_close_anchor_flag_if_observed_as_fresh
fresh_anchor_big_winner_if_observed_as_fresh
fresh_path_label_if_observed_as_fresh
```

`not_observed` rows 必须保留，用于 denominator audit 和 stage role baseline。

字段规则：

```text
first_observed_stage = seed:
  first_observed_offset = 0
  first_observed_signal_date = seed_trade_date
  first_observed_after_wait_return_bucket = "seed_anchor"
  first_observed_price_state_bucket = "seed_anchor"
  first_observed_wait_return_to_entry = 0
  fresh-anchor fields = null

first_observed_stage starts with fresh:
  fields come from the first fresh step where family appears in added_family_set

first_observed_stage = not_observed:
  first_observed_offset = null
  first_observed_signal_date = null
  first_observed_after_wait_return_bucket = "not_observed"
  first_observed_price_state_bucket = "not_observed"
  first_observed_wait_return_to_entry = null
  fresh-anchor fields = null
```

## 10. Price-State 与 Outcome 字段

R03d 必须继承 R03c 的 price-state 口径。

必需 price fields：

```text
wait_return_to_fresh_entry
wait_return_bucket
kth_fresh_offset_bucket
fresh_count_so_far
price_state_bucket
```

`fresh_count_so_far` 定义：

```text
prefix_step_index for transition candidate rows
kth_fresh_step_index_raw for step rows
0 for seed-stage rows
```

`price_state_bucket` 默认等于 R03c 的 `wait_return_bucket`，允许取值固定为：

```text
seed_anchor
not_observed
down_or_flat
up_0_5pct
up_5_10pct
up_10_20pct
up_gt_20pct
missing_or_invalid
```

R03d 不要求重建 seed 到 step 之间是否盘中触发 `+10%` 或 `-5%` 的高低点路径，因为 R03b/R03c 当前输入没有逐日 high/low path。不得凭 `wait_return_to_fresh_entry` 推断 `seed_to_step_hit_plus10_flag` 或 `seed_to_step_hit_minus5_flag`。

必需 seed-anchor outcome：

```text
seed_anchor_big_winner
seed_complete_h120_close_anchor_flag
seed_path_label
seed_P_good_flag
seed_P_bad_flag
observable_failure_offset
```

必需 fresh-anchor outcome：

```text
fresh_anchor_big_winner
fresh_complete_h120_close_anchor_flag
fresh_path_label
fresh_P_good_flag
fresh_P_bad_flag
fresh_max_gain_120d
fresh_max_drawdown_120d
fresh_close_return_t20
fresh_close_return_t60
fresh_close_return_t120
fresh_hit_plus10_before_minus5
fresh_early_failure_flag
fresh_path_quality_flag
```

fresh-anchor outcome 只对实际 fresh step 或 pair completion step 有意义；对 `not_observed` / terminal candidate rows 必须为 null，不得向前填充。

所有会参与 rate 汇总的 row-level panel 必须携带可复核的 completeness flags：

```text
r03d_family_order_step_panel:
  seed_complete_h120_close_anchor_flag
  fresh_complete_h120_close_anchor_flag

r03d_order_transition_candidate_panel:
  seed_complete_h120_close_anchor_flag
  next_step_fresh_complete_h120_close_anchor_flag
  candidate_fresh_complete_h120_close_anchor_flag

r03d_pair_order_panel:
  seed_complete_h120_close_anchor_flag
  pair_completion_fresh_complete_h120_close_anchor_flag

r03d_stage_role_panel:
  seed_complete_h120_close_anchor_flag
  fresh_complete_h120_close_anchor_flag_if_observed_as_fresh
```

validator 必须能仅依赖 R03d 输出 panel 重算所有 summary 中的 denominator 和 rate，不得依赖 runner 内存态。

## 11. 聚合口径

所有 summary table 必须使用同一套 rate 计算规则。

seed-anchor big-winner：

```text
denominator = rows where seed_complete_h120_close_anchor_flag == true
count = rows where seed_anchor_big_winner == true
rate = count / denominator
```

fresh-anchor big-winner：

```text
denominator = rows where fresh_complete_h120_close_anchor_flag == true
count = rows where fresh_anchor_big_winner == true
rate = count / denominator
```

path label：

```text
path_denominator = rows where label in {good_path, bad_path, neutral_path}
P_good = good_path_count / path_denominator
P_bad = bad_path_count / path_denominator
P_neutral = neutral_path_count / path_denominator
```

`censored_or_invalid` 不得进入 `P_good / P_bad` denominator，但必须在 summary 中以 `censored_or_invalid_count` 或 audit 表保留。

transition-candidate grain 的特殊聚合规则：

```text
candidate_occurrence_rate =
  sum(candidate_weight * candidate_occurs_at_next_step) / sum(candidate_weight)

next_step_fresh_anchor_big_winner_rate_weighted =
  sum(candidate_weight * next_step_fresh_anchor_big_winner
      where next_step_fresh_complete_h120_close_anchor_flag == true)
  / sum(candidate_weight where next_step_fresh_complete_h120_close_anchor_flag == true)

candidate_fresh_anchor_big_winner_rate =
  sum(candidate_weight * candidate_fresh_anchor_big_winner
      where candidate_fresh_complete_h120_close_anchor_flag == true)
  / sum(candidate_weight where candidate_fresh_complete_h120_close_anchor_flag == true)
```

transition-candidate 的 `fresh_anchor_big_winner_rate` 在 explanatory power comparison 中必须指向 weighted `next_step_fresh_anchor_big_winner_rate_weighted`。`candidate_fresh_anchor_big_winner_rate` 只能用于描述 candidate 实际命中下一步时的 path，不得用于 `candidate_occurs_at_next_step == false` rows。

`unique_signal_date_count` 统一定义：

```text
seed stage:
  count distinct seed_trade_date
fresh stage:
  count distinct first_observed_signal_date or step_signal_date
not_observed:
  count distinct seed_trade_date
transition candidate:
  count distinct next_step_signal_date when present, otherwise seed_trade_date
```

所有 `all` split 只能描述，不得用于 sparse bucket selection、candidate selection 或 final decision。

## 12. 必需 Summary Tables

### 12.1 Family Position Summary

输出：`r03d_family_position_summary.csv`

粒度：

```text
split x family x first_observed_stage
```

必需指标：

```text
episode_count
unique_instrument_count
unique_signal_date_count
seed_anchor_big_winner_denominator
seed_anchor_big_winner_rate
seed_P_good
seed_P_bad
fresh_anchor_big_winner_denominator
fresh_anchor_big_winner_rate
fresh_P_good
fresh_P_bad
wait_return_p50
fresh_max_gain_120d_p50
fresh_max_drawdown_120d_p50
sample_sufficiency_status
```

用途：判断某个 family 出现在 seed / fresh_1 / fresh_2 / fresh_3 / fresh_4plus 时，outcome 是否存在 stage role 差异。

`first_observed_stage in {seed, not_observed}` 时 fresh-anchor denominator 可能为 0；对应 fresh-anchor rate 必须为 null，不得填 0。

### 12.2 Stage Role Summary

输出：`r03d_stage_role_summary.csv`

粒度：

```text
split x family x stage_role_candidate
```

`stage_role_candidate` 至少包括：

```text
probe_candidate
early_confirmation
late_continuation
lagging_price_state_proxy
not_supported
```

runner 不得用 outcome 直接分配 role。role assignment 必须先由 observable stage/price/order features 生成 candidate，再由 outcome 做 audit。

推荐规则：

```text
probe_candidate:
  first_observed_stage == seed
  or (
    first_observed_stage == fresh_1
    and median(first_observed_wait_return_to_entry) <= 0.05
  )

early_confirmation:
  first_observed_stage in {fresh_1, fresh_2}
  and 0.00 <= median(first_observed_wait_return_to_entry) <= 0.10

late_continuation:
  first_observed_stage in {fresh_2, fresh_3, fresh_4plus}
  and median(first_observed_wait_return_to_entry) > 0.05

lagging_price_state_proxy:
  median(first_observed_wait_return_to_entry) > 0.10
  or share(first_observed_price_state_bucket in {up_10_20pct, up_gt_20pct})
     >= stage_role_dominant_price_bucket_share
```

final report 必须说明这些 role 是 descriptive candidate，不是交易角色。

如果同一 `split x family` 同时满足多个 role candidate，按以下优先级分配：

```text
lagging_price_state_proxy
late_continuation
early_confirmation
probe_candidate
not_supported
```

role candidate 的分配只允许使用 `first_observed_stage`、`wait_return_bucket`、`price_state_bucket`、denominator 和 occurrence share，不得使用 outcome。

### 12.3 Next Family Given Prefix Summary

输出：`r03d_next_family_given_prefix_summary.csv`

粒度：

```text
split x prefix_family_count_bucket x prefix_family_set_bucket x candidate_next_family x candidate_occurs_at_next_step
```

`prefix_family_set_bucket` 规则：

```text
exact set if train denominator >= min_exact_prefix_denominator
"other_sparse_prefix" otherwise
```

prefix sparse bucket 必须只用 train split 的 denominator 冻结；validation、robustness、all 必须复用 train 冻结后的 exact/sparse mapping。不得因为 validation 或 robustness denominator 充足而把 train-sparse prefix 展开。

必需指标：

```text
candidate_row_count
candidate_weight_sum
seed_episode_count
candidate_occurrence_rate
seed_anchor_big_winner_rate
seed_P_good
seed_P_bad
next_step_fresh_anchor_big_winner_rate_weighted
next_step_fresh_P_good_weighted
next_step_fresh_P_bad_weighted
candidate_fresh_anchor_big_winner_rate
candidate_fresh_P_good
candidate_fresh_P_bad
wait_return_p50
sample_sufficiency_status
```

用途：判断在相同 prefix 下，下一个出现哪个 family 是否有增量；同时保留未出现的 candidate rows。`next_step_*` 指下一根实际 fresh step 的 weighted outcome，`candidate_*` 只在 candidate family 实际成为下一根 fresh step 时有 denominator。

### 12.4 Pair Order Asymmetry Summary

输出：`r03d_pair_order_asymmetry_summary.csv`

粒度：

```text
split x unordered_pair_key x pair_order_key
```

必需指标：

```text
episode_count
pair_completion_count
same_offset_pair_count
seed_anchor_big_winner_rate
seed_P_good
seed_P_bad
pair_completion_fresh_anchor_big_winner_rate
pair_completion_fresh_P_good
pair_completion_fresh_P_bad
pair_completion_wait_return_p50
sample_sufficiency_status
```

必须另行输出 pair asymmetry 字段：

```text
opposite_order_episode_count
seed_anchor_big_winner_rate_diff_vs_opposite_order
seed_P_good_diff_vs_opposite_order
fresh_anchor_big_winner_rate_diff_vs_opposite_order
fresh_P_good_diff_vs_opposite_order
asymmetry_status
```

`asymmetry_status`：

```text
insufficient_pair_denominator
same_offset_only
unstable_across_split
no_material_asymmetry
candidate_order_asymmetry
```

`candidate_order_asymmetry` 只允许在 validation 和 robustness 两个 split 的方向一致，且两个方向都满足 `min_pair_episode_count` 时输出。

### 12.5 Last Added Family Price-Conditioned Summary

输出：`r03d_last_added_family_price_conditioned_summary.csv`

粒度：

```text
split x kth_fresh_step_bucket x kth_fresh_offset_bucket x wait_return_bucket x last_added_family_set
```

必需指标：

```text
fresh_step_count
seed_episode_count
unique_instrument_count
unique_signal_date_count
seed_anchor_big_winner_rate
seed_P_good
seed_P_bad
fresh_anchor_big_winner_rate
fresh_P_good
fresh_P_bad
fresh_max_gain_120d_p50
fresh_max_drawdown_120d_p50
sample_sufficiency_status
```

用途：在同一 kth/offset/price-state 下，看 last added family 是否仍有解释力。

### 12.6 Order Explanatory Power Comparison

输出：`r03d_order_explanatory_power_comparison.csv`

必须比较下列 grouping schemes：

```text
fresh_step_base
fresh_count
kth_offset
kth_offset_price_state
family_presence_after_step
kth_offset_price_state_plus_family_presence
kth_offset_price_state_plus_last_added_family
seed_family_position_base
family_position
completed_pair_base
unordered_pair
pair_order
pair_wait_state
pair_wait_state_plus_order
transition_prefix_base
unordered_prefix_presence
ordered_prefix
price_state_plus_unordered_prefix
price_state_plus_ordered_prefix
```

grouping scheme 的 grain、key 和 parent 固定如下：

| grouping_scheme | row_grain | grouping_key | parent_grouping_scheme |
|:--|:--|:--|:--|
| `fresh_step_base` | `fresh_step` | `all_fresh_steps` | `none` |
| `fresh_count` | `fresh_step` | `kth_fresh_step_bucket` | `fresh_step_base` |
| `kth_offset` | `fresh_step` | `kth_fresh_step_bucket + kth_fresh_offset_bucket` | `fresh_count` |
| `kth_offset_price_state` | `fresh_step` | `kth_fresh_step_bucket + kth_fresh_offset_bucket + wait_return_bucket` | `kth_offset` |
| `family_presence_after_step` | `fresh_step` | `family_presence_signature_after_step_bucket` | `fresh_step_base` |
| `kth_offset_price_state_plus_family_presence` | `fresh_step` | `kth_fresh_step_bucket + kth_fresh_offset_bucket + wait_return_bucket + family_presence_signature_after_step_bucket` | `kth_offset_price_state` |
| `kth_offset_price_state_plus_last_added_family` | `fresh_step` | `kth_fresh_step_bucket + kth_fresh_offset_bucket + wait_return_bucket + last_added_family_set_bucket` | `kth_offset_price_state` |
| `seed_family_position_base` | `seed_episode_family` | `family` | `none` |
| `family_position` | `seed_episode_family` | `family + first_observed_stage` | `seed_family_position_base` |
| `completed_pair_base` | `completed_pair` | `all_completed_pairs` | `none` |
| `unordered_pair` | `completed_pair` | `unordered_pair_key` | `completed_pair_base` |
| `pair_order` | `completed_pair` | `unordered_pair_key + pair_order_key` | `unordered_pair` |
| `pair_wait_state` | `completed_pair` | `unordered_pair_key + pair_completion_wait_return_bucket` | `unordered_pair` |
| `pair_wait_state_plus_order` | `completed_pair` | `unordered_pair_key + pair_completion_wait_return_bucket + pair_order_key` | `pair_wait_state` |
| `transition_prefix_base` | `transition_candidate` | `prefix_family_count_bucket` | `none` |
| `unordered_prefix_presence` | `transition_candidate` | `prefix_family_count_bucket + prefix_family_set_bucket` | `transition_prefix_base` |
| `ordered_prefix` | `transition_candidate` | `prefix_family_count_bucket + prefix_family_set_bucket + candidate_next_family + candidate_occurs_at_next_step` | `unordered_prefix_presence` |
| `price_state_plus_unordered_prefix` | `transition_candidate` | `price_state_bucket + prefix_family_count_bucket + prefix_family_set_bucket` | `unordered_prefix_presence` |
| `price_state_plus_ordered_prefix` | `transition_candidate` | `price_state_bucket + prefix_family_count_bucket + prefix_family_set_bucket + candidate_next_family + candidate_occurs_at_next_step` | `price_state_plus_unordered_prefix` |

runner 必须在 comparison table 中输出 parent rows，不能只输出 child rows。`none` parent 的 base rows 只用于被 child 引用，不参与 order-edge 结论。

必需字段：

```text
split
grouping_scheme
row_grain
outcome
bucket_count
sufficient_bucket_count
covered_episode_count
covered_fresh_step_count
parent_grouping_scheme
weighted_abs_lift_vs_parent
weighted_signed_lift_vs_parent
max_abs_lift_vs_parent
median_abs_lift_vs_parent
sample_sufficiency_status
interpretability_status
```

outcome 至少包括：

```text
seed_anchor_big_winner_rate
seed_P_good_minus_P_bad
fresh_anchor_big_winner_rate
fresh_P_good_minus_P_bad
fresh_max_gain_120d_p50
fresh_max_drawdown_120d_p50
```

对 `row_grain = transition_candidate` 的 rows：

```text
fresh_anchor_big_winner_rate = next_step_fresh_anchor_big_winner_rate_weighted
fresh_P_good_minus_P_bad = next_step_fresh_P_good_weighted - next_step_fresh_P_bad_weighted
denominator / weights must use candidate_weight
```

不得在 `transition_candidate` explanatory power 中使用 `candidate_fresh_*` 字段，因为 `candidate_occurs_at_next_step == false` rows 没有 candidate-specific fresh-anchor outcome。

比较规则：

- 不同 row grain 的 `weighted_abs_lift_vs_parent` 不得直接排名。
- `family_position` 只能与 `seed_family_position_base` 比较。
- `pair_order` 只能与同一个 `unordered_pair_key` 的 `unordered_pair` parent 比较。
- `pair_wait_state_plus_order` 必须与同一个 `unordered_pair_key + pair_completion_wait_return_bucket` 的 `pair_wait_state` parent 比较。
- `ordered_prefix` 必须与同一个 `prefix_family_count_bucket + prefix_family_set_bucket` 的 `unordered_prefix_presence` parent 比较。
- `price_state_plus_ordered_prefix` 必须与同一个 `price_state_bucket + prefix_family_count_bucket + prefix_family_set_bucket` 的 `price_state_plus_unordered_prefix` parent 比较。
- `kth_offset_price_state_plus_last_added_family` 和 `kth_offset_price_state_plus_family_presence` 必须与同一个 `kth_fresh_step_bucket + kth_fresh_offset_bucket + wait_return_bucket` 的 `kth_offset_price_state` parent 比较。
- 如果 ordered scheme bucket 数显著增加但 sufficient bucket 比例下降，final report 必须明确标注 denominator cost。

`weighted_abs_lift_vs_parent` 计算规则：

```text
For each child bucket:
  lift = child_outcome_value - parent_outcome_value
  weight = child_denominator / sum(child_denominator across comparable child buckets)
weighted_abs_lift_vs_parent = sum(weight * abs(lift))
weighted_signed_lift_vs_parent = sum(weight * lift)
```

当 child 与 parent grain 不一致时，必须先 reduce 到相同 grain 后再计算 lift；无法 reduce 时 `interpretability_status = non_comparable_grain`。

### 12.7 Split Stability Audit

输出：`r03d_order_split_stability_audit.csv`

粒度：

```text
grouping_scheme x grouping_key x outcome
```

必需字段：

```text
train_denominator
validation_denominator
robustness_denominator
train_value
validation_value
robustness_value
validation_lift_vs_parent
robustness_lift_vs_parent
lift_sign_consistent
lift_magnitude_stable
sample_sufficiency_status
stability_status
```

`stability_status`：

```text
stable_descriptive
direction_only
unstable
denominator_thin
split_missing
```

任何 final report 中被点名的 family/order candidate，必须在该表中有对应 stability row。

### 12.8 Denominator And Survival Audit

输出：`r03d_denominator_and_survival_audit.csv`

必需指标：

```text
split
seed_episode_count
no_clean_fresh_episode_count
failed_before_first_clean_fresh_count
first_clean_fresh_episode_count
stage_role_not_observed_row_count
transition_candidate_row_count
actual_transition_row_count
same_offset_multi_family_step_count
same_offset_multi_family_step_rate
ordered_pair_observable_count
same_offset_pair_count
terminal_after_prefix_count
exhausted_prefix_count
```

final report 必须明确说明：

```text
survival conditioning 可以是 probe lifecycle 的一部分；
但 order/family edge 必须在 survived 条件下提供 fresh-anchor 或 remaining-path 增量，才可被视作升级信息。
```

## 13. Sample Sufficiency 与稀疏处理

config 必须包含：

```yaml
min_seed_episode_count: 80
min_fresh_step_count: 80
min_pair_episode_count: 60
min_split_denominator: 30
min_unique_instrument_count: 20
min_unique_signal_date_count: 20
min_exact_prefix_denominator: 120
min_sufficient_bucket_ratio: 0.20
min_material_rate_lift_pp: 0.02
min_material_pgood_minus_pbad_lift_pp: 0.05
max_child_to_parent_bucket_multiplier: 3.0
stage_role_dominant_price_bucket_share: 0.50
```

默认 `sample_sufficiency_status`：

```text
sufficient
thin_episode_denominator
thin_fresh_step_denominator
thin_pair_denominator
thin_unique_instrument
thin_unique_signal_date
split_missing
```

稀疏 prefix / pair 不得删除，只能折叠到：

```text
other_sparse_prefix
other_sparse_pair
```

但折叠不得使用 outcome。

稀疏折叠规则：

```text
prefix / ordered_prefix:
  用 train split 的 prefix denominator 决定 exact vs other_sparse_prefix。

last_added_family_set:
  用 train split 的 fresh_step_count 决定 exact vs other_sparse_last_added_family。

unordered_pair_key:
  用 train split 的 completed pair denominator 决定 exact vs other_sparse_pair。
```

validation、robustness、all 必须复用 train 冻结后的 mapping。若 train 中不存在但 validation/robustness 中出现的新 key，必须归入对应 `other_sparse_*` bucket。

`insufficient_denominator` 硬触发条件：

```text
如果 validation 或 robustness 任一 split 中，
ordered_prefix / pair_order / price_state_plus_ordered_prefix 任一关键 scheme 的
sufficient_bucket_count / bucket_count < min_sufficient_bucket_ratio，
且该 scheme 被用于 final report 的 order-edge 判断，
则 final_decision 必须为 insufficient_denominator。
```

如果所有 order schemes 都只作为 descriptive-only 输出，不进入 final order-edge 判断，则可不触发 `insufficient_denominator`，但 final report 必须显式写明 denominator 不支持 order-edge 结论。

## 14. Validation 与 Fail-Closed 条件

validator 必须检查：

1. 所有必需输入存在且 validation passed。
2. R03d seed episode 数与 R03b seed episode 数完全一致。
3. R03d fresh step 数与 R03c fresh step price panel 行数完全一致。
4. 7-family universe 没有未知 family。
5. same-offset multi-family step 没有被拆成任意顺序。
6. `r03d_stage_role_panel` 总行数等于 `seed_episode_count x 7`。
7. `not_observed` stage rows 已保留，数量等于 `seed_episode_count x 7 - observed_family_rows`。
8. transition candidate panel 包含 `candidate_occurs_at_next_step == false` rows。
9. 没有 clean fresh 且 prefix 未 exhausted 的 episode 也有 `prefix_step_index = 0` candidate rows。
10. 每个存在 candidate rows 的 `seed_episode_id x prefix_step_index` 下 `sum(candidate_weight) == 1`，容差不超过 `1e-9`；exhausted prefix 必须只出现在 denominator audit，不得输出 zero-weight candidate row。
11. `candidate_occurs_at_next_step == false` rows 的 `candidate_fresh_*` fields 必须为 null。
12. 所有 row-level panel 都包含第 10 节要求的 completeness flags，且 summary denominator 可由 panel 重算。
13. seed-anchor 与 fresh-anchor outcome 没有混用。
14. `price_state_bucket` 只包含第 10 节允许的枚举值。
15. stage-role candidate assignment 只使用 observable fields，且 `stage_role_dominant_price_bucket_share` 阈值生效。
16. sparse bucket mapping 只由 train denominator 冻结，validation/robustness 没有自行展开 train-sparse key。
17. explanatory power comparison 中每个 child row 都存在 parent row，或 `interpretability_status = non_comparable_grain`。
18. ordered scheme 的 grouping key 不包含未来 outcome 字段或未来 signal suffix 字段。
19. final report 点名的 candidate 都能在 split stability audit 中找到。

若任一硬校验失败，validation status 必须为 failed，decision 必须为：

```text
blocked_validation_failed
```

## 15. Final Report 必答问题

`r03d_family_order_stage_role_final_report.md` 必须用中文回答：

1. 7 个 family 是否存在稳定 stage role？
2. 哪些 family 更像 seed/probe candidate？证据来自 seed-anchor 还是 fresh-anchor？
3. 哪些 family 更像 late continuation / price-state proxy？
4. pair order 是否有方向不对称？是否超过 unordered pair？
5. ordered prefix 是否超过 unordered family presence？
6. 在控制 `fresh_count + kth_offset + wait_return_bucket` 后，last added family 是否仍有增量？是否只属于 `last_added_family_incremental` 而非 order edge？
7. 如果顺序信息没有增量，是否应正式停止 sequence-order path？
8. 哪些发现只能用于 hold-state / exit-state，不得用于 entry/add？

必须包含结论段：

```text
R03d 是否支持继续研究 family order？
R03d 是否只支持 family stage-role descriptive usage？
R03d 是否建议把后续 budget 转向 single-family entry timing？
prefix_order_incremental / pair_order_incremental / last_added_family_incremental 各自是什么状态？
```

## 16. 决策状态

最终 manifest 必须给出一个 `final_decision`：

```text
supported_order_incremental_edge
stage_role_only_no_order_increment
price_state_proxy_only
insufficient_denominator
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_validation_failed
```

最终 manifest 还必须给出 `decision_components`：

```text
prefix_order_incremental:
  supported | no_increment | price_state_proxy | insufficient_denominator

pair_order_incremental:
  supported | no_increment | price_state_proxy | insufficient_denominator

last_added_family_incremental:
  supported | no_increment | price_state_proxy | insufficient_denominator
```

判定规则：

- `prefix_order_incremental = supported` 只有在同时满足下列条件时才允许：
  - validation 与 robustness 方向一致；
  - `ordered_prefix` 相对 `unordered_prefix_presence` 的 fresh-anchor lift 达到 material threshold；
  - `price_state_plus_ordered_prefix` 相对 `price_state_plus_unordered_prefix` 的 fresh-anchor lift 仍达到 material threshold；
  - sufficient bucket 比例不低于 `min_sufficient_bucket_ratio`；
  - child bucket 数不超过 parent bucket 数的 `max_child_to_parent_bucket_multiplier`，除非 final report 明确标注 denominator cost 且 validation/robustness 都仍 sufficient。
- `pair_order_incremental = supported` 只有在同时满足下列条件时才允许：
  - validation 与 robustness 方向一致；
  - `pair_order` 相对 `unordered_pair` 的 fresh-anchor lift 达到 material threshold；
  - `pair_wait_state_plus_order` 相对 `pair_wait_state` 的 fresh-anchor lift 仍达到 material threshold；
  - sufficient bucket 比例不低于 `min_sufficient_bucket_ratio`。
- `last_added_family_incremental = supported` 只有在同时满足下列条件时才允许：
  - validation 与 robustness 方向一致；
  - `kth_offset_price_state_plus_last_added_family` 相对 `kth_offset_price_state` 的 fresh-anchor lift 达到 material threshold；
  - sufficient bucket 比例不低于 `min_sufficient_bucket_ratio`。
- `supported_order_incremental_edge` 只有在 `prefix_order_incremental` 或 `pair_order_incremental` 至少一个为 `supported` 时才允许。
- `stage_role_only_no_order_increment` 用于 family 出现 stage 有描述性结构，但 ordered feature 未超过 baseline。
- `price_state_proxy_only` 用于 family/order lift 主要被 wait-return 或 price-state 解释。
- `insufficient_denominator` 用于 ordered/pair/prefix denominator 无法支持判断。

优先级：

```text
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_validation_failed
insufficient_denominator
supported_order_incremental_edge
price_state_proxy_only
stage_role_only_no_order_increment
```

如果 `family_position` 有 stable descriptive structure，但所有 ordered schemes 均未超过 parent，则必须选择 `stage_role_only_no_order_increment`，不得选择 `supported_order_incremental_edge`。

如果 ordered schemes 的 raw lift 存在，但相对 `kth_offset_price_state`、`pair_wait_state` 或 `price_state_plus_unordered_prefix` parent 的 lift 低于 material threshold，则对应 decision component 必须为 `price_state_proxy`。如果所有 non-insufficient order components 都是 `price_state_proxy`，最终 `final_decision` 必须为 `price_state_proxy_only`。

## 17. 推荐默认解释口径

R03d 默认应以保守方式解释：

```text
seed-anchor improvement = episode selection / survival / state evidence
fresh-anchor improvement = possible remaining-path information
ordered > unordered = possible order information
ordered <= unordered = no order information
ordered <= kth_offset_price_state / pair_wait_state / price_state_plus_unordered_prefix = price-state proxy
```

除非 `supported_order_incremental_edge` 成立，否则不得把 family order 写成可交易 alpha。
