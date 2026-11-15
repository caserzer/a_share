# R200 龙头扩散与延迟追赶的regime对照

## 想验证什么

在原当时行业市值前三龙头定义和固定同伴成员下，市场趋势/波动四态是否改善龙头信息的预测？分别检查regime对含龙头模型的改善、相同regime下龙头变量相对无龙头控制的增量。

输入为R145修复版本R109/R111 joined_panel，main80与strict100分别执行；历史成分和当时市值排名没有重新按未来表现定义。原三任务20/60日与原延迟追赶目标分开。追赶仍为下一月末至再下一月末的固定成员收益差；产物horizon=0仅是该日历目标的标识，不表示零日收益。

原完整母体内按日期中心化排序后才筛任务资格、状态与训练标签；原BASE控制与ALL加leader_spread两个方法，分别拟合base/state/interaction。原日期等权、Ridge alpha10、Logit/Platt C1、tol1e-10/max_iter10000、独立过去半年校准及300行18月等门槛不变。只用训练标准化，未知标签保留在预测母体；不降低每类/校准门槛。收益及追赶IC至少20个完整行业，不沿用上一轮其他机制的5行业门槛。

## 发现什么

完成540个模型、625098条预测；352条方法级资格记录跳过，不能视为352个独立折。未收敛模型0。全部保存参数与独立状态设计预测误差0，线性正规方程误差低于1.16e-15；208366条原模型对照预测全部精确复现，因此本次已拟合折没有因状态缺失改变训练样本。首次启动漏导入工具函数的失败保留，修复后运行成功。

以下为含龙头模型的状态交互减原模型，正值才改善。三任务展示20日，追赶展示其原日历目标；全部60日结果另存。

| family            | task     | metric          |   groups |   positive |       median |
|:------------------|:---------|:----------------|---------:|-----------:|-------------:|
| catchup_main80    | catchup  | ic              |        5 |          1 | -0.00883171  |
| catchup_main80    | catchup  | mse_reduction   |        5 |          0 | -0.000194326 |
| catchup_strict100 | catchup  | ic              |        5 |          0 | -0.0198736   |
| catchup_strict100 | catchup  | mse_reduction   |        5 |          0 | -0.000224652 |
| leader_main80     | onset    | brier_reduction |        4 |          2 | -8.1596e-05  |
| leader_main80     | return   | ic              |        5 |          1 | -0.0575265   |
| leader_main80     | return   | mse_reduction   |        5 |          1 | -0.000255629 |
| leader_main80     | reversal | brier_reduction |        4 |          0 | -0.00475056  |
| leader_strict100  | onset    | brier_reduction |        4 |          2 |  4.27302e-06 |
| leader_strict100  | return   | ic              |        5 |          1 | -0.0584418   |
| leader_strict100  | return   | mse_reduction   |        5 |          2 | -0.00024899  |
| leader_strict100  | reversal | brier_reduction |        4 |          1 | -0.00544741  |

追赶模型两个覆盖版本各5组MSE全部恶化；IC主覆盖只有1组改善，严格覆盖无改善。龙头收益排序同样多数变差。覆盖版本、层级和时期共享数据，这些不是独立试验次数。

再控制相同状态交互，单独比较加龙头信息与无龙头控制：

| family            | task     | metric          |   groups |   positive |       median |
|:------------------|:---------|:----------------|---------:|-----------:|-------------:|
| catchup_main80    | catchup  | ic              |        5 |          0 | -0.0150516   |
| catchup_main80    | catchup  | mse_reduction   |        5 |          1 | -3.0014e-05  |
| catchup_strict100 | catchup  | ic              |        5 |          0 | -0.0134085   |
| catchup_strict100 | catchup  | mse_reduction   |        5 |          1 | -3.32861e-05 |
| leader_main80     | onset    | brier_reduction |        4 |          3 |  0.000249561 |
| leader_main80     | return   | ic              |        5 |          2 | -0.00186211  |
| leader_main80     | return   | mse_reduction   |        5 |          1 | -3.96083e-06 |
| leader_main80     | reversal | brier_reduction |        4 |          2 | -2.70821e-06 |
| leader_strict100  | onset    | brier_reduction |        4 |          3 |  0.000113248 |
| leader_strict100  | return   | ic              |        5 |          3 |  0.00100885  |
| leader_strict100  | return   | mse_reduction   |        5 |          1 | -6.36545e-06 |
| leader_strict100  | reversal | brier_reduction |        4 |          2 | -2.40939e-05 |

两个对照必须区分：龙头信息在某个状态模型下有微小增量，并不表示加入regime后整体优于原模型。全部逐年、逐状态结果保存在paired_comparisons.csv；日期指标及总体配对结果独立重算，年度/状态分组均值尚未逐项独立重算。

## 为什么不能作更强结论

历史已被反复研究，仍为Historical-proxy，原特征、覆盖和未来成员路径缺失限制不变；部分IC日期不足，一级追赶仅1个日期达到20行业IC门槛，不据此作稳定性判断。四态交互增加维度且状态支持不均；本轮负结果不证明所有状态模型必然无效，也不支持继续无依据搜索状态窗口或惩罚参数。现有结果未证明龙头信息对未来追赶具有稳定独立领先能力，更不能作为因果或扣费配置证据。

保留原模型和负结果，不采用regime版本。概率校准、成本与退出代价、全实验不确定性仍待整体评价。全16类中10类完成首轮适配；剩余利润事件、双时钟财务、资本会计、宏观交互、早期财务、固定排序6类继续。

协议protocols/r200.json；实现src/regime_leader_r200.py；保存参数、原对照与指标验证分别为verify_regime_leader_r200.py、verify_leader_controls_r200.py、verify_regime_metrics_r200.py。全部证据及哈希在outputs/r200，未采集、部署或交易。
