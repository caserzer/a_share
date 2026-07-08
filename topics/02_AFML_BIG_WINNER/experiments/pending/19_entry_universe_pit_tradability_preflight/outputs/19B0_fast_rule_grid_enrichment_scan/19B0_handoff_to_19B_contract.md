# 19B0 Handoff to 19B Contract

19B may read robustness outcome only for rows frozen in `robustness_test_manifest.csv`.
Validation outcome remains forbidden in 19B.

## Promotion Claim Boundary

19B must preserve the `promotion_claim_type` and `residual_alpha_claim_allowed`
fields frozen by 19B0.

If `promotion_claim_type = positive_beta_exposure_candidate` and 19B does not
separately obtain a matched-baseline residual pass, the maximum EP19 terminal
state is:

```text
19_entry_universe_enrichment_only_diagnostic
```

Such a family/cell must not by itself authorize:

```text
19_entry_universe_pit_tradability_and_enrichment_supported
requirement_20_entry_universe_separability_or_policy_preflight.md
entry policy preflight
```

19B must not relabel positive beta/exposure persistence as residual alpha when
`residual_alpha_claim_allowed = false`.

## Correction Scope Boundary

Residual-alpha and positive-beta/exposure tracks use separate correction scopes:

```text
residual_alpha_correction_scope =
    N_residual_alpha_candidate_pairs * primary_tail_lift_50

positive_beta_exposure_correction_scope =
    N_positive_beta_exposure_candidate_pairs * positive_exposure_score_50
```

The two scopes must not be pooled into one `primary_metric` correction scope.

## Frozen Rows

| family_id | grid_cell_id | promotion_claim_type | residual_alpha_claim_allowed | max_ep19_terminal_state_if_no_residual_pass |
|---|---|---|---|---|
| none | none | none | false | none |
