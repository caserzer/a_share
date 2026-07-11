# 20B TrendPV 与 Residual Momentum 历史设计 / 复制诊断

## 一页决策

- decision state：`20B_mixed_direction_design_only`
- 20C requirement generation authorized：`false`
- exact replication reachable：`false`
- historical sample role：`design_contaminated_historical`；任何结果都不是 support。
- preoutcome bundle：`8acd8bbebe3a942acc9ad26e031843f01b3c58abd16de66c198a7acf9b6c43c9`
- historical bundle：`ecbaa78fe154d82c959821c90c2ff5e7bd5dcc84ccd8b109453d9a3807ae62d1`

20B 目标是正收益暴露设计，不要求 matched alpha。P2/P3 因 exact data/history/universe gates 失败而 registered-not-run。

## Primary gates

| arm | materialized | favorable full | favorable early | favorable late | spread full | positive exposure gate |
|---|---:|---:|---:|---:|---:|---:|
| P1 TrendPV strict | 54 months | -0.007741 | -0.032996 | 0.017513 | -0.019794 | False |
| P4 R2 market residual | 63 months | 0.003496 | -0.005685 | 0.012390 | 0.006601 | False |

## 边界

所有收益是 close-to-close gross provider-qfq proxy，不是 next-open、成本后、cash-inclusive 20C NAV。Paper-sort morphology 与 favorable bucket 绝对收益分别报告；任何显著性只作 design diagnostic。

P5 使用 2025 static concept-board proxy；2025 年以前及混合 formation 均标记 retrospective look-ahead。P4 pass 不晋升 R2，也不改变冻结的 R3 residual primary。

3/6/12 overlapping appendix 使用 within-cohort buy-and-hold drift 与跨 cohort 1/H allocation 完整物化；它不参与任何 gate。

Finalize raw input read count：`0`；outcome recompute count：`0`。
