# 需求：Experiment E - Risk-on Post-Filter Replay Cost Rejector

## 1. 背景

Experiment A / B / C / D 已经把 08 的下一步方向修正清楚：

1. `07_E1_only` 仍是当前候选体系的干净 backbone，不应被移除。
2. `risk_on` 的主要问题已经不是找不到 recall source，而是 R-series 事件的 `fast-fail` / `false-repair` 成本过高。
3. Experiment C 证明 entry-ranker / density compression 主线没有解决成本问题：所有 C arms 都停在 `diagnostic_only_or_no_candidate`，direct-entry pass 0，feature-source pass 0。
4. Experiment D 补齐了 post-replay event-to-episode membership source：本地 membership 有 `357,450` 行，06 episode window `4,986/4,986` ready，C arm pre-replay 对账 `189/189 pass`，leakage audit pass。
5. D 的 final decision 是 `post_replay_retention_source_source_caveated_complete`，且 `entry_support_allowed = false`，所以 D 是下游 rejector 的 source layer，不是 entry gate。

D 的 risk_on 读数已经足够支持切换问题定义：

| source | split | post-replay any recall | E1-missed denominator | E1-missed post-replay capture |
| --- | --- | ---: | ---: | ---: |
| `08_R_core_event_regime_gated` | train | 98.22% | 83 | 80 |
| `08_R_core_event_regime_gated` | robustness | 94.48% | 92 | 84 |
| `08_R6_event_regime_gated` | train | 96.00% | 83 | 77 |
| `08_R6_event_regime_gated` | robustness | 90.06% | 92 | 77 |

因此 Experiment E 的任务不是继续扩 R-series family、不是重做 C 的 entry-ranker，也不是做 transition 修复。E 的任务是：

```text
在 risk_on regime 中，训练一个只使用 t0 可见特征的 post-filter cost rejector，
筛掉 fast-fail / false-repair 高风险事件，同时尽量保留 R-core / R6 已经证明存在的
bridge / E1-missed post-replay capture。
```

## 2. Primary Question

Experiment E 必须回答：

```text
Can a train-only supervised cost rejector reduce risk_on fast-fail / false-repair
cost from R-series post-replay recall sources while preserving bridge-positive
and E1-missed episode capture out of sample?
```

中文等价问题：

```text
能否在不使用未来标签作为 t0 特征的前提下，训练一个 risk_on 成本 rejector，
把 R-core / R6 中最容易快速失败或假修复的事件过滤掉，并在 robustness split
仍保留足够的 bridge / E1-missed capture？
```

## 3. 范围

Experiment E 只覆盖：

1. `risk_on` target regime。
2. R-series post-replay source 的成本过滤。
3. supervised rejector / meta-label source 设计。
4. post-filter 后的 replay retention、density、fast-fail、false-repair、OOS separability audit。

Experiment E 不覆盖：

1. `transition` sub-regime taxonomy audit。
2. transition family rediscovery。
3. 新 event family 发明。
4. C 的 entry-ranker / density compression arm grid 延伸。
5. 交易策略、组合回测、止盈止损、仓位模拟。

`transition` 在 E 中最多可作为报告中的 negative context，不得参与训练、阈值选择或 final support。

## 4. Required Inputs

### 4.1 上游 manifests

必须读取：

```text
outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
outputs/manifests/regime_family_matrix/regime_family_matrix_manifest.json
outputs/manifests/risk_on_r_series_bridge_ranker/risk_on_r_series_bridge_ranker_manifest.json
outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
```

允许的上游 final decisions：

| experiment | allowed decisions |
| --- | --- |
| A | `density_fast_fail_audit_complete`, `density_fast_fail_audit_partial_source_complete` |
| B | `regime_family_matrix_complete`, `regime_family_matrix_source_caveated_complete` |
| C | `risk_on_r_series_ranker_complete`, `risk_on_r_series_ranker_source_caveated_complete` |
| D | `post_replay_retention_source_complete`, `post_replay_retention_source_source_caveated_complete` |

若 D manifest 缺失、D decision 不在允许列表、或 D `entry_support_allowed != false` / `oracle_policies_audit_only != true`，必须停止并输出：

```text
risk_on_cost_rejector_input_blocked
```

若 A / B / C / D 任一上游是 source-caveated 完成态，Experiment E 可以继续，但最终 decision 必须带 `source_caveated` 后缀；报告不得声称 production-ready entry gate。

### 4.2 D post-replay source

硬输入：

```text
outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_scope_retention_by_split_regime.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_e1_missed_retention_summary.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_policy_effect_summary.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_source_coverage_audit.csv
outputs/publishable/reports/post_replay_event_to_episode_retention_source/post_replay_retention_source_contract.md
```

D local membership 必须满足：

1. row count 与 manifest 一致。
2. schema fingerprint 与 manifest 一致。
3. hash 与 manifest 一致。
4. `post_replay_label_leakage_audit.csv` 全部 `leakage_status = pass`。
5. `post_replay_scope_retention_by_split_regime.csv` 中 risk_on / train / robustness 的 R-core 与 R6 binding values 与本需求第 6 节一致。

任一不满足，停止并输出：

```text
risk_on_cost_rejector_d_source_blocked
```

### 4.3 Event / label / feature sources

必须读取：

```text
outputs/publishable/tables/candidate_family_canonical_events.csv.gz
outputs/publishable/tables/candidate_family_event_instances.csv.gz
outputs/local_cache/candidate_family_event_labels.parquet
outputs/local_cache/candidate_family_capture.parquet
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
```

`candidate_scope_mapping_contract.csv` 与 `candidate_scope_reconstructability_audit.csv` 是
R6 / R-core / R1 source-pool reconstruction 的 source of truth。E 不得用临时字符串匹配、
手写 family list 或 C compression frontier 的 aggregate rows 直接重建训练池。

监督式 rejector 需要 t0 feature source。优先使用：

```text
outputs/local_cache/cross_section_feature_panel.parquet
```

如果 `cross_section_feature_panel.parquet` 缺失，E 仍必须输出 input / label / source audit，但所有 supervised arms 必须 fail closed：

```text
rejector_arm_status = supervised_feature_source_blocked_missing_cross_section_panel
```

此时 final decision 只能是：

```text
risk_on_cost_rejector_feature_source_blocked
```

除非实现提供了等价的、可 hash 审计的 t0 feature table，并在 `risk_on_cost_rejector_feature_contract.csv` 中逐字段证明没有未来信息。

### 4.4 07 E1 baseline

必须读取：

```text
../07_topn_multichannel_repair_candidate_generator_v0/outputs/manifests/run_manifest.json
../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv
../07_topn_multichannel_repair_candidate_generator_v0/outputs/local_cache/topn_canonical_event_labels.parquet
```

`07_E1_only` 是 baseline 和 E1-missed denominator 的来源。如果不能重建 E1 baseline，停止并输出：

```text
risk_on_cost_rejector_e1_baseline_blocked
```

### 4.5 Scope reconstruction contract

E 必须通过 A 的 scope mapping contract 重建所有 source pool：

1. `07_E1_only`
2. `08_R6_event_regime_gated`
3. `08_R_core_event_regime_gated`
4. `08_R1_event_regime_gated`
5. 任何被纳入 E 的 C diagnostic arm 或 deterministic baseline。

重建规则：

1. `candidate_scope_mapping_contract.csv` 是 `source_artifact_path`、`source_row_filter`、`canonicalization_rule` 与 `reconstructability_requirement` 的唯一权威来源。
2. `candidate_scope_reconstructability_audit.csv` 是 `scope_status`、`hard_gate_eligible_flag` 与 event-level label/source availability 的唯一权威来源。
3. 只有 `scope_status = reconstructable_event_membership` 且 `hard_gate_eligible_flag = true` 的 scope 才能进入 supervised rejector 或 research-entry gate。
4. `08_R_compression_arm::*` 这类 `aggregate_frontier_only_no_event_membership` rows 只能作为历史 diagnostic context，不得作为 E 的训练样本、threshold frontier、density gate 或 replay retention source。
5. 如果 `08_R6_event_regime_gated`、`08_R_core_event_regime_gated` 或 `08_R1_event_regime_gated` 无法按 mapping contract 重建，必须停止并输出：

```text
risk_on_cost_rejector_scope_reconstruction_blocked
```

6. Scope count binding 以 `candidate_scope_reconstructability_audit.csv` 的
   `source_row_count` 为重建基准，不以 `published_reference_event_count` 为硬相等基准。
   `published_reference_event_count` 只用于解释上游 published readout 的参考计数。
7. `08_R_core_event_regime_gated` 已由 A 记录并接受
   `source_row_count = 47914`、`published_reference_event_count = 47929`、
   `reconstructed_vs_published_count_difference = -15.0`，且
   `scope_status = reconstructable_event_membership`、`hard_gate_eligible_flag = true`。
   E 必须把这一已审计差异写入 `risk_on_cost_rejector_scope_reconstruction_audit.csv`，
   不得因此阻断 R-core source pool。
8. 只有当 reconstructed event count 与 `source_row_count` 不一致，或 audit 中未记录的
   新差异出现时，才停止并输出：

```text
risk_on_cost_rejector_scope_binding_drift_blocked
```

9. 报告与 `risk_on_cost_rejector_input_audit.csv` 必须列出每个 source pool 的 mapping row、source hash、row filter、reconstructed event count、source row count、published reference count、count difference、accepted difference reason 与 hard-gate eligibility。

## 5. Regime / Split 纪律

### 5.1 Regime 字段

E 必须区分：

1. `event_regime_bucket`：event t0 / replay anchor date 上可观测的市场 regime，可作为 t0 feature 或 gating feature。
2. `episode_regime_bucket`：target episode low date 或 D membership 中的 target regime，用于 recall / bridge / E1-missed retention readout。

Regime 字段必须按 source artifact 解释，不能只按列名解释。

D publishable summary tables 中：

```text
post_replay_scope_retention_by_split_regime.csv.market_regime_bucket = episode_regime_bucket
post_replay_arm_retention_by_split_regime.csv.market_regime_bucket = episode_regime_bucket
post_replay_e1_missed_retention_summary.csv.market_regime_bucket = episode_regime_bucket
post_replay_policy_effect_summary.csv.market_regime_bucket = episode_regime_bucket
```

D membership parquet 中：

```text
post_replay_event_episode_membership.parquet.market_regime_bucket = event_regime_bucket
post_replay_event_episode_membership.parquet.market_regime_bucket_canonical = event_regime_bucket
post_replay_event_episode_membership.parquet.market_regime_bucket_episode = episode_regime_bucket
post_replay_event_episode_membership.parquet.episode_market_regime_bucket = episode_regime_bucket
```

08 event sources 中：

```text
candidate_family_canonical_events.csv.gz.event_regime_bucket = event_regime_bucket
candidate_family_canonical_events.csv.gz.market_regime_bucket = event_regime_bucket
candidate_family_event_labels.parquet.event_split = event_split
```

E 必须在输出中显式重命名或审计：

```text
regime_column_role_by_source_artifact
```

不得把 D summary tables 的 episode-side `market_regime_bucket` 误当成 event t0 feature；
也不得把 D membership parquet 的 event-side `market_regime_bucket` 误当成 episode-side
headline denominator。

### 5.2 Target regime

Primary target：

```text
episode_regime_bucket = risk_on
```

训练样本可使用 t0 可见的 `event_regime_bucket = risk_on` 作为 candidate gate，但必须保留审计：

1. gate 前后 event count。
2. gate 前后 label completeness。
3. gate 前后 fast-fail / false-repair rate。
4. gate 前后 post-replay E1-missed capture。

若 event-level regime 缺失，不能用 episode regime 替代 event regime 来训练或 gate；只能输出 source-blocked 或 diagnostic-only。

### 5.3 Split 字段

E 必须区分：

1. `event_split`：用于 supervised model fit、event-level OOS separability、cost label evaluation。
2. `episode_split`：用于 post-replay any / bridge / E1-missed retention readout。

训练、特征选择、模型选择、阈值选择只能使用 train split。Validation 与 robustness 只读。

Supervised event-level cost model 的训练样本以 `event_split = train` 为准，non-target
events 不要求存在 `episode_split`，必须继续保留。只有 replay-retention threshold
约束、headline support / block readout 与 post-filter episode retention 需要 split-aligned
membership rows。

用于 replay-retention threshold 约束的 train rows 必须同时满足：

```text
event_split = train
episode_split = train
```

也就是说：

1. supervised fit、feature selection、model selection、cost-label threshold candidate generation 只能使用 `event_split = train` 的 cost labels。
2. 若 threshold selection 使用 train replay retention 约束，该 retention 只能从 `event_split = train` 且 `episode_split = train` 的 membership rows 计算。
3. validation headline readout 必须使用 `event_split = validation` 且 `episode_split = validation` 的 rows。
4. robustness headline readout 必须使用 `event_split = robustness` 且 `episode_split = robustness` 的 rows。
5. `event_split != episode_split` 的 membership rows 必须保留在 `risk_on_cost_rejector_split_alignment_audit.csv` 中，但不得参与 threshold selection 或 headline support / block。

由于 validation risk_on denominator 很小，validation risk_on 只能作为 diagnostic，不得支持或阻止 final candidate；robustness 是主要 OOS support / block split。

## 6. Binding Values

以下数值是 load-time bindings，不是背景说明。实现必须从 D outputs 校验，容差为：

1. count 字段必须完全一致；scope reconstruction count 例外按第 4.5 节执行，以
   `source_row_count` 为硬基准，已审计的 R-core `-15` published-reference 差异不得阻断。
2. rate 字段按百分比展示时允许 `0.01` percentage point 以内的四舍五入误差。
3. hash / row count 必须与 manifest 完全一致。

### 6.1 D source binding

| field | required value |
| --- | --- |
| D decision | `post_replay_retention_source_source_caveated_complete` or `post_replay_retention_source_complete` |
| D local membership row count | `357450` |
| D episode window audit rows | `4986` |
| D C-arm reconciliation | `189/189 pass` |
| D `entry_support_allowed` | `false` |
| D `oracle_policies_audit_only` | `true` |

若绑定漂移，停止并输出：

```text
risk_on_cost_rejector_binding_drift_blocked
```

报告必须列出 stale field、expected value、source value、source artifact。

### 6.2 Risk-on source binding

`window = low_to_first_50pct`，`replay_policy_id = post_replay_executable_horizon_complete`。

| source | split | target_episode_n | post_replay_any_recall | E1-missed n | E1-missed post-replay capture |
| --- | --- | ---: | ---: | ---: | ---: |
| `08_R_core_event_regime_gated` | train | 225 | 98.22% | 83 | 80 |
| `08_R_core_event_regime_gated` | robustness | 181 | 94.48% | 92 | 84 |
| `08_R6_event_regime_gated` | train | 225 | 96.00% | 83 | 77 |
| `08_R6_event_regime_gated` | robustness | 181 | 90.06% | 92 | 77 |

这些绑定说明 R-core / R6 是 recall source。E 的目标是成本过滤，不是重新证明 recall source 存在。

## 7. Candidate Universe

### 7.1 Baselines

必须包含：

1. `07_E1_only`：clean baseline。
2. `08_R6_event_regime_gated`：primary compact recall source。
3. `08_R_core_event_regime_gated`：wide recall source / stress pool。
4. `08_R1_event_regime_gated`：support diagnostic source，至少用于 E1-missed readout 对照。

可选但推荐包含：

1. C 中表现最好的 risk_on diagnostic arms。
2. R-core 去除同日重复后的 deterministic de-overlap baseline。
3. E1 + R6 add-on baseline。
4. E1 + R-core post-filter add-on baseline。

### 7.2 Supervised candidate rows

训练候选行必须来自 event-level source，而不是只来自 captured target episode：

1. 必须保留 non-target events。
2. 必须保留 failed events。
3. 必须保留 bridge-negative events。
4. 不得只训练 target episode window 内事件。
5. 不得用 `target_episode_id` 是否存在作为训练特征。

Canonical event key 必须至少包含：

```text
source_id
canonical_event_id
instrument
event_t0_date
event_t0_pos
trade_open_date
trade_open_pos
replay_anchor_date
replay_anchor_pos
event_regime_bucket
event_split
```

如果同一个 `canonical_event_id` 通过多个 source_id 出现，必须保留 source membership 多值，并输出 overlap audit；不得静默去重成一个不带 source identity 的事件。

### 7.3 Label join contract

`candidate_family_event_labels.parquet` 中 `event_id` 不是全局唯一键；同一 `event_id`
可能同时存在 `all_new_candidate_union` 与 `selected_candidate_union` 等 `label_scope`。
E 必须使用显式 label scope join，不得只按 `event_id` 裸连。

08 label join 规则：

1. 对 `candidate_family_canonical_events.csv.gz` 重建出的 R-series canonical source pool，默认使用：

```text
join_key = event_id + label_scope
required_label_scope = all_new_candidate_union
```

2. 对明确属于 selected candidate union 的 source pool，使用：

```text
join_key = event_id + label_scope
required_label_scope = selected_candidate_union
```

3. 对 raw event instance source，使用：

```text
join_key = event_id + label_scope
required_label_scope = event_instance
```

4. 对 D membership rows，若已携带 `failure_10_label`、`failure_10_complete`、`event_false_repair_20d_label`、`event_false_repair_20d_complete`，这些字段可作为 post-replay retention / oracle gap audit 的 label source，但 supervised full-universe training sample 仍必须与 event-level label source reconciliation。
5. D membership rows 若缺少 `label_scope`，E 必须按 source pool 明确派生 `membership_label_scope`：

```text
canonical R-series source pool -> all_new_candidate_union
selected candidate union source pool -> selected_candidate_union
raw event instance source pool -> event_instance
```

6. 对 D membership 与 event-level label source 中共同存在的 rows，必须按
   `event_id + membership_label_scope` 对账以下字段：

```text
failure_10_label
failure_10_complete
event_false_repair_20d_label
event_false_repair_20d_complete
```

7. 任一 supervised source pool 出现 label mismatch，必须 fail closed，并在
   `risk_on_cost_rejector_label_source_audit.csv` 中记录 mismatch count 与 sample rows。
   若 R6 或 R-core 出现 mismatch，停止并输出：

```text
risk_on_cost_rejector_label_reconciliation_blocked
```

8. `canonical_event_id` 只能用于 source membership / replay membership 对齐；不得在缺少 label_scope 约束时替代 label join key。
9. 任一 source pool 在 label-scope 过滤后出现 duplicate join rows，必须停止并输出：

```text
risk_on_cost_rejector_label_join_blocked
```

10. 任一 supervised source pool 的 cost-label coverage 低于 95%，该 source pool 的 supervised arms 必须 fail closed；如果 R6 与 R-core 都低于 95%，final decision 必须是：

```text
risk_on_cost_rejector_label_horizon_blocked
```

11. `risk_on_cost_rejector_label_source_audit.csv` 必须报告 `source_pool`、`label_scope`、`event_n`、`label_joined_n`、`duplicate_join_n`、`missing_label_n`、`cost_label_complete_n`、`cost_label_complete_rate`、`membership_label_reconciled_n`、`membership_label_mismatch_n` 与 fail-closed reason。

## 8. Label Contract

### 8.1 Primary cost labels

必须构造以下 supervised labels：

```text
fast_fail_bad_10d = failure_10_label == 1
false_repair_bad_20d = event_false_repair_20d_label == 1
cost_bad_10_20 = fast_fail_bad_10d OR false_repair_bad_20d
cost_clean_10_20 = horizon_complete AND NOT cost_bad_10_20
```

其中：

```text
horizon_complete = failure_10_complete == true AND event_false_repair_20d_complete == true
```

`horizon_complete` 必须继承 A / D 对 execution 与 label horizon completeness 的定义，不得另起口径。

不完整 label 的处理规则：

1. `horizon_complete = false` 的事件必须标记为 `cost_label_status = incomplete_or_censored`。
2. `cost_label_status = incomplete_or_censored` 的事件不得进入 supervised fit、threshold optimization、AUC / PR-AUC、top-decile lift 或 cost-rate before/after 分母。
3. 不完整 label 不得被当作 `cost_clean_10_20`。
4. 不完整 label 事件必须保留在 source coverage、density 和 selected/rejected event audit 中。
5. 如果任一 split / source_pool 的 `cost_label_complete_rate < 95%`，该 cell 必须标记 `label_horizon_low_coverage`；该 cell 不得支持 final candidate。

### 8.2 Label 使用边界

`failure_10_label`、`event_false_repair_20d_label`、`event_big_winner_120d_label` 是未来结果字段：

1. 可以作为 supervised label。
2. 可以作为 train-only threshold frontier 的目标或约束。
3. 可以作为 OOS readout。
4. 不得作为 t0 feature。
5. 不得用于生成新事件。

`target_episode_id`、`episode_low_date`、`episode_high_date`、`first_50pct_touch_date`、`captured_target_episode_id_first`、post-replay membership flag 是 episode/membership 字段：

1. 可以用于 train-only retention frontier 约束。
2. 可以用于 validation / robustness readout。
3. 不得作为 event feature。
4. 不得用于筛选训练样本，除非该筛选仅用于单独标记的 diagnostic table。

### 8.3 Secondary labels

`event_big_winner_120d_label` 只能作为后段 readout，不是 E 的 primary training target。

E 不得因为 120d winner precision 改善而忽略 10d fast-fail / 20d false-repair 恶化。

## 9. Feature Contract

### 9.1 允许的 feature families

允许使用 t0 或 t0 前可见字段，包括但不限于：

1. R-series 原始 score / rank / threshold distance。
2. family id、mechanism cluster、source scope membership。
3. same-day cross-family overlap count。
4. same-instrument trailing 10d / 20d event count。
5. prior adjacent event gap。
6. board bucket、style proxy、market regime、market trend / drawdown t0 values。
7. t0 前收益、波动率、成交额、换手、相对强弱、价格位置。
8. E2 / E3 / E6 同日 tags，前提是这些 tags 在 t0 可见。
9. calendar features，如 month / quarter / trading-day index，前提是不编码未来 split。

### 9.2 Daily panel as-of join contract

`cross_section_feature_panel.parquet` 是日频 `(instrument, date)` 面板，不是事件级表。
它不提供 `canonical_event_id`、`event_t0_pos`、`replay_anchor_pos`、`event_split` 或
post-replay membership key。E 必须显式执行 as-of join：

```text
feature_join_key = instrument
feature_as_of_date = max(panel.date where panel.instrument = event.instrument and panel.date <= event.event_t0_date)
feature_join_policy = latest_same_or_prior_event_t0_date
```

As-of join 规则：

1. `feature_as_of_date` 必须小于等于 `event_t0_date`。
2. 默认禁止使用 `trade_open_date`、`replay_anchor_date` 或任何 episode-side date 作为 feature panel join date。
3. 如果某个 feature 必须使用 event source 自带的 t0 字段而非 daily panel，必须在 `risk_on_cost_rejector_feature_contract.csv` 中标记 `source_kind = event_envelope`。
4. 每个 joined feature row 必须保留 `feature_as_of_date`、`feature_lag_days`、`feature_join_policy` 与 `feature_source_hash`。
5. 任一 joined row 出现 `feature_as_of_date > event_t0_date`，必须停止并输出：

```text
risk_on_cost_rejector_leakage_blocked
```

6. 若某 instrument/event 找不到 `date <= event_t0_date` 的 feature row，该事件的 daily-panel feature status 为 `asof_feature_missing`；不得向未来补齐。
7. As-of join 参数、panel hash、join code hash 与 missing policy 必须写入 manifest。

### 9.3 禁止 feature

以下字段或其派生字段不得作为 feature：

```text
failure_10_label
event_false_repair_20d_label
event_big_winner_120d_label
forward_20_return
forward_60_return
mfe_120d
mae_120d
target_episode_id
captured_target_episode_id_first
episode_low_date
episode_high_date
first_50pct_touch_date
first_100pct_touch_date
post_replay_captured_flag
bridge_positive_label
e1_missed_episode_flag
window_start_pos
window_end_pos
any field created after replay by looking inside the target episode window
```

若 feature table 中存在禁止字段，必须：

1. 在 `risk_on_cost_rejector_feature_contract.csv` 中标记 `feature_allowed = false`。
2. 从训练矩阵中剔除。
3. 在 leakage audit 中报告。

若禁止字段进入模型训练矩阵，停止并输出：

```text
risk_on_cost_rejector_leakage_blocked
```

### 9.4 Feature source audit

必须输出每个 feature 的：

1. `feature_name`
2. `source_artifact`
3. `source_hash`
4. `as_of_policy`
5. `source_kind`
6. `feature_join_key`
7. `feature_as_of_date_policy`
8. `max_feature_as_of_date_minus_event_t0_date`
9. `uses_future_information`
10. `allowed_as_t0_feature`
11. `missing_rate_train`
12. `missing_rate_validation`
13. `missing_rate_robustness`
14. `blocked_reason`

训练矩阵中任一 feature 在 train 或 robustness 的 missing rate > 20%，必须：

1. 被剔除，或
2. 进入明确的 missing bucket，并在报告中说明。

不得对 validation / robustness 单独学习 imputation 参数。

## 10. Model / Rejector Requirements

### 10.1 必跑 arms

E 至少需要运行以下 arms：

1. `keep_all_r6`: 不过滤 R6，作为 compact recall source baseline。
2. `keep_all_r_core`: 不过滤 R-core，作为 wide recall source baseline。
3. `oracle_non_fast_fail`: D audit-only oracle，不可作为 deployable candidate。
4. `oracle_non_false_repair`: D audit-only oracle，不可作为 deployable candidate。
5. `oracle_non_fast_fail_and_non_false_repair`: D audit-only oracle，不可作为 deployable candidate。
6. `supervised_fast_fail_rejector`: 训练 `fast_fail_bad_10d`。
7. `supervised_false_repair_rejector`: 训练 `false_repair_bad_20d`。
8. `supervised_joint_cost_rejector`: 训练 `cost_bad_10_20`。

如果 feature source 不足，supervised arms 必须 fail closed，但 deterministic baseline 与 oracle gap audit 仍应输出。

### 10.2 模型约束

至少需要一个可解释 baseline model：

1. logistic regression / regularized linear model，或
2. monotonic scorecard / calibrated rule list。

可选非线性模型：

1. gradient boosting / random forest / calibrated tree ensemble。

任何非线性模型都必须输出 feature importance / permutation audit，并与可解释 baseline 对比。若非线性模型 OOS 好但可解释 baseline 反转，final decision 最高只能是 `diagnostic_only_or_no_candidate`，除非报告解释并通过 robustness leakage audit。

### 10.3 Fit discipline

训练流程：

1. 只在 train split fit model。
2. 只在 train split 做 feature selection。
3. 只在 train split 选择 threshold / quota / family budget。
4. validation 只读 diagnostic。
5. robustness 只读 support / block。
6. 同一 instrument 的相邻事件必须做 purge 或 group-aware validation audit，避免同一短周期重复事件同时影响 fit 与 readout。

若实现使用 cross-validation，只能在 train 内部做 purged / grouped CV。不得把 validation 或 robustness 放入 CV。

### 10.4 Threshold frontier

每个 supervised arm 必须输出 train-frozen threshold frontier，至少包含：

1. `threshold_id`
2. `model_id`
3. `source_pool`
4. `threshold_value`
5. `train_reject_rate`
6. `train_fast_fail_rate_before`
7. `train_fast_fail_rate_after`
8. `train_false_repair_rate_before`
9. `train_false_repair_rate_after`
10. `train_cost_bad_rate_before`
11. `train_cost_bad_rate_after`
12. `train_any_recall_retention`
13. `train_bridge_recall_retention`
14. `train_e1_missed_capture_retention`
15. `density_readout_status`
16. `candidate_tier`

Threshold 选择可以使用 train 的 post-replay retention 约束，但必须在报告中标注：

```text
threshold_selected_with_train_replay_retention_constraint
```

这不是 t0 feature，但它使 E 仍然是 research candidate，不是 live trading rule。

每个 candidate tier 必须最多发布一个 selected `(model_id, threshold_id)`。所有 final gate
指标，包括 cost reduction、fast-fail / false-repair rate、any recall retention、
E1-missed capture retention、density 与 concentration，必须全部读自同一个 selected
`(model_id, threshold_id)`。不得从 threshold frontier 中分别挑选 cost 最优点与 recall
最优点来拼接 final decision。

## 11. Evaluation Metrics

### 11.1 Event-level separability

必须按 model / source_pool / split 报告：

1. sample count。
2. label prevalence。
3. ROC-AUC。
4. PR-AUC。
5. top-decile lift。
6. bottom-decile cost_bad rate。
7. calibration / Brier score。
8. score monotonicity by decile。
9. feature missing coverage。

若任一 OOS split 的 AUC < 0.50 或 top-decile lift 反转，相关 arm 不能支持 final candidate。

### 11.2 Cost readout

必须按 source_pool / threshold / split / episode_regime_bucket 报告：

1. selected event count。
2. rejected event count。
3. reject rate。
4. `fast_fail_bad_10d` count / rate before and after。
5. `false_repair_bad_20d` count / rate before and after。
6. `cost_bad_10_20` count / rate before and after。
7. horizon-complete event rate。
8. cost reduction absolute pp。
9. cost reduction relative percent。

Cost before / after 分母必须固定：

```text
before_cost_rate = raw source pool in the same source_pool / split / regime cell,
                   restricted to horizon_complete events
after_cost_rate = selected events from the same source_pool / split / regime cell
                  under the same selected model_id / threshold_id,
                  restricted to horizon_complete events
cost_reduction_relative = (before_cost_rate - after_cost_rate) / before_cost_rate
```

`horizon_complete = false` 的事件不得进入 before 或 after cost-rate 分母。所有 readout
必须同时报告 `before_horizon_complete_event_n` 与 `after_horizon_complete_event_n`，
防止分母漂移制造虚假 cost reduction。

### 11.3 Post-filter replay retention

必须使用 D membership source 对 post-filter event set 重放，按 train / validation / robustness 报告：

1. any recall before / after。
2. bridge recall before / after。
3. E1-missed capture before / after。
4. E1-missed capture retention。
5. incremental capture over E1。
6. post-filter selected event count。
7. filtered event count。
8. replay source status。

Headline readout 只看：

```text
episode_regime_bucket = risk_on
window = low_to_first_50pct
replay_policy_id = post_replay_executable_horizon_complete
```

`low_to_high` 可以作为 diagnostic，不得替代 headline。

### 11.4 Density readout

必须引用 A 的 `density_fast_fail_caliber_contract.md`，不得重定义 density。

Research-entry / feature-source 使用的数值上限必须在 E 的 config 中预声明，并在
`risk_on_cost_rejector_density_readout.csv` 中记录。A contract 只提供计算口径；
如果 E config 没有声明 density / concentration 上限，research-entry gate 不得通过，
最高只能进入 feature-source 或 diagnostic-only。

至少输出：

1. formal full-denominator event-day density。
2. rolling 10d executable event-day density。
3. rolling 20d executable event-day density。
4. per-instrument rolling duplicate rate。
5. adjacent event gap p10 / median / p90。
6. p95 density。
7. family concentration。
8. board concentration。

Episode-window density 只能作为 diagnostic alert，不得作为 admission hard fail 的唯一依据。

## 12. Decision Gates

### 12.1 Research entry-admission candidate gate

只有同时满足以下条件，才能输出：

```text
risk_on_cost_rejector_research_entry_candidate_supported
```

若任一上游 source-caveated，则必须输出：

```text
risk_on_cost_rejector_research_entry_candidate_source_caveated_supported
```

硬门槛：

1. input / binding / leakage audit 全部 pass。
2. supervised feature source 完整，train 与 robustness feature coverage >= 95%。
3. event-level OOS separability 不反转：robustness ROC-AUC >= 0.55 且 PR-AUC 高于 prevalence。
4. 后续所有 gate 指标必须来自同一个 selected `(model_id, threshold_id)`。
5. train 与 robustness 的 `cost_bad_10_20` rate 均较 raw source 下降 >= 15% relative；before / after 必须使用第 11.2 节的同一 horizon-complete 分母口径。
6. train 与 robustness 的 `fast_fail_bad_10d` rate 均不高于 raw source。
7. train 与 robustness 的 `false_repair_bad_20d` rate 均不高于 raw source。
8. train any recall retention >= 90%，robustness any recall retention >= 80%。
9. train E1-missed capture retention >= 85%，robustness E1-missed capture retention >= 75%。
10. robustness post-filter incremental capture over E1 仍为正，且
    `robustness_post_filter_e1_missed_captured_episode_n >= 60`。这里的 n 是被 post-filter
    selected events 实际捕获的 E1-missed episode 数，不是 E1-missed denominator。
11. density gate pass：formal event-day density、rolling 10d density、p95 density 均按 A contract 口径计算，且不超过 E config 中预声明的 research-entry 上限。
12. family concentration 与 board concentration 不超过 E config 中预声明的上限。
13. validation 不得触发任何阈值微调；validation risk_on 必须打印真实 denominator n、cost-label complete n、selected event n 与 post-filter E1-missed captured episode n，并只作为 diagnostic。

Research entry-admission 支持只表示该 source 有资格进入下一阶段 primary-model / meta-label
研究，不表示可部署 direct-entry union，也不表示交易策略上线。

### 12.2 Meta-label / rejector feature-source gate

如果 research-entry gate 未通过，但满足以下条件，可以输出：

```text
risk_on_cost_rejector_feature_source_supported
```

若任一上游 source-caveated，则必须输出：

```text
risk_on_cost_rejector_feature_source_caveated_supported
```

门槛：

1. input / binding / leakage audit 全部 pass。
2. supervised model 在 train 与 robustness 上没有 separability 反转。
3. robustness ROC-AUC >= 0.52 或 top-decile cost_bad lift 明显为正。
4. train 或 robustness 至少一个 OOS readout 的 `cost_bad_10_20` rate 较 raw source 下降 >= 10% relative，另一个 split 不得恶化；所有 readout 必须来自同一个 selected `(model_id, threshold_id)`，且 before / after 使用第 11.2 节的同一 horizon-complete 分母口径。
5. robustness any recall retention >= 70%。
6. robustness E1-missed capture retention >= 60%。
7. robustness post-filter incremental capture over E1 仍为正。
8. density / concentration 即使未达 research-entry，也必须可审计且未比 raw source 明显恶化。
9. 报告必须明确：该结果只能进入下一阶段 meta-label / rejector feature source，不得作为 direct entry union。

### 12.3 Diagnostic-only / no-candidate

以下任一情况，final decision 必须是：

```text
risk_on_cost_rejector_diagnostic_only_or_no_candidate
```

1. cost separability 在 robustness 反转。
2. cost rate 改善来自大量牺牲 E1-missed capture。
3. fast-fail 降低但 false-repair 明显恶化，或反之。
4. 只在 train 有改善，validation / robustness 无法支持。
5. post-filter recall 低于 E1 baseline 或 incremental capture over E1 不再为正。
6. density / concentration 无法审计。
7. 结果只依赖 oracle future label filter。

Diagnostic-only 仍是有效结果，必须输出模型分数、失败分布、threshold frontier、rejected-event audit 和下一步建议。

### 12.4 Blocked states

可返回的 blocked decisions：

```text
risk_on_cost_rejector_input_blocked
risk_on_cost_rejector_d_source_blocked
risk_on_cost_rejector_e1_baseline_blocked
risk_on_cost_rejector_scope_reconstruction_blocked
risk_on_cost_rejector_scope_binding_drift_blocked
risk_on_cost_rejector_feature_source_blocked
risk_on_cost_rejector_binding_drift_blocked
risk_on_cost_rejector_label_join_blocked
risk_on_cost_rejector_label_reconciliation_blocked
risk_on_cost_rejector_leakage_blocked
risk_on_cost_rejector_label_horizon_blocked
risk_on_cost_rejector_sample_power_blocked
```

Blocked report 必须说明：

1. blocked artifact。
2. missing / stale field。
3. expected value。
4. observed value。
5. whether deterministic diagnostics were still produced。

## 13. Required Outputs

### 13.1 Manifest

```text
outputs/manifests/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_manifest.json
```

Manifest 至少包含：

1. `experiment_id`
2. `run_id`
3. `created_at`
4. `decision`
5. `blocked_reasons`
6. upstream decisions and hashes。
7. D membership hash。
8. feature source hash。
9. label source hash。
10. runner code hash。
11. requirement hash。
12. output paths。
13. output hashes。
14. output row counts。
15. `entry_support_allowed`
16. `source_caveated`
17. selected `model_id`
18. selected `threshold_id`
19. selected threshold source pool and candidate tier。
20. feature as-of join policy, parameters, source panel hash, join code hash, and missing policy。
21. regime column role mapping hash。
22. label join policy and membership-label reconciliation status。
23. scope reconstruction source-row-count bindings and accepted published-reference differences。

### 13.2 Reports

```text
outputs/publishable/reports/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_report.md
outputs/publishable/reports/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_contract.md
```

报告必须用中文写，至少包含：

1. A-D 结论承接。
2. 为什么 E 不继续做 entry-ranker / compression。
3. input / source caveat。
4. feature leakage audit 摘要。
5. model / threshold 选择逻辑。
6. OOS separability。
7. cost reduction vs retention tradeoff。
8. density / concentration readout。
9. final decision 与不可声称内容。
10. 若 negative result，必须解释失败来自 separability、成本、retention、density 还是 source。

### 13.3 Publishable tables

必须输出：

```text
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_input_audit.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_binding_audit.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_scope_reconstruction_audit.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_split_alignment_audit.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_feature_contract.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_label_source_audit.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_training_sample_summary.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_model_registry.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_oos_separability.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_threshold_frontier.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_cost_readout.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_post_filter_retention_by_split.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_e1_missed_retention.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_density_readout.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_oracle_gap_audit.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_leakage_audit.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_decision_tiers.csv
```

可选但推荐输出：

```text
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_event_scores.csv.gz
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_selected_events.csv.gz
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_rejected_events.csv.gz
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_top_failure_examples.csv
```

若 event score 文件过大，应压缩为 `.csv.gz` 或放入 local raw，并在 manifest 中记录；不得把超大未压缩 artifact 强行发布。

## 14. Reproducibility / Safety

Experiment E 不得覆盖：

1. A outputs。
2. B outputs。
3. C outputs。
4. D outputs。
5. 08 main run outputs。
6. 07 baseline outputs。

所有 E 输出必须写入：

```text
outputs/publishable/tables/risk_on_post_filter_cost_rejector/
outputs/publishable/reports/risk_on_post_filter_cost_rejector/
outputs/manifests/risk_on_post_filter_cost_rejector/
outputs/local_cache/risk_on_post_filter_cost_rejector/
```

实现必须支持 repeated run：

1. 同一输入 hash 与 config 下输出稳定。
2. manifest 记录 runner code hash。
3. report hash 写入 manifest。
4. publishable table hash 写入 manifest。
5. source-caveat 传递到 final decision。

## 15. Expected Interpretation

E 的成功标准不是“120d winner precision 最高”，而是：

```text
在 risk_on 中，post-filter R-series source 能以可审计的方式降低 10d fast-fail /
20d false-repair 成本，同时保留足够 E1-missed capture，使其有资格进入下一阶段
primary model / meta-label 设计。
```

如果 E 失败，合理结论包括：

1. risk_on 的成本标签在 t0 不可分。
2. R-series 的 E1-missed capture 与 fast-fail / false-repair 高度绑定，过滤成本会同步杀掉 recall。
3. 需要新的 risk_on event family，而不是 R-series rejector。
4. 需要更细的 risk_on sub-regime 或 board/style 分桶。

这些都是有效 negative result，但必须由 E 的 replay retention、cost readout、OOS separability 和 leakage audit 支撑。
