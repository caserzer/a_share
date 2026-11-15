# R205 利润预期事件regime预测扩展

想验证什么：既有R144事件研究是描述性比较，本轮新增明确登记的预测对照，检验事件前价格与利润预期修正的关系是否随市场状态变化。不把原描述性研究冒称已有预测模型。

覆盖固定FY修正、排除来源未知非事件控制的敏感性版本、当前/次年配对修正。保留原事件发布日期、身份、固定FY、行业归属和结果。市场状态取signal_date严格前一交易日收盘，避免用事件当天价格反应后的状态解释事件。信号后20/60日超额与固定FY原匹配非事件超额分别建模；匹配对照是结果定义，未当训练特征提前使用。

价格控制为原pre20/pre60，扩展加入revision或current/next；原始变量仅按训练样本标准化，Ridge alpha10，日期等权，年度切分，事件日和成熟日均严格早于年初，至少300行及18个日历月。基线/状态截距/交互共享同完整特征人口和训练成熟门槛。事件日期稀疏，不输出无依据截面IC。未搜索参数或改变原非事件控制定义。

实际完成300模型、107232预测，50个合格折；资格失败完整保留。独立正规方程误差低于1.04e-14；全部保存参数、标签身份重建误差0；32742条日期MSE独立核验通过。原描述性研究未改变，本轮是新增探索，不是独立未使用历史验证。

主20日对照正值才表示MSE改善：

| family           | level   | target_type   | second               |   dates |   mse_improvement |
|:-----------------|:--------|:--------------|:---------------------|--------:|------------------:|
| fixed_fy         | L2      | matched_post  | with_revision/base   |     370 |      -0.000254221 |
| fixed_fy         | L2      | matched_post  | controls/interaction |     370 |      -0.000176845 |
| fixed_fy         | L2      | post          | with_revision/base   |     371 |      -0.000299963 |
| fixed_fy         | L2      | post          | controls/interaction |     371 |      -0.000219016 |
| fixed_fy         | L3      | matched_post  | with_revision/base   |     350 |      -0.000931167 |
| fixed_fy         | L3      | matched_post  | controls/interaction |     350 |      -0.000301123 |
| fixed_fy         | L3      | post          | with_revision/base   |     362 |      -0.000586367 |
| fixed_fy         | L3      | post          | controls/interaction |     362 |      -6.26218e-05 |
| paired_fy        | L2      | post          | with_revision/base   |     325 |      -0.000381544 |
| paired_fy        | L2      | post          | controls/interaction |     325 |      -0.000269926 |
| paired_fy        | L3      | post          | with_revision/base   |     319 |      -0.000716222 |
| paired_fy        | L3      | post          | controls/interaction |     319 |      -9.04492e-05 |
| unknown_controls | L2      | matched_post  | with_revision/base   |     370 |      -0.000254247 |
| unknown_controls | L2      | matched_post  | controls/interaction |     370 |      -0.000176851 |
| unknown_controls | L2      | post          | with_revision/base   |     371 |      -0.000299963 |
| unknown_controls | L2      | post          | controls/interaction |     371 |      -0.000219016 |
| unknown_controls | L3      | matched_post  | with_revision/base   |     350 |      -0.000931213 |
| unknown_controls | L3      | matched_post  | controls/interaction |     350 |      -0.000301143 |
| unknown_controls | L3      | post          | with_revision/base   |     362 |      -0.000586367 |
| unknown_controls | L3      | post          | controls/interaction |     362 |      -6.26218e-05 |

十个状态交互相对base的比较全部恶化，控制同样交互后预期修正的增量也全部为负。原与未知控制敏感性版本部分结果一致，数据重叠，不能计为独立验证。日期约319—371个，但事件结果20日重叠，不能把事件日当独立样本；后续总体不确定性需要时间依赖处理。

预期修正没有在本固定模型中展示状态条件下稳定领先增量；这不是因果反证。选取的缓存报告、真实无消息控制未知、历史代理价格及重复使用历史的边界保留。没有概率、配置成本、股票执行或退出代价结论，不采用、不继续阈值搜索。

协议protocols/r205.json，代码src/regime_events_r205.py及verify_regime_events_r205.py，模型、资格、样本、状态日期、全期限结果与哈希在outputs/r205。
