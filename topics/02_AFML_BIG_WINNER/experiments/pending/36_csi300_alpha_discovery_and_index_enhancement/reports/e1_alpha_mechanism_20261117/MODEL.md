# 原 E1 选股解释与账本桥接

想验证什么：E1是否偏好强势回撤状态，该状态是否解释原账户超额。

怎么比较：24个季度原模型与变换器逐行复放；每项beta乘变换后特征，78项固定归入5组。最大分数误差2.11×10⁻¹⁵。季度系数、训练均值及标准差完整保存，没有重训。市场共同项在同一截面不改变股票相对排序。

发现什么：有效样本内强势回撤占池子约24%，占原Q5已覆盖部分约28%；同时强势未回撤也有富集，因此不能把模型简化为单一回撤买入。

| state                |   pool_share |   q5_share |
|:---------------------|-------------:|-----------:|
| 中期强势且短期未回撤 |      24.6544 |    29.5605 |
| 中期强势且短期回撤   |      23.9590 |    27.9749 |
| 中期弱势且短期未回撤 |      26.7549 |    19.7928 |
| 中期弱势且短期回撤   |      24.6317 |    22.6719 |

主区间Q5与未入选股票的分数组均值差：

| index               |   Q5_minus_nonQ5_mean_score |
|:--------------------|----------------------------:|
| returns_trend       |                      0.0687 |
| volatility_drawdown |                      0.0113 |
| range_position      |                      0.0724 |
| volume_liquidity    |                     -0.0013 |
| market_common       |                      0.0000 |

区间位置和收益趋势组分数差较大；这是选股分数构成，不是收益贡献。特征共线性意味着不能据此宣布哪组创造Alpha。季度系数变化、分数组相关性和完整映射见链接。

为什么不能下结论：原股票资本仅约三分之二可归入本轮状态，未知部分仍贡献大量收益；原账本分组不能作为因果分解。每个交易日使用严格早于当天的最新周信号，包含换入、换出及持仓漂移。费用和现金独立归因，各组逐日相加回到原账本。

| 状态                     |   wealth_contribution |
|:-------------------------|----------------------:|
| 状态未知或不属于本轮样本 |               19.3899 |
| 现金机会收益             |                0.9781 |
| 交易费用                 |              -10.0074 |
| 中期强势且短期未回撤     |               -0.1014 |
| 中期强势且短期回撤       |                8.1218 |
| 中期弱势且短期未回撤     |                7.2953 |
| 中期弱势且短期回撤       |               16.9549 |

固定案例为最高5个、最低5个、其余固定随机10个。代码为权威键，名称是参考，不代表历史时点名称认证。

| case     | instrument   | name_reference   | signal_date   | state              |   wealth_contribution |        u |        v |   raw_q5 |
|:---------|:-------------|:-----------------|:--------------|:-------------------|----------------------:|---------:|---------:|---------:|
| top5     | SZ300442     | 润泽科技         | 2024-12-06    | UNKNOWN            |                0.6801 | nan      | nan      | nan      |
| top5     | SH601216     | 君正集团         | 2021-01-22    | weak_pullback      |                0.5470 |   0.0500 |   0.7500 |   0.0000 |
| top5     | SZ300142     | 沃森生物         | 2022-03-11    | weak_no_pullback   |                0.5440 |   0.2639 |   0.4306 |   1.0000 |
| top5     | SH600703     | 三安光电         | 2021-07-16    | strong_pullback    |                0.5416 |   0.8333 |   0.7222 |   1.0000 |
| top5     | SZ002568     | 百润股份         | 2022-09-16    | weak_pullback      |                0.5099 |   0.1071 |   0.8929 |   1.0000 |
| bottom5  | SZ002773     | 康弘药业         | 2021-04-09    | weak_no_pullback   |               -0.5392 |   0.0167 |   0.1833 |   1.0000 |
| bottom5  | SH600009     | 上海机场         | 2021-01-29    | strong_no_pullback |               -0.4911 |   0.6786 |   0.1071 |   0.0000 |
| bottom5  | SZ002241     | 歌尔股份         | 2022-11-04    | weak_no_pullback   |               -0.4592 |   0.1400 |   0.4200 |   1.0000 |
| bottom5  | SH688256     | 寒武纪           | 2025-01-10    | UNKNOWN            |               -0.3895 | nan      | nan      | nan      |
| bottom5  | SZ300763     | 锦浪科技         | 2023-10-20    | weak_no_pullback   |               -0.3878 |   0.3167 |   0.0167 |   0.0000 |
| random10 | SZ300529     | 健帆生物         | 2021-09-30    | weak_no_pullback   |               -0.0237 |   0.0139 |   0.0694 |   0.0000 |
| random10 | SH600741     | 华域汽车         | 2022-04-29    | weak_no_pullback   |                0.0634 |   0.3182 |   0.4091 |   0.0000 |
| random10 | SZ300999     | 金龙鱼           | 2022-05-06    | UNKNOWN            |                0.0124 | nan      | nan      | nan      |
| random10 | SH603259     | 药明康德         | 2022-03-04    | weak_pullback      |                0.0265 |   0.0972 |   0.5694 |   1.0000 |
| random10 | SH600938     | 中国海油         | 2024-08-02    | UNKNOWN            |               -0.0280 | nan      | nan      | nan      |
| random10 | SZ000768     | 中航西飞         | 2021-04-02    | UNKNOWN            |                0.0333 | nan      | nan      | nan      |
| random10 | SH601169     | 北京银行         | 2024-05-31    | strong_pullback    |               -0.0150 |   0.6905 |   0.5476 |   1.0000 |
| random10 | SH600754     | 锦江酒店         | 2023-12-08    | UNKNOWN            |               -0.0047 | nan      | nan      | nan      |
| random10 | SH688271     | 联影医疗         | 2024-08-23    | UNKNOWN            |               -0.0107 | nan      | nan      | nan      |
| random10 | SH600803     | 新奥股份         | 2024-06-28    | strong_pullback    |                0.0429 |   0.5769 |   0.9615 |   0.0000 |

[78项映射](../../outputs/diagnostics/e1_alpha_mechanism_20261117/feature_groups.csv) · [季度系数](../../outputs/diagnostics/e1_alpha_mechanism_20261117/coefficients.csv) · [逐季复放](../../outputs/diagnostics/e1_alpha_mechanism_20261117/model_replay.csv) · [分数组均值](../../outputs/diagnostics/e1_alpha_mechanism_20261117/score_group_means.csv) · [分数组相关](../../outputs/diagnostics/e1_alpha_mechanism_20261117/score_group_correlations.csv) · [逐月状态贡献](../../outputs/diagnostics/e1_alpha_mechanism_20261117/state_month_contributions.csv) · [实际持仓资本覆盖](../../outputs/diagnostics/e1_alpha_mechanism_20261117/original_capital_coverage.csv) · [全部案例事件](../../outputs/diagnostics/e1_alpha_mechanism_20261117/all_case_events.csv)。

逐股完整特征和标签表保存在private/e1_alpha_mechanism_20261117/stock_signal_detail.parquet，原始数据依仓库规则保留本地。
