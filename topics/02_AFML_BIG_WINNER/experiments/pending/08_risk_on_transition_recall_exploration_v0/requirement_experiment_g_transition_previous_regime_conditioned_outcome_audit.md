# 需求：Experiment G - Previous-Regime Conditioned Transition Outcome Audit

## 1. 背景

Experiment F 已经证明，直接把 `transition` 当作一个独立第三态去做 deterministic taxonomy 或 120d 自动分类并不稳：

1. default taxonomy 中 `transition_boundary_or_mixed` 占比过高，train / robustness 中约 80% 的 transition events 都落入 boundary。
2. robustness split 中 `transition_recovery` core denominator 缺失，无法证明 recovery / deterioration 两个核心子态都能 out-of-time 复现。
3. 120d KMeans 虽然选出 `k=3`，但所有 cluster 都退化成 `auto_boundary_or_mixed_like`，block stability 失败。
4. transition 是 `risk_on` / `risk_off` 之外的 residual bucket，不是正向定义的单一状态。

进一步从三状态 regime 时间轴观察，`transition` 与前一个 regime 有明显关系。按 SH000985 重建的连续 regime segment 统计：

| transition 前后状态 | segment_n | segment_share | trading_day_share | 直觉解释 |
| --- | ---: | ---: | ---: | --- |
| `risk_on -> transition -> risk_on` | 59 | 51.8% | 50.8% | risk_on 中途震荡 / 休整后回到 risk_on |
| `risk_off -> transition -> risk_off` | 24 | 21.1% | 15.4% | risk_off 中途反弹 / 震荡后继续 risk_off |
| `risk_off -> transition -> risk_on` | 16 | 14.0% | 20.2% | risk_off 修复成 risk_on，即 recovery conversion |
| `risk_on -> transition -> risk_off` | 14 | 12.3% | 13.5% | risk_on 恶化成 risk_off，即 deterioration conversion |

这些方向级 conversion segment 数很少，尤其在 OOS / robustness 上更薄。因此本实验的 supported claim 只能建立在聚合层面的：

```text
transition_continuation vs transition_conversion
```

方向级 readout，例如 `risk_off_to_risk_on_recovery_conversion` 与 `risk_on_to_risk_off_deterioration_conversion`，只能作为 diagnostic。即使某个方向的 event_n 很大，也不得因为少数长 segment 的事件集中而升级为 supported evidence。

因此，当前更合理的问题不是“能否训练一个 transition 子状态模型”，而是：

```text
transition 是否主要是 previous regime 的缓冲区？
如果按 previous regime 条件化，continuation 与 conversion 的 recall / cost / density 是否表现不同？
```

本实验接受一个现实约束：`conversion` / `continuation` 的最终判断依赖未来 `next_non_transition_regime`，严格 PIT 时点可能无法准确知道。本实验不把未来 outcome 当作特征，也不训练预测模型；它只把 outcome 作为 ex-post readout label，用来验证 previous-regime conditioned transition 是否是一个更好的分析框架。

## 2. Primary Question

Experiment G 必须回答：

```text
Can transition be more usefully audited as a previous-regime conditioned
buffer state, where PIT assignment uses only the previous non-transition
regime, and continuation/conversion is evaluated only as an ex-post outcome?
```

中文等价问题：

```text
是否可以不训练模型，仅根据 transition 之前的非 transition regime，把 transition
拆成 transition_from_risk_on / transition_from_risk_off，并用未来 next regime 作为
readout，审计哪些 transition 是前态延续，哪些 transition 是 regime 转化？
```

## 3. 范围

Experiment G 覆盖：

1. 三状态 market regime segment 构造：`risk_on` / `transition` / `risk_off`。
2. transition segment 的 previous non-transition regime 绑定。
3. PIT taxonomy：

```text
transition_from_risk_on
transition_from_risk_off
transition_from_unknown_or_censored
```

4. ex-post outcome label：

```text
transition_continuation
transition_conversion
transition_outcome_pending_or_censored
```

5. previous-regime conditioned readout：
   - segment count / trading-day count / calendar-day count。
   - event composition。
   - target episode denominator。
   - E1 / R-core / R6 / T4 / T7 recall。
   - E1-missed capture。
   - fast-fail / false-repair / big-winner quality。
   - density / overlap。
6. 轻量 grid search：只搜索 deterministic rule 参数，不训练模型。

Experiment G 不覆盖：

1. supervised model / classifier / ranker / rejector 训练。
2. KMeans / kNN / elbow / learned taxonomy。
3. 新 event family rediscovery。
4. trading strategy、portfolio simulation、position sizing。
5. 使用 `next_regime` 或未来 label 做 PIT assignment。

最终输出只能是 previous-regime conditioned audit / recommendation，不能输出 direct-entry support。

## 4. 核心定义

### 4.1 Regime reconstruction

默认使用 SH000985 重建三状态 regime：

```text
market_trend_60d = close_t / close_{t-60} - 1
market_drawdown_120d = close_t / rolling_high_120d(min_periods=60) - 1

risk_on  = market_trend_60d >= 0 且 market_drawdown_120d > -10%
risk_off = market_trend_60d < 0 且 market_drawdown_120d <= -10%
transition = 其余完整观测
component_missing = market_trend_60d 或 market_drawdown_120d 缺失
```

`component_missing` 不得参与 readout denominator。

### 4.2 Segment construction

按交易日排序后，将连续相同 `regime` 合并为 segment：

```text
segment_id = cumulative count of regime changes
segment_start_date = first date in segment
segment_end_date = last date in segment
segment_trading_day_n = number of trading days in segment
segment_calendar_day_n = segment_end_date - segment_start_date + 1
```

若 segment 跨年，仍视为一个连续 segment；图形可以按年拆行显示，但表格必须保留原始连续 segment。

### 4.3 Transition universe 与 binding policy

G 必须明确区分两个 transition universe：

| universe | 定义 | 用途 |
| --- | --- | --- |
| `reconstructed_transition_universe` | 用 SH000985 按 §4.1 重建后，`event_t0_date` 落在 reconstructed `transition` segment 内的 candidate events | 主读数 universe |
| `published_transition_universe` | 上游 artifacts 中 `market_regime_bucket = transition` 的 events / membership rows | binding audit 与 sensitivity |

默认主读数使用 `reconstructed_transition_universe`。原因是 G 的 previous-regime / next-regime segment 来自 SH000985 reconstructed regime；如果继续强行以 published transition 为主 universe，会把 legacy 60d / reconstructed 120d horizon mismatch 混入 segment binding。

必须输出 universe binding status：

| condition | universe_binding_status |
| --- | --- |
| published transition 且 reconstructed transition | `published_and_reconstructed_transition` |
| published transition 但 reconstructed 非 transition | `published_transition_not_reconstructed_transition` |
| reconstructed transition 但 published 非 transition | `reconstructed_transition_not_published_transition` |
| 两者都非 transition | `non_transition_out_of_scope` |

主 recall / cost / density readout 默认只纳入：

```text
universe_binding_status in {
  published_and_reconstructed_transition,
  reconstructed_transition_not_published_transition
}
```

`published_transition_not_reconstructed_transition` 不得直接触发 join fail；必须进入 `transition_previous_regime_universe_binding_audit.csv`，并在报告中说明它是 legacy / reconstructed 口径漂移。如果该类事件超过 published transition events 的 20%，final decision 不得超过 diagnostic-only，除非 sensitivity readout 证明结论不依赖 universe 选择。

只有在 reconstructed transition segment 无法构造、或 reconstructed transition 主 universe 没有可读 event / episode denominator 时，才允许输出：

```text
transition_previous_regime_outcome_component_blocked
```

### 4.4 PIT previous-regime assignment

对每个 transition segment，取其前一个非 transition、非 component_missing segment：

```text
previous_non_transition_regime in {risk_on, risk_off}
previous_non_transition_trading_day_n
previous_non_transition_end_date
days_since_previous_regime_end
```

PIT taxonomy：

| condition | pit_transition_context |
| --- | --- |
| previous non-transition regime = `risk_on` | `transition_from_risk_on` |
| previous non-transition regime = `risk_off` | `transition_from_risk_off` |
| previous non-transition regime unavailable | `transition_from_unknown_or_censored` |

PIT assignment 只允许使用 `date <= event_t0_date` 可知的信息。不得使用 `next_regime`、future return、future low / high、future event label。

### 4.5 Ex-post outcome label

对每个 transition segment，取其后一个非 transition、非 component_missing segment：

```text
next_non_transition_regime in {risk_on, risk_off}
next_non_transition_start_date
days_to_next_regime_start
```

ex-post outcome：

| condition | transition_outcome_label |
| --- | --- |
| `next_non_transition_regime` 缺失 | `transition_outcome_pending_or_censored` |
| `next_non_transition_regime == previous_non_transition_regime` | `transition_continuation` |
| `next_non_transition_regime != previous_non_transition_regime` | `transition_conversion` |

方向标签：

| previous -> next | transition_outcome_direction |
| --- | --- |
| risk_on -> risk_on | `risk_on_continuation_buffer` |
| risk_on -> risk_off | `risk_on_to_risk_off_deterioration_conversion` |
| risk_off -> risk_off | `risk_off_continuation_buffer` |
| risk_off -> risk_on | `risk_off_to_risk_on_recovery_conversion` |
| unknown / censored | `unknown_or_censored` |

`transition_outcome_label` 与 `transition_outcome_direction` 只能用于 readout、report、diagnostic gate；不得回填为 PIT feature。

supported 层级只能使用聚合的 `transition_outcome_label`：

```text
transition_continuation
transition_conversion
```

`transition_outcome_direction` 只能用于解释和 diagnostic slicing。任何方向级 conversion 结论都必须标记：

```text
per_direction_conversion_diagnostic_only
```

尤其是以下两个方向不得单独作为 supported evidence：

```text
risk_off_to_risk_on_recovery_conversion
risk_on_to_risk_off_deterioration_conversion
```

## 5. 轻量 Grid Search

Experiment G 可以做轻量 grid search，但搜索对象必须是 deterministic rule 参数，不得训练模型。

### 5.1 Grid 参数

默认 grid：

| parameter | candidates | 说明 |
| --- | --- | --- |
| `min_previous_regime_trading_day_n` | `[1, 3, 5, 10, 20]` | previous regime 至少持续多少交易日才算有效前态 |
| `min_segment_age_at_event_t0` | `[1, 2, 3, 5]` | event_t0 当天，transition segment 已经持续多少交易日才参与主读数；这是 PIT 可知字段 |
| `online_confirmation_trading_day_n` | `[0, 1, 2, 3]` | 新 regime 需要连续出现多少交易日才确认；确认前标记为 `state_pending_confirmation`，只能使用过去信息 |
| `outcome_max_transition_trading_day_n` | `[20, 60, 120, 240, null]` | 从 transition segment start 起，多少交易日内必须完成 continuation / conversion，否则 outcome censored；`null` 表示样本内出现 next non-transition 即可 |

允许增加参数，但必须满足：

1. 参数数量不超过 6 个。
2. grid 组合不超过 5 * 4 * 4 * 5 = 400 个；若新增参数导致组合超过 500，必须先缩小 grid。
3. 每个参数必须是可解释的 market-state rule，不得是模型超参。
4. 不得用 validation / robustness 上的 recall 或 cost 反向挑选规则。
5. 不得使用完整 `segment_trading_day_n` 过滤 PIT assignment；完整 segment length 只能作为 ex-post readout。

禁止的 grid 参数：

```text
min_transition_segment_trading_day_n
flicker_merge_max_trading_day_n
```

原因：

1. 完整 transition segment 持续时间在 event_t0 时不可知。
2. flicker merge 通常需要知道短 segment 之后接的状态，若用于 PIT assignment 会泄漏未来。
3. 若需要处理 flicker，只能使用 `online_confirmation_trading_day_n` 这类只依赖过去连续观测的 confirmation rule。

### 5.2 Grid selection discipline

grid search 的目标不是最大化收益或 recall，而是选择一个稳定、可解释、不过度 censor 的 rule。

grid selection 分成两层：

1. structural eligibility guard：可以使用 train / validation / robustness 的 denominator、censored share、`unique_segment_n`、`effective_contributing_segment_n`、`top1_segment_episode_share` 等结构可读性字段，但这些 guard 必须预先声明，不得看 recall / cost / winner outcome。
2. tie-break selection：只能按下面的固定优先级选择，不得根据 validation / robustness 的表现方向调参。

默认 selected rule 必须满足以下 structural eligibility：

1. train / validation / robustness 都有 `transition_from_risk_on` 与 `transition_from_risk_off` 的可读 denominator。
2. `transition_outcome_pending_or_censored` share 不超过 20%，除非最后样本边界不可避免。
3. 聚合 continuation / conversion 两类至少各有一个 split 的 `unique_segment_n >= 10`、`effective_contributing_segment_n >= 5`、`top1_segment_episode_share <= 0.50`，且 event_n >= 100。
4. 与 base rule 的 segment outcome direction agreement >= 80%，否则必须标记为 unstable。
5. 不以 fast-fail / false-repair / big-winner / recall 指标作为 rule selection objective。
6. 如果某个核心聚合 outcome cell 只有 event_n 达标，但 `unique_segment_n < 3`、`effective_contributing_segment_n < 3` 或 `top1_segment_episode_share > 0.80`，必须标记 `low_segment_power_diagnostic`，不得作为 supported evidence。

若多个 grid 组合满足条件，按以下顺序选择：

```text
1. 更低 online confirmation 延迟
2. 更低 min_previous_regime_trading_day_n
3. 更低 min_segment_age_at_event_t0
4. 更低 censored share
5. 更接近 base rule 的 outcome direction distribution
```

报告必须同时输出 base rule 与 selected rule；如果 selected rule 不是 base rule，必须解释差异。

### 5.3 Base rule

base rule 固定为：

```text
min_previous_regime_trading_day_n = 1
min_segment_age_at_event_t0 = 1
online_confirmation_trading_day_n = 0
outcome_max_transition_trading_day_n = null
```

base rule 不允许删除。即使 selected rule 另有参数，base rule 也必须完整输出，作为可追溯参考。

## 6. Required Inputs

### 6.1 Upstream manifests

必须读取：

```text
outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
outputs/manifests/regime_family_matrix/regime_family_matrix_manifest.json
outputs/manifests/risk_on_r_series_bridge_ranker/risk_on_r_series_bridge_ranker_manifest.json
outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
outputs/manifests/transition_subregime_taxonomy_audit/transition_subregime_taxonomy_audit_manifest.json
```

Experiment F 可以是 diagnostic-only；G 的目的正是验证 F 之后的新解释框架。因此 F 不需要 supported，但其 manifest 必须存在，且不能是 input / component / leakage blocked。

若必要 manifest 缺失，输出：

```text
transition_previous_regime_outcome_input_blocked
```

G 必须与 F 使用同一套 reconstructed regime component 口径。优先级：

1. 若 F 输出了覆盖完整交易日历、可直接支持 G event-to-segment binding 的 date-level component / segment artifact，G 必须直接复用 F artifact，并记录 `component_reuse_policy = reuse_experiment_f_component_artifact`。
2. 若 F 只输出 event/window-level artifact，或只在 manifest / audit 表中记录 component source、formula 与 hash，不足以覆盖 G 的完整 reconstructed transition universe，G 可以重新从同一 SH000985 source 重建，但必须记录 `component_reuse_policy = rebuild_from_experiment_f_component_audit`，并对齐：
   - `component_source`
   - `component_source_hash`
   - `reconstruction_formula`
   - `market_drawdown_120d` 的 `rolling_high_120d(min_periods=60)`
   - `component_reconstruction_consistency_rate`
3. G 必须输出 `f_component_alignment_status`：

| condition | f_component_alignment_status |
| --- | --- |
| source hash / formula / row count 全部一致 | `aligned_with_experiment_f_component` |
| F artifact 可读且直接复用 | `reused_experiment_f_component_artifact` |
| source hash 一致但 row count 或 formula 漂移 | `component_alignment_drift_diagnostic` |
| 无法读取 F component audit / manifest | `component_alignment_blocked` |

若 `component_alignment_blocked`，final decision 必须是：

```text
transition_previous_regime_outcome_component_blocked
```

若 `component_alignment_drift_diagnostic`，可以继续 diagnostic-only，但不得 supported。

### 6.2 Market index source

默认 primary source：

```text
data/interim/index_qlib_csv/day/SH000985.csv
```

必须记录：

1. path。
2. sha256。
3. row count。
4. date min / max。
5. missing close count。
6. duplicate date count。
7. market component formulas。

如果 SH000985 缺失，可以使用 F 已审计的 fallback benchmark / proxy，但 final decision 不得超过 diagnostic-only，且报告必须标记 source caveat。

### 6.3 Event / replay / label source

必须读取：

```text
outputs/publishable/tables/candidate_family_canonical_events.csv.gz
outputs/publishable/tables/candidate_family_event_instances.csv.gz
outputs/local_cache/candidate_family_event_labels.parquet
outputs/local_cache/candidate_family_capture.parquet
outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_scope_retention_by_split_regime.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_e1_missed_retention_summary.csv
```

D membership 是 episode recall / E1-missed capture 的权威 source。不得从 aggregate retention table 反推 membership。

## 7. Event Join Contract

每个主 universe event 必须按 `event_t0_date` join 到唯一 reconstructed transition segment。

join policy：

1. `reconstructed_transition_universe` 内的 event 若无法 join 到唯一 reconstructed transition segment，必须进入 `transition_segment_join_failed`，并触发 label join audit。
2. `published_transition_not_reconstructed_transition` 不属于主 segment universe，不得算作 join failure；它只进入 universe binding audit / sensitivity。
3. `reconstructed_transition_not_published_transition` 属于主 readout universe，但必须保留 published `market_regime_bucket`，用于说明 legacy / reconstructed drift。
4. split 是 event-level 属性。segment_matrix 的 split 默认按 segment 内 event 的 `event_split` 展开统计；若同一 segment 覆盖多个 event_split，允许同一 segment 在多个 split 中出现，但必须输出 `split_assignment_policy = event_split_expanded` 与 `segment_cross_split_flag = True`。

输出字段：

```text
event_key
event_t0_date
event_split
published_market_regime_bucket
reconstructed_market_regime_bucket
universe_binding_status
transition_segment_id
segment_start_date
segment_end_date
final_segment_trading_day_n
segment_age_at_event_t0
observed_segment_trading_day_n_asof_t0
online_confirmation_status
segment_remaining_days_ex_post
previous_non_transition_regime
previous_non_transition_trading_day_n
pit_transition_context
next_non_transition_regime
transition_outcome_label
transition_outcome_direction
outcome_censor_flag
grid_rule_id
```

PIT 字段：

```text
previous_non_transition_regime
previous_non_transition_trading_day_n
pit_transition_context
segment_start_date
segment_age_at_event_t0
observed_segment_trading_day_n_asof_t0
online_confirmation_status
universe_binding_status
```

非 PIT / readout 字段：

```text
segment_end_date
final_segment_trading_day_n
next_non_transition_regime
transition_outcome_label
transition_outcome_direction
segment_remaining_days_ex_post
outcome_censor_flag
```

如果任何非 PIT 字段被用于 PIT assignment，必须 fail closed：

```text
transition_previous_regime_outcome_leakage_blocked
```

## 8. Readout Requirements

### 8.1 Segment composition

输出：

```text
transition_previous_regime_segment_matrix.csv
```

至少包含：

```text
grid_rule_id
split
split_assignment_policy
segment_cross_split_flag
cross_split_segment_n
universe_binding_status
pit_transition_context
transition_outcome_label
transition_outcome_direction
unique_segment_n
trading_day_n
calendar_day_n
mean_segment_trading_day_n
median_segment_trading_day_n
max_segment_trading_day_n
event_n
target_episode_n
top1_segment_event_share
top1_segment_episode_share
effective_contributing_segment_n
censored_segment_n
censored_segment_share
segment_power_status
```

`unique_segment_n` 口径：

1. 在每个 `(grid_rule_id, split, universe_binding_status, pit_transition_context, transition_outcome_label, transition_outcome_direction)` cell 内，按 unique `transition_segment_id` 去重。
2. 若同一 segment 因 event_split 展开出现在多个 split，必须在各 split 内分别去重，并额外输出 `cross_split_segment_n`。
3. power gate 必须使用 `unique_segment_n`，不得使用 raw event rows 或 raw membership rows。

贡献集中度口径：

```text
top1_segment_event_share = max(event_n contributed by one transition_segment_id) / cell event_n
top1_segment_episode_share = max(unique target episodes contributed by one transition_segment_id) / cell target_episode_n
effective_contributing_segment_n = 1 / sum(segment_episode_share_i^2)
```

其中 `effective_contributing_segment_n` 使用 episode share 计算；若 target episode 不可用，则使用 event share 并标记 `contribution_metric_fallback = event_share`.

`segment_power_status` 规则：

| condition | segment_power_status |
| --- | --- |
| `unique_segment_n >= 10` 且 `effective_contributing_segment_n >= 5` 且 `top1_segment_episode_share <= 0.50` | `sufficient_segment_power` |
| `3 <= unique_segment_n < 10` 或 `3 <= effective_contributing_segment_n < 5` 或 `0.50 < top1_segment_episode_share <= 0.80` | `low_segment_power_caution` |
| `unique_segment_n < 3` 或 `effective_contributing_segment_n < 3` 或 `top1_segment_episode_share > 0.80` | `low_segment_power_diagnostic` |

若条件重叠，必须按 diagnostic > caution > sufficient 的优先级判定。

任何 `low_segment_power_diagnostic` cell 不得用于 supported evidence，即使 event_n 很大。

### 8.2 Event / episode recall

输出：

```text
transition_previous_regime_recall_retention_matrix.csv
```

必须按以下维度切片：

```text
grid_rule_id
split
universe_binding_status
pit_transition_context
transition_outcome_label
transition_outcome_direction
source_id
window
replay_policy_id
```

核心 source：

```text
07_E1_only
08_R_core_event_regime_gated
08_R6_event_regime_gated
08_selected_T4_T7_union
08_T4_gated
08_T7_gated
```

核心指标：

```text
target_episode_denominator_n
unique_segment_n
effective_contributing_segment_n
top1_segment_episode_share
top1_segment_event_share
source_post_replay_captured_episode_n
source_post_replay_recall
e1_post_replay_captured_episode_n
e1_post_replay_recall
e1_missed_episode_n
source_post_replay_captures_e1_missed_n
source_post_replay_captures_e1_missed_rate
wilson_ci_low
wilson_ci_high
episode_power_status
segment_power_status
contribution_concentration_status
```

denominator 必须是当前 rule / split / universe binding / context / outcome 下的 unique target episode，不得使用 global transition denominator。

`contribution_concentration_status` 规则：

| condition | contribution_concentration_status |
| --- | --- |
| `top1_segment_episode_share <= 0.50` 且 `effective_contributing_segment_n >= 5` | `not_concentrated` |
| `0.50 < top1_segment_episode_share <= 0.80` 或 `3 <= effective_contributing_segment_n < 5` | `concentrated_low_power_caution` |
| `top1_segment_episode_share > 0.80` 或 `effective_contributing_segment_n < 3` | `single_segment_dominated_diagnostic` |

任何 `single_segment_dominated_diagnostic` cell 不得用于 supported evidence，即使 recall / E1-missed capture 看起来稳定。

### 8.3 Cost / quality

输出：

```text
transition_previous_regime_cost_quality_matrix.csv
```

至少包含：

```text
event_n
failure_10_complete_rate
fast_fail_10d_rate
event_false_repair_20d_complete_rate
false_repair_20d_rate
event_big_winner_120d_complete_rate
event_big_winner_120d_rate
```

必须同时输出 R-core 与 R6。若 T4 / T7 样本不足，可以输出 diagnostic-only。

### 8.4 Density / overlap

输出：

```text
transition_previous_regime_density_overlap_matrix.csv
```

density anchor 必须优先使用 D membership 中的 `replay_anchor_pos` / `replay_anchor_date`，与 Experiment A density contract 对齐。不得混用 event_t0 / trade_open 作为主 density anchor。

指标：

```text
selected_event_count
formal_event_day_density
rolling_10d_executable_event_day_density
rolling_20d_executable_event_day_density
rolling_10d_duplicate_rate
rolling_20d_duplicate_rate
family_concentration
cross_family_collision_rate
density_contract_reference
```

## 9. Leakage Rules

必须输出：

```text
transition_previous_regime_leakage_audit.csv
```

硬规则：

1. `pit_transition_context` 只能由 previous non-transition regime 与 event_t0 已知 segment age 生成。
2. `transition_outcome_label`、`transition_outcome_direction`、`next_non_transition_regime` 只能用于 readout。
3. grid selection 不得使用 recall / fast-fail / false-repair / big-winner 优化目标。
4. validation 只用于 diagnostic，不得反向调参。
5. robustness 只允许参与预声明的 structural eligibility guard；不得根据 robustness 的 recall / cost / winner 表现选择参数。
6. `final_segment_trading_day_n`、`segment_end_date`、`segment_remaining_days_ex_post` 不得用于 PIT assignment 或主 universe inclusion。
7. `online_confirmation_trading_day_n` 只能用过去连续 regime observations 实现，不得向后看是否为短 flicker。
8. `transition_outcome_label` 可用于 selected rule 的 structural coverage audit，但不得用于选择收益、recall 或 cost 最优参数。

任一违反，输出：

```text
transition_previous_regime_outcome_leakage_blocked
```

## 10. Decision Tiers

### 10.1 Supported

输出：

```text
transition_previous_regime_conditioning_explanatory_supported
```

必须同时满足：

1. input / component / leakage audit 全部 pass。
2. selected rule 在 train / validation / robustness 都有 `transition_from_risk_on` 与 `transition_from_risk_off` 的可读 denominator。
3. censored segment share <= 20%，或 censor 仅来自样本尾部且报告明确说明。
4. `published_transition_not_reconstructed_transition` share <= 20%；若超过 20%，只能 diagnostic-only，除非 sensitivity 证明主要结论不依赖 universe 选择。
5. continuation vs conversion 在至少两个 split 上表现出稳定差异，且方向一致；该稳定差异只能建立在聚合 `transition_outcome_label` 层级，不得建立在单独的 `transition_outcome_direction` 层级。例如：
   - conversion fast-fail / false-repair 高于 continuation；或
   - conversion recall 低于 continuation；或
   - previous-regime conditioned outcome 能解释 F 中 boundary over-capture。
6. 上述稳定差异所依赖的核心 cells 必须满足：
   - train 与 robustness 均有可读 denominator。
   - 每个用于 supported evidence 的聚合 outcome cell `unique_segment_n >= 3`。
   - 每个用于 supported evidence 的聚合 outcome cell `effective_contributing_segment_n >= 3`。
   - 每个用于 supported evidence 的聚合 outcome cell `top1_segment_episode_share <= 0.80`。
   - 若 `unique_segment_n < 10`、`effective_contributing_segment_n < 5` 或 `top1_segment_episode_share > 0.50`，报告必须标记 low power caveat。
   - 若 `unique_segment_n < 3`、`effective_contributing_segment_n < 3` 或 `top1_segment_episode_share > 0.80`，不得作为 supported evidence。
7. R-core / R6 readout 至少覆盖 train 与 robustness。
8. 不声称 PIT 能准确预测 conversion，只声称 previous-regime conditioned audit 有解释力。
9. final report 必须明确 supported 的含义是 explanatory audit supported，不是 direct-entry support。
10. per-direction conversion readout 必须保持 diagnostic-only；`risk_off_to_risk_on_recovery_conversion` 与 `risk_on_to_risk_off_deterioration_conversion` 不得单独触发 supported。

### 10.2 Diagnostic Only

输出：

```text
transition_previous_regime_conditioning_diagnostic_only
```

触发条件包括：

1. continuation / conversion 样本不足。
2. outcome 差异不稳定。
3. selected rule 与 base rule 差异过大。
4. source-caveated upstream decision 使结果不能升级。
5. grid 只能找到 highly censored rule。
6. published / reconstructed transition universe 漂移超过 20%，且 sensitivity 不足以证明结论稳定。
7. 任一关键 readout 只有 event_n 达标，但 `unique_segment_n < 3` 或 `effective_contributing_segment_n < 3`。
8. 任一关键 readout 被单个 transition segment 主导，`top1_segment_episode_share > 0.80`。
9. 所谓稳定差异只存在于 per-direction conversion，而不存在于聚合 continuation-vs-conversion。

### 10.3 Blocked

可能输出：

```text
transition_previous_regime_outcome_input_blocked
transition_previous_regime_outcome_component_blocked
transition_previous_regime_outcome_label_join_blocked
transition_previous_regime_outcome_leakage_blocked
transition_previous_regime_outcome_binding_drift_blocked
```

blocked 必须 fail closed，不得输出 supported / diagnostic conclusion。

`transition_previous_regime_outcome_binding_drift_blocked` 只在无法计算 published / reconstructed universe binding audit 时使用，例如缺少 `event_t0_date`、无法重建 reconstructed regime、或 event key 无法对账。单纯 drift share 过高不得 blocked；应按 §10.2 降级为 diagnostic-only。

## 11. Required Outputs

### 11.1 Tables

```text
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_input_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_component_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_universe_binding_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_segment_catalog.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_grid_search.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_event_assignment.csv.gz
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_segment_matrix.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_recall_retention_matrix.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_e1_missed_capture.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_cost_quality_matrix.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_density_overlap_matrix.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_label_join_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_leakage_audit.csv
outputs/publishable/tables/transition_previous_regime_outcome_audit/transition_previous_regime_decision_tiers.csv
```

### 11.2 Reports

```text
outputs/publishable/reports/transition_previous_regime_outcome_audit/transition_previous_regime_outcome_audit_report.md
outputs/publishable/reports/transition_previous_regime_outcome_audit/transition_previous_regime_outcome_contract.md
outputs/publishable/reports/transition_previous_regime_outcome_audit/transition_previous_regime_timeline.png
outputs/publishable/reports/transition_previous_regime_outcome_audit/transition_previous_regime_timeline.svg
```

report 必须用中文写明：

1. 为什么 G 不训练。
2. PIT context 与 ex-post outcome 的边界。
3. reconstructed transition universe 与 published transition universe 的 binding drift。
4. G 是否复用了 F reconstructed component，或是否出现 component alignment drift。
5. selected rule 与 base rule 的差异。
6. continuation / conversion 的 segment-level power、有效贡献 segment 数、top-1 segment 贡献集中度。
7. per-direction conversion 为什么只能 diagnostic-only，尤其 robustness 中 recovery / deterioration conversion segment 很少时不得 over-claim。
8. 是否解释了 F 的 boundary over-capture / robustness collapse。
9. 后续是继续 transition taxonomy、转向 cost rejector，还是停止 transition family rediscovery。

### 11.3 Manifest

```text
outputs/manifests/transition_previous_regime_outcome_audit/transition_previous_regime_outcome_audit_manifest.json
```

必须包含：

```text
experiment_id
final_decision
selected_grid_rule_id
base_grid_rule_id
grid_parameter_space
selected_rule_parameters
selection_reason
transition_universe_policy
universe_binding_summary
f_component_alignment_status
component_reuse_policy
segment_power_summary
contribution_concentration_summary
per_direction_conversion_policy
input_artifacts
input_hashes
output_paths
output_hashes
output_row_counts
runner_code_hash
requirement_hash
created_at
```

## 12. 不可声称内容

1. 不得声称 transition continuation / conversion 是 PIT 可完全识别的状态。
2. 不得用 `next_regime` 训练或筛选 entry。
3. 不得声称 direct-entry support。
4. 不得声称 official train process。
5. 不得把 selected grid rule 解释为收益最优规则。
6. 不得把 diagnostic-only 的 continuation / conversion 差异升级为 production gate。
7. 不得混用 published transition 与 reconstructed transition denominator；两者差异必须通过 universe binding audit 显式呈现。

## 13. 成功标准

本需求的成功不是“找到能交易的 transition signal”，而是回答：

1. previous regime 是否能解释 transition 的主要结构？
2. continuation 与 conversion 的 recall / cost / density 是否不同？
3. F 中 boundary over-capture 是否主要来自 previous-regime continuation buffer？
4. transition 后续应该继续 taxonomy，还是把重点转向 cost rejector / label source 重定义？

如果结果显示 continuation / conversion 差异稳定，即使无法 PIT 准确预测 conversion，G 仍可支持一个更清晰的后续方向：

```text
transition should be audited and filtered conditional on previous regime,
not treated as one independent third market state.
```
