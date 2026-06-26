# Episode 16 研究计划：从 winner label diagnostic 转向序贯 / 续航范式

## 0. 定位

Episode 16 是 Episode 15（path-defined winner label diagnostic）之后的范式转换。它不再问 "winner 是不是某种形态"，而是问 "如果不预测终局、只在持有过程中一段一段判断是否继续参与，采样地基与 label 设计应该怎么做"。

Episode 16 的第一步**不是**直接做序贯 entry，而是先做采样几何 preflight，因为 Episode 15 已经证明 anchor 不是独立样本单元。

## 1. 从 Episode 15 继承的判断

15A→15C2 的累积结论（来自各自报告）：

```text
15A: fixed-120d label 对慢速 path-defined winner 存在 material right-censoring（真实）。
15B: 整段 winner_episode_cluster 硬分类 path shape -> 统计单元太粗（disagreement 0.7320）。
15C: cluster 按 entry-phase 切分 -> 只有 outcome-relative（事后位置）通过 real-over-random；
     PIT-observable phase 三个 split 全部没过；coverage 不足。
15C2: soft membership 放弃硬分类 -> winner 形态是连续谱，且 cluster-blocked baseline 否定 sharpness：
      形态不独立于 episode cluster 的重复采样结构。
```

三个收敛结论，构成 Episode 16 的全部动机：

```text
1. winner 形态不是固有离散类别，而是 "entry position within realized episode" 的连续函数。
2. entry position 在 t0 不可知，因此 "t0 给整段路径贴形态标签" 是错误的提法。
   -> 两条路（离散形态 taxonomy、t0 可预测形态）都已被 Episode 15 关闭。
3. anchor 数严重高估有效独立样本量（15C2 episode_cluster_blocked_shuffle 否定 sharpness）。
   -> 任何序贯实验若仍用 anchor 当样本单元，会重蹈高估统计功效的覆辙。
```

## 2. Episode 16 分阶段计划

### Phase 16A: Sequential Sampling Geometry Preflight（本轮 requirement）

```text
目标：在写任何序贯 label / entry 之前，先钉死采样几何真相——
      anchor 数 vs episode cluster 数 vs 时间去重 step 数的真实比例、
      短窗 horizon 网格、step 间时间重叠、effective sample size、跨 episode 并发折减。
裁决：序贯范式可用的采样单元与 horizon 候选是什么，anchor 高估了多少倍有效样本，
      effective sample 是否足够、是否跨 split 稳定。
授权：仅可能授权 16B 设计诊断；不授权任何 sequential label / entry / 收益 / 模型 / separability。
纪律：16A 绝不计算 forward return / 收益；纯采样几何诊断。
```

### Phase 16B: Sequential Continuation Label Design Diagnostic（条件开启）

```text
前提：16A decision = 16A_sampling_geometry_ready_for_sequential_label_design。
目标：基于 16A 钉死的采样单元与 horizon，设计短窗 continuation / survival label
      （"下一小段是否值得继续参与"），并做 label 的 base rate / 去重后样本量 /
      与已知失败形态重叠的诊断。仍是 label-form diagnostic，不做 entry / 收益。
裁决：短窗 continuation label 是否有非平凡 base rate、去重后样本是否足够、
      是否不是 compression / drawdown-reversal 已失败形态换名。
授权：仅可能授权 16C；不授权 entry / 收益 / 模型。
```

### Phase 16C: Sequential Continuation Separability Diagnostic（条件开启）

```text
前提：16B 通过。
目标：检验 "持有中某一步的 t0-observable 状态" 是否对 "下一小段 continuation label" 有
      train-only 可分性。这是第一次允许引入 t0 可观测特征，但仍是 separability 诊断，不是 entry。
注意：必须复用 16A 的 effective-sample 去重，不得用 step 数当独立样本高估功效。
```

### Phase 16D+（远期，仅在 16C 通过后定义）

```text
若持有中续航判断 t0 可分，才进入真正的序贯 entry / exit / holding：
t0 不预测终局，只判断 "下一小段是否值得参与"，用短 horizon survival label 链式叠加，
让市场用后续 path 持续淘汰输家，cost 被长持有摊薄。
此阶段必须重新冻结 entry / exit / cost / 序贯决策结构，不在本 plan 展开。
```

## 3. 不可违反的纪律（从 12-15 失败中提炼）

```text
1. censored row 绝不当 negative。
2. 三档阈值 {0.50, 1.00, 1.50} 预注册冻结，不得用 validation / robustness 事后增减。
3. anchor 不是独立样本单元（15C2 已证实）；序贯线一律用 effective-sample 去重，不得用 anchor / step 数高估功效。
4. winner 形态是 entry-position 的连续函数，不是固有离散类别；不复活离散形态 taxonomy 或 t0 形态预测。
5. 16A 纯采样几何诊断，绝不计算 forward return / 收益 / cost。
6. cross_split / split-boundary touching cluster 只能 readout，不进入 primary。
7. 三档阈值分开报告，不得把 up50 的几何 / label / 可分性外推到 up100 / up150。
8. 每个 phase 只授权下一个明确命名的 phase，绝不一步跳到 entry / 部署。
9. 任何引入 t0 可观测特征的步骤（最早 16C）必须复用上游 effective-sample 去重，并独立做与已知失败形态的重叠诊断。
```

## 4. 与 Episode 15 的边界

```text
Episode 16 不复活：15B 硬分类 path type、15C PIT entry-phase t0 feature、15C2 soft taxonomy。
Episode 16 只新增一件事：把研究单位从 "t0 给整段路径贴 label" 换成
"持有过程中一段一段判断是否继续参与"，并先证明这条线的采样地基是否成立。
Episode 15 的 winner episode cluster lineage、split boundary、path-defined label 被继承为输入。
```
