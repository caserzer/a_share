# 20B-P4-CAP unknown 延迟退出与持仓容量诊断

## 1. 状态

```text
decision_state = complete_descriptive_capacity_diagnostic
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
deployment_authorized = false
```

本轮复用 sealed v5 P4 score，以等权 Top-N/Bottom-N 重新形成容量桶。`N` 是股票数，不是 quantile 数量。包含延迟退出的形成批次是 variable-horizon cohort diagnostic，不是普通月度 NAV。

## 2. 关键 findings

- 六档容量的 full Top-N 均值都为正；最高为 `N=50` 的 `+0.5240%`；
- early 六档是否全负：`true`；late 六档是否全正：`true`，说明主要结论仍是明显的时期翻转；
- 实际 held unknown 只有 `4` 个股票-形成月；延迟退出对任一容量 full 月均的最大绝对贡献仅 `0.0108` 个百分点；
- 因此容量结果主要来自扩大/收缩 Top-N 成员，而不是4个 deferred exits 主导；
- 本轮是 outcome 已知后的容量搜索，不能把 `N=50` 写成最优容量或用于参数选择。

## 3. Full sample 容量结果

| bucket_capacity_n | top_evaluable_month_n | top_mean | top_positive_rate | bottom_mean | spread_mean | top_deferred_position_n | bottom_deleted_unknown_n | middle_ignored_unknown_n |
|---|---|---|---|---|---|---|---|---|
| 5 | 63 | +0.2426% | +49.2063% | +0.0982% | +0.1444% | 0 | 1 | 28 |
| 10 | 63 | +0.2890% | +47.6190% | -0.2131% | +0.5021% | 0 | 1 | 28 |
| 20 | 63 | +0.2074% | +41.2698% | -0.2426% | +0.4500% | 0 | 1 | 28 |
| 30 | 63 | +0.4382% | +44.4444% | -0.2631% | +0.7013% | 0 | 1 | 28 |
| 40 | 63 | +0.4948% | +47.6190% | -0.2990% | +0.7937% | 1 | 2 | 26 |
| 50 | 63 | +0.5240% | +44.4444% | -0.3120% | +0.8361% | 4 | 2 | 23 |

## 4. Full / early / late

| bucket_capacity_n | month_scope | top_evaluable_month_n | top_mean | spread_mean |
|---|---|---|---|---|
| 5 | full | 63 | +0.2426% | +0.1444% |
| 5 | early | 32 | -0.9513% | +0.3172% |
| 5 | late | 31 | +1.4750% | -0.0338% |
| 10 | full | 63 | +0.2890% | +0.5021% |
| 10 | early | 32 | -0.8489% | +0.3855% |
| 10 | late | 31 | +1.4637% | +0.6226% |
| 20 | full | 63 | +0.2074% | +0.4500% |
| 20 | early | 32 | -0.7700% | +0.3470% |
| 20 | late | 31 | +1.2163% | +0.5564% |
| 30 | full | 63 | +0.4382% | +0.7013% |
| 30 | early | 32 | -0.4580% | +0.6204% |
| 30 | late | 31 | +1.3632% | +0.7848% |
| 40 | full | 63 | +0.4948% | +0.7937% |
| 40 | early | 32 | -0.3922% | +0.4934% |
| 40 | late | 31 | +1.4103% | +1.1038% |
| 50 | full | 63 | +0.5240% | +0.8361% |
| 50 | early | 32 | -0.3174% | +0.5687% |
| 50 | late | 31 | +1.3926% | +1.1120% |

## 5. Top-N unknown 延迟退出

| instrument_id | decision_date | affected_capacities | formation_mark | forced_exit_date | forced_exit_mark | deferred_gross_return | holding_calendar_days | deferred_resolution |
|---|---|---|---|---|---|---|---|---|
| SH600372 | 2022-04-29 00:00:00 | 50 | 16.4740 | 2022-06-13 00:00:00 | 21.4040 | +29.9259% | 45 | resolved_first_mark_in_t_plus_2 |
| SH601298 | 2023-05-31 00:00:00 | 50 | 6.2270 | 2023-07-03 00:00:00 | 5.8470 | -6.1025% | 33 | resolved_first_mark_in_t_plus_2 |
| SZ002049 | 2025-11-28 00:00:00 | 40|50 | 75.7540 | 2026-01-15 00:00:00 | 86.3840 | +14.0323% | 48 | resolved_first_mark_in_t_plus_2 |
| SZ002064 | 2024-09-30 00:00:00 | 50 | 8.1000 | 2024-11-04 00:00:00 | 7.7900 | -3.8272% | 35 | resolved_first_mark_in_t_plus_2 |

补充桥使用当前腾讯 qfq 日线，只服务于实际进入 Top-N 的 v5 unknown。它与 v5 原输入不是同一冻结快照，因此结果固定标记 mixed-provider bridge sensitivity。

## 6. 相对 N=10 的共同月份差异

| bucket_capacity_n | paired_top_month_n | top_delta_mean | paired_spread_month_n | spread_delta_mean |
|---|---|---|---|---|
| 5 | 63 | -0.0464% | 63 | -0.3577% |
| 10 | 63 | +0.0000% | 63 | +0.0000% |
| 20 | 63 | -0.0816% | 63 | -0.0521% |
| 30 | 63 | +0.1491% | 63 | +0.1991% |
| 40 | 63 | +0.2057% | 63 | +0.2916% |
| 50 | 63 | +0.2350% | 63 | +0.3339% |

## 7. 相邻容量 shell

| inner_capacity_n | outer_capacity_n | paired_month_n | outer_minus_inner_mean | incremental_shell_mean |
|---|---|---|---|---|
| 5 | 10 | 63 | +0.0464% | +0.3354% |
| 10 | 20 | 63 | -0.0816% | +0.1258% |
| 20 | 30 | 63 | +0.2308% | +0.8997% |
| 30 | 40 | 63 | +0.0566% | +0.6646% |
| 40 | 50 | 63 | +0.0293% | +0.6411% |

## 8. 解释边界

- middle unknown 不再污染 long-only Top-N；bottom unknown 只在 comparator 内删除并重新等权；
- Top-N unknown 保留原始 `1/N` 权重，并在第二自然月首个 mark 退出；
- 没有成本、next-open、现金账户或逐日 NAV；
- 本轮容量集合是在 v5 outcome 已知后提出，不能产生历史支持或授权。
