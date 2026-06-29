# 需求：16X Payoff-aligned Continuation Label Power Precheck

## 0. 路径基线

本需求使用以下路径别名。别名由 runner 在当前 checkout 中解析，不得把作者机器绝对路径写入
config、manifest 或 publishable outputs：

```text
REPO_ROOT = current repository root
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0
SOURCE_EP16_ROOT = EXPERIMENT_ROOT
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status、required flag、lineage role。
5. 必需输入缺失、schema 不匹配、上游 ready 裁决不可证明、payoff target 血缘不可证明、feature contract 不可复现、effective-sample discipline 不可证明、search accounting 不可证明时一律 fail closed。
6. 不得从报告文本、图像、人工讨论、聚合 readout 反推逐行 step / feature / payoff / split boundary。

## 1. 实验身份

```text
experiment_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
phase_id = 16X
run_id = 16X_payoff_aligned_continuation_label_power_precheck
status = implemented_full_run_complete
requirement_file = requirement_16x_payoff_aligned_continuation_label_power_precheck.md
config_file = configs/config_16x_payoff_aligned_continuation_label_power_precheck.yaml
runner_file = src/run_16x_payoff_aligned_continuation_label_power_precheck.py
test_file = tests/test_16x_payoff_aligned_continuation_label_power_precheck.py
source_plan = EXPERIMENT_ROOT/research_plan.md
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

## 2. Non-negotiable Scope

16X 是 Episode 16 在 16E-postmortem 关闭 survival-score continuation-as-action 主线之后，作为
topic-level research direction restart 插入的**单一前置闸门（power precheck）**。它不是
16E-postmortem `next_allowed = none` 之后的 continuation mainline 授权阶段；它只在 16E-postmortem
裁决为：

```text
16E_postmortem_mainline_closed_no_path_supported
next_allowed_requirement = none
continuation_as_action_mainline_closed = true
```

时允许运行。

16E-postmortem 已经用定量证据证明：16D 的 survival/0-1 continuation score 在 train 上对 realized payoff 单调（Spearman 0.9030），但在 robustness 上 payoff 排序坍塌（Spearman 0.0303），即**分类概率与 payoff magnitude 在 OOS 上解耦**。16X 只回答一个、且只有一个问题：

```text
如果把 continuation target 从 survival 0/1 换成一个直接面向 realized h20 payoff severity 的目标，
在 16C 已冻结的 t0 feature contract 与 effective-sample discipline 下，
这个 payoff-aligned target 是否在 ROBUSTNESS（confirmatory split）上具备
"可被 t0 特征稳定 rank-排序" 的 separability power？
```

16X 是一个**功效预检**，不是 label 重做、不是建模部署、不是 policy。它只用最小成本判断"换目标函数"这条路是否值得投入完整的 16B′→16C′→16D′→16E′ 重链。

16X **不是**且**不授权**：

```text
new tradeable label deployment
new policy / action / threshold / defend rule
entry policy / exit policy / holding policy
return / cost / drawdown / PnL backtest
portfolio construction / position sizing / bet sizing
probability calibration / production signal / deployment / live trading
16D / 16E / 16F 或任何 chained / utility / transition 工作
```

16X 可以训练**固定规格、低容量、诊断用途**的 rank/regression 探针模型来回答上面的功效问题；任何 score、coefficient、feature importance 都不得被解释为可交易信号或被外推到部署。

若 16X 通过，最多只能授权后续新建**一个** payoff-aligned label 重做链的起点 requirement：

```text
requirement_16b2_payoff_aligned_continuation_label_design_diagnostic.md
```

若 16X 不通过，授权 `none`，并确认 continuation-as-action 主线保持关闭，建议回到 topic 级 research direction（entry alpha 等更上游瓶颈，参考 `research_direction_discussion_20260614.md`）。

## 3. Upstream Authorization Replay

16X 必须复验 16E-postmortem 的 mainline_closed 裁决，不得只读报告文本。

Required 16E-postmortem values (from publishable tables / manifest):

```text
decision_state = 16E_postmortem_mainline_closed_no_path_supported
next_allowed_requirement = none
continuation_as_action_mainline_closed = true
selected_path_id = none
directionality_gate = fail
train_monotonicity_spearman = 0.903030
robustness_monotonicity_spearman = 0.030303
robustness_non_monotone_flag = true
thick_tail_mismatch_flag = true
no_new_computation_gate = pass
```

Required upstream lineage (复验，不重算)：

```text
16E decision_state = 16E_utility_diagnostic_not_supported
16C decision_state = 16C_sequential_continuation_separability_ready_for_policy_preflight
16C primary_model_id = ridge_logistic_bar_state_v1
16C primary_model_feature_n (frozen feature contract count)
16B primary_label_id = continuation_survival_h20_no_deep_drawdown
16B selected_threshold_id = up50pct
16B primary_horizon_sessions = 20
```

If 16E-postmortem decision is NOT `16E_postmortem_mainline_closed_no_path_supported`, 16X must fail closed:

```text
upstream_postmortem_authorization_gate = fail
decision_state = 16X_payoff_precheck_blocked_by_input_or_lineage_failure
next_allowed_requirement = none
```

特别地：若 16E-postmortem 裁决为任何 path A/B/C authorized、low_power、或 blocked 状态，16X 均**不适用**，必须 fail closed。16X 只在主线被明确关闭之后才有资格运行。

## 4. Research Questions

16X answers five questions, all on the ROBUSTNESS confirmatory split as primary. Primary probe
universe is frozen as **binary rows only** (`is_binary_target == true`, `label_class in {positive, negative}`)
so the payoff probe and survival probe share the same training/evaluation universe and can reuse 16C's
train binary fold assignment. Neutral rows remain a required stress/readout population but cannot drive
path authorization.

```text
X-Q1. payoff target 血缘：能否在不重算价格、不重训 16C model、不改 split boundary 的前提下，
      仅从 16C panel 既有列派生一个 payoff-severity target，并证明其与 16B survival label 的关系可审计？

X-Q2. survival-vs-payoff 解耦复验：在 16C frozen feature space 上重训一个 survival 0/1 探针，
      是否在 robustness 上复现 16E-postmortem 的 payoff 排序坍塌（即 survival 探针 rank IC vs payoff 显著低于 train）？
      这是把 postmortem 的 root cause 在 feature 层再独立确认一次。

X-Q3. payoff separability power（核心）：在同一 frozen feature contract 下训练一个
      payoff-aligned rank/regression 探针，其对 realized payoff 的 rank-ordering 在 robustness 上是否
      显著优于 survival 探针、且跨 split 不坍塌？以 cluster-grouped CV rank IC、robustness rank IC、
      decile payoff monotonicity 度量。

X-Q4. 稳健性与功效边界：robustness 仅约 1,872 primary-probe binary steps、204 episode cluster。
      payoff separability 的 cluster-bootstrap CI 是否排除 0？effective sample 是否足以支撑判断，
      而不是 train-only 假象或单 split 噪声？

X-Q5. 是否授权 payoff-aligned label 重做链：综合 X-Q1..Q4，是否有结构性证据表明
      "payoff-aligned target 在 robustness 上具备可用的 rank separability"，从而值得投入完整重链？
```

Decision mapping of questions:

```text
若 X-Q1 失败（payoff 血缘不可审计）-> lineage failure，fail closed。
若 X-Q3 payoff robustness rank-separability gate 失败 -> 不授权重做链，主线保持关闭。
若 X-Q3 通过但 X-Q4 功效不足（CI 含 0 / effective sample 不足）-> low_power，不授权。
若 X-Q3 通过且 X-Q4 功效充分 -> 授权 payoff-aligned label 重做链起点。
X-Q2 是机制复验，不单独决定授权，但若 survival 探针在 train 也不单调，则 lineage 复核失败。
```

## 5. Allowed And Forbidden Work

16X may:

1. 复验 16E-postmortem mainline_closed 裁决与上游 16C/16B/16E lineage。
2. 读取 16C frozen feature panel、score panel 与 effective-sample lineage。
3. 从 16C panel 既有列派生一个 payoff-severity target（见 §7），并审计其血缘。
4. 在 16C frozen feature contract 上训练固定规格、低容量的 survival 探针与 payoff 探针。
5. 计算 cluster-grouped CV rank IC、robustness rank IC、decile payoff monotonicity、cluster-bootstrap CI。
6. 输出 payoff separability power gate 与功效 gate。
7. 在通过时授权至多一个 payoff-aligned label 重做链起点 requirement。

16X must not:

1. 重算任何价格、forward return、cost、drawdown、PnL（payoff target 必须从既有列纯算术派生）。
2. 重训或改变 16C primary model（16C model 只用于 X-Q2 survival 探针的 lineage 复验比对）；
   16X 自己的 survival/payoff 探针是新的固定规格诊断模型，但不得改变 16C feature contract、split boundary、effective-sample 去重。
3. 改变 16B label id、threshold id（up50pct）、horizon（20）、16C feature 列集合。
4. 定义任何 entry / exit / holding / defend / threshold action 规则。
5. 计算任何 utility / 收益 / 成本口径的裁决量。
6. 用 validation 选择模型、target、feature 或 gate cutoff；validation 仅 stress readout。
   robustness 是预注册 confirmatory split，可参与 power gate，但不得用于 target 设计或 cutoff 调参。
7. 把 payoff 探针 score 解释成可交易信号或外推到 16D+。
8. 直接授权 16B′/16C′/16D′/16E′ 链的下游 phase；16X 只授权重链的**起点** requirement。

## 6. Required Inputs

All required inputs must enter `input_artifact_audit.csv` with:

```text
artifact_key
resolved_path
row_count
sha256
schema_status
read_status
required_flag
lineage_role
blocking_reason
```

Missing or schema-failing required inputs fail closed.

### 6.1 16E-postmortem Inputs

```text
outputs/publishable/tables/16E_postmortem_continuation_utility_failure_decomposition/continuation_utility_failure_postmortem_decision.csv
outputs/publishable/tables/16E_postmortem_continuation_utility_failure_decomposition/score_bucket_monotonicity_readout.csv
outputs/manifests/16E_postmortem_continuation_utility_failure_decomposition_manifest.json
```

### 6.2 16C Frozen Feature / Score Lineage Inputs

```text
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/sequential_continuation_separability_decision.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/oos_separability_readout.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_contract.csv
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/t0_feature_panel.parquet
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/separability_score_panel.parquet
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/fold_assignment_panel.parquet
```

16C `t0_feature_panel.parquet` is the **only** allowed row-level source of frozen t0 feature values and
payoff-derivation base columns. 16C `t0_feature_contract.csv` is the **only** allowed source of the
probe feature whitelist. 16X must not infer features from all panel columns and must not rebuild the
panel or feature contract from raw prices.

If present, it may be used only after proving:

```text
row keys unique at step_id
cluster_split_bucket present with values in {train, robustness, validation}
feature whitelist = rows in t0_feature_contract.csv where allowed_primary_model_feature == true
feature whitelist count matches 16C primary_model_feature_n
all whitelisted feature columns are present in t0_feature_panel.parquet
no column with forbidden_as_model_feature == true appears in the probe feature matrix
payoff_base_column step_end_price_ratio_minus_one_for_label_rule is NOT in the probe feature matrix
survival label / payoff / future close / future outcome drawdown / split-boundary columns are NOT in the
  probe feature matrix; 16C-whitelisted historical rolling state features such as max_drawdown_20d/60d
  remain allowed only if allowed_primary_model_feature == true
payoff base column step_end_price_ratio_minus_one_for_label_rule present; payoff finite rates audited by split
survival label columns continuation_positive / continuation_negative / continuation_neutral present
is_binary_target / target_binary present; label_class may be a deterministic lineage-audited derivation
  from continuation_positive / continuation_negative / continuation_neutral
effective-sample keys (episode_cluster_id, instrument, step_index) present
fold_assignment_panel join is 1:1 on step_id for train primary_probe_universe rows
primary_probe_universe row counts reconcile to 16C binary target population, not the wider labelable population
```

If validation fails, fail closed.

### 6.3 16B Label Lineage Inputs (read-only)

```text
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/sequential_continuation_label_decision.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_base_rate_readout.csv
```

These pin the survival label id, threshold id, horizon, and effective sample sizes for inheritance.

## 7. Payoff-aligned Target Definition

16X must freeze the payoff target spec in config **before** any probe training, and derive it only by
pure arithmetic from existing 16C panel columns. No price recomputation.

Primary payoff target (graded severity, continuous):

```text
payoff_target_id = realized_h20_payoff_severity_v1
payoff_base_column = step_end_price_ratio_minus_one_for_label_rule
payoff_raw = step_end_price_ratio_minus_one_for_label_rule        (existing h20 realized return)
payoff_target = payoff_raw                                        (continuous payoff used for rank IC)
payoff_rank_target = within-split rank of payoff_raw              (for Spearman rank IC)
```

Secondary diagnostic target (graded ordinal severity bins, readout only):

```text
payoff_ordinal_target_id = realized_h20_payoff_tercile_v1
payoff_ordinal = split-local tercile of payoff_raw over primary_probe_universe rows {low, mid, high}
```

Survival probe target (for X-Q2 decoupling replay, reuses 16B survival label):

```text
survival_target_id = continuation_survival_h20_no_deep_drawdown
survival_target = target_binary (16B/16C frozen survival 0/1, defined only on primary_probe_universe)
```

Universe discipline:

```text
primary_probe_universe = rows with is_binary_target == true, derived label_class in {positive, negative},
  finite target_binary, and finite payoff_raw
neutral_rows = rows with continuation_neutral == true; used only for stress/readout, not for probe fitting,
  robustness gate, margin gate, or next_allowed decision
```

Payoff target lineage audit must prove:

```text
payoff_base_column sourced from 16C t0_feature_panel, not recomputed
payoff_raw equals step_end_qfq_close / step_start_qfq_close - 1 within tolerance
  (consistency check against existing close columns; NOT a new price computation,
   it is a lineage cross-check using existing columns)
payoff target is config-frozen before probe training
no_new_price_or_return_computed = true
```

If this cannot be proven:

```text
payoff_target_lineage_gate = fail
decision_state = 16X_payoff_precheck_blocked_by_input_or_lineage_failure
next_allowed_requirement = none
```

## 8. Probe Model Specification

Two probes, both fixed low-capacity diagnostic models, both on the 16C frozen feature whitelist and
primary_probe_universe.

```text
feature_contract = t0_feature_contract rows where allowed_primary_model_feature == true
feature_contract_n = 16C primary_model_feature_n
forbidden_feature_columns = any t0_feature_contract row where forbidden_as_model_feature == true
payoff_base_column / survival labels / future close columns / future outcome drawdown columns / split columns
  are forbidden as features; 16C-whitelisted historical rolling drawdown state features remain allowed
preprocessing = train-only fit, applied to robustness/validation (no leakage)
cv_scheme = episode_cluster_grouped CV over train primary_probe_universe rows
fold_source = 16C fold_assignment_panel; must join 1:1 on train primary_probe_universe step_id
robustness_split = confirmatory holdout, never used for fitting or tuning
validation_split = stress readout only

survival_probe:
  probe_id = survival_logistic_probe_v1
  target = survival_target (0/1)
  family = ridge logistic (fixed regularization, config-frozen)

payoff_probe:
  probe_id = payoff_rank_probe_v1
  target = payoff_target (continuous realized h20 payoff)
  family = ridge regression on payoff_raw (fixed regularization, config-frozen)
  primary metric = rank IC (Spearman) between probe score and payoff_raw
```

Probe hyperparameters must be config-frozen before training. They must not be tuned on robustness or
validation. Probe scores are diagnostic only.

```text
probe_spec_frozen = true
robustness_used_for_probe_tuning = false
validation_used_for_probe_tuning = false
```

If violated:

```text
search_accounting_gate = fail
decision_state = 16X_payoff_precheck_blocked_by_search_or_leakage
next_allowed_requirement = none
```

## 9. Power And Separability Formulae

Primary split for decision = robustness. Train is supporting readout. Validation is stress readout only.

### 9.1 Rank IC (X-Q2, X-Q3)

```text
For each probe and split:
  rank_ic_spearman = Spearman( probe_score, payoff_raw ) over primary_probe_universe rows of that split

For CV (train only):
  cv_rank_ic_median = median over episode_cluster_grouped CV folds of rank_ic_spearman
```

### 9.2 Decile Payoff Monotonicity (X-Q3)

```text
Bucket robustness primary_probe_universe rows into deciles by payoff_probe score (low -> high).
For each decile: mean payoff_raw.
payoff_decile_monotonicity_spearman = Spearman( decile_index, mean payoff_raw )
payoff_monotone_flag = payoff_decile_monotonicity_spearman >= +0.6
```

### 9.3 Cluster-bootstrap CI (X-Q4)

```text
cluster_bootstrap_rank_ic_ci_low / ci_high =
  episode-cluster-resampled bootstrap CI of robustness payoff_probe rank_ic_spearman
ci_excludes_zero_flag = cluster_bootstrap_rank_ic_ci_low > 0

bootstrap_cluster_key = episode_cluster_id
bootstrap_resample_n = 2000
bootstrap_ci_level = 0.95
bootstrap_random_seed = 20260629
bootstrap_resampling_unit = episode_cluster_id clusters, sampled with replacement;
  include all primary_probe_universe rows from each sampled cluster
invalid_bootstrap_resample = resample has <2 unique probe_score ranks or <2 unique payoff_raw ranks
valid_bootstrap_resample_n must be >= 0.95 * bootstrap_resample_n, else low_power
```

### 9.4 Decoupling Replay (X-Q2)

```text
survival_probe robustness rank_ic_spearman vs payoff_raw
payoff_probe   robustness rank_ic_spearman vs payoff_raw
decoupling_replay_flag = true if
  survival_probe train rank IC is materially positive (>= +0.10)
  AND survival_probe robustness rank IC collapses (< +0.05)
  i.e. independently reproduces 16E-postmortem decoupling on the feature side.
```

## 10. Support Gates

### 10.1 Hard Lineage Gates

```text
input_artifact_gate = pass
upstream_postmortem_authorization_gate = pass
upstream_16c_feature_contract_gate = pass
payoff_target_lineage_gate = pass
fold_assignment_join_gate = pass
no_new_computation_gate = pass
search_accounting_gate = pass
```

Any hard lineage fail maps to:

```text
16X_payoff_precheck_blocked_by_input_or_lineage_failure
```

except probe tuning / leakage violation, which maps to:

```text
16X_payoff_precheck_blocked_by_search_or_leakage
```

### 10.2 Power Gates

```text
train_primary_probe_step_n >= 10000
train_episode_cluster_n >= 200
robustness_primary_probe_step_n >= 1000
robustness_episode_cluster_n >= 100
robustness_payoff_finite_rate >= 0.99
train_cv_valid_fold_n >= 5
valid_bootstrap_resample_n >= 0.95 * bootstrap_resample_n
```

Validation:

```text
validation_primary_probe_step_n >= 300   (stress readout only, does not block)
```

If robustness power floor fails:

```text
decision_state = 16X_payoff_precheck_low_power
next_allowed_requirement = none
```

### 10.3 Payoff Separability Gates (primary, X-Q3 + X-Q4)

These are evaluated on robustness as confirmatory split:

```text
robustness_payoff_probe_rank_ic_spearman >= 0.06
payoff_monotone_flag == true
ci_excludes_zero_flag == true
robustness_payoff_probe_rank_ic_spearman > robustness_survival_probe_rank_ic_spearman + 0.03
cv_rank_ic_median (train, payoff probe) >= 0.06
```

预注册阈值说明：

```text
0.06 robustness rank IC 是一个故意保守的最低 separability floor，对应 ~1,872 primary-probe binary steps /
204 episode cluster 下勉强非平凡的 rank-ordering。它低于 train 期望，但必须 cluster-bootstrap CI 排除 0。
+0.03 是 payoff probe 必须显著超过 survival probe 的最小 margin，证明 "换 target" 确有增量。
```

If payoff separability gates pass and power gates pass:

```text
payoff_separability_gate = pass
```

If payoff separability gate fails while power gates pass:

```text
decision_state = 16X_payoff_precheck_not_supported
next_allowed_requirement = none
continuation_as_action_mainline_closed = true (remains closed)
```

If power gates fail (cannot estimate separability):

```text
decision_state = 16X_payoff_precheck_low_power
next_allowed_requirement = none
```

### 10.4 Search Accounting Gates

```text
payoff_target_id config-frozen before probe training
probe_spec_frozen = true
no_new_price_or_return_computed = true
no_16c_model_refit = true
feature_contract_unchanged = true
threshold_id_unchanged = true (up50pct)
horizon_unchanged = true (20)
validation_used_for_selection = false
robustness_used_as_confirmatory_gate = true
robustness_used_for_probe_tuning = false
```

Any violation maps to:

```text
16X_payoff_precheck_blocked_by_search_or_leakage
```

## 11. Outputs

All publishable tables under:

```text
outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/
```

Required publishable tables:

```text
input_artifact_audit.csv
upstream_postmortem_authorization_audit.csv
feature_contract_audit.csv
payoff_target_lineage_audit.csv
no_new_computation_audit.csv
probe_spec_audit.csv
survival_vs_payoff_rank_ic_readout.csv
payoff_decile_monotonicity_readout.csv
cluster_bootstrap_rank_ic_readout.csv
power_gate_audit.csv
search_accounting_audit.csv
payoff_aligned_label_power_precheck_decision.csv
```

Local cache (read-derived only):

```text
outputs/local_cache/16X_payoff_aligned_continuation_label_power_precheck/probe_score_panel.parquet
```

Report:

```text
outputs/publishable/reports/payoff_aligned_continuation_label_power_precheck_report.md
```

Manifest:

```text
outputs/manifests/16X_payoff_aligned_continuation_label_power_precheck_manifest.json
```

## 12. Required Table Schemas

### 12.1 `input_artifact_audit.csv`

```text
artifact_key
resolved_path
row_count
sha256
schema_status
read_status
required_flag
lineage_role
blocking_reason
```

### 12.2 `upstream_postmortem_authorization_audit.csv`

```text
upstream_source
expected_decision_state
observed_decision_state
expected_next_allowed_requirement
observed_next_allowed_requirement
expected_continuation_as_action_mainline_closed
observed_continuation_as_action_mainline_closed
expected_directionality_gate
observed_directionality_gate
expected_no_new_computation_gate
observed_no_new_computation_gate
train_monotonicity_spearman
robustness_monotonicity_spearman
upstream_postmortem_authorization_gate
blocking_reason
```

### 12.3 `feature_contract_audit.csv`

```text
feature_contract_source
feature_contract_n_expected
feature_contract_n_actual
allowed_primary_model_feature_n
forbidden_as_model_feature_n
missing_feature_column_n
forbidden_feature_used_n
payoff_base_column_used_as_feature
label_or_future_column_used_as_feature_n
feature_contract_gate
blocking_reason
```

### 12.4 `payoff_target_lineage_audit.csv`

```text
payoff_target_id
payoff_base_column
payoff_raw_vs_close_ratio_abs_diff_max
payoff_finite_rate_train
payoff_finite_rate_robustness
payoff_finite_rate_validation
primary_probe_universe
train_primary_probe_step_n
robustness_primary_probe_step_n
validation_primary_probe_step_n
neutral_rows_excluded_from_primary_gate
config_frozen_before_training
no_new_price_or_return_computed
payoff_target_lineage_gate
blocking_reason
```

### 12.5 `no_new_computation_audit.csv`

```text
check_id
source_artifact_key
source_columns
allowed_transform_type
creates_new_price_or_return_cost_or_drawdown
recomputes_price
recomputes_forward_return
recomputes_cost
recomputes_drawdown
no_new_computation_gate
blocking_reason
```

### 12.6 `probe_spec_audit.csv`

```text
probe_id
target_id
family
regularization
feature_contract_source
feature_contract_n
primary_probe_universe
train_primary_probe_step_n
preprocessing_train_only
cv_scheme
fold_source
fold_assignment_join_gate
probe_spec_frozen
robustness_used_for_probe_tuning
validation_used_for_probe_tuning
blocking_reason
```

### 12.7 `survival_vs_payoff_rank_ic_readout.csv`

```text
split_bucket
probe_id
target_id
primary_probe_step_n
episode_cluster_n
rank_ic_spearman
cv_rank_ic_median
rank_ic_status
```

### 12.8 `payoff_decile_monotonicity_readout.csv`

```text
split_bucket
decile_index
row_n
mean_payoff_raw
mean_probe_score
payoff_decile_monotonicity_spearman
payoff_monotone_flag
```

### 12.9 `cluster_bootstrap_rank_ic_readout.csv`

```text
split_bucket
probe_id
rank_ic_spearman
cluster_bootstrap_rank_ic_ci_low
cluster_bootstrap_rank_ic_ci_high
bootstrap_ci_level
ci_excludes_zero_flag
bootstrap_resample_n
valid_bootstrap_resample_n
invalid_bootstrap_resample_n
bootstrap_cluster_key
bootstrap_random_seed
```

### 12.10 `power_gate_audit.csv`

```text
train_primary_probe_step_n
train_episode_cluster_n
robustness_primary_probe_step_n
robustness_episode_cluster_n
validation_primary_probe_step_n
robustness_payoff_finite_rate
train_cv_valid_fold_n
bootstrap_resample_n
valid_bootstrap_resample_n
invalid_bootstrap_resample_n
power_gate
low_power_reason
blocking_reason
```

### 12.11 `search_accounting_audit.csv`

```text
payoff_target_id
payoff_target_config_frozen_before_training
probe_spec_frozen_before_training
no_new_price_or_return_computed
no_16c_model_refit
feature_contract_unchanged
threshold_id_unchanged
horizon_unchanged
validation_used_for_selection
robustness_used_as_confirmatory_gate
robustness_used_for_probe_tuning
search_accounting_gate
blocking_reason
```

### 12.12 `payoff_aligned_label_power_precheck_decision.csv`

```text
decision_state
next_allowed_requirement
upstream_postmortem_decision_state
payoff_target_id
feature_contract_n
primary_probe_universe
train_primary_probe_step_n
robustness_primary_probe_step_n
validation_primary_probe_step_n
robustness_survival_probe_rank_ic_spearman
robustness_payoff_probe_rank_ic_spearman
payoff_minus_survival_rank_ic_margin
cv_payoff_rank_ic_median
payoff_monotone_flag
cluster_bootstrap_rank_ic_ci_low
cluster_bootstrap_rank_ic_ci_high
ci_excludes_zero_flag
bootstrap_resample_n
valid_bootstrap_resample_n
decoupling_replay_flag
payoff_separability_gate
power_gate
search_accounting_gate
upstream_postmortem_authorization_gate
feature_contract_gate
payoff_target_lineage_gate
continuation_as_action_mainline_closed
payoff_aligned_label_redo_authorized
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
chained_simulation_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

## 13. Decision Map

Final decision enum:

```text
16X_payoff_precheck_payoff_aligned_label_redo_authorized
16X_payoff_precheck_not_supported
16X_payoff_precheck_low_power
16X_payoff_precheck_blocked_by_input_or_lineage_failure
16X_payoff_precheck_blocked_by_search_or_leakage
```

Decision logic:

```text
all branches inherit:
  continuation_as_action_mainline_closed = true

if any forbidden recomputation / refit / leakage / probe tuning on OOS:
  decision_state = 16X_payoff_precheck_blocked_by_search_or_leakage
  next_allowed_requirement = none

elif any hard lineage gate fails:
  decision_state = 16X_payoff_precheck_blocked_by_input_or_lineage_failure
  next_allowed_requirement = none

elif robustness power gates fail (cannot estimate separability):
  decision_state = 16X_payoff_precheck_low_power
  next_allowed_requirement = none

elif payoff_separability_gate fails:
  decision_state = 16X_payoff_precheck_not_supported
  next_allowed_requirement = none
  continuation_as_action_mainline_closed = true

else:
  decision_state = 16X_payoff_precheck_payoff_aligned_label_redo_authorized
  next_allowed_requirement = requirement_16b2_payoff_aligned_continuation_label_design_diagnostic.md
  payoff_aligned_label_redo_authorized = true
  continuation_as_action_mainline_closed = true
```

Regardless of decision:

```text
continuation_as_action_mainline_closed = true
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
chained_simulation_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

16X 至多授权写一个 payoff-aligned label 重做链的**起点** requirement。即使 16X 通过，被重新打开的也不是
survival-score continuation-as-action 主线，而只是 topic-level research direction restart 下的一条 label
重做调查链；16X 绝不授权任何 utility / policy / chained / entry / deployment / live trading 工作。

## 14. Report Requirements

The Chinese report must include:

1. 单行 decision and next allowed requirement。
2. 16E-postmortem mainline_closed 复验与关键数字（train Spearman 0.9030 / robustness 0.0303 / directionality fail）。
3. payoff target 定义与血缘（从既有列纯算术派生，未重算价格）。
4. feature contract 白名单审计：特征只来自 `t0_feature_contract.csv` 中
   `allowed_primary_model_feature == true` 的行，不得从 `t0_feature_panel.parquet` 全列推断。
5. primary probe universe：只用 binary rows；neutral rows 只能作为 stress/readout，不参与 fitting、
   robustness gate、margin gate 或授权裁决。
6. probe 规格冻结（survival 探针 + payoff 探针，16C frozen feature whitelist）。
7. X-Q2 survival-vs-payoff 解耦复验：feature 层是否独立复现 OOS payoff 排序坍塌。
8. X-Q3 payoff separability：robustness rank IC、cv rank IC、decile payoff monotonicity。
9. X-Q4 功效：cluster-bootstrap CI 是否排除 0、effective sample 是否充分，并披露
   bootstrap_cluster_key、bootstrap_resample_n、valid_bootstrap_resample_n、bootstrap_ci_level、bootstrap_random_seed。
10. payoff probe 是否显著优于 survival probe（margin）。
11. Search accounting：无价格重算、无 16C refit、无 OOS 调参。
12. Findings and insight：是否值得投入 payoff-aligned label 重做链，或主线保持关闭。

Report must explicitly state:

```text
16X is a power precheck only. It computes no returns/cost/drawdown beyond lineage cross-checks,
refits no 16C model, defines no policy, and authorizes at most one payoff-aligned label redesign
requirement. It does not authorize entry, exit, holding, utility, chained simulation, deployment,
or live trading.
```

## 15. Manifest Requirements

```text
experiment_id
phase_id
run_id
created_at
requirement_path
requirement_sha256
config_path
config_sha256
upstream_postmortem_decision
payoff_target_id
feature_contract_source
feature_contract_n
primary_probe_universe
train_primary_probe_step_n
robustness_primary_probe_step_n
validation_primary_probe_step_n
bootstrap_cluster_key
bootstrap_resample_n
valid_bootstrap_resample_n
bootstrap_ci_level
bootstrap_random_seed
decision_state
next_allowed_requirement
payoff_aligned_label_redo_authorized
continuation_as_action_mainline_closed
robustness_payoff_probe_rank_ic_spearman
cluster_bootstrap_rank_ic_ci_low
authorization_booleans
input_artifact_hashes
output_hashes
row_counts
large_artifact_policy
```

## 16. Implementation Pattern

Implementation should remain experiment-local and may reuse existing runners via importlib:

```text
16C runner helpers for path resolution, hashing, feature contract, fold assignment, and metrics
16E-postmortem runner helpers for upstream replay and no-new-computation audit pattern
```

No shared-package refactor is required.

16X 只读 16C frozen feature panel、16E-postmortem decision 与 16B label decision。它不得调用 16C / 16D / 16E
的 full mode，不得写入上游任何 publishable / cache / manifest artifact。它只写自己的 16X 目录。
新的 probe 模型是 16X 本地诊断模型，不得污染或替换 16C primary model。

Large panels stored as local parquet. Publishable tables remain small aggregate readouts.

## 17. Test Plan

```text
test_postmortem_mainline_closed_required_for_16x
test_postmortem_other_decisions_fail_closed
test_16c_feature_contract_required_and_must_validate
test_feature_contract_audit_excludes_forbidden_and_payoff_columns
test_primary_probe_universe_binary_rows_only
test_neutral_rows_stress_only_not_used_for_authorization
test_fold_assignment_join_matches_train_primary_probe_universe
test_payoff_target_derived_from_existing_columns_only
test_payoff_raw_matches_close_ratio_within_tolerance
test_no_new_price_or_return_computed
test_no_16c_model_refit
test_feature_contract_unchanged_and_threshold_horizon_frozen
test_probe_spec_frozen_before_training
test_probe_not_tuned_on_robustness_or_validation
test_survival_probe_decoupling_replay_flag
test_payoff_probe_rank_ic_computed_on_cluster_grouped_cv
test_decile_payoff_monotonicity
test_cluster_bootstrap_ci_excludes_zero_flag
test_bootstrap_spec_seed_ci_and_resample_count_frozen
test_payoff_separability_gate_requires_margin_over_survival
test_robustness_is_primary_validation_is_stress_only
test_power_gate_failure_maps_to_low_power
test_separability_failure_maps_to_not_supported_mainline_stays_closed
test_pass_authorizes_only_payoff_label_redo_requirement
test_all_trading_utility_and_deployment_authorizations_false
test_all_required_publishable_outputs_have_declared_schema
test_decision_map_search_or_leakage
test_decision_map_lineage_failure
test_decision_map_low_power
test_decision_map_not_supported
test_decision_map_redo_authorized
test_manifest_contains_input_hashes_and_report_hash
test_16x_does_not_write_upstream_artifacts
```

## 18. Validation Commands

From `topics/02_AFML_BIG_WINNER`:

```bash
python -m py_compile experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16x_payoff_aligned_continuation_label_power_precheck.py
python -m pytest experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/tests/test_16x_payoff_aligned_continuation_label_power_precheck.py -q
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16x_payoff_aligned_continuation_label_power_precheck.py --mode check-inputs
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16x_payoff_aligned_continuation_label_power_precheck.py --mode full
git diff --check
```

After full run, confirm no 16C / 16D / 16E / 16E-postmortem publishable, cache, or manifest artifact was modified.

## 19. Expected Caveats To Carry Forward

```text
16B soft_overlap_partial_coverage_caveat = true
16B known_failed_context_exposure_caveat = true
16C neutral_population_caveat = true
16C validation_stress_evaluable = true but validation is not a selection split
16C effective-sample discipline inherited (anchor is not an independent sample unit)
16D robustness defense rate coverage caveat = true
16E drawdown_reduction_only_return_not_supported interpretation inherited
16E-postmortem survival-vs-payoff OOS decoupling (robustness Spearman 0.0303) is the motivating fact
```

## 20. Boundary Restatement

```text
16X 是一个 payoff-aligned target 的 robustness rank-separability 功效预检。
它在 16E-postmortem 关闭主线之后，用最小成本判断 "换目标函数到 payoff-severity" 是否值得投入完整重链。
它绝不重算价格 / return / cost / drawdown，绝不 refit 16C model，绝不定义 policy / utility / action，
绝不授权 16D+ / chained / entry / exit / holding / portfolio / deployment / live trading。
它至多授权一个 payoff-aligned label 重做链的起点 requirement，或确认主线保持关闭。
```
