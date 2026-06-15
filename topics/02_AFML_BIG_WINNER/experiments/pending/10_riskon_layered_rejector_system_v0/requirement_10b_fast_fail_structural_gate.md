# 需求：10B Fast-Fail Structural Gate

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/10_riskon_layered_rejector_system_v0`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. manifest 必须记录 resolved absolute path 与 hash。

## 1. 目标

10B 是 Layer 1 fast-fail structural safety gate。它回答一个窄问题：

```text
在 10A 冻结后的 default post-dedup population 上，
fast-fail-only score 是否相对规则化 swing-low structural stop
有 capacity-matched incremental capture lift，
且不造成不可接受的 winner injury。
```

10B 不是 cost optimizer，不是 medium-capacity rejector，也不能把 false-repair uplift 写成 fast-fail uplift。

10B 不改变 10A density population。所有 admitted/suppressed 决策必须继承 10A，10B 只能在 10A admitted population 上训练、打分、排序和做 reject-capacity readout。

## 2. 10A Frozen Evidence

10B 默认且唯一 supported population 是 10A 报告冻结的：

```text
population_id = 10A__same_instrument_cooldown_10d
rule_arm_id = same_instrument_cooldown_10d
input_denominator_id = risk_on_r_core_horizon_complete
denominator_id = post_dedup_risk_on_r_core
readout_only_flag = false
admission_status = admitted
```

当前 10A source state：

```text
10A decision = 10A_density_population_source_caveated_frozen
10A source_caveated = true
```

因此，只要该 upstream caveat 未解除，10B 的正向 supported 结论只能使用：

```text
10B_fast_fail_structural_gate_source_caveated_supported
```

不得输出 non-caveated `10B_fast_fail_structural_gate_supported`。

### 2.1 Default Population Sanity Counts

实现必须从 10A artifacts 读取真实数据；下表是当前 frozen 10A run 的 sanity expectation。若当前输入仍指向本次 10A manifest，但读数不匹配，必须 fail closed 为 `10B_fast_fail_input_blocked`，不得静默继续。

这些 frozen sanity counts 也必须写入 10B run config（例如 `config_10b.yaml.expected_10a_sanity_counts`）。Requirement 正文记录当前 10A 报告口径；runner 必须以 config 中的 frozen values 与 10A manifest hash 共同校验，避免未来合法重跑 10A 后旧数字被无意复用。

| split | input_row_n | admitted_event_n | suppressed_event_n | non_executable_audit_only_n | winner_n | fast_fail_positive_n | fast_fail_winner_n | false_repair_positive_n |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| `train` | 16,603 | 8,318 | 8,253 | 32 | 1,491 | 702 | 70 | 3,025 |
| `robustness` | 9,730 | 4,970 | 4,741 | 19 | 995 | 342 | 39 | 1,299 |
| `validation` | 4,457 | 2,514 | 1,941 | 2 | 161 | 236 | 5 | 709 |
| **total** | **30,790** | **15,802** | **14,935** | **53** | **2,647** | **1,280** | **114** | **5,033** |

Density must remain the 10A frozen density:

```text
formal_event_day_density = 1.0
p95_density = 1.0
rolling_10d_executable_event_day_density = 0.1
rolling_20d_executable_event_day_density = 0.1
```

10B must report these values but must not recompute an alternate density denominator.

### 2.2 10A Power Readiness Boundary

10A power audit says the default population has only `9` fast-fail ML-supported capacity rows:

| split | supported capacity ids |
|:--|:--|
| `train` | `keep_9000`, `keep_9250`, `keep_9300`, `keep_9400`, `keep_9500` |
| `robustness` | `keep_9000`, `keep_9250`, `keep_9300`, `keep_9500` |
| `validation` | none |

`keep_9000` is lower-bound sensitivity only. A supported operating point may only be selected from train-supported non-sensitivity thresholds:

```text
keep_9250
keep_9300
keep_9400
keep_9500
```

Validation is always low-power for fast-fail in this 10A run. Validation may block severe reversal, but it cannot by itself support a positive claim.

R6 readout has `fast_fail_ml_supported_gate_allowed = false` for every row. R6 must never be used for fit, feature selection, threshold selection, or supported gate.

## 3. Required Inputs

10B must read 10A outputs through the 10A manifest first:

```text
outputs/manifests/10A_density_rule_system_manifest.json
outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_sample_count_by_split.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_fast_fail_power_audit.csv
outputs/publishable/tables/10A_density_rule_system/power_audit_config.csv
outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet
```

`outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet` is a required local runtime dependency even though `outputs/local_cache/**` is not published to Git. If it is missing or its hash does not match `10A_density_rule_system_manifest.json.output_hashes.post_dedup_event_bindings`, supported 10B is blocked.

10B must also read the 09B feature foundation referenced by the 10A manifest:

```text
../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/feature_contract.csv
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/feature_matrix.parquet
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
```

10B must read 08 event labels for the MAE side constraint:

```text
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet
```

10B may read 09C event scores only as pre-dedup diagnostic replay:

```text
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09C_riskon_cost_rejector/event_scores.csv.gz
```

09C scores are hybrid cost scores trained pre-dedup. They must not be used as the supported 10B score and must not be used to select the 10B threshold.

## 4. Input Schemas And Joins

### 4.1 10A Event Bindings

Required columns in `post_dedup_event_bindings.parquet`:

```text
population_id
rule_arm_id
input_event_key
sample_id
selected_target_id
input_denominator_id
denominator_id
split
instrument
event_t0_date
event_t0_pos
event_window_anchor_date
event_window_anchor_pos
event_window_anchor_status
source_pool_id
source_family_id
mechanism_id
event_regime_bucket
raw_event_status
admission_status
readout_only_flag
admitted_event_id
representative_sample_id
suppressed_by_sample_id
suppression_reason
selected_fast_fail_10_label
frozen_false_repair_20d_label
selected_cost_bad_10_20_target
winner_120
E1_missed_winner_flag
feature_matrix_join_key
fast_fail_sample_weight_join_key
cost_bad_sample_weight_join_key
```

10A 当前 `post_dedup_event_bindings.parquet` 不保证物理包含 `canonical_event_id` 列。10B 必须从 `input_event_key` 恢复 canonical id：

```text
input_event_key = sample_id || "|" || selected_target_id || "|" || input_denominator_id || "|" || canonical_event_id
```

Derived field:

```text
binding_canonical_event_id = split(input_event_key, "|")[3]
```

10B must validate:

```text
input_event_key has exactly 4 pipe-delimited components
split(input_event_key, "|")[0] == sample_id
split(input_event_key, "|")[1] == selected_target_id
split(input_event_key, "|")[2] == input_denominator_id
binding_canonical_event_id is non-null
```

If a future 10A binding also contains a physical `canonical_event_id` column, it must equal `binding_canonical_event_id`. 10B must not assume `sample_id == canonical_event_id`; current artifacts may use identity values, but 09A only contracts `sample_id` as a deterministic function of canonical id.

Supported training/evaluation rows are exactly:

```text
population_id == "10A__same_instrument_cooldown_10d"
rule_arm_id == "same_instrument_cooldown_10d"
input_denominator_id == "risk_on_r_core_horizon_complete"
denominator_id == "post_dedup_risk_on_r_core"
readout_only_flag == false
admission_status == "admitted"
split in {"train", "validation", "robustness"}
```

Rows with `admission_status != admitted` must be retained only in audit counts and must not receive supported 10B reject decisions.

### 4.2 Feature Matrix Join

Join `post_dedup_event_bindings` to 09B `feature_matrix.parquet` using the exact tuple:

```text
left.sample_id = right.sample_id
left.selected_target_id = right.selected_target_id
left.input_denominator_id = right.denominator_id
left.binding_canonical_event_id = right.canonical_event_id
```

Equivalently, the implementation may verify and use 10A `feature_matrix_join_key`, but the tuple above must still be audited.

`split` in 10B comes from 10A binding `split`. 09B feature matrix has `event_split`; it is only a consistency check and must equal 10A `split` after join. If it disagrees, output `10B_fast_fail_input_blocked`.

Feature candidates are rows in `feature_contract.csv` with:

```text
allowed_for_09C_flag == true
t0_visible_flag == true
feature_dtype in {float64, int64, float32, int32}
```

The following columns are join/meta columns and must never be model features:

```text
sample_id
selected_target_id
denominator_id
canonical_event_id
instrument
event_t0_date
event_split
feature_as_of_date
```

### 4.3 Fast-Fail Sample Weight Join

Join 09B `sample_uniqueness_weights.parquet` using:

```text
left.sample_id = right.sample_id
left.selected_target_id = right.selected_target_id
left.input_denominator_id = right.denominator_id
left.binding_canonical_event_id = right.canonical_event_id
right.weight_horizon_id = fast_fail_10d
```

Required weight columns:

```text
final_sample_weight
weight_status
supported_training_scope_flag
```

For supported 10B, all admitted default-population rows must have `weight_status = complete` and non-null positive `final_sample_weight`. Missing or non-positive weights block supported training.

### 4.4 MAE10 Join

Join 08 `candidate_family_event_labels.parquet` for MAE using:

```text
left.binding_canonical_event_id = labels.event_id
labels.label_scope = all_new_candidate_union
labels.horizon_complete_10d = true
```

Required MAE column:

```text
mae_10d
```

`mae_10d` is expected to be a return-like value where more negative means worse adverse excursion. To keep the `accepted_MAE_10_improves` direction consistent across 10A/10B contracts, 10B must convert it to a positive adverse-excursion magnitude:

```text
adverse_excursion_10 = -1.0 * mae_10d
accepted_mean_MAE_10 = mean(adverse_excursion_10 over accepted rows)
```

Lower `accepted_mean_MAE_10` is better. If any joined `mae_10d > 0`, set `mae10_status = input_blocked_positive_mae_sign` and output `10B_fast_fail_input_blocked`.

The side constraint passes only if candidate accepted rows are not more adverse than both baselines:

```text
candidate_accepted_mean_MAE_10 <= rule_baseline_accepted_mean_MAE_10
and
candidate_accepted_mean_MAE_10 <= random_baseline_accepted_mean_MAE_10
```

If MAE cannot be joined for every admitted default-population row, output `10B_fast_fail_input_blocked`. Do not impute MAE or silently drop rows.

## 5. Model Contract

Primary supported score:

```text
model_id = regularized_logistic_fast_fail_10d_l2_v1
target = selected_fast_fail_10_label
positive_label = true
fit_split = train
readout_splits = train, validation, robustness
```

Estimator contract:

```text
estimator = sklearn.linear_model.LogisticRegression
penalty = l2
C = 1.0
solver = liblinear
max_iter = 1000
random_state = 20260615
class_weight = none
sample_weight = final_sample_weight
```

Preprocessing contract:

1. Fit preprocessing on `train` only.
2. For each feature, compute train median and train IQR after excluding non-finite values.
3. Impute missing/non-finite values with train median.
4. Scale as `(x - train_median) / train_iqr`.
5. If train IQR is zero or non-finite, drop that feature and record it in `model_registry.csv`.
6. Apply the train-fitted preprocessing unchanged to validation and robustness.
7. Do not use validation or robustness to select features, imputation values, scaling values, model hyperparameters, or thresholds.

The supported score is:

```text
candidate_fast_fail_score = predict_proba(positive_label=true)
```

Higher score means higher fast-fail risk and therefore higher rejection priority.

ROC-AUC / PR-AUC / top-decile lift are diagnostic readouts only. They must not select the supported model, supported threshold, or final decision. 10B exists because a ranking metric can look acceptable while still killing winners, failing cost/readout constraints, or relying on non-executable density.

## 6. Threshold Grid And Capacity

Fast-fail capacity grid is read from 10A `power_audit_config.csv` for `component_id = fast_fail_10d`:

| capacity_id | reject_fraction | role |
|:--|--:|:--|
| `keep_9000` | 0.100 | lower-bound sensitivity only |
| `keep_9250` | 0.075 | selectable |
| `keep_9300` | 0.070 | selectable |
| `keep_9400` | 0.060 | selectable |
| `keep_9500` | 0.050 | selectable |
| `keep_9600` | 0.040 | readout only for default 10A run unless power later passes |
| `keep_9700` | 0.030 | readout only for default 10A run unless power later passes |

For every split and capacity:

```text
reject_n = ceil(post_dedup_sample_n * reject_fraction)
accepted_n = post_dedup_sample_n - reject_n
```

Candidate rejected rows are the first `reject_n` rows sorted by:

```text
candidate_fast_fail_score descending
input_event_key ascending
```

Candidate accepted rows are all remaining admitted rows.

Threshold selection is train-only:

1. Candidate operating points are train-supported non-sensitivity thresholds from section 2.2.
2. Compute `train_constrained_utility` from section 8 for each candidate operating point.
3. Select the threshold with the largest train `train_constrained_utility`.
4. Ties break by larger train `capacity_matched_capture_lift_over_rule_baseline`.
5. Remaining ties break by larger train `capacity_matched_capture_lift_over_random`.
6. Remaining ties break by higher `winner_retention`.
7. Remaining ties break by lower `reject_fraction`.
8. Remaining ties break by lexicographic `capacity_id`.

Validation and robustness can block severe reversal, but cannot improve or choose the selected threshold.

## 7. Baselines

### 7.1 Rule Baseline

10B 的主比较对象是 10A `power_audit_config.csv` 中冻结的：

```text
rule_baseline_id = structural_swing_low_rank_v1
```

Required rule baseline features:

```text
close_to_ema60
ema60_slope_20d
return_20d
stock_vs_market_20d
atr_20_pct
```

Each required feature must exist uniquely in 09B `feature_matrix.parquet` and must have `allowed_for_09C_flag = true` in `feature_contract.csv`. If not, set `rule_baseline_status = input_blocked` and forbid supported pass.

Rule baseline rejection order:

```text
close_to_ema60 ascending nulls last
ema60_slope_20d ascending nulls last
return_20d ascending nulls last
stock_vs_market_20d ascending nulls last
atr_20_pct descending nulls last
input_event_key ascending
```

For every split/capacity, reject the first `reject_n` rows in this order.

### 7.2 Random Baseline

Random baseline must be deterministic and must use the 10A config:

```text
random_seed = 20260615
random_tie_break_key = sha256_input_event_key_capacity_seed
```

For each `capacity_id`, compute:

```text
random_key = sha256(input_event_key + "|" + capacity_id + "|" + random_seed)
```

Sort by `random_key ascending`, then `input_event_key ascending`, and reject the first `reject_n` rows.

Do not use a process-global RNG order.

## 8. Metrics

For each split and capacity, compute these counts for candidate, rule baseline, and random baseline:

```text
post_dedup_sample_n
reject_n
accepted_n
post_dedup_fast_fail_positive_n
post_dedup_fast_fail_winner_n
post_dedup_winner_n
rejected_fast_fail_positive_n
rejected_fast_fail_winner_n
rejected_fast_fail_non_winner_n
rejected_winner_n
accepted_fast_fail_positive_n
accepted_winner_n
accepted_mean_MAE_10
```

Capture and lift:

```text
candidate_capture_rate = candidate_rejected_fast_fail_positive_n / post_dedup_fast_fail_positive_n
rule_baseline_capture_rate = rule_rejected_fast_fail_positive_n / post_dedup_fast_fail_positive_n
random_baseline_capture_rate = random_rejected_fast_fail_positive_n / post_dedup_fast_fail_positive_n

capacity_matched_capture_lift_over_rule_baseline = candidate_capture_rate - rule_baseline_capture_rate
capacity_matched_capture_lift_over_random = candidate_capture_rate - random_baseline_capture_rate
```

Winner injury:

```text
wrong_kill_rate = candidate_rejected_winner_n / post_dedup_winner_n
winner_retention = 1 - wrong_kill_rate
```

MAE side constraint:

```text
accepted_MAE_10_improves =
  candidate_accepted_mean_MAE_10 <= rule_baseline_accepted_mean_MAE_10
  and
  candidate_accepted_mean_MAE_10 <= random_baseline_accepted_mean_MAE_10
```

Constrained utility weights must be read from `config_10b.yaml.utility_weights`, not hard-coded inside the runner. Current default profile:

```text
utility_weight_profile_id = 10B_default_v1
random_lift_weight = 0.5
winner_injury_excess_weight = 10.0
mae_worse_excess_weight = 1.0
density_excess_weight = 100.0
oos_threshold_instability_weight = 10.0
```

The manifest must record both full `config_hash` and a dedicated `utility_weights_hash = sha256(canonical_json(config_10b.yaml.utility_weights))`. Any future tuning must change `utility_weight_profile_id`, config hash, utility weights hash, and report text. Silent coefficient changes are input-blocking for supported claims.

Constrained utility:

```text
fast_fail_benefit =
  capacity_matched_capture_lift_over_rule_baseline
  + random_lift_weight * capacity_matched_capture_lift_over_random

winner_injury_excess = max(0, wrong_kill_rate - 0.0600)

mae_worse_excess = max(
  0,
  candidate_accepted_mean_MAE_10
  - min(rule_baseline_accepted_mean_MAE_10, random_baseline_accepted_mean_MAE_10)
)

density_excess =
  max(0, rolling_10d_executable_event_day_density - 0.1)
  + max(0, rolling_20d_executable_event_day_density - 0.1)

train_constrained_utility =
  fast_fail_benefit
  - winner_injury_excess_weight * winner_injury_excess
  - mae_worse_excess_weight * mae_worse_excess
  - density_excess_weight * density_excess
```

For 10B, this is a threshold/model-selection utility, not a training label. The training target remains `selected_fast_fail_10_label`. `cost_reduction` belongs to the 10C/medium-capacity cost rejector; 10B may report cost diagnostics, but it must not optimize a hybrid cost target.

After the train-only threshold is selected, compute OOS instability for the selected `capacity_id`:

```text
oos_threshold_instability = max(
  0,
  -0.0100
  - min(
      validation_capacity_matched_capture_lift_over_rule_baseline,
      validation_capacity_matched_capture_lift_over_random,
      robustness_capacity_matched_capture_lift_over_rule_baseline,
      robustness_capacity_matched_capture_lift_over_random
    )
)

supported_constrained_utility =
  train_constrained_utility
  - oos_threshold_instability_weight * oos_threshold_instability
```

`oos_threshold_instability` may block supported pass after train-only selection, but validation/robustness values must never be used to choose among thresholds.

All divisions by zero are fail-closed for supported pass and must emit an explicit status, not `NaN` interpreted as pass.

## 9. Supported Gate

A split/capacity row is eligible for supported gate only if the matching 10A `post_dedup_fast_fail_power_audit.csv` row has:

```text
rule_baseline_status = pass
capture_lift_power_status = pass
winner_injury_power_status = pass
fast_fail_ml_supported_gate_allowed = true
readout_only_flag = false
```

Additionally, the row must satisfy:

```text
post_dedup_fast_fail_positive_n >= 100
post_dedup_fast_fail_winner_n >= 20
rule_baseline_rejected_fast_fail_positive_n >= 10
rule_baseline_rejected_fast_fail_winner_n >= 3
```

The selected operating point can claim supported pass only if train passes all binding objectives:

```text
capacity_matched_capture_lift_over_rule_baseline >= 0.0200
capacity_matched_capture_lift_over_random >= 0.0200
accepted_MAE_10_improves = true
winner_retention >= 0.9400
wrong_kill_rate <= 0.0600
density_after_Layer_0 == 10A frozen density
train_constrained_utility > 0
oos_threshold_instability = 0
supported_constrained_utility > 0
```

OOS severe reversal block:

```text
For the selected capacity_id, if validation or robustness has
capacity_matched_capture_lift_over_rule_baseline < -0.0100
or
capacity_matched_capture_lift_over_random < -0.0100
then supported pass is forbidden.
```

Low-power validation/robustness rows may block severe reversal but must not be described as stable supporting evidence.

## 10. Ablation And Explanation

10B must report:

```text
full model
rule baseline
random baseline
drop FS2 / FS3 mechanism-overlap subset
pre-dedup 09C score replay diagnostic
```

Ablation feature removal:

```text
drop all feature_contract rows where feature_family in {FS2_basis_path_quality, FS3_vol_range_stop_distance}
or label_mechanism_overlap_type != none
```

If `dropped_feature_n == 0`, output `ablation_status = family_name_unmatched` and `10B_fast_fail_input_blocked`. A no-op ablation must never be interpreted as an ablation pass.

The no-overlap ablation is explanatory, not a primary kill switch. However, if the full model passes but the no-overlap ablation has:

```text
capacity_matched_capture_lift_over_rule_baseline < 0
and
capacity_matched_capture_lift_over_random < 0
```

on train at the selected capacity, conclusion must be downgraded to:

```text
10B_fast_fail_rule_based_structural_stop_diagnostic
```

and the report must state that the apparent lift is mechanism-overlap-dependent.

## 11. Required Outputs

10B must output:

```text
outputs/publishable/tables/10B_fast_fail_structural_gate/input_artifact_audit.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/fast_fail_power_gate_readout.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/fast_fail_threshold_frontier.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/capacity_matched_rule_lift.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/winner_injury_audit.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/accepted_mae10_audit.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/fast_fail_ablation_readout.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/pre_dedup_09c_replay_diagnostic.csv
outputs/publishable/tables/10B_fast_fail_structural_gate/model_registry.csv
outputs/local_cache/10B_fast_fail_structural_gate/post_dedup_fast_fail_scores.parquet
outputs/manifests/10B_fast_fail_structural_gate_manifest.json
outputs/publishable/reports/10B_fast_fail_structural_gate_report.md
```

### 11.1 `input_artifact_audit.csv`

Required columns:

```text
artifact_id
path
required_flag
exists_flag
hash
expected_hash
status
note
```

### 11.2 `fast_fail_power_gate_readout.csv`

Required columns:

```text
population_id
denominator_id
split
capacity_id
threshold_id
readout_only_flag
post_dedup_sample_n
post_dedup_fast_fail_positive_n
post_dedup_fast_fail_winner_n
post_dedup_winner_n
rule_baseline_status
capture_lift_power_status
winner_injury_power_status
fast_fail_ml_supported_gate_allowed
tenb_supported_row_allowed
tenb_supported_row_block_reason
```

### 11.3 `fast_fail_threshold_frontier.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
threshold_id
reject_fraction
reject_n
accepted_n
candidate_capture_rate
rule_baseline_capture_rate
random_baseline_capture_rate
capacity_matched_capture_lift_over_rule_baseline
capacity_matched_capture_lift_over_random
winner_retention
wrong_kill_rate
candidate_accepted_mean_MAE_10
rule_baseline_accepted_mean_MAE_10
random_baseline_accepted_mean_MAE_10
accepted_MAE_10_improves
fast_fail_benefit
winner_injury_excess
mae_worse_excess
density_excess
utility_weight_profile_id
random_lift_weight
winner_injury_excess_weight
mae_worse_excess_weight
density_excess_weight
oos_threshold_instability_weight
train_constrained_utility
oos_threshold_instability
supported_constrained_utility
selected_operating_point_flag
supported_pass_flag
status
```

### 11.4 `capacity_matched_rule_lift.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
baseline_id
post_dedup_sample_n
reject_n
candidate_rejected_fast_fail_positive_n
baseline_rejected_fast_fail_positive_n
candidate_capture_rate
baseline_capture_rate
capture_lift
```

### 11.5 `winner_injury_audit.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
post_dedup_winner_n
candidate_rejected_winner_n
rule_baseline_rejected_winner_n
random_baseline_rejected_winner_n
winner_retention
wrong_kill_rate
winner_injury_status
```

### 11.6 `accepted_mae10_audit.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
candidate_accepted_mean_MAE_10
rule_baseline_accepted_mean_MAE_10
random_baseline_accepted_mean_MAE_10
accepted_MAE_10_improves
mae10_joined_n
mae10_missing_n
mae10_status
```

### 11.7 `fast_fail_ablation_readout.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
dropped_feature_n
retained_feature_n
candidate_capture_rate
capacity_matched_capture_lift_over_rule_baseline
capacity_matched_capture_lift_over_random
winner_retention
wrong_kill_rate
accepted_MAE_10_improves
ablation_status
conclusion_effect
```

### 11.8 `pre_dedup_09c_replay_diagnostic.csv`

Required columns:

```text
score_source
model_id_09c
threshold_id_09c
split
joined_post_dedup_admitted_n
diagnostic_rejected_n
diagnostic_rejected_fast_fail_positive_n
diagnostic_capture_rate
overlap_with_10b_selected_rejected_n
diagnostic_status
note
```

If 09C scores are absent, emit one row with `diagnostic_status = not_available` and do not block supported 10B.

### 11.9 `model_registry.csv`

Required columns:

```text
model_id
ablation_id
estimator
target
fit_split
train_row_n
train_positive_n
feature_n_input
feature_n_used
feature_n_dropped_constant
feature_list_hash
preprocessing_fit_scope
sample_weight_column
random_state
model_status
sklearn_version
numpy_version
pandas_version
```

### 11.10 `post_dedup_fast_fail_scores.parquet`

This file must be long-form: one row per `(model_id, ablation_id, capacity_id, admitted event)`.

Required columns:

```text
model_id
ablation_id
capacity_id
threshold_id
reject_fraction
population_id
denominator_id
split
input_event_key
sample_id
selected_target_id
binding_canonical_event_id
instrument
event_t0_date
admitted_event_id
selected_fast_fail_10_label
winner_120
mae_10d
adverse_excursion_10
final_sample_weight
candidate_fast_fail_score
candidate_rank
rule_baseline_rank
random_baseline_rank
candidate_rejected_flag
rule_baseline_rejected_flag
random_baseline_rejected_flag
```

### 11.11 Manifest

`10B_fast_fail_structural_gate_manifest.json` must include:

```text
component_id
decision
source_caveated
selected_population_id
selected_denominator_id
selected_model_id
selected_capacity_id
selected_threshold_id
input_hashes
output_hashes
input_paths
outputs
config_hash
utility_weights_hash
requirement_hash
git_revision
created_at_utc
statuses
python_version
sklearn_version
numpy_version
pandas_version
```

## 12. Decision State Machine

10B decision must be exactly one of:

```text
10B_fast_fail_structural_gate_supported
10B_fast_fail_structural_gate_source_caveated_supported
10B_fast_fail_rule_based_structural_stop_diagnostic
10B_fast_fail_pre_dedup_diagnostic_only
10B_fast_fail_input_blocked
```

Decision rules:

1. If 10A post-dedup local cache is unavailable but 09C event scores are available and config explicitly enables pre-dedup replay, output only `10B_fast_fail_pre_dedup_diagnostic_only`.
2. Otherwise, missing required 10A/09B/08 artifact, hash mismatch, schema mismatch, join mismatch, no MAE coverage for admitted rows, no valid train feature matrix, or no valid sample weights -> `10B_fast_fail_input_blocked`.
3. If train has no non-sensitivity supported capacity row from section 2.2 -> `10B_fast_fail_rule_based_structural_stop_diagnostic`.
4. If selected train capacity fails any binding metric or OOS severe reversal block triggers -> `10B_fast_fail_rule_based_structural_stop_diagnostic`.
5. If selected train capacity passes all binding metrics and `source_caveated = true` -> `10B_fast_fail_structural_gate_source_caveated_supported`.
6. If selected train capacity passes all binding metrics and `source_caveated = false` -> `10B_fast_fail_structural_gate_supported`.

Reports must never describe a diagnostic state as supported, production-ready, or entry-candidate.

## 13. Implementation Command

Expected runner shape:

```text
python topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/src/run_fast_fail_structural_gate.py \
  --config topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/config_10b.yaml
```

The runner must be deterministic. Re-running with the same inputs and config must reproduce byte-stable publishable CSV/JSON/Markdown outputs, except for explicitly recorded `created_at_utc` if the project convention does not freeze timestamps.

## 14. Explicit Prohibitions

10B must not:

1. Use 09C hybrid score as supported score.
2. Train on validation or robustness.
3. Select thresholds on validation or robustness.
4. Include suppressed or non-executable 10A rows in supported training/evaluation.
5. Use R6 for supported fit, feature selection, threshold selection, or pass/fail support.
6. Recompute 10A density or change 10A admission.
7. Treat validation low-power readout as positive support.
8. Claim cost or false-repair uplift.
9. Claim production readiness.
