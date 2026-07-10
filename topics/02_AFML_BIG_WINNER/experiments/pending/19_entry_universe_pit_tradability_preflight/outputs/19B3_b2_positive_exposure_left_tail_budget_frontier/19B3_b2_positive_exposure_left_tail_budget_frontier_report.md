# 19B3 B2 正 exposure 左尾预算前沿报告

## 1. Executive decision

### 1.1 最终裁决

本轮最终状态为：

```text
19B3_forward_oos_underpowered_not_pass
```

这不是 R2 失败，也不是 R3 获得支持，而是一个严格的 **forward OOS 不可评价裁决**。当前数据覆盖到
`2026-05-29`，恰好只够覆盖已经消费的 robustness outcome path；20 个交易日 embargo 尚未开始形成，
因此有效 forward 起点、首个 forward 决策日和首个完整 120-session 标签日期全部仍为
`not_yet_observed`。forward candidate、instrument、decision month 和右尾事件数均为 0，runner 在读取
任何 forward outcome 之前停止。

19B3 的目标是先压低 B2 左尾，在正 exposure 下允许牺牲部分右尾。

| 决策项 | 当前结果 | 含义 |
|---|---:|---|
| contract / lineage / output contract | pass / pass / pass | 实验身份、上游血缘和产物合同有效 |
| spent-design arm-role gate | pass | R2-primary、R3-diagnostic 的角色重放与冻结依据一致 |
| forward preoutcome evaluability | fail | 当前没有可合法读取 outcome 的 forward 样本 |
| forward support | fail | 由样本数为 0 导致，不是由效果量失败导致 |
| forward primary / incremental / right-tail / placebo gates | not_evaluated | 没有用 0 或 spent 数据伪造 forward 结果 |
| validation-stress authorized | false | validation 未读取、未运行 |
| next allowed requirement | none | 不能进入 19B4 |

### 1.2 当前能说与不能说

当前可以说：spent robustness 的设计审计显示，R2 是比 R1/R3 更值得放到新 forward OOS 上证伪的
左尾压缩方案；staged pipeline、泄漏边界、arm registry、placebo assignment hash 和空样本 fail-closed
路径已经闭合。

当前不能说：R2 已在 forward 上压低左尾、仍保持正 exposure，或通过 bootstrap/placebo/month stability。
这些字段在 final decision 中保持空值或 `not_evaluated`，没有用 spent-design 数值回填。

## 2. Spent-design arm-role audit（明确 non-support）

### 2.1 口径与样本

spent-design audit 使用已经消费的 robustness B2 primary denominator：

```text
split = robustness
date range = 2024-01-02 .. 2025-11-26
candidate_n = 1,552
dataset_role = spent_robustness_design_only
selection_or_tuning_allowed = false
support_claim_allowed = false
forward_gate_contribution = false
```

这里的唯一用途是验证 human restart 所依据的 arm 角色是否能机械复算。它不能替代 forward OOS，
也不能贡献 19B3 support。

指标解释：`weighted_ES10_MAE20` 是最差 10% 权重质量上的平均 20-session loss，越低越好；
`weighted_MAE20_p10` 是加权 MAE 的 10% 分位，越接近 0 越好；`weighted_p_left_tail_20` 是
`MAE_20 <= -20%` 的加权概率，越低越好；`right_tail_capture_retention` 是相对 R0 保留的
`MFE_120 >= +50%` 权重质量，越高越好。

### 2.2 四个冻结 arm 的实际读数

| arm | 角色 | retained / 1,552 | gross weight | 右尾 capture | ES10 | MAE20 p10 | p(left tail -20%) |
|---|---|---:|---:|---:|---:|---:|---:|
| R0 S0 untrimmed | baseline | 1,552（100.00%） | 1,552.000 | 1.0000 | 0.2951 | -0.2288 | 0.1476 |
| R1 ATR20 top10 trim | mild comparator | 1,393（89.76%） | 1,393.000 | 0.9057 | 0.2794 | -0.2173 | 0.1278 |
| **R2 VOL60 top30 trim** | **唯一 primary** | **1,082（69.72%）** | **1,082.000** | **0.6460** | **0.2607** | **-0.1999** | **0.0998** |
| R3 continuous vol budget | diagnostic challenger | 1,552（100.00%） | 988.904 | 0.5800 | 0.2746 | -0.2139 | 0.1175 |

冻结阈值为：R1 的 candidate `q_atr20` p90 = `0.985972`；R2 的 candidate `q_vol60` p70 =
`0.945892`。R2 实际移除 470 行，即 `30.28%`，与“top30 hard trim”一致；边界相等行统一删除，
因此不要求恰好等于 30%。四个 arm 的 expected-value gate 全部通过。

### 2.3 相对 R0 的左尾改善与右尾代价

| arm | ES10 改善 | ES10 相对降幅 | MAE p10 改善 | p(left -20%) 绝对下降 | p(left -20%) 相对下降 | 右尾牺牲 |
|---|---:|---:|---:|---:|---:|---:|
| R1 | +0.0156 | 5.30% | +0.0115 | 0.0198 | 13.40% | 9.43% |
| **R2** | **+0.0343** | **11.64%** | **+0.0289** | **0.0477** | **32.35%** | **35.40%** |
| R3 | +0.0205 | 6.93% | +0.0149 | 0.0300 | 20.36% | 42.00% |

这里的“MAE p10 改善 +0.0289”是从 `-22.88%` 改善到 `-19.99%`，即约 2.89 个百分点。
它非常接近但仍低于 forward 冻结门 `>= 0.03`，差约 `0.00108`；不能因为接近就降低门槛。
另一方面，R2 的 p(left -20%) 相对下降 `32.35%`，超过冻结的 `30%` 点估计门，右尾 capture
`64.60%` 也高于最低预算 `60%`。这些冲突正是需要新 forward OOS 独立裁决的原因。

## 3. Human restart、lineage 与输入闭合

### 3.1 Human restart

19B3 来自 research plan Section 12 的 human research restart，不来自 19B2 automated handoff。
`upstream_pipeline_authorization = false`，因此 19B2 的 `next_allowed_requirement = none` 没有被伪装成
自动晋级许可。

上游事实共核验 20 项，全部通过：

| scope | 核验项数 | 关键事实 |
|---|---:|---|
| 19A | 3 | critical gates 全过；cooldown=10 sessions；validation selection=false |
| 19B0 | 4 | B2 family/grid/hash 一致；selection track=positive beta exposure |
| 19B | 3 | positive exposure robustness pass；false-positive burden fail；cell gate=false |
| 19B1 | 6 | family/grid/row scope 一致；separable diagnostic；validation 未读；无自动 handoff |
| 19B2 | 4 | validation 未读；interaction superiority fail；best single feature=ATR20 top10；无自动 handoff |

### 3.2 输入与原始源审计

- 36 个登记输入 artifact 全部存在、非空且通过 input gate；18 个具有上游 expected hash 的 artifact
  全部匹配，其余 artifact 也记录了实际 SHA-256、大小、行数和 schema hash。
- qfq inventory 覆盖 4,597 个 instrument、8,787,346 行、约 985 MB；最早日期 `2017-01-03`，
  最晚日期 `2026-05-29`。
- top-N executable universe 和 CSI300 benchmark 的最大日期同为 `2026-05-29`。
- qfq inventory hash 为
  `43dffff915324e78d202c3a9eff2985de134cdd1111d0b8c4d16b370ae4d3ce1`，不是目录 mtime。

因此本轮 underpowered 不能归因于缺文件、上游 hash 漂移或 contract failure；它是由严格时间边界与
现有数据终点共同决定的。

## 4. Outcome-access / evaluability boundary

### 4.1 时间边界的机械推导

| 边界 | 日期 / 状态 | 解释 |
|---|---|---|
| train spent outcome path end | 2022-07-05 | validation purge 的左侧已消费路径终点 |
| validation effective window | 2022-08-03 .. 2023-06-06 | purge/embargo 后压力测试窗口，共最多 11 个 decision month |
| spent robustness last decision | 2025-11-26 | nominal forward 只能严格晚于该日 |
| spent robustness 120-session path end | 2026-05-29 | 19B/19B1/19B2 已读路径的最晚终点 |
| effective forward start | not_yet_observed | 还需要在 2026-05-29 后完成 20-session embargo |
| current max label-complete decision date | 2025-11-26 | 当前数据能完整覆盖 120-session path 的最晚决策日 |
| first new forward label 所需最少新增 session | 141 | 20 embargo + 1 个新决策 session + 120-session path |

`purge_embargo_overlap_row_n = 0`，overlap gate 通过。validation 的 6-month support floor 没有超过
固定窗口最多 11 个月，feasibility gate 也通过；但这只说明压力测试窗口在设计上可行，不等于它已被授权。

### 4.2 Forward preoutcome funnel

| preoutcome 层级 | 行数 |
|---|---:|
| raw B2 trigger | 0 |
| canonical | 0 |
| fill feasible | 0 |
| cooldown survivor | 0 |
| 120-session path complete | 0 |
| B2 primary candidate | 0 |
| distinct instrument | 0 |
| instrument-month | 0 |
| decision month | 0 |
| R2 Kish effective n / ratio | 0 / 0 |

之所以 raw trigger 也是 0，不是市场从未出现 B2 trigger，而是 freeze 只允许在严格 effective-forward
边界之后构造样本；这个边界尚未出现在 exchange calendar 中，所以后续 funnel 必然全为 0。

forward preoutcome evaluability gate 通过前，19B3 只是 pipeline dry-run，不产生科学结论。

### 4.3 Outcome-access 事实

outcome access audit 只有一条记录：freeze 阶段读取 robustness `2024-01-02 .. 2025-11-26` 的
`MFE_120|MAE_20`，用途严格限定为 `spent_design_arm_role_audit`，且
`selection_or_tuning_allowed = false`。

```text
forward outcome read count = 0
validation outcome read count = 0
finalize raw outcome read count = 0
```

这说明“不评价”不是报告措辞，而是物理 outcome read 边界确实没有被跨越。

## 5. Forward OOS support

### 5.1 Forward readout 状态

forward 下列文件均按冻结 schema 输出，但为零行：

- `forward_outcome_panel.csv`
- `forward_eligible_outcome_panel.csv`
- `arm_tail_readout.csv`
- `arm_pairwise_readout.csv`
- `cluster_bootstrap_readout.csv`
- `leave_one_month_out_readout.csv`
- `placebo_null_readout.csv`
- `support_and_concentration_readout.csv`

因此 `primary_left_tail_gate`、`incremental_frontier_gate`、`right_tail_budget_gate`、`placebo_gate`、
`bootstrap_gate`、`calendar_stability_gate`、`concentration_gate` 和 `absolute_left_tail_burden_gate`
全部是 `not_evaluated`，不是 `fail`。唯一的 `support_gate = fail` 由样本支持为 0 触发。

### 5.2 四张 forward 图如何阅读

四张图都带 `not_evaluable` 水印：

- `forward_left_tail_frontier.png`：没有任何 forward arm 的 ES10/capture 点，不能从空图比较 R2 与 R3。
- `forward_exposure_capture_frontier.png`：没有 arm-calendar-matched exposure ratio，因此不能引用
  spent robustness 的旧 ratio 代替。
- `forward_bootstrap_improvement_distribution.png`：bootstrap replication 为 0，不存在 CI 或分布方向。
- `forward_month_stability.png`：decision month 为 0，不存在 leave-one-month-out 稳定率。

这些图是“结果缺失的可视化审计”，不是平坦曲线、零收益或策略无效的证据。

## 6. R2 left-tail reduction frontier 与 R3 diagnostic comparison

### 6.1 R2 相对 R1：更强左尾压缩，付出更多右尾

在 spent-design 样本上，R2 相对 R1：

- ES10 再改善 `+0.01870`；
- MAE p10 再改善 `+0.01743`；
- p(left -20%) 从 `12.78%` 降到 `9.98%`，再下降 `2.80` 个百分点；
- 但右尾 capture 从 `90.57%` 降到 `64.60%`，额外牺牲 `25.98` 个百分点；
- gross weight 从 1,393 降到 1,082，少 311 个 unit exposure。

这与研究目标一致：当前不是追求“几乎不损失右尾的温和过滤”，而是先验证能否在保留至少 60% 右尾
capture 和正 exposure 的前提下，把左尾显著压低。R1 是轻度 comparator，不是可在 R2 失败时替代晋级的 arm。

### 6.2 R3 相对 R2：更低 gross，却同时得到更差左尾与更差 capture

R3 保留全部 1,552 行，但连续权重总和只有 `988.904`，相当于 R0 gross 的 `63.72%`，其余
`36.28%` 留在 cash。尽管比 R2 还少 `93.10` 个 gross unit，R3 的结果反而是：

- ES10 比 R2 **恶化** `0.01389`；
- MAE p10 比 R2 **恶化** `0.01397`；
- p(left -20%) 比 R2高 `1.77` 个百分点；
- right-tail capture 比 R2低 `6.60` 个百分点，只有 `58.00%`，低于冻结的 60% floor。

也就是说，R3 在 spent-design 上不是“用更多右尾换来更低左尾”，而是用更低 gross 同时换来更差的左尾
和更差的右尾保留。36 个 continuous feasibility 组合的 joint point-gate pass 数也是 0；forward 中只冻结
1 个 R3 公式，promotion-eligible R3 数为 0，没有隐藏搜索或临时改曲线。

**Finding：** hard trim 的优势不是更复杂，而是更集中地清除高 vol60 区域；连续权重的 0.25 floor
仍给极端高波动行保留权重，同时又普遍削减中等样本的 gross，导致左尾压缩效率不如 R2。

**Insight：** R3 的失败形态支持“B2 左右尾共享高波区域”的解释。若未来要研究连续预算，应另立新 requirement
改变函数族，而不是在 19B3 forward outcome 出现后临时降低 floor、改变曲率或将 R3 升格。

R2 A_VOL60_top30 是唯一可晋级 primary arm；R3 continuous budget 只作 diagnostic challenger。

## 7. Positive-exposure denominator bridge / right-tail budget

### 7.1 冻结门与 denominator

R2 的 forward right-tail budget 必须同时满足：

```text
positive_exposure_ratio_50_primary_arm_calendar_matched >= 1.20
right_tail_event_50_capture_retention >= 0.60
```

primary eligible comparator 按每个 arm 的每日 candidate gross 做 calendar matching，避免 universe row count
更多的日期机械获得更大权重。legacy ratio 使用相同 frozen eligible rows 的未加权均值，只用于解释 denominator
变化，不进入 gate。

positive exposure ratio >= 1.20 只使用 arm-calendar-matched eligible denominator；legacy ratio 只作桥接。

### 7.2 当前为什么没有 ratio

forward candidate 和 eligible comparator 均为 0，所以 primary ratio、legacy ratio、bridge delta、capture
retention 和 top-tail payoff contribution retention 全部为空。报告不会把 spent robustness 的 B2 ratio、R2 capture
或 19B 的 positive-exposure readout移植到 forward 栏位。

**Insight：** 当前能冻结的是“允许牺牲多少右尾”的决策规则，不能冻结未来实际会得到的 exposure ratio。
真正的正 beta 判断必须同时看 candidate 右尾概率与 arm-calendar-matched eligible denominator，不能只看 capture。

## 8. Placebo、bootstrap 与 month stability

### 8.1 P0 assignment freeze

freeze 已生成 2,000 条 P0 replication hash，seed=`20260711`。每条记录的 same-day gross invariance 和
weight-multiset invariance 字段均为 pass。但 frozen candidate n=0，因此 2,000 条 hash 实际上是同一个空 assignment
hash；这只能证明 dry-run 的确定性与 schema 完整，不能称为 placebo 科学检验通过。

forward `placebo_null_summary.json` 明确记录：

```text
placebo_replication_n = 0
observed_R2_vs_R0_ES10_improvement = null
null_mean = null
null_p95 = null
one_sided_placebo_p_value = null
```

### 8.2 Bootstrap 与 month stability

cluster bootstrap 以 instrument 为 cluster、冻结 `resample_n=2000` 和 seed=`20260710`，但当前 readout
为 0 行，因为 preoutcome evaluability 未通过。leave-one-month-out 同样为 0 行；不能报告 CI、p-value、
stable rate 或 concentration pass。

**Finding：** “2,000 个 P0 hash 已冻结”与“2,000 个 outcome placebo replication 已评价”是两回事。
前者已完成，后者为 0。把二者混写会把工程准备度误报为统计证据。

## 9. Absolute burden comparison

absolute burden 使用：

```text
eligible arm-calendar-matched MAE20 p10 - candidate arm MAE20 p10 <= 0.02
```

它用于区分“相对左尾改善但绝对负担仍高”和“绝对负担也可接受”，不否定相对 reduction 本身。
当前 candidate/eligible outcome 都未读取，因此该 gate 为 `not_evaluated`；不能用 spent R2 的
`MAE20 p10=-19.99%` 判断 forward absolute burden。

## 10. Validation pressure test（未获授权）

validation 是压力测试集，不是 arm 选择、调参或正面确认集。

validation effective window 已冻结为 `2022-08-03 .. 2023-06-06`，最多 11 个 decision month，
6-month support floor 在结构上可达。但 forward provisional state 是 underpowered，
`validation_stress_authorized=false`，因此：

```text
validation preoutcome manifest = not created
validation outcome read = 0
validation stress gate = not_run
validation stress state = not_authorized
```

validation thresholds 是 frozen directional veto floors，不是 forward support floors；validation pass != independent positive support。
validation fail/underpowered 也不能通过 retune、换 arm 或回写 forward gate 修复。

## 11. Findings、失败解释与研究洞见

### Finding 1：19B3 当前验证的是管道纪律，不是 R2 的经济效果

contract、lineage、spent role、search accounting、purge/embargo、output contract 全部通过；唯一决定性阻断是
forward preoutcome evaluability。因而当前状态应读作“科学问题尚未开始被新数据检验”，而不是“实验运行失败”。

### Finding 2：R2 是设计样本上的有效 frontier incumbent，但尚未跨过独立证据门

R2 在 spent 样本上把 ES10 从 `29.51%` 压到 `26.07%`，把 MAE p10 从 `-22.88%` 改善到
`-19.99%`，把 -20% 左尾概率从 `14.76%` 降到 `9.98%`；代价是只保留 `64.60%` 的右尾 capture。
这正好落在“明显压左尾、允许损失部分右尾”的研究区域，所以适合作为唯一 primary，而不是结论已经成立。

### Finding 3：R3 在设计样本上被 R2 支配，不能承担救活角色

R3 的 gross 更低，但 ES10、MAE p10、-20% 左尾概率和右尾 capture 全部差于 R2。这个结果支持把 R3
留在 diagnostic 位，而不是以“连续权重更平滑”为理由给予 promotion 资格。

### Finding 4：当前 underpowered 是时间结构造成的，不是样本筛选太严

spent path 直到数据终点才完成，embargo 之后还需要新决策日及 120-session path。即使放宽 B2 threshold，
也无法在现有数据里创造合法 forward outcome；放宽 threshold 只能制造泄漏，不会增加真正的时间外证据。

### Insight：下一次重跑应由数据可评价性触发，而不是由当前 dry-run 状态触发

最早的单行完整标签至少需要新增 141 个 exchange session；而正式 support 还要求至少 300 candidates、
50 instruments、200 instrument-months、6 decision months、50 个 +50% 右尾事件以及 R2 Kish n>=200。
因此“出现首行标签”仍不等于“实验可评价”。重跑前应先检查 coverage audit 中所有 preoutcome floors，
不能为了尽快得到结果而提前读取不完整 outcome 或动用 validation 补样本。

## 12. Decision boundary 与 next step

当前机械裁决：

```text
final_decision_state = 19B3_forward_oos_underpowered_not_pass
blocking_reason = forward_preoutcome_evaluability_gate_failed
next_allowed_requirement = none
validation_stress_authorized = false
pipeline_dry_run_only = true
```

只有新的 forward OOS 先满足 evaluability/support floors，并通过 R2 left-tail reduction、R2-vs-R1 incremental、
right-tail budget、placebo、bootstrap、calendar stability、concentration 与 absolute burden gates，才可能授权
validation-stress；validation 只能 veto/downgrade，不能创建 support。

19B3 support 不等于可交易策略 support。
19C replay authorized = false。
EP20 policy preflight authorized = false。

所有 model training、entry/exit/holding policy、portfolio backtest、deployment、production signal 和 live trading
authorization 均为 false。

### Artifact index

- `freeze/spent_design_arm_role_audit.csv`：R0–R3 spent-design 角色与数值复算。
- `freeze/data_coverage_and_forward_support_audit.csv`：时间边界、validation 窗口和 forward funnel。
- `freeze/upstream_contract_audit.csv`：20 项上游事实核验。
- `freeze/source_artifact_hash_audit.csv`：4,597 个 qfq 文件的逐文件 inventory。
- `freeze/b2_arm_registry.csv`：唯一 primary、comparators、R3 diagnostic 与 P0 placebo 定义。
- `freeze/p0_permutation_assignment_hashes.csv`：2,000 条 preoutcome assignment hash。
- `forward/forward_decision.json`：underpowered、零 outcome read 和 validation 未授权裁决。
- `entry_universe_19b3_decision.csv`：最终一行决策与全部 authorization boundary。
- `outcome_access_audit.csv`：唯一 spent-design outcome read 记录。
