# 需求：18A Payoff-state Target and Feature Contract Preflight

## 0. Non-negotiable Scope

18A 是 EP18 的第一个可执行 phase。EP18 承接 EP17D 的研究授权：

```text
final_decision_state = oracle_payoff_state_research_allowed
recommended_next_requirement = requirement_18_payoff_state_representation_research.md
```

18A 只回答一个前置问题：

```text
在不训练模型、不做 separability、不定义 policy 的前提下，
能否把 payoff-state target、oracle reference denominator、O5 action-value identity、
train-frozen payoff cutoffs、neutral-preserving denominator、PIT-valid feature source inventory
冻结为可复验的 EP18 target / feature contract？
```

18A 的唯一正向裁决是：

```text
decision_state = 18A_payoff_state_contract_ready
next_allowed_requirement = requirement_18b_payoff_state_feature_matrix_audit.md
```

18A 不得输出：

```text
model training
model refit
feature selection
feature engineering search
payoff separability result
binary AUC as primary result
score threshold
entry policy
exit policy
holding policy
position sizing
portfolio construction
portfolio backtest
deployment authorization
production signal
live trading authorization
```

18A 可以重新计算或重放 payoff / action-value / drawdown fields，但仅限于 target lineage、contract reconciliation 和 sanity replay。18A 不得把任何 target distribution 或 feature bucket readout 解释为可交易 edge。

If any upstream decision, denominator, target lineage, oracle reference denominator, O5 identity, cutoff freeze, feature source PIT, leakage, or search-accounting check fails, 18A must fail closed with the most specific blocked decision defined in §12. `18A_target_contract_blocked` may only be used for otherwise unclassified target-contract failures.

```text
decision_state = one of the blocked decisions listed in §12
next_allowed_requirement = none
```

## 1. Identity

```text
experiment_id = 18_payoff_state_representation_research
phase_id = 18A
run_id = 18A_payoff_state_contract_preflight
requirement_file = requirement_18a_payoff_state_contract_preflight.md
config_file = configs/config_18a_payoff_state_contract_preflight.yaml
runner_file = src/run_18a_payoff_state_contract_preflight.py
test_file = tests/test_18a_payoff_state_contract_preflight.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths must be repo-relative or resolver-alias based. Do not hard-code author-machine absolute paths. Artifact identity must use content hash, schema, lineage role, row counts, and row-key reconciliation as primary identity. An older manifest absolute path such as `/home/...` is never sufficient reason to fail if content hash, schema, relative role, and row keys reconcile.

## 2. Upstream Authorization Gate

18A is authorized only if EP17D selected payoff-state representation research.

Required 17D final decision:

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

Required EP17 orientation:

```text
O5 perfect utility proves labelable_full action-space upper bound.
O4 payoff preservation passes but O4 label-positive primary is binary_primary, not labelable_full.
O4 top30/top20 high-upside stress pass on train-frozen cutoffs.
O4 top10 high-upside stress fails and must remain over-narrow stress.
O2 drawdown path-risk passes but is auxiliary, not final target.
EP16/16X current feature contract is insufficient for payoff-state ranking.
```

If EP17D artifacts are missing, stale, schema-incompatible, or internally inconsistent:

```text
decision_state = 18_upstream_oracle_contract_blocked
next_allowed_requirement = none
```

## 3. Research Questions

18A answers eight contract questions.

```text
Q1. Can the EP16/EP17 labelable, binary, and neutral denominators be reconciled
    across train / robustness / validation without mixing utility and binary denominators?

Q2. Can EP17 O5, O2, and O4 reference values be mapped to their correct source
    denominators so that later oracle-gap bridge cannot compare unmatched denominators?

Q3. Can the O5 incremental definition be replayed as
    max(0, defend_value - continue_value) under q_defend=0.0 and cost_bps=50?

Q4. Can train-frozen O4 top30/top20/top10 payoff cutoffs be reproduced from
    train labelable_full row count = 20,245, with no split-local recomputation?

Q5. Can continuous, action-value, ordinal, path-risk, and binary-sanity target
    columns be defined with explicit lineage and sign conventions?

Q6. Can neutral rows be preserved in target and denominator contracts rather than
    dropped, relabeled, or hidden in a binary-only denominator?

Q7. Can PIT-valid feature source families be inventoried and separated into
    primary t0 feature candidates vs appendix-only delayed or unavailable external sources?

Q8. Can search accounting prove that 18A performed no model training, no feature
    selection, no threshold tuning, no separability, and no policy/backtest/deployment?
```

All failures are fail-closed and must map to a specific 18A blocking decision.

## 4. Allowed And Forbidden Work

18A may:

1. Read EP17D, EP17C, EP17B, EP16X, EP16E, EP16C, and EP16B publishable tables, reports, and manifests.
2. Read local row-level caches only after hash/schema/key validation.
3. Recompute or replay payoff, defend/continue action values, O5 incremental identity, and signed drawdown strictly for target-lineage validation.
4. Freeze target definitions, cutoff definitions, oracle reference denominator mappings, feature source inventory, and leakage constraints.
5. Emit target contract docs, feature contract docs, audit tables, and a preflight report.

18A must not:

1. Train, refit, score, or calibrate any model.
2. Select features using target correlation or OOS performance.
3. Use robustness or validation outcomes to change thresholds, feature families, target definitions, or gates.
4. Compute payoff-state separability, rank IC, model AUC, policy utility, or oracle gap reduction.
5. Define an entry, exit, holding, sizing, or portfolio policy.
6. Treat O4/O5 oracle information as deployable signal.
7. Rewrite upstream EP16 or EP17 publishable artifacts.

## 5. Required Input Artifacts

All inputs must be recorded in `input_artifact_audit.csv` and `input_artifact_manifest_18a.json` with:

```text
artifact_key
artifact_role
required_flag
resolver_alias
resolved_path
relative_path
source_experiment_id
source_phase_id
row_count
sha256
schema_status
read_status
absolute_path_mismatch_ignored
blocking_reason
```

Missing or schema-failing required inputs fail closed.

### 5.1 EP18 local planning inputs

Required:

```text
experiments/pending/18_payoff_state_representation_research/research_plan.md
experiments/pending/18_payoff_state_representation_research/requirement_18_payoff_state_representation_research.md
experiments/pending/18_payoff_state_representation_research/requirement_18a_payoff_state_contract_preflight.md
```

### 5.2 EP17D decision inputs

Required:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_diagnosis_decision.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_diagnosis_decision_tree.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_value_source_attribution.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_upside_preservation_diagnosis.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_path_risk_threshold_diagnosis.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/oracle_learned_model_gap_bridge.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17D_oracle_diagnosis_report/search_accounting_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17D_oracle_diagnosis_report_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/oracle_diagnosis_engine_manifest.json
```

### 5.3 EP17B oracle semantics and target source inputs

Required:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_ladder_summary.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_high_upside_threshold_freeze.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o5_action_selection_proof.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o2_drawdown_threshold_replay.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_neutral_stress.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17B_oracle_ladder_replay_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/oracle_ladder_replay_engine_manifest.json
```

### 5.4 EP16 denominator / target / feature reference inputs

Required:

```text
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_base_rate_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16B_sequential_continuation_label_design_diagnostic/continuation_label_panel_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_contract.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_lineage_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16C_sequential_continuation_separability_diagnostic/t0_feature_leakage_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/utility_by_split_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16E_sequential_continuation_utility_diagnostic/six_cell_utility_reconciliation.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_target_lineage_audit.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/survival_vs_payoff_rank_ic_readout.csv
experiments/pending/16_winner_episode_sequential_sampling_geometry_preflight_v0/outputs/publishable/tables/16X_payoff_aligned_continuation_label_power_precheck/payoff_decile_monotonicity_readout.csv
```

Full row-level target construction must use a complete row-level source. `utility_panel_sample.csv.gz` is optional appendix / schema-sanity evidence only and must not satisfy `target_lineage_gate`, `denominator_reconciliation_gate`, or `o5_incremental_definition_replay_gate`.

18A must register exactly one primary full row-level target source in `input_artifact_audit.csv`:

```text
artifact_role = full_row_level_target_source
source_kind in {publishable_full_panel, validated_local_cache}
row_key_coverage = labelable_full
expected_total_labelable_step_n = 23405
expected_total_binary_step_n = 17339
expected_total_neutral_step_n = 6066
content_hash_validated = true
schema_validated = true
row_key_reconciliation_gate = pass
```

The `expected_total_*` counts are three-split totals, not a single split:

```text
expected_total_labelable_step_n = train 20245 + robustness 2496 + validation 664 = 23405
expected_total_binary_step_n = train 14962 + robustness 1872 + validation 505 = 17339
expected_total_neutral_step_n = train 5283 + robustness 624 + validation 159 = 6066
```

If a full row-level target panel is unavailable from publishable artifacts, 18A may use validated local caches from 16C/16E/17B for row-level target construction. Such use must be explicitly marked:

```text
local_cache_used = true
cache_hash_validated = true
cache_schema_validated = true
cache_key_reconciliation_gate = pass
```

For validated local caches:

```text
cache_hash_validated = true means the local cache file sha256 is computed and recorded.
If an upstream manifest hash exists for that exact cache role, it must match.
If no upstream manifest hash exists for that exact cache role, cache_hash_manifest_status = not_available_nonblocking and row count, schema, and row-key reconciliation against publishable artifacts must pass.
```

If neither publishable nor validated local row-level sources can support target construction:

```text
decision_state = 18A_target_lineage_blocked
next_allowed_requirement = none
```

## 6. Fixed Constants And Expected Values

18A must freeze the following constants before any target table is produced:

```text
primary_threshold_id = up50pct
primary_horizon_sessions = 20
primary_sampling_unit = full_horizon_nonoverlap_step
primary_denominator = labelable_full
primary_cost_bps = 50
primary_q_defend = 0.0
primary_split_for_later_gates = robustness
validation_role = stress_readout_only
```

Expected denominator reconciliation:

```text
split_bucket | labelable_step_n | binary_step_n | neutral_step_n
train        | 20,245           | 14,962        | 5,283
robustness   | 2,496            | 1,872         | 624
validation   | 664              | 505           | 159
```

Required oracle reference values:

```text
O5 perfect utility robustness mean incremental = 0.0294674283651707
O5 denominator = labelable_full
O5 robustness observed_step_n = 2,496

O2 drawdown primary robustness mean incremental = 0.0185108290944368
O2 denominator = labelable_full
O2 robustness observed_step_n = 2,496
O2 primary signed drawdown threshold = -0.10

O4 label-positive robustness mean incremental = 0.0246811054592491
O4 denominator = binary_primary
O4 robustness observed_step_n = 1,872
```

Required train-frozen high-upside cutoffs:

```text
cutoff_source_artifact = oracle_high_upside_threshold_freeze.csv
cutoff_source_denominator = train labelable_full
cutoff_source_train_row_count = 20,245

top30_cutoff = 0.0596330275229357
top20_cutoff = 0.1012285086722715
top10_cutoff = 0.1721071844362347
split_local_recompute_used = false
```

Required 16X baseline constants for future 18C only:

```text
sixteen_x_robustness_payoff_rank_ic_baseline = 0.051877
sixteen_x_payoff_minus_survival_margin = -0.000723
sixteen_x_robustness_payoff_decile_monotonicity_baseline = 0.163636
```

18A must record these baselines but must not evaluate whether EP18 features beat them.

## 7. Target Definitions

18A must write `payoff_state_target_contract.md` with exact target definitions.

### 7.1 Continuous payoff target

```text
y_payoff_h20 = realized h20 close-to-close return from step_start to step_end
```

Preferred lineage:

```text
Use existing EP16/16C/16E payoff or return column if hash/key reconciled.
Use qfq close replay only as lineage audit or fallback if existing column cannot support contract.
```

Required sign convention:

```text
positive y_payoff_h20 = positive continuation payoff
negative y_payoff_h20 = loss over h20
```

### 7.2 Action-value targets

Frozen action semantics:

```text
q_continue = 1.0
q_defend = 0.0
cost_bps = 50
cash_return = 0.0
blind_continue_base = continue_value
```

Target definitions:

```text
continue_value = continue_net_return_h20
defend_value   = defend_net_return_h20 under q_defend=0.0 and cost_bps=50

continue_advantage = continue_value - defend_value
defend_advantage   = defend_value - continue_value
o5_incremental     = max(0, defend_advantage)
```

Required identity:

```text
o5_policy_value = max(continue_value, defend_value)
o5_incremental = o5_policy_value - blind_continue_base
               = max(0, defend_value - continue_value)
               = max(0, defend_advantage)
```

18A must replay this identity against EP17B `oracle_o5_action_selection_proof.csv` or a validated O5 row-level source. Mismatch tolerance:

```text
max_abs_diff <= 1e-9 for aggregate replay
formula_mismatch_n = 0 for row-level proof where row-level proof is available
```

Aggregate O5 incremental must be computed over the full `labelable_full` denominator:

```text
aggregate_o5_incremental = mean(labelable_full rows, max(0, defend_value - continue_value))
non_defended_rows_contribute = 0
defended_only_mean_is_not_allowed = true
```

If the O5 identity cannot be proven:

```text
decision_state = 18A_o5_incremental_contract_blocked
next_allowed_requirement = none
```

### 7.3 Ordinal payoff-state target

Ordinal states use train-frozen absolute cutoffs:

```text
state_0 = below_top30_payoff        if y_payoff_h20 < top30_cutoff
state_1 = top30_to_top20_payoff     if top30_cutoff <= y_payoff_h20 < top20_cutoff
state_2 = top20_to_top10_payoff     if top20_cutoff <= y_payoff_h20 < top10_cutoff
state_3 = top10_extreme_payoff      if y_payoff_h20 >= top10_cutoff
```

Interpretation:

```text
state_1 and state_2 are primary broad payoff-positive regions.
state_3 is over-narrow extreme-winner stress, not a primary target.
```

The cutoff source denominator must be train `labelable_full`. If cutoffs are computed from binary_primary or any split-local denominator, 18A must fail closed.

The payoff column used for ordinal cutoff assignment must be the same target lineage as §7.1:

```text
ordinal_cutoff_payoff_column == y_payoff_h20
ordinal_cutoff_payoff_lineage_hash == target_definition_registry.y_payoff_h20.lineage_hash
payoff_cutoff_freeze.y_payoff_lineage_hash == target_definition_registry.y_payoff_h20.lineage_hash
```

### 7.4 Path-risk auxiliary target

Path-risk targets are auxiliary:

```text
y_signed_max_drawdown_h20
risk_state_dd08 = signed_max_drawdown_h20 <= -0.08
risk_state_dd10 = signed_max_drawdown_h20 <= -0.10
risk_state_dd12 = signed_max_drawdown_h20 <= -0.12
```

Sign convention:

```text
signed_max_drawdown_h20 <= 0
O2 threshold comparison uses signed drawdown, never abs drawdown.
```

If the path-risk sign convention cannot be verified:

```text
decision_state = 18A_path_risk_sign_convention_blocked
next_allowed_requirement = none
```

### 7.5 Binary sanity targets

Allowed only as sanity:

```text
16B label_class positive / negative / neutral
binary_positive_negative
top30_yes_no
top20_yes_no
drawdown_yes_no
```

Binary targets must be marked:

```text
binary_metric_used_as_primary_gate = false
```

## 8. Oracle Reference Denominator Contract

18A must produce `oracle_reference_denominator_map.csv` with at least:

```text
oracle_reference_id
source_artifact
source_denominator_type
split_bucket
observed_step_n
mean_incremental_return
allowed_bridge_denominator
direct_comparison_allowed
notes
```

Required rows:

```text
O5_perfect_utility_primary:
  source_denominator_type = labelable_full
  observed_step_n robustness = 2496
  allowed_bridge_denominator = labelable_full
  direct_comparison_allowed = true for learned labelable_full bridge

O2_dd_10pct_primary:
  source_denominator_type = labelable_full
  observed_step_n robustness = 2496
  allowed_bridge_denominator = labelable_full
  direct_comparison_allowed = true for learned labelable_full bridge

O4_label_positive_primary:
  source_denominator_type = binary_primary
  observed_step_n robustness = 1872
  allowed_bridge_denominator = binary_primary
  direct_comparison_allowed = false for learned labelable_full bridge

17D_mixed_o5_vs_best_label_path_gap:
  source_denominator_type = mixed_diagnostic_only
  source_value = 0.004786322905921601
  source_formula = O5_labelable_full_mean - O4_binary_primary_mean
  allowed_bridge_denominator = none
  direct_comparison_allowed = false
  notes = diagnostic-only upstream readout; deprecated for learned-score oracle-gap bridge
```

18A must explicitly forbid this operation:

```text
learned_labelable_full_mean - O4_binary_primary_mean
```

17D's `o5_vs_best_label_path_gap = 0.004786322905921601` is a mixed-denominator diagnostic readout, because it subtracts `O4 binary_primary` from `O5 labelable_full`. EP18D may cite this number only as upstream orientation. EP18D must recompute learned-score oracle gaps on aligned denominators and must not use the 17D mixed gap as the learned-score headroom target.

Any later O4/O5 gap statement must identify denominator alignment. If denominator mapping cannot be proven:

```text
decision_state = 18A_oracle_reference_denominator_blocked
next_allowed_requirement = none
```

## 9. Feature Source Contract

18A must write `payoff_state_feature_contract.md` and `feature_source_inventory.csv`.

Required columns for `feature_source_inventory.csv`:

```text
feature_family_id
feature_family_name
candidate_feature_source
pit_available_status
t0_available_status
source_artifact
requires_new_data
primary_allowed
appendix_only
forbidden_reason
notes
```

Candidate families from the research plan:

```text
F1 continuation strength / repair persistence
F2 participation / sponsorship
F3 cross-sectional leadership
F4 path-risk decoupling
F5 regime / board / market context
F6 delayed observed-state appendix
F7 external feature families
```

Rules:

```text
F1-F5 may be primary only if PIT-valid and t0-available.
F6 delayed t0+3 features are appendix-only and must not enter any primary 18C model.
F7 external features require existing PIT-valid source artifacts; otherwise they are unavailable, not assumed.
```

The feature contract must include a forbidden-column list:

```text
future payoff
step_end price
step_end return
future drawdown
oracle action
O1/O2/O4/O5 future labels
label_class if used as model feature
split id
instrument id as raw model feature
episode cluster id as raw model feature
validation / robustness outcome-derived columns
```

18A does not materialize the full feature matrix. It only freezes the source inventory and leakage contract. Full matrix materialization belongs to EP18B.

## 10. Required Outputs

18A must write publishable outputs under:

```text
experiments/pending/18_payoff_state_representation_research/outputs/publishable/
```

Required root-level contract docs:

```text
payoff_state_target_contract.md
payoff_state_feature_contract.md
```

Required report:

```text
outputs/publishable/reports/payoff_state_contract_preflight_report.md
```

Required tables:

```text
outputs/publishable/tables/18A_payoff_state_contract_preflight/input_artifact_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/upstream_authorization_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/target_denominator_reconciliation.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/oracle_reference_denominator_map.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/o5_incremental_definition_replay.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_cutoff_freeze.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/target_definition_registry.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/target_distribution_readout.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/path_risk_target_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/neutral_preservation_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/feature_source_inventory.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/leakage_forbidden_column_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/search_accounting_audit.csv
outputs/publishable/tables/18A_payoff_state_contract_preflight/payoff_state_contract_decision.csv
```

Minimum table schemas:

```text
target_denominator_reconciliation.csv:
  split_bucket, labelable_step_n, binary_step_n, neutral_step_n,
  expected_labelable_step_n, expected_binary_step_n, expected_neutral_step_n,
  denominator_reconciliation_gate, blocking_reason

o5_incremental_definition_replay.csv:
  split_bucket, cost_bps, q_defend, observed_step_n, defended_step_n,
  aggregate_o5_incremental_replay, source_mean_incremental_return,
  max_abs_diff, formula_mismatch_n, o5_incremental_definition_replay_gate,
  blocking_reason

payoff_cutoff_freeze.csv:
  threshold_id, oracle_variant_id, train_quantile, train_absolute_payoff_cutoff,
  train_row_count, robustness_applied_cutoff, validation_applied_cutoff,
  split_local_recompute_used, y_payoff_lineage_hash, train_frozen_cutoff_gate,
  blocking_reason

target_definition_registry.csv:
  target_id, target_family, definition, source_artifact, source_column,
  denominator_type, sign_convention, lineage_hash, primary_allowed,
  binary_metric_used_as_primary_gate, target_lineage_gate, blocking_reason

target_distribution_readout.csv:
  split_bucket, target_id, state_id, row_count, row_share,
  mean_y_payoff_h20, median_y_payoff_h20, min_y_payoff_h20, max_y_payoff_h20

path_risk_target_audit.csv:
  split_bucket, target_id, signed_drawdown_threshold, observed_step_n,
  predicate_true_n, predicate_true_rate, signed_max_drawdown_min,
  signed_max_drawdown_max, positive_abs_drawdown_used_for_threshold,
  path_risk_sign_convention_gate, blocking_reason

neutral_preservation_audit.csv:
  split_bucket, labelable_step_n, neutral_step_n,
  neutral_preserved_in_labelable_full, neutral_reclassified_as_positive_or_negative,
  neutral_preservation_gate, blocking_reason

leakage_forbidden_column_audit.csv:
  forbidden_column_family, forbidden_column_pattern, found_in_primary_feature_source,
  primary_feature_allowed, leakage_forbidden_column_gate, blocking_reason

payoff_state_contract_decision.csv:
  decision_state, next_allowed_requirement, all_hard_gates_pass,
  upstream_authorization_gate, input_artifact_gate, denominator_reconciliation_gate,
  target_lineage_gate, oracle_reference_denominator_gate,
  o5_incremental_definition_replay_gate, train_frozen_cutoff_gate,
  neutral_preservation_gate, path_risk_sign_convention_gate,
  feature_source_pit_gate, leakage_forbidden_column_gate,
  search_accounting_gate, entry_policy_authorized, exit_policy_authorized,
  holding_policy_authorized, portfolio_backtest_authorized,
  model_deployment_authorized, production_signal_authorized,
  live_trading_authorized, blocking_reason
```

Required manifests:

```text
outputs/manifests/18A_payoff_state_contract_preflight_manifest.json
outputs/manifests/input_artifact_manifest_18a.json
outputs/manifests/payoff_state_target_contract_manifest.json
```

## 11. Required Gates

18A pass requires all hard gates to pass:

```text
upstream_authorization_gate = pass
input_artifact_gate = pass
denominator_reconciliation_gate = pass
target_lineage_gate = pass
oracle_reference_denominator_gate = pass
o5_incremental_definition_replay_gate = pass
train_frozen_cutoff_gate = pass
neutral_preservation_gate = pass
path_risk_sign_convention_gate = pass
feature_source_pit_gate = pass
leakage_forbidden_column_gate = pass
search_accounting_gate = pass
```

If any gate fails, `next_allowed_requirement = none`.

### 11.1 Denominator reconciliation gate

Expected counts:

```text
train labelable/binary/neutral = 20245 / 14962 / 5283
robustness labelable/binary/neutral = 2496 / 1872 / 624
validation labelable/binary/neutral = 664 / 505 / 159
```

Neutral rows must be preserved:

```text
neutral_preserved_in_labelable_full = true
neutral_reclassified_as_positive_or_negative = false
```

### 11.2 Cutoff freeze gate

Required:

```text
train_row_count = 20245
split_local_recompute_used = false
robustness_applied_cutoff == train_absolute_payoff_cutoff
validation_applied_cutoff == train_absolute_payoff_cutoff
```

Cutoff values must match tolerance:

```text
abs(top30_cutoff - 0.0596330275229357) <= 1e-12
abs(top20_cutoff - 0.1012285086722715) <= 1e-12
abs(top10_cutoff - 0.1721071844362347) <= 1e-12
```

### 11.3 O5 identity gate

Required:

```text
o5_incremental = max(0, defend_value - continue_value)
```

Aggregate replay tolerance:

```text
max_abs_diff <= 1e-9
```

If row-level O5 proof is available:

```text
formula_mismatch_n = 0
```

Row-level O5 proof for `formula_mismatch_n = 0` must come from EP17B `oracle_o5_action_selection_proof.csv` or a full source hash-aligned to it. A local sample or schema-only cache may support aggregate sanity checks, but it must not satisfy row-level O5 proof on its own.

### 11.4 Feature source gate

Primary-allowed feature families must be PIT-valid and t0-available. Delayed features and unavailable external features must be marked appendix-only or unavailable.

### 11.5 Search accounting gate

Required flags:

```text
no_model_training = true
no_model_refit = true
no_feature_selection = true
no_target_selection_from_robustness = true
no_target_selection_from_validation = true
no_separability_metric_computed = true
no_binary_metric_used_as_primary_gate = true
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
delayed_features_used_in_primary_model = false
```

## 12. Decision Labels

18A must emit exactly one decision row in `payoff_state_contract_decision.csv`.

Allowed decisions:

```text
18A_payoff_state_contract_ready
18_upstream_oracle_contract_blocked
18A_target_lineage_blocked
18A_feature_source_pit_blocked
18A_denominator_reconciliation_blocked
18A_oracle_reference_denominator_blocked
18A_o5_incremental_contract_blocked
18A_cutoff_freeze_blocked
18A_neutral_preservation_blocked
18A_path_risk_sign_convention_blocked
18A_leakage_contract_blocked
18A_search_accounting_blocked
18A_target_contract_blocked
```

Positive decision:

```text
decision_state = 18A_payoff_state_contract_ready
next_allowed_requirement = requirement_18b_payoff_state_feature_matrix_audit.md
```

All blocked decisions:

```text
next_allowed_requirement = none
```

No 18A decision may authorize entry, exit, holding, portfolio backtest, model deployment, production signal, or live trading.

## 13. Report Requirements

`payoff_state_contract_preflight_report.md` must include:

1. One-line decision and next allowed requirement.
2. Upstream EP17D authorization replay.
3. Denominator reconciliation table.
4. Explicit O4/O5/O2 reference denominator map.
5. O5 incremental identity and replay result.
6. Payoff cutoff freeze table with train labelable_full source denominator.
7. Target definition registry.
8. Neutral preservation audit.
9. Path-risk signed drawdown convention.
10. Feature source inventory summary.
11. Leakage forbidden-column audit.
12. Search accounting and authorization boundary.

The report must state clearly:

```text
18A freezes targets and contracts only.
18A does not prove payoff-state separability.
18A does not authorize policy, backtest, deployment, or trading.
```

## 14. Handoff To 18B

18B may begin only if:

```text
decision_state = 18A_payoff_state_contract_ready
next_allowed_requirement = requirement_18b_payoff_state_feature_matrix_audit.md
all hard gates = pass
```

18B must consume the contracts emitted by 18A:

```text
payoff_state_target_contract.md
payoff_state_feature_contract.md
target_denominator_reconciliation.csv
oracle_reference_denominator_map.csv
payoff_cutoff_freeze.csv
target_definition_registry.csv
feature_source_inventory.csv
leakage_forbidden_column_audit.csv
18A manifest files
```

18B is still not allowed to train models or evaluate payoff-state separability unless its own requirement explicitly authorizes that work. Full separability belongs to EP18C.
