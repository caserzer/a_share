# 需求：12A3 Episode Precision / Recall Frontier

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
4. 每个被读取的输入 artifact 必须进入 `input_artifact_audit.csv`，记录 resolved path、row count、sha256、schema status、read status。
5. 必需输入缺失或 schema 不匹配时 fail closed；不得从报告文本、聚合表或未来标签中反推缺失事件。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A3
run_id = 12A3_episode_precision_recall_frontier
status = spec_draft_pending_review
expected_entrypoint = src/run_12a3_episode_precision_recall_frontier.py
expected_config = configs/config_12a3_episode_precision_recall_frontier.yaml
expected_test_file = tests/test_12a3_episode_precision_recall_frontier.py
```

12A3 承接两个已冻结事实：

```text
12A1 decision = 12A1_r_core_recall_benchmark_only
12A2 decision = 12A2_state_change_candidate_generation_supported
```

含义：

```text
R-core 只能作为 recall benchmark / precision-density 对照；
12A2 state-change canonical events 可以进入 episode frontier，
但尚不能被解释为交易 backbone 或 winner/failure morphology backbone。
```

## 2. 背景和研究问题

12A2 已经证明新的 state-change candidate pool 可运行且密度受控：

- primary canonical events: `28,691`
- supported raw instances after family / union / first-trigger filters: `59,881`
- next-open executable supported events: `59,881`
- next-open executable rate: `1.0000`
- all-sample primary density: `7.9204` events / instrument-year
- density vs 08 raw R-core: `0.5988`
- rolling 10d duplicate rate: `0.0725`
- runnable / diagnostic / blocked family count: `7 / 1 / 4`

但 12A2 没有回答 winner episode recall 和 event precision。12A3 只回答一个问题：

```text
与 R-core benchmark 相比，
12A2 state-change backbone 是否在 episode recall 足够可用的前提下，
赢得 event precision、event density、timing quality 和 bad-side exposure？
```

预期解释框架：

```text
R-core 可能继续赢 raw episode recall。
State-change backbone 必须用更高 precision、更低 density、更好的 timing
和更低 fast-fail / false-repair exposure 来证明它值得替代 R-core。
```

## 3. 非目标

12A3 明确不做：

- 不训练 winner / failure / fast-fail / meta-label 模型；
- 不修改 12A2 candidate generation threshold、family formula、canonical priority 的主口径；
- 不把 12A2 raw instances 当作 primary frontier denominator；
- 不使用 episode label、MFE、future return 或 label-derived touch coordinate 生成事件；
- 不做 policy replay、仓位、entry / exit 或交易可用性声明；
- 不进入 winner/failure morphology clustering；
- 不用 validation / robustness 结果回头选择更好看的 family；
- 不把 B7 diagnostic-only family 提升为 primary candidate；
- 不伪造 blocked industry / sector rotation family。

## 4. 必需输入

### 4.1 12A2 state-change candidate 输入

必需输入：

```text
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_generation_decision.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_canonical.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_instances.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_family_formula_spec.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_canonicalization_spec.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_density_audit.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_feature_pit_audit.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_family_overlap_diagnostic.csv
outputs/manifests/12A2_state_change_backbone_candidate_generator_manifest.json
```

12A2 gate：

```text
state_change_generation_decision.decision = 12A2_state_change_candidate_generation_supported
next_allowed_requirement = requirement_12a3_episode_precision_recall_frontier.md
upstream_next_allowed_requirement = stop_no_valid_backbone_for_morphology
handoff_conflict_flag = false
primary_canonical_event_n > 0
next_open_executable_gate_pass = true
density_hygiene_gate_pass = true
forbidden_feature_gate_pass = true
```

`upstream_next_allowed_requirement = stop_no_valid_backbone_for_morphology` 是预期值：它表示停止旧的 winner/failure morphology 路径，不阻断 12A2 replacement backbone diagnostic 进入 12A3 frontier。只有 `handoff_conflict_flag = true` 时才视为 handoff blocker。

`state_change_candidate_event_canonical.csv.gz` 必需字段：

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
candidate_generation_status
```

Primary frontier 只使用：

```text
candidate_generation_status = supported_canonical_event
non_executable_next_open = false
event_t0_pit_status = pass
trade_open_pit_status = pass
```

`state_change_candidate_event_instances.csv.gz` 只用于 priority sensitivity 和 family-only diagnostics，不得替代 primary canonical union。

### 4.2 12A0 / 12A1 target 和 R-core benchmark 输入

必需输入：

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/episode_target_registry_06_risk_on_428.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_demote_or_keep_decision.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_arm_event_registry.csv.gz
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_episode_alignment_by_window.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_event_precision_by_window.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_density_badside_tradeoff.csv
outputs/manifests/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit_manifest.json
```

Episode target gate：

```text
record_unit = deduped_big_winner_episode
selection_rule = market_regime_bucket == risk_on
expected_row_n = 428
primary_key = episode_id
lineage_status = frozen_06_risk_on_episode
```

`episode_target_registry_06_risk_on_428.csv` 必需字段：

```text
episode_id
instrument
episode_low_date
episode_high_date
first_50pct_date
pre120_calendar_start_date
low_to_high_sessions
mfe_120
split
duration_bucket
board_bucket
cluster_union_start_date
cluster_union_end_date
```

R-core benchmark gate：

```text
r_core_demote_or_keep_decision.decision = 12A1_r_core_recall_benchmark_only
population_bridge_status = pass
primary_benchmark_arm_id = 08_R_core_event_regime_gated_raw
secondary_reference_arm_id = 08_R6_event_regime_gated_raw
```

`08_R_core_event_regime_gated_raw` 是 12A3 的主 benchmark。`08_R6_event_regime_gated_raw` 可以作为较低密度参考，但不得替代 R-core benchmark 参与最终支持判定。

Density denominator source：

```text
density_basis_id = 08_full_evaluated_universe_years_252
authoritative_source =
  outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/r_core_density_badside_tradeoff.csv
required field = denominator_instrument_years
```

12A3 的 `events_per_instrument_year_*` 与 `density_ratio_vs_r_core` 必须从该 denominator 复算，并把该 artifact 写入 `input_artifact_audit.csv`。

### 4.3 价格、PIT 执行和 label recomputation 输入

12A3 必须能对 12A2 新事件重算 bad-side / winner readout labels，因为这些事件不是 09A selected label binding 的既有分母。

必需输入：

```text
topics/02_AFML_BIG_WINNER/configs/labels.yaml
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
topics/02_AFML_BIG_WINNER/data/processed/index/benchmark_indices_daily.csv
topics/02_AFML_BIG_WINNER/experiments/pending/04_high_recall_repair_event_candidate_generator_v0/code/pipeline.py
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/config.yaml
topics/02_AFML_BIG_WINNER/experiments/pending/08_risk_on_transition_recall_exploration_v0/outputs/local_cache/candidate_family_event_labels.parquet
topics/02_AFML_BIG_WINNER/experiments/pending/09_riskon_fastfail_label_feature_uplift/requirement_09a_fast_fail_label_frontier.md
topics/02_AFML_BIG_WINNER/experiments/pending/09_riskon_fastfail_label_feature_uplift/outputs/local_cache/09A_fast_fail_label_frontier/selected_label_event_bindings.parquet
```

Label recomputation 规则：

```text
entry_trade_time = next executable open after event_t0
price_adjustment = qfq
failure_10 horizon = 10 trading sessions
false_repair_20 component = 09A frozen_event_false_repair_20d_label component
winner_120 horizon = 120 trading sessions
incomplete_horizon = censored
non_executable_trade = drop from label-complete denominator, count separately
```

False-repair reconstructability gate：

```text
09A defines:
  selected_cost_bad_10_20_target =
    selected_fast_fail_10_label OR frozen_event_false_repair_20d_label

09A maps:
  frozen_false_repair_20d_label = event_false_repair_20d_label

The authoritative upstream event-level rule is 04/08
event_false_repair_label with:
  event_pos = event_t0_pos
  price column = qfq close
  horizon = 20 trading sessions
  drawdown = 08 config labels.false_repair_drawdown = -0.10
  event_false_repair_20d_label =
    any(close[event_t0_pos : event_t0_pos + 20] / close[event_t0_pos] - 1.0 <= -0.10)
  event_false_repair_20d_complete =
    event_t0_pos + 20 < instrument qfq row count

12A3 must reconstruct this component for 12A2 events using the same
event_t0 close anchor and qfq path basis. It is a readout label only;
it is not a t0 feature and must not be used to generate candidates.

If the exact frozen false-repair component cannot be reconstructed for
new 12A2 events, then:
  false_repair_20d_label = null
  false_repair_20d_rate = null
  bad_side_10_20_rate = null
  label_recompute_gate_pass = false
  final decision cannot be 12A3_state_change_backbone_supported
```

不得用旧 `mae_20d`、aggregate false-repair rate、R-core-only label binding 或临时 drawdown 近似替代 09A frozen component。

12A3 必须输出 label parity audit：

```text
state_change_label_recompute_parity_audit.csv
```

审计规则：

```text
For 08/09A events that can be joined by event_id / canonical_event_id:
  recompute failure_10, false_repair_20, winner_120 from qfq path
  compare against frozen upstream labels

If false_repair_20d parity match rate < 0.995 on matched complete rows:
  label_recompute_gate_pass = false
  final decision cannot be 12A3_state_change_backbone_supported

If winner_120 parity match rate < 0.995 on matched complete rows:
  label_recompute_gate_pass = false
  final decision cannot be 12A3_state_change_backbone_supported
```

R-core arm 的 primary label readout 优先使用 `r_core_arm_event_registry.csv.gz` 中的 frozen labels：

```text
fast_fail_10d_label
false_repair_20d_label
winner_120_label
horizon_complete_10d
horizon_complete_20d
horizon_complete_120d
```

如果实现同时重算 R-core labels，必须输出 cross-check；若重算值与 frozen registry 对同一 event key 不一致，R-core primary readout 仍以 frozen registry 为准，并在 report 中记录 mismatch count。

## 5. Frontier arm 定义

12A3 必须物化 `frontier_arm_registry.csv`。每个 arm 至少包含：

```text
frontier_arm_id
arm_role
source_population
source_path
event_selection_rule
priority_policy
is_primary_decision_arm
is_benchmark_arm
is_sensitivity_arm
is_family_slice
```

必需 arms：

| frontier_arm_id | role | 事件口径 |
| --- | --- | --- |
| `08_R_core_event_regime_gated_raw` | primary benchmark | 12A1 published R-core raw benchmark |
| `08_R6_event_regime_gated_raw` | secondary reference | 12A1 published R6 lower-density reference |
| `12A2_C0_primary_canonical_union` | primary candidate | 12A2 canonical supported events 全量 |
| `12A2_B1_primary` | family slice | `primary_family_id = B1` |
| `12A2_B2_primary` | family slice | `primary_family_id = B2` |
| `12A2_B3_primary` | family slice | `primary_family_id = B3` |
| `12A2_B4_primary` | family slice | `primary_family_id = B4` |
| `12A2_B5_primary` | family slice | `primary_family_id = B5` |
| `12A2_B6_primary` | family slice | `primary_family_id = B6` |
| `12A2_B8_primary` | family slice | `primary_family_id = B8` |
| `12A2_multi_family_trigger_ge2` | confidence tier | `triggered_family_count >= 2` |
| `12A2_single_family_trigger` | confidence tier | `triggered_family_count = 1` |
| `12A2_B8_only_same_event_diagnostic` | diagnostic slice | B8 trigger present and no B1 / B3 / B5 trigger on same canonical event；只回答 event-level overlap，不回答 incremental episode recall |
| `12A2_B8_incremental_episode_recall_vs_B1_B3_B5` | diagnostic slice | B8 captured episode/window minus episodes captured by B1/B3/B5 in the same window |
| `12A2_B1_B3_collision_current_priority` | diagnostic slice | canonical events with B1/B3 same-day raw collision under C0 current priority |
| `12A2_B3_before_B1_priority_sensitivity` | sensitivity | 从 raw instances 重新 canonicalize：B3 priority 高于 B1，仅用于 timing / recall sensitivity |

B7 为 12A2 diagnostic-only family，`canonical_priority = 90`，不进入 primary canonical union，也不设 family slice arm。若 12A3 primary frontier 中出现 `primary_family_id = B7` 或 blocked industry family，必须 fail closed。

Conditional arm：

```text
if 12A2_C0_primary_canonical_union event precision <= R-core precision
or B5 primary share drives more than 40% of inside-window false positives:
  include 12A2_B5_downpriority_sensitivity
```

Conditional arm 只能作为 diagnostic，不得替代 primary decision arm，除非后续另立 12A4/12A5 requirement。

### 5.1 Priority sensitivity 重算规则

`12A2_B3_before_B1_priority_sensitivity` 必须从 raw instances 重建，不能复用 C0 primary canonical event id、`union_cooldown_status` 或 C0 已经物化的 primary choice。

重建起点：

```text
source = state_change_candidate_event_instances.csv.gz
filter:
  raw_event_status = triggered
  family_input_status = runnable_existing_data
  allowed_for_primary_canonical_flag = true
  first_trigger_status IN (first_observed_in_sample, first_after_reset)
  non_executable_next_open = false
  event_t0_pit_status = pass
  trade_open_pit_status = pass
```

只允许改变 same-day primary priority：

```text
current C0 priority:
  B1=10, B3=20, B2=30, B4=40, B5=50, B6=60, B8=70

B3-before-B1 sensitivity priority:
  B3=10, B1=20, B2=30, B4=40, B5=50, B6=60, B8=70
```

重算步骤：

```text
1. group by instrument + event_t0_date
2. within same-day group choose lowest sensitivity priority as primary_family_id
3. preserve triggered_family_variants and triggered_family_count from all raw rows in the group
4. sort same-instrument same-day-collapsed events by event_t0_pos
5. apply the same C0 union_level_cooldown_sessions = 10 after same-day collapse
6. emit new deterministic sensitivity canonical_event_id prefixed by frontier_arm_id
```

不得重算 family formula、threshold、feature snapshot、reset state 或 raw trigger generation；不得把 sensitivity canonical events 写回 12A2 primary candidate artifacts。

## 6. Episode alignment 口径

### 6.1 窗口定义

每个 event 只允许按同一 `instrument` 对齐到 06 risk_on episode。必需窗口：

| window_id | inside-window 条件 |
| --- | --- |
| `pre120_calendar_to_high` | `pre120_calendar_start_date <= event_t0_date <= episode_high_date` |
| `low_to_high` | `episode_low_date <= event_t0_date <= episode_high_date` |
| `low_to_first_50pct` | `episode_low_date <= event_t0_date <= first_50pct_date`；若 `first_50pct_date` 缺失则该 episode 在此窗口不可评估 |

Primary recall 使用 `pre120_calendar_to_high` 和 `low_to_high`。`low_to_first_50pct` 是 timing / tradability sensitivity，不得单独决定 final status。

### 6.2 Episode recall

Episode recall 的分母是 06 risk_on 428 episodes：

```text
eligible_episode_n = count(episode_id)
captured_episode_n = count(episode_id with at least one arm event inside window)
episode_recall = captured_episode_n / eligible_episode_n
```

Split-specific episode recall 使用 episode 的 `split` 字段作为分母；只有同 split 的 event 可以捕捉该 split episode。跨 split event 命中必须计入：

```text
split_mismatch_candidate_n
```

但不得进入 split-specific numerator。

Validation split 的 06 risk_on eligible episode count 很小；validation 指标只作 readout / caveat，不参与 supported 或 forced-downgrade 判定。Supported / partial / no-improvement 的跨期稳定性判断以 train 与 robustness 为主。

### 6.3 Event precision

Event precision 的分母是 arm 内可执行事件：

```text
event_n = count(frontier arm events)
event_inside_window_n = count(events with at least one same-instrument episode window match)
event_precision = event_inside_window_n / event_n
outside_event_rate = 1 - event_precision
```

Split-specific event precision 也必须使用同 split 对齐：

```text
if split != all:
  event_n = count(frontier arm events where event_split = split)
  event_inside_window_n =
    count(events with same-instrument episode window match AND event_split = episode.split)
  split-mismatched same-instrument/window matches are excluded from numerator
```

如果一个 event 同时落入多个 episode window：

```text
event_inside_window_n 只计 1 次
multi_episode_event_overlap_n += 1
```

事件级 inside / outside 不能用 episode count 反推，必须从 event-level join 直接计算。

### 6.4 Timing

Timing 必须同时输出 event-level 和 captured-episode first-event 口径：

```text
event_minus_low_trading_days = event_t0_pos - episode_low_pos
event_minus_low_calendar_days = event_t0_date - episode_low_date
first_event_minus_low_trading_days =
  min(event_t0_pos inside window for that episode and arm) - episode_low_pos
```

`episode_low_pos` 必须从对应 instrument qfq 日线定位；如果 episode low date 不在 qfq calendar，必须记录 `episode_low_pos_status = missing`，该 episode 不进入 timing denominator，但仍进入 recall denominator。

Timing quality 的 primary 比较使用 `low_to_high` 窗口下 captured episodes 的 first-event median。`pre120_calendar_to_high` 下的负 lag 用于判断是否过早，不得被解释为更好 timing。

R-core timing baseline 必须由 12A3 用同一套 event-to-episode join 和 captured-episode first-event 口径重算：

```text
r_core_low_to_high_first_event_minus_low_median =
  median over captured episodes of first R-core event inside low_to_high window
```

不得直接使用 `r_core_event_precision_by_window.csv` 中的 `median_event_minus_low_days_for_matched_events` 作为 supported timing gate 的 baseline；该字段是已发布 R-core readout 的 matched-event 统计，可能混入 pre-low 事件，和本需求的 `low_to_high captured_episode_first_event` 不是同一个量。

## 7. 指标定义

### 7.1 Recall / precision frontier

每个 `frontier_arm_id x split x window_id` 必须输出：

```text
eligible_episode_n
captured_episode_n
missed_episode_n
episode_recall
event_n
event_inside_window_n
event_precision
outside_event_rate
recall_retention_vs_r_core = episode_recall / r_core_episode_recall
precision_delta_vs_r_core = event_precision - r_core_event_precision
precision_ratio_vs_r_core = event_precision / r_core_event_precision
```

若 R-core 对应 split / window 的 precision 或 recall 不可得，`*_vs_r_core` 字段必须为 null，并标记 `benchmark_status = missing`；不得用 secondary reference arm 补位。

### 7.1.1 B8 incremental episode recall

B8 incremental recall 必须按 episode/window 计算，不得用 same-day raw overlap 或 same canonical event overlap 近似。

定义：

```text
B8_captured_episode_window =
  episode_id x window_id captured by 12A2_B8_primary

B1_B3_B5_captured_episode_window =
  episode_id x window_id captured by any of:
    12A2_B1_primary
    12A2_B3_primary
    12A2_B5_primary

B8_incremental_episode_window =
  B8_captured_episode_window
  minus B1_B3_B5_captured_episode_window
```

必需 readout：

```text
b8_captured_episode_n
b1_b3_b5_captured_episode_n
b8_incremental_episode_n
b8_incremental_recall_pct_of_eligible
b8_incremental_share_of_b8_captured
b8_incremental_event_precision
b8_incremental_first_event_minus_low_median
b8_incremental_bad_side_10_20_rate
```

该 readout 只用于解释 B8 是 recall completion 还是 precision drag；不得单独把 B8 升级为 primary backbone。

### 7.2 Captured-episode density

每个 arm 必须按 captured episode 输出：

```text
events_per_captured_episode_median
events_per_captured_episode_p95
events_per_captured_episode_max
captured_episode_with_ge3_events_rate
captured_episode_with_ge5_events_rate
```

这些指标回答“是否用过多事件才捕捉到一个 episode”。如果 recall 提高完全来自单个 episode 内密集重复触发，必须在 report 中降级解释。

### 7.3 全局 event density 和 duplicate

Density denominator 必须沿用 12A2 / 12A1 兼容口径：

```text
density_basis_id = 08_full_evaluated_universe_years_252
events_per_instrument_year_mean = event_n / denominator_instrument_years
events_per_instrument_year_p95 = p95(per-instrument event count / active years)
```

同 instrument duplicate：

```text
same_instrument_10d_duplicate_rate =
  count(events whose previous same-arm same-instrument event is within 10 trading sessions)
  / event_n
```

所有 density 指标必须按 all / train / validation / robustness 输出，并可按 `board_bucket`、`market_regime_bucket` slice。

### 7.4 Bad-side exposure

12A3 必须输出 fast-fail / false-repair exposure：

```text
fast_fail_10d_rate =
  count(fast_fail_10d_label = true and horizon_complete_10d = true)
  / count(horizon_complete_10d = true)

false_repair_20d_rate =
  count(false_repair_20d_label = true and horizon_complete_20d = true)
  / count(horizon_complete_20d = true)

bad_side_10_20_rate =
  count((fast_fail_10d_label or false_repair_20d_label) and both relevant horizons complete)
  / count(both relevant horizons complete)
```

120d winner label 只作 exposure readout：

```text
winner_120_rate =
  count(winner_120_label = true and horizon_complete_120d = true)
  / count(horizon_complete_120d = true)
```

Label completeness 必须单独报告。任何 incomplete horizon 不得静默当作 negative label。

### 7.5 PIT executable coverage

每个 arm 必须输出：

```text
event_t0_pit_pass_rate
next_open_executable_rate
trade_open_price_available_rate
label_10d_complete_rate
label_20d_complete_rate
label_120d_complete_rate
```

12A2 primary candidate 若 `next_open_executable_rate < 0.99`，最终状态不得高于：

```text
12A3_state_change_backbone_partial_feature_source
```

### 7.6 Board / regime / family slices

必需 slice：

```text
board_bucket in {main_board, chinext}
market_regime_bucket in {risk_on, transition, risk_off}
primary_family_id in {B1, B2, B3, B4, B5, B6, B8}
triggered_family_count_bucket in {1, ge2}
```

Slice 必须写入单独的 `backbone_frontier_slice_readout.csv`；不得只在报告文本中口头描述。

如果 `main_board` 贡献超过 80% event_n 且 precision / recall uplift 主要来自 main_board，report 必须明确写出 board concentration caveat。

## 8. 决策规则

### 8.1 非阻塞研究状态

12A3 的三个非阻塞 final decision：

```text
12A3_state_change_backbone_supported
12A3_state_change_backbone_partial_feature_source
12A3_no_backbone_improvement_over_r_core
```

### 8.2 Operational failure 状态

允许的 fail-closed 状态：

```text
12A3_input_blocked
12A3_frontier_incomplete
```

这些状态不是研究结论，只表示 frontier 无法完整评估。

### 8.3 Supported gate

`12A3_state_change_backbone_supported` 要求 primary arm `12A2_C0_primary_canonical_union` 同时满足：

```text
pre120_calendar_to_high episode_recall_all >= 0.70
pre120_calendar_to_high episode_recall_robustness >= 0.60
low_to_high episode_recall_all >= 0.45

low_to_high event_precision_all >= max(
  r_core_low_to_high_event_precision_all + 0.02,
  r_core_low_to_high_event_precision_all * 1.30
)

pre120_calendar_to_high event_precision_all >= r_core_pre120_event_precision_all

events_per_instrument_year_mean_all <= r_core_events_per_instrument_year_mean_all * 0.75
events_per_instrument_year_p95_all <= r_core_events_per_instrument_year_p95_all * 0.75
same_instrument_10d_duplicate_rate_all <= 0.20

low_to_high first_event_minus_low_median_all <= r_core_low_to_high_first_event_minus_low_median_all
bad_side_10_20_rate_all <= r_core_bad_side_10_20_rate_all

next_open_executable_rate_all >= 0.99
label_20d_complete_rate_all >= 0.90
label_120d_complete_rate_all >= 0.80
```

当前上游 R-core `low_to_high` all-sample event precision 约为 `0.0639`，因此该 precision gate 的预期数量级约为 `0.0839`。实现必须从 12A3 recomputed / audited R-core frontier 中计算阈值，不得硬编码该数值。

Timing gate 的 R-core baseline 必须来自 §6.4 的 12A3 recomputed `low_to_high captured_episode_first_event` 口径。不得使用 12A1 published `median_event_minus_low_days_for_matched_events` 字段替代。

Validation / robustness 不参与调参，但如果 robustness 同方向完全塌缩，必须降级为 partial：

```text
robustness_precision_ratio_vs_r_core < 1.0
or robustness_density_ratio_vs_r_core > 0.90
or robustness_bad_side_10_20_rate > r_core_robustness_bad_side_10_20_rate
```

### 8.4 Partial feature source gate

输出 `12A3_state_change_backbone_partial_feature_source` 的典型条件：

- C0 primary union 未通过 supported gate，但至少一个 family / confidence tier 同时改善 precision、density、timing 中的两个以上维度；
- B3-priority sensitivity 明显改善 timing，但需要新 requirement 修改 canonical priority；
- B8 episode-level incremental recall 有可观补充，但 precision drag 明显；
- multi-family tier precision 明显优于 C0 union，但 recall 不足以单独当 backbone；
- C0 primary union 因 B5 占比过高或 B5-driven inside-window false positives 未过 precision gate，但 B5-downpriority / multi-family tier / non-B5 family slice 通过 precision-density-timing readout；
- label coverage 或 PIT coverage 有 caveat，但不影响 family-level diagnostic 使用。

Partial 状态必须在 report 中明确下一步是 feature source、priority revision、threshold sweep，还是 12A4 filter feasibility；不得直接进入 morphology modeling。

### 8.5 No improvement gate

输出 `12A3_no_backbone_improvement_over_r_core` 的条件：

- C0 primary union 相对 R-core 没有 precision uplift，且 density / duplicate 也没有足够改善；
- 或 recall retention 太低，导致即使 precision 更高也无法覆盖足够 06 episodes；
- 或 family / confidence tier 的改善只出现在 train，validation / robustness 不复现；
- 或 bad-side exposure 不低于 R-core，且 timing 没有改善。

## 9. 必需输出

所有 publishable tables 写入：

```text
outputs/publishable/tables/12A3_episode_precision_recall_frontier/
```

所有 reports 写入：

```text
outputs/publishable/reports/
```

### 9.1 `input_artifact_audit.csv`

必需字段：

```text
artifact_id
relative_path
resolved_path
required_flag
read_status
schema_status
row_count
sha256
mtime_utc
notes
```

### 9.2 `frontier_arm_registry.csv`

见 §5。所有进入 frontier 的 arm 必须有唯一 `frontier_arm_id`。

### 9.3 `backbone_episode_recall_precision_frontier.csv`

必需字段：

```text
frontier_arm_id
arm_role
split
split_basis
window_id
eligible_episode_n
captured_episode_n
missed_episode_n
episode_recall
event_n
event_inside_window_n
event_precision
outside_event_rate
r_core_episode_recall
r_core_event_precision
recall_retention_vs_r_core
precision_delta_vs_r_core
precision_ratio_vs_r_core
events_per_captured_episode_median
events_per_captured_episode_p95
events_per_instrument_year_mean
events_per_instrument_year_p95
density_ratio_vs_r_core
same_instrument_10d_duplicate_rate
next_open_executable_rate
fast_fail_10d_rate
false_repair_20d_rate
bad_side_10_20_rate
winner_120_rate
label_10d_complete_rate
label_20d_complete_rate
label_120d_complete_rate
multi_episode_event_overlap_n
split_mismatch_candidate_n
frontier_status
```

### 9.4 `backbone_event_timing_distribution.csv`

必需字段：

```text
frontier_arm_id
split
window_id
timing_population
matched_event_n
captured_episode_n
event_minus_low_trading_days_p10
event_minus_low_trading_days_p25
event_minus_low_trading_days_median
event_minus_low_trading_days_p75
event_minus_low_trading_days_p90
first_event_minus_low_trading_days_p10
first_event_minus_low_trading_days_p25
first_event_minus_low_trading_days_median
first_event_minus_low_trading_days_p75
first_event_minus_low_trading_days_p90
event_minus_low_calendar_days_median
timing_denominator_status
```

`timing_population` 取值：

```text
all_matched_events
captured_episode_first_event
```

### 9.5 `backbone_captured_episode_density.csv`

必需字段：

```text
frontier_arm_id
window_id
episode_id
instrument
episode_split
episode_low_date
episode_high_date
first_50pct_date
board_bucket
duration_bucket
event_count_inside_window
first_event_t0_date
first_event_primary_family_id
first_event_triggered_family_count
first_event_minus_low_trading_days
first_event_minus_low_calendar_days
last_event_t0_date
events_before_low_n
events_low_to_high_n
events_after_high_n
capture_status
```

`capture_status` 取值：

```text
captured
missed
timing_not_evaluable
```

### 9.6 `backbone_missed_episode_diagnostics.csv`

必需字段：

```text
frontier_arm_id
window_id
episode_id
instrument
episode_split
episode_low_date
episode_high_date
first_50pct_date
board_bucket
duration_bucket
low_to_high_sessions
mfe_120
nearest_event_before_window_date
nearest_event_before_window_gap_sessions
nearest_event_after_window_date
nearest_event_after_window_gap_sessions
nearest_same_family_event_date
nearest_same_family_event_gap_sessions
miss_reason
diagnostic_status
```

`miss_reason` 取值：

```text
no_same_instrument_event
only_before_pre120
only_after_high
only_wrong_split
only_non_executable
timing_calendar_gap
unknown
```

### 9.7 `backbone_b8_incremental_episode_recall.csv`

必需字段：

```text
split
window_id
eligible_episode_n
b8_captured_episode_n
b1_b3_b5_captured_episode_n
b8_incremental_episode_n
b8_incremental_recall_pct_of_eligible
b8_incremental_share_of_b8_captured
b8_incremental_event_n
b8_incremental_event_inside_window_n
b8_incremental_event_precision
b8_incremental_first_event_minus_low_median
b8_incremental_bad_side_10_20_rate
b8_incremental_label_20d_complete_rate
incremental_status
```

### 9.8 `backbone_event_label_exposure.csv`

必需字段：

```text
frontier_arm_id
split
label_source
event_n
label_10d_complete_n
label_20d_complete_n
label_120d_complete_n
non_executable_label_drop_n
censored_10d_n
censored_20d_n
censored_120d_n
fast_fail_10d_count
fast_fail_10d_rate
false_repair_20d_count
false_repair_20d_rate
bad_side_10_20_count
bad_side_10_20_rate
winner_120_count
winner_120_rate
label_status
```

### 9.9 `backbone_frontier_slice_readout.csv`

必需字段：

```text
frontier_arm_id
split
window_id
slice_type
slice_value
eligible_episode_n
captured_episode_n
episode_recall
event_n
event_inside_window_n
event_precision
outside_event_rate
events_per_instrument_year_mean
events_per_instrument_year_p95
same_instrument_10d_duplicate_rate
fast_fail_10d_rate
false_repair_20d_rate
bad_side_10_20_rate
label_20d_complete_rate
slice_status
```

Allowed `slice_type`：

```text
board_bucket
market_regime_bucket
primary_family_id
triggered_family_count_bucket
```

### 9.10 `state_change_label_recompute_parity_audit.csv`

必需字段：

```text
label_id
comparison_population
matched_event_n
complete_event_n
match_n
mismatch_n
match_rate
missing_recomputed_n
missing_frozen_n
mismatch_near_qfq_adjustment_boundary_n
corporate_action_boundary_status
frozen_source_path
recompute_rule_id
parity_status
```

`label_id` 至少包含：

```text
failure_10_label
event_false_repair_20d_label
event_big_winner_120d_label
```

`mismatch_near_qfq_adjustment_boundary_n` 用于解释 label parity mismatch 是否集中在复权边界附近。如果缺少可审计 corporate-action / adjustment-boundary source，必须写：

```text
corporate_action_boundary_status = not_available
```

但不得因此放宽 parity gate；只能作为 report 中的 mismatch 解释。

### 9.11 `backbone_frontier_decision.csv`

必需字段：

```text
decision
decision_reason
primary_candidate_arm_id
primary_benchmark_arm_id
input_gate_pass
episode_target_gate_pass
state_change_candidate_gate_pass
r_core_benchmark_gate_pass
label_recompute_gate_pass
supported_gate_pass
partial_feature_source_gate_pass
primary_pre120_recall_all
primary_low_to_high_recall_all
primary_low_to_high_precision_all
r_core_low_to_high_precision_all
primary_density_ratio_vs_r_core_all
primary_duplicate_rate_all
primary_bad_side_10_20_rate_all
r_core_bad_side_10_20_rate_all
primary_low_to_high_first_event_median_all
r_core_low_to_high_first_event_median_all
r_core_timing_baseline_source
recommended_next_requirement
block_reason
```

### 9.12 `backbone_frontier_decision_report.md`

报告必须用中文写，至少包含：

1. final decision 和一句话原因；
2. R-core vs 12A2 C0 union 的 recall / precision / density / timing / bad-side 对比；
3. family-sliced 结论，特别是 B3、B5、B6、B8；
4. B1/B3 priority sensitivity；
5. B8 episode-level incremental recall completion 与 precision drag；
6. multi-family confidence tier 是否改善 precision；
7. board / regime concentration caveat；
8. missed episode 的主要结构；
9. 是否允许进入 12A4 filter feasibility，或是否只保留为 feature source。

## 10. Manifest

必须输出：

```text
outputs/manifests/12A3_episode_precision_recall_frontier_manifest.json
```

Manifest 必须记录：

```text
run_id
requirement_path
requirement_sha256
config_path
config_sha256
input_artifact_audit_sha256
frontier_arm_registry_sha256
backbone_episode_recall_precision_frontier_sha256
backbone_event_timing_distribution_sha256
backbone_captured_episode_density_sha256
backbone_missed_episode_diagnostics_sha256
backbone_b8_incremental_episode_recall_sha256
backbone_event_label_exposure_sha256
backbone_frontier_slice_readout_sha256
state_change_label_recompute_parity_audit_sha256
backbone_frontier_decision_sha256
report_sha256
final_decision
created_at_utc
```

## 11. 测试要求

`tests/test_12a3_episode_precision_recall_frontier.py` 至少覆盖：

1. 06 risk_on episode registry 必须是 428 行且 `episode_id` 唯一；
2. 12A2 decision 必须为 supported 才能进入 frontier；
3. event-to-episode window 边界包含 start / end date；
4. event precision 分母是 event，不是 episode；
5. episode recall 分母是 episode，不是 event；
6. multi-episode event overlap 只在 event precision numerator 中计一次；
7. split mismatch 不得进入 split-specific recall numerator；
8. same-instrument 10d duplicate 按 trading sessions 计算；
9. incomplete horizon 不得当作 negative label；
10. B3-before-B1 sensitivity 不得覆盖 C0 primary frontier；
11. B3-before-B1 sensitivity 必须重算 same-day priority 和 union cooldown，不得复用 C0 `union_cooldown_status`；
12. split-specific event precision 的 numerator 必须要求 `event_split = episode.split`；
13. B8 incremental recall 必须按 episode/window complement 计算，不得用 same-event overlap 近似；
14. slice readout 必须包含 board/regime/family/triggered-family-count 四类 slice；
15. label parity audit match rate 低于阈值时不得输出 supported；
16. primary canonical union 的 `primary_family_id` 取值必须是 `{B1,B2,B3,B4,B5,B6,B8}` 子集，不得包含 B7 或 blocked industry family；
17. R-core timing baseline 必须由 12A3 按 low-to-high captured-episode first-event 口径重算，不得直接读取 12A1 matched-event median；
18. final decision 只能从 §8 的 allowed states 中选择；
19. required outputs schema 完整且非空，除非 final decision 是 input blocked。

## 12. 完成定义

12A3 完成条件：

```text
all required gates evaluated
all required output tables written
manifest written with hashes
Chinese decision report written
final decision in allowed states
```

如果最终不是 `12A3_state_change_backbone_supported`，report 必须明确说明停止原因或降级路径；不得只输出数值表而不解释是否继续。
