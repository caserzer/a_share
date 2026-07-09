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

## 2. 上游合同

19B1 必须先验证 19A、19B0、19B 的闭包。任何合同不通过时必须 fail closed。

### 2.1 19A / 19B0 必需事实

19B1 至少必须读取并校验 19B 已经校验过的 19A / 19B0 contract artifacts：

```text
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/upstream_19a_contract_audit.csv
EXPERIMENT_ROOT/outputs/19B_robust_right_tail_enrichment_and_false_positive_burden_readout/upstream_19b0_contract_audit.csv
```

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
```

本 requirement 主要目标是 B2：

```text
family_id = B2_relative_strength_breakout
grid_cell_id = B2-relative-strength-breakout__182b3d0f30f5
19B cell_decision_state = false_positive_burden_blocked
```

B5 可作为 negative-control / contrast diagnostic，但不得用 B5 结果修改 B2 结论。

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
row_scope = candidate_primary_denominator
split = robustness
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

允许的 T0 特征包括但不限于：

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
decision_month
instrument_month only for cluster/accounting, not as separability feature
instrument_id only for cluster/accounting, not as separability feature
```

禁止的特征：

```text
forward_mfe_*
forward_mae_*
forward_return_*
forward_big_winner_*
fast_fail_flag
false_repair_flag
任何 entry 后价格、成交、收益、路径、未来窗口统计
任何 validation outcome
任何 post-hoc 由 left/right label 反推出来的特征
```

所有 feature source 必须输出到 `t0_feature_source_audit.csv`，记录：

```text
feature_name
source_artifact
source_columns
asof_rule
pit_safe_flag
missing_rate
used_in_primary_readout
blocking_reason
```

任一 primary feature 无法证明 PIT 安全，必须从 primary readout 中剔除。

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

### 7.2 T0 单变量差异

对每个允许的 T0 feature，至少计算：

```text
left_bad_n
right_clean_n
left_bad_mean / median / p25 / p75
right_clean_mean / median / p25 / p75
standardized_mean_difference
median_difference
Mann-Whitney U p-value
Kolmogorov-Smirnov p-value
feature_auc_for_left_bad_vs_right_clean
direction_for_left_bad
cluster_bootstrap_CI_for_median_difference
cluster_bootstrap_CI_for_auc
missing_rate_by_group
```

Multiple testing：

```text
primary_feature_family = all T0 features used in left_bad vs right_clean
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
```

输出：

```text
t0_multivariate_diagnostic_separability_readout.csv
```

如果实现者认为多变量 readout 会造成策略训练歧义，可以跳过，但必须在报告中说明：

```text
multivariate_diagnostic_skipped_reason
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

输出：

```text
t0_separability_stability_readout.csv
```

## 8. 判定规则

19B1 的 positive diagnostic 判定不能只靠单一 p-value。必须同时满足：

```text
sample_support_gate = pass
outcome_overlap_gate = pass
t0_feature_pit_gate = pass
primary_feature_separability_gate = pass
stability_gate = pass
policy_authorization_gate = pass
output_contract_gate = pass
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
    BH_FDR_adjusted_p <= 0.10
    abs(standardized_mean_difference) >= 0.20
    feature_auc_for_left_bad_vs_right_clean >= 0.57
    cluster_bootstrap_AUC_CI_low > 0.50
```

`stability_gate = pass` 条件：

```text
For at least 1 top feature:
    direction is stable in >= 70% leave-one-month-out folds
    direction remains same after top1/top3 instrument removal
```

`policy_authorization_gate = pass` 条件：

```text
all model/policy/backtest/deployment/trading authorization fields are false
```

允许 decision states：

```text
19B1_t0_left_right_tail_separable_diagnostic
19B1_t0_left_right_tail_not_separable_diagnostic
19B1_sample_support_blocked
19B1_t0_feature_pit_contract_blocked
19B1_upstream_contract_blocked
19B1_upstream_19b_contract_blocked
19B1_output_contract_blocked
```

不允许任何状态授权 replay、policy 或 live trading。

## 9. 必需输出

输出目录：

```text
EXPERIMENT_ROOT/outputs/19B1_t0_left_right_tail_separability_readout/
```

必需 CSV：

```text
input_artifact_audit.csv
upstream_contract_audit.csv
t0_feature_source_audit.csv
t0_feature_matrix_manifest.csv
outcome_left_right_overlap_readout.csv
t0_univariate_feature_separability_readout.csv
t0_multivariate_diagnostic_separability_readout.csv
t0_separability_stability_readout.csv
search_accounting_audit.csv
entry_universe_19b1_decision.csv
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
N_candidate_rows
N_instruments
N_t0_features_tested
feature_family_correction_method
secondary_comparisons_count
B5_negative_control_used
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
