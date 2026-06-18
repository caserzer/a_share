# 12A0 + 12A1 Winner Registry Lineage and R-core Backbone Demotion Audit

## Final Decision

`decision = 12A1_r_core_recall_benchmark_only`

Reason: raw_r_core_fails_feature_source_minimum_or_event_quality_gates.

## A0 Population Registry

- 06 risk_on episodes: 428
- 11A2 frozen PIT candidate winner rows: 446
- 06 episodes with any 11A2 row in pre120-to-high: 120
- 06 episodes without 11A2 row in pre120-to-high: 308

The 06 episode target and 11A2 candidate-row readout remain separate populations.

## A1 Population Bridge

raw_08_r_core_contract/all=47914, risk_on_horizon_complete_09a/all=30790, post_dedup_10a_same_instrument/all=15802

The raw R-core decision is computed on `08_R_core_event_regime_gated_raw`. 09A and 10A/10B rows are compression/readout comparisons only.

## Raw R-core Metrics

- train pre120 episode recall: 1.0000
- robustness pre120 episode recall: 1.0000
- train low-to-high event precision: 0.0750
- robustness low-to-high event precision: 0.0788
- all density vs E1 full denominator: 7.0255

## Next Step

`next_allowed_requirement = stop_no_valid_backbone_for_morphology`
