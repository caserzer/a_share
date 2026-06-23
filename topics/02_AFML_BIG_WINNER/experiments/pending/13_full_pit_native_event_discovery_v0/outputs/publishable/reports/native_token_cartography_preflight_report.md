# 13A Full-PIT Native Token Cartography Preflight Report

## 裁决

| field | value |
|---|---|
| decision_state | `13A_no_native_token_survives_stop_event_mining` |
| next_allowed_requirement | `none` |
| selected_token_id | `volatility_20d__bottom_20pct` |
| selected_token_family_id | `volatility_range` |
| sequence_mining_authorized | `False` |
| decision_reason | `train_candidate_absent_or_validation_robustness_search_failed` |

结论先行：13A 不是因为输入、lineage、native universe 或 label portability 不可用而停止；这些 gate 都通过了。真正的停止原因是：train 里最强的 len-1 token 虽然有很强 winner uplift，但 validation / robustness matched control 不足，bad-side 同步放大，utility 与 deployability 全部失败，并且该 token 高度贴近 broad morphology。当前不授权 13B sequence mining。

13A 的实质发现是：full-PIT native universe 上确实存在可重复的低波动 / 区间压缩 winner enrichment，但它更像一个宽口径路径形态读数，不是可直接部署的 native event token。

## Gate 总览

| gate | status | 关键解释 |
|---|---|---|
| input_gate_status | `pass` | 必需输入存在，schema / read audit 通过 |
| upstream_lineage_gate_status | `pass` | 12A7g selected label lineage 可证明 |
| native_universe_gate_status | `pass` | full-PIT native opportunity universe 可构造 |
| label_portability_gate_status | `pass` | label base-rate dispersion = 0.0968，低于 0.10 上限 |
| winner_uplift_gate_status | `fail` | selected token readout 过线，但 validation / robustness control quality = `insufficient_control` |
| search_control_gate_status | `pass` | effective_search_space_n = 368640 后 deflated AUC 仍过线 |
| badside_gate_status | `fail` | fast-fail / lower-first uplift 在三段均显著为正，utility per entry 均为负 |
| stability_gate_status | `fail` | 当前 runner 按绝对 60% board concentration 规则标 fail；该规则与 400/100 原始 universe 先验不匹配，应解释为 gate 设计 caveat |
| deployability_gate_status | `fail` | 捕获正例多，但 total indexed utility 三段均为负 |
| morphology independent evidence | `fail` | `morphology_rediscovery_suspect`，且 utility margin 未给出独立证据 |

注意：`native_token_cartography_readout.csv` 的 `metric_status=pass` 只表示单个 readout 的方向、AUC、lift 过线；最终 `winner_uplift_gate_status` 还要求 validation / robustness control 不为 `insufficient_control`。selected token 在后两段未满足这一点，所以不能被授权。

## 1. 输入、Lineage 与 Cache 证明

13A 使用 12A7g 已冻结的 vol-scaled winner label：

```text
selected_label_id = vol20d_kup2p0_kdn1p0_H20
vol_reference_unit = daily_return_std
k_up = 2.0
k_dn = 1.0
horizon_sessions = 20
same_bar_priority = lower_first
```

Cache audit 通过：

| field | value |
|---|---:|
| cache_used | `True` |
| overall compared field-row cells | 6899824 |
| mismatch_n | 0 |
| mismatch_rate | 0.0000 |
| mismatch_status | `pass` |

这说明本轮没有重新发明 label，也没有从报告文本反推 label。13A 读入的 cache 与逐字段重算结果一致；这只是 lineage 证明，不是 alpha 证据。

## 2. Native Opportunity Universe

13A 构造的是 C0-free full-PIT native opportunity universe，不使用 C0 active band，也不修复 `volatility_reconciliation_fail`。

| split | native_denominator_n | instrument_n | not_evaluable_row_n | not_evaluable_share | missing_regime_bypassed_row_n |
|---|---:|---:|---:|---:|---:|
| all | 408715 | 1449 | 22524 | 5.22% | 0 |
| train | 216794 | 1119 | 15846 | 6.81% | 0 |
| validation | 61307 | 766 | 2220 | 3.49% | 0 |
| robustness | 130614 | 769 | 4458 | 3.30% | 0 |

冻结阈值只从 train 计算，且 `outcome_used_for_freeze=False`：

| threshold_id | feature_id | threshold_value | quantile/source | note |
|---|---|---:|---|---|
| basic_liquidity_floor | `money_median_20d` | 41820824.20 | train p05 | 使用成交额中位数作为流动性 floor |
| trading_continuity_floor | `trading_continuity_20d` | 0.950000 | fixed | 20 日可交易连续性要求 |
| volatility_sanity_floor | `volatility_20d` | 0.005883 | train p01 | 剔除过低 native volatility |
| volatility_sanity_cap | `volatility_20d` | 0.061365 | train p99 | 剔除过高 native volatility |

阈值邻域敏感性全部通过：

| variant | retained_row_n | retained_row_share_delta | winner_base_rate_delta | board_mix_max_abs_delta | year_mix_max_abs_delta | status |
|---|---:|---:|---:|---:|---:|---|
| base | 408715 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | pass |
| loose_liquidity_p02 | 416684 | 0.0195 | 0.0015 | 0.0008 | 0.0042 | pass |
| strict_liquidity_p10 | 394509 | -0.0348 | -0.0025 | 0.0006 | 0.0075 | pass |
| strict_continuity_100 | 408715 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | pass |
| strict_vol_p02_p98 | 400407 | -0.0203 | -0.0003 | 0.0009 | 0.0021 | pass |

解读：universe freeze 本身没有制造不稳定 denominator。后续停止不是 universe construction failure。

## 3. Label Portability

| split | denominator_n | winner_positive_n | winner_base_rate | fast_fail_rate | same_bar_conflict_rate | label_status |
|---|---:|---:|---:|---:|---:|---|
| all | 408715 | 55166 | 13.50% | 32.88% | 0.00% | pass |
| train | 216794 | 31474 | 14.52% | 34.46% | 0.00% | pass |
| validation | 61307 | 5880 | 9.59% | 39.93% | 0.00% | pass |
| robustness | 130614 | 17812 | 13.64% | 26.96% | 0.00% | pass |

`label_base_rate_dispersion = 0.0968`，刚好在预注册 `0.10` 上限内。label 可以迁移到 native universe，但它不是低风险标签：全样本 fast-fail baseline 已有 32.88%，validation 更高到 39.93%。因此，任何 token 不能只看 winner uplift，必须同时证明 lower-first / fast-fail 没有被同步放大。

## 4. Len-1 Token Cartography

20 个 primitive 全部可用，共生成 80 个 len-1 token：

| family_id | primitive_n | token_n | best_train_auc | best_train_diff |
|---|---:|---:|---:|---:|
| breakout_trend | 5 | 20 | 0.5889 | 0.0567 |
| liquidity_attention | 3 | 12 | 0.5729 | 0.0606 |
| relative_strength | 2 | 8 | 0.5463 | 0.0092 |
| reversal_drawdown | 3 | 12 | 0.6008 | 0.0695 |
| volatility_range | 7 | 28 | 0.6325 | 0.1024 |

Gate attrition 更能说明问题：

| stage | token_count | insight |
|---|---:|---|
| candidate len-1 tokens | 80 | 5 个 family，20 个 primitive，4 个 quantile rules |
| readout metric pass all splits | 26 | 方向、AUC、top lift 过线的 token 不少 |
| readout pass 且三段 control 不为 insufficient | 15 | 一部分 token 仍有 matched-control 可比性 |
| badside pass all splits | 0 | 没有 token 能证明 lower-first / utility 过关 |
| deployability pass all splits | 0 | 没有 token 能形成可部署 frontier |

所以 13A 不是没有发现统计相关性；它发现的是“相关性大多伴随 bad-side 或不可部署性”。

Search-control audit：

| field | value |
|---|---:|
| token_grid_size | 80 |
| family_grid_size | 5 |
| token_threshold_candidate_n | 4 |
| orientation_candidate_n | 2 |
| universe_floor_cap_candidate_n | 144 |
| match_coarsening_policy_n | 4 |
| effective_search_space_n | 368640 |
| effective_search_space_n_outcome_free_adjusted | 640 |
| selected_token_rank_train | 34 |
| fdr_q_value | 0.0000 |
| deflated_auc_validation | 0.640016 |
| search_control_status | pass |

这里的 search pass 只能说明“多重搜索折扣后 AUC 仍非随机噪声”。它不能覆盖 bad-side、stability、deployability 或 morphology 独立证据。

## 5. Selected Token：低 20 日波动压缩

selected token 定义：

| field | value |
|---|---|
| token_id | `volatility_20d__bottom_20pct` |
| family_id | `volatility_range` |
| primitive_id | `volatility_20d` |
| threshold_rule | `bottom_20pct` |
| threshold_value | 0.016023 |
| comparator | `<=` |
| available_at | `reference_date_close` |
| future_data_used | `False` |

它是 train 中按 winner diff / AUC 看的最强 token：

| split | treated_n | control_n | treated_winner_rate | control_winner_rate | diff | auc | top_decile_lift | control_quality |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| train | 43359 | 154019 | 23.01% | 12.77% | 10.24pp | 0.6325 | 8.75pp | coarsened_caveat |
| validation | 21170 | 40137 | 14.98% | 6.75% | 8.23pp | 0.6415 | 9.54pp | insufficient_control |
| robustness | 46770 | 83844 | 19.61% | 10.31% | 9.30pp | 0.6317 | 10.39pp | insufficient_control |

但 matched-control design 暴露了关键问题：

| split | coarsening_level | effective_control_ratio | matched_block_n | max_standardized_diff_after_match | match_status | control_quality |
|---|---|---:|---:|---:|---|---|
| train | level_0 | 3.55 | 482 | 2.4058 | pass | coarsened_caveat |
| validation | level_3 | 1.90 | 4 | 2.2424 | fail | insufficient_control |
| robustness | level_3 | 1.79 | 4 | 2.2331 | fail | insufficient_control |

validation / robustness 只能退到 `year + board + regime` 的 level_3 粗匹配，且 control ratio 低于 3。这个 token 的 uplift 读数很强，但不能被解释为充分可比 matched-control 下的独立事件效应。

## 6. Bad-side / Utility Veto

selected token 的上行命中率确实高，但下行先触发率也同步更高：

| split | upper_first_rate | treated_lower_first_rate | control_lower_first_rate | lower_first_uplift | median_upper_barrier_return | median_abs_lower_barrier_return | utility_per_entry | utility_status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| train | 23.01% | 43.03% | 32.38% | 10.66pp | 11.21% | 5.61% | -0.008323 | utility_fail |
| validation | 14.98% | 48.19% | 35.57% | 12.62pp | 11.06% | 5.53% | -0.020081 | utility_fail |
| robustness | 19.61% | 34.49% | 22.76% | 11.73pp | 10.75% | 5.37% | -0.007464 | utility_fail |

`same_bar_conflict_rate = 0`，所以这里不是同一根 bar 的 tie-handling 噪声；是 lower-first 本身被放大。经济含义很直接：低波动压缩 token 同时提高了“先上破”和“先下破”的概率，但 bad-side 增量更伤 utility。即使 winner readout 很漂亮，utility gate 仍必须 fail。

## 7. Morphology Collinearity

selected token 被标记为：

```text
morphology_flag = morphology_rediscovery_suspect
max_abs_rank_corr_with_reversal_anchor = 1.0
morphology_suspect_independent_evidence_status = fail
```

| split | selected_auc | broad_morphology_baseline_auc | auc_margin | broad_utility_total | utility_margin_vs_broad | independent_status |
|---|---:|---:|---:|---:|---:|---|
| train | 0.6325 | 0.6008 | 0.0318 | -0.000754 | -0.000910 | fail |
| validation | 0.6415 | 0.5904 | 0.0511 | -0.000766 | -0.006168 | fail |
| robustness | 0.6317 | 0.6221 | 0.0096 | 0.000358 | -0.003031 | fail |

相关结构也符合“broad morphology 重新发现”的担忧：

| anchor | train rank_corr | validation rank_corr | robustness rank_corr |
|---|---:|---:|---:|
| max_drawdown_20d | -0.5883 | -0.5450 | -0.6557 |
| distance_to_20d_low | 0.5570 | 0.5019 | 0.5903 |
| rebound_from_20d_low | 0.5570 | 0.5019 | 0.5903 |
| ret_20d | 0.2935 | 0.2407 | 0.3635 |
| volatility_20d | 1.0000 | 1.0000 | 1.0000 |

低波动 token 对 broad morphology baseline 的 AUC margin 在 train / validation 为正，但 utility margin 三段全为负。它更像“宽口径路径压缩 + drawdown/reversal 形态”的重新切片，而不是一个能独立授权 sequence mining 的 native event。

## 8. Stability

年度切片方向一致，8 个 calendar year 的 winner diff 全部为正：

| year | treated_n | control_n | diff | bootstrap_ci_low | status |
|---:|---:|---:|---:|---:|---|
| 2018 | 2420 | 5538 | 7.18pp | 5.18pp | pass |
| 2019 | 12958 | 38033 | 10.02pp | 8.02pp | pass |
| 2020 | 15107 | 66318 | 12.96pp | 10.96pp | pass |
| 2021 | 12874 | 63546 | 9.65pp | 7.65pp | pass |
| 2022 | 5544 | 17675 | 2.77pp | 0.77pp | pass |
| 2023 | 15626 | 22462 | 9.42pp | 7.42pp | pass |
| 2024 | 12737 | 40921 | 9.19pp | 7.19pp | pass |
| 2025 | 34033 | 42923 | 7.01pp | 5.01pp | pass |

当前 runner 的 `stability_gate_status = fail` 来自一个不合适的绝对 board concentration 规则：要求 supported token 的单一 board treated share 不超过 60%。这个规则不适合本轮 universe，因为原始 PIT universe 本来就是按主板前 400、创业板前 100 构造，native denominator 的 board mix 天然接近 80/20。

| board_bucket | native_row_share | treated_n | treated_share | control_n | control_share | treated_minus_native | treated_minus_control | diff | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| chinext | 19.11% | 7011 | 6.30% | 71108 | 23.91% | -12.81pp | -17.61pp | 10.51pp | pass |
| main_board | 80.89% | 104288 | 93.70% | 226308 | 76.09% | 12.81pp | 17.61pp | 9.17pp | pass |

正确解释应当是：selected token 相对 native baseline 和 control 都有主板偏移，属于 `board_mix_drift_caveat`；但不能因为 main_board share > 60% 就硬判为实质 stability failure。更合理的 gate 应改为相对 drift，例如比较 treated board share 与 native denominator / matched control board share 的差值，并预注册容差，而不是使用 60% 绝对上限。

此外，market regime 切片只有 `risk_on`，所以本轮仍没有提供跨 regime 的独立稳定性证据。也就是说，stability 的有效 caveat 是“board mix 相对偏主板 + regime 覆盖不足”，不是“单一 board 超过 60%”本身。

## 9. Deployability

| split | coverage_share | captured_positive_n | captured_positive_share | winner_rate | lift_vs_native_baseline | utility_total_indexed | deployability_status |
|---|---:|---:|---:|---:|---:|---:|---|
| train | 20.00% | 9978 | 31.70% | 23.01% | 8.49pp | -0.001665 | fail |
| validation | 34.53% | 3171 | 53.93% | 14.98% | 5.39pp | -0.006934 | fail |
| robustness | 35.81% | 9170 | 51.48% | 19.61% | 5.97pp | -0.002673 | fail |

这个 token 捕获了很多 positive，尤其 validation / robustness 中 captured positive share 超过 50%。但 coverage 也高达 34%-36%，说明它不是稀疏事件触发器，而是宽口径状态过滤器。更重要的是，total indexed utility 三段均为负，所以“捕获正例多”不能转化为可部署收益。

## 10. Findings 与 Insight

1. 13A 证明 full-PIT native route 可以运行。输入、lineage、cache、universe freeze、label portability 和 search-control 都可审计通过；当前停止不是工程数据链路 block。

2. native token 空间确实有 winner enrichment，且最强读数来自低波动 / range compression。`volatility_20d__bottom_20pct` 在 train 的 winner rate 为 23.01%，对照 control 12.77%，AUC 0.6325；validation / robustness AUC 也在 0.63-0.64。

3. 这个 enrichment 不能直接解释成“好事件”。同一 token 把 lower-first rate 从 control 的 35.57% 拉到 validation 的 48.19%，从 robustness 的 22.76% 拉到 34.49%。winner 和 fast-fail 是同一压缩形态的两面，不能只拿右尾读数进入 sequence mining。

4. search-control pass 不等于 deployability pass。FDR / deflated AUC 只回答“这不是简单的多重检验噪声”；它不回答 matched-control 可比性、bad-side、utility、板块集中或形态独立性。

5. selected token 更像 broad morphology 的低波动切片，而不是新的 native event family。它相对 broad morphology baseline 有 AUC margin，但 utility margin 三段全负，因此不能用“比 broad morphology AUC 高一点”来授权 13B。

6. 如果 Episode 13 继续，下一步不应直接写 13B sequence mining。更合理的是先做新的 13A 后续需求：扩展或重构 native token primitive，让候选 token 在 bad-side、control quality、board-mix relative drift、regime coverage 和 utility 上先过关，再谈 sequence。同时应修正 stability gate：从“单一 board 不超过 60%”改为“相对 native/control board mix 的漂移不超过预注册容差”。

## 结论

当前 13A 的正式裁决保持：

```text
decision_state = 13A_no_native_token_survives_stop_event_mining
sequence_mining_authorized = False
next_allowed_requirement = none
```

本轮最重要的研究结论不是“没有任何信号”，而是“full-PIT native 中最强 len-1 信号仍然是宽口径低波动 / 压缩形态；它能提高 winner 命中，但同时放大 lower-first，且不能通过 control、stability、morphology independent evidence 与 deployability gate”。因此，13B 不应基于当前 selected token 启动。
