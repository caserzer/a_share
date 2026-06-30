# Oracle Action Contract

run_id = 17A_oracle_replay_contract_preflight

Primary cost grid:

```text
round_trip_defense_cost_bps = [0, 25, 50, 100]
primary_round_trip_defense_cost_bps = 50
delayed_action_semantics = within_original_h20_switch_v1
delayed_k_sessions = [3, 5, 10]
restart_h20_at_t0_plus_k = False
```

| action_family_id        | baseline_action    |   q_continue |   q_defend | round_trip_defense_cost_bps_grid   | action_semantics_gate   |
|:------------------------|:-------------------|-------------:|-----------:|:-----------------------------------|:------------------------|
| blind_continue          | blind_continue_h20 |            1 |       1    | 0,25,50,100                        | pass                    |
| full_defend_exit_cash   | blind_continue_h20 |            1 |       0    | 0,25,50,100                        | pass                    |
| partial_defend_50pct    | blind_continue_h20 |            1 |       0.5  | 0,25,50,100                        | pass                    |
| partial_defend_25pct    | blind_continue_h20 |            1 |       0.25 | 0,25,50,100                        | pass                    |
| delayed_decision_k      | blind_continue_h20 |            1 |       0    | 0,25,50,100                        | pass                    |
| learned_score_reference | blind_continue_h20 |            1 |       0    | 0,25,50,100                        | pass                    |
