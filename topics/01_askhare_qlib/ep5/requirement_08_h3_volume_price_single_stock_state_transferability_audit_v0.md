# EP5 Requirement 08: H3 量价单股状态可迁移性审计 V0

## 1. Requirement Metadata

requirement_id: `ep5_r08_h3_volume_price_single_stock_state_transferability_audit_v0`

short_name: `r08_single_stock_state_transferability_audit_v0`

status: `requirement-draft`

workflow: `EP5`

created_date: `2026-05-23`

primary_output_namespace: `ep5/outputs/r08_h3_volume_price_single_stock_state_transferability_audit_v0/`

upstream_requirement:

- `ep5/requirement_07_short_horizon_timing_failure_attribution_audit_v0.md`

upstream_report:

- `ep5/outputs/r07_short_horizon_timing_failure_attribution_audit_v0/reports/r07_final_report.md`

upstream_final_decision:

```text
r07_insufficient_state_cell_sample_blocked
```

R08 继承 EP5 的本地 PIT mcap500 mainboard universe、weekly close-observed signal、next-open execution、H3 label、110bps round-trip cost、split-purity 规则和 no-online-data 边界。

R08 不继承 R07 的研究对象。R07 仍然是在横截面 family score pocket 上做状态归因；R08 改成单只股票相对自身历史的价量状态诊断。

## 2. 上游动机

R07 的结论不是完全没有信息，而是短周期相对信息残留无法被证明为干净、稳定、可授权的横截面 edge。

R07 的关键事实：

```text
Q1 relative-pocket cell count = 14
Q2 unconditional clean cell count = 0
Q3 stable state cell count = 0
Q3 state sample blocked = 112 / 126
final_decision = r07_insufficient_state_cell_sample_blocked
```

R07 中最强的正例是 `volume_price_correlation` 的 H3 pocket：

```text
validation spread   = 0.333%
robustness spread   = 0.170%
validation RankIC   = 0.927%
robustness RankIC   = 1.751%
```

同时，R07 已经给出停止信号：

```text
H1/H3 pocket 存在；
但 monotonicity、persistent-clean、style-clean 不能通过；
状态切片后样本不足；
没有任何 Q3-stable clean cell；
没有授权 downstream requirement。
```

因此 R08 不继续问：

```text
全市场横截面 top score 股票能不能交易？
```

R08 改问：

```text
同一只股票相对自身历史的价量状态异常，
是否具有跨年份、跨股票可迁移的短周期收益含义？
```

这不是 R07 的参数修补，也不是 R06/R07 的策略续集。R08 是新的问题定义：从横截面选股因子转为 single-stock time-series state transferability audit。

## 3. Research Positioning

R08 是诊断 requirement。

R08 不是策略 requirement。

R08 不输出：

- production signal；
- long-only alpha pass；
- hedged alpha pass；
- top-N 或 top-fraction basket；
- 每只股票专属因子；
- 每只股票专属阈值；
- 每只股票专属 horizon；
- validation 选出来的 family、threshold 或有效股票；
- LGBM、neural network、optimizer、right-tail 或 big-winner rescue。

R08 输出：

- H3 量价/VWAP family 的单股内状态分数；
- 单股内状态与 H3 self-relative return 的关系；
- 时间迁移结果；
- 股票迁移结果；
- concentration、monotonicity、industry / beta / liquidity attribution；
- 一个 final decision enum；
- 是否允许写 R09 narrow strategy requirement。

R08 即使支持可迁移状态信息，也不等于策略 pass。唯一可能授权的是后续 R09 的窄策略 requirement。

### 3.1 与 R06/R07 的区别

| 项目 | R06/R07 | R08 |
|:--|:--|:--|
| 研究对象 | 横截面 family / horizon / state pocket | 单只股票自身历史状态 |
| 分数含义 | 股票之间谁更高 | 这只股票相对自己历史是否异常 |
| 主要风险 | persistent-name / style exposure | 个股过拟合 / 不可迁移 |
| primary horizon | H1/H3/H5/H10 audit | 固定 H3 |
| family scope | Alpha191 primary families | 只看 3 个量价/VWAP family |
| 输出 | information residue / no downstream authorization | transferability support / no support |
| 是否策略 | 否 | 仍然否 |

## 4. Core Question

R08 只回答一个问题：

```text
在当前 PIT universe、weekly close-observed signal、
next-open execution、H3 horizon、110bps cost 的边界下，

H3 量价 / VWAP family 的单股内标准化状态，
是否存在跨年份、跨股票可迁移的短周期状态-收益关系？
```

关键词：

```text
single-stock time-series state
within-stock normalization
transferability
not cross-sectional stock selection
not stock-specific optimization
```

R08 的 primary evidence 是状态与收益的关系，不是 top20% strategy return。

## 5. Non-Goals and Explicit Prohibitions

R08 必须禁止：

1. 构造交易策略。
2. 输出 long-only alpha pass。
3. 输出 hedged alpha pass。
4. 输出 production signal。
5. 使用横截面 rank 作为 primary score。
6. 使用 top-N、top20%、top-decile 或任意横截面选股 basket 作为决策对象。
7. 给每只股票单独调因子。
8. 给每只股票单独调阈值。
9. 给每只股票单独调 horizon。
10. 根据 validation 选择有效股票。
11. 根据 validation 选择 family。
12. 根据 validation 选择状态阈值。
13. 根据 validation 改 factor direction。
14. 根据 validation 改 label 定义。
15. 引入 R08 scope 外的新 Alpha191 family。
16. 引入 H1、H5、H10、H20 或任意非 H3 primary horizon。
17. 引入 LGBM、neural network、linear optimizer、PCA、autoencoder 或组合优化器。
18. 使用 right-tail、big-winner、hit-rate 或单笔极端收益救回结论。
19. 使用 online data。
20. 触发回测、paper trading 或 production pipeline。

一句话：

```text
R08 不是找哪只股票能赚钱，
而是检验单股内价量状态是否有跨股票可迁移规律。
```

## 6. Data, Split, and Execution Contract

R08 继承本地 EP5 数据输入：

- local PIT Qlib provider；
- PIT mcap500 mainboard universe；
- PIT industry membership；
- trading calendar；
- `SH000300` index data；
- R06/R07 已冻结的 GTJA191 included factor registry 和 family map；
- no-online-data execution boundary。

时间 split 固定：

```text
train:
  2017-07-04 through 2021-12-31

validation:
  2022-01-01 through 2023-12-31

robustness:
  2024-01-01 through 2025-12-31
```

信号与执行：

```text
signal date D:
  weekly close-observed signal date

entry:
  first executable next open after D

exit:
  open after H3 trading days, using the existing EP5 natural-exit convention

cost:
  buy_cost_bps = 30
  sell_cost_bps = 80
  round_trip_cost_bps = 110
```

R08 只使用 H3：

```text
primary_horizon = H3
horizon_grid_audited = { H3 }
```

Split-purity rule：

```text
For H3 label in split S,
entry execution and H3 natural exit execution must both occur within S.
Cross-split labels are purged and counted in audit.
```

R08 的 candidate event 是：

```text
(signal_date, instrument_id)
```

只要该股票在 signal date 属于 PIT universe、factor 值可用、H3 label 可计算、且未被 split-purity purge，即成为 decision-bearing event。R08 不根据 score 选择股票。

## 7. Canonical Audit Scope

R08 只允许研究三个 family：

```text
volume_price_correlation
volume_surge_money_flow
vwap_deviation
```

Family assignment 与 included factor list 必须来自 R06 的 frozen artifacts：

```text
audit/r06_factor_family_map.csv
audit/r06_factor_registry.csv
```

R08 不允许：

- 新增 family；
- 合并 family；
- 拆分 family；
- validation-driven factor inclusion；
- validation-driven factor exclusion；
- validation-driven family selection。

R08 可以因为数据可用性排除某个 factor，但必须记录为 `factor_data_unavailable` 或 `factor_direction_sample_insufficient`，不得记录为 performance-driven exclusion。

Family 在 R08 中可评价必须满足：

```text
retained_factor_count >= max(2, ceil(0.50 * r06_family_included_factor_count))
```

若某 family 不满足该条件，该 family 的状态审计输出为 `family_blocked_insufficient_factor_coverage`。

## 8. Instrument Split and Transferability Contract

R08 必须同时测试时间迁移和股票迁移。

### 8.1 时间迁移

时间迁移沿用 EP5 split：

```text
train       = 2017-07-04 through 2021-12-31
validation  = 2022-01-01 through 2023-12-31
robustness  = 2024-01-01 through 2025-12-31
```

Train 只允许用于：

```text
factor direction
state bucket threshold
family state definition
normalization coverage rule
time-transfer non-deterioration baseline
```

Validation / robustness 只评价，不修改定义。

R08 必须区分两类 train 输入，不能混用：

```text
train_frozen_direction_input:
  instrument_train_set in train years only

train_frozen_bucket_edge_input:
  instrument_train_set in train years only

train_baseline_for_time_transfer_non_deterioration:
  all instruments active in PIT universe during train years,
  including instrument_train_set, instrument_validation_set,
  and instrument_robustness_set,
  after applying train-frozen factor direction and bucket edges
```

前两项用于冻结定义，必须只用 seen train instruments。第三项只用于 time-transfer 非劣化比较，必须使用 train years 内所有 active PIT instruments，使 validation / robustness 的 all-instrument spread 与 train baseline 的 instrument 口径对齐。任何 implementation 把这三项合并成一个 `train_mean_state_spread` 都视为 contract violation。

### 8.2 股票迁移

股票按 `instrument_id` 做 deterministic split：

```text
stable_hash = int(first_8_hex(sha256(instrument_id)), 16) mod 10

instrument_train_set:
  stable_hash in {0, 1, 2, 3, 4, 5}

instrument_validation_set:
  stable_hash in {6, 7}

instrument_robustness_set:
  stable_hash in {8, 9}
```

`instrument_train_set` 是 seen instruments。它可以出现在 train、validation、robustness 时间段中，但只有 train 时间段可用于方向和阈值冻结。

`instrument_validation_set` 是 validation unseen instruments。它只用于 validation 年份的 unseen 迁移评价。

`instrument_robustness_set` 是 robustness unseen instruments。它只用于 robustness 年份的 unseen 迁移确认。

Instrument split 基于所有曾经进入 PIT universe 的 `instrument_id` 冻结，但每个 split / segment 的样本判定必须基于该 split 内实际 active 的 PIT universe 周数。一个股票如果在某个 split 的 active 周数太少，不能因为 hash 落入该 segment 就计入迁移样本地板。

```text
instrument_active_signal_week_share_in_split
  = active_signal_week_count_in_split
    / total_signal_week_count_in_split

valid_for_segment_sample_floor:
  instrument_active_signal_week_share_in_split >= 0.50
```

R08 至少输出四个评价切片：

```text
seen instruments / validation years
unseen instruments / validation years
seen instruments / robustness years
unseen instruments / robustness years
```

核心问题是：

```text
单股内状态规律是否能迁移到未参与训练的股票？
```

如果只在 seen instruments 有效，final decision 只能是：

```text
r08_stock_specific_behavior_only
```

## 9. Within-Stock Normalization

R08 不再使用横截面 rank 作为 primary score。

对每只股票、每个 factor、每个 signal date D，使用该股票自身历史做 rolling 标准化。

### 9.1 Primary Percentile

Primary normalization：

```text
lookback_window_i(D):
  the prior 252 trading days before D for instrument i

min_history_count:
  126 valid factor observations

factor_ts_percentile_f,i(D):
  mid-rank percentile of current_factor_value_f,i(D)
  within valid lookback factor values
```

规则：

- lookback window 不包含 D 之后的数据；
- 当前 D 的 factor 值必须已经在 D close 可观察；
- 若 `valid_history_count < 126`，该 factor-stock-date 记为 `normalization_sample_insufficient`；
- percentile 范围为 `[0, 1]`；
- NaN、inf、停牌导致的无效值不得用未来值填充。

Tie handling 固定为 mid-rank percentile：

```text
factor_ts_percentile_f,i(D)
  = share(lookback_value < current_factor_value)
    + 0.5 * share(lookback_value == current_factor_value)
```

不得使用 `<= current_factor_value` 的右闭口径，因为量价 family 可能存在大量 0 值或近似常数簇，右闭 percentile 会把并列簇错误推到偏高状态。

### 9.2 Audit-Only Z-Score

Audit-only normalization：

```text
factor_ts_zscore_f,i(D)
  = (current_factor_value_f,i(D) - mean(prior_252_valid_values))
    / std(prior_252_valid_values)
```

`zscore` 只用于敏感性审计，因为它对极端值更敏感。Primary gates 不得使用 zscore 结果替代 percentile 结果。

### 9.3 As-Of Safety

R08 必须输出 normalization audit，证明：

```text
normalization_lookback_end_date < signal_date_or_equal_observed_close
normalization_uses_future_data = false
normalization_min_history_count_enforced = true
self_relative_label_lookback_only_uses_completed_h3_labels = true
self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1 = true
```

任何 future leak、cross-stock fill 或 validation-fitted scaler 都触发 `r08_blocked_data_or_execution_contract`。

## 10. Train-Only Direction and Family State Score

### 10.1 Factor Direction

每个 factor 的方向只能来自：

```text
instrument_train_set
train years
label_self_relative_H3
```

对每个 factor，先在每只股票内部计算：

```text
instrument_factor_rankic_f,i
  = SpearmanCorr(
      factor_ts_percentile_f,i(D),
      label_self_relative_H3_i(D)
    )
```

只使用满足以下条件的 instrument：

```text
train_signal_count_for_instrument_factor >= 80
factor_nonconstant_observation_share >= 0.80
```

Train-only direction statistic：

```text
factor_direction_stat_f
  = median_over_train_instruments(instrument_factor_rankic_f,i)
```

Direction：

```text
direction_f = +1 if factor_direction_stat_f >= 0
direction_f = -1 if factor_direction_stat_f < 0
```

若可用 train instruments 数量不足：

```text
train_direction_valid_instrument_count < 80
```

该 factor 记为 `factor_direction_sample_insufficient`，不得使用 validation / robustness 补方向。

### 10.2 Directional Percentile

为避免正负方向 factor 混在不同数值区间，R08 使用以下等价方向化：

```text
factor_oriented_percentile_f,i(D)
  = 0.5 + direction_f * (factor_ts_percentile_f,i(D) - 0.5)
```

含义：

```text
factor_oriented_percentile 越高，
代表该 factor 在 train direction 下越接近正向状态。
```

### 10.3 Family State Score

每个 family 的单股内状态分数为：

```text
family_ts_state_score_F,i(D)
  = equal_weight_mean_over_retained_family_factors(
      factor_oriented_percentile_f,i(D)
    )
```

约束：

- equal weight 固定；
- 不使用 RankIC weight；
- 不使用 t-stat weight；
- 不使用 validation weight；
- 不使用 per-stock factor weight；
- 不使用 optimizer。

若任一 family 的 `retained_factor_count < 3`，该 family 的结果必须带：

```text
low_factor_count_caveat = true
```

`low_factor_count_caveat` 不自动阻断 R08 评价，但如果该 family 是唯一 supported family，R09 授权必须在同一 supported scope 上重新确认：

```text
retained_factor_count >= 3
```

R08 的 family score 含义是：

```text
这只股票此刻相对自己历史处于多强的 family-defined 状态。
```

不是：

```text
这只股票相对其他股票是否更值得买。
```

## 11. Label Design

R08 primary label 固定为 H3。

### 11.1 Raw Stock Label

```text
label_raw_H3_i(D)
  = stock_H3_net_return_i(D)
```

`stock_H3_net_return` 使用 §6 的 entry、exit、110bps cost 和 split-purity 规则。

### 11.2 Self-Relative Label, Primary

Primary label：

```text
label_self_relative_H3_i(D)
  = stock_H3_net_return_i(D)
    - rolling_mean_stock_H3_net_return_i(
        over completed H3 labels whose H3 exit_date <= D - 1 trading day,
        within the prior 252 trading days before D
      )
```

规则：

- rolling mean 只使用 D 之前已经完成、可观察、且 split-purity 合格的 H3 labels；
- lookback H3 label 的 `exit_execution_date <= D - 1 trading day`；
- `min_self_label_history_count = 30`；
- history 不足时，该 stock-date 的 self-relative label 记为 unavailable；
- 不允许使用 validation / robustness 全局均值回填。

理由：

```text
R08 的问题是这只股票相对自身历史的状态是否有意义。
```

### 11.3 Industry-Relative Label, Audit-Only

```text
label_industry_relative_H3_i(D)
  = stock_H3_net_return_i(D)
    - same_industry_equal_weight_H3_net_return_excluding_self(D)
```

规则：

- industry membership 使用 PIT industry；
- same-industry return 必须排除当前股票；
- same-industry valid peer count 不足 10 时记为 unavailable；
- industry-relative label 是 residual / style audit，不是 primary gate 的替代品。

### 11.4 Gross Label

R08 必须同时输出 gross H3 label：

```text
stock_H3_gross_return
label_self_relative_H3_gross
label_industry_relative_H3_gross
```

Gross label 只用于成本敏感性解释，不得替代 net primary gate。

## 12. State Bucket Definition

R08 primary state bucket 使用 20% / 60% / 20% 的 extreme-tail 三桶，阈值只来自 train。它不是 equal-share tercile。这样做的目的是最大化 low/high 状态对比，而不是构造均匀三分组。

```text
bottom_quintile_state:
  family_ts_state_score <= train_q20(F)

middle_state:
  train_q20(F) < family_ts_state_score < train_q80(F)

top_quintile_state:
  family_ts_state_score >= train_q80(F)
```

阈值冻结样本：

```text
instrument_train_set
train years
decision-bearing stock-date events
```

每个 family 单独冻结 `train_q20` 和 `train_q80`。阈值一旦冻结，validation 和 robustness 不得修改。

下文 metric 名中的 `low_state` 等价于 `bottom_quintile_state`，`high_state` 等价于 `top_quintile_state`。Artifact 可以保留 `low_state` / `middle_state` / `high_state` 标签，但必须在 `r08_state_bucket_audit.csv` 中记录：

```text
bucket_method = train_frozen_extreme_tail_20_60_20
low_state_alias = bottom_quintile_state
high_state_alias = top_quintile_state
```

R08 同时保留 decile audit：

```text
state_decile_1 ... state_decile_10
```

Decile edges 同样只来自 train。Decile audit 只用于 monotonicity 解释，不用于调阈值。

## 13. Audit Units and Metric Definitions

R08 的 audit units：

```text
family_state_transfer_unit:
  granularity = (family, split, instrument_segment)
  state       = low / middle / high
  label       = label_self_relative_H3

family_decile_monotonicity_unit:
  granularity = (family, split, instrument_segment)
  state       = train-frozen decile

instrument_transfer_unit:
  granularity = (family, split, instrument_id)

year_transfer_unit:
  granularity = (family, split, calendar_year, instrument_segment)

concentration_unit:
  granularity = (family, split, contribution_source)
```

Primary spread 使用 date-weighted 计算，避免某些日期或某些股票因为事件更多而主导：

```text
date_high_mean(D)
  = mean(label_self_relative_H3 over high_state events on D)

date_low_mean(D)
  = mean(label_self_relative_H3 over low_state events on D)

date_high_minus_low_spread(D)
  = date_high_mean(D) - date_low_mean(D)

state_high_minus_low_spread
  = mean_over_valid_signal_dates(date_high_minus_low_spread(D))

state_high_minus_low_median
  = median_over_valid_signal_dates(date_high_minus_low_spread(D))
```

Valid signal date for primary spread：

```text
for all_instrument or seen_instrument segment:
  high_state_event_count(D) >= 10
  low_state_event_count(D)  >= 10

for unseen instrument segment:
  high_state_event_count(D) >= 5
  low_state_event_count(D)  >= 5
```

Unseen segment 使用较低 per-date floor 是为了避免 20% instrument hash bucket 在节假日、PIT 进出或 split-purity purge 后被机械卡死。该放松只影响 date 是否可评价，不放松 family-level sample gate、positive instrument share gate、monotonicity gate 或 non-deterioration gate。

Within-stock RankIC：

```text
within_stock_rankIC_F,i
  = SpearmanCorr(
      family_ts_state_score_F,i(D),
      label_self_relative_H3_i(D)
    )

within_stock_rankIC_F
  = median_over_valid_instruments(within_stock_rankIC_F,i)
```

Positive instrument share：

```text
instrument_high_minus_low_spread_F,i
  = mean(label_self_relative_H3 in high_state for i)
    - mean(label_self_relative_H3 in low_state for i)

positive_instrument_share_F
  = share of valid instruments with instrument_high_minus_low_spread_F,i > 0
```

Positive date share：

```text
positive_date_share_F
  = share of valid signal dates with date_high_minus_low_spread(D) > 0
```

Positive year count：

```text
positive_year_count_F
  = count of calendar years whose date-weighted high-low spread > 0
```

Decile monotonicity：

```text
state_decile_monotonicity_score
  = SpearmanCorr(decile_index, decile_mean_label_self_relative_H3)
```

每个 event 先按该 family 的 train-frozen decile edges 打上 within-stock decile。随后在 `(family, split, instrument_segment)` 内跨所有 event 池化，计算每个 decile 的 mean label，再用 `decile_index` 与 pooled decile mean label 计算 Spearman monotonicity。R08 不允许在每只股票内重新拟合 decile edges。

Contribution concentration：

```text
instrument_high_low_contribution_i
  = (mean(high_state_label_i) - mean(low_state_label_i))
    * (high_state_event_count_i + low_state_event_count_i)

instrument_contribution_share_i
  = abs(instrument_high_low_contribution_i)
    / sum_j(abs(instrument_high_low_contribution_j))

top1_instrument_contribution_share
  = max_i(instrument_contribution_share_i)

top5_instrument_contribution_share
  = sum of top 5 instrument_contribution_share_i values

industry_contribution_share_k
  = sum_{i in industry_k}(abs(instrument_high_low_contribution_i))
    / sum_j(abs(instrument_high_low_contribution_j))

top1_industry_contribution_share
  = max_k(industry_contribution_share_k)
```

若股票在 audit 窗口内换过行业，industry concentration 必须使用 signal date D 的 PIT industry，而不是使用当前行业或多数周行业。实现方式：

```text
industry_weight_i,k
  = count of high_state + low_state events for instrument i
    where PIT industry(i, D) = k
    / total high_state + low_state events for instrument i

industry_contribution_share_k
  = sum_i(abs(instrument_high_low_contribution_i) * industry_weight_i,k)
    / sum_j(abs(instrument_high_low_contribution_j))
```

必须用上述高低状态 spread 的绝对贡献分解计算，并输出 top1 / top5 instrument 与 top1 industry。若分母为 0，concentration gate 不得 pass，必须记录 `contribution_denominator_zero = true`。

## 14. Required Metrics

每个 family 至少输出：

```text
state_high_minus_low_spread
state_high_minus_low_median
state_decile_monotonicity_score
within_stock_rankIC
positive_instrument_share
positive_date_share
positive_year_count
unseen_instrument_spread
robustness_unseen_instrument_spread
top1_instrument_contribution_share
top5_instrument_contribution_share
top1_industry_contribution_share
industry_relative_high_minus_low_spread
gross_vs_net_spread_difference
```

特别重要：

```text
positive_instrument_share
```

因为 R08 必须防止：

```text
只有少数股票有效。
```

## 15. Gate Design

所有 gate 均按 family 独立评价。Final decision 根据 family-level gate replay 汇总。

### 15.1 Sample Gate

Sample gate 分为 full-scope floor 和 segment floor，避免把 unseen 20% instrument segment 错误要求到 300 只股票。

Full-scope floor：

```text
full_scope_instrument_count >= 300
retained_factor_count >= max(2, ceil(0.50 * r06_family_included_factor_count))
```

Segment floor，对每个 family、split、instrument_segment 分别评价：

```text
valid_instrument_count >= 100
valid_signal_dates >= 70 per split
min_per_instrument_signal_count >= 80
```

其中 `valid_instrument` 指在该 split / segment 下同时满足：

```text
instrument_active_signal_week_share_in_split >= 0.50
valid_signal_count >= 80
high_state_event_count >= 10
low_state_event_count >= 10
```

这里的 `high_state_event_count` / `low_state_event_count` 是该 instrument 在整个 split 内的事件数，不是单个 signal date 的横截面厚度。单个 signal date 的 high/low event floor 按 §13 的 segment-specific rule 评价。

若 sample gate 失败，family 记为 `family_sample_blocked`，不得当作 pass 或 fail。

若 in-scope 的 3 个 family 中有 2 个或以上 sample blocked，R08 不得由剩余单一 family 直接授权 R09；final decision 必须走 `r08_blocked_data_or_execution_contract`，并记录：

```text
sample_block_annotation = majority_family_sample_blocked
```

### 15.2 Time Transfer Gate

Time transfer gate 使用 all-instrument segment，但必须同时报告 seen / unseen 细分。

```text
validation_mean_state_spread > 0
validation_median_state_spread >= 0
validation_positive_year_count >= 2
validation_mean_state_spread
  >= train_baseline_time_transfer_mean_state_spread - 0.0030
robustness_mean_state_spread >= -0.0025
robustness_median_state_spread >= -0.0025
robustness_mean_state_spread
  >= train_baseline_time_transfer_mean_state_spread - 0.0040
```

这里的 `train_baseline_time_transfer_mean_state_spread` 必须使用 train years 内所有 active PIT instruments 的 decision-bearing events，不能限制为 `instrument_train_set`。它不得用于 factor direction、bucket edge 或 family definition 的冻结。

Validation 期只有 2022 和 2023 两年。R08 supported 仍要求：

```text
validation_positive_year_count >= 2
```

即两年都必须为正。若只有一年为正，R08 可以记录诊断 annotation，但不得把它当成 supported：

```text
validation_single_positive_year_candidate = true
  if validation_positive_year_count == 1
     and validation_mean_state_spread >= +0.0010
     and validation_negative_year_mean_spread >= -0.0015
```

该 annotation 只说明有单年线索，不授权 R09。

R08 的 robustness floor 允许小幅衰减，但不允许明显反转。

### 15.3 Instrument Transfer Gate

Instrument transfer gate 关注 unseen instruments：

```text
unseen_validation_mean_spread > 0
unseen_validation_median_spread >= 0
unseen_robustness_mean_spread >= -0.0025
unseen_validation_mean_spread >= seen_validation_mean_spread - 0.0020
unseen_robustness_mean_spread >= seen_robustness_mean_spread - 0.0030
positive_instrument_share_validation_all >= 0.55
positive_instrument_share_robustness_all >= 0.50
positive_instrument_share_validation_unseen >= 0.55
positive_instrument_share_robustness_unseen >= 0.50
```

若 seen instruments pass 但 unseen instruments fail，family 只能归为：

```text
stock_specific_behavior_only
```

### 15.4 Concentration Gate

```text
top1_instrument_contribution_share <= 0.05
top5_instrument_contribution_share <= 0.20
top1_industry_contribution_share <= 0.35
```

该 gate 防止状态关系只由少数股票或少数行业贡献。

### 15.5 Monotonicity Gate

```text
state_decile_monotonicity_score >= 0.60
high_state_minus_low_state_spread > 0
middle_state_mean_label between low_state_mean_label and high_state_mean_label
```

`middle_state_mean_label` 可以有小幅噪声，但不得出现 violently inverted pattern。R08 定义：

```text
violently_inverted_middle = true
  if middle_state_mean_label < min(low_state_mean_label, high_state_mean_label) - 0.0025
  or middle_state_mean_label > max(low_state_mean_label, high_state_mean_label) + 0.0025
```

R08 不放松 R06/R07 的 monotonicity discipline。虽然 R08 是单股内状态诊断，不是策略 requirement，但 `r08_single_stock_state_transferability_supported` 会授权 R09 narrow strategy requirement，因此 monotonicity gate 必须保持 `>= 0.60`。

### 15.6 Residual Audit, Not Primary Gate

Industry-relative、beta、liquidity decomposition 是解释性审计。它们不能创造 pass。

若 primary gate 全部通过，但 industry-relative spread 明显为负，final report 必须把结论标记为：

```text
transferability_supported_but_style_residual_unconfirmed
```

该标记不改变 final decision enum，但会限制 R09 只能写 residual-first narrow requirement，不能直接写 long-only strategy requirement。

## 16. Final Decisions

R08 输出 exactly one final decision：

```text
r08_blocked_data_or_execution_contract
r08_no_single_stock_transferability_support
r08_stock_specific_behavior_only
r08_time_transfer_only_unstable
r08_single_stock_state_transferability_supported
```

Decision definitions：

```text
r08_blocked_data_or_execution_contract:
  - data, split, H3 label, normalization, instrument split,
    factor coverage, or as-of contract fails;
  - or no family reaches sample gate;
  - or at least 2 of 3 in-scope families are sample blocked;
  - no downstream requirement is authorized.

r08_no_single_stock_transferability_support:
  - at least one family is evaluable;
  - no family passes time transfer + instrument transfer + concentration
    + monotonicity gates;
  - no downstream requirement is authorized.

r08_stock_specific_behavior_only:
  - at least one family passes seen-instrument validation criteria;
  - unseen validation or unseen robustness does not confirm;
  - evidence is stock-specific behavior only;
  - no strategy requirement is authorized.

r08_time_transfer_only_unstable:
  - at least one family passes validation time-transfer readout;
  - robustness does not confirm non-deterioration;
  - no strategy requirement is authorized.

r08_single_stock_state_transferability_supported:
  - sample gate passes;
  - time transfer gate passes;
  - instrument transfer gate passes;
  - concentration gate passes;
  - monotonicity gate passes;
  - train-relative validation and robustness non-deterioration pass;
  - R08 supports cross-stock and cross-year transferable H3 state information;
  - only this decision allows writing R09 narrow strategy requirement.
```

R08 supported 仍然不是 strategy pass。

## 17. First-Match Rule Replay

Final decision 必须通过固定 first-match rule replay 得出：

```text
rule_01:
  if scope_violation_detected
  or asof_violation_detected
  or instrument_split_violation_detected
  or h3_label_contract_violation_detected
  -> r08_blocked_data_or_execution_contract

rule_02:
  if evaluable_family_count == 0
  -> r08_blocked_data_or_execution_contract

rule_02b:
  if sample_blocked_family_count / total_in_scope_family_count >= 0.50
  -> r08_blocked_data_or_execution_contract
     with annotation = majority_family_sample_blocked

rule_03:
  if supported_family_count > 0
  -> r08_single_stock_state_transferability_supported

rule_04:
  if seen_instrument_pass_family_count > 0
     and unseen_transfer_pass_family_count == 0
  -> r08_stock_specific_behavior_only

rule_05:
  if validation_transfer_pass_family_count > 0
     and robustness_transfer_pass_family_count == 0
  -> r08_time_transfer_only_unstable

rule_06:
  otherwise
  -> r08_no_single_stock_transferability_support
```

Rule order 固定。R08 不允许根据中间结果调整 rule order。

## 18. Downstream Authorization

只有当 final decision 为：

```text
r08_single_stock_state_transferability_supported
```

才允许写 R09 narrow strategy requirement。

R09 scope 必须满足：

```text
scope_family_count <= 1
scope_horizon_count = 1
scope_horizon = H3
state_definition_inherits_R08 = true
instrument_transfer_evidence_required = true
monotonicity_gate_required = "state_decile_monotonicity_score >= 0.60"
retained_factor_count_recheck_required = true
retained_factor_count >= 3
validation_threshold_reselection_allowed = false
stock_specific_threshold_allowed = false
right_tail_gate_allowed = false
```

R08 supported 必须建立在至少 2 个 in-scope families 完成样本可评价的前提上。若 3 个 family 中有 2 个或以上 sample blocked，即使剩余单一 family 五门全过，R08 也不得授权 R09。

如果 R08 final decision 是任何其他值，Alpha191 在当前 EP5 框架下应停止，不得继续横截面或单股搜索。

## 19. Required Artifacts

R08 writes the following artifacts under
`ep5/outputs/r08_h3_volume_price_single_stock_state_transferability_audit_v0/`:

```text
audit/
  r08_run_manifest.json
  r08_input_data_audit.csv
  r08_factor_family_scope.csv
  r08_within_stock_normalization_audit.csv
  r08_factor_direction_audit.csv
  r08_instrument_split_audit.csv
  r08_h3_label_audit.csv
  r08_state_bucket_audit.csv
  r08_transferability_sample_audit.csv
  r08_concentration_audit.csv

metrics/
  r08_family_state_spread_summary.csv
  r08_instrument_transfer_summary.csv
  r08_time_transfer_summary.csv
  r08_seen_unseen_comparison.csv
  r08_state_decile_monotonicity.csv
  r08_industry_beta_liquidity_decomposition.csv

decision/
  r08_gate_inputs.csv
  r08_final_decision_replay.csv
  r08_final_decision.csv

reports/
  r08_final_report.md
```

### 19.1 Required Artifact Columns

`audit/r08_factor_family_scope.csv`：

```text
family
r06_family_included_factor_count
r08_retained_factor_count
retained_factor_ids
excluded_factor_ids
excluded_reason_set
family_scope_pass
low_factor_count_caveat
```

`audit/r08_within_stock_normalization_audit.csv`：

```text
family
factor_id
split
instrument_segment
stock_date_count
normalization_sample_pass_count
normalization_sample_fail_count
min_history_count
uses_future_data_flag
cross_stock_fill_flag
factor_value_tie_share_in_lookback
factor_value_at_tie_cluster_flag
```

`audit/r08_factor_direction_audit.csv`：

```text
family
factor_id
train_direction_valid_instrument_count
factor_direction_stat
factor_direction_stat_p25
factor_direction_stat_p75
direction
direction_source_split
direction_status
```

`audit/r08_instrument_split_audit.csv`：

```text
instrument_id
stable_hash_mod10
instrument_segment
first_eligible_signal_date
last_eligible_signal_date
train_signal_count
validation_signal_count
robustness_signal_count
train_active_signal_week_share
validation_active_signal_week_share
robustness_active_signal_week_share
```

`audit/r08_h3_label_audit.csv`：

```text
split
instrument_segment
total_signal_date_count
purged_cross_split_signal_date_count
unpurged_signal_date_count
raw_label_available_count
self_relative_label_available_count
industry_relative_label_available_count
industry_relative_peer_count_min
industry_relative_peer_count_p50
self_relative_label_lookback_only_uses_completed_h3_labels
self_relative_label_uses_lookback_h3_exit_date_le_D_minus_1
```

`audit/r08_state_bucket_audit.csv`：

```text
family
train_q20
train_q80
decile_edges_train
bucket_method
low_state_alias
high_state_alias
bucket_edges_source_split
frozen_before_validation_read
low_state_count_train
middle_state_count_train
high_state_count_train
```

`audit/r08_concentration_audit.csv`：

```text
family
split
instrument_segment
contribution_denominator
contribution_denominator_zero
top1_instrument_id
top1_instrument_contribution_share
top5_instrument_contribution_share
top1_industry
top1_industry_contribution_share
concentration_gate_pass
top1_instrument_event_count
top1_instrument_active_split_share
```

`audit/r08_transferability_sample_audit.csv`：

```text
family
split
instrument_segment
per_date_high_low_event_floor
valid_signal_date_count_by_event_floor
filtered_signal_date_count_by_event_floor
valid_instrument_count
sample_gate_pass
sample_block_reason
```

`metrics/r08_family_state_spread_summary.csv`：

```text
family
split
instrument_segment
state
valid_signal_dates
event_count
mean_label_self_relative_H3
median_label_self_relative_H3
state_high_minus_low_spread
state_high_minus_low_median
positive_date_share
```

`metrics/r08_instrument_transfer_summary.csv`：

```text
family
split
instrument_segment
valid_instrument_count
positive_instrument_count
positive_instrument_share
median_within_stock_rankIC
mean_instrument_high_minus_low_spread
median_instrument_high_minus_low_spread
```

`metrics/r08_time_transfer_summary.csv`：

```text
family
split
mean_state_spread
median_state_spread
positive_year_count
positive_date_share
train_baseline_time_transfer_mean_state_spread
validation_single_positive_year_candidate
validation_negative_year_mean_spread
validation_vs_train_non_deterioration_pass
robustness_vs_train_non_deterioration_pass
```

`metrics/r08_seen_unseen_comparison.csv`：

```text
family
split
seen_mean_spread
seen_median_spread
seen_positive_instrument_share
unseen_mean_spread
unseen_median_spread
unseen_positive_instrument_share
seen_minus_unseen_spread
unseen_vs_seen_non_deterioration_pass
```

`metrics/r08_state_decile_monotonicity.csv`：

```text
family
split
instrument_segment
decile
event_count
mean_label_self_relative_H3
state_decile_monotonicity_score
middle_state_violently_inverted_flag
```

`metrics/r08_industry_beta_liquidity_decomposition.csv`：

```text
family
split
instrument_segment
industry_relative_high_minus_low_spread
beta_bucket_high_minus_low_spread
liquidity_bucket_high_minus_low_spread
industry_relative_sign_confirms_primary
style_residual_annotation
```

`decision/r08_gate_inputs.csv`：

```text
family
sample_gate_pass
sample_block_annotation
time_transfer_gate_pass
instrument_transfer_gate_pass
concentration_gate_pass
monotonicity_gate_pass
validation_vs_train_non_deterioration_pass
robustness_vs_train_non_deterioration_pass
train_baseline_input_scope
train_frozen_direction_input_scope
train_frozen_bucket_edge_input_scope
seen_instrument_pass
unseen_transfer_pass
low_factor_count_caveat
validation_single_positive_year_candidate
supported_family_flag
family_decision_label
```

`decision/r08_final_decision_replay.csv`：

```text
rule_id
rule_condition_text
rule_fires_flag
selected_rule_flag
```

`decision/r08_final_decision.csv`：

```text
final_decision
authorized_r09_flag
authorized_family_set
style_residual_annotation
sample_block_annotation
sample_blocked_family_count
total_in_scope_family_count
```

## 20. Required Report Questions

`reports/r08_final_report.md` 必须按顺序回答：

1. R08 是否避免了横截面 top20% 策略构造？
2. 是否只研究 H3？
3. 是否只研究 `volume_price_correlation`、`volume_surge_money_flow`、`vwap_deviation`？
4. 单股内 percentile / zscore 是否 as-of safe？
5. 状态方向是否只来自 train？
6. validation 是否有 high-low state spread？
7. robustness 是否确认？
8. seen instruments 和 unseen instruments 表现是否一致？
9. positive instrument share 是否足够？
10. 是否只有少数股票贡献收益？
11. 是否只有少数行业贡献收益？
12. 是否存在单股内 decile monotonicity？
13. 哪个 family 的 transferability 最强？
14. 结果是可迁移状态信息、个股特异性，还是无支持？
15. 是否允许 R09 写 narrow strategy requirement？
16. `volume_price_correlation` H3 的 within-stock spread 在 seen / unseen / validation / robustness 四切片中，相比 R07 cross-sectional H3 spread（validation `0.333%` / robustness `0.170%`）方向和量级是否一致？如果方向相反或量级显著萎缩，原因是 within-stock 归一化效果，还是问题定义切换后失去了 R07 看到的信号？
17. Time-transfer non-deterioration 的 train baseline 是否使用 train years 内所有 active PIT instruments，并且是否与 direction / bucket edge 的 seen-train-only 冻结输入分离？
18. unseen segment 有多少 signal dates 因 high/low per-date event floor 被过滤，过滤后是否仍满足 sample gate？

Report 必须明确区分：

```text
transferability evidence
stock-specific behavior
time-only instability
no support
data blocked
```

## 21. Validator Expectations

R08 validator 至少检查：

```text
V01 requirement_id matches config phase
V02 output root matches requirement
V03 only H3 is used
V04 only three allowed families are used
V05 no top-N or top-fraction selected basket exists
V06 instrument split is deterministic sha256 mod10
V07 train-only direction source is enforced
V08 train-only state bucket edges are enforced
V09 within-stock normalization is as-of safe
V10 self-relative H3 label uses prior data only
V11 industry-relative label excludes self
V12 sample gate fields are present
V13 seen/unseen validation and robustness summaries are present
V14 concentration metrics are present
V15 monotonicity metrics are present
V16 first-match final decision replay selects exactly one rule
V17 no online data path is touched
V18 final report answers all required questions
V19 train-relative non-deterioration gates are present and replayed
V20 active PIT instrument week share is enforced in sample gates
V21 completed-H3-label as-of rule is enforced for self-relative labels
V22 R07 volume_price_correlation H3 sanity comparison is present in the report
V23 train baseline for time-transfer non-deterioration uses all active train-year instruments
V24 factor percentile tie handling uses mid-rank percentile
V25 unseen per-date event floor is segment-specific and reported
V26 industry concentration uses PIT industry at signal date
```

Any validator failure produces:

```text
r08_blocked_data_or_execution_contract
```

unless the failure is strictly report-format-only and all decision artifacts are valid. Report-format-only failures must still block publish until corrected.

## 22. Relationship to R07

R07 的结论是：

```text
横截面 pocket 存在；
但无法通过 clean attribution 和 state stability。
```

R08 的新问题是：

```text
这些 pocket 是否不是横截面排序问题，
而是单只股票自身状态问题？
```

所以 R08 不是 R07 的参数修补。R08 是问题定义切换。

最小 R08 只测试：

```text
families:
  volume_price_correlation
  volume_surge_money_flow
  vwap_deviation

horizon:
  H3

state:
  within-stock 252d percentile

label:
  H3 self-relative net return

validation:
  time transfer + instrument transfer
```

如果 R08 也失败，Alpha191 在当前 EP5 框架下应完全停止，而不是继续横截面或单股搜索。
