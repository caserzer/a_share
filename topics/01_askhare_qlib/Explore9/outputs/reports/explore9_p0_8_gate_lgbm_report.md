# Explore9 P0.8 Gate 组合与 LGBM 非线性评分探索报告

## 1. 总结判断

`recommendation = continue_p0_8_discovery`。本轮 P0.8 发现了若干有解释价值的 gate 组合和 LGBM 分数桶，但没有任何候选满足 P1 refine 条件，也不能生成 `validated_p1_rule`、clean OOS proof、Explore10 backtest 或 frozen strategy。

核心发现：

- `stable_candidate_oof_aggregation` 共 `233` 行，其中 gate `227` 行、LGBM score bucket `6` 行；`candidate_for_p1_refine = 0`。
- Gate 搜索确实找到高 lift 组合，但最强组合普遍存在 fold 数不足、行业/市场状态集中、或 search-bias 未通过的问题。
- LGBM 对 launch 和 failure 都有可见预测力，尤其是 failure task；但 LGBM null full-retrain 未执行，leaf rule 也全部是 single-fold diagnostic，因此不能作为 P1 规则来源。
- P0.8 的数据纪律基本成立：`fold_2024` 未进入 P1 OOF，observed-reference overlap 行未进入 P1，failure multi-window dedup 从 `87171` 个 validation window hit 压缩到 `29251` 个 event-level hit。
- 当前最值得继续观察的是 `launch_winner_score_lgbm` 的 top 5% bucket，以及 risk-off + 量价/行业一致性相关的 launch gate；failure reject 方向需要先解决 false reject 和行业集中问题。

## 2. 数据范围与样本纪律

### 2.1 Fold role

| fold | year | role | P1 OOF | observed label measurement |
| --- | ---: | --- | --- | --- |
| fold_2020 | 2020 | p1_promotion_eligible | True | False |
| fold_2021 | 2021 | p1_promotion_eligible | True | False |
| fold_2022 | 2022 | p1_promotion_eligible | True | False |
| fold_2023 | 2023 | p1_promotion_eligible | True | False |
| fold_2024 | 2024 | robustness_audit_only | False | True |

`fold_2024` 只作为 robustness audit。`p0_8_p1_promotion_oof_aggregation.csv` 中没有 `fold_2024` 的 P1 fold 值。

### 2.2 Leakage / observed-reference 审计

| panel | fold-expanded rows | decision overlap | feature overlap | label overlap | eligible overlap rows | pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| launch | 194900 | 90 | 0 | 33035 | 0 | True |
| failure | 584700 | 2955 | 2315 | 116135 | 0 | True |

这里的重点不是 overlap 行不存在，而是这些行没有进入 train/eval/P1 eligible。P0.8 对 observed-reference 的处理是保守的，特别是 label measurement overlap 被排除在 P1 之外。

### 2.3 样本权重与 dedup

| audit | result |
| --- | --- |
| `sample_weight == final_sample_weight` | launch / failure 均通过 |
| instrument-year cap | 未触发 cap；validation top instrument-year share 最高为 launch `3.23%`、failure `1.25%` |
| failure multi-window dedup | validation raw window hit `87171`，dedup launch-stratum event `29251`，duplicate window hit `57920` |
| candidate baseline missing | 所有 candidate 的 row missing rate 与 weight missing share 均为 `0` |

这说明本轮的主要不确定性不在数据拼接或权重，而在信号是否稳定、是否过度依赖行业/市场状态、以及是否能通过更严格的 search-bias / false-reject 门槛。

## 3. Candidate 总览

| candidate type | task | stable rows | P1 refine |
| --- | --- | ---: | ---: |
| gate | failure_reject_gate | 211 | 0 |
| gate | launch_winner_gate | 16 | 0 |
| lgbm_score_bucket | failure_reject_score_lgbm | 3 | 0 |
| lgbm_score_bucket | launch_winner_score_lgbm | 3 | 0 |

Gate 候选的 fold 覆盖并不均匀：

| task | mean P1 folds | max P1 folds | candidates with 4 positive validation folds |
| --- | ---: | ---: | ---: |
| failure_reject_gate | 3.09 | 4 | 42 |
| launch_winner_gate | 3.56 | 4 | 2 |
| failure_reject_score_lgbm bucket | 4.00 | 4 | 0 |
| launch_winner_score_lgbm bucket | 4.00 | 4 | 0 |

这里的 “positive validation fold” 只是候选在该 fold 有正向指标，不等于通过 P1。很多 failure gate 有高 precision lift，但 false reject、行业集中和 fold 稳定性不足。

## 4. Gate 发现

### 4.1 Launch gate: 有方向，但不够稳

Top launch gate 候选如下：

| formula | P1 folds | pos folds | events | lift vs all | lift vs family | winner coverage | false positive | top industry | search-bias |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `high_vol_quality_permit AND market_regime_risk_off` | 2020-2023 | 3 | 228 | 2.325 | 1.094 | 0.095 | 0.385 | 0.517 | False |
| `high_vol_quality_permit AND industry_breadth_coherence` | 2020-2023 | 4 | 450 | 1.660 | 0.812 | 0.176 | 0.589 | 0.179 | False |
| `industry_breadth_coherence AND market_regime_risk_off AND money_expansion_no_distribution` | 2020-2023 | 2 | 414 | 1.583 | 1.315 | 0.170 | 0.266 | 0.481 | False |
| `industry_breadth_coherence AND market_regime_risk_off AND money_price_upper_keep` | 2020-2023 | 3 | 458 | 1.567 | 1.302 | 0.175 | 0.276 | 0.481 | False |
| `industry_breadth_coherence AND market_regime_risk_off` | 2020-2023 | 4 | 3893 | 1.542 | 1.159 | 0.350 | 0.321 | 0.369 | False |

发现：

- launch gate 的方向更像 “risk-off 中的高质量 continuation / 行业一致性” 线索，而不是一个独立可交易规则。
- 最高 lift 的 `high_vol_quality_permit AND market_regime_risk_off` 只有 `228` 个 P1 OOF events，且 top industry contribution 达 `51.7%`，不能解释为全市场稳健规律。
- `industry_breadth_coherence AND market_regime_risk_off` 覆盖最大，`3893` events、winner coverage `0.350`，但 lift 只有 `1.542`，false positive `0.321`，仍不足以直接冻结。
- launch gate 的 search-bias 字段在 P1 聚合里没有通过，不能把这些 lift 当成可执行 alpha。

### 4.2 Failure gate: lift 高，但 false reject 和集中度风险更大

至少覆盖两个 P1 folds 的 top failure gate：

| formula | P1 folds | pos folds | reject events | failure lift | nonwinner lift | 50h false reject | 100h false reject | top industry | search-bias |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `destructive_high_vol_5d AND gap_fade_break_prior_close_5d AND money_price_upper_keep` | 2022-2023 | 1 | 66 | 1.917 | 1.017 | 0.046 | 0.212 | 0.480 | False |
| `destructive_high_vol_3d AND gap_fade_break_prior_close_5d AND money_price_upper_keep` | 2022-2023 | 1 | 66 | 1.917 | 1.017 | 0.046 | 0.212 | 0.480 | False |
| `high_vol_destructive_warning AND gap_fade_break_prior_close_5d AND money_price_upper_keep` | 2022-2023 | 1 | 66 | 1.917 | 1.017 | 0.046 | 0.212 | 0.480 | False |
| `destructive_high_vol_3d AND money_price_upper_keep` | 2022-2023 | 1 | 69 | 1.911 | 1.009 | 0.053 | 0.212 | 0.480 | False |
| `high_vol_destructive_warning AND industry_breadth_coherence AND money_price_upper_keep` | 2022-2023 | 1 | 33 | 1.892 | 1.000 | 0.061 | 0.345 | 0.690 | False |

发现：

- failure gate 的最高 lift 主要来自 2022-2023，且 positive folds 通常只有 `1`；这说明它更像局部 market episode 的解释，而不是稳定 reject 规则。
- 这些 gate 对 big-winner 的 false reject 很敏感：上表中 `100h false reject` 可到 `21.2%` 或 `34.5%`。
- nonwinner lift 接近 `1.0`，说明这些 gate 虽然能提高 failure precision，但没有很好地区分 “真正差交易” 与 “未来大赢家被错杀”。
- 行业集中明显，top industry contribution 常在 `48%` 以上，最极端达到 `69%`。

一折候选中存在更高 lift，例如 `destructive_high_vol_5d AND industry_breadth_coherence AND money_price_upper_keep` 在 `fold_2023` 有 failure lift `2.518`，但只有 `3` 个 reject events，且 `100h false reject` 达 `69.0%`。这类结果只能作为 failure mechanism 诊断，不能进入 P1。

## 5. LGBM 发现

### 5.1 Trainability 与 fold metrics

| fold | task | validation events | positives | AUC | logloss | best iter | status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| fold_2020 | launch | 4052 | 1271 | 0.601 | 0.667 | 65 | trainable |
| fold_2021 | launch | 4814 | 769 | 0.489 | 0.374 | 35 | trainable |
| fold_2022 | launch | 5358 | 505 | 0.522 | 0.273 | 1 | trainable |
| fold_2023 | launch | 5040 | 325 | 0.593 | 0.226 | 9 | trainable |
| fold_2024 | launch | 88 | 14 | - | - | - | insufficient outer validation rows |
| fold_2020 | failure | 11973 | 3347 | 0.631 | 0.652 | 17 | trainable |
| fold_2021 | failure | 14521 | 6105 | 0.600 | 0.642 | 32 | trainable |
| fold_2022 | failure | 15829 | 6900 | 0.514 | 0.711 | 52 | trainable |
| fold_2023 | failure | 14547 | 5389 | 0.648 | 0.625 | 28 | trainable |
| fold_2024 | failure | 280 | 75 | 0.741 | 0.514 | 67 | robustness audit only |

发现：

- Launch LGBM 在 2020、2023 有预测力，2021 接近反向，2022 很弱且 best iteration 为 `1`。这不是稳定可用的 launch model。
- Failure LGBM 整体更强，2020、2021、2023 都有 `0.60+` AUC；2022 只有 `0.514`，说明 regime sensitivity 很强。
- 2024 failure AUC `0.741` 不能用于 P1，因为它是 robustness audit only，且 validation events 只有 `280`。

### 5.2 LGBM score buckets

P1 folds 内的 bucket 聚合：

| task | bucket | folds | events | positives | mean lift | mean precision / winner rate | false reject 50h |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| launch | top 10% | 4 | 1446 | 261 | 1.498 | winner rate 0.168 | - |
| launch | top 5% | 4 | 781 | 143 | 2.609 | winner rate 0.289 | - |
| launch | top 2% | 4 | 229 | 12 | 1.106 | winner rate 0.148 | - |
| failure | top risk 10% | 4 | 1957 | 941 | 1.469 | precision 0.555 | 0.173 |
| failure | top risk 5% | 4 | 923 | 464 | 1.421 | precision 0.530 | 0.193 |
| failure | top risk 2% | 4 | 277 | 174 | 1.583 | precision 0.592 | 0.134 |

发现：

- Launch top 5% 是本轮最有价值的非线性 discovery lead：`781` events、mean lift `2.609`，强于 top 10% 和 top 2%。但它在 fold 之间不均匀，不能直接冻结。
- Launch top 2% 并没有更强，说明 LGBM score 的极端尾部可能过拟合或跨年校准不稳定。
- Failure top risk 2% 有最高 failure lift `1.583`，且 false reject 50h 均值 `0.134` 低于 top 5% / top 10%。如果继续探索 failure reject，应优先研究 top risk 2% 的共同结构，而不是直接使用 gate。
- Failure top risk buckets 在 2022 的 fold-level lift 全部低于或接近 `1`，这是当前 failure LGBM 最大的稳定性缺口。

### 5.3 Feature importance

| task | top features by total gain |
| --- | --- |
| launch_winner_score_lgbm | `industry`、`atr20_pct`、`prelaunch_drawdown_120d`、`launch_gain_from_recent_low_120d`、`ret_rank_20d_market`、`launch_gain_from_recent_low_60d`、`industry_breadth_20d`、`market_regime` |
| failure_reject_score_lgbm | `industry`、`atr20_pct`、`launch_gain_from_recent_low_120d`、`prelaunch_drawdown_120d`、`industry_breadth_20d`、`market_regime`、`rolling_range_20d`、`higher_low_count_20d` |

发现：

- 两个模型的第一重要特征都是 `industry`，这解释了 concentration audit 里的行业依赖。
- `atr20_pct`、`prelaunch_drawdown_120d`、`launch_gain_from_recent_low_*` 同时出现在 launch 和 failure 模型前列，说明 P0.8 的非线性模型主要在刻画 “波动率 + 前期涨幅/回撤 + 行业状态”。
- 这对研究有价值，但对可交易规则是风险：如果不做行业中性/行业内验证，模型可能只是在识别某些行业阶段。

### 5.4 Leaf rule

| task | leaf rows | validation events | mean train positive rate | mean validation positive rate | stable eligible |
| --- | ---: | ---: | ---: | ---: | ---: |
| launch_winner_score_lgbm | 20 | 1096 | 0.561 | 0.327 | 0 |
| failure_reject_score_lgbm | 25 | 4253 | 0.770 | 0.469 | 0 |

Leaf rule 的 train positive rate 明显高于 validation positive rate，且所有 leaf 都是 `single_fold_diagnostic_only`。它们只能解释模型局部行为，不能作为 stable OOF candidate。

## 6. Search-bias、null 与 concentration

### 6.1 Gate null permutation

| task | audited rows | search-bias pass | null p95 exceeded |
| --- | ---: | ---: | ---: |
| failure_reject_gate | 187 | 127 | 127 |
| launch_winner_gate | 13 | 9 | 9 |

Gate null permutation 对 `200` 个 gate candidate 执行了 full search-budget matched audit，且 `136` 个候选超过 null p95。这个结果说明 gate search 确实有非随机线索，但不是 P1 许可：

- stable gate candidates 有 `227` 个，其中 `27` 个没有进入 gate null audit 表。
- P1 聚合仍然没有任何 candidate 被提升。
- null p95 只回答 “是否超过随机 search baseline”，不回答 “是否跨 fold、跨行业、低 false reject 且可执行”。

### 6.2 LGBM null

| null type | full retrain required | executed | status |
| --- | --- | --- | --- |
| lgbm_bucket | True | False | not_executed_in_primary_profile_runtime_guard |
| lgbm_leaf_rule | True | False | not_executed_in_primary_profile_runtime_guard |

因此，LGBM bucket 即使表现更强，也不能提升到 P1。特别是 launch top 5% bucket 的 lift 很高，但没有 full-retrain null，不能排除 score bucket 搜索偏差。

### 6.3 行业 / regime concentration

| group | rows | regime specialist | industry specialist | mean top1 industry | mean top3 industry | mean industry count |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gate failure | 211 | 180 | 119 | 0.407 | 0.723 | 6.79 |
| gate launch | 16 | 16 | 9 | 0.391 | 0.706 | 9.31 |
| LGBM failure bucket | 3 | 3 | 2 | 0.443 | 0.725 | 9.67 |
| LGBM launch bucket | 3 | 3 | 3 | 0.707 | 0.864 | 10.33 |

发现：

- 行业/市场状态集中是 P0.8 最大的共性问题。
- Launch LGBM bucket 的 mean top1 industry contribution 高达 `0.707`，说明 top score bucket 很可能由少数行业主导。
- Failure gate 虽然候选数量多，但 `180/211` 是 regime specialist，`119/211` 是 industry specialist；这不支持直接生成跨市场规则。
- Ablation audit 当前没有触发 dependency warning，但从 concentration 指标看，下一轮必须用行业中性、行业内、或 leave-one-industry-out 的方式重验。

## 7. 与 P0.7 基线的关系

`p0_8_fold_local_p0_7_baseline_audit.csv` 记录了两个基线来源：

| baseline | scope | selected on validation | used for P1 gate |
| --- | --- | --- | --- |
| `p0_7ab_full_window_best_single_formula` | full_window_audit_only | False | False |
| `p0_7ab_fold_local_train_selected` | fold_local_train_selected | False | True |

解释：

- P0.8 没有把 P0.7 full-window best formula 当成可选规则，避免了 full-window selection 泄露。
- P0.7 的作用是 fold-local baseline / audit anchor，不是 P0.8 的 strategy source。
- P0.8 发现的 gate 和 LGBM 线索应当被视为对 P0.7 failure mechanism 的扩展解释，而不是 P0.7 的可交易替代品。

## 8. 最重要的实验发现

### 发现 1: Launch 的非线性信号比手工 gate 更值得继续

`launch_winner_score_lgbm` top 5% bucket 是当前最强 launch lead：`781` events、`143` positives、mean lift `2.609`。相比之下，最强 launch gate 的 lift 虽高，但样本更小、行业集中更强、search-bias 未过。

下一步如果继续 P0.8，应优先解释 top 5% bucket 的共同特征，而不是直接扩展手工 gate 组合数量。

### 发现 2: Failure reject 能识别风险，但还不能安全拒绝交易

Failure gate 和 LGBM 都能提高 failure precision。LGBM top risk 2% 的 precision `0.592`、failure lift `1.583`，看起来有价值。但 failure reject 的核心约束不是 precision alone，而是避免错杀未来赢家。当前 top gate 的 `100h false reject` 可到 `21.2%`、`34.5%`，个别一折高 lift gate 甚至达到 `69.0%`，不能进入 P1。

### 发现 3: 2022 是稳定性压力测试

Failure LGBM 在 2020、2021、2023 AUC 分别为 `0.631`、`0.600`、`0.648`，但 2022 只有 `0.514`。Launch LGBM 在 2021 也只有 `0.489`。这说明当前信号不是单调跨年有效，至少需要针对 2021/2022 的 regime failure 做解释。

### 发现 4: 行业和 regime 可能是主要驱动

两个 LGBM 模型的 top feature 都是 `industry`。同时，几乎所有 LGBM bucket 都被标记为 regime specialist，launch LGBM bucket 全部是 industry specialist。P0.8 目前更像 “行业/状态条件下的局部结构发现”，不是全市场规则发现。

### 发现 5: P0.8 的工程审计通过，但研究审计不够

工程侧通过：manifest、fold role、observed-reference exclusion、sample weight、dedup、baseline missing 都没有阻塞问题。研究侧未通过：LGBM null full-retrain 未执行，leaf rule 不稳定，industry/regime concentration 明显，candidate_for_p1_refine 为 `0`。

## 9. 结论与后续建议

本轮 P0.8 应继续停留在 discovery，不应进入 P1 或 Explore10。

建议的下一步不是扩大所有组合，而是缩小问题：

1. 对 `launch_winner_score_lgbm` top 5% bucket 做解释性拆解，重点看是否能形成行业中性后的简单条件。
2. 对 failure reject 加硬约束：big-winner false reject、50h false reject、行业 top share、最小 positive fold 数必须同时满足。
3. 对 LGBM bucket 执行 full-retrain null；未完成前，所有 LGBM bucket 只能写入 discovery lead。
4. 对 2021/2022 做单独 failure-case review，解释为什么 launch / failure LGBM 在这些年份弱化。
5. 如果继续 gate search，应优先约束行业/regime exposure，而不是继续增加 token 组合深度。

最终状态保持：

- `validated_p1_rule_generated = False`
- `p0_8_validation_clean_oos_proof = False`
- `ready_for_backtest = False`
- `proceed_to_explore10_backtest = False`
- `recommendation = continue_p0_8_discovery`
