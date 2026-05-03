# Explore3 EMA Trend Rule Strategy Report

## 1. Executive Summary

- Report generated: `2026-05-03 08:57:25` Asia/Shanghai.
- This is a rule-only Explore3 phase-one experiment. It does not use Alpha360, LightGBM, or any model predictions.
- Stock daily bars are read from `Explore1/data/qlib/cn_data` and treated as read-only Explore1 cache input.
- The static stock universe is `mcap500_mainboard_20251231` with `282` resolved instruments.
- Backtest window is `2025-01-01` to `2026-04-29`; source data ends at `2026-04-30`.
- Final selected phase-one strategy is `layered_exit`; it produced `41.89%` cost-after return and `-8.63%` max drawdown.
- The highest raw return variant is `ema_state_only` with `54.72%` cost-after return.
- The main result is not that the layered version maximizes return. It reduces drawdown and raises trade quality relative to the broad EMA-state baseline.

## 2. Reproduction Contract

| Item | Value |
| --- | --- |
| Config | `Explore3/configs/trend_rule_v1.yaml` |
| Config SHA256 | `0daa99d1c936355077f1b14cfc007839480da9284fc1fe335344234e64d58b5f` |
| CLI | `uv run python Explore3/scripts/run_explore3.py all --config Explore3/configs/trend_rule_v1.yaml` |
| Provider URI | `Explore1/data/qlib/cn_data` |
| Market | `mcap500_mainboard_20251231` |
| Benchmark | `SH000300` |
| Frequency | `day` |
| Deal price | `open`; close-based signals are executed at next trading day open |
| Initial account | `1,000,000.00` |
| Open cost | `0.05%` |
| Close cost | `0.15%` |
| Min cost | `5.00` |
| Limit threshold | `9.50%` |
| Risk-unit sizing | `False` |
| Tushare token stored in artifacts | `No`; manifest records only `tushare_token_present=True` |

## 3. Data Sources And Coverage

### 3.1 Stock Qlib Provider

| Check | Value |
| --- | --- |
| Instruments checked | 282 |
| Failed instruments | 0 |
| Coverage start | 2017-01-03 |
| Coverage end | 2026-04-30 |
| Total provider rows | 599,532 |
| Total missing field values | 33,180 |
| Duplicate date rows | 0 |
| Required fields | $open, $high, $low, $close, $volume, $money, $factor |

Provider rows by instrument are available in `Explore3/outputs/reports/explore1_cache_coverage.csv`.

### 3.2 Market, Industry, And Theme Targets

| Type | Targets | Fetched | Failed | Rows | Start | End | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| market | 4 | 4 | 0 | 9,052 | 2017-01-03 | 2026-04-30 | tushare.index_daily |
| industry | 31 | 31 | 0 | 70,153 | 2017-01-03 | 2026-04-30 | tushare.sw_daily |
| theme | 4 | 4 | 0 | 7,198 | 2017-01-03 | 2026-04-30 | tushare.index_daily |

- Total target history rows: `86,403`.
- Target fetch successes: `39`; failures: `0`.
- Market and theme index histories use `tushare.index_daily` when available.
- SW2021 industry index histories use `tushare.sw_daily`.

### 3.3 SW2021 Industry Membership

| Metric | Value |
| --- | --- |
| Membership source | tushare.index_member |
| Industry targets | 31 |
| Failed industry memberships | 0 |
| Active constituent rows | 5,199 |
| Universe instruments mapped | 282 / 282 |
| Membership as-of date | 20260430 |

Detailed industry membership status:

| Industry | Target key | Status | Rows | Source | As-of |
| --- | --- | --- | --- | --- | --- |
| 801010.SI | sw_801010 | ok | 104 | tushare.index_member | 20260430 |
| 801030.SI | sw_801030 | ok | 409 | tushare.index_member | 20260430 |
| 801040.SI | sw_801040 | ok | 44 | tushare.index_member | 20260430 |
| 801050.SI | sw_801050 | ok | 140 | tushare.index_member | 20260430 |
| 801080.SI | sw_801080 | ok | 481 | tushare.index_member | 20260430 |
| 801110.SI | sw_801110 | ok | 94 | tushare.index_member | 20260430 |
| 801120.SI | sw_801120 | ok | 123 | tushare.index_member | 20260430 |
| 801130.SI | sw_801130 | ok | 106 | tushare.index_member | 20260430 |
| 801140.SI | sw_801140 | ok | 158 | tushare.index_member | 20260430 |
| 801150.SI | sw_801150 | ok | 479 | tushare.index_member | 20260430 |
| 801160.SI | sw_801160 | ok | 131 | tushare.index_member | 20260430 |
| 801170.SI | sw_801170 | ok | 126 | tushare.index_member | 20260430 |
| 801180.SI | sw_801180 | ok | 99 | tushare.index_member | 20260430 |
| 801200.SI | sw_801200 | ok | 99 | tushare.index_member | 20260430 |
| 801210.SI | sw_801210 | ok | 81 | tushare.index_member | 20260430 |
| 801230.SI | sw_801230 | ok | 15 | tushare.index_member | 20260430 |
| 801710.SI | sw_801710 | ok | 72 | tushare.index_member | 20260430 |
| 801720.SI | sw_801720 | ok | 156 | tushare.index_member | 20260430 |
| 801730.SI | sw_801730 | ok | 367 | tushare.index_member | 20260430 |
| 801740.SI | sw_801740 | ok | 141 | tushare.index_member | 20260430 |
| 801750.SI | sw_801750 | ok | 334 | tushare.index_member | 20260430 |
| 801760.SI | sw_801760 | ok | 130 | tushare.index_member | 20260430 |
| 801770.SI | sw_801770 | ok | 122 | tushare.index_member | 20260430 |
| 801780.SI | sw_801780 | ok | 42 | tushare.index_member | 20260430 |
| 801790.SI | sw_801790 | ok | 82 | tushare.index_member | 20260430 |
| 801880.SI | sw_801880 | ok | 285 | tushare.index_member | 20260430 |
| 801890.SI | sw_801890 | ok | 533 | tushare.index_member | 20260430 |
| 801950.SI | sw_801950 | ok | 37 | tushare.index_member | 20260430 |
| 801960.SI | sw_801960 | ok | 47 | tushare.index_member | 20260430 |
| 801970.SI | sw_801970 | ok | 133 | tushare.index_member | 20260430 |
| 801980.SI | sw_801980 | ok | 29 | tushare.index_member | 20260430 |

## 4. Rule Design Implemented

### 4.1 Strategy Layers

1. Static large-cap mainboard stock universe copied from Explore1.
2. Market regime filter from broad-market EMA60 state and slope.
3. Market breadth filter from stock-pool EMA state ratios.
4. SW2021 industry trend filter from industry index EMA60, slope, and 60-day relative return versus broad market.
5. EMA trend candidate state on each stock.
6. Cross-sectional `trend_score` ranking.
7. Breakout and pullback entry triggers.
8. ATR/structure stop and layered exit rules.

### 4.2 Core Thresholds

| Rule | Config value |
| --- | --- |
| Market trend | broad_market close > EMA60 and EMA60 slope20 > 0 |
| Market breadth | close > EMA60 ratio > 55.00%; EMA20 > EMA60 ratio > 45.00% |
| Candidate distance | dist_ema20 < min(8.00%, 2.0 * ATR20 / close) |
| Candidate volatility | volatility20 <= daily p90 |
| Candidate liquidity | avg_money20 >= daily p20 |
| Trend-score buyable set | top 20.00% by score among industry-filtered candidates |
| Breakout | close > prior 60D high, money_ratio20 >= 1.2, close in upper half, upper shadow <= 40.00% |
| Pullback | pullback near EMA20/EMA30 within 3.00%, above EMA60, volume ratio <= 1.0, close reclaims EMA20 |
| Fixed stop | 8.00% below entry |
| ATR/structure stop | structure low minus 0.5 * ATR20, fallback 2.0 * ATR20 |
| Time stop | 10 calendar days without profit |
| Max positions | 20 |
| Single stock max weight | 5.00% |
| Max daily new weight | 20.00% |

### 4.3 Trend Score Formula

| Component | Weight |
| --- | --- |
| ema60_slope10 | 0.25 |
| ret60_excess | 0.2 |
| ema20_ema60_spread | 0.15 |
| money_ratio20 | 0.15 |
| ret20 | 0.1 |
| adx_proxy20 | 0.1 |
| overheat | -0.15 |
| volatility20 | -0.1 |

All score components are winsorized by daily cross-section and converted to z-scores before weighting.

### 4.4 `layered_exit` Strategy Mechanics: Entry, Holding, And Exit

`layered_exit` 是本轮 Explore3 第一阶段的最终规则版本。它不是简单的 `EMA20 > EMA60` 买入策略，而是一个分层趋势交易状态机：先判断是否处在适合趋势交易的市场和行业环境，再判断个股是否处于趋势候选状态，再用 `trend_score` 排序，最后只在突破或回踩触发时买入。买入之后，是否继续持有不再要求每天重新满足入场条件，而是由结构止损、ATR trailing、时间止损和 EMA60 趋势终结线共同决定。

#### 4.4.1 入场总流程

信号日为 `T` 日。所有入场条件都使用 `T` 日收盘后可以观察到的数据；实际成交安排在 `T+1` 交易日开盘。若 `T+1` 开盘价触发主板近似涨停限制，即 `open >= prev_close * (1 + limit_threshold)`，买入会被跳过。

| Layer | Required condition | Purpose |
| --- | --- | --- |
| 股票池 | `mcap500_mainboard_20251231` 静态大市值主板股票池 | 降低小票、低流动性和非主板涨跌停规则带来的噪音 |
| 市场趋势 | 沪深300 `close > EMA60` 且 `EMA60 slope20 > 0` | 只在主市场趋势向上时开新仓 |
| 市场宽度 | 股票池 `close > EMA60` 比例 > 55.00%，且 `EMA20 > EMA60` 比例 > 45.00% | 避免指数被少数权重股拉住但多数股票已经转弱 |
| 行业顺风 | 个股所属 SW2021 行业指数 `close > EMA60`、`EMA60 slope20 > 0`、`ret60 > broad_market ret60` | 只在行业趋势也顺风时交易个股 |
| 个股趋势候选 | `EMA20 > EMA60`、`EMA60 slope10 > 0`、`close > EMA60` | EMA 多头排列只表示候选状态，不直接等于买入 |
| 不追高 | `dist_ema20 < min(8.00%, 2.0 * ATR20 / close)` | 避免在短期加速末端追入 |
| 波动过滤 | `volatility20 <= daily p90` | 排除波动过高、止损距离不稳定的候选 |
| 流动性过滤 | `avg_money20 >= daily p20` | 排除当日截面中成交额偏低的股票 |
| 趋势质量 | `trend_score_pct <= 20.00%` | 只保留行业过滤后趋势质量排名靠前的候选 |
| 最终触发 | `breakout_entry OR pullback_entry` | 必须有明确买点，不能只因 EMA 多头就买 |

#### 4.4.2 突破型入场

突破型入场用于捕捉趋势继续向上加速。该类信号必须先通过所有共同过滤，再满足以下触发条件：

| Condition | Value |
| --- | --- |
| 突破位置 | `close > prior 60D high` |
| 成交额确认 | `money_ratio20 >= 1.2` |
| 日内收盘位置 | `close_pos >= 0.5`，即收盘在当日振幅上半区 |
| 上影线控制 | `upper_shadow_pct <= 40.00%` |
| 追高控制 | 仍需满足 `dist_ema20 < max_dist` |
| 成交方式 | `T` 日收盘生成信号，`T+1` 日开盘买入 |

#### 4.4.3 回踩型入场

回踩型入场用于捕捉趋势中的缩量回调后重新转强。该类信号必须先通过所有共同过滤，再满足以下触发条件：

| Condition | Value |
| --- | --- |
| 回踩位置 | `low <= EMA20 * (1 + 3.00%)` 或 `low <= EMA30 * (1 + 3.00%)` |
| 趋势底线 | `low > EMA60`，回踩不能跌破中期趋势线 |
| 缩量回调 | `money_ratio20 <= 1.0` |
| 重新转强 | `close >= EMA20` 且 `close > open` |
| 成交方式 | `T` 日收盘生成信号，`T+1` 日开盘买入 |

如果同一天同时满足突破和回踩，代码优先把交易标记为 `breakout`；否则满足回踩条件时标记为 `pullback`。

#### 4.4.4 建仓和初始风险

| Item | Rule |
| --- | --- |
| 最大持仓数 | 20 |
| 单票目标权重 | `min(5.00%, risk_degree / max_positions)`，当前约为 `4.75%` |
| 单日新增仓位上限 | 20.00% |
| 成交股数 | 按 100 股整数手向下取整 |
| 买入成本 | `max(value * 0.0005, 5)` |
| 初始风险 R | `R = max(entry_price - initial_stop, entry_price * 1%)` |

初始止损按入场类型决定：

| Entry type | Initial stop |
| --- | --- |
| breakout | `rolling_low20 - 0.5 * ATR20` |
| pullback | `recent_low5 - 0.5 * ATR20` |
| fallback | 若结构止损无效，使用 `entry_price - 2.0 * ATR20` |

#### 4.4.5 持有条件

买入后，持仓不会因为市场过滤、行业过滤或入场触发条件消失而立刻卖出。换句话说，入场条件只决定能不能开仓；开仓后，是否继续持有由持仓风控状态决定。

每天收盘后，策略根据当前浮盈对应的 `R` 值更新 `current_stop`。`current_stop` 只会上移，不会下移。

| Holding state | Stop update |
| --- | --- |
| 盈利未达到 1R | `current_stop` 保持为初始结构/ATR 止损 |
| 盈利达到 1R | `current_stop = max(current_stop, entry_price)`，把止损抬到成本附近 |
| 盈利达到 2R | `current_stop = max(current_stop, EMA20, close - 2.0 * ATR20)` |
| 盈利达到 3R 且价格明显远离 EMA20 | 若 `dist_ema20 > 10%`，则 `current_stop` 至少抬到 `EMA20` |

#### 4.4.6 退出条件

退出信号同样在 `T` 日收盘后判断，实际卖出安排在 `T+1` 交易日开盘。若 `T+1` 开盘价触发近似跌停限制，即 `open <= prev_close * (1 - limit_threshold)`，该卖出订单会被跳过，等待后续日期重新触发。

| Priority | Exit reason | Condition | Meaning |
| --- | --- | --- | --- |
| 1 | `stop_loss` or `trailing_stop` | `close <= current_stop` | 先执行硬风控；若 `current_stop >= entry_price`，记为 `trailing_stop`，否则记为 `stop_loss` |
| 2 | `time_stop` | `holding_days >= 10` 且 `close <= entry_price` | 买入后一段时间仍不赚钱，则释放资金 |
| 3 | `ema60_exit` | `close < EMA60` | 中期趋势破坏，退出剩余趋势仓位 |
| 4 | `end_of_backtest` | 回测结束后第一个交易日开盘强制平仓 | 只用于结算回测期末仍持有的仓位 |

#### 4.4.7 本次回测中的实际表现

`layered_exit` 共完成 `134` 笔交易，其中突破型 `22` 笔，回踩型 `112` 笔；胜率 `42.54%`，成本后收益 `41.89%`，最大回撤 `-8.63%`。

本版本的设计目标不是追求最高单次收益，而是用分层退出减少趋势利润回吐和组合回撤。和 `ema_state_only` 相比，它牺牲了一部分总收益，但把最大回撤从 `-21.04%` 降到 `-8.63%`。

## 5. Candidate Funnel And Regime Diagnostics

| Stage | Avg daily count | Median | Max | Days active |
| --- | --- | --- | --- | --- |
| ema_state | 65.32 | 61 | 168 | 2,253 |
| market_ok_entry | 39.49 | 0 | 168 | 1,020 |
| width_ok_entry | 30.34 | 0 | 168 | 712 |
| industry_ok_entry | 14.77 | 0 | 122 | 674 |
| trend_score_top20_entry | 2.83 | 0 | 24 | 673 |
| breakout_entry | 0.09 | 0 | 5 | 163 |
| pullback_entry | 0.45 | 0 | 13 | 403 |
| combined_entry | 0.54 | 0 | 13 | 453 |

- Candidate table rows: `2,263` trading days.
- Score table rows: `147,824` stock-day candidate rows.
- Signal table rows: `147,824` stock-day signal rows.

### 5.1 Market And Breadth State

| Metric | Value |
| --- | --- |
| Broad-market trend-ok days | 1,020 |
| Broad-market trend-ok ratio | 45.07% |
| Width-ok days | 793 |
| Width-ok ratio | 35.04% |
| Average close > EMA60 breadth | 50.17% |
| Average EMA20 > EMA60 breadth | 51.58% |

Market target regime summary:

| Target | Name | Days | Trend-ok ratio | Avg ret60 | Source |
| --- | --- | --- | --- | --- | --- |
| broad_market | 沪深300 | 2,263 | 45.07% | 1.23% | tushare.index_daily |
| growth_board_spread | 创业板指 | 2,263 | 33.80% | 2.57% | tushare.index_daily |
| mid_cap_spread | 中证500 | 2,263 | 27.57% | 1.20% | tushare.index_daily |
| small_cap_spread | 中证1000 | 2,263 | 25.63% | 0.58% | tushare.index_daily |

### 5.2 Industry Regime Extremes

| Target | Industry | Days | Trend-ok ratio | Avg ret60 |
| --- | --- | --- | --- | --- |
| sw_801120 | 食品饮料 | 2,263 | 36.19% | 2.84% |
| sw_801110 | 家用电器 | 2,263 | 36.15% | 1.99% |
| sw_801080 | 电子 | 2,263 | 34.95% | 3.39% |
| sw_801730 | 电力设备 | 2,263 | 34.91% | 2.98% |
| sw_801770 | 通信 | 2,263 | 33.89% | 3.12% |
| sw_801230 | 综合 | 2,263 | 30.53% | 1.78% |
| sw_801050 | 有色金属 | 2,263 | 30.36% | 3.63% |
| sw_801030 | 基础化工 | 2,263 | 28.59% | 1.70% |

Lowest industry trend-ok ratios:

| Target | Industry | Days | Trend-ok ratio | Avg ret60 |
| --- | --- | --- | --- | --- |
| sw_801170 | 交通运输 | 2,263 | 10.03% | -0.34% |
| sw_801180 | 房地产 | 2,263 | 12.42% | -1.61% |
| sw_801200 | 商贸零售 | 2,263 | 14.54% | -1.56% |
| sw_801720 | 建筑装饰 | 2,263 | 15.33% | -0.66% |
| sw_801130 | 纺织服饰 | 2,263 | 15.69% | -1.52% |
| sw_801970 | 环保 | 2,263 | 18.12% | -0.95% |
| sw_801160 | 公用事业 | 2,263 | 18.16% | -0.03% |
| sw_801040 | 钢铁 | 2,263 | 20.59% | 0.66% |

### 5.3 Theme State

Theme state is recorded for style diagnostics only. It is not used as a hard stock membership filter in phase one.

| Theme | Name | Days | Trend-ok ratio | Avg ret60 | Source |
| --- | --- | --- | --- | --- | --- |
| ai | 中证人工智能主题指数 | 2,263 | 30.89% | 3.14% | tushare.index_daily |
| central_soe | 中证中央企业综合指数 | 2,263 | 13.92% | 0.91% | tushare.index_daily |
| dividend | 中证红利指数 | 409 | 7.58% | -0.13% | tushare.index_daily |
| new_energy | 中证内地新能源主题指数 | 2,263 | 34.16% | 3.02% | tushare.index_daily |

## 6. Ablation Results

### 6.1 Main Ablation Table

| Version | Trades | Win rate | Return after cost | Return before cost | Annual after cost | Max drawdown | Ret/DD | Avg turnover | Ending account |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ema_state_only | 289 | 31.49% | 54.72% | 58.44% | 41.17% | -21.04% | 1.96 | 0.0758 | 1,547,168.08 |
| market_filter | 191 | 31.41% | 47.63% | 49.82% | 36.03% | -19.36% | 1.86 | 0.0470 | 1,476,331.13 |
| market_width | 116 | 34.48% | 50.88% | 52.32% | 38.39% | -16.45% | 2.33 | 0.0298 | 1,508,816.62 |
| industry_theme_state | 116 | 34.48% | 50.88% | 52.32% | 38.39% | -16.45% | 2.33 | 0.0298 | 1,508,816.62 |
| trend_score_top20 | 112 | 37.50% | 44.80% | 46.16% | 33.97% | -16.11% | 2.11 | 0.0293 | 1,448,004.73 |
| breakout_entry | 45 | 40.00% | 22.25% | 22.77% | 17.20% | -9.21% | 1.87 | 0.0132 | 1,222,478.95 |
| pullback_entry | 98 | 38.78% | 35.19% | 36.38% | 26.90% | -13.86% | 1.94 | 0.0275 | 1,351,912.37 |
| atr_structure_stop | 100 | 40.00% | 45.34% | 46.61% | 34.36% | -15.56% | 2.21 | 0.0273 | 1,453,375.25 |
| layered_exit | 134 | 42.54% | 41.89% | 43.62% | 31.83% | -8.63% | 3.69 | 0.0381 | 1,418,864.30 |

### 6.2 Incremental Interpretation

| Version | Comparison | Return delta | Drawdown delta | Trade delta |
| --- | --- | --- | --- | --- |
| ema_state_only | baseline | NA | NA | NA |
| market_filter | after ema_state_only | -7.08% | 1.68% | -98 |
| market_width | after market_filter | 3.25% | 2.92% | -75 |
| industry_theme_state | after market_width | 0.00% | 0.00% | 0 |
| trend_score_top20 | after industry_theme_state | -6.08% | 0.34% | -4 |
| breakout_entry | after trend_score_top20 | -22.55% | 6.90% | -67 |
| pullback_entry | after breakout_entry | 12.94% | -4.65% | 53 |
| atr_structure_stop | after pullback_entry | 10.15% | -1.71% | 2 |
| layered_exit | after atr_structure_stop | -3.45% | 6.94% | 34 |

### 6.3 Annual / Partial-Year Performance

| Version | Year | Return | Max drawdown | Avg turnover | Cost sum | Ending account |
| --- | --- | --- | --- | --- | --- | --- |
| ema_state_only | 2025 | 43.48% | -16.91% | 0.0717 | 18,041.81 | 1,434,818.19 |
| ema_state_only | 2026 | 7.83% | -21.04% | 0.0889 | 10,166.10 | 1,547,168.08 |
| market_filter | 2025 | 36.68% | -13.98% | 0.0511 | 12,782.05 | 1,366,768.94 |
| market_filter | 2026 | 8.02% | -19.36% | 0.0337 | 4,194.83 | 1,476,331.13 |
| market_width | 2025 | 40.28% | -14.12% | 0.0343 | 8,740.62 | 1,402,822.38 |
| market_width | 2026 | 7.56% | -16.45% | 0.0151 | 2,554.76 | 1,508,816.62 |
| industry_theme_state | 2025 | 40.28% | -14.12% | 0.0343 | 8,740.62 | 1,402,822.38 |
| industry_theme_state | 2026 | 7.56% | -16.45% | 0.0151 | 2,554.76 | 1,508,816.62 |
| trend_score_top20 | 2025 | 32.62% | -12.45% | 0.0341 | 8,605.63 | 1,326,177.36 |
| trend_score_top20 | 2026 | 9.19% | -16.11% | 0.0141 | 2,299.63 | 1,448,004.73 |
| breakout_entry | 2025 | 19.45% | -8.17% | 0.0131 | 3,358.56 | 1,194,546.43 |
| breakout_entry | 2026 | 2.34% | -9.21% | 0.0134 | 1,472.48 | 1,222,478.95 |
| pullback_entry | 2025 | 26.41% | -13.47% | 0.0315 | 8,326.06 | 1,264,108.95 |
| pullback_entry | 2026 | 6.95% | -13.86% | 0.0147 | 2,096.59 | 1,351,912.37 |
| atr_structure_stop | 2025 | 35.66% | -12.90% | 0.0299 | 8,052.40 | 1,356,558.60 |
| atr_structure_stop | 2026 | 7.14% | -15.56% | 0.0192 | 2,807.35 | 1,453,375.25 |
| layered_exit | 2025 | 37.78% | -8.47% | 0.0430 | 12,633.59 | 1,377,823.40 |
| layered_exit | 2026 | 2.98% | -8.63% | 0.0227 | 2,743.10 | 1,418,864.30 |

## 7. Trade Diagnostics

### 7.1 Entry-Type Statistics

| Version | Entry type | Trades | Win rate | Avg net return | Avg gross return | Avg holding days | Sum net return |
| --- | --- | --- | --- | --- | --- | --- | --- |
| atr_structure_stop | breakout | 16 | 56.25% | 11.58% | 11.82% | 57.5 | 185.30% |
| atr_structure_stop | pullback | 84 | 36.90% | 7.92% | 8.13% | 43.2 | 665.05% |
| breakout_entry | breakout | 45 | 40.00% | 10.20% | 10.42% | 51.2 | 459.17% |
| ema_state_only | ema_state | 289 | 31.49% | 4.26% | 4.47% | 31.7 | 1229.81% |
| industry_theme_state | ema_state | 116 | 34.48% | 8.85% | 9.07% | 46.1 | 1026.23% |
| layered_exit | breakout | 22 | 50.00% | 8.20% | 8.42% | 40.8 | 180.47% |
| layered_exit | pullback | 112 | 41.07% | 6.02% | 6.23% | 20.0 | 674.47% |
| market_filter | ema_state | 191 | 31.41% | 5.01% | 5.22% | 35.3 | 957.10% |
| market_width | ema_state | 116 | 34.48% | 8.85% | 9.07% | 46.1 | 1026.23% |
| pullback_entry | pullback | 98 | 38.78% | 7.65% | 7.87% | 43.6 | 749.98% |
| trend_score_top20 | ema_state | 112 | 37.50% | 8.03% | 8.25% | 47.9 | 899.85% |

### 7.2 Exit Reason Statistics

| Version | Exit reason | Trades | Win rate | Avg net return | Avg gross return | Avg holding days | Sum net return |
| --- | --- | --- | --- | --- | --- | --- | --- |
| atr_structure_stop | ema60_exit | 37 | 94.59% | 28.33% | 28.59% | 97.5 | 1048.17% |
| atr_structure_stop | stop_loss | 21 | 0.00% | -5.63% | -5.44% | 7.0 | -118.23% |
| atr_structure_stop | time_stop | 42 | 11.90% | -1.89% | -1.70% | 18.8 | -79.59% |
| breakout_entry | ema60_exit | 18 | 88.89% | 30.45% | 30.71% | 100.4 | 548.06% |
| breakout_entry | stop_loss | 5 | 0.00% | -9.89% | -9.71% | 7.2 | -49.46% |
| breakout_entry | time_stop | 22 | 9.09% | -1.79% | -1.60% | 20.8 | -39.43% |
| ema_state_only | ema60_exit | 93 | 62.37% | 17.64% | 17.88% | 63.8 | 1640.94% |
| ema_state_only | end_of_backtest | 20 | 90.00% | 13.14% | 13.37% | 17.2 | 262.82% |
| ema_state_only | stop_loss | 38 | 0.00% | -10.61% | -10.43% | 9.4 | -403.31% |
| ema_state_only | time_stop | 138 | 10.87% | -1.96% | -1.76% | 18.4 | -270.64% |
| industry_theme_state | ema60_exit | 44 | 84.09% | 29.07% | 29.33% | 92.5 | 1278.99% |
| industry_theme_state | stop_loss | 9 | 0.00% | -9.76% | -9.58% | 8.4 | -87.83% |
| industry_theme_state | time_stop | 63 | 4.76% | -2.62% | -2.42% | 19.0 | -164.93% |
| layered_exit | ema60_exit | 6 | 50.00% | -2.29% | -2.10% | 37.5 | -13.76% |
| layered_exit | stop_loss | 26 | 0.00% | -5.89% | -5.70% | 6.9 | -153.15% |
| layered_exit | time_stop | 40 | 15.00% | -2.63% | -2.44% | 14.7 | -105.28% |
| layered_exit | trailing_stop | 62 | 77.42% | 18.18% | 18.42% | 34.6 | 1127.12% |
| market_filter | ema60_exit | 56 | 78.57% | 23.77% | 24.01% | 82.4 | 1330.92% |
| market_filter | end_of_backtest | 20 | 55.00% | 4.00% | 4.21% | 8.2 | 80.00% |
| market_filter | stop_loss | 19 | 0.00% | -11.19% | -11.01% | 10.0 | -212.60% |
| market_filter | time_stop | 96 | 5.21% | -2.51% | -2.32% | 18.4 | -241.21% |
| market_width | ema60_exit | 44 | 84.09% | 29.07% | 29.33% | 92.5 | 1278.99% |
| market_width | stop_loss | 9 | 0.00% | -9.76% | -9.58% | 8.4 | -87.83% |
| market_width | time_stop | 63 | 4.76% | -2.62% | -2.42% | 19.0 | -164.93% |
| pullback_entry | ema60_exit | 32 | 96.88% | 30.53% | 30.79% | 101.1 | 976.98% |
| pullback_entry | stop_loss | 10 | 0.00% | -9.40% | -9.22% | 7.1 | -93.98% |
| pullback_entry | time_stop | 56 | 12.50% | -2.38% | -2.18% | 17.3 | -133.03% |
| trend_score_top20 | ema60_exit | 43 | 90.70% | 26.03% | 26.28% | 95.6 | 1119.12% |
| trend_score_top20 | end_of_backtest | 1 | 100.00% | 44.44% | 44.73% | 121.0 | 44.44% |
| trend_score_top20 | stop_loss | 10 | 0.00% | -9.84% | -9.66% | 7.8 | -98.38% |
| trend_score_top20 | time_stop | 58 | 3.45% | -2.85% | -2.66% | 18.3 | -165.32% |

### 7.3 Layered Strategy Trade Detail

| Entry type | Trades | Win rate | Avg net return | Avg gross return | Avg holding days | Sum net return |
| --- | --- | --- | --- | --- | --- | --- |
| breakout | 22 | 50.00% | 8.20% | 8.42% | 40.8 | 180.47% |
| pullback | 112 | 41.07% | 6.02% | 6.23% | 20.0 | 674.47% |

Top layered-exit instruments by summed net trade return:

| Instrument | Name | Industry | Trades | Win rate | Avg net | Sum net | Avg holding |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SZ002837 | 英维克 | 机械设备 | 1 | 100.00% | 116.22% | 116.22% | 43.0 |
| SH600673 | 东阳光 | 综合 | 1 | 100.00% | 95.92% | 95.92% | 78.0 |
| SZ000426 | 兴业银锡 | 有色金属 | 2 | 100.00% | 37.66% | 75.31% | 48.5 |
| SH603993 | 洛阳钼业 | 有色金属 | 5 | 60.00% | 14.35% | 71.74% | 23.0 |
| SZ002558 | 巨人网络 | 传媒 | 1 | 100.00% | 64.46% | 64.46% | 75.0 |
| SH600183 | 生益科技 | 电子 | 1 | 100.00% | 61.35% | 61.35% | 58.0 |
| SH601168 | 西部矿业 | 有色金属 | 1 | 100.00% | 56.84% | 56.84% | 130.0 |
| SH600143 | 金发科技 | 基础化工 | 1 | 100.00% | 56.55% | 56.55% | 48.0 |
| SZ002602 | 世纪华通 | 传媒 | 1 | 100.00% | 48.37% | 48.37% | 54.0 |
| SH603799 | 华友钴业 | 有色金属 | 2 | 50.00% | 19.61% | 39.21% | 45.0 |
| SZ000988 | 华工科技 | 机械设备 | 2 | 100.00% | 17.54% | 35.09% | 31.0 |
| SZ002738 | 中矿资源 | 有色金属 | 1 | 100.00% | 29.94% | 29.94% | 34.0 |
| SH603259 | 药明康德 | 医药生物 | 3 | 33.33% | 9.89% | 29.66% | 16.0 |
| SZ000657 | 中钨高新 | 有色金属 | 3 | 33.33% | 9.16% | 27.49% | 15.0 |
| SZ002466 | 天齐锂业 | 有色金属 | 1 | 100.00% | 24.30% | 24.30% | 63.0 |

Layered-exit exit reason counts:

| Exit reason | Count |
| --- | --- |
| trailing_stop | 62 |
| time_stop | 40 |
| stop_loss | 26 |
| ema60_exit | 6 |

## 8. Core Findings

- Best cost-after version by total return: `ema_state_only` with `54.72%`.
- Final layered strategy cost-after return: `41.89%`, max drawdown: `-8.63%`, trades: `134`.
- Breakout trades: `22`, pullback trades: `112`.
- Cost-after returns remain positive in the tested variants, but the highest-return baseline also has the largest drawdown; the layered version mainly improves drawdown and trade quality, not raw return.
- Meta-labeling is worth a later Explore3 phase only after validating that the lower-drawdown rule variants remain stable under fresh dates or stricter train/valid parameter selection.

## 9. Bias, Caveats, And What Needs Attention

- Phase one uses the Explore1 static large-cap mainboard universe. This accepts survivor bias and future-function risk for workflow and rule-structure validation.
- The static universe is not point-in-time. It should not be interpreted as an investable historical universe without additional survivorship-bias controls.
- Target histories and SW2021 membership are cached under Explore3. Stock daily bars are not refetched or backfilled in Explore3.
- SW2021 membership uses active `tushare.index_member` rows because `tushare.index_weight` returned empty for SW industry indexes in this environment.
- Theme state is reported as an index-level style regime only; it is not a stock membership filter.
- Market, industry, and theme target lists are fixed by `requirement.md`; the implementation does not auto-extend them.
- The backtest engine is a deterministic pandas state machine backed by Qlib data. It is not Qlib `TopkDropoutStrategy`, because this experiment requires trade-level stop, R, entry type, and exit-reason accounting.
- Costs are constant approximations across the whole backtest period. A production-grade study should use date-aware fees and tax assumptions.
- Limit handling uses a mainboard-style `limit_threshold=0.095`; this is acceptable only because the Explore1 universe is intended to be mainboard A shares.
- Results should be treated as exploratory if rules are changed after inspecting the 2025-2026 test window.

## 10. Files Produced

| Path | Exists | Bytes |
| --- | --- | --- |
| `Explore3/data/targets/industry_membership.csv` | yes | 422,592 |
| `Explore3/data/targets/industry_membership_status.csv` | yes | 1,866 |
| `Explore3/data/targets/industry_targets.csv` | yes | 1,278 |
| `Explore3/data/targets/market_targets.csv` | yes | 367 |
| `Explore3/data/targets/target_fetch_status.csv` | yes | 3,093 |
| `Explore3/data/targets/target_history.csv` | yes | 10,648,602 |
| `Explore3/data/targets/theme_targets.csv` | yes | 418 |
| `Explore3/data/universe/mcap500_mainboard_20251231.csv` | yes | 33,590 |
| `Explore3/data/universe/qlib_mcap500_mainboard_20251231.txt` | yes | 8,742 |
| `Explore3/outputs/backtests/atr_structure_stop/portfolio_daily.csv` | yes | 36,248 |
| `Explore3/outputs/backtests/atr_structure_stop/trade_detail.csv` | yes | 33,228 |
| `Explore3/outputs/backtests/breakout_entry/portfolio_daily.csv` | yes | 32,257 |
| `Explore3/outputs/backtests/breakout_entry/trade_detail.csv` | yes | 14,908 |
| `Explore3/outputs/backtests/ema_state_only/portfolio_daily.csv` | yes | 44,217 |
| `Explore3/outputs/backtests/ema_state_only/trade_detail.csv` | yes | 94,979 |
| `Explore3/outputs/backtests/industry_theme_state/portfolio_daily.csv` | yes | 37,234 |
| `Explore3/outputs/backtests/industry_theme_state/trade_detail.csv` | yes | 38,340 |
| `Explore3/outputs/backtests/layered_exit/portfolio_daily.csv` | yes | 36,408 |
| `Explore3/outputs/backtests/layered_exit/trade_detail.csv` | yes | 44,515 |
| `Explore3/outputs/backtests/market_filter/portfolio_daily.csv` | yes | 40,193 |
| `Explore3/outputs/backtests/market_filter/trade_detail.csv` | yes | 63,070 |
| `Explore3/outputs/backtests/market_width/portfolio_daily.csv` | yes | 37,234 |
| `Explore3/outputs/backtests/market_width/trade_detail.csv` | yes | 38,340 |
| `Explore3/outputs/backtests/pullback_entry/portfolio_daily.csv` | yes | 36,297 |
| `Explore3/outputs/backtests/pullback_entry/trade_detail.csv` | yes | 32,417 |
| `Explore3/outputs/backtests/trend_score_top20/portfolio_daily.csv` | yes | 37,076 |
| `Explore3/outputs/backtests/trend_score_top20/trade_detail.csv` | yes | 37,223 |
| `Explore3/outputs/cache/stock_indicators.pkl` | yes | 126,506,364 |
| `Explore3/outputs/cache/stock_panel.pkl` | yes | 28,181,244 |
| `Explore3/outputs/cache/stock_signals.pkl` | yes | 214,042,444 |
| `Explore3/outputs/reports/benchmark_comparison.csv` | yes | 729 |
| `Explore3/outputs/reports/daily_candidates.csv` | yes | 110,262 |
| `Explore3/outputs/reports/daily_scores.csv` | yes | 22,099,199 |
| `Explore3/outputs/reports/data_quality_report.csv` | yes | 12,670 |
| `Explore3/outputs/reports/explore1_cache_coverage.csv` | yes | 12,670 |
| `Explore3/outputs/reports/explore3_report.md` | yes | 31,573 |
| `Explore3/outputs/reports/explore3_verification_report.md` | yes | 2,365 |
| `Explore3/outputs/reports/fat_tail_stress.csv` | yes | 1,124 |
| `Explore3/outputs/reports/group_stability.csv` | yes | 43,927 |
| `Explore3/outputs/reports/industry_filter_audit.csv` | yes | 207,192 |
| `Explore3/outputs/reports/industry_regime.csv` | yes | 17,130,678 |
| `Explore3/outputs/reports/limit_skip_audit.csv` | yes | 2,956 |
| `Explore3/outputs/reports/market_regime.csv` | yes | 2,876,652 |
| `Explore3/outputs/reports/market_width.csv` | yes | 131,154 |
| `Explore3/outputs/reports/monthly_returns.csv` | yes | 3,816 |
| `Explore3/outputs/reports/order_execution_audit.csv` | yes | 289,602 |
| `Explore3/outputs/reports/portfolio_reconciliation.csv` | yes | 871 |
| `Explore3/outputs/reports/rolling_risk_report.csv` | yes | 497,950 |
| `Explore3/outputs/reports/signal_execution_audit.csv` | yes | 204,214 |
| `Explore3/outputs/reports/signals.csv` | yes | 28,933,660 |
| `Explore3/outputs/reports/theme_regime.csv` | yes | 1,997,261 |
| `Explore3/outputs/reports/trade_detail.csv` | yes | 413,672 |
| `Explore3/outputs/reports/trend_rule_ablation_summary.csv` | yes | 3,220 |
| `Explore3/reports/explore3_report.md` | yes | 31,573 |

## 11. Next-Step Recommendation

- Do not move directly to a large model search from this result alone.
- First rerun the same pipeline after adding fresh dates, then compare whether lower drawdown from `layered_exit` survives.
- If the result is stable, the natural next extension is meta-labeling on EMA candidates: predict whether a candidate has enough forward R-adjusted payoff to justify the trade.
- If the result is not stable, focus on parameter discipline and point-in-time universe/industry membership before adding models.

