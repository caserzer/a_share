# R08 H3 量价单股状态可迁移性审计报告

## 1. 最终结论

`final_decision = r08_blocked_data_or_execution_contract`

`authorized_r09_flag = False`

本次重跑已将 `train_direction_valid_instrument_count_min` 从 `100` 下调到 `80`。这个改动成功解除上一版的 direction 阻断：三个 family 都形成了可评价的 family state score，后续 spread、instrument transfer、monotonicity、concentration 也都有可读数值。

但 R08 仍然没有授权 R09。新的阻断点不是 factor direction，而是更下游的 segment-level sample gate：seen / unseen instrument segment 在多个 split 中有效股票数或有效信号日期不足，导致 3 个 in-scope family 仍被判定为 sample-blocked。

最终 first-match replay：

| item | value |
|:--|:--|
| final decision | `r08_blocked_data_or_execution_contract` |
| selected rule | `rule_02b` |
| selected reason | `sample_blocked_family_count / total_in_scope_family_count >= 0.50` |
| sample-blocked families | 3 / 3 |
| R09 authorization | False |

关键解释：

```text
把 direction 门槛降到 80 后，R08 已经可以观察到状态收益关系；
但这些关系无法通过 instrument segment 的样本厚度要求，
尤其是 unseen instruments 的有效股票数远低于 100。
因此结果仍是 data / sample contract blocked，而不是 supported。
```

## 2. 本次改动

本次变更只改变 direction 样本门槛：

| field | old | new |
|:--|--:|--:|
| `train_direction_valid_instrument_count_min` | 100 | 80 |

保持不变的关键门槛：

| field | value |
|:--|--:|
| `valid_instrument_count_min` | 100 |
| `valid_signal_dates_min` | 70 |
| `min_per_instrument_signal_count` | 80 |
| `instrument_active_signal_week_share_min` | 0.50 |
| `state_decile_monotonicity_min` | 0.60 |
| `positive_instrument_share_validation_unseen_min` | 0.55 |
| `positive_instrument_share_robustness_unseen_min` | 0.50 |

因此，这次不是放松所有样本纪律，只是允许 train-only factor direction 在 80 只有效股票以上成立。

## 3. 股票样本选择

R08 仍然从 R06 candidate base 的 PIT universe 合格事件出发，不按收益、股票名、family 表现或 validation 结果挑股票。

| source | rows | decision-bearing H3 events | instruments | signal dates | min signal date | max signal date |
|:--|--:|--:|--:|--:|:--|:--|
| `r06_candidate_base` | 85,846 | 83,756 | 489 | 430 | 2017-08-04 | 2025-12-31 |

instrument split 仍然是 deterministic hash：

```text
sha256(instrument_id) mod 10
0-5 -> instrument_train_set
6-7 -> instrument_validation_set
8-9 -> instrument_robustness_set
```

这意味着 R08 仍然是在检验跨股票迁移，不是 validation 选股。

## 4. Direction 阶段：已解除上一版阻断

降低门槛后，factor direction 结果如下：

| family | factor count | retained factors | insufficient factors | min valid instruments | median valid instruments | max valid instruments | positive direction | negative direction |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| volume_price_correlation | 3 | 3 | 0 | 90 | 90 | 90 | 1 | 2 |
| volume_surge_money_flow | 15 | 14 | 1 | 75 | 90 | 90 | 8 | 7 |
| vwap_deviation | 6 | 6 | 0 | 90 | 90 | 90 | 3 | 3 |

family scope：

| family | R06 included factors | R08 retained factors | excluded factor ids | family scope pass |
|:--|--:|--:|:--|:--|
| volume_price_correlation | 3 | 3 | NA | True |
| volume_surge_money_flow | 15 | 14 | `alpha025` | True |
| vwap_deviation | 6 | 6 | NA | True |

主要变化：

```text
上一版 retained factor count = 0 / 0 / 0；
本版 retained factor count = 3 / 14 / 6。
```

所以 R08 现在不再卡在 factor direction。后续的 spread、monotonicity、concentration 数值可以被解释，但解释必须带着 sample gate 失败的限制。

## 5. Sample Gate：新的核心阻断点

Sample gate 要求每个 family 在 split / segment 维度都有足够厚的有效样本：

```text
valid_instrument_count >= 100
valid_signal_dates >= 70
min_per_instrument_signal_count >= 80
```

新结果显示，all-instrument 口径多数可评价，但 seen / unseen segment 口径普遍不足，尤其 unseen segment 远低于 100 只有效股票。

| family | split | segment | valid dates | valid instruments | sample pass |
|:--|:--|:--|--:|--:|:--|
| volume_price_correlation | train | all | 107 | 149 | True |
| volume_price_correlation | train | seen | 63 | 89 | False |
| volume_price_correlation | train | unseen | 88 | 60 | False |
| volume_price_correlation | validation | all | 78 | 178 | True |
| volume_price_correlation | validation | seen | 57 | 104 | False |
| volume_price_correlation | validation | unseen | 23 | 33 | False |
| volume_price_correlation | robustness | all | 84 | 183 | True |
| volume_price_correlation | robustness | seen | 71 | 113 | True |
| volume_price_correlation | robustness | unseen | 35 | 37 | False |
| volume_surge_money_flow | train | all | 74 | 148 | True |
| volume_surge_money_flow | train | seen | 37 | 90 | False |
| volume_surge_money_flow | train | unseen | 62 | 58 | False |
| volume_surge_money_flow | validation | all | 75 | 124 | True |
| volume_surge_money_flow | validation | seen | 39 | 74 | False |
| volume_surge_money_flow | validation | unseen | 14 | 24 | False |
| volume_surge_money_flow | robustness | all | 55 | 162 | False |
| volume_surge_money_flow | robustness | seen | 33 | 99 | False |
| volume_surge_money_flow | robustness | unseen | 15 | 34 | False |
| vwap_deviation | train | all | 114 | 141 | True |
| vwap_deviation | train | seen | 75 | 83 | False |
| vwap_deviation | train | unseen | 108 | 58 | False |
| vwap_deviation | validation | all | 91 | 131 | True |
| vwap_deviation | validation | seen | 70 | 77 | False |
| vwap_deviation | validation | unseen | 33 | 22 | False |
| vwap_deviation | robustness | all | 82 | 152 | True |
| vwap_deviation | robustness | seen | 64 | 92 | False |
| vwap_deviation | robustness | unseen | 46 | 35 | False |

这张表是本次报告最重要的证据。R08 的样本不足已经从“factor direction 训练股票不够”转移为“state bucket 后的 seen / unseen segment 厚度不够”。

特别是 unseen segment：

| family | validation unseen valid instruments | robustness unseen valid instruments |
|:--|--:|--:|
| volume_price_correlation | 33 | 37 |
| volume_surge_money_flow | 24 | 34 |
| vwap_deviation | 22 | 35 |

这些数量远低于 `valid_instrument_count_min = 100`。因此，即使某些 unseen spread 为正，也不能被当作稳定的 cross-instrument transfer evidence。

## 6. Gate Replay

family gate replay：

| family | sample | time transfer | instrument transfer | concentration | monotonicity | supported | family decision |
|:--|:--|:--|:--|:--|:--|:--|:--|
| volume_price_correlation | False | False | False | True | True | False | no_support |
| volume_surge_money_flow | False | False | False | True | False | False | stock_specific_behavior_only |
| vwap_deviation | False | True | False | True | True | False | no_support |

final decision replay：

| rule | condition | fires | selected |
|:--|:--|:--|:--|
| rule_01 | scope/asof/instrument_split/h3_label_contract violation | False | False |
| rule_02 | evaluable_family_count == 0 | False | False |
| rule_02b | sample_blocked_family_count / total_in_scope_family_count >= 0.50 | True | True |
| rule_03 | supported_family_count > 0 | False | False |
| rule_04 | seen pass but unseen fail | False | False |
| rule_05 | validation pass but robustness fail | False | False |
| rule_06 | otherwise | False | False |

注意：`rule_02` 没有触发，说明本版不是“完全没有可评价 family”。触发的是 `rule_02b`，说明 family 有数值，但多数 family 的 sample contract 不足以支持最终判断。

## 7. Time Transfer 结果

all-instrument 口径下，三类 family 的 H3 state spread 如下：

| family | split | mean spread | median spread | positive year count | positive date share |
|:--|:--|--:|--:|--:|--:|
| volume_price_correlation | train | 0.0099% | -0.0140% | 3 | 49.53% |
| volume_price_correlation | validation | 0.1734% | 0.1437% | 1 | 55.13% |
| volume_price_correlation | robustness | 0.1942% | -0.0213% | 2 | 48.81% |
| volume_surge_money_flow | train | 0.1133% | 0.0889% | 2 | 51.35% |
| volume_surge_money_flow | validation | -0.0101% | -0.0068% | 1 | 48.00% |
| volume_surge_money_flow | robustness | -0.0614% | -0.0883% | 0 | 45.45% |
| vwap_deviation | train | 0.3059% | 0.2009% | 2 | 55.26% |
| vwap_deviation | validation | 0.2691% | 0.2501% | 2 | 56.04% |
| vwap_deviation | robustness | 0.2606% | 0.2456% | 2 | 58.54% |

解读：

- `vwap_deviation` 是唯一通过 time transfer gate 的 family，validation 与 robustness 都为正，且相对 train 没有明显劣化。
- `volume_price_correlation` 的 validation / robustness mean spread 为正，但 validation positive year count 只有 1，robustness median spread 为负，因此 time gate 不通过。
- `volume_surge_money_flow` 从 train 正 spread 退化到 validation / robustness 负 spread，time transfer 不成立。

## 8. Seen / Unseen Instrument Transfer

seen / unseen 对比是 R08 的核心。结果如下：

| family | split | seen mean spread | unseen mean spread | unseen positive instrument share | unseen-vs-seen non-deterioration |
|:--|:--|--:|--:|--:|:--|
| volume_price_correlation | validation | 0.1904% | -0.1116% | 54.55% | False |
| volume_price_correlation | robustness | 0.1577% | 0.0973% | 86.49% | True |
| volume_surge_money_flow | validation | 0.1323% | -0.8121% | 50.00% | False |
| volume_surge_money_flow | robustness | 0.1991% | -0.0060% | 41.18% | True |
| vwap_deviation | validation | 0.2993% | 0.1698% | 40.91% | True |
| vwap_deviation | robustness | 0.1266% | 0.2398% | 71.43% | True |

解读：

- `vwap_deviation` 的 unseen spread 在 validation / robustness 都为正，是本轮最接近 R08 原始假设的 family。
- 但 `vwap_deviation` 的 validation unseen positive instrument share 只有 40.91%，低于 55% 门槛；而且 validation unseen 有效股票只有 22 只，远低于 100。
- `volume_price_correlation` 在 robustness unseen 表现很好，但 validation unseen spread 为负，不能证明跨年份迁移。
- `volume_surge_money_flow` 是典型 seen 较强、unseen 不稳，gate label 被打成 `stock_specific_behavior_only`，但由于 sample gate 先阻断，不能作为最终 decision。

结论：instrument transfer 没有通过。最强的候选是 `vwap_deviation`，但它是“有迹象、样本太薄、positive instrument share 不够”，不是可授权结论。

## 9. Decile Monotonicity

all-instrument 口径下：

| family | train monotonicity | validation monotonicity | robustness monotonicity | gate interpretation |
|:--|--:|--:|--:|:--|
| volume_price_correlation | 0.5758 | 0.7091 | 0.9758 | validation / robustness strong, train slightly below 0.60 |
| volume_surge_money_flow | 0.8303 | 0.2848 | -0.5758 | fails out-of-sample monotonicity |
| vwap_deviation | 0.9273 | 0.6970 | 0.9152 | passes monotonicity |

seen / unseen 细分中，monotonicity 仍然暴露了样本问题：

| family | split | seen monotonicity | unseen monotonicity |
|:--|:--|--:|--:|
| volume_price_correlation | validation | 0.2727 | 0.5152 |
| volume_price_correlation | robustness | 0.9636 | 0.9030 |
| volume_surge_money_flow | validation | 0.4061 | -0.4303 |
| volume_surge_money_flow | robustness | -0.6848 | -0.5152 |
| vwap_deviation | validation | 0.4909 | 0.3576 |
| vwap_deviation | robustness | 0.9152 | 0.8909 |

解读：

- `vwap_deviation` all-instrument monotonicity 最稳定，但 validation 的 seen/unseen 细分都没有达到 0.60。
- `volume_price_correlation` robustness 很强，但 validation 细分弱，说明跨年份稳定性不足。
- `volume_surge_money_flow` 明显不应进入后续策略讨论。

## 10. Concentration

all-instrument 口径下，三类 family 的 concentration gate 都通过：

| family | split | top1 instrument share | top5 instrument share | top1 industry share | concentration pass |
|:--|:--|--:|--:|--:|:--|
| volume_price_correlation | validation all | 2.00% | 8.48% | 13.48% | True |
| volume_price_correlation | robustness all | 1.62% | 6.88% | 14.08% | True |
| volume_surge_money_flow | validation all | 2.25% | 8.56% | 13.49% | True |
| volume_surge_money_flow | robustness all | 3.23% | 10.23% | 10.74% | True |
| vwap_deviation | validation all | 3.93% | 11.98% | 9.69% | True |
| vwap_deviation | robustness all | 1.96% | 8.47% | 13.02% | True |

但 unseen segment 中多处 concentration 不通过，典型例子：

| family | split | segment | top1 instrument share | top5 instrument share | pass |
|:--|:--|:--|--:|--:|:--|
| volume_price_correlation | validation | unseen | 7.65% | 30.45% | False |
| volume_price_correlation | robustness | unseen | 7.53% | 29.27% | False |
| volume_surge_money_flow | validation | unseen | 8.48% | 31.03% | False |
| volume_surge_money_flow | robustness | unseen | 7.22% | 31.55% | False |
| vwap_deviation | validation | unseen | 13.40% | 34.76% | False |
| vwap_deviation | robustness | unseen | 8.46% | 35.13% | False |

这再次说明 unseen segment 的样本太薄。即使 unseen spread 为正，也容易由少数股票贡献较大比例，不能直接解释为可迁移规律。

## 11. Family-by-Family Findings

### 11.1 `volume_price_correlation`

`volume_price_correlation` 在本版中已经不再 direction-blocked，3 个 factor 全部保留。

正面证据：

- validation all-instrument spread = 0.1734%；
- robustness all-instrument spread = 0.1942%；
- robustness unseen spread = 0.0973%；
- robustness unseen positive instrument share = 86.49%；
- robustness monotonicity = 0.9758。

负面证据：

- validation unseen spread = -0.1116%；
- validation positive year count = 1；
- validation unseen valid instruments = 33；
- robustness unseen valid instruments = 37；
- unseen concentration 在 validation / robustness 都失败。

结论：R07 的 `volume_price_correlation H3` 正例在 R08 中出现了一部分延续，尤其 robustness 很强；但 validation unseen 不确认，样本也不足，不能支持 transferability。

### 11.2 `volume_surge_money_flow`

正面证据：

- train all-instrument spread = 0.1133%；
- validation seen spread = 0.1323%；
- robustness seen spread = 0.1991%。

负面证据：

- validation all-instrument spread = -0.0101%；
- robustness all-instrument spread = -0.0614%；
- validation unseen spread = -0.8121%；
- robustness unseen spread = -0.0060%；
- validation unseen positive instrument share = 50.00%；
- robustness unseen positive instrument share = 41.18%；
- robustness monotonicity = -0.5758。

结论：这是最接近“seen instruments 有效、unseen instruments 不确认”的 family。当前 gate label 为 `stock_specific_behavior_only`，但由于 sample gate 先阻断，它不能作为最终 decision。研究上应视为不支持可迁移。

### 11.3 `vwap_deviation`

正面证据：

- time transfer gate 通过；
- validation all-instrument spread = 0.2691%；
- robustness all-instrument spread = 0.2606%；
- validation unseen spread = 0.1698%；
- robustness unseen spread = 0.2398%；
- all-instrument monotonicity train / validation / robustness = 0.9273 / 0.6970 / 0.9152。

负面证据：

- validation unseen valid instruments = 22；
- robustness unseen valid instruments = 35；
- validation unseen positive instrument share = 40.91%，低于 55%；
- validation unseen monotonicity = 0.3576；
- unseen concentration 在 validation / robustness 都失败。

结论：`vwap_deviation` 是本轮最强候选。它的时间迁移与 all-instrument monotonicity 最干净，unseen spread 方向也为正。但 unseen 样本过薄、positive instrument share 不够、unseen concentration 失败，因此不能授权 R09。

## 12. 与 R07 的关系

R07 最强横截面正例是：

```text
volume_price_correlation H3
validation spread = 0.333%
robustness spread = 0.170%
validation RankIC = 0.927%
robustness RankIC = 1.751%
```

本轮 R08 对它的对应结果：

| metric | validation | robustness |
|:--|--:|--:|
| all-instrument spread | 0.1734% | 0.1942% |
| seen spread | 0.1904% | 0.1577% |
| unseen spread | -0.1116% | 0.0973% |
| all-instrument monotonicity | 0.7091 | 0.9758 |
| unseen positive instrument share | 54.55% | 86.49% |

解释：

- robustness 方向与 R07 大体一致；
- validation all-instrument 为正，但 unseen 为负；
- 因此不能说 R07 的 cross-sectional residue 已经成功转译成 single-stock transferable state；
- 更准确的判断是：R07 的 vpc H3 信息在 R08 中有残留迹象，但跨股票迁移不稳定，且 unseen 样本太薄。

## 13. 核心 Insight

### Insight 1：降 direction 门槛是有信息增量的

从 100 降到 80 后，R08 不再是“完全无法构造 family state score”。三个 family 都能形成状态分数，并暴露出明确差异：

- `vwap_deviation`：最强、最干净；
- `volume_price_correlation`：有 R07 延续迹象，但 validation unseen 不确认；
- `volume_surge_money_flow`：更像 seen / stock-specific 行为。

这说明上一版 blocked 不是因为量价/VWAP family 完全无信息，而是 direction 门槛与当前 PIT 动态 universe 的 train split 厚度不匹配。

### Insight 2：R08 的真正瓶颈转移到了 unseen segment

unseen validation 有效股票数只有 22-33，robustness unseen 只有 34-37。这与 `valid_instrument_count_min = 100` 的 contract 明显冲突。

因此，当前 R08 不能诚实回答“跨股票可迁移吗”。它最多说明：

```text
all-instrument 口径能看到一些 H3 状态收益关系；
但 deterministic unseen segment 太薄，
无法把这些关系升级为 cross-instrument transferability evidence。
```

### Insight 3：`vwap_deviation` 是唯一值得保留观察的方向，但不能进入策略

`vwap_deviation` 的 all-instrument evidence 明显最好：

```text
validation spread = 0.2691%
robustness spread = 0.2606%
validation monotonicity = 0.6970
robustness monotonicity = 0.9152
validation unseen spread = 0.1698%
robustness unseen spread = 0.2398%
```

但它仍然失败在：

```text
validation unseen valid instruments = 22
validation unseen positive instrument share = 40.91%
validation unseen monotonicity = 0.3576
unseen concentration fail
```

所以它是“研究上最值得解释的信号”，不是 “R09 策略授权”。

### Insight 4：继续放松 sample gate 会改变问题性质

如果下一步把 `valid_instrument_count_min` 从 100 降到 30 或 50，R08 可能会产生更完整的 transfer table；但那已经不是原 R08 的严格 transferability audit，而是一个新的 thin-unseen-sample exploratory audit。

这类改动必须写成新的 requirement 或 explicit sensitivity audit，不能把本次 R08 的 blocked 决策直接改成 supported。

## 14. Required Questions

1. R08 是否避免了横截面 top20% 策略构造？是，没有 selected basket、top fraction 或 strategy return artifact。
2. 是否只研究 H3？是。
3. 是否只研究三个量价/VWAP family？是。
4. 单股内 percentile 是否 as-of safe？是，使用 prior 252 trading days，min history 126，mid-rank tie handling。
5. 状态方向是否只来自 train？是，且本版 direction 门槛为 80。
6. validation 是否有 high-low state spread？有。`vpc = 0.1734%`，`vsmf = -0.0101%`，`vwap = 0.2691%`。
7. robustness 是否确认？`vwap` 最稳定，`vpc` mean 为正但 median / sample 有问题，`vsmf` 不确认。
8. seen instruments 和 unseen instruments 表现是否一致？不一致。`vwap` spread 方向较一致，但 positive instrument share 和样本数不足；`vpc` validation unseen 为负；`vsmf` unseen 弱。
9. positive instrument share 是否足够？多数关键 unseen 切片不足，尤其 `vwap validation unseen = 40.91%`。
10. 是否只有少数股票贡献收益？all-instrument 口径 concentration 通过；unseen segment 多处失败。
11. 是否只有少数行业贡献收益？all-instrument 口径没有明显行业集中；unseen segment 样本薄，行业解释不稳。
12. 是否存在单股内 decile monotonicity？`vwap` all-instrument 稳定存在；`vpc` robustness 强但 validation 细分弱；`vsmf` 不稳定。
13. 哪个 family 的 transferability 最强？研究信号最强的是 `vwap_deviation`，但不满足 R08 transferability authorization。
14. 结果是可迁移状态信息、个股特异性，还是无支持？最终仍是 `r08_blocked_data_or_execution_contract`。若只看 family behavior，`vsmf` 更接近 stock-specific，`vwap` 最接近 transferable candidate。
15. 是否允许 R09 写 narrow strategy requirement？不允许。
16. `volume_price_correlation` 是否复现 R07 cross-sectional H3 evidence？部分复现，尤其 robustness；validation unseen 不确认。
17. Time-transfer train baseline 是否与 direction / bucket freezing 分离？是。
18. unseen segment date filtering 是否输出？是，本版 filtered rows 非零，且揭示 unseen segment 厚度不足。

## 15. Artifact Pointers

| artifact | role |
|:--|:--|
| `audit/r08_factor_direction_audit.csv` | direction 门槛降为 80 后的 factor 保留情况 |
| `audit/r08_factor_family_scope.csv` | family retained factor count |
| `audit/r08_transferability_sample_audit.csv` | 本轮最终阻断的关键证据 |
| `metrics/r08_time_transfer_summary.csv` | time transfer spread |
| `metrics/r08_seen_unseen_comparison.csv` | seen / unseen transfer 对比 |
| `metrics/r08_instrument_transfer_summary.csv` | positive instrument share 与 instrument-level spread |
| `metrics/r08_state_decile_monotonicity.csv` | decile monotonicity |
| `audit/r08_concentration_audit.csv` | instrument / industry concentration |
| `decision/r08_gate_inputs.csv` | family gate replay |
| `decision/r08_final_decision_replay.csv` | final first-match replay |
| `manifests/r08_validation.json` | validator 通过记录 |

Validator 状态：

```text
validation_status = passed
gate_count = 27
passed_gate_count = 27
failed_gate_count = 0
final_decision = r08_blocked_data_or_execution_contract
```
