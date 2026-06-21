# 12A6c 两阶段 fast-fail rejector / continuation feasibility 报告

## 结论

12A6c 当前结论是 `12A6c_stage1_partial`。输入 gate 全部通过，但 stage-1 和 stage-2 的 train-frozen threshold health 都失败，因此不能进入 12A7 OOS validation；下一步应进入 `requirement_12a6d_stage1_rejector_feature_or_label_revision.md`。

| item | value |
|---|---:|
| input gate | pass |
| final decision | `12A6c_stage1_partial` |
| stage-1 status | `partial_c0_or_train_only` |
| stage-2 status | `failed` |
| stage-1 train threshold | 0.402579 |
| stage-2 train threshold | 0.137815 |
| gate failure reasons | `stage1_threshold_health_failed;stage2_threshold_health_failed;stage1_partial_c0_or_train_only` |

核心发现：模型不是完全没有排序能力。Stage-1 fast-fail score bucket 在 train/validation/robustness 都有单调性；Stage-2 continuation score bucket 也有单调性。但当严格按需求使用 train split 固定阈值外推时，stage-1 的 OOS 保留比例从 50% 膨胀到 84.5%/78.4%，stage-2 的 OOS 继续比例收缩到 37.7%/31.7%。这说明当前模型的 score calibration / threshold transport 不稳，不能把 split 内排序优势解释为可支持的两阶段策略。

## 输入与样本纪律

本次读数来自已生成的 publishable artifacts，没有重新生成代码或修改 runner。`input_artifact_audit.csv` 中 17 个输入 artifact 全部 `read_status=pass` 且 `schema_status=pass`，包括 12A4 meta-label universe / feature matrix、12A6b fast-fail baseline、12A2 decision、12A0/12A1 decision、global regime calendar、PIT executable daily、stock daily CSV directory 和 requirement。

| artifact group | status | note |
|---|---:|---|
| upstream event / feature artifacts | pass | 12A4 universe、targets、feature dictionary、feature matrix 全部可读 |
| 12A6b baselines | pass | matched random、fast-fail uplift、conditional continuation、decision 全部可读 |
| upstream gates | pass | 12A2 supported decision、12A0/12A1 decision、global regime calendar、PIT executable daily 全部通过 schema gate |
| local feature matrix | pass | 15,113 rows x 116 columns；publishable feature matrix 不含 target/evaluable label 泄漏列 |

PIT 边界如下：

- Stage-1 decision time: event_t0 close，只使用 12A4 t0 PIT features。
- Stage-1 target: `fast_fail_L10_H20`，即 H20 内先触达 -10% lower barrier。
- Stage-2 decision time: entry+20 close；reference price 是 entry+21 executable open。
- Stage-2 target: `continuation_U20_L10_H2_20`，即 H2=20 内 +20% upper barrier 先于 -10% lower barrier。
- Threshold policy: train split 固定预算选 score boundary，validation/robustness 只复用 train-frozen threshold；不允许在每个 split 内重新选 50%。

## 样本漏斗

C0 risk_on universe 共 15,113 个 executable events。Stage-1 所有事件都可评估；stage-2 path eligibility 是 H20 未 fast-fail 且 stage-2 reference / horizon 完整。当前 primary model 的 stage-1 keep 后，stage-2 primary evaluable 为 7,185 个。

| split | events | fast-fail n | fast-fail rate | no-fast-fail n | primary stage-1 keep n | stage-2 primary evaluable n | stage-2 base continuation rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 8,303 | 3,476 | 0.4186 | 4,827 | 4,152 | 3,107 | 0.1516 |
| validation | 2,151 | 731 | 0.3398 | 1,420 | 1,818 | 1,292 | 0.0782 |
| robustness | 4,659 | 1,425 | 0.3059 | 3,234 | 3,651 | 2,786 | 0.1228 |
| all | 15,113 | 5,632 | 0.3727 | 9,481 | 9,621 | 7,185 | 0.1272 |

这里已经能看到两个结构性问题。第一，train 的 fast-fail rate 最高，robustness 最低；如果 score 的绝对标尺没有处理这个时间漂移，train 阈值天然会在 OOS 上改变实际预算。第二，stage-2 base continuation 在 validation 只有 0.0782，而 robustness 回升到 0.1228，说明 continuation 本身也有明显年份/行情依赖。

## Threshold Health

Primary logistic regression 的 train budget 被精确控制在 50% 左右，但 OOS budget 明显漂移。这个 gate 是当前失败的直接原因。

| stage | split | target budget | actual budget | abs delta | threshold health |
|---|---:|---:|---:|---:|---|
| stage-1 | train | 0.5000 | 0.5001 | 0.0001 | pass |
| stage-1 | validation | 0.5000 | 0.8452 | 0.3452 | fail |
| stage-1 | robustness | 0.5000 | 0.7836 | 0.2836 | fail |
| stage-1 | all | 0.5000 | 0.6366 | 0.1366 | fail |
| stage-2 | train | 0.5000 | 0.5002 | 0.0002 | pass |
| stage-2 | validation | 0.5000 | 0.3769 | 0.1231 | fail |
| stage-2 | robustness | 0.5000 | 0.3166 | 0.1834 | fail |
| stage-2 | all | 0.5000 | 0.4068 | 0.0932 | fail |

Challenger shallow tree 也没有解决 transport 问题：stage-1 validation / robustness actual budget 为 0.7620 / 0.6611，stage-2 validation / robustness actual budget 为 0.2833 / 0.2753。也就是说，预算漂移不是 logistic 特有问题，而是当前 feature/label/time split 组合下的普遍现象。

## Stage-1 Fast-fail Rejector

Stage-1 primary model 是 `logistic_regression_l2`，使用 89 个 t0 PIT features，train_event_n=8,303，train positive rate=0.4186。LightGBM diagnostic challenger 因依赖不可用而跳过，不参与 gate。

| split | keep n | retention | keep fast-fail rate | C0 baseline | random p50 | delta vs random p50 | delta vs C0 | best single feature | model minus best single |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 4,152 | 0.5001 | 0.2517 | 0.4186 | 0.3137 | -0.0620 | -0.1670 | 0.2876 | -0.0359 |
| validation | 1,818 | 0.8452 | 0.2893 | 0.3398 | 0.2984 | -0.0091 | -0.0505 | 0.2091 | 0.0802 |
| robustness | 3,651 | 0.7836 | 0.2369 | 0.3059 | 0.2276 | 0.0093 | -0.0689 | 0.1554 | 0.0816 |
| all | 9,621 | 0.6366 | 0.2532 | 0.3727 | 0.2781 | -0.0249 | -0.1195 | 0.2363 | 0.0169 |

读数解释：

- Train 上 stage-1 有明确效果：fast-fail rate 从 0.4186 降到 0.2517，且比 random p50 低 0.0620，比 best single feature 还低 0.0359。
- Validation 上仍低于 C0 baseline 和 random p50，但优势明显变弱；更关键的是 retention 已经膨胀到 0.8452，说明 train threshold 不再代表同一预算。
- Robustness 上虽然比 C0 baseline 低 0.0689，但已经比 random same-budget p50 高 0.0093，且显著弱于 best single feature。换言之，stage-1 的“避开 fast-fail”信号在 OOS 不是没有，但当前多特征模型和固定阈值组合没有通过可支持 gate。

Stage-1 best single feature frontier 也说明了问题方向：robustness split 中最强的单特征是低波动方向。

| split | best single feature | orientation | selected n | selected fast-fail rate |
|---|---|---|---:|---:|
| train | `volatility_20d` | asc | 4,152 | 0.2876 |
| validation | `volatility_20d` | asc | 1,076 | 0.2091 |
| robustness | `volatility_60d` | asc | 2,330 | 0.1554 |
| all | `volatility_20d` | asc | 7,558 | 0.2363 |

Insight: stage-1 当前最稳的不是复杂交互，而是“低波动 / 靠近低位”的防守型过滤。多特征 logistic 在 train 中吃到了额外收益，但这个收益没有跨时间保持；robustness 上甚至明显输给单特征低波动 filter。

## Stage-1 Score Bucket

Stage-1 score 的排序能力是存在的。低 score bucket 的 fast-fail rate 明显低，高 score bucket 明显高。

| split | lowest-risk bucket target rate | highest-risk bucket target rate | spread |
|---|---:|---:|---:|
| train | 0.1367 | 0.7116 | 0.5750 |
| validation | 0.1601 | 0.5930 | 0.4329 |
| robustness | 0.1180 | 0.5612 | 0.4431 |

这给出一个重要判断：问题不是 rank signal 消失，而是绝对阈值不稳定。也就是说，当前模型可以排序 fast-fail 风险，但不能可靠地把 train 上的 50% keep boundary 迁移到 validation/robustness。

## Stage-2 Continuation Selector

Stage-2 primary model 是 `logistic_regression_l2`，使用 108 个 features，其中包括 t0 features 和通过 redundancy audit 的 realized path features。train_event_n=3,107，train positive rate=0.1516。

| split | evaluable n | continue n | retention | continuation rate | survivor base | random p50 | delta vs random p50 | best single feature | model minus best single | t0-only rate | realized-path incremental |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 3,107 | 1,554 | 0.5002 | 0.2272 | 0.1516 | 0.1811 | 0.0461 | 0.2027 | 0.0245 | 0.2181 | 0.0090 |
| validation | 1,292 | 487 | 0.3769 | 0.1109 | 0.0782 | 0.0714 | 0.0395 | 0.1006 | 0.0103 | 0.0994 | 0.0115 |
| robustness | 2,786 | 882 | 0.3166 | 0.1689 | 0.1228 | 0.1039 | 0.0650 | 0.1831 | -0.0141 | 0.1538 | 0.0151 |
| all | 7,185 | 2,923 | 0.4068 | 0.1902 | 0.1272 | 0.1385 | 0.0517 | 0.1756 | 0.0146 | 0.1781 | 0.0121 |

读数解释：

- Stage-2 在 train、validation、robustness 都高于 same-budget random p50；robustness delta 达 0.0650。
- Realized path features 有增量：robustness 的 realized-path incremental value 为 0.0151，说明 entry 到 day20 的路径信息对 continuation 选择有用。
- 但 robustness 上 model 仍低于 best single feature 0.0141。当前最强单特征是 `realized_path_volatility_0_20d` desc，selected continuation rate=0.1831，而模型只有 0.1689。
- Stage-2 不能单独支持 12A7：一方面 stage-1 已经不 supported，另一方面 stage-2 自己也有 threshold health fail 和 best-single-feature gate fail。

Stage-2 best single feature frontier：

| split | best single feature | orientation | selected n | selected continuation rate |
|---|---|---|---:|---:|
| train | `volatility_60d` | desc | 1,554 | 0.2027 |
| validation | `realized_early_window_ret_0_10d` | desc | 646 | 0.1006 |
| robustness | `realized_path_volatility_0_20d` | desc | 1,393 | 0.1831 |
| all | `realized_path_volatility_0_20d` | desc | 3,593 | 0.1756 |

Insight: stage-2 更像一个“survivor 之后的 realized path volatility / momentum continuation”问题。它确实比 random 好，但当前多特征模型没有稳定压过单个 realized volatility proxy，因此还不能证明需要复杂 continuation selector。

## Stage-2 Score Bucket

Stage-2 score bucket 同样有排序能力。这里 B1 是最高 continuation score bucket。

| split | highest-score bucket continuation rate | lowest-score bucket continuation rate | spread |
|---|---:|---:|---:|
| train | 0.2910 | 0.0434 | 0.2476 |
| validation | 0.1236 | 0.0463 | 0.0772 |
| robustness | 0.1738 | 0.0772 | 0.0966 |

这说明 stage-2 rank signal 比 stage-1 更稳定一些，但绝对 score 分布仍然漂移：train threshold 0.137815 在 train 上选 50.0%，在 robustness 只选 31.7%。如果后续继续推进，应优先研究 train-only calibration、board/year/family 分层阈值，或直接用更稳定的 single-feature / monotone rule 做 continuation 读数。

## Random Same-budget Baseline

Random baseline 使用 100 个 seeds，并按 split / board / calendar_month 的 same-budget deterministic retention 协议重算。Stage-1 random audit 有 25,600 行，Stage-2 random audit 有 23,784 行。

| stage | split | seed n | selected n median | random p05 | random p50 | random p95 |
|---|---:|---:|---:|---:|---:|---:|
| stage-1 | train | 100 | 4,151 | 0.3028 | 0.3137 | 0.3241 |
| stage-1 | validation | 100 | 1,818 | 0.2855 | 0.2984 | 0.3157 |
| stage-1 | robustness | 100 | 3,651 | 0.2188 | 0.2276 | 0.2373 |
| stage-2 | train | 100 | 1,429 | 0.1664 | 0.1811 | 0.1941 |
| stage-2 | validation | 100 | 478 | 0.0509 | 0.0714 | 0.0914 |
| stage-2 | robustness | 100 | 878 | 0.0864 | 0.1039 | 0.1216 |

注意 stage-2 random selected n 与 model continue n 不完全相同，因为 same-budget 是在 split / board / month cells 内按 C0 model budget replay 到 matched random 样本，cell rounding 会产生少量差异。这不是 gate failure 的主因；主因仍是 train threshold 外推后的 C0 actual budget drift。

## Board / Family / Year 稳定性

Robustness split 中，board 差异非常明显：

| board | event n | stage-1 base fast-fail | stage-1 keep n | stage-1 keep fast-fail | stage-2 evaluable n | stage-2 base continuation |
|---|---:|---:|---:|---:|---:|---:|
| main_board | 3,619 | 0.2644 | 3,084 | 0.2189 | 2,409 | 0.1100 |
| chinext | 1,040 | 0.4500 | 567 | 0.3351 | 377 | 0.2042 |

Family 维度同样有强异质性：

| family | event n | stage-1 base fast-fail | stage-1 keep n | stage-1 keep fast-fail | stage-2 evaluable n | stage-2 base continuation |
|---|---:|---:|---:|---:|---:|---:|
| B5 | 1,884 | 0.3025 | 1,482 | 0.2301 | 1,141 | 0.1262 |
| B1 | 686 | 0.3411 | 574 | 0.2892 | 408 | 0.1029 |
| B8 | 643 | 0.2908 | 457 | 0.2363 | 349 | 0.1232 |
| B2 | 571 | 0.2820 | 502 | 0.2271 | 388 | 0.1186 |
| B3 | 387 | 0.2067 | 374 | 0.1925 | 302 | 0.1523 |
| B6 | 344 | 0.3256 | 230 | 0.2391 | 175 | 0.0857 |
| B4 | 144 | 0.5625 | 32 | 0.2813 | 23 | 0.2609 |

Year 维度是最强的漂移来源之一：

| split | year | event n | stage-1 base fast-fail | stage-1 keep n | stage-1 keep fast-fail | stage-2 evaluable n | stage-2 base continuation |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 2018 | 344 | 0.7326 | 40 | 0.6750 | 13 | 0.0000 |
| train | 2019 | 2,189 | 0.3266 | 1,346 | 0.1590 | 1,132 | 0.1113 |
| train | 2020 | 3,083 | 0.4343 | 1,479 | 0.2874 | 1,054 | 0.2220 |
| train | 2021 | 2,687 | 0.4354 | 1,287 | 0.2945 | 908 | 0.1222 |
| validation | 2022 | 749 | 0.4139 | 559 | 0.3309 | 374 | 0.0668 |
| validation | 2023 | 1,402 | 0.3003 | 1,259 | 0.2709 | 918 | 0.0828 |
| robustness | 2024 | 2,039 | 0.3565 | 1,526 | 0.2955 | 1,075 | 0.0642 |
| robustness | 2025 | 2,620 | 0.2664 | 2,125 | 0.1948 | 1,711 | 0.1596 |

Insight: 当前失败不是单一模型参数问题，而是时段、board、family 的 base rate shift 共同导致阈值不可迁移。2024 与 2025 的 robustness continuation base rate 差异尤其大：2024 为 0.0642，2025 为 0.1596；如果不显式处理这种 year/regime shift，固定阈值很难稳定。

## Findings

1. 输入和 PIT discipline 没有阻塞项。17 个输入 artifact 均通过 read/schema gate，当前 failure 应归因于 label / feature / model / threshold transport，而不是上游产物缺失。

2. Stage-1 有 train 内有效性，但不是 OOS supported。Train keep fast-fail rate 0.2517 明显低于 C0 baseline 0.4186 和 random p50 0.3137；但 robustness 在 train-frozen threshold 下 retention 膨胀到 0.7836，且 fast-fail rate 0.2369 高于 random p50 0.2276。

3. Stage-1 最稳信号是低波动单特征。Robustness best single feature `volatility_60d` asc 的 selected fast-fail rate 只有 0.1554，显著好于多特征 logistic 的 0.2369。这提示下一轮不应盲目加复杂模型，而应先确认低波动 / 低位距离类规则能否成为更稳的 rejector backbone。

4. Stage-2 有 continuation rank signal 和 realized-path incremental value。Robustness continuation rate 0.1689 高于 survivor base 0.1228，也高于 random p50 0.1039；realized-path incremental value 为 0.0151。问题在于它仍低于 best single feature 0.1831，并且 threshold health 失败。

5. 两阶段链条当前不能支持 12A7。即便 stage-2 单独看起来有 uplift，12A7 要求 stage-1 rejector 先通过可执行 OOS gate；当前 stage-1 是 partial，且 threshold transport 失败，所以应停在 12A6d。

## Insight

AFML 视角下，这次结果更像“rank signal 存在，但 label/process 非平稳导致 train threshold 失效”，不是“没有 alpha proxy”。Score bucket 单调性说明排序模型确实捕捉了 fast-fail risk 和 continuation propensity；但固定预算阈值一旦从 train 迁移到 validation/robustness，实际 exposure 大幅变化，导致同一个模型在不同年份承担了不同的风险预算。

12A6d 的优先方向应是：

- 先做 stage-1 rejector revision，而不是直接推进 stage-2。Stage-1 是链条入口；入口预算漂移会污染 stage-2 denominator。
- 把 low-volatility / distance-to-low 这类稳定单特征作为基准 backbone，要求多特征模型必须在 robustness 上超过它，而不是只超过 random。
- 研究 train-only calibration 或分层阈值，但必须保持 OOS 不重选预算。候选分层维度应至少包括 board、calendar year/regime proxy、primary_family_id。
- Stage-2 可保留为 diagnostic continuation module。它显示 realized path features 有价值，但当前更像单特征 realized volatility selector，尚不足以证明复杂模型可支持。

当前最保守的结论是：12A6c 证明了 C0 risk_on 事件中存在 fast-fail/continuation 可排序形态，但没有证明 train-frozen 两阶段阈值可以稳定迁移。因此下一步不是 12A7 OOS validation，而是 12A6d 的 stage-1 feature/label/threshold revision。
