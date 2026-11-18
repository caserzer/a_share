# EP37 原78特征与RankIC训练

按用户“先保留EP36-78的原特征，然后以Rank IC为目标训练模型”的要求建立独立追加分支。状态：`COMPLETE_WITH_LIMITATIONS`，2026-11-18。

**[完整中文报告](outputs/REPORT.md)** · [图表HTML](outputs/REPORT.html) · [冻结合同](config.json) · [验证回执](manifests/validation.json)

保留原78项特征的公式、顺序和训练变换，恢复原每周训练记录。简单线性模型以可微Spearman近似损失训练，过去12个月的真实RankIC选择训练步数，季度扩展重训。保留原收益MSE和收益秩MSE两种78特征对照；交易固定H10、D1至D10，主组合为最高分D10。

| 模型 | 主区间RankIC | D10净年化 |
| --- | --- | --- |
| 原78特征 收益MSE | 0.0406 | +0.11% |
| 原78特征 RankIC目标 | 0.0552 | −1.69% |
| 原78特征 收益秩MSE | 0.0692 | +2.81% |
| 旧11特征 共同池重算 | 0.0071 | −11.72% |

主区间2021-01-11至2025-03-03开盘，共100个H10窗口；成本买10bp、卖20bp，账户为有边界的停牌估值代理。恢复完整输入后排序明显恢复，但RankIC目标尚未证明比原78特征收益MSE有更好的净收益或独立Alpha。扩展排序有139个窗口，部分连续账户在2025年后受未知终值限制，不能比较不同终点年化。

72个最终模型已保存在本地被忽略的`local_cache/models/`。当前最后一折为[2026Q4 RankIC模型](local_cache/models/2026Q4_RIC_78.json)，训练截止2026-09-30，最新使用标签到期日为2026-09-29，所选训练步数60；[模型路径与哈希回执](manifests/latest_model.json)。这不是实盘部署。

推理使用`model.predict(features, saved_model)`，输入原78特征列；训练中位数、均值、标准差及权重均包含在模型文件内。预测接口拒绝收益标签，分数只用于同日横截面排序。完整排名、目标持仓、所有十分组和连续账户结果见`outputs/`；逐日实际成交、持仓及净值见`local_cache/ledgers/`和`local_cache/daily_accounts.parquet`。

7项单元测试通过，72个保存模型重放通过，18条连续主成本代理账户账本独立重建通过。78项原特征的11,723,400个值和缺失位置完全一致；24折原E1训练行数与预测精确复现。来源、原EP37代码与新训练代码哈希在`manifests/freeze.json`冻结。

在本目录复核：

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=4 python -m pytest test_model.py -q
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=4 python validate.py
```

完整重跑应先将代码与合同复制到同级新目录，不复制已有缓存或回执，再依次执行`run.py prepare`、`train`、`select`、`economics`、`analyze`，以及`validate.py`、`report.py`。原EP36和EP37首轮保持只读；没有扩大参数搜索、修改执行方式、提交推送或部署。
