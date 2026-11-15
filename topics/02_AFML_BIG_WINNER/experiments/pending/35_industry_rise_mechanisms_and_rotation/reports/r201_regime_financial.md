# R201 双时钟财务模型regime对照

## 想验证什么

财务利润变化模型能否在同一市场状态定义下改善？分别保留notice公告代理时钟、update公告与更新取较晚值代理时钟，以及两时钟共同样本。update不是档案首次获取时钟；两种都缺版本历史，不能称严格PIT。

读取R146修复的R121 joined_panel及R123 common_panel；原main80与strict100不合并。单时钟控制/加财务两方法、共同样本控制/公告财务/更新财务三方法均运行base/state/interaction。使用R195四态，原完整母体内中心化排序，训练标准化、日期等权、Ridge alpha10、300行18月与成熟标签边界不变。原R121三任务资格全检查；共同样本沿用R123收益任务。IC至少20行业，未因样本小降低标准。

## 实际执行

980个原计划唯一折全部保留，包括没有测试样本；10个折可拟合（7个单时钟、3个共同样本），970个折未达资格。完成69次拟合、6297条预测。只有SW2021三级main80收益任务可拟合；严格覆盖、启动和反转没有可训练结果，不能填补为概率或零效果。参数记录按方法重复，不能用其行数冒充唯一折数。

2099条base对照与原修复模型精确复现。全部6297条预测独立构造状态与交互后参数推断误差0；线性正规方程误差低于1.23e-15。582条日期指标及144项总体配对比较独立重算通过，年度/状态子组均值尚未全部独立复算。

## 发现什么

主20日状态交互相对原方法的MSE改善如下，负值表示变差：

| family        | first                      | second              |   dates |        delta |
|:--------------|:---------------------------|:--------------------|--------:|-------------:|
| common_main80 | controls/interaction       | controls/base       |      15 | -0.000496034 |
| common_main80 | notice_model/interaction   | notice_model/base   |      15 | -0.000536619 |
| common_main80 | update_model/interaction   | update_model/base   |      15 | -0.000472808 |
| notice_main80 | controls/interaction       | controls/base       |      20 | -0.000564669 |
| notice_main80 | with_financial/interaction | with_financial/base |      20 | -0.000581196 |
| update_main80 | controls/interaction       | controls/base       |      15 | -0.000496034 |
| update_main80 | with_financial/interaction | with_financial/base |      15 | -0.000472808 |

七个方法/时钟对照全部恶化。各组重叠，不能当作独立统计试验。不同单时钟母体不能直接比较效果；跨时钟仅查看common_main80。

保持相同状态交互后的财务/时钟增量：

| family        | first                      | second                   |   dates |        delta |
|:--------------|:---------------------------|:-------------------------|--------:|-------------:|
| common_main80 | notice_model/interaction   | controls/interaction     |      15 | -5.35269e-05 |
| common_main80 | update_model/interaction   | controls/interaction     |      15 |  4.18716e-05 |
| common_main80 | update_model/interaction   | notice_model/interaction |      15 |  9.53985e-05 |
| notice_main80 | with_financial/interaction | controls/interaction     |      20 | -1.18356e-05 |
| update_main80 | with_financial/interaction | controls/interaction     |      15 |  4.18716e-05 |

全部IC日期均不足原20行业门槛，报告为未知，不解读为零增量。公告时钟20个可评价月，更新与共同样本15个月，仍不足原稳定性条件。60日期限、状态截距版及年度/状态结果均保留在paired_comparisons.csv，没有只保留负结果或局部正结果。

## 判断与边界

固定状态交互没有修复本财务模型的预测误差；尚不能判定财务变化有跨状态稳定领先增量。历史时钟代理、部分覆盖选择和重复使用历史的限制依旧存在。未检验扣费配置或退出价值，不将误差比较当作收益承诺。本轮不采用、不换状态或惩罚参数寻找成功。

保留所有失败折与原模型。16类中11类完成首轮拟合/资格适配；剩余利润事件、资本会计、宏观交互、早期财务、固定排序5类仍需处理，已完成分支完整评价也未结束。

证据入口：protocols/r201.json；src/regime_financial_r201.py、verify_regime_financial_r201.py、verify_financial_controls_r201.py、verify_regime_metrics_r201.py；outputs/r201内含模型、预测、原对照、全部门槛、比较与哈希。没有新增采集、生产部署或交易。
