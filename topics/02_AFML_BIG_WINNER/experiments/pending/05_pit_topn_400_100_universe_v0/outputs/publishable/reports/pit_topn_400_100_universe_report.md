# PIT Top-N 400/100 Universe Report

## Final decision

- Decision: `topn_universe_candidate_panel_blocked`
- Validation passed: `False`
- Active source gap count: `229`
- This experiment does not rerun 02 reverse lifecycle profile and does not produce a target episode denominator.
- Next step: rerun 02 reverse lifecycle profile on this universe only after the manifest decision is supported.

## Input source / manifest / hash audit

- Upstream 01 manifest hash: `d59ed5ff734c9d4f59f01ff713f8bd15f41cd56e397c5a897506e4540bd887f8`
- `fixed_cap_executable_csv`: `92c3d52d55354e86e5093f2849dd40da1a6677159f2f5f4c4af57927eb891a13`
- `fixed_cap_membership_csv`: `06e855088a6515ca72922449ddcbe3c7370421b9088681acee9fab6fb0631b4a`
- `instrument_metadata_csv`: `3175ae478bbfe9729d2b45cc0c8ca373fe903ee8d9acc9a96fed111441452601`
- `sz_name_change_csv`: `10b869499050656f356f91bea9fe22760bfe6ea1964368112595073cd15041b7`
- `trading_calendar_csv`: `1d5ff82a6718fc4e19b95c98456813043b30aeaa1b452d591376b1d427c2b60d`
- `upstream_01_config_yaml`: `62e0975519e4c82be5513e9604f6602ca1cb70fed6f9ea023abe0cbc5a533971`
- `upstream_01_daily_universe_counts_csv`: `ab7b4120f4397c5883b36f65c389ce879528cb370297a5ab46776054ef7a59e1`
- `upstream_01_market_cap_source_audit_csv`: `c0834916b0b1be02a8501d09c3efbc6c9321f185c6fbc10aa2b7d4abde529eee`
- `upstream_01_run_manifest_json`: `d59ed5ff734c9d4f59f01ff713f8bd15f41cd56e397c5a897506e4540bd887f8`
- `upstream_01_source_coverage_audit_csv`: `d35f0d96abbd9d571063e9a432fd47dbb942f98ba4e9d52135e4302563f1c024`

## Universe rule summary

- Main board: daily PIT total market cap rank <= 400.
- ChiNext: daily PIT total market cap rank <= 100.
- Ranking field: raw unadjusted close at membership date close times historical total share as-of.
- Deterministic tie-break: total_market_cap_cny desc, instrument asc.
- PIT clock: membership_date close is shifted to the next usable_trade_date.
- History readiness is diagnostic only; it is not a membership eligibility gate.

## Yearly universe summary

| year | trading_days | avg_daily_member_count | min_daily_member_count | max_daily_member_count | instrument_days | universe_years_252 | avg_main_board_count | avg_chinext_count | main_board_quota_fill_rate_mean | chinext_quota_fill_rate_mean | history_ready_240d_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | 244 | 500 | 500 | 500 | 122000 | 484.127 | 400 | 100 | 1 | 1 | 0.0145738 |
| 2018 | 243 | 500 | 500 | 500 | 121500 | 482.143 | 400 | 100 | 1 | 1 | 0.908008 |
| 2019 | 244 | 500 | 500 | 500 | 122000 | 484.127 | 400 | 100 | 1 | 1 | 0.944787 |
| 2020 | 243 | 500 | 500 | 500 | 121500 | 482.143 | 400 | 100 | 1 | 1 | 0.950099 |
| 2021 | 243 | 500 | 500 | 500 | 121500 | 482.143 | 400 | 100 | 1 | 1 | 0.952337 |
| 2022 | 242 | 500 | 500 | 500 | 121000 | 480.159 | 400 | 100 | 1 | 1 | 0.954364 |
| 2023 | 242 | 500 | 500 | 500 | 121000 | 480.159 | 400 | 100 | 1 | 1 | 0.973711 |
| 2024 | 242 | 500 | 500 | 500 | 121000 | 480.159 | 400 | 100 | 1 | 1 | 0.990413 |
| 2025 | 243 | 500 | 500 | 500 | 121500 | 482.143 | 400 | 100 | 1 | 1 | 0.990848 |
| 2026 | 95 | 500 | 500 | 500 | 47500 | 188.492 | 400 | 100 | 1 | 1 | 0.985958 |

## Quota fill audit

| board_bucket | avg_fill_rate | min_fill_rate | avg_eligible_count | avg_kept_count |
| --- | --- | --- | --- | --- |
| chinext | 1 | 1 | 750.133 | 100 |
| main_board | 1 | 1 | 2364.68 | 400 |

## Rank cutoff market cap distribution

| board_bucket | cutoff_min | cutoff_median | cutoff_max |
| --- | --- | --- | --- |
| chinext | 2.9128e+09 | 1.13874e+10 | 3.33761e+10 |
| main_board | 9.3867e+09 | 2.31654e+10 | 3.96584e+10 |

## Fixed-cap overlap

| board_bucket | topn_count_avg | fixed_cap_count_avg | intersection_avg | topn_only_avg | fixed_cap_only_avg | jaccard_avg |
| --- | --- | --- | --- | --- | --- | --- |
| chinext | 100 | 48.6765 | 45.5164 | 54.4836 | 3.16002 | 0.432491 |
| main_board | 400 | 157.873 | 157.873 | 242.127 | 0 | 0.394683 |

## History and exclusions

| year | board_bucket | member_rows | unique_instruments | history_ready_240d_count | history_observed_sessions_mean | history_observed_sessions_min | history_ready_240d_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | chinext | 24400 | 168 | 285 | 111.141 | 1 | 0.0116803 |
| 2017 | main_board | 97600 | 587 | 1493 | 117.953 | 1 | 0.0152971 |
| 2018 | chinext | 24300 | 192 | 20724 | 323.618 | 1 | 0.85284 |
| 2018 | main_board | 97200 | 571 | 89599 | 341.719 | 1 | 0.9218 |
| 2019 | chinext | 24400 | 196 | 21833 | 517.088 | 1 | 0.894795 |
| 2019 | main_board | 97600 | 548 | 93431 | 562.837 | 1 | 0.957285 |
| 2020 | chinext | 24300 | 214 | 22061 | 700.127 | 1 | 0.90786 |
| 2020 | main_board | 97200 | 594 | 93376 | 780.644 | 1 | 0.960658 |
| 2021 | chinext | 24300 | 207 | 21571 | 854.789 | 1 | 0.887695 |
| 2021 | main_board | 97200 | 603 | 94138 | 994.687 | 1 | 0.968498 |
| 2022 | chinext | 24200 | 166 | 20430 | 960.207 | 1 | 0.844215 |
| 2022 | main_board | 96800 | 552 | 95048 | 1222.7 | 1 | 0.981901 |
| 2023 | chinext | 24200 | 173 | 22100 | 1199.12 | 1 | 0.913223 |
| 2023 | main_board | 96800 | 529 | 95719 | 1465.93 | 1 | 0.988833 |
| 2024 | chinext | 24200 | 169 | 23356 | 1471.75 | 1 | 0.965124 |
| 2024 | main_board | 96800 | 541 | 96484 | 1700.85 | 1 | 0.996736 |
| 2025 | chinext | 24300 | 172 | 23715 | 1685.44 | 1 | 0.975926 |
| 2025 | main_board | 97200 | 548 | 96673 | 1921.79 | 1 | 0.994578 |
| 2026 | chinext | 9500 | 133 | 9244 | 1770.11 | 1 | 0.973053 |
| 2026 | main_board | 38000 | 506 | 37589 | 2074.24 | 1 | 0.989184 |

| board_bucket | missing_daily_bar_avg | st_excluded_avg | suspended_excluded_avg | missing_market_cap_avg |
| --- | --- | --- | --- | --- |
| chinext | 34.0517 | 10.8531 | 0 | 0 |
| main_board | 154.203 | 82.7063 | 0 | 0 |

## Source coverage

| support_state | instrument_count |
| --- | --- |
| missing_active_source | 229 |
| missing_inactive_source | 89 |
| supported | 4597 |
