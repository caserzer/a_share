# 18C Refresh Payoff-state Separability Diagnostic Report

## 结论

18C refresh 在 18E 刷新后的 49 个 model-ready 特征矩阵上给出正向结论：

```text
decision_state = 18C_payoff_state_separability_supported
next_allowed_requirement = requirement_18f_payoff_state_oracle_gap_bridge.md
next_allowed_requirement_scope = refreshed_matrix_oracle_gap_bridge
all_hard_gates_pass = true
```

这个结论的含义是：当前 49 特征低容量模型已经能在冻结的
robustness split 上提供可复核的 payoff rank separability，因此可以进入
18F，检查这个分离能力是否真的能缩小 oracle action gap。它不等于 entry
policy、exit policy、holding policy、portfolio backtest、model deployment、
production signal 或 live trading 授权；这些授权字段仍全部为 false。

核心证据是四个主门槛同时成立：

| 指标 | 观测值 | 门槛或基准 | 判断 |
|:--|--:|--:|:--|
| robustness payoff rank IC | 0.125362 | >= 0.080000 | pass |
| robustness decile monotonicity Spearman | 0.733333 | >= 0.600000 | pass |
| robustness cluster bootstrap IC CI low | 0.088221 | > 0 | pass |
| rank IC - volatility20d baseline | 0.060590 | > 0.005000 | pass |

AFML 解释：这次不是“二分类能不能分出 positive/negative”的结果，而是
payoff rank 上的连续排序能力通过了支持门槛。下一步应验证该排序是否能解释
继续持有/防守之间的 oracle utility gap，而不是直接把 score 当成交易信号。

## 输入和矩阵完整性

输入审计显示 27 个 required artifacts 全部通过读取、schema 和 cache-key
校验。其中 18E handoff artifact 共 16 个，全部 pass。18E 刷新矩阵本地 cache
存在，且 hash 与 manifest 一致：

```text
source_18e_matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
source_18e_schema_sha256 = 56429807004c0d3ad69101c87d1f125b4c8e33713d702f53f251002fea235a26
```

矩阵 replay 的关键检查如下：

| check | expected | observed | gate |
|:--|--:|--:|:--|
| matrix_row_n | 23405 | 23405 | pass |
| train_row_n | 20245 | 20245 | pass |
| robustness_row_n | 2496 | 2496 | pass |
| validation_row_n | 664 | 664 | pass |
| primary_model_ready_feature_n | 49 | 49 | pass |
| existing_18B_model_ready_feature_n | 23 | 23 | pass |
| refresh_model_ready_feature_n | 26 | 26 | pass |
| target_column_n | 19 | 19 | pass |
| primary_identity_key_duplicate_n | 0 | 0 | pass |
| full_lineage_key_duplicate_n | 0 | 0 | pass |

这说明本次 refresh 没有再停在之前的 cache/schema 问题上：`step_id|label_id`
主键唯一，完整 lineage key 也唯一；18B retained 特征 23 个，18E 新增 refresh
特征 26 个，组成 49 特征矩阵。

score panel 也完整产出：

| artifact | row_count | status | split counts |
|:--|--:|:--|:--|
| refreshed_payoff_state_score_panel.parquet | 23405 | scored | train 20245; robustness 2496; validation 664 |

## Handoff 和 no-search 边界

18E handoff replay 全部通过：18E 决策为
`18E_payoff_state_feature_matrix_refresh_supported`，next scope 为
`refreshed_matrix_rerun`，18D contract、feature source/formula/lineage、PIT
t0 availability、target binding、schema、missingness、family coverage、
train-only preprocessing、forbidden feature 和 search accounting 全部为 pass。

本次 18C refresh 自身的 search accounting 也为 pass：

| 边界 | 结果 |
|:--|:--|
| model family registry predeclared | true |
| primary model predeclared | true |
| no feature selection from target correlation | true |
| no feature selection from robustness/validation | true |
| no model-family selection from robustness/validation | true |
| no threshold tuning on robustness/validation | true |
| no split-local payoff cutoff recompute | true |
| no split-local score threshold recompute for gate | true |
| binary metric not primary gate | true |
| validation stress readout only | true |
| no policy/backtest/deployment/signal/trading authorization | true |

因此，这次正向结论不是通过 OOS 调参、threshold search 或 binary metric
替代主门槛得到的。

## 模型和 OOS 排序能力

主模型是 `ridge_payoff_rank_h20_v1`，只用 train split 拟合，然后冻结参数在
robustness 和 validation 上复用。主模型 OOS readout：

| split | rows | episode clusters | rank IC | continue-advantage rank IC | status |
|:--|--:|--:|--:|--:|:--|
| train | 20245 | 652 | 0.176534 | 0.176534 | train_in_sample |
| robustness | 2496 | 204 | 0.125362 | 0.125362 | pass |
| validation | 664 | 41 | 0.177075 | 0.177075 | stress_readout_only |

`continue_advantage_rank_ic` 与 `payoff_rank_ic` 完全一致，是因为
`continue_advantage` 是 `y_payoff_h20` 的 affine replay；它用于 lineage
一致性检查，不是独立证据。

robustness 上各模型的 payoff rank IC：

| model | robustness rank IC | role |
|:--|--:|:--|
| ridge_payoff_rank_h20_v1 | 0.125362 | primary support |
| elastic_net_payoff_rank_h20_v1 | 0.125205 | diagnostic |
| ridge_ordinal_payoff_state_v1 | 0.074279 | diagnostic |
| shallow_tree_payoff_depth2_v1 | 0.065213 | diagnostic |
| volatility20d_defense_baseline | 0.064772 | same-denominator baseline |

两个线性 payoff-rank 模型的 robustness IC 非常接近，说明结果不是 ridge
单一正则化形式的偶然输出。ordinal 和浅树模型也有正 IC，但未达到主门槛。
更重要的是，主模型相对同分母 volatility baseline 有 0.060590 的 IC 增量，
这使 `baseline_improvement_gate` 通过。

train-only grouped CV 的均值并不强，主 ridge 的 5-fold mean payoff rank IC
只有 0.011940，fold 区间为 -0.047430 到 0.084941。这里的解读不是“CV 选出了
模型”，因为 CV 仅为 diagnostic readout；真正的支持来自预注册主模型在
robustness split 上的冻结 OOS 表现。

## Decile monotonicity

robustness decile curve 不是严格逐档递增，但排序方向稳定，Spearman 为
0.733333，top3-minus-bottom3 payoff gap 为 0.027960，超过 monotonicity gate。

| robustness decile | rows | mean_payoff | mean_continue_advantage | mean_score |
|--:|--:|--:|--:|--:|
| 1 | 444 | 0.015230 | 0.020230 | -0.021486 |
| 2 | 333 | 0.016477 | 0.021477 | -0.002523 |
| 3 | 324 | 0.026491 | 0.031491 | 0.005249 |
| 4 | 247 | 0.033791 | 0.038791 | 0.011321 |
| 5 | 259 | 0.071947 | 0.076947 | 0.016568 |
| 6 | 247 | 0.034978 | 0.039978 | 0.021689 |
| 7 | 202 | 0.049378 | 0.054378 | 0.027498 |
| 8 | 172 | 0.031130 | 0.036130 | 0.033858 |
| 9 | 170 | 0.053387 | 0.058387 | 0.042778 |
| 10 | 98 | 0.063241 | 0.068241 | 0.058887 |

关键观察：中高分区间的 payoff 明显高于低分区间，但 robustness 的第 5 档异常高，
第 8 档回落，因此它是“可用的 rank signal”，不是足以直接当作 deterministic
policy rule 的单调收益阶梯。18F 应重点检查 top-score 区间是否对应更大的
oracle continue advantage，而不是只看 decile 平均 payoff。

validation 是 stress readout only，但方向也支持：

| validation decile | rows | mean_payoff | mean_continue_advantage | mean_score |
|--:|--:|--:|--:|--:|
| 1 | 74 | -0.025739 | -0.020739 | -0.027677 |
| 2 | 61 | 0.001865 | 0.006865 | -0.001599 |
| 3 | 50 | 0.038639 | 0.043639 | 0.004980 |
| 4 | 76 | 0.020397 | 0.025397 | 0.011247 |
| 5 | 72 | 0.025880 | 0.030880 | 0.016521 |
| 6 | 64 | 0.022436 | 0.027436 | 0.022130 |
| 7 | 67 | 0.021363 | 0.026363 | 0.027007 |
| 8 | 69 | 0.026822 | 0.031822 | 0.033861 |
| 9 | 74 | 0.066519 | 0.071519 | 0.043666 |
| 10 | 57 | 0.074812 | 0.079812 | 0.063667 |

validation 的 decile 1 为负，decile 9/10 显著为正，这是一个有意义的 stress
confirmation；但 validation 只有 664 行、41 个 episode clusters，不能反向参与
模型或阈值选择。

## Bucket lift

bucket lift 使用 train-frozen score cutoff，不做 split-local threshold recompute。

| split | bucket | rows | unconditional rate | bucket rate | lift |
|:--|:--|--:|--:|--:|--:|
| train | score_top30_bucket | 6074 | 0.300074 | 0.377017 | 1.256412 |
| train | score_top20_bucket | 4049 | 0.200000 | 0.273895 | 1.369474 |
| robustness | score_top30_bucket | 440 | 0.341346 | 0.375000 | 1.098592 |
| robustness | score_top20_bucket | 268 | 0.234776 | 0.302239 | 1.287352 |
| validation | score_top30_bucket | 200 | 0.319277 | 0.390000 | 1.221509 |
| validation | score_top20_bucket | 131 | 0.218373 | 0.312977 | 1.433219 |

robustness top20 的 lift 为 1.287352，validation top20 的 lift 为 1.433219。
这说明 score 的高分段确实更集中地捕获高 payoff 状态。不过 bucket lift 仍只是
supporting evidence；主结论由连续 rank IC、decile monotonicity、bootstrap 和
baseline improvement 共同决定。

## Bootstrap 和 baseline

cluster bootstrap 使用 `episode_cluster_id`，2000 次 resample 全部有效：

| metric | point | CI low | CI high | valid resamples | status |
|:--|--:|--:|--:|--:|:--|
| robustness payoff rank IC | 0.125362 | 0.088221 | 0.161625 | 2000 | pass |

CI low 大于 0，说明 robustness IC 不是少数 cluster 的单点噪声。与基准相比：

| comparison | model | baseline | delta | hard gate |
|:--|--:|--:|--:|:--|
| payoff_rank_ic_vs_volatility20d | 0.125362 | 0.064772 | 0.060590 | true |
| monotonicity_vs_volatility20d | 0.733333 | 0.139394 | 0.593939 | false |
| payoff_rank_ic_vs_16x_external | 0.125362 | 0.051877 | 0.073485 | false |
| monotonicity_vs_16x_external | 0.733333 | 0.163636 | 0.569697 | false |
| bootstrap_ci_low_vs_16x_external | 0.088221 | 0.007706 | 0.080516 | false |

只有 same-denominator volatility20d baseline 是 hard gate。16X 是外部 coarse
context，分母和目标构造不同，只能辅助说明：刷新后的 18C payoff-state score
比 16X payoff probe 更强，但这不是一个可直接替代 action utility 的证据。

## Family removal sensitivity

robustness family removal 结果：

| removed family | removed n | rank IC after removal | retention | role | insight |
|:--|--:|--:|--:|:--|:--|
| M1 | 8 | 0.094356 | 0.752665 | primary_refresh | refresh morphology family 中影响最大 |
| F2 | 5 | 0.098861 | 0.788607 | 18B retained | flow/volume 对排序有实质贡献 |
| F1 | 7 | 0.101205 | 0.807306 | 18B retained | return/path location 保留贡献 |
| M5 | 6 | 0.102448 | 0.817215 | primary_refresh | episode age/position 有贡献 |
| M3 | 5 | 0.108963 | 0.869187 | primary_refresh | upside-room 类变量有贡献 |
| M2 | 7 | 0.112397 | 0.896578 | primary_refresh | money-flow morphology 有贡献 |
| F4 | 5 | 0.121777 | 0.971401 | 18B retained risk | risk-only gate pass |
| F5 | 4 | 0.130691 | 1.042509 | 18B retained | 去除后略升，非核心正贡献 |
| F3 | 2 | 0.139882 | 1.115822 | 18B retained | 去除后升，可能是噪声或反向约束 |

最重要的结论是：risk-only gate 通过。移除 F4 risk family 后 robustness rank IC
仍为 0.121777，retention 0.971401，高于 0.50，并且仍大于 0。这说明正向结果
不是单纯由 volatility/drawdown/range risk state 驱动。

同时，refresh morphology 的 M1/M5/M3/M2 都有贡献，其中 M1 移除后 retention
降到 0.752665，是新增族中最强的 robustness contributor。这支持 18E refresh 的
研究方向：新特征不是只增加维度，而是在 episode path morphology 上带来额外
payoff ranking 信息。

validation family removal 给出一个风险提示：

| removed family | validation rank IC after removal | validation retention |
|:--|--:|--:|
| F4 | 0.078835 | 0.445209 |
| M3 | 0.138176 | 0.780324 |
| M1 | 0.153871 | 0.868959 |
| M2 | 0.175034 | 0.988474 |
| M5 | 0.204162 | 1.152972 |

validation 中移除 F4 后 retention 降到 0.445209，说明 stress split 对 risk family
更敏感。由于 validation 是 stress readout only，这不会否定 18C refresh 的
supported 决策，但它提示 18F 需要重点检查：score 是在捕获可行动的 payoff
directionality，还是在某些 regime 中仍然依赖 risk-state proxy。

## Top coefficient concentration

主 ridge 的标准化系数前 15 个特征如下：

| rank | feature | family | standardized coefficient |
|--:|:--|:--|--:|
| 1 | mr_volume_20d_zscore | F2 | 0.030175 |
| 2 | mr_max_drawdown_20d | F4 | -0.018054 |
| 3 | mr_money_20d_zscore | F2 | -0.017854 |
| 4 | mr_volatility_60d | F4 | -0.015148 |
| 5 | mr_turnover_rate_20d_mean | F2 | -0.011198 |
| 6 | mr_turnover_rate_20d_zscore | F2 | -0.009842 |
| 7 | mr_m5_bars_since_episode_low | M5 | -0.008790 |
| 8 | mr_ret_20d | F1 | 0.008186 |
| 9 | mr_volatility_20d | F4 | 0.008121 |
| 10 | mr_m5_high_to_t0_age_ratio | M5 | 0.007740 |
| 11 | mr_m2_turnover_compression_20_vs_60 | M2 | -0.007652 |
| 12 | mr_m3_upside_room_to_episode_high | M3 | 0.007246 |
| 13 | mr_ret_5d | F1 | -0.007142 |
| 14 | mr_distance_to_60d_high | F1 | 0.007115 |
| 15 | mr_m5_nonoverlap_step_index_to_t0 | M5 | 0.005849 |

Top-k removal 更清楚地显示了 concentration：

| removal | robustness rank IC after removal | retention |
|:--|--:|--:|
| top1_abs_coefficient_removed | -0.000260 | -0.002073 |
| top3_abs_coefficient_removed | 0.086959 | 0.693664 |
| top5_abs_coefficient_removed | 0.007239 | 0.057747 |

解释：排序能力高度依赖少数 flow/risk/path 特征，特别是
`mr_volume_20d_zscore`。这不是坏事，因为模型是低容量 ridge；但这意味着 18F
不应只验证平均 IC，还应检查高贡献特征对应的 action mechanism 是否稳定。如果
单个 volume/flow 变量只是 liquidity regime proxy，utility bridge 可能仍然失败。

## Binary sanity

binary sanity 结果不是主门槛，且所有 `binary_metric_used_as_primary_gate` 均为
false。

| split | model | target | roc_auc | AP | base rate | precision lift |
|:--|:--|:--|--:|--:|--:|--:|
| robustness | ridge_logistic_top30_sanity_v1 | top30_yes_no | 0.568169 | 0.403892 | 0.341346 | 0.062546 |
| robustness | ridge_logistic_top20_sanity_v1 | top20_yes_no | 0.581185 | 0.295647 | 0.234776 | 0.060872 |
| robustness | ridge_payoff_rank_h20_v1 | binary_positive_negative | 0.506831 | 0.756417 | 0.750000 | 0.006417 |

这里的 insight 是：top30/top20 binary sanity 有一定增益，但
positive/negative 二分类几乎没有 AUC 优势。18C refresh 支持的是 payoff rank
ordering，不是一个强 binary classifier。因此 18F 不应把它简化为
yes/no continuation classifier，而应使用 score 的连续排序和 oracle action value
gap 进行桥接。

## Findings

1. 18E refresh 解决了原 18C 特征表达不足的问题。49 特征矩阵在 robustness 上
   产生 0.125362 的 payoff rank IC，超过 0.08 materiality floor，并且 bootstrap
   CI low 为 0.088221。

2. 这个 signal 不是纯 risk-state proxy。F4 risk family 移除后 robustness rank
   IC 仍为 0.121777，retention 0.971401，因此 risk-only gate pass。

3. 新增 morphology features 有实质贡献。M1 removal 的 robustness retention 为
   0.752665，是 refresh families 中最强的贡献来源；M5/M3/M2 也都有正贡献。

4. 高分 bucket 对 payoff state 有 lift。robustness top20 bucket lift 为 1.287352，
   validation top20 bucket lift 为 1.433219，说明 train-frozen score cutoff 在
   OOS split 上仍有排序含义。

5. 需要防止过度解释。robustness decile curve 不是严格单调，validation 对 F4
   risk family 更敏感，top-k removal 显示排序能力集中在少数 flow/risk/path
   特征上。这些都要求 18F 做 oracle-gap bridge，而不是直接进入 policy。

## 18F Handoff

18F 可以使用本次产出的 `refreshed_payoff_state_score_panel.parquet` 作为冻结输入，
但必须保持以下边界：

```text
source_18e_matrix_sha256 = 03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc
score_panel_sha256 = a3f431c8b634dcb9d24b31a5ed38574b94e7332672d4861470037837492cfc2c
score_panel_status = scored
score_panel_row_n = 23405
primary_model_id = ridge_payoff_rank_h20_v1
primary_split = robustness
primary_target_id = y_payoff_h20
```

18F 的核心问题应是：这个 payoff-state score 是否能解释继续持有与防守之间的
oracle gap，并形成 action-value bridge。如果 18F 发现 score 只是在捕获高波动、
流动性或 episode path regime，而不能区分 action utility，那么 18C refresh 的
supported 结论仍应降级为 representation insight，而不是 policy precursor。
