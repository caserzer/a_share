# 工程特征残差分数与预测诊断

每项特征的分数贡献使用原季度TrainTransform与Ridge系数，不能把不同季度的标准化系数直接当作相同原始单位的效应。各项先除以当日完整分数标准差、行业去均值，再用同一13风格投影取残差。

逐项残差加总必须精确回到完整残差；组分配定义为组残差与总残差的内积，占总残差平方和的比例。原冻结特征组保持不变。

| group               |   signed_allocation |   own_energy |   signed_share |
|:--------------------|--------------------:|-------------:|---------------:|
| market_common       |             -0.0000 |       0.0000 |        -0.0000 |
| range_position      |          11232.6830 |   15758.4796 |        64.9752 |
| returns_trend       |           3818.6295 |    4497.8453 |        22.0888 |
| volatility_drawdown |           1750.3934 |    5751.2372 |        10.1251 |
| volume_liquidity    |            485.9385 |     511.5061 |         2.8109 |

own_energy是该组自身平方和，组间有相关性，因此各组own_energy不应加总当成整体平方和。signed_share才是本合同下可加总的带符号分配。

## 区间位置组三项

| feature   |   signed_share |   min_coefficient |   max_coefficient |
|:----------|---------------:|------------------:|------------------:|
| pos20     |         8.9452 |            0.0105 |            0.0346 |
| pos5      |        -0.7534 |           -0.0116 |           -0.0007 |
| pos60     |        56.7834 |            0.1118 |            0.1514 |

pos5、pos20、pos60分别采用5/20/60日最低low和最高high计算区间位置。当前模型系数中pos60、pos20为正，pos5为负，但这只解释分数方向，未证明单项净收益。特征级细分在看到组结果后补充，明确属于事后记账，不进行78项未来收益筛选。

示意而非真实回测：两只股票同样从90涨到100，首尾涨幅相同；若一只期间最低80、最高120，区间位置为0.5；另一只最低90、最高100，区间位置为1。简单累计收益无法区分这样的路径。

## 未来收益辅助检查

| score                        | metric      |   n |     mean |   ci_low |   ci_high |
|:-----------------------------|:------------|----:|---------:|---------:|----------:|
| E1                           | rank_ic     | 171 |   0.0471 |   0.0193 |    0.0759 |
| E1                           | industry_ic | 171 |   0.0443 |   0.0248 |    0.0629 |
| EXPLAINED13                  | rank_ic     | 171 |   0.0339 |   0.0115 |    0.0561 |
| EXPLAINED13                  | industry_ic | 171 |   0.0461 |   0.0191 |    0.0736 |
| FIXED78                      | rank_ic     | 171 |   0.0306 |   0.0072 |    0.0541 |
| FIXED78                      | industry_ic | 171 |   0.0394 |   0.0201 |    0.0579 |
| RESIDUAL13                   | rank_ic     | 171 |   0.0137 |   0.0034 |    0.0236 |
| RESIDUAL13                   | industry_ic | 171 |   0.0226 |   0.0093 |    0.0352 |
| residual_market_common       | rank_ic     |   0 | nan      | nan      |  nan      |
| residual_market_common       | industry_ic |   0 | nan      | nan      |  nan      |
| residual_range_position      | rank_ic     | 171 |   0.0046 |  -0.0119 |    0.0196 |
| residual_range_position      | industry_ic | 171 |   0.0104 |  -0.0084 |    0.0278 |
| residual_returns_trend       | rank_ic     | 171 |   0.0024 |  -0.0120 |    0.0159 |
| residual_returns_trend       | industry_ic | 171 |   0.0045 |  -0.0115 |    0.0208 |
| residual_volatility_drawdown | rank_ic     | 171 |   0.0146 |  -0.0017 |    0.0323 |
| residual_volatility_drawdown | industry_ic | 171 |   0.0225 |   0.0042 |    0.0417 |
| residual_volume_liquidity    | rank_ic     | 171 |   0.0033 |  -0.0070 |    0.0128 |
| residual_volume_liquidity    | industry_ic | 171 |   0.0125 |   0.0002 |    0.0249 |

rank_ic为分数与原始H10未来收益的Spearman；industry_ic为先逐行业计算相关再按有效股票数加权。不是严格条件因果统计。时间块13周、5000次，普通95%区间未做本轮辅助族的多重校正；不得从其中最好的组升级主结论。

市场共同项在行业去均值后近乎零，不能形成股票排序，其相关记未知，不填零。其他组单独正点估计也不能替代成本后组合验证。

## 为什么与早期 A1 不同

本轮采用缩小C样本、2021-10-08后共同区间、标准化并行业去均值的教师分数和对应残差；早期A1使用不同样本、区间及投影合同。因此本轮残差IC的正区间不能重写早期主裁决，也不能称为又一次独立确认。

13风格矩阵当前信号均满秩；条件数中位约40.10、最大约76.81。仍有共线性，尤其市值字段；本轮用映射后的分数变化作比较，不能宣称已消除所有数值敏感性。

[逐特征完整分配](../../outputs/diagnostics/e1_mapping_drift_20261117/feature_residual_summary.csv) · [每期特征贡献](../../outputs/diagnostics/e1_mapping_drift_20261117/feature_residual_allocation.csv) · [逐期RankIC](../../outputs/diagnostics/e1_mapping_drift_20261117/rank_ic.csv) · [投影条件数](../../outputs/diagnostics/e1_mapping_drift_20261117/projection_conditioning.csv)。

当前结构平均可解释约33.8%的行业去均值分数平方量；其分母与此前含行业均值的总分数R²不同，不能直接对比成“解释率下降”。原模型没有重训，未生成新组合策略。
