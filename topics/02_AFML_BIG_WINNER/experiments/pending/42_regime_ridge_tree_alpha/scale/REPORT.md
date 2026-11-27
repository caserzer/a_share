# EP42｜绝对量纲、模型形式与盈利归因的历史回放

407,372个沪深300股票日、23个季度折、1,389个日度评分截面已经完成核对。原值信息影响树的买单，但波动水平与离散度这一组特征的真实时点，对全账户的收益优势没有跨段通过登记条件。按市场状态在Ridge与树间切换，仍以D5主要账户检验判断。两池A4另核对特征、交易时段及风格归因。

| 实验和独立报告 | 本轮判读 |
|---|---|
| [S1](reports/S1.md) | 前段结构关联，后段未辨明 |
| [S2](reports/S2.md) | 同掩码历史点差为正，区间跨零且集中 |
| [S3](reports/S3.md) | 原尺度与固定尺度整账户跨段变号 |
| [S4](reports/S4.md) | 支持子样本有历史线索，全池判据未通过 |
| [S5](reports/S5.md) | 匹配分歧有限；固定构成状态无完整参考历史 |
| [G2](reports/G2.md) | 同特征同损失的高低状态差未辨明 |
| [G3](reports/G3.md) | 状态交互未见跨段稳定增量 |
| [A4](a4/REPORT.md) | 两池分数与实际损益均核平，风险为历史代理 |

沪深300每季度用已成熟周标签训练，收盘生成信号、下一开盘建H10仓。十份独立本金错峰运行，每段初始本金1，买10 bp、卖20 bp，同股成交净额收费。前段为2021-01-11至2025-03-03，后段独立从2025-03-03至2026-10-12。共同完整月份49、18个；表中账户差均为配对月收益的算术平均，单位 bp/月。95%区间段内每次抽连续三个月，共10,000次，按月数合并。各项均是登记晚于回放终点的历史机制检验。

日度输入按日期、股票编码核对。原Ridge78、原值树69和原配方树78与EP41分数和账户逐日对照，净值、现金、费用及净额交叉最大偏差低于1e−10。S1叶值位于每折原值树存档，叶ID字节串每一个字节对应一棵树，按树序读取。时间窗与实现见各自报告。[账户、持仓批次与路径恒等式](results/account_audit.json) · [账户复核](results/book_parity.csv) · [模型及填补常数](results/models) · [各臂逐月](results/months.csv) · [各段逐年与基准](results/annual_benchmarks.csv) · [原始订单](results/orders) · [结果索引及哈希](results/verification.json)

## 复现

使用主题目录 `.venv/bin/python`。按序运行 `prepare.py`、`joint_tree.py`、`fit_models.py`、`transform_scale.py`、`branches.py`、`interaction.py`、`style.py`、`replay.py`、`trace_origins.py`、`summarize.py`、`paired_only.py`、`ledger_extras.py`、`path_audit.py`、`node_features.py`、`encoding_bins.py`、`decision_capital.py`、`benchmark_scale.py`、`audit_final.py`、`write_reports.py`。早期内折依赖EP42 state的原始季度时钟与每日特征块；A4复现顺序和800实际覆盖见[A4报告](a4/REPORT.md)。原有EP41档案只读。
