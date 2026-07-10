# Episode 20 Research Plan：论文约束下的 A 股 OHLCV 正 Beta 暴露研究

> 文档状态：`draft_research_plan`
>
> 生成日期：2026-07-10
>
> Episode ID：`20_ohlcv_positive_beta_exposure_research`
>
> Supersedes draft ID：`20_ohlcv_directional_alpha_replication`
>
> 上游结论：Episode 19 已结题；B2 保留为冻结的、已知可增加大赢家暴露的正 beta incumbent。
>
> 重启性质：`topic_level_human_restart`
>
> 自动授权：`upstream_automatic_authorization = false`
>
> 本 Episode 第一份预期需求：`requirement_20a_paper_lineage_data_and_replication_contract.md`

## 0. 一页结论

EP20 不再继续搜索“更像大赢家的事件形态”，而是更换被解释变量：

```text
EP1–EP19：event -> MFE / winner enrichment -> suppress left tail
EP20：     frozen signal -> fixed-horizon realized return -> holdable positive-beta sleeve
```

主问题是：**主要由 PIT OHLCV 构造、且有论文依据的信号，能否在本项目 A 股可执行股票池中形成一个全资金、成本后
预期收益为正、右尾/大赢家暴露为正、左尾与回撤在冻结预算内的可持有 sleeve？**

### 目标决断：追求正 beta，不要求 alpha

EP20 的 primary objective 是 `deployable_positive_beta`，不是“风险调整后仍显著的 alpha”。一个 sleeve 的收益即使能被
市场 beta、波动率、size、board 或流动性暴露解释，只要这些暴露是事前透明、可以持有、成本后仍有正收益，并满足
左尾/回撤/容量预算，就可以通过。Scale matching、within-vol sort 和横截面回归保留为**收益来源分解**，不再是淘汰门。

因此 B2 不再是 negative control，而是：

```text
arm_role = frozen_positive_beta_incumbent
known_property = about +33% big-winner exposure before matched attribution
alpha_claim = false
promotion_condition = fixed-return, cost, left-tail, drawdown and capacity gates pass
```

若新候选在 matching 后仍有增量，额外标记为 `positive_beta_with_incremental_alpha`；但没有该增量不会自动失败。

研究顺序固定为：

1. 先做论文、公式、数据和可复制性审计，不看本地 outcome；
2. 用 TrendPV、total momentum、residual momentum 和 Low Vol 的论文公式约束项目适配；
3. 将论文的 long-short 因子证据桥接到本项目真正关心的 long-only、full-capital、next-open 可执行收益；
4. 只有主信号通过 historical beta-design gate，才允许增加 FIP；
5. Low Vol 与 moving-average timing 只进入风险/组合层，不冒充独立 entry edge；
6. CNN 只作为共享样本上的表征上限诊断，不直接成为生产策略；
7. 历史设计/复制诊断完成后冻结最多两个候选，等待 freeze 之后真实形成的 forward cohort。

当前本地日频数据覆盖约为 2017-01 至 2026-05；warm-up 后只有约 65–75 个可用月，且这段历史已被本 topic 的
EP15–EP19 反复观察。**整段本地历史一律是 design-contaminated evidence；唯一可信支持只能来自 contract freeze
之后真实形成的 forward cohort。**任何 freeze 前已经发生、以后才补入数据库的数据都属于 historical backfill，不能
重命名为 forward OOS。

此外，`U_project` 是每月约 400–500 只的 top-N 可执行池，而论文通常使用排除最小 30% 后的全 A 股宽截面。虽然
qfq 价格文件接近全市场，但宽截面 PIT 总股本/市值和 E/P 当前未确认可用。因此：

```text
不补宽截面 PIT history -> EP20 默认是 paper-grounded project adaptation
补齐宽截面 PIT market-cap/E-P/history -> 才可能另行获得 exact replication 资格
```

若要发表“复制论文”的主张，补齐至少至 2005 年的宽截面 PIT history 是近似必需项；否则 paper-native 结果只作
诊断，EP20 的有效目标仍是项目正 beta 适配。

换用 1-month primary label 带来一个现实优势：每个 forward decision month 约一个月后即可完成标签。若约在
2026-08 freeze，6 个完整月可在 2027 年初形成 interim readout，12 个独立月最快约在 2027 年中至第三季度形成
positive-beta support；明显快于 19B3 的 120-session 主标签。

EP20 的成功不是“某个 top bucket 的 MFE 更高”，而是同时满足：

```text
positive fixed-return exposure
+ long-only full-capital economic value
+ positive exposure and transparent risk-source attribution
+ frozen left-tail / drawdown budget
+ cost/capacity feasibility
+ cross-time and cross-sectional stability
+ true-forward confirmation
```

在这些门通过之前，不授权 policy、portfolio optimization 或 production signal。

---

## 1. 为什么必须更换研究对象

### 1.1 EP19 已经证明的边界

EP19 的 B2 family 能增加大幅上涨路径的暴露，但也同时增加左尾、VOL60 和路径振幅。随后做的 suppressor、hard trim
与 inverse-vol budget 主要是在 scale 上做取舍：风险压缩能够改善左尾，却会同步切走决定均值的厚右尾。这个模式说明：

```text
high MFE enrichment != positive conditional mean
right-tail exposure can be useful beta even when it is not alpha
lower left tail != better full-capital return
```

因此，继续在同一事件附近加入 RSI、MACD、均线交叉或更多 suppressor，最可能重复得到“左右尾一起动”的结果，
却不能回答这种 beta 在固定期限、全资金和成本后是否值得持有。EP20 的换轴是 utility 验证，不是否认 B2 的正暴露。

### 1.2 EP20 的估计对象

主估计对象从 barrier/path label 改为固定收益：

```text
Y_primary(i,t) = executable total return from next eligible open after decision t
                 to next scheduled rebalance open

Y_attribution(i,t) = Y_primary(i,t)
                     - contemporaneous benchmark/cash return over the same interval
```

`Y_primary` 的成本后、cash-inclusive、full-capital 结果决定正 beta 是否可持有；`Y_attribution`、factor alpha 与
matched lift 只解释收益来自哪里。它们可以提升证据等级，但不是 primary pass 的必要条件。

必须同时报告：

- 原始收益 `raw_return`；
- 基准超额收益 `excess_return`；
- 扣除交易成本后的 `net_return`；
- long-only top bucket 的全资金收益；
- top-minus-bottom 因子收益；
- cash 未投资口径与只在候选内平均口径的差异。

MFE/MAE、`+50%`、`+100%` 和 first-hit ordering 降级为解释性 path diagnostics，不能再充当 primary success metric。

### 1.3 “正 beta”与“alpha”的操作定义

这里的“正 beta”是研究目标术语：**持有某类事前可识别股票，可以获得为正的、经济上可实现的 payoff exposure**。
它不等同于 CAPM 回归系数，也不要求回归截距显著为正。产物统一使用：

```text
positive_beta_sleeve = net full-capital expected return above frozen cash hurdle
                       + positive right-tail / winner exposure
                       + acceptable left-tail, drawdown, turnover and capacity

market_beta          = regression exposure to the market factor
incremental_alpha    = return increment that remains after frozen risk/scale attribution
```

决策优先级固定为：

1. 先判断 sleeve 是否有可持有的正 beta；
2. 再说明收益由 market/volatility/size/board/liquidity 中哪些暴露贡献；
3. matching 后仍存活的部分才叫 incremental alpha；
4. `incremental_alpha = 0` 不否决正 beta；但若 scale 暴露导致左尾、回撤或容量超预算，则 sleeve 仍不可部署。

---

## 2. 论文证据地图与角色冻结

### 2.1 证据优先级

文献必须按下列优先级使用：

1. journal version of record；
2. 作者/大学保存的完整 working paper，用于获得公式、样本和附录细节；
3. journal internet appendix 与官方 replication code；
4. 后续市场/样本论文仅用于外部有效性与压力测试；
5. 搜索摘要、博客、聚合页只作定位，不能支撑 requirement 中的公式或阈值。

所有实现公式都必须在 `paper_formula_registry.csv` 中映射到论文、版本、页码/表格/公式编号、项目字段和 timing。

### 2.2 核心论文与研究角色

| 路线 | 核心论文证据 | 原论文对象 | EP20 冻结角色 |
|---|---|---|---|
| TrendPV | Liu, Liu, Zhou & Zhu (2024) | A 股多期限价量趋势因子 | `primary_candidate_1` |
| Residual Momentum | Blitz, Huij & Martens (2011)；Jansen, Swinkels & Zhou (2021) | 去除系统因子后的 12-1 momentum | `primary_candidate_2` |
| Total Momentum | residual-momentum 论文中的原始 comparator | 12-1 total return momentum | `mandatory_incumbent_comparator` |
| FIP | Da, Gurun & Warachka (2014) | 在相同 formation return 下区分连续与离散信息 | `conditional_incremental_challenger` |
| Low Vol | Blitz, Hanauer & van Vliet (2021) | A 股低波动因子 | `risk_scale_comparator_and_overlay` |
| MA timing | Han, Yang & Zhou (2013) | 对波动率组合做组合层择时 | `portfolio_risk_overlay_only` |
| OHLCV CNN | Jiang, Kelly & Xiu (2023) | 价格图像预测未来收益 | `representation_oracle_only` |
| EP19 B2 | EP19 本地冻结证据 | 高波动、双尾、约 +33% 大赢家暴露 | `frozen_positive_beta_incumbent` |
| 大规模技术规则 | Bajgrowicz & Scaillet (2012) | 7,846 条规则的数据窥探检验 | `negative_governance_evidence` |

### 2.3 不允许的角色漂移

- TrendPV 的 **score** 主要来自 OHLCV，但论文完整 Trend factor 还使用 Size 和 earnings-to-price 参与 2×3×3
  portfolio sorts。若本地没有 PIT E/P，不能把 raw TrendPV score 称为“完整 Trend factor 精确复制”。
- Residual Momentum 需要先用市场、size、value 因子回归。只用市场残差的版本是项目适配，不是 Blitz et al. 或
  Jansen et al. 的 exact replication。
- Low Vol 的 long-short beta-neutral premium 不等于 long-only sleeve 收益；它优先是 scale comparator/风险层。
- Han–Yang–Zhou 的 moving average 作用于**先按波动率形成的组合指数**，不是个股均线交叉。不得把它改写成
  个股 entry rule 后仍引用原论文结论。
- CNN 的高 Sharpe 来自论文特定的美国样本、图像、训练和交易设定；只能检验表征缺口，不能作为本地先验收益。

---

## 3. 论文方法档案

本节固定每条路线的原论文定义、可迁移部分和不可迁移部分。Requirement 不得只引用论文结论而省略构造细节。

### 3.1 TrendPV / Trend Factor in China

#### 3.1.1 版本与样本

版本论文为 Yang Liu、Yang Liu、Guofu Zhou、Yingzi Zhu，*Trend Factor in China: The Role of Large
Individual Trading*，*The Review of Asset Pricing Studies* 14(2), 348–380，2024，DOI
[`10.1093/rapstu/raae003`](https://doi.org/10.1093/rapstu/raae003)。

完整方法以作者 working paper 和 internet appendix 为补充。论文使用沪深 A 股，底层数据覆盖 2000-01-04 至
2018-07-31；由于 400 个交易日 signal warm-up 和约 38 个月系数 warm-up，有效因子样本约从 2005-01 开始。

#### 3.1.2 原论文信号

在每个月末，对每只股票和窗口

```text
L in {3, 5, 10, 20, 50, 100, 200, 300, 400}
```

构造价格与成交量的移动平均，并用当期价格或成交量归一化：

```text
MP(i,L,t) = mean(close(i,t-L+1:t)) / close(i,t)
MV(i,L,t) = mean(volume(i,t-L+1:t)) / volume(i,t)
```

每月做横截面回归：用 `t-1` 月末已知的多期限 price/volume signals 解释 `t` 月股票收益。每一个 signal 的下一月
系数预测使用指数平滑：

```text
E_t[beta(t+1)] = (1 - lambda) * E_(t-1)[beta(t)] + lambda * beta(t)
lambda = 0.02
```

再用预测系数与当月 signal 合成股票 trend score。所有用于 `t+1` 预测的信息必须在 `t` 月末可得。

原论文完整 Trend factor 并不止于这个 score。其典型构造还包含：

- 排除市值最小 30% 股票；
- Size 以中位数断点分组；
- earnings-to-price 与 trend score 用 30/70 分位断点；
- 形成 2×3×3 共 18 个价值加权组合；
- Trend 因子为 6 个 high-trend 组合均值减 6 个 low-trend 组合均值。

working-paper 样本中，论文报告 Trend 因子月均收益约 1.43%、Sharpe 约 0.48、最大回撤约 13.17%，并讨论约
1.35% 的交易成本 break-even。它们是原样本 long-short factor 统计量，不是本项目 long-only 收益先验，也不能直接
作为本地 pass floor。

#### 3.1.3 A 股交易细节与本项目偏差

论文对停牌价格和缺失成交量有其特定处理，例如停牌期沿用最近价格，并为交易记录不足的月份使用历史量信号。
本项目已有 executable universe，因此必须同时运行：

```text
paper_semantics_diagnostic  = 尽量遵循论文缺失/停牌处理，只用于复制
project_executable_primary  = 决策时必须可交易，next-open 无成交不得假设成交
```

两者不能混合。若结论只在论文式插补样本中成立，而在可执行样本中消失，关闭 deployment claim。

#### 3.1.4 EP20 可复制层级

```text
T0 = total 12-1 momentum comparator
T1 = OHLCV-only raw TrendPV score
T2 = paper-native full Trend factor, only if PIT E/P and total-share market cap pass
T3 = project-executable long-only TrendPV bridge
```

T1 通过不等于 T2 exact replication；T2 通过也不等于 T3 可部署。

### 3.2 Residual Momentum

#### 3.2.1 原始证据

David Blitz、Joop Huij、Martin Martens，*Residual Momentum*，*Journal of Empirical Finance* 18(3),
506–521，2011，DOI [`10.1016/j.jempfin.2011.01.003`](https://doi.org/10.1016/j.jempfin.2011.01.003)。

原论文使用 CRSP 1926–2009 数据，组合结果约从 1930 年开始。每月对个股过去 36 个月的超额收益做 Fama–French
三因子回归；随后用最近 12 个月、跳过最近 1 个月的残差收益，并以同期残差波动率标准化，构造 residual momentum
score。排序后形成 decile long-short，并考察 1、3、6、12 个月 overlapping holding periods。

论文报告的代表性 1-month holding 结果中，total momentum 年化收益约 10.26%、波动约 22.70%、Sharpe 约 0.45；
residual momentum 年化收益约 11.20%、波动约 12.49%、Sharpe 约 0.90。核心贡献是降低动态因子暴露和波动，
而不是保证所有市场都有相同收益。

#### 3.2.2 A 股版本证据

Maarten Jansen、Laurens Swinkels、Weili Zhou，*Anomalies in the China A-share Market*，
*Pacific-Basin Finance Journal* 68, 101607，2021，DOI
[`10.1016/j.pacfin.2021.101607`](https://doi.org/10.1016/j.pacfin.2021.101607)。论文使用 CSMAR 的沪深 A 股，
主样本 2000–2019，并系统检验 32 类 anomaly。

其 A 股 residual momentum 同样基于过去 36 个月的市场、size、value 三因子残差，再计算 12-1 标准化残差表现。
论文表中 residual momentum 的 1-month long-short 收益约为：

```text
equal weighted：0.66% / month，t = 3.36
value weighted：0.59% / month，t = 2.11
```

而普通 12-1 momentum 在其样本中较弱；residual momentum 的效果在 6/12 个月持有期明显衰减。因此 EP20 的
primary holding horizon 固定为 1 个月，不允许 outcome 后改成表现最好的持有期。

#### 3.2.3 精确复制与适配版本

精确 A 股三因子定义还依赖 Jianan Liu、Robert F. Stambaugh、Yu Yuan 的 *Size and Value in China*，
*Journal of Financial Economics* 134(1), 48–69，2019，DOI
[`10.1016/j.jfineco.2019.03.008`](https://doi.org/10.1016/j.jfineco.2019.03.008)。该文针对 A 股壳价值问题
排除市值最小 30%，并用 earnings-to-price 而不是 book-to-market 构造 value factor。20A 必须冻结 residual
regression 使用作者公开 CH-3 factor series，还是用本地 PIT 数据重建；两者都要记录 factor vintage 和可得时间，
不得混用全样本更新后的 factor 与实时可得 claim。

```text
R0 = total_return_momentum_12_1
R1 = exact_china_ff3_residual_momentum
R2 = market_only_residual_momentum_adaptation
R3 = market_plus_size_plus_ep19_2025_board_proxy_adaptation
```

- 只有本地 PIT market/size/value factor 完整、无 future accounting information 时，R1 才可标为 exact。
- R2/R3 必须带 `_adaptation` 后缀。它们可以作为本项目的正 beta 候选独立进入 frozen forward，但永远不能将失败或
  不可评价的 R1 升级为“exact replication 通过”。
- 行业中性 exact residual momentum 仍要求 historical PIT industry membership；board proxy 不能替代该论文主张。
- 36 个月回归与 12-1 scoring 的完整历史要求意味着约 47 个月有效 warm-up；不允许用不足月份自动降阶而仍叫 exact。

#### 3.2.4 EP19 2025 板块数据作为 industry proxy

按本项目决策，R3 和 exposure attribution 使用 EP19 冻结的 2025 年东方财富概念板块快照：

```text
proxy_id = ep19_dc_2025_static_board_proxy
source   = outputs/tushare_dc_yearly_board_snapshot/by_year/2025/
           dc_member_2025_20250102.csv
snapshot = 2025-01-02 first-open snapshot
rows     = 43,468 memberships
boards   = 458 listed boards; 314 boards with member rows
shape    = multi-label concept-board membership, not one-stock-one-industry
```

上述 `source` 的完整仓库相对路径为：

```text
topics/02_AFML_BIG_WINNER/experiments/pending/
19_entry_universe_pit_tradability_preflight/outputs/
tushare_dc_yearly_board_snapshot/by_year/2025/dc_member_2025_20250102.csv
```

其研究角色冻结为 `static_industry_proxy`，而不是 `historical_pit_industry`。使用规则：

1. 2025 快照在整个实验中保持不变，不根据 outcome 选择板块、合并板块或更换 snapshot；
2. 对 2025 年以前的历史日期，它是由 2025 taxonomy 回填的 look-ahead proxy，只能用于 design-stage attribution/
   sensitivity，不能支撑历史 PIT、exact replication 或 alpha claim；
3. 对 contract freeze 之后的 forward dates，2025 snapshot 已是事前冻结信息，可用于 R3 的 board-exposure control；
4. 因一只股票可以属于多个概念板块，20A 必须在 outcome access 前冻结 multi-hot exposure、缺失股票处理、稀有板块
   合并和共线性处理；不得事后选择最有利的“主行业”；
5. 必须同时报告不使用 board proxy 的 R2，区分 market-only 与 board-controlled adaptation；
6. 任何使用该 proxy 的产物都带 `industry_semantics=ep19_2025_static_concept_board_proxy`。

这项代理解决的是项目 exposure attribution 和 forward 控制问题，不改变宽截面 PIT E/P/market-cap 缺失导致 exact
Trend/CH-3 replication 不可得的事实。

### 3.3 Frog in the Pan（FIP）

Zhi Da、Umit G. Gurun、Mitch Warachka，*Frog in the Pan: Continuous Information and Momentum*，
*The Review of Financial Studies* 27(7), 2171–2218，2014，DOI
[`10.1093/rfs/hhu003`](https://doi.org/10.1093/rfs/hhu003)。

FIP 不是独立的“涨跌天数因子”；它首先要求股票具有相似的 formation-period cumulative return，再用 information
discreteness 区分收益是由连续小变化还是少数离散跳跃形成。论文核心变量可写为：

```text
PRET = cumulative return over prior 12 months, skipping the latest month
ID   = sign(PRET) * (% negative-return days - % positive-return days)
```

低 ID 对应更连续的信息到达，高 ID 对应更离散的信息到达。论文对 PRET 与 ID 做 sequential double sort，并考察
6-month 以及更长持有期。其 1976–2007 主样本中，相同 PRET 下 continuous 与 discrete 组的 6-month momentum
差异约 5.95 个百分点（t≈5.13）；扩展样本的 5.94% 与 -2.07% 属于另一报告口径，不能与主样本表格混为同一估计。

EP20 只允许在 TrendPV 或 residual momentum 已显示固定收益方向后，将 FIP 作为 1 个增量维度：

```text
within matched formation-return and volatility cells:
    continuous-drift candidate vs discrete-jump candidate
```

不得先扫描大量 ID 窗口、zero-return 处理和断点，再选择最好版本。2024 年关于 market-state 的后续论文报告 FIP 与
momentum 关系集中在 UP market；EP20 预注册 market state 只作 heterogeneity stress，不作为事后选择开关。

### 3.4 A 股 Low Vol

David Blitz、Matthias X. Hanauer、Pim van Vliet，*The Volatility Effect in China*，
*Journal of Asset Management* 22, 338–349，2021，DOI
[`10.1057/s41260-021-00218-0`](https://doi.org/10.1057/s41260-021-00218-0)。

论文样本为 2000-11 至 2018-12 的 A 股可投资 universe，基准构造使用过去 36 个月月收益波动率，每月形成价值加权
decile，观察下一月；还构造 beta-neutral 2×3 VOL factor。论文报告 VOL factor 年化 premium 约 9.1%、Sharpe
约 0.88，并在不同 lookback 和 holding periods 中做稳健性测试。

这些结果支持“低风险效应值得作为 A 股强基准”，但不能直接证明它能形成满足本项目预算的正 beta sleeve。EP20 中：

```text
L0 = raw VOL60 / 12m / 36m scale comparator
L1 = low-vol long-only comparator
L2 = beta-neutral long-short diagnostic, only with valid factor construction
L3 = candidate signal within-volatility matched evaluation
```

Vol-matched cells 用于解释 TrendPV/residual 的收益是否来自波动率。若 matching 后收益消失，但原 sleeve 仍满足成本后
正收益与风险预算，则标为 `positive_beta_supported_scale_explained`，不判失败；若波动率来源同时导致左尾/回撤超预算，
才判为不可持有。

### 3.5 波动率组合上的 Moving-Average Timing

Yufeng Han、Ke Yang、Guofu Zhou，*A New Anomaly: The Cross-Sectional Profitability of Technical Analysis*，
*Journal of Financial and Quantitative Analysis* 48(5), 1433–1461，2013，DOI
[`10.1017/S0022109013000586`](https://doi.org/10.1017/S0022109013000586)。

论文先用个股日收益年化波动率形成组合，再对**组合指数**应用 10/20/50/100/200 日 moving average：若前一日组合
收盘高于前一日 MA，则持有该组合，否则持有 30-day T-bill。论文在美国 1963/1973–2009 样本中发现高波动组合的
MA timing 相对 buy-and-hold 有较高异常收益，并明确计入每次交易 25bp 的成本敏感性。

EP20 只在正 beta sleeve 已成立后运行固定的 20-day MA overlay：

```text
input  = frozen long-only candidate sleeve NAV
state  = prior_close > prior_MA20
action = hold sleeve, otherwise cash/benchmark-defined defensive asset
```

它评价的是风险预算和 drawdown，不评价个股 entry；不得扫描 5 个 MA 后择优。

### 3.6 OHLCV Image CNN

Jingwen Jiang、Bryan T. Kelly、Dacheng Xiu，*(Re-)Imag(in)ing Price Trends*，*The Journal of Finance*
78(6), 3193–3249，2023，DOI [`10.1111/jofi.13268`](https://doi.org/10.1111/jofi.13268)。官方页面同时提供
internet appendix 与 replication code。

论文把 5/20/60 日 OHLC、移动平均和成交量画成标准化图像，用 CNN 预测未来 5/20/60 日收益方向。原始研究使用
CRSP 1993–2019；1993–2000 内做训练/验证，冻结模型后测试 2001–2019。论文报告不同 horizon 和 weighting 下的
强 long-short 结果，但短周期换手很高，并对 10/20bp 单边成本做专门讨论。

EP20 的 CNN 必须满足：

- 与手工信号完全相同的 universe、decision dates、labels、cost model 和 eligibility denominator；
- 严格时间切分，不允许随机打散本地全样本；
- 只运行一个预注册图像/horizon 主规格和一个 appendix sensitivity；
- 输出 CNN 相对 TrendPV/residual 的增量，而不是单独展示最高 Sharpe；
- 仅作为 `representation_oracle`，即使通过也只授权下一轮表征研究。

20F 另设 `cnn_training_support_gate`。20A 必须在 outcome access 前冻结最低训练日历长度、独立 market regimes、
train/validation 月数、图片数量、每月有效股票数和最小 frozen-test 月数。当前历史在 warm-up 后可能只剩约 4–5 年可供
训练；若任一支持门不足，状态固定为 `cnn_underpowered_not_evaluable`，不得把 CNN 失败解释为“OHLCV 没有信息”，
也不得用于关闭日频 OHLCV 主线。

### 3.7 为什么禁止 RSI/MACD/大网格

Pierre Bajgrowicz、Olivier Scaillet，*Technical Trading Revisited: False Discoveries, Persistence Tests, and
Transaction Costs*，*Journal of Financial Economics* 106(3), 473–491，2012，DOI
[`10.1016/j.jfineco.2012.06.001`](https://doi.org/10.1016/j.jfineco.2012.06.001)。论文在 1897–2011 DJIA 上检验
7,846 条技术规则，使用 false discovery rate、持久性测试和成本，结论是事前选择与成本会消除历史上的表观优势。

它不是“中国市场所有技术信号无效”的证明，但对 EP20 提供直接治理约束：

```text
no unrestricted RSI/MACD/MA/breakout grid
no best-horizon reporting
no outcome-driven threshold repair
all tested arms count toward multiplicity family
```

---

## 4. 本地数据可行性与必须先解决的缺口

### 4.1 当前已知覆盖

截至计划生成时，现有核心数据大致为：

| 数据 | 当前覆盖/状态 | 可支持 | 主要限制 |
|---|---|---|---|
| PIT executable universe | 2017-01 至 2026-05 | 项目股票池、可交易状态、总股本/市值 | 不是论文全 A 股 universe |
| qfq OHLCV | 约 4,597 只股票，至 2026-05 | 日频价格、成交量、收益、图像 | 需要严格 corporate-action/timing QA |
| benchmark daily | 2017-01 至 2026-05 | market return、calendar | 历史长度有限 |
| PIT earnings-to-price | 未确认可用 | Trend full factor、China value factor | 若缺失，不得 exact |
| EP19 2025 DC board membership | 已有 43,468 条 multi-label membership | R3/attribution 的静态 industry proxy | 2025 前是 look-ahead proxy，不是历史 PIT industry |
| PIT historical industry | 未确认可用 | 论文级 industry-neutral analysis | 2025 静态 proxy 不能升级此状态 |
| risk-free return | 未冻结 | excess-return regression | 需来源、频率、发布日期契约 |

### 4.2 Warm-up 对有效样本的影响

若不补历史，warm-up 后只有约 65–75 个可用月（精确数量由 20A 按冻结公式重算）：

- TrendPV 最长 400 sessions 加系数预测 warm-up，当前可行性实测最早约 2020-03；20A 按论文初始化规则复算；
- exact residual momentum 需要 36 个月回归，再使用 12-1 residual ranking，当前实测最早约 2020-12；
- Low Vol 论文主规格需要 36 个月月收益；
- CNN 还要划出互不重叠的 train、validation 与 frozen test。

这不只是统计功效偏薄的问题。2017–2026-05 已被本 topic 的多个 Episode 反复观察，整段都属于
`design_contaminated_historical`。历史 Newey–West、bootstrap 或多 time-fold 一致性只能帮助设计和排错，不能恢复
OOS 身份，也不能形成可信 support。

20A 必须在 outcome access 前做二选一：

```text
Option A：补齐至少至 2005 年的 qfq/PIT 状态/市值历史，并重建可审计 lineage；
Option B：保留现有历史，但将任务降级为 project adaptation feasibility，禁止发表 exact replication claim。
```

若目标包括“复制论文”，Option A 是近似必需项而不是普通 robustness；Option B 等于放弃一切 exact replication
support，只保留 paper-grounded adaptation。不能因为补历史困难而偷偷缩短 36 个月/400 日窗口，或将不稳定 warm-up
期计入 primary result。

### 4.3 两个 universe，两个 estimand

必须并行但分开维护：

```text
U_paper:
    尽可能接近论文的沪深 A 股截面、最小市值排除、value weighting 与 accounting filters；
    用于判断“是否复制论文”。

U_project:
    本项目已有 PIT top-N 400/100 executable universe；
    用于判断“是否对目标策略有用”。
```

`U_project` 当前约每月 400–500 只、历史去重约 1,800 只；论文宽截面通常在排除最小 30% 后仍覆盖更广的 A 股。
趋势、动量与低波收益可能随 size 截面系统变化，因此 universe 差异不是普通小误差。不得把 `U_project` 的结果命名为
paper replication，也不得用 `U_paper` 中不可交易股票的收益支撑 deployment。

返回口径也必须分开：

```text
paper_return_semantics:
    paper-defined month-end close-to-close / total return，diagnostic only

project_return_semantics:
    decision at close -> next eligible open entry -> next rebalance eligible open exit
    with suspension, limit, cost and cash handling，primary economic estimand
```

### 4.4 20A 数据可得性 go/no-go 表

20A 的第一张决策表必须是 `ep20a_data_replication_go_no_go.csv`，在写 20B requirement 前锁定每条路线可达到的最高
证据等级：

| 数据门 | 若通过 | 若失败 | 对正 beta 主线的影响 |
|---|---|---|---|
| 宽截面 qfq OHLCV + 状态历史 | 可构造 `U_paper` price-side signals | 只能 `U_project` | adaptation 仍可继续 |
| 宽截面 PIT total-share/market-cap | 可复制 size exclusions/weights | full Trend/CH-3 universe 不可 exact | 不阻断项目正 beta |
| PIT E/P + publication timing | 可重建 China value/full Trend | T2/R1 exact 不可达 | 改用预注册 adaptation |
| historical PIT industry | 可做论文级 industry control | exact industry-neutral 不可达 | 使用 EP19 2025 static proxy |
| EP19 2025 board proxy lineage | 可做 R3 forward board control | R3 unavailable | R2 market-only 保留 |
| risk-free 与 benchmark vintage | 可做 paper excess/factor regression | exact residual 不可达 | raw-return beta 仍可评价 |
| 历史长度/有效月数 | paper diagnostic 有基本 power | historical underpowered | 只做 pipeline/design QA |
| CNN train/validation support | 允许 20F | `cnn_underpowered_not_evaluable` | 不得用 CNN 关闭 OHLCV 主线 |

每行必须输出 `status`、`evidence_path`、`coverage`、`highest_allowed_role`、`blocked_arms` 和机械 verdict。20A 报告首页
直接给出 `exact_replication_reachable`、`project_adaptation_reachable`、`forward_beta_test_reachable` 三个布尔值。

### 4.5 20A outcome firewall

20A 在读取任何 `future_return`、MFE、MAE、winner label 或候选收益之前，必须冻结并 hash：

- paper/version registry；
- 公式、lag、warm-up、missing-data 和 zero-return 规则；
- universe 与 return semantics；
- arms、primary horizon、bucket breakpoints；
- factor model、risk-free 和 benchmark；
- cost/capacity assumptions；
- sample split 和 forward start；
- primary metrics、multiplicity family、gates 与 terminal states。

允许在 freeze 前查看的仅有日期覆盖、字段、缺失率、重复键、PIT lineage、交易日历与样本数量，不允许查看 outcome
分组统计。所有 outcome-access 文件必须纳入审计日志。

---

## 5. 分阶段研究架构

### Stage 20A：Paper lineage、数据和复制契约

目标：回答“每篇论文究竟做了什么，本地能精确复制到哪一级，以及正 beta forward test 能否执行”。不产生任何
收益支持结论。

必做审计：

1. 论文 version-of-record、完整方法稿、appendix、code 链接与 hash；
2. 每个公式的字段、频率、lag、断点、weighting、holding period；
3. `U_paper` 与 `U_project` 的覆盖和差异；
4. PIT E/P、total share、historical industry、risk-free、benchmark availability；
5. EP19 2025 static board proxy 的 schema、multi-label coverage 与 forward 可用性；
6. qfq 的 corporate action、停牌、涨跌停和 next-open eligibility；
7. warm-up 后每月 eligible N、可形成月份数；
8. backfill 方案与 forward 起点；
9. exact / adapted / unavailable 的机械分类；
10. `ep20a_data_replication_go_no_go.csv` 与各路线最高证据等级。

20A 输出后必须再次人工批准，才可读取历史 outcome 运行 20B。

### Stage 20B：Paper-grounded historical design / replication diagnostic

目标：先确认本地数据和实现能否重现论文方向，不优化项目策略。

最小 arms（避免与 EP19 B2 混淆，paper-diagnostic 使用 `P*` 命名）：

```text
P0 total momentum 12-1
P1 raw TrendPV score adaptation
P2 full Trend factor, only if exact-data gate passes
P3 exact FF3 residual momentum, only if exact-data gate passes
P4 market-only residual adaptation
P5 market+size+EP19-2025-board-proxy residual adaptation
P6 Low Vol comparator
```

报告 deciles/quintiles、top-bottom monotonicity、paper-defined long-short、equal/value weighted 和论文指定持有期。结果必须
与论文的 sample/universe 差异并列解释，不以“没达到论文同等 Sharpe”直接判错，也不以同方向点估计直接判成功。

20B 全部带 `sample_role=design_contaminated_historical`。无论结果多强，它都只是 formula QA、effect sizing 和候选冻结
依据，不是 OOS support。Option B 下，20B 标题和报告不得使用“local replication passed”。

### Stage 20C：Project-executable positive-beta bridge

目标：回答论文因子是否转化为本项目需要的 long-only 正向收益。

冻结以下比较：

```text
C0 = all eligible U_project, full-capital baseline
C1 = total momentum top bucket
C2 = TrendPV top bucket
C3 = residual momentum top bucket
C4 = Low Vol top bucket comparator
C5 = frozen EP19 B2 positive-beta incumbent
```

每个 active arm 同时报告：

- 等权 active-position return；
- 按当月可投资资金归一后的 full-capital return；
- 缺少信号/不可交易时持有 cash 的 return；
- gross 与 net return；
- absolute net return 与 frozen cash hurdle 的差；
- top bucket、top-minus-middle、top-minus-bottom；
- 右尾/大赢家 exposure、左尾/回撤预算；
- 相对 C0、total momentum 与 EP19 B2 的 paired difference（attribution，不是 alpha 必要门）。

不得只展示 long-short，因为 A 股 short leg 未必可执行；不得只展示 active-position mean，因为低覆盖 arm 会虚增收益。

### Stage 20D：FIP incremental test

只有 C2、C3 或 C5 至少一个满足 historical beta-design gate，才允许 20D。FIP 固定为在形成期收益与 volatility 匹配后的
二分/三分 challenger，不另开大网格。

核心估计：

```text
incremental_FIP = E[Y | high base score, continuous drift]
                  - E[Y | high base score, discrete jump]
```

必须同时检查 candidate retention、winner retention、mean、median、ES10 和 turnover。若 FIP 只是选择更低波动样本，
而 vol-matched incremental return 消失，则归类为 `scale_explained_beta_filter`；只要 sleeve 仍满足正收益和风险预算，
不因此淘汰，但不能声称 FIP 提供 incremental alpha。

### Stage 20E：Low Vol 与 MA 组合风险层

只有一个 long-only sleeve 在 20C 成立后，才测试：

```text
E0 = frozen sleeve buy-and-hold monthly rebalance
E1 = sleeve with frozen volatility budget
E2 = sleeve-index prior-close vs MA20 timing
```

20E 的 primary utility 是 net mean / ES10 / drawdown / turnover 的联合变化。若风险改善但 full-capital mean 不增加，
结论为 `risk_overlay_supported_no_return_increment`，仍可保留为组合层研究，但不回写独立 entry edge。

### Stage 20F：CNN representation oracle

只有手工信号定义、样本和成本全部冻结后才运行。CNN 与手工信号共享同一 prediction date 和 fixed-return label，输出：

1. CNN alone；
2. hand-crafted factor alone；
3. CNN + hand-crafted factor；
4. 增量 rank IC、top-bucket return 和 net utility；
5. saliency/occlusion 对 price、volume、MA 区域的稳定性；
6. 不同 time fold 的 sign consistency。

20F 先执行 `cnn_training_support_gate`。不达标时只输出 `cnn_underpowered_not_evaluable`。只有训练支持充分且 frozen test
充分时，CNN 成立而手工信号失败才得到 `representation_gap_diagnostic`；CNN 可评价且二者都失败，才可作为关闭
daily OHLCV 静态入场主线的一部分证据。

### Stage 20G：Frozen true-forward confirmation

历史阶段完成后最多冻结两个候选。Forward 起点为：

```text
first_exchange_session_strictly_after_preoutcome_contract_freeze
```

要求：

- freeze 后形成的 decision months；
- primary 1-month label 完整；
- 同一股票跨月相关性用 instrument/block cluster 处理；
- 至少 6 个独立月份才允许 evaluability readout；
- 至少 12 个独立月份才允许 positive-beta support claim；
- 最终数量门还须由 20A 的 minimum detectable effect / power audit 冻结；
- 6–11 个月只能标为 `forward_interim_not_support`。

若约在 2026-08 完成 freeze，预计 2027 年初形成 6-month interim，2027 年中至第三季度才可能形成第一个 12-month
support readout；实际日期以每个 decision month 的 label-complete audit 为准。

若以后要把候选重新桥接到 120-session Big Winner，则另等完整 120-session path；不能用 1-month forward pass 代替。

### Stage 20H：Policy authorization（不在本计划内自动执行）

只有 20G 全部门通过后，才允许另写 policy/portfolio requirement。20H 必须是新的人类授权，不因 EP20 某张表 pass
自动产生。

---

## 6. 统计设计

### 6.1 Primary horizon 与标签

主频率固定为月度，主持有期固定为一个月。Decision 在月末最后一个可用 close 形成，项目主执行语义为下一可交易日
open 建仓、下一月预定 rebalance 的可交易 open 平仓/换仓。

辅助 horizon 只允许：

```text
5 sessions   = short diagnostic
20 sessions  = primary approximation / calendar QA
60 sessions  = persistence diagnostic
120 sessions = Big Winner bridge diagnostic
```

不得选择其中历史表现最好者作为新 primary。

### 6.2 Primary metrics

每个 sleeve 的 primary positive-beta 估计量：

```text
1. cash-inclusive full-capital net return and CI
2. net return minus frozen cash hurdle
3. positive-month rate and cumulative NAV
4. right-tail / big-winner exposure and capture
5. p10 / ES10 / max drawdown vs frozen budget
6. turnover, capacity and effective holdings
```

以下属于 secondary attribution，不是 beta pass 的必要条件：

```text
Spearman rank IC(score_t, Y_t+1)
top-bucket minus all-eligible return
top-minus-bottom return
monotonic slope across buckets
matched / regression incremental alpha
```

经济与风险联合 readout：

```text
mean / median / positive-month rate
p10 / ES10 / p90
annualized volatility / Sharpe / max drawdown
turnover / one-way cost / break-even cost
coverage / cash share / holdings N / effective N
market beta / size / volatility / liquidity / board exposures
top-month and top-instrument concentration
```

### 6.3 Scale / risk-source attribution（不是淘汰门）

必须使用三种互补方法：

1. 在 decision-date 内按 VOL60 或冻结的波动率指标分 cell，做 within-cell score sort；
2. 对 base candidate 做 volatility/size/liquidity nearest-neighbor 或 coarsened exact matching；
3. 横截面回归未来固定收益于 score、volatility、size、liquidity、market beta 和 calendar fixed effects。

三种方法输出如下来源标签：

```text
beta_source.market
beta_source.volatility
beta_source.size
beta_source.board_2025_static_proxy
beta_source.liquidity
incremental_alpha_after_attribution
```

如果 matching 后效应消失，但 absolute net return、正 exposure、左尾/回撤、成本和容量通过，则结论为
`positive_beta_supported_scale_explained`；如果 matching 后仍有增量，则升级描述为
`positive_beta_supported_with_incremental_alpha`。只有来源暴露导致冻结风险预算或容量失败，才淘汰 sleeve。

### 6.4 置信区间与相关性

- 月度组合收益使用 Newey–West，lag 在 requirement 中按 holding overlap 冻结；
- 股票级差分使用 decision-month block × instrument cluster bootstrap；
- 同一 decision month 的全截面不能被当作独立时间证据；
- overlapping holding portfolios 必须按论文公式构造并正确调整相关性；
- 报告 point estimate、95% CI、effective months 和 effective holdings，不只报告 t 值。
- 所有 2017–2026-05 历史 CI 都标 `design_only_not_support`；统计显著性不能消除 topic-level outcome consumption。

### 6.5 多重检验

Project primary family 只包含两个预注册候选：

```text
F_primary = {raw_TrendPV_project_adaptation,
             market_size_EP19_2025_board_proxy_residual_adaptation}
```

Market-only residual、Total Momentum、Low Vol 和 EP19 B2 是冻结 comparator。Paper-exact arms 只回答 replication，
不得升级失败的 project primary；project adaptation 也不得升级 exact claim。FIP 是有序增量检验，CNN 是独立 oracle
family。Primary family 使用 Holm correction。所有运行过的窗口、定义、修复版都登记，不能把失败 arms 从 family 中删除。

### 6.6 成本与容量

20A 必须基于本项目已有 execution/cost 证据冻结：

- commission、stamp duty、transfer fee；
- spread/slippage floor；
- next-open limit/suspension 无法成交；
- ADV participation cap；
- 最小持仓数与单名权重 cap；
- value/equal weight 的容量差异。

每张 gross 表旁必须有相同口径 net 表。若只在 gross 成立，结论为 `gross_only_not_economic`。

---

## 7. 冻结门与决策语义

数值 effect floors 必须在 20A 根据成本、目标容量和 minimum economically meaningful return 冻结，不能从 20B
历史结果倒推。下列逻辑门先行冻结。

### 7.1 Paper replication gate

用于回答实现是否忠于论文，不是正 beta project candidate 的先决门：

```text
formula_lineage_complete
warmup_and_timing_exact
paper-universe coverage adequate
expected sort direction reproduced
no single month/instrument dominance
```

若数据不足，状态为 `exact_replication_not_evaluable_data_gap`。Adaptation 可以按自己的 project/forward 门产生正 beta
证据，但不能替代或升级 exact replication。

### 7.2 Historical beta-design gate

TrendPV/residual 至少需要：

```text
cash-inclusive net full-capital point estimate above frozen cash hurdle
right-tail / winner exposure positive
left-tail and drawdown within frozen design budget
turnover and coverage mechanically evaluable
effect present in more than one time fold
```

Scale-matched lift 只记录 attribution，不决定本门。这只是允许冻结候选等待 forward 的 design gate，不是 support claim。

### 7.3 Economic gate

```text
net mean return exceeds frozen cash/economic hurdle
break-even one-way cost exceeds implementation cost by frozen margin
cash-inclusive full-capital result passes
turnover and ADV capacity pass
effective holdings and concentration pass
```

只在 active positions 或 long-short 中成立，不通过 long-only/full-capital gate。

### 7.4 True-forward gate

```text
forward support floor met
primary cash-inclusive net return CI lower bound above frozen beta floor
direction holds in both early/late forward blocks when evaluable
right-tail / winner exposure gate passes
left-tail budget passes
scale/risk-source attribution is complete and disclosed
no outcome-access or immutable-bundle violation
```

Validation/stress 只能 veto，不能补足 forward support。

### 7.5 Big Winner bridge gate

这是 secondary claim。只有 fixed-return candidate 已通过，才观察：

- `MFE_120 >= 0.50 / 1.00` capture；
- MAE20/60、ES10；
- first `+50%` vs first `-20%` hit；
- 与 EP19 B2 的 candidate overlap；
- 右尾来源由 market/volatility/size/board/liquidity 中哪些暴露解释。

即使 Big Winner bridge 失败，只要 fixed-return positive beta 成立，候选仍可保留；反之 Big Winner enrichment 不能挽救
成本后固定收益或左尾预算失败。

---

## 8. 预注册 terminal states

```text
ep20a_data_contract_not_ready
    -> project adaptation 或 forward beta test 所需的 OHLCV/execution lineage 不足；停止 outcome run。

exact_replication_not_evaluable_data_gap
    -> 宽截面 PIT market-cap/E-P/history 不足；只能做 adaptation，不得声称复制论文。

historical_design_only_not_support
    -> 2017–2026-05 结果无论多强都只用于设计和冻结候选，不能作 support。

paper_signal_not_locally_reproduced
    -> TrendPV / residual momentum 在 paper semantics 下均无预期方向；记录 paper diagnostic 失败。

factor_replication_only_no_long_only_entry_path
    -> long-short 成立，long-only/full-capital 正 beta 不成立；保留资产定价证据，关闭该 sleeve。

gross_only_not_economic
    -> gross 通过但成本后失败；不进入 forward。

positive_beta_supported_scale_explained
    -> matching 后 alpha 消失，但成本后正收益、正 exposure、左尾/回撤和容量通过；这是合格 beta，不是失败态。

positive_beta_supported_with_incremental_alpha
    -> 正 beta 全部门通过，且 matching/regression 后仍有增量；作为更强证据标签，不是必要条件。

scale_exposure_unholdable_risk_budget
    -> 正 exposure 依赖的 scale 同时使左尾、回撤、成本或容量超预算；不可持有，停止该 sleeve。

risk_overlay_supported_no_return_increment
    -> Low Vol/MA 改善风险但不增加 full-capital mean；只保留风险层角色。

fip_no_incremental_directionality
    -> FIP 不能在匹配 PRET/volatility 后增加收益；关闭 FIP 分支。

representation_gap_diagnostic
    -> CNN 有 OOS 增量而手工因子失败；允许新表征研究，不授权策略。

cnn_underpowered_not_evaluable
    -> 训练跨度、regimes、样本或 frozen test 不足；不评价 CNN，也不能用其失败关闭 OHLCV 主线。

daily_ohlcv_directional_information_not_supported
    -> 手工因子失败，且 CNN training-support/forward gates 均可评价后仍失败；才允许关闭日频 OHLCV 静态入场主线。

forward_interim_not_support
    -> 只有 6–11 个完整 forward months；只报告，不作 support。

deployable_positive_beta_candidate_supported
    -> fixed-return、positive exposure、risk budget、economic、stability、concentration、true-forward 全部通过；
       允许人工发起新的 policy/portfolio requirement。
```

每个 terminal state 都必须是可复算的布尔逻辑，不能用叙事替代。

---

## 9. Requirement 路线图

### 20A：论文血缘、数据与复制契约

建议文件：

```text
requirement_20a_paper_lineage_data_and_replication_contract.md
```

只做 preoutcome 审计、backfill 决策、formula registry 和 freeze bundle。它是当前唯一授权生成的 requirement。

### 20B：TrendPV 与 Residual Momentum 历史设计/复制诊断

```text
requirement_20b_trendpv_residual_momentum_design_and_replication_diagnostic.md
```

只有 20A 获人工批准后生成；是否允许使用“exact replication”由 go/no-go 表决定。

### 20C：可执行 long-only 正 Beta 桥接

```text
requirement_20c_executable_long_only_positive_beta_bridge.md
```

历史 design-only；固定 full-capital、next-open、成本和风险预算。Scale matching 只作 attribution。

### 20D：FIP 连续信息增量

```text
requirement_20d_fip_continuous_information_incremental_test.md
```

只有 20C 至少一个候选满足 historical beta-design gate 才生成。

### 20E：组合风险覆盖层

```text
requirement_20e_low_vol_ma20_portfolio_risk_overlay.md
```

不回写独立 entry edge。

### 20F：OHLCV CNN 表征上限

```text
requirement_20f_ohlcv_image_cnn_representation_oracle.md
```

共享 frozen panel，只诊断 representation gap。

### 20G：真实前向验证

```text
requirement_20g_frozen_positive_beta_true_forward_validation.md
```

只有历史阶段冻结候选后生成；不得提前读取未冻结 forward outcome。

---

## 10. 最小 publishable artifacts

```text
paper_source_registry.csv
paper_formula_registry.csv
paper_to_local_field_mapping.csv
ep20a_data_replication_go_no_go.csv
factor_feature_lineage_audit.csv
pit_fundamental_availability_audit.csv
pit_industry_membership_availability_audit.csv
ep19_2025_static_board_proxy_audit.csv
warmup_and_monthly_support_audit.csv
paper_vs_project_universe_overlap.csv
return_semantics_audit.csv
preoutcome_access_log.csv
freeze_bundle_manifest.json
historical_replication_role_audit.csv
factor_portfolio_return_readout.csv
long_only_full_capital_return_readout.csv
positive_beta_sleeve_utility_readout.csv
volatility_matched_directionality_readout.csv
scale_and_risk_source_attribution_readout.csv
factor_exposure_and_concentration_readout.csv
turnover_cost_capacity_readout.csv
fip_incremental_readout.csv
portfolio_overlay_readout.csv
cnn_representation_oracle_readout.csv
barrier_first_hit_ordering_readout.csv
forward_evaluability_preflight.csv
episode_20_positive_beta_research_report.md
output_hashes.json
```

每个表必须包含：`sample_role`、`universe_id`、`return_semantics`、`arm_id`、`decision_date` 或汇总粒度、eligible
denominator、cash treatment、cost version、`industry_semantics`、`beta_or_alpha_claim`、code/config/data hash。

---

## 11. 质量控制与反泄漏清单

### 11.1 PIT/timing

- 所有 signal 只使用 decision close 以前可得的数据；
- accounting field 使用公开日期/有效日期，而非报告期末直接回填；
- exact historical industry membership 必须有 effective-from/to；
- EP19 2025 board proxy 在 2025 年前只能进入 `design_only_non_pit_proxy` 产物；forward 使用时必须保持 2025 snapshot
  不变，并明确它是 multi-label concept-board proxy；
- qfq adjustment 不能利用未来 corporate action 泄漏信号；
- next-open execution 与 limit/suspension 状态逐行审计；
- 当月断点只能用当月 eligible cross-section。

### 11.2 论文忠实度

- exact 与 adapted 产物使用不同 `replication_role`；
- adaptation 可以产生 project positive-beta evidence，但永远不能升级 exact replication claim；
- Option B 下所有论文复制结论固定为 `not_claimed`；
- 未满足 warm-up 的行不可进入 exact；
- 不把 paper long-short 结果改写为 long-only；
- 不把 paper U.S. evidence 改写为 China prior；
- 不把作者 working paper 的一组统计与 version-of-record 另一口径混用；
- 每个公开数字标明 sample、weighting、holding period 和 gross/net。

### 11.3 统计与选择

- 在任何 outcome run 前冻结 arms 与主指标；
- 保留所有失败 arms；
- primary family 做 Holm correction；
- 不从多个 horizon、bucket、cost、winsorization 中择优；
- robustness/validation 只 veto；
- 任何 post-hoc 发现都必须标 `exploratory_not_support`。
- 所有 freeze 前历史结果必须标 `design_contaminated_historical`；只有 post-freeze forward 可以形成 support。

### 11.4 工程复现

- staged immutable hash bundles；
- 输入/中间表/输出 schema contract；
- unique keys、row counts、coverage reconciliation；
- deterministic seeds；
- 一键从 frozen inputs 重建 publishable tables；
- report 数字全部由 machine-readable artifact 生成或逐项 hash 对账。

---

## 12. 完整论文材料与引用清单

以下链接是 EP20 requirement 应优先使用的 version-of-record、完整正文、附录或代码入口。

### 12.1 TrendPV / 中国趋势因子

1. Liu, Yang; Liu, Yang; Zhou, Guofu; Zhu, Yingzi. 2024. “Trend Factor in China: The Role of Large
   Individual Trading.” *The Review of Asset Pricing Studies* 14(2): 348–380.
   DOI: [`10.1093/rapstu/raae003`](https://doi.org/10.1093/rapstu/raae003).
   [Oxford version of record](https://academic.oup.com/raps/article-abstract/14/2/348/7590854).
2. Liu, Yang; Liu, Yang; Zhou, Guofu; Zhu, Yingzi. “Trend Factor in China: The Role of Large Individual
   Trading,” full working paper with method and appendix.
   [AUT/ACFR full PDF](https://acfr.aut.ac.nz/__data/assets/pdf_file/0014/324113/Y-Liu-New-TrendChina_12_1_WithAppendix.pdf).
3. Authors’ internet appendix.
   [TrendChina Appendix PDF](https://guofuzhou.github.io/TrendChina_Appendix.pdf).

使用范围：多期限 price/volume signal、cross-sectional coefficient forecasting、factor sorts、停牌/成交量处理、
成本与 additional tests。若版本公式有差异，以 version-of-record/appendix 为准，并在 registry 记录差异。

### 12.2 Residual Momentum

1. Blitz, David; Huij, Joop; Martens, Martin. 2011. “Residual Momentum.” *Journal of Empirical Finance*
   18(3): 506–521. DOI: [`10.1016/j.jempfin.2011.01.003`](https://doi.org/10.1016/j.jempfin.2011.01.003).
   [Elsevier version of record](https://www.sciencedirect.com/science/article/pii/S0927539811000041).
2. Blitz, David; Huij, Joop; Martens, Martin. 2011. “Residual Momentum,” accepted/full paper.
   [Erasmus University Repository PDF](https://repub.eur.nl/pub/22252/ResidualMomentum-2011.pdf)；
   [repository record](https://repub.eur.nl/pub/22252).
3. Jansen, Maarten; Swinkels, Laurens; Zhou, Weili. 2021. “Anomalies in the China A-share Market.”
   *Pacific-Basin Finance Journal* 68: 101607.
   DOI: [`10.1016/j.pacfin.2021.101607`](https://doi.org/10.1016/j.pacfin.2021.101607).
   [Open-access version of record](https://www.sciencedirect.com/science/article/pii/S0927538X21001141)；
   [Erasmus full PDF](https://pure.eur.nl/ws/files/58642799/Anomalies_in_the_China_A_share_market.pdf).
4. Liu, Jianan; Stambaugh, Robert F.; Yuan, Yu. 2019. “Size and Value in China.”
   *Journal of Financial Economics* 134(1): 48–69.
   DOI: [`10.1016/j.jfineco.2019.03.008`](https://doi.org/10.1016/j.jfineco.2019.03.008).
   [Elsevier issue/version-of-record entry](https://www.sciencedirect.com/journal/journal-of-financial-economics/vol/134/issue/1)；
   [Wharton full PDF](https://faculty.wharton.upenn.edu/wp-content/uploads/2018/03/Size-and-Value-in-China.pdf)；
   [online appendix](https://finance.wharton.upenn.edu/~stambaug/size_value_china_appendix_2_rev.pdf)；
   [authors' factor data entry](https://finance.wharton.upenn.edu/~stambaug/).

使用范围：36-month factor regression、12-1 residual score、standardization、holding periods、A 股本地外部证据、
China market/size/E/P value factor、size/industry robustness 与 equal/value-weighted 区别。

### 12.3 Frog in the Pan

1. Da, Zhi; Gurun, Umit G.; Warachka, Mitch. 2014. “Frog in the Pan: Continuous Information and Momentum.”
   *The Review of Financial Studies* 27(7): 2171–2218.
   DOI: [`10.1093/rfs/hhu003`](https://doi.org/10.1093/rfs/hhu003).
   [Oxford version of record](https://academic.oup.com/rfs/article-abstract/27/7/2171/1578455)；
   [full working-paper PDF](https://business.uq.edu.au/sites/default/files/events/files/mitch-warachka-paper.pdf).
2. “Frog in the Pan and the market-state effect on momentum.” 2024. *Finance Research Letters* 63: 105374.
   DOI: [`10.1016/j.frl.2024.105374`](https://doi.org/10.1016/j.frl.2024.105374).
   [Open-access article](https://www.sciencedirect.com/science/article/pii/S1544612324004045).

使用范围：PRET 条件化、information discreteness、continuous vs discrete、holding-period persistence；第二篇只用于
market-state stress，不能替代原始 FIP 定义。

### 12.4 中国低波动

1. Blitz, David; Hanauer, Matthias X.; van Vliet, Pim. 2021. “The Volatility Effect in China.”
   *Journal of Asset Management* 22: 338–349.
   DOI: [`10.1057/s41260-021-00218-0`](https://doi.org/10.1057/s41260-021-00218-0).
   [Open-access full article](https://link.springer.com/article/10.1057/s41260-021-00218-0).

使用范围：A 股 universe、36-month volatility/beta sorts、value-weighted deciles、beta-neutral VOL factor、lookback/
holding robustness 与 low-vol 的组合层角色。

### 12.5 Moving-Average Portfolio Timing

1. Han, Yufeng; Yang, Ke; Zhou, Guofu. 2013. “A New Anomaly: The Cross-Sectional Profitability of
   Technical Analysis.” *Journal of Financial and Quantitative Analysis* 48(5): 1433–1461.
   DOI: [`10.1017/S0022109013000586`](https://doi.org/10.1017/S0022109013000586).
   [Cambridge version of record](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/new-anomaly-the-crosssectional-profitability-of-technical-analysis/B9E41049F2E55B4F274D46E72ECA8E29)；
   [full working-paper PDF](https://www.nowandfutures.com/large/TA_profitability_ssrn-id1656460.pdf).

使用范围：volatility portfolio construction、prior-close MA state、cash leg、transaction cost 与组合层解释。

### 12.6 OHLCV 图像 CNN

1. Jiang, Jingwen; Kelly, Bryan T.; Xiu, Dacheng. 2023. “(Re-)Imag(in)ing Price Trends.”
   *The Journal of Finance* 78(6): 3193–3249.
   DOI: [`10.1111/jofi.13268`](https://doi.org/10.1111/jofi.13268).
   [Wiley version of record, appendix and replication code](https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13268)；
   [Yale full PDF](https://economics.yale.edu/sites/default/files/2023-11/The%20Journal%20of%20Finance%20-%202023%20-%20JIANG%20-%20Re%25E2%2580%2590%20Imag%20in%20ing%20Price%20Trends_0.pdf).

使用范围：图像编码、time split、label horizons、long/short decomposition、turnover/cost 与 oracle role。

### 12.7 数据窥探与技术规则治理

1. Bajgrowicz, Pierre; Scaillet, Olivier. 2012. “Technical Trading Revisited: False Discoveries,
   Persistence Tests, and Transaction Costs.” *Journal of Financial Economics* 106(3): 473–491.
   DOI: [`10.1016/j.jfineco.2012.06.001`](https://doi.org/10.1016/j.jfineco.2012.06.001).
   [Elsevier version of record](https://www.sciencedirect.com/science/article/pii/S0304405X1200116X)；
   [University of Geneva accepted manuscript](https://archive-ouverte.unige.ch/unige:79889).

使用范围：FDR、persistence、transaction costs、technical-rule multiplicity 与禁止大网格的研究治理。

---

## 13. 对论文证据的最终解释边界

这些论文共同说明：价量历史中存在值得严格检验的方向性结构，但它们并未共同证明“任意 OHLCV 技术指标都能产生
A 股 long-only 正收益”。它们的证据对象不同：

```text
TrendPV        = A 股 price-volume cross-sectional factor
Residual MOM   = 去系统因子后的 momentum ranking
FIP            = 在相同 cumulative return 下的信息到达形态
Low Vol        = 风险与收益截面的强基准/风险层
MA timing      = 波动率组合层的时间序列 risk overlay
CNN            = OHLCV 表征上限与非线性 oracle
FDR paper      = 防止把大量规则中的幸运赢家当成规律
```

EP20 的贡献不是再次证明某篇论文在其原样本中的数字，而是建立一条不混淆证据角色的链：

```text
paper formula fidelity
    -> exact replication diagnostic when data permits
    -> paper-grounded project adaptation
    -> executable long-only positive-beta utility
    -> disclosed scale/risk-source attribution
    -> frozen true-forward confirmation
```

若手工信号失败，且 CNN 的 training-support 与 frozen-test 样本充分后仍失败，才可接受
`daily_ohlcv_directional_information_not_supported`。若 CNN underpowered，则本 Episode 对 OHLCV 表征上限保持不判定。
若只有 long-short 因子成立，应把它留在资产定价/组合构造层，而不是勉强称为 sleeve。只有真实 forward 中成本后、
全资金固定收益、正 exposure 与风险预算全部通过，才允许开启下一阶段 policy 研究；scale matching 后是否有 alpha
只改变证据标签，不决定正 beta 的生死。
