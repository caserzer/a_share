# 16E Sequential Continuation Utility Diagnostic Report

## 1. 单行裁决

`decision_state = 16E_utility_diagnostic_not_supported`；`next_allowed_requirement = none`。

16E 不授权 entry、exit、holding、chained simulation、portfolio backtest、model deployment、production signal 或 live trading。16E 只回答一个问题：16D 选出的 `defend_next_h20` vs `continue_next_h20` 单步 h20 action，在冻结的 diagnostic action semantics 下，是否有足够的 utility 支撑进入 16F chained action transition freeze。答案是否定的。

核心裁决原因是：50bps primary close-to-close utility 在 train 和 robustness 都为负，虽然 drawdown avoidance gate 通过，但 return utility gate 失败。当前结果属于 `drawdown_reduction_only_return_not_supported`，不是成本脆弱、执行延迟脆弱，也不是 context-concentrated-only。

## 2. 血缘与授权复验

16E 复验了 16D 的 publishable decision、hard gates、authorization booleans 和 primary bottom-30% action rule。`policy_action_sample.csv.gz` 没有作为 row-level truth 使用；本次使用的是 16D full action panel cache，并通过 row count、threshold、split count 和 known-failed context replay 验证。

| item | value |
| --- | --- |
| upstream decision | `16D_policy_preflight_ready_for_utility_diagnostic` |
| upstream next allowed | `requirement_16e_sequential_continuation_utility_diagnostic.md` |
| primary policy | `defense_bottom_30pct_continuation_score_v1` |
| selected threshold | `up50pct` |
| threshold value replayed | 0.457071 |
| primary horizon | 20 sessions |
| action panel source | `optional_16d_cache_used` |
| primary policy row count | 23,405 |
| binary / neutral rows | 17,339 / 6,066 |
| full action panel rebuild status | pass |
| action semantics gate | pass |
| policy utility binding gate | pass |
| price path replay gate | pass |
| search accounting gate | pass |

16D 作为分类/捕捉型 preflight 的表现仍然成立：train negative capture rate 为 0.470721，robustness negative capture rate 为 0.372624；train positive sacrifice rate 为 0.217305，robustness positive sacrifice rate 为 0.149331。16E 的结论不是否定 16D 的排序能力，而是说明这套 bottom-30% action 在经济 utility 口径下不能通过单步 h20 gate。

## 3. 冻结的 Action Semantics

本次 diagnostic 使用固定语义：

| field | value |
| --- | --- |
| primary action semantics | `full_avoidance_cash_h20_close_to_close_v1` |
| decision time | `step_start_date close` |
| baseline action | `blind_continue_next_h20` |
| continue exposure | 1.0 |
| defend exposure | 0.0 |
| defend cash return h20 | 0.0 |
| primary round-trip defense cost | 50 bps |
| cost grid | 0, 25, 50, 100 bps |
| delay stress | `one_session_delay_close_to_close_v1` |
| validation / robustness used for semantics selection | false / false |

解释边界很重要：这里的 `defend_next_h20` 不是完整卖出策略、不是止损规则、不是持仓管理，也不是可以交易的部署信号。它只是一个单步 h20 block 内的 full avoidance cash diagnostic，用来评估如果在该 block 开始时完全规避，是否能在 return/drawdown/cost/delay 口径下优于 blind continue。

## 4. 样本、价格重放和分母

价格路径全部从 qfq close path 重算。step start/end close、max drawdown 和 one-session delay row 均通过重放校验。

| split | labelable steps | valid price rows | start mismatch | end mismatch | max dd diff max | delay missing | price gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 20,245 | 20,245 | 0 | 0 | 0.000000 | 0 | pass |
| robustness | 2,496 | 2,496 | 0 | 0 | 0.000000 | 0 | pass |
| validation | 664 | 664 | 0 | 0 | 0.000000 | 0 | pass |

所有 utility 均使用 full labelable denominator。neutral rows 留在分母中，不使用 defended-only denominator。50bps 下 action coverage 为：train defend 5,584 / 20,245 = 27.58%；robustness defend 486 / 2,496 = 19.47%；validation defend 183 / 664 = 27.56%。

## 5. Primary Utility 结果

50bps 是 primary cost tier。train、robustness、validation 的 full-denominator mean incremental return 都为负；drawdown avoidance gate 均通过。

| split | labelable | defended | positive | negative | neutral | mean incremental | sum incremental | mean drawdown avoided | return gate | drawdown gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| train | 20,245 | 5,584 | 10,078 | 4,884 | 5,283 | -0.002316 | -46.892550 | 0.025833 | fail | pass |
| robustness | 2,496 | 486 | 1,346 | 526 | 624 | -0.005529 | -13.800725 | 0.017731 | fail | pass |
| validation | 664 | 183 | 325 | 180 | 159 | -0.005812 | -3.858970 | 0.025309 | fail | pass |

成本网格显示，0bps 时 utility 已经为负，因此失败不是单纯由交易成本造成：

| split | cost bps | defended | mean incremental | sum incremental | return gate | drawdown gate |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| train | 0 | 5,584 | -0.000937 | -18.972550 | fail | pass |
| robustness | 0 | 486 | -0.004556 | -11.370725 | fail | pass |
| validation | 0 | 183 | -0.004434 | -2.943970 | fail | pass |
| train | 25 | 5,584 | -0.001627 | -32.932550 | fail | pass |
| robustness | 25 | 486 | -0.005042 | -12.585725 | fail | pass |
| validation | 25 | 183 | -0.005123 | -3.401470 | fail | pass |
| train | 50 | 5,584 | -0.002316 | -46.892550 | fail | pass |
| robustness | 50 | 486 | -0.005529 | -13.800725 | fail | pass |
| validation | 50 | 183 | -0.005812 | -3.858970 | fail | pass |
| train | 100 | 5,584 | -0.003695 | -74.812550 | fail | pass |
| robustness | 100 | 486 | -0.006503 | -16.230725 | fail | pass |
| validation | 100 | 183 | -0.007190 | -4.773970 | fail | pass |

## 6. Six-cell Utility Decomposition

50bps 下，train 和 robustness 的负 utility 主要来自错防 positive 的 opportunity cost。防住 negative 和 neutral 的收益存在，但不足以覆盖 positive sacrifice。

| split | cell | n | continue return sum | policy net return sum | incremental sum | drawdown avoided sum |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| train | defended_positive | 2,190 | 320.257522 | -10.950000 | -331.207522 | 66.343026 |
| train | defended_negative | 2,299 | -253.662136 | -11.495000 | 242.167136 | 383.607110 |
| train | defended_neutral | 1,095 | -47.622836 | -5.475000 | 42.147836 | 73.042207 |
| train | continued_positive | 7,888 | 823.964620 | 823.964620 | 0.000000 | 0.000000 |
| train | continued_negative | 2,585 | -265.689063 | -265.689063 | 0.000000 | 0.000000 |
| train | continued_neutral | 4,188 | -163.810780 | -163.810780 | 0.000000 | 0.000000 |
| robustness | defended_positive | 201 | 31.494665 | -1.005000 | -32.499665 | 6.242359 |
| robustness | defended_negative | 196 | -16.673211 | -0.980000 | 15.693211 | 32.148781 |
| robustness | defended_neutral | 89 | -3.450729 | -0.445000 | 3.005729 | 5.864692 |
| robustness | continued_positive | 1,145 | 129.168474 | 129.168474 | 0.000000 | 0.000000 |
| robustness | continued_negative | 330 | -32.159819 | -32.159819 | 0.000000 | 0.000000 |
| robustness | continued_neutral | 535 | -21.324855 | -21.324855 | 0.000000 | 0.000000 |
| validation | defended_positive | 77 | 12.829871 | -0.385000 | -13.214871 | 2.385332 |
| validation | defended_negative | 81 | -8.726611 | -0.405000 | 8.321611 | 12.825346 |
| validation | defended_neutral | 25 | -1.159291 | -0.125000 | 1.034291 | 1.594761 |

关键比例：

| split | positive defended rate | negative defended rate | neutral defended rate | defended positive loss / defended negative gain | net shortfall after negative+neutral |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 21.73% | 47.07% | 20.73% | 1.367682 | 46.892550 |
| robustness | 14.93% | 37.26% | 14.26% | 2.070938 | 13.800725 |
| validation | 23.69% | 45.00% | 15.72% | 1.588018 | 3.858970 |

AFML 解释：16D policy 有 negative capture，但 economic utility 要求捕捉收益大于错防正例的 opportunity cost。robustness 中每单位 defended negative gain 对应超过 2 倍的 defended positive loss，说明分类优势没有转化为可接受的收益/风险交换。

## 7. Positive Sacrifice、Negative Avoidance 和 Leakage

Positive sacrifice 与 negative avoidance 的对照如下：

| split | defended positive n | defended positive mean continue return | defended positive incremental sum | sacrificed upside |
| --- | ---: | ---: | ---: | ---: |
| train | 2,190 | 0.146236 | -331.207522 | 331.207522 |
| robustness | 201 | 0.156690 | -32.499665 | 32.499665 |
| validation | 77 | 0.166622 | -13.214871 | 13.214871 |

| split | defended negative n | defended negative mean continue return | defended negative incremental sum | defended negative drawdown avoided mean | avoided loss |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 2,299 | -0.110336 | 242.167136 | 0.166858 | 277.321853 |
| robustness | 196 | -0.085067 | 15.693211 | 0.164024 | 20.513371 |
| validation | 81 | -0.107736 | 8.321611 | 0.158338 | 9.365627 |

Continued negative leakage 没有消失。即使 16E 的 caveat 字段为空，原因也不是 leakage 不重，而是需求规定 `utility_positive_but_leaky` 只有在 primary utility gates pass 后才可触发；当前 primary return utility gate 已 fail。

| split | continued negative n | residual loss | defended negative avoided loss | residual loss share | leakage caveat |
| --- | ---: | ---: | ---: | ---: | --- |
| train | 2,585 | 279.257036 | 277.321853 | 1.006978 | none, primary utility failed |
| robustness | 330 | 33.661775 | 20.513371 | 1.640967 | none, primary utility failed |
| validation | 99 | 11.137834 | 9.365627 | 1.189225 | none, primary utility failed |

Neutral rows 提供了一部分正向 incremental utility，但不足以改变裁决：

| split | neutral n | neutral defended | neutral continued | neutral continue mean | neutral incremental mean | neutral gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| train | 5,283 | 1,095 | 4,188 | -0.040022 | 0.007978 | pass |
| robustness | 624 | 89 | 535 | -0.039704 | 0.004817 | pass |
| validation | 159 | 25 | 134 | -0.044597 | 0.006505 | pass |

## 8. Context Utility

Non-known-failed context 是 primary context gate。known-failed context 只能解释集中性，不能 rescue 非 known-failed 失败。50bps 下，non-known-failed context 在 train 和 robustness 都失败；known-failed context 本身也没有通过 robustness utility。

| split | context | labelable | defended | mean incremental | sum incremental | mean dd avoided | return gate | context status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| train | all_steps | 20,245 | 5,584 | -0.002316 | -46.892550 | 0.025833 | fail | readout |
| train | late_rescue_context | 10,621 | 2,912 | -0.000094 | -0.994448 | 0.025807 | fail | readout |
| train | non_late_rescue_context | 9,624 | 2,672 | -0.004769 | -45.898103 | 0.025862 | fail | readout |
| train | known_failed_context_any | 15,454 | 4,298 | -0.000978 | -15.112635 | 0.026363 | fail | readout |
| train | non_known_failed_context | 4,791 | 1,286 | -0.006633 | -31.779915 | 0.024125 | fail | fail |
| robustness | all_steps | 2,496 | 486 | -0.005529 | -13.800725 | 0.017731 | fail | readout |
| robustness | late_rescue_context | 423 | 80 | 0.001413 | 0.597836 | 0.016554 | pass | readout |
| robustness | non_late_rescue_context | 2,073 | 406 | -0.006946 | -14.398562 | 0.017971 | fail | readout |
| robustness | known_failed_context_any | 1,301 | 280 | -0.005447 | -7.086905 | 0.019042 | fail | readout |
| robustness | non_known_failed_context | 1,195 | 206 | -0.005618 | -6.713821 | 0.016303 | fail | fail |
| validation | all_steps | 664 | 183 | -0.005812 | -3.858970 | 0.025309 | fail | stress_readout |
| validation | late_rescue_context | 489 | 140 | -0.000816 | -0.398789 | 0.027629 | fail | stress_readout |
| validation | non_late_rescue_context | 175 | 43 | -0.019772 | -3.460180 | 0.018828 | fail | stress_readout |
| validation | known_failed_context_any | 599 | 167 | -0.003143 | -1.882686 | 0.026297 | fail | stress_readout |
| validation | non_known_failed_context | 65 | 16 | -0.030404 | -1.976284 | 0.016210 | fail | stress_readout |

Context insight：late-rescue robustness 子集的 mean incremental return 为 +0.001413，但 train late-rescue 已经是 -0.000094，validation late-rescue 也是 -0.000816。因此这不能构成稳健授权。真正的 primary context - non-known-failed - 在 train、robustness、validation 都为负，说明该 action 更像一个条件风险读数，而不是 morphology-independent 的可链式 transition signal。

## 9. Cost、Delay 和 Validation Stress

Delay stress 使用 full labelable denominator。50bps 下：

| split | primary close-to-close mean | one-session-delay mean | primary minus delay | delay status |
| --- | ---: | ---: | ---: | --- |
| train | -0.002316 | -0.002544 | 0.000227 | fail |
| robustness | -0.005529 | -0.005086 | -0.000443 | fail |
| validation | -0.005812 | -0.006278 | 0.000466 | fail |

Validation 只作为 stress readout，不参与 action semantics、threshold、cost 或 context selection，也不单独阻塞裁决。

| stress split | cost bps | labelable | defended | mean incremental | delay mean incremental | used for selection | blocks decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| validation | 0 | 664 | 183 | -0.004434 | -0.004900 | false | false |
| validation | 25 | 664 | 183 | -0.005123 | -0.005589 | false | false |
| validation | 50 | 664 | 183 | -0.005812 | -0.006278 | false | false |
| validation | 100 | 664 | 183 | -0.007190 | -0.007656 | false | false |

## 10. Search Accounting

Search accounting 通过：

| field | value |
| --- | --- |
| search family | `sequential_continuation_utility_diagnostic` |
| primary policy | `defense_bottom_30pct_continuation_score_v1` |
| primary action semantics | `full_avoidance_cash_h20_close_to_close_v1` |
| primary cost | 50 bps |
| validation used for selection | false |
| robustness used for selection | false |
| return metric used for selection | false |
| cost metric used for selection | false |
| context filter used for selection | false |
| threshold changed after 16D | false |
| model refit after 16D | false |
| entry rule defined | false |
| chained policy simulated | false |
| portfolio metric computed | false |
| deployment metric computed | false |

因此，16E 的失败不是 OOS selection 或 chained simulation contamination 造成的，而是 frozen single-step action 在 utility math 下未达标。

## 11. Findings And Insight

1. 16D policy 有分类价值，但不足以成为 utility-positive action。
   16D 的 train/robustness negative capture 分别为 47.07% / 37.26%，说明 bottom-30% continuation score 确实捕捉到一部分 negative continuation。然而 16E 把 action 映射到 cash avoidance 后，robustness defended positive 的损失为 -32.499665，defended negative 的收益只有 +15.693211，neutral 贡献 +3.005729，净 shortfall 为 -13.800725。分类信号没有转化成经济上可接受的 action utility。

2. Drawdown reduction 不是充分条件。
   所有 split 的 drawdown avoidance gate 都通过，50bps robustness mean drawdown avoided 为 0.017731，defended-negative drawdown avoided mean 为 0.164024。但 AFML 决策需要 utility gate，而不是单独的 drawdown gate。当前状态应解释为 risk-reduction-only readout，不应解释为可交易 exit/holding policy。

3. 0bps 仍失败，说明根因不是交易成本。
   0bps 下 train mean incremental return = -0.000937，robustness = -0.004556，validation = -0.004434。成本只会扩大负 utility；即使零成本执行，这个 action 仍不能通过 primary return gate。

4. Continued negative leakage 仍然严重，但不是当前 caveat 的触发路径。
   robustness continued negative residual loss share = 1.640967，说明被继续持有的 negative loss 大于已防住 negative 的 avoided loss。由于 primary return utility gate 已失败，`utility_positive_but_leaky` caveat 按需求不触发；但研究含义仍然明确：policy 同时存在 missed-negative 和 false-positive 两侧损耗。

5. Context 不能 rescue。
   non-known-failed context 在 train 和 robustness 均失败，robustness known-failed context 也为负。late-rescue robustness 局部为正，但 train/validation late-rescue 不稳健。因此 16E 不能把结果降格成“只在某个 context 下可进入 16F”的授权。

6. 16F 当前不被授权。
   16F chained action transition freeze 的前提是 16E 证明单步 action utility 通过。当前 primary return gate、delay stress gate、context utility gate 均未通过，因此不应进入 chained transition simulation 或完整 holding policy 设计。

## 12. 后续研究方向

建议不要直接写 16F。更合理的下一步是围绕 16E 的失败做 postmortem 或 alternative hypothesis requirement：

1. 将 16D score 降级为 meta-label / participation filter，而不是直接 action。
   现有证据更支持“它能提示风险区域”，不支持“它能直接触发 full h20 avoidance”。

2. 重构目标函数，从分类 capture 改为 utility-weighted objective。
   需要让 positive sacrifice、negative severity、drawdown depth、neutral distribution 和 continued negative leakage 同时进入训练/阈值选择，而不是先做分类 preflight 再事后套 utility。

3. 探索 severity-aware 或 asymmetric threshold。
   当前 false positive 的平均 sacrificed upside 太大，尤其 robustness defended positive mean continue return = 0.156690。后续如果继续研究，应优先减少高-upside positive 被 defend 的概率。

4. 将 drawdown reduction 作为风险 overlay，而不是独立交易动作。
   当前 drawdown avoided 有经济含义，但 return utility 不过关。它可能适合作为仓位上限、风险预算或风险解释层，而不是 full avoidance action。

5. 单独诊断 missed-negative leakage。
   robustness continued negative residual loss share = 1.640967，说明当前 bottom-30% threshold 留下太多 negative loss。后续可以研究是否存在更稳定的 severity signal，而不是直接提高 defend rate。
