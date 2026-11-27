# 本地复核

账户、模型、协议和取数回执均在EP43目录。日期使用A股交易日历。outputs/revisions/before_pool_rank_alignment 保留基本面排名修订前的账户，主报告读取 outputs/accounts。

## 查一笔交易

从 [年度净值](outputs/summary/annual.csv) 选股票池、arm、segment 与 multiple。进入 outputs/accounts/股票池/arm/段号，对照下列文件。arm 带一层斜线，例如 W/LP。day 和 stock 是从0开始的历史交易日和证券索引，可在 [300证券字典](outputs/symbols_300.csv)、[800证券字典](outputs/symbols_800.csv) 与 [交易日字典](outputs/summary/calendar.csv) 查回。

| 文件 | 记录 |
|---|---|
| targets.parquet | 每个决策日、袖、证券的冻结目标权重。day 为执行开盘，信号在前一交易日收盘。 |
| transactions.parquet | 稀疏的期初、期末份额、目标金额、成交净流量和实付费。未变化且无订单的头寸继承上日份额。 |
| cash.parquet、session.parquet、exposures.parquet | 十袖各自现金、日内与隔夜损益、收盘集中度、行业和市值敞口。 |
| fifo.parquet | 份额从买入到卖出的生命周期。可按是否一轮、段末结算、延期、随后再次买入筛选。 |
| 对应的 _2fee 文件 | 双倍费用独立账户的收盘决策、真实成交与现金。 |
| 上一级 daily.parquet、monthly.csv、detail.csv | 两档费率逐日净值、完整月和分段核对。 |

三个月区块抽样在每个估值段内独立进行。不同策略或同池等权基准可能先遇到缺价。年度表将完整自身窗口和同池等权共同窗口分别记为 whole 与 equal_common，空值保留。成本敏感性列的同池等权参考固定为原费率。

## 复核与重建

从本项目根目录运行。模型使用项目本地Python环境、LightGBM和单线程BLAS，账本使用C++17。以下命令核查本次产物，包括预登记原件指纹、账户资金守恒、两个费率下的目标与成交、前视时钟、区间和报告链接。

```bash
ep=topics/02_AFML_BIG_WINNER/experiments/pending/43_rank_blend_sessions_turnover_fundamentals
research_py=topics/02_AFML_BIG_WINNER/.venv/bin/python
env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/ep43mpl "$research_py" "$ep/code/verify43.py"
```

完全重建可在一份保留相同相对目录结构的研究副本内运行。下表给出脚本顺序。模型与账本脚本会复用已有的季度文件和完成标志，新版本使用独立输出位置。CSV和Parquet表为本地研究产物，原件收据包含抓取时间、发行人、报告期、URL与哈希。

| 顺序 | 入口及参数 |
|---|---|
| 上游数据 | EP42 state/inputs42.py、state/domain_features.py 生成 /tmp/ep42_regime_r1_inputs 日截面缓存。EP36 private、EP38本机市场面板以及EP40至EP42冻结评分与开户输入见 [历史依赖指纹](outputs/summary/input_hashes.csv)。 |
| 树与分时模型 | models.py 同时处理两池31个季度，score_audit.py 分别传 300 和 800 复核预测，生成独立总秩树。diagnostic_ranks.py 按相同破同分顺序复核前K交集。 |
| 排名与账户 | accounts43.py 分别传 300 和 800。bl.py 依次传入 300 B、800 B、300 L、800 L。800冻结迁移使用300内折记录。 |
| 权重诊断 | w_audit.py、w_diagnostics.py 各传股票池。后者保留同期开盘的十袖状态，进行单袖H10分叉回放。 |
| 基本面源 | fetch.py 采集带原始回执的财报及历史总市值。disclosures.py、issuer_sources.py、original_cells.py、amendments.py 建立原件和修订证据。可直接使用封存的 outputs/sources 和 outputs/fundamental/originals、primary_cells、amendments 离线重建。 |
| 基本面训练 | fund_panel.py、rank_population.py，随后 fund_fit.py fit、fund_fit.py accounts、fund_diag.py、supplement.py F、industry_ic.py。严格子集用 strict_panel.py、strict_accounts.py。source_audit.py、asof_examples.py 生成字段、取数及时间边界盘点，support_audit.py 和 edge_attribution.py 核算实际资本覆盖、风格和尾部。 |
| 账本封存 | supplement.py 各传股票池补同席数对照。seal_orders.py 按股票池及 B、L、W 执行，800另执行 F。positions43.py、reconcile.py、mechanisms.py 分别对两池重建风险、FIFO与资金变化。 |
| 汇总 | parity43.py、statistics43.py、final_bridges.py、write_results.py、verify43.py。 |

固定前瞻门槛为实际入场前封存后12及24个不重叠成熟H10。本轮是截至2026-10-12的历史账，前瞻计数为0。
