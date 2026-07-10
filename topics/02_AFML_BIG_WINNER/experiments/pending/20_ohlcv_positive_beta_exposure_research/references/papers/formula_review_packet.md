# EP20A Formula Review Packet

This packet is pre-outcome. It does not authorize freeze.

- source manifest sha256: `0c55518aab927a1317ec3c69271e48a3925f14ba49cc34835b9f30ba6bfb9a95`
- formula draft sha256: `6c3e13cd12f5e5c5526218feecaf3ae2dbddb5c184f74719ee21d046c6453b90`

- acquired and validated sources: `9/11`

## Source checklist

| source_id | HTTP | bytes | material gate | local path / acquisition error |
|---|---:|---:|---|---|
| china_anomalies_full_paper | 200 | 1713434 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/china_anomalies_full_paper__f3a7452cff08c6ca.pdf |
| china_low_vol_full_article | 200 | 589336 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/china_low_vol_full_article__a4bcf93229408898.pdf |
| china_size_value_appendix | 200 | 251046 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/china_size_value_appendix__7e612f3688f809e4.pdf |
| china_size_value_full_paper | 200 | 633468 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/china_size_value_full_paper__40178157c9556453.pdf |
| fip_full_working_paper | 200 | 422763 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/fip_full_working_paper__39f432cbfe323794.pdf |
| ma_portfolio_timing_full_paper | 0 | 0 | fail | RuntimeError:urllib=HTTPError:HTTP Error 522: <none>;curl=CalledProcessError:Command '['curl', '-L', '--fail', '--silent', '--show-error', '--max-time', '90', '-A', 'Mozilla/5.0', 'https://www.nowandfutures.com/large/TA_profitability_ssrn-id1656460.pdf']' returned non-zero exit status 56. |
| ohlcv_cnn_full_paper | 200 | 1931469 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/ohlcv_cnn_full_paper__534c580c875e9266.pdf |
| residual_momentum_full_paper | 200 | 356559 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/residual_momentum_full_paper__db0ebbbe9de1d46d.pdf |
| technical_fdr_accepted_manuscript | 200 | 724688 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/technical_fdr_accepted_manuscript__5bcc2e5b56a4c4a1.html |
| trend_china_full_working_paper | 0 | 0 | fail | RuntimeError:urllib=HTTPError:HTTP Error 403: Forbidden;curl=CalledProcessError:Command '['curl', '-L', '--fail', '--silent', '--show-error', '--max-time', '90', '-A', 'Mozilla/5.0', 'https://acfr.aut.ac.nz/__data/assets/pdf_file/0014/324113/Y-Liu-New-TrendChina_12_1_WithAppendix.pdf']' returned non-zero exit st |
| trend_china_internet_appendix | 200 | 357812 | pass | topics/02_AFML_BIG_WINNER/experiments/pending/20_ohlcv_positive_beta_exposure_research/references/papers/source_materials/trend_china_internet_appendix__5704faa6a07acd3c.pdf |

## Formula checklist

| formula_id | source_id | page/equation anchor | current gate |
|---|---|---|---|
| TMOM_12_1 | residual_momentum_full_paper | p11-p12 portfolio definition | pending_human_review |
| TRENDPV_SIGNALS | trend_china_full_working_paper | equations 1-4, pp5-6 | pending_human_review |
| TRENDPV_MONTHLY_CS_REG | trend_china_full_working_paper | equations 5-7, p6 | pending_human_review |
| TRENDPV_FULL_FACTOR | trend_china_full_working_paper | section 2.2, pp6-7 | pending_human_review |
| RESMOM_EXACT_CH3 | residual_momentum_full_paper | equation 1 and pp11-12 | pending_human_review |
| RESMOM_R2_MARKET_ONLY_ADAPTATION | residual_momentum_full_paper | project adaptation of equation 1 and pp11-12 | pending_human_review |
| RESMOM_R3_BOARD_ADAPTATION | residual_momentum_full_paper | project two-stage adaptation of equation 1 and industry robustness | pending_human_review |
| LOWVOL_36M | china_low_vol_full_article | methodology low-volatility ranking | pending_human_review |
| FIP_ID | fip_full_working_paper | information discreteness definition | pending_human_review |
| MA20_OVERLAY | ma_portfolio_timing_full_paper | moving-average portfolio timing rule | pending_human_review |
| CNN_MAIN_DEFERRED | ohlcv_cnn_full_paper | image construction and prediction setup | pending_human_review |

## Authorization procedure

Review every formula against the cached local material, resolve every implementation choice, then sign
`formula_review_authorization.json`. Set each reviewed draft row's `formula_gate=pass`, then update both
hash fields, the complete reviewed source/formula ID lists, reviewer, reviewed_at,
all_implementation_choices_resolved=true and authorization_granted=true.

Do not authorize while any source material gate is fail or while any formula choice remains implicit.
