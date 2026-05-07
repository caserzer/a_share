# Explore10B 电子行业样本宽度可行性验证报告

报告位置：`Explore10/outputs/explore10b/reports/explore10b_report.md`

## 1. 执行结论

Explore10B 的结论是：

```text
recommendation = proceed_to_explore10c_electronics_path_quality_requirement
width_problem_solved_phase_level = true
electronics_launch_width_solved_excluding_expected_fold_2020_boundary = true
secondary_failure_diagnostic_status = pass
```

这表示：在当前 Explore10 的 row identity、feature availability、trainability denominator 与数据纪律约束下，`电子` 这个宽行业标签已经解决了 Explore10A 暴露的汽车单行业样本宽度问题。下一步可以写 Explore10C，专门验证电子行业 path quality / primitive quality。

但这个结论的边界必须保持清楚：

```text
Explore10B 只证明电子是否解决样本宽度问题，不证明电子 primitive 有效。
```

本阶段没有训练新模型，没有 path extraction，没有 primitive discovery，没有选择 score bucket，没有策略回测，也没有产生 P1 candidate。

## 2. 样本宽度主结论

Explore10A 显示汽车 launch core folds 的 trainability denominator 只有 `0 / 12 / 13 / 13`，低于原始门槛 `min_distinct_instruments_original = 20`。Explore10B 把 primary scope 切到电子后，launch required core folds `fold_2021 / fold_2022 / fold_2023` 全部超过 20。

### 2.1 电子 launch width gate

| fold | scope locked instruments | v1 feature available instruments | trainability denominator instruments | gate |
|---|---:|---:|---:|---|
| fold_2020 | 0 | 0 | 0 | expected_event_history_boundary |
| fold_2021 | 26 | 26 | 24 | pass |
| fold_2022 | 25 | 25 | 24 | pass |
| fold_2023 | 27 | 27 | 25 | pass |
| fold_2024 | 30 | 30 | 25 | robustness only, not support |

关键判断：

- `fold_2020` launch 为 0，是已分类的 `expected_event_history_boundary`，不作为 10B launch pass 的必要支持。
- 真正用于 launch width pass 的三个 core folds 是 `fold_2021 / fold_2022 / fold_2023`。
- 这三个 folds 的 trainability denominator 分别为 `24 / 24 / 25`，均高于门槛 20。
- v1 feature availability 没有造成额外 instrument 级坍缩：scope locked 与 feature available 在三折中均为 `26/25/27`。

结论：电子 launch 在 required core folds 上解决了汽车阶段的样本宽度问题。

### 2.2 电子 failure secondary diagnostic

| fold | scope locked instruments | v1 feature available instruments | trainability denominator instruments | gate |
|---|---:|---:|---:|---|
| fold_2020 | 23 | 23 | 21 | pass |
| fold_2021 | 28 | 28 | 24 | pass |
| fold_2022 | 28 | 28 | 24 | pass |
| fold_2023 | 30 | 30 | 25 | pass |
| fold_2024 | 33 | 33 | 25 | robustness only, not support |

failure task 是 secondary diagnostic，不能替代 launch primary。但它提供了一个重要交叉验证：电子不是只在 launch 任务上偶然变宽，failure side 也稳定超过 20。

结论：secondary failure diagnostic 也支持“电子宽度足够”的判断，且 `secondary_failure_diagnostic_status = pass`。

## 3. Feature Availability 研究数据

Explore10B 的 feature availability 必须来自 row-level cache：

```text
Explore10/outputs/explore10/cache/explore10_lgbm_train_eval_panel.parquet
```

实际使用的 predicate 是：

```text
sample_has_required_features = true
feature_asof_leakage_violation = false if present
```

本阶段没有用 `explore10_fold_trainability_audit.csv` 的 `feature_available_count` 替代 row-level feature width；也没有启用 fallback。

### 3.1 Feature available row count

| task | fold_2020 | fold_2021 | fold_2022 | fold_2023 | fold_2024 |
|---|---:|---:|---:|---:|---:|
| launch_winner | 0 | 1104 | 1472 | 1913 | 2396 |
| failure_reject | 2309 | 3636 | 4861 | 6107 | 7739 |

### 3.2 Feature available distinct instruments

| task | fold_2020 | fold_2021 | fold_2022 | fold_2023 | fold_2024 |
|---|---:|---:|---:|---:|---:|
| launch_winner | 0 | 26 | 25 | 27 | 30 |
| failure_reject | 23 | 28 | 28 | 30 | 33 |

观察：

- launch 的 `fold_2021 / fold_2022 / fold_2023` 在 feature availability 后没有掉到 20 以下。
- failure 的四个 core folds 全部在 feature availability 后保持 23 到 30 个 distinct instruments。
- 电子的 feature row count 随年份增长明显，但 distinct instrument count 只从 20 多到 30 多，说明下一阶段不能只看 row count，仍要控制 instrument / instrument-year concentration。

结论：Explore10B 的宽度改善不是通过放宽 feature availability 得到的，也不是 report-only 字段推断出来的；它来自 row-level cache 的可验证行级证据。

## 4. 与汽车的宽度对比

Explore10A 的 root cause 是：

```text
phase_level_primary_bottleneck = automotive_scope_width
```

Explore10B 对比电子与汽车的 trainability denominator：

| task | fold | electronics denominator | automotive denominator | delta |
|---|---|---:|---:|---:|
| launch_winner | fold_2020 | 0 | 0 | 0 |
| launch_winner | fold_2021 | 24 | 12 | +12 |
| launch_winner | fold_2022 | 24 | 13 | +11 |
| launch_winner | fold_2023 | 25 | 13 | +12 |
| failure_reject | fold_2020 | 21 | 10 | +11 |
| failure_reject | fold_2021 | 24 | 13 | +11 |
| failure_reject | fold_2022 | 24 | 13 | +11 |
| failure_reject | fold_2023 | 25 | 13 | +12 |

核心 insight：

- 电子 launch 的 required core folds 比汽车多约 11 到 12 个可训练 distinct instruments。
- 这不是微弱改善，而是从“不足 20”的失败区间移动到“稳定超过 20”的可探查区间。
- failure side 也有相似幅度的改善，说明电子行业标签作为 broad denominator handle 是有效的。
- `fold_2020` launch 不能用来支持电子通过，它只是 expected event-history boundary；因此本阶段的有效 launch 结论是 `fold_2021 / fold_2022 / fold_2023` 三折通过。

## 5. 数据纪律与 row identity 审计

Explore10B 的数据纪律全部通过。

| audit item | result |
|---|---:|
| feature_asof_leakage_violation_count | 0 |
| observed_reference_decision_feature_overlap_eligible_rows | 0 |
| row_identity_mismatch_count | 0 |
| fold_2024_support_usage_count | 0 |
| threshold_selection_violation_count | 0 |
| metric_selection_violation_count | 0 |
| forbidden_recommendation_violation_count | 0 |

row identity 使用 task-aware keys：

- launch: `instrument;fold_id;signal_date;event_effective_date;launch_stratum_event_id`
- failure: `instrument;fold_id;failure_signal_date;failure_decision_effective_date;launch_stratum_event_id;atomic_failure_event_id`

所有 folds 的 `row_identity_key_status = complete`，没有 `schema_key_missing`，也没有 missing/extra mismatch。`fold_2020` launch 的零行通过 expected boundary 处理，不被误记为 purge 或 row identity violation。

结论：电子样本宽度通过不是由 leakage、purge 错误、observed-reference overlap 或 row identity mismatch 造成的。

## 6. 后验选择边界

电子不是 Explore10 原始 primary scope。Explore10B 选择电子，是因为 Explore10 / Explore10A 已经观察到：

- 汽车 primary 因 `automotive_scope_width` 失败。
- 电子 reference scope 有更宽 denominator。
- 电子 reference scope 产生了 candidate-like path records。

因此电子在 Explore10B 中只能支持一个结论：

```text
electronics_sample_width_solved_for_next_requirement
```

它不能支持：

```text
electronics_alpha_or_primitive_validated
```

角色重标也已经审计：

| Explore10 reference role | Explore10B role |
|---|---|
| 电子 launch_winner = weak_signal_sanity_check | primary_sample_width_probe |
| 电子 failure_reject = negative_control_placebo | secondary_width_diagnostic |

`role_relabel_used_for_alpha_claim = false`。这意味着后验选择被显式记录，但没有被用来做 alpha 或 primitive 有效性结论。

## 7. Candidate reference count 的使用边界

Explore10B 只读取候选表中的：

```text
industry
task
```

然后按 `industry/task` 分组计数：

| industry | task | reference_candidate_count | usage |
|---|---|---:|---|
| 电子 | launch_winner | 49 | width evidence only |
| 电子 | failure_reject | 50 | width evidence only |

审计确认：

| forbidden read surface | read |
|---|---|
| formula columns | false |
| primitive text | false |
| threshold columns | false |
| metric value columns | false |

这 99 条 candidate-like path records 只能说明 Explore10 infrastructure 在电子 scope 上有足够行宽来产生 reference records，不能说明这些 paths 有 alpha，也不能说明任何 primitive 可进入下一阶段。

## 8. Artifact authority 与 cache hygiene

Explore10B artifact contract 全部通过：

| item | result |
|---|---:|
| artifact_count_expected | 22 |
| artifact_count_produced | 22 |
| required_artifact_authority_pass | true |
| cache_tracking_pass | true |
| recommendation_allowed | true |

row-level parquet caches：

| cache | rows | columns | git ignored |
|---|---:|---:|---|
| explore10b_electronics_launch_width_panel.parquet | 6885 | 412 | true |
| explore10b_electronics_failure_width_panel.parquet | 24652 | 412 | true |
| explore10b_electronics_feature_availability_panel.parquet | 31537 | 14 | true |

报告和审计 CSV 是可追踪 artifact；parquet cache 被 `.gitignore` 排除，且 `tracked_by_git = false`。

## 9. 研究发现与判断

### 9.1 第一发现：电子确实解决了样本宽度问题

汽车的问题是行业 scope 本身太窄，feature bank v1 缺失不是第一瓶颈。电子切换后，launch required core folds 的 trainability denominator 达到 `24 / 24 / 25`，failure core folds 达到 `21 / 24 / 24 / 25`。这已经越过原始门槛 20。

所以，从样本宽度角度看，继续围绕汽车单行业做 path-to-primitive 没有意义；电子是更适合验证 Explore10 infrastructure 的宽行业 handle。

### 9.2 第二发现：电子宽度不是靠放松 gate 得来的

Explore10B 没有降低 `min_distinct_instruments_original = 20`。`fold_2024` 也没有用于 support。feature availability 是从 row-level cache 计算，不是从汇总 report 反推。候选表也只用于 grouped count，不读取公式、阈值或指标。

因此本阶段的通过是一个比较干净的 width feasibility pass。

### 9.3 第三发现：电子可以进入 Explore10C，但不能直接进入 P1

Explore10C 应该验证 path quality / primitive quality，包括但不限于：

- 电子 paths 是否在 OOF 上有稳定 lift。
- null / placebo 后是否仍然成立。
- 是否存在 instrument-year concentration。
- 是否能形成可手工解释的 primitive。
- 后验选择带来的 selection-family 风险如何控制。

Explore10B 不能跳过这些问题。当前只能说“样本宽度足够，可以继续问 path-quality 问题”。

### 9.4 第四发现：行业标签仍不是产业链定义

电子行业解决的是 denominator 问题，不解决真实上下游 membership 问题。它是一个 broad denominator handle，而不是业务同质 cohort。后续如果要回到汽车产业链问题，仍然需要人工产业链 cohort 或更可靠的主题/供应链映射。

## 10. 13 个 requirement 问题的回答

1. 电子是否解决了汽车暴露的样本宽度问题？

   是。launch required core folds `fold_2021 / fold_2022 / fold_2023` 的 trainability denominator 为 `24 / 24 / 25`，全部高于 20。

2. 电子 launch 的 `fold_2021 / fold_2022 / fold_2023` 是否都 >=20 distinct instruments？

   是。scope locked 为 `26 / 25 / 27`，feature available 为 `26 / 25 / 27`，trainability denominator 为 `24 / 24 / 25`。

3. `fold_2020` launch zero rows 是否已分类？

   是，分类为 `expected_event_history_boundary`。它不作为 launch width pass 的支持 fold。

4. 电子 failure 是否作为 secondary diagnostic 支持同一结论？

   是。failure core folds 的 trainability denominator 为 `21 / 24 / 24 / 25`，`secondary_failure_diagnostic_status = pass`。

5. feature availability 后电子宽度是否仍然足够？

   是。除 `fold_2020` launch expected boundary 外，feature availability 后 launch/failure 均保持 >=20 distinct instruments。

6. 电子宽度优势是否来自真实 row scope，而不是 leakage / mismatch？

   是。row identity mismatch 为 0，feature-asof violation 为 0，observed-reference overlap eligible rows 为 0，purge pass 为 true。

7. 与汽车相比，宽度差异是多少？

   Launch required folds 上，电子 trainability denominator 比汽车多 `+12 / +11 / +12`。Failure core folds 上多 `+11 / +11 / +11 / +12`。

8. 电子作为 Explore10B primary 是否属于后验选择，边界如何处理？

   是，属于后验选择。报告只允许输出 sample-width feasibility 结论，不允许输出 alpha、primitive 或策略结论。

9. Explore10 reference role 如何被重标为 Explore10B role？

   Explore10 中电子 launch 是 `weak_signal_sanity_check`，在 Explore10B 中重标为 `primary_sample_width_probe`；电子 failure 是 `negative_control_placebo`，在 Explore10B 中重标为 `secondary_width_diagnostic`。

10. candidate reference count 是否只作为宽度证据使用？

   是。只读取 `industry/task`，按 grouped row count 得到 launch 49、failure 50；不读取 formula、primitive、threshold 或 metric。

11. 是否可以进入下一份 path-quality requirement？

   可以。Recommendation 是 `proceed_to_explore10c_electronics_path_quality_requirement`。

12. 本阶段没有回答哪些问题？

   没有回答电子 path 是否有 alpha、primitive 是否有效、是否能进入 P1、是否能回测、是否能形成交易规则或 freeze strategy。

13. 是否触发任何 forbidden output？

   没有。Forbidden self-check 全部通过。

## 11. 最终建议

Explore10B 已经完成“电子是否解决样本宽度问题”的验证。建议下一阶段写 Explore10C requirement，问题应从 width feasibility 转向 path-quality / primitive-quality：

```text
电子行业在样本宽度足够的前提下，Explore10 产生的 path records 是否有稳定、可解释、非后验污染的 primitive-quality evidence？
```

Explore10C 仍然不能直接做策略回测或 P1 推进。它应该先验证 path 是否真实有质量，而不是因为电子更宽就默认 paths 有效。
