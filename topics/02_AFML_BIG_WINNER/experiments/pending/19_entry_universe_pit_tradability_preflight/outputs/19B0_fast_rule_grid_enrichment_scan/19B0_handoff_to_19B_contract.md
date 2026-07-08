# 19B0 Handoff to 19B Contract

19B may read robustness outcome only for rows frozen in `robustness_test_manifest.csv`.
Validation outcome remains forbidden in 19B.

19B must preserve `promotion_claim_type`, `residual_alpha_claim_allowed`, and the separate correction scopes.
A positive beta/exposure candidate without a matched-baseline residual pass can only support `19_entry_universe_enrichment_only_diagnostic`.

| family_id | grid_cell_id | promotion_claim_type | residual_alpha_claim_allowed | max_ep19_terminal_state_if_no_residual_pass |
|---|---|---|---:|---|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | positive_beta_exposure_candidate | False | 19_entry_universe_enrichment_only_diagnostic |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | positive_beta_exposure_candidate | False | 19_entry_universe_enrichment_only_diagnostic |
