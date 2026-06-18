# Requirement: 12A2 State-Change Backbone Candidate Generator

## 0. 路径基线

本需求使用以下路径别名：

```text
REPO_ROOT = /home/xiaolv/code/a_share
TOPIC_ROOT = REPO_ROOT/topics/02_AFML_BIG_WINNER
EXPERIMENT_ROOT = TOPIC_ROOT/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0
```

路径解析规则：

1. 以 `topics/` 开头的路径相对 `REPO_ROOT`。
2. 以 `data/`、`experiments/` 开头的路径相对 `TOPIC_ROOT`。
3. 以 `outputs/`、`configs/`、`src/`、`tests/` 开头的路径相对 `EXPERIMENT_ROOT`。
4. 每个输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status。
5. 必需输入缺失时 fail closed；不得从聚合表、历史报告文本或未来标签中反推缺失字段。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A2
run_id = 12A2_state_change_backbone_candidate_generator
status = spec_frozen_pending_run
expected_entrypoint = src/run_12a2_state_change_backbone_candidate_generator.py
expected_config = configs/config_12a2_state_change_backbone_candidate_generator.yaml
expected_test_file = tests/test_12a2_state_change_backbone_candidate_generator.py
```

本阶段承接 12A0/12A1 的结论：

```text
12A1 decision = 12A1_r_core_recall_benchmark_only
```

含义：

```text
R-core 只能作为 recall benchmark / source pool 对照，
不能继续被默认当作干净 event backbone。
```

12A2 的任务不是 winner/failure 分类，而是生成一组新的、PIT-safe、低泄漏风险的 state-change event candidates，供 12A3 做 episode recall / event precision frontier。

## 2. 研究目的

12A2 回答一个问题：

```text
在不使用 future return、MFE、episode label、touch coordinate 的前提下，
能否从 PIT price / benchmark / board / Top-N universe 中生成
比 R-core 更像“状态变化”的候选事件集合？
```

本阶段只允许输出 event candidates 与审计表。它不判断交易可用性，不训练模型，不做 winner/failure morphology，不选择买卖阈值。

## 3. 非目标

本需求明确不做：

- 不训练 fast-fail、winner、failure、meta-label 模型；
- 不使用 06 episode low/high、11A2 MFE、09/10/11 label 作为生成特征；
- 不把 R-core event 当作正样本或训练标签；
- 不做 12A3 的 episode recall / event precision frontier；
- 不做 policy replay；
- 不授权任何交易策略；
- 不把 blocked industry CUSUM 伪装为可运行 family；
- 不生成下行、顶部转折、派发、做空方向的 state-change candidates；
- 不为了提高 recall 调整 threshold 到未来标签最优。

## 4. 前置输入

### 4.1 12A0/12A1 前置结果

必需输入：

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_demote_or_keep_decision.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_density_badside_tradeoff.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_arm_event_registry.csv.gz
outputs/manifests/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_manifest.json
```

前置 gate：

```text
r_core_demote_or_keep_decision.decision IN (
  12A1_r_core_recall_benchmark_only,
  12A1_r_core_feature_source_only,
  12A1_r_core_backbone_supported
)
population_bridge_status = pass
```

12A1 的 `next_allowed_requirement` 解释规则：

```text
if next_allowed_requirement = stop_no_valid_backbone_for_morphology:
  含义是停止 winner/failure morphology；
  不阻止 12A2 生成新的 replacement backbone candidates。

if next_allowed_requirement = requirement_12a2_state_change_backbone_candidate_generator.md:
  直接进入 12A2。

if next_allowed_requirement points to any morphology / classifier / policy requirement:
  12A2 必须记录 handoff_conflict_flag = true，
  但只要 population_bridge_status = pass，仍可作为 replacement-path diagnostic 运行。
```

如果 `decision = 12A1_r_core_population_blocked`，12A2 必须停止：

```text
decision = 12A2_state_change_candidate_generation_blocked
block_reason = upstream_12a1_population_blocked
```

`12A1_r_core_recall_benchmark_only` 不是 blocker。它正是 12A2 重建 backbone 的触发条件。

### 4.2 PIT universe 和日线输入

必需输入：

```text
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_membership_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/index/benchmark_indices_daily.csv
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/config.yaml
```

`pit_topn_400_100_executable_daily.csv` 必需字段：

```text
usable_trade_date
instrument
source_membership_date
membership_date
available_time
board_bucket
is_listed
is_st
is_suspended
raw_unadjusted_close
total_market_cap_cny
history_ready_240d_flag
history_observed_sessions_before_usable_date
```

`pit_topn_400_100_membership_daily.csv` 必需字段：

```text
membership_date
usable_trade_date
instrument
board_bucket
is_listed
is_st
is_suspended
raw_unadjusted_close
total_market_cap_cny
history_ready_240d_flag
history_observed_sessions_before_usable_date
```

用途：

```text
membership_daily 用于 cross-section / board feature 计算、event_t0 PIT snapshot、event_t0 universe eligibility；
executable_daily 用于 trade_open eligibility；
两者不得互相替代 eligibility 判断。
```

`benchmark_indices_daily.csv` 必需字段：

```text
trade_date
index_alias
open
high
low
close
volume
money
```

qfq 日线必需字段：

```text
date
open
high
low
close
volume
money
instrument
```

必需 benchmark：

```text
index_alias = all_a
```

如果 `all_a` 不存在，或者 qfq 日线文件目录不可读，必须停止。

### 4.3 08 公式和候选事件参考

参考输入：

```text
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_formula_spec.csv
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/density_fast_fail_audit/candidate_10d_density_summary.csv
```

这些输入只用于：

- 复用字段命名、event anchor convention、density denominator；
- 记录 R-core / T-family 参考口径；
- 做 overlap / provenance audit。

它们不得作为 12A2 trigger label，也不得把 08 family 的命中结果直接复制为 12A2 candidate。

## 5. 时间和 PIT 口径

### 5.1 事件时间

12A2 event 使用 t0 close confirmation：

```text
event_t0_date = qfq daily date at signal close
event_t0_pos = zero-based qfq daily position at event_t0_date
event_signal_time = t0_close
```

执行锚点：

```text
trade_open_date = immediate next market trading date after event_t0_date
trade_open_pos = qfq position of trade_open_date
trade_open_price = qfq open at trade_open_date
execution_anchor_policy = t0_close_next_open
```

`trade_open_date` 必须来自 `all_a` benchmark trading calendar 中 `event_t0_date` 后的第一个交易日。
不得为了找到 qfq open 或 executable row 向后搜索更晚日期。
如果 immediate next market trading date 缺 qfq open、停牌、或不在 executable universe，必须标记为 non-executable。

如果 next-open 不可得：

```text
non_executable_next_open = true
non_executable_reason IN (
  missing_next_trading_session,
  missing_qfq_open,
  suspended_or_not_in_executable_universe_at_trade_open,
  price_nonpositive_or_nan
)
```

非 executable event 必须保留在 raw instance audit，但不得进入 `state_change_candidate_event_canonical.csv.gz` 的 supported canonical denominator。

### 5.2 universe eligibility

支持事件必须同时满足：

```text
instrument 在 event_t0_date 有 qfq bar；
instrument 在 event_t0_date 有 PIT membership universe row；
instrument 在 trade_open_date 有 PIT executable universe row；
event_t0_date PIT membership row:
  is_listed = true；
  is_st = false；
  is_suspended = false；
  history_ready_240d_flag = true；
  board_bucket 非空；
trade_open_date PIT executable row:
  is_listed = true；
  is_st = false；
  is_suspended = false；
```

字段来源：

```text
board_bucket = event_t0_date PIT membership row board_bucket
total_market_cap_cny = event_t0_date PIT membership row total_market_cap_cny
event_split = split(event_t0_date)
market_regime_bucket = 5.4 节定义的 all_a t0 close regime
trade_open eligibility = trade_open_date PIT executable row
```

不得用 trade_open executable row 回填 t0 board / mcap / regime。不得用 episode 结果回填。

### 5.3 split 口径

复用 08 config 的 split：

```text
train_start = 2017-01-03
train_end = 2021-12-31
validation_start = 2022-01-01
validation_end = 2023-12-31
robustness_start = 2024-01-01
```

`event_split` 按 `event_t0_date` 归属，不按 future label completion date 归属。

### 5.4 market regime 口径

`market_regime_bucket` 必须复用 02/04/08 的 all_a regime 逻辑，直接由 t0 close 可得的 `all_a` 指数序列计算：

```text
all_a_close = benchmark_indices_daily.close where index_alias = all_a

market_trend_60d =
  all_a_close / rolling_mean(all_a_close, 60, min_periods=60) - 1

market_drawdown_120d =
  all_a_close / rolling_max(all_a_close, 120, min_periods=120) - 1

if market_trend_60d is missing OR market_drawdown_120d is missing:
  market_regime_bucket = missing_insufficient_lookback
elif market_trend_60d >= 0 AND market_drawdown_120d > -0.10:
  market_regime_bucket = risk_on
elif market_trend_60d < 0 AND market_drawdown_120d <= -0.10:
  market_regime_bucket = risk_off
else:
  market_regime_bucket = transition
```

Primary canonical denominator 不得包含：

```text
market_regime_bucket = missing_insufficient_lookback
```

这些 rows 可以进入 raw audit，并记录：

```text
pit_status = blocked_missing_market_regime_lookback
```

## 6. 共同特征构造

所有特征必须只使用 `<= event_t0_date` 的 qfq close/high/low/open/volume/money、benchmark close、PIT universe membership。

基本特征：

```text
ret_1d = close / close.shift(1) - 1
ret_5d = close / close.shift(5) - 1
ret_10d = close / close.shift(10) - 1
ret_20d = close / close.shift(20) - 1
market_ret_1d = all_a.close / all_a.close.shift(1) - 1
market_ret_5d = all_a.close / all_a.close.shift(5) - 1
market_ret_20d = all_a.close / all_a.close.shift(20) - 1
direction_up_1d = 1 if ret_1d > 0 else 0
direction_entropy_20d = binary_entropy(mean(direction_up_1d, 20))
ema20 = ewm(close, span=20, adjust=false, min_periods=20)
ema60 = ewm(close, span=60, adjust=false, min_periods=60)
close_to_ema20 = close / ema20 - 1
close_to_ema60 = close / ema60 - 1
above_ema60_flag = 1 if close > ema60 else 0
above_ema60_days_20 = rolling_sum(above_ema60_flag, 20)
amount_ratio_20d = money / rolling_mean(money, 20).shift(1)
amount_ratio_60d = money / rolling_mean(money, 60).shift(1)
range_pct = high / low - 1
close_position_in_range = (close - low) / (high - low)
true_range = max(high - low, abs(high - close.shift(1)), abs(low - close.shift(1)))
atr14 = rolling_mean(true_range, 14)
atr14_pct = atr14 / close
atr_pct_rank_60d = rolling_percentile_rank(atr14_pct, 60)
rolling_low_60 = rolling_min(low, 60)
rolling_high_60 = rolling_max(high, 60)
distance_from_low_60 = close / rolling_low_60 - 1
near_high_60 = close / rolling_high_60
beta_60 = rolling_cov(ret_1d, market_ret_1d, 60).shift(1)
          / rolling_var(market_ret_1d, 60).shift(1)
residual_ret_1d = ret_1d - beta_60 * market_ret_1d
residual_ret_5d = ret_5d - beta_60 * market_ret_5d
```

市场和 board 特征：

```text
all_a_ret_20d = all_a.close / all_a.close.shift(20) - 1
all_a_drawdown_60d = all_a.close / rolling_max(all_a.close, 60) - 1
board_equal_weight_ret_1d = equal_weight(ret_1d) by board_bucket among PIT membership members
board_ret_20d = product(1 + board_equal_weight_ret_1d, 20) - 1
board_relative_cusum_20d = rolling_sum(board_equal_weight_ret_1d - market_ret_1d, 20)
stock_vs_board_20d = ret_20d - board_ret_20d
stock_vs_board_cusum_20d = rolling_sum(ret_1d - board_equal_weight_ret_1d, 20)
momentum_percentile_20d = cross_section_percentile(ret_20d) among PIT membership members
momentum_percentile_20d_lag20 = momentum_percentile_20d.shift(20) by instrument
momentum_rank_jump_20d = momentum_percentile_20d - momentum_percentile_20d_lag20
```

Board / cross-section 特征必须使用 `pit_topn_400_100_membership_daily.csv`：

```text
feature_date = event_t0_date or historical date <= event_t0_date
membership_date = feature_date
member_ret_1d = qfq close(feature_date) / qfq close(previous qfq date) - 1
member enters board aggregation only if membership row exists and qfq ret_1d is finite
```

`pit_topn_400_100_executable_daily.csv` 只用于 trade_open eligibility，
不得替代 membership_daily 来计算 board breadth / equal-weight return。

如果 board membership finite-return member count 小于 `cross_section_min_members = 120`，board 特征当日不可用。

## 7. Candidate family 公式

所有 B-family 必须输出 raw event instances；C0 再做 canonical 化和 first-trigger discipline。

Variant 参数绑定规则：

```text
每个 formula 中出现的 *_min / *_max / *_multiple threshold variable
必须在该 variant 的 threshold_grid_json 中有同名字段；
runner 不得保留未绑定的 threshold / amount_threshold / predeclared_* 占位符；
state_change_family_formula_spec.csv.formula_text 必须是可复现公式，
threshold_grid_json 必须记录该 variant 的全部参数值。
```

### 7.1 B1: relative residual CUSUM break

目的：

```text
捕捉个股相对全市场的累积残差变化，而不是单纯 momentum 高位。
```

输入：

```text
qfq stock daily
all_a benchmark daily
PIT membership universe for t0 snapshot / board features
PIT executable universe only for trade_open eligibility
```

公式：

```text
beta_60 = rolling_cov(ret_1d, market_ret_1d, 60).shift(1)
          / rolling_var(market_ret_1d, 60).shift(1)
beta_60 clip 到 [-1, 3]
residual_ret_1d = ret_1d - beta_60 * market_ret_1d
residual_cusum_20d = rolling_sum(residual_ret_1d, 20)
residual_cusum_20d_lagmax = rolling_max(residual_cusum_20d.shift(1), 20)
```

Trigger grid：

```text
B1a:
  residual_cusum_20d >= 0.08
  residual_cusum_20d_lagmax < 0.08
  residual_ret_5d >= 0.02
  close_to_ema60 >= -0.02

B1b:
  residual_cusum_20d >= 0.10
  residual_cusum_20d_lagmax < 0.10
  residual_ret_5d >= 0.03
  close_to_ema60 >= 0.00

B1c_stock_vs_board:
  stock_vs_board_cusum_20d >= 0.08
  rolling_max(stock_vs_board_cusum_20d.shift(1), 20) < 0.08
  residual_ret_5d >= 0.02
  close_to_ema60 >= -0.02

B1d_board_vs_market_context:
  board_relative_cusum_20d >= 0.06
  rolling_max(board_relative_cusum_20d.shift(1), 20) < 0.06
  stock_vs_board_20d >= 0
  residual_ret_5d >= 0.015
```

Reset 必须按 variant 分开记录到 `reset_rule_text`：

```text
B1a/B1b:
  residual_cusum_20d <= 0
  OR close_to_ema60 < -0.05

B1c_stock_vs_board:
  stock_vs_board_cusum_20d <= 0
  OR close_to_ema60 < -0.05

B1d_board_vs_market_context:
  board_relative_cusum_20d < 0
  OR stock_vs_board_20d < -0.03
  OR close_to_ema60 < -0.05
```

### 7.2 B2: compression-to-expansion

目的：

```text
捕捉低波动压缩后的方向性扩张，而不是持续高位动量。
```

公式：

```text
compression_flag =
  atr_pct_rank_60d.shift(1) <= atr_pct_rank_60d_max
  AND rolling_mean(range_pct, 10).shift(1) / rolling_mean(range_pct, 60).shift(1) <= 0.75

expansion_flag =
  range_pct >= rolling_mean(range_pct, 20).shift(1) * expansion_multiple
  AND amount_ratio_20d >= amount_ratio_20d_min
  AND close_position_in_range >= 0.65
  AND ret_5d >= 0.02

entropy_compression_flag =
  direction_entropy_20d.shift(1) <= direction_entropy_20d_max

entropy_expansion_flag =
  ret_5d >= ret_5d_min
  AND residual_ret_5d >= residual_ret_5d_min
  AND amount_ratio_20d >= amount_ratio_20d_min
  AND close_position_in_range >= 0.65
```

Trigger grid：

```text
B2a:
  atr_pct_rank_60d_max = 0.35
  expansion_multiple = 1.20
  amount_ratio_20d_min = 1.15

B2b:
  atr_pct_rank_60d_max = 0.45
  expansion_multiple = 1.35
  amount_ratio_20d_min = 1.30

B2c_entropy:
  direction_entropy_20d_max = 0.85
  ret_5d_min = 0.035
  residual_ret_5d_min = 0.02
  amount_ratio_20d_min = 1.10
```

Trigger：

```text
B2a/B2b:
  compression_flag AND expansion_flag

B2c_entropy:
  entropy_compression_flag AND entropy_expansion_flag
```

Reset 必须按 variant 分开记录到 `reset_rule_text`：

```text
B2a/B2b:
  atr_pct_rank_60d > 0.70
  OR close_to_ema20 < -0.03

B2c_entropy:
  direction_entropy_20d > 0.95
  OR close_to_ema20 < -0.03
```

### 7.3 B3: low-reclaim / repair transition

目的：

```text
捕捉从低位修复到可观察趋势恢复的 first reclaim，
但不使用 episode_low_date 或 future touch coordinate。
```

公式：

```text
prior_below_ema60_days_20 =
  rolling_sum(close.shift(1) < ema60.shift(1), 20)

ema60_reclaim_today =
  close >= ema60
  AND close.shift(1) < ema60.shift(1)

low_repair_context =
  distance_from_low_60 >= distance_from_low_60_min
  AND near_high_60 <= 0.95

confirmation =
  prior_below_ema60_days_20 >= prior_below_ema60_days_20_min
  AND ret_5d >= ret_5d_min
  AND stock_vs_board_20d >= -0.02
  AND close_position_in_range >= 0.60
```

Trigger grid：

```text
B3a:
  prior_below_ema60_days_20_min = 10
  distance_from_low_60_min = 0.08
  ret_5d_min = 0.03

B3b:
  prior_below_ema60_days_20_min = 15
  distance_from_low_60_min = 0.12
  ret_5d_min = 0.04
```

Trigger：

```text
ema60_reclaim_today AND low_repair_context AND confirmation
```

Reset：

```text
close_to_ema60 < -0.03
```

### 7.4 B4: breadth/regime context transition

目的：

```text
捕捉市场/board 环境由压制转向扩散时，个股同步出现的状态变化。
```

B4 不得使用行业分类。行业 PIT classification 不可用时，必须记录：

```text
family_id = B4_industry_breadth_context
family_input_status = blocked_missing_pit_industry_classification
```

12A2 必须集中声明以下行业/轮动 state-change 维度不可运行：

```text
R4_industry_breadth_expansion = blocked_missing_pit_industry_classification
T1_stock_vs_industry_CUSUM_break = blocked_missing_pit_industry_classification
T2_industry_vs_market_CUSUM_break = blocked_missing_pit_industry_classification
```

可运行 B4 只允许使用 Top-N / board / all_a proxy。

公式：

```text
market_turn =
  all_a_ret_20d >= 0
  AND all_a_drawdown_60d >= -0.10

board_turn =
  board_relative_cusum_20d >= board_relative_cusum_20d_min
  AND board_ret_20d >= 0

stock_participation =
  residual_ret_5d >= residual_ret_5d_min
  AND stock_vs_board_20d >= 0
```

Trigger grid：

```text
B4a:
  board_relative_cusum_20d_min = 0.04
  residual_ret_5d_min = 0.015

B4b:
  board_relative_cusum_20d_min = 0.06
  residual_ret_5d_min = 0.020
```

Trigger：

```text
market_turn AND board_turn AND stock_participation
```

Reset：

```text
all_a_drawdown_60d < -0.15
OR board_relative_cusum_20d < 0
```

### 7.5 B5: participation / volume regime shift

目的：

```text
捕捉资金参与基线变化，而不是只把成交额当作单日 confirmation。
```

B5 可运行，因为只使用 qfq money、price、market relative return。

公式：

```text
volume_regime_shift =
  amount_ratio_20d >= amount_ratio_20d_min
  AND amount_ratio_60d >= amount_ratio_60d_min

positive_price_confirmation =
  ret_5d >= ret_5d_min
  AND residual_ret_5d >= residual_ret_5d_min
  AND close_position_in_range >= close_position_in_range_min
```

Trigger grid：

```text
B5a:
  amount_ratio_20d_min = 1.80
  amount_ratio_60d_min = 1.30
  ret_5d_min = 0.035
  residual_ret_5d_min = 0.015
  close_position_in_range_min = 0.60

B5b:
  amount_ratio_20d_min = 2.20
  amount_ratio_60d_min = 1.50
  ret_5d_min = 0.025
  residual_ret_5d_min = 0.010
  close_position_in_range_min = 0.65
```

Trigger：

```text
volume_regime_shift AND positive_price_confirmation
```

Reset：

```text
amount_ratio_20d < 1.00
OR close_to_ema20 < -0.03
```

### 7.6 B6: first leadership rank entry

目的：

```text
捕捉个股第一次进入相对强势横截面，而不是持续高位动量。
```

B6 是 R7 rank-jump 的 state-change 版本。它必须要求 prior rank 不高、当日 rank jump 明确、
并且只允许 first-trigger canonical 后进入 primary。否则会退化成 R-core momentum rank pool。

公式：

```text
rank_entry =
  momentum_percentile_20d_lag20 <= lag_momentum_percentile_20d_max
  AND momentum_percentile_20d >= momentum_percentile_20d_min
  AND momentum_rank_jump_20d >= momentum_rank_jump_20d_min

quality_confirmation =
  residual_ret_5d >= residual_ret_5d_min
  AND close_to_ema60 >= close_to_ema60_min
```

Trigger grid：

```text
B6a:
  lag_momentum_percentile_20d_max = 0.50
  momentum_percentile_20d_min = 0.80
  momentum_rank_jump_20d_min = 0.25
  residual_ret_5d_min = 0.015
  close_to_ema60_min = -0.02

B6b:
  lag_momentum_percentile_20d_max = 0.40
  momentum_percentile_20d_min = 0.85
  momentum_rank_jump_20d_min = 0.30
  residual_ret_5d_min = 0.020
  close_to_ema60_min = 0.00
```

Trigger：

```text
rank_entry AND quality_confirmation
```

Reset：

```text
momentum_percentile_20d < 0.55
OR close_to_ema60 < -0.05
```

### 7.7 B7: high-base breakout diagnostic

目的：

```text
保留 near-high / volume breakout 作为对照，但默认不进入 primary canonical。
```

B7 接近 08 R2/R3 high-base breakout，可能重新制造 R-core 式高位追随密度。
因此在 12A2 中固定为 diagnostic-only：

```text
family_input_status = diagnostic_only
allowed_for_primary_canonical_flag = false
```

12A2 不提供 B7 primary override 开关。
如果后续研究要把 high-base breakout 升级为 primary family，必须新开 requirement。

公式：

```text
high_base_breakout =
  near_high_60 >= near_high_60_min
  AND amount_ratio_20d >= amount_ratio_20d_min
  AND close_position_in_range >= close_position_in_range_min
  AND residual_ret_5d >= residual_ret_5d_min
```

Trigger grid：

```text
B7_diagnostic:
  near_high_60_min = 0.96
  amount_ratio_20d_min = 1.50
  close_position_in_range_min = 0.65
  residual_ret_5d_min = 0.02
```

Trigger：

```text
high_base_breakout
```

Reset：

```text
near_high_60 < 0.90
OR close_to_ema20 < -0.03
```

### 7.8 B8: sustained trend state confirmation

目的：

```text
捕捉已经进入健康趋势态、但本研究窗口内没有发生 EMA reclaim / residual first break 的赢家候选。
```

B8 是 08 R8 persistent distance above EMA 的 state-change 化版本。
它不是把持续动量原样搬回 primary backbone，而是只在“首次确认进入持续趋势态”时触发：
当前窗口满足持续趋势条件，上一窗口不满足，并继续走 C0 first-trigger / cooldown。

公式：

```text
sustained_trend_state =
  above_ema60_days_20 >= above_ema60_days_20_min
  AND close_to_ema60 >= close_to_ema60_min
  AND ret_20d >= ret_20d_min
  AND residual_ret_5d >= residual_ret_5d_min

prior_sustained_trend_state =
  sustained_trend_state.shift(1)
```

B8 prior-state 缺失必须显式区分，不能在实现中静默当作 false：

```text
if required B8 lookback is incomplete:
  trigger = false
  raw_event_status = blocked_missing_b8_prior_state
  b8_trigger_origin = missing_required_lookback

if required B8 lookback is complete
and previous evaluated state exists:
  prior_sustained_trend_state = previous evaluated sustained_trend_state

if required B8 lookback is complete
and previous evaluated state is missing
and sustained_trend_state = true:
  trigger may be true
  b8_trigger_origin = first_observed_sustained_state
```

`first_observed_sustained_state` 是 B8 用来覆盖“样本内无穿越但趋势已经在位”的唯一允许首观测入口。
不得把 lookback 不足、PIT membership 缺口、停牌后不可评估状态误记为 B8 first-observed trigger。
B8 的 `b8_trigger_origin` 必须写入 raw instance 的 `family_trigger_origin`；
如果 B8 成为 primary family，也必须写入 canonical event 的 `primary_family_trigger_origin`。

Trigger grid：

```text
B8a:
  above_ema60_days_20_min = 10
  close_to_ema60_min = 0.03
  ret_20d_min = 0.08
  residual_ret_5d_min = 0.00

B8b:
  above_ema60_days_20_min = 15
  close_to_ema60_min = 0.05
  ret_20d_min = 0.10
  residual_ret_5d_min = 0.01
```

Trigger：

```text
sustained_trend_state = true
AND (
  prior_sustained_trend_state = false
  OR b8_trigger_origin = first_observed_sustained_state
)
```

Reset：

```text
above_ema60_days_20 < 5
OR close_to_ema60 < -0.02
```

### 7.9 C0: first-trigger density discipline

C0 是 canonical post-processor，不是未来标签过滤器。
C0 的 priority、cooldown、first-trigger 状态机必须写入
`state_change_canonicalization_spec.csv`，并由 manifest hash 覆盖。

输入：

```text
B1/B2/B3/B4/B5/B6/B7/B8 raw event instances
```

排序优先级：

```text
B1 relative residual CUSUM break = 10
B3 low-reclaim / repair transition = 20
B2 compression-to-expansion = 30
B4 breadth/regime context transition = 40
B5 participation / volume regime shift = 50
B6 first leadership rank entry = 60
B8 sustained trend state confirmation = 70
B7 high-base breakout diagnostic = 90
```

同一 instrument / event_t0_date 有多个 family 命中时：

```text
保留 priority 最小的 primary family；
triggered_family_variants 记录全部命中 family_variant_id；
triggered_family_count 记录命中 family 数；
```

同一 instrument 过密触发时：

```text
family_level_cooldown_sessions = 20
union_level_cooldown_sessions = 10
```

Reset 后允许新一轮 first trigger：

```text
B1 reset OR B2 reset OR B3 reset OR B4 reset OR B5 reset OR B6 reset OR B7 reset OR B8 reset
```

如果没有 reset，仅 cooldown 到期也可以触发，但必须标记：

```text
first_trigger_status = cooldown_reentry_without_reset
```

支持 backbone 候选默认只使用：

```text
first_trigger_status IN (
  first_after_reset,
  first_observed_in_sample
)
```

`cooldown_reentry_without_reset` 可以保留在 raw audit，但不得进入 primary canonical denominator。

状态机必须按以下顺序执行。

Step 1: raw instance generation：

```text
对每个 instrument 按 event_t0_pos 升序扫描；
先计算所有 B1/B2/B3/B4/B5/B6/B7/B8 trigger 和 reset；
同一日期允许多个 family raw instance 同时存在；
```

Step 2: family-level first-trigger：

```text
state key = instrument + family_variant_id
family-level cooldown means per formula-spec row / family_variant_id
initial armed_state = true
last_family_kept_pos = missing

if reset_rule true before evaluating current trigger:
  armed_state = true

下面的条件必须按顺序判断，命中第一条后不再继续判断后续条件。

1. if trigger false:
  no raw instance

2. if trigger true AND last_family_kept_pos is missing:
  first_trigger_status = first_observed_in_sample
  family_cooldown_status = pass
  armed_state = false

3. if trigger true AND armed_state = true:
  first_trigger_status = first_after_reset
  family_cooldown_status = pass
  armed_state = false

4. if trigger true AND armed_state = false AND event_t0_pos - last_family_kept_pos >= family_level_cooldown_sessions:
  first_trigger_status = cooldown_reentry_without_reset
  family_cooldown_status = pass

5. if trigger true AND armed_state = false AND event_t0_pos - last_family_kept_pos < family_level_cooldown_sessions:
  first_trigger_status = suppressed_family_cooldown
  family_cooldown_status = blocked
```

`last_family_kept_pos` 只在 `family_cooldown_status = pass` 时更新。

Step 3: same-day canonical priority：

```text
同一 instrument + event_t0_date 内，
只在 family_cooldown_status = pass 且 allowed_for_primary_canonical_flag = true 的 raw instances 中选择 primary；
primary = canonical_priority 最小；
triggered_family_variants = 当日所有 family_cooldown_status = pass 的 family_variant_id；
```

Step 4: union-level cooldown：

```text
state key = instrument
last_union_kept_pos = missing

if last_union_kept_pos is missing:
  union_cooldown_status = pass

elif event_t0_pos - last_union_kept_pos >= union_level_cooldown_sessions:
  union_cooldown_status = pass

else:
  union_cooldown_status = blocked
```

`last_union_kept_pos` 只在 `union_cooldown_status = pass` 且 row 进入 primary canonical denominator 时更新。

Primary canonical denominator 只保留：

```text
family_cooldown_status = pass
AND union_cooldown_status = pass
AND allowed_for_primary_canonical_flag = true
AND first_trigger_status IN (
  first_after_reset,
  first_observed_in_sample
)
AND non_executable_next_open = false
AND event_t0_pit_status = pass
AND trade_open_pit_status = pass
AND pit_status = pass
```

被 family cooldown、union cooldown、non-executable、PIT blocked 排除的 rows 必须保留在 instance audit，并写明 `candidate_generation_status`。

## 8. 禁止特征和泄漏审计

以下字段或语义不得出现在任何 trigger formula：

```text
episode_low_date
episode_high_date
first_50pct_date
qfq_high_at_high_date
mfe_120
mfe_120d_frozen
mfe_120_recomputed
event_big_winner_120d_label
failure_10_label
false_repair_20d_label
winner_120
class_big_winner
class_big_failure_proxy_nonwinner
future_return
forward_high
forward_low
post_t0
label
```

如果 `state_change_family_formula_spec.csv` 或 runner 内部 formula registry 中出现上述字段，必须停止：

```text
decision = 12A2_state_change_candidate_generation_blocked
block_reason = forbidden_future_or_label_feature_detected
```

## 9. 输出文件

所有输出路径相对 `EXPERIMENT_ROOT`。

基础输出目录：

```text
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/
outputs/publishable/reports/
outputs/manifests/
```

必需输出：

```text
input_artifact_audit.csv
state_change_candidate_event_instances.csv.gz
state_change_candidate_event_canonical.csv.gz
state_change_family_formula_spec.csv
state_change_canonicalization_spec.csv
state_change_feature_pit_audit.csv
state_change_density_audit.csv
state_change_family_overlap_diagnostic.csv
state_change_generation_decision.csv
state_change_candidate_generation_report.md
outputs/manifests/12A2_state_change_backbone_candidate_generator_manifest.json
```

### 9.1 `state_change_family_formula_spec.csv`

必需字段：

```text
family_id
variant_id
family_variant_id
family_role
input_series
required_input_columns
lookback_window
lag_policy
formula_text
threshold_grid_json
reset_rule_text
cooldown_sessions
event_t0_confirmation_time
execution_anchor_policy
pit_status
family_input_status
blocked_reason
forbidden_feature_scan_status
allowed_for_primary_canonical_flag
```

允许的 `family_input_status`：

```text
runnable_existing_data
blocked_missing_pit_industry_classification
blocked_missing_required_feature
diagnostic_only
```

Family 计数定义：

```text
runnable_family_n =
  count distinct family_id
  where family_input_status = runnable_existing_data
    and allowed_for_primary_canonical_flag = true

diagnostic_family_n =
  count distinct family_id
  where family_input_status = diagnostic_only

blocked_family_n =
  count distinct family_id
  where family_input_status IN (
    blocked_missing_pit_industry_classification,
    blocked_missing_required_feature
  )
```

`diagnostic_only` family 可以进入 raw instance audit 和 density/readout audit，
但不得用于满足 `runnable_family_n >= 2`。

### 9.2 `state_change_canonicalization_spec.csv`

一行是 C0 canonicalizer 的一个 frozen rule component。

必需字段：

```text
canonicalizer_id
component_id
component_role
input_family_scope
priority_order_json
family_level_cooldown_sessions
union_level_cooldown_sessions
first_trigger_supported_statuses_json
cooldown_reentry_policy
same_day_collision_policy
union_cooldown_policy
allowed_primary_filter
diagnostic_family_policy
non_executable_policy
pit_blocked_policy
rule_text
rule_hash
```

必需行：

```text
C0_priority_order
C0_family_level_first_trigger
C0_same_day_collision
C0_union_level_cooldown
C0_primary_denominator_filter
C0_diagnostic_family_policy
```

`rule_hash` 必须由该 component 的全部规则字段稳定生成。
如果 C0 priority / cooldown / denominator filter 有任何变化，`state_change_canonicalization_spec.csv`
和 manifest 的 `canonicalization_spec_hash` 必须变化。

### 9.3 `state_change_candidate_event_instances.csv.gz`

一行是一个 raw family variant 命中。

必需字段：

```text
event_instance_id
family_id
variant_id
family_variant_id
instrument
event_t0_date
event_t0_pos
event_signal_time
trade_open_date
trade_open_pos
trade_open_price
non_executable_next_open
non_executable_reason
event_split
board_bucket
market_regime_bucket
total_market_cap_cny
history_ready_240d_flag
feature_snapshot_hash
trigger_values_json
family_trigger_origin
reset_state_before_event
first_trigger_status
family_cooldown_status
union_cooldown_status
raw_event_status
pit_status
event_t0_pit_status
trade_open_pit_status
candidate_generation_status
```

`event_instance_id` 生成规则：

```text
stable_hash(
  run_id,
  family_variant_id,
  instrument,
  event_t0_date,
  event_t0_pos,
  trade_open_date,
  formula_version
)
```

### 9.4 `state_change_candidate_event_canonical.csv.gz`

一行是 C0 canonical 后的支持候选事件。

必需字段：

```text
canonical_event_id
primary_event_instance_id
primary_family_id
primary_variant_id
instrument
event_t0_date
event_t0_pos
event_signal_time
trade_open_date
trade_open_pos
trade_open_price
event_split
board_bucket
market_regime_bucket
triggered_family_variants
triggered_family_count
first_trigger_status
canonicalization_rule
canonical_priority
event_window_anchor_date
event_window_anchor_pos
event_window_anchor_status
non_executable_next_open
event_t0_pit_status
trade_open_pit_status
raw_instance_count_collapsed
feature_snapshot_hash
source_formula_hash
canonicalization_spec_hash
primary_family_trigger_origin
candidate_generation_status
```

`canonical_event_id` 生成规则：

```text
stable_hash(
  run_id,
  instrument,
  event_t0_date,
  event_t0_pos,
  primary_family_id,
  triggered_family_variants,
  formula_version
)
```

### 9.5 `state_change_feature_pit_audit.csv`

必需字段：

```text
feature_id
family_id
input_source_id
input_source_path
required_columns
lookback_sessions
lag_policy
available_at_t0_close_flag
uses_future_return_flag
uses_episode_label_flag
uses_label_touch_coordinate_flag
missing_value_policy
raw_row_count
usable_row_count
missing_row_rate
blocked_row_count
blocked_reason
pit_audit_status
```

`pit_audit_status` 允许值：

```text
pass
blocked_missing_source
blocked_missing_required_columns
blocked_future_or_label_leakage
warning_high_missing_rate
```

### 9.6 `state_change_density_audit.csv`

必需字段：

```text
candidate_scope_id
split
event_n
unique_instrument_n
unique_event_day_n
density_basis_id
denominator_source_id
denominator_instrument_years
events_per_instrument_year_mean
events_per_instrument_year_p95
density_vs_08_r_core
density_vs_07_E1_only
r_core_reference_event_n
r_core_reference_events_per_instrument_year_mean
e1_reference_event_n
e1_reference_events_per_instrument_year_mean
rolling_10d_duplicate_rate
rolling_20d_duplicate_rate
adjacent_gap_median
top_instrument_event_share
top_board_event_share
non_executable_event_rate
first_trigger_supported_rate
density_status
```

密度 denominator 必须复用 08/12A1 的 full evaluated universe basis：

```text
density_basis_id = 08_full_evaluated_universe_years_252
```

不得用每个 family 自己的最小/最大日期跨度重算 denominator。

`density_vs_08_r_core` 计算规则：

```text
For each split in (all, train, validation, robustness):
  r_core_reference row =
    12A1 r_core_density_badside_tradeoff
    where arm_id = 08_R_core_event_regime_gated_raw
      and split = current split

  density_vs_08_r_core =
    candidate events_per_instrument_year_mean
    / r_core_reference.events_per_instrument_year_mean

  r_core_reference_event_n =
    r_core_reference.event_n

  r_core_reference_events_per_instrument_year_mean =
    r_core_reference.events_per_instrument_year_mean
```

`density_vs_07_E1_only` 计算规则：

```text
E1 reference row =
  08 candidate_family_density_summary
  where candidate_scope_id = 07_e1_only

For split = all:
  e1_reference_event_n =
    E1 reference row.event_count

  e1_reference_events_per_instrument_year_mean =
    E1 reference row.events_per_instrument_year_mean

For split in (train, validation, robustness):
  E1 split reference =
    parse_json(E1 reference row.density_by_split)[current split]

  e1_reference_event_n =
    E1 split reference.event_count

  e1_reference_events_per_instrument_year_mean =
    E1 split reference.events_per_instrument_year

density_vs_07_E1_only =
  candidate events_per_instrument_year_mean
  / e1_reference_events_per_instrument_year_mean
```

如果 split-level R-core 或 E1 reference 缺失，必须 fail closed：

```text
decision = 12A2_state_change_candidate_generation_blocked
block_reason IN (
  missing_r_core_density_reference_for_split,
  missing_07_e1_density_reference_for_split
)
```

### 9.7 `state_change_family_overlap_diagnostic.csv`

一行是一个 family 与另一个 family 在 raw / canonical 层面的 overlap 或 gap 归因切片。
该表用于 12A3 判断 recall 缺口来自 family 设计、C0 priority，还是 next-open / PIT gate。

必需字段：

```text
diagnostic_scope_id
family_id
overlap_family_id
split
raw_event_n
canonical_event_n
family_only_raw_event_n
family_only_canonical_event_n
overlap_raw_event_n
overlap_canonical_event_n
same_instrument_same_day_overlap_n
covered_06_episode_n
missed_06_episode_n
median_trading_days_from_episode_low
p25_trading_days_from_episode_low
p75_trading_days_from_episode_low
diagnostic_status
diagnostic_reason
```

必需切片：

```text
B8 vs B1
B8 vs B3
B8 vs B1_or_B3
B1 vs B3 same-day collision
```

### 9.8 `state_change_generation_decision.csv`

必需字段：

```text
decision
decision_reason
input_gate_pass
pit_feature_gate_pass
forbidden_feature_gate_pass
candidate_nonempty_gate_pass
train_candidate_presence_gate_pass
robustness_candidate_presence_gate_pass
next_open_executable_gate_pass
density_hygiene_gate_pass
primary_canonical_event_n
raw_instance_event_n
runnable_raw_instance_event_n
supported_raw_instance_event_n
next_open_executable_event_n
next_open_executable_rate
runnable_family_n
diagnostic_family_n
blocked_family_n
handoff_conflict_flag
block_reason
next_allowed_requirement
```

允许的 decision：

```text
12A2_state_change_candidate_generation_supported
12A2_state_change_candidate_generation_supported_with_density_caveat
12A2_state_change_candidate_generation_empty
12A2_state_change_candidate_generation_blocked
```

## 10. Gates

### 10.1 输入 gate

必须满足：

```text
所有 required input artifact exists；
所有 required columns present；
all_a benchmark present；
qfq_dir readable；
PIT membership universe row_count > 0；
PIT executable universe row_count > 0；
12A1 population_bridge_status = pass；
```

否则：

```text
decision = 12A2_state_change_candidate_generation_blocked
```

### 10.2 PIT feature gate

必须满足：

```text
每个 allowed primary family 的 required features available_at_t0_close_flag = true；
每个 allowed primary family 的 pit_audit_status = pass；
blocked industry family 不进入 primary canonical；
```

如果 B4 industry 版本被 blocked，不影响可运行 B4 board/topn proxy 版本。

### 10.3 forbidden feature gate

必须满足：

```text
uses_future_return_flag = false
uses_episode_label_flag = false
uses_label_touch_coordinate_flag = false
forbidden_feature_scan_status = pass
```

任何 family 失败，则全 run blocked。

### 10.4 candidate non-empty gate

支持生成的最小要求：

```text
primary canonical event_n > 0
runnable_family_n >= 2
train primary canonical event_n > 0
robustness primary canonical event_n > 0
```

如果输入和 PIT gate 通过但没有事件：

```text
decision = 12A2_state_change_candidate_generation_empty
```

### 10.5 next-open executable gate

分母必须固定为：

```text
supported_raw_instance_event_n =
  raw event instances
  where family_input_status = runnable_existing_data
    and allowed_for_primary_canonical_flag = true
    and family_cooldown_status = pass
    and union_cooldown_status = pass
    and first_trigger_status IN (
      first_after_reset,
      first_observed_in_sample
    )
    and event_t0_pit_status = pass
    and market_regime_bucket != missing_insufficient_lookback
```

分子：

```text
next_open_executable_event_n =
  supported_raw_instance_event_n
  where non_executable_next_open = false
    and trade_open_pit_status = pass
```

Rate：

```text
next_open_executable_rate =
  next_open_executable_event_n / supported_raw_instance_event_n
```

支持状态要求：

```text
next_open_executable_rate >= 0.95
```

如果低于该值：

```text
decision = 12A2_state_change_candidate_generation_blocked
block_reason = next_open_executable_rate_below_floor
```

### 10.6 density hygiene gate

12A2 不是最终 backbone 支持判定，但需要避免产生比 R-core 更失控的候选池。

支持阈值：

```text
density_vs_08_r_core <= 1.25
rolling_10d_duplicate_rate <= 0.50
top_board_event_share <= 0.85
first_trigger_supported_rate >= 0.70
```

Gate 应用范围：

```text
必须在 split IN (all, train, robustness) 全部通过；
validation 只做 readout，不作为 blocker。
```

如果其他 gate 全通过但 density hygiene 失败：

```text
decision = 12A2_state_change_candidate_generation_supported_with_density_caveat
next_allowed_requirement = requirement_12a3_episode_precision_recall_frontier.md
```

如果 density hygiene 通过：

```text
decision = 12A2_state_change_candidate_generation_supported
next_allowed_requirement = requirement_12a3_episode_precision_recall_frontier.md
```

## 11. Report 要求

`state_change_candidate_generation_report.md` 必须用中文写，并至少包含：

1. A1 结论回顾：R-core 为 recall benchmark only；
2. B1-B8 family 是否 runnable，blocked / diagnostic family 为什么 blocked 或不能进入 primary；
3. 每个 family 的事件数、split 分布、executable rate；
4. primary canonical union 的密度、重复触发、board concentration；
5. forbidden feature / PIT audit 结论；
6. 12A2 decision 和 `next_allowed_requirement`；
7. 明确声明：12A2 不证明 episode recall / precision，12A3 才做 frontier；
8. 显式列出被 PIT 行业数据 block 掉的 state-change 维度：
   `R4_industry_breadth_expansion`、`T1_stock_vs_industry_CUSUM_break`、
   `T2_industry_vs_market_CUSUM_break`；
9. 输出 B1 vs B3 同日碰撞诊断，并由 `state_change_family_overlap_diagnostic.csv` 支撑：
   - same instrument + event_t0_date 同时触发 B1 和 B3 的 event_n；
   - C0 primary 选择 B1 / B3 的 event_n；
   - B1 event_t0_date 相对 06 `episode_low_date` 的 trading-day lag 分布；
   - B3 event_t0_date 相对 06 `episode_low_date` 的 trading-day lag 分布；
   - B1 primary 是否比 B3 primary 系统性更晚的结论；
10. 输出 B8 sustained trend state confirmation 的独立 readout，并由 `state_change_family_overlap_diagnostic.csv` 支撑：
    - B8 event_n、split 分布、density；
    - B8 `family_trigger_origin` 分布；
    - B8 与 B1/B3 的 overlap；
    - B8-only canonical events 是否解释“无穿越但趋势在位”的 recall 缺口。

## 12. Manifest

必需 manifest：

```text
outputs/manifests/12A2_state_change_backbone_candidate_generator_manifest.json
```

必需字段：

```text
run_id
experiment_id
legacy_directory_id
created_at
git_commit
python
platform
config_hash
input_artifacts
output_artifacts
output_hashes
decision
decision_reason
forbidden_feature_scan_hash
formula_spec_hash
canonicalization_spec_hash
```

`output_artifacts` 必须包含本需求第 9 节所有必需输出。

## 13. 实现提示

实现可以复用 08 pipeline 的以下逻辑，但必须在 12A2 runner 中显式记录 provenance：

```text
load_daily_inputs-style PIT feature loading
qfq daily feature enrichment
benchmark all_a return map
board equal-weight cross-section features
event_split assignment
event window anchor convention
density denominator convention
```

允许复用函数，不允许复用 08 已生成的 event hit 结果来冒充 12A2 event。

## 14. 验证命令

实现后至少运行：

```bash
cd topics/02_AFML_BIG_WINNER
python -m py_compile experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/src/run_12a2_state_change_backbone_candidate_generator.py
pytest -q experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/tests/test_12a2_state_change_backbone_candidate_generator.py
python experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/src/run_12a2_state_change_backbone_candidate_generator.py --mode check-inputs
python experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/src/run_12a2_state_change_backbone_candidate_generator.py --mode full
```

`check-inputs` 必须只生成 `input_artifact_audit.csv`，不得生成 candidate events。

## 15. 完成定义

12A2 run 完成条件：

```text
所有必需输出存在；
manifest output_hashes 覆盖所有输出；
state_change_generation_decision.csv 有且仅有一行；
decision IN (
  12A2_state_change_candidate_generation_supported,
  12A2_state_change_candidate_generation_supported_with_density_caveat,
  12A2_state_change_candidate_generation_empty,
  12A2_state_change_candidate_generation_blocked
)；
report 中文说明 candidate generation status；
```

12A2 downstream eligible 条件：

```text
decision IN (
  12A2_state_change_candidate_generation_supported,
  12A2_state_change_candidate_generation_supported_with_density_caveat
)；
forbidden feature gate pass；
PIT feature gate pass；
candidate_nonempty_gate_pass = true；
next_open_executable_gate_pass = true；
```

如果 decision 为 `12A2_state_change_candidate_generation_supported_with_density_caveat`，仍可进入 12A3，但 12A3 必须把 density caveat 作为 frontier 解读的一部分。

如果 decision 为 `12A2_state_change_candidate_generation_empty` 或 `12A2_state_change_candidate_generation_blocked`，run 可以完整结束，但不得进入 12A3。
