# 12 Multi-K Winner / Failure Path Morphology Research Plan

## 0. 定位

本目录用于承接 11 系列之后的独立研究计划。它不是 11C 的继续调参，也不是新的买入 / 卖出规则需求。

12 的核心问题是：

```text
在 risk_on ∩ strict PIT-valid 的候选分母内，
t0 之后的多 K observed path 是否提供了
超过 11A2 单 K 双通道读数的额外可分自由度；
如果有，是否可以稳定描述 winner path archetype 与 failure path archetype，
并进一步形成可校准的 meta-label probability。
```

本计划只冻结研究背景、目标、边界、阶段和决策门。若本计划通过评审，后续再拆成具体 requirement，例如 `12A0` 输入审计、`12A1` multi-K incremental separability audit、`12A2` path morphology profiling、`12A3` calibrated meta-label feasibility。

---

## 1. 背景

### 1.1 当前 PIT / candidate scope 下的 big winner 数量

12 的 primary research scope 继承 11A1/11A2 的严格 PIT universe：

```text
analysis_regime_bucket == risk_on
AND strict PIT-valid executable universe
```

在 11A1/11A2 primary 口径下，`risk_on` 的 `class_big_winner` split 分布如下：

| split | PIT-valid evaluated rows | big winner rows | big winner rate | big winner instruments |
|---|---:|---:|---:|---:|
| all | 4,665 | 446 | 9.56% | 187 |
| train | 1,708 | 151 | 8.84% | 64 |
| validation | 865 | 16 | 1.85% | 11 |
| robustness | 2,092 | 279 | 13.34% | 134 |

这个统计有两个直接含义：

- train 与 robustness 的 big winner 样本量足够支撑 12 的主诊断；validation winner 只有 16 rows / 11 instruments，只能作为 readout，不适合作为强 OOS veto。
- 12 后续所有 morphology / probability / policy-handoff 判断都必须明确区分 `risk_on pre-PIT` 与 `risk_on ∩ PIT universe`；本计划的 primary 结论只适用于后者。

#### 1.1.1 不同 winner / episode population 不能混用

这里必须区分三层不同分母。它们都在 PIT / Top-N 相关 universe 内，但不是同一个 population：

| population | 来源 | all count | 含义 |
|---|---|---:|---|
| `06_topn_reverse_lifecycle_episode` | 06 Top-N full instrument-day scan | 2,493 | 从 Top-N evaluated instrument-days 中识别出的完整 big-winner episode |
| `10_big_winner_profiling_scope` | 10 big-winner profiling PIT-filtered 09A winners | 3,075 | 09A winner label true 且 PIT matched 的 winner profiling rows |
| `10A_11_candidate_injury_scope` | 10A/11 candidate or injury scope PIT-filtered winners | 1,092 | 进入 10A/10C/11 candidate/injury 链路后的 PIT winner subset |

因此，`1,092` 不是 06 的全量 Top-N big-winner episode 数，也不是全量 09A PIT winner profiling 分母。它是 10A/11 候选链路后的子集。这个差距不能用年份不对齐解释，核心来自 population scope 压缩：

```text
Top-N instrument-day full scan
  -> full big-winner episode/profiling population
  -> event candidate generator / post-dedup / 10A-10C-11 candidate chain
  -> candidate/injury-scope PIT winners
```

06 的 regime episode count 为：

| market_regime_bucket | 06 Top-N episode count |
|---|---:|
| risk_on | 428 |
| risk_off | 1,580 |
| transition | 485 |
| all | 2,493 |

10 profiling 的 PIT-filtered 09A winner count 为：

| path_regime_state | 10 profiling winner rows |
|---|---:|
| risk_on | 1,268 |
| risk_off | 1,393 |
| transition | 414 |
| all | 3,075 |

下面的 1,092 表只对应 `10A_11_candidate_injury_scope`，用于解释 11A1/11A2 当前研究分母的 winner supply，不代表 Top-N 全量 episode supply。

| split | risk_on winner rows | risk_off winner rows | transition winner rows | total PIT winner rows |
|---|---:|---:|---:|---:|
| all | 446 | 495 | 151 | 1,092 |
| train | 151 | 157 | 91 | 399 |
| validation | 16 | 44 | 15 | 75 |
| robustness | 279 | 294 | 45 | 618 |

对应 unique instrument 数如下：

| split | risk_on winner instruments | risk_off winner instruments | transition winner instruments | total winner instruments |
|---|---:|---:|---:|---:|
| all | 187 | 169 | 70 | 282 |
| train | 64 | 62 | 46 | 117 |
| validation | 11 | 26 | 9 | 40 |
| robustness | 134 | 105 | 21 | 196 |

这个扩展统计的含义是：

- 在 10A/11 candidate-scope 内，`risk_off` PIT winner count 并不小：all split 有 495 rows，略高于 risk_on 的 446 rows；但它没有进入 11A1/11A2 的 primary payoff-risk audit，因此 12 不应把它混入 primary model。
- 在 10A/11 candidate-scope 内，`transition` all split 有 151 winner rows，样本明显更少；validation 与 robustness 的 transition winner 分别只有 15 / 45 rows，只适合解释性 readout。
- 若后续要研究 cross-regime morphology，应单独开 `risk_off` / `transition` readout 分支，并重新定义 denominator、failure class 与 stability gate。

### 1.2 11A1：t0 proxy 有信号，但 winner 与 failure 暴露纠缠

11A1 在严格分母下运行：

```text
analysis_regime_bucket == risk_on
AND PIT executable universe valid
AND is_listed=True
AND is_st=False
AND is_suspended=False
```

最终 evaluated denominator 为 4,665 rows，final status 为：

```text
11A1_archetype_proxy_robust_payoff_risk_screen_empty
```

这不是输入不可用，也不是 join / PIT / ST / 停牌审计失败。真正的问题是：8 个预注册 t0 proxy family 没有任何一个同时满足右尾捕获、payoff 非劣、failure 暴露稳定不恶化、matched-base power 与 top-k 稳定性。

关键读数：

| proxy | winner delta | big failure delta | 解释 |
|---|---:|---:|---|
| `P4_momentum_leader` | +6.11pp | +10.34pp | 最像 winner proxy，但 failure 暴露同步上升 |
| `P6_repair_structure` | +5.80pp | +7.34pp | 捕捉修复结构，也捕捉 false repair |
| `P3_volatility_expansion` | -0.44pp | -3.67pp | 风险读数较好，但右尾捕获不足 |
| `P7_flow_confirmation` | -2.48pp | -1.75pp | 太宽，matched base 支撑不足 |
| `P8_recurrence_density` | +4.26pp | +22.54pp | 几乎全覆盖，不是有效 screen |

因此 A1 给出的不是“t0 没有信息”，而是：

```text
当前 t0 feature bank 捕捉到的是事件活跃度、动量、修复、流动性、密度等背景状态；
这些状态与 big winner 有关，但和 big failure / false repair 绑定太紧。
```

这说明单一 t0 proxy 不适合直接作为 retention override 或 winner-protection rule。

### 1.3 11A2：t0 后 K3 出现路径分离，但只是 diagnostic

11A2 使用与 11A1 完全一致的 denominator，对 `class_big_winner` 与 `class_big_failure_proxy_nonwinner` 做 post-t0 path divergence 诊断。

核心结论：

```text
11A2_post_t0_archetype_path_divergence_separation_detected_tradable
```

主对比 C1 在 full-cohort 口径下形成 dual-channel Tier3 confirmed onset：

| contrast | full-cohort confirmed onset | return Tier3 | structure Tier3 | 解释 |
|---|---:|---:|---:|---|
| C1 winner vs big failure proxy | K3 | K1 | K3 | 主结论 |
| C2 winner vs false repair only | K3 | K3 | K3 | false-repair 子类也在 K3 可分 |
| C3 winner vs fast fail | K5 | K3 | K5 | fast-fail 结构通道更晚 |
| C4 winner vs neutral | none | none | K10 | 不构成双通道确认 |
| C5 winner vs all nonwinner | none | K10 | none | all nonwinner 聚合会冲掉结构信号 |

K3 的 tradability lag 通过：winner 组在 K3 时的 `ep_mfe_to_Kstar / mfe_120_recomputed` 中位数为 4.331%，低于 50% ceiling。因此该分离不是在大部分后续有利路径已经兑现后才出现。

但 11A2 也留下两个重要限制：

- return channel 与 structure channel 的秩相关约 0.77，双通道更像同一早期路径质量的两个投影，不是两个独立 alpha。
- 11A2 的 early-path feature registry 是 category-B readout-only，用于证明路径差异存在，不等于已经形成可上线 feature bank。

### 1.4 11C：粗糙 K3 hard rule 能降 failure，但牺牲 winner capture

11C 将 K3 observed state 放入 after-cost / capacity-constrained replay。selected diagnostic arm 为：

```text
B2_wait_confirm_K3__S1_reclaim_damage__target_1.00
```

相对 B0 baseline，selected arm 的主要变化：

| metric | B0 | B2 selected | 变化 |
|---|---:|---:|---:|
| entry_filled_n | 971 | 740 | -231 |
| net_EV_per_exposure_day | -0.000678 | -0.000554 | +0.000124 |
| winner_120_capture_rate | 0.2390 | 0.1951 | -0.0439 |
| winner_120_captured_n | 98 | 80 | -18 |
| big_failure_proxy_entry_rate | 0.0764 | 0.0433 | -0.0332 |
| false_repair_entry_rate | 0.0797 | 0.0454 | -0.0343 |
| cash_drag_mean | 0.5415 | 0.6663 | +0.1248 |

11C 说明：

```text
K3 wait-confirm 确实能减少坏样本进入，
但主要收益来自少交易、少暴露；
它同时丢失了太多 winner，且 EV/day 仍为负。
```

trial-entry 也没有解决问题。10% / 25% trial 会提高 winner capture，但更大幅度提高 big_failure / false_repair exposure，等于把 K3 前尚未分离的坏路径提前买进来。

因此 12 的起点不是“继续调 K3 阈值”，而是：

```text
当前 observed-state rule 太粗；
winner 形态与 failure 形态尚未建模；
不同 path family 可能对应不同 K 与不同决策语义。
```

---

## 2. 核心研究问题

### 2.1 主问题

```text
多 K observed path state 是否提供了超过 11A2 单 K 双通道读数的额外可分自由度？
```

这里的“额外可分自由度”必须满足：

- 在 train 与 robustness 中同向复现。
- 通过 instrument-block bootstrap 或等价 block 依赖审计。
- 不是由少数 instrument / event 贡献。
- 不是 label-derived future coordinate 的同义反复。
- 在控制 11A2 的 K3 return / drawdown 主维度后仍有增量。

### 2.2 次级问题

1. 能否离线描述稳定的 `winner_path_archetype` 与 `failure_path_archetype`？
2. 不同 failure 子类是否需要不同 K frontier，例如 false-repair K3/K5、fast-fail K5、neutral no-separation？
3. t0 feature bank 中的 P4/P6/P3/P7/P8 应该作为 candidate/context/control 如何进入 post-t0 meta layer？
4. observed-state feature bank 是否能形成 calibrated probability，而不只是 hard state？
5. 若 probability 有效，它改善的是 winner capture、failure suppression、EV/exposure-day、capital utilization 中的哪一项？
6. Lane B rejected-then-reclaim 是否应作为独立低频 event family 挂起，而不是 10C override？

---

## 3. 目标

### 3.1 研究目标

12 的目标是建立一个严格的研究路径，回答：

```text
是否值得把 post-t0 winner/failure path morphology
推进到 meta-label probability 或后续 policy replay。
```

具体目标：

- 复用 11A1/11A2 的 strict denominator，避免 scope drift。
- 把 t0 proxy bank、early-path readout bank、observed-state policy bank 的边界讲清楚。
- 建立 multi-K observed-state feature plan，覆盖 K1/K3/K5/K10，必要时保留 K15/K20 作为 late readout。
- 判断多 K 特征是否只是 11A2 K3 return/drawdown 的重复投影。
- 如果存在增量，进行 path archetype 离线 profiling。
- 如果 archetype 稳定，再评估 calibrated meta-label probability 的可行性。
- 输出是否够格进入后续 policy replay 的判定，而不是直接输出交易规则。

### 3.2 工程目标

后续若拆 requirement，12 系列应产出可复现 artifacts：

- frozen config 与 manifest。
- input artifact audit。
- denominator reconciliation vs 11A1/11A2/11C。
- observed-state feature registry。
- multi-K feature matrix schema。
- incremental separability readout。
- morphology stability readout。
- calibration readout。
- top-k / block bootstrap / multiple-comparison audit。
- final research decision report。

### 3.3 非目标

12 不做以下事情：

- 不改写 10C。
- 不直接授权 t0 或 t0+K 买入。
- 不输出 `state-positive => buy`。
- 不把 winner / fast_fail / false_repair / future return / future MFE 当作 feature。
- 不继续微调单一 K3 hard rule。
- 不用 train-only clustering 直接定义 archetype。
- 不因 Lane B robustness readout 有趣就降低 power floor。
- 不把减少 exposure 误读为策略有效。

---

## 4. 研究边界

### 4.1 分母边界

primary denominator 必须继承 11A1/11A2：

```text
risk_on ∩ strict PIT-valid evaluated denominator
```

当前行数基准：

| split | rows |
|---|---:|
| all | 4,665 |
| train | 1,708 |
| validation | 865 |
| robustness | 2,092 |

任何后续 requirement 必须对账：

- 11A1 PIT-valid rows。
- 11A2 PIT-valid rows。
- 11C replay candidate scope。
- instrument / event_t0_date uniqueness。
- canonical id join status。
- qfq anchor / event_window_anchor_date match。

若 denominator drift 超过预注册 ceiling，研究状态不得高于 statistics_incomplete。

### 4.2 label 边界

允许作为 outcome / target / readout：

```text
winner_120
class_big_winner
class_big_failure_proxy_nonwinner
subclass_false_repair_only
subclass_fast_fail
class_neutral_chop
forward_return_120d
MFE / MAE beyond K
```

禁止作为 primary feature：

```text
winner_120
forward_return_120d
future MFE / MAE beyond observed K
selected_fast_fail_barrier_id
selected_fast_fail_touch_pos
selected_fast_fail_touch_date
label-derived future coordinate
任何从 outcome definition 直接回填的状态
```

fast-fail touch 只能进入 label-overlap audit。K 越晚，fast-fail touch 越接近标签同义反复；K10 已经与 fast-fail 标签完全重合，因此不得作为 primary morphology feature。

### 4.3 时间边界

observed-state feature 在 K 时点只能使用：

```text
(t0, t0+K] 内已经发生的 qfq OHLCV、money、volume、limit/executable 状态、relative board path
```

收益、回撤、MFE/MAE 的基准必须与 11A2 一致：

```text
entry_anchor_price = t0+1 open
window = (t0, t0+K]
```

K 候选：

```text
K = [1, 3, 5, 10]
```

K15/K20 可以作为 late readout，但不应默认进入 primary decision frontier。若加入，必须明确解释 label-overlap 与 tradability-lag 风险。

### 4.4 策略边界

12 是 research layer，不是 policy replay layer。

允许输出：

```text
multi-K separability exists / absent
archetype stable / unstable
probability candidate calibrated / not calibrated
eligible for future policy replay / diagnostic only
```

不允许输出：

```text
buy
sell
override 10C
increase position
state-positive => route
```

---

## 5. 需要建立的 feature bank

### 5.1 t0 context bank

当前 A1 的 t0 bank 不足以单独区分 winner/failure，但仍可作为 context：

| family | 用法 |
|---|---|
| P4 momentum / P6 repair | right-tail candidate context，不是 hard screen |
| P3 volatility expansion | risk-suppression context |
| P7 flow / P8 recurrence | market activity / event-density covariate，不能作为 positive membership |
| board / regime / liquidity | stratification 与 calibration context |
| 10C reject / keep lane | event-source context，不直接 override |

t0 context bank 的原则：

```text
t0 context 只回答“这是什么类型的 candidate”，
post-t0 observed state 才回答“它是否在路径上自证”。
```

### 5.2 multi-K observed path bank

12 需要比 11C 的三条 K3 hard state 更丰富，但必须保持可解释与非泄漏。

#### EP1 return path

候选字段：

- `ret_0_to_1`
- `ret_1_to_3`
- `ret_3_to_5`
- `ret_5_to_10`
- `ret_0_to_K`
- `close_vs_t0_close_at_K`
- `close_in_K_range`
- `positive_close_day_count_K`
- `return_slope_K`

研究目的：

```text
区分 immediate reclaim、delayed grind、early spike then fade。
```

#### EP2 drawdown / path damage

候选字段：

- `max_drawdown_to_K`
- `min_close_ret_to_K`
- `days_to_min_low_K`
- `drawdown_duration_K`
- `breach_t0_low_through_K_flag`
- `close_after_breach_reclaim_flag`
- `damage_then_recover_ratio_K`

研究目的：

```text
区分 constructive shakeout 与 destructive damage。
```

#### EP3 recovery / reclaim shape

候选字段：

- `recovery_from_min_to_K`
- `recovery_speed_from_min_K`
- `close_above_t0_high_at_K_flag`
- `close_above_t0_close_at_K_flag`
- `close_above_ema20_at_K_flag`
- `days_above_ema20_through_K`
- `failed_reclaim_count_K`

研究目的：

```text
区分真正路径自证与 false repair。
```

#### EP4 volume / liquidity confirmation

候选字段：

- `money_ratio_K_vs_20d`
- `volume_ratio_K_vs_20d`
- `up_day_volume_expansion_K`
- `down_day_volume_contraction_K`
- `vol_decay_ratio_K`
- `money_on_reclaim_days_K`
- `money_on_damage_days_K`

研究目的：

```text
检查 price reclaim 是否有成交确认；
避免只用价格路径重复 11A2 return/drawdown。
```

#### EP5 volatility sequence

候选字段：

- `atr_change_t0_to_K`
- `range_contraction_K`
- `range_expansion_then_contract_K`
- `intraday_range_median_K`
- `volatility_burst_day_count_K`

研究目的：

```text
区分健康换手、失控波动和假修复。
```

#### EP6 relative path

候选字段：

- `stock_vs_board_ret_0_to_K`
- `stock_vs_board_drawdown_K`
- `stock_vs_market_ret_0_to_K`
- `relative_reclaim_flag_K`
- `relative_volume_confirmation_K`

研究目的：

```text
把个股路径与板块 / 市场背景分离，避免把 beta path 误读为 archetype。
```

#### EP7 execution / tradability state

候选字段：

- `entry_t0pKplus1_executable_flag`
- `limit_up_locked_next_open_flag`
- `limit_down_exit_failure_flag`
- `suspended_through_K_flag`
- `tradable_open_after_K_flag`
- `turnover_capacity_proxy_K`

研究目的：

```text
保证形态分离不是不可交易状态造成的虚假优势。
```

### 5.3 morphology descriptors

12 可以离线 profile 下列 path family，但进入 feature 的必须是 K 时点可见 proxy：

| path family | 可能 K | 研究含义 |
|---|---:|---|
| immediate reclaim winner | K1/K3 | 早期自证，可能 observation-first upgrade |
| constructive shakeout winner | K3/K5 | 先 damage 后 reclaim，容易被 hard K3 杀掉 |
| delayed realization winner | K5/K10 | 早期不强，但不破坏结构 |
| false repair failure | K3/K5 | 表面修复后继续转弱 |
| fast damage failure | K3/K5 | 结构通道更晚确认，但 label-overlap 风险高 |
| neutral chop | none / late | 不适合硬分离，可能只做 exposure control |
| rejected then reclaim | K3/K5 | 新 observed-state event，不是 10C override |

---

## 6. 阶段计划

### Phase 12A0：scope freeze 与输入审计

目标：

```text
确保 12 使用的 denominator、anchor、label、qfq path 与 11A1/11A2/11C 对齐。
```

任务：

- 读取 11A1 final denominator 或重建 strict PIT-valid denominator。
- 对账 11A2 class distribution。
- 对账 11C Lane A / Lane B 口径。
- 冻结 config、feature registry、K grid、contrast registry。
- 输出 input artifact audit 与 manifest。

成功条件：

- all/train/validation/robustness row count 与 11A1/11A2 drift 在 ceiling 内。
- event_t0_date 与 qfq anchor match rate 通过。
- label class 互斥且与 11A2 一致。

失败时解释：

```text
statistics_incomplete，不进入 morphology。
```

### Phase 12A1：multi-K incremental separability audit

目标：

```text
先回答多 K 是否有增量自由度，再决定是否做 archetype。
```

核心对照：

| contrast | positive | negative | 用途 |
|---|---|---|---|
| C1 | big winner | big failure proxy nonwinner | primary |
| C2 | big winner | false repair only | constructive vs false repair |
| C3 | big winner | fast fail | damage / failure timing |
| C4 | big winner | neutral chop | 检查是否只是 failure-specific |
| C5 | big winner | all nonwinner | 检查聚合负类是否塌缩 |

需要输出两类读数：

1. raw separability：
   - per feature × K × split Cliff's delta / AUC / KS。
   - channel direction。
   - bootstrap CI。

2. incremental separability：
   - 在控制 11A2 `ep_ret_t0_to_3` 与 `ep_max_drawdown_to_3` 后的残差增量。
   - K increments 相对 cumulative K 的增量。
   - non-price families 对 price-only baseline 的增量。
   - grouped cross-fit AUC / log-loss / Brier lift。

最低判断逻辑：

```text
如果 multi-K + non-price features 不能稳定超过 K3 return/drawdown baseline，
则说明可分信息主要是一个早期路径质量维度；
12 应停在 diagnostic，不进入 morphology clustering。
```

### Phase 12A2：path morphology profiling

触发条件：

```text
12A1 证明存在可复现增量自由度。
```

目标：

```text
用离线方式描述 winner/failure path archetype，
但不把 outcome label 泄漏进 primary feature。
```

可选方法：

- 预定义 rule-based path descriptors。
- 低自由度 prototype matching。
- 预注册聚类，但必须冻结簇数、距离度量、初始化、随机种子。
- supervised profiling 只能作为解释，不得直接变成 policy rule。

稳定性要求：

- train / robustness archetype 分布同向。
- instrument-block bootstrap 稳定。
- top-k instrument removal 后 archetype 解释不翻转。
- cluster / prototype 不能只在 train 上成立。
- validation 仅在 power 足够时参与 conflict 判定；否则 readout-only。

输出：

- `winner_path_archetype_profile`
- `failure_path_archetype_profile`
- `archetype_feature_signature`
- `archetype_onset_K`
- `archetype_power_readout`
- `archetype_stability_readout`
- `label_overlap_risk`

### Phase 12A3：calibrated meta-label probability feasibility

触发条件：

```text
12A2 证明至少一个 path archetype 在 train / robustness 稳定复现。
```

目标：

```text
判断 observed-state morphology 是否能形成 calibrated probability，
而不是只能形成 hard label 或漂亮图形。
```

候选 targets：

- `P(winner_120 | event, t0_context, observed_state_K)`
- `P(big_failure_proxy | same conditioning)`
- `P(false_repair_only | same conditioning)`
- `P(fast_fail | same conditioning)`
- `E[net payoff / exposure-day | same conditioning]` as readout-only until policy replay

模型纪律：

- 使用 grouped / purged / embargoed cross-fit。
- instrument-block 依赖必须显式处理。
- 所有 hyperparameter 必须预注册或使用极小 search space。
- 输出 calibration，不只输出 AUC。
- 不允许使用 future MFE/MAE、forward return、label touch coordinate 作为 feature。

最低读数：

- AUC / PR-AUC。
- Brier score。
- Expected calibration error。
- reliability by probability bucket。
- winner capture vs failure exposure frontier。
- lift after top-k removal。
- split-level drift。

若 probability 不校准：

```text
形态可能真实，但不够格进入 policy replay。
```

### Phase 12A4：policy replay handoff decision

目标：

```text
只决定是否值得进入后续 policy replay，不在 12 内运行策略。
```

handoff 条件：

- multi-K 增量自由度存在。
- 至少一个 archetype 稳定。
- probability 校准通过。
- failure exposure 没有通过牺牲过多 winner capture 来改善。
- 结果不依赖 top-k instrument。
- 交易可执行状态没有制造虚假优势。
- 预估 EV/exposure-day frontier 有研究价值，但最终 EV 必须留给后续 replay。

可能 handoff：

```text
12_policy_replay_candidate_observation_first
12_policy_replay_candidate_delayed_rescue_readout
12_diagnostic_only_no_policy_handoff
```

---

## 7. 统计与验证纪律

### 7.1 split 与 block dependency

primary 判断应优先使用 train + robustness。

validation 的使用规则：

- 如果 validation winner / negative power 足够，可以作为 conflict 判定。
- 如果 validation underpowered，只能 readout，不推翻 train/robustness。

必须保留：

- instrument-block bootstrap。
- event-block sensitivity。
- top-k instrument removal。
- top-k episode removal。
- sample uniqueness / overlap weighting。

### 7.2 multiple comparison

12 的比较空间大于 11A2：

```text
K × feature_family × feature × contrast × split × cohort × optional archetype
```

必须继承并加严 11A2 的 null audit：

- 在 `split + event_year_quarter + source_family_id` 或更合理的 cell 内置换 label。
- 保持 class marginal count。
- 重算 raw 与 incremental readout。
- 输出 actual vs null p95 / p99。
- 不允许用 null 结果事后删 feature。

### 7.3 incremental freedom test

12A1 的关键不是 raw AUC 高，而是增量成立。

建议至少比较三组 baseline：

| baseline | 目的 |
|---|---|
| `K3_return_drawdown_baseline` | 11A2 主维度 |
| `price_only_multi_K_baseline` | 检查多 K 价格路径是否足够 |
| `price_plus_volume_relative_execution` | 检查非价格族是否提供增量 |

如果第三组相对第一组没有稳定提升，则不应进入复杂 morphology。

### 7.4 tradability 与 execution

任何形态都必须在 K 时点仍可交易：

- K 时点 winner 后续 MFE 未大量兑现。
- K+1 entry executable。
- 涨停锁定 / 跌停退出失败不制造假收益。
- 停牌 / 退市 / qfq path 缺失不造成 survivorship separation。
- capacity 与 turnover 至少作为 handoff 风险记录。

### 7.5 leakage audit

必须输出 forbidden feature audit：

- outcome label 字段是否进入 feature matrix。
- fast-fail touch coordinate 是否进入 primary feature。
- future MFE/MAE 是否进入 feature。
- forward return 是否进入 feature。
- K 之后的 qfq bar 是否被使用。

任何 leakage 命中，final research status 不得高于 input_blocked 或 statistics_incomplete。

---

## 8. 决策门

### Gate 0：输入完整

通过条件：

- denominator 对账通过。
- qfq anchor 对账通过。
- label class 对账通过。
- K window feature coverage 通过。
- forbidden feature audit 通过。

失败状态：

```text
12_input_blocked
12_statistics_incomplete
```

### Gate 1：多 K 增量自由度

通过条件：

- multi-K / non-price / incremental path features 在 train 与 robustness 中相对 K3 baseline 有稳定增量。
- block bootstrap 支持。
- top-k removal 后不翻转。

失败状态：

```text
12_multi_k_no_incremental_freedom_stop
```

解释：

```text
可分信息基本就是 11A2 的早期路径质量维度；
继续做 morphology 只会把同一信号包装得更复杂。
```

### Gate 2：path archetype 稳定

通过条件：

- 至少一个 winner archetype 与一个 failure archetype 在 train / robustness 中可复现。
- archetype 不是少数 instrument 驱动。
- archetype 的 feature signature 可解释且 K 时点可见。

失败状态：

```text
12_morphology_unstable_diagnostic
```

解释：

```text
形态可能存在，但无法稳定支持后续 probability 或 policy。
```

### Gate 3：probability 可校准

通过条件：

- winner / failure probability 有可接受 calibration。
- probability bucket 的 payoff-risk frontier 单调或至少稳定。
- winner capture 没有因 failure suppression 明显塌缩。

失败状态：

```text
12_probability_uncalibrated_diagnostic
```

### Gate 4：policy handoff

通过条件：

- Gate 0-3 通过。
- handoff risk table 无 hard veto。
- 只授权后续 policy replay，不授权当前交易。

成功状态：

```text
12_meta_label_probability_policy_replay_candidate
```

---

## 9. 预注册失败模式

| failure mode | 结论 | 系统含义 |
|---|---|---|
| 多 K 无增量 | K1/K3/K5/K10 只是同一早期路径质量维度 | 停在 diagnostic，不做 morphology |
| 非价格特征无增量 | volume / relative / execution 不增加可分性 | 12 不扩 feature bank，只保留 A2 readout |
| morphology train-only | archetype 只在 train 好看 | 不进入 probability，不进入 policy |
| archetype top-k dependent | 少数 instrument 贡献主导 | 不支持 |
| fast-fail K5 可分但 label-overlap 高 | 可能接近 label tautology | 只允许 readout |
| winner archetype 可分但 EV frontier 不支持 | 形态真实但不可交易 | 不进入 policy replay |
| failure 降低来自牺牲 winner | 重复 11C | 说明 hard rule 或 probability cutoff 过粗 |
| Lane B 有信号但 power 不足 | 低频高赔率分支 | 独立挂起，等待自然样本积累 |
| calibration 失败 | ranking 可能有用但概率不可用 | 不做 sizing |
| validation underpowered | 不能强证 OOS | train/robustness 主导，validation readout-only |

---

## 10. 建议 artifact 布局

若后续从 research plan 拆成 executable requirements，建议目录保持：

```text
12_multi_k_winner_failure_path_morphology_research_v0/
  research_plan.md
  requirement_12a0_scope_input_audit.md
  requirement_12a1_multi_k_incremental_separability_audit.md
  requirement_12a2_path_morphology_profiling.md
  requirement_12a3_calibrated_meta_label_probability_feasibility.md
  configs/
  src/
  tests/
  outputs/
    publishable/
      reports/
      tables/
    local_cache/
```

第一阶段只需要 `research_plan.md`。不要提前创建 code/config/test skeleton，避免把尚未评审的研究计划伪装成已经冻结的 implementation requirement。

---

## 11. 与 11 系列的关系

12 继承 11 的结论，但不修改 11。

```text
11A1:
  t0 proxy screen empty。
  右尾候选与 failure 暴露纠缠。
  当前 t0 feature bank 不足以做 winner-protection screen。

11A2:
  post-t0 K3 path divergence 存在且 tradability lag 通过。
  但 return / drawdown 双通道高度共线。
  early-path feature 是 diagnostic readout，不是 policy feature bank。

11C:
  K3 hard state 可以降低 failure exposure。
  但 winner capture 损失、EV/day 仍负、train/top-k 不支持。
  wait-confirm 比 trial-entry 干净，但不是完整策略。

12:
  不继续调单一 K3 hard rule。
  先检验 multi-K 是否有额外自由度。
  再决定是否做 path archetype 与 calibrated meta-label probability。
```

---

## 12. 初步研究命题

12 可以从以下命题开始，但所有命题都必须接受反证：

### H1：multi-K path increments 有增量

```text
ret_1_to_3、ret_3_to_5、drawdown timing、recovery speed
可能比单一 K3 cumulative return/drawdown 更能区分 constructive shakeout 与 false repair。
```

反证：

```text
控制 K3 return/drawdown 后，增量不稳定或消失。
```

### H2：false-repair 与 fast-fail 需要不同 K frontier

```text
false-repair 可能在 K3/K5 分离；
fast-fail 结构通道可能更接近 K5；
neutral chop 不应与 failure 混为同一负类。
```

反证：

```text
子类分离只是 power / label-overlap / top-k artifact。
```

### H3：volume / relative / execution 能提供正交信息

```text
价格 reclaim 若缺少 volume / relative confirmation，可能更接近 false repair；
有确认的 reclaim 可能更接近 winner path。
```

反证：

```text
这些特征只是在重复 return/drawdown 或流动性背景，不提供增量。
```

### H4：winner 不是同质类

```text
最容易被 10C/11C hard rule 误伤的 winner 可能是
constructive shakeout / delayed realization，
而不是 immediate straight-line winner。
```

反证：

```text
所谓子类只在 train 可见，robustness 不复现。
```

### H5：Lane B 是新事件，不是 t0 override

```text
rejected-then-reclaim 若路径自证，应被视为 t0+K 的新 observed-state event。
```

反证：

```text
样本长期低 power，或 robustness readout 随新增年份消失。
```

---

## 13. 推荐下一步

建议下一步只做一件事：

```text
起草 requirement_12a0_scope_input_audit.md 与
requirement_12a1_multi_k_incremental_separability_audit.md。
```

不要先做 clustering，也不要先写 probability model。原因是：

```text
如果 12A1 证明多 K 没有增量自由度，
后续 morphology / probability 都没有必要。
```

12A1 的成功不是要求找到策略，而是要求明确回答：

```text
多 K observed path 是否提供了
超过 11A2 K3 return/drawdown baseline 的可复现增量？
```

这个问题回答清楚后，才决定 12A2 是否启动。
