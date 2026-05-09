# Requirement 05 实验报告：Daily Continuation / Profit Protection Prephase

## 1. 执行结论

- 本次只执行 R05-pre deterministic-only mini-phase；`full_model_stage_executed=False`，`model_training_executed=False`，没有训练或选择任何模型。
- 结果状态：`selection_status=failed_no_continuation_policy_edge`，`next_phase_proceed_status=failed_no_continuation_policy_edge`。
- 推荐动作：`recommendation=stop_due_to_insufficient_selection_power`；`full_model_stage_allowed=False`。
- 三条简单 profit-protection / continuation policy 都没有通过 validation Track A、Track B 和 matched-random p95 gate。
- 核心发现不是 winner capture 完全无效，而是捕获更多 winner 的代价主要来自更长资金占用和更差尾部风险：validation strict capture 从 R03 的 2 个提升到 5 个，但 p05 return 恶化约 1.6-1.9pct，capital occupancy 提升到 2.56-3.32 倍。
- 因此，本阶段证据支持“EP2 entry 对短周期事件 sleeve 有价值”，但不支持“当前 entry 已经足够特定，可以直接作为长周期 big-winner holding entry”。

## 2. 阶段边界与模型审计

- implementation_mode: `deterministic_prephase_only`
- selected_policy_id: `none`
- model_policy_candidate_count: `0`
- deterministic_policy_candidate_count: `3`，只包含三条 deterministic profit-protection rules；R03/R04 replay 和 matched random 不计入候选数。
- R05-pre 的用途是低成本判断 post-exposure policy 是否有足够 edge；当前结果不允许进入 R05 full-model stage。

## 3. 样本量与 selection power

| split      |   exposed_episode_count |   big_winner_episode_count_50h120 |   actionable_big_winner_episode_count_50h120 |   baseline_strict_captured_big_winner_count_50h120 |   actionable_uncaptured_big_winner_count_50h120 | deterministic_stage_allowed   | full_model_stage_allowed   | failure_reason                       |
|:-----------|------------------------:|----------------------------------:|---------------------------------------------:|---------------------------------------------------:|------------------------------------------------:|:------------------------------|:---------------------------|:-------------------------------------|
| robustness |                     149 |                               127 |                                           46 |                                                  3 |                                              43 | True                          | True                       |                                      |
| train      |                     236 |                               185 |                                           73 |                                                  6 |                                              67 | True                          | True                       |                                      |
| validation |                     104 |                                43 |                                           16 |                                                  2 |                                              14 | True                          | False                      | insufficient_full_model_sample_power |

解释：validation 只有 104 个 exposed episodes、43 个 50h120 big-winner episodes、16 个 actionable big-winner episodes。这个规模足够跑三条 deterministic policy 的 prephase，但不足以支撑多模型和大 grid 的 full-model stage，因此 validator 按合同保持 fail-closed。

## 4. 三条 deterministic policy 的定义

| policy_id                      | 规则                                                                                                             | 意图                                                                  |
|:-------------------------------|:-----------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------|
| profit_lock_rule_simple        | 从首次 exposure 起浮盈达到 +10% 后，下一交易日把仓位降到 0.30；之后若从峰值利润回撤 6pct，则下一交易日全退。     | 先锁住大部分利润，再给剩余仓位留一点上行空间。                        |
| trailing_stop_rule_simple      | 从首次 exposure 起浮盈达到 +10% 后，启用 trailing stop，止损线为历史最高收盘价的 92%；收盘跌破后下一交易日全退。 | 不主动降仓，用移动止损保护已出现的 winner。                           |
| partial_exit_after_profit_rule | 从首次 exposure 起浮盈达到 +12% 后，下一交易日卖出一半；剩余半仓沿用 trailing stop。                             | 在 profit lock 和纯 trailing 之间折中，试图同时保留利润和一部分上行。 |

这三条都不是重新选 entry，而是在 R03 confirm-add 后改变持有 / 退出规则。它们共同测试一个问题：如果 entry 之后出现利润，能否用简单规则保护利润并保留 winner 上行。

## 5. Validation 主结果

| policy_id                      |   mean_return |   p05_return |   MAE_mean |   strict_capture_count |   strict_capture_rate |   exposure_weighted_capture |   partial_capture_rate |   capital_occupancy |   exposure_day_multiple |   matched_p50_diff |   matched_p95_diff |
|:-------------------------------|--------------:|-------------:|-----------:|-----------------------:|----------------------:|----------------------------:|-----------------------:|--------------------:|------------------------:|-------------------:|-------------------:|
| R03_original_H10_replay        |      0.008592 |    -0.007543 |  -0.003362 |                      2 |              0.046512 |                    0.030233 |               0.372093 |             1.39906 |                 1       |                    |                    |
| profit_lock_rule_simple        |      0.009393 |    -0.023672 |  -0.005103 |                      5 |              0.116279 |                    0.034884 |               0.372093 |             3.5812  |                 2.55972 |           0.001023 |          -0.002617 |
| trailing_stop_rule_simple      |      0.009453 |    -0.02504  |  -0.005017 |                      5 |              0.116279 |                    0.1      |               0.372093 |             4.64474 |                 3.3199  |           0.000924 |          -0.001501 |
| partial_exit_after_profit_rule |      0.00981  |    -0.026198 |  -0.005424 |                      5 |              0.116279 |                    0.05     |               0.372093 |             4.54511 |                 3.24869 |           0.001451 |          -0.001504 |

R03 baseline 的 validation strict capture 只有 2/43，即 0.046512；三条 policy 都提升到 5/43，即 0.116279。这个提升是真实存在的，但不是免费提升。

## 6. 相对 R03 的 validation 差异

| policy_id                      |   mean_diff_vs_R03 |   p05_diff_vs_R03 |   MAE_diff_vs_R03 |   strict_count_diff |   strict_rate_diff |   weighted_capture_diff |   exposure_multiple |   random_p95_diff |
|:-------------------------------|-------------------:|------------------:|------------------:|--------------------:|-------------------:|------------------------:|--------------------:|------------------:|
| profit_lock_rule_simple        |           0.000801 |         -0.016129 |         -0.001741 |                   3 |           0.069767 |                0.004651 |             2.55972 |         -0.002617 |
| trailing_stop_rule_simple      |           0.000862 |         -0.017497 |         -0.001654 |                   3 |           0.069767 |                0.069767 |             3.3199  |         -0.001501 |
| partial_exit_after_profit_rule |           0.001218 |         -0.018656 |         -0.002062 |                   3 |           0.069767 |                0.019767 |             3.24869 |         -0.001504 |

Track A 要求 strict capture count 至少增加 3 个，且 p05 deterioration 不低于 -0.003000、exposure-day multiple 不超过 3.000000、matched-random p95 shortfall 不低于 -0.001000。

## 7. Gate 分解

| policy_id                      | Track_A_strict_count   | Track_A_p05   | Track_A_exposure_days   | Track_A_matched_p95   | Track_A_overall   | Track_B_mean   | Track_B_p05   | Track_B_MAE   | Track_B_matched_p95   | Track_B_overall   |
|:-------------------------------|:-----------------------|:--------------|:------------------------|:----------------------|:------------------|:---------------|:--------------|:--------------|:----------------------|:------------------|
| profit_lock_rule_simple        | 是                     | 否            | 是                      | 否                    | 否                | 否             | 否            | 否            | 否                    | 否                |
| trailing_stop_rule_simple      | 是                     | 否            | 否                      | 否                    | 否                | 否             | 否            | 否            | 否                    | 否                |
| partial_exit_after_profit_rule | 是                     | 否            | 否                      | 否                    | 否                | 是             | 否            | 否            | 否                    | 否                |

细看 gate 分解后，失败不是因为 winner capture 没提升：三条规则的 strict_count_diff 都是 +3，超过 Track A 最小要求。真正的硬失败来自：

- p05 return 明显恶化：profit_lock -0.016129，trailing -0.017497，partial_exit -0.018656，远低于 Track A 允许的 -0.003000。
- trailing_stop 和 partial_exit 的 exposure_day_multiple 分别为 3.319898 和 3.248690，超过 3.0 上限；profit_lock 虽然 exposure multiple 为 2.559721，但 p05 仍失败。
- Track B 要求作为 risk/profit-protection overlay 时 p05 和 MAE 必须改善；三条规则的 p05 和 MAE 都是恶化，不满足 risk-filter 方向。
- matched-random p95 gate 也失败：三条 policy 的 real-minus-random-p95 分别为 -0.002617、-0.001501、-0.001504，低于 -0.001000 阈值。

## 8. matched-random p95 是否过严

matched-random p95 gate 的确偏保守，特别是在 validation 样本只有 104 个 exposed episodes 时，它更像 search-bias guard，而不是主要经济结论。即使临时放松这个 gate，三条 policy 仍会因为 p05 deterioration 或 exposure-day multiple 失败。因此当前 no-go 不是单纯由 matched-random p95 造成。

更准确的解释是：这些规则通过延长实际持有和放大 winner 暴露提高 capture，但同时把更多 episode 暴露在后续回撤中，尾部亏损分位被拉坏。这个失败形态说明固定利润阈值 + 固定 trailing / partial exit 的信息利用太粗，不能证明 continuation edge。

## 9. Robustness 观察

| policy_id                      |   mean_return |   p05_return |   MAE_mean |   strict_capture_count |   strict_capture_rate |   exposure_weighted_capture |   partial_capture_rate |   capital_occupancy |   exposure_day_multiple |   matched_p50_diff |   matched_p95_diff |
|:-------------------------------|--------------:|-------------:|-----------:|-----------------------:|----------------------:|----------------------------:|-----------------------:|--------------------:|------------------------:|-------------------:|-------------------:|
| R03_original_H10_replay        |      0.005769 |    -0.018225 |  -0.00398  |                      3 |              0.023622 |                    0.01811  |               0.362205 |             1.34909 |                 1       |                    |                    |
| profit_lock_rule_simple        |      0.012163 |    -0.021311 |  -0.004807 |                     12 |              0.094488 |                    0.028346 |               0.362205 |             3.1687  |                 2.34877 |           0.006486 |           0.003997 |
| trailing_stop_rule_simple      |      0.013668 |    -0.015907 |  -0.004552 |                     14 |              0.110236 |                    0.099213 |               0.362205 |             3.89429 |                 2.8866  |           0.008039 |           0.005791 |
| partial_exit_after_profit_rule |      0.013535 |    -0.018141 |  -0.004498 |                     15 |              0.11811  |                    0.053543 |               0.362205 |             3.29604 |                 2.44316 |           0.007502 |           0.005156 |

robustness 上三条 policy 的 mean 都高于 R03 baseline，matched-random p95 也为正，但这不能反推 validation selection。R05 合同要求 validation-only selection，robustness 只做 holdout。validation 与 robustness 的方向差异说明 regime 可能存在，但当前 regime audit 只达到 weak diagnostic，不能作为进入 full model 的充分理由。

## 10. Regime audit

- regime_mismatch_status: `weak_diagnostic`
- regime_mismatch_confidence: `medium`
- R04 的 fixed holding schedules 在 validation 与 robustness 间有反转信号，但 condition B 未触发，因此不是 blocking。
- 这提示后续如果继续研究，应优先做 regime-conditional requirement，而不是直接扩大 R05 模型自由度。

## 11. 关于 entry 是否不够特定

当前数据更像是在说：R02/R03 的 entry 能找到短周期事件后的可执行 probe/confirm 机会，但它不是一个足够特定的长周期 winner-entry。若 entry 对长周期 winner 足够特定，延长持有或利润保护应当至少做到三点：capture 上升、mean 上升、p05 / MAE 不明显恶化。实际结果是 capture 上升、mean 只小幅上升，但 p05 大幅恶化，并且资金占用显著增加。

所以问题不只是 exit 规则太简单，也包括 entry 标签和 entry 条件没有显式识别“值得继续持有的 episode”。时间长度不应是策略核心参数，它更应该是 continuation / risk model 优化后自然产生的结果。

## 12. 研究建议

- 不建议启动当前 R05 full-model stage；validation 样本和 deterministic prephase 证据都不足。
- 不建议继续调固定 H、固定盈利阈值或固定 trailing 参数来寻找长持 winner；这会扩大 search space，但不会解决 entry specificity。
- 若继续，应先定义新的 winner-quality / continuation / regime filter requirement，只允许 as-of daily information，目标是判断“今天是否仍值得承担下一段风险”，而不是直接调持仓天数。
- 在没有新 entry/continuation 证据前，EP2 更适合保留为短周期 event sleeve，或作为后续 BaseRate / risk-filter overlay 的输入，而不是冻结为长周期 big-winner holding system。

## 13. 关键产物

- `requirement_05_sample_power_audit.csv`：样本量与 full-model stage 许可审计。
- `requirement_05_deterministic_prephase_results.csv`：三条 deterministic policy 的 split-level 指标。
- `requirement_05_gate_audit.csv`：Track A / Track B / matched-random gate 结果。
- `requirement_05_R04_regime_audit.csv`：R04 regime reversal 的弱诊断。
- `requirement_05_selected_policy.csv`：最终未选择 policy，未允许 full model。
