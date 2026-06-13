# Experiment I Contract

- Scope: transition primary universe only.
- Primary question: previous-regime PIT context ablation for cost_bad sorting.
- Model: balanced L2 logistic regression; train-only preprocessing and threshold selection.
- Context collinearity policy: `previous_non_transition_regime` is audit-only; only `pit_transition_context` enters the model matrix.
- Forbidden fields: future outcome, next regime, complete segment duration, and conversion/continuation labels as model features.
- Decisions are diagnostic only and do not modify E/H risk_on selected threshold or manifests.
