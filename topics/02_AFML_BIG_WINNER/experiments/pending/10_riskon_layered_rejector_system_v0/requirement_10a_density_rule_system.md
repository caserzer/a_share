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
```

09 local_cache parquet 是硬依赖，当前预期位于服务器环境。如果任一 local_cache 输入缺失、hash 不匹配或无法按 sample key 唯一 join，10A 必须停止：

```text
decision = 10A_density_population_input_blocked
```

禁止用 publishable aggregate table 反推缺失的 event-level binding、feature matrix 或 sample weights。

如果 09 source caveat 未修复，10A 可以继续执行，但所有正向结论必须使用 `source_caveated` variant。

## 2.1 Event-level source id contract

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

`mechanism_id` normalization rule:

```text
split triggered_mechanism_clusters on ";" / "|" / "," delimiters
trim empty values
sort unique tokens
join with ";"
```

If normalization yields no value or multiple source rows join to one `canonical_event_id`, only `same_mechanism_dedup_10d` is arm-blocked unless the affected row also breaks required fields for all other arms.

Date fields ending in `_date` may be copied from 09 local_cache if already present; otherwise they must be derived from position fields using the same trading calendar as 08 density audit. The calendar source path and hash must be recorded in manifest.

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
source_pool = 08_R_core_event_regime_gated
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

arm 定义：

| rule_arm_id | admission rule |
| --- | --- |
| `same_instrument_cooldown_10d` | 同 instrument 第一个 eligible event admitted；之后 `event_window_anchor_pos <= admitted_anchor_pos + 10` 的 same-instrument event suppress |
| `same_family_dedup_10d` | 同 instrument + `source_family_id` 的 10D window 内只 admit chronologically first event |
| `same_mechanism_dedup_10d` | 同 instrument + `mechanism_id` 的 10D window 内只 admit chronologically first event |
| `same_instrument_rolling_cap_10d_cap1` | 任一 same-instrument rolling 10D window 内 admitted event count 不得超过 1 |
| `same_instrument_rolling_cap_20d_cap1` | 任一 same-instrument rolling 20D window 内 admitted event count 不得超过 1 |

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

`post_dedup_event_bindings.parquet` 是 10A 的核心产物，必须一行对应一个 09 raw selected event x `population_id`，至少包含：

```text
population_id
rule_arm_id
sample_id
selected_target_id
denominator_id
split
instrument
event_t0_date
event_t0_pos
event_window_anchor_date
event_window_anchor_pos
event_window_anchor_status
source_pool
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
sample_weight_join_key
feature_matrix_join_key
```

`admission_status` 取值域冻结为：

```text
admitted
suppressed_by_density_rule
non_executable_audit_only
arm_input_blocked
```

如果 global required fields 无法从 09 local_cache 或 08 source contract 唯一重建，必须全局 input-blocked。Global required fields:

```text
sample_id
selected_target_id
denominator_id
split
instrument
event_t0_pos
event_window_anchor_pos
event_window_anchor_status
selected_fast_fail_10_label
frozen_false_repair_20d_label
selected_cost_bad_10_20_target
winner_120
sample_weight_join_key
feature_matrix_join_key
```

如果只缺 arm-specific fields，例如 `source_family_id` 或 `mechanism_id`，只 block 对应 arm，不得降级其他 instrument-only arms，也不得使用 aggregate-only population freeze。

## 7. 10B Power Audit Contract

`post_dedup_fast_fail_power_audit.csv` 是 10B 的 ML go / no-go 输入，至少包含：

10A 的 power audit 只做 predeclared capacity count，不做 threshold tuning。capacity grid、random seed 与 10B structural rule baseline 必须来自共享预声明 config，并写入 manifest hash：

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
```

`rule_baseline_id` for 10B must be the predeclared swing-low structural-stop baseline owned by 10B, not the best 10A density arm. 10A only evaluates expected count / power implications of that baseline on each frozen population.

```text
population_id
denominator_id
split
readout_only_flag
threshold_id
capacity_id
post_dedup_sample_n
post_dedup_fast_fail_positive_n
post_dedup_fast_fail_winner_n
random_rejected_fast_fail_positive_n
random_rejected_fast_fail_winner_n
random_rejected_fast_fail_non_winner_n
rule_baseline_rejected_fast_fail_positive_n
rule_baseline_rejected_fast_fail_winner_n
rule_baseline_rejected_fast_fail_non_winner_n
capture_lift_power_status
winner_injury_power_status
fast_fail_ml_supported_gate_allowed
```

如果 post-dedup fast-fail positive 或 winner count 低于预声明下限，10B 必须降级为 rule-based structural stop diagnostic。

## 8. 10C Power Audit Contract

`post_dedup_false_repair_power_audit.csv` 是 10C 的支持性输入，至少包含：

```text
population_id
denominator_id
split
readout_only_flag
capacity_id
post_dedup_sample_n
post_dedup_false_repair_positive_n
post_dedup_winner_n
post_dedup_E1_missed_winner_n
random_rejected_false_repair_positive_n
rule_rejected_false_repair_positive_n
false_repair_ml_supported_gate_allowed
```

如果 post-dedup 后 false-repair positive count 或 winner retention denominator 不足，10C 只能输出 diagnostic。

## 9. 决策状态

10A 决策必须使用以下之一：

```text
10A_density_population_frozen
10A_density_population_source_caveated_frozen
10A_density_population_diagnostic_only
10A_density_population_input_blocked
```

只有 `10A_density_population_frozen` 或 `10A_density_population_source_caveated_frozen` 允许 10B / 10C 进入 supported gate。
