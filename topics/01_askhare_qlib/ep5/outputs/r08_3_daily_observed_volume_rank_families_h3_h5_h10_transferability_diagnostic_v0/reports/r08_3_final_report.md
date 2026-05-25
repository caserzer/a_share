# R08.3 Daily-Observed Volume/Rank Families H3/H5/H10 Transferability Diagnostic 最终报告

## 1. 结论摘要

`aggregate_r08_3_final_decision = r08_3_no_family_h3_transferability_support`

`authorized_strategy_requirement = false`

R08.3 的结论很直接：

```text
在 daily close-observed 口径下，
volume_surge_money_flow、volume_price_correlation、rank_ts_rank_structure
三个非 vwap family 都没有形成可支持 H3 transferability 的证据链。

R08.3 不授权任何 strategy requirement，
不构造组合，不选择 winning family，不形成 cross-family score，
也不允许用 H5/H10 diagnostic 结果 rescue H3。
```

三个 family 的最终状态如下：

| family | final decision | sample status | H3 validation spread | H3 robustness spread | validation positive inst | robustness positive inst | cleanliness failed |
|:--|:--|:--|--:|--:|--:|--:|:--|
| `volume_surge_money_flow` | `r08_3_family_blocked_scope_or_sample_insufficient` | `fail` | +5.55bp | +3.38bp | 55.42% | 74.57% | 是 |
| `volume_price_correlation` | `r08_3_no_daily_family_h3_transferability_support` | `pass` | -22.97bp | +5.38bp | 48.36% | 57.69% | 否 |
| `rank_ts_rank_structure` | `r08_3_no_daily_family_h3_transferability_support` | `pass` | +15.96bp | -2.03bp | 59.43% | 64.96% | 否 |

核心判断：

1. `volume_surge_money_flow` 的 H3 validation/robustness spread 都为正，但样本、fold stability、monotonicity、concentration 和年度稳定性不干净，因此只能记录为“正 spread 但 cleanliness failed”，不能支持 H3。
2. `volume_price_correlation` 在 validation H3 上明显为负，且 validation anchor、year、instrument breadth 都不支持，robustness 的小幅转正不能抵消 validation 失败。
3. `rank_ts_rank_structure` 在 validation H3 为正，但 robustness H3 转负；它还是 single-factor family，不能把 validation 的强读数解释成稳定 family 级 transferability。
4. R08.2 的 `vwap_deviation` daily H3 支持是一个特殊结果，不能外推到 volume/rank families。R08.3 的结果说明：daily observation 本身不是通用修复，family 结构仍然决定 transferability 是否成立。

## 2. 实验边界与数据安全

R08.3 是 diagnostic-only audit。primary horizon 固定为 H3；H5/H10 只作为 diagnostic labels，不参与 direction、bucket edge、factor retention 或 final decision。

| 项目 | 值 |
|:--|:--|
| source | `r06_cache/r05_daily_feature_panel` |
| candidate rows | 416,393 |
| instruments | 506 |
| signal dates | 2,064 |
| date range | 2017-07-04 ~ 2025-12-31 |
| primary families | `volume_surge_money_flow`; `volume_price_correlation`; `rank_ts_rank_structure` |
| primary horizon | H3 |
| diagnostic horizons | H5; H10 |
| shared daily panel across families | true |

Daily signal panel：

| split | event count | instruments | daily signal dates | date range | daily signal | weekly not primary |
|:--|--:|--:|--:|:--|:--|:--|
| train | 196,252 | 422 | 1,096 | 2017-07-04 ~ 2021-12-31 | true | true |
| validation | 109,722 | 323 | 483 | 2022-01-04 ~ 2023-12-29 | true | true |
| robustness | 110,419 | 342 | 485 | 2024-01-02 ~ 2025-12-31 | true | true |

Label completion 造成 split end 的自然截断，不是未来数据或缺失数据导致的异常：

| horizon | split | declared end | last label-complete signal date | actual end | evaluable years | actual signal dates |
|:--|:--|:--|:--|:--|--:|--:|
| H3 | train | 2021-12-31 | 2021-12-27 | 2021-12-27 | 5 | 1,092 |
| H3 | validation | 2023-12-31 | 2023-12-25 | 2023-12-25 | 2 | 479 |
| H3 | robustness | 2025-12-31 | 2025-12-25 | 2025-12-25 | 2 | 481 |
| H5 | train | 2021-12-31 | 2021-12-23 | 2021-12-23 | 5 | 1,090 |
| H5 | validation | 2023-12-31 | 2023-12-21 | 2023-12-21 | 2 | 477 |
| H5 | robustness | 2025-12-31 | 2025-12-23 | 2025-12-23 | 2 | 479 |
| H10 | train | 2021-12-31 | 2021-12-16 | 2021-12-16 | 5 | 1,085 |
| H10 | validation | 2023-12-31 | 2023-12-14 | 2023-12-14 | 2 | 472 |
| H10 | robustness | 2025-12-31 | 2025-12-16 | 2025-12-16 | 2 | 474 |

As-of 约束通过：self-relative labels 只使用 completed labels，lookback exit date 均不晚于 D-1；within-stock normalization 使用每只股票 D-1 之前的 reference distribution，不使用 future data，不做 cross-stock fill，并启用 mid-rank tie handling。

| horizon | split | complete labels | self-relative labels | industry-relative labels | completed-only | exit <= D-1 |
|:--|:--|--:|--:|--:|:--|:--|
| H3 | train | 192,308 | 178,884 | 84,856 | true | true |
| H3 | validation | 107,627 | 106,126 | 62,171 | true | true |
| H3 | robustness | 108,113 | 104,988 | 66,354 | true | true |
| H5 | train | 190,958 | 176,978 | 83,884 | true | true |
| H5 | validation | 106,823 | 105,204 | 61,547 | true | true |
| H5 | robustness | 107,245 | 104,054 | 65,660 | true | true |
| H10 | train | 188,147 | 172,837 | 82,005 | true | true |
| H10 | validation | 105,024 | 103,146 | 60,233 | true | true |
| H10 | robustness | 105,284 | 101,840 | 63,870 | true | true |

## 3. Family Scope 与 Bucket Edge

R08.3 不按结果选择 family。三个 pre-registered families 全部同步报告。

| family | in-scope factors | retained factor count | retained factor ids | dropped factor ids | comparability pass | caveat |
|:--|--:|:--|:--|:--|:--|:--|
| `volume_surge_money_flow` | 15 | 14/15 in folds 0,1,3,4; 15/15 in fold 2 | `alpha025`; `alpha069`; `alpha076`; `alpha080`; `alpha081`; `alpha086`; `alpha098`; `alpha100`; `alpha135`; `alpha145`; `alpha146`; `alpha168`; `alpha169`; `alpha181`; plus `alpha178` only in fold 2 | `alpha178` in folds 0,1,3,4 | true | no |
| `volume_price_correlation` | 3 | 3/3 in all folds | `alpha022`; `alpha031`; `alpha185` | none | true | no |
| `rank_ts_rank_structure` | 1 | 1/1 in all folds | `alpha038` | none | true | single-factor family caveat |

`volume_surge_money_flow` 的 factor scope 不是完全相同集合，主要来自 `alpha178` 的 direction sample insufficiency；但变化被 audit 解释，retained factor set comparability 仍为 pass。`rank_ts_rank_structure` 只有 `alpha038`，因此任何正向结果都必须按 single-factor caveat 解释，不能自动代表一个宽 family。

Bucket edge 使用 train-seen daily count-based extreme-tail 20/60/20，冻结在 validation/robustness read 之前。

| family | train-seen events range | tail count range | q20 range | q80 range | bottom share range | top share range | max q20 tie | max q80 tie | valid all | frozen all |
|:--|--:|--:|:--|:--|:--|:--|--:|--:|:--|:--|
| `volume_surge_money_flow` | 138,173 ~ 148,136 | 27,635 ~ 29,628 | 0.386054 ~ 0.392493 | 0.596581 ~ 0.604478 | 19.8781% ~ 20.2178% | 20.0669% ~ 20.5792% | 0.0008% | 0.0005% | 是 | 是 |
| `volume_price_correlation` | 138,097 ~ 148,054 | 27,620 ~ 29,611 | 0.310847 ~ 0.313492 | 0.690237 ~ 0.690476 | 19.8327% ~ 20.1925% | 19.1184% ~ 19.2292% | 0.0552% | 0.0436% | 是 | 是 |
| `rank_ts_rank_structure` | 138,554 ~ 148,505 | 27,711 ~ 29,701 | 0.384921 ~ 0.388889 | 0.827381 ~ 0.831349 | 19.0461% ~ 19.6148% | 18.8934% ~ 19.2890% | 0.3001% | 0.2742% | 是 | 是 |

## 4. H3 Primary Readout

H3 primary readout 使用 anchor offset 控制 daily overlapping label。H3 有 3 个 anchor offsets。

| family | split | mean spread | median spread | positive anchors | positive inst share | full-valid instruments | valid dates | monotonicity | max anchor abs contribution | full/anchor sign conflict |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| `volume_surge_money_flow` | train_oof_unseen | +4.30bp | -0.03bp | 1 | 76.47% | 204 | 760 | 0.9515 | 95.19% | 否 |
| `volume_surge_money_flow` | validation_oof_unseen | +5.55bp | +6.87bp | 2 | 55.42% | 240 | 455 | 0.6121 | 55.79% | 否 |
| `volume_surge_money_flow` | robustness_oof_unseen | +3.38bp | +2.78bp | 3 | 74.57% | 232 | 395 | 0.9515 | 55.35% | 否 |
| `volume_price_correlation` | train_oof_unseen | -11.80bp | -13.48bp | 0 | 54.90% | 204 | 809 | 0.3333 | 52.95% | 否 |
| `volume_price_correlation` | validation_oof_unseen | -22.97bp | -22.52bp | 0 | 48.36% | 244 | 452 | -0.3576 | 44.76% | 否 |
| `volume_price_correlation` | robustness_oof_unseen | +5.38bp | +1.89bp | 2 | 57.69% | 234 | 456 | 0.4061 | 85.20% | 否 |
| `rank_ts_rank_structure` | train_oof_unseen | +3.23bp | +1.58bp | 2 | 61.27% | 204 | 861 | 0.5273 | 61.31% | 否 |
| `rank_ts_rank_structure` | validation_oof_unseen | +15.96bp | +14.02bp | 3 | 59.43% | 244 | 458 | 0.6000 | 44.34% | 否 |
| `rank_ts_rank_structure` | robustness_oof_unseen | -2.03bp | -7.32bp | 1 | 64.96% | 234 | 474 | 0.6000 | 40.47% | 否 |

Full daily 与 anchor-controlled readout 没有 sign conflict，但这不等于 H3 support。R08.3 的 support 需要同时满足 time transfer、instrument transfer、fold stability、anchor stability、monotonicity、concentration、robustness non-deterioration 和 sample status。

Gate replay：

| family | sample | time | instrument | fold | anchor | monotonicity | concentration | robustness non-deterioration | validation folds | robustness folds | validation dates | robustness dates | positive years val/rob |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|--:|--:|--:|--:|:--|
| `volume_surge_money_flow` | fail | 否 | 是 | 否 | 是 | 否 | 否 | 是 | 3 | 3 | 455 | 395 | 1/1 |
| `volume_price_correlation` | pass | 否 | 否 | 否 | 否 | 否 | 否 | 是 | 5 | 5 | 452 | 456 | 0/1 |
| `rank_ts_rank_structure` | pass | 否 | 是 | 否 | 否 | 否 | 是 | 是 | 5 | 5 | 458 | 474 | 2/1 |

Fold dispersion：

| family | split | evaluable folds | positive folds | median fold spread | min fold spread | fold positive inst median | fold mono median | max fold top1 | max fold top5 |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| `volume_surge_money_flow` | train_oof_unseen | 5 | 1 | -15.58bp | -26.79bp | 73.17% | 0.8303 | 10.32% | 35.41% |
| `volume_surge_money_flow` | validation_oof_unseen | 3 | 4 | +32.34bp | -10.22bp | 56.82% | 0.1879 | 26.50% | 43.68% |
| `volume_surge_money_flow` | robustness_oof_unseen | 3 | 2 | -1.64bp | -22.48bp | 70.83% | 0.7333 | 15.40% | 42.15% |
| `volume_price_correlation` | train_oof_unseen | 5 | 0 | -2.45bp | -29.37bp | 55.10% | 0.2000 | 13.53% | 37.71% |
| `volume_price_correlation` | validation_oof_unseen | 5 | 1 | -4.53bp | -49.48bp | 48.08% | -0.5515 | 10.23% | 30.88% |
| `volume_price_correlation` | robustness_oof_unseen | 5 | 1 | -9.02bp | -30.43bp | 54.17% | 0.2848 | 17.01% | 39.92% |
| `rank_ts_rank_structure` | train_oof_unseen | 5 | 4 | +12.92bp | -2.55bp | 63.41% | 0.4061 | 10.60% | 38.91% |
| `rank_ts_rank_structure` | validation_oof_unseen | 5 | 4 | +20.18bp | -6.51bp | 57.69% | 0.4545 | 10.98% | 31.17% |
| `rank_ts_rank_structure` | robustness_oof_unseen | 5 | 2 | -1.60bp | -18.44bp | 66.07% | 0.6121 | 9.49% | 36.60% |

注意 `volume_surge_money_flow` validation/robustness 的 `positive folds` 看似高于 evaluable folds，是因为 fold dispersion summary 统计了可形成 fold spread 的 fold-level positive count，而 sample gate 另按 full-valid instruments、anchor min valid dates 等条件判定 evaluable folds。最终门禁使用 gate replay 中的 sample status，不用该列绕开 sample fail。

Fold sample 门槛：

| family | horizon | split | evaluable folds | full-valid instruments range | valid signal dates range | min anchor dates | invalid folds |
|:--|:--|:--|--:|:--|:--|--:|:--|
| `volume_surge_money_flow` | H3 | validation_oof_unseen | 3/5 | 44 ~ 53 | 110 ~ 156 | 34 | 1,4 |
| `volume_surge_money_flow` | H3 | robustness_oof_unseen | 3/5 | 38 ~ 55 | 107 ~ 201 | 34 | 0,4 |
| `volume_price_correlation` | H3 | validation_oof_unseen | 5/5 | 44 ~ 54 | 161 ~ 206 | 48 | none |
| `volume_price_correlation` | H3 | robustness_oof_unseen | 5/5 | 39 ~ 56 | 181 ~ 278 | 55 | none |
| `rank_ts_rank_structure` | H3 | validation_oof_unseen | 5/5 | 44 ~ 54 | 168 ~ 209 | 49 | none |
| `rank_ts_rank_structure` | H3 | robustness_oof_unseen | 5/5 | 39 ~ 56 | 206 ~ 319 | 64 | none |

H3 年度读数：

| family | split | year | mean spread | positive | valid dates |
|:--|:--|--:|--:|:--|--:|
| `volume_surge_money_flow` | train_oof_unseen | 2018 | +47.31bp | 是 | 186 |
| `volume_surge_money_flow` | train_oof_unseen | 2019 | -0.98bp | 否 | 129 |
| `volume_surge_money_flow` | train_oof_unseen | 2020 | +9.19bp | 是 | 207 |
| `volume_surge_money_flow` | train_oof_unseen | 2021 | -30.82bp | 否 | 238 |
| `volume_surge_money_flow` | validation_oof_unseen | 2022 | +33.51bp | 是 | 225 |
| `volume_surge_money_flow` | validation_oof_unseen | 2023 | -21.85bp | 否 | 230 |
| `volume_surge_money_flow` | robustness_oof_unseen | 2024 | +17.11bp | 是 | 163 |
| `volume_surge_money_flow` | robustness_oof_unseen | 2025 | -6.25bp | 否 | 232 |
| `volume_price_correlation` | train_oof_unseen | 2018 | +1.87bp | 是 | 175 |
| `volume_price_correlation` | train_oof_unseen | 2019 | -9.79bp | 否 | 184 |
| `volume_price_correlation` | train_oof_unseen | 2020 | -30.64bp | 否 | 212 |
| `volume_price_correlation` | train_oof_unseen | 2021 | -6.41bp | 否 | 238 |
| `volume_price_correlation` | validation_oof_unseen | 2022 | -16.60bp | 否 | 221 |
| `volume_price_correlation` | validation_oof_unseen | 2023 | -29.13bp | 否 | 231 |
| `volume_price_correlation` | robustness_oof_unseen | 2024 | -0.33bp | 否 | 225 |
| `volume_price_correlation` | robustness_oof_unseen | 2025 | +11.02bp | 是 | 231 |
| `rank_ts_rank_structure` | train_oof_unseen | 2018 | +23.29bp | 是 | 183 |
| `rank_ts_rank_structure` | train_oof_unseen | 2019 | -10.43bp | 否 | 210 |
| `rank_ts_rank_structure` | train_oof_unseen | 2020 | -2.53bp | 否 | 230 |
| `rank_ts_rank_structure` | train_oof_unseen | 2021 | +4.84bp | 是 | 238 |
| `rank_ts_rank_structure` | validation_oof_unseen | 2022 | +20.23bp | 是 | 232 |
| `rank_ts_rank_structure` | validation_oof_unseen | 2023 | +11.69bp | 是 | 226 |
| `rank_ts_rank_structure` | robustness_oof_unseen | 2024 | +7.97bp | 是 | 236 |
| `rank_ts_rank_structure` | robustness_oof_unseen | 2025 | -11.92bp | 否 | 238 |

年度数据解释了 gate replay 为什么严格：`volume_surge_money_flow` 和 `volume_price_correlation` 都只有一个 robustness 正年份，`volume_surge_money_flow` validation 也只有一个正年份；`rank_ts_rank_structure` 虽然 validation 两年都为正，但 robustness 在 2025 转负，H3 support 断在 robustness。

## 5. Concentration Readout

Aggregate anchor-controlled concentration：

| family | split | top1 instrument | top1 events | top1 contribution | top5 contribution | top1 industry | top1 industry contribution | max anchor abs contribution |
|:--|:--|:--|--:|--:|--:|:--|--:|--:|
| `volume_surge_money_flow` | train_oof_unseen | SH601698 | 153 | 3.42% | 11.71% | sw_801080 | 11.58% | 95.19% |
| `volume_surge_money_flow` | validation_oof_unseen | SH601127 | 172 | 3.81% | 13.79% | sw_801080 | 12.62% | 55.79% |
| `volume_surge_money_flow` | robustness_oof_unseen | SZ000792 | 232 | 4.12% | 16.78% | sw_801080 | 12.22% | 55.35% |
| `volume_price_correlation` | train_oof_unseen | SH600309 | 321 | 2.55% | 10.05% | sw_801150 | 9.94% | 52.95% |
| `volume_price_correlation` | validation_oof_unseen | SH600196 | 160 | 3.09% | 10.91% | sw_801150 | 9.16% | 44.76% |
| `volume_price_correlation` | robustness_oof_unseen | SH605117 | 111 | 6.94% | 17.78% | sw_801730 | 12.90% | 85.20% |
| `rank_ts_rank_structure` | train_oof_unseen | SH600547 | 326 | 2.25% | 9.92% | sw_801150 | 9.30% | 61.31% |
| `rank_ts_rank_structure` | validation_oof_unseen | SH603392 | 149 | 3.15% | 10.67% | sw_801730 | 10.15% | 44.34% |
| `rank_ts_rank_structure` | robustness_oof_unseen | SH600085 | 132 | 2.85% | 11.13% | sw_801080 | 11.23% | 40.47% |

Worst fold concentration：

| family | split | worst fold | top1 instrument | top1 contribution | top5 contribution | top1 industry | top1 industry contribution |
|:--|:--|--:|:--|--:|--:|:--|--:|
| `volume_surge_money_flow` | validation_oof_unseen | 3 | SH601127 | 26.50% | 43.68% | sw_801880 | 26.84% |
| `volume_surge_money_flow` | robustness_oof_unseen | 3 | SH601336 | 15.40% | 42.15% | sw_801790 | 19.86% |
| `volume_price_correlation` | validation_oof_unseen | 4 | SZ002460 | 10.23% | 28.83% | sw_801050 | 11.83% |
| `volume_price_correlation` | robustness_oof_unseen | 0 | SH605117 | 17.01% | 39.92% | sw_801730 | 22.83% |
| `rank_ts_rank_structure` | validation_oof_unseen | 0 | SH600188 | 10.98% | 31.17% | sw_801730 | 18.92% |
| `rank_ts_rank_structure` | robustness_oof_unseen | 0 | SH600895 | 9.49% | 36.14% | sw_801730 | 19.81% |

Concentration 是 `volume_surge_money_flow` 和 `volume_price_correlation` 的重要 blocker。`volume_surge_money_flow` 的 validation worst fold top1 达到 26.50%，top5 达到 43.68%；`volume_price_correlation` robustness aggregate max anchor abs contribution 达到 85.20%。这类结构意味着 spread 不能被当作稳定横截面关系。

## 6. H5/H10 Diagnostic

H5/H10 只解释 horizon shape，不参与 H3 final support。

| family | horizon | validation mean | validation median | robustness mean | robustness median | validation positive inst | robustness positive inst | val mono | rob mono | val anchors | rob anchors | diagnostic positive |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| `volume_surge_money_flow` | H5 | +13.21bp | +23.20bp | +11.32bp | +7.17bp | 58.75% | 70.43% | 0.5030 | 0.6970 | 4 | 4 | 是 |
| `volume_surge_money_flow` | H10 | +29.48bp | +26.12bp | +12.66bp | +10.69bp | 60.34% | 65.50% | 0.4788 | 0.5636 | 8 | 8 | 否 |
| `volume_price_correlation` | H5 | -42.08bp | -53.49bp | +3.19bp | +1.83bp | 45.23% | 62.07% | -0.5879 | 0.8667 | 0 | 3 | 否 |
| `volume_price_correlation` | H10 | -51.63bp | -45.83bp | -22.60bp | -10.52bp | 48.95% | 60.43% | -0.6242 | 0.7091 | 1 | 3 | 否 |
| `rank_ts_rank_structure` | H5 | +21.74bp | +20.55bp | -2.64bp | -3.36bp | 51.04% | 47.41% | 0.3939 | 0.2242 | 5 | 2 | 否 |
| `rank_ts_rank_structure` | H10 | +42.98bp | +44.70bp | +23.44bp | +18.24bp | 57.74% | 44.35% | 0.6727 | 0.1636 | 8 | 6 | 否 |

Horizon shape：

| family | split | H3 | H5 | H10 | H5-H3 | H10-H3 | sign pattern |
|:--|:--|--:|--:|--:|--:|--:|:--|
| `volume_surge_money_flow` | validation_oof_unseen | +5.55bp | +13.21bp | +29.48bp | +7.66bp | +23.93bp | `+/+/+` |
| `volume_surge_money_flow` | robustness_oof_unseen | +3.38bp | +11.32bp | +12.66bp | +7.95bp | +9.29bp | `+/+/+` |
| `volume_price_correlation` | validation_oof_unseen | -22.97bp | -42.08bp | -51.63bp | -19.11bp | -28.66bp | `-/-/-` |
| `volume_price_correlation` | robustness_oof_unseen | +5.38bp | +3.19bp | -22.60bp | -2.19bp | -27.97bp | `+/+/-` |
| `rank_ts_rank_structure` | validation_oof_unseen | +15.96bp | +21.74bp | +42.98bp | +5.78bp | +27.02bp | `+/+/+` |
| `rank_ts_rank_structure` | robustness_oof_unseen | -2.03bp | -2.64bp | +23.44bp | -0.62bp | +25.47bp | `-/-/+` |

Diagnostic insight：

1. `volume_surge_money_flow` 的 H5 是唯一 diagnostic-positive horizon，H10 虽然 spread 更大但 diagnostic gate 没有过。这个结果只说明中短 horizon 可能有后续诊断价值，不能改变 H3 final decision。
2. `volume_price_correlation` 的 horizon shape 最差。validation 从 H3 到 H10 全部为负，且越长越负。
3. `rank_ts_rank_structure` 的 H10 spread 看起来强，但 robustness positive instrument share 只有 44.35%，而且 primary H3 robustness 已经转负。它更像 horizon-dependent fragility，不是 H3 transferability。

## 7. Family-Level Findings

### 7.1 `volume_surge_money_flow`

表面上它是最容易误判的 family：H3 validation mean +5.55bp，robustness mean +3.38bp，H5 validation/robustness 也都是正数。但它没有通过 H3 support，原因不是单一指标，而是多重 cleanliness 问题叠加：

1. H3 sample status 是 `fail`，validation 和 robustness 都只有 3/5 folds evaluable。
2. validation 只有 2022 为正，2023 为 -21.85bp；robustness 只有 2024 为正，2025 为 -6.25bp。
3. fold stability 失败。validation fold median 虽为 +32.34bp，但 min fold 为 -10.22bp；robustness median fold spread 为 -1.64bp。
4. monotonicity 失败。validation fold monotonicity median 只有 0.1879。
5. concentration 失败。validation worst fold top1 instrument contribution 为 26.50%，top5 为 43.68%。

我的判断：`volume_surge_money_flow` 可能存在一段短 horizon 的交易反应，但当前 H3 证据链不够干净。后续如果要继续，只能作为 H5 diagnostic decomposition，而不是生成 H3 策略需求。

### 7.2 `volume_price_correlation`

这是三个 family 中方向最明确的失败。H3 validation mean 为 -22.97bp，median 为 -22.52bp，validation positive anchors 为 0，validation positive years 为 0，positive instrument share 只有 48.36%。

Robustness H3 mean +5.38bp 不能救这个 family，因为：

1. validation 是正式前推窗口，且已经系统性为负。
2. H5/H10 validation 也分别为 -42.08bp 和 -51.63bp，horizon 越长越差。
3. instrument transfer、anchor stability、fold stability、monotonicity、concentration 全部失败。
4. robustness 的正数伴随 85.20% max anchor abs contribution，稳定性不足。

我的判断：在当前 daily close-observed self-relative net return 口径下，`volume_price_correlation` 不应再作为 transferability 候选推进。

### 7.3 `rank_ts_rank_structure`

`rank_ts_rank_structure` 是最有解释价值但不能授权的 family。H3 validation mean +15.96bp，median +14.02bp，2022/2023 都为正；但 robustness mean -2.03bp，median -7.32bp，2025 年为 -11.92bp。

关键 blocker：

1. H3 time transfer gate 失败。validation 为正，robustness 转负。
2. anchor stability 失败。robustness 只有 1/3 anchors positive。
3. fold stability 失败。robustness positive folds 只有 2/5，min fold -18.44bp。
4. 它是 single-factor family，只来自 `alpha038`，即使 validation 正，也不能解释为宽 rank/ts-rank 结构稳定成立。
5. H10 robustness mean +23.44bp 但 robustness positive instrument share 只有 44.35%，说明长 horizon 形状不够广泛。

我的判断：`rank_ts_rank_structure` 更像一个 regime-sensitive single-factor diagnostic。它提示 2022-2023 的 rank/ts-rank 状态可能有用，但跨到 2024-2025 后不能保持 H3。

## 8. 与 R08.2 的关系

R08.2 的 `vwap_deviation` daily H3 是 diagnostic-supported，但仍不授权策略；R08.3 则明确没有任何 family 支持 H3。两者放在一起看，结论不是“daily signal 一定有效”，而是：

```text
daily observation 可以改善样本密度和 overlap 控制，
但只有当 family 本身的状态关系足够稳定时，
daily 化才会把信号变得更可评价、更干净。

vwap_deviation 通过了这个检验；
volume_surge_money_flow、volume_price_correlation、rank_ts_rank_structure 没有。
```

这对后续研究方向很重要。R08.2 不能被泛化成“所有 daily-observed family 都值得策略化”。当前 evidence 更支持把 `vwap_deviation` 视为特殊结构继续做 confirmatory work，而不是扩展到 volume/rank family 组合。

## 9. 研究建议

1. 不要基于 R08.3 写 strategy requirement。aggregate final decision 已经明确禁止。
2. 不要选择 R08.3 family winner。所有 family 都是 co-primary diagnostic，报告中没有 cross-family score。
3. 若要继续 H3 主线，应优先围绕 R08.2 `vwap_deviation` 做确认性约束，而不是把 R08.3 的非 vwap family 纳入策略候选。
4. 若要继续探索 `volume_surge_money_flow`，合理问题是 H5 diagnostic decomposition，而不是 H3 transferability。它的 H5 读数为 validation +13.21bp、robustness +11.32bp，但必须重新定义为 diagnostic follow-up，不能从 R08.3 直接升级。
5. `rank_ts_rank_structure` 可以作为 regime-sensitive explanatory artifact 保存，但不适合进入策略授权路径。

## 10. Contract Replay

Validation manifest 显示：

| item | value |
|:--|:--|
| validation_status | `passed` |
| gate_count | 50 |
| passed_gate_count | 50 |
| failed_gate_count | 0 |
| aggregate_final_decision | `r08_3_no_family_h3_transferability_support` |

必要问题回答：

1. R08.3 是否保持 diagnostic-only？是。
2. 是否同步验证三个 pre-registered families？是。
3. 是否没有使用 `vwap_deviation` 作为 primary family？是。
4. 是否固定 signal frequency 为 daily close-observed？是。
5. 是否只把 H3 作为 primary horizon？是。
6. H5/H10 是否只作为 diagnostic labels？是。
7. 是否使用 deterministic 5-fold instrument OOF unseen？是。
8. direction 是否只来自 train years + seen folds + H3？是。
9. H5/H10 是否没有参与 direction、bucket edge、factor retention 或 final decision？是。
10. 是否没有 family winner selection 或 cross-family score？是。
11. 是否允许写 strategy requirement？否。
