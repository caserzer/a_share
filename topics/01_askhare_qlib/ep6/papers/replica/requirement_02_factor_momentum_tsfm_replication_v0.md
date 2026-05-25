# EP6 Paper Replica Requirement 02: Factor Momentum TSFM Replication V0

## 1. Requirement Metadata

requirement_id: `ep6_paper_replica_02_factor_momentum_tsfm_replication_v0`

short_name: `r02_factor_momentum_tsfm_replication_v0`

status: `requirement-draft`

workflow: `EP6`

created_date: `2026-05-25`

requirement_path: `ep6/papers/replica/requirement_02_factor_momentum_tsfm_replication_v0.md`

source_paper:

- local_pdf: `ep6/papers/02_factor_momentum_in_the_chinese_stock_market_ma_liao_jiang_2023.pdf`
- title: `Factor momentum in the Chinese stock market`
- authors: `Tian Ma, Cunfei Liao, Fuwei Jiang`
- journal: `Journal of Empirical Finance`
- doi: `10.1016/j.jempfin.2023.101458`

primary_output_namespace: `ep6/outputs/r02_factor_momentum_tsfm_replication_v0/`

## 2. Research Positioning

This requirement replicates only the paper's **time-series factor momentum** (`TSFM`) result under the local EP5 universe and data discipline.

It does not attempt to replicate:

```text
CSFM
60-anomaly extension
stock momentum / high-priced momentum / industry momentum regressions
factor timing vs buy-and-hold decomposition
information asymmetry mechanism tests
short-sale constraint mechanism tests
culture-index cross-country tests
strategy allocator / production portfolio
```

The local research question is:

```text
Using the EP5 PIT mcap500 mainboard universe,
can the locally implementable subset of the paper's TSFM construction produce
a positive, stable, out-of-sample factor-level momentum readout?
```

This is a replication diagnostic, not a strategy authorization.

Because the current local repository does not contain PIT accounting statement fields, this requirement first freezes a local feasible factor set. It is therefore:

```text
paper-inspired TSFM replication diagnostic
not exact 10-factor paper replication
```

## 3. Paper Result To Reproduce

The paper's main TSFM setup:

```text
Data:
  CSMAR A-share stocks, 2001-01 to 2019-12

Factors:
  10 characteristic-based non-momentum factors

Factor return:
  high-quintile average return minus low-quintile average return

TSFM signal:
  if factor's prior 12-month return > 0: long the factor next month
  if factor's prior 12-month return < 0: short the factor next month

Rebalance:
  monthly

Main sample:
  2002-01 to 2019-12
```

Key paper readout to reproduce directionally:

| Paper metric | Paper value |
|:--|--:|
| TSFM annualized mean return | 9.91% |
| TSFM t-stat | 4.88 |
| TSFM Sharpe | 1.15 |
| TSFM FF5 alpha | 9.59% |
| TSFM CH3 alpha | 7.76% |
| TSFM conditional CH3 alpha | 7.04% |
| TSFM winner-leg annualized return | 14.07% |
| TSFM loser-leg annualized return | 3.37% |

Local replication is not expected to match these magnitudes exactly because it uses a different universe, shorter sample, and local data availability. The target is to test whether the TSFM effect survives directionally under the EP5 PIT universe.

## 4. EP5 Universe And Data Inheritance

The replication must inherit EP5's local universe and timing discipline:

| Component | Required path / value |
|:--|:--|
| Qlib provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| PIT instrument map | `data/universe/pit_qlib_instrument_universe.csv` |
| PIT industry membership | `data/targets/pit_industry_membership.csv` |
| Trading calendar | `data/qlib/cn_data_pit/calendars/day.txt` |
| Qlib instrument file | `data/qlib/cn_data_pit/instruments/pit_mcap500_mainboard.txt` |
| Market benchmark / context | `SH000300` |
| Provider load end | `2026-04-30` |

The universe is **not** the old `selected` 36-stock pool and not the static `mcap500_mainboard_20251231` Explore1 universe.

The universe is:

```text
PIT mcap500 mainboard universe as of each monthly factor formation date.
```

Constituent eligibility on each rebalance date must require:

1. instrument is a PIT universe member as of the rebalance signal date;
2. instrument has enough price history for the next-month return label;
3. instrument has required factor values available as-of the rebalance signal date;
4. no future financial statement data may be used before its report availability / announcement date;
5. no stock outside the PIT universe may enter factor construction.

## 5. Sample Split

The split must follow EP5 calendar boundaries where possible:

| Split | Calendar window | Notes |
|:--|:--|:--|
| train | `2017-07-04` to `2021-12-31` | first 12 months are formation warmup; first evaluable TSFM month occurs after enough factor-return history exists |
| validation | `2022-01-01` to `2023-12-31` | primary out-of-sample decision window |
| robustness | `2024-01-01` to `2025-12-31` | post-validation robustness window |

Monthly timestamps:

```text
signal_month_end S_m = last trading date of calendar month m
holding_month H_{m+1} = next calendar month's tradable month

stock_month_return_{i,m+1} =
  provider-adjusted close return from S_m close to S_{m+1} close

factor_return_{f,m+1} =
  high-minus-low stock return formed at S_m and realized over H_{m+1}

tsfm_position_{f,m+1} =
  position formed at S_m using only factor_return labels m-11 through m

tsfm_return_{m+1} =
  tsfm_position_{f,m+1} multiplied by factor_return_{f,m+1}
```

No factor return with label `m+1` may enter the position for holding month `m+1`.

If the first evaluable TSFM month falls after `2018-07-31`, report the exact warmup start in `r02_tsfm_run_manifest.json`.

## 6. Data Availability Contract

This requirement must not fake a paper replication with price-only proxies.

Local data scan as of `2026-05-25`:

| Local source | Available fields |
|:--|:--|
| `data/qlib/cn_data_pit/features/*` | `open`, `close`, `high`, `low`, `volume`, `money`, `factor` |
| `data/universe/pit_mcap500_mainboard_daily.csv` | PIT membership, `total_share`, `market_cap_asof_T`, listing/status metadata |
| `data/targets/pit_industry_membership.csv` | PIT industry membership |
| `data/qlib/cn_data_pit/features/sh000300` / `data/targets/target_history.csv` | SH000300 index OHLCV |

Local data scan did **not** find PIT-ready fields for:

```text
book equity
total assets
gross profit
revenue
COGS
earnings / net income
operating cash flow
accrual statement components
financial report announcement dates
```

The paper's 10-factor TSFM requires characteristic inputs beyond OHLCV for most factors. The implementation must first create a data availability manifest:

`r02_factor_input_availability_manifest.csv`

Required columns:

```text
factor_id
paper_factor_name
required_raw_fields
available_raw_fields
availability_status
replication_action
local_formula_id
asof_policy
coverage_train_months
coverage_validation_months
coverage_robustness_months
coverage_train_instruments_median
coverage_validation_instruments_median
coverage_robustness_instruments_median
block_reason
```

Allowed `availability_status` values:

```text
available_full
available_partial
missing_required_fundamental_fields
missing_required_price_fields
missing_asof_timestamp
blocked_not_reproducible
```

Allowed `replication_action` values:

```text
retain
remove
```

The local feasible factor set is frozen before any validation performance is observed:

```text
local_feasible_factor_set_v0:
  retained:
    SIZE
    ILL
    TURN
    BAB
  removed:
    BM
    GP
    CINVEST
    EP
    ACC
    CFP
```

Removed factors may not be silently reintroduced. They can only be restored by a later requirement that adds a PIT accounting data source and defines explicit as-of rules.

Every run under this requirement must include the caveat:

```text
local_feasible_factor_set_not_paper_equivalent
```

The local Qlib OHLCV provider alone is insufficient for exact full paper replication because it provides price/volume/money/factor fields but not all required accounting fields. This requirement therefore removes unavailable accounting factors now, instead of leaving implementation to rediscover the same blocker.

Local price-adjustment contract:

```text
price_adjustment_mode = provider_ohlc_already_adjusted
primary_return_price = close from Qlib provider
do_not_reapply_factor_day_bin_to_ohlc = true
```

The local `factor` field may be used only as an audit field to confirm provider lineage. It must not be multiplied into OHLC prices in this requirement. If a later implementation changes `price_adjustment_mode`, it must emit a separate `price_adjustment_audit` artifact and cannot claim comparability to this requirement.

All PIT joins must be keyed by:

```text
date + instrument
```

`money` is the local turnover amount field. Implementations must not silently substitute `amount` or another provider-specific alias.

## 7. Factor Set

The paper factor universe and local feasibility decision are fixed:

| factor_id | Paper name | Local feasibility | Local fields | replication_action | Required local construction |
|:--|:--|:--|:--|:--|:--|
| `SIZE` | Size | implementable | `market_cap_asof_T` | retain | `local_SIZE_market_cap_high_minus_low_v0`; rank by `log(market_cap_asof_T)` at `S_m`; require positive market cap; high quintile minus low quintile |
| `BM` | Book-to-market / value | not implementable | missing book equity / shareholder equity | remove | `missing_required_fundamental_fields` |
| `GP` | Gross profitability | not implementable | missing gross profit, revenue/COGS, assets | remove | `missing_required_fundamental_fields` |
| `CINVEST` | Investment | not implementable | missing total assets and lagged asset growth | remove | `missing_required_fundamental_fields` |
| `ILL` | Illiquidity | implementable | daily return, `money` | retain | `local_ILL_amihud_21d_v0`; rank by prior 21 trading days ending `S_m`: `mean(abs(ret_d) / money_d)`; require `money_d > 0`, at least 15 valid observations; high minus low |
| `EP` | Earnings-to-price | not implementable | missing earnings / net income | remove | `missing_required_fundamental_fields` |
| `ACC` | Accruals | not implementable | missing accrual statement components and operating cash flow | remove | `missing_required_fundamental_fields` |
| `CFP` | Cash-flow-to-price | not implementable | missing operating cash flow | remove | `missing_required_fundamental_fields` |
| `TURN` | Turnover | implementable if volume units pass audit | `volume`, `total_share` | retain | `local_TURN_share_turnover_21d_v0`; rank by prior 21 trading days ending `S_m`: `mean(volume_d / (total_share_asof_T * 10000))`; require at least 15 valid observations; if `volume` unit or `total_share` unit cannot be verified, block `TURN` rather than using an unscaled proxy |
| `BAB` | Betting-against-beta | implementable as local beta-sort reconstruction | stock returns, `SH000300` returns | retain | `local_BAB_beta_sort_252d_v0`; rank by 252-trading-day beta to SH000300 ending `S_m`; require at least 126 overlapping daily returns and positive market-return variance; high beta minus low beta |

`BAB` is retained only as a local beta-sort reconstruction. It is not a full Frazzini-Pedersen leveraged, beta-neutral BAB implementation unless a later requirement explicitly adds the leverage / risk-free / beta-neutral construction.

No winsorization, factor-direction flip, lookback change, or missing-data imputation may be selected after validation returns are observed. Any cleaning rule beyond the formulas above must be frozen in the config before factor returns are computed.

The canonical retained factor list for this requirement is:

```text
SIZE
ILL
TURN
BAB
```

The canonical removed factor list for this requirement is:

```text
BM
GP
CINVEST
EP
ACC
CFP
```

For TSFM long-short returns, factor orientation is less fragile than in cross-sectional factor ranking because:

```text
sign(-past_return) * (-future_return) == sign(past_return) * future_return
```

Nevertheless, the raw factor construction direction must be recorded exactly in the manifest so that winner-leg and loser-leg diagnostics are interpretable.

The final report must not describe this run as a complete 10-factor paper replication. It must describe it as:

```text
4-factor local feasible TSFM replication diagnostic
```

## 8. Factor Construction Rules

For each factor `f` and month-end signal date `S_m`:

1. Build eligible stock universe from EP5 PIT universe on `S_m`.
2. Join factor value `x_{i,f,m}` using only data available as of `S_m`.
3. Drop instruments with missing `x_{i,f,m}` or missing next-month return.
4. Sort eligible instruments by `x_{i,f,m}`.
5. Assign quintiles using deterministic tie rules:

```text
sort by factor_value ascending, instrument_id ascending
split into 5 near-equal buckets
```

6. Compute next-month stock return:

```text
stock_month_return_{i,m+1} =
  close_{i,S_{m+1}} / close_{i,S_m} - 1
```

where `close` is the provider-adjusted close under `price_adjustment_mode = provider_ohlc_already_adjusted`.

Primary paper-style factor return:

```text
factor_return_{f,m+1,gross_equal_weight} =
  mean(next_month_return of high quintile)
  - mean(next_month_return of low quintile)
```

Primary construction is equal-weight inside high/low factor legs to keep the replication simple and avoid hidden optimization. If value-weighted or free-float-weighted factor returns are later added, they must be diagnostic-only and may not replace the primary equal-weight TSFM decision.

Minimum monthly factor coverage:

```text
eligible_instrument_count_per_factor_month >= 120
high_quintile_count >= 20
low_quintile_count >= 20
```

If a factor-month fails coverage, set:

```text
factor_month_status = blocked_insufficient_factor_month_coverage
```

and exclude it from TSFM for that month.

## 9. TSFM Signal Formula

For each factor `f` and signal month `m`, define prior 12-month factor return:

```text
past_12m_factor_return_{f,m} =
  compounded_return(
    factor_return_{f,m-11},
    factor_return_{f,m-10},
    ...,
    factor_return_{f,m}
  )
```

If factor returns are arithmetic long-short returns and compounding would produce unstable values, implementation may also report arithmetic sum as a diagnostic, but the primary formula must be frozen before running validation.

Primary TSFM position:

```text
tsfm_position_{f,m+1} =
  +1 if past_12m_factor_return_{f,m} > 0
  -1 if past_12m_factor_return_{f,m} < 0
   0 if past_12m_factor_return_{f,m} = 0
   0 if fewer than 12 complete prior factor returns exist
```

Monthly TSFM gross return:

```text
tsfm_return_{m+1} =
  mean over active factors f of:
    tsfm_position_{f,m+1} * factor_return_{f,m+1}
```

where active factors are retained factors with:

```text
complete 12-month formation history
complete holding-month factor return
replication_action = retain
```

Winner-leg diagnostic:

```text
tsfm_winner_leg_return_{m+1} =
  mean factor_return_{f,m+1} over factors with tsfm_position_{f,m+1} = +1
```

Loser-leg diagnostic:

```text
tsfm_loser_leg_return_{m+1} =
  mean factor_return_{f,m+1} over factors with tsfm_position_{f,m+1} = -1
```

If no winner or no loser factors exist in a month, report leg status as:

```text
leg_status = no_active_winner_factors
leg_status = no_active_loser_factors
```

and do not impute a zero return for leg diagnostics.

## 10. Cost And Executability Diagnostics

Paper-style replication must report gross returns first, but this requirement reconstructs factor legs from stock constituents. Therefore after-cost diagnostics are mandatory unless the run is data-blocked before factor-leg construction.

EP5-style executability diagnostics:

```text
buy_cost_bps = 30
sell_cost_bps = 80
round_trip_cost_bps = 110
entry_execution_rule = rebalance at month-end close-consistent implementation
execution_mode = stock_constituent_replay_after_cost_mode
```

Monthly turnover must be computed from the high/low stock legs used to produce each retained factor return:

```text
high_leg_turnover_{f,m+1} = one-way turnover of equal-weight high-quintile basket
low_leg_turnover_{f,m+1} = one-way turnover of equal-weight low-quintile basket

factor_after_cost_return_{f,m+1} =
  factor_gross_return_{f,m+1}
  - buy_turnover_{f,m+1} * 30bps
  - sell_turnover_{f,m+1} * 80bps
```

The TSFM after-cost diagnostic must be computed from the signed stock book implied by active TSFM factor positions:

```text
signed_factor_weight_{i,f,m+1} =
  tsfm_position_{f,m+1}
  * (+ equal_weight if i in high quintile for factor f
     - equal_weight if i in low quintile for factor f)

tsfm_signed_stock_weight_{i,m+1} =
  mean signed_factor_weight_{i,f,m+1} over active factors f

tsfm_buy_turnover_{m+1} =
  sum positive increases in tsfm_signed_stock_weight from m to m+1

tsfm_sell_turnover_{m+1} =
  sum absolute negative decreases in tsfm_signed_stock_weight from m to m+1

tsfm_after_cost_return_{m+1} =
  tsfm_gross_return_{m+1}
  - tsfm_buy_turnover_{m+1} * 30bps
  - tsfm_sell_turnover_{m+1} * 80bps
```

The cost replay is a diagnostic, not a deployability claim. Because some TSFM positions invert a long-short factor return, the report must explicitly identify months that require short exposure and must not assume shorting is freely available in A shares.

If the implementation cannot reconstruct stock-level turnover for a non-data-blocked run, final decision must be downgraded to:

```text
ep6_tsfm_replication_execution_replay_blocked
```

## 11. Required Metrics

Primary TSFM metrics by split:

```text
month_count
active_factor_count_mean
active_factor_count_min
annualized_mean_return
monthly_mean_return
monthly_volatility
annualized_volatility
sharpe_ratio
t_stat_monthly_mean
positive_month_share
max_drawdown
winner_leg_annualized_mean_return
loser_leg_annualized_mean_return
winner_factor_count_mean
loser_factor_count_mean
annualized_mean_return_after_cost
monthly_mean_return_after_cost
sharpe_ratio_after_cost
positive_month_share_after_cost
mean_buy_turnover
mean_sell_turnover
months_requiring_short_exposure
```

Required paper reference comparison table:

`r02_tsfm_paper_reference_comparison.csv`

Columns:

```text
metric
paper_value
local_train_value
local_validation_value
local_robustness_value
local_full_value
comparability_status
reference_gap
interpretation
```

Allowed `comparability_status` values:

```text
directional_reference_only
not_comparable_due_to_4factor_local_proxy
not_comparable_due_to_sample_universe_difference
```

`reference_gap` must be interpreted only as a descriptive difference from the paper's headline result. It must not be described as local underperformance or outperformance versus the paper, because this run uses a 4-factor local feasible proxy rather than the paper's full 10-factor universe.

Required factor-level diagnostics:

```text
factor_id
split
available_month_count
replication_action
local_formula_id
mean_factor_return
t_stat_factor_return
positive_month_share
mean_past_12m_return
tsfm_long_month_count
tsfm_short_month_count
tsfm_zero_month_count
tsfm_contribution_mean
tsfm_contribution_share_abs
```

## 12. Validation Gates

Because local monthly sample is much shorter than the paper sample, gates must be directional and diagnostic, not production-grade.

### 12.1 Data Gates

Pass requires:

```text
retained_factor_count >= 3
validation_evaluable_month_count >= 18
robustness_evaluable_month_count >= 18
active_factor_count_median >= 3
```

If these fail:

```text
sample_status = fail
final_decision = ep6_tsfm_replication_data_blocked_or_sample_insufficient
```

### 12.2 Validation Support Gates

Validation support requires all:

```text
validation_annualized_mean_return > 0
validation_t_stat_monthly_mean > 0
validation_sharpe_ratio > 0.25
validation_positive_month_share >= 0.50
validation_active_factor_count_median >= 3
```

### 12.3 Robustness Support Gates

Robustness support requires all:

```text
robustness_annualized_mean_return > 0
robustness_t_stat_monthly_mean > 0
robustness_sharpe_ratio > 0.25
robustness_positive_month_share >= 0.50
robustness_active_factor_count_median >= 3
```

### 12.4 Concentration Guard

No single factor may dominate the absolute TSFM contribution:

```text
validation_top1_factor_abs_contribution_share <= 0.60
robustness_top1_factor_abs_contribution_share <= 0.60
validation_top2_factor_abs_contribution_share <= 0.85
robustness_top2_factor_abs_contribution_share <= 0.85
```

If concentration fails while returns are positive:

```text
final_decision = ep6_tsfm_replication_positive_but_factor_concentrated
```

### 12.5 After-Cost Guard

After-cost diagnostics do not turn this requirement into a strategy test, but they must prevent an overclaimed positive result.

If gross validation and robustness gates pass but after-cost mean return is not positive in either validation or robustness:

```text
final_decision = ep6_tsfm_replication_gross_positive_after_cost_not_supported
```

## 13. Final Decision Logic

First-match decision priority:

1. If fewer than 3 retained factors are implementable, output:

```text
ep6_tsfm_replication_data_blocked_insufficient_retained_factors
```

2. Else if sample gates fail, output:

```text
ep6_tsfm_replication_data_blocked_or_sample_insufficient
```

3. Else if a non-data-blocked run cannot reconstruct stock-level turnover, output:

```text
ep6_tsfm_replication_execution_replay_blocked
```

4. Else if validation support gates fail, output:

```text
ep6_tsfm_replication_validation_not_supported
```

5. Else if validation passes but robustness support gates fail, output:

```text
ep6_tsfm_replication_validation_only_not_robust
```

6. Else if validation and robustness returns are positive but concentration guard fails, output:

```text
ep6_tsfm_replication_positive_but_factor_concentrated
```

7. Else if gross validation and robustness gates pass but after-cost guard fails, output:

```text
ep6_tsfm_replication_gross_positive_after_cost_not_supported
```

8. Else output:

```text
ep6_tsfm_4factor_local_proxy_positive_diagnostic_only
```

No final decision may authorize a live strategy or portfolio allocator.

## 14. Required Artifacts

All artifacts must be written under:

`ep6/outputs/r02_factor_momentum_tsfm_replication_v0/`

Required files:

| Artifact | Description |
|:--|:--|
| `configs/r02_factor_momentum_tsfm_replication_v0.yaml` | Frozen implementation config generated from this requirement |
| `manifests/r02_tsfm_run_manifest.json` | Run metadata, data mode, code version, date range, factor count, final decision |
| `manifests/r02_factor_input_availability_manifest.csv` | Factor input availability, retention/removal decision, and block reasons |
| `factors/r02_monthly_factor_returns.csv` | Monthly retained-factor return panel |
| `signals/r02_tsfm_monthly_signal_panel.csv` | Past 12m factor returns and TSFM positions |
| `returns/r02_tsfm_monthly_returns.csv` | Monthly TSFM, winner-leg, loser-leg returns |
| `reports/r02_tsfm_split_summary.csv` | Train / validation / robustness metrics |
| `reports/r02_tsfm_factor_contribution.csv` | Factor contribution and concentration diagnostics |
| `reports/r02_tsfm_paper_reference_comparison.csv` | Directional paper reference comparison, not exact paper replication |
| `reports/r02_tsfm_final_report.md` | Chinese final report |
| `validation/r02_tsfm_validation_manifest.json` | Machine-readable gate results |

If data is blocked, the run must still produce:

```text
manifests/r02_tsfm_run_manifest.json
manifests/r02_factor_input_availability_manifest.csv
reports/r02_tsfm_final_report.md
validation/r02_tsfm_validation_manifest.json
```

## 15. Report Requirements

The final report must be written in Chinese and include:

1. exact paper result used as reference;
2. local EP5 universe and sample differences;
3. factor input availability table;
4. retained factor table and removed factor table;
5. TSFM formula and active factor count;
6. train / validation / robustness split metrics;
7. winner-leg and loser-leg diagnostics;
8. factor contribution concentration;
9. paper reference comparison with explicit non-comparability caveat;
10. explicit statement:

```text
This is a 4-factor local feasible TSFM proxy diagnostic.
This is a paper-replication diagnostic only.
It does not authorize strategy construction.
```

## 16. Explicit Prohibitions

The implementation must not:

1. Use the 36-stock `selected` universe.
2. Use the static Explore1 `mcap500_mainboard_20251231` universe.
3. Reintroduce `BM`, `GP`, `CINVEST`, `EP`, `ACC`, or `CFP` without a later PIT fundamental-data requirement.
4. Replace missing fundamentals with price-only proxies.
5. Tune factor direction based on validation returns.
6. Tune formation window based on validation returns.
7. Add CSFM.
8. Add 60-anomaly TSFM.
9. Add stock momentum / industry momentum regressions.
10. Add portfolio optimization.
11. Output strategy authorization.
12. Treat a data-blocked run as a negative alpha result.
13. Reapply `factor.day.bin` or the provider `factor` field to OHLC prices under this requirement.
14. Switch `price_adjustment_mode` after observing returns.
15. Interpret `reference_gap` as local underperformance or outperformance versus the paper.

## 17. Implementation Notes

The first implementation should start with the data availability manifest before building any returns.

Recommended implementation sequence:

```text
1. Load EP5 PIT universe and calendar.
2. Load available local fields.
3. Build factor input availability manifest.
4. Freeze `price_adjustment_mode = provider_ohlc_already_adjusted`.
5. Enforce retained set `{SIZE, ILL, TURN, BAB}` and removed set `{BM, GP, CINVEST, EP, ACC, CFP}`.
6. Verify each retained factor's exact local formula and required unit assumptions.
7. If fewer than 3 retained factors are implementable, stop with data-blocked artifacts.
8. Construct monthly retained-factor return panel.
9. Construct TSFM positions using prior 12 monthly factor returns ending at signal month `m`.
10. Compute monthly TSFM gross and after-cost diagnostic returns.
11. Compute train / validation / robustness metrics.
12. Apply gate logic.
13. Write Chinese final report.
```

The requirement is intentionally strict about data blocking and comparison language because a price-only approximation or a 4-factor local proxy overclaim would answer a different question from the paper.
