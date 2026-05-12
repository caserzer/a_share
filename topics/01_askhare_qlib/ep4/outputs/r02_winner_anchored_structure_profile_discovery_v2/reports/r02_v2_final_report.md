# EP4 R02 V2 赢家锚定结构画像发现报告

## 1. 执行结论

- Final decision: `revise_profile_search_space`
- 本轮结论不是进入 R03，也不是形成交易策略；它更像一次“赢家画像能否转成 action-time prior”的压力测试。
- R02 V2 确实找到了赢家窗口里反复出现的结构，但被保留下来的结构主要仍是 momentum、near-high、gap/acceleration 这类强势状态。
- 这些结构在 train 上有正的 posterior / likelihood ratio，但 validation 和 robustness 没有同时满足稳定性与执行诊断要求；3 个 frozen representative 最终都被标为 `audit_only_removed_after_robustness`。
- 因此当前证据支持“继续修正搜索空间”，不支持把这些 family 交给 R03 做 evidence accumulation。

最重要的边界：

- Stage A winner coverage 是“已知大赢家在 `t0..t0+30` 画像窗口中出现过某结构”的覆盖率。
- Stage B action-time prior / posterior precision / likelihood ratio 是“在完整 PIT stock-day 分母上，当天可观察信号触发后，对未来大赢家概率的估计”。
- 两者不是同一个概率，不能用 Stage A 覆盖率替代 Stage B posterior。

## 2. Reference Event 与样本有效性

R02 V2 使用自建 action-time label panel 重新构造 canonical big-winner reference，不依赖 R02 V1 cache 作为 authority。

| 项目 | 数值 |
|---|---:|
| R02 V2 reference event 总数 | 802 |
| Stage A 可用 train complete profile event | 448 |
| 非 Stage A 事件 | 354 |
| raw positive action-time rows 合计 | 34,028 |
| 每个 episode raw positive rows 中位数 | 22 |
| 每个 episode raw positive rows p90 | 107 |

R01 V3 reference reconciliation 通过：

| 指标 | 数值 |
|---|---:|
| R02 V2 reference count | 802 |
| R01 V3 reference count | 838 |
| instrument overlap rate | 0.9881 |
| instrument-year overlap rate | 0.9611 |
| same reference date rate | 0.6920 |
| within-20d reference date rate | 0.7531 |
| overlap status | `passed` |

解读：

- instrument 和 instrument-year overlap 很高，说明 V2 reference pool 与 R01 V3 大体一致。
- same-date 只有 69.2%，within-20d 只有 75.3%，说明“同一赢家事件的参考日定义”仍有显著偏移。这不是 leakage，但会影响 Stage A 画像窗口的形态。
- 这次 drift 没有阻塞研究，因为 overlap status passed；但如果下一轮要精细比较 R01/R02 的 entry timing，reference date policy 仍需要保持显式审计。

## 3. Candidate Grid 与 Stage A 漏斗

候选字典共 588 个候选，全部由 config-declared feature atoms、pattern template、window、lookback、dedup grid 机械生成。

| group | candidate count |
|---|---:|
| momentum_persistence | 72 |
| industry_market_support | 72 |
| volume_money_confirmation | 72 |
| pullback_hold_and_recovery | 72 |
| relative_strength_confirmation | 72 |
| acceleration_and_gap | 60 |
| volatility_contraction_expansion | 60 |
| near_high_persistence | 60 |
| distribution_absence | 24 |
| failure_absorption | 24 |

Stage A 结果：

| 项目 | 数值 |
|---|---:|
| Stage A candidates | 588 |
| Stage A passed | 31 |
| Stage A rejected | 557 |

Stage A passed group 分布：

| group | passed count |
|---|---:|
| momentum_persistence | 10 |
| acceleration_and_gap | 8 |
| volume_money_confirmation | 6 |
| near_high_persistence | 5 |
| relative_strength_confirmation | 2 |

主要 reject 原因：

| failed rule | count |
|---|---:|
| `not_generic_strength_proxy` | 467 |
| `max_action_time_background_signal_rate` | 440 |
| `min_winner_vs_background_coverage_lift` | 425 |
| `min_winner_vs_background_coverage_lift_ci90_lower` | 339 |
| `max_trigger_days_per_event_p90` | 204 |
| `min_winner_coverage` | 132 |
| `min_winner_coverage_ci90_lower` | 92 |
| `min_years_present` | 42 |

Stage A top structures 主要是动量持续：

| structure | group | feature/window | winner coverage | background coverage | lift | action-time background rate |
|---|---|---|---:|---:|---:|---:|
| `r02v2_momentum...ret5...full_window...3d` | momentum | ret5 full | 0.6116 | 0.2509 | 2.44 | 0.0348 |
| `r02v2_momentum...ret5...full_window...5d` | momentum | ret5 full | 0.6116 | 0.2509 | 2.44 | 0.0680 |
| `r02v2_momentum...ret20...continuation...3d` | momentum | ret20 continuation | 0.3705 | 0.0969 | 3.82 | 0.0855 |
| `r02v2_momentum...ret20...point...continuation` | momentum | ret20 continuation | 0.3304 | 0.0786 | 4.20 | 0.0759 |
| `r02v2_momentum...ret5...point...continuation` | momentum | ret5 continuation | 0.6295 | 0.2835 | 2.22 | 0.0897 |

初步发现：

- Stage A 证明“赢家早期窗口中确实有重复结构”，但这些结构几乎都围绕涨幅、近高、RPS、量能、gap。
- `pullback_hold_and_recovery`、`volatility_contraction_expansion`、`distribution_absence`、`failure_absorption` 没有进入 Stage B，说明当前 grid 没有找到“更接近风险控制或结构吸收”的有效画像。
- 很多赢家画像在背景分母中也常见，因此被 generic / dense gate 拦截。这是本轮最核心的负面证据：画像重复不等于 action-time 稀缺 prior。

## 4. Stage B Action-Time Prior Calibration

31 个 Stage A passed candidates 被映射回完整 PIT stock-day action-time denominator 评估。

Train 上最强的候选：

| structure | group | signal_n | signal_rate | base rate | posterior | primary_LR | LR CI90 lower | precision lift | EV_R | failed_seed_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gap persistence 3d continuation | acceleration_and_gap | 418 | 0.0023 | 0.1453 | 0.2508 | 1.9690 | 1.6248 | 1.7260 | 0.2280 | 0.3995 |
| gap persistence 5d continuation | acceleration_and_gap | 1,169 | 0.0065 | 0.1453 | 0.2506 | 1.9665 | 1.7708 | 1.7243 | -0.1644 | 0.3841 |
| gap point full-window | acceleration_and_gap | 1,460 | 0.0081 | 0.1453 | 0.2389 | 1.8461 | 1.6923 | 1.6440 | -0.1654 | 0.3705 |
| ret5 persistence | momentum_persistence | 2,302 | 0.0127 | 0.1453 | 0.2317 | 1.7738 | 1.6267 | 1.5945 | -0.1707 | 0.3827 |
| ret5 persistence compact | momentum_persistence | 2,025 | 0.0112 | 0.1453 | 0.2219 | 1.6771 | 1.5323 | 1.5269 | -0.2284 | 0.3906 |

观察：

- Train 上确实存在正向 prior：base rate 14.53%，top posterior 约 25.08%，primary_LR 接近 1.97。
- 但是 EV_R 很脆弱。只有最稀疏的 gap persistence 在 train 上 EV_R 为正；多数高 LR 候选的 EV_R 仍为负。
- failed_seed_rate 普遍在 0.35-0.40 附近，说明“更容易成为大赢家”与“短期失败风险低”并没有同时成立。
- 这更像是“强势状态提升 winner posterior”，不是“可执行、低回撤、可进入 R03 的 evidence family”。

## 5. Frozen Representatives 与 OOS 表现

Stage C frozen 3 个 representative，满足数量和 group 多样性下限，但全部因 robustness 结果被移出 R03 pool。

| representative | structure | group | train posterior | train LR | train EV_R | status |
|---|---|---|---:|---:|---:|---|
| `r02v2_rep_01` | gap persistence, continuation, 3d | acceleration_and_gap | 0.2508 | 1.9690 | 0.2280 | `audit_only_removed_after_robustness` |
| `r02v2_rep_02` | close near high20 persistence, 5d | near_high_persistence | 0.1702 | 1.2062 | -0.0631 | `audit_only_removed_after_robustness` |
| `r02v2_rep_03` | close near high20 persistence, 3d | near_high_persistence | 0.1671 | 1.1801 | -0.0562 | `audit_only_removed_after_robustness` |

跨 split 明细：

| representative | split | signal_n | signal_rate | posterior | primary_LR | precision lift | EV_R | failed_seed_rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| gap persistence 3d | train | 418 | 0.0023 | 0.2508 | 1.9690 | 1.7260 | 0.2280 | 0.3995 |
| gap persistence 3d | validation | 80 | 0.0007 | 0.1324 | 2.8291 | 2.5871 | -0.5104 | 0.3375 |
| gap persistence 3d | robustness | 280 | 0.0026 | 0.0929 | 0.9325 | 0.9388 | -1.2354 | 0.6321 |
| near-high 5d | train | 3,078 | 0.0170 | 0.1702 | 1.2062 | 1.1711 | -0.0631 | 0.3034 |
| near-high 5d | validation | 1,493 | 0.0137 | 0.0563 | 1.1058 | 1.0998 | -0.5632 | 0.2257 |
| near-high 5d | robustness | 1,918 | 0.0175 | 0.0732 | 0.7193 | 0.7398 | 0.2367 | 0.2059 |
| near-high 3d | train | 2,336 | 0.0129 | 0.1671 | 1.1801 | 1.1500 | -0.0562 | 0.3104 |
| near-high 3d | validation | 1,078 | 0.0099 | 0.0496 | 0.9689 | 0.9704 | -0.5166 | 0.2161 |
| near-high 3d | robustness | 1,406 | 0.0128 | 0.0675 | 0.6594 | 0.6824 | 0.3388 | 0.1977 |

关键判断：

- gap representative 在 validation 的 LR 仍强，但 validation EV_R 为 -0.5104，robustness LR 跌到 0.9325，EV_R 跌到 -1.2354；它不是稳定 family。
- near-high representative 在 train 很稳，但 validation/robustness posterior 接近或低于 base rate，robustness LR 明显低于 1。
- robustness 中 near-high EV_R 转正并不够，因为其 big-winner posterior / LR 失败；这说明收益诊断与大赢家识别不是同一个问题。

## 6. Prior Decomposition 与集中度线索

### 6.1 年份分解

gap representative 的年份差异很大：

| split/year | signal_n | posterior | LR | stable flag |
|---|---:|---:|---:|---|
| train 2017 | 2 | 0.0000 | 0.0000 | False |
| train 2018 | 44 | 0.0455 | 0.7630 | False |
| train 2019 | 53 | 0.1400 | 1.5405 | True |
| train 2020 | 155 | 0.4056 | 2.0286 | True |
| train 2021 | 164 | 0.1579 | 0.9826 | False |
| validation 2022 | 59 | 0.1250 | 2.1864 | True |
| validation 2023 | 21 | 0.1667 | 6.1595 | True |
| robustness 2024 | 181 | 0.0549 | 0.6175 | False |
| robustness 2025 | 99 | 0.4211 | 5.1716 | True |

解读：

- gap signal 的证据高度 regime/year-dependent。2020、2022、2023、2025 很强，但 2018、2021、2024 失败。
- 特别是 robustness 被 2024 拉垮，而 2025 又很强；这提示它可能依赖市场风险偏好、涨停/跳空后延续环境，不能作为 unconditional family。

near-high representative 的年份分解也不稳：

| structure | split/year | signal_n | posterior | LR | stable flag |
|---|---|---:|---:|---:|---|
| near-high 5d | train 2020 | 866 | 0.3123 | 1.3504 | True |
| near-high 5d | train 2021 | 952 | 0.1518 | 0.9382 | False |
| near-high 5d | validation 2022 | 751 | 0.0671 | 1.1014 | True |
| near-high 5d | validation 2023 | 742 | 0.0393 | 1.2599 | True |
| near-high 5d | robustness 2024 | 942 | 0.0597 | 0.6752 | False |
| near-high 5d | robustness 2025 | 976 | 0.1017 | 0.8050 | False |

结论：near-high 是更宽的状态描述，OOS 中不稳定，不能单独解释为 winner evidence。

### 6.2 市场宽度分解

Train 内 gap representative 在所有 market breadth bucket 中 LR 都大于 1：

| bucket | signal_n | posterior | LR |
|---|---:|---:|---:|
| lt20 | 22 | 0.4211 | 4.0356 |
| 20_40 | 97 | 0.2817 | 2.5961 |
| 40_60 | 136 | 0.2188 | 1.5402 |
| 60_80 | 92 | 0.3231 | 2.5058 |
| gte80 | 71 | 0.1406 | 1.2417 |

这说明 gap 不是只在单一 market breadth bucket 上成立；但样本非常稀疏，尤其 lt20 只有 22 个信号，不能过度解释。

near-high 在 gte80 bucket 反而较弱：

| structure | bucket | signal_n | posterior | LR |
|---|---|---:|---:|---:|
| near-high 5d | gte80 | 535 | 0.1148 | 0.9839 |
| near-high 3d | gte80 | 457 | 0.0909 | 0.7588 |

猜测：过热或全市场普涨时，“靠近高点”会变成拥挤状态，区分度下降。

### 6.3 流动性分解

gap representative 在 train 的 q1-q5 liquidity bucket 中 LR 都大于 1，q3 最强：

| liquidity bucket | signal_n | posterior | LR |
|---|---:|---:|---:|
| q1 | 31 | 0.1786 | 2.2971 |
| q2 | 58 | 0.2128 | 2.0321 |
| q3 | 73 | 0.3793 | 3.4865 |
| q4 | 107 | 0.2308 | 1.3691 |
| q5 | 149 | 0.2308 | 1.1322 |

near-high 在 q1/q5 边缘 bucket 弱一些，q2-q4 较好。这可能意味着 near-high 更依赖中间流动性状态，而不是最高流动性或最低流动性。

### 6.4 market-cap bucket 无效

`r02_v2_bucket_boundaries.csv` 显示 market-cap bucket 的 `missing_mcap_share = 1.0`，状态为 `invalid_missing_mcap_share`。因此本轮不能对市值集中度做有效判断。

这不是研究结论本身，而是数据/字段接入问题：报告中的 market-cap decomposition 不能用于解释 candidate 是否偏大盘或小盘。

## 7. Mandatory Baselines

| baseline | split | signal_n | winner/base rate | EV_R | status |
|---|---|---:|---:|---:|---|
| no signal | train | 181,227 | 0.1453 | -0.2162 | passed |
| R01 V3 seed | train | 14,428 | 0.1654 | -0.1051 | passed |
| no signal | validation | 108,970 | 0.0512 | -0.6792 | passed |
| R01 V3 seed | validation | 8,429 | 0.0576 | -0.5000 | passed |
| no signal | robustness | 109,510 | 0.0990 | 0.1511 | passed |
| R01 V3 seed | robustness | 8,793 | 0.1097 | 0.2100 | passed |
| R02 V1 broad-strength reference | train | 36,250 | n/a | -0.1308 | resolved |

解释：

- R01 V3 seed 的 posterior 比 no-signal base rate 略高，但提升有限。
- R02 V2 top gap 在 train 上 posterior 和 LR 明显强于 R01 V3 seed，但 validation/robustness 执行表现失败。
- 因此 V2 不是“没有找到任何先验”，而是“找到的先验不能稳定转化为可执行 family”。

## 8. Gate Audit

| gate | actual | expected | status |
|---|---:|---:|---|
| min_3_non_baseline_frozen_representatives | 3 | 3 | passed |
| min_2_distinct_structure_groups | 2 | 2 | passed |
| r01_v3_reference_overlap_rate | 0.9881 | >= 0.80 | passed |
| validation_at_least_2_lr_ci_lower_ge_1 | 0 | 2 | failed |
| robustness_at_least_2_lr_ge_1 | 0 | 2 | failed |
| validation_at_least_2_ev_ge_minus_005 | 0 | 2 | failed |
| robustness_at_least_2_ev_ge_minus_005 | 2 | 2 | passed |
| no_major_validator_leakage_finding | True | True | passed |

结论：

- 数量门槛与 reference reconciliation 都过了。
- 真正失败的是 OOS 统计稳定性和 validation execution feasibility。
- 这正是 `revise_profile_search_space`，而不是 `go_to_r03_evidence_accumulation` 的原因。

## 9. Findings, Insights, Guesses

### 9.1 已验证发现

1. 赢家早期窗口有强重复画像，但重复画像集中在强势状态。
2. Stage A 的 winner-vs-background lift 可以筛掉大量泛化状态，但通过 Stage A 的候选进入 Stage B 后仍会暴露 OOS 不稳。
3. gap/acceleration 是本轮最有信息量的 action-time prior，但它高度稀疏、年份依赖强，且 robustness 失败。
4. near-high 是较稳定出现的赢家画像，但 action-time posterior 不够稳定，尤其 robustness LR 低于 1。
5. 当前 grid 没有找到有效的 pullback/recovery、failure absorption、distribution absence 类结构。这些本应更接近“降低回撤、提高执行质量”的方向，但本轮没有证据支持。

### 9.2 初步 insight

- “成为大赢家”与“短期执行路径可承受”仍然分离。top gap train LR 很强，但 failed_seed_rate 仍约 40%，robustness EV_R 很差。
- 单纯从赢家窗口倒推结构，容易重新发现上涨之后自然可见的强势状态；这些状态能提高 posterior，但不一定能提供可执行价格、可控风险或可复用 entry。
- R02 V2 比 V1 的价值在于更清楚地证明了这个问题：即使先看赢家窗口，最后落到 action-time denominator 后，generic strength 仍然是主要成分。

### 9.3 猜测和下一步方向

这些是猜测，不是 validated evidence：

- gap/acceleration 可能需要 regime-conditioned 处理，而不是 unconditional family。特别是 2024 与 2025 的差异提示市场风险偏好或涨停后续流动性环境很关键。
- near-high 可能只适合作为 context feature，不适合作为独立 evidence family。它可能需要和“回撤不破坏 / 量能不派发 / 行业强度不退潮”结合。
- 下一轮如果继续结构发现，应该减少 broad strength 维度，强制加入 risk-state、failure-absorption、post-gap hold、bad-trade early warning 之类的条件，否则大概率继续找回高密度强势状态。
- 如果目标仍是“可执行价格下同时降低回撤、保留大 winner 上行空间”，下一轮不应只优化 posterior，应把 failed_seed_rate、validation EV_R、robustness LR 同时作为 primary discovery objective。

## 10. 当前注意事项

- 本报告只更新 markdown artifact，没有修改代码、config 或重新执行 pipeline。
- market-cap bucket 在本轮输出中不可用，`missing_mcap_share = 1.0`，不能做市值分层结论。
- validation / robustness 没有 bootstrap CI，下游判断主要依赖点估计 gate；这符合当前 artifact，但解释时要保守。
- 所有 R02 V2 的 `unit_return_R` 都是通用诊断执行指标，不可与 R01 V3 `return_R` 直接数值比较。

## 11. Required Report Tokens

Final decision, action-time prior, posterior precision, likelihood ratio, execution feasibility, Stage A winner coverage, Stage B action-time prior.
