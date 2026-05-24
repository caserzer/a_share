# R08.1 VWAP Deviation H3 K-Fold Transferability Sensitivity Audit 最终报告

## 1. 结论摘要

`final_decision = r08_1_no_vwap_kfold_transferability_support`

`authorized_strategy_requirement = false`

R08.1 的结论不是“没有读数”，而是：

```text
R08 的单次 unseen segment 样本过薄问题已经被 5-fold OOF 设计明显缓解；
vwap_deviation H3 单股内状态在 aggregate OOF 上有稳定正 spread；
但 validation positive instrument share、fold-level monotonicity、fold concentration
仍不足以支持“跨股票可迁移状态信息”。
```

因此 R08.1 不能授权任何 R09 strategy requirement，也不能把 `vwap_deviation H3` 作为 production signal 或 long-only alpha seed。它提供的是研究诊断结论：`vwap_deviation` 比 R08 单次 unseen 切分更有信息，但仍没有达到 transferability support 的纪律门槛。

最核心的五个事实：

| 项目 | 结果 | 判断 |
|:--|--:|:--|
| aggregate OOF sample status | `pass` | R08 的主要样本阻断被缓解 |
| validation OOF mean spread | `+0.2638%` | 正向，且高于 R08 单次 unseen 的 `+0.1698%` |
| robustness OOF mean spread | `+0.2484%` | 正向，接近 R08 单次 unseen 的 `+0.2398%` |
| validation positive instrument share | `52.49%` | 低于 gate `55%`，instrument transfer 不过 |
| validation fold monotonicity median | `0.3818` | 低于 fold-level gate `0.50`，monotonicity 不稳 |

## 2. 实验边界

R08.1 继承 R08 的执行边界：

```text
universe:
  PIT mcap500 mainboard universe

signal:
  weekly close-observed signal

execution:
  next-open entry
  H3 natural exit
  110bps round-trip cost

primary family:
  vwap_deviation

audit-only comparator:
  volume_price_correlation

primary state:
  within-stock 252d percentile

primary label:
  H3 self-relative net return

instrument transfer:
  deterministic sha256(instrument_id.lower()) mod 5
  each fold evaluated only on its unseen instruments
```

R08.1 没有构造任何策略、组合、top-N、top20%、top-decile basket、backtest、paper trading 或 production signal。

## 3. 数据可用性

Robustness 的声明窗口是 `2024-01-01 ~ 2025-12-31`，但本地可完成 H3 label 的最后 signal date 是 `2025-12-19`。

| 字段 | 值 |
|:--|:--|
| declared_robustness_end_date | `2025-12-31` |
| last_available_trading_date | `2026-04-30` |
| last_h3_label_complete_signal_date | `2025-12-19` |
| robustness_window_actual_end_date | `2025-12-19` |
| robustness_window_truncated_by_data_availability | `true` |
| robustness_actual_evaluable_year_count | `2` |
| robustness_actual_signal_date_count | `102` |

这个 truncation 不影响 R08.1 的主要解释，因为 robustness 仍包含 `2024` 和 `2025` 两个可评价年份；year-count gate 使用的是实际可用年份，而不是声明日历年份。

## 4. Factor Direction 与 Family Score

`vwap_deviation` 在 5 个 fold 中都保留了完整 `6 / 6` 个因子，没有发生 direction 阶段阻断。

| factor | fold valid instrument count range | direction stat range | direction |
|:--|--:|--:|:--|
| alpha018 | 116 ~ 125 | -0.0490 ~ -0.0367 | -1 |
| alpha027 | 116 ~ 125 | -0.0319 ~ -0.0137 | -1 |
| alpha041 | 116 ~ 125 | +0.0305 ~ +0.0374 | +1 |
| alpha095 | 116 ~ 125 | -0.0493 ~ -0.0436 | -1 |
| alpha144 | 116 ~ 125 | +0.0483 ~ +0.0582 | +1 |
| alpha156 | 116 ~ 125 | +0.0082 ~ +0.0188 | +1 |

这说明 R08.1 与 R08 最新版一致：当前瓶颈不是 factor direction 样本不足。`vwap_deviation` family score 可以稳定构造，且每个 fold 的 direction 都只来自 train years + seen folds。

`volume_price_correlation` comparator 也完整保留 `3 / 3` 个因子，但它只是 audit-only comparator，不参与 final decision。

## 5. Sample Gate：R08 的样本阻断已被缓解

R08 的核心失败点是单次 20% unseen segment 太薄：`vwap_deviation` validation unseen 只有 `22` 只有效股票，robustness unseen 只有 `35` 只有效股票。R08.1 改成 5-fold OOF 后，aggregate unseen full-valid instrument count 明显提高。

| family | split | full valid instruments | partial event-only instruments | valid dates | sample read |
|:--|:--|--:|--:|--:|:--|
| vwap_deviation | train_oof_unseen | 149 | 60 | 151 | 可评价 |
| vwap_deviation | validation_oof_unseen | 181 | 30 | 97 | 可评价 |
| vwap_deviation | robustness_oof_unseen | 188 | 20 | 91 | 可评价 |
| volume_price_correlation | validation_oof_unseen | 192 | 30 | 92 | comparator 可读 |
| volume_price_correlation | robustness_oof_unseen | 196 | 20 | 94 | comparator 可读 |

Fold-level sample：

| split | fold | valid instruments | partial instruments | valid dates | fold evaluable |
|:--|--:|--:|--:|--:|:--|
| validation | 0 | 29 | 9 | 35 | true |
| validation | 1 | 36 | 7 | 42 | true |
| validation | 2 | 37 | 7 | 31 | true |
| validation | 3 | 41 | 6 | 50 | true |
| validation | 4 | 38 | 1 | 40 | true |
| robustness | 0 | 32 | 3 | 23 | false |
| robustness | 1 | 42 | 3 | 42 | true |
| robustness | 2 | 34 | 5 | 37 | true |
| robustness | 3 | 44 | 7 | 49 | true |
| robustness | 4 | 36 | 2 | 37 | true |

Sample interpretation：

```text
validation:
  5 / 5 folds evaluable

robustness:
  4 / 5 folds evaluable
  fold 0 valid dates = 23, below fold-level 30-date floor

aggregate:
  aggregate_oof_sample_status = pass
  fold_coverage_caveat = false
```

所以 R08.1 已经不是 R08 那种 sample-blocked result。它进入了真正的 transferability gate 判断。

## 6. Aggregate OOF Unseen Readout

Primary `vwap_deviation` 的 aggregate OOF spread 明显为正，且 validation / robustness 都没有出现衰减到零以下。

| family | split | mean spread | median spread | pooled spread | positive date share | positive instrument share | valid instruments | valid dates | median IC | agg monotonicity |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| vwap_deviation | train_oof_unseen | +0.2499% | +0.2296% | +0.5230% | 54.97% | 71.14% | 149 | 151 | 0.0690 | 0.8909 |
| vwap_deviation | validation_oof_unseen | +0.2638% | +0.2381% | +0.1720% | 54.64% | 52.49% | 181 | 97 | 0.0316 | 0.7818 |
| vwap_deviation | robustness_oof_unseen | +0.2484% | +0.2808% | +0.7366% | 54.95% | 69.68% | 188 | 91 | 0.0710 | 0.9273 |
| volume_price_correlation | train_oof_unseen | +0.0338% | +0.0410% | +0.1751% | 51.66% | 50.67% | 150 | 151 | 0.0240 | 0.4909 |
| volume_price_correlation | validation_oof_unseen | +0.0301% | +0.1425% | +0.1311% | 52.17% | 56.77% | 192 | 92 | 0.0252 | 0.7212 |
| volume_price_correlation | robustness_oof_unseen | +0.1909% | +0.1153% | +0.8598% | 54.26% | 84.18% | 196 | 94 | 0.0866 | 0.9879 |

Key read:

```text
vwap_deviation:
  validation mean spread = +0.2638%
  robustness mean spread = +0.2484%
  validation vs train non-deterioration = pass
  robustness vs train non-deterioration = pass

但是:
  validation positive instrument share = 52.49%
  gate requirement = 55.00%
```

这个差距很小，但在 R08.1 contract 下不能放松。因为 R08.1 的目标不是找一个“看起来有 spread”的 family，而是判断是否有跨股票可迁移性。validation 中只有 `52.49%` 的 full-valid instruments 为正，说明收益关系仍然没有足够广泛地覆盖股票。

## 7. Year Readout

`vwap_deviation` 的 aggregate OOF 年度表现如下：

| split | year | mean spread | positive | valid dates |
|:--|--:|--:|:--|--:|
| train_oof_unseen | 2018 | -0.4026% | false | 24 |
| train_oof_unseen | 2019 | +0.3233% | true | 32 |
| train_oof_unseen | 2020 | +0.0320% | true | 44 |
| train_oof_unseen | 2021 | +0.6988% | true | 51 |
| validation_oof_unseen | 2022 | +0.5547% | true | 48 |
| validation_oof_unseen | 2023 | -0.0212% | false | 49 |
| robustness_oof_unseen | 2024 | +0.4665% | true | 44 |
| robustness_oof_unseen | 2025 | +0.0442% | true | 47 |

Interpretation:

```text
validation 的正 spread 主要来自 2022；
2023 基本接近 0，但略负；
robustness 的 2024 明显为正，2025 仍正但幅度较小。
```

这支持“有短周期状态读数”的判断，但不支持“跨年份完全 clean”的判断。尤其 `2023` 的轻微负值解释了为什么 validation 虽然 aggregate 为正，但不能把 R08.1 读成策略授权。

## 8. Fold Dispersion

`vwap_deviation` fold spread 的方向很稳定：validation 和 robustness 都是 `5 / 5` folds positive。

| split | fold | mean spread | median spread | positive inst share | valid instruments | valid dates | fold monotonicity | top1 inst share | top5 inst share |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| validation | 0 | +0.1603% | +0.8926% | 37.93% | 29 | 35 | 0.3818 | 11.34% | 38.36% |
| validation | 1 | +0.2219% | +0.2198% | 47.22% | 36 | 42 | 0.4182 | 11.58% | 38.67% |
| validation | 2 | +0.0039% | +0.0674% | 62.16% | 37 | 31 | 0.2848 | 6.41% | 25.26% |
| validation | 3 | +0.1933% | +0.1795% | 53.66% | 41 | 50 | 0.2000 | 17.51% | 37.72% |
| validation | 4 | +0.5769% | +0.8985% | 57.89% | 38 | 40 | 0.6970 | 10.29% | 38.81% |
| robustness | 0 | +0.1560% | -0.1048% | 65.63% | 32 | 23 | 0.5515 | 7.96% | 31.26% |
| robustness | 1 | +0.1021% | -0.1193% | 76.19% | 42 | 42 | 0.9515 | 8.06% | 31.30% |
| robustness | 2 | +0.2076% | +0.0713% | 50.00% | 34 | 37 | 0.9273 | 8.99% | 32.33% |
| robustness | 3 | +0.1532% | +0.0304% | 77.27% | 44 | 49 | 0.8545 | 8.96% | 30.02% |
| robustness | 4 | +0.2266% | +0.1950% | 75.00% | 36 | 37 | 0.7697 | 7.39% | 33.46% |

Fold stability gate itself passes:

| metric | validation | robustness | gate |
|:--|--:|--:|:--|
| positive_fold_count | 5 | 5 | pass |
| median_fold_spread | +0.1933% | +0.1560% | pass |
| min_fold_spread | +0.0039% | +0.1021% | pass |
| fold positive instrument share median | 53.66% | 75.00% | pass |

Important nuance:

```text
fold spread 方向稳定，不是 fold-fragile；
但 fold monotonicity 和 fold concentration 不稳定。
```

所以 final decision 不是 `r08_1_fold_fragile_vwap_state_candidate`。R08.1 的问题不是 spread 只靠某个 fold 正值拉起来，而是 fold 内状态排序不够顺、且 fold 内贡献集中度过高。

## 9. Monotonicity

Aggregate decile monotonicity 看起来较好：

```text
validation aggregate monotonicity = 0.7818
robustness aggregate monotonicity = 0.9273
```

但 final monotonicity gate 仍然失败，因为 R08.1 要求 aggregate + fold-level 都稳定。Fold-level median：

```text
validation fold_monotonicity_median = 0.3818
robustness fold_monotonicity_median = 0.8545

gate:
  fold_monotonicity_median_validation >= 0.50
```

Validation fold-level monotonicity 不达标，是 `monotonicity_gate_pass = false` 的直接原因。

Aggregate decile mean label：

| split | decile 1 | decile 5 | decile 10 | monotonicity | read |
|:--|--:|--:|--:|--:|:--|
| validation | -0.3710% | -0.2627% | -0.2590% | 0.7818 | 中高分位改善，但 top decile 没有明显抬升 |
| robustness | -0.2758% | +0.2888% | +0.5865% | 0.9273 | 更接近单调改善 |

Validation 的 decile 结构说明：

```text
低 decile 明显更差；
中高 decile 整体改善；
但 decile 8/9/10 没有形成干净递增。
```

这与 R08.1 的定位一致：`vwap_deviation` 有状态诊断信息，但还不是足以支持策略或 confirmatory pass 的单调状态函数。

## 10. Concentration

Aggregate concentration 本身并不差：

| family | split | top1 instrument | top5 instruments | top1 industry | industry overweight |
|:--|:--|--:|--:|--:|--:|
| vwap_deviation | train_oof_unseen | 1.74% | 7.74% | 9.59% | +2.22% |
| vwap_deviation | validation_oof_unseen | 4.06% | 12.51% | 9.86% | +2.71% |
| vwap_deviation | robustness_oof_unseen | 2.01% | 8.81% | 12.72% | +2.51% |

Aggregate top1/top5/industry 都低于 R08.1 hard gate：

```text
top1 instrument <= 5%
top5 instruments <= 20%
top1 industry <= 35%
```

但 fold-level concentration gate 失败。主要超标点：

| split | fold | top instrument | top1 share | top5 share | top industry | top industry share |
|:--|--:|:--|--:|--:|:--|--:|
| validation | 3 | SH600010 | 17.51% | 37.72% | sw_801040 | 17.51% |
| validation | 1 | SH600196 | 11.58% | 38.67% | sw_801740 | 15.88% |
| validation | 0 | SZ002920 | 11.34% | 38.36% | sw_801730 | 16.26% |
| validation | 4 | SZ002459 | 10.29% | 38.81% | sw_801730 | 20.21% |
| robustness | 4 | SH600438 | 7.39% | 33.46% | sw_801120 | 14.10% |

Fold concentration gate：

```text
max_fold_top1_instrument_contribution_share <= 15%
max_fold_top5_instrument_contribution_share <= 45%
max_fold_contribution_share_of_total_abs_contribution <= 35%
```

Observed：

```text
max fold top1 instrument share = 17.51%
max fold contribution share of total abs contribution = 11.72%
```

所以 concentration failure 主要不是 aggregate 被单一股票或行业支配，而是 validation fold 3 内部出现了单一 instrument 贡献超标。这一点很重要：R08.1 的 aggregate 读数更干净，但 fold 内仍有局部集中风险。

## 11. Gate Replay

Primary gate replay：

| gate | result | 关键数值 | 解释 |
|:--|:--|:--|:--|
| sample | pass | validation 181 instruments / robustness 188 instruments | R08 sample blocker 被缓解 |
| time_transfer | pass | val +0.2638%, robust +0.2484% | 相对 train 没有劣化 |
| instrument_transfer | fail | validation positive instrument share 52.49% < 55% | 股票覆盖不够广 |
| fold_stability | pass | val/robust 都 5/5 folds positive | spread 不是单 fold 偶然 |
| monotonicity | fail | validation fold mono median 0.3818 < 0.50 | fold 内状态排序不够顺 |
| concentration | fail | validation fold 3 top1 instrument share 17.51% > 15% | 局部贡献集中 |
| robustness_non_deterioration | pass | robust +0.2484% vs train +0.2499% | robustness 未明显衰减 |
| no_disallowed_caveat | false | concentration / monotonicity 不过 | 不允许 supported |

Decision replay：

| rule | condition | raw condition | selected |
|:--|:--|:--|:--|
| rule_01 | data / execution / scope / as-of / fold contract violation | false | false |
| rule_02 | primary vwap family cannot form fold-specific state score | false | false |
| rule_03 | aggregate_oof_sample_status = fail | false | false |
| rule_04 | non-fold gates pass but fold stability fails | false | false |
| rule_05 | time pass but instrument transfer fail, with other gates pass | false | false |
| rule_06 | all support gates pass | false | false |
| rule_07 | otherwise | true | true |

Selected rule：

```text
rule_07 -> r08_1_no_vwap_kfold_transferability_support
```

Why not fold-fragile：

```text
fold_stability_gate_pass = true
```

Why not time-transfer-only：

```text
instrument_transfer_gate_pass = false
but monotonicity_gate_pass = false
and concentration_gate_pass = false
```

Why not supported：

```text
instrument_transfer_gate_pass = false
monotonicity_gate_pass = false
concentration_gate_pass = false
```

## 12. 与 R08 的对照

R08 的 final decision 是：

```text
r08_blocked_data_or_execution_contract
reason = majority_family_sample_blocked
authorized_r09_flag = false
```

R08 中 `vwap_deviation` 的关键 unseen 读数：

| metric | R08 single unseen | R08.1 5-fold OOF | change |
|:--|--:|--:|:--|
| validation valid instruments | 22 | 181 | 样本厚度大幅改善 |
| robustness valid instruments | 35 | 188 | 样本厚度大幅改善 |
| validation unseen mean spread | +0.1698% | +0.2638% | 更强 |
| robustness unseen mean spread | +0.2398% | +0.2484% | 基本确认 |
| validation positive instrument share | 40.91% | 52.49% | 明显改善但仍低于 55% |
| robustness positive instrument share | 71.43% | 69.68% | 仍高 |

R08.1 的意义：

```text
R08 blocked 的确有很大一部分来自 single unseen split 太薄；
5-fold OOF 后，vwap_deviation 的正 spread 不是消失，而是增强；
但更厚样本同时暴露出一个关键事实：
validation 只有 52.49% 的股票贡献为正，仍不足以证明跨股票可迁移。
```

所以 R08.1 不是推翻 R08，而是把 R08 的 blocked 原因拆开了：

```text
sample blocker:
  resolved

transferability support:
  still not resolved
```

## 13. Comparator：volume_price_correlation

`volume_price_correlation` 是 audit-only comparator，不能替代 primary。

| metric | vwap_deviation | volume_price_correlation | read |
|:--|--:|--:|:--|
| validation mean spread | +0.2638% | +0.0301% | vwap 明显更强 |
| robustness mean spread | +0.2484% | +0.1909% | vwap 仍更强 |
| validation positive instrument share | 52.49% | 56.77% | vpc 股票覆盖略好 |
| robustness positive instrument share | 69.68% | 84.18% | vpc 股票覆盖更好 |
| validation fold stability | pass | pass | 两者都不是单 fold 偶然 |
| comparator_dominates_primary_flag | false | false | comparator 不支配 primary |

VPC 的现象：

```text
spread 不如 vwap_deviation；
positive instrument share 更好；
robustness spread 和 monotonicity 很强；
但 validation fold sample / monotonicity 仍不够干净。
```

这说明 R07/R08 里 `volume_price_correlation H3` 的信息残留并没有完全消失，但 R08.1 的 primary question 是 `vwap_deviation` sensitivity，不允许因为 comparator 表现不错而切换 primary family。

## 14. Findings

### Finding 1：R08.1 证明了 R08 的样本 blocker 不是“信号不存在”

R08 单次 unseen segment 太薄，`vwap_deviation` validation unseen 只有 22 只股票。R08.1 聚合 5 个 out-of-fold unseen readout 后，validation full-valid instruments 提升到 181，robustness 提升到 188，并且 aggregate sample status 变成 `pass`。

这说明 R08 的 blocked 不能解读为：

```text
vwap_deviation 没有任何单股状态信息。
```

更准确的解读是：

```text
R08 的 instrument transfer 评价设计太薄；
R08.1 解决样本厚度后，确实读到了正的状态收益关系。
```

### Finding 2：vwap_deviation 的 spread 稳定，但股票覆盖不足

`vwap_deviation` validation / robustness aggregate OOF spread 都约为 `+0.25%`，且 validation / robustness 都是 `5 / 5` folds positive。这个读数比 R08 更干净。

但是 validation positive instrument share 只有 `52.49%`，低于 `55%`。这说明正 spread 不是完全由一两个股票贡献，但也没有广泛到足以支持“跨股票可迁移”。

### Finding 3：validation 的问题主要在 2023 和 fold-level monotonicity

Validation 年度拆分：

```text
2022: +0.5547%
2023: -0.0212%
```

Validation aggregate decile monotonicity 虽然是 `0.7818`，但 fold-level monotonicity median 只有 `0.3818`。这意味着在全体聚合上能看到低位差、高位改善，但拆到 fold 后，状态排序不够稳定。

### Finding 4：concentration 的问题不是 aggregate，而是局部 fold

Aggregate concentration 全部通过硬阈值：

```text
validation aggregate top1 = 4.06%
validation aggregate top5 = 12.51%
validation aggregate top industry = 9.86%
```

真正的问题是 fold-level：

```text
validation fold 3 top1 instrument share = 17.51%
gate = 15%
```

这说明 R08.1 的 aggregate spread 不是明显被单一股票支配，但局部 fold 仍有贡献集中，不能宣称 clean transferability。

### Finding 5：vwap_deviation 比 VPC 更像 primary，但仍不够干净

VPC comparator 在 positive instrument share 上更强，但 spread 明显弱于 vwap：

```text
validation spread:
  vwap = +0.2638%
  vpc  = +0.0301%

robustness spread:
  vwap = +0.2484%
  vpc  = +0.1909%
```

因此 R08.1 没有理由把 primary 从 `vwap_deviation` 切换成 `volume_price_correlation`。Comparator 不支配 primary。

## 15. Insight

### Insight A：R08.1 把问题从“样本不足”推进到了“可迁移性不足”

这是 R08.1 最重要的信息增量。R08 卡在 sample blocker，R08.1 样本通过后，仍然没有 supported。这比 R08 的结论更强：

```text
不是因为完全看不到；
而是看到了以后，质量仍不够。
```

### Insight B：vwap_deviation 更像“状态诊断变量”，不像“可直接策略化变量”

`vwap_deviation` 在 validation / robustness 都有正 spread，说明它确实捕捉了某种单股内状态异常。但 gate 失败点显示，这种状态关系：

```text
不是所有股票都有效；
不是每个 fold 的 decile 结构都顺；
也不能完全排除局部股票贡献。
```

所以它更适合作为后续诊断维度，而不是直接变成 entry signal。

### Insight C：2023 仍是关键压力年

Validation aggregate 在 2022 很强，但 2023 轻微为负。这个模式与前面 EP5 多个实验中 2023 的压力一致：短周期状态信息在某些年份会衰减或反转。

如果后续继续研究，重点不应是再放松 gate，而是解释：

```text
2022 为什么有效？
2023 为什么失效？
2024/2025 为什么恢复？
```

### Insight D：不能用 aggregate monotonicity 掩盖 fold-level disorder

Aggregate monotonicity 达标很容易让结论看起来乐观，但 fold-level validation median monotonicity 只有 `0.3818`。这说明 R08.1 的 fold-level gate 是必要的：如果只看 aggregate，就会过度解读状态排序。

### Insight E：后续如果做 confirmatory diagnostic，目标应是解释结构，不是策略回测

R08.1 没有支持 R09 strategy。更合理的下一步如果要继续，应是 confirmatory diagnostic，例如：

```text
只针对 vwap_deviation H3；
解释 2023 失效；
解释 validation fold 0/1/3/4 的 concentration；
确认 positive instrument share 能否稳定超过 55%；
不引入交易策略、不调 threshold、不选股票。
```

## 16. Report Required Questions

1. R08.1 是否保持 diagnostic-only，且没有构造任何策略？是。没有 top-N、top20%、portfolio、backtest、paper trading 或 production signal。
2. 是否只把 `vwap_deviation` 作为 primary family？是。
3. 是否只研究 H3？是。
4. 5-fold instrument assignment 是否 deterministic 且 train 前冻结？是。使用 canonical repo-native instrument id 的 lowercase utf-8 bytes，sha256 digest first 8 bytes，mod 5。
5. 每个 fold 的 direction 是否只来自 train years + seen folds？是。
6. 每个 fold 的 state bucket edge 是否只来自 train years + seen folds？是。
7. 是否每只股票只在自己的 unseen fold 中参与 primary out-of-fold evaluation？是。
8. validation aggregate out-of-fold spread 是否为正？是，`+0.2638%`。
9. robustness aggregate out-of-fold spread 是否确认？是，`+0.2484%`。
10. validation / robustness aggregate positive instrument share 是否达标？validation 不达标，`52.49% < 55%`；robustness 达标，`69.68% >= 50%`。
11. 5 个 fold 中有多少 fold spread 为正？validation `5 / 5`，robustness `5 / 5`。
12. 最差 fold 的 spread 与 positive instrument share 是多少？validation 最差 spread fold 2 为 `+0.0039%`，positive instrument share `62.16%`；validation 最差 positive share fold 0 为 `37.93%`。
13. aggregate monotonicity 是否 >= 0.60？是。validation `0.7818`，robustness `0.9273`。
14. fold-level monotonicity 是否稳定？否。validation fold monotonicity median `0.3818 < 0.50`。
15. aggregate concentration 是否通过？aggregate 层面通过，但 final concentration gate 因 fold-level concentration 失败而不通过。
16. 是否有单一 fold、单一股票或单一行业贡献过大？有。validation fold 3 的 SH600010 top1 contribution share 为 `17.51%`，超过 `15%` fold gate。
17. `vwap_deviation` 相比 R08 单次 unseen split 的结果是否改善？是。validation instruments 从 `22` 增至 `181`，validation spread 从 `+0.1698%` 增至 `+0.2638%`。
18. `volume_price_correlation` comparator 是否只是 audit-only？是，不能影响 final decision。
19. 最终结果是 k-fold sensitivity supported、fold-fragile，还是 no support？`r08_1_no_vwap_kfold_transferability_support`。
20. 是否允许写 strategy requirement？不允许。
21. 如果结果 supported，允许的下一步 confirmatory diagnostic 是什么？本次没有 supported；理论上的 allowed next requirement 只能是 `confirmatory_vwap_state_transferability_diagnostic`，不是 strategy。
22. aggregate OOF metric 命名是否一致，gate 使用的是 mean / median spread 还是 pooled spread？一致。gate 使用 `aggregate_oof_unseen_mean_spread` 和 `aggregate_oof_unseen_median_spread`；pooled spread 是 report-only。
23. train_oof_unseen baseline 是否落盘并用于 non-deterioration replay？是。train OOF mean spread 为 `+0.2499%`。
24. robustness 实际可用结束日期是哪一天，是否发生 data availability truncation？实际结束日 `2025-12-19`，发生 truncation，但仍有 `2024/2025` 两个可评价年份。
25. fold coverage caveat path 是否触发，`aggregate_oof_sample_status` 是什么？未触发，`aggregate_oof_sample_status = pass`。
26. direction-insufficient factor 是否已从 retained set 中删除？是；本次 `vwap_deviation` 没有 direction-insufficient factor，保留 `6 / 6`。
27. `comparator_dominates_primary_flag` 是否为 true，它是否只作为 audit annotation？为 `false`；即使为 true，也只能作为 annotation。
28. partial instruments 是否只进入 event-level spread，且没有计入 sample gate 或 positive instrument denominator？是。
29. 如果 final decision 是 fold-fragile，是否确认 monotonicity、concentration、time transfer 与 aggregate instrument transfer 均已通过？本次不是 fold-fragile；rule_04 未触发，因为 monotonicity / concentration / instrument transfer 没有全部通过。

## 17. Artifact Pointers

| artifact | purpose |
|:--|:--|
| `decision/r08_1_final_decision.csv` | final decision |
| `decision/r08_1_gate_inputs.csv` | gate replay inputs |
| `decision/r08_1_final_decision_replay.csv` | first-match decision replay |
| `metrics/r08_1_aggregate_oof_unseen_state_spread.csv` | aggregate OOF spread / monotonicity / instrument share |
| `metrics/r08_1_fold_unseen_state_spread.csv` | fold-level spread / monotonicity / concentration |
| `metrics/r08_1_fold_dispersion_summary.csv` | fold dispersion summary |
| `metrics/r08_1_year_availability_and_positive_count.csv` | yearly spread and positive-year count |
| `audit/r08_1_concentration_audit.csv` | instrument / industry contribution decomposition |
| `audit/r08_1_factor_direction_by_fold_audit.csv` | train-seen-only factor direction |
| `audit/r08_1_data_availability_audit.csv` | robustness actual end-date audit |
| `manifests/r08_1_validation.json` | validator result |

Validator status:

```text
validation_status = passed
gate_count = 32
passed_gate_count = 32
failed_gate_count = 0
```
