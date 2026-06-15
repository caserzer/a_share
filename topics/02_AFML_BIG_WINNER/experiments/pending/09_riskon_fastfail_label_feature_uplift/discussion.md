# 09 Rejector 研究目标再校准（Reviewer-driven Revision）

## 0. 本文定位

本文是对 09A / 09B / 09C 之后 reviewer feedback 的结构化重构。

它不是新实验，也不是 requirement，而是：

```text
决定 rejector 下一阶段应该做什么、不该做什么的研究边界重定义文档。
```

核心变化是：rejector 不再被视为一个单模型问题，而是被拆成三层系统设计问题：

```text
safety / efficiency / execution 必须分离。
```

### 0.1 Density population freeze

density / execution layer 负责重新确定 downstream population。

```text
10A = density population freeze
10B / 10C supported gate = post-dedup population only
```

原因是 density 不是一个普通后验 gate。它会改变进入后续模型的样本总体：

```text
raw R-core events
    ↓
hard execution / feasibility filter
    ↓
density-only cooldown / de-dup rules
    ↓
post-dedup population
    ↓
10B / 10C train / threshold / gate population
```

因此 10A 的核心产物不是“density pass/fail”，而是一个新的 downstream denominator / sample contract：

```text
post_dedup_population_contract
post_dedup_sample_count_by_split
post_dedup_label_coverage_audit
post_dedup_feature_matrix_contract
post_dedup_sample_weight_contract
```

这个 population contract 至少要按 split / denominator 报告：

```text
sample_n
evaluable_event_n
winner_n
E1_missed_winner_n
fast_fail_positive_n
fast_fail_winner_n
false_repair_positive_n
hybrid_positive_n
unique_instrument_n
unique_event_day_n
formal_event_day_density
p95_density
rolling_10d_executable_event_day_density
rolling_20d_executable_event_day_density
```

10B / 10C 可以使用 pre-dedup 样本做 diagnostic replay，但不能用 pre-dedup 结果 claim supported。所有 supported 训练、threshold selection、gate 和 cascade readout 都必须在 10A 冻结后的 post-dedup population 上完成。否则就是在一个总体上训练 / 评估，在另一个总体上部署，会产生 train / serve skew。

## 1. 总体共识

review 已确认以下三点成立。

### 1.1 09C 是有信号，但不是可用 rejector

09C 证明：

```text
hybrid cost target 存在 OOS signal
```

但也证明：

```text
当前 selected hybrid model 不是可部署 rejector
```

因此 09C 不能被解释成已通过的 risk_on cost rejector，也不能被解释成 fast-fail uplift。

### 1.2 三类问题必须拆开

```text
fast-fail     -> structural safety, low capacity
false-repair  -> exposure efficiency, medium capacity
density       -> execution constraint, rule system
```

这三类问题不能继续混成一个 hybrid target / one-model rejector。

### 1.3 09C 最大价值是 diagnostic，不是 model

09C 的价值在于：

```text
feature structure 有效
cost signal 存在
component decomposition 暴露了问题
```

09C 的失败也同样清楚：

```text
winner retention 不够
fast-fail 被 false-repair 稀释
density 未系统化前置
threshold tuning 不能替代结构改进
```

## 2. 核心修正：Rejector 不能是单模型

已废弃结构：

```text
one hybrid model:
    break_swing_low_20 OR false_repair_20d
```

review 后的正确结构：

```text
Layer 0: Density / execution rules, no ML
Layer 1: Fast-fail structural safety rejector, low capacity
Layer 2: False-repair / exposure-cost rejector, medium capacity
```

后续 requirement 不应再写成“继续训练 risk_on hybrid cost rejector”，而应写成三层系统的独立验证。

## 3. Layer 0：Density 是系统约束，不是模型问题

### 3.1 定位

Density layer 的作用是：

```text
去重
限流
执行可行性约束
同一机会重复触发控制
```

review 的关键结论是：

```text
density is not a learning problem
density is a system constraint
```

因此 density 必须在 ML rejector 前处理。

更准确地说，density layer 的核心职责是冻结样本总体，而不是给既有模型输出再加一个 pass/fail 标签。10A 必须回答：

```text
经过 execution / cooldown / de-dup 后，
真正进入 10B / 10C 的样本量是多少？
各 split / target component 的 positive count 是否还足够？
post-dedup population 是否仍能代表 R-core supported source？
```

只有这些问题回答清楚后，10B / 10C 的模型读数才有可迁移性。

### 3.2 必须规则化

density layer 应使用可部署规则，而不是 ML：

```text
same-instrument cooldown
same-family de-dup
same-mechanism de-dup
rolling 10D / 20D cap
execution feasibility filter
```

最小 baseline：

```text
For same instrument, density-first baseline:
    after the first chronologically eligible R-core event is admitted
    by hard data / execution rules,
    suppress new entry candidate events for 10 trading days.

If another raw source event appears inside cooldown:
    keep it as state / readout feature,
    not as a new entry sample.
```

这里的 `admitted` 只表示通过 hard data / execution / density rule 的 chronological admission，不表示已经通过 fast-fail 或 false-repair score。

如果要测试 score-aware within-window de-dup，必须作为单独 arm 预声明：

```text
score then cooldown
cooldown then score
within 20D keep lowest P(failure)
within 20D keep highest expected utility
```

这些规则必须部署可实现，不能使用未来 episode boundary、未来 MFE / MAE 或事后 winner window。

## 4. Layer 1：Fast-fail structural safety rejector

### 4.1 目标

Fast-fail layer 的严格目标是：

```text
kill early structural failure
subject to high winner retention
```

它是 safety gate，不是 alpha source，也不是 exposure optimizer。

### 4.2 本质约束

当前 `break_swing_low_20` label 的自然 failure region 约为 6% 到 7%：

```text
R-core label-oracle natural point:
    reject fraction ~= 7.0613%
    keep fraction ~= 92.9387%
    winner retention ~= 96.6730%
    non-winner hit ~= 7.8377%
    fast-fail non-winner capacity ~= 6.4886%
```

这意味着：

```text
fast-fail capacity ~= 7%
不是 20% 到 30% rejector
不是大容量 cost optimizer
```

### 4.3 Reviewer 修正点

之前的错误是把 fast-fail 当成 20% 到 30% reject model。这个方向已经废弃。

正确定位：

```text
small safety gate only
```

### 4.4 Threshold 区间

下一轮 fast-fail-only threshold grid：

```text
keep_9000
keep_9250
keep_9300
keep_9400
keep_9500
keep_9600
keep_9700
```

其中 `keep_9000` 只作为 lower-bound sensitivity。真正的 selected operating point 应落在：

```text
keep_9250 到 keep_9700
```

并由 winner-retention floor 决定，而不是因为 grid 包含 `keep_9000` 就允许 10% reject capacity。

### 4.5 Gate

fast-fail structural safety gate 必须把 binding 与 floor 分清，并通过统计功效预检。

step 0 — absolute-count power gate（precondition，不过就禁 ML claim）：

```text
per threshold cell, train / validation / robustness 各自报告：
    fast_fail_positive_n
    fast_fail_winner_n
    rejected_fast_fail_positive_n
    rejected_fast_fail_winner_n
    rejected_fast_fail_non_winner_n

capture-lift power:
    看 fast_fail_positive_n 与 rejected_fast_fail_positive_n

winner-injury / wrong-kill power:
    看 fast_fail_winner_n 与 rejected_fast_fail_winner_n

any split below predeclared min count:
    对应 claim 降级，不得把低功效读数写成支持证据
```

这里要纠正一个容易误读的点：09A 中 validation `5`、robustness `61` 不是 fast-fail positive 总数，而是 `fast_fail_positive AND winner_120` 的数量。它们主要约束 winner-injury / wrong-kill 的统计功效，不直接约束 fast-fail capture-lift。capture-lift 的分母应使用 fast-fail positive 总数。

09A R-core supported split 的关键计数如下：

| split | fast_fail_positive_n | fast_fail_winner_n | random rejected fast-fail positives @ keep_9700 | random rejected fast-fail positives @ keep_9250 | random rejected fast-fail winners @ keep_9700 | random rejected fast-fail winners @ keep_9250 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 1,250 | 110 | 37.5 | 93.8 | 3.3 | 8.3 |
| validation | 338 | 5 | 10.1 | 25.4 | 0.2 | 0.4 |
| robustness | 582 | 61 | 17.5 | 43.7 | 1.8 | 4.6 |

这张表只是 pre-dedup 的解释性读数，用来说明功效风险的来源。它不得作为 10B 的 go / no-go 判定。10B 的硬功效门槛必须读取 10A 冻结后的 post-dedup population，因为 density 从 `26.34` 压到 `7.5` cap 附近会显著压缩样本量；validation 的 `fast_fail_winner_n = 5` 在 post-dedup 后可能只剩 1 到 2 个甚至更少。

因此更准确的解释是：

```text
capture-lift:
    validation / robustness 仍有 338 / 582 个 fast-fail positives，
    可以做方向性读数，但在 keep_9700 到 keep_9250 的小容量下
    rejected_fast_fail_positive_n 预计只有十几个到几十个，
    需要 absolute-count power gate。

winner-injury / wrong-kill:
    validation 只有 5 个 fast-fail winners，
    robustness 只有 61 个 fast-fail winners，
    小容量 reject 后 rejected_fast_fail_winner_n 可能接近 0 到个位数，
    因此不能把低 injury 读数误写成稳定支持证据。
```

10A 必须输出 post-dedup fast-fail power audit，并把 random baseline 与 rule baseline 同时列出：

```text
post_dedup_fast_fail_power_audit

keys:
    denominator_id
    split
    threshold_id / capacity_id

population counts:
    post_dedup_sample_n
    post_dedup_fast_fail_positive_n
    post_dedup_fast_fail_winner_n

random baseline counts:
    random_rejected_fast_fail_positive_n
    random_rejected_fast_fail_winner_n
    random_rejected_fast_fail_non_winner_n

rule baseline counts:
    rule_baseline_rejected_fast_fail_positive_n
    rule_baseline_rejected_fast_fail_winner_n
    rule_baseline_rejected_fast_fail_non_winner_n

candidate score counts:
    score_rejected_fast_fail_positive_n
    score_rejected_fast_fail_winner_n
    score_rejected_fast_fail_non_winner_n

go_no_go:
    capture_lift_power_status
    winner_injury_power_status
    fast_fail_ml_supported_gate_allowed
```

其中 rule baseline 是 §4.5 定义的规则化 swing-low stop / structural stop null，不是 random uniform rejection。10B 的 binding objective 是相对 rule baseline 与 random baseline 的增量；如果功效表只列 random baseline，就缺少真正的主比较对象。

post-dedup go / no-go 规则：

```text
if post_dedup_fast_fail_positive_n < predeclared_min_positive_count:
    10B 只能输出 rule-based structural stop diagnostic
    不得 claim fast-fail capture-lift

if post_dedup_fast_fail_winner_n < predeclared_min_winner_count:
    10B 只能输出 rule-based structural stop diagnostic
    不进入 ML supported gate
    不得 claim winner-injury / wrong-kill 稳定性

if rule_baseline_rejected_fast_fail_positive_n 或
   rule_baseline_rejected_fast_fail_winner_n 低于 predeclared min count:
    capacity_matched_capture_lift_over_rule_baseline 只能 diagnostic
    不得作为 supported pass
```

step 1 — binding objectives（决定 pass / fail）：

```text
capacity_matched_capture_lift_over_rule_baseline > predeclared margin
capacity_matched_capture_lift_over_random > predeclared margin
accepted_MAE_10 improves
```

step 2 — floor / side constraints（必要但不用于选择）：

```text
winner_retention >= predeclared floor
wrong_kill_rate <= predeclared cap
density not worse
OOS readout no severe reversal
```

为什么 winner_retention 从主判据降为 floor：label oracle 在 reject 7% 时 retention 已经 96.67%，在 keep_9250+ 的小容量上模型拒得更少，retention 会机械地偏高，94% 到 96% 的 floor 几乎对所有模型都成立，不能区分好坏。真正 binding 的是匹配容量下相对 rule / random baseline 的 capture lift。

no-overlap ablation 只作解释，不作 kill：fast-fail-only 主轴是 FS2_basis_path_quality（09B group MDA train AUC drop 0.2654），与 break_swing_low_20 structural stop 机制同源，去 related-overlap 后坍塌是先验上大概率成立的事件。因此不能把「去 overlap 后是否坍塌」当 kill 判据，而应把规则化 swing-low stop 设为显式 null / control，让 10B 只回答「ML 在该规则之上是否有增量」。若 full 有效但 drop related-overlap 后完全坍塌，解释为 rule-equivalent，降级为：

```text
rule-based structural stop diagnostic
```

不能 claim 泛化 fast-fail alpha。

## 5. Layer 2：False-repair / exposure-cost rejector

### 5.1 目标

False-repair layer 的目标是：

```text
减少无效 exposure
降低 repair-failure 成本
提高 confirm 前质量
```

它不是 fast-fail 的增强版本。

### 5.2 Reviewer 关键结论

09C hybrid uplift 主要来自 false-repair，而不是 fast-fail。

因此正确解释是：

```text
false-repair != safety
false-repair = efficiency
```

### 5.3 正确定位

| layer | role | capacity |
| --- | --- | --- |
| fast-fail | structural safety | low |
| false-repair | exposure efficiency | medium |
| density | execution constraint | rule |

False-repair rejector 可以保留，但必须单独建模、单独 gate、单独解释。不能再混入 fast-fail target 后声称 fast-fail uplift。

### 5.4 Threshold 与 readout

建议 false-repair threshold grid：

```text
keep_8000
keep_8250
keep_8500
keep_8750
keep_9000
```

必须报告：

```text
winner retention
E1-missed retention
bridge retention
false-repair reduction
exposure-days reduction
MFE / confirm_20 relation
OOS rejected-fraction spread
density after cascade
```

winner retention floor 可以低于 fast-fail layer，但不能接近 09C 的 67% 到 70%。否则它只是一个有 cost signal 但不可用的 rejector。

## 6. 最大结构性问题：source_caveated 没有 exit path

当前 09 的设计继承了：

```text
source_caveated = true
```

review 指出的最大结构问题是：

```text
所有结论都继承 source_caveated=true，
但文档没有给出 exit path。
```

这会导致后续研究永远只能写 caveated conclusion，却不清楚什么时候可以升级。

### 6.1 必须拆成两条路径

后续 requirement 必须显式区分：

```text
Path A: diagnostic-only research
    允许 source_caveated=true
    只能输出 diagnostic / feature-source / source_caveated_candidate

Path B: candidate for entry
    source contract 修复完成
    必须重新跑 input audit
    必须重新确认 source_pool reconstruction
    必须重新生成 09A/10A/10B/10C 受影响的 label binding
    必须重新生成 feature matrix、sample weights、model scores、threshold frontier
    必须刷新 manifest hashes 与 report hashes
    才能进入无 caveat research-entry 讨论

Path B+:
    若目标是真正 entry-candidate，
    还必须新增 entry / execution contract
    包括 trade_time、next-open feasibility、cooldown deployment rule、
    post-dedup execution replay、density caps、risk / sizing 非目标边界。
    source 修复只是必要条件，不是 entry-candidate 的充分条件。
```

### 6.2 决策命名约束

只要 source caveat 未修复，所有正向结论只能使用 caveated variant：

```text
source_caveated_research_entry_candidate
source_caveated_feature_source_supported
source_caveated_diagnostic_supported
```

不得输出无 caveat 的：

```text
research_entry_supported
entry_candidate_supported
production_ready
```

## 7. fast-fail label 本身的结构性问题

`break_swing_low_20` 的核心含义不是“一个好 rejector distribution”，而是一个 structural event filter。

它的结构事实是：

```text
natural failure region ~= 6% 到 7%
```

含义：

| item | conclusion |
| --- | --- |
| fast-fail capacity | about 7% |
| not | 20% 到 30% rejector |
| not | cost optimizer |
| yes | structural safety alert |

因此后续不能再把 fast-fail label 放进 hybrid target 后，用大容量 threshold 去 claim fast-fail cost rejector。

## 8. Density 重新定性

错误理解：

```text
density = ML problem
```

正确理解：

```text
density = system constraint
```

review 要求：

```text
density must be handled before ML
```

09C 的 density 失败不是“模型还不够强”，而是系统层缺少前置 de-dup / cooldown / execution feasibility control。

## 9. 三个 rejector 的真实关系

最终结构：

```text
Density Layer
    rules only
    same-instrument cooldown / same-family de-dup / rolling cap
        ↓
Fast-fail Structural Gate
    low capacity, about 7%
    high winner retention first
        ↓
False-repair Rejector
    medium capacity exposure-efficiency filter
        ↓
Execution / entry
```

Scope 纪律：

```text
R-core:
    supported scope for fit / threshold / gate

R6:
    readout-only scope
    no fit
    no feature selection
    no threshold selection
    no cooldown tuning
    no supported gate
```

如果下一轮要把 R6 升级为 training / gate scope，必须补充新的 source pool contract 和 input audit。

### 9.1 Population 冻结：避免 train / serve skew

Layer 0 的 density / execution 规则会改变下游总体。09C 的 density 是全 split 的结构性超标（formal_event_day_density 26.34 vs cap 7.5），de-dup 会大幅改变事件总体。因此：

```text
10A 冻结 post-dedup population
10B / 10C 必须在 post-dedup population 上训练与评 gate
禁止在 pre-dedup 总体上评 gate、在 post-dedup 总体上部署
```

诊断可以并行起步，但 gate 评估的 population 必须统一到部署 population，否则 10B / 10C 的读数不可迁移。

### 9.2 Cascade 级联合 gate

三个分段 gate 各自通过，不等于级联后有净改善。fast-fail 与 false-repair 会拒掉部分重叠事件（09C component attribution 的 both-rejected 列已显示），二者 cost reduction 不可加。因此必须预声明一个 cascade-level 联合 readout：

```text
overlap-deduplicated cost attribution（避免双计）
primary: cascade vs same R-core pre-cascade population:
    winner recall net change
    false-positive exposure-days net change
    density after Layer 0
        = Layer 0 frozen value, not Layer 1/2 incremental gain

secondary readout: E1 baseline / E1-missed retention
    只作外部 repair baseline 与 missed retention 参照
    不作为 rejector uplift 的主比较对象
```

最终判据是「同一 R-core population 上 cascade 前后的净改善」，而不是三段各自的分数，也不是把 R-core cascade 与 07 E1 baseline 直接混作一个 uplift comparison。E1 可以保留为外部 repair baseline、E1-missed retention 或 fallback 参照。

## 10. reviewer 对 09C 的最终定性

09C 成功点：

```text
有 OOS signal
feature structure valid
decomposition 正确
```

09C 失败点：

```text
1. hybrid model 混合三种问题
2. fast-fail 被 false-repair 稀释
3. density 未系统化前置
4. threshold tuning 不是 structural improvement
```

因此 09C 的最终价值是 diagnostic evidence，而不是 model candidate。

## 11. 下一步允许做什么

Only allowed scope：

```text
fast-fail small-capacity gate analysis
false-repair medium-capacity rejector
density rule system
ablation-based validation
source-caveat exit-path audit
```

推荐拆分：

```text
10A = density rule system, non-ML
10B = fast-fail structural gate, low capacity
10C = false-repair rejector, medium capacity
```

Diagnostic 与 supported gate 必须区分：

```text
10B / 10C 可以并行做 pre-dedup diagnostic replay。
10A 冻结 post-dedup population。
10B / 10C 的 supported gate 必须在 post-dedup population 上重新训练或重新校准后评估。
禁止用 pre-dedup 训练 / 选择的模型直接 claim post-dedup supported gate。
```

### 11.1 10A Density rule system

目标：

```text
让 selected events 形成可部署的 post-dedup population。
```

必须比较：

```text
cooldown-only
same-family de-dup
same-mechanism de-dup
```

必须输出：

```text
post_dedup_population_contract
post_dedup_sample_count_by_split
post_dedup_label_coverage_audit
post_dedup_fast_fail_power_audit
post_dedup_false_repair_power_audit
post_dedup_density_audit
```

其中 `post_dedup_fast_fail_power_audit` 是 10B 的 ML go / no-go 输入。若该表显示 post-dedup fast-fail winner 或 positive count 低于预声明下限，10B 直接降级为 rule-based structural stop diagnostic，不进入 ML supported gate。

Layer 0 baseline 只能使用无 score 的规则。以下 score-aware arm 不属于纯 Layer 0，只能作为 post-score cascade diagnostic：

```text
score then cooldown
cooldown then score
```

任何 score-aware arm 都必须 train-only 冻结，validation / robustness 只能 readout。

### 11.2 10B Fast-fail structural gate

目标（窄化为相对规则基线的增量问题）：

```text
以规则化 swing-low stop 为显式 null / control，
验证 fast-fail-only score 在匹配容量下相对该规则是否有 incremental capture lift。
```

注意：09C 已经 fit 过一个 fast-fail-only score 模型，它只能作为 pre-dedup diagnostic replay 的参照。由于 10A 会改变 post-dedup population，10B 允许并且在 supported gate 下必须在 post-dedup population 上重新训练、重新校准或至少重新冻结 threshold policy。任何只复用 09C pre-dedup score 的结果，只能输出 diagnostic，不得 claim supported。

§4.5 的 absolute-count power gate 通过后，再看：

```text
capacity_matched capture lift over rule / random baseline (binding)
accepted MAE_10 improvement (binding)
winner retention floor (side)
wrong-kill / winner injury (side)
density after Layer 0
full vs no-overlap ablation (interpretation only)
```

### 11.3 10C False-repair rejector

目标：

```text
验证 false_repair_20d_component 是否能作为中容量 exposure-efficiency filter。
```

注意：09C ablation 显示 false-repair 信号不依赖 swing-low 同源特征（drop_fs2_related_subset_only 后 robustness cost reduction 反而升到 24.28%），因此 10B 的 overlap-collapse 风险不适用于 10C；10C 是三段里信号最实、最可能产出 caveated research-entry 的一段。

R2 source 处理必须作为 10C frozen input 定死（补 amount / volume 字段或给单独 family budget / cooldown），不得留作 10C 内部可调项，否则又多一个隐性 knob 同时改变特征集与样本总体。

必须看：

```text
false-repair reduction
winner retention
exposure-days reduction
E1-missed retention
bridge retention
MFE / confirm_20 relation
OOS rejected-fraction spread
train-only threshold instability proxy
    = purged-CV 下 selected threshold / reject-fraction 的方差
    只能来自 train-only purged folds, 不得读 validation / robustness
```

## 12. 禁止继续做什么

后续不得继续：

```text
hybrid cost model tuning
PCA-driven feature expansion
threshold sweep optimization
transition modeling
single-model rejector
validation / robustness threshold selection
future episode-boundary de-dup
using AUC / PR-AUC as rejector success criterion
```

尤其不要继续把问题写成：

```text
找到更好的模型，把 09C hybrid frontier 推过线。
```

这会重复 09C 的结构性错误。

## 13. 最终一句话

```text
Rejector 不是一个模型问题，
而是一个三层系统设计问题：
execution / safety / efficiency 必须分离。
```

下一阶段应重新设计为：

```text
10A = density rule system, non-ML
10B = fast-fail structural gate, low capacity
10C = false-repair rejector, medium capacity
```
