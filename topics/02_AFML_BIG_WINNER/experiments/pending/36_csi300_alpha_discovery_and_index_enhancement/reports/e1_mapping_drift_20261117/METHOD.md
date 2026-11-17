# 映射变化的模型与数据分解

本轮只解释此前复制失败，不搜索收益参数。先冻结两种时间跨度、两个样本口径和分解公式，再计算结构，封存结构后才接入H10标签。

每个数据截面将13风格作总体标准化并行业去均值，得到X。原Ridge分数作总体标准化并行业去均值，得到y。令gamma=pinv(X)y，rcond=1e-12。两个日期可能有不同股票数量，但gamma始终为相同13维风格坐标。

用M0/M1表示旧/新原Ridge整套模型，D0/D1表示旧/新数据。计算gamma00、gamma10、gamma01、gamma11：
- 模型分配=0.5×[(gamma10−gamma00)+(gamma11−gamma01)]。
- 数据分配=0.5×[(gamma01−gamma00)+(gamma11−gamma10)]。
- 二者相加精确等于gamma11−gamma00。
- 使用新数据的X1将三者映射到股票分数空间；不是用易受共线性影响的系数欧氏距离直接作经济归因。

对每个日期用平均股票平方变化定义能量。某项带符号分配为该项分数变化与总变化的内积，再除以总变化平方和；汇总先加各日期分子分母再求比。分配可能负值或超过100%，并非互相独立的正方差，也不是利润份额。

| clock    | scope   | sample            |   pairs |   change_energy_sum |   model_share |   data_share |
|:---------|:--------|:------------------|--------:|--------------------:|--------------:|-------------:|
| adjacent | common  | all               |     173 |             25.3041 |        0.6460 |      99.3540 |
| adjacent | common  | model_change_only |      14 |              2.9148 |        5.6078 |      94.3922 |
| adjacent | native  | all               |     173 |             25.6649 |        0.6469 |      99.3531 |
| adjacent | native  | model_change_only |      14 |              2.8878 |        5.7496 |      94.2504 |
| anchor   | common  | all               |     172 |            111.0562 |        6.9579 |      93.0421 |
| anchor   | common  | model_change_only |     160 |            107.8532 |        7.1645 |      92.8355 |
| anchor   | native  | all               |     172 |             60.6622 |        8.4906 |      91.5094 |
| anchor   | native  | model_change_only |     160 |             57.5154 |        8.9551 |      91.0449 |

相邻周的同季度模型完全一致，模型分配必须为零；此外单列模型确实更换的边界配对。固定首日2021-10-08的比较跨越多个季度，减少“多数周不更新”的机械影响。common口径只用两期共有股票，但仍保留各期特征、行业和标准化；不是固定整个市场环境。

**新模型放到旧数据上属于事后交叉诊断，可能使用旧日期之后的信息，不能生成可交易历史预测。** 唯一辅助未来预测对照FIXED78使用2021Q4已训练模型向后应用，未读取未来模型。

模型项包含系数、训练均值/标准差、中位数填补变化；数据项也包含标准化和行业分类变化。本轮不进一步把它们分别命名为因果机制。

[四格投影系数](../../outputs/diagnostics/e1_mapping_drift_20261117/mapping_cells.csv) · [逐配对分解](../../outputs/diagnostics/e1_mapping_drift_20261117/mapping_decomposition.csv) · [原分数复放](../../outputs/diagnostics/e1_mapping_drift_20261117/replay.csv) · [输入代码冻结](../../outputs/diagnostics/e1_mapping_drift_20261117/freeze.json) · [无未来收益的结构封存](../../outputs/diagnostics/e1_mapping_drift_20261117/structure_complete.json) · [分析完成](../../outputs/diagnostics/e1_mapping_drift_20261117/analysis_complete.json)。
