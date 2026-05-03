# Explore5 Regime Holdout Report

- 所有 holdout 均在 T 日信号资格阶段排除，并重新进行完整组合回放。
- Holdout 版本只用于诊断，不形成冻结版本。

## Holdout Summary

| holdout | fold | total_return_with_cost | max_drawdown | trades | full_portfolio_replay |
| --- | --- | --- | --- | --- | --- |
| industry_sync_off | WF1 | -5.22% | -12.14% | 168 | True |
| industry_sync_off | WF2 | -3.72% | -6.40% | 121 | True |
| industry_sync_off | WF3 | -4.89% | -6.39% | 46 | True |
| industry_sync_off | WF4 | -1.85% | -3.24% | 50 | True |
| industry_sync_off | WF5 | -2.47% | -7.33% | 167 | True |
| pullback | WF1 | -1.17% | -5.20% | 50 | True |
| pullback | WF2 | 1.18% | -2.09% | 31 | True |
| pullback | WF3 | -1.78% | -2.02% | 12 | True |
| pullback | WF4 | 0.91% | -1.13% | 15 | True |
| pullback | WF5 | 0.42% | -2.62% | 32 | True |
| pullback_money_weak | WF1 | -2.30% | -8.19% | 86 | True |
| pullback_money_weak | WF2 | 2.09% | -2.32% | 49 | True |
| pullback_money_weak | WF3 | -1.93% | -2.32% | 14 | True |
| pullback_money_weak | WF4 | 0.60% | -1.27% | 20 | True |
| pullback_money_weak | WF5 | 0.15% | -3.39% | 72 | True |
| pullback_top10_20 | WF1 | -3.34% | -10.21% | 113 | True |
| pullback_top10_20 | WF2 | -1.09% | -4.19% | 76 | True |
| pullback_top10_20 | WF3 | -3.31% | -4.44% | 28 | True |
| pullback_top10_20 | WF4 | -0.44% | -1.91% | 27 | True |
| pullback_top10_20 | WF5 | -0.28% | -3.68% | 88 | True |
| width_weak | WF1 | -5.22% | -12.14% | 168 | True |
| width_weak | WF2 | -3.72% | -6.40% | 121 | True |
| width_weak | WF3 | -4.89% | -6.39% | 46 | True |
| width_weak | WF4 | -1.85% | -3.24% | 50 | True |
| width_weak | WF5 | -2.47% | -7.33% | 167 | True |

## Regime Attribution

| version | fold | year | regime_dimension | regime | trades | total_return_with_cost | net_pnl_sum |
| --- | --- | --- | --- | --- | --- | --- | --- |
| frozen_fixed_weight | WF1 | 2019 | industry_sync | industry_sync_on | 73 | -6.48% | -64,813 |
| frozen_fixed_weight | WF1 | 2019 | market_trend | market_trend_on | 73 | -6.48% | -64,813 |
| frozen_fixed_weight | WF3 | 2021 | market_trend | market_trend_on | 30 | -5.17% | -51,702 |
| frozen_fixed_weight | WF3 | 2021 | industry_sync | industry_sync_on | 30 | -5.17% | -51,702 |
| frozen_fixed_weight | WF5 | 2024 | industry_sync | industry_sync_on | 138 | -5.03% | -50,255 |
| frozen_fixed_weight | WF5 | 2024 | market_trend | market_trend_on | 138 | -5.03% | -50,255 |
| frozen_fixed_weight | WF5 | 2024 | trend_score | top10_20 | 86 | -4.89% | -48,938 |
| frozen_fixed_weight | WF1 | 2019 | trend_score | top10_20 | 41 | -4.82% | -48,213 |
| frozen_fixed_weight | WF5 | 2024 | width | width_strong | 132 | -4.82% | -48,173 |
| frozen_fixed_weight | WF1 | 2019 | entry_type | pullback | 56 | -4.73% | -47,334 |
| frozen_fixed_weight | WF1 | 2019 | width | width_strong | 60 | -4.45% | -44,492 |
| frozen_fixed_weight | WF2 | 2021 | market_trend | market_trend_on | 25 | -4.17% | -41,716 |
| frozen_fixed_weight | WF2 | 2021 | industry_sync | industry_sync_on | 25 | -4.17% | -41,716 |
| risk_unit_with_industry_cap | WF1 | 2019 | market_trend | market_trend_on | 72 | -4.07% | -40,658 |
| risk_unit_with_industry_cap | WF1 | 2019 | industry_sync | industry_sync_on | 72 | -4.07% | -40,658 |
| frozen_fixed_weight | WF1 | 2020 | pullback_money | pullback_money_weak | 60 | -3.95% | -39,505 |
| frozen_fixed_weight | WF1 | 2020 | alias | pullback_money_weak | 60 | -3.95% | -39,505 |
| frozen_fixed_weight | WF1 | 2019 | alias | pullback_money_weak | 48 | -3.88% | -38,808 |
| frozen_fixed_weight | WF1 | 2019 | pullback_money | pullback_money_weak | 48 | -3.88% | -38,808 |
| frozen_fixed_weight | WF5 | 2024 | alias | pullback_top10_20 | 74 | -3.77% | -37,680 |
