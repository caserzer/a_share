# Explore2 Alpha360 Expanded Search Report

## Scope

This rerun expanded both search layers while reusing cached data from `Explore1/data/qlib/cn_data`:

- Model search: 8 LightGBM parameter candidates under `Explore2/configs/model_search/`.
- Strategy search: `topk=20/30/50/80/100/150` x `n_drop=1/3/5/10/20`, 30 backtests.
- Prediction source for expanded strategy grid: `mlruns/9/db426cb9edea4f059f1b9619b7a405be/artifacts/pred.pkl`.

## Best Results

- Best default model candidate: `low_lr_deep` with default `topk=50,n_drop=5`, costed excess annualized return `39.59%`, IR `3.2452`.
- Best expanded-grid return: `topk=30,n_drop=1`, costed excess annualized return `49.42%`, IR `3.0650`.
- Best expanded-grid IR: `topk=150,n_drop=3`, costed excess annualized return `25.86%`, IR `3.7450`.
- Lowest drawdown row: `topk=150,n_drop=20`, max drawdown `-4.23%`.

## Model Search

| candidate | best_iteration | best_valid_l2 | IC | Rank IC | excess_return_with_cost.annualized_return | excess_return_with_cost.information_ratio | excess_return_with_cost.max_drawdown |
| --- | --- | --- | --- | --- | --- | --- | --- |
| low_lr_deep | 19 | 0.996298 | 0.0240149 | 0.00454537 | 39.59% | 3.24519 | -8.52% |
| high_lr_shallow | 12 | 0.996142 | 0.0282569 | 0.00224115 | 38.07% | 2.73339 | -9.43% |
| medium_reg | 38 | 0.996266 | 0.0271279 | 0.00557648 | 37.28% | 2.86438 | -10.89% |
| relaxed_current | 6 | 0.996327 | 0.0241423 | 0.00317163 | 36.56% | 2.95349 | -9.11% |
| low_reg_shallow | 33 | 0.9959 | 0.026335 | 0.00508139 | 35.75% | 2.73389 | -9.52% |
| light_reg_wide | 11 | 0.996017 | 0.0188126 | 0.00422842 | 35.25% | 2.65996 | -10.99% |
| current_rerun | 3 | 0.996383 | 0.0214196 | -0.000203268 | 32.72% | 2.74502 | -8.72% |
| strong_reg_small_leaf | 1 | 0.99639 | 0.0150519 | -0.00330656 | 25.88% | 2.06248 | -11.46% |

## Expanded Strategy Grid: Top By Return

| topk | n_drop | excess_return_with_cost.annualized_return | excess_return_with_cost.information_ratio | excess_return_with_cost.max_drawdown | strategy_return_with_cost.annualized_return | turnover_mean | cost_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 30 | 1 | 49.42% | 3.06501 | -9.58% | 65.54% | 7.04% | 0.01% |
| 20 | 1 | 46.39% | 2.61347 | -12.66% | 62.51% | 10.83% | 0.01% |
| 30 | 3 | 45.28% | 3.16157 | -9.00% | 61.40% | 20.16% | 0.02% |
| 20 | 3 | 44.19% | 2.81465 | -12.12% | 60.31% | 30.01% | 0.03% |
| 30 | 5 | 42.73% | 3.02688 | -9.23% | 58.86% | 33.22% | 0.03% |
| 50 | 5 | 39.59% | 3.24519 | -8.52% | 55.71% | 20.08% | 0.02% |
| 20 | 5 | 38.12% | 2.47979 | -10.44% | 54.24% | 49.09% | 0.05% |
| 50 | 1 | 37.15% | 2.95013 | -9.24% | 53.27% | 4.40% | 0.00% |
| 50 | 3 | 35.83% | 2.92135 | -10.18% | 51.95% | 12.21% | 0.01% |
| 100 | 1 | 34.98% | 3.68811 | -7.80% | 51.10% | 2.65% | 0.00% |
| 80 | 3 | 34.03% | 3.35446 | -7.62% | 50.16% | 7.81% | 0.01% |
| 80 | 1 | 33.77% | 3.40297 | -7.54% | 49.89% | 3.19% | 0.00% |
| 80 | 5 | 33.71% | 3.31173 | -7.09% | 49.83% | 12.78% | 0.01% |
| 100 | 3 | 32.50% | 3.62098 | -7.18% | 48.62% | 6.46% | 0.01% |
| 50 | 10 | 32.07% | 2.75789 | -8.90% | 48.19% | 39.33% | 0.04% |

## Expanded Strategy Grid: Top By IR

| topk | n_drop | excess_return_with_cost.annualized_return | excess_return_with_cost.information_ratio | excess_return_with_cost.max_drawdown | strategy_return_with_cost.annualized_return | turnover_mean | cost_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 150 | 3 | 25.86% | 3.74497 | -5.34% | 41.98% | 4.55% | 0.00% |
| 100 | 1 | 34.98% | 3.68811 | -7.80% | 51.10% | 2.65% | 0.00% |
| 100 | 3 | 32.50% | 3.62098 | -7.18% | 48.62% | 6.46% | 0.01% |
| 80 | 1 | 33.77% | 3.40297 | -7.54% | 49.89% | 3.19% | 0.00% |
| 150 | 1 | 23.27% | 3.35464 | -4.39% | 39.39% | 1.78% | 0.00% |
| 80 | 3 | 34.03% | 3.35446 | -7.62% | 50.16% | 7.81% | 0.01% |
| 80 | 5 | 33.71% | 3.31173 | -7.09% | 49.83% | 12.78% | 0.01% |
| 100 | 5 | 29.64% | 3.30824 | -7.25% | 45.76% | 10.31% | 0.01% |
| 150 | 10 | 22.45% | 3.26732 | -5.11% | 38.57% | 13.44% | 0.01% |
| 50 | 5 | 39.59% | 3.24519 | -8.52% | 55.71% | 20.08% | 0.02% |
| 100 | 10 | 27.76% | 3.22769 | -5.88% | 43.88% | 19.96% | 0.02% |
| 80 | 10 | 31.29% | 3.17603 | -7.04% | 47.41% | 24.92% | 0.02% |
| 150 | 5 | 22.20% | 3.16613 | -5.04% | 38.32% | 7.05% | 0.01% |
| 30 | 3 | 45.28% | 3.16157 | -9.00% | 61.40% | 20.16% | 0.02% |
| 30 | 1 | 49.42% | 3.06501 | -9.58% | 65.54% | 7.04% | 0.01% |

## Artifacts

- Model search summary: `Explore2/outputs/reports/alpha360_model_search_summary.csv`
- Expanded strategy summary: `Explore2/outputs/reports/alpha360_topk_grid_expanded_low_lr_deep_summary.csv`
- Expanded strategy backtests: `Explore2/outputs/backtests/alpha360_grid_expanded_low_lr_deep/`
- Updated default config: `Explore2/configs/qlib_lightgbm_alpha360_mcap500.yaml`
