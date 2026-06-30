# EP17 Research Plan: Oracle Action-Value Upper-Bound Diagnostic

创建日期：2026-06-30

## 0. 实验定位

EP17 是 topic-level diagnostic restart，不是 EP16 的 `16F`，也不是 `16B2` payoff-aligned label redesign。EP16 已正式关闭 continuation-as-action mainline：

```text
EP16 closure_state = EP16_closed_no_next_requirement
continuation_as_action_mainline_closed = true
16F_chained_action_transition_freeze_authorized = false
16B2_payoff_aligned_label_redesign_authorized = false
entry_policy_authorized = false
exit_policy_authorized = false
holding_policy_authorized = false
portfolio_backtest_authorized = false
production_signal_authorized = false
live_trading_authorized = false
```

EP17 不尝试绕过这个关闭裁决。它只用 oracle replay 回答一个更上层的问题：

```text
当前 big winner / continuation decision-state universe 到底有没有可被利用的 action value?
```

EP16 已经证明：

```text
survival / drawdown-risk 有一定 OOS separability
但转成 defend / continue action 后
positive sacrifice > negative avoided
最终 full-denominator utility 为负
```

所以 EP17 不训练新模型，也不继续调 EP16 的 survival score。它建立一组 oracle upper bound：

```text
如果某类未来信息被完美知道，
在同一个 decision/action/cost space 内最多能带来多少 utility?
```

如果 oracle 都没有足够价值，继续训练模型没有意义。如果 oracle 有价值但 learned score 没价值，问题才可能是 feature、model、payoff label 或 action semantics 表达不足。

## 1. 核心研究问题

EP17 要回答五个问题。

### Q1. 当前 decision-state universe 是否存在 action value?

即使完美知道未来某些 outcome，是否能通过 defend / continue / partial defend / delayed decision 改善 utility?

解释边界：

```text
如果 perfect oracle 也无法改善:
    event source / holding state 本身缺少可交易 action value

如果 perfect oracle 改善巨大:
    当前系统不是没有机会，而是 feature / label / model / action 没有提取出来
```

### Q2. 问题是 risk signal 不够，还是 payoff signal 不够?

EP16 显示 risk signal 有，但 payoff ordering 不成立。EP17 要进一步分解：

```text
Perfect Negative Oracle 是否有效?
Perfect Positive Preservation Oracle 是否更关键?
Perfect Utility Oracle 的 value 来自 avoided loss，还是 retained right tail?
```

### Q3. 当前 action semantics 是否错误?

EP16 的 primary action 是 full avoidance cash：

```text
score low -> defend / exit to 0 exposure
```

但 low score bucket 混入了 high-upside positive，导致 positive sacrifice。EP17 要比较：

```text
full exit
partial defend
delayed defend
hold through
```

如果 partial defend 明显优于 full exit，说明 EP16 的 action mapping 太激烈。如果 oracle full exit 本身也无价值，则不是 action intensity 的问题。

### Q4. 是否需要延迟决策?

如果 t0 状态不可学，但 t+3 / t+5 / t+10 后 observed path 让 oracle value 明显改善，后续系统应转向：

```text
t0 small trial
t+k observed-state upgrade / exit
```

而不是在 t0 强行预测整段 h20 payoff。

### Q5. 如果 oracle 有价值，价值来自哪个方向?

EP17 最终要把失败方向归类为：

```text
A. event / source 没有足够 action value
B. action policy 设计错
C. 当前 feature representation 不足
D. payoff label 表达不足
E. payoff signal 只能在 delayed decision 后出现
F. execution / cost / capacity 吃掉理论 value
```

## 2. 实验边界

### 2.1 EP17 不做什么

EP17 不做：

```text
不训练新模型
不 refit EP16 ridge logistic
不调 survival score threshold
不重新设计 feature set
不重新定义 winner taxonomy
不做新的 archetype classifier
不启动 16F chained simulation
不启动 16B2 payoff label redesign
不做 production backtest claim
不输出 entry signal
不输出 exit / holding / sizing policy
```

### 2.2 EP17 做什么

EP17 只做：

```text
同一批 decision states
同一价格路径或同一可审计 qfq replay source
同一 split / episode-cluster discipline
同一 cost grid
同一 action definitions

用不同 oracle information set replay actions
比较 utility upper bound
```

### 2.3 Oracle 不是可部署信号

所有 oracle 都使用未来信息，不可部署。EP17 的任何正结果最多授权后续研究方向，例如 feature redesign、payoff-state representation 或 delayed observed-state diagnostic；不授权真实或模拟交易部署。

## 3. Primary Denominator

### 3.1 主分母

EP17 主分母沿用 EP16 的 non-overlap h20 full-horizon continuation decision states：

```text
primary_denominator =
    EP16 up50pct / h20 / full-horizon / non-overlap continuation decision states
```

要求：

```text
1. 每个 decision state 有明确 t0 / step_start
2. 每个 state 有完整 h20 outcome
3. 同一 episode 内不能密集重复采样
4. 保留 train / robustness / validation split
5. 保留 instrument、episode_cluster_id、step_id 用于 bootstrap
6. 保留 16B label_class: positive / negative / neutral
7. 保留 16D score 与 action bucket only for learned-score comparison, not for oracle selection
```

EP17A 必须冻结 `denominator_reconciliation` 表，不能只写一个 row count。EP16 同时存在 labelable denominator 与 binary denominator：

```text
split_bucket | labelable_step_n | binary_step_n | neutral_step_n
train        | 20,245           | 14,962        | 5,283
robustness   | 2,496            | 1,872         | 624
validation   | 664              | 505           | 159
```

口径定义：

```text
labelable_step_n = positive + negative + neutral
binary_step_n    = positive + negative
neutral_step_n   = neutral
```

每个 oracle 的 primary denominator 必须显式声明：

```text
O0 No Oracle Baseline                  -> labelable_full
O1 Perfect Negative Oracle             -> binary_primary; labelable_neutral_stress required
O2 Perfect Deep Drawdown Oracle        -> labelable_full, because drawdown threshold is defined for every labelable step
O3 False-repair Oracle                 -> depends on joined label coverage; appendix-only if incomplete
O4 Positive Preservation Oracle        -> binary_primary; labelable_neutral_stress required
O5 Perfect Utility Oracle              -> labelable_full
O6 Capacity-constrained Utility Oracle -> labelable_full if calendar/exposure gate passes
O7 Delayed Utility Oracle              -> labelable_full under frozen delayed semantics
Action 4 learned-score reference       -> threshold fit is binary, replay/readout includes labelable full denominator and separate binary confusion
```

Fail-closed 规则必须区分分母口径：

```text
如果 O0/O2/O5/O6/O7 的 full-denominator replay 与 EP16 labelable count 不一致 -> fail closed.
如果 O1/O4 primary readout 或 16D learned-reference confusion 与 EP16 binary count 不一致 -> fail closed.
如果 neutral count 与 EP16 不一致，或 neutral rows 无法 reconcile -> 在解释任何 full-denominator utility 前 fail closed.
```

这条规则防止 validation 的 664 vs 505 被误判：当 oracle 明确使用 binary denominator 时，505 是合法口径，不是 row-count mismatch。

### 3.2 允许的输入来源

优先输入：

```text
EP16 16E utility panel
EP16 16D policy/action panel
EP16 16C t0 feature/score panel
EP16 16B label panel
EP16 16A sampling geometry audit
qfq close path only for replay checks and delayed-return materialization
```

EP17 可以计算 oracle action PnL，因为这是新的 diagnostic objective；但必须把所有 forward-return、drawdown、cost、delay 计算写入 lineage manifest，并且不得用于训练、调参或 production claim。

Input lineage must use content hashes and schema checks as the primary identity, not absolute filesystem paths. Older upstream manifests may contain author-machine paths such as `/home/...`; EP17A must not fail solely because the current checkout root is different, as long as content hash, relative artifact role, schema, and row-level keys reconcile.

### 3.3 Secondary readout denominator

可选 secondary denominators：

```text
entry-event candidate denominator
risk_on R-core event denominator
risk_off / E1 event denominator
10B fast-fail gate denominator
```

这些只做 appendix / secondary readout，不进入 EP17 主裁决。EP17 主裁决集中在 EP16 失败发生的 continuation / holding decision-state universe。

## 4. Action Definitions

所有 action 都相对于 blind continue baseline 计算 incremental utility。

### Action 0: Blind Continue

基准动作：

```text
所有 decision states 从 t0 继续持有到 h20 end
exposure = 1.0
```

### Action 1: Full Defend / Exit

如果 oracle 判断应 defend：

```text
从 decision time 开始降到 0 exposure
cash return = 0
transaction cost = configured round-trip defense cost
```

primary cost 与 EP16 对齐：

```text
primary_round_trip_defense_cost_bps = 50
cost_grid_bps = {0, 25, 50, 100}
```

### Action 2: Partial Defend

不是完全退出，而是降 exposure：

```text
q_defend in {0.50, 0.25}
```

收益语义：

```text
policy_return = q_defend * forward_return_remaining - cost_bps * abs(1.0 - q_defend)
```

用途：测试 EP16 是否因为 full avoidance 太激烈而失败。

### Action 3: Delayed Decision

Primary delayed semantics 必须在 EP17A 的 `oracle_action_contract.md` 中冻结为以下口径：

```text
delayed_action_semantics = within_original_h20_switch_v1
```

这表示不在 t0 立即做 defend / continue，而是在原始 h20 block 内：

```text
k in {3, 5, 10}
```

之后再用 oracle 判断剩余区间：

```text
t0 -> t0+k: exposure = 1.0
t0+k -> h20 end: oracle chooses continue or defend
```

delayed action 的 incremental utility 仍与 t0 blind continue full h20 baseline 对比。因为 primary denominator 已经是完整 h20 full-horizon step，`t0+k -> h20 end` 的剩余区间应天然存在。若 replay engine 无法定位 t0+k close 或剩余区间价格路径，说明 price-path materialization 有 bug；O7 必须 fail closed，不能使用 partial tail 填充。

禁止把 primary O7 解释为：

```text
t0+k 后重新开启一个新的 h20 forward window
```

这种 `restart_h20_at_t0_plus_k` 语义如需研究，只能作为单独 appendix 或未来 requirement，不能与 primary delayed oracle 混用。

### Action 4: Learned-score Reference

EP16 的 16D bottom-30% policy 只作为 reference：

```text
defense_bottom_30pct_continuation_score_v1
threshold = 0.457071
```

它不参与 oracle selection，也不得重新调 threshold。

## 5. Oracle Ladder

每个 oracle 都是未来信息上界，不可部署。

### O0. No Oracle Baseline

```text
policy = blind_continue_all
```

用途：提供 continuation baseline。

### O1. Perfect Negative Oracle

定义：

```text
perfectly knows EP16/16B h20 label_class == negative
```

Primary denominator：

```text
binary_primary = positive + negative
neutral rows excluded from primary O1 action-value gate
```

动作：

```text
negative -> defend
positive -> continue
```

Neutral stress readout：

```text
neutral -> continue
```

Neutral stress 必须输出 full labelable denominator six-cell，但不参与 O1 primary binary gate。

用途：测试只要能避开 negative label，是否有正 utility。

### O2. Perfect Deep Drawdown Oracle

定义：

```text
perfectly knows future h20 max drawdown threshold hit
primary threshold = -10%
stress thresholds = {-8%, -12%, -15%, -20%}
```

动作：

```text
deep drawdown -> defend
otherwise -> continue
```

用途：测试 drawdown avoidance 本身是否足够有价值。O2 与 EP16 survival/drawdown-risk score 直接对齐。

### O3. Perfect False-repair / Ineffective-exposure Oracle

定义必须在 EP17A 冻结。优先级：

```text
1. 如果可从既有 09/10/16 lineage join 到 pre-existing false-repair label，则使用该 label。
2. 如果无法无歧义 join，则 O3 降级为 appendix-only or skipped，不得临时创造主标签。
```

动作：

```text
false_repair_or_ineffective_exposure -> defend
otherwise -> continue
```

用途：测试 false-repair 作为 action target 是否有理论价值。

O3 仅为 explanatory oracle，不是 primary ladder gate。若 O3 因 label lineage 或 join coverage 不足被 skip，不阻断也不改变 O1/O2/O4/O5 的主裁决；报告中必须显式标记 `O3_status = skipped_nonblocking` 或 `O3_status = appendix_only`。

### O4. Perfect Positive Preservation Oracle

定义：

```text
perfectly knows future h20 label_class == positive
or high-upside positive under frozen payoff threshold
```

Primary denominator：

```text
binary_primary = positive + negative
neutral rows excluded from primary O4 action-value gate
```

primary action：

```text
positive -> continue
negative -> defend
```

Neutral stress readout：

```text
neutral -> defend
```

Neutral stress 用于量化"把非 positive 都防掉"的成本，但不参与 O4 primary binary gate。

stress：

```text
high_upside_positive thresholds = top 30%, top 20%, top 10% realized h20 payoff within train only
```

所有 payoff 分位阈值一律 train-frozen，并以绝对 payoff cutoff 记录在 manifest。Robustness 与 validation 必须套用同一组 train-frozen absolute thresholds，不能使用各 split 自身分位重算。这样做是为了让 O4 high-upside stress、top-k sensitivity 和 matched-base readout 在 split 间可比。

用途：衡量 EP16 positive sacrifice 的理论上界。如果 O4 远强于 O1/O2，说明主要价值来自保留右尾，而不是避险。

### O5. Perfect Utility Oracle

定义：

```text
perfectly knows net utility of continue vs defend under frozen action semantics and cost
```

动作：

```text
if utility(defend_action) > utility(continue):
    defend
else:
    continue
```

O5 在 `labelable_full` 全口径上运行，neutral rows 不得被预先改写成 positive 或 negative。Neutral 的动作也走同一条 rule：

```text
neutral row:
    choose defend only if utility(defend) > utility(continue)
    otherwise continue
```

由于 defend neutral 在 50bps 成本下通常不划算，O5 的 six-cell decomposition 必须单列 `defended_neutral` 与 `continued_neutral`，防止 neutral cost 噪音污染 positive/negative 归因。

用途：当前 action space 的理论上界。O5 是 EP17 的核心 oracle。

### O6. Capacity-constrained Utility Oracle

在 O5 基础上加入组合限制：

```text
max active positions
max gross exposure
max per-name exposure
max turnover
max board / sector concentration
```

O6 只有在 calendar/exposure reconstruction gate 通过后才可作为 primary capacity readout。若组合日历或 exposure reconstruction 不可审计，O6 降级为 appendix，不阻断 O1-O5 裁决。

用途：测试理论 value 在组合容量下是否仍存在。

### O7. Delayed Utility Oracle

在 `t0+k` 后使用 perfect utility oracle：

```text
k in {3, 5, 10}
```

用途：测试延迟决策是否显著提升 action value。若 delayed oracle 明显强于 t0 oracle，说明 t0 信息不足，后续应研究 staged trial / later observed-state decision。

## 6. 统一收益 / 风险计算

所有 oracle 使用同一 replay engine。

### 6.1 Per-state PnL

对每个 decision state：

```text
blind_continue_pnl = forward_return_h20

continue_pnl = q_continue * forward_return_remaining - holding_cost
defend_pnl   = q_defend   * forward_return_remaining - transaction_cost

incremental_pnl = oracle_policy_pnl - blind_continue_pnl
```

默认：

```text
q_continue = 1.0
q_full_defend = 0.0
q_partial_defend in {0.50, 0.25}
holding_cost = 0 unless explicitly configured
cash_return = 0
```

### 6.2 Main metrics

每个 oracle/action/cost/split 输出：

```text
labelable_step_n
defended_step_n
continued_step_n
mean incremental return
median incremental return
trimmed mean incremental return
winsorized mean incremental return
sum incremental return
EV per exposure-day
MFE retained
MAE avoided
turnover
transaction cost
exposure-days removed
defended positive opportunity cost
defended negative gain
defended neutral gain
continued negative leakage
continued positive retained
net full-denominator utility
```

### 6.3 Six-cell decomposition

必须继承 EP16 的六格归因：

```text
defended_positive
defended_negative
defended_neutral
continued_positive
continued_negative
continued_neutral
```

EP17 不能只看 negative avoided，因为 EP16 已证明只看 avoided loss 会误判。所有 oracle positive result 都必须同时解释：

```text
positive sacrifice 是否下降?
negative avoided 是否上升?
neutral rows 是否贡献或拖累 utility?
continued negative leakage 是否仍然很重?
```

## 7. Robustness 处理

### 7.1 主裁决 split

Primary confirmatory split 仍为 `robustness`。`train` 用于 lineage、calibration 和 explanatory readout；`validation` 是 stress readout，不参与 oracle selection 或 threshold tuning。

### 7.2 不使用 raw mean EV 作为唯一主指标

Big winner 分布肥尾，因此每个 oracle 都要输出：

```text
raw mean
trimmed mean
winsorized mean
median
top-k removal sensitivity
cluster bootstrap CI
```

### 7.3 Top-k removal

对每个 oracle：

```text
remove top 1 instrument contribution
remove top 3 instrument contributions
remove top 5 instrument contributions
remove top 1% episode contributions
```

如果 oracle value 主要来自极少数名字，标记：

```text
tail_concentrated_upper_bound = true
```

### 7.4 Bootstrap

允许的 bootstrap：

```text
cluster bootstrap by episode_cluster_id
cluster bootstrap by instrument
block bootstrap by calendar month / quarter
```

禁止按 event row 独立 bootstrap。

### 7.5 Materiality gate

EP17A 必须在 config 中冻结 materiality floors。默认建议：

```text
primary_cost_bps = 50
robustness_mean_incremental_floor = 0.0025
robustness_trimmed_mean_floor = 0.0000
cluster_bootstrap_ci_low_floor = 0.0000
topk_removed_mean_floor = 0.0000
```

这些 floor 只能在 train/config 阶段声明，不能根据 robustness 或 validation 调整。

Gate 判定优先级必须固定：

```text
Primary support gates:
  1. robustness_trimmed_mean_incremental > robustness_trimmed_mean_floor
  2. robustness_cluster_bootstrap_ci_low > cluster_bootstrap_ci_low_floor
  3. robustness_topk_removed_mean > topk_removed_mean_floor

Materiality confirmation:
  4. robustness_raw_mean_incremental >= robustness_mean_incremental_floor
```

Raw mean 不能单独触发任何 positive decision。若 raw mean 通过但 trimmed mean、bootstrap CI 或 top-k removal 不通过，只能解释为 tail-concentrated diagnostic readout。若 trimmed/CI/top-k 通过但 raw mean 未达到 25bps floor，最多标记为 weak positive upper-bound，不得直接触发 `oracle_payoff_state_research_allowed`。

## 8. Matched Base

不能只和 global baseline 比较。每个 oracle 还要按 matched base 对照：

```text
same split
same calendar block
same regime if PIT available
same board / market bucket
same known_failed_context bucket
same event/denominator source if secondary denominator is used
```

输出：

```text
global baseline comparison
time-block matched comparison
board / market matched comparison
known-failed-context matched comparison
regime-matched provisional comparison
```

Regime 仍需要 PIT audit；在 PIT audit 未通过前，regime readout 只能标记为 `provisional`。

## 9. Diagnostic Decision Tree

EP17 的主要产出不是某个 oracle 数值，而是诊断分流。

### Case A. Perfect Utility Oracle 也没有明显正 value

结论：

```text
当前 continuation / holding decision-state universe 缺少可交易 action value
```

后续方向：

```text
回到 event source / entry source
不要继续 continuation model
```

### Case B. Negative Oracle 有效，但 learned survival score 无效

结论：

```text
label 有 action value，但现有 feature / model 不够
```

后续方向：

```text
补充风险-state feature
测试 delayed observed-state
重新定义 risk representation
```

### Case C. Positive Oracle 远强于 Negative Oracle

结论：

```text
right-tail preservation 是主要价值
防守型模型天然危险
```

后续方向：

```text
不要用 risk score 直接 exit
改成 partial exposure reduction 或 position-size adjustment
独立研究 upside-preservation / payoff magnitude state
```

### Case D. Utility Oracle 强，但 Payoff Oracle / learned payoff weak

结论：

```text
可交易 action value 存在，但当前 payoff-state representation 不足
```

后续方向候选：

```text
order-flow / liquidity impulse
industry diffusion
news / catalyst
limit-up chain
leader-follower structure
cross-sectional sponsorship
```

### Case E. Delayed Oracle 明显强

结论：

```text
t0 不够，t+k 后更可判别
```

后续方向：

```text
t0 small trial
t+3 / t+5 / t+10 upgrade or defend
```

### Case F. Unconstrained Oracle 强，capacity-constrained Oracle 弱

结论：

```text
理论信号存在，但组合容量 / turnover / execution 吃掉价值
```

后续方向：

```text
portfolio-level selection
capital allocation
capacity-aware sizing
```

## 10. Gate / Decision Labels

EP17 不输出 research-entry 或 deployment authorization。它只能输出以下 decision。

### `oracle_no_action_value_in_current_space`

条件：

```text
Perfect Utility Oracle net utility 不显著优于 baseline
或 top-k removal 后消失
或 robustness bootstrap CI 不支持正 incremental utility
```

含义：

```text
当前 continuation / holding state 空间不值得继续建模
```

### `oracle_value_exists_feature_gap`

条件：

```text
Oracle value 明显存在
但 learned score / existing features 无法接近
```

含义：

```text
需要新 feature / 新 payoff-state representation
```

### `oracle_risk_signal_only_no_payoff_value`

条件：

```text
Negative / drawdown oracle 有效
但 positive sacrifice 太大
或 Positive Preservation Oracle 明显主导 Negative Oracle
```

含义：

```text
risk score 只能作为 sizing / risk budget 候选，不能作为 full exit
```

### `oracle_delayed_decision_supported`

条件：

```text
Delayed Oracle 明显优于 t0 Oracle
且 top-k / bootstrap / matched base 不推翻
```

含义：

```text
未来系统应研究 small trial + later observed-state decision
```

### `oracle_execution_capacity_blocked`

条件：

```text
unconstrained oracle strong
capacity / cost constrained oracle weak
```

含义：

```text
主要瓶颈在组合和执行层
```

### `oracle_payoff_state_research_allowed`

条件：

```text
Utility Oracle strong
Positive / payoff-oriented oracle has robust value
top-k sensitivity pass
matched base pass
capacity/cost stress not fatal
```

其中 `Utility Oracle strong` 必须同时满足 §7.5 的 primary support gates 和 materiality confirmation。Raw mean 单独为正不够；top-k removal 或 bootstrap CI 任一不通过，都不能授权 payoff-state research。

含义：

```text
可以进入新的 payoff-state representation research
```

### `oracle_lineage_or_denominator_blocked`

条件：

```text
EP16 denominator 无法复验
row count 与 EP16 不一致
qfq replay 不可审计
delayed/capacity materialization 缺关键字段且无法安全降级
```

含义：

```text
先修数据 / denominator / replay contract，不得解释 oracle value
```

## 11. 推荐执行顺序

### EP17A: Denominator and Replay Contract

目标：

```text
冻结 decision-state denominator
冻结 action definitions
冻结 cost / execution assumptions
确认 non-overlap sampling
确认 split / cluster / instrument keys
确认 qfq replay and delayed materialization coverage
```

输出：

```text
oracle_denominator_contract.md
oracle_action_contract.md
oracle_replay_engine_manifest.json
tables/denominator_lineage_audit.csv
tables/action_semantics_audit.csv
tables/ep16_replay_sanity_check.csv
```

Acceptance checks:

```text
1. denominator_reconciliation reproduces EP16 labelable/binary/neutral counts for train/robustness/validation.
2. learned-score reference replay reproduces EP16 16D threshold = 0.457071 and binary confusion counts.
3. utility replay reproduces EP16 16E primary 50bps robustness full-denominator mean incremental return = -0.005529 within tolerance.
4. drawdown replay reproduces EP16 16E robustness defended_negative_drawdown_avoided_mean = 0.164024 within tolerance for the 16D primary defended-negative set.
5. O2 drawdown oracle uses the same qfq drawdown calculation as this sanity replay. O2's defended set may differ from 16D, so its mean need not equal 0.164024, but the underlying row-level drawdown field must reconcile.
6. input_artifact_manifest uses content hash + schema + role + row-key reconciliation as primary lineage, not absolute path equality.
```

If any sanity check fails, EP17A must return `oracle_lineage_or_denominator_blocked` and no oracle value may be interpreted.

裁决：

```text
EP17A_oracle_replay_contract_ready
or
oracle_lineage_or_denominator_blocked
```

### EP17B: Oracle Ladder Replay

目标：

```text
跑 O0-O5 primary oracle ladder
跑 partial-defend action variants
输出 ladder summary + six-cell decomposition
```

输出：

```text
tables/oracle_ladder_summary.csv
tables/oracle_six_cell_decomposition.csv
tables/oracle_action_intensity_frontier.csv
figures/oracle_ladder_net_utility.png
figures/positive_sacrifice_vs_negative_avoidance.png
```

裁决：

```text
EP17B_oracle_ladder_ready_for_robustness
or
oracle_no_action_value_in_current_space
```

### EP17C: Robustness Stress

目标：

```text
top-k removal
cluster bootstrap
time/block matched base
regime provisional readout
capacity-constrained oracle if reconstruction gate passes
delayed oracle curve
```

输出：

```text
tables/oracle_topk_sensitivity.csv
tables/oracle_bootstrap_ci.csv
tables/oracle_matched_base.csv
tables/oracle_delay_curve.csv
tables/oracle_capacity_constraint.csv
figures/delayed_oracle_curve.png
figures/capacity_constrained_oracle_curve.png
figures/oracle_topk_sensitivity.png
```

裁决：

```text
EP17C_oracle_robustness_ready_for_diagnosis
or one of:
    oracle_no_action_value_in_current_space
    oracle_execution_capacity_blocked
```

### EP17D: Diagnosis Report

目标：

```text
根据 decision tree 判断问题方向
明确是否进入 feature redesign / event redesign / delayed observed-state diagnostic / payoff-state research
```

输出：

```text
reports/ep17_oracle_action_value_diagnostic_report.md
tables/oracle_diagnosis_decision_tree.csv
```

最终裁决只能来自 §10 的 decision labels。

## 12. Expected Output Artifacts

建议目录结构：

```text
outputs/
  publishable/
    reports/
      ep17_oracle_action_value_diagnostic_report.md
    tables/
      denominator_lineage_audit.csv
      action_semantics_audit.csv
      oracle_ladder_summary.csv
      oracle_six_cell_decomposition.csv
      oracle_action_intensity_frontier.csv
      oracle_topk_sensitivity.csv
      oracle_bootstrap_ci.csv
      oracle_matched_base.csv
      oracle_delay_curve.csv
      oracle_capacity_constraint.csv
      oracle_diagnosis_decision_tree.csv
    figures/
      oracle_ladder_net_utility.png
      positive_sacrifice_vs_negative_avoidance.png
      delayed_oracle_curve.png
      capacity_constrained_oracle_curve.png
      oracle_topk_sensitivity.png
    manifests/
      oracle_replay_engine_manifest.json
      input_artifact_manifest.json
```

Figure requirements:

```text
positive_sacrifice_vs_negative_avoidance.png must be split-faceted:
    train / robustness / validation

The robustness panel remains the primary confirmatory visual, but train and validation panels are required to expose overfit and stress behavior.
```

Root-level optional docs:

```text
oracle_denominator_contract.md
oracle_action_contract.md
```

## 13. Search Accounting

EP17 必须记录：

```text
no_model_training = true
no_model_refit = true
no_survival_threshold_tuning = true
no_validation_selection = true
no_robustness_tuning = true
no_feature_selection = true
no_payoff_label_redesign = true
no_entry_policy_authorized = true
no_exit_policy_authorized = true
no_holding_policy_authorized = true
no_portfolio_backtest_authorized = true
no_model_deployment_authorized = true
no_production_signal_authorized = true
no_live_trading_authorized = true
```

任何 oracle threshold 或 payoff bucket 必须在 train/config 阶段冻结。Validation 只能作为 stress readout；robustness 是 confirmatory gate，不可用于 tuning。

## 14. 与当前 topic 结论的关系

`research_conclusions.md` 给出的当前总裁决是：

```text
deployable_strategy_found = false
production_signal_authorized = false
continuation_as_action_mainline_closed = true
main_unsolved_problem = OOS payoff/utility ranking, not recall
```

EP17 正是针对这个 unresolved problem 的 upper-bound diagnostic。它不推翻 01-16 的失败结论；它只判断：

```text
失败是因为 action space 本身没有价值，
还是因为当前 feature / label / action / execution 没能提取价值。
```

## 15. 最终总结

EP17 的核心不是再证明某个模型，而是回答：

```text
当前 decision/action space 到底有没有可被利用的 action value?
```

如果答案是没有，后续应该回到 event source / strategy space。

如果答案是有，但 learned model 失败，才值得继续做 feature / payoff-state representation。

如果答案只在 delayed oracle 中出现，系统应转向 staged trial / later upgrade。

如果答案被 capacity 吃掉，问题在 portfolio execution，而不是标签或模型。

一句话：

```text
EP17 用 oracle upper bound 拆解 EP16 的失败：
到底是没有可交易空间，还是有空间但当前 feature / label / action / execution 没有把它提取出来。
```
