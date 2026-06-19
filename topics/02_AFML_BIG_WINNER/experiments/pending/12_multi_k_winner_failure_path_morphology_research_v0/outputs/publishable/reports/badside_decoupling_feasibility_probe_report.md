# 12A5A Bad-side Decoupling Feasibility Probe 决策报告

## 结论

最终状态：`12A5A_no_decoupling_stop_keep_feature_source`。

一句话判断：12A5A 找到了可以降低 bad-side 的 rejector 工作点，但没有证明 clean winner 与 bad-side 在当前 PIT feature 空间稳定可分；并且主分析发生了 `shallow_tree_top20 -> density_only_top20` fallback，因此不能进入 12A5B 完整 morphology bad-side reduction modeling。

建议：停止把 state-change 当作独立 timing signal 继续扩展；保留 C0/state-change 作为低密度、PIT 可执行的 feature source。若要继续研究，只应作为新特征空间的前置诊断，而不是在当前 12A4 feature bank 内继续调 rejector。

## 输入与审计

12A5A 使用 12A4 已物化的 risk_on C0 universe、target 和 PIT feature matrix：

| audit | value |
| --- | ---: |
| primary C0 risk_on joined rows | 15,113 |
| unique `meta_event_id` | 15,113 |
| allowed PIT feature columns | 87 |
| missing target rows | 0 |
| missing feature rows | 0 |
| split mismatch | 0 |
| event-feature join gate | pass |
| feature dictionary parity gate | pass |
| label completeness on selected pools | 100% |

12A4 robustness baseline 同口径如下：

| source | event_n | inside_n | precision | bad-side | episode recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 state-change | 4,659 | 370 | 7.94% | 28.12% | 92.82% |
| R-core | 9,730 | 794 | 8.16% | 32.17% | 88.40% |

这说明 12A5A 的目标不是继续提高 raw recall，而是在 12A4 high-uplift bucket 内验证 bad-side 能否被二次过滤。

## Bucket 重建

12A5A 按 12A4 官方 top20 bucket 口径在本阶段重建 selected pool。deterministic pools 全部通过 event/inside/published rate cross-check；refit pools 因 feature hash 或 membership cross-check 未通过，只能 diagnostic，不进入 decision gate。

| pool | status | event_n | inside_n | precision | bad-side | note |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| density_only_top20 | ok | 1,139 | 126 | 11.06% | 31.17% | decision fallback pool |
| freshness_only_top20 | ok | 1,012 | 104 | 10.28% | 28.26% | low bad-side comparator |
| r_core_interaction_top20 | ok | 989 | 101 | 10.21% | 30.64% | R-core interaction comparator |
| shallow_tree_top20 | refit hash mismatch | 1,535 | 182 | 11.86% | 40.59% | hard bucket diagnostic |
| lightgbm_top20 | refit mismatch | 1,623 | 192 | 11.83% | 37.34% | challenger diagnostic only |

`shallow_tree_top20` 的 event_n/inside_n/precision/bad-side 与 12A4 published readout 一致，但 feature-list hash cross-check 未通过，因此按需求 fail-closed，不能作为 primary decision pool。主分析 fallback 到更干净的 `density_only_top20`，同时保留 shallow hard bucket 的诊断结论。

## Bad-side 分解

所有 robustness selected pools 的 bad-side 都不是 fast-fail-only 主导，而是 fast-fail 与 false-repair overlap 主导：

| pool | bad-side | fast-fail only | false-repair only | overlap | dominant |
| --- | ---: | ---: | ---: | ---: | --- |
| density_only_top20 | 31.17% | 11.83% | 24.79% | 63.38% | overlap |
| freshness_only_top20 | 28.26% | 12.94% | 29.02% | 58.04% | overlap |
| r_core_interaction_top20 | 30.64% | 13.20% | 26.73% | 60.07% | overlap |
| shallow_tree_top20 | 40.59% | 13.64% | 25.84% | 60.51% | overlap |
| lightgbm_top20 | 37.34% | 10.89% | 26.40% | 62.71% | overlap |

这个结果有两层含义：

1. bad-side 不是简单的“买太早导致 fast-fail”问题，理论上 morphology filter 有着力点，因为 overlap/false-repair 成分很高。
2. 但 high-precision 模型桶里 overlap 也一起被放大，尤其 shallow tree bad-side 达到 40.59%。这说明当前特征空间把“更像 winner 的强修复/强波动形态”和“更容易假修复后再坏掉的形态”混在了一起。

## Separability

主决策池 `density_only_top20` 的 clean winner 正样本数为 49，超过 30 的薄样本 guard，但低容量可分性未通过：

| positive class | best method | positive_n | bad_side_n | AUC | CI low | CI high |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| clean_winner_event | shallow_tree_depth_2 | 49 | 355 | 0.5682 | 0.4948 | 0.6372 |
| clean_capture_event diagnostic | shallow_tree_depth_2 | 86 | 355 | 0.5360 | 0.4902 | 0.5789 |

supported/partial gate 要求 clean winner separability 的 best AUC >= 0.60 且 CI low >= 0.55。当前 AUC 点估计不足，CI 下界也低于门槛，因此 `separable = false`。

主决策池最强单变量均来自波动率/低位距离/低位反弹：

| feature | group | AUC | abs(AUC-0.5) |
| --- | --- | ---: | ---: |
| distance_to_60d_low | pre_event_path | 0.2394 | 0.2606 |
| rebound_from_60d_low | event_native | 0.2394 | 0.2606 |
| volatility_60d | pre_event_path | 0.2436 | 0.2564 |
| distance_to_120d_low | pre_event_path | 0.2616 | 0.2384 |
| volatility_20d | pre_event_path | 0.2715 | 0.2285 |

这些变量有读数，但方向上更像“低波动、低位置、低反弹幅度”在筛 bad-side。它们不是新的 morphology alpha，更像风险强度/波动状态的弱代理。clean-capture diagnostic 也未过，说明即使不要求 120d winner，只要求“低到高捕获且不 bad-side”，可分性也没有明显改善。

## Shallow Hard Bucket 诊断

需求要求即使 fallback，也必须回答 40.6% bad-side 的 `shallow_tree_top20` 难 bucket 是否可解耦。结论是不支持。

`shallow_tree_top20` robustness：

| metric | value |
| --- | ---: |
| event_n | 1,535 |
| inside_n | 182 |
| precision | 11.86% |
| bad-side | 40.59% |
| clean_winner_n | 62 |
| dominant bad-side component | overlap |
| overlap share of bad-side | 60.51% |
| best low-capacity AUC | 0.5157 |
| AUC CI low | 0.4362 |

shallow hard bucket 的 bad-side 明显比 density bucket 更高，但 clean winner vs bad-side 的 AUC 接近随机。最强单变量为 volatility/event position/high-distance 一类变量：

| feature | group | AUC | abs(AUC-0.5) |
| --- | --- | ---: | ---: |
| volatility_20d | pre_event_path | 0.3095 | 0.1905 |
| volatility_60d | pre_event_path | 0.3217 | 0.1783 |
| distance_to_60d_high | pre_event_path | 0.6524 | 0.1524 |
| event_t0_pos | event_native | 0.6521 | 0.1521 |
| evaluated_member_count | event_native | 0.3545 | 0.1455 |

这说明 40.6% hard bucket 的 bad-side 并不是“已有 PIT feature 可以轻松拆开”的问题。即使可用 scorecard rejector 在 diagnostic readout 中把 bad-side 从 40.59% 降到 32.03%，retained precision 只有 12.38%，相对 shallow pool 仅 +0.52pp；核心 separability AUC 仍不过关。因此不能把这个结果解释为 morphology 解耦已成立。

## Rejector 工作点

12A5A 的 rejector 严格用 train internal CV 选择 reject_fraction，robustness 只读出。主决策池 `density_only_top20` 的最佳 allowed workpoint：

| item | value |
| --- | ---: |
| rejector | logistic_regression_l2 |
| label policy | bad_side_vs_clean_winner |
| reject score direction | higher_is_worse |
| chosen reject_fraction | 40% |
| train-CV retained event_n | 1,090 |
| train-CV retained precision | 9.54% |
| robustness retained event_n | 683 |
| robustness retained precision | 12.88% |
| robustness retained bad-side | 25.62% |
| bad-side reduction vs pool | 5.55pp |
| precision delta vs pool | +1.82pp |
| retained episode recall | 36.46% |

表面上，这个 workpoint 很诱人：它同时提高 precision、降低 bad-side，并保住超过 35% 的 episode recall。但它仍不能触发 supported 或 partial，因为：

1. primary pool 是 fallback 后的 density bucket，不是 40.6% bad-side 的 shallow hard bucket，需求规定 fallback 不允许 supported。
2. separability gate 未过。当前工作点可能是薄样本和弱风险代理共同产生的 readout，不能证明 clean winner 与 bad-side 在特征空间中稳定可分。
3. train-CV 选择的 retained precision 为 9.54%，只略高于 guard，说明阈值选择本身并不强。

其他 bucket 的最佳 workpoint 也支持同一结论：

| pool | best allowed rejector | retained precision | retained bad-side | bad-side reduction | retained recall |
| --- | --- | ---: | ---: | ---: | ---: |
| density_only_top20 | logistic_l2 | 12.88% | 25.62% | 5.55pp | 36.46% |
| freshness_only_top20 | logistic_l2 | 12.36% | 20.76% | 7.50pp | 31.49% |
| r_core_interaction_top20 | scorecard | 11.30% | 21.92% | 8.71pp | 29.83% |
| shallow_tree_top20 | scorecard | 12.38% | 32.03% | 8.56pp | 45.86% |
| lightgbm_top20 | scorecard | 12.23% | 29.80% | 7.53pp | 46.41% |

降低 bad-side 是做得到的，但它主要来自剔除高风险尾部；没有足够证据说明剔除的是“bad-side 可分形态”，而不是用低波动/低位置代理同时重排 winner 与 bad-side。

## Findings

1. **bad-side 的主问题不是 fast-fail-only，而是 false-repair/fast-fail overlap。**
   这给 morphology 提供了理论入口，但并不代表当前特征已经能拆开它。

2. **高 precision bucket 与高 bad-side 仍然耦合。**
   density-only 是最干净的 high-precision 简单方案，precision 11.06%、bad-side 31.17%；shallow tree 把 precision 推到 11.86%，但 bad-side 同时推到 40.59%。这延续了 12A4 的核心观察。

3. **现有 PIT feature 能识别风险强度，但不能稳定识别 clean winner。**
   单变量最强的是 volatility、distance_to_low/high、event_t0_pos；它们解释的是状态强弱/位置，而不是“真修复 vs 假修复”的独立形态结构。

4. **rejector 有局部工程价值，但不足以成为 timing 模型。**
   fallback density pool 上 logistic_l2 的 robustness retained precision 达 12.88%、bad-side 25.62%，但 separability gate 不过，且主桶 fallback 后问题难度降低，不能支持 12A5B。

5. **shallow hard bucket 的诊断最关键：不支持解耦。**
   40.59% bad-side 的 bucket 是 12A5A 原本最想拯救的对象，但 best AUC 只有 0.5157、CI low 0.4362。这里没有看到足够强的 morphology separability。

## Insight

12A5A 的结果更像是一个“风险尾部剔除可行，但 clean-winner 识别不可行”的结论。

这和 12A3/12A4 的主线一致：state-change 事件很适合作为低重复、早触发、PIT 可执行的特征源；但一旦把它提升为择时信号，就会遇到 base-rate 与 bad-side 耦合。当前 feature bank 可以把事件从 8% base precision 推到 10%-12% 的 top bucket，也可以用 rejector 把 bad-side 压低几个百分点；但它没有证明“保留的那部分就是未来 winner，而剔除的那部分就是 bad-side”。

如果继续研究，下一步不应直接做 12A5B 完整 morphology modeling。更合理的路线是先新增能描述“修复质量”的外部或新形态特征，再重新跑一个小规模 decoupling probe，例如：

- 修复后的缩量质量、放量衰竭、成交额承接；
- 低点后的高低点抬升序列；
- false-break 后的回撤深度与恢复速度；
- 板块/同主题同步修复质量；
- 事件后 3-5 日的 PIT-confirmation 状态，但必须严格定义为可交易延迟特征，不得偷看 low_to_high。

在没有这些新信息之前，继续在当前 12A4 feature bank 内调 rejector，大概率只是在 precision/bad-side frontier 上移动，而不是突破 frontier。

## 最终建议

不进入 `12A5B_state_change_morphology_badside_reduction_modeling`。

建议将当前阶段关闭为：

```text
12A5A_no_decoupling_stop_keep_feature_source
```

保留：

```text
state-change C0 as feature source
```

停止：

```text
state-change C0 as standalone timing signal
```
