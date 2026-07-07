# 19A Entry Universe Contract Report

## 1. Upstream Closure

EP19 restarts after 18F closed without a policy handoff.

```text
                required_fact                   observed_value upstream_closure_gate
               decision_state 18F_utility_bridge_not_supported                  pass
     next_allowed_requirement                             none                  pass
   policy_training_authorized                            False                  pass
     policy_replay_authorized                            False                  pass
        deployment_authorized                            False                  pass
 learned_utility_support_gate                             fail                  pass
      entry_policy_authorized                            False                  pass
       exit_policy_authorized                            False                  pass
    holding_policy_authorized                            False                  pass
portfolio_backtest_authorized                            False                  pass
  model_deployment_authorized                            False                  pass
 production_signal_authorized                            False                  pass
      live_trading_authorized                            False                  pass
```

## 2. Candidate Row Schema and Lineage

Primary materialized source: `EP07_topn_multichannel_recommended_union`.

```text
                                      candidate_generator_id                                   lineage_status  materialized_in_19a
           EP04_high_recall_repair_event_candidate_generator candidate_source_optional_until_adapter_selected                False
                    EP07_topn_multichannel_recommended_union                   lineage_supported_with_adapter                 True
                        EP13_full_pit_native_event_discovery candidate_source_optional_until_adapter_selected                False
EP14_full_native_sparse_state_change_event_utility_preflight candidate_source_optional_until_adapter_selected                False
```

## 3. Execution and Fill Feasibility

```text
decision_time_bucket         entry_price_source entry_execution_gate
       after_close_t qfq_open_next_tradable_day                 pass
```

```text
     split  cooldown_entry_n  fill_feasible_n  entry_limit_up_blocked_n fill_feasibility_gate
     train              5254             5116                         6                  pass
robustness              2640             2638                         2                  pass
validation              2902             2901                         1                  pass
```

## 4. Canonicalization and Cooldown

```text
 raw_trigger_rows  canonical_event_rows event_canonicalization_gate
            15161                 15161                        pass
```

```text
     split  cooldown_entry_rows  cooldown_suppressed_rows cooldown_entry_denominator_gate
     train                 5254                      2074                            pass
robustness                 2640                      1047                            pass
validation                 2902                      1244                            pass
```

## 5. Forward Label and Censoring

Forward label fields frozen: `27`. All are readout-only and
`candidate_membership_uses_forward_label = false`.

```text
     split  path_complete_120_rate censoring_treatment_gate
     train                1.000000                     pass
robustness                0.998863                     pass
validation                1.000000                     pass
```

## 6. Split Freeze

Validation does not select thresholds, families, or grid cells.

```text
     split min_decision_date max_decision_date  purge_window_sessions  embargo_window_sessions
     train        2018-01-18        2021-12-31                    120                       20
robustness        2024-01-02        2025-11-26                    120                       20
validation        2022-01-04        2023-12-29                    120                       20
```

## 7. TuShare DC Concept-Board Contract

TuShare DC concept-board yearly snapshots are the only in-contract board/theme
source. `15` classification years are marked as 2025 fixed-taxonomy
backfill and cannot be used as historical PIT matching keys.

## 8. AkShare Quarantine

`experiments/pending/19_entry_universe_pit_tradability_preflight/outputs/akshare_board_full_dump` is `quarantined_out_of_contract`.
Allowed use is `inventory_hash_provenance_audit_only`.

## 9. Industry / Board / Theme Support

```text
                          data_layer                           support_status  primary_feature_allowed
             industry_classification unsupported_external_pit_industry_source                    False
          industry_relative_strength              unsupported_primary_feature                    False
                    industry_breadth              unsupported_primary_feature                    False
board_or_style_proxy_from_tushare_dc                                forbidden                    False
              concept_or_theme_proxy  supported_as_annual_vendor_theme_bucket                     True
             akshare_board_full_dump              quarantined_out_of_contract                    False
```

## 10. Baseline Budget and Matching

```text
                              baseline_family      split  same_budget_row_count
             calendar_time_random_same_budget      train                   5116
             calendar_time_random_same_budget robustness                   2635
             calendar_time_random_same_budget validation                   2901
        instrument_matched_random_same_budget      train                   5116
        instrument_matched_random_same_budget robustness                   2635
        instrument_matched_random_same_budget validation                   2901
liquidity_size_volatility_matched_same_budget      train                   5116
liquidity_size_volatility_matched_same_budget robustness                   2635
liquidity_size_volatility_matched_same_budget validation                   2901
```

```text
                                    matching_key  primary_matching_allowed                theme_bucket_matching_policy
                                  decision_month                      True pre_2025_backfill_forbidden_as_matching_key
      instrument_or_industry_bucket_if_supported                     False pre_2025_backfill_forbidden_as_matching_key
            market_cap_bucket_asof_decision_date                      True pre_2025_backfill_forbidden_as_matching_key
    rolling_20d_amount_bucket_asof_decision_date                      True pre_2025_backfill_forbidden_as_matching_key
rolling_60d_volatility_bucket_asof_decision_date                      True pre_2025_backfill_forbidden_as_matching_key
     recent_20d_return_bucket_asof_decision_date                      True pre_2025_backfill_forbidden_as_matching_key
```

```text
                                 quality_metric                               quality_status baseline_matching_quality_gate
                       unmatched_candidate_rate frozen_pending_19B0_baseline_materialization                           pass
                            baseline_reuse_rate frozen_pending_19B0_baseline_materialization                           pass
max_standardized_mean_difference_after_matching frozen_pending_19B0_baseline_materialization                           pass
                  decision_month_coverage_delta frozen_pending_19B0_baseline_materialization                           pass
                      instrument_coverage_delta frozen_pending_19B0_baseline_materialization                           pass
             matched_baseline_primary_row_count frozen_pending_19B0_baseline_materialization                           pass
```

## 11. Grid Search and Multiplicity

```text
                                 family_id  grid_cell_n               family_status
   B1_near_120d_high_plus_volume_expansion           36    supported_primary_family
             B2_relative_strength_breakout           36    supported_primary_family
    B3_industry_or_theme_breadth_expansion            0 unsupported_primary_feature
   B4_volatility_contraction_then_breakout           36    supported_primary_family
B5_recent_high_close_plus_amount_expansion           36    supported_primary_family
    B6_low_drawdown_reclaim_or_ema_reclaim           36    supported_primary_family
```

```text
                                                   family_id  counts_toward_N_family_cap  N_supported_primary_family
           EP04_high_recall_repair_event_candidate_generator                       False                           6
                    EP07_topn_multichannel_recommended_union                        True                           6
                        EP13_full_pit_native_event_discovery                       False                           6
EP14_full_native_sparse_state_change_event_utility_preflight                       False                           6
                     B1_near_120d_high_plus_volume_expansion                        True                           6
                               B2_relative_strength_breakout                        True                           6
                      B3_industry_or_theme_breadth_expansion                       False                           6
                     B4_volatility_contraction_then_breakout                        True                           6
                  B5_recent_high_close_plus_amount_expansion                        True                           6
                      B6_low_drawdown_reclaim_or_ema_reclaim                        True                           6
```

```text
family_level_correction   cell_level_accounting      active_correction_scope                              status
       Bonferroni-Sidak all_tried_cells_counted pending_19B0_train_selection frozen_pending_19B0_train_selection
```

## 12. Minimum Sample and Effective Sample

```text
     split  primary_enrichment_denominator_rows  instrument_n
     train                                 5116           803
robustness                                 2635           551
validation                                 2901           602
```

```text
     split  effective_sample_n  effective_sample_ratio
     train                4889                0.955629
robustness                2544                0.965465
validation                2796                0.963806
```

## 13. Final Decision

`decision_state = 19A_entry_universe_contract_ready`

`next_allowed_requirement = requirement_19b0_fast_rule_grid_enrichment_scan.md`

Blocking reason: ``

19A does not prove that any entry signal works.

19A does not train a model.

19A does not authorize a strategy.

Pre-2025 TuShare DC concept membership is a fixed taxonomy backfill, not
historical PIT membership evidence.
