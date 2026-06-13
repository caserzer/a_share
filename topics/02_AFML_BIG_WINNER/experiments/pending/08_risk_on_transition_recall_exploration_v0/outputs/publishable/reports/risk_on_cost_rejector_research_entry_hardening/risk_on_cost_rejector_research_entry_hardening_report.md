# Experiment H - Risk-on Cost Rejector Research-Entry Hardening 报告

最终决策：`risk_on_cost_rejector_diagnostic_only_or_no_candidate`

## 结论

H 是对 Experiment E 的 research-entry hardening replay，不是新 family、不是 transition extension，也不是正式训练流程。本轮固定 `08_R_core_event_regime_gated + supervised_joint_cost_rejector`，只验证一件事：在补齐 admission contract 后，risk_on cost rejector 是否可以作为 research-entry candidate 成立。

结论是：模型本身有明确 OOS readout 信号，但还没有通过 research-entry。失败不是因为 label、as-of join、feature coverage、denominator 或 E artifact binding 崩掉，而是 train-only threshold selection 找不到一个同时满足 cost 与 recall 的阈值。

核心边界非常窄：

- `keep_0800` 保住 train any recall：`90.0452% >= 90%`，但 train cost reduction 只有 `14.1389%`，距离 `15%` 差 `0.8611pct`。
- `keep_0775` 达到 train cost reduction：`15.3452% >= 15%`，但 train any recall 只有 `89.1403%`，距离 `90%` 差 `0.8597pct`。
- E1-missed retention 不是主要瓶颈：`keep_0800` 为 `95.00%`，`keep_0775` 为 `93.75%`，都高于 `85%`。
- robustness 侧大部分阈值反而更容易过 cost gate；真正卡住的是 train split 上 cost/any-recall 的同阈值交叉点。

因此，本轮应解释为：H 证明了这条线有可用的 supervised cost signal，但在当前 feature set 与 logistic regression threshold grid 下，尚未形成可以提交 research-entry 的同阈值证据。

## Admission Gap 修补状态

H 针对 E 距离 research-entry 最近但尚未完全闭合的三个 admission 缺口做了 hardening：

1. density / concentration gate 已在 H config 中预声明，并写入 manifest。
2. `momentum_percentile_20d_lag20` 被明确剔除，没有做未来填充。
3. 所有 gate 指标必须来自同一个 selected threshold，禁止从 cost frontier 与 recall frontier 分别 cherry-pick。

本轮 `source_caveated propagation = True`，因为 H 继承 E 的 caveated source status。该 caveat 没有阻塞 H replay，但会影响最终 candidate tier 的表述。

## Scope / Input Audit

H 重新读取了 raw input 与 D/E materialized artifacts，而不是只复用 E 汇总结果。

| input | row_count | 说明 |
|---|---:|---|
| `candidate_family_canonical_events.csv.gz` | 90,576 | canonical event universe |
| `candidate_family_event_instances.csv.gz` | 238,679 | 已在 full run 实际读取，105 列 |
| `candidate_family_event_labels.parquet` | 331,318 | event-level label source |
| `cross_section_feature_panel.parquet` | 912,586 | t0 daily panel feature source |
| `post_replay_event_episode_membership.parquet` | 357,450 | replay membership 与 episode binding |

R-core label reconciliation 结果是可用的：

| source_pool | event_n | label_joined_n | missing_label_n | cost_label_complete_n | complete_rate | membership mismatch |
|---|---:|---:|---:|---:|---:|---:|
| `08_R_core_event_regime_gated` | 47,914 | 47,914 | 0 | 47,849 | 99.8643% | 0 |
| `08_R6_event_regime_gated` | 16,204 | 16,204 | 0 | 16,168 | 99.7778% | 0 |

H 的实际模型 replay 只使用 R-core risk_on 子集，event scores 输出为 30,790 行：

| split | event_n | horizon_complete_n | positive_n | score_nonnull |
|---|---:|---:|---:|---:|
| train | 16,603 | 16,571 | 6,979 | 16,603 |
| validation | 4,457 | 4,455 | 1,401 | 4,457 |
| robustness | 9,730 | 9,711 | 3,130 | 9,730 |

## Feature 与 Preprocessing

- 模型类型：`logistic_regression_balanced_l2`
- 目标标签：`cost_bad_10_20`
- 训练样本：16,571 个 horizon-complete train events
- train positive：6,969
- 模型状态：`trained`
- model feature count：53

H 沿用 E 的 train-only preprocessing：

`train_median_impute__nonnegative_log1p_selected_numeric__train_winsorize_1_99__train_zscore__categorical_train_vocab_one_hot`

关键修补是删除：

`momentum_percentile_20d_lag20`

删除原因：该字段在 E 中 train missing rate 为 `6.70%`，不满足 H 对 allowed t0 feature 的 coverage 要求。本轮没有补源数据，也没有 forward/backward fill，更没有使用未来信息。

Feature contract 中共有 51 个候选字段：

| source_kind | artifact | n |
|---|---|---:|
| event envelope | `event_envelope` | 31 |
| daily panel | `cross_section_feature_panel` | 16 |
| blocked label/episode source | `label_or_episode_source` | 4 |

允许进入 t0 model 的字段为 46 个。保留字段的最大 missing rate：

| split | max missing rate |
|---|---:|
| train | 2.4464% |
| validation | 0.0000% |
| robustness | 0.0000% |

as-of join 审计通过：

- policy：`latest_same_or_prior_event_t0_date`
- join key：`instrument`
- joined rows：40,050
- missing rows：0
- future join rows：0
- min/max feature lag：0 / 0 trading days
- panel feature columns：16

这说明 H 当前失败不是由 feature leakage 或 t0 feature coverage 造成的。

## OOS Separability

OOS readout 显示模型有稳定排序信号。validation 仅作 diagnostic，不参与 threshold tuning。

| split | sample_n | prevalence | ROC-AUC | PR-AUC | top-decile lift | monotonicity | feature coverage |
|---|---:|---:|---:|---:|---:|---|---:|
| train | 16,571 | 42.0554% | 0.6921 | 0.6090 | 1.7095 | monotone increasing | 99.6007% |
| validation | 4,455 | 31.4478% | 0.6819 | 0.4933 | 1.9678 | monotone increasing | 100.0000% |
| robustness | 9,711 | 32.2212% | 0.6858 | 0.5239 | 2.0307 | monotone increasing | 100.0000% |

这个读数的含义是：模型确实能把 bad-cost events 往高分端集中，且 robustness 没有反转。当前问题不在 ranking signal，而在 post-filter 阈值需要同时保留足够 recall。

## Threshold Frontier

H 的正式 grid 为 `[0.85, 0.825, 0.80, 0.775, 0.75, 0.725, 0.70]`，使用 train-only selection。下表是核心 frontier：

| keep | train reject | train cost red. | train any recall | train E1 missed | train E1 n | robustness cost red. | robustness any recall | robustness E1 missed | robustness E1 n |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.850 | 15.0635% | 11.2350% | 90.9502% | 97.5000% | 78 | 17.0554% | 88.3041% | 85.7143% | 72 |
| 0.825 | 17.5571% | 12.5821% | 90.4977% | 96.2500% | 77 | 18.6244% | 88.3041% | 85.7143% | 72 |
| 0.800 | 20.0506% | 14.1389% | 90.0452% | 95.0000% | 76 | 20.4693% | 86.5497% | 84.5238% | 71 |
| 0.775 | 22.5622% | 15.3452% | 89.1403% | 93.7500% | 75 | 21.8745% | 84.7953% | 80.9524% | 68 |
| 0.750 | 25.0557% | 16.7917% | 88.6878% | 93.7500% | 75 | 22.9721% | 83.6257% | 78.5714% | 66 |
| 0.725 | 27.5492% | 18.3380% | 86.4253% | 91.2500% | 73 | 25.1800% | 82.4561% | 76.1905% | 64 |
| 0.700 | 30.0428% | 19.6667% | 85.9729% | 90.0000% | 72 | 26.7125% | 78.9474% | 70.2381% | 59 |

Train gate 的关键缺口：

| keep | train cost >= 15% | train any recall >= 90% | 结论 |
|---:|---|---|---|
| 0.850 | fail，差 3.7650pct | pass，超 0.9502pct | 太保守，cost 不够 |
| 0.825 | fail，差 2.4179pct | pass，超 0.4977pct | cost 仍不够 |
| 0.800 | fail，差 0.8611pct | pass，超 0.0452pct | 最接近，但 cost 未过 |
| 0.775 | pass，超 0.3452pct | fail，差 0.8597pct | cost 过了，recall 掉出 |
| 0.750 | pass，超 1.7917pct | fail，差 1.3122pct | recall 不够 |
| 0.725 | pass，超 3.3380pct | fail，差 3.5747pct | recall 不够 |
| 0.700 | pass，超 4.6667pct | fail，差 4.0271pct | recall 与 robustness E1 n 都不足 |

因此 `risk_on_research_entry_hardening_train_threshold_not_found` 是合理的 fail-closed 结果，不是实现或读取错误。

## Denominator Audit

cost before/after 使用同一 source/split/regime cell 内的 horizon-complete event 分母；incomplete 或 censored events 在 before 与 after 两侧按同一规则排除。

审计结果：

- audited threshold/split rows：21
- pass rows：21
- fail rows：0

raw horizon-complete 分母：

| split | raw_event_n | raw_horizon_complete_n | incomplete_or_censored_n |
|---|---:|---:|---:|
| train | 16,603 | 16,571 | 32 |
| validation | 4,457 | 4,455 | 2 |
| robustness | 9,730 | 9,711 | 19 |

这点很重要：cost reduction 不是靠改变 denominator 做出来的。H 的 cost/recall frontier 可以解释为同口径下真实 tradeoff。

## Density / Concentration

本轮没有 selected threshold，因此 density readout 状态是：

`not_evaluable_no_selected_threshold`

已预声明 caps：

| metric | cap |
|---|---:|
| `formal_event_day_density` | 7.50 |
| `p95_density` | 20.00 |
| `rolling_10d_executable_event_day_density` | 1.80 |
| `rolling_20d_executable_event_day_density` | 2.20 |
| `family_concentration` | 0.30 |
| `board_concentration` | 0.85 |

因为没有 selected event set，density / concentration 不能被解释为 pass。它只能说明 H 已补齐 research-entry 所需的 predeclared config 与 report schema，但 gate replay 仍停在 threshold selection 之前。

density contract source hash：

`b2a483a46a6f1511ede5fd0b58d8696935a3edf7151a7be9785440f8ff9745b6`

## Oracle Gap

Oracle diagnostic 仅用于解释 frontier，不允许进入 final decision。

robustness-best threshold：

`supervised_joint_cost_rejector__08_R_core_event_regime_gated__keep_0725`

该点 robustness 读数较强：

- robustness cost reduction：25.1800%
- robustness any recall：82.4561%
- robustness E1-missed retention：76.1905%
- robustness E1-missed captured n：64

但该点在 train 上 any recall 只有 86.4253%，明显低于 90%。所以它不能被拿来替代 train-selected threshold。这个结果也说明，如果允许从 robustness 或 cost frontier 挑点，很容易得到看起来漂亮但不合规的结论。

## 与 E 的关系

H 删除 `momentum_percentile_20d_lag20` 后，primary frontier 与 E 的形状非常接近。关键点对照：

| threshold family | E train cost | H train cost | E train any recall | H train any recall |
|---|---:|---:|---:|---:|
| around keep 0.80 | 14.1748% | 14.1389% | 90.0452% | 90.0452% |
| around keep 0.75 | 16.8491% | 16.7917% | 88.6878% | 88.6878% |

这说明 lag20 feature 的 coverage 修补没有破坏模型，也没有创造新的假信号。H 的价值在于把 E 的 caveated readout 转成更严格的 admission replay；它没有把边界推过 research-entry。

## Findings / Insight

1. 这条线的主要机会仍然存在：OOS separability 在 train/validation/robustness 三段都稳定，robustness ROC-AUC `0.6858`、top-decile lift `2.0307`，不是随机排序。
2. 当前瓶颈不是 “能不能识别坏事件”，而是 “在保留 bridge / E1-missed capture 的同时能不能筛掉足够 cost”。这正好符合 E/H 的研究定位：post-filter cost rejector，而不是 recall source。
3. train frontier 在 `keep_0800` 与 `keep_0775` 之间断裂，缺口不到 1 个百分点。这意味着方向接近可行，但现在不能为了过 gate 放松同阈值纪律。
4. robustness 侧更乐观，说明模型没有明显 OOS 崩坏；但 H 的正式 selected threshold 必须由 train constrained rule 产生，不能反向用 robustness-best 选择阈值。
5. E1-missed retention 不是当前主要问题。真正要提升的是 cost score 在 train 上的局部排序，使 `keep_0800` 附近多剔除一点 cost-bad，或让 `keep_0775` 附近少损失一点 any recall。
6. 后续如果继续推进，优先级不应是继续调 threshold，而是增强 feature 或 target construction，使 frontier 在 0.80 附近整体上移；否则很容易变成 threshold overfit。

## Non-Claims

- 本结果不是 direct-entry support。
- 本结果不是 production-ready gate。
- 本结果不是交易策略或组合上线证据。
- validation 不参与 threshold tuning。
- transition previous-regime context 未进入 H 的正式训练特征。
