# 11B Archetype Protected Retention Readout Report

## 结论

- final_status: `11B_archetype_protected_retention_statistics_incomplete`
- direct cause: `risk_on_pre_pit_retention_recon_diff_gt_ceiling`
- pre-ceiling retention gate: `ambiguous`
- primary evaluated denominator: 4,665 PIT-valid rows
- retention eligible rows: 4,663 rows = 446 `winner_120_protected` + 4,217 `nonwinner_reference`; `class_unresolved` = 2 rows
- overall PIT-valid winner retention / nonwinner retention / relative retention: 0.8475 / 0.9274 / 0.9138

11B 本轮不是策略回测，也不是 10C override。它只审计 10C `keep_9000` diagnostic reference slice 在 `risk_on ∩ strict PIT-valid` universe 内是否对 `winner_120` 子群有 retention 伤害。当前结果的核心含义是：

1. row identity、scope 和 10C reject decision 还原是干净的；
2. 在 PIT-valid primary scope 内，train split 没有 winner retention 伤害，但 robustness split 出现明显但未能定性的 retention 弱化；
3. validation 读数很差，但 winner 样本只有 16 个，按预注册 power guard 只能 readout；
4. 最终 status 被 ceiling 到 `statistics_incomplete`，不是因为 11B 主表无法计算，而是因为 requirement 要求的 `risk_on pre-PIT` winner retention 与 10C 已发布 frontier 对账超过 0.02 容忍阈值。

因此本报告的结论不能写成 “10C reference slice 非歧视通过”，也不能写成 “应放宽 10C”。更准确的结论是：当前证据提示 robustness 与 shakeout winner 上存在 retention 风险，但 11B 由于 pre-PIT frontier 对账口径冲突，只能作为 diagnostic readout 输入 11C。

## 数据来源与运行边界

| 输入 | 用途 | 本轮读数 |
| --- | --- | --- |
| 11A1 `proxy_scored_denominator.parquet` | PIT-valid evaluated denominator | 4,665 rows |
| 11A1 / 11A2 scope audit | 三层 scope 对账 | 全部 split drift = 0 |
| 10C `post_dedup_false_repair_scores.parquet` | `keep_9000` reject decision | slice rows = 15,802 |
| 10C `false_repair_threshold_frontier.csv` | published winner_retention cross-check | score-cache primary 精确匹配；risk_on pre-PIT 不匹配 |
| 11A1 denominator completeness audit | ST / suspended / delist left-tail 完整性 | `ok` |

边界声明：

- `keep_9000` 是 diagnostic reference slice，不是已部署工作点。
- 10C manifest 当前 `selected_capacity_id = null`、`selected_threshold_id = null`、`selected_cascade_status = blocked`、`source_caveated = true`。
- 本报告不计算 EV、不输出 entry/exit/sizing、不放宽或重训 10C。
- `winner_120` 只用于 audit，不作为 rejector feature。

## Scope 对账

三层 denominator 与 11A1/11A2 完全一致：

| split | score-cache primary | risk_on pre-PIT | PIT-valid evaluated | status |
| --- | ---: | ---: | ---: | --- |
| all | 15,802 | 11,293 | 4,665 | ok |
| train | 8,318 | 5,836 | 1,708 | ok |
| validation | 2,514 | 1,898 | 865 | ok |
| robustness | 4,970 | 3,559 | 2,092 | ok |

PIT/status 完整性也没有发现 left-tail 缺口：PIT membership match rate = 1.0000，ST rows = 0，suspended rows = 0，not-listed rows = 0，`left_tail_status_audit_status = ok`。

### Protected Count

| split | winner_120_protected | nonwinner_reference | class_unresolved |
| --- | ---: | ---: | ---: |
| all | 446 | 4,217 | 2 |
| train | 151 | 1,557 | 0 |
| validation | 16 | 849 | 0 |
| robustness | 279 | 1,811 | 2 |

两个要点：

- PIT-valid primary scope 中 `winner_120_protected` 只占 9.56%，因此 split 级判断必须严格使用 power guard。
- validation 的 winner_n = 16、unique instrument_n = 11，低于 `validation_min_class_n = 30` 和 `validation_min_instrument_n = 20`，所以 validation 只能 readout。

## 10C Slice 还原

| audit item | value |
| --- | --- |
| rejector_slice_mode | `keep_9000_reference_slice` |
| model_id | `regularized_logistic_false_repair_20d_l2_v1` |
| ablation_id | `full` |
| capacity_id / threshold_id | `keep_9000` / `keep_9000` |
| slice_selected_flag | false |
| slice_decision_block_reason | `not_selected` |
| reject decision derivation | `10C_candidate_rejected_flag` |
| materialization hit rate | 1.0000 |
| reject join key | `sample_id|selected_target_id|denominator_id|input_event_key` |
| duplicate reject join key | 0 |
| risk_on pre-PIT join hit rate | 1.0000 |
| PIT-valid join hit rate | 1.0000 |
| instrument/date/split mismatch | 0 / 0 / 0 |

这说明 11B 没有把 `(instrument, event_t0_date)` 当作主 join，也没有混入多 threshold slice。当前 final status 的问题不在 row-level decision reconstruction。

## 与 10C Frontier 的对账

11B 同时输出两个对账口径：

1. score-cache primary scope：与 10C frontier 的 published winner_retention 完全一致；
2. risk_on pre-PIT scope：按 11B requirement 要求与 10C frontier 比较，但三 split 均超出 0.02 容忍阈值。

| scope | split | winner_n | 11B recomputed | 10C published | abs diff | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| score_cache_primary | train | 1,491 | 0.8960 | 0.8960 | 0.0000 | ok |
| score_cache_primary | validation | 161 | 0.7578 | 0.7578 | 0.0000 | ok |
| score_cache_primary | robustness | 995 | 0.8714 | 0.8714 | 0.0000 | ok |
| risk_on_pre-PIT | train | 669 | 0.8356 | 0.8960 | 0.0605 | diff_gt_ceiling |
| risk_on_pre-PIT | validation | 57 | 0.5789 | 0.7578 | 0.1788 | diff_gt_ceiling |
| risk_on_pre-PIT | robustness | 498 | 0.7992 | 0.8714 | 0.0722 | diff_gt_ceiling |

发现：

- 10C frontier 的 published winner_retention 是在 score-cache primary denominator 上形成的；11B 的 risk_on pre-PIT slice 是更窄的 11A1/11A2 analysis scope。
- 一旦限定到 risk_on pre-PIT，winner retention 明显下降：train 下降 6.05pct，validation 下降 17.88pct，robustness 下降 7.22pct。
- 因为 requirement 把 risk_on pre-PIT vs 10C frontier 差异列为 `statistics_incomplete` ceiling 条件，所以本轮即使 PIT-valid retention gate 可计算，也不能给出最终 non-discriminatory / discriminatory 定性。

Insight:

这个差异本身是重要发现。它说明 10C 发布 frontier 的 winner retention 不应直接外推到 11B 的 risk_on executable universe；risk_on 过滤不是中性采样，至少对 winner retention 读数有实质影响。11C 如果继续消费 10C reference slice，应该把 10C frontier retention 与 11B risk_on retention 分开报告。

## Primary PIT-Valid Retention Gate

| split | winner_n | winner_retained | winner_retention | nonwinner_n | nonwinner_retention | relative winner/nonwinner | CI 5%-95% | P(relative < 0.90) | status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| all | 446 | 378 | 0.8475 | 4,217 | 0.9274 | 0.9138 | [0.8738, 0.9516] | 0.251 | readout_only |
| train | 151 | 145 | 0.9603 | 1,557 | 0.9383 | 1.0234 | [0.9898, 1.0519] | 0.000 | non_discriminatory |
| validation | 16 | 9 | 0.5625 | 849 | 0.9376 | 0.6000 | [0.3243, 0.8119] | 0.993 | validation_low_power |
| robustness | 279 | 224 | 0.8029 | 1,811 | 0.9133 | 0.8791 | [0.8166, 0.9313] | 0.722 | ambiguous |

### Train

Train 是唯一清晰的非负面 split：

- winner retention = 145 / 151 = 0.9603；
- nonwinner retention = 1,461 / 1,557 = 0.9383；
- relative retention = 1.0234；
- bootstrap CI = [0.9898, 1.0519]，完整高于 floor = 0.90。

Interpretation: 在 train 的 PIT-valid universe 内，`keep_9000` reference slice 没有系统性误伤 winner；winner retention 反而略高于 nonwinner。

### Validation

Validation 读数非常弱，但不能作为 gate：

- winner_n = 16，unique winner instrument_n = 11；
- winner retention = 9 / 16 = 0.5625；
- relative retention = 0.6000；
- CI = [0.3243, 0.8119]，完全低于 0.90。

Interpretation: validation 显示强烈 winner retention 伤害信号，但样本功率不足。按预注册规则，它只能提示风险，不能改写 train/robustness gate，也不能单独判 discriminatory。

### Robustness

Robustness 是本轮最关键的 primary readout：

- winner retention = 224 / 279 = 0.8029；
- nonwinner retention = 1,654 / 1,811 = 0.9133；
- relative retention = 0.8791；
- CI = [0.8166, 0.9313]，跨过 0.90 floor；
- P(relative < 0.90) = 0.722。

Interpretation: robustness 中 winner retention 明显低于 nonwinner，但 CI 上界仍高于 floor，按预注册 gate 是 `ambiguous`，不是正式 `discriminatory`。这不是 “没有问题”，而是 “存在方向一致的 retention 风险，但不能按 11B gate 定性”。

### Bootstrap Block Sensitivity

| split | instrument direction | event-block direction | conflict |
| --- | --- | --- | --- |
| train | non_discriminatory | non_discriminatory | no |
| validation | discriminatory | discriminatory | no, but low power |
| robustness | ambiguous | ambiguous | no |
| all | ambiguous | ambiguous | no |

Instrument-block 与 event-block 方向没有冲突，因此本轮不存在 `episode_block_retention_conflict`。这提高了 primary readout 的可信度，但不能绕过 pre-PIT frontier ceiling。

## Secondary Seed Subgroup Readout

Seed 子群只用于解释 retention 风险集中在哪里，不进入 final status。

| subgroup | all eligible_n | retention | relative vs nonwinner | CI 5%-95% | P(relative < 0.90) | CI below floor |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| winner_shakeout_seed | 97 | 0.6907 | 0.7448 | [0.6564, 0.8381] | 0.995 | true |
| winner_volatile_chop_seed | 70 | 0.8143 | 0.8780 | [0.7833, 0.9677] | 0.652 | false |
| winner_gap_event_seed | 234 | 0.8718 | 0.9400 | [0.8945, 0.9824] | 0.070 | false |

Split 视角：

| subgroup | train | validation | robustness |
| --- | --- | --- | --- |
| winner_shakeout_seed | 22/23 retained, underpowered | 0/3 retained, underpowered | 45/71 retained, relative 0.6940, CI [0.5919, 0.7983] |
| winner_volatile_chop_seed | 13/13 retained, underpowered | 2/5 retained, underpowered | 42/52 retained, relative 0.8844, CI [0.7649, 0.9966] |
| winner_gap_event_seed | 65/68 retained, ok | 4/7 retained, underpowered | 135/159 retained, relative 0.9297, CI [0.8739, 0.9881] |

Multiple-comparison audit:

- tested subgroup cells = 9；
- CI-below-floor significant cells = 1；
- null expected significant cells = 0.244；
- null significant cells p95 = 1.0；
- actual_exceeds_null_p95_flag = false；
- multiple_comparison_status = `ok`。

Finding:

`winner_shakeout_seed` 是 retention 伤害最集中的 seed 子群，尤其在 robustness split。全样本 shakeout winner retention 只有 0.6907，relative retention 的 CI 完整低于 0.90。可是经过预注册 multiple-comparison audit 后，这仍然只能作为解释性证据，不是 primary gate 结果。

Insight:

11A1 已经说明 t0 proxy family 不能作为 acceptance gate；11B 的 seed readout 与这一点并不矛盾。这里的信号更像是 “10C reference slice 的 winner 误伤在 shakeout-like winners 上更集中”。它可以帮助 11C 设计分层 reporting 或 sensitivity readout，但不能在 11B 内授权 carve-out。

## Why Final Status Is Statistics Incomplete

本轮有三件事同时成立：

1. Scope 与 row identity 完整：15,802 / 11,293 / 4,665 三层对账全部 ok，10C reject join hit rate = 1.0。
2. PIT-valid primary retention gate 可读：train = non-discriminatory，robustness = ambiguous，validation = low power。
3. Requirement 要求的 risk_on pre-PIT winner_retention vs 10C frontier 对账失败：三 split diff 均超过 0.02。

因此最终 status 必须是：

```text
11B_archetype_protected_retention_statistics_incomplete
```

这不是 input failure，也不是 bootstrap failure；它是一个明确的 contract ceiling。换句话说，11B 当前已经告诉我们 primary PIT-valid retention 的方向，但不能把该方向升级为正式的 non-discriminatory 或 discriminatory 结论。

## Findings

1. 10C `keep_9000` reference slice 的 reject decision 被正确还原；没有发现 join drift、重复 key 或 identity mismatch。
2. 10C published frontier 与 score-cache primary denominator 完全一致，说明 11B 没有误读 10C frontier。
3. risk_on pre-PIT winner retention 明显低于 10C published frontier，说明 risk_on analysis scope 不是 frontier retention 的简单子样本。
4. PIT-valid train split 对 winner 没有 retention 伤害；relative retention = 1.0234，CI 完整高于 0.90。
5. PIT-valid robustness split 存在 winner retention 弱化；relative retention = 0.8791，P(relative < 0.90) = 0.722，但 CI 跨 floor，因此是 ambiguous。
6. Validation 的方向很差，但 winner_n = 16，不能驱动 final status。
7. Seed readout 显示 `winner_shakeout_seed` 是误伤最集中的 winner 子群；robustness shakeout relative retention 只有 0.6940，CI 完整低于 0.90。
8. Multiple-comparison audit 没有显示 seed subgroup 结果超过 null p95，因此 seed 结论只能作为解释线索。

## Insight For 11C

11C 不应把 11B 当成 “10C retention 非歧视通过” 的上游。更稳妥的使用方式是：

- 将 11B 状态传入 11C 为 `statistics_incomplete` / `readout-only`；
- 在 11C replay 中显式报告 Lane A / Lane B 的 winner retention、shakeout winner retention 和 robustness split retention；
- 不用 11B 授权替代或放宽 10C；
- 如果 11C 发现 K=3 two-stage policy 的收益来自被 10C reference slice 更容易 reject 的 shakeout winners，需要把这部分作为单独 sensitivity，而不是直接认定为可交易 alpha；
- 11C 的主结论仍必须由带成本、可成交性、资金占用、涨跌停约束后的 net EV / exposure-day 与 failure exposure 共同决定。

一句话总结：11B 没有给 10C `keep_9000` reference slice 发 “非歧视合格证”；它更像是提示 11C，winner retention 风险主要出现在 robustness 与 shakeout-like winners 上，同时当前 10C frontier retention 口径不能直接代表 11B 的 risk_on executable universe。
