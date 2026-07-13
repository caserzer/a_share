# 20B-SRC Short-Term Residual Continuation Family 设计诊断

## 1. Decision 与授权边界

- terminal state：`20B_SRC_not_identified_design_only`
- historical sample role：`design_contaminated_historical`
- signal/outcome authorization gates：`pass / pass`
- implementation authorized：`true`
- true-forward / 20C / policy / deployment authorization：全部 `false`
- preoutcome / signal / historical bundle：`0f2741d10ea9c3283a304b7a5b838f0f00db48e053b4454a39557f3e146cead7` / `cd6d108a0c6990e5759ab25880dc62033dd1cd76a8c57b76b7e31e4f8d97958c` / `8ac871e63e4b1a01ed407627e3c5c74942bd78ebb88dc6b648aabff087261f90`

20B-SRC 是 outcome-contaminated historical design diagnostic。它在 20B 月度 P4 结果已被观察后提出，任何历史结果都不能形成 true OOS support。

## 2. 新 family 身份

20B-SRC 改变了 signal formation frequency 与 formula family；它不是 20B P4 的 1 周/2 周 holding sensitivity，也不是论文 12-1 Residual Momentum 的 exact replication。

本诊断使用逐日 causal 252-session CSI300 market model、5D/10D immediate residual continuation score，以及 H5/H10 完整 horizon matrix。没有从 grid 中挑选最好组合。

## 3. Input lineage、boundary 与 tradability

冻结历史边界为 `2017-01-03..2026-05-29`。`U_project` 使用 next-session `usable_trade_date` 与 decision-close availability；QFQ filename、全文件 internal instrument 与 canonical id 通过 exact mapping。

20B-SRC 不读取、不推断逐日停牌状态。所有进入 registered decision denominator 的股票均假设可交易；这是一项乐观的设计近似，不能作为成交可行性或 executable/deployable 证据。缺失 qfq mark 仍按 unknown data gap fail closed，不得因“假设可交易”而 carry、补零或插值。

## 4. Weekly calendar 与 daily rolling regression

Decision 是每个 ISO week 的最后一个 exchange session；5D/10D 均为 exchange-session offset。每个 residual 日只用前 252 个 scheduled returns，至少 200 个 paired rows；当日 residual 使用当日 stock/CSI300 return，但回归系数严格只截至前一 session。

Signal firewall 保留 raw-file future rows loaded audit，同时证明 `future_rows_contributed_to_signal=0`、weekly `max_contributing_date<=decision_date`。

## 5. Signal coverage 与 beta

5D/10D residual、matched total continuation 与 Low Vol comparator 均完整物化，warm-up/missing rows 未删除。Style table 共 962 行；weighted beta 缺任一 positive-weight constituent 时 fail closed。

## 6. 完整 2 × 2 matrix

| primary | fold | evaluable weeks | favorable mean | spread mean |
|---|---|---:|---:|---:|
| SRC 5×5 | FULL | 405 | -0.000521 | -0.002469 |
| SRC 5×5 | EARLY | 201 | -0.001605 | -0.002993 |
| SRC 5×5 | LATE | 204 | 0.000547 | -0.001962 |
| SRC 10×10 | FULL | 391 | 0.002806 | 0.000866 |
| SRC 10×10 | EARLY | 191 | -0.001071 | -0.001339 |
| SRC 10×10 | LATE | 200 | 0.006507 | 0.002875 |

Cross 5×10、10×5 以及 total/Low Vol/baseline、EW/VW、quintile/decile、project/complete-case 全部保留在 sealed tables，不能用 cross mapping 替代 primary gate。

## 7. Favorable absolute return 与 spread

Favorable bucket 是 A 股 long-only positive-beta 判断。Favorable-minus-unfavorable 为正不能替代 favorable bucket 绝对收益为正。A 股 long-only 正 beta 判断不得依赖不可执行 short leg。

5×5 positive gate=`False`，sort gate=`False`；10×10 分别为 `False` / `False`。

## 8. Stability 与 dominance

Stability table 共 24 行，分别覆盖 FULL/EARLY/LATE 与每个 frozen calendar year。LODO/LOMO/LOIO 使用 sealed assignments，不重排 bucket；dominance summary 另报告单周/top3 绝对贡献占比与 H5/H10 joint correlation。

## 9. Residual vs total paired attribution

| pair | common weeks | favorable delta | spread delta | vol ratio | ES10 ratio | residualization value |
|---|---:|---:|---:|---:|---:|---|
| SRC3_MKT_RESID_CONT_5D × H5 | 373 | -0.000563 | -0.001203 | 1.012125 | 1.027751 | False |
| SRC4_MKT_RESID_CONT_10D × H10 | 347 | 0.000588 | -0.001759 | 1.072131 | 0.965544 | False |

所有 delta 使用 residual/total 同周共同 evaluable population；没有使用 unpaired arm means。

## 10. Low Vol、size 与 beta overlap

| arm | median corr(-VOL20) | median LowVol Jaccard | median corr(log cap) | scale warning | size warning |
|---|---:|---:|---:|---|---|
| SRC3_MKT_RESID_CONT_5D | -0.023929 | 0.043956 | 0.003959 | False | False |
| SRC4_MKT_RESID_CONT_10D | -0.060328 | 0.034287 | 0.011341 | False | False |

Overall scale/size warning=`False` / `False`；warning 是 morphology modifier，不覆盖正向点估计。

## 11. H5/H10 path decomposition

Primary favorable joint-evaluable path rows=1884。`R_6_10` 由同一 ex-ante weights 下的 `V10/V5-1` 计算，不把 endpoint returns 简单相加，也不构造 continuous NAV。

## 12. Turnover 与 inherited-cost pressure test

| primary | transitions | mean target turnover | mean gross return | break-even multiple | cost feasible |
|---|---:|---:|---:|---:|---|
| SRC3_MKT_RESID_CONT_5D × H5 | 404 | 0.895667 | -0.000382 | -0.209817 | False |
| SRC4_MKT_RESID_CONT_10D × H10 | 390 | 0.692471 | 0.003147 | 2.238834 | True |

费用继承 20A v2，但 stamp tax 以现行 5 bps 统一回放且不含 5 CNY minimum commission；这是乐观 target-turnover proxy，不是实际成交成本或 net return。

## 13. HAC、block bootstrap 与 AFML classification

| matched primary | estimate | nominal HAC p | Holm p |
|---|---:|---:|---:|
| SRC3_MKT_RESID_CONT_5D × H5 | -0.000521 | 0.746405 | 0.845103 |
| SRC4_MKT_RESID_CONT_10D × H10 | 0.002806 | 0.422551 | 0.845103 |

Weekly rows 与 10-session overlapping labels 不是独立证据。样本量、HAC、block bootstrap 和 fold 统计必须按冻结的 weekly/calendar block 口径报告，不能把 instrument rows 或重叠 cohort rows当作独立 N。

AFML utility classification=`20B_SRC_not_identified_design_only`；true-forward freeze recommended=`False`，participation/meta-label research recommended=`False`。这只是 design-only recommendation，不是 support 或执行授权。

## 14. Gate truth table 与 no-authorization footer

| gate | value |
|---|---|
| 5×5 sample / paired support | True / True |
| 10×10 sample / paired support | True / True |
| 5×5 residualization / cost | False / False |
| 10×10 residualization / cost | False / True |
| preoutcome / signal / historical hashes | pass / pass / pass |
| outcome firewall | pass |

本阶段没有 next-open fill、blocked entry/exit、持续资本、现金腿、实际费用扣账、实际滑点或容量；只有继承 20A 冻结成本的 target-turnover pressure-test proxy，因此任何结果都不能称为 deployable sleeve 或 net strategy。

`next_requirement_generation_authorized=false`，`true_forward_execution_authorized=false`，`20C_requirement_generation_authorized=false`，`20C_execution_authorized=false`，`policy_training_authorized=false`，`policy_replay_authorized=false`，`portfolio_optimization_authorized=false`，`deployment_authorized=false`。
