# 需求：18 Payoff-state Representation Research

## 0. Umbrella Requirement Role

This file is the top-level EP18 requirement authorized by EP17D:

```text
final_decision_state = oracle_payoff_state_research_allowed
recommended_next_requirement = requirement_18_payoff_state_representation_research.md
```

It is an umbrella requirement, not an executable runner requirement. Executable work must begin with:

```text
requirement_18a_payoff_state_contract_preflight.md
```

No EP18 phase may skip 18A.

## 1. Research Question

EP18 must answer:

```text
Can PIT-valid observable state rank a broad payoff-positive continuation region
well enough to reduce the gap between EP16 learned scores and EP17 O4/O5 oracle headroom?
```

The primary direction is payoff-state representation, not binary classification.

## 2. Non-negotiable Boundaries

EP18 may produce research diagnostics only. It must not authorize:

```text
entry policy
exit policy
holding policy
position sizing
portfolio construction
portfolio backtest
model deployment
production signal
live trading
```

Binary AUC, binary precision, and positive/negative confusion are appendix or sanity metrics only. They must not be used as primary gates.

## 3. Required Upstream Authorization

The EP17D decision must satisfy:

```text
final_decision_state = oracle_payoff_state_research_allowed
recommended_next_requirement = requirement_18_payoff_state_representation_research.md
lineage_gate = pass
contract_validation_gate = pass
o5_upper_bound_gate = pass
label_path_support_gate = pass
path_risk_support_gate = pass
payoff_preservation_support_gate = pass
current_feature_gap_gate = pass
delayed_decision_supported_gate = fail
capacity_execution_block_gate = not_evaluable_nonblocking
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

If this authorization cannot be replayed, EP18 must fail closed before 18A starts.

## 4. Phase Map

EP18 is decomposed into four ordered phases:

```text
18A = payoff-state target and feature contract preflight
18B = payoff-state feature matrix audit
18C = low-capacity payoff-state separability diagnostic
18D = learned payoff-state utility bridge and oracle-gap diagnostic
```

Allowed handoffs:

```text
18A_payoff_state_contract_ready -> requirement_18b_payoff_state_feature_matrix_audit.md
18B_payoff_state_feature_matrix_ready -> requirement_18c_payoff_state_separability_diagnostic.md
18C_payoff_state_separability_supported -> requirement_18d_payoff_state_oracle_gap_bridge.md
18D_payoff_state_policy_preflight_allowed -> requirement_19_payoff_state_policy_preflight.md
```

Each phase must fail closed if its hard gates fail. A blocked phase sets:

```text
next_allowed_requirement = none
```

## 5. Denominator Contract

EP18 primary target research must use the labelable full denominator:

```text
train labelable/binary/neutral = 20245 / 14962 / 5283
robustness labelable/binary/neutral = 2496 / 1872 / 624
validation labelable/binary/neutral = 664 / 505 / 159
```

Neutral rows must remain neutral. They must not be reclassified as positive or negative.

Oracle references must keep their native denominators:

```text
O5 perfect utility = labelable_full
O2 drawdown oracle = labelable_full
O4 label-positive primary = binary_primary
O4 high-upside top30/top20/top10 stress = labelable_full with train-frozen cutoffs
```

Any learned-vs-oracle bridge must align denominators explicitly:

```text
learned labelable_full utility bridge -> O5/O2 labelable_full reference
learned binary_primary restricted diagnostic -> O4 binary_primary reference
```

EP17D's `o5_vs_best_label_path_gap = 0.004786322905921601` is a mixed-denominator diagnostic readout:

```text
17D mixed gap = O5 labelable_full mean - O4 binary_primary mean
```

It may be cited only as upstream orientation. EP18D must recompute oracle gaps on aligned denominators and must not use this mixed gap as the learned-score headroom target.

## 6. Target Contract

EP18 target work must prioritize:

```text
continuous h20 payoff ranking
ordinal payoff-state representation
continue-advantage / action-value ranking
path-risk auxiliary diagnostics
neutral-aware utility decomposition
```

The O5 incremental identity is fixed as:

```text
continue_value = continue_net_return_h20
defend_value = defend_net_return_after_cost
o5_incremental = max(0, defend_value - continue_value)
```

Aggregate O5 incremental is the mean over the full `labelable_full` denominator. Non-defended rows contribute zero and must not be dropped.

All payoff quantile cutoffs used outside train must be train-frozen absolute values from the train labelable_full denominator:

```text
top30 cutoff = 0.0596330275229357
top20 cutoff = 0.1012285086722715
top10 cutoff = 0.1721071844362347
split_local_quantile_recompute = false
```

Top10 is an over-narrow stress only and must not become the primary target.

The payoff column used for ordinal cutoff assignment must share the same lineage hash as `y_payoff_h20`.

## 7. Feature Contract

Primary features must be observable at `t0` and PIT-valid. The following are forbidden as model features:

```text
future h20 payoff
future drawdown / drawup labels
oracle action labels
O1/O2/O4/O5 future labels
label_class if used as model feature
split id
instrument id as raw model feature
episode cluster id as raw model feature
validation / robustness outcome-derived columns
```

Delayed features are appendix-only unless a later requirement explicitly authorizes a separate delayed-state research branch. They are not primary EP18 features.

## 8. Terminal Decisions

Acceptable terminal research diagnostics include:

```text
18C_current_features_reconfirmed_insufficient
18C_payoff_state_signal_weak_or_nonmonotone
18C_binary_only_not_supported
18C_over_narrow_winner_target_blocked
18C_risk_only_no_payoff_state
18D_payoff_state_representation_diagnostic_only
18D_utility_bridge_not_supported
18D_oracle_gap_contract_blocked
18D_oracle_gap_not_reduced
18D_over_narrow_winner_bridge_blocked
```

These are valid research outcomes, not implementation failures. No runner may weaken gates, tune on robustness/validation, or switch back to binary primary metrics to avoid these decisions.

## 9. Search Accounting

Every EP18 phase must record:

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

## 10. Immediate Next Requirement

The only requirement authorized directly by this umbrella file is:

```text
requirement_18a_payoff_state_contract_preflight.md
```

18A may authorize 18B only after all 18A hard gates pass and `decision_state = 18A_payoff_state_contract_ready`.
