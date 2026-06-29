# 需求：16E-postmortem Continuation Utility Failure Decomposition

## 0. Non-negotiable Scope

16E-postmortem 是 Episode 16 在 16E 裁决为 `not_supported` 之后插入的诊断 phase。它只在 16E 裁决为：

```text
16E_utility_diagnostic_not_supported
next_allowed_requirement = none
utility_interpretation = drawdown_reduction_only_return_not_supported
```

时允许运行。

16E-postmortem 的唯一任务是：在**完全不改动 16D policy、不改 threshold、不 refit model、不重选 action semantics、不计算任何新的 forward return / cost / drawdown / PnL** 的前提下，对 16E 已落地的 publishable utility tables 做**只读结构性分解**，回答一个问题：

```text
16E 的 not_supported 是来自一个"可修复的目标函数 / action 映射错配"（classify-then-bolt-on-utility mismatch），
还是来自一个"信号本身不携带可转化为 utility 的方向性"的根本性失败？
并据此在三条预注册 alternative-hypothesis 路径（A / B / C）中授权至多一条作为下一个 requirement。
```

16E-postmortem **不是**且**不授权**：

```text
new model / refit
new threshold / re-tuned threshold
new action semantics / new cost model
new forward-return / PnL / drawdown computation
entry policy / exit policy / holding policy
chained sequential simulation
portfolio construction / position sizing
production signal / deployment / live trading
16F chained action transition freeze
```

16E-postmortem 是**只读、零新 forward-return / cost / drawdown / refit 计算、纯分解**的诊断。它读取 16E（必要时 16D）已发布的 row-level utility panel 与 readout tables，重新组织/分组/统计，但**不得**产生任何新的 return、cost、drawdown 数值——所有 per-row utility 量必须来自 16E `utility_panel`（local parquet）或 publishable readouts 的复用，并通过 checksum / 聚合复算与 16E 对齐。允许的新量仅限于对既有列的分组聚合、分位数、比率、Spearman 相关和 boolean gate。

若 16E-postmortem 通过，最多只能授权后续新建以下三者**之一**：

```text
路径 A: requirement_16d_prime_utility_weighted_continuation_objective.md
路径 B: requirement_16e_overlay_risk_budget_continuation_readout.md
路径 C: requirement_16d_meta_continuation_participation_filter.md
```

或在证据不支持任何路径时，授权 `none`（即关闭 continuation-as-action 主线，回到 topic 级 research direction 讨论）。

## 1. Identity

```text
experiment_id = 16_winner_episode_sequential_sampling_geometry_preflight_v0
phase_id = 16E_postmortem
run_id = 16E_postmortem_continuation_utility_failure_decomposition
requirement_file = requirement_16e_postmortem_continuation_utility_failure_decomposition.md
config_file = configs/config_16e_postmortem_continuation_utility_failure_decomposition.yaml
runner_file = src/run_16e_postmortem_continuation_utility_failure_decomposition.py
test_file = tests/test_16e_postmortem_continuation_utility_failure_decomposition.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths in config should be repo-relative or resolver-alias based. Do not hard-code author-machine absolute paths.

## 2. Upstream Authorization Replay

16E-postmortem 必须复验 16E 的 not_supported 裁决，不得只读报告文本。

Required 16E values (from publishable tables / manifest, not report prose):

```text
decision_state = 16E_utility_diagnostic_not_supported
next_allowed_requirement = none
utility_interpretation = drawdown_reduction_only_return_not_supported
primary_label_id = continuation_survival_h20_no_deep_drawdown
selected_threshold_id = up50pct
primary_horizon_sessions = 20
primary_model_id = ridge_logistic_bar_state_v1
primary_policy_id = defense_bottom_30pct_continuation_score_v1
primary_action_semantics_id = full_avoidance_cash_h20_close_to_close_v1
primary_round_trip_defense_cost_bps = 50
threshold_value = 0.457071
primary_return_utility_gate = fail
drawdown_avoidance_gate = pass
delay_stress_gate = fail
context_power_gate = pass
context_utility_gate = fail
six_cell_reconciliation_gate = pass
search_accounting_gate = pass
```

Required 16E hard gates (all must have been pass except return/delay/context utility):

```text
input_artifact_gate = pass
upstream_16d_authorization_gate = pass
full_action_panel_rebuild_gate = pass
utility_price_path_gate = pass
action_semantics_gate = pass
policy_utility_binding_gate = pass
six_cell_reconciliation_gate = pass
neutral_utility_gate = pass
context_utility_rebuild_gate = pass
search_accounting_gate = pass
```

Required 16E authorization booleans (all false):

```text
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
chained_simulation_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

If 16E decision is NOT `16E_utility_diagnostic_not_supported`, this postmortem must fail closed:

```text
upstream_16e_authorization_gate = fail
decision_state = 16E_postmortem_blocked_by_input_or_lineage_failure
next_allowed_requirement = none
```

特别地：若 16E 裁决为 `cost_or_execution_fragile`、`context_concentrated_only`、`low_power`、
`ready_for_chained_action_transition_freeze`，本 postmortem 均**不适用**，必须 fail closed。
postmortem 只解释 `not_supported`。

## 3. Research Questions

16E-postmortem answers six diagnostic questions, all answerable from 16E frozen artifacts.

```text
PM-Q1. 失败的算术归因：在 50bps primary 下，full-denominator negative incremental utility
       有多少来自 defended_positive 的 opportunity cost，多少来自 continued_negative 的 residual loss，
       多少被 defended_negative + defended_neutral 的正向 utility 抵消？
       （纯六格重组，不引入新数值。）

PM-Q2. 厚尾错配诊断（机制核心）：被防住的 positive（defended_positive）的 realized upside 分布，
       相对于全体 positive 的 upside 分布，是否被系统性地偏向高分位？
       即 bottom-30% continuation score 是否倾向于把高 upside 的 positive 误判为低分？
       这检验 "0/1 label ranking 对厚尾上涨无差别惩罚" 这一结构假设。

PM-Q3. 单调性诊断：把 16E utility panel 的 primary-cost labelable rows 按既有 `score` 列
       分成十分位 score bucket，
       每个 bucket 的 mean continue_return_h20 是否随 score 单调上升、单调下降、还是非单调？
       若非单调或弱单调，说明 score 不携带稳定的方向性 utility（根本性失败信号）；
       若单调但 bottom-30% 仍 utility 为负，说明是 threshold / action 映射问题（可修复信号）。

PM-Q4. 分类价值 vs utility 价值 gap：16D 的 negative capture（train 0.4707 / robustness 0.3726）
       是真实分类能力，但 16E utility 为负。量化 "每单位 defended_negative avoided loss"
       对应的 "defended_positive sacrificed upside" 比率（loss-avoidance efficiency），
       在 train / robustness / 各 score bucket 下分别是多少？

PM-Q5. drawdown-only 残值定位：16E drawdown avoidance gate pass 但 return gate fail。
       drawdown 信息（defended_negative drawdown_avoided_abs）是否在某个 exposure 区间
       （而非 full avoidance）下可能产生正的 risk-adjusted 残值？
       这是一个 readout 性质的 feasibility 判断，不是新的 utility 计算。

PM-Q6. 路径授权决策：综合 PM-Q1..Q5，A / B / C 三条路径中，哪一条（至多一条）
       得到结构性证据支持？是否所有路径都不被支持（关闭主线）？
```

Decision mapping of questions:

```text
若 PM-Q3 在 train 或 robustness 单调性失败（score 不携带方向性 utility）
  -> 三路径均不支持，关闭主线。
若 PM-Q3 train+robustness 均单调，且 PM-Q2 显示厚尾错配 + PM-Q4 efficiency 可改善
  -> 授权路径 A（utility-weighted objective）。
若 PM-Q3 train+robustness 均单调，且 A 不成立，但 PM-Q5 显示 drawdown 残值在 partial exposure 下可行
  -> 授权路径 B（risk-budget overlay）。
若 PM-Q3 单调但无独立 entry source 假设，且 A/B 均不占优     -> 授权路径 C（meta-label participation filter）。
```

路径优先级（当多条同时被支持时，按此固定优先级选唯一一条，且优先级是预注册的，不得事后调整）：

```text
A > B > C
```

## 4. Allowed And Forbidden Work

16E-postmortem may:

1. 复验 16E not_supported 裁决与所有 16E 已发布 gates / booleans / numbers。
2. 读取 16E 的 row-level `utility_panel`（local parquet）与 publishable readout tables。
3. 对已有 per-row utility 量做**重组、分组、分位统计、比率计算**（PM-Q1..Q5）。
4. 按 16E panel 既有 `score` 列做 bucket 化的 readout（score decile / quantile）。
5. 对每条路径输出一个 boolean `path_supported` + 证据摘要。
6. 在 A > B > C 优先级下授权**至多一条** alternative-hypothesis requirement。
7. 若无路径被支持，授权 `none` 并标注 `continuation_as_action_mainline_closed = true`。

16E-postmortem must not:

1. 重新计算任何 forward return / cost / drawdown / PnL（所有数值必须复用 16E artifact 并 checksum 对齐）。
2. refit / re-train 任何 model，或改变 16C score、16D threshold（0.457071）、16D policy id。
3. 重选 / 新增 action semantics、cost tier、delay rule。
4. 定义或评估任何 entry / exit / holding rule。
5. 模拟任何 chained policy 或 portfolio。
6. 使用 validation 的结果去"选择"被授权的路径，或使用 robustness 结果调参 / 改阈值 / 改 gate。
   路径授权只能由预注册的 §3 decision mapping 在 train + robustness diagnostic 上触发；
   robustness 是预注册 confirmatory split，可参与 path gate，但不得用于事后选择阈值、bucket 数、
   action semantics 或 gate cutoff。validation 只能作为 stress readout，不参与 path gate。
7. 把 drawdown-only 残值（PM-Q5）解释成可交易的 risk overlay——PM-Q5 只是 feasibility readout，
   真正的 overlay utility 必须留给被授权后的路径 B requirement 重新计算。
8. 直接授权 16F 或任何 chained / entry / deployment 工作。
9. 声称任何 live / simulated / deployable trading performance。

## 5. Required Inputs

All required inputs must enter `input_artifact_audit.csv` with:

```text
artifact_key
resolved_path
row_count
sha256
schema_status
read_status
required_flag
lineage_role
blocking_reason
```

Missing or schema-failing required inputs fail closed.

### 5.1 16E Publishable Inputs

```text
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/sequential_continuation_utility_decision.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/upstream_16d_authorization_audit.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/single_step_action_semantics_audit.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/six_cell_utility_reconciliation.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/utility_by_split_readout.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/utility_by_context_readout.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/positive_sacrifice_utility_readout.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/negative_avoidance_utility_readout.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/continued_negative_leakage_utility_readout.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/neutral_utility_readout.csv
outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/search_accounting_audit.csv
outputs/manifests/16E_sequential_continuation_utility_diagnostic_manifest.json
```

### 5.2 16E Row-level Utility Panel

postmortem 的分位 / 单调性 / 厚尾分解需要 row-level utility，但**只能复用** 16E 已生成的 panel：

```text
outputs/local_cache/16E_sequential_continuation_utility_diagnostic/utility_panel.parquet
```

This local parquet is the **only** allowed row-level source. If missing, 16E-postmortem must fail closed
(it must NOT rebuild it by re-running 16E full mode, because that would recompute utility):

```text
if utility_panel.parquet missing:
  row_level_panel_gate = fail
  decision_state = 16E_postmortem_blocked_by_input_or_lineage_failure
  next_allowed_requirement = none
```

If present, it may be used only after proving (no new numbers, only validation):

```text
row keys are unique at (policy_id, step_id, cost_bps)
primary-cost row keys are unique at (policy_id, step_id) after filtering cost_bps == 50
policy_id == defense_bottom_30pct_continuation_score_v1
threshold_value == 0.457071 within tolerance
cluster_split_bucket column present with values in {train, robustness, validation}
score column present and finite for labelable rows
score is inherited from 16D via 16E utility_panel passthrough; postmortem must not recompute score
candidate_action present and in {defend_next_h20, continue_next_h20}
per-row continue_return_h20, continue_max_drawdown_h20, policy_net_return_h20,
  incremental_net_return_h20, drawdown_avoided_abs, cost_bps, cell_id present
postmortem normalizes panel.cluster_split_bucket -> split_bucket before aggregation
  and records that rename in derived_metric_lineage_audit.csv as allowed_transform_type = column_rename
aggregate replay: sum(panel.incremental_net_return_h20) grouped by
  (split_bucket, cost_bps) reproduces
  utility_by_split_readout.full_denominator_sum_incremental_return within tolerance
aggregate replay: six-cell re-grouping reproduces 16E six_cell_utility_reconciliation within tolerance
```

If aggregate replay fails, fail closed. postmortem must never compute on a panel that disagrees with 16E.

### 5.3 16D Lineage Inputs (read-only)

仅用于复验 score 与 policy 血缘，不得 refit / 改 threshold：

```text
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/sequential_continuation_policy_preflight_decision.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_threshold_freeze_audit.csv
outputs/publishable/tables/16D_sequential_continuation_policy_preflight/policy_confusion_readout.csv
```

## 6. No-new-computation Contract

This is the central discipline of 16E-postmortem.

```text
no_new_forward_return_computed = true
no_new_cost_computed = true
no_new_drawdown_computed = true
no_model_refit = true
no_threshold_change = true
no_action_semantics_added = true
all per-row utility values sourced from 16E utility_panel.parquet
all aggregate utility values reconciled against 16E publishable readouts within tolerance
```

postmortem 允许产生的**新**量仅限于：对既有 per-row 值的**分组聚合、分位边界、比率、单调性统计、相关性**。
任何看起来像"新的 return 数字"的输出，都必须能追溯回 16E panel 的既有列的纯算术变换。

`no_new_computation_audit.csv` 必须逐项声明上述 boolean，并对每个 postmortem 派生量记录其来源列。
若任一 boolean 不成立：

```text
no_new_computation_gate = fail
decision_state = 16E_postmortem_blocked_by_recomputation_violation
next_allowed_requirement = none
```

## 7. Failure Decomposition Formulae

所有量均为对 16E 既有 per-row 值的纯重组。primary split = robustness（与 16E 一致），train 为支持读数，
validation 仅 stress readout。primary cost = 50bps。

For row-level PM-Q2..PM-Q5 diagnostics, define:

```text
primary_panel = utility_panel where cost_bps == 50
split_bucket = cluster_split_bucket renamed from the 16E panel column
score_column = score
labelable rows = all rows in primary_panel with finite score and label_class in {positive, negative, neutral}
binary rows = label_class in {positive, negative}
score deciles are split-local quantile buckets over labelable rows, ordered low score -> high score.
```

Never run score-bucket or thick-tail diagnostics on all four cost tiers at once; that would duplicate each
row four times.

### 7.1 Arithmetic Attribution (PM-Q1)

For each `(split, cost_bps)`:

```text
full_denominator_net_utility_total = full_denominator_sum_incremental_return
  (from 16E, must reconcile)

Use panel.cell_id as the only six-cell assignment source:
  defended_positive, defended_negative, defended_neutral,
  continued_positive, continued_negative, continued_neutral

defended_positive_oppcost = - sum(incremental_net_return_h20 over defended_positive rows)
defended_negative_gain     = sum(incremental_net_return_h20 over defended_negative rows)
defended_neutral_gain       = sum(incremental_net_return_h20 over defended_neutral rows)
continued_negative_residual = sum(max(0, -continue_return_h20) over continued_negative rows)

attribution_identity_check:
  defended_positive_incremental_sum
  + defended_negative_incremental_sum
  + defended_neutral_incremental_sum
  == full_denominator_net_utility_total
  (within tolerance; continued cells contribute 0 incremental by construction)

continued_incremental_zero_check:
  abs(sum(incremental_net_return_h20 over continued_positive rows)) <= tolerance
  abs(sum(incremental_net_return_h20 over continued_negative rows)) <= tolerance
  abs(sum(incremental_net_return_h20 over continued_neutral rows)) <= tolerance

six_cell_bidirectional_replay:
  panel groupby (split_bucket, context_stratum = all_steps, cost_bps, cell_id)
  for cell_step_n, continue_return_sum, policy_net_return_sum,
  incremental_return_sum, drawdown_avoided_abs_sum
  must match six_cell_utility_reconciliation.csv within tolerance.
```

### 7.2 Thick-tail Mismatch Diagnostic (PM-Q2)

```text
For all positive rows (label_class == positive), take continue_return_h20.
Compute upside distribution quantiles q50, q75, q90, q95 over ALL positive rows.

For defended_positive rows only, compute the same quantiles.

defended_positive_upside_mean_ratio =
  defended_positive.upside_mean / max(all_positive.upside_mean, epsilon)

defended_positive_upside_q75_ratio =
  defended_positive.upside_q75 / max(all_positive.upside_q75, epsilon)

defended_positive_upside_q90_vs_all_q75_flag =
  defended_positive.upside_q90 >= all_positive.upside_q75

thick_tail_mismatch_flag = true if any of:
  defended_positive_upside_mean_ratio >= 0.80
  defended_positive_upside_q75_ratio >= 0.80
  defended_positive_upside_q90_vs_all_q75_flag == true

These thresholds are pre-registered and apply independently within train and robustness.
Validation may report the same readout but cannot set the path gate.

Report both distributions; do not reduce to a single scalar verdict without the quantile table.
```

### 7.3 Score-bucket Monotonicity (PM-Q3)

```text
Bucket labelable rows in primary_panel by existing score column into deciles (10 buckets),
split-local, low score -> high score, no refit and no score recomputation.
For each decile:
  decile_index
  score_low, score_high
  row_n
  binary_step_n
  positive_n, negative_n, neutral_n
  mean_continue_return_h20
  mean_continue_max_drawdown
  base_rate_positive

monotonicity_spearman = Spearman rank corr between decile_index and mean_continue_return_h20
monotone_increasing_flag = monotonicity_spearman >= +0.6   (score high -> return high; expected if signal directional)
non_monotone_flag        = abs(monotonicity_spearman) < 0.3
inverted_flag            = monotonicity_spearman <= -0.6
robustness_monotonicity_unstable_caveat = true if
  split_bucket == robustness
  AND monotonicity_spearman >= +0.3
  AND monotonicity_spearman < +0.6
```

解释：

```text
若 train 和 robustness 均 monotone_increasing_flag，且 bottom-three deciles 中存在负 mean return
  -> 信号有方向性，问题在 threshold / action 映射 -> 利好路径 A。
若 train 或 robustness 任一 non_monotone_flag
  -> 信号不携带稳定方向性 utility -> 三路径均不支持，关闭主线。
若 robustness_monotonicity_unstable_caveat
  -> 仍不授权 A/B/C，因 directionality_gate 未通过；但报告必须区分
     "明确非单调" 与 "robustness 方向性不足以过 gate"。
若 train 或 robustness 任一 inverted_flag
  -> score orientation 与 16D 假设矛盾 -> lineage 复核失败，fail closed 转 lineage failure。
```

### 7.4 Loss-avoidance Efficiency (PM-Q4)

```text
For each split and score decile in primary_panel:
  avoided_loss_abs = sum(max(0, -continue_return_h20) over defended_negative rows)
  sacrificed_upside_abs = sum(max(0, continue_return_h20) over defended_positive rows)
  loss_avoidance_efficiency = avoided_loss_abs / max(sacrificed_upside_abs, epsilon)

candidate_defend_region_deciles = {1, 2, 3}  (the frozen bottom-30% region, low score -> high score)

efficiency_above_one_in_any_bucket_flag = true if:
  train has at least one non-low-power candidate_defend_region_decile with loss_avoidance_efficiency > 1.0
  AND robustness has at least one non-low-power candidate_defend_region_decile with loss_avoidance_efficiency > 1.0
```

解释：

```text
若 efficiency 在 score 最低 bucket 明显 > 1.0，但 bottom-30% 整体 < 1.0
  -> 说明更窄的 defend region 可能 utility-positive -> 利好路径 A 的 severity-aware / asymmetric threshold。
```

### 7.5 Drawdown Residual Feasibility (PM-Q5, readout only)

```text
For defended_negative rows, the 16E panel already has drawdown_avoided_abs and continue_return_h20.
Compute a hypothetical PARTIAL-exposure incremental WITHOUT new return computation by
  linear scaling of existing per-row continue_return_h20 at exposure levels e in {0.25, 0.5, 0.75}:
    partial_incremental(e) = (1 - e) * (-continue_return_h20) - e * 0   ... NO: this would be new utility.

This is forbidden. Instead PM-Q5 must ONLY report, from existing columns:
  defended_negative drawdown_avoided_abs distribution
  defended_positive continue_return_h20 distribution
and emit a boolean feasibility hint:
  partial_exposure_feasibility_hint = true if
    train and robustness defended_negative drawdown_avoided_abs median are both >= 0.10
    AND train and robustness defended_positive continue_return_h20 median are both <= 0.08
    AND train and robustness defended_negative_drawdown_to_positive_upside_median_ratio are both >= 1.50
  i.e. the rows we defend have deep drawdowns but modest upside, suggesting a graded
  exposure (path B) is worth a dedicated requirement.

partial_exposure utility itself is NOT computed here; it is deferred to path B requirement.
```

> 注意：§7.5 的设计刻意禁止任何 partial-exposure utility 重算。postmortem 只允许从 16E 既有列读出
> drawdown 与 upside 的分布形状，给出一个 feasibility hint boolean；真正的 overlay utility 必须在
> 路径 B 被授权后由新 requirement 重新、显式、可审计地计算。

## 8. Path Support Gates

每条路径输出一个 `path_supported` boolean + evidence 摘要。路径授权遵循 §3 decision mapping 与 A>B>C 优先级。

Before evaluating A/B/C:

```text
directionality_gate = pass if
  train_monotone_increasing_flag == true
  AND robustness_monotone_increasing_flag == true
  AND train_non_monotone_flag == false
  AND robustness_non_monotone_flag == false
  AND train_inverted_flag == false
  AND robustness_inverted_flag == false

if directionality_gate != pass:
  path_a_supported = false
  path_b_supported = false
  path_c_supported = false
  mainline_closed = true
```

### 8.1 Path A — Utility-weighted / severity-aware continuation objective

```text
path_a_supported = true if
  directionality_gate == pass
  AND thick_tail_mismatch_flag == true
  AND efficiency_above_one_in_any_bucket_flag == true
```

含义：信号有方向性，但 0/1 label 训练导致厚尾上涨被误防，且存在更优 defend region。
授权 `requirement_16d_prime_utility_weighted_continuation_objective.md`。

### 8.2 Path B — Risk-budget / graded-exposure overlay

```text
path_b_supported = true if
  directionality_gate == pass
  AND path_a_supported == false
  AND drawdown_avoidance_gate (from 16E) == pass
  AND partial_exposure_feasibility_hint == true
```

含义：drawdown 信息真实，被防的行是"深回撤、薄上涨"，graded exposure 值得专门评估。
授权 `requirement_16e_overlay_risk_budget_continuation_readout.md`。

### 8.3 Path C — Meta-label participation filter

```text
path_c_supported = true if
  directionality_gate == pass
  AND path_a_supported == false
  AND path_b_supported == false
```

含义：信号有方向性但既不适合改 objective 也不适合 overlay，更适合作为 meta-labeling secondary
filter，配合未来的独立 entry source（当前 topic 尚无 entry alpha，故路径 C 仅在 A/B 都不成立时备选）。
授权 `requirement_16d_meta_continuation_participation_filter.md`。

### 8.4 Mainline closure

```text
mainline_closed = true if
  directionality_gate != pass
  OR (path_a_supported == false AND path_b_supported == false AND path_c_supported == false)
```

授权 `none`，并在 decision CSV 与报告中标注 `continuation_as_action_mainline_closed = true`，
建议回到 topic 级 research direction 讨论（参考 `research_direction_discussion_20260614.md`）。

## 9. Support Gates

### 9.1 Hard Lineage Gates

All must pass:

```text
input_artifact_gate = pass
upstream_16e_authorization_gate = pass
row_level_panel_gate = pass
panel_aggregate_replay_gate = pass
no_new_computation_gate = pass
attribution_identity_gate = pass
score_orientation_consistency_gate = pass
search_accounting_gate = pass
```

Any hard lineage fail maps to:

```text
16E_postmortem_blocked_by_input_or_lineage_failure
```

except recomputation violation, which maps to:

```text
16E_postmortem_blocked_by_recomputation_violation
```

except inverted score orientation (PM-Q3 inverted_flag), which maps to:

```text
16E_postmortem_blocked_by_input_or_lineage_failure
（because inverted orientation contradicts 16D score_orientation_gate = pass）
```

### 9.2 Power Gates

postmortem 的分位 / efficiency 统计需要每个 score bucket 足够样本：

```text
train_binary_step_n >= 10000
train_defended_positive_n >= 1000
train_defended_negative_n >= 1000
robustness_binary_step_n >= 1000
robustness_defended_positive_n >= 100
robustness_defended_negative_n >= 100
min_rows_per_score_decile_train >= 200
min_rows_per_score_decile_robustness >= 30
```

Validation 仅 stress readout：

```text
validation_binary_step_n >= 300
```

若 robustness 单 decile 样本不足，对应 decile efficiency 标 `decile_low_power = true` 但不阻塞整体裁决，
除非 monotonicity Spearman 因样本过少无法估计——此时：

```text
decision_state = 16E_postmortem_low_power
next_allowed_requirement = none
```

### 9.3 Search Accounting Gates

```text
primary_policy_id inherited from 16D, unchanged
threshold_value == 0.457071 unchanged
no_model_refit = true
no_new_action_semantics = true
path_priority_A_gt_B_gt_C_preregistered = true
validation_used_for_path_selection = false
robustness_used_as_confirmatory_path_gate = true
robustness_used_for_threshold_tuning = false
```

Any violation maps to:

```text
16E_postmortem_blocked_by_recomputation_violation
```

## 10. Outputs

All publishable tables must be written under:

```text
outputs/publishable/tables/16E_postmortem_continuation_utility_failure_decomposition/
```

Required publishable tables:

```text
input_artifact_audit.csv
upstream_16e_authorization_audit.csv
no_new_computation_audit.csv
derived_metric_lineage_audit.csv
panel_aggregate_replay_audit.csv
failure_arithmetic_attribution.csv
defended_positive_thick_tail_readout.csv
score_bucket_monotonicity_readout.csv
loss_avoidance_efficiency_by_bucket.csv
drawdown_residual_feasibility_readout.csv
path_support_decision.csv
search_accounting_audit.csv
continuation_utility_failure_postmortem_decision.csv
```

Local cache outputs (optional, read-derived only):

```text
outputs/local_cache/16E_postmortem_continuation_utility_failure_decomposition/postmortem_grouping.parquet
```

Report:

```text
outputs/publishable/reports/continuation_utility_failure_postmortem_report.md
```

Manifest:

```text
outputs/manifests/16E_postmortem_continuation_utility_failure_decomposition_manifest.json
```

## 11. Required Table Schemas

### 11.1 `input_artifact_audit.csv`

Minimum columns:

```text
artifact_key
resolved_path
row_count
sha256
schema_status
read_status
required_flag
lineage_role
blocking_reason
```

### 11.2 `upstream_16e_authorization_audit.csv`

Minimum columns:

```text
upstream_16e_decision_state
upstream_16e_next_allowed_requirement
upstream_16e_utility_interpretation
primary_policy_id
primary_action_semantics_id
primary_round_trip_defense_cost_bps
threshold_value
primary_return_utility_gate
drawdown_avoidance_gate
delay_stress_gate
context_power_gate
context_utility_gate
six_cell_reconciliation_gate
search_accounting_gate
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
chained_simulation_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
upstream_16e_authorization_gate
blocking_reason
```

### 11.3 `panel_aggregate_replay_audit.csv`

Minimum columns:

```text
replay_key
split_bucket
cost_bps
source_table
source_value_column
panel_groupby_columns
panel_value_column
source_value
panel_replay_value
abs_diff
tolerance
replay_status
blocking_reason
```

### 11.4 `no_new_computation_audit.csv`

Minimum columns:

```text
no_new_forward_return_computed
no_new_cost_computed
no_new_drawdown_computed
no_model_refit
no_threshold_change
no_action_semantics_added
all_per_row_values_sourced_from_16e_panel
all_aggregates_reconciled_within_tolerance
forbidden_computation_detected_n
derived_metric_lineage_complete
no_new_computation_gate
blocking_reason
```

### 11.5 `derived_metric_lineage_audit.csv`

One row per postmortem-derived metric family:

```text
derived_metric_id
output_table
source_artifact_key
source_columns
allowed_transform_type
creates_new_return_cost_or_drawdown
lineage_status
blocking_reason
```

### 11.6 `failure_arithmetic_attribution.csv`

```text
split_bucket
cost_bps
full_denominator_net_utility_total
defended_positive_incremental_sum
defended_negative_incremental_sum
defended_neutral_incremental_sum
continued_positive_incremental_sum
continued_negative_incremental_sum
continued_neutral_incremental_sum
continued_negative_residual_loss_abs
defended_positive_oppcost_share
defended_negative_gain_share
defended_neutral_gain_share
attribution_identity_abs_diff
attribution_identity_status
continued_incremental_zero_abs_max
continued_incremental_zero_status
six_cell_bidirectional_replay_status
```

### 11.7 `defended_positive_thick_tail_readout.csv`

```text
split_bucket
population
row_n
upside_mean
upside_q25
upside_q50
upside_q75
upside_q90
upside_q95
defended_positive_upside_mean_ratio
defended_positive_upside_q75_ratio
defended_positive_upside_q90_vs_all_q75_flag
thick_tail_mismatch_flag
```

`population` ∈ {all_positive, defended_positive}.

### 11.8 `score_bucket_monotonicity_readout.csv`

```text
split_bucket
decile_index
score_column
score_low
score_high
row_n
binary_step_n
positive_n
negative_n
neutral_n
base_rate_positive
mean_continue_return_h20
mean_continue_max_drawdown
decile_low_power
monotonicity_spearman
monotone_increasing_flag
non_monotone_flag
inverted_flag
robustness_monotonicity_unstable_caveat
```

`monotonicity_spearman` / flags repeated per split (constant across decile rows of same split).

### 11.9 `loss_avoidance_efficiency_by_bucket.csv`

```text
split_bucket
decile_index
cost_bps
candidate_defend_region_flag
defended_negative_n
defended_positive_n
avoided_loss_abs
sacrificed_upside_abs
loss_avoidance_efficiency
decile_low_power
efficiency_above_one_flag
```

### 11.10 `drawdown_residual_feasibility_readout.csv`

```text
split_bucket
defended_negative_n
defended_negative_drawdown_avoided_abs_median
defended_negative_drawdown_avoided_abs_mean
defended_positive_continue_return_h20_median
defended_positive_continue_return_h20_mean
defended_negative_drawdown_to_positive_upside_median_ratio
partial_exposure_feasibility_hint
feasibility_note
```

### 11.11 `path_support_decision.csv`

```text
path_id
path_requirement_file
path_supported
directionality_gate
support_evidence_summary
path_priority_rank
selected_path_flag
```

`path_id` ∈ {A, B, C, none}.

### 11.12 `search_accounting_audit.csv`

```text
primary_policy_id
threshold_value
no_model_refit
no_threshold_change
no_new_action_semantics
path_priority_A_gt_B_gt_C_preregistered
validation_used_for_path_selection
robustness_used_as_confirmatory_path_gate
robustness_used_for_threshold_tuning
search_accounting_gate
blocking_reason
```

### 11.13 `continuation_utility_failure_postmortem_decision.csv`

```text
decision_state
next_allowed_requirement
upstream_16e_decision_state
upstream_16e_utility_interpretation
primary_policy_id
primary_action_semantics_id
directionality_gate
train_monotonicity_spearman
robustness_monotonicity_spearman
robustness_monotonicity_unstable_caveat
train_monotone_increasing_flag
robustness_monotone_increasing_flag
train_non_monotone_flag
robustness_non_monotone_flag
train_inverted_flag
robustness_inverted_flag
thick_tail_mismatch_flag
efficiency_above_one_in_any_bucket_flag
partial_exposure_feasibility_hint
path_a_supported
path_b_supported
path_c_supported
selected_path_id
continuation_as_action_mainline_closed
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
chained_simulation_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

## 12. Decision Map

Final decision enum:

```text
16E_postmortem_path_a_utility_weighted_objective_authorized
16E_postmortem_path_b_risk_budget_overlay_authorized
16E_postmortem_path_c_meta_label_participation_filter_authorized
16E_postmortem_mainline_closed_no_path_supported
16E_postmortem_low_power
16E_postmortem_blocked_by_input_or_lineage_failure
16E_postmortem_blocked_by_recomputation_violation
```

Decision logic:

```text
if any forbidden recomputation / refit / threshold change / action semantics addition:
  decision_state = 16E_postmortem_blocked_by_recomputation_violation
  next_allowed_requirement = none

elif any hard lineage gate fails (incl. panel replay, attribution identity, inverted orientation):
  decision_state = 16E_postmortem_blocked_by_input_or_lineage_failure
  next_allowed_requirement = none

elif score-bucket monotonicity cannot be estimated due to power:
  decision_state = 16E_postmortem_low_power
  next_allowed_requirement = none

elif mainline_closed:
  decision_state = 16E_postmortem_mainline_closed_no_path_supported
  next_allowed_requirement = none
  continuation_as_action_mainline_closed = true

elif path_a_supported:
  decision_state = 16E_postmortem_path_a_utility_weighted_objective_authorized
  next_allowed_requirement = requirement_16d_prime_utility_weighted_continuation_objective.md
  selected_path_id = A

elif path_b_supported:
  decision_state = 16E_postmortem_path_b_risk_budget_overlay_authorized
  next_allowed_requirement = requirement_16e_overlay_risk_budget_continuation_readout.md
  selected_path_id = B

elif path_c_supported:
  decision_state = 16E_postmortem_path_c_meta_label_participation_filter_authorized
  next_allowed_requirement = requirement_16d_meta_continuation_participation_filter.md
  selected_path_id = C

else:
  decision_state = 16E_postmortem_mainline_closed_no_path_supported
  next_allowed_requirement = none
```

Regardless of decision:

```text
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
chained_simulation_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

postmortem 至多授权写一个下一阶段 requirement 文件，且绝不授权任何 live / simulated / chained / entry / deployment 工作。

## 13. Report Requirements

The Chinese report must include:

1. 单行 decision and next allowed requirement（含 selected_path_id 或 mainline_closed）。
2. 16E not_supported 裁决复验与精确数字（return gate fail / drawdown gate pass / context fail）。
3. No-new-computation 声明：postmortem 未产生任何新 return / cost / drawdown / refit。
4. Column lineage：`cluster_split_bucket -> split_bucket` rename、`score` 16D passthrough、
   `incremental_net_return_h20 -> full_denominator_sum_incremental_return` aggregate replay。
5. PM-Q1 失败算术归因：panel.cell_id 六格 incremental、continued 三格 zero-incremental 子检查、
   与 six_cell_utility_reconciliation.csv 的双向对账。
6. PM-Q2 厚尾错配：defended_positive vs all_positive upside 分位对比表。
7. PM-Q3 score-bucket 单调性：十分位 mean continue return + Spearman +
   monotone / non_monotone / inverted directionality flags +
   `robustness_monotonicity_unstable_caveat`。
8. PM-Q4 loss-avoidance efficiency by bucket。
9. PM-Q5 drawdown 残值 feasibility hint（明确标注：未计算 partial-exposure utility）。
10. 三路径 path_supported 证据与 A>B>C 优先级裁决。
11. 若 mainline_closed：明确建议回到 topic 级 research direction；若 robustness caveat 为 true，
    必须区分"明确非单调"与"方向性不足以过 robustness gate"。
12. Search accounting：无 OOS path selection、无 refit、无 threshold change。
13. Findings and insight：classify-then-bolt-on mismatch 是否被结构性证据支持。

Report must explicitly state:

```text
16E-postmortem does not compute new returns, does not refit any model, does not change any threshold,
and does not authorize entry, exit, holding, chained simulation, deployment, or live trading.
It authorizes at most one alternative-hypothesis requirement (A / B / C) or closes the mainline.
```

## 14. Manifest Requirements

Manifest must include:

```text
experiment_id
phase_id
run_id
created_at
requirement_path
requirement_sha256
config_path
config_sha256
upstream_16e_decision
upstream_16e_utility_interpretation
primary_policy_id
primary_action_semantics_id
threshold_value
decision_state
next_allowed_requirement
selected_path_id
continuation_as_action_mainline_closed
monotonicity_spearman_by_split
robustness_monotonicity_unstable_caveat
no_new_computation_audit_summary
authorization_booleans
input_artifact_hashes
output_hashes
row_counts
large_artifact_policy
```

## 15. Implementation Pattern

Implementation should remain experiment-local and may reuse existing runners via importlib:

```text
16E runner helpers for path resolution, hashing, table writing, and panel schema
16D runner helpers only for score / threshold lineage replay (no refit)
```

No shared-package refactor is required.

postmortem 只读 16E `utility_panel.parquet` 与 publishable readouts。它不得调用 16E / 16D 的 full mode，
不得写入 16E / 16D 的任何 publishable / cache / manifest artifact。它只写自己的 postmortem 目录。

Large groupings should be stored as local parquet. Publishable tables remain small aggregate readouts.

## 16. Test Plan

Implement focused synthetic tests covering:

```text
test_16e_not_supported_required_for_postmortem
test_16e_other_decisions_fail_closed
test_16e_utility_panel_required_and_must_validate
test_panel_cluster_split_bucket_renamed_to_split_bucket_with_lineage
test_score_column_is_16d_passthrough_not_recomputed
test_missing_panel_fails_closed_does_not_rebuild
test_panel_incremental_net_return_replay_matches_16e_split_readout
test_panel_six_cell_replay_uses_cell_id_and_matches_16e_six_cell_readout
test_no_new_forward_return_or_cost_or_drawdown_computed
test_no_model_refit_no_threshold_change_no_new_action_semantics
test_attribution_identity_six_cells_sum_to_net_utility_total
test_continued_cells_incremental_sum_zero_within_tolerance
test_thick_tail_readout_uses_existing_continue_return_only
test_score_bucket_monotonicity_spearman_and_flags
test_robustness_monotonicity_unstable_caveat_when_spearman_between_0_3_and_0_6
test_inverted_orientation_maps_to_lineage_failure
test_non_monotone_maps_to_mainline_closed
test_loss_avoidance_efficiency_by_bucket
test_drawdown_residual_feasibility_is_readout_only_no_partial_utility
test_partial_exposure_utility_computation_is_forbidden
test_path_a_support_condition
test_path_b_support_condition
test_path_c_support_condition_only_when_a_and_b_false
test_path_priority_a_gt_b_gt_c_when_multiple_supported
test_mainline_closed_when_no_path_supported
test_low_power_when_monotonicity_unestimable
test_validation_not_used_for_path_selection
test_all_required_publishable_outputs_have_declared_schema
test_decision_map_recomputation_violation
test_decision_map_lineage_failure
test_decision_map_low_power
test_decision_map_path_a
test_decision_map_path_b
test_decision_map_path_c
test_decision_map_mainline_closed
test_all_trading_deployment_and_chained_sim_authorizations_false
test_manifest_contains_input_hashes_and_report_hash
test_postmortem_does_not_write_16e_or_16d_artifacts
```

## 17. Validation Commands

From `topics/02_AFML_BIG_WINNER`:

```bash
python -m py_compile experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_postmortem_continuation_utility_failure_decomposition.py
python -m pytest experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/tests/test_16e_postmortem_continuation_utility_failure_decomposition.py -q
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_postmortem_continuation_utility_failure_decomposition.py --mode check-inputs
python experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/src/run_16e_postmortem_continuation_utility_failure_decomposition.py --mode full
git diff --check
```

After full run, confirm no 16E / 16D publishable, cache, or manifest artifact was modified.

## 18. Expected Caveats To Carry Forward

16E-postmortem must carry these inherited caveats:

```text
16B soft_overlap_partial_coverage_caveat = true
16B known_failed_context_exposure_caveat = true
16C neutral_population_caveat = true
16C validation_stress_evaluable = true but validation is not a selection split
16D robustness defense rate coverage caveat = true (robustness defense rate ~21.21% < train 30.00%)
16E drawdown_reduction_only_return_not_supported interpretation inherited
16E continued_negative_leakage_caveat context inherited (residual loss share robustness ~1.64)
```

## 19. Boundary Restatement

```text
16E-postmortem 是只读、零新 forward-return / cost / drawdown / refit 计算、纯结构性分解的诊断 phase。
它解释 16E 为何 not_supported，并在预注册的 A>B>C 优先级下授权至多一条 alternative-hypothesis requirement，
或在证据不支持时关闭 continuation-as-action 主线。
它绝不计算新的 return / cost / drawdown，绝不 refit / 改 threshold / 加 action semantics，
绝不授权 16F / chained simulation / entry / exit / holding / portfolio / deployment / live trading。
```
