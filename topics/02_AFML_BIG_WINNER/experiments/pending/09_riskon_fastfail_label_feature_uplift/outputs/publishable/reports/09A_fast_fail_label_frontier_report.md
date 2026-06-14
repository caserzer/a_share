# 09A Fast-Fail Label Frontier Report

生成日期：2026-06-14

- decision: `09A_label_frontier_candidate_source_caveated_selected`
- selected fast-fail labels: `break_swing_low_20`, `fixed_mae10_neg_12`
- event binding primary fast-fail label: `break_swing_low_20`
- selected cost target: `selected_fast_fail_10_label OR frozen_event_false_repair_20d_label`
- 09A 只做 label diagnostic，不训练模型；09C 必须读取事件级 binding，并独立评估 fast-fail-only target。

## 1. 结论

09A 可以进入 09C，但结论需要比初版报告更克制：

1. `break_swing_low_20` 是一个很温和的 structural fast-fail gate。它在 train 的 positive rate 只有 7.5433%，episode winner recall retention 为 100.0000%，winner injury rate 为 3.7062%，确实比 incumbent -10% 更少误伤 winner。
2. 但这不能直接解释为“精准 cost rejector”。在 train non-winner 样本上，`break_swing_low_20` 的 fast-fail 命中率只有 8.3805%，远低于 incumbent -10% 的 32.2870% 和 `fixed_mae10_neg_12` 的 21.4953%。它可能只是“杀得少”，因此自然更少杀错。
3. 两个入选 label 的 fast-fail 机制差异很大，但与 `false_repair_20d` 合成后，hybrid cost target 几乎相同。`fixed_mae10_neg_12` 与 `break_swing_low_20` 的 fast-fail Jaccard 只有 0.2619，但 cost-target positive-rate 差异只有 0.0227pp。这说明 09C 如果只训练 hybrid target，模型大概率主要学习 false-repair 结构，而不是 fast-fail 机制差异。
4. 因此 09C 的硬要求是：hybrid cost target 可以保留，但必须同时报告 fast-fail-only target 的排序质量、bad-side coverage、component-level contribution 和两个 selected label 的对照结果。否则无法回答 swing-low 是否真的提升 cost sorting。

## 2. 本轮任务边界

09A 的目的不是选择最终模型，也不是调阈值，而是把 `failure_10` / fast-fail label 的定义从单一 -10% barrier 扩展成可比较的 frontier：

- fixed MAE10: `-5%`, `-6%`, `-8%`, `-10%`, `-12%`
- vol / ATR scaled barrier
- structural break: event low, swing low, EMA20, EMA60
- incumbent baseline: 现有 `failure_10_label`
- cost bridge: fast-fail component 与 `frozen_event_false_repair_20d_label` 的 hybrid target 对齐

所有选择只基于 train。validation / robustness 只读，用于 caveat、降级和 09C 风险提示。

## 3. 数据与分母

主分母为 `risk_on_r_core_horizon_complete`，这是 09C 的主要候选训练对象。另有 `risk_on_r6_horizon_complete` 作为 risk_on 子集读数，`risk_off_e1_horizon_complete_readonly` 只作只读辅助。

| denominator | split | rows | winner_120_complete | winner_120_incomplete | non_executable | censored |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| risk_on_r_core | train | 16,603 | 16,571 | 32 | 32 | 0 |
| risk_on_r_core | validation | 4,457 | 4,455 | 2 | 2 | 0 |
| risk_on_r_core | robustness | 9,730 | 9,705 | 25 | 19 | 6 |
| risk_on_r_core | all | 30,790 | 30,731 | 59 | 53 | 6 |
| risk_on_r6 | all | 9,260 | 9,228 | 32 | 30 | 2 |
| risk_off_e1_readonly | all | 1,887 | 1,885 | 2 | 2 | 0 |

`winner_censoring_status` 不另造口径，而是由上游 `candidate_outcome_120d_status` 固定映射：

- `not_missing` -> `complete`
- `censored_incomplete_horizon` -> `incomplete_120d`
- `non_executable_next_open` -> `non_executable`

所有 winner 指标均在 `event_big_winner_120d_label` 非空样本上计算，空值数量必须等于 `winner_120_incomplete_n`。

## 4. Train Frontier

主分母 `risk_on_r_core_horizon_complete` 的 train 读数如下。

| candidate | positive rate | kill-wrong | winner injury | episode retention | gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `break_swing_low_20` | 7.5433% | 8.8000% | 3.7062% | 100.0000% | pass |
| `break_ema60` | 26.7757% | 10.3001% | 15.3976% | 95.7535% | pass |
| `fixed_mae10_neg_12` | 19.7031% | 10.4441% | 11.4892% | 97.5021% | pass |
| `atr14_2_0` | 35.8216% | 10.7789% | 21.5633% | 95.8368% | pass |
| `incumbent_failure_10_label` | 29.7990% | 11.0571% | 18.3962% | 96.5029% | diagnostic |
| `fixed_mae10_neg_10` | 27.5843% | 11.0917% | 17.0822% | 96.7527% | pass |
| `fixed_mae10_neg_08` | 37.8432% | 12.1352% | 25.6402% | 95.0874% | pass |
| `atr14_1_5` | 50.3222% | 12.2462% | 34.4003% | 92.7552% | fail |

`incumbent_failure_10_label` 被标为 `diagnostic` 不是因为它不合格，而是因为 requirement 将现役 label 固定为 baseline，不参与 Pareto selection；几乎等价的 `fixed_mae10_neg_10` 作为普通候选可以通过 bound gate，但未进入最终 selected set。

## 5. 入选 Label 的真实含义

09A 最终选出两个 label：

| selected fast-fail label | mechanism | train positive | train kill-wrong | train winner injury | train episode retention | max split positive spread |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `break_swing_low_20` | structural | 7.5433% | 8.8000% | 3.7062% | 100.0000% | 1.5732pp |
| `fixed_mae10_neg_12` | fixed MAE10 | 19.7031% | 10.4441% | 11.4892% | 97.5021% | 9.1083pp |

解释：

- `break_swing_low_20` 更像 winner-preserving 的 conservative gate，而不是已经证明有效的 cost rejector。
- `fixed_mae10_neg_12` 是 incumbent -10% 的更保守 fixed-barrier 对照，牺牲一部分 bad-side coverage，换取更低 winner injury。
- 两者都可以进入 09C，但必须拆开 fast-fail component 看效果。

## 6. Validation Power Caveat

validation 上的 winner 样本太少，不能用来支撑 label 选择，只能作只读 sanity check。

| label | validation positive_n | killed winner_n | validation kill-wrong | validation winner injury | winner_n |
| --- | ---: | ---: | ---: | ---: | ---: |
| `break_swing_low_20` | 338 | 5 | 1.4793% | 1.6779% | 298 |
| `fixed_mae10_neg_12` | 472 | 18 | 3.8136% | 6.0403% | 298 |
| `incumbent_failure_10_label` | 870 | 36 | 4.1379% | 12.0805% | 298 |

`break_swing_low_20` validation 只杀到 5 个 winner，这个单元格没有足够 power。报告中任何“validation 证明 swing-low 更优”的表述都应删除；正确说法是 train-only selection 通过，validation 未发现结构性反证，但 winner injury 读数低 power。

## 7. Non-Winner Hit Rate：低 Positive Rate 的反向证据

为了区分“精准保护 winner”和“几乎不过滤”，需要看 non-winner 上的 fast-fail 命中率。这里用 `winner_120_complete` 子集，non-winner = `event_big_winner_120d_label != 1`。

| label | split | positive_n | killed winner_n | non-winner hit_n | non-winner hit rate |
| --- | --- | ---: | ---: | ---: | ---: |
| `break_swing_low_20` | train | 1,250 | 110 | 1,140 | 8.3805% |
| `fixed_mae10_neg_12` | train | 3,265 | 341 | 2,924 | 21.4953% |
| `incumbent_failure_10_label` | train | 4,938 | 546 | 4,392 | 32.2870% |
| `break_swing_low_20` | all | 2,172 | 176 | 1,996 | 7.8465% |
| `fixed_mae10_neg_12` | all | 5,255 | 584 | 4,671 | 18.3610% |
| `incumbent_failure_10_label` | all | 8,151 | 947 | 7,204 | 28.3173% |

这张表改变了对 `break_swing_low_20` 的解释。它保留 winner 的能力强，但同时拦截 bad-side / non-winner 的覆盖也弱。对 09C 来说，它可以作为低误伤 structural gate 候选，但不能直接视为 cost rejector 的主 target。

## 8. Cost Target Bridge：False-Repair 稀释

主分母 `risk_on_r_core_horizon_complete` 上，fast-fail component 与 hybrid cost target 的关系如下。

| candidate | old fast-fail n | new fast-fail n | fast-fail Jaccard | old target n | new target n | old only | new only | hybrid Jaccard | old-only winner rate | new-only winner rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `incumbent_failure_10_label` | 8,151 | 8,151 | 1.0000 | 11,510 | 11,510 | 0 | 0 | 1.0000 | NA | NA |
| `fixed_mae10_neg_12` | 8,151 | 5,255 | 0.6447 | 11,510 | 10,755 | 755 | 0 | 0.9344 | 21.0596% | NA |
| `break_swing_low_20` | 8,151 | 2,172 | 0.2084 | 11,510 | 10,748 | 1,053 | 291 | 0.8861 | 21.4625% | 6.5517% |

关键观察：

- `break_swing_low_20` 与 incumbent 的 fast-fail Jaccard 只有 0.2084，说明它杀的不是同一批样本。
- 但合成 hybrid target 后，Jaccard 提升到 0.8861，因为 `false_repair_20d` 占主导。
- `fixed_mae10_neg_12` 与 `break_swing_low_20` 的 fast-fail Jaccard 只有 0.2619，但 cost-target positive-rate 仅差 0.0227pp。

这对 09C 是实质风险：如果只用 hybrid target 训练，模型可能学到的是 false-repair，而不是新 fast-fail label 的差异。

## 9. Robustness Caveat

robustness 段整体更难，尤其是 conditional kill-wrong。

| label | train kill-wrong | robustness kill-wrong | train winner injury | robustness winner injury |
| --- | ---: | ---: | ---: | ---: |
| `break_swing_low_20` | 8.8000% | 10.4811% | 3.7062% | 3.0138% |
| `fixed_mae10_neg_12` | 10.4441% | 14.8515% | 11.4892% | 11.1166% |
| `incumbent_failure_10_label` | 11.0571% | 15.5983% | 18.3962% | 18.0336% |

winner injury 没有全面恶化，但 kill-wrong 在 robustness 对三个核心 label 都上升。09C 不能只看 train frontier，也不能把 validation 的低 kill-wrong 当成稳定改善。

## 10. Binding 与字段语义修复

09A 的事件级 binding 输出为：

- `outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet`

本轮修复了一个容易误用的字段语义：

- `selected_fast_fail_touch_pos`：标的日线文件里的绝对 bar index，不是相对 horizon。
- `selected_fast_fail_touch_offset_sessions`：从 `trade_time` 到首次 touch 的交易日偏移；未触发或不可评估为 `-1`。

最新 binding 中，`selected_fast_fail_touch_offset_sessions` 的触发分布为 0 到 9 个交易日，符合 10D fast-fail horizon；未触发或不可评估为 `-1`。

| offset sessions | count |
| ---: | ---: |
| -1 | 38,837 |
| 0 | 52 |
| 1 | 149 |
| 2 | 236 |
| 3 | 278 |
| 4 | 354 |
| 5 | 426 |
| 6 | 393 |
| 7 | 406 |
| 8 | 424 |
| 9 | 382 |

09B / 09C 不得用 `selected_fast_fail_touch_pos` 计算 horizon，必须使用 `selected_fast_fail_touch_offset_sessions`。

## 11. Findings

1. 09A 成功把 incumbent -10% 放进了可审计 frontier，而不是继续凭直觉调整 barrier。
2. `fixed_mae10_neg_12` 是 incumbent 的自然保守版本：train positive rate 从 29.7990% 降到 19.7031%，winner injury 从 18.3962% 降到 11.4892%，但 non-winner hit rate 也从 32.2870% 降到 21.4953%。
3. `break_swing_low_20` 的主要价值是 winner-preserving，而不是已证明的 bad-sample recall。它 train episode retention 为 100.0000%，但 non-winner hit rate 只有 8.3805%。
4. cost target 的变化被 false-repair component 明显稀释。两个入选 label 的 fast-fail component 差异很大，但 hybrid target 几乎相同。
5. validation winner 单元格 power 太低，不能作为选择证据。09A 的选择纪律仍然是 train-only，OOS 只读。
6. transition 不应进入 09A/09C 主线；本轮所有 selected label 都绑定在 risk_on 主分母。

## 12. 对 09C 的硬要求

09C 可以使用两个 selected cost target：

- `break_swing_low_20__or_false_repair_20d`
- `fixed_mae10_neg_12__or_false_repair_20d`

但必须增加以下硬约束：

1. 必须单独训练或至少单独评估 fast-fail-only target，不能只报告 hybrid cost target。
2. 必须拆分 component-level metrics：fast-fail component、false-repair component、hybrid target 三套读数都要报。
3. 必须报告 non-winner hit rate / bad-side coverage，避免把低 positive rate 自动解释为高质量。
4. 必须把 validation winner injury 标为 low-power readout，不得用于 label 选择。
5. 必须保留 `source_caveated=True` 的继承说明，09C 结论不能越过 09A 的 source caveat。
6. 若 train-selected label 在 OOS positive-rate spread 超过 15pp，09C 必须降级为 diagnostic-only，不得仅写 caveat 后继续 claim uplift。
7. downstream horizon 与 touch offset 必须使用 `selected_fast_fail_touch_offset_sessions`，不能误用绝对 bar index。

## 13. 研究判断

09A 的价值不是“找到了最终答案”，而是把 09C 的问题收窄了：

- 如果目标是低误伤结构性停损，`break_swing_low_20` 值得保留。
- 如果目标是替代 incumbent -10% 的更温和 fixed barrier，`fixed_mae10_neg_12` 是合理对照。
- 如果目标是提升 cost rejector 排序质量，09C 不能只看 hybrid target。它必须证明 fast-fail component 本身能改善 cost sorting，否则 09A 的 label uplift 会被 false-repair component 吞掉。

最终建议：09C 继续，但把 `break_swing_low_20` 定位为 conservative structural gate candidate，把 `fixed_mae10_neg_12` 定位为 incumbent fixed-barrier challenger，并把 fast-fail-only evaluation 升级为硬 gate。
