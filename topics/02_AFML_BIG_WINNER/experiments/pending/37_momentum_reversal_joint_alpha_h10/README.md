# EP37 动量与反转联合 Alpha

[收益秩 MSE 的 ICIR 与沪深 300 超额](notes/RANK_MSE_78_BENCHMARK.md)给出最高十分组相对全收益指数及价格指数的同期扣费后表现。

EP37 寻找动量与反转联合建模产生的增量预测信息，并检验它能否在固定持有 10 个交易日后兑现为成本后收益。首轮采用独立定义的11项联合特征；随后按用户要求，新增保留EP36全部78项原特征、以RankIC为目标的训练分支。

最新分支已完成：**[原78特征与RankIC训练报告](extensions/original78_rankic_20261118/outputs/REPORT.md)** · [图表HTML](extensions/original78_rankic_20261118/outputs/REPORT.html) · [模型与复核入口](extensions/original78_rankic_20261118/README.md)。恢复每周训练样本，完成72个最终季度模型。主区间RankIC目标模型RankIC为0.0552、D10净年化−1.69%；原收益MSE为0.0406、+0.11%；收益秩MSE对照为0.0692、+2.81%。均使用共同H10口径，收益为停牌估值代理。排序恢复不等于独立Alpha获证，三项主检验均未通过Holm 5%阈值。原78特征和原E1预测逐项复现，7项测试、72份模型重放、18条账本重建通过。

首轮状态：`RESEARCH_COMPLETE_WITH_LIMITATIONS`，2026-11-18。用户回复“执行”后，已完成数据重建、216个最终季度模型、完整十分组、270条账户分支和六项主检验。**首轮未确认稳定独立Alpha。**以下保留首轮报告与结论，冻结合同和既有结果未被追加分支覆盖。

- [完整中文实验报告](outputs/publishable/reports/REPORT.md) · [含图表HTML](outputs/publishable/reports/REPORT.html)
- [排序与十分组](outputs/publishable/reports/H1_RANKING.md) · [H10账户与净收益](outputs/publishable/reports/H2_ECONOMICS.md)
- [条件信息与覆盖](outputs/publishable/reports/H3_INDEPENDENCE.md) · [训练与稳健性](outputs/publishable/reports/TRAINING.md)
- [执行记录及报告生成修复](notes/EXECUTION.md) · [最终核验](outputs/manifests/final_validation.json)

主区间2021-01-11至2025-03-03开盘，100个H10窗口：联合秩目标模型J_R的RankIC为0.0072，加法模型A_R为0.0022，配对差区间跨零；两者D10停牌估值代理账户净年化分别−11.84%、−11.85%。六项主检验Holm p均为1，条件信息仅35个有效窗口。十分组没有形成清晰单调的收益梯度。

完整日历延伸至2026-10-12，共139个H10窗口；部分连续账户在此前因未知价格或公司行动端点停止，未将不同终点CAGR直接横排。严格报价分支全部受阻；完整账户结果使用明确标记的停牌估值代理。Historical-proxy、未完成真实权益认证和真实前瞻未启动边界保留。

20项单元测试、4171项实现核验通过，216个模型数值重放、70条主成本代理账户的实际成交与持仓账本重建通过；605个冻结输入哈希保持不变。条件消融未触发，没有按结果追加参数搜索。

- [完整研究合同](GOAL.md)
- [参数与候选登记](config.yaml)
- [EP36 阅读记录与本轮设计依据](notes/EP36_REVIEW.md)
- [只读来源快照](notes/source_snapshot.json)

主线为：独立动量和反转基线 → 简单加法模型 → 包含交互项和四状态的联合模型 → D1 至 D10 全部分组 → 风格控制与净收益检验。D10 表示最高分，D1 表示最低分。

四类比例用于解释联合模型的选择，并保留均衡配置与训练加权对照。首轮不依据 EP36 的历史贡献设定双跌超配比例。固定 H10，不搜索持仓天数、月内最佳日期或历史最佳分组。

目录遵循实验工作区约定：`config.yaml` 管理冻结合同，`notes/` 存放设计与来源；实验代码、测试、可发布结果分别在 `code/`、`tests/`、`outputs/publishable/`。完整模型和实际逐日持仓账本在被忽略的 `outputs/local_cache/`。配置中的EXECUTING为冻结时状态，当前状态以结果回执为准。

复核现有结果：在本目录执行 `OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 python -m pytest tests -q` 和 `OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1 python code/validate.py`。复现完整训练与回测应另开输出版本，保留本次结果。
