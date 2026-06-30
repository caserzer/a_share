# 17C Oracle Robustness Stress Report

## 1. 结论

```text
decision_state = EP17C_oracle_robustness_ready_for_diagnosis
next_allowed_requirement = requirement_17d_oracle_diagnosis_report.md
blocking_reason = none
```

17C 的结论是：当前 action space 中存在稳定的 oracle upper-bound utility，且不是由单一股票、单一 episode、单一 calendar cluster 或单一 matched bucket 支撑。因此 17D 可以继续做诊断解释，研究这个 action value 来自 payoff-state、path-risk 还是 delayed action geometry。

但这个结论仍然是 upper-bound diagnostic，不是策略授权。17C 不授权 entry、exit、holding、sizing、portfolio backtest、model deployment、production signal 或 live trading。O5 是后见之明 perfect utility 上界；O1/O2/O4 是用 label/path 信息构造的现实知识 oracle。17C 的正结果只能说明“值得解释 action value 是否存在”，不能说明“已有可交易信号”。

## 2. 核心发现

1. **O5 上界很强，但不是唯一证据。** Robustness split 上 O5 的 mean incremental return 为 2.95%，trimmed mean 为 2.76%，bootstrap 最低 CI low 为 2.17%，top-k 去除后最低仍有 2.69%。这确认 action-space 上界有足够 headroom。
2. **O1/O4 label/path oracle 也过了所有 primary gate。** O1 与 O4 在 robustness split 上 mean 都是 2.47%，bootstrap 最低 CI low 约 1.48%-1.51%，top-k 最差后仍有 2.20%。这说明结果不只是 O5 hindsight artifact，label/path 方向本身也含有正 utility。
3. **O2 drawdown path signal 有独立价值，但强度随阈值加深快速衰减。** -8% drawdown threshold 的 mean 为 2.02%；-10% primary 为 1.85%；-20% 只剩 0.56%。所有 O2 threshold 仍为正，但越深的 drawdown 越像稀疏防守事件，而不是宽覆盖 action rule。
4. **O4 high-upside stress 暴露了“过窄保留 winner”的风险。** Top30 和 Top20 high-upside stress 仍为正且通过 top-k/bootstrap；Top10 stress 的 mean 变成 -0.33%，top-k 和 bootstrap 均 fail。只保留最极端 upside 会过度 defend，牺牲太多可继续持有的 winner path。
5. **Delayed action 是可研究方向，但等待损耗明显。** Robustness split 的 k=3 delayed mean 为 2.99%，略高于 O5 t0 reference 2.95%；k=5 降到 2.74%，k=10 降到 2.35%。Train 和 validation 上 k=3 已经低于 O5 t0，k=10 retention 进一步降到 73.22% 和 65.07%。这支持 17D 研究 staged decision，但不支持把 delayed flag 直接当作 policy。
6. **Capacity 仍不可评估。** O6 capacity constraint 是 `appendix_only_nonblocking`，所以 17C 的 positive result 没有执行容量含义。后续如果进入实现层，必须先解决 capacity reconstruction。

## 3. 血缘与契约校验

17C 的输入和 17B handoff gate 全部通过。关键 row-level panel 有 3,224,736 行；17B ladder summary 有 432 行；17C contract validation 产出 72 个检查项，全部 pass。

| check area | observed | status | implication |
|:--|--:|:--|:--|
| 17C input artifacts | 24 artifacts | pass | requirement、research plan、17A/17B tables、manifests、qfq source 均可读 |
| 17B contract validation | 72 checks | pass | decision row、manifest hash、row counts、ladder summary reconciliation 均通过 |
| Row-level canonicalization | 6 checks | pass | `cluster_split_bucket`、canonical split、signed drawdown、abs drawdown 均可用 |
| 17A delayed/capacity inheritance | 10 rows total | pass / appendix-only | delayed 可重放；capacity 只作为 appendix-only |

Row-level canonicalization 的关键点是 drawdown 口径已经拆开：O2 阈值使用 signed-negative 的 `signed_max_drawdown_h20`，capacity/reporting 使用 positive abs 的 `drawdown_abs_for_reporting`。这避免了把 positive abs drawdown 与负阈值比较导致 O2 永不触发的问题。

## 4. Primary Oracle 稳健性

Primary setting 固定为 robustness split、`cost_bps=50`、`q_defend=0.0`。O1/O4 的 denominator 是 binary rows，O2/O5 的 denominator 是 labelable rows。

| oracle | denominator n | defended rate | mean incremental | trimmed mean | bootstrap CI low min | top-k mean min | matched pass share | primary gate |
|:--|--:|--:|--:|--:|--:|--:|--:|:--|
| O1 negative label | 1,872 | 28.10% | 2.47% | 2.47% | 1.48% | 2.20% | 100% | pass |
| O2 drawdown <= -10% | 2,496 | 21.07% | 1.85% | 1.82% | 1.14% | 1.65% | 100% | pass |
| O4 label/path positive | 1,872 | 28.10% | 2.47% | 2.47% | 1.51% | 2.20% | 100% | pass |
| O5 perfect utility | 2,496 | 42.31% | 2.95% | 2.76% | 2.17% | 2.69% | 100% | pass |

**解读。** O5 作为后见之明 oracle 确实最高，但 O1/O4 与 O2 也都有正值并通过 robustness gate。最重要的不是 O5 本身，而是 O1/O2/O4 没有塌掉：这把问题从“action space 完全没有价值”推进到“哪些状态变量能解释这个 action value”。

## 5. 尾部集中度压力测试

Top-k removal 的 denominator 固定为原始 observed steps；也就是说，去掉贡献最大的股票或 episode 后，不重新缩小 denominator。这是更保守的 stress。

| oracle | original mean | worst removal | remaining mean | retained share | gate |
|:--|--:|:--|--:|--:|:--|
| O1 negative label | 2.47% | remove top 5 instruments | 2.20% | 88.95% | pass |
| O2 drawdown <= -10% | 1.85% | remove top 5 instruments | 1.65% | 88.95% | pass |
| O4 label/path positive | 2.47% | remove top 5 instruments | 2.20% | 88.95% | pass |
| O5 perfect utility | 2.95% | remove top 5 instruments | 2.69% | 91.29% | pass |

**解读。** 结果不是由少数 super winner 股票撑起来的。最坏 stress 都是 remove top 5 instruments，而不是 remove top 1% episodes；这说明贡献有一定股票维度集中度，但去掉前五个股票后仍保留接近 89%-91% 的 mean utility。17D 不应只去找单名股票或少数 episode 的解释，而应检查更一般的 payoff-state/path-risk 结构。

## 6. Bootstrap 与 Matched-base 稳定性

Primary bootstrap families 是 episode cluster、instrument、calendar month；calendar quarter 只做 readout-only，因为 cluster 数为 10，低于 primary bootstrap floor。

| oracle | weakest primary bootstrap family | cluster n | CI low | CI high | gate |
|:--|:--|--:|--:|--:|:--|
| O1 negative label | calendar_month | 26 | 1.48% | 3.68% | pass |
| O2 drawdown <= -10% | calendar_month | 26 | 1.14% | 2.72% | pass |
| O4 label/path positive | calendar_month | 26 | 1.51% | 3.57% | pass |
| O5 perfect utility | calendar_month | 26 | 2.17% | 3.81% | pass |

Matched-base hard families 全部通过，且 family pass share 都是 100%。

| oracle | calendar_month | calendar_quarter | board bucket | matched gate |
|:--|:--|:--|:--|:--|
| O1 negative label | 25 / 25 buckets pass | 9 / 9 buckets pass | 3 / 3 buckets pass | pass |
| O2 drawdown <= -10% | 25 / 25 buckets pass | 9 / 9 buckets pass | 3 / 3 buckets pass | pass |
| O4 label/path positive | 25 / 25 buckets pass | 9 / 9 buckets pass | 3 / 3 buckets pass | pass |
| O5 perfect utility | 25 / 25 buckets pass | 9 / 9 buckets pass | 3 / 3 buckets pass | pass |

**解读。** Calendar-month bootstrap 是最弱 stress，但最低 CI low 仍显著大于 0。Matched-base 进一步说明结果不是某个月份、某个季度或某个板块 bucket 独占。17D 可以把时间/板块作为解释维度，但不应把它们当作唯一 source of value。

## 7. O2 回撤阈值稳健性

O2 使用 signed drawdown rule：`signed_max_drawdown_h20 <= threshold`。下表展示 robustness split 上不同 drawdown 阈值的 action intensity 和 utility。

| O2 variant | threshold | defended n | defended rate | mean | trimmed mean | top-k mean min | bootstrap CI low min |
|:--|--:|--:|--:|--:|--:|--:|--:|
| O2_dd_08pct_stress | -8% | 731 | 29.29% | 2.02% | 2.06% | 1.81% | 1.21% |
| O2_dd_10pct_primary | -10% | 526 | 21.07% | 1.85% | 1.82% | 1.65% | 1.14% |
| O2_dd_12pct_stress | -12% | 369 | 14.78% | 1.53% | 1.46% | 1.33% | 0.92% |
| O2_dd_15pct_stress | -15% | 211 | 8.45% | 1.09% | 0.93% | 0.91% | 0.65% |
| O2_dd_20pct_stress | -20% | 71 | 2.84% | 0.56% | 0.33% | 0.42% | 0.25% |

**解读。** Drawdown path risk 是真实 utility source，但它的 marginal value 很依赖覆盖率。-8% 到 -12% 的区间仍有较高 mean 和足够 action count；-20% 虽然仍 pass，但只覆盖 71 行，utility 已经压到 0.56%。因此 17D 应把 O2 视为 path-risk diagnostic，而不是直接冻结一个 deep drawdown threshold 当 rule。

## 8. O4 高上行阈值压力测试

O4 high-upside thresholds 使用 train split 冻结 cutoff，不在 robustness/validation 上重算 quantile。

| threshold id | train quantile | frozen cutoff | robustness cutoff | validation cutoff | split-local recompute |
|:--|--:|--:|--:|--:|:--|
| high_upside_top30_stress | 70% | 0.059633 | 0.059633 | 0.059633 | false |
| high_upside_top20_stress | 80% | 0.101229 | 0.101229 | 0.101229 | false |
| high_upside_top10_stress | 90% | 0.172107 | 0.172107 | 0.172107 | false |

| O4 variant | defended n | defended rate | mean | top-k mean min | bootstrap CI low min | top-k gate | bootstrap gate |
|:--|--:|--:|--:|--:|--:|:--|:--|
| O4_label_positive_primary | 526 | 28.10% | 2.47% | 2.20% | 1.51% | pass | pass |
| O4_high_upside_top30_stress | 1,644 | 65.87% | 2.21% | 1.97% | 1.34% | pass | pass |
| O4_high_upside_top20_stress | 1,910 | 76.52% | 1.32% | 1.11% | 0.36% | pass | pass |
| O4_high_upside_top10_stress | 2,207 | 88.42% | -0.33% | -0.50% | -1.64% | fail | fail |

**解读。** O4 的核心信息不是“越严格筛 winner 越好”，而是相反：如果只保留 top10 upside，oracle 会 defend 88.42% 的 rows，结果变成负值。Top30/Top20 仍可行，Top10 失败，说明 continuation value 不是只集中在最极端 payoff tail；过度防守会牺牲一大段 still-profitable continuation path。17D 需要解释“哪些 positive path 应继续暴露”，不能只学习“不是超级 winner 就防守”。

## 9. O5 证明与上界解释

17B 的 O5 proof 在 primary setting 下通过：

| split | cost bps | q_defend | observed n | defended n | recompute mismatch | action-set proof | gate |
|:--|--:|--:|--:|--:|--:|:--|:--|
| robustness | 50 | 0.0 | 2,496 | 1,056 | 0 | equal to full defend reference | pass |

O5 formula 是 `defend if q_defend * forward_return_h20 - cost_bps/10000 > forward_return_h20`。在 primary setting 下，O5 defended rate 是 42.31%，高于 O1/O4 的 28.10% 和 O2 的 21.07%。

**解读。** O5 的存在保证 action-space upper bound 不为零，但 O5 不能作为可实现 policy。真正有诊断价值的是：O1/O2/O4 在不使用 perfect utility selection 的情况下仍然 positive。这是 17D 的研究入口。

## 10. Delayed Oracle 曲线

O7 delayed diagnostic 在原始 H20 endpoint 内切换，不重启 H20，不做 partial tail fill。`delayed_mean_gap_vs_o5_t0` 是诊断 gap，不是 support gate。

| split | O5 t0 mean | best k | best delayed mean | best gap vs O5 | best retention | k=10 retention | delayed gates |
|:--|--:|--:|--:|--:|--:|--:|:--|
| train | 3.56% | 3 | 3.33% | -0.23% | 93.67% | 73.22% | pass |
| robustness | 2.95% | 3 | 2.99% | 0.05% | 101.56% | 79.64% | pass |
| validation | 3.91% | 3 | 3.40% | -0.52% | 86.83% | 65.07% | pass |

完整 delayed curve：

| split | k | delayed mean | delayed trimmed mean | O5 t0 mean | gap vs O5 | retention |
|:--|--:|--:|--:|--:|--:|--:|
| train | 3 | 3.33% | 3.11% | 3.56% | -0.23% | 93.67% |
| train | 5 | 3.16% | 2.94% | 3.56% | -0.39% | 88.92% |
| train | 10 | 2.60% | 2.41% | 3.56% | -0.95% | 73.22% |
| robustness | 3 | 2.99% | 2.79% | 2.95% | 0.05% | 101.56% |
| robustness | 5 | 2.74% | 2.54% | 2.95% | -0.21% | 92.82% |
| robustness | 10 | 2.35% | 2.17% | 2.95% | -0.60% | 79.64% |
| validation | 3 | 3.40% | 3.19% | 3.91% | -0.52% | 86.83% |
| validation | 5 | 3.11% | 2.96% | 3.91% | -0.80% | 79.55% |
| validation | 10 | 2.55% | 2.40% | 3.91% | -1.37% | 65.07% |

**解读。** Delayed action 的形状很清楚：k=3 仍然有价值，k=10 明显衰减。Robustness 上 k=3 略高于 O5 t0 是一个 staged accounting readout，不应解释为 delayed policy 支配 perfect utility；train/validation 都显示等待有成本。17D 应把 delayed result 当作“action timing sensitivity”：如果真实信号只能延迟触发，value 会快速折损，尤其 validation 上 k=10 只保留 65.07%。

## 11. Capacity 与执行边界

Capacity result 仍是 inherited appendix-only：

| split | observed n | O5 unconstrained defended n | unconstrained mean | capacity status | capacity gate |
|:--|--:|--:|--:|:--|:--|
| train | 20,245 | 9,409 | 3.56% | appendix_only_nonblocking | not_evaluable_nonblocking |
| robustness | 2,496 | 1,056 | 2.95% | appendix_only_nonblocking | not_evaluable_nonblocking |
| validation | 664 | 319 | 3.91% | appendix_only_nonblocking | not_evaluable_nonblocking |

**解读。** 17C 不能回答“这个 action value 能否被容量约束下执行”。它只说明 unconstrained action space 有 upper-bound value。任何后续执行研究都必须先补 O6 capacity reconstruction；否则 O5/O7 的 defended count 只代表 diagnostic action intensity，不代表可部署换手或持仓容量。

## 12. Search Accounting 与授权边界

Search accounting gate 为 pass：没有 model training、没有 refit、没有 survival threshold tuning、没有 validation selection、没有 robustness tuning、没有 feature selection、没有 payoff label redesign、没有 oracle threshold tuning、没有 bootstrap/matched family selection、没有 capacity constraint selection from results。

所有授权位均为 false：

| authorization | value |
|:--|:--|
| entry_policy_authorized | false |
| exit_policy_authorized | false |
| holding_policy_authorized | false |
| portfolio_backtest_authorized | false |
| model_deployment_authorized | false |
| production_signal_authorized | false |
| live_trading_authorized | false |

## 13. 17D 交接

17C 给 17D 的问题不是“是否交易”，而是“正的 oracle action value 来自哪里”。建议 17D 聚焦三条诊断线：

1. **Payoff-state line:** O1/O4 与 O5 的差距是多少，哪些 label/path state 能解释 O5 的 extra headroom。
2. **Path-risk line:** O2 在 -8% 到 -20% drawdown 阈值上 value 单调衰减，17D 应拆解 drawdown depth、recovery probability、positive continuation sacrifice。
3. **Timing line:** O7 k=3 到 k=10 的 retention 快速下降，17D 应判断 action value 是否要求早期识别，还是可由 delayed staged decision 捕获。

最终解释边界：17C 支持进入 `requirement_17d_oracle_diagnosis_report.md`，但不支持进入 policy implementation、portfolio backtest 或 live trading。
