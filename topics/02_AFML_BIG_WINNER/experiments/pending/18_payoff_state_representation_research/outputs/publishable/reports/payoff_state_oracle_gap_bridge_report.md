# 18F Payoff-state Oracle Gap Bridge Report

## 结论

`decision_state = 18F_utility_bridge_not_supported`。

18F 的问题不是上游 18C 不可用，也不是输入、join、oracle denominator 或 no-policy 约束失败。相反，上游 18C refresh 已经通过，43 个输入 artifact 均可读且 schema/cache gate 通过，18C score panel 与 18E refreshed matrix 一对一 join 成功，O5 incremental identity replay 也通过。真正的阻塞点是：18C 刷新后的 payoff ranking score 没有转化为可用的 action-value utility mask。

18F is not a policy, not a backtest, and not a production signal.

本报告只判断 payoff-state 表征是否已经足以作为后续 policy preflight 的 utility evidence。结论是：不能。当前证据仍应停留在 representation/ranking diagnostic 层，不应进入 19 policy preflight。

## 核心发现

1. **18C 的排序可分性没有转化成正 utility。** Primary train-frozen operating point `defend_bottom30_continue_rest` 在 robustness labelable_full 分母上的 learned mean incremental return 为 `-0.010552`，而 O5 perfect utility oracle 为 `0.029467`，O2 drawdown oracle 为 `0.018511`。这意味着 O5 gap remaining 达到 `0.040019`，O5 approximation ratio 为 `-0.358080`，不是“离 oracle 还有距离”，而是方向已经为负。

2. **失败来自过度牺牲正 payoff，而不是 oracle contract 错误。** Robustness primary 分解显示，被防守的 positive 行有 `519` 行，占全分母 `20.79%`，贡献 `-0.025077` 的全分母拖累；被防守的 negative 行只有 `298` 行，贡献 `+0.010495`；neutral 贡献 `+0.004031`。三者相加后正好得到 `-0.010552`。也就是说，负样本规避收益和 neutral 收益不足以覆盖 positive opportunity cost。

3. **primary cutoff 在 robustness 上实际防守了 44.11% 的行。** 规则是 train-frozen 的 bottom30 cutoff，train defended rate 为 `30.00%`，但 robustness defended rate 升到 `44.11%`。这不是 validation/tuning 泄漏，而是 score 分布迁移造成的实际 action coverage 扩张；扩张后的防守集合吸入了太多后续可能继续上涨的 positive 行。

4. **payoff retention gate 同时失败。** Robustness primary 的 top30 payoff retention rate 为 `0.625587`，低于 `0.70` 门槛；top20 payoff retention rate 为 `0.636519`，低于 `0.80` 门槛。换句话说，如果把该 score 当作防守掩码，它会丢掉过多高 payoff opportunity。

5. **cluster bootstrap 给出稳定负结论。** Robustness primary learned utility 的 2000 次 episode-cluster bootstrap 95% CI 为 `[-0.014387, -0.007484]`，整个区间低于 0。该结果不是少数 cluster 噪声导致的单点失败。

6. **top-k/family sensitivity 没有找到“移除某个特征后 utility 转正”的证据。** 因 base learned utility 已经为负，retention rate 按需求定义不可评估，所有 sensitivity row 均为 `not_evaluable`。但 sensitivity learned utility 本身也全为负：top1 removal 后为 `-0.016227`，top5 removal 后为 `-0.012234`，family_M1_removed 虽然改善到 `-0.007850`，仍未转正。

7. **validation stress 没有推翻 robustness 结论。** Validation learned utility 为 `-0.001605`，比 robustness 轻，但仍为负；validation top30/top20 retention 分别为 `0.787736` 和 `0.772414`。这说明 validation 上的主要问题不是 payoff retention，而是 learned defend action 仍没有正增量收益。

8. **binary O4 只能作为 appendix sanity，不可救回 labelable_full 失败。** Robustness binary_primary appendix 上，primary learned mean 为 `-0.019444`，O4 binary oracle 为 `0.024681`，binary approximation ratio 为 `-0.787796`。即使只看 positive/negative 二元分母，当前 action mask 也没有形成正 utility；并且该 appendix 按契约不能覆盖 labelable_full primary gate。

## Decision 和授权边界

| item | value |
|---|---:|
| decision_state | `18F_utility_bridge_not_supported` |
| next_allowed_requirement | `none` |
| next_allowed_requirement_scope | `none` |
| primary_operating_point_id | `defend_bottom30_continue_rest` |
| primary learned utility, robustness labelable_full | `-0.0105517` |
| all_hard_gates_pass | `False` |
| entry/exit/holding policy authorized | `False / False / False` |
| portfolio backtest / deployment / production / live trading authorized | `False / False / False / False` |

## Gate Summary

| gate | status | interpretation |
|---|---|---|
| upstream_18c_refresh_contract_gate | pass | 18C refresh 已授权 18F |
| input_artifact_gate | pass | 43 个输入 artifact 全部可读、schema/cache 通过 |
| score_matrix_join_gate | pass | score panel 与 18E matrix 一对一 join 成功 |
| oracle_denominator_contract_gate | pass | O5/O2/O4 denominator 边界通过 |
| o5_identity_replay_gate | pass | `o5_incremental = max(defend_advantage, 0)` replay 通过 |
| o5_upper_bound_contract_gate | pass | learned utility 没有超过 O5 上界 |
| operating_point_freeze_gate | pass | cutoff 全部来自 train，不在 robustness/validation 重算 |
| learned_utility_support_gate | fail | primary learned utility 为负 |
| oracle_gap_reduction_gate | fail | O5/O2 approximation ratio 均为负 |
| positive_sacrifice_gate | fail | positive sacrifice / avoidance = `1.568818` |
| payoff_retention_gate | fail | top30/top20 retention 低于门槛 |
| neutral_reconciliation_gate | pass | neutral 行数和 residual reconciliation 通过 |
| cluster_bootstrap_utility_gate | fail | 95% CI 全区间为负 |
| topk_sensitivity_gate | fail | base utility 非正，sensitivity retention 不可评估 |
| validation_stress_gate | fail | validation learned utility 仍为负 |
| binary_boundary_gate | pass | O4 binary 只作为 appendix |
| search_accounting_gate | pass | no-policy/no-backtest/no-deployment 约束通过 |

## 上游和输入审计

| audit item | observed |
|---|---:|
| input artifact count | `43` |
| input read/schema/cache gate | `pass / pass / pass` |
| 18C decision_state | `18C_payoff_state_separability_supported` |
| 18C next_allowed_requirement | `requirement_18f_payoff_state_oracle_gap_bridge.md` |
| 18C robustness payoff rank IC | `0.1253619566` |
| 18C robustness decile monotonicity Spearman | `0.7333333333` |
| 18C rank-IC cluster bootstrap CI low | `0.0882212271` |
| 18C score panel sha256 | `a3f431c8b634dcb9d24b31a5ed38574b94e7332672d4861470037837492cfc2c` |
| source 18E matrix sha256 | `03d409f73836413adc9f3bd7f3827d072c68ea4b259ffb8c221570bd882641fc` |

18C 的 ranking evidence 是成立的：rank IC、monotonicity、bootstrap CI 和 baseline delta 都通过。18F 的失败因此更有信息量：它说明“可排序”不等于“可直接作为 defend/continue utility mask”。

## Join 和 oracle replay

| check | observed |
|---|---:|
| primary identity key | `step_id\|label_id` |
| full lineage key | `step_id\|label_id\|threshold_id\|horizon_sessions\|instrument\|episode_cluster_id\|step_index\|step_start_date\|step_end_date` |
| score panel to 18E matrix join type | `one_to_one` |
| joined rows | `23405` |
| unmatched score panel rows | `0` |
| unmatched matrix rows | `0` |
| target value mismatches | `0` |
| model-ready feature mismatches | `0` |
| joined O5 max abs diff | `0.0` |
| joined O5 formula mismatches | `0` |

Oracle denominator replay 也通过：O5 和 O2 都在 `labelable_full` robustness 分母上直接可比；O4 在 `binary_primary` 分母上只能作为 appendix sanity。18F 没有把 `learned_labelable_full - O4_binary_primary` 这种混分母差值用作 primary gate。

## Train-frozen operating points

| operating_point_id | role | train defended rate | robustness defended rate | validation defended rate |
|---|---|---:|---:|---:|
| defend_bottom10_continue_rest | diagnostic_conservative | `0.100025` | `0.177885` | `0.111446` |
| defend_bottom20_continue_rest | diagnostic_conservative | `0.200000` | `0.311298` | `0.203313` |
| defend_bottom30_continue_rest | primary | `0.300025` | `0.441106` | `0.278614` |
| defend_bottom40_continue_rest | diagnostic_aggressive | `0.400000` | `0.540064` | `0.338855` |
| defend_bottom50_continue_rest | diagnostic_aggressive | `0.500025` | `0.643830` | `0.421687` |
| continue_top30_defend_rest | over_narrow_stress | `0.300025` | `0.823718` | `0.277108` |
| continue_top20_defend_rest | over_narrow_stress | `0.200000` | `0.892628` | `0.203313` |
| continue_top10_defend_rest | top10_over_narrow_stress_only | `0.100025` | `0.960737` | `0.111446` |

Primary rule 是 train q30 cutoff 下的 bottom-score defend rule。它没有在 robustness 或 validation 重算 cutoff，但 robustness 上 score 分布相对 train 明显左移，使 primary action coverage 从预期的 30% 扩到 44.11%。这会放大误防守 positive 行的成本。

## Primary utility by split

| split | rows | clusters | defended rate | learned mean | defended positive | defended negative | defended neutral | sacrifice ratio | top30 retention | top20 retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 20245 | 652 | `0.300025` | `0.000104` | `-0.013570` | `0.010763` | `0.002911` | `0.954529` | `0.763128` | `0.767350` |
| robustness | 2496 | 204 | `0.441106` | `-0.010552` | `-0.025077` | `0.010495` | `0.004031` | `1.568818` | `0.625587` | `0.636519` |
| validation | 664 | 41 | `0.278614` | `-0.001605` | `-0.016572` | `0.012069` | `0.002898` | `1.098540` | `0.787736` | `0.772414` |

Train 上 primary learned utility 只有 `0.000104`，接近零；robustness 转为明显负值；validation 仍为负但程度较轻。这不是一个“训练强、样本外弱”的可部署信号，而是 utility margin 本身过薄，并且样本外 positive sacrifice 超过 negative avoidance。

## Robustness operating-point frontier

| operating_point_id | defended rate | learned mean | sacrifice ratio | top30 retention | top20 retention |
|---|---:|---:|---:|---:|---:|
| defend_bottom10_continue_rest | `0.177885` | `-0.003599` | `1.364316` | `0.860329` | `0.848123` |
| defend_bottom20_continue_rest | `0.311298` | `-0.006464` | `1.436790` | `0.745305` | `0.750853` |
| defend_bottom30_continue_rest | `0.441106` | `-0.010552` | `1.568818` | `0.625587` | `0.636519` |
| defend_bottom40_continue_rest | `0.540064` | `-0.014390` | `1.682757` | `0.517606` | `0.529010` |
| defend_bottom50_continue_rest | `0.643830` | `-0.022375` | `1.998078` | `0.383803` | `0.387372` |
| continue_top30_defend_rest | `0.823718` | `-0.030732` | `2.135658` | `0.193662` | `0.199659` |
| continue_top20_defend_rest | `0.892628` | `-0.033222` | `2.137869` | `0.133803` | `0.138225` |
| continue_top10_defend_rest | `0.960737` | `-0.037198` | `2.213616` | `0.056338` | `0.061433` |

没有一个 robustness operating point 产生正 learned utility。更保守的 defend_bottom10 保留了较高 top payoff retention，但 utility 仍为负；更激进或 over-narrow 的规则则进一步恶化。这说明问题不是 primary cutoff 选得不够巧，而是当前 score-to-action 映射没有形成稳定的 defend/continue utility frontier。

## O5/O2 oracle gap

| oracle | oracle mean | learned mean | gap remaining | approximation ratio | upper-bound violation |
|---|---:|---:|---:|---:|---|
| O5_perfect_utility_primary | `0.029467` | `-0.010552` | `0.040019` | `-0.358080` | `False` |
| O2_dd_10pct_primary | `0.018511` | `-0.010552` | `0.029063` | `-0.570028` | `False` |

O5 upper-bound gate 通过，因为 learned utility 没有超过 oracle。问题反而是 learned action mask 在 O5/O2 同分母对照下为负。这里不能用 O4 binary oracle 去解释 primary utility，也不能用二元 appendix 的任何结果覆盖 labelable_full 失败。

## Six-cell decomposition

Robustness primary 的 direct incremental-return 分解如下：

| action bucket | label class | rows | row share | sum incremental | full-denom mean | positive opportunity cost | negative avoidance gain | neutral contribution | continued positive retained | continued negative leakage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| defended | positive | 519 | `0.207933` | `-62.593291` | `-0.025077` | `0.025077` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |
| defended | negative | 298 | `0.119391` | `26.194751` | `0.010495` | `0.000000` | `0.011954` | `0.000000` | `0.000000` | `0.000000` |
| defended | neutral | 284 | `0.113782` | `10.061538` | `0.004031` | `0.000000` | `0.000000` | `0.004031` | `0.000000` | `0.000000` |
| continued | positive | 827 | `0.331330` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.041987` | `0.000000` |
| continued | negative | 228 | `0.091346` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.008808` |
| continued | neutral | 340 | `0.136218` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |

解释：

- Defended positive 的机会成本 `0.025077` 是最大单项拖累。
- Defended negative 的避免收益 `0.010495` 与 defended neutral 的 `0.004031` 合计约 `0.014526`，不足以覆盖 positive cost。
- Continued positive retained 为 `0.041987`，说明大量正 payoff opportunity 被正确保留；但 primary defend mask 中误防守的 positive 已经足以把整体 utility 拉负。
- Continued negative leakage 为 `0.008808`，表示仍有部分 negative 行没有被防守；但进一步扩大防守会更严重牺牲 positive payoff，从 robustness frontier 看并不可取。

## Cluster bootstrap

| metric | value |
|---|---:|
| split_bucket | `robustness` |
| cluster_key | `episode_cluster_id` |
| episode clusters | `204` |
| bootstrap_resample_n | `2000` |
| valid_bootstrap_resample_n | `2000` |
| learned mean | `-0.010552` |
| 95% CI low | `-0.014387` |
| 95% CI high | `-0.007484` |
| status | `fail` |

Bootstrap CI 全区间为负，因此不能把 primary failure 解释成偶然 cluster composition。这个结果支持一个更严格的解释：18C score 在当前 action mapping 下稳定地产生负 utility。

## Top-k and family sensitivity

| sensitivity_id | removed n | family | sensitivity learned mean | 95% CI low | 95% CI high | status |
|---|---:|---|---:|---:|---:|---|
| top1_abs_coefficient_removed | 1 | mixed | `-0.016227` | `-0.019910` | `-0.012630` | not_evaluable |
| top3_abs_coefficient_removed | 3 | mixed | `-0.013950` | `-0.018071` | `-0.010248` | not_evaluable |
| top5_abs_coefficient_removed | 5 | mixed | `-0.012234` | `-0.014802` | `-0.009746` | not_evaluable |
| family_F4_removed | 5 | F4 | `-0.011724` | `-0.015296` | `-0.008594` | not_evaluable |
| family_M1_removed | 8 | M1 | `-0.007850` | `-0.011231` | `-0.004932` | not_evaluable |
| family_M2_removed | 7 | M2 | `-0.012501` | `-0.016615` | `-0.008914` | not_evaluable |
| family_M3_removed | 5 | M3 | `-0.011921` | `-0.015711` | `-0.008687` | not_evaluable |
| family_M5_removed | 6 | M5 | `-0.010717` | `-0.014265` | `-0.007596` | not_evaluable |

Base learned utility 为 `-0.010552`，因此 retention rate 按需求定义不可评估。即便如此，敏感性读数仍有诊断价值：移除 M1 后结果最接近 0，但仍为负；移除 top1 反而更差。这说明当前失败不是由某一个 top coefficient 的异常支配造成，也不是简单移除某个 feature family 就能变成 utility-supporting mask。

## Validation stress

| metric | value |
|---|---:|
| validation rows | `664` |
| validation clusters | `41` |
| validation learned mean | `-0.001605` |
| validation O5 approximation ratio | `-0.054484` |
| validation top30 retention | `0.787736` |
| validation top20 retention | `0.772414` |
| sign reversal | `False` |
| status | `fail` |

Validation stress 的含义要谨慎读：top payoff retention 并不差，失败来自 learned utility 仍为负。`sign_reversal = False` 不是好消息，因为 robustness 本身也是负值；validation 只是“没反转”，不是“支持 policy preflight”。

## Binary appendix

| metric | value |
|---|---:|
| binary denominator rows | `1872` |
| primary learned binary mean | `-0.019444` |
| O4 binary primary oracle mean | `0.024681` |
| O4 binary gap remaining | `0.044125` |
| O4 binary approximation ratio | `-0.787796` |
| role | `appendix_sanity_only` |

Binary appendix 没有给出相反证据。即使在 positive/negative 二元分母上，primary learned mask 仍为负；并且 O4 binary_primary 不能被拿来抵消 labelable_full O5/O2 的失败。

## AFML interpretation

18C refresh 证明了 payoff-state score 具有可排序的 representation value，但 18F 证明它还不是 action-value utility evidence。AFML 上，这个结果应被解释为：当前表征可以继续作为候选 state/ranking signal 或 meta-label research input，但不能直接升级为 defend/continue policy preflight。

更具体地说，当前 score 学到的“payoff ranking”与“防守动作应该避开什么”之间存在错位。Bottom-score 区域确实包含一些 negative/neutral 可防守收益，但同时包含过多 positive continuation opportunity。由于 positive sacrifice 超过 negative avoidance，任何直接 threshold mask 都会把 ranking evidence 转换成负 utility。

下一步不应是调参寻找一个能过关的 threshold，而应回到 action-value 定义本身：

1. 区分 payoff ranking 与 defend action label。ranking score 可以保留为 state representation，但 defend/continue 需要单独的 utility-aware 目标。
2. 检查 robustness 上 bottom-score 分布迁移为何使 defended rate 从 train 的 30% 扩到 44.11%。
3. 对 defended-positive false positives 做特征剖面，尤其是被防守但后续 high payoff 的 519 行。
4. 重新设计损失函数或标签，使 positive opportunity cost 在训练目标中显式进入，而不是事后由 threshold gate 才发现。

在这些问题解决前，18F 的正确收口是 `18F_utility_bridge_not_supported`，且 `next_allowed_requirement = none`。
