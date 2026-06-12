# Experiment D Post-Replay Retention Source Contract

- 06 `episode_id` is canonicalized to D `target_episode_id`.
- 06 `split` is canonicalized to D `episode_split`.
- `candidate_family_capture.parquet` supplies replay window boundaries.
- C selected events are enriched through 08 canonical events by `canonical_event_id`.
- Membership uses instrument plus replay-anchor position inside materialized window bounds.
- `captured_target_episode_id_first` is audit-only and never a membership join key.
- All D replay policies have `entry_support_allowed = false`.
- Oracle policies are audit-only and use future labels.
