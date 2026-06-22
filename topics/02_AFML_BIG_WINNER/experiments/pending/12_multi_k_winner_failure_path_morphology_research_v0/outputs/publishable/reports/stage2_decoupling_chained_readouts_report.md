# 12A7c Direction E: stage-2 解耦诊断与 chained readout 报告

## 结论

本轮 12A7c **不能进入 deployable stage-2 策略支持态**。最终状态为 `12A7c_blocked_input_or_stage1_anchor_failure`，直接原因不是上游 artifact 缺失，也不是 stage-1 anchor 重建失败，而是选中的 decoupled 与 chained 两条 readout 都没有通过 matched random replay 覆盖门：

- `gate_failure_reasons = decoupled_random_replay_failed;chained_random_replay_failed`
- `next_allowed_requirement = none`
- `recommended_internal_followup = gate_specific_failure_triage`

关键解释：数据里存在 continuation uplift，尤其在真 no-fast-fail survivor 的 decoupled 视角下较明显；但 Direction E 的部署判断要求同预算 random replay 可比。当前 random replay 对 split × board_bucket × calendar_month 的精确匹配覆盖不足，导致必须 fail-closed。这个结论应理解为“stage-2 信号尚不能被 random-matched 验证链条支持”，不是“stage-2 没有任何信号”。

## 需求字段映射

| contract field | 中文解释 |
|---|---|
| validation stress warning | validation split 中 decoupled 与 chained 均为 `random_replay_failed`；decoupled 仍有 +8.36pp delta vs random p50，但有效 seed 仅 29；chained random baseline 为 NA，valid seeds 为 0 |
| single-feature challenger result | 最强单特征 challenger 为 `realized_path_volatility_0_20d`；robustness chained 的 complex - single 为 +0.36pp，CI [-3.79pp, +4.41pp] |
| complex-vs-single-feature paired result | complex score 未稳定胜过单特征；decoupled robustness 为 -2.38pp，CI [-4.85pp, +0.18pp]，chained robustness 为 +0.36pp，CI [-3.79pp, +4.41pp] |

## 输入与 anchor 审计

所有必需输入 artifact 读取与 schema 审计通过：35 个 required input 均为 `read_status=pass` 且 `schema_status=pass`。stage-1 anchor 也重建通过：

| item | value |
|---|---:|
| stage-1 anchor rule | `simple_0066e3511eb63515` |
| anchor feature | `volatility_20d` |
| orientation | `asc` |
| X | 0.30 |
| history policy | `board_then_global_rolling_504_sessions` |
| local cache cross-check | `pass` |
| publishable count reconciliation | `pass` |

Anchor 选中计数：

| split | selected_n |
|---|---:|
| train | 2,023 |
| validation | 957 |
| robustness | 1,476 |
| all | 4,456 |

因此，本报告后续的 blocked 状态应归因于 stage-2 random replay gate，而不是输入链路或 anchor 复现链路。

## 分母结构

12A7c 只评估 C0 risk_on 且 stage-1 evaluable 的事件。两个分母口径不同：

- **decoupled**：真 no-fast-fail survivor 分母，仅诊断“真正存活者中是否存在 continuation 信号”。
- **chained**：固定 12A7b stage-1 anchor 后，再在 anchor 选中的 no-fast-fail survivor 中做 stage-2 选择；这是唯一接近部署语义的 readout。

| split | primary scope | ground-truth survivor | chained survivor | chained / ground-truth |
|---|---:|---:|---:|---:|
| train | 8,303 | 4,827 | 1,582 | 32.77% |
| validation | 2,151 | 1,420 | 769 | 54.15% |
| robustness | 4,659 | 3,234 | 1,265 | 39.12% |
| all | 15,113 | 9,481 | 3,616 | 38.14% |

Stage-1 anchor 明显压缩了 stage-2 可操作分母，尤其 train 与 robustness。这个压缩不是坏事，因为它对应 fast-fail 防守；但它会同步压缩 continuation 机会集，使 chained stage-2 的 random baseline 更难构造。

## 选中的 stage-2 候选

train-frozen 选择在 decoupled 与 chained 两条线上都选中 `complex_stage2_score`，X=0.30。可用候选共 6 个：

| candidate | family | orientation |
|---|---|---:|
| `complex_stage2_score` | complex score | desc |
| `realized_path_volatility_0_20d` | single feature | desc |
| `realized_max_high_return_0_20d` | single feature | desc |
| `realized_early_window_ret_0_10d` | single feature | desc |
| `realized_ma_5_20_spread_at_day20` | single feature | desc |
| `distance_to_120d_low` | single feature | desc |

train 上 `complex_stage2_score, X=0.30` 的 continuation rate 是最高的，因此被冻结为主候选；single-feature challenger 是 `realized_path_volatility_0_20d, X=0.30`。

## Decoupled readout: 真 survivor 中有 continuation 信号

decoupled 口径不代表可部署策略，因为它使用了事后可知的 no-fast-fail survivor 分母。但它回答一个很重要的问题：如果已经知道路径没有 fast-fail，是否还能在其中找到 continuation 右尾信号？

| split | denominator_n | base rate | selected_n | selected rate | delta vs base | random p50 | valid seeds | delta vs random p50 | CI 95% | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| train | 4,827 | 15.60% | 1,496 | 23.46% | +7.86pp | 17.85% | 29 | +5.61pp | [+3.48pp, +7.75pp] | `random_replay_failed` |
| validation | 1,420 | 8.66% | 287 | 15.33% | +6.67pp | 6.97% | 29 | +8.36pp | [+4.18pp, +12.54pp] | `random_replay_failed` |
| robustness | 3,234 | 13.45% | 840 | 19.29% | +5.83pp | 10.71% | 29 | +8.57pp | [+5.83pp, +11.31pp] | `random_replay_failed` |

信号层面的读法：

- robustness 中，selected continuation rate 为 19.29%，分母 base rate 为 13.45%，绝对 uplift 为 +5.83pp。
- 与 random p50 相比，robustness delta 为 +8.57pp，CI 下界 +5.83pp，方向上很强。
- 但 `valid_seed_n=29`，低于配置门槛 `min_random_seed_n=100`，所以 readout 必须标为 `random_replay_failed`。

Insight：decoupled 结果说明“真存活者内部确有 continuation ranking 信号”。这支持继续研究 stage-2，但它不能单独支持部署，因为真实 t0 决策时不知道哪些行会 no-fast-fail。

## Chained readout: 部署语义下信号变弱且 random baseline 缺失

chained 口径先应用 12A7b 的 stage-1 anchor，再在已通过 fast-fail 防守的 survivor 中做 stage-2。这更接近实际操作，但当前 random replay 完全无法给出有效 baseline。

| split | denominator_n | base rate | selected_n | selected rate | delta vs base | random p50 | valid seeds | budget drift vs X | rank not evaluable | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| train | 1,582 | 12.20% | 434 | 19.35% | +7.16pp | NA | 0 | +0.50pp | 7.02% | `random_replay_failed` |
| validation | 769 | 8.06% | 191 | 13.09% | +5.03pp | NA | 0 | +4.77pp | 1.56% | `random_replay_failed` |
| robustness | 1,265 | 9.33% | 279 | 12.90% | +3.58pp | NA | 0 | +7.89pp | 0.24% | `random_replay_failed` |

信号层面的读法：

- chained robustness 仍有正向 uplift：12.90% vs 9.33%，delta +3.58pp。
- 但 uplift 比 decoupled robustness 的 +5.83pp 明显收缩，说明 stage-1 fast-fail 防守确实吃掉了一部分 continuation 机会。
- random p50 和 CI 全为 NA，根因是 chained random replay 没有任何 seed 能完整满足所有 matched cell 的抽样要求。

Insight：chained 不是完全无信号，而是“有弱正向信号，但无法被当前 random-matched 设计验证”。在 requirement 的 fail-closed 规则下，这种状态不能宣称 deployable。

## Random replay 失败细节

配置要求 `min_random_seed_n=100`，即 100 个 random seed 都要在同预算、同 split × board_bucket × calendar_month cell 内完成精确 matched replay。

| denominator | audit rows | seeds total | valid seeds | insufficient cells | main failure location |
|---|---:|---:|---:|---:|---|
| decoupled ground-truth survivor | 11,900 | 100 | 29 | 107 | train 77, validation 29, robustness 1 |
| chained stage-1 survivor | 9,100 | 100 | 0 | 369 | train 282, validation 68, robustness 19 |

Decoupled 的失败不是大面积崩溃，而是少数 cell 的 random 可用行不足。最严重 shortfall 只有 3 行，例如 train/chinext/2019-07 请求 6 行但可用 3 行；train/main_board/2020-01 请求 25 行但可用 23 行。由于判定规则要求 seed 内所有 matched cell 都 pass，少数稀疏 cell 也会使该 seed 失效，最终只剩 29 个有效 seed。

Chained 更严重：stage-1 anchor 先抽走一部分 random survivor，再要求 stage-2 同预算匹配，导致 369 个 cell 不足，且 100 个 seed 全部至少有一个 cell 失败。典型失败包括 train/main_board/2020-01 请求 8 行但可用 4 行，以及 train/chinext/2020-05 请求 7 行但可用 3-4 行。

Insight：当前 blocked 的核心不是 bootstrap 不稳定，而是 random baseline construction 不可用。后续应优先做 gate-specific triage：检查 random pool 覆盖、cell 粒度、replacement replay 规则和 stage-1 chained random survivor 的可用性，再谈 calibration 或 policy replay。

## 复杂模型 vs 单特征 challenger

复杂模型没有稳定击败最强单特征 `realized_path_volatility_0_20d`。paired comparison 的 CI 均跨 0：

| denominator | split | complex rate | single-feature matched rate | delta complex - single | CI 95% |
|---|---:|---:|---:|---:|---:|
| decoupled | train | 23.46% | 22.33% | +1.14pp | [-0.76pp, +3.05pp] |
| decoupled | validation | 15.33% | 16.72% | -1.39pp | [-5.26pp, +2.48pp] |
| decoupled | robustness | 19.29% | 21.67% | -2.38pp | [-4.85pp, +0.18pp] |
| chained | train | 19.35% | 19.12% | +0.23pp | [-2.93pp, +3.20pp] |
| chained | validation | 13.09% | 15.18% | -2.09pp | [-6.33pp, +2.36pp] |
| chained | robustness | 12.90% | 12.54% | +0.36pp | [-3.79pp, +4.41pp] |

Insight：如果只看 continuation ranking，complex score 在 train 上被选中是合理的；但 out-of-sample 和 paired matched comparison 不支持“复杂模型显著优于单特征”。这意味着下一步不应优先加模型容量，而应优先解决 denominator/random replay 的可比性问题。

## Budget drift 与 rank 可评估性

选中的 `complex_stage2_score, X=0.30` 在 robustness 上没有出现 12A6c/12A7 早期那种大规模预算放水：

| denominator | split | selected budget total | selected budget rank-evaluable | abs drift vs X | rank not evaluable |
|---|---:|---:|---:|---:|---:|
| decoupled | train | 30.99% | 31.78% | 1.78pp | 2.49% |
| decoupled | validation | 20.21% | 20.30% | 9.70pp | 0.42% |
| decoupled | robustness | 25.97% | 26.06% | 3.94pp | 0.34% |
| chained | train | 27.43% | 29.50% | 0.50pp | 7.02% |
| chained | validation | 24.84% | 25.23% | 4.77pp | 1.56% |
| chained | robustness | 22.06% | 22.11% | 7.89pp | 0.24% |

Budget drift 仍需注意两点：

- decoupled validation 的 rank-evaluable budget drift 为 9.70pp，接近 10pp gate 上限。
- chained train 的 rank_not_evaluable_rate 为 7.02%，超过 5% 的诊断阈值；validation 与 robustness 已恢复到 1.56% 和 0.24%。

Insight：本轮不是预算漂移导致失败；random replay 覆盖才是主 blocker。但 validation drift 接近阈值，说明在更小 split 或更细 cell 下，rank cut 仍会受到历史不足和离散 cell size 影响。

## Stage-1 防守的 opportunity cost

Stage-1 anchor 的目标是降低 fast-fail 风险，但它对 continuation 机会有明确成本：

| split | ground-truth survivor rate | chained survivor rate | chained share of survivors | continuation delta | positive capture rate | status |
|---|---:|---:|---:|---:|---:|---|
| train | 15.60% | 12.20% | 32.77% | -3.40pp | 25.63% | `continuation_cost_but_stage2_recoverable` |
| validation | 8.66% | 8.06% | 54.15% | -0.60pp | 50.41% | `no_material_continuation_cost` |
| robustness | 13.45% | 9.33% | 39.12% | -4.12pp | 27.13% | `continuation_cost_but_stage2_recoverable` |
| all | 13.83% | 10.32% | 38.14% | -3.51pp | 28.45% | `continuation_cost_but_stage2_recoverable` |

Insight：12A7b 的 simple backbone 作为 fast-fail 防守是有代价的。robustness 中，stage-1 只保留了 39.12% 的真 survivor，并且 continuation rate 从 13.45% 降到 9.33%。Stage-2 selector 能把 chained survivor 内的 selected rate 拉到 12.90%，但仍没有恢复到 decoupled 真 survivor 的 19.29%。

## 稳定性切片

对选中的 chained `complex_stage2_score, X=0.30` 做切片审计：

| slice_type | pass | insufficient_n | comment |
|---|---:|---:|---|
| split | 3 | 0 | train/validation/robustness 三个 split 均方向为正 |
| board_bucket | 3 | 3 | robustness main_board pass；chinext selected_n=51，不足且方向为负 |
| calendar_year | 5 | 3 | robustness 2025 pass；2024 selected_n=95，不足 |
| primary_family_id | 2 | 19 | 大多数 family 粒度样本不足 |
| calendar_month | 0 | 61 | 月度切片基本不可用于稳定结论 |
| stage1_anchor_selected_flag | 3 | 0 | anchor flag 维度方向通过 |

Robustness 关键切片：

| slice | selected_n | selected rate | base rate | delta | status |
|---|---:|---:|---:|---:|---|
| main_board | 228 | 12.28% | 7.45% | +4.83pp | pass |
| chinext | 51 | 15.69% | 17.75% | -2.06pp | insufficient_n |
| year 2025 | 184 | 17.39% | 11.71% | +5.68pp | pass |
| year 2024 | 95 | 4.21% | 2.69% | +1.52pp | insufficient_n |

Insight：总体 split 方向是正的，但细分稳定性还不够。robustness 的主要支持来自 main_board 与 2025；chinext、family、month 维度样本不足，不能支持“广泛稳定”的 stage-2 部署结论。

## Findings

1. **Decoupled 证明“真 survivor 内部有 continuation signal”**：robustness 中 selected rate 19.29%，base 13.45%，random p50 10.71%，delta vs random p50 为 +8.57pp，CI 下界 +5.83pp。
2. **Chained 证明“stage-1 之后信号仍有但变弱”**：robustness selected rate 12.90%，base 9.33%，delta +3.58pp；但 random baseline 为 NA，valid seeds 为 0。
3. **当前 blocker 是 matched random replay coverage，不是模型没有排序能力**：decoupled 仅 29/100 seeds 有效，chained 0/100 seeds 有效，必须 fail-closed。
4. **复杂模型没有稳定胜过单特征**：robustness chained 的 complex - single 仅 +0.36pp，CI [-3.79pp, +4.41pp]；decoupled robustness 甚至为 -2.38pp，CI [-4.85pp, +0.18pp]。
5. **Stage-1 fast-fail 防守有 continuation opportunity cost**：robustness 中 chained survivor 只占真 survivor 的 39.12%，continuation rate 低 4.12pp。
6. **预算漂移不是本轮主因**：选中点 robustness 的 rank-evaluable budget drift 为 decoupled 3.94pp、chained 7.89pp，均未超过 10pp 上限；但 validation decoupled 9.70pp 接近阈值。
7. **稳定性还不足以支持部署**：split 维度方向通过，但 board/family/month 多数细切片 insufficient_n，尤其 chained random replay 在这些细 cell 下不可用。

## 建议

下一步不要直接进入 probability calibration 或 policy replay。优先做 `gate_specific_failure_triage`：

1. 审计 random sample pool 在 split × board_bucket × calendar_month 下的可用性，尤其是 chained random survivor 的 cell 短缺。
2. 评估 random replay cell 粒度是否过细，或是否需要预先保证每个 cell 的 minimum random support。
3. 单独复核 stage-1 chained random survivor 的构造：当前 stage-1 keep 后再 stage-2 matching 会把可用 random denominator 压得很薄。
4. 在 random replay 能给出有效 p50 与 CI 后，再决定是否进入 calibration/policy replay。
5. 模型容量不是优先方向；若继续 stage-2，`realized_path_volatility_0_20d` 应作为强 challenger 保留。

总之，Direction E 的实质发现是：**continuation 信号存在，但当前 stage-2 chained 部署证据链被 matched random baseline 覆盖卡住。应先修 baseline 可比性，再讨论是否部署或校准。**
