# Requirement: 19B3 B2 Positive-Exposure Left-Tail Budget Frontier

## 0. 不可协商范围

19B3 是读取 19B/19B1/19B2 结果后，由 `research_plan.md` Section 12 发起的
human research restart。它不是 19B2 pipeline handoff，因为 19B2 的正式输出仍是：

```text
decision_state = 19B2_suppressor_improves_burden_but_not_interaction_supported_diagnostic
next_allowed_requirement = none
max_ep19_terminal_state = 19_entry_universe_enrichment_only_diagnostic
```

本 requirement 不追溯改变上述裁决，只检验一个新问题：

```text
在冻结 B2 positive-exposure sleeve 和右尾牺牲预算后，
当前最强 simple incumbent A_VOL60_top30（R2）能否在新的 forward OOS 上
复现 left-tail ES / MAE 改善并保住 positive exposure/right-tail budget；
smooth continuous R3 是否继续落后于 hard-trim frontier？
```

19B3 允许：

```text
冻结一个 B2 family/cell/hash
从 PIT universe、qfq daily 和 benchmark daily 重建 forward OOS B2 rows
比较 R0/R1/R2/R3 与同预算 placebo P0
计算 weighted left-tail ES、MAE quantile、left-tail exceedance
计算 +50% right-tail exposure / capture retention
计算 effective exposure、concentration、bootstrap 和 placebo randomization
在 forward primary decision 完成后，按授权读取一次 validation stress
输出 diagnostic decision 和下一研究边界
```

19B3 禁止：

```text
训练模型
搜索新的 family/cell 或扩展 feature set
在 forward OOS 或 validation stress 上选择 threshold / weight floor / formula
用 validation 选择 arm、确认 support、补样本或救活 forward failure
把 matched-baseline failure 解释为 pure beta / alpha = 0
把 MFE event rate 解释为可实现收益
运行 exit / stop / delayed-entry / holding replay
做 target-vol portfolio、position sizing、portfolio backtest
输出 entry / exit / holding policy、production signal 或 live trading authorization
```

19B3 的 `validation` 固定为压力测试集：

```text
validation can maintain, downgrade, or veto an existing forward conclusion.
validation cannot create, select, improve, promote, or rescue support.
```

## 1. 身份与 staged execution

```text
experiment_id = 19_entry_universe_pit_tradability_preflight
phase_id = 19B3
run_id = 19B3_b2_positive_exposure_left_tail_budget_frontier
requirement_file = requirement_19b3_b2_positive_exposure_left_tail_budget_frontier.md
config_file = configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml
runner_file = src/run_19b3_b2_positive_exposure_left_tail_budget_frontier.py
test_file = tests/test_19b3_b2_positive_exposure_left_tail_budget_frontier.py
output_root = outputs/19B3_b2_positive_exposure_left_tail_budget_frontier
```

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

Config 路径必须相对该 topic root 或通过显式 alias 解析；禁止硬编码个人机器绝对路径。

实现必须支持且发布时必须依次执行：

```text
freeze
forward
validation-stress   # only when forward handoff authorizes it
finalize
```

禁止提供绕过 stage lock 的 `--stage all` 发布路径。每个 stage 必须验证前一阶段 immutable hash bundle。

### 1.1 Config contract

Config 必须冻结以下 section；缺失、类型错误或出现未注册 primary arm 时 fail closed：

```yaml
run_id: 19B3_b2_positive_exposure_left_tail_budget_frontier
experiment_id: 19_entry_universe_pit_tradability_preflight
phase_id: 19B3

input_paths:
  research_plan: experiments/pending/19_entry_universe_pit_tradability_preflight/research_plan.md
  nineteen_a_contract_freeze: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/19A_contract_freeze.md
  nineteen_a_manifest: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/manifest_19a_entry_universe_pit_lineage_tradability_and_data_contract.json
  nineteen_a_output_hashes: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/output_hashes_19a_entry_universe_pit_lineage_tradability_and_data_contract.json
  split_construction_freeze: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/split_construction_freeze.csv
  validation_stress_rule_freeze: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/validation_stress_rule_freeze.csv
  cooldown_audit: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/cooldown_audit.csv
  entry_execution_convention_audit: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/entry_execution_convention_audit.csv
  entry_fill_feasibility_audit: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/entry_fill_feasibility_audit.csv
  censoring_treatment_freeze: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/censoring_treatment_freeze.csv
  forward_outcome_label_freeze: .../outputs/19A_entry_universe_pit_lineage_tradability_and_data_contract/forward_outcome_label_freeze.csv
  nineteen_b0_grid_cell_manifest: .../outputs/19B0_fast_rule_grid_enrichment_scan/grid_cell_manifest.csv
  nineteen_b0_selected_family_cell_manifest: .../outputs/19B0_fast_rule_grid_enrichment_scan/selected_family_cell_manifest.csv
  nineteen_b0_simple_rule_feature_source_map: .../outputs/19B0_fast_rule_grid_enrichment_scan/simple_rule_feature_source_map.csv
  nineteen_b0_matching_feature_source_map: .../outputs/19B0_fast_rule_grid_enrichment_scan/matching_feature_source_map.csv
  nineteen_b0_label_source_map: .../outputs/19B0_fast_rule_grid_enrichment_scan/label_source_map.csv
  nineteen_b0_output_hashes: .../outputs/19B0_fast_rule_grid_enrichment_scan/output_hashes_19b0_fast_rule_grid_enrichment_scan.json
  nineteen_b_decision: .../outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/entry_universe_19b_decision.csv
  nineteen_b_metric_readout: .../outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/robustness_metric_readout.csv
  nineteen_b_candidate_manifest: .../outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/robustness_candidate_row_manifest.csv
  nineteen_b_outcome_boundary_audit: .../outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/robustness_outcome_boundary_audit.csv
  nineteen_b_output_hashes: .../outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/output_hashes_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json
  nineteen_b1_decision: .../outputs/19B1_t0_left_right_tail_separability_readout/entry_universe_19b1_decision.csv
  nineteen_b1_overlap_readout: .../outputs/19B1_t0_left_right_tail_separability_readout/outcome_left_right_overlap_readout.csv
  nineteen_b1_manifest: .../outputs/19B1_t0_left_right_tail_separability_readout/manifest_19b1_t0_left_right_tail_separability_readout.json
  nineteen_b1_output_hashes: .../outputs/19B1_t0_left_right_tail_separability_readout/output_hashes_19b1_t0_left_right_tail_separability_readout.json
  nineteen_b2_decision: .../outputs/19B2_b2_high_vol_extension_left_tail_suppressor_ablation/entry_universe_19b2_decision.csv
  nineteen_b2_variant_grid: .../outputs/19B2_b2_high_vol_extension_left_tail_suppressor_ablation/suppressor_variant_grid.csv
  nineteen_b2_ablation_readout: .../outputs/19B2_b2_high_vol_extension_left_tail_suppressor_ablation/suppressor_ablation_readout.csv
  nineteen_b2_manifest: .../outputs/19B2_b2_high_vol_extension_left_tail_suppressor_ablation/manifest_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.json
  nineteen_b2_output_hashes: .../outputs/19B2_b2_high_vol_extension_left_tail_suppressor_ablation/output_hashes_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.json
  topn_executable_universe: data/processed/universe/pit_topn_400_100_executable_daily.csv
  stock_qfq_dir: data/raw/akshare/day/qfq
  benchmark_daily: data/processed/index/benchmark_indices_daily.csv

output:
  output_root: experiments/pending/19_entry_universe_pit_tradability_preflight/outputs/19B3_b2_positive_exposure_left_tail_budget_frontier
  output_root_may_be_created: true
  immutable_stage_subdirs: true

primary_scope:
  family_id: B2_relative_strength_breakout
  grid_cell_id: B2-relative-strength-breakout__182b3d0f30f5
  parameter_hash: 182b3d0f30f5c407544f209b2597ca6959a1ad8e8f94d6957345c7931da6e1a2
  row_scope: candidate_primary_denominator
  denominator_contract_id: primary_enrichment_denominator
  entry_anchor: next_executable_open
  cooldown_window_sessions: 10
  cooldown_scope: instrument

split:
  train_start: 2018-01-18
  train_end: 2021-12-31
  validation_stress_start: 2022-01-04
  validation_stress_end: 2023-12-29
  spent_robustness_start: 2024-01-02
  spent_robustness_end: 2025-11-26
  forward_oos_nominal_start_exclusive: 2025-11-26
  forward_oos_effective_start_rule: first_decision_after_spent_outcome_path_end_plus_embargo
  forward_oos_end_rule: latest_decision_date_with_120_session_path_complete
  forward_horizon_sessions: 120
  purge_window_sessions: 120
  embargo_window_sessions: 20

b2_rule:
  stock_vs_market_return_20d_min: 0.15
  return_60d_cross_section_rank_pct_min: 0.90
  close_to_ema60_min: 0.00
  market_regime_filter: all

arms:
  primary_arm_id: R2_VOL60_TOP30_TRIM
  comparator_arm_ids: [R0_S0_UNTRIMMED, R1_ATR20_TOP10_TRIM, R3_CONTINUOUS_VOL_BUDGET]
  placebo_arm_id: P0_R2_SAME_DAY_RANDOM_TRIM
  r1_candidate_q_atr20_quantile: 0.90
  r2_candidate_q_vol60_quantile: 0.70
  hard_trim_quantile_method: linear
  hard_trim_tie_rule: remove_equal_threshold
  r3_vol60_median_scope: same_day_full_executable_eligible_universe
  continuous_weight_floor: 0.25
  continuous_weight_cap: 1.00
  epsilon: 1.0e-12
  cash_treatment: unallocated_weight_remains_cash_no_redistribution

spent_design_role_audit:
  split: robustness
  design_only_no_support_claim: true
  primary_arm_expected: R2_VOL60_TOP30_TRIM
  diagnostic_challenger_expected: R3_CONTINUOUS_VOL_BUDGET
  numeric_tolerance: 1.0e-9
  expected_R2_candidate_q_vol60_p70: 0.9458917835671342
  expected_R2_retained_n: 1082
  expected_R2_weight_sum: 1082.0
  expected_R2_right_tail_capture: 0.6459770114942529
  expected_R2_ES10: 0.26073103500724965
  expected_R2_MAE20_p10: -0.1998799519807923
  expected_R2_p_left_tail_20: 0.09981515711645102
  expected_R3_right_tail_capture: 0.5799618225830623
  expected_R3_weight_sum: 988.9036149812879
  expected_R3_ES10: 0.2746192039435396
  expected_R3_MAE20_p10: -0.2138511932615816
  expected_R3_ES10_improvement_vs_R2: -0.013888168936289969
  continuous_feasibility_screen_gamma: [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
  continuous_feasibility_screen_floor: [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
  continuous_feasibility_variant_n_expected: 36
  continuous_feasibility_joint_point_gate_pass_n_expected: 0
  continuous_feasibility_variant_allowed_in_forward: false

labels:
  right_tail_event_50: 0.50
  left_tail_event_10: -0.10
  left_tail_event_20: -0.20
  left_tail_event_30: -0.30
  primary_left_tail_mass: 0.10

forward_support:
  candidate_n_min: 300
  instrument_n_min: 50
  instrument_month_n_min: 200
  decision_month_n_min: 6
  right_tail_event_50_n_min: 50
  path_complete_120_rate_min: 0.95
  rank_cross_section_n_min: 30
  effective_exposure_n_min: 200
  effective_exposure_ratio_min: 0.60

forward_evaluability:
  preoutcome_gate_excludes_right_tail_event_count: true
  no_post_embargo_row_treatment: pipeline_dry_run_only
  preoutcome_support_failure_treatment: pipeline_dry_run_only
  outcome_read_before_preoutcome_evaluable: false
  earliest_evaluable_month_unknown_value: not_yet_observed

forward_gates:
  mae_20_p10_improvement_vs_r0_min: 0.03
  p_left_tail_20_relative_reduction_vs_r0_min: 0.30
  primary_positive_exposure_ratio_50_min: 1.20
  right_tail_capture_retention_min: 0.60
  left_tail_es10_improvement_vs_r1_min: 0.01
  absolute_mae_worsening_vs_eligible_cap: 0.02
  max_instrument_weight_share_cap: 0.02
  max_instrument_right_tail_weight_share_cap: 0.02
  max_instrument_month_weight_share_cap: 0.02
  max_decision_month_weight_share_cap: 0.20
  calendar_direction_stable_rate_min: 0.80
  placebo_p_value_max: 0.05

positive_exposure_comparator:
  primary_denominator: arm_calendar_matched_eligible_same_dates
  legacy_bridge_denominator: unweighted_eligible_same_dates
  primary_ratio_floor: 1.20
  legacy_bridge_is_gate: false

validation_stress:
  selection_allowed: false
  can_create_or_upgrade_support: false
  threshold_role: frozen_directional_veto_not_forward_support
  arm_registry_must_equal_freeze: true
  inherit_forward_support_floors: true
  decision_month_n_min: 6
  fixed_window_decision_month_upper_bound_expected: 11
  support_floor_must_not_exceed_fixed_window_upper_bound: true
  apply_purge_embargo_censoring: true
  primary_positive_exposure_ratio_50_floor: 1.00
  right_tail_capture_retention_floor: 0.60
  left_tail_es10_improvement_vs_r0_floor: 0.00
  mae_20_p10_improvement_vs_r0_floor: 0.00
  p_left_tail_20_relative_reduction_vs_r0_floor: 0.00
  underpowered_treatment: downgrade_to_underpowered_not_pass

bootstrap:
  primary_cluster_key: instrument
  calendar_stress_key: decision_month
  resample_n: 2000
  seed: 20260710
  rng: numpy_default_rng_PCG64
  ci_level: 0.95

placebo:
  permutation_n: 2000
  seed: 20260711
  rng: numpy_default_rng_PCG64
  primary_strata: decision_date|board_bucket
  fallback_strata: decision_date

runtime:
  cache_preoutcome_feature_panel: true
  cache_may_contain_outcome_columns: false
  progress_every_instruments: 250
```

上面 config block 中的 `...` 是唯一固定 alias：
`experiments/pending/19_entry_universe_pit_tradability_preflight`。Runner 必须先展开该 alias，
不得把 `...` 当作字面路径，也不得搜索同名目录猜测输入。
`forward_gates.primary_positive_exposure_ratio_50_min` 必须等于
`positive_exposure_comparator.primary_ratio_floor`；不相等时 config contract fail closed。

## 2. 上游合同与 human restart lineage

实现必须机械验证：

```text
19A:
    all_critical_gates_pass = true
    cooldown_window_sessions = 10
    validation_selection_allowed = false

19B0 selected B2:
    family_id / grid_cell_id / parameter_hash 与 config 完全一致
    selection_track = positive_beta_exposure

19B B2 component:
    positive_exposure_robustness_pass = true
    false_positive_burden_gate = fail
    cell_positive_exposure_gate = false

19B1:
    family_id / grid_cell_id 与 config 完全一致
    row_scope = candidate_primary_denominator
    decision_state = 19B1_t0_left_right_tail_separable_diagnostic
    validation_outcome_read = false
    next_allowed_requirement = none

19B2:
    validation_outcome_read = false
    interaction_superiority_gate = fail
    best_single_feature_variant_id = A_ATR20_top10
    next_allowed_requirement = none
```

Research-plan restart audit 必须验证：

```text
research_plan contains Section 12 Human Research Restart
research_plan names this requirement
research_plan states validation is stress-test-only
research_plan states new support requires forward OOS
```

Manifest 必须明确：

```text
upstream_pipeline_authorization = false
restart_type = human_research_restart
restart_source = research_plan_section_12
```

所有 tracked upstream input 必须存在、非空、匹配 upstream output hashes，并记录 sha256、size、
row count 和 schema hash。Raw qfq directory 必须对实际读取文件生成排序 inventory，并计算
`qfq_input_inventory_hash`；禁止只记录目录 mtime。

Freeze 可以读取已经 spent 的 robustness outcome artifacts，但只能机械重放 config 中的
`spent_design_role_audit`，用于验证 R2-primary/R3-diagnostic 角色是否与 human restart 依据一致。
19B2 的 `best_single_feature_variant_id = A_ATR20_top10` 是 removal-efficiency/interaction audit
口径；19B3 选择 R2 是“允许更大右尾预算后最强 aggressive left-tail frontier”口径。两者不得
互相覆盖，也不得把 R2 写成 19B2 supported policy。
该 read 必须标记：

```text
dataset_role = spent_robustness_design_only
selection_or_tuning_allowed = false
support_claim_allowed = false
forward_gate_contribution = false
```

任一 expected value 不匹配 tolerance 时 `spent_design_arm_role_gate = fail`，阻断 forward outcome read；
不得现场改 threshold、formula 或 primary arm 继续运行。
`search_accounting_audit.csv` 必须记录 36 个 continuous feasibility variants、joint point-gate pass
数为 0、forward 中 materialized R3 variant 数为 1 且 promotion-eligible R3 数为 0。隐藏或新增
design variants 必须使 `search_accounting_gate = fail`。

## 3. Staged outcome-access contract

### 3.1 Stage `freeze`

只允许读取 PIT/pre-outcome 数据和 metadata，不得读取任何 forward/validation outcome value。
唯一例外是 Section 2 已登记的 spent robustness design-only role audit；它不得进入任何
forward metric、gate 或 support claim。
本 stage 必须先构造并冻结 forward candidate membership 与全部 arm weights。

必须输出并 hash：

```text
freeze/resolved_config.yaml
freeze/human_restart_authorization.json
freeze/contract_freeze_19b3.json
freeze/source_artifact_hash_audit.csv
freeze/input_artifact_audit.csv
freeze/upstream_contract_audit.csv
freeze/spent_design_arm_role_audit.csv
freeze/data_coverage_and_forward_support_audit.csv
freeze/search_accounting_audit.csv
freeze/forward_candidate_preoutcome_manifest.csv
freeze/forward_eligible_preoutcome_manifest.csv
freeze/forward_arm_weight_manifest.csv
freeze/p0_permutation_assignment_hashes.csv
freeze/b2_arm_registry.csv
freeze/outcome_access_audit.csv
freeze/freeze_manifest_19b3.json
freeze/freeze_output_hashes_19b3.json
```

审计必须证明：

```text
forward_outcome_read = false
validation_outcome_read = false
forbidden_outcome_column_read_n = 0
preoutcome_cache_forbidden_column_n = 0
```

### 3.2 Stage `forward`

先验证 freeze hash bundle 和其中已经落盘的 `forward_candidate_preoutcome_manifest.csv`、
`forward_eligible_preoutcome_manifest.csv`、`forward_arm_weight_manifest.csv`，之后才可读取
`decision_date > effective_forward_start` 且
path-complete 的 outcomes；`effective_forward_start` 按 Section 4 计算，并且必然晚于
`2025-11-26`。
在读取 outcome 前必须先计算 Section 4 `forward_preoutcome_evaluability_gate`；不通过时只允许
写 dry-run/underpowered artifacts 并直接进入 `finalize`，不得打开任何 forward outcome column。
不得读取 validation date range 的 outcome rows/columns。

若 outcome 在 membership/weight freeze 前被读取：

```text
decision_state = 19B3_forward_outcome_boundary_blocked
```

### 3.3 Stage `validation-stress`

仅以下 forward provisional states 授权 stress：

```text
19B3_forward_positive_exposure_left_tail_budget_supported
19B3_forward_left_tail_reduction_supported_but_absolute_burden_high
```

必须先验证 forward hash bundle。未获授权而读取 validation：

```text
decision_state = 19B3_validation_stress_unauthorized_access_blocked
blocking_reason = validation_read_without_forward_authorization
```

Stress membership/weights 必须先由 validation pre-outcome features 冻结。Runner 必须先关闭并
fsync 所有 preoutcome artifacts，生成 immutable `validation_preoutcome_freeze_manifest.json` 和
`validation_preoutcome_freeze_output_hashes.json`，再次校验 hash 后才可读取 outcomes。
Outcome-access audit 的 authorization artifact 必须指向该 preoutcome manifest hash。
Stress 不得修改 freeze/forward/preoutcome-freeze artifacts。

### 3.4 Stage `finalize`

不得读取 raw qfq outcome 或新的 label source。只能读取 immutable stage bundles，机械聚合 final state、
报告、handoff、manifest 和 output hashes。

## 4. Split 和数据覆盖

```text
train       = 2018-01-18 .. 2021-12-31, spent/discovery-only
validation  = 2022-01-04 .. 2023-12-29, sealed stress-test-only
robustness  = 2024-01-02 .. 2025-11-26, spent/design-only for 19B3
forward_oos = decision_date > effective_forward_start and 120-session path complete
```

Nominal split 日期不等于有效可评价边界。必须使用同一 exchange-session calendar 落实
120-session purge 和 20-session embargo：

```text
spent_outcome_path_end =
    max path_end_date_120 among every robustness candidate outcome read by 19B/19B1/19B2

effective_forward_start =
    later_of(
        2025-11-26,
        advance_exchange_sessions(spent_outcome_path_end, 20)
    )

forward row requires decision_date > effective_forward_start
```

Validation stress 仍使用 nominal `2022-01-04 .. 2023-12-29`，但有效 rows 必须同时满足：

```text
decision_date > advance_exchange_sessions(train_spent_outcome_path_end, 20)
path_end_date_120 < retreat_exchange_sessions(robustness_first_decision_date, 20)
```

这样 validation outcome window 不与 train selection outcome 或 robustness design outcome 重叠。
Purge/embargo 后样本不足只能触发 stress underpowered，不能放宽边界。

Forward end 必须由 qfq coverage 和 entry-specific 120-session completion 推导。覆盖审计至少输出：

```text
topn_universe_max_date
benchmark_max_date
qfq_min_max_date_by_used_instrument
train_spent_outcome_path_end
spent_robustness_outcome_path_end
effective_forward_start
earliest_forward_decision_date
earliest_single_row_label_complete_date
minimum_additional_exchange_sessions_for_first_label_complete
earliest_evaluable_forward_month
forward_preoutcome_evaluability_gate
pipeline_dry_run_only
validation_effective_min_max_decision_date
validation_max_possible_decision_month_n
validation_support_floor_feasibility_gate
purge_embargo_overlap_row_n
max_label_complete_decision_date
forward_raw_trigger_n / canonical_n / cooldown_n / fill_feasible_n
forward_path_complete_120_n / B2_candidate_n / instrument_n / decision_month_n
forward_support_gate
```

`purge_embargo_overlap_row_n` 必须为 0；否则 data coverage/outcome overlap gate fail closed。
按 frozen CSI300 exchange calendar，当前固定 validation 有效窗口应为
`2022-08-03 .. 2023-06-06`，最多 11 个 decision months。实现必须重算而不是盲信该 expected value；
若重算上限与 config 不同，或 `decision_month_n_min` 高于重算上限，config contract fail closed。

Forward evaluability 必须在任何 forward outcome value read 前判定：

```text
forward_preoutcome_evaluability_gate =
    path_complete_candidate_n >= 300
    and instrument_n >= 50
    and instrument_month_n >= 200
    and decision_month_n >= 6
    and path_complete_120_rate >= 0.95
    and min_same_day_rank_cross_section_n >= 30
    and R2_effective_exposure_n >= 200
    and R2_effective_exposure_ratio >= 0.60
```

该 gate 故意不含 outcome-dependent `right_tail_event_50_n`。若不通过：

```text
pipeline_dry_run_only = true
forward_outcome_read = false
earliest_evaluable_forward_month = first observed month where this preoutcome gate passes,
                                   else not_yet_observed
forward_evaluability_state = not_yet_observed_no_post_embargo_path
                            | preoutcome_support_underpowered
                            | outcome_read_authorized
decision_state = 19B3_forward_oos_underpowered_not_pass
```

报告必须写明：在 `earliest_evaluable_forward_month` 被实际观察到之前，19B3 只验证管道、
lineage 和 leakage boundary，不产生 R2/R3 科学结论。不得用日历外推日期冒充 observed evaluability。
若 calendar 尚未覆盖 future boundary，所有未来日期字段写 `not_yet_observed`，但
`minimum_additional_exchange_sessions_for_first_label_complete` 必须按 session count 机械计算。
在 requirement 起草快照中，spent path end 与数据末日同为 2026-05-29，因此首个 post-embargo
decision 的 120-session label 至少还需 141 个新增 exchange sessions；该数值是 coverage diagnostic，
不是“2027 年某月”的承诺日期，运行时必须重算。

Support 口径冻结为：

```text
instrument_month_n = count_distinct(instrument, decision_month)
path_complete_120_rate = path_complete_120_n / fill_feasible_B2_candidate_n
right_tail_event_50_n = unweighted R0 count(MFE_120 >= 0.50)

forward_sample_support_gate =
    candidate_n >= 300
    and instrument_n >= 50
    and instrument_month_n >= 200
    and decision_month_n >= 6
    and right_tail_event_50_n >= 50
    and path_complete_120_rate >= 0.95
    and min_same_day_rank_cross_section_n >= 30
    and R2_effective_exposure_n >= 200
    and R2_effective_exposure_ratio >= 0.60
```

`fill_feasible_B2_candidate_n = 0` 时 path-complete rate unsupported，不得约定为 1。
Freeze candidate manifest 必须保留 cooldown/fill-feasible 后的全部 B2 rows，并用
`forward_120_complete` 区分；metric `candidate_n` 和 primary denominator 只统计
`forward_120_complete = true`。不得通过只落盘 path-complete rows 把 completion rate 机械变成 1。

若 support 不足，停止且不读 validation：

```text
decision_state = 19B3_forward_oos_underpowered_not_pass
next_allowed_stage = finalize
validation_outcome_read = false
```

## 5. B2 membership 和 denominator

### 5.1 B2 rule

```text
stock_vs_market_return_20d_asof_decision_date >= 0.15
return_60d_cross_section_rank_pct_asof_decision_date >= 0.90
close_to_ema60_asof_decision_date >= 0.00
market_regime_filter = all
```

Feature rebuild 必须在每只股票完整 qfq daily 序列上、以 decision-date close 截止：

```text
return_20d = close[t] / close[t-20] - 1
return_60d = close[t] / close[t-60] - 1
benchmark_return_20d = csi300_close[t] / csi300_close[t-20] - 1
stock_vs_market_return_20d = return_20d - benchmark_return_20d
ema60 = ewm(close, span=60, adjust=false, min_periods=60)
close_to_ema60 = close[t] / ema60[t] - 1
daily_return = close.pct_change()
match_vol60 = rolling_std(daily_return, 60, min_periods=60, ddof=1)
true_range = max(abs(high-low), abs(high-prev_close), abs(low-prev_close))
atr_20_pct = rolling_mean(true_range, 20, min_periods=20) / close[t]
```

Benchmark 固定 `index_alias = csi300`。禁止在只含 candidate/date 的稀疏 panel 上先做
`pct_change()` 或 rolling；这会把非相邻交易日误当相邻 session。

Cross-sectional rank 使用同日 executable universe、average rank、ascending、pct=True；最小有效横截面 30。
`board_bucket` 必须来自 PIT topn universe 的同一 `usable_trade_date × instrument` row；
不得用当前证券板块回填。缺失 board bucket 统一写 `UNKNOWN`，并在 placebo strata audit 披露，
不得按 outcome 分配 bucket。

### 5.2 Entry / cooldown / denominator

```text
decision_time <= decision_date close
entry_date = next executable open after decision_date
entry_price = qfq-compatible next executable open
cooldown = 10 trading sessions per instrument

primary_enrichment_denominator =
    B2 candidate
    ∩ canonical event
    ∩ cooldown eligible
    ∩ fill feasible
    ∩ entry anchor available
    ∩ 120-session path complete
```

稳定主键：

```text
candidate_id = sha256(instrument | decision_date | entry_date | family_id | grid_cell_id)
row_key = candidate_id
```

同一输入重跑必须得到相同 `candidate_id`、row ordering 和 cooldown survivors。

暂停、不可成交涨跌停、无有效 open 或缺失 path 的 row 不得进入 primary denominator。
Execution/fill/censoring 必须逐字段继承并 hash 校验 19A 的
`entry_execution_convention_audit.csv`、`entry_fill_feasibility_audit.csv` 和
`censoring_treatment_freeze.csv`；不得因 forward 数据新增而放宽规则。

Eligible-universe comparator 使用相同 decision-date、entry、fill、cooldown 和 path-complete 规则，
但不施加 B2 membership；日期只取 R0 B2 primary sample 出现的 decision dates。
它只用于 exposure/absolute burden reference，不产生 residual-alpha claim。
Eligible cooldown 对每个 instrument 在这些 decision dates 上按日期升序独立运行：保留首个
fill-feasible row，后续 row 仅在距上一个 retained eligible row 至少 10 个 exchange sessions 时保留；
不得沿用 B2 candidate 的 cooldown survivor flag。

为避免 calendar composition 改变 positive-exposure ratio，每个 arm 的 eligible comparator 必须
按该 arm 的当日 gross exposure 做 calendar matching：

```text
W_arm,d = sum(candidate arm weight on decision_date d)
N_eligible,d = eligible comparator row count on d
eligible_row_weight_arm,i,d = W_arm,d / N_eligible,d
```

若某日 `W_arm,d > 0` 且 `N_eligible,d = 0`，该 arm comparator gate fail closed。
不得让 universe row count 较多的日期机械获得更高 comparator 权重，也不得按 outcome 匹配。

同时输出非 gate 的 legacy bridge：

```text
p_eligible_50_unweighted_same_dates =
    mean(eligible_right_tail_event_50 on the same frozen eligible rows)

positive_exposure_ratio_50_legacy_bridge =
    p_candidate_50_after / p_eligible_50_unweighted_same_dates
positive_exposure_ratio_denominator_bridge_delta =
    positive_exposure_ratio_50_primary_arm_calendar_matched
    - positive_exposure_ratio_50_legacy_bridge
```

Primary `>= 1.20` gate 只使用 arm-calendar-matched ratio。两套 ratio 必须并列输出，且报告必须
把差异归因于 denominator change，不得归因于 B2/R2 exposure 改善。

### 5.3 Pre-outcome 禁止字段

Candidate/weight manifest 和 preoutcome cache 禁止：

```text
forward_mfe_* / forward_mae_* / forward_return_* / forward_big_winner_*
MFE_* / MAE_* / right_tail_event_* / left_tail_event_*
right_clean / left_bad / both / neither / outcome_group
```

## 6. Arm contract

### 6.1 Arm roles

```text
R0_S0_UNTRIMMED:
    role = baseline
    promotion_eligible = false
    weight = 1.0

R1_ATR20_TOP10_TRIM:
    role = mild_static_comparator
    promotion_eligible = false

R2_VOL60_TOP30_TRIM:
    role = only_primary_candidate_and_simple_incumbent
    promotion_eligible = true

R3_CONTINUOUS_VOL_BUDGET:
    role = smooth_budget_diagnostic_challenger
    promotion_eligible = false

P0_R2_SAME_DAY_RANDOM_TRIM:
    role = R2_same-day_same-budget_placebo
    promotion_eligible = false
```

R1/R3/P0 不得救活 R2 failure。`N_primary_arm = 1`，不允许看到 outcome 后把 comparator
改名为 primary。

### 6.2 Rank 和 hard-trim construction

先在同一 decision date 的 executable universe 计算：

```text
q_atr20 = rank_pct(atr_20_pct_asof_decision_date)
q_vol60 = rank_pct(match_vol60)
```

随后在当前 stage 的 B2 primary candidate rows 上按 pre-outcome score 计算 split-local threshold：

```text
R1 remove if q_atr20 >= candidate q_atr20 p90
R2 remove if q_vol60 >= candidate q_vol60 p70
```

Quantile 使用 pandas linear quantile；边界相等全部 remove，因此实际 removal rate 可略高于目标。

### 6.3 Continuous volatility budget

对每个 decision date，在完整 executable eligible universe 上计算：

```text
median_vol60_asof_t0 = median(match_vol60 among nonmissing eligible rows)
raw_weight_i = median_vol60_asof_t0 / max(match_vol60_i, 1e-12)
R3_weight_i = clip(raw_weight_i, 0.25, 1.00)
```

规则：

```text
不在 B2 rows 内计算 median
不使用 outcome-conditioned median
不把 unused weight 重新分配给其他 row
不把 total weight rescale 回 R0 gross exposure
1 - weight 解释为未分配/cash exposure，仅用于 diagnostic mass accounting
同日多个 B2 candidate 各自从 R0 unit weight 独立缩放，不做 candidate 间归一化或竞争分配
同日 gross exposure = sum(candidate weights)，不施加 portfolio gross cap
```

所有 arm 的 `cash_weight_i = 1.0 - final_weight_i`；该字段只用于 exposure accounting，
不产生 cash return，也不进入 MFE/MAE 分子。

任一 B2 primary row 的 `match_vol60` 非有限/小于 0，或当日 eligible median 非有限或
`<= epsilon` 时，feature/weight gate fail closed。

### 6.4 Same-budget placebo

P0 在每次 permutation 中保留 R2 binary weight multiset，只打乱 row assignment：

```text
primary strata = decision_date × board_bucket
if stratum_n < 2: fallback to decision_date
if fallback_n < 2: keep unchanged and disclose
permutation_n = 2000
seed = 20260711
```

Fallback partition 必须无重叠：同日 `board_bucket` 样本数至少 2 的 rows 只在本 board 内置换；
所有 singleton-board rows 汇总成该日唯一 fallback pool 后置换；fallback pool 仍不足 2 才保持不变。
同一 row 在一次 replication 中只能属于一个 permutation pool。
RNG 顺序固定为：replication_id 升序；pool 按 `decision_date, pool_type, board_bucket` 升序；
pool 内 row 按 `candidate_id` 升序，然后调用一次 `Generator.permutation`。Assignment hash 使用
`replication_id|candidate_id|source_candidate_id|assigned_weight` 的稳定排序 UTF-8 CSV bytes。

每次 permutation 必须逐 decision date 满足：

```text
sum(P0_weight on date d) = sum(R2_weight on date d)
multiset(P0_weight on date d) = multiset(R2_weight on date d)
```

因此 P0 只能破坏同日 candidate-level vol ordering，不得改变每日 gross/cash budget。
所有 replication assignment 必须在 forward outcome read 前生成；每个 replication 保存
`assignment_hash`，forward 重建 assignment 后必须先验 hash 再计算 placebo outcome。

```text
placebo_p_value =
    (1 + count(placebo_ES_improvement_vs_R0 >= observed_R2_ES_improvement_vs_R0))
    / (1 + permutation_n)
```

## 7. Label 和 weighted metric 定义

### 7.1 Readout-only labels

Labels 从 entry anchor 重建，只能在 manifest freeze 后 join：

```text
MFE_120 = max(qfq high[entry_pos : entry_pos + 119]) / entry_price - 1
MAE_20  = min(qfq low [entry_pos : entry_pos + 19 ]) / entry_price - 1

right_tail_event_50 = MFE_120 >= 0.50
left_tail_event_10  = MAE_20 <= -0.10
left_tail_event_20  = MAE_20 <= -0.20
left_tail_event_30  = MAE_20 <= -0.30
loss20 = max(0, -MAE_20)
```

### 7.2 Weighted probability

```text
weighted_probability(y, arm) = sum(weight_arm_i * y_i) / sum(weight_arm_i)

p_left_tail_20_relative_reduction_arm_vs_R0 =
    (weighted_p_left_tail_20_R0 - weighted_p_left_tail_20_arm)
    / weighted_p_left_tail_20_R0
```

若 `sum(weight) <= 0` 或 R0 left-tail denominator 为 0，该 arm 的相关 metric unsupported，
不得 smoothing 后通过。

### 7.3 Weighted ES10

`left_tail_ES10` 必须使用精确 weighted tail mass：

```text
1. sort by loss20 descending, then row_key ascending
2. target_tail_weight = 0.10 * sum(weight)
3. accumulate from largest loss downward
4. use fractional boundary-row weight so consumed weight equals target_tail_weight
5. ES10 = sum(consumed_weight_i * loss20_i) / target_tail_weight
```

禁止简单纳入 quantile threshold 上全部 ties。ES 越低越好：

```text
ES10_improvement_R2_vs_R0 = ES10_R0 - ES10_R2
ES10_improvement_R2_vs_R1 = ES10_R1 - ES10_R2
ES10_improvement_R3_vs_R0 = ES10_R0 - ES10_R3  # diagnostic only
ES10_improvement_R3_vs_R2 = ES10_R2 - ES10_R3  # diagnostic only
```

### 7.4 Weighted MAE quantile

`MAE_20_p10`：按 MAE 从小到大、row_key tie-break 排序，累计 weight 首次达到总 weight 10%
时的 MAE value。MAE 越高越好。

```text
MAE_p10_improvement_R2_vs_R0 = MAE_p10_R2 - MAE_p10_R0
MAE_p10_improvement_R2_vs_R1 = MAE_p10_R2 - MAE_p10_R1
```

### 7.5 Right-tail budget

```text
p_candidate_50_after = sum(weight * right_tail_event_50) / sum(weight)
p_eligible_50_arm_matched =
    sum(eligible_row_weight_arm * eligible_right_tail_event_50)
    / sum(eligible_row_weight_arm)
positive_exposure_ratio_50_primary_arm_calendar_matched =
    p_candidate_50_after / p_eligible_50_arm_matched

p_eligible_50_unweighted_same_dates = mean(eligible_right_tail_event_50)
positive_exposure_ratio_50_legacy_bridge =
    p_candidate_50_after / p_eligible_50_unweighted_same_dates

right_tail_event_50_capture_retention =
    sum(weight * right_tail_event_50) / sum(R0_weight * right_tail_event_50)

top_tail_payoff_i = max(MFE_120 - 0.50, 0)
top_tail_payoff_contribution_retention =
    sum(weight * top_tail_payoff_i) / sum(R0_weight * top_tail_payoff_i)
```

若 denominator 为 0，必须标记 unsupported，不得 smoothing 后通过。

### 7.6 Effective exposure 和 absolute burden

```text
effective_exposure_n = (sum(weight) ** 2) / sum(weight ** 2)
effective_exposure_ratio = effective_exposure_n / R0_candidate_n

mae_abs_worsening_vs_eligible =
    arm_calendar_matched_eligible_MAE_20_p10 - arm_MAE_20_p10
```

`mae_abs_worsening_vs_eligible <= 0.02` 才通过 absolute burden gate。该 gate 只区分
“budget supported”与“reduction supported but burden high”，不否定相对 reduction 的存在。

## 8. Uncertainty、calendar stability 和 concentration

### 8.1 Paired cluster bootstrap

```text
cluster_key = instrument
resample_n = 2000
seed = 20260710
CI = percentile 95%
CI_low = linear_quantile(bootstrap_metric, 0.025)
CI_high = linear_quantile(bootstrap_metric, 0.975)
```

同一 sample 必须同时计算 R0/R1/R2/R3，保留 paired delta。Cluster 被重复抽样时必须通过 replicate id
复制全部 rows，不能 concat 后去重。
Bootstrap cluster universe 是 frozen candidate 与 eligible comparator panels 的 instrument union；
某 instrument 被抽中时，其 candidate/eligible rows 必须带同一 replicate id 一起复制。
每次 replicate 重新计算 arm date gross、eligible calendar weights 和 exposure ratio。

Required bootstrap metrics：

```text
ES10_improvement_R3_vs_R0
ES10_improvement_R3_vs_R2
ES10_improvement_R1_vs_R0
ES10_improvement_R2_vs_R0
ES10_improvement_R2_vs_R1
MAE_p10_improvement_R3_vs_R0
MAE_p10_improvement_R1_vs_R0
MAE_p10_improvement_R2_vs_R0
MAE_p10_improvement_R2_vs_R1
p_left_tail_20_relative_reduction_R3_vs_R0
p_left_tail_20_relative_reduction_R1_vs_R0
p_left_tail_20_relative_reduction_R2_vs_R0
positive_exposure_ratio_50_primary_arm_calendar_matched_R3
positive_exposure_ratio_50_primary_arm_calendar_matched_R1
positive_exposure_ratio_50_primary_arm_calendar_matched_R2
right_tail_capture_retention_R3
right_tail_capture_retention_R1
right_tail_capture_retention_R2
```

### 8.2 Calendar direction stability

对每个 decision month 做 leave-one-month-out：

```text
direction_pass = ES10_improvement_R2_vs_R0 > 0
                 and MAE_p10_improvement_R2_vs_R0 > 0
calendar_direction_stable_rate = pass_month_n / evaluable_month_n
```

最少 6 个 evaluable months，且 stable rate >= 0.80。

### 8.3 Concentration

必须输出：

```text
max_instrument_weight_share
max_instrument_right_tail_weight_share
max_instrument_month_weight_share
max_decision_month_weight_share
top1/top3 instrument removed sensitivity
```

普通 share 的分母为 R2 全部 `sum(weight)`；right-tail share 的分母为
`sum(weight * right_tail_event_50)`。Instrument-month key 固定为
`instrument × decision_month`。分母为 0 时 concentration gate unsupported。

Top1/top3 removal 后，R2 必须仍满足：

```text
ES10_improvement_vs_R0 > 0
positive_exposure_ratio_50_primary_arm_calendar_matched >= 1.20
right_tail_capture_retention >= 0.60
```

Top1/top3 按 R2 `sum(weight)` 的 instrument share 降序、instrument 升序 tie-break 定义；
不得按 outcome contribution 选择要移除的 instrument。
Sensitivity 重算时必须从 R0、R2 和 eligible comparator 同时移除相同 instrument，
不得只削弱某一个 arm。

```text
concentration_gate =
    max_instrument_weight_share <= 0.02
    and max_instrument_right_tail_weight_share <= 0.02
    and max_instrument_month_weight_share <= 0.02
    and max_decision_month_weight_share <= 0.20
    and top1 removal sensitivity passes
    and top3 removal sensitivity passes
```

## 9. Forward gates

### 9.1 Gate 列表

```text
config_contract_gate
input_artifact_gate
upstream_contract_gate
human_restart_lineage_gate
spent_design_arm_role_gate
stage_lock_gate
outcome_access_gate
data_coverage_gate
purge_embargo_overlap_gate
validation_support_floor_feasibility_gate
forward_preoutcome_evaluability_gate
forward_sample_support_gate
B2_membership_gate
entry_fill_gate
cooldown_gate
path_complete_gate
feature_pit_gate
arm_registry_gate
arm_weight_recompute_gate
search_accounting_gate
left_tail_metric_gate
bootstrap_gate
placebo_gate
right_tail_budget_gate
effective_exposure_gate
calendar_stability_gate
concentration_gate
absolute_left_tail_burden_gate
validation_stress_boundary_gate
policy_authorization_gate
output_contract_gate
```

### 9.2 R2 primary reduction gate

```text
R2_primary_left_tail_reduction_gate =
    ES10_improvement_R2_vs_R0 > 0
    and bootstrap_ES10_improvement_R2_vs_R0_CI_low > 0
    and MAE_p10_improvement_R2_vs_R0 >= 0.03
    and bootstrap_MAE_p10_improvement_R2_vs_R0_CI_low > 0
    and p_left_tail_20_relative_reduction_R2_vs_R0 >= 0.30
```

### 9.3 Incremental frontier gate

```text
R2_incremental_frontier_gate =
    ES10_improvement_R2_vs_R1 >= 0.01
    and bootstrap_ES10_improvement_R2_vs_R1_CI_low > 0
    and R2_MAE_20_p10 >= R1_MAE_20_p10
    and placebo_p_value <= 0.05
```

R1/R3 不得替代 failed R2。

### 9.4 Right-tail budget gate

```text
right_tail_budget_gate =
    positive_exposure_ratio_50_primary_arm_calendar_matched_R2 >= 1.20
    and right_tail_event_50_capture_retention_R2 >= 0.60
```

### 9.5 Forward provisional states

```text
If critical contract / input / stage / outcome boundary fails:
    corresponding blocked state

Else if forward preoutcome evaluability fails:
    19B3_forward_oos_underpowered_not_pass
    pipeline_dry_run_only = true
    forward_outcome_read = false
    next_allowed_stage = finalize

Else if forward sample support fails:
    19B3_forward_oos_underpowered_not_pass
    next_allowed_stage = finalize

Else if R2 primary reduction or incremental frontier gate fails:
    19B3_forward_no_incremental_left_tail_improvement
    next_allowed_stage = finalize

Else if right_tail_budget_gate fails:
    19B3_forward_right_tail_budget_failed
    next_allowed_stage = finalize

Else if effective exposure / calendar / concentration gate fails:
    19B3_forward_support_or_concentration_blocked
    next_allowed_stage = finalize

Else if absolute_left_tail_burden_gate fails:
    19B3_forward_left_tail_reduction_supported_but_absolute_burden_high
    next_allowed_stage = validation-stress

Else:
    19B3_forward_positive_exposure_left_tail_budget_supported
    next_allowed_stage = validation-stress
```

## 10. Validation stress gate

Validation stress 对完全相同的 arm registry、R2 p70 hard-trim rule、R3 diagnostic formula 和
metric definitions 只做
veto/downgrade，不得重新选择 arm。Section 1.1 的 validation floors 是 outcome read 前冻结的
directional veto thresholds，不是 forward effect-size support thresholds；stress pass 不能贡献 support。
R1/R2 可以按 validation preoutcome 分布重算 frozen p90/p70 数值，R3 可以按当日 eligible
universe 重算 median；这些是预注册公式求值，不是调参。Percentile、clip、epsilon、rank scope、
cash treatment 和 gate 一律不变。

Stress sample support 使用与 forward 相同的 candidate/instrument/right-tail/effective-n floors；
`decision_month_n_min = 6`。该 floor 不超过 Section 4 固定 validation 有效窗口可达到的 11 个月上限。
Underpowered 必须输出 `underpowered_not_pass`。

```text
validation_stress_gate =
    positive_exposure_ratio_50_primary_arm_calendar_matched_R2 >= 1.00
    and right_tail_capture_retention_R2 >= 0.60
    and ES10_improvement_R2_vs_R0 >= 0.00
    and MAE_p10_improvement_R2_vs_R0 >= 0.00
    and p_left_tail_20_relative_reduction_R2_vs_R0 >= 0.00
```

Stress pass 只表示 `no_downgrade`，不得写 `validation_supported`。

## 11. Final decision states

`finalize` 按以下顺序机械聚合：

```text
19B3_validation_stress_unauthorized_access_blocked
    if validation was read without forward authorization

19B3_validation_preoutcome_boundary_blocked
    if validation outcome was read before a valid immutable validation preoutcome bundle was sealed

19B3_contract_or_lineage_blocked
    if any critical contract/lineage/outcome boundary gate fails

19B3_forward_oos_underpowered_not_pass
    if forward_state = 19B3_forward_oos_underpowered_not_pass

19B3_no_incremental_left_tail_improvement
    if forward_state = 19B3_forward_no_incremental_left_tail_improvement

19B3_right_tail_budget_failed
    if forward_state = 19B3_forward_right_tail_budget_failed

19B3_support_or_concentration_blocked
    if forward_state = 19B3_forward_support_or_concentration_blocked

19B3_validation_stress_incomplete_blocked
    if forward authorized validation-stress but no valid immutable stress bundle exists

19B3_validation_stress_underpowered_not_pass
    if authorized stress is underpowered

19B3_validation_stress_failed_diagnostic
    if authorized stress was evaluated and stress gate = fail

19B3_left_tail_reduction_supported_but_absolute_burden_high
    if forward_state = 19B3_forward_left_tail_reduction_supported_but_absolute_burden_high
    and validation_stress_gate = pass

19B3_positive_exposure_left_tail_budget_supported
    if forward_state = 19B3_forward_positive_exposure_left_tail_budget_supported
    and validation_stress_gate = pass
```

```text
If final state in {
    19B3_positive_exposure_left_tail_budget_supported,
    19B3_left_tail_reduction_supported_but_absolute_burden_high
}:
    next_allowed_requirement = requirement_19b4_b2_path_aware_left_tail_containment.md
Else:
    next_allowed_requirement = none
```

所有状态的 policy/replay/deployment authorization flags 必须为 false，包括：

```text
model_training / entry / exit / holding / portfolio_backtest
model_deployment / production_signal / live_trading
19C_replay / EP20_policy_preflight
```

## 12. 输出合同

实现入口与默认路径：

```text
runner_file = src/run_19b3_b2_positive_exposure_left_tail_budget_frontier.py
config_file = configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml
test_file = tests/test_19b3_b2_positive_exposure_left_tail_budget_frontier.py
output_root = outputs/19B3_b2_positive_exposure_left_tail_budget_frontier
```

所有 CSV 必须使用稳定列顺序和稳定排序；所有浮点输出至少保留 10 位有效数字；
缺失值使用空字段，不得用隐式 `0`。`freeze`、`forward`、`validation-stress` 只能写入各自
子目录；`finalize` 只能写 Section 12.4 的 root-level final artifacts。任何 stage 都不得覆盖
前一 stage 已经进入 hash bundle 的 artifact。

### 12.1 Freeze artifacts

`freeze` 必须输出：

```text
freeze/resolved_config.yaml
freeze/human_restart_authorization.json
freeze/contract_freeze_19b3.json
freeze/source_artifact_hash_audit.csv
freeze/input_artifact_audit.csv
freeze/upstream_contract_audit.csv
freeze/spent_design_arm_role_audit.csv
freeze/data_coverage_and_forward_support_audit.csv
freeze/search_accounting_audit.csv
freeze/forward_candidate_preoutcome_manifest.csv
freeze/forward_eligible_preoutcome_manifest.csv
freeze/forward_arm_weight_manifest.csv
freeze/p0_permutation_assignment_hashes.csv
freeze/b2_arm_registry.csv
freeze/outcome_access_audit.csv
freeze/freeze_manifest_19b3.json
freeze/freeze_output_hashes_19b3.json
```

`spent_design_arm_role_audit.csv` 一行对应 R0/R1/R2/R3，至少包含：

```text
split
arm_id
arm_role
promotion_eligible
candidate_n
threshold_value
retained_n
weight_sum
right_tail_capture_retention
weighted_ES10_MAE20
weighted_MAE20_p10
weighted_p_left_tail_20
ES10_improvement_vs_R0
ES10_improvement_vs_R1
ES10_improvement_vs_R2
expected_value_gate
source_artifact_hashes
design_only_no_support_claim
spent_design_arm_role_gate
```

报告只能称其为 role-selection/design audit，不得与 forward OOS readout 合并。

`forward_candidate_preoutcome_manifest.csv` 一行对应一个 forward B2 candidate，至少包含：

```text
run_id
candidate_id
instrument
decision_date
decision_month
board_bucket
family_id
grid_cell_id
membership_rule_hash
eligible_universe_row_count
b2_candidate_row_count
candidate_denominator_id
return_20d_stock
return_20d_benchmark
stock_vs_market_20d
return_60d
return_60d_rank_pct
close_to_ema60
vol60
atr20
q_vol60
q_atr20
median_vol60_asof_t0
forward_120_complete
preoutcome_feature_hash
```

`forward_eligible_preoutcome_manifest.csv` 一行对应一个 calendar-matched eligible-universe
comparator row，至少包含 `eligible_candidate_id`、instrument、decision_date、entry_date、
board_bucket、fill/cooldown/path-complete flags、`N_eligible,d` 和 preoutcome hash。

该 manifest 禁止出现 `MFE`、`MAE`、forward return、left-tail flag、right-tail flag、
outcome group、arm decision 或 validation metric。

`forward_arm_weight_manifest.csv` 一行对应 `candidate_id × arm_id`，其中 arm 只允许
R0/R1/R2/R3；P0 只在 registry 和 permutation assignment hash manifest 中出现。Columns 至少包含：

```text
candidate_id
arm_id
arm_role
is_retained
raw_weight
final_weight
cash_weight
weight_formula_id
threshold_source_scope
threshold_value
preoutcome_manifest_hash
```

R0/R1/R2 的 `final_weight` 只能为 0 或 1；R3 可以连续取值。P0 不存在单一
`final_weight`，不得在主 manifest 中伪造一个 replication-agnostic value。

`p0_permutation_assignment_hashes.csv` 一行对应一个 replication，至少包含：

```text
replication_id
seed
rng
primary_strata
fallback_strata
candidate_n
assignment_hash
date_gross_invariance_gate
date_weight_multiset_invariance_gate
forward_candidate_manifest_hash
```

`b2_arm_registry.csv` 至少包含：

```text
arm_id
arm_role
promotion_eligible
formula
parameter_json
parameter_source
frozen_before_forward_outcome
right_tail_budget_ratio_floor
right_tail_capture_floor
preoutcome_assignment_hash_manifest_hash
```

### 12.2 Forward artifacts

`forward` 必须输出：

```text
forward/forward_outcome_panel.csv
forward/forward_eligible_outcome_panel.csv
forward/arm_tail_readout.csv
forward/arm_pairwise_readout.csv
forward/cluster_bootstrap_readout.csv
forward/leave_one_month_out_readout.csv
forward/placebo_null_readout.csv
forward/placebo_null_summary.json
forward/support_and_concentration_readout.csv
forward/forward_decision.json
forward/outcome_access_audit.csv
forward/forward_manifest.json
forward/forward_output_hashes.json
forward/figures/forward_left_tail_frontier.png
forward/figures/forward_exposure_capture_frontier.png
forward/figures/forward_bootstrap_improvement_distribution.png
forward/figures/forward_month_stability.png
```

若 `pipeline_dry_run_only = true`，outcome/readout CSV 仍须按冻结 schema 输出零行文件，
figures 输出带 `not_evaluable` 水印的空读图；`forward_decision.json` 和 manifest 必须完整，
且 outcome-access audit 证明 forward outcome read count = 0。

`forward_outcome_panel.csv` 一行对应一个 candidate，必须从 frozen candidate manifest 左连接，
且至少包含：

```text
candidate_id
instrument
decision_date
path_end_date_20
path_end_date_120
forward_120_complete
MFE_120
MAE_20
right_tail_50_flag
left_tail_10_flag
left_tail_20_flag
left_tail_30_flag
outcome_source_hash
freeze_preoutcome_manifest_hash
```

`forward_eligible_outcome_panel.csv` 必须从 frozen eligible manifest 左连接，并保存每个 arm 的
`eligible_row_weight`、MFE120、MAE20 和对应 path/source hash；不得在 outcome join 后改变
eligible membership 或 calendar weights。

`arm_tail_readout.csv` 一行对应 `sample_scope × arm_id`，arm 仅为 R0/R1/R2/R3；
P0 replication 只进入 placebo artifact。该表至少包含：

```text
sample_scope
arm_id
candidate_n_raw
candidate_n_retained
instrument_n
decision_month_n
weight_sum
weight_sq_sum
kish_effective_n
p_candidate_50_after
p_eligible_50_arm_matched
positive_exposure_ratio_50_primary_arm_calendar_matched
p_eligible_50_unweighted_same_dates
positive_exposure_ratio_50_legacy_bridge
positive_exposure_ratio_denominator_bridge_delta
right_tail_capture_retention
top_tail_payoff_contribution_retention
weighted_ES10_MAE20
weighted_MAE20_p10
weighted_p_left_tail_10
weighted_p_left_tail_20
weighted_p_left_tail_30
eligible_weighted_MAE20_p10_arm_matched
ES10_improvement_vs_R0
MAE_p10_improvement_vs_R0
p_left_tail_20_relative_reduction_vs_R0
absolute_left_tail_burden_gap_vs_eligible
support_gate
right_tail_budget_gate
```

`arm_pairwise_readout.csv` 必须固定比较：

```text
R1_vs_R0
R2_vs_R0
R2_vs_R1
R3_vs_R0
R3_vs_R2
```

至少包含 `ES10_improvement`、`MAE_p10_improvement`、
`p_left_tail_relative_reduction`、`positive_exposure_ratio_50_primary_arm_calendar_matched`、
`positive_exposure_ratio_50_legacy_bridge`、
`right_tail_capture_retention` 和 gate result。除 legacy bridge 只要求点估计外，其余 metrics
必须包含对应 bootstrap CI；legacy bridge 不得进入 gate。

`placebo_null_readout.csv` 必须保存每次 P0 replication 的 placebo-vs-R0 ES10 improvement，
使 Section 6 p-value 可逐行复算。Columns：

```text
replication_id
assignment_hash
assignment_hash_gate
placebo_ES10
placebo_ES10_improvement_vs_R0
R2_ES10_improvement_vs_R0
placebo_at_least_as_good_as_R2
primary_strata_n
fallback_strata_n
unchanged_strata_n
date_gross_invariance_gate
seed
```

同目录的 `placebo_null_summary.json` 必须输出：

```text
placebo_replication_n
observed_R2_vs_R0_ES10_improvement
null_mean
null_p95
one_sided_placebo_p_value
seed
bucket_fallback_count
```

`forward_decision.json` 至少包含：

```text
run_id
freeze_manifest_hash
primary_arm_id
spent_design_arm_role_gate
forward_candidate_n
forward_instrument_n
forward_decision_month_n
forward_kish_effective_n_R2
earliest_evaluable_forward_month
pipeline_dry_run_only
forward_evaluability_state
forward_preoutcome_evaluability_gate
validation_support_floor_feasibility_gate
support_gate
primary_left_tail_gate
incremental_frontier_gate
right_tail_budget_gate
absolute_left_tail_burden_gate
placebo_gate
forward_state
validation_stress_authorized
blocking_reasons
```

### 12.3 Validation stress artifacts

仅当 `forward_decision.json.validation_stress_authorized = true` 时，
`validation-stress` 才能输出：

```text
validation_stress/validation_candidate_preoutcome_manifest.csv
validation_stress/validation_eligible_preoutcome_manifest.csv
validation_stress/validation_arm_weight_manifest.csv
validation_stress/validation_preoutcome_freeze_manifest.json
validation_stress/validation_preoutcome_freeze_output_hashes.json
validation_stress/validation_outcome_panel.csv
validation_stress/validation_eligible_outcome_panel.csv
validation_stress/validation_arm_tail_readout.csv
validation_stress/validation_stress_decision.json
validation_stress/outcome_access_audit.csv
validation_stress/validation_stress_manifest.json
validation_stress/validation_stress_output_hashes.json
validation_stress/figures/validation_stress_directional_readout.png
```

`validation_arm_weight_manifest.csv` 只物化 R0/R1/R2/R3，schema 与 forward arm weight manifest
一致。P0 definition 仍必须保留在 frozen registry，但 validation directional veto 不重新运行
placebo randomization，且不得据此改变 forward placebo gate。
`validation_arm_tail_readout.csv` 必须复用 Section 12.2 arm-tail schema，包括 primary/legacy
positive-exposure denominator bridge；validation 不得切换 denominator。

Validation preoutcome bundle 必须只覆盖前三个 preoutcome CSV 和 resolved frozen arm registry hash。
Hash 规则与 Section 14 stage bundle 相同；manifest 必须记录 `sealed_at`，outcome audit 中第一条
validation outcome read 的 `accessed_at` 必须严格晚于 `sealed_at`。任一 preoutcome artifact 在
seal 后变化，必须输出 `19B3_validation_preoutcome_boundary_blocked`。

Validation 必须重放 frozen R2 candidate-p70 hard-trim rule、R3 diagnostic formula、clip、epsilon、
percentile parameters 和 Section 1.1 directional veto floors；不得重新估计 median
以外的自由参数，不得加入新 arm，不得改变 gate。`validation_stress_decision.json` 至少包含：

```text
forward_decision_hash
stress_access_authorized
frozen_arm_registry_hash
validation_preoutcome_freeze_manifest_hash
candidate_n
instrument_n
decision_month_n
kish_effective_n_R2
support_gate
directional_stress_gate
stress_state
downgrade_required
selection_or_tuning_performed
```

其中 `selection_or_tuning_performed` 必须恒为 false；否则 contract blocked。

### 12.4 Final artifacts

`finalize` 必须输出：

```text
entry_universe_19b3_decision.csv
outcome_access_audit.csv
19B3_b2_positive_exposure_left_tail_budget_frontier_report.md
19B3_handoff_contract.md
manifest_19b3_b2_positive_exposure_left_tail_budget_frontier.json
output_hashes_19b3_b2_positive_exposure_left_tail_budget_frontier.json
```

`entry_universe_19b3_decision.csv` 只能有一行，至少包含：

```text
run_id
created_at
requirement_file_hash
config_file_hash
freeze_manifest_hash
forward_manifest_hash
validation_stress_manifest_hash
validation_preoutcome_freeze_manifest_hash
contract_gate
lineage_gate
spent_design_arm_role_gate
outcome_access_gate
primary_arm_id
forward_preoutcome_evaluability_gate
earliest_evaluable_forward_month
pipeline_dry_run_only
forward_evaluability_state
forward_support_gate
forward_primary_left_tail_gate
forward_incremental_frontier_gate
forward_right_tail_budget_gate
forward_placebo_gate
forward_absolute_left_tail_burden_gate
validation_stress_authorized
validation_preoutcome_boundary_gate
validation_stress_gate
validation_stress_state
final_decision_state
blocking_reason
R2_positive_exposure_ratio_50_primary_arm_calendar_matched
R2_positive_exposure_ratio_50_legacy_bridge
R2_positive_exposure_ratio_denominator_bridge_delta
R2_right_tail_capture_retention
R2_weighted_ES10_MAE20
R2_weighted_MAE20_p10
R2_weighted_p_left_tail_20
R2_ES10_improvement_vs_R0
R2_ES10_improvement_vs_R1
R2_ES10_improvement_vs_R1_ci_low
R2_placebo_p_value
R3_diagnostic_right_tail_capture_retention
R3_diagnostic_ES10_improvement_vs_R2
R3_diagnostic_MAE_p10_improvement_vs_R2
next_allowed_requirement
model_training_authorized
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
19C_replay_authorized
EP20_policy_preflight_authorized
```

所有 authorization 字段必须为 false。

## 13. 报告与 handoff 合同

中文报告必须按以下顺序组织：

```text
1. Executive decision
2. Spent-design arm-role audit（明确 non-support）
3. Human restart 与 lineage
4. Outcome-access / evaluability boundary
5. Forward OOS support
6. R2 left-tail reduction frontier 与 R3 diagnostic comparison
7. Positive-exposure denominator bridge / right-tail budget
8. Placebo、bootstrap 与 month stability
9. Absolute burden comparison
10. Validation pressure test（若被授权）
11. Failure interpretation
12. Decision boundary 与 next step
```

Executive decision 必须并列报告 `R2 vs R0`、`R2 vs R1` 和 diagnostic `R3 vs R2`；
不得只报告 R2 vs R0，也不得让 R3 diagnostic 读数触发 promotion。

报告必须明确区分：

```text
selection evidence = forward_oos only
validation role = sealed pressure test with veto/downgrade only
validation thresholds = frozen directional veto floors, not forward support floors
validation pass != independent positive support
validation fail/underpowered cannot be repaired by retuning
```

报告中必须逐字包含：

```text
19B3 的目标是先压低 B2 左尾，在正 exposure 下允许牺牲部分右尾。
validation 是压力测试集，不是 arm 选择、调参或正面确认集。
R2 A_VOL60_top30 是唯一可晋级 primary arm；R3 continuous budget 只作 diagnostic challenger。
positive exposure ratio >= 1.20 只使用 arm-calendar-matched eligible denominator；legacy ratio 只作桥接。
forward preoutcome evaluability gate 通过前，19B3 只是 pipeline dry-run，不产生科学结论。
19B3 support 不等于可交易策略 support。
19C replay authorized = false。
EP20 policy preflight authorized = false。
```

`19B3_handoff_contract.md` 只在 Section 11 允许的两个 final state 下生成 actionable
19B4 handoff；其他状态只能记录 `next_allowed_requirement = none` 和失败原因。
Handoff 不得包含 validation 派生阈值，不得把 R1/R3 升格为 primary。

## 14. Manifest、hash 与 outcome-access 审计

最终 manifest 至少记录：

```text
run_id
created_at
requirement_file
requirement_file_hash
config_file
config_file_hash
runner_file_hash
human_restart_authorization_hash
source_artifact_hashes
freeze_bundle_hash
forward_bundle_hash
validation_preoutcome_freeze_bundle_hash
validation_stress_bundle_hash
stage_execution_order
stage_started_at
stage_completed_at
required_outputs
output_hashes
outcome_access_summary
primary_arm_id
forward_evaluability_state
decision_state
authorization_state
```

Hash 规则：

```text
each stage manifest.output_hashes excludes that manifest and its output_hashes file
each stage output_hashes includes that stage manifest
each stage output_hashes excludes itself
validation preoutcome freeze bundle follows the same stage hash rules and is immutable before outcome read
final manifest.output_hashes excludes final manifest and final output_hashes
final output_hashes includes final manifest and all required final artifacts
final output_hashes excludes itself
```

任一 upstream、freeze、forward 或 stress bundle hash 不匹配，必须 fail closed；不得静默重算
或覆盖原 bundle。

`outcome_access_audit.csv` 必须汇总所有 stage 的每次 outcome read：

```text
run_id
stage
accessed_at
dataset_role
split
date_min
date_max
artifact_path
artifact_sha256
columns_read
access_authorized
authorization_artifact
authorization_artifact_hash
purpose
selection_or_tuning_allowed
```

硬约束：

```text
freeze unspent forward/validation outcome read count = 0
freeze spent_robustness_design_only reads are allowed only for spent_design_arm_role_audit
forward split read before freeze hash = 0
validation read before forward authorization = 0
validation outcome read before validation preoutcome freeze seal = 0
validation selection_or_tuning_allowed = false
finalize raw outcome read count = 0
```

违反任何一项：

```text
outcome_access_gate = fail
final_decision_state = 19B3_contract_or_lineage_blocked
```

## 15. 实现与测试要求

测试至少覆盖：

```text
1. Human restart artifact 存在，且不接受 19B2 automated handoff。
2. B2 family/grid-cell/hash/rule 与 frozen contract 完全一致。
3. forward decision_date 严格大于 Section 4 effective boundary，且必然大于 2025-11-26。
4. forward/validation outcome windows 与已读 split 的 purge/embargo overlap 为 0。
5. 只纳入 120-session outcome path 完整的 forward rows。
6. 10-session instrument cooldown 与既有口径一致。
7. freeze stage 不读取任何 unspent forward/validation outcome；spent robustness outcome 只可进入 role audit。
8. candidate manifest 不含 forbidden outcome/decision columns。
9. R1/R2 threshold 使用本 sample 的 candidate pre-outcome rank，且不看 outcome。
10. R3 median_vol60 只使用同日完整 eligible universe，公式与 clip 可逐行复算。
11. R3 未将保留权重重新归一为 1；差额进入 cash_weight。
12. P0 只在同一 decision date 的 frozen bucket 内置换 R2 binary weight，逐日 gross/multiset 完全不变。
13. weighted ES10 fractional-mass 算法在边界权重处精确复算。
14. positive exposure、capture retention 与 contribution 的分母完全符合 Section 7。
15. Kish effective n、instrument/month support floor 和 underpowered state fail closed。
16. paired bootstrap 以 instrument 为 cluster，paired arms 使用相同 draw。
17. leave-one-month-out stability 与 concentration 指标可复算。
18. R2 primary gate 与 R2-vs-R1 incremental gate 均为必需条件；R3 不得触发 promotion。
19. 右尾 budget 可以容忍损失，但 ratio >= 1.20 且 capture >= 0.60。
20. validation 在 forward authorization 前不可读。
21. validation 只重放 frozen R2 hard-trim rule 和 R3 diagnostic formula；任何 retune/new arm 导致 blocked。
22. validation pass 只能 no_downgrade，不能提供 positive support。
23. validation fail/underpowered 按 Section 11 downgrade，不得回写 forward gate。
24. finalize 不读取 raw outcome，只读 immutable hashed bundles。
25. 所有 policy/replay/deployment authorization 恒为 false。
26. stage/final manifest 与 output hashes 双向一致。
27. 中文报告包含 Section 13 所有 boundary phrases。
28. eligible comparator membership 在 outcome join 前冻结，且 arm-level calendar weights 符合 Section 5。
29. validation decision-month floor 不超过固定 purge/embargo 窗口的可达上限。
30. validation outcome read 严格晚于 immutable validation preoutcome bundle seal。
31. P0 assignment hash 在 outcome read 前冻结，forward 重建后逐 replication 验证一致。
32. primary 与 legacy positive-exposure denominator/ratio 同时输出，且只有 primary ratio 进入 gate。
33. forward preoutcome evaluability 不通过时 outcome read count 为 0，且只能输出 dry-run underpowered state。
34. spent robustness role audit 按正式 universe-rank→candidate-p70 口径复算，并验证 R2 primary/R3 diagnostic。
```

推荐验收命令：

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b3_b2_positive_exposure_left_tail_budget_frontier.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml \
  --stage freeze

python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b3_b2_positive_exposure_left_tail_budget_frontier.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml \
  --stage forward

# 仅当 forward_decision.json 明确授权时运行：
python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b3_b2_positive_exposure_left_tail_budget_frontier.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml \
  --stage validation-stress

python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b3_b2_positive_exposure_left_tail_budget_frontier.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19b3_b2_positive_exposure_left_tail_budget_frontier.yaml \
  --stage finalize

python -m pytest topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19b3_b2_positive_exposure_left_tail_budget_frontier.py -q

git diff --check -- topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight
```

## 16. 失败解释与研究含义

不得把任一失败简化为 “B2 没有 alpha”。必须机械区分：

```text
1. forward preoutcome not evaluable / underpowered：当前新增数据不足以评价，只是 pipeline dry-run，
   不是 R2/R3 支持或证伪。
2. positive exposure ratio < 1.20：压左尾后已失去正 beta 目标，不值得用更低左尾交换。
3. capture retention < 0.60：右尾牺牲超过预注册预算。
4. R2 vs R0 有改善但 R2 vs R1 不增量：aggressive hard trim 没有提供足够额外左尾价值。
5. 点估计改善但 CI/稳定性失败：frontier 不稳定，不能晋级。
6. placebo 失败：改善可能只是同预算随机删除，而非 high-vol ordering。
7. absolute burden high：相对压左尾有效，但 B2 的绝对左尾仍不足以支持后续 policy work。
8. validation stress fail：forward support 被压力测试否决；不得在 validation 上重调。
9. validation stress underpowered：压力测试没有通过；不得把缺样本写成 no-downgrade。
10. outcome-access/lineage blocked：研究过程无效，所有数值仅供排错。
```

若最终支持，只能得出：在独立 forward OOS 上，冻结的 R2 A_VOL60_top30 hard trim 在保留
预注册正 exposure/right-tail budget 的条件下，相对 R0 和 R1 都降低了 B2 左尾，且未被
validation 压力测试否决。R3 只解释 smooth budget 与 hard trim 的 frontier 差异。
该结论仍不是 entry/exit/holding rule、portfolio backtest 或部署授权。
