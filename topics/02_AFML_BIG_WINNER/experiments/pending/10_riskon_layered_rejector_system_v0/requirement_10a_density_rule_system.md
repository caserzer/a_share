# 需求骨架：10A Density Rule System

## 0. 路径基准

本 requirement 同时引用 repo-root 路径与实验目录相对路径，必须按以下规则解析：

1. `REPO_ROOT` 是当前 Git repository root。
2. `TOPIC_ROOT` 是 `topics/02_AFML_BIG_WINNER`。
3. `EXPERIMENT_ROOT` 是 `TOPIC_ROOT/experiments/pending/10_riskon_layered_rejector_system_v0`。
4. 以 `topics/` 开头的路径一律按 repo-root-relative 解析。
5. 以 `../` 开头的路径一律按 `EXPERIMENT_ROOT` 相对路径解析。
6. manifest 必须记录 resolved absolute path 与 hash。

## 1. 目标

10A 是 Layer 0 density / execution rule system。它不训练模型，不选择 score threshold，只负责把 09 的 selected events 转成可部署的 post-dedup downstream event population。

10A 必须冻结：

```text
post_dedup_population_contract
post_dedup_event_bindings
```

10A 只冻结 event population，不 materialize、不冻结新的 feature matrix 或 sample weights。10B / 10C 必须用 10A 输出的 post-dedup event population 去过滤 / join 09B 已冻结的 feature matrix 与 sample weights。

10B / 10C 的 supported training、threshold selection、gate 与 cascade readout 只能使用 10A 冻结后的 post-dedup event population。

## 2. 输入与依赖

必须读取 09 的最终或可用中间输出：

```text
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09A_fast_fail_label_frontier_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09B_feature_foundation_ablation_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/feature_matrix.parquet
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
```

必须读取上游 source pool 与 membership contract：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_event_instances.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
```

`post_replay_event_episode_membership.parquet` 只服务 E1-missed readout。它缺失或不可读时按 §2.3 降级处理，不触发 population freeze input-blocked。

09 local_cache parquet 是硬依赖，当前预期位于服务器环境。如果任一 local_cache 输入缺失、hash 不匹配，或 eligible risk-on rows 无法按本 requirement 冻结的 composite join key 唯一 join，10A 必须停止：

```text
decision = 10A_density_population_input_blocked
```

禁止用 publishable aggregate table 反推缺失的 event-level binding、feature matrix 或 sample weights。

如果 09 source caveat 未修复，10A 可以继续执行，但所有正向结论必须使用 `source_caveated` variant。

## 2.1 Scope eligibility, denominator mapping, and join keys

10A 的 raw input table 是 09A `selected_label_event_bindings.parquet`，但 10A 只 materialize risk-on selected events。09A 中的 risk-off E1 readonly control rows 是显式 out-of-scope，不得因为缺少 08 R-source join 或 09B feature / weight rows 触发全局 input-blocked。

Scope policy 冻结为：

| 09A `event_regime_bucket` | 09A `source_pool_id` | 10A `input_denominator_id` | 10A treatment | 10A output `denominator_id` | `readout_only_flag` | downstream supported gate |
| --- | --- | --- | --- | --- | --- | --- |
| `risk_on` | `08_R_core_event_regime_gated` | `risk_on_r_core_horizon_complete` | materialize every no-score arm | `post_dedup_risk_on_r_core` | `false` | allowed only if power audit allows |
| `risk_on` | `08_R6_event_regime_gated` | `risk_on_r6_horizon_complete` | materialize every no-score arm as readout-only | `post_dedup_risk_on_r6_readout` | `true` | always false |
| `risk_off` | `07_E1_only` | `risk_off_e1_horizon_complete_readonly` | exclude before rule-arm materialization | `excluded_riskoff_e1_readonly` | `true` | always false |
| any other value | any other value | any other value | stop with input-blocked | n/a | n/a | n/a |

Risk-off E1 excluded rows must be counted in `input_scope_exclusion_audit.csv` and manifest input audit. They must not appear in `post_dedup_event_bindings.parquet`, must not be used for density rules, and must not be silently dropped from the report. They may be mentioned only as an external E1 readonly control.

10A freezes exact join keys:

```text
input_event_key =
    sample_id
    selected_target_id
    input_denominator_id
    canonical_event_id

feature_matrix_join_key =
    sample_id
    selected_target_id
    input_denominator_id
    canonical_event_id

fast_fail_sample_weight_join_key =
    sample_id
    selected_target_id
    input_denominator_id
    canonical_event_id
    weight_horizon_id = fast_fail_10d

cost_bad_sample_weight_join_key =
    sample_id
    selected_target_id
    input_denominator_id
    canonical_event_id
    weight_horizon_id = cost_bad_10_20_20d
```

`input_denominator_id` is a 10A output alias of the upstream 09 denominator field. Upstream parquet files are not required to expose a physical `input_denominator_id` column. 10A must map:

```text
09A selected_label_event_bindings.denominator_id -> input_denominator_id
09B feature_matrix.denominator_id -> input_denominator_id counterpart
09B sample_uniqueness_weights.denominator_id -> input_denominator_id counterpart
```

`split` is a 10A output alias of upstream event split fields. Upstream sample weights do not carry split and must not be used to infer it:

```text
09A selected_label_event_bindings.event_split -> split
09B feature_matrix.event_split -> split counterpart
09B sample_uniqueness_weights has no split column
```

For each eligible risk-on row, 09A `event_split` and the joined 09B feature matrix `event_split` must match exactly after normalization. Split used in all 10A grouping, sorting, output schemas, and power audits must come from the 09A binding row and be cross-checked against the feature matrix. If the feature matrix split is missing or mismatched, 10A must stop with `decision = 10A_density_population_input_blocked`. Sample weights are split-agnostic and may only be joined after split is fixed from binding / feature rows.

`input_event_key` is a 10A-constructed stable string, not an upstream-required column:

```text
input_event_key =
    str(sample_id)
    || "|"
    || str(selected_target_id)
    || "|"
    || str(input_denominator_id)
    || "|"
    || str(canonical_event_id)
```

All four components must be non-null after normalization. If any component is null or maps to more than one upstream row, 10A must stop with `decision = 10A_density_population_input_blocked`. The constructed `input_event_key` is the value used for `admitted_event_id`, deterministic tie-breaks, random-baseline hashes, and output join diagnostics. 09B feature matrix is not required to contain an `input_event_key` column.

`sample_id` alone is explicitly forbidden as a join key because R-core and R6 can share the same `sample_id`. For every eligible risk-on input row, `feature_matrix_join_key` must match exactly one 09B feature row, and each sample-weight join key must match exactly one 09B sample-weight row. If any eligible risk-on row fails these uniqueness checks, 10A must stop with:

```text
decision = 10A_density_population_input_blocked
```

10A may record the frozen 09B join keys in output artifacts, but it must not materialize a new feature matrix and must not recompute sample weights.

## 2.2 Event-level source id contract

10A 的 event-level source fields 必须从 09 local_cache 与 08 event source 唯一 join 出来，不得从 aggregate 表反推。

Canonical join：

```text
09 selected_label_event_bindings.canonical_event_id
    -> 08 candidate_family_canonical_events.canonical_event_id
```

字段来源：

| 10A field | canonical source | policy |
| --- | --- | --- |
| `source_family_id` | `candidate_family_canonical_events.primary_family_id` | required only for `same_family_dedup_10d` |
| `source_family_id_set` | `candidate_family_canonical_events.triggered_family_ids` | audit/readout only |
| `mechanism_id` | normalized `candidate_family_canonical_events.triggered_mechanism_clusters` | required only for `same_mechanism_dedup_10d` |
| `event_window_anchor_pos` | 08 density caliber contract; executable rows use `trade_open_pos` | required for every arm |
| `event_window_anchor_date` | derived from `event_window_anchor_pos` plus trading calendar | required derived audit field |
| `winner_120` | `selected_label_event_bindings.event_big_winner_120d_label` | downstream label/readout only |

`mechanism_id` normalization rule:

```text
split triggered_mechanism_clusters on ";" / "|" / "," delimiters
trim empty values
sort unique tokens
join with ";"
```

If normalization yields no value or multiple source rows join to one `canonical_event_id`, only `same_mechanism_dedup_10d` is arm-blocked unless the affected row also breaks required fields for all other arms.

Date fields ending in `_date` may be copied from 09 local_cache if already present; otherwise they must be derived from position fields using the same trading calendar as 08 density audit. The calendar source path and hash must be recorded in manifest.

Execution anchor policy is frozen:

```text
if non_executable_next_open is false and trade_open_pos is non-null:
    event_window_anchor_pos = trade_open_pos
    event_window_anchor_date = trade_open_date
    event_window_anchor_status = executable_trade_open
    raw_event_status = executable
else:
    event_window_anchor_pos = event_t0_pos
    event_window_anchor_date = event_t0_date
    event_window_anchor_status = non_executable_t0_fallback
    raw_event_status = non_executable_audit_only
    admission_status = non_executable_audit_only
```

Non-executable rows remain in `post_dedup_event_bindings.parquet` for audit, but they must not be counted as admitted events and must not be eligible representatives for suppression.

## 2.3 E1-missed readout contract

`E1_missed_winner_flag` is readout-only. It must not be used for admission, density-rule selection, threshold selection, model fitting, feature construction, or supported-gate pass / fail except where 10C explicitly reports E1-missed retention as a readout.

10A computes E1-missed fields from:

```text
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
```

Required membership columns:

```text
canonical_event_id
candidate_scope_id
target_episode_id
bridge_positive_denominator_included
```

E1 reference episode set:

```text
target_episode_id where
    candidate_scope_id = 07_E1_only
    and target_episode_id is not null
    and bridge_positive_denominator_included = true
```

Per eligible risk-on event:

```text
event_episode_ids =
    target_episode_id values from membership rows where canonical_event_id matches

e1_episode_hit_flag =
    any event_episode_id is in E1 reference episode set

e1_missed_proxy_flag =
    not e1_episode_hit_flag

E1_missed_winner_flag =
    winner_120 == 1 and e1_missed_proxy_flag == true
```

If an eligible risk-on event has no membership rows, 10A must set:

```text
e1_episode_hit_flag = false
e1_missed_proxy_flag = true
E1_missed_winner_flag = winner_120 == 1
e1_missed_proxy_status = no_episode_membership_for_event
```

If the membership parquet is missing, unreadable, or missing required columns, 10A may still freeze the density population, but E1 readouts must be explicitly degraded:

```text
E1_missed_winner_flag = null
e1_episode_hit_flag = null
e1_missed_proxy_flag = null
e1_missed_proxy_status = episode_membership_proxy_input_blocked
false_repair_ml_supported_gate_allowed = false
```

Allowed event-level `e1_missed_proxy_status` values:

```text
episode_level_proxy_from_08_membership
no_episode_membership_for_event
episode_membership_proxy_input_blocked
```

Aggregate tables must not reuse the event-level status domain without rollup. Any aggregate output field named `e1_missed_proxy_status` is a group-level rollup over the table grain, for example `population_id` / `rule_arm_id` / `input_denominator_id` / `denominator_id` / `split`, and additionally `threshold_id` / `capacity_id` where present.

Allowed aggregate `e1_missed_proxy_status` values:

```text
all_episode_level_proxy_from_08_membership
all_no_episode_membership_for_event
mixed_non_blocking
episode_membership_proxy_input_blocked
```

Rollup rule:

```text
if any event-level status is episode_membership_proxy_input_blocked:
    aggregate status = episode_membership_proxy_input_blocked
else if all event-level statuses are episode_level_proxy_from_08_membership:
    aggregate status = all_episode_level_proxy_from_08_membership
else if all event-level statuses are no_episode_membership_for_event:
    aggregate status = all_no_episode_membership_for_event
else:
    aggregate status = mixed_non_blocking
```

`mixed_non_blocking` is expected when some admitted rows have 08 episode membership rows and others do not. It is non-blocking for 10C power gating; only `episode_membership_proxy_input_blocked` blocks the E1-missed readout from supporting 10C.

## 3. 非目标

10A 明确不做：

1. 不训练 ML 模型。
2. 不使用 model score 选择 density rule。
3. 不调 10B / 10C threshold。
4. 不用 validation / robustness 选择 cooldown 参数。
5. 不把 density reduction 解释成 rejector uplift。
6. 不重新定义 fast-fail 或 false-repair label。
7. 不生成新的 feature matrix。
8. 不重算 sample weights。
9. 不在多个 rule arms 之间选择唯一最优 arm。

## 4. Scope 纪律

supported population 只能来自：

```text
event_regime_bucket = risk_on
source_pool_id = 08_R_core_event_regime_gated
input_denominator_id = risk_on_r_core_horizon_complete
denominator_id = post_dedup_risk_on_r_core
readout_only_flag = false
```

R6 只能作为 readout-only scope：

```text
no fit
no feature selection
no threshold selection
no cooldown tuning
no supported gate
```

R6 readout rows must use a distinct denominator:

```text
denominator_id = post_dedup_risk_on_r6_readout
readout_only_flag = true
fast_fail_ml_supported_gate_allowed = false
false_repair_ml_supported_gate_allowed = false
```

禁止在 pre-dedup population 上评 gate，再在 post-dedup population 上部署。

## 5. Rule Arms

10A 必须尝试 materialize 全部预声明无 score rule arms。每个可构造 arm 都是一份 frozen post-dedup population variant，用 `population_id` / `rule_arm_id` 区分；不可构造 arm 必须以 `arm_status = input_blocked` 保留在 contract 中。10A 不选择唯一 winner arm；10B / 10C 若要使用某个 arm 做 supported gate，必须在各自 requirement / config 中预声明 `population_id`，不得根据 validation / robustness 模型读数回选。

`population_id` 命名规则冻结为：

```text
population_id = 10A__{rule_arm_id}
```

10B / 10C 的默认 supported gate population 预声明为：

```text
population_id = 10A__same_instrument_cooldown_10d
denominator_id = post_dedup_risk_on_r_core
```

其他 10A arms 可以输出完整 audit 和 readout，但不得在 10B / 10C 内根据 validation / robustness 结果回选成 supported gate population。

必须输出以下无 score arms：

```text
same_instrument_cooldown_10d
same_family_dedup_10d
same_mechanism_dedup_10d
same_instrument_rolling_cap_10d_cap1
same_instrument_rolling_cap_20d_cap1
```

共同规则：

1. 时间锚点必须使用 08 `density_fast_fail_caliber_contract.md` 的 `event_window_anchor_pos`；可执行 rows 的 anchor 即 `event_window_anchor_pos = trade_open_pos`。
2. non-executable rows 保留为 audit-only，不得进入 admitted post-dedup population。
3. 每个 split / denominator / instrument 内按 `event_window_anchor_pos`, `event_t0_date`, `sample_id` 稳定排序。
4. 同一排序 key 内不得随机 tie-break；必须使用 manifest 中记录的 deterministic tie-break key。
5. 被 suppress 的 raw events 必须保留在 `post_dedup_event_bindings.parquet` 中，标记为 `admission_status = suppressed_by_density_rule`，不得静默丢弃。

arm 定义中的 `window_sessions` 是交易 session 数，不是日历日：

| rule_arm_id | window_sessions | cap | admission rule |
| --- | ---: | ---: | --- |
| `same_instrument_cooldown_10d` | 10 | 1 | 同 instrument 第一个 eligible event admitted；之后 `event_window_anchor_pos <= admitted_anchor_pos + 10` 的 same-instrument event suppress |
| `same_family_dedup_10d` | 10 | 1 | 同 instrument + `source_family_id` 的 10-session window 内只 admit chronologically first event |
| `same_mechanism_dedup_10d` | 10 | 1 | 同 instrument + `mechanism_id` 的 10-session window 内只 admit chronologically first event |
| `same_instrument_rolling_cap_10d_cap1` | 10 | 1 | 任一 same-instrument rolling 10-session window 内 admitted event count 不得超过 1 |
| `same_instrument_rolling_cap_20d_cap1` | 20 | 1 | 任一 same-instrument rolling 20-session window 内 admitted event count 不得超过 1 |

Arm blocking rule：

```text
if an arm-specific required field is missing:
    mark only that arm as arm_status = input_blocked
    keep materializing other arms

if all mandatory no-score arms are input_blocked:
    decision = 10A_density_population_input_blocked

if at least one no-score arm freezes a post-dedup event population:
    10A may output frozen / source_caveated_frozen
    blocked arms remain in rule_arm_contract.csv and report
```

Score-aware arms are not owned by 10A. `score then cooldown`, `cooldown then score`, within-window lowest failure probability, and within-window highest expected utility are deferred to 10B / 10C post-score cascade diagnostics. 10A may mention them as non-goals, but must not materialize them and must not include them in `rule_arm_contract.csv`.

## 6. 必须输出的 Audit

10A 必须输出：

```text
outputs/publishable/tables/10A_density_rule_system/rule_arm_contract.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_population_contract.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_sample_count_by_split.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_label_coverage_audit.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_fast_fail_power_audit.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_false_repair_power_audit.csv
outputs/publishable/tables/10A_density_rule_system/post_dedup_density_audit.csv
outputs/publishable/tables/10A_density_rule_system/power_audit_config.csv
outputs/publishable/tables/10A_density_rule_system/input_scope_exclusion_audit.csv
outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet
outputs/manifests/10A_density_rule_system_manifest.json
outputs/publishable/reports/10A_density_rule_system_report.md
```

`rule_arm_contract.csv` 至少包含：

```text
population_id
rule_arm_id
rule_arm_type
window_sessions
cap
uses_score_flag
admission_order_key
tie_break_key
execution_anchor_policy
non_executable_policy
arm_status
arm_block_reason
```

`arm_status` 取值域冻结为：

```text
materialized
input_blocked
diagnostic_only
```

`post_dedup_population_contract.csv` 至少按 `population_id` / split / denominator 报告：

```text
population_id
rule_arm_id
input_denominator_id
denominator_id
split
readout_only_flag
sample_n
evaluable_event_n
admitted_event_n
suppressed_event_n
non_executable_audit_only_n
winner_n
E1_missed_winner_n
fast_fail_positive_n
fast_fail_winner_n
false_repair_positive_n
hybrid_positive_n
unique_instrument_n
unique_event_day_n
formal_event_day_density
p95_density
rolling_10d_executable_event_day_density
rolling_20d_executable_event_day_density
```

`post_dedup_sample_count_by_split.csv` 至少包含：

```text
population_id
rule_arm_id
input_denominator_id
denominator_id
split
readout_only_flag
input_row_n
eligible_risk_on_row_n
admitted_event_n
suppressed_event_n
non_executable_audit_only_n
unique_sample_n
unique_instrument_n
feature_matrix_joined_n
fast_fail_weight_joined_n
cost_bad_weight_joined_n
sample_count_status
```

`post_dedup_label_coverage_audit.csv` 至少包含：

```text
population_id
rule_arm_id
input_denominator_id
denominator_id
split
readout_only_flag
admitted_event_n
horizon_complete_10d_n
horizon_complete_20d_n
horizon_complete_120d_n
selected_fast_fail_10_label_nonnull_n
frozen_false_repair_20d_label_nonnull_n
selected_cost_bad_10_20_target_nonnull_n
winner_120_nonnull_n
E1_missed_winner_flag_nonnull_n
e1_missed_proxy_status
e1_status_episode_level_proxy_from_08_membership_n
e1_status_no_episode_membership_for_event_n
e1_status_episode_membership_proxy_input_blocked_n
label_coverage_status
```

`post_dedup_density_audit.csv` 至少包含：

```text
population_id
rule_arm_id
input_denominator_id
denominator_id
split
readout_only_flag
instrument
event_day_n
admitted_event_n
suppressed_event_n
formal_event_day_density
p50_density
p95_density
max_density
rolling_10d_executable_event_day_density
rolling_20d_executable_event_day_density
density_audit_status
```

`input_scope_exclusion_audit.csv` 至少包含：

```text
input_denominator_id
source_pool_id
event_regime_bucket
excluded_row_n
excluded_unique_sample_n
exclusion_reason
feature_matrix_join_attempted_flag
sample_weight_join_attempted_flag
post_dedup_materialized_flag
```

`post_dedup_event_bindings.parquet` 是 10A 的核心产物，必须一行对应一个 eligible risk-on 09 selected event x `population_id`，至少包含：

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
source_family_id_set
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
e1_episode_hit_flag
e1_missed_proxy_flag
e1_missed_proxy_status
feature_matrix_join_key
fast_fail_sample_weight_join_key
cost_bad_sample_weight_join_key
```

`source_family_id`、`mechanism_id`、`source_family_id_set` must be present as columns in `post_dedup_event_bindings.parquet`, but they are arm-specific source fields, not global required fields. For instrument-only arms (`same_instrument_cooldown_10d`, `same_instrument_rolling_cap_10d_cap1`, `same_instrument_rolling_cap_20d_cap1`), these fields may be null and must not trigger global input-blocked. Missing `source_family_id` blocks only `same_family_dedup_10d`; missing or non-normalizable `mechanism_id` blocks only `same_mechanism_dedup_10d`.

`admission_status` 取值域冻结为：

```text
admitted
suppressed_by_density_rule
non_executable_audit_only
arm_input_blocked
```

`event_window_anchor_status` 取值域冻结为：

```text
executable_trade_open
non_executable_t0_fallback
```

Admission binding fields are frozen:

```text
if admission_status = admitted:
    admitted_event_id = input_event_key
    representative_sample_id = sample_id
    suppressed_by_sample_id = null
    suppression_reason = not_suppressed

if admission_status = suppressed_by_density_rule:
    admitted_event_id = input_event_key of the admitted representative that caused suppression
    representative_sample_id = sample_id of that admitted representative
    suppressed_by_sample_id = representative_sample_id
    suppression_reason = {rule_arm_id}_window

if admission_status = non_executable_audit_only:
    admitted_event_id = null
    representative_sample_id = null
    suppressed_by_sample_id = null
    suppression_reason = non_executable_next_open

if admission_status = arm_input_blocked:
    admitted_event_id = null
    representative_sample_id = null
    suppressed_by_sample_id = null
    suppression_reason = arm_input_blocked
```

For rolling cap arms, the admitted representative that caused suppression is the earliest admitted event inside the violated rolling window after sorting by `admission_order_key`.

Allowed `suppression_reason` values:

```text
not_suppressed
same_instrument_cooldown_10d_window
same_family_dedup_10d_window
same_mechanism_dedup_10d_window
same_instrument_rolling_cap_10d_cap1_window
same_instrument_rolling_cap_20d_cap1_window
non_executable_next_open
arm_input_blocked
```

如果 global required fields 无法从 09 local_cache 或 08 source contract 唯一重建，必须全局 input-blocked。Global required fields:

```text
input_event_key
sample_id
selected_target_id
input_denominator_id
denominator_id
split
instrument
event_t0_pos
event_window_anchor_pos
event_window_anchor_status
source_pool_id
selected_fast_fail_10_label
frozen_false_repair_20d_label
selected_cost_bad_10_20_target
winner_120
feature_matrix_join_key
fast_fail_sample_weight_join_key
cost_bad_sample_weight_join_key
```

如果只缺 arm-specific fields，例如 `source_family_id` 或 `mechanism_id`，只 block 对应 arm，不得降级其他 instrument-only arms，也不得使用 aggregate-only population freeze。

## 7. 10B Power Audit Contract

`post_dedup_fast_fail_power_audit.csv` 是 10B 的 ML go / no-go 输入，至少包含：

10A 的 power audit 只做 frozen capacity count，不做 threshold tuning。capacity grid、random seed、minimum count gates 与 structural baseline rank rule 必须写入共享 config，并写入 manifest hash：

```text
outputs/publishable/tables/10A_density_rule_system/power_audit_config.csv
```

Minimum config fields:

```text
component_id
capacity_id
reject_fraction
threshold_id
random_seed
random_tie_break_key
rule_baseline_id
rule_baseline_owner
rule_baseline_required_features
min_positive_count
min_winner_count
min_rule_positive_count
min_rule_winner_count
capture_lift_margin
winner_retention_floor
wrong_kill_rate_cap
```

`power_audit_config.csv` 必须至少包含以下 frozen rows：

| component_id | capacity_id | threshold_id | reject_fraction | random_seed | random_tie_break_key | rule_baseline_id | rule_baseline_owner | rule_baseline_required_features | min_positive_count | min_winner_count | min_rule_positive_count | min_rule_winner_count | capture_lift_margin | winner_retention_floor | wrong_kill_rate_cap |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `fast_fail_10d` | `keep_9000` | `keep_9000` | 0.1000 | 20260615 | `sha256_input_event_key_capacity_seed` | `structural_swing_low_rank_v1` | `10B` | `close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct` | 100 | 20 | 10 | 3 | 0.0200 | 0.9400 | 0.0600 |
| `fast_fail_10d` | `keep_9250` | `keep_9250` | 0.0750 | 20260615 | `sha256_input_event_key_capacity_seed` | `structural_swing_low_rank_v1` | `10B` | `close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct` | 100 | 20 | 10 | 3 | 0.0200 | 0.9400 | 0.0600 |
| `fast_fail_10d` | `keep_9300` | `keep_9300` | 0.0700 | 20260615 | `sha256_input_event_key_capacity_seed` | `structural_swing_low_rank_v1` | `10B` | `close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct` | 100 | 20 | 10 | 3 | 0.0200 | 0.9400 | 0.0600 |
| `fast_fail_10d` | `keep_9400` | `keep_9400` | 0.0600 | 20260615 | `sha256_input_event_key_capacity_seed` | `structural_swing_low_rank_v1` | `10B` | `close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct` | 100 | 20 | 10 | 3 | 0.0200 | 0.9400 | 0.0600 |
| `fast_fail_10d` | `keep_9500` | `keep_9500` | 0.0500 | 20260615 | `sha256_input_event_key_capacity_seed` | `structural_swing_low_rank_v1` | `10B` | `close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct` | 100 | 20 | 10 | 3 | 0.0200 | 0.9400 | 0.0600 |
| `fast_fail_10d` | `keep_9600` | `keep_9600` | 0.0400 | 20260615 | `sha256_input_event_key_capacity_seed` | `structural_swing_low_rank_v1` | `10B` | `close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct` | 100 | 20 | 10 | 3 | 0.0200 | 0.9400 | 0.0600 |
| `fast_fail_10d` | `keep_9700` | `keep_9700` | 0.0300 | 20260615 | `sha256_input_event_key_capacity_seed` | `structural_swing_low_rank_v1` | `10B` | `close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct` | 100 | 20 | 10 | 3 | 0.0200 | 0.9400 | 0.0600 |
| `false_repair_20d_component` | `keep_8000` | `keep_8000` | 0.2000 | 20260615 | `sha256_input_event_key_capacity_seed` | `none` | `10C` | `none` | 300 | 100 | 0 | 0 | 0.0000 | 0.8500 | 0.1500 |
| `false_repair_20d_component` | `keep_8250` | `keep_8250` | 0.1750 | 20260615 | `sha256_input_event_key_capacity_seed` | `none` | `10C` | `none` | 300 | 100 | 0 | 0 | 0.0000 | 0.8500 | 0.1500 |
| `false_repair_20d_component` | `keep_8500` | `keep_8500` | 0.1500 | 20260615 | `sha256_input_event_key_capacity_seed` | `none` | `10C` | `none` | 300 | 100 | 0 | 0 | 0.0000 | 0.8500 | 0.1500 |
| `false_repair_20d_component` | `keep_8750` | `keep_8750` | 0.1250 | 20260615 | `sha256_input_event_key_capacity_seed` | `none` | `10C` | `none` | 300 | 100 | 0 | 0 | 0.0000 | 0.8500 | 0.1500 |
| `false_repair_20d_component` | `keep_9000` | `keep_9000` | 0.1000 | 20260615 | `sha256_input_event_key_capacity_seed` | `none` | `10C` | `none` | 300 | 100 | 0 | 0 | 0.0000 | 0.8500 | 0.1500 |

For `fast_fail_10d` rows, `rule_baseline_required_features` must equal:

```text
close_to_ema60;ema60_slope_20d;return_20d;stock_vs_market_20d;atr_20_pct
```

These five feature IDs are a hard 09B feature contract dependency. Each feature must be uniquely registered in 09B `feature_contract.csv` with `allowed_for_09C_flag = true`, and each corresponding feature column must exist in 09B `feature_matrix.parquet`. 10A must use the feature matrix columns by these exact `feature_id` names; it must not infer replacements from feature family names, recompute the features, or substitute similarly named columns. If any required feature ID is missing from the 09B contract, duplicated in the contract, has `allowed_for_09C_flag != true`, is missing from the feature matrix, or cannot be uniquely joined by the frozen feature join key, then `rule_baseline_status = input_blocked`, `capture_lift_power_status = rule_baseline_input_blocked`, and `fast_fail_ml_supported_gate_allowed = false`; random-baseline counts must still be emitted.

For `false_repair_20d_component` rows, `rule_baseline_required_features = none` and `rule_baseline_id = none`.

Random baseline is deterministic: within each `population_id` / `denominator_id` / `split`, sort admitted rows by:

```text
sha256(input_event_key || capacity_id || random_seed) ascending
input_event_key ascending
```

and reject the first `ceil(post_dedup_sample_n * reject_fraction)` rows.

`rule_baseline_id = structural_swing_low_rank_v1` is a frozen 10B-owned structural-stop null, not a 10A density arm and not a trained model. 10A may compute only its capacity-matched count readout by joining admitted rows to the frozen 09B feature matrix and ranking rows by the following deterministic tuple:

```text
close_to_ema60 ascending nulls last
ema60_slope_20d ascending nulls last
return_20d ascending nulls last
stock_vs_market_20d ascending nulls last
atr_20_pct descending nulls last
input_event_key ascending
```

For each capacity, `structural_swing_low_rank_v1` rejects the first `ceil(post_dedup_sample_n * reject_fraction)` rows by this tuple. If any required feature is missing or non-uniquely joined, `rule_baseline_status = input_blocked`, `capture_lift_power_status = rule_baseline_input_blocked`, and `fast_fail_ml_supported_gate_allowed = false`; random-baseline counts must still be emitted.

```text
population_id
rule_arm_id
input_denominator_id
denominator_id
split
readout_only_flag
threshold_id
capacity_id
post_dedup_sample_n
post_dedup_fast_fail_positive_n
post_dedup_fast_fail_winner_n
post_dedup_winner_n
random_rejected_fast_fail_positive_n
random_rejected_fast_fail_winner_n
random_rejected_fast_fail_non_winner_n
rule_baseline_rejected_fast_fail_positive_n
rule_baseline_rejected_fast_fail_winner_n
rule_baseline_rejected_fast_fail_non_winner_n
rule_baseline_status
capture_lift_power_status
winner_injury_power_status
fast_fail_ml_supported_gate_allowed
```

Power status rules are frozen:

```text
capture_lift_power_status = pass
    only if post_dedup_fast_fail_positive_n >= min_positive_count
    and random_rejected_fast_fail_positive_n >= min_rule_positive_count
    and rule_baseline_rejected_fast_fail_positive_n >= min_rule_positive_count

winner_injury_power_status = pass
    only if post_dedup_fast_fail_winner_n >= min_winner_count
    and random_rejected_fast_fail_winner_n >= min_rule_winner_count
    and rule_baseline_rejected_fast_fail_winner_n >= min_rule_winner_count

fast_fail_ml_supported_gate_allowed = true
    only for denominator_id = post_dedup_risk_on_r_core
    and readout_only_flag = false
    and capture_lift_power_status = pass
    and winner_injury_power_status = pass
    and rule_baseline_status = pass
```

If any of these conditions fail, 10B must consume the row as diagnostic only and must not claim supported ML fast-fail gate.

## 8. 10C Power Audit Contract

`post_dedup_false_repair_power_audit.csv` 是 10C 的支持性输入，至少包含：

```text
population_id
rule_arm_id
input_denominator_id
denominator_id
split
readout_only_flag
threshold_id
capacity_id
post_dedup_sample_n
post_dedup_false_repair_positive_n
post_dedup_winner_n
post_dedup_E1_missed_winner_n
e1_missed_proxy_status
post_dedup_e1_status_episode_level_proxy_from_08_membership_n
post_dedup_e1_status_no_episode_membership_for_event_n
post_dedup_e1_status_episode_membership_proxy_input_blocked_n
random_rejected_false_repair_positive_n
random_rejected_false_repair_winner_n
random_rejected_E1_missed_winner_n
random_rejected_false_repair_non_winner_n
false_repair_power_status
winner_retention_power_status
false_repair_ml_supported_gate_allowed
```

For 10C, status rules are frozen:

```text
false_repair_power_status = pass
    only if post_dedup_false_repair_positive_n >= min_positive_count

winner_retention_power_status = pass
    only if post_dedup_winner_n >= min_winner_count

false_repair_ml_supported_gate_allowed = true
    only for denominator_id = post_dedup_risk_on_r_core
    and readout_only_flag = false
    and false_repair_power_status = pass
    and winner_retention_power_status = pass
    and e1_missed_proxy_status != episode_membership_proxy_input_blocked
```

10A does not select a 10C threshold and does not prove final 10C winner retention. 10A only freezes the capacity grid and count constraints; 10C must later prove `winner_retention >= winner_retention_floor`.

## 9. 决策状态

10A 决策必须使用以下之一：

```text
10A_density_population_frozen
10A_density_population_source_caveated_frozen
10A_density_population_diagnostic_only
10A_density_population_input_blocked
```

只有 `10A_density_population_frozen` 或 `10A_density_population_source_caveated_frozen` 允许 10B / 10C 进入 supported gate。
