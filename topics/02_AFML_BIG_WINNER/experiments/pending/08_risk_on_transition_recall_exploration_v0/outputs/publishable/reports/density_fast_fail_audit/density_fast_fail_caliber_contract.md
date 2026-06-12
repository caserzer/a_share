# Density / Fast-Fail Caliber Contract

This contract freezes the executable event-day density and fast-fail audit
caliber for Experiments B / C / D / E.

## Event Timing

- `event_t0` is the observable event date / position.
- `event_execution_key` is the next-open executable row.
- `event_window_anchor_pos` is `trade_open_pos` for executable rows and
  `event_t0_pos` only for non-executable audit rows.
- Non-executable rows remain in audit denominators and carry
  `event_window_anchor_status = non_executable_t0_fallback`.

## Rolling Density

- `rolling_10d_window_count_self_included` counts same-instrument and
  same-candidate-scope events in `[event_window_anchor_pos,
  event_window_anchor_pos + 10]`.
- Duplicate rates use ex-self neighbor counts, not self-included counts.
- The 20d window uses the same convention.

## Uniqueness

- `event_uniqueness_10d` uses active intervals
  `[event_window_anchor_pos, event_window_anchor_pos + 10]`.
- Concurrency is computed only within the same instrument and same candidate
  scope.
- E1 is a sparse reference anchor, not the alert baseline for expanded
  candidate families.

## Fast-Fail Labels

- `failure_10` and mapped `false_repair_10d` are forward diagnostic labels.
- They may be used for audit readouts and rejector targets only.
- Any replay that removes fast-fail events is an audit-only oracle replay and
  must not be described as an implementable t0 entry filter.

## Episode Density

Episode-window event counts are diagnostic-only. They must not set hard gates
unless an executable-timing diagnostic also fires, and even then the episode
window remains explanatory rather than a direct admission gate.
