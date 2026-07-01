# EP18 Research Plan: Payoff-State Representation Research

创建日期：2026-07-01

## 0. 实验定位

EP18 承接 EP17D 的最终裁决：

```text
EP17 final_decision_state = oracle_payoff_state_research_allowed
recommended_next_requirement = requirement_18_payoff_state_representation_research.md
```

EP18 不是交易策略实验，也不是继续修 EP16 的 survival score。它的核心问题是：

```text
能否用 PIT-valid observable state 近似 EP17 中 O4/O5 暴露出的 payoff-positive action value?
```

EP17 已经给出三条关键事实：

```text
1. action space 有 oracle upper-bound value:
   O5 perfect utility robustness mean incremental = 2.9467%

2. payoff preservation 有宽状态价值:
   O4 label-positive primary robustness mean incremental = 2.4681%
   O4 top30 payoff stress pass
   O4 top20 payoff stress pass
   O4 top10 payoff stress fail

3. 当前 16C feature contract 不足:
   16X robustness payoff rank IC = 0.051877
   payoff-minus-survival margin = -0.000723
   payoff decile monotonicity Spearman = 0.163636
```

因此 EP18 的研究方向不是 binary classification，而是 payoff-state representation：用连续或 ordinal 的方式刻画未来 h20 payoff / action value，并检验这种表征是否能在 robustness split 上稳定排序收益幅度。

## 0.1 Current EP18 Status After 18C

18A/18B/18C 已经完成到低容量 separability diagnostic。18C 的实际结论是：

```text
decision_state = 18C_payoff_state_signal_weak_or_nonmonotone
next_allowed_requirement = none
all_hard_gates_pass = false
```

关键读数：

```text
robustness_payoff_rank_ic = 0.064398
rank_ic_materiality_floor = 0.080000
robustness_decile_payoff_monotonicity_spearman = 0.612121
robustness_cluster_bootstrap_rank_ic_ci_low = 0.020608
rank_ic_vs_volatility20d_delta = -0.000374
baseline_improvement_required_delta = +0.005000
```

解释：

```text
current F1-F5 feature set has weak positive payoff-ranking information
current F1-F5 feature set is not strong enough for a deferred oracle-gap bridge
current signal is participation-heavy and too concentrated in F2 features
current failure is not primarily risk-only, because F4 removal retention > 1
```

Therefore the next EP18 step is not learned-score oracle bridge. The next step is feature representation diagnostic:

```text
next_research_direction = payoff-state feature representation diagnostic
do_not_start = learned payoff-state utility bridge / oracle-gap bridge
```

## 1. Non-negotiable Scope

EP18 不做：

```text
不输出 entry policy
不输出 exit policy
不输出 holding policy
不做 position sizing
不做 portfolio construction
不做 portfolio backtest
不做 model deployment
不做 production signal
不做 live trading
不继续调 EP16 survival threshold
不启动 EP17 oracle action as strategy
不把 oracle future label 当作可部署信号
```

EP18 允许做：

```text
冻结 payoff-state target contract
冻结 PIT-valid feature contract
构造 payoff/action-value continuous and ordinal targets
构造 feature matrix
做低容量 separability diagnostic
做 feature representation diagnostic
在 representation 支持后再做 learned-score vs O4/O5 oracle gap bridge
```

所有正向结论最多授权下一步 research requirement，例如 payoff-state policy preflight；不得直接授权策略或回测。

## 2. 为什么 Binary 不再适合做主判定

EP18 明确把 binary classification 降级为辅助诊断，原因如下。

### 2.1 EP16 已证明 binary survival 可分但 utility 失败

16C/16D 的 survival / negative-risk binary score 有 OOS separability 和 precision lift，但 16E 的 full-denominator return utility 失败。也就是说：

```text
binary survival probability != payoff / utility ordering
```

### 2.2 EP17 证明价值来自宽 payoff-positive state

O4 top30/top20 stress 通过，top10 失败。下一步不能只预测极端 winner，也不能只做 positive/negative 二分。真正要学的是：

```text
足够宽、可观测、可迁移的 payoff-positive continuation state
```

### 2.3 Neutral 不可丢弃

EP16 neutral rows 占 labelable population 约 23%-26%。EP17 O5 证明 neutral rows 中存在可避免损失。EP18 不能再把 neutral 排除出主研究分母，也不能把 neutral 偷换成 positive 或 negative。

因此 EP18 的主目标应从：

```text
binary classification
```

转向：

```text
continuous payoff ranking
ordinal payoff-state representation
action-value / utility ranking
```

Binary AUC、binary precision、positive/negative confusion 只能作为 sanity check 或 auxiliary readout，不能作为 primary gate。

## 3. Upstream Evidence Contract

EP18 必须读取并复验以下上游裁决：

```text
17D final_decision_state = oracle_payoff_state_research_allowed
17D recommended_next_requirement = requirement_18_payoff_state_representation_research.md
17D payoff_preservation_support_gate = pass
17D path_risk_support_gate = pass
17D current_feature_gap_gate = pass
17D delayed_decision_supported_gate = fail
17D capacity_execution_block_gate = not_evaluable_nonblocking
```

必要参考指标：

```text
EP17 O5 robustness mean incremental = 0.0294674284 on labelable_full denominator (2,496 rows)
EP17 O2 robustness mean incremental = 0.0185108291 on labelable_full denominator (2,496 rows)
EP17 O4 label-positive robustness mean incremental = 0.0246811055 on binary_primary denominator (1,872 rows)
EP17 O4 top30 train cutoff = 0.0596330275 from train labelable_full denominator (20,245 rows)
EP17 O4 top20 train cutoff = 0.1012285087 from train labelable_full denominator (20,245 rows)
EP17 O4 top10 train cutoff = 0.1721071844 from train labelable_full denominator (20,245 rows)
EP17 O2 primary drawdown threshold = -0.10
16X robustness payoff rank IC baseline = 0.051877
16X robustness payoff decile monotonicity baseline = 0.163636
```

If EP17D artifacts are missing, stale, or inconsistent, EP18 must fail closed:

```text
decision_state = 18_upstream_oracle_contract_blocked
next_allowed_requirement = none
```

## 4. Primary Denominator

EP18 primary denominator inherits EP16/EP17 full labelable continuation states:

```text
threshold_id = up50pct
horizon = h20
sampling = full-horizon non-overlap continuation decision states
primary_denominator = labelable_full = positive + negative + neutral
```

Expected counts:

```text
split_bucket | labelable_step_n | binary_step_n | neutral_step_n
train        | 20,245           | 14,962        | 5,283
robustness   | 2,496            | 1,872         | 624
validation   | 664              | 505           | 159
```

Primary metrics must use `labelable_full` unless explicitly labeled as binary sanity readout. Binary-only denominators are not allowed for EP18 final decisions.

Oracle reference values must carry their source denominator and cannot be compared across denominators without an explicit bridge:

```text
O4 label-positive primary = binary_primary reference, not labelable_full reference
O5 perfect utility primary = labelable_full reference
O2 drawdown primary = labelable_full reference
EP18 learned payoff-state scores = labelable_full primary evaluation
```

Therefore the deferred oracle-gap bridge must report at least two aligned comparisons:

```text
1. labelable_full bridge:
   learned_score labelable_full utility / O5 labelable_full utility
   learned_score labelable_full utility / O2 labelable_full utility

2. binary_primary bridge:
   learned_score restricted to binary_primary / O4 binary_primary utility
```

The plan must not subtract `O4 binary_primary mean` directly from `learned labelable_full mean`. Any O4/O5 gap statement must identify denominator alignment.

EP17D's `o5_vs_best_label_path_gap = 0.004786322905921601` is inherited as a mixed-denominator diagnostic orientation only:

```text
17D mixed gap = O5 labelable_full mean - O4 binary_primary mean
```

The deferred oracle-gap bridge must recompute learned-score oracle gaps on aligned denominators. It must not use the 17D mixed gap as the learned-score headroom target.

## 5. Target Contract

EP18 uses a target stack, not a single binary label.

### 5.1 Continuous Payoff Target

Primary continuous target:

```text
y_payoff_h20 = realized h20 close-to-close return from step_start to step_end
```

Preferred source lineage:

```text
EP16/16C or 16E existing payoff/return column if available and hash-reconciled
qfq close replay only as audit or if existing column cannot support target contract
```

### 5.2 Action-value Targets

Define both signs explicitly:

```text
continue_value = continue_net_return_h20
defend_value   = defend_net_return_h20 under q_defend = 0.0, cost_bps = 50

continue_advantage = continue_value - defend_value
defend_advantage   = defend_value - continue_value
```

Payoff-state representation should primarily learn `continue_advantage` or `y_payoff_h20`, not `defend_advantage`. `defend_advantage` is an auxiliary risk/action target.

EP18A must include an "O5 incremental definition replay" section in `payoff_state_target_contract.md`. The required identity is:

```text
blind_continue_base = continue_value
o5_policy_value     = max(continue_value, defend_value)
o5_incremental      = o5_policy_value - blind_continue_base
                   = max(0, defend_value - continue_value)
                   = max(0, defend_advantage)
```

This identity must be validated on the EP17/17B O5 row-level proof before any learned oracle-gap bridge is interpreted. The target contract must state the baseline used by each target:

```text
y_payoff_h20        -> absolute continue payoff
continue_advantage  -> payoff-state continuation preference vs defend
defend_advantage    -> action-value defense preference vs continue
o5_incremental      -> positive part of defend_advantage under frozen action semantics
```

Aggregate O5 incremental is the mean over the full `labelable_full` denominator. Non-defended rows contribute zero and must not be dropped.

If learned-score utility bridge uses a different baseline than O5, the deferred oracle bridge must fail closed with `18F_oracle_gap_contract_blocked`.

### 5.3 Ordinal Payoff-state Target

Train-frozen absolute cutoffs from EP17 O4 high-upside stress:

```text
top30_cutoff = 0.0596330275
top20_cutoff = 0.1012285087
top10_cutoff = 0.1721071844
```

Cutoff freeze contract:

```text
cutoff_source_artifact = 17B oracle_high_upside_threshold_freeze.csv
cutoff_source_denominator = train labelable_full
cutoff_source_train_row_count = 20,245
split_local_recompute_used = false
robustness_applied_cutoff = train_absolute_payoff_cutoff
validation_applied_cutoff = train_absolute_payoff_cutoff
```

EP18A `payoff_cutoff_freeze.csv` must reproduce the source denominator, row count, quantile, absolute cutoff, and applied robustness/validation cutoffs. If the cutoff source denominator cannot be verified as train `labelable_full`, EP18A must fail closed.

The payoff column used for ordinal cutoff assignment must share the same lineage hash as `y_payoff_h20` in the target registry.

Ordinal payoff states:

```text
state_0 = below_top30_payoff
state_1 = top30_to_top20_payoff
state_2 = top20_to_top10_payoff
state_3 = top10_extreme_payoff
```

Interpretation:

```text
state_1/state_2 are primary payoff-positive regions.
state_3 is over-narrow extreme winner stress, not the primary objective.
```

Robustness and validation must use the same train-frozen absolute cutoffs. Split-local quantile recomputation is prohibited.

### 5.4 Path-risk Auxiliary Target

O2 drawdown path-risk remains valuable but not final:

```text
y_signed_max_drawdown_h20
risk_state_dd08 = signed_drawdown <= -0.08
risk_state_dd10 = signed_drawdown <= -0.10
risk_state_dd12 = signed_drawdown <= -0.12
```

These targets are auxiliary. They can explain downside risk, but cannot replace payoff-state target as the primary research objective.

### 5.5 Binary Sanity Targets

Allowed only as sanity or auxiliary readout:

```text
16B label_class positive / negative / neutral
binary positive vs negative
drawdown yes/no
top30 yes/no
top20 yes/no
```

Binary AUC or precision cannot be an EP18 primary pass gate.

## 6. Feature Representation Hypotheses

EP18 should test whether observable state can represent payoff-positive continuation. Feature construction must be PIT-valid and t0-available.

Candidate feature families:

### F1. Continuation strength / repair persistence

Examples:

```text
rank persistence
moving-average spread and slope
distance to recent high/low
repair range persistence
post-repair volatility compression / expansion
```

### F2. Participation / sponsorship

Examples:

```text
turnover and amount z-scores
turnover persistence
money participation relative to board/universe
volume-price confirmation
```

### F3. Cross-sectional leadership

Examples:

```text
cross-sectional return rank
rank improvement persistence
board-relative strength
industry-relative strength if PIT industry data exists
leader-follower diffusion if source exists
```

### F4. Path-risk decoupling

Examples:

```text
signed drawdown risk proxies
intraday / rolling range
volatility_20d and volatility_60d
downside acceleration
failed-repair context proxies
```

### F5. Regime / board / market context

Examples:

```text
risk_on / risk_off if PIT audit passes
board bucket
market breadth
index trend and dispersion
```

### F6. Delayed observed-state appendix

EP17 timing result is not final, but k=3 has signal. EP18 may include an appendix-only delayed feature readout:

```text
t0 + 3 observed-state features
```

This cannot drive primary decision unless a separate delayed requirement is authorized.

Delayed observed-state features are prohibited from the EP18 primary model:

```text
delayed_features_used_in_primary_model = false
```

If delayed features are materialized, they must be stored and reported under appendix/readout artifacts only. Any primary 18C model using t0+k features must fail search accounting.

### F7. External feature families

Order-flow, news, catalyst, limit-up-chain, and industry diffusion should only be included if source artifacts already exist or can be made PIT-valid. EP18 must not assume unavailable external data.

## 7. Phase Plan

### EP18A: Payoff-state Target and Feature Contract Preflight

Goal:

```text
freeze denominator
freeze continuous / ordinal / action-value targets
freeze train-only payoff cutoffs
freeze feature source inventory
freeze leakage rules
```

EP18A does not train models and does not evaluate separability.

Required outputs:

```text
payoff_state_target_contract.md
payoff_state_feature_contract.md
tables/target_denominator_reconciliation.csv
tables/payoff_cutoff_freeze.csv
tables/oracle_reference_denominator_map.csv
tables/o5_incremental_definition_replay.csv
tables/target_distribution_readout.csv
tables/feature_source_inventory.csv
tables/leakage_forbidden_column_audit.csv
reports/payoff_state_contract_preflight_report.md
```

Pass gates:

```text
denominator_reconciliation_gate = pass
target_lineage_gate = pass
train_frozen_cutoff_gate = pass
oracle_reference_denominator_gate = pass
o5_incremental_definition_replay_gate = pass
neutral_preservation_gate = pass
feature_source_pit_gate = pass
leakage_forbidden_column_gate = pass
search_accounting_gate = pass
```

Possible decisions:

```text
18A_payoff_state_contract_ready
18A_target_lineage_blocked
18A_feature_source_pit_blocked
18A_denominator_reconciliation_blocked
18A_oracle_reference_denominator_blocked
18A_o5_incremental_contract_blocked
```

Only `18A_payoff_state_contract_ready` may authorize EP18B.

### EP18B: Payoff-state Feature Matrix and Representation Audit

Goal:

```text
materialize PIT-valid t0 feature matrix
bind feature rows to payoff-state targets
audit missingness, leakage, stationarity, split drift, and feature-family coverage
```

EP18B may compute target distribution by feature-family buckets for diagnostics, but must not select model features from robustness/validation.

Required outputs:

```text
tables/payoff_state_feature_matrix_schema.csv
tables/feature_missingness_audit.csv
tables/feature_lineage_audit.csv
tables/feature_family_coverage.csv
tables/train_only_preprocessing_audit.csv
tables/split_drift_feature_readout.csv
tables/feature_target_binding_audit.csv
reports/payoff_state_feature_matrix_audit_report.md
```

Pass gates:

```text
feature_complete_rate_gate = pass
feature_lineage_gate = pass
train_only_preprocessing_gate = pass
forbidden_feature_gate = pass
split_binding_gate = pass
```

Possible decisions:

```text
18B_payoff_state_feature_matrix_ready
18B_feature_lineage_blocked
18B_feature_matrix_low_coverage
18B_target_binding_blocked
```

Only `18B_payoff_state_feature_matrix_ready` may authorize EP18C.

### EP18C: Low-capacity Payoff-state Separability Diagnostic

Goal:

```text
test whether PIT-valid t0 features can rank payoff / continue_advantage out-of-sample
```

Primary model family should be low-capacity:

```text
ridge regression / elastic net for continuous payoff
ordinal regression or monotone bucket score for ordinal payoff state
ridge logistic for top30/top20 binary sanity only
single shallow tree as diagnostic readout only
```

Baselines:

```text
intercept / unconditional baseline
16C 27-feature baseline
16X payoff probe baseline
simple volatility_20d defense baseline
```

Primary robustness metrics:

```text
payoff_rank_ic
continue_advantage_rank_ic
decile_payoff_monotonicity_spearman
top3_minus_bottom3_payoff_gap
top30_payoff_state_lift
top20_payoff_state_lift
cluster_bootstrap_rank_ic_ci_low
top-k removal sensitivity
```

Materiality and baseline gates:

```text
robustness_payoff_rank_ic >= 0.080000
robustness_decile_monotonicity_spearman >= 0.600000
cluster_bootstrap_ci_low > 0
primary_rank_ic - volatility20d_defense_rank_ic > 0.005000
payoff score must not rely on split-local threshold recomputation
16X payoff probe is external coarse context only, not a hard baseline gate
```

Binary metrics:

```text
binary AUC
average precision
precision lift
```

are appendix/sanity metrics only.

Required outputs:

```text
tables/payoff_state_model_cv_readout.csv
tables/payoff_state_oos_rank_readout.csv
tables/payoff_state_decile_monotonicity.csv
tables/payoff_state_bucket_lift.csv
tables/payoff_state_bootstrap_ci.csv
tables/baseline_comparison_vs_16x.csv
tables/binary_sanity_readout.csv
figures/payoff_state_decile_curve.png
figures/score_vs_payoff_rank_surface.png
reports/payoff_state_separability_diagnostic_report.md
```

Possible decisions:

```text
18C_payoff_state_separability_supported
18C_payoff_state_signal_weak_or_nonmonotone
18C_current_features_reconfirmed_insufficient
18C_binary_only_not_supported
18C_over_narrow_winner_target_blocked
18C_risk_only_no_payoff_state
```

Only `18C_payoff_state_separability_supported` may authorize the deferred oracle bridge. The actual 18C state `18C_payoff_state_signal_weak_or_nonmonotone` does not authorize that bridge; it redirects the research plan to EP18D feature representation diagnostic.

18C actual result:

```text
decision_state = 18C_payoff_state_signal_weak_or_nonmonotone
next_allowed_requirement = none
rank_ic_support_gate = fail
baseline_improvement_gate = fail
monotonicity_support_gate = pass
bucket_lift_gate = pass
bootstrap_ci_gate = pass
risk_only_gate = pass
```

Interpretation:

```text
current feature representation is insufficient for oracle-gap bridge
weak signal is present, but not strong enough and not better than same-denominator volatility baseline
capacity-vs-representation is thin-margin: depth-2 tree IC is close to the 0.080 floor
do not weaken gates, switch to binary primary target, or start utility bridge
```

The next research phase should be a feature representation diagnostic, not the oracle-gap bridge.

### EP18D: Payoff-state Feature Representation Diagnostic

Goal:

```text
diagnose why the current PIT-valid t0 feature representation is too weak for broad payoff-state ranking
identify missing observable state dimensions before refreshing 18B/18C
```

Primary questions:

```text
Q1. Which payoff morphology information is missing from current F1-F5?
Q2. Is the current weak signal mostly participation/sponsorship rather than payoff-state shape?
Q3. Which candidate feature families can be PIT-valid and t0-available?
Q4. Can candidate features be justified by lineage before any target-correlation selection?
Q5. Which feature families should be added to a refreshed feature matrix for a new separability run?
```

Candidate representation families to audit:

```text
M1 episode-local morphology:
   low reclaim quality, high reclaim quality, distance from episode low/high,
   repair slope, drawdown recovery shape, close location in recent range,
   path entropy, transition entropy, repair path efficiency

M2 supply and pressure:
   turnover compression/expansion, volume dry-up after low, money-flow persistence,
   signed money-flow inflow/outflow proxy, positive/negative money-flow share,
   price-flow divergence, abnormal participation decay, high-volume failure bars

M3 payoff asymmetry context:
   upside room proxy, downside crowding proxy, recent failed breakout count,
   volatility-adjusted repair strength, upside/downside path entropy imbalance

M4 regime and cross-sectional context:
   board-relative leadership drift, industry/market context if PIT-valid,
   largecap/smallcap regime interaction, market beta state if available

M5 episode position and maturity:
   bars since episode low, bars since reclaim, episode age, local trend phase,
   non-overlap step position diagnostics
```

Required diagnostics:

```text
capacity_vs_representation_readout.csv
capacity threshold sensitivity and bounded depth<=4 train-only probe
candidate_feature_inventory.csv
candidate_feature_lineage_audit.csv
candidate_feature_pit_availability_audit.csv
current_feature_gap_decomposition.csv
payoff_morphology_proxy_readout.csv
feature_family_candidate_prioritization.csv
representation_refresh_decision.csv
payoff_state_feature_representation_diagnostic_report.md
```

Allowed positive output:

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
```

Allowed blocked outputs:

```text
18D_feature_representation_contract_blocked
18D_no_pit_valid_candidate_features_found
18D_candidate_features_delayed_or_leaky
18D_representation_gap_diagnostic_only
```

EP18D must not train the final payoff separability model and must not authorize policy, backtest, deployment, production signal, or trading. Its role is to define a better feature representation contract for a refreshed 18B/18C-style cycle.

### EP18E: Payoff-state Feature Matrix Refresh

Goal:

```text
materialize the feature-family recommendations from EP18D into a refreshed
PIT-valid, t0-available feature matrix contract before rerunning separability
```

EP18E may start only after EP18D emits:

```text
decision_state = 18D_feature_representation_refresh_supported
next_allowed_requirement = requirement_18e_payoff_state_feature_matrix_refresh.md
```

EP18E must not train a final payoff separability model and must not run a utility bridge. It should refresh source lineage, feature formulas, train-only preprocessing, PIT/t0 availability, and matrix schema for the prioritized families from EP18D.

Primary diagnostics:

```text
refreshed candidate source audit
refreshed candidate feature formula registry
refreshed feature lineage/PIT/t0 audit
train-only preprocessing contract
refreshed feature matrix schema
neutral-preserving target alignment
search accounting for no robustness/validation feature selection
```

EP18E remains a representation-construction step. It does not authorize entry, exit, holding, portfolio backtest, deployment, production signal, or live trading.

Required outputs:

```text
tables/refreshed_feature_source_audit.csv
tables/refreshed_feature_formula_registry.csv
tables/refreshed_feature_lineage_audit.csv
tables/refreshed_feature_matrix_schema.csv
tables/refreshed_feature_matrix_decision.csv
reports/payoff_state_feature_matrix_refresh_report.md
```

Possible decisions:

```text
18E_payoff_state_feature_matrix_refresh_supported
18E_feature_matrix_refresh_contract_blocked
18E_no_refresh_candidate_family_supported
18E_feature_matrix_refresh_diagnostic_only
```

### EP18F: Deferred Learned Payoff-state Utility Bridge and Oracle Gap

Goal:

```text
compare learned payoff-state score to EP17 O4/O5 oracle headroom
without claiming an entry/exit/holding strategy
```

EP18F may start only after a future separability diagnostic on the refreshed
feature matrix emits:

```text
decision_state = 18C_payoff_state_separability_supported
```

EP18F may use train-frozen score operating points only. It must not tune thresholds on robustness or validation.

Primary diagnostics:

```text
learned_score full-denominator utility at train-frozen operating points
positive sacrifice vs negative/neutral avoidance
top30/top20 payoff-state retention
O4 oracle approximation ratio
O5 upper-bound gap remaining
neutral contribution
top-k removal
cluster bootstrap
validation stress
```

Utility bridge is not a portfolio backtest. It is a single-step diagnostic comparable to EP16/EP17.

Required outputs:

```text
tables/learned_payoff_state_utility_bridge.csv
tables/oracle_gap_bridge.csv
tables/payoff_state_six_cell_decomposition.csv
tables/score_operating_point_freeze.csv
tables/topk_bootstrap_utility_bridge.csv
figures/oracle_gap_bridge_curve.png
figures/positive_sacrifice_vs_payoff_preservation.png
reports/payoff_state_oracle_gap_bridge_report.md
```

Possible decisions:

```text
18F_payoff_state_policy_preflight_allowed
18F_payoff_state_representation_diagnostic_only
18F_utility_bridge_not_supported
18F_oracle_gap_contract_blocked
18F_oracle_gap_not_reduced
18F_over_narrow_winner_bridge_blocked
```

If `18F_payoff_state_policy_preflight_allowed`, next allowed requirement may be:

```text
requirement_19_payoff_state_policy_preflight.md
```

This still does not authorize entry, exit, holding, portfolio backtest, deployment, production signal, or live trading.

## 8. Primary Gates and Failure Modes

### 8.1 Primary support gate

EP18 support requires all of:

```text
payoff ranking clears 0.080000 materiality floor
payoff ranking improves over same-denominator volatility20d baseline by > 0.005000
16X remains external coarse context only
decile payoff curve is monotone enough in robustness
top30/top20 payoff-state readouts are positive
top10 is treated as over-narrow stress, not selected as primary
cluster bootstrap CI low > 0
top-k removal does not erase signal
neutral contribution is explicitly reconciled
validation does not hard reverse
```

EP18 should be expected to fail cleanly if current observable feature families cannot clear materiality or same-denominator baseline gates. This is a valid research outcome, not an implementation failure. The plan explicitly treats the following as acceptable terminal diagnostics:

```text
18C_current_features_reconfirmed_insufficient
18C_payoff_state_signal_weak_or_nonmonotone
18C_binary_only_not_supported
18C_over_narrow_winner_target_blocked
18C_risk_only_no_payoff_state
18D_representation_gap_diagnostic_only
18E_feature_matrix_refresh_diagnostic_only
18F_payoff_state_representation_diagnostic_only
18F_utility_bridge_not_supported
18F_oracle_gap_contract_blocked
18F_oracle_gap_not_reduced
18F_over_narrow_winner_bridge_blocked
```

No runner may weaken gates, add robustness-tuned features, or switch to a binary primary target merely to avoid these decisions.

### 8.2 Binary-only failure

If binary AUC / precision improves but payoff rank IC, monotonicity, or utility bridge fails:

```text
decision_state = 18C_binary_only_not_supported
```

Interpretation:

```text
classification signal exists but remains unsuitable for payoff-state action value
```

### 8.3 Over-narrow winner failure

If top10-like target looks good in train but fails robustness during EP18C:

```text
decision_state = 18C_over_narrow_winner_target_blocked
```

If a learned utility bridge in EP18F relies on an over-narrow top10-like operating point and causes large positive sacrifice:

```text
decision_state = 18F_over_narrow_winner_bridge_blocked
```

Interpretation:

```text
research is rediscovering the EP17 top10 failure mode
```

### 8.4 Risk-only failure

If drawdown-risk features work but payoff-state ranking fails:

```text
decision_state = 18C_risk_only_no_payoff_state
```

Interpretation:

```text
do not convert this into exit policy; possible future risk-budget research only
```

## 9. Search Accounting

EP18 must record:

```text
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
validation_used_for_selection = false
robustness_used_for_tuning = false
split_local_quantile_recompute = false
binary_metric_used_as_primary_gate = false
top10_extreme_winner_used_as_primary_target = false
delayed_features_used_in_primary_model = false
```

All preprocessing must be train-only. All thresholds used outside train must be train-frozen absolute values.

## 10. Expected Directory Structure

Expected artifacts:

```text
configs/
  config_18a_payoff_state_contract_preflight.yaml
  config_18b_payoff_state_feature_matrix_audit.yaml
  config_18c_payoff_state_separability_diagnostic.yaml
  config_18d_payoff_state_feature_representation_diagnostic.yaml
  config_18e_payoff_state_feature_matrix_refresh.yaml
  config_18f_payoff_state_oracle_gap_bridge.yaml

requirement_18_payoff_state_representation_research.md
requirement_18a_payoff_state_contract_preflight.md
requirement_18b_payoff_state_feature_matrix_audit.md
requirement_18c_payoff_state_separability_diagnostic.md
requirement_18d_payoff_state_feature_representation_diagnostic.md
requirement_18e_payoff_state_feature_matrix_refresh.md
requirement_18f_payoff_state_oracle_gap_bridge.md

outputs/publishable/reports/
  payoff_state_contract_preflight_report.md
  payoff_state_feature_matrix_audit_report.md
  payoff_state_separability_diagnostic_report.md
  payoff_state_feature_representation_diagnostic_report.md
  payoff_state_feature_matrix_refresh_report.md
  payoff_state_oracle_gap_bridge_report.md
```

`requirement_18_payoff_state_representation_research.md` is the top-level requirement name authorized by EP17D. The `18a/18b/18c/18d/18e/18f` requirement files are phase decompositions under that umbrella. Any handoff check from EP17D should look for the top-level requirement first, then phase-specific requirements once EP18A begins.

## 11. Final Research Direction

EP18 should be judged by whether it can answer this question:

```text
Can PIT-valid observable state rank a broad payoff-positive continuation region
well enough to reduce the gap between EP16 learned scores and EP17 O4/O5 oracle headroom?
```

The correct direction is not:

```text
find a better binary classifier
find only top10 extreme winners
turn drawdown risk into an exit policy
use delayed k=3 as a strategy
start capacity or portfolio backtest
```

The correct direction is:

```text
continuous / ordinal payoff-state representation
wide top30/top20 payoff-positive state
neutral-aware full-denominator utility
path-risk as auxiliary context
feature representation diagnostic after weak separability
strict OOS payoff ranking before oracle-gap bridge
```
