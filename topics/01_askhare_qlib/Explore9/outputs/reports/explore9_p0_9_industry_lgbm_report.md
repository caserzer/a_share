# Explore9 P0.9 行业专用 LGBM 非线性模型探索报告

## 1. 总结判断

`recommendation = industry_diagnostic_only_due_to_insufficient_sample`。

本轮 P0.9 没有产生任何可进入 industry P1 refine 的候选：

- `candidate_for_industry_p1_refine_count = 0`
- 固定 9 个行业全部完成 PIT mapping，且均为 `exact_match`
- `industry/task/fold` trainability 检查共 `90` 行，trainable 组合为 `0`
- 因为没有 trainable fold，LGBM bucket、candidate OOF aggregation、candidate-level null、matched-delay candidate audit 都只有 schema，没有有效候选行
- 本轮结论只能说明当前 P0.9 合同下样本切分不可训练，不能说明行业专用 LGBM 方向已经被收益指标否定

关键判断：

1. 数据链路和行业映射不是主要问题。9 个固定行业都能映射到 PIT 申万一级行业，且 launch / failure opportunity 数量看起来并不小。
2. 真正的瓶颈是严格 purged expanding WF + industry-local split + inner validation gate 叠加后，每个行业 fold 的训练样本、instrument 覆盖或 inner validation 样本不足。
3. 当前没有模型输出，因此不应讨论 score bucket 的好坏、SHAP 解释、null 显著性或可执行过滤效果。
4. 若继续探索，需要先把“行业专用模型是否可训练”作为独立问题重新注册，不应在本轮结果后直接放松 P1 gate 并沿用当前输出。

## 2. 固定行业与 PIT Mapping

9 个固定行业全部 exact match，没有发生行业名近似替换或静默丢弃。

| 行业 | PIT match | 样本事件 | 股票数 | instrument-year |
| --- | --- | ---: | ---: | ---: |
| 国防军工 | exact_match | 1035 | 14 | 62 |
| 基础化工 | exact_match | 1454 | 34 | 92 |
| 汽车 | exact_match | 1878 | 20 | 97 |
| 交通运输 | exact_match | 2303 | 20 | 123 |
| 机械设备 | exact_match | 842 | 11 | 45 |
| 建筑材料 | exact_match | 553 | 11 | 36 |
| 传媒 | exact_match | 463 | 7 | 29 |
| 电力设备 | exact_match | 1947 | 27 | 105 |
| 电子 | exact_match | 2973 | 35 | 155 |

解释：

- 电子、交通运输、电力设备、汽车的 raw coverage 较好。
- 传媒、建筑材料、机械设备天然股票数偏少，后续进入 industry-local fold 后很难满足 `min_distinct_instruments = 20` 和 `min_distinct_instrument_years = 40`。
- mapping 本身没有阻塞 P0.9，阻塞发生在 trainability gate。

## 3. Feasibility Count

下面的 train / validation 数是 fold-expanded eligible row，不是去重股票数。

### 3.1 Launch 样本

| 行业 | 股票数 | instrument-year | launch events | train rows | train positives | validation rows | validation positives |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 国防军工 | 14 | 55 | 1030 | 1293 | 379 | 791 | 155 |
| 基础化工 | 34 | 84 | 1451 | 1993 | 469 | 879 | 137 |
| 汽车 | 19 | 88 | 1877 | 3509 | 641 | 1210 | 274 |
| 交通运输 | 20 | 116 | 2303 | 4179 | 263 | 1503 | 57 |
| 机械设备 | 11 | 42 | 842 | 1258 | 175 | 585 | 76 |
| 建筑材料 | 11 | 33 | 549 | 663 | 178 | 360 | 56 |
| 传媒 | 7 | 25 | 462 | 797 | 267 | 211 | 22 |
| 电力设备 | 26 | 91 | 1934 | 2331 | 487 | 1380 | 252 |
| 电子 | 35 | 141 | 2972 | 4226 | 1305 | 2088 | 350 |

Launch 侧的表面样本量并不低，但 fold-level trainability 仍失败。核心原因是每个 fold 再切 inner validation 后，很多行业的 inner validation rows / positives 过少，或者 early folds 的 purged train instrument 覆盖不足。

### 3.2 Failure 样本

| 行业 | 股票数 | instrument-year | failure opportunities | train rows | train positives | validation rows | validation positives |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 国防军工 | 14 | 62 | 15435 | 3795 | 1319 | 2367 | 899 |
| 基础化工 | 34 | 90 | 21525 | 5856 | 1956 | 2598 | 1003 |
| 汽车 | 20 | 94 | 27985 | 10378 | 4199 | 3597 | 1320 |
| 交通运输 | 20 | 122 | 34545 | 12385 | 4431 | 4476 | 1419 |
| 机械设备 | 11 | 45 | 12610 | 3740 | 1267 | 1746 | 672 |
| 建筑材料 | 11 | 36 | 8270 | 1951 | 705 | 1074 | 524 |
| 传媒 | 7 | 29 | 6885 | 2277 | 965 | 590 | 329 |
| 电力设备 | 27 | 105 | 29170 | 6888 | 2821 | 4094 | 1911 |
| 电子 | 35 | 155 | 44420 | 12610 | 4602 | 6146 | 2864 |

Failure 侧 raw opportunity 更充足，但仍没有 trainable fold。这里暴露的是 industry-local trainability gate 与 purged inner split 的冲突，而不是 failure opportunity 不存在。

## 4. Purge、Observed Reference 与 Label Truncation

### 4.1 Purge

| task | raw train rows | label-window purge | event-date purge | feature-asof purge | train rows after purge | validation rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| failure | 96667 | 32638 | 0 | 0 | 59880 | 26688 |
| launch | 32615 | 9507 | 0 | 0 | 20249 | 9007 |

结论：

- purge 主要来自 `label_window_end_date` 跨入 validation start。
- `event_effective_date` 和 `feature_asof_date` 没有额外违规，说明 signal-date / next-open 的时间边界基本成立。
- label-window purge 对 industry-local early folds 影响很大。全局看还有 59,880 条 failure train row 和 20,249 条 launch train row，但分行业、分 fold、再切 inner validation 后仍不足。

### 4.2 Observed Reference

| panel | raw rows | decision overlap | feature overlap | label measurement overlap | train rows | outer validation rows | P1 promotion rows | eligible overlap rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| failure | 200845 | 1520 | 1135 | 47175 | 59880 | 26688 | 19353 | 0 |
| launch | 67100 | 65 | 0 | 12375 | 20249 | 9007 | 6592 | 0 |

结论：

- observed-reference overlap 行存在，尤其是 label measurement overlap。
- 但 `eligible_overlap_rows = 0`，没有进入可训练或 P1 promotion 的 overlap 行。
- 这支持本轮“不使用 2025-2026 做选择”的边界。

### 4.3 Label Truncation

| task | raw rows | label truncated rows | truncated rows in P1 promotion |
| --- | ---: | ---: | ---: |
| failure | 200845 | 20480 | 0 |
| launch | 67100 | 6700 | 0 |

结论：

- truncated label rows 被保留为审计数据，但没有进入 P1 promotion。
- 当前失败不是因为 truncated rows 污染了 P1，而是因为严格过滤后 fold-level trainability 不足。

## 5. Trainability Gate 失败拆解

P0.9 的 trainability gate 要求每个 `target_industry + model_task + fold` 在训练前同时满足：

- train rows >= 500
- train positives >= 30
- train negatives >= 100
- train distinct instruments >= 20
- train distinct instrument-years >= 40
- inner validation rows >= 100
- inner validation positives >= 8
- outer validation rows >= 80
- outer validation positives >= 5
- outer validation distinct instruments >= 8
- outer validation distinct instrument-years >= 8

本轮 `90/90` 个组合失败。

### 5.1 失败原因频次

| 失败项 | 触发 fold 数 |
| --- | ---: |
| train_distinct_instruments | 86 |
| train_distinct_instrument_years | 80 |
| inner_validation_event_count | 70 |
| train_event_count_after_purge | 64 |
| inner_validation_positive_count | 58 |
| train_positive_count_after_purge | 39 |
| outer_validation_distinct_instruments | 38 |
| outer_validation_distinct_instrument_years | 38 |
| train_negative_count_after_purge | 33 |
| outer_validation_positive_count_eligible | 10 |
| outer_validation_event_count_eligible | 10 |

解读：

- 最常见失败项不是 positive label，而是 `distinct instruments` 和 `distinct instrument-years`。
- 这意味着行业专用模型的最大问题是横截面宽度不足，尤其是小行业。
- `inner_validation_event_count` 和 `inner_validation_positive_count` 也非常关键。许多行业在 train_all 中看似够样本，但最新 train year 被切做 inner validation 后，inner validation 太薄。

### 5.2 最接近通过的 Failure folds

| 行业 | fold | train rows | train pos | train instruments | train inst-years | inner rows | inner pos | outer rows | outer pos | 失败项 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 电子 | 2024 | 3535 | 1315 | 24 | 71 | 12 | 8 | 1362 | 399 | inner rows |
| 电子 | 2023 | 2492 | 769 | 21 | 53 | 2 | 2 | 1211 | 675 | inner rows, inner positives |
| 汽车 | 2023 | 1439 | 611 | 9 | 25 | 635 | 320 | 763 | 304 | train instruments, train inst-years |
| 基础化工 | 2024 | 1043 | 271 | 10 | 21 | 400 | 241 | 619 | 225 | train instruments, train inst-years |
| 国防军工 | 2024 | 684 | 188 | 7 | 20 | 364 | 173 | 566 | 177 | train instruments, train inst-years |

解读：

- 电子 failure 是最接近可训练的方向，但最接近的一折是 `fold_2024`，它只能做 robustness audit，不能进入 P1 promotion。
- 电子 `fold_2023` 在 core fold 内也接近，但 inner validation 只有 `2` 行、`2` 个 positive，不能用于 early stopping。
- 汽车、基础化工、国防军工的 failure 样本量并不低，但行业内有效 instrument 覆盖不够。

### 5.3 最接近通过的 Launch folds

| 行业 | fold | train rows | train pos | train instruments | train inst-years | inner rows | inner pos | outer rows | outer pos | 失败项 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 电子 | 2024 | 1187 | 362 | 24 | 70 | 10 | 0 | 455 | 158 | inner rows, inner positives |
| 电子 | 2023 | 834 | 309 | 21 | 54 | 2 | 0 | 419 | 33 | inner rows, inner positives |
| 汽车 | 2024 | 708 | 154 | 11 | 38 | 202 | 40 | 313 | 43 | train instruments, train inst-years |
| 交通运输 | 2024 | 1066 | 65 | 14 | 59 | 2 | 0 | 442 | 13 | train instruments, inner rows, inner positives |
| 电力设备 | 2024 | 641 | 191 | 14 | 40 | 3 | 0 | 208 | 40 | train instruments, inner rows, inner positives |

解读：

- Launch 侧同样是电子最接近，但核心问题仍是 inner validation 过薄。
- 汽车、电力设备、交通运输有一定 train rows，但 train instruments 不足或 inner validation 太薄。
- 当前不应把 launch LGBM 没有候选解释为“非线性无效”，只能解释为“按当前严格合同不可训练”。

## 6. Industry-local Baseline

这些 baseline 没有用于模型候选，因为没有 trainable LGBM bucket，但它们可以说明行业内部 opportunity 的基本形态。

### 6.1 Launch baseline

| 行业 | validation events | winner rate | false positive rate | median drawdown 60d |
| --- | ---: | ---: | ---: | ---: |
| 汽车 | 1210 | 24.0% | 35.4% | -10.0% |
| 国防军工 | 791 | 22.5% | 38.9% | -10.2% |
| 电力设备 | 1380 | 21.4% | 42.2% | -10.4% |
| 基础化工 | 879 | 18.8% | 41.7% | -12.4% |
| 机械设备 | 585 | 17.3% | 37.0% | -7.7% |
| 电子 | 2088 | 16.7% | 44.2% | -11.8% |
| 建筑材料 | 360 | 15.8% | 48.0% | -12.4% |
| 传媒 | 211 | 5.7% | 45.2% | -14.5% |
| 交通运输 | 1503 | 4.2% | 31.3% | -8.8% |

观察：

- 汽车、国防军工、电力设备的 launch baseline winner rate 最高。
- 交通运输 launch winner rate 只有 `4.2%`，即使样本较多，也不是当前 launch winner discovery 的自然优先方向。
- 建筑材料、传媒的 false positive / drawdown 形态偏差，样本又薄，不适合直接推进行业模型。

### 6.2 Failure opportunity baseline

| 行业 | validation opportunities | failure precision | nonwinner precision | 50h false reject | 100h false reject | median decision drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 电子 | 6146 | 46.7% | 83.5% | 16.5% | 11.1% | -12.9% |
| 建筑材料 | 1074 | 44.8% | 84.1% | 15.9% | 8.2% | -11.2% |
| 电力设备 | 4094 | 43.0% | 79.2% | 20.8% | 16.6% | -10.3% |
| 传媒 | 590 | 42.9% | 92.9% | 7.1% | 5.7% | -13.5% |
| 国防军工 | 2367 | 38.2% | 77.9% | 22.1% | 5.0% | -9.2% |
| 基础化工 | 2598 | 37.0% | 80.3% | 19.7% | 16.3% | -9.3% |
| 汽车 | 3597 | 36.8% | 75.7% | 24.3% | 13.7% | -10.1% |
| 机械设备 | 1746 | 35.6% | 83.0% | 17.0% | 15.2% | -10.5% |
| 交通运输 | 4476 | 31.8% | 95.8% | 4.2% | 1.9% | -8.6% |

观察：

- 电子 failure baseline 最强，precision `46.7%`，机会数量也最大，是后续若重开 trainability 探索时最值得优先检查的行业。
- 交通运输 nonwinner precision 很高、false reject 很低，但 failure precision 只有 `31.8%`，说明它可能更像“少 winner、低波动”的行业，不一定适合 failure LGBM score。
- 电力设备、汽车、基础化工的 false reject 风险偏高，即使未来能训练模型，也必须把 from-launch false reject 作为硬 veto。

## 7. Failure 多窗口、权重与 Dedup

Failure 多窗口主指标需要 event-level dedup。本轮审计通过，但没有候选进入 P1。

| 审计项 | 结果 |
| --- | ---: |
| window weight normalization rows | 86568 |
| normalization pass rows | 86568 |
| unique launch events in window audit | 11526 |
| validation raw window hits | 30995 |
| event-level dedup rows | 10657 |
| duplicate window hits removed | 20338 |

按行业的 failure window dedup：

| 行业 | raw window hits | duplicate hits |
| --- | ---: | ---: |
| 电子 | 6994 | 4588 |
| 电力设备 | 5041 | 3287 |
| 交通运输 | 4695 | 3084 |
| 汽车 | 3858 | 2554 |
| 基础化工 | 3319 | 2188 |
| 国防军工 | 2629 | 1734 |
| 机械设备 | 2024 | 1326 |
| 建筑材料 | 1497 | 967 |
| 传媒 | 938 | 610 |

结论：

- 多窗口重复很明显，约三分之二 raw window hit 是重复窗口。
- P0.9 使用 event-level dedup 是必要的，否则 failure precision 会被同一 launch event 的多个 decision window 放大。
- 本轮权重与 dedup 审计没有暴露数据错误，但这些审计只证明 denominator 纪律，不证明模型有效。

## 8. Null、Matched-delay、解释性产物

由于 `lgbm_training_enabled_for_industry_fold = false` 对所有 90 个 industry/task/fold 成立：

- `p0_9_industry_launch_lgbm_bucket_leaderboard.csv` 只有 header
- `p0_9_industry_failure_lgbm_bucket_leaderboard.csv` 只有 header
- `p0_9_industry_oof_core_2020_2023_aggregation.csv` 只有 header
- `p0_9_candidate_level_null_aggregation.csv` 只有 header
- `p0_9_industry_failure_matched_delay_baseline.csv` 只有 header
- `p0_9_industry_lgbm_feature_importance.csv` / SHAP / leaf diagnostic 没有有效模型解释行

这不是缺少 artifact，而是当前 trainability gate 下没有合法 candidate 可计算。

## 9. 方向判断

### 可以保留的研究线索

- 电子是最接近可训练的行业，failure 和 launch 都有较高 raw coverage；failure baseline precision 也最高。
- 汽车和电力设备在 launch winner rate 上较好，但 false positive 和 false reject 风险需要硬约束。
- 交通运输不适合直接作为 launch winner discovery 优先行业，但 failure 侧低 false reject 的形态值得作为防错基线参考。

### 当前不能推进的事项

- 不能根据本轮输出选择任何 industry score bucket。
- 不能输出行业专用可执行过滤规则。
- 不能做跨行业泛化判断。
- 不能把 2024 robustness 或 observed-reference label measurement 当作 P1 promotion 证据。

### 下一步建议

如果继续 P0.9，建议不要直接放松当前 gate 后重用本轮结论，而是新增一个更窄的 requirement：

1. 先做 `industry_trainability_probe`，目标只回答哪些行业在 purged WF 下可训练，不做 P1 promotion。
2. 对电子、汽车、电力设备分别测试预注册的 inner validation 方案，例如固定无 early stopping、合并 inner validation 年、或降低 instrument gate。
3. 任何 threshold / trainability gate / feature allowlist 的调整，都应作为 fresh preregistered rerun，不能从本轮 validation 后直接继承。

当前最稳妥的结论是：

```text
P0.9 implementation completed.
P0.9 data discipline passed.
Industry-local LGBM candidate discovery did not start because strict trainability gates failed.
The phase should remain diagnostic-only unless a new preregistered trainability probe is created.
```
