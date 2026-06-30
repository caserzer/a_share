# 17B Oracle Ladder Replay Report

## 1. 决策结论

```text
decision_state = EP17B_oracle_ladder_ready_for_robustness
next_allowed_requirement = requirement_17c_oracle_robustness_stress.md
primary_positive_oracle_id = O5
primary_positive_oracle_variant_id = O5_perfect_utility_primary
blocking_reason = none
```

17B 的结论是：在当前 frozen denominator、frozen action semantics、50bps round-trip cost、`q_defend = 0.00` 的 primary gate 下，oracle action space 存在正的上界收益，因此只授权进入 EP17C robustness stress。17B 不授权 entry、exit、holding、sizing、portfolio backtest、model deployment、production signal 或 live trading。

最关键的研究含义不是“可以交易”，而是“继续/防御这个动作空间本身还有可测 headroom”。如果连 perfect utility oracle 都不能产生正收益，则后续模型研究应停止；本次结果相反，且 O1/O2/O4 这些非 O5 的 frozen oracle 也在 robustness split 上为正，因此 EP17C 有研究价值。

## 2. 核心发现

1. robustness primary gate 由 O5 触发，但 O1/O2/O4 也给出正值。O5 在 2,496 个 labelable robustness rows 上 defended 1,056 行，mean incremental return 为 2.9467%，trimmed mean 为 2.7594%，总 incremental return 为 73.5507。O1/O4 在 binary denominator 上 defended 526 个 negative rows，mean 为 2.4681%；O2 在 labelable denominator 上同样 defended 526 个 deep-drawdown rows，mean 为 1.8511%。
2. O1/O4/O2 primary 的收益几乎全部来自 defended negative rows。robustness split 中，O1/O4/O2 的 defended negative gain 都是 46.2030；primary O2 比 O1/O4 的 mean 更低，是因为 denominator 从 binary 1,872 行扩大到 labelable 2,496 行，624 个 neutral rows 稀释了均值。
3. O5 的额外收益来自两个地方：更精确地选择 negative rows，以及利用 neutral rows 中的可避免损失。robustness O5 defended_negative_gain 为 51.8208，defended_neutral_gain 为 21.7299；这解释了 O5 总收益 73.5507 高于 O1/O4/O2 的 46.2030。
4. O2 signed drawdown oracle 是稳定正值，但阈值越深，coverage 和收益越低。robustness 中，-8% 阈值 defended 731 行、mean 2.0213%；primary -10% defended 526 行、mean 1.8511%；-20% 只 defended 71 行、mean 降到 0.5593%。
5. O4 high-upside stress 证明“保留极高上涨”不是越严格越好。top30 stress 仍为正，mean 2.2123%；top20 降到 1.3158%；top10 变为 -0.3299%，因为过度防御 positive rows 带来 -78.5853 的 positive opportunity sacrifice。
6. partial defend 会显著压低 action value。robustness 50bps 下，O5 从 `q_defend = 0.00` 的 mean 2.9467% 降到 `q_defend = 0.25` 的 2.1576%、`q_defend = 0.50` 的 1.3705%。这说明当前上界主要来自“完全移除坏路径暴露”，保留部分暴露会削弱收益。
7. 本报告使用的所有 lineage 和 replay gate 均为 pass：17A 独立内容校验 141 项 pass；17B input gate 15/15 pass；row replay gate 6/6 pass；O2 drawdown replay 15/15 pass；O5 action selection proof 36/36 pass。

## 3. Gate 与 Denominator 口径

17B 只重放 frozen oracle ladder，不进行模型训练、阈值搜索、validation 选择、robustness tuning 或 payoff-label redesign。17A report prose 不是 gate；17B 以 17A machine-readable artifacts 为准，并重新做独立内容校验。

| gate_scope | pass_n | total_n | 说明 |
|:--|--:|--:|:--|
| 17A contract validation checks | 141 | 141 | 覆盖 decision、denominator、binding、action semantics、price path、delayed materialization、input artifact、contracts、manifests |
| 17B input artifacts | 15 | 15 | 3 个 17B 本地输入、11 个 17A handoff artifacts、1 个 16E row-level source |
| row replay audit | 6 | 6 | train/robustness/validation x labelable/binary denominator |
| O2 drawdown replay | 15 | 15 | 5 个 signed drawdown thresholds x 3 splits |
| O5 action selection proof | 36 | 36 | 3 splits x 4 cost tiers x 3 q_defend variants |

16E `utility_panel.parquet` 是按 4 个 cost tiers 膨胀的面板，共 93,620 行。17B 先固定 primary source cost tier = 50bps，并按 primary row key 去重，得到 23,405 个 replay denominator rows；再在 17B 内重新展开 oracle/cost/action-intensity 网格。这个处理避免了把 16E 的 cost-expanded rows 误当作 denominator。

| split_bucket | denominator_type | expected_step_n | observed_step_n | qfq replay diff max | signed drawdown diff max | O2 abs drawdown misuse | gate |
|:--|:--|--:|--:|--:|--:|:--|:--|
| train | labelable_full | 20,245 | 20,245 | 0.000000 | 0.000000 | False | pass |
| train | binary_primary | 14,962 | 14,962 | 0.000000 | 0.000000 | False | pass |
| robustness | labelable_full | 2,496 | 2,496 | 0.000000 | 0.000000 | False | pass |
| robustness | binary_primary | 1,872 | 1,872 | 0.000000 | 0.000000 | False | pass |
| validation | labelable_full | 664 | 664 | 0.000000 | 0.000000 | False | pass |
| validation | binary_primary | 505 | 505 | 0.000000 | 0.000000 | False | pass |

## 4. Oracle 定义与 primary gate

primary gate 使用 robustness split、50bps、`q_defend = 0.00`、primary variants only。主指标为 `trimmed_mean_incremental_return > 0`，并额外要求 `mean_incremental_return >= 0.0025`。`incremental_return = oracle_policy_net_return - blind_continue_net_return`；`q_defend = 0.00` 表示 defend 后进入 cash，完全移除后续 H20 暴露。

| oracle | primary variant | denominator | action rule | 用途 |
|:--|:--|:--|:--|:--|
| O0 | O0_blind_continue_primary | labelable_full | 全部 continue | 零收益 baseline |
| O1 | O1_negative_primary | binary_primary | negative defend，positive continue | 标签 oracle，下界现实知识读数 |
| O2 | O2_dd_10pct_primary | labelable_full | signed max drawdown <= -10% defend | 路径 drawdown oracle |
| O3 | skipped_nonblocking | appendix only | 当前无 false-repair label | 非阻塞状态 |
| O4 | O4_label_positive_primary | binary_primary | positive continue，negative defend | positive-preservation 标签 oracle |
| O5 | O5_perfect_utility_primary | labelable_full | defend_net > continue_net 才 defend | action-space 后见上界 |

## 5. Primary Ladder 结果

primary ladder 说明：下表只展示 50bps、`q_defend = 0.00` 的 primary variants。O0 的 incremental return 恒为 0；其他 oracle 的 mean/trimmed mean 是相对 blind continue 的平均增量收益。

| oracle | split | denominator | observed_n | defended_n | defended_rate | mean_incremental | trimmed_mean | sum_incremental | negative_gain | neutral_gain |
|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| O1 | train | binary_primary | 14,962 | 4,884 | 32.64% | 3.3079% | 3.2646% | 494.9312 | 494.9312 | 0.0000 |
| O1 | robustness | binary_primary | 1,872 | 526 | 28.10% | 2.4681% | 2.4747% | 46.2030 | 46.2030 | 0.0000 |
| O1 | validation | binary_primary | 505 | 180 | 35.64% | 3.6767% | 3.6101% | 18.5673 | 18.5673 | 0.0000 |
| O2 | train | labelable_full | 20,245 | 4,877 | 24.09% | 2.4444% | 2.3664% | 494.8674 | 494.8674 | 0.0000 |
| O2 | robustness | labelable_full | 2,496 | 526 | 21.07% | 1.8511% | 1.8220% | 46.2030 | 46.2030 | 0.0000 |
| O2 | validation | labelable_full | 664 | 180 | 27.11% | 2.7963% | 2.7144% | 18.5673 | 18.5673 | 0.0000 |
| O4 | train | binary_primary | 14,962 | 4,884 | 32.64% | 3.3079% | 3.2646% | 494.9312 | 494.9312 | 0.0000 |
| O4 | robustness | binary_primary | 1,872 | 526 | 28.10% | 2.4681% | 2.4747% | 46.2030 | 46.2030 | 0.0000 |
| O4 | validation | binary_primary | 505 | 180 | 35.64% | 3.6767% | 3.6101% | 18.5673 | 18.5673 | 0.0000 |
| O5 | train | labelable_full | 20,245 | 9,409 | 46.48% | 3.5563% | 3.3342% | 719.9625 | 534.3381 | 185.6245 |
| O5 | robustness | labelable_full | 2,496 | 1,056 | 42.31% | 2.9467% | 2.7594% | 73.5507 | 51.8208 | 21.7299 |
| O5 | validation | labelable_full | 664 | 319 | 48.04% | 3.9138% | 3.7224% | 25.9880 | 19.6785 | 6.3095 |

主要读数：

1. O1 与 O4 primary 在当前 binary denominator 下数值相同，因为 binary rows 只有 positive/negative，`negative defend` 与 `positive continue` 是同一个 action partition。
2. O2 primary 在 robustness defended_n 与 O1/O4 相同，都是 526，但 denominator 是 2,496 而不是 1,872，所以 mean 从 2.4681% 降到 1.8511%。这是 denominator 扩大导致的稀释，不是 defended negative gain 下降。
3. O5 在 robustness 的增量收益比 O1/O4 高 27.3477 个总收益单位，即 73.5507 - 46.2030。这部分主要来自 neutral rows 的可避免损失，以及比 label oracle 更细的 per-row utility 判断。
4. train、robustness、validation 三个 split 的方向一致：O1/O4/O2/O5 均为正，validation 并没有反向。这支持进入 17C，但不能替代 17C 的 stress test。

## 6. Six-cell 分解

six-cell 分解回答“增量收益从哪里来”。robustness、50bps、`q_defend = 0.00` 的关键分解如下。

| oracle | denominator | cell_id | step_n | mean_incremental | sum_incremental | contribution |
|:--|:--|:--|--:|--:|--:|--:|
| O1 | binary_primary | continued_positive | 1,346 | 0.0000% | 0.0000 | 0.00% |
| O1 | binary_primary | defended_negative | 526 | 8.7838% | 46.2030 | 100.00% |
| O2 | labelable_full | continued_positive | 1,346 | 0.0000% | 0.0000 | 0.00% |
| O2 | labelable_full | continued_neutral | 624 | 0.0000% | 0.0000 | 0.00% |
| O2 | labelable_full | defended_negative | 526 | 8.7838% | 46.2030 | 100.00% |
| O4 | binary_primary | continued_positive | 1,346 | 0.0000% | 0.0000 | 0.00% |
| O4 | binary_primary | defended_negative | 526 | 8.7838% | 46.2030 | 100.00% |
| O5 | labelable_full | continued_positive | 1,346 | 0.0000% | 0.0000 | 0.00% |
| O5 | labelable_full | defended_neutral | 587 | 3.7019% | 21.7299 | 29.54% |
| O5 | labelable_full | defended_negative | 469 | 11.0492% | 51.8208 | 70.46% |
| O5 | labelable_full | continued_neutral | 37 | 0.0000% | 0.0000 | 0.00% |
| O5 | labelable_full | continued_negative | 57 | 0.0000% | 0.0000 | 0.00% |

解释：

O1/O2/O4 的 primary 结果非常干净：没有 defended_positive sacrifice，也没有 defended_neutral gain；全部收益来自 defended_negative。O2 的 deep-drawdown rule 在 robustness primary 上刚好捕获了全部 526 个 negative rows，因此 six-cell 总收益与 O1/O4 相同。但 O2 的 denominator 包含 neutral，导致平均值更低。

O5 的结构不同。O5 不是标签 oracle，而是逐行比较 `defend_net_return(q_defend,cost_bps)` 和 `continue_net_return`。因此它会继续 57 个虽然 label 为 negative 但继续更优的 rows，也会 defend 587 个 neutral rows 中继续路径为负的 rows。这个行为说明：标签 negative 不是唯一 action-value 来源，neutral 里也有可防御的损失；但这正是后见之明上界，不能直接作为可交易规则。

## 7. Action Intensity 与成本敏感性

下表聚焦 robustness split 的 primary variants，展示 cost 与 q_defend 对 mean incremental return 的影响。`q_defend = 0.00` 是 full defend to cash；`q_defend = 0.25/0.50` 表示 defend 后仍保留部分 forward exposure。

| oracle | cost_bps | q=0.00 mean | q=0.25 mean | q=0.50 mean | q=0.00 defended_n | q=0.50 defended_n |
|:--|--:|--:|--:|--:|--:|--:|
| O1 | 0 | 2.6086% | 1.9564% | 1.3043% | 526 | 526 |
| O1 | 50 | 2.4681% | 1.8160% | 1.1638% | 526 | 526 |
| O1 | 100 | 2.3276% | 1.6755% | 1.0233% | 526 | 526 |
| O2 primary | 0 | 1.9564% | 1.4673% | 0.9782% | 526 | 526 |
| O2 primary | 50 | 1.8511% | 1.3620% | 0.8729% | 526 | 526 |
| O2 primary | 100 | 1.7457% | 1.2566% | 0.7675% | 526 | 526 |
| O4 | 0 | 2.6086% | 1.9564% | 1.3043% | 526 | 526 |
| O4 | 50 | 2.4681% | 1.8160% | 1.1638% | 526 | 526 |
| O4 | 100 | 2.3276% | 1.6755% | 1.0233% | 526 | 526 |
| O5 | 0 | 3.1631% | 2.3723% | 1.5815% | 1,095 | 1,095 |
| O5 | 50 | 2.9467% | 2.1576% | 1.3705% | 1,056 | 997 |
| O5 | 100 | 2.7410% | 1.9574% | 1.1802% | 997 | 900 |

发现：

1. 所有 primary oracle 在 100bps、`q_defend = 0.50` 下仍为正，但收益显著缩小。
2. q_defend 的影响大于 50bps 到 100bps 的成本变化。以 O5 为例，50bps 下从 q=0.00 到 q=0.50，mean 从 2.9467% 降到 1.3705%；而 q=0.00 下从 50bps 到 100bps，只从 2.9467% 降到 2.7410%。
3. O1/O2/O4 的 defended_n 不随 q_defend 改变，因为 action set 由 frozen oracle rule 决定；O5 的 defended_n 会随 q_defend/cost 改变，因为它逐 variant 重算 `defend_net > continue_net`。

## 8. Neutral Stress

neutral stress 不是 primary binary gate 的一部分，但它解释了 labelable denominator 下的均值变化。

| oracle | split | neutral_action_rule | neutral_n | binary_mean | labelable_stress_mean | neutral_mean | neutral_sum |
|:--|:--|:--|--:|--:|--:|--:|--:|
| O1 | train | continue | 5,283 | 3.3079% | 2.4447% | 0.0000% | 0.0000 |
| O1 | robustness | continue | 624 | 2.4681% | 1.8511% | 0.0000% | 0.0000 |
| O1 | validation | continue | 159 | 3.6767% | 2.7963% | 0.0000% | 0.0000 |
| O4 | train | defend | 5,283 | 3.3079% | 3.3586% | 3.5022% | 185.0186 |
| O4 | robustness | defend | 624 | 2.4681% | 2.7187% | 3.4704% | 21.6556 |
| O4 | validation | defend | 159 | 3.6767% | 3.7445% | 3.9597% | 6.2959 |

O1 neutral stress 等价于“neutral continue”，所以 labelable_stress_mean 只是把同一份 negative gain 分摊到更大的 denominator。robustness 中，46.2030 / 2,496 = 1.8511%，这正好对应 O2 primary 的 labelable mean。O4 neutral stress 则把 neutral 全部 defend，在 robustness 中额外产生 21.6556 的 neutral gain，使 labelable_stress_mean 升到 2.7187%。这说明 neutral 并非无价值，但 neutral handling 仍不能进入 primary binary gate，否则会把标签定义和 action-policy 诊断混在一起。

## 9. O2 Signed Drawdown Stress

O2 使用 signed negative drawdown，判定为 `signed_max_drawdown_h20 <= threshold`。所有 qfq lineage reconciliation 均为 pass，`signed_max_drawdown_replay_abs_diff_max = 0`，且 `positive_abs_drawdown_used_for_o2_threshold = False`。也就是说，O2 没有误用 abs drawdown 与负阈值比较。

| variant | threshold | robustness_n | defended_n | mean_incremental | trimmed_mean | gate |
|:--|--:|--:|--:|--:|--:|:--|
| O2_dd_08pct_stress | -8% | 2,496 | 731 | 2.0213% | 2.0596% | pass |
| O2_dd_10pct_primary | -10% | 2,496 | 526 | 1.8511% | 1.8220% | pass |
| O2_dd_12pct_stress | -12% | 2,496 | 369 | 1.5295% | 1.4644% | pass |
| O2_dd_15pct_stress | -15% | 2,496 | 211 | 1.0934% | 0.9262% | pass |
| O2_dd_20pct_stress | -20% | 2,496 | 71 | 0.5593% | 0.3252% | pass |

O2 的含义是：在当前 winner-episode step space 中，未来 H20 深回撤本身有明显 action value。阈值越浅，coverage 越高，收益越高；阈值越深，虽然单行被防御的损失更大，但触发太少，总体 mean 被 denominator 稀释。primary -10% 是一个中间点：它不依赖 payoff label，且正好覆盖 robustness 的 526 个 negative rows。

## 10. O4 High-upside Threshold Freeze

O4 high-upside stress 使用 train-only payoff quantile cutoff，不允许 split-local recompute。

| variant | train_quantile | train_cutoff | robustness defended_n | mean_incremental | positive_sacrifice | negative_gain | neutral_gain |
|:--|--:|--:|--:|--:|--:|--:|--:|
| O4_high_upside_top30_stress | 0.70 | 0.059633 | 1,644 | 2.2123% | -17.3773 | 50.9416 | 21.6556 |
| O4_high_upside_top20_stress | 0.80 | 0.101229 | 1,910 | 1.3158% | -38.6237 | 49.8097 | 21.6556 |
| O4_high_upside_top10_stress | 0.90 | 0.172107 | 2,207 | -0.3299% | -78.5853 | 48.6953 | 21.6556 |

这个 stress 的信息很重要：如果只保留极少数 high-upside positives，其余 rows 都 defend，positive opportunity sacrifice 会迅速吞掉 negative/neutral avoidance。top30 仍能为正，top20 边际下降明显，top10 已经变负。因此 O4 high-upside stress 更适合作为“保留 positive opportunity 的敏感性读数”，不适合作为 primary action rule。

## 11. O5 Action Selection Proof

O5 是 perfect utility upper bound。每个 `q_defend/cost_bps` variant 都独立重算：

```text
defend if q_defend * forward_return_h20 - cost_bps / 10000 > forward_return_h20
```

robustness split 的 proof 如下。`formula_recomputed_mismatch_n = 0` 表示报告中的 O5 action set 与公式逐行一致；当 cost=0 且 q_defend>0 时，partial defend 与 full defend action set 相同是公式上的等价结果，不是复用 full-defend action set。

| cost_bps | q_defend | observed_n | defended_n | formula_mismatch_n | same_as_full_defend_ref | reuse_gate | proof_gate |
|--:|--:|--:|--:|--:|:--|:--|:--|
| 0 | 0.00 | 2,496 | 1,095 | 0 | True | reference | pass |
| 0 | 0.25 | 2,496 | 1,095 | 0 | True | pass_same_by_formula_zero_cost | pass |
| 0 | 0.50 | 2,496 | 1,095 | 0 | True | pass_same_by_formula_zero_cost | pass |
| 25 | 0.00 | 2,496 | 1,080 | 0 | True | reference | pass |
| 25 | 0.25 | 2,496 | 1,076 | 0 | False | pass | pass |
| 25 | 0.50 | 2,496 | 1,056 | 0 | False | pass | pass |
| 50 | 0.00 | 2,496 | 1,056 | 0 | True | reference | pass |
| 50 | 0.25 | 2,496 | 1,039 | 0 | False | pass | pass |
| 50 | 0.50 | 2,496 | 997 | 0 | False | pass | pass |
| 100 | 0.00 | 2,496 | 997 | 0 | True | reference | pass |
| 100 | 0.25 | 2,496 | 964 | 0 | False | pass | pass |
| 100 | 0.50 | 2,496 | 900 | 0 | False | pass | pass |

O5 的正值近乎是数学上预期的：它只在 defend_net 大于 continue_net 时 defend。因此它应该被理解为 action-space upper bound，而不是可实现 signal。真正有诊断意义的是：O1/O2/O4 也在 robustness primary 下为正，说明即使不用 O5 的完美后见信息，冻结标签和冻结路径 oracle 也显示 action headroom。

## 12. Search Accounting 与授权边界

| check | status |
|:--|:--|
| no_model_training | True |
| no_model_refit | True |
| no_survival_threshold_tuning | True |
| no_validation_selection | True |
| no_robustness_tuning | True |
| no_payoff_label_redesign | True |
| no_split_local_payoff_quantile_recompute | True |
| no_live_trading_authorized | True |
| search_accounting_gate | pass |

17B 不做模型选择，也不把 OOS 结果用于选择 cost、q_defend、drawdown threshold 或 payoff threshold。O4 high-upside threshold 来自 train quantile freeze；primary decision 只读 robustness split 的 frozen primary variants。

## 13. 研究判断与下一步

本次 17B 不是 episode 的最终成功，而是“action-value upper bound diagnostic 通过”。结论可以分三层：

1. 最弱层：O5 perfect utility upper bound 为正。这说明当前 action space 没有被 16E 的失败完全否定，至少在后见之明下存在可避免损失。
2. 中间层：O1/O4 label oracle 与 O2 signed drawdown oracle 也为正。这比单独 O5 更有价值，因为它说明收益不完全依赖逐行 perfect utility。
3. 风险层：所有 oracle 都使用未来信息或 frozen labels，不是可交易模型。下一步只能进入 EP17C robustness stress，检查这些上界是否对 split、cost、denominator、neutral handling、threshold stress 和可能的实现代理仍有稳定余量。

因此，17B 的 actionable handoff 是：

```text
allowed_next_step = requirement_17c_oracle_robustness_stress.md
not_allowed = payoff-state research, production signal, live trading, portfolio backtest
```

17C 应重点压力测试三件事：第一，O1/O2/O4 的正值是否只来自当前 split 的偶然 denominator；第二，O5 的额外 neutral gain 是否在更严格成本和 partial exposure 下仍保留；第三，O2 signed drawdown oracle 的 -8% 到 -20% 梯度是否在更宽的样本切片中保持单调、正值且不依赖 abs drawdown 口径错误。
