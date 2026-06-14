# 08 Risk-on / Transition 全实验最终报告

## 0. 报告定位

本报告汇总 `08_risk_on_transition_recall_exploration_v0` 下已经形成 publishable decision 的全部实验、补丁与诊断报告。它不是新的模型训练结果，也不替代各实验自己的 manifest；它的作用是把 08 从最初的 risk_on / transition 召回修复，整理成一条可复核的研究旅程，并给出当前阶段的综合判断。

覆盖范围：

- 08 主实验：`risk_on_transition_recall_exploration_report.md`
- R-series density compression patch
- episode interval density diagnostic
- Experiment A：10d density / fast-fail audit
- Experiment B：regime x event-family performance matrix
- Experiment C：risk-on / transition R-series bridge-positive ranker
- Experiment D：post-replay event-to-episode retention source
- Experiment E：risk-on post-filter cost rejector
- Experiment F：transition sub-regime taxonomy audit
- Experiment G：previous-regime conditioned transition outcome audit
- Experiment H：risk-on cost rejector research-entry hardening
- Experiment I：transition previous-regime context cost rejector ablation

`requirement_patch_regime_specific_unions.md` 等需求文件没有独立 publishable decision/report，本报告只把它们作为 B/C 后续设计背景，不把它们列为单独实验结论。

本报告的综合判断是：

```text
risk_on：召回源足够，真正瓶颈是 cost / fast-fail / false-repair 排序质量；当前 cost rejector 有稳定 OOS 信号，但尚未达到 research-entry。
transition：当前 residual transition label 下不应继续 family rediscovery；问题主要是状态桶混合、样本段 power 不足、OOS 子状态不可复现。
```

## 1. 背景

08 的背景来自 06 / 07 两个前置事实。

第一，06 冻结了 big-winner episode denominator：`mfe_120 >= 50%` target episodes 共 `2,493` 个。该 denominator 来自 Top-N / proxy universe，可用于 local proxy research，但不能解释成 exact historical top 400/100 全市场结果。

第二，07 证明 E1 是最可靠的 candidate backbone，但它在 risk_on / transition 中仍有明显漏召回。07 E1-only 捕获 `1,773 / 2,493` 个 target episodes，before-first-50pct recall 为 `71.1%`，bridge recall 为 `32.6%`；E1 本身非常稀疏，canonical event `6,820` 个，10d rolling duplicate rate 只有 `0.19%`，fast-fail 10d 为 `14.52%`。它的问题不是过密，而是覆盖不足。

08 的原始问题因此很明确：在不破坏 E1 稀疏性和可执行性的前提下，寻找能补 `risk_on` / `transition` missed episodes 的候选事件或过滤机制。

整个 08 过程逐步把问题拆成三层：

1. 候选生成层：是否存在能找回 missed episodes 的 event family。
2. 密度与执行层：这些事件是否在 executable event-day / rolling 10d 口径下可控。
3. 质量成本层：是否能在 OOS 中降低 10d fast-fail / 20d false-repair，同时保留 bridge-positive / E1-missed capture。

最终答案不是“08 找不到信号”，而是更细：risk_on 找到了召回和成本排序信号，但还没达到 research-entry；transition 不是同一个问题，当前 residual label 不支持继续当单一可交易状态建模。

## 2. 实验决策总览

| 阶段 | 报告 / 实验 | 正式 decision | 主要结论 |
| --- | --- | --- | --- |
| 主实验 | Risk-on / Transition Recall Exploration V0 | `risk_on_transition_recall_exploration_density_blocked` | T4/T7 selected union 稀疏但 bridge 质量低，all-new union 证明有召回空间但太密。 |
| 补充诊断 | Event Density Episode-Interval Diagnostic | diagnostic report | R-core union 在同一 episode 内反复触发，risk_on episode 内 R gated count median `5`、相邻间隔 median `4` 日。 |
| Patch | Risk-on R-series Density Compression | `risk_on_r_series_no_compression_candidate` | R1/R2/R6/R7/R8 bridge 强但 deterministic compression 无法同时保 bridge 与 density。 |
| A | 10d Density / Fast-Fail Audit | `density_fast_fail_audit_partial_source_complete` | E1 10d 稀疏；T4/T7 不拥挤但 fast-fail 高；R-core union cross-family 拥挤严重。 |
| B | Regime x Event-Family Matrix | `regime_family_matrix_source_caveated_complete` | R-family 是强 pre-replay source；T4/T7 不能当 transition backbone；所有结论受 source caveat 限制。 |
| C | R-series Bridge-Positive Ranker | `risk_on_r_series_ranker_source_caveated_complete` | 63 个 arm 中 direct-entry pass `0`、feature-source pass `0`；risk_on 是质量成本问题，transition 是稳定性问题。 |
| D | Post-Replay Retention Source | `post_replay_retention_source_source_caveated_complete` | 补齐 event-to-episode membership；risk_on R-core/R6 post-replay recall 很强，transition robustness 塌陷。 |
| E | Risk-on Post-Filter Cost Rejector | `risk_on_cost_rejector_feature_source_caveated_supported` | cost rejector 有 OOS 信号，`keep_080` 近 research-entry，但有 admission contract 缺口。 |
| F | Transition Sub-Regime Taxonomy Audit | `transition_subregime_taxonomy_diagnostic_only` | transition 不是稳定第三态；boundary 过度吞没，robustness recovery core 为 `0`。 |
| G | Previous-Regime Conditioned Transition Outcome | `transition_previous_regime_conditioning_diagnostic_only` | previous-regime 有路径解释力，但 segment power / universe binding 不支持 taxonomy。 |
| H | Risk-on Cost Rejector Research-Entry Hardening | `risk_on_cost_rejector_diagnostic_only_or_no_candidate` | E 的契约缺口已补，OOS 排序稳定；同一 train-only 阈值仍无法同时过 cost 与 recall。 |
| I | Transition Previous-Regime Context Cost Rejector Ablation | `transition_previous_regime_context_cost_rejector_diagnostic_no_uplift` | previous-regime context 加入 transition cost rejector 后 OOS 弱于 no-context baseline。 |

## 3. 研究旅程

### 3.1 从“补召回”开始

08 主实验从 07 E1-only baseline 出发，尝试补 risk_on / transition missed episodes。主实验确实找到了候选空间：

- candidate event instances：`238,679`
- candidate canonical events：`90,576`
- selected canonical events：`2,063`
- selected density：`0.5695` events / instrument-year
- selected / E1 canonical count ratio：`0.3025x`
- selected next-open executable rate：`99.5%`
- selected 120d label completeness：`99.5%`

但是 selected union 只保留 T4 / T7 两个 gated variants，最终没有通过 graduation gate：

- T4 占 selected union 事件密度 `70.9%`，超过 `35%` family-share gate。
- selected union 的 bridge-positive recall 显著低于 E1，最差 split/regime 差值为 `-27.6 pct`。
- selected union 对 robustness risk_on 的 incremental recall 只有 `5.0 pct`，对 robustness transition 只有 `2.0 pct`。

这一步给出的第一条洞察是：risk_on / transition missed episodes 不是完全找不到事件；问题是低密度版本的 bridge 质量不够，高召回版本又过密。

### 3.2 R-series 证明“高召回源存在”，也暴露 density 和质量成本

R-series compression patch 把注意力转向 R1/R2/R6/R7/R8。preflight 结果显示，这些 family 在 risk_on 上具有明显的增量召回和 bridge signal：

| family | train incremental recall | train bridge delta | robustness incremental recall | robustness bridge delta | density vs E1 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R1 | 34.7% | +14.4% | 40.9% | +19.9% | 2.72x | 7.0 |
| R2 | 33.3% | +5.8% | 29.3% | +12.7% | 1.63x | 5.0 |
| R6 | 34.7% | +15.3% | 42.5% | +26.5% | 3.22x | 8.0 |
| R7 | 29.8% | +7.1% | 38.1% | +18.3% | 1.92x | 5.0 |
| R8 | 32.9% | +6.7% | 35.4% | +10.2% | 2.21x | 7.0 |
| R5 negative control | 4.9% | -22.7% | 2.2% | -27.1% | 0.33x | 5.0 |

R5 是关键反例：低密度本身不是好信号。R1/R2/R6/R7/R8 是真正的 high-bridge source，但 density / p95 / concentration 过高。

compression frontier 进一步证明 deterministic rule 解决不了问题：

- train recall pass：`24/24`
- train bridge pass：`19/24`
- density `<= 1.0x` pass：`1/24`
- p95 `<= 4` pass：`3/24`
- single-family share `<= 65%` pass：`13/24`
- 唯一 density pass 的 `consensus_family_count__min3`：density `0.45x`、p95 `2`，但 train bridge delta `-17.7 pct`。
- `cooldown_after_selected_event__40d` 保留 train bridge `+15.6 pct`、robustness bridge `+21.3 pct`，但 density 仍 `2.05x`、p95 `5`。

这一步把问题从“缺不缺召回源”推进为“如何在高桥接信号里筛掉成本和拥挤”。

### 3.3 A/B/C 把 density、regime 和 ranker 三个口径拆开

Experiment A 冻结了可执行事件日 + 10d fast-fail 口径，修正了早期把多种 density 混在一起的风险。

核心数据：

| scope | events | density / inst-year | p95 | rolling 10d dup | gap median | fast-fail 10d | false-repair 20d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 07_E1_only | 6,820 | 1.883 | 4.70 | 0.19% | 104 | 14.52% | 20.62% |
| 07_full_union | 15,161 | 4.185 | 10.85 | 29.60% | 15 | 16.33% | 23.13% |
| 08_selected_T4_T7_union | 2,063 | 0.570 | 1.53 | 3.73% | 167 | 35.19% | 39.07% |
| 08_R_core_event_regime_gated | 47,914 | 13.227 | 38.12 | 57.83% | 7 | 24.20% | 31.11% |
| 08_R6_event_regime_gated | 16,204 | 4.473 | 12.23 | 0.00% | 44 | 23.19% | 30.30% |

A 的结论是：E1 稀疏，T4/T7 不拥挤但质量差，R-core union 是 cross-family collision 过密，不是单 family 自己反复触发。

Experiment B 用 regime x family matrix 证明 R-family 的 pre-replay coverage 强，但不能直接解释为 post-filter trading signal。B 的关键判断是：

- E1 不是 density 失败，问题是 coverage。
- 07 full union 的增量召回太小但拥挤明显。
- T4/T7 稀疏但 recall / bridge 不够，不能作为 transition 默认假设。
- R-core union 高 recall 伴随严重 duplicate；R6 是 transition 中最值得观察的 candidate，但不是 entry support。

Experiment C 把 R-series 做成 train-only ranker / budget / cooldown / de-overlap arm，结果全部停在 diagnostic：

- arm/regime rows：`63`
- risk_on arms：`21`
- transition arms：`21`
- direct-entry pass：`0`
- feature-source pass：`0`
- selected event rows：`452,074`
- unique selected canonical events：`49,219`

C 的关键分化是：

- risk_on：bridge 覆盖真实，但 fast-fail / false-repair 成本压不下来。例如 risk_on R-core train bridge delta `+13.78pp`、robustness bridge delta `+19.34pp`，但 density/E1 `4.515`、rolling 10d duplicate `54.43%`、fast-fail excess `+12.86pp`。
- transition：不是单纯 density 问题，而是 robustness bridge 不成立。transition R-core train bridge delta `+1.98pp`，robustness bridge delta `-5.82pp`；压缩后 robustness bridge 仍为负。

这一步之后，08 的研究方向正式分轨：risk_on 走 cost rejector，transition 先审计 label / state，而不是继续做同一套 ranker compression。

### 3.4 D 补齐 post-replay membership，确认 risk_on 召回源足够

Experiment D 的价值是补齐 A/B/C 缺失的 event-to-episode post-replay retention source，而不是训练新模型。

关键产物：

- local raw membership：`357,450` rows
- episode window：`4,986` rows
- episode_window_ready：`4,986 / 4,986`
- dedup conflict：`0`
- C arm pre-replay reconciliation：`189 / 189` pass
- leakage audit：pass

D 的新证据把方向进一步分清：

- risk_on R-core post-replay recall 很强：train / robustness 为 `98.2% / 94.5%`。
- risk_on R6 post-replay recall 也强：train / robustness 为 `96.0% / 90.1%`。
- E1-missed 中，R-core 抓到 train `80 / 83`、robustness `84 / 92`。
- E1-missed 中，R6 抓到 train `77 / 83`、robustness `77 / 92`。
- transition R-core train / validation 很高，但 robustness 掉到约 `50.0%`，说明 transition 不是同一个稳定问题。

D 之后，risk_on 的核心问题不再是“是否有 recall source”，而是“怎样把 R-core/R6 的高召回源变成可控成本的候选集”。

### 3.5 E/H 证明 risk_on cost rejector 有信号，但没有 research-entry

Experiment E 训练 risk_on post-filter cost rejector，目标是用 t0 可见特征预测 `cost_bad_10_20`，即 fast-fail / false-repair 合成成本。E 选择 `supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_080`，结果接近 research-entry：

| split | sample n | prevalence | ROC-AUC | PR-AUC | top-decile lift |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 16,571 | 42.06% | 0.692 | 0.609 | 1.708 |
| validation | 4,455 | 31.45% | 0.682 | 0.493 | 1.939 |
| robustness | 9,711 | 32.22% | 0.686 | 0.524 | 2.021 |

selected `keep_080` 的 cost / recall：

| split | before cost | after cost | cost reduction | any recall retention | E1-missed retention |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 42.06% | 36.09% | 14.17% | 90.05% | 95.00% |
| validation | 31.45% | 28.55% | 9.21% | 72.73% | 61.54% |
| robustness | 32.22% | 25.62% | 20.48% | 86.55% | 84.52% |

E 没有通过 research-entry，原因是：

1. train cost reduction `14.17%`，低于 `15%`，差约 `0.83pp`。
2. `momentum_percentile_20d_lag20` train coverage `93.30%`，低于 `95%`。
3. density 可审计但上限未预声明。

Experiment H 是 E 的 hardening replay。H 删除 lag20 字段、补齐 density / concentration cap、要求所有 gate 指标来自同一 selected threshold。H 后，工程契约不再是主要问题：

- R-core label complete rate：`99.8643%`
- membership mismatch：`0`
- as-of future join rows：`0`
- model feature count：`53`
- allowed t0 feature 最大 missing rate：train `2.4464%`，validation / robustness `0%`
- robustness ROC-AUC：`0.6858`
- robustness PR-AUC：`0.5239`
- robustness top-decile lift：`2.0307`

但 H 仍然没有 research-entry，因为 train-only threshold grid 中没有同一个阈值同时满足 cost 与 recall：

| keep | train cost reduction | train any recall | train E1-missed retention | robustness cost reduction | robustness any recall |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.850 | 11.2350% | 90.9502% | 97.5000% | 17.0554% | 88.3041% |
| 0.825 | 12.5821% | 90.4977% | 96.2500% | 18.6244% | 88.3041% |
| 0.800 | 14.1389% | 90.0452% | 95.0000% | 20.4693% | 86.5497% |
| 0.775 | 15.3452% | 89.1403% | 93.7500% | 21.8745% | 84.7953% |
| 0.750 | 16.7917% | 88.6878% | 93.7500% | 22.9721% | 83.6257% |

核心边界非常窄：

- `keep_0800` 保住 train any recall `90.0452% >= 90%`，但 train cost reduction `14.1389%`，差 `0.8611pp`。
- `keep_0775` 达到 train cost reduction `15.3452% >= 15%`，但 train any recall `89.1403%`，差 `0.8597pp`。
- E1-missed retention 不是瓶颈，两个点都高于 `85%`。

因此 risk_on 线的正确结论是：监督式成本排序确实有效，但当前 feature / target / model 还没有把 `0.80` 附近的 frontier 推过 research-entry。下一步不能继续调 threshold，而要提升局部排序质量或重新设计 cost target。

### 3.6 F/G/I 证明 current transition label 不应继续推进

transition 的关键前提是：它不是正向定义的单一市场状态，而是 risk_on / risk_off 以外的 residual bucket。当前定义下，transition 混合了至少两类相反过程：

- recovery transition：趋势转正但仍处于较深回撤，更像 risk_off -> risk_on。
- deterioration transition：趋势转弱但尚未深回撤，更像 risk_on -> risk_off。

Experiment F 尝试把 transition 拆成 recovery / deterioration / boundary-or-mixed，并用 120d market-state rolling windows 做自动 taxonomy。结果停在 diagnostic-only：

- transition event assignment rows：`25,214`
- train / validation / robustness event count：`11,497 / 9,104 / 4,613`
- component source：`SH000985`
- date range：`2017-01-03` 至 `2026-05-29`
- component reconstruction consistency：`81.17%`
- train 名义 rolling windows：`230`
- 有效独立窗口约：`34.92`

默认 taxonomy 的核心失败：

| split | boundary event share | deterioration event share | recovery event share |
| --- | ---: | ---: | ---: |
| train | 79.2% | 15.0% | 5.8% |
| validation | 63.7% | 32.6% | 3.7% |
| robustness | 80.2% | 19.8% | 0.0% |

robustness recovery core 为 `0`，直接触发 `missing_core_subregime:robustness`。KMeans 虽然选 k=3，但三个 cluster 都退化为 boundary-like，block stability 失败，ARI `0.148`。F 的有用发现是 deterioration 在 robustness 上明显更脏：R-core fast-fail `24.5%`、false-repair `30.4%`，高于 boundary 的 `7.4% / 13.3%`。但这只是 risk readout，不是稳定 taxonomy。

Experiment G 从 previous non-transition regime 角度解释 transition path。结果显示前态有解释力：

- 已完成 outcome 的 transition segment：`113` 段。
- previous risk_off 后转 risk_on：`16 / 40 = 40.0%`。
- previous risk_on 后转 risk_off：`14 / 74 = 18.9%`。
- grid candidates：`400`
- structural eligible：`0`
- published transition not reconstructed share：`30.59%`

G 的问题不是 label leakage，而是 segment power。robustness conversion 只有 `3` 段，其中 risk_off -> risk_on conversion `1` 段，risk_on -> risk_off conversion `2` 段；top1 segment episode share 最高达到 `100.0%` / `93.8%`。episode count 看起来不少，但独立 transition 段太少，不能支持 taxonomy 或训练规则。

G 的最有价值 readout 是：

- robustness `from_risk_on / continuation` 很干净：R-core fast-fail `2.3%`、false-repair `5.3%`、big-winner `54.3%`。
- robustness `from_risk_on / conversion to risk_off` 很脏：R-core fast-fail `23.0%`、false-repair `29.0%`。

但 conversion / continuation 是 ex-post outcome，不能作为 t0 feature。

Experiment I 进一步验证：把 t0 可见的 previous-regime context 加入 transition cost rejector，是否能稳定改善 `cost_bad_10_20` 排序。结果是否定的：

- primary event_n：`26,840`
- cost label complete rate：`99.94%`
- future feature used：`0`
- model arms：no-context、prev-context、context-only

OOS separability：

| model | split | ROC-AUC | PR-AUC | top-decile lift | bottom-decile cost_bad |
| --- | --- | ---: | ---: | ---: | ---: |
| no_context | validation | 0.6804 | 0.5106 | 1.9536 | 0.1362 |
| prev_context | validation | 0.6530 | 0.4842 | 1.8229 | 0.1691 |
| context_only | validation | 0.4864 | 0.3162 | 1.0987 | 0.2758 |
| no_context | robustness | 0.6449 | 0.3352 | 1.5456 | 0.1248 |
| prev_context | robustness | 0.5895 | 0.3065 | 1.4646 | 0.2086 |
| context_only | robustness | 0.4173 | 0.2141 | 0.9347 | 0.3440 |

train 内部 segment-CV 看起来有 context uplift，但 validation / robustness 全面转负：

| split | ROC uplift | PR uplift | top-decile lift uplift | cost reduction uplift | any recall delta | E1-missed capture delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | +0.0194 | +0.0278 | +0.0878 | +0.0344 | -0.0197 | -0.0077 |
| validation | -0.0274 | -0.0264 | -0.1307 | -0.0110 | +0.0035 | +0.0200 |
| robustness | -0.0554 | -0.0288 | -0.0810 | -0.0421 | -0.0431 | -0.1039 |

I 的结论是：previous-regime context 可以解释 transition segment composition，但不能作为稳定 OOS event-level cost sorting feature。它不能并入 E/H 的 risk_on-only gate，也不能复活当前 transition 主线。

## 4. 详细发现

### Finding 1：E1 是 backbone，不是瓶颈

E1 在 08 中继续作为基准 anchor 成立。它的全样本 recall 已经达到 `71.1%`，bridge recall `32.6%`，而 rolling 10d duplicate 只有 `0.19%`。它不应该被更密的 full union 替代。

07 full union 相比 E1 只把 pre-replay any recall 从 `71.12%` 提高到 `72.04%`，bridge recall 从 `32.56%` 提高到 `34.75%`，但事件数从 `6,820` 增到 `15,161`，rolling 10d duplicate 从 `0.19%` 增到 `29.60%`。这说明“多加 family”不是好路线。

### Finding 2：08 主实验找到了信号空间，但 selected T4/T7 不是答案

T4/T7 selected union 的优点是稀疏：`2,063` canonical events，density `0.570`，p95 `1.53`，rolling 10d duplicate `3.73%`。但它的质量不足：

- fast-fail 10d：`35.19%`
- false-repair 20d：`39.07%`
- all/all recall：`17.61%`
- all/all bridge recall：`5.09%`
- robustness transition any recall：`12.00%`
- robustness transition bridge recall：`2.00%`

因此 T4/T7 只能作为 negative control / quality context，不应作为 transition recall backbone。

### Finding 3：R-core 是强 recall source，但不能直接 entry

R-core 的强项是召回和 bridge：

- risk_on D post-replay R-core recall train / robustness：`98.2% / 94.5%`
- risk_on E1-missed R-core capture train / robustness：`80/83`、`84/92`
- C 中 risk_on R-core robustness any recall：`87.29%`
- C 中 risk_on R-core robustness bridge recall：`54.14%`
- C 中 risk_on R-core E1-missed captures：`78`

R-core 的弱点是 density、duplicate 和成本：

- Experiment A R-core density：`13.227`
- p95 density：`38.12`
- rolling 10d duplicate：`57.83%`
- fast-fail 10d：`24.20%`
- false-repair 20d：`31.11%`

这就是 08 最核心的机制分解：R-core 不是坏 source，但它需要 supervised cost rejector / post-filter，而不是直接变成 entry union。

### Finding 4：risk_on 的 binding constraint 是 cost，transition 的 binding constraint 是 state stability

C 和 D 已经把 risk_on / transition 拆成两类问题。

risk_on：

- recall source 足够，robustness E1-missed capture 能维持 `72-78` 个级别。
- bridge recall 能维持 `47%-54%` 区间。
- blocker 是 fast-fail / false-repair excess 和 density / duplicate。
- E/H 证明 cost_bad 排序有 OOS 信号，robustness ROC-AUC 约 `0.686`，top-decile lift 约 `2.03`。

transition：

- R-core 在 train/validation 可能很高，但 robustness 会塌陷。
- C 中 transition R-core robustness bridge delta 为 `-5.82pp`。
- D 中 transition R-core recall train / validation 很高，但 robustness 只有约 `50.0%`。
- F/G/I 都证明 current transition label 不是稳定可训练目标。

因此，risk_on 可以继续做 feature / target construction uplift；transition 不应继续在当前 residual label 下做 family rediscovery。

### Finding 5：10d fast-fail 口径改变了整个评价框架

08 过程中最重要的口径修正是：density 不能只按 episode-window 或 full instrument-year 汇总来解释。

现在必须同时区分：

- full-denominator density：跨 scope 粗粒度比较。
- rolling 10d executable event-day density：同 instrument 的短期触发拥挤。
- episode-window density：解释一个 winner episode 内部事件重复触发。
- fast-fail / false-repair cost：事件质量成本，不是 t0 feature。

episode interval diagnostic 说明 R-core 在 episode 内非常密：

- E1 episode count mean / median：`0.80 / 1`
- R gated episode count mean / median：`4.69 / 5`
- risk_on R gated episode count mean / median：`5.27 / 5`
- risk_on R gated top 10% event count：`9`
- risk_on R gated adjacent gap median：`4` 个交易日

但最终 admission gate 不能直接用 episode-window hard gate，因为 episode 边界事后可知。正确做法是把它作为 diagnostic alert，同时坚持 executable event-day density 与 cost_bad OOS readout。

### Finding 6：transition 的“有解释力”不等于“可交易”

F/G/I 都找到了一些有解释力的 transition 读数：

- deterioration 在 robustness 上更脏：F 中 R-core fast-fail `24.5%`、false-repair `30.4%`。
- previous regime 带路径信息：risk_off -> transition 后转 risk_on 的历史比例 `40.0%`，risk_on -> transition 后转 risk_off 为 `18.9%`。
- from_risk_on continuation 很干净，from_risk_on conversion 很脏。

但这些都没有跨过 supported 边界：

- F：boundary 占 `63.7%-80.2%`，robustness recovery core 为 `0`。
- G：400 个 rule 中 structural eligible 为 `0`，robustness conversion 只有 `3` 段。
- I：prev_context OOS 弱于 no_context，robustness ROC-AUC `0.5895` vs `0.6449`。

因此不能把这些解释变量直接变成 PIT entry label 或 rejector feature。它们只能作为 future transition-side diagnostic 或新 regime label 设计的线索。

## 5. 综合 Insight

### 5.1 08 的真正成果不是一个 entry signal，而是一套问题分解

08 没有给出可直接上线的 entry union，但它完成了一个关键研究拆解：

- E1 继续作为 sparse backbone。
- R-core / R6 作为 risk_on recall source 充分。
- T4/T7 降级为 quality/context diagnostic。
- density 从单一指标拆成 full-denominator、rolling 10d、episode-window 三种口径。
- fast-fail / false-repair 被提升为 primary-model admission 前的硬成本问题。
- transition 被从“待补召回 regime”改判为“residual label / state definition 问题”。

这个拆解比一个勉强通过的 low-density union 更有价值，因为它避免把高召回、高成本的事件池误当 alpha。

### 5.2 risk_on 已经进入“局部 frontier 上移”阶段

E/H 的信号不是弱信号。robustness 上 cost reduction、AUC、top-decile lift 都稳定，且 H 修补了 E 的 feature coverage、density config 和同阈值 readout 缺口。失败点非常具体：train `keep_0800` cost 差 `0.8611pp`，`keep_0775` recall 差 `0.8597pp`。

这意味着下一步不应再写成：

```text
继续调 keep fraction / 放宽 gate / 复用 robustness-best threshold
```

而应写成：

```text
提升 score 在 0.775-0.800 附近的局部排序质量，或重新构造 cost_bad_10_20 target，使同一 train-only threshold 同时保留 recall 与降低 cost。
```

可尝试的方向包括：

- 补充更稳的 t0 microstructure / amount / volume / range quality feature。
- 重新审查 `cost_bad_10_20` 中 fast-fail 与 false-repair 的组合权重。
- 对 R2 补 amount / volume expansion 字段，避免 R2 作为 unscored density floor。
- 做 feature ablation，定位哪些特征在 OOS 中真正贡献 cost sorting。
- 在不改变 gate 的前提下测试更稳健的模型族或 calibration，但仍必须 train-only threshold。

### 5.3 transition 当前应关闭，而不是继续“再找 family”

F/G/I 给出的证据已经足够关闭当前 residual transition label 下的 family rediscovery：

- 子态 taxonomy 不稳定。
- previous-regime context 有解释力但不能稳定排序。
- transition robustness 的有效独立 segment 太少。
- published/reconstructed transition 漂移太大。
- OOS 上 no-context cost rejector 反而强于 prev-context。

如果继续在当前 label 下寻找 T6/T8/VCP/volatility family，很容易把 regime composition、短 transition segment 和未来 outcome 混成看似有效的 alpha。未来若要复活 transition，必须先解决数据和标签问题，而不是继续调 event family。

合理的复活条件只有两类：

1. 扩展样本时间跨度，使 transition recovery / conversion 在 robustness-like OOT 中有足够 segment power。
2. 重定义 market regime label source，让 transition 不再是 residual bucket，而是有正向定义、PIT 可识别、跨 split 可复现的状态。

在当前 08 范围内，这两项都不成立。

## 6. 下一步建议

### P0：只推进 risk_on feature / target uplift

下一份 requirement 若继续 08 线，应聚焦 risk_on cost rejector 的 frontier uplift。目标不是重新证明 R-core 有 recall，也不是继续 compression arm grid，而是证明新的 feature / target / model 设计能让 `keep_0800` 附近 cost reduction 上移，或让 `keep_0775` 附近 recall 保持在 90% 以上。

必须保留的 gate：

- train-only threshold selection。
- validation / robustness 只作 readout，不参与调参。
- cost before/after 使用同一 horizon-complete denominator。
- no future feature / no label leakage。
- 保留 E1-missed retention 与 bridge retention。
- density / concentration cap 预声明，不事后补。

### P1：把 transition 只作为 diagnostic，不并入 E/H

G/I 的 previous-regime context 不应并入 H 的 risk_on-only gate。它只定义在 transition universe 内，且 OOS uplift 未成立。若未来要继续 transition-side rejector，应另开新 requirement，明确：

- 只在 transition universe 内训练。
- conversion / continuation 只作 ex-post readout。
- previous-regime context 只作为 PIT feature 的候选，不得替代 future outcome。
- segment-aware power 是硬约束。
- no-context baseline 必须作为主对照。

### P2：关闭当前 label 下的 transition family rediscovery

当前不建议继续做：

- T4/T7 de-overlap 作为主线。
- R-series transition ranker compression。
- transition-specific family rediscovery。
- previous-regime context 直接并入 risk_on cost rejector。
- 用 future conversion / continuation 训练 PIT classifier。

这些方向当前都缺少 supported 前提。

## 7. 不可声称内容

- 不能声称 08 已经产出 direct-entry signal。
- 不能声称 H 已通过 research-entry。
- 不能用 robustness-best threshold 替代 train-selected threshold。
- 不能把 120d winner precision 当成 entry admission 的唯一目标。
- 不能把 fast-fail / false-repair label 当作 t0 feature。
- 不能把 transition taxonomy 说成 supported。
- 不能把 previous-regime conversion / continuation 当作 PIT 可知标签。
- 不能把 R-core 高 recall 解释成可直接交易。

## 8. 最终结论

08 的最终研究结论不是“risk_on / transition 修复失败”，而是：

1. `risk_on` 已经找到有效 recall source 和稳定 cost sorting signal，但当前版本还差一个很窄的 train-only cost/recall frontier。下一步应做 feature / target construction uplift，而不是阈值微调或继续扩 source。
2. `transition` 在当前 residual label 下应停止推进。F/G/I 一致表明它不是稳定第三态，继续找 family 会把混合状态和低 power segment 误当作 alpha。
3. E1 继续是 backbone；R-core/R6 是 risk_on cost rejector 的主要 source；T4/T7 是 negative control / context tag；R-series deterministic compression 已被证伪为主线。
4. 08 后续真正值得投入的是一个严格的 risk_on cost-rejector uplift requirement，而不是新的 transition family search。
