# EP6 Paper Replica Requirement 07: Weekly Idiosyncratic Momentum Risk Horse Race V0

## 1. Requirement Metadata

requirement_id: `ep6_paper_replica_07_weekly_idiosyncratic_momentum_risk_horse_race_v0`

short_name: `r07_weekly_idiosyncratic_momentum_risk_horse_race_v0`

status: `requirement-draft`

workflow: `EP6`

created_date: `2026-05-26`

requirement_path: `ep6/papers/replica/requirement_07_weekly_idiosyncratic_momentum_risk_horse_race_v0.md`

source_paper:

- local_pdf: `ep6/papers/07_horse_race_weekly_idiosyncratic_momentum_china_shi_zhou_2021_arxiv.pdf`
- title: `Horse race of weekly idiosyncratic momentum strategies with respect to various risk metrics: Evidence from the Chinese stock market`
- authors: `Huai-Long Shi, Wei-Xing Zhou`
- version: `arXiv:1910.13115v2`
- paper_date: `2022-10-08`
- paper_sample: `China A-share common stocks, 1997-01 to 2017-12`

primary_output_namespace: `ep6/outputs/r07_weekly_idiosyncratic_momentum_risk_horse_race_v0/`

## 2. Research Positioning

This requirement replicates the paper's weekly **idiosyncratic momentum** (`IMOM`) horse-race idea under the local EP5 universe and data discipline.

The local research question is:

```text
Using the EP5 PIT mcap500 mainboard universe,
does weekly residual-return momentum outperform raw-return momentum,
and do IVOL / IMD risk filters improve the IMOM readout out of sample?
```

This is a replication diagnostic, not a strategy authorization.

The requirement does not attempt to replicate:

```text
full CSMAR stock universe
CSMAR Fama-French 5 factor residuals
CSMAR risk-free-rate excess returns
Baker-Wurgler sentiment index
IPO / closed-end fund discount sentiment inputs
paper's 1997-2017 historical sample
production short book or portfolio allocator
```

Because the local repository does not currently contain CSMAR daily FF5 factors or risk-free rates, this requirement is:

```text
paper-inspired local weekly IMOM horse-race diagnostic
not exact FF5 idiosyncratic momentum replication
```

Every final report under this requirement must include the caveat:

```text
local_residual_model_not_paper_FF5_equivalent
```

## 3. Paper Result To Reproduce Directionally

The paper's main setup:

```text
Data:
  CSMAR A-share common stocks, 1997-01 to 2017-12

Raw MOM:
  rank stocks by cumulative raw return over past J weeks

IMOM:
  estimate daily FF5 residual returns
  rank stocks by cumulative idiosyncratic return over past J weeks

Skip:
  one week between formation and holding

J:
  2, 3, 4, 8, 13, 26, 52 weeks

K:
  1, 2, 3, 4, 8, 13, 26, 52 weeks

Portfolio:
  equal-weight top decile minus bottom decile
```

Key paper readouts to reproduce directionally:

| Paper result | Directional target |
|:--|:--|
| raw weekly momentum | mostly contrarian in China after early sample |
| weekly IMOM | positive and significant across most J/K portfolios |
| strongest IMOM region | short formation / holding windows, especially J around 2-4 weeks and K around 1-4 weeks |
| idiosyncratic risk relation | most idiosyncratic risk metrics negatively related to future returns |
| strongest risk metrics | `IVOL` and `IMD` |
| best risk-adjusted IMOM variants | `IVOL-IMOM` and `IMD-IMOM`, especially under bivariate double sort |
| conditional performance | stronger in upside markets, high liquidity, and high sentiment states |

Local replication is not expected to match the paper's magnitudes because it uses a different universe, shorter local sample, and a market-model residual in place of CSMAR FF5 residuals. The target is to test whether the paper's ordering survives locally:

```text
IMOM better than raw MOM
IVOL / IMD risk-aware IMOM better than weaker risk metrics
short-horizon weekly windows stronger than long-horizon windows
```

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
| Market benchmark / residual benchmark | `SH000300` |
| Provider load end | `2026-04-30` |

The universe is:

```text
PIT mcap500 mainboard universe as of each weekly signal date.
```

Constituent eligibility on each weekly signal date must require:

1. instrument is a PIT universe member as of the signal date;
2. instrument has enough daily close history for the relevant J window;
3. instrument has enough next-holding-period price history for the relevant K label;
4. instrument has enough observations for residual estimation and risk metrics;
5. no stock outside the PIT universe may enter any portfolio;
6. all joins must be keyed by `date + instrument`.

The universe is not the old `selected` 36-stock pool and not the static `mcap500_mainboard_20251231` Explore1 universe.

## 5. Local Data Availability Contract

Local data scan as of this requirement:

| Local source | Available fields |
|:--|:--|
| `data/qlib/cn_data_pit/features/*` | `open`, `close`, `high`, `low`, `volume`, `money`, `factor` |
| `data/universe/pit_mcap500_mainboard_daily.csv` | PIT membership, `total_share`, `market_cap_asof_T`, listing/status metadata |
| `data/targets/pit_industry_membership.csv` | PIT industry membership |
| `data/qlib/cn_data_pit/features/sh000300` / `data/targets/target_history.csv` | SH000300 index OHLCV |

Local data scan did not find:

```text
daily CSMAR FF3 / FF5 factor returns
daily risk-free rate
Baker-Wurgler sentiment inputs
IPO count and first-day IPO returns
closed-end fund discount
dividend premium
equity issuance share
```

The run must create a local data availability manifest:

`r07_input_availability_manifest.csv`

Required columns:

```text
input_id
paper_required_input
local_source
availability_status
replication_action
local_proxy_id
asof_policy
coverage_train_weeks
coverage_validation_weeks
coverage_robustness_weeks
block_reason
```

Allowed `availability_status` values:

```text
available_full
available_partial
missing_required_factor_source
missing_required_sentiment_source
missing_required_price_fields
missing_asof_timestamp
blocked_not_reproducible
```

Allowed `replication_action` values:

```text
retain
retain_local_proxy
remove
diagnostic_only
```

Mandatory availability decisions:

| Paper input | Local action | Reason |
|:--|:--|:--|
| raw stock returns | `retain` | provider close available |
| FF5 residual returns | `retain_local_proxy` | replace with local market-model residual |
| idiosyncratic risk metrics | `retain_local_proxy` | compute from local residual returns |
| market state | `retain_local_proxy` | compute from SH000300 cumulative return |
| liquidity state | `retain_local_proxy` | compute local Amihud aggregate from return and `money` |
| sentiment state | `remove` | required BW sentiment inputs unavailable locally |

Local price-adjustment contract:

```text
price_adjustment_mode = provider_ohlc_already_adjusted
primary_return_price = close from Qlib provider
do_not_reapply_factor_day_bin_to_ohlc = true
```

The local `factor` field may be used only as an audit field to confirm provider lineage. It must not be multiplied into OHLC prices in this requirement.

## 6. Weekly Calendar And Sample Split

Weekly endpoints must be derived from the local trading calendar:

```text
week_end W_t = last trading day of each Friday-ending calendar week
skip week if the week has <= 2 trading days
weekly_return_{i,t} = close_{i,W_t} / close_{i,W_{t-1}} - 1
```

Formation and holding must follow the paper's one-week skip:

```text
formation window for signal t:
  weeks t-J-1 through t-2

skip week:
  week t-1

holding window:
  weeks t through t+K-1
```

Portfolio construction for holding week `t` may only use data available no later than `W_{t-1}`.

The local evaluation split is:

| Split | Calendar window | Notes |
|:--|:--|:--|
| warmup | `2017-01-03` to first complete signal date | used only for residual/risk/formation history |
| train | `2018-07-01` to `2021-12-31` | first complete local window after max lookback warmup |
| validation | `2022-01-01` to `2023-12-31` | primary out-of-sample decision window |
| robustness | `2024-01-01` to `2025-12-31` | post-validation robustness window |

Split assignment is based on the first week of the holding window. If a J/K portfolio cannot complete the full holding window before provider end, mark:

```text
holding_status = blocked_incomplete_future_return_label
```

and exclude that portfolio-week from metrics. Do not impute missing holding returns.

## 7. Local Idiosyncratic Return Model

The paper uses daily FF5 residuals. This local requirement freezes a simpler model before any validation returns are observed:

```text
local_residual_model_id = market_model_sh000300_ols_v0
```

For each stock `i` and each signal week `t`, estimate a rolling daily market model using daily returns over the required estimation window:

```text
r_{i,d} = alpha_i + beta_i * r_{mkt,d} + epsilon_{i,d}
```

where:

```text
r_{i,d} = close_{i,d} / close_{i,d-1} - 1
r_{mkt,d} = close_{SH000300,d} / close_{SH000300,d-1} - 1
```

Risk-free adjustment is omitted because no local daily risk-free source is available. The run manifest must record:

```text
risk_free_mode = omitted_missing_local_source
```

Minimum residual-estimation coverage:

```text
lookback_days_for_risk_metrics = 130 trading days
min_valid_days_for_130d_model = 90
min_valid_days_for_J_window_model = max(10, ceil(0.60 * J * 5))
market_return_variance > 0
```

The primary IMOM signal uses the daily residuals from the local market model. A diagnostic variant may also report raw market-adjusted returns:

```text
ret_minus_mkt_{i,d} = r_{i,d} - r_{mkt,d}
```

but this diagnostic may not replace the primary residual model unless a later requirement explicitly changes the residual model.

## 8. Signal Definitions

Canonical J values:

```text
2, 3, 4, 8, 13, 26, 52 weeks
```

Canonical K values:

```text
1, 2, 3, 4, 8, 13, 26, 52 weeks
```

Raw momentum signal:

```text
MOM_{i,t,J} =
  product over weeks u = t-J-1 through t-2 of (1 + weekly_return_{i,u}) - 1
```

Local idiosyncratic momentum signal:

```text
IMOM_{i,t,J} =
  product over trading days d in weeks t-J-1 through t-2 of (1 + epsilon_{i,d}) - 1
```

Primary short-horizon cluster:

```text
J in {2, 3, 4, 8, 13}
K in {1, 2, 3, 4}
```

Long-horizon diagnostics:

```text
J in {26, 52}
K in {8, 13, 26, 52}
```

No J/K subset may be selected after validation returns are observed. The final report may highlight the paper's short-horizon cluster, but it must still publish all canonical J/K tables.

## 9. Idiosyncratic Risk Metrics

Risk metrics are computed from local daily residual returns over the past 130 trading days ending no later than the final trading day of week `t-2`.

Retained primary risk metrics:

| metric_id | Local definition | Action |
|:--|:--|:--|
| `IVOL` | standard deviation of daily residual returns | primary |
| `IMD` | maximum drawdown of cumulative residual-return curve | primary |

Retained diagnostic risk metrics:

| metric_id | Local definition | Action |
|:--|:--|:--|
| `ISKEW` | skewness of daily residual returns | diagnostic |
| `IKURT` | kurtosis of daily residual returns | diagnostic |
| `IES5` | expected shortfall of residual returns at 5% left tail | diagnostic |
| `IVAR5` | VaR of residual returns at 5% left tail | diagnostic |
| `IES1` | expected shortfall of residual returns at 1% left tail | diagnostic |
| `IVAR1` | VaR of residual returns at 1% left tail | diagnostic |

Metric sign convention:

```text
IVOL, IMD, IES, IVAR are positive risk magnitudes.
higher value means higher idiosyncratic risk.
ISKEW and IKURT keep their natural statistical sign/value.
```

The risk-only portfolio buys the lowest-risk decile and shorts the highest-risk decile. If a metric has no stable economic ordering, such as `IKURT`, it remains diagnostic and cannot be used for primary conclusions.

## 10. Portfolio Construction Rules

For each signal week `t`, J, K, and portfolio family:

1. Build eligible stock universe from EP5 PIT universe as of `W_{t-1}`.
2. Drop instruments with insufficient formation, residual, risk, or holding data.
3. Sort by the relevant signal using deterministic tie rules:

```text
sort by signal_value ascending, instrument_id ascending
split into 10 near-equal decile buckets
```

4. Construct equal-weight decile portfolios.
5. Compute calendar-time overlapping portfolio returns for K-week holding windows.

Primary long-short return conventions:

```text
raw_mom_return = winner_decile_return - loser_decile_return
raw_contrarian_return = loser_decile_return - winner_decile_return

imom_return = high_IMOM_decile_return - low_IMOM_decile_return
risk_only_return = low_risk_decile_return - high_risk_decile_return
```

The paper reports raw momentum in a way that highlights contrarian effects. This local requirement must report both:

```text
raw_mom_W_minus_L
raw_contrarian_L_minus_W
```

Bivariate risk-adjusted IMOM is the primary risk-horse-race test:

```text
long leg:
  intersection of highest IMOM decile and lowest risk decile

short leg:
  intersection of lowest IMOM decile and highest risk decile

risk_adjusted_imom_return:
  long_leg_return - short_leg_return
```

Direct risk-adjusted IMOM is diagnostic only:

```text
direct_adjusted_signal = IMOM / risk_metric
```

Direct adjustment is allowed only for strictly positive risk metrics:

```text
IVOL, IMD, IES5, IVAR5, IES1, IVAR1
```

It is not allowed for `ISKEW` because negative skewness values create sorting ambiguity.

Minimum portfolio coverage:

```text
eligible_instrument_count >= 120
decile_count_min >= 10
bivariate_intersection_count_min >= 5 per leg
```

If a portfolio-week fails coverage, set:

```text
portfolio_week_status = blocked_insufficient_portfolio_coverage
```

## 11. Cost And Executability Diagnostics

Paper-style replication must report gross returns first. Because weekly long-short books are reconstructed from stock constituents, after-cost diagnostics are mandatory unless the run is data-blocked before portfolio construction.

EP5-style transaction-cost assumptions:

```text
buy_cost_bps = 30
sell_cost_bps = 80
round_trip_cost_bps = 110
execution_mode = weekly_stock_constituent_replay_after_cost_mode
```

For each weekly portfolio:

```text
buy_turnover_t = sum positive increases in signed stock weights
sell_turnover_t = sum absolute negative decreases in signed stock weights

after_cost_return_t =
  gross_return_t
  - buy_turnover_t * 30bps
  - sell_turnover_t * 80bps
```

The report must explicitly separate:

```text
gross paper-style diagnostic
after-cost executability diagnostic
long-leg return
short-leg return
```

The final report must not assume shorting is freely available in A shares. Any positive long-short result remains diagnostic unless a later requirement defines a feasible long-only or hedge-instrument implementation.

## 12. Conditional State Diagnostics

Market state diagnostics are retained:

```text
upside_market_26w:
  cumulative SH000300 return over prior 26 weeks > 0

downside_market_26w:
  cumulative SH000300 return over prior 26 weeks <= 0

upside_market_52w:
  cumulative SH000300 return over prior 52 weeks > 0

downside_market_52w:
  cumulative SH000300 return over prior 52 weeks <= 0
```

Liquidity diagnostics are retained with local Amihud aggregate:

```text
ILLIQ_{i,d} = abs(r_{i,d}) / money_{i,d}
AILLIQ_t = equal-weight mean over eligible stocks and trading days in week t

high_liquidity:
  AILLIQ_t below full-sample median

low_liquidity:
  AILLIQ_t above full-sample median

extreme_high_liquidity:
  AILLIQ_t below 20th percentile

extreme_low_liquidity:
  AILLIQ_t above 80th percentile
```

Sentiment diagnostics are blocked:

```text
sentiment_status = blocked_missing_Baker_Wurgler_inputs
```

Do not replace Baker-Wurgler sentiment with turnover alone in this requirement. Turnover already enters local liquidity and risk diagnostics.

## 13. Required Artifacts

The implementation must create:

```text
ep6/outputs/r07_weekly_idiosyncratic_momentum_risk_horse_race_v0/
  configs/
    r07_weekly_imom_horse_race_v0.yaml
  manifests/
    r07_input_availability_manifest.csv
    r07_weekly_imom_run_manifest.json
    r07_validation_manifest.json
  weekly/
    r07_weekly_calendar.csv
    r07_weekly_stock_returns.parquet
  residuals/
    r07_residual_model_manifest.csv
    r07_weekly_residual_signal_panel.parquet
  signals/
    r07_mom_signal_panel.parquet
    r07_imom_signal_panel.parquet
    r07_risk_metric_panel.parquet
    r07_bivariate_imom_risk_signal_panel.parquet
  returns/
    r07_raw_mom_jk_returns.csv
    r07_imom_jk_returns.csv
    r07_risk_only_jk_returns.csv
    r07_bivariate_risk_adjusted_imom_jk_returns.csv
    r07_direct_risk_adjusted_imom_jk_returns.csv
  reports/
    r07_jk_summary_raw_mom.csv
    r07_jk_summary_imom.csv
    r07_jk_summary_risk_only.csv
    r07_jk_summary_bivariate_risk_adjusted_imom.csv
    r07_metric_horse_race_summary.csv
    r07_conditional_state_summary.csv
    r07_final_report.md
```

Parquet may be replaced by CSV only if the implementation records the reason in `r07_weekly_imom_run_manifest.json`.

## 14. Required Metrics

Each J/K portfolio family must report by split:

```text
week_count
active_portfolio_count
eligible_instrument_count_mean
eligible_instrument_count_min
long_leg_count_mean
short_leg_count_mean
weekly_mean_return
annualized_mean_return = weekly_mean_return * 52
weekly_volatility
annualized_volatility = weekly_volatility * sqrt(52)
sharpe_ratio
t_stat_weekly_mean_newey_west
positive_week_share
max_drawdown
mean_buy_turnover
mean_sell_turnover
after_cost_weekly_mean_return
after_cost_annualized_mean_return
after_cost_sharpe_ratio
long_leg_weekly_mean_return
short_leg_weekly_mean_return
```

Primary summary rows:

```text
raw_mom_W_minus_L
raw_contrarian_L_minus_W
imom
IVOL_risk_only
IMD_risk_only
IVOL_IMOM_bivariate
IMD_IMOM_bivariate
```

Diagnostic summary rows:

```text
ISKEW_risk_only
IKURT_risk_only
IES5_risk_only
IVAR5_risk_only
IES1_risk_only
IVAR1_risk_only
IES5_IMOM_bivariate
IVAR5_IMOM_bivariate
IES1_IMOM_bivariate
IVAR1_IMOM_bivariate
direct_adjusted_IMOM variants
```

The final report must include a compact paper-reference comparison table:

| Paper claim | Local test | Supported locally? |
|:--|:--|:--|
| raw weekly MOM is mostly contrarian | raw W-L vs L-W J/K tables | yes/no/mixed |
| IMOM is positive | IMOM J/K tables | yes/no/mixed |
| IVOL and IMD are strongest risk metrics | horse-race summary | yes/no/mixed |
| bivariate risk-adjusted IMOM improves results | IVOL/IMD-IMOM vs pure IMOM | yes/no/mixed |
| upside market strengthens IMOM | conditional SH000300 state table | yes/no/mixed |
| high liquidity strengthens IMOM | conditional local Amihud table | yes/no/mixed |
| high sentiment strengthens IMOM | blocked | unavailable locally |

## 15. Validation Gates

This requirement has no strategy-authorization gate. It has only diagnostic gates.

Primary diagnostic gate:

```text
validation_short_cluster_imom_mean > validation_short_cluster_raw_mom_mean
validation_short_cluster_imom_mean > 0
robustness_short_cluster_imom_mean > 0
```

where:

```text
short_cluster = J in {2,3,4,8,13}, K in {1,2,3,4}
```

Risk horse-race gate:

```text
validation_short_cluster_best_of_IVOL_IMD_bivariate_mean
  >= validation_short_cluster_imom_mean

robustness_short_cluster_best_of_IVOL_IMD_bivariate_mean
  >= robustness_short_cluster_imom_mean
```

Weak support is allowed if one split passes and one split is mixed:

```text
ep6_weekly_imom_local_proxy_mixed_positive_diagnostic
```

Failure decisions:

```text
ep6_weekly_imom_local_proxy_not_supported
ep6_weekly_imom_data_blocked
ep6_weekly_imom_execution_replay_blocked
```

Positive diagnostic decision:

```text
ep6_weekly_imom_local_proxy_positive_diagnostic_only
```

Even if all diagnostic gates pass, the final report must state:

```text
authorized_strategy_requirement = false
```

## 16. Reproducibility Rules

All configuration choices must be frozen in:

```text
configs/r07_weekly_imom_horse_race_v0.yaml
```

before validation and robustness metrics are computed.

The run manifest must record:

```text
git_commit_or_worktree_status
created_at
python_version
qlib_provider_path
universe_path
calendar_path
price_adjustment_mode
residual_model_id
risk_free_mode
J_values
K_values
split_boundaries
cost_assumptions
blocked_inputs
```

No rule may be tuned after observing validation or robustness returns:

```text
J/K subset
residual model
risk metric sign convention
winsorization
minimum coverage thresholds
cost assumptions
split boundaries
```

If a bug fix changes historical metrics, the implementation must regenerate all downstream artifacts and document the change in `r07_validation_manifest.json`.

