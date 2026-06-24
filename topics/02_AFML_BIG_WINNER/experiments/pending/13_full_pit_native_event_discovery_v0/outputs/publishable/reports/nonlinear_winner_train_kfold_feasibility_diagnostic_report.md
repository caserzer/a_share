# 13E Nonlinear Winner Train-KFold Feasibility Diagnostic Report

## 1. 裁决

13E 的结论是 **stop: no nonlinear AUC improvement**。在 train-only、purged K-fold 的诊断口径下，非线性模型没有在预注册的主比较上提供可接受的增量 winner capacity，因此本诊断 **不授权 sequence mining、meta-labeling 或 bet sizing**。

| item | value |
|---|---:|
| decision_state | 13E_stop_no_nonlinear_auc_improvement |
| selected_state_id | repair_range_participation_core_30 |
| train event rows | 6,232 |
| validation_used_in_13e | false |
| robustness_used_in_13e | false |
| confirmatory_status | false |
| sequence_mining_authorized | false |
| meta_labeling_authorized | false |
| bet_sizing_authorized | false |
| next_allowed_requirement | none |
| primary_failure_reason | nonlinear_auc_improvement_gate_failed |
| train_kfold_capacity_readout | nonlinear_capacity_signal_absent |

这个结果的含义不是“event 完全没有信息”，而是更窄的一句话：**在 13C 已经给出的 augmented morphology/residual feature set 之上，用 HistGradientBoostingClassifier 不能稳定战胜 logistic baseline**。因此 13E 不能作为继续推进 winner entry、meta-labeling 或风险预算放大的依据。

## 2. Gate 状态

| gate | status | interpretation |
|---|---|---|
| input_gate_status | pass | 输入工件齐全。 |
| upstream_lineage_gate_status | pass | 13C lineage、schema、row count 和 feature dictionary 对齐。 |
| row_level_rebuild_gate_status | pass | 逐行从 event panel 重建，未使用报告文字作为 row truth。 |
| nonlinear_model_availability_gate_status | pass | logistic 与 HGB 都完成训练与评估。 |
| purged_cv_integrity_gate_status | pass | K-fold 使用 t1 重建、purge 和 embargo。 |
| sample_uniqueness_gate_status | pass_with_exact_t1 | 所有 fold 都用 exact t1 计算 uniqueness。 |
| nonlinear_auc_improvement_gate_status | fail | 主比较 AUC 没有达到非线性增量门槛。 |
| nonlinear_uplift_improvement_gate_status | fail | uplift 均值略正，但 fold 方向不稳定。 |
| nonlinear_utility_proxy_gate_status | fail | 50bps utility 均值略正，但 one-std 稳健性失败。 |
| search_accounting_status | diagnostic_train_only_not_confirmatory | 本次只是 post-13C train-only 诊断，不是确认性 OOS。 |

关键约束是 `validation_used_in_13e=false` 和 `robustness_used_in_13e=false`。即使某些 train-fold 指标看起来有 lift，也只能解释为训练期内的容量诊断，不能升级成 out-of-sample trading evidence。

## 3. 数据重建与 Lineage

| audit item | value |
|---|---:|
| row_count | 6,232 |
| unique_row_id_count | 6,232 |
| non_train_row_count | 0 |
| required_column_missing_count | 0 |
| event_span_unavailable_n | 0 |
| instrument_reference_date_duplicate_n | 0 |
| min_train_event_n | 1,000 |
| report_text_used_as_row_truth | false |
| bucket_refit_in_13e | false |
| validation_rows_used | false |
| robustness_rows_used | false |
| row rebuild status | pass |

上游 13C lineage audit 共 19 项，全部通过。最重要的两个硬约束是：

| upstream artifact check | observed | expected | status |
|---|---:|---:|---|
| morphology_residual_panel.manifest_schema_hash | 6c980cae1dcf516620b03f74d194cba11128f86f465e294ce3e9b02fdc242a23 | 6c980cae1dcf516620b03f74d194cba11128f86f465e294ce3e9b02fdc242a23 | pass |
| morphology_residual_panel.manifest_row_count | 431,239 | 431,239 | pass |

因此，13E 当前失败不是由于输入漂移、schema 漂移、report truth 泄漏或 row reconstruction 问题导致，而是模型比较本身没有满足增量门槛。

## 4. Search Accounting

| item | value |
|---|---:|
| posthoc_after_13c_report | true |
| feature_set_n | 2 |
| model_family_n | 2 |
| target_n | 1 |
| fold_n | 5 |
| effective_search_space_n | 4 |
| hyperparameter_search_used | false |
| fold_internal_tuning_used | false |
| early_stopping_used | false |
| oos_used_for_selection | false |

这里没有做 hyperparameter search，也没有把 OOS 用于选择模型；但因为 13E 是 13C 之后的 post-hoc train-only diagnostic，所以它天然不具备确认性地位。这个 search accounting 的结果支持一个保守读法：**本诊断可以用于判断“是否值得开新方向”，不能用于直接部署或授权下一阶段策略**。

## 5. Sample Uniqueness 与 Concurrency

所有 fold 都通过 exact-t1 uniqueness gate。事件之间存在重叠，但不是严重到让 K-fold 诊断失效的程度；平均 uniqueness 大约在 0.40 附近，对应平均 concurrency 约 3.9-4.0。

| fold | event_n | purged | embargoed | effective_train | train_mean_uniqueness | train_p10_uniqueness | train_mean_concurrency | train_p95_concurrency | test_mean_uniqueness |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2,091 | 30 | 129 | 3,982 | 0.4150 | 0.1667 | 3.8176 | 8.0 | 0.3814 |
| 1 | 1,656 | 115 | 795 | 3,666 | 0.3982 | 0.1588 | 3.9860 | 9.0 | 0.4010 |
| 2 | 1,195 | 63 | 251 | 4,723 | 0.3965 | 0.1638 | 3.9331 | 8.0 | 0.4153 |
| 3 | 504 | 34 | 440 | 5,254 | 0.4014 | 0.1631 | 3.9308 | 8.0 | 0.5208 |
| 4 | 786 | 5 | 66 | 5,375 | 0.3995 | 0.1620 | 3.9676 | 9.0 | 0.4178 |

这个表给出的核心判断是：**样本重叠需要被计入不确定性，但它不是本次 stop 的主因**。真正的主因是非线性模型在主 feature set 上没有产生稳定增量。

## 6. 主比较：Augmented Feature Set

预注册主比较应该看 augmented feature set，因为它代表 13C 已经确认并输出的 morphology/residual 信息集。在这个口径下，HGB 没有战胜 logistic。

| metric | logistic_mean | hgb_mean | hgb_minus_logistic | hgb_std | gate readout |
|---|---:|---:|---:|---:|---|
| AUC | 0.5510 | 0.5480 | -0.0030 | 0.0462 | fail: HGB 低于 logistic，且未达到 +0.005 AUC 门槛 |
| logloss | 0.6986 | 0.7342 | +0.0356 | 0.1197 | fail: HGB 概率质量更差 |
| top20% uplift | 0.0360 | 0.0370 | +0.0010 | 0.0460 | fail: 均值微弱，fold 方向不稳定 |
| utility 0bps | 0.0155 | 0.0165 | +0.0009 | 0.0136 | weak positive mean only |
| utility 50bps | 0.0105 | 0.0115 | +0.0009 | 0.0136 | fail: HGB mean - std = -0.0022 |
| utility 100bps | 0.0055 | 0.0065 | +0.0009 | 0.0136 | weak positive mean only |

最关键的失败项是 AUC：`0.5480 - 0.5510 = -0.0030`。这说明 augmented feature set 下，非线性模型并没有更好地区分 winner / non-winner。utility 的均值改善只有 `+0.0009`，且 50bps 口径下 `mean - std < 0`，不能作为仓位调整依据。

## 7. Augmented Fold 细节

| fold | logistic_auc | hgb_auc | auc_delta | logistic_uplift | hgb_uplift | uplift_delta | logistic_utility_50bps | hgb_utility_50bps | utility_delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.5333 | 0.5403 | +0.0071 | 0.0088 | 0.0136 | +0.0048 | 0.0088 | 0.0117 | +0.0029 |
| 1 | 0.6124 | 0.6119 | -0.0005 | 0.1010 | 0.0708 | -0.0302 | 0.0098 | 0.0088 | -0.0010 |
| 2 | 0.4937 | 0.4835 | -0.0103 | -0.0134 | -0.0134 | +0.0000 | 0.0148 | 0.0143 | -0.0005 |
| 3 | 0.5587 | 0.5425 | -0.0162 | 0.0550 | 0.0154 | -0.0396 | 0.0004 | -0.0078 | -0.0083 |
| 4 | 0.5569 | 0.5617 | +0.0048 | 0.0285 | 0.0985 | +0.0701 | 0.0189 | 0.0303 | +0.0114 |

Fold 级别的 pattern 比均值更重要：

- AUC 只有 2/5 个 fold 为正，平均差为负。
- uplift 严格为正的 fold 只有 2/5；fold 2 是 0，fold 1 和 fold 3 明显为负。
- 50bps utility 也是 2/5 个 fold 为正；fold 4 很强，但 fold 3 明显拖累。

这不是一个“稳定弱 edge”，而是一个**局部 fold 正、整体不稳、主 ranking 指标失败**的容量读数。

## 8. Baseline Feature Set 对照

baseline feature set 下，HGB 看起来有更明显的正向信号：

| metric | logistic_mean | hgb_mean | hgb_minus_logistic | interpretation |
|---|---:|---:|---:|---|
| AUC | 0.5323 | 0.5397 | +0.0074 | HGB 在 baseline 上有 AUC 改善。 |
| logloss | 0.6944 | 0.7541 | +0.0596 | 但概率质量明显变差。 |
| top20% uplift | -0.0057 | 0.0236 | +0.0294 | HGB 能从弱 baseline 中挖出部分排序 lift。 |
| utility 50bps | 0.0089 | 0.0095 | +0.0006 | 经济改善很小。 |

这个对照非常关键：**非线性模型不是完全学不到东西，而是它学到的东西在加入 augmented morphology/residual 信息后不再是增量信息**。换句话说，baseline HGB 的 lift 更可能来自对简单 morphology、state 或 residual proxy 的非线性组合；当这些信息已经以 augmented 特征形式交给 logistic 后，HGB 的额外容量没有继续贡献。

## 9. Findings

1. **13E 的失败是模型容量失败，不是数据完整性失败。** 输入、lineage、row rebuild、purged CV 和 exact-t1 uniqueness 都通过；stop 发生在 nonlinear improvement gates。

2. **augmented logistic 已经吸收了主要可用信息。** baseline HGB 的 AUC delta 为 `+0.0074`，但 augmented HGB 的 AUC delta 变成 `-0.0030`。这说明“非线性胜出”的表象依赖较弱的 baseline，而不是对 13C 完整特征集的真实增量。

3. **utility lift 不足以转化为风险预算信号。** augmented HGB 的 50bps utility 均值比 logistic 高 `+0.0009`，但 fold 方向只有 2/5 为正，且 HGB 的 `mean - std = -0.0022`。这类信号不适合直接做加仓/减仓规则。

4. **logloss 对 HGB 不利，提示概率校准风险。** augmented 口径下 HGB logloss 为 `0.7342`，logistic 为 `0.6986`。即使某些 top bucket 有 lift，HGB 输出概率也更不适合作为 meta-labeling sizing probability。

5. **样本 uniqueness 可接受，但会压低置信度。** train mean uniqueness 约 `0.3965-0.4150`，p10 约 `0.1588-0.1667`，平均 concurrency 约 `3.82-3.99`。这支持 purge/embargo 的必要性，也意味着不能把 6,232 rows 当成完全独立事件。

## 10. Insight

从 AFML 的角度，本诊断把问题拆成了两层：

- 第一层是 **event 是否有 lift**。从 baseline HGB 和部分 fold 的 top-bucket utility 看，event 并非完全无信息。
- 第二层是 **这个 lift 是否能变成可交易的 winner-entry 或 meta-labeling edge**。13E 的答案是否定的，因为在 augmented feature set、purged K-fold 和 one-std utility 约束下，非线性增量不稳定。

因此，当前最合理的解释是：`repair_range_participation_core_30` 这类 event 更像是一个 **conditional participation context**，而不是一个可以独立驱动 winner entry 的信号。它可以帮助描述“某些市场状态下更容易出现局部 lift”，但还不能回答“发生 event 后应该系统性加仓多少”。

如果后续继续研究，方向不应是直接扩大模型复杂度或进入 sequence mining，而应先解决更基础的问题：

- 是否存在更清晰的 target，使 event lift 与经济 utility 对齐，而不是只追 winner classification。
- 是否需要把 event 当作 participation filter，而不是 winner predictor。
- 是否需要先做 calibration / probability quality 诊断，因为当前 HGB logloss 明显差于 logistic。
- 是否应该用完全独立的 confirmatory OOS 来检验 event-conditioned risk budget，而不是从 13E train-fold 直接授权。

## 11. Final Readout

13E 不支持“非线性 winner 训练已经可行”的结论。它支持的更保守结论是：

> 当前 event 有局部 lift，但没有形成稳定、可确认、可用于 meta-labeling 或 bet sizing 的非线性增量 edge。

所以 13E 的正确使用方式是作为 stop diagnostic：记录 baseline-HGB 曾经出现的 lift 迹象，同时明确它在 augmented 主比较中失效。后续如果要继续做 event-conditioned 风险预算，需要另开一个确认性 requirement，并且不能把 13E 的 train-only 结果当成授权依据。
