# 需求总览：09 Risk-on Fast-Fail Label / Feature / Cost Rejector Uplift

本目录将 09 拆成三份独立 requirement。三份 requirement 是串联关系，不是并行实验网格：

```text
09A_fast_fail_label_frontier
    ↓
09B_feature_foundation_ablation
    ↓
09C_riskon_cost_rejector_uplift
```

09 的主线判断来自 `08_risk_on_transition_recall_exploration_v0`：`risk_on` 已有足够 recall source，后续瓶颈不是继续找 source，也不是继续 transition family rediscovery，而是把 fast-fail / false-repair 成本 target 定义清楚，并提升 `0.775-0.800` 附近的局部排序质量。

## 1. 三份 Requirement

| requirement | 角色 | 是否训练模型 | 是否允许输出 supported |
| --- | --- | --- | --- |
| `requirement_09a_fast_fail_label_frontier.md` | 纯 label diagnostic，冻结 selected fast-fail / cost target 与事件级 label binding | 否 | 只允许输出 09A candidate selected |
| `requirement_09b_feature_foundation_ablation.md` | 构建 t0 feature foundation、sample weights、importance 与 mechanism overlap audit | 否，不做最终模型 | 只允许输出 09B feature foundation complete |
| `requirement_09c_riskon_cost_rejector_uplift.md` | 用 09A selected label 与 09B feature foundation 训练 risk_on cost rejector | 是 | 允许输出 research-entry / feature-source / diagnostic |

`requirement.md` 只是路由与总约束，不替代三份子需求。实现时必须读取对应子需求。

## 2. 执行顺序与阻塞关系

1. 先执行 09A。
2. 09A 输出 `09A_label_frontier_candidate_selected` 或 `09A_label_frontier_candidate_source_caveated_selected` 后，09C 才允许进入 supported gate。
3. 如果 09A 只输出 `diagnostic_only_no_candidate`，09B 仍可执行，但 09C 只能 diagnostic。
4. 09B 输出 `09B_feature_foundation_complete` 后，09C 才允许输出 research-entry supported。
5. 如果 09B blocked 或 diagnostic-only，09C 只能 diagnostic。
6. 09C 不得重新定义 label，不得重算 sample weights，不得做 full-sample feature selection。

## 3. 共享上游输入

三份 requirement 都必须遵守以下上游约束，并在各自 manifest 中记录 hash：

```text
topics/02_AFML_BIG_WINNER/README.md
topics/02_AFML_BIG_WINNER/research_direction_discussion_20260614.md
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/08_all_experiments_final_report.md
```

核心 08 manifest：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/density_fast_fail_audit/density_fast_fail_audit_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/post_replay_event_to_episode_retention_source/post_replay_event_to_episode_retention_source_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/risk_on_post_filter_cost_rejector/risk_on_post_filter_cost_rejector_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/risk_on_cost_rejector_research_entry_hardening/risk_on_cost_rejector_research_entry_hardening_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/transition_subregime_taxonomy_audit/transition_subregime_taxonomy_audit_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/transition_previous_regime_outcome_audit/transition_previous_regime_outcome_audit_manifest.json
../08_risk_on_transition_recall_exploration_v0/outputs/manifests/transition_previous_regime_context_cost_rejector_ablation/transition_previous_regime_context_cost_rejector_ablation_manifest.json
```

核心事件、label、feature 与 membership 源：

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

07 E1 baseline：

```text
../07_topn_multichannel_repair_candidate_generator_v0/outputs/manifests/run_manifest.json
../07_topn_multichannel_repair_candidate_generator_v0/outputs/publishable/tables/topn_multichannel_candidate_event_canonical.csv
../07_topn_multichannel_repair_candidate_generator_v0/outputs/local_cache/topn_canonical_event_labels.parquet
```

如果 D / E / H manifest 缺失或 hash 不可读，09 必须停止：

```text
decision = 09_input_blocked_missing_core_upstream
```

如果 E1 baseline 无法重建，09C 必须停止：

```text
decision = 09_riskon_uplift_e1_baseline_blocked
```

## 4. 共享非目标

09 明确不做：

1. 不做 `transition` primary model、transition cost rejector、transition family rediscovery。
2. 不把 `transition_from_*`、`transition_conversion`、`next_regime` 作为训练特征或 threshold 选择字段。
3. 不继续 C 的 R-series deterministic compression arm grid。
4. 不发明新 event family；09 默认使用 08 已证明的 R-core / R6 source。
5. 不做 full entry backtest、组合收益曲线、仓位模拟、止盈止损或交易执行策略。
6. 不把 `winner_120` 当作唯一 entry label。
7. 不在 validation / robustness 上调参。
8. 不做 full-sample feature selection、full-sample PCA、full-sample scaling 或 full-sample calibration。
9. 不把 post-event volume、future return、future high/low、future barrier touch 或 label-derived variable 当作 t0 feature。
10. 不因为新 target 使 cost reduction 更容易，就直接声称相对 H 旧 frontier 的 uplift。

## 5. 共享 Regime / Split 纪律

09 必须区分：

1. `event_regime_bucket`：event t0 / replay anchor date 上可观测的 market regime，可作为 t0 feature 或 gating feature。
2. `episode_regime_bucket`：target episode low date 或 D membership 中的 target regime，用于 recall / bridge / E1-missed retention readout。

09 的主训练 scope 是：

```text
event_regime_bucket = risk_on
source_pool in {08_R_core_event_regime_gated, 08_R6_event_regime_gated}
```

headline retention readout 必须按 `episode_regime_bucket = risk_on` 报告。若 event regime 与 episode regime 同时出现，报告必须列出交叉矩阵，不得混用。

09A 必须先输出：

```text
outputs/publishable/tables/09A_fast_fail_label_frontier/regime_label_pit_audit.csv
outputs/publishable/reports/09A_fast_fail_label_frontier/regime_label_pit_audit.md
```

如果 `risk_on` 无法按公开规则重建，或 robustness consistency 低于预声明下限，09C 不得输出 supported。

## 6. 共享 Source Pool Reconstruction Contract

09 必须通过 08 A 的 scope mapping contract 重建所有训练与对照 source pool，不得用临时字符串匹配或手写 family list：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
```

必须重建并审计：

1. `08_R_core_event_regime_gated`
2. `08_R6_event_regime_gated`
3. `07_E1_only`
4. 09C risk_off read-only 对照使用的 risk_off E1 / available sample

重建要求：

1. `scope_status` 必须是 `reconstructable_event_membership` 或等价可审计状态。
2. `hard_gate_eligible_flag` 必须为 true，才可进入 09C supervised training 或 research-entry gate。
3. aggregate-only R compression arms 不得作为 09 训练样本、threshold frontier、density gate 或 replay retention source。
4. R-core 继续接受 08 A / H 已审计的 `47914` vs published `47929` 的 `-15` 差异；但必须在 `source_pool_reconstruction_audit.csv` 中记录 accepted difference reason。
5. 如果 reconstructed event count 与 `source_row_count` 不一致，且该差异未被上游 audit 接受，必须停止。

09 必须输出：

```text
outputs/publishable/tables/input_audit/source_pool_reconstruction_audit.csv
```

## 7. Source Caveat 传播

当前 08 的 A/B/C/D/E/H 多个上游都是 `source_caveated` 或 `partial_source_complete` 状态。09 可以继续运行，但必须传播 caveat：

1. 如果 D / E / H 任一上游为 source-caveated，09C 的 supported 决策必须使用 `source_caveated` variant。
2. 如果 09A / 09B 因 local-cache-only source、untracked raw source 或 compressed replacement 才能运行，manifest 必须记录 `source_caveated = true`。
3. 报告不得声称 production-ready entry gate，只能声称 research-entry / diagnostic evidence。

## 8. 09 总输出

目录级最终输出：

```text
outputs/manifests/run_manifest.json
outputs/publishable/reports/09_riskon_fastfail_label_feature_uplift_report.md
```

三份子需求各自输出：

```text
outputs/manifests/09A_fast_fail_label_frontier_manifest.json
outputs/manifests/09B_feature_foundation_ablation_manifest.json
outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
outputs/publishable/reports/09A_fast_fail_label_frontier_report.md
outputs/publishable/reports/09B_feature_foundation_ablation_report.md
outputs/publishable/reports/09C_riskon_cost_rejector_uplift_report.md
outputs/publishable/tables/09A_fast_fail_label_frontier/candidate_label_evaluability_audit.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_contract.csv
outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_event_binding_summary.csv
outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
```

所有 publishable / local_cache 大表必须写入 manifest hash。若 publishable CSV 超大，应使用 `.csv.gz`，不得直接提交超大 raw CSV。

## 9. 总决策

09 总决策由 09A / 09B / 09C 共同决定：

```text
09_riskon_fastfail_label_feature_uplift_research_entry_supported
09_riskon_fastfail_label_feature_uplift_source_caveated_supported
09_riskon_fastfail_label_feature_uplift_feature_source_supported
09_riskon_fastfail_label_feature_uplift_diagnostic_only_or_no_candidate
09_riskon_fastfail_label_feature_uplift_input_blocked
```

只有同时满足以下条件，才允许输出 research-entry supported：

1. 09A selected label 成立，且新旧 target bridge 清楚。
2. 09A regime PIT audit 支持 risk_on scope。
3. 09B feature foundation complete。
4. 09B sample weights 被 09C 复用。
5. 09C selected model / threshold 通过 train-only gate。
6. validation / robustness 不反转。
7. density / concentration / leakage audit pass。
8. overlap ablation 未证明 full model 只是 label mechanism proxy。

否则必须降级为 feature-source supported、diagnostic-only 或 input-blocked。

## 10. 一句话要求

不要继续找新 source，不要继续 transition，不要继续调 keep threshold。先把 fast-fail / cost target 定义清楚并与 H 旧 target 对账，再构建可审计的 t0 feature foundation 和冻结 sample weights，最后只在 risk_on R-core / R6 source 上训练少量模型，用 train-only threshold 证明新的 label + feature 确实把 cost / recall frontier 推过线。
