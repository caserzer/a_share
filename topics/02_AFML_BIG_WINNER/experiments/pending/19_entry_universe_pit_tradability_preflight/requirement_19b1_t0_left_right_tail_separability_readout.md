# Requirement: 19B1 T0 左尾/右尾可区分性诊断读出

## 0. 不可协商范围

19B1 是 19B 之后的 diagnostic-only readout。它只回答一个问题：

```text
在 T0 / as-of-decision-date 已知信息上，19B 中暴露出来的左尾坏样本
和右尾好样本是否存在统计上明显、可复现、PIT 合法的差异？
```

19B1 不生成新 candidate family，不扩展 grid，不训练模型，不选择 entry rule，
不读取 validation outcome，不运行 19C replay，不输出 entry/exit/holding policy，
不运行组合回测，不输出 production signal，不授权 live trading。

19B1 可以产出：

```text
t0_left_right_tail_separable_diagnostic:
    在 19B 冻结 rows 上，部分 T0 特征对 left-tail false-positive 样本和
    right-tail winner 样本有统计可区分性。

t0_left_right_tail_not_separable_diagnostic:
    在 19B 冻结 rows 上，T0 特征没有形成足够稳定的左/右尾区分信号。
```

无论 19B1 结果如何，最高授权仍保持：

```text
max_ep19_terminal_state = 19_entry_universe_enrichment_only_diagnostic
19C replay authorized = false
EP20 policy preflight authorized = false
entry_policy_preflight_authorized = false
```

19B1 的正向结果只能作为下一轮 pre-registered B2 left-tail suppressor hypothesis
的设计依据；不得回写 19B0/19B 的结论，不得把 diagnostic feature separability
解释为 alpha、strategy edge 或 validation support。

## 1. 身份

```text
experiment_id = 19_entry_universe_pit_tradability_preflight
phase_id = 19B1
run_id = 19B1_t0_left_right_tail_separability_readout
requirement_file = requirement_19b1_t0_left_right_tail_separability_readout.md
config_file = configs/config_19b1_t0_left_right_tail_separability_readout.yaml
runner_file = src/run_19b1_t0_left_right_tail_separability_readout.py
test_file = tests/test_19b1_t0_left_right_tail_separability_readout.py
```

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

所有路径必须通过 config 或显式 path alias 解析。实现不得硬编码个人机器绝对路径。

### 1.1 Config contract

`config_file` 必须在运行前冻结以下字段。任何必需字段缺失、输入路径不存在、
或 whitelist / threshold / diagnostic constant 与本 requirement 不一致，必须 fail closed：

```text
input_paths:
    nineteen_b_output_root
    nineteen_b_decision
    nineteen_b_manifest
    nineteen_b_output_hashes
    nineteen_b_handoff_contract
    upstream_19a_contract_audit
    upstream_19b0_contract_audit
    robustness_candidate_row_manifest
    robustness_outcome_boundary_audit
    robustness_metric_readout
    false_positive_burden_readout
    mfe_mae_joint_readout
    simple_rule_feature_source_map
    matching_feature_source_map
    topn_executable_universe
    stock_qfq_dir
    benchmark_daily

output:
    output_root
    output_root_may_be_created = true
    output_root_parent_must_exist = true

primary_scope:
    family_id = B2_relative_strength_breakout
    grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
    split = robustness
    row_scope = candidate_primary_denominator

feature_contract:
    primary_t0_feature_whitelist = exact list in Section 6
    accounting_only_columns = exact list in Section 6
    exploratory_features_allowed = true

thresholds:
    right_tail_event_50 = 0.50
    left_tail_event_10 = -0.10
    left_tail_event_20 = -0.20

support:
    candidate_n_min = 300
    instrument_n_min = 30
    right_clean_n_min = 50
    left_bad_n_min = 50
    per_feature_left_bad_nonmissing_n_min = 50
    per_feature_right_clean_nonmissing_n_min = 50
    per_feature_max_group_missing_rate = 0.20
    per_feature_max_missing_rate_delta_abs = 0.10

bootstrap:
    bootstrap_resample_n = 2000
    bootstrap_seed = 20260709
    cluster_key = instrument_id
    leave_one_month_min_effective_fold_n_for_reporting = 6
    leave_one_month_out_required_for_stability_gate = false
    stability_bootstrap_direction_stable_rate_min = 0.70

diagnostic_probe:
    multivariate_enabled = false
    logistic_regularization_C = 1.0
    rank_bin_count = 10
    decision_stump_max_depth = 1
    crossfit_cluster_key in {instrument_id, instrument_month}
    random_seed = 20260709
```

`input_artifact_audit.csv` 只记录 `input_paths` 中的输入 artifact existence、row count、
observed hash 和 input gate；不得把 `output_root` 当作 input artifact 要求预先存在或
计算 hash。`config_contract_gate` 只要求 `output_root` 的 parent 存在且路径能按 alias
解析，runner 可以创建 `output_root`。`manifest_19b1...json` 必须记录 config hash、
requirement hash、primary whitelist hash 和所有 input artifact hashes。

## 2. 上游合同

19B1 必须先验证 19A、19B0、19B 的闭包。任何合同不通过时必须 fail closed。

### 2.1 19A / 19B0 必需事实

19B1 至少必须读取并校验 19B 已经校验过的 19A / 19B0 contract artifacts：

```text
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/upstream_19a_contract_audit.csv
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/upstream_19b0_contract_audit.csv
```

这些 audit 文件如果只有逐事实 `contract_gate`，19B1 必须派生聚合 gate：

```text
upstream_19a_contract_gate = pass iff all upstream_19a_contract_audit.contract_gate == pass
upstream_19b0_contract_gate = pass iff all upstream_19b0_contract_audit.contract_gate == pass
```

不得假设 audit 文件存在同名聚合字段。

必需事实：

```text
upstream_19a_contract_gate = pass
upstream_19b0_contract_gate = pass
validation_outcome_read = false
model_training_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

如果 19A/19B0 contract gate 不通过：

```text
decision_state = 19B1_upstream_contract_blocked
blocking_reason = upstream_19a_or_19b0_contract_failed
```

### 2.2 19B 必需事实

必须读取并校验：

```text
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/entry_universe_19b_decision.csv
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/manifest_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/output_hashes_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/19B_handoff_contract.md
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/robustness_candidate_row_manifest.csv
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/robustness_outcome_boundary_audit.csv
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/robustness_metric_readout.csv
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/false_positive_burden_readout.csv
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/mfe_mae_joint_readout.csv
```

必需事实：

```text
decision_state in {
    19B_false_positive_burden_blocked,
    19B_positive_exposure_persistent_enrichment_only_diagnostic,
    19B_baseline_quality_blocked_enrichment_only_diagnostic_possible
}
validation_outcome_read = false
N_family_brought_to_robustness = 2
N_tested_family_cell_pairs = 2
positive_exposure_robustness_gate = pass
matched_baseline_residual_gate = fail
max_ep19_terminal_state_if_no_residual_pass = 19_entry_universe_enrichment_only_diagnostic
robustness_candidate_manifest_gate = pass
outcome_boundary_gate = pass
robustness_candidate_manifest_frozen_before_label_readout = true
label_read_before_manifest_freeze = false
```

19B boundary facts 的聚合规则：

```text
outcome_boundary_gate = pass
    iff entry_universe_19b_decision.outcome_boundary_gate == pass
    and robustness_outcome_boundary_audit.boundary_gate == pass

robustness_candidate_manifest_frozen_before_label_readout = true
    iff robustness_outcome_boundary_audit.robustness_candidate_manifest_frozen_before_label_readout == true
    and all robustness_candidate_row_manifest.manifest_frozen_before_label_readout == true

label_read_before_manifest_freeze = false
    iff all robustness_candidate_row_manifest.label_read_before_manifest_freeze == false
```

本 requirement 主要目标是 B2：

```text
family_id = B2_relative_strength_breakout
grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
19B cell_decision_state = false_positive_burden_blocked
```

B5 可作为 negative-control / contrast diagnostic，但不得用 B5 结果修改 B2 结论。

19B 的 `next_allowed_requirement = none` 不阻断 19B1，因为 19B1 不是 replay、
policy preflight 或交易授权 requirement。19B1 必须在自己的 handoff 中继续保持
`next_allowed_requirement = none`，只能给出 non-executable research suggestion。

19B `output_hashes_19b...json` 的 key 可以是 extensionless artifact id，例如
`mfe_mae_joint_readout`。19B1 校验 hash 时必须使用以下映射，不得因为 key 无 `.csv`
后缀误判缺失：

```text
entry_universe_19b_decision -> entry_universe_19b_decision.csv
robustness_candidate_row_manifest -> robustness_candidate_row_manifest.csv
robustness_outcome_boundary_audit -> robustness_outcome_boundary_audit.csv
robustness_metric_readout -> robustness_metric_readout.csv
false_positive_burden_readout -> false_positive_burden_readout.csv
mfe_mae_joint_readout -> mfe_mae_joint_readout.csv
19B_handoff_contract -> 19B_handoff_contract.md
```

如果 19B 输出缺失、hash 不一致、validation outcome 已被读取、或 policy/trading
授权字段为 true：

```text
decision_state = 19B1_upstream_19b_contract_blocked
```

## 3. 研究问题

19B1 只回答四个问题。

```text
Q1. 在 B2 robustness candidate rows 内部，右尾事件和左尾事件是否只是同一批
    高波动样本的两个后验表现，还是存在统计上可区分的 outcome group？

Q2. 使用 T0 / as-of-decision-date 已知特征，是否能区分：
    left_bad = 左尾坏样本
    right_clean = 干净右尾样本
    both = 同时发生右尾和左尾
    neither = 二者都没有发生

Q3. 哪些 T0 特征的差异最大、方向最稳定、cluster bootstrap 后仍显著？
    这些特征是否更像左尾 suppressor proxy，而不是简单地删除全部右尾？

Q4. 这些差异是否足以支持下一轮 pre-registered left-tail suppressor ablation
    的 hypothesis，但仍不足以支持策略、replay 或 alpha claim？
```

19B1 不回答：

```text
1. 哪个过滤阈值应该上线。
2. 哪个新 rule/cell 应该进入 validation。
3. 加过滤器后的策略收益如何。
4. 是否可以运行 19C replay。
5. 是否可以训练模型或部署生产信号。
```

## 4. 允许和禁止工作

允许：

```text
1. 读取 19B 已冻结的 robustness candidate rows 和 `mfe_mae_joint_readout.csv`。
2. 用 19B 的 robustness outcome 定义 diagnostic group label。
3. 只为这些 frozen rows 重建或读取 T0/as-of-decision-date 特征。
4. 检查 left/right outcome group 在 T0 特征上的单变量差异、分布差异、
   稳健性、cluster bootstrap CI 和 multiple-testing-corrected p-value。
5. 做 diagnostic-only 的简单线性/逻辑 separability readout，但不得把它称为模型。
6. 输出机器可读 audit、中文报告、manifest、output hashes 和图表。
```

禁止：

```text
1. 不得读取 validation outcome。
2. 不得读取 validation MFE / MAE / winner / fast-fail label。
3. 不得使用 validation 或 19C replay 数据。
4. 不得新增 family/cell、扩展 grid、选择阈值或生成新 entry rule。
5. 不得训练 predictive model、hyperparameter tuner、policy model 或 portfolio model。
6. 不得用 outcome 优化任何可交易规则。
7. 不得把 T0 separability 解读为 residual alpha、independent alpha 或可交易 edge。
8. 不得授权 19C replay、EP20 policy preflight、entry/exit/holding policy、
   portfolio backtest、production signal 或 live trading。
9. 不得使用非 PIT feature、未来窗口、forward return、forward MFE/MAE 派生特征
   作为 T0 separability 输入。
```

## 5. 样本定义

### 5.1 Primary family

Primary readout 只使用：

```text
family_id = B2_relative_strength_breakout
grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
row_scope = candidate_primary_denominator
split = robustness
diagnostic_only_flag = false
```

Primary rows 必须从 `mfe_mae_joint_readout.csv` 中按上述条件过滤，并与
`robustness_candidate_row_manifest.csv` 做一对一合同校验：

```text
join_keys = family_id, grid_cell_id, row_key, instrument_id, decision_date
required_manifest_flags:
    candidate_flag = true
    primary_enrichment_denominator_flag = true
    manifest_frozen_before_label_readout = true
    label_read_before_manifest_freeze = false
```

禁止把以下 row_scope 混入 primary readout：

```text
eligible_universe_baseline_sample
matched_baseline_diagnostic_sample
matched_baseline_quality_pass_sample
```

任一 primary row 无法在 manifest 中一对一匹配、出现重复 join key、或 join 后
`candidate_n` 与 19B `robustness_metric_readout.csv` 中 B2 的
`candidate_n` 不一致，必须 fail closed：

```text
decision_state = 19B1_upstream_19b_contract_blocked
blocking_reason = primary_candidate_row_scope_or_join_contract_failed
```

`t0_feature_join_audit.csv` 必须记录：

```text
family_id
grid_cell_id
row_scope
split
expected_candidate_n_from_19b_metric
observed_candidate_n_from_mfe_mae_joint
observed_candidate_n_after_manifest_join
unique_join_key_n
duplicate_join_key_n
missing_in_candidate_manifest_n
extra_manifest_row_n
primary_enrichment_denominator_flag_false_n
manifest_frozen_before_label_readout_false_n
label_read_before_manifest_freeze_true_n
feature_matrix_row_n
feature_missing_any_primary_n
primary_row_join_gate
blocking_reason
```

B2 的 minimum support：

```text
candidate_n >= 300
instrument_n >= 30
right_clean_n >= 50
left_bad_n >= 50
```

不足时：

```text
decision_state = 19B1_sample_support_blocked
```

### 5.2 Diagnostic outcome groups

在 19B frozen candidate rows 上定义：

```text
right_tail_event_50 = MFE_120 >= +0.50
left_tail_event_10 = MAE_20 <= -0.10
left_tail_event_20 = MAE_20 <= -0.20

right_clean = right_tail_event_50 and not left_tail_event_10
left_bad = left_tail_event_10 and not right_tail_event_50
both = right_tail_event_50 and left_tail_event_10
neither = not right_tail_event_50 and not left_tail_event_10
```

Primary separability comparison：

```text
left_bad vs right_clean
```

Secondary comparisons：

```text
left_tail_event_10 vs not left_tail_event_10
right_tail_event_50 vs not right_tail_event_50
both vs right_clean
left_tail_event_20 vs not left_tail_event_20
```

这些 group label 可使用 19B robustness outcome 定义，但只能用于 diagnostic analysis；
不得用于选择交易规则。

## 6. T0 / as-of feature 白名单

19B1 只能使用在 decision date close 后、entry next open 前已经可知的字段。

Primary feature family 必须在运行前冻结在 config 中，且只能使用下列字段：

```text
return_5d_asof_decision_date
return_10d_asof_decision_date
return_20d_asof_decision_date
return_60d_asof_decision_date
stock_vs_market_return_20d_asof_decision_date
return_60d_cross_section_rank_pct_asof_decision_date
close_to_ema60_asof_decision_date
amount_ratio_20d_asof_decision_date
rolling_20d_money_mean_asof_decision_date
atr_20_pct_asof_decision_date
atr_20_pct_rank_asof_decision_date
intraday_range_pct_asof_decision_date
close_position_in_120d_range_asof_decision_date
market_regime_risk_on_asof_decision_date
market_drawdown_60d_asof_decision_date
match_market_cap
match_amount20
match_vol60
match_return20
```

下列字段只允许用于 split、cluster、accounting 或 stability，不得作为 separability
feature 参与 primary gate：

```text
decision_month
instrument_month
instrument_id
row_key
family_id
grid_cell_id
split
row_scope
```

任何未列入上述 primary whitelist 的 T0 字段只能进入 exploratory appendix，
不得进入 `primary_feature_family`、multiple-testing correction 或 positive
diagnostic gate。

禁止的特征：

```text
forward_mfe_*
forward_mae_*
forward_return_*
forward_big_winner_*
fast_fail_flag
false_repair_flag
MFE_120
MAE_20
right_tail_event_50
left_tail_event_10
left_tail_event_20
right_clean
left_bad
both
neither
任何 entry 后价格、成交、收益、路径、未来窗口统计
任何 validation outcome
任何 post-hoc 由 left/right label 反推出来的特征
```

### 6.1 Feature source alias contract

Primary whitelist 中所有字段必须落入以下 feature signal group。`t0_feature_source_audit.csv`
必须记录 `feature_signal_group`，positive diagnostic 中同一 group 最多只能贡献一个
通过特征。

```text
recent_return:
    return_5d_asof_decision_date
    return_10d_asof_decision_date
    return_20d_asof_decision_date
    return_60d_asof_decision_date
    match_return20

relative_strength:
    stock_vs_market_return_20d_asof_decision_date
    return_60d_cross_section_rank_pct_asof_decision_date
    close_to_ema60_asof_decision_date

liquidity_amount:
    amount_ratio_20d_asof_decision_date
    rolling_20d_money_mean_asof_decision_date
    match_amount20

volatility_range:
    atr_20_pct_asof_decision_date
    atr_20_pct_rank_asof_decision_date
    intraday_range_pct_asof_decision_date
    match_vol60

range_position:
    close_position_in_120d_range_asof_decision_date

market_regime:
    market_regime_risk_on_asof_decision_date
    market_drawdown_60d_asof_decision_date

size:
    match_market_cap
```

字段到 source 的 alias 规则必须固定：

```text
rolling_20d_money_mean_asof_decision_date:
    source_artifact = qfq money
    source_columns = money
    asof_rule = decision_date close
    reconstruction_formula = rolling mean money over sessions [t-19, t]

match_market_cap:
    source_alias = market_cap_bucket_asof_decision_date
    canonical_source_artifact = pit_topn_400_100_executable_daily.csv
    source_columns = total_market_cap_cny

match_amount20:
    source_alias = rolling_20d_amount_bucket_asof_decision_date
    canonical_source_artifact = qfq money
    source_columns = money

match_vol60:
    source_alias = rolling_60d_volatility_bucket_asof_decision_date
    canonical_source_artifact = qfq close
    source_columns = close

match_return20:
    source_alias = recent_20d_return_bucket_asof_decision_date
    canonical_source_artifact = qfq close
    source_columns = close
```

所有 feature source 必须输出到 `t0_feature_source_audit.csv`，记录：

```text
feature_name
feature_signal_group
source_alias
feature_value_type
source_artifact
source_columns
asof_rule
pit_safe_flag
missing_rate
left_bad_nonmissing_n
right_clean_nonmissing_n
left_bad_missing_rate
right_clean_missing_rate
missing_rate_delta_abs
used_in_primary_readout
primary_whitelist_flag
exploratory_only_flag
feature_support_gate
blocking_reason
```

任一 primary feature 无法证明 PIT 安全，必须从 primary readout 中剔除。
如果 config 的 primary whitelist 与本节字段集合不一致，必须 fail closed：

```text
decision_state = 19B1_t0_feature_pit_contract_blocked
blocking_reason = primary_t0_feature_whitelist_not_frozen_or_expanded
```

## 7. 统计读出

### 7.1 Outcome-space separability

必须先复现 19B 已观察到的 outcome-space 区分：

```text
P(left_tail_event_10 | right_tail_event_50)
P(left_tail_event_10 | not right_tail_event_50)
P(right_tail_event_50 | left_tail_event_10)
P(right_tail_event_50 | not left_tail_event_10)
Fisher exact test / chi-square test
phi coefficient
mutual information
cluster bootstrap CI for conditional probability differences
```

输出：

```text
outcome_left_right_overlap_readout.csv
```

`outcome_left_right_overlap_readout.csv` 必须至少记录：

```text
family_id
grid_cell_id
split
row_scope
candidate_n
instrument_n
right_tail_event_50_n
left_tail_event_10_n
left_tail_event_20_n
right_clean_n
left_bad_n
both_n
neither_n
p_left_tail_10_given_right_tail_50
p_left_tail_10_given_not_right_tail_50
p_right_tail_50_given_left_tail_10
p_right_tail_50_given_not_left_tail_10
left_tail_conditional_probability_diff_not_right_minus_right
right_tail_conditional_probability_diff_not_left_minus_left
fisher_exact_p_value
chi_square_p_value
phi_coefficient
mutual_information
cluster_bootstrap_diff_ci_low
cluster_bootstrap_diff_ci_high
outcome_overlap_gate
diagnostic_only_flag
blocking_reason
```

### 7.2 T0 单变量差异

对每个允许的 T0 feature，至少计算：

```text
left_bad_n
right_clean_n
left_bad_nonmissing_n
right_clean_nonmissing_n
left_bad_missing_rate
right_clean_missing_rate
missing_rate_delta_abs
left_bad_mean / median / p25 / p75
right_clean_mean / median / p25 / p75
standardized_mean_difference
median_difference
Mann-Whitney U p-value
Kolmogorov-Smirnov p-value
feature_auc_raw_left_bad_positive
feature_auc_oriented_left_bad_vs_right_clean = max(raw_auc, 1 - raw_auc)
direction_for_left_bad
cluster_bootstrap_CI_for_median_difference
cluster_bootstrap_oriented_auc_ci_low
cluster_bootstrap_oriented_auc_ci_high
missing_rate_by_group
feature_support_gate
```

`feature_support_gate = pass` 条件：

```text
left_bad_nonmissing_n >= per_feature_left_bad_nonmissing_n_min
right_clean_nonmissing_n >= per_feature_right_clean_nonmissing_n_min
max(left_bad_missing_rate, right_clean_missing_rate) <= per_feature_max_group_missing_rate
missing_rate_delta_abs <= per_feature_max_missing_rate_delta_abs
```

`feature_support_gate = fail` 的 feature 必须从 primary_feature_family 和 positive
diagnostic gate 中剔除，只能在 exploratory / blocked-feature appendix 中报告。

`direction_for_left_bad` 必须按 `left_bad median - right_clean median` 定义：

```text
positive = left_bad median > right_clean median
negative = left_bad median < right_clean median
flat = median difference == 0 or insufficient non-missing support
```

当 `direction_for_left_bad = negative` 时，原始 AUC 可以小于 0.50；primary gate
必须使用方向化后的 `feature_auc_oriented_left_bad_vs_right_clean`，不得用单向 raw AUC
错误剔除负方向可区分特征。

Multiple testing：

```text
primary_feature_family =
    config frozen primary_t0_feature_whitelist
    after PIT-safe filtering
    after feature_support_gate == pass filtering
correction_method = Benjamini-Hochberg FDR plus Bonferroni-Sidak sensitivity
report both raw_p and adjusted_p
```

输出：

```text
t0_univariate_feature_separability_readout.csv
```

### 7.3 多变量 diagnostic-only readout

允许做一个极简 diagnostic separability readout，目的不是训练模型，而是判断单变量差异
是否在共同出现时仍有信息。

允许方法：

```text
regularized_logistic_regression_diagnostic
rank_binned_logistic_regression_diagnostic
shallow_decision_stump_summary
```

约束：

```text
1. 只能在 B2 robustness frozen rows 内做 cross-fit diagnostic。
2. 至少使用 instrument-month 或 instrument cluster-aware split。
3. 只能报告 AUC、balanced accuracy、calibration-free rank metrics 和 feature coefficient stability。
4. 不得输出阈值化交易规则。
5. 不得把该 readout 称为 model_training 或 policy_training。
6. 不得调参、不得选择可交易阈值、不得持久化 model artifact。
7. 所有 regularization / binning / stump depth 必须使用 config 中预冻结常数。
8. multivariate readout 不得单独触发 positive diagnostic；只能作为 supporting diagnostic。
```

输出：

```text
t0_multivariate_diagnostic_separability_readout.csv
```

如果实现者认为多变量 readout 会造成策略训练歧义，可以跳过，但必须在报告中说明：

```text
multivariate_diagnostic_skipped_reason
```

当 `diagnostic_probe.multivariate_enabled = false` 时：

```text
t0_multivariate_diagnostic_separability_readout.csv
    必须输出一行 skipped record
multivariate_diagnostic_skipped_reason =
    multivariate_probe_disabled_by_pre_frozen_config_to_avoid_model_training_ambiguity
```

`t0_multivariate_diagnostic_separability_readout.csv` 必须至少记录：

```text
run_id
family_id
grid_cell_id
split
row_scope
multivariate_enabled
diagnostic_method
diagnostic_status
multivariate_diagnostic_skipped_reason
row_n
feature_n
crossfit_cluster_key
random_seed
auc
balanced_accuracy
rank_metric
feature_coefficient_stability_summary
model_artifact_written
threshold_rule_written
policy_training_flag
model_training_authorized
diagnostic_only_flag
blocking_reason
```

当 `multivariate_enabled = false` 时，该 CSV 必须输出一行：

```text
diagnostic_method = skipped_by_config
diagnostic_status = skipped
auc / balanced_accuracy / rank_metric = NaN
model_artifact_written = false
threshold_rule_written = false
policy_training_flag = false
model_training_authorized = false
diagnostic_only_flag = true
```

### 7.4 Stability checks

至少做以下稳定性检查：

```text
1. 按 instrument cluster bootstrap。
2. 按 decision_month leave-one-month-out。
3. 去除 top1/top3 winner instruments 后重算 primary feature separability。
4. B5 negative-control / contrast：同样统计，但不允许影响 B2 结论。
5. matched diagnostic sample 不作为 primary；只能报告是否方向一致。
```

Stability schema 必须固定：

```text
top_winner_instrument_rank_scope = B2 candidate_primary_denominator
top_winner_instrument_rank_metric =
    count(right_tail_event_50 and row_scope == candidate_primary_denominator)
top1_removal = remove instrument with rank 1 by winner count
top3_removal = remove instruments with ranks 1-3 by winner count
leave_one_month_fold_key = decision_month
leave_one_month_scope = held-out month diagnostic only
leave_one_month_min_effective_fold_n_for_reporting = 6
leave_one_month_out_required_for_stability_gate = false
effective_lomo_fold = held-out month where left_bad_nonmissing_n >= 20 and right_clean_nonmissing_n >= 20
if effective_lomo_fold_n < leave_one_month_min_effective_fold_n_for_reporting:
    lomo_stability_status = diagnostic_only_insufficient_effective_month_support
B5_negative_control_required_support:
    candidate_n >= 300
    right_clean_n >= 50
    left_bad_n >= 50
```

如果 B5 support 不足：

```text
B5_negative_control_support_gate = fail
B5_negative_control_used = false
B5_negative_control_skipped_reason = diagnostic_only_skipped_insufficient_support
```

B5 support fail 只能跳过 contrast diagnostic，不得影响 B2 primary decision_state。

输出：

```text
t0_separability_stability_readout.csv
```

`t0_separability_stability_readout.csv` 必须至少记录：

```text
family_id
grid_cell_id
stability_check
feature_name
baseline_direction_for_left_bad
check_direction_for_left_bad
direction_stable_flag
effective_fold_n
direction_stable_fold_n
direction_stable_fold_rate
top_removed_instrument_n
top_removed_winner_n
oriented_auc_after_check
feature_support_gate_after_check
stability_gate_component
lomo_stability_status
diagnostic_only_flag
blocking_reason
```

## 8. 判定规则

19B1 的 positive diagnostic 判定不能只靠单一 p-value。必须同时满足：

```text
config_contract_gate = pass
input_artifact_gate = pass
sample_support_gate = pass
primary_row_join_gate = pass
outcome_overlap_gate = pass
t0_feature_pit_gate = pass
primary_feature_separability_gate = pass
stability_gate = pass
policy_authorization_gate = pass
output_contract_gate = pass
```

`config_contract_gate = pass` 条件：

```text
all required config keys exist
all input_paths resolve under the experiment/repo roots or explicit path aliases and exist
output_root resolves under the experiment/repo roots or explicit path aliases
output_root parent exists; output_root itself may be created by the runner
primary_t0_feature_whitelist equals Section 6 list exactly
thresholds/support/bootstrap/diagnostic constants equal Section 1.1
```

`input_artifact_gate = pass` 条件：

```text
all required input artifacts exist
all required input artifacts have observed hashes recorded in input_artifact_audit.csv
all 19B artifacts listed in output_hashes_19b...json match observed hashes
```

`t0_feature_pit_gate = pass` 条件：

```text
all used primary features have pit_safe_flag = true in t0_feature_source_audit.csv
all used primary features have primary_whitelist_flag = true
all used primary features have exploratory_only_flag = false
all used primary features have feature_signal_group in Section 6.1
all match_* aliases resolve through Section 6.1 alias contract
no forbidden feature column is present in the feature matrix
no forward_* / MFE_120 / MAE_20 / group label / validation outcome /
    post-hoc label-derived feature is used
all used primary features trace to simple_rule_feature_source_map,
    matching_feature_source_map, qfq, benchmark, or topn executable universe source
```

`output_contract_gate = pass` 条件：

```text
all required CSV / figure / report / handoff / manifest / output_hash files exist
all required tabular outputs are non-empty unless explicitly skipped by frozen config
all required schemas in this requirement are satisfied
manifest_19b1...json lists every required output and records hashes for every non-manifest output
output_hashes_19b1...json records hashes for every required output except itself
observed output hashes match all non-circular manifest/output_hashes records
report contains all required authorization and diagnostic-only statements
handoff contract contains no executable next_allowed_requirement
```

`outcome_overlap_gate = pass` 条件：

```text
P(left_tail_event_10 | not right_tail_event_50)
  - P(left_tail_event_10 | right_tail_event_50) > 0
cluster_bootstrap_CI_low > 0
```

`primary_feature_separability_gate = pass` 条件：

```text
At least 2 PIT-safe T0 features satisfy all:
    feature_support_gate = pass
    BH_FDR_adjusted_p <= 0.10
    abs(standardized_mean_difference) >= 0.20
    feature_auc_oriented_left_bad_vs_right_clean >= 0.57
    cluster_bootstrap_oriented_auc_ci_low > 0.50
    direction_for_left_bad in {positive, negative}
The passing features must come from at least 2 distinct feature_signal_group values.
At most 1 passing feature per feature_signal_group may count toward the minimum.
```

`stability_gate = pass` 条件：

```text
For at least 1 top feature:
    cluster bootstrap direction stable rate >= stability_bootstrap_direction_stable_rate_min
    direction remains same after top1/top3 instrument removal
    feature_support_gate_after_check = pass after top1/top3 instrument removal
LOMO monthly stability is diagnostic-only and cannot by itself fail stability_gate.
```

`policy_authorization_gate = pass` 条件：

```text
all model/policy/backtest/deployment/trading authorization fields are false
```

允许 decision states：

```text
19B1_t0_left_right_tail_separable_diagnostic
19B1_t0_left_right_tail_not_separable_diagnostic
19B1_config_contract_blocked
19B1_input_artifact_blocked
19B1_sample_support_blocked
19B1_t0_feature_pit_contract_blocked
19B1_upstream_contract_blocked
19B1_upstream_19b_contract_blocked
19B1_output_contract_blocked
```

不允许任何状态授权 replay、policy 或 live trading。

Decision precedence 必须固定：

```text
1. config contract 失败:
       decision_state = 19B1_config_contract_blocked
2. input artifact 缺失或 19B input hash 不一致:
       decision_state = 19B1_input_artifact_blocked
3. output artifact/schema/hash 失败:
       decision_state = 19B1_output_contract_blocked
4. 19A/19B0 聚合合同失败:
       decision_state = 19B1_upstream_contract_blocked
5. 19B 合同、boundary、row-scope 或 join 合同失败:
       decision_state = 19B1_upstream_19b_contract_blocked
6. Primary B2 support 不足:
       decision_state = 19B1_sample_support_blocked
7. Primary feature whitelist 未冻结/被扩展、PIT source 无法证明、或全部 primary
   features 因 PIT/source/support 被剔除:
       decision_state = 19B1_t0_feature_pit_contract_blocked
8. 以上合同均通过，但 outcome_overlap_gate、primary_feature_separability_gate
   或 stability_gate 任一未通过:
       decision_state = 19B1_t0_left_right_tail_not_separable_diagnostic
9. 全部 positive diagnostic gates 通过:
       decision_state = 19B1_t0_left_right_tail_separable_diagnostic
```

## 9. 必需输出

输出目录：

```text
EXPERIMENT_ROOT/outputs/19B1_t0_left_right_tail_separability_readout/
```

必需 CSV：

```text
input_artifact_audit.csv
upstream_contract_audit.csv
t0_feature_join_audit.csv
t0_feature_source_audit.csv
t0_feature_matrix_manifest.csv
outcome_left_right_overlap_readout.csv
t0_univariate_feature_separability_readout.csv
t0_multivariate_diagnostic_separability_readout.csv
t0_separability_stability_readout.csv
search_accounting_audit.csv
entry_universe_19b1_decision.csv
```

`upstream_contract_audit.csv` 必须至少记录：

```text
upstream_scope
artifact_id
source_file
required_fact
expected_value
observed_value
source_row_filter
derived_gate
contract_gate
hash_verified
validation_outcome_read
authorization_field
authorization_value
blocking_reason
```

`upstream_scope` 只允许：

```text
19A
19B0
19B
19B_boundary
19B_hash
```

`entry_universe_19b1_decision.csv` 必须输出单行，并至少记录：

```text
run_id
created_at
requirement_file_hash
config_file_hash
primary_whitelist_hash
input_artifact_hash_manifest
config_contract_gate
input_artifact_gate
upstream_19a_contract_gate
upstream_19b0_contract_gate
upstream_19b_contract_gate
sample_support_gate
primary_row_join_gate
outcome_overlap_gate
t0_feature_pit_gate
primary_feature_separability_gate
stability_gate
policy_authorization_gate
output_contract_gate
decision_state
blocking_reason
family_id
grid_cell_id
row_scope
split
candidate_n
instrument_n
right_clean_n
left_bad_n
both_n
neither_n
N_primary_whitelist_features_frozen
N_primary_features_pit_safe_used
N_primary_features_support_pass
N_primary_features_support_fail
N_primary_features_separability_pass
N_distinct_passing_feature_signal_groups
B5_negative_control_used
B5_negative_control_support_gate
B5_negative_control_skipped_reason
validation_outcome_read
max_ep19_terminal_state
next_allowed_requirement
next_research_suggestion
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

`t0_feature_matrix_manifest.csv` 必须记录：

```text
family_id
grid_cell_id
row_scope
split
row_n
feature_n
primary_feature_columns_json
accounting_only_columns_json
exploratory_feature_columns_json
forbidden_column_n
forbidden_columns_json
forbidden_label_column_n
forbidden_label_columns_json
feature_matrix_hash
candidate_row_hash
primary_whitelist_hash
missing_any_primary_n
missing_any_primary_rate
all_primary_features_pit_safe
all_primary_features_support_pass_n
feature_matrix_gate
blocking_reason
```

必需图表：

```text
figures/b2_outcome_left_right_overlap.png
figures/b2_t0_top_feature_distributions.png
figures/b2_t0_feature_auc_forest.png
figures/b2_t0_separability_stability.png
```

必需文本/JSON：

```text
19B1_t0_left_right_tail_separability_readout_report.md
19B1_handoff_contract.md
manifest_19b1_t0_left_right_tail_separability_readout.json
output_hashes_19b1_t0_left_right_tail_separability_readout.json
```

报告必须明确写出：

```text
1. 19B1 是 diagnostic-only。
2. validation outcome read = false。
3. 19C replay authorized = false。
4. EP20 policy preflight authorized = false。
5. entry/exit/holding/portfolio/model/production/live trading authorization = false。
6. T0 separability 不等于 alpha support。
7. 任何后续 left-tail suppressor 必须作为新的 pre-registered requirement，
   不能从 19B1 直接生成交易规则。
```

## 10. 搜索/accounting 约束

`search_accounting_audit.csv` 必须记录：

```text
N_family_primary = 1
primary_family = B2_relative_strength_breakout
primary_grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
primary_row_scope = candidate_primary_denominator
N_candidate_rows
N_instruments
N_t0_features_tested
N_primary_whitelist_features_frozen
N_primary_features_pit_safe_used
N_primary_features_support_pass
N_primary_features_support_fail
N_exploratory_features_reported
feature_family_correction_method
secondary_comparisons_count
B5_negative_control_used
B5_negative_control_support_gate
validation_outcome_read = false
thresholds_frozen_before_19B1 = true
left_tail_thresholds = [-0.10, -0.20]
right_tail_thresholds = [+0.50]
```

19B1 可以使用 19B 已观察到的 `-10%` fast-fail 和 `+50%` big-winner threshold；
不得在 19B1 内搜索新的 outcome threshold 作为 primary claim。

## 11. Handoff

19B1 handoff 只能给出下一步研究建议，不得授权执行。

如果 separability positive：

```text
next_research_suggestion =
    draft_pre_registered_B2_left_tail_suppressor_ablation_requirement
```

如果 separability negative：

```text
next_research_suggestion =
    do_not_attempt_B2_t0_left_tail_suppressor_without_new_features
```

无论哪种情况：

```text
next_allowed_requirement = none
19C replay remains forbidden
EP20 policy preflight remains forbidden
```
