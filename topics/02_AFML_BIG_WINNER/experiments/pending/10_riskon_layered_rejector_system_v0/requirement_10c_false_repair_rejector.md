# 需求：10C False-Repair Rejector

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/10_riskon_layered_rejector_system_v0`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. 其他相对路径，包括 `outputs/`、`configs/`、`src/`、`tests/`，一律按 `EXPERIMENT_ROOT` 相对路径解析。
7. manifest 必须记录 resolved absolute path、relative path、file size、mtime UTC 与 content hash。

## 1. 目标

10C 是 Layer 2 false-repair / exposure-efficiency rejector。它回答：

```text
在 10A 冻结后的 post-dedup R-core population 上，
false_repair_20d_component 是否能作为中容量 exposure-efficiency filter，
并且在接入 10B fast-fail gate 后仍然带来 overlap-deduplicated 净改善。
```

10C 不是 fast-fail safety gate，也不能把 false-repair signal 写成 fast-fail uplift。10C 的正向结论必须同时满足：

1. false-repair-only target 在 10A post-dedup population 上有 train-only constrained utility；
2. winner / E1-missed winner / bridge winner injury 不触发硬约束；
3. validation / robustness 没有 severe reversal；
4. 与 10B selected gate 叠加后，净 readout 仍然可解释，不把 10B 已经拒绝的行重复记为 10C 增量。

## 2. 当前冻结上游结论

10C 必须继承以下 10A / 10B 冻结状态，不得在本阶段回改。

| upstream | frozen value | 10C implication |
|---|---:|---|
| 10A decision | `10A_density_population_source_caveated_frozen` | 10C 正向结论只能是 source-caveated supported |
| 10A default population | `10A__same_instrument_cooldown_10d` | 唯一 supported fit / threshold / gate population |
| 10A default rule arm | `same_instrument_cooldown_10d` | Layer 0 density 固定，不可调 |
| input denominator | `risk_on_r_core_horizon_complete` | 用于 09B feature / weight join |
| output denominator | `post_dedup_risk_on_r_core` | 用于 10C 输出与下游消费 |
| admitted rows | 15,802 | post-dedup supported universe |
| false-repair positives | 5,033 | 10C target 正例池 |
| winners | 2,647 | 10C winner injury denominator |
| E1-missed winners | 1,357 | E1-missed retention readout |
| 10B decision | `10B_fast_fail_structural_gate_source_caveated_supported` | 可作为 Layer 1 cascade 输入 |
| 10B selected gate | authoritative source is 10B manifest `selected_*`; current expected value is `keep_9400` / `reject_fraction=0.0600` | 只用于 cascade overlap attribution，不作为 10C feature |

默认 population 的 split counts 冻结如下，implementation 必须在 input audit 中逐项核对：

| split | admitted | false_repair+ | hybrid+ | winner | E1-missed winner |
|---|---:|---:|---:|---:|---:|
| `train` | 8,318 | 3,025 | 3,132 | 1,491 | 811 |
| `validation` | 2,514 | 709 | 782 | 161 | 64 |
| `robustness` | 4,970 | 1,299 | 1,402 | 995 | 482 |

10A false-repair power audit 对默认 R-core population 的 15 个 split-capacity rows 全部允许 ML supported gate。10C 仍必须重新训练、重新排序、重新选择 threshold；10A 只证明样本功效，不证明 10C rejector 有 uplift。

09C 只能作为 diagnostic prior。09C 的 hybrid score、AUC、pre-dedup threshold 或 replay 结果不得作为 10C supported model、supported threshold 或 supported uplift 证据。

## 3. 非目标

10C 明确不做：

1. 不做 fast-fail structural safety gate；fast-fail target、fast-fail score 与 10B selected flag 只能作为 cascade readout 输入。
2. 不训练 `hybrid_cost_bad_10_20` target，也不使用 `selected_cost_bad_10_20_target` 作为 supported training label。
3. 不调 10A density / cooldown / cap / family / mechanism 规则。
4. 不在 validation / robustness 上选择 threshold、模型、feature set 或 utility 权重。
5. 不把 E1 baseline 当作主 uplift comparator。
6. 不声称 production-ready、entry-candidate 或 non-caveated supported。
7. 不补齐 R2 amount / volume，不重建 09B feature matrix，不根据 10C 结果回写 10A / 10B。

## 4. Required Inputs

### 4.1 10A inputs

| artifact | required | usage |
|---|---|---|
| `outputs/manifests/10A_density_rule_system_manifest.json` | yes | source caveat、input hash、population provenance |
| `outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv` | yes | default population contract |
| `outputs/publishable/tables/10A_density_rule_system/post_dedup_false_repair_power_audit.csv` | yes | capacity power gate |
| `outputs/publishable/tables/10A_density_rule_system/power_audit_config.csv` | yes | capacity grid、random baseline seed、winner retention floor |
| `outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet` | yes | row-level target、split、winner、E1、join keys |

10C supported scope 必须过滤：

```text
population_id = 10A__same_instrument_cooldown_10d
rule_arm_id = same_instrument_cooldown_10d
input_denominator_id = risk_on_r_core_horizon_complete
denominator_id = post_dedup_risk_on_r_core
readout_only_flag = false
admission_status = admitted
```

如果 `post_dedup_event_bindings.parquet` 缺少 `frozen_false_repair_20d_label`、`winner_120`、`E1_missed_winner_flag`、`split`、`input_event_key` 或 `feature_matrix_join_key`，10C 必须 `10C_false_repair_input_blocked`。

### 4.2 09B inputs

| artifact | required | usage |
|---|---|---|
| `../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09B_feature_foundation_ablation_manifest.json` | yes | upstream hash / caveat |
| `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/feature_matrix.parquet` | yes | feature matrix |
| `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/feature_contract.csv` | yes | feature eligibility |
| `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet` | yes | `cost_bad_10_20_20d` sample weight and exposure interval |
| `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09B_feature_foundation/sample_uniqueness_audit.csv` | yes | weight audit readout |

09B feature matrix 的 split 列名是 `event_split`。10C 内部统一别名为 `split`，但 `split` 的 authoritative source 必须来自 10A binding；implementation 必须 assert：

```text
10A binding.split == 09B feature_matrix.event_split
```

09B weights 没有 split 列。禁止从 weights 推断 split；split 必须从 10A binding 携带。

### 4.3 08 readout inputs

| artifact | required | usage |
|---|---|---|
| `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet` | yes | MFE / confirm_20 / false-repair label consistency readout |
| `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet` | yes | bridge retention / E1 membership coverage readout |

08 label parquet 必须至少提供：

```text
event_id
confirm_20_label
confirm_20_complete
mfe_20d
horizon_complete_20d
event_false_repair_20d_label
label_scope
```

08 membership parquet 必须至少提供：

```text
canonical_event_id
target_episode_id
bridge_positive_denominator_included
membership_basis
```

`source_caveat_status` is not a required 08 membership column. Source caveat must be inferred from 08 / 10A / 10B manifest decisions; if a row-level caveat column exists in future membership artifacts, 10C may audit it but must not require it.

08 readout join 失败不得静默填 0。若 label artifact 完全不可读，10C input-blocked；若 membership 部分缺失，bridge retention readout 必须显式输出 missing coverage rows，并将 bridge retention gate 降级为 non-binding readout。

### 4.4 10B cascade inputs

| artifact | required for supported cascade | usage |
|---|---|---|
| `outputs/manifests/10B_fast_fail_structural_gate_manifest.json` | yes | selected 10B gate provenance |
| `outputs/local_cache/10B_fast_fail_structural_gate/post_dedup_fast_fail_scores.parquet` | yes | selected fast-fail rejection flags |

10C must first read authoritative selected gate fields from 10B manifest:

```text
selected_model_id
selected_population_id
selected_denominator_id
selected_capacity_id
selected_threshold_id
selected_operating_point.ablation_id
selected_operating_point.reject_fraction
```

Then filter 10B scores using those manifest-selected values, not hard-coded capacity values:

```text
model_id = manifest.selected_model_id
ablation_id = manifest.selected_operating_point.ablation_id
population_id = manifest.selected_population_id
denominator_id = manifest.selected_denominator_id
capacity_id = manifest.selected_capacity_id
threshold_id = manifest.selected_threshold_id
```

Current 10B report expectation is:

```text
selected_capacity_id = keep_9400
selected_threshold_id = keep_9400
selected_operating_point.reject_fraction = 0.0600
```

If 10B manifest-selected values differ from the current expected values in `configs/config_10c.yaml`, 10C must fail closed for cascade-supported decision with `10B_selected_gate_mismatch`. It may still emit standalone false-repair diagnostics, but it must not silently filter `keep_9400` when the manifest selected a different gate.

如果 10B manifest 表示 supported 或 source-caveated supported，但 10B scores local cache 缺失或 hash mismatch，10C 可以输出 standalone false-repair diagnostics，但不能输出 `10C_false_repair_rejector_supported` 或 `10C_false_repair_rejector_source_caveated_supported`。

### 4.5 09C diagnostic inputs

| artifact | required | usage |
|---|---|---|
| `../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json` | yes | diagnostic prior provenance |
| `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/reports/09C_riskon_cost_rejector_uplift_report.md` | yes | narrative comparison |

If 09C row-level diagnostic scores are present, 10C may emit pre/post-dedup comparison readout. Missing optional 09C row-level scores must not block 10C.

## 5. Join Contract

### 5.1 Binding canonical event id

10A binding does not require a standalone `canonical_event_id` column. 10C must derive the binding canonical id from `input_event_key`, which is the only 10A key contracted as a pipe-delimited string:

```text
input_event_key_parts = split(input_event_key, "|")
assert len(input_event_key_parts) == 4
assert input_event_key_parts[0] == sample_id
assert input_event_key_parts[1] == selected_target_id
assert input_event_key_parts[2] == input_denominator_id
binding_canonical_event_id = input_event_key_parts[3]
```

If any component contains `|` and makes `input_event_key` unparsable, 10C must input-block rather than guessing.

`feature_matrix_join_key` is a join/audit key, not the source of `binding_canonical_event_id`. If it is materialized as a matching pipe string, implementation may cross-check it; if it is materialized as a struct/list/logical tuple in a future 10A run, 10C must still join by the explicit components in Section 5.2 and must not parse it as a string.

`input_event_key` remains the unique post-dedup row key and must be carried to every output table. `binding_canonical_event_id` is used only for upstream feature / label / membership joins.

### 5.2 Feature join

10C feature join key:

```text
left:  10A binding.sample_id
       10A binding.selected_target_id
       10A binding.input_denominator_id
       binding_canonical_event_id

right: 09B feature_matrix.sample_id
       09B feature_matrix.selected_target_id
       09B feature_matrix.denominator_id
       09B feature_matrix.canonical_event_id
```

Required assertions:

1. join cardinality is one-to-one for supported scope;
2. no supported-scope 10A admitted row is dropped;
3. `10A split == 09B event_split`;
4. feature matrix `denominator_id` is the upstream input denominator, not 10A output denominator;
5. `post_dedup_risk_on_r_core` must never be used to join 09B feature matrix.

### 5.3 Weight join

10C sample weight join key:

```text
left:  10A binding.sample_id
       10A binding.selected_target_id
       10A binding.input_denominator_id
       binding_canonical_event_id

right: 09B sample_uniqueness_weights.sample_id
       09B sample_uniqueness_weights.selected_target_id
       09B sample_uniqueness_weights.denominator_id
       09B sample_uniqueness_weights.canonical_event_id

filter:
       weight_horizon_id = cost_bad_10_20_20d
       weight_status = complete
```

`final_sample_weight` is the training sample weight. `active_interval_start` and `active_interval_end` define exposure interval readouts. For 10C:

```text
active_interval_calendar_day_n =
    (date(active_interval_end) - date(active_interval_start)).days + 1
```

Rows with missing or non-positive `final_sample_weight` are input-blocking unless they are outside supported scope. Rows with invalid active interval are excluded from exposure-days denominators and counted in `exposure_interval_invalid_n`; if invalid rows exceed 1% of supported scope, 10C cannot be supported.

### 5.4 10A power-audit join

For every 10C `(split, capacity_id, threshold_id)` row, join 10A false-repair power audit by:

```text
population_id
rule_arm_id
input_denominator_id
denominator_id
split
readout_only_flag
capacity_id
threshold_id
```

Required assertions:

1. exactly one 10A power-audit row is found for each 10C split-capacity row;
2. `false_repair_ml_supported_gate_allowed=true` for any row considered for supported selection;
3. 10A `post_dedup_sample_n`, `post_dedup_false_repair_positive_n`, `post_dedup_winner_n`, and `post_dedup_E1_missed_winner_n` match 10C recomputed counts exactly;
4. 10A `e1_missed_proxy_status=episode_membership_proxy_input_blocked` forces 10C diagnostic-only for that row.

### 5.5 08 label join

10C must join 08 labels by:

```text
left:  binding_canonical_event_id
right: candidate_family_event_labels.event_id
```

When duplicate 08 rows exist for the same `event_id`, keep the row with:

```text
label_scope = all_new_candidate_union first,
then canonical_event_scope lexicographically,
then event_family lexicographically
```

If `event_false_repair_20d_label` disagrees with 10A `frozen_false_repair_20d_label` for supported-scope rows, output `label_consistency_mismatch_n`; any mismatch rate above 0.5% is input-blocking.

### 5.6 08 bridge membership join

10C must join 08 membership by:

```text
left:  binding_canonical_event_id
right: post_replay_event_episode_membership.canonical_event_id
```

Because membership may be one-to-many across episode windows, aggregate row-level bridge flags before joining back to 10C rows:

```text
bridge_positive_flag =
    any(bridge_positive_denominator_included == true)

bridge_membership_row_n =
    count(membership rows for binding_canonical_event_id)

bridge_membership_missing_flag =
    bridge_membership_row_n == 0
```

Bridge retention denominator:

```text
bridge_winner_denominator =
    winner_120 == true
    and bridge_positive_flag == true
```

Rows with no membership are not treated as bridge negatives. They must be counted separately.

Bridge retention is a binding gate only when coverage is sufficient:

```text
bridge_membership_missing_rate =
    bridge_membership_missing_n / supported_scope_row_n

bridge_gate_binding_flag =
    bridge_winner_n >= 100
    and bridge_membership_missing_rate <= 0.5000
```

If `bridge_gate_binding_flag=false`, bridge metrics remain mandatory readouts but cannot by themselves pass or fail the supported decision.

### 5.7 10B cascade join

10C must join selected 10B rows by:

```text
input_event_key
sample_id
selected_target_id
binding_canonical_event_id
split
```

Required assertions:

1. row count equals 10C supported-scope row count for each split;
2. no duplicate 10B selected rows after filtering to the manifest-selected gate;
3. 10B `candidate_rejected_flag` is boolean and non-null;
4. 10B score is never used as a 10C feature.

## 6. Target And Labels

10C supported training target is:

```text
target_component = false_repair_20d_component
target_label_column = frozen_false_repair_20d_label
positive = true
```

Do not train on:

```text
selected_cost_bad_10_20_target
selected_fast_fail_10_label
event_false_repair_20d_label directly from 08
09C score / rank / rejected flag
10B score / rank / rejected flag
```

Readout labels:

| label | source | usage |
|---|---|---|
| `winner_120` | 10A binding | winner injury / retention |
| `E1_missed_winner_flag` | 10A binding | E1-missed retention |
| `bridge_positive_flag` | 08 membership aggregate | bridge retention |
| `confirm_20_label` | 08 labels | confirm relation readout |
| `mfe_20d` | 08 labels | MFE relation readout |
| `selected_cost_bad_10_20_target` | 10A binding | diagnostic comparison only |
| `selected_fast_fail_10_label` | 10A / 10B | cascade interaction readout only |

`false_repair_non_winner_flag` must be computed as:

```text
frozen_false_repair_20d_label == true and winner_120 == false
```

This flag is the primary denominator for false-positive exposure-days reduction.

## 7. Feature Eligibility And Model

### 7.1 Feature eligibility

Eligible model features are numeric columns in 09B `feature_matrix.parquet` whose `feature_id` appears in `feature_contract.csv` with:

```text
allowed_for_09C_flag = true
t0_visible_flag = true
feature_dtype is numeric, including but not limited to float64, float32, int64, int32, bool
```

The following columns or feature families are forbidden as 10C predictors even if present:

```text
sample_id
selected_target_id
denominator_id
canonical_event_id
instrument
event_t0_date
event_split
feature_as_of_date
any label / outcome / horizon-complete column
any 08 membership / E1 / winner / false-repair / fast-fail readout column
any 09C score / rank / rejected flag
any 10B score / rank / rejected flag
final_sample_weight
active_interval_start
active_interval_end
active_interval_calendar_day_n
```

If feature contract and feature matrix disagree, the run must output `feature_contract_mismatch_n`; any selected feature missing from contract is input-blocking.

### 7.2 Model

Default supported model:

```text
model_id = regularized_logistic_false_repair_20d_l2_v1
library = sklearn.linear_model.LogisticRegression
penalty = l2
solver = liblinear
C = 1.0
class_weight = null
max_iter = 1000
random_state = 20260615
fit_intercept = true
```

Preprocessing:

```text
fit split = train only
imputation = train median per feature
scaling = train median / train IQR; if IQR == 0, drop feature
missing indicator = false
sample_weight = final_sample_weight from 09B cost_bad_10_20_20d weights
```

All preprocessing statistics must be stored in local model registry metadata. validation / robustness must use train-fitted preprocessing without refit.

### 7.3 Ablation

10C must output at least two ablations:

| ablation_id | rule |
|---|---|
| `full` | all eligible features |
| `no_label_mechanism_overlap` | drop feature_contract rows where `label_mechanism_overlap_type` is not `none` or null |

Only `full` can be selected as the default supported candidate unless `no_label_mechanism_overlap` has higher train constrained utility and passes every safety gate. The selected ablation must be recorded in config and manifest.

## 8. Capacity Grid And Baselines

10C capacity grid is inherited from 10A `power_audit_config.csv` for `component_id=false_repair_20d_component`:

| capacity_id | threshold_id | reject_fraction |
|---|---|---:|
| `keep_8000` | `keep_8000` | 0.200 |
| `keep_8250` | `keep_8250` | 0.175 |
| `keep_8500` | `keep_8500` | 0.150 |
| `keep_8750` | `keep_8750` | 0.125 |
| `keep_9000` | `keep_9000` | 0.100 |

For every split and capacity:

```text
reject_n = ceil(split_sample_n * reject_fraction)
candidate_rank = row_number over stable ordering:
    candidate_false_repair_score desc,
    input_event_key asc
candidate_rejected_flag = candidate_rank <= reject_n
```

Random baseline must match 10A power config:

```text
random_seed = 20260615
random_tie_break_key = sha256(input_event_key + "|" + capacity_id + "|" + random_seed)
random_baseline_rank = row_number over stable ordering:
    random_tie_break_key asc,
    input_event_key asc
random_baseline_rejected_flag = random_baseline_rank <= reject_n
```

There is no rule baseline for false-repair in 10A:

```text
rule_baseline_id = none
rule_baseline_owner = 10C
```

Any output column involving rule baseline must be absent or null with `rule_baseline_status=not_applicable`; do not invent a false-repair rule baseline.

## 9. Train-Only Selection Utility

10C must select the operating point using train split only. validation / robustness can block severe reversal but cannot improve, re-rank, or rescue the selected threshold.

### 9.1 Metrics per split-capacity

For each `(model_id, ablation_id, split, capacity_id)` compute:

```text
sample_n
reject_n
reject_fraction_actual = reject_n / sample_n
false_repair_positive_n
winner_n
e1_missed_winner_n
bridge_winner_n

candidate_rejected_false_repair_positive_n
candidate_rejected_false_repair_non_winner_n
candidate_rejected_winner_n
candidate_rejected_e1_missed_winner_n
candidate_rejected_bridge_winner_n

random_rejected_false_repair_positive_n
random_rejected_false_repair_non_winner_n
random_rejected_winner_n

false_repair_capture_rate =
    candidate_rejected_false_repair_positive_n / false_repair_positive_n

random_false_repair_capture_rate =
    random_rejected_false_repair_positive_n / false_repair_positive_n

false_repair_capture_lift_vs_random =
    false_repair_capture_rate - random_false_repair_capture_rate

candidate_precision =
    candidate_rejected_false_repair_positive_n / reject_n

winner_retention =
    1 - candidate_rejected_winner_n / winner_n

wrong_kill_rate =
    candidate_rejected_winner_n / winner_n

e1_missed_retention =
    1 - candidate_rejected_e1_missed_winner_n / e1_missed_winner_n

e1_missed_wrong_kill_rate =
    candidate_rejected_e1_missed_winner_n / e1_missed_winner_n

bridge_retention =
    1 - candidate_rejected_bridge_winner_n / bridge_winner_n

bridge_wrong_kill_rate =
    candidate_rejected_bridge_winner_n / bridge_winner_n
```

If a denominator is zero, the metric is null and the row cannot support a positive conclusion for that metric.

### 9.2 Exposure-days reduction

Exposure-days readout is based on 09B cost weight active interval:

```text
false_repair_non_winner_exposure_days_before =
    sum(active_interval_calendar_day_n where false_repair_non_winner_flag)

false_repair_non_winner_exposure_days_rejected =
    sum(active_interval_calendar_day_n where false_repair_non_winner_flag and candidate_rejected_flag)

false_repair_non_winner_exposure_days_reduction =
    false_repair_non_winner_exposure_days_rejected
    / false_repair_non_winner_exposure_days_before

random_false_repair_non_winner_exposure_days_rejected =
    sum(active_interval_calendar_day_n where false_repair_non_winner_flag and random_baseline_rejected_flag)

random_false_repair_non_winner_exposure_days_reduction =
    random_false_repair_non_winner_exposure_days_rejected
    / false_repair_non_winner_exposure_days_before

exposure_days_lift_vs_random =
    false_repair_non_winner_exposure_days_reduction
    - random_false_repair_non_winner_exposure_days_reduction
```

Also report:

```text
all_rejected_exposure_days
winner_rejected_exposure_days
```

Do not call this trading PnL. It is an exposure-efficiency proxy.

### 9.3 Two-stage utility formula

10C uses a two-stage utility to avoid CV / threshold circularity.

Stage 1 selects the train operating point using only same-row train metrics:

```text
winner_injury_excess =
    max(0, wrong_kill_rate - wrong_kill_rate_cap)

e1_missed_injury_excess =
    max(0, e1_missed_wrong_kill_rate - e1_missed_wrong_kill_rate_cap)

bridge_injury_excess =
    max(0, bridge_wrong_kill_rate - bridge_wrong_kill_rate_cap)

train_selection_utility =
    false_repair_capture_weight * false_repair_capture_lift_vs_random
    + exposure_days_reduction_weight * exposure_days_lift_vs_random
    - winner_injury_excess_weight * winner_injury_excess
    - e1_missed_injury_excess_weight * e1_missed_injury_excess
    - bridge_injury_excess_weight * bridge_injury_excess
```

Stage 2 evaluates the selected operating point with train-only CV instability:

```text
threshold_instability_excess =
    max(0, train_cv_selected_reject_fraction_std - train_cv_selected_reject_fraction_std_cap)

selected_train_constrained_utility =
    selected_train_selection_utility
    - threshold_instability_weight * threshold_instability_excess
```

`selected_train_selection_utility` is the `train_selection_utility` of the Stage 1 selected row.

`train_cv_selected_reject_fraction_std` and `oos_rejected_fraction_spread` are post-selection blockers. They must not enter Stage 1 selection; OOS spread must never enter train threshold selection because it uses validation / robustness.

Default config values:

```yaml
utility:
  false_repair_capture_weight: 1.0
  exposure_days_reduction_weight: 0.5
  winner_injury_excess_weight: 10.0
  e1_missed_injury_excess_weight: 5.0
  bridge_injury_excess_weight: 2.0
  threshold_instability_weight: 1.0
  wrong_kill_rate_cap: 0.1500
  e1_missed_wrong_kill_rate_cap: 0.1500
  bridge_wrong_kill_rate_cap: 0.1500
  winner_retention_floor: 0.8500
  e1_missed_retention_floor: 0.8500
  bridge_retention_floor: 0.8500
  oos_rejected_fraction_spread_cap: 0.1500
  train_cv_selected_reject_fraction_std_cap: 0.0500
```

These values must live in `configs/config_10c.yaml` and be included in manifest hash. Requirement hard-codes the defaults only to make the first implementation reproducible.

### 9.4 Supported selection gate

A train row can be selected only if all conditions hold:

```text
false_repair_ml_supported_gate_allowed == true in 10A power audit
post_dedup_false_repair_positive_n >= 300
post_dedup_winner_n >= 100
winner_retention >= 0.8500
wrong_kill_rate <= 0.1500
e1_missed_retention >= 0.8500
bridge_retention >= 0.8500 when bridge_gate_binding_flag == true
false_repair_capture_lift_vs_random > 0
exposure_days_lift_vs_random >= 0
train_selection_utility > 0
```

Among passing train rows, select max `train_selection_utility`, tie-break by:

```text
lower wrong_kill_rate
higher false_repair_capture_lift_vs_random
lower reject_fraction
capacity_id ascending lexicographic
ablation_id ascending lexicographic
model_id ascending lexicographic
```

After Stage 2, the selected row remains supportable only if:

```text
selected_train_constrained_utility > 0
train_cv_selected_reject_fraction_std <= train_cv_selected_reject_fraction_std_cap
```

## 10. OOS And Instability Blocking

validation and robustness do not support positive conclusions, but can block selected gate.

Selected gate must be downgraded to `10C_false_repair_diagnostic_only` if any OOS split has:

```text
false_repair_capture_lift_vs_random < -0.0200
winner_retention < 0.8000
e1_missed_retention < 0.8000 when e1_missed_winner_n >= 100
bridge_retention < 0.8000 when bridge_gate_binding_flag == true
```

OOS rejected-fraction spread:

```text
oos_rejected_fraction_spread =
    max(validation.reject_fraction_actual, robustness.reject_fraction_actual)
    - min(validation.reject_fraction_actual, robustness.reject_fraction_actual)
```

If `oos_rejected_fraction_spread > 0.1500`, selected gate is diagnostic-only.

Train-only instability proxy:

```text
use only train split
sort train rows by event_t0_date, then input_event_key
create 5 contiguous folds
embargo = 20 calendar days around validation fold
for each fold:
    fit on train-minus-fold-minus-embargo
    score held-out fold
    select capacity by the same train_selection_utility formula on that fold
train_cv_selected_reject_fraction_std =
    std(selected reject_fraction across 5 folds)
```

If fewer than 4 folds have positive / winner denominators after embargo, instability status is `insufficient_train_cv_power` and selected gate cannot be supported.

## 11. Cascade With 10B

10C standalone metrics are necessary but not sufficient for positive supported decision. If 10B is frozen as supported or source-caveated supported, 10C must emit cascade overlap attribution using the 10B manifest-selected gate.

For each row:

```text
fast_fail_rejected_flag = 10B candidate_rejected_flag
false_repair_rejected_flag = 10C selected candidate_rejected_flag

cascade_bucket =
    both_rejected if fast_fail_rejected_flag and false_repair_rejected_flag
    fast_fail_only_rejected if fast_fail_rejected_flag and not false_repair_rejected_flag
    false_repair_only_rejected if false_repair_rejected_flag and not fast_fail_rejected_flag
    accepted_by_cascade otherwise
```

Cascade retained row:

```text
cascade_accepted_flag =
    not fast_fail_rejected_flag and not false_repair_rejected_flag
```

Cascade net metrics must be computed against the same 10A default pre-cascade population:

```text
cascade_total_rejected_n
cascade_fast_fail_only_rejected_n
cascade_false_repair_only_rejected_n
cascade_both_rejected_n
cascade_false_repair_positive_caught_n
cascade_false_repair_positive_incremental_to_10b_n
cascade_false_repair_non_winner_exposure_days_reduction
cascade_winner_retention
cascade_e1_missed_retention
cascade_bridge_retention
```

10C positive supported decision additionally requires:

```text
cascade_false_repair_positive_incremental_to_10b_n > 0 on train
cascade_false_repair_non_winner_exposure_days_reduction > 0 on train
cascade_winner_retention >= 0.8500 on train
```

If 10B input is missing, stale, or not joinable, 10C may still publish standalone model/readout tables, but decision must be diagnostic-only or feature-source-supported, not rejector-supported.

## 12. R2 Source Handling

R2 source handling is frozen:

```text
r2_source_policy = separate_family_budget_cooldown
```

10C must not backfill amount / volume fields, rebuild R2 source rows, or alter 10A density. `r2_source_policy`, 10A population hash, 09B feature matrix hash, and 10B selected gate hash must be written to 10C manifest.

If implementation detects that R2 handling would change feature rows or supported population membership, 10C must be input-blocked.

## 13. Required Outputs

All publishable tables must be UTF-8 CSV with stable column ordering and deterministic sorting. Local cache parquet may contain extra diagnostic columns, but every publishable metric must be reproducible from local cache plus manifest.

### 13.1 Input audit

`outputs/publishable/tables/10C_false_repair_rejector/input_artifact_audit.csv`

Required columns:

```text
artifact_id
relative_path
resolved_path
required_flag
exists_flag
content_hash
schema_status
row_count
failure_reason
```

### 13.2 Model registry

`outputs/publishable/tables/10C_false_repair_rejector/model_registry.csv`

Required columns:

```text
model_id
ablation_id
selected_flag
feature_count
dropped_constant_feature_count
dropped_missing_feature_count
train_fit_rows
train_positive_n
train_weight_sum
solver
penalty
C
random_state
preprocess_fit_split
model_status
```

### 13.3 False-repair power gate readout

`outputs/publishable/tables/10C_false_repair_rejector/false_repair_power_gate_readout.csv`

Required columns:

```text
model_id
ablation_id
population_id
denominator_id
split
capacity_id
threshold_id
sample_n
reject_n
reject_fraction_actual
false_repair_positive_n
winner_n
e1_missed_winner_n
bridge_winner_n
candidate_rejected_false_repair_positive_n
candidate_rejected_false_repair_non_winner_n
candidate_rejected_winner_n
candidate_rejected_e1_missed_winner_n
candidate_rejected_bridge_winner_n
random_rejected_false_repair_positive_n
random_rejected_false_repair_non_winner_n
random_rejected_winner_n
false_repair_capture_rate
random_false_repair_capture_rate
false_repair_capture_lift_vs_random
candidate_precision
winner_retention
wrong_kill_rate
e1_missed_retention
e1_missed_wrong_kill_rate
bridge_retention
bridge_wrong_kill_rate
bridge_gate_binding_flag
train_selection_utility
supported_row_flag
row_block_reason
```

### 13.4 Threshold frontier

`outputs/publishable/tables/10C_false_repair_rejector/false_repair_threshold_frontier.csv`

Required columns:

```text
model_id
ablation_id
capacity_id
threshold_id
selected_flag
selection_rank
train_selection_utility
selected_train_constrained_utility
train_false_repair_capture_lift_vs_random
train_exposure_days_lift_vs_random
train_winner_retention
train_e1_missed_retention
train_bridge_retention
validation_false_repair_capture_lift_vs_random
validation_winner_retention
robustness_false_repair_capture_lift_vs_random
robustness_winner_retention
oos_rejected_fraction_spread
train_cv_selected_reject_fraction_std
decision_block_reason
```

`selected_train_constrained_utility` is non-null only for the selected row; non-selected rows must leave it null.

### 13.5 Exposure efficiency readout

`outputs/publishable/tables/10C_false_repair_rejector/exposure_efficiency_readout.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
false_repair_non_winner_exposure_days_before
false_repair_non_winner_exposure_days_rejected
false_repair_non_winner_exposure_days_reduction
random_false_repair_non_winner_exposure_days_reduction
exposure_days_lift_vs_random
all_rejected_exposure_days
winner_rejected_exposure_days
exposure_interval_invalid_n
exposure_interval_invalid_rate
```

### 13.6 Winner retention audit

`outputs/publishable/tables/10C_false_repair_rejector/winner_retention_audit.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
winner_n
candidate_rejected_winner_n
winner_retention
e1_missed_winner_n
candidate_rejected_e1_missed_winner_n
e1_missed_retention
e1_missed_wrong_kill_rate
bridge_winner_n
candidate_rejected_bridge_winner_n
bridge_retention
bridge_wrong_kill_rate
bridge_gate_binding_flag
bridge_membership_missing_n
bridge_membership_missing_rate
retention_status
```

### 13.7 MFE / confirm readout

`outputs/publishable/tables/10C_false_repair_rejector/mfe_confirm_relation_readout.csv`

Required columns:

```text
model_id
ablation_id
split
capacity_id
bucket
row_n
confirm_20_positive_n
confirm_20_positive_rate
mfe_20d_mean
mfe_20d_median
mfe_20d_p25
mfe_20d_p75
label_consistency_mismatch_n
label_consistency_mismatch_rate
```

Allowed `bucket`:

```text
candidate_rejected
candidate_accepted
random_rejected
cascade_rejected
cascade_accepted
```

### 13.8 Train-only threshold instability

`outputs/publishable/tables/10C_false_repair_rejector/train_only_threshold_instability.csv`

Required columns:

```text
fold_id
fold_start_date
fold_end_date
fit_rows
holdout_rows
holdout_false_repair_positive_n
holdout_winner_n
selected_capacity_id
selected_reject_fraction
fold_train_selection_utility
fold_status
```

The table must include a final summary row with `fold_id=summary`.

### 13.9 Cascade overlap attribution

`outputs/publishable/tables/10C_false_repair_rejector/cascade_overlap_attribution.csv`

Required columns:

```text
split
cascade_bucket
row_n
false_repair_positive_n
false_repair_non_winner_n
fast_fail_positive_n
winner_n
e1_missed_winner_n
bridge_winner_n
false_repair_non_winner_exposure_days
winner_retention_contribution
notes
```

The table must include per-split bucket rows plus per-split `cascade_bucket=total` rows.

### 13.10 09C diagnostic comparison

`outputs/publishable/tables/10C_false_repair_rejector/pre_dedup_09c_diagnostic_comparison.csv`

Required columns:

```text
diagnostic_source
split
metric_id
metric_value
comparison_note
```

This table is diagnostic only and must not feed supported decision logic.

### 13.11 Row-level scores

`outputs/local_cache/10C_false_repair_rejector/post_dedup_false_repair_scores.parquet`

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
frozen_false_repair_20d_label
false_repair_non_winner_flag
selected_fast_fail_10_label
winner_120
E1_missed_winner_flag
bridge_positive_flag
confirm_20_label
mfe_20d
final_sample_weight
active_interval_calendar_day_n
candidate_false_repair_score
candidate_rank
random_baseline_rank
candidate_rejected_flag
random_baseline_rejected_flag
fast_fail_rejected_flag
cascade_bucket
```

### 13.12 Manifest and report

```text
outputs/manifests/10C_false_repair_rejector_manifest.json
outputs/publishable/reports/10C_false_repair_rejector_report.md
```

Manifest must include:

```text
decision
source_caveated
selected_population_id
selected_denominator_id
selected_model_id
selected_ablation_id
selected_capacity_id
selected_threshold_id
selected_train_selection_utility
selected_train_constrained_utility
actual_10b_selected_model_id
actual_10b_selected_ablation_id
actual_10b_selected_capacity_id
actual_10b_selected_threshold_id
actual_10b_selected_reject_fraction
expected_10b_selected_model_id
expected_10b_selected_ablation_id
expected_10b_selected_capacity_id
expected_10b_selected_threshold_id
expected_10b_selected_reject_fraction
tenb_selected_gate_match_flag
selected_cascade_status
input_hashes
config_hash
feature_contract_hash
model_registry_hash
publishable_table_hashes
local_cache_hashes
input_failures
decision_block_reasons
```

Report must be Chinese, include detailed data tables, findings, insight, and explicitly state whether 10C is supported, source-caveated supported, feature-source-supported, diagnostic-only, or input-blocked.

## 14. Config Contract

Implementation must create:

```text
configs/config_10c.yaml
```

Minimum required keys:

```yaml
run:
  experiment_id: 10C_false_repair_rejector
  random_seed: 20260615
  selected_population_id: 10A__same_instrument_cooldown_10d
  selected_rule_arm_id: same_instrument_cooldown_10d
  input_denominator_id: risk_on_r_core_horizon_complete
  denominator_id: post_dedup_risk_on_r_core
  target_component: false_repair_20d_component
  target_label_column: frozen_false_repair_20d_label
  weight_horizon_id: cost_bad_10_20_20d
  r2_source_policy: separate_family_budget_cooldown

model:
  model_id: regularized_logistic_false_repair_20d_l2_v1
  solver: liblinear
  penalty: l2
  C: 1.0
  max_iter: 1000
  random_state: 20260615

capacity_grid:
  keep_8000: 0.200
  keep_8250: 0.175
  keep_8500: 0.150
  keep_8750: 0.125
  keep_9000: 0.100

cascade:
  require_10b_for_supported_decision: true
  use_10b_manifest_selected_gate: true
  expected_10b_model_id: regularized_logistic_fast_fail_10d_l2_v1
  expected_10b_ablation_id: full
  expected_10b_capacity_id: keep_9400
  expected_10b_threshold_id: keep_9400
  expected_10b_reject_fraction: 0.0600

utility:
  false_repair_capture_weight: 1.0
  exposure_days_reduction_weight: 0.5
  winner_injury_excess_weight: 10.0
  e1_missed_injury_excess_weight: 5.0
  bridge_injury_excess_weight: 2.0
  threshold_instability_weight: 1.0
  wrong_kill_rate_cap: 0.1500
  e1_missed_wrong_kill_rate_cap: 0.1500
  bridge_wrong_kill_rate_cap: 0.1500
  winner_retention_floor: 0.8500
  e1_missed_retention_floor: 0.8500
  bridge_retention_floor: 0.8500
  oos_rejected_fraction_spread_cap: 0.1500
  train_cv_selected_reject_fraction_std_cap: 0.0500
```

Changing any config value requires a new manifest hash and report note.

## 15. Decision States

10C decision must be exactly one of:

```text
10C_false_repair_rejector_supported
10C_false_repair_rejector_source_caveated_supported
10C_false_repair_feature_source_supported
10C_false_repair_diagnostic_only
10C_false_repair_input_blocked
```

State rules:

| decision | condition |
|---|---|
| `10C_false_repair_rejector_supported` | all supported gates pass and upstream source caveat is false |
| `10C_false_repair_rejector_source_caveated_supported` | all supported gates pass and any upstream source caveat is true |
| `10C_false_repair_feature_source_supported` | model has positive train false-repair/exposure signal, but rejector-supported gate is blocked by retention, cascade, OOS, instability, or source-readout caveat |
| `10C_false_repair_diagnostic_only` | inputs are readable and tables can be produced, but no selected row can support a rejector conclusion |
| `10C_false_repair_input_blocked` | required artifact missing, schema mismatch, join loss, label mismatch above tolerance, leakage detected, or supported-scope weights/features unavailable |

Because 10A and 10B currently carry source caveat, any positive rejector decision in the current artifact set must be:

```text
10C_false_repair_rejector_source_caveated_supported
```

Non-caveated supported is forbidden until upstream source caveat is explicitly cleared and manifests prove it.

## 16. Determinism And Validation

Implementation must be deterministic:

```text
PYTHONHASHSEED fixed or no hash-order dependence
all random seeds fixed at 20260615
stable sorting before rank / tie-break / CSV output
no wall-clock timestamps in publishable tables
manifest generated_at allowed but excluded from table hashes
```

Validation command must run after implementation:

```bash
python topics/02_AFML_BIG_WINNER/experiments/pending/10_riskon_layered_rejector_system_v0/src/run_10c_false_repair_rejector.py
```

If the package layout requires a different executable path, the report and manifest must record the exact command used.

Minimum validation assertions:

1. input audit has no failures for required artifacts;
2. supported-scope row count equals 15,802;
3. split counts match Section 2;
4. feature join has zero row loss and zero duplicate rows;
5. cost weight join has zero row loss and zero duplicate rows;
6. selected target positive counts match Section 2;
7. no forbidden feature is present in the fitted design matrix;
8. train-only preprocessing is not refit on validation / robustness;
9. 10B cascade join has zero row loss if supported decision is attempted;
10. every publishable table hash is present in manifest.

## 17. Implementation Notes

Recommended implementation location:

```text
src/run_10c_false_repair_rejector.py
```

Recommended internal modules:

```text
src/experiment_paths.py
src/io_contracts.py
src/modeling.py
src/metrics.py
src/reporting.py
```

These module names are recommendations, not downstream contract. Publishable artifact names, schemas, state machine, target label, joins, and config hash are the contract.
