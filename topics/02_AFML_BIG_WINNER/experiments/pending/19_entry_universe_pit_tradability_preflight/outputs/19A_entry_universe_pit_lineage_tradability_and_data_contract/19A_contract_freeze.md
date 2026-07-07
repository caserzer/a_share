# 19A Contract Freeze

run_id: `19A_entry_universe_pit_lineage_tradability_and_data_contract`
decision_state: `19A_entry_universe_contract_ready`
next_allowed_requirement: `requirement_19b0_fast_rule_grid_enrichment_scan.md`

19A materializes candidate and forward-label rows only for lineage,
denominator, tradability, path-completeness, sample-support, and
effective-sample audits. It does not train a model, rank candidates, select
thresholds from validation, or authorize any policy.

TuShare DC Eastmoney concept-board data is an annual vendor theme bucket.
Pre-2025 rows are fixed taxonomy backfill from the 2025 snapshot and are
forbidden as historical PIT matching keys. AkShare board dumps are quarantined
out of contract.
