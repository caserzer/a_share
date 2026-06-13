# Experiment I - Transition Previous-Regime Context Cost Rejector Ablation 报告

最终决策：`transition_previous_regime_context_cost_rejector_diagnostic_no_uplift`

Non-pass reason：`robustness_or_validation_uplift_gate_not_met`

## 1. 实验定位

本实验只回答一个窄问题：

> 在 transition universe 内，把 t0 可见的 previous-regime context 加入 cost rejector，是否能相对同一套 t0 feature 的 no-context baseline 稳定改善 `cost_bad_10_20` 排序？

结论是：**不能**。

更准确地说，`pit_transition_context` 在 train 内部和 segment-CV 上看起来有局部增益，但这个增益没有穿过 validation / robustness。OOS 上，加入 previous-regime context 后 ROC-AUC、PR-AUC、top-decile lift、robustness cost reduction、robustness recall retention 均弱于 no-context baseline。因此 I 只能作为 diagnostic ablation，不能升级为 research-entry，也不能并入 H/E 的 risk_on-only gate。

本实验没有训练 conversion / continuation classifier。`transition_outcome_label`、`transition_outcome_direction`、`next_non_transition_regime` 只用于 ex-post readout，没有进入模型、threshold selection 或 final gate。

## 2. 上游绑定与数据完整性

上游状态：

| upstream | decision / role |
| --- | --- |
| G | `transition_previous_regime_conditioning_diagnostic_only` |
| H | `risk_on_cost_rejector_diagnostic_only_or_no_candidate` |
| D | `post_replay_retention_source_source_caveated_complete` |
| E | `risk_on_cost_rejector_feature_source_caveated_supported` |

Primary universe 来自 G 的 selected grid rule，限定在 transition events 且 `pit_transition_context` 为 `transition_from_risk_on` / `transition_from_risk_off`。label 绑定状态通过：

| item | value |
| --- | ---: |
| primary event_n | 26,840 |
| label_joined_n | 26,840 |
| missing_label_n | 0 |
| cost_label_complete_n | 26,824 |
| cost_label_complete_rate | 99.94% |
| membership_label_compared_n | 5,305 |
| membership_label_mismatch_n | 0 |
| future feature used by model | 0 |

这说明本次 negative result 不是 label 绑定、D membership 对账或 future leakage 造成的。它是模型读数本身没有在 OOS 站住。

## 3. Universe 与 Segment Power

event 数量看起来充足，但 transition 的真实独立样本是 segment。I 因此同时报告 event-level 与 segment-level power。

| split | event_n | complete_n | positive_n | prevalence | unique segment_n | effective segment_n | from_risk_on event_n | from_risk_off event_n | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 12,423 | 12,413 | 3,527 | 28.41% | 52 | 23.99 | 5,680 | 6,743 | pass |
| validation | 8,810 | 8,808 | 2,830 | 32.13% | 25 | 10.64 | 4,768 | 4,042 | pass |
| robustness | 5,607 | 5,603 | 1,357 | 24.22% | 27 | 8.71 | 3,132 | 2,475 | pass |

解释：

1. `event_n` 足够，但 robustness 的 effective segment_n 只有 8.71，说明读数仍容易被少数长 transition 段影响。
2. 三个 split 都没有 cross-split segment，因此没有同一 transition segment 同时污染 train / validation / robustness 的问题。
3. robustness 的 prevalence 比 validation 低很多：24.22% vs 32.13%。这对 threshold generalization 是真实压力测试。

## 4. 模型与特征处理

三个 arm：

| model_id | raw feature_n | design feature_n | train_sample_n | train_positive_n | model |
| --- | ---: | ---: | ---: | ---: | --- |
| `transition_cost_rejector_no_context` | 44 | 56 | 12,413 | 3,527 | balanced L2 logistic regression |
| `transition_cost_rejector_prev_context` | 50 | 66 | 12,413 | 3,527 | balanced L2 logistic regression |
| `transition_cost_rejector_context_only` | 6 | 10 | 12,413 | 3,527 | balanced L2 logistic regression |

特征预处理策略：

```text
train_median_impute
nonnegative_log1p_selected_numeric
train_winsorize_1_99
train_zscore
categorical_train_vocab_one_hot
```

baseline feature 共 44 个，来自 H 已允许的 t0 event envelope 与 cross-section panel，例如：

```text
return_5d, return_10d, return_20d, return_60d,
stock_vs_market_5d/10d/20d,
amount_ratio_20d/60d, turnover_ratio_20d/60d,
close_to_high_60/120,
direction_entropy_20d, relative_cusum_20d,
momentum_percentile_20d,
universe_up_share, universe_up_share_z, universe_up_share_change_5d,
stock_vs_board_20d, board_relative_cusum_20d,
atr_pct_rank_60d, ema60_positive_run,
family_count, channel_count,
panel_return_1d/5d/20d/60d,
panel_stock_vs_market_20d,
panel_close_to_high_60,
panel_momentum_percentile_20d/60d,
panel_universe_up_share,
panel_universe_new_high_60_share,
panel_board_relative_1d,
panel_board_relative_cusum_20d,
panel_board_return_20d,
board_bucket, primary_family_id
```

previous-regime context feature 共 6 个：

```text
pit_transition_context,
previous_non_transition_trading_day_n,
previous_non_transition_duration_bucket,
segment_age_at_event_t0,
observed_segment_trading_day_n_asof_t0,
days_since_previous_regime_end_asof_event
```

`previous_non_transition_regime` 没有进模型。它与 `pit_transition_context` 在过滤 unknown 后共线，因此只作为 audit-only 字段保留。

## 5. OOS Separability

核心 OOS 排序读数如下：

| model_id | split | ROC-AUC | PR-AUC | top-decile lift | bottom-decile cost_bad | monotonicity |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| no_context | validation | 0.6804 | 0.5106 | 1.9536 | 0.1362 | monotone |
| prev_context | validation | 0.6530 | 0.4842 | 1.8229 | 0.1691 | monotone |
| context_only | validation | 0.4864 | 0.3162 | 1.0987 | 0.2758 | weak |
| no_context | robustness | 0.6449 | 0.3352 | 1.5456 | 0.1248 | monotone |
| prev_context | robustness | 0.5895 | 0.3065 | 1.4646 | 0.2086 | monotone |
| context_only | robustness | 0.4173 | 0.2141 | 0.9347 | 0.3440 | weak |

读数含义：

1. no-context baseline 在 validation 和 robustness 都是三个 arm 中最稳的。
2. prev_context 在 train 内更强，但 OOS 明显弱于 no_context：validation ROC -0.0274，robustness ROC -0.0554。
3. context_only 在 robustness ROC-AUC 只有 0.4173，已经接近反向信号；这说明 previous-regime context 不能单独当作 cost rejector 的主轴。

## 6. Segment-Aware Stability 与 OOS 冲突

train 内部 segment-aware CV 给出了正读数：

| cv_scheme | valid folds | median ROC uplift | median PR uplift | positive fold share | status |
| --- | ---: | ---: | ---: | ---: | --- |
| segment_grouped_cv | 5/5 | +0.0168 | +0.0051 | 0.60 | stable_nonnegative_context_uplift |
| chronological_purged_segment_cv | 5/5 | +0.0209 | +0.0198 | 0.80 | stable_nonnegative_context_uplift |

但外推到 validation / robustness 后，uplift 全面转负：

| split | ROC uplift | PR uplift | top-decile lift uplift | cost reduction uplift | any recall delta | E1-missed capture delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | +0.0194 | +0.0278 | +0.0878 | +0.0344 | -0.0197 | -0.0077 |
| validation | -0.0274 | -0.0264 | -0.1307 | -0.0110 | +0.0035 | +0.0200 |
| robustness | -0.0554 | -0.0288 | -0.0810 | -0.0421 | -0.0431 | -0.1039 |

这是本实验最关键的发现：**previous-regime context 能解释 train 内 transition segment 的一部分结构，但这个结构不是稳定 OOS 排序信号**。它更像是 regime composition / segment composition 的局部描述变量，而不是可泛化的 event-level cost_bad scoring feature。

## 7. Train-Selected Threshold 读数

三个 arm 都在 train-only 规则下选中 `keep_0700`。也就是说，这不是 threshold cherry-pick；比较发生在同一 keep fraction 上。

| model_id | selected threshold | train cost reduction | validation cost reduction | robustness cost reduction |
| --- | --- | ---: | ---: | ---: |
| no_context | `keep_0700` | 29.52% | 19.84% | 19.38% |
| prev_context | `keep_0700` | 32.97% | 18.74% | 15.17% |
| context_only | `keep_0700` | 15.14% | -0.74% | -13.18% |

prev_context 在 train 上比 no_context 多 3.44pp cost reduction，但 validation 少 1.10pp，robustness 少 4.21pp。这个方向反转直接触发 `diagnostic_no_uplift`。

## 8. Cost Quality 分解

selected threshold 下的 all-primary cost quality：

| model_id | split | before rate | after rate | reject rate | relative reduction | fast-fail after | false-repair after |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_context | train | 28.41% | 20.03% | 30.02% | 29.52% | 12.14% | 17.39% |
| prev_context | train | 28.41% | 19.05% | 30.03% | 32.97% | 11.74% | 16.45% |
| no_context | validation | 32.13% | 25.76% | 24.46% | 19.84% | 14.08% | 24.30% |
| prev_context | validation | 32.13% | 26.11% | 24.44% | 18.74% | 14.54% | 24.50% |
| no_context | robustness | 24.22% | 19.53% | 27.73% | 19.38% | 10.89% | 17.92% |
| prev_context | robustness | 24.22% | 20.55% | 30.71% | 15.17% | 11.69% | 19.08% |

prev_context 的 robustness reject rate 更高：30.71% vs no_context 27.73%，但 after cost_bad 反而更差：20.55% vs 19.53%。这说明它不是“拒得更多所以更保守”，而是**拒错了部分样本**。

按 previous-regime context 拆开看 prev_context arm：

| split | context | before rate | after rate | reject rate | relative reduction |
| --- | --- | ---: | ---: | ---: | ---: |
| train | from_risk_on | 32.16% | 19.35% | 37.73% | 39.84% |
| train | from_risk_off | 25.26% | 18.84% | 23.54% | 25.40% |
| validation | from_risk_on | 32.00% | 23.25% | 29.45% | 27.35% |
| validation | from_risk_off | 32.29% | 29.03% | 18.53% | 10.08% |
| robustness | from_risk_on | 20.60% | 18.38% | 26.53% | 10.76% |
| robustness | from_risk_off | 28.80% | 23.69% | 36.00% | 17.75% |

这里能看到一个 regime shift：train / validation 中 `transition_from_risk_on` 似乎更适合被 context 强化拒绝；但 robustness 中 `transition_from_risk_on` 本身变得更干净，before cost_bad 只有 20.60%，context 强化后的拒绝收益只剩 10.76%。这也是 OOS 失败的重要来源。

## 9. Recall Retention

selected threshold 下的 episode recall retention：

| model_id | split | any retention | bridge retention | E1-missed retention |
| --- | --- | ---: | ---: | ---: |
| no_context | train | 82.85% | 82.21% | 72.59% |
| prev_context | train | 80.88% | 81.73% | 71.81% |
| no_context | validation | 82.46% | 86.75% | 84.00% |
| prev_context | validation | 82.81% | 90.36% | 86.00% |
| no_context | robustness | 83.29% | 85.79% | 77.92% |
| prev_context | robustness | 78.98% | 84.15% | 67.53% |

validation 上 prev_context 的 recall 稍好，这也是为什么只看 validation 会误判。但 robustness 上：

1. any recall retention 少 4.31pp；
2. bridge retention 少 1.64pp；
3. E1-missed capture retention 少 10.39pp。

I 的目标不是单纯降低 cost_bad，而是在 transition 侧保留 replay capture。prev_context 在 robustness 中把 E1-missed capture 明显打掉，因此不能支持。

## 10. Density / Overlap

selected event 的 density 与 concentration 没有显示出主要 blocker：

| model_id | split | selected events | event-day density | unique instruments | unique dates | family concentration | board concentration |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_context | robustness | 4,052 | 33.49 | 602 | 121 | 19.67% | 83.96% |
| prev_context | robustness | 3,885 | 32.38 | 602 | 120 | 20.00% | 83.24% |
| context_only | robustness | 3,706 | 47.51 | 626 | 78 | 21.51% | 74.72% |

prev_context 相比 no_context 并没有明显更高的 formal density，也没有更糟的 family / board concentration。问题主要不是 overlap / density，而是 sorting 方向在 robustness 退化。

segment contribution 也未触发 hard block，但需要保留 caution：

| model_id | split | selected segment_n | effective selected segment_n | top1 episode share | top3 episode share | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| no_context | robustness | 27 | 8.08 | 34.30% | 66.34% | pass |
| prev_context | robustness | 27 | 6.98 | 36.52% | 73.04% | pass |
| context_only | robustness | 13 | 6.59 | 33.78% | 70.90% | pass |

prev_context robustness 的 top3 segment episode share 达 73.04%，说明结果仍受少数长段影响。它没有超过 blocked threshold，但解释时不能把 5,607 robustness events 当作完全独立样本。

## 11. Ex-Post Continuation / Conversion Readout

这一节只做 readout，不参与训练或 threshold selection。

robustness 的关键分解：

| context | outcome | segment_n | prefilter cost_bad | selected cost_bad | readout |
| --- | --- | ---: | ---: | ---: | --- |
| from_risk_off | continuation | 5 | 34.50% | 30.92% | 风险高，过滤改善有限 |
| from_risk_off | conversion to risk_on | 3 | 24.16% | 15.76% | 过滤改善明显，但 segment_n 很薄 |
| from_risk_on | continuation | 17 | 15.03% | 10.32% | 本身较干净，过滤有效 |
| from_risk_on | conversion to risk_off | 2 | 36.07% | 34.69% | 风险最高，但 OOS segment_n 只有 2 |

这个 readout 解释了为什么 previous-regime context 不是足够的 feature：

1. `transition_from_risk_on` 不是单一风险状态。它下面既有很干净的 continuation，也有很脏的 risk_on->risk_off conversion。
2. 真正区分脏/干净的变量更接近未来 outcome direction，但这在 t0 不可知，不能作为模型 feature。
3. robustness 中最有画面感的 `risk_on_to_risk_off_deterioration_conversion` 只有 2 个 segment，不能作为 supported evidence。

因此，G 的 previous-regime context 更适合做 transition-side diagnostic / stratification，而不是直接塞进 supervised rejector 来期待稳定 uplift。

## 12. Findings / Insight

### 12.1 最重要结论

`pit_transition_context` 有解释力，但不是当前形式下的 OOS 增益特征。

证据链是：

1. train 与 segment-CV 都显示 prev_context 有正 uplift；
2. validation / robustness 均转负；
3. context_only 在 robustness 明显反向；
4. robustness 的 E1-missed capture 被 prev_context 多打掉 10.39pp；
5. ex-post outcome readout 显示真实风险分化发生在 continuation / conversion 内部，而不是 previous-regime context 本身。

### 12.2 为什么 train-CV positive 但 OOS negative

最可能原因不是实现 bug，而是 segment/regime composition shift：

1. train 中 `transition_from_risk_on` 更脏，context 强化拒绝能带来 39.84% train cost reduction。
2. robustness 中 `transition_from_risk_on` 的 prefilter cost_bad 只有 20.60%，已经相对干净；继续按 train 学到的 context 逻辑拒绝，会伤害 capture。
3. robustness 中真正很脏的 `risk_on_to_risk_off_deterioration_conversion` 只有 2 个 segment，模型无法用 PIT previous-regime context 稳定识别。

这说明 previous-regime context 在 transition universe 内是“状态描述”，不是稳定的“坏事件排序”。

### 12.3 对 E/H 的影响

本实验不改变 H 的判断：

1. H 的 risk_on-only rejector 仍是当前最接近 research-entry 的方向。
2. I 没有证明 G context 能改善 cost_bad sorting。
3. `transition_from_risk_on` / `transition_from_risk_off` 只在 transition universe 内有定义，不能污染 risk_on-only training scope。

因此，不能把 I 的 context feature 加进 E/H gate，也不能用 I 结果为 H 补票。

### 12.4 后续方向

合理后续不是训练 PIT conversion classifier，而是两个更窄的 diagnostic：

1. 在 transition-only universe 内，做 per-context threshold calibration，而不是把 context 当作普通 feature 拼进同一个 logistic model。
2. 用 no-context baseline 固定 score，只做 previous-regime context 的 stratified readout，检查不同 context 下是否需要不同的 reject-rate 上限。

如果继续研究 transition，多数价值应来自“如何不误伤干净 continuation / E1-missed capture”，而不是从 previous-regime context 本身挖一个 production-grade cost rejector。

## 13. Explicit Non-Claims

- 不是 E/H research-entry gate。
- 不是 direct-entry support。
- 不是 production-ready model。
- 没有训练 conversion / continuation classifier。
- 没有证明 previous-regime context 应进入 risk_on-only model。
- 即使 G 的 context 有解释力，I 也没有证明它能稳定改善 OOS cost_bad sorting。
