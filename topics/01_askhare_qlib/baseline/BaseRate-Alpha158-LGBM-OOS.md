# BaseRate-Alpha158-LGBM-OOS 研究需求

> 文件名：`BaseRate-Alpha158-LGBM-OOS.md`
> 阶段：`BaseRate-1` / `BR-Alpha158-LGBM-OOS`
> 标题：PIT Broad-Universe Alpha158 + LightGBM After-Cost OOS Baseline
> 状态：implementation-ready requirement
> 生成日期：2026-05-08
> 重要说明：本阶段不是 primitive discovery、不是事件研究、不是 P1 refine、不是最终策略冻结。它只回答一个基础问题：**PIT 宽基 universe 下的朴素 Alpha158 + LightGBM，在真实交易约束和成本下，是否存在可用的 OOS base rate。**

---

## 0. 一句话结论

当前项目应先把 Explore10 系列 primitive / path-to-primitive / 行业单点事件研究降为次级路线，优先回到一个最朴素、可复现、可比较的 PIT 宽基 ML 基线：

```text
PIT broad universe
+ Alpha158 feature set
+ LightGBM ranking / regression model
+ TopK / TopKDropout long-only portfolio
+ next-open execution
+ A 股真实成本与成交约束
+ 2024 / 2025 OOS after-cost backtest
```

本阶段的目标不是找一个最终策略，而是建立 **base rate**：

```text
在不做行业切分、不做 launch/failure event、不做 primitive search、不做手工 gate 的情况下，
最朴素的 Alpha158 + LGBM pipeline 能否在 OOS、含成本、含成交约束下跑赢合理基准？
```

只有先回答这个问题，后续的 failure overlay、risk filter、event-regime cohort、primitive 或更复杂模型研究才有比较锚点。

---

## 1. 前因后果

### 1.1 为什么要从 Explore10 系列收口

Explore9 到 Explore10 的路线本来是：

```text
先理解大 winner 的可观察结构
-> 再拆 launch / entry / failure / hold
-> 再用 gate / LGBM / primitive 寻找可审计结构
-> 最后才可能进入 formal hypothesis 或回测
```

这条路线在早期是合理的，因为它帮助排除了很多看起来有效但实际不稳的方向。但到 Explore10 后，主线 primitive 研究已经明显进入边际收益很低的状态：

```text
P0.6: delayed entry trigger 全部失败，不能证明“等确认再入场”更好。
P0.8: gate + LGBM 有 discovery lead，但没有 P1 candidate，也没有 clean OOS proof。
P0.9B: 行业 LGBM 到手工 primitive 转写失败，0 个 primitive 进入下一阶段。
Explore10: atomic feature bank / path-to-primitive 没有产生 next-stage seed。
Explore10A: 汽车单行业路线被样本宽度问题阻断。
Explore10D: 电子 launch risk-filter 只留下 manual review 窄口，不证明 primitive 可交易。
```

因此继续把 Explore10E / manual formula review / 更细 primitive 需求作为主线推进，风险是：

```text
把负向结果不断改名解释；
不断扩大 search space；
不断生成 audit artifact；
但始终没有一个可交易 base rate 锚点。
```

这不是否定 Explore10D 的窄口结论：Explore10D 允许继续人工复核电子 launch risk-filter primitive，但它不能替代本阶段的 PIT 宽基 after-cost OOS base-rate 锚点。

### 1.2 P0.6 的教训：入场 trigger 不是当前主线

P0.6 的价值不是发现入场规则，而是排除了一个容易误判的方向：

```text
如果只看单笔 precision，部分 hold / pullback trigger 看起来有用；
但加入 direct baseline、convertible direct baseline、instrument-year、missed winner 后，25 个 entry trigger 全部失败。
```

因此，本阶段不得继续从：

```text
launch 后等 3/5/10/20 日确认再入场
pullback 后再入场
higher-low 后再入场
strict close hold 后再入场
```

这些方向寻找主 baseline。它们最多是 future risk / hold / add-on overlay 的候选，不是 BaseRate 阶段的核心。

### 1.3 P0.8 / P0.9 的教训：LGBM 有预测痕迹，但不能直接等于策略

P0.8 说明 LGBM 对 launch / failure 有一些可见预测力，尤其 failure 方向更像风险识别；但它没有通过 P1 candidate gate，也没有 clean OOS proof。P0.9 / P0.9A / P0.9B 进一步证明：

```text
行业专用模型最初合同不可训练；
T1 下汽车 / 电子可以作为 diagnostic probe；
但 LGBM 的树路径不能安全转写成手工 primitive；
行业 / regime / instrument-year concentration 与 null / placebo 是硬问题。
```

因此，BaseRate 阶段不再问：

```text
LGBM 是否能解释某个行业 / launch / failure primitive？
```

而只问：

```text
LGBM 作为 PIT 宽基横截面打分器，在正常 ML 回测链路里，是否能产生 after-cost OOS base rate？
```

### 1.4 Explore10 / 10A / 10D 的教训：primitive 研究缺少基线锚点

Explore10 使用 Alpha158-like atomic feature bank 和 LGBM path-to-primitive，希望把更底层的 feature path 转成 audited primitive。但最终：

```text
汽车主任务没有可训练 locked LGBM probe；
99 个 primitive candidate 全部来自电子 placebo / weak-signal scope；
没有任何 atomic_primitive_candidate_for_next_requirement = true；
feature bank v1 missing / duplicate 问题严重；
电子 placebo 产生 stable-looking candidate，说明 search-bias 风险很真实。
```

Explore10A 又进一步证明，汽车单行业样本宽度是关键瓶颈。这意味着：

```text
继续单行业 path-to-primitive，不是当前最高性价比方向。
```

Explore10D 保留了一个更窄的电子 launch risk-filter manual review 方向，但这个方向的边界是：

```text
可以作为后续人工公式复核候选；
不能写成 validated primitive；
不能写成可交易策略；
不能替代全局 base-rate 测试。
```

下一步应回到最朴素的 PIT 宽基回测：

```text
先跑出一个可审计的 PIT 宽基 Alpha158 + LGBM after-cost OOS baseline；
再决定是否值得继续做 failure overlay、risk filter、event-regime cohort 或 primitive discovery。
```

---

## 2. 阶段定位

BaseRate-Alpha158-LGBM-OOS 是 `base-rate establishment phase`。

它不是：

```text
primitive discovery
launch winner trigger discovery
failure primitive discovery
行业专用模型
P1 validation
最终策略回测
模型部署
参数搜索竞赛
```

它是：

```text
最小可交易 ML pipeline 的真实 OOS 基线测试。
```

BaseRate 阶段允许输出：

```text
baseline_positive_after_cost
baseline_negative_after_cost
baseline_inconclusive_due_to_data_or_execution
proceed_to_risk_filter_overlay_research
proceed_to_factor_regime_cohort_research
stop_primitive_discovery_until_positive_base_rate
fix_data_or_backtest_infra_before_research
```

BaseRate 阶段禁止输出：

```text
primitive_candidate = true
candidate_for_p1_strategy = true
validated_model = true
production_model = true
selected_final_strategy = true
freeze_strategy = true
```

---

## 3. 核心研究问题

BaseRate 必须回答以下问题。

### 3.1 PIT 宽基 Alpha158 + LGBM 是否有 after-cost OOS base rate？

主问题：

```text
在 PIT 宽基 universe 中，使用 Alpha158 特征和 LightGBM 预测横截面收益，
通过 TopK / TopKDropout long-only portfolio，
在 next-open 执行、真实交易成本、T+1、涨跌停/停牌不可成交约束下，
2024 / 2025 OOS 是否能跑赢合理基准？
```

### 3.2 收益是否能覆盖成本和换手？

必须拆分：

```text
gross return
commission cost
stamp tax
slippage cost
limit/suspension execution loss
turnover drag
net return
```

如果 gross 有 alpha，但 net 被成本吃掉，结论必须是：

```text
predictive_but_not_tradable_under_current_turnover
```

### 3.3 结果是否稳定，还是单一年份 / 单一风格驱动？

至少按以下维度拆分：

```text
calendar year
market regime
size bucket
turnover bucket
volatility bucket
industry bucket only as audit, not selection
```

### 3.4 BaseRate 是否足以支持后续研究？

如果 PIT 宽基 baseline 成立，后续可以研究：

```text
risk filter overlay
failure / drawdown avoidance primary task
factor-regime cohort
capacity / turnover-aware strategy refinement
```

如果 PIT 宽基 baseline 不成立，后续应优先检查：

```text
数据质量
label 对齐
交易成本模型
universe / liquidity filtering
model training contract
Alpha158 feature construction
```

而不是继续 primitive discovery。

---

## 4. Scope Lock

### 4.1 主任务

```text
model_task = pit_broad_universe_cross_sectional_return_prediction
model = LightGBM
feature_set = Alpha158
portfolio = long_only_topk / topk_dropout
execution = next_open
```

### 4.2 Universe

主 universe：

```text
PIT universe from existing project data
默认优先：data/universe/pit_mcap500_mainboard_daily.csv
```

Universe naming contract：

```text
本文中的 PIT 宽基 baseline 默认不是全 A 股市场；
默认实现范围是 mcap500 mainboard PIT universe；
报告标题、manifest、recommendation 不得把它写成 all-A-share full-market proof。
```

若项目已有 Qlib instrument 文件：

```text
data/universe/qlib_pit_mcap500_mainboard.txt
```

必须与 PIT universe membership 对齐。

不得使用：

```text
非 PIT universe
回测结果反选 universe
2024/2025 OOS 表现反选 universe
行业或主题筛选作为主 universe
```

### 4.3 Feature set

主 feature set：

```text
Alpha158
```

允许做 sensitivity：

```text
Alpha158 + simple cross-sectional rank normalization
Alpha158 + liquidity sanity features
```

但主报告必须先给出纯 Alpha158 结果。

禁止：

```text
使用 Explore10 path candidate feature 作为主特征
使用 primitive / launch / failure event label 作为 feature
使用历史交易结果作为 feature
使用 2024/2025 OOS 结果进行 feature selection
```

### 4.4 Model

主模型：

```text
primary_model_id = LGBM_REGRESSION_ALPHA158_FIXED_V1
model_class = qlib.contrib.model.gbdt.LGBModel
loss = mse
```

主实现必须固定一套 predeclared config。不得在 2024/2025 OOS 上调参。

Primary model parameters：

```yaml
primary_model_params:
  loss: mse
  colsample_bytree: 0.8879
  learning_rate: 0.0421
  subsample: 0.8789
  lambda_l1: 205.6999
  lambda_l2: 580.9768
  max_depth: 8
  num_leaves: 210
  num_threads: 20
  early_stopping_rounds: 50
  eval_metric: l2
  seed: 20260508
```

这些参数来自既有 Alpha158/LGBM baseline 配置，只作为固定 BaseRate 起点，不允许通过 2024/2025 OOS 表现修改。

允许 sensitivity：

```text
LGBM_RANKER_FIXED_V1
fixed_n_estimators vs early_stopping_on_train_validation_only
```

但不得用 OOS 表现选择最终模型。

---

## 5. 数据纪律

### 5.1 Time range

```text
research_start = 2017-07-04
research_end = 2025-12-31, if data available
canonical_data_start = 2017-07-04
canonical_data_end = 2026-04-30
```

说明：当前 canonical PIT universe 与 PIT Qlib provider 从 `2017-07-04` 开始。不得把 `2017-01-01..2017-07-03` 当作缺失错误；只能作为 pre-canonical unavailable period 记录。

如果 2025 数据不可用，报告必须写：

```text
2025_oos_not_available_reason
```

不得用 2026 数据做 selection。若 2026 数据存在，只能保留为 future robustness placeholder，不进入本阶段主结论。

Coverage gates：

```text
data_preflight_pass = true only if:
  pit_universe_min_date <= 2017-07-04
  pit_universe_max_date >= 2025-12-31
  provider_calendar_min_date <= 2017-07-04
  provider_calendar_max_date >= 2025-12-31
  benchmark_SH000300_available_for_all_test_dates = true
  fold_2021_train_partial_2017_status = expected_due_to_canonical_start
```

Alpha158 warmup rule：

```text
feature_warmup_start = canonical_data_start
first_eligible_signal_date = first date where all required Alpha158 rolling windows can be computed
rows before first_eligible_signal_date are warmup rows, not training samples
```

### 5.2 Fold design

主 walk-forward folds：

```text
fold_2021:
  train = 2017-2019
  valid = 2020
  test  = 2021

fold_2022:
  train = 2017-2020
  valid = 2021
  test  = 2022

fold_2023:
  train = 2017-2021
  valid = 2022
  test  = 2023

fold_2024:
  train = 2017-2022
  valid = 2023
  test  = 2024

fold_2025:
  train = 2017-2023
  valid = 2024
  test  = 2025
```

如果使用 `fold_2025`，valid=2024 只能用于该 fold 的 training early stopping / model fit control，不得用于修改 global strategy config、TopK、cost model 或 feature set。

Fold sample gates：

```text
each fold must report:
  raw_calendar_day_count
  raw_instrument_day_count
  eligible_feature_row_count
  eligible_label_row_count
  prediction_row_count
  missing_feature_rate
  missing_label_rate
  universe_membership_coverage_rate

fold_trainable = true only if:
  eligible_label_row_count > 0
  prediction_row_count > 0
  missing_feature_rate <= 0.30
  missing_label_rate <= 0.10
```

### 5.3 Anti-leakage

对每个样本：

```text
feature_asof_date = signal_date
signal_date = T 日收盘后可得特征日
execution_date = next_trading_day(signal_date)
execution_price_reference = next_open
```

禁止 predictive feature：

```text
execution_date high
execution_date low
execution_date close
execution_date volume
execution_date money
future return
future rank
future index / industry state
```

### 5.4 Label alignment

BaseRate 必须区分两类 label。

#### B0: Qlib-compatible short-horizon baseline

用于复现最朴素 Alpha158 + LGBM pipeline：

```text
LABEL_1D_Q = Ref(close, -2) / Ref(close, -1) - 1
```

语义：

```text
T 日特征
T+1 可买
T+2 close 相对 T+1 close 的变化
```

注意：实际回测仍以 next-open execution 和 portfolio engine 为准；label 只用于模型训练。

#### B1: Trading-aware 5D label

用于降低过度换手的 sensitivity baseline：

```text
LABEL_5D = Ref(close, -6) / Ref(close, -1) - 1
```

语义：

```text
T 日特征
T+1 可买
持有到 T+6 附近
```

#### B2: Trading-aware 10D label sensitivity

```text
LABEL_10D = Ref(close, -11) / Ref(close, -1) - 1
```

### 5.5 Label hierarchy

主报告必须按以下顺序呈现：

```text
1. B0 Qlib-compatible baseline
2. B1 5D trading-aware baseline
3. B2 10D sensitivity
```

不得只报告表现最好的 label。

### 5.6 Label / execution / realized-return separation

BaseRate 必须把三类口径分开记录，不能混用：

```text
training_label_return:
  用于训练 LightGBM 的监督目标；
  可以是 Qlib-compatible close-to-close label；
  不得直接解释为交易收益。

execution_return:
  用 next_open 可成交价格、T+1、涨跌停、停牌、成本和滑点计算；
  是 portfolio engine 的成交口径；
  必须作为 after-cost OOS 主结论来源。

diagnostic_ic_return:
  用于 rank_ic / prediction diagnostics；
  只解释模型排序能力；
  不得替代 portfolio after-cost return。
```

报告必须输出：

```text
label_definition_hash
execution_return_definition_hash
diagnostic_ic_return_definition_hash
label_execution_alignment_audit.csv
```

若训练 label 是 close-to-close，而执行收益是 next-open，报告必须显式标记：

```text
label_execution_price_basis_mismatch = true
mismatch_allowed_for_training_only = true
portfolio_conclusion_uses_execution_return_only = true
```

---

## 6. 交易与回测约束

### 6.1 Execution assumption

```text
信号生成：T 日收盘后
下单时间：T+1 next_open
买入成交价：T+1 open，若可成交
卖出成交价：T+1 open，若可成交
```

不得使用 same-close execution。

### 6.1.1 Portfolio target and order generation

每日目标组合生成规则：

```text
input_signal = prediction score with index [signal_date, instrument]
rank_date = signal_date
execution_date = next_trading_day(signal_date)
primary_portfolio = topk_50_dropout_5_daily
current_holding_set = holdings after previous execution_date close
target_candidate_set = top 50 instruments by score among PIT-eligible instruments
drop_set = lowest-ranked current holdings not in target_candidate_set, capped by n_drop = 5
buy_set = highest-ranked target candidates not currently held, capped by available slots after drops
sell_orders generated for drop_set
buy_orders generated for buy_set
```

Tie-breaks：

```text
score ties sort by instrument ascending
missing score instruments are ineligible for buy
current holdings with missing score are eligible to sell if they fall outside target set
```

### 6.1.2 Fill algorithm

执行日按以下顺序模拟：

```text
1. mark current holdings at execution_date open where open is available
2. execute sell orders first
3. blocked sells remain holding
4. available cash includes previous cash plus filled sell proceeds
5. execute buy orders with equal target weight among desired holdings
6. unfilled buy notional remains cash
7. end-of-day portfolio value uses execution_date close for holdings if available, otherwise last valid close with stale_price_flag = true
```

Order block rules：

```text
buy blocked if suspended_or_missing_open = true
buy blocked if zero_volume_or_money = true
buy blocked if limit_up_buy_block = true
sell blocked if suspended_or_missing_open = true
sell blocked if zero_volume_or_money = true
sell blocked if limit_down_sell_block = true
sell blocked if instrument not in PIT universe and forced_liquidation_allowed = false
```

Cash rule：

```text
sell_cash_reuse_same_execution_date = true
cash_return = 0
min_trade_cash = 0 unless configured
```

### 6.2 A 股交易约束

必须模拟：

```text
T+1 交易限制
停牌不可交易
涨停买入不可成交
跌停卖出不可成交
无成交量 / 无报价不可成交
股票不在当日 PIT universe 不可交易
```

涨跌停判断必须记录来源：

```text
limit_rule_source = exchange_board_metadata / inferred_board_rule / config_default
```

如果实现暂时无法精确识别不同板块涨跌停规则，必须至少做：

```text
limit_rule_sensitivity:
  conservative_limit_block
  relaxed_limit_block
```

并在报告中标记：

```text
limit_rule_precision_limitation = true
```

### 6.3 Cost model

主成本配置：

```yaml
cost_model:
  commission_buy: 0.001
  commission_sell: 0.001
  stamp_tax_sell: 0.0005
  slippage_buy: 0.0005
  slippage_sell: 0.0005
```

Sensitivity：

```yaml
cost_sensitivity:
  low:
    commission_buy: 0.0005
    commission_sell: 0.0005
    stamp_tax_sell: 0.0005
    slippage_buy: 0.0002
    slippage_sell: 0.0002
  base:
    commission_buy: 0.001
    commission_sell: 0.001
    stamp_tax_sell: 0.0005
    slippage_buy: 0.0005
    slippage_sell: 0.0005
  high:
    commission_buy: 0.001
    commission_sell: 0.001
    stamp_tax_sell: 0.001
    slippage_buy: 0.001
    slippage_sell: 0.001
```

报告不得只展示 low-cost 情况。

---

## 7. Portfolio construction

### 7.1 Primary strategy

主策略：

```text
long_only_topk_dropout
```

默认：

```yaml
portfolio_primary:
  topk: 50
  n_drop: 5
  rebalance: daily
  weight: equal_weight
  max_position_weight: 0.05
  cash_when_unfilled: true
```

解释：

```text
TopKDropout 比 daily full-rebalance 更接近可交易组合，能降低换手；
但仍保持足够朴素，作为 base rate 更合适。
```

### 7.2 Required sensitivity portfolios

必须同时报告：

```text
topk_20_dropout_2
topk_50_dropout_5
topk_100_dropout_10
topk_50_full_rebalance
topk_100_full_rebalance
weekly_rebalance_topk_50
```

禁止：

```text
根据 OOS 表现选择 best topK / best dropout / best rebalance。
```

### 7.3 Position and cash rules

```text
long-only
no leverage
no shorting
unfilled buy order remains cash
unfilled sell order remains holding until executable
cash earns zero return unless explicitly configured
```

---

## 8. Benchmarks

必须至少比较：

```text
1. HS300 / SH000300
2. PIT universe equal-weight benchmark
3. PIT universe market-cap-weight benchmark, if market cap is available
4. random same-turnover TopK portfolios
5. model score shuffled same-turnover portfolio
```

Random baseline：

```yaml
random_baseline:
  n_repeats: 200
  same_universe: true
  same_topk: true
  same_turnover_or_n_drop: true
  same_execution_constraints: true
  same_cost_model: true
```

报告必须回答：

```text
模型组合是否显著优于同换手随机组合？
```

---

## 9. Metrics

### 9.1 Primary metrics

主报告必须输出：

```text
net_annual_return
net_cumulative_return
max_drawdown
sharpe
calmar
annual_volatility
turnover_daily_mean
turnover_annualized
average_holding_days
cost_drag_annualized
slippage_drag_annualized
execution_block_rate
limit_up_buy_block_rate
limit_down_sell_block_rate
cash_drag
benchmark_excess_return
benchmark_tracking_error
information_ratio
```

### 9.2 Secondary metrics

```text
gross_annual_return
commission_paid
stamp_tax_paid
slippage_paid
trade_count
order_count
fill_rate
partial_or_blocked_order_count
win_rate
profit_loss_ratio
hit_rate_by_score_decile
rank_ic_mean
rank_ic_ir
prediction_coverage
```

Win rate 不得作为主成功指标。

### 9.3 Year-by-year reporting

必须按年度输出：

```text
2021
2022
2023
2024
2025, if available
```

每年都要有：

```text
return
max_drawdown
turnover
cost_drag
benchmark_excess
fill_rate
```

---

## 10. Data and artifact discipline

### 10.1 Project-level canonical data rule

为避免各 Explore 阶段重复维护基础数据，本项目从 BaseRate 起把可复用基础数据集中到根目录 `data/`。

Project-wide rule：

```text
data/ is the canonical reusable base-data root.
Explore*/data/ may keep historical run-local snapshots for reproducibility.
New requirements, configs, scripts, and reports must reference data/ first.
If a required reusable dataset only exists under Explore*/data/, it must be promoted or copied into data/ before being used by new work.
```

Tracking policy：

```text
Tracked canonical inputs:
  data/universe/*.csv
  data/universe/*.txt
  data/targets/*.csv
  data/qlib/cn_data_pit/**

Ignored/generated data:
  data/raw/**
  data/interim/**
  BaseRate/outputs/alpha158_lgbm_oos/cache/**
  any row-level experiment output not listed as a canonical input

Before commit:
  git check-ignore data/qlib/cn_data_pit/calendars/day.txt must return no match
  git check-ignore data/universe/pit_mcap500_mainboard_daily.csv must return no match
  git check-ignore BaseRate/outputs/alpha158_lgbm_oos/cache/feature_panel.parquet must return a match
```

If any canonical input exceeds repository limits or becomes operationally too large, the requirement must be amended to define a deterministic rebuild command and content hash before implementation proceeds.

已集中到 `data/` 的基础数据包括：

```text
data/universe/pit_mcap500_mainboard_daily.csv
data/universe/qlib_pit_mcap500_mainboard.txt
data/universe/pit_qlib_instrument_universe.csv
data/universe/mcap500_mainboard_20251231.csv
data/universe/qlib_mcap500_mainboard_20251231.txt
data/targets/pit_industry_membership.csv
data/targets/industry_targets.csv
data/targets/market_targets.csv
data/targets/theme_targets.csv
data/targets/target_history.csv
data/qlib/cn_data_pit/
```

Path policy：

```text
PIT universe path: data/universe/pit_mcap500_mainboard_daily.csv
PIT qlib instruments path: data/universe/qlib_pit_mcap500_mainboard.txt
PIT qlib provider path: data/qlib/cn_data_pit
PIT industry membership path: data/targets/pit_industry_membership.csv
Static Explore1-style universe path: data/universe/mcap500_mainboard_20251231.csv
```

Explore-local paths are allowed only as provenance fields or historical comparison inputs, not as the default path for new phases.

任何 promoted/copy 到 `data/` 的基础数据都必须能审计来源：

```text
canonical_path
source_explore_path
source_phase
copy_timestamp
file_size_bytes
content_hash
row_count_or_file_count
promoted_reason
```

### 10.2 Required report artifacts

```text
base_rate_run_manifest.json
base_rate_data_preflight_audit.csv
base_rate_canonical_data_audit.csv
base_rate_pit_universe_audit.csv
base_rate_feature_dictionary.csv
base_rate_label_dictionary.csv
base_rate_split_audit.csv
base_rate_feature_asof_leakage_audit.csv
base_rate_observed_reference_audit.csv
base_rate_model_config_audit.csv
base_rate_model_train_metric_by_fold.csv
base_rate_prediction_coverage_audit.csv
base_rate_portfolio_config_matrix.csv
base_rate_execution_constraint_audit.csv
base_rate_cost_model_audit.csv
base_rate_trade_summary_by_fold.csv
base_rate_portfolio_daily_summary.csv
base_rate_benchmark_comparison.csv
base_rate_random_same_turnover_baseline.csv
base_rate_cost_sensitivity.csv
base_rate_topk_sensitivity.csv
base_rate_capacity_proxy.csv
base_rate_year_by_year_metrics.csv
base_rate_failure_case_review.csv
base_rate_forbidden_selection_self_check.csv
BaseRate-Alpha158-LGBM-OOS-report.md
```

### 10.3 Required artifact schemas

These schemas are the minimum contract. Implementations may add columns but must not omit or rename required columns.

| artifact | row grain | required columns |
|---|---|---|
| `base_rate_run_manifest.json` | run | `phase`, `run_id`, `created_at`, `git_commit_hash`, `config_path`, `config_hash`, `provider_uri`, `output_root`, `recommendation`, `forbidden_output_violation_count` |
| `base_rate_data_preflight_audit.csv` | data source | `data_source`, `path`, `exists`, `min_date`, `max_date`, `row_count`, `file_count`, `content_hash`, `pass`, `blocked_reason` |
| `base_rate_canonical_data_audit.csv` | canonical input | `canonical_path`, `source_explore_path`, `source_phase`, `copy_timestamp`, `file_size_bytes`, `content_hash`, `row_count_or_file_count`, `promoted_reason`, `tracked_policy`, `pass` |
| `base_rate_pit_universe_audit.csv` | date | `date`, `pit_member_count`, `provider_member_count`, `intersection_count`, `missing_in_provider_count`, `extra_in_provider_count`, `coverage_rate`, `pass` |
| `base_rate_feature_dictionary.csv` | feature | `feature_name`, `feature_family`, `qlib_expression_or_source`, `lookback_window`, `uses_future_data`, `primary_allowed`, `sensitivity_allowed` |
| `base_rate_label_dictionary.csv` | label | `label_name`, `label_expression`, `training_role`, `decision_role`, `horizon_days`, `price_basis`, `hash`, `allowed_for_positive_decision` |
| `base_rate_split_audit.csv` | fold | `fold_id`, `train_start`, `train_end`, `valid_start`, `valid_end`, `test_start`, `test_end`, `eligible_feature_row_count`, `eligible_label_row_count`, `fold_trainable`, `pass` |
| `base_rate_feature_asof_leakage_audit.csv` | feature/fold | `fold_id`, `feature_name`, `feature_asof_date_rule`, `future_reference_detected`, `execution_date_field_used`, `pass` |
| `base_rate_observed_reference_audit.csv` | field | `field_name`, `used_in_feature`, `used_in_label`, `used_in_execution`, `observed_after_signal_date`, `allowed_role`, `pass` |
| `base_rate_model_config_audit.csv` | model/fold | `fold_id`, `model_id`, `model_class`, `param_hash`, `hyperparameter_search_used`, `oos_used_for_model_selection`, `early_stopping_segment`, `pass` |
| `base_rate_model_train_metric_by_fold.csv` | fold/label/model | `fold_id`, `label_name`, `model_id`, `train_row_count`, `valid_row_count`, `best_iteration`, `valid_metric`, `rank_ic_mean_valid`, `fit_status` |
| `base_rate_prediction_coverage_audit.csv` | fold/date | `fold_id`, `date`, `pit_member_count`, `prediction_count`, `missing_prediction_count`, `prediction_coverage`, `pass` |
| `base_rate_portfolio_config_matrix.csv` | portfolio config | `portfolio_id`, `label_name`, `topk`, `n_drop`, `rebalance`, `weight_method`, `decision_primary`, `sensitivity_role`, `predeclared` |
| `base_rate_execution_constraint_audit.csv` | date/order_side/block_reason | `date`, `side`, `block_reason`, `order_count`, `blocked_order_count`, `blocked_notional`, `block_rate`, `limit_rule_source` |
| `base_rate_cost_model_audit.csv` | cost scenario | `cost_scenario`, `commission_buy`, `commission_sell`, `stamp_tax_sell`, `slippage_buy`, `slippage_sell`, `decision_primary`, `pass` |
| `base_rate_trade_summary_by_fold.csv` | fold/portfolio/cost | `fold_id`, `portfolio_id`, `cost_scenario`, `order_count`, `trade_count`, `fill_rate`, `turnover_daily_mean`, `turnover_annualized`, `cost_drag_annualized` |
| `base_rate_portfolio_daily_summary.csv` | date/portfolio/cost | `date`, `fold_id`, `portfolio_id`, `cost_scenario`, `gross_return`, `net_return`, `portfolio_value`, `cash_weight`, `turnover`, `blocked_order_count` |
| `base_rate_benchmark_comparison.csv` | fold/portfolio/benchmark/cost | `fold_id`, `portfolio_id`, `benchmark_id`, `cost_scenario`, `net_annual_return`, `benchmark_annual_return`, `excess_return`, `tracking_error`, `information_ratio`, `max_drawdown`, `benchmark_max_drawdown` |
| `base_rate_random_same_turnover_baseline.csv` | fold/portfolio/repeat | `fold_id`, `portfolio_id`, `repeat_id`, `same_turnover`, `same_execution_constraints`, `same_cost_model`, `net_annual_return`, `excess_return`, `model_beats_random`, `empirical_p_value` |
| `base_rate_cost_sensitivity.csv` | fold/portfolio/cost | `fold_id`, `portfolio_id`, `cost_scenario`, `net_annual_return`, `cost_drag_annualized`, `collapse_vs_base`, `pass` |
| `base_rate_topk_sensitivity.csv` | fold/portfolio | `fold_id`, `portfolio_id`, `label_name`, `topk`, `n_drop`, `rebalance`, `net_annual_return`, `turnover_annualized`, `decision_primary`, `selection_allowed` |
| `base_rate_capacity_proxy.csv` | date/portfolio | `date`, `portfolio_id`, `estimated_trade_notional`, `money_available`, `participation_rate_proxy`, `capacity_warning`, `pass` |
| `base_rate_year_by_year_metrics.csv` | year/portfolio/cost | `year`, `portfolio_id`, `cost_scenario`, `return`, `max_drawdown`, `turnover`, `cost_drag`, `benchmark_excess`, `fill_rate` |
| `base_rate_failure_case_review.csv` | case | `case_id`, `date`, `instrument`, `portfolio_id`, `failure_type`, `metric_impact`, `root_cause`, `action_required` |
| `base_rate_forbidden_selection_self_check.csv` | forbidden output | `forbidden_output`, `observed_count`, `pass`, `evidence_path` |

### 10.4 Required cache artifacts

Full row-level outputs must be parquet cache only:

```text
BaseRate/outputs/alpha158_lgbm_oos/cache/feature_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/cache/label_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/cache/prediction_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/cache/order_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/cache/trade_panel.parquet
BaseRate/outputs/alpha158_lgbm_oos/cache/portfolio_daily.parquet
```

Cache tracking rule:

```text
git check-ignore BaseRate/outputs/alpha158_lgbm_oos/cache/*.parquet must pass
full row-level panels cannot be tracked CSV
report CSV/JSON/markdown artifacts live under BaseRate/outputs/alpha158_lgbm_oos/reports/
```

---

## 11. Success / failure interpretation

### 11.1 Positive base rate

允许标记：

```text
baseline_positive_after_cost = true
```

Positive 判定只能使用预注册主口径：

```text
decision_label = LABEL_1D_Q
decision_portfolio = topk_50_dropout_5_daily
decision_cost_model = base
decision_execution = next_open
decision_universe = mcap500_mainboard_pit_default
```

B1 / B2 label、TopK / rebalance sensitivity、low-cost / high-cost sensitivity、random baseline repeat 都只能用于稳健性解释，不得反向选择成 primary success path。

当且仅当主组合在 OOS 中满足：

```text
net_annual_return > benchmark_annual_return + thresholds.min_excess_return
max_drawdown <= benchmark_max_drawdown + thresholds.max_dd_worse_than_benchmark
sharpe >= thresholds.min_sharpe
calmar >= thresholds.min_calmar
cost_sensitivity_base_pass = true
cost_sensitivity_high_not_total_collapse = true
random_same_turnover_p_value <= thresholds.max_random_baseline_p_value
turnover_annualized <= thresholds.max_turnover_annualized
execution_block_rate <= thresholds.max_execution_block_rate
```

默认阈值：

```yaml
thresholds:
  min_excess_return: 0.03
  max_dd_worse_than_benchmark: 0.05
  min_sharpe: 0.50
  min_calmar: 0.30
  max_random_baseline_p_value: 0.10
  max_turnover_annualized: 60.0
  max_execution_block_rate: 0.20
```

这些阈值不是最终投资要求，只是判断 baseline 是否值得继续研究。

### 11.2 Negative base rate

若出现以下任一情况，标记：

```text
baseline_negative_after_cost = true
```

条件：

```text
net OOS return <= benchmark
or high-cost sensitivity 使收益完全坍缩
or turnover / execution block 导致不可交易
or random same-turnover baseline 不显著劣于模型组合
or 2024 / 2025 单独年份完全崩溃且无法解释
```

### 11.3 Inconclusive

若因数据或实现问题无法判断，标记：

```text
baseline_inconclusive_due_to_data_or_execution = true
```

典型原因：

```text
PIT universe 不完整
Alpha158 feature 生成失败
label 对齐不清楚
execution constraint 无法模拟
成本模型无法审计
OOS 数据不可用
```

---

## 12. Recommendation enum

最终 recommendation 必须是以下之一：

```text
proceed_to_risk_filter_overlay_research
proceed_to_factor_regime_cohort_research
continue_base_rate_sensitivity_audit
fix_data_or_backtest_infra_before_research
stop_primitive_discovery_until_positive_base_rate
stop_due_to_negative_after_cost_base_rate
```

禁止 recommendation：

```text
proceed_to_primitive_discovery
proceed_to_explore11
candidate_for_p1_strategy
validated_strategy
selected_final_model
selected_score_bucket
freeze_strategy
```

### 12.1 推荐逻辑

如果：

```text
baseline_positive_after_cost = true
```

则可以输出：

```text
proceed_to_risk_filter_overlay_research
```

下一阶段主问题应是：

```text
给定 PIT 宽基 Alpha158 + LGBM topK portfolio，
failure / risk filter 是否能降低回撤或改善 net performance，
同时不显著牺牲收益和容量？
```

如果：

```text
baseline_negative_after_cost = true
```

则必须输出：

```text
stop_primitive_discovery_until_positive_base_rate
```

如果：

```text
baseline_inconclusive_due_to_data_or_execution = true
```

则输出：

```text
fix_data_or_backtest_infra_before_research
```

---

## 13. Required report structure

`BaseRate-Alpha158-LGBM-OOS-report.md` 至少包含：

```text
1. Executive conclusion
2. Why BaseRate is needed after Explore10 series
3. Scope and forbidden conclusions
4. Data source and PIT universe audit
5. Alpha158 feature construction and label alignment
6. Fold design and anti-leakage audit
7. Model training summary
8. Prediction coverage and IC diagnostics
9. Portfolio construction
10. Execution constraints and cost model
11. OOS net performance
12. Benchmark comparison
13. Random same-turnover baseline
14. Cost sensitivity
15. TopK / rebalance sensitivity
16. Year-by-year results
17. Turnover, capacity, fill and blocked-order analysis
18. Failure cases
19. Base rate conclusion
20. Recommendation
21. Forbidden conclusion self-check
```

---

## 14. Config sketch

```yaml
phase: base_rate_alpha158_lgbm_oos
title: pit_broad_universe_alpha158_lgbm_after_cost_oos_baseline
output_root: BaseRate/outputs/alpha158_lgbm_oos

universe:
  pit_membership: data/universe/pit_mcap500_mainboard_daily.csv
  qlib_instruments: data/universe/qlib_pit_mcap500_mainboard.txt
  allow_industry_filter: false
  allow_result_based_filter: false

provider:
  provider_uri: data/qlib/cn_data_pit
  fallback_provider_uri_for_schema_only: Explore1/data/qlib/cn_data
  fallback_provider_eligible_row_count_required: 0

features:
  primary_feature_set: Alpha158
  alpha158_default_workflow_allowed: true
  custom_feature_extension_allowed_in_primary: false

labels:
  primary:
    - LABEL_1D_Q
  secondary_reported_not_decision:
    - LABEL_5D
  sensitivity:
    - LABEL_10D
  choose_best_label_by_oos: false

folds:
  - fold: 2021
    train: [2017, 2018, 2019]
    valid: [2020]
    test: [2021]
  - fold: 2022
    train: [2017, 2018, 2019, 2020]
    valid: [2021]
    test: [2022]
  - fold: 2023
    train: [2017, 2018, 2019, 2020, 2021]
    valid: [2022]
    test: [2023]
  - fold: 2024
    train: [2017, 2018, 2019, 2020, 2021, 2022]
    valid: [2023]
    test: [2024]
  - fold: 2025
    train: [2017, 2018, 2019, 2020, 2021, 2022, 2023]
    valid: [2024]
    test: [2025]

data_discipline:
  signal_date_rule: close_after_market
  execution_date_rule: next_trading_day_open
  same_close_execution_allowed: false
  feature_asof_date_rule: signal_date
  execution_date_ohlcvm_as_feature_allowed: false
  observed_reference_selection_allowed: false

model:
  type: lightgbm
  primary_model_id: LGBM_REGRESSION_ALPHA158_FIXED_V1
  class: qlib.contrib.model.gbdt.LGBModel
  loss: mse
  params:
    colsample_bytree: 0.8879
    learning_rate: 0.0421
    subsample: 0.8789
    lambda_l1: 205.6999
    lambda_l2: 580.9768
    max_depth: 8
    num_leaves: 210
    num_threads: 20
    early_stopping_rounds: 50
    eval_metric: l2
    seed: 20260508
  hyperparameter_search_allowed: false
  early_stopping_uses_valid_only: true
  oos_used_for_model_selection: false

portfolio:
  primary:
    name: topk_50_dropout_5_daily
    topk: 50
    n_drop: 5
    rebalance: daily
    weight: equal_weight
    max_position_weight: 0.05
  sensitivity:
    - topk_20_dropout_2
    - topk_50_dropout_5
    - topk_100_dropout_10
    - topk_50_full_rebalance
    - topk_100_full_rebalance
    - weekly_rebalance_topk_50

cost_model:
  commission_buy: 0.001
  commission_sell: 0.001
  stamp_tax_sell: 0.0005
  slippage_buy: 0.0005
  slippage_sell: 0.0005

execution_constraints:
  t_plus_1: true
  deal_price: open
  sell_first: true
  sell_cash_reuse_same_execution_date: true
  suspension_block: true
  limit_up_buy_block: true
  limit_down_sell_block: true
  zero_volume_block: true

benchmarks:
  - SH000300
  - pit_universe_equal_weight
  - pit_universe_mcap_weight_if_available
  - random_same_turnover

random_baseline:
  n_repeats: 200
  same_turnover: true
  same_execution_constraints: true
  same_cost_model: true

thresholds:
  min_excess_return: 0.03
  max_dd_worse_than_benchmark: 0.05
  min_sharpe: 0.50
  min_calmar: 0.30
  max_random_baseline_p_value: 0.10
  max_turnover_annualized: 60.0
  max_execution_block_rate: 0.20
```

---

## 15. Implementation commands

建议新增独立入口，避免继续污染 Explore9 / Explore10 primitive pipeline。

```bash
uv run python BaseRate/scripts/run_base_rate.py profile-alpha158-lgbm-oos \
  --config BaseRate/configs/alpha158_lgbm_oos.yaml

uv run python BaseRate/scripts/run_base_rate.py report-alpha158-lgbm-oos \
  --config BaseRate/configs/alpha158_lgbm_oos.yaml
```

禁止把旧 momentum / close-price TopK 脚本当作本阶段完成实现：

```text
scripts/05_backtest_topk.py:
  status: not_allowed_as_base_rate_implementation
  reason:
    - it builds a momentum signal, not Alpha158 + LightGBM predictions
    - existing compatible configs use deal_price: close
    - it does not emit the required label / execution / cost / random-baseline audits
```

若复用任何既有 Qlib workflow，只能作为内部组件，且必须先满足：

```text
uses_alpha158_lgbm_prediction_panel = true
deal_price = open
signal_date_rule = T_close_after_market
execution_date_rule = next_trading_day_open
required_audit_artifacts_emitted = true
fallback_script_not_reported_as_completed_baseline = true
```

报告必须记录：

```text
script_path
config_path
git_commit_hash
qlib_provider_uri
feature_set_hash
label_definition_hash
cost_model_hash
portfolio_config_hash
```

---

## 16. Preflight checklist

运行前必须确认：

```text
[ ] PIT universe 文件存在并能按日期读取
[ ] Qlib provider 存在并能读取 open/high/low/close/volume/money/factor
[ ] Alpha158 feature pipeline 可复现
[ ] Label 定义与 next-open 执行语义一致
[ ] 2024 / 2025 OOS 不用于调参、选择 topK、选择成本模型或选择特征
[ ] 交易成本模型已配置
[ ] 涨跌停 / 停牌 / 无量不可成交规则已配置或标记 limitation
[ ] benchmark 数据存在
[ ] random same-turnover baseline 配置固定
[ ] full row-level artifacts 写入 parquet cache，不写 tracked CSV
[ ] report 不输出 primitive / P1 / freeze / selected final strategy
```

---

## 17. Final boundary statement

BaseRate 报告必须重复以下边界：

```text
This stage establishes a PIT broad-universe Alpha158 + LightGBM after-cost OOS base rate.
It does not discover primitives, does not validate a final strategy, and does not freeze a model.
A positive result only permits risk-filter / failure-overlay research on top of this baseline.
A negative result stops further primitive discovery until data, labels, execution, or model baseline issues are fixed.
```
