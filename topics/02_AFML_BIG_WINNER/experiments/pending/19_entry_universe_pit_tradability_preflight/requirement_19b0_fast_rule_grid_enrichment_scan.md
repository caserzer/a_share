# Requirement: 19B0 快速规则网格右尾富集扫描

## 0. 不可协商范围

19B0 是 EP19 在 19A 合同冻结之后的第一个 outcome readout 阶段，但它只允许在
`train` split 上做预注册规则网格的快速筛选。19B0 的任务是决定哪些
`family_id / grid_cell_id` 有资格进入 19B 的正式 robustness confirmation。

19B0 不训练模型，不生成交易策略，不运行组合回测，不读取 validation outcome，不用
robustness outcome 做选择，也不声明任何 out-of-sample 支持。19B0 的正向结论只能是：

```text
decision_state = 19B0_candidate_family_eligible_for_19B
next_allowed_requirement = requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md
```

该正向结论只表示：预注册 family/cell 在 train 上达到进入 19B 的候选资格。
它不是 alpha 支持、不是策略可用、不是 robustness 通过，也不能授权 19C replay。

允许的 19B0 决策状态：

```text
19B0_candidate_family_eligible_for_19B
19B0_candidate_family_train_diagnostic
19B0_no_candidate_family_passed
19B0_upstream_19a_contract_blocked
19B0_train_only_boundary_blocked
19B0_grid_contract_blocked
19B0_baseline_materialization_blocked
19B0_metric_contract_blocked
19B0_output_contract_blocked
```

## 1. 身份

```text
experiment_id = 19_entry_universe_pit_tradability_preflight
phase_id = 19B0
run_id = 19B0_fast_rule_grid_enrichment_scan
requirement_file = requirement_19b0_fast_rule_grid_enrichment_scan.md
config_file = configs/config_19b0_fast_rule_grid_enrichment_scan.yaml
runner_file = src/run_19b0_fast_rule_grid_enrichment_scan.py
test_file = tests/test_19b0_fast_rule_grid_enrichment_scan.py
```

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

所有路径必须通过 config 或显式 path alias 解析。实现不得硬编码
`/home/xiaolv/...` 绝对路径。

## 2. 上游 19A 闭包

19B0 必须首先读取并验证 19A 输出：

```text
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/entry_universe_preflight_decision.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/manifest_19a_entry_universe_pit_lineage_tradability_and_data_contract.json
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/candidate_density_and_overlap_audit.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/effective_sample_size_readout.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/grid_search_manifest.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/family_search_accounting_manifest.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/baseline_budget_freeze.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/baseline_matching_spec.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/baseline_matching_quality_audit.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/primary_metric_and_margin_freeze.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/multiple_testing_correction_freeze.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/validation_stress_rule_freeze.csv
```

必需 19A 事实：

```text
decision_state = 19A_entry_universe_contract_ready
next_allowed_requirement = requirement_19b0_fast_rule_grid_enrichment_scan.md
all_critical_gates_pass = true
model_training_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

如果 19A 输出缺失、hash 不一致、决策不是 ready、或授权任何 policy/trading 行为，
19B0 必须停止：

```text
decision_state = 19B0_upstream_19a_contract_blocked
```

19A / 19B0 denominator boundary:

```text
19A:
    owns readout-only materialization of candidate density, path completeness,
    sample support, and effective sample size gates.
    Required artifacts:
        candidate_density_and_overlap_audit.csv
        effective_sample_size_readout.csv

19B0:
    consumes 19A all_critical_gates_pass = true and the two 19A audit artifacts.
    It may materialize train grid cells and train matched baselines under the
    frozen 19A denominator, but it must not redefine 19A sample-support gates.
```

If `candidate_density_and_overlap_audit.csv` or `effective_sample_size_readout.csv`
is missing, stale relative to the 19A manifest, or inconsistent with the 19A
decision row, 19B0 must stop with `19B0_upstream_19a_contract_blocked`.

## 3. 研究问题

19B0 只回答 train-only triage 问题：

```text
Q1. 在 19A 冻结的 primary_enrichment_denominator 上，哪些预注册
    simple rule family/cell 在 train split 上显示右尾富集？

Q2. 这些 train-only 读数是否超过冻结的最低 train triage 门槛，并足以进入
    19B 的 robustness confirmation？

Q3. matched baseline 是否可以在 train split 上按 19A 冻结规则物化，并产出
    质量审计？

Q4. 进入 19B 的 family/cell 数量、correction scope 和 robustness_test_manifest
    是否已经在读取 robustness outcome 之前冻结？
```

19B0 不回答：

```text
1. 该规则是否在 robustness 上有效。
2. 该规则是否在 validation 上有效。
3. 该规则是否有策略收益。
4. 该规则是否值得进入 19C replay。
5. 该规则是否可部署。
```

## 4. 允许和禁止工作

允许：

```text
1. 读取 19A 合同、manifest、audit 和 frozen grid。
2. 先从候选元数据构造 train event key，再只为 train event key 读取/连接 label 字段。
3. 读取 baseline eligible universe 所需的 PIT universe、行情和 as-of matching 字段。
4. 物化 train split 的预注册 simple rule grid cell。
5. 按 19A 冻结规则构造 train-only same-budget baseline。
6. 计算 train-only primary_tail_lift_50 和 sensitivity readouts。
7. 对每个 family 选择默认 1 个 train-selected cell 进入 19B。
8. 冻结 19B 使用的 selected family/cell manifest、N_family_brought_to_robustness、
   N_tested_family_cell_pairs 和 active correction scope。
9. 输出机器可读 audit、manifest 和中文报告。
```

禁止：

```text
1. 不得训练模型或拟合预测器。
2. 不得读取 validation outcome。
3. 不得用 robustness outcome 选择 family、cell、threshold、baseline arm 或 margin。
4. 不得调整 19A 冻结的 grid、baseline、censoring、cooldown、entry execution 或 metric。
5. 不得使用 pre-2025 TuShare DC backfilled concept/theme bucket 作为 PIT matching key。
6. 不得使用 AkShare board dump 作为 feature、matching key、theme source 或候选 family 输入。
7. 不得把 train-only 富集解释为 out-of-sample support。
8. 不得授权 entry/exit/holding policy、backtest、portfolio simulation、
   production signal 或 live trading。
9. 不得在任何 19B0 dataframe / output / temp artifact 中物化非 train split 的 outcome 字段值。
```

## 5. 输入合同

### 5.1 19A 合同输入

19B0 必须把以下文件写入 `input_artifact_audit.csv`，并记录行数、列数、hash：

```text
requirement_19a_entry_universe_pit_lineage_tradability_and_data_contract.md
requirement_19b0_fast_rule_grid_enrichment_scan.md
19A manifest
19A decision
19A candidate density audit
19A effective sample audit
19A grid search manifest
19A family accounting manifest
19A baseline budget freeze
19A baseline matching spec
19A baseline matching quality audit
19A primary metric and margin freeze
19A multiple-testing correction freeze
19A validation stress rule freeze
```

### 5.2 候选行与标签输入

19B0 可读取 19A 主候选源：

```text
SOURCE_EP07_ROOT/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv
SOURCE_EP07_ROOT/outputs/local_cache/topn_canonical_event_labels.parquet
```

强制读取顺序：

```text
1. 先从 canonical candidate metadata 读取 event_id、instrument、event_t0_date、
   event_t0_pos、event_split 和非 outcome feature/context 字段。
2. 构造 candidate_train_keys，其中 event_split = train。
3. 只为 candidate_train_keys 读取或连接 label/outcome anchor metadata。
4. 任何 robustness/validation/test split 的 outcome 字段值不得被加载、materialize、
   join、缓存或写入 19B0 输出。
```

实现可以为了验证 split 分布读取非 outcome 元数据，但任何 robustness/validation 的
forward label、MFE、MAE、winner label、fast-fail label 都不能参与 19B0 排名或选择。
EP07 label parquet 中的 `label_anchor_type = event_anchored` 行只能提供 train key
校验、ready-made label equivalence audit 和 diagnostic comparison；19B0 primary /
sensitivity label 必须按第 7 节以 next-open executable entry 重新构造。

如果底层 parquet/CSV API 无法证明 outcome columns 只被 train key 访问，必须 fail closed：

```text
decision_state = 19B0_train_only_boundary_blocked
blocking_reason = non_train_outcome_materialization_not_excludable
```

`train_only_boundary_audit.csv` 必须至少记录：

```text
candidate_metadata_row_n
candidate_train_key_row_n
train_label_row_n
non_train_outcome_columns_loaded
non_train_outcome_row_n
robustness_label_value_access_n
validation_label_value_access_n
selection_uses_train_only
boundary_gate
blocking_reason
```

### 5.3 Baseline eligible universe 输入

19B0 的 baseline 不能只从候选集内抽样，必须从 train split 内的 eligible universe
物化。默认输入为项目已存在的 PIT universe 和 qfq 行情源：

```text
data/processed/universe/pit_topn_400_100_executable_daily.csv
data/processed/universe/pit_topn_400_100_membership_daily.csv
data/raw/akshare/day/qfq/
```

baseline eligible row 的最低条件：

```text
instrument_date in train calendar range
listed_or_membership_eligible_asof_date = true
topn_executable_universe_asof_date = true
entry_date = next_open_trade_date_after_decision_date
entry_fill_feasible_under_19A_rule = true
cooldown_eligible_under_19A_rule = true
executable_entry_anchor_available = true
label_path_complete_under_executable_entry_anchor = true
matching_fields_available_asof_decision_date = true
```

baseline membership 和 matching bucket 必须在读取 forward label 之前冻结。baseline
eligible universe 可为 train baseline 按 executable next-open anchor 计算同一主标签和
敏感标签，但不得为非 train row 读取 outcome 值。

`eligible_universe_baseline_audit.csv` 必须记录各过滤阶段的 row count、instrument
count、decision month coverage、label path completeness 和 blocking reason。

### 5.4 支持的 family 范围

19A 当前支持并计入 `N_family_cap` 的 primary family 为：

```text
EP07_topn_multichannel_recommended_union
B1_near_120d_high_plus_volume_expansion
B2_relative_strength_breakout
B4_volatility_contraction_then_breakout
B5_recent_high_close_plus_amount_expansion
B6_low_drawdown_reclaim_or_ema_reclaim
```

以下 family 不得进入 primary scan：

```text
B3_industry_or_theme_breadth_expansion:
    status = unsupported_primary_feature
    reason = no genuine PIT industry source

EP04 / EP13 / EP14:
    status = candidate_source_optional_until_adapter_selected
    role = audit_only unless future requirement adds adapter
```

## 6. Grid Cell 合同

每个 grid cell 必须有稳定、可复现的标识：

```text
family_id
grid_cell_id
parameter_json
parameter_hash
selection_split = train
source_contract
candidate_row_source
feature_source_map_version
```

冻结限制：

```text
grid_parameter_n_per_family <= 5
grid_total_cells_all_families <= 300
validation_selected_cells = 0
N_family_cap = 10
```

19A 中 `B1/B2/B4/B5/B6` 每个 family 的默认网格规模为 `36` cells。
`EP07_topn_multichannel_recommended_union` 作为 existing candidate family 可进入
train readout，但如果没有额外 grid 参数，应只有一个 identity cell：

```text
grid_cell_id = EP07_identity_cell
parameter_json = {}
source_contract =
    19A_family_search_accounting_manifest
    + SOURCE_EP07_ROOT canonical candidate source
candidate_row_source = EP07 canonical train candidate rows
```

`19A_grid_search_manifest.csv` 只冻结 B1-B6 simple-rule grid。EP07 identity cell
不得假装来自 `19A_grid_search_manifest`；它必须由
`19A_family_search_accounting_manifest.csv` 中的 supported primary family 事实、
EP07 canonical candidate source 和 label source 共同证明。

19B0 必须在读取任何 label/outcome 前产出并冻结 `simple_rule_grid_registry.csv`。
该 registry 是 simple rule grid 的唯一执行定义，至少包含：

```text
family_id
feature_fields
parameter_axes
allowed_values
predicate_formula
grid_cell_id_rule
grid_cell_n
requires_supported_feature_status
materialization_status
blocking_reason
registry_frozen_before_label_readout
```

19B0 还必须在读取任何 label/outcome 前产出并冻结
`simple_rule_feature_source_map.csv`。该表是 B1/B2/B4/B5/B6 的 PIT feature
重建合同，至少包含：

```text
feature_field
source_type
source_artifact
source_columns
asof_rule
window_rule
cross_section_universe
reconstruction_formula
candidate_column_alias_if_ep07
baseline_rebuild_required
pit_guard
missing_policy
materialization_status
blocking_reason
```

默认 feature source map：

```text
close_asof_decision_date:
    source_type = qfq_rebuild
    source_artifact = data/raw/akshare/day/qfq/{instrument}.csv
    source_columns = date, close
    asof_rule = event_t0_date close; never use trade_open_date or future bars
    reconstruction_formula = qfq close on decision date

rolling_120d_high_asof_decision_date:
    source_type = qfq_rebuild
    source_artifact = data/raw/akshare/day/qfq/{instrument}.csv
    source_columns = date, high
    asof_rule = event_t0_date close
    window_rule = rolling 120 trading sessions ending at event_t0_date,
                  min_periods = 120
    reconstruction_formula = max(high[t-119:t])

amount_ratio_20d_asof_decision_date:
    source_type = ep07_direct_or_qfq_rebuild
    candidate_column_alias_if_ep07 = amount_ratio_20d
    source_artifact = EP07 canonical for EP07 candidates;
                      qfq money series for simple-rule/baseline universe
    window_rule = current money / rolling 20d mean money ending at event_t0_date

return_5d_asof_decision_date / return_10d_asof_decision_date /
return_20d_asof_decision_date / return_60d_asof_decision_date:
    source_type = ep07_direct_or_qfq_rebuild
    candidate_column_alias_if_ep07 = return_5d / return_10d / return_20d / return_60d
    source_artifact = EP07 canonical for EP07 candidates;
                      qfq close series for simple-rule/baseline universe
    asof_rule = event_t0_date close
    reconstruction_formula = close[t] / close[t-n] - 1

stock_vs_market_return_20d_asof_decision_date:
    source_type = ep07_direct_or_benchmark_rebuild
    candidate_column_alias_if_ep07 = stock_vs_market_20d
    source_artifact = EP07 canonical for EP07 candidates;
                      qfq close + data/processed/index/benchmark_indices_daily.csv
                      for simple-rule/baseline universe
    reconstruction_formula = stock_return_20d - benchmark_return_20d

return_60d_cross_section_rank_pct_asof_decision_date:
    source_type = universe_cross_section_rebuild
    source_artifact = baseline_eligible_universe + qfq close
    cross_section_universe = all baseline-eligible instruments on decision date
    reconstruction_formula = percentile_rank(return_60d, ascending = true)
    pit_guard = rank universe fixed before label readout

close_to_ema60_asof_decision_date:
    source_type = ep07_direct_or_qfq_rebuild
    candidate_column_alias_if_ep07 = close_to_ema60
    source_artifact = EP07 canonical for EP07 candidates;
                      qfq close for simple-rule/baseline universe
    reconstruction_formula = close / ema(close, span = 60, adjust = false) - 1

atr_20_pct_asof_decision_date:
    source_type = ep07_direct_or_qfq_rebuild
    candidate_column_alias_if_ep07 = atr_20_pct
    source_artifact = EP07 canonical for EP07 candidates;
                      qfq high/low/close for simple-rule/baseline universe
    window_rule = Wilder-style or simple rolling ATR must be fixed in config;
                  default = rolling mean true range over 20 sessions
    reconstruction_formula = atr_20 / close

atr_20_pct_rank_asof_decision_date:
    source_type = universe_cross_section_rebuild
    source_artifact = baseline_eligible_universe + atr_20_pct_asof_decision_date
    cross_section_universe = all baseline-eligible instruments on decision date
    reconstruction_formula = percentile_rank(atr_20_pct, ascending = true)

intraday_range_pct_asof_decision_date:
    source_type = ep07_direct_or_qfq_rebuild
    candidate_column_alias_if_ep07 = intraday_range_pct
    source_artifact = EP07 canonical for EP07 candidates;
                      qfq high/low/close for simple-rule/baseline universe
    reconstruction_formula = (high - low) / close

close_position_in_120d_range_asof_decision_date:
    source_type = qfq_rebuild
    source_artifact = data/raw/akshare/day/qfq/{instrument}.csv
    window_rule = rolling 120 trading sessions ending at event_t0_date,
                  min_periods = 120
    reconstruction_formula =
        (close - rolling_120d_low) / max(rolling_120d_high - rolling_120d_low, eps)

market_regime_risk_on_asof_decision_date:
    source_type = ep07_direct_or_benchmark_rebuild
    candidate_column_alias_if_ep07 = market_regime_bucket
    source_artifact = EP07 canonical for EP07 candidates;
                      data/processed/index/benchmark_indices_daily.csv
                      for simple-rule/baseline universe
    reconstruction_formula =
        market_regime_bucket == risk_on when EP07 column exists;
        otherwise use the same regime rule frozen in config before label readout

market_drawdown_60d_asof_decision_date:
    source_type = ep07_direct_or_benchmark_rebuild
    candidate_column_alias_if_ep07 = market_drawdown_60d
    source_artifact = EP07 canonical for EP07 candidates;
                      benchmark_indices_daily.csv for simple-rule/baseline universe
    reconstruction_formula = benchmark_close / rolling_60d_benchmark_high - 1

quality_amount_flag_asof_decision_date:
    source_type = ep07_direct_or_qfq_rebuild
    candidate_column_alias_if_ep07 = quality_amount_flag
    source_artifact = EP07 canonical for EP07 candidates;
                      qfq money availability for simple-rule/baseline universe
    reconstruction_formula = money is finite and rolling 20d money mean is finite

early_no_false_repair_10d_asof_decision_date:
    source_type = ep07_direct_only
    candidate_column_alias_if_ep07 = early_no_false_repair_10d
    baseline_rebuild_required = false
    pit_guard = may be used only where EP07 canonical proves it is as-of;
                no forward failure label may be used to reconstruct it
    missing_policy =
        non-EP07 simple-rule/baseline rows receive missing;
        cells requiring true are not materializable unless a future requirement
        adds a PIT-safe reconstruction contract
```

Any feature with `materialization_status != materialized_before_label_readout`
must make every dependent cell `train_scan_not_materializable` before labels are
read. Implementations may not silently substitute a nearby column after seeing
cell outcomes.

默认 simple rule registry：

```text
B1_near_120d_high_plus_volume_expansion:
    feature_fields =
        close_asof_decision_date,
        rolling_120d_high_asof_decision_date,
        amount_ratio_20d_asof_decision_date,
        return_20d_asof_decision_date,
        market_regime_risk_on_asof_decision_date
    parameter_axes =
        near_high_120d_pct_max in {0.02, 0.05, 0.08}
        amount_ratio_20d_min in {1.20, 1.50, 2.00}
        return_20d_min in {0.00, 0.05}
        market_regime_filter in {all, risk_on}
    predicate_formula =
        close >= rolling_120d_high * (1 - near_high_120d_pct_max)
        and amount_ratio_20d >= amount_ratio_20d_min
        and return_20d >= return_20d_min
        and (market_regime_filter = all or market_regime_risk_on = true)
    grid_cell_n = 3 * 3 * 2 * 2 = 36

B2_relative_strength_breakout:
    feature_fields =
        stock_vs_market_return_20d_asof_decision_date,
        return_60d_cross_section_rank_pct_asof_decision_date,
        close_to_ema60_asof_decision_date,
        market_regime_risk_on_asof_decision_date
    parameter_axes =
        stock_vs_market_20d_min in {0.05, 0.10, 0.15}
        return_60d_rank_pct_min in {0.70, 0.80, 0.90}
        close_to_ema60_min in {0.00, 0.02}
        market_regime_filter in {all, risk_on}
    predicate_formula =
        stock_vs_market_return_20d >= stock_vs_market_20d_min
        and return_60d_cross_section_rank_pct >= return_60d_rank_pct_min
        and close_to_ema60 >= close_to_ema60_min
        and (market_regime_filter = all or market_regime_risk_on = true)
    grid_cell_n = 3 * 3 * 2 * 2 = 36

B4_volatility_contraction_then_breakout:
    feature_fields =
        atr_20_pct_rank_asof_decision_date,
        intraday_range_pct_asof_decision_date,
        amount_ratio_20d_asof_decision_date,
        return_5d_asof_decision_date
    parameter_axes =
        atr_20_pct_rank_max in {0.30, 0.40, 0.50}
        intraday_range_pct_max in {0.03, 0.05, 0.08}
        amount_ratio_20d_min in {1.20, 1.50}
        return_5d_min in {0.00, 0.03}
    predicate_formula =
        atr_20_pct_rank <= atr_20_pct_rank_max
        and intraday_range_pct <= intraday_range_pct_max
        and amount_ratio_20d >= amount_ratio_20d_min
        and return_5d >= return_5d_min
    grid_cell_n = 3 * 3 * 2 * 2 = 36

B5_recent_high_close_plus_amount_expansion:
    feature_fields =
        return_10d_asof_decision_date,
        close_position_in_120d_range_asof_decision_date,
        amount_ratio_20d_asof_decision_date,
        quality_amount_flag_asof_decision_date
    parameter_axes =
        return_10d_min in {0.03, 0.06, 0.10}
        close_position_in_120d_range_min in {0.70, 0.85, 0.95}
        amount_ratio_20d_min in {1.20, 1.50}
        quality_amount_flag_required in {true, false_or_missing_allowed}
    predicate_formula =
        return_10d >= return_10d_min
        and close_position_in_120d_range >= close_position_in_120d_range_min
        and amount_ratio_20d >= amount_ratio_20d_min
        and (quality_amount_flag_required = false_or_missing_allowed
             or quality_amount_flag = true)
    grid_cell_n = 3 * 3 * 2 * 2 = 36

B6_low_drawdown_reclaim_or_ema_reclaim:
    feature_fields =
        market_drawdown_60d_asof_decision_date,
        close_to_ema60_asof_decision_date,
        return_5d_asof_decision_date,
        early_no_false_repair_10d_asof_decision_date
    parameter_axes =
        market_drawdown_60d_min in {-0.20, -0.15, -0.10}
        close_to_ema60_min in {0.00, 0.02, 0.05}
        return_5d_min in {0.00, 0.03}
        early_no_false_repair_10d_required in {true, false_or_missing_allowed}
    predicate_formula =
        market_drawdown_60d >= market_drawdown_60d_min
        and close_to_ema60 >= close_to_ema60_min
        and return_5d >= return_5d_min
        and (early_no_false_repair_10d_required = false_or_missing_allowed
             or early_no_false_repair_10d = true)
    grid_cell_n = 3 * 3 * 2 * 2 = 36
```

`grid_cell_id` 必须由 `family_id + sorted(parameter_json)` 确定性生成。推荐格式：

```text
grid_cell_id = family_slug + "__" + parameter_hash_12
parameter_hash = sha256(canonical_json(parameter_json))
```

如果实现无法复现某个 simple rule family 的 PIT feature 条件，该 family 必须输出：

```text
family_status = train_scan_not_materializable
selected_for_19B_robustness_flag = false
blocking_reason = missing_pit_feature_or_adapter_before_label_readout
```

不得在看过 outcome 后删除该 family 或修改参数空间。

## 7. Denominator 和 Label 合同

19B0 primary denominator 必须等于 19A 定义：

```text
primary_enrichment_denominator =
    fill_feasible_candidate_denominator
    intersect cooldown_entry_rows
    intersect label_eligible_rows_under_frozen_censoring_rule
    intersect split = train
```

所有 cell 必须报告：

```text
raw_candidate_n
cooldown_entry_n
fill_feasible_candidate_n
primary_denominator_n
path_complete_120_n
path_complete_30_n
instrument_n
instrument_month_n
decision_month_n
```

### 7.1 Executable-entry label anchor

19B0 的 primary / sensitivity forward label 必须以可成交入场行为为锚点：

```text
label_anchor_type = executable_next_open_anchored
entry_date = trade_open_date
entry_pos = trade_open_pos
entry_price = trade_open_price
entry_price_source = qfq_open_next_tradable_day
entry_anchor_source = EP07 canonical/label anchor metadata
```

`trade_open_price` 必须大于 0 且非缺失。若任一 train candidate 或 baseline row
无法绑定 `trade_open_date / trade_open_pos / trade_open_price`，该 row 不得进入
primary denominator，并必须写入 denominator / label audit。

EP07 label parquet 的 `label_anchor_type = event_anchored`、`mfe_120d`、
`event_big_winner_120d_label` 等 ready-made outcome 字段不是 19B0 primary label。
它们只允许用于：

```text
1. train-only label equivalence diagnostic
2. source-field availability audit
3. report caveat explaining event-anchored vs executable-entry anchored delta
```

任何 19B0 selection、ranking、primary_tail_lift_50、sensitivity_tail_lift_*、
baseline matching outcome 或 19B handoff 都不得使用 event-anchored ready-made label。

### 7.2 Label source map

19B0 必须在读取或重建任何 forward outcome 前冻结 `label_source_map.csv`。该表至少包含：

```text
label_field
selected_anchor_type
selected_source_artifact
selected_source_columns
diagnostic_source_columns
reconstruction_formula
horizon_sessions
path_complete_rule
ready_made_label_allowed_for_primary
ready_made_label_allowed_for_diagnostic
entry_price_column
entry_pos_column
label_materialized_after_train_filter
blocking_reason
```

默认 label source map：

```text
forward_mfe_20d / forward_mfe_30d / forward_mfe_60d / forward_mfe_120d:
    selected_anchor_type = executable_next_open_anchored
    selected_source_artifact =
        data/raw/akshare/day/qfq/{instrument}.csv
        + EP07 train candidate anchor metadata
        + baseline eligible universe anchor metadata
    selected_source_columns =
        qfq date, high, low, close,
        trade_open_date, trade_open_pos, trade_open_price
    diagnostic_source_columns =
        EP07 label parquet mfe_20d / mfe_30d / mfe_60d / mfe_120d
    reconstruction_formula =
        max(high[entry_pos : entry_pos + horizon_sessions - 1]) / entry_price - 1
    path_complete_rule =
        entry_price > 0
        and all required qfq high/low/close observations exist for the horizon
        and entry_pos + horizon_sessions - 1 exists
    ready_made_label_allowed_for_primary = false
    ready_made_label_allowed_for_diagnostic = true

forward_mae_20d / forward_mae_30d / forward_mae_60d / forward_mae_120d:
    selected_anchor_type = executable_next_open_anchored
    reconstruction_formula =
        min(low[entry_pos : entry_pos + horizon_sessions - 1]) / entry_price - 1
    ready_made_label_allowed_for_primary = false
    ready_made_label_allowed_for_diagnostic = true

forward_return_20d / forward_return_30d / forward_return_60d / forward_return_120d:
    selected_anchor_type = executable_next_open_anchored
    reconstruction_formula =
        close[entry_pos + horizon_sessions - 1] / entry_price - 1
    ready_made_label_allowed_for_primary = false
    ready_made_label_allowed_for_diagnostic = true

path_complete_20d / path_complete_30d / path_complete_60d / path_complete_120d:
    selected_anchor_type = executable_next_open_anchored
    selected_source_columns = reconstructed horizon availability flags
    diagnostic_source_columns =
        EP07 label parquet horizon_complete_20d / horizon_complete_30d /
        horizon_complete_60d / horizon_complete_120d

forward_big_winner_20d / forward_big_winner_30d /
forward_big_winner_60d / forward_big_winner_120d:
    selected_anchor_type = executable_next_open_anchored
    reconstruction_formula = forward_mfe_{horizon}d >= 0.50
    diagnostic_source_columns =
        EP07 label parquet event_big_winner_120d_label only for 120d
    ready_made_label_allowed_for_primary = false
    ready_made_label_allowed_for_diagnostic = true
```

The implementation must emit a train-only `label_anchor_rebuild_audit.csv`
comparing executable-entry labels to EP07 event-anchored diagnostic labels where
both are available. This audit must report counts and rates, but it must not
change selection or thresholds.

### 7.3 Label definitions

主标签：

```text
forward_big_winner_120d = forward_mfe_120d >= 0.50
forward_mfe_120d = executable-entry anchored MFE rebuilt from trade_open_price
path_complete_120d = true under executable-entry anchored path completeness rule
```

敏感标签：

```text
forward_big_winner_20d = executable-entry forward_mfe_20d >= 0.50, require path_complete_20d = true
forward_big_winner_30d = executable-entry forward_mfe_30d >= 0.50, require path_complete_30d = true
forward_big_winner_60d = executable-entry forward_mfe_60d >= 0.50, require path_complete_60d = true
tail_lift_20 = mean(forward_big_winner_20d | candidate) / mean(forward_big_winner_20d | matched_baseline)
tail_lift_30 = mean(forward_big_winner_30d | candidate) / mean(forward_big_winner_30d | matched_baseline)
tail_lift_60 = mean(forward_big_winner_60d | candidate) / mean(forward_big_winner_60d | matched_baseline)
tail_lift_120 = primary 120d label reused as long-horizon diagnostic by baseline family
```

EP07 label cache provides event-anchored 10/20/30/60/120d diagnostic horizons.
19B0 primary labels are executable-entry anchored and rebuilt for 20/30/60/120d
only. 19B0 must not invent a 100d label unless a future requirement adds a
separate qfq path-rebuild contract for that horizon.

所有标签都是 train-only readout 字段。它们可以用于 19B0 train triage，但不能用于
模型训练、validation 选择、robustness 选择或生产信号。

## 8. Baseline 物化合同

19B0 必须在 train split 上物化 19A 冻结的三类 baseline：

```text
calendar_time_random_same_budget
instrument_matched_random_same_budget
liquidity_size_volatility_matched_same_budget
```

baseline 抽样母体必须来自第 5.3 节冻结的 `baseline_eligible_universe`，
不得从 candidate cell 内部重采样代替 matched baseline。baseline row 的 membership、
matching bucket、baseline_family 和 baseline_sample_id 必须在读取 baseline forward label
之前冻结，并写入 audit。

Same-budget 规则：

```text
每个 baseline_family / family_id / grid_cell_id / split=train 的 baseline row count
必须等于对应 cell 的 primary_denominator_n，除非 matching quality audit 记录
unmatched_candidate_rate 并触发 blocking 或 diagnostic 降级。
```

默认 matching keys：

```text
decision_month
instrument_or_industry_bucket_if_supported
market_cap_bucket_asof_decision_date
rolling_20d_amount_bucket_asof_decision_date
rolling_60d_volatility_bucket_asof_decision_date
recent_20d_return_bucket_asof_decision_date
```

Matching-key feature source rule:

```text
1. Candidate rows and baseline rows must use the same matching-key feature
   reconstruction path.
2. EP07 direct feature columns may be used for candidate selection predicates
   only when allowed by `simple_rule_feature_source_map.csv`; they must not be
   used to bucket candidates for matched baseline construction unless
   `matching_feature_equivalence_audit.csv` proves equality to the canonical
   reconstruction.
3. Default 19B0 policy is stricter: all numeric matching keys are rebuilt from
   qfq/universe/index sources for both EP07 candidates and baseline rows.
```

19B0 必须在 baseline materialization 前冻结
`matching_feature_source_map.csv`：

```text
decision_month:
    source = event_t0_date / decision_date calendar month
    candidate_source = canonical metadata
    baseline_source = baseline eligible universe decision_date

market_cap_bucket_asof_decision_date:
    source = data/processed/universe/pit_topn_400_100_executable_daily.csv
    source_columns = usable_trade_date, instrument, total_market_cap_cny
    candidate_policy = rebuild from universe file, do not use EP07 total_market_cap_cny
    baseline_policy = rebuild from same universe file
    bucket_rule = quantile bucket within decision_month before label readout

rolling_20d_amount_bucket_asof_decision_date:
    source = data/raw/akshare/day/qfq/{instrument}.csv
    source_columns = date, money
    candidate_policy = rebuild from qfq, do not use EP07 amount_ratio_20d
    baseline_policy = rebuild from same qfq formula
    formula = rolling 20d mean money ending at decision_date
    bucket_rule = quantile bucket within decision_month before label readout

rolling_60d_volatility_bucket_asof_decision_date:
    source = data/raw/akshare/day/qfq/{instrument}.csv
    source_columns = date, close
    candidate_policy = rebuild from qfq, do not use EP07 atr_20_pct or market_volatility_20d
    baseline_policy = rebuild from same qfq formula
    formula = rolling 60d std of close-to-close returns ending at decision_date
    bucket_rule = quantile bucket within decision_month before label readout

recent_20d_return_bucket_asof_decision_date:
    source = data/raw/akshare/day/qfq/{instrument}.csv
    source_columns = date, close
    candidate_policy = rebuild from qfq, do not use EP07 return_20d unless equivalence audit passes
    baseline_policy = rebuild from same qfq formula
    formula = close[t] / close[t-20] - 1
    bucket_rule = quantile bucket within decision_month before label readout

instrument_or_industry_bucket_if_supported:
    source = instrument only by default
    industry_policy = disabled because genuine PIT industry source is unsupported
    concept_theme_policy = forbidden for pre-2025 backfill and diagnostic-only otherwise
```

`matching_feature_equivalence_audit.csv` may compare EP07 direct fields to the
canonical rebuild as diagnostic, but matching must use the canonical rebuild
unless config explicitly freezes an equivalence-backed override before label
readout.

边界：

```text
1. `instrument_or_industry_bucket_if_supported` 不能由 pre-2025 TuShare DC
   backfilled concept/theme membership 填充。
2. exact-year TuShare DC concept/theme bucket 只能作为 annual_vendor_theme_bucket
   明确标注，不得冒充 PIT industry bucket。
3. AkShare board dump 永远 forbidden_as_matching_key。
4. 当前市值/current-view 字段不得用作历史 matching key。
```

匹配质量门槛沿用 19A：

```text
unmatched_candidate_rate <= 0.05
baseline_reuse_rate <= 0.20
max_standardized_mean_difference_after_matching <= 0.10
decision_month_coverage_delta <= 0.02
instrument_coverage_delta <= 0.05
matched_baseline_primary_row_count >= primary_enrichment_denominator_row_count
```

如果任一进入选择候选的 cell 无法通过 matching quality gate，该 cell 不得进入 19B。
如果所有 cell 都无法物化 baseline，19B0 必须停止：

```text
decision_state = 19B0_baseline_materialization_blocked
```

## 9. 指标合同

主指标：

```text
p_candidate_50 =
    mean(executable-entry forward_big_winner_120d |
         candidate cell, train primary denominator)

p_matched_50_by_baseline[baseline_family] =
    mean(executable-entry forward_big_winner_120d |
         matched_budget_baseline[baseline_family], train primary denominator)

primary_tail_lift_50_by_baseline[baseline_family] =
    p_candidate_50 / p_matched_50_by_baseline[baseline_family]

primary_tail_lift_50_conservative =
    min(primary_tail_lift_50_by_baseline across the three baseline families)
```

Baseline families in scope:

```text
calendar_time_random_same_budget
instrument_matched_random_same_budget
liquidity_size_volatility_matched_same_budget
```

The primary pass rule is conjunctive across all three baseline families, matching
the 19A frozen `primary_baseline_pass_rule`.

Zero-baseline 规则：

```text
if p_matched_50_by_baseline[any baseline_family] = 0:
    primary_tail_lift_50_primary_pass_allowed_for_that_baseline = false
    train_triage_pass = false
    jeffreys_smoothed_ratio may be reported as diagnostic_only
```

Train-only triage margin：

```text
primary_tail_lift_50_train_margin_ratio =
    max(0.10, 2 * SE_delta_probability / p_matched_50_by_baseline)

train_triage_baseline_pass[baseline_family] =
    primary_tail_lift_50_by_baseline[baseline_family]
    >= 1.0 + primary_tail_lift_50_train_margin_ratio[baseline_family]

train_triage_pass =
    all(train_triage_baseline_pass across the three baseline families)
```

19B0 是 train-only 快速扫描，不执行完整 2000 次 candidate bootstrap +
matched-baseline rerandomization。19B0 使用 config 冻结的
`analytic_cluster_proxy_for_registered_bootstrap` 作为 triage margin 的近似
`SE_delta_probability`：

```text
SE_delta_probability =
    sqrt(p_candidate * (1 - p_candidate) / N_candidate_cluster
         + p_matched * (1 - p_matched) / N_matched_cluster)

cluster_key = instrument_month
```

完整 candidate cluster bootstrap 和 matched-baseline rerandomization 是 19B
robustness 阶段的验证合同，不得被 19B0 偷读或用于 train selection 调参。
19B0 必须在 `cell_cluster_bootstrap_margin_audit.csv` 中记录已注册的
bootstrap/rerandomization 参数、实际使用的 `se_delta_method`，并明确该行是
train-only analytic proxy。`SE_delta_probability` 和
`2 * SE_delta_probability` 的量纲是概率点；除以
`p_matched_50_by_baseline` 后才成为该 baseline arm 的 ratio margin。
默认复现配置：

```text
bootstrap_config:
    bootstrap_resample_n = 2000
    bootstrap_seed = 20260707
    candidate_cluster_key = instrument_month
    matched_baseline_rerandomization_n = 2000
    matched_baseline_rerandomization_seed = 20260707
    se_delta_method = analytic_cluster_proxy_for_registered_bootstrap
    multiway_cluster_enabled = false
```

敏感指标：

```text
sensitivity_tail_lift_20
sensitivity_tail_lift_30
sensitivity_tail_lift_60
sensitivity_tail_lift_120
winner_capture_rate
candidate_per_winner
fast_fail_rate
false_repair_rate
MAE_20_p10
MFE_120_p90
top1_instrument_removed_tail_lift
top3_instrument_removed_tail_lift
matched_baseline_delta
```

敏感指标只能用于解释和 diagnostic flag。它们不能替代失败的
`primary_tail_lift_50`。

## 10. Selection 合同

默认规则：

```text
每个 supported primary family 至多选择 1 个 train cell 进入 19B。
selection_metric = primary_tail_lift_50_train_margin_adjusted_conservative
tie_breaker = larger primary_denominator_n, then lower candidate_per_winner, then grid_cell_id lexicographic
```

默认 ranking score：

```text
primary_tail_lift_50_train_margin_adjusted_by_baseline[baseline_family] =
    primary_tail_lift_50_by_baseline[baseline_family]
    - 1.0
    - primary_tail_lift_50_train_margin_ratio[baseline_family]

primary_tail_lift_50_train_margin_adjusted_conservative =
    min(primary_tail_lift_50_train_margin_adjusted_by_baseline
        across the three baseline families)
```

选择条件：

```text
train_triage_pass = true
baseline_matching_quality_gate = pass
all_three_baseline_families_present = true
primary_denominator_n >= cell_primary_denominator_n_min
instrument_n >= cell_instrument_n_min
cell_effective_sample_ratio >= cell_effective_sample_ratio_min
```

默认 cell-level floor：

```text
cell_primary_denominator_n >= 300
cell_instrument_n >= 30
cell_effective_sample_ratio >= 0.30
```

19A 的 overall train support floor 只约束 19A 主候选源和 train denominator 是否足以进入
19B0；它不是每个 grid cell 的最低样本数。19B0 每个 cell 的默认 floor 为
`300 / 30 / 0.30`，除非 config 在运行前显式冻结更高或更低的 cell-level floor。

`cell_selection_process_gate` 检查选择过程是否可审计，而不是要求至少选中一个 cell。
它通过的条件：

```text
all_supported_cells_have_metric_or_blocking_reason = true
all_supported_cells_have_selection_rank_or_not_ranked_reason = true
tie_breaker_applied_deterministically = true
selected_cell_rule_applied_before_robustness_readout = true
```

如果 family 内无 cell 达到 selection 条件，但存在正向 diagnostic 读数，该 family 可标记：

```text
family_triage_status = train_diagnostic_only
selected_for_19B_robustness_flag = false
```

如果至少一个 family 有 selected cell：

```text
decision_state = 19B0_candidate_family_eligible_for_19B
```

如果没有 selected cell 但存在 diagnostic-only family：

```text
decision_state = 19B0_candidate_family_train_diagnostic
next_allowed_requirement = none
```

如果所有 family/cell 均失败：

```text
decision_state = 19B0_no_candidate_family_passed
next_allowed_requirement = none
```

## 11. Search Accounting 和 19B Handoff

19B0 必须在任何 19B robustness readout 之前冻结：

```text
selected_family_cell_manifest.csv
robustness_test_manifest.csv
```

必须记录：

```text
N_family_brought_to_robustness
N_tested_family_cell_pairs
active_correction_scope
family_level_correction
cell_level_accounting
selected_cell_rule
validation_selected_cells = 0
```

默认：

```text
selected_cell_rule = one_train_selected_cell_per_family_by_default
N_tested_family_cell_pairs = N_family_brought_to_robustness
active_correction_scope = N_family_brought_to_robustness * primary_metric
```

如果未来启用 top-2/top-3 low-correlation cell promotion，必须在 19B0 config 中
预先声明，并将：

```text
N_tested_family_cell_pairs = selected_family_cell_pair_count
active_correction_scope = N_tested_family_cell_pairs * primary_metric
expanded_cell_rule_enabled = true
```

本 requirement 默认不启用 expanded-cell promotion。

## 12. Required Outputs

19B0 output root：

```text
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan
```

机器可读输出：

```text
input_artifact_audit.csv
upstream_19a_contract_audit.csv
train_only_boundary_audit.csv
eligible_universe_baseline_audit.csv
simple_rule_grid_registry.csv
simple_rule_feature_source_map.csv
label_source_map.csv
label_anchor_rebuild_audit.csv
matching_feature_source_map.csv
matching_feature_equivalence_audit.csv
grid_cell_manifest.csv
family_grid_materialization_audit.csv
candidate_cell_denominator_audit.csv
baseline_materialization_audit.csv
baseline_matching_quality_audit.csv
train_cell_metric_readout.csv
train_cell_sensitivity_readout.csv
cell_cluster_bootstrap_margin_audit.csv
instrument_concentration_sensitivity.csv
family_selection_audit.csv
selected_family_cell_manifest.csv
robustness_test_manifest.csv
search_accounting_audit.csv
entry_universe_19b0_decision.csv
```

叙述输出：

```text
19B0_fast_rule_grid_enrichment_scan_report.md
19B0_handoff_to_19B_contract.md
```

manifest 输出：

```text
manifest_19b0_fast_rule_grid_enrichment_scan.json
output_hashes_19b0_fast_rule_grid_enrichment_scan.json
```

## 13. Required Schemas

### 13.1 `train_only_boundary_audit.csv`

```text
candidate_metadata_row_n
candidate_train_key_row_n
train_label_row_n
non_train_outcome_columns_loaded
non_train_outcome_row_n
robustness_label_value_access_n
validation_label_value_access_n
selection_uses_train_only
boundary_gate
blocking_reason
```

### 13.2 `eligible_universe_baseline_audit.csv`

```text
stage_name
row_n
instrument_n
decision_month_n
path_complete_120_rate
path_complete_30_rate
matching_fields_available_rate
filtered_out_row_n
blocking_reason
```

### 13.3 `simple_rule_grid_registry.csv`

```text
family_id
feature_fields
parameter_axes
allowed_values
predicate_formula
grid_cell_id_rule
grid_cell_n
requires_supported_feature_status
materialization_status
blocking_reason
registry_frozen_before_label_readout
```

### 13.4 `simple_rule_feature_source_map.csv`

```text
feature_field
source_type
source_artifact
source_columns
asof_rule
window_rule
cross_section_universe
reconstruction_formula
candidate_column_alias_if_ep07
baseline_rebuild_required
pit_guard
missing_policy
materialization_status
blocking_reason
```

### 13.5 `label_source_map.csv`

```text
label_field
selected_anchor_type
selected_source_artifact
selected_source_columns
diagnostic_source_columns
reconstruction_formula
horizon_sessions
path_complete_rule
ready_made_label_allowed_for_primary
ready_made_label_allowed_for_diagnostic
entry_price_column
entry_pos_column
label_materialized_after_train_filter
blocking_reason
```

### 13.6 `label_anchor_rebuild_audit.csv`

```text
split = train
family_id
grid_cell_id
row_scope
row_n
entry_anchor_available_n
trade_open_price_positive_rate
executable_entry_path_complete_20_rate
executable_entry_path_complete_30_rate
executable_entry_path_complete_60_rate
executable_entry_path_complete_120_rate
event_anchored_diagnostic_available_n
event_anchored_vs_executable_big_winner_120d_match_rate
ready_made_label_used_for_primary = false
ready_made_label_used_for_selection = false
blocking_reason
```

### 13.7 `matching_feature_source_map.csv`

```text
matching_key
canonical_source_artifact
canonical_source_columns
candidate_policy
baseline_policy
reconstruction_formula
bucket_rule
ep07_direct_field_allowed_for_matching
equivalence_override_allowed
frozen_before_baseline_materialization
blocking_reason
```

### 13.8 `matching_feature_equivalence_audit.csv`

```text
matching_key
ep07_direct_column
canonical_rebuild_column
compared_row_n
exact_match_rate
rank_correlation
bucket_match_rate
max_abs_delta
diagnostic_only_flag
override_enabled
blocking_reason
```

### 13.9 `grid_cell_manifest.csv`

```text
family_id
grid_cell_id
parameter_json
parameter_hash
selection_split = train
source_contract
candidate_row_source
feature_source_map_version
label_source_map_version
matching_feature_source_map_version
baseline_family_required_n = 3
registry_frozen_before_label_readout
label_readout_started = false
blocking_reason
```

### 13.10 `family_grid_materialization_audit.csv`

```text
family_id
family_source
declared_grid_cell_n
materialized_grid_cell_n
not_materialized_grid_cell_n
dependent_feature_missing_n
source_contract_verified
feature_source_map_verified
materialization_status
materialized_before_label_readout
blocking_reason
```

### 13.11 `candidate_cell_denominator_audit.csv`

```text
family_id
grid_cell_id
family_source
ep07_identity_cell_flag
split = train
source_candidate_train_n
raw_candidate_n
cooldown_entry_n
fill_feasible_candidate_n
entry_anchor_available_n
primary_denominator_n
path_complete_120_n
path_complete_30_n
instrument_n
instrument_month_n
decision_month_n
cell_primary_denominator_n_min
cell_instrument_n_min
cell_effective_sample_ratio
denominator_gate
blocking_reason
```

### 13.12 `baseline_materialization_audit.csv`

```text
baseline_family
family_id
grid_cell_id
split = train
baseline_eligible_universe_row_n
requested_same_budget_row_n
materialized_baseline_row_n
unmatched_candidate_n
baseline_sample_id_n
membership_frozen_before_label_readout
matching_bucket_frozen_before_label_readout
baseline_forward_label_read_after_membership_freeze
baseline_label_anchor_type = executable_next_open_anchored
ready_made_event_anchored_label_used = false
baseline_materialization_gate
blocking_reason
```

### 13.13 `baseline_matching_quality_audit.csv`

```text
baseline_family
family_id
grid_cell_id
split = train
unmatched_candidate_rate
baseline_reuse_rate
max_standardized_mean_difference_after_matching
decision_month_coverage_delta
instrument_coverage_delta
matched_baseline_primary_row_count
primary_enrichment_denominator_row_count
baseline_matching_quality_gate
cell_eligible_for_selection_under_this_baseline
blocking_reason
```

### 13.14 `train_cell_metric_readout.csv`

```text
family_id
grid_cell_id
baseline_family
split = train
label_anchor_type = executable_next_open_anchored
candidate_n
tradable_n
instrument_n
instrument_month_n
cooldown_entry_n
primary_denominator_n
path_complete_120_n
path_complete_30_n
p_candidate_50
p_matched_50_by_baseline
primary_tail_lift_50_by_baseline
primary_tail_lift_50_conservative
primary_tail_lift_50_train_margin_ratio_by_baseline
primary_tail_lift_50_train_margin_adjusted_by_baseline
primary_tail_lift_50_train_margin_adjusted_conservative
zero_baseline_flag
train_triage_baseline_pass
train_triage_pass
train_primary_metric_rank
selected_for_19B_robustness_flag
blocking_reason
```

There must be one `train_cell_metric_readout.csv` row per
`family_id / grid_cell_id / baseline_family`. `train_triage_pass` may be true
only if all three baseline-family rows pass for that cell.

### 13.15 `train_cell_sensitivity_readout.csv`

```text
family_id
grid_cell_id
baseline_family
split = train
label_anchor_type = executable_next_open_anchored
forward_big_winner_20d_rate
forward_big_winner_30d_rate
forward_big_winner_60d_rate
forward_big_winner_120d_rate
sensitivity_tail_lift_20
sensitivity_tail_lift_30
sensitivity_tail_lift_60
sensitivity_tail_lift_120
winner_capture_rate
candidate_per_winner
fast_fail_rate
false_repair_rate
MAE_20_p10
MFE_120_p90
matched_baseline_delta
diagnostic_only_flag
blocking_reason
```

### 13.16 `cell_cluster_bootstrap_margin_audit.csv`

```text
family_id
grid_cell_id
baseline_family
bootstrap_resample_n
bootstrap_seed
candidate_cluster_key
matched_baseline_rerandomization_n
matched_baseline_rerandomization_seed
se_delta_method
SE_delta_probability
primary_tail_lift_50_train_margin_ratio
multiway_cluster_enabled
blocking_reason
```

### 13.17 `instrument_concentration_sensitivity.csv`

```text
family_id
grid_cell_id
baseline_family
split = train
top1_instrument_removed_tail_lift
top3_instrument_removed_tail_lift
top1_instrument_removed_train_triage_pass
top3_instrument_removed_train_triage_pass
max_instrument_candidate_share
max_instrument_winner_share
diagnostic_only_flag
blocking_reason
```

### 13.18 `family_selection_audit.csv`

```text
family_id
supported_primary_family_flag
materialized_grid_cell_n
ranked_grid_cell_n
selected_grid_cell_id
selected_parameter_hash
best_primary_tail_lift_50_train_margin_adjusted_conservative
all_three_baseline_families_present
label_anchor_type = executable_next_open_anchored
selected_for_19B_robustness_flag
family_triage_status
selection_rank_within_all_families
selection_rule_applied_before_robustness_readout
blocking_reason
```

### 13.19 `selected_family_cell_manifest.csv`

```text
family_id
grid_cell_id
parameter_hash
selection_split = train
selection_metric
selection_rank_within_family
label_anchor_type = executable_next_open_anchored
selected_for_19B_robustness_flag
N_family_brought_to_robustness
N_tested_family_cell_pairs
active_correction_scope
manifest_frozen_before_robustness_readout = true
blocking_reason
```

### 13.20 `robustness_test_manifest.csv`

```text
family_id
grid_cell_id
parameter_hash
selected_in_19B0_train_only
label_anchor_type = executable_next_open_anchored
robustness_split_outcome_read_allowed_in_19B = true
validation_split_outcome_read_allowed_in_19B = false
N_family_brought_to_robustness
N_tested_family_cell_pairs
active_correction_scope
family_level_correction
cell_level_accounting
manifest_frozen_before_robustness_readout = true
blocking_reason
```

### 13.21 `search_accounting_audit.csv`

```text
N_supported_primary_family
N_materialized_family
N_family_brought_to_robustness
N_tested_family_cell_pairs
active_correction_scope
family_level_correction
cell_level_accounting
selected_cell_rule
expanded_cell_rule_enabled
validation_selected_cells
search_accounting_gate
blocking_reason
```

## 14. Decision Gates

Critical gates：

```text
upstream_19a_contract_gate
train_only_boundary_gate
grid_manifest_gate
family_materialization_gate
primary_denominator_gate
baseline_materialization_gate
baseline_matching_quality_gate
metric_readout_gate
cell_selection_process_gate
search_accounting_gate
no_policy_authorization_gate
output_contract_gate
```

Gate 到 fail-closed state 的映射：

```text
19B0_upstream_19a_contract_blocked:
    upstream_19a_contract_gate

19B0_train_only_boundary_blocked:
    train_only_boundary_gate

19B0_grid_contract_blocked:
    grid_manifest_gate
    family_materialization_gate

19B0_baseline_materialization_blocked:
    baseline_materialization_gate
    baseline_matching_quality_gate

19B0_metric_contract_blocked:
    primary_denominator_gate
    metric_readout_gate

19B0_output_contract_blocked:
    cell_selection_process_gate
    search_accounting_gate
    no_policy_authorization_gate
    output_contract_gate
```

如果多个 gate 失败，决策行必须选择上述顺序中最早的 blocking state，并在
`blocking_reason` 中列出所有 failed gates。

所有 critical gates 通过后，`decision_state` 按以下规则机械推导：

```text
if selected_family_cell_pair_n > 0:
    decision_state = 19B0_candidate_family_eligible_for_19B
    next_allowed_requirement = requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md

else if selected_family_cell_pair_n = 0 and diagnostic_family_n > 0:
    decision_state = 19B0_candidate_family_train_diagnostic
    next_allowed_requirement = none

else if selected_family_cell_pair_n = 0 and diagnostic_family_n = 0:
    decision_state = 19B0_no_candidate_family_passed
    next_allowed_requirement = none
```

`19B0_candidate_family_train_diagnostic` 和 `19B0_no_candidate_family_passed` 是合法
非正向结论，不代表 gate failure。只有选择过程不可审计时，才由
`cell_selection_process_gate` 失败并进入 fail-closed state。

## 15. 决策行字段

`entry_universe_19b0_decision.csv` 必须包含：

```text
run_id
created_at
requirement_file_hash
config_file_hash
upstream_19a_manifest_hash
decision_state
next_allowed_requirement
upstream_19a_contract_gate
train_only_boundary_gate
grid_manifest_gate
family_materialization_gate
primary_denominator_gate
baseline_materialization_gate
baseline_matching_quality_gate
metric_readout_gate
cell_selection_process_gate
search_accounting_gate
no_policy_authorization_gate
output_contract_gate
N_family_brought_to_robustness
N_tested_family_cell_pairs
selected_family_n
selected_family_cell_pair_n
diagnostic_family_n
validation_outcome_read
robustness_outcome_used_for_selection
model_training_authorized
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

所有 authorization 字段必须为 `false`。

## 16. 报告要求

中文报告必须包含：

```text
1. 19A ready 证据和冻结合同摘要。
2. 19B0 train-only 边界，明确未读取 validation outcome。
3. 支持/不支持 family 列表。
4. 每个 family 的 grid materialization 情况。
5. executable next-open label anchor、label source map，以及 EP07 event-anchored
   diagnostic label 与 executable-entry rebuilt label 的差异。
6. train primary denominator、instrument_n、instrument_month_n，并单独披露
   EP07 identity family 的 train denominator / path-complete denominator。
7. matching feature source map，明确候选与 baseline 使用同一 qfq/universe
   重建路径。
8. 三类 baseline 的物化和 matching quality。
9. 三类 baseline 分臂的 primary_tail_lift_50、conjunctive pass 和
   conservative margin-adjusted 排名。
10. sensitivity 指标，明确 diagnostic-only。
11. instrument concentration / top-k removal 风险。
12. selected family/cell manifest。
13. search accounting、N_family_brought_to_robustness、correction scope。
14. 最终 decision_state 和 next_allowed_requirement。
```

报告必须明确写出：

```text
19B0 不是 robustness confirmation。
19B0 不证明策略有效。
19B0 不授权 19C replay。
19B0 不授权模型、entry/exit/holding policy、回测、生产信号或交易。
进入 19B 的资格不是 support claim。
```

## 17. 验证命令

预期命令：

```bash
cd topics/02_AFML_BIG_WINNER

python -m py_compile \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b0_fast_rule_grid_enrichment_scan.py

python -m pytest \
  experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19b0_fast_rule_grid_enrichment_scan.py

python \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b0_fast_rule_grid_enrichment_scan.py \
  --config experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19b0_fast_rule_grid_enrichment_scan.yaml

git diff --check
```

如果 `ruff` 可用，还应运行：

```bash
python -m ruff check \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b0_fast_rule_grid_enrichment_scan.py \
  experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19b0_fast_rule_grid_enrichment_scan.py
```

## 18. Acceptance Checklist

19B0 可实现条件：

```text
[ ] 19A decision ready 且 next_allowed_requirement 指向 19B0。
[ ] 19A manifest/hash 可验证。
[ ] train-only 边界可机械审计。
[ ] validation outcome 不被读取。
[ ] robustness outcome 不用于选择。
[ ] EP07 event-anchored ready-made label 不进入 primary / sensitivity / selection。
[ ] label_source_map 和 executable next-open label rebuild contract 已冻结。
[ ] 支持 family 列表完全来自 19A。
[ ] B3 和 AkShare/TuShare forbidden matching 边界被继承。
[ ] baseline eligible universe 输入、过滤阶段和 audit schema 已冻结。
[ ] B1/B2/B4/B5/B6 的 feature fields、参数轴、谓词和 36-cell registry 已冻结。
[ ] simple-rule feature source map、PIT reconstruction formula 和 missing policy 已冻结。
[ ] matching feature source map 要求候选与 baseline 使用同一 qfq/universe 重建路径。
[ ] grid cell manifest 在 outcome readout 前冻结。
[ ] EP07 identity cell 的 source contract 不误用 19A grid_search_manifest。
[ ] EP07 identity family 的 train denominator 单独披露。
[ ] 三类 baseline materialization、matching quality 和分臂 metric readout 可审计。
[ ] forward_big_winner_30d、path_complete_30d 和 sensitivity_tail_lift_30 已定义。
[ ] bootstrap/rerandomization seed、resample count 和 cluster key 已冻结。
[ ] 不使用未声明重建路径的 100d label。
[ ] primary_tail_lift_50 和 margin 规则沿用 19A，并对三类 baseline 执行 conjunctive pass。
[ ] 每个 family 的 selected cell 规则固定为 train-only。
[ ] selected=0 的 diagnostic/no-pass 状态是合法非正向结论，不被误报为 gate failure。
[ ] robustness_test_manifest 在 19B 前冻结。
[ ] entry/exit/holding/backtest/deployment/production/live 授权字段均为 false。
[ ] 所有 output、manifest、decision states、validation commands 已声明。
```
