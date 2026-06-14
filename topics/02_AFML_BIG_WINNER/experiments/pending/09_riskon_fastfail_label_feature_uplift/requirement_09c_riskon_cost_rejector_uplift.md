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

09C 当前唯一 supported target 是：

```text
break_swing_low_20__or_false_repair_20d
```

`fixed_mae10_neg_12__or_false_repair_20d` 只允许作为 sensitivity / aggregate readout 背景。除非 09A 后续补发完整事件级 binding，并在 contract 中显式改为 `usable_for_09C_supported_gate=true`，否则 09C 不得把 fixed-12 目标用于 supported training、threshold selection 或 research-entry gate。

09C 必须把 09A 的 `source_caveated=true` 继承到本实验 manifest 与最终决策。若 09C 达到 research-entry gate，决策也只能使用 `source_caveated` variant，不能升级成无 caveat supported。

09C 必须读取 09B 输出：

```text
outputs/manifests/09B_feature_foundation_ablation_manifest.json
outputs/local_cache/09B_feature_foundation/feature_matrix.parquet
outputs/publishable/tables/09B_feature_foundation/feature_contract.csv
outputs/publishable/tables/09B_feature_foundation/feature_matrix_schema.csv
outputs/publishable/tables/09B_feature_foundation/feature_stationarity_audit.csv
outputs/publishable/tables/09B_feature_foundation/sample_uniqueness_audit.csv
outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
outputs/publishable/tables/09B_feature_foundation/label_mechanism_overlap_audit.csv
outputs/publishable/tables/09B_feature_foundation/group_mda_importance.csv
outputs/publishable/tables/09B_feature_foundation/single_feature_importance.csv
outputs/publishable/tables/09B_feature_foundation/feature_transform_contract.json
```

09B 必须是：

```text
decision = 09B_feature_foundation_complete
```

否则 09C 只能 diagnostic，不得输出 research-entry supported。

`feature_matrix.parquet` 是 09C 唯一允许消费的 model feature matrix。09C 不得从 08 raw feature panel、09B feature contract 或 schema 重新 materialize model matrix；contract / schema 只能用于字段审计与解释。若 `feature_matrix.parquet` 缺失或无法按 `(sample_id, selected_target_id, denominator_id)` 与 09A binding、09B weights 唯一 join，必须停止：

```text
decision = 09C_riskon_cost_rejector_input_blocked
```

09C 必须显式读取 09B 的以下风险结论，并在 config / report 中标记：

1. `fast_fail_only_10d` 与 `hybrid_cost_bad_10_20` 的主导 family 不同。
2. `hybrid_cost_bad_10_20` 更接近 `false_repair_20d_component`，不能替代 fast-fail-only 结论。
3. `break_swing_low_20` 与 FS2 / FS3 中部分 price-location、EMA、range、ATR feature 存在 mechanism overlap。
4. rolling / fracdiff hygiene feature 存在 train split warmup missing 更高的 asymmetry。
5. 09B importance 来自 LogisticRegression 诊断模型，09C 需要非线性 shallow-tree 读数对照。

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
8. 不把 09B 的 diagnostic AUC 解释为 research-entry 通过。
9. 不使用 global PCA 作为主降维或主解释流程。

## 5. Source Pool 与 Caveat

09C 主训练 scope：

```text
event_regime_bucket = risk_on
source_pool = 08_R_core_event_regime_gated
denominator_id = risk_on_r_core_horizon_complete
```

09C scope 分层必须严格遵守：

| denominator | 09C role |
| --- | --- |
| `risk_on_r_core_horizon_complete` | 唯一 supported training / threshold / research-entry denominator |
| `risk_on_r6_horizon_complete` | readout-only，不参与 fit、feature selection、threshold selection 或 supported gate |
| `risk_off_e1_horizon_complete_readonly` | readonly control / input audit，不进入 feature、weight、importance 或 threshold scope |

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
2. 冻结 baseline feature set：09B `feature_contract.csv` 中 `feature_family = FS0_baseline_h_features` 且 `allowed_for_09C_flag = true` 的 feature。
3. H-style model：balanced L2 logistic regression。
4. 09A selected target。
5. 09B sample weights。

09C 必须输出 baseline feature list 与 hash：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/baseline_feature_list.csv
```

不得在 implementation 中临时选择 “H allowed features” 或 “after lag20 drop” 的替代口径；如果 FS0 baseline feature 无法从 09B contract 重建，必须 input-blocked。

这个 baseline 是 09C uplift 的真正对照。H 旧 target frontier 只作为历史背景。

baseline replay 必须按 target component 拆开。字段映射冻结如下：

| target_component | 09A binding field | contract component id | weight_horizon_id | baseline role |
| --- | --- | --- | --- | --- |
| `fast_fail_only_10d` | `selected_fast_fail_10_label` | `break_swing_low_20` | `fast_fail_10d` | 证明 swing-low fast-fail 本身是否可排序 |
| `false_repair_20d_component` | `frozen_false_repair_20d_label` | `frozen_event_false_repair_20d_label` | `cost_bad_10_20_20d` | 拆出 false-repair 主导结构 |
| `hybrid_cost_bad_10_20` | `selected_cost_bad_10_20_target` | `break_swing_low_20__or_false_repair_20d` | `cost_bad_10_20_20d` | 09C 主 cost target |

09C 不得只输出 hybrid baseline。若 fast-fail-only component 无法从 binding 重建，必须降级：

```text
decision = 09C_riskon_cost_rejector_diagnostic_only_or_no_candidate
```

## 7. 模型候选

模型数量必须控制：

```text
logistic / elastic net
random forest or bagging shallow trees
shallow LightGBM
```

最低模型集合必须包含：

1. `h_style_logistic_baseline`：复现 H-style balanced L2 logistic baseline。
2. `regularized_logistic_or_elastic_net`：09C 的线性主候选。
3. `shallow_tree_or_bagging_shallow_trees_diagnostic`：用于检查 FS3 / FS4 / FS6 非线性交互是否被线性模型低估。

LightGBM 若使用，必须是 shallow configuration，并且不能扩大成多模型大网格。validation / robustness 只读，不得用于模型家族选择或 threshold 选择。

必须显式测试 train-fold calibration：

```text
Platt / logistic calibration
isotonic calibration
calibration fit inside train fold only
calibration before/after frontier readout around keep_0800
```

对于有明确经济方向的 feature，例如 drawdown、stop-distance、ATR-normalized distance、volatility shock，允许 monotonic constraint 或 monotonic sanity check。单调约束的目标是提升局部排序稳定性，不是追求最高 AUC。

所有模型必须同时报告三个 target component 的 OOS separability、frontier 和 cost / recall readout。模型可以选择一个主 target 做最终 threshold，但不能省略 component-level 读数。

`model_registry.csv` 的最小唯一键必须是：

```text
(model_family, train_target_component, ablation_id, calibration_id)
```

其中：

1. `train_target_component in {fast_fail_only_10d, false_repair_20d_component, hybrid_cost_bad_10_20}`。
2. 每个 `train_target_component` 可以训练独立模型，但 validation / robustness 只读。
3. research-entry selected model 默认只能从 `train_target_component = hybrid_cost_bad_10_20` 的模型中选择。
4. `fast_fail_only_10d` 与 `false_repair_20d_component` 模型用于 component-level 诊断与 feature-source 判断；除非 config 预先冻结独立 failure-only research gate，否则不得替代 hybrid 主模型 claim cost-rejector research-entry。
5. selected threshold 必须由 train split 的 frozen selection policy 产生；不得用 validation / robustness 的 AUC、recall 或 cost readout 选择模型家族、ablation 或 calibration。

## 8. Feature Use 与 Leakage Block

09C 只能使用 09B `feature_contract.csv` 中 `allowed_for_09C_flag = true` 的 t0 feature。

09C 必须从 09B `feature_transform_contract.json` 复用以下规则：

1. imputer 只在 train fold / train scope fit。
2. winsor / scaler 只在 train fold / train scope fit。
3. validation / robustness / R6 / risk-off 只 transform，不 fit。
4. PCA 默认不使用；若作为 sensitivity，只能 family 内 train-fold fit，并必须与 raw / representative feature 对照。

必须禁止：

1. `failure_10_label`
2. `frozen_false_repair_20d_label` / `event_false_repair_20d_label`
3. `winner_120`
4. post-replay membership flag
5. future MFE / MAE
6. future high / low
7. transition outcome / conversion label
8. `next_regime`
9. any post-event volume or return
10. any label-derived variable

实际字段黑名单至少包括以下列；这些列只允许作为 target、metadata、audit 或 readout，不得进入 model feature matrix：

```text
selected_fast_fail_10_label
frozen_false_repair_20d_label
selected_cost_bad_10_20_target
event_big_winner_120d_label
event_super_winner_120d_label
event_near_winner_120d_label
selected_fast_fail_touch_date
selected_fast_fail_touch_pos
selected_fast_fail_touch_offset_sessions
selected_fast_fail_barrier_id
label_t1_date
censoring_status
candidate_outcome_120d_status
winner_censoring_status
```

若任何 forbidden field 进入 model matrix，停止：

```text
decision = 09C_riskon_cost_rejector_feature_leakage_blocked
```

09C 还必须输出 feature family 使用审计：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/feature_family_usage_audit.csv
```

该表至少包含每个 model / target_component 的 feature count、family count、direct_overlap_feature_count、related_overlap_feature_count、rolling_fracdiff_feature_count。

## 8.1 Target Component 与 Weight Horizon

09C 必须把 target 和 weight horizon 显式绑定，不允许使用通用 sample weight：

| target_component | 09A binding field | weight_horizon_id | label_t1_date |
| --- | --- | --- | --- |
| `fast_fail_only_10d` | `selected_fast_fail_10_label` | `fast_fail_10d` | 10D fast-fail horizon |
| `false_repair_20d_component` | `frozen_false_repair_20d_label` | `cost_bad_10_20_20d` | 20D horizon |
| `hybrid_cost_bad_10_20` | `selected_cost_bad_10_20_target` | `cost_bad_10_20_20d` | max(10D, 20D) horizon |

`sample_uniqueness_weights.parquet` 中 `final_sample_weight = 0` 的样本不得进入对应 horizon 的训练损失、threshold selection 或 train gate，但可以保留在 coverage / not-evaluable readout 中。

`target_component_contract.csv` 必须把上表的 `target_component`、`09A binding field`、`contract component id`、`weight_horizon_id`、`label_t1_date rule` 固化为机器可读 contract。09C 实现不得在代码里硬编码另一套 target 字段映射。

09C 必须输出：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/target_component_contract.csv
outputs/publishable/tables/09C_riskon_cost_rejector/weight_horizon_usage_audit.csv
```

`weight_horizon_usage_audit.csv` 至少按 target_component / denominator / split 报告 sample_n、positive_n、evaluable_n、zero_weight_n、avg_uniqueness_mean、concurrency_mean。

## 8.2 09A Label Caveat 继承

09C 必须继承 09A 的以下 caveat：

1. `break_swing_low_20` 是 low-positive-rate structural gate，不能默认解释为精准 cost rejector。
2. 09C 必须报告 non-winner hit rate / bad-side coverage，避免把低 positive rate 自动解释为高质量。
3. validation winner injury 属于 low-power readout，不能用于模型或 threshold 选择。
4. 若 OOS positive-rate spread 超过 15pp，最终 supported 决策必须降级为 diagnostic-only。
5. downstream horizon 只能使用 `selected_fast_fail_touch_offset_sessions`，不得用 `selected_fast_fail_touch_pos` 推导相对交易日。

这里的 OOS positive-rate spread 指 selected threshold 后的 rejected fraction split spread，而不是 raw target prevalence：

```text
rejected_fraction(split) = rejected_event_n(split) / evaluable_event_n(split)
oos_positive_rate_spread = max(
    abs(rejected_fraction(validation) - rejected_fraction(train)),
    abs(rejected_fraction(robustness) - rejected_fraction(train))
)
```

该规则只对最终 selected model / selected threshold 的 `hybrid_cost_bad_10_20` 主 gate 生效；fast-fail-only 与 false-repair component 需要报告同口径 readout，但不单独触发此 15pp 降级线。

09C 必须输出：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/bad_side_coverage_readout.csv
```

该表至少包含 target_component / model_id / threshold_id / split 下的 positive_rate、non_winner_hit_rate、winner_injury_rate、kill_wrong_rate、winner_complete_n、winner_power_caveat。

## 9. Threshold / Gate

09C 必须在 config 中冻结：

```text
selected_target_label
target_component_selection_policy
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
baseline_replay_gate_refreeze_policy
fast_fail_only_auc_min_robustness
fast_fail_only_bad_side_capture_min_policy
fast_fail_component_contribution_min_train
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
| fast-fail-only robustness AUC | >= 0.60 |
| fast-fail-only train bad-side capture | >= random rejection baseline |
| fast-fail attributed cost-reduction share, train | >= 10% |

`train relative cost reduction >= 15%` 是从 H 旧 target 继承的 placeholder 默认值，不得未经复核直接解释为新 target 的 research-entry 门槛。09C 必须在 §6 baseline replay 完成后、读取 validation / robustness 任何 readout 前，基于新 target 的 train-only baseline replay 重新冻结最终 `cost_reduction_min_train`：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/gate_refreeze_audit.csv
```

`gate_refreeze_audit.csv` 至少包含：

```text
gate_name
placeholder_default_value
baseline_replay_train_value
final_frozen_value
refreeze_reason
fit_scope = risk_on_r_core_horizon_complete/train
oos_readout_seen_before_freeze = false
```

如果 09A selected target 与旧 target 差异极大，默认 gate 可以在 config 中重新冻结，但必须在 `gate_refreeze_audit.csv` 与 report 中解释重声明原因，并禁止与 H 旧 frontier 逐点比较。

09C threshold 选择必须只基于 train，并以 `hybrid_cost_bad_10_20` 的 accepted cost reduction / winner recall retention frontier 为主 gate；同时必须满足 fast-fail-only component 的非坍塌约束：

| auxiliary gate | default |
| --- | ---: |
| fast-fail-only train bad-side capture | >= selected-threshold rejected fraction |
| fast-fail-only robustness AUC | >= 0.60 |
| false-repair component contribution | report |
| fast-fail attributed cost-reduction share, train | >= 10% |
| hybrid-vs-component dominance | report and no false-repair-only pass |

定义：

```text
selected_threshold_rejected_fraction_train
    = rejected_event_n(train) / evaluable_event_n(train)

fast_fail_bad_side_capture_train
    = rejected_event_n(train where selected_fast_fail_10_label = 1)
      / evaluable_event_n(train where selected_fast_fail_10_label = 1)
```

`fast_fail_bad_side_capture_train` 必须不低于 `selected_threshold_rejected_fraction_train`，否则说明 selected threshold 对 fast-fail positives 的捕获不优于随机拒绝基准。

component attribution 必须把 hybrid positives 拆成互斥 bucket：

```text
fast_fail_only    = selected_fast_fail_10_label = 1 and frozen_false_repair_20d_label = 0
false_repair_only = selected_fast_fail_10_label = 0 and frozen_false_repair_20d_label = 1
both              = selected_fast_fail_10_label = 1 and frozen_false_repair_20d_label = 1
neither           = selected_fast_fail_10_label = 0 and frozen_false_repair_20d_label = 0
```

默认 attribution：

```text
fast_fail_attributed_cost_reduction
    = cost_reduction(fast_fail_only) + 0.5 * cost_reduction(both)

fast_fail_attributed_cost_reduction_share
    = fast_fail_attributed_cost_reduction / total_hybrid_cost_reduction
```

如果 `total_hybrid_cost_reduction <= 0`，research-entry gate 自动不通过。默认 `fast_fail_attributed_cost_reduction_share_train >= 10%`；config 可以更严格，但不得更宽松。若最终模型只在 hybrid target 上通过，但 fast-fail-only AUC、bad-side capture 或 attributed cost-reduction share 未过上述 hard gate，09C 只能输出 feature-source supported 或 diagnostic，不得 claim fast-fail cost-rejector uplift。

09C 必须输出 component-level threshold frontier：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/threshold_frontier_by_component.csv
outputs/publishable/tables/09C_riskon_cost_rejector/component_contribution_readout.csv
```

`component_contribution_readout.csv` 至少回答：selected threshold 的 rejected events 中，有多少来自 fast-fail-only、false-repair-only、both、neither；cost reduction 主要由哪个 component 贡献。

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

由于 `break_swing_low_20` 是 low-positive-rate structural gate，density cap 可能天然容易通过。09C 必须在 report 中说明 density gate 对 selected threshold 是否仍有约束力，并输出：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/density_gate_binding_audit.csv
```

该表至少包含每个 density / concentration metric 的 value、cap、cap_usage_ratio、binding_flag。若所有 density cap 的 `cap_usage_ratio < 0.25`，报告必须将 density gate 标为 weakly-binding，不得把“轻松通过 density”解释为 source 质量改善。

## 11. Risk-off Read-only 对照

09C 必须输出：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/riskoff_readonly_control.csv
outputs/publishable/tables/09C_riskon_cost_rejector/riskoff_transform_coverage_audit.csv
```

规则：

1. 默认使用 09C 在 risk_on train 上 fit 完成的 selected preprocessing、model、calibration 和 threshold，直接 score risk_off sample。
2. 不允许为了 risk_off 对照重新训练模型、重新 fit calibration、重新选择 threshold 或重新选择 feature。
3. 在 risk_off E1 或可审计 risk_off sample 上只输出 readout。
4. 不调参。
5. 不进入 09C gate。
6. 只用于判断 uplift 是否 risk_on 特异。

`riskoff_transform_coverage_audit.csv` 必须使用同一个 risk_on R-core train-fitted imputer / winsor / scaler，对 risk_off read-only sample 报告：

```text
feature_id
missing_rate_before_impute
winsor_low_clip_rate
winsor_high_clip_rate
post_transform_null_rate
risk_on_train_reference_rate
clip_rate_excess_vs_risk_on_train
```

如果 risk_off 的任一核心 feature family clip rate 显著高于 risk_on train，risk-off readout 只能定性解释 uplift 是否 risk_on 特异，不得定量比较 uplift 幅度。

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
4. drop FS2 related subset only。
5. drop FS0 rolling / fracdiff hygiene features。
6. family representative features only。

如果去掉 overlap features 后模型完全坍塌，09C 可以仍输出 diagnostic，但不得把 full model 的可分性解释为稳定泛化 alpha。

09C 必须额外输出 warmup / imputation 风险审计：

```text
outputs/publishable/tables/09C_riskon_cost_rejector/warmup_missing_ablation.csv
```

该表至少包含：

1. `log_close_fracdiff_d04`、`panel_return_20d_rolling_z_60d`、`panel_return_20d_rolling_pct_60d` 的 per-split missing rate。
2. full feature set vs without rolling / fracdiff hygiene features 的 target_component readout。
3. imputation pattern 是否在 train / validation / robustness 之间形成明显 split cue 的 caveat。

若 removing overlap 或 removing rolling / fracdiff hygiene 后，09C 的 supported conclusion 依赖关系发生反转，必须降级为：

```text
decision = 09C_riskon_cost_rejector_feature_source_supported
```

或对应 `source_caveated` variant，不能输出 research-entry supported。

## 13. 输出

09C 必须输出：

```text
outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
outputs/publishable/reports/09C_riskon_cost_rejector_uplift_report.md
outputs/publishable/tables/09C_riskon_cost_rejector/09C_h_style_baseline_replay_on_selected_target.csv
outputs/publishable/tables/09C_riskon_cost_rejector/gate_refreeze_audit.csv
outputs/publishable/tables/09C_riskon_cost_rejector/baseline_feature_list.csv
outputs/publishable/tables/09C_riskon_cost_rejector/model_registry.csv
outputs/publishable/tables/09C_riskon_cost_rejector/oos_separability.csv
outputs/publishable/tables/09C_riskon_cost_rejector/target_component_contract.csv
outputs/publishable/tables/09C_riskon_cost_rejector/weight_horizon_usage_audit.csv
outputs/publishable/tables/09C_riskon_cost_rejector/feature_family_usage_audit.csv
outputs/publishable/tables/09C_riskon_cost_rejector/calibration_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/threshold_frontier.csv
outputs/publishable/tables/09C_riskon_cost_rejector/threshold_frontier_by_component.csv
outputs/publishable/tables/09C_riskon_cost_rejector/component_contribution_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/bad_side_coverage_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/cost_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/post_filter_retention_by_split.csv
outputs/publishable/tables/09C_riskon_cost_rejector/e1_missed_retention.csv
outputs/publishable/tables/09C_riskon_cost_rejector/density_concentration_readout.csv
outputs/publishable/tables/09C_riskon_cost_rejector/density_gate_binding_audit.csv
outputs/publishable/tables/09C_riskon_cost_rejector/riskoff_readonly_control.csv
outputs/publishable/tables/09C_riskon_cost_rejector/riskoff_transform_coverage_audit.csv
outputs/publishable/tables/09C_riskon_cost_rejector/label_mechanism_overlap_ablation.csv
outputs/publishable/tables/09C_riskon_cost_rejector/warmup_missing_ablation.csv
outputs/publishable/tables/09C_riskon_cost_rejector/selected_events.csv.gz
outputs/publishable/tables/09C_riskon_cost_rejector/rejected_events.csv.gz
outputs/publishable/tables/09C_riskon_cost_rejector/event_scores.csv.gz
```

`selected_events.csv.gz`、`rejected_events.csv.gz`、`event_scores.csv.gz` 的 schema 必须至少包含：

```text
sample_id
selected_target_id
denominator_id
event_split
train_target_component
model_id
ablation_id
calibration_id
threshold_id
score
selected_flag
rejected_flag
selected_fast_fail_10_label
frozen_false_repair_20d_label
selected_cost_bad_10_20_target
```

R6 readout 与 R-core supported 行必须通过 `denominator_id` 区分；component model / hybrid model 必须通过 `train_target_component` 区分。缺少这些字段时，大表不得进入 publishable 输出。

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
selected_supported_target_id
selected_target_contract_hash
selected_label_event_bindings_hash
selected_feature_contract_hash
feature_matrix_hash
sample_uniqueness_weights_hash
baseline_feature_list_hash
selected_model_id
selected_threshold_id
target_component_status
weight_horizon_usage_status
label_mechanism_overlap_ablation_status
warmup_missing_ablation_status
bad_side_coverage_status
gate_refreeze_status
density_gate_binding_status
riskoff_transform_coverage_status
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
8. `break_swing_low_20` 的低 positive rate 到底带来 bad-side coverage，还是只是“几乎不过滤”。
9. fast-fail-only、false-repair component、hybrid target 三者的排序质量与贡献差异。
10. no-overlap ablation 和 warmup hygiene ablation 是否改变结论。
11. shallow-tree / bagging shallow trees 诊断是否发现线性模型低估的 FS3 / FS4 / FS6 非线性交互。
12. 为什么 PCA 没有进入主流程；若做 sensitivity，必须说明 family 内 train-fold fit 的结果。
13. `15%` cost-reduction placeholder 如何在 baseline replay 后、OOS readout 前被重新冻结。
14. fast-fail attributed cost-reduction share 是否达到预声明下限；若未达到，为什么不能 claim fast-fail uplift。
15. density gate 在 low-positive-rate swing-low target 下是否仍然 binding。
16. risk-off read-only 对照是否受到 transform clip / coverage 差异影响。

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

决策解释规则：

1. 只有同时通过主 hybrid gate、component-level fast-fail 非坍塌约束、overlap ablation、warmup ablation、density / concentration gate，才允许 research-entry supported。
2. 如果模型有 OOS separability，但 cost / recall frontier 未通过，只能是 feature-source supported 或 diagnostic。
3. 如果 supported 结论主要依赖 overlap feature 或 rolling / fracdiff missing pattern，只能是 feature-source supported，不得是 research-entry supported。
4. 如果 09C 只证明 false-repair component 有排序质量，而 fast-fail-only 无改善，必须在 report 中明确写成 false-repair uplift，不得 claim fast-fail uplift。
