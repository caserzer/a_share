# 需求总览：10 Risk-on Layered Rejector System

本目录是 09 reviewer-driven revision 后的独立 10 阶段 requirement。10 不再把 rejector 写成一个 hybrid model，而是拆成三层系统：

```text
10A = density rule system, non-ML
10B = fast-fail structural gate, low capacity
10C = false-repair rejector, medium capacity
```

## 1. 三份 Requirement

| requirement | 角色 | 是否训练模型 | supported scope |
| --- | --- | --- | --- |
| `requirement_10a_density_rule_system.md` | Layer 0 density / execution rules，冻结 post-dedup population | 否 | R-core population freeze |
| `requirement_10b_fast_fail_structural_gate.md` | Layer 1 fast-fail structural safety gate | 是，仅 fast-fail-only | post-dedup R-core |
| `requirement_10c_false_repair_rejector.md` | Layer 2 false-repair exposure-efficiency rejector | 是，仅 false-repair component | post-dedup R-core |

## 2. 执行顺序

```text
10A post-dedup population freeze
    ↓
10B fast-fail supported gate on post-dedup population
10C false-repair supported gate on post-dedup population
    ↓
cascade-level overlap-deduplicated readout
```

10A 尝试输出全部预声明 no-score rule arms，每个可构造 arm 都是一份 frozen post-dedup population variant；若缺少 arm-specific event-level 字段，只 block 对应 arm，不连坐 instrument-only arms。10B / 10C 可以并行做 pre-dedup diagnostic replay，但 supported gate 必须读取 10A 冻结后的某个 `population_id`。禁止用 pre-dedup 训练 / 选择的模型直接 claim post-dedup supported gate，也禁止根据 validation / robustness 模型读数回选 10A arm。

Score-aware arms such as `score then cooldown` / `cooldown then score` are not owned by 10A；它们只能作为 10B / 10C post-score cascade diagnostic。

## 3. 共享依赖

10 读取 09 的 label / feature / diagnostic 产物作为上游输入：

```text
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09A_fast_fail_label_frontier_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09B_feature_foundation_ablation_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09C_riskon_cost_rejector_uplift_manifest.json
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/feature_matrix.parquet
../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09B_feature_foundation/sample_uniqueness_weights.parquet
```

09 local_cache parquet 是硬依赖，预期位于服务器环境。如果缺失，本地 run 必须 input-blocked，不得从 publishable aggregate table 反推 event-level binding、feature matrix 或 sample weights。

10 继续读取 08 source pool / membership contract：

```text
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_event_instances.csv.gz
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/reports/density_fast_fail_audit/density_fast_fail_caliber_contract.md
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_mapping_contract.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_scope_reconstructability_audit.csv
../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/post_replay_event_to_episode_retention_source/post_replay_label_leakage_audit.csv
```

## 4. 共享纪律

supported scope：

```text
event_regime_bucket = risk_on
source_pool_id = 08_R_core_event_regime_gated
input_denominator_id = risk_on_r_core_horizon_complete
denominator_id = post_dedup_risk_on_r_core
population_id = 10A__same_instrument_cooldown_10d by default
```

R6 只能 readout-only：

```text
no fit
no feature selection
no threshold selection
no cooldown tuning
no supported gate
```

只要 source caveat 未修复，所有正向结论只能使用 `source_caveated` variant。

## 5. 共享非目标

10 明确不做：

1. 不继续 hybrid cost model tuning。
2. 不继续 PCA-driven feature expansion。
3. 不在 validation / robustness 上选择 threshold。
4. 不做 transition modeling。
5. 不把 E1 baseline 当作 rejector uplift 的主比较对象。
6. 不声称 production-ready 或 entry-candidate。
