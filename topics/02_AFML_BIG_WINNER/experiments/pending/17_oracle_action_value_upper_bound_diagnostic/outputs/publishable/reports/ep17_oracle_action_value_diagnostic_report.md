# EP17 Oracle Action Value 诊断报告

## 1. 结论摘要

17D 的最终裁决是：

```text
final_decision_state = oracle_payoff_state_research_allowed
recommended_next_requirement = requirement_18_payoff_state_representation_research.md
selected_priority_rank = 6
```

这不是交易结论，而是研究授权结论。EP17A-17C 证明的是：在冻结 denominator、冻结 action semantics、冻结 cost=50bps、冻结 `q_defend=0.0` 的条件下，未来信息 oracle 确实存在可测 action-space value；并且这个 value 不只是完美 utility hindsight 的孤立现象，O1/O2/O4 三类更接近解释路径的 oracle 也都在 primary robustness slice 上通过了 top-k、bootstrap、matched-base gate。

最重要的解释是：

- **action-space headroom 存在**：O5 perfect utility primary 的 robustness mean incremental return 为 **2.9467%**。
- **label/path oracle 不是空的**：O1/O4 primary mean 都为 **2.4681%**，O2 primary mean 为 **1.8511%**，三者 gate 均为 pass。
- **payoff preservation 有实质支撑**：O4 label-positive primary 通过，top30/top20 high-upside stress 也通过；但 top10 过窄会失败。
- **当前 learned feature contract 仍失败**：16E return utility 不支持，16X payoff separability 失败，说明问题不是 action space 没价值，而是当前 observable representation 抓不到 payoff-state。
- **delayed timing 有信号但不是最终裁决**：robustness best delayed k=3 retention 为 **1.0156**，但 validation retention 只有 **0.8683**，未达到双 split dominance 要求。
- **capacity 不能解释本轮结论**：capacity 状态是 `appendix_only_nonblocking`，不能授权 execution-capacity 结论。

因此，下一步应进入 payoff-state representation research，而不是交易规则、entry/exit、holding policy、portfolio backtest、deployment 或 production signal。

## 2. 机器契约与输入可信度

17D 首先校验上游机器产物，而不是信任报告 prose：

```text
lineage_gate = pass
contract_validation_gate = pass
17C handoff = ready
17d_input_gate_audit = 38 / 38 pass
17d_contract_validation_audit = 120 / 120 pass
```

`17d_contract_validation_audit.csv` 覆盖了：

- 17C decision handoff：`EP17C_oracle_robustness_ready_for_diagnosis`，next requirement 指向 17D。
- 17C publishable tables：hash、row_count、schema 均与 manifest 对齐。
- 17B supporting tables：包含 `oracle_o2_drawdown_threshold_replay.csv`、`oracle_o5_action_selection_proof.csv`、`oracle_high_upside_threshold_freeze.csv` 等下游必需契约。
- 16D/16E/16E-postmortem/16X reference tables：hash、row_count、schema 均通过。
- Episode 16 final report hash：与 `episode_16_final_report_manifest.json` 对齐。
- authorization flags：entry、exit、holding、portfolio backtest、deployment、production signal、live trading 均为 false。

这个结果很关键：17D 的结论不是由人工解释拼出来的，而是建立在跨 16D/16E/16X 与 17B/17C 的机器契约一致性之上。

## 3. Final Decision Priority Replay

17D 的 priority tree 逐项裁决如下：

| priority | gate | observed | implication |
|---:|---|---|---|
| 1 | lineage / contract | pass | 不阻断 |
| 2 | O5 upper bound | pass | 当前 action space 有 material upper-bound value |
| 3 | capacity execution block | not_evaluable_nonblocking | 不触发 capacity-blocked |
| 4 | delayed decision support | fail | delayed 不足以成为最终裁决 |
| 5 | risk-only path | path risk pass, payoff preservation pass | 因 payoff 也 pass，不走 risk-only |
| 6 | payoff preservation + current feature gap | pass + pass | 触发最终裁决 |
| 7 | O5-only fallback | not used | 已有更强解释路径 |

因此最终落到 priority 6：

```text
oracle_payoff_state_research_allowed
```

这说明 EP17 的主发现不是“风险信号可用”，也不是“延迟执行可用”，更不是“完美 hindsight 可交易”。更准确的说法是：**存在 payoff-preserving action value，但当前 16-series feature/label contract 无法把它转成可学习、可部署的 observed-state policy。**

## 4. O5 Upper Bound：action-space headroom 的大小

Primary robustness slice 固定为：

```text
split_bucket = robustness
cost_bps = 50
q_defend = 0.0
```

核心 upper-bound 读数：

| oracle | observed_step_n | defended_rate | mean_incremental | trimmed_mean | bootstrap_low_min | topk_min | matched_min | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| O5 perfect utility | 2,496 | 42.3077% | 2.9467% | 2.7594% | 2.1661% | 2.6901% | 1.0000 | pass |

O5 的意义是 action-space 上界：它知道 defend 与 continue 的 realized net utility，因此只能用于证明“如果有足够好的状态识别，动作空间本身有价值”。它不能被解释成策略，也不能授权交易。

O5 与最好的 label/path oracle 的 headroom gap 为：

```text
best_label_path_mean = 2.4681%
o5_vs_best_label_path_gap = 0.4786 percentage point
```

这个 gap 的含义是：O1/O4 这种 label-level oracle 已经解释了 O5 大部分 value，但 O5 仍保留约 **47.86 bps** 的额外完美选择空间。

需要明确的是，这里是 mixed-denominator orientation：O5 primary 使用 `labelable_full` denominator，O1/O4 primary 使用 `binary_primary` denominator。因此该 gap 只能作为 EP18 研究方向的上游定位，不能直接作为 18D learned-score oracle-gap target。18D 必须在 aligned denominator 上重新计算 learned score 与 O4/O5 的 gap。

下一阶段不应直接追逐 O5，而应研究能否用可观测 payoff-state representation 缩小 aligned-denominator oracle gap。

## 5. Label / Path / Payoff Oracle 支撑

Primary label/path oracle 读数：

| oracle | denominator | observed_step_n | defended_rate | mean_incremental | trimmed_mean | bootstrap_low_min | topk_min | support |
|---|---|---:|---:|---:|---:|---:|---:|---|
| O1 negative label | binary_primary | 1,872 | 28.0983% | 2.4681% | 2.4747% | 1.4846% | 2.1953% | pass |
| O2 drawdown <= -10% | labelable_full | 2,496 | 21.0737% | 1.8511% | 1.8220% | 1.1368% | 1.6465% | pass |
| O4 label positive preservation | binary_primary | 1,872 | 28.0983% | 2.4681% | 2.4747% | 1.5143% | 2.1953% | pass |

三个结论：

1. O1 与 O4 在 binary primary 上给出同等 mean incremental return，说明 Episode 16 的 positive/negative label 在 hindsight 下确实有 action value。
2. O2 使用 labelable_full denominator，mean 较低但仍通过，说明 drawdown path-risk 本身也能产生正向防守价值。
3. O4 与 O1 同时通过，使最终解释不能停留在“只会避险”。如果只有 O2 pass、O4 fail，结论会偏向 risk-only；但现在 payoff preservation 也 pass，所以更合理的下一步是 payoff-state representation。

## 6. O2 Drawdown Threshold Curve：风险路径有价值，但不是最终答案

O2 使用 signed-negative drawdown，阈值越深，防守行越少：

| O2 variant | signed threshold | defended_n | defended_rate | mean_incremental | topk_min | bootstrap_low_min | decay vs -8% | gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| O2_dd_08pct_stress | -0.08 | 731 | 29.2869% | 2.0213% | 1.8090% | 1.2087% | 0.0000 pp | pass |
| O2_dd_10pct_primary | -0.10 | 526 | 21.0737% | 1.8511% | 1.6465% | 1.1368% | -0.1702 pp | pass |
| O2_dd_12pct_stress | -0.12 | 369 | 14.7837% | 1.5295% | 1.3288% | 0.9173% | -0.4919 pp | pass |
| O2_dd_15pct_stress | -0.15 | 211 | 8.4535% | 1.0934% | 0.9135% | 0.6502% | -0.9280 pp | pass |
| O2_dd_20pct_stress | -0.20 | 71 | 2.8446% | 0.5593% | 0.4160% | 0.2511% | -1.4620 pp | pass |

这里的形态很干净：随着阈值从 -8% 加深到 -20%，defended_rate 从 **29.29%** 降到 **2.84%**，mean incremental 从 **2.0213%** 降到 **0.5593%**。所有阈值仍为 pass，但 value 单调衰减。

解释上，这说明“深回撤路径”确实是一个 action-value 来源；但它更像 risk overlay 的候选维度，而不是本轮最终答案。原因是 O4 payoff preservation 同样通过，且 final priority 明确规定：当 payoff preservation pass 时，不把 episode 降级为 risk-only。

## 7. O4 Upside Preservation：宽 payoff 状态有效，过窄 winner-only 失效

O4 的 high-upside stress 使用 train-frozen cutoff，不在 robustness/validation 重新选阈值：

| O4 variant | threshold | train cutoff | defended_n | defended_rate | mean_incremental | topk_min | bootstrap_low_min | topk | bootstrap |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| O4_label_positive_primary | label positive | NA | 526 | 28.0983% | 2.4681% | 2.1953% | 1.5143% | pass | pass |
| O4_high_upside_top30_stress | top30 | 5.9633% | 1,644 | 65.8654% | 2.2123% | 1.9731% | 1.3433% | pass | pass |
| O4_high_upside_top20_stress | top20 | 10.1229% | 1,910 | 76.5224% | 1.3158% | 1.1083% | 0.3581% | pass | pass |
| O4_high_upside_top10_stress | top10 | 17.2107% | 2,207 | 88.4215% | -0.3299% | -0.5047% | -1.6440% | fail | fail |

这个表是 17D 最重要的 insight 之一。

top30 与 top20 都能保留正向 value，说明 payoff preservation 不是只能靠极端赢家；它需要保留一个足够宽的 positive payoff 状态区域。top10 失败则说明，若只把最极端的 upside 当作“值得继续”的状态，会把大量中等但有贡献的赢家误防守掉，导致 mean incremental 变成负数。

因此下一阶段的 payoff-state representation 不应只建一个“极端大赢家识别器”。更合理的研究问题是：能否识别一个足够宽、稳定、可观测的 payoff-positive continuation state，让 top30/top20 这种区域在非 oracle 特征中可近似。

## 8. Episode 16 Bridge：为什么不是直接回到旧 learned model

16-series evidence 给出的结论是 current-feature gap，而不是 action-space no-value。

| source | metric | observed | interpretation |
|---|---|---:|---|
| 16D policy preflight | decision_state | 16D_policy_preflight_ready_for_utility_diagnostic | survival/risk policy 有可测试信号 |
| 16D robustness | negative capture | 37.2624% | 能抓到一部分负样本 |
| 16D robustness | precision lift vs binary negative base | 0.2127 | 防守命中率相对 base 有提升 |
| 16E utility diagnostic | decision_state | 16E_utility_diagnostic_not_supported | 当前 policy utility 不支持 |
| 16E primary | return utility gate | fail | return utility 主门失败 |
| 16E primary | drawdown avoidance gate | pass | 有 drawdown reduction，但不是 return utility |
| 16E six-cell | reconciliation status | pass | 算术一致性不是问题 |
| 16E-postmortem | directionality_gate | fail | utility 方向性不稳定 |
| 16E-postmortem | mainline closed | true | continuation-as-action 主线关闭 |
| 16X payoff precheck | payoff rank IC | 0.051877 | payoff 排序信号弱 |
| 16X payoff precheck | payoff-minus-survival margin | -0.000723 | payoff 不优于 survival |
| 16X payoff precheck | payoff_monotone_flag | false | payoff 单调性失败 |
| 16X payoff precheck | payoff_aligned_label_redo_authorized | false | 不授权重做 payoff label |

这组证据说明：

1. 16D 学到的是 survival / downside-risk 信息，能降低 drawdown，但不足以转换成稳健 return utility。
2. 16E-postmortem 已经排除了“只是算术或执行成本写错”的简单解释；six-cell 与 postmortem arithmetic 都是 pass，失败来自方向性和 payoff representation。
3. 16X 显示当前 feature contract 对 payoff severity 的排序能力很弱，且 payoff-minus-survival margin 为负。

因此，17D 把正向 oracle value 解释为 **payoff-state representation gap**。这比“继续调 survival threshold”更合理，也比“直接进入策略回测”更克制。

## 9. Delayed Timing Sensitivity：有 timing 信号，但 validation 不支持最终裁决

Delayed oracle 的 best k 都是 3 sessions：

| split | best_k | delayed_mean | gap_vs_o5_t0 | retention_vs_o5_t0 | k10_retention | delayed_gate |
|---|---:|---:|---:|---:|---:|---|
| train | 3 | 3.3311% | -0.2252 pp | 0.9367 | 0.7322 | fail |
| robustness | 3 | 2.9927% | +0.0460 pp | 1.0156 | 0.7964 | fail |
| validation | 3 | 3.3983% | -0.5156 pp | 0.8683 | 0.6507 | fail |

Robustness split 上，k=3 delayed mean 略高于 O5 t0，retention 为 **1.0156**，所以 timing_sensitivity_candidate 为 true。但 17D 要求 robustness 与 validation 双 split 同时满足 dominance 和 retention floor。validation 的 gap 为 **-0.5156 pp**，retention 只有 **0.8683**，不满足 `delayed_retention_floor = 1.0`。

这避免了一个常见误判：单个 robustness split 的 delayed improvement 可能只是时点结构或样本路径现象，不能直接升级为 delayed observed-state policy。17D 因此保留 timing insight，但不把最终裁决改为 `oracle_delayed_decision_supported`。

## 10. Capacity / Execution Boundary

Capacity 读数：

```text
capacity_status = appendix_only_nonblocking
capacity_execution_block_gate = not_evaluable_nonblocking
```

含义很直接：本轮没有足够的 capacity reconstruction 来判断 execution 是否会阻断 oracle value。它既不能推翻 payoff-state research，也不能授权 capacity-constrained portfolio backtest。

因此，capacity 在本报告中只是边界条件，不是研究方向选择的主因。

## 11. Findings

### Finding 1：action space 有价值，但不是 O5-only 伪阳性

O5 的 mean incremental 为 **2.9467%**，并且 bootstrap/top-k/matched-base 均通过。如果只有 O5 pass，17D 会落到 `oracle_value_exists_feature_gap`。但这里 O1/O2/O4 也 pass，说明 action value 并非只存在于完美 utility hindsight。

### Finding 2：O4 是下一步研究的核心证据

O4 label-positive primary 与 O1 negative primary 同样达到 **2.4681%** mean incremental，说明 preserving payoff-positive rows 与 defending negative rows 在 hindsight 下同样有价值。更重要的是，top30/top20 high-upside stress 仍 pass，说明 payoff preservation 有宽状态区域，而不是只靠极端 top10。

### Finding 3：top10 high-upside 失败给出了 representation 的形状约束

Top10 cutoff 为 **17.2107%**，defended_rate 高达 **88.4215%**，mean incremental 降到 **-0.3299%**。这意味着“只继续最极端赢家”会牺牲太多中等 payoff-positive continuation。下一步 representation 不应过窄，否则会把 payoff preservation 变成 overdefense。

### Finding 4：O2 风险路径有效，但不应主导下一阶段

O2 从 -8% 到 -20% 全部 pass，但 mean 单调从 **2.0213%** 降到 **0.5593%**。风险路径有价值，可作为 payoff-state representation 的辅助维度；但 payoff preservation 同时通过，所以不应把 EP17 降级为 risk-only overlay。

### Finding 5：16-series 失败不是反证，而是定位了 feature gap

16D 能捕捉部分负样本，16E 显示 drawdown avoidance pass 但 return utility fail，16X 显示 payoff separability fail。和 17D 的 oracle 结果放在一起看，结论不是“这个 action space 没价值”，而是“现有 feature contract 没有捕捉到 payoff-state”。

## 12. 下一步建议

建议生成并实现：

```text
requirement_18_payoff_state_representation_research.md
```

下一阶段应围绕以下问题设计：

1. 能否在 t0 之前或 t0 当下，用 PIT-valid observable features 近似 O4 的 payoff-positive state？
2. payoff-state 不应只瞄准 top10 极端 winner，应优先考虑 top30/top20 这种更宽的 positive payoff 区域。
3. O2 signed drawdown path-risk 可作为辅助特征或风险约束，但不应替代 payoff-state target。
4. delayed k=3 可以作为 timing sensitivity readout，但必须保留 validation dominance gate，不能只凭 robustness split 通过。
5. 任何后续研究仍必须保持 no entry/exit/holding/portfolio backtest/deployment/live trading authorization，直到非 oracle observed-state policy 通过独立 utility gate。

## 13. Search Accounting 与授权边界

17D 的 search accounting 机器表为：

```text
search_accounting_gate = pass
no_model_training = true
no_model_refit = true
no_survival_threshold_tuning = true
no_validation_selection = true
no_robustness_tuning = true
no_feature_selection = true
no_payoff_label_redesign = true
no_oracle_threshold_tuning = true
no_decision_threshold_tuning = true
```

这意味着 17D 只是 readout-only decision-tree layer。它没有重新训练模型、没有重新选择 survival/payoff/oracle 阈值、没有用 robustness 或 validation 调参，也没有做 feature selection 或 payoff label redesign。

授权边界同样由机器表固定：

```text
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
```

所以 `oracle_payoff_state_research_allowed` 只允许进入下一步研究需求，不允许把 oracle 读数解释成可部署策略。

## 14. 明确不授权事项

本报告不授权：

```text
entry policy
exit policy
holding policy
position sizing
portfolio construction
portfolio backtest
model deployment
production signal
live trading
```

EP17D 的正向结论只到 research authorization：允许研究 payoff-state representation，不允许把 oracle action value 当成可交易 edge。
