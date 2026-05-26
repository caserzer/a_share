# R07 周度市场残差 IMOM 风险赛跑本地复刻报告

## 1. 结论

`final_decision = ep6_weekly_imom_local_proxy_not_supported`

`authorized_strategy_requirement = false`

本实验复刻的是论文中 weekly idiosyncratic momentum horse-race 的本地代理版本。这里的 `IMOM` 不是论文的 CSMAR FF5 残差动量，而是 `market_model_sh000300_ols_v0` 下的市场残差动量，因此结论应解释为“本地市场残差代理不支持”，不能直接解释为论文结论被否定。

核心结论有三点：

1. 主信号没有通过。短周期簇 `J in {2,3,4,8,13}`、`K in {1,2,3,4}` 中，validation 段 IMOM gross 周均收益为 `-0.247%`，Newey-West t-stat 均值为 `-0.896`，20 个短周期 cell 里只有 `5.0%` 的 cell 为正。robustness 段转正到 `0.174%`，但 validation 已经失败，不能视为稳定复刻。
2. 风险过滤有局部信号。`IVOL x IMOM` 双重排序在 validation 和 robustness 两段 gross 都为正，分别为 `0.474%` 和 `0.438%`，且通过同一风险指标跨段一致的 horse-race gate。但 after-cost 仍为负，validation 为 `-0.151%`，robustness 为 `-0.200%`。
3. 成本直接压垮可交易解释。配置使用买入 `30 bps`、卖出 `80 bps`，短周期簇的目标权重买入 turnover 均值约 `0.57-0.62`。IMOM validation 从 gross `-0.247%` 进一步降到 after-cost `-0.926%`；即使 IVOL 双重排序 gross 为正，after-cost 也未转正。

因此，本实验可以保留两个诊断性发现：第一，A 股本地样本中“单纯市场残差 IMOM”不是一个稳定的正收益代理；第二，IVOL 条件过滤确实改善了 gross 结果，但改善幅度不足以抵消交易成本，也不足以授权任何策略使用。

## 2. 数据与实现边界

样本与切分：

| 项 | 值 |
|:--|:--|
| provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| benchmark | `data/qlib/cn_data_pit/features/sh000300` |
| warmup | `2017-01-03` to `2018-06-30` |
| train | `2018-07-01` to `2021-12-31` |
| validation | `2022-01-01` to `2023-12-31` |
| robustness | `2024-01-01` to `2025-12-31` |
| J grid | `[2, 3, 4, 8, 13, 26, 52]` |
| K grid | `[1, 2, 3, 4, 8, 13, 26, 52]` |
| short cluster | `J in {2,3,4,8,13}`, `K in {1,2,3,4}` |
| cost model | buy `30 bps`, sell `80 bps`, round-trip `110 bps` |
| drift-adjusted weights | not reported, primary after-cost uses target-weight turnover |

本地输入可得性：

| input_id | 本地状态 | 本地处理 |
|:--|:--|:--|
| raw stock returns | available_full | 使用 provider 调整后的 close return |
| CSMAR FF5 residual returns | missing_required_factor_source | 用 `SH000300` rolling market model 代理 |
| idiosyncratic risk metrics | available_partial | 基于本地 market residual panel 计算 |
| market state | available_full | 使用 `SH000300` 26w / 52w 状态 |
| liquidity state | available_full | 使用本地 Amihud 4w AILLIQ，train-only 阈值 |
| sentiment state | missing_required_sentiment_source | 阻断，不参与结论 |

残差模型约束：

| 项 | 值 |
|:--|:--|
| beta window | 130 trading days |
| beta min valid days | 90 |
| risk metric window | 130 trading days |
| valid return day | finite close and previous close, `volume > 0`, `money > 0`, finite SH000300 return |
| shortened beta window | false |
| suspended return zero fill | false |
| residual non-null count | 1,088,624 |
| residual instrument count | 539 |

周历使用 Friday-ending calendar week。候选周交易日数 `<= 2` 的周被跳过，周收益分母回退到上一 retained week。全样本周历共有 `477` 个候选周，保留 `462` 个，跳过 `15` 个：

| calendar_week_id | calendar_friday | trading_days | retained week_end | previous_retained_week_end |
|:--|:--|--:|:--|:--|
| 2017-W05 | 2017-02-03 | 1 | 2017-02-03 | 2017-01-26 |
| 2018-W08 | 2018-02-23 | 2 | 2018-02-23 | 2018-02-14 |
| 2019-W18 | 2019-05-03 | 2 | 2019-04-30 | 2019-04-26 |
| 2019-W40 | 2019-10-04 | 1 | 2019-09-30 | 2019-09-27 |
| 2020-W41 | 2020-10-09 | 1 | 2020-10-09 | 2020-09-30 |
| 2021-W07 | 2021-02-19 | 2 | 2021-02-19 | 2021-02-10 |
| 2021-W18 | 2021-05-07 | 2 | 2021-05-07 | 2021-04-30 |
| 2021-W40 | 2021-10-08 | 1 | 2021-10-08 | 2021-09-30 |
| 2022-W18 | 2022-05-06 | 2 | 2022-05-06 | 2022-04-29 |
| 2023-W18 | 2023-05-05 | 2 | 2023-05-05 | 2023-04-28 |
| 2024-W18 | 2024-05-03 | 2 | 2024-04-30 | 2024-04-26 |
| 2024-W40 | 2024-10-04 | 1 | 2024-09-30 | 2024-09-27 |
| 2025-W05 | 2025-01-31 | 1 | 2025-01-27 | 2025-01-24 |
| 2025-W40 | 2025-10-03 | 2 | 2025-09-30 | 2025-09-26 |
| 2025-W41 | 2025-10-10 | 2 | 2025-10-10 | 2025-09-26 |

首个合格信号周：

| J | first evaluable signal week |
|--:|:--|
| 2 | 2018-06-29 |
| 3 | 2018-06-29 |
| 4 | 2018-06-29 |
| 8 | 2018-06-29 |
| 13 | 2018-06-29 |
| 26 | 2018-06-29 |
| 52 | 2019-02-22 |

覆盖审计：

| split | rows | weeks | pit_mean | pit_min | raw_valid_mean | imom_valid_mean | raw_complete_share | imom_complete_share |
|:--|--:|--:|--:|--:|--:|--:|:--|:--|
| train | 1218 | 174 | 186.132 | 114 | 181.540 | 179.054 | 93.1% | 90.7% |
| validation | 686 | 98 | 225.582 | 0 | 223.430 | 219.582 | 99.0% | 96.6% |
| robustness | 693 | 99 | 226.596 | 180 | 224.333 | 219.703 | 100.0% | 97.0% |

细分到 J 后，validation 和 robustness 的主要覆盖如下：

| split | J | weeks | pit_mean | pit_min | raw_valid_mean | imom_valid_mean | raw_complete | imom_complete |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| validation | 2 | 98 | 225.582 | 0 | 225.388 | 188.061 | 97 | 81 |
| validation | 3 | 98 | 225.582 | 0 | 225.306 | 225.429 | 97 | 97 |
| validation | 4 | 98 | 225.582 | 0 | 225.235 | 225.469 | 97 | 97 |
| validation | 8 | 98 | 225.582 | 0 | 224.908 | 225.531 | 97 | 97 |
| validation | 13 | 98 | 225.582 | 0 | 224.316 | 225.286 | 97 | 97 |
| validation | 26 | 98 | 225.582 | 0 | 222.531 | 224.449 | 97 | 97 |
| validation | 52 | 98 | 225.582 | 0 | 216.327 | 222.847 | 97 | 97 |
| robustness | 2 | 99 | 226.596 | 180 | 226.111 | 179.980 | 99 | 78 |
| robustness | 3 | 99 | 226.596 | 180 | 225.970 | 226.212 | 99 | 99 |
| robustness | 4 | 99 | 226.596 | 180 | 225.828 | 226.222 | 99 | 99 |
| robustness | 8 | 99 | 226.596 | 180 | 225.263 | 226.455 | 99 | 99 |
| robustness | 13 | 99 | 226.596 | 180 | 224.515 | 226.556 | 99 | 99 |
| robustness | 26 | 99 | 226.596 | 180 | 222.949 | 226.404 | 99 | 99 |
| robustness | 52 | 99 | 226.596 | 180 | 219.697 | 226.091 | 99 | 99 |

一个需要记录的审计问题：`r07_money_unit_audit.csv` 的前 10 个 sample day 均为 `instrument_count = 0`，因此它没有实际验证 `money` 字段的 CNY 单位分布。这个问题不直接改变本轮收益结论，但削弱了流动性状态审计的可读性；后续如果继续使用 Amihud 状态，应重新抽取有 PIT 成员的日期做 money 分布审计。

## 3. 主结果总览

下表为 short cluster 的 cell 均值。`cells = 20` 表示 `5` 个 J 乘 `4` 个 K。`gross_t` 和 `after_cost_t` 是各 cell 的 Newey-West t-stat 均值，不是把所有 cell 合并后的单一统计量。

| 组合 | split | cells | week_min | week_median | gross_mean | gross_t | positive_cell_share | positive_week_share | after_cost_mean | after_cost_t | turnover_buy | mean_drawdown |
|:--|:--|--:|--:|--:|:--|--:|:--|:--|:--|--:|--:|:--|
| Raw W-L | train | 20 | 165 | 172.0 | 0.113% | 0.438 | 90.0% | 52.9% | -0.571% | -2.086 | 0.622 | -31.384% |
| Raw W-L | validation | 20 | 97 | 98.0 | -0.352% | -1.198 | 0.0% | 43.5% | -1.024% | -3.437 | 0.611 | -42.498% |
| Raw W-L | robustness | 20 | 99 | 99.0 | 0.145% | 0.549 | 60.0% | 51.9% | -0.523% | -1.735 | 0.607 | -29.319% |
| IMOM | train | 20 | 133 | 169.0 | -0.061% | -0.240 | 30.0% | 48.9% | -0.739% | -3.031 | 0.616 | -35.546% |
| IMOM | validation | 20 | 81 | 98.0 | -0.247% | -0.896 | 5.0% | 45.4% | -0.926% | -3.235 | 0.618 | -37.809% |
| IMOM | robustness | 20 | 78 | 99.0 | 0.174% | 0.653 | 90.0% | 52.4% | -0.496% | -1.811 | 0.609 | -21.150% |
| IVOL x IMOM | train | 20 | 37 | 66.5 | -0.159% | -0.387 | 30.0% | 44.3% | -0.787% | -1.712 | 0.571 | -35.882% |
| IVOL x IMOM | validation | 20 | 39 | 65.0 | 0.474% | 1.079 | 90.0% | 56.4% | -0.151% | -0.307 | 0.568 | -18.874% |
| IVOL x IMOM | robustness | 20 | 42 | 69.0 | 0.438% | 0.959 | 100.0% | 59.4% | -0.200% | -0.420 | 0.580 | -23.110% |
| IMD x IMOM | train | 20 | 64 | 119.0 | -0.435% | -1.341 | 5.0% | 45.0% | -1.100% | -3.244 | 0.605 | -54.072% |
| IMD x IMOM | validation | 20 | 48 | 88.0 | -0.080% | -0.279 | 30.0% | 49.8% | -0.737% | -2.017 | 0.598 | -34.537% |
| IMD x IMOM | robustness | 20 | 60 | 94.0 | 0.230% | 0.696 | 100.0% | 55.6% | -0.430% | -1.288 | 0.600 | -23.754% |

这张表说明：

- Raw W-L 在 validation 段是明显反转方向，W-L 为 `-0.352%`，对应 L-W contrarian 为 `+0.352%`。这也是 `validation_imom_beats_raw_best_direction` 的比较阈值。
- IMOM 在 validation 没有改善到正收益，反而仍为 `-0.247%`。它比 raw W-L 少亏一点，但没有超过 raw 的最佳方向。
- IVOL x IMOM 是唯一在 validation 和 robustness 同时 gross 为正的主要风险交叉组合，但 after-cost 依旧为负。
- 成本拖累约为每周 `0.62-0.68%`。这与 weekly rebalancing、短 holding overlap 和目标权重 turnover 共同相关。

## 4. Gate replay

| gate | passed | value | threshold |
|:--|:--|:--|:--|
| validation_evaluable_short_cluster_cell_count | True | 20 | 16 |
| robustness_evaluable_short_cluster_cell_count | True | 20 | 16 |
| validation_short_cluster_min_week_count_per_cell | True | 81 | 52 |
| robustness_short_cluster_min_week_count_per_cell | True | 78 | 52 |
| validation_imom_beats_raw_best_direction | False | -0.247% | 0.352% |
| validation_imom_mean_positive | False | -0.247% | 0 |
| validation_imom_t_stat_positive | False | -0.896 | 0 |
| robustness_imom_mean_positive | True | 0.174% | 0 |
| robustness_imom_t_stat_positive | True | 0.653 | 0 |
| single_IVOL_or_IMD_bivariate_metric_passes_both_splits | True | IVOL | same metric validation and robustness >= IMOM |
| validation_imom_after_cost_mean_positive | False | -0.926% | 0 |
| validation_imom_after_cost_t_stat_positive | False | -3.235 | 0 |
| robustness_imom_after_cost_mean_positive | False | -0.496% | 0 |
| robustness_imom_after_cost_t_stat_positive | False | -1.811 | 0 |

Gate 的含义很直接：样本覆盖足够，风险过滤 gross 有改善，但主 IMOM validation 失败，而且 after-cost guard 两段均失败。最终决策不是因为数据不足，而是因为本地代理信号本身没有达到复刻要求。

## 5. J/K 细节

### 5.1 IMOM short cluster gross matrix

Validation：

| J | K1 | K2 | K3 | K4 |
|--:|:--|:--|:--|:--|
| 2 | 0.008% | -0.203% | -0.228% | -0.159% |
| 3 | -0.233% | -0.280% | -0.254% | -0.292% |
| 4 | -0.282% | -0.278% | -0.296% | -0.340% |
| 8 | -0.545% | -0.430% | -0.277% | -0.248% |
| 13 | -0.185% | -0.149% | -0.126% | -0.137% |

Robustness：

| J | K1 | K2 | K3 | K4 |
|--:|:--|:--|:--|:--|
| 2 | 0.492% | 0.420% | 0.320% | 0.280% |
| 3 | 0.353% | 0.359% | 0.269% | 0.145% |
| 4 | 0.108% | 0.193% | 0.106% | 0.085% |
| 8 | 0.101% | 0.085% | 0.062% | 0.007% |
| 13 | 0.069% | 0.062% | -0.003% | -0.041% |

IMOM 的 J/K 图像显示出明显的时段不稳定。validation 段几乎整片为负，只有 `J=2,K=1` 近似持平；robustness 段则主要由 `J=2` 和 `J=3` 短形成期贡献，J 拉长后收益快速衰减。这个形态更像局部短期反弹或短期横截面风险偏好变化，而不是稳定的 idiosyncratic momentum。

### 5.2 IVOL x IMOM short cluster gross matrix

Validation：

| J | K1 | K2 | K3 | K4 |
|--:|:--|:--|:--|:--|
| 2 | 0.414% | 0.831% | 0.517% | 0.453% |
| 3 | 1.183% | 0.911% | 0.524% | 0.593% |
| 4 | 0.422% | 0.531% | 0.261% | 0.294% |
| 8 | -0.025% | -0.015% | 0.229% | 0.385% |
| 13 | 0.367% | 0.545% | 0.449% | 0.617% |

Robustness：

| J | K1 | K2 | K3 | K4 |
|--:|:--|:--|:--|:--|
| 2 | 1.191% | 0.937% | 0.565% | 0.170% |
| 3 | 0.206% | 0.167% | 0.158% | 0.070% |
| 4 | 0.194% | 0.203% | 0.034% | 0.082% |
| 8 | 0.341% | 0.140% | 0.255% | 0.146% |
| 13 | 1.429% | 1.059% | 0.804% | 0.614% |

IVOL 双重排序的 gross 改善比较广，不是单一 cell 贡献。validation 段 20 个 cell 中 18 个为正，robustness 段 20 个 cell 全为正。但这组组合的 week_count 明显低于单排序，因为 5x5 交集约束导致部分周被 block。它是“风险过滤改善 gross”的证据，不是“可交易收益已经成立”的证据。

### 5.3 全网格最好与最差 cell

| 组合 | split | side | J | K | weeks | gross | t | after_cost | after_cost_t | pos_week | turnover | blocked |
|:--|:--|:--|--:|--:|--:|:--|--:|:--|--:|:--|--:|--:|
| Raw W-L | validation | best | 2 | 52 | 98 | 0.059% | 0.583 | 0.021% | 0.204 | 54.1% | 0.035 | 0 |
| Raw W-L | validation | worst | 26 | 1 | 97 | -0.562% | -1.470 | -1.090% | -2.831 | 43.3% | 0.480 | 1 |
| Raw W-L | robustness | best | 2 | 1 | 99 | 0.481% | 1.555 | -0.939% | -3.024 | 61.6% | 1.290 | 0 |
| Raw W-L | robustness | worst | 26 | 4 | 99 | -0.210% | -0.596 | -0.453% | -1.280 | 48.5% | 0.221 | 0 |
| IMOM | validation | best | 52 | 52 | 98 | 0.264% | 2.704 | 0.223% | 2.296 | 57.1% | 0.037 | 0 |
| IMOM | validation | worst | 26 | 2 | 98 | -0.650% | -1.926 | -1.045% | -3.039 | 40.8% | 0.359 | 0 |
| IMOM | robustness | best | 2 | 1 | 78 | 0.492% | 1.463 | -0.883% | -2.643 | 65.4% | 1.250 | 21 |
| IMOM | robustness | worst | 52 | 4 | 99 | -0.490% | -2.369 | -0.764% | -3.653 | 43.4% | 0.249 | 0 |
| IVOL x IMOM | validation | best | 3 | 1 | 43 | 1.183% | 1.759 | 0.142% | 0.209 | 62.8% | 0.946 | 55 |
| IVOL x IMOM | validation | worst | 26 | 1 | 56 | -0.084% | -0.155 | -0.755% | -1.393 | 50.0% | 0.610 | 42 |
| IVOL x IMOM | robustness | best | 13 | 1 | 50 | 1.429% | 3.031 | 0.740% | 1.610 | 70.0% | 0.626 | 49 |
| IVOL x IMOM | robustness | worst | 52 | 4 | 78 | -0.648% | -1.600 | -0.949% | -2.337 | 44.9% | 0.273 | 21 |
| IMD x IMOM | validation | best | 2 | 2 | 66 | 0.665% | 1.752 | -0.103% | -0.273 | 57.6% | 0.699 | 32 |
| IMD x IMOM | validation | worst | 4 | 2 | 81 | -0.578% | -1.703 | -1.261% | -3.702 | 43.2% | 0.621 | 17 |
| IMD x IMOM | robustness | best | 2 | 2 | 75 | 0.570% | 1.651 | -0.283% | -0.823 | 64.0% | 0.775 | 24 |
| IMD x IMOM | robustness | worst | 52 | 8 | 99 | -0.348% | -0.951 | -0.557% | -1.516 | 52.5% | 0.191 | 0 |

这张表提示两个风险：

- 单个漂亮 cell 不能代表论文复刻成功。例如 validation 中 IMOM `J=52,K=52` after-cost 为 `0.223%` 且 t-stat 为 `2.296`，但它不属于主 short cluster，且 robustness 中长 J cell 并不稳定。
- IVOL x IMOM 的最好 cell 有较高 block 数。validation 最好 cell `J=3,K=1` 有 `55` 个 blocked week，robustness 最好 cell `J=13,K=1` 有 `49` 个 blocked week。5x5 交集提高了信号质量，但也降低了可用周数。

## 6. 风险指标 horse race

### 6.1 双重排序：risk bucket x IMOM bucket

| metric_id | split | cells | gross_mean | gross_t | after_cost_mean | after_cost_t | positive_cell_share |
|:--|:--|--:|:--|--:|:--|--:|:--|
| IVOL | validation | 20 | 0.474% | 1.079 | -0.151% | -0.307 | 90.0% |
| IVAR1 | validation | 20 | 0.318% | 0.787 | -0.341% | -0.871 | 100.0% |
| IVAR5 | validation | 20 | 0.307% | 0.758 | -0.325% | -0.750 | 85.0% |
| IES5 | validation | 20 | 0.215% | 0.495 | -0.442% | -1.035 | 75.0% |
| IES1 | validation | 20 | 0.149% | 0.341 | -0.504% | -1.243 | 75.0% |
| IMD | validation | 20 | -0.080% | -0.279 | -0.737% | -2.017 | 30.0% |
| IVOL | robustness | 20 | 0.438% | 0.959 | -0.200% | -0.420 | 100.0% |
| IES5 | robustness | 20 | 0.284% | 0.744 | -0.376% | -0.932 | 85.0% |
| IMD | robustness | 20 | 0.230% | 0.696 | -0.430% | -1.288 | 100.0% |
| IVAR5 | robustness | 20 | 0.160% | 0.440 | -0.491% | -1.238 | 70.0% |
| IES1 | robustness | 20 | 0.157% | 0.470 | -0.504% | -1.381 | 75.0% |
| IVAR1 | robustness | 20 | 0.105% | 0.307 | -0.552% | -1.518 | 70.0% |

IVOL 是唯一满足“同一 metric 在 validation 与 robustness 都优于 IMOM”的强风险过滤指标。IMD 在 robustness 为正，但 validation 为 `-0.080%`，不应与 IVOL 并列解释为本地强支持。更准确的读法是：本地数据支持“IVOL 条件过滤改善 gross”，不支持“IVOL/IMD 都稳定强”。

### 6.2 直接风险调整 IMOM

| metric_id | split | gross_mean | gross_t | after_cost_mean | after_cost_t | positive_cell_share |
|:--|:--|:--|--:|:--|--:|:--|
| IMD | validation | -0.185% | -0.815 | -0.904% | -3.606 | 15.0% |
| IES1 | validation | -0.186% | -0.771 | -0.895% | -3.523 | 10.0% |
| IVOL | validation | -0.194% | -0.824 | -0.917% | -3.646 | 10.0% |
| IVAR5 | validation | -0.199% | -0.850 | -0.919% | -3.645 | 10.0% |
| IVAR1 | validation | -0.210% | -0.912 | -0.922% | -3.708 | 5.0% |
| IES5 | validation | -0.214% | -0.901 | -0.932% | -3.668 | 0.0% |
| IVOL | robustness | 0.226% | 0.906 | -0.483% | -1.861 | 100.0% |
| IVAR5 | robustness | 0.175% | 0.717 | -0.527% | -2.119 | 80.0% |
| IES1 | robustness | 0.156% | 0.660 | -0.537% | -2.232 | 90.0% |
| IES5 | robustness | 0.142% | 0.598 | -0.561% | -2.283 | 80.0% |
| IVAR1 | robustness | 0.126% | 0.532 | -0.573% | -2.405 | 80.0% |
| IMD | robustness | 0.125% | 0.510 | -0.584% | -2.364 | 75.0% |

直接风险调整在 validation 段全部为负，说明改善不是来自“简单扣掉风险指标”这个线性处理，而是来自双重排序交集。换言之，本地可见的风险效果更像横截面条件过滤，而不是稳定的残差动量净化。

### 6.3 Risk-only 对照

| metric_id | split | gross_mean | gross_t | after_cost_mean | after_cost_t | positive_cell_share |
|:--|:--|:--|--:|:--|--:|:--|
| IVOL | validation | 0.591% | 1.622 | 0.458% | 1.247 | 100.0% |
| IVAR5 | validation | 0.588% | 1.551 | 0.434% | 1.140 | 100.0% |
| IES5 | validation | 0.428% | 1.167 | 0.275% | 0.745 | 100.0% |
| IVAR1 | validation | 0.377% | 1.104 | 0.215% | 0.626 | 100.0% |
| IES1 | validation | 0.343% | 0.995 | 0.187% | 0.536 | 100.0% |
| IMD | validation | 0.276% | 0.828 | 0.083% | 0.246 | 100.0% |
| ISKEW | validation | 0.056% | 0.354 | -0.193% | -1.204 | 100.0% |
| IKURT | validation | -0.528% | -2.332 | -0.788% | -3.498 | 0.0% |
| ISKEW | robustness | 0.238% | 1.185 | -0.013% | -0.057 | 100.0% |
| IVOL | robustness | 0.023% | 0.059 | -0.135% | -0.356 | 100.0% |
| IVAR5 | robustness | -0.016% | -0.042 | -0.214% | -0.594 | 25.0% |
| IES5 | robustness | -0.042% | -0.116 | -0.218% | -0.611 | 0.0% |
| IKURT | robustness | -0.095% | -0.526 | -0.335% | -1.864 | 0.0% |
| IVAR1 | robustness | -0.117% | -0.340 | -0.306% | -0.895 | 0.0% |
| IMD | robustness | -0.119% | -0.361 | -0.356% | -1.094 | 0.0% |
| IES1 | robustness | -0.134% | -0.413 | -0.317% | -0.979 | 0.0% |

Risk-only 的 validation 很强，尤其 IVOL 和 IVAR5 after-cost 仍为正；但 robustness 迅速衰减。这说明 2022-2023 的风险排序收益可能很强，但它不是跨段稳定的独立风险溢价。R07 的主问题不是找到 risk-only 策略，而是检验 IMOM 与风险指标的论文式关系，因此 risk-only 只能作为解释线索。

## 7. 条件状态诊断

### 7.1 IMOM 条件状态

| state_axis | state_value | split | week_count | gross_mean | after_cost_mean | positive_week_share |
|:--|:--|:--|--:|:--|:--|:--|
| liquidity_state | high_liquidity | validation | 1776 | -0.178% | -0.840% | 45.6% |
| liquidity_state | low_liquidity | validation | 140 | -1.311% | -2.127% | 37.9% |
| liquidity_state | unavailable | validation | 15 | 1.228% | 0.821% | 93.3% |
| liquidity_state | high_liquidity | robustness | 1910 | 0.158% | -0.503% | 52.0% |
| liquidity_state | low_liquidity | robustness | 37 | 0.746% | 0.074% | 62.2% |
| liquidity_extreme_state | extreme_high_liquidity | validation | 911 | 0.275% | -0.389% | 50.8% |
| liquidity_extreme_state | middle_liquidity | validation | 1005 | -0.746% | -1.429% | 39.8% |
| liquidity_extreme_state | unavailable | validation | 15 | 1.228% | 0.821% | 93.3% |
| liquidity_extreme_state | extreme_high_liquidity | robustness | 1494 | 0.261% | -0.393% | 53.2% |
| liquidity_extreme_state | middle_liquidity | robustness | 453 | -0.135% | -0.816% | 49.0% |
| market_state_26w | downside | validation | 1694 | -0.255% | -0.922% | 46.0% |
| market_state_26w | upside | validation | 237 | -0.207% | -0.914% | 41.4% |
| market_state_26w | downside | robustness | 640 | 0.104% | -0.548% | 53.6% |
| market_state_26w | upside | robustness | 1307 | 0.200% | -0.464% | 51.6% |
| market_state_52w | downside | validation | 1891 | -0.312% | -0.985% | 45.2% |
| market_state_52w | upside | validation | 40 | 2.718% | 2.094% | 57.5% |
| market_state_52w | downside | robustness | 747 | 0.067% | -0.610% | 50.6% |
| market_state_52w | upside | robustness | 1200 | 0.232% | -0.418% | 53.2% |

IMOM 的状态诊断更支持“流动性改善有帮助”，不支持“市场上涨状态稳定强化 IMOM”。Validation 中高流动性明显好于低流动性，极高流动性也从负转正；但 after-cost 仍为负。52w upside validation 的 gross `2.718%` 很高，但只有 `40` 个 week-observations，不能作为主结论。

### 7.2 IVOL x IMOM 条件状态

| state_axis | state_value | split | week_count | gross_mean | after_cost_mean | positive_week_share |
|:--|:--|:--|--:|:--|:--|:--|
| liquidity_state | high_liquidity | validation | 1195 | 0.547% | -0.048% | 56.8% |
| liquidity_state | low_liquidity | validation | 62 | -1.157% | -1.600% | 48.4% |
| liquidity_state | unavailable | validation | 2 | 1.995% | 1.995% | 100.0% |
| liquidity_state | high_liquidity | robustness | 1298 | 0.334% | -0.271% | 59.0% |
| liquidity_state | low_liquidity | robustness | 37 | 2.446% | 1.830% | 67.6% |
| liquidity_extreme_state | extreme_high_liquidity | validation | 595 | 1.047% | 0.413% | 61.2% |
| liquidity_extreme_state | middle_liquidity | validation | 662 | -0.062% | -0.607% | 52.1% |
| liquidity_extreme_state | unavailable | validation | 2 | 1.995% | 1.995% | 100.0% |
| liquidity_extreme_state | extreme_high_liquidity | robustness | 923 | -0.037% | -0.634% | 56.0% |
| liquidity_extreme_state | middle_liquidity | robustness | 412 | 1.356% | 0.729% | 66.5% |
| market_state_26w | downside | validation | 1085 | 0.457% | -0.117% | 57.1% |
| market_state_26w | upside | validation | 174 | 0.514% | -0.146% | 52.3% |
| market_state_26w | downside | robustness | 488 | 0.961% | 0.407% | 60.9% |
| market_state_26w | upside | robustness | 847 | 0.065% | -0.571% | 58.3% |
| market_state_52w | downside | validation | 1242 | 0.358% | -0.230% | 55.9% |
| market_state_52w | upside | validation | 17 | 8.304% | 7.846% | 100.0% |
| market_state_52w | downside | robustness | 535 | 1.265% | 0.648% | 67.5% |
| market_state_52w | upside | robustness | 800 | -0.191% | -0.789% | 53.8% |

IVOL x IMOM 的状态读数更有研究价值，但方向与论文的“upside market strengthens IMOM”并不完全一致。robustness 中 26w 和 52w downside 都强于 upside，说明本地 IVOL 条件收益可能更像“压力状态下的高风险补偿”或“风险偏好反弹”，而不是传统上涨市场中的动量延续。

流动性状态上，validation 的 `high_liquidity` 和 `extreme_high_liquidity` 明显改善，`extreme_high_liquidity` after-cost 也达到 `0.413%`。但 robustness 中 `extreme_high_liquidity` 反而为负，`middle_liquidity` 为正，说明流动性分层不是一个跨段稳定的硬规则。

## 8. 与论文方向的对照

| 论文方向 | 本地测试 | 本地支持度 |
|:--|:--|:--|
| raw weekly MOM 多数表现为反转 | Raw W-L short cluster | 部分支持。validation 为 `-0.352%`，但 train 和 robustness 为正 |
| IMOM 为正且强于 raw-return 方向 | IMOM vs raw best direction | 不支持。validation IMOM 为 `-0.247%`，且未超过 raw contrarian `+0.352%` |
| IVOL 和 IMD 是强风险指标 | bivariate risk x IMOM | 只支持 IVOL。IMD validation 为负 |
| bivariate risk-adjusted IMOM 改善结果 | IVOL x IMOM vs pure IMOM | gross 支持，after-cost 不支持 |
| upside market 强化 IMOM | SH000300 26w / 52w 状态 | 不稳定，部分小样本 cell 很强但不可作主结论 |
| high liquidity 强化 IMOM | local Amihud 4w 状态 | 部分支持，尤其 validation；after-cost 与跨段稳定性不足 |
| high sentiment 强化 IMOM | sentiment inputs | 本地不可评估 |

## 9. 发现与解释

**发现 1：本地市场残差 IMOM 没有复刻论文核心方向。**
Validation 是本实验的关键段，IMOM short cluster 的 gross 为 `-0.247%`，20 个 cell 只有 1 个为正。这不是统计显著性不足的问题，而是方向本身没有站住。Robustness 转正只能说明后段市场里出现过相同方向的短期收益，不能补救 validation 失败。

**发现 2：raw weekly momentum 的本地形态更像阶段性反转，而不是稳定动量。**
Raw W-L validation 为 `-0.352%`，说明 winner-minus-loser 在 2022-2023 更偏反转；但 train 与 robustness 又为正。这个时间不稳定性会直接污染 IMOM 的解释，因为 IMOM 的目标本来是从 raw return 中剥离系统性成分后得到更稳定的 idiosyncratic continuation，但本地代理没有做到。

**发现 3：IVOL 的改善是真实可见的，但主要是 gross 诊断，不是 after-cost 结论。**
IVOL x IMOM 在 validation / robustness 分别为 `0.474%` / `0.438%`，positive cell share 为 `90%` / `100%`。这说明“在 IVOL 条件下筛 IMOM”确实把横截面收益的方向改善了。但 after-cost 分别为 `-0.151%` / `-0.200%`，t-stat 也为负，因此不能升级为可交易规则。

**发现 4：直接风险调整失败，双重排序成功，说明风险变量更像条件变量而不是线性扣减项。**
Validation 中直接风险调整 IMOM 全部为负，IVOL direct-adjusted 为 `-0.194%`，IMD direct-adjusted 为 `-0.185%`。相反，IVOL 5x5 双重排序为正。这说明本地风险信息更适合解释“哪些股票的 IMOM 有条件成立”，而不是简单从 IMOM 中扣掉风险暴露。

**发现 5：交易成本是硬约束，不是报告上的小修正。**
IMOM validation 的 gross `-0.247%` 已经失败，after-cost `-0.926%` 更弱。IVOL x IMOM gross 虽然强，但 after-cost 仍负。短周期 weekly long-short 在 A 股 PIT mcap500 中 turnover 太高，任何未来需求如果继续沿用 weekly rebalance，都必须先回答成本、换手、容量和可融券约束，而不是只优化 signal rank。

**发现 6：流动性状态有解释力，但不够稳定。**
IMOM validation 中 high liquidity 为 `-0.178%`，low liquidity 为 `-1.311%`；IVOL x IMOM validation 中 high liquidity 为 `0.547%`，low liquidity 为 `-1.157%`。这支持“低流动性状态会破坏信号”的解释。但 robustness 的 low-liquidity week-observations 只有 `37`，且结果反而为正，说明该状态不能直接升为硬 gate。

**发现 7：市场状态不支持简单的 upside market 叙事。**
IMOM 在 26w upside/downside validation 都为负。IVOL x IMOM 在 robustness 中 downside 明显强于 upside。52w upside 的若干 validation cell 很高，但样本数只有 `17-40` 级别。这更像局部样本事件，而不是稳定市场状态规律。

**发现 8：money audit 需要修补。**
当前 money audit 的前 10 个 sample day 都没有 PIT 成员，导致 `money_min/p25/median/p75/max` 全部为空。收益与 gate 结果仍可读，但 Amihud 状态的审计证据不完整。后续若继续使用 liquidity_state，应生成“有有效 PIT 成员的抽样日 money 分布”作为报告必备表。

## 10. 后续研究建议

1. 不建议继续把 `market_model_sh000300_ols_v0` 当作论文 FF5 residual 的高保真代理。下一步若要认真复刻论文，应优先补齐本地 A 股 FF3/FF5 因子或行业/规模/价值/盈利/投资代理，再重跑 IMOM。
2. 可以保留 IVOL x IMOM 作为诊断线索，但下一需求应改成“低换手、非周频、容量受限的风险条件过滤诊断”，而不是继续 weekly long-short horse race。
3. 若继续做 liquidity state，应先修复 money audit，并把 `high_liquidity` 的条件效果拆成“收益提升”和“交易成本降低”两部分，否则容易把可交易性和信号有效性混在一起。
4. 不建议从本报告直接生成策略。即便 IVOL x IMOM gross 通过，after-cost 仍不通过，且 A 股融券、冲击成本和组合容量均未纳入生产级约束。

## 11. 产物索引

主要报告和汇总：

- `reports/r07_gate_decision_summary.csv`
- `reports/r07_metric_horse_race_summary.csv`
- `reports/r07_jk_summary_raw_mom.csv`
- `reports/r07_jk_summary_imom.csv`
- `reports/r07_jk_summary_risk_only.csv`
- `reports/r07_jk_summary_bivariate_risk_adjusted_imom.csv`
- `reports/r07_conditional_state_summary.csv`

关键审计文件：

- `manifests/r07_weekly_imom_run_manifest.json`
- `manifests/r07_validation_manifest.json`
- `manifests/r07_input_availability_manifest.csv`
- `manifests/r07_money_unit_audit.csv`
- `residuals/r07_residual_model_manifest.csv`
- `weekly/r07_weekly_calendar.csv`
- `weekly/r07_weekly_signal_eligibility_audit.csv`

Required caveat: `local_residual_model_not_paper_FF5_equivalent`
