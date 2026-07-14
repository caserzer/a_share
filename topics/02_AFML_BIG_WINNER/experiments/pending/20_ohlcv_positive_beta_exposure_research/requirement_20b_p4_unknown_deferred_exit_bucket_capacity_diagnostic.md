# Requirement 20B-P4-CAP：P4 unknown 延迟退出与持仓容量敏感性诊断

## 1. 目的与研究边界

本 requirement 建立一个独立于 sealed `20B_v5` 的只读 follow-up diagnostic，回答两个问题：

1. P4 market-only residual momentum 的 `unknown` 不再因为出现在未持有股票或非目标桶中而令整个月份失效后，结果如何变化；
2. 等权 long-only P4 持仓容量 `N=5/10/20/30/40/50` 对收益、排序 spread、unknown 暴露与稳定性的影响。

本轮复用 sealed `20B_v5` 已形成的 P4 分数，不重新估计 36 个月 market model，不改变 11 个月 residual-momentum score，不修改、覆盖或重新发布 v5。

本轮是在查看 v5 outcome 后生成的容量/退出规则诊断，固定标记：

```text
historical_sample_role = design_contaminated_followup
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
deployment_authorized = false
```

## 2. Run 身份与文件

```text
run_id = 20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_v0
contract_version = 20B_P4_CAP_v0
primary_arm = P4_RESMOM_R2_MARKET_ONLY_ADAPTATION
primary_weighting = EW
```

必须新增而不是改写：

- `configs/config_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.yaml`
- `src/run_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.py`
- `tests/test_20b_p4_unknown_deferred_exit_bucket_capacity_diagnostic.py`
- `outputs/20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_v0/`

## 3. 输入契约

### 3.1 Sealed signal/outcome 输入

只允许读取 sealed v5：

- `historical/instrument_month_signal_bucket_assignment.parquet`
- `historical/outcome_resolution_audit.csv.gz`
- `preoutcome/statistical_and_fold_freeze.csv`
- v5 manifest/hash artifacts

P4 signal panel 固定取：

```text
arm_id = P4_RESMOM_R2_MARKET_ONLY_ADAPTATION
semantic_track = project_sequential_market_residual_primary
source bucket_count = 10       # 仅用于去除v5中5/10重复行，不继承原decile membership
signal_eligible = true
score = raw_signal
```

同一 `(instrument_id, decision_date)` 必须唯一。发现重复分数不一致、非有限分数、日期重复或输入 hash 缺失时 fail closed。

### 3.2 Deferred-exit bridge

只有进入本轮 Top-N 且 v5 outcome 为 `unknown_bridge_arm_month_not_evaluable` 的真实持仓，才允许读取补充价格桥。

补充桥固定为腾讯日线 qfq 接口：

```text
provider = tencent_ifzq_qfq
endpoint = https://web.ifzq.gtimg.cn/appstock/app/fqkline/get
frequency = day
adjustment = qfq
```

每个 HTTP response 必须原样保存并记录：URL、访问时间、HTTP status、payload SHA-256、instrument、请求日期范围。禁止把腾讯桥写成 v5 原 AKShare/Eastmoney snapshot 的同源复制；必须标记 `mixed_provider_bridge_sensitivity=true`。

## 4. 容量定义

这里的 `5/10/20/30/40/50` 是每个极端桶的**股票容量**，不是 quantile bucket 的数量。

对每个 decision month：

1. 在 signal-eligible 股票中按 `(raw_signal DESC, instrument_id ASC)` 稳定排序；
2. 前 N 名为 `favorable_top_n`；
3. 后 N 名为 `unfavorable_bottom_n`；
4. 其余股票为 `not_selected_middle`；
5. 要求 `signal_eligible_n >= 2*N`，否则该容量月份不可形成；
6. Top-N 与 Bottom-N 内均采用等权；本轮不构造新的市值权重。

容量集合预先固定：

```text
bucket_capacity_n = [5, 10, 20, 30, 40, 50]
```

## 5. Unknown 与持仓状态机

### 5.1 非持仓 unknown

Primary portfolio 只持有 `favorable_top_n`。

- unknown 位于 `not_selected_middle`：不进入持仓、不影响 Top-N 月份可评价性；
- unknown 位于 `unfavorable_bottom_n`：从 comparator bottom bucket 删除，只对剩余已解析股票重新等权；必须记录删除数和有效 N；
- 不允许因为 middle/bottom unknown 删除或改变任何 Top-N 成员及其形成时权重。

Bottom-N 删除规则是 comparator-only outcome sensitivity，不是可交易 short portfolio 声明。

### 5.2 Top-N 已持仓 unknown

若 unknown 位于 `favorable_top_n`，它是形成时已持仓股票，不得事后删除并把权重分给其他 Top-N 股票。

固定退出规则：

```text
formation month = t
ordinary exit month = t+1
unknown at t+1 -> retain original 1/N cohort weight
forced exit month = t+2
forced exit price = t+2 自然月内首个可得腾讯 qfq close
deferred gross return = forced_exit_price / formation_date_qfq_close - 1
```

若 formation decision date 没有 qfq close，或 t+2 整月没有退出 mark：

```text
resolution = deferred_exit_unresolved
affected capacity-month = not evaluable
```

不得使用 t+1 最后一个非月末 close 当作正常月末卖出，不得删除已持仓 unknown，不得以零收益或 `-1` 静默填充。

### 5.3 收益解释

包含 deferred exit 的 Top-N formation cohort 混合了 1 个月与约 2 个月持有期。因此输出只能称为：

```text
formation_cohort_deferred_exit_gross_return
```

不得称为独立同分布的月收益、月度 NAV 或成本后策略收益。必须同时披露 deferred position 数量、实际持有日数和其对 cohort return 的贡献。

## 6. 统计与比较

对每个容量和 `full/early/late` 固定输出：

- signal month N、evaluable month N；
- Top-N cohort mean/median/std、positive rate、HAC mean t/p（design-only）；
- Bottom-N delete-and-renormalize mean；
- Top-minus-Bottom spread mean、positive rate；
- Top-N unknown held N、Bottom-N unknown deleted N、middle unknown ignored N；
- deferred exit 对 Top-N mean 的贡献；
- 与 `N=10` 在共同月份上的 paired delta；
- 相邻容量的增量 shell return。

Early/late 边界继承 v5 `P4_PRIMARY_CALENDAR`，不得根据本轮结果重新切分。

## 7. 必需输出

至少生成：

```text
contract_snapshot.json
input_hash_audit.csv
source/tencent_qfq_bridge_*.json
historical/p4_capacity_assignment.parquet
historical/p4_deferred_exit_audit.csv
historical/p4_capacity_monthly_returns.csv.gz
historical/p4_capacity_summary.csv
historical/p4_capacity_paired_delta_vs_10.csv
historical/p4_capacity_shell_attribution.csv
20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_decision.csv
20B_P4_unknown_deferred_exit_bucket_capacity_diagnostic_report.md
manifest_20b_p4_capacity.json
output_hashes_20b_p4_capacity.json
```

## 8. Decision state

本轮不设置可授权 20C 的 pass/fail gate。

```text
complete_descriptive_capacity_diagnostic
partial_deferred_exit_bridge_blocked
input_integrity_blocked
```

只有六个容量均形成、所有实际 Top-N unknown 均得到可审计 deferred exit、必需输出完整且 manifest hash 通过时，才允许 `complete_descriptive_capacity_diagnostic`。

无论 terminal state 为何：

```text
historical_support_claim_allowed = false
20C_requirement_generation_authorized = false
20C_execution_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```

## 9. 测试要求

单元测试至少覆盖：

1. 分数相同时 instrument id 稳定排序；
2. middle unknown 不使 Top-N 失效；
3. bottom unknown 删除后只在 bottom comparator 内重加权；
4. Top-N unknown 不得删除，必须使用 t+2 首个 mark；
5. t+2 无 mark 时 affected capacity-month fail closed；
6. N=5/10/20/30/40/50 均实际输出；
7. `N=10` paired delta 恒为零；
8. manifest/hash 复算一致。
