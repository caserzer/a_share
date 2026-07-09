# Requirement: 19B2 B2 高波动强势延伸左尾 suppressor 消融预检

## 0. 不可协商范围

19B2 是 19B1 之后的新预注册 diagnostic / ablation requirement。它只回答一个问题：

```text
在 19B 已冻结的 B2 robustness candidate rows 上，是否存在一个 PIT 合法、
简单、可解释的 high-volatility x extension suppressor，能优先删除 left_bad
污染样本，同时尽量保留 right_clean 右尾 reservoir？
```

19B2 不训练模型，不做 hyperparameter search，不读取 validation outcome，不运行 19C
replay，不输出 entry/exit/holding/portfolio policy，不输出 production signal，不授权 live
trading。

19B2 允许在同一个冻结 B2 robustness 样本上做预注册消融：

```text
1. 使用 19B1 已经通过 diagnostic 的 T0 feature family。
2. 固定 score 公式和 threshold grid。
3. 读取 19B robustness outcome 只用于 diagnostic readout。
4. 输出 suppressor ablation metrics、四分组保留/删除表、common-support 描述性审计、
   中文报告、manifest 和 output hashes。
```

19B2 的正向结果最多只能说明：

```text
19B2_high_vol_extension_suppressor_ablation_supported_diagnostic:
    B2 left_bad 污染样本中存在可解释的 high-volatility x extension 子群；
    该子群在冻结 robustness 样本上可以被 T0 score 优先删除。
```

它不得被解释为 alpha support、residual alpha、validation support、entry rule approval
或策略可交易性。

无论 19B2 结果如何，最高授权仍保持：

```text
max_ep19_terminal_state = 19_entry_universe_enrichment_only_diagnostic
validation_outcome_read = false
19C_replay_authorized = false
EP20_policy_preflight_authorized = false
entry_policy_preflight_authorized = false
model_training_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

如果 19B2 支持 high-vol-extension suppressor，它只能作为后续新的
pre-registered requirement 的 hypothesis source；后续如果要研究 delayed
confirmation、entry timing、left-tail rejector model 或 replay，必须另开 requirement。

## 1. 身份

```text
experiment_id = 19_entry_universe_pit_tradability_preflight
phase_id = 19B2
run_id = 19B2_b2_high_vol_extension_left_tail_suppressor_ablation
requirement_file = requirement_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.md
config_file = configs/config_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.yaml
runner_file = src/run_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.py
test_file = tests/test_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.py
output_root = outputs/19B2_b2_high_vol_extension_left_tail_suppressor_ablation
```

执行工作目录：

```bash
cd topics/02_AFML_BIG_WINNER
```

所有路径必须通过 config 或显式 path alias 解析。实现不得硬编码个人机器绝对路径。

### 1.1 Config contract

`config_file` 必须在运行前冻结以下字段。任何必需字段缺失、输入路径不存在、score
公式、grid、threshold 或 whitelist 与本 requirement 不一致，必须 fail closed。

```text
input_paths:
    nineteen_b_decision
    nineteen_b_manifest
    nineteen_b_output_hashes
    nineteen_b_handoff_contract
    nineteen_b_robustness_candidate_row_manifest
    nineteen_b_robustness_outcome_boundary_audit
    nineteen_b_robustness_metric_readout
    nineteen_b_false_positive_burden_readout
    nineteen_b_mfe_mae_joint_readout
    nineteen_b_robustness_baseline_quality_audit
    nineteen_b_topk_concentration_sensitivity
    nineteen_b_upstream_19a_contract_audit
    nineteen_b_upstream_19b0_contract_audit
    nineteen_b1_decision
    nineteen_b1_manifest
    nineteen_b1_output_hashes
    nineteen_b1_handoff_contract
    nineteen_b1_outcome_left_right_overlap_readout
    nineteen_b1_univariate_feature_separability_readout
    nineteen_b1_feature_source_audit
    nineteen_b1_feature_join_audit
    nineteen_b1_feature_matrix_manifest
    nineteen_b1_stability_readout
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
    primary_suppressor_feature_whitelist:
        match_vol60
        atr_20_pct_asof_decision_date
        return_60d_asof_decision_date
        close_to_ema60_asof_decision_date
    rank_scope = executable_universe_same_decision_date
    rank_pct_method = average_rank_pct_ascending
    high_value_means_higher_left_tail_risk = true
    forbidden_feature_prefixes:
        forward_mfe_
        forward_mae_
        forward_return_
        forward_big_winner_
    forbidden_label_columns:
        MFE_120
        MAE_20
        right_tail_event_50
        left_tail_event_10
        left_tail_event_20
        right_clean
        left_bad
        both
        neither

score_contract:
    q_vol60 = rank_pct(match_vol60)
    q_atr20 = rank_pct(atr_20_pct_asof_decision_date)
    q_ret60 = rank_pct(return_60d_asof_decision_date)
    q_ema60_dist = rank_pct(close_to_ema60_asof_decision_date)
    vol_block = max(q_vol60, q_atr20)
    extension_block = max(q_ret60, q_ema60_dist)
    tail_risk_score = vol_block * extension_block
    basis_risk_score = q_ema60_dist * max(q_atr20, q_vol60)
    vol_expansion_rank_spread = q_atr20 - q_vol60
    atr20_over_vol60 = atr_20_pct_asof_decision_date / max(match_vol60, epsilon)
    candidate_vol_block_rank_pct = rank_pct(vol_block within B2 primary candidate rows)
    candidate_extension_block_rank_pct = rank_pct(extension_block within B2 primary candidate rows)
    candidate_q_atr20_rank_pct = rank_pct(q_atr20 within B2 primary candidate rows)
    candidate_q_ema60_dist_rank_pct = rank_pct(q_ema60_dist within B2 primary candidate rows)
    candidate_q_vol60_rank_pct = rank_pct(q_vol60 within B2 primary candidate rows)
    candidate_q_ret60_rank_pct = rank_pct(q_ret60 within B2 primary candidate rows)
    epsilon = 1e-12

grid_contract:
    primary_tail_risk_top_pct = [0.10, 0.15, 0.20, 0.25, 0.30]
    single_feature_top_pct = [0.10, 0.20, 0.30]
    logical_interaction_threshold_pairs:
        vol80_extension80
        vol70_extension85
        vol85_extension70
        atr80_ema80
        vol60_80_ret60_80
    basis_risk_top_pct = [0.10, 0.15, 0.20, 0.25, 0.30]
    volatility_contraction_top_pct = [0.20]

support:
    candidate_n_min = 300
    instrument_n_min = 30
    right_clean_n_min = 50
    left_bad_n_min = 50
    kept_candidate_n_min = 300
    kept_right_tail_event_50_n_min = 50
    rank_cross_section_min_n = 30

primary_success_thresholds:
    left_bad_removed_per_right_clean_removed_min = 2.0
    MAE_20_p10_improvement_vs_S0_min = 0.01
    p_candidate_50_after_min = 0.24
    right_clean_kept_rate_min = 0.70
    interaction_vs_single_feature_efficiency_lift_min = 0.10
    interaction_efficiency_lift_ci_low_min = 0.00

bootstrap:
    bootstrap_resample_n = 2000
    bootstrap_seed = 20260709
    cluster_key = instrument_id
```

`input_artifact_audit.csv` 只记录 `input_paths` 中输入 artifact 的 existence、row count、
observed hash 和 input gate；不得把 `output_root` 当作 input artifact 要求预先存在。
所有 config 相对路径必须以 `topics/02_AFML_BIG_WINNER` 为运行根目录解析；不得相对 repo 根
或个人机器绝对路径解析。

## 2. 上游合同

19B2 必须先验证 19A、19B0、19B、19B1 的闭包。任何合同不通过时必须 fail closed。

### 2.1 19B 必需事实

必须读取并校验：

```text
entry_universe_19b_decision.csv
manifest_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json
output_hashes_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.json
19B_handoff_contract.md
robustness_candidate_row_manifest.csv
robustness_metric_readout.csv
false_positive_burden_readout.csv
mfe_mae_joint_readout.csv
robustness_baseline_quality_audit.csv
topk_concentration_sensitivity.csv
upstream_19a_contract_audit.csv
upstream_19b0_contract_audit.csv
```

必需事实：

```text
upstream_19a_contract_gate = pass
upstream_19b0_contract_gate = pass
validation_outcome_read = false
positive_exposure_robustness_gate = pass
matched_baseline_residual_gate = fail
robustness_candidate_manifest_gate = pass
outcome_boundary_gate = pass
robustness_candidate_manifest_frozen_before_label_readout = true
label_read_before_manifest_freeze = false
max_ep19_terminal_state_if_no_residual_pass = 19_entry_universe_enrichment_only_diagnostic
```

B2 必须存在且处于 false-positive burden blocked 或 enrichment-only diagnostic 轨道：

```text
family_id = B2_relative_strength_breakout
grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
split = robustness
row_scope = candidate_primary_denominator
```

如果 19B 输出缺失、hash 不一致、validation outcome 已被读取、或任何 policy/trading
授权字段为 true：

```text
decision_state = 19B2_upstream_19b_contract_blocked
blocking_reason = upstream_19b_contract_failed
```

### 2.2 19B1 必需事实

必须读取并校验：

```text
entry_universe_19b1_decision.csv
manifest_19b1_t0_left_right_tail_separability_readout.json
output_hashes_19b1_t0_left_right_tail_separability_readout.json
19B1_handoff_contract.md
outcome_left_right_overlap_readout.csv
t0_univariate_feature_separability_readout.csv
t0_feature_source_audit.csv
t0_feature_join_audit.csv
t0_feature_matrix_manifest.csv
t0_separability_stability_readout.csv
```

必需事实：

```text
19B1 decision_state = 19B1_t0_left_right_tail_separable_diagnostic
validation_outcome_read = false
19C_replay_authorized = false
EP20_policy_preflight_authorized = false
model_training_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
max_ep19_terminal_state = 19_entry_universe_enrichment_only_diagnostic
```

19B1 必须已经确认 B2 四分组和 feature separability：

```text
candidate_n = 1552
instrument_n = 524
right_clean_n = 290
left_bad_n = 614
both_n = 145
neither_n = 503
primary_feature_separability_gate = pass
stability_gate = pass
```

19B2 primary suppressor feature 必须是 19B1 separability pass 且方向为
`left_bad` 更高的字段：

```text
match_vol60
atr_20_pct_asof_decision_date
return_60d_asof_decision_date
close_to_ema60_asof_decision_date
```

这些字段必须在 `t0_univariate_feature_separability_readout.csv` 中满足：

```text
separability_pass = true
feature_support_gate = pass
direction_for_left_bad = positive
cluster_bootstrap_direction_stable_rate >= 0.70
```

如果任一字段不满足，必须 fail closed：

```text
decision_state = 19B2_upstream_19b1_contract_blocked
blocking_reason = required_19b1_feature_separability_not_confirmed
```

19B1 的 `next_allowed_requirement = none` 不阻断 19B2，因为 19B2 是用户新开、
预注册、diagnostic-only 的 ablation requirement；19B2 必须在自己的 handoff 中继续保持
`next_allowed_requirement = none`，只能给出 non-executable research suggestion。

### 2.3 上游 output hash resolver

19B2 必须校验 19B 和 19B1 `output_hashes_*.json` 中所有 artifact id。hash resolver
必须使用下列固定映射；不得用文件名猜测、不得只校验子集。

19B artifact id 到文件路径映射：

```text
entry_universe_19b_decision -> entry_universe_19b_decision.csv
input_artifact_audit -> input_artifact_audit.csv
upstream_19a_contract_audit -> upstream_19a_contract_audit.csv
upstream_19b0_contract_audit -> upstream_19b0_contract_audit.csv
robustness_candidate_row_manifest -> robustness_candidate_row_manifest.csv
robustness_outcome_boundary_audit -> robustness_outcome_boundary_audit.csv
robustness_metric_readout -> robustness_metric_readout.csv
robustness_positive_exposure_readout -> robustness_positive_exposure_readout.csv
robustness_residual_alpha_readout -> robustness_residual_alpha_readout.csv
robustness_baseline_quality_audit -> robustness_baseline_quality_audit.csv
robustness_baseline_row_manifest -> robustness_baseline_row_manifest.csv
baseline_repair_variant_registry -> baseline_repair_variant_registry.csv
baseline_repair_sweep_audit -> baseline_repair_sweep_audit.csv
false_positive_burden_readout -> false_positive_burden_readout.csv
topk_concentration_sensitivity -> topk_concentration_sensitivity.csv
cluster_bootstrap_ci -> cluster_bootstrap_ci.csv
tail_lift_curve_readout -> tail_lift_curve_readout.csv
ccdf_survival_curve_readout -> ccdf_survival_curve_readout.csv
capture_vs_burden_readout -> capture_vs_burden_readout.csv
b2_right_left_tail_lift_balance_readout -> b2_right_left_tail_lift_balance_readout.csv
mfe_mae_joint_readout -> mfe_mae_joint_readout.csv
search_accounting_audit -> search_accounting_audit.csv
handoff_contract -> 19B_handoff_contract.md
report -> 19B_robust_right_tail_enrichment_and_false_positive_burden_readout_report.md
tail_lift_curve_figure -> figures/tail_lift_curve.png
ccdf_survival_curve_figure -> figures/ccdf_survival_curve.png
capture_vs_burden_figure -> figures/capture_vs_burden.png
mfe_mae_joint_scatter_figure -> figures/mfe_mae_joint_scatter.png
b2_right_left_tail_lift_balance_figure -> figures/b2_right_left_tail_lift_balance.png
```

19B1 artifact id 到文件路径映射：

```text
entry_universe_19b1_decision -> entry_universe_19b1_decision.csv
input_artifact_audit -> input_artifact_audit.csv
upstream_contract_audit -> upstream_contract_audit.csv
t0_feature_join_audit -> t0_feature_join_audit.csv
outcome_left_right_overlap_readout -> outcome_left_right_overlap_readout.csv
t0_feature_source_audit -> t0_feature_source_audit.csv
t0_feature_matrix_manifest -> t0_feature_matrix_manifest.csv
t0_univariate_feature_separability_readout -> t0_univariate_feature_separability_readout.csv
t0_separability_stability_readout -> t0_separability_stability_readout.csv
t0_multivariate_diagnostic_separability_readout -> t0_multivariate_diagnostic_separability_readout.csv
search_accounting_audit -> search_accounting_audit.csv
handoff_contract -> 19B1_handoff_contract.md
manifest -> manifest_19b1_t0_left_right_tail_separability_readout.json
report -> 19B1_t0_left_right_tail_separability_readout_report.md
b2_outcome_left_right_overlap_figure -> figures/b2_outcome_left_right_overlap.png
b2_t0_feature_auc_forest_figure -> figures/b2_t0_feature_auc_forest.png
b2_t0_separability_stability_figure -> figures/b2_t0_separability_stability.png
b2_t0_top_feature_distributions_figure -> figures/b2_t0_top_feature_distributions.png
```

如果 `output_hashes_*.json` 出现未列入映射的 artifact id，必须 fail closed：

```text
decision_state = 19B2_input_artifact_blocked
blocking_reason = upstream_output_hash_key_unmapped
```

## 3. 研究问题

19B2 只回答五个问题：

```text
Q1. B2 left_bad 是否主要集中在 high-volatility x extension 的 T0 子群？

Q2. tail_risk_score = max(vol60_rank, atr20_rank) *
    max(return60_rank, ema60_distance_rank) 是否比单变量截断更能优先删除
    left_bad、保留 right_clean？

Q3. entry basis risk = ema60_distance_rank * max(atr20_rank, vol60_rank)
    是否解释了 B2 的“买点离支撑太远”左尾污染？

Q4. volatility contraction / expansion 描述性消融是否支持：
    B2 应保留收敛后突破，过滤高波状态下继续冲高？

Q5. 在不读取 validation、不训练模型、不运行 replay 的情况下，19B2 是否足以支持
    下一轮更具体的 pre-registered delayed confirmation 或 entry basis requirement？
```

19B2 不回答：

```text
1. 该 suppressor 是否可交易。
2. 该 suppressor 在 validation 上是否有效。
3. 该 suppressor 是否能进入 19C replay。
4. 该 suppressor 是否应该直接成为 entry rule。
5. delayed confirmation 的具体交易时点、成交价、滑点或组合收益。
6. left-tail rejector model 是否有效。
```

## 4. 允许和禁止工作

允许：

```text
1. 读取 19B 已冻结的 B2 robustness candidate rows 和 19B robustness outcome。
2. 读取 19B1 的 feature separability 结论，作为 19B2 feature whitelist 的依据。
3. 用同一批 B2 frozen rows 重建 PIT / as-of-decision-date feature panel。
4. 按本 requirement 冻结的 score 和 threshold grid 生成 suppressor variants。
5. 对每个 variant 输出 right_clean / left_bad / both / neither 四分组保留/删除表。
6. 输出 p_candidate_50_after、MAE_20_p10_after、fast_fail_rate_after、
   candidate_per_winner_after、common-support 和 concentration 描述性指标。
7. 对 primary metrics 做 cluster bootstrap CI。
8. 输出机器可读 audit、中文报告、manifest、output hashes 和图表。
```

禁止：

```text
1. 不得读取 validation outcome、validation MFE/MAE、validation winner 或 validation fast-fail label。
2. 不得运行 19C replay、EP20 policy preflight、组合回测或生产信号生成。
3. 不得训练 predictive model、left-tail rejector model、hyperparameter tuner 或 policy model。
4. 不得使用 19B2 outcome 结果动态调整 score 公式、threshold grid、feature whitelist 或 success gate。
5. 不得新增 19B1 未确认的 primary feature。
6. 不得把 both group 粗暴当成坏样本；both 必须单独输出和单独解释。
7. 不得把 return_60d 或 close_to_ema60 的高值单独解释为必须删除的坏信号。
8. 不得把 common-support / market-regime 描述性改善解释为 left-tail suppressor 机制成立。
9. 不得输出任何 executable entry/exit/holding rule、position sizing rule、portfolio allocation
   或 live trading instruction。
```

## 5. 样本和标签定义

### 5.1 Primary rows

Primary rows 必须从 19B `mfe_mae_joint_readout.csv` 中按以下条件过滤：

```text
family_id = B2_relative_strength_breakout
grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
split = robustness
row_scope = candidate_primary_denominator
```

并与 19B `robustness_candidate_row_manifest.csv` 做一对一合同校验：

```text
join_keys = family_id, grid_cell_id, row_key, instrument_id, decision_date
required_manifest_flags:
    candidate_flag = true
    primary_enrichment_denominator_flag = true
    manifest_frozen_before_label_readout = true
    label_read_before_manifest_freeze = false
```

禁止混入：

```text
eligible_universe_baseline_sample
matched_baseline_diagnostic_sample
matched_baseline_quality_pass_sample
train split
validation split
```

### 5.2 Outcome groups

在 19B frozen B2 candidate rows 上定义：

```text
right_tail_event_50 = MFE_120 >= +0.50
left_tail_event_10 = MAE_20 <= -0.10
left_tail_event_20 = MAE_20 <= -0.20

right_clean = right_tail_event_50 and not left_tail_event_10
left_bad = left_tail_event_10 and not right_tail_event_50
both = right_tail_event_50 and left_tail_event_10
neither = not right_tail_event_50 and not left_tail_event_10
```

`both` 不得并入 `left_bad`。Primary objective 必须只比较：

```text
desired_removed_group = left_bad
protected_group = right_clean
tracked_ambiguous_group = both
tracked_neutral_group = neither
```

### 5.3 Rank construction

Primary score 必须使用 PIT rank。默认 rank scope：

```text
rank_scope = executable_universe_same_decision_date
rank_source = 19A / 19B executable universe feature materialization, as of decision_date close
```

每个 `decision_date` 上，必须在可执行 universe 的横截面内计算 rank percentile：

```text
q_feature = rank_pct(feature_value, ascending = true, method = average)
```

如果当日 rank cross-section 的可用样本数小于 `rank_cross_section_min_n`，该日期 rows
不得进入 primary score，应记录到 `rank_source_audit.csv`。不得 fallback 到全样本 rank、
robustness-period rank、或 outcome group 内 rank。

所有 rank 必须在读取 outcome group 之前按 row key 物化到
`b2_pre_outcome_rank_panel.csv`。该文件不得包含 `MFE_120`、`MAE_20`、
`right_tail_event_*`、`left_tail_event_*`、`outcome_group`、`fast_fail_flag`、
`false_repair_flag` 或任何 forward label。后续 `b2_suppressor_score_panel.csv` 只能
通过 `row_key / instrument_id / decision_date` 从该 pre-outcome panel join outcome。

`rank_source_audit.csv` 必须证明 rank 只依赖 decision_date 当时已知特征，并至少记录：

```text
decision_date
rank_scope
rank_cross_section_n
rank_feature_n
rank_source_artifact
rank_source_before_outcome_join
forbidden_label_column_n
missing_required_feature_n
rank_source_gate
blocking_reason
```

## 6. Score 和消融矩阵

### 6.1 Primary score

19B2 primary score 固定为：

```text
q_vol60 = rank_pct(match_vol60)
q_atr20 = rank_pct(atr_20_pct_asof_decision_date)
q_ret60 = rank_pct(return_60d_asof_decision_date)
q_ema60_dist = rank_pct(close_to_ema60_asof_decision_date)

vol_block = max(q_vol60, q_atr20)
extension_block = max(q_ret60, q_ema60_dist)

tail_risk_score = vol_block * extension_block
```

解释：

```text
high return60 alone is not bad;
high ema60 distance alone is not bad;
high volatility alone is not sufficient;
the primary risk hypothesis is high volatility and strong extension appearing together.
```

### 6.2 Entry basis score

19B2 entry-basis diagnostic score 固定为：

```text
basis_risk_score = q_ema60_dist * max(q_atr20, q_vol60)
```

它只检验“买点离 EMA60 太远且处于高波动状态”是否是 left_bad 来源。它不得被解释为
entry timing rule。

### 6.3 Volatility expansion / contraction score

19B2 volatility contraction diagnostic 只允许使用已有四个 primary feature 派生：

```text
vol_expansion_rank_spread = q_atr20 - q_vol60
atr20_over_vol60 = atr_20_pct_asof_decision_date / max(match_vol60, 1e-12)
```

`atr20_over_vol60` 是 volatility expansion proxy，不是严格量纲一致的物理比率：
`atr_20_pct_asof_decision_date` 是 ATR 百分比，`match_vol60` 是 60 日收益率标准差。
该字段只允许用于 D 组 descriptive ablation 和图表解释，不得进入 primary success gate。

D 组只做 descriptive ablation，不进入 primary success gate。更完整的 VCP / base quality
特征，例如 close_to_vwap20、close_to_20d_low、distance_to_recent_pivot_low、
ATR_normalized_stop_distance、bollinger bandwidth、range_contraction_days，全部 deferred
到后续 requirement；19B2 primary 不得新增这些特征。

Logical interaction variants 不得直接使用 `vol_block >= 0.80` 这类 executable-universe
绝对 rank 阈值，因为 B2 candidate 本身已经位于 universe 的高波动/高强势尾部，会造成
删除量失控。B 组必须先在 pre-outcome B2 primary candidate rows 内，对 score component
再做一次 score-ordering rank：

```text
candidate_vol_block_rank_pct
candidate_extension_block_rank_pct
candidate_q_atr20_rank_pct
candidate_q_ema60_dist_rank_pct
candidate_q_vol60_rank_pct
candidate_q_ret60_rank_pct
```

这些 candidate-scope ranks 只用于 variant budget control，不是 feature PIT rank，也不得
按 outcome group 计算；它们必须在 outcome join 前写入 `b2_pre_outcome_rank_panel.csv`。

### 6.4 Variant grid

必须生成 `suppressor_variant_grid.csv`，且至少包含以下 variants。下表是机器可读
grid contract；实现和测试必须逐行校验 `variant_id / suppressor_family / score_name /
threshold_type / threshold_value / candidate_removed_target_pct / logical_condition /
primary_success_eligible / exploratory_only / excluded_from_primary_success_gate`。

```text
variant_id,suppressor_family,score_name,threshold_type,threshold_value,candidate_removed_target_pct,logical_condition,primary_success_eligible,exploratory_only,excluded_from_primary_success_gate
S0,baseline,none,none,,0.00,keep_all,false,false,true
S1,tail_risk_score_top_pct,tail_risk_score,top_pct,0.10,0.10,tail_risk_score >= p90,true,false,false
S2,tail_risk_score_top_pct,tail_risk_score,top_pct,0.15,0.15,tail_risk_score >= p85,true,false,false
S3,tail_risk_score_top_pct,tail_risk_score,top_pct,0.20,0.20,tail_risk_score >= p80,true,false,false
S4,tail_risk_score_top_pct,tail_risk_score,top_pct,0.25,0.25,tail_risk_score >= p75,true,false,false
S5,tail_risk_score_top_pct,tail_risk_score,top_pct,0.30,0.30,tail_risk_score >= p70,true,false,false
A_VOL60_top10,single_feature,q_vol60,top_pct,0.10,0.10,q_vol60 >= p90,false,false,true
A_VOL60_top20,single_feature,q_vol60,top_pct,0.20,0.20,q_vol60 >= p80,false,false,true
A_VOL60_top30,single_feature,q_vol60,top_pct,0.30,0.30,q_vol60 >= p70,false,false,true
A_ATR20_top10,single_feature,q_atr20,top_pct,0.10,0.10,q_atr20 >= p90,false,false,true
A_ATR20_top20,single_feature,q_atr20,top_pct,0.20,0.20,q_atr20 >= p80,false,false,true
A_ATR20_top30,single_feature,q_atr20,top_pct,0.30,0.30,q_atr20 >= p70,false,false,true
A_RET60_top10,single_feature,q_ret60,top_pct,0.10,0.10,q_ret60 >= p90,false,false,true
A_RET60_top20,single_feature,q_ret60,top_pct,0.20,0.20,q_ret60 >= p80,false,false,true
A_RET60_top30,single_feature,q_ret60,top_pct,0.30,0.30,q_ret60 >= p70,false,false,true
A_EMA60_top10,single_feature,q_ema60_dist,top_pct,0.10,0.10,q_ema60_dist >= p90,false,false,true
A_EMA60_top20,single_feature,q_ema60_dist,top_pct,0.20,0.20,q_ema60_dist >= p80,false,false,true
A_EMA60_top30,single_feature,q_ema60_dist,top_pct,0.30,0.30,q_ema60_dist >= p70,false,false,true
B_vol80_extension80,logical_interaction,candidate_vol_block_rank_pct__candidate_extension_block_rank_pct,candidate_score_rank_threshold,0.80,,candidate_vol_block_rank_pct >= 0.80 and candidate_extension_block_rank_pct >= 0.80,true,false,false
B_vol70_extension85,logical_interaction,candidate_vol_block_rank_pct__candidate_extension_block_rank_pct,candidate_score_rank_threshold,0.70|0.85,,candidate_vol_block_rank_pct >= 0.70 and candidate_extension_block_rank_pct >= 0.85,true,false,false
B_vol85_extension70,logical_interaction,candidate_vol_block_rank_pct__candidate_extension_block_rank_pct,candidate_score_rank_threshold,0.85|0.70,,candidate_vol_block_rank_pct >= 0.85 and candidate_extension_block_rank_pct >= 0.70,true,false,false
B_atr80_ema80,logical_interaction,candidate_q_atr20_rank_pct__candidate_q_ema60_dist_rank_pct,candidate_score_rank_threshold,0.80,,candidate_q_atr20_rank_pct >= 0.80 and candidate_q_ema60_dist_rank_pct >= 0.80,true,false,false
B_vol60_80_ret60_80,logical_interaction,candidate_q_vol60_rank_pct__candidate_q_ret60_rank_pct,candidate_score_rank_threshold,0.80,,candidate_q_vol60_rank_pct >= 0.80 and candidate_q_ret60_rank_pct >= 0.80,true,false,false
C_basis_top10,basis_risk_score_top_pct,basis_risk_score,top_pct,0.10,0.10,basis_risk_score >= p90,true,false,false
C_basis_top15,basis_risk_score_top_pct,basis_risk_score,top_pct,0.15,0.15,basis_risk_score >= p85,true,false,false
C_basis_top20,basis_risk_score_top_pct,basis_risk_score,top_pct,0.20,0.20,basis_risk_score >= p80,true,false,false
C_basis_top25,basis_risk_score_top_pct,basis_risk_score,top_pct,0.25,0.25,basis_risk_score >= p75,true,false,false
C_basis_top30,basis_risk_score_top_pct,basis_risk_score,top_pct,0.30,0.30,basis_risk_score >= p70,true,false,false
D_atr20_over_vol60_top20,volatility_contraction_descriptive,atr20_over_vol60,top_pct,0.20,0.20,atr20_over_vol60 >= p80,false,false,true
D_rank_spread_top20,volatility_contraction_descriptive,vol_expansion_rank_spread,top_pct,0.20,0.20,vol_expansion_rank_spread >= p80,false,false,true
```

Baseline：

```text
S0:
    suppressor_family = baseline
    suppressor_rule = keep_all
```

Primary high-vol extension score：

```text
S1: remove tail_risk_score top 10%
S2: remove tail_risk_score top 15%
S3: remove tail_risk_score top 20%
S4: remove tail_risk_score top 25%
S5: remove tail_risk_score top 30%
```

Single-feature ablation：

```text
A_VOL60_top10 / top20 / top30: remove q_vol60 top 10/20/30%
A_ATR20_top10 / top20 / top30: remove q_atr20 top 10/20/30%
A_RET60_top10 / top20 / top30: remove q_ret60 top 10/20/30%
A_EMA60_top10 / top20 / top30: remove q_ema60_dist top 10/20/30%
```

Logical interaction ablation：

```text
B_vol80_extension80:
    remove if candidate_vol_block_rank_pct >= 0.80 and candidate_extension_block_rank_pct >= 0.80
B_vol70_extension85:
    remove if candidate_vol_block_rank_pct >= 0.70 and candidate_extension_block_rank_pct >= 0.85
B_vol85_extension70:
    remove if candidate_vol_block_rank_pct >= 0.85 and candidate_extension_block_rank_pct >= 0.70
B_atr80_ema80:
    remove if candidate_q_atr20_rank_pct >= 0.80 and candidate_q_ema60_dist_rank_pct >= 0.80
B_vol60_80_ret60_80:
    remove if candidate_q_vol60_rank_pct >= 0.80 and candidate_q_ret60_rank_pct >= 0.80
```

Entry basis ablation：

```text
C_basis_top10 / top15 / top20 / top25 / top30:
    remove basis_risk_score top 10/15/20/25/30%
```

Volatility expansion / contraction descriptive ablation：

```text
D_atr20_over_vol60_top20:
    remove atr20_over_vol60 top 20%
D_rank_spread_top20:
    remove vol_expansion_rank_spread top 20%
```

任何额外 variant 必须标记：

```text
exploratory_only = true
excluded_from_primary_success_gate = true
```

## 7. 指标定义

### 7.1 四分组保留/删除

对每个 variant，必须输出：

```text
candidate_n_before
candidate_n_removed
candidate_n_after
right_clean_n_before
right_clean_n_removed
right_clean_n_after
right_clean_kept_rate = right_clean_n_after / right_clean_n_before
left_bad_n_before
left_bad_n_removed
left_bad_n_after
left_bad_removed_rate = left_bad_n_removed / left_bad_n_before
both_n_before
both_n_removed
both_n_after
both_removed_rate = both_n_removed / both_n_before
neither_n_before
neither_n_removed
neither_n_after
neither_removed_rate = neither_n_removed / neither_n_before
left_bad_removed_per_right_clean_removed = left_bad_n_removed / max(right_clean_n_removed, 1)
```

如果 `right_clean_n_removed = 0` 且 `left_bad_n_removed > 0`，必须另设：

```text
right_clean_removed_zero_flag = true
```

### 7.2 Tail / burden metrics

对每个 variant，必须输出：

```text
right_tail_event_50_n_after
left_tail_event_10_n_after
left_tail_event_20_n_after
p_candidate_50_after = right_tail_event_50_n_after / candidate_n_after
p_left_tail_10_after = left_tail_event_10_n_after / candidate_n_after
p_left_tail_20_after = left_tail_event_20_n_after / candidate_n_after
MAE_20_p10_after
MAE_20_p05_after
MFE_120_p90_after
fast_fail_rate_after = left_tail_event_10_n_after / candidate_n_after
candidate_per_winner_after = candidate_n_after / max(right_tail_event_50_n_after, 1)
```

`left_tail_event_20` 是 severe-left-tail sensitivity，不得用作 `fast_fail_rate_after`。

`MAE_worsening_after` 必须保留为 report-only descriptive metric，相对 19B eligible
universe baseline 定义：

```text
MAE_worsening_after = eligible_universe_MAE_20_p10 - candidate_kept_MAE_20_p10
```

其中 MAE 是负收益。若 eligible p10 = -0.087 且 kept candidate p10 = -0.150，则：

```text
MAE_worsening_after = -0.087 - (-0.150) = 0.063
```

如果 `MAE_worsening_after <= 0`，说明 kept candidate 的 p10 不比 eligible baseline 更差。
但 `MAE_worsening_after` 不进入 primary success gate，因为 B2 是高波动右尾突破族，
同时要求 `p_candidate_50_after >= 0.24` 和 `MAE_worsening_after <= 0.03` 会把
有效 suppressor 锁死为失败。

Primary burden-improvement gate 必须使用 S0 未过滤 B2 candidate baseline：

```text
S0_candidate_MAE_20_p10 =
    MAE_20_p10 of B2 primary candidate rows before any suppressor

MAE_20_p10_improvement_vs_S0 =
    MAE_20_p10_after - S0_candidate_MAE_20_p10
```

MAE 是负收益，所以 `MAE_20_p10_improvement_vs_S0 > 0` 表示 kept candidates 的左尾
p10 比未过滤 B2 更浅。Primary gate 使用：

```text
MAE_20_p10_improvement_vs_S0 >= 0.01
```

### 7.3 Common support 和 concentration

19B2 不把 common support 当作 primary suppressor 机制，但必须输出描述性审计：

```text
max_SMD_after
max_SMD_feature_after
SMD_match_market_cap_after
SMD_match_amount20_after
SMD_match_vol60_after
SMD_match_return20_after
top10_instrument_winner_share_after
top20_instrument_winner_share_after
winner_instrument_n_after
candidate_instrument_n_after
```

`max_SMD_after` 只能用于判断 suppressor 是否让 B2 candidate 更接近 eligible universe；
它不得替代 left_bad/right_clean 的 primary objective。

Support / SMD comparator contract：

```text
support_comparator_scope = eligible_universe_primary
support_comparator_rows =
    topn_executable_universe rows on the same decision_date set as B2 primary rows,
    after applying 19A executable universe flags and PIT feature availability
support_smd_features =
    match_market_cap
    match_amount20
    match_vol60
    match_return20
```

SMD 公式：

```text
SMD_feature_after =
    abs(mean(kept_candidate_feature) - mean(eligible_universe_feature))
    / pooled_std(kept_candidate_feature, eligible_universe_feature)
```

如果任一 comparator feature 无法从 PIT source 重建，`support_descriptive_gate` 必须为
`not_evaluable_missing_comparator_distribution`，并记录 `blocking_reason`；不得从 19B
`robustness_baseline_quality_audit.csv` 的空 `per_feature_smd_json = {}` 推断逐特征 SMD。

### 7.4 Bootstrap

Primary variants 必须按 `instrument_id` cluster bootstrap 输出：

```text
left_bad_removed_per_right_clean_removed_ci_low
left_bad_removed_per_right_clean_removed_ci_high
right_clean_kept_rate_ci_low
left_bad_removed_rate_ci_low
p_candidate_50_after_ci_low
MAE_20_p10_improvement_vs_S0_ci_low
MAE_20_p10_improvement_vs_S0_ci_high
MAE_worsening_after_ci_low
MAE_worsening_after_ci_high
```

Bootstrap 不得重新选择 variant 或 threshold；只对已冻结 variants 做不确定性读出。

## 8. 决策门禁

### 8.1 Gate 列表

`entry_universe_19b2_decision.csv` 必须输出以下 gates：

```text
config_contract_gate
input_artifact_gate
upstream_19a_contract_gate
upstream_19b0_contract_gate
upstream_19b_contract_gate
upstream_19b1_contract_gate
sample_support_gate
primary_row_join_gate
feature_pit_gate
rank_source_gate
score_contract_gate
variant_grid_gate
ablation_metric_gate
interaction_superiority_gate
policy_authorization_gate
output_contract_gate
```

### 8.2 Primary support gate

19B2 primary support 只允许从以下 variant family 判断：

```text
suppressor_family in {
    tail_risk_score_top_pct,
    logical_interaction,
    basis_risk_score_top_pct
}
exploratory_only = false
```

不能用 single-feature ablation、D 组 volatility contraction descriptive ablation 或
market/common-support 交互作为 primary support。

Primary support 通过条件：

```text
exists primary_variant such that:
    candidate_n_after >= kept_candidate_n_min
    right_tail_event_50_n_after >= kept_right_tail_event_50_n_min
    left_bad_removed_per_right_clean_removed >= 2.0
    MAE_20_p10_improvement_vs_S0 >= 0.01
    p_candidate_50_after >= 0.24
    right_clean_kept_rate >= 0.70
```

Interaction superiority 通过条件：

```text
best_primary_interaction_or_basis_variant.left_bad_removed_per_right_clean_removed
    >= best_budget_matched_single_feature_variant.left_bad_removed_per_right_clean_removed * 1.10
and
best_budget_comparison.efficiency_lift_pct_ci_low >= 0.00
```

Budget matched 的定义：

```text
abs(primary_variant.candidate_removed_rate - single_feature_variant.candidate_removed_rate) <= 0.05
```

如果没有 budget-matched single-feature variant，必须输出：

```text
interaction_superiority_gate = fail
blocking_reason = no_budget_matched_single_feature_comparator
```

### 8.3 Decision states

允许的决策状态：

```text
19B2_high_vol_extension_suppressor_ablation_supported_diagnostic
19B2_suppressor_improves_burden_but_not_interaction_supported_diagnostic
19B2_no_suppressor_pareto_improvement_diagnostic
19B2_config_contract_blocked
19B2_input_artifact_blocked
19B2_upstream_19b_contract_blocked
19B2_upstream_19b1_contract_blocked
19B2_sample_support_blocked
19B2_primary_row_join_blocked
19B2_feature_pit_contract_blocked
19B2_rank_source_blocked
19B2_score_contract_blocked
19B2_variant_grid_blocked
19B2_output_contract_blocked
```

状态规则：

```text
if any contract/input/upstream/sample/join/feature/rank/score/grid/output gate fails:
    use corresponding blocked state

else if primary support gate passes and interaction_superiority_gate passes:
    decision_state = 19B2_high_vol_extension_suppressor_ablation_supported_diagnostic

else if primary support gate passes and interaction_superiority_gate fails:
    decision_state = 19B2_suppressor_improves_burden_but_not_interaction_supported_diagnostic

else:
    decision_state = 19B2_no_suppressor_pareto_improvement_diagnostic
```

任何非 blocked 状态都必须保持：

```text
validation_outcome_read = false
next_allowed_requirement = none
max_ep19_terminal_state = 19_entry_universe_enrichment_only_diagnostic
19C_replay_authorized = false
EP20_policy_preflight_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

## 9. 输出合同

19B2 必须输出以下 artifact。

```text
entry_universe_19b2_decision.csv
input_artifact_audit.csv
upstream_contract_audit.csv
primary_row_join_audit.csv
rank_source_audit.csv
suppressor_feature_source_audit.csv
b2_pre_outcome_rank_panel.csv
b2_suppressor_score_panel.csv
suppressor_variant_grid.csv
suppressor_ablation_readout.csv
suppressor_budget_comparison_readout.csv
support_and_concentration_readout.csv
search_accounting_audit.csv
19B2_b2_high_vol_extension_left_tail_suppressor_ablation_report.md
19B2_handoff_contract.md
manifest_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.json
output_hashes_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.json
figures/suppressor_efficiency_frontier.png
figures/four_group_removed_rate_by_variant.png
figures/tail_risk_score_group_distribution.png
figures/mae_vs_right_tail_retention_frontier.png
```

### 9.1 `entry_universe_19b2_decision.csv`

Columns:

```text
run_id
created_at
requirement_file_hash
config_file_hash
input_artifact_hash_manifest
config_contract_gate
input_artifact_gate
upstream_19a_contract_gate
upstream_19b0_contract_gate
upstream_19b_contract_gate
upstream_19b1_contract_gate
sample_support_gate
primary_row_join_gate
feature_pit_gate
rank_source_gate
score_contract_gate
variant_grid_gate
ablation_metric_gate
interaction_superiority_gate
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
variant_n_total
variant_n_primary
best_variant_id
best_variant_family
best_variant_candidate_removed_rate
best_variant_left_bad_removed_per_right_clean_removed
best_variant_right_clean_kept_rate
best_variant_left_bad_removed_rate
best_variant_both_removed_rate
best_variant_p_candidate_50_after
best_variant_MAE_20_p10_improvement_vs_S0
best_variant_MAE_worsening_after
best_single_feature_variant_id
interaction_efficiency_lift_vs_single_feature
interaction_efficiency_lift_ci_low
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

### 9.2 `b2_pre_outcome_rank_panel.csv`

Pre-outcome rank panel. This is the authoritative source for all 19B2 scores. It must be
written before any outcome label join and must not contain forward labels. Columns:

```text
family_id
grid_cell_id
split
row_scope
row_key
instrument_id
decision_date
decision_month
rank_scope
rank_source_artifact
rank_cross_section_n
match_vol60
atr_20_pct_asof_decision_date
return_60d_asof_decision_date
close_to_ema60_asof_decision_date
q_vol60
q_atr20
q_ret60
q_ema60_dist
vol_block
extension_block
tail_risk_score
basis_risk_score
vol_expansion_rank_spread
atr20_over_vol60
candidate_vol_block_rank_pct
candidate_extension_block_rank_pct
candidate_q_atr20_rank_pct
candidate_q_ema60_dist_rank_pct
candidate_q_vol60_rank_pct
candidate_q_ret60_rank_pct
feature_pit_gate
rank_source_gate
pre_outcome_rank_panel_hash
blocking_reason
```

Forbidden columns:

```text
MFE_120
MAE_20
forward_mfe_*
forward_mae_*
forward_return_*
forward_big_winner_*
fast_fail_flag
false_repair_flag
right_tail_event_50
left_tail_event_10
left_tail_event_20
right_clean
left_bad
both
neither
outcome_group
```

### 9.3 `b2_suppressor_score_panel.csv`

Row-level score panel. Columns:

```text
family_id
grid_cell_id
split
row_scope
row_key
instrument_id
decision_date
decision_month
MFE_120
MAE_20
right_tail_event_50
left_tail_event_10
left_tail_event_20
outcome_group
match_vol60
atr_20_pct_asof_decision_date
return_60d_asof_decision_date
close_to_ema60_asof_decision_date
q_vol60
q_atr20
q_ret60
q_ema60_dist
vol_block
extension_block
tail_risk_score
basis_risk_score
vol_expansion_rank_spread
atr20_over_vol60
candidate_vol_block_rank_pct
candidate_extension_block_rank_pct
candidate_q_atr20_rank_pct
candidate_q_ema60_dist_rank_pct
candidate_q_vol60_rank_pct
candidate_q_ret60_rank_pct
rank_cross_section_n
rank_source_gate
feature_pit_gate
pre_outcome_rank_panel_hash
```

This file may contain 19B robustness outcome labels because 19B2 is a diagnostic readout.
It must never include validation outcome labels.

### 9.4 `suppressor_variant_grid.csv`

Columns:

```text
variant_id
suppressor_family
suppressor_rule
score_name
threshold_type
threshold_value
candidate_removed_target_pct
logical_condition
primary_success_eligible
exploratory_only
excluded_from_primary_success_gate
pre_registered_flag
blocking_reason
```

### 9.5 `suppressor_ablation_readout.csv`

Columns:

```text
variant_id
suppressor_family
primary_success_eligible
candidate_n_before
candidate_n_removed
candidate_n_after
candidate_removed_rate
right_clean_n_before
right_clean_n_removed
right_clean_n_after
right_clean_kept_rate
left_bad_n_before
left_bad_n_removed
left_bad_n_after
left_bad_removed_rate
both_n_before
both_n_removed
both_n_after
both_removed_rate
neither_n_before
neither_n_removed
neither_n_after
neither_removed_rate
left_bad_removed_per_right_clean_removed
right_clean_removed_zero_flag
right_tail_event_50_n_after
left_tail_event_10_n_after
left_tail_event_20_n_after
p_candidate_50_after
p_left_tail_10_after
p_left_tail_20_after
MAE_20_p10_after
MAE_20_p05_after
MFE_120_p90_after
S0_candidate_MAE_20_p10
MAE_20_p10_improvement_vs_S0
eligible_universe_MAE_20_p10
MAE_worsening_after
fast_fail_rate_after
candidate_per_winner_after
left_bad_removed_per_right_clean_removed_ci_low
left_bad_removed_per_right_clean_removed_ci_high
right_clean_kept_rate_ci_low
left_bad_removed_rate_ci_low
p_candidate_50_after_ci_low
MAE_20_p10_improvement_vs_S0_ci_low
MAE_20_p10_improvement_vs_S0_ci_high
MAE_worsening_after_ci_low
MAE_worsening_after_ci_high
primary_success_gate
diagnostic_only_flag
blocking_reason
```

### 9.6 `suppressor_budget_comparison_readout.csv`

Columns:

```text
primary_variant_id
primary_variant_family
single_feature_comparator_variant_id
candidate_removed_rate_abs_diff
primary_efficiency
single_feature_efficiency
efficiency_lift_abs
efficiency_lift_pct
efficiency_lift_pct_ci_low
efficiency_lift_pct_ci_high
primary_right_clean_kept_rate
single_feature_right_clean_kept_rate
primary_p_candidate_50_after
single_feature_p_candidate_50_after
primary_MAE_20_p10_improvement_vs_S0
single_feature_MAE_20_p10_improvement_vs_S0
primary_MAE_worsening_after
single_feature_MAE_worsening_after
budget_matched_flag
interaction_superiority_component_gate
blocking_reason
```

### 9.7 `support_and_concentration_readout.csv`

Columns:

```text
variant_id
support_comparator_scope
support_comparator_n
candidate_n_after
candidate_instrument_n_after
winner_instrument_n_after
max_SMD_after
max_SMD_feature_after
SMD_match_market_cap_after
SMD_match_amount20_after
SMD_match_vol60_after
SMD_match_return20_after
top10_instrument_winner_share_after
top20_instrument_winner_share_after
support_descriptive_gate
concentration_descriptive_gate
diagnostic_only_flag
blocking_reason
```

## 10. 报告要求

中文报告必须包含：

```text
1. 明确写出 19B2 是 diagnostic / ablation only。
2. 明确写出 validation outcome read = false。
3. 明确写出 19C replay authorized = false。
4. 明确写出 entry/exit/holding/portfolio/model/production/live trading authorization = false。
5. 复述 19B1 的四分组事实：
   right_clean = 290, left_bad = 614, both = 145, neither = 503。
6. 解释为什么 both 不能当成坏样本直接删除。
7. 解释 tail_risk_score 为什么使用乘法而不是简单相加。
8. 对比 primary interaction / basis score 与 single-feature ablation。
9. 给出 best variant 的 right_clean kept、left_bad removed、both removed、
   p_candidate_50_after、MAE_20_p10_improvement_vs_S0 和 report-only MAE_worsening_after。
10. 解释 common support / market state 为什么只是描述性审计，不是主 suppressor。
11. 如果支持门通过，只能写 non-executable next research suggestion；
    不得写可交易规则或策略授权。
```

报告必须包含以下原句：

```text
19B2 是 diagnostic-only suppressor ablation。
T0 suppressor ablation 不等于 alpha support。
validation outcome read = false。
19C replay authorized = false。
EP20 policy preflight authorized = false。
任何 delayed confirmation、entry timing 或 left-tail rejector model 都必须作为新的 pre-registered requirement。
```

## 11. Manifest 和 hash

`manifest_19b2...json` 必须记录：

```text
run_id
created_at
requirement_file
requirement_file_hash
config_file
config_file_hash
decision_state
primary_scope
primary_suppressor_feature_whitelist
score_contract
variant_grid_contract
pre_outcome_rank_panel_hash
input_artifact_hashes
required_outputs
output_hashes
authorization_state
```

`output_hashes_19b2...json` 必须覆盖所有 required outputs。规则：

```text
manifest.output_hashes excludes manifest and output_hashes
output_hashes includes manifest
output_hashes excludes output_hashes itself
```

如果 report 更新后 manifest 或 output_hashes 未同步，必须：

```text
decision_state = 19B2_output_contract_blocked
output_contract_gate = fail
```

## 12. 实现测试要求

测试文件必须至少覆盖：

```text
1. 19B / 19B1 upstream hash 和 authorization gates 全部闭合。
2. 只使用 B2 robustness candidate_primary_denominator rows。
3. right_clean / left_bad / both / neither 计数与 19B1 一致。
4. primary suppressor feature whitelist 与本 requirement 完全一致。
5. 19B / 19B1 output_hashes 中所有 artifact id 都按 Section 2.3 映射校验。
6. rank_source_gate 禁止 robustness-period rank 或 outcome-group rank fallback。
7. `b2_pre_outcome_rank_panel.csv` 不含任何 forbidden forward/outcome columns。
8. `b2_suppressor_score_panel.csv.pre_outcome_rank_panel_hash` 与 pre-outcome panel 一致。
9. score 公式逐列可复算。
10. variant grid 与本 requirement 完全一致，且所有额外 variant 都是 exploratory_only。
11. `fast_fail_rate_after = left_tail_event_10_n_after / candidate_n_after`。
12. B 组 logical interaction variants 必须使用 `candidate_*_rank_pct`，不得直接使用 universe-rank 绝对阈值。
13. `MAE_20_p10_improvement_vs_S0` 必须按 S0 未过滤 B2 candidate baseline 复算。
14. interaction superiority 必须同时满足点估计 lift 和 `efficiency_lift_pct_ci_low >= 0`。
15. single-feature ablation 不得单独触发 high-vol-extension supported decision。
16. both group 单独输出，不得并入 left_bad。
17. support/SMD comparator 使用 `eligible_universe_primary`，或明确 `not_evaluable_missing_comparator_distribution`。
18. validation / 19C / policy / trading authorization 全部为 false。
19. manifest.output_hashes 与 output_hashes 文件一致。
20. 中文报告包含所有 required boundary phrases。
```

推荐命令：

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/src/run_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/configs/config_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.yaml

python -m pytest topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight/tests/test_19b2_b2_high_vol_extension_left_tail_suppressor_ablation.py -q

git diff --check -- topics/02_AFML_BIG_WINNER/experiments/pending/19_entry_universe_pit_tradability_preflight
```

## 13. 失败解释

如果 19B2 不支持 high-vol-extension suppressor，不得简单写成 “B2 bad”。报告必须区分：

```text
1. suppressor 删除 left_bad 不够多；
2. suppressor 误杀 right_clean 太多；
3. MAE_20_p10 没有相对 S0 未过滤 B2 候选改善至少 1 个百分点；
4. p_candidate_50 掉回 eligible baseline 附近；
5. interaction score 没有以点估计和 bootstrap CI 同时优于 single-feature ablation；
6. both 被过度删除，说明问题可能更适合 exit / holding policy，而不是 entry suppressor；
7. common support 或 concentration 仍阻断，说明 B2 只能保留 morphology diagnostic 价值。
```

如果 19B2 支持 high-vol-extension suppressor，报告也必须写明：

```text
1. 这只是 robustness diagnostic，不是 validation support。
2. 该 suppressor 不能直接上线、不能直接进入 replay、不能直接生成交易规则。
3. 下一步如果要做 delayed confirmation，应只针对 high-risk bucket，而不是全体 B2 延迟。
4. 下一步如果要做 left-tail rejector model，必须先另开 requirement，并明确标签只使用
   left_bad vs right_clean，both 单独处理。
```
