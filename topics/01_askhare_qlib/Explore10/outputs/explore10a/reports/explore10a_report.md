# Explore10A 汽车样本宽度与 Feature Bank Hygiene 审计报告

## 1. 执行结论

Explore10A 的 Phase-0 问题已经可以回答：汽车样本宽度坍缩的 phase-level root cause 是 `automotive_scope_width`，不是 P0.9B 到 Explore10 的行构造错误，不是 feature-asof / observed-reference / purge discipline violation，也不是单纯由 Alpha158-like v1 缺失导致。

最终 recommendation 为：

```text
stop_automotive_single_industry_path_due_to_sample_width
```

关键门禁结果：

| gate | result |
|:--|:--|
| sample_width_root_cause_proven_phase_level | True |
| phase_level_primary_bottleneck | automotive_scope_width |
| Explore10B readiness | False |
| Readiness block reason | root_cause_is_automotive_scope_width |
| required_artifact_authority_pass | True |
| forbidden recommendation self-check | True |
| primitive candidate / selected model / score bucket / backtest | 未产生 |

我的判断：当前结果不支持继续在“汽车单行业 + 原始 20 distinct instruments guardrail + path-to-primitive”这条路线上修 v2 feature bank。v1 feature bank 确实有 missingness 和重复问题，但汽车 launch 的 scope 本身在 core folds 已经只有 0/15/15/15 个 distinct instruments，低于原始 20 门槛；即使补回 v1 缺失的 2-3 个 instruments，也无法把 core folds 恢复到 Explore10B 所需宽度。

## 2. Requirement 问题逐项回答

| requirement question | answer | evidence |
|:--|:--|:--|
| 1. 汽车样本宽度为什么收缩到 12-13 个 distinct instruments？ | 因为汽车单行业 scope/event eligible universe 本身过窄；launch core folds 的 scope lock 宽度为 0/15/15/15，v1 feature 可用宽度进一步变成 0/12/13/13。 | `explore10a_sample_width_attribution.csv` |
| 2. 是构造 / scope lock / feature missing / purge / asof 问题，还是汽车单行业天然宽度不足？ | phase-level bottleneck 是 `automotive_scope_width`。P0.9B 与 Explore10 行身份完全匹配；asof、observed-reference、purge 审计通过；feature missing 是次级损耗，不是主因。 | reconciliation matched 22,492 rows, p0_only=0, explore10_only=0 |
| 3. v1 missing / duplicate 是否需要修复为 v2？ | 本 requirement 下不应启动支持 readiness 的 v2。v1 hygiene 不好，但 root cause 已证明为 automotive_scope_width；v2 只能作为未来 hygiene documentation，不支持 Explore10B。 | v2 artifacts: execution_status=not_started |
| 4. v2 后汽车 launch 是否能恢复足够 trainable core folds？ | 未允许计算；且按现有 scope 宽度看，恢复到原始 20 distinct instruments guardrail 的概率很低。Explore10A 输出 counterfactual status-only。 | trainability_counterfactual: not_started |
| 5. 是否停止汽车单行业 path-to-primitive，改成更宽 cohort？ | 是。当前推荐停止汽车单行业路线；下一阶段若继续，应改为 broader cohort 或 event-regime cohort requirement。 | recommendation=stop_automotive_single_industry_path_due_to_sample_width |

## 3. 数据与 artifact 权威性

Explore10A 使用现有 Explore10 / Explore9 / Explore7 产物做 repair audit，没有重跑 Explore10 path-to-primitive。输入 artifact 审计 18 项全部通过，输出 artifact authority 31 项全部通过。

| source artifact | rows | columns | pass |
|:--|--:|--:|:--|
| Explore10 lgbm train/eval panel | 54,029 | 411 | True |
| Explore10 atomic launch event panel | 11,748 | 410 | True |
| Explore10 atomic failure decision panel | 42,281 | 410 | True |
| P0.9B locked train/eval panel | 54,029 | 240 | True |
| P0.9B prediction panel | 12,354 | 244 | True |
| P0.9A trainability contract matrix | 150 | 15 | True |
| PIT universe membership | 439,140 | 16 | True |
| PIT industry membership | 439,140 | 6 | True |
| Feature bank v1 dictionary | 175 | 23 | True |
| Explore10 trainability audit | 20 | 26 | True |

输出侧：

| artifact class | count | pass |
|:--|--:|:--|
| report/json artifacts | 26 | True |
| parquet cache artifacts | 5 | True |

这意味着本报告的判断来自结构化 CSV/JSON/parquet 证据，而不是重新解释模型分数或手工选择样本。

## 4. Phase-0 Root Cause Gate

Phase-0 gate 的 fold-level、task-level、phase-level 都已显式区分。所有汽车 core folds 的 unknown loss weight share 为 0，secondary failure discipline violation count 为 0。因此 root cause 可以上升为 phase-level 结论。

| task | fold | fold proven | task proven | phase proven | bottleneck | unknown loss weight share |
|:--|:--|:--|:--|:--|:--|--:|
| launch_winner | fold_2020 | True | True | True | automotive_scope_width | 0.0000 |
| launch_winner | fold_2021 | True | True | True | automotive_scope_width | 0.0000 |
| launch_winner | fold_2022 | True | True | True | automotive_scope_width | 0.0000 |
| launch_winner | fold_2023 | True | True | True | automotive_scope_width | 0.0000 |
| launch_winner | fold_2024 | True | True | True | automotive_scope_width | 0.0000 |
| failure_reject | fold_2020 | True | True | True | automotive_scope_width | 0.0000 |
| failure_reject | fold_2021 | True | True | True | automotive_scope_width | 0.0000 |
| failure_reject | fold_2022 | True | True | True | automotive_scope_width | 0.0000 |
| failure_reject | fold_2023 | True | True | True | automotive_scope_width | 0.0000 |
| failure_reject | fold_2024 | True | True | True | automotive_scope_width | 0.0000 |

解读：`fold_2024` 是 robustness-only，不用于 readiness 支持；但它也显示同样的宽度问题。真正决定 phase-level 的是汽车 launch primary core folds，其中 `fold_2021` 到 `fold_2023` scope lock 只有 15 个 instruments，`fold_2020` launch 没有有效 scope rows。这个宽度低于 `min_distinct_instruments_original = 20`。

## 5. 汽车样本宽度归因

核心宽度表：

| task | fold | raw distinct | scope locked distinct | v1 available distinct | scope->v1 loss | scope gap to 20 | v1 gap to 20 | primary bottleneck |
|:--|:--|--:|--:|--:|--:|--:|--:|:--|
| launch_winner | fold_2020 | 0 | 0 | 0 | 0 | 20 | 20 | automotive_scope_width |
| launch_winner | fold_2021 | 15 | 15 | 12 | 3 | 5 | 8 | automotive_scope_width |
| launch_winner | fold_2022 | 15 | 15 | 13 | 2 | 5 | 7 | automotive_scope_width |
| launch_winner | fold_2023 | 15 | 15 | 13 | 2 | 5 | 7 | automotive_scope_width |
| launch_winner | fold_2024 | 17 | 17 | 13 | 4 | 3 | 7 | automotive_scope_width |
| failure_reject | fold_2020 | 12 | 12 | 10 | 2 | 8 | 10 | automotive_scope_width |
| failure_reject | fold_2021 | 15 | 15 | 13 | 2 | 5 | 7 | automotive_scope_width |
| failure_reject | fold_2022 | 16 | 16 | 13 | 3 | 4 | 7 | automotive_scope_width |
| failure_reject | fold_2023 | 16 | 16 | 13 | 3 | 4 | 7 | automotive_scope_width |
| failure_reject | fold_2024 | 17 | 17 | 13 | 4 | 3 | 7 | automotive_scope_width |

最重要的观察：

1. 对汽车 launch 主任务，`fold_2021`、`fold_2022`、`fold_2023` 在 raw/scope 阶段已经只有 15 个 instruments，距离 20 门槛差 5 个。
2. v1 feature availability 再损失 2-3 个 instruments，使 trainability denominator 变成 12-13，但这不是从 20 坍缩到 12-13 的主因；它只是把已经不足的 15 进一步压低。
3. 汽车 failure secondary task 也表现为相同方向：scope 宽度 12-16，v1 后 10-13。failure 不是 primary，但它支持“汽车单行业宽度不足”这个解释，而不是 launch label 单点异常。
4. `v2_restores_distinct_instruments = False`，因为在 `automotive_scope_width` 根因下，v2 不应被解释为能恢复原始 cohort 宽度。

## 6. Feature Availability 明细

Explore10A cache 中的 feature availability panel 覆盖 22,492 行。按 instrument/fold/task 聚合后，v1 feature availability 的损失集中在少数重复 instruments 上：

| task | fold | instruments | available instruments | unavailable instruments | unavailable names |
|:--|:--|--:|--:|--:|:--|
| launch_winner | fold_2021 | 15 | 12 | 3 | SH600297, SH600733, SZ000800 |
| launch_winner | fold_2022 | 15 | 13 | 2 | SH600297, SH600733 |
| launch_winner | fold_2023 | 15 | 13 | 2 | SH600297, SH600733 |
| launch_winner | fold_2024 | 17 | 13 | 4 | SH600066, SH600297, SH600418, SH600733 |
| failure_reject | fold_2020 | 12 | 10 | 2 | SH600066, SH600297 |
| failure_reject | fold_2021 | 15 | 13 | 2 | SH600066, SH600297 |
| failure_reject | fold_2022 | 16 | 13 | 3 | SH600066, SH600297, SH600733 |
| failure_reject | fold_2023 | 16 | 13 | 3 | SH600066, SH600297, SH600733 |
| failure_reject | fold_2024 | 17 | 13 | 4 | SH600066, SH600297, SH600418, SH600733 |

这个表对 v1 hygiene 有两个启发：

1. v1 缺失不是随机分散在所有汽车股票上，而是集中在少数 instrument 上，尤其是 `SH600297` 和 `SH600733`。这说明未来做 feature bank hygiene 时可以优先检查这些股票的 PIT OHLCV/rolling warmup/停牌或上市期覆盖。
2. 即使把这些 v1 unavailable instruments 全部补回来，汽车 launch core folds 也只是回到 15 个 instruments，仍然低于 Explore10B 原始门槛 20。因此它不能支撑 `proceed_to_explore10b_atomic_feature_bank_v2_rerun`。

## 7. P0.9B vs Explore10 Reconciliation

P0.9B 与 Explore10 的汽车行身份没有发现真实 row mismatch。总计 22,492 行 matched，`p0_9b_only_row_count = 0`，`explore10_only_row_count = 0`。

| task | fold | matched rows | P0.9B only | Explore10 only | common instruments | status |
|:--|:--|--:|--:|--:|--:|:--|
| launch_winner | fold_2021 | 852 | 0 | 0 | 15 | present_in_both_but_probe_contract_explained |
| launch_winner | fold_2022 | 1,078 | 0 | 0 | 15 | present_in_both_but_probe_contract_explained |
| launch_winner | fold_2023 | 1,320 | 0 | 0 | 15 | present_in_both_but_probe_contract_explained |
| launch_winner | fold_2024 | 1,613 | 0 | 0 | 17 | present_in_both_but_probe_contract_explained |
| failure_reject | fold_2020 | 2,073 | 0 | 0 | 12 | present_in_both_but_probe_contract_explained |
| failure_reject | fold_2021 | 2,843 | 0 | 0 | 15 | present_in_both_but_probe_contract_explained |
| failure_reject | fold_2022 | 3,404 | 0 | 0 | 16 | present_in_both_but_probe_contract_explained |
| failure_reject | fold_2023 | 4,144 | 0 | 0 | 16 | present_in_both_but_probe_contract_explained |
| failure_reject | fold_2024 | 5,165 | 0 | 0 | 17 | present_in_both_but_probe_contract_explained |

Schema 侧有 2 个 optional keys 缺失，被记录为 schema-key missing，而不是 row mismatch。所有 matched rows 都被归类为 `present_in_both_but_probe_contract_explained`，说明 P0.9B 与 Explore10 的主要差异不是“样本丢了”，而是 probe contract / feature eligibility / trainability guardrail 使这些行不能进入 path extraction。

我的判断：这排除了一个重要假设，即“Explore10 写错了汽车 panel 或 scope lock，把 P0.9B 的汽车样本误删了”。行身份和权重对齐后，问题回到样本宽度和 trainability guardrail 本身。

## 8. Explore10 Trainability 证据

汽车 launch/failure 的 trainability audit 显示失败 predicate 主要是 `distinct_instruments`。这与 Phase-0 root cause 一致。

| task | fold | role | train rows after purge | validation rows | train positives | validation positives | feature count | distinct instruments | pass | failed predicate |
|:--|:--|:--|--:|--:|--:|--:|--:|--:|:--|:--|
| launch_winner | fold_2020 | core_oof | 0 | 0 | 0 | 0 | 0 | 0 | False | train/validation/positive/instrument/features all insufficient |
| launch_winner | fold_2021 | core_oof | 601 | 206 | 95 | 44 | 160 | 12 | False | distinct_instruments |
| launch_winner | fold_2022 | core_oof | 819 | 213 | 196 | 40 | 160 | 13 | False | distinct_instruments |
| launch_winner | fold_2023 | core_oof | 1,018 | 256 | 236 | 30 | 160 | 13 | False | distinct_instruments |
| launch_winner | fold_2024 | robustness_only | 1,254 | 1 | 260 | 0 | 160 | 13 | False | validation_event_count; validation_positive_count; distinct_instruments |
| failure_reject | fold_2020 | core_oof | 1,320 | 605 | 547 | 161 | 163 | 10 | False | distinct_instruments |
| failure_reject | fold_2021 | core_oof | 1,993 | 635 | 745 | 320 | 163 | 13 | False | distinct_instruments |
| failure_reject | fold_2022 | core_oof | 2,516 | 642 | 971 | 231 | 163 | 13 | False | distinct_instruments |
| failure_reject | fold_2023 | core_oof | 3,114 | 751 | 1,249 | 304 | 163 | 13 | False | distinct_instruments |
| failure_reject | fold_2024 | robustness_only | 3,951 | 6 | 1,543 | 6 | 163 | 13 | False | validation_event_count; distinct_instruments |

这里有一个关键差异：row count 并不总是小，failure task 有上千训练行，但这些行集中在 10-13 个 instruments 上。Path-to-primitive 的问题不是“没有事件行”，而是“独立股票宽度不足”。这会放大 instrument-specific artifacts，也会让 tree path 容易变成少数股票的历史切片，而不是可泛化的行业 primitive。

## 9. Discipline Audits

数据纪律审计没有发现能解释样本坍缩的违规。

| audit | rows / count | result |
|:--|--:|:--|
| feature-asof eligible rows | 19,901 | pass |
| feature-asof leakage violations | 0 | pass |
| observed-reference decision/feature overlap eligible rows | 0 | pass |
| observed-reference decision overlap | 0 | pass |
| observed-reference feature overlap | 0 | pass |
| observed-reference label-measurement overlap | 0 | pass |
| purge audit rows with crossing flag | 9 | walk_forward_purge_pass=True, pass=True |

解读：`purge_audit` 中每个 fold 有 1 条 crossing diagnostic，但该 artifact 的 `walk_forward_purge_pass=True` 且 `pass=True`，因此它不构成 discipline violation，也不能解释 automotive scope width。更重要的是，observed-reference 和 asof 的 hard violation 都是 0。

## 10. Feature Bank v1 Hygiene

Explore10 原始 feature bank preflight 显示 v1 确实不干净：

| metric | value | pass |
|:--|--:|:--|
| feature_count_total | 164 | |
| allowed_for_path_extraction_count | 164 | |
| missing_row_rate | 0.3552 | False |
| missing_weight_share | 0.3857 | False |
| constant_or_near_constant_rate | 0.0183 | True |
| duplicate_or_high_corr_cluster_count | 64 | False |
| duplicate threshold | 0.995 | |
| max_feature_family_share | 0.2927 | True |
| feature_family_missing_weight_share_max | 0.2331 | |
| feature_bank_preflight_pass | False | False |

这说明 v1 的 missingness 和 duplicate/high-corr cluster 是真实的 hygiene 问题。可是 Explore10A 的门禁结论是：它不是本阶段 primary root cause。原因很简单：

1. v1 前的汽车 launch core scope 宽度已经只有 15 或 0。
2. v1 后宽度变成 12-13，确实恶化，但没有改变“低于 20”的根本事实。
3. requirement 明确规定当 `phase_level_primary_bottleneck = automotive_scope_width` 时，不得把 v2 construction 用作 Explore10B readiness 支持。

因此，v2 artifacts 正确地输出 status-only：

| artifact group | execution_status | not_started_reason | upstream_gate_pass |
|:--|:--|:--|:--|
| feature_bank_v2_dictionary | not_started | root_cause_is_automotive_scope_width | True |
| feature_bank_v1_to_v2_hygiene_audit | not_started | root_cause_is_automotive_scope_width | True |
| v2 feature drop / duplicate / missingness / family coverage | not_started | root_cause_is_automotive_scope_width | True |

## 11. Trainability Counterfactual

Counterfactual 没有启动：

| field | value |
|:--|:--|
| execution_status | not_started |
| not_started_reason | root_cause_is_automotive_scope_width |
| feature_bank_version | v2_hygiene |
| primitive_candidate_generation_allowed | False |
| path_extraction_allowed | False |

这不是缺失实验，而是正确执行 requirement。Counterfactual 只有在 v2 被允许构造且 root cause 允许 repair 时才有意义；在 `automotive_scope_width` 下，放松到 15 或 12 instruments 只能作为 future diagnostic，不能支持 Explore10B。

## 12. Electronics Placebo

Electronics 在 Explore10 reference 中更容易生成候选：

| evidence | value |
|:--|--:|
| electronics_v1_path_candidate_count_reference | 99 |
| electronics launch trainable core folds | 3 |
| electronics failure trainable core folds | 4 |
| electronics_v2 status | not_started |
| placebo_dominates_primary_risk | False |

这里的 insight 是：电子 placebo 的“容易出 candidates”进一步证明 sample width matters。电子在 core folds 中有 24-25 个 distinct instruments，能够通过更多 trainability folds；汽车只有 12-13 个 v1-available distinct instruments，自然无法形成 path eligible folds。

但 Explore10A 没有运行 v2 placebo path-to-primitive，因此不能得出“电子 v2 是否仍然产生稳定候选”的完整结论。它只能作为 reference risk：如果未来改 broader cohort，需要保留 placebo guardrail，防止更宽样本只是在制造更容易讲故事的负控路径。

## 13. Sample Weight 与 Concentration

Sample weight / concentration gate 通过。没有 weight cap violation，最大 top instrument-year weight share 和 HHI 都低于配置门槛。

| metric | observed max | threshold | pass |
|:--|--:|--:|:--|
| top_instrument_year_weight_share | 0.0571 | 0.0800 | True |
| instrument_year_weight_hhi | 0.0433 | 0.0800 | True |
| weight_cap_violation_count | 0 | 0 | True |

按 fold 看，top5 instrument contribution 大约在 0.6588 到 0.7104。这个集中度并未触发权重门禁，但它提醒我们：在只有 12-13 个 instruments 的汽车任务里，即使权重 cap 合规，解释性路径仍然容易被少数 instrument-year 主导。这是停止单行业路径的另一个实践理由。

## 14. Explore10B Readiness

Readiness gate 结果：

| condition | result |
|:--|:--|
| sample_width_root_cause_proven_phase_level | True |
| phase_level_primary_bottleneck | automotive_scope_width |
| primary_bottleneck_allowed_for_explore10b | False |
| feature_bank_v2_hygiene_pass | False |
| feature_asof_leakage_violation_count | 0 |
| observed_reference_decision_feature_overlap_eligible_rows | 0 |
| trainable_core_fold_count_for_explore10b | 0 |
| sample_weight_and_concentration_pass | True |
| electronics placebo guardrail does not dominate primary | True |
| metric selection violation count | 0 |
| threshold selection violation count | 0 |
| required_artifact_authority_pass | True |
| explore10b_readiness_pass | False |

结论：Explore10B readiness 被正确阻断。阻断点不是 artifact authority、leakage、observed-reference、sample weight 或 threshold selection，而是 requirement Section 14 明确排除的 `automotive_scope_width`。

## 15. Findings 与研究洞察

### 15.1 主要发现

第一，Explore10 汽车失败不是“模型没调好”。所有汽车 folds 的 tree_count 为 0，是 trainability guardrail 阻断后没有进入 fit/path extraction，而不是 LightGBM 已训练后 alpha 弱。

第二，Explore10 汽车失败也不是“P0.9B 到 Explore10 行被误删”。P0.9B/Explore10 reconciliation 的 matched rows 为 22,492，两个方向的 only rows 都是 0。这是很强的反证。

第三，feature bank v1 有质量问题，但不是当前 phase 的 first-order bottleneck。v1 missingness 可以解释 15 到 12/13 的二级收缩，不能解释为什么 automotive launch 一开始就只有 15 个 scope instruments。

第四，汽车 failure secondary task 支持同一结论。它不是 primary，但 scope 宽度 12-17、v1 后 10-13，与 launch 的问题同向。

第五，电子 placebo 的 99 个 reference candidates 不是 Explore10A 的成果，而是风险信号：更宽行业更容易形成路径。未来如果换 broader cohort，必须继续保留 placebo/null/concentration guardrail，否则只是在更宽样本上制造更漂亮的树路径。

### 15.2 对下一步的建议

不建议直接进入 `Explore10B atomic_feature_bank_v2_rerun`。

更合理的下一步是写一个 broader cohort requirement，至少要改变 denominator，而不是只修 feature dictionary。候选方向：

1. 汽车 + 电新 + 机械 + 电子中与汽车产业链相关的 broader manufacturing cohort。
2. `event-regime cohort`：按 launch/failure event regime 聚合，而不是按单一申万行业锁死。
3. 保留汽车为 slice / appendix diagnostic，而不是 primary path-to-primitive source。
4. 若仍要修 v2 feature bank，应定位为 provider/feature hygiene 文档，不应承诺恢复 Explore10B readiness。

我不建议降低 `min_distinct_instruments_original = 20` 来放行汽车单行业。把门槛降到 15 或 12 会让当前 folds 看起来可训练，但这违反 requirement 的 Explore10B readiness 定义，也会让 path 更容易变成少数股票的历史规则。

## 16. Forbidden Boundary Check

Explore10A 没有产生以下 forbidden outputs：

| forbidden output | violation |
|:--|--:|
| proceed_to_explore11_manual_atomic_primitive_formula_discovery | 0 |
| proceed_to_strategy_backtest | 0 |
| candidate_for_p1_strategy | 0 |
| validated_model | 0 |
| selected_lgbm_model | 0 |
| selected_score_bucket | 0 |
| atomic_primitive_candidate_for_next_requirement | 0 |
| freeze_strategy | 0 |

最终边界声明：Explore10A 已证明汽车单行业样本宽度是当前主瓶颈。这个结论支持停止汽车单行业 path-to-primitive 路线，或另写 broader cohort requirement；不支持进入 Explore10B，也不支持从本阶段产出任何 primitive、模型、score bucket、交易规则或回测结论。
