# 需求：Experiment H - Risk-on Cost Rejector Research-Entry Hardening

## 1. 背景

Experiment E 已经证明 risk_on post-filter cost rejector 有真实 OOS 信号，但还没有通过
research-entry admission。

E 的已知结果：

1. selected source / model / threshold：
   - source pool：`08_R_core_event_regime_gated`
   - model：`supervised_joint_cost_rejector`
   - target：`cost_bad_10_20`
   - model type：`logistic_regression_balanced_l2`
   - selected threshold：`supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_080`
2. OOS separability 没有反转：
   - ROC-AUC train / validation / robustness = `0.692 / 0.682 / 0.686`
   - robustness PR-AUC = `0.524`，高于 prevalence `0.322`
   - robustness top-decile lift = `2.021`
3. selected `keep_080` 的 research-entry 差距：
   - train cost reduction = `14.17%`，低于 `15%`，差 `0.83pp`
   - robustness cost reduction = `20.48%`，已通过
   - train any recall retention = `90.05%`，刚过 `90%`
   - robustness any recall retention = `86.55%`
   - robustness E1-missed retention = `84.52%`，captured n = `71`
4. `keep_075` 的 tradeoff：
   - train / robustness cost reduction = `16.85% / 23.10%`
   - train any recall retention = `88.69%`，低于 `90%`
5. 两个 admission contract 缺口：
   - `momentum_percentile_20d_lag20` train coverage = `93.30%`，低于逐字段 `95%` coverage gate
   - density / concentration 可审计，但 E config 没有预声明 research-entry 上限，触发 `density_gate_not_configured`

因此 H 不是重新寻找新 family，也不是 transition extension。H 的任务是把 E 的原
risk_on scope 做成 research-entry 可判定的 hardening replay：

```text
固定 E 的 risk_on post-filter cost rejector 主线，
修复 feature coverage 与 density config 契约，
用预声明 selected-threshold 规则重新评估 keep_080 / keep_075 附近边界，
判断它是否能进入 research-entry candidate。
```

## 2. Primary Question

Experiment H 必须回答：

```text
After fixing feature coverage and predeclaring density / concentration caps,
can the E risk_on cost rejector pass research-entry admission under one
preselected model-threshold rule without frontier cherry-picking?
```

中文等价问题：

```text
在不扩大 E 原 scope、不引入 transition-only readout、不使用未来信息的前提下，
能否通过一次预声明的 hardening run，让 risk_on cost rejector 同时满足
成本下降、召回保留、E1-missed capture、density / concentration 与 feature coverage 门槛？
```

## 3. 范围

H 只覆盖：

1. `risk_on` target regime。
2. E 的 R-core / R6 post-replay risk_on source pool；primary candidate 固定为 E selected 的
   `08_R_core_event_regime_gated + supervised_joint_cost_rejector`。
3. E 的 feature coverage hardening。
4. E 的 density / concentration gate 预声明。
5. `keep_080` / `keep_075` 附近的预声明 threshold replay。
6. research-entry admission gate replay。

H 不覆盖：

1. transition sub-regime taxonomy。
2. G 的 `transition_from_risk_on` / `transition_from_risk_off` 特征接入。
3. transition-side diagnostic ablation / multi-regime rejector。
4. 新 event family 发明。
5. C 的 entry-ranker / compression grid 延伸。
6. 交易策略、组合回测、止盈止损、仓位模拟。

如果实现中出现任何 `transition_from_*`、`next_regime`、`transition_conversion` 作为训练特征、
阈值选择字段或 final gate 字段，必须停止并输出：

```text
risk_on_research_entry_hardening_transition_scope_leakage_blocked
```

## 4. Required Inputs

### 4.1 上游 manifests

必须读取：

```text
outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
outputs/manifests/regime_family_matrix/regime_family_matrix_manifest.json
outputs/manifests/risk_on_r_series_bridge_ranker/risk_on_r_series_bridge_ranker_manifest.json
outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
outputs/manifests/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_manifest.json
```

E manifest 必须满足：

| field | required value |
| --- | --- |
| `decision` | `risk_on_cost_rejector_feature_source_caveated_supported` |
| `selected_candidate_tier` | `research_entry` |
| `selected_source_pool` | `08_R_core_event_regime_gated` |
| `selected_model_id` | `supervised_joint_cost_rejector` |
| `selected_threshold_id` | `supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_080` |
| `source_caveated` | `true` |

若 E manifest 缺失、hash 不可读、上述字段与上表不一致，必须停止并输出：

```text
risk_on_research_entry_hardening_e_source_blocked
```

若后续 E rerun 已经 stronger，允许的 stronger decision 只能是：

```text
risk_on_cost_rejector_research_entry_candidate_supported
risk_on_cost_rejector_research_entry_candidate_source_caveated_supported
```

但此时仍必须记录 `e_decision_binding_status = stronger_than_required`，并对比 E selected
source/model/threshold 是否仍与 H 的 primary candidate 一致。若不一致，必须停止并输出
`risk_on_research_entry_hardening_e_source_blocked`。

若 A / B / C / D / E 任一上游带 `source_caveated`，H 可以继续，但最终 research-entry
通过态必须带 `source_caveated` 后缀，不得声称 production-ready entry gate。

### 4.2 E 产物

必须读取：

```text
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_feature_contract.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_model_registry.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_oos_separability.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_threshold_frontier.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_cost_readout.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_post_filter_retention_by_split.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_e1_missed_retention.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_density_readout.csv
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_event_scores.csv.gz
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_selected_events.csv.gz
outputs/publishable/tables/risk_on_post_filter_cost_rejector/risk_on_cost_rejector_rejected_events.csv.gz
```

E 产物必须与 E manifest 的 `output_hashes` 一致。任一 hash mismatch 必须停止：

```text
risk_on_research_entry_hardening_e_artifact_hash_blocked
```

### 4.3 D replay membership 与 label source

H 必须重新读取 D 的 materialized membership 与 event-level labels，而不是只复用 E 的汇总表：

```text
outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
outputs/local_cache/candidate_family_event_labels.parquet
outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
```

要求：

1. D leakage audit 全部 pass。
2. label join 与 E 同口径：`failure_10_label`、`event_false_repair_20d_label`。
3. 若 membership 与 event-level label source 同时携带同名 label 字段，必须按 event key 对账；
   任一 `failure_10_label` / `event_false_repair_20d_label` 不一致，必须 fail closed。
4. H 的 event universe / split / episode regime 与 E selected source 可对账。
5. horizon-complete denominator 口径必须与 E 第 11.2 节一致。

任一不满足，停止：

```text
risk_on_research_entry_hardening_replay_binding_blocked
```

### 4.4 Raw feature reconstruction inputs

因为 H 会删除低 coverage feature 后重新 fit preprocessing pipeline 与 primary model，不能只依赖
E 的 `event_scores.csv.gz`。必须读取 E 同口径 raw feature inputs：

```text
outputs/publishable/tables/candidate_family_canonical_events.csv.gz
outputs/publishable/tables/candidate_family_event_instances.csv.gz
outputs/local_cache/cross_section_feature_panel.parquet
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
```

要求：

1. `cross_section_feature_panel.parquet` 必须按 E 的 as-of join contract 使用：

```text
feature_as_of_date = max(panel.date where panel.instrument = event.instrument and panel.date <= event.event_t0_date)
```

2. 每个 joined feature row 必须保留 `feature_as_of_date`、`feature_lag_days`、
   `feature_join_policy` 与 `feature_source_hash`。
3. 任一 joined row 出现 `feature_as_of_date > event_t0_date`，必须停止：

```text
risk_on_research_entry_hardening_feature_asof_leakage_blocked
```

4. H 的 reconstructed primary source event count 必须与 E selected source 的 source-row-count
   binding 对齐；R-core 继续接受 A audit 已记录的 `47914` vs published `47929` 的 `-15` 差异，
   不得用 published reference count 硬相等阻断。
5. raw input hash、schema fingerprint、as-of join parameter hash 必须写入 manifest。

## 5. H Config Contract

必须新增独立 config 或 config section，记录为 H manifest 的 hash：

```text
experiment_id: 08_experiment_h_risk_on_cost_rejector_research_entry_hardening
target_regime: risk_on
primary_source_pool: 08_R_core_event_regime_gated
primary_model_id: supervised_joint_cost_rejector
primary_target_label: cost_bad_10_20
feature_fix_policy: drop_low_coverage_lag20
threshold_grid: [0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]
density_caps:
  formal_event_day_density_max: 7.50
  p95_density_max: 20.00
  rolling_10d_executable_event_day_density_max: 1.80
  rolling_20d_executable_event_day_density_max: 2.20
  family_concentration_max: 0.30
  board_concentration_max: 0.85
threshold_selection_policy: train_constrained_lowest_keep_fraction_then_robustness_gate_replay
validation_policy: diagnostic_only_no_threshold_tuning
```

说明：

1. 上述 density caps 是 H 的预声明上限，来源于 E 的 auditable readout 与小幅 buffer。
2. H run 开始后不得根据 H output 修改 caps。
3. 若 reviewer 想使用更严格或更宽松的 caps，必须先改需求或 config，再运行。
4. `rolling_10d_duplicate_rate`、`rolling_20d_duplicate_rate`、adjacent gap 仍必须报告，但本轮不作为 hard gate，除非 config 显式声明。

若 config 缺失任一上限，停止：

```text
risk_on_research_entry_hardening_density_config_blocked
```

Threshold id 命名必须可复现：

| keep_fraction | threshold suffix |
| ---: | --- |
| 0.85 | `keep_0850` |
| 0.825 | `keep_0825` |
| 0.80 | `keep_0800` |
| 0.775 | `keep_0775` |
| 0.75 | `keep_0750` |
| 0.725 | `keep_0725` |
| 0.70 | `keep_0700` |

E legacy threshold id `keep_080` / `keep_075` 必须在 H 的
`risk_on_hardening_feature_delta_from_e.csv` 中作为 E baseline 对照保留，但 H 新输出统一使用
四位 suffix，避免 `0.80` 与 `0.800` 命名漂移。

## 6. Feature Coverage Hardening

### 6.1 Primary policy

H 的 primary run 固定使用：

```text
feature_fix_policy = drop_low_coverage_lag20
```

具体要求：

1. 从 feature set 中移除 `momentum_percentile_20d_lag20`。
2. 重新生成 feature contract。
3. 重新计算 feature columns hash。
4. 重新 fit preprocessing pipeline。
5. 重新训练 primary model。
6. train / robustness 的每个允许 t0 feature coverage 必须 >= 95%。

如果删除该字段后仍有任何 allowed feature 在 train 或 robustness coverage < 95%，必须停止并输出：

```text
risk_on_research_entry_hardening_feature_coverage_blocked
```

### 6.2 Optional diagnostic policy

允许额外做 diagnostic：

```text
feature_fix_policy = source_repair_lag20
```

但必须满足：

1. 修复源必须证明 `as_of_date <= event_t0_date`。
2. 不得用未来填充。
3. 不得用 validation / robustness 的缺失模式决定填充规则。
4. 该 diagnostic 不能替代 primary run，除非需求被明确修改。

## 7. Model Contract

### 7.1 Primary model

H primary model 固定为：

```text
source_pool = 08_R_core_event_regime_gated
model_id = supervised_joint_cost_rejector
target_label = cost_bad_10_20
model_type = logistic_regression_balanced_l2
```

参数沿用 E：

```text
LogisticRegression(max_iter=1000, class_weight="balanced", C=0.5)
```

预处理沿用 E，但必须在删除低 coverage feature 后重新 fit：

```text
train_median_impute
nonnegative_log1p_selected_numeric
train_winsorize_1_99
train_zscore
categorical_train_vocab_one_hot
```

OOS category 使用 train vocabulary，未见 category 走 all-zero policy。

### 7.2 Secondary diagnostic models

允许同时回放 E 的 R6 / fast-fail / false-repair 单目标模型，但只能作为 diagnostic。
final research-entry decision 只能基于 primary model，除非需求另行修改。

## 8. Threshold Selection Contract

H 必须使用预声明 threshold grid：

```text
keep_fraction = [0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]
```

不得临时插入新 keep fraction。不得在看到 robustness 结果后修改 grid。

### 8.1 Metric denominator contract

所有 threshold frontier、selected threshold readout 与 final gate 必须使用同一组分母契约：

1. cost reduction 的 `before` 固定为同一 `(source_pool, split, target_regime)` cell 内 raw source 的
   horizon-complete cost rate。
2. cost reduction 的 `after` 固定为同一 cell、同一 horizon-complete denominator 口径下 selected
   events 的 cost rate。
3. fast-fail rate、false-repair rate、any recall retention 与 E1-missed retention 必须使用同一
   selected `(model_id, threshold_id)`，不得按 metric 单独换 denominator。
4. `incomplete_or_censored` 事件必须在 before / after 两侧用同一规则处理；不得只从 after 移除。
5. 必须输出 denominator audit，逐 split / threshold 记录 raw denominator n、selected n、
   rejected n、horizon-complete n 与 excluded reason counts。

任一 denominator 无法复现或 before / after 不同口径，必须停止：

```text
risk_on_research_entry_hardening_denominator_binding_blocked
```

### 8.2 Train-only selection

selected threshold 必须只用 train split 选择。

train constraints：

1. train cost reduction relative >= 15%。
2. train fast-fail rate 不高于 raw source。
3. train false-repair rate 不高于 raw source。
4. train any recall retention >= 90%。
5. train E1-missed retention >= 85%。
6. train post-filter E1-missed captured n >= 60。
7. selected event count > 0。

选择规则：

```text
在满足全部 train constraints 的 threshold 中，
选择 keep_fraction 最低的 threshold；
若并列，选择 cost reduction 更高者；
若仍并列，选择 threshold_id 字典序最小者。
```

如果没有 threshold 满足 train constraints，不得进入 research-entry gate replay，final decision 输出
`risk_on_cost_rejector_diagnostic_only_or_no_candidate`，并记录 no-candidate failure reason：

```text
risk_on_research_entry_hardening_train_threshold_not_found
```

### 8.3 Robustness gate replay

robustness 只能用于 gate replay，不得用于选择 threshold。

所有 final gate 指标必须来自同一个 selected `(model_id, threshold_id)`。
禁止以下行为：

1. cost reduction 从 `keep_075` 取，recall retention 从 `keep_080` 取。
2. train 用一个 threshold，robustness 用另一个 threshold。
3. model selection 用 validation / robustness 结果。
4. density cap 根据 selected robustness result 调整。

任一发生，停止：

```text
risk_on_research_entry_hardening_threshold_cherrypick_blocked
```

必须额外输出 `risk_on_hardening_oracle_gap_audit.csv`，记录：

1. train-selected threshold。
2. robustness-best threshold under all gates（oracle diagnostic only）。
3. 若两者不同，报告不得使用 robustness-best threshold 做 final decision。
4. robustness-best 只用于解释 tradeoff，不得进入 selected threshold。

## 9. Density / Concentration Gate

H 必须重新输出 selected threshold 下的 density / concentration readout。

Hard gates：

| metric | cap |
| --- | ---: |
| `formal_event_day_density` | <= 7.50 |
| `p95_density` | <= 20.00 |
| `rolling_10d_executable_event_day_density` | <= 1.80 |
| `rolling_20d_executable_event_day_density` | <= 2.20 |
| `family_concentration` | <= 0.30 |
| `board_concentration` | <= 0.85 |

必须同时报告：

1. selected event count。
2. rejected event count。
3. rolling 10d / 20d duplicate rate。
4. adjacent gap p10 / median / p90。
5. density vs E1。
6. density contract source hash。

若任一 hard cap 不满足，research-entry 不得通过，输出 gate-failed reason：

```text
density_or_concentration_cap_failed
```

## 10. Research-Entry Gate

只有同时满足以下条件，才能输出：

```text
risk_on_cost_rejector_research_entry_candidate_supported
```

若任一上游 source-caveated，则输出：

```text
risk_on_cost_rejector_research_entry_candidate_source_caveated_supported
```

硬门槛：

1. input / binding / leakage audit 全部 pass。
2. no transition-scope leakage。
3. feature coverage gate pass：train 与 robustness 每个 allowed feature coverage >= 95%。
4. OOS separability 不反转：robustness ROC-AUC >= 0.55，PR-AUC 高于 prevalence，top-decile lift > 1。
5. selected threshold 由第 8.2 节 train-only policy 决定。
6. train 与 robustness cost reduction relative 均 >= 15%。
7. train 与 robustness fast-fail rate 均不高于 raw source。
8. train 与 robustness false-repair rate 均不高于 raw source。
9. train any recall retention >= 90%。
10. robustness any recall retention >= 80%。
11. train E1-missed retention >= 85%。
12. robustness E1-missed retention >= 75%。
13. robustness post-filter E1-missed captured n >= 60。
14. density / concentration hard caps 全部 pass。
15. validation 只作为 diagnostic，不触发任何 model / threshold / cap 修改。

Research-entry support 只表示该 source 可以进入下一阶段 primary-model / meta-label 研究。
不得解释为 direct-entry admission、production gate、交易策略或组合上线。

## 11. Non-Pass Decisions

### 11.1 Feature-source supported

如果 research-entry 未通过，但满足：

1. input / binding / leakage pass。
2. feature coverage pass 或明确只剩 non-primary diagnostic feature 失败。
3. robustness ROC-AUC >= 0.52 或 top-decile lift > 1。
4. train 或 robustness 至少一个 split cost reduction >= 10%，另一个 split 不恶化。
5. robustness any recall retention >= 70%。
6. robustness E1-missed retention >= 60%。
7. density / concentration 可审计。

则输出：

```text
risk_on_cost_rejector_feature_source_supported
```

若上游 source-caveated：

```text
risk_on_cost_rejector_feature_source_caveated_supported
```

### 11.2 Diagnostic-only

以下任一情况输出：

```text
risk_on_cost_rejector_diagnostic_only_or_no_candidate
```

1. 没有 threshold 满足 train constraints，并记录 `risk_on_research_entry_hardening_train_threshold_not_found`。
2. robustness 出现 separability 反转。
3. recall retention 大幅低于 feature-source gate。
4. density / concentration 明显恶化且不可解释。
5. label coverage / replay membership 不足以支撑 gate replay。

### 11.3 Blocked states

必须使用明确 blocked reason：

```text
risk_on_research_entry_hardening_e_source_blocked
risk_on_research_entry_hardening_e_artifact_hash_blocked
risk_on_research_entry_hardening_replay_binding_blocked
risk_on_research_entry_hardening_denominator_binding_blocked
risk_on_research_entry_hardening_density_config_blocked
risk_on_research_entry_hardening_feature_coverage_blocked
risk_on_research_entry_hardening_feature_asof_leakage_blocked
risk_on_research_entry_hardening_transition_scope_leakage_blocked
risk_on_research_entry_hardening_threshold_cherrypick_blocked
```

注意：`risk_on_research_entry_hardening_train_threshold_not_found` 是 no-candidate failure reason，
不是 input-blocked 状态。

## 12. Required Outputs

必须输出：

```text
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_input_audit.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_config_contract.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_feature_contract.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_feature_delta_from_e.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_model_registry.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_oos_separability.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_threshold_frontier.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_selected_threshold_readout.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_metric_denominator_audit.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_cost_readout.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_post_filter_retention_by_split.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_e1_missed_retention.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_density_readout.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_oracle_gap_audit.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_research_entry_gate_replay.csv
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_decision_tiers.csv
outputs/publishable/reports/risk_on_cost_rejector_research_entry_hardening/risk_on_cost_rejector_research_entry_hardening_report.md
outputs/publishable/reports/risk_on_cost_rejector_research_entry_hardening/risk_on_cost_rejector_research_entry_hardening_contract.md
outputs/manifests/risk_on_cost_rejector_research_entry_hardening/risk_on_cost_rejector_research_entry_hardening_manifest.json
```

允许输出：

```text
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_event_scores.csv.gz
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_selected_events.csv.gz
outputs/publishable/tables/risk_on_cost_rejector_research_entry_hardening/risk_on_hardening_rejected_events.csv.gz
outputs/local_cache/risk_on_cost_rejector_research_entry_hardening/
```

若 event-level 输出超过合理 Git 体积，应优先 gzip，并在 manifest 中记录 uncompressed row count、
compressed hash 与 schema fingerprint。

## 13. Manifest Requirements

manifest 必须记录：

1. experiment id。
2. created_at。
3. requirement hash。
4. H config hash。
5. all input paths / hashes。
6. all output paths / hashes。
7. feature fix policy。
8. dropped feature list。
9. feature columns hash。
10. preprocessing hash。
11. selected source pool。
12. selected model id。
13. selected threshold id。
14. selected keep fraction。
15. threshold selection policy。
16. density caps。
17. density contract source hash。
18. final decision。
19. blocked reasons 与 non-pass failure reasons。
20. source-caveated propagation status。
21. explicit statement: `transition_scope_features_used = false`。
22. E baseline threshold id and H threshold id mapping。
23. feature as-of join policy, parameters, source panel hash, and max observed feature lag.
24. metric denominator policy hash and denominator audit hash.

## 14. Report Requirements

报告必须用中文说明：

1. H 与 E 的关系：H 是 E research-entry hardening，不是新 family / transition extension。
2. E 未通过 research-entry 的三项原因与 H 的修复方式。
3. `momentum_percentile_20d_lag20` 的处理结果。
4. selected threshold 是如何按 train-only policy 选出的。
5. `keep_080` / `keep_075` / intermediate keep fractions 的 frontier。
6. cost reduction 的 before / after denominator audit。
7. selected threshold 的 train / robustness cost reduction 与 recall retention。
8. density / concentration caps 是否通过。
9. validation 的真实 n 与 diagnostic readout。
10. 如果 research-entry 未通过，必须明确差在哪个 gate，不能只写“near miss”。
11. 不得声称 direct-entry support、production support 或交易策略有效。

## 15. Explicit Non-Claims

无论 H 结果如何，报告不得声称：

1. 该 rejector 是 production-ready entry gate。
2. 该 rejector 可直接用于交易。
3. transition previous-regime context 已成为 E 的正式特征。
4. conversion 是 PIT 可预测标签。
5. density cap 是从 H output 事后调出来的。
6. research-entry support 等价于 winner precision support。

## 16. Success Criteria

理想成功状态：

```text
risk_on_cost_rejector_research_entry_candidate_source_caveated_supported
```

这表示：

1. E 的 risk_on cost rejector 原 scope 已补齐 admission contract。
2. feature coverage 不再阻断。
3. density / concentration 有预声明 gate 并通过。
4. selected threshold 在同一 `(model_id, threshold_id)` 下同时满足 train / robustness cost 与 recall gate。
5. 结果仍继承上游 source-caveated，不是 production-ready。

如果只能输出 feature-source supported，报告必须明确下一步剩余 blocker，不得继续扩大
entry-ranker / compression 或 transition rediscovery。
