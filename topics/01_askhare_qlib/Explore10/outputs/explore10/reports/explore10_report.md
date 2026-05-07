# Explore10 详细研究报告：Alpha158-like Atomic Feature Bank 与 Path-to-Primitive Discovery

## 1. 执行结论

本次 Explore10 的最终建议为：

```text
recommendation = stop_due_to_zero_or_insufficient_atomic_support
```

核心结论不是“atomic feature bank 已经证明无效”，而是：

```text
汽车主任务没有形成可训练的 locked LGBM probe，
因此没有资格进入 path extraction、candidate support、null pass 或 next requirement。
```

本次运行生成了 `99` 个 primitive candidate，但全部来自 `电子` placebo / weak-signal scope：

| scope | candidates | allowed_for_next_requirement |
|---|---:|---:|
| 电子 failure_reject | 50 | 0 |
| 电子 launch_winner | 49 | 0 |
| 汽车 launch_winner | 0 | 0 |
| 汽车 failure_reject | 0 | 0 |

因此，本阶段没有任何 `atomic_primitive_candidate_for_next_requirement = true`，`explore10_next_requirement_candidate_map.csv` 为空。

## 2. 研究问题回答

### 2.1 Atomic bank 是否覆盖原 primitive 失效区域？

答案：不能给出正向覆盖结论。

原因是汽车主任务在进入 token coverage 之前已经失败。`汽车 + launch_winner` 的 core folds 中，`fold_2021` 到 `fold_2023` 虽然有 validation rows 和 positives，但 `distinct_instruments` 只有 `12-13`，低于配置门槛 `20`，因此 `model_fit_pass = false`、`allowed_for_path_extraction = false`。

| fold | train rows | train positives | validation rows | validation positives | distinct instruments | used features | pass |
|---|---:|---:|---:|---:|---:|---:|---|
| 汽车 launch fold_2020 | 0 | 0 | 0 | 0 | 0 | 0 | false |
| 汽车 launch fold_2021 | 601 | 95 | 206 | 44 | 12 | 160 | false |
| 汽车 launch fold_2022 | 819 | 196 | 213 | 40 | 13 | 160 | false |
| 汽车 launch fold_2023 | 1018 | 236 | 256 | 30 | 13 | 160 | false |

P0.9B high-score coverage audit 也没有给出正向支持。所有 frozen candidate 都来自电子 scope，audit-only high-score coverage 中 `covered_high_score_row_count = 0`，不能说明汽车高分区域被 atomic tokens 覆盖。

### 2.2 LGBM path 是否能稳定复现？

答案：只在电子 placebo / weak-signal scope 中观察到 path；汽车 scope 没有 path。

电子任务产生了 `2138` 条 raw paths 和 `1789` 个 relaxed patterns：

| scope | raw paths | excluded paths | canonical patterns | max fold presence |
|---|---:|---:|---:|---:|
| 电子 failure_reject | 910 | 30 | 729 | 2 |
| 电子 launch_winner | 1228 | 37 | 1060 | 3 |

电子 launch 的 path 机制主要集中在：

```text
volatility_range
cross_section_rank
industry_market_context
```

电子 failure 的 path 机制主要集中在：

```text
industry_market_context
volatility_range
price_distance
volume_money
```

这些机制读数只能作为 placebo / weak-signal stress。它们不能迁移为汽车主任务结论。

### 2.3 Path pattern 是否能转成 audited primitive candidate？

答案：技术上可以转写，但没有任何可进入下一阶段的主候选。

所有 `99` 个 candidate 都满足 freeze / manualizability / threshold nonselection 的机械约束：

| audit | result |
|---|---|
| candidate freeze audit | pass |
| metric nonselection audit | pass |
| threshold nonselection audit | pass |
| forbidden recommendation self-check | pass |
| required artifact authority audit | pass |

但候选全部来自电子，因此自动带有 `placebo_only`。在 rejection summary 中，按候选去重后的拒绝原因如下：

| rejection reason | candidate count |
|---|---:|
| placebo_only | 99 |
| collapsed_under_null | 85 |
| instrument_year_concentration_too_high | 25 |
| zero_or_insufficient_support | 5 |

### 2.4 Alpha158-like bank 是否只是制造更多 search bias？

答案：本次结果强烈提示 search-bias 风险存在，不能推进。

电子 placebo scope 中确实出现了若干看起来不错的 candidate：

| scope | stable_atomic_primitive | weak_but_not_collapsed | collapsed_under_null |
|---|---:|---:|---:|
| 电子 failure_reject | 12 | 11 | 27 |
| 电子 launch_winner | 2 | 12 | 35 |

这恰好是 Explore10 requirement 想要捕捉的风险：如果 negative-control / weak-signal scope 也能产生“漂亮 primitive”，那么 path-to-primitive 流程本身可能在较大 feature bank 下制造叙事。`explore10_placebo_stress_audit.csv` 记录 `electronics_failure_stable_candidate_count = 14`，因此 placebo stress 不支持把这些候选解释为主线正向证据。

Null audit 已记录：

| null / audit family | rows |
|---|---:|
| label_permutation_within_industry_fold | 6940 |
| instrument_year_block_shuffle | 6940 |
| path_structure_null_from_permuted_lgbm | 6940 |
| candidate_level_null_aggregation | 99 |

Candidate-level null aggregation 明确没有使用 fold-level p-value averaging，也没有使用 best-fold-only null。

### 2.5 是否存在可进入下一阶段的 atomic primitive seed？

答案：不存在。

`explore10_next_requirement_candidate_map.csv` 为 0 行。当前不应进入 Explore11，不应回测，不应冻结规则。

## 3. Feature Bank Preflight

Atomic feature bank resolved 后共有 `164` 个 path/formula eligible features。

| metric | value | gate |
|---|---:|---|
| feature_count_total | 164 | diagnostic |
| missing_row_rate | 35.52% | high |
| missing_weight_share | 38.57% | fail, threshold 20% |
| constant_or_near_constant_rate | 1.83% | pass |
| duplicate_or_high_corr_cluster_count | 64 | fail, threshold 50 |
| max_feature_family_share | 29.27% | pass |
| feature_family_missing_weight_share_max | 23.31% | pass |
| feature_bank_preflight_pass | false | blocking |

这里有两个重要含义：

1. 缺失不是单一 feature family 爆掉，而是整体 missing weight share 过高。
2. duplicate / high-corr cluster 超标，说明 Alpha158-like bank 的表达空间仍有过多近似重复 token。

因此，即使汽车任务 trainability 不失败，当前 feature bank 也不应直接作为稳定 primitive discovery 的通过版本。

## 4. Scope Lock 与 Trainability

Scope lock 本身通过了 row reconciliation，但 trainability 只在电子任务通过：

| scope | source rows | model_fit_pass folds | path eligible folds |
|---|---:|---:|---:|
| 汽车 launch_winner | 4863 | 0 | 0 |
| 汽车 failure_reject | 17629 | 0 | 0 |
| 电子 launch_winner | 6885 | 3 | 3 |
| 电子 failure_reject | 24652 | 4 | 4 |

汽车 failure 也被 `distinct_instruments` 卡住：

| fold | train rows | train positives | validation rows | validation positives | distinct instruments | pass |
|---|---:|---:|---:|---:|---:|---|
| 汽车 failure fold_2020 | 1320 | 547 | 605 | 161 | 10 | false |
| 汽车 failure fold_2021 | 1993 | 745 | 635 | 320 | 13 | false |
| 汽车 failure fold_2022 | 2516 | 971 | 642 | 231 | 13 | false |
| 汽车 failure fold_2023 | 3114 | 1249 | 751 | 304 | 13 | false |

这说明本次 stop 的第一原因是“汽车样本宽度不足以满足 locked probe 合同”，不是“汽车 atomic primitive 已经被充分检验后失败”。

## 5. 电子 Placebo / Weak-Signal 读数

电子 launch 的 LGBM probe 有一定诊断读数：

| fold | validation rows | positives | AUC | prediction_std | unique predictions |
|---|---:|---:|---:|---:|---:|
| fold_2021 | 412 | 53 | 0.6044 | 0.2651 | 205 |
| fold_2022 | 356 | 10 | 0.5728 | 0.1822 | 180 |
| fold_2023 | 372 | 31 | 0.6769 | 0.1933 | 157 |

电子 failure 的读数更弱：

| fold | validation rows | positives | AUC | prediction_std | unique predictions |
|---|---:|---:|---:|---:|---:|
| fold_2020 | 1027 | 366 | 0.3807 | 0.2039 | 425 |
| fold_2021 | 1200 | 633 | 0.5030 | 0.2092 | 516 |
| fold_2022 | 1039 | 606 | 0.5281 | 0.1216 | 473 |
| fold_2023 | 1043 | 541 | 0.5604 | 0.1125 | 362 |

从 feature-family importance 看，电子 launch 的 top families 是 `volatility_range`、`cross_section_rank`、`industry_market_context`；电子 failure 的 top families 是 `industry_market_context`、`volatility_range`、`price_distance`。这些读数更像流程压力测试，而不是可复用行业机制。

## 6. Candidate Coverage / Null / Concentration

电子候选的 token support 并不差：

| scope | candidate-fold rows | support median | support max | token pass rows |
|---|---:|---:|---:|---:|
| 电子 failure_reject | 200 | 413.5 | 946 | 175 |
| 电子 launch_winner | 147 | 220.0 | 396 | 145 |

但 support 不是充分条件。候选仍被拒绝，主要因为：

```text
1. scope 是电子 placebo，不是汽车 primary；
2. 大多数 candidate collapsed_under_null；
3. 部分 candidate 存在 instrument / instrument-year concentration；
4. placebo stress 出现 stable candidate，说明 search-bias 风险不可忽略。
```

Concentration audit 中：

| scope | candidates | concentration pass | median top instrument-year share | max top instrument-year share |
|---|---:|---:|---:|---:|
| 电子 failure_reject | 50 | 43 | 5.40% | 12.02% |
| 电子 launch_winner | 49 | 31 | 5.58% | 11.16% |

电子 launch 中有 candidate 的 top5 instrument contribution 高达 `86.09%`，这类结构即使 lift 好看，也不能被视为稳健 primitive。

## 7. 对 Requirement 的逐项结论

| requirement question | answer |
|---|---|
| Atomic bank 是否覆盖 P0.9B primitive 失效区域？ | 否。汽车主任务没有 trainable core folds，无法进入覆盖验证。 |
| LGBM path 是否稳定复现？ | 只在电子 placebo scope 复现；汽车 scope 没有 path。 |
| Path 是否能转成 audited primitive？ | 电子 scope 可以机械转写 99 个，但全部不得进入下一阶段。 |
| 是否只是制造 search bias？ | 是高风险。电子 placebo 产生 14 个 stable-looking candidates。 |
| 是否存在 next-stage seed？ | 不存在。next requirement map 为空。 |

## 8. 研究洞察

### 8.1 当前 stop 更像样本合同失败，不是机制失败

汽车主任务失败在 `distinct_instruments`，而不是 AUC、null、support 或 path stability。这意味着现在不能说“汽车 atomic primitive 不存在”；只能说“当前 locked panel + 当前 trainability guardrail 下，汽车主任务没有资格被检验”。

### 8.2 Feature bank v1 过宽且冗余

`missing_weight_share = 38.57%` 和 `duplicate_or_high_corr_cluster_count = 64` 同时失败，说明 feature bank v1 还不是一个干净的 atomic bank。后续如果继续 Explore10，优先级应该是 feature bank hygiene，而不是扩大 search space。

### 8.3 Placebo 产生 stable candidate 是强警告

电子不是主任务，却产生了 14 个 stable-looking candidates。这个结果说明 path-to-primitive translation 在大 feature bank 下容易产生“看起来可解释”的结构。任何下一轮实验都必须保留 negative-control，并且不能只看 real lift。

### 8.4 不建议降低门槛直接救汽车任务

汽车 distinct instruments 只有 12-13，低于 20。直接降门槛可能让 path extraction 变成少数股票叙事。更合理的下一步是先审查汽车样本构造与 P0.9B row selection，确认为什么 PIT 汽车主任务只剩这么窄的 instrument coverage。

## 9. 建议的下一步

不建议进入 Explore11。

如果继续 Explore10，应先做一个修复型 requirement，而不是 validation/backtest：

```text
Explore10A: automotive sample-width and feature-bank hygiene audit
```

建议目标：

1. 审计汽车 `launch_winner` 与 `failure_reject` 的 source row selection，解释为什么 distinct instruments 只有 12-13。
2. 不降低 trainability guardrail，除非 requirement 明确给出新的最小样本合同。
3. 清理 feature bank：去掉高缺失、高相关、重复表达的 atomic features。
4. 重新跑 primary 汽车 launch，只有在至少 2 个 core folds trainable 后，才允许讨论 path pattern 和 primitive candidate。
5. 保留电子 failure negative control，防止再次把 placebo 结构误读成机制。

## 10. 自检

| audit | result |
|---|---|
| required artifact authority | pass |
| candidate freeze | pass |
| metric nonselection | pass |
| threshold nonselection | pass |
| forbidden recommendation self-check | pass |
| cache parquet ignored by git | pass |

本报告没有输出：

```text
selected_lgbm_model
selected_score_bucket
actionable_trade_rule
strategy_backtest
freeze_strategy
```

Explore10 仍是 atomic primitive discovery phase，不是策略验证阶段。
