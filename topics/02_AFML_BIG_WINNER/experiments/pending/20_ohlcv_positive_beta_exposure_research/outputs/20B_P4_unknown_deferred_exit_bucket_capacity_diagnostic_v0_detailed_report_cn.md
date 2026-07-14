# 20B-P4-CAP：Unknown 延迟退出与持仓容量敏感性中文详细报告

> 本文是 `20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_v0` 的中文解释性 companion report。正式机器输出位于同名 run bundle 内。本文不修改 sealed `20B_v5`，也不改变新 run 的 manifest/hash。

## 1. 执行结论

本轮已经实际完成，而不是 requirement-only：

```text
decision_state = complete_descriptive_capacity_diagnostic
capacity_set = 5|10|20|30|40|50
signal_month_n = 63
held_unknown_case_n = 4
resolved_deferred_exit_n = 4
bridge_lineage_mismatch_n = 0
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
deployment_authorized = false
```

核心结果是：

1. 不再让未持有的 middle unknown 污染整个 P4 月份后，六档容量均恢复到 `63` 个可评价形成月；
2. 六档 full-sample Top-N 等权收益均为正，`N=30/40/50` 高于 `N=5/10/20`；
3. 但所有容量的 early fold 都为负，所有容量的 late fold 都为正，P4 仍存在明显时期翻转；
4. 实际进入 Top-N 的 unknown 只有 `4` 个股票-形成月，全部在第二自然月找到退出价；
5. deferred exits 对任一容量 full 月均收益的最大贡献仅 `0.0108` 个百分点，容量差异不是由这4个特殊案例主导；
6. `N=50` 的 full 均值最高，但容量集合是在看到 v5 outcome 后提出，不能把它升级为“最优容量”。

## 2. 与 sealed v5 的关系

本轮只复用 v5 已物化的 P4 signal：

```text
arm_id = P4_RESMOM_R2_MARKET_ONLY_ADAPTATION
semantic_track = project_sequential_market_residual_primary
score = raw_signal
formation = t-11 ... t-1 residual momentum
market model = sequential prior-36-month OLS
```

本轮没有：

- 重新估计 P4 market beta；
- 改变11个月 residual score；
- 调整 signal-eligible universe；
- 修改 v5 的43个月官方 readout；
- 把本轮结果写回 v5 decision 或 manifest。

本轮是 outcome 已知后的 follow-up sensitivity，因此固定属于：

```text
historical_sample_role = design_contaminated_followup
inference_role = descriptive_not_support
```

## 3. “桶容量”的精确定义

这里的 `5/10/20/30/40/50` 是每个极端桶持有的股票数量，不是把横截面分成5、10、20、30、40、50个 quantile。

每个 decision month 机械执行：

```text
按 raw_signal 降序、instrument_id 升序稳定排序
前 N 名 -> favorable_top_n
后 N 名 -> unfavorable_bottom_n
其他股票 -> not_selected_middle
Top-N / Bottom-N 均等权
```

Primary portfolio 是 long-only `favorable_top_n`。Bottom-N 仅用于排序 morphology comparator，不代表实际做空组合。

## 4. 新 Unknown 规则

### 4.1 Middle unknown

如果 unknown 不在 Top-N 或 Bottom-N：

```text
not_selected_middle
-> 没有持仓
-> 不进入收益计算
-> 不影响 Top-N 月份可评价性
```

这修复了 v5 中“middle bucket 一只 unknown 令所有10个 decile 同月删除”的非线性放大。

### 4.2 Bottom-N unknown

如果 unknown 落在 Bottom-N：

```text
从 bottom comparator 删除
对剩余 bottom 股票重新等权
记录 nominal N / effective N / deleted unknown N
```

这是用户指定的 comparator sensitivity，不是可交易 short portfolio 声明。

### 4.3 Top-N unknown

如果 unknown 已进入 Top-N，它是形成时真实持仓，不能事后删除并重分权重：

```text
t     ：形成并持有，原始权重 1/N
t+1   ：月末 outcome unknown，不强行删除
t+2   ：第二自然月首个可得 qfq close 卖出
return：exit_mark_t+2 / formation_mark_t - 1
```

因此含 deferred exit 的 formation cohort 混合了一个月和约两个月持有期，只能解释为：

```text
formation_cohort_deferred_exit_gross_return
```

不能解释成普通独立月收益、逐月 NAV 或成本后组合收益。

## 5. 数据桥与可验证性

原 v5 qfq/status 输入快照目前不在工作区，因此4个真实 held unknown 使用当前腾讯 qfq 日线补充退出桥。

固定标记：

```text
provider = tencent_ifzq_qfq
mixed_provider_bridge_sensitivity = true
```

每个接口原始 JSON、URL、访问时间和 payload SHA-256 均已保存在新 run 的 `source/` 目录。

四个案例的“首月最后交易日期”与 v5 `outcome_resolution_audit` 全部一致，`bridge_lineage_mismatch_n=0`。这只验证日期断点一致，不代表两个 provider 的历史调整因子完全等同。

## 6. Full sample 容量结果

Primary weighting 均为等权：

| Top-N容量 | 可评价月 | Top-N月均 | 月收益>0 | Bottom-N均值 | Top-Bottom | Top held unknown | Bottom删除unknown | Middle忽略unknown |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 63 | +0.2426% | 49.21% | +0.0982% | +0.1444% | 0 | 1 | 28 |
| 10 | 63 | +0.2890% | 47.62% | -0.2131% | +0.5021% | 0 | 1 | 28 |
| 20 | 63 | +0.2074% | 41.27% | -0.2426% | +0.4500% | 0 | 1 | 28 |
| 30 | 63 | +0.4382% | 44.44% | -0.2631% | +0.7013% | 0 | 1 | 28 |
| 40 | 63 | +0.4948% | 47.62% | -0.2990% | +0.7937% | 1 | 2 | 26 |
| 50 | 63 | +0.5240% | 44.44% | -0.3120% | +0.8361% | 4 | 2 | 23 |

### 6.1 如何理解容量形态

- `N=5 -> 10`：Top-N 均值上升 `+0.0464` 个百分点/月；
- `N=10 -> 20`：均值反而下降 `-0.0816` 个百分点/月；
- `N=20 -> 30`：均值上升 `+0.2308` 个百分点/月；
- `N=30 -> 40`：再上升 `+0.0566` 个百分点/月；
- `N=40 -> 50`：再上升 `+0.0293` 个百分点/月。

所以结果不是“容量越大收益严格单调越高”。更准确的形态是：

```text
5/10/20：约 +0.21% 至 +0.29%/形成月
30/40/50：约 +0.44% 至 +0.52%/形成月
```

主要增量出现在从20只扩展到30只的 shell。

## 7. Early / Late 稳定性

| Top-N容量 | Early N | Early Top-N | Early spread | Late N | Late Top-N | Late spread |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 32 | -0.9513% | +0.3172% | 31 | +1.4750% | -0.0338% |
| 10 | 32 | -0.8489% | +0.3855% | 31 | +1.4637% | +0.6226% |
| 20 | 32 | -0.7700% | +0.3470% | 31 | +1.2163% | +0.5564% |
| 30 | 32 | -0.4580% | +0.6204% | 31 | +1.3632% | +0.7848% |
| 40 | 32 | -0.3922% | +0.4934% | 31 | +1.4103% | +1.1038% |
| 50 | 32 | -0.3174% | +0.5687% | 31 | +1.3926% | +1.1120% |

最重要的观察不是 full-sample 最佳容量，而是：

```text
所有容量 early Top-N < 0
所有容量 late Top-N > 0
```

容量扩大能缓解 early 负收益的幅度，但不能消除方向翻转。因此，新 unknown 规则解决了月份可评价率，却没有解决 P4 的时间状态依赖。

## 8. HAC 诊断

Full-sample Top-N HAC p-value：

| N | HAC t | HAC p |
|---:|---:|---:|
| 5 | 0.235 | 0.814 |
| 10 | 0.322 | 0.747 |
| 20 | 0.274 | 0.784 |
| 30 | 0.546 | 0.585 |
| 40 | 0.663 | 0.507 |
| 50 | 0.782 | 0.434 |

Full-sample spread HAC p-value 从 N=5 的 `0.903` 降至 N=50 的 `0.284`，但没有一档达到普通5%水平。

HAC 仅为 design-only 描述。本轮既不是预注册容量检验，也没有多重比较授权，因此不能根据最小 p-value 选择容量。

## 9. 四个 Top-N deferred exits

| 股票 | 形成日 | 受影响容量 | 形成价 | 第二自然月退出日 | 退出价 | Deferred return | 持有日历日 |
|---|---|---|---:|---|---:|---:|---:|
| SH600372 | 2022-04-29 | 50 | 16.474 | 2022-06-13 | 21.404 | +29.9259% | 45 |
| SH601298 | 2023-05-31 | 50 | 6.227 | 2023-07-03 | 5.847 | -6.1025% | 33 |
| SZ002064 | 2024-09-30 | 50 | 8.100 | 2024-11-04 | 7.790 | -3.8272% | 35 |
| SZ002049 | 2025-11-28 | 40/50 | 75.754 | 2026-01-15 | 86.384 | +14.0323% | 48 |

数量关系：

```text
N <= 30：没有 held unknown
N = 40 ：1 个 held unknown
N = 50 ：4 个 held unknown
```

这些 deferred positions 对 full 月均的贡献：

```text
N=40：约 +0.0056 个百分点/月
N=50：约 +0.0108 个百分点/月
```

所以 `N=40/50` 的较高均值并不是延迟退出个案机械抬高造成的。

## 10. 相对 N=10 的共同月份差异

所有配对都使用相同63个 decision months：

| 容量N | Top-N减N10 | Spread减N10 |
|---:|---:|---:|
| 5 | -0.0464pp/月 | -0.3577pp/月 |
| 10 | 0 | 0 |
| 20 | -0.0816pp/月 | -0.0521pp/月 |
| 30 | +0.1491pp/月 | +0.1991pp/月 |
| 40 | +0.2057pp/月 | +0.2916pp/月 |
| 50 | +0.2350pp/月 | +0.3339pp/月 |

N=30–50 相对 N=10 的 full-sample paired delta 为正，但这仍是 outcome-known search，不能作为选择30、40或50只的正式证据。

## 11. 与 v5 官方 P4 readout 的差异

v5 官方 P4 使用：

```text
10个decile
要求所有10个decile同月完整
43个可评价月
```

其 official full readout 为：

```text
favorable = +0.5798%
spread = +1.6189%
```

本轮最接近原 decile 容量的是 N=40，但使用全部63个月：

```text
Top-40 = +0.4948%
Top40-Bottom40 = +0.7937%
```

两者不能直接当作纯粹 unknown-policy delta，因为同时存在：

1. 原 decile 每月股票数随 signal N 变化，N=40是固定容量；
2. v5 只保留所有10个decile都完整的43个月；
3. 本轮只要求实际持有Top-N可退出，Bottom-N允许删除unknown；
4. held unknown 使用变长持有期和补充provider bridge。

但方向上可以确认：恢复被 middle unknown 删除的月份后，spread 明显低于 v5 的43个月条件样本，early Top-N 也重新变为负值。

## 12. 研究判断

### Finding 1：Unknown 主要是 evaluability 问题，不是持仓大面积失控

最多50只的 Top-N 中，63个月只有4个 held unknown。原 v5 丢失20个月，主要原因是 middle/bottom unknown 被全10桶共同完整规则放大。

### Finding 2：30–50只在 full sample 更强，但不是稳定最优

N=30/40/50 的 full 均值高于 N=5/10/20，但不存在严格单调关系，且这些容量在 early 仍全部为负。

### Finding 3：P4 的真正风险是 regime instability

无论容量如何，early/late 都发生同方向翻转。扩大容量降低集中度，却没有建立跨时期正收益。

### Finding 4：更合理的下一步不是继续搜索 N

如果继续研究，应在新的 forward/preoutcome contract 中预先选择少量容量，例如固定 `N=30/40/50` 或指定单一容量，并建立原生 stateful daily NAV、停牌持仓和退出规则；不应在当前63个月上继续搜索35、45、60等容量。

## 13. Evidence 与文件

正式 run bundle：

- `20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_v0/20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_report.md`
- `.../historical/p4_capacity_assignment.parquet`
- `.../historical/p4_capacity_monthly_returns.csv.gz`
- `.../historical/p4_capacity_summary.csv`
- `.../historical/p4_capacity_paired_delta_vs_10.csv`
- `.../historical/p4_capacity_shell_attribution.csv`
- `.../historical/p4_deferred_exit_audit.csv`
- `.../source/tencent_qfq_bridge_*.json`
- `.../manifest_20b_p4_capacity.json`
- `.../output_hashes_20b_p4_capacity.json`

Requirement 与实现：

- `requirement_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.md`
- `configs/config_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.yaml`
- `src/run_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.py`
- `tests/test_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.py`

固定授权边界：

```text
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
20C_execution_authorized = false
policy_training_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```
