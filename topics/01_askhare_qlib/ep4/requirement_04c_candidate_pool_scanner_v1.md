# EP4 需求 04c: Candidate Pool Scanner V1

## 1. 需求元信息

- 需求 id: `ep4_r04c_candidate_pool_scanner_v1`
- 简称: `r04c_candidate_pool_scanner_v1`
- 状态: 首版可实现的 pool scanner 诊断型需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion4.md`
- 上游 R04 需求: `ep4/requirement_04_dynamic_momentum_exposure_eligibility_audit_v1.md`
- 上游 R04b 需求: `ep4/requirement_04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1.md`
- 上游 R04 输出根目录: `ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/`
- 上游 R04b 输出根目录: `ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/`
- 必需输出根目录: `ep4/outputs/r04c_candidate_pool_scanner_v1/`
- 必需 config 路径: `ep4/configs/r04c_candidate_pool_scanner_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r04c_candidate_pool_scanner.py`
- 必需 validator 路径: `ep4/scripts/validate_r04c_candidate_pool_scanner.py`
- 日期: 2026-05-18

## 2. 背景与实验目的

R04 v1 的结论是：

```text
RPS / momentum 更像右尾候选池生成器，不是 action-time entry trigger。
market / industry exposure eligibility 没有通过稳定 OOS 证明。
```

R04b v1 的结论进一步收窄：

```text
固定 baseline_A RPS pool 后，exit / sizing policy 可以压缩左尾和 bad path；
但 selected policy 在 robustness 上 net_return_mean_delta_vs_hold120 = -3.05%，
没有证明 hold / exit / risk-budget policy 能跨 split 稳定提高期望收益。
```

因此 R04c 不继续调 CTA / trailing / stop 参数，也不继续在 baseline_A 上追加 exit policy。R04c 只回答一个前置问题：

```text
在进入 R04b-style hold / exit / risk-budget replay 之前，
EP4 已有 artifact 或少量预注册 deterministic selector 中，
是否存在一个比 R04 baseline_A 更值得管理的固定 candidate pool？
```

R04c 的输出不是交易策略，也不是 R04b 的替代实现。R04c 是一个 pool scanner：

```text
candidate pool quality first,
exit management later.
```

只有当某个 pool 在 hold120 no-exit baseline 上已经比 baseline_A 更稳健，才允许进入后续 R04b-style replay。否则继续调 exit policy 只是在差池子上优化保险条款。

## 3. R04c 要回答的问题

R04c 必须回答：

1. 是否存在 hold120 baseline 明显优于 R04 baseline_A 的 candidate pool？
2. 这个改善是否同时出现在 validation 和 robustness，而不是只在单一 split 好看？
3. 改善是否相对 matched baseline_A 仍存在，而不是来自年份、市场状态或行业状态偏置？
4. 改善来自更高 net mean、更低 bad path、更高右尾，还是只是 denominator shrink？
5. 该 pool 的 +50 winner rate 是否没有被牺牲？
6. 该 pool 是否存在严重 calendar-year concentration / instrument concentration？
7. 该 pool 是否由 train-only selection 得出，validation / robustness 是否没有参与定义或参数选择？
8. 哪些上游 source 只能作为 descriptive lead，不能作为 promotable pool？
9. 是否有 pool 值得进入下一版 R04b-style replay？

## 4. Non-Negotiables

### 4.1 R04c 不跑 exit policy

R04c 只评估 candidate pool 的 hold120 baseline quality。禁止在 R04c 中运行或选择：

```text
fixed_stop
time_stop
break_even_after_gain
profit_lock_after_gain
ATR trailing
EMA trailing
CTA / trailing
volatility_scaled exit policy
market_state_scaled exit policy
```

R04c 可以复用 R04b 的 price / cost / hold120 replay semantics，但只能使用：

```text
hold_120d no_exit fixed_size
```

### 4.2 Pool selector 不是 action-time entry gate

R04c 可以定义一个新的 fixed candidate pool，但不能在 pool 内继续做动态 allow/block。

允许：

```text
预注册 pool_id = source_rule_id + deterministic membership rule
每个 pool 内固定 entry = first executable next-open after source anchor
```

禁止：

```text
在同一个 pool 内按 market / industry / validation outcome 再筛 entry
先用 R04b exit result 反向找 pool
用 robustness 表现调 pool threshold
把 pool scanner 结论写成 production entry rule
```

### 4.3 Selection leakage 必须 fail closed

Train / validation / robustness 的职责固定为：

```text
train: 允许 pool 参数选择与 train score 排序
validation: 允许确认 train-selected pools 是否通过 hard gates
robustness: final readout only，不参与任何选择
```

如果某个 pool 的定义来自已经看过 validation / robustness outcome 的上游 artifact，它必须标记：

```text
pool_promotability_status = descriptive_lead_only_oos_seen
```

这种 pool 可以报告，但不得成为 `selected_candidate_pool_id`。

### 4.4 R04 baseline_A 是强制 comparator

所有 pool 必须同时和以下两个 comparator 比较：

```text
global_baseline_A
matched_baseline_A
```

`global_baseline_A` 是 R04 included single_momentum_rps episode-first-trigger rows。

`matched_baseline_A` 是按同一 split / calendar / market / industry 条件匹配后的 baseline_A 子样本，用来排除“新 pool 只是更多落在好年份或好 regime”的假象。

如果 matched comparator 不足，pool 只能 descriptive，不得 selected。

### 4.5 不允许 pooled OOS 掩盖 split 失败

R04c 可以输出 pooled OOS 描述，但 final gate 必须逐 split 判断：

```text
validation pass
robustness readout pass
```

禁止用：

```text
validation + robustness pooled
all split pooled
train + validation + robustness pooled
```

来覆盖 validation 或 robustness 单独失败。

## 5. 必需输入

### 5.1 必需上游输入

R04c 必须加载并校验：

```text
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/manifests/r04_dynamic_momentum_exposure_eligibility_validation.json
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/manifests/r04_dynamic_momentum_exposure_eligibility_manifest.json
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/cache/r04_rps_candidate_action_panel.parquet
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/cache/r04_candidate_regime_join_panel.parquet
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/cache/r04_background_action_time_panel.parquet

ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/manifests/r04b_fixed_entry_hold_exit_risk_budget_cta_validation.json
ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/manifests/r04b_fixed_entry_hold_exit_risk_budget_cta_manifest.json
ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/cache/r04b_daily_policy_path_panel.parquet
ep4/outputs/r04b_fixed_entry_hold_exit_risk_budget_cta_diagnostic_v1/reports/r04b_policy_replay_summary.csv
```

R04 / R04b validation status 必须为 `passed`。否则 R04c 必须 fail closed：

```text
blocked_upstream_validation_failed
```

### 5.1.1 必需本地 PIT price provider

R04b 的 `r04b_daily_policy_path_panel.parquet` 只覆盖 baseline_A replay events，不能作为 R02/R03 upstream pool 的全局价格路径来源。R04c 必须显式加载本地 PIT price provider，并把 provider hash 写入 manifest：

```text
data/qlib/cn_data_pit/calendars/day.txt
data/qlib/cn_data_pit/features/*/{open,high,low,close,volume,money,factor}.day.bin
data/qlib/cn_data_pit/instruments/*.txt
```

默认 price schema 与 R04b 一致：

```text
adjusted_open
adjusted_high
adjusted_low
adjusted_close
volume
money
suspended_or_dirty_bar
```

Price materialization 必须复用 R04b price-provider 语义：

```text
provider_uri = data/qlib/cn_data_pit
feature expressions = R04b loader 的 $open/$high/$low/$close/$volume/$money/$factor
output schema = adjusted_open/adjusted_high/adjusted_low/adjusted_close/volume/money/factor
dirty bar logic = R04b suspended_or_dirty_bar 判定
```

不得重新解释 `factor.day.bin` 或在 R04c 中引入新的 adjustment policy。若 materialized price 与 R04b baseline_A reconciliation 不一致，必须 fail closed：

```text
blocked_price_materialization_mismatch
```

R04c runner 必须对每个 source pool 重新构造 hold120 price path。R04b daily path 只能用于：

```text
baseline_A reconciliation
R04b baseline hold120 profile cross-check
price-provider hash / adjustment-policy lineage check
```

如果本地 PIT price provider 缺失或无法覆盖任一 promotable pool 的 entry-to-day120 window，该 pool 必须标记：

```text
pool_promotability_status = unavailable
invalid_pool_reason = missing_price_provider_or_path
```

### 5.2 可选 source registry

R04c v1 必须内置 source registry，并对每个 source 输出 readiness status。可选 source 缺失时不阻断整个 scanner，但对应 source 的 pools 必须标记 unavailable。

优先扫描的本地 sources：

| source_id | source root | primary artifacts | 用途 | 默认 promotability |
|---|---|---|---|---|
| `r02_family_precision` | `ep4/outputs/r02_family_precision_forward_return_stats_v1/` | `cache/r02_family_action_time_panel.parquet`, `reports/r02_family_precision_by_split.csv`, `reports/r02_family_forward_return_stats_by_split.csv` | frozen family signal occurrence pools | promotable if definition train-frozen |
| `r02_evidence_family` | `ep4/outputs/r02_evidence_family_discovery_v1/` | `cache/r02_action_time_panel.parquet`, `reports/r02_combo_search_summary.csv`, `reports/r02_family_selection_summary.csv` | evidence family / combo pools | train-only required |
| `r03b_signal_sequence` | `ep4/outputs/r03b_signal_sequence_big_winner_path_diagnostic_v1/` | `cache/r03b_seed_episode_panel.parquet`, `cache/r03b_sequence_step_panel.parquet`, `reports/r03b_sequence_pattern_summary.csv` | sequence-derived candidate leads | descriptive unless rule frozen train-only |
| `r03c_family_set_pooling` | `ep4/outputs/r03c_price_aware_kth_fresh_family_set_pooling_diagnostic_v1/` | `cache/r03c_family_set_pooling_panel.parquet`, `reports/r03c_family_set_pooling_summary.csv` | family-set pooling leads | descriptive unless rule frozen train-only |
| `r02_winner_anchored_v2` | `ep4/outputs/r02_winner_anchored_structure_profile_discovery_v2/` | `cache/r02_v2_action_time_eventized_signals.parquet`, `reports/r02_v2_representative_selection.csv`, `reports/r02_v2_winner_profile_search_summary.csv` | winner-anchored structural leads | descriptive by default |
| `r01_pre60_indicator_search_v2` | `ep4/outputs/r01_big_winner_pre60_indicator_search_v2/` | `reports/pre60_condition_search_v2_top_*.csv` | big-winner-precondition leads | descriptive by default |
| `r01_post30_indicator_search_v1` | `ep4/outputs/r01_big_winner_post30_indicator_search_v1/` | `reports/post30_condition_search_v1_top_*.csv` | post-winner state leads | descriptive by default |

R04c v1 只要求实现以下 promotable adapters：

```text
r04_deterministic_auxiliary
r02_family_precision_frozen_family_occurrence
r03c_config_frozen_family_set_pool
```

其他 source 在 v1 中必须进入 source readiness 和 descriptive-lead audit，但不得临时发明 adapter 或成为 selected pool：

```text
pool_promotability_status = descriptive_lead_only_adapter_not_implemented_v1
```

Validator 必须输出每个 source：

```text
source_id
source_root
required_artifacts_present
source_validation_status
source_hash
source_promotability_default
source_readiness_status
unavailable_reason
```

### 5.2.1 Adapter contract: `r02_family_precision_frozen_family_occurrence`

该 adapter 只能从 `r02_family_action_time_panel.parquet` 构造 7 个 frozen family occurrence pools。默认 `pool_id`：

```text
r02_precision_momentum_rps
r02_precision_oscillator
r02_precision_price_trend
r02_precision_pullback_drawdown
r02_precision_range_breakout
r02_precision_volatility_band
r02_precision_volume_money
```

Membership rule 固定为：

```text
condition_group_id belongs to the frozen 7 family representatives
signal_occurs == true
feature_complete_flag == true
base action-time row is executable
```

Anchor 固定为：

```text
anchor_signal_date = trade_date
```

如果 `r02_family_action_time_panel.parquet` 字段名不同，runner 必须在 `r04c_source_readiness_audit.csv` 中列出 exact column mapping；不得用 summary CSV 反推 row-level membership。

### 5.2.2 Adapter contract: `r03c_config_frozen_family_set_pool`

R03c family-set source 默认是 descriptive-only。只有当 config 显式列出 train-frozen family-set keys 时，才允许构造 promotable pool：

```yaml
r03c_promotable_pooling_keys:
  - <pooling_key>
r03c_pooling_key_column: pooling_key
r03c_anchor_signal_date_column: step_signal_date
r03c_instrument_column: instrument_id
```

默认 key column 固定为 `pooling_key`，因为当前 `r03c_family_set_pooling_panel.parquet` 的 row-level pool identity 字段是 `pooling_key`，不是 `family_set_key`。Config 只有在显式声明 column mapping 且该 column 实际存在时，才允许覆盖默认字段。

这些 keys 必须满足：

```text
key appears in r03c_family_set_pooling_panel.parquet[r03c_pooling_key_column]
key selection source is train-only
key was not selected from validation / robustness / all outcome tables
```

Membership rule 固定为：

```text
row[r03c_pooling_key_column] in r03c_promotable_pooling_keys
source row is observable at anchor date
```

Anchor 默认固定为 `step_signal_date`。Runner 必须在 pool registry 中写出 exact anchor column。`fresh_entry_date` 可以用于 source reconciliation，但不得作为默认 anchor，因为 R04c 会从 `anchor_signal_date` 重新计算 next-open entry。如果 exact key / anchor / instrument column 不存在，该 pool 必须 unavailable，不得从 summary tables 推断 key 或 anchor。

### 5.3 Descriptive-only source 的处理

R01 big-winner search 和 R02 winner-anchored source 不能直接作为 promotable pool，原因是它们的发现过程以已知 winner 为条件，天然有反向发现风险。

R04c v1 中它们必须保持 descriptive-only，不得生成 `promotable_candidate`，也不得成为 `selected_candidate_pool_id`。后续版本如果要把它们升级为 promotable adapter，必须先单独修订 requirement，并至少满足：

```text
condition text 可以在 action-time denominator 上重放
参数选择只使用 train split
validation / robustness 不参与 condition threshold 或 rule selection
matched_baseline_A comparator sufficient
```

R04c v1 runner 必须标记：

```text
pool_promotability_status = descriptive_lead_only_winner_anchored
```

## 6. Pool Registry

R04c 必须在任何 replay 前冻结 `r04c_pool_registry_frozen.csv`。

字段至少包括：

```text
pool_id
pool_family_id
pool_source_id
adapter_id
pool_source_artifact_path
pool_source_artifact_hash
pool_type
anchor_type
anchor_signal_date_column
instrument_column
membership_rule_text
membership_rule_json
membership_rule_hash
field_source_map_hash
episode_collapse_rule
selection_stage_allowed
pool_promotability_status
leakage_risk_class
invalid_pool_reason
```

### 6.1 必选 control pools

R04c 必须包含以下 control pools：

```text
baseline_A_r04_included_rps_episode_first_trigger
baseline_A_matched_background
```

`baseline_A_r04_included_rps_episode_first_trigger` 必须和 R04/R04b 的 baseline_A 分母一致：

```text
r04_inclusion_status == included
episode_entry_valid == true
one row per r04_candidate_event_id
```

### 6.2 R04-derived deterministic auxiliary pools

R04c v1 可以预注册以下 R04-derived pools。它们不是通过 outcome 搜出来的，因此可以参与 train selection。

| pool_id | membership rule | required logical fields |
|---|---|---|
| `r04_rps95` | `stock_rps_60d >= 0.95` | `stock_rps_60d` |
| `r04_rps95_money80` | `stock_rps_60d >= 0.95 AND money_rank_20d >= 0.80` | `stock_rps_60d`, `money_rank_20d` |
| `r04_rps95_industry80` | `stock_rps_60d >= 0.95 AND industry_rps_60d >= 0.80` | `stock_rps_60d`, `industry_rps_60d` |
| `r04_rps95_industry_relative10` | `stock_rps_60d >= 0.95 AND stock_rps_minus_industry_rps_60d >= 0.10` | `stock_rps_60d`, `stock_rps_minus_industry_rps_60d` |

R04-derived required fields 是 logical fields。Runner 必须先按 config 中冻结的 source map 解析每个 logical field：

```yaml
r04_derived_field_source_map:
  stock_rps_60d:
    source_type: source_column_from_r04_artifact
    source_artifact: r04_candidate_regime_join_panel.parquet
    source_column: stock_rps_60d
  stock_rps_minus_industry_rps_60d:
    source_type: source_column_from_r04_artifact
    source_artifact: r04_candidate_regime_join_panel.parquet
    source_column: stock_rps_minus_industry_rps_60d
  money_rank_20d:
    source_type: derived_from_local_pit_provider_with_frozen_formula
    formula_id: money_rank_20d_v1
  industry_rps_60d:
    source_type: derived_from_local_pit_provider_with_frozen_formula
    formula_id: industry_rps_60d_v1
```

R04c v1 不允许现场重新设计 R04-derived selector。若需要使用高成交或行业共振字段，字段来源必须在 config 中冻结为以下两类之一：

```text
source_column_from_r04_artifact
derived_from_local_pit_provider_with_frozen_formula
```

默认 derivation 仅允许：

```text
money_rank_20d =
  cross_sectional_percentile_rank(
    rolling_mean(money, 20 trading days) as of anchor_signal_date
  )

industry_rps_60d =
  cross_sectional_percentile_rank(
    industry 60d return as of anchor_signal_date
  )
```

解析顺序固定为：

```text
1. read logical field source_type from r04_derived_field_source_map
2. if source_type == source_column_from_r04_artifact, exact source_artifact/source_column must exist
3. if source_type == derived_from_local_pit_provider_with_frozen_formula, formula_id must be one of the allowed derivations above
4. materialize field coverage by pool event before replay
5. if field cannot be materialized, mark only the affected pool unavailable
```

如果某个 logical field 在 source map 解析和 materialization 后仍不存在，runner 不得临时替代字段或改阈值，必须标记：

```text
invalid_pool_reason = missing_required_logical_field_after_resolution
pool_promotability_status = unavailable
```

如果本地 artifact 没有行业 membership 或无法 PIT 计算 `industry_rps_60d`，对应 pool 必须 unavailable，不得改成 market-wide proxy。

### 6.3 Upstream artifact pools

对 R02/R03 source，runner 只能从 source registry 中注册的 artifact 构造 pool。每个 upstream pool 必须落到统一 grain：

```text
instrument_id
anchor_signal_date
entry_execution_date
pool_id
pool_source_id
```

如果 source 原始 grain 是 stock-day signal，R04c 必须 episode-collapse：

```text
For each instrument_id, pool_id:
  consecutive signal days belong to the same pool episode;
  if the next signal occurs within episode_gap_trading_days after previous episode end,
  merge into the same episode.
anchor_signal_date = first signal date in collapsed episode.
```

默认：

```yaml
episode_gap_trading_days: 20
```

不得根据 performance 调整该 gap。

如果 source 原始 grain 是 seed episode / family-set / sequence pattern，runner 必须保留 source-defined episode id，并只使用 source-defined observable anchor。

### 6.4 V1 adapter scope freeze

R04c v1 的 promotable adapter scope 固定如下：

| adapter_id | promotable | allowed pool source | membership authority | anchor authority |
|---|---|---|---|---|
| `r04_deterministic_auxiliary` | yes | R04 candidate/regime panels + local PIT derived fields | Section 6.2 frozen rule | R04 `anchor_signal_date` |
| `r02_family_precision_frozen_family_occurrence` | yes | R02 precision action-time panel | R02 row-level signal occurrence | R02 `trade_date` |
| `r03c_config_frozen_family_set_pool` | conditional | R03c family-set pooling panel | config-frozen family-set keys | source observable anchor column |
| `r02_evidence_family` | no in v1 | R02 evidence artifacts | readiness/descriptive only | n/a |
| `r03b_signal_sequence` | no in v1 | R03b sequence artifacts | readiness/descriptive only | n/a |
| `r02_winner_anchored_v2` | no in v1 | R02 v2 winner-anchored artifacts | readiness/descriptive only | n/a |
| `r01_pre60_indicator_search_v2` | no in v1 | R01 pre60 search artifacts | readiness/descriptive only | n/a |
| `r01_post30_indicator_search_v1` | no in v1 | R01 post30 search artifacts | readiness/descriptive only | n/a |

任何未列入上表或 `promotable == no in v1` 的 adapter，不得输出 promotable pool。Validator 必须检查 selected pool 的 `adapter_id` 属于 v1 promotable adapter set。

## 7. Replay 口径

R04c 的 replay 口径必须与 R04b hold120 baseline 兼容。

### 7.1 Entry

每个 pool event 的 entry 固定为：

```text
entry_execution_date = first executable next-open after anchor_signal_date
entry_price = adjusted_open(entry_execution_date)
```

可执行 open 定义沿用 R04b：

```text
bar exists
adjusted_open > 0
volume > 0
money > 0
suspended_or_dirty_bar == false
```

### 7.2 Hold120 no-exit

R04c 只计算：

```text
hold_120d no_exit fixed_size
```

Exit 固定为：

```text
exit_signal_date = day 120 close
exit_execution_date = first executable open after day 120 close
```

如果找不到 exit execution，标记：

```text
replay_status = censored_by_no_exit_execution
```

### 7.3 Return / cost

成本口径沿用 R04b：

```yaml
cost_model:
  cost_model_id: a_share_daily_replay_default_v1
  entry_slippage_bps: 5.0
  exit_slippage_bps: 5.0
  commission_bps_per_side: 3.0
  stamp_tax_bps_on_exit: 5.0
  min_fee_policy: none
```

主指标：

```text
gross_return = exit_price / entry_price - 1
net_return = gross_return - entry_cost - exit_cost
```

`max_gain50` 和 path quality 使用 gross adjusted close path，不扣成本。

### 7.4 Censoring

每个 event/pool replay 必须有：

```text
replay_status in {
  replay_complete,
  censored_by_split_boundary,
  censored_by_missing_price,
  censored_by_missing_required_indicator,
  censored_by_suspension_or_dirty_bar,
  censored_by_no_exit_execution,
  invalid_entry
}
```

`censored_share` 超过阈值的 pool 不得 selected。

## 8. Matched Baseline Comparator

### 8.1 Comparator 目的

R04c 必须区分：

```text
pool 本身更好
```

和：

```text
pool 只是更多出现在好年份 / 好 market regime / 好 industry regime
```

因此每个 pool 必须有 matched baseline_A comparator。

### 8.2 Matching keys

默认 matching keys：

```text
split
entry_calendar_year
entry_calendar_quarter
market_regime_bucket
industry_regime_bucket
```

如果某个 key 缺失，按以下 fallback：

```text
industry_regime_bucket missing -> use missing_industry
market_regime_bucket missing -> use missing_market_regime
entry_calendar_quarter insufficient -> fallback to entry_calendar_year
market+industry comparator insufficient -> fallback to market only
market-only comparator insufficient -> comparator_status = insufficient
```

每个 pool event 可以使用 baseline_A rows 作为 comparator with replacement，但必须输出：

```text
matched_comparator_count
matched_comparator_unique_event_count
matched_comparator_effective_sample_size
matched_comparator_status
```

Baseline_A comparator weighting 必须冻结：

```text
For each pool event i:
  find eligible baseline_A comparator rows under the strictest available matching key.
  assign each matched comparator row weight = 1 / n_i.

For each pool_id x split:
  aggregate comparator row weights across all pool events.
  matched_comparator_count = total matched comparator row assignments
  matched_comparator_unique_event_count = unique baseline_A event ids with weight > 0
  matched_comparator_effective_sample_size =
    (sum_j w_j)^2 / sum_j(w_j^2)
```

其中 `w_j` 是同一个 baseline_A event 在所有 pool events 匹配后累积的权重。若 `sum_j(w_j^2) == 0`，则 ESS 为 0 且 comparator insufficient。

### 8.3 Matched delta

每个 pool/split 至少计算：

```text
net_return_mean_delta_vs_matched_baseline_A
loss_le_minus5_delta_vs_matched_baseline_A
max_gain50_rate_delta_vs_matched_baseline_A
p10_delta_vs_matched_baseline_A
top1_calendar_year_share_delta_vs_matched_baseline_A
```

所有 primary gate 使用 matched delta，而不是只用 global baseline_A delta。

## 9. Metrics

### 9.1 Pool hold120 profile

每个 `pool_id x split` 必须输出：

```text
event_count
replay_complete_count
censored_count
censored_share
net_return_mean
net_return_median
net_return_p10
net_return_p25
net_return_p75
net_return_p90
loss_le_minus5_rate
loss_le_minus10_rate
max_drawdown_p50
max_drawdown_p90
max_gain50_count
max_gain50_rate
max_gain120d_p90
avg_holding_days
```

### 9.2 Baseline deltas

每个 pool/split 必须同时输出：

```text
net_return_mean_delta_vs_global_baseline_A
p10_delta_vs_global_baseline_A
loss_le_minus5_delta_vs_global_baseline_A
max_gain50_rate_delta_vs_global_baseline_A

net_return_mean_delta_vs_matched_baseline_A
p10_delta_vs_matched_baseline_A
loss_le_minus5_delta_vs_matched_baseline_A
max_gain50_rate_delta_vs_matched_baseline_A
```

### 9.3 Concentration

每个 pool/split 必须输出：

```text
top1_calendar_year_share
matched_baseline_top1_calendar_year_share
top1_instrument_share
matched_baseline_top1_instrument_share
top5_instrument_share
top1_industry_share
calendar_year_count
instrument_count
industry_count
```

### 9.4 Overlap / uniqueness

R04c 不能只找 baseline_A 的极小重叠子集而不说明 denominator shrink。

必须输出：

```text
pool_event_count
baseline_A_event_count
overlap_with_baseline_A_count
overlap_with_baseline_A_share
pool_unique_event_share
pairwise_jaccard_with_other_pools
```

## 10. Gate 与阈值

### 10.1 Minimum denominator

默认阈值：

```yaml
minimum_train_replay_complete_count: 500
minimum_validation_replay_complete_count: 300
minimum_robustness_replay_complete_count: 500
minimum_validation_max_gain50_count: 30
minimum_robustness_max_gain50_count: 50
max_censored_share: 0.25
minimum_matched_comparator_effective_sample_size: 300
```

低于阈值的 pool：

```text
pool_denominator_status = insufficient
```

只能 descriptive，不得 selected。

### 10.2 Train selection score

Train-only selection score 用于排序，不替代 hard gates。

默认：

```text
train_pool_quality_score =
  z(net_return_mean_delta_vs_matched_baseline_A)
  - z(loss_le_minus5_delta_vs_matched_baseline_A)
  + z(max_gain50_rate_delta_vs_matched_baseline_A)
  + z(p10_delta_vs_matched_baseline_A)
  - concentration_penalty
```

其中：

```text
concentration_penalty =
  max(0, top1_calendar_year_share - 0.50)
  + max(0, top1_instrument_share - 0.05)
```

z-score reference set 必须在同一 `pool_family_id` 内、跨 `pool_id` 计算，并在 `r04c_pool_registry_frozen.csv` 写出后冻结。

### 10.3 Validation hard gates

Train-selected pool 必须在 validation 同时满足：

```text
replay_complete_count >= minimum_validation_replay_complete_count
censored_share <= max_censored_share
matched_comparator_status == sufficient
net_return_mean > 0
net_return_mean_delta_vs_matched_baseline_A > 0
loss_le_minus5_delta_vs_matched_baseline_A < 0
max_gain50_rate >= 0.8 * matched_baseline_A_max_gain50_rate
max_gain50_count >= minimum_validation_max_gain50_count
top1_calendar_year_share <= max(0.50, matched_baseline_A_top1_calendar_year_share + 0.10)
top1_instrument_share <= max(0.05, matched_baseline_A_top1_instrument_share + 0.02)
```

如果 validation 未通过，pool 不得进入 `selected_candidate_pool_id`，但可以报告为 rejected lead。

### 10.4 Robustness final readout gates

Validation-passed pool 在 robustness 必须满足：

```text
replay_complete_count >= minimum_robustness_replay_complete_count
censored_share <= max_censored_share
matched_comparator_status == sufficient
net_return_mean > 0.08
net_return_mean_delta_vs_matched_baseline_A > 0.02
loss_le_minus5_rate < 0.30
loss_le_minus5_delta_vs_matched_baseline_A < 0
max_gain50_rate >= max(0.10, 0.8 * matched_baseline_A_max_gain50_rate)
max_gain50_count >= minimum_robustness_max_gain50_count
top1_calendar_year_share <= max(0.50, matched_baseline_A_top1_calendar_year_share + 0.10)
top1_instrument_share <= max(0.05, matched_baseline_A_top1_instrument_share + 0.02)
```

解释：

```text
robustness net mean > 8% 是相对 baseline_A robustness 6.12% 的最低改善要求；
matched delta > 2pct 用于防止只是市场年份偏置；
loss<=-5% < 30% 是相对 baseline_A robustness 35.25% 的改善要求；
+50 winner rate 不能明显牺牲右尾。
```

Concentration gate 使用相对 matched baseline_A 的原因是：如果某个 OOS split 本身年份很集中，不应把所有 pool 自动判死；但 pool 的集中度也不能明显高于它的 matched comparator。

### 10.5 Same-direction requirement

Validation 和 robustness 必须同向：

```text
validation.net_return_mean_delta_vs_matched_baseline_A > 0
robustness.net_return_mean_delta_vs_matched_baseline_A > 0
validation.loss_le_minus5_delta_vs_matched_baseline_A < 0
robustness.loss_le_minus5_delta_vs_matched_baseline_A < 0
```

如果只有一个 split 好，final decision 不得通过。

## 11. Selection Lifecycle

R04c selection lifecycle 固定为四段：

### 11.1 Stage 0: Source readiness

输出：

```text
r04c_source_readiness_audit.csv
```

如果 R04 / R04b 必需输入失败：

```text
final_decision = blocked_upstream_validation_failed
```

### 11.2 Stage 1: Pool definition freeze

输出：

```text
r04c_pool_registry_frozen.csv
r04c_pool_definition_leakage_audit.csv
```

任何 pool 如果 membership rule 依赖 future return、big winner label、validation result、robustness result、R04b exit result，必须：

```text
pool_promotability_status != promotable
```

### 11.3 Stage 2: Train screen

只使用 train split 计算 `train_pool_quality_score` 和 train gates。

输出：

```text
r04c_train_pool_selection_trace.csv
```

### 11.4 Stage 3: Validation gate

只评估 train-selected pools。

输出：

```text
r04c_validation_gate_audit.csv
```

Validation stage 必须冻结唯一的 `selected_candidate_pool_id`：

```text
selected_candidate_pool_id =
  highest validation_selection_score among validation_gate_pass == true pools
```

默认 validation score：

```text
validation_selection_score =
  z(net_return_mean_delta_vs_matched_baseline_A)
  - z(loss_le_minus5_delta_vs_matched_baseline_A)
  + z(max_gain50_rate_delta_vs_matched_baseline_A)
  + z(p10_delta_vs_matched_baseline_A)
  - concentration_penalty
```

Validation score reference set 只能包含 train-selected pools。`selected_candidate_pool_id` 一旦写入 `r04c_validation_gate_audit.csv` 和 `r04c_pool_selection_panel.parquet`，robustness 不得改变。

如果多个 pool 分数相同，tie-breaker 固定为：

```text
1. larger net_return_mean_delta_vs_matched_baseline_A
2. lower loss_le_minus5_rate
3. larger max_gain50_rate
4. lexicographically smaller pool_id
```

### 11.5 Stage 4: Robustness readout

只读，不调参，不改 pool。

输出：

```text
r04c_robustness_readout.csv
```

Robustness stage 只能对 validation-frozen `selected_candidate_pool_id` 给出 pass/fail final readout。其他 validation-passed pools 可以输出到 secondary readout，但不得改变 selected pool，也不得让 final decision 选择 robustness 表现最好的 pool。

## 12. Final Decision

允许的 final decision：

```text
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_price_materialization_mismatch
blocked_pool_definition_invalid
blocked_selection_leakage_detected
r04c_no_candidate_pool_passed_validation
r04c_candidate_pool_not_robust_scanner_complete
r04c_candidate_pool_passed_diagnostic_only
```

决策优先级：

1. 必需输入缺失 -> `blocked_missing_required_input`
2. R04 / R04b validation 未通过 -> `blocked_upstream_validation_failed`
3. price materialization 与 R04b baseline_A reconciliation 不一致 -> `blocked_price_materialization_mismatch`
4. pool registry 或 membership rule 无法冻结 -> `blocked_pool_definition_invalid`
5. 发现 validation / robustness leakage 且无法隔离 -> `blocked_selection_leakage_detected`
6. 无 train-selected pool 通过 validation -> `r04c_no_candidate_pool_passed_validation`
7. validation-frozen selected pool 的 robustness gate 失败 -> `r04c_candidate_pool_not_robust_scanner_complete`
8. validation-frozen selected pool 通过 robustness gate -> `r04c_candidate_pool_passed_diagnostic_only`

即使通过，也只能写：

```text
candidate pool passed diagnostic-only scanner;
eligible for future R04b-style hold/exit replay.
```

不得写：

```text
production ready
entry gate passed
R04c strategy passed
```

## 13. 必需输出

runner 必须写出：

```text
ep4/outputs/r04c_candidate_pool_scanner_v1/
  cache/
    r04c_pool_event_panel.parquet
    r04c_hold120_replay_panel.parquet
    r04c_matched_baseline_panel.parquet
    r04c_pool_selection_panel.parquet
  reports/
    r04c_source_readiness_audit.csv
    r04c_pool_registry_frozen.csv
    r04c_pool_definition_leakage_audit.csv
    r04c_pool_membership_waterfall.csv
    r04c_hold120_pool_profile.csv
    r04c_global_baseline_delta_summary.csv
    r04c_matched_baseline_delta_summary.csv
    r04c_train_pool_selection_trace.csv
    r04c_validation_gate_audit.csv
    r04c_robustness_readout.csv
    r04c_concentration_audit.csv
    r04c_overlap_uniqueness_audit.csv
    r04c_source_family_comparison.csv
    r04c_rejected_descriptive_leads.csv
    r04c_final_decision.csv
    r04c_candidate_pool_scanner_final_report.md
    r04c_candidate_pool_scanner_validation_audit.csv
  manifests/
    r04c_candidate_pool_scanner_manifest.json
    r04c_candidate_pool_scanner_validation.json
```

Cache parquet 可被 `.gitignore` 忽略；reports 和 manifests 是可追踪审计产物。

## 14. Schema 要求

### 14.1 `r04c_hold120_pool_profile.csv`

字段至少包含：

```text
pool_id
pool_family_id
pool_source_id
adapter_id
pool_promotability_status
split
event_count
replay_complete_count
censored_share
net_return_mean
net_return_p10
net_return_p90
loss_le_minus5_rate
loss_le_minus10_rate
max_gain50_count
max_gain50_rate
max_gain120d_p90
top1_calendar_year_share
top1_instrument_share
pool_denominator_status
```

### 14.2 `r04c_matched_baseline_delta_summary.csv`

字段至少包含：

```text
pool_id
split
matched_comparator_status
matched_comparator_count
matched_comparator_unique_event_count
matched_comparator_effective_sample_size
pool_net_return_mean
matched_baseline_net_return_mean
net_return_mean_delta_vs_matched_baseline_A
pool_net_return_p10
matched_baseline_net_return_p10
p10_delta_vs_matched_baseline_A
pool_loss_le_minus5_rate
matched_baseline_loss_le_minus5_rate
loss_le_minus5_delta_vs_matched_baseline_A
pool_max_gain50_rate
matched_baseline_max_gain50_rate
max_gain50_rate_delta_vs_matched_baseline_A
pool_top1_calendar_year_share
matched_baseline_top1_calendar_year_share
top1_calendar_year_share_delta_vs_matched_baseline_A
pool_top1_instrument_share
matched_baseline_top1_instrument_share
top1_instrument_share_delta_vs_matched_baseline_A
```

### 14.3 `r04c_final_decision.csv`

字段至少包含：

```text
final_decision
selected_candidate_pool_id
selected_pool_family_id
selected_pool_source_id
selected_adapter_id
selected_pool_type
validation_gate_pass
robustness_gate_pass
validation_selected_rank
validation_net_return_mean
robustness_net_return_mean
validation_net_return_mean_delta_vs_matched_baseline_A
robustness_net_return_mean_delta_vs_matched_baseline_A
validation_p10_delta_vs_matched_baseline_A
robustness_p10_delta_vs_matched_baseline_A
validation_loss_le_minus5_delta_vs_matched_baseline_A
robustness_loss_le_minus5_delta_vs_matched_baseline_A
validation_max_gain50_rate
robustness_max_gain50_rate
validation_top1_calendar_year_share
robustness_top1_calendar_year_share
validation_matched_baseline_top1_calendar_year_share
robustness_matched_baseline_top1_calendar_year_share
decision_reason
```

## 15. Validator Requirements

Validator 必须检查：

1. R04 / R04b validation status 为 `passed`。
2. 所有必需 reports / manifests 存在。
3. 所有 cache/reports/manifests 路径写入 manifest。
4. Local PIT price materialization 复用 R04b provider 语义，且 baseline_A reconciliation 通过。
5. `r04c_pool_registry_frozen.csv` 存在且 `membership_rule_hash` / `field_source_map_hash` 完整。
6. R04-derived logical fields 必须先经 `r04_derived_field_source_map` 解析；解析失败的 pool 必须 unavailable。
7. R03c promotable adapter 必须使用存在的 key / anchor / instrument columns；默认 key column 为 `pooling_key`，默认 anchor 为 `step_signal_date`。
8. R01 big-winner search 和 R02 winner-anchored source 在 v1 中必须保持 descriptive-only。
9. 所有 `pool_id` 稳定、唯一、非空。
10. 所有 promotable pool 的 `leakage_risk_class == no_known_oos_leakage`。
11. descriptive-only source 不得成为 selected pool。
12. selected pool 的 `adapter_id` 必须属于 v1 promotable adapter set。
13. train selection trace 的 `split_used` 只能是 `train`。
14. validation gate audit 的输入 pool 必须来自 train-selected pool。
15. validation gate audit 必须冻结唯一 `selected_candidate_pool_id`，且 selected rank == 1 among validation-passed pools。
16. robustness 不得出现在 selection trace 的 `split_used` 中。
17. robustness readout 不得改变 validation-frozen selected pool。
18. matched comparator insufficient 的 pool 不得 selected。
19. validation gate failed 的 pool 不得 selected。
20. robustness gate failed 时 final decision 不得为 passed。
21. concentration gate 必须使用 `max(0.50, matched_baseline_A_top1_calendar_year_share + 0.10)` 和 `max(0.05, matched_baseline_A_top1_instrument_share + 0.02)`。
22. pool event replay 不能包含 R04b exit policy columns as selection fields。
23. local PIT price provider hash 必须写入 manifest。
24. report 必须包含 mandatory boundary strings。

Mandatory boundary strings：

```text
R04c is candidate-pool scanner, not hold/exit policy replay.
R04c uses hold120 no-exit baseline only.
Matched baseline_A is mandatory for pool promotion.
Validation and robustness cannot define pool membership.
Robustness is final readout only.
No production entry rule is emitted by this scanner.
```

## 16. Final Report Requirements

Final report 必须用中文写出，并至少回答：

1. baseline_A 在 hold120 下的 train / validation / robustness profile 是什么？
2. 扫描了哪些 source，每个 source 有多少可用 pool？
3. 哪些 pool 是 promotable，哪些只能 descriptive？
4. train selection 选出了哪些 pool，选择分数和参数是什么？
5. 哪些 pool 在 validation 上通过 hard gates？
6. selected pool 在 robustness 中是否保持 net mean、loss<=-5、+50 winner rate 的改善？
7. 改善相对 matched baseline_A 是否仍存在？
8. 改善是否来自真实 path quality，而不是 calendar / industry concentration？
9. 是否有 pool 的 validation/robustness 同向？
10. 是否值得进入 R04b-style hold/exit/risk-budget replay？
11. validation-frozen selected pool 是否就是 robustness readout 的唯一 final candidate？

Final report 必须单独列出：

```text
matched_comparator_status != sufficient 的 pool 占比
pool_promotability_status != promotable 的 pool 占比
top1_calendar_year_share > 0.50 的 pool 占比
top1_calendar_year_share > max(0.50, matched_baseline_A_top1_calendar_year_share + 0.10) 的 pool 占比
validation passed but robustness failed 的 pool 列表
```

不得只展示最好看的 validation pool。

## 17. Implementation Checklist

- [ ] R04 validation passed.
- [ ] R04b validation passed.
- [ ] baseline_A control pool 与 R04/R04b 分母一致。
- [ ] Pool registry 在 replay 前冻结。
- [ ] Pool membership rule 不依赖 future outcome。
- [ ] descriptive-only source 不可 selected。
- [ ] selected pool 的 adapter 属于 v1 promotable adapter set。
- [ ] Train selection 不读取 validation / robustness。
- [ ] Validation 只评估 train-selected pools。
- [ ] Validation 阶段冻结唯一 selected_candidate_pool_id。
- [ ] Robustness 只读，不参与选择，且不得更换 validation-selected pool。
- [ ] Local PIT price provider / calendar / adjustment policy 写入 manifest。
- [ ] Matched baseline_A comparator 完整输出。
- [ ] Matched baseline_A comparator ESS 使用 Kish ESS 公式。
- [ ] Matched comparator insufficient 的 pool 不可 selected。
- [ ] hold120 replay 不包含 exit / CTA policy selection。
- [ ] validation 和 robustness 不允许 pooled OOS 互相掩盖。
- [ ] concentration / overlap / denominator shrink audit 完整输出。
- [ ] final report 用中文回答 Section 16 的问题。
- [ ] validator 输出 `validation_status: passed` 后，才可讨论是否进入 R04b-style replay。
