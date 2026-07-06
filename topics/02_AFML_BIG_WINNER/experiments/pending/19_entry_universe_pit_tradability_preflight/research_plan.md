# EP19 Research Plan: Entry-Universe PIT Tradability and Right-Tail Enrichment Preflight

创建日期：2026-07-03
更新日期：2026-07-06

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

EP19 因此切换研究对象：

```text
realized-winner conditioned universe
    ↓
no-hindsight PIT entry candidate universe
```

EP19 is a topic-level restart to test whether a PIT-valid, tradeable, no-hindsight entry candidate universe can be constructed, and whether that universe shows robust right-tail enrichment under matched baselines and false-positive burden constraints.

EP19 不只是冻结 entry candidate denominator，还必须判断该 denominator 是否在 full candidate population 上具备稳健右尾富集，且这种富集不能由少数极端名字、risk-on 择时、行业/板块 hindsight、重复 event 或不可成交机会解释。

EP19 只回答一个前置问题：

```text
Can a PIT-valid, no-hindsight, tradeable entry candidate universe be constructed
before realized-winner conditioning,
and does it show robust right-tail enrichment with acceptable false-positive burden?
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
不使用 validation 选择 event family、阈值、grid cell 或 baseline arm
不把 current industry/concept/theme membership retroactively 用作历史特征
```

EP19 允许做：

```text
冻结 PIT entry candidate universe 的 lineage 和 denominator
冻结 raw -> canonical -> cooldown 三层 event denominator
审计 candidate generator 是否可在 t0 或 t0 close 后生成 next-open entry row
审计 next-open / next-tradable-open 是否真的可成交，而不是只存在理论价格
冻结 forward big-winner / MFE / MAE / path outcome labels，并证明它们不参与 candidate membership
冻结 industry / board / theme data contract 和 PIT 使用边界
预注册 simple rule-grid search space 并做快速 enrichment scan
评估 candidate universe 对 future right-tail outcome 的 enrichment / capture / false-positive burden
在 entry-conditioned universe 上重测 post-entry opportunity、fast-fail、O5/O2 headroom 与 CTA-style replay headroom
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
再问这个 denominator 是否有稳健右尾富集、可成交性、可控重复触发和可接受 false-positive burden。
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
episode_or_event_cluster_n
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

### Q3. Candidate universe 是否存在稳健右尾富集?

EP19 不要求直接通过策略收益，但必须证明 candidate universe 不是纯随机触发，也不是由重复 event、少数极端名字、risk-on beta、行业/板块 hindsight 或不可成交机会制造出来的表观 lift。

不能只看：

```text
big_winner_forward_rate
```

必须同时评估：

```text
tail_lift_curve
CCDF / survival curve
winner_capture_vs_burden
MFE / MAE joint distribution
top-k removal sensitivity
matched-base tail lift
cluster_bootstrap_CI
```

Candidate universe must show robust right-tail enrichment:

```text
not only higher P(MFE_120 >= 50%),
but also a better right-tail / left-tail tradeoff
under matched time / instrument / liquidity / regime baselines.
```

Required Q3 readouts:

```text
primary_tail_lift_50 on fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows
sensitivity_tail_lift_20
sensitivity_tail_lift_30
sensitivity_tail_lift_100
ccdf_candidate_vs_baseline
winner_capture_rate
candidate_per_winner
MFE_120_p75 / p90 / p95
MAE_20_p10 / p05
MFE_to_MAE_ratio
top_1_instrument_removed_tail_lift
top_3_instruments_removed_tail_lift
cluster_bootstrap_CI
matched_baseline_delta
```

Minimum primary Q3 readouts:

```text
primary_tail_lift_50
candidate_per_winner
MAE_20_p10
family_level_multiplicity_corrected_margin_pass
```

Q3 的 primary enrichment denominator 必须是：

```text
fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule
```

理论候选集、raw trigger rows、canonical rows 或不可成交 entry rows 的富集只能作为 diagnostic，不能用于 support claim。

Primary metric definition:

```text
p_candidate_50 =
    P(forward_mfe_120 >= 0.50 | primary_enrichment_denominator, candidate family/cell)

p_matched_50 =
    P(forward_mfe_120 >= 0.50 | same primary_enrichment_denominator rules, matched_budget_baseline)

primary_tail_lift_50 =
    p_candidate_50 / p_matched_50
```

If `p_matched_50 = 0`, 19A must either freeze a smoothing rule before readout or mark the cell/family as not supportable for primary lift. The primary pass rule is ratio-based:

```text
primary_tail_lift_50 >= 1.0 + pre_frozen_corrected_margin_ratio
```

Q3 是 EP19 的 primary go/no-go gate。Train-only enrichment 不算正向证据；robustness 必须相对 matched-budget baseline 在预注册单一主指标 `primary_tail_lift_50` 上有稳定提升，并通过 family-level multiple-testing correction。`tail_lift_20/30/100`、CCDF 和 MFE/MAE 图只能作为 sensitivity 或解释，不得替代主指标。如果 Q3 在 robustness 上跑不赢 matched baseline，EP19 应直接收口为 `19_entry_universe_not_tradeable` 或 `19_entry_universe_enrichment_only_diagnostic`，不得下沉到 19C/19D 寻找补偿性证据。

Validation 只能作为最终压力读数，不能用于选择 event family、阈值、grid cell、baseline arm、margin 或 correction method。Robustness 也不能被当作跨 family 的筛选集合；进入 robustness 的 family 总数和选择规则必须在 19A 冻结。

Validation stress rule must also be frozen in 19A. Validation cannot improve or select anything, but a predeclared validation collapse rule may veto or downgrade a robustness-supported claim to diagnostic-only.

### Q4. Candidate universe 的 false-positive burden 是否可接受?

入场 universe 不能只看捕获 winner，也必须量化非赢家负担：

```text
non_winner_rate
fast_fail_rate
false_repair_rate
max_drawdown stress
MAE_20 left-tail
holding-period opportunity cost
candidate_per_winner_burden
```

如果 winner capture 高但 false-positive denominator 爆炸，后续 holding/exit 研究会被噪声淹没。

### Q5. 在 entry-conditioned universe 上，post-entry O5/O2 和 CTA-style headroom 是否仍存在?

EP18 的 O5=2.94% 是 realized-winner holding universe 内的上界。EP19 必须在真实 entry-conditioned universe 上重测：

```text
O5_entry_conditioned_perfect_utility
O2_entry_conditioned_drawdown_oracle
blind_entry_continue_baseline
candidate_after_cost_expectancy
post-entry defend/continue headroom
CTA-style right-tail participation headroom
```

如果进入真实入场宇宙后 O5/O2 headroom 消失，或 candidate + simple CTA exit 跑不过 random same-budget CTA，则这条 event universe 的交易价值可疑。

### Q6. Entry universe 是否能支持下一步 separability / policy preflight?

即使 candidate universe 有 uplift，也必须有足够可学习空间：

```text
train/robustness/validation split support
cluster bootstrap support
feature availability at t0
no feature family dominated by future-derived fields
baseline-improvement over simple filters
right-tail / left-tail tradeoff stability
```

EP19 只判断是否值得进入 EP20，不训练最终 policy。

### Q7. 结果是否仍可能只是 participation / market-regime exposure?

必须区分：

```text
true entry edge
participation filter
risk-on regime proxy
liquidity/size/volatility beta
industry/board/style beta
calendar regime artifact
```

如果正读数主要来自 risk-on exposure 或 broad market participation，EP19 只能输出 diagnostic，不授权 entry policy preflight。

## 4. Denominator / Labels / Industry Data / Cooldown Contracts

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
5. repeated triggers must use the raw -> canonical -> cooldown denominator contract.
6. split assignment must be frozen before any model/cutoff/grid selection.
7. Q3/19B primary tail-lift must be computed only on fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule.
8. 19A must freeze matched-baseline method, primary metric, margin rule, censoring treatment, family selection rule/cap and multiple-testing correction before outcome readout.
9. 19A must freeze chronological split construction, purge/embargo, same-instrument overlap handling and label-horizon boundary handling.
10. 19C replay eligibility must be frozen separately from 19B 120-session label eligibility.
```

EP19 必须同时维护三个比较分母：

```text
candidate_denominator      = all PIT entry candidates after selected denominator level
eligible_universe_baseline = all eligible instrument-date rows under same calendar/universe filters
matched_budget_baseline    = random or matched rows with same count/density/cooldown budget
primary_enrichment_denominator =
    fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule
replay_denominator =
    fill_feasible ∩ cooldown_entry_rows ∩ replay_path_eligible_rows_under_frozen_replay_horizon_rule
```

任何 uplift / utility / recall 都必须说明使用哪个分母。

### 4.1 Event canonicalization and dedup contract

Every candidate source must output three denominator levels:

```text
raw_trigger_rows
canonical_event_rows
cooldown_entry_rows
```

Definitions:

```text
raw_trigger_rows:
    原始 event family 触发行。

canonical_event_rows:
    same instrument + same decision_date 合并为一行；
    多 event family 只作为 feature flags 保留。

cooldown_entry_rows:
    same instrument 在 predeclared cooldown window 内只保留一个 entry candidate。
```

Cooldown window must be predeclared:

```text
same-instrument cooldown ∈ {5D, 10D, 20D}
primary default = 10D
```

Primary support rule:

```text
19B 的 primary gate 只能使用 fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule。
19C 的 replay gate 只能使用 fill_feasible ∩ cooldown_entry_rows ∩ replay_path_eligible_rows_under_frozen_replay_horizon_rule。
raw_trigger_rows 只能作为 diagnostic。
```

Reason:

```text
如果不用 cooldown，任何右尾富集都可能只是一个 episode 内多次重复触发造成的伪样本膨胀。
```

### 4.2 Forward outcome label freeze

19A must freeze PIT-clean forward outcome labels before any enrichment readout. Labels are outcome-only and cannot be used in candidate generation.

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
forward_mfe_20
forward_mfe_60
forward_mfe_120
forward_mae_10
forward_mae_20
forward_mae_60
forward_return_20
forward_return_60
forward_return_120
fast_fail_10
false_repair_20
big_failure_20_or_60
forward_big_winner_120d
path_complete_flag
path_complete_20
path_complete_60
path_complete_120
censoring_status
last_available_forward_session
label_readout_only_flag = true
candidate_membership_uses_forward_label = false
```

Rules:

```text
1. forward_big_winner_120d is a right-tail audit label, not the only outcome.
2. 19B must evaluate both right-tail payoff and left-tail burden.
3. This label is not realized winner episode membership.
4. This label is computed from the executable entry row, not from a hindsight episode anchor.
5. A candidate source that needs the future label to define membership fails the PIT gate.
6. +20%, +30%, +100% may be diagnostic sensitivity labels, but +50% / 120 sessions is the primary Big Winner audit label unless 19A explicitly freezes a different threshold with evidence.
7. 19A must freeze the 120-session right-censoring treatment before any enrichment readout.
8. Default primary treatment: `path_complete_120 = true` is required for candidate rows and all matched baselines; dropped censored rows must be reported by split, calendar month, instrument count and regime bucket.
9. If a survival-analysis treatment is chosen instead, it must be predeclared in 19A and applied identically to candidate and baseline rows. Censored rows cannot be silently assigned `forward_big_winner_120d = false`.
10. Recommended fallback trigger: if `path_complete_120_rate < 0.70` in the validation primary denominator, automatically add Kaplan-Meier or IPCW survival-analysis readouts. These are censoring-adjusted diagnostics unless 19A explicitly predeclares them as fallback decision readouts.
11. If the fallback trigger fires, the final decision must note that high censoring lowers conclusion confidence by at least one level unless effective-sample support remains above the frozen validation minimum.
```

### 4.3 Industry / board / theme data contract

EP19 may use industry / board / theme data only under an explicit data contract. The contract must state whether each field is a supported PIT feature, a board/style fallback, or diagnostic-only context.

Data layers:

```text
industry_classification:
    用于 PIT 行业归属、行业相对强弱、行业 breadth。

board_or_style_proxy:
    用于创业板 / 主板 / 科创板 / 小盘 / 成长等 style fallback。

concept_or_theme_proxy:
    用于题材扩散、概念热度、事件驱动 readout。
```

Public / semi-public source candidates:

```text
1. CNInfo / 巨潮行业分类与行业变更
   - 优点：有行业分类和变更日期，适合 PIT 行业归属审计
   - 用途：industry PIT membership, industry-relative return, industry breadth

2. AkShare 东方财富行业板块 / 概念板块
   - 优点：接口方便，板块 / 概念 / 成份股丰富
   - 缺点：很多是当前视图，不天然 PIT
   - 用途：board/theme proxy, daily snapshot required

3. AkShare 同花顺行业 / 概念板块
   - 优点：题材覆盖较丰富，贴近 A 股主题行情
   - 缺点：成分定义漂移，必须每日快照
   - 用途：theme diffusion diagnostic

4. BaoStock
   - 优点：行情、基础数据较方便
   - 缺点：题材 / 概念 / 历史成分较弱
   - 用途：行情备份和基础字段

5. Tushare Pro
   - 优点：数据结构较完整
   - 缺点：积分 / 权限限制，不是纯公开
   - 用途：辅助交叉验证
```

Recommended EP19A data priority:

```text
primary supported industry source:
    CNInfo / 巨潮 and/or 申万一级行业历史变更表, if PIT effective dates can be proven

concept/theme membership:
    diagnostic-only by default unless daily historical snapshots already exist

execution priority:
    do not block B1 / B2 / B4 / B5 on concept/theme data infrastructure
    B3 is the only simple baseline source that depends directly on PIT industry/board breadth
```

PIT rules:

```text
Industry membership must be PIT.
Concept/theme membership must be daily-snapshotted if used as feature.
Current membership cannot be used retroactively.
If only current concept membership is available, it may be used only as diagnostic, not as supported feature.
Board/style proxies must state whether they are exchange-native, security-master derived, or vendor-derived.
Any industry/board/theme feature must include source_date, effective_date, snapshot_date and decision_date compatibility.
If PIT industry membership cannot be proven, industry-dependent features cannot be supported primary features.
If only current concept/theme membership is available, theme diffusion remains diagnostic-only and cannot support B3 or any primary enrichment claim.
```

## 5. Candidate Generator Sources and Grid-Search Space

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
canonicalization proof
duplicate/cooldown proof
winner-label independence proof
industry/board/theme PIT proof if used
```

### 5.2 Required baseline entry universes

必须包含至少三类 baseline：

```text
calendar-time random same-budget baseline
instrument-matched random same-budget baseline
liquidity/size/volatility matched baseline
```

These baselines prevent market-regime / liquidity beta / broad participation from being mistaken for entry edge.

19A must freeze the matched-baseline construction method before any outcome readout.

Primary baseline gate rule must also be frozen in 19A:

```text
primary default = conjunctive pass across all three required baselines
    calendar-time random same-budget baseline
    instrument-matched random same-budget baseline
    liquidity/size/volatility matched baseline

If 19A chooses a single primary baseline instead, the choice and rationale must be predeclared.
If 19A allows pass-on-any-baseline, that additional baseline-selection multiplicity must be included in search accounting.
```

Required baseline matching spec:

```text
baseline_matching_method:
    stratified / coarsened-exact / nearest-neighbor / propensity-style, predeclared in 19A

calendar_match_keys:
    decision_month or decision_week, split, regime_bucket if used

budget_match_keys:
    candidate_count, daily_density, cooldown window, label eligibility and fill feasibility

instrument_match_keys:
    same instrument where feasible, otherwise predeclared instrument cluster / industry / board / size bucket

liquidity_size_vol_match_keys:
    train-fitted amount / turnover / market-cap / volatility decile bins, or predeclared caliper values

replacement_policy:
    with or without replacement, fixed before readout

random_seed_policy:
    deterministic seed or manifest-tracked seed set
```

Required baseline quality audit:

```text
matched_row_n
unmatched_candidate_n
baseline_reuse_rate
standardized_mean_difference_max
calendar_coverage_delta
instrument_coverage_delta
liquidity_size_vol_balance_status
baseline_matching_gate
```

If matching quality fails, matched-baseline improvement cannot be used as support evidence.

### 5.3 Simple rule-grid baseline candidate sources

EP19 restart 必须允许 simple rule-grid baseline sources。否则无法判断复杂 event 是否有增量。

Predeclared simple sources:

```text
B1: near 120d high + volume expansion
B2: relative strength breakout
B3: industry/board breadth expansion
B4: volatility contraction then breakout
B5: recent high close + amount expansion
B6: low drawdown reclaim / EMA reclaim
```

Each source must be:

```text
PIT computable
next-open executable
forward label independent
cooldown-controlled
matched-baseline comparable
```

B3 PIT prerequisite:

```text
B3: industry/board breadth expansion is supported only if PIT industry membership
or PIT board/style membership is proven before 19B0.

If PIT industry membership is unavailable, the industry-breadth variant of B3 fails closed.
If only current concept/theme membership is available, B3 may be reported only as diagnostic.
```

### 5.4 Rule-grid search discipline

19B0 may scan simple event rules on train only, but the search space must be frozen in 19A. 19B0 is a triage phase; 19B is the only phase that performs the formal robustness confirmation.

Grid limits:

```text
grid_parameter_n <= 5
grid_total_cells <= 300
validation must not be used for selection
all grid cells must be counted in search accounting
one_train_selected_cell_per_family_enters_robustness = true by default
```

19A may choose a less brittle robustness entry rule:

```text
recommended alternative:
    top_2_to_3_train_selected_low_correlation_cells_per_family_enter_robustness

requirements:
    selected cells must be chosen by train-only or predeclared deterministic ranking
    low-correlation / non-redundancy rule must be frozen in 19A
    all tested family-cell pairs must be counted in N_tested_family_cell_pairs
    correction_scope must expand accordingly
```

Family-level search accounting:

```text
19A must freeze the family selection rule and maximum N_family cap.
Actual N_family_brought_to_robustness must be frozen in robustness_test_manifest after 19B0 train-only triage and before any robustness readout.
All families admitted to formal 19B robustness count toward family-level multiplicity.
PIT-blocked or data-contract-blocked families must remain in the manifest with blocking reason, but are not treated as tested families.
The family inclusion list cannot be revised after 19B0 train-only triage is frozen.
Robustness cannot be used to try many families and keep only survivors without correction.
```

Primary metric discipline:

```text
primary_metric = primary_tail_lift_50
primary_denominator = fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule
sensitivity_metrics = tail_lift_20, tail_lift_30, tail_lift_100, CCDF, MFE/MAE diagnostics
sensitivity metrics cannot rescue a failed primary metric
```

Family-level correction:

```text
correction_method ∈ {Bonferroni-Sidak, Benjamini-Hochberg FDR, deflated-threshold}
primary default = Bonferroni-Sidak unless 19A freezes another method with rationale
default_correction_scope = N_family_brought_to_robustness × primary_metric
default scope is valid only when exactly one train-selected cell per family enters 19B robustness
if multiple cells per family enter 19B robustness, correction_scope = N_tested_family_cell_pairs × primary_metric
tail_lift_20/30/100 remain sensitivity and must be reported separately if used
```

Margin rule:

```text
primary_margin_rule must be frozen in 19A before outcome readout.
recommended default:
    cluster_bootstrap_SE_p_candidate_50 =
        cluster bootstrap SE of p_candidate_50 on the primary denominator

    pre_frozen_corrected_margin_ratio =
        2 × cluster_bootstrap_SE_p_candidate_50 / p_matched_50

    equivalent probability-difference form:
        p_candidate_50 - p_matched_50 >= 2 × cluster_bootstrap_SE_p_candidate_50
The margin may combine a fixed effect-size floor and a corrected bootstrap / randomization threshold.
The null distribution must resample or rerandomize the matched baseline so denominator uncertainty in p_matched_50 is included.
The margin cannot be tuned after seeing train, robustness or validation results.
The margin should explicitly account for train-to-robustness winner's-curse shrinkage from train-selected family/cell effects.
```

Allowed parameter families:

```text
ret_20_threshold
amount_z_threshold
distance_to_high_120_threshold
volatility_contraction_threshold
cooldown
regime_filter
```

Selection discipline:

```text
selected rule must come from train-only ranking or predeclared deterministic rule ranking
one train-selected cell per family enters robustness by default
validation cannot select
robustness confirmation happens only in 19B, not in 19B0
failed cells remain counted
family-level corrected failures remain counted
```

### 5.5 Disallowed sources

不允许：

```text
realized winner episode membership
future max return / max drawdown thresholds as filters
post-entry path shape or future phase labels
any field whose source_pos > decision_pos
validation-selected event family
validation-selected grid cell
current concept/theme membership retroactively used as historical feature
```

### 5.6 Sampling geometry inheritance

EP19 must inherit the sampling caution from EP16A: raw trigger count is not independent sample count.

Required reuse of 16A-style discipline:

```text
instrument-level cooldown accounting
same-instrument overlap accounting
episode-or-event cluster id for bootstrap
calendar-month and instrument-month support
effective_sample_size_readout
validation_effective_sample_size_after_censoring
cluster-aware bootstrap, not row-only bootstrap
```

19A must freeze minimum effective-sample support after censoring for each split, especially validation. If `path_complete_120 = true` and purge/embargo make validation too thin, validation stress status must be downgraded to underpowered rather than used as a strong veto.

Any report that presents row count without cluster/effective-sample context is incomplete. If repeated triggers from the same instrument/month dominate the evidence, EP19 must downgrade enrichment and utility claims to diagnostic-only.

## 6. Phase Plan

### Phase 19A: Lineage / Tradability / Data Contract

目标：冻结 EP19 的 denominator、entry timing、candidate source list、PIT audit、fill-feasibility audit、forward labels、baseline budget、industry/board/theme data status、dedup/cooldown rules 和 grid-search search space。

关键输出：

```text
input_artifact_audit.csv
entry_candidate_lineage_audit.csv
pit_feature_availability_audit.csv
entry_execution_convention_audit.csv
entry_fill_feasibility_audit.csv
event_canonicalization_audit.csv
cooldown_audit.csv
split_construction_freeze.csv
forward_outcome_label_freeze.csv
censoring_treatment_freeze.csv
candidate_density_and_overlap_audit.csv
effective_sample_size_readout.csv
industry_data_contract.csv
industry_pit_audit.csv
theme_snapshot_status.csv
baseline_budget_freeze.csv
baseline_matching_spec.csv
baseline_matching_quality_audit.csv
grid_search_manifest.csv
family_search_accounting_manifest.csv
robustness_test_manifest.csv
primary_metric_and_margin_freeze.csv
multiple_testing_correction_freeze.csv
validation_stress_rule_freeze.csv
replay_path_eligibility_freeze.csv
entry_universe_preflight_decision.csv
```

19A 的正向裁决只授权 19B0 fast rule-grid enrichment scan，不授权模型或策略。

### Phase 19B0: Fast Rule-Grid Enrichment Scan

目标：在 train split 上快速扫描预注册 simple event rules，决定哪些 family/cell 可进入 19B 的正式 robustness confirmation。

19B0 不训练模型，不输出策略，不读取 validation，不在 robustness 上做 support claim。它只做 train-only event-family / rule-family triage。

输入：

```text
candidate_panel.parquet
features already precomputed at t0
forward outcome labels readout-only
baseline budget frozen from 19A
grid_search_manifest frozen from 19A
```

Grid 限制：

```text
grid_parameter_n <= 5
grid_total_cells <= 300
family selection rule and N_family cap frozen from 19A
actual N_family_brought_to_robustness frozen before robustness readout
one_train_selected_cell_per_family_enters_robustness = true by default
top_2_to_3_low_correlation_cells_per_family allowed if frozen in 19A
validation must not be used for selection
robustness must not be used for 19B0 selection
all train grid cells counted in search accounting
all families selected for 19B counted in family-level search accounting
all tested family-cell pairs counted in N_tested_family_cell_pairs when expanded-cell rule is used
```

每个 cell 输出：

```text
family_id
grid_cell_id
split = train
candidate_n
tradable_n
instrument_n
instrument_month_n
cooldown_entry_n
primary_denominator_n
path_complete_120_n
primary_tail_lift_50
sensitivity_tail_lift_20
sensitivity_tail_lift_30
sensitivity_tail_lift_100
winner_capture_rate
candidate_per_winner
fast_fail_rate
false_repair_rate
MAE_20_p10
MFE_120_p90
top3_instrument_removed_tail_lift
matched_baseline_delta
train_primary_metric_rank
selected_for_19B_robustness_flag
blocking_reason
```

19B0 decision states:

```text
19B0_no_candidate_family_passed
19B0_candidate_family_train_diagnostic
19B0_candidate_family_eligible_for_19B
```

Only event/rule families and train-selected cells marked eligible by 19B0 may enter 19B formal readout. Eligibility is not support. Support requires 19B robustness confirmation under the predeclared primary metric, denominator, margin rule and correction scope. A failed 19B0 family cannot be rescued later by 19C oracle replay.

### Phase 19B: Robust Right-Tail Enrichment and False-Positive Burden Readout

目标：在冻结 denominator 上，衡量 candidate universe 的 right-tail enrichment、winner capture、false-positive burden 和 matched-baseline improvement。

19B 必须包含四张图：

```text
1. Tail Lift Curve
2. CCDF / Survival Curve
3. Capture vs Burden
4. MFE / MAE Joint Scatter
```

主读数：

```text
primary_tail_lift_50 by split
tested_family_cell_pair_n
sensitivity_tail_lift_20 / tail_lift_30 / tail_lift_100 by split
ccdf_candidate_vs_baseline
winner_capture_rate by split
candidate_per_winner
precision/lift vs eligible universe
precision/lift vs random same-budget baseline
precision/lift vs instrument/liquidity/regime matched baseline
robustness matched-baseline delta as primary gate
fast_fail_rate
false_repair_rate
MAE_20_p10 / MAE_20_p05
MFE_120_p75 / MFE_120_p90 / MFE_120_p95
MFE_to_MAE_ratio
top_1_instrument_removed_tail_lift
top_3_instruments_removed_tail_lift
cluster-aware bootstrap CI
```

19B primary pass requires:

```text
only 19B0 train-selected family/cell pairs are tested
robustness primary_tail_lift_50 on fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule >= 1.0 + pre_frozen_corrected_margin_ratio
and family-level multiple-testing correction pass
and candidate_per_winner below cap
and MAE_20_p10 not worse than matched baseline by more than tolerance
and top-k removal sensitivity pass
and matched-baseline quality gate pass
```

Recommended false-positive burden tolerance:

```text
mae_abs_worsening =
    matched_baseline_MAE_20_p10 - candidate_MAE_20_p10

absolute tolerance pass:
    mae_abs_worsening <= 0.02

or

relative tolerance pass:
    mae_relative_worsening <= 0.10
```

19A must freeze which tolerance form is primary before any 19B readout. If both are used, the conjunction/disjunction rule must be predeclared and any pass-on-either logic must be treated as an additional selection opportunity.

`tail_lift_20/30/100` are sensitivity readouts. They cannot substitute for a failed `primary_tail_lift_50` gate.

19B must also apply the predeclared validation stress rule after robustness pass/fail is determined. Validation cannot improve, select or tune anything. It may only confirm the stress readout or downgrade/veto a supported claim according to the frozen rule.

19B 仍不是 policy。它只判断 entry universe 是否值得继续。如果 robustness matched-baseline delta 失败，19B 不得继续进入 19C，并且不能用 oracle headroom 去救一个没有 OOS 富集的 entry universe。

### Phase 19C: Entry-Conditioned Oracle + CTA-Style Replay Headroom

目标：在真实 candidate denominator 上重测 EP17/EP18 中的 oracle headroom，并比较 simple CTA-style right-tail participation arms，而不是沿用 realized-winner universe 的 O5/O2。

19C replay denominator:

```text
fill_feasible ∩ cooldown_entry_rows ∩ replay_path_eligible_rows_under_frozen_replay_horizon_rule
```

`replay_path_eligible_rows` must be frozen in 19A by replay arm and maximum required path horizon. It is separate from the 19B `label_eligible_rows_under_frozen_censoring_rule`, which is tied to the 120-session right-tail label.

Replay arms:

```text
A. random same-budget entry + fixed exit
B. candidate entry + fixed horizon
C. candidate entry + hard stop
D. candidate entry + ATR trailing
E. candidate entry + EMA trailing
F. candidate entry + simple staged upgrade
G. candidate entry + oracle exit
```

These are not strategy authorization. They are entry-conditioned action-space headroom diagnostics.

主读数：

```text
blind_entry_continue_baseline
after-cost entry expectancy
O5_entry_conditioned_perfect_utility
O2_entry_conditioned_drawdown_oracle
MFE capture ratio
MAE avoided
R-multiple distribution
return per exposure-day
stop hit rate
winner retention
turnover
post-entry payoff retention
post-entry false-positive cost
fill-adjusted opportunity loss
limit-up unfilled rate
limit-down exit failure rate
```

If candidate + simple CTA exit cannot beat random same-budget CTA, the event universe has weak trading value even if it shows diagnostic right-tail enrichment.

19C must recompute O5/O2 from the entry-conditioned denominator. EP17/EP18 O5/O2 values are reference-only and must not be copied. Cost assumptions must be frozen in 19A and should include at minimum commission/slippage, stamp-tax side effects where relevant, limit-up fill premium/blocked-fill handling, and next-open execution delay.

### Phase 19D: Separability Readiness Diagnostic

目标：不训练最终 entry policy，只判断是否存在足够支持下一步 EP20 的 separability surface。

允许读数：

```text
simple train-only ranking probe
time-split OOS rank IC
decile monotonicity
tail-lift preservation by score bucket
MFE / MAE tradeoff by score bucket
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
19_entry_universe_pit_tradability_and_enrichment_supported
  -> may authorize requirement_20_entry_universe_separability_or_policy_preflight.md

19_entry_universe_enrichment_only_diagnostic
  -> representation/opportunity exists, but no policy preflight

19_entry_universe_validation_stress_failed_diagnostic
  -> robustness support exists, but validation stress rule downgrades support claim

19_entry_universe_not_tradeable
  -> no deployable entry universe; close Big Winner active entry path

19_entry_universe_lineage_blocked
  -> PIT/tradability/denominator/data contract failed

19_entry_universe_search_overfit_blocked
  -> grid/search discipline failed; close or rerun from 19A contract
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
event_canonicalization_gate
cooldown_entry_denominator_gate
primary_enrichment_denominator_gate
censoring_treatment_gate
industry_data_contract_gate
industry_pit_gate
theme_snapshot_status_gate
sample_support_gate
candidate_density_gate
effective_sample_size_gate
baseline_budget_gate
baseline_matching_quality_gate
split_stability_gate
primary_metric_margin_freeze_gate
validation_stress_gate
tail_enrichment_robustness_gate
matched_baseline_improvement_gate
false_positive_burden_gate
top_k_contribution_sensitivity_gate
replay_path_eligibility_gate
entry_conditioned_o5_headroom_gate
cta_replay_headroom_gate
search_accounting_gate
family_level_multiplicity_gate
no_policy_authorization_gate
```

Critical blocking gates:

```text
pit_lineage_gate
fill_feasibility_gate
winner_membership_independence_gate
cooldown_entry_denominator_gate
primary_enrichment_denominator_gate
censoring_treatment_gate
split_stability_gate
primary_metric_margin_freeze_gate
baseline_matching_quality_gate
matched_baseline_improvement_gate
validation_stress_gate
search_accounting_gate
family_level_multiplicity_gate
```

Failure of any critical blocking gate prevents support for 19B/EP20. Other hard gates remain mandatory report requirements; if they fail, the report must state whether the failure blocks the phase, downgrades claims to diagnostic-only, or invalidates a specific candidate family such as B3.

### 7.1 Tail enrichment robustness gate

```text
Candidate universe must beat matched baseline on robustness split
for the single predeclared primary metric:
    primary_tail_lift_50

The primary metric must be computed on:
    fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule

tail_lift_20 / tail_lift_30 / tail_lift_100 are sensitivity metrics only.

Primary pass uses the ratio rule:
    primary_tail_lift_50 >= 1.0 + pre_frozen_corrected_margin_ratio
```

### 7.2 False-positive burden gate

```text
Candidate universe must not have unacceptable:
    fast_fail_rate
    false_repair_rate
    MAE_20 left-tail
    candidate_per_winner burden
```

### 7.3 Event duplication gate

```text
Primary readout must be based on fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule.
Raw trigger enrichment cannot be used for support claim.
```

### 7.4 Search accounting gate

```text
All grid cells must be counted.
All families brought to robustness must be counted as N_family.
Selected rule must come from train-only or predeclared rule ranking.
By default, exactly one train-selected cell per family can enter 19B robustness.
If more cells enter robustness, N_tested_family_cell_pairs replaces N_family in the correction scope.
Validation cannot select.
Robustness must confirm.
Family-level multiple-testing correction must pass.
Primary metric, margin rule and correction method must be frozen in 19A.
Robustness survivors cannot be used as an uncorrected selection set.
```

### 7.5 Censoring and matching gate

```text
120-session right-censoring treatment must be frozen in 19A.
Candidate and baseline rows must use the same label eligibility / censoring rule.
Matched-baseline construction and quality thresholds must be frozen in 19A.
The primary margin cannot be tuned after seeing train, robustness or validation results.
Chronological split construction, purge/embargo, same-instrument overlap handling and label-horizon boundary handling must be frozen in 19A.
Validation stress downgrade/veto rule must be frozen in 19A.
```

Suggested non-final thresholds must be frozen in the 19A requirement, not in this plan. The plan-level intent is:

```text
1. Candidate universe must be large enough to evaluate.
2. Candidate universe must not be so dense that it becomes market exposure.
3. Winner enrichment must beat matched baselines, not just raw universe.
4. False-positive burden must be bounded.
5. Event duplication must be controlled by canonicalization and cooldown.
6. Entry-conditioned oracle and CTA-style headroom must remain material after costs.
7. Entry rows must be fill-feasible under A-share limit/suspension/liquidity constraints.
8. Industry/board/theme data must not introduce hindsight membership.
9. Cross-family search must be corrected, not just within-family grid search.
10. 120-session right-censoring must not be silently converted into non-winner labels.
```

## 8. Report Requirements for Future Implementations

Every EP19 report must state:

```text
EP19 is not a policy, not a backtest, and not a production signal.
```

Reports must include:

```text
1. candidate denominator and baseline denominator definitions
2. raw_trigger_rows / canonical_event_rows / cooldown_entry_rows definitions
3. primary_enrichment_denominator = fill_feasible ∩ cooldown_entry_rows ∩ label_eligible_rows_under_frozen_censoring_rule
4. PIT lineage and source_pos / decision_pos audit
5. entry execution convention
6. A-share fill feasibility: suspension, limit-up/limit-down, liquidity and impact proxy
7. forward outcome label definition and proof labels are readout-only
8. 120d censoring treatment and calendar coverage audit
9. split_construction_freeze and purge/embargo audit
10. candidate density, overlap and effective sample size by split, including validation after censoring
11. path_complete_120_rate and survival fallback trigger status
12. canonicalization_audit
13. cooldown_audit
14. industry_data_contract
15. industry_PIT_audit
16. theme_snapshot_status
17. B3 PIT prerequisite status
18. baseline_matching_spec
19. baseline_matching_quality_audit
20. primary baseline gate rule, baseline margin rule and primary_metric freeze
21. false-positive burden tolerance freeze
22. grid_search_manifest
23. grid_cell_count
24. train_selected_cell_per_family manifest
25. robustness_test_manifest and N_tested_family_cell_pairs
26. family_search_accounting_manifest, N_family cap and actual N_family tested
27. multiple_testing_correction_status
28. validation_stress_rule and validation_stress_status
29. primary_tail_lift_50
30. sensitivity_tail_lift_curve
31. CCDF / survival curve
32. capture_vs_burden
33. MFE_MAE_scatter
34. false-positive burden
35. matched baseline comparison
36. top-k contribution sensitivity
37. cluster_bootstrap_CI
38. critical blocking gate status
39. replay_path_eligibility_audit
40. entry-conditioned O5/O2 headroom
41. CTA-style replay baseline comparison
42. search accounting and validation non-use
43. final AFML interpretation
```

## 9. First Requirement to Generate

The next concrete artifact should be:

```text
requirement_19a_entry_universe_pit_lineage_tradability_and_data_contract.md
```

19A should not train a model. It should freeze the contract and the freeze protocol for:

```text
denominator
execution
labels
split construction / purge / embargo
baseline budget
baseline matching method and quality thresholds
primary metric
primary margin rule
margin default / override rationale, including 2 × cluster_bootstrap_SE if used
primary baseline gate rule
matched-baseline randomization null for p_matched_50 uncertainty
train-to-robustness shrinkage / winner's-curse treatment
120-session censoring treatment
survival-analysis fallback trigger and method
minimum effective-sample support after censoring by split
false-positive burden tolerance form and threshold
validation stress downgrade/veto rule
industry/board/theme data status
PIT industry primary source priority and concept/theme diagnostic-only status
dedup/cooldown rules
grid-search search space
family selection rule and N_family cap
one train-selected cell per family rule, or top-2-to-3 low-correlation cell rule with expanded tested-cell correction scope
family-level multiple-testing correction method
replay path eligibility by replay arm
```

The actual `N_family_brought_to_robustness`, selected family/cell pairs and correction scope must be frozen in `robustness_test_manifest.csv` after 19B0 train-only triage and before any robustness readout.

If needed, 19A may later be split into:

```text
19A1_denominator_tradability_contract
19A2_data_and_candidate_grid_contract
```

But the default is one 19A requirement to keep the restart simple.

If 19A cannot prove PIT membership, next-open executable entry timing, fill feasibility, forward-label independence, industry/theme data status, cooldown denominator integrity, primary enrichment denominator integrity, split construction, 120d censoring treatment, matched-baseline construction, pre-frozen margin rule, validation stress rule and family-level search accounting, EP19 should fail closed before any outcome readout.

## 10. Summary

EP19 changes the research object:

```text
from:
  realized-winner conditioned holding/exit states

to:
  no-hindsight PIT entry candidate universes
```

The central test is not whether a model can predict `winner_120`, but whether a candidate universe can show robust right-tail enrichment under matched baselines, acceptable false-positive burden, tradeable execution, and controlled event duplication.

EP19 does not authorize policy.

It only decides whether there is a PIT, fill-feasible, enrichment-supported entry universe worth taking into EP20.
