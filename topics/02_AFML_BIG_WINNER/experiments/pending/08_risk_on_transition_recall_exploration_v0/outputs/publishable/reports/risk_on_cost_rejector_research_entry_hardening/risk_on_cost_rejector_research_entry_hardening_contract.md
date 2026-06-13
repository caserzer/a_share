# Risk-on Cost Rejector Research-Entry Hardening Contract

- H replays E's primary `08_R_core_event_regime_gated + supervised_joint_cost_rejector` only.
- `momentum_percentile_20d_lag20` is dropped before preprocessing and model fit.
- Daily panel features use latest `panel.date <= event_t0_date` by instrument.
- Cost before/after denominators use the same horizon-complete raw source cell.
- Threshold selection is train-only over `[0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]`.
- H threshold ids use four-digit keep suffixes such as `keep_0800`.
- Robustness-best threshold is diagnostic only.
- Density caps are predeclared in H config and are not tuned from H output.
- R-core accepts A's recorded 47914 vs 47929 published-reference difference.
