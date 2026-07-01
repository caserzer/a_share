# Payoff-state Feature Contract

decision scope: EP18A feature-source inventory and leakage contract only

## Primary Feature Rule

Primary features must be observable at t0 and PIT-valid. EP18A does not materialize the full feature matrix.

Allowed primary candidate families if PIT and t0 audits pass:

- F1 continuation strength / repair persistence
- F2 participation / sponsorship
- F3 cross-sectional leadership
- F4 path-risk decoupling
- F5 regime / board / market context

F6 delayed observed-state features are appendix-only and must not enter a primary 18C model.

F7 external feature families are unavailable unless an existing PIT-valid source artifact is present.

## Forbidden Primary Columns

- future payoff
- step_end price
- step_end return
- future drawdown
- oracle action
- O1/O2/O4/O5 future labels
- label_class if used as model feature
- split id
- instrument id as raw model feature
- episode cluster id as raw model feature
- validation / robustness outcome-derived columns

No EP18A output authorizes entry, exit, holding, portfolio backtest, deployment, production signal, or live trading.
