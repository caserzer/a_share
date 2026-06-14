# 需求：09C Risk-on Cost Rejector Uplift

## 1. 目标

09C 用 09A selected label 与 09B selected feature foundation 训练 risk_on cost rejector，目标是把 H 中 `keep_0775` / `keep_0800` 附近的局部 frontier 推过 research-entry。

09C 必须以新 target 重新建立 baseline，不得直接拿 H 旧 target frontier 当比较对象。

## 2. 硬依赖

09C 必须读取 09A 输出：

```text
outputs/manifests/09A_fast_fail_label_frontier_manifest.json
outputs/publishable/reports/09A_fast_fail_label_frontier/fast_fail_label_contract.md
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_contract.csv
outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_event_binding_summary.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/cost_target_bridge.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/label_mechanism_contract.csv
```

09A 必须是：

```text
decision in {
    09A_label_frontier_candidate_selected,
    09A_label_frontier_candidate_source_caveated_selected
}
```

否则 09C 只能输出：

```text
decision = 09C_riskon_cost_rejector_diagnostic_only_or_no_candidate
```

09C 必须从 `selected_label_event_bindings.parquet` 读取 supervised target、`label_t1_date`、denominator view 与 censoring status。禁止从 aggregate label frontier 表或 selected label contract 反推事件级 target。

09C 必须读取 09B 输出：

```text
outputs/manifests/09B_feature_foundation_ablation_manifest.json
outputs/publishable/tables/09B_feature_foundation/feature_contract.csv
outputs/publishable/tables/09B_feature_foundation/feature_stationarity_audit.csv
outputs/publishable/tables/09B_feature_foundation/sample_uniqueness_audit.csv
outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
outputs/publishable/tables/09B_feature_foundation/label_mechanism_overlap_audit.csv
```

09B 必须是：

```text
decision = 09B_feature_foundation_complete
```

否则 09C 只能 diagnostic，不得输出 research-entry supported。

## 3. 上游输入

必须读取并记录 hash：

```text
topics/02_AFML_BIG_WINNER/README.md
topics/02_AFML_BIG_WINNER/research_direction_discussion_20260614.md
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/08_all_experiments_final_report.md
```

必须读取核心 08 manifest：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/risk_on_cost_rejector_research_entry_hardening/risk_on_cost_rejector_research_entry_hardening_manifest.json
```

必须读取核心事件、feature 与 membership 源：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_event_instances.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_capture.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/cross_section_feature_panel.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
```

必须读取 07 E1 baseline：

```text
../07_topn_multichannel_repair_candidate_generator_v0/outputs/manifests/run_manifest.json
../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv
../07_topn_multichannel_repair_candidate_generator_v0/outputs/local_cache/topn_canonical_event_labels.parquet
```

如果 E1 baseline 无法重建，09C 必须停止：

```text
decision = 09C_riskon_cost_rejector_input_blocked
```

## 4. 非目标

09C 明确不做：

1. 不重新定义 label。
2. 不重算 sample weights。
3. 不做 transition model、transition cost rejector 或 transition feature uplift。
4. 不发明新 event family 或新 source。
5. 不训练 risk_off 模型。
6. 不做 full entry backtest、组合收益曲线、仓位模拟或交易执行策略。
7. 不在 validation / robustness 上选择 threshold。

## 5. Source Pool 与 Caveat

09C 主训练 scope：

```text
event_regime_bucket = risk_on
source_pool in {08_R_core_event_regime_gated, 08_R6_event_regime_gated}
```

必须复用 09A / 09B 的 source pool reconstruction audit：

```text
outputs/publishable/tables/input_audit/source_pool_reconstruction_audit.csv
```

重建要求：

1. `scope_status` 必须是 `reconstructable_event_membership` 或等价可审计状态。
2. `hard_gate_eligible_flag` 必须为 true，才可进入 supervised training 或 research-entry gate。
3. aggregate-only R compression arms 不得作为训练样本、threshold frontier、density gate 或 replay retention source。
4. R-core 继续接受 08 A / H 已审计的 `47914` vs published `47929` 的 `-15` 差异；但必须在 audit 中记录 accepted difference reason。
5. 如果 reconstructed event count 与 `source_row_count` 不一致，且该差异未被上游 audit 接受，必须停止。

如果 D / E / H 任一上游为 source-caveated，09C 的 supported 决策必须使用 `source_caveated` variant。

## 6. Baseline Replay

09C 必须先输出：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/09C_h_style_baseline_replay_on_selected_target.csv
```

该 baseline 使用：

1. H primary source：`08_R_core_event_regime_gated`。
2. H baseline allowed features 或 H feature set after lag20 drop。
3. H-style model：balanced L2 logistic regression。
4. 09A selected target。
5. 09B sample weights。

这个 baseline 是 09C uplift 的真正对照。H 旧 target frontier 只作为历史背景。

## 7. 模型候选

模型数量必须控制：

```text
logistic / elastic net
random forest or bagging shallow trees
shallow LightGBM
```

必须显式测试 train-fold calibration：

```text
Platt / logistic calibration
isotonic calibration
calibration fit inside train fold only
calibration before/after frontier readout around keep_0800
```

对于有明确经济方向的 feature，例如 drawdown、stop-distance、ATR-normalized distance、volatility shock，允许 monotonic constraint 或 monotonic sanity check。单调约束的目标是提升局部排序稳定性，不是追求最高 AUC。

## 8. Feature Use 与 Leakage Block

09C 只能使用 09B `feature_contract.csv` 中 `allowed_for_09C_flag = true` 的 t0 feature。

必须禁止：

1. `failure_10_label`
2. `event_false_repair_20d_label`
3. `winner_120`
4. post-replay membership flag
5. future MFE / MAE
6. future high / low
7. transition outcome / conversion label
8. `next_regime`
9. any post-event volume or return
10. any label-derived variable

若任何 forbidden field 进入 model matrix，停止：

```text
decision = 09C_riskon_cost_rejector_feature_leakage_blocked
```

## 9. Threshold / Gate

09C 必须在 config 中冻结：

```text
selected_target_label
cost_reduction_min_train
any_recall_retention_min_train
e1_missed_retention_min_train
bridge_retention_min_train
robustness_no_reversal_rule
density_caps
family_concentration_cap
board_concentration_cap
threshold_grid
threshold_selection_policy
```

默认 threshold grid：

```text
[0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]
```

默认 research-entry gate，除非 config 更严格：

| gate | default |
| --- | ---: |
| train relative cost reduction | >= 15% |
| train any recall retention | >= 90% |
| train E1-missed retention | >= 85% |
| train bridge retention | report and non-collapse |
| robustness cost reduction | > 0 and no severe reversal |
| robustness any recall retention | >= 80% |
| robustness E1-missed retention | >= 70% |

如果 09A selected target 与旧 target 差异极大，默认 gate 可以在 config 中重新冻结，但必须在 report 中解释重声明原因，并禁止与 H 旧 frontier 逐点比较。

## 10. Density / Concentration Caps

默认沿用 H caps，除非 config 更严格：

| metric | cap |
| --- | ---: |
| formal_event_day_density | 7.50 |
| p95_density | 20.00 |
| rolling_10d_executable_event_day_density | 1.80 |
| rolling_20d_executable_event_day_density | 2.20 |
| family_concentration | 0.30 |
| board_concentration | 0.85 |

Density / concentration 必须对 selected threshold 的 selected events 计算，不能只对 raw source pool 计算。

## 11. Risk-off Read-only 对照

09C 必须输出：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/riskoff_readonly_control.csv
```

规则：

1. 默认使用 09C 在 risk_on train 上 fit 完成的 selected preprocessing、model、calibration 和 threshold，直接 score risk_off sample。
2. 不允许为了 risk_off 对照重新训练模型、重新 fit calibration、重新选择 threshold 或重新选择 feature。
3. 在 risk_off E1 或可审计 risk_off sample 上只输出 readout。
4. 不调参。
5. 不进入 09C gate。
6. 只用于判断 uplift 是否 risk_on 特异。

如果 risk_off input 不足，可输出：

```text
riskoff_readonly_control_input_insufficient
```

但必须说明原因。

## 12. Overlap Ablation

若 09B 标记 feature-label mechanism overlap，09C 必须输出：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/label_mechanism_overlap_ablation.csv
```

至少比较：

1. full selected feature set。
2. drop direct-overlap features。
3. drop direct + related overlap features。

如果去掉 overlap features 后模型完全坍塌，09C 可以仍输出 diagnostic，但不得把 full model 的可分性解释为稳定泛化 alpha。

## 13. 输出

09C 必须输出：

```text
outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
outputs/publishable/reports/09C_riskon_cost_rejector_uplift_report.md
outputs/publishable/tables/09C_riskon_cost_rejector/09C_h_style_baseline_replay_on_selected_target.csv
outputs/publishable/tables/09C_riskon_cost_rejector/model_registry.csv
outputs/publishable/tables/09C_riskon_cost_rejector/oos_separability.csv
outputs/publishable/tables/09C_riskon_cost_rejector/calibration_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/threshold_frontier.csv
outputs/publishable/tables/09C_riskon_cost_rejector/cost_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/post_filter_retention_by_split.csv
outputs/publishable/tables/09C_riskon_cost_rejector/e1_missed_retention.csv
outputs/publishable/tables/09C_riskon_cost_rejector/density_concentration_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/riskoff_readonly_control.csv
outputs/publishable/tables/09C_riskon_cost_rejector/label_mechanism_overlap_ablation.csv
outputs/publishable/tables/09C_riskon_cost_rejector/selected_events.csv.gz
outputs/publishable/tables/09C_riskon_cost_rejector/rejected_events.csv.gz
outputs/publishable/tables/09C_riskon_cost_rejector/event_scores.csv.gz
```

manifest 至少包含：

```text
experiment_id
run_timestamp
git_commit
decision
source_caveated
input_hashes
output_hashes
config_hash
selected_target_label
selected_target_contract_hash
selected_label_event_bindings_hash
selected_feature_contract_hash
sample_uniqueness_weights_hash
selected_model_id
selected_threshold_id
source_pool_reconstruction_status
regime_label_pit_status
label_bridge_status
feature_leakage_status
forbidden_feature_count
threshold_selection_policy
density_concentration_status
oversized_artifact_policy
```

所有 publishable / local_cache 大表必须写入 manifest hash。若 publishable CSV 超大，应使用 `.csv.gz`，不得直接提交超大 raw CSV。

## 14. Report 必须解释

09C 报告必须用中文写清楚：

1. 09C uplift 是相对 09 baseline replay，而不是相对 H 旧 target 直接比较。
2. 新 target 与旧 `cost_bad_10_20` 的 bridge 关系如何影响 gate 解读。
3. 09B sample weights 如何被 09C 复用。
4. 哪些 feature family 贡献了稳定 importance，哪些只是同机制 proxy。
5. Calibration / monotonic constraint 是否改善 `0.775-0.800` 局部 frontier。
6. Risk-off read-only 对照说明 uplift 是否 risk_on 特异。
7. Transition 为什么继续冻结，不进入本实验训练。

## 15. 09C 决策

允许的 09C 决策：

```text
09C_riskon_cost_rejector_research_entry_supported
09C_riskon_cost_rejector_research_entry_source_caveated_supported
09C_riskon_cost_rejector_feature_source_supported
09C_riskon_cost_rejector_feature_source_caveated_supported
09C_riskon_cost_rejector_diagnostic_only_or_no_candidate
09C_riskon_cost_rejector_input_blocked
09C_riskon_cost_rejector_feature_leakage_blocked
```

如果任一上游带 source caveat，research-entry supported 与 feature-source supported 决策都必须带 `source_caveated` variant。
