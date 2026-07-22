# 21F v5 Data-first 暂定诊断报告

> 生成阶段：`DATA_FIRST` 已完成，`REVERSE_VALIDATION` 未执行。
> 证据角色：`provisional_design_contaminated_diagnostic`。
> 本报告只总结当前已生成的数据，不构成正式模型选择、论文复现结论或可交易策略结论；禁止密封。

## 1. 执行摘要

本轮最重要的结果不是“已经找到最终模型”，而是观察到了一个清晰但存在内部张力的模式：

1. 对收益输入做 decision-date cross-sectional z-score 后，T1/T2/T3 的 inner RankIC 明显高于 raw-return T0；收益语义修复很可能是本轮效果提升的主要来源。
2. provisional fallback T1 在 2023 上取得稳定为正的 RankIC，且相对同一 backbone 的 Koopman-only K0，在上下半年都存在正增量；这说明 DRC 路径可能确实带来了额外排序信息，而不只是旧 Q0 基线失效造成的假象。
3. 但 T1 的跨 seed 排名形态与 Top30 成分很不稳定，且相邻决策日 Top30 turnover 高。它提高了 ensemble RankIC，却没有产生稳定的单模型选股形态。
4. 因此当前更合理的解释是：DRC 可能是一个对 ensemble 有价值、但尚不适合直接驱动集中持仓的增量 alpha。它是否能升级为正式 predictor，仍取决于 Q1→Q2 收敛和形态稳定性反向验证。

当前结论维持：`research_selection_allowed=false`、`seal_authorized=false`。

## 2. 数据与执行闭合

- E2 复用：30/30 inner checkpoints 已完成 byte-hash 校验，没有重新训练。
- E3 Q1 arm readout：30/30 checkpoint scores 已落盘。
- Provisional refit：T1 的 3/3 seeds 已完成，每个 seed 固定训练 44 epochs。
- 2023 fast design readout：2 个时间段 × 3 variants × 3 seeds，共 18/18 scores 已完成。
- 2023 样本：Early 107 个决策日，Late 103 个决策日；每日截面约 480 只股票。
- 本轮 predictor 使用 `Q1_SCORE_MEAN64`；Q2 256-draw reference 尚未计算。

## 3. Inner arm 选择结果

Q1 下的 provisional 排名为：

1. `T1_CSZ_COUPLED_LINEAR`
2. `T2_CSZ_STOPGRAD_LINEAR`
3. `T3_CSZ_TWO_STAGE_LINEAR`
4. `T0_RAW_COUPLED_LINEAR`
5. `T4_CSZ_STOPGRAD_POINTWISE_MLP`

但 `basic_eligible_arm_ids=[]`，即没有任何 arm 同时通过两个 inner folds 的全部基础门槛。T1 是 fallback，不是正式入选。

| Arm | I0 2021 RankIC | I1 2022 RankIC | 主要未通过项 | 诊断含义 |
|---|---:|---:|---|---|
| T0 Raw + Coupled + Linear | -0.00081 | 0.00570 | RankIC、rho、Top30 overlap、turnover | raw-return 语义基本没有形成稳定信号 |
| T1 CSZ + Coupled + Linear | 0.06340 | 0.06910 | I0 overlap 4.33<6；I1 overlap 4<6、turnover 0.817>0.80 | RankIC 最强且跨 fold 最均衡，但选股形态不稳 |
| T2 CSZ + Stopgrad + Linear | 0.05551 | 0.05086 | I1 rho 0.227<0.25、overlap 5.33<6 | 稳定性优于 T1 的部分指标，但跨 fold 仍未闭合 |
| T3 CSZ + Two-stage + Linear | 0.06464 | 0.05004 | I1 overlap 5.33<6 | I0 很强，I1 衰减，存在 regime sensitivity |
| T4 CSZ + Stopgrad + Pointwise MLP | -0.00544 | 0.00586 | RankIC、rho、overlap、turnover | 更复杂 decoder 没有带来增益，反而破坏信号 |

T1 被选中的直接原因是 lexicographic fallback 优先最大化 worst-fold RankIC：T1 的 worst-fold 为 0.06340，高于 T2 的 0.05086 和 T3 的 0.05004。这一规则偏好预测强度，而不是形态稳定性，必须在解释结果时保留这个前提。

## 4. 2023 RankIC 结果

| 时间段 | T1 selected DRC | Same-backbone K0 | Sealed 21C Q0 | DRC−K0 | DRC−Q0 |
|---|---:|---:|---:|---:|---:|
| Early 2023 | 0.04882 | 0.02723 | 0.01566 | +0.02159 | +0.03317 |
| Late 2023 | 0.04753 | 0.02323 | -0.00230 | +0.02430 | +0.04983 |

Late 2023 的正式 paired descriptive statistics 为：

| Contrast | Paired days | RankIC delta | 同方向 seeds | Holm p |
|---|---:|---:|---:|---:|
| T1 DRC − K0 | 103 | +0.02430 | 3/3 | 0.0032 |
| T1 DRC − Q0 | 103 | +0.04983 | 3/3 | 0.0000 |

三个 T1 seeds 的平均 daily RankIC 也全部为正：

| 时间段 | Seed 20260713 | Seed 20260714 | Seed 20260715 | Ensemble |
|---|---:|---:|---:|---:|
| Early 2023 | 0.02866 | 0.03129 | 0.04000 | 0.04882 |
| Late 2023 | 0.03484 | 0.03195 | 0.03531 | 0.04753 |

这说明 2023 的正结果并非由单个 seed 独占。与此同时，ensemble 明显高于每个单 seed，说明不同 seeds 提供了互补排序信息；这既是 ensemble 的优势，也是“单模型形态不稳定”的另一面。

## 5. 形态稳定性与 turnover

下面的 rho 和 overlap 是三个 seed-pairs 的均值；overlap 的分母为 Top30。

| 时间段 | Variant | Cross-seed Spearman | Cross-seed Top30 overlap | Ensemble adjacent turnover |
|---|---|---:|---:|---:|
| Early 2023 | T1 DRC | 0.227 | 3/30 | 0.860 |
| Early 2023 | K0 | 0.536 | 12/30 | 0.600 |
| Early 2023 | Q0 | 0.002 | 2/30 | 0.939 |
| Late 2023 | T1 DRC | 0.201 | 3/30 | 0.873 |
| Late 2023 | K0 | 0.537 | 11/30 | 0.593 |
| Late 2023 | Q0 | approximately 0.000 | 2/30 | 0.938 |

T1 相对 K0 的问题非常明确：

- RankIC 提高约 0.022–0.024；
- 但 cross-seed Spearman 从约 0.54 降至约 0.20–0.23；
- Top30 overlap 从 11–12 只降至 3；
- adjacent turnover 从约 0.59–0.60 升至约 0.86–0.87。

因此 DRC 的增量并不是一个“保持 K0 排名骨架的小修正”，而是大幅改写了截面排序。这个改写在 ensemble 层面有预测价值，但在 seed 层面缺少身份稳定性。

这里的 turnover 是相邻观测决策日的 Top30 诊断指标，不等于已经实施每日再平衡，也不能直接换算为真实交易成本。本轮没有生成 portfolio output，实际非每日再平衡规则仍未验证。

## 6. 时间稳定性（LOMO）

LOMO 表示每次剔除一个月后，在其余月份上重新计算 ensemble mean daily RankIC。

| 时间段 | Variant | Positive LOMO | LOMO RankIC 范围 |
|---|---|---:|---:|
| Early 2023 | T1 DRC | 6/6 | 0.04371–0.05252 |
| Early 2023 | K0 | 6/6 | 0.02237–0.03330 |
| Early 2023 | Q0 | 6/6 | 0.01294–0.02036 |
| Late 2023 | T1 DRC | 6/6 | 0.03776–0.05436 |
| Late 2023 | K0 | 6/6 | 0.01431–0.03451 |
| Late 2023 | Q0 | 1/6 | -0.00605–0.00114 |

T1 与 K0 的正 RankIC 都不是由某一个月份单独驱动；T1 在 12 个 leave-one-month-out 场景中全部保持为正。Q0 则在 2023 下半年明显失效。这支持“新语义修复有效”的方向性判断，但不能区分其中有多少来自 CSZ、coupled gradient、DRC predictor 或三者交互。

## 7. Materiality 字段的正确解释

`provisional_design_contrasts.csv` 中两行 `materiality_pass=False` 不能直接解释为两个 contrast 都未达到数值门槛。当前 data-first helper 在生成 paired statistics 时将该字段初始化为 `False`，而正式 fresh-2023 materiality 计算被后置，没有在本轮执行。

若只按已预注册规则进行诊断性重算，而不写回正式 gate：

- C10（DRC−K0）满足 RankIC delta≥0.005、3/3 seeds 同方向、paired days≥100、Holm p≤0.10；但 morphology non-worse 不成立，因为 T1 的 rho、Top30 overlap 和 turnover 三项都劣于 K0。因此 C10 的完整 materiality rule 不支持“DRC 在不牺牲形态的条件下提供增量价值”。
- C11（DRC−Q0）满足 selected RankIC≥0.030 且 delta≥0.020 的数值条件。它支持“相对旧 Q0 的 ranking repair”，但仍是 Q1/data-first 层面的暂定证据。

## 8. Findings（发现）

### F1. CSZ 比 raw-return 更像本轮的一级修复来源

T1/T2/T3 在两个 inner folds 均显著为正，而保持 raw-return 的 T0 接近零。这个对照比 T1/T2/T3 之间的差异更大。当前证据优先支持“收益尺度/截面语义错误是旧实现的重要问题”，而不是直接支持某一种 DRC gradient graph 已被唯一识别。

### F2. Shared linear decoder 是必要的稳定基线

仅把 T2 的 shared linear decoder 改为 pointwise MLP 后，T4 的 RankIC 降至接近零，rho、overlap 和 turnover 也全面恶化。更复杂 decoder 没有吸收误差，反而可能破坏 Koopman latent 与预测 readout 的共同坐标结构。

### F3. Coupled gradient 提高了 worst-fold RankIC，但没有解决 morphology

T1 的两个 fold RankIC 最均衡，因此赢得 fallback；T2/T3 在至少一个 fold 的稳定性指标更好。当前更像“coupled graph 换取预测强度、stopgrad/two-stage 换取部分形态稳定性”，而不是 T1 对其他实现的全面支配。

### F4. DRC 增量具有跨半年、跨 seed、跨月份一致性

DRC−K0 在上下半年都约为 +0.02，Late 2023 三个 seeds 同方向，T1 的 12/12 LOMO 均为正。这比只与 Q0 比较更有信息量，因为 K0 使用同一 refit backbone，排除了部分“只是换了训练模型”的解释。

### F5. 增量 alpha 与可交易身份稳定性发生分裂

T1 的 ensemble RankIC 很强，但任意两个 seeds 的 Top30 只重合 3 只，且 turnover 高于 0.86。也就是说，“平均意义上的排序预测有效”与“稳定持有同一组股票”不是同一个结论。

## 9. Insights（研究洞察）

### I1. DRC 当前更适合作为 ensemble alpha，而不是单独的 Top30 selector

低 seed overlap 与高 ensemble lift 同时出现，说明不同 seeds 可能捕捉到方向一致、但股票身份不同的弱信号。短期内更合理的研究位置是：ensemble score、meta-label 或 participation filter；在 morphology 修复前，不宜直接把单 seed DRC 当成集中持仓生成器。

### I2. 下一步不应只问“Q2 后 RankIC 是否还为正”

真正需要反向验证的是三个层次：

1. Q1 与 Q2 的 daily score Spearman、Top30 overlap 和 RankIC delta 是否收敛；
2. T1 与 T2 的 provisional 排名是否翻转；
3. Q2 是否改善 T1 的跨 seed morphology，还是仅重复 Q1 的高 RankIC/高 turnover 模式。

如果 Q2 只维持 RankIC、却不能改善 morphology，那么问题更可能在训练得到的 seed-specific latent/DRC correction，而不是 Monte Carlo draw 数不足。

### I3. Predictor 与 DRC 不能再用单一 RankIC 一起验收

目前 T1 的强 RankIC 会掩盖形态失败。后续应继续把“预测强度”和“形态稳定性”作为两个独立轴：前者回答有没有 alpha，后者回答该 alpha 能否形成稳定、可执行的截面身份。

### I4. 旧 Q0 的 2023 下半年失效不能单独证明新实现正确

Q0 Late RankIC 为负、LOMO 仅 1/6 为正，说明旧 readout 不稳定；但新 DRC 同时显著优于 K0，才构成更有价值的增量证据。最终仍需 Q2 reference 排除 Q1 proxy 偏差。

## 10. 当前决策与边界

- T1 只能称为 `provisional fallback arm`，不能称为 research-selected arm。
- 目前可以记录“CSZ/shared-linear 方向得到支持”和“DRC 存在暂定增量 RankIC”。
- 目前不能声称 Predictor/DRC 实现已与论文一致，也不能声称已经得到可交易策略。
- `targeted_reverse_validation_status=not_run`。
- `full_reverse_validation_status=not_run`。
- `next_requirement_execution_authorized=false`。
- `seal_authorized=false`。

在用户明确授权前，不启动 validation，不更新代码，不密封当前 `.building` bundle。
