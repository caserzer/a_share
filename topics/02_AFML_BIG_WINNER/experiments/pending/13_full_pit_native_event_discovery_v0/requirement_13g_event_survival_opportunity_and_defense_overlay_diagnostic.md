# 需求：13G Event Survival Opportunity and Defense Overlay Diagnostic

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/13_full_pit_native_event_discovery_v0
SOURCE_EP12_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明、split boundary 不可证明、entry executability 不可证明、label horizon completeness 不可证明、feature availability 不可证明时 fail closed。
6. 不得从报告文本、图像或人工讨论文本反推出逐行 universe、标签、event membership、split 边界、entry 价格、decision point 或 path outcome。

## 1. 实验身份

```text
experiment_id = 13_full_pit_native_event_discovery_v0
phase_id = 13G
run_id = 13G_event_survival_opportunity_and_defense_overlay_diagnostic
status = spec_draft_pending_review
expected_entrypoint = src/run_13g_event_survival_opportunity_and_defense_overlay_diagnostic.py
expected_config = configs/config_13g_event_survival_opportunity_and_defense_overlay_diagnostic.yaml
expected_test_file = tests/test_13g_event_survival_opportunity_and_defense_overlay_diagnostic.py
upstream_requirement_13a3 = EXPERIMENT_ROOT/requirement_13a3_compression_repair_state_cost_and_native_feasibility_diagnostic.md
upstream_requirement_13c = EXPERIMENT_ROOT/requirement_13c_morphology_orthogonal_residual_importance_diagnostic.md
upstream_requirement_13e = EXPERIMENT_ROOT/requirement_13e_nonlinear_winner_train_kfold_feasibility_diagnostic.md
upstream_requirement_13f = EXPERIMENT_ROOT/requirement_13f_early_path_confirmation_delayed_entry_train_diagnostic.md
upstream_report_13c = EXPERIMENT_ROOT/outputs/publishable/reports/morphology_orthogonal_residual_importance_diagnostic_report.md
upstream_report_13e = EXPERIMENT_ROOT/outputs/publishable/reports/nonlinear_winner_train_kfold_feasibility_diagnostic_report.md
upstream_report_13f = EXPERIMENT_ROOT/outputs/publishable/reports/early_path_confirmation_delayed_entry_train_diagnostic_report.md
upstream_requirement_12a7g = SOURCE_EP12_ROOT/requirement_12a7g_vol_scaled_label_panel_c0_separability_triage.md
```

13G 是 13C / 13E / 13F 之后的新诊断分支。它不复活 t0 winner-entry search，不做 sequence mining，不做 meta-labeling 训练，也不授权 bet sizing。13G 的出发点是：

```text
13C: residual winner signal is probability-only and no utility
13E: nonlinear model capacity does not improve winner train-kfold utility
13F: delayed early-path confirmation does not improve delayed-entry utility
```

因此 13G 不再问“event 能否直接给 winner entry edge”，而是把 event 降级为：

```text
1. event-level survival / opportunity label carrier
2. rule-based defense / participation risk-budget state
```

13G 回答一个更窄的问题：

```text
在固定 event-level denominator 下，selected event 之后的 survival / opportunity / bad-side path
是否能被清晰量化；并且一个低自由度、非 ML 的 rule-based overlay 是否能在不牺牲过多 winner
opportunity 的前提下改善 after-cost utility、bad-side avoided 与 exposure-day return？
```

任何 13G decision 都必须固定：

```text
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
confirmatory_status = False
```

即使 13G diagnostic positive，也只能说明“rule-based risk-budget overlay 值得人工讨论或另开 confirmatory requirement”，不得声明可部署策略、meta-labeling ready 或 sizing ready。

## 2. 核心问题

13G 回答以下问题：

```text
Q1. 在 selected event repair_range_participation_core_30 的 event-level denominator 上，
    用 +20% / +30% / +50% MFE、-10% / -15% / -20% MAE、20d / 60d / 120d
    构造 survival / opportunity label panel 后，机会与坏侧是否可被拆开描述？

Q2. winner-before-fail、time-to-hit、survive-without-fail 这些路径标签是否说明：
    过去的“有 lift 但没 edge”主要来自机会概率不足、坏侧成本太高、timing 太早，
    还是重复事件 / density 吞掉 utility？

Q3. 在不训练 ML model 的前提下，一个预注册 rule-based defense / participation overlay
    是否能相对 baseline participation 改善 after-cost utility、bad-side avoided 与
    exposure-day return？

Q4. overlay 的改善若存在，是否仍保留足够 winner opportunity，而不是通过大量 skip / reduce
    牺牲未来 winner 换来表面 utility 改善？

Q5. 13G 是否只支持“label panel / defense overlay diagnostic”，还是提供足够证据让人工考虑
    单独的 confirmatory requirement？它不得直接授权 meta-labeling、bet sizing 或交易部署。
```

必须输出一个单一裁决：

```text
decision_state
```

## 3. Scope Boundary

13G 明确不是：

```text
t0 winner entry retry
13B sequence mining
nonlinear winner model retry
delayed entry retry
meta-labeling training
probability calibration
bet sizing
holding / exit / profit-protection policy
portfolio backtest
cost model calibration
production risk engine
```

13G 允许做的只有：

```text
1. 复用 13C full-split lineage 中的 selected event membership；13F 只作为 negative decision lineage；
2. 用 qfq daily bars 重建 event 后 20d / 60d / 120d 的 MFE / MAE / time-to-hit；
3. 在固定 event-level denominator 上生成 survival_opportunity_label_panel；
4. 计算 event uniqueness、concurrency、density 与 duplicate episode exposure；
5. 用预注册、低自由度、非 ML 的 rule-based overlay 生成 increase / keep / reduce / skip；
6. 比较 baseline participation 与 overlay participation 的 same-event after-cost utility、
   bad-side avoided、winner opportunity retained 与 exposure-day return；
7. 输出 diagnostic-only readout。
```

13G 不得产生任何 alpha、仓位、生产、交易或 meta-labeling 授权声明。13G 的 positive 只能是：

```text
rule-based defense / participation overlay diagnostic signal present
```

而不是：

```text
entry edge confirmed
meta-labeling ready
bet sizing ready
strategy deployable
```

## 4. 继承边界

### 4.1 允许继承

13G 可以继承：

```text
record_unit = instrument x reference_date
reference_date = PIT executable row date
entry_date = next executable open after reference_date
entry_price = qfq open at entry_date
selected_state_id = repair_range_participation_core_30
selected_event_membership from 13C full-split row-level rebuild only
native opportunity universe definition from 13A
13A3 selected composite state dictionary
13C feature cluster definitions and train-frozen buckets
13C exact event-span uniqueness reconstruction method
13F delayed-entry / early-path stop decision as negative lineage only
split boundary from 12A7g / 13A / 13C / 13E / 13F
cost_buffer_grid = [0bps, 50bps, 100bps]
reference_cost_buffer_return = 0.0100 unless upstream lineage proves otherwise
moderate_cost_buffer_return = 0.0050
```

13G 必须读取以下 lineage artifacts：

```text
outputs/publishable/tables/13A3_compression_repair_state_cost_and_native_feasibility_diagnostic/compression_repair_state_feasibility_decision.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_orthogonal_residual_importance_decision.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/feature_cluster_dictionary.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/sample_uniqueness_audit.csv
outputs/publishable/tables/13C_morphology_orthogonal_residual_importance_diagnostic/row_level_rebuild_audit.csv
outputs/local_cache/13C_morphology_orthogonal_residual_importance_diagnostic/morphology_residual_panel.parquet
outputs/publishable/tables/13E_nonlinear_winner_train_kfold_feasibility_diagnostic/nonlinear_winner_train_kfold_feasibility_decision.csv
outputs/publishable/tables/13F_early_path_confirmation_delayed_entry_train_diagnostic/early_path_confirmation_delayed_entry_decision.csv
```

13F 是 train-only diagnostic，13G 不得使用 13F row-level outputs、13F fold membership、13F train-only uniqueness 或 13F delayed-entry panels 来构造 13G 的全 split event universe。13F 只能作为“delayed-entry 路线已停”的 negative decision lineage。

Cache 校验项：

```text
row key uniqueness
instrument x reference_date coverage
split boundary equality
selected_state_id equality
selected event membership equality against 13C full-split membership
entry date / entry price rebuild equality for audited rows
feature cluster availability for rule-only context features
sha256 / schema hash when manifest provides it
```

Cache 校验失败时必须从 raw PIT universe 与 qfq daily bars 重建；不得 fail open。

### 4.2 禁止继承 / 禁止主张

13G 明确不得：

- 不重新搜索 selected event / state；
- 不新增 native token、composite state 或 directional filter；
- 不把 label panel 的最佳组合事后提升为主端点；
- 不用 validation / robustness 来 fit threshold、选择规则、选择 primary label 或调参；
- 不训练 logistic / tree / nonlinear / calibration / meta-labeling model；
- 不用 AUC 作为主指标；
- 不做 probability calibration；
- 不做 bet sizing；
- 不做 holding / exit policy；
- 不把 overlay multiplier 解释为真实生产仓位；
- 不把 diagnostic positive 解释为 OOS edge confirmed。

13G 不能主张：

```text
event is a deployable entry signal
selected state recovered deployability
meta-labeling will make the state profitable
bet sizing is ready
```

13G 只能主张：

```text
event-level survival/opportunity labels and a rule-based defense/participation overlay
do / do not show diagnostic utility improvement on a fixed same-event denominator.
```

## 5. 必需输入

### 5.1 Full PIT universe 与行情

同 13C / 13F：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/11_archetype_proxy_validation_system_v0/outputs/publishable/tables/11A0_regime_pit_availability_audit/regime_daily_series_audit.csv
```

每个 `(instrument, reference_date)` 必须唯一映射到：

```text
reference_pos
entry_pos = next executable open after reference_date
entry_price = qfq open at entry_pos
path_window_end_pos for H in {20, 60, 120}
```

任一 row 的 entry 不可执行、price 缺失、label horizon 不完整时，该 row 在对应 horizon 上标记 `not_evaluable`；全局 PIT / schema / split 失败时 fail closed。

### 5.2 Upstream decision requirements

13G 要求上游 decision table 满足：

```text
13A3: decision_state = 13A3_selected_composite_state_not_supported
      selected_state_id = repair_range_participation_core_30
      sequence_mining_authorized = False

13C: decision_state = 13C_stop_residual_probability_only_no_utility
      selected_state_id = repair_range_participation_core_30
      meta_labeling_authorized = False
      bet_sizing_authorized = False

13E: decision_state = 13E_stop_no_nonlinear_auc_improvement
      selected_state_id = repair_range_participation_core_30
      meta_labeling_authorized = False
      bet_sizing_authorized = False

13F: decision_state = 13F_stop_no_delayed_utility_improvement
      selected_state_id = repair_range_participation_core_30
      meta_labeling_authorized = False
      bet_sizing_authorized = False
```

若任一上游 lineage / row-level audit 未通过，13G 必须 fail closed：

```text
13G_blocked_upstream_lineage_failure
```

## 6. Event-Level Survival / Opportunity Label Panel

### 6.1 固定 denominator

13G 的 record unit 固定为：

```text
event_id = instrument + reference_date + selected_state_id
raw_event_denominator = all selected_state events with PIT executable entry_date
analysis_event_denominator =
  subset of raw_event_denominator with complete max_horizon_sessions = 120
  qfq path and valid split lineage
```

硬约束：

```text
1. denominator 是 event-level，不是 winner episode-level；
2. 所有 threshold / horizon 组合的主读数与 overlay gate 必须共享同一
   analysis_event_denominator，不得因 horizon shorter 而扩大分母；
3. raw_event_denominator 中不满足 analysis_event_denominator 的 rows 必须留在
   row-level audit，不得静默丢弃；
4. 同一 event 的所有 label variants 必须保留同一 split；
5. downstream overlay 也必须使用同一 analysis_event_denominator，未参与 / skip 的
   event 留在分母内。
```

`analysis_event_denominator` 的目的不是删除坏样本，而是让 27 个 label endpoint 与 overlay utility 在同一批可评价 events 上比较。所有被排除的 raw rows 必须按原因输出：

```text
entry_not_executable
entry_price_missing
max_horizon_path_incomplete
split_lineage_missing
qfq_bar_mapping_missing
```

Rule feature missing 不得把 row 从 `analysis_event_denominator` 中删除；这些 rows 必须 action 回退 `keep`，并计入 `rule_feature_missing_fraction`。只有缺失比例超过 config 上限时，`rule_freeze_gate_status = fail`。

Analysis coverage gate：

```text
analysis_event_fraction_by_split =
  analysis_event_n(split) / raw_event_n(split)

min_analysis_event_fraction_by_split = 0.80
min_analysis_event_n_by_split:
  train = 300
  validation = 100
  robustness = 100
```

若任一 split 的 `analysis_event_fraction_by_split` 低于阈值，或 `analysis_event_n` 低于最小样本数，`event_denominator_gate_status = fail`，且 decision 必须停在 `13G_blocked_event_denominator_failure`。若缺失主要来自样本尾部 120d horizon 不完整，报告必须明确这是 max-horizon complete cohort 的可评价性限制，而不是 overlay negative/positive evidence。

### 6.2 Label grid

预注册 label grid：

```text
up_mfe_threshold_grid = [0.20, 0.30, 0.50]
down_mae_threshold_grid = [-0.10, -0.15, -0.20]
horizon_sessions_grid = [20, 60, 120]
same_bar_priority = lower_first
primary_up_threshold = 0.30
primary_down_threshold = -0.15
primary_horizon_sessions = 60
legacy_big_winner_audit = up_0p50_H120
fast_fail_audit = down_m0p10_H20
```

主端点固定为：

```text
primary_survival_opportunity_endpoint = up_0p30_before_down_m0p15_H60
```

其余 26 个组合只作 sensitivity 与 mechanism readout，不得事后替代主端点。

### 6.3 Row-level path labels

对每个 `(event_id, up_threshold, down_threshold, horizon_sessions)` 输出：

```text
mfe_return
mae_return
terminal_return
upper_hit
lower_hit
time_to_upper_sessions
time_to_lower_sessions
first_touch_side              # upper / lower / vertical / ambiguous
winner_before_fail
fail_before_winner
survive_without_fail
opportunity_without_fail
same_bar_ambiguous
evaluable_flag
not_evaluable_reason
```

定义：

```text
winner_before_fail = upper_hit AND (time_to_upper < time_to_lower OR lower_hit = false)
fail_before_winner = lower_hit AND (time_to_lower <= time_to_upper OR upper_hit = false)
survive_without_fail = lower_hit = false through horizon
opportunity_without_fail = upper_hit AND fail_before_winner = false
```

若同一 bar 同时触及 upper 与 lower，主口径按 `lower_first`；同时输出 `same_bar_ambiguous = true`，并在 sensitivity 中给出 upper-first 影响，但不得用 upper-first 改写主裁决。

### 6.4 Label panel cache

必须输出 local cache：

```text
outputs/local_cache/13G_event_survival_opportunity_and_defense_overlay_diagnostic/survival_opportunity_label_panel.parquet
```

该 cache 至少包含：

```text
event_id
instrument
reference_date
entry_date
entry_price
split
selected_state_id
up_threshold
down_threshold
horizon_sessions
mfe_return
mae_return
terminal_return
upper_hit
lower_hit
first_touch_side
time_to_upper_sessions
time_to_lower_sessions
winner_before_fail
fail_before_winner
survive_without_fail
opportunity_without_fail
same_bar_ambiguous
evaluable_flag
not_evaluable_reason
```

## 7. Event Uniqueness / Density / Duplicate Audit

13G 必须重新计算 event-level uniqueness，不得只继承 13C/13F summary。

### 7.1 Event span

主 span：

```text
event_span_start_pos = entry_pos
event_span_end_pos = entry_pos + max(horizon_sessions_grid) - 1
```

同时输出 threshold-specific first-touch span：

```text
touch_span_end_pos = min(first_touch_pos, entry_pos + horizon_sessions - 1)
```

主 uniqueness gate 使用 max-horizon event span，避免低估 overlapping exposure；touch span 仅作诊断。

### 7.2 必需指标

必须输出：

```text
average_uniqueness
median_uniqueness
p10_uniqueness
p90_concurrency
event_density_per_instrument_year
rolling_20d_event_count_mean
rolling_20d_event_count_p95
duplicate_episode_event_count
duplicate_episode_fraction
```

duplicate episode 定义：

```text
同一 instrument 上，两个 event 的 max-horizon event_span 有重叠，且第二个 event
发生在第一个 event 的 horizon 结束前。
```

若 exact uniqueness 不可重建：

```text
13G_stop_uniqueness_unavailable_for_overlay
```

## 8. Rule-Based Defense / Participation Overlay

### 8.1 Overlay intent

13G 的 overlay 不是 entry signal。它只模拟当 selected event 发生后，对一单位 baseline participation 的风险预算调整：

```text
action in {increase, keep, reduce, skip}
risk_budget_multiplier:
  increase = 1.50
  keep     = 1.00
  reduce   = 0.50
  skip     = 0.00
```

`baseline participation` 是诊断用一单位事件风险预算，不代表真实组合当前持仓，也不构成交易建议。

### 8.2 Rule features

Rule features 只能使用 event 当日可得的 t0 context，不得使用 event 后路径：

```text
t0_ret_20d_bucket
t0_max_drawdown_20d_bucket
t0_distance_to_20d_low_bucket
t0_volatility_20d_bucket
t0_liquidity_or_turnover_bucket if available in 13C panel
t0_compression_repair_feature_cluster buckets from 13C
t0_prior_selected_event_count_20d_bucket
t0_active_selected_event_count_120d_bucket
t0_market_selected_event_count_today_bucket
```

t0 crowding features 的可用性定义：

```text
t0_prior_selected_event_count_20d =
  count of same-instrument selected_state events with reference_date in
  [current_reference_date - 20 sessions, current_reference_date)

t0_active_selected_event_count_120d =
  count of same-instrument selected_state events with prior reference_date
  whose fixed 120-session scheduled event span still includes current entry_date

t0_market_selected_event_count_today =
  count of selected_state events across instruments on current_reference_date
```

这些 crowding features 只依赖已经发生的 event timestamps 与预注册固定 horizon，不得使用未来 realized first-touch、future overlap、future duplicate episode 或未来收益。`duplicate_episode_event_count` 是 ex-post density audit 字段，严禁作为 rule feature。

阈值来源：

```text
1. 优先沿用 13C train-frozen buckets；
2. 若 13C 未提供某 rule feature 的 bucket，则只允许在 train split 上 freeze
   tercile / p80 thresholds，并写入 rule_overlay_dictionary；
3. validation / robustness 不得参与 threshold freeze。
```

### 8.3 Pre-registered rule family

第一版只允许以下低自由度规则族：

```text
defense_skip_rule:
  action = skip
  when badside_risk_context = high
       AND opportunity_context != high

defense_reduce_rule:
  action = reduce
  when badside_risk_context = medium
       OR t0_known_crowding_context = crowded

participation_increase_rule:
  action = increase
  when opportunity_context = high
       AND badside_risk_context = low
       AND t0_known_crowding_context != crowded

default_rule:
  action = keep
```

Context definitions must be frozen before scoring validation / robustness:

```text
badside_risk_context:
  high   if at least 2 of:
           t0_max_drawdown_20d_bucket = severe
           t0_distance_to_20d_low_bucket = near_low
           t0_volatility_20d_bucket = high
           t0_ret_20d_bucket = weak
  medium if exactly 1 of the above is true
  low    if none of the above is true

opportunity_context:
  high   if:
           t0_ret_20d_bucket in {flat, positive}
           AND t0_distance_to_20d_low_bucket in {mid, far_from_low}
           AND t0_max_drawdown_20d_bucket != severe
           AND t0_compression_repair_feature_cluster_status != unfavorable
  medium if:
           t0_ret_20d_bucket in {flat, positive}
           OR t0_distance_to_20d_low_bucket in {mid, far_from_low}
  low    otherwise

t0_known_crowding_context:
  crowded if:
           t0_prior_selected_event_count_20d_bucket = high
           OR t0_active_selected_event_count_120d_bucket = high
           OR t0_market_selected_event_count_today_bucket = high
  normal  otherwise
```

Bucket label construction must be deterministic:

```text
ret_20d_bucket: weak / flat / positive
max_drawdown_20d_bucket: mild / moderate / severe
distance_to_20d_low_bucket: near_low / mid / far_from_low
volatility_20d_bucket: low / medium / high
crowding count buckets: low / medium / high, with high = train-frozen p80 or above
t0_compression_repair_feature_cluster_status:
  favorable / neutral / unfavorable if 13C provides a deterministic non-outcome
  feature-cluster direction; otherwise neutral for all rows with
  cluster_status_source = neutral_fallback
```

每个 bucket 的 source column、threshold、direction、train row count 必须写入 `rule_overlay_dictionary.csv`。不得增加模型、score、fit 权重、网格搜索或事后挑规则。若任何 required bucket 无法构造，action 必须退回 `keep` 并标记 `rule_feature_missing_caveat`；若缺失比例超过 config 上限（默认 5%），`rule_freeze_gate_status = fail`。若需要超过上述规则族，必须另开 requirement。

### 8.4 Overlay utility accounting

主 utility 使用 primary endpoint 的 path utility，并对每个 cost tier 独立计算：

```text
cost_tier_bps in {0, 50, 100}
cost_buffer_return_by_tier:
  0bps   = 0.0000
  50bps  = 0.0050
  100bps = 0.0100

overlay_adjustment_cost_buffer_by_tier:
  0bps   = 0.0000
  50bps  = 0.0050
  100bps = 0.0100

primary_path_utility_component_{cost_tier_bps} =
  1[winner_before_fail] * up_threshold
  + 1[fail_before_winner] * down_threshold
  + 1[first_touch_side = vertical] * terminal_return
  - cost_buffer_return_by_tier[cost_tier_bps]
```

Overlay per-event utility：

```text
baseline_per_event_utility_{cost_tier_bps} =
  1.00 * primary_path_utility_component_{cost_tier_bps}

overlay_path_exposure_component_{cost_tier_bps} =
  risk_budget_multiplier(action) * primary_path_utility_component_{cost_tier_bps}

overlay_adjustment_cost_component_{cost_tier_bps} =
  abs(risk_budget_multiplier(action) - 1.00)
  * overlay_adjustment_cost_buffer_by_tier[cost_tier_bps]

overlay_per_event_utility_{cost_tier_bps} =
  overlay_path_exposure_component_{cost_tier_bps}
  - overlay_adjustment_cost_component_{cost_tier_bps}
```

主 gate 使用 50bps tier；0bps 与 100bps 是 sensitivity / cost robustness readout。13G 的 overlay 假设是“对既有 baseline participation 做风险预算调整”。因此 `skip` 表示把原本 1.00 的 event risk budget 降到 0.00：它没有路径 exposure，但需要支付对应 cost tier 的 adjustment cost；其 utility 为 `-overlay_adjustment_cost_buffer_by_tier[cost_tier_bps]`，不是从分母删除，也不是免费跳过。`increase` 不是授权加仓，只是诊断风险预算 multiplier。

## 9. Metrics

### 9.1 Survival / opportunity readout

必须输出每个 `(split, up_threshold, down_threshold, horizon_sessions)`：

```text
raw_event_n
analysis_event_n
analysis_event_fraction
evaluable_n
not_evaluable_n
rate_denominator = analysis_event_n
upper_hit_rate
lower_hit_rate
winner_before_fail_rate
fail_before_winner_rate
survive_without_fail_rate
opportunity_without_fail_rate
median_time_to_upper
median_time_to_lower
terminal_return_mean
mfe_return_mean
mae_return_mean
same_bar_ambiguous_rate
```

所有 rate 字段的分母固定为 `analysis_event_n`。`raw_event_n - analysis_event_n` 的差异必须在 row-level audit 和 label grid readout 中按 not-evaluable reason 拆出；不得让 shorter horizon endpoint 使用更大的分母。

### 9.2 Overlay readout

必须在 train / validation / robustness 各 split 输出：

```text
raw_event_n
analysis_event_n
analysis_event_fraction
rate_denominator = analysis_event_n
baseline_utility_per_event_mean_0bps
baseline_utility_per_event_mean_50bps
baseline_utility_per_event_mean_100bps
overlay_utility_per_event_mean_0bps
overlay_utility_per_event_mean_50bps
overlay_utility_per_event_mean_100bps
delta_overlay_vs_baseline_50bps
baseline_exposure_mean
overlay_exposure_mean
baseline_exposure_day_return_50bps
overlay_exposure_day_return_50bps
badside_avoided_rate
winner_opportunity_retained_rate
badside_support_caveat
winner_retention_support_caveat
increase_fraction
keep_fraction
reduce_fraction
skip_fraction
average_uniqueness
event_density_per_instrument_year
```

Definitions：

```text
badside_avoided_rate =
  count(fail_before_winner AND action in {reduce, skip}) / count(fail_before_winner)

winner_opportunity_retained_rate =
  count(winner_before_fail AND action in {increase, keep}) / count(winner_before_fail)

overlay_exposure_mean =
  mean(risk_budget_multiplier)

baseline_exposure_mean =
  1.00

baseline_exposure_day_return_50bps =
  sum(baseline_per_event_utility_{cost_tier_bps=50})
  / sum(1.00 * horizon_exposure_days)

overlay_exposure_day_return_50bps =
  sum(overlay_per_event_utility_{cost_tier_bps=50})
  / sum(risk_budget_multiplier * horizon_exposure_days)

horizon_exposure_days =
  primary_horizon_sessions for all analysis events unless first_touch_side in {upper, lower};
  if first_touch_side in {upper, lower}, use first touch session count clipped to [1, primary_horizon_sessions].
```

若 `sum(risk_budget_multiplier * horizon_exposure_days) = 0`，`overlay_exposure_day_return_50bps` 必须标记为 not_evaluable，且 `overlay_utility_gate_status` 不得 pass。

`winner_opportunity_retained_rate` 分母为 primary endpoint 下的 `winner_before_fail` event。若该分母过小，必须标记 `winner_retention_support_caveat`，不得 pass gate。

`badside_avoided_rate` 分母为 primary endpoint 下的 `fail_before_winner` event。若该分母为 0 或小于 config 最小支持数（默认 `min_badside_event_n_by_split = 30`），必须标记 `badside_support_caveat`，且 `density_adjustment_gate_status` 与 `winner_retention_gate_status` 不得单独把该 split 解释为 defense evidence。

## 10. Required Outputs

Publishable tables：

```text
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/input_artifact_audit.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/upstream_lineage_audit.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/row_level_rebuild_audit.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/survival_opportunity_label_grid_readout.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/time_to_hit_distribution.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/event_uniqueness_density_audit.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/rule_overlay_dictionary.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/rule_overlay_action_distribution.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/rule_overlay_utility_readout.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/rule_overlay_winner_retention_audit.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/search_multiplicity_audit.csv
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/event_survival_opportunity_overlay_decision.csv
```

Local cache：

```text
outputs/local_cache/13G_event_survival_opportunity_and_defense_overlay_diagnostic/survival_opportunity_label_panel.parquet
outputs/local_cache/13G_event_survival_opportunity_and_defense_overlay_diagnostic/rule_overlay_event_panel.parquet
```

Report：

```text
outputs/publishable/reports/event_survival_opportunity_and_defense_overlay_diagnostic_report.md
```

Manifest：

```text
outputs/manifests/13G_event_survival_opportunity_and_defense_overlay_diagnostic_manifest.json
```

## 11. Decision Gates

13G gate statuses：

```text
input_gate_status
upstream_lineage_gate_status
row_level_rebuild_gate_status
label_panel_gate_status
event_denominator_gate_status
event_uniqueness_gate_status
rule_freeze_gate_status
overlay_utility_gate_status
winner_retention_gate_status
density_adjustment_gate_status
search_accounting_status
```

### 11.1 Gate pass requirements

`label_panel_gate_status = pass` requires：

```text
全部 3 x 3 x 3 label grid 已生成；
primary endpoint 固定为 up_0p30_before_down_m0p15_H60；
same_bar_priority = lower_first；
not-evaluable rows 被显式审计；
没有 event 后路径、future overlap 或 duplicate_episode 字段进入 t0 rule features。
```

`event_denominator_gate_status = pass` requires：

```text
所有 label variants 与 overlay readout 使用同一 analysis_event_denominator；
raw_event_denominator 与 analysis_event_denominator 的差异被按原因审计；
train / validation / robustness 的 analysis_event_fraction 均 >= 0.80；
train / validation / robustness 的 analysis_event_n 均达到 min_analysis_event_n_by_split；
skip / reduce / not-evaluable rows 未被静默删除；
split 边界与上游一致。
```

`event_uniqueness_gate_status = pass` requires：

```text
max-horizon event span exact uniqueness 可重建；
average uniqueness / concurrency / duplicate episode fraction 已输出；
若 average_uniqueness 过低，decision 仍可继续，但必须带 density caveat。
```

`rule_freeze_gate_status = pass` requires：

```text
规则族固定为 defense_skip / defense_reduce / participation_increase / default；
所有 thresholds 只来自 13C frozen buckets 或 train split freeze；
validation / robustness 未参与 rule construction；
duplicate_episode_count / future overlap / future first-touch 未参与 rule construction；
没有 ML model、score fitting、hyperparameter search。
```

`overlay_utility_gate_status = pass` requires（主经济 gate）：

```text
validation delta_overlay_vs_baseline_50bps > 0
AND robustness delta_overlay_vs_baseline_50bps >= 0
AND train delta_overlay_vs_baseline_50bps > 0
AND overlay_exposure_day_return_50bps(validation) > baseline_exposure_day_return_50bps(validation)
AND overlay_exposure_day_return_50bps(robustness) >= baseline_exposure_day_return_50bps(robustness)
```

`winner_retention_gate_status = pass` requires：

```text
winner_opportunity_retained_rate(validation) >= 0.80
AND winner_opportunity_retained_rate(robustness) >= 0.75
AND badside_support_caveat = false for validation / robustness
AND winner_retention_support_caveat = false
```

`density_adjustment_gate_status = pass` requires：

```text
utility improvement is not solely concentrated in ex-post duplicate episodes;
event density, t0-known crowding, and ex-post duplicate episode fraction are explicitly reported;
skip / reduce counts from ex-post duplicate episodes are separately audited;
duplicate_episode_count is never used as a rule feature.
```

### 11.2 Decision states

```text
13G_blocked_input_or_lineage_failure
13G_blocked_upstream_lineage_failure
13G_blocked_row_level_rebuild_failure
13G_blocked_label_panel_failure
13G_blocked_event_denominator_failure
13G_stop_uniqueness_unavailable_for_overlay
13G_blocked_rule_freeze_failure
13G_stop_label_panel_only_no_overlay_utility
13G_stop_overlay_improves_by_winner_sacrifice
13G_stop_overlay_improvement_density_artifact
13G_diagnostic_survival_overlay_signal_present
```

## 12. Search / Multiplicity Accounting

13G 同时输出 27 个 label endpoint 与 4 个 action buckets，必须显式记账：

```text
up_threshold_n = 3
down_threshold_n = 3
horizon_n = 3
label_endpoint_n = 27
primary_endpoint = up_0p30_before_down_m0p15_H60
action_n = 4
rule_family_n = 1
ml_model_used = false
hyperparameter_search_used = false
validation_used_for_rule_freeze = false
robustness_used_for_rule_freeze = false
effective_search_space_n = 27
confirmatory_status = false
search_accounting_status = diagnostic_pre_registered_primary_endpoint
```

非主 endpoint 的 positive 不得升级 decision。若只有 `+50% / 120d` 或 `+20% / 20d` 等非主 endpoint 有漂亮读数，报告只能写为 sensitivity，不得改写主裁决。

## 13. Decision Precedence

严格优先级：

```text
1. 13G_blocked_input_or_lineage_failure
2. 13G_blocked_upstream_lineage_failure
3. 13G_blocked_row_level_rebuild_failure
4. 13G_blocked_label_panel_failure
5. 13G_blocked_event_denominator_failure
6. 13G_stop_uniqueness_unavailable_for_overlay
7. 13G_blocked_rule_freeze_failure
8. overlay_utility_gate_status != pass -> 13G_stop_label_panel_only_no_overlay_utility
9. overlay utility improves but winner_retention_gate_status != pass
   -> 13G_stop_overlay_improves_by_winner_sacrifice
10. overlay utility improves but density_adjustment_gate_status != pass
    -> 13G_stop_overlay_improvement_density_artifact
11. overlay utility + winner retention + density adjustment all pass
    -> 13G_diagnostic_survival_overlay_signal_present
```

No decision may be upgraded by non-primary endpoint, selected-entry-only utility, AUC, probability score, or posthoc rule variant。

## 14. Final Decision Output

必须输出：

```text
outputs/publishable/tables/13G_event_survival_opportunity_and_defense_overlay_diagnostic/event_survival_opportunity_overlay_decision.csv
```

字段：

```text
decision_state
next_allowed_requirement
sequence_mining_authorized
meta_labeling_authorized
bet_sizing_authorized
selected_state_id
primary_endpoint
effect_interpretation
confirmatory_status
raw_event_n
analysis_event_n
analysis_event_fraction
rule_feature_missing_fraction
badside_support_caveat
winner_retention_support_caveat
input_gate_status
upstream_lineage_gate_status
row_level_rebuild_gate_status
label_panel_gate_status
event_denominator_gate_status
event_uniqueness_gate_status
rule_freeze_gate_status
overlay_utility_gate_status
winner_retention_gate_status
density_adjustment_gate_status
validation_used_for_rule_freeze
robustness_used_for_rule_freeze
ml_model_used
hyperparameter_search_used
search_accounting_status
primary_failure_reason
survival_opportunity_readout
overlay_capacity_readout
```

所有 decision 固定：

```text
sequence_mining_authorized = False
meta_labeling_authorized = False
bet_sizing_authorized = False
confirmatory_status = False
```

`next_allowed_requirement` 取值：

```text
none
manual_review_only
```

只有 `13G_diagnostic_survival_overlay_signal_present` 可以写：

```text
next_allowed_requirement = manual_review_only
```

这只表示人工可考虑另开独立 confirmatory requirement；不得自动生成 13H，不得直接授权 meta-labeling 或 sizing。

`overlay_capacity_readout` 取值：

```text
label_panel_only_no_overlay_utility
overlay_improves_by_winner_sacrifice
overlay_improvement_density_artifact
rule_based_overlay_utility_signal_present
blocked_or_not_evaluable
```

## 15. Report Requirements

报告必须用中文写，并包含：

1. 单行裁决：13G 是否只是 label panel diagnostic，还是 rule-based overlay 也有 utility signal。
2. 为什么 13G 不推翻 13C / 13E / 13F：前者否决的是 t0 winner entry、非线性 winner 模型与 delayed entry；13G 只评估 event-level survival / opportunity 与 risk-budget overlay。
3. 固定 denominator 声明：raw event denominator、analysis event denominator、max-120d complete cohort 的差异、各 split analysis coverage gate 是否通过，以及所有 label variants、overlay actions、skip / reduce events 都在同一 analysis denominator 内。
4. Survival / opportunity label panel：+20/+30/+50、-10/-15/-20、20/60/120 的完整 readout，并突出主端点 `+30 before -15 within 60d`。
5. 机会与坏侧拆解：winner-before-fail、fail-before-winner、survive-without-fail、time-to-hit 说明 lift 为何未自动变成 edge。
6. Event uniqueness / density：average uniqueness、t0-known crowding、ex-post duplicate episode fraction、event density 与 overlay action distribution；明确 duplicate episode 没有进入 rule input。
7. Rule overlay dictionary：increase / keep / reduce / skip 的规则、阈值来源、train freeze 证据，明确没有 ML / AUC / probability score。
8. Overlay utility：baseline vs overlay 的 0/50/100bps utility、50bps 主 gate、bad-side avoided、winner opportunity retained、exposure-day return，并说明 adjustment cost 随 cost tier 变化。
9. Winner / badside support audit：若 overlay 改善 utility，必须说明是否通过牺牲 winner opportunity 获得，并报告 badside_support_caveat / winner_retention_support_caveat。
10. Density artifact audit：若 overlay 改善主要集中在 ex-post duplicate episodes，必须降级解释；同时说明 duplicate episode 仅用于 audit，不用于 rule。
11. Sensitivity：非主 26 个 endpoint 的结果只作机制解释，不得覆盖主端点 decision。
12. 明确结论：是否值得人工考虑另开 confirmatory requirement；同时强调不授权 meta-labeling、bet sizing、entry policy 或生产仓位。

报告必须避免以下措辞：

```text
alpha discovered
deployable strategy
confirmed edge
meta-labeling ready
bet sizing ready
position sizing validated
```

## 16. Test Requirements

必须实现 synthetic tests，不依赖大文件：

1. `test_path_resolution_contract`
   确认路径解析规则。

2. `test_upstream_stop_states_required`
   13A3/13C/13E/13F 未处于预期 stop 状态或授权 flags 异常时，13G 必须 blocked。

3. `test_selected_membership_from_13c_full_split`
   13G event universe 必须来自 13C full-split membership；若使用 13F train-only row / fold / uniqueness artifact 构造 universe，必须 fail。

4. `test_event_denominator_fixed`
   所有 label variants 与 overlay readout 必须共享同一 analysis_event_denominator；若按 winner episode 分母或 endpoint-specific evaluable 分母计算必须 fail。

5. `test_analysis_denominator_max_horizon_complete`
   analysis denominator 必须要求 max_horizon_sessions=120 完整可评价；shorter horizon 不得扩大分母。

6. `test_analysis_denominator_coverage_gate`
   任一 split 的 `analysis_event_fraction` 低于 0.80 或 `analysis_event_n` 低于最小样本数时，必须 `13G_blocked_event_denominator_failure`。

7. `test_label_grid_complete`
   必须生成 3 x 3 x 3 label grid；缺任一 endpoint 时 `13G_blocked_label_panel_failure`。

8. `test_primary_endpoint_fixed`
   主端点固定为 `up_0p30_before_down_m0p15_H60`；非主 endpoint 不能改写 decision。

9. `test_same_bar_lower_first`
   同一 bar 同时触及 upper/lower 时主口径必须 lower-first，并记录 same_bar_ambiguous。

10. `test_time_to_hit_and_survival_labels`
    winner_before_fail、fail_before_winner、survive_without_fail、opportunity_without_fail 的布尔逻辑必须正确。

11. `test_not_evaluable_rows_retained`
    horizon 不完整或 entry 不可执行的 rows 必须进入 audit，不得静默删除。

12. `test_no_future_data_in_rule_features`
    rule features 只能使用 t0 context；若使用 event 后 MFE/MAE/time-to-hit 必须 fail。

13. `test_no_future_duplicate_in_rule_features`
    duplicate_episode_event_count、future overlap、future first-touch 不得进入 action rule；若参与 rule construction 必须 fail。

14. `test_t0_known_crowding_only`
    t0 crowding 只能由 prior selected events、fixed scheduled 120d span、same-day market event count 构造；不得使用未来 realized path。

15. `test_rule_freeze_train_only`
    新阈值只能在 train split freeze；validation / robustness 参与 freeze 时必须 `13G_blocked_rule_freeze_failure`。

16. `test_rule_feature_missing_kept_default_keep`
    rule feature 缺失的 analysis rows 必须保留在分母内并 action 回退 keep；若静默删除必须 fail，若缺失比例超过上限则 `rule_freeze_gate_status=fail`。

17. `test_no_ml_model_or_score`
    若 runner fit logistic/tree/calibration/meta-labeling model，必须 fail；`ml_model_used=false`。

18. `test_action_multiplier_mapping`
    increase/keep/reduce/skip 必须分别映射到 1.50/1.00/0.50/0.00。

19. `test_skip_kept_in_denominator`
    skip events 必须留在 same-event denominator，不能被删除。

20. `test_overlay_cost_tier_formula`
    0/50/100bps 必须使用同一 generic utility formula；adjustment cost 必须随 cost tier 使用 0/50/100bps 对应成本。

21. `test_overlay_incremental_cost_applied`
    risk budget multiplier 偏离 1.00 时必须扣除对应 cost tier 的 adjustment cost；skip 的 path exposure 为 0 但 adjustment cost 不得遗漏。

22. `test_baseline_exposure_day_return_output`
    `rule_overlay_utility_readout.csv` 必须输出 baseline 与 overlay exposure-day return；gate 不得引用未输出字段。

23. `test_badside_avoided_and_winner_retained`
    badside_avoided_rate 与 winner_opportunity_retained_rate 的分母必须正确。

24. `test_badside_support_caveat`
    primary endpoint 下 badside 分母为 0 或低于最小支持数时，必须标记 `badside_support_caveat`，且不能把该 split 解释为 defense evidence。

25. `test_exact_uniqueness_max_horizon_span`
    exact uniqueness 必须使用 max-horizon event span；只用 first-touch span 时必须 fail。

26. `test_density_artifact_gate`
    overlay 改善若主要集中在 ex-post duplicate episodes，必须输出 `13G_stop_overlay_improvement_density_artifact`；duplicate episode 不得是 rule input。

27. `test_overlay_no_utility_stop`
    主 endpoint 下 overlay utility 未改善时 → `13G_stop_label_panel_only_no_overlay_utility`。

28. `test_overlay_winner_sacrifice_stop`
    utility 改善但 winner retention 不达标时 → `13G_stop_overlay_improves_by_winner_sacrifice`。

29. `test_overlay_signal_present_decision`
    utility、winner retention、density adjustment 全过时 → `13G_diagnostic_survival_overlay_signal_present`，但 authorization flags 仍为 false。

30. `test_no_authorization_invariants`
    任何 decision 都必须 `sequence_mining_authorized=False`、`meta_labeling_authorized=False`、`bet_sizing_authorized=False`、`confirmatory_status=False`。

31. `test_search_accounting`
    必须输出 `effective_search_space_n=27`、`hyperparameter_search_used=false`、`search_accounting_status=diagnostic_pre_registered_primary_endpoint`。

## 17. Implementation Order

建议实现顺序：

1. Parse config and resolve paths.
2. Load upstream 13A3 / 13C / 13E / 13F decisions and assert required stop states.
3. Load or rebuild selected event row panel from 13C full-split morphology_residual_panel under PIT constraints; use 13F only as negative decision lineage.
4. Rebuild entry_pos / entry_price from qfq daily bars and PIT executable universe.
5. Construct raw_event_denominator and analysis_event_denominator using max-120d complete path requirements.
6. Generate full survival / opportunity label grid for 3 up thresholds x 3 down thresholds x 3 horizons on the fixed analysis denominator.
7. Write label panel cache and label grid readout, including raw-vs-analysis exclusion reasons.
8. Recompute max-horizon event uniqueness, t0-known crowding, density and ex-post duplicate episode audit.
9. Build train-frozen rule context buckets using 13C buckets or train-only freeze; verify no future duplicate / future overlap fields are rule inputs.
10. Apply pre-registered rule family to all splits; produce increase / keep / reduce / skip actions.
11. Compute baseline vs overlay utility, bad-side avoided, winner retained and exposure-day return on same analysis denominator.
12. Apply gates and decision precedence using primary endpoint only.
13. Write publishable tables, local caches, report, manifest and synthetic tests.

No step may use event-post path data, future duplicate episodes, future overlap, or future first-touch as rule features. No step may use 13F train-only rows to construct the 13G universe, switch denominator to winner episodes, drop skip rows, train a model, use validation / robustness to freeze rules, select a non-primary endpoint after seeing results, or convert diagnostic positive into meta-labeling / bet-sizing authorization.
