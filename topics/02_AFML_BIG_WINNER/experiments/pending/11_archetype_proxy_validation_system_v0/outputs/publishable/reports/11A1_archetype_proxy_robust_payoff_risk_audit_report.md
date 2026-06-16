# 11A1 Archetype Proxy Robust Payoff-Risk Audit Report

## 结论

本轮 11A1 采用严格分母：先取 `analysis_regime_bucket == risk_on`，再按 `instrument + event_t0_date = instrument + membership_date` inner join PIT executable universe，只保留 `is_listed=True`、`is_st=False`、`is_suspended=False` 的 PIT-valid 行进入 proxy threshold、matched base、bootstrap、top-k、multiple-comparison 与 final acceptance。

最终状态为：

```text
11A1_archetype_proxy_robust_payoff_risk_screen_empty
```

含义是：输入、join、PIT/ST/停牌完整性与多重比较审计都通过，但 8 个预注册 t0 proxy family 没有任何一个同时满足右尾捕获、payoff 非劣、failure 暴露稳定不恶化、matched-base power 与 top-k 稳定性要求。

| 项目 | 数值 |
| --- | ---: |
| 10A pre-filter row_n | 200,250 |
| 10A primary denominator row_n | 15,802 |
| risk_on pre-PIT row_n | 11,293 |
| strict PIT-valid evaluated row_n | 4,665 |
| PIT excluded row_n | 6,628 |
| PIT excluded rate | 58.69% |
| risk_off out-of-scope row_n | 3,469 |
| transition out-of-scope row_n | 1,040 |
| regime missing row_n | 0 |
| supported proxy_n | 0 |
| hard-veto failed proxy_n | 6 |
| underpowered proxy_n | 2 |

核心判断：

- `screen_empty` 不是数据不可用导致的保守结论；过滤后的 denominator 在 PIT/ST/停牌审计中 `pit_membership_match_rate=1.0`，`st_row_n=0`，`suspended_row_n=0`，`not_listed_row_n=0`，status=`ok`。
- 严格 PIT 后，之前 58.69% 的 risk_on 样本不再进入 evaluated denominator。这个过滤会明显改变 winner 分布，尤其 `before_first_pit_membership` 被排除样本的 winner_120_rate 为 25.61%，远高于 PIT-valid 的 9.56%。因此本报告结论只适用于当前 PIT largecap main/chinext executable universe。
- 失败的主要原因不是 proxy 没有任何右尾信号，而是右尾信号和 failure exposure 绑定太紧。`P4_momentum_leader` 与 `P6_repair_structure` 有较高 winner uplift，但同时有显著 big_failure uplift；`P3_volatility_expansion` 风险读数较好但右尾捕获不够；`P7`、`P8` 覆盖过宽导致 matched base underpowered。

## 数据来源与 Join

| 审计项 | left_row_count | matched_row_count | match_rate | 状态 |
| --- | ---: | ---: | ---: | --- |
| 10A -> 10C canonical id | 15,802 | 15,802 | 100.00% | ok |
| 10A -> 09B feature matrix | 15,802 | 15,802 | 100.00% | ok |
| 10A -> 08 label path | 15,802 | 15,802 | 100.00% | ok |
| 10A -> 09A label frontier | 15,802 | 15,802 | 100.00% | ok |

补充说明：

- canonical id 全部来自 10C join：`canonical_id_10c_join_success_rate=1.0`，`canonical_id_fallback_to_join_key_parse_rate=0.0`。
- 08 label path 右表有 `duplicate_right_key_n=2063`，但 join 后 split、instrument、event_t0_date 校验均为 100%，没有影响当前 evaluated denominator。
- 09B sample uniqueness weights 在 strict PIT-valid denominator 内全部命中 supported-training 权重：`supported_training_weight_row_n=4665`，`readout_only_fallback_row_n=0`，`unit_weight_fallback_row_n=0`。

## Regime Scope

`analysis_regime_bucket` 使用 `09A.episode_regime_bucket -> 10A.event_regime_bucket -> 09A.event_regime_bucket` 回填。残余 missing 为 0。本轮只保留 `risk_on`，不比较 `risk_off` 或 `transition`。

| split | primary row_n | risk_on pre-PIT | risk_on rate | risk_off excluded | transition excluded |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 8,318 | 5,836 | 70.16% | 1,663 | 819 |
| validation | 2,514 | 1,898 | 75.50% | 542 | 74 |
| robustness | 4,970 | 3,559 | 71.61% | 1,264 | 147 |
| all | 15,802 | 11,293 | 71.47% | 3,469 | 1,040 |

## Strict PIT Filter

PIT 过滤后分母如下：

| split | risk_on pre-PIT | PIT-valid evaluated | PIT join/valid rate | excluded row_n | excluded rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 5,836 | 1,708 | 29.27% | 4,128 | 70.73% |
| validation | 1,898 | 865 | 45.57% | 1,033 | 54.43% |
| robustness | 3,559 | 2,092 | 58.78% | 1,467 | 41.22% |
| all | 11,293 | 4,665 | 41.31% | 6,628 | 58.69% |

PIT 排除不是由 ST/停牌/非上市状态造成：`non_listed_excluded_row_n=0`，`st_excluded_row_n=0`，`suspended_excluded_row_n=0`。排除主要来自 PIT universe membership 本身。

| PIT reason | row_n | unique instrument_n | winner_120_rate | big_failure_proxy_rate |
| --- | ---: | ---: | ---: | ---: |
| pit_valid | 4,665 | 593 | 9.56% | 35.41% |
| instrument_never_in_pit | 2,966 | 585 | 6.91% | 47.10% |
| before_first_pit_membership | 1,679 | 308 | 25.61% | 40.02% |
| not_pit_member_on_event_t0_date | 1,124 | 246 | 11.74% | 32.38% |
| after_last_pit_membership | 859 | 177 | 1.28% | 41.68% |

按年份看，PIT coverage 随时间明显改善，早期样本被排除更多：

| event_year | pre-PIT row_n | PIT-valid row_n | valid rate | excluded rate | PIT-valid winner_rate | excluded winner_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2018 | 321 | 84 | 26.17% | 73.83% | 2.38% | 2.11% |
| 2019 | 1,452 | 300 | 20.66% | 79.34% | 2.00% | 7.55% |
| 2020 | 1,948 | 533 | 27.36% | 72.64% | 18.95% | 17.39% |
| 2021 | 2,115 | 791 | 37.40% | 62.60% | 5.31% | 13.60% |
| 2022 | 738 | 297 | 40.24% | 59.76% | 0.67% | 3.63% |
| 2023 | 1,160 | 568 | 48.97% | 51.03% | 2.46% | 4.22% |
| 2024 | 1,519 | 833 | 54.84% | 45.16% | 5.64% | 6.56% |
| 2025 | 2,040 | 1,259 | 61.72% | 38.28% | 18.43% | 22.28% |

按 board 看，创业板 PIT-valid coverage 高于主板，但创业板的 failure exposure 也更高：

| board | pre-PIT row_n | PIT-valid row_n | valid rate | PIT-valid winner_rate | PIT-valid big_failure_rate | excluded big_failure_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| chinext | 2,239 | 1,134 | 50.65% | 15.43% | 50.62% | 55.48% |
| main_board | 9,054 | 3,531 | 39.00% | 7.67% | 30.53% | 39.44% |

Insight：strict PIT 是必要的，否则会把大量不属于当前可执行 universe 的样本混入分母。但 strict PIT 也改变了 archetype 分布，尤其排除了很多 `before_first_pit_membership` winner。后续 11B/11C 不应把本轮结论外推到非 PIT 或历史入池前状态。

## Proxy Registry 与 Threshold

所有 8 个 proxy family 均来自 09B t0-visible feature contract，`proxy_input_status=ok`。阈值只在 strict PIT-valid train denominator 内拟合，`fit_row_n=1708`，所有字段 `pre_imputation_missing_rate=0`。

| proxy | 字段 | 关键 train 阈值 |
| --- | --- | --- |
| P1_gap_event | `gap_open_pct`, `intraday_range_atr_norm`, `close_position_in_range`, `amount_ratio_20d`, `turnover_ratio_20d`, `family_count`, `channel_count` | gap_open_pct p70=0.0730；intraday_range_atr_norm p70=0.3527；close_position_in_range p60=0.5786；amount_ratio_20d p70=0.1493 |
| P2_shakeout_prior_path | `close_to_high_60`, `close_to_high_120`, `upper_shadow_pct`, `close_position_in_range`, `atr_pct_rank_60d`, `stock_vs_board_20d` | close_to_high_60 p30=-0.4097；close_to_high_120 p30=-0.4324；upper_shadow_pct p60=-0.2134；atr_pct_rank_60d p40=-0.6594 |
| P3_volatility_expansion | `direction_entropy_20d`, `atr_pct_rank_60d`, `range_width_ratio_20d_60d` | direction_entropy_20d p60=0.6380；atr_pct_rank_60d p60=0.1328；range_width_ratio_20d_60d p60=-0.3400 |
| P4_momentum_leader | `momentum_percentile_20d`, `return_20d`, `close_to_ema20` | momentum_percentile_20d p70=0.3092；return_20d p60=-0.4451；close_to_ema20 p50=-0.5296 |
| P5_low_noise_accumulation | `return_20d`, `atr_pct_rank_60d`, `prior_event_count_60d`, `ema60_positive_run` | return_20d p35=-0.6961 / p65=-0.3630；atr_pct_rank_60d p60=0.1328；prior_event_count_60d p50=-0.6032 |
| P6_repair_structure | `close_to_ema20`, `close_to_ema60`, `ema20_slope_20d`, `atr_pct_rank_60d` | close_to_ema20 p50=-0.5296；close_to_ema60 p50=-0.5806；ema20_slope_20d p50=-0.4468；atr_pct_rank_60d p70=0.5289 |
| P7_flow_confirmation | `quality_amount_flag`, `amount_ratio_20d`, `turnover_ratio_20d` | quality_amount_flag == 1；amount_ratio_20d p70=0.1493；turnover_ratio_20d p60=-0.0379 |
| P8_recurrence_density | `prior_event_count_60d`, `raw_cluster_event_count`, `family_count`, `channel_count` | prior_event_count_60d p70=-0.0636；raw_cluster_event_count p70=0.3574；family_count p60=-0.6226；channel_count p60=-0.6025 |

## Proxy Coverage、Matched Base 与 Acceptance

| proxy | status | evidence | coverage | train/robust matched coverage | all winner delta | all big failure delta | all 60d median delta | all 60d winsorized mean delta | train/robust P(failure delta <= 0.5pp) | train/robust failure p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1_gap_event | `proxy_hard_veto_failed` | 2/6 | 51.70% | 96.98% / 98.80% | +1.21% | -0.08% | -2.15% | -1.36% | 0.764 / 0.052 | +3.32% / +9.62% |
| P2_shakeout_prior_path | `proxy_hard_veto_failed` | 2/6 | 18.07% | 100.00% / 99.57% | +2.23% | +8.20% | -3.51% | -2.73% | 0.152 / 0.006 | +11.18% / +15.95% |
| P3_volatility_expansion | `proxy_hard_veto_failed` | 3/6 | 12.86% | 100.00% / 99.65% | -0.44% | -3.67% | -0.43% | +0.17% | 0.394 / 0.999 | +9.54% / -5.48% |
| P4_momentum_leader | `proxy_hard_veto_failed` | 3/6 | 17.83% | 99.78% / 99.75% | +6.11% | +10.34% | -1.99% | +0.63% | 0.015 / 0.001 | +19.41% / +16.88% |
| P5_low_noise_accumulation | `proxy_hard_veto_failed` | 2/6 | 10.91% | 98.29% / 100.00% | +2.08% | +1.58% | -0.64% | -0.32% | 0.184 / 0.208 | +12.53% / +12.54% |
| P6_repair_structure | `proxy_hard_veto_failed` | 4/6 | 11.47% | 99.29% / 100.00% | +5.80% | +7.34% | -3.60% | +0.69% | 0.395 / 0.010 | +10.55% / +16.71% |
| P7_flow_confirmation | `proxy_underpowered` | 1/6 | 70.72% | 66.41% / 62.35% | -2.48% | -1.75% | +0.28% | -0.10% | 0.405 / 0.593 | +7.99% / +5.06% |
| P8_recurrence_density | `proxy_underpowered` | 1/6 | 98.48% | 4.58% / 15.49% | +4.26% | +22.54% | -8.27% | -4.22% | 0.076 / 0.255 | +37.99% / +28.87% |

字段解释：

- `winner delta`、`big failure delta`、`60d median delta`、`60d winsorized mean delta` 都是 proxy-positive 相对 matched base 的差。
- `P(failure delta <= 0.5pp)` 是 bootstrap failure hard veto 的核心概率读数；低于阈值说明无法证明 failure 暴露没有恶化。
- `failure p95` 是 bootstrap failure delta 的 95 分位；远高于 +1.5pp 的 proxy 不应支持。

关键观察：

- `P4`、`P6` 是最接近“winner archetype proxy”的两类：all split winner delta 分别为 +6.11pp、+5.80pp，evidence 分别为 3/6、4/6。但它们同时带来 +10.34pp、+7.34pp 的 big_failure delta，robustness failure p95 分别达到 +16.88pp、+16.71pp，因此不能作为保护性 screen。
- `P3` 是唯一 all split big_failure delta 显著为负的 proxy（-3.67pp），robustness failure bootstrap 也稳定，但它的 winner delta 为 -0.44pp，right-tail capture 不达标。
- `P7` 看似风险略降，但 coverage 70.72%，matched positive coverage 只有 66.41% / 62.35%，说明可比负样本不足；其 proxy 定义太宽，不适合作为可支持的 archetype screen。
- `P8` 覆盖 98.48%，几乎等于全分母，matched base 退化为极少数 negative rows；train matched coverage 仅 4.58%，因此所有 uplift 读数都不可信。

## Split-Level Payoff-Risk Delta

下表只列核心 delta。单位为百分点或 return 小数差值。

| proxy | split | winner delta | big failure delta | false repair delta | fast fail delta | 60d median return delta | 60d winsorized mean delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | train | -1.41% | -1.61% | -0.73% | +0.23% | -1.83% | -1.31% |
| P1 | validation | -0.16% | -5.57% | -4.69% | -1.05% | -1.07% | -0.53% |
| P1 | robustness | +5.13% | +5.24% | +8.18% | -4.59% | -3.36% | -1.70% |
| P2 | train | -2.29% | +4.73% | +4.95% | +0.44% | -2.78% | -3.68% |
| P2 | validation | +1.24% | +11.81% | +14.80% | -3.87% | -3.55% | -2.91% |
| P2 | robustness | +6.95% | +9.53% | +12.06% | -1.37% | -3.95% | -1.93% |
| P3 | train | -3.58% | +1.31% | +2.91% | -5.17% | +0.31% | -0.90% |
| P3 | validation | +2.63% | +2.83% | +5.12% | -9.55% | +0.84% | +1.86% |
| P3 | robustness | +0.73% | -10.68% | -8.59% | -7.20% | +0.19% | -0.14% |
| P4 | train | +4.39% | +11.08% | +11.94% | -9.27% | -1.79% | -0.25% |
| P4 | validation | +0.49% | +7.70% | +11.12% | -5.55% | -6.18% | -5.16% |
| P4 | robustness | +11.12% | +10.89% | +13.70% | -9.68% | -2.10% | +5.54% |
| P5 | train | +7.77% | +4.86% | +6.18% | +4.14% | -0.68% | +2.29% |
| P5 | validation | -0.68% | -9.39% | -9.57% | -5.84% | +0.64% | -1.70% |
| P5 | robustness | -0.93% | +4.52% | +5.36% | +1.92% | +1.00% | -2.49% |
| P6 | train | +6.52% | +1.56% | +2.48% | -8.08% | -0.14% | +2.90% |
| P6 | validation | -1.10% | +16.94% | +21.56% | -5.12% | -3.78% | -4.90% |
| P6 | robustness | +9.38% | +9.85% | +11.84% | -1.21% | -4.58% | +2.67% |
| P7 | train | -4.92% | +1.46% | +1.42% | -4.88% | +0.27% | -0.01% |
| P7 | validation | +0.52% | -9.59% | -8.93% | -2.94% | -1.13% | +1.25% |
| P7 | robustness | -1.42% | -0.08% | -0.07% | -3.96% | -0.76% | -1.47% |
| P8 | train | -6.85% | +20.98% | +18.86% | -5.79% | -4.57% | -8.53% |
| P8 | validation | -3.29% | +32.85% | +29.27% | +12.45% | -12.12% | -8.11% |
| P8 | robustness | +12.90% | +9.23% | +5.44% | +12.10% | -0.87% | +1.28% |

Insight：没有任何 proxy 在 train 与 robustness 同时表现为“右尾更强、payoff 不坏、failure 不升”。`P4/P6` 的右尾优势来自更强的趋势/修复结构，但它们也选择到了更多 false repair；`P3/P7` 有部分风险读数，但缺少稳定右尾收益；`P8` 不是 screen，而是几乎全覆盖的密度标签。

## Bootstrap 与 Top-K 稳定性

bootstrap 使用 instrument block 作为 primary acceptance；event block 作为 secondary sensitivity。下表为 acceptance-primary 的关键 failure 读数：

| proxy | train P(failure <= 0.5pp) | robustness P(failure <= 0.5pp) | train failure p95 | robustness failure p95 |
| --- | ---: | ---: | ---: | ---: |
| P1 | 0.764 | 0.052 | +3.32% | +9.62% |
| P2 | 0.152 | 0.006 | +11.18% | +15.95% |
| P3 | 0.394 | 0.999 | +9.54% | -5.48% |
| P4 | 0.015 | 0.001 | +19.41% | +16.88% |
| P5 | 0.184 | 0.208 | +12.53% | +12.54% |
| P6 | 0.395 | 0.010 | +10.55% | +16.71% |
| P7 | 0.405 | 0.593 | +7.99% | +5.06% |
| P8 | 0.076 | 0.255 | +37.99% | +28.87% |

acceptance 要求 failure delta 的 CI-aware hard veto 通过。除 `P3` robustness 外，大多数 proxy 的 train 或 robustness failure p95 明显偏高；这解释了为什么 evidence score 较高的 `P6` 仍不能支持。

top-k sensitivity 进一步显示部分 proxy 对少数 instrument/event 依赖较强。移除 top3 instrument 后：

| proxy | split | winner delta | median 60d delta | winsorized 60d delta | big failure delta |
| --- | --- | ---: | ---: | ---: | ---: |
| P1 | train | -1.10% | -1.49% | -1.32% | -1.08% |
| P1 | robustness | +4.57% | -3.49% | -1.95% | +5.18% |
| P2 | train | -3.30% | -3.13% | -4.08% | +4.61% |
| P2 | robustness | +5.88% | -4.09% | -2.44% | +10.27% |
| P3 | train | -4.25% | +0.20% | -1.38% | +1.68% |
| P3 | robustness | +0.11% | +0.25% | -0.81% | -10.52% |
| P4 | train | +1.78% | -2.25% | -2.14% | +12.31% |
| P4 | robustness | +9.50% | -2.28% | +2.45% | +11.25% |
| P5 | train | +4.79% | -2.06% | +0.06% | +2.99% |
| P5 | robustness | -2.37% | +0.92% | -3.29% | +4.52% |
| P6 | train | +1.94% | -0.23% | +0.14% | +3.77% |
| P6 | robustness | +6.11% | -4.96% | -2.68% | +10.03% |
| P7 | train | -4.54% | +0.83% | +0.26% | +0.88% |
| P7 | robustness | -0.75% | -0.76% | -0.49% | -0.20% |
| P8 | train | +2.84% | -3.61% | -1.09% | +18.85% |
| P8 | robustness | +12.00% | -2.56% | +0.45% | +9.24% |

Insight：top-k 稳定性没有为任何 proxy 提供反证支持。对最有右尾感的 `P4/P6`，移除 top names 后仍保留 failure uplift；对 `P1/P2`，payoff 方向仍弱。

## Multiple Comparison 与 Overlap

multiple-comparison audit 在同 coverage、同 split/time/source-family cell 内随机置换 proxy membership：

| 指标 | 数值 |
| --- | ---: |
| pre_registered_proxy_family_n | 8 |
| evaluated_proxy_family_n | 8 |
| null_simulation_n | 500 |
| null_expected_supported_proxy_n | 0.804 |
| null_supported_proxy_n_p95 | 2.0 |
| actual_supported_proxy_n | 0 |
| multiple_comparison_status | ok |

解释：在这个 gate 体系下，随机 proxy 平均也可能产生约 0.8 个 apparent supported；当前实际 supported 为 0，低于 null p95。也就是说，本轮不是“挑剔到所有东西都过不了但随机会过很多”的异常状态，而是预注册 proxy 在严格门槛下没有稳定支持。

proxy overlap 的高值：

| pair | intersection_n | union_n | jaccard |
| --- | ---: | ---: | ---: |
| P7_flow_confirmation / P8_recurrence_density | 3,256 | 4,637 | 0.702 |
| P1_gap_event / P7_flow_confirmation | 2,142 | 3,569 | 0.600 |
| P1_gap_event / P8_recurrence_density | 2,384 | 4,622 | 0.516 |
| P4_momentum_leader / P6_repair_structure | 304 | 1,063 | 0.286 |
| P4_momentum_leader / P7_flow_confirmation | 687 | 3,444 | 0.199 |

Insight：`P7/P8` 高 overlap 加上高 coverage，说明它们更像“市场活跃/事件密度背景变量”，不是清晰的 archetype screen。`P4/P6` overlap 中等，说明 momentum 与 repair structure 有共同部分，但二者都携带 false repair 风险。

## Rejected-Subpopulation Override Readout

该读数只用于诊断，不能推翻 10C。

| proxy | rejected proxy row_n | rejected winner_rate | rejected big_failure_rate | rejected 60d median return | rejected MFE120 median | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| P1 | 172 | 14.67% | 65.35% | -13.92% | 19.34% | powered diagnostic |
| P2 | 137 | 20.89% | 72.30% | -12.84% | 15.48% | powered diagnostic |
| P3 | 59 | 17.35% | 57.02% | -8.39% | 24.89% | underpowered |
| P4 | 218 | 14.85% | 68.55% | -15.56% | 17.34% | powered diagnostic |
| P5 | 27 | 24.48% | 75.52% | -5.44% | 19.72% | underpowered |
| P6 | 93 | 16.06% | 68.33% | -14.30% | 21.62% | underpowered |
| P7 | 276 | 14.18% | 68.89% | -14.28% | 15.58% | powered diagnostic |
| P8 | 370 | 16.00% | 70.25% | -13.78% | 17.07% | powered diagnostic |

Insight：rejected-subpopulation 里确实有 winner，但同时 big_failure_rate 极高，60d median return 普遍为负。MFE120 p95 可以很高，但这是 upper-bound path readout，不是可实现收益。这个读数支持“后续若要救回 winner，必须做策略层执行/风险控制”，不支持直接降低 10C rejector。

## Findings

1. **strict PIT 后结论更干净**
   旧口径下 PIT miss 会把 final status 压成 statistics_incomplete；新口径下 PIT-valid 分母本身完整，`screen_empty` 是 proxy 统计失败，不是数据完整性失败。

2. **当前 t0 proxy 更像风险/事件活跃度 proxy，而不是单独可用的 winner-protection screen**
   `P4/P6` 捕捉到了更强右尾，但 false repair 同步增加；`P3/P7` 风险更稳或更宽，但右尾/可比性不足；`P8` 几乎全覆盖，无法形成有效筛选。

3. **big winner archetype 不应直接转成单维 hard retention rule**
   当前证据显示，winner archetype 的可见 proxy 和失败暴露高度纠缠。后续如果继续，需要做组合式结构：先用 archetype proxy 捕捉右尾候选，再用 failure-suppressor 或 execution-aware replay 判断是否值得保留，而不是让单一 proxy 直接 override rejector。

4. **PIT universe 本身是重要的研究边界**
   被 strict PIT 排除的样本不是随机噪声。`before_first_pit_membership` 的 winner_120_rate 达 25.61%，说明入池前或非 PIT 状态包含大量 big winner 信息，但这些不属于当前可执行 universe。后续如果研究“早期入池前 winner”，必须作为单独实验，不应混入 11A1。

5. **11A1 不支持直接进入策略 EV，但支持下一步缩小问题**
   11A1 的主要价值是排除了“单 proxy 直接支持”的路径，并指出可继续研究的方向：`P4/P6` 可作为右尾候选源，但必须叠加 false-repair suppression；`P3` 可作为风险过滤背景变量；`P7/P8` 应降级为 context/coverage controls，而不是 screen。

## 建议

- 11B 不要把任何 11A1 proxy 当成 supported retention rule；应把 `P4/P6` 作为 diagnostic candidate，重点检查 rejector 对其 right-tail retention 是否存在系统性误杀。
- 11C 若继续策略回放，应采用 two-stage policy：第一阶段捕捉 `P4/P6` 右尾候选，第二阶段用 failure-suppression、可成交性、limit-up/limit-down、capacity 和 portfolio concentration 控制风险。
- 对 `P7/P8` 应重新定义：降低 coverage，或把它们作为 regime/context covariate，而不是 proxy-positive membership。
- 对 PIT excluded 的 `before_first_pit_membership` 单独建档；这类样本 winner rate 高，但不属于当前 PIT executable universe，不能用于本轮 supported 判定。

## 使用边界

- 11A1 不是买入信号，不计算策略 EV。
- 本轮结论只适用于 `risk_on ∩ PIT-valid` evaluated denominator，不外推到 `risk_off`、`transition`、非 PIT universe 或入池前样本。
- MFE/MAE 只作为路径读数；MFE 是 capturable upper bound，不是 realized return。
- rejected-subpopulation override readout 只允许作为诊断，不授权推翻 10C。
