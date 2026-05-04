# Explore9 需求说明：大涨股早期结构的广度探索

## 1. 背景

Explore8 的 PIT 年度大涨股画像已经把问题从“继续调规则”推进到“理解真实大涨股结构”。

当前最重要的证据包括：

- PIT universe 中并不缺少年度大涨股：2017-2024 共发现 `734` 个年内大涨 episode。
- 2019、2020、2021、2024 是高机会年份；2024 有 `161` 个大涨股票年，占 PIT universe 的 `57.71%`。
- 当前规则族整体捕获能力很弱：Explore8 的规则错配中，`no_signal` 占 `55.22%`，`late_signal` 占 `17.97%`，两者合计 `73.19%`。
- `first_breakout_signal` 缺失率 `57.63%`，出现时平均已经涨过约 `50%`，更像后期确认，不像早期发现。
- `first_ema60_reclaim` 更早，平均低点后 `7.61` 个交易日出现，但 trend score 平均分位只有 `50.53%`，说明早期修复阶段不一定满足强趋势筛选。
- pullback 系列 `no_signal` 在 `71.93%` 到 `80.38%` 之间，严格版几乎抓不到大涨股。
- `early_exit` 虽然占比不如 `no_signal` 高，但平均损失可达 `46-58%`，说明已有信号也没有为大 winner 的高波动和长持有设计。
- 年度切片会切碎完整主升段：`734` 个年内事件中有 `507` 个被自然年边界截断，跨年审计发现 `307` 个连续主升事件。

因此 Explore9 不应继续围绕 `EMA / breakout / pullback` 这些既有形态做局部调参。Explore9 的主要目标是：

```text
基于 PIT universe 和 Explore8 的大涨股画像结论，
对大涨股早期可观察结构进行尽可能广的探索，
从价格、成交、相对强度、波动、行业、市场、形态片段、生命周期等多个维度寻找候选线索，
形成下一阶段可验证的信号假设，而不是直接产出最终策略。
```

Explore9 是 broad discovery 阶段；formal hypothesis generation 只作为 P1 记录，等待 P0 完成后再细化。Explore9 不是策略冻结阶段。

## 2. 核心问题

Explore9 要回答的问题不是“哪一个 EMA 参数最好”，而是：

```text
在 T 日完全可观察的信息下，
未来会成为 50% / 100% / 200% 大涨股的股票，
在早期、中期、确认期分别呈现出哪些稳定、可解释、可复现的结构？
这些结构是否能跨年份、跨行业、跨市场状态保持一定覆盖率和提前量？
```

必须拆成四个子问题：

1. **早期发现**：在大涨完成前，哪些 T 日可观察特征能提前识别潜在 winner？
2. **中期确认**：当股票已经上涨 20% / 30% 后，哪些条件说明它仍可能继续扩展，而不是普通反弹？
3. **持有延展**：哪些状态支持从普通盈利交易切换为 winner hold，而不是被 time stop / stop loss 过早退出？
4. **环境分层**：市场和行业状态应如何影响确认强度、仓位或退出容忍度，而不是作为硬过滤直接屏蔽？

## 3. 与 Explore8 的关系

Explore9 可以读取 Explore8 的报告和画像输出作为背景，但必须独立计算。

允许读取为 `background_reference`：

- `Explore8/outputs/reports/explore8_big_winner_profile_report.md`
- `Explore8/expand_requirement.md`
- `Explore8/requirement.md`

允许读取为 `schema_reference / audit_reference`：

- `Explore8/outputs/reports/yearly_big_winner_episodes.csv`
- `Explore8/outputs/reports/yearly_big_winner_anchor_profile.csv`
- `Explore8/outputs/reports/yearly_big_winner_cross_year_audit.csv`
- `Explore8/outputs/reports/yearly_big_winner_rule_miss_attribution.csv`
- `Explore8/outputs/reports/yearly_big_winner_year_summary.csv`
- `Explore8/outputs/reports/yearly_big_winner_industry_summary.csv`
- `Explore8/outputs/reports/yearly_big_winner_regime_summary.csv`

约束：

- Explore8 的画像 CSV 可以用于 schema 对照和结果一致性审计，但不得直接作为 Explore9 的训练标签、候选信号、排序分数或策略选择输入。
- Explore9 必须从 PIT universe 和 provider 行情重新生成 stock-day labels、episode labels、primitive features、candidate families 和报告。
- 若实现中读取 Explore8 CSV，manifest 必须记录其用途为 `audit_reference_only`，并记录：

```text
explore8_profile_csv_used_for_label = false
explore8_profile_csv_used_for_signal = false
explore8_profile_csv_used_for_selection = false
```

禁止以下行为：

- 将 Explore3-Explore8 的 `trade_detail`、`portfolio_daily`、`signals`、`daily_candidates`、`model_predictions`、`year_metrics` 或任何历史交易结果 CSV 作为计算输入。
- 将 Explore8 的 `low_date` 当作可交易启动点。
- 将 Explore8 中相对最好的 `ema_state_baseline` 直接升级成 Explore9 主线。
- 将 `breakout`、`EMA60 reclaim`、`pullback` 作为唯一探索空间。
- 使用 2025-2026 observed reference 选择特征、阈值、模型或 candidate family。

## 4. 数据边界

Explore9 必须沿用 PIT 数据链路。

默认输入：

```text
universe_membership: Explore7/data/universe/pit_mcap500_mainboard_daily.csv
qlib_instruments: Explore7/data/universe/qlib_pit_mcap500_mainboard.txt
industry_membership: Explore7/data/targets/pit_industry_membership.csv
market_targets: Explore7/data/targets/market_targets.csv
industry_targets: Explore7/data/targets/industry_targets.csv
target_history: Explore7/data/targets/target_history.csv
provider_uri: Explore7/data/qlib/cn_data_pit
fallback_provider_uri: Explore1/data/qlib/cn_data
benchmark: SH000300
required_fields: open, high, low, close, volume, money, factor
price_adjustment_mode: provider_ohlc_already_adjusted
```

硬约束：

- 每个 `date + instrument` 样本必须显式 join PIT membership。
- 不在当日 PIT membership 的股票不得作为训练样本、候选样本或回放样本。
- 行业归属必须按 `date + instrument` 的 PIT industry membership join；缺失行业记录为 `UNKNOWN`。
- 行情必须具备 `open/high/low/close/volume/money/factor`。成交额字段使用 `money`，不得改用 `amount`。
- provider 覆盖不足时，必须输出 coverage audit，并在报告中降级结论权限。
- OHLC 默认认为已调整，不得再乘一次 `factor`。

所有 Explore9 配置、脚本、缓存、输出、报告和 manifest 必须落在 `Explore9/` 下。

## 5. 时间范围与选择纪律

默认时间范围：

```text
data_start: 2017-01-01
research_start: 2017-01-01
research_end: 2024-12-31
observed_reference_start: 2025-01-01
observed_reference_end: 2026-04-30
```

研究纪律：

- 2017-2024 是主研究期。
- 2025-2026 只能作为 observed reference，不得用于特征选择、阈值选择、模型选择或候选 family 选择。
- 若需要训练/验证，必须采用时间推进的 walk-forward 或 expanding train 方式，不得随机切分 stock-day rows。
- 所有 T 日特征只能使用 T 日或 T 日以前可观察数据。
- 所有未来收益标签只用于训练、画像、排序评估，不得作为 T 日特征。

Explore9 第一版默认不要求形成可交易策略，但如果产生候选信号假设，必须按 distinct calendar year 输出，不得只报告 pooled 全样本结果。

### 5.1 特征 warmup 与 history eligibility

P0 原语包含 `ret120`、`low240`、rolling rank、趋势年龄等长窗口特征，因此必须显式处理 history eligibility。

每个 primitive 必须在 `primitive_feature_dictionary.csv` 中记录：

```text
feature_name
feature_family
min_history_trading_days
lookback_window
requires_benchmark_history
requires_industry_history
feature_eligible_rule
warmup_partial_year_handling
```

样本级必须记录：

```text
feature_eligible
feature_missing_reason
available_history_trading_days
first_feature_eligible_date
```

规则：

- 某个 primitive 的 `available_history_trading_days < min_history_trading_days` 时，该 primitive 对该样本必须记为 `feature_eligible = false`。
- `feature_eligible = false` 的样本不得进入该 primitive 的 lift 分母。
- 新上市股票、PIT membership 新进入股票和 2017 年 warmup 不足样本必须保留在 coverage / eligibility audit 中，不得静默删除。
- 2017 年若因为 provider 从 2017-01-01 开始导致长窗口不足，必须标记 `warmup_partial_year = true`，并在报告中说明哪些 primitive 的 2017 结论受限。
- feature warmup 缺失不是 provider coverage miss，必须单独进入 `primitive_feature_coverage.csv`。

## 6. 标签体系

Explore9 必须重新生成标签，不能直接复用 Explore8 episode CSV 作为标签源。

### 6.1 Stock-day 前向标签

样本单位默认是 `date + instrument` 的 stock-day snapshot。

对每个 T 日样本，至少生成以下前向标签：

```text
future_max_high_gain_20d
future_max_high_gain_60d
future_max_high_gain_120d
future_max_high_gain_240d
future_max_close_gain_20d
future_max_close_gain_60d
future_max_close_gain_120d
future_max_close_gain_240d
future_max_drawdown_before_gain_60d
future_max_drawdown_before_gain_120d
future_max_drawdown_in_horizon_60d
future_max_drawdown_in_horizon_120d
future_time_to_50pct_high_gain
future_time_to_100pct_high_gain
future_time_to_50pct_close_gain
future_time_to_100pct_close_gain
```

二分类标签至少包括：

```text
is_future_50pct_high_60d
is_future_50pct_high_120d
is_future_50pct_high_240d
is_future_100pct_high_240d
is_future_50pct_close_120d
is_future_50pct_close_240d
```

标签说明：

- `high_gain` 和 `close_gain` 必须分开。
- 盘中达到 50% 但收盘未确认的样本必须单独标记。
- 如果 T 日距离研究期末不足前向窗口，必须记录 `label_horizon_truncated = true`，不得静默当作 negative。
- 如果前向窗口延伸到 2025-2026，必须记录 `observed_reference_overlap = true`，不得用于 2017-2024 主选择。
- 如果前向窗口内没有达到目标涨幅，`future_time_to_*` 必须为 null，不能填 0 或窗口长度；对应 `is_future_*` 为 false。
- `future_max_drawdown_before_gain_*` 只对已经达到目标涨幅的样本计算；未达标样本必须为 null。
- `future_max_drawdown_in_horizon_*` 对所有 horizon-valid 样本计算，用于描述未达标样本的普通风险。
- 所有 null / truncation / observed overlap 都必须进入 `label_coverage_audit.csv`。

#### 6.1.1 主 lift 的 label eligibility

P0 主 lift 只能使用同时满足以下条件的样本：

```text
label_horizon_truncated = false
observed_reference_overlap = false
feature_eligible = true
pit_member = true
provider_required_fields_ok = true
```

不满足上述条件的样本：

- 可以进入 `label_coverage_audit.csv`、`primitive_feature_coverage.csv` 和报告覆盖说明。
- 不得进入 P0 主 lift 的分子或分母。
- 不得作为 preliminary discovery lead 的正负样本。

如果某个 horizon 因为 2024 样本延伸到 2025-2026 而大量 `observed_reference_overlap = true`，必须单独报告该 horizon 的可用样本比例。P0 主结论不得依赖 observed reference overlap 样本。

#### 6.1.2 重复样本与 episode 去重

stock-day 标签会让同一只未来大涨股票在连续多个 T 日都成为 positive。为避免一个 winner 被重复计数导致 lift 虚高，每个 primitive 和 preliminary discovery lead 必须同时报告以下口径：

```text
stock_day_count
unique_instrument_count
unique_instrument_year_count
unique_episode_count
positive_stock_day_count
positive_unique_instrument_count
positive_unique_instrument_year_count
positive_unique_episode_count
```

评价要求：

- 主 precision / lift 以 stock-day 为基础，但必须同时输出 `episode_dedup_lift` 和 `instrument_year_dedup_lift`。
- 每个 lead 必须报告样本是否被少数股票或少数 episode 主导。
- 若 `positive_stock_day_count` 很高但 `positive_unique_episode_count` 很低，必须标记为 `duplicate_positive_risk = true`。
- 年度稳定性必须至少按 `instrument_year` 或 `episode` 去重后再复核一次。

### 6.2 Episode 生命周期标签

Explore9 仍需生成 episode 级标签，但目的不是复刻 Explore8，而是支持生命周期研究。

必须输出两套 stage，避免把事后生命周期误用成 T 日可交易状态。

#### 6.2.1 `retrospective_lifecycle_stage`

该字段是事后画像标签，可以使用完整 episode 的 `low_date`、`high_date`、`future max gain` 和高点后状态。

默认枚举：

- `pre_repair`
- `early_repair`
- `confirmed_20pct`
- `confirmed_30pct`
- `trend_extension`
- `late_trend`
- `post_peak`

使用边界：

- 只能用于画像、报告、审计和生命周期统计。
- 不得作为 T 日训练特征。
- 不得作为 T 日候选信号。
- 不得用于 hypothesis selection。
- 不得用于任何可交易规则公式。

#### 6.2.2 `observable_state_stage`

该字段必须只由 T 日或 T 日以前可观察数据定义，用于 stock-day 分组、primitive lift 和候选线索描述。

默认枚举：

- `observable_downtrend`
- `observable_base_building`
- `observable_repairing`
- `observable_relative_strength_leading`
- `observable_20pct_from_recent_low`
- `observable_30pct_from_recent_low`
- `observable_trend_extension`
- `observable_late_acceleration_risk`

约束：

- `recent_low` 只能来自 T 日以前 rolling window，例如 `low20/low60/low120/low240`，不得使用未来才知道的 episode `low_date`。
- `observable_20pct_from_recent_low` 和 `observable_30pct_from_recent_low` 必须基于 T 日以前 rolling low 到 T 日 close/high 的已发生涨幅。
- `observable_late_acceleration_risk` 只能用 T 日以前的已发生涨幅、成交、波动和趋势年龄定义，不能用未来高点后回落确认。
- 如果某个 stage 无法保证 T 日可观察，必须归入 `retrospective_lifecycle_stage`，不得进入 `observable_state_stage`。

关键约束：

- `low_date` 只能作为事后生命周期标签。
- 任何可交易候选必须锚定到 T 日可观察状态，不得锚定到未来才知道的最低点。
- 训练、candidate family、hypothesis formula 只能使用 `observable_state_stage`，不能使用 `retrospective_lifecycle_stage`。

## 7. 探索范围

Explore9 的核心要求是广度探索。实现不得只围绕 EMA、breakout、pullback 三类形态。

以下 10 类信号原语是完整探索地图，不等于 P0 第一版必须把每一类都深挖完成。P0 第一版必须建立完整 feature family registry，并实现一批足够覆盖不同方向的 P0 原语；P1 / P2 仅记录为后续路线，等待 P0 完成后再细化和实现。

### 7.1 价格状态原语

包括但不限于：

- 多周期收益：`ret3/5/10/20/60/120`。
- 多周期高低点位置：距离 `high20/high60/high120`、距离 `low20/low60/low120`。
- 新高 / 新低 / 近新高状态。
- 底部修复幅度。
- 阶段涨幅后的横盘。
- 大阳线、长上影、长下影、实体占比。
- gap up / gap down。
- 涨停、接近涨停、连续涨停或涨停后整理。

### 7.2 相对强度原语

包括但不限于：

- 相对沪深300收益：`relative_ret20/60/120_vs_benchmark`。
- 相对行业目标收益。
- 个股收益在 PIT universe 中的横截面分位。
- 个股收益在行业内的横截面分位。
- 弱市场中的相对强股票。
- 行业弱但个股先行的领先股。
- 行业强且个股同步扩展的共振股。

### 7.3 成交与流动性原语

包括但不限于：

- `money_ratio5/20/60`。
- 成交额在 PIT universe 中的分位。
- 成交额在行业内的分位。
- 缩量横盘后放量。
- 放量突破后回落但不破位。
- 长期低成交后成交额 regime shift。
- 高成交额持续天数。
- 成交额与涨幅背离。

### 7.4 波动与压缩扩张原语

包括但不限于：

- `volatility10/20/60`。
- `atr10/20/60_pct`。
- 波动率分位。
- 波动压缩后扩张。
- 高波动趋势延续。
- 大振幅日占比。
- 连续窄幅整理。
- 低波慢趋势与高波快趋势分型。

### 7.5 回撤修复与底部结构原语

包括但不限于：

- 从 60/120/240 日高点回撤幅度。
- 回撤后首次修复关键区间。
- 长期下跌后的止跌横盘。
- 低点抬高 / 高点抬高。
- V 型修复、U 型修复、长平台修复。
- 跌破后快速收复。
- 多次假跌破后回到区间上沿。

注意：这里可以包含 EMA reclaim，但不得只用 EMA reclaim 表示全部修复结构。

### 7.6 趋势年龄与趋势阶段原语

包括但不限于：

- 当前上升趋势持续天数。
- 距离趋势起点的交易日数。
- 趋势斜率变化。
- 趋势加速度。
- 已涨幅度与剩余潜在空间的关系。
- 趋势中继与末端加速的区分。

趋势定义不得只依赖 EMA。可以同时使用移动高低点、线性斜率、收益曲线、rolling rank 和 change point。

### 7.7 市场与行业 regime 原语

包括但不限于：

- benchmark trend / drawdown / volatility。
- market width。
- 行业收益、行业宽度、行业同步。
- 行业内强势股占比。
- 行业集中度。
- 市场弱但个股领先。
- 市场强但个股滞后。
- 市场转折初期的领先股。

regime 不得默认作为硬过滤。必须同时评估：

- 作为 filter 的效果。
- 作为 sizing / confidence 的效果。
- 作为 exit tolerance 的效果。
- 作为 confirmation requirement 的效果。

### 7.8 行业与风格分层原语

必须按行业、波动、成交额、趋势速度、market cap、listing age 分层。

最低分层：

- 行业：SW / target industry。
- 波动：低 / 中 / 高。
- 成交额：低 / 中 / 高。
- 趋势速度：慢趋势 / 中速趋势 / 快速趋势。
- 行情类型：普涨修复 / 结构性行情 / 弱市独立 alpha / 强行业共振。

目标是避免银行、非银、食品饮料、汽车、有色、电力设备共用同一个固定阈值。

### 7.9 形态片段与序列原语

Explore9 允许做形态片段探索，但不能提前假设形态名称。

本节属于 P2 记录。P0 只需要把该 family 写入 registry，不要求实际聚类或 motif discovery。

P2 若启动，必须至少支持：

- 过去 20 / 60 / 120 日标准化价格序列聚类。
- 成交额序列聚类。
- 收益 + 成交 + 波动联合序列聚类。
- 大涨股早期窗口与普通股票窗口的 motif 差异。
- 序列簇按年份、行业、后续涨幅分布的稳定性。

可选方法：

- DTW / shape clustering。
- rolling z-score 序列聚类。
- change-point detection。
- 简单 shape descriptors。

P2 第一版不要求深度学习序列模型；若使用，必须只作为诊断，不得直接宣称策略有效。

### 7.10 横截面异常与领先性原语

包括但不限于：

- 过去 N 日收益突然进入全市场前 X%。
- 成交额突然进入全市场前 X%。
- 行业内排名突然跃迁。
- 个股领先行业转强。
- 个股在行业未同步前已经持续强于行业。
- 低波动行业中异常放量上涨。
- 弱市场中的孤立强势。

这类原语是 Explore9 的重点之一，因为 Explore8 已经说明很多 winner 的早期阶段还没有市场和行业同步确认。

### 7.11 P0 / P1 / P2 阶段边界

Explore9 必须明确分阶段，避免第一版范围过大导致实现流于表面。

#### P0：第一版必须完成

P0 只做 broad discovery 的基础层，目标是把标签、原语和 lift 体系跑通，并形成可审计的初步线索。

P0 必须完成：

- 数据审计、coverage audit、source audit、manifest。
- stock-day forward labels 和 episode lifecycle labels 的独立重算。
- `retrospective_lifecycle_stage` 与 `observable_state_stage` 的隔离。
- 10 类 feature family 的 registry / dictionary。
- 至少 `30` 个 P0 单变量原语。
- 至少 `10` 个 P0 双变量组合。
- 每个 P0 原语的覆盖率、baseline、future 50% / 100% lift、年度稳定性、行业稳定性。
- 至少 `5` 个 preliminary discovery leads，其中至少 `3` 个不依赖 EMA、breakout、pullback。
- 中文 P0 报告，明确哪些方向进入 P1，哪些方向淘汰。

P0 不要求形成正式 hypothesis，不要求做 shape clustering，不要求完成 hold / exit 深化，不要求做策略回测。

#### P1：仅记录，P0 完成后再细化

P1 是后续 hypothesis generation 阶段。当前需求只记录方向，不作为 P0 验收项。

P1 候选内容：

- 可解释规则挖掘。
- formal hypothesis leaderboard。
- post-20pct / post-30pct continuation 深化。
- early exit replacement hypotheses。
- regime-aware confirmation / sizing / exit tolerance 设计。

P1 必须等待 P0 报告确认值得继续的 feature families 后再细化。

#### P2：仅记录，P0 完成后再细化

P2 是后续复杂形态和策略准备阶段。当前需求只记录方向，不作为 P0 验收项。

P2 候选内容：

- price / money / joint sequence clustering。
- motif discovery。
- change-point / shape descriptor 深化。
- 面向 Explore10 的策略回测候选整理。

P2 不得在 P0 尚未完成前抢先实现为主线。

## 8. 探索方法

Explore9 必须同时使用 rule-based profiling 和 data-driven discovery，不得只做单一模型。

### 8.1 P0：单变量与双变量 lift

P0 必须对每个已启用的 P0 原语输出：

- 样本覆盖率。
- future 50% / 100% 标签命中率。
- 相对全样本 baseline 的 lift。
- 年度命中率。
- 行业分布。
- 平均提前量。
- 平均未来最大涨幅。
- future drawdown before gain。

P0 双变量组合至少覆盖以下方向中的代表组合，不要求第一版穷尽全部组合：

- 价格状态 + 成交。
- 相对强度 + 市场 regime。
- 行业同步 + 个股领先。
- 波动压缩 + 放量扩张。
- 回撤修复 + 相对强度。

P0 只输出 preliminary discovery leads，不输出正式策略规则。

#### 8.1.1 Baseline 与 binning 规则

P0 必须固定 baseline 口径，避免不同原语之间 lift 不可比。

主 baseline：

```text
same_year_same_horizon_horizon_valid_pit_stock_days
```

即：同一年、同一 forward horizon、满足 6.1.1 主 lift eligibility 的 PIT stock-day 样本。

补充 baseline：

- `global_horizon_valid_baseline`：全研究期同 horizon 的 horizon-valid PIT stock-days。
- `industry_year_baseline`：同一年、同行业、同 horizon 的 horizon-valid PIT stock-days。
- `market_regime_year_baseline`：同一年、同 market regime、同 horizon 的 horizon-valid PIT stock-days。

每个 primitive / lead 必须记录：

```text
baseline_scope
baseline_sample_count
baseline_positive_rate
lead_positive_rate
lift_vs_baseline
global_lift
industry_relative_lift
```

分箱规则：

- 连续变量默认按每个自然年内的 PIT 横截面分位分箱，默认分位为 `p10/p20/p40/p60/p80/p90`。
- 对成交额、波动率、收益率等重尾变量，必须同时记录 winsorization 或 clipping 规则。
- 所有阈值如果从数据分位产生，必须逐年计算，不得用全样本未来分布。
- 二元原语必须明确 true / false 的定义。
- 双变量组合必须记录两个变量各自分箱和组合后的样本数；样本过少的组合必须标记 `sparse_bin = true`。

### 8.2 P1 记录：可解释规则挖掘

本节仅记录 P1 方向，P0 不要求实现。P0 完成后，允许使用 decision tree / rule list / monotonic binning 做候选规则挖掘。

P1 要求：

- 每条规则必须只由 T 日可观察特征组成。
- 每条规则必须输出 human-readable formula。
- 规则复杂度必须受限，例如最大深度、最大条件数。
- 不得把黑箱模型分数直接当作规则。
- 每条规则必须按 distinct year 输出覆盖率、precision、lift、提前量和行业集中度。

### 8.3 P2 记录：序列聚类与形态发现

本节仅记录 P2 方向，P0 不要求实现。P2 若启动，必须至少输出：

- `price_shape_cluster_summary.csv`
- `money_shape_cluster_summary.csv`
- `joint_shape_cluster_summary.csv`

每个 cluster 至少统计：

- 样本数。
- future 50% / 100% 命中率。
- 主要年份。
- 主要行业。
- 平均未来涨幅。
- 平均未来回撤。
- 与 Explore9 独立重算的大涨 episode 早期窗口的匹配比例。

Explore8 大涨 episode CSV 只能用于最终 audit diff，不能用于 cluster 训练、cluster 打分或 early window 匹配计算。

### 8.4 P0 / P1：生命周期分析

P0 必须把 preliminary discovery leads 映射到 `observable_state_stage` 和报告阶段，不得把所有线索都描述为买点。

P1 若启动，必须进一步把 formal hypotheses 映射到生命周期阶段：

- early discovery：大涨前或低点后早期。
- repair confirmation：已经修复但未进入强趋势。
- continuation confirmation：已经上涨 20% / 30%。
- hold confirmation：应延长持有而非退出。
- late warning：可能已经进入末端加速或冲高回落。

生命周期映射只能使用 T 日可观察状态；如果某个阶段只能事后确认，必须标记为 `retrospective_only`。

### 8.5 P1 记录：Exit / Hold 探索

本节仅记录 P1 方向，P0 不要求深化实现。P0 只需在报告中指出是否存在值得进入 P1 的 hold / exit 线索。

P1 至少分析：

- 已经上涨 20% 后继续上涨到 50% / 100% 的条件。
- 已经上涨 30% 后继续上涨到 100% / 200% 的条件。
- 高点前正常回撤与趋势破坏的区别。
- market / industry 状态改善是否支持放宽退出。
- 成交额持续放大是否支持 winner hold。
- 行业收益进入 `40%+` 或 `60%+` 后是否提高尾部延展概率。

P1 输出必须区分：

- `fast_failure_exit_condition`
- `normal_pullback_hold_condition`
- `winner_hold_condition`
- `late_trend_risk_condition`

## 9. 候选假设生成

本节是 P1 记录，P0 不要求输出 formal candidate hypotheses。

P0 只输出 `preliminary_discovery_leads`，用于说明哪些 feature families 值得进入 P1。P0 lead 不得被称为策略规则，也不得被标记为可回测版本。

P1 若启动，可以输出 candidate hypotheses，但不得直接输出 frozen strategy。每个 hypothesis 必须包含：

```text
hypothesis_id
hypothesis_name
stage
human_readable_formula
feature_family
sample_count
year_coverage
industry_coverage
future_50pct_precision
future_100pct_precision
lift_vs_baseline
avg_lead_time_to_50pct
avg_future_max_gain
avg_future_drawdown_before_gain
market_regime_dependency
industry_dependency
known_failure_modes
recommended_next_test
candidate_for_strategy_backtest
candidate_for_strategy_backtest_reason
```

`candidate_for_strategy_backtest = true` 只能表示“值得下一阶段回测验证”，不能表示可冻结或可实盘。

P1 默认门槛：

- `general_hypothesis` 样本必须覆盖至少 `4` 个 distinct years。
- `general_hypothesis` 不能有超过 `50%` 样本来自单一年份。
- `general_hypothesis` 不能有超过 `50%` 样本来自单一行业。
- `industry_specific_hypothesis` 可以集中于单一行业，但必须至少覆盖 `3` 个 distinct years 或明确标记为 `diagnostic_only_industry_cycle_hypothesis`。
- `regime_specific_hypothesis` 可以集中于特定 market / industry regime，但必须单独报告 regime 覆盖率和失效 regime。
- future 50% lift 必须高于 baseline，且至少在 `3` 个 distinct years 中为正。
- 平均提前量必须早于 `first_breakout_signal` 的平均 lag。
- 若交易样本过少，必须标记为 `diagnostic_only_sparse_hypothesis`。

## 10. 必须输出的文件

本节按 P0 / P1 / P2 分层。P0 文件是第一版验收范围；P1 / P2 文件只记录为后续计划，P0 不要求生成。

### 10.1 P0 必须输出：数据与标签审计

```text
Explore9/outputs/reports/source_data_audit.csv
Explore9/outputs/reports/source_data_audit_summary.json
Explore9/outputs/reports/provider_coverage_audit.csv
Explore9/outputs/reports/label_coverage_audit.csv
Explore9/outputs/reports/run_manifest.json
```

manifest 必须记录：

```text
point_in_time_universe = true
point_in_time_industry = true
price_adjustment_mode
explore8_profile_csv_used_for_label = false
explore8_profile_csv_used_for_signal = false
explore8_profile_csv_used_for_selection = false
historical_trade_results_used_for_labeling = false
historical_trade_results_used_for_signal = false
observed_reference_used_for_selection = false
```

### 10.2 P0 必须输出：标签与样本

```text
Explore9/outputs/cache/stock_day_label_panel.parquet
Explore9/outputs/reports/stock_day_label_panel_summary.csv
Explore9/outputs/reports/episode_lifecycle_labels.csv
Explore9/outputs/reports/label_distribution_by_year.csv
Explore9/outputs/reports/label_distribution_by_industry.csv
Explore9/outputs/reports/observed_reference_label_audit.csv
```

明细级 `stock_day_label_panel` 默认写入 `outputs/cache/`，不得作为 report CSV 默认提交。`outputs/reports/` 只放 summary、分布和审计表。manifest 必须记录明细 panel 的路径、格式、行数、列数和文件大小。

### 10.3 P0 必须输出：原语特征与 lift

```text
Explore9/outputs/reports/primitive_feature_dictionary.csv
Explore9/outputs/reports/primitive_feature_coverage.csv
Explore9/outputs/reports/primitive_univariate_lift.csv
Explore9/outputs/reports/primitive_pairwise_lift.csv
Explore9/outputs/reports/primitive_year_stability.csv
Explore9/outputs/reports/primitive_industry_stability.csv
```

P0 还必须输出：

```text
Explore9/outputs/reports/preliminary_discovery_leads.csv
Explore9/outputs/reports/p0_scope_completion_audit.csv
```

`preliminary_discovery_leads.csv` 至少包含：

```text
lead_id
lead_name
feature_family
observable_state_stage
formula_or_bin
direction
horizon
baseline_scope
stock_day_count
unique_instrument_count
unique_instrument_year_count
unique_episode_count
positive_stock_day_count
positive_unique_instrument_year_count
positive_unique_episode_count
baseline_positive_rate
lead_future_50pct_precision
lead_future_100pct_precision
lift_vs_baseline
episode_dedup_lift
instrument_year_dedup_lift
year_positive_lift_count
distinct_year_count
distinct_industry_count
industry_concentration_top1
avg_lead_time_to_50pct
median_lead_time_to_50pct
avg_future_max_gain
avg_future_drawdown_before_gain
label_horizon_truncated_rate
observed_reference_overlap_rate
duplicate_positive_risk
sparse_bin
failure_reason
recommended_next_phase
```

`recommended_next_phase` 只能取：

```text
drop
p1_hypothesis_refine
p1_hold_exit_refine
p2_shape_refine
needs_more_data
```

### 10.4 P2 记录：形态与序列

```text
Explore9/outputs/reports/price_shape_cluster_summary.csv
Explore9/outputs/reports/money_shape_cluster_summary.csv
Explore9/outputs/reports/joint_shape_cluster_summary.csv
Explore9/outputs/reports/shape_cluster_examples.csv
```

以上文件不是 P0 验收项。若 P0 未生成，manifest 必须记录为 `deferred_to_p2`。

### 10.5 P1 记录：候选假设

```text
Explore9/outputs/reports/hypothesis_discovery_leaderboard.csv
Explore9/outputs/reports/hypothesis_year_breakdown.csv
Explore9/outputs/reports/hypothesis_industry_breakdown.csv
Explore9/outputs/reports/hypothesis_lifecycle_stage_breakdown.csv
Explore9/outputs/reports/hypothesis_failure_modes.csv
```

以上文件不是 P0 验收项。若 P0 未生成，manifest 必须记录为 `deferred_to_p1`。

### 10.6 P1 记录：持有与退出

```text
Explore9/outputs/reports/hold_condition_analysis.csv
Explore9/outputs/reports/early_exit_replacement_hypotheses.csv
Explore9/outputs/reports/post_20pct_continuation_analysis.csv
Explore9/outputs/reports/post_30pct_continuation_analysis.csv
```

以上文件不是 P0 验收项。若 P0 未生成，manifest 必须记录为 `deferred_to_p1`。

### 10.7 P0 必须输出：最终报告

```text
Explore9/outputs/reports/explore9_broad_discovery_report.md
```

最终报告必须用中文，至少包含：

- 数据覆盖和标签质量。
- Explore8 关键发现如何转化为 Explore9 探索问题。
- 大涨股早期结构的广度探索结果。
- 各类原语的 lift 和稳定性。
- 非 EMA / 非 breakout / 非 pullback 形态的发现。
- 市场和行业状态如何影响发现、确认和持有。
- preliminary discovery leads 的优先级。
- 哪些方向不值得进入 P1。
- 哪些方向建议进入 P1 / P2，且说明原因。
- 是否具备进入 P1 / P2 细化的基础；Explore10 只能作为远期路径记录，不得作为 P0 直接建议。

## 11. 评价指标

Explore9 的评价指标不是组合收益优先，而是 discovery 质量优先。

P0 对每个 primitive 和 preliminary discovery lead 必须报告：

- `baseline_future_50pct_rate`
- `lead_future_50pct_precision`
- `lead_future_100pct_precision`
- `lift_vs_baseline`
- `sample_count`
- `unique_instrument_count`
- `unique_instrument_year_count`
- `unique_episode_count`
- `distinct_year_count`
- `distinct_industry_count`
- `year_positive_lift_count`
- `industry_concentration_top1`
- `avg_lead_time_to_50pct`
- `median_lead_time_to_50pct`
- `avg_future_max_gain`
- `avg_future_drawdown_before_gain`
- `turnover_proxy`
- `market_regime_dependency`
- `industry_regime_dependency`
- `label_horizon_truncated_rate`
- `observed_reference_overlap_rate`
- `episode_dedup_lift`
- `instrument_year_dedup_lift`
- `duplicate_positive_risk`

P1 若生成 formal hypothesis，可在同一口径下增加 `hypothesis_*` 字段，但 P0 不要求。

报告必须明确区分：

- 高 precision 但样本极少。
- 样本多但 lift 很弱。
- 只在单一年份有效。
- 只在单一行业有效。
- 强市场有效但弱市场无效。
- 弱市场领先但强市场滞后。
- 入场线索和持有线索。

## 12. 广度探索最低覆盖要求

为了避免 Explore9 退化为 EMA / breakout 的局部扩展，同时避免 P0 第一版范围过大导致 superficial，P0 只要求满足以下最低覆盖：

- 10 类信号原语全部进入 `primitive_feature_dictionary.csv` 的 registry。
- 至少 `30` 个单变量原语。
- 至少 `10` 个双变量组合。
- 至少 `5` 个 preliminary discovery leads。
- 至少 `3` 个 preliminary discovery leads 不依赖 EMA、breakout、pullback。
- 至少 `2` 个 preliminary discovery leads 来自相对强度 / 行业领先。
- 至少 `2` 个 preliminary discovery leads 来自成交额 / 波动压缩扩张。
- 至少 `1` 个 preliminary discovery lead 描述 continuation / hold 方向，但 P0 不要求完成 hold / exit 深化。
- P1 / P2 的 formal hypothesis、形态聚类、完整 hold / exit 文件只记录为 deferred，不计入 P0 失败。

若无法满足，报告必须标记：

```text
broad_discovery_p0_minimum_coverage_met = false
```

并说明缺失原因。

## 13. 禁止事项

禁止：

- 只围绕 EMA、breakout、pullback 调参。
- 只输出收益排名，不解释样本数量、年份稳定性和行业集中度。
- 把低点、未来高点、未来涨幅、未来行业收益作为 T 日特征。
- 用 2025-2026 observed reference 做阈值选择。
- 用 Explore8 的 episode CSV 直接当训练标签。
- 用历史交易结果 CSV 作为 label、signal、feature 或 selection input。
- 只报告 AUC / accuracy，不报告 lift、提前量、年度稳定性。
- 只做黑箱模型，不输出 human-readable lead / hypothesis。
- 在 P0 阶段强行实现 P1 / P2 范围，导致标签、原语和 lift 审计没有完成。
- 直接形成 `candidate_for_future_final_test` 或 frozen strategy。

## 14. 成功标准

Explore9 P0 第一版成功不要求产生可交易策略，也不要求完成 formal hypothesis。P0 必须产生可信的下一阶段研究方向。

最低成功标准：

- PIT 数据和标签生成通过审计。
- stock-day forward labels 可重算。
- Explore8 中的年度大涨分布能在 Explore9 标签体系中被近似复核。
- 至少发现 `3` 个跨年份、有正 lift、非单一年份/行业驱动的 early discovery preliminary leads。
- 至少发现 `1` 个 post-20pct / post-30pct continuation 或 winner hold 方向的 preliminary lead，若没有则必须说明为什么 P1 hold / exit 暂不值得继续。
- 明确淘汰一批无效线索，并说明原因。
- 最终报告给出“是否进入 P1 / P2 细化”的清晰建议。
- P0 不得直接建议进入 Explore10 策略回测。Explore10 只能作为远期路径记录，是否进入必须等待 P1 / P2 细化后重新评估。

如果没有任何 preliminary lead 达标，Explore9 P0 仍可成功，但报告必须明确结论为：

```text
未发现足够稳定的早期结构，下一阶段不应进入 P1 hypothesis 细化或策略回测，应继续数据画像或扩大数据维度。
```

## 15. 建议命令

P0 第一版可以在 `Explore9/scripts/run_explore9.py` 中实现以下命令：

```text
self-test
build-labels
profile-primitives
explore9-report
```

命令职责：

- `build-labels`：生成 stock-day forward labels、episode lifecycle labels、coverage audit。
- `profile-primitives`：生成所有原语特征和 lift 表。
- `explore9-report`：读取 Explore9 输出，生成中文最终报告。

P1 / P2 记录命令，P0 不要求实现：

```text
discover-hypotheses
analyze-hold-exit
cluster-shapes
```

- `discover-hypotheses`：P1，从 P0 lead 中生成 formal hypotheses。
- `analyze-hold-exit`：P1，专门分析 20% / 30% 后的继续上涨与退出替代条件。
- `cluster-shapes`：P2，做价格、成交和联合序列聚类。

## 16. 测试与验收

静态检查：

```text
uv run python -m compileall Explore9/scripts
uv run python Explore9/scripts/run_explore9.py self-test --config Explore9/configs/broad_discovery_v1.yaml
```

数据与标签：

```text
uv run python Explore9/scripts/run_explore9.py build-labels --config Explore9/configs/broad_discovery_v1.yaml
```

必须验证：

- required outputs 存在；report CSV 必须有 header，cache parquet 必须能读取 schema。
- 每个 T 日样本都在当日 PIT membership 中。
- label horizon truncation 被显式记录。
- 主 lift 样本排除了 `label_horizon_truncated = true` 和 `observed_reference_overlap = true`。
- 每个 primitive 的 feature warmup / history eligibility 被显式记录。
- 2025-2026 observed reference 没有用于 selection。
- Explore8 profile CSV 没有用于 label/signal/selection。

P0 探索：

```text
uv run python Explore9/scripts/run_explore9.py profile-primitives --config Explore9/configs/broad_discovery_v1.yaml
```

必须验证：

- 10 类原语都有 registry。
- P0 enabled primitives 有 coverage、lift、year stability、industry stability。
- 至少有非 EMA / 非 breakout / 非 pullback preliminary discovery lead。
- 每个 preliminary discovery lead 有年份和行业 breakdown。
- 每个 preliminary discovery lead 同时报告 stock-day、instrument-year 和 episode 去重口径。
- baseline 使用同年、同 horizon、horizon-valid PIT stock-day 主口径。
- P1 / P2 deferred items 在 manifest 和报告中记录清楚。

P1 / P2 记录命令，P0 不要求执行：

```text
uv run python Explore9/scripts/run_explore9.py discover-hypotheses --config Explore9/configs/broad_discovery_v1.yaml
uv run python Explore9/scripts/run_explore9.py analyze-hold-exit --config Explore9/configs/broad_discovery_v1.yaml
uv run python Explore9/scripts/run_explore9.py cluster-shapes --config Explore9/configs/broad_discovery_v1.yaml
```

报告：

```text
uv run python Explore9/scripts/run_explore9.py explore9-report --config Explore9/configs/broad_discovery_v1.yaml
```

报告必须回答：

- 哪些早期结构值得进一步研究。
- 哪些结构只是后期确认，不适合作为入场。
- 哪些市场/行业状态应作为分层而不是硬过滤。
- 哪些 hold / exit 方向可能减少 Explore8 的 early exit 损失，并是否值得进入 P1。
- 是否建议进入 P1 / P2 细化；Explore10 只能作为远期路径记录。

## 17. 第一版不做的事情

Explore9 第一版不做：

- 不训练全市场收益预测 topK 模型。
- 不生成生产策略。
- 不形成 frozen candidate。
- 不用 2025-2026 选择规则。
- 不继续修 pullback 规则。
- 不把 breakout 当作主入场。
- P0 不输出 formal hypothesis leaderboard。
- P0 不做 shape clustering / motif discovery。
- P0 不做完整 hold / exit 深化。
- 不以组合收益作为唯一成功标准。
- 不承诺所有 hypothesis 都进入回测。

Explore9 的产物应该是一组数据支撑的、可解释的、跨年份审计过的研究假设，而不是又一个局部调参后的策略版本。
