# 大赢家反向生命周期画像 V0：详细发现与研究洞察

最终决策：`reverse_lifecycle_sequence_supported_universal_dominance`。

本报告基于本次全量重跑后的 publishable CSV 与 run manifest 重写。它是**反向生命周期画像**，不是交易系统、不是回测，也不是可直接下单的事件合约。报告中的 winner/control 差异均应理解为“已发生大赢家 episode 的生命周期诊断”，尤其是低点之后的强变量，多数属于确认指标，而不是低点当天即可使用的领先指标。

## 1. 结论摘要

1. 大赢家 episode 共 `866` 个，低点轴匹配后进入 dominance 的 winner 为 `851` 个；低点匹配覆盖率 `98.3%`，平均每个 winner 有 `4.55` 个 control。
2. 结果最强的不是单个 t0 因子，而是低点后的路径与序列：`S3_repair_rank_persistence_v0`、`S6_continuation_discriminator_v0`、`S2_repair_money_vwap_v0` 三条序列达到 universal candidate；其中 S3 和 S6 是主信号。
3. 单因子强 effect 主要出现在低点后 `+20/+60/+120` 或 EMA60 reclaim 后：`return_60d`、`max_runup_axis_to_plus_60d`、`ema60_slope_20d`、`close_to_ema60`、`atr_20_pct` 等。这些是“推进已经发生”的确认变量，不应被解释为低点当天领先因子。
4. 低点当天的非路径特征明显弱得多。低点当天最高的非路径 SMD 主要是 `atr_20_pct`，SMD 约 `0.35`；`close_to_ema20`、`stock_vs_market_20d`、`drawdown_from_60d_high` 等并没有形成强领先区分。
5. near-winner 对照显示，仅仅 30%-50% MFE 不足以解释差异。winner 与 near-winner 在 S2 上很接近，但在 S3 rank persistence 和部分 S6 continuation 上仍有明显分化。
6. false-repair control 很多：EMA60 anchor 匹配 control 中 `74.4%` 被标记为 false repair。这说明“修复/站回均线”本身不是充分条件，后续是否继续保持相对强度和避免失败修复才是区分点。

## 2. 样本、切分与机会集

### Episode 分布

| split      |   episodes | mfe_mean   | mfe_median   | mfe_max   |
|:-----------|-----------:|:-----------|:-------------|:----------|
| robustness |        412 | 92.3%      | 73.4%        | 504.2%    |
| train      |        285 | 81.8%      | 68.7%        | 334.0%    |
| validation |        169 | 71.8%      | 62.8%        | 426.3%    |

### 从低点到 120 日内最高点的节奏

| duration_bucket   |   episodes |   sessions_mean |   sessions_median | mfe_mean   |
|:------------------|-----------:|----------------:|------------------:|:-----------|
| fast              |        103 |            24.2 |                25 | 67.5%      |
| long              |        551 |           107   |               110 | 90.1%      |
| medium            |        212 |            63   |                63 | 79.6%      |

洞察：样本不是短促反弹主导。`long` bucket 有 `551` 个，占全部 episode 的 `63.6%`，中位低点到高点约 110 个交易日。这意味着大赢家画像更接近“低点后持续推进的生命周期”，而不是一次性跳涨。

### 低点所处市场状态

| split      | market_regime_bucket   |   episodes |
|:-----------|:-----------------------|-----------:|
| robustness | risk_off               |        197 |
| robustness | risk_on                |        138 |
| robustness | transition             |         77 |
| train      | risk_off               |        136 |
| train      | risk_on                |         62 |
| train      | transition             |         87 |
| validation | risk_off               |        120 |
| validation | risk_on                |         10 |
| validation | transition             |         39 |

市场 regime 本身不是强区分变量：winner/control 在 `risk_off`、`risk_on`、`transition` 的占比差异很小。

| bucket                        |   winner_count |   control_count | winner_rate   | control_rate   | lift   | absolute_rate_difference   |
|:------------------------------|---------------:|----------------:|:--------------|:---------------|:-------|:---------------------------|
| risk_on                       |            199 |             879 | 23.4%         | 22.3%          | 1.05   | 1.1%                       |
| risk_off                      |            451 |            2137 | 53.0%         | 54.2%          | 0.98   | -1.2%                      |
| transition                    |            201 |             924 | 23.6%         | 23.5%          | 1.01   | 0.2%                       |
| missing_insufficient_lookback |              0 |               0 | 0.0%          | 0.0%           |        | 0.0%                       |

这说明本实验的主要区分不是“只在某个大盘 regime 才出现 winner”，而是个股在低点之后是否走出持续修复和相对强度。

## 3. 匹配质量与 anchor 可观测性

### Control matching

| match_axis        | split      |   winner_count |   matched_winner_count |   control_match_count | match_coverage   |   average_controls_per_winner |   unmatched_winner_count |   cross_split_boundary_unusable_count |
|:------------------|:-----------|---------------:|-----------------------:|----------------------:|:-----------------|------------------------------:|-------------------------:|--------------------------------------:|
| shared_axis_low   | all        |            866 |                    851 |                  3940 | 98.3%            |                          4.55 |                       15 |                                     0 |
| shared_axis_low   | train      |            285 |                    271 |                  1229 | 95.1%            |                          4.31 |                       14 |                                     0 |
| shared_axis_low   | validation |            169 |                    169 |                   797 | 100.0%           |                          4.72 |                        0 |                                     0 |
| shared_axis_low   | robustness |            412 |                    411 |                  1914 | 99.8%            |                          4.65 |                        1 |                                     0 |
| shared_axis_ema60 | all        |            866 |                    817 |                  3615 | 94.3%            |                          4.17 |                       49 |                                   299 |
| shared_axis_ema60 | train      |            285 |                    265 |                  1061 | 93.0%            |                          3.72 |                       20 |                                     0 |
| shared_axis_ema60 | validation |            169 |                    161 |                   753 | 95.3%            |                          4.46 |                        8 |                                    56 |
| shared_axis_ema60 | robustness |            412 |                    391 |                  1801 | 94.9%            |                          4.37 |                       21 |                                   243 |

低点轴匹配质量较好：validation split 低点匹配覆盖率为 `100.0%`，robustness 为 `99.8%`。EMA60 anchor 匹配较难，原因是 anchor 发生日期跨 split 边界更容易被拒绝；全样本 EMA60 匹配覆盖率为 `94.3%`，仍足以支撑 anchor 画像，但相关结论应记住它比低点轴更受 anchor 日期约束。

### EMA60 reclaim anchor

| source_group         | split      |   row_count |   anchor_present_count | anchor_occurrence_rate   |   missing_event_absent_count |   anchor_year_coverage |
|:---------------------|:-----------|------------:|-----------------------:|:-------------------------|-----------------------------:|-----------------------:|
| winner_reference     | robustness |         412 |                    395 | 95.9%                    |                           17 |                      3 |
| winner_reference     | train      |         285 |                    276 | 96.8%                    |                            9 |                      5 |
| winner_reference     | validation |         169 |                    163 | 96.4%                    |                            6 |                      3 |
| matched_low_controls | robustness |        1914 |                   1888 | 98.6%                    |                           26 |                      3 |
| matched_low_controls | train      |        1229 |                   1222 | 99.4%                    |                            7 |                      5 |
| matched_low_controls | validation |         797 |                    794 | 99.6%                    |                            3 |                      3 |

winner reference 的 EMA60 reclaim 出现率约 95%-97%，说明它是一个稳定可观测的生命周期 anchor。但这不代表 EMA60 reclaim 是充分买点：control candidate 也有很高的 reclaim 出现率，matched low controls 在 validation 中 reclaim rate 达 `99.6%`。真正的区分发生在 reclaim 之后的 money/rank/continuation 序列。

## 4. 单因子结果：强项主要是确认，不是领先

### 全样本 headline 强因子

| feature                    | shared_axis       |   relative_day | winner_mean   | control_mean   |   standardized_mean_difference | claim_status          |
|:---------------------------|:------------------|---------------:|:--------------|:---------------|-------------------------------:|:----------------------|
| return_60d                 | shared_axis_low   |             60 | 27.5%         | 4.3%           |                           1.46 | effect_size_candidate |
| max_runup_axis_to_plus_60d | shared_axis_low   |              0 | 43.5%         | 19.8%          |                           1.42 | effect_size_candidate |
| return_60d                 | shared_axis_ema60 |             60 | 18.9%         | -2.5%          |                           1.32 | effect_size_candidate |
| ema60_slope_20d            | shared_axis_ema60 |             60 | 6.6%          | 0.6%           |                           1.3  | effect_size_candidate |
| ema60_slope_20d            | shared_axis_low   |             60 | 3.7%          | -1.6%          |                           1.24 | effect_size_candidate |
| close_to_ema60             | shared_axis_low   |             60 | 7.9%          | -1.5%          |                           1.06 | effect_size_candidate |
| ema60_slope_20d            | shared_axis_low   |            120 | 5.3%          | -0.4%          |                           1.06 | effect_size_candidate |
| atr_20_pct                 | shared_axis_low   |            120 | 4.6%          | 3.2%           |                           1    | effect_size_candidate |
| close_to_ema60             | shared_axis_ema60 |             60 | 7.1%          | -1.9%          |                           0.98 | effect_size_candidate |
| atr_20_pct                 | shared_axis_ema60 |             60 | 4.2%          | 2.9%           |                           0.97 | effect_size_candidate |
| return_60d                 | shared_axis_low   |            120 | 18.0%         | -0.0%          |                           0.94 | effect_size_candidate |
| return_20d                 | shared_axis_low   |             20 | 15.8%         | 8.1%           |                           0.91 | effect_size_candidate |

这些强项有明显后验性质：

- `return_60d`、`max_runup_axis_to_plus_60d` 直接描述低点之后已经涨起来的路径。
- `ema60_slope_20d`、`close_to_ema60` 在 `+60` 变强，说明趋势修复已经进入推进阶段。
- `atr_20_pct` 在 `+60/+120` 变强，说明波动扩张更多是 winner 生命周期的结果，而不是低点前稳定先验。

### 低点当天的非路径特征

| feature                     | winner_mean   | control_mean   |   standardized_mean_difference | claim_status          |
|:----------------------------|:--------------|:---------------|-------------------------------:|:----------------------|
| atr_20_pct                  | 4.4%          | 3.8%           |                           0.35 | effect_size_candidate |
| distance_to_120d_high       | -28.1%        | -25.7%         |                          -0.22 | no_claim              |
| drawdown_from_60d_high      | -24.1%        | -22.2%         |                          -0.2  | no_claim              |
| intraday_range_pct          | 5.9%          | 5.2%           |                           0.19 | no_claim              |
| stock_vs_market_20d         | -7.8%         | -6.6%          |                          -0.17 | no_claim              |
| close_to_ema20              | -8.9%         | -8.2%          |                          -0.14 | no_claim              |
| gap_open_pct                | -1.2%         | -0.9%          |                          -0.14 | no_claim              |
| return_5d                   | -7.3%         | -6.6%          |                          -0.13 | no_claim              |
| return_20d                  | -12.5%        | -11.6%         |                          -0.13 | no_claim              |
| close_to_derived_daily_vwap | 0.5%          | 0.4%           |                           0.09 | no_claim              |

低点当天并没有出现足够强的单因子领先画像。`atr_20_pct` 有一定差异，但强度远低于低点之后的收益、均线斜率和相对强度。对未来事件定义而言，低点当天的单因子更适合作为弱过滤或风险描述，而不是核心 entry trigger。

### Validation split 的单因子读数

| feature                    | shared_axis       |   relative_day | winner_mean   | control_mean   |   standardized_mean_difference | claim_status          |
|:---------------------------|:------------------|---------------:|:--------------|:---------------|-------------------------------:|:----------------------|
| max_runup_axis_to_plus_60d | shared_axis_low   |              0 | 41.4%         | 19.2%          |                           1.48 | effect_size_candidate |
| ema60_slope_20d            | shared_axis_low   |             60 | 3.7%          | -1.5%          |                           1.37 | effect_size_candidate |
| return_60d                 | shared_axis_low   |             60 | 26.1%         | 4.7%           |                           1.32 | effect_size_candidate |
| ema60_slope_20d            | shared_axis_ema60 |             60 | 5.3%          | 0.7%           |                           1.19 | effect_size_candidate |
| return_60d                 | shared_axis_ema60 |             60 | 11.6%         | -2.9%          |                           1.08 | effect_size_candidate |
| ema20_slope_20d            | shared_axis_ema60 |             20 | 11.8%         | 4.8%           |                           1.06 | effect_size_candidate |
| atr_20_pct                 | shared_axis_low   |            120 | 4.2%          | 3.0%           |                           1.01 | effect_size_candidate |
| stock_vs_market_20d        | shared_axis_low   |             20 | 15.0%         | 6.5%           |                           0.97 | effect_size_candidate |
| stock_vs_market_20d        | shared_axis_ema60 |             20 | 6.6%          | -1.6%          |                           0.97 | effect_size_candidate |
| close_to_ema60             | shared_axis_low   |             60 | 6.2%          | -1.6%          |                           0.95 | effect_size_candidate |

validation 中的强因子仍集中在低点之后：`max_runup_axis_to_plus_60d`、`ema60_slope_20d +60`、`return_60d +60`、`stock_vs_market_20d +20`。这进一步支持“生命周期确认”的解释，而不是“低点当天即可识别”。

## 5. Sequence 结果：真正有信息的是修复后的持续性

### 全样本 sequence dominance

| sequence_id                      |   winner_count |   control_count | winner_sequence_rate   | control_sequence_rate   |   lift | absolute_rate_difference   |   train_lift |   validation_lift |   robustness_lift | split_stability               | claim_status                           |
|:---------------------------------|---------------:|----------------:|:-----------------------|:------------------------|-------:|:---------------------------|-------------:|------------------:|------------------:|:------------------------------|:---------------------------------------|
| S1_context_to_repair_v0          |            851 |            3940 | 93.5%                  | 90.3%                   |   1.04 | 3.2%                       |         1.08 |              1.08 |              0.99 | not_stable_or_sample_blocked  | no_claim                               |
| S2_repair_money_vwap_v0          |            851 |            3940 | 85.1%                  | 76.9%                   |   1.11 | 8.1%                       |         1.14 |              1.19 |              1.05 | same_positive_sign_all_splits | sequence_supported_universal_candidate |
| S3_repair_rank_persistence_v0    |            851 |            3940 | 57.3%                  | 16.2%                   |   3.54 | 41.2%                      |         3.66 |              3.29 |              3.61 | same_positive_sign_all_splits | sequence_supported_universal_candidate |
| S4_contraction_expansion_v0      |            851 |            3940 | 92.7%                  | 91.3%                   |   1.02 | 1.4%                       |         1.04 |              1.09 |              0.97 | not_stable_or_sample_blocked  | no_claim                               |
| S5_money_no_distribution_v0      |            851 |            3940 | 99.2%                  | 99.4%                   |   1    | -0.2%                      |         1    |              1    |              1    | not_stable_or_sample_blocked  | no_claim                               |
| S6_continuation_discriminator_v0 |            851 |            3940 | 79.2%                  | 32.4%                   |   2.45 | 46.8%                      |         2.85 |              2.36 |              2.26 | same_positive_sign_all_splits | sequence_supported_universal_candidate |

核心读法：

- `S3_repair_rank_persistence_v0` 是最强序列。winner sequence rate 为 `57.3%`，control 为 `16.2%`，lift `3.54`，绝对差 `41.2pct`。这不是简单站上均线，而是修复后个股相对市场强度能否持续。
- `S6_continuation_discriminator_v0` 也很强。winner rate `79.2%`，control `32.4%`，lift `2.45`，绝对差 `46.8pct`。但它依赖低点后 +20% close-observed path state，因此是确认性 continuation discriminator。
- `S2_repair_money_vwap_v0` 稳定但强度较弱。winner rate `85.1%`，control `76.9%`，lift `1.11`，绝对差 `8.1pct`。它更像“修复质量过滤”，不是单独的决定性条件。
- `S1_context_to_repair_v0`、`S4_contraction_expansion_v0`、`S5_money_no_distribution_v0` 不应被作为 headline。S1/S4 发生率高但 control 也高；S5 几乎没有区分度。

### Validation split sequence readout

| sequence_id                      |   winner_count |   control_count | winner_sequence_rate   | control_sequence_rate   |   lift | absolute_rate_difference   | claim_status                          |
|:---------------------------------|---------------:|----------------:|:-----------------------|:------------------------|-------:|:---------------------------|:--------------------------------------|
| S1_context_to_repair_v0          |            169 |             797 | 95.9%                  | 88.6%                   |   1.08 | 7.3%                       | sequence_regime_conditional_candidate |
| S2_repair_money_vwap_v0          |            169 |             797 | 89.3%                  | 74.9%                   |   1.19 | 14.4%                      | sequence_regime_conditional_candidate |
| S3_repair_rank_persistence_v0    |            169 |             797 | 69.8%                  | 21.2%                   |   3.29 | 48.6%                      | sequence_regime_conditional_candidate |
| S4_contraction_expansion_v0      |            169 |             797 | 93.5%                  | 85.8%                   |   1.09 | 7.7%                       | sequence_regime_conditional_candidate |
| S5_money_no_distribution_v0      |            169 |             797 | 99.4%                  | 99.7%                   |   1    | -0.3%                      | no_claim                              |
| S6_continuation_discriminator_v0 |            169 |             797 | 79.3%                  | 33.6%                   |   2.36 | 45.7%                      | sequence_regime_conditional_candidate |

validation 是 2022-2023 的固定压力窗口。在这个 split 中，S3 和 S6 仍然强：S3 绝对差 `48.6pct`，S6 绝对差 `45.7pct`。S2 在 validation 也有 `14.4pct` 的绝对差。相比之下，S5 仍无区分度。

### Validation regime-conditioned readout

| id                               | regime_bucket   |   winner_count |   control_count | effect   |   lift | claim_status                          |
|:---------------------------------|:----------------|---------------:|----------------:|:---------|-------:|:--------------------------------------|
| S2_repair_money_vwap_v0          | risk_off        |            120 |             546 | 14.2%    |   1.18 | sequence_regime_conditional_candidate |
| S2_repair_money_vwap_v0          | risk_on         |             10 |              47 | 14.0%    |   1.21 | sample_blocked_occurrence_count       |
| S2_repair_money_vwap_v0          | transition      |             39 |             204 | 14.5%    |   1.21 | sequence_regime_conditional_candidate |
| S3_repair_rank_persistence_v0    | risk_off        |            120 |             546 | 53.6%    |   4.44 | sequence_regime_conditional_candidate |
| S3_repair_rank_persistence_v0    | risk_on         |             10 |              47 | 32.3%    |   2.17 | sample_blocked_occurrence_count       |
| S3_repair_rank_persistence_v0    | transition      |             39 |             204 | 39.6%    |   2.14 | sequence_regime_conditional_candidate |
| S6_continuation_discriminator_v0 | risk_off        |            120 |             546 | 41.8%    |   2.03 | sequence_regime_conditional_candidate |
| S6_continuation_discriminator_v0 | risk_on         |             10 |              47 | 52.3%    |   2.89 | sample_blocked_occurrence_count       |
| S6_continuation_discriminator_v0 | transition      |             39 |             204 | 53.1%    |   4.28 | sequence_regime_conditional_candidate |

validation 的 regime-conditioned 读数说明：

- S3 在 `risk_off`、`transition` 都强，`risk_on` 因 validation 样本只有 10 个 winner，状态为 sample-blocked，不应过度解释。
- S6 在 `risk_off`、`transition` 都强，`risk_on` 同样受样本数限制。
- S2 在三个 regime 的绝对差都约 14pct，但本质仍是确认序列。

## 6. Near-winner 与 false-repair：为什么“修复”还不够

### Near-winner 对照

| split      |   winner_count |   near_winner_control_count | winner_mfe_120_mean   | near_winner_mfe_120_mean   |
|:-----------|---------------:|----------------------------:|:----------------------|:---------------------------|
| all        |            866 |                        1895 | 84.9%                 | 39.6%                      |
| train      |            285 |                         490 | 81.8%                 | 40.5%                      |
| validation |            169 |                         295 | 71.8%                 | 39.8%                      |
| robustness |            412 |                        1110 | 92.3%                 | 39.1%                      |

near-winner control 的 MFE 已经达到 30%-50%，但仍明显低于 winner。真正有用的是看 sequence 分化：

| split      | sequence_id                      | winner_sequence_rate   | near_winner_sequence_rate   |   lift | absolute_rate_difference   |
|:-----------|:---------------------------------|:-----------------------|:----------------------------|-------:|:---------------------------|
| all        | S2_repair_money_vwap_v0          | 85.1%                  | 83.7%                       |   1.02 | 1.3%                       |
| validation | S2_repair_money_vwap_v0          | 89.3%                  | 88.1%                       |   1.01 | 1.2%                       |
| all        | S3_repair_rank_persistence_v0    | 57.3%                  | 23.7%                       |   2.42 | 33.7%                      |
| validation | S3_repair_rank_persistence_v0    | 69.8%                  | 36.6%                       |   1.91 | 33.2%                      |
| all        | S6_continuation_discriminator_v0 | 79.2%                  | 59.1%                       |   1.34 | 20.1%                      |
| validation | S6_continuation_discriminator_v0 | 79.3%                  | 78.3%                       |   1.01 | 1.0%                       |

洞察：S2 在 winner 与 near-winner 之间差异很小，说明“钱流/VWAP/区间修复”很多强反弹也会出现；S3 的差异更稳定，说明大赢家更需要 rank persistence。S6 在 validation near-winner 中几乎不区分，但在 train/robustness 更明显，说明 continuation discriminator 对不同市场环境敏感，不能单独作为 universal 规则。

### False-repair control

| split      |   control_count |   false_repair_count | false_repair_rate   |   false_repair_10d_count |   false_repair_20d_count | drawdown_anchor_to_plus_20d_mean   | runup_axis_low_to_anchor_plus_20d_mean   |
|:-----------|----------------:|---------------------:|:--------------------|-------------------------:|-------------------------:|:-----------------------------------|:-----------------------------------------|
| all        |            3615 |                 2690 | 74.4%               |                     2547 |                     2466 | -7.1%                              | 19.9%                                    |
| train      |            1061 |                  841 | 79.3%               |                      800 |                      751 | -7.5%                              | 18.2%                                    |
| validation |             753 |                  567 | 75.3%               |                      521 |                      522 | -7.8%                              | 19.2%                                    |
| robustness |            1801 |                 1282 | 71.2%               |                     1226 |                     1193 | -6.5%                              | 21.2%                                    |

false-repair rate 很高，尤其 train 为 `79.3%`、validation 为 `75.3%`。这说明 EMA60 reclaim 后仍可能很快失败，不能把 reclaim 本身升格为入场事件。更合理的 forward 研究方向是：reclaim 后必须叠加相对强度持续、money confirmation、以及避免 10/20 日内失败修复。

## 7. Winner-only 生命周期画像

| stage         | return_20d_mean   |   amount_ratio_20d_mean | close_to_ema60_mean   | close_to_derived_daily_vwap_mean   | atr_20_pct_mean   | stock_vs_market_20d_mean   |
|:--------------|:------------------|------------------------:|:----------------------|:-----------------------------------|:------------------|:---------------------------|
| pre_low_60d   | 2.1%              |                    1.02 | 3.2%                  | -0.0%                              | 4.1%              | 1.6%                       |
| low_to_high   | 7.1%              |                    1.18 | 6.5%                  | 0.1%                               | 4.0%              | 5.3%                       |
| post_high_30d | 3.9%              |                    0.9  | 9.7%                  | -0.1%                              | 5.3%              | 1.5%                       |

winner-only 阶段画像只用于解释生命周期，不用于 winner-vs-control claim。可以看到：

- `low_to_high` 阶段 20 日收益均值、成交额比、EMA60 偏离和 stock-vs-market 明显抬升。
- `post_high_30d` 阶段 EMA60 偏离和 ATR 仍高，但 stock-vs-market 均值下降，说明高点后往往进入波动扩张和相对强度回落。
- `pre_low_60d` 阶段已经有一定正收益和轻微相对强度，但远不如低点后的推进阶段明显。

## 8. 研究含义：下一步 forward event 应该怎么写

当前结果不支持“低点当天靠单因子预测大赢家”。更合理的方向是把它拆成分阶段事件：

1. 候选低点只是 opportunity set，不是信号本身。
2. 第一个可检验事件应发生在低点之后，例如 first EMA60 reclaim。
3. reclaim 后需要确认：money/VWAP 或 range hold 可以作为弱过滤，rank persistence 应作为核心过滤。
4. continuation discriminator 可以作为加仓/确认条件，但它天然滞后，因为需要先观察到从低点口径 +20% 的路径状态。
5. false-repair 需要显式排除：如果 reclaim 后 10/20 日出现明显回撤或无法形成足够 runup，应进入失败修复分支。

因此，本实验给出的不是“买在最低点”的答案，而是“从大赢家倒推，其生命周期里哪些修复和确认最有区分度”。

## 9. 风险与边界

- 本实验是 retrospective profile。control matching 中 `future_label_used_for_profile_only=True`，不能直接作为可交易标签。
- 最强单因子多为低点后的确认变量，不能直接转换成 t0 leading signal。
- PIT industry 数据不可用，行业相对强弱没有纳入；这可能影响 rank persistence 的解释。
- validation risk_on 样本很小，相关 regime-conditioned claim 被 sample-blocked 或只能作提示。
- sequence family 是 requirement-prespecified single variant，没有做结构搜索；因此结论更干净，但也意味着没有探索更多候选序列。
- 如果重新运行 pipeline，自动报告会被覆盖；本报告是基于当前产物的中文解释版。

## 10. 输出与复核

- `big_winner_episode_reference_summary.csv`: `866` rows。
- `shared_axis_factor_dominance.csv`: `13504` rows，其中 conditioned factor rows `12660`。
- `shared_axis_sequence_dominance.csv`: `384` rows，其中 conditioned sequence rows `360`。
- `unconditional_validation_readout.csv`: `217` rows。
- `regime_conditioned_validation_readout.csv`: `651` rows。
- `validation_opportunity_audit.csv`: `6` rows。
- run manifest decision: `reverse_lifecycle_sequence_supported_universal_dominance`。
