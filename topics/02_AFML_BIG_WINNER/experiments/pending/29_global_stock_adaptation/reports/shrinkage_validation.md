# 收缩、控制与过拟合

固定正控制、零附加效应控制和身份置乱均通过预定管道检查。通过控制只证明方法能在构造世界中工作、未制造指定容忍度外的假优势，不证明真实A股存在相同机制。

## 正负合成世界

120家公司、180个月、最后60月评价，固定种子；以6月共享事件块制造重叠，部分公司仅在评价前12月进入。它是二元事件控制世界，不是完整价格路径/公司行动模拟。

| world | comparison | estimate | low95 | high95 |
| --- | --- | --- | --- | --- |
| positive | GPI-G | -0.01451813 | -0.017918716 | -0.010764584 |
| positive | GI-G | -0.0070510795 | -0.010303998 | -0.0035239746 |
| positive | GP-G | -0.010848307 | -0.013430084 | -0.008252131 |
| positive | GPI-GP | -0.0036698228 | -0.0054989592 | -0.001576863 |
| zero | GPI-G | 0.0014063808 | 0.00080801809 | 0.0019366061 |
| zero | GI-G | 0.00039264353 | 1.7310751e-06 | 0.00090845811 |
| zero | GP-G | 0.0010500888 | 0.00038230587 | 0.0017061796 |
| zero | GPI-GP | 0.00035629198 | -1.7601072e-05 | 0.00084971385 |


正世界中，适配公司偏移与真实个体效应相关0.5515；稀少历史公司的同行oracle MSE改善0.011898。零世界反而有GPI Brier损失约0.001406，且仍有1,676行触发个股适配：收缩没有消灭噪声拟合。不能只展示正控制而忽略这种成本。

零事件公司在两个世界分别有698和833条评价行，个股修正均回退0，正式概率保持内部值。首末时间段持久性、至少两个不重叠事件/非事件窗、21成熟月及训练内tau共同控制适配；这些窗口并不等于经济上独立事件。

## 无修正、强收缩、训练内收缩、弱先验与严格无收缩

原注册`L_unshrunk`实际上是Jeffreys(.5,.5)弱平滑，不能冒称严格无收缩。另在真实适配/评分前登记`L_MLE`补足目标要求：同一成熟历史的事件数/月份数，无先验，仅数值clip；无历史回退G。它是诊断，不是新增正式候选。

| population | model | brier | extreme_probability_fraction | oracle_MSE |
| --- | --- | --- | --- | --- |
| D0 | G | 0.13809523 | 0 | NA |
| D0 | GI | 0.13803591 | 0 | NA |
| D0 | GP | 0.13832719 | 0 | NA |
| D0 | GPI | 0.13827244 | 0 | NA |
| D0 | GPI_strong | 0.13826798 | 0 | NA |
| D0 | L | 0.13855308 | 0 | NA |
| D0 | L_MLE | 0.15587978 | 0.26505059 | NA |
| D0 | L_unshrunk | 0.14694847 | 0 | NA |
| cohort40 | G | 0.12257091 | 0 | NA |
| cohort40 | GI | 0.12195574 | 0 | NA |
| cohort40 | GP | 0.1217042 | 0 | NA |
| cohort40 | GPI | 0.12113693 | 0 | NA |
| cohort40 | GPI_strong | 0.12121358 | 0 | NA |
| cohort40 | L | 0.11478572 | 0 | NA |
| cohort40 | L_MLE | 0.11475191 | 0.27532618 | NA |
| cohort40 | L_unshrunk | 0.11037781 | 0 | NA |
| synthetic_positive | G | 0.20764547 | 0 | 0.030296827 |
| synthetic_positive | GI | 0.20059439 | 0 | 0.024130196 |
| synthetic_positive | GP | 0.19679716 | 0 | 0.021349703 |
| synthetic_positive | GPI | 0.19312734 | 0 | 0.018092628 |
| synthetic_positive | GPI_strong | 0.19561443 | 0 | 0.020205219 |
| synthetic_positive | L | 0.20120078 | 0 | 0.026596119 |
| synthetic_positive | L_MLE | 0.21113774 | 0.11111111 | 0.037998995 |
| synthetic_positive | L_unshrunk | 0.20469791 | 0 | 0.030935504 |
| synthetic_zero | G | 0.17267768 | 0 | 1.8745718e-34 |
| synthetic_zero | GI | 0.17307032 | 0 | 0.00015196754 |
| synthetic_zero | GP | 0.17372777 | 0 | 0.00024187071 |
| synthetic_zero | GPI | 0.17408406 | 0 | 0.00036888435 |
| synthetic_zero | GPI_strong | 0.17371668 | 0 | 0.00025562918 |
| synthetic_zero | L | 0.19123577 | 0 | 0.016926414 |
| synthetic_zero | L_MLE | 0.20678132 | 0.12138889 | 0.034582057 |
| synthetic_zero | L_unshrunk | 0.2017894 | 0 | 0.02769202 |


无收缩在D0约26.5%的月份等权预测进入<1%或>99%的极端区间；GPI正式预测未出现这种极端。D0中部分池化比无收缩局部模型明显稳健，但40公司队列中L及弱先验的点估计反而较好，不能说分层模型普遍胜出。

| population | candidate | baseline | estimate | low95 | high95 |
| --- | --- | --- | --- | --- | --- |
| D0 | GPI | L_MLE | -0.017607337 | -0.027752029 | -0.008562961 |
| D0 | L | L_MLE | -0.017326696 | -0.02517449 | -0.010257736 |
| D0 | L_unshrunk | L_MLE | -0.0089313033 | -0.020777576 | 0.0021537731 |
| D0 | L_MLE | G | 0.017784551 | 0.0083552284 | 0.028566857 |
| cohort40 | GPI | L_MLE | 0.0063850182 | -0.0048540596 | 0.017947543 |
| cohort40 | L | L_MLE | 3.3805482e-05 | -0.0072769802 | 0.006213807 |
| cohort40 | L_unshrunk | L_MLE | -0.0043741054 | -0.012479403 | 0.0026994101 |
| cohort40 | L_MLE | G | -0.0078190022 | -0.020418041 | 0.0041765589 |


训练内收缩与固定强收缩的D0差异：+0.00000446，95%区间[-0.00002483, +0.00003227]。不据此重新选择tau或改候选。

## 身份置乱

同日期×行业×市值/波动中位数组内一次固定置乱，特征、标签及G概率整行保留；实际改变身份69.23%，小组不能充分置乱，故是部分身份持续性破坏。

| comparison | estimate | low95 | high95 |
| --- | --- | --- | --- |
| GI-G | 3.3468829e-05 | -8.6093649e-06 | 9.0038999e-05 |
| GPI-GP | 3.5961423e-05 | -5.0359283e-06 | 9.0328377e-05 |
| GPI-G | 4.2899981e-05 | -0.00022025529 | 0.00038084453 |


没有稳定的虚假个股优势。但这不能证明真实公司效应为零，保留的行业/市场结构仍可有信息。

## 不确定性与真实回退

| world | rows | adapted | approximate_latent_individual_coverage | conditional_interval_note | zero_events | zero_event_individual_nonzero |
| --- | --- | --- | --- | --- | --- | --- |
| positive | 7200 | 2704 | 0.93565089 | model approximation; random-effects hyperparameter/global/peer uncertainty omitted | 698 | 0 |
| zero | 7200 | 1676 | 1 | model approximation; random-effects hyperparameter/global/peer uncertainty omitted | 833 | 0 |


上述潜在效应区间覆盖只是人工世界下、触发适配行的近似检查；正世界约93.6%，低于名义95%，零世界100%也不能认证真实覆盖。实际输出的个股区间条件于G、同行和tau；它不是包含数据版本、市场非平稳和超参数误差的完整概率区间。回退标为[0,1]，明确表示缺乏可用个股置信范围。

| reason | predictions | known | mean_history_months | mean_effective_months |
| --- | --- | --- | --- | --- |
| adapted | 2663 | 2284 | 44.77469 | 6.3963843 |
| few_independent_event_windows | 7805 | 7066 | 35.602178 | 5.0860254 |
| few_non_event_windows | 6 | 6 | 24 | 3.4285714 |
| no_mature_history | 2798 | 2643 | 0 | 0 |
| short_history | 9217 | 8746 | 10.524466 | 1.5034951 |
| unstable_or_unavailable_temporal_direction | 5528 | 4907 | 39.953509 | 5.7076442 |
| zero_persistent_variance_in_training | 1579 | 1578 | 40.621279 | 5.8030399 |
