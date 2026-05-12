# EP4 Requirement 02：Evidence Family Discovery V1

> Requirement id: `ep4_r02_evidence_family_discovery_v1`
> Status: research requirement draft
> Scope: 从全市场 action-time 样本中寻找 3 到 5 个互补 evidence family，为后续 evidence accumulation / 30 日建仓 / 1R 风险预算分配提供冻结候选；本 requirement 不实现最终仓位映射、不证明完整交易策略。
> Upstream discussion: `ep4/discussion2.md`
> Upstream evidence: `ep4/outputs/r01_high_recall_probe_fail_fast_v3_post30_profile_seed/reports/r01_final_report.md`
> Date: 2026-05-12

---

## 1. Purpose

R01 V3 说明：`post30 profile` 对 big winner 有很高覆盖率，但不能直接当作完整 entry trigger。下一步不应继续寻找单一万能入口，而应先回答一个更小的问题：

```text
在全市场可交易 action-time 样本中，
是否存在 3 到 5 个互补 evidence family，
它们分别提供 momentum、structure、survival、industry / market 等不同证据，
并且在 train split 中表现出可复现的 forward lift、EV_R 和执行可行性？
```

R02 V1 的目标不是建仓，不是加仓，不是组合回测，而是发现并冻结一批候选 family，供后续 evidence accumulation 实验使用。

V1 主选择目标固定为：

```yaml
primary_selection_label_id: big_winner_forward
secondary_no_harm_label_ids:
  - continuation_h20
  - continuation_h60
  - failed_seed_forward
  - executable_entry_available
```

所有未显式写 label id 的 `LR`、`P(winner | signal)`、`P(signal | winner)` 和 `P(signal | non_winner)`，默认都指 `primary_selection_label_id = big_winner_forward`。

`primary_selection_label_id = big_winner_forward` 用于选择右尾 evidence；`EV_R` 使用 H20 diagnostic execution，只用于短期执行成本、买入可行性和 no-harm 质量控制。R02 V1 不允许用 H20 `EV_R` 替代 h120 primary label 做 right-tail family selection，也不允许忽略 H20 `EV_R` 的执行质量风险。

---

## 2. Phase Boundary

本 requirement 只允许做 family discovery 和 family validation。

不允许：

- 训练最终 entry / add / exit 模型；
- 根据 validation / robustness 结果反向修改 family 公式或阈值；
- 把 winner-anchored coverage 当作 prior；
- 直接用 family posterior 生成仓位；
- 设计 1R 风险预算映射表；
- 做 staged add、trailing stop、profit giveback 或完整 portfolio simulation；
- 宣称任何 family 是独立可交易策略。

允许：

- 在 train split 内搜索 primitive evidence；
- 在 train split 内聚类并冻结 family；
- 在 validation / robustness 上只评估冻结 family；
- 报告 family 的 coverage、precision、LR、EV_R、density、overlap 和 execution diagnostics；
- 把 winner-anchored coverage 作为 recall diagnostic，但不得作为风险预算 prior。

---

## 3. Core Research Question

R02 V1 只回答三件事：

```text
Q1. 哪些 primitive evidence 在 action-time 样本上有稳定 forward lift？
Q2. 哪些 primitive 其实是同一类证据，应该合并为同一个 family？
Q3. 冻结后的 3 到 5 个 family 是否互补，是否值得进入下一阶段 evidence accumulation？
```

如果 Q1 / Q2 / Q3 中任意一个不成立，不能进入后续 30 日建仓实验。

---

## 4. Sampling Grain

family prior 必须来自 action-time 样本，而不是 big-winner 回看窗口。

主粒度：

```text
instrument_id
trade_date
primitive_id
family_candidate_id
```

episode 辅助粒度：

```text
seed_episode_id
family_candidate_id
family_trigger_date
```

每条 event 必须满足：

```text
event_t = primitive or family 在 trade_date 当日触发
label = event_t 后固定 horizon 内是否形成目标状态
```

禁止用下面的分母估 prior：

```text
big_winner reference_date 后 T+0..T+30 内出现过 signal 的样本
```

正确分母是：

```text
train split 中所有 eligible stock-days / action-time rows
```

### 4.1 Action-Time Universe and Eligibility

R02 V1 的主分母必须沿用 R01 V3 的 PIT universe / tradability 口径，不允许实现者自行扩大或缩小 universe。

主 action-time row 必须同时满足：

```text
instrument_id 在 data/universe/pit_mcap500_mainboard_daily.csv 的 PIT universe 中；
trade_date 在对应 split 的有效日期范围内；
Qlib PIT instrument provider 覆盖该 instrument_id / trade_date；
当日存在有效 OHLCV / amount 数据；
当日不是 suspended_or_dirty_bar；
primitive 所需的最大 lookback window 在 trade_date 之前有足够历史；
用于 forward label 的 horizon 有完整后验窗口，否则标记 incomplete_forward_window，不进入 label 分母。
```

每个 split / label 必须记录 effective label boundary：

```text
label_horizon_days:
  continuation_h20: 20
  continuation_h60: 60
  big_winner_forward: 120
  failed_seed_forward: 10
  executable_entry_available: 1

effective_label_end(label, split) =
  last split trade_date whose next_open_after(trade_date)
  has a complete forward window for that label
```

`trade_date > effective_label_end(label, split)` 的 action-time row 必须保留在 `r02_action_time_panel.parquet`，但对该 label 标记为 `incomplete_forward_window`，不得进入该 label 的 LR / EV_R / precision 分母。

`next_open_after(trade_date)` 不可执行的 action-time row 必须保留，且按 label 分别处理：

```text
for executable_entry_available:
  enter denominator as executable_entry_available = false
  entry_execution_status = entry_execution_unavailable

for continuation_h20 / continuation_h60 / big_winner_forward / failed_seed_forward:
  mark entry_execution_status = entry_execution_unavailable
  exclude from outcome-label denominator because entry_price_t cannot be reproduced
```

这样 buyability / execution feasibility 不会因为排除不可执行样本而被高估。

instrument-year 可用于 density / concentration 分母，口径沿用 R01 V3：

```text
eligible_instrument_year =
  split 内该 instrument 至少有 120 个 eligible_stock_days
```

V1 主搜索不允许加入价格状态 broad pre-filter，例如：

```text
必须 60d 新高；
必须先通过 EP2 launch detector；
必须满足 post30 profile 的任一条件；
```

这些都只能作为 primitive / family 自身被评估，不能先改变 non-winner 分母。否则 `P(signal | non_winner)` 和 LR 会失去可比性。

---

## 5. Label Definitions

family discovery 需要多层 label，避免只优化最终 big winner。

所有 forward label 都以 event_t 的收盘后可观察状态为 anchor。若 label horizon 不完整，必须标记为 `incomplete_forward_window`，不得进入该 label 的分母。

统一价格 anchor：

```text
signal_date = trade_date
entry_price_t = next_open_after(signal_date)
forward_close_peak_hN = max(close over next N trading days after entry)
```

V1 固定以下 label：

| label | formula | role |
|:--|:--|:--|
| `continuation_h20` | `close_h20 / entry_price_t - 1 >= 0.10` and `min(close_h1:h20) / entry_price_t - 1 > -0.06` | 短期延续 |
| `continuation_h60` | `close_h60 / entry_price_t - 1 >= 0.20` and `forward_close_peak_h60 / entry_price_t - 1 >= 0.30` | 中期延续 |
| `big_winner_forward` | `forward_close_peak_h120 / entry_price_t - 1 >= 0.50` | 沿用 R01 V3 的 `50h120` 右尾目标，但以 action-time event_t 为 anchor |
| `failed_seed_forward` | `min(close_h1:h10) / entry_price_t - 1 <= -0.06` | 固定短期失败标签，用于 family 失败率和 EV_R 解释 |
| `executable_entry_available` | T+1 open 可执行，且用 R02 V1 generic lookback-low stop 口径得到 `2% <= initial_risk_pct <= 12%` | 是否存在统一 diagnostic probe entry |

每个 label 必须只使用 event_t 之后的数据。event_t 当日可观察字段必须保持 PIT。

label 语义必须明确区分：

```text
failed_seed_forward = H10 early failure label；
continuation_h20 = H20 continuation with no -6% interim close drawdown；
continuation_h60 = H60 medium continuation，不内置 H10 fail-fast 判定；
```

这三个 label 会天然重叠但不等价。final report 必须输出 event-level confusion matrix，至少覆盖：

```text
continuation_h20 x continuation_h60
continuation_h20 x failed_seed_forward
continuation_h60 x failed_seed_forward
```

`winner` / `non_winner` 在 LR 中按具体 label 定义：

```text
winner(label) = label_positive 且 forward window complete
non_winner(label) = label_negative 且 forward window complete
```

不能把 canonical big-winner reference panel 中的 winner 身份直接投射到所有 stock-day。

### 5.1 Diagnostic Execution for EV_R

R02 V1 的 `EV_R` 只用于横向比较 family，不代表最终策略。

统一 diagnostic execution：

```text
signal_date = trade_date
entry_execution_date = next tradable day after signal_date
entry_price = next tradable day open
initial_structural_stop = closest valid stop below entry among:
  signal_day_low
  prior_10d_low
  prior_20d_low
initial_risk_pct = (entry_price - initial_structural_stop) / entry_price
eligible if 2% <= initial_risk_pct <= 12%
terminal_horizon = H20
fail_fast_window = 10 trading days
all executable events use the same deterministic fail-fast + H20 terminal rule:
  if any close within H1..H10 <= entry_price * (1 - 0.06):
    terminal_exit_date = first such fail-fast date
  else:
    terminal_exit_date = entry_execution_date + 20 trading days
unit_return_R = after_cost_return_pct / initial_risk_pct
```

如果 T+1 open 不可买、缺少有效 stop、或 `initial_risk_pct` 不在 `[2%, 12%]`，该 event 必须保留在 panel 中并标记为 execution-ineligible，不得静默删除。

`EV_R` 使用 `unit_return_R` 计算，不乘 R01 的 `0.25R` probe budget。这样不同 family 的 payoff quality 可以直接比较；后续是否给 0.10R / 0.25R / 1.00R 风险预算不属于 R02 V1。

This is intentionally an R01-style diagnostic execution, not neutral H20 gross-return measurement. It must apply symmetrically to all executable events, not only to events labeled `failed_seed_forward`.

stop candidates 的精确定义：

```text
signal_day_low = low[signal_date]
prior_10d_low = min(low over the 10 trading days before signal_date)
prior_20d_low = min(low over the 20 trading days before signal_date)

valid stop below entry =
  stop_price < entry_price
  and 0.02 <= (entry_price - stop_price) / entry_price <= 0.12

closest valid stop below entry =
  max(stop_price among valid stop candidates)
```

R02 V1 deliberately uses generic lookback-low stop candidates so every primitive / combo can be evaluated under the same action-time risk unit. This differs from R01 V3's seed-specific structural stop candidates. Therefore R02 `unit_return_R` / `EV_R` are comparable across R02 families, but are not numerically comparable to R01 V3 `return_R`.

`after_cost_return_pct` 必须沿用 R01 V3 的 execution cost source：

```text
cost_model_source = ep2/engineering_baseline/config.yaml
after_cost_return_pct =
  exit_price / entry_price - 1 - round_trip_cost_pct
```

如果 cost config 缺失或字段不可复现，validator 必须作为 contract failure 退出。

---

## 6. Primitive Search Space

第一阶段先搜索 primitive，不直接搜索最终 family。

候选 primitive 至少覆盖以下证据源：

| group | examples | intended role |
|:--|:--|:--|
| price / momentum | close near high5 / high20 / high60, breakout | 状态确认 |
| volume / money | vol_ratio3 / 10 / 20, amount expansion | 资金参与 |
| relative strength | rps5 / rps20 / rps60, industry-relative rank | 横截面强度 |
| pullback / structure | EMA hold, pivot hold, pullback depth | 低风险结构 |
| survival / no-failure | H5 / H10 未破位、未触发 stop | 负证据消失 |
| volatility state | ATR contraction / expansion | 整理后启动 |
| industry / market | industry breadth, market regime, index risk | beta / 主题环境 |
| distribution absence | no high-volume down day, no repeated failed breakout | 未派发 |

注意：`survival / no-failure` 和 `distribution absence` 作为 primitive 时，只能使用 `trade_date` 之前已经发生的信息。例如：

```text
past_h10_no_close_below_prior_stop
past_h20_no_high_volume_down_day
past_h10_no_failed_breakout
```

不能把 event_t 之后 H5 / H10 是否失败写成 primitive；那是 label，不是 signal。

阈值只能使用粗网格或 train split 分位数。禁止在 validation 上微调阈值。

示例粗网格：

```text
rps: 50 / 60 / 70 / 80
vol_ratio: 1.1 / 1.2 / 1.5 / 2.0
near_high: 0% / -2% / -5%
pullback_depth: 3% / 5% / 8% / 12%
survival_horizon: 5 / 10 / 20 trading days
```

### 6.1 Combination Control

R02 V1 主搜索允许有限组合，但必须把自由度写死在 config 中，不能由 validation / robustness 结果反向扩大。

V3 post30 seed 是例外：它是 `mandatory_composite_baseline`，不是 primary primitive search 的候选，不参与 single-primitive restriction 的 violation 统计。

Primary search candidate 可以是：

```text
single primitive
or approved_2_primitive_and
or mandatory_composite_baseline
```

`approved_2_primitive_and` 必须满足：

```text
最多 2 个 primitive；
两个 primitive 必须来自不同 group；
不能把同一 raw feature 的两个阈值组合在一起；
两个 primitive 都必须先通过 single-primitive early rejection；
组合自身也必须通过 combo early rejection；
不能用 validation / robustness 结果选择组合；
不能构造 3+ primitive 组合；
每个 group-pair 最多保留 train split ranked top 20 个组合；
max_total_approved_combos = 600；
所有组合必须进入同一 cluster / redundancy audit；
```

combo ranking 固定使用 train split score：

```text
combo_rank_score =
  max(0, log(primary_LR))
  * max(0, EV_R + 0.05)
  * sqrt(min(stock_day_density, 0.02) / 0.02)
```

排序 tie-breaker 必须固定为：

```text
primary_LR desc
EV_R desc
stock_day_density desc
combo_id asc
```

`approved_2_primitive_and` 可以成为 family representative，但必须额外报告：

```text
component_primitive_ids
component_group_ids
component_single_LR
component_single_EV_R
combo_incremental_LR_vs_best_component
combo_incremental_EV_R_vs_best_component
combo_density_vs_components
```

combo 进入 family representative selection 的额外门槛：

```text
combo_incremental_LR_vs_best_component >= 1.05
or combo_incremental_EV_R_vs_best_component > 0.00
```

不满足边际增量门槛的 combo 只能进入 audit，不得成为 family representative。

这样做是在适度增加搜索自由度的同时，避免 primitive × 阈值 × label × split 的组合爆炸。

---

## 7. Primitive Metrics

每个 primitive 必须在 train split 输出以下指标：

```text
trigger_count
stock_day_density
instrument_year_concentration
P(signal | winner)
P(signal | non_winner)
P(winner | signal)
LR = P(signal | winner) / P(signal | non_winner)
primary_LR_ci90_lower
primary_LR_ci90_upper
log_lift = log(LR)
EV_R
avg_win_R
avg_loss_R
failed_seed_rate
entry_buyability_rate
initial_risk_pct_distribution
delay_sensitivity
```

`instrument_year_concentration` 是 audit / tie-breaker，不是绝对 reject gate。右尾结构天然会集中在强势年份和强势股票；R02 V1 不允许因为绝对集中度高就自动删除 momentum family。

集中度只能用于：

```text
同一 cluster 内代表公式的相对排序；
final report 的风险提示；
判断是否需要在 R03 里做 portfolio cap；
```

`P(signal | winner)` 只能解释 recall。进入 family discovery 排序时，至少同时看：

```text
LR
P(winner | signal)
EV_R
density
risk / buyability diagnostics
```

`primary_LR_ci90_lower` / `primary_LR_ci90_upper` 必须使用 train split instrument-year block bootstrap 计算：

```text
bootstrap_unit = instrument_year
bootstrap_replicates = 200
bootstrap_random_seed = 20260512
confidence = 90%
```

---

## 8. Early Rejection Rules

primitive 必须先通过 train split 的最低质量过滤。

建议 fail-closed 条件：

```text
min_train_trigger_count_single = 200
min_train_trigger_count_combo = 120
min_train_primary_positive_count_single = 20
min_train_primary_positive_count_combo = 15
max_train_stock_day_density_single = 0.10
max_train_stock_day_density_combo = 0.06
min_train_primary_LR = 1.00
min_train_primary_LR_ci90_lower = 1.00
min_train_EV_R = -0.05
min_train_entry_buyability_rate = 0.30
max_train_risk_distance_ineligible_rate = 0.70
instrument / year concentration 过高 -> audit-only concentration warning, not direct reject
```

这些阈值必须写入 `ep4/configs/r02_evidence_family_discovery_v1.yaml`，validator 必须检查实际运行使用的阈值与 config 一致。实现可以在 train split 中额外报告更严格阈值的 sensitivity，但不能用 sensitivity 改变 V1 primary family pool。

`single primitive` 必须使用 `*_single` 阈值；`approved_2_primitive_and` 必须使用 `*_combo` 阈值。combo 的 component primitive 通过 single threshold 只是进入组合构造的前置条件，combo 自身若未通过 combo threshold，只能进入 audit，不能进入 family representative selection。

---

## 9. Family Clustering

family 不是人工命名后直接成立，必须由 primitive 的重叠和增量证据支持。

需要计算：

```text
same_day_overlap
within_5d_overlap
binary_signal_correlation
jaccard_overlap
winner_conditional_overlap
non_winner_conditional_overlap
failed_episode_overlap
shared_raw_feature_penalty
incremental_LR_after_selected_family
incremental_EV_R_after_selected_family
```

V1 固定 `incremental_LR_after_selected_family` 使用条件 LR 口径：

```text
selected_family_set = already selected representative families
active_selected = any selected family fires on the same instrument-date

incremental_LR(candidate | selected) =
  P(candidate_signal | winner and active_selected)
  / P(candidate_signal | non_winner and active_selected)
```

如果 `active_selected` 子样本不足，必须输出 `insufficient_conditional_sample`，不得用全样本 LR 代替。

`incremental_EV_R_after_selected_family` 使用同一 `active_selected` 子样本，比较：

```text
EV_R(active_selected AND candidate)
minus
EV_R(active_selected AND NOT candidate)
```

如果两个 primitive：

```text
触发高度重叠；
winner 样本和 non-winner 样本中都高度重叠；
叠加后没有明显 incremental_LR 或 incremental_EV_R；
共享同一类 raw feature；
```

则必须合并为同一个 family，不允许作为两个独立 family 进入后续风险预算。

V1 固定 clustering / merge 规则：

```text
same_day_jaccard >= 0.70
or within_5d_overlap >= 0.85
or (
  shared_raw_feature_penalty = true
  and incremental_LR_after_selected_family < 1.05
  and incremental_EV_R_after_selected_family <= 0.02
)
```

若任一条件成立，两个 primitive 必须进入同一 cluster。若 conditional sample 不足导致 incremental metrics 不可用，则只能按 overlap / shared raw feature 合并，不能用缺失的 incremental metric 支持拆分。

---

## 10. Family Selection

R02 V1 最终只能冻结 3 到 5 个 family。

第一版候选方向至少包含 6 个，避免 cluster 合并后只剩 1 到 2 类证据：

```text
F1: post30 profile / momentum state
F2: pullback / structure hold
F3: no-failure survival
F4: industry / market support
F5: volatility contraction / expansion
F6: acceleration
F7: distribution absence
```

其中 V3 post30 seed 必须以原始冻结公式作为 mandatory composite baseline 进入对比：

```text
close_near_high5_gt_0pct
AND vol_ratio10_gt_1_2
AND vol_ratio3_gt_1_2
AND rps5_gt_60
```

V3 seed baseline 是 allowed composite exception：

```text
它必须作为 mandatory_composite_baseline 报告；
它可以进入 R03 family pool only if 它通过 validation / robustness / execution / R03 decision gates；
它不需要满足 approved_2_primitive_and 的 2-primitive component constraint；
如果同一 cluster 内已有更稳定的 family representative，则 V3 seed baseline 只能保留为 baseline comparison；
V3 seed baseline 不能成为 go_to_r03_evidence_accumulation 的唯一通过依据；
V3 seed baseline 不必通过 §11 year stability gate 才能作为 mandatory baseline 报告；
如果 V3 seed baseline 申请进入 R03 pool，则必须通过 §11 year stability gate 和所有 R03 gates；
```

如果 train split 中相邻粗阈值版本更稳定，报告可以推荐为 later V2 search-space candidate；V1 的 primary comparison 必须始终保留原 V3 seed baseline。V3 seed baseline 不能因 primary search 的组合约束被 validator 判为违规。

每个 family 只能保留一个代表公式。代表公式应满足：

```text
条件数量少；
阈值粗；
train 内稳定；
validation 不再修改；
与其他 family 的 overlap 可解释；
有明确状态含义。
```

---

## 11. Split Protocol

train split：

```text
使用 year-bootstrap / year-slice stability，不做可选 train_inner_discovery 日期切分；
搜索 primitive；
过滤 primitive；
聚类 family；
选择 family representative；
冻结 family formula / thresholds / cluster assignment；
冻结所有报告口径。
```

train split 内必须报告：

```text
positive_LR_year_share
non_negative_EV_R_year_share
trigger_count_by_year
```

对 `approved_2_primitive_and`，year stability 必须按 combo event 自身重新计算，不能继承 component primitive 的 stability。

允许进入 family representative selection 的最低稳定性：

```text
positive_LR_year_share >= 0.50
non_negative_EV_R_year_share >= 0.40
at least 3 train years with trigger_count >= 30
```

validation split：

```text
只评估冻结 family；
不允许新增 family；
不允许改阈值；
不允许重排 family；
不允许根据结果修改 posterior / risk mapping。
```

robustness split：

```text
只做 no-harm / stability / regime 检查；
不作为 family 选择依据；
如果某个 frozen family 在 robustness 上 LR < 1 或 EV_R < -0.05，该 family 必须降级为 audit-only，不能进入 R03 family pool。
```

---

## 12. Required Outputs

输出根目录建议：

```text
ep4/outputs/r02_evidence_family_discovery_v1/
```

必须生成：

```text
manifests/r02_family_discovery_manifest.json
cache/r02_action_time_panel.parquet
cache/r02_primitive_event_panel.parquet
cache/r02_family_event_panel.parquet
reports/r02_primitive_search_summary.csv
reports/r02_primitive_rejection_audit.csv
reports/r02_combo_search_summary.csv
reports/r02_family_cluster_matrix.csv
reports/r02_family_incremental_lift.csv
reports/r02_family_selection_summary.csv
reports/r02_family_validation_summary.csv
reports/r02_family_execution_diagnostics.csv
reports/r02_family_stability_by_year.csv
reports/r02_effective_window_audit.csv
reports/r02_label_confusion_matrix.csv
reports/r02_mandatory_v3_seed_baseline.csv
reports/r02_final_report.md
```

`r02_effective_window_audit.csv` 必须包含：

```text
split
label_id
raw_action_time_rows
complete_forward_rows
incomplete_forward_rows
entry_execution_unavailable_rows
effective_label_end
complete_forward_rate
```

必须提供对应 config 和 validator：

```text
ep4/configs/r02_evidence_family_discovery_v1.yaml
ep4/scripts/run_r02_evidence_family_discovery.py
ep4/scripts/validate_r02_evidence_family_discovery.py
```

默认运行资源：

```yaml
runtime:
  default_n_jobs: 12
  max_n_jobs: 12
  parallel_backend: process_pool
  random_seed: 20260512
  deterministic_sort_required: true
```

实现必须默认使用 12 CPU 并行处理 primitive / combo / split-year metric jobs。若运行环境 CPU 少于 12，可自动降级到可用 CPU 数，但 manifest 必须记录：

```text
configured_n_jobs
effective_n_jobs
parallel_backend
random_seed
deterministic_sort_keys
```

并行计算必须满足：

```text
same config 下，effective_n_jobs = 1 与 effective_n_jobs = 12 的 selected family pool、combo top-k 和 final decision 完全一致；
所有 groupby / ranking / top-k 输出必须使用稳定排序；
所有同分排序必须使用 deterministic id ascending tie-breaker；
```

validator 必须 fail-closed 检查：

```text
action-time denominator 来自 PIT eligible stock-days；
effective_label_end / incomplete_forward_window 可复现；
executable_entry_available 的 denominator 保留 entry_execution_unavailable rows as negative；
winner / non-winner label 可由 event_t 和 forward windows 复现；
survival / distribution primitive 没有使用 event_t 之后的数据；
V3 post30 seed baseline 存在且原公式未被改写；
primary search 只使用 single primitive / approved_2_primitive_and / mandatory_composite_baseline；
approved_2_primitive_and 没有超过 2 个 primitive；
approved_2_primitive_and 的 component primitive 来自不同 group 且都通过 single-primitive early rejection；
approved_2_primitive_and 自身通过 combo early rejection；
每个 group-pair 的 approved combo 数量没有超过 config 上限；
approved combo 总数没有超过 max_total_approved_combos；
combo_rank_score 和 tie-breaker 可复现；
combo family representative 满足 incremental gate，否则只能 audit-only；
primary_LR_ci90_lower / upper 可由 instrument-year bootstrap 复现；
family representative 的 primary_LR_ci90_lower >= 1.00；
mandatory_composite_baseline 不被误判为 primary search AND 组合；
mandatory_composite_baseline 若进入 R03 pool，满足 allowed composite exception gates；
EV_R diagnostic execution 对所有 executable events 使用同一 fail-fast + H20 terminal rule；
label confusion matrix 存在且 row counts 可复现；
manifest 记录 configured_n_jobs / effective_n_jobs / parallel_backend / random_seed / deterministic_sort_keys；
effective_n_jobs = 1 deterministic smoke run 与 configured parallel run 的 selected family ids 一致；
instrument_year_concentration 没有作为绝对 reject gate；
validation / robustness 没有反向改变 frozen family；
contract validation failure 和 research gate failure 分开报告；
final decision 属于允许枚举值。
```

`r02_final_report.md` 必须明确区分：

```text
winner coverage diagnostic
action-time prior
posterior precision
EV_R
execution feasibility
family overlap / redundancy
label confusion matrix
R02 generic R-unit not numerically comparable to R01 V3 return_R
```

---

## 13. Required Final Decision

最终 decision 必须是以下之一：

```text
go_to_r03_evidence_accumulation
revise_family_search_space
archive_family_discovery_no_r03
```

允许进入 R03 的最低条件：

```text
至少 3 个进入 R03 pool 的冻结 family；baseline-only V3 seed 不计入该数量；
每个 family 在 validation primary_selection_label_id 上 LR > 1；
至少 2 个 family 在 validation 上 EV_R 非负；
每个进入 R03 的 family 在 robustness 上 LR >= 1；
每个进入 R03 的 family 在 robustness 上 EV_R >= -0.05；
不能出现 h20 正向但 h60 显著反向的 family；
family 之间没有被 cluster audit 判定为完全重复；
entry buyability / risk-distance 没有暴露不可执行缺陷；
post30 profile 不被单独解释为 full-size entry trigger；
所有公式和阈值都来自 train split 冻结。
```

如果只找到一个强 family，或者多个 family 都是 momentum 变体，则不能进入 evidence accumulation，只能回到 search space revision。

`h20 正向但 h60 显著反向` 的最低判定：

```text
validation continuation_h20 LR > 1.10
and validation continuation_h60 LR < 0.95
```

满足该条件的 family 可以保留为 audit-only，但不能进入 R03 family pool。

---

## 14. Implementation Notes

实现时应优先复用 R01 / EP2 已有的 daily PIT data、split convention、buyability / risk-distance 计算和 report generator pattern。

R02 V1 只复用 R01 V3 的 split / PIT universe / buyability / risk-distance bounds / cost model 思想；R02 V1 的 generic lookback-low stop 与 R01 V3 的 seed-specific structural stop 不同，因此 R02 family `unit_return_R` 不得在报告中直接和 R01 V3 `return_R` 数值比较。

本 requirement 不要求重新抓取市场数据。

本 requirement 不要求读取 post30 row-level search output。`post30 profile` 可作为一个已知 candidate family 被重建和评估，但它的先验必须来自 R02 action-time panel，而不是 R01 V3 的 winner-anchored provenance。
