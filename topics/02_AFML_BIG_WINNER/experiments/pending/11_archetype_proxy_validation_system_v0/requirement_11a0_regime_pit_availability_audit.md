# 需求：11A0 Regime PIT Availability Audit

## 0. 本需求要回答的问题

`11A0` 是 `11_archetype_proxy_validation_system_v0` 的前置审计实验。它只回答一个问题：

> `risk_on` / `risk_off` / `transition` regime 是否在 t0 因果可得，并且稳定到足以支撑后续 11A1 的 regime-sliced readout 或 matched-base diagnostic？

11A0 不验证 proxy payoff，不设计交易策略，不改变 08/09/10 的既有 label、feature、rejector 或 population。

## 1. 实验名称与状态

- experiment_id: `11_archetype_proxy_validation_system_v0`
- primary_run_id: `11A0_regime_pit_availability_audit`
- parent_experiment_id: `10_riskon_layered_rejector_system_v0`
- status: `implemented_and_run`
- expected_entrypoint: `src/run_11a0_regime_pit_availability_audit.py`
- expected_config: `configs/config_11a0_regime_pit_availability_audit.yaml`
- expected_test_file: `tests/test_regime_pit_availability_audit.py`

## 2. 核心原则

### 2.1 regime 的角色

regime 只能作为：

- downstream readout dimension
- matched-base diagnostic axis
- later policy replay 的 context variable

regime 不得在 11A0 中被解释为 buy signal、rejector override signal 或独立 alpha。

### 2.2 PIT 与稳定性分离

11A0 必须分开判断两件事：

1. `pit_availability`: regime 是否在 t0 或 t0 之前可得，且未通过未来 label/path 回填。
2. `real_time_stability`: t0 regime 在后续 5/20 个交易 session 是否频繁翻转。

PIT 可得但高翻转的 regime 仍可用于 readout，但不得作为 hard matched-base axis 或策略条件。

### 2.3 11A0 不做的事

11A0 明确不做以下事项：

- 不计算 winner/payoff/failure advantage。
- 不改变 09A/10A 的 `event_regime_bucket` 或 `episode_regime_bucket`。
- 不重新定义 risk_on/risk_off/transition 的经济含义。
- 不用 future return、MFE、MAE 或 winner label 修正 regime。
- 不把 missing regime 作为第四类 regime。
- 不授权 11A1 使用 regime 作为 hard gate；只输出 usage decision。

## 3. 上游输入

### 3.1 讨论与需求输入

以下文件作为需求来源，不作为可变数据输入：

- `../10_riskon_layered_rejector_system_v0/next_step_discussion.md`
- `requirement_11a1_archetype_proxy_robust_payoff_risk_audit.md`

runner 必须在 `input_artifact_audit.csv` 中记录 path、sha256、mtime。

### 3.2 09A regime PIT audit 与 selected bindings

必需输入：

- `../09_riskon_fastfail_label_feature_uplift/outputs/manifests/09A_fast_fail_label_frontier_manifest.json`
- `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09A_fast_fail_label_frontier/regime_label_pit_audit.csv`
- `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/reports/09A_fast_fail_label_frontier/regime_label_pit_audit.md`
- `../09_riskon_fastfail_label_feature_uplift/outputs/publishable/tables/09A_fast_fail_label_frontier/selected_label_contract.csv`
- `../09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet`

关键字段：

- `event_regime_bucket`
- `episode_regime_bucket`
- `event_split`
- `denominator_id`
- `source_pool_id`
- `canonical_event_id`
- `instrument`
- `event_t0_date`
- `trade_time`

### 3.3 08 regime source artifacts

必需输入：

- `../08_risk_on_transition_recall_exploration_v0/outputs/manifests/run_manifest.json`
- `../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_canonical_events.csv.gz`
- `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/cross_section_feature_panel.parquet`
- `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_capture.parquet`
- `../08_risk_on_transition_recall_exploration_v0/outputs/local_cache/post_replay_event_to_episode_retention_source/post_replay_event_episode_membership.parquet`

可选输入：

- `../08_risk_on_transition_recall_exploration_v0/outputs/publishable/tables/candidate_family_event_instances.csv.gz`

可选输入只用于 event instance-level gating reconciliation；缺失不得触发 `11A0_regime_pit_input_blocked`。
若该可选输入存在，至少需要字段：`event_id`, `instrument`, `event_t0_date`, `event_split`, `event_regime_bucket`, `market_regime_bucket`, `event_regime_gating`, `event_t0_confirmation_time`。

关键字段：

| artifact | required fields |
| --- | --- |
| `candidate_family_canonical_events.csv.gz` | `canonical_event_id`, `instrument`, `event_t0_date`, `event_split`, `event_regime_bucket`, `market_regime_bucket`, `event_regime_gating`, `trade_open_date`, `event_t0_confirmation_time` |
| `cross_section_feature_panel.parquet` | `date`, `instrument`, `market_regime_bucket`, `universe_up_share`, `universe_up_share_z`, `universe_up_share_change_5d`, `evaluated_member_count` |
| `candidate_family_capture.parquet` | `target_episode_id`, `episode_split`, `market_regime_bucket`, `first_event_id`, `first_event_t0_date`, `candidate_scope_id` |
| `post_replay_event_episode_membership.parquet` | `event_id`, `canonical_event_id`, `instrument`, `event_t0_date`, `event_split`, `market_regime_bucket`, `market_regime_bucket_canonical`, `episode_market_regime_bucket`, `target_regime`, `target_episode_id`, `episode_split` |

### 3.4 10A downstream population cross-check

必需输入：

- `../10_riskon_layered_rejector_system_v0/outputs/manifests/10A_density_rule_system_manifest.json`
- `../10_riskon_layered_rejector_system_v0/outputs/local_cache/10A_density_rule_system/post_dedup_event_bindings.parquet`

用途：

- 确认 11A1 主分母 rows 的 regime 是否能由 09A/08 authority source 覆盖。
- 输出 downstream 11A1 regime usage decision。

10A 不是 11A0 的 regime 权威来源；它只是 downstream population coverage check。

关键字段：

- `input_event_key`
- `feature_matrix_join_key`
- `instrument`
- `event_t0_date`
- `split`
- `source_family_id`
- `event_regime_bucket`

### 3.5 PIT universe 与交易日历

必需输入：

- PIT executable universe: `topics/02_AFML_BIG_WINNER/data/processed/universe/pit_largecap_main_chinext_executable_daily.csv`
- qfq primary dir: `topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq`
- qfq fallback dir: `topics/02_AFML_BIG_WINNER/data/interim/qlib_csv/day`

用途：

- 作为 `cross_section_feature_panel.date` 主交易日历的覆盖性 reconciliation。
- 计算 t0 前后的 session offset。
- 验证 `event_t0_date` / `trade_open_date` 是否为可审计交易日。

## 4. Regime 定义与回填合同

### 4.1 allowed buckets

合法 regime bucket 仅为：

- `risk_on`
- `risk_off`
- `transition`

空字符串、`missing`、`unknown`、`nan`、`None` 不得作为 regime bucket。它们必须进入 missing audit。

### 4.2 event regime authority

event-level regime 权威优先级：

1. 08 `candidate_family_canonical_events.event_regime_bucket`
2. 08 `candidate_family_canonical_events.market_regime_bucket`
3. 09A `selected_label_event_bindings.event_regime_bucket`

`event_regime_bucket` 与 `market_regime_bucket` 若同时存在，必须输出 agreement rate；若 agreement rate < 99.5%，最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。

10A `post_dedup_event_bindings.event_regime_bucket` 不得进入 event regime authority，也不得作为 `analysis_event_regime_bucket` 的 fallback。10A 只能用于验证 11A1 主分母是否可由 08/09A 权威来源覆盖。

当前数据中 08 canonical `event_regime_bucket`、`market_regime_bucket` 与按 date 聚合出的 `daily_regime_bucket` 预期几乎完全一致；多层 authority chain 是为了防止未来 source schema 变化，不代表当前 fallbacks 会被频繁使用。

### 4.3 episode regime authority

episode-level regime 只用于 readout，不得覆盖 event-level t0 regime。

episode regime 优先级：

1. 09A `selected_label_event_bindings.episode_regime_bucket`
2. 08 `post_replay_event_episode_membership.episode_market_regime_bucket`
3. 08 `candidate_family_capture.market_regime_bucket`

08 membership 中若同时存在 `market_regime_bucket_episode` 与 `episode_market_regime_bucket`，11A0 只使用 `episode_market_regime_bucket`；`market_regime_bucket_episode` 只允许进入 reconciliation readout，不得作为 authority fallback。

若 episode regime 与 event regime 不一致，runner 必须输出 divergence，不得强行改写其中任一层。

### 4.4 analysis regime

下游 readout 使用：

```text
analysis_event_regime_bucket =
  coalesce_valid(
    08_canonical.event_regime_bucket,
    08_canonical.market_regime_bucket,
    09A.event_regime_bucket
  )
```

episode readout 使用：

```text
analysis_episode_regime_bucket =
  coalesce_valid(
    09A.episode_regime_bucket,
    08_membership.episode_market_regime_bucket,
    08_capture.market_regime_bucket
  )
```

`analysis_regime_bucket_for_11A1` 默认等于 `analysis_event_regime_bucket`。`analysis_episode_regime_bucket` 只能作为附加 readout，不得作为 11A1 proxy 的主匹配轴，除非 11A0 final status 明确支持。

### 4.5 join contract

11A0 必须以 08 `candidate_family_canonical_events.csv.gz` 为 row-level 主表。所有 join 必须输出 left row count、matched row count、match rate、duplicate key count、conflict count。

#### 4.5.1 08 canonical -> 09A selected bindings

主 join key：

```text
08_canonical.canonical_event_id = 09A.selected_label_event_bindings.canonical_event_id
```

一致性断言：

- `instrument` 相等。
- `event_t0_date` 相等。
- `event_split` 相等。

09A 未覆盖的 08 canonical row 不得被丢弃；只记录为 `09A_binding_missing_for_08_event`。09A 覆盖不足不得自动阻塞 11A0，除非导致 08 权威 event regime 无法构造。

#### 4.5.2 08 canonical -> 08 event-episode membership

主 join key：

```text
08_canonical.canonical_event_id = 08_membership.canonical_event_id
```

一致性断言：

- `instrument` 相等。
- `event_t0_date` 相等。
- `event_split = event_split_canonical` 或 `event_split` 相等。

membership 未覆盖的 canonical event 只影响 episode readout completeness，不得覆盖 event-level t0 regime。

#### 4.5.3 08 membership -> 08 capture

主 join key：

```text
08_membership.target_episode_id = 08_capture.target_episode_id
```

一致性断言：

- `episode_split` 相等。
- 若两侧均提供 `instrument`，则 `instrument` 相等。
- 若两侧均提供 `first_event_t0_date`，则 membership event date 不得晚于 capture episode window 的可解释范围；异常进入 `episode_join_temporal_conflict`。

capture 只提供 episode-level regime readout，不得反向覆盖 event-level t0 regime。

#### 4.5.4 08 canonical -> 10A downstream coverage

10A coverage audit 用于回答：11A1 主分母中的 row 是否能找到 08/09A 权威 event regime。该 join 不得产生新的 regime authority。

10A 必须从 `input_event_key` 和 `feature_matrix_join_key` 中解析候选 canonical id：

```text
split(key, "|")[3]
```

若两者均存在且解析结果不一致，记录 `10A_key_parse_conflict`。若解析失败，记录 `10A_key_parse_failed`，并使最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。

coverage join key：

```text
10A.binding_canonical_event_id_for_audit = 08_canonical.canonical_event_id
10A.instrument = 08_canonical.instrument
10A.event_t0_date = 08_canonical.event_t0_date
10A.split = 08_canonical.event_split
```

输出 `downstream_10a_regime_coverage_audit.csv`，至少包含：

- `ten_a_row_count`
- `ten_a_key_parse_success_rate`
- `ten_a_to_08_match_rate`
- `ten_a_regime_field_agreement_rate_readout_only`
- `authority_regime_coverage_rate_for_11A1`
- `coverage_status`

`ten_a_regime_field_agreement_rate_readout_only` 只用于发现下游转写问题；不得用于修正 `analysis_event_regime_bucket`。

#### 4.5.5 event regime gating diagnostic

08 canonical `event_regime_gating` 必须进入 readout，但不得改变 `analysis_event_regime_bucket`。

runner 必须输出：

- `gated_event_count`
- `gated_event_share`
- `gated_event_share_by_split`
- `gated_event_share_by_analysis_event_regime_bucket`
- `gated_event_vs_ungated_regime_distribution`

若可选 `candidate_family_event_instances.csv.gz` 存在，runner 应按 `event_id` 与 canonical/source event 信息做 instance-level gating reconciliation；若缺失，只记录 `event_instance_gating_reconciliation_skipped`，不得阻塞 11A0。

## 5. PIT 因果可得性审计

### 5.1 source-level PIT audit

必须读取 09A `regime_label_pit_audit.csv`，并逐 split 校验：

- `t0_visible_flag == true`
- `future_join_count == 0`
- `published_reconstructed_consistency >= 0.995`
- `risk_on_reconstructed_not_published_share <= 0.005`
- `published_risk_on_not_reconstructed_share <= 0.005`
- `feature_panel_market_wide_regime_check == pass`

若任一 split 不满足，最终状态不得高于 `11A0_regime_pit_statistics_incomplete`；若 audit 文件缺失或 schema 不完整，则最终状态必须为 `11A0_regime_pit_input_blocked`。

### 5.2 row-level t0 audit

runner 必须以 08 canonical events 为主表，构造 row-level audit：

join keys：

| 左表 | 右表 |
| --- | --- |
| `candidate_family_canonical_events.event_t0_date` | `cross_section_feature_panel.date` |

由于 `cross_section_feature_panel` 是 instrument-level panel，同一 `date` 可能多行。runner 必须按 `date` 聚合出 market-wide regime：

```text
daily_regime_bucket = mode(market_regime_bucket by date)
daily_regime_conflict_rate = rows_not_equal_mode / rows_total
```

若同一日期 `daily_regime_conflict_rate > 0.01`，该日期标记为 `daily_regime_conflict`. 冲突日期不能静默使用。

row-level t0 audit 输出：

- `event_id`
- `canonical_event_id`
- `instrument`
- `event_t0_date`
- `event_split`
- `event_regime_bucket`
- `market_regime_bucket`
- `daily_regime_bucket`
- `daily_regime_conflict_rate`
- `event_vs_daily_regime_match_flag`
- `t0_regime_available_flag`
- `t0_pit_status`

`t0_causality_audit.csv` 还必须输出以下 aggregate readout：

- `event_vs_daily_regime_match_rate = mean(event_vs_daily_regime_match_flag)`
- `t0_regime_available_rate = mean(t0_regime_available_flag)`
- `invalid_or_missing_regime_rate`
- `event_vs_daily_regime_match_rate_by_split`
- `event_vs_daily_regime_match_rate_by_analysis_event_regime_bucket`

### 5.3 confirmation time audit

`event_t0_confirmation_time` 必须为 t0 close 或更早的可审计时点。允许值：

- `t0_close_next_open_executable`
- `t0_close`

任何其他非空值必须输出 `confirmation_time_unrecognized`，并使最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。缺失值必须输出 `confirmation_time_missing`，并使最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。若出现 t0 后才确认的 regime source，必须输出 `confirmation_after_t0`，最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。

## 6. Real-time stability metrics

### 6.1 交易日序列

runner 必须从 `cross_section_feature_panel.date` 构造 primary trading-session calendar，并按 date 排序去重。不得使用 calendar days 代替 trading sessions。

PIT executable universe 与 qfq daily bars 只作为 calendar coverage reconciliation：

- 若 08 canonical `event_t0_date` 不在 primary calendar 中，输出 `event_t0_not_in_primary_calendar`，最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。
- 若 primary calendar 与 PIT/qfq 可审计交易日集合的 mismatch rate > 0.5%，输出 `calendar_reconciliation_failed`，最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。
- 若 mismatch rate <= 0.5%，runner 仍必须在 `regime_daily_series_audit.csv` 中报告差异日期数量与样例。

### 6.2 date-level stability primitives

regime stability 是 market-wide date property，不是 event-density property。runner 必须先在 §6.1 的唯一交易日序列上计算 stability primitives，每个 trading date 只出现一次；不得直接在 08 canonical event rows 上计算 hard gate。

`daily_regime_series.parquet` 必须至少包含：

- `date`
- `date_pos`
- `regime_t0`
- `regime_t_minus_5`
- `regime_t_minus_20`
- `regime_t_plus_5`
- `regime_t_plus_20`
- `date_forward_5d_eligible_flag`
- `date_forward_20d_eligible_flag`
- `date_flip_end_5d_flag = regime_t_plus_5 != regime_t0`
- `date_flip_end_20d_flag = regime_t_plus_20 != regime_t0`
- `date_flip_any_5d_flag = any(regime_t_plus_1 ... regime_t_plus_5 != regime_t0)`
- `date_flip_any_20d_flag = any(regime_t_plus_1 ... regime_t_plus_20 != regime_t0)`
- `date_pre_flip_any_5d_flag = any(regime_t_minus_5 ... regime_t_minus_1 != regime_t0)`
- `date_pre_flip_any_20d_flag = any(regime_t_minus_20 ... regime_t_minus_1 != regime_t0)`

若 t+5/t+20 不足，保留 date row 并标记 `date_forward_stability_horizon_incomplete`，不得从 denominator 中静默丢弃。

### 6.3 event-joined stability readout

完成 date-level primitives 后，runner 必须按 `event_t0_date = daily_regime_series.date` join 回 08 canonical events，生成 event-weighted diagnostic readout。

`real_time_flip_stability.csv` 必须同时输出两套指标：

- `date_level_unweighted_*`: 每个 trading date 权重相同；这是 §8.3 hard stability gate 的唯一依据。
- `event_weighted_*`: 每个 canonical event row 权重相同；只用于显示 event-density 对 readout 的影响，不得作为 hard gate basis。

event-weighted readout 至少按 `split`、`analysis_event_regime_bucket`、`split + analysis_event_regime_bucket` 输出。date-level unweighted readout 至少按 `regime_t0` 输出；若需要 split 视角，只能通过 event join 生成 diagnostic，不得把 split-diagnostic 反推为 calendar stability。

### 6.4 regime age

`regime_age_sessions_t0` 在 date-level series 上定义为：

```text
从 t0 向前数，连续等于 regime_t0 的交易 session 数，包含 t0。
```

最大 cap 为 120 sessions，超过记为 120。

输出 date-level unweighted 与 event-weighted 两套分布：

- p05
- p25
- median
- p75
- p95
- share_age_lt_3
- share_age_lt_5
- share_age_ge_20

§8.3 hard gate 使用 date-level unweighted `median_regime_age_sessions_t0`。

### 6.5 confirmation lag

`confirmation_lag_sessions` 在 date-level series 上定义为：

```text
从 t0 开始向后寻找最小 k >= 0，使得 t+k, t+k+1, t+k+2 连续 3 个 session 均等于 regime_t0。
```

若 20 sessions 内不存在，记为 `-1`，并标记 `confirmation_lag_not_found_20d`.

注意：confirmation lag 是 ex-post stability readout，不是 t0 可用特征。

### 6.6 confidence score

11A0 输出两个分数：

```text
t0_regime_confidence_score = min(regime_age_sessions_t0, 20) / 20
```

该分数只使用 t0 及 t0 以前信息，可用于 downstream readout 分层。

```text
ex_post_regime_stability_score_20d = 1 - (number of t+1..t+20 sessions not equal regime_t0 / available forward sessions)
```

该分数使用 t0 后信息，只能作为稳定性诊断，不得进入 11A1 proxy membership。

两个分数均先在 date-level series 上计算，再 join 回 event rows；event row 上的分数只是该 event_t0_date 的 date-level 分数副本。

## 7. 汇总维度

event-level / downstream population 核心读数至少按以下维度输出：

- `all`
- `split`
- `analysis_event_regime_bucket`
- `split + analysis_event_regime_bucket`
- `source_pool_id`
- `source_family_id` 或 08 `primary_family_id`

date-level unweighted stability 读数至少按以下维度输出：

- `all`
- `regime_t0`

date-level stability 没有天然 `split` 维度；任何 split 视角都必须标记为 event-joined diagnostic。

对 transition 必须单独输出，不得并入 risk_on 或 risk_off。

## 8. Acceptance rules

### 8.1 global input gates

以下任一失败，最终状态必须为 `11A0_regime_pit_input_blocked`：

- 必需输入文件缺失。
- 必需字段缺失。
- 无法构造 daily regime series。
- 08 canonical event rows 为空。
- 09A `regime_label_pit_audit.csv` 缺失或无法读取。

### 8.2 PIT availability gates

以下任一失败，最终状态不得高于 `11A0_regime_pit_statistics_incomplete`：

- `t0_visible_flag != true` 任一 split 出现。
- `future_join_count > 0` 任一 split 出现。
- `published_reconstructed_consistency < 0.995` 任一 split 出现。
- `event_vs_daily_regime_match_rate < 0.995`。
- `t0_regime_available_rate < 0.995`。
- residual invalid/missing regime rate > 0。
- `event_t0_not_in_primary_calendar` 非零。
- `calendar_reconciliation_failed` 非零。
- `confirmation_time_missing` 或 `confirmation_time_unrecognized` 非零。
- `confirmation_after_t0` 非零。

### 8.3 stability usage gates

对 `risk_on` 与 `risk_off` 分别计算 date-level unweighted metrics：

- `date_n`
- `forward_5d_date_eligible_rate`
- `forward_20d_date_eligible_rate`
- `date_flip_end_5d_rate`
- `date_flip_any_5d_rate`
- `date_flip_end_20d_rate`
- `date_flip_any_20d_rate`
- `date_confirmation_lag_not_found_20d_rate`
- `date_median_regime_age_sessions_t0`

`split_regime_sample_power.csv` 必须同时输出三种 `population_scope`：

- `date_level_calendar`: 用于 §8.3 hard stability gate。
- `08_canonical_event_weighted`: 只用于显示 event-density weighting，不得作为 hard gate。
- `10A_post_dedup_downstream`: 用于 §9 downstream 11A1 usage decision 的 slice-power check。

date-level stability gate 先经过 calendar coverage floor：

- `date_n >= 100`
- `forward_20d_date_eligible_rate >= 0.90`

若 risk_on 或 risk_off 未通过 calendar coverage floor，但 PIT availability gates 通过，最终状态不得高于 `11A0_regime_pit_statistics_incomplete`。这代表 regime time-series 覆盖不足，不代表 regime 高翻转。

稳定性 hard usage gate：

- `date_flip_end_5d_rate <= 0.25`
- `date_flip_end_20d_rate <= 0.45`
- `date_confirmation_lag_not_found_20d_rate <= 0.25`
- `date_median_regime_age_sessions_t0 >= 3`

只有 calendar coverage floor 通过的 risk_on/risk_off 才能进入 stability hard usage gate。若 calendar coverage floor 通过但 stability hard usage gate 未通过，最终状态为 `11A0_regime_pit_available_unstable_readout_only`。

transition 不要求通过上述 calendar coverage floor 或 stability gate；transition 默认只能作为 readout/provisional context，除非另一个需求专门定义 transition policy。runner 仍必须输出 transition 的 `date_n`、event-weighted row count、各 split event_n 与 stability readout；若 transition `date_n < 30` 或 downstream event_n < 100，报告中必须明确标注 `transition_underpowered_readout`。

### 8.4 downstream 11A1 slice-power check

11A0 final_status 只证明 regime PIT 可得性与 date-level real-time stability，不证明 11A1 实际 post-dedup slice 有足够样本。runner 必须在 10A downstream population 上另算 slice-power：

- `ten_a_event_n`
- `ten_a_train_event_n`
- `ten_a_validation_event_n`
- `ten_a_robustness_event_n`
- `ten_a_authority_regime_coverage_rate`
- `ten_a_slice_power_flag`

默认 10A slice-power floor：

- `ten_a_event_n >= 500`
- `ten_a_train_event_n >= 100`
- `ten_a_validation_event_n >= 100`
- `ten_a_robustness_event_n >= 100`
- `ten_a_authority_regime_coverage_rate >= 0.995`

若 10A slice-power floor 未通过，不改变 11A0 final_status，但 §9 中 `11A1_matched_base_axis` 的 `usage_scope` 必须降为 `diagnostic_only` 或 `readout_only`，并设置 `11A1_must_recheck_slice_power_flag = true`。11A1 仍必须在自己的最终 modeling denominator 上重新检查 per-slice n。

### 8.5 final status

最终 `acceptance_summary.csv` 必须给出唯一 final_status：

| status | 条件 |
| --- | --- |
| `11A0_regime_pit_available_stable_supported` | global input gates 通过，PIT availability gates 通过，risk_on/risk_off calendar coverage floor 与 date-level stability usage gates 均通过 |
| `11A0_regime_pit_available_unstable_readout_only` | PIT availability gates 通过，risk_on/risk_off calendar coverage floor 通过，但 date-level stability usage gates 未全通过 |
| `11A0_regime_pit_statistics_incomplete` | 输入可读，但 PIT/source/stability 核心审计不完整或触发 statistics ceiling |
| `11A0_regime_pit_input_blocked` | global input gates 失败 |

## 9. Downstream usage decision

必须输出 `downstream_11a1_regime_usage_decision.csv`：

| 字段 | 说明 |
| --- | --- |
| `usage_target` | `11A1_proxy_readout`, `11A1_matched_base_axis`, `11B_retention_readout`, `11C_policy_context` |
| `allowed_flag` | 是否允许使用 |
| `allowed_regime_buckets` | 允许值 |
| `usage_scope` | `primary`, `diagnostic_only`, `readout_only`, `blocked` |
| `stability_gate_basis` | 必须为 `date_level_unweighted`，不得为 event-weighted |
| `ten_a_slice_power_flag` | 10A post-dedup downstream slice 是否满足 §8.4 floor |
| `11A1_must_recheck_slice_power_flag` | 固定为 true；11A1 必须在自身最终分母重检 |
| `reason` | 决策原因 |

默认规则：

- 若 final_status 为 `11A0_regime_pit_available_stable_supported`：11A1 可把 `analysis_event_regime_bucket` 作为 readout dimension；是否进入 primary matched base 仍由 11A1 自身决定。
- 若 final_status 为 `11A0_regime_pit_available_stable_supported` 但 `ten_a_slice_power_flag = false`：`11A1_matched_base_axis` 不得标记为 `primary`，只能是 `diagnostic_only` 或 `readout_only`。
- 若 final_status 为 `11A0_regime_pit_available_stable_supported` 且 `ten_a_slice_power_flag = true`：`11A1_matched_base_axis` 仍只能表示 11A0 允许使用该 axis；11A1 必须在自己的最终 modeling denominator 上重新检查 per-slice n 与 matched-base overlap。
- 若 final_status 为 `11A0_regime_pit_available_unstable_readout_only`：11A1 只能把 regime 作为附加 readout/provisional diagnostic，不得作为 hard matched-base axis。
- 若 final_status 为 `11A0_regime_pit_statistics_incomplete` 或 `11A0_regime_pit_input_blocked`：11A1 不得解释 regime-sliced proxy 差异。

## 10. 输出文件

### 10.1 publishable tables

输出目录：

```text
outputs/publishable/tables/11A0_regime_pit_availability_audit/
```

必须生成：

- `input_artifact_audit.csv`
- `regime_source_contract.csv`
- `regime_daily_series_audit.csv`
- `event_regime_join_coverage.csv`
- `regime_source_reconciliation.csv`
- `event_regime_gating_readout.csv`
- `episode_event_regime_divergence.csv`
- `downstream_10a_regime_coverage_audit.csv`
- `t0_causality_audit.csv`
- `real_time_flip_stability.csv`
- `regime_age_confidence_distribution.csv`
- `split_regime_sample_power.csv`
- `downstream_11a1_regime_usage_decision.csv`
- `acceptance_summary.csv`

### 10.2 local cache

输出目录：

```text
outputs/local_cache/11A0_regime_pit_availability_audit/
```

允许生成：

- `regime_scored_events.parquet`
- `daily_regime_series.parquet`

### 10.3 report 与 manifest

必须生成：

- `outputs/publishable/reports/11A0_regime_pit_availability_audit_report.md`
- `outputs/publishable/manifest_11A0_regime_pit_availability_audit.json`

报告必须包含：

1. 数据来源、hash 与 row count。
2. regime source 权威顺序与 PIT 因果审计结果。
3. daily regime series 的冲突率与覆盖率。
4. event/market/daily regime 的一致性，并说明当前 fallbacks 是否实际被使用。
5. event/episode regime 一致性与 divergence。
6. `event_regime_gating` 的 gated_event_share 与 regime 分布诊断。
7. date-level unweighted `flip_rate_5d/20d`, `confirmation_lag`, `regime_age`, `confidence`，并并列 event-weighted diagnostic。
8. transition 的 readout-only/provisional 说明。
9. 10A post-dedup downstream slice-power 与 11A1 必须重检 per-slice n 的说明。
10. downstream 11A1 usage decision。
11. final_status 与不能越界使用的说明。

## 11. 验证要求

### 11.1 单元测试

`tests/test_regime_pit_availability_audit.py` 至少覆盖：

- allowed buckets 校验，missing 不得变成第四类。
- 10A `event_regime_bucket` 不得进入 event regime authority 或 `analysis_event_regime_bucket` fallback。
- 08 canonical -> 09A selected bindings join key 与一致性断言。
- 08 canonical -> 08 membership -> 08 capture join key 与 duplicate/conflict audit。
- 10A downstream coverage key parse、parse conflict 与 parse failure 状态。
- 10A post-dedup slice-power floor 与 downstream usage decision 降级。
- `event_regime_gating` gated share readout；candidate_family_event_instances 缺失不得 input_blocked。
- primary trading calendar 来自 `cross_section_feature_panel.date`，PIT/qfq 只做 reconciliation。
- `event_t0_confirmation_time` 只允许 `t0_close_next_open_executable` 与 `t0_close`。
- risk_on/risk_off date-level calendar coverage floor 与 insufficient-coverage final status ceiling。
- daily regime series mode 聚合与 conflict rate。
- t0 event regime 与 daily regime reconciliation。
- `event_vs_daily_regime_match_rate` aggregate 计算。
- date-level `regime_age_sessions_t0` 计算，并 join 回 event rows。
- date-level `flip_end_5d`, `flip_any_5d`, `flip_end_20d`, `flip_any_20d` 计算。
- event-weighted flip metrics 与 date-level unweighted metrics 不同且 hard gate 只读 date-level metrics。
- date-level `confirmation_lag_sessions` 计算与 `-1` 状态。
- `t0_regime_confidence_score` 不使用未来数据。
- final status precedence。
- downstream usage decision 映射。

### 11.2 运行验证

实现后至少运行：

```bash
uv run python -m pytest tests/test_regime_pit_availability_audit.py
uv run python src/run_11a0_regime_pit_availability_audit.py --config configs/config_11a0_regime_pit_availability_audit.yaml
```

若项目当前没有 `uv` 环境，允许使用项目既有 Python runner，但必须在 report 中记录实际命令。

### 11.3 artifact validation

runner 完成后必须校验：

- publishable CSV 均非空，除非 final_status 是 `11A0_regime_pit_input_blocked`。
- manifest 中所有 publishable artifact sha256 可复算。
- `acceptance_summary.csv` 只有一个 final_status。
- report 中引用的核心数值能在 CSV 中定位。

## 12. 报告措辞约束

报告不得使用以下措辞：

- “regime 是买入信号”
- “transition 可直接交易”
- “11A0 证明 risk_on/off 有 alpha”
- “regime 可以覆盖 proxy 或 rejector 决策”

允许使用：

- “PIT available”
- “real-time stability”
- “readout-only regime context”
- “diagnostic matched-base axis”
- “provisional transition context”

## 13. 后续依赖

- 11A1 必须读取 11A0 的 `downstream_11a1_regime_usage_decision.csv`。
- 11A1 必须在自己的最终 modeling denominator 上重新检查 regime slice sample power；不得把 11A0 final_status 解释为 11A1 样本量充分。
- 11B 若做 regime-sliced protected retention，必须继承 11A0 的 PIT/stability status。
- 11C 若把 regime 作为 policy context，必须另立 requirement，不得仅凭 11A0 支持策略化。
