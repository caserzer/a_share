# Requirement: 19B 稳健右尾富集与假阳性负担读出

## 0. 不可协商范围

19B 是 EP19 在 19B0 train-only triage 之后的正式 robustness readout 阶段。它只允许读取
19B0 已冻结的 `robustness_test_manifest.csv` 中的 family/cell，并在 robustness split 上
检验右尾富集是否稳健、假阳性负担是否可接受、top-k 集中度是否可控，以及 matched baseline
是否足以支持 residual-alpha 归因。

19B 不生成新候选 family，不扩展 grid，不重新选择 train cell，不读取 validation outcome，不训练模型，
不输出 entry/exit/holding policy，不运行组合回测，不输出生产信号，不授权交易。

19B 的正向结果最多分成两类：

```text
positive_exposure_persistent:
    19B0 的 positive_beta_exposure_candidate 在 robustness split 上仍显示
    broad eligible-universe 右尾暴露，并通过 false-positive burden 和 top-k
    sensitivity 约束。

residual_alpha_supported:
    在 positive exposure persistence 之外，19A/19B0 已冻结的原始
    matched-baseline 协议也通过 quality gate、primary_tail_lift_50、
    预冻结 margin 和 multiple-testing correction。
```

如果只得到 `positive_exposure_persistent`，EP19 的最高终态仍只能是：

```text
19_entry_universe_enrichment_only_diagnostic
```

它不能授权 19C replay、EP20 policy preflight、entry policy preflight 或任何交易实现。

如果 19B 使用 19A/19B0 已冻结的原始 matched-baseline 协议另行取得 residual pass，
19B 不得回写或篡改 19B0 的 `promotion_claim_type`。19B0 的字段必须保持为：

```text
promotion_claim_type = positive_beta_exposure_candidate
residual_alpha_claim_allowed_19b0 = false
```

19B 只能在自己的输出中增加新的 readout 字段，例如：

```text
matched_baseline_residual_pass_19b
residual_alpha_support_claim_allowed_19b
```

换言之，19B 可以证明“这个 19B0 positive exposure candidate 在 robustness 上，
相对已经冻结的原始 matched baseline 额外取得了 residual-style 支持”，但不能把
19B0 的 train-only candidate 追溯改名为 `residual_alpha_candidate`。

### 0.1 与 research plan 的关系

research plan 中 19B 原始目标包括 validation stress rule。当前 19B0 handoff 合同更严格：

```text
Validation outcome remains forbidden in 19B.
```

因此本 requirement 的 19B 不读取 validation outcome。若 19B 取得 residual-style robustness
支持，validation stress 必须作为后续单独 requirement 或更高阶段的只读压力测试；本 19B 不用
validation 改善、选择、调参或否决。

## 1. 身份

```text
experiment_id = 19_entry_universe_pit_tradability_preflight
phase_id = 19B
run_id = 19B_robust_right_tail_enrichment_and_false_positive_burden_readout
requirement_file = requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md
config_file = configs/config_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.yaml
runner_file = src/run_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py
test_file = tests/test_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py
```

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

所有路径必须通过 config 或显式 path alias 解析。实现不得硬编码 `/home/xiaolv/...`
绝对路径。

## 2. 上游合同

19B 必须先验证 19A 和 19B0 的闭包。

### 2.1 19A 必需事实

必须读取并校验：

```text
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/entry_universe_preflight_decision.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/manifest_19a_entry_universe_pit_lineage_tradability_and_data_contract.json
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/baseline_budget_freeze.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/baseline_matching_spec.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/primary_metric_and_margin_freeze.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/multiple_testing_correction_freeze.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/validation_stress_rule_freeze.csv
EXPERIMENT_ROOT/outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/replay_path_eligibility_freeze.csv
```

必需事实：

```text
decision_state = 19A_entry_universe_contract_ready
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

如果 19A manifest/hash 不一致、decision 非 ready、或任何 policy/trading 授权字段为 true，
19B 必须停止：

```text
decision_state = 19B_upstream_19a_contract_blocked
```

### 2.2 19B0 必需事实

必须读取并校验：

```text
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/entry_universe_19b0_decision.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/manifest_19b0_fast_rule_grid_enrichment_scan.json
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/output_hashes_19b0_fast_rule_grid_enrichment_scan.json
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/selected_family_cell_manifest.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/robustness_test_manifest.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/search_accounting_audit.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/grid_cell_manifest.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/label_source_map.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/matching_feature_source_map.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/baseline_matching_quality_audit.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/train_cell_metric_readout.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/train_cell_sensitivity_readout.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/instrument_concentration_sensitivity.csv
EXPERIMENT_ROOT/outputs/19B0_fast_rule_grid_enrichment_scan/19B0_handoff_to_19B_contract.md
```

必需事实：

```text
decision_state = 19B0_candidate_family_eligible_for_19B
next_allowed_requirement = requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md
N_family_brought_to_robustness = 2
N_tested_family_cell_pairs = 2
selected_residual_alpha_cell_pair_n = 0
selected_positive_beta_exposure_cell_pair_n = 2
residual_alpha_correction_scope = 0 * primary_tail_lift_50
positive_beta_exposure_correction_scope = 2 * positive_exposure_score_50
validation_outcome_read = false
robustness_outcome_used_for_selection = false
manifest_frozen_before_robustness_readout = true
```

19B 允许测试的 family/cell 只能是：

| family_id | grid_cell_id | promotion_claim_type | selection_track |
|---|---|---|---|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | positive_beta_exposure_candidate | positive_beta_exposure |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | positive_beta_exposure_candidate | positive_beta_exposure |

任何新增 family、替换 cell、扩展参数、读取未冻结 cell、或把 B1/B4/B6/EP07 重新带入
robustness primary readout，均必须 fail closed：

```text
decision_state = 19B_upstream_19b0_contract_blocked
blocking_reason = robustness_test_manifest_not_frozen_or_expanded
```

## 3. 研究问题

19B 只回答五个问题。

```text
Q1. B2/B5 的 train-only positive exposure 是否在 robustness split 上仍成立？

Q2. 在 robustness split 上，B2/B5 是否能在 matched baseline quality 通过后取得
    primary_tail_lift_50 residual-style 支持？

Q3. B2/B5 的 false-positive burden 是否可接受？
    重点包括 fast_fail_rate、false_repair_rate、candidate_per_winner、
    MAE_20_p10 / MAE_20_p05 和 left-tail worsening。

Q4. B2/B5 的右尾读数是否由少数股票、少数月份或重复 event 驱动？
    重点包括 top1/top3 instrument removal、instrument/month concentration、
    cluster-aware bootstrap CI。

Q5. 19B 的结论应进入哪个终态：
    residual-style support、enrichment-only diagnostic、not supported、
    baseline/common-support blocked、false-positive burden blocked、
    或 output/contract blocked。
```

19B 不回答：

```text
1. 该规则是否可交易。
2. 该规则是否值得部署。
3. 该规则是否能训练模型。
4. 该规则是否在 validation 上成立。
5. 该规则是否能进入 19C replay。
6. 该规则是否能授权 EP20 policy preflight。
```

## 4. 允许和禁止工作

允许：

```text
1. 读取 19A / 19B0 manifest、audit、selected manifest 和 robustness_test_manifest。
2. 只为 19B0 冻结的 B2/B5 family/cell 物化 robustness split 候选行。
3. 只为 19B0 冻结的 B2/B5 family/cell 物化 robustness split matched baseline。
4. 在读取 outcome 前冻结 robustness candidate row manifest 和 baseline row manifest。
5. 读取 robustness split 的 executable next-open anchored labels。
6. 计算 robustness primary_tail_lift_50、positive_exposure_score_50、
   false-positive burden、top-k sensitivity 和 cluster bootstrap CI。
7. 按预注册 baseline repair variants 输出 baseline common-support / quality audit。
8. 输出机器可读 audit、manifest、中文报告和四张 required research-plan 图。
```

禁止：

```text
1. 不得读取 validation outcome。
2. 不得读取 validation MFE / MAE / winner / fast-fail label。
3. 不得使用 robustness outcome 选择 family、grid cell、threshold、baseline arm、
   repair variant、margin 或 correction method。
4. 不得新增 family 或 grid cell。
5. 不得把 B1/B4/B6/EP07 的 diagnostic readout 升级为 19B primary readout。
6. 不得训练模型、拟合预测器或调参器。
7. 不得运行 portfolio backtest。
8. 不得授权 entry/exit/holding policy、production signal 或 live trading。
9. 不得把 positive_beta_exposure_candidate 的 persistence 直接解释为 independent alpha。
10. 不得用 sensitivity metric 救回 primary metric 失败。
```

## 5. Robustness outcome 边界

19B 必须保持三层冻结顺序：

```text
1. 读取 19B0 robustness_test_manifest，确认 family/cell 列表和 correction scope。
2. 在不读取 outcome 的情况下物化 robustness_candidate_row_manifest.csv 和
   robustness_baseline_row_manifest.csv。
3. 只为上述 frozen rows 读取 executable next-open anchored robustness outcome。
```

`robustness_outcome_boundary_audit.csv` 必须至少记录：

```text
selected_family_cell_pair_n
robustness_candidate_manifest_frozen_before_label_readout
robustness_baseline_manifest_frozen_before_label_readout
robustness_outcome_row_n_loaded
validation_outcome_columns_loaded
validation_outcome_row_n
validation_label_value_access_n
robustness_outcome_used_to_expand_or_select_test_set
boundary_gate
blocking_reason
```

要求：

```text
validation_outcome_columns_loaded = false
validation_outcome_row_n = 0
validation_label_value_access_n = 0
robustness_outcome_used_to_expand_or_select_test_set = false
```

若无法证明 validation outcome 未被 materialize，必须停止：

```text
decision_state = 19B_outcome_boundary_blocked
blocking_reason = validation_outcome_materialization_not_excludable
```

## 6. Denominator 和标签

19B primary denominator 继承 research plan 和 19A/19B0 合同：

```text
primary_enrichment_denominator =
    fill_feasible
    ∩ cooldown_entry_rows
    ∩ label_eligible_rows_under_frozen_censoring_rule
```

primary label：

```text
forward_big_winner_120d =
    max_qfq_high_from_entry_through_120_sessions / executable_next_open - 1 >= 0.50
```

19B 必须继续使用 `executable_next_open_anchored` label。EP07 ready-made
`event_anchored` label 只允许作为 equivalence diagnostic，不得进入 primary metric、
selection 或 decision。

每个 selected cell 必须分别报告：

```text
candidate_n
tradable_n
instrument_n
instrument_month_n
decision_month_n
cooldown_entry_n
primary_denominator_n
path_complete_20_n
path_complete_30_n
path_complete_60_n
path_complete_120_n
path_complete_120_rate
p_candidate_50
p_eligible_universe_50
p_matched_50_by_baseline
```

## 7. Baseline repair 和 residual-alpha 归因

19B0 已证明原始 three-arm matching quality 全部失败。因此 19B 必须显式区分：

```text
positive_exposure_robustness:
    与 robustness eligible universe broad base rate 比较，用于判断右尾暴露是否持久。

matched_baseline_residual_readout:
    只能与 19A/19B0 已冻结的原始 matched budget baseline 比较；
    只有这些 frozen baseline 的 quality gate 通过时，才允许支持
    residual-style claim。
```

### 7.1 Frozen baseline 与 diagnostic repair variants

19B 不得在看到 robustness outcome 后选择、替换或新增 primary residual baseline。
本 requirement 中允许产生 residual-style support 的 baseline 只能来自 19A/19B0 已冻结的
原始 baseline family：

```text
primary_residual_baseline_variant_set =
    original_calendar_time_random_same_budget
    original_instrument_matched_random_same_budget
    original_liquidity_size_volatility_matched_same_budget

primary_residual_baseline_gate_rule = conjunctive_pass_across_all_three_original_baselines
pass_on_any_baseline = false
```

19B 可以在读取 outcome 前冻结 diagnostic repair variants，用于评估下一步是否需要
单独的 baseline-repair prefreeze requirement；但这些 repair variants 不得产生
`matched_baseline_residual_pass_19b = true`，也不得进入 residual-alpha correction scope。

实现必须在读取 outcome 前输出：

```text
baseline_repair_variant_registry.csv
```

默认 variants：

| repair_variant_id | baseline_family | role | matching method | outcome use |
|---|---|---|---|---|
| original_calendar_time_random_same_budget | calendar_time_random_same_budget | primary_original_frozen | 19B0 frozen method | residual pass allowed if quality pass |
| original_instrument_matched_random_same_budget | instrument_matched_random_same_budget | primary_original_frozen | 19B0 frozen method | residual pass allowed if quality pass |
| original_liquidity_size_volatility_matched_same_budget | liquidity_size_volatility_matched_same_budget | primary_original_frozen | 19B0 frozen method | residual pass allowed if quality pass |
| repaired_lsv_return_cem_v1 | liquidity_size_volatility_recent_return_matched_same_budget | diagnostic_repair_only | coarsened exact matching | diagnostic only |
| repaired_lsv_return_nn_caliper_v1 | liquidity_size_volatility_recent_return_nearest_neighbor_same_budget | diagnostic_repair_only | nearest-neighbor with frozen calipers | diagnostic only |

禁止：

```text
config may not promote diagnostic_repair_only variants into primary residual variants.
pass-on-any diagnostic repair variant is forbidden.
diagnostic repair variants do not change next_allowed_requirement.
```

如果未来需要让 repaired baseline 支持 residual-alpha claim，必须先生成单独 requirement，
在不读取 robustness/validation outcome 的前提下冻结 repair registry、cap、correction scope
和 decision rule。当前 19B 只允许把 repair sweep 作为 next-research diagnostic。

当前必须同时保留两套 correction-scope 字段，避免把 19B0 train-only promotion scope
与 19B robustness residual-style readout scope 混写：

```text
residual_alpha_correction_scope_19b0_frozen =
    0 * primary_tail_lift_50

residual_style_readout_correction_scope_19b =
    N_tested_family_cell_pairs * primary_tail_lift_50
```

`residual_alpha_correction_scope_19b0_frozen` 是上游事实，不得被 19B 回写。
`residual_style_readout_correction_scope_19b` 只用于本 requirement 的 robustness
residual-style p-value / Sidak alpha readout；即使该 readout 通过，也不得把 19B0 的
`promotion_claim_type` 改写为 residual-alpha candidate。

### 7.2 Matching quality gate

每个 selected family/cell 和 repair variant 必须输出：

```text
matched_candidate_n
unmatched_candidate_n
unmatched_candidate_rate
baseline_reuse_rate
max_standardized_mean_difference_after_matching
per_feature_smd_json
decision_month_coverage_delta
instrument_coverage_delta
matched_baseline_primary_row_count
primary_enrichment_denominator_row_count
baseline_matching_quality_gate
common_support_pass
failure_reason
```

默认 quality gate：

```text
unmatched_candidate_rate <= 0.05
baseline_reuse_rate <= 0.20
max_standardized_mean_difference_after_matching <= 0.10
decision_month_coverage_delta <= 0.02
instrument_coverage_delta <= 0.05
```

如果任一 original frozen baseline 的 quality gate 失败，则：

```text
matched_baseline_residual_pass_19b = false
residual_alpha_support_claim_allowed_19b = false
residual_blocking_reason = original_frozen_baseline_quality_not_conjunctively_passed
```

但 positive exposure robustness readout 仍可继续，且只能支持 enrichment-only diagnostic。

## 8. Primary metrics

### 8.1 Positive exposure robustness track

对 19B0 的两个 selected cells 计算：

```text
p_candidate_50 =
    P(forward_big_winner_120d = true | selected cell, robustness primary denominator)

p_eligible_universe_50 =
    P(forward_big_winner_120d = true | robustness eligible universe primary denominator)

positive_exposure_delta_50 =
    p_candidate_50 - p_eligible_universe_50

positive_exposure_ratio_50 =
    p_candidate_50 / p_eligible_universe_50
```

默认 margin 继承 19B0 口径，并把 family-level correction 机械化为固定的
cluster-bootstrap SE normal-approx one-sided p-value gate。19B0 已冻结：

```text
positive_exposure_absolute_margin_floor_50 = 0.02
positive_exposure_relative_margin_ratio_floor = 0.20
positive_beta_exposure_correction_scope = 2 * positive_exposure_score_50
family_level_correction = Bonferroni-Sidak
```

19B 不允许把 `positive_exposure_relative_margin_ratio_floor` 改成 config 未声明值。
positive exposure 的不确定性读出必须使用以下固定方法，不能在看到 outcome 后改成
matched rerandomization、双侧检验、不同 cluster key 或不同 seed：

```text
positive_exposure_p_value_method =
    cluster_bootstrap_se_normal_approx_one_sided_candidate_vs_eligible_universe
positive_exposure_alternative = p_candidate_50 > p_eligible_universe_50
positive_exposure_cluster_key = instrument_month
positive_exposure_bootstrap_resample_n = 2000
positive_exposure_bootstrap_seed = 20260707
positive_exposure_SE_delta_probability =
    cluster-bootstrap SE of positive_exposure_delta_50
cluster_bootstrap_SE_margin_50 =
    2 * positive_exposure_SE_delta_probability

positive_exposure_z_50 =
    positive_exposure_delta_50 / positive_exposure_SE_delta_probability
positive_exposure_p_value_50 =
    1 - standard_normal_cdf(positive_exposure_z_50)
```

如果 `positive_exposure_SE_delta_probability <= 0`、cluster 数不足以重采样、或实现无法复现
上述 seed/key/resample contract，必须停止：

```text
decision_state = 19B_metric_contract_blocked
blocking_reason = positive_exposure_p_value_method_not_reproducible
```

```text
positive_exposure_absolute_margin_floor_50 = 0.02
positive_exposure_relative_margin_ratio_floor = 0.20
positive_exposure_relative_margin_floor_50 =
    p_eligible_universe_50 * positive_exposure_relative_margin_ratio_floor

positive_exposure_margin_50 =
    max(
        cluster_bootstrap_SE_margin_50,
        positive_exposure_absolute_margin_floor_50,
        positive_exposure_relative_margin_floor_50
    )

positive_exposure_score_50 =
    positive_exposure_delta_50 - positive_exposure_margin_50

positive_exposure_sidak_alpha =
    1 - (1 - 0.05) ** (1 / N_tested_family_cell_pairs)
```

Positive exposure robustness pass：

```text
positive_exposure_score_50 > 0
and positive_exposure_ratio_50 >= 1.0 + positive_exposure_relative_margin_ratio_floor
and positive_exposure_p_value_50 <= positive_exposure_sidak_alpha
```

该 pass 不允许声明 residual alpha。

### 8.2 Residual-style matched-baseline track

只在三类 original frozen baseline 的 quality gate 全部通过后计算 primary residual pass：

19A 冻结的是 primary margin 公式而不是某个 split 上的数值。19B 必须在 robustness split
上按 19A 冻结公式、19B 冻结 seed 和 original frozen matching protocol 计算 margin ratio：

```text
p_matched_50_conservative =
    max(p_matched_50_by_each_original_frozen_baseline)

primary_tail_lift_50 =
    p_candidate_50 / p_matched_50_conservative

residual_SE_delta_probability =
    matched-rerandomization SE under original frozen matching protocol of
    p_candidate_50 - p_matched_50_conservative

residual_corrected_margin_ratio_50 =
    max(0.10, 2 * residual_SE_delta_probability / p_matched_50_conservative)

primary_tail_lift_50_margin_adjusted =
    primary_tail_lift_50 - (1.0 + residual_corrected_margin_ratio_50)

residual_p_value_method =
    matched_baseline_rerandomization_one_sided_under_original_frozen_matching_protocol
residual_rerandomization_n = 2000
residual_rerandomization_seed = 20260707

primary_tail_lift_50_p_value =
    (1 + count(rerandomized_primary_tail_lift_50 >= observed_primary_tail_lift_50))
    / (1 + residual_rerandomization_n)

residual_alpha_sidak_alpha =
    1 - (1 - 0.05) ** (1 / N_tested_family_cell_pairs)
```

Primary residual pass：

```text
all_three_original_frozen_baseline_quality_gate = pass
and primary_tail_lift_50_margin_adjusted > 0
and primary_tail_lift_50_p_value <= residual_alpha_sidak_alpha
and false_positive_burden_gate = pass
and topk_residual_gate = pass
```

如果任一 original frozen baseline 的 `p_matched_50 = 0`，必须使用 19A/19B0 已冻结的
smoothing rule；若没有冻结 smoothing，该 cell 的 residual readout 必须标记为：

```text
residual_readout_status = not_supportable_zero_baseline_without_frozen_smoothing
```

### 8.3 Sensitivity metrics

必须报告但不能替代 primary pass：

```text
sensitivity_tail_lift_20
sensitivity_tail_lift_30
sensitivity_tail_lift_60
sensitivity_tail_lift_120
ccdf_candidate_vs_baseline
MFE_120_p75 / p90 / p95
MAE_20_p10 / p05
MFE_to_MAE_ratio
winner_capture_rate
candidate_per_winner
matched_baseline_delta
```

## 9. False-positive burden gate

19B 必须显式量化非 winner 负担。每个 selected cell 输出：

```text
non_winner_rate
candidate_per_winner
fast_fail_rate
false_repair_rate
MAE_20_p10
MAE_20_p05
burden_comparator_scope
burden_comparator_MAE_20_p10
burden_comparator_MAE_20_p05
matched_baseline_MAE_20_p10_if_quality_pass
matched_baseline_MAE_20_p05_if_quality_pass
mae_abs_worsening
mae_relative_worsening
holding_period_opportunity_cost_proxy
false_positive_burden_gate
blocking_reason
```

默认 false-positive burden tolerance 继承 research plan，并在本 requirement 中冻结
缺省 cap，避免实现因缺失 config 直接进入 `19B_metric_contract_blocked`。

```text
candidate_per_winner_cap = 6.0
fast_fail_rate_cap = 0.60
false_repair_rate_cap = 0.60
mae_abs_worsening_cap = 0.02
```

默认 MAE tolerance：

```text
burden_comparator_scope =
    eligible_universe_primary for positive_exposure_robustness
    original_frozen_matched_conservative for residual_style only if
        all_three_original_frozen_baseline_quality_gate = pass

mae_abs_worsening =
    burden_comparator_MAE_20_p10 - MAE_20_p10

absolute tolerance pass:
    mae_abs_worsening <= 0.02
```

当 original frozen baseline quality 未全部通过时，positive exposure track 的
`false_positive_burden_gate` 必须使用 `eligible_universe_primary` comparator；
matched-baseline MAE 字段只能作为 diagnostic nullable 字段，不能阻断或放行
positive exposure persistence。只有 residual-style track 在三类 original frozen baseline
quality 全部通过后，才允许使用 `original_frozen_matched_conservative` comparator。

如果实现同时使用 relative tolerance，必须在 config 中冻结 conjunction/disjunction 规则。
默认不允许 pass-on-either：

```text
false_positive_burden_gate =
    candidate_per_winner <= candidate_per_winner_cap
    and fast_fail_rate <= fast_fail_rate_cap
    and false_repair_rate <= false_repair_rate_cap
    and mae_abs_worsening <= mae_abs_worsening_cap
```

如果 config 提供更严格 cap，必须在 outcome readout 前冻结，并写入
`false_positive_burden_readout.csv`。如果 config 提供更宽松 cap，必须 fail closed：

```text
decision_state = 19B_metric_contract_blocked
blocking_reason = false_positive_burden_tolerance_weakened_after_contract_default
```

## 10. Top-k concentration 和 cluster bootstrap

19B 必须证明 robustness readout 不是单一股票、少数月份或重复触发驱动。

必须输出：

```text
top_1_instrument_removed_tail_lift_against_original_frozen_baseline
top_3_instruments_removed_tail_lift_against_original_frozen_baseline
top_1_instrument_removed_positive_exposure_score_50
top_3_instruments_removed_positive_exposure_score_50
max_instrument_candidate_share
max_instrument_winner_share
max_instrument_month_candidate_share
max_decision_month_candidate_share
cluster_bootstrap_seed
cluster_bootstrap_resample_n
candidate_cluster_key
cluster_bootstrap_CI_p_candidate_50
cluster_bootstrap_CI_positive_exposure_delta_50
cluster_bootstrap_CI_primary_tail_lift_50_if_quality_pass
```

默认 top-k cap 在本 requirement 中冻结：

```text
max_instrument_winner_share_cap = 0.02
```

top-k gate 分为 positive exposure 与 residual-style 两套口径：

```text
topk_positive_exposure_gate =
    top_1_instrument_removed_positive_exposure_score_50 > 0
    and top_3_instruments_removed_positive_exposure_score_50 > 0
    and max_instrument_winner_share <= max_instrument_winner_share_cap

topk_residual_gate =
    all_three_original_frozen_baseline_quality_gate = pass
    and top_1_instrument_removed_tail_lift_against_original_frozen_baseline >= 1.0
    and top_3_instruments_removed_tail_lift_against_original_frozen_baseline >= 1.0
    and max_instrument_winner_share <= max_instrument_winner_share_cap
```

如果 top-k removal 后 positive exposure pass 消失，最终结论必须降级：

```text
decision_state = 19B_topk_concentration_blocked
```

如果 matched baseline quality 失败，则 `topk_residual_gate` 只能输出 diagnostic，不得阻断
positive exposure diagnostic。

## 11. Required figures

19B 必须生成四张 research-plan required figures。图可以由同名 CSV 支撑，但报告中必须引用：

```text
figures/tail_lift_curve.png
figures/ccdf_survival_curve.png
figures/capture_vs_burden.png
figures/mfe_mae_joint_scatter.png
```

对应数据文件：

```text
tail_lift_curve_readout.csv
ccdf_survival_curve_readout.csv
capture_vs_burden_readout.csv
mfe_mae_joint_readout.csv
```

图表必须按 family/cell 分面或分色，并同时显示 candidate、eligible universe baseline 和 matched baseline
的口径。若 matched baseline quality 失败，图例和报告必须明确标注 matched baseline readout
为 diagnostic-only。

## 12. Search accounting 和 correction scope

19B 必须沿用 19B0 冻结的测试集合：

```text
N_family_brought_to_robustness = 2
N_tested_family_cell_pairs = 2
tested family/cell pairs = B2 selected cell, B5 selected cell
```

默认 correction scope 必须拆名输出：

```text
positive_beta_exposure_correction_scope =
    2 * positive_exposure_score_50

residual_alpha_correction_scope_19b0_frozen =
    0 * primary_tail_lift_50

residual_style_readout_correction_scope_19b =
    2 * primary_tail_lift_50
```

其中 `2` 来自 19B0 冻结的 `N_tested_family_cell_pairs = 2`。三类 original frozen
baseline 使用 conjunctive conservative pass，不构成 pass-on-any-baseline 的额外选择机会。
`residual_alpha_correction_scope_19b0_frozen` 用来证明 19B0 未发出 residual-alpha promotion；
`residual_style_readout_correction_scope_19b` 只服务 19B robustness readout 的
Sidak alpha 计算。

如果任一 original frozen baseline quality fail：

```text
residual_alpha_support_claim_allowed_19b = false
matched_baseline_residual_gate = fail
```

19B 不允许根据 robustness outcome 只保留 survivor。所有 tested family/cell 必须出现在
最终 metric、decision 和报告中。

### 12.1 Cell-level 与 run-level 聚合

每个 selected family/cell 必须先生成 `cell_decision_state`，再聚合为 run-level
`decision_state`。cell-level gate 定义如下：

```text
cell_positive_exposure_gate =
    positive_exposure_robustness_pass
    and false_positive_burden_gate = pass
    and topk_positive_exposure_gate = pass

cell_residual_style_gate =
    matched_baseline_residual_pass_19b
    and false_positive_burden_gate = pass
    and topk_residual_gate = pass

cell_decision_state =
    residual_alpha_supported
    if cell_residual_style_gate

    positive_exposure_persistent_baseline_quality_blocked
    if cell_positive_exposure_gate
    and original frozen baseline quality did not conjunctively pass

    positive_exposure_persistent_residual_not_supported
    if cell_positive_exposure_gate
    and original frozen baseline quality passes
    and matched_baseline_residual_pass_19b = false

    false_positive_burden_blocked
    if positive_exposure_robustness_pass
    and false_positive_burden_gate = fail

    topk_concentration_blocked
    if positive_exposure_robustness_pass
    and false_positive_burden_gate = pass
    and topk_positive_exposure_gate = fail

    robustness_not_supported
    otherwise
```

run-level blocked state 只在没有任何 selected cell 取得正向 `cell_decision_state`
时触发。换言之，若 B2 通过 positive exposure gate 而 B5 false-positive fail，
run-level 仍可进入 positive-exposure diagnostic 状态，但报告和 handoff 必须逐 cell
披露 B5 的 failure。全局 contract blocked 例外：upstream、outcome boundary、metric
contract、output contract 任一失败时必须直接停止，不进入 cell-level 聚合。

## 13. Decision states

允许的 `decision_state`：

```text
19B_residual_alpha_supported_for_validation_stress_readout
19B_positive_exposure_persistent_enrichment_only_diagnostic
19B_robustness_not_supported
19B_false_positive_burden_blocked
19B_topk_concentration_blocked
19B_baseline_quality_blocked_enrichment_only_diagnostic_possible
19B_upstream_19a_contract_blocked
19B_upstream_19b0_contract_blocked
19B_outcome_boundary_blocked
19B_metric_contract_blocked
19B_output_contract_blocked
```

机械推导规则：

```text
If upstream 19A / 19B0 contract fails:
    decision_state = corresponding upstream blocked state

Else if validation outcome is read or cannot be proven unread:
    decision_state = 19B_outcome_boundary_blocked

Else if required metric tolerances / correction scopes are not frozen,
or config attempts to weaken the contract-default burden caps:
    decision_state = 19B_metric_contract_blocked

Else if any selected cell obtains cell_decision_state = residual_alpha_supported:
    decision_state = 19B_residual_alpha_supported_for_validation_stress_readout
    next_allowed_requirement = requirement_19b1_validation_stress_readout.md

Else if no residual cell exists,
and at least one selected cell obtains
cell_decision_state = positive_exposure_persistent_baseline_quality_blocked:
    decision_state = 19B_baseline_quality_blocked_enrichment_only_diagnostic_possible
    next_allowed_requirement = none

Else if no residual cell exists,
and at least one selected cell obtains
cell_decision_state = positive_exposure_persistent_residual_not_supported:
    decision_state = 19B_positive_exposure_persistent_enrichment_only_diagnostic
    next_allowed_requirement = none

Else if no positive/residual cell exists,
and at least one selected cell has cell_decision_state = false_positive_burden_blocked:
    decision_state = 19B_false_positive_burden_blocked
    next_allowed_requirement = none

Else if no positive/residual cell exists,
and at least one selected cell has cell_decision_state = topk_concentration_blocked:
    decision_state = 19B_topk_concentration_blocked
    next_allowed_requirement = none

Else if positive exposure or residual-style primary robustness fails:
    decision_state = 19B_robustness_not_supported
    next_allowed_requirement = none
```

若没有任何正向 cell，false-positive burden 或 top-k gate 失败优先于 generic
robustness failure：

```text
19B_false_positive_burden_blocked
19B_topk_concentration_blocked
```

注意：即使 `19B_residual_alpha_supported_for_validation_stress_readout` 成立，本 19B 仍不授权
19C replay。由于 validation outcome 在本 requirement 中禁止读取，下一步必须先做单独的
validation stress readout，且 validation 只能 downgrade/veto，不能改善或选择。

## 14. Required outputs

19B output root：

```text
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout
```

机器可读输出：

```text
input_artifact_audit.csv
upstream_19a_contract_audit.csv
upstream_19b0_contract_audit.csv
robustness_outcome_boundary_audit.csv
robustness_candidate_row_manifest.csv
robustness_baseline_row_manifest.csv
baseline_repair_variant_registry.csv
baseline_repair_sweep_audit.csv
robustness_metric_readout.csv
robustness_baseline_quality_audit.csv
robustness_positive_exposure_readout.csv
robustness_residual_alpha_readout.csv
false_positive_burden_readout.csv
tail_lift_curve_readout.csv
ccdf_survival_curve_readout.csv
capture_vs_burden_readout.csv
mfe_mae_joint_readout.csv
topk_concentration_sensitivity.csv
cluster_bootstrap_ci.csv
search_accounting_audit.csv
entry_universe_19b_decision.csv
```

叙述输出：

```text
19B_robust_right_tail_enrichment_and_false_positive_burden_readout_report.md
19B_handoff_contract.md
```

图表输出：

```text
figures/tail_lift_curve.png
figures/ccdf_survival_curve.png
figures/capture_vs_burden.png
figures/mfe_mae_joint_scatter.png
```

manifest 输出：

```text
manifest_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json
output_hashes_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json
```

## 15. Required schemas

### 15.1 `input_artifact_audit.csv`

```text
artifact_id
artifact_path
required_flag
exists
row_count_if_tabular
source_manifest_hash
observed_file_hash
hash_verified
input_artifact_gate
blocking_reason
```

### 15.2 `upstream_19a_contract_audit.csv`

```text
artifact_id
required_fact
expected_value
observed_value
contract_gate
blocking_reason
```

### 15.3 `upstream_19b0_contract_audit.csv`

```text
artifact_id
required_fact
expected_value
observed_value
contract_gate
blocking_reason
```

### 15.4 `robustness_candidate_row_manifest.csv`

不得包含 forward outcome / validation outcome 字段。

```text
family_id
grid_cell_id
parameter_hash
split
row_key
instrument_id
decision_date
executable_next_open_date
primary_enrichment_denominator_flag
candidate_flag
manifest_frozen_before_label_readout
label_read_before_manifest_freeze
row_source_hash
blocking_reason
```

### 15.5 `robustness_baseline_row_manifest.csv`

不得包含 forward outcome / validation outcome 字段。

```text
family_id
grid_cell_id
parameter_hash
split
repair_variant_id
baseline_family
variant_role
candidate_row_key
baseline_row_key
baseline_instrument_id
baseline_decision_date
matching_weight
manifest_frozen_before_label_readout
label_read_before_manifest_freeze
row_source_hash
blocking_reason
```

### 15.6 `robustness_baseline_quality_audit.csv`

```text
family_id
grid_cell_id
split
repair_variant_id
baseline_family
variant_role
primary_residual_claim_allowed
candidate_n
matched_candidate_n
unmatched_candidate_n
unmatched_candidate_rate
baseline_reuse_rate
max_standardized_mean_difference_after_matching
per_feature_smd_json
decision_month_coverage_delta
instrument_coverage_delta
matched_baseline_primary_row_count
primary_enrichment_denominator_row_count
common_support_pass
baseline_matching_quality_gate
quality_blocks_residual_alpha_only
positive_exposure_readout_allowed
diagnostic_repair_only_flag
failure_reason
```

### 15.7 `robustness_positive_exposure_readout.csv`

该文件是 `robustness_metric_readout.csv` 的 positive-exposure 投影；重叠字段必须逐值一致。

```text
family_id
grid_cell_id
parameter_hash
split
p_candidate_50
p_eligible_universe_50
positive_exposure_delta_50
positive_exposure_ratio_50
positive_exposure_SE_delta_probability
cluster_bootstrap_SE_margin_50
positive_exposure_margin_50
positive_exposure_score_50
positive_exposure_p_value_method
positive_exposure_p_value_50
positive_exposure_sidak_alpha
positive_exposure_robustness_pass
false_positive_burden_gate
topk_positive_exposure_gate
cell_positive_exposure_gate
cell_decision_state
blocking_reason
```

### 15.8 `robustness_residual_alpha_readout.csv`

该文件是 `robustness_metric_readout.csv` 的 residual-style 投影；重叠字段必须逐值一致。

```text
family_id
grid_cell_id
parameter_hash
split
all_three_original_frozen_baseline_quality_gate
p_candidate_50
p_matched_50_by_original_frozen_baseline_json
p_matched_50_primary_residual_baseline
residual_SE_delta_probability
residual_corrected_margin_ratio_50
primary_tail_lift_50
primary_tail_lift_50_margin_adjusted
residual_p_value_method
residual_rerandomization_n
residual_rerandomization_seed
primary_tail_lift_50_p_value
residual_alpha_sidak_alpha
matched_baseline_residual_pass_19b
residual_alpha_support_claim_allowed_19b
residual_readout_status
residual_blocking_reason
topk_residual_gate
cell_residual_style_gate
cell_decision_state
blocking_reason
```

### 15.9 `tail_lift_curve_readout.csv`

```text
family_id
grid_cell_id
split
baseline_family
curve_scope
horizon_sessions
threshold_return
p_candidate
p_eligible_universe
p_matched_baseline_if_quality_pass
tail_lift_vs_eligible_universe
tail_lift_vs_matched_baseline_if_quality_pass
diagnostic_only_flag
blocking_reason
```

### 15.10 `ccdf_survival_curve_readout.csv`

```text
family_id
grid_cell_id
split
baseline_family
curve_scope
horizon_sessions
threshold_return
candidate_ccdf
eligible_universe_ccdf
matched_baseline_ccdf_if_quality_pass
diagnostic_only_flag
blocking_reason
```

### 15.11 `capture_vs_burden_readout.csv`

```text
family_id
grid_cell_id
split
threshold_return
candidate_n
winner_n
winner_capture_rate
candidate_per_winner
non_winner_rate
fast_fail_rate
false_repair_rate
MAE_20_p10
burden_comparator_scope
mae_abs_worsening
diagnostic_only_flag
blocking_reason
```

### 15.12 `mfe_mae_joint_readout.csv`

```text
family_id
grid_cell_id
split
row_scope
row_key
instrument_id
decision_date
MFE_120
MAE_20
forward_big_winner_120d
fast_fail_flag
false_repair_flag
diagnostic_only_flag
blocking_reason
```

### 15.13 `search_accounting_audit.csv`

```text
N_family_brought_to_robustness
N_tested_family_cell_pairs
tested_family_cell_pairs_json
positive_beta_exposure_correction_scope
residual_alpha_correction_scope_19b0_frozen
residual_style_readout_correction_scope_19b
family_level_correction
cell_level_accounting
robustness_outcome_used_to_drop_survivors
search_accounting_gate
blocking_reason
```

### 15.14 `robustness_metric_readout.csv`

```text
family_id
grid_cell_id
parameter_hash
split
label_anchor_type
promotion_claim_type_19b0
candidate_n
tradable_n
instrument_n
instrument_month_n
decision_month_n
cooldown_entry_n
primary_denominator_n
path_complete_20_n
path_complete_30_n
path_complete_60_n
path_complete_120_n
p_candidate_50
p_eligible_universe_50
positive_exposure_delta_50
positive_exposure_ratio_50
positive_exposure_SE_delta_probability
cluster_bootstrap_SE_margin_50
positive_exposure_margin_50
positive_exposure_score_50
positive_exposure_p_value_method
positive_exposure_p_value_50
positive_exposure_sidak_alpha
positive_exposure_robustness_pass
p_matched_50_primary_residual_baseline
residual_SE_delta_probability
residual_corrected_margin_ratio_50
primary_tail_lift_50
primary_tail_lift_50_margin_adjusted
residual_p_value_method
primary_tail_lift_50_p_value
residual_alpha_sidak_alpha
matched_baseline_residual_pass_19b
residual_alpha_support_claim_allowed_19b
residual_readout_status
residual_blocking_reason
false_positive_burden_gate
topk_positive_exposure_gate
topk_residual_gate
cell_positive_exposure_gate
cell_residual_style_gate
cell_decision_state
blocking_reason
```

### 15.15 `baseline_repair_variant_registry.csv`

```text
repair_variant_id
baseline_family
variant_role
matching_method
bucket_spec_id
caliper_spec_id
primary_residual_claim_allowed
diagnostic_repair_only_flag
outcome_read_before_registry_freeze
registry_frozen_before_label_readout
blocking_reason
```

### 15.16 `baseline_repair_sweep_audit.csv`

```text
family_id
grid_cell_id
repair_variant_id
baseline_family
variant_role
primary_residual_claim_allowed
matching_method
bucket_spec_id
caliper_spec_id
candidate_n
matched_candidate_n
unmatched_candidate_n
unmatched_candidate_rate
baseline_reuse_rate
max_standardized_mean_difference_after_matching
per_feature_smd_json
decision_month_coverage_delta
instrument_coverage_delta
matched_baseline_primary_row_count
primary_enrichment_denominator_row_count
common_support_pass
baseline_matching_quality_gate
quality_blocks_residual_alpha_only
positive_exposure_readout_allowed
diagnostic_repair_only_flag
failure_reason
```

### 15.17 `false_positive_burden_readout.csv`

```text
family_id
grid_cell_id
split
candidate_n
winner_n
non_winner_n
non_winner_rate
candidate_per_winner
fast_fail_rate
false_repair_rate
MAE_20_p10
MAE_20_p05
burden_comparator_scope
burden_comparator_MAE_20_p10
burden_comparator_MAE_20_p05
matched_baseline_MAE_20_p10_if_quality_pass
matched_baseline_MAE_20_p05_if_quality_pass
mae_abs_worsening
mae_relative_worsening
candidate_per_winner_cap
fast_fail_rate_cap
false_repair_rate_cap
mae_abs_worsening_cap
false_positive_burden_gate
blocking_reason
```

### 15.18 `robustness_outcome_boundary_audit.csv`

```text
selected_family_cell_pair_n
robustness_candidate_manifest_frozen_before_label_readout
robustness_baseline_manifest_frozen_before_label_readout
robustness_outcome_row_n_loaded
validation_outcome_columns_loaded
validation_outcome_row_n
validation_label_value_access_n
robustness_outcome_used_to_expand_or_select_test_set
boundary_gate
blocking_reason
```

### 15.19 `topk_concentration_sensitivity.csv`

```text
family_id
grid_cell_id
split
baseline_family
top_1_instrument_removed_tail_lift_against_original_frozen_baseline
top_3_instruments_removed_tail_lift_against_original_frozen_baseline
top_1_instrument_removed_positive_exposure_score_50
top_3_instruments_removed_positive_exposure_score_50
max_instrument_candidate_share
max_instrument_winner_share
max_instrument_month_candidate_share
max_decision_month_candidate_share
topk_positive_exposure_gate
topk_residual_gate
diagnostic_only_flag
blocking_reason
```

### 15.20 `cluster_bootstrap_ci.csv`

```text
family_id
grid_cell_id
split
metric_id
cluster_key
resample_n
seed
p_value_method
alternative
estimate
SE
ci_low
ci_high
p_value
sidak_alpha
bootstrap_contract_gate
blocking_reason
```

### 15.21 `entry_universe_19b_decision.csv`

```text
run_id
created_at
requirement_file_hash
config_file_hash
upstream_19a_manifest_hash
upstream_19b0_manifest_hash
decision_state
next_allowed_requirement
upstream_19a_contract_gate
upstream_19b0_contract_gate
outcome_boundary_gate
robustness_candidate_manifest_gate
baseline_repair_registry_gate
baseline_matching_quality_gate
positive_exposure_robustness_gate
matched_baseline_residual_gate
false_positive_burden_gate
topk_positive_exposure_gate
topk_residual_gate
cluster_bootstrap_gate
search_accounting_gate
output_contract_gate
N_family_brought_to_robustness
N_tested_family_cell_pairs
N_positive_exposure_robustness_pass
N_matched_baseline_residual_pass
N_original_frozen_baseline_quality_pass
N_cell_false_positive_burden_fail
N_cell_topk_concentration_fail
positive_beta_exposure_correction_scope
residual_alpha_correction_scope_19b0_frozen
residual_style_readout_correction_scope_19b
validation_outcome_read
model_training_authorized
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
max_ep19_terminal_state_if_no_residual_pass
blocking_reason
```

所有 authorization 字段必须为 `false`。

## 16. 报告要求

中文报告必须包含：

```text
1. 19A / 19B0 ready 证据和 hash/manifest 校验摘要。
2. 19B outcome boundary，明确 validation outcome 未读取。
3. 19B0 冻结的 selected B2/B5 family/cell manifest。
4. B2/B5 的 train readout 摘要和 19B robustness readout 对比。
5. robustness primary denominator、instrument_n、instrument_month_n、
   decision_month_n 和 path completeness。
6. positive exposure robustness track：p_candidate_50、eligible universe base rate、
   delta、ratio、margin、score、correction scope。
7. matched-baseline residual track：original frozen baseline 的 quality gate、
   SMD、unmatched、p_matched_50、primary_tail_lift_50、margin-adjusted readout、
   residual-style correction scope，并单独披露 diagnostic repair variants 不支持 residual claim。
8. false-positive burden：candidate_per_winner、fast_fail_rate、false_repair_rate、
   MAE left-tail、burden comparator scope、burden gate。
9. 四张 required figures：tail lift curve、CCDF/survival、capture vs burden、
   MFE/MAE scatter。
10. top-k instrument/month concentration 和 cluster bootstrap CI。
11. B2 和 B5 的逐项结论：cell_decision_state、persistent exposure、
    residual-style support、diagnostic-only 或 blocked。
12. final decision_state、next_allowed_requirement 和授权边界。
```

报告必须明确写出：

```text
19B 不是 policy。
19B 不是 backtest。
19B 不授权 production signal 或 live trading。
19B 不读取 validation outcome。
positive exposure persistence 不是 independent alpha。
matched-baseline quality failure blocks residual-alpha support only.
positive exposure persistence without matched-baseline residual pass can only
support 19_entry_universe_enrichment_only_diagnostic.
19C replay remains forbidden unless a later requirement explicitly authorizes it
after validation stress handling.
```

## 17. 验证命令

预期命令：

```bash
cd topics/02_AFML_BIG_WINNER

python -m py_compile \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py

python -m pytest \
  experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py

python \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py \
  --config experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.yaml

git diff --check
```

如果 `ruff` 可用，还应运行：

```bash
python -m ruff check \
  experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py \
  experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.py
```

## 18. Acceptance checklist

```text
[ ] 19A decision ready 且 manifest/hash 可验证。
[ ] 19B0 decision = 19B0_candidate_family_eligible_for_19B。
[ ] 19B0 next_allowed_requirement 指向本 requirement。
[ ] robustness_test_manifest 冻结且只包含 B2/B5 两个 selected cells。
[ ] promotion_claim_type、selection_track、19B0 frozen correction scope 从 19B0 原样继承。
[ ] validation outcome 不被读取、materialize、join、缓存或写入输出。
[ ] robustness candidate/baseline manifests 在 outcome readout 前冻结。
[ ] executable next-open anchored label 继续作为 primary label。
[ ] EP07 event-anchored ready-made label 不进入 primary metric 或 decision。
[ ] diagnostic repair variants 在 outcome 前冻结，且不允许产生 residual claim。
[ ] residual-style support 只来自三类 original frozen baseline 的 conjunctive pass。
[ ] `residual_alpha_correction_scope_19b0_frozen = 0 * primary_tail_lift_50`，
    且 `residual_style_readout_correction_scope_19b = 2 * primary_tail_lift_50`。
[ ] diagnostic repair variants 不扩大或改变 residual-style readout correction scope。
[ ] positive exposure robustness track 与 residual-style matched-baseline track 分开。
[ ] positive exposure p-value method、cluster key、seed、resample_n 已冻结并输出。
[ ] broad eligible-universe base rate、positive exposure margin 和 score 已披露。
[ ] matched-baseline quality failure 只阻断 residual-alpha support，不自动阻断
    positive exposure diagnostic。
[ ] false-positive burden comparator scope 已按 positive exposure / residual-style track
    分开输出。
[ ] false-positive burden tolerance 和 cap 值使用本 requirement 默认值，或在 config 中
    进一步收紧且于 outcome 前冻结。
[ ] candidate_per_winner、fast_fail、false_repair、MAE left-tail 已读出。
[ ] top1/top3 removal、instrument/month concentration 和 cluster bootstrap CI 已读出。
[ ] 四张 required figures 及其 CSV 支撑文件已输出。
[ ] family-level multiplicity correction 和 search accounting 已机械校验。
[ ] output_hashes 与 manifest 覆盖所有输出。
[ ] cell_decision_state 先逐 cell 推导，run-level decision_state 再按机械聚合规则推导。
[ ] 所有 policy/trading authorization 字段为 false。
```
