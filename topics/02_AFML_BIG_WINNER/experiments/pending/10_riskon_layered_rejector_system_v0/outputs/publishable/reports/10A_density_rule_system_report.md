# 10A 密度规则系统报告

## 结论摘要

- 决策状态：`10A_density_population_source_caveated_frozen`
- source caveat：`True`。10A 继承 09 系列输入的 source caveat，因此本报告冻结的是 source-caveated population，不应被解读为最终生产口径已经解除数据源风险。
- E1 proxy 状态：`episode_level_proxy_from_08_membership`
- 已物化 rule arm 数：`5`
- 输入总行数：`41,937`；其中 risk-on 可物化行数 `40,050`，risk-off E1 readonly 排除行数 `1,887`。
- 10A 只做密度 population 冻结、审计与 power-readiness 统计；不训练模型、不选择阈值，也不声明 rejector uplift。

核心发现：

1. R-core 的密度问题主要来自同一标的的重复触发，而不是 family 或 mechanism 层面的重叠。
2. 默认 population `10A__same_instrument_cooldown_10d` 在 R-core 上压制 `14,935 / 30,790 = 48.51%` 的审计分母，同时保留 `15,802` 个 admitted events、`2,647` 个 winner、`1,280` 个 fast-fail positives 和 `5,033` 个 false-repair positives，是后续 10B/10C 最稳健的折中口径。
3. `same_instrument_cooldown_10d` 与 `same_instrument_rolling_cap_10d_cap1` 在当前数据上完全等价；`20d cap1` 更激进，R-core 压制率升至 `56.96%`，但 admitted winner 降至 `2,180`。
4. `same_family_dedup_10d` 和 `same_mechanism_dedup_10d` 保留了大多数样本与 winner，但对 R-core 密度削减很弱，分别只压制 `0.08%` 和 `2.75%` 的审计分母。
5. R6 readout 基本不触发 10D 去重压制，除 `20d cap1` 外压制率均为 `0.00%`；因此 R6 更适合作为 readout/control，不应作为主要密度治理依据。

## 输入范围与排除审计

10A 从 09A/09B 的 risk-on scoped event bindings、feature matrix 和 sample weights 进入密度规则系统。risk-off E1 scope 只允许作为外部 readout/control，不参与 10A 物化，也不尝试 feature 或 weight join。

| scope | source_pool_id | input_denominator_id | event_regime_bucket | row_n | unique_sample_n | action |
|:--|:--|:--|:--|--:|--:|:--|
| risk-on materialized | `08_R_core_event_regime_gated` / `08_R6_event_regime_gated` | risk-on horizon-complete scopes | `risk_on` | 40,050 | 40,050 | 进入 5 个 rule arm 物化 |
| risk-off E1 readonly | `07_E1_only` | `risk_off_e1_horizon_complete_readonly` | `risk_off` | 1,887 | 1,887 | `excluded_riskoff_e1_readonly` |

risk-off E1 readonly 的 `feature_matrix_join_attempted_flag = False`、`sample_weight_join_attempted_flag = False`、`post_dedup_materialized_flag = False`。这保证 E1-missed readout 不会反向改变 risk-on admission。

## Rule Arm 总览

审计分母按 `admitted + suppressed + non_executable_audit_only` 计算。`non_executable_audit_only` 行保留在审计中，但不计入 admitted population。

| rule_arm_id | denominator_id | 审计分母 | admitted | suppressed | nonexec | 压制率 | winner | winner/admitted | fast_fail+ | false_repair+ | E1-missed winner |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `same_family_dedup_10d` | `post_dedup_risk_on_r6_readout` | 9,260 | 9,230 | 0 | 30 | 0.00% | 1,607 | 17.41% | 741 | 3,113 | 844 |
| `same_family_dedup_10d` | `post_dedup_risk_on_r_core` | 30,790 | 30,711 | 26 | 53 | 0.08% | 5,284 | 17.21% | 2,172 | 10,360 | 2,703 |
| `same_instrument_cooldown_10d` | `post_dedup_risk_on_r6_readout` | 9,260 | 9,230 | 0 | 30 | 0.00% | 1,607 | 17.41% | 741 | 3,113 | 844 |
| `same_instrument_cooldown_10d` | `post_dedup_risk_on_r_core` | 30,790 | 15,802 | 14,935 | 53 | 48.51% | 2,647 | 16.75% | 1,280 | 5,033 | 1,357 |
| `same_instrument_rolling_cap_10d_cap1` | `post_dedup_risk_on_r6_readout` | 9,260 | 9,230 | 0 | 30 | 0.00% | 1,607 | 17.41% | 741 | 3,113 | 844 |
| `same_instrument_rolling_cap_10d_cap1` | `post_dedup_risk_on_r_core` | 30,790 | 15,802 | 14,935 | 53 | 48.51% | 2,647 | 16.75% | 1,280 | 5,033 | 1,357 |
| `same_instrument_rolling_cap_20d_cap1` | `post_dedup_risk_on_r6_readout` | 9,260 | 8,797 | 433 | 30 | 4.68% | 1,511 | 17.18% | 713 | 2,925 | 787 |
| `same_instrument_rolling_cap_20d_cap1` | `post_dedup_risk_on_r_core` | 30,790 | 13,200 | 17,537 | 53 | 56.96% | 2,180 | 16.52% | 1,070 | 4,174 | 1,110 |
| `same_mechanism_dedup_10d` | `post_dedup_risk_on_r6_readout` | 9,260 | 9,230 | 0 | 30 | 0.00% | 1,607 | 17.41% | 741 | 3,113 | 844 |
| `same_mechanism_dedup_10d` | `post_dedup_risk_on_r_core` | 30,790 | 29,889 | 848 | 53 | 2.75% | 5,154 | 17.24% | 2,119 | 10,070 | 2,643 |

从密度治理角度看，family 和 mechanism 去重几乎没有解决 R-core 的核心问题。R-core 在 family 去重后仍保留 `30,711` 个 admitted events，基本等同原始密度；mechanism 去重也只减少 `848` 行。相反，同一标的 10D cooldown 直接把 admitted events 从约 `30.7k` 降到 `15.8k`，且 winner/admitted 只从 `17.21%` 降到 `16.75%`，说明被压制的主要是密集重复触发，而不是单纯筛掉 winner。

## 默认 Population 明细

默认下游 population 是 `10A__same_instrument_cooldown_10d`，对应 `same_instrument_cooldown_10d` + `post_dedup_risk_on_r_core`。

总量：

- 审计分母：`30,790`
- admitted events：`15,802`
- suppressed events：`14,935`
- non-executable audit-only：`53`
- admitted winner：`2,647`
- fast-fail positive：`1,280`
- false-repair positive：`5,033`
- E1-missed winner readout：`1,357`
- unique instrument：`1,015`
- unique event day：`872`

按 split：

| split | 审计分母 | admitted | suppressed | nonexec | 压制率 | winner | winner/admitted | fast_fail+ | fast_fail winner | false_repair+ | hybrid+ | unique_instrument | unique_day |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `train` | 16,603 | 8,318 | 8,253 | 32 | 49.71% | 1,491 | 17.93% | 702 | 70 | 3,025 | 3,132 | 1,015 | 473 |
| `robustness` | 9,730 | 4,970 | 4,741 | 19 | 48.73% | 995 | 20.02% | 342 | 39 | 1,299 | 1,402 | 760 | 271 |
| `validation` | 4,457 | 2,514 | 1,941 | 2 | 43.55% | 161 | 6.40% | 236 | 5 | 709 | 782 | 669 | 128 |

密度读数：

| split | formal_density_p95 | rolling_10d_density | rolling_20d_density |
|:--|--:|--:|--:|
| `train` | 1.0 | 0.1 | 0.1 |
| `robustness` | 1.0 | 0.1 | 0.1 |
| `validation` | 1.0 | 0.1 | 0.1 |

默认口径在三个 split 上都把 10D 同标的密度压到 `0.1`，即每个 instrument-session 窗口内只保留一个主事件。validation 的 winner/admitted 明显低于 train 和 robustness，说明 10A 的 split 留存不能被误读为 label uplift；它只是给 10B/10C 提供不经事后调参的稳定 population。

## Power Gate Readiness

Power audit 的 supported rows 是容量审计单元，不是模型训练结果，也不是 uplift 结论。10A 的职责是判断给定 rule arm 和 scope 是否具备进入后续 ML supported gate 的最小样本条件。

| rule_arm_id | R-core fast-fail supported rows | R-core false-repair supported rows | R6 fast-fail supported rows | R6 false-repair supported rows |
|:--|--:|--:|--:|--:|
| `same_family_dedup_10d` | 11 | 15 | 0 | 0 |
| `same_instrument_cooldown_10d` | 9 | 15 | 0 | 0 |
| `same_instrument_rolling_cap_10d_cap1` | 9 | 15 | 0 | 0 |
| `same_instrument_rolling_cap_20d_cap1` | 8 | 15 | 0 | 0 |
| `same_mechanism_dedup_10d` | 11 | 15 | 0 | 0 |
| **合计** | **48** | **75** | **0** | **0** |

含义：

- fast-fail supported rows 合计 `48`，其中默认口径贡献 `9` 行；R6 readout 贡献 `0` 行。
- false-repair supported rows 合计 `75`，5 个 R-core rule arm 各贡献 `15` 行；R6 readout 贡献 `0` 行。
- 默认口径保留 `1,280` 个 fast-fail positives 和 `5,033` 个 false-repair positives，满足后续 10B/10C 做 capacity-aware 评估的基本样本条件。
- 这些结果只说明 population 具备后续审计空间，不说明任何 rule arm 已经带来可交易的 rejector uplift。

## E1 Rollup 与 Readout

E1 rollup 在所有 arm/scope 上均为 `mixed_non_blocking`。这表示 E1 episode membership 覆盖不完整，但不阻塞 10A population 冻结；E1-missed 只作为 readout 保留，不能改变 admitted/suppressed 决策。

| rule_arm_id | denominator_id | admitted | E1 membership | no membership | status |
|:--|:--|--:|--:|--:|:--|
| `same_family_dedup_10d` | `post_dedup_risk_on_r6_readout` | 9,230 | 3,342 | 5,888 | `mixed_non_blocking` |
| `same_family_dedup_10d` | `post_dedup_risk_on_r_core` | 30,711 | 11,676 | 19,035 | `mixed_non_blocking` |
| `same_instrument_cooldown_10d` | `post_dedup_risk_on_r6_readout` | 9,230 | 3,342 | 5,888 | `mixed_non_blocking` |
| `same_instrument_cooldown_10d` | `post_dedup_risk_on_r_core` | 15,802 | 5,465 | 10,337 | `mixed_non_blocking` |
| `same_instrument_rolling_cap_10d_cap1` | `post_dedup_risk_on_r6_readout` | 9,230 | 3,342 | 5,888 | `mixed_non_blocking` |
| `same_instrument_rolling_cap_10d_cap1` | `post_dedup_risk_on_r_core` | 15,802 | 5,465 | 10,337 | `mixed_non_blocking` |
| `same_instrument_rolling_cap_20d_cap1` | `post_dedup_risk_on_r6_readout` | 8,797 | 3,139 | 5,658 | `mixed_non_blocking` |
| `same_instrument_rolling_cap_20d_cap1` | `post_dedup_risk_on_r_core` | 13,200 | 4,432 | 8,768 | `mixed_non_blocking` |
| `same_mechanism_dedup_10d` | `post_dedup_risk_on_r6_readout` | 9,230 | 3,342 | 5,888 | `mixed_non_blocking` |
| `same_mechanism_dedup_10d` | `post_dedup_risk_on_r_core` | 29,889 | 11,333 | 18,556 | `mixed_non_blocking` |

默认口径中，`5,465 / 15,802` admitted events 能够映射到 E1 membership，`10,337` 行没有 membership。这个覆盖率足够做保守 readout，但不足以把 E1 retention 作为 10A admission 的硬约束。

## 方法论解释

10A 的价值不是证明一个新信号，而是把 09C 之前高密度、重复触发的候选事件变成可审计、可复现、不会通过事后回看调参的 population。当前数据支持以下判断：

1. `same_instrument_cooldown_10d` 是最适合作为默认下游入口的规则：它用简单、可解释的 10-session 同标的去重，消除了接近一半的 R-core 审计分母，同时保留了足够多的 winner 和 cost labels。
2. `same_instrument_rolling_cap_20d_cap1` 可作为更强约束的敏感性分析，但不适合作为默认口径。它多压制 `2,602` 个 R-core events，相比 10D cooldown 少保留 `467` 个 winner、`210` 个 fast-fail positives 和 `859` 个 false-repair positives。
3. family/mechanism 去重可以作为解释性 readout，但不应被当作密度治理主规则。它们的 admitted winner rate 略高，主要原因是几乎没有压制事件，而不是完成了有效的去密度。
4. R6 readout 的 supported gate 全为 `0`，说明它在 10A 中的角色应保持为对照和审计，不应进入默认 ML-supported gate。
5. source caveat 未解除前，10A 输出只能作为 source-caveated frozen population 使用。后续 10B/10C 可以在该 population 上训练或评估，但结论必须继续携带这一上游 caveat。
