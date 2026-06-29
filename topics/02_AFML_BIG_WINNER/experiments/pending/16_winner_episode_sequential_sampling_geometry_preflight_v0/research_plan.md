# Episode 16 研究计划：从 winner label diagnostic 转向序贯 / 续航范式

## 0. 定位

Episode 16 是 Episode 15（path-defined winner label diagnostic）之后的范式转换。它不再问 "winner 是不是某种形态"，而是问 "如果不预测终局、只在持有过程中一段一段判断是否继续参与，采样地基与 label 设计应该怎么做"。

Episode 16 的第一步**不是**直接做序贯 entry，而是先做采样几何 preflight，因为 Episode 15 已经证明 anchor 不是独立样本单元。

**当前进度（2026-06-29）：** 16A / 16B / 16C / 16D 四个 phase 均已在磁盘上完成（report + tables + manifest 齐备），最新已落地裁决为
`16D_policy_preflight_ready_for_utility_diagnostic`。**当前研究前沿是 16E**（`requirement_16e_sequential_continuation_utility_diagnostic.md`，尚未创建）。下文 §2 各 phase 的"本轮 / 已完成 / 下一步"标注以此为准。

**路径约定：** 旧 requirement 中出现的绝对 `REPO_ROOT` 只记录作者环境来源；后续 requirement 应使用 repo-relative path 或 resolver alias，不得把 `/home/xiaolv/code/a_share` 当作可移植路径假设。


## 1. 从 Episode 15 继承的判断

15A→15C2 的累积结论（来自各自报告）：

```text
15A: fixed-120d label 对慢速 path-defined winner 存在 material right-censoring（真实）。
15B: 整段 winner_episode_cluster 硬分类 path shape -> 统计单元太粗（representative taxonomy disagreement 0.7265）。
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

### Phase 16A: Sequential Sampling Geometry Preflight（已完成）

```text
目标：在写任何序贯 label / entry 之前，先钉死采样几何真相——
      anchor 数 vs episode cluster 数 vs 时间去重 step 数的真实比例、
      短窗 horizon 网格、step 间时间重叠、effective sample size、
      同 threshold / instrument 的 episode cluster non-overlap lineage audit。
裁决：序贯范式可用的采样单元与 horizon 候选是什么，anchor 高估了多少倍有效样本，
      effective sample 是否足够、是否跨 split 稳定。
授权：仅可能授权 16B 设计诊断；不授权任何 sequential label / entry / 收益 / 模型 / separability。
纪律：16A 绝不计算 forward return / 收益；纯采样几何诊断。
```

### Phase 16B: Sequential Continuation Label Design Diagnostic（已完成）

```text
前提：16A decision = 16A_sampling_geometry_ready_for_sequential_label_design。
目标：基于 16A 钉死的采样单元与 horizon，设计短窗 continuation / survival label
      （"下一小段是否值得继续参与"），并做 label 的 base rate / 去重后样本量 /
      与已知失败形态重叠的诊断。仍是 label-form diagnostic，不做 entry / 收益。
裁决：短窗 continuation label 是否有非平凡 base rate、去重后样本是否足够、
      是否不是 compression / drawdown-reversal 已失败形态换名。
授权：仅可能授权 16C；不授权 entry / 收益 / 模型。
```

### Phase 16C: Sequential Continuation Separability Diagnostic（已完成）

```text
前提：16B 通过。
目标：检验 "持有中某一步的 t0-observable 状态" 是否对 "下一小段 continuation label" 有
      train-only 可分性。这是第一次允许引入 t0 可观测特征，但仍是 separability 诊断，不是 entry。
注意：必须复用 16A 的 effective-sample 去重，不得用 step 数当独立样本高估功效。
```

### Phase 16D: Sequential Continuation Policy Preflight（已完成）

```text
前提：16C decision = 16C_sequential_continuation_separability_ready_for_policy_preflight。
目标：把 16C 的 continuation score 转成 train-frozen 的 defend-vs-continue label action，
      检查 threshold freeze、neutral handling、context stratification、search accounting 是否可审计。
裁决：primary policy = defense_bottom_30pct_continuation_score_v1；
      decision = 16D_policy_preflight_ready_for_utility_diagnostic。
授权：仅可能授权 16E utility diagnostic；不授权 entry / exit / holding / return backtest / cost model / deployment。
纪律：defend_next_h20 只是 counterfactual label action，不是实际卖出、减仓、避险或交易建议。
```

16D 的关键证据：

```text
1. primary bottom-30% policy 在 robustness 捕获 196/526 = 37.26% negative；
2. robustness defense precision = 49.37%，高于 binary negative base rate 28.10%，lift = +21.27pp；
3. non-known-failed robustness context 仍有 lift = +25.30pp；
4. neutral 占 labelable steps 约 25%，不能在 utility 阶段被偷换成 positive 或 negative；
5. robustness defense rate 只有 21.21%，低于 train 的 30.00%，必须作为 coverage/capacity caveat。
```

### Phase 16E: Sequential Continuation Utility Diagnostic（本轮 requirement / 下一步）

```text
前提：16D decision = 16D_policy_preflight_ready_for_utility_diagnostic。
目标：第一次把 defend-vs-continue action 放到 utility / return / drawdown / cost / execution 口径下诊断，
      但仍只评估单个 h20 continuation decision，不做完整 chained strategy 或 deployment。
前置门：16E 在任何 return / cost / execution 表之前，必须先冻结 single-step diagnostic action semantics：
        defend_next_h20 在单个 h20 block 内到底表示 full_exit、partial_de-risk、no-additional-sleeve
        还是 cash/benchmark substitution；若语义无法冻结，16E fail closed，不得计算 utility。
核心问题：少踩 negative deep-drawdown 的收益，是否足以抵消错防 positive、continued negative leakage、
          neutral 经济分布、交易成本、滑点、执行延迟和资金占用。
必须继承：up50pct、h20、non-overlap full-horizon step、train-only preprocessing、
          train-frozen bottom-30% threshold、known-failed context caveat、neutral denominator caveat。
授权：若通过，只能授权 16F chained action transition freeze；不得直接授权完整 entry / exit / holding strategy。
```

16E 的 primary readout 应至少包括（前两项为并列首位裁决量：utility 净值由
"防住 negative deep-drawdown 省下的损失" 减去 "错防 positive 放弃的 upside" 决定，
缺任一侧都无法做出 utility 裁决）：

```text
0. single-step diagnostic action semantics pre-gate：
   primary defend semantics、execution timing、cash/benchmark treatment、cost scope 必须先冻结；
   validation / robustness 不得用于选择语义。
1. [并列首位裁决量 A] positive sacrifice 的 opportunity cost：
   被防住的 positive（16D robustness 实测 201 个，sacrifice rate 14.93%）放弃了多少 upside，
   按 realized h20 return / 厚尾 upside 分布给出，而非仅计数。
2. [并列首位裁决量 B] avoided negative deep-drawdown 的 utility 节省：
   被正确防住的 negative（16D robustness 196/526）规避的 realized loss / max drawdown / tail loss。
3. continue_next_h20 的 realized h20 return / max drawdown / tail loss distribution；
4. defended bucket vs continued bucket 的 gross utility reconciliation：
   必须同时核对 defended_positive / defended_negative / defended_neutral /
   continued_positive / continued_negative / continued_neutral 六格 utility，
   不能只用 1 与 2 的 binary 净额替代总体 gross delta；
5. cost / slippage / one-session delay stress 后的 net utility delta；
6. continued negative leakage 的 residual loss（16D robustness 仍 continue 62.74% 的 negative）；
7. neutral rows 的独立 utility 分布（neutral 约占 labelable steps 25%，
   不得默认归零收益、零成本或随机归类）；
8. all / late_rescue / non_late_rescue / known_failed / non_known_failed 分层 utility；
9. train / robustness / validation stress readout，primary gate 仍以 robustness 为主。
```

### Phase 16F: Chained Action Transition Freeze

```text
前提：16E 已通过 utility diagnostic，且 single-step diagnostic action semantics pre-gate 已冻结。
目标：把 16E 的单步 primary semantics 扩展成 chained simulation 可执行的 transition contract，
      避免后续 simulation 中对 defend / continue / re-entry / cooldown 事后改口。
必须冻结：
  1. defend 持续多久；
  2. defend 后何时允许重新进入 continue 状态；
  3. 连续 low-score block 是否延长 defend；
  4. cash / benchmark / residual exposure 如何累积；
  5. cooldown、forced re-entry、forced exit 的触发条件；
  6. 不同 transition 的 cost and execution timing。
裁决：确认 16E primary single-step semantics 可以无歧义扩展为 chained transition contract；
      appendix semantics 不得在 16F 变成 primary。
授权：仅可能授权 16G chained sequential policy simulation preflight。
纪律：不得根据 16E 的 return/cost 结果重新挑选 action semantics；
      不得把 defend 解释成卖在 h20 内最优价格，也不得保留上涨同时规避下跌。
```

### Phase 16G: Chained Sequential Policy Simulation Preflight

```text
前提：16F 冻结 chained action transition contract。
目标：把单步 h20 action 串起来，检查连续 decision points 是否仍可审计。
核心问题：
  1. 连续 defend 后何时重新允许 continue；
  2. h20 decision schedule 是否保持 non-overlap，不重新制造 anchor/overlap overcount；
  3. policy 是否导致过高 churn 或长期空仓；
  4. signal 是否只在 episode 特定阶段有效；
  5. chained exposure 的 effective sample / cluster dependency 如何计量。
授权：若通过，只能授权 16H entry-conditioned continuation diagnostic。
```

### Phase 16H: Entry-conditioned Continuation Diagnostic

```text
前提：16G 证明 chained continuation policy 可回放且没有重新制造样本依赖。
目标：检验 continuation module 接到真实 entry 来源或冻结 entry universe 后是否仍成立。
关键边界：
  1. 不在 16H 发明新 entry alpha；
  2. primary conditioning 只能使用冻结 upstream entry candidate / existing anchor universe；
     episode_start 只能作为 oracle upper-bound appendix，不得作为 primary real-entry source；
  3. 报告 entry phase、episode age、known-failed context、liquidity、board、calendar 分层；
  4. 明确区分 "winner episode 内持有管理" 和 "真实世界 entry 策略"。
授权：若通过，只能授权 16I full holding policy prototype。
```

### Phase 16I: Full Holding Policy Prototype

```text
前提：16H 证明 entry-conditioned continuation module 仍有 utility。
目标：冻结 entry、initial position、continue、defend、re-entry、forced exit、max holding、cost、portfolio accounting，
      形成完整 holding policy prototype。
必须冻结：
  entry source；
  execution price；
  decision calendar；
  max holding；
  re-entry cooldown；
  stop / forced exit；
  position sizing；
  transaction cost and slippage；
  portfolio aggregation；
  failed-data handling。
授权：若通过，只能授权 16J OOS robustness and ablation。
纪律：16I 是 prototype，不是 deployable strategy。
```

### Phase 16J: OOS Robustness And Ablation

```text
前提：16I prototype 可回放。
目标：证明完整 policy 的 utility 不是来自偶然 split、known-failed morphology、cost 假设过轻、
      特定 instrument/board/calendar/liquidity 结构或 hidden search。
必须做：
  cluster-blocked score shuffle；
  threshold family frozen readout；
  known_failed vs non_known_failed utility split；
  instrument / board / liquidity / calendar split；
  high-cost stress；
  delayed-execution stress；
  neutral stress；
  entry-source ablation；
  train-only calibration replay。
授权：若通过，只能授权 16K deployment readiness diagnostic。
```

### Phase 16K: Deployment Readiness Diagnostic

```text
前提：16J OOS robustness and ablation 通过。
目标：判断是否值得进入 production-grade research，而不是直接上线。
必须审计：
  PIT data availability；
  daily inference reproducibility；
  signal latency；
  suspension / limit-up / limit-down handling；
  turnover and capacity；
  slippage and market-impact assumptions；
  monitoring metrics；
  retraining schedule；
  model drift；
  action audit trail；
  rollback and fail-closed rules。
裁决：只能是 production_research_ready / blocked / not_supported；
      不得从 Episode 16 直接得出 live deployment authorization。
```

## 3. 关键失败模式

```text
1. winner-episode conditioning bias：
   16A-D 的 population 仍在 path-defined winner episode 内，可能只回答 "winner 内何时别继续"，
   不自动回答真实世界何时 entry。

2. label-utility mismatch：
   16B negative 是 h20 内 deep drawdown，positive 是 survival + end nonnegative；
   真实 utility 还受收益厚度、路径回撤、资金占用、成本和机会成本影响。

3. positive sacrifice too expensive：
   16D primary policy 在 robustness 错防 201 个 positive，positive sacrifice = 14.93%；
   若这些 positive 的 upside 很厚，defend 可能在 utility 上不划算。

4. negative leakage remains high：
   16D robustness 中仍有 62.74% negative 被 continue；
   policy 是风险集中器，不是完整风控器。

5. neutral denominator risk：
   neutral 约占 labelable population 四分之一；
   utility 阶段若把 neutral 当无收益、无成本或任意归类，都会污染结论。

6. known-failed context shadow：
   train / validation known-failed exposure 高；
   后续 utility 必须证明结果不是只来自 late-rescue 或其他已知失败 context。

7. score calibration / coverage drift：
   train bottom-30% threshold 迁移到 robustness 后 defense rate 只有 21.21%；
   这可能是保守迁移，也可能是 calibration drift。

8. chained decision dependency：
   单步 non-overlap 不保证 chained policy 独立；
   连续 decision 可能重新制造 overlap、duration weighting 和重复计数。

9. cost and execution reversal：
   若 defend 对应真实卖出/买回，cost、slippage、停牌、涨跌停、冲击成本可能翻转 utility。

10. entry unresolved：
    Episode 16 当前主线是 continuation / holding management，不是 entry alpha；
    若没有独立 entry source，最终只能成为已有持仓管理模块。
```

## 4. 不可违反的纪律（从 12-15 失败中提炼）

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
10. 16E 之前不得计算 return / PnL / cost；16E 之后也只能按 phase authorization 逐步引入。
11. 16D 的 defend_next_h20 不是 exit policy；16E 必须先冻结 single-step diagnostic action semantics，
    才允许计算 return / cost / execution utility；16F 只负责链式 transition freeze。
12. 任何 chained policy 必须重新审计 overlap、effective sample、cluster dependency 和 search accounting。
13. 任何 entry-conditioned 研究不得把已知 winner episode membership 偷换成真实 entry alpha。
14. deployment readiness 只能在 16K 之后讨论，且 16K 也只授权 production-grade research，不授权 live trading。
```

## 5. 与 Episode 15 的边界

```text
Episode 16 不复活：15B 硬分类 path type、15C PIT entry-phase t0 feature、15C2 soft taxonomy。
Episode 16 只新增一件事：把研究单位从 "t0 给整段路径贴 label" 换成
"持有过程中一段一段判断是否继续参与"，并先证明这条线的采样地基是否成立。
Episode 15 的 winner episode cluster lineage、split boundary、path-defined label 被继承为输入。
```
