# Payoff-state Target Contract

decision scope: EP18A contract preflight only

## Continuous Payoff Target

target_id = y_payoff_h20
definition = realized h20 close-to-close return from step_start to step_end
source_column = step_end_price_ratio_minus_one_for_label_rule
denominator = labelable_full
lineage_hash = 602ad3986a32d8634cb0948181be74c15a70cb50122d994d3ae7f253acbcc3d3

positive y_payoff_h20 means positive continuation payoff. Negative y_payoff_h20 means h20 loss.

## Action-value Identity

q_continue = 1.0
q_defend = 0.0
cost_bps = 50
cash_return = 0.0

continue_value = continue_net_return_h20
defend_value = defend_net_return_h20 under q_defend=0.0 and cost_bps=50
continue_advantage = continue_value - defend_value
defend_advantage = defend_value - continue_value
o5_incremental = max(0, defend_advantage)

Aggregate O5 incremental is computed over labelable_full rows. Non-defended rows contribute zero.

## Ordinal Payoff States

state_0 = below_top30_payoff if y_payoff_h20 < 0.0596330275229357
state_1 = top30_to_top20_payoff if top30 <= y_payoff_h20 < 0.1012285086722715
state_2 = top20_to_top10_payoff if top20 <= y_payoff_h20 < 0.1721071844362347
state_3 = top10_extreme_payoff if y_payoff_h20 >= 0.1721071844362347

state_1 and state_2 are the broad payoff-positive regions. state_3 is over-narrow stress only.

## Path-risk Auxiliary Target

y_signed_max_drawdown_h20 <= 0
risk_state_dd08 = signed_max_drawdown_h20 <= -0.08
risk_state_dd10 = signed_max_drawdown_h20 <= -0.10
risk_state_dd12 = signed_max_drawdown_h20 <= -0.12

Path-risk targets are auxiliary and cannot replace payoff-state target work.

## Binary Sanity Targets

Binary positive/negative labels, top30 yes/no, top20 yes/no, and drawdown yes/no are sanity targets only.
binary_metric_used_as_primary_gate = false
