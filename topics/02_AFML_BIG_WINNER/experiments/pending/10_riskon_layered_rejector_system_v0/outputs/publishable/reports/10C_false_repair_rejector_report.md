# 10C False-Repair Rejector Report

## 结论

10C 当前结论是 `10C_false_repair_feature_source_supported`，不是可上线的 false-repair rejector。模型确实识别出了一部分 false-repair / exposure 信号，但所有候选 operating point 都未通过 winner retention 约束，因此没有 `selected_capacity_id` / `selected_threshold_id`。

核心原因很集中：训练集上最好的候选是 `full / keep_9000`，它只 reject 10.00% 样本，训练 utility 为 `0.0795`，false-repair capture lift 为 `+7.80pp`，non-winner exposure lift 为 `+6.90pp`。但它的 `E1_missed_winner` retention 只有 `84.34%`，低于 10C 冻结门槛 `85.00%`，因此被阻断。更激进的 keep_8750 / keep_8500 / keep_8250 / keep_8000 虽然捕获更多 false-repair，但 winner / E1-missed winner injury 更重，utility 也转负。

这说明 10C 不是“没有信号”，而是信号和 winner-like 行为重叠过高。false-repair score 能找到更高 MFE、更高 confirm 倾向的活跃事件，其中一部分正是我们不想杀掉的 winner 或 E1-missed winner。

## Run State

| item | value |
|:--|:--|
| decision | `10C_false_repair_feature_source_supported` |
| selected population | `10A__same_instrument_cooldown_10d` |
| selected denominator | `post_dedup_risk_on_r_core` |
| selected 10C gate | none |
| block reason | `no_train_supported_capacity` |
| upstream source caveat | `true` |
| 10B selected gate used for cascade readout | `regularized_logistic_fast_fail_10d_l2_v1 / full / keep_9400` |
| 10B selected reject fraction | `0.0600` |
| 10B manifest selected gate match | `true` |
| input failures | none |
| config hash | `e9e3c46d5e19f76ccf22a2584c80d220188b9e5d33a0ca2debb7e473225b0ac9` |
| utility hash | `7b1e43bc94db280d3527bcc1d8510df32c17e8cb6942850595e5b97cafb4e978` |

## Input Audit

所有输入可读且 schema audit 通过。10B manifest / scores 在实现中被标为 supported-only 输入：当前文件存在且通过 schema，因此 cascade readout 可以计算；未来如果 10B local cache 缺失，10C 仍可输出 standalone diagnostics，但不能输出 rejector-supported 结论。

| required_flag | schema_status | artifact_n |
|:--|:--|--:|
| `true` | `pass` | 14 |
| `false` | `pass` | 3 |

| artifact_id | required_flag | exists_flag | schema_status | row_count |
|:--|:--|:--|:--|--:|
| `upstream_10b_manifest` | `false` | `true` | `pass` | 1 |
| `upstream_10b_scores` | `false` | `true` | `pass` | 221228 |

输出规模：

| artifact | rows | columns |
|:--|--:|--:|
| `false_repair_power_gate_readout.csv` | 30 | 36 |
| `false_repair_threshold_frontier.csv` | 10 | 20 |
| `winner_retention_audit.csv` | 30 | 19 |
| `exposure_efficiency_readout.csv` | 30 | 13 |
| `mfe_confirm_relation_readout.csv` | 96 | 14 |
| `cascade_overlap_attribution.csv` | 9 | 12 |
| `post_dedup_false_repair_scores.parquet` | 158020 | 32 |

## Population

10C 使用 10A 默认 post-dedup population，按 `train / validation / robustness` 固定切分。false-repair positive 在 train 中占比较高，但 validation / robustness 中 winner 分布差异很大，这也是 OOS retention 需要单独审计的原因。

| split | sample_n | false_repair_positive_n | false_repair_rate | winner_n | winner_rate | E1_missed_winner_n | bridge_winner_n |
|:--|--:|--:|--:|--:|--:|--:|--:|
| train | 8318 | 3025 | 36.37% | 1491 | 17.92% | 811 | 1009 |
| validation | 2514 | 709 | 28.20% | 161 | 6.40% | 64 | 111 |
| robustness | 4970 | 1299 | 26.14% | 995 | 20.02% | 482 | 675 |

## Model Registry

10C 训练两个 L2 logistic false-repair 模型：一个 full feature set，一个去掉 label-mechanism-overlap family 的 ablation。两者训练状态均为 `pass`，训练目标均为 `frozen_false_repair_20d_label`，训练 split 只使用 `train`。

| ablation_id | feature_count | dropped_constant | dropped_missing | train_fit_rows | train_positive_n | train_weight_sum | status |
|:--|--:|--:|--:|--:|--:|--:|:--|
| `full` | 46 | 2 | 0 | 8318 | 3025 | 9560.0145 | `pass` |
| `no_label_mechanism_overlap` | 33 | 2 | 0 | 8318 | 3025 | 9560.0145 | `pass` |

## Train Frontier

训练集没有任何 row 同时满足 capture / exposure / winner retention / E1-missed retention / utility。最接近的是 `full / keep_9000`，但仍被 `e1_missed_retention` 阻断。

| ablation_id | capacity | reject_rate | FR caught | FR lift | exposure lift | winner retention | E1 retention | bridge retention | utility | blocker |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| `full` | `keep_8000` | 20.00% | 990 | +12.53pp | +11.87pp | 79.41% | 71.89% | 86.72% | -1.0301 | winner, wrong-kill, E1, utility |
| `full` | `keep_8250` | 17.50% | 877 | +12.10pp | +11.36pp | 82.23% | 75.09% | 89.00% | -0.5949 | winner, wrong-kill, E1, utility |
| `full` | `keep_8500` | 15.00% | 778 | +10.91pp | +10.16pp | 84.84% | 77.81% | 91.38% | -0.2156 | winner, wrong-kill, E1, utility |
| `full` | `keep_8750` | 12.50% | 662 | +9.82pp | +9.17pp | 87.32% | 81.13% | 92.96% | -0.0492 | E1, utility |
| `full` | `keep_9000` | 10.00% | 547 | +7.80pp | +6.90pp | 89.60% | 84.34% | 94.55% | 0.0795 | E1 |
| `no_label_mechanism_overlap` | `keep_8000` | 20.00% | 924 | +10.35pp | +9.30pp | 77.13% | 68.68% | 85.53% | -1.4531 | winner, wrong-kill, E1, utility |
| `no_label_mechanism_overlap` | `keep_8250` | 17.50% | 814 | +10.02pp | +8.73pp | 79.34% | 71.27% | 87.81% | -1.1084 | winner, wrong-kill, E1, utility |
| `no_label_mechanism_overlap` | `keep_8500` | 15.00% | 714 | +8.79pp | +7.66pp | 82.29% | 74.85% | 90.19% | -0.6521 | winner, wrong-kill, E1, utility |
| `no_label_mechanism_overlap` | `keep_8750` | 12.50% | 617 | +8.33pp | +7.50pp | 85.78% | 78.42% | 92.96% | -0.2081 | E1, utility |
| `no_label_mechanism_overlap` | `keep_9000` | 10.00% | 510 | +6.58pp | +5.75pp | 88.80% | 82.37% | 95.34% | -0.0371 | E1, utility |

Row blocker 分布也支持同一个结论：

| split | dominant blockers | row_n |
|:--|:--|--:|
| train | winner + wrong-kill + E1 + utility | 6 |
| train | E1 + utility | 3 |
| train | E1 only | 1 |
| validation | winner + wrong-kill + E1 + utility | 10 |
| robustness | winner + wrong-kill + E1 + utility | 8 |
| robustness | E1 + utility | 2 |

## Best Candidate Deep Dive

`full / keep_9000` 是唯一 train utility 为正的候选，但它只差一点点没有过 E1 retention floor。这个 operating point 的好处和代价都很清楚。

| metric | value |
|:--|--:|
| train sample_n | 8318 |
| rejected_n | 832 |
| rejected fraction | 10.00% |
| false-repair positives caught | 547 |
| random false-repair positives caught | 311 |
| false-repair capture rate | 18.08% |
| random capture rate | 10.28% |
| false-repair capture lift | +7.80pp |
| candidate precision | 65.75% |
| rejected winners | 155 |
| winner retention | 89.60% |
| E1-missed retention | 84.34% |
| bridge retention | 94.55% |
| train utility | 0.0795 |
| blocker | `e1_missed_retention` |

Exposure 角度同样显示它有真实 signal，但 signal 不够 winner-safe：

| split | non-winner exposure before | candidate exposure rejected | candidate reduction | random reduction | lift vs random | all rejected exposure | winner rejected exposure |
|:--|--:|--:|--:|--:|--:|--:|--:|
| train | 83549 | 14404 | 17.24% | 10.34% | +6.90pp | 24642 | 4510 |
| validation | 20177 | 3724 | 18.46% | 11.91% | +6.54pp | 7366 | 1136 |
| robustness | 32900 | 6695 | 20.35% | 10.98% | +9.37pp | 14311 | 3724 |

## OOS Stress

OOS 结果说明 10C 的主要失败不是 train-only overfit，而是 winner retention 在 validation 中明显不稳。即便最保守的 `keep_9000`，validation winner retention 仍只有 75.78% 到 75.16%，远低于 supported gate 要求。

| ablation_id | capacity | split | FR lift | winner retention | E1 retention | utility | blocker |
|:--|:--|:--|--:|--:|--:|--:|:--|
| `full` | `keep_9000` | train | +7.80pp | 89.60% | 84.34% | 0.0795 | E1 |
| `full` | `keep_9000` | validation | +7.48pp | 75.78% | 57.81% | -2.1743 | winner, wrong-kill, E1, utility |
| `full` | `keep_9000` | robustness | +10.93pp | 87.14% | 79.05% | -0.1415 | E1, utility |
| `no_label_mechanism_overlap` | `keep_9000` | train | +6.58pp | 88.80% | 82.37% | -0.0371 | E1, utility |
| `no_label_mechanism_overlap` | `keep_9000` | validation | +7.48pp | 75.16% | 59.38% | -2.1588 | winner, wrong-kill, E1, utility |
| `no_label_mechanism_overlap` | `keep_9000` | robustness | +8.08pp | 85.13% | 75.93% | -0.3380 | E1, utility |

`train_only_threshold_instability.csv` 只有 `summary / not_selected`，这是正确状态：没有 selected 10C gate，因此不应强行做 CV threshold stability 结论。

## Cascade Readout

由于 10C 没有 supported gate，cascade attribution 是 10B-only baseline，不是 10B+10C 联合 rejector。它用于说明当前 Layer 1 已经造成的密度和 retention 成本。

| split | rows | 10B rejected_n | reject_rate | false-repair positives caught | false-repair capture | non-winner exposure reduction | winner retention | E1 retention | bridge retention |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 8318 | 500 | 6.01% | 230 | 7.60% | 7.77% | 94.03% | 91.37% | 95.14% |
| validation | 2514 | 151 | 6.01% | 50 | 7.05% | 7.17% | 96.27% | 96.88% | 96.40% |
| robustness | 4970 | 299 | 6.02% | 105 | 8.08% | 7.68% | 95.78% | 94.19% | 97.19% |

10B-only gate 的 retention 明显比 10C standalone keep_9000 更稳。10C 若要作为 Layer 2 叠加，必须证明 incremental false-repair capture 大于新增 winner injury；当前没有任何 10C threshold 能满足这个 supported condition。

## MFE / Confirm Relation

MFE readout 是解释 retention injury 的关键。以 `full / keep_9000` 为例，candidate rejected bucket 的 MFE 往往高于 accepted bucket，validation / robustness 的 confirm_20 positive rate 也明显更高。这意味着模型抓到的是“高活动、高波动、部分会确认”的事件，而不是纯粹的坏修复。

| split | bucket | row_n | confirm_20_positive_rate | mfe_20d_mean | mfe_20d_median | label mismatch |
|:--|:--|--:|--:|--:|--:|--:|
| train | candidate_rejected | 832 | 33.65% | 16.53% | 10.51% | 0 |
| train | candidate_accepted | 7486 | 35.72% | 13.41% | 9.21% | 0 |
| train | random_rejected | 832 | 36.06% | 14.07% | 9.82% | 0 |
| validation | candidate_rejected | 252 | 31.75% | 15.08% | 11.11% | 0 |
| validation | candidate_accepted | 2262 | 19.76% | 8.00% | 5.66% | 0 |
| validation | random_rejected | 252 | 17.06% | 8.31% | 5.42% | 0 |
| robustness | candidate_rejected | 497 | 37.02% | 17.36% | 11.78% | 0 |
| robustness | candidate_accepted | 4473 | 29.64% | 11.28% | 7.09% | 0 |
| robustness | random_rejected | 497 | 28.37% | 10.54% | 6.64% | 0 |

这个结果对策略解释很重要：10C false-repair score 对 “false repair” 有识别力，但这个 label 仍混入了不少 future-confirm / high-MFE 行为。如果直接用它做 rejector，容易把未来还能走出 MFE 或 confirm 的边界样本一起杀掉。

## 09C Diagnostic Prior

09C 只作为诊断先验，不进入 10C supported decision，也不进入 10C training features。

| diagnostic_source | metric_id | value | note |
|:--|:--|--:|:--|
| `09C_manifest` | `manifest_exists` | 1.0 | 09C artifact present |
| `09C_report` | `report_exists` | 1.0 | 09C report present |
| `09C_manifest` | `decision_is_diagnostic_prior` | 1.0 | `09C_riskon_cost_rejector_diagnostic_only_or_no_candidate` |

## Findings And Insight

1. **10C 有 feature-source 价值，但没有 rejector 结论。** `full / keep_9000` 在 train 上同时给出 positive false-repair lift 和 positive exposure lift，证明 09B feature source 对 false-repair 方向有信息。但 supported rejector 的标准更高，需要 winner-safe，这一点当前失败。

2. **E1-missed winner 是最紧的约束。** 最佳候选只差 `0.66pp` 才达到 85% E1 retention floor，但这不是可以忽略的误差，因为 validation 上 E1 retention 掉到 57.81%。换句话说，train 上的“差一点”在 OOS 上会放大成明显 winner injury。

3. **false-repair label 仍然太接近活跃事件。** Rejected bucket 的 MFE 均值在 train / validation / robustness 分别是 16.53% / 15.08% / 17.36%，显著高于 accepted bucket 的 13.41% / 8.00% / 11.28%。这解释了为什么 capture lift 和 exposure lift 看起来不错，但 retention gate 过不了。

4. **去掉 label-mechanism-overlap feature 后并没有修复问题。** `no_label_mechanism_overlap` 的 feature_count 从 46 降到 33，但 utility 更低，E1 retention 仍然失败。这说明当前问题不是单一 overlap feature 泄漏，而是 label 本身和 winner-like market behavior 共享结构。

5. **10B-only cascade 是当前可解释基线。** 10B gate 在三段 split 中稳定 reject 约 6%，false-repair capture 约 7.05% 到 8.08%，winner retention 约 94.03% 到 96.27%。10C 要作为 Layer 2，必须在这个基础上给出 incremental capture，同时不破坏 retention。当前没有满足条件的 operating point。

6. **下一步不应直接放宽 retention gate。** 如果为了让 `full / keep_9000` 通过而把 E1 retention floor 从 85% 降低，validation 上的 57.81% 会暴露同样的问题。更合理的方向是把训练/选择目标进一步改成 winner-safe false repair，例如显式强调 `false_repair_non_winner`、winner injury penalty、或引入 confirm/MFE safety feature 和 thresholding 约束。
