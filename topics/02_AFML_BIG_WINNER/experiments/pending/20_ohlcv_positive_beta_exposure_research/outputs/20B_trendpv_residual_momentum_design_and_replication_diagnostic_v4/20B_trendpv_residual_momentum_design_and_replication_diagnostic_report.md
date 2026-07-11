# 20B TrendPV 与 Residual Momentum 历史设计 / 复制诊断

## 1. 一页决策

- decision state：`20B_underpowered_design_diagnostic`
- 20C requirement generation authorized：`false`
- exact replication reachable：`false`
- historical sample role：`design_contaminated_historical`；任何结果都不是 support。
- preoutcome bundle：`7d36d4be47b4c996c4f119423130557b2f5eecc8f2ca7662b9133b249afa4d43`
- historical bundle：`0aa2020b20d043903220037b05a44bf6c5991fc555f6edf9d2ace0587c933ddc`

20B 目标是正收益暴露设计，不要求 matched alpha。P2/P3 因 exact data/history/universe gates 失败而 registered-not-run。

## 2. 正 beta 目标，不是 alpha 目标

冻结目标是 favorable bucket 的绝对 gross return 方向；`incremental_alpha_required=false`。Spread 只诊断 paper-style sorting morphology，不替代正收益暴露门。

## 3. 20A lineage 与运行授权

20A freeze hash 固定为 `da5902ac7a987ec061cdffc33e8735ad34c22f1ae771a43540fe005fd77acb05`。Preoutcome bundle `7d36d4be47b4c996c4f119423130557b2f5eecc8f2ca7662b9133b249afa4d43` 在 outcome access 前完成密封；本轮直接运行授权绑定到该 hash，历史 bundle 为 `0aa2020b20d043903220037b05a44bf6c5991fc555f6edf9d2ace0587c933ddc`。

## 4. Metadata resolution

R2 universe/replication/promotion 已解析为 `U_project / project_adaptation / promotion=false`；P4 仅保留 family-bridge authorization。Trend warm-up 使用 400 sessions 后 38 个 complete coefficient months，不复用旧的 97-month metadata。

## 5. Exact routes

| arm | status | reason |
|---|---|---|
| P2 | registered_not_run | wide PIT market-cap、PIT EP、paper universe/history gates 不满足 |
| P3 | registered_not_run | risk-free、CH-3 vintage、paper universe/history gates 不满足 |

## 6. 支持月份、coverage 与 missingness

`monthly_signal_support.csv` 共 666 行，逐 arm-track-month 披露 denominator、signal/decile coverage、paper completeness、project resolution 与 unknown bridge。P1 strict/P1 paper-fill/P4/P5/P0/P6 的 primary evaluable months 分别为 35/54/43/46/56/49。

## 7. TrendPV 18 signals 与 coefficient path

使用 9 个 price 与 9 个 normalized-volume predictor；月度 OLS 为 float64 `lstsq(rcond=1e-12)`。Artifact 同时保存 realized beta、EMA beta、rank、fit row hash、complete-month count 与 staleness，score 分解为 price/volume components。

## 8. 月末动量与 sequential R2

P0 固定使用 `t-11...t-1` 11 个 project-conservative returns。P4 每个 residual month 只用此前 36 个 paired stock/CSI300 months 回归，再以 `t-11...t-1` 的 11 个 residuals 形成 score。

## 9. R3 board ridge 与 paired attribution

P5 复用逐行 P4 residual，再用 lagged log-size 与去重后的 2025 board multi-hot 做 ridge。Retrospective/mixed/fully-post scopes 均机械标注；paired attribution 产生 456 个 return scope summary，不使用 unpaired arm means。

## 10. Outcome resolution

Audit rows 的 resolution 数量：valid=663,156，suspension carry=0，confirmed delisting -1=0，unknown bridge=2,844。只有 security master 确认退市才允许 -1；unknown 会令整个 project bucket-month 不可评价。

## 11. EW/VW sorting morphology 与 primary gates

| arm | materialized | favorable full | favorable early | favorable late | spread full | positive exposure gate |
|---|---:|---:|---:|---:|---:|---:|
| P1 TrendPV strict | 35 months | -0.012722 | -0.037870 | 0.029836 | -0.023221 | False |
| P4 R2 market residual | 43 months | 0.005798 | 0.000169 | 0.013616 | 0.016189 | False |

所有 decile/quintile EW/VW、bucket means、favorable-minus-unfavorable、favorable-minus-middle、raw/aligned Spearman 均保留在 sealed tables。

## 12. 3/6/12 overlapping appendix

共 12,420 个 overlapping portfolio-month rows。Within-cohort 使用 buy-and-hold drift，跨 cohort 固定 1/H；只有恰好 H 个 active 且 observable cohorts 时可评价。Delisting -1 只在 terminal month 一次，后续为 `post_terminal_zero_value`；该 appendix 不进入 gate。

## 13. Frozen folds、dominance 与 design-only inference

P1/P4 使用 preoutcome 冻结的 48/24 与 60/30 calendars；实际缺失月份不会重切 early/late。Quantile、ES10、HAC Bartlett、drawdown、month dominance、LOMO 与 LOIO 均为 design-only fragility diagnostics。

## 14. Paper context 不可直接比较

本地使用 U_project、provider-qfq、固定本地 dates/weights/holding；论文样本、universe、数据库与 portfolio construction 不同，因此 paper statistic 与 local value 均标记 `direct_comparability=false`。

## 15. Gate、family bridge 与 20C

P1 paper-sort=False，P4 paper-sort=False，P1 paper-fill diagnostic=False，P5 retrospective diagnostic=False。P4 `arm_promotion_eligible=false`，仅能通过 family-bridge field 参与 20C generation。`20C_requirement_generation_authorized=False`。

## 16. Access、resolution 与 manifest 证据

Historical access audit 分开记录 qfq、PIT universe/status/size、CSI300、board snapshot 与 security master。三个 bundle 均执行 file-set 双向 hash 校验；v1 输出保留为 superseded，v2 通过 transactional candidate publication。

## 17. 授权边界

所有收益是 close-to-close gross provider-qfq proxy，不是 next-open、成本后、cash-inclusive 20C NAV。Paper-sort morphology 与 favorable bucket 绝对收益分别报告；任何显著性只作 design diagnostic。

P5 使用 2025 static concept-board proxy；2025 年以前及混合 formation 均标记 retrospective look-ahead。P4 pass 不晋升 R2，也不改变冻结的 R3 residual primary。

3/6/12 overlapping appendix 使用 within-cohort buy-and-hold drift 与跨 cohort 1/H allocation 完整物化；它不参与任何 gate。

`20C_execution_authorized=false`，`policy_training_authorized=false`，`policy_replay_authorized=false`，`portfolio_optimization_authorized=false`，`deployment_authorized=false`。

Finalize raw input read count：`0`；outcome recompute count：`0`。
