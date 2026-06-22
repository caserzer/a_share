# 12A7e 防守-参与度 Frontier 报告

## 结论先行

12A7e 的最终状态是 `12A7e_x030_defense_optimal_for_downside_not_winner`。train-only frontier 选择的 preferred X 是 `0.20`，不是上游锚点 `X=0.30`；但这个选择不应被解释成 `X=0.20` 已经是强可部署 operating point。更准确地说，当前 fixed-barrier proxy 对 fast-fail penalty 更敏感，因此偏向更窄的 stage-1 denominator。

从 frontier 形态看，stage-1 rank 对 fast-fail 有单调防守方向，但区分度并不强：`X=0.20` 到 `X=0.70` 在 train 上都仍有负的 fast-fail random CI high，直到 `X=0.85/1.00` 才明显失守。stage-2 端也没有显示出独立的强 winner discrimination；stage2 selected count 和 selected positive count 大体随 survivor denominator 同比例扩张。12A7e 因此更像揭示了一个 participation throttle，而不是证明 stage-1 / stage-2 rank 已经能清晰分离坏路径和右尾 winner。

这次结果不能简单解释为“stage-2 deployable signal 已经失败”。更准确的读法是：stage-1 防守强度和 big-winner capture 目标发生了结构性冲突，同时当前 rank / proxy 还不足以把这个冲突压缩成单一可部署 X。`X=0.30` 相比更宽 X 仍保留 downside-defense 的合理性，但它确实切掉了大量右尾 opportunity set；而直接放宽到 `X>=0.50` 又会抬高 fast-fail 风险，并让 per-entry nominal proxy 变差。

| 字段 | 值 |
|---|---:|
| final decision_state | `12A7e_x030_defense_optimal_for_downside_not_winner` |
| input gate | `pass` |
| candidate reconstruction | `pass` |
| stage-1 random source | `pass` |
| stage-2 random source | `pass` |
| selection split | `train` |
| train-selected preferred X | 0.2000 |
| frozen stage-2 candidate | `complex_stage2_score` |
| frozen stage-2 X | 0.3000 |
| X=0.30 train proxy | -0.0198 |
| preferred train proxy | -0.0179 |
| X=0.30 robustness survivor share | 0.3912 |
| preferred robustness survivor share | 0.2826 |
| lookahead guard | `pass` |
| next allowed requirement | `requirement_12a8_budget_probability_calibration.md` |
| recommended internal follow-up | `separate_defense_overlay_from_winner_capture_objective` |

12A7e 没有重新训练 stage-1 或 stage-2 模型，也没有用 validation / robustness 选择 X。preferred X 只来自 train frontier；validation 和 robustness 只用于只读验证与 rank 检查。

## 冻结设置

| 组件 | 冻结口径 |
|---|---|
| stage-1 feature | `volatility_20d` |
| stage-1 orientation | `asc` |
| stage-1 X grid | `0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85, 1.00` |
| X=0.30 role | upstream reference |
| X=1.00 role | no-stage-1-defense anchor, not deployable |
| stage-2 candidate | `complex_stage2_score` |
| stage-2 orientation | `desc` |
| stage-2 X | `0.30` |
| selection discipline | train-only; validation / robustness report-only |

## 重建审计

X=0.30 的 stage-1 与 chained stage-2 复现都通过。stage-2 selected count、positive count 和 rank-evaluable budget 与 12A7d 上游完全一致。

| reconstruction_scope | split | recomputed_selected_n | upstream_selected_n | recomputed_selected_positive_n | upstream_selected_positive_n | status |
|---|---|---:|---:|---:|---:|---|
| stage2_chained_x030 | all | 904 | 904 | 145 | 145 | `pass` |
| stage2_chained_x030 | train | 434 | 434 | 84 | 84 | `pass` |
| stage2_chained_x030 | validation | 191 | 191 | 25 | 25 | `pass` |
| stage2_chained_x030 | robustness | 279 | 279 | 36 | 36 | `pass` |
| stage1_anchor_x030 | all | 4456 | 4456 | NA | NA | `pass` |
| stage1_anchor_x030 | train | 2023 | 2023 | NA | NA | `pass` |
| stage1_anchor_x030 | validation | 957 | 957 | NA | NA | `pass` |
| stage1_anchor_x030 | robustness | 1476 | 1476 | NA | NA | `pass` |

## Train Selection Audit

train 中 `X=0.20` 到 `X=0.70` 都通过可选资格门；`X=0.85` 的 fast-fail random CI high 已不再低于 0，`X=1.00` 同时没有相对 no-defense anchor 的 fast-fail 改善，因此被排除。选择路径为 `max_proxy;larger_capture;lower_fast_fail;larger_stage2_selected;smaller_X`。

| X | eligible | failure reason | fast-fail | capture | survivor share | stage2_n | stage2_pos | proxy | proxy rank | selected |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0.20 | true | NA | 0.1924 | 0.1567 | 0.2252 | 297 | 54 | -0.0179 | 1 | true |
| 0.30 | true | NA | 0.2180 | 0.2563 | 0.3277 | 434 | 84 | -0.0198 | 2 | false |
| 0.40 | true | NA | 0.2441 | 0.3665 | 0.4344 | 575 | 129 | -0.0213 | 3 | false |
| 0.50 | true | NA | 0.2738 | 0.4595 | 0.5337 | 732 | 165 | -0.0234 | 4 | false |
| 0.60 | true | NA | 0.2911 | 0.5923 | 0.6310 | 918 | 223 | -0.0237 | 5 | false |
| 0.70 | true | NA | 0.3144 | 0.7198 | 0.7386 | 1092 | 268 | -0.0250 | 6 | false |
| 0.85 | false | `stage1_delta_ci_high_not_below_zero` | 0.3573 | 0.8632 | 0.8728 | 1309 | 315 | -0.0281 | 7 | false |
| 1.00 | false | `stage1_delta_ci_high_not_below_zero;fast_fail_not_improved_vs_x100` | 0.4186 | 1.0000 | 1.0000 | 1496 | 351 | -0.0334 | 8 | false |

## Frontier 明细

下表中的 `capture` 是 chained survivor continuation positive 相对 ground-truth survivor positive 的捕获率；`pos_capture_entry` 是 stage-2 selected positive 相对 stage1_entry_n 的 per-entry 分母指标，用于 nominal barrier expectancy proxy。`pareto=true` 表示该 X 在同 split 内未被其他 X 同时支配。

### Train

| X | stage1_n | fast-fail | ff_ci_high | survivor_n | survivor share | capture | stage2_n | stage2_pos | stage2 rate | pos_capture_entry | proxy | pareto | proxy rank | capture rank | ff rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 0.20 | 1346 | 0.1924 | -0.1181 | 1087 | 0.2252 | 0.1567 | 297 | 54 | 0.1818 | 0.0065 | -0.0179 | true | 1 | 8 | 1 |
| 0.30 | 2023 | 0.2180 | -0.0983 | 1582 | 0.3277 | 0.2563 | 434 | 84 | 0.1935 | 0.0101 | -0.0198 | true | 2 | 7 | 2 |
| 0.40 | 2774 | 0.2441 | -0.0817 | 2097 | 0.4344 | 0.3665 | 575 | 129 | 0.2243 | 0.0155 | -0.0213 | true | 3 | 6 | 3 |
| 0.50 | 3547 | 0.2738 | -0.0584 | 2576 | 0.5337 | 0.4595 | 732 | 165 | 0.2254 | 0.0199 | -0.0234 | true | 4 | 5 | 4 |
| 0.60 | 4297 | 0.2911 | -0.0435 | 3046 | 0.6310 | 0.5923 | 918 | 223 | 0.2429 | 0.0269 | -0.0237 | true | 5 | 4 | 5 |
| 0.70 | 5200 | 0.3144 | -0.0265 | 3565 | 0.7386 | 0.7198 | 1092 | 268 | 0.2454 | 0.0323 | -0.0250 | true | 6 | 3 | 6 |
| 0.85 | 6555 | 0.3573 | 0.0037 | 4213 | 0.8728 | 0.8632 | 1309 | 315 | 0.2406 | 0.0379 | -0.0281 | true | 7 | 2 | 7 |
| 1.00 | 8303 | 0.4186 | 0.0455 | 4827 | 1.0000 | 1.0000 | 1496 | 351 | 0.2346 | 0.0423 | -0.0334 | true | 8 | 1 | 8 |

### Validation

| X | stage1_n | fast-fail | ff_ci_high | survivor_n | survivor share | capture | stage2_n | stage2_pos | stage2 rate | pos_capture_entry | proxy | pareto | proxy rank | capture rank | ff rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 0.20 | 674 | 0.1602 | -0.1098 | 566 | 0.3986 | 0.3659 | 137 | 19 | 0.1387 | 0.0088 | -0.0143 | true | 1 | 8 | 1 |
| 0.30 | 957 | 0.1964 | -0.0751 | 769 | 0.5415 | 0.5041 | 191 | 25 | 0.1309 | 0.0116 | -0.0173 | true | 2 | 7 | 2 |
| 0.40 | 1218 | 0.2307 | -0.0476 | 937 | 0.6599 | 0.6179 | 235 | 30 | 0.1277 | 0.0139 | -0.0203 | true | 3 | 6 | 3 |
| 0.50 | 1462 | 0.2544 | -0.0280 | 1090 | 0.7676 | 0.7398 | 258 | 34 | 0.1318 | 0.0158 | -0.0223 | true | 4 | 5 | 4 |
| 0.60 | 1661 | 0.2769 | -0.0090 | 1201 | 0.8458 | 0.7724 | 281 | 35 | 0.1246 | 0.0163 | -0.0244 | true | 5 | 4 | 5 |
| 0.70 | 1834 | 0.2944 | 0.0044 | 1294 | 0.9113 | 0.8537 | 295 | 40 | 0.1356 | 0.0186 | -0.0257 | true | 6 | 3 | 6 |
| 0.85 | 2010 | 0.3164 | 0.0219 | 1374 | 0.9676 | 0.9350 | 298 | 42 | 0.1409 | 0.0195 | -0.0277 | true | 7 | 2 | 7 |
| 1.00 | 2151 | 0.3398 | 0.0423 | 1420 | 1.0000 | 1.0000 | 287 | 44 | 0.1533 | 0.0205 | -0.0299 | true | 8 | 1 | 8 |

### Robustness

| X | stage1_n | fast-fail | ff_ci_high | survivor_n | survivor share | capture | stage2_n | stage2_pos | stage2 rate | pos_capture_entry | proxy | pareto | proxy rank | capture rank | ff rank |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 0.20 | 1044 | 0.1245 | -0.0795 | 914 | 0.2826 | 0.1701 | 246 | 18 | 0.0732 | 0.0039 | -0.0117 | true | 1 | 8 | 1 |
| 0.30 | 1476 | 0.1430 | -0.0683 | 1265 | 0.3912 | 0.2713 | 279 | 36 | 0.1290 | 0.0077 | -0.0127 | true | 2 | 7 | 2 |
| 0.40 | 1915 | 0.1614 | -0.0511 | 1606 | 0.4966 | 0.3793 | 369 | 53 | 0.1436 | 0.0114 | -0.0139 | true | 3 | 6 | 3 |
| 0.50 | 2335 | 0.1747 | -0.0407 | 1927 | 0.5959 | 0.4966 | 439 | 74 | 0.1686 | 0.0159 | -0.0143 | true | 4 | 5 | 4 |
| 0.60 | 2717 | 0.1958 | -0.0239 | 2185 | 0.6756 | 0.6115 | 497 | 94 | 0.1891 | 0.0202 | -0.0155 | true | 5 | 4 | 5 |
| 0.70 | 3150 | 0.2190 | -0.0038 | 2460 | 0.7607 | 0.7333 | 575 | 115 | 0.2000 | 0.0247 | -0.0170 | true | 6 | 3 | 6 |
| 0.85 | 3807 | 0.2587 | 0.0281 | 2822 | 0.8726 | 0.8920 | 686 | 143 | 0.2085 | 0.0307 | -0.0197 | true | 7 | 2 | 7 |
| 1.00 | 4659 | 0.3059 | 0.0704 | 3234 | 1.0000 | 1.0000 | 840 | 162 | 0.1929 | 0.0348 | -0.0236 | true | 8 | 1 | 8 |

## Strict Random Support

stage-1 strict same-budget random replay 对所有 X 都有 100 个有效 seed，并且 fast-fail CI high 在 `X<=0.70` 上保持低于 0；因此 `X=0.20` 到 `X=0.70` 的 train 选择资格来自 stage-1 防守证据。stage-2 strict random support 仍不足，所有 X 的 `stage2_random_support_status` 都是 `insufficient`，最多只有 29 个有效 seed，远低于 100。因此 stage-2 读数只能解释为 frontier diagnostic，不能升级成 strict random-supported alpha claim。

| X | stage1 random status | stage1 valid seeds | stage2 valid seeds | stage2 random status |
|---:|---|---:|---:|---|
| 0.20 | `pass` | 100 | 1 | `insufficient` |
| 0.30 | `pass` | 100 | 0 | `insufficient` |
| 0.40 | `pass` | 100 | 5 | `insufficient` |
| 0.50 | `pass` | 100 | 6 | `insufficient` |
| 0.60 | `pass` | 100 | 4 | `insufficient` |
| 0.70 | `pass` | 100 | 20 | `insufficient` |
| 0.85 | `pass` | 100 | 13 | `insufficient` |
| 1.00 | `pass` | 100 | 29 | `insufficient` |

## 区分度补充诊断

下面把 frontier 拆成几个更接近机制的比例项。`stage2_budget_realized = stage2_n / survivor_n`，如果它大体稳定，则 stage2_n 的增长主要来自 survivor denominator 变厚，而不是 stage-2 rank 自身显著扩大选择强度。`stage2_pos_per_survivor = stage2_pos / survivor_n` 用于观察 stage-2 selected positive 是否相对 survivor pool 有明显富集。`proxy_positive_term = 0.20 * pos_capture_entry`，`proxy_fastfail_penalty = -0.10 * fast-fail`。

### Train Proportionality

| X | survivor share | stage2 budget realized | stage2 rate | stage2 pos / survivor | proxy positive term | fast-fail penalty | proxy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.20 | 0.2252 | 0.2732 | 0.1818 | 0.0497 | 0.0013 | -0.0192 | -0.0179 |
| 0.30 | 0.3277 | 0.2743 | 0.1935 | 0.0531 | 0.0020 | -0.0218 | -0.0198 |
| 0.40 | 0.4344 | 0.2742 | 0.2243 | 0.0615 | 0.0031 | -0.0244 | -0.0213 |
| 0.50 | 0.5337 | 0.2842 | 0.2254 | 0.0641 | 0.0040 | -0.0274 | -0.0234 |
| 0.60 | 0.6310 | 0.3014 | 0.2429 | 0.0732 | 0.0054 | -0.0291 | -0.0237 |
| 0.70 | 0.7386 | 0.3063 | 0.2454 | 0.0752 | 0.0065 | -0.0314 | -0.0250 |
| 0.85 | 0.8728 | 0.3107 | 0.2406 | 0.0748 | 0.0076 | -0.0357 | -0.0281 |
| 1.00 | 1.0000 | 0.3099 | 0.2346 | 0.0727 | 0.0085 | -0.0419 | -0.0334 |

train 中，stage2 budget realized 大体停在 `0.27-0.31`，说明 stage2_n 与 stage2_pos 的扩张主要跟随 survivor denominator 扩张。stage2 rate 在 `X=0.40-0.85` 有一定改善，但 validation 没有同样的稳定斜率；因此不能把它解释成强 stage-2 rank discrimination。proxy 的正项从 0.0013 增到 0.0085，但 fast-fail penalty 从 -0.0192 变到 -0.0419，负项主导了 train objective。

### Validation / Robustness Cross-check

| split | X | survivor share | stage2 budget realized | stage2 rate | stage2 pos / survivor | proxy positive term | fast-fail penalty | proxy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| validation | 0.20 | 0.3986 | 0.2420 | 0.1387 | 0.0336 | 0.0018 | -0.0160 | -0.0143 |
| validation | 0.30 | 0.5415 | 0.2484 | 0.1309 | 0.0325 | 0.0023 | -0.0196 | -0.0173 |
| validation | 0.70 | 0.9113 | 0.2280 | 0.1356 | 0.0309 | 0.0037 | -0.0294 | -0.0257 |
| validation | 1.00 | 1.0000 | 0.2021 | 0.1533 | 0.0310 | 0.0041 | -0.0340 | -0.0299 |
| robustness | 0.20 | 0.2826 | 0.2691 | 0.0732 | 0.0197 | 0.0008 | -0.0125 | -0.0117 |
| robustness | 0.30 | 0.3912 | 0.2206 | 0.1290 | 0.0285 | 0.0015 | -0.0143 | -0.0127 |
| robustness | 0.70 | 0.7607 | 0.2337 | 0.2000 | 0.0467 | 0.0049 | -0.0219 | -0.0170 |
| robustness | 1.00 | 1.0000 | 0.2597 | 0.1929 | 0.0501 | 0.0070 | -0.0306 | -0.0236 |

validation 中 stage2 pos / survivor 基本维持在 `0.029-0.034`，更像同比例扩张。robustness 中该比例随 X 放宽上升，但同时 fast-fail penalty 也同步扩大，且 stage-2 strict random support 仍不足。综合看，stage-2 在更宽 denominator 上有 participation benefit，但还没有形成足够强、足够稳定的独立排序证据。

## X=0.30 与 X=1.00 Anchor

`X=1.00` 的意义是 no-stage-1-defense anchor，不是可部署策略。它显示如果完全不做 stage-1 防守，winner participation 可以恢复到 100%，但 fast-fail 成本也同步显著上升。

| split | X | fast-fail | survivor share | capture | stage2_n | stage2_pos | proxy |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 0.30 | 0.2180 | 0.3277 | 0.2563 | 434 | 84 | -0.0198 |
| train | 1.00 | 0.4186 | 1.0000 | 1.0000 | 1496 | 351 | -0.0334 |
| robustness | 0.30 | 0.1430 | 0.3912 | 0.2713 | 279 | 36 | -0.0127 |
| robustness | 1.00 | 0.3059 | 1.0000 | 1.0000 | 840 | 162 | -0.0236 |

在 train 中，从 `X=0.30` 放宽到 `X=1.00`，stage2 selected positives 从 84 增加到 351，capture 从 0.2563 增加到 1.0000；但 fast-fail 从 0.2180 增加到 0.4186，proxy 从 -0.0198 下降到 -0.0334。robustness 方向一致：stage2 positives 从 36 增加到 162，capture 从 0.2713 到 1.0000，但 fast-fail 从 0.1430 到 0.3059，proxy 从 -0.0127 到 -0.0236。

## Findings

1. **X 主要像 participation throttle，而不是清晰的 rank separator。**
   在 train split 中，survivor share 从 `X=0.20` 的 0.2252 单调上升到 `X=1.00` 的 1.0000，continuation positive capture 从 0.1567 上升到 1.0000，stage2 selected positives 从 54 上升到 351。这说明右尾参与度随 X 放宽恢复，但恢复本身主要来自 denominator 变厚。

2. **stage-1 rank 有防守方向，但 fast-fail 区分度不强。**
   train fast-fail rate 从 `X=0.20` 的 0.1924 增加到 `X=0.30` 的 0.2180，再增加到 `X=1.00` 的 0.4186；方向是单调的。但 `X=0.20` 到 `X=0.70` 的 fast-fail CI high 都仍低于 0，说明它不是一个能显著切开 fast-fail 的强 rank，只是在逐步控制风险暴露。

3. **stage-2 selected positives 大体随 survivor denominator 同比例扩张。**
   train 的 stage2 budget realized 大体稳定在 `0.27-0.31`，validation 大体在 `0.20-0.25`。因此 stage2_n 和 stage2_pos 的增长很大程度来自 survivor_n 增长，而不是 stage-2 rank 在更宽 X 下显著提升了样本质量。validation 的 stage2 pos / survivor 基本稳定，也支持这个判断。

4. **train objective 选择 X=0.20 很大程度是 proxy 权重结果。**
   nominal barrier expectancy proxy 的正项很小：train 中从 `X=0.20` 的 0.0013 增至 `X=1.00` 的 0.0085；fast-fail penalty 更大，从 -0.0192 变为 -0.0419。proxy 在 train 上从 -0.0179 逐步变差到 -0.0334，因此 train-only selection 选择 `X=0.20`。这说明当前 fixed-barrier proxy 更奖励防守，而不是证明 `X=0.20` 是稳定最优。

5. **Pareto 全 true 的信息量有限。**
   当前 Pareto 结果中所有 X 都是 `true`，主要因为不同 X 的 budget 差异很大、目标之间单调 tradeoff 明显，跨 X 支配很难发生。它不应被解读成“每个 X 都有强有效前沿证据”，而应解读成“当前 objective 不能把 tradeoff 压缩成单一支配解”。

6. **stage-2 strict random support 仍不足。**
   stage-2 strict random replay 在所有 X 上都是 `insufficient`。这意味着本报告不能把 stage-2 readout 解释成已经被 strict random null 支持的 alpha，只能说明：当 denominator 被 stage-1 放宽时，可供 stage-2 尝试捕获的 positive opportunity set 明显变厚。

## Insight

12A7e 回答的问题不是“哪个 X 可以直接部署”，而是“12A7d 的失败更像 stage-2 没信号，还是 stage-1 denominator 过窄”。当前证据表明 `X=0.30` 确实削弱 right-tail participation，但这不是一个已经被 rank 清晰解决的问题。stage-1 rank 没有显著地区分 fast-fail，只是把风险暴露按 X 渐进缩放；stage-2 rank 在更宽 denominator 上也更多表现为同口径扩容，而不是稳定的 winner discrimination。

因此，最稳妥的后续不是直接 replay `X=0.20` 或更宽 X 策略，而是把两个目标拆开：先承认 X frontier 主要是 participation throttle，再用 probability / budget calibration 检查 stage-2 score 是否能在给定 denominator 内提供真正的边际排序能力。下一步进入 `requirement_12a8_budget_probability_calibration.md` 是合理的，因为需要先把 stage-2 score 从固定 barrier hit-rate 读数转成可校准的 probability / budget ranking，再决定是否存在一个比 `X=0.30` 更适合右尾目标的 deployable operating point。
