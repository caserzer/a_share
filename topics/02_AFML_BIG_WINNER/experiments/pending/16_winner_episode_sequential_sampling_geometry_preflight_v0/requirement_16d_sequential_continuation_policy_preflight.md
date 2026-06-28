# 需求：16D Sequential Continuation Policy Preflight

## 0. Non-negotiable Scope

16D 是 Episode 16 第四个 phase。它只在 16C 裁决为：

```text
16C_sequential_continuation_separability_ready_for_policy_preflight
next_allowed_requirement = requirement_16d_sequential_continuation_policy_preflight.md
```

时允许运行。

16D 的任务是把 16C 已证明可分的 t0-observable continuation score，转换成一个**可审计的、train-frozen 的 continuation / defense action rule preflight**。它只回答：

```text
在已经处于 16B materialized sequential step universe 的条件下，
16C score 是否能定义一个稳定、不过度牺牲 positive continuation、
且不只依赖 known-failed context 的 defend-vs-continue 候选规则？
```

16D 仍然不是：

```text
entry policy
exit policy
holding policy
return / PnL / alpha backtest
cost model
position sizing
portfolio construction
production signal
```

16D 可以定义 `candidate_policy_id`，但这个 policy 只是 label-action preflight。任何 `defend_next_h20` / `continue_next_h20` action 都是 counterfactual diagnostic label action，不是实际卖出、买入、减仓、持仓或交易建议。

若 16D 通过，最多只能授权后续新建：

```text
requirement_16e_sequential_continuation_utility_diagnostic.md
```

16E 仍需重新冻结 utility, return, cost, execution, and deployment boundaries。16D 不得提前计算收益或成本。

## 1. Identity

```text
experiment_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
phase_id = 16D
run_id = 16D_sequential_continuation_policy_preflight
requirement_file = requirement_16d_sequential_continuation_policy_preflight.md
config_file = configs/config_16d_sequential_continuation_policy_preflight.yaml
runner_file = src/run_16d_sequential_continuation_policy_preflight.py
test_file = tests/test_16d_sequential_continuation_policy_preflight.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

## 2. Upstream Authorization Replay

16D 必须复验 16C 的 ready 裁决，不得只读报告文本。

Required 16C values:

```text
decision_state = 16C_sequential_continuation_separability_ready_for_policy_preflight
next_allowed_requirement = requirement_16d_sequential_continuation_policy_preflight.md
primary_label_id = continuation_survival_h20_no_deep_drawdown
selected_threshold_id = up50pct
primary_horizon_sessions = 20
primary_model_id = ridge_logistic_bar_state_v1
train_binary_step_n = 14962
train_positive_n = 10078
train_negative_n = 4884
train_episode_cluster_n = 652
robustness_binary_step_n = 1872
robustness_positive_n = 1346
robustness_negative_n = 526
robustness_episode_cluster_n = 204
primary_model_feature_n = 27
train_feature_complete_rate = 1.0
robustness_feature_complete_rate = 1.0
episode_cluster_grouped_cv_valid_fold_n = 5
episode_cluster_grouped_cv_median_roc_auc = 0.675971
episode_cluster_grouped_cv_median_pr_auc_lift_vs_binary_base = 0.122421
instrument_purged_chronological_cv_valid_fold_n = 5
instrument_purged_chronological_cv_median_roc_auc = 0.646587
robustness_roc_auc = 0.672220
robustness_pr_auc_lift_vs_binary_base = 0.099183
robustness_cluster_bootstrap_auc_ci_low = 0.647004
known_failed_context_independence_gate = pass
validation_stress_evaluable = true
soft_overlap_partial_coverage_caveat = true
known_failed_context_exposure_caveat = true
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
```

Required 16C hard gates:

```text
input_artifact_gate = pass
upstream_16b_authorization_gate = pass
step_label_binding_gate = pass
feature_contract_gate = pass
feature_lineage_gate = pass
feature_coverage_gate = pass
feature_leakage_gate = pass
pit_context_feature_gate = pass
qfq_feature_source_gate = pass
preprocessing_train_only_gate = pass
cv_fold_assignment_gate = pass
known_failed_context_rebuild_gate = pass
search_accounting_gate = pass
cv_power_gate = pass
train_cv_separability_gate = pass
robustness_separability_gate = pass
```

If any required value cannot be proven from publishable 16C tables and manifest, 16D must fail closed:

```text
upstream_16c_authorization_gate = fail
decision_state = 16D_policy_preflight_blocked_by_input_or_lineage_failure
next_allowed_requirement = none
```

## 3. Research Questions

16D answers five questions.

```text
Q1. Can the 16C frozen score be deterministically rebuilt without using 16C local cache
    as a required source?

Q2. Can a train-frozen score threshold define a nontrivial defend-vs-continue
    candidate policy without validation/robustness selection?

Q3. Does the primary policy capture enough negative continuation windows while
    not sacrificing too many positive continuation windows?

Q4. Does the policy remain evaluable and directionally supported in robustness,
    and is validation only a stress readout?

Q5. Is the policy signal still present outside known-failed episode context,
    rather than merely reusing late-rescue / mixed-path morphology?
```

If Q1 fails, it is lineage failure. If Q2 fails, it is low-power or degenerate policy. If Q3/Q4 fail, policy preflight is not supported. If Q5 fails, it is context-concentrated only and cannot authorize 16E.

## 4. Allowed And Forbidden Work

16D may:

1. Rebuild the 16C primary score using the 16C frozen feature contract, model registry, preprocessing policy, and train-only fit.
2. Freeze score thresholds using train split only.
3. Materialize diagnostic actions:
   `defend_next_h20` and `continue_next_h20`.
4. Evaluate action-vs-label confusion against the 16B continuation label.
5. Report binary positive/negative tradeoff, neutral handling, known-failed context stratification, and validation stress behavior.
6. Define a next-phase question for utility diagnostics if all gates pass.

16D must not:

1. Use forward returns beyond the already materialized 16B label fields.
2. Compute PnL, gross return, net return, transaction cost, slippage, drawdown utility, Sharpe, CAGR, turnover cost, or portfolio allocation.
3. Define an entry rule or select stocks to buy.
4. Treat `defend_next_h20` as a real exit, sell, hedge, stop, or position-size instruction.
5. Optimize thresholds on validation or robustness.
6. Search over model families, hyperparameters, feature subsets, label horizons, thresholds, or objective functions.
7. Use 15B path taxonomy, known_failed family, episode future geometry, label outcome, split identity, or step_end fields as model features.
8. Convert neutral rows into negatives.
9. Use local cache as the only row-level source in a fresh checkout.

## 5. Required Inputs

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
```

Missing or schema-failing required inputs fail closed.

### 5.1 16C Publishable Inputs

16D must read the following publishable 16C artifacts:

```text
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/sequential_continuation_separability_decision.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/upstream_16b_authorization_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/step_label_binding_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_contract.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_lineage_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_coverage_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_leakage_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/separability_training_universe_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/separability_fold_assignment_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/separability_model_registry.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/grouped_cv_separability_readout.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/oos_separability_readout.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/known_failed_context_rebuild_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/known_failed_context_stratified_separability_readout.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/neutral_population_audit.csv
outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/search_accounting_audit.csv
outputs/manifests/16C_sequential_continuation_separability_diagnostic_manifest.json
```

`separability_score_sample.csv.gz` is required only as a publishable score-format readout and hash lineage sample. It must not be treated as a full row-level source.

### 5.2 16B Row-level Label Inputs And Rebuild Contract

16D requires the full 16B row-level continuation label panel. The local parquet is an `optional_cache`, not a required source:

```text
outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/continuation_label_step_panel.parquet
```

16D must also read the 16B publishable lineage tables below:

```text
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_base_rate_readout.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/sequential_continuation_label_decision.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/step_materialization_audit.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/step_lineage_adapter_audit.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/qfq_price_source_audit.csv
outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/known_failed_overlap_readout.csv
outputs/manifests/16B_sequential_continuation_label_design_diagnostic_manifest.json
```

16D must be runnable from a fresh checkout where local parquet caches are absent. Therefore the 16B runner and config are required rebuild inputs:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/configs/config_16b_sequential_continuation_label_design_diagnostic.yaml
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16b_sequential_continuation_label_design_diagnostic.py
```

If the local label cache exists, 16D may use it only after proving:

```text
cache row keys are unique
cache row counts match 16B publishable split/base-rate counts
cache label counts match continuation_label_base_rate_readout.csv
cache threshold_id == up50pct
cache horizon_sessions == 20
cache label_id == continuation_survival_h20_no_deep_drawdown
cache manifest lineage is consistent with the current 16B manifest
```

If the local label cache is missing or fails validation, 16D must rebuild it by importing the 16B runner and replaying the 16B label materialization contract. It must fail closed if the runner/config is missing or the rebuild cannot reproduce the required 16B publishable counts. It must not continue with sampled rows or aggregate-only 16B tables.

### 5.3 Required Feature Sources For Score Rebuild

16D must be able to rebuild the 16C primary score without relying on 16C local score or feature caches. The required raw feature sources are the same as 16C:

```text
stock_daily_qfq_dir = data/raw/akshare/day/qfq
pit_executable_daily = data/processed/universe/pit_topn_400_100_executable_daily.csv
pit_membership_daily = data/processed/universe/pit_topn_400_100_membership_daily.csv
```

The 16C runner and config are required score-rebuild inputs:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/configs/config_16c_sequential_continuation_separability_diagnostic.yaml
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16c_sequential_continuation_separability_diagnostic.py
```

The feature contract, as-of policy, board bucket enum, missing policy, and train-only preprocessing must match 16C exactly. Any drift is a hard fail:

```text
feature_contract_replay_gate = fail
decision_state = 16D_policy_preflight_blocked_by_input_or_lineage_failure
```

16D must rebuild scores for:

```text
model_id = ridge_logistic_bar_state_v1
row population = 16B materialized h20 step universe with 16C feature contract applied
score orientation = higher score means continuation_positive
```

The score rebuild must replay 16C train and robustness AUC within tolerance and must additionally replay validation AUC as a non-selection lineage check.

### 5.4 16C Optional Local Caches

The following 16C local caches may be used only as acceleration:

```text
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/t0_feature_panel.parquet
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/separability_score_panel.parquet
outputs/local_cache/16C_sequential_continuation_separability_diagnostic/fold_assignment_panel.parquet
```

If used, 16D must validate:

```text
cache row keys match rebuilt row keys
cache model_id == ridge_logistic_bar_state_v1
cache score orientation matches 16C score orientation
cache split counts match 16C decision counts
cache OOS metrics replay within tolerance
```

If used, the cache must be checked against rebuilt row keys and replayed metrics:

```text
score_row_key_match_status = exact
score_abs_diff_max <= 1e-10 when deterministic rebuild is available
score_spearman_corr_vs_cache >= 0.999999 when floating-point solver drift prevents exact equality
auc_abs_delta_train <= 1e-6
auc_abs_delta_robustness <= 1e-6
auc_abs_delta_validation <= 1e-6
```

If validation fails, implementation must discard or fail the cache. It must not let an inconsistent cache drive the policy preflight.

### 5.5 Row-level Known-failed Context Inputs

16D context stratification requires row-level context flags. Aggregate 16B/16C readouts are insufficient.

Required 15B rebuild inputs:

```text
experiments/pending/15_path_defined_winner_episode_label_v0/configs/config_15b_winner_path_shape_taxonomy_diagnostic.yaml
experiments/pending/15_path_defined_winner_episode_label_v0/src/run_15b_winner_path_shape_taxonomy_diagnostic.py
experiments/pending/15_path_defined_winner_episode_label_v0/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_feature_definition_audit.csv
experiments/pending/15_path_defined_winner_episode_label_v0/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_rule_audit.csv
experiments/pending/15_path_defined_winner_episode_label_v0/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/winner_episode_cluster_membership_audit.csv
experiments/pending/15_path_defined_winner_episode_label_v0/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/path_shape_taxonomy_readout.csv
experiments/pending/15_path_defined_winner_episode_label_v0/outputs/publishable/tables/15B_winner_path_shape_taxonomy_diagnostic/representative_anchor_audit.csv
```

Optional row-level acceleration caches:

```text
outputs/local_cache/16B_sequential_continuation_label_design_diagnostic/known_failed_overlap_panel.parquet
experiments/pending/15_path_defined_winner_episode_label_v0/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/taxonomy_assignment_panel.parquet
experiments/pending/15_path_defined_winner_episode_label_v0/outputs/local_cache/15B_winner_path_shape_taxonomy_diagnostic/anchor_path_shape_feature_panel.parquet
```

16D must first prove that the 15B rule audit and feature-definition audit are sufficient to deterministically rebuild every required 15B `path_type` branch. If the rule audit is underspecified, set:

```text
known_failed_context_rebuild_gate = fail_rule_underspecified
decision_state = 16D_policy_preflight_blocked_by_input_or_lineage_failure
```

The rebuilt row-level context must replay 16B and 16C aggregate context readouts within tolerance. If optional caches are used, they must match the rebuilt context keys and aggregate counts. Required context flags are:

```text
late_rescue_context = cluster_failed_anchor_share for late_rescue_winner >= 0.50
known_failed_context_any = max cluster_failed_anchor_share across known-failed families >= 0.50
non_late_rescue_context = not late_rescue_context
non_known_failed_context = not known_failed_context_any
```

## 6. Primary Policy Definition

16D defines a train-frozen score-to-action rule.

Score orientation:

```text
primary_score = P(continuation_positive = true | t0 features)
higher score means more likely to survive the next h20 window without deep drawdown
lower score means more defense-worthy
```

Score orientation is not allowed to be auto-flipped in 16D. The machine check is:

```text
train_roc_auc(primary_score, continuation_positive) > 0.50
robustness_roc_auc(primary_score, continuation_positive) > 0.50
train_bottom30_defense_precision_lift_vs_binary_negative_base > 0
robustness_bottom30_defense_precision_lift_vs_binary_negative_base > 0
score_sign_flipped = false
```

If the rebuilt score has inverse orientation, 16D must fail lineage instead of multiplying the score by `-1`.

Threshold fit population:

```text
train_binary_primary_model_score_rows =
  cluster_split_bucket == train
  and model_id == ridge_logistic_bar_state_v1
  and is_binary_target == true
  and continuation_label in {continuation_positive, continuation_negative}
```

Neutral rows are excluded from threshold fitting. They are scored and assigned an action only after train thresholds are frozen.

Primary action:

```text
threshold_value = quantile(primary_score over train_binary_primary_model_score_rows, 0.30)

if primary_score <= threshold_value:
  candidate_action = defend_next_h20
else:
  candidate_action = continue_next_h20
```

Primary policy id:

```text
primary_policy_id = defense_bottom_30pct_continuation_score_v1
primary_defense_rate = 0.30
score_source_model_id = ridge_logistic_bar_state_v1
selected_threshold_id = up50pct
primary_horizon_sessions = 20
primary_label_id = continuation_survival_h20_no_deep_drawdown
```

Diagnostic grid:

```text
defense_bottom_10pct_continuation_score_v1
defense_bottom_20pct_continuation_score_v1
defense_bottom_30pct_continuation_score_v1
defense_bottom_40pct_continuation_score_v1
```

Only `defense_bottom_30pct_continuation_score_v1` is primary. The grid is readout-only and may not be used to pick a better policy after seeing robustness or validation.

## 7. Neutral Handling

16B labels have three states:

```text
continuation_positive
continuation_negative
continuation_neutral
```

16D binary policy metrics must use:

```text
binary_denominator = positive_n + negative_n
neutral rows excluded from binary confusion rates
```

Neutral rows must still be materialized in policy action readout:

```text
neutral_defended_n
neutral_continued_n
neutral_defense_rate
neutral_action_caveat = true
```

Neutral rows must never be counted as negatives. If any implementation maps neutral to negative, it is a hard fail:

```text
neutral_handling_gate = fail
decision_state = 16D_policy_preflight_blocked_by_input_or_lineage_failure
```

## 8. Metrics

For each split, policy id, and context stratum, compute:

```text
binary_step_n = positive_n + negative_n
defended_binary_step_n
continued_binary_step_n
defended_positive_n
defended_negative_n
continued_positive_n
continued_negative_n
neutral_step_n
neutral_defended_n
neutral_continued_n
```

Primary rates:

```text
binary_negative_base_rate = negative_n / binary_step_n
defense_rate = defended_binary_step_n / binary_step_n
defense_negative_capture_rate = defended_negative_n / negative_n
positive_sacrifice_rate = defended_positive_n / positive_n
defense_precision = defended_negative_n / defended_binary_step_n
defense_precision_lift_vs_binary_negative_base = defense_precision - binary_negative_base_rate
continue_positive_precision = continued_positive_n / continued_binary_step_n
continue_negative_leakage_rate = continued_negative_n / negative_n
neutral_defense_rate = neutral_defended_n / neutral_step_n
```

Interpretation:

```text
defense_negative_capture_rate:
  Of all negative continuation windows, how many would the policy flag for defense?

positive_sacrifice_rate:
  Of all positive continuation windows, how many would the policy incorrectly defend?

defense_precision_lift_vs_binary_negative_base:
  Whether defended windows are enriched for negative labels relative to the split's binary base rate.

continue_negative_leakage_rate:
  How many negative windows remain in the continue action bucket.
```

No return, PnL, utility, cost, or execution metric is allowed in 16D.

## 9. Context Stratification

16D must reuse 16C's known-failed context rebuild contract.

Required context strata:

```text
all_steps
late_rescue_context
non_late_rescue_context
known_failed_context_any
non_known_failed_context
```

Primary context gate is evaluated on:

```text
non_known_failed_context
```

Reason:

```text
16D must prove the policy is not merely a proxy for 15B known-failed morphology.
```

Validation split context rows with low power must remain readout-only. They cannot block the primary decision unless a lineage failure is discovered.

## 10. Threshold Freeze

All policy cutoffs are train-only.

For each policy id:

```text
threshold_source_split = train
threshold_source_model_id = ridge_logistic_bar_state_v1
threshold_fit_population = train_binary_primary_model_score_rows
threshold_type = train_score_quantile
threshold_quantile in {0.10, 0.20, 0.30, 0.40}
threshold_value = quantile(primary_score over train_binary_primary_model_score_rows, threshold_quantile)
threshold_tie_policy = defend if primary_score <= threshold_value
```

The threshold value is then applied unchanged to train, robustness, and validation.

Neutral rows are not included in `threshold_value` fitting. They are materialized only after threshold freeze for action coverage and caveat reporting.

Forbidden:

```text
validation threshold selection
robustness threshold selection
threshold search by OOS metric
choosing a different quantile after seeing readout
using 16C feature importance to select policy variables
```

The threshold freeze audit must prove:

```text
all threshold rows use train only
all threshold rows use binary target rows only
all configured grid values are present
primary_policy_id is fixed before OOS evaluation
no validation/robustness columns enter threshold fitting
neutral rows are excluded from threshold fitting and included only after freeze
```

## 11. Support Gates

### 11.1 Hard Lineage Gates

All must pass:

```text
input_artifact_gate = pass
upstream_16c_authorization_gate = pass
upstream_16b_label_rebuild_gate = pass
score_rebuild_lineage_gate = pass
feature_contract_replay_gate = pass
score_orientation_gate = pass
threshold_freeze_gate = pass
neutral_handling_gate = pass
policy_action_binding_gate = pass
known_failed_context_rebuild_gate = pass
search_accounting_gate = pass
```

Any hard lineage fail maps to:

```text
16D_policy_preflight_blocked_by_input_or_lineage_failure
```

### 11.2 Power Gates

For `primary_policy_id = defense_bottom_30pct_continuation_score_v1`:

All sample counts in this section use the binary denominator:

```text
binary_step_n = continuation_positive_n + continuation_negative_n
neutral rows are excluded from power gates
train_binary_step_n expected from 16C replay = 14962
```

The floors are deliberately below the replayed 16C populations. They are conservative power floors for policy preflight, not optimization targets: train floors are roughly one third of the replayed train binary/positive/negative populations, and robustness floors preserve at least about 3x headroom against the replayed robustness counts.

```text
train_binary_step_n >= 5000
train_negative_n >= 1000
train_positive_n >= 3000
train_episode_cluster_n >= 200
train_defended_binary_step_n >= 1000
train_defended_negative_n >= 300

robustness_binary_step_n >= 1000
robustness_negative_n >= 200
robustness_positive_n >= 500
robustness_episode_cluster_n >= 100
robustness_defended_binary_step_n >= 150
robustness_defended_negative_n >= 40
```

Validation:

```text
validation_binary_step_n >= 300
validation_defended_binary_step_n >= 30
```

Validation power is stress-readout only. If validation is below this floor, set:

```text
validation_stress_low_power_caveat = true
```

but do not block primary decision.

### 11.3 Primary Policy Usefulness Gates

For `primary_policy_id` on train and robustness:

```text
train_defense_negative_capture_rate >= 0.35
robustness_defense_negative_capture_rate >= 0.30

train_defense_precision_lift_vs_binary_negative_base >= 0.05
robustness_defense_precision_lift_vs_binary_negative_base >= 0.03

train_positive_sacrifice_rate <= 0.40
robustness_positive_sacrifice_rate <= 0.45

train_continue_negative_leakage_rate <= 0.65
robustness_continue_negative_leakage_rate <= 0.70
```

These gates deliberately avoid PnL. They only ask whether the score can define a defensible label-action split.

### 11.4 Context Independence Gates

For `non_known_failed_context`:

```text
non_known_failed_train_binary_step_n >= 1000
non_known_failed_train_negative_n >= 250
non_known_failed_train_defended_negative_n >= 75
non_known_failed_train_defense_precision_lift >= 0.03

non_known_failed_robustness_binary_step_n >= 300
non_known_failed_robustness_negative_n >= 75
non_known_failed_robustness_defended_negative_n >= 20
non_known_failed_robustness_defense_precision_lift >= 0.02
```

The `defended_negative_n` floors are evaluated under the primary policy `primary_defense_rate = 0.30`. For robustness non-known-failed context, the expected defended-negative count from replayed 16C/16B context populations must retain comfortable headroom above the floor; otherwise the gate should fail as low power rather than be interpreted as a policy-quality failure.

If all primary policy gates pass only inside known-failed context but fail outside it:

```text
decision_state = 16D_policy_preflight_context_concentrated_only
next_allowed_requirement = none
```

### 11.5 Stability Gates

For the train-only grid `{10%, 20%, 30%, 40%}`:

```text
negative_capture_rate should be nondecreasing as defense_rate increases
positive_sacrifice_rate should be nondecreasing as defense_rate increases
defense_precision should be above binary negative base for at least 3 of 4 grid points in train
defense_precision should be above binary negative base for at least 2 of 4 grid points in robustness
```

Small monotonicity violations are warnings, not hard fail, unless they affect the primary policy id. If primary policy violates usefulness gates, decision is not supported.

## 12. Outputs

All publishable tables must be written under:

```text
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/
```

Required publishable tables:

```text
input_artifact_audit.csv
upstream_16c_authorization_audit.csv
score_rebuild_lineage_audit.csv
feature_contract_replay_audit.csv
policy_candidate_registry.csv
policy_threshold_freeze_audit.csv
policy_action_binding_audit.csv
policy_confusion_readout.csv
policy_tradeoff_frontier_readout.csv
known_failed_context_rebuild_audit.csv
policy_context_stratified_readout.csv
neutral_policy_handling_audit.csv
policy_stability_audit.csv
validation_stress_policy_readout.csv
search_accounting_audit.csv
sequential_continuation_policy_preflight_decision.csv
policy_action_sample.csv.gz
```

Local cache outputs:

```text
outputs/local_cache/16D_sequential_continuation_policy_preflight/policy_score_panel.parquet
outputs/local_cache/16D_sequential_continuation_policy_preflight/policy_action_panel.parquet
```

Report:

```text
outputs/publishable/reports/sequential_continuation_policy_preflight_report.md
```

Manifest:

```text
outputs/manifests/16D_sequential_continuation_policy_preflight_manifest.json
```

## 13. Required Table Schemas

### 13.1 `upstream_16c_authorization_audit.csv`

Minimum columns:

```text
upstream_decision_state
upstream_next_allowed_requirement
primary_label_id
selected_threshold_id
primary_horizon_sessions
primary_model_id
train_binary_step_n
train_positive_n
train_negative_n
robustness_binary_step_n
robustness_positive_n
robustness_negative_n
episode_cluster_grouped_cv_median_roc_auc
instrument_purged_chronological_cv_median_roc_auc
robustness_roc_auc
robustness_pr_auc_lift_vs_binary_base
known_failed_context_independence_gate
soft_overlap_partial_coverage_caveat
known_failed_context_exposure_caveat
authorization_status
blocking_reason
```

### 13.2 `score_rebuild_lineage_audit.csv`

Minimum columns:

```text
score_source
score_rebuild_method
model_id
preprocessing_spec_sha256
feature_contract_sha256
score_row_key_match_status
train_score_row_n
robustness_score_row_n
validation_score_row_n
replayed_train_auc
replayed_robustness_auc
replayed_validation_auc
source_16c_train_auc
source_16c_robustness_auc
source_16c_validation_auc
auc_abs_delta_train
auc_abs_delta_robustness
auc_abs_delta_validation
score_abs_diff_max
score_spearman_corr_vs_cache
train_bottom30_defense_precision_lift_vs_binary_negative_base
robustness_bottom30_defense_precision_lift_vs_binary_negative_base
score_sign_flipped
score_orientation_status
score_orientation_gate
score_rebuild_lineage_gate
blocking_reason
```

If local 16C score cache is used:

```text
optional_cache_used = true
optional_cache_key_match_status
optional_cache_metric_replay_status
```

### 13.3 `policy_candidate_registry.csv`

Minimum columns:

```text
policy_id
policy_family
policy_role
score_model_id
defense_quantile
threshold_source_split
action_rule
used_for_primary_decision
allowed_for_16e_if_ready
```

### 13.4 `policy_threshold_freeze_audit.csv`

Minimum columns:

```text
policy_id
threshold_source_split
threshold_source_model_id
threshold_fit_population
threshold_quantile
threshold_value
threshold_tie_policy
train_score_n
train_binary_score_n
neutral_rows_excluded_from_fit
validation_used_for_threshold
robustness_used_for_threshold
threshold_freeze_status
blocking_reason
```

### 13.5 `policy_action_binding_audit.csv`

Minimum columns:

```text
policy_id
label_id
threshold_id
horizon_sessions
primary_step_n
binary_step_n
neutral_step_n
duplicate_step_policy_key_n
missing_score_n
missing_action_n
positive_negative_overlap_n
neutral_mapped_to_negative_n
policy_action_binding_gate
blocking_reason
```

### 13.6 `policy_confusion_readout.csv`

Minimum columns:

```text
policy_id
split_bucket
context_stratum
binary_step_n
positive_n
negative_n
neutral_step_n
defended_binary_step_n
continued_binary_step_n
defended_positive_n
defended_negative_n
continued_positive_n
continued_negative_n
neutral_defended_n
neutral_continued_n
binary_negative_base_rate
defense_rate
defense_negative_capture_rate
positive_sacrifice_rate
defense_precision
defense_precision_lift_vs_binary_negative_base
continue_positive_precision
continue_negative_leakage_rate
neutral_defense_rate
policy_confusion_status
```

### 13.7 `policy_tradeoff_frontier_readout.csv`

One row per split and policy grid point:

```text
split_bucket
policy_id
defense_quantile
threshold_value
defense_rate
defense_negative_capture_rate
positive_sacrifice_rate
defense_precision
defense_precision_lift_vs_binary_negative_base
continue_negative_leakage_rate
frontier_status
```

### 13.8 `known_failed_context_rebuild_audit.csv`

Minimum columns:

```text
context_rebuild_source
source_15b_membership_row_n
source_15b_cluster_n
path_type_enum_status
taxonomy_rule_completeness_status
joined_step_n
joined_cluster_n
missing_context_step_n
hard_context_projection_coverage
optional_cache_used
optional_cache_row_key_match_status
aggregate_delta_vs_16b_known_failed_overlap_readout
aggregate_delta_vs_16c_context_stratified_readout
late_rescue_context_step_n
known_failed_context_any_step_n
non_known_failed_context_step_n
known_failed_context_rebuild_gate
blocking_reason
```

### 13.9 `policy_context_stratified_readout.csv`

One row per split, policy id, and context stratum. Same metric columns as `policy_confusion_readout.csv`, plus:

```text
valid_stratum_power
context_independence_status
context_caveat
```

### 13.10 `neutral_policy_handling_audit.csv`

Minimum columns:

```text
split_bucket
labelable_step_n
binary_step_n
neutral_step_n
neutral_rate
neutral_defended_n
neutral_continued_n
neutral_defense_rate
neutral_usage
neutral_handling_gate
```

### 13.11 `policy_stability_audit.csv`

Minimum columns:

```text
split_bucket
policy_family
grid_point_n
negative_capture_monotonic_status
positive_sacrifice_monotonic_status
defense_precision_above_base_grid_n
stability_status
blocking_reason
```

### 13.12 `search_accounting_audit.csv`

Must declare:

```text
search_family = sequential_continuation_policy_preflight
selected_threshold_id = up50pct
primary_horizon_sessions = 20
primary_label_id = continuation_survival_h20_no_deep_drawdown
primary_policy_id = defense_bottom_30pct_continuation_score_v1
policy_grid_pre_registered = true
validation_used_for_policy_selection = false
robustness_used_for_policy_selection = false
return_metric_used_for_selection = false
cost_metric_used_for_selection = false
hyperparameter_grid_searched = false
feature_selection_grid_searched = false
model_family_grid_searched = false
```

## 14. Decision Map

Final decision enum:

```text
16D_policy_preflight_ready_for_utility_diagnostic
16D_policy_preflight_blocked_by_input_or_lineage_failure
16D_policy_preflight_blocked_by_policy_search_or_leakage
16D_policy_preflight_low_power
16D_policy_preflight_not_supported
16D_policy_preflight_context_concentrated_only
```

Decision logic:

```text
if any forbidden search / leakage / return / cost / deployment contamination:
  decision_state = 16D_policy_preflight_blocked_by_policy_search_or_leakage
  next_allowed_requirement = none

elif any hard lineage gate fails:
  decision_state = 16D_policy_preflight_blocked_by_input_or_lineage_failure
  next_allowed_requirement = none

elif any power gate fails:
  decision_state = 16D_policy_preflight_low_power
  next_allowed_requirement = none

elif primary policy usefulness gates fail:
  decision_state = 16D_policy_preflight_not_supported
  next_allowed_requirement = none

elif context independence gates fail:
  decision_state = 16D_policy_preflight_context_concentrated_only
  next_allowed_requirement = none

else:
  decision_state = 16D_policy_preflight_ready_for_utility_diagnostic
  next_allowed_requirement = requirement_16e_sequential_continuation_utility_diagnostic.md
```

Regardless of decision:

```text
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
return_backtest_authorized = false
cost_model_authorized = false
```

If ready, 16D authorizes only writing the 16E utility diagnostic requirement. It does not authorize any live or simulated trading policy.

## 15. Report Requirements

The Chinese report must include:

1. 单行 decision and next allowed requirement.
2. 16C authorization replay with exact numbers.
3. Explanation that 16D is policy preflight, not trading authorization.
4. Primary policy definition and train-only threshold freeze.
5. Denominator explanation: labelable vs binary vs neutral.
6. Train and robustness policy confusion table.
7. Diagnostic frontier across 10/20/30/40% defense rates.
8. Neutral handling and caveat.
9. Known-failed context stratified policy evidence.
10. Validation stress caveat.
11. Search accounting: no return, no cost, no threshold selection on OOS.
12. Findings and insight: whether 16E utility diagnostic is justified and what 16E must inherit.

Report must explicitly state:

```text
16D does not authorize entry, exit, holding, deployment, return backtest, or cost model.
```

## 16. Manifest Requirements

Manifest must include:

```text
experiment_id
phase_id
run_id
created_at
requirement_path
requirement_sha256
config_path
config_sha256
upstream_16a_decision
upstream_16b_decision
upstream_16c_decision
primary_label_id
selected_threshold_id
primary_horizon_sessions
primary_model_id
primary_policy_id
policy_thresholds_sha256
score_rebuild_lineage_sha256
decision_state
next_allowed_requirement
authorization_booleans
input_artifact_hashes
output_hashes
row_counts
large_artifact_policy
```

## 17. Implementation Pattern

Implementation should remain experiment-local and may reuse existing runners via importlib:

```text
16A runner helpers for path resolution, YAML, hashing, table writing
16B runner helpers for label panel loading and known-failed projection
16C runner helpers for feature building, train preprocessing, model registry, score rebuild, metrics
```

No shared-package refactor is required.

Use local caches only after lineage validation. Required publishable audits remain mandatory even when caches exist. Even if the current workspace already contains local parquet caches, implementation must still run the §5.2/§5.4/§5.5 key, row-count, schema, and metric replay checks before trusting them.

Large full row-level panels should be stored as local parquet. Publishable row-level action output should be sampled/compressed:

```text
policy_action_sample.csv.gz
max_publishable_policy_action_sample_rows = 5000
```

## 18. Test Plan

Implement focused synthetic tests covering:

```text
test_16c_ready_authorization_required_for_16d
test_16c_next_allowed_requirement_must_match_16d
test_16c_authorization_replays_exact_sample_and_auc_values
test_16b_label_cache_is_optional_and_rebuild_path_is_required
test_local_score_cache_is_optional_and_must_match_rebuilt_scores
test_score_orientation_higher_means_positive_continuation
test_score_orientation_gate_uses_auc_and_bottom30_defense_lift
test_thresholds_are_train_only_quantiles
test_threshold_fit_population_is_train_binary_primary_model_rows
test_threshold_fit_excludes_neutral_rows_before_policy_freeze
test_validation_and_robustness_not_used_for_threshold_selection
test_primary_policy_id_is_frozen_to_bottom_30pct
test_policy_action_binding_rejects_missing_scores_and_duplicate_keys
test_neutral_rows_are_not_mapped_to_negative
test_policy_confusion_formulae_exact
test_defense_precision_lift_uses_binary_negative_base_rate
test_positive_sacrifice_and_negative_capture_denominators
test_known_failed_context_requires_row_level_rebuild_not_readout_only
test_known_failed_context_rebuild_replays_15b_rules_and_16b_aggregates
test_context_cache_cannot_replace_rule_rebuild
test_non_known_failed_context_gate_blocks_context_concentrated_policy
test_validation_low_power_is_caveat_not_hard_fail
test_no_return_or_cost_columns_are_allowed
test_search_accounting_rejects_posthoc_policy_grid_or_model_search
test_decision_map_lineage_failure
test_decision_map_low_power
test_decision_map_not_supported
test_decision_map_context_concentrated_only
test_ready_decision_only_allows_16e_requirement
test_all_trading_and_deployment_authorizations_remain_false
test_manifest_contains_input_artifact_hashes_and_report_hash
test_large_action_panel_is_local_cache_with_publishable_sample_only
```

## 19. Validation Commands

From `topics/02_AFML_BIG_WINNER`:

```bash
python -m py_compile experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16d_sequential_continuation_policy_preflight.py
python -m pytest experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/tests/test_16d_sequential_continuation_policy_preflight.py -q
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16d_sequential_continuation_policy_preflight.py --mode check-inputs
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16d_sequential_continuation_policy_preflight.py --mode full
git diff --check
```

After full run, inspect generated artifact sizes before publish. Full action/score panels should remain local parquet unless deliberately compressed and sampled.

## 20. Expected Caveats To Carry Forward

16D must carry these inherited caveats:

```text
16B soft_overlap_partial_coverage_caveat = true
16B known_failed_context_exposure_caveat = true
16C neutral_population_caveat = true
16C validation_stress_evaluable = true but validation is not a selection split
16C history_depth_feature_pair collinearity caveat
16C score separability is diagnostic, not utility
```

If 16D is ready, 16E must inherit:

```text
up50pct threshold
h20 continuation horizon
non-overlap h20 sampling unit
train-only preprocessing and score threshold freeze
primary policy id defense_bottom_30pct_continuation_score_v1
neutral handling rules
known-failed context caveat
no entry authorization from 16D
no deployment authorization from 16D
```
