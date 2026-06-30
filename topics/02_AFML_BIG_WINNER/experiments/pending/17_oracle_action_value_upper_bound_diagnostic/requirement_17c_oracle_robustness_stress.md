# 需求：17C Oracle Robustness Stress

## 0. Non-negotiable Scope

17C 是 EP17 的第三个可执行 phase。它只能在 17B 已经证明 oracle ladder 存在可测 action-value headroom 后运行。

17C 只回答一个问题：

```text
17B 的正向 oracle action value 是否能经受 top-k concentration、cluster bootstrap、
matched-base、delayed decision、cost/action intensity、以及 capacity 可评估性压力测试？
```

17C 不得做：

```text
new model training
model refit
feature selection
payoff label redesign
survival threshold tuning
oracle threshold tuning
validation-based selection
robustness-based selection
entry policy
exit policy
holding policy
position sizing
portfolio backtest
production signal
deployment authorization
live trading authorization
```

17C 可以使用未来信息 oracle，但只能作为 upper-bound robustness diagnostic。任何正结果最多授权 EP17D 诊断报告或后续研究方向判断；不得解释为可部署 edge。

17C 的正向裁决只能是：

```text
decision_state = EP17C_oracle_robustness_ready_for_diagnosis
next_allowed_requirement = requirement_17d_oracle_diagnosis_report.md
```

17C 的负向或阻断裁决为：

```text
oracle_no_action_value_in_current_space
oracle_execution_capacity_blocked
oracle_lineage_or_denominator_blocked
```

17C 不得输出 `oracle_payoff_state_research_allowed`、`oracle_value_exists_feature_gap`、`oracle_risk_signal_only_no_payoff_value` 或 `oracle_delayed_decision_supported` 作为最终裁决。这些属于 EP17D decision-tree 解释层。17C 可以输出同名 diagnostic flags，但 final `decision_state` 必须限制在本节列出的状态内。

## 1. Identity

```text
experiment_id = 17_oracle_action_value_upper_bound_diagnostic
phase_id = 17C
run_id = 17C_oracle_robustness_stress
requirement_file = requirement_17c_oracle_robustness_stress.md
config_file = configs/config_17c_oracle_robustness_stress.yaml
runner_file = src/run_17c_oracle_robustness_stress.py
test_file = tests/test_17c_oracle_robustness_stress.py
```

Must run from:

```bash
cd topics/02_AFML_BIG_WINNER
```

All paths must be repo-relative or resolver-alias based. Do not hard-code author-machine absolute paths. Artifact identity must use content hash, schema, lineage role, and row-key reconciliation as primary identity.

## 2. 17B Handoff Gate

17C must read 17B artifacts, but must not trust the 17B report prose alone.

Required 17B decision:

```text
decision_state = EP17B_oracle_ladder_ready_for_robustness
next_allowed_requirement = requirement_17c_oracle_robustness_stress.md
input_gate = pass
row_replay_gate = pass
denominator_gate = pass
oracle_ladder_gate = pass
six_cell_gate = pass
action_intensity_gate = pass
neutral_stress_gate = pass
high_upside_threshold_gate = pass
search_accounting_gate = pass
primary_ladder_cost_bps = 50
primary_ladder_q_defend = 0.00
primary_positive_oracle_id must be non-empty
```

17C must not require `primary_ladder_materiality_floor` as a 17B handoff field. If a newer 17B decision table emits it, 17C may record it in contract validation, but 17C's binding materiality floor is its own `robustness_mean_incremental_floor` in Section 5.

Allowed non-blocking 17B status:

```text
o3_status in {skipped_nonblocking, appendix_only, materialized}
o6_status_inherited = appendix_only_nonblocking
```

17C must independently validate these 17B machine-readable outputs:

```text
17b_input_gate_audit.csv
17a_contract_validation_audit.csv
oracle_row_replay_audit.csv
oracle_ladder_summary.csv
oracle_six_cell_decomposition.csv
oracle_action_intensity_frontier.csv
oracle_neutral_stress.csv
oracle_o2_drawdown_threshold_replay.csv
oracle_o5_action_selection_proof.csv
oracle_high_upside_threshold_freeze.csv
oracle_ladder_decision.csv
search_accounting_audit.csv
17B_oracle_ladder_replay_manifest.json
oracle_ladder_replay_engine_manifest.json
input_artifact_manifest_17b.json
```

Required 17B row-level source:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/local_cache/17B_oracle_ladder_replay/oracle_ladder_panel.parquet
```

The row-level 17B panel is required for top-k removal, cluster bootstrap, delayed decision replay, and matched-base stress. If this local cache is missing, 17C may rebuild an equivalent 17C-local panel only if it can prove byte-level or row-key/value equality to 17B publishable summaries without mutating any 17B artifact. Otherwise 17C must fail closed:

```text
decision_state = oracle_lineage_or_denominator_blocked
blocking_reason = missing_or_unverifiable_17b_row_level_panel
```

The 17B publishable report is not a machine gate for 17C. If report prose is incomplete but the machine-readable contract artifacts pass, 17C may run. If any machine-readable artifact is missing, stale, schema-incompatible, or internally inconsistent, 17C must return `oracle_lineage_or_denominator_blocked`.

17C input canonicalization must be explicit before any filter, join, or groupby:

```text
17B row-level input field       | 17C canonical/output field | rule
cluster_split_bucket            | split_bucket               | required; copy into canonical split_bucket
split_bucket                    | split_bucket               | allowed only if equal to cluster_split_bucket when both exist
signed_max_drawdown_h20         | signed_max_drawdown_h20     | required signed-negative O2/path field
drawdown_abs_for_reporting      | drawdown_abs_for_reporting  | required positive abs reporting field
```

17C must not assume the 17B row-level parquet contains `split_bucket` or `drawdown_avoided_abs`. If an output table uses `split_bucket`, it is the canonicalized field derived from `cluster_split_bucket`. If a capacity or reporting sort needs drawdown severity, it must use `drawdown_abs_for_reporting` unless a later audited artifact explicitly defines another field.

The input gate audit must include blocking checks:

```text
cluster_split_bucket_present
canonical_split_bucket_created
split_bucket_conflict_count = 0 when both fields exist
drawdown_abs_for_reporting_present
drawdown_avoided_abs_not_required
```

## 3. Required Input Artifacts

Required 17B publishable tables:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/17b_input_gate_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/17a_contract_validation_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_row_replay_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_ladder_summary.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_six_cell_decomposition.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_action_intensity_frontier.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_neutral_stress.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o2_drawdown_threshold_replay.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_o5_action_selection_proof.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_high_upside_threshold_freeze.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/oracle_ladder_decision.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17B_oracle_ladder_replay/search_accounting_audit.csv
```

Required 17B manifests:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/17B_oracle_ladder_replay_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/oracle_ladder_replay_engine_manifest.json
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/input_artifact_manifest_17b.json
```

Required local cache:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/local_cache/17B_oracle_ladder_replay/oracle_ladder_panel.parquet
```

Required 17A contract files and manifests for delayed/capacity status inheritance:

```text
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/oracle_action_contract.md
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/oracle_denominator_contract.md
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/delayed_materialization_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17A_oracle_replay_contract_preflight/capacity_reconstruction_audit.csv
experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/manifests/oracle_replay_engine_manifest.json
```

Required qfq source for delayed replay:

```text
data/raw/akshare/day/qfq
```

If qfq replay cannot materialize every row required by O7 delayed replay at `t0 + k` for `k in {3, 5, 10}`, 17C must fail closed for delayed materialization. If delayed materialization failure is inherited from 17A, 17C must return `oracle_lineage_or_denominator_blocked`; if 17A delayed gate passed but 17C cannot reproduce it, 17C must also block.

## 4. Stress Universe

17C primary stress universe:

```text
split_bucket = robustness
cost_bps = 50
q_defend = 0.00
primary_variant = true
primary_candidate_variants = {
    O1_negative_primary,
    O2_dd_10pct_primary,
    O4_label_positive_primary,
    O5_perfect_utility_primary
}
```

17C required readout universe:

```text
all train / robustness / validation splits
cost_bps in {0, 25, 50, 100}
q_defend in {0.00, 0.25, 0.50}
O2 drawdown stress variants = {-0.08, -0.10, -0.12, -0.15, -0.20}
O4 high-upside stress variants = train-frozen top30/top20/top10
O5 action variants with independent action recomputation
O7 delayed utility curve for k in {3, 5, 10}
O6 capacity constraint only if capacity reconstruction gate is pass
```

Only the primary stress universe may drive 17C final decision. Readout universe rows must not rescue a failed primary gate.

O4 high-upside stress variants are readout variants, but they still require full `oracle_variant_id` coverage in `oracle_topk_sensitivity.csv`, `oracle_bootstrap_ci.csv`, and `oracle_robustness_primary_summary.csv`. Implementations must not compute top-k/bootstrap only for primary variants and then leave `O4_high_upside_top30_stress`, `O4_high_upside_top20_stress`, or `O4_high_upside_top10_stress` without readout rows. These rows are non-primary for 17C readiness, but they are required by 17D payoff/upside preservation diagnosis.

Primary row key inherited from 17B:

```text
step_id
label_id
threshold_id
instrument
episode_cluster_id
horizon_sessions
step_index
step_start_date
step_end_date
```

17C must preserve 17B denominator row counts:

```text
split_bucket | labelable_step_n | binary_step_n | neutral_step_n | positive_n | negative_n
train        | 20245            | 14962         | 5283           | 10078      | 4884
robustness   | 2496             | 1872          | 624            | 1346       | 526
validation   | 664              | 505           | 159            | 325        | 180
```

Fail-closed rules:

```text
O0/O2/O5/O7 labelable rows must equal labelable_step_n for every split.
O1/O4 primary rows must equal binary_step_n for every split.
O1/O4 neutral stress rows must reconcile neutral_step_n for every split.
duplicate primary row key count must be 0 within each oracle/variant/cost/q/split group.
missing primary row key field count must be 0.
missing qfq close or nonfinite qfq close count must be 0.
17C must not silently drop rows from a primary denominator.
```

## 5. Metrics and Support Gates

17C must use the 17B metric definitions:

```text
incremental_net_return = oracle_policy_net_return - blind_continue_net_return
trim_fraction_each_tail = 0.01
winsor_fraction_each_tail = 0.01
primary_cost_bps = 50
primary_q_defend = 0.00
```

17C materiality floors are frozen before run:

```text
robustness_mean_incremental_floor = 0.0025
robustness_trimmed_mean_floor = 0.0000
cluster_bootstrap_ci_low_floor = 0.0000
topk_removed_mean_floor = 0.0000
matched_base_min_pass_share = 0.75
matched_min_bucket_step_n = 20
delayed_mean_incremental_floor = 0.0025
capacity_mean_incremental_floor = 0.0025
bootstrap_iterations = 1000
bootstrap_ci = 95%
random_seed = 20260630
bootstrap_min_cluster_n_primary = 20
```

Primary support gates must be evaluated in this order:

```text
1. robustness_trimmed_mean_incremental > robustness_trimmed_mean_floor
2. robustness_cluster_bootstrap_ci_low > cluster_bootstrap_ci_low_floor
3. robustness_topk_removed_mean > topk_removed_mean_floor
4. robustness_matched_base_gate = pass
```

Materiality confirmation:

```text
5. robustness_raw_mean_incremental >= robustness_mean_incremental_floor
```

Raw mean alone cannot trigger a positive 17C decision. If raw mean passes but trimmed mean, bootstrap CI, top-k, or matched-base fails, the oracle must be marked:

```text
tail_or_match_fragile_upper_bound = true
```

If trimmed/bootstrap/top-k/matched gates pass but raw mean fails the 25bps materiality floor, the oracle may be marked:

```text
weak_positive_upper_bound = true
```

but it must not trigger `EP17C_oracle_robustness_ready_for_diagnosis`.

## 6. Top-k Removal Sensitivity

17C must compute top-k concentration on the primary stress universe and as readout for all required variants.

For O4 high-upside readout variants, top-k rows must be emitted for the same frozen removal families as primary variants. Their `topk_gate` is readout-level evidence for 17D and must not be silently replaced by the parent `O4_label_positive_primary` top-k result.

For each oracle/variant/cost/q/split group, compute contribution by:

```text
instrument_contribution = sum(incremental_net_return) grouped by instrument
episode_contribution = sum(incremental_net_return) grouped by episode_cluster_id
```

Required removals:

```text
remove top 1 positive instrument contribution
remove top 3 positive instrument contributions
remove top 5 positive instrument contributions
remove top 1% positive episode_cluster_id contributions, ceiling to at least 1 episode when positive episodes exist
```

Canonical `removal_family` values are frozen:

```text
remove_top_1_instrument
remove_top_3_instruments
remove_top_5_instruments
remove_top_1pct_episodes
```

For every removal:

```text
removed_group_n
removed_step_n
removed_sum_incremental_return
remaining_step_n
remaining_sum_incremental_return
remaining_mean_incremental_return = remaining_sum_incremental_return / original_observed_step_n
```

The denominator for `remaining_mean_incremental_return` must be the original observed step count, not the reduced row count. This makes top-k removal a contribution stress rather than a changed-denominator average.

Primary top-k gate:

```text
primary_topk_gate = pass
if every required removal for the primary robustness row has
    remaining_mean_incremental_return > topk_removed_mean_floor
else fail
```

If any primary variant fails top-k but raw mean was positive, mark:

```text
tail_concentrated_upper_bound = true
```

## 7. Bootstrap Stress

Allowed bootstrap families:

```text
episode_cluster_id cluster bootstrap
instrument cluster bootstrap
calendar_month block bootstrap
calendar_quarter block bootstrap
```

Primary bootstrap family discipline:

```text
primary_required_bootstrap_families = {
    episode_cluster_id,
    instrument,
    calendar_month
}
readout_only_bootstrap_families = {
    calendar_quarter
}
bootstrap_min_cluster_n_primary = 20
```

`calendar_quarter` is a required readout but not a primary blocking bootstrap family, because the 17B robustness primary universe currently spans 10 calendar quarters. It must still be reported with `bootstrap_family_status = readout_only_insufficient_clusters` when `cluster_n < bootstrap_min_cluster_n_primary`; this status must not be converted into `primary_bootstrap_gate = fail`.

Forbidden bootstrap:

```text
row-level independent bootstrap
bootstrap after dropping failed rows
bootstrap with validation-selected parameters
bootstrap iteration count selected from result stability
```

Bootstrap procedure:

```text
For each oracle/variant/cost/q/split group:
    1. build clusters according to bootstrap_family
    2. sample clusters with replacement using frozen random_seed
    3. concatenate all rows from sampled clusters
    4. compute mean_incremental_return over sampled rows
    5. repeat bootstrap_iterations times
    6. report ci_low, ci_mid, ci_high using 2.5%, 50%, 97.5%
```

Primary bootstrap gate:

```text
primary_bootstrap_gate = pass
if all primary_required_bootstrap_families for the primary robustness row have
    ci_low > cluster_bootstrap_ci_low_floor
else fail
```

If a primary-required bootstrap family has fewer than `bootstrap_min_cluster_n_primary` clusters for a primary group, it must be marked:

```text
bootstrap_family_status = insufficient_clusters_blocking
primary_bootstrap_gate = fail
```

For readout-only bootstrap families and non-primary readout groups, insufficient clusters must be marked `readout_only_insufficient_clusters`, but must not block the primary decision or be hidden.

For O4 high-upside readout variants, bootstrap rows must be emitted for every allowed bootstrap family. Their `bootstrap_gate` is readout-level evidence for 17D and must not be inherited from `O4_label_positive_primary`.

## 8. Matched-base Stress

17C must not compare oracle value only against a global baseline. It must produce matched-base readouts showing whether positive utility is stable across coarse context buckets.

Required matched-base families:

```text
calendar_month
calendar_quarter
instrument_board_bucket
known_failed_context_bucket if available
market_regime_bucket if PIT audited
```

Required derivations:

```text
calendar_month = YYYY-MM from step_start_date
calendar_quarter = YYYYQn from step_start_date
instrument_board_bucket derived from instrument prefix:
    SH60 = sh_main
    SH68 = star
    SZ00 = sz_main
    SZ30 = chinext
    BJ or other = other_or_unknown
```

Known-failed-context and market-regime readouts are not allowed to be guessed. If the required PIT fields are not present in the 17B panel or in a configured audited source, 17C must emit:

```text
matched_family_status = not_evaluable_nonblocking
matched_gate_in_primary_decision = false
```

Regime readout may only be:

```text
matched_family_status = provisional
```

unless a PIT regime audit proves that the regime value was known as of `step_start_date`.

Matched-base metrics for every evaluable family/bucket:

```text
oracle_id
oracle_variant_id
split_bucket
cost_bps
q_defend
matched_family
matched_bucket
bucket_step_n
bucket_mean_incremental_return
bucket_trimmed_mean_incremental_return
bucket_sum_incremental_return
bucket_positive_sacrifice
bucket_negative_avoidance
bucket_neutral_contribution
bucket_gate
```

Bucket eligibility and aggregation are frozen:

```text
matched_bucket_evaluable = bucket_step_n >= matched_min_bucket_step_n
bucket_gate = pass if matched_bucket_evaluable and bucket_trimmed_mean_incremental_return > 0
bucket_gate = fail if matched_bucket_evaluable and bucket_trimmed_mean_incremental_return <= 0
bucket_gate = small_sample_readout_only if bucket_step_n < matched_min_bucket_step_n
family_pass_share = pass_bucket_n / evaluable_bucket_n
family_pass_share_weighting = equal_bucket_weight, not row_weighted
```

Hard-required matched families must satisfy:

```text
calendar_month: evaluable_bucket_n >= 6
calendar_quarter: evaluable_bucket_n >= 4
instrument_board_bucket: evaluable_bucket_n >= 2
```

`calendar_quarter` intentionally has different blocking roles in bootstrap and matched-base stress. In bootstrap it is a resampling cluster family and the 17B robustness primary universe has fewer than 20 quarter clusters, so it is readout-only. In matched-base stress it is a coarse context bucket family; it remains hard-required when at least 4 quarter buckets each satisfy `matched_min_bucket_step_n`.

Primary matched-base gate:

```text
primary_matched_base_gate = pass
if every hard-required matched family has enough evaluable buckets
and every hard-required matched family has
    family_pass_share >= matched_base_min_pass_share
else fail
```

Hard-required matched families for 17C primary gate:

```text
calendar_month
calendar_quarter
instrument_board_bucket
```

Known-failed-context and regime readouts do not block 17C if they are not evaluable, but their non-evaluability must be explicit in both table and report.

## 9. Delayed Oracle Curve

17C must materialize O7 delayed utility oracle under the 17A action contract:

```text
oracle_id = O7
oracle_name = Delayed Utility Oracle
delayed_action_semantics = within_original_h20_switch_v1
delayed_k_sessions = [3, 5, 10]
denominator = labelable_full
```

Delayed decision semantics:

```text
t0 -> t0+k: exposure = 1.0
t0+k -> h20 end: oracle chooses continue or defend
baseline = t0 blind continue through original h20 endpoint
```

Forbidden delayed semantics:

```text
restart_h20_at_t0_plus_k
partial tail fill
dropping rows missing t0+k price
using validation/robustness to choose k
```

Per-row delayed formula:

```text
prefix_return_t0_to_k = qfq_close[t0+k] / qfq_close[t0] - 1
remaining_return_k_to_end = qfq_close[h20_end] / qfq_close[t0+k] - 1
delayed_continue_net_return =
    prefix_return_t0_to_k
    + (1 + prefix_return_t0_to_k) * (q_continue * remaining_return_k_to_end)
    - holding_cost
delayed_defend_net_return =
    prefix_return_t0_to_k
    + (1 + prefix_return_t0_to_k) * (q_defend * remaining_return_k_to_end)
    - cost_bps / 10000

if delayed_defend_net_return > delayed_continue_net_return:
    delayed_action = defend_at_t0_plus_k
else:
    delayed_action = continue

delayed_policy_net_return = selected delayed action return
delayed_incremental_net_return = delayed_policy_net_return - forward_return_h20
```

This is a staged-decision diagnostic, not the same action-time upper bound as 17B O5 at `t0`. The delayed return includes the realized prefix exposure from `t0` to `t0+k`; therefore 17C must not require O7 to improve on O5 at `t0` before reporting a delayed diagnostic.

The cost convention is inherited from 17B: `cost_bps / 10000` is charged once only when the delayed defend action is selected, and is not scaled by `q_defend`.

Primary delayed readout:

```text
split_bucket = robustness
cost_bps = 50
q_defend = 0.00
k in {3, 5, 10}
```

Delayed comparison metrics:

```text
delayed_mean_gap_vs_o5_t0 =
    delayed_mean_incremental_return - O5_perfect_utility_primary_t0_mean_incremental_return
delayed_retention_ratio_vs_o5_t0 =
    delayed_mean_incremental_return / O5_perfect_utility_primary_t0_mean_incremental_return
```

`delayed_mean_gap_vs_o5_t0` is expected to be non-positive when waiting loses avoidable prefix damage. It is a diagnostic gap, not a support gate.

17C must not emit `oracle_delayed_decision_supported` as final decision. It must emit:

```text
delayed_decision_diagnostic_flag = true
```

only if:

```text
best delayed k has delayed_mean_incremental_return >= delayed_mean_incremental_floor
and delayed_trimmed_mean_incremental_return > 0
and delayed top-k gate passes
and delayed bootstrap gate passes
and delayed matched-base gate passes
```

This flag authorizes EP17D to discuss staged trial / later observed-state decision. It does not authorize a trading rule.

## 10. Capacity Constraint

17C must read 17A capacity status:

```text
capacity_reconstruction_gate
o6_status_for_17b
```

If:

```text
capacity_reconstruction_gate != pass
```

then 17C must emit:

```text
capacity_status = appendix_only_nonblocking
capacity_constraint_gate = not_evaluable_nonblocking
o6_primary_decision_allowed = false
```

and capacity must not block `EP17C_oracle_robustness_ready_for_diagnosis`.

If capacity reconstruction is pass, 17C must compute O6 capacity-constrained utility over O5 action candidates using config-frozen constraints:

```text
max_active_positions
max_gross_exposure
max_per_name_exposure
max_turnover_per_day
max_board_concentration
capacity_selection_sort_key
```

The constraints and selection sort key must be frozen in config before replay. They must not be selected from robustness or validation utility.

Allowed capacity sort keys:

```text
oracle_policy_net_return_desc
incremental_net_return_desc
drawdown_abs_for_reporting_desc
```

Primary capacity gate when capacity is evaluable:

```text
capacity_constraint_gate = pass
if O6 robustness mean_incremental_return >= capacity_mean_incremental_floor
and O6 top-k gate passes
and O6 bootstrap gate passes
else fail
```

If O5 is robustly positive but evaluable O6 fails, 17C must output:

```text
decision_state = oracle_execution_capacity_blocked
next_allowed_requirement = none
```

If capacity is not evaluable because 17A already downgraded it to appendix-only, 17C must not output `oracle_execution_capacity_blocked`.

## 11. Decision Logic

17C decision split discipline:

```text
primary_decision_split = robustness
train = lineage / calibration / explanatory readout only
validation = stress readout only; never rescues or blocks 17C
```

Lineage block:

```text
if any required 17B handoff / row-level / denominator / qfq / delayed-materialization / search gate fails:
    decision_state = oracle_lineage_or_denominator_blocked
    next_allowed_requirement = none
```

No action value:

```text
if O5_perfect_utility_primary fails any of:
    primary trimmed gate
    primary bootstrap gate
    primary top-k gate
    primary matched-base gate
    primary materiality confirmation
on robustness, 50bps, q_defend = 0.00:
    decision_state = oracle_no_action_value_in_current_space
    next_allowed_requirement = none
```

Capacity blocked:

```text
if O5_perfect_utility_primary passes all primary robustness gates
and capacity_reconstruction_gate = pass
and O6 capacity_constraint_gate = fail:
    decision_state = oracle_execution_capacity_blocked
    next_allowed_requirement = none
```

Ready for diagnosis:

```text
if O5_perfect_utility_primary passes all primary robustness gates
and capacity is either pass or appendix_only_nonblocking
and all required outputs/manifests/report are emitted:
    decision_state = EP17C_oracle_robustness_ready_for_diagnosis
    next_allowed_requirement = requirement_17d_oracle_diagnosis_report.md
```

Rationale:

```text
O5 alone proves action-space upper bound and is enough to justify EP17D diagnosis.
At least one robust O1/O2/O4 label/path oracle is still required before EP17D can discuss
payoff-state or feature-representation research as more than a perfect-hindsight-only result.
```

If O5 passes but all O1/O2/O4 fail robustness stress, 17C must still output `EP17C_oracle_robustness_ready_for_diagnosis`, but with:

```text
diagnostic_warning = perfect_utility_only_no_label_or_path_oracle_support
payoff_state_research_candidate = false
```

This allows EP17D to close or redirect the episode explicitly instead of hiding a perfect-hindsight-only result.

## 12. Required Outputs

Publishable tables under:

```text
outputs/publishable/tables/17C_oracle_robustness_stress/
```

Required tables:

```text
17c_input_gate_audit.csv
seventeen_b_contract_validation_audit.csv
oracle_robustness_primary_summary.csv
oracle_topk_sensitivity.csv
oracle_bootstrap_ci.csv
oracle_matched_base.csv
oracle_delay_curve.csv
oracle_capacity_constraint.csv
oracle_robustness_decision.csv
search_accounting_audit.csv
```

Required figures under:

```text
outputs/publishable/figures/17C_oracle_robustness_stress/
```

Required figures:

```text
oracle_topk_sensitivity.png
oracle_bootstrap_ci.png
oracle_matched_base_heatmap.png
delayed_oracle_curve.png
capacity_constrained_oracle_curve.png
```

Required report:

```text
outputs/publishable/reports/oracle_robustness_stress_report.md
```

Required manifests:

```text
outputs/manifests/17C_oracle_robustness_stress_manifest.json
outputs/manifests/oracle_robustness_engine_manifest.json
outputs/manifests/input_artifact_manifest_17c.json
```

Optional local cache:

```text
outputs/local_cache/17C_oracle_robustness_stress/delayed_oracle_panel.parquet
outputs/local_cache/17C_oracle_robustness_stress/capacity_oracle_panel.parquet
```

Local cache files must not be required for publication, but all publishable tables must contain enough aggregate audit information to reproduce the decision.

## 13. Required Table Schemas

### 13.1 `17c_input_gate_audit.csv`

Required columns:

```text
artifact_key
artifact_role
required_flag
resolved_path
relative_path
source_phase_id
row_count
sha256
schema_status
lineage_status
row_key_status
gate_status
blocking_reason
```

### 13.2 `seventeen_b_contract_validation_audit.csv`

Required columns:

```text
artifact_key
validation_check_id
observed_value
expected_value
validation_status
blocking_reason
```

This table must include checks for:

```text
17B decision row
17B manifest output hashes
17B row-level panel row counts
17B primary ladder summary reconciliation
17B O2 signed drawdown replay gates
17B O5 action selection proof gates
17B search accounting gates
17A delayed and capacity inherited status
```

### 13.3 `oracle_robustness_primary_summary.csv`

Required columns:

```text
oracle_id
oracle_variant_id
split_bucket
cost_bps
q_defend
primary_variant
observed_step_n
mean_incremental_return
trimmed_mean_incremental_return
winsorized_mean_incremental_return
median_incremental_return
sum_incremental_return
bootstrap_ci_low_min
topk_removed_mean_min
matched_base_pass_share_min
required_bootstrap_family_n
required_bootstrap_family_pass_n
required_matched_family_n
required_matched_family_pass_n
defended_step_n
continued_step_n
defended_rate
topk_gate
bootstrap_gate
matched_base_gate
materiality_gate
primary_support_gate
tail_concentrated_upper_bound
weak_positive_upper_bound
blocking_reason
```

### 13.4 `oracle_topk_sensitivity.csv`

Required columns:

```text
oracle_id
oracle_variant_id
split_bucket
cost_bps
q_defend
primary_variant
removal_family
removal_k
group_key_type
original_step_n
original_sum_incremental_return
original_mean_incremental_return
removed_group_n
removed_step_n
removed_sum_incremental_return
remaining_step_n
remaining_sum_incremental_return
remaining_mean_incremental_return
top_removed_group_keys
tail_concentrated_upper_bound
topk_gate
blocking_reason
```

### 13.5 `oracle_bootstrap_ci.csv`

Required columns:

```text
oracle_id
oracle_variant_id
split_bucket
cost_bps
q_defend
primary_variant
bootstrap_family
bootstrap_primary_role
cluster_key
cluster_n
bootstrap_iterations
random_seed
observed_mean_incremental_return
ci_low
ci_mid
ci_high
ci_alpha
bootstrap_family_status
bootstrap_gate
blocking_reason
```

### 13.6 `oracle_matched_base.csv`

Required columns:

```text
oracle_id
oracle_variant_id
split_bucket
cost_bps
q_defend
primary_variant
matched_family
matched_bucket
matched_family_status
matched_gate_in_primary_decision
matched_bucket_evaluable
matched_min_bucket_step_n
family_evaluable_bucket_n
family_pass_bucket_n
family_pass_share
family_pass_share_weighting
bucket_step_n
bucket_mean_incremental_return
bucket_trimmed_mean_incremental_return
bucket_sum_incremental_return
bucket_positive_sacrifice
bucket_negative_avoidance
bucket_neutral_contribution
bucket_gate
matched_base_gate
blocking_reason
```

### 13.7 `oracle_delay_curve.csv`

Required columns:

```text
oracle_id
oracle_variant_id
split_bucket
cost_bps
q_defend
delay_k_sessions
delayed_action_semantics
observed_step_n
missing_t0_plus_k_price_n
missing_original_h20_endpoint_n
restart_h20_at_t0_plus_k
partial_tail_fill_used
delayed_defended_step_n
delayed_continued_step_n
delayed_mean_incremental_return
delayed_trimmed_mean_incremental_return
delayed_sum_incremental_return
o5_t0_mean_incremental_return
delayed_mean_gap_vs_o5_t0
delayed_retention_ratio_vs_o5_t0
topk_gate
bootstrap_gate
matched_base_gate
delayed_curve_gate
delayed_decision_diagnostic_flag
blocking_reason
```

### 13.8 `oracle_capacity_constraint.csv`

Required columns:

```text
oracle_id
oracle_variant_id
split_bucket
cost_bps
q_defend
capacity_status
capacity_reconstruction_gate
o6_primary_decision_allowed
capacity_cap_id
max_active_positions
max_gross_exposure
max_per_name_exposure
max_turnover_per_day
max_board_concentration
capacity_selection_sort_key
observed_step_n
unconstrained_defended_step_n
capacity_defended_step_n
unconstrained_mean_incremental_return
capacity_mean_incremental_return
capacity_sum_incremental_return
capacity_cost_sum
topk_gate
bootstrap_gate
capacity_constraint_gate
blocking_reason
```

If capacity is appendix-only, this table must still exist and contain one row per split with:

```text
capacity_status = appendix_only_nonblocking
capacity_constraint_gate = not_evaluable_nonblocking
o6_primary_decision_allowed = false
```

### 13.9 `oracle_robustness_decision.csv`

Required columns:

```text
decision_state
next_allowed_requirement
input_gate
seventeen_b_contract_gate
row_level_panel_gate
topk_gate
bootstrap_gate
matched_base_gate
delayed_curve_gate
capacity_constraint_gate
search_accounting_gate
primary_decision_split
primary_cost_bps
primary_q_defend
primary_oracle_id
primary_oracle_variant_id
primary_mean_incremental_return
primary_trimmed_mean_incremental_return
primary_bootstrap_ci_low
primary_topk_removed_mean_min
primary_matched_base_pass_share
label_or_path_oracle_support_gate
diagnostic_warning
payoff_state_research_candidate
delayed_decision_diagnostic_flag
capacity_status
entry_policy_authorized
exit_policy_authorized
holding_policy_authorized
portfolio_backtest_authorized
model_deployment_authorized
production_signal_authorized
live_trading_authorized
blocking_reason
```

### 13.10 `search_accounting_audit.csv`

Required columns:

```text
search_family
phase_id
no_model_training
no_model_refit
no_survival_threshold_tuning
no_validation_selection
no_robustness_tuning
no_feature_selection
no_payoff_label_redesign
no_oracle_threshold_tuning
no_bootstrap_family_selection
no_matched_base_family_selection
no_capacity_constraint_selection_from_results
no_entry_policy_authorized
no_exit_policy_authorized
no_holding_policy_authorized
no_portfolio_backtest_authorized
no_model_deployment_authorized
no_production_signal_authorized
no_live_trading_authorized
search_accounting_gate
blocking_reason
```

## 14. Figure Requirements

`oracle_topk_sensitivity.png` must show:

```text
robustness split primary variants
x-axis = removal_family
y-axis = remaining_mean_incremental_return
horizontal line at 0
highlight O5 and O1/O2/O4 primary variants
```

`oracle_bootstrap_ci.png` must show:

```text
robustness split primary variants
bootstrap families as facets or grouped intervals
point = observed mean
interval = 95% CI
horizontal line at 0
```

`oracle_matched_base_heatmap.png` must show:

```text
evaluable matched families
matched buckets on y-axis
primary variants on x-axis
cell color = bucket_trimmed_mean_incremental_return
explicit marking for not_evaluable_nonblocking and provisional families
```

`delayed_oracle_curve.png` must show:

```text
delay_k_sessions = 3, 5, 10
train / robustness / validation panels
O7 delayed mean and trimmed mean
O5 t0 reference line
```

`capacity_constrained_oracle_curve.png` must show:

```text
if capacity evaluable:
    O5 unconstrained vs O6 capacity-constrained by split
else:
    explicit appendix_only_nonblocking panel
```

Figures must be generated from publishable tables, not from hidden intermediate arrays.

## 15. Report Requirements

The Chinese report must include:

1. Single-line decision, next allowed requirement, and blocking reason.
2. 17B handoff gate status and independent validation summary.
3. Row-level panel reconciliation and denominator counts.
4. Primary robustness summary for O1/O2/O4/O5 under 50bps, `q_defend = 0.00`.
5. Top-k removal sensitivity and whether each positive upper bound is tail-concentrated.
6. Bootstrap CI by episode_cluster_id, instrument, calendar month, and calendar quarter.
7. Matched-base readout by calendar and board bucket; known-failed-context/regime must be explicitly marked if not evaluable or provisional.
8. O2 drawdown threshold robustness, including whether the -8% to -20% gradient remains positive after top-k/bootstrap stress.
9. O4 high-upside stress, including why top10/top20/top30 are or are not robust after positive sacrifice.
10. O5 proof carried forward from 17B, plus 17C stress result showing whether O5 remains positive after top-k/bootstrap/matched-base.
11. O7 delayed oracle curve and whether delayed decision is only a diagnostic flag or a future staged-decision research candidate.
12. O6 capacity status: pass / fail / appendix_only_nonblocking, and whether capacity can or cannot block 17C.
13. Search accounting: no model/refit/threshold/bootstrap/matched-base/capacity selection from OOS result.
14. Explicit statement that 17C does not authorize entry, exit, holding, sizing, portfolio, deployment, production signal, or live trading.
15. Explicit statement that 17C positive results only authorize EP17D diagnosis, not payoff-state research directly.

## 16. Manifest Requirements

`17C_oracle_robustness_stress_manifest.json` must include:

```text
run_id
experiment_id
phase_id
created_at_utc
git_commit_if_available
config_file
config_sha256
requirement_file
requirement_sha256
runner_file
test_file
input_artifact_hashes
output_hashes
row_counts
primary_decision_split
primary_cost_bps
primary_q_defend
primary_candidate_variants
materiality_floors
bootstrap_iterations
bootstrap_ci
random_seed
topk_removal_grid
matched_base_families
delayed_k_sessions
delayed_action_semantics
capacity_status
capacity_constraints
decision_state
next_allowed_requirement
authorization_flags
```

`oracle_robustness_engine_manifest.json` must include enough formula detail to reproduce:

```text
top-k removal denominator rule
bootstrap cluster sampling rule
matched-base bucket derivation
O7 delayed formula
O7 delayed gap/retention diagnostic definitions
O6 capacity formula or appendix-only status
trim/winsor definitions
search-accounting constants
```

`input_artifact_manifest_17c.json` must list every input path with:

```text
artifact_key
artifact_role
required_flag
resolved_path
relative_path
source_phase_id
row_count
sha256
schema_status
read_status
blocking_reason
```

## 17. Validation Commands

Required commands:

```bash
cd topics/02_AFML_BIG_WINNER
python -m py_compile experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17c_oracle_robustness_stress.py
python experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17c_oracle_robustness_stress.py --mode check-inputs
python experiments/pending/17_oracle_action_value_upper_bound_diagnostic/src/run_17c_oracle_robustness_stress.py --mode full
python -m pytest experiments/pending/17_oracle_action_value_upper_bound_diagnostic/tests/test_17c_oracle_robustness_stress.py -q
git diff --check -- experiments/pending/17_oracle_action_value_upper_bound_diagnostic
```

Required post-run assertions:

```python
from pathlib import Path
import pandas as pd

base = Path("experiments/pending/17_oracle_action_value_upper_bound_diagnostic/outputs/publishable/tables/17C_oracle_robustness_stress")
decision = pd.read_csv(base / "oracle_robustness_decision.csv").iloc[0]
assert decision["decision_state"] in {
    "EP17C_oracle_robustness_ready_for_diagnosis",
    "oracle_no_action_value_in_current_space",
    "oracle_execution_capacity_blocked",
    "oracle_lineage_or_denominator_blocked",
}
assert decision["entry_policy_authorized"] == False
assert decision["exit_policy_authorized"] == False
assert decision["portfolio_backtest_authorized"] == False
assert decision["production_signal_authorized"] == False
assert decision["live_trading_authorized"] == False

topk = pd.read_csv(base / "oracle_topk_sensitivity.csv")
assert {"remove_top_1_instrument", "remove_top_3_instruments", "remove_top_5_instruments", "remove_top_1pct_episodes"}.issubset(set(topk["removal_family"]))

boot = pd.read_csv(base / "oracle_bootstrap_ci.csv")
assert not boot["bootstrap_family"].eq("row_independent").any()
assert not (
    boot["bootstrap_family"].eq("calendar_quarter")
    & boot["bootstrap_family_status"].eq("insufficient_clusters_blocking")
).any()

matched = pd.read_csv(base / "oracle_matched_base.csv")
assert {"calendar_month", "calendar_quarter", "instrument_board_bucket"}.issubset(set(matched["matched_family"]))
assert matched["family_pass_share_weighting"].dropna().eq("equal_bucket_weight").all()

delay = pd.read_csv(base / "oracle_delay_curve.csv")
assert set(delay["delay_k_sessions"].dropna().astype(int)).issubset({3, 5, 10})
assert not delay["restart_h20_at_t0_plus_k"].astype(bool).any()
assert not delay["partial_tail_fill_used"].astype(bool).any()
assert "delayed_mean_improvement_vs_o5_t0" not in delay.columns
assert {"delayed_mean_gap_vs_o5_t0", "delayed_retention_ratio_vs_o5_t0"}.issubset(delay.columns)
```

## 18. Required Tests

The implementation must include focused tests for:

```text
test_17b_ready_decision_required_for_17c
test_17c_rejects_missing_17b_row_level_panel
test_17c_canonicalizes_cluster_split_bucket_to_split_bucket
test_17c_rejects_conflicting_split_bucket_aliases
test_topk_removed_mean_uses_original_denominator
test_topk_removal_uses_positive_contribution_groups_not_abs_losses
test_o4_high_upside_readout_variants_emit_topk_rows
test_bootstrap_rejects_row_independent_resampling
test_bootstrap_is_deterministic_for_frozen_random_seed
test_o4_high_upside_readout_variants_emit_bootstrap_rows
test_calendar_quarter_bootstrap_is_readout_only_when_under_min_clusters
test_matched_base_derives_calendar_and_board_buckets_without_split_leakage
test_matched_base_pass_share_is_equal_bucket_weighted_by_family
test_regime_matched_readout_requires_pit_audit_or_marks_provisional
test_known_failed_context_missing_is_not_evaluable_nonblocking
test_o7_delayed_semantics_use_original_h20_endpoint
test_o7_delayed_gap_vs_o5_is_diagnostic_not_support_gate
test_o7_rejects_restart_h20_at_t0_plus_k
test_o7_missing_t0_plus_k_price_blocks_delayed_curve
test_capacity_sort_key_uses_drawdown_abs_for_reporting_not_missing_drawdown_avoided_abs
test_capacity_appendix_only_does_not_emit_execution_capacity_blocked
test_capacity_evaluable_failure_can_emit_execution_capacity_blocked
test_o5_failure_after_topk_or_bootstrap_emits_no_action_value
test_o5_pass_with_o1_o2_o4_pass_emits_ready_for_diagnosis
test_no_policy_authorization_flags_are_true
```

## 19. Implementation Notes

Implementation must prefer structured data APIs over ad hoc string parsing.

The 17B row-level parquet is large and local-cache scoped. 17C may read it, but publishable outputs must remain aggregate CSV/JSON/PNG/MD artifacts. Do not publish the 17B or 17C row-level parquet unless a later requirement explicitly changes artifact policy.

If manual report edits are made after running 17C, the manifest `output_hashes.report` must be refreshed without rerunning a generator that overwrites the manual report.

## 20. Final Authorization Boundary

17C is a robustness diagnostic, not a strategy requirement.

Even if 17C returns:

```text
EP17C_oracle_robustness_ready_for_diagnosis
```

the only authorized next step is:

```text
requirement_17d_oracle_diagnosis_report.md
```

17C must explicitly keep:

```text
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
model_deployment_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```
