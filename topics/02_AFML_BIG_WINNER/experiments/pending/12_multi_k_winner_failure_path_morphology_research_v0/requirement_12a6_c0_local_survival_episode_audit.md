# 需求：12A6 C0 Local Survival Episode Audit

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
5. 必需输入缺失、schema 不匹配、PIT 时间戳不可证明时 fail closed；不得从报告文本或聚合表反推出事件、标签或特征。

## 1. 实验身份

```text
experiment_id = 12_state_change_event_backbone_rebuild_v0
legacy_directory_id = 12_multi_k_winner_failure_path_morphology_research_v0
phase_id = 12A6
run_id = 12A6_c0_local_survival_episode_audit
status = spec_draft_pending_review
expected_entrypoint = src/run_12a6_c0_local_survival_episode_audit.py
expected_config = configs/config_12a6_c0_local_survival_episode_audit.yaml
expected_test_file = tests/test_12a6_c0_local_survival_episode_audit.py
```

12A6 是纯 audit 阶段，不训练模型，不做 policy replay，不声明交易 alpha。它只回答：

```text
C0 state-change 买点是否能形成稳定的 event-level survival opportunity？
如果能，MAE / MFE / horizon 的候选阈值应如何从 forward path 统计中校准？
```

本阶段不是重构 06 big-winner episode registry，也不是替换 12A0/12A1 冻结的 06/11A2 winner 分母。12A6 新建的是 C0-local event-level survival outcome。

## 2. 上游冻结事实

12A6 承接以下已发布事实：

```text
12A1 decision = 12A1_r_core_recall_benchmark_only
12A2 decision = 12A2_state_change_candidate_generation_supported
12A3 decision = 12A3_state_change_backbone_partial_feature_source
12A4 decision = 12A4_meta_label_partial_feature_source
12A5A decision = 12A5A_no_decoupling_stop_keep_feature_source
```

12A3 关键读数：

```text
C0 event_n = 28,691
R-core event_n = 47,914
C0 low_to_high recall = 98.60%
R-core low_to_high recall = 97.43%
C0 low_to_high event precision = 5.32%
R-core low_to_high event precision = 6.39%
C0 same-instrument 10d duplicate = 7.25%
R-core same-instrument 10d duplicate = 57.83%
C0 first event minus low median = 9 sessions
R-core first event minus low median = 14 sessions
```

12A4 / 12A5A 关键含义：

```text
C0 是低密度、低重复、PIT 可执行的 state-change feature source。
C0 不是已被证明的 standalone timing selector。
12A4 meta-labeling 有 precision uplift，但 bad-side 同时上升。
12A5A 没有证明 clean winner 与 bad-side 在当前 PIT feature 空间稳定可分。
```

12A6 的研究动机：

```text
big winner 是稀有右尾目标。
用 rare big-winner episode 作为 C0 买点的唯一成功定义，会把一批中右尾、
可交易但不是超级右尾的 C0 机会计为 false positive。
因此需要先独立校准 C0-local survival outcome。
big winner 与 survival episode 是两个不同目标；12A6 只在 survival outcome
确定后检查 big-winner enrichment，而不把 big winner 作为 survival label。
```

## 3. Primary Scope

### 3.1 Primary Event Universe

12A6 的 primary denominator 固定为 12A2 已发布的 C0 canonical supported events：

```text
source_artifact =
  outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/
  state_change_candidate_event_canonical.csv.gz

source_scope_id = 12A2_C0_primary_canonical_union
primary_denominator = one row per canonical_event_id
expected_primary_event_n = 28,691
```

`source_scope_id` is a 12A6-derived constant materialized in 12A6 outputs. It is not an upstream column in the 12A2 canonical CSV and must not be read as one.

Primary filter：

```text
candidate_generation_status = supported_canonical_event
non_executable_next_open = false
event_t0_pit_status = pass
trade_open_pit_status = pass
trade_open_price is not null
canonical_event_id is unique
```

12A6 不复用 12A4/12A5A 的 risk_on-only denominator。Risk-on 读数必须保留，但只作为 mandatory slice，不作为 12A6 primary denominator。

### 3.2 Regime / Board / Family Slices

12A6 不搜索 regime filter，不比较哪个 regime 最好后再回头选择。所有 primary frontier 必须同时输出以下固定切片：

```text
scope_id = all_c0
scope_id = regime_risk_on
scope_id = regime_transition
scope_id = regime_risk_off
scope_id = board_main_board
scope_id = board_chinext
scope_id = primary_family_B1
scope_id = primary_family_B2
scope_id = primary_family_B3
scope_id = primary_family_B4
scope_id = primary_family_B5
scope_id = primary_family_B6
scope_id = primary_family_B8
```

Expected family counts in the primary 12A2 canonical universe are:

```text
B1 = 4,570
B2 = 3,143
B3 = 3,508
B4 = 369
B5 = 10,887
B6 = 2,443
B8 = 3,771
```

There is no `B7` family in the published 12A2 canonical universe. Do not emit a primary `primary_family_B7` slice. If the implementation performs a family completeness diagnostic, `B7` may appear only as an explicitly blocked / absent diagnostic note, never as a primary slice.

切片只用于诊断稳定性和后续研究路由。12A6 的 success/fail 不能由事后挑选单个最好切片决定。

Per-family slices are diagnostic-only. They must set `selection_eligible_flag = false` and must not participate in selected candidate eligibility, robustness gates, or final decision-state gates. This is required because thin family slices such as `B4 = 369` cannot satisfy the primary `complete_executable_event_n >= 500` threshold even before split / regime / board subdivision.

### 3.3 Event-Level Outcome, Not Episode Collapse

12A6 第一阶段定义的是 event-level survival outcome：

```text
one row = one C0 canonical event
anchor = event_t0_date
entry = trade_open_date / trade_open_price
```

不做 same-instrument episode collapse，不把多个 C0 事件合并成一个新 episode。若同一 instrument 在同一趋势内出现多个 C0 事件，它们在 primary event-level audit 中各自保留。

需要单独输出 overlap / density readout：

```text
same_instrument_prior_c0_10d
same_instrument_prior_c0_20d
same_instrument_next_c0_20d
overlap_with_other_c0_survival_window_n
```

如果后续要构建真正的 survival episode registry，必须另写 requirement 定义 cooldown / collapse / priority 规则。

### 3.4 06 / 11A2 / Big-Winner Enrichment Discipline

12A6 不把以下 population 作为 survival 成功定义的分母：

```text
06 risk_on big-winner episodes = 428
11A2 risk_on PIT-valid big-winner rows = 446
12A4 risk_on C0 event universe = 15,113
```

这些 population 只能作为 enrichment / diagnostic：

```text
06 / 11A2:
  用于观察 survival-selected C0 events 是否富集既有 big-winner lifecycle；
  不参与 primary survival denominator。

12A4 risk_on C0:
  用于 sanity cross-check risk_on slice；
  不替代 all-C0 primary denominator。
```

## 4. 核心研究问题

12A6 回答以下问题：

1. C0 canonical events 在 event-level forward path 上是否有稳定的 survival opportunity？
2. 不同 survival upper barrier 的 time-to-hit 曲线分别长什么样？
3. 成功触达 `+20%` / `+30%` 前，C0 事件通常经历多深的 pre-success MAE？
4. `-8%`、`-10%`、`-12%`、`-15%` 等下障碍会杀掉多少 true survivor？
5. 40d / 60d / 80d / 120d horizon 的边际收益是否存在拐点？
6. survival-selected C0 events 是否在与既有 registry 相同 regime 的 baseline 内富集 big-winner lifecycle？
7. 主升浪后期 C0 买点更偏向 `lower_first`、`neutral`，还是 `not_big_winner_but_survivor`？

## 5. 非目标

12A6 明确不做：

- 不训练 meta-label model、selector、rejector 或 LightGBM challenger；
- 不做 policy replay、仓位、entry / exit 组合优化、交易成本回测或资金曲线；
- 不声明可交易 alpha；
- 不修改 12A2 family formula、threshold、canonicalization priority 或 C0 primary union；
- 不重新搜索 regime filter；
- 不把 robustness / OOS 结果用于回头挑更好看的 MAE / MFE / horizon；
- 不把 survival outcome 用作当期特征；
- 不使用 future return、MFE、MAE、episode low/high、target label 生成任何 t0 feature；
- 不替换 06 risk_on big-winner episode registry；
- 不创建新的 survival episode registry collapse 规则。

## 6. 必需输入

### 6.1 12A2 C0 事件输入

必需输入：

```text
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_generation_decision.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_canonical.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_candidate_event_instances.csv.gz
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_canonicalization_spec.csv
outputs/publishable/tables/12A2_state_change_backbone_candidate_generator/state_change_density_audit.csv
outputs/manifests/12A2_state_change_backbone_candidate_generator_manifest.json
```

12A2 gate：

```text
state_change_generation_decision.decision =
  12A2_state_change_candidate_generation_supported

state_change_generation_decision.primary_canonical_event_n = 28691
state_change_generation_decision.next_open_executable_gate_pass = true
state_change_generation_decision.pit_feature_gate_pass = true
```

`state_change_candidate_event_instances.csv.gz` 只能用于 overlap / triggered-family diagnostics，不得重新生成 primary denominator。

### 6.2 行情、执行和标签配置输入

必需输入：

```text
topics/02_AFML_BIG_WINNER/configs/labels.yaml
topics/02_AFML_BIG_WINNER/data/raw/akshare/day/qfq/{instrument}.csv
topics/02_AFML_BIG_WINNER/data/processed/universe/pit_topn_400_100_executable_daily.csv
```

`pit_topn_400_100_executable_daily.csv` is a large PIT membership file. Implementations must filter by required instruments / dates or stream the file by instrument/date key. Loading unrelated full-history membership rows into memory is not required and must not be assumed by tests.

Price contract：

```text
price_adjustment = qfq
price columns required = date, open, high, low, close, volume, money, turnover_rate
entry_price = trade_open_price from 12A2 canonical event
entry_date = trade_open_date from 12A2 canonical event
```

Barrier observation must match existing label policy unless a sensitivity table explicitly says otherwise:

```text
upper_touch_price = high
lower_touch_price = low
same_bar_priority = lower_barrier_first
incomplete_horizon = censored
non_executable_trade = drop / entry_blocked audit row
```

`close`-based confirmation can be added only as diagnostic sensitivity. It must not replace the primary high/low first-hit label.

### 6.3 Big-Winner Enrichment 输入

Big winner 与 survival outcome 是两个不同目标。12A6 不重算 big-winner label 作为 survival label，也不把 `+50% / 120d` 放入 survival 阈值选择。Big winner 只作为 enrichment diagnostic：

```text
question:
  selected survival events 是否比同 regime 的 C0 baseline 更容易落入既有 big-winner lifecycle？
```

必需 enrichment 输入：

```text
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/episode_target_registry_06_risk_on_428.csv
outputs/publishable/tables/12A0_12A1_winner_registry_lineage_and_r_core_backbone_demotion_audit/pit_candidate_winner_registry_11a2_446.csv
```

可选 sanity cross-check 输入：

```text
outputs/publishable/tables/12A4_state_change_meta_label_filter_feasibility/meta_label_event_targets.csv.gz
```

使用约束：

1. 06 / 11A2 winner registry 只能用于 enrichment readout，不参与 survival threshold selection。
2. 06 / 11A2 registry 是 `risk_on` scope；headline enrichment 必须在 `risk_on` scope 内同时计算 numerator 和 baseline。
3. `meta_label_event_targets.csv.gz` 只覆盖 12A4 risk_on C0 / R-core universe，不能覆盖 all-C0 primary denominator。
4. `meta_label_event_targets.csv.gz` 只能用于 risk_on subset sanity cross-check。
5. all-C0 enrichment 可以作为 diagnostic-only readout，但不能作为 06 / 11A2 headline enrichment ratio。
6. 不得把任何 big-winner label 作为 12A6 survival label 或 decision gate。

Enrichment 口径：

```text
bigwinner_enrichment_rate =
  selected_upper_first_survival_events_in_registry_scope_with_bigwinner_overlap
  / selected_upper_first_survival_events_in_registry_scope

registry_scope_baseline_rate =
  all_complete_executable_c0_events_in_registry_scope_with_bigwinner_overlap
  / all_complete_executable_c0_events_in_registry_scope

bigwinner_enrichment_ratio =
  bigwinner_enrichment_rate / registry_scope_baseline_rate
```

For `06_registry` and `11a2_registry`, `registry_scope_id = regime_risk_on`, `baseline_scope_id = regime_risk_on`, and `headline_enrichment_flag = true`. If `registry_scope_baseline_rate = 0`, set `bigwinner_enrichment_ratio = NaN` and `enrichment_status = undefined_zero_baseline`.

If an all-C0 diagnostic row is emitted, set `headline_enrichment_flag = false` and `diagnostic_only_flag = true`.

Overlap windows must be reported separately:

```text
06_low_to_high_overlap
06_pre120_to_high_overlap
11a2_pre120_to_high_overlap
```

No enrichment metric can change the selected survival threshold or final 12A6 decision state.

## 7. Survival Label 定义

### 7.1 Barrier Grid

12A6 必须完整评估以下 grid：

```text
horizon_sessions = [10, 20, 40, 60, 80, 120]
upper_barrier_pct = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
lower_barrier_pct = [-0.06, -0.08, -0.10, -0.12, -0.15, -0.20]
```

Existing `labels.yaml` `continuation_60` is a comparison anchor only:

```text
continuation_60.horizon_days = 60
continuation_60.min_mfe_pct = 0.20
continuation_60.max_drawdown_pct = -0.15
```

It does not preselect 12A6 survival thresholds. The report must state when the selected audit threshold differs from this existing label.

所有 barrier 以 entry price 为基准：

```text
upper_touch_threshold = entry_price * (1 + upper_barrier_pct)
lower_touch_threshold = entry_price * (1 + lower_barrier_pct)
```

Horizon observation is inclusive from entry day:

```text
observation_positions = [entry_pos, entry_pos + horizon_sessions] inclusive
python_slice = price.iloc[entry_pos : entry_pos + horizon_sessions + 1]
horizon_complete = entry_pos + horizon_sessions < len(price)
time_to_hit_sessions = hit_pos - entry_pos
```

This means a same-day hit has `time_to_hit_sessions = 0`. A 60-session horizon requires price data through `entry_pos + 60`.

### 7.2 First-Hit 状态

每个 `(event, horizon, upper, lower)` 组合输出一个 first-hit outcome：

```text
upper_first:
  horizon 内 high 首先触达 upper_touch_threshold；
  如果同一日 high 和 low 同时触障，按 lower_first 处理。

lower_first:
  horizon 内 low 首先触达 lower_touch_threshold；
  包括 same_bar_conflict lower-first cases。

neutral:
  horizon 内上下障碍均未触达，且 horizon 完整。

censored:
  price data 不足以观察完整 horizon。

entry_blocked:
  entry_date / entry_price 无法证明 next executable open 可交易。
```

Because the primary universe already requires `non_executable_next_open = false` and `trade_open_pit_status = pass`, `entry_blocked_n` is expected to be zero. If recomputation finds `entry_blocked_n > 0`, output the rows in `c0_entry_executability_audit.csv`, set `entry_parity_gate_pass = false`, and final decision must be `12A6_blocked_input_or_pit_failure`.

Rate denominators are frozen as:

```text
event_n = all rows in the selected scope
complete_executable_event_n = event_n - entry_blocked_n - censored_n

upper_first_rate = upper_first_n / complete_executable_event_n
lower_first_rate = lower_first_n / complete_executable_event_n
neutral_rate = neutral_n / complete_executable_event_n
same_bar_conflict_rate = same_bar_conflict_n / complete_executable_event_n
```

`same_bar_conflict` rows are counted inside `lower_first_n` because `same_bar_priority = lower_barrier_first`.

### 7.3 Forward Path 指标

对每个 event 和 horizon 必须计算：

```text
mfe_h = max(high over observation_positions) / entry_price - 1
mae_h = min(low over observation_positions) / entry_price - 1
close_return_h = close[entry_pos + horizon_sessions] / entry_price - 1
time_to_upper_sessions
time_to_lower_sessions
first_hit_date
first_hit_status
same_bar_conflict_flag
```

对每个 upper barrier，必须计算：

```text
pre_success_mae:
  在 upper_first event 中，从 entry 到 upper_first date 之间的 min(low)/entry_price - 1。

true_survivor_killed_by_lower:
  对给定 upper 和 lower，若 event 最终能在 horizon 内触达 upper，
  但在触达 upper 前先触发 lower，则记为 killed_by_lower。
```

### 7.4 Payoff Proxy

12A6 不做完整回测，但每个 grid row 必须输出交易含义读数：

```text
exit_return_proxy:
  upper_first -> upper_barrier_pct
  lower_first -> lower_barrier_pct
  neutral -> close_return_h
  censored / entry_blocked -> NaN

r_multiple_proxy:
  exit_return_proxy / abs(lower_barrier_pct)

expected_r_multiple_proxy:
  mean(r_multiple_proxy) over complete, executable rows

time_penalized_expected_r_proxy:
  expected_r_multiple_proxy / sqrt(median_time_to_upper_sessions + 1)
```

`exit_return_proxy` and `expected_r_multiple_proxy` are first-hit proxies, not tradable PnL, not slippage-aware execution results, and not limit-up / limit-down fill simulations. Because `r_multiple_proxy = exit_return_proxy / abs(lower_barrier_pct)`, it structurally rewards tighter lower barriers. It may be used as an audit readout and late tie-breaker only; it must not be the first ranking key for threshold selection.

## 8. 阈值校准规则

12A6 是 audit，但仍必须用 deterministic train-only 规则给出候选标签建议，避免从 robustness / OOS 回头挑阈值。

### 8.1 Candidate Selection From Audit Grid

12A6 不预先指定 `+20%` 或 `+30%` 为正式 survival label。Upper barrier、lower barrier、horizon 都从第 7 节完整 grid 的 train split 统计中选择。

Eligible survival candidates must satisfy on train:

```text
candidate_scope_id = all_c0
candidate_split = train
selection_eligible_flag = true
complete_executable_event_n >= 500
upper_first_rate >= 0.10
lower_first_rate <= 0.40
true_survivor_killed_by_lower_rate <= 0.25
expected_r_multiple_proxy >= 0
median_time_to_upper_sessions <= horizon_sessions * 0.80
```

`selection_eligible_flag = true` is allowed only for `scope_id = all_c0` and `split = train`. `complete_executable_event_n >= 500` applies only to that train all-C0 candidate-selection row. Mandatory regime / board / family readouts may have lower row counts; those rows are diagnostic unless explicitly used by the board/regime robustness rule in §8.5. Per-family rows are always diagnostic-only and cannot become selected candidates.

This is a statistical selection rule, not a claim that any hard-coded MFE / MAE / horizon is correct before the audit.

### 8.2 Primary Survival Candidate Selection

From eligible candidates, choose `selected_survival_candidate` using train-only ordering:

```text
sort key 1: upper_first_rate descending
sort key 2: median_time_to_upper_sessions ascending
sort key 3: lower_first_rate ascending
sort key 4: true_survivor_killed_by_lower_rate ascending
sort key 5: upper_barrier_pct descending
sort key 6: time_penalized_expected_r_proxy descending
sort key 7: expected_r_multiple_proxy descending
sort key 8: horizon_sessions ascending
```

This ordering intentionally avoids making raw `expected_r_multiple_proxy` the first key because that proxy is mechanically inflated by tight lower barriers.

If no grid row is eligible:

```text
selected_candidate_status = no_viable_survival_threshold
```

If a grid row is selected:

```text
selected_candidate_status = pass
selected_survival_candidate_label =
  survival_U{upper_pct}_L{abs_lower_pct}_H{horizon_sessions}
```

### 8.3 Secondary / Strong Candidate Readout

After selecting the primary candidate, output a secondary strong-candidate readout:

```text
strong_candidate_scope:
  eligible candidates with upper_barrier_pct >= 0.30

selection:
  same train-only sort order as primary candidate

if none exists:
  strong_survival_candidate_status = no_viable_strong_threshold
```

If a strong candidate is selected:

```text
strong_survival_candidate_status = pass
```

The strong candidate is a readout for future ranking targets. It is not required for 12A6 supported status.

### 8.4 Horizon Plateau Readout

For every candidate upper/lower pair, compute horizon plateau on a fixed cohort:

```text
plateau_max_horizon_sessions = max(configured horizon_sessions)

plateau_cohort =
  complete executable rows whose price history is complete through plateau_max_horizon_sessions

plateau_upper_first_rate(h) =
  upper_first_n_by_horizon_h_on_plateau_cohort / plateau_cohort_event_n

next_horizon_incremental_upper_first_rate =
  plateau_upper_first_rate(next longer horizon) - plateau_upper_first_rate(current horizon)

horizon_plateau_flag =
  next_horizon_incremental_upper_first_rate <= 0.03
```

Do not subtract standard `upper_first_rate` values computed on different horizon-specific complete cohorts. The plateau readout must use the same longest-horizon-complete denominator across all horizons in the ladder.

If the selected candidate is at the longest configured horizon, set:

```text
selected_horizon_status = max_horizon_reached_no_next_horizon
```

If a shorter selected candidate has `horizon_plateau_flag = false`, set:

```text
selected_horizon_status = horizon_plateau_not_observed
```

Otherwise:

```text
selected_horizon_status = horizon_plateau_observed
```

### 8.5 Robustness Validation

The selected train candidate is then read out on validation and robustness. Robustness / validation cannot change the chosen thresholds.

Validation flags:

```text
robustness_upper_first_rate_relative_to_train >= 0.70
robustness_lower_first_rate_minus_train <= 0.10
robustness_expected_r_multiple_proxy >= 0
board_or_regime_instability_flag = false unless a slice with event_n >= 500 has
  upper_first_rate < 0.50 * all_c0_upper_first_rate
```

`board_or_regime_instability_flag` may use only board / regime slices with sufficient row count. Per-family slices must not feed this flag or any other decision gate. `robustness_complete_executable_event_n` in §12.3 refers to the selected all-C0 robustness split, not to diagnostic family rows.

Validation failures do not change the train-selected candidate; they change only the final decision state.

## 9. Late-Stage Diagnostic

12A6 must include a t0-visible late-stage diagnostic. It is readout-only and cannot change survival labels.

Required t0-visible features, computed from price history before or at event_t0 close:

```text
ret_20d
ret_60d
distance_to_60d_high
distance_to_120d_high
distance_to_60d_low
distance_to_120d_low
trend_ma_20_60_spread
volatility_20d
volatility_60d
prior_c0_event_count_20d
same_day_c0_event_count_all
```

Feature formulas:

```text
ret_20d = close_t0 / close_t0_minus_20_sessions - 1
ret_60d = close_t0 / close_t0_minus_60_sessions - 1
distance_to_60d_high = close_t0 / rolling_high_60d_at_t0 - 1
distance_to_120d_high = close_t0 / rolling_high_120d_at_t0 - 1
distance_to_60d_low = close_t0 / rolling_low_60d_at_t0 - 1
distance_to_120d_low = close_t0 / rolling_low_120d_at_t0 - 1
trend_ma_20_60_spread = ema20_t0 / ema60_t0 - 1
```

`rolling_high_*` and `rolling_low_*` include event_t0 close-observed daily bar and must not use any future bar.

EMA / rolling feature definitions must match the published 12A2 / PIT price-feature policy when an equivalent t0-visible definition exists. If the implementation recomputes these fields locally, it must use the same `qfq`, `close_observed`, daily-bar seeding, and window-inclusion policy, and the report must include a feature-source note. Any detected policy mismatch sets `late_stage_feature_policy_status = diagnostic_not_comparable`; it does not change labels, but it blocks strong conclusions from the late-stage diagnostic.

Required late-stage buckets:

```text
near_60d_high = distance_to_60d_high >= -0.05
near_120d_high = distance_to_120d_high >= -0.08
extended_20d = ret_20d >= 0.20
extended_60d = ret_60d >= 0.40
late_stage_composite = near_60d_high AND (extended_20d OR extended_60d)
```

Output must show, by split and regime:

```text
late_stage_bucket
event_n
selected_upper_first_rate
selected_lower_first_rate
selected_neutral_rate
expected_r_multiple_proxy
bigwinner_enrichment_ratio
```

This answers whether "主升浪后期 C0 买点" is actually a hard-fail problem, a neutral/no-payoff problem, or a not-big-winner-but-survivor problem.

## 10. 必需输出

### 10.1 Publishable Tables

All table outputs go under:

```text
outputs/publishable/tables/12A6_c0_local_survival_episode_audit/
```

Required tables:

```text
input_artifact_audit.csv
c0_survival_event_universe.csv.gz
c0_forward_path_distribution.csv
c0_triple_barrier_grid_frontier.csv
c0_pre_success_mae_distribution.csv
c0_time_to_hit_curve.csv
c0_threshold_candidate_decision.csv
c0_bigwinner_enrichment_crosstab.csv
c0_late_stage_failure_diagnostics.csv
c0_entry_executability_audit.csv
c0_same_bar_conflict_audit.csv
c0_overlap_density_audit.csv
```

### 10.2 Local Cache

Local cache output:

```text
outputs/local_cache/12A6_c0_local_survival_episode_audit/
  c0_survival_event_path_matrix.parquet
```

The parquet matrix may contain row-level event × horizon × barrier path details and can be large. It is not required to be publishable unless size permits.

### 10.3 Publishable Report

Required report:

```text
outputs/publishable/reports/c0_local_survival_episode_audit_report.md
```

Report must include:

1. primary denominator audit and row counts;
2. explanation that this is event-level survival outcome, not a new big-winner registry;
3. all-C0 survival grid summary;
4. risk_on / transition / risk_off slice readout;
5. selected train-only threshold candidates and robustness validation;
6. pre-success MAE findings;
7. late-stage diagnostic findings;
8. big-winner enrichment diagnostic with regime-matched headline baseline and all-C0 diagnostic rows separated;
9. comparison against existing `continuation_60` label settings from `labels.yaml`;
10. final decision state and next allowed requirement.

### 10.4 Manifest

Required manifest:

```text
outputs/manifests/12A6_c0_local_survival_episode_audit_manifest.json
```

Manifest must include:

```text
run_id
phase_id
generated_at
input_hashes
output_hashes
config_hash
git_commit_if_available
decision_state
selected_candidate_status
strong_survival_candidate_status
bigwinner_enrichment_status
late_stage_feature_policy_status
```

## 11. Output Schema Contracts

### 11.1 c0_survival_event_universe.csv.gz

Required columns:

```text
survival_event_id
canonical_event_id
instrument
event_t0_date
event_t0_pos
trade_open_date
trade_open_pos
trade_open_price
event_split
board_bucket
market_regime_bucket
primary_family_id
primary_variant_id
triggered_family_variants
triggered_family_count
canonical_priority
candidate_generation_status
non_executable_next_open
event_t0_pit_status
trade_open_pit_status
entry_status
source_scope_id
```

Uniqueness:

```text
survival_event_id unique
canonical_event_id unique
```

### 11.2 c0_triple_barrier_grid_frontier.csv

Required columns:

```text
scope_id
split
board_bucket
market_regime_bucket
primary_family_id
upper_barrier_pct
lower_barrier_pct
horizon_sessions
event_n
complete_executable_event_n
entry_blocked_n
censored_n
same_bar_conflict_n
same_bar_conflict_rate
upper_first_n
upper_first_rate
lower_first_n
lower_first_rate
neutral_n
neutral_rate
median_time_to_upper_sessions
median_time_to_lower_sessions
true_survivor_killed_by_lower_rate
expected_r_multiple_proxy
time_penalized_expected_r_proxy
median_exit_return_proxy
selection_eligible_flag
diagnostic_only_flag
label_status
```

For all-C0 rows where a slice dimension is not applicable, use:

```text
board_bucket = all
market_regime_bucket = all
primary_family_id = all
```

### 11.3 c0_pre_success_mae_distribution.csv

Required columns:

```text
scope_id
split
upper_barrier_pct
horizon_sessions
upper_first_n
pre_success_mae_p25
pre_success_mae_p50
pre_success_mae_p75
pre_success_mae_p90
pre_success_mae_p95
survivor_killed_by_lower_minus_06_rate
survivor_killed_by_lower_minus_08_rate
survivor_killed_by_lower_minus_10_rate
survivor_killed_by_lower_minus_12_rate
survivor_killed_by_lower_minus_15_rate
survivor_killed_by_lower_minus_20_rate
```

### 11.4 c0_threshold_candidate_decision.csv

Required columns:

```text
decision_state
selected_survival_candidate_label
selected_upper_barrier_pct
selected_lower_barrier_pct
selected_horizon_sessions
selected_horizon_status
selected_train_upper_first_rate
selected_train_lower_first_rate
selected_train_expected_r_multiple_proxy
selected_train_time_penalized_expected_r_proxy
selected_robustness_upper_first_rate
selected_robustness_lower_first_rate
selected_robustness_expected_r_multiple_proxy
selected_candidate_status
strong_survival_candidate_label
strong_upper_barrier_pct
strong_lower_barrier_pct
strong_horizon_sessions
strong_train_upper_first_rate
strong_robustness_upper_first_rate
strong_candidate_status
bigwinner_enrichment_ratio
bigwinner_enrichment_status
gate_failure_reasons
next_allowed_requirement
```

### 11.5 c0_forward_path_distribution.csv

Required columns:

```text
scope_id
split
horizon_sessions
event_n
complete_executable_event_n
mfe_p25
mfe_p50
mfe_p75
mfe_p90
mfe_p95
mae_p25
mae_p50
mae_p75
mae_p90
mae_p95
close_return_p25
close_return_p50
close_return_p75
close_return_p90
close_return_p95
```

### 11.6 c0_time_to_hit_curve.csv

Required columns:

```text
scope_id
split
upper_barrier_pct
lower_barrier_pct
horizon_sessions
complete_executable_event_n
upper_first_n
upper_first_rate
lower_first_n
lower_first_rate
median_time_to_upper_sessions
p75_time_to_upper_sessions
median_time_to_lower_sessions
p75_time_to_lower_sessions
plateau_max_horizon_sessions
plateau_cohort_event_n
plateau_upper_first_rate
next_horizon_incremental_upper_first_rate
horizon_plateau_flag
```

### 11.7 c0_bigwinner_enrichment_crosstab.csv

Required columns:

```text
overlap_source
overlap_window
scope_id
split
registry_scope_id
baseline_scope_id
selected_survival_candidate_label
selected_upper_first_survival_event_n
selected_upper_first_overlap_n
selected_upper_first_overlap_rate
baseline_event_n
baseline_overlap_n
baseline_overlap_rate
bigwinner_enrichment_ratio
enrichment_status
headline_enrichment_flag
diagnostic_only_flag
```

Allowed `overlap_source` / `overlap_window` values:

```text
overlap_source in [06_registry, 11a2_registry, 12a4_risk_on_sanity]
overlap_window in [low_to_high, pre120_to_high, risk_on_sanity_winner_120]
```

### 11.8 c0_late_stage_failure_diagnostics.csv

Required columns:

```text
late_stage_bucket
scope_id
split
market_regime_bucket
event_n
selected_survival_candidate_label
selected_upper_barrier_pct
selected_lower_barrier_pct
selected_horizon_sessions
selected_upper_first_n
selected_upper_first_rate
selected_lower_first_n
selected_lower_first_rate
selected_neutral_n
selected_neutral_rate
expected_r_multiple_proxy
bigwinner_enrichment_ratio
late_stage_feature_policy_status
```

### 11.9 c0_entry_executability_audit.csv

Required columns:

```text
entry_status
event_n
missing_trade_open_date_n
missing_trade_open_price_n
non_executable_next_open_true_n
trade_open_pit_fail_n
pit_membership_missing_n
entry_blocked_n
entry_parity_gate_pass
block_reason
```

### 11.10 c0_same_bar_conflict_audit.csv

Required columns:

```text
scope_id
split
upper_barrier_pct
lower_barrier_pct
horizon_sessions
complete_executable_event_n
same_bar_conflict_n
same_bar_conflict_rate
conflict_counted_as
```

`conflict_counted_as` must be `lower_first`.

### 11.11 c0_overlap_density_audit.csv

Required columns:

```text
scope_id
split
event_n
same_instrument_prior_c0_10d_rate
same_instrument_prior_c0_20d_rate
same_instrument_next_c0_20d_rate
overlap_with_other_c0_survival_window_mean
overlap_with_other_c0_survival_window_p95
selected_survival_candidate_label
```

## 12. Decision States

Valid final decision states:

```text
12A6_survival_threshold_candidates_supported
12A6_survival_threshold_candidates_partial
12A6_no_stable_survival_threshold
12A6_blocked_input_or_pit_failure
```

### 12.1 Supported

Output `12A6_survival_threshold_candidates_supported` only if:

```text
input gates pass
selected_candidate_status = pass
robustness_upper_first_rate_relative_to_train >= 0.70
robustness_lower_first_rate_minus_train <= 0.10
robustness_expected_r_multiple_proxy >= 0
board_or_regime_instability_flag = false
```

Next allowed requirement:

```text
requirement_12a7_c0_survival_meta_label_feasibility.md
```

### 12.2 Partial

Output `12A6_survival_threshold_candidates_partial` if:

```text
input gates pass
selected_candidate_status = pass
but one or more robustness / stability gates fail
and hard robustness failure is false
```

Next allowed requirement:

```text
requirement_12a6b_survival_scope_or_threshold_revision.md
```

### 12.3 No Stable Threshold

Output `12A6_no_stable_survival_threshold` if:

```text
input gates pass
no selected survival candidate satisfies train eligibility constraints
or hard robustness failure is true
```

Hard robustness failure is true if any condition holds:

```text
robustness_upper_first_rate_relative_to_train < 0.40
robustness_expected_r_multiple_proxy < -0.25
robustness_complete_executable_event_n < 300
selected_robustness_upper_first_rate < 0.05
```

Next allowed requirement:

```text
stop_c0_survival_as_primary_target_keep_diagnostic_only
```

### 12.4 Blocked

Output `12A6_blocked_input_or_pit_failure` if:

```text
required input missing
input schema mismatch
12A2 gate not supported
canonical_event_id not unique
price data missing for required instruments
PIT entry executability cannot be proven
```

## 13. Test Requirements

Unit tests must cover:

1. first-hit ordering with upper-first, lower-first, neutral, censored, and same-bar conflict cases;
2. lower-first priority when high and low cross barriers on the same daily bar;
3. event universe filter and uniqueness;
4. primary family enumeration excludes `B7` and emits only `B1,B2,B3,B4,B5,B6,B8`;
5. per-family rows are `diagnostic_only_flag = true` and `selection_eligible_flag = false`;
6. entry blocked / missing price handling;
7. train-only threshold selection with robustness readout unable to change selected thresholds;
8. raw `expected_r_multiple_proxy` is not the first candidate-ranking key;
9. horizon plateau uses one longest-horizon-complete cohort rather than horizon-specific denominators;
10. 06 / 11A2 enrichment uses `risk_on` baseline for headline rows and marks all-C0 rows diagnostic-only;
11. pre-success MAE calculation;
12. survivor killed by lower barrier calculation;
13. output schema presence for all publishable tables;
14. decision state mapping.

Minimum command:

```text
pytest -q topics/02_AFML_BIG_WINNER/experiments/pending/12_multi_k_winner_failure_path_morphology_research_v0/tests/test_12a6_c0_local_survival_episode_audit.py
```

## 14. Implementation Notes

1. Prefer vectorized per-instrument price path processing; do not loop over every event × grid cell with repeated CSV reads.
2. Read each instrument qfq CSV once, sort by date, and map `event_t0_pos` / `trade_open_pos` against actual price rows.
3. All price-derived labels are future outcomes and must never enter any t0 feature matrix.
4. Filter or stream the PIT membership file by required instrument/date keys; do not rely on full-file eager loading.
5. The report should keep the distinction between:
   - event-level survival outcome;
   - existing big-winner episode lifecycle;
   - future meta-labeling target.
6. The report must make clear that `continuation_60` from `labels.yaml` is an existing comparison label, while 12A6 selects survival upper / lower / horizon from audit statistics.
7. If generated row-level path matrices are large, keep them in `outputs/local_cache/` and publish only aggregate tables plus manifest hashes.
