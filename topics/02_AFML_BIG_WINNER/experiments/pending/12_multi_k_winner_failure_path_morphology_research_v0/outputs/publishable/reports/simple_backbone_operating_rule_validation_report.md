# 12A7b Direction C 简单骨干操作规则验证报告

## 结论

最终状态为 `12A7b_simple_backbone_supported_low_capacity_not_supported`。

这意味着：在 C0 risk_on、stage-1 可评估事件内，一个极简的 train-frozen 单特征规则已经可以稳定降低 20 日内 -10% fast-fail 风险；但进一步加入低容量三特征单调加法模型，并没有在 robustness 上以足够幅度和置信度击败这个简单规则。因此本轮支持的是“简单骨干操作规则”，不是“更复杂低容量模型”。

| 项目 | 数值 |
|---|---:|
| input gate | `pass` |
| PIT gate | `pass` |
| phase-1 simple backbone gate | `pass` |
| phase-2 enabled | `true` |
| phase-2 policy | `mandatory_after_phase_1_pass` |
| selected primary tuple | `volatility_20d` |
| selected X | 0.30 |
| robustness selected_n | 1476 |
| robustness budget_total | 31.68% |
| robustness budget_abs_delta_rank_evaluable_vs_X | 1.80pp |
| robustness fast_fail_rate | 14.30% |
| robustness delta_vs_random_p50 | -8.20pp |
| robustness delta_vs_random_p50 95% CI | [-9.96pp, -6.37pp] |
| robustness delta_vs_complex_model | -0.47pp |
| robustness delta_vs_complex_model 95% CI | [-2.12pp, 1.05pp] |
| complex comparator status | `numerical_near_miss_diagnostic` |
| selected low-capacity rule | `lowcap_d233a7af2275e0c1` |
| low-capacity delta_vs_simple_backbone, robustness | -0.63pp |
| low-capacity delta_vs_simple_backbone 95% CI, robustness | [-1.72pp, 0.44pp] |
| gate failure reasons | `phase2_delta_vs_simple_backbone_not_supported;phase2_simple_backbone_ci_crosses_zero` |
| recommended follow-up | `simple_backbone_policy_replay_or_12A8_calibration_scope_review` |

## 数据口径与门禁

本报告只覆盖 C0 risk_on 且 stage-1 evaluable 的事件，不代表所有 regime 或所有 entry 形态。当前输入审计共 25 个 artifact，`read_status = pass` 且 `schema_status = pass` 全部通过。

| split | raw_event_n | included_event_n | excluded_event_n | source_arm_is_c0_rate | risk_on_rate | stage_1_evaluable_rate |
|---|---:|---:|---:|---:|---:|---:|
| all | 15113 | 15113 | 0 | 100.00% | 100.00% | 100.00% |
| train | 8303 | 8303 | 0 | 100.00% | 100.00% | 100.00% |
| validation | 2151 | 2151 | 0 | 100.00% | 100.00% | 100.00% |
| robustness | 4659 | 4659 | 0 | 100.00% | 100.00% | 100.00% |

板块分布上，`main_board` 为 11998 个事件，`chinext` 为 3115 个事件。年份覆盖 2018-2025，其中 2020 为 3083 个事件、2021 为 2687 个事件、2025 为 2620 个事件。该覆盖足以支撑 trailing rank 的跨期验证，但也意味着 validation/robustness 的局部月份会出现预算和样本量波动。

## Phase-1: 简单骨干规则

训练集冻结选择为 `volatility_20d`、ascending、`X = 0.30`。选择逻辑只使用 train split：先过最小样本和 random uplift 硬门，再按最低 train fast-fail rate、较大 selected_n、feature name、X 排序。最终选中的 train fast-fail rate 为 21.80%，显著低于 train base 41.86%，也低于 matched random p50 33.44%。

| feature | X | train selected_n | train fast_fail | train random_p50 | train delta_vs_random_p50 | CI high |
|---|---:|---:|---:|---:|---:|---:|
| volatility_20d | 0.30 | 2023 | 21.80% | 33.44% | -11.64pp | -9.89pp |
| volatility_60d | 0.30 | 1966 | 22.63% | 34.31% | -11.67pp | -9.82pp |
| distance_to_60d_low | 0.30 | 2358 | 24.00% | 34.92% | -10.92pp | -9.10pp |
| rebound_from_60d_low | 0.30 | 2358 | 24.00% | 34.92% | -10.92pp | -9.10pp |
| volatility_20d | 0.40 | 2774 | 24.41% | 33.96% | -9.55pp | -7.89pp |
| max_drawdown_60d | 0.30 | 2729 | 45.91% | 35.78% | +10.13pp | +11.95pp |

核心发现是：最低波动率类特征在 train 中形成稳定的 fast-fail 防守信号，而 `max_drawdown_60d` 的同向低分选择反而显著恶化 fast-fail。这说明“低风险骨干”不是任意低形态变量都有效，而是主要由短期/中期波动率压制承载。

## Phase-1 transport 结果

| split | selected_n | budget_total | budget_rank_evaluable | selected fast_fail | base fast_fail | random_p50 | delta_vs_random_p50 | 95% CI | complex matched rate | delta_vs_complex |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2023 | 24.36% | 25.13% | 21.80% | 41.86% | 33.44% | -11.64pp | [-13.45pp, -9.89pp] | 21.70% | +0.10pp |
| validation | 957 | 44.49% | 44.87% | 19.64% | 33.98% | 28.79% | -9.14pp | [-11.81pp, -6.58pp] | 21.11% | -1.46pp |
| robustness | 1476 | 31.68% | 31.80% | 14.30% | 30.59% | 22.49% | -8.20pp | [-9.96pp, -6.37pp] | 14.77% | -0.47pp |
| all | 4456 | 29.48% | 30.06% | 18.85% | 37.27% | 28.88% | -10.03pp | [-11.20pp, -8.90pp] | 19.28% | -0.43pp |

Phase-1 支持成立的关键不是 selected fast-fail 绝对低，而是 robustness 上同时满足三件事：

1. 预算漂移可控：robustness 的 rank-evaluable budget 为 31.80%，相对 X=30% 只偏离 1.80pp。
2. 相对 random 有统计优势：delta_vs_random_p50 为 -8.20pp，CI high 仍为 -6.37pp。
3. rank 覆盖风险低：robustness rank_not_evaluable_rate 为 0.36%，没有 warm-up 覆盖问题。

Validation 的作用应解读为 stress readout，而不是选择依据。validation 的 selected budget_total 为 44.49%，rank-evaluable budget 为 44.87%，相对 X=30% 偏离 14.87pp，确实暴露了前序 12A6c/12A7 中讨论过的预算漂移压力。但即使在这个压力区间，validation fast-fail 仍为 19.64%，低于 base 33.98% 和 random p50 28.79%。因此 validation 不推翻方向，只提示实际落地时需要预算校准。

## 与复杂模型的 matched comparator

复杂模型 comparator 在 common denominator 内按 split、board_bucket、calendar_month 匹配 selected_n。复杂模型逐行 score 来源为 `trailing_rank_score_matrix.parquet`，当前比较状态为 `pass_near_miss` / `numerical_near_miss_diagnostic`。

| split | common_denominator_n | candidate selected_n | complex selected_n | simple rate | complex rate | delta simple - complex | 95% CI | status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| train | 8050 | 2023 | 2023 | 21.80% | 21.70% | +0.10pp | [-1.45pp, 1.54pp] | `numerical_near_miss_diagnostic` |
| validation | 2133 | 957 | 957 | 19.64% | 21.11% | -1.46pp | [-3.57pp, 0.62pp] | `numerical_near_miss_diagnostic` |
| robustness | 4642 | 1476 | 1476 | 14.30% | 14.77% | -0.47pp | [-2.12pp, 1.05pp] | `numerical_near_miss_diagnostic` |
| all | 14825 | 4456 | 4456 | 18.85% | 19.28% | -0.43pp | [-1.42pp, 0.54pp] | `numerical_near_miss_diagnostic` |

这里的洞察是：复杂模型没有提供稳健、可证明的增益。简单规则在 robustness 上略好于复杂模型 0.47pp，但 CI 跨 0；train 上甚至略差 0.10pp，同样完全不显著。更合理的解释是，复杂模型的 stage-1 防守能力大部分已经被 `volatility_20d` 这个简单骨干吸收。复杂模型可以作为诊断参考，但不能作为提升复杂度的证据。

## Phase-2: 低容量单调加法模型

按照需求，phase-1 pass 后 phase-2 必跑。训练集中选中的低容量规则为：

```text
rule_id = lowcap_d233a7af2275e0c1
feature_list = volatility_20d | volatility_60d | distance_to_60d_low
weight_json = [0.25, 0.5, 0.25]
feature_count = 3
stage1_budget_X = 0.30
```

候选空间共 55 个低容量单调规则，其中 15 个两特征、40 个三特征，全部满足单调加法约束。train 上最优规则的 fast-fail rate 为 20.73%，比 simple matched backbone 低 1.32pp，且 train CI 为 [-2.44pp, -0.26pp]，看起来有训练内增益。

| split | selected_n | budget_total | fast_fail | random_p50 | delta_vs_random_p50 | simple matched rate | delta_vs_simple | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2190 | 26.38% | 20.73% | 33.24% | -12.51pp | 22.05% | -1.32pp | [-2.44pp, -0.26pp] |
| validation | 990 | 46.03% | 20.91% | 30.35% | -9.44pp | 21.52% | -0.61pp | [-2.07pp, 0.72pp] |
| robustness | 1423 | 30.54% | 13.84% | 21.96% | -8.12pp | 14.48% | -0.63pp | [-1.72pp, 0.44pp] |
| all | 4603 | 30.46% | 18.64% | 29.20% | -10.56pp | 19.60% | -0.96pp | [-1.66pp, -0.27pp] |

Phase-2 不支持的原因很明确：robustness 上 low-capacity 相对 simple backbone 只改善 0.63pp，未达到 `delta_vs_simple_backbone <= -1.00pp` 的门槛，并且 CI high 为 +0.44pp，跨 0。也就是说，复杂度在 train/all 上有轻微优势，但在真正的 robustness 判断里没有足够稳定的边际收益。

这给出的研究含义是：在 stage-1 fast-fail 防守任务中，增加 `volatility_60d` 和 `distance_to_60d_low` 可以微调排序，但没有改变主导结构。最有价值的信号仍是“低短期波动率”这个骨干，而不是三特征模型本身。

## 稳定性诊断

稳定性审计共 102 个 slice。按状态计数：

| slice_type | pass | insufficient_n | fail |
|---|---:|---:|---:|
| split | 3 | 0 | 0 |
| calendar_year | 7 | 1 | 0 |
| board_bucket | 6 | 0 | 0 |
| primary_family_id | 13 | 8 | 0 |
| calendar_month | 15 | 48 | 1 |

唯一 fail 出现在 train 的 2020-01 月份：selected_n=115，selected_fast_fail_rate=80.87%，base=74.75%，random_p50=74.78%。这是训练早期局部月份的反向点，不在 robustness。robustness 中所有 selected_n >= 100 的 slice 均为 pass；非 pass 的 robustness slice 都是 insufficient_n。

Robustness 关键 slice：

| slice | selected_n | selected fast_fail | base fast_fail | random_p50 | delta_vs_random_p50 | status |
|---|---:|---:|---:|---:|---:|---|
| robustness overall | 1476 | 14.30% | 30.59% | 30.62% | -16.33pp | pass |
| 2024 | 418 | 20.10% | 35.65% | 35.53% | -15.43pp | pass |
| 2025 | 1058 | 12.00% | 26.64% | 26.70% | -14.70pp | pass |
| chinext | 305 | 24.26% | 45.00% | 44.59% | -20.33pp | pass |
| main_board | 1171 | 11.70% | 26.44% | 26.39% | -14.69pp | pass |
| B1 | 168 | 15.48% | 34.11% | 33.93% | -18.45pp | pass |
| B2 | 341 | 16.42% | 28.20% | 28.45% | -12.02pp | pass |
| B3 | 145 | 13.10% | 20.67% | 20.00% | -6.90pp | pass |
| B5 | 599 | 11.52% | 30.25% | 30.47% | -18.95pp | pass |
| B8 | 118 | 16.95% | 29.08% | 28.81% | -11.86pp | pass |

稳定性结论：robustness 没有发现 sign inversion 或 slope collapse。样本量不足的 B4、B6 以及若干月份不能用于强判断，但它们没有构成对主结论的反证。

## Stage-2 诊断

Stage-2 是 diagnostic-only，不允许升级或改变 12A7b decision。它的价值是观察 stage-1 防守过滤后，是否仍保留 continuation 机会。

Robustness stage-2 结果：

| readout | X | selected_n | continuation rate | base continuation | random_p50 | complex matched rate | delta simple - complex | 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ground_truth_no_fast_fail_survivor | NA | 3234 | 13.45% | 13.45% | NA | NA | NA | NA |
| stage1_simple_backbone_chained_survivor | NA | 1265 | 9.33% | 13.45% | NA | NA | NA | NA |
| matched_random_same_budget | 0.30 | 1093 | 12.58% | 13.45% | 12.58% | NA | NA | NA |
| simple_stage2_vs_complex_stage2 | 0.30 | 1093 | 17.57% | 13.45% | 12.58% | 18.21% | -0.64pp | [-2.46pp, 1.01pp] |
| matched_random_same_budget | 0.50 | 1735 | 12.07% | 13.45% | 12.07% | NA | NA | NA |
| simple_stage2_vs_complex_stage2 | 0.50 | 1735 | 15.97% | 13.45% | 12.07% | 16.66% | -0.69pp | [-1.77pp, 0.42pp] |

最重要的诊断洞察是：stage-1 simple backbone 作为防守规则，会筛掉一部分 continuation 机会。robustness 中所有 no-fast-fail survivor 的 continuation rate 为 13.45%，但经过 stage-1 simple backbone 链式保留下来的 survivor continuation rate 只有 9.33%。这并不否定 stage-1 的 fast-fail 防守价值，而是说明 stage-1 防守和 stage-2 进攻延续不是同一个目标。后续如果要追求 winner continuation，需要在 stage-2 单独做 continuation 校准，而不是把 stage-1 fast-fail filter 误当作完整交易策略。

Stage-2 的 `distance_to_120d_low desc` 对 continuation 有诊断价值：robustness X=0.30 时 continuation 为 17.57%，高于 base 13.45% 和 matched random 12.58%；X=0.50 时 continuation 为 15.97%，也高于 base 和 random。但它相对 complex stage-2 的 paired delta CI 仍跨 0，因此只能建议后续 requirement 继续研究，不能改变 12A7b 的支持状态。

## Findings

1. `volatility_20d` 是可运输的 stage-1 fast-fail 防守骨干。它在 train、validation、robustness 三个 split 中都低于 base 和 matched random，robustness delta_vs_random_p50 为 -8.20pp，CI high 为 -6.37pp。

2. validation 的主要问题是预算漂移，不是方向反转。validation selected_budget_total 为 44.49%，rank-evaluable budget 为 44.87%，明显高于 X=30%；但 fast-fail rate 仍从 base 33.98% 降到 19.64%。这说明规则方向有效，但落地需要预算校准和 policy replay。

3. 复杂模型没有提供稳定增益。robustness 中 simple vs complex 的 delta 为 -0.47pp，CI 为 [-2.12pp, 1.05pp]，属于 near-miss / parity 诊断。当前证据更支持“复杂模型的大部分 stage-1 信息可由一个简单波动率骨干解释”。

4. 低容量三特征模型不能升级结论。它在 train 上相对 simple backbone 改善 1.32pp，但 robustness 只改善 0.63pp，且 CI high 为 +0.44pp。复杂度增加没有换来足够稳健的 out-of-train 边际收益。

5. Stage-2 暗示目标函数需要分离。stage-1 防守规则降低 fast-fail，但 chained survivor 的 continuation rate 低于 survivor base；stage-2 continuation 需要独立建模，而不是继续堆叠 stage-1 防守变量。

## Insight

AFML 角度下，本轮结果更像是一个“操作规则可用性”结论，而不是一个“预测模型胜利”结论。`volatility_20d` 的价值在于提供了一个低容量、PIT、train-frozen、预算可审计的 fast-fail rejector。它把 C0 risk_on 中最容易快速跌穿 -10% 的路径剔除掉，并且这种剔除在 robustness 中没有明显 regime 反转。

但这个规则不应该被直接解释为买入 alpha。它保护的是 downside path，不保证后续 big-winner continuation。Stage-2 诊断显示，防守筛选后留下的 survivor continuation 反而偏低；这符合一个常见结构：低波动防守能减少坏路径，但也可能牺牲部分高动能、高弹性的右尾路径。因此下一步不应简单增加 stage-1 复杂度，而应把 stage-1 rejector 与 stage-2 continuation selector 分开校准。

推荐下一步是 `simple_backbone_policy_replay_or_12A8_calibration_scope_review`：先把 `volatility_20d, X=0.30` 当作可审计的 simple backbone policy replay 对象，重点处理 validation 暴露的预算漂移；再在独立 requirement 中研究 stage-2 continuation selector 是否能在不重新引入 fast-fail 风险的前提下恢复右尾参与度。

## Scope 与 caveat

Validation is readout-only because prior 12A6c / 12A7 evidence shows a pathological low-base-rate budget-drift interval.

No feature, orientation, X, or model capacity was chosen using validation or robustness.

If phase-1 simple backbone passes, phase-2 low-capacity monotone validation was mandatory and could not be skipped by config.

The conclusion applies only to C0 risk_on events, not all regimes.
