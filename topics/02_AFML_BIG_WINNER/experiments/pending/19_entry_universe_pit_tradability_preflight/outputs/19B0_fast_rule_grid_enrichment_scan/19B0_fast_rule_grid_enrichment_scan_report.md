# 19B0 快速规则网格右尾富集扫描报告

## 1. 最终结论

19B0 的最终状态是：

```text
decision_state = 19B0_candidate_family_eligible_for_19B
next_allowed_requirement = requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md
N_family_brought_to_robustness = 2
N_tested_family_cell_pairs = 2
selected_residual_alpha_cell_pair_n = 0
selected_positive_beta_exposure_cell_pair_n = 2
```

进入 19B 的两个 family/cell 是：

| family | selected cell | selection track | promotion claim |
|---|---|---|---|
| B2_relative_strength_breakout | B2-relative-strength-breakout__182b3d0f30f5 | positive_beta_exposure | positive_beta_exposure_candidate |
| B5_recent_high_close_plus_amount_expansion | B5-recent-high-close-plus-amount-expansion__25d72c708fc1 | positive_beta_exposure | positive_beta_exposure_candidate |

核心判断：

- B2 是本轮最清晰的右尾暴露水库。候选分母 4,061，`+50/120d` 命中 930，命中率 22.901%，高于同口径 broad baseline 的 16.253%，绝对提升 6.648 pct。
- B5 是弱很多的第二候选。候选分母 6,503，`+50/120d` 命中 1,319，命中率 20.283%，绝对提升 4.030 pct；但 matched-baseline conservative adjusted lift 为负，说明它更像趋势/流动性状态暴露，而不是可归因 alpha。
- 本轮没有 residual-alpha candidate。所有 baseline matching quality 都失败，因此不能把 train lift 解释为独立 alpha、规则筛选力或可交易 entry policy。
- 19B0 只授权进入 19B 做 robustness / false-positive burden readout；不授权 19C replay、EP20 policy preflight、模型训练、回测、生产信号或交易。

## 2. Train-only 和授权边界

本轮只读取 train outcome：

| item | value |
|---|---|
| validation outcome read | false |
| robustness outcome used for selection | false |
| model training authorized | false |
| entry / exit / holding policy authorized | false |
| portfolio backtest authorized | false |
| model deployment / production signal / live trading authorized | false |

所有 contract gate 均为 `pass`，但这里有一个容易误读的点：`baseline_matching_quality_audit_gate=pass` 只表示质量审计已生成并进入决策流程，不表示 matched baseline 质量通过。实际 489 条 baseline-family-cell 质量行的 `baseline_matching_quality_gate` 全部为 `fail`，所以 residual-alpha 归因被关闭。

## 3. 数据分母和标签锚点

19B0 使用 `executable_next_open_anchored` 标签，核心标签为：

```text
forward_big_winner_120d = max(high[entry_open:entry_open+120d]) / executable_next_open - 1 >= 0.50
```

EP07 ready-made `event_anchored` label 只作为 diagnostic，不进入 primary metric 或 selection。

| audit item | value |
|---|---:|
| EP07 train candidate rows | 7,328 |
| executable entry anchor available | 7,328 |
| executable path complete 20/30/60/120d rate | 100.000% |
| event-anchored diagnostic available rows | 7,320 |
| event-anchored vs executable `+50/120d` match rate | 99.918% |
| ready-made label used for primary / selection | false / false |

baseline eligible universe 是本轮所有 positive exposure 判断的 broad denominator：

| stage | rows | instruments | months | matching fields available | cooldown eligible | frozen before label |
|---|---:|---:|---:|---:|---:|---|
| raw_train_universe | 607,536 | 1,407 | 60 | 88.089% | 9.485% | true |
| cooldown_eligible_under_19a_rule | 57,623 | 1,407 | 60 | 86.500% | 100.000% | true |
| matching_fields_available | 535,171 | 1,103 | 57 | 100.000% | 9.314% | true |
| pre_label_baseline_eligible_candidate | 40,552 | 999 | 49 | 100.000% | 100.000% | true |
| baseline_eligible | 40,552 | 999 | 49 | 100.000% | 100.000% | true |

同口径 broad baseline 的 `+50/120d` base rate 为 16.253%，对应 6,591 个 positive rows。B2/B5 的 positive exposure 结论都必须相对这个分母理解，而不是相对原始 607,536 行 train universe 理解。

## 4. Family 和 Grid 物化

B3 `industry_or_theme_breadth_expansion` 未进入本轮扫描，因为没有 genuine PIT industry source。其余 family 的物化情况如下：

| family | declared cells | materialized cells | missing cells | dependent feature missing | status |
|---|---:|---:|---:|---:|---|
| B1_near_120d_high_plus_volume_expansion | 36 | 36 | 0 | 0 | materialized_before_label_readout |
| B2_relative_strength_breakout | 36 | 36 | 0 | 0 | materialized_before_label_readout |
| B4_volatility_contraction_then_breakout | 36 | 36 | 0 | 0 | materialized_before_label_readout |
| B5_recent_high_close_plus_amount_expansion | 36 | 36 | 0 | 0 | materialized_before_label_readout |
| B6_low_drawdown_reclaim_or_ema_reclaim | 36 | 18 | 18 | 18 | materialized_before_label_readout |
| EP07_topn_multichannel_recommended_union | 1 | 1 | 0 | 0 | materialized_before_label_readout |

解释：

- B1/B2/B4/B5 完整物化，说明本轮不是因为候选规则无法生成而通过 B2/B5。
- B6 只有 18/36 个 cell 进入 readout，缺失来自 `early_no_false_repair_10d_required=true` 分支；该特征只能 EP07-direct 使用，不能在全 baseline eligible universe 上重建。
- 实际 metric/baseline readout 覆盖 163 个 materialized cells 和 489 个 baseline-family-cell rows。
- registry、matching bucket、membership 都在 label readout 前冻结，当前输出没有 label leakage 证据。

## 5. Baseline Matching Quality

三类 same-budget baseline 都成功物化，但质量全部失败：

| baseline family | rows | pass_n | median unmatched | max unmatched | median max SMD | max SMD | median month delta | median instrument delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calendar_time_random_same_budget | 163 | 0 | 12.869% | 24.234% | 0.803 | 1.275 | 2.331% | 0.327% |
| instrument_matched_random_same_budget | 163 | 0 | 2.410% | 5.590% | 0.897 | 1.246 | 3.558% | 0.077% |
| liquidity_size_volatility_matched_same_budget | 163 | 0 | 29.594% | 36.527% | 0.374 | 0.731 | 2.331% | 0.255% |

质量失败来源：

| rule | threshold | fail_n / rows | interpretation |
|---|---:|---:|---|
| unmatched_candidate_rate | > 5% | 329 / 489 | common support 不足，尤其 LSV arm |
| baseline_reuse_rate | > 20% | 17 / 489 | 不是主问题，但 LSV 尾部有复用压力 |
| max_standardized_mean_difference_after_matching | > 0.10 | 488 / 489 | 主要阻断项，covariate balance 基本未达标 |
| decision_month_coverage_delta | > 2% | 432 / 489 | 时间覆盖仍有偏差 |
| instrument_coverage_delta | > 5% | 0 / 489 | instrument 覆盖不是本轮主问题 |

洞察：

- `instrument_matched` 能把 unmatched rate 压低，但 SMD 和 month delta 仍差，说明只按股票匹配不能消除强势状态暴露。
- `liquidity_size_volatility_matched` 的 SMD 明显更低，方向更接近正确控制，但 unmatched rate 高，说明 candidate cell 的 common support 变窄。
- 因为所有 quality row 均 fail，19B0 只能选择 positive beta/exposure candidate，不能发出 residual-alpha claim。

## 6. Family 排序和选择

Family-level selection audit：

| family | materialized cells | best positive exposure score | best residual adjusted lift | status | selected for 19B | reason |
|---|---:|---:|---:|---|---|---|
| B2_relative_strength_breakout | 36 | 0.033969 | 0.000592 | selected_for_19B | true | positive exposure 最强，且唯一 train triage pass |
| B5_recent_high_close_plus_amount_expansion | 36 | 0.007791 | -0.070336 | selected_for_19B | true | positive exposure 通过，但 matched-baseline adjusted 不足 |
| EP07_topn_multichannel_recommended_union | 1 | -0.028698 | -0.094090 | train_diagnostic_only | false | no_cell_met_residual_or_positive_exposure_selection_condition |
| B6_low_drawdown_reclaim_or_ema_reclaim | 18 | -0.011956 | -0.100883 | train_diagnostic_only | false | no_cell_met_residual_or_positive_exposure_selection_condition |
| B1_near_120d_high_plus_volume_expansion | 36 | -0.019209 | -0.105794 | train_diagnostic_only | false | no_cell_met_residual_or_positive_exposure_selection_condition |
| B4_volatility_contraction_then_breakout | 36 | -0.069996 | -0.309239 | no_cell_passed | false | no_cell_met_residual_or_positive_exposure_selection_condition |

Family distribution 支持这个排序：

| family | cells | median candidate_n | median p50 | max p50 | median positive score | max positive score | positive-pass cells | residual-pass cells |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B2_relative_strength_breakout | 36 | 5,801 | 21.628% | 22.901% | 0.021238 | 0.033969 | 32 | 0 |
| B5_recent_high_close_plus_amount_expansion | 36 | 5,319 | 18.566% | 20.283% | -0.009381 | 0.007791 | 10 | 0 |
| B6_low_drawdown_reclaim_or_ema_reclaim | 18 | 21,120 | 17.181% | 18.308% | -0.023229 | -0.011956 | 0 | 0 |
| EP07_topn_multichannel_recommended_union | 1 | 5,116 | 16.634% | 16.634% | -0.028698 | -0.028698 | 0 | 0 |
| B1_near_120d_high_plus_volume_expansion | 36 | 4,438 | 16.443% | 17.583% | -0.030613 | -0.019209 | 0 | 0 |
| B4_volatility_contraction_then_breakout | 36 | 7,664 | 10.425% | 12.504% | -0.090788 | -0.069996 | 0 | 0 |

解释：

- B2 不是单个偶然 cell：36 个 cell 中 32 个 positive exposure pass，family 中位 p50 达 21.628%，显著高于 broad baseline 16.253%。
- B5 有 10 个 positive exposure pass，但 family 中位 positive score 为负，说明只有部分强 trend/amount 参数组合有右尾富集。
- B1、B6、EP07 接近 broad baseline 或略高，但没有跨过 positive exposure margin；B4 整体低于 broad baseline，不应作为 19B 主候选。

## 7. Selected Cell 明细

两个 selected cells 的参数和核心 readout：

| family | selected parameter | primary_n | p_candidate_50 | broad base | delta | ratio | positive margin | positive score | conservative lift | adjusted lift | train triage pass |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| B2_relative_strength_breakout | `stock_vs_market_20d>=0.15; return_60d_rank_pct>=0.90; close_to_ema60>=0.00; market_regime=all` | 4,061 | 22.901% | 16.253% | 6.648 pct | 1.409 | 3.251 pct | 3.397 pct | 1.1006 | 0.0006 | true |
| B5_recent_high_close_plus_amount_expansion | `return_10d>=0.10; close_position_120d>=0.70; amount_ratio_20d>=1.20; quality_amount=false_or_missing_allowed` | 6,503 | 20.283% | 16.253% | 4.030 pct | 1.248 | 3.251 pct | 0.779 pct | 1.0297 | -0.0703 | false |

B2 的结论更强：

- 它同时通过 positive exposure train pass 和 train triage pass。
- conservative lift 刚刚高于 1.10，adjusted lift 只有 0.0006，余量很薄。
- 这意味着 B2 有进入 19B 的价值，但 19B 必须重点验证这个边际优势是否在 robustness split、false-positive burden 和 baseline repair 下保持。

B5 的结论更弱：

- 它通过的是 broad-baseline positive exposure，不是 matched-baseline train triage。
- conservative lift 只有 1.0297，adjusted lift 为 -0.0703。
- B5 可以作为 19B 的弱候选或对照型趋势状态，但不应在报告语言里被写成“稳定 alpha”。

## 8. Selected Cell 的 Baseline Arm 明细

| family | baseline | p_matched_50 | lift | adjusted lift | arm triage pass | unmatched | max SMD | quality gate |
|---|---|---:|---:|---:|---|---:|---:|---|
| B2 | calendar_time_random_same_budget | 16.326% | 1.4027 | 0.2873 | true | 11.204% | 1.186 | fail |
| B2 | instrument_matched_random_same_budget | 20.808% | 1.1006 | 0.0006 | true | 5.590% | 1.108 | fail |
| B2 | liquidity_size_volatility_matched_same_budget | 20.044% | 1.1425 | 0.0425 | true | 32.258% | 0.593 | fail |
| B5 | calendar_time_random_same_budget | 15.870% | 1.2781 | 0.1781 | true | 7.289% | 0.899 | fail |
| B5 | instrument_matched_random_same_budget | 19.007% | 1.0672 | -0.0328 | false | 2.876% | 0.929 | fail |
| B5 | liquidity_size_volatility_matched_same_budget | 19.699% | 1.0297 | -0.0703 | false | 27.449% | 0.389 | fail |

这张表解释了为什么 B2/B5 都只能是 positive exposure candidate：

- B2 在三个 baseline arm 上的 lift 都为正，但质量 fail 全部来自匹配平衡不足；它最像“高动量/高横截面排名状态”的右尾暴露。
- B5 只有 calendar arm 的 triage pass 较强，instrument 和 LSV arm 都不足；它的 right-tail readout 对 baseline 定义更敏感。
- LSV arm 对两者的 SMD 更低，但 unmatched 很高，显示 common support 是下一轮需要解决的结构性问题。

## 9. Sensitivity 和风险读数

Sensitivity 指标全部是 diagnostic-only，不参与 selection 和授权。

| family | 20d p50 | 30d p50 | 60d p50 | 120d p50 | fast fail | MAE20 p10 | MFE120 p90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| B2 selected cell | 4.260% | 6.575% | 12.903% | 22.901% | 55.799% | -24.461% | 78.553% |
| B5 selected cell | 3.552% | 5.628% | 11.672% | 20.283% | 48.408% | -22.844% | 73.694% |

Tail lift 随 horizon 拉长后的 baseline-arm 读数：

| family | baseline | lift 20d | lift 30d | lift 60d | lift 120d |
|---|---|---:|---:|---:|---:|
| B2 | calendar | 3.7609 | 2.2437 | 1.7467 | 1.4027 |
| B2 | instrument | 2.0353 | 1.6584 | 1.2243 | 1.1006 |
| B2 | LSV | 1.6019 | 1.4278 | 1.1802 | 1.1425 |
| B5 | calendar | 2.2000 | 1.8300 | 1.5060 | 1.2781 |
| B5 | instrument | 2.3814 | 1.7596 | 1.2735 | 1.0672 |
| B5 | LSV | 1.3916 | 1.2323 | 1.1211 | 1.0297 |

洞察：

- 两个 selected cells 在 20d/30d 的短 horizon lift 更高，120d lift 明显收敛，说明它们更像强趋势状态下的右尾机会池，而不是长期稳定的独立 alpha。
- fast fail 接近 48%-56%，且 MAE20 p10 接近 -23% 到 -24%，提示候选集合内存在很重的早期反向风险；19B 必须同时读 false-positive burden，不能只看 `+50` 命中。
- B2 的 120d lift 在 LSV arm 下仍有 1.1425，而 B5 只剩 1.0297；这进一步支持“B2 是主候选，B5 是弱候选/对照”的解释。

## 10. Instrument Concentration

| family | max candidate share | max winner share | top1 removed lift range | top3 removed lift range | top1/top3 pass pattern |
|---|---:|---:|---:|---:|---|
| B2 selected cell | 0.566% | 1.183% | 1.0961 - 1.3971 | 1.0966 - 1.3976 | all arms pass |
| B5 selected cell | 0.431% | 0.910% | 1.0247 - 1.2720 | 1.0213 - 1.2677 | only calendar arm pass |

解释：

- B2/B5 的 winner share 都低于 1.2%，没有明显由单一股票驱动的集中度问题。
- B2 移除 top1/top3 instrument 后仍在三个 baseline arm 上保留 pass pattern，说明不是单票贡献。
- B5 移除 top instruments 后在 instrument/LSV arm 仍不通过，进一步说明它的优势更薄。

## 11. 研究洞察

第一，当前 `+50/120d` 右尾标签最偏好的不是泛化的近高点或放量，而是相对强势和横截面强势。B2 的 selected cell 要求 `stock_vs_market_20d >= 0.15` 且 `return_60d_rank_pct >= 0.90`，并且不需要 `risk_on` 过滤；这说明右尾富集主要来自个股相对市场的强势状态，而不是只来自大盘环境。

第二，B5 的“近期高位收盘 + 10d 强涨 + 成交额扩张”确实有 positive exposure，但它对 baseline arm 很敏感。它可以作为 B2 的趋势确认或替代 exposure family 进入 19B，但不应承担独立发现的主结论。

第三，baseline repair 的优先级非常明确：不是先修 instrument coverage，也不是先修 baseline reuse，而是同时修 `max_SMD` 与 `unmatched_candidate_rate`。LSV arm 证明状态匹配方向有效，但 common support 代价过高；instrument arm 证明支持域好，但状态平衡不够。

第四，B1/B4/B6/EP07 当前更适合作为 diagnostic。B4 的 p50 family distribution 明显低于 broad baseline，B1/B6/EP07 也没有跨过 positive exposure margin；若后续继续投入，应先有新的经济假设或 feature 变体，而不是直接扩大 19B robustness 预算。

第五，即使 19B 证明 B2/B5 的 exposure persistence，只要 matched-baseline residual pass 仍不存在，EP19 的最高终态仍只能是：

```text
19_entry_universe_enrichment_only_diagnostic
```

这意味着它可以告诉我们“哪里更容易出现右尾机会”，但不能直接变成交易策略、entry policy 或 EP20 preflight 输入。

## 12. 19B Handoff

Search accounting：

| item | value |
|---|---|
| N_supported_primary_family | 6 |
| N_materialized_family | 6 |
| N_family_brought_to_robustness | 2 |
| N_tested_family_cell_pairs | 2 |
| N_residual_alpha_candidate_pairs | 0 |
| N_positive_beta_exposure_candidate_pairs | 2 |
| residual_alpha_correction_scope | `0 * primary_tail_lift_50` |
| positive_beta_exposure_correction_scope | `2 * positive_exposure_score_50` |
| track_correction_scope_policy | `separate_by_promotion_claim_type` |
| family_level_correction | `Bonferroni-Sidak` |
| cell_level_accounting | `all_tried_cells_counted` |

19B 应该重点回答三件事：

1. B2 的 3.397 pct positive exposure score 是否在 robustness split 上仍成立。
2. B5 的弱 positive exposure 是否只是 train-only 状态偏差，还是有稳定右尾机会池价值。
3. baseline repair 后，B2/B5 是否仍只表现为 beta/exposure，还是能出现可防御的 residual-alpha readout。

Final authorization：

- 允许进入 `requirement_19b_robust_right_tail_enrichment_and_false_positive_burden_readout.md`。
- 不允许 19C replay。
- 不允许 EP20 policy preflight。
- 不允许模型、entry/exit/holding policy、组合回测、生产信号或交易。
