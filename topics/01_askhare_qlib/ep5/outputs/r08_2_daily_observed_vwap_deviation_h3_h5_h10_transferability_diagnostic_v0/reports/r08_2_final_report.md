# R08.2 Daily-Observed VWAP Deviation H3/H5/H10 Transferability Diagnostic 最终报告

## 1. 结论摘要

`final_decision = r08_2_daily_vwap_h3_transferability_diagnostic_supported`

`authorized_strategy_requirement = false`

R08.2 的结论是：

```text
daily close-observed 的 vwap_deviation 单股内状态，
在 H3 primary label 上通过了 overlap-controlled、5-fold OOF、instrument transfer、
fold stability、anchor stability、monotonicity、concentration 和 robustness non-deterioration gates。

但 R08.2 仍然是 diagnostic-only audit，不授权任何 strategy requirement。
```

这版最重要的信息增量是：

```text
R08.1 weekly signal 下，vwap_deviation H3 有正 spread，
但 validation positive instrument share、fold-level monotonicity、fold-level concentration 不够干净。

R08.2 改成 daily signal 后，
样本密度显著增加，H3 的 fold-level monotonicity 和 concentration 同时改善，
不再只是“spread 好看但 cleanliness 不过”。
```

Primary decision 只来自：

```text
family:
  vwap_deviation

primary horizon:
  H3

signal observation:
  daily close-observed

execution:
  next-open entry
  H3 natural exit
  110bps round-trip cost

label:
  H3 self-relative net return

transfer design:
  5-fold instrument OOF unseen
  anchor-offset overlap control
```

H5/H10 只是 diagnostic labels。它们不能替代 H3，不能 rescue H3，也不能授权 horizon switching。

## 2. 为什么 R08.2 有必要

R08.1 已经回答了一个关键问题：R08 的单次 20% unseen 切分太薄，5-fold OOF 可以缓解样本问题。但 R08.1 仍然没有授权，因为 weekly H3 的证据链不够干净：

| 项目 | R08.1 weekly H3 | R08.2 daily H3 | 变化 |
|:--|--:|--:|:--|
| validation full-valid instruments | 181 | 242 | 样本厚度增加 |
| robustness full-valid instruments | 188 | 232 | 样本厚度增加 |
| validation valid dates | 97 | 477 | 时间样本显著增加 |
| robustness valid dates | 91 | 433 | 时间样本显著增加 |
| validation mean spread | +0.2638% | +0.2710% | spread 基本延续 |
| robustness mean spread | +0.2484% | +0.2178% | 稍弱但仍为正 |
| validation positive instrument share | 52.49% | 69.01% | 从不过门变为过门 |
| robustness positive instrument share | 69.68% | 75.86% | 进一步改善 |
| validation fold monotonicity median | 0.3818 | 0.7091 | 从不过门变为过门 |
| robustness fold monotonicity median | 0.8545 | 0.6121 | 仍过门 |

所以 R08.2 不是换 family、换 primary horizon 或换交易目标；它只检验一个很具体的问题：

```text
R08.1 的 weekly observation 是否过稀，
导致 H3 状态关系在 fold-level 和 monotonicity 上被低估？
```

当前结果支持这个判断：daily 观察没有制造一个全新的信号，而是把 R08.1 已经存在的 vwap_deviation H3 正向关系变得更可评价、更广泛、更干净。

## 3. 数据与执行边界

R08.2 使用 R06/R05 daily feature cache 构建 daily signal panel。weekly panel 没有作为 primary signal 使用。

| 字段 | 值 |
|:--|:--|
| source | `r06_cache/r05_daily_feature_panel` |
| candidate rows | 416,393 |
| instrument count | 506 |
| signal date count | 2,064 |
| min signal date | 2017-07-04 |
| max signal date | 2025-12-31 |
| primary family | `vwap_deviation` |
| primary horizon | H3 |
| diagnostic horizons | H5; H10 |

Split 级 daily signal panel：

| split | event count | instruments | daily signal dates | date range | daily signal | weekly not primary |
|:--|--:|--:|--:|:--|:--|:--|
| train | 196,252 | 422 | 1,096 | 2017-07-04 ~ 2021-12-31 | true | true |
| validation | 109,722 | 323 | 483 | 2022-01-04 ~ 2023-12-29 | true | true |
| robustness | 110,419 | 342 | 485 | 2024-01-02 ~ 2025-12-31 | true | true |

Robustness 声明窗口到 2025-12-31，但按不同 horizon 的 label 完成日期有自然截断：

| horizon | declared end | last available trading date | last label-complete signal date | actual end | truncated | evaluable years | actual signal dates |
|:--|:--|:--|:--|:--|:--|--:|--:|
| H3 | 2025-12-31 | 2025-12-31 | 2025-12-25 | 2025-12-25 | true | 2 | 481 |
| H5 | 2025-12-31 | 2025-12-31 | 2025-12-23 | 2025-12-23 | true | 2 | 479 |
| H10 | 2025-12-31 | 2025-12-31 | 2025-12-16 | 2025-12-16 | true | 2 | 474 |

这个 truncation 是 H3/H5/H10 exit 日期导致的正常 label-completion 约束，不是数据缺失导致的样本失败；2024 和 2025 都满足可评价年份要求。

## 4. As-Of 与标签安全性

R08.2 的主要 as-of 约束都通过：

| horizon | split | events | complete labels | self-relative labels | industry-relative labels | completed-only | exit <= D-1 |
|:--|:--|--:|--:|--:|--:|:--|:--|
| H3 | train | 196,252 | 192,308 | 178,884 | 84,856 | true | true |
| H3 | validation | 109,722 | 107,627 | 106,126 | 62,171 | true | true |
| H3 | robustness | 110,419 | 108,113 | 104,988 | 66,354 | true | true |
| H5 | train | 196,252 | 190,958 | 176,978 | 83,884 | true | true |
| H5 | validation | 109,722 | 106,823 | 105,204 | 61,547 | true | true |
| H5 | robustness | 110,419 | 107,245 | 104,054 | 65,660 | true | true |
| H10 | train | 196,252 | 188,147 | 172,837 | 82,005 | true | true |
| H10 | validation | 109,722 | 105,024 | 103,146 | 60,233 | true | true |
| H10 | robustness | 110,419 | 105,284 | 101,840 | 63,870 | true | true |

Within-stock normalization 使用每只股票 D-1 之前的 252 个交易日作为 reference distribution，并使用 mid-rank tie handling。没有 cross-stock fill，也没有使用未来数据。

## 5. Factor Direction 与 Family Score

`vwap_deviation` 的 6 个 in-scope 因子全部可用，5 个 fold 均保留 `6 / 6`。Direction 只来自 train years + seen folds + H3 anchor-controlled stats；full daily overlapping stats 只作为参考，不决定方向。

| factor | valid instrument count range | anchor-median direction stat range | direction | anchor stability |
|:--|--:|--:|--:|:--|
| alpha018 | 175 ~ 191 | -0.0393 ~ -0.0343 | -1 | 5 / 5 |
| alpha027 | 175 ~ 191 | -0.0448 ~ -0.0386 | -1 | 5 / 5 |
| alpha041 | 175 ~ 191 | +0.0152 ~ +0.0203 | +1 | 5 / 5 |
| alpha095 | 175 ~ 191 | -0.0775 ~ -0.0727 | -1 | 5 / 5 |
| alpha144 | 175 ~ 191 | +0.0696 ~ +0.0777 | +1 | 5 / 5 |
| alpha156 | 175 ~ 191 | +0.0155 ~ +0.0229 | +1 | 5 / 5 |

解释：

```text
Direction 阶段不是瓶颈。
6 个 vwap_deviation 因子方向在所有 fold 中都稳定，
而且方向来自 H3 anchor-controlled train-seen 口径。
```

Train-seen frozen bucket edges 是 fold-specific 的 daily 20/60/20 extreme-tail bucket，不使用 validation/robustness 调阈值。各 fold 的 q20 大约在 `0.312 ~ 0.317`，q80 大约在 `0.642 ~ 0.644`。

## 6. H3 Anchor-Controlled Primary Readout

H3 primary readout 使用 anchor offset 控制 daily overlapping labels。H3 有 3 个 anchor offset；validation 和 robustness 中 3 个 offset 全部为正。

| split | mean spread | median spread | anchor min | anchor median | positive anchors | positive inst share | full-valid instruments | valid dates | monotonicity | full-anchor conflict |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| train_oof_unseen | +0.3685% | +0.1785% | +0.3479% | +0.3764% | 3 / 3 | 76.85% | 203 | 819 | 1.0000 | false |
| validation_oof_unseen | +0.2710% | +0.1833% | +0.2419% | +0.2729% | 3 / 3 | 69.01% | 242 | 477 | 0.8909 | false |
| robustness_oof_unseen | +0.2178% | +0.1637% | +0.1695% | +0.2002% | 3 / 3 | 75.86% | 232 | 433 | 0.7212 | false |

这里最重要的是三点：

```text
1. validation 和 robustness 的 H3 mean spread 都为正；
2. 每个 H3 anchor offset 都为正，说明不是重叠 daily label 造成的单一路径幻觉；
3. positive instrument share 从 R08.1 的 validation 52.49% 提升到 69.01%，跨股票覆盖明显改善。
```

Full daily 与 anchor-controlled 没有方向冲突。full daily 与 anchor-controlled 的 spread gap 约为 `-0.000118%` 到 `+0.000152%`，基本可以忽略。

## 7. H3 年度读数

H3 在 validation 和 robustness 的每个可评价年份都为正：

| split | year | mean spread | positive | valid signal dates |
|:--|--:|--:|:--|--:|
| train_oof_unseen | 2018 | +0.4824% | true | 193 |
| train_oof_unseen | 2019 | +0.4165% | true | 174 |
| train_oof_unseen | 2020 | +0.1234% | true | 213 |
| train_oof_unseen | 2021 | +0.4601% | true | 239 |
| validation_oof_unseen | 2022 | +0.4730% | true | 239 |
| validation_oof_unseen | 2023 | +0.0678% | true | 238 |
| robustness_oof_unseen | 2024 | +0.2091% | true | 211 |
| robustness_oof_unseen | 2025 | +0.2265% | true | 222 |

2023 明显偏弱，但仍为正。这一点和 R08.1/R05 中对 2023 反转环境的担忧一致：daily vwap_deviation 并不是每年同等强，但没有在 2023 变成负数。

## 8. Fold-Level Transferability

H3 5-fold OOF 的 fold-level readout：

| split | fold | mean spread | min anchor spread | positive anchors | positive inst share | instruments | dates | monotonicity | top1 contrib | top5 contrib |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| validation | 0 | +0.3680% | +0.1636% | 3 / 3 | 65.91% | 44 | 211 | 0.7091 | 9.29% | 29.19% |
| validation | 1 | +0.2782% | +0.0574% | 3 / 3 | 71.15% | 52 | 239 | 0.6000 | 9.70% | 32.37% |
| validation | 2 | -0.0731% | -0.2616% | 1 / 3 | 63.27% | 49 | 197 | 0.6121 | 7.16% | 26.33% |
| validation | 3 | +0.1675% | +0.1122% | 3 / 3 | 71.15% | 52 | 278 | 0.8667 | 10.56% | 34.53% |
| validation | 4 | +0.2808% | +0.1079% | 3 / 3 | 73.33% | 45 | 237 | 0.7697 | 10.01% | 34.75% |
| robustness | 0 | +0.0763% | -0.0004% | 2 / 3 | 78.95% | 38 | 173 | 0.6364 | 9.27% | 32.73% |
| robustness | 1 | +0.1220% | -0.0733% | 2 / 3 | 75.00% | 48 | 220 | 0.5515 | 9.39% | 27.40% |
| robustness | 2 | +0.3315% | +0.1707% | 3 / 3 | 70.83% | 48 | 213 | 0.5636 | 6.66% | 29.64% |
| robustness | 3 | +0.3045% | +0.2297% | 3 / 3 | 83.64% | 55 | 264 | 0.9030 | 4.55% | 21.29% |
| robustness | 4 | +0.1666% | +0.1347% | 3 / 3 | 69.77% | 43 | 189 | 0.6121 | 5.95% | 27.13% |

Fold dispersion summary：

| split | evaluable folds | positive folds | median fold spread | min fold spread | fold positive inst share median | fold mono median | mono positive folds | max top1 | max top5 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train_oof_unseen | 5 | 5 | +0.1738% | +0.0250% | 78.05% | 0.9152 | 5 | 18.30% | 36.67% |
| validation_oof_unseen | 5 | 4 | +0.2782% | -0.0731% | 71.15% | 0.7091 | 5 | 10.56% | 34.75% |
| robustness_oof_unseen | 5 | 5 | +0.1666% | +0.0763% | 75.00% | 0.6121 | 5 | 9.39% | 32.73% |

解释：

```text
validation fold 2 是唯一负 spread fold，mean spread = -0.0731%。
但该 fold 的 positive instrument share 仍有 63.27%，decile monotonicity = 0.6121。
因此它更像 fold-specific weak spread，而不是完全反向的 transfer failure。

robustness 5 个 fold 全部正，且 concentration 没有超门槛。
```

## 9. Monotonicity 结构

H3 decile monotonicity 在 aggregate anchor-controlled 口径下通过。Decile mean label 显示 high-state 区间整体优于 low-state 区间。

| split | decile monotonicity | decile 1 mean | decile 5 mean | decile 10 mean | interpretation |
|:--|--:|--:|--:|--:|:--|
| train_oof_unseen | 1.0000 | -0.4280% | -0.1772% | +0.3003% | clean monotonic |
| validation_oof_unseen | 0.8909 | -0.3974% | -0.0975% | +0.0177% | mostly monotonic, upper tail weaker |
| robustness_oof_unseen | 0.7212 | -0.4050% | +0.1579% | +0.3091% | low state clearly bad, mid/high more noisy |

这和 R08.1 的关键区别在于：R08.1 validation fold-level monotonicity median 只有 `0.3818`，R08.2 validation 提升到 `0.7091`。这说明 daily 观察不仅增加样本，还改善了状态分桶后的排序结构。

## 10. Concentration 与行业暴露

H3 aggregate concentration 明显低于 fold-level 约束：

| split | aggregate top1 instrument | top1 share | top5 share | top1 industry | top1 industry share |
|:--|:--|--:|--:|:--|--:|
| train_oof_unseen | SZ002459 | 4.20% | 10.05% | sw_801080 | 9.71% |
| validation_oof_unseen | SH600010 | 2.41% | 10.11% | sw_801730 | 11.67% |
| robustness_oof_unseen | SH603259 | 1.93% | 7.45% | sw_801080 | 11.61% |

Fold-level 最大值：

| split | max fold top1 | max fold top5 | gate read |
|:--|--:|--:|:--|
| train_oof_unseen | 18.30% | 36.67% | train reference，不决定 validation support |
| validation_oof_unseen | 10.56% | 34.75% | pass |
| robustness_oof_unseen | 9.39% | 32.73% | pass |

R08.2 的 supported 不是由少数单股贡献出来的。validation/robustness 的 aggregate top1 contribution 都低于 2.5%，fold-level top1 也低于 15% gate。

## 11. H5/H10 Diagnostic Readout

H5/H10 只用于 horizon-shape diagnostic，不参与 H3 direction、bucket edge、factor retention，也不能改变 primary final decision。

| horizon | split | mean spread | median spread | pooled spread | positive date share | valid dates | event count | full-valid instruments | positive inst share | median IC | monotonicity |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| H5 | train | +0.5207% | +0.3171% | +0.9155% | 55.72% | 813 | 162,059 | 202 | 81.19% | 0.0790 | 0.9879 |
| H5 | validation | +0.4416% | +0.4246% | +0.5302% | 57.89% | 475 | 104,386 | 239 | 71.13% | 0.0582 | 0.8909 |
| H5 | robustness | +0.2858% | +0.2176% | +0.8369% | 53.13% | 431 | 102,783 | 230 | 74.78% | 0.0752 | 0.9636 |
| H10 | train | +0.6862% | +0.2836% | +1.3980% | 52.79% | 807 | 158,933 | 198 | 80.30% | 0.0831 | 0.9879 |
| H10 | validation | +0.8373% | +0.4256% | +1.0883% | 55.53% | 470 | 102,442 | 237 | 76.37% | 0.0833 | 0.9636 |
| H10 | robustness | +0.3754% | +0.1029% | +1.5398% | 51.88% | 426 | 100,663 | 227 | 77.53% | 0.0897 | 0.8545 |

Horizon diagnostic gate：

| horizon | validation spread | robustness spread | validation inst share | robustness inst share | validation anchors | robustness anchors | validation top1 | robustness top1 | diagnostic positive |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| H5 | +0.4417% | +0.2879% | 71.13% | 74.78% | 5 / 5 | 5 / 5 | 1.95% | 1.70% | true |
| H10 | +0.8393% | +0.3795% | 76.37% | 77.53% | 10 / 10 | 8 / 10 | 1.77% | 1.78% | true |

Horizon shape：

| split | H3 | H5 | H10 | H5-H3 | H10-H3 | sign pattern |
|:--|--:|--:|--:|--:|--:|:--|
| validation_oof_unseen | +0.2710% | +0.4417% | +0.8393% | +0.1707% | +0.5684% | +/+/+ |
| robustness_oof_unseen | +0.2178% | +0.2879% | +0.3795% | +0.0700% | +0.1616% | +/+/+ |

Interpretation：

```text
R08.2 没有显示“只在 H3 后立刻消失”的短寿命形态。
H5/H10 diagnostic 都为正，说明 vwap_deviation 的单股状态更像 persistent state relation，
而不是单日噪声或 H3-only micro effect。

但这不改变 primary horizon。
H5/H10 如果要成为 primary，必须另写 confirmatory requirement。
```

## 12. Gate Replay

全部 H3 primary gates 通过：

| gate | value |
|:--|:--|
| primary_score_formed_flag | true |
| daily_panel_sample_gate_pass | true |
| aggregate_oof_sample_status | pass |
| fold_coverage_caveat | false |
| validation_evaluable_fold_count | 5 |
| robustness_evaluable_fold_count | 5 |
| validation_full_valid_instrument_count | 242 |
| robustness_full_valid_instrument_count | 232 |
| validation_valid_signal_date_count | 477 |
| robustness_valid_signal_date_count | 433 |
| H3_time_transfer_gate_pass | true |
| H3_instrument_transfer_gate_pass | true |
| H3_fold_stability_gate_pass | true |
| H3_anchor_stability_gate_pass | true |
| H3_monotonicity_gate_pass | true |
| H3_concentration_gate_pass | true |
| H3_robustness_non_deterioration_pass | true |
| no_disallowed_caveat_active | true |
| H5_diagnostic_horizon_positive | true |
| H10_diagnostic_horizon_positive | true |
| authorized_strategy_requirement | false |

Final decision replay：

| rule | condition | raw condition | selected | decision |
|:--|:--|:--|:--|:--|
| rule_01 | data / execution / scope / as-of / fold contract violation | false | false | blocked data/execution |
| rule_02 | primary vwap family cannot form fold-specific state score | false | false | sample insufficient |
| rule_03 | aggregate OOF sample fails or H3 anchor sample gate fails | false | false | sample insufficient |
| rule_04 | all non-fold H3 support gates pass and fold stability fails | false | false | fold-fragile candidate |
| rule_05 | time transfer passes, instrument transfer fails, other H3 cleanliness gates pass | false | false | time-transfer-only |
| rule_06 | all H3 support gates pass | true | true | diagnostic supported |
| rule_07 | H3 fails but H5/H10 diagnostic passes | false | false | horizon mismatch only |
| rule_08 | otherwise | true | false | no support |

## 13. Findings

### Finding 1：daily observation 不是简单提高 spread，而是改善了 transfer cleanliness

R08.1 weekly H3 已经有正 spread：

```text
validation mean spread = +0.2638%
robustness mean spread = +0.2484%
```

但 R08.1 卡在：

```text
validation positive instrument share = 52.49% < 55%
validation fold monotonicity median = 0.3818
monotonicity gate fail
concentration gate fail
```

R08.2 daily H3 的 validation mean spread 只是从 `+0.2638%` 到 `+0.2710%`，并不是大幅膨胀；真正变化是：

```text
validation positive instrument share = 69.01%
validation fold monotonicity median = 0.7091
validation max fold top1 contribution = 10.56%
```

这说明 daily observation 的信息增量主要在“样本密度和状态排序稳定性”，不是把 point estimate 人为抬高。

### Finding 2：H3 anchor 控重后仍然全部为正

H3 validation 三个 anchor offset 的 mean spread 分别为：

```text
anchor 0: +0.2981%
anchor 1: +0.2729%
anchor 2: +0.2419%
```

H3 robustness 三个 anchor offset 的 mean spread 分别为：

```text
anchor 0: +0.1695%
anchor 1: +0.2002%
anchor 2: +0.2838%
```

这很关键。daily label 有 overlap 风险，如果只看 full daily pooled readout，可能夸大 confidence；但 anchor offset 切开后，每条互不重叠路径仍然为正。

### Finding 3：2023 弱，但不是反向

R08.2 validation 年度 readout：

```text
2022: +0.4730%
2023: +0.0678%
```

2023 很弱，接近零，但没有翻负。因此 R08.2 的 positive-year gate 不是靠单一年份撑出来的。它反映的是：

```text
强年份有明显 spread；
弱年份仍保留正向状态关系；
跨年关系没有断裂。
```

### Finding 4：H5/H10 显示状态可能持续，而不是 H3-only

Horizon shape 是：

```text
validation: H3 +0.2710%, H5 +0.4417%, H10 +0.8393%
robustness: H3 +0.2178%, H5 +0.2879%, H10 +0.3795%
```

这不是典型的 H3 短促脉冲形态。更合理的解释是：

```text
vwap_deviation 的 within-stock 状态可能对应一个持续数日的状态修复 / 状态延续过程。
```

但 H10 robustness 的 anchor offset 中只有 `8 / 10` 个为正，且 H10 是 diagnostic-only，所以不能据此直接切换 primary horizon。

### Finding 5：R08.2 仍然不是策略 pass

`diagnostic_supported` 的含义是：

```text
在当前 daily-observed audit contract 下，
vwap_deviation H3 单股内状态存在跨股票、跨年份、overlap-controlled 的可迁移诊断证据。
```

它不等价于：

```text
可以交易；
可以做 long-only alpha；
可以做 top-N portfolio；
可以生产 signal；
可以写 strategy requirement。
```

下一步只能是 confirmatory diagnostic requirement，而不是 R09 strategy。

## 14. Insight

### Insight A：R08.2 把 EP5 的问题从“有没有读数”推进到“是否可确认”

R07 的状态是：

```text
横截面 pocket 存在，但 clean attribution / monotonicity / state stability 不过。
```

R08 的状态是：

```text
single-stock state 方向有读数，但 unseen segment 太薄，blocked。
```

R08.1 的状态是：

```text
5-fold 缓解样本问题，但 weekly H3 cleanliness 不够。
```

R08.2 的状态是：

```text
daily + anchor control 后，H3 transferability diagnostic supported。
```

这说明 EP5 的后续问题不再是“继续横截面搜索”，而是：

```text
daily vwap_deviation H3 的单股内状态关系，
能否在更严格的 confirmatory setup 中复现？
```

### Insight B：信号强度不大，但 breadth 明显好于 R08.1

H3 validation/robustness mean spread 约 `+0.22% ~ +0.27%`，不是大信号。但 positive instrument share 在 validation/robustness 分别为 `69.01% / 75.86%`，说明它不是由少数股票拉出来的。

这类结构更适合继续做 diagnostic confirmation，而不是马上进入策略设计。原因是：

```text
spread 不大，执行成本和换手路径可能很快吃掉收益；
但 breadth 和 monotonicity 已经足够值得确认。
```

### Insight C：H5/H10 强于 H3 是机会，也是风险

H5/H10 diagnostic 更强，尤其 validation H10 达到 `+0.8393%`。但这也带来两个风险：

```text
1. 如果后续直接切 H10，就是 horizon shopping；
2. 如果 H10 只是同一状态的延长读数，可能包含更多市场/行业状态成分。
```

所以正确下一步不是“改做 H10 策略”，而是：

```text
在 confirmatory diagnostic 中继续把 H3 作为 primary，
同时保留 H5/H10 作为 shape evidence。
```

### Insight D：R08.2 的 supported 应该被视为“研究解封”，不是“策略授权”

R08.2 通过了所有 H3 diagnostic gates，这足以解除 R08/R08.1 的方法学阻断。但它还没有解决：

```text
交易组合构造；
容量；
换手；
行业中性；
beta / liquidity decomposition；
realized cost sensitivity；
entry/exit path；
signal overlap in actual portfolio holding；
post-entry drawdown control。
```

因此 R08.2 最多允许一个更严格的 confirmatory diagnostic requirement，不能直接进入 production 或 strategy requirement。

## 15. 必答问题

1. R08.2 是否保持 diagnostic-only，且没有构造任何策略？
   是。`authorized_strategy_requirement = false`。

2. 是否把 signal frequency 从 weekly 改成 daily？
   是。Primary signal 是 daily close-observed，weekly panel 没有作为 primary 使用。

3. 是否只把 `vwap_deviation` 作为 primary family？
   是。可用因子为 `alpha018; alpha027; alpha041; alpha095; alpha144; alpha156`。

4. 是否只把 H3 作为 primary horizon？
   是。H3 是唯一 primary decision horizon。

5. H5/H10 是否只作为 diagnostic labels？
   是。H5/H10 不参与 direction、bucket edge、factor retention 或 final support rescue。

6. daily signal panel 是否 PIT / as-of safe？
   是。daily_trading_calendar_index 全市场共用、跨 split 连续，normalization 使用 D-1 前 252 日。

7. H3/H5/H10 self-relative labels 是否只使用 completed labels？
   是。`self_relative_label_lookback_exit_date_le_D_minus_1 = true`。

8. daily overlapping label 是否被显式控制？
   是。H3 用 3 个 anchor offset，H5 用 5 个，H10 用 10 个。

9. H3 anchor offsets 是否全部可评价？
   是。validation/robustness 的 H3 anchor offset 全部为正且可评价。

10. 5-fold instrument assignment 是否 deterministic 且 train 前冻结？
    是。hash input 是 canonical instrument id lowercase 的 utf-8 bytes。

11. direction 是否只来自 train years + seen folds + H3？
    是，并且使用 H3 anchor-controlled train-seen stats。

12. validation H3 anchor-controlled spread 是否为正？
    是，`+0.2710%`。

13. robustness H3 anchor-controlled spread 是否确认？
    是，`+0.2178%`。

14. validation / robustness H3 positive instrument share 是否达标？
    是，分别为 `69.01%` 和 `75.86%`。

15. H3 fold stability 是否达标？
    是。validation `4 / 5` fold 为正，robustness `5 / 5` fold 为正。

16. H3 anchor stability 是否达标？
    是。validation/robustness 都是 `3 / 3` anchor 为正。

17. H3 monotonicity 是否达标？
    是。validation aggregate monotonicity `0.8909`，robustness `0.7212`；fold median 分别为 `0.7091` 和 `0.6121`。

18. H3 concentration 是否达标？
    是。validation max fold top1 `10.56%`，robustness max fold top1 `9.39%`。

19. H5 diagnostic label 的状态如何？
    Positive。validation spread `+0.4417%`，robustness spread `+0.2879%`。

20. H10 diagnostic label 的状态如何？
    Positive。validation spread `+0.8393%`，robustness spread `+0.3795%`。

21. Horizon shape 是 short-lived、persistent、horizon-mismatch 还是 no-support？
    更接近 persistent diagnostic shape。H3/H5/H10 在 validation 和 robustness 都为正。

22. 如果 H5/H10 强于 H3，是否改变 primary final decision？
    不改变。H3 仍是 primary，H5/H10 不能触发 horizon switching。

23. 结果相比 R08.1 weekly H3 是否改善？
    是。主要改善在 sample density、positive instrument breadth、fold-level monotonicity 和 concentration cleanliness。

24. final decision 是什么？
    `r08_2_daily_vwap_h3_transferability_diagnostic_supported`。

25. 是否允许写 strategy requirement？
    不允许。

26. 如果 supported，允许的下一步是什么？
    只允许 `confirmatory_daily_vwap_h3_transferability_diagnostic`，不是 strategy。

## 16. 建议的下一步

R08.2 不应直接进入策略设计。建议下一步写一个 confirmatory diagnostic requirement，目标是确认：

```text
daily vwap_deviation H3 within-stock state relation
是否在更严格的 confirmatory setup 中仍然成立。
```

建议 confirmatory diagnostic 至少包含：

```text
1. 继续固定 primary family = vwap_deviation；
2. 继续固定 primary horizon = H3；
3. 继续使用 daily close-observed signal；
4. 继续使用 anchor-offset overlap control；
5. 不允许根据 R08.2 结果选择新 horizon；
6. H5/H10 继续只做 shape diagnostic；
7. 增加 beta / industry / liquidity decomposition；
8. 增加 cost sensitivity，但仍不构造 strategy；
9. 检查 H3 relation 是否由 gap、limit、停牌、低流动性或行业状态驱动；
10. 只有 confirmatory diagnostic 再次通过，才讨论是否写 narrow strategy feasibility requirement。
```

一句话：

```text
R08.2 已经把 daily vwap_deviation H3 从 exploratory diagnostic 推到 supported diagnostic；
但它仍然不是 strategy pass。
```
