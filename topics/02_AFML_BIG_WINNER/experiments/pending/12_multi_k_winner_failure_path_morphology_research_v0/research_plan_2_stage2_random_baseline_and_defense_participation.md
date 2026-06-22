# Research Plan 2: Stage-2 Baseline Triage and Defense-Participation Frontier

## 0. 阶段定位

本计划承接以下已完成实跑结论：

- `12A6c_two_stage_fast_fail_rejector_continuation_feasibility`：模型排序能力存在，但 train-frozen absolute threshold 跨 split 运输失败，stage-1 / stage-2 threshold health 均失败。
- `12A7_direction_a_trailing_rank_operating_point_audit`：PIT trailing-rank 能把 absolute threshold transport failure 拆成可审计的 rank operating point。
- `12A7b_direction_c_simple_backbone_operating_rule_validation`：stage-1 simple backbone `volatility_20d asc, X=0.30` 已获得支持，低容量单调模型未能稳定击败 simple backbone。
- `12A7c_direction_e_stage2_decoupling_chained_readouts`：stage-2 continuation signal 存在，但 chained deployable readout 被 matched random replay 覆盖门卡住，不能升级为 deployable selector。

本计划不是新的 implementation requirement，而是 12A7 之后的研究路线修订。核心判断：

```text
Stage-1 downside defense is supported.
Stage-2 big-winner continuation remains unresolved.
The next work must separate baseline-construction failure from true signal failure,
then quantify whether aggressive defense is destroying winner participation.
```

## 1. 当前已落袋资产

### 1.1 Stage-1 simple backbone 已支持

当前唯一 deployable-grade 资产是：

```text
stage = 1
rule = volatility_20d ascending
X = 0.30
history_policy = PIT trailing-rank
scope = C0 risk_on, stage-1 evaluable events
decision_state = 12A7b_simple_backbone_supported_low_capacity_not_supported
```

关键 robustness 读数：

| metric | value |
|---|---:|
| selected_n | 1476 |
| selected_budget_total | 31.68% |
| budget_abs_delta_rank_evaluable_vs_X | 1.80pp |
| selected fast_fail_rate | 14.30% |
| base fast_fail_rate | 30.59% |
| delta_vs_random_p50 | -8.20pp |
| delta_vs_random_p50 95% CI | [-9.96pp, -6.37pp] |

解释：

- 这是 downside path defense，不是 winner alpha。
- validation 的 budget drift 仍然存在，但 robustness 上 budget drift 可控、random uplift 显著、rank coverage 风险低。
- 复杂模型和 low-capacity monotone 模型没有提供足够 out-of-train 边际收益。

### 1.2 Stage-2 continuation 信号仍悬空

12A7c 的关键读数：

| readout | split | selected rate | base rate | random p50 | valid seeds | status |
|---|---|---:|---:|---:|---:|---|
| decoupled survivor | robustness | 19.29% | 13.45% | 10.71% | 29 | random_replay_failed |
| chained survivor | robustness | 12.90% | 9.33% | NA | 0 | random_replay_failed |

解释：

- decoupled 视角说明真 no-fast-fail survivor 内部存在 continuation ranking signal。
- chained 视角更接近部署，但 current matched random baseline 无法构造出有效 p50 / CI。
- 因此 12A7c 的 block 是 baseline-construction failure，不是 continuation signal collapse。

### 1.3 Defense opportunity cost 已经显性化

12A7c opportunity-cost audit 显示：

| split | ground-truth survivor continuation | chained survivor continuation | chained share of survivor | continuation delta |
|---|---:|---:|---:|---:|
| train | 15.60% | 12.20% | 32.77% | -3.40pp |
| validation | 8.66% | 8.06% | 54.15% | -0.60pp |
| robustness | 13.45% | 9.33% | 39.12% | -4.12pp |

解释：

```text
Stage-1 simple backbone lowers fast-fail risk,
but it also removes a large fraction of true no-fast-fail survivors.
For a BIG_WINNER objective, aggressive defense may be too narrow.
```

## 2. Strategic Question

12-series 当前必须先回答一个战略问题：

```text
Is this system primarily a downside-protection overlay,
or is it a big-winner participation system?
```

两条目标的优先实验不同：

| objective | current status | next priority |
|---|---|---|
| downside protection | stage-1 backbone supported | policy replay + budget calibration |
| big-winner capture | stage-2 unresolved, defense cost high | random baseline triage + defense-participation frontier |

本 topic 名为 `BIG_WINNER`，因此本计划默认优先解决 winner participation，而不是立即把 stage-1 defense replay 成完整策略。

## 3. Recommended Sequence

```text
P0: 12A7d random-baseline support triage + 12A7c sensitivity replay
P0/P1: 12A7e defense-participation frontier
P1: simple backbone policy replay, only if downside overlay is the objective
P2: 12A8 budget / probability calibration
P3: 12A9 vol-scaled label revision
```

## 4. 12A7d: Random Baseline Support Triage

### 4.1 Purpose

12A7d 的目标是区分：

```text
stage-2 signal failure
vs
random baseline construction failure
```

当前 12A7c 使用 strict exact matched replay：

```text
for each seed:
  every split x board_bucket x calendar_month cell must have enough random rows
  otherwise the entire seed is invalid
```

这个规则在 `X=0.30`、stage-1 survivor 进一步收缩后非常脆弱。decoupled 只剩 29/100 valid seeds；chained 为 0/100。

### 4.2 Required Baseline Variants

12A7d 不能简单“放宽直到过”。每个 baseline variant 必须预注册、独立输出、独立解释。

| baseline_id | definition | allowed conclusion |
|---|---|---|
| `strict_exact_cell_replay` | 保留 12A7c 原始 split x board x month 全 cell exact replay | 原始 fail-closed benchmark |
| `hierarchical_cell_replay` | month 不足时退到 quarter；若仍不足，再退到 split x board | primary sensitivity only while board dimension is preserved; split x board fallback is diagnostic |
| `pooled_cell_weighted_replay` | cell-level weighted replay，不要求 seed 内所有 cell 全过 | sensitivity / diagnostic |
| `with_replacement_replay` | 稀疏 cell 允许 replacement 补齐，并输出 effective_n / duplicate rate | diagnostic only unless variance is corrected |

Hard interpretation rule:

```text
Evidence strength strictly decreases as the random null becomes coarser:
strict_exact_cell_replay
  > hierarchical_cell_replay with board preserved
  > pooled_cell_weighted_replay
  > with_replacement_replay

A win under a coarser null is not equivalent to a win under the strict null.
Coarser variants can show directional sensitivity, but cannot by themselves
prove deployable support.
```

Reason:

```text
Coarsening month -> quarter -> split x board weakens the matched null.
The random_p50 may become easier to beat because board x month composition
is no longer controlled at the original granularity.
```

Variant results must not be aggregated by taking the best result. Each variant is interpreted independently, and the decision row must report the weakest accepted null that still supports the claim.

### 4.3 Output Readouts

必须输出：

```text
random_support_cell_audit.csv
random_replay_variant_readout.csv
random_replay_variant_bootstrap_ci.csv
stage2_chained_sensitivity_decision.csv
stage2_random_baseline_triage_report.md
```

核心字段：

```text
baseline_id
denominator_type
candidate_id
stage2_budget_X
split
cell_grain
null_strength_rank
board_dimension_preserved_flag
requested_selected_n
available_random_n
shortfall_n
shortfall_rate
valid_seed_n
effective_seed_n
random_p05 / random_p50 / random_p95
delta_vs_random_p50
delta_vs_random_p50_ci95_low / high
baseline_construction_status
allowed_interpretation
```

### 4.4 Decision Logic

12A7d 不应直接宣称 stage-2 supported，除非严格或近严格 baseline 支持。Coarser variants are capped at diagnostic-only unless they are only confirming a stricter result.

```text
if strict_exact_cell_replay pass and chained delta CI low > 0:
  decision_state = 12A7d_strict_chained_stage2_supported

elif hierarchical_cell_replay pass
     and board_dimension_preserved_flag = true
     and chained delta CI low > 0
     and pooled_cell_weighted_replay direction agrees:
  decision_state = 12A7d_chained_stage2_supported_with_baseline_caveat

elif chained positive only under split x board fallback,
     pooled_cell_weighted_replay,
     or with_replacement_replay:
  decision_state = 12A7d_stage2_signal_diagnostic_only

elif decoupled positive but chained only positive under diagnostic variants:
  decision_state = 12A7d_stage2_signal_diagnostic_only

elif all variants fail support construction:
  decision_state = 12A7d_random_baseline_support_insufficient

else:
  decision_state = 12A7d_stage2_not_supported
```

### 4.5 Expected Interpretation

12A7d is expected to clarify baseline feasibility, not necessarily to flip 12A7c into support. The chained robustness sample is structurally thin:

```text
selected_n ~= 279
selected_positive_n ~= 36
valid_seed_n = 0 under strict 12A7c replay
```

Even if the random null is repaired, candidate-side bootstrap uncertainty may remain wide. Therefore the default expectation is:

```text
12A7d likely produces diagnostic_only or baseline_support_insufficient,
not full deployable support.
```

If 12A7d still cannot support chained stage-2, that does not kill continuation research. It means:

```text
the current stage-1 X=0.30 denominator is too narrow
or
the random replay design cannot support such a narrow chained sample.
```

This directly motivates 12A7e.

## 5. 12A7e: Defense-Participation Frontier

### 5.1 Purpose

12A7e answers:

```text
How aggressive should stage-1 defense be if the final objective is big-winner capture?
```

12A7b selected X=0.30 because it is a strong fast-fail rejector. But 12A7c shows that this choice also reduces winner participation. 12A7e must quantify the tradeoff rather than treating X=0.30 as fixed.

### 5.2 Frontier Grid

Stage-1 backbone is frozen to:

```text
feature = volatility_20d
orientation = asc
history_policy = PIT trailing-rank
```

Only X varies:

```text
stage1_X_grid = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.85, 1.00]
```

`X = 1.00` is the no-stage-1-defense anchor:

```text
stage1 keep all rows
chained survivor denominator = all observable no-fast-fail survivors
stage-2 remains deployable at the stage-2 decision time
```

This anchor connects the chained frontier back to the decoupled ceiling and directly tests whether the two-stage architecture is losing winner participation because stage-1 defense is too aggressive.

For each X, compute:

```text
stage1_selected_n
stage1_selected_budget_total
stage1_fast_fail_rate
stage1_delta_vs_random_p50
ground_truth_survivor_n
chained_survivor_n
chained_survivor_share_of_ground_truth
chained_survivor_continuation_rate
continuation_positive_capture_rate
stage2_selected_n
stage2_selected_continuation_rate
stage2_selected_positive_capture_rate
stage2_delta_vs_random_p50
nominal_barrier_expectancy_proxy
```

### 5.3 Frontier Decision

12A7e is a frontier audit, not an OOS X re-selection exercise. Any preferred X must be selected on train only:

```text
selection_split = train
validation = readout_only
robustness = readout_only
forbidden: choose X using validation or robustness continuation outcomes
```

The frontier should not choose the lowest fast-fail rate by default. It must expose Pareto points:

```text
minimize fast_fail_rate
maximize continuation_positive_capture_rate
maximize stage2 deployable evidence
maximize nominal_barrier_expectancy_proxy
control budget drift
```

The diagnostic expectancy proxy is not a trading PnL estimate. It is a fixed-barrier objective used only to compare frontier points under the current labels:

```text
nominal_barrier_expectancy_proxy =
  0.20 * stage2_selected_positive_capture_rate
  - 0.10 * fast_fail_rate
```

`stage2_selected_positive_capture_rate` must use a per-entry denominator:

```text
stage2_selected_positive_capture_rate =
  stage2_selected_continuation_positive_n / stage1_entry_n
```

This is intentionally different from `stage2_selected_continuation_rate`, which is conditional on the stage-2 selected survivor denominator:

```text
stage2_selected_continuation_rate =
  stage2_selected_continuation_positive_n / stage2_selected_n
```

The proxy must not combine a survivor-conditional continuation rate with an entry-level fast-fail rate. If a frontier table also reports survivor-conditional rates, those fields are diagnostic only and must not feed the proxy.

If transaction cost / holding-period / position sizing is later added, that belongs to policy replay, not this frontier audit.

Potential states:

```text
12A7e_x030_defense_optimal_for_downside_not_winner
12A7e_wider_stage1_frontier_preferred_for_winner_capture
12A7e_no_stage1_width_recovers_winner_participation
12A7e_policy_objective_split_required
```

Decision rows must include:

```text
selection_split
preferred_X_if_train_selected
robustness_frontier_rank_for_preferred_X
lookahead_selection_guard_status
```

### 5.4 Required Insight

12A7e must explicitly answer:

```text
Is the two-stage architecture failing because stage-2 has no deployable signal,
or because stage-1 X=0.30 removes too much of the right-tail opportunity set?
```

## 6. 12A8: Budget / Probability Calibration

12A8 remains useful but should not precede 12A7d / 12A7e.

Reason:

```text
12A7b simple backbone already works without calibration in robustness.
The unresolved question is winner participation, not probability scale alone.
```

12A8 should focus on:

```text
validation budget drift
calendar-aware budget stabilization
board-aware target exposure
probability / rank calibration readouts
policy replay exposure control
```

Allowed next state:

```text
12A8_calibration_supports_policy_replay
12A8_calibration_diagnostic_only
12A8_prior_shift_not_calibratable_under_current_labels
```

## 7. 12A9: Vol-scaled Label Revision

12A9 is high-cost and should remain deferred.

Rationale:

```text
vol-scaled barriers may reduce base-rate nonstationarity,
but they change the label definition and break direct comparability
with 12A6c / 12A7 / 12A7b / 12A7c.
```

12A9 should only start if:

```text
12A7d shows baseline construction is feasible but signal remains unstable
or
12A7e shows no defense width can preserve winner participation under fixed barriers
or
12A8 shows calibration cannot handle prior shift under fixed -10% / +20% labels
```

## 8. What Not To Do Next

Do not prioritize:

1. Larger stage-1 model capacity.
   - Low-capacity monotone model failed to beat simple backbone robustly.
   - Complex model is near parity, not a clear upgrade.

2. Direct stage-2 policy replay.
   - Chained random baseline is currently unavailable.
   - Policy replay would mix signal failure with baseline construction failure.

3. Standalone downside policy replay if the strategic objective is big-winner capture.
   - It may validate a useful overlay, but it does not solve right-tail participation.

4. Label revision before baseline triage.
   - It is too expensive and destroys clean comparison to the existing run chain.

## 9. Proposed Next Requirement Names

Recommended immediate next file:

```text
requirement_12a7d_stage2_random_baseline_support_triage.md
```

Recommended parallel design file:

```text
requirement_12a7e_defense_participation_frontier.md
```

Deferred:

```text
requirement_12a8_simple_backbone_budget_calibration_policy_replay.md
requirement_12a9_vol_scaled_barrier_label_stability_audit.md
```

## 10. Final Recommendation

Proceed in this order:

```text
1. Write 12A7d requirement.
2. Implement and rerun 12A7c sensitivity under pre-registered random baseline variants.
3. Draft 12A7e in parallel, because current evidence already shows defense participation cost.
4. Decide whether the project branch is downside overlay or big-winner capture.
5. Only then choose between policy replay, calibration, or label revision.
```

Short version:

```text
Fix the random baseline first.
Then measure the defense-vs-winner frontier.
Do not add model complexity until those two questions are settled.
```
