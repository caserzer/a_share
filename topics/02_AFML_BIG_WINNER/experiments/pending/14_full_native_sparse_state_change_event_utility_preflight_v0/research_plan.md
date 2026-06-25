# 14 Full-Native Sparse State-Change Event Utility Preflight 研究计划

## 0. 定位

Episode 14 从 2026-06-25 的 topic-level retrospective 出发。它接受 Episode 01-13 已经反复暴露的主 blocker：

```text
ranking / recall / probability readout repeatedly exists,
but it does not reliably transport into after-cost full-denominator entry utility.
```

Episode 14 不继续 13B sequence mining，而是打开一个不同的研究对象：

```text
full-native sparse state-change event
```

这个对象必须明确区别于：

```text
dense daily state token
C0-derived repair state
compression-repair composite state
post-hoc selected morphology slice
rule overlay on an already failed selected state
```

因此 14A 不是“再换一个 token 试试”，而是对当前 active winner-entry thesis 的边界检验：

```text
daily state token
  -> sparse state-change event

single-stock time-series state
  -> event + PIT cohort relative position

winner / ranking readout
  -> after-cost full-denominator utility transport
```

如果 14A 仍失败，后续不应继续主动 winner-entry event family search；只能把 topic 降级到 defense / participation overlay，或正式更换 thesis。

本文件仍是研究计划，不是 14A requirement。等方向确认后，14A requirement 必须再冻结：

```text
path / lineage identity
cost grid and cost meaning
split boundary source
event formula and parameter grid
cohort availability audit
decision_state <-> gate_failure mapping
```

这些属于执行契约，不在本 plan 里展开成完整规格。

## 1. 核心假设

剩下的正向假设很窄：

```text
部分 winner 信息可能存在于标的发生状态切换的瞬间，
而不是存在于每日持续状态本身。

如果这个切换足够 sparse、first-trigger、de-duplicated，
并且用严格 PIT 的 current / trailing cohort 进行相对化评价，
已有的 ranking 信号可能转化为 after-cost utility。
```

这里的核心不是：

```text
sparse event alone works.
```

而是：

```text
sparse state-change event
  + strict PIT cohort relative position
  -> ranking-to-utility transport
```

Raw sparse event 只是必要 baseline；PIT cohort normalization 才是 14A 真正要正面攻击的新维度。

同样重要的是负向假设：

```text
如果 sparse first-trigger event 加上 PIT cohort normalization 后仍然无法通过 utility，
则本 topic 应停止继续寻找主动 winner-entry event family，
只把 defense / participation overlay 作为一个更低目标的独立方向讨论。
```

因此，14A 的有效正向证据必须同时满足两点：

```text
1. sparse event 不是 pure noise，至少有 opportunity / ranking 表面；
2. PIT cohort relative position 能把这个表面转成 full-denominator utility。
```

如果 raw sparse event 完全没有 opportunity / ranking 表面，不应继续在纯噪声 family 上消耗 cohort search budget。

## 2. 工作流结构

### Phase 14A0: Lineage Freeze

先冻结继承的数据与标签表面：

- 继承 13A 的 native opportunity universe lineage；
- 继承 12A7g / 13A 的 selected vol-scaled label：`vol20d_kup2p0_kdn1p0_H20`；
- 固定 next-open entry convention；
- 固定 split boundary 与 horizon completeness checks；
- 固定 cost grid，并以 50bps 作为 primary gate。

这里必须记录一个 split 解释 caveat：

```text
validation split 是当前研究链路中的病态压力测试区间：
它对应长时间下跌 / risk-off 压力环境，不应被解释为普通中性 OOS 区间。
```

这条 caveat 不允许用来调低 gate，也不允许用 validation 回头选 family / threshold / cohort arm。它只改变结果解释：

```text
validation pass:
  强压力区间也能保持 utility，证据含金量更高。

validation fail:
  必须区分是 no-signal failure，还是 stress-regime utility transport failure。
  但二者都不能直接授权主动 winner-entry search 继续推进。
```

输出：

```text
input_artifact_audit.csv
upstream_lineage_audit.csv
native_label_portability_audit.csv
```

### Phase 14A1: Sparse Event Formula Freeze

预注册一组小规模 event family。每个 family 只能产生 transition event：

- false-to-true state transition；
- residual break；
- first reclaim after controlled damage；
- compression-to-expansion transition；
- board-relative strength jump；
- participation ignition with price control。

每个 family 必须定义：

- 只使用 t0 可观测特征；
- trigger formula；
- reset condition；
- cooldown window；
- max density target；
- event_id canonicalization；
- disallowed overlap behavior。

输出：

```text
sparse_event_family_formula_spec.csv
sparse_event_generation_audit.csv
sparse_event_density_audit.csv
```

### Phase 14A2: Raw Event Utility Preflight

在任何 cohort normalization 之前，先评估每个 family 的 raw event 表现：

- event count 与 instrument-year density；
- 20d / 60d / 120d opportunity readout；
- selected winner label readout；
- lower-first / fast-fail readout；
- 0bps / 50bps / 100bps utility；
- event uniqueness 与 duplicate episode exposure。

这个阶段回答一个基础问题：

```text
sparse first-trigger discipline 本身是否已经改变 opportunity / bad-side / utility 表面。
```

但 14A 不以 raw event 单独成立作为最终目标。Raw event 如果只有 winner lift / ranking readout 而没有 utility，仍然可以进入 14A3；因为本轮真正要检验的是 cohort-relative position 是否能完成 utility transport。

进入 14A3 前应有最低 opportunity 表面：

```text
no winner/opportunity/ranking surface
  -> family stops at 14A2

winner/opportunity/ranking surface exists but no raw utility
  -> allowed into 14A3 cohort transport test
```

输出：

```text
sparse_event_raw_readout.csv
sparse_event_badside_utility_audit.csv
sparse_event_uniqueness_density_audit.csv
```

### Phase 14A3: Strict PIT Cohort Normalization

在不引入未来信息的前提下，加入 cohort-relative selection arms。这是 14A 的主实验臂，不是附表诊断。

允许的 normalization family：

- same reference-date full cross-section，前提是 decision point 为收盘后、entry 为 next-open；
- same-board same reference-date cross-section；
- rolling prior event cohort by family；
- rolling prior board-event cohort；
- month-to-date partial cohort，只使用 `<= t0` 的日期；
- week-to-date partial cohort，只使用 `<= t0` 的日期。

同日 cross-section arm 是 14A 最大的 PIT 风险源。它只有在能证明以下条件时才允许进入主读数：

```text
decision_time = t0 close
entry_time = next executable open
same-date cohort membership / board / executable flags / t0 features are all observable before entry
```

若 cohort availability audit 不能证明这些条件，该 cohort arm 必须作废，不能降级为可用诊断。

禁止的 normalization：

- whole-month full cohort rank；
- whole-split rank；
- future event count；
- 任何包含 t0 之后日期的 cohort statistic；
- 任何 validation / robustness selected threshold。

primary question 不是 cohort rank 是否提高 AUC，而是：

```text
它是否在保留 winner opportunity 的同时，
改善 50bps same-event full-denominator utility。
```

如果只看到 rank / AUC / winner-rate 改善，而 50bps full-denominator utility 仍不过，结论必须写成：

```text
cohort signal present, utility transport failed.
```

输出：

```text
pit_cohort_normalization_dictionary.csv
pit_cohort_rank_availability_audit.csv
pit_cohort_normalized_utility_readout.csv
cohort_normalization_transport_audit.csv
```

### Phase 14A4: Decision

14A 必须输出一个单一 decision state：

```text
14A_supported_open_14B_confirmatory_sparse_event_requirement
14A_diagnostic_raw_event_signal_but_no_cohort_transport
14A_diagnostic_cohort_signal_only_no_utility
14A_stop_no_sparse_event_utility
14A_stop_no_cohort_utility_transport
14A_stop_validation_stress_failure_no_active_entry_authorization
14A_stop_density_duplicate_or_morphology_rediscovery
14A_input_blocked
```

后续 requirement 必须把 decision state 与 gate failure 做确定性映射，避免人工解释裁决。

## 3. 候选 Event Families

初始 family 数量必须足够少，保证可审计：

```text
F1 residual_cusum_break
F2 compression_to_directional_expansion
F3 controlled_damage_first_reclaim
F4 board_relative_strength_rank_jump
F5 participation_ignition_with_price_control
F6 low_volatility_range_expansion_first_trigger
```

优先级按“是否真正像状态变化”排序：

```text
priority_1:
  F1 residual_cusum_break
  F3 controlled_damage_first_reclaim
  F4 board_relative_strength_rank_jump

priority_2:
  F5 participation_ignition_with_price_control

caution:
  F2 compression_to_directional_expansion
  F6 low_volatility_range_expansion_first_trigger
```

F2 / F6 允许保留，但必须防止滑回 13A 的 compression / low-volatility dense token。它们只有在满足 first-trigger、reset、cooldown，并且通过 morphology rediscovery gate 时，才可以作为 state-change event 解释。

对 F2 / F6 还应有更高解释门槛：

```text
它们必须证明不是 13A volatility compression token、
也不是 13A3 / 13C selected compression-repair morphology 的换名。
```

如果 F2 / F6 的正向读数主要来自 compression / low-vol overlap，而没有独立 utility，应裁决为 morphology rediscovery，而不是 state-change support。

每个 family 可以有一个小型 frozen parameter grid，但必须在读取 validation / robustness 之前声明。一个 family 如果只有 train ranking 好、utility 不过，不能靠事后追加 filter 救回来。

为防止 search budget 失控，14A requirement 应预注册：

```text
family count
parameter-grid count
cohort-arm count
train-only selection rule
maximum operating arms allowed into validation / robustness
```

## 4. Primary Gates

本计划在任何下游研究前设置硬 gate：

- input / lineage gate；
- sparse event construction gate；
- density / duplicate gate；
- native label portability gate；
- bad-side veto gate；
- 50bps after-cost full-denominator utility gate；
- cohort-normalization incremental utility gate；
- morphology rediscovery gate；
- validation stress interpretation gate；
- search accounting gate。

最重要的 gate 是：

```text
At 50bps, the selected train-frozen event arm must be positive in both
validation and robustness under same-event full denominator.
```

对 normalized arms，skipped events 必须留在 event denominator 中，participation return 记为 0。这样可以防止 selected-entry utility 偷换 full-denominator utility。

因为 validation 是长下跌压力测试区间，14A 的结果表述必须额外报告：

```text
validation_stress_status
stress_split_utility_50bps
stress_split_winner_opportunity_retained
stress_split_badside_exposure
```

但这些只是解释层字段，不是新的调参入口。

## 5. Stop Conditions

只要出现以下任一情况，Episode 14 应在 14A 后停止：

- 没有 family 能产生 sparse、auditable、next-open executable events；
- 所有 family 在 cooldown 后仍退化为 dense state proxy；
- raw sparse events 完全没有 opportunity / ranking / utility 表面；
- raw sparse events 有 winner lift / ranking readout，但 PIT cohort normalization 仍不能把它转成 full-denominator utility；
- PIT cohort normalization 只改善 rank metrics，但不改善 full-denominator utility；
- robustness 有表面但 validation 压力区间 utility 崩溃，且无法证明 stress-safe transport；
- 最优 family 只是 broad drawdown / compression morphology rediscovery，且没有 independent utility；
- utility 依赖 look-ahead cohort rank 或 validation-selected threshold。

只有当 14A 产生一个 train-frozen family 和 operating arm，并且通过上述 gate，才允许打开 14B。

14A 失败时必须区分几类含义：

```text
no_sparse_event_surface:
  sparse event thesis itself failed.

ranking_to_utility_transport_failed:
  sparse event has signal, but cohort-relative ranking still cannot become utility.

stress_validation_failure:
  signal may exist outside stress interval, but long-downtrend validation does not permit active entry authorization.
```

这些失败类型都不授权继续主动 winner-entry search，但它们对后续复盘含义不同。

## 6. 非目标

14A 不做：

- sequence mining；
- meta-labeling；
- nonlinear model capacity retry；
- probability calibration；
- bet sizing；
- portfolio backtest；
- exit / holding policy；
- cost model calibration；
- post-hoc replacement of selected event family；
- defense overlay。

Defense overlay 只能作为一个更低目标的独立 thesis 重新讨论，不能作为拯救失败 14A winner-entry preflight 的补丁。
