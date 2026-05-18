# EP4 需求 04: Dynamic Momentum Exposure Eligibility Audit V1

## 1. 需求元信息

- 需求 id: `ep4_r04_dynamic_momentum_exposure_eligibility_audit_v1`
- 简称: `r04_dynamic_momentum_exposure_eligibility_audit_v1`
- 状态: 首版可实现的诊断型需求
- 所属 workflow: EP4
- 上游讨论: `ep4/discussion4.md`
- 上游 R02 path-query 需求: `ep4/requirement_02_family_signal_120d_path_query_v1.md`
- 上游 R02 coverage 需求: `ep4/requirement_02_big_winner_coverage_ratio_search_v1.md`
- 上游 R03 系列结论: `ep4/requirement_03a_*` through `ep4/requirement_03e_*`
- 必需输出根目录: `ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/`
- 必需 config 路径: `ep4/configs/r04_dynamic_momentum_exposure_eligibility_audit_v1.yaml`
- 必需 runner 路径: `ep4/scripts/run_r04_dynamic_momentum_exposure_eligibility_audit.py`
- 必需 validator 路径: `ep4/scripts/validate_r04_dynamic_momentum_exposure_eligibility_audit.py`
- 日期: 2026-05-18

## 2. 实验目的

R02/R03 系列已经说明：

```text
single family / same-day bundle / fresh sequence / family order / bad-shape repair
都没有证明稳定的 action-time entry edge。
```

更精确的结论不是 “single family 没有信息”，而是：

```text
单一事件信号作为可复用 entry anchor 的路线失败；
seed-anchor improvement 不能替代 action-time forward edge。
```

R04 v1 不再寻找更复杂的 entry anchor，也不寻找 production gate。R04 v1 只回答一个收窄后的诊断问题：

```text
在冻结的 RPS / momentum candidate pool 上，
market regime 与 industry regime 是否能解释 action-time forward path 的条件差异？
```

R04 v1 必须回答：

1. `single_momentum_rps` episode-first-trigger candidate pool 的 action-time baseline outcome 是什么？
2. 预注册 market regime bucket 是否在 OOS 中稳定区分 path quality？
3. 预注册 industry regime bucket 是否在 RPS + market parent 下提供增量？
4. market-only / industry-only 在 full background stock-day denominator 上是否已经有同等解释力？
5. 表面改善是否只是 denominator shrink、年份集中、行业集中或 split drift？
6. `post_drawdown_rebound` 对 A-share long-only momentum 是风险状态还是机会状态？
7. 如果 RPS + market + industry 没有 OOS 增量，是否应停止 exposure eligibility 路线并转向 hold / exit / risk-budget diagnostics？

本需求是 exposure eligibility audit，不是 entry 策略、不是加仓规则、不是 stop/exit 策略、不是 position sizing 实验。

## 3. R04 Non-Negotiables

### 3.1 Action-Time Anchor

本需求必须固定 action-time anchor：

```text
anchor_signal_date = decision date for the denominator scope
entry_execution_date = next tradable open after anchor_signal_date
entry_price = next-open executable price
forward path = from entry_execution_date
```

所有 feature 必须满足：

```text
feature_asof_date <= anchor_signal_date
```

不得使用 seed-anchor、fresh-anchor、future path、winner label 或 post-signal outcome 来构造 regime bucket。

### 3.2 Anti-Patterns

R04 必须显式禁止：

```text
same-day multi-signal AND as independent evidence
seed-anchor P_good as action-time edge
fresh-count lift as "wait for more signals then buy"
denominator shrink as posterior improvement
exit / trailing-stop improvement as exposure eligibility improvement
validation / robustness outcome based bucket tuning
```

### 3.3 Scope Freeze

R04 v1 只允许三层 exposure eligibility audit：

```text
baseline_A: RPS candidate pool only
baseline_B: RPS + market regime
baseline_C: RPS + market regime + industry regime
```

以下内容不进入 R04 v1 primary gate：

```text
volume_money
stock volatility / ATR gate
price extension gate
volatility risk-budget cap
CTA / trailing exit
family fresh sequence
family order
bad-shape filter
```

这些只能作为后续 R04 v2 / R04b 的候选方向，或作为 descriptive risk note 出现在 final report 中。

## 4. Pre-Registered Spec Sheet

R04 运行前，config 必须冻结一份 spec sheet。runner 必须把该 spec 原样写出到：

```text
reports/r04_spec_sheet_frozen.csv
```

每个 feature / bucket 必须包含：

```text
feature_name
feature_group
feature_formula
feature_asof_rule
lookback_window
required_input_fields
bucket_name
bucket_formula
bucket_cutpoints
bucket_priority_order
bucket_count_cap
missing_value_policy
minimum_train_denominator
minimum_validation_denominator
minimum_robustness_denominator
minimum_background_denominator
primary_metric
secondary_metrics
race_ambiguous_policy
matching_background_comparator
kill_criteria_id
formula_hash
```

runner 和 validator 必须 fail closed：

- spec sheet 缺失；
- feature 或 bucket 没有 formula_hash；
- 实际产物中出现 config/spec 未声明的 bucket；
- bucket cutpoint 与 spec 不一致；
- 使用 outcome 后新增、合并、重命名 bucket；
- 同一个 feature 的 as-of rule 不唯一。

任何跑完 outcome 后新增字段、改断点、合并 bucket 的行为，只能进入下一版 requirement，不能回填当前 R04。

## 5. 必需输入产物

所有输入必须来自本地 artifact，不得在线抓取数据。

### 5.1 RPS Candidate Pool

R04 v1 的 RPS candidate pool 固定为 R02 path-query 的 frozen single-family momentum signal：

```text
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_manifest.json
ep4/outputs/r02_family_signal_120d_path_query_v1/manifests/r02_family_signal_120d_path_query_validation.json
ep4/outputs/r02_family_signal_120d_path_query_v1/reports/episode_signals/single_momentum_rps_120d_episode_audit.csv
ep4/outputs/r02_family_signal_120d_path_query_v1/reports/signals/single_momentum_rps_120d_path.csv
```

不得在 R04 v1 中重新搜索 RPS threshold、改写 RPS condition、加入新的 momentum feature，或从其它 family 借用 trigger。

`single_momentum_rps_120d_episode_audit.csv` 是 primary decision grain 的主输入。R04 v1 的 promotion / kill criteria 只能使用 episode-first-trigger grain。

该 episode audit 至少必须包含：

```text
signal_id
signal_type
family_id
required_family_set
instrument_id
signal_date
split
episode_id
episode_start_signal_date
episode_end_signal_date
episode_trigger_count
episode_entry_date
episode_entry_price
episode_entry_valid
episode_path_quality_flag
entry_date
entry_price
entry_valid
path_complete_120d
first_plus10_hit_flag
first_plus10_offset
first_minus5_hit_flag
first_minus5_offset
race_plus10_minus5_status
hit_plus10_before_minus5
path_quality_flag
early_failure_flag
max_gain_120d
max_drawdown_120d
close_return_t20
close_return_t60
close_return_t120
```

其中 unprefixed path outcome fields 必须是 `episode-first-trigger` grain 的 canonical outcome，不得从 raw repeated-trigger row 重新取值或聚合。若 `episode_*` 字段与 unprefixed 字段同时存在，headline candidate panel 必须使用 episode-first-trigger canonical row，并在 validation audit 中校验二者的 entry anchor 一致性。

`single_momentum_rps_120d_path.csv` 是 raw action-time signal row audit 输入，只能用于：

```text
raw_trigger_count
episode_compression_ratio
raw_vs_episode_outcome_audit
overlap / repeated-trigger audit
```

不得用 raw action-time rows 做 R04 v1 promotion、kill criteria 或 final decision。

### 5.2 PIT Universe / OHLCV

PIT universe 和 OHLCV 使用 R02 coverage 的 eligible day panel：

```text
ep4/outputs/r02_big_winner_coverage_ratio_search_v1/manifests/r02_big_winner_coverage_manifest.json
ep4/outputs/r02_big_winner_coverage_ratio_search_v1/cache/r02_eligible_day_density_panel.parquet
```

该 panel 是 market / industry regime 的主价格输入，至少必须包含：

```text
instrument_id
trade_date
split
is_r01_pit_executable_eligible
suspended_or_dirty_bar
open
high
low
close
volume
money
source_price_hash
source_calendar_hash
```

### 5.3 Calendar / Industry Membership

必须使用本地 PIT calendar 与行业归属：

```text
data/qlib/cn_data_pit/calendars/day.txt
data/targets/pit_industry_membership.csv
```

行业归属口径固定为 `pit_industry_membership.csv` 中的：

```text
date
instrument
industry_target_key
industry_ts_code
industry_name
source
```

R04 v1 禁止使用概念板块、题材板块、事后人工主题分类或任何 future-known group。

行业 membership 必须满足：

```text
membership.date <= anchor_signal_date
```

其中：

```text
RPS episode primary:
  anchor_signal_date = episode_start_signal_date

raw action-time audit:
  anchor_signal_date = signal_date

background action-time:
  anchor_signal_date = background_signal_date / trade_date
```

对每个 `instrument_id x anchor_signal_date`，runner 只能使用 `date <= anchor_signal_date` 的最后一条 membership。找不到 membership 的候选必须进入：

```text
industry_regime_bucket = missing_industry
```

Join key 固定为：

```text
membership.instrument == instrument_id
membership.date <= anchor_signal_date
```

若同一 `instrument x date` 存在多条 membership，runner 不得随机选择。必须按以下确定性顺序排序后保留第一条，并在 membership duplicate audit 中报告重复数量：

```text
sort by instrument, date, source, industry_target_key, industry_ts_code
```

### 5.4 Upstream Validation

runner 必须校验：

```text
r02_family_signal_120d_path_query_validation.json.validation_status == passed
r02 single_momentum_rps episode audit exists and is readable
r02 single_momentum_rps raw signal path exists and is readable
r02_big_winner_coverage_manifest.json exists and is readable
r02_eligible_day_density_panel.parquet exists and is readable
calendar file exists and is readable
pit_industry_membership.csv exists and is readable
```

如果任一必需输入缺失或 validation 未通过，runner 不得生成 headline outcome。最终 decision 必须为：

```text
blocked_missing_required_input
blocked_upstream_validation_failed
```

## 6. Candidate / Background Panel 构造

### 6.1 Primary Grain

R04 v1 primary grain 固定为：

```text
episode-first-trigger grain from single_momentum_rps_120d_episode_audit.csv
```

其中 `signal_id` 必须等于：

```text
single_momentum_rps
```

每一行生成一个稳定 id：

```text
r04_candidate_event_id =
  sha256("r04_episode|" + signal_id + "|" + instrument_id + "|" + episode_id + "|" + episode_start_signal_date)
```

同一 `episode_id` 不得重复。重复 row 必须进入 duplicate audit，primary panel 保留确定性排序后的第一行：

```text
sort by signal_id, instrument_id, episode_start_signal_date, episode_id
```

Raw action-time rows from `single_momentum_rps_120d_path.csv` 必须另建 audit panel，不得混入 primary candidate denominator。

### 6.2 Candidate Inclusion

进入 headline denominator 的 row 必须满足：

```text
episode_entry_valid == true
path_complete_120d == true
split in {train, validation, robustness}
episode_start_signal_date and episode_entry_date remain inside same split
```

不满足的 row 不得静默删除，必须保留在 candidate funnel audit 中，标记：

```text
r04_inclusion_status
r04_exclusion_reason
```

`r04_inclusion_status` allowed values:

```text
included
excluded_invalid_episode_entry
excluded_incomplete_120d_path
excluded_cross_split
excluded_out_of_scope_split
excluded_duplicate_episode
excluded_missing_required_field
```

### 6.3 Path Outcomes

R04 v1 primary metric 使用 path-query 已有字段。

派生字段：

```text
race_ambiguous_flag =
  race_plus10_minus5_status in {same_offset, censored_incomplete}

primary_success_flag =
  true  when race_plus10_minus5_status in {upside_first, upside_only_complete}
  false when race_plus10_minus5_status in {downside_first, downside_only_complete, neither_hit_complete}
  null  when race_plus10_minus5_status in {same_offset, censored_incomplete}

metric_denominator_eligible_flag =
  r04_inclusion_status == included
  AND primary_success_flag is not null

bad_path_flag =
  path_quality_flag in {early_failure, whipsaw_after_profit, severe_drawdown, incomplete}
  OR early_failure_flag == true

good_path_flag =
  path_quality_flag in {clean_continuation, tradable_continuation}

max_gain50_proxy = max_gain_120d >= 0.50
```

`primary_success_flag` 不得独立于 `race_plus10_minus5_status` 重新计算。`same_offset` 不得默认算作 success 或 failure，必须进入 race ambiguity audit。

`max_gain50_proxy` 只是 proxy，不得命名为 canonical big winner。若后续接入 close-anchor big-winner row-level label，可另行输出 `big_winner_status = canonical_available`，但 R04 v1 不依赖它。

### 6.4 Raw Action-Time Audit

Raw action-time audit panel 必须保留所有 `single_momentum_rps_120d_path.csv` rows，并输出：

```text
raw_action_time_event_id =
  sha256("r04_raw|" + signal_id + "|" + instrument_id + "|" + signal_date)
```

```text
raw_signal_row_count
episode_count
episode_compression_ratio
raw_repeated_trigger_count
raw_path_overlap_proxy
raw_primary_metric
episode_primary_metric
raw_vs_episode_metric_delta
```

这些结果只能解释 repeated-trigger bias，不得用于 promotion 或 stopping rule。

### 6.5 Full Market / Industry Background Denominator

R04 v1 必须 materialize 一个 full action-time background denominator，用于真正评估 market-only / industry-only ablation。

Background grain 固定为：

```text
instrument_id x trade_date
```

每一行生成一个稳定 id：

```text
background_event_id =
  sha256("r04_background|" + instrument_id + "|" + background_signal_date)
```

候选 rows 来自 `r02_eligible_day_density_panel.parquet`：

```text
is_r01_pit_executable_eligible == true
suspended_or_dirty_bar == false
close > 0
split in {train, validation, robustness}
```

对每个 background row，runner 必须用同一 trading calendar 找到 next tradable open，并从该 execution anchor 计算 120D path outcome：

```text
background_signal_date = trade_date
background_entry_date = immediate next trading date after trade_date
background_entry_price = open[background_entry_date]
background_path_complete_120d
background_first_plus10_hit_flag
background_first_plus10_offset
background_first_minus5_hit_flag
background_first_minus5_offset
background_race_plus10_minus5_status
background_hit_plus10_before_minus5
background_path_quality_flag
background_early_failure_flag
background_max_gain_120d
background_max_drawdown_120d
background_close_return_t20 / t60 / t120
```

`background_entry_valid = true` 当且仅当：

```text
immediate next trading date row exists for the same instrument_id
background_entry_date remains inside same split as background_signal_date
background entry row is_r01_pit_executable_eligible == true
background entry row suspended_or_dirty_bar == false
background entry row open > 0
```

不得跳过不可执行的 next row 去寻找更晚的 open。若 immediate next trading date row 不可执行、forward path 不完整或跨 split，row 必须保留并标记 incomplete，不得进入 background headline denominator。

`background_inclusion_status` allowed values:

```text
included
excluded_not_pit_executable
excluded_suspended_or_dirty_bar
excluded_nonpositive_close
excluded_out_of_scope_split
excluded_invalid_next_open
excluded_incomplete_120d_path
excluded_cross_split
excluded_missing_required_field
```

Background path label 必须复用 R02 path-query 的同一套算法语义：

```text
same entry anchor rule: next tradable open after signal date
same OHLC trigger semantics: upside uses high, downside uses low
same thresholds: +10 before -5 for primary race
same T+120 comparison horizon
same race status values and null policy
same path_quality_flag classification policy
```

不得为 background denominator 另写一套简化 path label。runner 必须输出 sampled reconciliation audit，抽样校验 background path labeler 与 R02 path-query labeler 的 race-status / offset / path-quality 语义一致。

Reconciliation audit 固定为：

```text
reconciliation_universe =
  rows from single_momentum_rps_120d_path.csv
  with entry_valid == true

sample_key =
  sha256("r04_path_reconcile|" + signal_id + "|" + instrument_id + "|" + signal_date)

sample rows =
  deterministic lowest sample_key rows per split,
  capped by config.validation.path_reconciliation_sample_size_per_split
```

默认 `path_reconciliation_sample_size_per_split = 500`。若某个 split 的 eligible reconciliation rows 少于 500，则使用该 split 全量。

runner 必须用 R04 background path labeler 对 sample rows 重新计算，并与 R02 raw signal path 字段逐项比较：

```text
entry_date
entry_price
path_complete_120d
first_plus10_offset
first_minus5_offset
race_plus10_minus5_status
hit_plus10_before_minus5
path_quality_flag
early_failure_flag
max_gain_120d
max_drawdown_120d
```

Pass criteria:

```text
date / bool / enum / offset fields: exact match
price / return fields: abs(diff) <= 1e-10
total_mismatch_count == 0
```

若 reconciliation audit 不通过，runner 可以写出 diagnostic report，但不得生成 headline outcome。最终 decision 必须为：

```text
blocked_background_path_label_validation_failed
```

Background primary fields 必须按同一 null policy 派生：

```text
background_primary_success_flag =
  true  when background_race_plus10_minus5_status in {upside_first, upside_only_complete}
  false when background_race_plus10_minus5_status in {downside_first, downside_only_complete, neither_hit_complete}
  null  when background_race_plus10_minus5_status in {same_offset, censored_incomplete}

background_metric_denominator_eligible_flag =
  background_inclusion_status == included
  AND background_primary_success_flag is not null
```

Background denominator 不得用于修改 RPS candidate pool；它只回答：

```text
market-only / industry-only states 在完整 eligible stock-day denominator 上是否本身有 edge？
RPS + market / industry 是否超过对应 background state？
```

## 7. Market Regime 构造

### 7.1 Market Proxy

R04 v1 不依赖外部指数。market proxy 从 `r02_eligible_day_density_panel.parquet` 构造：

```text
eligible rows:
  is_r01_pit_executable_eligible == true
  suspended_or_dirty_bar == false
  close > 0

daily instrument return:
  close / prior_close - 1

market_proxy_return:
  equal-weight mean daily return over eligible rows

market_proxy_index:
  cumulative product of 1 + market_proxy_return
```

`prior_close` 规则固定为：

```text
For each instrument_id, sort rows by trade_date using the same trading calendar.
prior_close = close from the immediately previous trading date row for that instrument.
daily instrument return is valid only when:
  current row is eligible and clean
  previous trading date row exists
  previous row suspended_or_dirty_bar == false
  previous close > 0
```

如果 prior row 缺失、dirty、suspended 或 `prior_close <= 0`，该 instrument-day 的 daily return 为 null，不进入当日 equal-weight mean。不得用未来价格、下一条可交易行或跨停牌缺口后的旧 close 填补 prior close。

Market proxy complete day 规则：

```text
market_return_valid_count = count(non-null daily instrument return among eligible clean rows)
market_return_missing_count = eligible_count - market_return_valid_count

market_proxy_return =
  equal-weight mean(valid daily instrument return)
  only if eligible_count >= config.market.min_eligible_count
  AND market_return_valid_count >= config.market.min_return_valid_count
  else null

market_proxy_complete_flag =
  market_proxy_return is not null
```

`market_proxy_index` 必须按 `trade_date` 升序确定性计算：

```text
index_base = 1.0 before the first trade_date
if market_proxy_return[t] is null:
  market_proxy_index[t] = null
else:
  market_proxy_index[t] = last_non_null_market_proxy_index * (1 + market_proxy_return[t])
```

其中 first non-null return 使用 `index_base` 作为 `last_non_null_market_proxy_index`。Incomplete day 不得被当作 0 return。

每日 market proxy 必须同时记录：

```text
market_return_valid_count
market_return_missing_count
market_proxy_complete_flag
```

每日 market proxy 必须记录：

```text
trade_date
split
eligible_count
market_return_valid_count
market_return_missing_count
market_proxy_complete_flag
market_proxy_return
market_proxy_index
source_price_hash_aggregate
source_calendar_hash
```

`source_price_hash_aggregate` 固定为：

```text
source_price_hash_aggregate =
  sha256(concat_with_pipe(sort(unique(source_price_hash from rows used in eligible_count on trade_date))))
```

若同一 `trade_date` 出现多个 `source_calendar_hash`，runner 必须 fail closed，不得任选其一。

如果某日 `eligible_count < config.market.min_eligible_count` 或 `market_return_valid_count < config.market.min_return_valid_count`，该日 market feature 标记为 incomplete。

### 7.2 Market Features

R04 v1 must-have market features：

```text
market_ret_20d
market_ret_60d
market_ret_120d
market_ret_252d
market_drawdown_252d
market_realized_vol_60d
market_breadth_ma60
```

Scope clarification:

```text
R04 v1 bucket 只依赖 60d realized volatility 与 252d drawdown。
discussion4.md 中提到的 market_drawdown_120d、market_realized_vol_20d、
market_realized_vol_126d 不进入 R04 v1 spec sheet，不进入 bucket，
也不进入 promotion / kill criteria；它们保留给 R04 v2 作为 diagnostic candidates。
```

定义：

```text
market_ret_Nd = product(1 + market_proxy_return over last N trading dates ending t) - 1
market_drawdown_252d = 1 - market_proxy_index[t] / rolling_max_252d(market_proxy_index)
market_realized_vol_60d = std(market_proxy_return over last 60 trading dates ending t) * sqrt(252)
market_breadth_ma60 = share of breadth-valid eligible instruments with close > ma60 on trade_date
```

所有 rolling feature 必须使用 `trade_date <= anchor_signal_date` 的历史，并且必须满足窗口完整性：

```text
market_ret_Nd complete only if all N market_proxy_return values are non-null
market_realized_vol_60d complete only if all 60 market_proxy_return values are non-null
market_drawdown_252d complete only if market_proxy_index[t] is non-null
  AND all 252 market_proxy_return values in the trailing 252-date window are non-null
instrument ma60 complete only if all 60 close values in the trailing 60-date window are clean and positive
market_breadth_ma60 denominator = eligible clean instruments with complete ma60 on trade_date
market_breadth_ma60 complete only if denominator >= config.market.min_return_valid_count
market_feature_complete_flag = all must-have market features are non-null
```

### 7.3 Market Bucket

Market bucket 使用固定 priority order。每个 anchor signal date 只能落入一个 `market_regime_bucket`：

```text
1. post_drawdown_rebound_hypothesis:
   market_ret_60d <= -0.10
   AND market_ret_20d >= 0.05
   AND market_realized_vol_60d >= train_q67_market_realized_vol_60d

2. panic_high_vol:
   market_drawdown_252d >= 0.25
   AND market_realized_vol_60d >= train_q67_market_realized_vol_60d
   AND NOT post_drawdown_rebound_hypothesis

3. normal_uptrend:
   market_ret_120d >= 0
   AND market_drawdown_252d < 0.10

4. normal_range:
   market_ret_120d >= -0.05
   AND market_drawdown_252d < 0.25

5. downtrend_low_breadth:
   all remaining complete rows

6. missing_market_regime:
   incomplete market feature rows
```

`train_q67_market_realized_vol_60d` 必须由 train split 的 market feature rows 在 outcome 计算前冻结，并写入 spec sheet。

重要解释约束：

```text
post_drawdown_rebound_hypothesis 不能预设为降权状态。
```

它必须作为待验证 bucket 单独报告。只有 validation / robustness 同时显示 primary metric 恶化，后续版本才允许考虑降权或 block。

## 8. Industry Regime 构造

### 8.1 Industry Universe

对每个 `trade_date x industry_target_key`，使用当日可执行 eligible rows 构造 industry proxy：

```text
eligible rows:
  is_r01_pit_executable_eligible == true
  suspended_or_dirty_bar == false
  close > 0
  industry membership as of trade_date exists
```

Industry member daily return 使用与 market proxy 完全相同的 `prior_close` 规则：只能使用同一 instrument 在上一交易日 row 的 clean positive close，缺失或 dirty/suspended 则该 member-day return 为 null，不得 forward-fill 或跨停牌缺口填补。

Industry proxy complete day 规则：

```text
industry_return_valid_count = count(non-null member daily return)
industry_return_missing_count = industry_member_count - industry_return_valid_count

industry_proxy_return =
  equal-weight mean(valid member daily return)
  only if industry_member_count >= config.industry.min_member_count
  AND industry_return_valid_count >= config.industry.min_return_valid_count
  else null

industry_proxy_complete_flag =
  industry_proxy_return is not null
```

`industry_proxy_index` 使用与 market proxy 相同的 index rule：按 `trade_date` 升序，只在 `industry_proxy_return` 非 null 时更新，incomplete day 的 index 为 null，不得当作 0 return。

每日 industry 必须满足：

```text
industry_member_count >= config.industry.min_member_count
industry_return_valid_count >= config.industry.min_return_valid_count
```

不足的 industry-date 标记为 `thin_industry`.

### 8.2 Industry Features

R04 v1 must-have industry features：

```text
industry_ret_20d
industry_ret_60d
industry_rps_60d
industry_breadth_ma60
stock_ret_60d
stock_rps_60d
stock_rps_minus_industry_rps_60d
```

定义：

```text
industry_proxy_return = equal-weight mean daily return of eligible industry members
industry_proxy_index = cumulative product of 1 + industry_proxy_return on complete days
industry_ret_Nd = product(1 + industry_proxy_return over last N trading dates ending t) - 1
industry_rps_60d = percentile_rank(industry_ret_60d across complete industries on trade_date)
industry_breadth_ma60 = share of breadth-valid industry eligible members with close > ma60
stock_ret_60d = close[t] / close[t-60] - 1
stock_rps_60d = percentile_rank(stock_ret_60d across all eligible instruments with valid stock_ret_60d on trade_date)
stock_rps_minus_industry_rps_60d = stock_rps_60d - industry_rps_60d
```

Window completeness and rank rules:

```text
industry_ret_Nd complete only if all N industry_proxy_return values are non-null
industry_rps_60d universe = industries with complete industry_ret_60d and not thin_industry on trade_date
industry_breadth_ma60 denominator = industry eligible members with complete 60-date clean positive ma60
industry_breadth_ma60 complete only if denominator >= config.industry.min_return_valid_count

stock_ret_60d uses exact 60 trading-date offset from the same calendar:
  current instrument row at t exists, is eligible/clean, close > 0
  lag instrument row at t-60 exists, suspended_or_dirty_bar == false, close > 0
  no forward-fill and no next-clean-row substitution

stock_rps_60d universe =
  all instruments with current row eligible/clean and valid stock_ret_60d on trade_date

percentile_rank formula for industry_rps_60d and stock_rps_60d:
  sort ascending by return
  ties use average rank
  percentile = (average_rank - 1) / (valid_count - 1)
  if valid_count < 2, percentile is null and feature is incomplete
```

All features must be as-of `anchor_signal_date`.

### 8.3 Industry Bucket

每个 candidate row 派生一个 `industry_regime_bucket`：

```text
industry_leading:
  industry_rps_60d >= 0.70
  AND industry_breadth_ma60 >= 0.60

industry_rebound_from_drawdown:
  industry_ret_60d < 0
  AND industry_ret_20d >= 0.05

industry_lagging:
  industry_rps_60d <= 0.30
  OR industry_breadth_ma60 <= 0.40

industry_neutral:
  complete rows not matched above

missing_industry:
  missing membership or incomplete industry feature

thin_industry:
  industry_member_count below threshold
```

Priority order:

```text
missing_industry
thin_industry
industry_rebound_from_drawdown
industry_leading
industry_lagging
industry_neutral
```

`industry_rebound_from_drawdown` 与 market rebound 一样，只是待验证状态，不得预设为正向或负向 gate。

## 9. Baseline 与 Ablation

### 9.1 Nested Baselines

R04 v1 headline nested baselines：

```text
baseline_A_rps_only:
  all included single_momentum_rps episode-first-trigger rows

baseline_B_market_bucket:
  baseline_A rows grouped by market_regime_bucket

baseline_C_market_industry_bucket:
  baseline_A rows grouped by market_regime_bucket x industry_regime_bucket
```

R04 v1 不允许用 train outcome 选择 market bucket 或 industry bucket 后再在 validation / robustness 中汇报 promoted gate。所有 bucket 都是 pre-registered diagnostic bucket。

### 9.2 Pre-Registered Candidate Masks

为了评估 “eligibility” 是否可能存在，runner 可以输出下列 pre-registered masks，但不得把它们称为 production rule：

```text
mask_A_all_rps:
  all included rows

mask_B_market_non_missing:
  market_regime_bucket != missing_market_regime

mask_B_market_constructive_no_default_rebound_penalty:
  market_regime_bucket in {
    normal_uptrend,
    normal_range,
    post_drawdown_rebound_hypothesis
  }

mask_C_industry_leadership:
  mask_B_market_constructive_no_default_rebound_penalty
  AND industry_regime_bucket in {
    industry_leading,
    industry_rebound_from_drawdown
  }
```

`post_drawdown_rebound_hypothesis` 和 `industry_rebound_from_drawdown` 被包含在 constructive mask 中只是为了避免默认惩罚 rebound。它们必须另行单 bucket 报告。如果 OOS 显示 rebound bucket 恶化，后续版本才允许修改 mask。

### 9.3 Negative Ablation

R04 v1 必须输出：

```text
full_background_component:
  full eligible stock-day background
  background + market bucket
  background + industry bucket
  background + market x industry bucket

rps_component:
  RPS episode only
  RPS + market bucket
  RPS + industry bucket
  RPS + market x industry bucket

leave_one_out:
  RPS + market + industry
  RPS + industry only
  RPS + market only
```

输出必须回答：

```text
market regime 是否真的有增量？
industry regime 是否只是 RPS 或 market 的代理？
market-only / industry-only 在完整 background denominator 上是否已经解释大部分效果？
baseline_C 的 lift 是否来自 denominator shrink？
```

### 9.4 Matching Background Comparator

任何 `RPS + regime` 的解释都必须与 matching background comparator 比较，避免把市场/行业本身的状态收益误读为 RPS 增量。

Comparator 固定为：

```text
same split
same denominator status: headline background rows only
same metric null policy
same active regime dimensions
```

Active regime dimensions 定义：

```text
market-only comparator:
  cell = market_regime_bucket

industry-only comparator:
  cell = industry_regime_bucket

market x industry comparator:
  cell = market_regime_bucket x industry_regime_bucket
```

对单一 bucket 或单一 cell：

```text
matching_background_rate =
  plus10_before_minus5_rate of background_action_time rows
  in the same split and same regime cell
```

对包含多个 regime cell 的 mask，例如 `mask_C_industry_leadership`：

```text
1. compute RPS mask cell weights by split:
   weight(cell) = RPS rows in cell / RPS rows in mask

2. compute background cell rates on background_action_time rows

3. matching_background_rate =
   sum(weight(cell) * background_rate(cell))
```

不得使用 global background average 替代 matching background comparator。若任一参与比较的 background cell 低于 `minimum_background_denominator`，该 comparator 必须标记：

```text
matching_background_status = insufficient_background_denominator
```

`matching_background_status` allowed values:

```text
sufficient
insufficient_background_denominator
missing_background_cell
invalid_comparator
no_rps_cell_weight
```

Definitions:

```text
sufficient:
  every participating background cell exists and meets minimum_background_denominator

missing_background_cell:
  at least one RPS-weighted cell has no background rows

insufficient_background_denominator:
  at least one RPS-weighted cell exists but has denominator < minimum_background_denominator

no_rps_cell_weight:
  RPS mask has zero metric-denominator rows after null policy

invalid_comparator:
  cell weights are null, do not sum to 1.0 within tolerance 1e-12, or use undeclared buckets
```

该状态下对应 RPS mask / bucket 只能 descriptive，不得触发 `proceed_to_r04_v2_volume_volatility_spec_only`。

## 10. Metrics

### 10.1 Primary Metric

R04 v1 明确不使用 EV_R。EV_R 输入、1R sizing、risk-budget mapping 均不在本需求范围内。

Primary metric 固定为 probability-only path metric：

```text
plus10_before_minus5_rate = mean(primary_success_flag over metric-denominator rows)
```

在不同 denominator scope 下使用对应字段：

```text
rps_episode_primary:
  primary_success_flag derived from race_plus10_minus5_status

background_action_time:
  background_primary_success_flag derived from background_race_plus10_minus5_status
```

Metric-denominator rows 必须满足：

```text
primary_success_flag is not null
```

`same_offset` 和 `censored_incomplete` 不得静默丢弃，必须单独报告：

```text
path_complete_denominator
metric_denominator
race_ambiguous_count
race_ambiguous_rate
```

Primary metric 必须同时报告：

```text
path_complete_denominator
metric_denominator
success_count
plus10_before_minus5_rate
Wilson / Jeffreys interval lower and upper
lift_vs_parent
matching_background_rate
lift_vs_matching_background
matching_background_status
```

如果某个实现发现 EV_R 输入已经存在，也不得在 R04 v1 中把 EV_R 作为 primary metric；只能在 final report 中标记：

```text
ev_r_status = out_of_scope_for_r04_v1
```

每个 split x bucket x mask 必须输出 denominator sufficiency：

```text
denominator_sufficiency_status =
  sufficient
  insufficient_rps_denominator
  insufficient_background_denominator
  insufficient_both
```

低于 spec sheet 中 `minimum_train_denominator` / `minimum_validation_denominator` / `minimum_robustness_denominator` / `minimum_background_denominator` 的 cell 或 mask 只能作为 descriptive evidence，不得触发 proceed decision。

### 10.2 Hard Constraints

任何 candidate mask 或 bucket 不得只因 primary metric 上升就被解释为改善。必须同时满足并报告：

```text
P_bad must not increase vs parent
max_gain50_proxy_retention must not fall below configured floor
denominator shrink must be reported
denominator sufficiency must be satisfied in validation and robustness
race_ambiguous_rate must not exceed configured ceiling
OOS direction must be consistent in validation and robustness
RPS + regime lift must exceed matching background comparator
```

默认讨论阈值应在 config 中冻结。建议初始值：

```yaml
minimum_oos_primary_lift: 0.02
max_allowed_p_bad_increase: 0.00
min_max_gain50_proxy_retention: 0.70
max_denominator_shrink_vs_parent: 0.70
minimum_train_denominator: 200
minimum_validation_denominator: 100
minimum_robustness_denominator: 100
minimum_background_denominator: 500
max_race_ambiguous_rate: 0.02
market:
  min_eligible_count: 1000
  min_return_valid_count: 800
industry:
  min_member_count: 10
  min_return_valid_count: 8
validation:
  path_reconciliation_sample_size_per_split: 500
r04b:
  min_mask_A_oos_max_gain50_proxy_rate: 0.05
  min_mask_A_oos_max_gain_120d_p90: 0.30
```

这些阈值只是首版建议，最终 authority 是 config/spec sheet。

### 10.3 Secondary Metrics

必须输出：

```text
good_path_rate
bad_path_rate
early_failure_rate
first_minus5_hit_rate
first_plus10_hit_rate
max_gain_120d_p50 / p75 / p90
max_drawdown_120d_p50 / p75 / p90
close_return_t20_p50
close_return_t60_p50
close_return_t120_p50
max_gain50_proxy_rate
max_gain50_proxy_retention_vs_parent
```

`max_gain50_proxy` 不得替代 canonical big winner label。final report 必须清楚标记：

```text
big_winner_status = proxy_only
```

除非后续 row-level canonical label 输入被明确接入并通过 validator。

## 11. Split / Stability / Concentration

所有 headline table 必须按下列 split 输出：

```text
train
validation
robustness
all
```

`all` 只能描述，不得用于 promotion 或 decision。

每个 baseline / bucket / mask 必须输出：

```text
year
market_regime_bucket
industry_regime_bucket
industry_target_key
instrument_id concentration
```

必须有 concentration audit：

```text
top1_year_share
top1_industry_share
top1_instrument_share
top5_instrument_share
```

若任一 OOS lift 由单一年份或单一行业主导，必须标记：

```text
concentration_warning = true
```

默认警戒线：

```yaml
max_top1_year_share_of_lift: 0.50
max_top1_industry_share_of_lift: 0.35
max_top1_instrument_share: 0.05
max_top5_instrument_share: 0.15
```

## 12. Stopping Rule

R04 v1 必须输出 kill criteria audit。

Final decision precedence 固定为：

```text
1. blocked_* decisions override all outcome-based decisions.
2. If matching_background_status == invalid_comparator:
     blocked_matching_background_comparator_invalid
3. If denominator_sufficiency_status != sufficient or
   matching_background_status in {insufficient_background_denominator, missing_background_cell, no_rps_cell_weight}:
     r04_v1_exposure_eligibility_audit_complete_descriptive_only
4. If baseline_C / mask_C passes all hard constraints in validation and robustness:
     proceed_to_r04_v2_volume_volatility_spec_only
5. Else if exposure eligibility fails and mask_A_all_rps has persistent upside:
     proceed_to_r04b_hold_exit_only
6. Else if exposure eligibility fails without persistent upside:
     stop_exposure_eligibility_route_no_oos_lift
```

Persistent upside for `proceed_to_r04b_hold_exit_only` 必须量化：

```text
mask_A_all_rps in both validation and robustness satisfies at least one:
  max_gain50_proxy_rate >= config.r04b.min_mask_A_oos_max_gain50_proxy_rate
  OR max_gain_120d_p90 >= config.r04b.min_mask_A_oos_max_gain_120d_p90
```

不得用主观图表解释替代该条件。

建议决策逻辑：

```text
If mask_C_industry_leadership vs mask_A_all_rps:
  validation and robustness primary_metric lift < minimum_oos_primary_lift
  OR P_bad increases in either OOS split beyond max_allowed_p_bad_increase
  OR max_gain50_proxy_retention < min_max_gain50_proxy_retention
  OR denominator shrink > max_denominator_shrink_vs_parent
  OR race_ambiguous_rate > max_race_ambiguous_rate
  OR mask_C primary_metric does not exceed matching background comparator
  OR lift is concentration-dominated

then final_decision:
  apply final decision precedence above:
    proceed_to_r04b_hold_exit_only if persistent upside is true
    otherwise stop_exposure_eligibility_route_no_oos_lift
```

如果 baseline_C / mask_C 在 validation 和 robustness 中方向一致，并且通过 hard constraints：

```text
proceed_to_r04_v2_volume_volatility_spec_only
```

注意：该 decision 只允许进入 R04 v2 requirement drafting，不允许直接上线、不允许 production sizing、不允许 CTA exit 混入当前结论。

如果 R04 v1 失败但 `mask_A_all_rps` 满足上文 persistent upside 条件：

```text
proceed_to_r04b_hold_exit_only
```

## 13. 输出目录结构

runner 必须写出：

```text
ep4/outputs/r04_dynamic_momentum_exposure_eligibility_audit_v1/
  cache/
    r04_rps_candidate_action_panel.parquet
    r04_raw_action_time_audit_panel.parquet
    r04_background_action_time_panel.parquet
    r04_market_regime_panel.parquet
    r04_industry_regime_panel.parquet
    r04_candidate_regime_join_panel.parquet
    r04_ablation_membership_panel.parquet
  reports/
    r04_input_readiness_audit.csv
    r04_spec_sheet_frozen.csv
    r04_feature_dictionary.csv
    r04_candidate_funnel_audit.csv
    r04_raw_vs_episode_audit.csv
    r04_background_denominator_audit.csv
    r04_background_path_label_reconciliation_audit.csv
    r04_industry_membership_join_audit.csv
    r04_market_regime_bucket_summary.csv
    r04_industry_regime_bucket_summary.csv
    r04_post_drawdown_rebound_audit.csv
    r04_nested_baseline_ablation_summary.csv
    r04_negative_ablation_summary.csv
    r04_matching_background_comparator_audit.csv
    r04_outcome_hierarchy_summary.csv
    r04_denominator_shrink_audit.csv
    r04_denominator_sufficiency_audit.csv
    r04_race_ambiguity_audit.csv
    r04_split_stability_audit.csv
    r04_year_industry_concentration_audit.csv
    r04_kill_criteria_audit.csv
    r04_dynamic_momentum_exposure_eligibility_final_report.md
    r04_dynamic_momentum_exposure_eligibility_validation_audit.csv
  manifests/
    r04_dynamic_momentum_exposure_eligibility_manifest.json
    r04_dynamic_momentum_exposure_eligibility_validation.json
```

## 14. Required Cache Schemas

### 14.1 `r04_rps_candidate_action_panel.parquet`

Required columns:

```text
r04_candidate_event_id
signal_id
family_id
episode_id
instrument_id
signal_date
anchor_signal_date
episode_start_signal_date
episode_end_signal_date
episode_trigger_count
split
entry_execution_date
entry_price
episode_entry_valid
path_complete_120d
r04_inclusion_status
r04_exclusion_reason
first_plus10_hit_flag
first_plus10_offset
first_minus5_hit_flag
first_minus5_offset
race_plus10_minus5_status
hit_plus10_before_minus5
primary_success_flag
race_ambiguous_flag
metric_denominator_eligible_flag
path_quality_flag
good_path_flag
bad_path_flag
early_failure_flag
max_gain_120d
max_drawdown_120d
close_return_t20
close_return_t60
close_return_t120
max_gain50_proxy
source_signal_path
source_episode_audit_path
source_signal_hash
```

### 14.2 `r04_raw_action_time_audit_panel.parquet`

Required columns:

```text
raw_action_time_event_id
signal_id
family_id
instrument_id
signal_date
split
entry_date
entry_price
entry_valid
path_complete_120d
episode_id
episode_start_signal_date
episode_trigger_count
raw_is_episode_first_trigger
first_plus10_hit_flag
first_plus10_offset
first_minus5_hit_flag
first_minus5_offset
race_plus10_minus5_status
hit_plus10_before_minus5
path_quality_flag
early_failure_flag
max_gain_120d
max_drawdown_120d
source_signal_path
source_signal_hash
```

### 14.3 `r04_background_action_time_panel.parquet`

Required columns:

```text
background_event_id
instrument_id
background_signal_date
anchor_signal_date
split
is_r01_pit_executable_eligible
suspended_or_dirty_bar
background_entry_date
background_entry_price
background_entry_valid
background_path_complete_120d
background_inclusion_status
background_exclusion_reason
background_first_plus10_hit_flag
background_first_plus10_offset
background_first_minus5_hit_flag
background_first_minus5_offset
background_race_plus10_minus5_status
background_hit_plus10_before_minus5
background_primary_success_flag
background_race_ambiguous_flag
background_metric_denominator_eligible_flag
background_path_quality_flag
background_good_path_flag
background_bad_path_flag
background_early_failure_flag
background_max_gain_120d
background_max_drawdown_120d
background_close_return_t20
background_close_return_t60
background_close_return_t120
background_max_gain50_proxy
source_price_hash
source_calendar_hash
```

### 14.4 `r04_market_regime_panel.parquet`

Required columns:

```text
trade_date
split
eligible_count
market_return_valid_count
market_return_missing_count
market_proxy_complete_flag
market_proxy_return
market_proxy_index
market_ret_20d
market_ret_60d
market_ret_120d
market_ret_252d
market_drawdown_252d
market_realized_vol_60d
market_breadth_ma60
train_q67_market_realized_vol_60d
market_regime_bucket
market_feature_complete_flag
market_feature_incomplete_reason
source_price_hash_aggregate
source_calendar_hash
```

### 14.5 `r04_industry_regime_panel.parquet`

Required columns:

```text
trade_date
industry_target_key
industry_ts_code
industry_name
industry_member_count
industry_return_valid_count
industry_return_missing_count
industry_proxy_complete_flag
industry_proxy_return
industry_proxy_index
industry_ret_20d
industry_ret_60d
industry_rps_60d
industry_breadth_ma60
industry_regime_bucket
industry_feature_complete_flag
industry_feature_incomplete_reason
industry_membership_source
```

### 14.6 `r04_candidate_regime_join_panel.parquet`

Required columns:

```text
r04_candidate_event_id
background_event_id
raw_action_time_event_id
denominator_scope
episode_id
instrument_id
signal_date
background_signal_date
anchor_signal_date
split
market_regime_bucket
industry_target_key
industry_regime_bucket
stock_ret_60d
stock_rps_60d
stock_rps_minus_industry_rps_60d
market_feature_complete_flag
industry_feature_complete_flag
primary_success_flag
race_ambiguous_flag
metric_denominator_eligible_flag
good_path_flag
bad_path_flag
early_failure_flag
max_gain50_proxy
matching_background_rate
matching_background_denominator
matching_background_status
```

`denominator_scope` allowed values:

```text
rps_episode_primary
background_action_time
raw_action_time_audit
```

Mixed-scope id/date semantics:

```text
rps_episode_primary:
  r04_candidate_event_id populated
  background_event_id = null
  raw_action_time_event_id = null
  signal_date = episode_start_signal_date
  background_signal_date = null
  anchor_signal_date = episode_start_signal_date

background_action_time:
  r04_candidate_event_id = null
  background_event_id populated
  raw_action_time_event_id = null
  signal_date = background_signal_date
  background_signal_date populated
  anchor_signal_date = background_signal_date

raw_action_time_audit:
  r04_candidate_event_id = null
  background_event_id = null
  raw_action_time_event_id populated
  signal_date = raw signal_date
  background_signal_date = null
  anchor_signal_date = raw signal_date
```

### 14.7 `r04_ablation_membership_panel.parquet`

Required columns:

```text
r04_candidate_event_id
background_event_id
raw_action_time_event_id
denominator_scope
ablation_id
ablation_type
parent_ablation_id
included_flag
inclusion_reason
exclusion_reason
market_regime_bucket
industry_regime_bucket
split
primary_success_flag
metric_denominator_eligible_flag
bad_path_flag
max_gain50_proxy
denominator_sufficiency_status
matching_background_status
```

## 15. Report Requirements

### 15.1 Final Report

`r04_dynamic_momentum_exposure_eligibility_final_report.md` 必须包含：

1. final decision；
2. R04 v1 scope：RPS + market + industry only；
3. 为什么 R04 不是 entry signal search；
4. R03 anti-pattern 复述；
5. spec sheet hash 与 frozen cutpoints；
6. input readiness summary；
7. candidate funnel；
8. raw action-time vs episode-first-trigger audit；
9. full background denominator audit；
10. background path label reconciliation audit；
11. industry membership join audit；
12. baseline_A/B/C headline；
13. market bucket summary，尤其 `post_drawdown_rebound_hypothesis`；
14. industry bucket summary；
15. nested ablation 与 negative ablation；
16. matching background comparator audit；
17. primary metric 与 hard constraints；
18. denominator shrink / sufficiency audit；
19. race ambiguity audit；
20. split stability；
21. year / industry / instrument concentration；
22. kill criteria audit；
23. 是否允许进入 R04 v2 spec drafting；
24. `ev_r_status = out_of_scope_for_r04_v1`；
25. 明确声明不得输出 production gate、position size、CTA exit rule。

### 15.2 Validation Audit

Validator 必须输出 `r04_dynamic_momentum_exposure_eligibility_validation_audit.csv`，至少包含：

```text
check_name
status
severity
details
artifact_path
```

## 16. Validator Requirements

Validator 必须检查：

1. 所有 required files 存在；
2. upstream validation passed；
3. 所有 required input columns 存在；
4. spec sheet 存在且 formula_hash 非空；
5. 所有实际 bucket 都在 spec 中声明；
6. `single_momentum_rps` 是唯一 primary candidate signal；
7. primary RPS candidate grain 为 `episode_id`，且无重复；
8. raw action-time rows 只出现在 audit panel，不进入 promotion / kill criteria；
9. full background action-time denominator exists and has path-complete headline denominator；
10. background path label 使用 R02 path-query 的 race-status / censoring / path-quality 语义；
11. background path reconciliation audit 按固定 sample 规则执行且 `total_mismatch_count == 0`；
12. `background_event_id` 与 `raw_action_time_event_id` 按固定 hash 生成且唯一；
13. RPS headline denominator 只包含 `episode_entry_valid == true` 且 `path_complete_120d == true`；
14. RPS primary outcome 来自 episode-first-trigger canonical fields，不来自 raw repeated-trigger rows；
15. candidate/background inclusion status 只使用 allowed enum；
16. background headline denominator 只包含 next-open executable 且 120D path complete rows；
17. `primary_success_flag` 与 `race_plus10_minus5_status` 机械一致；
18. `same_offset` / `censored_incomplete` 没有被默认算作 success 或 failure；
19. market / industry return 使用 immediate previous trading date clean close，不 forward-fill；
20. market / industry proxy index 和 rolling features 遵守 incomplete-window policy；
21. industry_rps_60d / stock_rps_60d 使用固定 percentile_rank formula；
22. matching background comparator 按 same split + same cell + RPS cell weights 生成；
23. denominator sufficiency status 存在，且 insufficient rows 不触发 proceed decision；
24. market feature 只使用 `trade_date <= anchor_signal_date`；
25. industry membership 使用 `instrument == instrument_id` 且 `date <= anchor_signal_date` 的 latest row；
26. mixed-scope join panel 的 id/date nullability 符合 schema 语义；
27. final decision 遵守 precedence 和 persistent-upside quant rule；
28. concept/theme board 字段未被使用；
29. `post_drawdown_rebound_hypothesis` 单独报告，且没有被默认标记为 bad gate；
30. volume_money / volatility / extension / CTA 不进入 R04 v1 primary ablation；
31. EV_R 未进入 primary metric，且 final report 标记 `ev_r_status = out_of_scope_for_r04_v1`；
32. nested baseline 与 negative ablation 都存在；
33. primary metric 与 hard constraints 都存在；
34. all split 未被用于 promotion decision；
35. kill criteria audit 存在；
36. final decision 属于 allowed values。

Allowed final decisions:

```text
blocked_missing_required_input
blocked_upstream_validation_failed
blocked_spec_sheet_invalid
blocked_background_path_label_validation_failed
blocked_matching_background_comparator_invalid
r04_v1_exposure_eligibility_audit_complete_descriptive_only
stop_exposure_eligibility_route_no_oos_lift
proceed_to_r04_v2_volume_volatility_spec_only
proceed_to_r04b_hold_exit_only
```

## 17. Implementation Readiness Checklist

- [ ] R04 v1 只使用 `single_momentum_rps` candidate pool；
- [ ] primary decision grain is episode-first-trigger；
- [ ] raw action-time rows are audit-only；
- [ ] full market/industry background denominator is materialized；
- [ ] background path labels reuse R02 race-status and path-quality semantics；
- [ ] background path reconciliation has zero mismatches；
- [ ] candidate/background inclusion statuses use fixed enums；
- [ ] matching background comparator is same-split and cell-weighted；
- [ ] race ambiguity is audited and excluded from metric denominator；
- [ ] denominator sufficiency blocks proceed decisions when insufficient；
- [ ] market / industry returns use immediate previous trading date clean close；
- [ ] proxy index and rolling features follow incomplete-window policy；
- [ ] stock / industry percentile ranks use fixed tie-aware formula；
- [ ] no new RPS thresholds are searched；
- [ ] no same-day composite signal is created；
- [ ] market regime bucket cutpoints are frozen before outcome；
- [ ] industry taxonomy is fixed to PIT industry membership；
- [ ] industry membership joins on `instrument == instrument_id` with `date <= anchor_signal_date`；
- [ ] mixed-scope join panel id/date fields follow denominator-scope semantics；
- [ ] final decision follows precedence and persistent-upside quant rule；
- [ ] concept/theme board is excluded；
- [ ] `post_drawdown_rebound_hypothesis` is treated as hypothesis, not default penalty；
- [ ] primary metric is pre-registered；
- [ ] EV_R is out of scope for v1；
- [ ] negative ablation exists；
- [ ] denominator shrink is reported for every mask；
- [ ] denominator sufficiency is reported for every mask；
- [ ] concentration audit exists；
- [ ] kill criteria exists；
- [ ] CTA / trailing exit is excluded from R04 v1；
- [ ] final report states this is not a production gate.
