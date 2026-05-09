# EP2 Requirement 01-03 实验结果总结

生成日期：2026-05-09

本文汇总 EP2 Requirement 01、Requirement 02、Requirement 03 的实验目标、冻结合同、主要结果、门槛状态和后续注意事项。结论基于当前本地结构化 artifacts：

- `ep2/outputs/requirement_01_label_and_baseline_freeze/`
- `ep2/outputs/requirement_02_hazard_timing_model/`
- `ep2/outputs/requirement_03_schedule_bridge/`

## 1. 总体结论

EP2 当前前三个 requirement 全部通过。

| 阶段 | 目标 | 状态 | 下一阶段判断 |
| --- | --- | --- | --- |
| Requirement 01 | 冻结 primary label 与 no-model baseline | passed, 20/20 gates | 可以进入 hazard timing |
| Requirement 02 | 训练并验证 hazard timing model | passed, 27/27 gates | 可以进入 schedule bridge |
| Requirement 03 | 将 hazard probe 组装为 probe / confirm-add / fast-fail schedule，并做 BaseRate overlap audit | passed, 17/17 gates | 可以进入 Requirement 04 |

当前最重要的结论：

1. R01 确认 `probe_with_simple_stop` 是唯一通过全部 no-model baseline gates 的低换手 schedule primitive。
2. R02 证明 hazard model 可以在 validation / robustness 上选择低频 probe，并相对 R01 frozen baseline 有正 after-cost lift。
3. R03 证明在 R02 probe 上增加 deterministic confirm-add 后，validation / robustness 的 mean after-cost return 进一步提高，且没有额外损失 big-winner coverage。
4. R03 的 BaseRate overlap audit 显示 EP2 exposure 大部分没有被 BaseRate primary buy/trade 覆盖，说明它不是简单复刻 BaseRate TopK。
5. 但当前 EP2 仍不是完整策略。最大未解决问题是 holding / exit：big-winner 真正持有到 +50% target 的 capture rate 很低，R04 需要专门解决这个问题。

## 2. Requirement 01: Label and Baseline Freeze

Requirement 01 的作用是冻结后续阶段不能随意修改的研究合同，包括 primary label、no-model baseline、输入 artifacts 和 gate 解释。

### 2.1 冻结结果

冻结状态：

| 字段 | 结果 |
| --- | --- |
| validation_status | passed |
| gate_count | 20 |
| passed_gate_count | 20 |
| failed_gate_count | 0 |
| primary_label_id | `confirm_h10_u10_d06_conservative_fail` |
| frozen_baseline_id | `probe_with_simple_stop` |

Primary label 含义：

- horizon: 10 trading days
- upside target: +10%
- drawdown stop: -6%
- same-day policy: conservative fail

该 label 的主要统计：

| 指标 | 数值 |
| --- | ---: |
| candidate_positive_rate | 0.224157 |
| episode_any_positive_rate | 0.431616 |
| episode_first_valid_positive_rate | 0.267022 |
| episode_weighted_positive_rate | 0.243188 |
| top1_instrument_year_positive_share | 0.009139 |
| same_day_ambiguity_rate | 0.000000 |

解释：这个 label 的 candidate positive rate 不高，避免了过宽标签；episode 层面仍有足够正样本，后续 hazard model 有训练空间；同日 ambiguity 为 0，避免了同日先涨后跌顺序不清的问题。

### 2.2 Baseline freeze 结果

R01 对多种 no-model schedule 做了同口径比较。只有 `probe_with_simple_stop` 通过所有 gates。

| schedule | probe_rate | mean_after_cost_return | big_winner_capture_rate | turnover_proxy | all_gates_passed |
| --- | ---: | ---: | ---: | ---: | --- |
| buy_all_on_launch_hold_to_H | 0.997565 | -0.004504 | 0.039216 | 50.185227 | false |
| buy_all_on_launch_with_same_fast_fail | 0.997565 | -0.005116 | 0.039216 | 50.246591 | false |
| fixed_delay_1d | 0.903409 | -0.004767 | 0.028125 | 45.511364 | false |
| fixed_delay_3d | 0.753653 | -0.006723 | 0.033473 | 37.984091 | false |
| fixed_delay_5d | 0.642857 | -0.006334 | 0.040404 | 32.389773 | false |
| fixed_delay_10d | 0.463880 | -0.004777 | 0.014599 | 23.359091 | false |
| random_probe_within_launch_window | 0.997159 | -0.005470 | 0.056779 | 50.211511 | false |
| staged_buy_all | 0.993101 | -0.006214 | 0.039660 | 44.674773 | false |
| probe_then_naive_add | 0.993101 | -0.006574 | 0.045326 | 45.637159 | false |
| probe_with_simple_stop | 0.993101 | -0.001409 | 0.039660 | 15.006477 | true |

关键解释：

- 直接全买或固定延迟买入频率过高，且 after-cost return 为负。
- `probe_with_simple_stop` 不是收益很强的最终策略，但它在 no-model baseline 中是唯一满足 gate 的低换手 primitive。
- R01 因此没有证明 EP2 已经能交易，只是冻结了一个可被后续模型改进的 baseline。

## 3. Requirement 02: Hazard Timing Model

Requirement 02 的作用是：在 R01 冻结的 label 和 baseline 上，训练 validation-selected hazard timing model，选择每个 launch episode 的低频 probe 时点。

### 3.1 冻结合同与模型配置

R02 manifest 关键字段：

| 字段 | 结果 |
| --- | --- |
| phase | `requirement_02_hazard_timing_model` |
| validation_status | passed |
| requirement_03_proceed_status | passed |
| primary_label_id | `confirm_h10_u10_d06_conservative_fail` |
| frozen_baseline_id | `probe_with_simple_stop` |
| model_type | `lightgbm_multiclass_softmax` |
| selected_threshold | 0.3205667777673395 |
| selected_stop_risk_ceiling | 0.27410397287415667 |

模型类别为三分类：

- `target_first`
- `stop_first`
- `neither`

训练/验证/稳健性切分：

| split | episode_count | rows |
| --- | ---: | ---: |
| train | 1142 | 8149 |
| validation | 532 | 4467 |
| robustness | 770 | 5628 |

### 3.2 类别分布

| split | target_first row_share | stop_first row_share | neither row_share |
| --- | ---: | ---: | ---: |
| train | 0.248374 | 0.375383 | 0.376242 |
| validation | 0.179987 | 0.324603 | 0.495411 |
| robustness | 0.189943 | 0.256752 | 0.553305 |

解释：

- validation / robustness 中 `neither` 占比更高，说明后验环境比 train 更难。
- `target_first` 在 validation / robustness 中约 18%-19%，仍有可学习空间。
- 类别分布变化使得只看 train 表现没有意义，R02 的关键是 validation 选择与 robustness holdout。

### 3.3 模型指标

| split | multiclass_logloss | target_first_auc_ovr | stop_first_auc_ovr | neither_auc_ovr | top_decile_target_first_rate | top_decile_stop_first_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 0.884071 | 0.804591 | 0.754596 | 0.742646 | 0.740964 | 0.072289 |
| validation | 0.999980 | 0.719774 | 0.646084 | 0.608463 | 0.586130 | 0.093960 |
| robustness | 1.001518 | 0.740909 | 0.646656 | 0.654769 | 0.472469 | 0.120782 |

解释：

- `target_first_auc_ovr` 在 validation 为 0.719774、robustness 为 0.740909，说明模型对目标先到达有稳定排序能力。
- `top_decile_target_first_rate` 明显高于整体 `target_first` row_share，说明 hazard score 的高分区有实际信息。
- `stop_first_auc_ovr` 约 0.646，风险识别能力弱于 target，但足够支持 stop-risk ceiling 过滤。

### 3.4 阈值选择

R02 选择结果：

| 字段 | 数值 |
| --- | ---: |
| selected_threshold | 0.320567 |
| selected_stop_risk_ceiling | 0.274104 |
| selection_split | validation |
| validation_objective_value | 0.005353 |
| validation_passed_all_gates | true |

选择原则：

- 阈值只用 validation score quantiles 选择。
- robustness 不参与阈值选择，只作为 holdout。
- 如果没有 validation-passing threshold，R02 必须 fail closed；当前不是这种情况。

### 3.5 R02 schedule 结果

R02 schedule id: `hazard_probe_with_simple_stop`

| split | episode_count | exposed_count | probe_rate | fast_fail_exit_rate | mean_after_cost_return | p05 | p95 | big_winner_capture_rate | turnover_proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1142 | 236 | 0.206655 | 0.022767 | 0.005058 | 0.000000 | 0.041882 | 0.043243 | 3.124623 |
| validation | 532 | 104 | 0.195489 | 0.016917 | 0.002693 | -0.003753 | 0.027170 | 0.046512 | 2.955789 |
| robustness | 770 | 149 | 0.193506 | 0.031169 | 0.002689 | -0.006188 | 0.029606 | 0.023622 | 2.925818 |

R02 相对 R01 frozen baseline 的对比：

| split | mean_after_cost_return_diff | median_after_cost_return_diff | big_winner_coverage_loss | turnover_reduction |
| --- | ---: | ---: | ---: | ---: |
| train | 0.005192 | 0.006712 | 0.111111 | 0.937116 |
| validation | 0.005353 | 0.006526 | 0.000000 | 0.940514 |
| robustness | 0.005210 | 0.006500 | 0.000000 | 0.941117 |

解释：

- R02 将 R01 的 almost-all-episode probe 变成约 19%-21% 的低频 probe。
- validation / robustness 都保持正 after-cost lift。
- 相对 daily BaseRate turnover reference，turnover reduction 约 94%。
- big-winner coverage 没有在 validation / robustness 中恶化。

### 3.6 R02 gate 结论

R02 gate audit 共 27 行，全部通过。

关键 hard gates：

- validation mean diff > 0: 0.005353
- robustness mean diff > 0: 0.005210
- validation / robustness big-winner coverage loss: 0
- validation turnover reduction: 0.940514
- robustness turnover reduction: 0.941117
- validation top1 instrument-year exposure share: 0.019231
- robustness top1 instrument-year exposure share: 0.020134
- validation positive PnL year count: 2
- robustness positive PnL year count: 2

Requirement-gated judgment: R02 可以进入 R03。

## 4. Requirement 03: Schedule Bridge and BaseRate-Overlap Audit

Requirement 03 的作用是：把 R02 的 hazard probe 组装成完整 schedule：

```text
hazard_probe_confirm_add_fast_fail
```

其规则为：

- R02 selected probe 执行后先建 `0.30` 权重；
- 在 probe 后 +1 到 +3 个交易日内寻找最早 valid confirm-add；
- confirm-add 后目标权重变为 `1.00`；
- 仍使用 fast-fail 与 H=10 natural exit；
- BaseRate row-level 数据只能用于 overlap audit，不能反向影响 EP2 schedule。

### 4.1 R3 manifest 状态

| 字段 | 结果 |
| --- | --- |
| validation_status | passed |
| next_phase_proceed_status | passed |
| primary_label_id | `confirm_h10_u10_d06_conservative_fail` |
| frozen_baseline_id | `probe_with_simple_stop` |
| hazard_schedule_id | `hazard_probe_with_simple_stop` |
| schedule_bridge_id | `hazard_probe_confirm_add_fast_fail` |
| selected_threshold | 0.3205667777673395 |
| selected_stop_risk_ceiling | 0.27410397287415667 |

### 4.2 R3 schedule 结果

| split | episode_count | exposed_count | probe_rate | confirm_add_rate | fast_fail_exit_rate | mean_after_cost_return | p05 | p95 | big_winner_capture_rate | turnover_proxy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1142 | 236 | 0.206655 | 0.135727 | 0.020140 | 0.012852 | -0.002695 | 0.107665 | 0.043243 | 7.979264 |
| validation | 532 | 104 | 0.195489 | 0.139098 | 0.015038 | 0.008592 | -0.007543 | 0.080889 | 0.046512 | 7.920000 |
| robustness | 770 | 149 | 0.193506 | 0.142857 | 0.031169 | 0.005769 | -0.018225 | 0.057771 | 0.023622 | 8.044364 |

解释：

- R3 没有改变 episode-level probe coverage，probe rate 与 R2 一致。
- confirm-add rate 约 13.6%-14.3%，说明大部分 probe 后仍没有满足 confirm-add 条件，schedule 仍然比较低频。
- mean after-cost return 明显高于 R2 simple-stop。
- turnover proxy 从 R2 约 2.9-3.1 提高到约 7.9-8.0，但仍远低于 daily BaseRate reference。

### 4.3 R3 相对 R2 的改进

| split | mean_after_cost_return_diff vs R2 | big_winner_coverage_loss | turnover_reduction vs daily BaseRate | confirm_add_return_contribution | fast_fail_return_contribution |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 0.007794 | ~0 | 0.839415 | 0.007794 | -0.000990 |
| validation | 0.005899 | ~0 | 0.840608 | 0.005899 | -0.000641 |
| robustness | 0.003080 | ~0 | 0.838105 | 0.003080 | -0.001608 |

解释：

- R3 的收益增量主要来自 confirm-add。
- `fast_fail_return_contribution` 为负，说明 fast-fail 当前更像风险控制合同，而不是 mean-return 增强项。
- R3 没有提高 strict big-winner capture rate，但也没有比 R2 损失 big-winner coverage。

### 4.4 R3 gate 结论

R3 gate audit 共 17 行，全部通过。

关键 hard gates：

| gate | validation | robustness | threshold | 状态 |
| --- | ---: | ---: | ---: | --- |
| mean_after_cost_return_diff_vs_requirement_02 | 0.005899 | 0.003080 | validation > 0, robustness >= -0.001 | passed |
| big_winner_coverage_loss_vs_requirement_02 | ~0 | ~0 | <= 0.10 | passed |
| missed_gain_to_exposure_median | 0.000000 | 0.000000 | <= 0.08 | passed |
| turnover_reduction_vs_daily_baserate | 0.840608 | 0.838105 | >= 0.50 | passed |
| top1_instrument_year_exposure_share | 0.019231 | 0.020134 | <= 0.10 | passed |
| top5_instrument_exposure_share | 0.096154 | 0.073826 | <= 0.35 | passed |
| baserate_overlap_report_coverage | 1.000000 | 1.000000 | >= 0.95 | passed |
| uncovered_ep2_exposure_share | 0.994382 | 0.945946 | >= 0.20 | passed |

Requirement-gated judgment: R3 可以进入 R4。

## 5. BaseRate Overlap Audit

R3 的 BaseRate 部分是 audit-only，不参与 schedule selection。

### 5.1 BaseRate coverage

| split | eligible_ep2_action_count | prediction_coverage_rate | order_coverage_rate | trade_coverage_rate | coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| validation | 178 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| robustness | 259 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

解释：validation / robustness 上所有 EP2 executed exposure actions 都能在 BaseRate OOS panel 的日期域中被审计，coverage gate 干净通过。

### 5.2 Launch overlap

| split | probes | prediction top50 hit rate | order hit rate | trade hit rate | any hit rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| validation | 104 | 0.125000 | 0.009615 | 0.009615 | 0.125000 |
| robustness | 149 | 0.335570 | 0.093960 | 0.093960 | 0.335570 |

解释：

- EP2 probe 与 BaseRate 高分区存在一定交集，尤其 robustness 中 prediction top50 hit rate 为 33.56%。
- 但实际 order/trade overlap 很低，validation 约 0.96%，robustness 约 9.40%。
- 这说明 EP2 不是 BaseRate primary TopK trade 的简单子集。

### 5.3 Score-region overlap

| split | action_type | event_count | mean_score_rank_pct | high_score_region_rate | prediction_top50_hit_rate |
| --- | --- | ---: | ---: | ---: | ---: |
| validation | probe_entry | 104 | 0.535106 | 0.173077 | 0.125000 |
| validation | confirm_add | 74 | 0.424739 | 0.135135 | 0.081081 |
| robustness | probe_entry | 149 | 0.650512 | 0.395973 | 0.335570 |
| robustness | confirm_add | 110 | 0.531854 | 0.227273 | 0.163636 |

解释：

- probe_entry 比 confirm_add 更接近 BaseRate 高分区域。
- confirm_add 仍有一部分落在 BaseRate 高分区，但整体更偏向 EP2 自己的 event timing 逻辑。

### 5.4 Uncovered low-frequency opportunity

| split | executed_ep2_exposure_count | BaseRate trade overlap rate | uncovered exposure share | uncovered_episode_share | uncovered_mean_after_cost_return | uncovered_big_winner_capture_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | 178 | 0.005618 | 0.994382 | 0.193609 | 0.044379 | 0.125000 |
| robustness | 259 | 0.054054 | 0.945946 | 0.175325 | 0.033847 | 0.068182 |

解释：

- 大多数 EP2 exposure action 没有被 BaseRate primary trade 覆盖。
- uncovered subset 自身仍有正 after-cost return。
- 这是 R3 最有价值的 bridge evidence：EP2 暂时不应被视为 BaseRate 的重复交易，而是一个可继续研究的低频事件机会集合。

### 5.5 Leakage audit

BaseRate leakage audit 11/11 passed。关键审计包括：

- R02 threshold 未变化；
- R02 stop-risk ceiling 未变化；
- BaseRate 未用于 probe selection；
- BaseRate 未用于 confirm-add selection；
- BaseRate 未用于 feature construction；
- BaseRate 未用于 label selection；
- BaseRate 未用于 schedule selection；
- BaseRate portfolio return 未作为 gate；
- BaseRate row-level 数据只在 EP2 schedule action / exposure artifacts 生成后读取；
- action panel hash 在 BaseRate load 前后不变；
- exposure panel hash 在 BaseRate load 前后不变。

因此 R3 的 BaseRate 部分是诊断审计，不是模型选择或 schedule 调参。

## 6. Big-Winner 解释

R3 的 strict big-winner capture rate 看起来低：

| split | strict capture rate |
| --- | ---: |
| train | 0.043243 |
| validation | 0.046512 |
| robustness | 0.023622 |

这个指标的定义很严格：必须在 +50% target 到来前已经有 exposure，并且到达 +50% target 当天仍未退出。

如果改成“只要 big-winner episode 被买入过就算成功”，比例明显更高：

| split | big_winner_count | bought_count | bought_rate | strict_captured_count | strict_capture_rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 185 | 73 | 0.394595 | 8 | 0.043243 |
| validation | 43 | 16 | 0.372093 | 2 | 0.046512 |
| robustness | 127 | 46 | 0.362205 | 3 | 0.023622 |

解释：

- hazard/probe 对未来 big winner 有一定命中能力：validation 买到 37.21%，robustness 买到 36.22%。
- strict capture 低的主因不是完全买不到，而是 H=10 natural exit 太短，很多后续 +50% winner 在 target 到来前已经被卖出。
- R4 的核心问题应该是 holding / exit，而不是重新搜索 R2 hazard threshold 或 R3 confirm-add 规则。

## 7. 阶段性判断

EP2 到 R3 为止的逻辑链条是成立的：

1. R1 找到并冻结了唯一通过 no-model gates 的低换手 baseline：`probe_with_simple_stop`。
2. R2 用 hazard model 将 probe 从几乎全覆盖压缩到约 20% episode，并在 validation / robustness 中获得正 after-cost lift。
3. R3 在 R2 probe 上加入 deterministic confirm-add，进一步提高 mean after-cost return，且没有增加 big-winner coverage loss。
4. BaseRate overlap audit 显示 EP2 exposure 与 daily TopK 有有限交集，但大量实际 exposure 是 BaseRate 未覆盖的低频机会。

当前不能得出的结论：

- 不能说 EP2 已经是完整可交易策略；
- 不能说 EP2 在组合层面优于 BaseRate；
- 不能说 fast-fail 提高了 mean return；
- 不能说当前 10-day schedule 能有效捕获大 winner。

可以得出的结论：

- EP2 event timing 信号有继续研究价值；
- R2 hazard score 具备稳定排序能力；
- R3 confirm-add 是当前最明确的收益增量来源；
- 后续应进入 R4，专门研究 holding / exit / portfolio assembly。

## 8. Requirement 04 建议方向

R4 不应重做 R1-R3 的 label、threshold 或 BaseRate selection。建议保持以下 frozen contract：

- primary label: `confirm_h10_u10_d06_conservative_fail`
- R2 threshold: `0.3205667777673395`
- R2 stop-risk ceiling: `0.27410397287415667`
- R3 schedule: `hazard_probe_confirm_add_fast_fail`

R4 的重点应是：

1. 持有期延长与退出规则：解决 H=10 过早退出导致 big-winner strict capture 低的问题。
2. fast-fail 的角色重估：当前 fast-fail 对 mean return 是负贡献，应评估其是否减少尾部损失，而不是把它当作收益来源。
3. 组合层面约束：验证低频 EP2 exposure 在真实组合聚合后是否仍有正收益、低集中度和可控换手。
4. 与 BaseRate 的组合关系：R3 已证明有 uncovered opportunity，R4 可以研究是否作为独立 sleeve、overlay，或只作为事件型补充信号。

最终 gate judgment：

```text
Requirement 01: passed
Requirement 02: passed
Requirement 03: passed
Proceed to Requirement 04: yes
```
