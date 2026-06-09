# 需求：可观测锚点事件合约 V0（03_observable_anchor_event_contract_v0）

## 1. 目标

在 `topics/02_AFML_BIG_WINNER` 下，把 `02_big_winner_reverse_lifecycle_profile_v0`
画像阶段中通过匹配对照、跨切分稳健的序列证据，固化为一个**可观测、收盘可计算、
次日开盘可执行**的事件合约，并用 AFML 三重壁垒标签在样本外评估该事件相对匹配基线
是否具备前向区分度。

本实验回答的研究问题是：

```text
把 EMA60 reclaim 作为对齐锚点，将“修复后相对强度跳升并持续”（S3）固化为
close-observed、next-open executable 的事件 t0 之后，该事件相对匹配基线事件，
是否在样本外（2022-2023 负 beta 验证窗 + 2024+ robustness）仍具备前向标签优势，
并能稳定剔除 false-repair？
```

本实验产出的是**冻结的事件合约定义 + 事件标签数据集 + 匹配基线前向统计**。它不是
策略、不是组合规则、不是回测、不是模型。事件是否“值得交易”由后续阶段决定，本阶段
只负责证明事件是否可执行、是否具备样本外前向 edge、是否可控 false-repair。

### 1.1 上游授权与定位

本实验由 `02_big_winner_reverse_lifecycle_profile_v0` 的最终决策
`reverse_lifecycle_sequence_supported_universal_dominance` 授权。授权范围严格限定为：

```text
仅将以下三条已 supported 的序列改写为事件合约候选：
  S3_repair_rank_persistence_v0   -> 主事件（primary event）
  S6_continuation_discriminator_v0 -> 条件性确认 / 加仓确认（conditional confirmation）
  S2_repair_money_vwap_v0          -> 弱过滤门（weak gate）
```

画像阶段的明确结论是本合约的设计前提：

```text
EMA60 reclaim 是稳定对齐锚点，不是充分买点（winner 与 control reclaim 率均接近必然）。
低点当天单因子无领先区分（最高非路径 SMD 约 0.35，且为 no_claim）。
强单因子（return_60d / ema60_slope / atr 等）多为 +20/+60/+120 确认变量，不可前置成 t0。
false-repair 在 EMA60 anchor control 中占 74.4%，必须显式排除。
S6 在 near-winner 与弱市场敏感，不能作为 universal entry，只能作条件性确认。
```

## 2. 非目标（Non-Goals）

本实验不得：

- 运行回测、模拟组合净值、计算策略收益曲线。
- 产出买入/卖出/仓位/止损/止盈/调仓规则。
- 训练任何预测模型。
- 把回溯局部低点或回溯最高点引入事件 t0、状态计算或标签计算。
- 把任何依赖未来固定窗口（+20/+60/+120 收益、未来高点）的确认变量当作 t0 领先特征。
- 把单日 EMA60 reclaim 直接升格为事件买点。
- 用样本外（validation / robustness）数据去选择、重定时、删改事件状态、阈值、窗口或壁垒参数。
- 使用非 PIT 行业标签产生主结论。
- 授权任何下游策略 / 组合 / 实盘阶段。下游授权由本实验最终决策单独给出。

## 3. 上游依赖与输入契约

主输入来自：

```text
01_data_prepare_pit_largecap_akshare_qlib_v0   -> PIT 可执行股票池、个股日线、基准日线、交易日历
02_big_winner_reverse_lifecycle_profile_v0     -> 冻结的 episode 参考集、匹配对照面板、序列定义、anchor 面板
topics/02_AFML_BIG_WINNER/data/                -> 复权 OHLCV、money、turnover
```

必需输入：

```text
PIT 可执行股票池：
  pit_largecap_main_chinext，按 usable_trade_date 主键，point-in-time

个股日线：
  qfq OHLCV、money、turnover
  raw OHLC 仅用于 VWAP 复权基准与可执行性审计

基准指数日线：
  csi300、chinext_index、all_a

交易日历：
  A 股交易日序列

上游画像产物（只读，不得在本实验改写）：
  big_winner_episode_reference_summary.csv
  shared_axis_sequence_dominance.csv
  matched_control_panel（local_cache / large_raw）
  anchor_aligned_daily_panel
  run_manifest.json（用于记录上游 git revision 与 hash）
```

实现必须把所有输入路径、上游 manifest hash、上游 git revision、本实验 git revision
记录进 `outputs/manifests/run_manifest.json`。如果上游 manifest 的最终决策不是
`reverse_lifecycle_sequence_supported_universal_dominance`，本实验必须 fail closed，
不得自行降级运行。

上游 `matched_control_panel` 与 `anchor_aligned_daily_panel` 可能位于 02 的
`outputs/local_cache/` 或 `outputs/large_raw/`，不一定随 publishable bundle 入库。若这些
本地可重生成产物缺失，03 只能用同一上游 git revision 与同一 manifest hash 重新生成只读输入，
或 fail closed；不得仅凭 02 的 publishable 汇总表伪造逐日面板、匹配对照行或事件级路径。

### 3.1 行业数据状态

沿用 02 的行业数据契约。运行必须设置：

```text
industry_data_status in {
  pit_available,
  best_effort_non_pit,
  unavailable
}
```

规则：

- `pit_available`：相对强度状态可拆分为 stock-vs-industry 与 industry-vs-market，行业条件可作为主诊断。
- `best_effort_non_pit`：行业相关项仅作 diagnostic-only，并带显式 as-of caveat，不进入主事件统计。
- `unavailable`：rank persistence 仅用 stock-vs-market 口径，行业拆分跳过，报告必须显式说明
  “当前 rank persistence 无法排除行业 beta”。

当前 v0 数据层预期为 `unavailable`。这意味着主事件 S3 的 rank persistence 仍以
`stock_vs_market_20d` 为基准，本实验必须把“行业 beta 未剔除”列为已知限制，不得隐瞒。

## 4. 日期范围与切分

复用 02 的冻结切分，但切分键改为**事件 t0 日期**（`event_t0_date`），不是 episode 低点。

```text
train:
  2017-01-03 <= event_t0_date <= 2021-12-31

validation:
  2022-01-01 <= event_t0_date <= 2023-12-31

robustness:
  2024-01-01 <= event_t0_date <= latest_label_complete_t0_date
```

其中：

```text
latest_label_complete_t0_date =
  最后一个交易日 D，使得 D 之后存在足够前向交易日完成最长壁垒窗口（见第 8 节）的标签观测
```

`latest_label_complete_t0_date` 只保证三重壁垒标签窗口完整。第 8 节的补充连续读数
`forward_return_60d` / 60d MFE / 60d MAE 使用独立 horizon 完整性标记；近端 t0 若满足 20 日壁垒完整
但不满足 60 日连续读数完整，必须把 60d 读数标记为 `censored_incomplete_horizon`，不得静默截断。

约束：

- 2022-2023 validation 是固定负 beta 压力窗，必须单独读，不得当作普通中性验证窗。
- 不得为满足样本门移动切分边界、缩短壁垒窗口、降低事件阈值或纳入标签不完整的 t0。
- 所有事件状态、阈值、窗口、壁垒参数、seed / reclaim / event 密度参数必须仅用 train 证据一次性冻结。
  validation 与 robustness 只用于样本外读数，不得用于结构选择。
- E_S3 事件按 `event_t0_date` 分配 split；baseline 事件按各自 `baseline_t0_date` 分配 split。
  event 与 baseline 的 split 不得用对方 t0 或 anchor date 代替。

报告必须分别给出：

```text
unconditional_oos_readout            -> 验证 + robustness 无条件事件前向读数
regime_conditioned_oos_readout       -> 按 market_regime_bucket 拆分的事件前向读数
event_density_audit                  -> 每年 / 每股 seed、reclaim、event 三层密度审计
```

## 5. 事件定义（核心）

### 5.1 设计原则

所有事件必须满足以下硬约束，否则不得进入 publishable 事件统计：

```text
close_observed:     所有状态只用截至状态日收盘可得的信息计算
no_retrospective:   不依赖回溯局部低点、不依赖任何未来高点 / 未来固定窗口收益
next_open_executable: 事件 t0 当日收盘确认，交易时间为 t0 次一可成交开盘
seed_day_controlled: 同一标的近邻 seed、reclaim、t0 必须按密度规则去重，避免单股灌水
regime_named:        不支持的 regime 必须显式命名，不得静默丢弃
```

事件由“对齐锚点 + 有序 close-observed 状态序列的完成日”构成。完成日即 `event_t0_date`，
是序列中最后一个状态被确认的收盘日。

### 5.2 对齐锚点：first_ema60_reclaim

EMA60 reclaim 是 v0 唯一冻结的可观测对齐锚点（与 02 一致），但**它本身不是事件触发器**，
只是序列的起点坐标。

```text
ema60[D] = rolling_mean(qfq_close, 60)[D]，仅用截至 D 收盘的 close
first_ema60_reclaim = anchor_search_start 之后首个 D，满足：
  qfq_close[D-1] < ema60[D-1]
  qfq_close[D]   >= ema60[D]
```

事件版搜索边界（必须完全 close-observed，不依赖 episode 高点）：

```text
anchor_search_start = candidate_seed_low_date
anchor_search_end   = candidate_seed_low_date + 120 交易日
```

其中 `candidate_seed_low_date` 是 close-observed 的回看锚点，**不是回溯局部低点**：

```text
candidate_seed_low_date = D，满足：
  qfq_low[D] 是 [D - 60 交易日, D] 区间内的最低 qfq_low（仅回看，不看未来）
  D 至少有 250 个历史交易日用于特征
```

注意：与 02 的 episode 低点（前后各 20 日窗口、含未来）不同，本实验的 seed low 只用回看窗口，
因此在 t0 当日完全可观测。seed low 只用于框定 reclaim 搜索起点，绝不进入交易或标签价格基准。

若搜索边界内无 `first_ema60_reclaim`，该 seed 不产生事件，标记 `missing_event_absent`，不得插补。

### 5.3 主事件 E_S3：修复后相对强度跳升并持续

E_S3 是本合约的主事件，由 S3 序列改写为 close-observed 完成日。

序列状态（全部以 reclaim 为对齐轴，relative_day 从 reclaim 日起算）：

```text
state_0  ema60_reclaim                                  at r0
state_1  rank_jump:        stock_vs_market_20d[r] >= 0.05         在 [r0, r0 + rank_jump_window] 内首次成立，记为 rj 日
state_2  rank_persistence: 自 rj 起，stock_vs_market_20d 在 persistence_window 个交易日内
                            保持 >= persistence_floor 的覆盖比例 >= persistence_coverage
```

事件 t0：

```text
event_t0_date = rank_persistence 被确认的收盘日
              = rj + persistence_window（持续性窗口结束、且覆盖条件成立的当日收盘）
```

v0 使用以下固定参数，视为 train-only 冻结常数。实现不得重新校准、不得用 validation /
robustness 调参；若未来版本要改阈值，必须新建实验版本并产出独立 calibration audit。

```text
rank_jump_threshold      = 0.05      # stock_vs_market_20d 跳升阈值
rank_jump_window         = 20        # reclaim 后允许出现 rank jump 的交易日窗口
persistence_window       = 20        # rank jump 后的持续观察窗
persistence_floor        = 0.00      # 持续期内相对强度下限
persistence_coverage     = 0.70      # 持续期内满足下限的交易日覆盖比例
```

E_S3 必须满足 5.1 全部硬约束。`stock_vs_market_20d` 必须用 5.4 规定的 close-observed 基准口径。

### 5.4 相对强度口径

```text
stock_return_20d  = qfq_close[r] / qfq_close[r-20] - 1
market_return_20d = benchmark_close[r] / benchmark_close[r-20] - 1
stock_vs_market_20d = stock_return_20d - market_return_20d
```

基准对齐（与 02 一致）：

```text
主板个股行     -> csi300
创业板个股行   -> chinext_index
跨市场汇总行   -> all_a
```

若 `industry_data_status = pit_available`，必须额外计算 `stock_vs_industry_20d`，
并产出 E_S3 在“个股 alpha 口径”与“stock-vs-market 口径”下的双读数，用于回答行业 beta 拆分问题。

### 5.5 弱过滤门 G_S2：修复后金额/VWAP 承接

S2 在画像中是稳定但弱的“修复质量过滤”，本合约把它作为 E_S3 的**可选弱过滤门**，不是独立事件。

```text
G_S2 在 event_t0_date 当日及 reclaim 至 t0 区间内要求：
  amount_ratio_20d >= 1.5  至少出现一次
  且 t0 当日满足 vwap_hold 或 range_hold：
    vwap_hold:  qfq_close[t0] >= qfq_daily_vwap[t0]
    range_hold: close_position_in_range[t0] >= 0.5
```

G_S2 默认作为标注列输出（`g_s2_passed`），不强制裁剪事件集。报告必须分别给出
“E_S3 全集”与“E_S3 ∩ G_S2”两套前向读数，由证据决定 G_S2 是否提升 edge。

### 5.6 条件性确认 C_S6：+20% 后排名/资金持续

S6 在画像中被降级（near-winner lift 仅 1.34、validation near-winner 仅 1.01、弱市场敏感）。
本合约把 S6 改写为**条件性确认列**，绝不作为独立 entry 事件。

S6 的 +20% 状态必须完全 close-observed，**不得**从回溯低点计量。冻结口径：

```text
plus20_base_price = qfq_close[first_ema60_reclaim]      # 以 reclaim 收盘价为 close-observed 基准
plus20_state_date = reclaim 之后首个 D，满足 qfq_close[D] / plus20_base_price - 1 >= 0.20
C_S6 confirm:
  自 plus20_state_date 起 continuation_window 内，
  rank 或 money 持续（stock_vs_market_20d >= 0 覆盖比例 >= 0.60
                      或 amount_ratio_20d >= 1.2 覆盖比例 >= 0.60）
```

v0 固定参数：

```text
plus20_threshold     = 0.20
continuation_window  = 20
```

C_S6 仅作为 E_S3 事件的附加标注列（`c_s6_confirmed` 与 `c_s6_confirm_date`）。报告必须显式说明
C_S6 天然滞后（需先观测到 +20% 路径），不适合作主信号，且在 near-winner / 弱市场不稳定。

口径漂移审计必须单独产出：02 的 S6 以 retrospective axis low 为 +20% 基准；03 为满足
close-observed 约束，改为 reclaim close 基准。该改写是新的可观测事件合同口径，不得在报告中声称
与 02 axis-low S6 完全等价。实现必须在 train split 上同时计算：

```text
s6_axis_low_reference_pass_rate        # 仅作 02 对照，不进入 03 事件
s6_reclaim_close_contract_pass_rate    # 03 合同口径
s6_basis_pass_rate_delta
s6_basis_confirm_delay_delta
```

并输出 `s6_basis_transform_audit.csv`，用于说明从画像口径到可观测口径的语义变化。

### 5.7 固定事件快照 schema

每个事件 t0 必须产出统一快照（沿用 02 snapshot 字段，全部 as-of t0 收盘）：

```text
instrument
event_id
event_type                  # E_S3
event_t0_date
trade_open_date             # t0 次一可成交开盘日
anchor_family               # first_ema60_reclaim
anchor_date
candidate_seed_low_date
rank_jump_date
rank_persistence_confirmed
g_s2_passed
c_s6_confirmed
c_s6_confirm_date
close_to_ema20
close_to_ema60
ema20_slope_20d
ema60_slope_20d
return_5d
return_20d
return_60d
amount_ratio_20d
amount_ratio_60d
turnover_ratio_20d
derived_daily_vwap_available
close_to_derived_daily_vwap
vwap_reclaim_flag
intraday_range_pct
close_position_in_range
upper_shadow_pct
gap_open_pct
gap_fade_flag
atr_20_pct
market_return_20d
market_drawdown_60d
market_volatility_20d
market_regime_bucket
benchmark_alias
stock_vs_market_20d
stock_vs_industry_20d        # 仅 pit_available
industry_vs_market_20d       # 仅 pit_available
split
seed_cluster_id
reclaim_cluster_id
event_cluster_id
density_stage
density_kept
false_repair_observed_asof_t0
false_repair_drawdown_trigger_date
false_repair_10d_diagnostic
false_repair_20d_diagnostic
insufficient_runup_20d_diagnostic
future_false_repair_any_diagnostic
event_invalidated_false_repair
```

VWAP 派生字段口径与 02 完全一致：

```text
raw_daily_vwap = money / volume
qfq_daily_vwap = raw_daily_vwap * qfq_adjustment_factor
qfq_adjustment_factor = qfq_close / raw_close
```

单位不兼容、money/volume 缺失或复权基准无法核验时，VWAP 字段标记
`missing_unit_incompatible` 或 `missing_source_field`，不得用 raw VWAP 与 qfq 价直接比较。

缺失值必须区分（不得合并）：

```text
missing_insufficient_lookback
missing_event_absent
missing_source_field
missing_unit_incompatible
missing_out_of_coverage
censored_incomplete_horizon
non_executable_next_open
cross_split_boundary_unusable
```

## 6. False-Repair 显式排除

画像阶段显示 EMA60 anchor control 中 74.4% 为 false repair（train 79.3% / validation 75.3%）。
因此**事件合约必须自带失败修复审计与排除分支**，否则会被大量假修复污染。

### 6.1 False-repair 标记

对每个候选 seed 的 reclaim，必须同时计算 as-of 排除标记与未来诊断标记。二者不得混用：

- `false_repair_observed_asof_t0`：只用截至 `event_t0_date` 收盘已经发生的信息，可用于排除 E_S3。
- `false_repair_10d_diagnostic` / `false_repair_20d_diagnostic` /
  `insufficient_runup_20d_diagnostic`：需要 reclaim 后完整 10/20 日路径或未来 runup，只能作为独立
  诊断列输出，不得聚合后替代 as-of 排除规则。
- `future_false_repair_any_diagnostic`：仅为上述三个未来诊断列的 OR 聚合，便于报告汇总；不得用于 t0 前
  事件选择。

候选路径需要逐日维护以下 close-observed 状态：

```text
false_repair_drawdown_trigger_date:
  reclaim 后首次 D，满足 qfq_close[D] / qfq_close[first_ema60_reclaim] - 1 <= false_repair_drawdown_floor

false_repair_10d_diagnostic:
  reclaim 后 10 个交易日窗口完整后，窗口内曾触发 false_repair_drawdown_trigger_date

false_repair_20d_diagnostic:
  reclaim 后 20 个交易日窗口完整后，窗口内曾触发 false_repair_drawdown_trigger_date

insufficient_runup_20d_diagnostic:
  reclaim 后 20 个交易日窗口完整后，max(qfq_high[reclaim, reclaim + 20]) / qfq_close[first_ema60_reclaim] - 1
  < insufficient_runup_floor

future_false_repair_any_diagnostic:
  false_repair_10d_diagnostic
  or false_repair_20d_diagnostic
  or insufficient_runup_20d_diagnostic
```

v0 固定参数：

```text
false_repair_drawdown_floor   = -0.10
insufficient_runup_floor      = 0.05
```

### 6.2 排除规则

E_S3 的状态序列天然要求 reclaim 后相对强度持续，已经在结构上排斥部分 false repair。
但合约必须额外保证：**E_S3 的 t0 不得落在 t0 当时已经触发的失败修复路径上**。

```text
false_repair_observed_asof_t0 =
  false_repair_drawdown_trigger_date is not null
  and false_repair_drawdown_trigger_date <= event_t0_date
```

若 `false_repair_observed_asof_t0 = true`，候选作废并标记 `event_invalidated_false_repair`。
`false_repair_10d_diagnostic`、`false_repair_20d_diagnostic` 与
`insufficient_runup_20d_diagnostic` 不得在其窗口完成前用于排除事件；若窗口尚未完成，只能标记
`missing_out_of_coverage` 或 `censored_incomplete_horizon`。

报告必须给出 `false_repair_exclusion_audit.csv`，统计被排除的候选数、排除前后事件数与年度分布。

## 7. Seed / Reclaim / Event 密度控制

为避免单一标的的震荡路径产生大量近邻 seed、reclaim 与 t0，虚高机会集、基线池和前向统计分母，
密度控制必须分三层执行，且每层都保留审计行。

### 7.1 Seed-level 去重

`candidate_seed_low_date` 是 60 日滚动新低，天然会在下跌或低位平台中连续触发。实现必须先对
同一 instrument 的 seed 做非链式直接区间去重：

```text
对同一 instrument 的 candidate_seed_low_date 升序：
  以首个 seed 为 seed_cluster 起点
  若后续 seed 落在 [seed, seed + seed_density_window] 内，则并入同一 seed_cluster
  每个 seed_cluster 仅保留 earliest seed 进入 reclaim 搜索
  非 canonical seed 保留在 candidate_seed_pool 审计中，不进入主机会集
```

### 7.2 Reclaim-level 去重

多个 canonical seed 可能找到相同或近邻的 `first_ema60_reclaim`。实现必须在进入 E_S3 / baseline
状态计算前，对同一 instrument 的 reclaim 做非链式直接区间去重：

```text
对同一 instrument 的 first_ema60_reclaim 升序：
  以首个 reclaim 为 reclaim_cluster 起点
  若后续 reclaim 落在 [reclaim, reclaim + reclaim_density_window] 内，则并入同一 reclaim_cluster
  每个 reclaim_cluster 仅保留 earliest reclaim 进入事件与基线候选池
```

### 7.3 Event-level 去重

通过 E_S3 的候选事件与 baseline 候选事件仍必须按各自 t0 做 per-instrument 非链式直接区间去重
（沿用 02 control 去重思想）：

```text
canonical_t0_date = event_t0_date      # E_S3
canonical_t0_date = baseline_t0_date   # baseline

对同一 instrument 的候选行，按 canonical_t0_date 升序：
  以首个 canonical_t0_date 为 event_cluster 起点
  若后续 canonical_t0_date 与 event_cluster 起点的 [t0, t0 + event_density_window] 区间直接重叠，则并入同一 event_cluster
  每个 event_cluster 仅保留 earliest canonical_t0_date 作为 canonical 行（density_kept = true）
  非 canonical 候选行保留在 cluster 审计中（density_kept = false），不进入主前向统计
```

v0 固定参数：

```text
seed_density_window    = 20
reclaim_density_window = 20
event_density_window   = 20
```

被任一密度规则折叠的 seed / reclaim / event 不得进入 publishable 主前向 edge 统计的分子或分母，
但必须在 `event_density_audit.csv` 中按 stage 可见，使机会集、事件集和基线池计数可解释。

## 8. 标签契约（事件前向评估）

本实验不是回测，但需要用 AFML 三重壁垒标签客观评估事件是否具备前向区分度。标签**只用于事件评估**，
不构成交易规则。

### 8.1 执行口径

```text
t0          = event_t0_date（收盘确认）
trade_time  = next_executable_open_after_t0（次一可成交开盘）
price_basis = qfq
执行价      = trade_open_date 的 qfq_open
不可执行（停牌/无开盘/一字板无法成交）的事件按 censoring 规则处理，不得静默丢弃
```

日频 OHLCV 不能真实观测开盘排队成交，只能做保守 proxy。实现必须 fail closed 使用以下规则：

```text
missing_open_or_volume:
  qfq_open 缺失、volume <= 0、money <= 0 或交易日缺失 -> non_executable_next_open

one_price_limit_open_proxy:
  qfq_open == qfq_high == qfq_low == qfq_close
  且 abs(raw_open / previous_raw_close - 1) 接近当日涨跌停阈值
  -> non_executable_next_open

limit_threshold_status:
  若无法从证券板块 / ST 状态确定 10% / 20% / 5% 等涨跌停阈值，则标记
  limit_rule_unavailable，并把该 trade_open 视为 non_executable_next_open
```

`executability_audit.csv` 必须按 split / year / board_proxy 汇总 `non_executable_next_open`、
`limit_rule_unavailable` 与标签可用率。

### 8.2 壁垒标签（train-only 冻结阈值）

采用两组固定壁垒，均以执行价为基准：

```text
confirm_20:
  horizon_days     = 20
  upper_barrier    = +0.12
  lower_barrier    = -0.08
  touch_priority   = lower_barrier_first
  label            = +1 触上界 / -1 触下界 / 0 到期未触

failure_10:
  horizon_days     = 10
  lower_barrier    = -0.10
  upper_barrier    = none
  label            = 1 触发失败 / 0 未触发
```

补充连续读数（不替代壁垒标签）：

```text
forward_return_10d / forward_return_20d / forward_return_60d   # 自执行价起的 qfq 前向收益
mfe_10d / mae_10d
mfe_20d / mae_20d
mfe_60d / mae_60d
horizon_complete_10d / horizon_complete_20d / horizon_complete_60d
```

20 日壁垒完整不代表 60 日连续读数完整。`forward_return_60d`、`mfe_60d`、`mae_60d`
必须单独检查 `horizon_complete_60d`；若不完整，相关 60d 字段标记 `censored_incomplete_horizon`，
不得用截断窗口填值，也不得进入 60d 均值 / 中位数 / 分位数统计。

### 8.3 Censoring

```text
horizon 未完成（数据右截断）         -> 标记 censored_incomplete_horizon，不计入主 win/loss 统计
trade_open 不可执行（停牌/一字）     -> 标记 non_executable_next_open，单独审计，不计入主统计
```

主 win/loss 统计只依赖 `confirm_20` 与 `failure_10` 的 horizon 完整性。60d 连续读数的 censoring
只影响 60d 描述统计，不得反向剔除已完成壁垒标签的事件。

所有壁垒阈值、horizon 仅用 train 冻结。validation / robustness 不得调阈值。

## 9. 匹配基线与对照

事件 edge 必须是**事件 vs 匹配基线事件**的相对结论，不得用事件单边胜率宣称 edge。

### 9.1 基线事件集

基线来自同一机会集，但**未通过 E_S3 完整序列**的可观测 reclaim 事件：

```text
baseline_reclaim_event:
  同样满足 candidate_seed_low_date 资格
  同样出现 first_ema60_reclaim
  但未满足 rank_jump 或 rank_persistence（即仅站回均线，未形成持续相对强度）
```

基线事件的主 t0 必须是 close-observed 的失败判定日，不得用 winner / E_S3 平均完成 offset
制造合成 entry time。主口径：

```text
baseline_t0_policy = observed_failure_decision_date

rank_jump_failed:
  到 r0 + rank_jump_window 收盘仍从未满足 stock_vs_market_20d >= rank_jump_threshold
  -> baseline_t0_date = r0 + rank_jump_window

rank_persistence_failed:
  曾满足 rank_jump，但到 rj + persistence_window 收盘时 persistence coverage 不达标
  -> baseline_t0_date = rj + persistence_window
```

为审计 timing 敏感性，必须额外输出一个 deterministic-offset baseline 诊断口径：

```text
baseline_t0_policy = deterministic_max_horizon
baseline_t0_date   = r0 + rank_jump_window + persistence_window
```

该诊断口径只进入 `baseline_t0_timing_audit.csv`，不得替代主 baseline。基线必须经过相同的
seed / reclaim / event 密度控制与 false-repair 标记。

为分离“剔除假修复”与“rank persistence 独立加值”两种效应，baseline 必须产出两个主变体：

```text
false_repair_observed_asof_baseline_t0 =
  false_repair_drawdown_trigger_date is not null
  and false_repair_drawdown_trigger_date <= baseline_t0_date

baseline_raw:
  baseline_t0_policy = observed_failure_decision_date
  保留 false_repair_observed_asof_baseline_t0 = true 的基线行
  用于回答：E_S3 合约整体相对原始 EMA60 reclaim 失败机会集是否有 edge

baseline_false_repair_excluded:
  baseline_t0_policy = observed_failure_decision_date
  同样排除 false_repair_observed_asof_baseline_t0 = true 的基线行
  不要求 rank_jump / rank_persistence 通过
  用于回答：在同样剔除 as-of false-repair 后，rank persistence 是否仍有独立前向加值
```

headline edge 必须同时报告：

```text
E_S3 vs baseline_raw
E_S3 vs baseline_false_repair_excluded
```

若只相对 `baseline_raw` 有 edge、但相对 `baseline_false_repair_excluded` 无 edge，报告必须把结论降级为
`event_contract_false_repair_filter_dominant_no_rank_persistence_separation`，不得宣称 rank persistence 独立有效。

### 9.2 匹配字段

```text
same anchor family (first_ema60_reclaim)
same anchor date or nearest available same-week anchor date
same market_regime_bucket
similar market cap bucket
similar liquidity bucket
similar prior 20d / 60d return bucket
similar prior drawdown bucket
similar volatility bucket
same industry, if PIT industry data is available
```

最近同周匹配若跨切分边界，必须丢弃或标记 `cross_split_boundary_unusable`，
不得让 validation / robustness 的基线行通过最近周匹配进入 train 统计。

### 9.3 Near-winner 对照

沿用 02 near-winner 定义（同 120 日窗 forward MFE 落在 30%-50%，从不触及 50%），
用于回答“E_S3 在后验相近强势路径中是否仍有区分度”。该定义显式使用未来 outcome，
因此只能作为 `profile_only_future_outcome_control`：

```text
near_winner_profile_anchor_date:
  E_S3 行使用 event_t0_date
  baseline/profile control 行使用各自 baseline_t0_date

near_winner_profile_start_price:
  near_winner_profile_anchor_date 之后 next_executable_open 的 qfq_open

near_winner_forward_mfe_120d:
  max(qfq_high[trade_open_date, trade_open_date + 120]) / near_winner_profile_start_price - 1

near_winner_flag:
  0.30 <= near_winner_forward_mfe_120d < 0.50
  且同一 120 日窗口内从不触及 0.50
```

不得用 `candidate_seed_low_date`、02 retrospective episode low 或 `first_ema60_reclaim` 作为 03
near-winner 主锚点。若报告需要展示 02-aligned near-winner 参考读数，必须另列为 diagnostic-only，
并明确其窗口锚点不同。

```text
future_label_used_for_profile_only = true
near_winner_rows_excluded_from_contract_selection = true
near_winner_rows_excluded_from_acceptance_gates = true
```

near-winner 不得参与事件阈值选择、baseline 匹配、主 OOS edge gate 或最终授权决策。
报告必须单独产出 E_S3 在 near-winner 子集上的前向读数与壁垒标签率，并明确这是后验诊断，
不是可执行事件宇宙的一部分。

## 10. Market Regime 条件

market regime 口径与 02 完全一致，as-of t0 由基准收盘计算：

```text
market_trend_60d     = all_a_close / rolling_mean(all_a_close, 60) - 1
market_drawdown_120d = all_a_close / rolling_max(all_a_close, 120) - 1
market_drawdown_60d  = all_a_close / rolling_max(all_a_close, 60) - 1
market_volatility_20d = std(daily_return(all_a_close), 20)

risk_on:     market_trend_60d >= 0  且 market_drawdown_120d > -0.10
risk_off:    market_trend_60d < 0   且 market_drawdown_120d <= -0.10
transition:  其余完整观测
```

`market_drawdown_60d` 与 `market_volatility_20d` 只作为 snapshot / matching covariates，
不改变 regime bucket 定义。若 02 已有同名字段，实现必须沿用 02 公式并在
`event_contract_definition.csv` 中记录来源。

2022-2023 仍是固定负 beta 验证切分，即使个别 t0 日按规则落入 transition / risk_on。
不支持的 regime 必须显式命名，不得静默剔除。

## 11. 必需输出

Publishable：

```text
outputs/publishable/tables/event_contract_definition.csv
outputs/publishable/tables/event_instances.csv
outputs/publishable/tables/event_label_outcomes.csv
outputs/publishable/tables/event_vs_baseline_forward_stats.csv
outputs/publishable/tables/event_vs_near_winner_forward_stats.csv
outputs/publishable/tables/baseline_t0_timing_audit.csv
outputs/publishable/tables/baseline_false_repair_attribution_audit.csv
outputs/publishable/tables/false_repair_exclusion_audit.csv
outputs/publishable/tables/event_density_audit.csv
outputs/publishable/tables/threshold_freeze_audit.csv
outputs/publishable/tables/s6_basis_transform_audit.csv
outputs/publishable/tables/data_source_coverage_audit.csv
outputs/publishable/tables/oos_readout_unconditional.csv
outputs/publishable/tables/oos_readout_regime_conditioned.csv
outputs/publishable/tables/executability_audit.csv
outputs/publishable/reports/observable_anchor_event_contract_report.md
outputs/manifests/run_manifest.json
```

`event_contract_definition.csv` 必须冻结并记录：

```text
event_type
anchor_family
shared_axis
required_states
forbidden_states
order_constraints
state_thresholds
lookback_windows
seed_density_window
reclaim_density_window
event_density_window
false_repair_rules
t0_definition
trade_time_definition
label_contract
threshold_freeze_basis = train_only
```

`event_vs_baseline_forward_stats.csv` 必须包含：

```text
event_type
baseline_family              # baseline_raw / baseline_false_repair_excluded
baseline_t0_policy
false_repair_policy
split
regime_bucket
event_count
baseline_count
baseline_match_coverage
event_confirm20_pos_rate
baseline_confirm20_pos_rate
confirm20_rate_lift
event_failure10_rate
baseline_failure10_rate
failure10_rate_diff
event_forward_return_20d_mean / median
baseline_forward_return_20d_mean / median
forward_return_20d_diff
event_payoff_ratio
censored_count
non_executable_next_open_count
executable_rate_denominator_count
executable_rate_numerator_count
train_lift
validation_lift
robustness_lift
split_stability
claim_status
```

`event_label_outcomes.csv` 必须包含每个 horizon 的完整性状态：

```text
event_id
event_type
split
trade_open_date
confirm_20_label
failure_10_label
forward_return_10d
forward_return_20d
forward_return_60d
mfe_10d / mae_10d
mfe_20d / mae_20d
mfe_60d / mae_60d
horizon_complete_10d
horizon_complete_20d
horizon_complete_60d
forward_return_60d_status
```

`forward_return_60d_status = censored_incomplete_horizon` 的行不得进入任何 60d 描述统计。

`baseline_t0_timing_audit.csv` 必须包含：

```text
split
regime_bucket
baseline_family
baseline_t0_policy
baseline_count
median_reclaim_to_baseline_t0_days
median_reclaim_to_event_t0_days
confirm20_rate
failure10_rate
forward_return_20d_mean
policy_used_for_main_claim
```

`baseline_false_repair_attribution_audit.csv` 必须包含：

```text
split
regime_bucket
baseline_family
event_count
baseline_count
baseline_false_repair_asof_count
event_vs_baseline_confirm20_lift
event_vs_baseline_failure10_diff
event_vs_baseline_forward_return_20d_diff
rank_persistence_independent_edge_status
```

`threshold_freeze_audit.csv` 必须包含全部冻结常数、来源说明、是否参与校准、以及
`oos_used_for_selection = false`。v0 所有阈值应记录为 fixed_contract_constant。

大文件 / 可重生成：

```text
outputs/local_cache/candidate_seed_pool.parquet
outputs/local_cache/event_aligned_panel.parquet
outputs/large_raw/baseline_event_pool.parquet
```

若 `industry_data_status != pit_available`：

```text
不产出 stock-vs-industry 双读数列
不在前向统计中加入行业相对状态
报告显式声明 rank persistence 未剔除行业 beta
```

## 12. 验收门与最终决策

样本门：

```text
min_total_event_count            = 120
min_validation_event_count       = 30
min_robustness_event_count       = 30
min_baseline_match_coverage      = 0.80
min_validation_baseline_match_coverage = 0.70
min_robustness_baseline_match_coverage = 0.70
min_event_label_complete_rate    = 0.70    # 非 censored / 可执行事件占比
min_executable_rate              = 0.80    # trade_open 可成交占比
```

`min_total_event_count`、`min_validation_event_count`、`min_robustness_event_count` 的分母只能使用
`density_kept = true` 且未被 `event_invalidated_false_repair` 排除、且具备主标签可执行性的 canonical E_S3
事件。折叠前 seed / reclaim / event 候选数、被 false-repair 排除数、non-executable 行均不得用于凑样本门。

`min_executable_rate` 必须使用执行性过滤前的 canonical E_S3 事件集计算，避免与样本门分母循环：

```text
executable_rate_denominator =
  density_kept = true
  and event_invalidated_false_repair = false
  and confirm_20 / failure_10 label horizon would be complete if trade_open executable

executable_rate_numerator =
  executable_rate_denominator
  and non_executable_next_open = false
```

`min_event_label_complete_rate` 则在可执行事件中计算主标签 horizon 完整率；不得用已经剔除
non-executable 的集合反推 `min_executable_rate`。

任一 regime-conditioned headline claim 也必须给出该 regime 内的 baseline match coverage；
coverage 未达 0.70 的 regime 只能标记为 `sample_blocked`，不得作为支持性结论。

baseline match coverage 必须按 `baseline_family` 分别计算与 gate：

```text
baseline_match_coverage[baseline_raw]
baseline_match_coverage[baseline_false_repair_excluded]
validation_baseline_match_coverage[baseline_family]
robustness_baseline_match_coverage[baseline_family]
```

headline 主判定使用 `baseline_false_repair_excluded`，因此其 total / validation / robustness coverage
必须分别满足上述 0.80 / 0.70 / 0.70 门槛；不得用 `baseline_raw` 的高覆盖率替代。

Edge 门（事件 vs 匹配基线，train-only 冻结，OOS 只读）：

```text
confirm20_rate_lift            >= 1.25  或 confirm20 绝对差 >= 5pct
failure10_rate_diff            <= 0      # 事件失败率不得高于基线
forward_return_20d_diff        > 0
```

universal / regime-conditional headline edge 的主判定必须基于
`E_S3 vs baseline_false_repair_excluded`。`E_S3 vs baseline_raw` 只能说明完整合约相对原始 reclaim
失败机会集的总体改善，不能单独证明 rank persistence 独立有效。

唯一预注册 headline 检验为：

```text
event_set        = E_S3 全集（不强制 G_S2）
baseline_family  = baseline_false_repair_excluded
label            = confirm_20
split_readout     = train / validation / robustness 三段同向，2022-2023 validation 单独通过方向检查
regime_scope      = unconditional universal headline
```

其他组合，包括 `baseline_raw`、`failure_10`、regime-conditioned、`E_S3 ∩ G_S2`、near-winner、
C_S6、60d 连续读数，均为 secondary / diagnostic readout。报告不得在 headline 失败后改挑其他维度
声明 universal 支持；多重检验计数必须把这些 secondary / diagnostic 读数纳入 family 记录。

near-winner separation 只作为 `profile_only_future_outcome_control` 诊断读数，不进入 hard gate。

稳定性门：

```text
validation 与 robustness 同号
headline edge 在 train / validation / robustness 三段均有非零支持
2022-2023 负 beta 验证窗未否定方向
单一年份或单一标的不解释多数 edge
```

允许的最终决策：

```text
event_contract_supported_universal_edge
event_contract_regime_conditional_candidate
event_contract_negative_beta_not_supported
event_contract_validation_sample_blocked
event_contract_sample_blocked
event_contract_executability_blocked
event_contract_no_baseline_separation
event_contract_false_repair_filter_dominant_no_rank_persistence_separation
```

规则：

- `event_contract_supported_universal_edge` 故意难达成。regime-conditional、负 beta 不支持、
  样本受限均为合法结果，不是实现失败。
- 若事件相对基线无前向区分，使用 `event_contract_no_baseline_separation`。
- 若事件只相对 `baseline_raw` 有 edge、但相对 `baseline_false_repair_excluded` 无 edge，使用
  `event_contract_false_repair_filter_dominant_no_rank_persistence_separation`。
- 若可执行率或标签完成率不达标，使用 `event_contract_executability_blocked`，不得放宽执行口径凑数。
- universal headline edge 必须通过 2022-2023 负 beta 验证切分；在该窗 unsupported 或 sample-blocked 的，
  只能报 `regime_conditional_candidate` 或对应 blocked 状态。

下游授权（是否进入策略 / 组合 / 回测阶段）由本实验最终决策单独给出，且仅当达成
`event_contract_supported_universal_edge` 或显式 `regime_conditional_candidate` 时才授权下一阶段，
否则不授权。

## 13. 报告要求

最终报告必须包含：

- 输入路径、上游 manifest hash、上游与本实验 git revision。
- 上游 local_cache / large_raw 输入可用性与 data source coverage audit。
- 行业数据状态与 caveat（含 rank persistence 行业 beta 未剔除声明，若适用）。
- 冻结的事件合约定义（状态、阈值、窗口、t0、trade_time、标签契约）。
- 阈值冻结审计，明确 v0 是否 fixed_contract_constant、是否使用 OOS 选择。
- 事件数按 split / 年 / regime 分布。
- seed / reclaim / event 三层密度审计（折叠前后事件数）。
- false-repair 排除审计（as-of 排除数、未来诊断数与年度分布）。
- 可执行性审计（non_executable_next_open 数、censored 数、可执行率）。
- baseline t0 timing audit（主 observed-failure 口径与 deterministic-offset 诊断口径差异）。
- baseline false-repair attribution audit（`baseline_raw` 与 `baseline_false_repair_excluded` 的 edge 分解）。
- baseline family 分别计算的 match coverage gate，特别是 headline 使用的
  `baseline_false_repair_excluded` coverage。
- executable rate 的执行性过滤前分母、可执行分子，以及与 label complete rate 的分母差异。
- 事件 vs 匹配基线前向统计（confirm20 lift、failure10 diff、forward return diff、payoff）。
- 事件 vs near-winner 前向统计，并明确其使用未来 outcome、仅为 profile-only 诊断。
- E_S3 全集 与 E_S3 ∩ G_S2 双读数（G_S2 是否提升 edge）。
- C_S6 条件性确认读数、S6 basis transform audit，并明确其滞后性、口径转换与弱市场不稳定性。
- 无条件 OOS 读数 与 regime-conditioned OOS 读数。
- 60d 连续读数的 horizon completeness 与 censoring 状态，明确其不影响 20d/10d 主壁垒标签完整性。
- 多重检验计数（事件 family x split x regime x label）。
- 唯一预注册 headline 检验组合，以及 secondary / diagnostic readout 列表。
- 最终决策 replay。

报告不得把单边事件胜率当作 edge，不得把 winner-only 描述当作 control-adjusted 结论，
不得把回溯低点 / 未来确认变量呈现为 t0 可用信息。

## 14. 测试与验证

聚焦测试必须覆盖：

- `candidate_seed_low_date` 仅回看窗口、在 t0 完全可观测（合成路径）。
- `first_ema60_reclaim` 的 as-of 计算与 close-observed 控制版搜索边界。
- E_S3 状态序列（reclaim -> rank jump -> rank persistence）只用截至状态日信息计算。
- rank persistence 覆盖比例与窗口约束在合成路径上的正确性。
- event_t0 与 trade_open（次一可成交开盘）执行口径，含停牌 / 一字板不可执行处理。
- 日频 one-price limit proxy 与 limit_rule_unavailable fail-closed 行为。
- false-repair as-of 标记、未来诊断标记与 `event_invalidated_false_repair` 排除逻辑。
- `baseline_raw` 保留 as-of false-repair、`baseline_false_repair_excluded` 同步排除 as-of false-repair 的归因分解。
- baseline match coverage 按 `baseline_family` 分别 gate，不得用 raw 覆盖率替代 excluded 覆盖率。
- `min_executable_rate` 使用执行性过滤前 canonical 事件分母，`min_event_label_complete_rate` 使用可执行事件分母。
- 唯一预注册 headline 检验为 E_S3 全集 vs baseline_false_repair_excluded 的 confirm_20 universal readout。
- seed / reclaim / event 三层非链式区间去重，含 A-B-C 重叠行为。
- 三重壁垒标签 touch_priority（lower_barrier_first）与 censoring，含 60d 连续读数独立 censoring。
- 匹配基线 observed-failure 主 t0、deterministic-offset 诊断 t0，以及最近同周匹配拒绝 / 标记跨切分边界。
- E_S3 切分按 `event_t0_date` 分配，baseline 切分按 `baseline_t0_date` 分配。
- near-winner 对照标记为 profile-only，不参与事件选择、baseline 匹配或 hard gate。
- near-winner 120 日 forward MFE 从 profile t0 的 next executable open 起算，不使用 seed low / reclaim / 02 episode low。
- C_S6 的 +20% 基准为 reclaim 收盘价、绝不使用回溯低点。
- S6 axis-low 参考口径与 reclaim-close 合同口径的 transform audit。
- `market_drawdown_60d` 与 `market_volatility_20d` 按第 10 节公式生成，且不改变 regime bucket。
- 行业不可用时的条件产物行为（跳过行业拆分、保留声明）。
- VWAP qfq 复权基准核验与单位不兼容时的 missing 标记。

运行必须 fail closed：上游决策不符、必需输入缺失、源单位不兼容、可执行性无法评估、
或验收门无法计算时，不得降级产出 publishable 结论。

## 15. 与上游画像的一致性约束

- 事件不得引入 02 已判定为“确认而非领先”的固定未来窗口变量（return_60d、ema60_slope@+60、
  atr@+120 等）作为 t0 触发条件。它们只能作为事件后的描述性读数。
- S3 为主、S6 为条件、S2 为弱门的优先级由 02 证据冻结，本实验不得擅自把 S6 提升为主事件。
- 若本实验发现 E_S3 在样本外无法保持 edge，正确结论是相应 blocked / no-separation 决策，
  而不是回到画像阶段重挖单因子或放宽事件定义。
