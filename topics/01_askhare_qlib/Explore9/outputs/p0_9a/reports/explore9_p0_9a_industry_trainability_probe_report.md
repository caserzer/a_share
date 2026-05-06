# Explore9 P0.9A 行业专用 LGBM Trainability Probe 报告

## 1. 执行结论

P0.9A 的机械汇总结果给出 `recommendation = proceed_to_p0_9b_industry_lgbm_discovery_rerun`，但从审计数据看，这个结论不能被解读为“无条件进入下一阶段”。本轮实验确认了行业专用 LGBM 在 `电子 / 汽车 / 电力设备` 的 trainability 边界：`汽车` 和 `电子` 的两个任务都能在 `T1_fixed_rounds_no_inner_validation` 下形成足够 core folds；`电力设备` 两个任务均未达到 P0.9B 主合同资格。

最重要的保留意见来自 `p0_9a_sample_weight_group_cap_audit.csv`：9,709 条 group-cap 审计记录中有 72 条失败，`top_instrument_year_weight_share` 最高为 `9.42%`，超过配置上限 `8.00%`。这与“只在 count gate、purge gate、anti-leakage gate、class balance、sample weight 等规则通过时训练”的合同精神存在冲突。因此，本报告把 P0.9B 结论写为“条件性推进”：可以把 `汽车/电子 + T1` 作为下一阶段候选形态，但在启动 P0.9B 前必须重新处理或正式豁免 sample-weight cap 失败；否则不能把本轮结果称为 clean eligibility。

本轮没有产生后续建模精修、回测、策略冻结或已验证模型结论。AUC、logloss、Brier、feature importance、score bucket 和 2024 robustness 都只能作为诊断信息，不能用于选择合同，也不能扩大 P0.9B 候选范围。

## 2. 数据覆盖与 PIT 行业映射

三个目标行业的 PIT 映射均为 exact match，说明本轮没有因为行业名称或映射失败丢失目标行业。覆盖规模排序为 `电子 > 电力设备 > 汽车`，但行业覆盖规模并不直接决定 trainability；后续失败主要来自 fold 内 cross-section、purge 后样本和合同约束。

| industry | match | enabled | panel rows | instruments |
| --- | --- | --- | --- | --- |
| 电子 | exact_match | True | 59,280 | 35 |
| 汽车 | exact_match | True | 37,370 | 20 |
| 电力设备 | exact_match | True | 38,840 | 27 |

样本可行性上，failure 任务拥有显著更多 raw / eligible rows；launch 任务更稀疏，更容易在严格 fold gate 下失败。`电力设备` 的 raw 覆盖并不低，但可训练 fold 数不足，说明问题不是简单的总样本量，而是时间分布、purge 后剩余截面、instrument-year 权重集中度和合同结构共同造成的。

| industry | task | raw rows | eligible rows | raw positive labels | instruments | instrument-years |
| --- | --- | --- | --- | --- | --- | --- |
| 电子 | launch | 14,860 | 7,551 | 3,000 | 35 | 141 |
| 汽车 | launch | 9,385 | 5,505 | 1,660 | 19 | 88 |
| 电力设备 | launch | 9,670 | 4,507 | 1,485 | 26 | 91 |
| 电子 | failure | 44,420 | 24,652 | 20,550 | 35 | 155 |
| 汽车 | failure | 27,985 | 17,629 | 11,125 | 20 | 94 |
| 电力设备 | failure | 29,170 | 14,603 | 14,840 | 27 | 105 |

## 3. 合同矩阵结论

P0.9A 的合同选择没有使用模型指标，而是按预注册优先级和 trainability hard gates 决定。结果非常集中：所有可进入 P0.9B 的行业任务都落在 `T1_fixed_rounds_no_inner_validation`，没有任何 `T0/T2/T3/T4` 被推荐为主合同。

| industry | task | T0 core | T1 core | T2 core | T3 core | T4 core | P0.9B recommended |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 汽车 | failure | 0 | 4 | 2 | 2 | 4 | T1 |
| 汽车 | launch | 0 | 3 | 1 | 1 | 4 | T1 |
| 电力设备 | failure | 0 | 2 | 0 | 0 | 3 | none |
| 电力设备 | launch | 0 | 2 | 0 | 0 | 3 | none |
| 电子 | failure | 2 | 4 | 1 | 1 | 4 | T1 |
| 电子 | launch | 0 | 3 | 1 | 1 | 4 | T1 |

合同层面的含义如下：

- `T0_strict_p0_9_reproduction`：只在 5 个 industry-task-fold 组合上 strict trainable，其中 `电子 failure` 有 2 个 core folds，但不足以推荐。T0 与既有 P0.9 审计的 reconciliation 全部通过，差异均为可解释差异，没有 unexplained difference。
- `T1_fixed_rounds_no_inner_validation`：是唯一形成主合同资格的安全探针。全局 30 个组合中有 24 个 trainable_under_safe_probe；按行业任务聚合后，`汽车 failure` 4 folds、`汽车 launch` 3 folds、`电子 failure` 4 folds、`电子 launch` 3 folds 均达到资格。
- `T2_pooled_inner_validation`：全局只有 10 个组合 trainable，按行业任务聚合后没有一个任务达到主合同资格。其失败主要不是 inner split 泄漏，而是 latest-2-train-years 被留作 pooled inner validation 后，outer train purge 后截面不足。
- `T3_grouped_temporal_inner_validation`：结果与 T2 基本一致，说明 deterministic grouped temporal block 没有提供额外 trainability。它没有 backtracking，因此没有为了改善可训练性而改变合同。
- `T4_diagnostic_minimal_instrument_gate`：全局 28 个组合可训练，表明降低 instrument gate 后模型确实能跑起来；但它是 diagnostic-only，不能进入 P0.9B 主合同，也不能覆盖 `电力设备` 的资格缺口。

## 4. 行业任务分析

`汽车` 是本轮最干净的候选行业。failure 任务在 T1 下 4 个 core folds 全部 fit 且 non-degenerate，launch 任务在 T1 下 3 个 core folds 全部 fit 且 non-degenerate。OOF 诊断指标也相对最好，尤其 launch 的 AUC 为 `0.7348`，但这个数值只能说明探针有可学习迹象，不能作为合同选择依据。T2/T3 在汽车 launch 上出现过更高的诊断 AUC，但只有 1 个 core fold，不具备主合同资格。

`电子` 达到 trainability 资格，但信号质量明显弱于汽车。failure 任务 T1 有 4 个 core folds 且 sanity 通过，但 OOF AUC 为 `0.4866`，低于随机基准附近；这说明 failure reject 标签在当前固定轮数、当前特征、当前 purge 合同下可以训练出非退化模型，但不代表它已经有可交易的排序能力。launch 任务 T1 有 3 个 core folds，OOF AUC 为 `0.5201`，只能视为轻微信号。T2/T3 在 `电子 launch fold_2023` 出现 non-degenerate sanity 失败，模型只使用极少树和极少特征，进一步支持不要用 inner-validation 合同推进电子 launch。

`电力设备` 不应进入 P0.9B 主合同。两个任务在 T1 下都只有 2 个 core folds，未达到资格；T2/T3 为 0 core folds；T4 虽有 3 个 diagnostic folds，但 T4 明确不能推荐。这里的关键判断是：`电力设备` 的 raw 样本不少，failure raw positives 也不少，但 hard gates 后可用 fold 不足，不能用“行业看起来有样本”替代合同资格。

## 5. 模型诊断指标

下表只列出被推荐合同 `T1` 的 OOF 诊断指标。它们用于判断模型是否退化、是否值得在报告中描述信号形态，但不参与推荐。

| industry | task | T1 core folds | OOF events | AUC | logloss | Brier | 诊断解释 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 汽车 | failure | 4 | 2,750 | 0.5749 | 0.6849 | 0.2451 | 有弱可学习性，适合保留为 P0.9B 候选 |
| 汽车 | launch | 3 | 701 | 0.7348 | 0.4358 | 0.1434 | 本轮最强诊断信号，但仍不能作为选择依据 |
| 电子 | failure | 4 | 4,586 | 0.4866 | 0.9091 | 0.3321 | 可训练但排序信号弱，P0.9B 要重点做 null 对照 |
| 电子 | launch | 3 | 1,212 | 0.5201 | 0.5904 | 0.2059 | 轻微信号，需防止把 trainability 误读为有效性 |

非退化审计显示，所有被推荐的 `T1` 行业任务均通过 fit 与 sanity；失败集中在未推荐的 T2/T3 分支，例如 `电子 launch fold_2023` 和 `电力设备 launch fold_2024`。这些失败模型的 prediction uniqueness、prediction std、tree count 和 feature_used_count 都偏低，说明它们更像合同过严后的退化结果，而不是可用于发现阶段的稳定模型。

## 6. 泄漏、防穿越与标签窗口

本轮最强的正面结果来自 anti-leakage 和窗口审计：P0.9A 的可训练性结论没有依赖明显穿越。

| audit area | result |
| --- | --- |
| feature as-of leakage | 30 条审计记录，feature violation 为 0 |
| observed-reference overlap | eligible decision overlap 为 0，eligible feature overlap 为 0 |
| label horizon truncation | eligible truncated rows 为 0；raw truncated rows 为 3,995 |
| inner split leakage | inner split label-window cross 为 0；same-launch cross 为 0 |
| failure post-target exclusion | 130 条 post-target rows 被排除，entered training loss 为 0 |
| T0 reconciliation | 30 条 reconciliation 全部 pass，unexplained diff 为 False |

需要注意的是，raw 层面存在 `label_measurement_overlap = 31,205`，但这些 overlap 没有进入 eligible decision/feature audit 的违规项。也就是说，原始观测引用本身很宽，但 P0.9A 的 eligible training/evaluation 管线没有把它们用作训练期可见信息。

## 7. Failure 任务与权重审计

Failure 任务的事件级去重和窗口归一化基本满足训练探针需求。`汽车 T1` 的 failure window pass 与 event dedup pass 都是 5/5；`电子 T1` 也是 5/5。`电力设备 T1` 的 failure window pass 只有 3/5，event dedup pass 为 4/5，这与其最终不推荐一致。全量 failure window normalization 共 43,713 行，`window_weight_normalization_pass` 全部为 True。

真正需要阻塞下一步的是 sample-weight group cap。审计显示：

| metric | value |
| --- | --- |
| audited rows | 9,709 |
| failed rows | 72 |
| configured cap | 8.00% |
| max top instrument-year weight share | 9.42% |
| max instrument-year weight HHI | 0.0846 |

失败样本集中在部分早期 folds 与若干 instrument-year，例如 `SZ002459_2020`、`SH601727_2020` 等。这意味着某些训练切片的权重仍可能被单一 instrument-year 过度影响。即使 count gate 与 model fit 通过，也不能忽略这个集中度问题；它会直接影响 P0.9B 发现阶段的 null family 和可解释性。

## 8. Selection Boundary

合同选择审计确认，推荐只使用 `trainability_count_and_model_fit_only`，metric-selection violation 为 False。最终推荐边界应写成：

| industry | task | recommended contract | P0.9B status |
| --- | --- | --- | --- |
| 汽车 | failure | T1 | 条件性进入 P0.9B |
| 汽车 | launch | T1 | 条件性进入 P0.9B |
| 电子 | failure | T1 | 条件性进入 P0.9B，但信号弱 |
| 电子 | launch | T1 | 条件性进入 P0.9B，但信号弱 |
| 电力设备 | failure | none | 不进入主合同 |
| 电力设备 | launch | none | 不进入主合同 |

P0.9B 若继续推进，应承接 fixed 9 industries、selected 3 industries、2 tasks、全部 P0.9A contracts 与 deterministic selection rule 的 null / multiplicity family。推进前必须处理三件事：

- 明确 sample-weight group cap 失败是实现问题、配置问题，还是可以被正式豁免的诊断例外。
- 固定 `T1` 合同：launch 使用 64 rounds，failure 使用 32 rounds，不引入 early stopping 或基于 outer validation 的迭代选择。
- 保持 `电力设备` 为 diagnostic-only，不因为 T4 可以训练或 raw 样本充足而进入主合同。

## 9. Artifact Self-check

Section 17 要求的 artifact 已全部生成：required artifacts 为 `52`，missing 为 `0`。manifest 记录了 4 个 parquet cache artifacts 和 48 个 report artifacts；本报告仅根据这些已生成实验数据做分析展开。
