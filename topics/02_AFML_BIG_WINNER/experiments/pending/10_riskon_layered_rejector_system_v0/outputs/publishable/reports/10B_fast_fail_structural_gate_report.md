# 10B Fast-Fail Structural Gate Report

## 结论

本次 10B 在 10A 冻结后的 default post-dedup population 上得到：

```text
decision = 10B_fast_fail_structural_gate_source_caveated_supported
selected_population_id = 10A__same_instrument_cooldown_10d
selected_denominator_id = post_dedup_risk_on_r_core
selected_capacity_id = keep_9400
selected_threshold_id = keep_9400
selected_status = selected_by_train_constrained_utility
supported_pass = true
source_caveated = true
```

含义是：在 10A 的 `source_caveated=true` 仍未解除前，10B 只能给出 source-caveated supported 结论，不能写成 non-caveated supported，更不能描述为 production-ready。就当前样本而言，`keep_9400` 是 train-only constrained utility 下最合适的 fast-fail gate：它在 6% reject capacity 下抓到 26.50% 的 train fast-fail positive，同时把 train winner wrong-kill 压在 6% 上限以内。

关键判断：10B 的 fast-fail-only score 有可执行增量价值，但 winner retention 是硬约束且已经接近边界。这个 gate 可以作为 Layer 1 structural safety gate 的研究支持版本继续向 10C 传递，但不应该被解释成 cost optimizer，也不应该用 validation 的低功效行来增强正向结论。

## 输入与训练口径

所有 required input artifact 均通过 input audit；当前 manifest 中 `input_failures=[]`。模型使用 `sklearn.linear_model.LogisticRegression`，训练目标为 `selected_fast_fail_10_label`，只在 train split 拟合，sample weight 使用 `final_sample_weight`。

| item | full model | no-overlap ablation |
|:--|--:|--:|
| train rows | 8,318 | 8,318 |
| train fast-fail positives | 702 | 702 |
| input features | 48 | 27 |
| used features after preprocessing | 46 | 25 |
| dropped constant/IQR features | 2 | 2 |
| model status | pass | pass |

10A default post-dedup population 是本次 10B 的唯一 supported population，不包含 suppressed 或 non-executable rows。

| split | admitted samples | fast-fail positives | winners | fast-fail winners |
|:--|--:|--:|--:|--:|
| train | 8,318 | 702 | 1,491 | 70 |
| validation | 2,514 | 236 | 161 | 5 |
| robustness | 4,970 | 342 | 995 | 39 |

## 阈值选择

阈值选择只使用 train。`keep_9000` 是 sensitivity，不参与 supported operating point 选择；`keep_9600` / `keep_9700` 在 10A power gate 中不是 supported row；实际可选集合是 `keep_9250`、`keep_9300`、`keep_9400`、`keep_9500`。

| capacity | reject % | reject_n | captured fast-fail | candidate precision | capture rate | winner retention | wrong-kill | train utility | supported row |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| keep_9000 | 10.0% | 832 | 257 | 30.89% | 36.61% | 90.07% | 9.93% | -0.0280 | sensitivity |
| keep_9250 | 7.5% | 624 | 210 | 33.65% | 29.91% | 92.56% | 7.44% | 0.1540 | yes |
| keep_9300 | 7.0% | 583 | 200 | 34.31% | 28.49% | 93.09% | 6.91% | 0.2041 | yes |
| keep_9400 | 6.0% | 500 | 186 | 37.20% | 26.50% | 94.03% | 5.97% | 0.2813 | yes |
| keep_9500 | 5.0% | 416 | 161 | 38.70% | 22.93% | 95.24% | 4.76% | 0.2514 | yes |
| keep_9600 | 4.0% | 333 | 135 | 40.54% | 19.23% | 95.91% | 4.09% | 0.2151 | no |
| keep_9700 | 3.0% | 250 | 120 | 48.00% | 17.09% | 96.65% | 3.35% | 0.2108 | no |

`keep_9400` 胜出的原因不是 precision 最高，而是 utility 在 capture 与 winner injury 之间取得了最好的平衡。`keep_9250` 和 `keep_9300` 多抓 fast-fail，但 wrong-kill 高于 6% 上限；`keep_9500` 更保守，winner retention 更高，但 fast-fail benefit 下降，utility 低于 `keep_9400`。

## Selected Capacity Readout

`keep_9400` 在三个 split 上的读数如下。validation / robustness 只用于 severe reversal block，不作为正向支持证据。

| split | sample_n | reject_n | fast-fail positives | candidate caught | rule caught | random caught | candidate precision | capture rate | lift vs rule | lift vs random | winner killed | winner retention | accepted MAE10 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 8,318 | 500 | 702 | 186 | 58 | 47 | 37.20% | 26.50% | +18.23pp | +19.80pp | 89 / 1,491 | 94.03% | 0.073978 |
| validation | 2,514 | 151 | 236 | 62 | 24 | 7 | 41.06% | 26.27% | +16.10pp | +23.31pp | 6 / 161 | 96.27% | 0.061343 |
| robustness | 4,970 | 299 | 342 | 68 | 50 | 15 | 22.74% | 19.88% | +5.26pp | +15.50pp | 42 / 995 | 95.78% | 0.065409 |

train 上 fast-fail prevalence 为 8.44%，candidate rejected bucket 的 fast-fail precision 为 37.20%，约为总体 prevalence 的 4.41 倍。相同 capacity 下 rule baseline precision 为 11.60%，random baseline precision 为 9.40%。这说明 10B score 的排序能力并不只是来自 density reduction 或随机抽样，而是在 post-dedup admitted population 内进一步集中 fast-fail risk。

winner retention 是本次结论最紧的约束。train wrong-kill 为 5.969%，只略低于 6% cap；这也是为什么 `keep_9400` 能 pass，而更高 reject capacity 的 `keep_9250` / `keep_9300` 虽然捕获更多 fast-fail，却不能成为 supported operating point。

## Utility 与 OOS 阻断

`keep_9400` 的 train utility 组成：

```text
capacity_matched_capture_lift_over_rule_baseline = 0.182336
capacity_matched_capture_lift_over_random = 0.198006
fast_fail_benefit = 0.182336 + 0.5 * 0.198006 = 0.281339
winner_injury_excess = 0
mae_worse_excess = 0
density_excess = 0
train_constrained_utility = 0.281339
oos_threshold_instability = 0
supported_constrained_utility = 0.281339
```

validation 与 robustness 没有触发 severe reversal：两个 OOS split 的 lift vs rule 和 lift vs random 都为正。因此 OOS 只做到了“不阻断”，不能被写成“稳定支持”。尤其 robustness 的 lift vs rule 只有 +5.26pp，明显低于 train 的 +18.23pp，提示该 fast-fail signal 有 OOS 衰减。

## Power Gate 解释

10A power gate 的 supported row 分布：

| split | supported rows | total rows | 解释 |
|:--|--:|--:|:--|
| train | 5 | 7 | 可用于 train-only supported threshold selection |
| validation | 0 | 7 | fast-fail winner 样本太少，只能做 severe reversal block |
| robustness | 4 | 7 | 可读出 robustness，但 selected `keep_9400` 本身不是 robustness supported row |

selected `keep_9400` 的 train power row 为 pass；validation row 被 `winner_injury_power_status`、`fast_fail_ml_supported_gate_allowed`、`post_dedup_fast_fail_winner_n`、`rule_baseline_rejected_fast_fail_winner_n` 阻断；robustness row 被 `winner_injury_power_status` 与 `fast_fail_ml_supported_gate_allowed` 阻断。按 requirement，validation / robustness 的低功效行不能支持正向结论，但可以阻断 severe reversal。本次没有 severe reversal，所以 train supported pass 保留。

## MAE Side Constraint

accepted MAE10 约束在三个 split 均通过，candidate accepted rows 的 adverse excursion 不高于 rule baseline 与 random baseline。

| split | candidate accepted MAE10 | rule accepted MAE10 | random accepted MAE10 | status |
|:--|--:|--:|--:|:--|
| train | 0.073978 | 0.075526 | 0.074968 | pass |
| validation | 0.061343 | 0.061726 | 0.061994 | pass |
| robustness | 0.065409 | 0.065909 | 0.065564 | pass |

这点很关键：10B 并不是只在 top bucket 里抓更多 fast-fail，同时把剩余 accepted population 的 adverse excursion 变坏；当前读数显示 accepted side 没有比两个 baseline 更差。

## Ablation Insight

no-overlap ablation 移除了 21 个 FS2 / FS3 / mechanism-overlap feature，保留 27 个 feature。该 ablation 没有 collapse，但 uplift 明显收缩。

| split | model | dropped features | retained features | capture rate | lift vs rule | lift vs random | winner retention | MAE improves |
|:--|:--|--:|--:|--:|--:|--:|--:|:--|
| train | full | 0 | 48 | 26.50% | +18.23pp | +19.80pp | 94.03% | true |
| train | no-overlap | 21 | 27 | 18.95% | +10.68pp | +12.25pp | 94.03% | true |
| validation | full | 0 | 48 | 26.27% | +16.10pp | +23.31pp | 96.27% | true |
| validation | no-overlap | 21 | 27 | 21.19% | +11.02pp | +18.22pp | 95.65% | false |
| robustness | full | 0 | 48 | 19.88% | +5.26pp | +15.50pp | 95.78% | true |
| robustness | no-overlap | 21 | 27 | 17.84% | +3.22pp | +13.45pp | 94.57% | false |

解释：10B 的增量不是完全由 FS2/FS3/机制重叠特征驱动，因为 train no-overlap 仍然保留 +10.68pp vs rule 和 +12.25pp vs random；但这些特征贡献很大，移除后 train lift vs rule 从 +18.23pp 降到 +10.68pp，约保留 58.6%。因此结论应写成“有结构性增量，但部分依赖 path/vol/range/overlap family”，而不是“纯粹无机制依赖”。

## 09C Pre-Dedup Replay Diagnostic

09C hybrid cost score 只作为 pre-dedup diagnostic，不参与 10B score 或 threshold selection。对比显示，09C 需要拒绝更多样本才能达到类似或更低的 fast-fail capture，说明它不是合适的 fast-fail structural gate。

| split | 09C rejected_n | 09C fast-fail caught | 09C capture | 09C precision | 10B rejected_n | 10B fast-fail caught | 10B precision | overlap with 10B rejected |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 2,392 | 203 | 28.92% | 8.49% | 500 | 186 | 37.20% | 194 |
| validation | 316 | 31 | 13.14% | 9.81% | 151 | 62 | 41.06% | 31 |
| robustness | 1,155 | 68 | 19.88% | 5.89% | 299 | 68 | 22.74% | 105 |

最明显的是 robustness：09C 拒绝 1,155 行抓到 68 个 fast-fail，而 10B 在 `keep_9400` 只拒绝 299 行也抓到 68 个 fast-fail。train 上 09C 捕获数略高，但拒绝量是 10B 的 4.78 倍，precision 只有 8.49%。这支持 10B requirement 的方法论边界：fast-fail gate 应该训练 fast-fail-only target，并按 capacity / winner / density 约束选阈值；不能把 09C 的 hybrid cost score 当作 supported fast-fail gate。

## Findings

1. `keep_9400` 是当前最合理 operating point：它刚好满足 winner retention floor，同时相对 rule baseline 和 random baseline 保持清晰 capture lift。
2. winner injury 是主要风险源，不是 fast-fail capture。train wrong-kill 5.97% 距离 6% cap 很近，后续任何 upstream 10A source caveat 修复或样本重跑都可能改变 pass/fail。
3. OOS 读数没有 severe reversal，但 robustness lift 明显低于 train。当前可以说“未被 OOS 阻断”，不能说“跨样本稳定充分验证”。
4. no-overlap ablation 说明信号不是纯机制重叠，但 overlap/path/vol/range family 对 uplift 贡献显著；这是解释层面的 caveat。
5. 09C hybrid score 的 pre-dedup replay 进一步证明：AUC 或 hybrid cost ranking 不能替代 constrained fast-fail utility。10B 的价值来自在较低 reject capacity 下集中 fast-fail positive，并同时控制 winner injury。

## Operational Read

当前推荐使用方式是：把 `10B_fast_fail_structural_gate_source_caveated_supported` 作为 Layer 1 fast-fail structural safety gate 的研究支持结果，向 10C 继续传递；在 10A source caveat 解除前，不应发布为 non-caveated supported，也不应宣称 production readiness。下一步最值得跟踪的是 `keep_9400` 附近的 winner injury margin，以及 10A source-caveat 修复后 train / robustness lift 是否仍保持正值。
