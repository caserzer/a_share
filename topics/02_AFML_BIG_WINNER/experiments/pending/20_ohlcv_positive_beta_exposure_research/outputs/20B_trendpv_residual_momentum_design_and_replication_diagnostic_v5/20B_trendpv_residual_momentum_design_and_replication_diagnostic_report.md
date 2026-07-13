# 20B TrendPV 与 Residual Momentum 历史设计 / 复制诊断

## 1. 一页决策

- decision state：`20B_underpowered_design_diagnostic`
- 20C requirement generation authorized：`false`
- exact replication reachable：`false`
- historical sample role：`design_contaminated_historical`；任何结果都不是 support。
- preoutcome bundle：`4079813d74ce16344dd53886c6a986c356a17589dd5725c18622a807de1102d1`
- historical bundle：`bac77bc13efcd7b75df5b18f44940bcc24e57589e62dde593bd0ef748705426f`

20B 目标是正收益暴露设计，不要求 matched alpha。P2/P3 因 exact data/history/universe gates 失败而 registered-not-run。

## 2. 正 beta 目标，不是 alpha 目标

冻结目标是 favorable bucket 的绝对 gross return 方向；`incremental_alpha_required=false`。Spread 只诊断 paper-style sorting morphology，不替代正收益暴露门。

## 3. 20A lineage 与运行授权

20A freeze hash 固定为 `da5902ac7a987ec061cdffc33e8735ad34c22f1ae771a43540fe005fd77acb05`。Preoutcome bundle `4079813d74ce16344dd53886c6a986c356a17589dd5725c18622a807de1102d1` 在 outcome access 前完成密封；本轮直接运行授权绑定到该 hash，历史 bundle 为 `bac77bc13efcd7b75df5b18f44940bcc24e57589e62dde593bd0ef748705426f`。

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

Historical access audit 分开记录 qfq、PIT universe/status/size、CSI300、board snapshot 与 security master。三个 bundle 均执行 file-set 双向 hash 校验；早期 superseded bundles 保持 immutable，当前 `20B_v5` 通过 transactional candidate publication。

## 17. 授权边界

所有收益是 close-to-close gross provider-qfq proxy，不是 next-open、成本后、cash-inclusive 20C NAV。Paper-sort morphology 与 favorable bucket 绝对收益分别报告；任何显著性只作 design diagnostic。

P5 使用 2025 static concept-board proxy；2025 年以前及混合 formation 均标记 retrospective look-ahead。P4 pass 不晋升 R2，也不改变冻结的 R3 residual primary。

3/6/12 overlapping appendix 使用 within-cohort buy-and-hold drift 与跨 cohort 1/H allocation 完整物化；它不参与任何 gate。

`20C_execution_authorized=false`，`policy_training_authorized=false`，`policy_replay_authorized=false`，`portfolio_optimization_authorized=false`，`deployment_authorized=false`。

Finalize raw input read count：`0`；outcome recompute count：`0`。

## 18. Post-seal 报告增补说明

本节及以下内容是 2026-07-13 基于已密封表的人工叙事性增补，只扩写研究发现，不重算 outcome、不改变 decision CSV、
不修改任何代码，也不授权后续阶段。增补使用的核心数据表包括 `monthly_signal_support.csv`、
`sort_monotonicity_readout.csv`、`arm_summary_statistics.csv`、`month_instrument_dominance_audit.csv`、
`p4_p5_board_attribution_readout.csv` 与 residual overlapping appendix。

需要特别说明：final manifest 保存的是增补前报告 SHA256
`370904e7e69ab947f74c7e9cbfe98732ee9a3bcd53df5d39aa2623ea6ad66f26`。因此，增补后的 Markdown 不再是该 final
manifest 中的原始字节对象；不得对编辑后的报告声称 `final_manifest_hash_gate=pass`。机器 decision 与 historical bundle
没有被修改，historical bundle hash 仍为
`bac77bc13efcd7b75df5b18f44940bcc24e57589e62dde593bd0ef748705426f`。若未来需要重新形成 immutable final bundle，
必须使用新的 contract/run version 重新发布，而不是回写 v5 manifest。

## 19. 详细执行结论：公式通过，样本硬门失败

当前 terminal state 的准确含义是：P0/P1/P4/P5/P6 均完成了相应公式或诊断物化，P2/P3 按约定未运行；但 P1/P4
primary 的有效月份未达到预注册样本门。因此，本轮不是“没有数据”，也不是“公式失败”，而是“有方向性数据、但不足以授权
20C requirement generation”。

| 项目 | 结果 | 解释 |
|---|---:|---|
| assignment rows | 666,000 | 111 个 decision months × 6 signal tracks × 500 denominator × 5/10 两套 bucket assignments |
| signal rows | 175,771 | 已实际形成信号的 instrument-month rows |
| bucket-return rows | 24,480 | EW/VW、5/10 buckets、两种 return semantics 与 folds 的物化结果 |
| P1 formula integrity | True | 18 signals、OLS/EMA、时序和无未来泄漏检查通过 |
| P4 formula integrity | True | 36m sequential regression 与 11 residual-month score 检查通过 |
| P1 sample support | False | 35 个 project-conservative 月；要求 48，且 early/late 各至少 24 |
| P4 sample support | False | 43 个 project-conservative 月；要求 60，且 early/late 各至少 30 |
| P1/P4 positive-exposure gate | False / False | 首先被 sample support 阻断；P1 的 full/early 方向本身也为负 |
| 20C requirement generation | False | 没有 primary arm 通过完整 design gate |

关键研究判断：P4 给出值得继续观察的正方向点估计，但契约不允许用“点估计很好”绕过样本门；P1 则不仅样本不足，
full/early 的方向也与预期相反。

## 20. 月份支持、股票数、coverage 与 missingness

`U_project` 每个 decision month 的冻结 denominator 为 500。下表的“信号就绪月”表示公式和 bucket floor 已满足；
“project 可评价月”还要求 project-conservative outcome 没有 unknown bridge。Coverage 是在信号就绪月份内的月均值。

| arm / track | 信号就绪月 | project 可评价月 | 信号股票数 min/median/max | 月均 signal coverage | unknown 影响月份/rows |
|---|---:|---:|---:|---:|---:|
| P0 Total Momentum | 99 | 56 | 387 / 470 / 495 | 92.80% | 43 / 86 |
| P1 TrendPV paper-fill | 54 | 35 | 455 / 484.5 / 495 | 96.17% | 19 / 28 |
| P1 TrendPV project-strict | 54 | 35 | 455 / 484.5 / 495 | 96.16% | 19 / 26 |
| P4 market-only residual | 63 | 43 | 295 / 418 / 447 | 79.52% | 20 / 29 |
| P5 market+size+board residual | 63 | 46 | 213 / 306 / 360 | 59.59% | 17 / 23 |
| P6 Low Vol | 75 | 49 | 315 / 425 / 469 | 83.74% | 26 / 34 |

P1 paper-fill 的 54 个月是 `paper_qfq_complete_case_sensitivity` 可评价月；若换成 project-conservative whole-bucket
规则，同一信号 track 只有 35 个月。旧版摘要中的“35/54”不是矛盾，而是两个 return semantics。Paper complete-case
不能进入正收益暴露门。

全局 outcome-resolution audit 有 666,000 rows：`valid_mark=663,156`（99.573%），
`unknown_bridge_arm_month_not_evaluable=2,844`（0.427%）；`suspension_carry=0`、确认退市 `-1=0`。虽然 unknown
row 比率很低，但契约要求它使涉及的整个 bucket-month 不可评价，因而会显著压缩时间样本。零 suspension/delisting 只能说明
本轮数据没有解析到这些状态，不能推断实际 A 股组合不存在停牌或退市风险。

## 21. TrendPV：18 signals、系数路径与成分诊断

P1 对窗口 `3/5/10/20/50/100/200/300/400` 分别构造 9 个 normalized-price 与 9 个 normalized-volume
predictors。月度横截面 OLS 使用 `float64 lstsq(rcond=1e-12)`；完整回归的 rank 恒为 19（含截距），EMA
`lambda=0.02`，只有 38 个 complete coefficient months 后才允许形成 score。

两条 Trend track 各有 113 个 coefficient calendar months，其中 93 个 complete，完整区间为 2018-09 至 2026-05；
complete fit N 的范围为：paper-fill 444–494（中位 466），project-strict 340–494（中位 466）；最大 coefficient
staleness 为 0。第一批 score 月为 2021-10，而不是复用 20A planning metadata 中错误的 97-month support。

Component diagnostic 共 55 个 score months（2021-10 至 2026-04），每条 track 每月股票数中位数约 485：

| track | price component 月均绝对值 | volume component 月均绝对值 | corr(price, total) | corr(volume, total) |
|---|---:|---:|---:|---:|
| paper-fill | 0.06403 | 0.00343 | 0.99951 | 0.19831 |
| project-strict | 0.05973 | 0.00271 | 0.99951 | 0.21120 |

这说明本地 TrendPV score 的月均截面中心变化几乎完全由 price component 驱动，volume component 对均值的量级约为
price 的 4%–5%。这不是说个股横截面上的 volume 信息为零，但至少表明本轮失败不能简单归因于“少了一个很强的成交量
均值贡献”。更重要的差异仍是：本地只运行 raw OHLCV score，未运行论文的 size × E/P × Trend 2×3×3 完整因子。

## 22. Residual Momentum：sequential R2 与 R3 ridge 诊断

P4 每个 residual month 对每只股票只使用此前 36 个完整 stock/CSI300 months 做带截距回归，再用
`t-11...t-1` 共 11 个 residuals 的均值除以样本波动形成 score。Time-series regression audit 有 101,273 个
`pass` rows、1,615 只股票、76 个 residual months（2020-02 至 2026-05）；每行 observation N 恒为 36、rank 恒为 2。
估计 market beta 的 p10/median/p90 为 0.325 / 0.857 / 1.498，说明原始股票池的市场暴露差异很大，顺序回归确实不是
“股票收益减 CSI300 常数”。

P5 先完整复用 P4 residual，再对 lagged log-size 与 2025-01-02 static concept-board multi-hot 做
`ridge(alpha=1, solver=svd)`。76 个月的 ridge audit 全部为 `pass`；final fit N 为 315–468（中位 426.5），
predictor N 为 220–232（中位 228）。其中 60 个 residual months 在 board snapshot 之前、16 个在 snapshot 之后。
因此历史 P5 的主体是 retrospective look-ahead sensitivity，不是 PIT industry-neutral portfolio。

Score paired attribution 共 19,108 个 common instrument-month pairs、646 只股票、64 个 decision months；P5-P4 score
的均值为 0.107、标准差 0.378，平均绝对变化约 0.30。按 scope 分为 48 个 pre-snapshot decision months、12 个 mixed
months、4 个 theoretical fully-post score months；在 project-conservative decile summary 中，最终只有 37/8/1 个可评价月。

对 project-conservative、EW decile 的 common-return rows，paired 结果为：

| paired series | paired month N | P4 月均 | P5 月均 | P5-P4 |
|---|---:|---:|---:|---:|
| favorable bucket | 61 | 0.2341% | 0.1572% | -0.0768% |
| favorable-minus-middle | 51 | -0.2802% | -0.5705% | -0.2903% |
| favorable-minus-unfavorable | 58 | 0.5714% | -0.4022% | -0.9737% |

Paired spread 减少约 0.97%/月，表明 size/board residualization 在当前样本中基本消除了 P4 的横截面排序差异。这可以有两种
解释：P4 收益主要承载了 size/board 风险来源；或 static concept-board 高维代理与低 coverage 过度中和了有效信号。
由于绝大多数月份是 retrospective，且 fully-post project-evaluable 只有 1 个月，现有数据无法在两者之间作可靠判断。

## 23. 全样本 EW/VW、quintile/decile morphology

下表统一使用 1-month `project_conservative_primary`。所有数字均为月均 gross return；favorable 对 P6 是低波动 bucket，
对其他 arm 是高 score bucket。Spearman 已按 favorable 方向对齐。

| arm / track | weighting | buckets | N | favorable | middle | unfavorable | F-U spread | aligned Spearman |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| P0 Total Momentum | EW | 5 | 56 | 0.2443% | 0.5289% | -0.3003% | 0.5446% | 0.0964 |
| P0 Total Momentum | EW | 10 | 56 | -0.2581% | 0.5275% | -0.5987% | 0.3406% | 0.0697 |
| P0 Total Momentum | VW | 5 | 56 | 0.6502% | 0.4793% | -0.1423% | 0.7924% | 0.1304 |
| P0 Total Momentum | VW | 10 | 56 | -0.0791% | 0.4935% | -0.6488% | 0.5697% | 0.1032 |
| P1 TrendPV paper-fill signal | EW | 10 | 35 | -1.0455% | -0.0674% | 0.8694% | -1.9149% | -0.2000 |
| P1 TrendPV project-strict | EW | 5 | 35 | -1.1782% | 0.2335% | 1.0702% | -2.2484% | -0.2971 |
| P1 TrendPV project-strict | EW | 10 | 35 | -1.2722% | 0.2356% | 1.0499% | -2.3221% | -0.2589 |
| P1 TrendPV project-strict | VW | 5 | 35 | -1.2344% | 0.2649% | 1.1048% | -2.3392% | -0.2171 |
| P1 TrendPV project-strict | VW | 10 | 35 | -1.3094% | 0.2389% | 0.7926% | -2.1020% | -0.1841 |
| P4 market-only residual | EW | 5 | 43 | 0.8052% | 0.5180% | -0.7347% | 1.5398% | 0.1953 |
| P4 market-only residual | EW | 10 | 43 | 0.5798% | 0.5161% | -1.0391% | 1.6189% | 0.1769 |
| P4 market-only residual | VW | 5 | 43 | 0.9547% | 0.1163% | -0.8528% | 1.8075% | 0.2349 |
| P4 market-only residual | VW | 10 | 43 | 0.4003% | 0.1822% | -0.4659% | 0.8663% | 0.1856 |
| P5 board residual | EW | 5 | 46 | -0.0670% | 0.4253% | -0.1894% | 0.1224% | 0.0500 |
| P5 board residual | EW | 10 | 46 | -0.0531% | 0.4248% | -0.0592% | 0.0061% | 0.0353 |
| P5 board residual | VW | 5 | 46 | 0.2719% | 0.2100% | -0.2853% | 0.5573% | 0.1152 |
| P5 board residual | VW | 10 | 46 | 0.4697% | 0.2333% | -0.3553% | 0.8250% | 0.0954 |
| P6 Low Vol | EW | 5 | 49 | 0.9395% | 0.6302% | -0.0725% | 1.0120% | 0.1673 |
| P6 Low Vol | EW | 10 | 49 | 1.0250% | 0.6306% | -0.0338% | 1.0588% | 0.1166 |
| P6 Low Vol | VW | 5 | 49 | 0.8040% | 0.1169% | 0.2843% | 0.5197% | 0.0980 |
| P6 Low Vol | VW | 10 | 49 | 1.0025% | 0.1103% | 0.3402% | 0.6623% | 0.0912 |

形态结论很清楚：P1 在 EW/VW、quintile/decile 下均为反向；P4 在四种组合下均保持 favorable 与 spread 为正；P5 的
EW 形态接近零，但 VW 为正，说明结果对 size weighting 高度敏感；Low Vol 是本轮最稳定的正向 comparator。P0 的 spread
虽略正，但 EW/VW decile favorable bucket 本身为负，说明 long-short morphology 与 long-only 正收益必须分开。

## 24. Early/late 稳定性与门禁对应值

下表使用每条 gate 冻结的 track/return mapping；P1 paper-fill 使用 paper complete-case，其余使用 project-conservative。

| arm / diagnostic | full N | early N | late N | favorable full / early / late | spread full / early / late |
|---|---:|---:|---:|---:|---:|
| P0 Total Momentum | 56 | 24 | 32 | -0.2581% / -0.8047% / 0.1518% | 0.3406% / -0.7342% / 1.1466% |
| P1 project-strict | 35 | 22 | 13 | -1.2722% / -3.7870% / 2.9836% | -2.3221% / -3.8821% / 0.3179% |
| P1 paper-fill diagnostic | 54 | 27 | 27 | -0.3056% / -2.4891% / 1.8779% | -1.4394% / -1.9846% / -0.8943% |
| P4 market-only residual | 43 | 25 | 18 | 0.5798% / 0.0169% / 1.3616% | 1.6189% / 1.3728% / 1.9606% |
| P5 full-history retrospective | 46 | 27 | 19 | -0.0531% / -0.3478% / 0.3658% | 0.0061% / 0.2031% / -0.2737% |
| P6 Low Vol | 49 | 26 | 23 | 1.0250% / 1.2415% / 0.7802% | 1.0588% / 1.3835% / 0.6917% |

P1 的 late fold 转正不能挽救 full/early 反向，且 late 只有 13 个 project-evaluable months；这更像明显的时间状态变化，
不是稳定复制。Paper-fill 的 spread 在 early/late 仍都为负，说明 carry/complete-case 处理没有恢复论文方向。

P4 的 favorable 与 spread 在 full/early/late 均为正，是最有价值的设计信号；但 early favorable 仅 0.0169%/月，接近零，
且 25/18 的 fold N 均低于冻结的 30。其结果更适合定义为“late-strengthened residual-family hypothesis”，不能定义为
“历史正 beta 已支持”。

## 25. 风险、统计不确定性与 dominance

以下是 EW decile favorable bucket 的 gross、close-to-close、非 stateful 月度统计。年化均值采用 `12 × monthly mean`，
不是复合 CAGR；nominal CI 与 p-value 仅为 design diagnostic，不进入支持结论。

| arm | N | 月均 | 年化均值 | 年化波动 | Sharpe | 正月率 | p10 | ES10 loss | 月度复利 MDD | nominal 95% CI（月） |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | 56 | -0.2581% | -3.10% | 27.22% | -0.114 | 42.9% | -9.58% | 12.98% | 54.71% | [-1.989%, 1.473%] |
| P1 strict | 35 | -1.2722% | -15.27% | 23.69% | -0.645 | 34.3% | -9.65% | 11.67% | 58.62% | [-3.798%, 1.254%] |
| P4 | 43 | 0.5798% | 6.96% | 21.70% | 0.321 | 53.5% | -5.48% | 8.29% | 31.97% | [-1.320%, 2.480%] |
| P5 | 46 | -0.0531% | -0.64% | 16.78% | -0.038 | 37.0% | -5.65% | 7.06% | 22.80% | [-1.196%, 1.090%] |
| P6 Low Vol | 49 | 1.0250% | 12.30% | 13.25% | 0.928 | 55.1% | -3.75% | 4.40% | 8.84% | [0.073%, 1.977%] |

P4 的 CI 很宽且包含零，说明 43 个月还不足以稳定估计 0.58% 的月均值。P6 的 nominal CI 下界略高于零，但它仍是已被
topic 消费的 design-contaminated comparator，不能因为 nominal `p=0.0348` 就升级为支持证据。

与 20A 风险预算作仅供设计的 proxy 对照：P4 的月度 ES10、p10 和 gross monthly-series MDD 数值落在 15%、-12%、35%
阈值内；P1 的 MDD 58.62% 明显超出 35%。但 20A 的正式 MDD 是 daily stateful NAV，且要求 next-open、blocked exit、
cash、turnover 与成本，因此本表不能机械宣告 economic/risk gate 通过。

EW decile spread dominance audit 显示：

| arm | full spread | 最大单月绝对贡献 | top-3 月贡献 | LOMO mean min | LOIO mean range |
|---|---:|---:|---:|---:|---:|
| P1 strict | -2.3221% | 10.62% | 28.03% | -2.6392% | [-2.4105%, -2.2505%] |
| P4 | 1.6189% | 7.48% | 18.75% | 1.2595% | [1.4730%, 1.6787%] |
| P5 | 0.0061% | 4.83% | 14.11% | -0.0987% | [-0.1044%, 0.0890%] |
| P6 | 1.0588% | 7.06% | 17.25% | 0.6866% | [1.0056%, 1.1431%] |

P4 spread 在 leave-one-month-out 与 leave-one-instrument-out 下仍为正，说明其方向不是由单一月份或单一股票机械造成；
P5 则在这些扰动下跨零。这提高了 P4 作为“值得做更长样本/前向验证的设计假设”的可信度，但不改变硬门失败。

## 26. 3/6/12 overlapping holding appendix

Appendix 共 12,420 个 portfolio-month rows，其中 6,222 rows 可评价。下表只列 EW decile favorable 与 spread；
within-cohort 为 buy-and-hold drift，跨 cohort 固定 1/H，并且只有恰好 H 个 active、observable cohorts 时才计入。

| arm | H | favorable 可评价月 | favorable 月均 | spread 可评价月 | spread 月均 | spread 正月率 |
|---|---:|---:|---:|---:|---:|---:|
| P4 | 3 | 55 | 0.7754% | 54 | 0.8370% | 46.3% |
| P4 | 6 | 39 | 0.9592% | 38 | 0.5981% | 50.0% |
| P4 | 12 | 12 | 0.5215% | 12 | 0.3617% | 50.0% |
| P5 | 3 | 58 | 0.6574% | 53 | -0.2580% | 41.5% |
| P5 | 6 | 49 | 1.0530% | 38 | 0.1284% | 50.0% |
| P5 | 12 | 22 | 1.9025% | 14 | -0.1217% | 42.9% |

P4 的 spread 随持有期从 3 到 12 个月逐步衰减，方向与 A 股 residual-momentum 文献中 6/12 月效果减弱的描述一致；
但本地不是 exact CH-3 replication，且 H=12 只有 12 个 spread months，不能用这一形态声称复制成功。P5 favorable
的长持有均值上升、spread 却不稳定，提示它更可能承载共同市场/风格收益，而不是稳定的横截面排序优势。

该 appendix 不是 20C 的 stateful long-only NAV：它没有 next-open 成交、现金腿、成本、限价/停牌阻断和持续资本约束，
不得拿 3/6/12 中表现最好的 horizon 替换冻结的 1-month primary。

## 27. 对论文效果的条件性评估

### 27.1 TrendPV / Trend Factor in China

论文对象是 2000–2018 宽截面 A 股，完整 Trend factor 还包含排除最小市值 30%、Size 中位数、E/P 与 Trend 30/70
breakpoints、18 个 VW portfolios。论文 working-paper context 的约 1.43% 月均 long-short、Sharpe 0.48、约 13.17%
最大回撤和约 1.35% break-even cost，均属于该样本与完整 long-short factor。

本地 P1 只是 U_project 上的 raw OHLCV score adaptation。其 project-strict EW decile spread 为 -2.32%/月，
paper-fill diagnostic spread 为 -1.44%/月，且 paper-fill early/late 都为负；因此，本轮没有观察到 TrendPV raw-score 的论文式
排序方向。这个结果足以否定“当前本地 raw score 已可直接进入下一阶段”的设计主张，但不足以否定论文：P2 因 PIT E/P、
wide PIT market cap、paper universe/history 缺失而从未运行。

实际金融含义是：在本项目 top-500 executable universe 中，raw TrendPV 高分更像一个阶段性反向或 regime-sensitive
exposure。晚期 13 个月 favorable 转为 +2.98%，说明信号可能受市场状态影响，但不能据此事后只保留晚期。若要评估论文
本身，应先补齐 U_paper、PIT E/P/size 和 2005 年前后历史，再运行完整 2×3×3；若目标是部署，则即使完整论文因子成功，
仍必须另做 long-only、next-open、cash-inclusive、cost/capacity 的 20C/20G bridge。

### 27.2 Residual Momentum

Blitz et al. 的美国样本报告 residual momentum 约 11.20% 年化、12.49% 波动、Sharpe 0.90；Jansen et al. 的 A 股
样本报告 1-month long-short EW 约 0.66%/月（t=3.36）、VW 约 0.59%/月（t=2.11）。这些结果来自更长样本、宽截面与
market/size/value 三因子 residual。

本地 P4 market-only adaptation 的 EW decile spread 为 +1.62%/月、favorable 为 +0.58%/月，full/early/late 方向一致，
且 dominance 较低；这是与论文机制方向相符的设计信号。与此同时，P4 不是 CH-3、没有 risk-free excess return、只覆盖
43 个 project-evaluable months，favorable nominal CI 包含零。因此，合理结论是“market residual family 值得扩充样本和
前向检验”，不是“residual momentum 已在本地复制”。

P5 board residualization 将 paired spread 平均削弱约 0.97%/月，提示 P4 的回报可能部分来自 size/board exposure。
这与 EP20 的正 beta 目标并不冲突，因为 incremental alpha 并非必要门；但若这些 exposure 同时造成成本、拥挤、容量或
回撤超预算，则实际 sleeve 仍会失败。当前 P5 代理又存在 retrospective look-ahead 与低 coverage，无法用它证明 P4
只是假 alpha，也无法用它证明 R3 是更好的可执行版本。

### 27.3 Total Momentum 与 Low Vol comparators

P0 Total Momentum 的 favorable decile 为 -0.26%/月，spread 仅 +0.34%，且 early/late 反转，符合研究计划所述“普通
12-1 momentum 在 A 股较弱”的外部背景。它不构成有吸引力的 long-only comparator。

P6 Low Vol 的 favorable decile 为 +1.03%/月，EW/VW、quintile/decile、early/late 均为正，gross risk proxy 也明显优于
P1/P4。它是本轮最强的实际金融基准：任何未来 residual sleeve 都应回答，是否只是换一种方式获得 low-vol/size/board
暴露，以及在同一 next-open 和成本口径下是否比简单 Low Vol 更有用途。P6 仍是 comparator-only，不能单独授权 20C。

## 28. 实际 A 股金融场景评估

即使 20C 被硬门阻断，现有证据仍可对实际应用给出以下条件性判断：

1. **Long-short 不是可执行收益。** P4 的 +1.62% spread 很大一部分来自 unfavorable bucket 的 -1.04%。A 股 short leg
   通常受融券可得性、成本和容量限制；实际 long-only 可获得的是 favorable gross +0.58%，不是完整 spread。
2. **Gross close-to-close 不是可部署 NAV。** 本轮没有 next-open fill、涨跌停、停牌 blocked exit、现金占用、stateful
   capital、手续费、印花税、transfer fee、slippage 与 1% ADV capacity。0.58%/月的 P4 gross 在这些摩擦后可能显著收缩。
3. **P4 有风险预算上的初步可行性，但尚无经济门证据。** 它的月度 proxy p10=-5.48%、ES10=8.29%、MDD=31.97%，
   表面上落在 20A 冻结阈值内；但正式阈值基于 daily stateful NAV，不能在 20B 宣告 pass。
4. **样本缺失不是随机小问题。** P4 信号就绪 63 个月、project 可评价仅 43 个月；unknown bridge 虽少，却按 whole-bucket
   规则删去 20 个月。若实际执行系统不能补齐 delisting/security-master/status bridge，正收益估计会持续低功效。
5. **P5 暂不适合替代 P4。** 它 coverage 仅约 59.6%，EW favorable 近零，且只有 1 个 fully-post project-evaluable month。
   实际 forward 应同时保留 R2 market-only comparator 与冻结的 R3 primary，并监控 2025 snapshot age；不得用历史 P5
   结果删除 R2。
6. **Low Vol 是必须面对的机会成本。** P6 gross favorable、波动和 MDD proxy 均优于 P4。若未来 P4 在成本后不优于或不能
   补充 Low Vol，最简单的正 beta sleeve 可能是 Low Vol，而非 residual momentum；这一判断只能在获授权的同口径 bridge
   中确认。
7. **TrendPV 当前不具备直接工程化理由。** P1 的 full/early 反向与高 MDD proxy 表明，直接把 raw score 转成 long-only
   top bucket 风险很高。除非补 exact inputs 或在新的、预注册的 forward regime 中重新验证，否则不应按晚期结果追涨式修复。

## 29. 核心发现与洞察

综合 requirement、research plan 和 sealed data，可归纳为：

- **最重要的正向发现是 P4 的方向一致性，而不是 gate pass。** P4 在 EW/VW、5/10 buckets、full/early/late 和 LOMO/LOIO
  下大体保持正 spread，是 residual family 的有效设计线索；失败原因主要是有效月份不足，而不是公式或方向全面失败。
- **最重要的负向发现是 P1 的稳健反向。** Project-strict 与 paper-fill、EW 与 VW、quintile 与 decile 均未恢复预期方向；
  这比单一规格的负数更有诊断价值。
- **P4 的“alpha 形态”可能是可持有 beta source。** P5 中和 size/board 后 spread 大幅下降，说明 P4 很可能依赖这些风格
  exposure。研究目标允许这种来源，只要未来成本后绝对收益和风险预算通过；不应把“不是纯 alpha”误写成失败。
- **P5 目前不能用于归因定案。** 高维 static board proxy、retrospective 回填和较低 coverage 同时存在，使“中和后归零”
  既可能是正确归因，也可能是测量误差/过度中和。
- **Low Vol 的强势要求重新校准比较基准，但不能改 family。** 它显示简单风险排序可能已捕获更稳定的正收益暴露；未来
  必须做同口径 paired utility comparison，而不是只比较 paper spread。
- **时间样本是主要瓶颈。** TrendPV 的 400 sessions + 38 coefficients、Residual 的 36+11 months，以及 strict unknown
  bridge 共同使 2017–2026 的历史窗口天然低功效。这个瓶颈不能靠缩短 lookback、重切 folds 或选择 late period 修复。

## 30. Gate truth table 与下一步边界

| gate | 状态 | 数据依据 | 允许的解释 |
|---|---|---|---|
| P1 formula integrity | True | 18 predictors、93 complete coefficients、rank/timing audits | 实现可物化 |
| P1 sample support | False | 35 < 48；22/13 < 24/24 | underpowered |
| P1 paper-sort | False | full/early spread 为负 | raw-score 未复现预期 morphology |
| P1 positive exposure | False | full/early favorable 为负且样本门失败 | 不生成 20C |
| P4 formula integrity | True | 101,273 sequential regression rows 全 pass | R2 adaptation 可物化 |
| P4 sample support | False | 43 < 60；25/18 < 30/30 | underpowered |
| P4 paper-sort | False | 方向为正，但 materialization gate 被样本门阻断 | 不能写 pass |
| P4 positive exposure | False | 三折点估计为正，但 materialization gate 被样本门阻断 | 仅 design signal |
| P5 materialization | True | ridge/scope audit 完整 | retrospective sensitivity 可用 |
| P5 diagnostic gate | False | 46 < 60，且 late spread 为负 | 不可替代 R2 |
| P0/P6 materialization | True / True | comparator metrics 完整 | 只作比较，不授权 20C |
| 20C requirement generation | False | P1/P4 均未通过完整 positive-exposure gate | 不得生成/执行 20C |

在当前 contract 下，唯一合规结论仍是 `20B_underpowered_design_diagnostic`。如未来希望继续评估论文与实际金融场景，
研究层面可考虑补宽截面 PIT market cap、PIT E/P、risk-free、CH-3 vintage、historical PIT industry 和更长历史；但这
属于新数据与新 contract/version 的工作，不是对 v5 的事后修补。无论是否补 exact data，任何可部署判断仍必须经过独立
授权的 next-open、stateful、cash-inclusive、cost/capacity bridge 与冻结 true-forward confirmation。

本增补不生成 20C requirement，不改变 residual primary
`C3_RESMOM_R3_BOARD_ADAPTATION`，也不改变以下授权：

```text
20C_execution_authorized = false
policy_training_authorized = false
policy_replay_authorized = false
portfolio_optimization_authorized = false
deployment_authorized = false
```
