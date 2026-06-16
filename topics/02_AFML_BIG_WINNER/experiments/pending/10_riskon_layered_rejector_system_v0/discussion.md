# 10 系列 Rejector 系统讨论：false-repair 失败的根因诊断

> 本文档为只读讨论记录，整理 10A–10C 系统的失败诊断、对外部 "Routing System" 提案的评估、以及一系列只读 crosstab / score-layer 验证的计算结果与结论。所有计算口径基于 10A default supported scope：
> `population_id = 10A__same_instrument_cooldown_10d` / `denominator_id = post_dedup_risk_on_r_core` / `admission_status = admitted`，总样本 `15,802`，winner `2,647`（总体 winner rate `16.75%`）。
> 数据来源：`outputs/publishable/tables/10C_false_repair_rejector/winner_retention_audit.csv`、`false_repair_threshold_frontier.csv`，以及上游 10A power audit。

---

## 0. TL;DR（一句话结论）

10C 不是"模型能力不足"，也不是简单的"label 混了 winner"。诊断链最终锁定为：

> **拒绝"量"不漂，拒绝"方向"漂。** 同一个 10% 拒绝预算，train 上能避开 winner，OOS 上系统性地、精准地把一类特定 winner —— **E1-missed（早期 shakeout / 回踩再上型）大赢家** —— 误判成 false-repair 拒掉。被 10C 杀掉的 winner 中约 **70–82% 是 E1-missed**。

这把根因从"label entanglement"修正为 **"boundary transport failure（决策面在 OOS 方向漂移）+ 打击点高度集中在 E1-missed winner 的 early shakeout 区间"**。直接含义：winner 保护应下沉到 **exit 层（t+k path-dependent 早退）**，而非在 t0 entry 层做不可逆裁决。

---

## 1. 外部 "Routing System" 提案评估

讨论者提出：当前问题是 false-repair 与 winner early-phase 在 t0 特征空间结构性不可分（entanglement），应从 "Classification System" 转向 "Layered Risk Routing System"（输出多策略概率/权重而非唯一类别）。

### 1.1 诊断部分：正确，但 10D 已内建

"entanglement 是根因"不是新观点，而是 10D 需求的设计前提：

- 10D §6 的 **Gate-0 entanglement separability diagnostic** 就是用 09B t0 特征训练 injury(winner/E1) vs clean-false-repair 的可分性探针，只看 validation/robustness AUC 是否过 `0.60` floor。
- 若不可分，10D §6.3 直接禁止 rejector-supported，把结论导向 "09B feature extension / winner-safe label 工程"。

### 1.2 药方部分：逃不开同一个信息上限（核心反驳）

```text
Classification: decision = argmax P(class | x)
Routing:        decision = π(policy_k | x)
```

`π` 和 `argmax` 用的是**同一个 x**。若真的 `P(injury|x) ≈ P(clean|x)`，那么任何建立在 x 上的策略函数 π(·|x) 信息量完全相同。Routing 可以更保守、可以重新分配风险，但**无法凭空制造 x 里不存在的可分信息**。entanglement 是 feature space 的属性，不是 model head 的属性。换 head 不解决 feature 不可分。

### 1.3 "Routing 更稳定" 是 trivial 的稳定

动作空间只有 reject/keep 一个 entry 候选，"uncertainty 路由"最终塌回 keep 或 reject。让系统更保守 = 少拒 = 吐回 false-repair capture —— 这正是 10D §13 `rescue_capture_tradeoff` 已经在量化的 trade-off。Routing 的"稳定"就是这条曲线上更靠近"少拒"的一端，不是新能力。

### 1.4 唯一可吸收的增量

显式 abstention / uncertainty 桶（conformal selective prediction）在统计上合理，但：它是 10D 的**增量而非替代**，可作为 10E 提案；且它仍依赖"哪些行 uncertain"在 OOS 稳定可识别 —— 如果连这个都不稳定，abstention 退化成"全弃权"，零信息。

**结论：Routing 提案的诊断与 10D 重合，药方逃不开 entanglement 的信息上限，本质是把"该去补特征/换决策层"换成了"该换架构"的更贵也更虚的说法。先用 Gate-0 把可分性测出来，再决定要不要谈架构。**

---

## 2. 三层系统回顾

| 层 | 本质 | 最优点 | 结果 | 状态 |
|---|---|---|---|---|
| 10A Density | same-instrument cooldown，去事件冗余 | `same_instrument_cooldown_10d` | density ↓ ~48%，winner 结构基本不变 | 解决数据冗余，非信息结构 |
| 10B Fast-Fail | low-risk structural filter（10d horizon） | `keep_9400` | fast-fail lift +18pp，winner retention ≈94% | 可稳定工作，但不解释结构 |
| 10C False-Repair | false-repair 分类拒绝（20d horizon） | `full / keep_9000` | train lift +7.8pp，validation winner retention 75%、E1 retention 57% | **失败点** |

---

## 3. 诊断链：四轮验证

### 3.1 第一轮：horizon-mismatch 假说（后被部分证伪）

初始直觉：fast-fail（10d reject）安全而 false-repair（20d reject）崩，是因为 20d label 物理上覆盖了 120d winner 的 early shakeout，导致 20d 正类比 10d 正类混进更多 winner。

预测：`P(winner | false_repair_20d+)` 应显著高于 `P(winner | fast_fail_10d+)`。

### 3.2 第二轮：ALL crosstab —— 证伪 per-capita 污染率假说

| label | positive_n | positive_winner_n | P(winner \| label+) | P(label+ \| winner) |
|---|---:|---:|---:|---:|
| `fast_fail_10d` | 1,280 | 114 | **8.91%** | 4.31% |
| `false_repair_20d` | 5,033 | 467 | **9.28%** | 17.64% |

By split：

| split | fast_fail P(winner\|+) | false_repair P(winner\|+) |
|---|---|---|
| train | 70/702 = 9.97% | 277/3,025 = 9.16% |
| validation | 5/236 = 2.12% | 20/709 = 2.82% |
| robustness | 39/342 = 11.40% | 170/1,299 = 13.09% |

**结论修正：**

1. **label 层无罪。** 两个 label 的单位污染率几乎相等（8.91% vs 9.28%），且都**低于**总体 winner rate 16.75% —— 两个正类其实都是 winner-**稀释**的。"20d label 比 10d 更脏"在 rate 层不成立，horizon-mismatch 的"污染率"版本被证伪。
2. **差异不在 rate，在 blast radius。** false-repair 正类池 5,033，覆盖 467 个 winner（全部 winner 的 17.64%）；fast-fail 池仅 1,280，覆盖 114 个（4.31%）。即使单位污染率相同，false-repair 的拒绝决策**暴露在 4.1 倍多的 winner 面前**。
3. **fast-fail 的安全部分来自"体量小 + 射程窄"**，不全是"结构上更可分"。
4. **validation 对两个 label 都塌**（2% 级 vs train/rob 的 9–13%），强烈提示 validation 崩溃含相当比例的 **regime + power artifact**（分子仅 5、20 个 winner），不是 false-repair 独有的结构罪。

### 3.3 第三轮：score-layer 富集检查 —— 定位到 score 且仅 OOS 发作

label 是 winner-稀释的，不代表被 rejector 实际拒掉的子集也 winner-稀释。rejector 按 score 拒 top-k，需直接看 `P(winner | 被10C拒)`。

口径：`full / keep_9000`，逐行拒绝计数取自 `winner_retention_audit.csv`，随机同量拒的期望命中率 = 该 split admitted 池 base rate。

| split | rej_winner_n | rejected_n | **P(win\|10C拒)** | base rate | **lift vs random** |
|---|---:|---:|---:|---:|---:|
| train | 155 | 832 | **18.63%** | 17.92% (1491/8318) | **+0.71pp** |
| validation | 39 | 252 | **15.48%** | 6.40% (161/2514) | **+9.08pp** |
| robustness | 128 | 497 | **25.76%** | 20.02% (995/4970) | **+5.74pp** |

过度拒绝倍率（winner 被拒比例 / 整体 10% 拒绝预算）：

| split | winner 被拒比例 | 整体拒绝比例 | **过度拒绝倍率** |
|---|---:|---:|---:|
| train | 155/1491 = 10.4% | 10.0% | **1.04x** |
| validation | 39/161 = 24.2% | 10.0% | **2.42x** |
| robustness | 128/995 = 12.9% | 10.0% | **1.29x** |

**关键签名：** train 行 `P(win|拒)=18.63% ≈ base rate 17.92%`（倍率 1.04x，几乎完全中性）—— 在 train 上 score 根本不富集 winner。但搬到 validation，score 把 winner 按 **2.42x** 往拒绝端塞（命中率从随机 6.40% 抬到 15.48%，+9.08pp）。

**这不是 label entanglement，是 boundary transport failure：** 模型在 train 上学到的 false-repair 决策面在 train 上避得开 winner，但泛化不出去，搬到 OOS 后漂移到 winner 富集的方向。winner 与 false-repair 在 t0 特征里不是天然重叠（train 能分开），而是**分界面不稳定，OOS 一抖就压到 winner 上**。

### 3.4 第四轮：决策面方向漂移 + E1-missed 集中度（机制锁定）

**检查 A —— reject_fraction 是否漂？** 取 `false_repair_threshold_frontier.csv`（full / keep_9000）：

```text
oos_rejected_fraction_spread          = 0.000239   （万分之二）
train_cv_selected_reject_fraction_std ≈ 1e-4 量级
```

拒绝**量**稳如磐石，三个 split 都是 ~10%。**排除阈值标定问题**，锁定为"同一 10% 预算落到的人不同" —— 拒绝量不漂，拒绝方向漂。

**检查 B —— 被拒 winner 是否集中在 E1-missed？** E1-missed 过度拒绝倍率（full / keep_9000）：

| split | winner 过度拒绝 | **E1-missed 过度拒绝** | E1 retention |
|---|---:|---:|---:|
| train | 1.04x | **1.57x** | 84.34% |
| validation | 2.42x | **4.22x** | 57.81% |
| robustness | 1.29x | **2.10x** | 79.05% |

被拒 winner 中 E1-missed 占比：

| split | 被拒 winner | 其中 E1-missed | **占比** |
|---|---:|---:|---:|
| train | 155 | 127 | **82%** |
| validation | 39 | 27 | **69%** |
| robustness | 128 | 101 | **79%** |

E1-missed 在**每个** split 都比"winner 整体"被杀得更狠（OOS 尤甚，validation 4.22x）。模型杀掉的 winner 约 **70–82% 是 E1-missed** —— 早期被甩下车、需回踩再上的大赢家。

---

## 4. 锁定结论

把四轮拼起来，定位完全锁死：

1. **label 无罪** —— false-repair 正类 winner-稀释（9.28%），标签构造不偏向 winner。
2. **拒绝量无罪** —— OOS reject_fraction spread 万分之二，阈值标定稳定。
3. **罪在决策面方向 + 精准打到 E1-missed** —— 模型在 OOS 把"早期回踩/假摔"判成 false-repair，而早期回踩正是 E1-missed winner 的物理特征。score 不是抽象地"混淆 winner"，它系统性地把**一类特定 winner —— 早期 shakeout 型 —— 误判成假修复**。

这是最初 horizon 直觉的**正确版本**：不是"20d label 整体混 winner"，而是 **"20d false-repair 的判定窗口恰好覆盖 E1-missed winner 的 early shakeout 区间，t0 特征在 OOS 分不开这两者"**。fast-fail（10d）避开这个区间所以安全 —— 不只是体量小，是 10d 太短、还没走到 shakeout，物理上够不着 E1-missed winner。

---

## 5. 对方向选择的硬含义

### 5.1 对 Gate-0（10D §6）

- **必须上多折 walk-forward**，不能只看单一 validation 窗口 —— 该窗口 winner 极稀薄（2.8%），会误导出错误的 entangled / separable 判定。
- **必须按 E1-missed 单独测可分性**，而非全 winner 混在一起。真正要测的是"E1-missed winner 的 early shakeout vs 真 false-repair 在 t0 是否可分"。基于上述证据，预期 OOS 不可分。

### 5.2 对 10D Track A relabel

10D Track A 的 `false_repair_non_winner = false_repair AND NOT winner_120` 在 **label 层**把 winner 抠掉，但伤害来自 **OOS 的 score 方向漂移**。relabel 后决策面在 OOS 照样会漂到 E1-missed 上（early shakeout 信号仍在特征里，且与真 false-repair 不可分）。**预期 10D 大概率仍 OOS block**，与需求 §6.3 / §17 的 `feature_source_supported` fallback 一致。

### 5.3 winner 保护应下沉到 exit 层（主推方向）

E1-missed = 早期被甩、回踩再上。这类 winner 在 **t0 entry 层天然分不出来**（当下看就是在跌/假摔），只有**让它走一段、用 t+k path 信息**才能区分"回踩后续涨"与"真 false-repair 后续死"。这精确指向 ep2/ep4 的 holding-exit / continuation 线（`requirement_04_holding_exit_winner_capture_extension`、`requirement_05_daily_continuation_profit_protection_policy`），而非 entry rejection。

### 5.4 Big Winner 应保留 endpoint 定义，但新增 path archetype

当前 `winner_120` 本质是简单的 **时间 + 结果** endpoint label：在 120d horizon 内是否达到 big winner 结果。这个定义仍应保留为主 KPI / retention denominator，因为它简单、可审计、与最终经济目标一致。

但 10C 的失败说明：`winner_120` 不是同质类。false-repair rejector 不是平均地伤害所有 winner，而是集中伤害 **E1-missed / early shakeout** 这类路径。也就是说，"直线型大赢家"与"先假摔、回踩、再走出的大赢家"在 endpoint 上同为 winner，但对 entry rejector 的风险完全不同。

因此应新增 secondary path label / readout，而不是替换主 winner label：

```text
winner_120                         # 主 endpoint label，继续作为 KPI / retention 分母
winner_path_archetype_v0           # secondary diagnostic / policy label
```

初步可执行定义已拆到 `big_winner_archetype_diagnostic.md`。该定义只是 v0 diagnostic draft，不是冻结 requirement；其中阈值必须先用现有 forward-path 数据做分布、覆盖率、类别重叠、OOS 稳定性、以及 10C rejected-winner concentration 统计后再最终敲定。

纪律边界：`winner_path_archetype_v0` 使用未来路径信息，**不得作为 t0 entry rejector predictor**。它只能用于：

1. 诊断：看被 10C / 10D 杀掉的 winner 集中在哪种 path；
2. 分层 retention：按 path archetype 分别算 winner injury；
3. 目标工程：对 `shakeout_reversal_winner` / E1-missed winner 给更高保护权重；
4. exit / continuation：等 t+k path 信息出现后，再判断是真 false-repair 还是 shakeout winner。

对 10D / Gate-0 的直接含义：不要只测 `injury winner vs clean false-repair`，而要重点测：

```text
E1-missed / shakeout-reversal winner
vs
true false-repair non-winner
```

如果这组在 t0 特征空间不可分，就基本坐实：问题不应继续用 entry rejector 硬切，而应转向 staged entry + path-dependent continuation / exit。

---

## 6. "feature 增补后 OOS 仍崩" 的后续方向（decision tree）

若 Gate-0 判不可分、且 09B feature extension 后 OOS 仍崩，按以下顺序推进（先证伪"崩溃是真的"，再谈范式重构）：

```text
A. 先证伪"崩溃是真的"（最便宜，必做）
   - power：给 retention 配 Wilson / bootstrap CI（validation 仅 64 个 E1-missed）
   - 单周期 regime：purged + embargoed walk-forward 多折，看是否只某一折崩
   - Bayes-error 直测：kNN / 互信息 / KDE overlap 估两类可分上限
     ├─ 崩溃非真（power/单周期） → 回 A，多折 + regime-conditioning
     └─ 真天花板 ↓

B. 决策从 t0 挪到 t+k（最强方向）
   - 放弃 t0 不可逆二分，改 staged 小仓进 + path-dependent 早退（optimal stopping）
   - 对接 ep2/ep4 holding-exit / continuation

C. 不预测 label，直接优化经济目标
   - maximize E[net_MFE | action] s.t. winner suppression ≤ cap（cost-sensitive / policy learning）

D. 重定义 label 使其与 winner 构造正交
   - 从标注阶段用 triple-barrier 把 winner 分支切走，而非事后 AND

E. 条件化到可分子总体（按 sector / 流动性 / regime / family 切，其余 abstain）

F. conformal selective prediction（仅当 uncertainty OOS-stable）

G. 引入新数据模态（日内微结构 / 真实 order flow / 龙虎榜 / 板块联动），非同源再派生

H. 诚实负结论：撤 rejector 层，只留 10B + 下游 exit 风控，冻结为 frozen negative result
```

推荐优先级：A → （B + D）→（C / E）→ F → G → H。

---

## 7. 待办的只读验证（不改任何产物）

1. **多折 walk-forward 下的 Gate-0**：单 validation 窗口不足以判 separable / entangled。
2. **E1-missed 专项可分性探针**：injury 限定 E1-missed early shakeout vs 真 false-repair。
3. **Bayes-error / 互信息直测**：在最佳可用特征空间估两类可分上限，区分"信息天花板"与"模型/正则/样本问题"。
4. **retention 的 Wilson / bootstrap CI**：扣掉 validation 的 power/regime artifact 后再谈"结构性失效"。
5. **Big Winner path archetype 只读分型**：保留 `winner_120` endpoint 主 label，新增 path readout，检查 10C rejected winner 是否集中在 `shakeout_reversal_winner` / E1-missed 路径。

---

## 附：关键数字速查

- 总样本 `15,802`，winner `2,647`，总体 winner rate `16.75%`
- `P(winner | fast_fail_10d+)` = 8.91%（114/1,280）
- `P(winner | false_repair_20d+)` = 9.28%（467/5,033）
- 10C full/keep_9000 被拒 winner：train 155 / val 39 / rob 128
- 被拒 winner 中 E1-missed 占比：train 82% / val 69% / rob 79%
- OOS reject_fraction spread：0.000239（拒绝量稳定）
- winner 过度拒绝倍率：train 1.04x / val 2.42x / rob 1.29x
- E1-missed 过度拒绝倍率：train 1.57x / val 4.22x / rob 2.10x
