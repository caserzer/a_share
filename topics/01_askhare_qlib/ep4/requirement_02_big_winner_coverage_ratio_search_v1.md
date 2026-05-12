# EP4 Requirement 02: Big Winner Coverage Ratio Search V1

## 1. Requirement Metadata

- Requirement id: `ep4_r02_big_winner_coverage_ratio_search_v1`
- Short name: `r02_big_winner_coverage_ratio_search_v1`
- Status: descriptive profile requirement draft
- Owner workflow: EP4
- Required output root: `ep4/outputs/r02_big_winner_coverage_ratio_search_v1/`
- Required config path: `ep4/configs/r02_big_winner_coverage_ratio_search_v1.yaml`
- Required runner path: `ep4/scripts/run_r02_big_winner_coverage_ratio_search.py`
- Required validator path: `ep4/scripts/validate_r02_big_winner_coverage_ratio_search.py`
- Required parallelism: CPU `12` cores for condition-group coverage / density search

## 2. Purpose

本需求只回答一个窄问题：

```text
在 845 个 canonical R01 primary big winner 的 reference_date 后 T+0 到 T+30 窗口内，
哪些同 family 内部的 3 到 4 个并列日级条件，
可以覆盖至少 85% 的 big winner，
同时在 R01 PIT-executable eligible stock-days 上保持可解释的日级触发密度？
```

本需求不是 entry 策略，不训练模型，不做仓位分配，不把 winner-window coverage 当成 prior / posterior / precision。

本需求明确是 full-sample descriptive profile。845 个 canonical R01 primary big winner 可以全部用于覆盖率搜索、排序和报告，但所有结果只能作为事后画像证据，不允许进入下一阶段 promotion、family freezing、evidence accumulation、entry trigger 或风险预算设计。

## 3. Hard Scope

允许：

- 使用固定的 845 个 canonical R01 primary big winner 作为覆盖率分母；
- 在每个 big winner 的 `reference_date + 0` 到 `reference_date + 30` 内计算日级条件是否触发；
- 在 R01 PIT-executable eligible stock-days 上计算同一条件的日级触发密度；
- 按 feature family 内部搜索 3 条或 4 条并列条件；
- 使用 12 core CPU 并行计算 condition-group coverage / density；
- 输出覆盖率、密度、触发 offset、split 稳定性和 uncovered winner 明细。

禁止：

- 搜索跨 family 的组合，例如 `price_trend AND volume_money AND momentum_rps`；
- 使用 1 条、2 条、5 条或更多条并列条件作为主搜索结果；
- 使用除 `5 / 10 / 30 / 60` 外的窗口作为主搜索窗口；
- 用 validation / robustness 结果反向改条件、阈值或 family 定义；
- 把 `T+0..T+30` winner-window coverage 解释为 action-time 胜率；
- 把 market_context 当作普通技术指标混进同 family 条件组合；
- 将任何候选标记为 train-selected、holdout-validated、R03-ready 或可交易 family；
- 因并行分片顺序改变候选集合、排序、hash 或报告结果；
- 引入新的在线数据抓取。

## 4. Required Inputs

主输入必须来自本地已有 EP4 / R01 数据和 PIT 数据：

- `845` 个 canonical R01 primary big winner reference events；
- 每个 reference event 的 `instrument_id`、`reference_date`、`split`；
- R01 PIT-executable eligible stock-day denominator；
- PIT OHLCV / amount / turnover / industry / market context 数据；
- R01 使用过的交易日历、停牌/脏 bar、可执行性过滤口径。

实现必须记录输入 artifact path、hash、row count 和 coverage denominator count。若 canonical R01 primary big winner 数量不是 `845`，必须 fail closed，除非 config 显式声明 `allow_reference_count_drift = true` 且报告单独解释 drift。

## 5. Core Definitions

### 5.1 Big Winner Coverage

覆盖定义固定为：

```text
covered(event, condition_group) =
  exists profile_trade_date in [reference_date + 0, reference_date + 30 trading days]
  such that condition_group is true on that profile_trade_date
```

整体覆盖率：

```text
coverage_t0_t30 =
  count(covered canonical R01 primary big winner events) / 845
```

主通过门槛：

```text
coverage_t0_t30 >= 0.85
```

必须同时报告：

- `covered_events_t0_t30`
- `uncovered_events_t0_t30`
- `coverage_t0_t30`
- `coverage_t0_t30_by_split`
- `coverage_t0_t30_by_year`
- `median_earliest_hit_offset`
- `median_closest_hit_offset`
- `offset_bucket_coverage`: `D0-D5`, `D6-D10`, `D11-D20`, `D21-D30`

### 5.2 Eligible-Day Density

密度定义固定为：

```text
eligible_day_density =
  count(R01 PIT-executable eligible stock-days where condition_group is true)
  / count(R01 PIT-executable eligible stock-days)
```

若与 Section 12 的详细口径冲突，以 Section 12 为准；这里的 `eligible_day_density` 等价于 Section 12 的 global-denominator density。

密度不是 winner-window 内的触发比例。报告必须把下面两个分母分开：

- `winner_coverage_denominator = 845 canonical R01 primary big winner events`
- `density_denominator = R01 PIT-executable eligible stock-days`

密度用于排序和成本解释，不作为本需求的硬 stop gate。默认排序优先级为：

```text
coverage_t0_t30 desc,
eligible_day_density asc,
median_earliest_hit_offset asc,
condition_group_id asc
```

## 6. Feature Families

主搜索只允许以下 7 个技术状态 family。每个候选组合必须完全来自同一个 family。

| family_id | allowed concept scope |
|:--|:--|
| `price_trend` | 价格、MA、EMA、趋势斜率、价格相对均线、均线排列 |
| `momentum_rps` | 收益率、动量、RPS、相对强度、行业内/市场内强弱排名 |
| `volatility_band` | 波动率、ATR、Bollinger、通道宽度、价格在通道内的位置 |
| `volume_money` | 成交量、成交额、换手、量能放大/缩小、价量配合 |
| `range_breakout` | 突破、区间位置、新高新低、N 日高低点距离 |
| `pullback_drawdown` | 回撤、回踩、反弹、距高点天数、从低点反弹幅度 |
| `oscillator` | RSI、KDJ、CCI、MACD hist、震荡超买超卖状态 |

### 6.1 Market Context

`market_context` 只允许作为分层或审计字段，不允许作为主搜索 family 条件混入 3 到 4 条并列条件，也不允许以 `context_filter` 的形式改变 `ge85` 主结果表。

允许的用途：

- 市场状态分层，例如 index trend / market breadth；
- 行业、主题、风格分层；
- 输出 coverage / density decomposition。

禁止的用途：

```text
price_trend_condition_1 AND market_context_condition_1 AND price_trend_condition_2
```

交易状态约束只能来自 R01 PIT-executable eligible stock-day denominator 的既有资格过滤，例如非停牌、非脏 bar、可执行性口径；不得在本需求中新增市场、行业、主题或风格过滤。

如果需要报告 market context decomposition，必须对每个主结果输出：

- `market_context_dimension`
- `market_context_bucket`
- `bucket_winner_count`
- `bucket_coverage_t0_t30`
- `bucket_eligible_day_count`
- `bucket_eligible_day_density`
- `decomposition_only_flag = true`

## 7. Window Contract

所有主搜索窗口固定为：

```yaml
allowed_windows: [5, 10, 30, 60]
```

不得在主搜索中使用 `3 / 20 / 120 / 250` 等其他窗口。若实现需要额外窗口做调试，只能写入 diagnostic artifact，不能进入候选字典、排序、推荐结果或 final decision。

每个原子条件必须记录：

- `atomic_condition_id`
- `family_id`
- `window`
- `operator`
- `threshold`
- `pit_formula`
- `required_fields`
- `lookback_days_required`
- `nan_policy`

## 8. Atomic Search Space Contract

实现必须在任何 coverage / density 计算前，从 config 生成冻结原子条件字典：

`reports/r02_big_winner_coverage_atomic_condition_dictionary.csv`

该字典是主搜索空间的唯一 authority。实现不得在运行中根据覆盖结果新增、删除、重命名或调参。

每个原子条件必须包含：

- `atomic_condition_id`
- `family_id`
- `feature_template_id`
- `window`: only one of `5 / 10 / 30 / 60`
- `operator`
- `threshold`
- `pit_formula`
- `required_fields`
- `lookback_days_required`
- `warmup_policy`
- `nan_policy`
- `formula_hash`

允许的 feature templates 至少包括：

| family_id | required template examples |
|:--|:--|
| `price_trend` | `close_over_ma_N`, `close_over_ema_N`, `ma_slope_N`, `ema_slope_N`, `ma_alignment_N` |
| `momentum_rps` | `ret_N`, `roc_N`, `rps_N`, `market_relative_ret_N`, `industry_relative_ret_N` |
| `volatility_band` | `realized_vol_N`, `atr_ratio_N`, `boll_pct_b_N`, `boll_width_N`, `price_channel_position_N` |
| `volume_money` | `volume_ratio_N`, `amount_ratio_N`, `turnover_ratio_N`, `money_zscore_N`, `money_price_coherence_N` |
| `range_breakout` | `close_near_high_N`, `close_breaks_high_N`, `close_near_low_N`, `range_position_N`, `new_high_flag_N` |
| `pullback_drawdown` | `drawdown_from_high_N`, `pullback_depth_N`, `rebound_from_low_N`, `days_since_high_N`, `pullback_recovery_N` |
| `oscillator` | `rsi_N`, `kdj_k_N`, `kdj_d_N`, `cci_N`, `macd_hist_state_N` |

每个 template 的 threshold 列表必须在 config 中显式声明，例如：

```yaml
thresholds:
  rps_N: [50, 60, 70, 80]
  ret_N: [0.0, 0.05, 0.10]
  close_over_ma_N: [0.0, 0.03, 0.05]
```

validator 必须 fail closed：

- 原子条件缺少 formula 或 formula_hash；
- 原子条件使用未声明 template；
- 原子条件使用非法 window；
- 原子条件 threshold 不在 config 声明列表内；
- 原子条件含有 future data 或 winner-label 字段。

候选组合可以使用 deterministic atom preselection 控制组合爆炸，但必须在 config 中声明：

```yaml
search:
  deterministic_candidate_atom_cap_per_family: 24
```

preselection 规则必须满足：

- 每个 family 内按 template 轮转选择 atom；
- 每个 template 内按 `window, threshold, atomic_condition_id` 稳定排序；
- atomic dictionary 必须保留全部 atom，并用 `selected_for_candidate_generation` 标记是否进入 AND3 / AND4 组合生成；
- candidate dictionary 只能由 `selected_for_candidate_generation = true` 的 atom 生成；
- final report / manifest 必须报告 `atomic_condition_count`、`selected_atomic_condition_count` 和 `deterministic_candidate_atom_cap_per_family`。

## 9. Parallel Condition Search Contract

本需求中的“并列条件”定义为同一交易日上同时满足的 `AND` 条件组。

主搜索只允许：

```text
same_family_and3: condition_a AND condition_b AND condition_c
same_family_and4: condition_a AND condition_b AND condition_c AND condition_d
```

硬约束：

- `n_terms in [3, 4]`
- 所有 `atomic_condition.family_id` 必须相同；
- 同一组合内不得出现完全重复的 `atomic_condition_id`；
- 同一组合内允许不同 window 的同类条件，例如 `MA5 / MA10 / MA30`；
- 同一组合内允许同 window 但不同阈值的条件，前提是报告 `redundancy_flag`；
- 不允许 `k-of-n` 作为主搜索结果；
- 不允许 OR / NOT / sequence / future-aware 条件；
- 不允许条件之间带时间先后关系。

组合 ID 规范：

```text
{family_id}__and{n_terms}__{short_hash}
```

示例合法组合：

```text
price_trend: close_above_ma5 AND close_above_ma10 AND ma30_slope_gt_0
momentum_rps: ret10_gt_0 AND rps30_gt_70 AND relative_strength60_gt_0
volume_money: amount_ratio5_gt_1_2 AND turnover10_gt_median AND money_price_coherence30_gt_0
```

示例非法组合：

```text
price_trend.close_above_ma10 AND volume_money.amount_ratio10_gt_1_2 AND momentum_rps.rps30_gt_70
```

## 10. Parallel Execution Contract

主搜索必须支持 CPU 12 core 并行执行：

```yaml
parallel_search:
  enabled: true
  backend: process_pool
  max_workers: 12
  chunk_unit: condition_group_id
  deterministic_merge: true
```

并行边界：

- 并行任务粒度必须是 `condition_group_id` 或其 deterministic chunk；
- worker 只能读取冻结的 atomic dictionary、candidate dictionary、winner profile panel 和 eligible-day density panel；
- worker 不得在运行中新增、删除或改写候选；
- worker 输出必须包含 `condition_group_id`、`worker_id`、`chunk_id`、`chunk_sequence` 和 `result_hash`；
- merge 必须按 `condition_group_id` 稳定排序后再计算 rank；
- 相同输入、相同 config、相同 `max_workers = 12` 必须生成完全相同的 CSV / manifest hash；
- 若实际机器可用 CPU 小于 12，runner 必须 fail closed，除非 config 显式设置 `allow_worker_downgrade = true`，并在 manifest / final report 写明实际 worker 数。

禁止：

- 用并行 worker 随机抽样候选；
- 因超时、内存或 worker failure 静默丢弃 chunk；
- 因 chunk 完成顺序决定 top-N；
- 在 worker 内读取 validation / robustness 结果来改变条件；
- 使用线程共享可变全局状态累计 coverage / density。

manifest 必须记录：

- `parallel_enabled`
- `parallel_backend`
- `configured_max_workers`
- `actual_worker_count`
- `allow_worker_downgrade`
- `chunk_unit`
- `chunk_count`
- `failed_chunk_count`
- `retried_chunk_count`
- `deterministic_merge`
- `parallel_result_hash`
- `atomic_condition_count`
- `selected_atomic_condition_count`
- `deterministic_candidate_atom_cap_per_family`

validator 必须 fail closed：

- `configured_max_workers != 12`；
- `parallel_enabled != true`；
- `deterministic_merge != true`；
- `failed_chunk_count > 0`；
- 任一 candidate dictionary row 缺少对应搜索结果；
- rerun manifest 的 `parallel_result_hash` 与同输入 single-pass audit hash 不一致。

实现可以额外提供 single-pass audit mode，但 audit mode 只能用于验证 12-core 并行结果，不得替代主搜索输出。

## 11. Candidate Dictionary

实现必须在计算 coverage 之前生成冻结候选字典：

`reports/r02_big_winner_coverage_candidate_dictionary.csv`

必需字段：

- `condition_group_id`
- `family_id`
- `kind`: `same_family_and3` or `same_family_and4`
- `n_terms`
- `atomic_condition_ids`
- `windows`
- `thresholds`
- `pit_formula`
- `uses_market_context_filter`: must be `false`
- `market_context_decomposition_required`
- `redundancy_flag`
- `formula_hash`

validator 必须 fail closed：

- 后续结果中出现未登记的 `condition_group_id`；
- 任一组合混入多个技术 family；
- 任一组合使用非法 window；
- 任一组合 `n_terms` 不在 `[3, 4]`；
- 任一组合使用 market_context 作为普通 term。
- 任一组合使用 market_context 作为 filter。

## 12. Density Denominator And Missingness

由于 `5 / 10 / 30 / 60` 窗口存在不同 warmup 要求，density 必须同时报告两个分母：

```text
global_eligible_day_denominator =
  count(R01 PIT-executable eligible stock-days)

feature_eligible_day_denominator(condition_group) =
  count(R01 PIT-executable eligible stock-days
        where every atomic condition in the group has complete required lookback)
```

主排序 density 使用：

```text
eligible_day_density =
  eligible_day_trigger_count / global_eligible_day_denominator
```

同时必须报告：

```text
feature_eligible_day_density =
  eligible_day_trigger_count / feature_eligible_day_denominator
```

missing / warmup 规则：

- 如果 stock-day 属于 R01 PIT-executable eligible denominator，但某个 atomic condition 缺少必要 lookback，则该 stock-day 在 `global_eligible_day_denominator` 中保留，并对该 condition_group 视为 `condition_group_trigger = false`；
- 同一 stock-day 只有当组合内所有 atomic condition 都 feature-complete 时，才进入 `feature_eligible_day_denominator`；
- 必须报告 `feature_eligible_ratio = feature_eligible_day_denominator / global_eligible_day_denominator`；
- 若 `feature_eligible_ratio < 0.80`，候选必须带 `low_feature_coverage_warning = true`。

## 13. Metrics

每个 `condition_group_id` 至少输出：

- `condition_group_id`
- `family_id`
- `kind`
- `n_terms`
- `condition_text`
- `coverage_t0_t30`
- `covered_events_t0_t30`
- `uncovered_events_t0_t30`
- `eligible_day_density`
- `eligible_day_trigger_count`
- `eligible_day_denominator`
- `global_eligible_day_denominator`
- `feature_eligible_day_denominator`
- `feature_eligible_day_density`
- `feature_eligible_ratio`
- `low_feature_coverage_warning`
- `median_earliest_hit_offset`
- `median_closest_hit_offset`
- `coverage_by_split_train`
- `coverage_by_split_validation`
- `coverage_by_split_robustness`
- `coverage_by_year_min`
- `coverage_by_year_max`
- `offset_bucket_first_hit_distribution`
- `market_context_decomposition_status`
- `rank_score`

必须保留 uncovered 明细：

`reports/r02_big_winner_coverage_uncovered_events.csv`

必需字段：

- `condition_group_id`
- `winner_event_id`
- `instrument_id`
- `reference_date`
- `split`
- `forward_peak_return`
- `forward_peak_date`
- `missing_reason`

## 14. Required Cache Schemas

### 14.1 Reference Events

`cache/r02_big_winner_reference_events.parquet`

Grain: `winner_event_id`

Required fields:

- `winner_event_id`
- `instrument_id`
- `reference_date`
- `split`
- `winner_label_version`
- `reference_event_source_path`
- `reference_event_source_hash`
- `forward_peak_return`
- `forward_peak_date`
- `profile_window_start`
- `profile_window_end`
- `complete_profile_window_flag`

### 14.2 Winner Profile Panel

`cache/r02_winner_t0_t30_profile_panel.parquet`

Grain: `winner_event_id, profile_trade_date`

Required fields:

- `winner_event_id`
- `instrument_id`
- `reference_date`
- `profile_trade_date`
- `offset_day`
- `split`
- `complete_profile_window_flag`
- `is_r01_pit_executable_eligible`
- OHLCV / amount fields required by the atomic feature bank
- computed atomic feature columns or a deterministic pointer to the feature store
- `feature_complete_flag_by_condition`

### 14.3 Eligible-Day Density Panel

`cache/r02_eligible_day_density_panel.parquet`

Grain: `instrument_id, trade_date`

Required fields:

- `instrument_id`
- `trade_date`
- `split`
- `is_r01_pit_executable_eligible`
- `suspended_or_dirty_bar`
- `entry_execution_status`
- OHLCV / amount fields required by the atomic feature bank
- computed atomic feature columns or a deterministic pointer to the feature store
- `source_price_hash`
- `source_calendar_hash`

## 15. Gates

### 15.1 Hard Gates

候选进入主结果表必须满足：

```text
coverage_t0_t30 >= 0.85
n_terms in [3, 4]
single_family_only = true
all_windows_allowed = true
pit_formula_valid = true
uses_market_context_filter = false
full_sample_descriptive_only = true
parallel_enabled = true
configured_max_workers = 12
deterministic_merge = true
```

任何 hard gate 失败的候选必须进入 rejection artifact，不得进入推荐表。

### 15.2 Reporting Gates

final report 必须明确标记：

- `coverage_ge_85_count`
- `best_condition_by_family`
- `lowest_density_ge85_condition_by_family`
- `overall_lowest_density_ge85_condition`
- `family_without_ge85_condition`
- `high_coverage_high_density_warning`

如果没有任何候选满足 `coverage_t0_t30 >= 0.85`，最终决策必须是：

```text
stop_big_winner_coverage_ratio_search_no_ge85_condition
```

如果至少一个 family 有满足条件的组合，最终决策可以是：

```text
descriptive_coverage_profiles_found
```

但报告必须写明：这只表示存在 full-sample high-recall winner profile，不表示可执行 entry edge，不允许进入下一阶段 promotion，也不构成 holdout validation。

## 16. Required Artifacts

```text
ep4/outputs/r02_big_winner_coverage_ratio_search_v1/
  cache/
    r02_big_winner_reference_events.parquet
    r02_winner_t0_t30_profile_panel.parquet
    r02_eligible_day_density_panel.parquet
  reports/
    r02_big_winner_coverage_atomic_condition_dictionary.csv
    r02_big_winner_coverage_candidate_dictionary.csv
    r02_big_winner_coverage_all.csv
    r02_big_winner_coverage_ge85.csv
    r02_big_winner_coverage_top_by_family.csv
    r02_big_winner_coverage_lowest_density_ge85.csv
    r02_big_winner_coverage_rejected.csv
    r02_big_winner_coverage_uncovered_events.csv
    r02_big_winner_coverage_market_context_decomposition.csv
    r02_big_winner_coverage_validation_audit.csv
    r02_big_winner_coverage_final_report.md
  manifests/
    r02_big_winner_coverage_manifest.json
```

## 17. Final Report Requirements

`reports/r02_big_winner_coverage_final_report.md` 必须包含：

1. 样本与分母说明：845 个 canonical R01 primary big winner，R01 PIT-executable eligible stock-days；
2. 搜索空间说明：7 个技术 family，窗口固定为 `5 / 10 / 30 / 60`，只搜索同 family `AND3 / AND4`；
3. 覆盖率与密度定义；
4. 全局最低密度且 coverage >= 85% 的候选；
5. 每个 family 的最佳候选；
6. 每个 family 的最低密度达标候选；
7. 未覆盖 winner 的明细总结；
8. split / year / market_context 分解；
9. 12-core parallel search 执行摘要：backend、worker count、chunk count、failed / retried chunk count、parallel result hash；
10. 为什么该结果只是 full-sample winner profile / coverage evidence，不是 entry prior，不是 holdout validation；
11. final decision。

## 18. Implementation Readiness Checklist

- [ ] canonical R01 primary big winner denominator count is exactly `845`;
- [ ] coverage denominator and density denominator are separate;
- [ ] profile window is exactly `T+0..T+30`;
- [ ] allowed windows are exactly `5 / 10 / 30 / 60`;
- [ ] atomic condition dictionary is generated before metrics and is the only search-space authority;
- [ ] every atomic condition has formula, threshold, window, family, NaN policy, warmup policy, and formula hash;
- [ ] every main candidate is same-family `AND3` or same-family `AND4`;
- [ ] main search uses `parallel_search.enabled = true` and `max_workers = 12`;
- [ ] parallel merge is deterministic and independent of chunk completion order;
- [ ] manifest records worker count, chunk count, failed chunk count, retried chunk count, and parallel result hash;
- [ ] market_context is only a decomposition / audit dimension and never changes the ge85 main table;
- [ ] density reports both global and feature-eligible denominators;
- [ ] required cache artifacts have the declared row grain and schema;
- [ ] all formulas are PIT on each profile_trade_date / eligible stock-day;
- [ ] ge85 table contains only `coverage_t0_t30 >= 0.85`;
- [ ] final report does not interpret coverage as posterior precision, holdout validation, next-stage promotion, or tradable edge.
