# 15 Path-Defined Winner Episode Label 研究计划

## 0. 定位

Episode 15 从 2026-06-25 的 14A / 14C 失败复盘出发。Episodes 01-14 在 winner-entry 上累计失败 10 次以上，confirmatory / deployable pass count = 0。核心 blocker 反复是同一个：

```text
ranking / recall / probability readout repeatedly exists,
but it does not transport into after-cost full-denominator entry utility,
and positive signal repeatedly collapses back into compression / drawdown-reversal morphology.
```

Episode 15 不再在同一地基上换 token / family / cohort / model / entry-timing / overlay（这六类已被 12-14 全部证伪）。它转而第一次正面质疑此前从未被检验的**最底层地基：winner label 定义本身**。

## 1. 思路链（为什么是 label）

三个递进的洞察构成 Episode 15 的动机：

```text
洞察 1（人工）：在 t0 去预测长期涨幅是不现实的。
  -> 所有 01-14 实验都是 "t0 单点静态预测 [t0, t0+H] 右尾结局"。
     大赢家的形成是多阶段、需持续确认的过程，t0 时点赢家/输家几乎不可分。
     这解释了 separability / utility transport 反复失败。

洞察 2（人工）：用 120d / 50% 这类 fixed-horizon label 时，
  有一些标的因为走完涨幅所需时间超过 120 天，反而没被算进 winner episode。
  -> fixed-horizon label 对 "慢牛 / 长趋势" 型大赢家存在 right-censoring，
     系统性偏向短期爆发，恰好把研究推回 compression / reversal 形态。

洞察 3（推论）：在用新 label 找信号之前，必须先把 "winner 集合定义对"，
  并量化 fixed-horizon 到底漏了多少、漏的是什么、censoring 是否被正确隔离。
  -> 这就是 15A：一个纯 label 诊断，不找信号、不授权交易。
```

## 2. Episode 15 分阶段计划

### Phase 15A: Label Censoring Diagnostic（本轮 requirement）

```text
目标：用 path-defined、无 horizon 上限、右删失隔离的 winner episode label
      （首达阈值 {50%, 100%, 150%}），相对 fixed-horizon baseline，
      量化漏标规模、time-to-threshold 分布、slow-winner 形态独立性。
裁决：是否存在实质 censoring，且 slow winner 是否呈现区别于已失败形态的新表面。
授权：仅可能授权 15B；不授权任何 entry / 模型 / 仓位 / label 部署。
```

### Phase 15B: Winner Path Shape Taxonomy Diagnostic（本轮新增）

```text
前提：15A 已证明 fixed-horizon label 存在 material right-censoring，
      但 slow winner 未通过已知失败形态独立性读数。
目标：在任何 separability / signal search 之前，先把 path-defined winner
      按 realized path shape 做 episode 去重后的 taxonomy diagnostic，
      区分 smooth trend、stair-step、jump repricing、choppy reversal、
      slow grind、late rescue 等形态，并检验 entropy 是否提供独立信息。
裁决：是否存在稳定、可解释、跨 split 可读的 winner path type。
授权：仅可能授权 15C；不授权任何 entry / 模型 / 仓位 / label 部署。
```

### Phase 15C: Winner Entry Phase and Mixture Taxonomy Diagnostic（本轮新增，取代原 separability 15C）

```text
前提：15B decision = 15B_no_stable_path_shape_taxonomy，且最强失败信号是
      winner_episode_cluster 单元太粗（representative_disagreement = 0.7320，
      76.8% cluster 含 2 个以上 path type）。
判断：15B 失败不是 quantile 调不准，而是统计单元粒度不足。
      原计划直接进入 separability 的 15C 因此被取代。
目标：把 winner 拆成 outcome + threshold + entry-phase + path-quality 四层（仍是 label-form 诊断）。
      不再用 cluster-medoid 单点代表，而是把 cluster 内 anchor 按 entry phase 切分，
      在 (phase, anchor) 子段上重算 path-quality，再做 cluster mixture taxonomy。
      并列计算 PIT-observable 与 outcome-relative 两套 entry-phase；
      用随机切分基线证明异质性下降是真实结构而非样本变小假象。
裁决：entry-phase 切分能否显著降低 cluster 内异质性、提升单一 subtype 覆盖率、
      跨 split 形成 material subtype，且显著优于随机切分基线。
授权：仅可能授权 15D；不授权任何 separability / entry / 模型 / 仓位 / label 部署。
```

### Phase 15C 实际结果（2026-06-26）

```text
15C decision = 15C_entry_phase_reduces_heterogeneity_but_coverage_insufficient。
关键证据：
  - outcome-relative phase 通过 real-over-random（train uplift 0.1133、robustness 0.1135），
    证明 winner path 形态异质性是真实结构；
  - PIT-observable phase 三个 split 都没过 real-over-random（uplift ≈ 0.045），
    说明当前 t0 morphology（ret60d / distance_to_high_low / trend_spread）太粗；
  - coverage 不足：up50 train PIT single coverage 0.1188、mixed share 0.8223，
    大量 episode 被硬阈值打成 mixed。
因此 15D 的 "条件开启" 前提（PIT supported）未满足，15D 暂不开启。
```

### Phase 15C2: Winner Soft Shape Membership Diagnostic（本轮新增，15C 姐妹诊断）

```text
前提：15C 证明形态结构真实存在（outcome real-over-random 通过），
      但被两个约束压住：(A) 硬分类 dominant_share>=0.70 把边界 episode 打成 mixed；
      (B) PIT real-over-random / coverage gate 绑定了 "服务 t0 separability" 目标。
判断：人工目标是 "区分 winner 形态"，不是 "t0 可知"。t0 可知性是后续独立问题。
目标：显式解除上述两约束。复用 15B 的 6 个 morphology 原型与 train-only 冻结特征，
      把硬分类换成 "到原型中心的标准化距离 + softmax" 软隶属度向量；
      用隶属熵 / 尖锐度 + 随机基线判定 winner 形态是否真实可分；
      输出 path-type 共现谱与 descriptive winner 形态图谱。
裁决：软隶属尖锐性是否显著优于随机基线（排除 softmax 假象），
      且 capture-friendly 原型不是 compression / drawdown-reversal 换名。
授权：无。15C2 是 descriptive 终点；即使形态高度可分，next_allowed_requirement 仍为 none。
      任何 separability / t0 prediction 必须独立重新立项并自行论证 t0 可知性。
```

### Phase 15D: Capture-Friendly Winner Separability Diagnostic（条件开启，前提暂未满足）

```text
前提：需要一个上游诊断给出 "PIT-observable + capture-friendly subtype 可作为 separability 候选"。
      15C 的 PIT scheme 未通过，15C2 是 descriptive 终点不授权 separability，
      因此当前没有任何上游授权 15D。若后续重新设计 PIT-observable phase（更贴近 episode onset /
      compression-release / volume-turnover regime / breakout timing 的 t0 features）并通过，
      才可能重新满足该前提。
目标：只对 PIT-observable entry-phase + capture-friendly subtype
      （smooth_trend / stair_step / slow_grind）检验 t0-close 可观测特征的 train-only 可分性。
注意：15D 仍是 separability 诊断，不是 entry；不得使用 outcome-relative phase 作为 feature；
      即使可分，也不直接授权交易。
```

### Phase 15E+（远期，仅在 15D 通过后定义）

```text
若 capture-friendly winner 在 t0 可分，且不是已失败形态换名，
后续才进入序贯 / 续航范式：t0 不预测终局，只判断 "下一小段是否值得参与"，
用短 horizon survival label 链式叠加，让市场用后续 path 持续淘汰输家。
这一阶段才是真正的 winner entry，且 cost 被长持有摊薄。
此阶段的 requirement 必须重新冻结 entry / exit / cost / 序贯决策结构，不在本 plan 展开。
```

## 3. 不可违反的纪律（从 12-14 失败中提炼）

```text
1. censored row 绝不当 negative —— 否则污染对照，重蹈 label 偏差。
2. 三档阈值 {0.50, 1.00, 1.50} 预注册冻结，不得用 validation / robustness 事后增减。
3. 任何 t0-close morphology readout 只用 reference_pos 及之前数据；label 可用未来 path。
4. slow winner 必须做与 compression / drawdown-reversal 的 overlap 诊断；
   若只是这些已失败形态换名，不直接进入 separability。
5. 15B 必须先解决 winner path type，而不是把 fast / slow 当成最终 label。
6. path-shape taxonomy 必须先 episode 去重，再讨论 anchor-row readout。
7. entropy 只能作为 path-shape descriptor，不能单独定义 winner。
8. 15A / 15B / 15C 都是 label 诊断，绝不产生 entry / 模型 / 仓位 / separability / label 部署授权。
9. entry / cost / universe 三块地基本轮不动（universe 右尾密度可作为另一独立诊断方向，
   不在 15A scope 内）。
10. 15C 因果顺序冻结：entry_phase -> sub-segment path-quality -> cluster mixture；
    path-quality 是 (entry_phase x anchor) 的属性，不是 episode 的属性，
    绝不先对整段 / medoid 算 quality 再按 phase 分组（这是 15B 的 bug）。
11. 15C 必须并列计算 PIT-observable 与 outcome-relative 两套 entry-phase；
    outcome-relative phase 永远只能是 label-form descriptor，绝不升级为 t0 feature。
12. 15C 异质性下降必须对照随机切分基线证明为真实结构，
    不得把 "子段样本变小导致 dominant_share 机械上升" 当成切分有效。
```

## 4. 与既有失败路径的边界

```text
15A 不复活：13A dense token、13A2 directional filter、13A3/13C compression-repair、
            13E nonlinear、13F delayed entry、13G overlay、14A sparse event / cohort。
15A 只新增一件事：质疑 fixed-horizon winner label 是否 right-censor 慢牛大赢家。
```
