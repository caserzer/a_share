# Explore5 Walk-forward Report

- 本报告使用 2019-2024 overlapping two-year valid folds，并以 distinct-year 指标作为选择依据。
- 2025-2026 observed replication 未参与选择。

## 版本稳定性

| version | candidate_type | positive_valid_years | controlled_flat_years | qualified_valid_years | worst_year_drawdown | year_return_concentration | selected_for_freeze |
| --- | --- | --- | --- | --- | --- | --- | --- |
| frozen_fixed_weight | baseline | 0 | 0 | 0 | -11.66% | NA | False |
| risk_unit_with_industry_cap | candidate_baseline | 1 | 0 | 1 | -7.31% | 100.00% | False |
| breakout_only_diagnostic | diagnostic_only | 2 | 1 | 3 | -3.35% | 79.31% | False |
| pullback_regime_gated_diagnostic | diagnostic_only | 2 | 0 | 2 | -5.66% | 89.14% | False |

## Fold 结果

| version | fold | total_return_with_cost | max_drawdown | trades | avg_cash_ratio |
| --- | --- | --- | --- | --- | --- |
| breakout_only_diagnostic | WF1 | -1.17% | -5.20% | 50 | 95.99% |
| breakout_only_diagnostic | WF2 | 1.18% | -2.09% | 31 | 96.90% |
| breakout_only_diagnostic | WF3 | -1.78% | -2.02% | 12 | 99.11% |
| breakout_only_diagnostic | WF4 | 0.91% | -1.13% | 15 | 98.58% |
| breakout_only_diagnostic | WF5 | 0.42% | -2.62% | 32 | 96.75% |
| frozen_fixed_weight | WF1 | -6.96% | -18.81% | 168 | 79.07% |
| frozen_fixed_weight | WF2 | -3.58% | -10.06% | 123 | 85.22% |
| frozen_fixed_weight | WF3 | -8.30% | -10.38% | 48 | 96.02% |
| frozen_fixed_weight | WF4 | -3.30% | -5.14% | 50 | 94.79% |
| frozen_fixed_weight | WF5 | -4.76% | -12.05% | 170 | 83.18% |
| pullback_regime_gated_diagnostic | WF1 | -1.91% | -9.11% | 105 | 91.57% |
| pullback_regime_gated_diagnostic | WF2 | 0.23% | -3.74% | 70 | 93.96% |
| pullback_regime_gated_diagnostic | WF3 | -2.33% | -3.32% | 20 | 98.59% |
| pullback_regime_gated_diagnostic | WF4 | 0.12% | -1.62% | 23 | 98.34% |
| pullback_regime_gated_diagnostic | WF5 | 0.06% | -3.34% | 85 | 94.22% |
| risk_unit_with_industry_cap | WF1 | -5.22% | -12.14% | 168 | 87.36% |
| risk_unit_with_industry_cap | WF2 | -3.72% | -6.40% | 121 | 91.45% |
| risk_unit_with_industry_cap | WF3 | -4.89% | -6.39% | 46 | 97.69% |
| risk_unit_with_industry_cap | WF4 | -1.85% | -3.24% | 50 | 96.86% |
| risk_unit_with_industry_cap | WF5 | -2.47% | -7.33% | 167 | 89.82% |

## Distinct-year 结果

| version | calendar_year | year_return_with_cost | max_drawdown | trades | year_instances |
| --- | --- | --- | --- | --- | --- |
| breakout_only_diagnostic | 2019 | -0.92% | -3.35% | 24 | 1 |
| breakout_only_diagnostic | 2020 | 0.51% | -2.50% | 26 | 2 |
| breakout_only_diagnostic | 2021 | -0.34% | -1.28% | 4 | 2 |
| breakout_only_diagnostic | 2022 | -1.12% | -1.24% | 7 | 2 |
| breakout_only_diagnostic | 2023 | 1.97% | -1.08% | 8 | 2 |
| breakout_only_diagnostic | 2024 | -1.55% | -2.39% | 24 | 1 |
| frozen_fixed_weight | 2019 | -4.51% | -10.96% | 73 | 1 |
| frozen_fixed_weight | 2020 | -1.52% | -11.62% | 96 | 2 |
| frozen_fixed_weight | 2021 | -3.44% | -6.28% | 28 | 2 |
| frozen_fixed_weight | 2022 | -3.95% | -4.87% | 18 | 2 |
| frozen_fixed_weight | 2023 | -0.05% | -5.14% | 32 | 2 |
| frozen_fixed_weight | 2024 | -4.77% | -11.66% | 138 | 1 |
| pullback_regime_gated_diagnostic | 2019 | -1.29% | -5.66% | 46 | 1 |
| pullback_regime_gated_diagnostic | 2020 | 0.15% | -4.30% | 60 | 2 |
| pullback_regime_gated_diagnostic | 2021 | -0.87% | -1.94% | 11 | 2 |
| pullback_regime_gated_diagnostic | 2022 | -1.20% | -1.32% | 8 | 2 |
| pullback_regime_gated_diagnostic | 2023 | 1.25% | -1.64% | 15 | 2 |
| pullback_regime_gated_diagnostic | 2024 | -1.20% | -3.09% | 70 | 1 |
| risk_unit_with_industry_cap | 2019 | -2.80% | -7.01% | 72 | 1 |
| risk_unit_with_industry_cap | 2020 | -2.25% | -7.31% | 98 | 2 |
| risk_unit_with_industry_cap | 2021 | -1.97% | -3.50% | 25 | 2 |
| risk_unit_with_industry_cap | 2022 | -2.30% | -2.87% | 18 | 2 |
| risk_unit_with_industry_cap | 2023 | 0.05% | -3.26% | 32 | 2 |
| risk_unit_with_industry_cap | 2024 | -2.58% | -6.85% | 135 | 1 |
