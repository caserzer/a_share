# EP19 Research Plan: Entry-Universe PIT Tradability Preflight

创建日期：2026-07-03

## 0. 实验定位

EP19 是 EP18 收口后的 topic-level restart，不是 `18G`，也不是继续精修 payoff-state exit/defend bridge。

EP18 的正式收口是：

```text
closure_state = EP18_closed_representation_only_no_policy_path
closing_phase = 18F_payoff_state_oracle_gap_bridge
closing_decision_state = 18F_utility_bridge_not_supported
next_requirement_within_ep18 = none
```

Lineage note:

```text
18F itself emits next_allowed_requirement = none.
EP18 closure_state is recorded in EP18 discussion.md as a topic-level research closure note,
not as a pipeline authorization handoff.
EP19 is therefore a human research restart at topic level, not an 18F-authorized next requirement.
```

EP18 给出两个并存结论：

```text
1. refreshed 18C payoff-state score has ranking representation value.
2. that ranking score does not transport into positive defend/continue action utility.
```

更上层的问题是：EP16-EP18 的 denominator 是 realized-winner episode 内的 holding/exit states。这个 universe 带有 hindsight 条件化，且预设已经在仓位里。没有一个可部署的 entry universe，就无法把 holding/exit diagnostic 转成交易路径。

EP19 因此只回答一个前置问题：

```text
Can a PIT-valid, no-hindsight, tradeable entry candidate universe be constructed
before realized-winner conditioning?
```

如果答案是否定的，Big Winner 主线应在 entry 层收口，而不是继续在 realized-winner 子宇宙里优化退出。

## 1. Non-Negotiable Scope

EP19 不做：

```text
不输出 entry policy
不输出 exit policy
不输出 holding policy
不做 position sizing
不做 portfolio construction
不做 portfolio backtest
不做 production signal
不做 live trading
不使用 realized winner episode membership 作为入场条件
不使用 t0 之后才知道的 winner path / episode end / entry phase
不继续调 18F 的 threshold / cutoff / defend mask
不把 18C payoff-state score 直接升级成交易信号
```

EP19 允许做：

```text
冻结 PIT entry candidate universe 的 lineage 和 denominator
审计 candidate generator 是否可在 t0 或 t0 close 后生成 next-open entry row
审计 next-open / next-tradable-open 是否真的可成交，而不是只存在理论价格
冻结 forward big-winner outcome label，并证明它不参与 candidate membership
评估 candidate universe 对 future big-winner outcome 的 base-rate enrichment / capture / false-positive burden
在 entry-conditioned universe 上重测 post-entry opportunity、fast-fail、O5 headroom 与 holding/defend diagnostic value
比较 strict baseline / matched baseline / random same-budget baseline
给出是否值得进入 EP20 的 go/no-go 裁决
```

所有正向结论最多授权下一步 requirement，例如 entry-universe separability 或 policy preflight。EP19 本身不得授权策略或回测。

## 2. 上游证据与为什么要新开 EP19

### 2.1 EP15：t0 winner morphology 入场路径已被否定

EP15 的核心结论是：

```text
winner 形态不是 t0 可预测的离散类别；
entry position within realized episode 在 t0 不可知；
对整段 winner episode 做 hindsight taxonomy 不能形成可部署 entry signal。
```

这意味着 EP19 不能把"未来会成为 winner episode"当作入场 universe，也不能把 realized episode phase 当作 t0 可用特征。

### 2.2 EP16-EP18：holding/exit 子问题没有形成 policy path

EP16 关闭了 continuation-as-action mainline。EP17 证明 realized-winner holding universe 内存在 O5 perfect utility upper bound，但这是 oracle upper bound，不是 deployable signal。EP18 进一步证明 refreshed payoff-state ranking score 不能桥接成正 action utility。

关键读数：

```text
18F primary learned utility = -0.010552
18F O5 oracle mean = 0.029467
18F O5 approximation ratio = -0.358080
18F cluster bootstrap CI = [-0.014387, -0.007484]
18F top30 retention = 0.625587
18F top20 retention = 0.636519
```

结论：继续在 realized-winner 条件化 universe 内调 exit mask 没有部署意义。下一步必须先回到 entry denominator。

### 2.3 EP13/EP14：已有 event/entry 线索不能直接复用为答案

EP13/EP14 已经探索过 full PIT native event、compression/repair、sparse state-change、cohort normalization 等方向。它们可以作为 EP19 的候选输入来源，但不能直接被当成可部署 entry universe。

EP19 的区别是：

```text
不是再找一个高 uplift event；
而是先冻结一个无 hindsight 的 entry candidate denominator，
然后问这个 denominator 是否有足够 tradeable base-rate / capture / utility headroom。
```

## 3. 核心研究问题

EP19 要回答七个问题。

### Q1. 是否存在无 hindsight 的 entry candidate universe?

一个 candidate row 必须满足：

```text
decision_time <= t0 close
entry_time = next tradable open after decision_time
all features and filters are PIT-observable at decision_time
membership does not depend on future winner outcome
membership does not depend on realized winner episode boundary
```

如果 candidate generator 只能在事后 winner path 中定义，EP19 fail closed。

### Q2. Candidate universe 是否有足够样本、可成交性和可交易密度?

需要同时评估：

```text
entry_candidate_n by split
instrument_n / instrument_month_n / calendar_month_n
episode_cluster_n
same-instrument overlap / cooldown pressure
daily signal density and capacity proxy
entry_fill_feasible_rate
entry_suspended_rate
entry_limit_up_blocked_rate
entry_limit_down_stress_rate
entry_open_liquidity_coverage_rate
entry_impact_cost_proxy
```

太稀疏会导致不可评估；太密集则退化成宽市场 beta / participation filter。A 股还必须单独审计 fill feasibility：有 next open 不等于能成交。若候选最强的那批主要落在次日一字涨停、停牌、无量开盘或严重流动性枯竭上，winner capture 必须降级或 fail closed，因为它是不可买入的机会。

### Q3. Candidate universe 是否富集 future big-winner outcome?

EP19 不要求直接通过策略收益，但必须证明 candidate universe 不是纯随机触发。

主读数：

```text
big_winner_forward_rate
winner_capture_rate
precision_vs_universe_base_rate
lift_vs_random_same_budget
lift_vs_time_matched_baseline
lift_vs_instrument_matched_baseline
```

如果只能在 train 上富集、robustness/validation 消失，则不支持 EP20。

Q3 是 EP19 的 primary go/no-go gate。Train-only enrichment 不算正向证据；robustness 必须相对 matched-budget baseline 有稳定提升，validation 只能作为压力读数，不能用于选择 event family、阈值或 baseline arm。如果 Q3 在 robustness 上跑不赢 matched baseline，EP19 应直接收口为 `19_entry_universe_not_tradeable` 或 `19_entry_universe_enrichment_only_diagnostic`，不得下沉到 19C/19D 寻找补偿性证据。

### Q4. Candidate universe 的 false-positive burden 是否可接受?

入场 universe 不能只看捕获 winner，也必须量化非赢家负担：

```text
non_winner_rate
fast_fail_rate
max_drawdown stress
left-tail loss
holding-period opportunity cost
candidate_per_winner_burden
```

如果 winner capture 高但 false-positive denominator 爆炸，后续 holding/exit 研究会被噪声淹没。

### Q5. 在 entry-conditioned universe 上，post-entry O5 headroom 是否仍存在?

EP18 的 O5=2.94% 是 realized-winner holding universe 内的上界。EP19 必须在真实 entry-conditioned universe 上重测：

```text
O5_entry_conditioned_perfect_utility
O2_entry_conditioned_drawdown_oracle
blind_entry_continue_baseline
candidate_after_cost_expectancy
post-entry defend/continue headroom
```

如果进入真实入场宇宙后 O5 headroom 消失，说明这条主线没有可交易后续。

### Q6. Entry universe 是否能支持下一步 separability / policy preflight?

即使 candidate universe 有 uplift，也必须有足够可学习空间：

```text
train/robustness/validation split support
cluster bootstrap support
feature availability at t0
no feature family dominated by future-derived fields
baseline-improvement over simple filters
```

EP19 只判断是否值得进入 EP20，不训练最终 policy。

### Q7. 结果是否仍可能只是 participation / market-regime exposure?

必须区分：

```text
true entry edge
participation filter
risk-on regime proxy
liquidity/size/volatility beta
calendar regime artifact
```

如果正读数主要来自 risk-on exposure 或 broad market participation，EP19 只能输出 diagnostic，不授权 entry policy preflight。

## 4. Primary Denominator

EP19 primary denominator 是 candidate entry rows，而不是 realized-winner episode steps。

定义：

```text
entry_candidate_row =
    instrument
    decision_date
    decision_time_bucket
    entry_date
    entry_price_source
    entry_fill_feasibility_status
    candidate_generator_id
    candidate_event_id
    PIT feature snapshot
    forward outcome labels for audit only
```

硬约束：

```text
1. candidate membership must be computable at or before decision_time.
2. entry execution must use next-open or another predeclared executable convention.
3. executable price must pass fill-feasibility checks under A-share limit/suspension/liquidity constraints.
4. all forward labels are readout-only and cannot affect candidate membership.
5. same instrument repeated triggers require predeclared cooldown or overlap accounting.
6. split assignment must be frozen before any model/cutoff selection.
```

EP19 必须同时维护三个分母：

```text
candidate_denominator      = all PIT entry candidates
eligible_universe_baseline = all eligible instrument-date rows under same calendar/universe filters
matched_budget_baseline    = random or matched rows with same count/density/cooldown budget
```

任何 uplift / utility / recall 都必须说明使用哪个分母。

## 4.1 Forward outcome label freeze

19A must freeze a PIT-clean forward outcome label before any enrichment readout. The label is outcome-only and cannot be used in candidate generation.

Primary forward big-winner audit label:

```text
forward_big_winner_120d =
    max_qfq_high_from_entry_through_120_sessions / entry_executable_price - 1 >= 0.50
```

Required label fields:

```text
forward_label_id
entry_price_source
forward_horizon_sessions
max_forward_high_price_source
forward_mfe_return
forward_big_winner_flag
path_completeness_flag
label_readout_only_flag = true
candidate_membership_uses_forward_label = false
```

Rules:

```text
1. This label is not realized winner episode membership.
2. This label is computed from the executable entry row, not from a hindsight episode anchor.
3. A candidate source that needs the future label to define membership fails the PIT gate.
4. +30% and +100% may be diagnostic sensitivity labels, but +50% / 120 sessions is the primary Big Winner audit label unless 19A explicitly freezes a different threshold with evidence.
```

## 5. Candidate Generator Sources

EP19 不做无限搜索。允许进入 19A 的候选来源必须来自已有研究链路或预注册的简单 baseline。

### 5.1 Existing event-source families

允许审计但不默认支持：

```text
04_high_recall_repair_event_candidate_generator_v0
07_topn_multichannel_repair_candidate_generator_v0
13_full_pit_native_event_discovery_v0
14_full_native_sparse_state_change_event_utility_preflight_v0
```

每个来源必须被重新审计：

```text
PIT membership proof
decision_time proof
entry execution proof
fill feasibility proof
duplicate/cooldown proof
winner-label independence proof
```

### 5.2 Baseline entry universes

必须包含至少三类 baseline：

```text
calendar-time random same-budget baseline
instrument-matched random same-budget baseline
liquidity/size/volatility matched baseline
```

这些 baseline 是防止把 market-regime / liquidity beta 误判为 entry edge。

### 5.3 Disallowed sources

不允许：

```text
realized winner episode membership
future max return / max drawdown thresholds as filters
post-entry path shape or future phase labels
any field whose source_pos > decision_pos
validation-selected event family
```

## 5.4 Sampling geometry inheritance

EP19 must inherit the sampling caution from EP16A: raw trigger count is not independent sample count.

Required reuse of 16A-style discipline:

```text
instrument-level cooldown accounting
same-instrument overlap accounting
episode-or-event cluster id for bootstrap
calendar-month and instrument-month support
effective_sample_size_readout
cluster-aware bootstrap, not row-only bootstrap
```

Any report that presents row count without cluster/effective-sample context is incomplete. If repeated triggers from the same instrument/month dominate the evidence, EP19 must downgrade enrichment and utility claims to diagnostic-only.

## 6. Phase Plan

### Phase 19A: Entry Universe Lineage and Tradability Preflight

目标：冻结 EP19 的 denominator、entry timing、candidate source list、PIT audit、fill-feasibility audit、forward big-winner label 和 baseline budget。

关键输出：

```text
input_artifact_audit.csv
entry_candidate_lineage_audit.csv
pit_feature_availability_audit.csv
entry_execution_convention_audit.csv
entry_fill_feasibility_audit.csv
forward_big_winner_label_freeze.csv
candidate_density_and_overlap_audit.csv
effective_sample_size_readout.csv
baseline_budget_freeze.csv
entry_universe_preflight_decision.csv
```

19A 的正向裁决只授权 19B outcome readout，不授权模型或策略。

### Phase 19B: Entry Candidate Outcome and Base-Rate Readout

目标：在冻结 denominator 上，衡量 candidate universe 的 winner enrichment、capture 和 false-positive burden。

主读数：

```text
big_winner_forward_rate by split
winner_capture_rate by split
precision/lift vs eligible universe
precision/lift vs random same-budget baseline
precision/lift vs instrument/liquidity matched baseline
robustness matched-baseline delta as primary gate
candidate_per_winner_burden
fast_fail_rate
drawdown/tail-loss readout
cluster-aware bootstrap CI
```

19B 仍不是 policy。它只判断 entry universe 是否值得继续。如果 robustness matched-baseline delta 失败，19B 不得继续进入 19C，并且不能用 oracle headroom 去救一个没有 OOS 富集的 entry universe。

### Phase 19C: Entry-Conditioned Utility Headroom Replay

目标：在真实 candidate denominator 上重测 EP17/EP18 中的 oracle headroom，而不是沿用 realized-winner universe 的 O5。

主读数：

```text
blind_entry_continue_baseline
after-cost entry expectancy
O5_entry_conditioned_perfect_utility
O2_entry_conditioned_drawdown_oracle
post-entry payoff retention
post-entry false-positive cost
fill-adjusted opportunity loss
```

如果 entry-conditioned O5 也没有足够 headroom，则不进入 model/separability。

19C must recompute O5/O2 from the entry-conditioned denominator. EP17/EP18 O5/O2 values are reference-only and must not be copied. Cost assumptions must be frozen in 19A and should include at minimum commission/slippage, stamp-tax side effects where relevant, limit-up fill premium/blocked-fill handling, and next-open execution delay.

### Phase 19D: Entry Separability Readiness Diagnostic

目标：不训练最终 entry policy，只判断是否存在足够支持下一步 EP20 的 separability surface。

允许读数：

```text
simple train-only ranking probe
time-split OOS rank IC
decile monotonicity
bootstrap CI
baseline delta vs matched random
feature family leakage audit
```

禁止：

```text
validation-driven feature selection
threshold tuning on robustness/validation
portfolio backtest
trade recommendation
```

### Phase 19E: Closure and Handoff

可能结论：

```text
19_entry_universe_pit_tradability_supported
  -> may authorize requirement_20_entry_universe_separability_or_policy_preflight.md

19_entry_universe_enrichment_only_diagnostic
  -> representation/opportunity exists, but no policy preflight

19_entry_universe_not_tradeable
  -> no deployable entry universe; close Big Winner active entry path

19_entry_universe_lineage_blocked
  -> PIT/tradability/denominator contract failed
```

## 7. Gate Philosophy

EP19 gates should be stricter than EP18 because EP19 is closer to deployment.

Hard gates:

```text
pit_lineage_gate
entry_execution_gate
fill_feasibility_gate
forward_label_freeze_gate
winner_membership_independence_gate
sample_support_gate
candidate_density_gate
effective_sample_size_gate
baseline_budget_gate
split_stability_gate
matched_baseline_improvement_gate
false_positive_burden_gate
entry_conditioned_o5_headroom_gate
search_accounting_gate
no_policy_authorization_gate
```

Suggested non-final thresholds must be frozen in the 19A requirement, not in this plan. The plan-level intent is:

```text
1. Candidate universe must be large enough to evaluate.
2. Candidate universe must not be so dense that it becomes market exposure.
3. Winner enrichment must beat matched baselines, not just raw universe.
4. False-positive burden must be bounded.
5. Entry-conditioned oracle headroom must remain material after costs.
6. Entry rows must be fill-feasible under A-share limit/suspension/liquidity constraints.
```

## 8. Report Requirements for Future Implementations

Every EP19 report must state:

```text
EP19 is not a policy, not a backtest, and not a production signal.
```

Reports must include:

```text
1. candidate denominator and baseline denominator definitions
2. PIT lineage and source_pos / decision_pos audit
3. entry execution convention
4. A-share fill feasibility: suspension, limit-up/limit-down, liquidity and impact proxy
5. forward big-winner label definition and proof it is readout-only
6. candidate density, overlap and effective sample size
7. winner enrichment and capture
8. false-positive burden
9. matched baseline comparison
10. entry-conditioned O5/O2 headroom
11. search accounting and validation non-use
12. final AFML interpretation
```

## 9. First Requirement to Generate

The next concrete artifact should be:

```text
requirement_19a_entry_universe_pit_lineage_and_tradability_preflight.md
```

19A should not train a model. It should freeze the denominator and decide whether a PIT, executable, fill-feasible, auditable entry candidate universe exists.

If 19A cannot prove PIT membership, next-open executable entry timing, fill feasibility, and forward-label independence, EP19 should fail closed before any outcome readout.

## 10. Summary

EP19 changes the research object:

```text
from:
  realized-winner conditioned holding/exit states

to:
  no-hindsight PIT entry candidate universe
```

This is the right next step because EP18 has exhausted the representation-to-exit bridge within the realized-winner universe, and that universe cannot be entered without a separate deployable entry process.
