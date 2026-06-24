# 13C Morphology-Orthogonal Residual Importance Diagnostic Report

## 裁决

单行裁决：selected state `repair_range_participation_core_30` 存在 morphology-orthogonal winner / ranking readout，但不存在足以授权下一步的 selected-state residual utility edge；`decision_state = 13C_stop_residual_probability_only_no_utility`。

| 字段 | 结果 |
|:---|:---|
| `next_allowed_requirement` | `none` |
| `sequence_mining_authorized` | `False` |
| `meta_labeling_authorized` | `False` |
| `bet_sizing_authorized` | `False` |
| `primary_failure_reason` | `residual_winner_positive_but_utility_non_positive` |
| `residual_winner_gate_status` | `residual_readout_probability_only_no_utility` |
| `clustered_mda_gate_status` | `pass` |
| `incremental_utility_gate_status` | `pass` |
| `sample_uniqueness_gate_status` | `pass_with_exact_t1` |
| `residual_calibration_status` | `residual_drift_caveat` |
| `residual_badside_readout_status` | `caveat_left_tail_residual_positive` |

13C 不推翻 13A3。13A3 否决的是 direct winner-buy / sequence mining 的 total native effect；13C 只检查 broad drawdown / reversal morphology 被剥离后是否还剩 residual information。这里的关键不是“完全没有信息”，而是信息停在 probability / ranking 层面：selected state 在 validation 和 robustness 的 residual winner uplift 都为正，但 validation 的 residual utility per entry 为负，因此不能授权 13D，也不能把 compression-repair branch 重新升格为 sequence mining 或 bet sizing 候选。

## 数据完整性与审计边界

本轮报告只使用 13C 已生成的 publishable tables 和 manifest，不重新运行模型、不更新代码。输入层共有 37 个 artifact 进入 `input_artifact_audit.csv`，全部 `read_status = pass`。关键 row-truth 来源如下：

| 输入类别 | 行数 / 覆盖 | 审计结论 |
|:---|---:|:---|
| PIT executable daily | 1,140,000 rows | `pass` |
| PIT membership daily | 1,140,500 rows | `pass` |
| qfq daily directory | 4,598 files | `directory` |
| global regime calendar | 1,912 rows | `pass` |
| 13A native universe cache | 431,239 rows | `pass` |
| 13A2 compression base cache | 111,299 rows | `pass` |
| 13A2 directional filter matrix cache | 431,239 rows | `pass` |
| 13A3 composite state matrix cache | 431,239 rows | `pass` |

上游 lineage audit 共 49 项全部通过。`row_id` 唯一性、`instrument x reference_date` 唯一性、filter / state matrix 覆盖、compression base membership、required composite state membership、PIT `reference_pos` / `entry_pos` / `entry_price`、entry executability、horizon completeness、selected label、horizon sessions 和 same-bar priority 都通过。13A2 / 13A3 cache 的 manifest schema hash 与当前文件一致；13A local cache schema 在上游 manifest 中未声明，因此本轮记录为 `not_declared` 但不作为 fail。

| Lineage 来源 | pass 项数 | 说明 |
|:---|---:|:---|
| 13A | 13 | native row key、PIT mapping、label lineage |
| 13A2 | 6 | compression base 与 directional filter lineage |
| 13A3 | 14 | upstream decision、state matrix、row-level cache premise |
| 13A / 13A2 config | 10 | selected label 参数一致 |
| 13C config | 1 | same-bar priority lower-first |
| cache schema | 5 | manifest schema hash 或 not-declared audit |

row-level rebuild audit 也全部通过，说明 13C 的 residual panel 可以逐行复现上游 selected label 与 composite membership，不是从报告文本或 aggregate readout 反推。

| split | row_count | instruments | horizon_complete | label_match | state_membership_match | required_feature_nonnull | PIT status | status |
|:---|---:|---:|---:|---:|---:|---:|:---|:---|
| train | 216,794 | 1,119 | 1.000 | 1.000 | 1.000 | 1.000 | pass | pass |
| validation | 61,307 | 766 | 1.000 | 1.000 | 1.000 | 1.000 | pass | pass |
| robustness | 130,614 | 769 | 1.000 | 1.000 | 1.000 | 1.000 | pass | pass |

Feature availability 不是本轮失败原因。5 个 feature cluster 共 17 个 features 全部 `pass`，其中 `range_width_20d` 虽是 optional feature，但本轮也可用。13 个 morphology / denominator anchors 全部可用，均以 train-frozen zscore 或 train-frozen quantile bucket 构造。

## Selected State Raw vs Residual Readout

Selected state 为 `repair_range_participation_core_30`。注意下面 residual readout 的 `treated_n` 是通过 cell support gate 后的可比较 treated rows，不完全等于 sample uniqueness audit 里的全部 selected events。train 中 selected events 为 6,232，但在 residual support gate 下只有 3,653 个 treated rows 进入同 cell comparison；validation 为 2,589 / 2,627，robustness 为 4,801 / 4,813。

| split | treated_n | control_n | cells supported / total | raw winner diff | residual winner diff | raw utility | residual utility | residual utility vs broad | residual gate | bad-side caveat |
|:---|---:|---:|:---|---:|---:|---:|---:|---:|:---|:---|
| train | 3,653 | 11,195 | 77 / 545 | 0.0915 | 0.1025 | 0.0103 | 0.0109 | 0.0169 | pass | no caveat |
| validation | 2,589 | 38,861 | 5 / 9 | 0.1036 | 0.0828 | -0.0076 | -0.0020 | 0.0069 | probability-only | left-tail positive |
| robustness | 4,801 | 99,361 | 6 / 7 | 0.0870 | 0.0584 | 0.0018 | 0.0074 | -0.0096 | pass | left-tail positive |

核心发现有三点：

1. Winner uplift 没有消失。剥离 morphology / denominator cell mean 后，validation residual winner diff 仍为 +0.0828，robustness 为 +0.0584。
2. Utility translation 不稳定。validation 的 residual utility per entry 为 -0.0020，低于 0；因此即使 winner probability 为正，也不能通过 selected-state residual utility gate。
3. Bad-side residual 没有被完全消除。validation 的 residual lower-first diff 为 +0.0117，robustness 为 +0.0314；robustness 的 residual fast-fail diff 为 +0.0106，触及 fast-fail caveat 阈值附近。这说明 residual probability uplift 伴随左尾风险，而不是干净的 payoff improvement。

Utility reconciliation 使用全部 selected events，并与 13A3 median-barrier utility readout 对齐；它不是 final gate，但能解释为什么本轮不能把 probability uplift 当作经济 edge。

| split | cost tier | selected events | row utility per entry | total indexed utility | 13A3 median-barrier utility | row vs 13A3 delta |
|:---|:---|---:|---:|---:|---:|---:|
| train | 0bps | 6,232 | 0.0125 | 0.000361 | 0.0130 | -0.000452 |
| train | 50bps | 6,232 | 0.0075 | 0.000217 | 0.0080 | -0.000452 |
| train | 100bps | 6,232 | 0.0025 | 0.000073 | 0.0030 | -0.000452 |
| validation | 0bps | 2,627 | -0.0025 | -0.000107 | -0.0018 | -0.000685 |
| validation | 50bps | 2,627 | -0.0075 | -0.000321 | -0.0068 | -0.000685 |
| validation | 100bps | 2,627 | -0.0125 | -0.000535 | -0.0118 | -0.000685 |
| robustness | 0bps | 4,813 | 0.0068 | 0.000250 | 0.0074 | -0.000651 |
| robustness | 50bps | 4,813 | 0.0018 | 0.000066 | 0.0024 | -0.000651 |
| robustness | 100bps | 4,813 | -0.0032 | -0.000118 | -0.0026 | -0.000651 |

Insight：validation 已经在 0bps 时为负，50bps / 100bps 后继续恶化；robustness 在 50bps 勉强为正，但 100bps 转负。这个形态更像“上涨概率 readout 能排序一部分样本，但 payoff asymmetry 与成本会吞掉 selected event 的收益”，不是可以进入交易或仓位建模的 edge。

## 全部 Required States 对照

13C 允许报告全部 required states，但授权必须基于 predeclared selected state，不能因为其他 state 更好而事后换 state。全 state 对照显示，selected state 的失败不是单点异常：多数 repair-participation state 在 validation 都出现 residual utility <= 0。

| state_id | validation residual winner | validation residual utility | robustness residual winner | robustness residual utility | OOS readout |
|:---|---:|---:|---:|---:|:---|
| `repair_range_participation_core_30` | 0.0828 | -0.0020 | 0.0584 | 0.0074 | selected, probability-only |
| `repair_sma_participation_core_30` | 0.0882 | -0.0016 | 0.0615 | 0.0075 | probability-only |
| `repair_close_position_participation_core_30` | 0.0871 | -0.0019 | 0.0613 | 0.0074 | probability-only |
| `repair_range_participation_broad_40` | 0.0697 | -0.0033 | 0.0576 | 0.0073 | probability-only |
| `repair_ret60_volume_suspect_30` | 0.1160 | 0.0045 | 0.0540 | 0.0058 | non-selected positive, hypothesis-only |
| `repair_drawdown_amount_suspect_30` | 0.0716 | -0.0034 | 0.0684 | 0.0081 | probability-only |

`repair_ret60_volume_suspect_30` 是唯一在 validation 和 robustness 同时呈现 positive residual utility 的非 selected state。但它属于 suspect branch，且本需求明确禁止 validation / robustness 事后换 state。AFML 上这类结果只能作为 hypothesis-generating 线索，不能升级 13C 裁决。

## Baseline vs Augmented Model

Baseline model 只使用 drawdown morphology 与 denominator controls；augmented model 额外加入 compression、position strength 与 participation clusters。Winner target 和 `utility_positive_50bps` target 的 AUC / utility proxy delta 在两个 OOS split 都为正。

| target | split | baseline AUC | augmented AUC | AUC delta | baseline utility proxy | augmented utility proxy | utility delta | status |
|:---|:---|---:|---:|---:|---:|---:|---:|:---|
| winner_positive | validation | 0.6379 | 0.6453 | 0.0074 | -0.0148 | -0.0041 | 0.0107 | pass |
| winner_positive | robustness | 0.6360 | 0.6448 | 0.0088 | 0.0002 | 0.0012 | 0.0010 | pass |
| lower_first | validation | 0.5922 | 0.6085 | 0.0164 | -0.0254 | -0.0280 | -0.0026 | auc-only |
| lower_first | robustness | 0.6270 | 0.6498 | 0.0229 | -0.0165 | -0.0408 | -0.0243 | auc-only |
| fast_fail | validation | 0.6740 | 0.6995 | 0.0256 | -0.0244 | -0.0235 | 0.0008 | pass |
| fast_fail | robustness | 0.6361 | 0.6736 | 0.0375 | -0.0110 | -0.0203 | -0.0094 | auc-only |
| utility_positive_50bps | validation | 0.6379 | 0.6453 | 0.0074 | -0.0148 | -0.0041 | 0.0107 | pass |
| utility_positive_50bps | robustness | 0.6360 | 0.6448 | 0.0088 | 0.0002 | 0.0012 | 0.0010 | pass |

Insight：model-level readout 的确说明非 morphology features 仍有 ranking information；但 model utility proxy 是 evaluation split 内 top-N 排序上界，不能替代 predeclared selected state 的 residual utility gate。13C 的 stop 不是因为模型完全看不到信息，而是因为 selected event definition 没有稳定转化为 after-cost utility。

## Clustered MDA

Clustered MDA 更清楚地揭示了信息结构。`cluster_compression` 对 winner AUC 的贡献最大：validation MDA importance 为 +0.0899，robustness 为 +0.0637；这说明 compression cluster 对 winner probability 的解释力没有被 broad drawdown morphology 完全吸收。

| target | split | cluster | metric | baseline | permuted mean | importance | CI low | status |
|:---|:---|:---|:---|---:|---:|---:|---:|:---|
| winner_positive | validation | compression | auc | 0.6453 | 0.5554 | 0.0899 | 0.0883 | positive |
| winner_positive | robustness | compression | auc | 0.6448 | 0.5811 | 0.0637 | 0.0631 | positive |
| winner_positive | validation | participation | auc | 0.6453 | 0.6405 | 0.0048 | 0.0042 | positive |
| winner_positive | robustness | participation | auc | 0.6448 | 0.6332 | 0.0117 | 0.0114 | positive |
| utility_positive_50bps | validation | compression | utility_proxy | -0.0041 | -0.0123 | 0.0082 | 0.0077 | positive |
| utility_positive_50bps | robustness | compression | utility_proxy | 0.0012 | 0.0030 | -0.0018 | -0.0027 | not positive |
| utility_positive_50bps | validation | position_strength | utility_proxy | -0.0041 | -0.0083 | 0.0041 | 0.0039 | positive |
| utility_positive_50bps | robustness | position_strength | utility_proxy | 0.0012 | -0.0031 | 0.0043 | 0.0041 | positive |
| utility_positive_50bps | validation | participation | utility_proxy | -0.0041 | -0.0086 | 0.0044 | 0.0042 | positive |
| utility_positive_50bps | robustness | participation | utility_proxy | 0.0012 | -0.0036 | 0.0048 | 0.0044 | positive |

Compression cluster 的 readout 是本轮最有价值的发现：它对 winner probability 很强，但在 robustness 的 utility proxy 上转为负贡献。这与 selected state 的 probability-only failure 一致，说明 compression 变量更像“能识别反弹概率或路径形态的条件变量”，不是独立的 payoff generator。Position strength 与 participation cluster 在 utility proxy 上更稳，但它们只是模型排序信息，不能倒推 selected composite state 可交易。

## Sample Uniqueness / Overlap

Exact `t1` event span 已用 `entry_pos + first-touch / vertical-horizon offset` 重建；instrument-month block 只保留为 proxy context。全部 6 个 required states 在 train / validation / robustness 都为 `pass_with_exact_t1`，不再需要把 exact t1 rebuild 留给 13D。

| split | selected events | mean uniqueness | median uniqueness | p10 uniqueness | mean concurrency | p95 concurrency | instrument-month blocks | effective block n | status |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| train | 6,232 | 0.4035 | 0.3241 | 0.1632 | 3.9110 | 8.0 | 2,248 | 1,451.8 | pass_with_exact_t1 |
| validation | 2,627 | 0.4255 | 0.3333 | 0.1659 | 3.7496 | 8.0 | 1,126 | 749.7 | pass_with_exact_t1 |
| robustness | 4,813 | 0.4197 | 0.3333 | 0.1698 | 3.7258 | 8.0 | 1,806 | 1,151.9 | pass_with_exact_t1 |

Insight：overlap 不是本轮 blocker。事件平均并发约 3.7 到 3.9，p95 concurrency 为 8，说明后续若重开 meta-labeling，也必须继续使用 event-span uniqueness / purging，而不是简单按 row 独立训练。但在本轮 13C 中，sample uniqueness 已经可审计，不能解释 selected-state utility failure。

## Residual Calibration Caveat

Residual calibration 比较 train-fitted expected cell rates 与 validation / robustness realized rates。结果触发 `residual_drift_caveat`，并已进入 final decision 的 `residual_drift_caveat_from_13c = True` 与 `calibration_recheck_required = True`。

| target | split | predicted mean from train | realized mean | calibration error | weighted abs error | max cell abs error | status |
|:---|:---|---:|---:|---:|---:|---:|:---|
| winner_positive | validation | 0.1584 | 0.0959 | -0.0625 | 0.0625 | 0.1183 | residual drift |
| winner_positive | robustness | 0.1586 | 0.1364 | -0.0223 | 0.0223 | 0.0370 | residual drift |
| lower_first | validation | 0.3584 | 0.3993 | 0.0408 | 0.0408 | 0.1048 | residual drift |
| lower_first | robustness | 0.3581 | 0.2696 | -0.0884 | 0.0884 | 0.1124 | residual drift |
| fast_fail | validation | 0.0462 | 0.0359 | -0.0103 | 0.0106 | 0.0333 | pass |
| fast_fail | robustness | 0.0461 | 0.0358 | -0.0103 | 0.0109 | 0.0386 | pass |
| utility_50bps | validation | -0.0115 | -0.0240 | -0.0125 | 0.0125 | 0.0278 | residual drift |
| utility_50bps | robustness | -0.0114 | -0.0059 | 0.0055 | 0.0056 | 0.0139 | residual drift |

Calibration insight：train-fitted cells overpredict validation winner rate by 6.25pp and overpredict validation utility by 1.25pp. Robustness 的 winner drift 较小但仍超过阈值，utility drift 方向反转。这个形态说明 residual readout 中仍混入 calendar / regime drift；即使某些 non-selected state 看起来 positive，也必须先做 calibration / regime stability preflight，不能直接训练 meta-label。

## Search Accounting

13C 是 posthoc diagnostic，不是 confirmatory test。Search audit 记录如下：

| 字段 | 值 |
|:---|---:|
| required_state_n | 6 |
| feature_cluster_n | 5 |
| anchor_n | 8 |
| model_family_n | 1 |
| target_n | 4 |
| effective_search_space_n | 960 |
| hyperparameter_search_used | False |
| validation_used_for_selection | False |
| robustness_used_for_selection | False |
| confirmatory_status | False |
| search_accounting_status | diagnostic_posthoc_not_confirmatory |

因此，本轮最强的结论是 negative gate，而不是 positive discovery。Negative gate 可以阻止错误推进；positive-looking non-selected readout 只能作为下一轮需求的候选问题描述，不能作为授权依据。

## Findings

1. 13C 的数据链路已经足够干净。PIT、label lineage、row-level rebuild、feature availability、state membership、exact t1 uniqueness 都通过；本轮 stop 不是实现或数据缺失导致的保守失败。
2. Selected state 的 winner residual 为正，但 utility residual 在 validation 为负。validation 是 hard gate，所以 final decision 必须是 `13C_stop_residual_probability_only_no_utility`。
3. Compression cluster 确实保留 morphology-orthogonal ranking information。它对 winner AUC 的 MDA contribution 在 validation / robustness 分别为 +0.0899 / +0.0637，是最强 cluster；但 robustness 的 utility proxy contribution 为 -0.0018，说明它没有稳定经济转化。
4. Bad-side residual caveat 与 utility failure 同向。Validation / robustness residual lower-first diff 分别为 +0.0117 / +0.0314，robustness residual fast-fail diff 为 +0.0106。这解释了为什么 winner probability uplift 不能直接等价为 payoff edge。
5. Non-selected `repair_ret60_volume_suspect_30` 在两个 OOS split 都有 positive residual utility，但这是 hypothesis-generating 结果。按 13C 预注册边界，不允许事后替换 selected state。
6. Calibration drift 使任何下游正向解释都必须降级。Winner / lower-first / utility target 均触发 residual drift caveat，说明 cell residualization 仍可能吸收 regime 或 calendar shift。

## AFML Insight

AFML 的处理方式不是继续挖同一个 event branch，而是把问题拆成三个层级：

1. `event authorization`：selected compression-repair event 不通过，因为它只提供 probability uplift，不能稳定提供 cost-adjusted residual utility。
2. `feature usefulness`：compression、position strength、participation features 仍有用，但它们更适合作为 meta-label / participation filter 的候选输入，而不是作为独立 primary event。
3. `research boundary`：若以后要研究 `repair_ret60_volume_suspect_30` 或 compression cluster 的 ranking signal，必须新建需求，预注册 state、target、calibration、purging 和 utility gate；不能在 13C 内把 posthoc 发现升级成授权。

本轮结论应写成：compression-repair family 没有通过 selected-state residual utility gate；compression features 仍有 diagnostic value，但应降级为 feature research / meta-label filter candidate，而不是继续作为 native winner event 或 sequence mining seed。

## Negative / Positive Boundary

若 13C negative，本轮不允许：

- 不允许进入 `requirement_13d_compression_repair_meta_labeling_feasibility_preflight.md`；
- 不允许重启 13B sequence mining；
- 不允许基于 selected state 做 bet sizing；
- 不允许用 MDA positive 或 non-selected state positive 覆盖 selected-state hard gate。

若未来另开需求，最小可信问题应是：在预注册 state 与 exact event-span uniqueness 下，compression / participation features 是否能作为 risk-control 或 meta-label filter 降低 lower-first / fast-fail，而不是再次寻找 direct winner-buy alpha。
