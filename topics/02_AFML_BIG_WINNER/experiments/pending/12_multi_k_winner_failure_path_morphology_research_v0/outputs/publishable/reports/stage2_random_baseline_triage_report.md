# 12A7d stage-2 random baseline support triage report

## 1. 结论

12A7d 的最终状态是 `12A7d_stage2_signal_diagnostic_only`。这不是一个可部署的 stage-2 continuation support 结论，而是一个基线构造诊断结论：冻结的 chained stage-2 候选在 robustness 上相对 random p50 有正点估计，但 strict exact 和 month-quarter 近严格 random null 都没有达到足够的随机支持，能够构造完整随机支持的 split-board fallback 和 pooled weighted null 又只能给诊断级解释。

| field | value |
|---|---:|
| final decision_state | `12A7d_stage2_signal_diagnostic_only` |
| selected chained candidate | `complex_stage2_score` |
| selected chained X | 0.3000 |
| stage-1 anchor tuple | `simple_0066e3511eb63515` / `volatility_20d` / `asc` |
| stage-1 anchor X | 0.3000 |
| strict replay construction status | `insufficient` |
| hierarchical month-quarter construction status | `insufficient` |
| hierarchical split-board construction status | `pass` |
| pooled weighted construction status | `pass` |
| with-replacement construction status | `insufficient` |
| strongest accepted null | `hierarchical_split_board_fallback_replay` |
| weakest accepted null that supports claim | `` |
| robustness candidate selected_n / positive_n | 279 / 36 |
| robustness candidate continuation_rate | 0.1290 |
| robustness random_p50 | 0.1039 |
| robustness delta_vs_random_p50 | 0.0251 |
| robustness delta CI | [-0.0126, 0.0646] |
| best strict-or-near random_p50 | 0.1039 |
| best strict-or-near CI | [-0.0126, 0.0646] |
| allowed interpretation | `diagnostic_only` |
| next allowed requirement | `requirement_12a7e_defense_participation_frontier.md` |
| recommended internal follow-up | `test_whether_stage1_X030_denominator_is_too_narrow` |

本需求没有重新选择 stage-2 candidate、feature、X 或模型族，也没有改变 stage-1 simple backbone anchor。所有数字只适用于当前 C0 risk_on 样本、当前固定 `-10% / +20%` 标签、以及 12A7c 冻结的 chained candidate。

## 2. Lineage 和冻结候选

输入和 lineage 没有阻塞项：`input_artifact_audit.csv` 的 25 个输入 artifact 全部 `read_status = pass` 且 `schema_status = pass`；`frozen_candidate_reconciliation.csv` 的 8 个 split x denominator 校验全部通过。12A7d 因此没有因为 PIT、label、split、candidate 重建或 upstream decision schema 失败而 block。

冻结候选来自 12A7c 的 `direction_e_decision.csv`：

| denominator | split | selected_n | positive_n | continuation_rate | selected_budget_rank_evaluable | reconciliation |
|---|---|---:|---:|---:|---:|---|
| `stage1_anchor_chained_survivor` | all | 904 | 145 | 0.1604 | 0.2590 | pass |
| `stage1_anchor_chained_survivor` | train | 434 | 84 | 0.1935 | 0.2950 | pass |
| `stage1_anchor_chained_survivor` | validation | 191 | 25 | 0.1309 | 0.2523 | pass |
| `stage1_anchor_chained_survivor` | robustness | 279 | 36 | 0.1290 | 0.2211 | pass |
| `ground_truth_no_fast_fail_survivor` | all | 2623 | 557 | 0.2124 | 0.2807 | pass |
| `ground_truth_no_fast_fail_survivor` | train | 1496 | 351 | 0.2346 | 0.3178 | pass |
| `ground_truth_no_fast_fail_survivor` | validation | 287 | 44 | 0.1533 | 0.2030 | pass |
| `ground_truth_no_fast_fail_survivor` | robustness | 840 | 162 | 0.1929 | 0.2606 | pass |

这里最重要的差异是 denominator 的含义。Decoupled ground-truth survivor 上的 continuation rate 明显更高，但它是事后知道 no-fast-fail survivor 的诊断读数，不能被解释成可部署策略。12A7d 的 decision 只看 `stage1_anchor_chained_survivor` robustness，即 stage-1 anchor 先筛过以后还能不能用 stage-2 score 在可部署路径上打过 random。

## 3. Robustness random baseline 结果

Robustness split 是唯一能设置 12A7d decision 的 split。五个预注册 random null 的结果如下：

| baseline_id | strength | construction | valid_seed_n | candidate_rate | random_p50 | delta | CI | interpretation |
|---|---:|---|---:|---:|---:|---:|---|---|
| `strict_exact_cell_replay` | 1 | `insufficient` | 81 | 0.1290 | 0.1039 | 0.0251 | [-0.0108, 0.0681] | original fail-closed benchmark |
| `hierarchical_month_quarter_replay` | 2 | `insufficient` | 92 | 0.1290 | 0.1039 | 0.0251 | [-0.0143, 0.0681] | sensitivity with baseline caveat |
| `hierarchical_split_board_fallback_replay` | 3 | `pass` | 100 | 0.1290 | 0.1039 | 0.0251 | [-0.0126, 0.0646] | diagnostic only |
| `pooled_cell_weighted_replay` | 4 | `pass` | 100 | 0.1290 | 0.1039 | 0.0251 | [0.0215, 0.0287] | diagnostic only |
| `with_replacement_replay` | 5 | `insufficient` | 91 | 0.1290 | 0.1004 | 0.0287 | [-0.0108, 0.0681] | diagnostic only |

读法如下：

- Strict exact replay 是最强 null，因为它完整保留 `split x board_bucket x calendar_month`。但 robustness 只有 81 个 valid seeds，低于 `min_random_seed_n = 100`，所以不能作为支持或否定候选的充分随机基线。
- Month-quarter fallback 把 valid seeds 从 81 提到 92，但仍低于 100；这说明问题不是单个稀疏月份完全不可救，而是 stage-1 X=0.30 后的 survivor denominator 太窄，近严格 calendar control 仍不够稳。
- Split-board fallback 能构造 100 个 valid seeds，但它放松了 calendar 维度，证据强度下降；即使点估计为正，CI low 仍为负，因此只能说明方向上有信号，不能支持 deployable claim。
- Pooled weighted replay 也能构造 100 个 valid seeds，而且 pooled CI 为正；但 pooled 允许部分 cell 缺 random support 时只在 supported cells 上加权，它天然是较弱 null，不能替代 strict/near-strict null。
- With-replacement replay 允许 sparse cell 内重复抽样，但 robustness 仍只有 91 个 valid seeds；这说明 replacement 并没有彻底解决 random 支持问题，反而提示某些 cell 是零支持或极低支持。

## 4. 跨 split 稳定性

跨 split 结果显示，stage-2 chained candidate 的正 delta 不是 robustness 单点偶然，但严格随机基线的可构造性在不同 split 上明显不一致。

| baseline_id | split | construction | valid_seed_n | candidate_rate | random_p50 | delta | CI low | supported_weight_share |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `strict_exact_cell_replay` | train | insufficient | 0 | 0.1935 | NA | NA | NA | 0.9816 |
| `strict_exact_cell_replay` | validation | insufficient | 33 | 0.1309 | 0.0733 | 0.0576 | 0.0105 | 0.9930 |
| `strict_exact_cell_replay` | robustness | insufficient | 81 | 0.1290 | 0.1039 | 0.0251 | -0.0108 | 0.9982 |
| `hierarchical_month_quarter_replay` | train | insufficient | 26 | 0.1935 | 0.1671 | 0.0265 | -0.0104 | 0.9974 |
| `hierarchical_month_quarter_replay` | validation | insufficient | 34 | 0.1309 | 0.0707 | 0.0602 | 0.0131 | 0.9931 |
| `hierarchical_month_quarter_replay` | robustness | insufficient | 92 | 0.1290 | 0.1039 | 0.0251 | -0.0143 | 0.9992 |
| `hierarchical_split_board_fallback_replay` | train | pass | 100 | 0.1935 | 0.1671 | 0.0265 | -0.0115 | 1.0000 |
| `hierarchical_split_board_fallback_replay` | validation | pass | 100 | 0.1309 | 0.0733 | 0.0576 | 0.0156 | 1.0000 |
| `hierarchical_split_board_fallback_replay` | robustness | pass | 100 | 0.1290 | 0.1039 | 0.0251 | -0.0126 | 1.0000 |
| `pooled_cell_weighted_replay` | train | pass | 100 | 0.1940 | 0.1699 | 0.0241 | 0.0195 | 0.9965 |
| `pooled_cell_weighted_replay` | validation | pass | 100 | 0.1309 | 0.0707 | 0.0602 | 0.0572 | 0.9987 |
| `pooled_cell_weighted_replay` | robustness | pass | 100 | 0.1290 | 0.1039 | 0.0251 | 0.0215 | 0.9996 |
| `with_replacement_replay` | train | insufficient | 16 | 0.1935 | 0.1682 | 0.0253 | -0.0138 | 0.9965 |
| `with_replacement_replay` | validation | insufficient | 86 | 0.1309 | 0.0707 | 0.0602 | 0.0157 | 0.9987 |
| `with_replacement_replay` | robustness | insufficient | 91 | 0.1290 | 0.1004 | 0.0287 | -0.0108 | 0.9996 |

一个关键细节是：validation 在多个 null 下 CI low 为正，但 validation 不能设置 final decision；robustness 下 strict/near-strict 的 CI low 为负，且可构造性不足。换句话说，当前证据不是“stage-2 score 完全无信号”，而是“在最需要做外推检验的 robustness split 上，强 null 支持不足，弱 null 支持只能给诊断级结论”。

## 5. Random support failure 来自哪里

Stage-1 random keep 并不是瓶颈。所有 baseline 在 stage-1 keep 的 train/validation/robustness 抽样都没有 shortfall。瓶颈出现在 stage-2 survivor denominator：stage-1 anchor 先把路径压窄，随后 no-fast-fail survivor 和 stage-2 label 条件又进一步减少 random 可匹配路径。

| baseline_id | replay_step | split | requested | sampled | shortfall | zero_support_cells | fallback_rows | duplicate_rows |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `strict_exact_cell_replay` | stage2_select | train | 43400 | 42600 | 800 | 146 | 0 | 0 |
| `strict_exact_cell_replay` | stage2_select | validation | 19100 | 18967 | 133 | 14 | 0 | 0 |
| `strict_exact_cell_replay` | stage2_select | robustness | 27900 | 27851 | 49 | 9 | 0 | 0 |
| `hierarchical_month_quarter_replay` | stage2_select | train | 43400 | 43288 | 112 | 89 | 287 | 0 |
| `hierarchical_month_quarter_replay` | stage2_select | validation | 19100 | 18969 | 131 | 14 | 68 | 0 |
| `hierarchical_month_quarter_replay` | stage2_select | robustness | 27900 | 27878 | 22 | 2 | 19 | 0 |
| `hierarchical_split_board_fallback_replay` | stage2_select | robustness | 27900 | 27900 | 0 | 0 | 19 | 0 |
| `pooled_cell_weighted_replay` | stage2_select | robustness | 27900 | 27876 | 24 | 9 | 0 | 0 |
| `with_replacement_replay` | stage2_select | robustness | 27900 | 27889 | 11 | 9 | 0 | 13 |

Strict exact replay 在 robustness 上最大的 shortfall cells：

| board_bucket | calendar_month | requested | sampled | shortfall | zero_seed_cells | pass_seed_cells |
|---|---:|---:|---:|---:|---:|---:|
| `main_board` | 2024-09 | 300 | 279 | 21 | 1 | 93 |
| `chinext` | 2024-05 | 500 | 480 | 20 | 0 | 96 |
| `chinext` | 2025-11 | 100 | 93 | 7 | 7 | 93 |
| `main_board` | 2025-04 | 100 | 99 | 1 | 1 | 99 |

这些 shortfall 的形态很有信息量。Robustness strict 的总 shortfall 只有 49 / 27900，supported weight share 高达 0.9982，但 valid_seed_n 仍只有 81。说明 strict baseline 的失败不是总体 random 样本数量太少，而是 fail-closed 规则非常严：一个 seed 只要在任意 requested cell 无法完整满足，就会从 valid seed 集合里剔除。窄 denominator 下少数 calendar-board cell 的稀疏性会被放大成 seed-level construction failure。

## 6. Findings

1. **12A7c 的失败更像 random null construction failure，而不是 stage-2 score 完全没有信号。** Robustness candidate rate 为 0.1290，strict/near-strict random p50 为 0.1039，点估计 delta 为 +0.0251。多个弱化 null 方向一致，但强 null 没有足够支持。

2. **stage-1 X=0.30 denominator 太窄，是当前链式路径的主要压力源。** Stage-1 random keep 本身没有 shortfall；shortfall 出现在 stage-2 survivor 抽样。这说明问题不是 stage-1 anchor 无法随机复刻，而是 anchor 之后再要求 no-fast-fail survivor 和 stage-2 label 时，某些 board x month cell 无法承载 strict same-budget replay。

3. **month-quarter fallback 只解决一部分问题。** Robustness valid_seed_n 从 81 提高到 92，shortfall 从 49 降到 22，zero-support cells 从 9 降到 2，但仍达不到 min_random_seed_n=100。近严格 calendar control 下仍不足，支持了“需要扩 stage-1 defense denominator”的判断。

4. **split-board fallback 的 pass 是诊断 pass，不是 deployable support。** 它把 valid_seed_n 提到 100，说明只要放松 calendar 维度，random support 可以构造；但 robustness CI low 仍为 -0.0126，且 fallback 已弱化了时间匹配，因此不能声称 chained continuation 被严格支持。

5. **pooled weighted replay 给出了最强的方向性诊断，但证据等级较弱。** Pooled robustness CI 为 [0.0215, 0.0287]，显示 supported cells 内 candidate 稳定高于 weighted random p50；但 pooled 允许 unsupported cells 不进入 delta 分母，只能说明“在可支持 cell 上 stage-2 score 有正分离”，不能替代 strict exact null。

6. **with-replacement 没有真正修复支持问题。** Robustness valid_seed_n 为 91，仍不足；虽然 p50 降到 0.1004、delta 提到 +0.0287，但 CI low 为 -0.0108，且 duplicate_rows=13。重复抽样没有把 sparse-cell 问题转化为可用强证据。

## 7. Insight

AFML 视角下，12A7d 的核心启示不是“换一个 stage-2 score”或“调一个 X 就能上线”，而是 denominator design 问题。12A7c 的 chained candidate 已经固定为 `complex_stage2_score, X=0.30`，并且 frozen reconstruction 完全对齐；12A7d 进一步证明，当前 stage-1 anchor 先过滤后，stage-2 可评估 survivor 的 calendar-board cell 太窄，导致严格 random null 无法稳定构造。

这意味着下一步不应急于做 policy replay。更合理的 12A7e 问题是：stage-1 defense participation 能否被拓宽，使 strict 或 near-strict random baseline 有足够支持，同时不牺牲 stage-1 fast-fail 防御的主要收益。只有当 denominator 变宽以后，stage-2 continuation score 的正 delta 才能从“diagnostic signal”升级为“deployable chained support”。

本报告的结论边界是：12A7d 支持继续研究 stage-2 continuation 信号，但不支持当前 chained operating rule 直接进入策略化使用。当前最稳妥的行动是进入 `requirement_12a7e_defense_participation_frontier.md`，优先审计 stage-1 X=0.30 是否过窄，以及哪些 defense-participation frontier 可以同时保留 fast-fail 防御和 random-baseline 可检验性。
