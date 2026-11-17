# 共同反弹对照与交易时间路径

想验证什么：收益是否来自普遍反弹、共同风险或日期与名单刷新。

怎么比较：市场状态仅用信号前20日总收益和波动，波动阈值取此前252日中位数；未知历史保持UNKNOWN。匹配为同行业13风格每项0.5标准差以内，允许控制股重复，不能保证因果可比。

发现什么：严格股票匹配预算覆盖约2.1%，安慰剂通过51/14000次。匹配和随机分支均为PARTIAL_IDENTIFICATION，不能从其很小的成功子样本判定M2成立或排除M2。

固定H10的日期比较，均为新规则账户名单，不是原E1名单。单位为pp，数量为各差值已知配对数：

| strategy   |   immediate_minus_delayed_count |   immediate_minus_delayed_mean |   fresh_minus_delayed_count |   fresh_minus_delayed_mean |
|:-----------|--------------------------------:|-------------------------------:|----------------------------:|---------------------------:|
| B          |                              49 |                        -0.1688 |                          48 |                    -0.1394 |
| E1         |                              46 |                        -0.3914 |                          46 |                    -0.1311 |
| J          |                              50 |                        -0.1680 |                          49 |                    -0.1278 |

立即与延迟差异同时包含信号老化和日期；同日新名单与旧名单差异定位刷新效应。这里仅作描述，不从负点估计宣布“第二周更优”，不选择新相位。

月初同一H20路径、J减B的阶段贡献，单位pp；路径包括一次入场费及末段一次退出费，各段加总已核对：

| segment   |   n |   J_minus_B |
|:----------|----:|------------:|
| first5    |  49 |     -0.0414 |
| next5     |  49 |      0.0396 |
| last10    |  49 |      0.0031 |

目标匹配并不等于成交后风险中性。下表是每日持仓按最近调仓信号的冻结风格衡量，未知旧仓权重单列；不是每日更新风险模型：

| strategy   |   mean_gap |   maximum_gap |   unknown_weight |   within_bound_fraction |
|:-----------|-----------:|--------------:|-----------------:|------------------------:|
| B          |     0.0294 |        0.1316 |           0.0460 |                 98.2018 |
| E1         |     0.2575 |        0.3603 |           0.0458 |                 41.9580 |
| J          |     0.1411 |        0.2970 |           0.0455 |                 95.7043 |

为何不能下结论：主净增量未确认、随机和逐股对照覆盖不足；时间路径只能描述当前规则，并未建立原E1月初优势的完整解释。保持原相位，不据此调参。

[匹配失败及结果](../../outputs/diagnostics/e1_alpha_mechanism_20261117/matched_outcomes.csv) · [匹配预算覆盖](../../outputs/diagnostics/e1_alpha_mechanism_20261117/matched_budget_coverage.csv) · [随机通过记录](../../outputs/diagnostics/e1_alpha_mechanism_20261117/placebo_coverage.csv) · [各随机副本比较](../../outputs/diagnostics/e1_alpha_mechanism_20261117/placebo_comparisons.csv) · [预先市场状态](../../outputs/diagnostics/e1_alpha_mechanism_20261117/market_regimes.csv) · [状态分层结果](../../outputs/diagnostics/e1_alpha_mechanism_20261117/regime_events.csv) · [完整日期配对](../../outputs/diagnostics/e1_alpha_mechanism_20261117/timing_comparisons.csv) · [阶段路径](../../outputs/diagnostics/e1_alpha_mechanism_20261117/marginal_paths.csv) · [每日实际风险](../../outputs/diagnostics/e1_alpha_mechanism_20261117/actual_daily_risk.csv)。
