# 需求：高召回修复事件候选生成器 V0（04_high_recall_repair_event_candidate_generator_v0）

## 1. 目标

在 `topics/02_AFML_BIG_WINNER` 下，基于 02 的大赢家反向生命周期画像与 03 的可观测事件合约负结果，
构造一个**高召回、可观测、可执行、可审计的事件候选生成器**。

本实验的核心定位是：

```text
找 event candidate，不是训练 primary model；
追求对未来 big winner episode 的早期覆盖与样本池质量，不要求单个事件规则本身具备可交易 edge。
```

03 已证明：

```text
E_S3 = first_ema60_reclaim -> rank jump -> rank persistence
```

作为 universal entry 过窄、过晚、且 clean baseline coverage 不足。它能提高 `confirm_20` 触上界概率，
但 `failure_10` 也同步升高，`forward_return_20d` 不稳定。因此 04 不再尝试把 E_S3 继续收紧为
交易信号，而是把 t0 前移到 `candidate_seed_low`、`first_ema60_reclaim` 与 reclaim 后早期质量状态，
形成 primary model 后续可使用的候选事件池。

本实验回答的研究问题是：

```text
在不使用未来 winner outcome 作为特征、不训练模型、不做回测的前提下，
能否用一组宽口径、close-observed、next-open executable 的修复事件 family，
高召回地覆盖未来 big winner episode 的低点后早期路径，
并控制事件密度、可执行性、false-repair 诊断和标签完整性，
从而产出一个适合后续 primary model / meta-labeling 的候选事件样本池？
```

### 1.1 与 02 / 03 的关系

上游事实：

```text
02:
  big winner episode 共 866 个。
  EMA60 reclaim 是稳定生命周期 anchor：winner reference reclaim rate 约 95%-97%。
  但 EMA60 reclaim 不是充分买点：matched controls 的 reclaim rate 也很高。
  S3 rank persistence、S6 continuation 等强变量多数是确认指标。

03:
  E_S3 作为严格事件合约未获授权，decision = event_contract_sample_blocked。
  clean baseline coverage total = 63.5%，validation = 54.8%。
  E_S3 相对 clean baseline confirm20 lift = 1.44，但 failure10 diff = +6.9pct。
  E_S3 更像确认指标，不是高召回候选生成器。
```

04 的设计结论：

```text
first_ema60_reclaim 是稳定 anchor，但 anchor is not feature restriction。
候选事件必须覆盖 VWAP、money-flow、range-position、turnover、gap/fade、
early relative strength、false-repair avoidance 等修复质量特征。
```

## 2. 非目标（Non-Goals）

本实验不得：

- 训练 primary model、meta model、ranking model、分类器或回归器。
- 运行策略回测、组合净值、仓位、止损、止盈或调仓规则。
- 用单个事件 family 的前向收益 edge 授权交易化。
- 把低 precision 或高 false-positive 本身视为失败；只要 recall、密度、可执行性和标签丰富度达标，噪声可留给后续模型处理。
- 用未来 50% / 100% runup、未来 MFE、near-winner outcome、episode high 等信息生成事件 t0 或事件特征。
- 把 retrospective episode low 当作 t0 可用信息。
- 因为 validation / robustness 结果不好而移动切分边界、调低 recall gate、删改事件 family。
- 将 `risk_off` 直接硬排除出主候选池。risk_off 必须作为标注与诊断维度输出；是否作为后续模型特征或过滤门由下游决定。

## 3. 输入契约

主输入来自：

```text
01_data_prepare_pit_largecap_akshare_qlib_v0
  -> PIT 可执行股票池、个股日线、基准日线、交易日历

02_big_winner_reverse_lifecycle_profile_v0
  -> big winner episode reference、episode aligned panel、anchor / sequence 画像结果

03_observable_anchor_event_contract_v0
  -> E_S3 负结果、false-repair / baseline / execution 审计，作为设计依据只读
```

必需输入：

```text
PIT 可执行股票池：
  pit_largecap_main_chinext_executable_daily.csv

个股日线：
  qfq OHLCV、money、turnover
  raw OHLC 仅用于 VWAP 复权校验与涨跌停可执行性 proxy

基准指数日线：
  csi300、chinext_index、all_a

02 episode 参考：
  outputs/publishable/tables/big_winner_episode_reference_summary.csv
  outputs/local_cache/big_winner_episode_reference.parquet 或可重生成等价输入
  outputs/local_cache/episode_aligned_daily_panel.parquet 或可重生成等价输入

03 只读诊断：
  outputs/publishable/reports/observable_anchor_event_contract_report.md
  outputs/publishable/tables/event_vs_baseline_forward_stats.csv
  outputs/publishable/tables/false_repair_exclusion_audit.csv
  outputs/publishable/tables/baseline_t0_timing_audit.csv
```

若 02 local_cache / large_raw 不在 Git 中，04 可以按相同上游 git revision 与 manifest hash 重新生成只读输入；
不得仅用 publishable 汇总表伪造逐日路径。所有输入路径、hash、上游 decision、上游 git revision 必须写入
`outputs/manifests/run_manifest.json`。

若 02 的最终决策不是 `reverse_lifecycle_sequence_supported_universal_dominance`，或 03 的最终决策不是
`event_contract_sample_blocked` / `event_contract_no_baseline_separation` / `event_contract_false_repair_filter_dominant_no_rank_persistence_separation`
等合法负结果之一，04 必须 fail closed，并在报告中说明上游状态不满足本实验前提。

## 4. 日期范围与切分

沿用 02 / 03 的固定切分，但必须区分两种 split 口径：

```text
event_split:
  按 event_t0_date 分配，用于事件密度、可执行性、特征缺失、20d 标签与 precision / readiness 读数

episode_split:
  按 episode_low_date 分配，用于 target episode denominator 与 headline recall
```

任何 capture / recall 表都必须同时保留 `episode_split` 与首次捕获事件的 `event_split`，避免用事件日期切分污染
episode-level 召回归因。

```text
train:
  2017-01-03 <= date <= 2021-12-31

validation:
  2022-01-01 <= date <= 2023-12-31

robustness event pool:
  2024-01-01 <= event_t0_date <= latest_main_label_complete_t0_date
```

必须拆分两个 horizon 完整性边界：

```text
latest_main_label_complete_t0_date:
  至少保证主 AFML 标签 horizon = 20 trading sessions 完整

latest_120d_outcome_complete_t0_date:
  至少保证候选生成器 outcome horizon = 120 trading sessions 完整，
  用于 big_winner / near_winner / MFE / precision 标签
```

如果某个 event t0 满足 20 日标签完整但不满足 120 日 outcome 完整：

```text
main_barrier_label_complete = true
candidate_outcome_120d_status = censored_incomplete_horizon
```

该事件可以进入执行性 / 密度 / 20 日标签统计，但不得进入 120 日 big-winner label rate、precision、near-winner 或 forward MFE 统计。

## 5. Target Episode 定义（Recall 分母）

04 的 recall 分母来自 02 冻结的 canonical big winner episodes，不重新定义 winner：

```text
target_episode_id = 02 episode_id
target_episode_low_date = 02 episode_low_date
target_episode_high_date = 02 episode_high_date
target_mfe_120 = 02 mfe_120
target threshold: mfe_120 >= 50%
```

04 必须在个股逐日路径上补充计算：

```text
target_duration_sessions:
  episode_low_date 到 episode_high_date 的交易日距离

duration_bucket:
  优先复用 02 的冻结 duration bucket；
  若 02 未直接输出，则按 02 同口径由 target_duration_sessions 重算，
  并在 report / manifest 中写明 fast / medium / long 的 cutoff 来源

first_50pct_touch_date:
  target episode low 后 120 个交易日内，
  首个 qfq_high[D] / qfq_low_at_low_date - 1 >= 0.50 的日期

first_100pct_touch_date:
  同窗口内首个 qfq_high[D] / qfq_low_at_low_date - 1 >= 1.00 的日期，若不存在则 missing_event_absent
```

这些日期只用于 outcome 评估与 lead-time 统计，不得作为事件特征。

target episode 可用性：

```text
target_recall_denominator =
  02 canonical episode
  and first_50pct_touch_date present
  and target episode has required daily path coverage
```

报告必须分别给出 all / train / validation / robustness 的 denominator。

## 6. 候选事件设计原则

04 的候选事件必须是宽口径 union event family。原则：

```text
high_recall_first: 先覆盖未来大赢家 episode，再由后续模型处理 precision
close_observed:    所有事件状态只用截至 t0 收盘信息
next_open_executable: t0 后次一可成交开盘可评估
feature_rich:      输出足够宽的 as-of 特征快照，供后续 primary model 使用
density_controlled: 每股事件不能爆炸
outcome_separated: future MFE / big winner 标签只能作为 label，不可作为特征
```

事件 family 应按“早到晚”分层输出，而不是只输出一个严格事件：

```text
E0_seed_low_setup
E1_first_ema60_reclaim
E2_reclaim_quality_burst
E3_early_no_false_repair
E4_early_relative_strength_turn
E5_strict_rank_persistence_reference
E_union_high_recall_repair_candidate
E_union_reclaim_based_candidate
```

`E5_strict_rank_persistence_reference` 只是 03 E_S3 的参考复现 / 分层列，不能作为 04 的主 candidate generator。
`E_union_high_recall_repair_candidate` 是 setup-inclusive 主候选池，必须包含 E0。
`E_union_reclaim_based_candidate` 是 secondary / model-ready 读数，用于观察不含 E0 时的样本质量与密度。

## 7. 事件 Family 定义

### 7.1 E0_seed_low_setup

目的：捕捉低位修复观察起点，最大化早期覆盖。

```text
event_family = E0_seed_low_setup
event_t0_date = D

D 满足：
  qfq_low[D] 是 [D - 60 trading sessions, D] 的最低 qfq_low
  D 有 >= 250 个历史交易日
  instrument 在 D 属于 PIT executable universe
```

E0 是宽口径 setup，不要求 EMA60 reclaim。它的 precision 预计较低，主用途是：

```text
episode_low_proximity_recall
lead-time upper bound
后续模型候选池的最早观察点
```

E0 进入主候选池是为了最大化 recall，但必须防止把 headline 误读为“有信息 edge”。02 的 episode low
本身通常接近局部低点，因此 E0 对 low+20 / low+30 recall 可能形成近似同义反复。报告和 final decision
必须把 E0 依赖作为与 headline 同级的解释项披露：

```text
E0_only_capture_share
recall_without_E0
marginal_recall_E0_over_reclaim_based
marginal_recall_E1/E2/E4_over_E0
```

若主 recall 主要由 E0-only 捕获贡献，实验仍可支持高召回候选池，但只能解释为“宽网样本池可覆盖”，不能解释为
“修复质量规则已经具备独立识别力”。

### 7.2 E1_first_ema60_reclaim

目的：捕捉 02 已证明稳定的生命周期 anchor。

```text
event_family = E1_first_ema60_reclaim
seed = E0_seed_low_setup
anchor_search_end = seed + 120 trading sessions

event_t0_date = first D after seed, 满足：
  qfq_close[D-1] < ema60[D-1]
  qfq_close[D]   >= ema60[D]
```

E1 不要求 money / rank / persistence 条件。它是 04 的默认主 anchor event。

### 7.3 E2_reclaim_quality_burst

目的：在不大幅损失 recall 的情况下，标注 reclaim 附近的量价质量。

E2 不是硬过滤门，而是一组 close-observed quality flags。实现必须输出独立 raw event 行，同时也把 E2 flags
写回同一 union cluster 的 canonical union 行；否则无法做 E2 recall / ablation / density-loss 归因。

在 `E1` 的 reclaim 日 `r0` 至 `r0 + 5` 交易日内，首次满足任一 quality flag 即形成 E2：

```text
event_family = E2_reclaim_quality_burst
event_t0_date = first quality flag date

quality flags:
  amount_ratio_20d >= 1.50
  or amount_ratio_60d >= 1.20
  or close_to_derived_daily_vwap >= 0
  or vwap_reclaim_flag = true
  or close_position_in_range >= 0.60
  or gap_fade_flag_status = not_missing
     and gap_fade_flag = false
     and upper_shadow_pct <= 0.35
```

`gap_fade_flag` 不得把缺失当作 false。所有 quality flag 必须输出 `<flag>_status`，取值至少包括
`not_missing`、`missing_source_field`、`missing_insufficient_lookback`、`missing_unit_incompatible`。
这些阈值为 v0 fixed_contract_constant，不得用 validation / robustness 调参。

### 7.4 E3_early_no_false_repair

目的：把 03 中重要的 false-repair 问题前移为可观测诊断。

E3 是 reclaim 后早期生存状态，不是主入口必要条件。

```text
event_family = E3_early_no_false_repair
base = E1_first_ema60_reclaim

variant:
  E3_5d:
    event_t0_date = r0 + 5 trading sessions
    no qfq_close[t] / qfq_close[r0] - 1 <= -0.10 for t in [r0, r0 + 5]

  E3_10d:
    event_t0_date = r0 + 10 trading sessions
    no qfq_close[t] / qfq_close[r0] - 1 <= -0.10 for t in [r0, r0 + 10]
```

E3 的主要 readout 是：

```text
recall loss vs false_repair reduction
lead-time loss
downstream label enrichment
```

### 7.5 E4_early_relative_strength_turn

目的：捕捉比 03 S3 更早的相对强度转向，不要求 20 日 persistence。

```text
event_family = E4_early_relative_strength_turn
base = E1_first_ema60_reclaim
search_window = [r0, r0 + 10 trading sessions]

event_t0_date = first D in search_window satisfying any:
  stock_vs_market_5d[D]  >= 0.03
  or stock_vs_market_10d[D] >= 0.05
  or stock_vs_market_20d[D] >= 0.05
```

若 5d / 10d 相对强度字段当前不存在，实现必须按 close-observed 方式派生：

```text
stock_vs_market_Nd = stock_return_Nd - benchmark_return_Nd
```

行业数据不可用时，行业 beta 拆分跳过并写入 caveat；不得用非 PIT 行业主张主结论。

### 7.6 E5_strict_rank_persistence_reference

目的：复现 03 E_S3 作为严格确认参考。

```text
event_family = E5_strict_rank_persistence_reference
definition = 03 E_S3
```

E5 不得进入 04 主 union 的 high-recall gate。它只用于说明“越严格越晚、recall 如何变化”。

### 7.7 E_union_high_recall_repair_candidate

主候选事件池是 setup-inclusive 宽 union。因为 04 是 event candidate generator，目标是尽量早且高召回地覆盖
未来大赢家 episode，E0 必须进入主候选池：

```text
E_union_high_recall_repair_candidate =
  E0_seed_low_setup
  union E1_first_ema60_reclaim
  union E2_reclaim_quality_burst
  union E4_early_relative_strength_turn
```

secondary model-ready union 用于观察不含 E0 时的样本质量、可执行性、precision 与后续模型准备度：

```text
E_union_reclaim_based_candidate =
  E1_first_ema60_reclaim
  union E2_reclaim_quality_burst
  union E4_early_relative_strength_turn
```

E3 是 survival diagnostic，可作为分层，不默认硬过滤。
E5 是 strict reference，不进入主 union。

若 E0、E1、E2、E4 在同一 instrument 的相近日期重复触发，必须保留 event_family 原始行，同时按 union family
分别产出 canonical union 行：

```text
canonical_union_event_t0_date =
  同一 instrument、同一 union_cluster 内最早的 event_t0_date，不论该事件次日开盘是否可执行

union_cluster:
  对同一 instrument、同一 union_family 的 event_t0_date 升序，
  非链式直接区间去重 window = 20 trading sessions

union_family:
  setup_inclusive = E0/E1/E2/E4
  reclaim_based   = E1/E2/E4
```

canonical 选取不得使用 `non_executable_next_open`。可执行性必须作为 canonical 行的下游标注列与 hard gate
单独审计；否则 canonical 集合的 executable rate 会被构造性推高，使 `min_executable_rate` 失去约束力。

## 8. 密度控制

高 recall 不等于无限事件。必须三层审计：

```text
seed-level density:
  E0 seed low 20 trading day non-chain direct interval dedup

anchor-level density:
  E1 reclaim 20 trading day non-chain direct interval dedup

setup-inclusive union-level density:
  E0/E1/E2/E4 union events 20 trading day non-chain direct interval dedup

reclaim-based union-level density:
  E1/E2/E4 union events 20 trading day non-chain direct interval dedup
```

所有被折叠的候选都必须保留在 local / large raw 审计中，并在 publishable `event_density_audit.csv`
中汇总：

```text
event_family
union_family
event_split
year
raw_candidate_count
density_kept_count
density_folded_count
density_loss_capture_count
events_per_instrument_year_mean
events_per_instrument_year_p95
```

主 recall gate 使用 `E_union_high_recall_repair_candidate` 的 density-kept canonical union events。报告必须额外披露：

```text
raw_union_recall
canonical_union_recall
density_kept_union_recall
density_loss_recall = canonical_union_recall - density_kept_union_recall
```

上述四项必须分别按 `setup_inclusive` 与 `reclaim_based` 两个 union family 输出。headline 只使用
`setup_inclusive`，`reclaim_based` 是 secondary / model-readiness 读数。

## 9. 特征快照

每个候选事件 t0 必须输出 as-of close snapshot。至少包含：

```text
instrument
event_id
event_family
union_family
canonical_event_scope
event_t0_date
trade_open_date
trade_open_price
non_executable_next_open
event_family_priority
source_seed_low_date
first_ema60_reclaim_date
days_seed_to_event
days_reclaim_to_event
event_split
market_regime_bucket
benchmark_alias
board_bucket
is_st
total_market_cap_cny
liquidity_money_20d

close_to_ema20
close_to_ema60
ema20_slope_20d
ema60_slope_20d
return_5d
return_10d
return_20d
return_60d
stock_vs_market_5d
stock_vs_market_10d
stock_vs_market_20d
amount_ratio_20d
amount_ratio_60d
turnover_ratio_20d
turnover_ratio_60d
derived_daily_vwap_available
close_to_derived_daily_vwap
vwap_reclaim_flag
intraday_range_pct
close_position_in_range
upper_shadow_pct
gap_open_pct
gap_fade_flag
gap_fade_flag_status
atr_20_pct

quality_amount_flag
quality_vwap_flag
quality_range_flag
quality_gap_fade_flag
quality_amount_flag_status
quality_vwap_flag_status
quality_range_flag_status
quality_gap_fade_flag_status
early_no_false_repair_5d
early_no_false_repair_10d
early_relative_strength_turn_flag
strict_rank_persistence_reference_flag
```

### 9.1 执行性 proxy

04 必须沿用 03 第 8.1 节的 next-open executable 口径，并在本实验内重述如下，防止实现漂移：

```text
t0          = event_t0_date（收盘确认）
trade_time  = next_executable_open_after_t0（次一可成交开盘）
price_basis = qfq
执行价      = trade_open_date 的 qfq_open
```

日频 OHLCV 不能真实观测开盘排队成交，只能做保守 proxy。实现必须 fail closed：

```text
missing_open_or_volume:
  qfq_open 缺失、volume <= 0、money <= 0 或交易日缺失
  -> non_executable_next_open

one_price_limit_open_proxy:
  qfq_open == qfq_high == qfq_low == qfq_close
  且 abs(raw_open / previous_raw_close - 1) 接近当日涨跌停阈值
  -> non_executable_next_open

limit_threshold_status:
  若无法从证券板块 / ST 状态确定 10% / 20% / 5% 等涨跌停阈值，
  标记 limit_rule_unavailable，并把该 trade_open 视为 non_executable_next_open
```

不可执行事件不得静默丢弃；必须进入 `executability_audit.csv`，并在 recall / density / label completeness
的分母口径中明确是否位于执行性过滤之前或之后。

缺失字段必须使用显式状态，不得用 0 填充：

```text
missing_insufficient_lookback
missing_event_absent
missing_source_field
missing_unit_incompatible
missing_out_of_coverage
censored_incomplete_horizon
non_executable_next_open
```

## 10. 标签与 Outcome

04 输出标签用于评估候选池与后续模型训练准备度，不用于事件生成。

### 10.1 主 AFML 标签

沿用 03：

```text
confirm_20:
  horizon_days  = 20
  upper_barrier = +0.12
  lower_barrier = -0.08
  touch_priority = lower_barrier_first

failure_10:
  horizon_days = 10
  lower_barrier = -0.10
```

主 AFML 标签只作为 interim tradeability / repair durability proxy：

```text
confirm_20:
  观察事件后 20 日内是否有短期可交易推进

failure_10:
  观察事件后 10 日内是否快速假修复
```

它们不是 120 日 big-winner 的代理标签。一个最终 120 日 +50% 的 episode，事件后 20 日内仍可能先触及
`-8%` 下界。后续 primary / meta 研究必须显式选择目标：

```text
primary_big_winner_objective:
  使用 event_big_winner_120d_label / event_near_winner_120d_label

interim_tradeability_objective:
  使用 confirm_20 / failure_10
```

04 必须同时输出两组标签，但报告不得用 `confirm_20` 的好坏替代 `event_big_winner_120d_label` 的模型目标准备度。

### 10.2 候选生成器 outcome 标签

每个 event t0 还必须输出：

```text
forward_return_10d
forward_return_20d
forward_return_30d
forward_return_60d
forward_return_120d
mfe_10d / mae_10d
mfe_20d / mae_20d
mfe_30d / mae_30d
mfe_60d / mae_60d
mfe_120d / mae_120d
horizon_complete_10d / 20d / 30d / 60d / 120d

event_big_winner_120d_label:
  mfe_120d >= 0.50

event_super_winner_120d_label:
  mfe_120d >= 1.00

event_near_winner_120d_label:
  0.30 <= mfe_120d < 0.50

event_false_repair_10d_label:
  min close drawdown from event close <= -0.10 within next 10 trading sessions

event_false_repair_20d_label:
  min close drawdown from event close <= -0.10 within next 20 trading sessions
```

10d / 20d / 30d / 60d / 120d 的 forward return、MFE、MAE 只作为 diagnostic / model-readiness 标签，
不得反向参与事件触发或阈值调参。

所有 120d outcome label 必须有 `candidate_outcome_120d_status`。右截断事件不得进入 120d precision / positive-rate 统计。

### 10.3 Target Episode Capture Label

对每个 target episode，查找同一 instrument 的 candidate events：

```text
capture_pre_low_20d:
  exists event_t0_date in [episode_low_date - 20, episode_low_date]

capture_low_to_plus_10d:
  exists event_t0_date in [episode_low_date, episode_low_date + 10 trading sessions]

capture_low_to_plus_20d:
  exists event_t0_date in [episode_low_date, episode_low_date + 20 trading sessions]

capture_low_to_plus_30d:
  exists event_t0_date in [episode_low_date, episode_low_date + 30 trading sessions]

capture_low_to_plus_60d:
  exists event_t0_date in [episode_low_date, episode_low_date + 60 trading sessions]

capture_low_to_plus_120d:
  exists event_t0_date in [episode_low_date, episode_low_date + 120 trading sessions]

capture_before_first_50pct:
  exists event_t0_date in [episode_low_date, first_50pct_touch_date)

capture_before_episode_high:
  exists event_t0_date in [episode_low_date, episode_high_date)
```

预注册 co-headline recall metrics：

```text
pre_registered_early_window_recall =
  episode_recall_low_to_plus_30d on
  E_union_high_recall_repair_candidate / setup_inclusive / density-kept canonical events

episode_recall_low_to_plus_30d =
  captured target episodes / target_recall_denominator

pre_registered_actionable_recall =
  episode_recall_before_first_50pct on
  E_union_high_recall_repair_candidate / setup_inclusive / density-kept canonical events

episode_recall_before_first_50pct =
  captured target episodes before first_50pct_touch_date / target_recall_denominator
```

headline support metric：

```text
episode_recall_low_to_plus_20d
```

diagnostic recall：

```text
episode_recall_pre_low_20d
episode_recall_low_to_plus_10d
episode_recall_low_to_plus_60d
episode_recall_low_to_plus_120d
episode_recall_before_episode_high
late_after_first_50pct_capture_share:
  episodes captured by low+30 but not before first_50pct / episodes captured by low+30
```

`capture_pre_low_20d` 是 diagnostic-only，不进入 hard gate。它用于观察候选池是否能在 retrospective low
之前提前出现，但不得被解释为可稳定交易的低点识别能力，因为 episode low 本身不可事前知道。

Lead time：

```text
lead_time_to_first_50pct_sessions =
  first_50pct_touch_date - first_capturing_event_t0_date

lead_time_to_episode_high_sessions =
  episode_high_date - first_capturing_event_t0_date
```

若多个 event family 捕获同一 episode，必须记录最早 event 与各 family 首次捕获日期。

所有 co-headline recall 必须按 `duration_bucket` 拆分报告。特别是 fast duration bucket 不得被 all-episode
headline 均值掩盖；若 low+30 recall 高但 before-first-50pct recall 在 fast bucket 明显偏低，报告必须把结论写为
“候选池偏晚，快赢家可行动捕获不足”，不得用 low+30 headline 单独宣布成功。

## 11. Baseline / Precision 的定位

04 不以 matched baseline edge 为主 gate，但必须给出候选池 precision 与背景机会集对照。

背景机会集必须按 union family 分开：

```text
all density-kept setup_inclusive E_union candidates
all density-kept reclaim_based E_union candidates
non-target candidates:
  same candidate generation process
  but event_t0 后 120d MFE < 50%
near-winner candidates:
  30% <= event_t0 后 120d MFE < 50%
```

输出必须包含：

```text
event_big_winner_120d_rate
event_near_winner_120d_rate
event_false_repair_10d_rate
event_false_repair_20d_rate
positive_label_count
negative_label_count
class_balance_by_event_split
event_concurrency_mean / p95
average_uniqueness_mean / p25
cluster_positive_count
```

Precision / label rate 只用于 model-readiness 诊断，不作为阻塞 high recall 的主条件。若 positive rate 很低但 recall 与 density 达标，最终状态应为
`candidate_generator_supported_high_recall_noisy_precision`，而不是失败。

必须显式区分两种合法但不同的锚定口径：

```text
episode-anchored recall:
  以 02 target episode low 为锚，回答“候选池是否捕获了这个未来大赢家 episode”

event-anchored positive label:
  以 event_t0 为锚，回答“这个事件自身之后 120d MFE 是否达到 +50%”
```

同一个事件可能在 episode-anchored recall 中捕获了某个 target episode，但从该 event_t0 往后 120 日
`mfe_120d < 0.50`，因此在 event-anchored readiness 标签里是 negative。二者都必须保留，禁止混算或交叉解释：
recall headline 使用 episode-anchored 口径，downstream model readiness / class balance 使用 event-anchored 口径。

### 11.1 AFML concurrency / uniqueness 口径

downstream model readiness 必须按 AFML 重叠标签口径输出并发度与平均唯一性。默认对两个 label span 分别计算：

```text
label_span_20d:
  [trade_open_date, min(first_barrier_touch_date, trade_open_date + 20 trading sessions)]

label_span_120d:
  [trade_open_date, trade_open_date + 120 trading sessions]
  仅对 horizon_complete_120d = true 的事件计算
```

对任一 label horizon H：

```text
c_t(H):
  在交易日 t 仍处于 label_span_H 内的事件数

event_uniqueness_i(H):
  mean over t in label_span_i(H) of 1 / c_t(H)

average_uniqueness_mean(H):
  mean_i event_uniqueness_i(H)

average_uniqueness_p25(H):
  p25_i event_uniqueness_i(H)

event_concurrency_mean(H):
  mean_t c_t(H), restricted to dates with c_t(H) > 0

event_concurrency_p95(H):
  p95_t c_t(H), restricted to dates with c_t(H) > 0
```

`cluster_positive_count` 必须按 `union_cluster_id` 聚合：同一 union cluster 内任一 event-anchored 120d
positive，则该 cluster 记为 positive cluster。报告必须同时给 event-level positive count 与 cluster-level
positive count，避免密集候选把样本数虚增。

## 12. 验收门与最终决策

### 12.1 Hard Gates

唯一预注册 headline 检验是一组 co-headline，不允许事后只挑其中一个：

```text
E_union_high_recall_repair_candidate
union_family = setup_inclusive
event row = density-kept canonical
split = episode_split
metric_1 = episode_recall_low_to_plus_30d
metric_2 = episode_recall_before_first_50pct
```

主门槛：

```text
min_total_target_episode_count = 150
min_validation_target_episode_count = 30
min_robustness_target_episode_count = 30

min_total_episode_recall_low_to_plus_30d = 0.70
min_validation_episode_recall_low_to_plus_30d = 0.60
min_robustness_episode_recall_low_to_plus_30d = 0.60

min_total_episode_recall_before_first_50pct = 0.70
min_validation_episode_recall_before_first_50pct = 0.60
min_robustness_episode_recall_before_first_50pct = 0.60

min_total_episode_recall_low_to_plus_20d = 0.60
min_validation_episode_recall_low_to_plus_20d = 0.50
min_robustness_episode_recall_low_to_plus_20d = 0.50

max_setup_inclusive_events_per_instrument_year_p95 = 18
max_setup_inclusive_events_per_instrument_year_mean = 8

max_reclaim_based_events_per_instrument_year_p95 = 12
max_reclaim_based_events_per_instrument_year_mean = 6

min_executable_rate = 0.80
min_main_label_complete_rate = 0.70
min_120d_outcome_complete_rate_for_precision_readout = 0.60
min_supported_positive_rate_for_clean_support = 0.10
max_supported_false_repair_20d_rate_for_clean_support = 0.50
```

validation / robustness 的 recall 门低于 total 门，是因为 04 检验的是宽网候选生成器的跨期覆盖能力，而不是
事件 edge 或交易收益；较小 split denominator 下允许固定 guard band。该 guard band 必须在运行前冻结，不得根据
validation / robustness 结果回调阈值、移动切分或删改 event family。

`min_executable_rate` 的分母是 density-kept canonical events 中执行性过滤之前的候选事件数，分子才是
`non_executable_next_open = false` 的事件数；不得在先剔除 non-executable 后再计算可执行率。
`executability_audit.csv` 必须分别披露 raw events、canonical events、density-kept canonical events 的
non-executable count 与 executable rate，证明 canonical 选取没有使用执行性信息。

before-first-50pct 是 hard gate，代表“仍在 50% 机会窗口之前捕获”。low+30 是早期窗口 hard gate，代表
“低点后固定时间内出现候选”。二者必须同时过门。60d / 120d 捕获率只作为 diagnostic，不得替代 low+20 /
low+30 / before-first-50pct headline。

上述 hard gates 的 recall 与密度主判定只用于 `E_union_high_recall_repair_candidate`
的 `setup_inclusive` density-kept canonical events。`E_union_reclaim_based_candidate`
必须单独报告并通过 secondary density audit，但不得用其好坏替代 headline。

### 12.2 Soft Diagnostics

以下不作为 hard fail，但必须报告：

```text
event_big_winner_120d_rate
event_near_winner_120d_rate
false_repair_10d_rate
false_repair_20d_rate
risk_off recall / density / false_repair
episode_recall_pre_low_20d
episode_recall_low_to_plus_10d / 60d / 120d
episode_recall_low_to_plus_30d by duration_bucket
episode_recall_before_first_50pct by duration_bucket
late_after_first_50pct_capture_share by duration_bucket
average lead_time_to_first_50pct
median lead_time_to_first_50pct
raw vs canonical vs density-kept recall loss by union_family
positive / negative sample count for downstream model
event concurrency / average uniqueness / cluster positive count
```

### 12.3 Allowed Decisions

```text
candidate_generator_data_blocked
candidate_generator_no_target_recall
candidate_generator_executability_blocked
candidate_generator_total_recall_blocked
candidate_generator_validation_recall_blocked
candidate_generator_robustness_recall_blocked
candidate_generator_recall_supported_density_blocked
candidate_generator_coverage_supported_actionability_late_blocked
candidate_generator_supported_high_recall_noisy_precision
candidate_generator_supported_high_recall
```

decision 必须按以下顺序短路求值，命中即返回。不得在同一运行中输出多个 final decision：

```text
1. candidate_generator_data_blocked
2. candidate_generator_no_target_recall
3. candidate_generator_executability_blocked
4. candidate_generator_total_recall_blocked
5. candidate_generator_validation_recall_blocked
6. candidate_generator_robustness_recall_blocked
7. candidate_generator_recall_supported_density_blocked
8. candidate_generator_coverage_supported_actionability_late_blocked
9. candidate_generator_supported_high_recall_noisy_precision
10. candidate_generator_supported_high_recall
```

短路规则：

- 若输入路径、上游 manifest、上游 decision、交易日历、PIT universe 或必要标签 horizon 不完整，返回
  `candidate_generator_data_blocked`。
- 若 target episode denominator 不满足 `min_total_target_episode_count`、`min_validation_target_episode_count` 或
  `min_robustness_target_episode_count`，返回 `candidate_generator_no_target_recall`。
- 若 `min_executable_rate` 或 `min_main_label_complete_rate` 不过门，返回
  `candidate_generator_executability_blocked`。
- 若 total 的 low+30 fixed-window recall 或 low+20 support recall 不过门，返回
  `candidate_generator_total_recall_blocked`。
- 若 validation 的 low+30 fixed-window recall 或 low+20 support recall 不过门，返回
  `candidate_generator_validation_recall_blocked`。
- 若 robustness 的 low+30 fixed-window recall 或 low+20 support recall 不过门，返回
  `candidate_generator_robustness_recall_blocked`。
- 若 fixed-window recall 与 executability 过门，但任一主密度门超标，返回
  `candidate_generator_recall_supported_density_blocked`。
- 若 low+20 support recall、low+30 fixed-window recall、executability 与 density 全部过门，但
  before-first-50pct actionable recall 在 total、validation 或 robustness 任一主 split 不过门，返回
  `candidate_generator_coverage_supported_actionability_late_blocked`。该状态表示“候选池能覆盖 episode，但系统性偏晚”，
  下一步应寻找更早 anchor，而不是继续收紧修复质量过滤。
- 若 recall / density / executability / label completeness 全部过门，但 `event_big_winner_120d_rate`
  低于 `min_supported_positive_rate_for_clean_support`，或 `event_false_repair_20d_rate`
  高于 `max_supported_false_repair_20d_rate_for_clean_support`，返回
  `candidate_generator_supported_high_recall_noisy_precision`。这仍然授权进入后续 primary model 研究。
- 若 recall / density / executability / label completeness 全部过门，且 false-repair 与 precision 达到上述 clean-support
  阈值，返回 `candidate_generator_supported_high_recall`。
- 本实验不得输出任何交易授权 decision。

## 13. 输出产物

必须生成：

```text
outputs/publishable/reports/high_recall_repair_event_candidate_report.md

outputs/publishable/tables/event_family_definition.csv
outputs/publishable/tables/candidate_event_instances.csv
outputs/publishable/tables/candidate_event_label_outcomes.csv
outputs/publishable/tables/episode_capture_audit.csv
outputs/publishable/tables/event_family_recall_stats.csv
outputs/publishable/tables/event_family_ablation_audit.csv
outputs/publishable/tables/duration_bucket_actionable_recall.csv
outputs/publishable/tables/lead_time_distribution.csv
outputs/publishable/tables/event_density_audit.csv
outputs/publishable/tables/density_loss_capture_audit.csv
outputs/publishable/tables/event_precision_label_readout.csv
outputs/publishable/tables/false_repair_diagnostic_by_family.csv
outputs/publishable/tables/regime_recall_density_audit.csv
outputs/publishable/tables/downstream_model_readiness_audit.csv
outputs/publishable/tables/executability_audit.csv
outputs/publishable/tables/data_source_coverage_audit.csv

outputs/manifests/run_manifest.json

outputs/local_cache/candidate_event_panel.parquet
outputs/local_cache/episode_capture_panel.parquet
outputs/large_raw/raw_candidate_event_pool.parquet
outputs/large_raw/event_daily_aligned_panel.parquet
```

`local_cache` 与 `large_raw` 可被 `.gitignore` 排除，但 manifest 必须记录路径、hash（若存在）和可重生成说明。

### 13.1 candidate_event_instances.csv schema

必须包含：

```text
event_id
instrument
event_family
union_family
canonical_event_scope
event_t0_date
trade_open_date
trade_open_price
non_executable_next_open
source_seed_low_date
first_ema60_reclaim_date
union_cluster_id
union_density_kept
event_family_priority
event_split
market_regime_bucket
board_bucket
all snapshot fields from section 9
```

### 13.2 episode_capture_audit.csv schema

必须包含：

```text
episode_id
instrument
episode_low_date
first_50pct_touch_date
episode_high_date
target_duration_sessions
episode_split
duration_bucket
market_regime_bucket
captured_by_setup_inclusive_density_kept_pre_low_20d
captured_by_setup_inclusive_density_kept_low_to_plus_10d
captured_by_setup_inclusive_raw_low_to_plus_20d
captured_by_setup_inclusive_raw_low_to_plus_30d
captured_by_setup_inclusive_canonical_low_to_plus_20d
captured_by_setup_inclusive_canonical_low_to_plus_30d
captured_by_setup_inclusive_density_kept_low_to_plus_20d
captured_by_setup_inclusive_density_kept_low_to_plus_30d
captured_by_setup_inclusive_density_kept_low_to_plus_60d
captured_by_setup_inclusive_density_kept_low_to_plus_120d
captured_by_setup_inclusive_raw_before_first_50pct
captured_by_setup_inclusive_canonical_before_first_50pct
captured_by_setup_inclusive_density_kept_before_first_50pct
captured_by_reclaim_based_pre_low_20d
captured_by_reclaim_based_low_to_plus_20d
captured_by_reclaim_based_low_to_plus_30d
captured_by_reclaim_based_density_kept_before_first_50pct
density_loss_capture_low_to_plus_20d
density_loss_capture_low_to_plus_30d
density_loss_capture_before_first_50pct
late_after_first_50pct_capture_flag
first_capturing_event_id
first_capturing_event_family
first_capturing_event_t0_date
first_capturing_event_split
lead_time_to_first_50pct_sessions
lead_time_to_episode_high_sessions
captured_by_E0
captured_by_E1
captured_by_E2
captured_by_E3
captured_by_E4
captured_by_E5
missing_reason
```

### 13.3 downstream_model_readiness_audit.csv schema

必须包含：

```text
event_split
event_family
union_family
label_horizon
event_count
label_complete_20d_count
outcome_complete_120d_count
big_winner_120d_positive_count
near_winner_120d_count
negative_count
positive_rate
events_per_instrument_year_mean
events_per_instrument_year_p95
event_concurrency_mean
event_concurrency_p95
average_uniqueness_mean
average_uniqueness_p25
cluster_positive_count
feature_missing_rate_mean
feature_missing_rate_p95
status
```

### 13.4 candidate_event_label_outcomes.csv schema

必须包含：

```text
event_id
instrument
event_t0_date
trade_open_date
event_split
union_family
union_cluster_id
label_anchor_type = event_anchored
confirm_20_label
failure_10_label
forward_return_10d / 20d / 30d / 60d / 120d
mfe_10d / 20d / 30d / 60d / 120d
mae_10d / 20d / 30d / 60d / 120d
horizon_complete_10d / 20d / 30d / 60d / 120d
event_big_winner_120d_label
event_near_winner_120d_label
event_super_winner_120d_label
candidate_outcome_120d_status
captured_target_episode_count
captured_target_episode_id_first
captured_target_episode_anchor_note = episode_anchored_recall_not_event_positive_label
```

### 13.5 event_family_ablation_audit.csv schema

必须包含：

```text
episode_split
duration_bucket
union_family
ablation_variant
recall_low_to_plus_20d
recall_low_to_plus_30d
recall_before_first_50pct
E0_only_capture_share
recall_without_E0
marginal_recall_E0_over_reclaim_based
marginal_recall_E1_E2_E4_over_E0
event_density_p95
event_density_mean
interpretation_caveat
```

## 14. 报告要求

报告必须用中文写，并明确声明：

```text
本实验是 event candidate generator，不是 primary model、不是策略、不是回测。
高 recall 是主目标，precision / false positive 噪声可留给后续模型。
```

报告至少包含：

- 输入路径、上游 manifest hash、git revision。
- 02 / 03 对本实验的设计约束。
- target episode denominator by episode_split / year / regime。
- 各 event family 的 raw count、density-kept count、事件密度。
- 两个 union family 的 episode recall：pre-low 20、low+10、low+20、low+30、low+60、low+120、
  before first 50pct、before high。
- 预注册 co-headline replay：setup-inclusive density-kept canonical union 的 low+30 recall 与 before-first-50pct recall。
- low+20 support recall，以及 low+30 captured 但 first_50pct 之后才捕获的 late capture share。
- co-headline recall 按 duration_bucket 拆分，尤其必须单列 fast bucket 的 before-first-50pct recall。
- pre-low 20 diagnostic recall，并明确它不代表事前识别 retrospective low 的能力。
- raw / canonical / density-kept recall 差异，以及 density folding 导致的捕获损失。
- lead-time 分布：均值、中位数、p25/p75、按 episode_split / duration bucket。
- event family ablation 必须与 headline 同级解读：E0-only capture share、without-E0 recall、E1/E2/E4 对 E0 的边际贡献、
  E0 对 reclaim-based union 的边际贡献。
- false-repair 诊断：按 family / event_split / regime。
- risk_off 专项读数：recall、density、false-repair、precision。
- downstream model readiness：样本数、正负样本、标签完整性、特征缺失、concurrency、average uniqueness。
- 10d / 20d / 30d / 60d / 120d forward return、MFE、MAE diagnostic 标签概览。
- episode-anchored recall 与 event-anchored positive label 的差异说明，不得把捕获 episode 的 event negative 样本误解释为矛盾。
- confirm_20 / failure_10 与 event_big_winner_120d_label 的 horizon mismatch 说明。
- final decision replay。
- 下一阶段是否授权 primary model 研究；不得授权交易化。

## 15. 测试与验证

聚焦测试必须覆盖：

- 合成 big winner path 上的 `first_50pct_touch_date` 计算。
- E0 trailing low 只使用过去窗口，不看未来。
- E1 EMA60 reclaim close-observed 搜索边界。
- E2 quality flags 使用 t0 当日或之前数据，并必须输出独立 raw event 行。
- E2 gap_fade_flag 缺失不得被解释为 false。
- E3 no-false-repair 5d / 10d 不提前使用未完成窗口。
- E4 early relative strength 不要求 20d persistence。
- E_union 非链式直接区间去重，保留 raw family 行与 setup-inclusive / reclaim-based canonical union 行。
- canonical union event 选取最早 event_t0_date，不得因为最早事件 non-executable 而跳到更晚 executable 事件。
- min_executable_rate 在 density-kept canonical events 上用执行性过滤前分母计算。
- episode capture window：pre-low 20、low+10、low+20、low+30、low+60、low+120、before first 50pct。
- low+30 捕获但 first_50pct 之后才捕获的 episode 必须计入 low+30，但不得计入 actionable before-first recall。
- low+30 / low+20 过门但 before-first-50pct 不过门时，decision 必须为
  `candidate_generator_coverage_supported_actionability_late_blocked`。
- duration_bucket 拆分 recall 不得使用 event_split。
- headline recall 使用 episode_split，不使用 event_split。
- event density / executability / label completeness 使用 event_split。
- non_executable_next_open 沿用 03 one-price-limit proxy 与 limit_rule_unavailable fail-closed。
- lead-time 计算不使用 event 之后不可观测信息作为特征。
- 120d outcome censoring 不影响 20d 主标签完整性。
- risk_off 不被硬排除，只作为 regime 标注。
- density gate 使用 setup-inclusive density-kept canonical union events，不用 raw folded events 凑 headline recall。
- raw / canonical / density-kept recall loss 归因必须可复算。
- AFML concurrency / average uniqueness 在重叠 label span 上可复算。
- event-anchored negative label 与 episode-anchored captured episode 可同时成立。
- downstream model readiness 不训练任何模型。

## 16. 实现约束

- 代码必须位于 `04_high_recall_repair_event_candidate_generator_v0/code/`。
- 配置必须位于 `config.yaml`，所有阈值、窗口、gate 必须配置化并写入 threshold audit。
- 不得修改 01 / 02 / 03 的代码或产物。
- 可以复用 02 / 03 的纯函数，但必须通过只读 import 或复制必要逻辑，不能让 04 运行时改写上游输出。
- 全量运行必须从 `topics/02_AFML_BIG_WINNER` 目录使用 `uv run` 可复现。
- publishable CSV 必须小于 GitHub 安全边界；大型逐日 panel 放入 local_cache / large_raw。

## 17. 最终边界

04 的成功只授权：

```text
进入后续 primary model / meta-labeling / feature ranking 研究
```

04 的成功不授权：

```text
交易策略
组合回测
实盘模拟
单规则买入
```

如果 04 失败，正确动作不是收紧成 E_S3，而是诊断：

```text
recall 不足：事件 t0 太晚或 anchor 覆盖不足
density 过高：seed / reclaim / union clustering 需要更强去重
validation recall 失败：高 recall 事件对 2022-2023 负 beta 压力窗不稳
false-repair 过高：后续模型必须优先学习 repair durability
```
