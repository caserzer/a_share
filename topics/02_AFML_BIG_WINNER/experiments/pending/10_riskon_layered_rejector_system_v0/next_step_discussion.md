# Next-Step Discussion: 从 Archetype Profiling 到可执行 Proxy 验证

decision: `archetype_proxy_robust_payoff_risk_audit_design_frozen`

> 本文档记录从 `big_winner_archetype_profiling_report.md` 出发，经过多轮评审迭代，最终把"下一步该做什么"收敛成 `11A1` 实验设计的完整讨论过程、背景与结论。
> 讨论的核心转折是：**archetype 不是系统规则，而是 hypothesis generator；任何放行/保护规则在进入策略之前，必须先在 full candidate denominator 上通过稳健的 payoff-risk 验证。**

---

## 0. 结论摘要（TL;DR）

1. **Archetype profiling 报告只支持 readout，不支持冻结 archetype。** 它只回答 `P(archetype | winner)`，回答不了系统真正需要的 `P(winner | proxy)` / `P(failure | proxy)`。
2. **下一步不是写 archetype-specific 的 entry/exit 规则**，而是先做一个 full-denominator 的 proxy payoff-risk 验证实验：`11A1_archetype_proxy_robust_payoff_risk_audit`。
3. **主指标不是 winner lift，也不是 raw mean EV**，而是 robust median-based payoff-risk package（右尾捕捉 + 失败暴露 + 假修复暴露 + top-k 敏感性 + matched-base + proxy 去重 + rejected-subpopulation 验证 + exposure-day 归一）。
4. **系统架构从 `event → rejector → entry` 升级为分层保护 + 分级建仓 + observed-state 退出**，但 archetype 只进入 offline 诊断 / sizing / exit 假设，永不直接进入 buy signal。
5. **应停止继续评审，开始运行。** 无条件版本的 11A1 今天即可跑；用真实数据驱动后续设计，而不是用想象再迭代一轮方法论。
6. **三条诚实条款必须预注册**：(a) override 子群欠功率则整体搁置；(b) 0 proxy 通过时的预注册结论先写死；(c) denominator 必须包含退市/ST 否则左尾失真。

---

## 1. 背景

### 1.1 起点

讨论起点是只读统计报告 `outputs/publishable/reports/big_winner_archetype_profiling_report.md`。该报告在 PIT executable universe 内对 big winner 的 forward path 形态做了 profiling，关键事实：

- 主分母是 PIT-filtered winner，共 **3,075** 个（raw 09A winner candidate 7,187 个，PIT 过滤掉 57.21%）。
- big winner 不是单一快涨形态：`day_to_target` 中位数 58 个 session，p90=107；只有 11.87% 在 20 日内达到 +50%，25.04% 落在 90–120 日。
- risk_on winner 更像"深回撤后兑现"：target 更慢、pre-target drawdown 更深、touch failure lower rate=47.24%（risk_off 仅 25.84%）。
- seed flags 高度重叠：20.10% winner 无任何 seed，41.98% 命中一个，37.92% 命中两个及以上。
- 10C rejected winners 集中在 shakeout / volatile chop / gap-event，injury concentration lift 分别为 0.2529 / 0.1930 / 0.1881。
- 报告自我设限：path metrics 全部是 forward、t0 不可见，只能用于 label repair / post-hoc profiling，**不能作为 entry/rejector 特征**。

### 1.2 原始问题

最初的三个问题是：

1. 按这种统计情况，big winner archetype 怎么设计比较好？
2. 如果直接舍弃 p25 以下的情况会不会比较好？
3. 对整体系统设计有什么建议？

随后讨论从"如何分类"逐步打穿到"archetype 根本不能直接驱动规则"，并经过 4 轮评审把下一步实验设计收敛清楚。

---

## 2. 讨论过程（按轮次记录）

### 2.1 第 0 轮：三个原始问题的回答

**Q1 archetype 怎么设计：**

- seed flags 高度重叠，不是 taxonomy → 任何互斥单标签分类从一开始就是错的。
- path metrics 是 forward、t0 不可见 → 只能描述 winner 如何兑现，不能作入场判据。
- 结论：双层 archetype（**Outcome 后验层**用于 label repair / 诊断；**Entry 决策层**只用 t0 可见特征），outcome 层用 multi-label 而非 priority single-label，先做冗余压缩（timing / drawdown / ignition 三个 family），regime 作为一级轴。

**Q2 砍 p25：**

- 不建议。若按 forward 指标砍是 lookahead；若按"只保留兑现快/回撤浅"砍，会系统性删掉 25% 的 late realization winner 和 risk_on winner（36% winner 触及 ≤ -8% drawdown）。
- big winner 是稀有 + 非对称任务，召回比精度值钱，无差别砍 p25 是用召回换精度，方向反了。
- 替代方案：regime-conditional segmentation，而非全局截断。

**Q3 系统建议：**

- 分离 post-hoc 与 t0 维度；rejector 阈值 regime-aware；10D 定向修复；保住 PIT 纪律；validation 不驱动阈值；显式建模 precision/recall/coverage 目标；保留 regime source 审计。

### 2.2 第 1 轮评审：分层系统设计草案

用户提出把架构从 `event → rejector → entry` 升级为：

```
event
  → archetype-aware protection / rejector
  → staged entry
  → confirmation / continuation
  → archetype-aware exit / sizing
```

并给出五条建议：rejector 变 archetype-aware（按 archetype 报告 retention）、fast-fail ≠ 浅止损（区分 destructive failure 和 constructive shakeout，引入 `shakeout_safe_failure_proxy`）、entry 必须 staged、不同 archetype 对应不同 exit/stop、archetype 用于保护而非直接买入。

**评审意见（关键反驳）：**

1. **致命假设：报告只有 winner 分子，没有 loser 分母 → 给不了 precision。** 每条"保护性放松"都在用召回换精度，但无法量化放进了多少坏样本。
2. `shakeout_safe_failure_proxy` 是最容易混入 lookahead 的地方；constructive vs destructive 在早期部分不可判定，必须配硬结构底线。
3. regime 在 t0 是否真可见存疑（22.47% 来自 event fallback）。
4. retention gate 要 power floor + CI，且只在 train+robustness 上算。
5. staged entry 先做 2 阶段，避免过拟合；要纳入 A 股涨跌停可成交性。
6. exit 不能 key 在"真实 archetype"上，要 key 在 observed state 上。
- 锚点：第 9 条（archetype 用于保护而非买入信号）是整套设计的正确锚点，必须守住。

### 2.3 第 2 轮评审（v2）：吸收为"hypothesis generator"框架

用户吸收评审，把下一阶段从 `archetype-aware system design` 改为：
`winner-only profiling → 提出保护假设 → full-denominator precision 验证 → 通过后才进入 policy replay`。
并提出 `11A1_archetype_proxy_precision_base_rate_audit`，三层 proxy 分类（t0 可见 / early-path / retrospective），硬结构底线，regime PIT 审计前置，非歧视 retention gate，2 阶段优先，组合层 + 执行可成交性，observed-state exit。

**评审意见（仍未堵的洞）：**

1. **winner lift 不足以支撑非对称任务**：proxy 可 lift<1 但 EV 为正，也可 lift>1 但 EV 为负（同时富集 big winner 和 big failure）。主输出应是 payoff-weighted 的联合分布。
2. 多重检验纪律要加在 11A1（proxy-fishing 的真正发生地），不只是 11B。
3. denominator 是一个自由度，必须冻结 + PIT + 和上游 `hard_failure_first_blocks_winner` conditioning 对账。
4. category-B proxy 必须专门对 `false_repair` 验证，而非 `P(winner)`。
5. regime 不该硬 block 11A1；无条件版本可先跑，regime 分层标 provisional；regime 还要测 real-time 翻转稳定性。
6. staged entry 缺组合层成本。
7. 需要预注册 acceptance 判据。

### 2.4 第 3 轮评审（v3）：吸收为 payoff-risk 联合审计

用户把主指标从 winner lift 改为 payoff 联合分布，denominator 写成正式 contract + hard-failure reconciliation 表，预注册 ≤8 个 proxy family，两段确认（train freeze / robustness confirm / validation readout），category-B 对 false_repair 验证，regime provisional + real-time stability，组合层 replay，预注册 acceptance 判据。

**评审意见（洞集中在 EV 这个估计量本身）：**

1. **肥尾下 `mean(forward_return)` 被极少数名字主导** → 必须 trimmed/winsorized + top-k removal 敏感性 + instrument/episode bootstrap；median-based 联合判据设为主判据，raw mean EV 设辅助。
2. 11A1 量的是被动 proxy EV，不是策略 EV（真实系统有 fast-fail exit）→ 11A1 只 screen，11C 才给策略 EV。
3. base 必须 time/regime matched，否则 proxy lift = 择时假象。
4. 8 个 proxy 不独立（drawdown family Spearman 0.94–0.9999，seed 重叠 37.92%）→ 先做 co-occurrence + conditional incremental value。
5. **§7.1 acceptance 判据写串台**：把 failure rate 和 retention ratio 混了，是 category error → 11A1 proxy 接受门与 11B 非歧视门必须分离。
6. override 必须在 rejected subpopulation 里证明，且那里 power 很低。
7. 补充：label 版本冻结；EV 做 capital efficiency 归一（EV / exposure-day）。

### 2.5 第 4 轮评审（v4）：robust payoff-risk contract 成型

用户把 11A1 定名为 `11A1_archetype_proxy_robust_payoff_risk_audit`，主指标改为 robust payoff-risk package，明确：

- 主判据 = median right-tail capture + failure exposure non-worsening + top-k sensitivity + matched-base advantage；raw mean EV 仅 secondary。
- top-k 按 instrument/episode 删（非 event row）；bootstrap 用 block/episode-level。
- 11A1 只是 passive proxy screen，不 claim 策略 EV。
- matched base（time-block + denominator matched 为 primary，regime-matched provisional）。
- proxy overlap audit + conditional incremental readout。
- 11A1 proxy acceptance gate 与 11B protected retention gate 彻底分离（修正 category error）。
- override 在 rejected subpopulation 验证 + power floor。
- label / denominator / proxy 全部冻结并 hash；hard-failure reconciliation。
- EV capital efficiency 归一。
- 主判据 A–G 七条 + 角色边界（11A1 screen，11C 才出策略 EV）。

**评审意见（元判断 + 三条诚实条款）：**

1. **应停止评审，开始运行。** 这是第四轮，边际收益接近零；继续打磨方法论本身正在变成拖延。无条件 11A1 今天即可跑，真实数据比第五轮评审更有信息量。
2. **洞 1（可能致命）：override 这条线很可能 power 上死掉。** rejected winner 只有 105 个，按 8 proxy × split 拆几乎全 low_power → 必须预注册"欠功率则整体搁置"，不得事后松 floor。
3. **洞 2（过度保守的反面风险）：7 重 AND gate 可能把真信号也杀光。** 失败模式已从假阳翻转成假阴 → 区分 hard veto（A/C/D）与证据强度评分；预注册"0 proxy 通过时的结论"。
4. **洞 3（新增数据完整性洞）：退市/ST 幸存者偏差。** st 只有 3 个可疑，若 denominator 不含退市/ST，左尾被系统性低估、EV 高估 → 必须校验分母含退市/ST 且其 forward path 有定义。
5. 提醒：MFE 是 capturable 上界、非可兑现收益，不应在 11A1 阶段主导排序。

---

## 3. 最终结论：系统设计原则

```
1. Winner lift is secondary.
2. Raw mean EV is secondary.
3. Robust median-based payoff-risk is primary.
4. Proxy must beat matched base, not global base.
5. Proxy advantage must survive top-k removal.
6. Proxy clusters must be de-duplicated.
7. Override must be proven inside rejected subpopulation.
8. Category-B proxy must reduce false-repair.
9. 11A1 screens proxies; 11C tests strategy EV.
```

补充三条贯穿原则：

- **Archetype profiling is not a policy** —— 它是 hypothesis generator。
- **Regime-stratified findings are provisional** —— 直到 PIT 与 real-time stability 通过。
- **Stop reviewing, start running** —— 用真实数据驱动 v5，而非想象。

### 3.1 目标系统架构

```
Event source
  ↓
Density / execution rule
  ↓
Fast-fail structural safety gate
  ↓
Trial entry (small)
  ↓
Observed-state monitor: reclaim? confirm? failure? liquidity executable?
  ↓
Upgrade / hold / exit
```

archetype 不进入 buy signal，只进入：offline protected readout / policy diagnostic / sizing / exit hypothesis。

### 3.2 三层 proxy 分类（防 lookahead）

| 类别 | 用途 | 示例 | 可用时点 |
|---|---|---|---|
| A. t0 可见 proxy | entry-time feature | prior_20d_pullback_depth, long_lower_shadow_count, close_position_in_range, ATR/volume spike before t0 | t0 |
| B. early-path proxy | upgrade/hold/no-exit 再决策 | reclaim EMA20, reclaim event low, 放量下跌后缩量, DIB 转正 | t0+3 / t0+5 / t0+10 |
| C. retrospective label | 仅 profiling，不得上线 | deepest_pre_target_ret_low, max_drawdown_to_target, day_to_target, future MFE | 事后 |

---

## 4. 最终结论：11A1 实验 contract

实验命名：`11A1_archetype_proxy_robust_payoff_risk_audit`

**目标：** 在 full PIT candidate denominator 上，验证预注册 proxy 是否在稳健的 payoff-risk 分布上优于 matched base，并确认该优势不由少数极端名字、时间/制度择时、proxy 共线或 rejected-subpopulation power 不足造成。

### 4.1 主输出

```
1. denominator / label / proxy contract audit (含 hash)
2. hard-failure conditioning reconciliation
3. proxy coverage and matched-base rates
4. robust payoff-risk readout
5. top-k removal sensitivity
6. bootstrap CI (instrument/episode block)
7. proxy overlap / clustering
8. conditional incremental value
9. rejected-subpopulation override readout
10. acceptance summary
```

### 4.2 主判据（proxy 进入 11C 的条件）

```
A. pre-registered and PIT-valid                         [hard veto]
B. coverage pass
C. matched-base robust payoff-risk pass:                [failure 部分为 hard veto]
     median right-tail capture non-inferior or better
     big_failure not worse
     false_repair not worse
     EV_per_exposure not worse
D. top-k sensitivity pass:                              [hard veto]
     remove top 1/3/5 instruments still non-negative advantage
E. bootstrap stability pass:
     no severe deterioration under episode/instrument bootstrap
F. proxy overlap check:
     unique cluster representative OR conditional incremental value pass
G. if used as override:
     rejected-subpopulation power pass AND advantage holds in rejected subset
```

注：A / C(failure) / D 作为 hard veto，其余作为证据强度评分而非生死门，避免在小样本下把真信号杀光。

### 4.3 主指标包（每个 proxy 必须输出）

```
raw_mean_return            (secondary)
winsorized_mean_return
trimmed_mean_return
median_forward_return
median_MFE / median_MAE
P(winner_120) / P(big_failure) / P(false_repair_20)
EV_per_exposure_day
top_k_removed_EV (by instrument/episode)
bootstrap_CI_by_instrument_or_episode
```

主判据用 median-based right-tail capture + failure exposure + top-k + matched-base；raw mean EV 仅 secondary readout。

### 4.4 冻结项（hash 化）

```
labels_yaml_hash
candidate_denominator_hash
proxy_definition_hash
label_contract_hash
```

冻结 label：winner_120, big_failure, false_repair_20, confirm_20, failure_10, MFE/MAE horizon, cost assumption, execution assumption, hard_failure_first_blocks_winner。

### 4.5 Denominator contract

```
primary denominator:   R-core post-density PIT candidate population
secondary readouts:     E1 baseline / R6 readout-only / pre-density R-core diagnostic
```

- 看 outcome 前冻结，主判据只认一个 primary，不能事后挑最有利的 denominator/base。
- 必须和 hard-failure conditioning 对账（把 hard-failure-first candidate 放回分母）。
- primary base = time-block + denominator matched；regime-matched base 在 11A0 通过前标 provisional。

### 4.6 预注册 proxy（≤8 family）

```
P1_gap_event_proxy
P2_shakeout_prior_path_proxy
P3_volatile_chop_proxy
P4_early_momentum_proxy
P5_late_bloomer_proxy
P6_clean_repair_proxy
P7_flow_confirmation_proxy
P8_recurrence_density_proxy
```

每个 proxy 写清：feature fields / threshold / available time / category (t0 / early-path / retrospective)。看 outcome 后不得新增 proxy。

---

## 5. 必须预注册的三条诚实条款（运行前写死）

1. **Override 欠功率处置**：若 override 子群欠功率（rejected winner 仅 ~105 个，多数 cell 必然 low_power），protection-override 这条线整体搁置，proxy 仅保留为 full-denominator screen 结论，不进入 rejector override。**不得通过降低 power floor 来"救活"override。**

2. **0 proxy 通过的预注册结论**：若 0 个 proxy 通过主判据，预注册结论是"archetype 保护方向在当前数据下不可行，回到单层 rejector / readout-only"，而非事后放宽 gate。

3. **Denominator 完整性（退市/ST）**：full candidate denominator 必须保留 horizon 内退市/ST/停牌的 candidate，且其 forward path 有定义（退市按归零或最后可成交价处理）。否则 payoff-risk 左尾失真、EV 系统性高估。（报告 §2 board buckets 中 st 仅 3 个，可疑，必须校验。）

---

## 6. 下游实验排序

| step | 名称 | 目标 | 依赖 |
|---|---|---|---|
| Step 0 | `11A0_regime_pit_availability_audit` | 确认 risk_on/off/transition 在 t0 因果可得，并测 real-time 翻转稳定性 (flip_rate_5d/20d, confirmation_lag, regime_age, confidence) | 可与 11A1 无条件版并行 |
| Step 1 | `11A1_archetype_proxy_robust_payoff_risk_audit` | winner-only profiling → full-denominator robust payoff-risk screen | 无条件版无依赖，可立即跑 |
| Step 2 | `11A2_shakeout_proxy_pit_causality_audit` | 区分 t0 / early-path / retrospective 特征，对 category-B 验 false_repair 削减 | 11A1 |
| Step 3 | `11B_archetype_protected_retention_readout` | rejector 非歧视约束（relative retention + power floor + CI） | 11A1 |
| Step 4 | `11C_portfolio_aware_two_stage_policy_replay` | 唯一计算策略 EV 的地方：单票 + 组合层 + 执行可成交性 | 11A1/11A2/11B |

11C 必输出（除单票 MFE/MAE 外）：capital utilization, active/trial position count, upgrade fill rate, turnover, transaction cost, exposure-days, gross/net exposure, max concurrent positions, sector/board concentration, cash drag, capacity, limit-up unfilled rate, limit-down exit failure rate；gap/event proxy 单独看 upgrade executable rate / gap slippage / limit-up chain blockage。

---

## 7. 关键边界声明

```
11A1 outputs proxy diagnostic only.
It does not authorize entry policy.
It does not claim strategy EV.
Strategy EV is only computed in 11C (entry timing + size + fast-fail exit
+ upgrade + cost + limit-up execution + exposure-days + portfolio capacity).
```

---

## 8. 最终判断与下一动作

- 方法论已经收敛，不需要 v5 评审。v4 contract + 第 5 节三条诚实条款已具备运行所需的全部纪律。
- **下一动作：把 11A1 写成可执行 requirement spec（denominator/label 冻结 contract、8 个预注册 proxy 字段+category+阈值模板、hard-failure reconciliation 表 schema、payoff 联合输出表含 trimmed EV / top-k 敏感性 / bootstrap CI / EV-per-exposure-day、分离后的 11A1 接受门 + 11B 非歧视门），然后跑无条件 11A1。**
- 用真实数据（很可能直接砍掉一半 proxy）驱动后续设计，而不是再迭代一轮想象中的方法论。

> 最关键的一句话：**Winner archetype profiling 只能告诉你"哪些 winner 容易被误伤"，不能告诉你"哪些 candidate 值得放行"。放行规则必须先经过 full-denominator robust payoff-risk 验证。**
