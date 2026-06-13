# Risk-on Post-Filter Cost Rejector Contract

- Scope reconstruction uses A `candidate_scope_mapping_contract.csv` and `source_row_count` bindings.
- R-core accepted published-reference difference: source row count 47914 vs published reference 47929.
- D summary `market_regime_bucket` is episode-side; D membership `market_regime_bucket` is event-side.
- Daily panel features join by `instrument` and latest `date <= event_t0_date` only.
- Labels join by `event_id + label_scope`; D membership labels reconcile against event-level labels.
- Final gates read from one selected `(model_id, threshold_id)`.
- Cost before/after denominators are horizon-complete events in the same source/split/regime cell.
