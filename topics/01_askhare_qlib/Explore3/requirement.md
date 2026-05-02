# Explore3 需求说明：EMA 趋势状态规则策略验证

## 1. 背景

`Explore3/ideas.md` 提出的核心方向不是再做一轮 `Alpha360 + LightGBM` 参数搜索，也不是把 `EMA`、`RSI`、`MACD`、`ADX`、布林带和成交量简单堆成多指标共振系统。

本轮 Explore3 要验证的是一套规则化趋势交易框架：

```text
市场状态决定能不能做；
行业 / 主题强度决定去哪里做；
EMA 多头排列决定谁进入候选；
趋势质量评分决定谁更值得做；
突破 / 回踩触发决定什么时候做；
ATR 和结构止损决定错了亏多少；
EMA20 / ATR trailing 保护利润；
EMA60 保留最后一段趋势尾部。
```

中心假设：

```text
EMA 多头排列不是买入信号，而是趋势候选状态。
真正的交易决策应由市场环境、行业 / 主题强度、趋势质量、入场位置和风险收益比共同决定。
```

## 2. Explore3 边界

Explore3 是独立实验，不依赖 Explore2 的配置、脚本、输出和中间产物。

要求：

- `Explore3` 下必须有自己的 `configs`、`scripts`、`data`、`outputs` 和 `reports` 目录。
- Explore3 可以参考 Explore2 的结论作为背景，但不能直接把 Explore2 的文件作为运行输入。
- 股票日线行情直接复用 Explore1 已缓存数据，避免逐只股票重新下载；Explore3 必须记录复用来源、覆盖范围和校验结果。
- 因为复用 Explore1 Qlib provider，Explore3 允许沿用 provider 内已有 market 名称 `mcap500_mainboard_20251231` 和对应 instrument 文件；除此之外，Explore3 的配置、信号、交易明细、回测结果和报告都必须使用 Explore3 自己的路径与命名。
- Explore3 的最终报告不得把 Explore2 的结果当作本轮实验结果。

本阶段只整理需求，不直接实现代码、不运行实验。

## 3. 研究问题

本轮要回答：

```text
在大市值、高流动性 A 股股票池中，基于 EMA 趋势状态的规则策略，
是否能通过市场环境过滤、行业 / 主题相对强度、趋势质量评分和分层退出，
获得比单纯 EMA 多头策略更低磨损、更低回撤、更稳健的成本后表现？
```

重点不是追求单次最高年化收益，而是验证以下改动是否真实改善交易质量：

- 市场环境过滤是否减少震荡市假信号。
- 行业 / 主题过滤是否提升顺风交易比例。
- `trend_score` 排序是否改善候选股质量。
- 突破型和回踩型入场哪一种更适合大市值 A 股。
- ATR / 结构止损是否改善亏损分布。
- EMA20 / ATR trailing 是否减少利润回吐。
- 按风险单位建仓是否让组合回撤更可控。

## 4. 目标

第一阶段目标是跑通规则版趋势系统，并完成分层 ablation。

必须包含：

- 一个单纯 EMA 多头 baseline。
- 一个市场过滤版本。
- 一个市场过滤 + 行业 / 主题过滤版本。
- 一个加入 `trend_score` 排名的版本。
- 突破型入场版本。
- 回踩型入场版本。
- ATR / 结构止损版本。
- 分层退出版本。
- 成本前和成本后结果对比。

后续可以再引入模型版，但不属于第一阶段主目标。

## 5. 非目标

本轮第一阶段不做：

- `Alpha360 + LightGBM` 重新调参。
- 大规模机器学习模型搜索。
- 使用模型替代规则策略。
- 实盘交易接口。
- 高频或分钟级策略。
- 科创板、创业板、北交所、ST 股票的差异化涨跌停规则工程。
- 将 Explore2 的脚本和结果直接迁移为 Explore3 产物。

模型版只作为后续扩展：

```text
用模型判断某个 EMA 候选信号是否值得交易。
```

## 6. 股票池要求

股票池应服务于大市值、机构票、低操纵风险的趋势策略假设。

Explore3 第一阶段股票池固定采用 Explore1 的静态股票池定义，不重新发明股票池口径。

股票池名称：

```text
mcap500_mainboard_20251231
```

参考来源：

- Explore1 静态股票池定义。
- `Explore1/data/universe/mcap500_mainboard_20251231.csv`
- `Explore1/data/universe/qlib_mcap500_mainboard_20251231.txt`

Explore3 可以用 Explore1 的股票池文件作为定义参考，但正式运行产物必须复制或重建到 Explore3 自己的目录，例如：

```text
Explore3/data/universe/mcap500_mainboard_20251231.csv
Explore3/data/universe/qlib_mcap500_mainboard_20251231.txt
```

静态股票池定义：

- 范围：沪深主板 A 股。
- 基准日：`2025-12-31`。
- 市值条件：总市值大于 `500` 亿元人民币，即 `50,000,000,000`。
- 市值计算方式参考 Explore1：`2025-12-31` 附近未复权收盘价乘以当日前有效总股本。
- 排除：创业板、科创板、北交所、B 股、ETF、LOF、场内基金、债券、可转债、指数、ST、`*ST`、退市整理期股票。

报告必须明确：

```text
第一阶段接受使用 Explore1 的静态股票池口径；该口径存在幸存者偏差和未来函数风险，
结论应定位为 workflow、策略结构和规则有效性的探索性验证。
```

市值口径需要单独记录：

- 使用总市值。
- 数据源。
- 取值日期。
- 单位。
- 缺失或异常处理方式。

### 6.1 股票日线行情复用

为节省单只股票数据获取时间，Explore3 第一阶段不重新逐只下载股票日线行情，直接使用 Explore1 已缓存数据。

股票行情数据来源：

```text
Explore1/data/qlib/cn_data
```

可追溯缓存来源：

```text
Explore1/data/raw/akshare/day/raw
Explore1/data/raw/akshare/day/qfq
Explore1/data/interim/qlib_csv/day
```

要求：

- Explore3 的 Qlib `provider_uri` 默认指向 `Explore1/data/qlib/cn_data`。
- Explore1 缓存作为只读行情源使用，不在 Explore3 中逐只重新抓取股票 open/high/low/close/volume/money/factor。
- 股票日线字段必须匹配 Explore1 Qlib provider 的字段命名；成交额使用 `money`，不另行定义 `amount` 字段。
- Explore3 仍必须生成自己的 universe copy、target tables、regime tables、signals、trades、reports 和 manifest。
- `run_manifest.json` 必须记录 `stock_data_source: Explore1/data/qlib/cn_data`、实际覆盖区间、字段覆盖和校验结果。
- 如果 Explore1 缓存缺少股票、字段或日期，第一阶段应停止并报告缺口；不得自动逐只下载补齐，除非后续需求明确允许。
- 本节只约束股票日线行情；市场、行业、主题指数仍按第 7 节目标定义获取。

## 7. 市场、行业与主题环境

市场环境过滤是 Explore3 的第一优先级，因为趋势策略的主要磨损通常来自震荡市中的假趋势。

### 7.1 必选数据目标

Explore3 的市场、行业和主题环境只能使用本节列出的目标。实现时可以同时记录 Tushare 与 AKShare 字段，但不得自动扩展目标列表。

#### 7.1.1 市场目标

| `target_key` | 指数名称 | Tushare `ts_code` | AKShare API | AKShare `symbol` |
| --- | --- | --- | --- | --- |
| `broad_market` | 沪深300 | `000300.SH` | `stock_zh_index_hist_csindex` | `000300` |
| `mid_cap_spread` | 中证500 | `000905.SH` | `stock_zh_index_hist_csindex` | `000905` |
| `small_cap_spread` | 中证1000 | `000852.SH` | `stock_zh_index_hist_csindex` | `000852` |
| `growth_board_spread` | 创业板指 | `399006.SZ` | `index_hist_cni` | `399006` |

市场目标用途：

- `broad_market` 作为主市场状态和回测基准参考。
- `mid_cap_spread`、`small_cap_spread`、`growth_board_spread` 用于判断大小盘和成长板块风格扩散，不自动改变股票池。

#### 7.1.2 行业目标

行业目标使用以下固定 SW2021 一级行业列表：

| Tushare `ts_code` | 行业名称 |
| --- | --- |
| `801010.SI` | 农林牧渔 |
| `801030.SI` | 基础化工 |
| `801040.SI` | 钢铁 |
| `801050.SI` | 有色金属 |
| `801080.SI` | 电子 |
| `801110.SI` | 家用电器 |
| `801120.SI` | 食品饮料 |
| `801130.SI` | 纺织服饰 |
| `801140.SI` | 轻工制造 |
| `801150.SI` | 医药生物 |
| `801160.SI` | 公用事业 |
| `801170.SI` | 交通运输 |
| `801180.SI` | 房地产 |
| `801200.SI` | 商贸零售 |
| `801210.SI` | 社会服务 |
| `801230.SI` | 综合 |
| `801710.SI` | 建筑材料 |
| `801720.SI` | 建筑装饰 |
| `801730.SI` | 电力设备 |
| `801740.SI` | 国防军工 |
| `801750.SI` | 计算机 |
| `801760.SI` | 传媒 |
| `801770.SI` | 通信 |
| `801780.SI` | 银行 |
| `801790.SI` | 非银金融 |
| `801880.SI` | 汽车 |
| `801890.SI` | 机械设备 |
| `801950.SI` | 煤炭 |
| `801960.SI` | 石油石化 |
| `801970.SI` | 环保 |
| `801980.SI` | 美容护理 |


要求：

- 目标数据准备阶段不得修改行业目标定义。
- 目标数据准备阶段不得自动新增任何本列表之外的 SW2021 行业代码。
- 目标数据准备阶段不得自动删除本列表内的任何 SW2021 行业代码。
- 行业指数只用于行业环境、行业相对强度和行业分组分析，不直接扩大或缩小股票池。

#### 7.1.3 主题目标

| `target_key` | 指数名称 | Tushare `ts_code` | AKShare API | AKShare `symbol` |
| --- | --- | --- | --- | --- |
| `dividend` | 中证红利指数 | `000922.SH` | `stock_zh_index_hist_csindex` | `000922` |
| `central_soe` | 中证中央企业综合指数 | `000926.SH` | `stock_zh_index_hist_csindex` | `000926` |
| `ai` | 中证人工智能主题指数 | `930713.CSI` | `stock_zh_index_hist_csindex` | `930713` |
| `new_energy` | 中证内地新能源主题指数 | `000941.SH` | `stock_zh_index_hist_csindex` | `000941` |

主题目标用途：

- 判断红利、央企、AI、新能源等主题风格是否处于顺风状态。
- 作为市场环境和候选股分组分析的辅助维度。
- 不自动把主题指数成分加入股票池。

#### 7.1.4 数据获取与认证

Tushare 只用于获取本节列出的市场、行业和主题指数目标，不用于股票日线行情、股票池构建或个股基础数据补齐。

市场、行业和主题目标优先使用 Tushare `ts_code` 获取。AKShare API 和 `symbol` 作为备用来源和交叉校验来源。

使用 Tushare 时：

- Tushare token 定义在 topic 根目录的 `.env` 中。
- 默认环境变量名为 `TUSHARE_TOKEN`。
- 实现必须通过 `.env` 或环境变量读取 token，不得把 token 写入命令行参数、日志、CSV、报告、`run_manifest.json` 或 git 追踪文件。
- 如果 `.env` 不存在、`TUSHARE_TOKEN` 不存在或 token 无效，目标数据准备阶段应停止并报告认证缺失。
- 报告和 manifest 只能记录 `tushare_token_present: true/false`，不能记录 token 内容。

### 7.2 指数趋势过滤

候选规则：

```text
broad_market close > EMA60
broad_market EMA60 最近 10 到 20 日斜率 > 0
可选：close > EMA120
```

如果指数趋势过滤不通过：

- 停止新开仓。
- 已有仓位只执行止损、利润保护和最终退出。

### 7.3 市场宽度过滤

候选规则：

```text
股票池中 close > EMA60 的股票比例 > 50% 或 55%
股票池中 EMA20 > EMA60 的股票比例 > 40% 或 50%
```

市场宽度需要按交易日预计算，并写入 Explore3 自己的输出目录。

### 7.4 行业趋势过滤

候选规则：

```text
行业指数 close > EMA60
行业 EMA60 斜率 > 0
行业 60 日收益 > broad_market 60 日收益
可选：行业内强势股比例 > 50%
```

行业过滤的数据契约：

- 行业目标只能来自 7.1.2 中的固定列表。
- 若需要统计股票到行业的归属，必须记录行业分类来源和是否 point-in-time。
- 行业指数或行业组合收益的计算方式。
- 股票缺失行业归属时的处理方式。
- 行业环境输出必须包含行业级别状态。
- 行业内强势股比例只有在存在可复现股票行业映射时才作为硬过滤；否则第一阶段记录为缺失，不阻塞指数级行业环境验证。

### 7.5 主题趋势过滤

候选规则：

```text
主题指数 close > EMA60
主题指数 EMA60 斜率 > 0
主题 60 日收益 > broad_market 60 日收益
```

主题过滤的数据契约：

- 主题目标只能来自 7.1.3 中的固定列表。
- 第一阶段主题只作为全局主题风格状态和分组分析维度，不做个股 membership 过滤。
- 股票是否属于某主题，只有在后续提供明确、可复现的映射来源后，才允许作为个股过滤条件。
- 主题环境输出必须至少包含主题指数级别状态。

第一阶段即使没有股票到主题的映射，也必须实现主题指数状态；不得因为缺少主题 membership 映射而阻塞实验。

## 8. 个股候选状态

EMA 多头排列只负责生成候选，不直接触发买入。

候选条件：

```text
EMA20 > EMA60
EMA60 最近 10 日斜率 > 0
close > EMA60
close 距离 EMA20 不过远
过去 20 日波动率不能极端过高
过去 20 日成交额不能太低
```

追高约束候选写法：

```text
(close - EMA20) / close < 2 * ATR20 / close
```

或简化为：

```text
close / EMA20 - 1 < 5% 到 8%
```

最终阈值不能直接用 test 区间调优，应通过 train / valid 或规则先验固定。

## 9. 趋势质量评分

Explore3 不应把多个技术指标都变成硬条件。指标应进入 `trend_score`，用于候选股排序。

候选评分维度：

- EMA60 斜率。
- 60 日相对强度。
- EMA20 / EMA60 乖离。
- 成交额相对强度。
- MACD 或动量状态。
- ADX 或趋势强度。
- 过热惩罚。
- 波动率过高惩罚。

评分要求：

- 所有分量必须先做截面标准化，例如 rank、z-score 或 winsorized z-score。
- 权重必须在实验前固定，不能用 test 区间事后调参。
- 报告中需要列出每个版本使用的评分公式。
- 至少输出每日候选数、入选数、评分分布和分位数。

第一版可使用简单等权或少量手工权重，重点验证框架，不追求最优参数。

## 10. 入场规则

突破型和回踩型必须分开实现、分开统计、分开报告。

### 10.1 突破型

前置条件：

```text
市场环境 OK
行业环境 OK
主题环境作为全局风格状态记录，不作为第一阶段个股入场硬过滤
个股 EMA20 > EMA60
EMA60 斜率向上
trend_score 位于候选池前 10% 或 20%
```

触发条件：

```text
close > 过去 60 日高点
成交额 > 过去 20 日平均成交额 * 1.1 或 1.2
收盘价位于当日振幅上半区
上影线不能过长
close 距离 EMA20 不能过远
```

可选确认：

```text
突破日不立刻重仓；
加入观察池；
第 2 到第 3 天仍站在突破位上方，或回踩突破位不破，再买入。
```

### 10.2 回踩型

前置条件：

```text
EMA20 > EMA60
EMA60 上行
市场环境 OK
行业趋势向上
主题趋势作为全局风格状态记录，不作为第一阶段个股入场硬过滤
个股 trend_score 靠前
```

触发条件：

```text
价格回踩 EMA20 / EMA30 附近
不跌破 EMA60
回踩过程中缩量
重新站上 EMA20
或出现放量转强阳线
```

报告必须比较：

- 突破型交易数量。
- 回踩型交易数量。
- 各自胜率。
- 平均盈亏比。
- 平均持仓天数。
- 成本后收益。
- 最大回撤。
- 大盈利交易贡献。

## 11. 止损与仓位

### 11.1 初始止损

候选规则：

```text
突破买入：
止损 = 突破平台下沿 - 0.5 * ATR20

回踩买入：
止损 = 回踩低点 - 0.5 * ATR20

通用版本：
止损 = 入场价 - 2 * ATR20
```

实际实现时需要记录每笔交易的：

- 入场价。
- 初始止损价。
- 初始风险 `R`。
- 止损来源。
- 是否因止损退出。

### 11.2 风险单位仓位

候选规则：

```text
单笔最大亏损 = 总资金的 0.5% 到 1%
买入股数 = 单笔最大亏损 / (入场价 - 初始止损价)
```

组合约束：

```text
单票最大权重：3% 到 6%
单行业最大权重：20% 到 30%
最大持仓数量：15 到 30 只
单日最大新增仓位：10% 到 20%
```

第一版如果 Qlib 自定义 Strategy 难以一次实现全部仓位逻辑，可以先做固定权重版本作为 baseline，再单独加入风险单位仓位做 ablation。

## 12. 退出规则

退出应分层，不把 EMA60 当作唯一退出。

### 12.1 初始失败退出

```text
触发初始止损，退出。
买入后 8 到 12 个交易日仍未盈利，退出或减仓。
突破失败并跌回突破平台，退出。
```

### 12.2 盈利保护

```text
盈利 >= 1R，止损抬到成本附近。
盈利 >= 2R，使用 EMA20 / ATR trailing / 前低跟踪。
盈利 >= 3R，若价格明显远离 EMA20，可部分减仓或收紧止盈。
```

### 12.3 趋势终结

```text
剩余仓位跌破 EMA60，最终退出。
```

分批止盈不作为默认规则。若测试分批止盈，必须单独作为 ablation：

- 版本 A：不分批，只用 trailing stop。
- 版本 B：极端乖离时减仓，剩余用 trailing stop。

## 13. Qlib 落地要求

Explore3 的 Qlib 落地分三层：

```text
因子层：构造 EMA、动量、波动、成交量、相对强度等特征。
规则层：生成市场状态、行业状态、主题状态、候选状态、trend_score、入场触发。
策略层：根据持仓状态、止损、仓位和退出规则生成交易。
```

第一阶段优先使用规则版自定义 Strategy。

Qlib 数据源：

```text
provider_uri: Explore1/data/qlib/cn_data
market: mcap500_mainboard_20251231
benchmark: SH000300
```

Explore3 可以读取 Explore1 的 Qlib provider，但不得把回测、信号、交易明细或报告写入 Explore1。

要求：

- 策略必须显式处理持仓状态。
- 策略必须保存每笔交易的 entry、exit、stop、R、entry_type 和 exit_reason。
- 信号生成和成交必须避免 T 日收盘信号直接使用 T 日成交价。
- 若使用 T 日收盘生成信号，最早成交日应为 T+1。
- 回测报告必须验证 signal date、order date、deal date 的对齐。

如果使用 Qlib 表达式因子，至少需要覆盖：

- `ema20_ema60_spread`
- `ema60_slope10`
- `dist_ema20`
- `breakout60_pos`
- `ret20`
- `ret60`
- `volume_ratio20`
- `volatility20`
- `atr_proxy20`

真实 ATR、ADX、RSI 如 Qlib 表达式不方便，可以在预处理阶段计算，并作为 Explore3 自定义字段写入。

## 14. 时间周期与回测设置

Explore3 的时间周期固定参考 Explore1。

数据区间：

```text
2017-01-01 到 2026-04-30
```

训练、验证和测试区间：

```text
train: 2017-01-01 到 2022-12-31
valid: 2023-01-01 到 2024-12-31
test:  2025-01-01 到 2026-04-30
```

组合回测区间：

```text
backtest: 2025-01-01 到 2026-04-29
```

说明：

- 数据截止到 `2026-04-30`，回测结束日使用 `2026-04-29`，为下一个交易日成交和收益计算保留 calendar entry。
- 如果后续重跑时数据结束日变化，必须在 `run_manifest.json` 中记录实际数据截止日和回测截止日；默认需求口径仍以 Explore1 为准。

基础回测参数建议：

| 项目 | 候选值 |
| --- | --- |
| benchmark | `SH000300` |
| initial account | `1,000,000` 或 `10,000,000` |
| freq | `day` |
| deal_price | 优先 `open`，用于模拟 T+1 开盘成交 |
| open_cost | `0.0005` |
| close_cost | `0.0015` |
| min_cost | `5` |
| limit_threshold | `0.095` |

注意：

- 若回测区间跨越不同印花税和交易费率时期，正式报告应说明成本假设是常数近似还是分段成本。
- 如果股票池包含非主板股票，涨跌停限制不能继续简单使用主板近似。
- 数据截止到 `T` 时，回测结束日需要保留足够的下一个交易日用于成交和收益计算；Explore3 默认按 Explore1 使用 `T=2026-04-30`、回测结束日 `2026-04-29`。

## 15. 实验阶段

按以下顺序逐层增加功能：

| 阶段 | 版本 | 目的 |
| --- | --- | --- |
| 0 | 单纯 EMA 多头排列 | baseline |
| 1 | 加大盘过滤 | 验证是否减少震荡市磨损 |
| 2 | 加市场宽度过滤 | 验证是否比单指数过滤更稳 |
| 3 | 加行业过滤 + 主题状态记录 | 验证是否改善顺风交易 |
| 4 | 加 `trend_score` 排名 | 验证是否提升候选质量 |
| 5 | 拆分突破型 / 回踩型入场 | 比较两类买点 |
| 6 | 固定止损改 ATR / 结构止损 | 验证亏损分布是否改善 |
| 7 | 加 EMA20 / ATR trailing | 验证利润回吐是否下降 |
| 8 | 加风险单位仓位 | 验证回撤是否更可控 |
| 9 | 可选 meta-labeling | 判断哪些 EMA 信号值得交易 |

阶段 9 不属于第一阶段必做内容。
阶段 8 属于第二阶段增强项，不纳入第一阶段验收；第一阶段报告需要说明是否进入阶段 8。

## 16. 参数选择纪律

避免把 Explore3 变成 test 区间调参。

要求：

- 所有阈值和参数必须记录来源。
- 参数只能在 train / valid 或样本外之前的区间选择。
- 最终 test 区间只能作为最后评估使用。
- 若对 test 区间做了多轮调整，报告必须明确说明结论降级为探索性结果。

建议时间切分：

```text
train: 2017-01-01 到 2022-12-31
valid: 2023-01-01 到 2024-12-31
test:  2025-01-01 到 2026-04-30
backtest: 2025-01-01 到 2026-04-29
```

纯规则策略也应遵守同样纪律：规则和阈值先固定，再评估 test。

## 17. 评估指标

组合层面：

- 年化收益。
- 最大回撤。
- 收益回撤比。
- 超额收益。
- 超额信息比率。
- 换手率。
- 成本前收益。
- 成本后收益。
- 期末账户。

交易层面：

- 交易笔数。
- 胜率。
- 平均盈利。
- 平均亏损。
- 平均盈亏比。
- 平均持仓天数。
- 最大单笔盈利。
- 最大单笔亏损。
- 大盈利交易贡献。
- 剔除前 5 笔最大盈利后的收益。
- 平均利润回吐。
- 止损退出占比。
- 时间止损退出占比。
- EMA60 退出占比。

分组分析：

- 突破型 vs 回踩型。
- 市场过滤通过 vs 不通过。
- 行业 / 主题过滤通过 vs 不通过。
- trend_score 分位数。
- 不同市场阶段。
- 不同年份。
- 不同行业。
- 不同主题状态。

关键判断：

```text
如果成本前赚钱、成本后亏钱，主要问题可能是换手和执行。
如果成本前也不赚钱，说明信号本身没有优势，需要重做过滤和入场。
如果收益主要来自少数大盈利交易，需要验证剔除肥尾后策略是否仍有基础收益。
```

## 18. 对比基线

至少需要以下基线：

1. `broad_market`，即沪深 300。
2. 同股票池等权持有基准。
3. 单纯 EMA 多头排列策略。
4. EMA 多头 + 固定退出策略。
5. Explore3 最终规则策略。

如引用 Explore2 的 Alpha360 或 TopK 结果，只能作为背景参考，不作为 Explore3 的直接基线，除非在 Explore3 独立重跑并生成 Explore3 自己的产物。

## 19. 产物要求

Explore3 完成第一阶段后，至少应产出：

- `Explore3/requirement.md`
- `Explore3/data/targets/market_targets.csv`
- `Explore3/data/targets/industry_targets.csv`
- `Explore3/data/targets/theme_targets.csv`
- `Explore3/data/universe/...`
- `Explore3/configs/...`
- `Explore3/scripts/...`
- `Explore3/outputs/reports/data_quality_report.csv`
- `Explore3/outputs/reports/explore1_cache_coverage.csv`
- `Explore3/outputs/reports/market_regime.csv`
- `Explore3/outputs/reports/industry_regime.csv`
- `Explore3/outputs/reports/theme_regime.csv`
- `Explore3/outputs/reports/daily_candidates.csv`
- `Explore3/outputs/reports/daily_scores.csv`
- `Explore3/outputs/reports/signals.csv`
- `Explore3/outputs/reports/trend_rule_ablation_summary.csv`
- `Explore3/outputs/reports/trade_detail.csv`
- `Explore3/outputs/reports/run_manifest.json`
- `Explore3/outputs/reports/explore3_report.md`

`explore3_report.md` 必须明确区分：

```text
链路是否跑通；
是否严格使用 Explore1 静态股票池口径；
规则信号是否有成本前优势；
成本后是否仍有效；
改善来自市场过滤、行业 / 主题过滤、入场、退出还是仓位；
结果是否依赖少数肥尾交易；
是否存在未来函数或幸存者偏差。
```

## 20. 第一阶段验收标准

第一阶段完成标准：

- Explore3 产物全部落在 `Explore3` 目录下。
- 市场、行业、主题目标与第 7.1 节完全一致。
- Qlib provider 允许复用 `Explore1/data/qlib/cn_data` 和 provider 内的 `mcap500_mainboard_20251231` market；除只读 provider 输入外，配置、信号、交易明细、回测和报告不得写入 Explore1。
- 能独立复现规则策略回测。
- 至少完成阶段 0 到阶段 7 的 ablation。
- 突破型和回踩型结果分开统计。
- 输出交易明细，并包含 entry_type、exit_reason、initial_stop、R。
- 报告同时展示成本前和成本后结果。
- 报告明确说明股票池是否存在静态池偏差。
- 报告给出下一步是否值得进入模型版 meta-labeling 的判断。
