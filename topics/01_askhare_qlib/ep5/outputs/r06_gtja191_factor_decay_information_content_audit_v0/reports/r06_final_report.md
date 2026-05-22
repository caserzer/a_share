# R06 GTJA191 因子衰减与信息含量审计报告

## 1. 结论摘要

`final_decision = r06_decay_information_exists_but_not_tradeable`。

R06 没有构造 top20% 交易策略，也没有输出 long-only alpha pass。它只审计 GTJA191 / Alpha191 在 H1/H3/H5/H10/H20 上是否仍有可复现、非纯风格、非 persistent-name 驱动的短周期横截面信息。

核心结论是：

- Alpha191 不是完全没有信息。validation 中 H1/H3 的 family-level RankIC 和 top-bottom spread 仍有弱正读数，尤其是 `volume_price_correlation`、`volume_surge_money_flow`、`vwap_deviation` 的 H3。
- 这些信息不能进入交易化。没有任何 train-selected family 同时通过 information、monotonicity、persistent-name clean、style clean 和 cost gates。
- 成本不是主要失败点。H3 三个弱正 family 的 net spread 仍为正，`cost_survival_ratio = 0.989`，但它们失败在 monotonicity、persistent-name 和 style exposure。
- R05 的失败不是因为 H10 样本不可评价，也不是因为 top20% 分位设置单点偶然。R06 显示信息主要在 H1/H3 较短 horizon，H10/H20 衰减明显，而且弱正均值会被 persistent-name 和 style 暴露污染。

因此，R06 只能支持一个诊断性判断：

```text
Alpha191 在当前 EP5 PIT universe 下仍有局部短周期信息痕迹，
但没有 clean residual family 足以授权 R07 strategy requirement。
```

## 2. 数据完整性与执行边界

R06 使用 R05 产出的本地 PIT universe、split、next-open executable return label、110bps round-trip cost、matched comparator discipline 和 no-online-data 边界。报告只读取已经生成的 R06 artifacts。

| item | value |
|:--|--:|
| final validator status | passed |
| validator checks passed | 13 / 13 |
| final replay selected rule | rule_07 |
| final decision | r06_decay_information_exists_but_not_tradeable |
| included factor count | 125 |
| evaluable family count | 7 |
| partial family coverage warning | False |
| all horizon label sample gate | True |

Horizon label purge 后仍有足够样本，样本不足不是本次结论的原因。

| split | H1 usable dates | H3 usable dates | H5 usable dates | H10 usable dates | H20 usable dates |
|:--|--:|--:|--:|--:|--:|
| train | 226 | 226 | 225 | 224 | 222 |
| validation | 97 | 96 | 96 | 96 | 94 |
| robustness | 102 | 102 | 101 | 100 | 98 |

## 3. 因子库与 family map

GTJA191 source factors 共 191 个，其中 125 个 included，66 个 excluded。excluded 的主因是 V0 中公式实现不可用或过慢。

| factor status | count |
|:--|--:|
| included | 125 |
| excluded_formula_implementation_failed | 65 |
| excluded_insufficient_cross_section_coverage | 1 |

Family map 覆盖 8 个 primary families。注意 source factor count 与 included factor count 不同，后续 RankIC / spread 只在 included 且可评价因子上计算。

| family | source factor count | included factor count |
|:--|--:|--:|
| composite_price_volume | 105 | 62 |
| volume_surge_money_flow | 25 | 15 |
| other_gtja191 | 23 | 17 |
| close_location | 19 | 18 |
| vwap_deviation | 10 | 6 |
| range_volatility | 4 | 3 |
| volume_price_correlation | 4 | 3 |
| rank_ts_rank_structure | 1 | 1 |

这里已经能看到一个结构性问题：`composite_price_volume` 占 included 因子的 49.6%，而 `rank_ts_rank_structure` 只有 1 个因子。R06 因此采用 family-level 审计，而不是继续让因子数量多的族在 composite 中重复投票。

## 4. Horizon Decay

Family-level oriented RankIC 的衰减曲线显示：train 内各 horizon 都是正的，但 validation 与 robustness 主要集中在 H1/H3/H5，H10 开始接近零，H20 转负。

| split | H1 mean RankIC | H3 mean RankIC | H5 mean RankIC | H10 mean RankIC | H20 mean RankIC |
|:--|--:|--:|--:|--:|--:|
| train | 0.00842 | 0.01622 | 0.01604 | 0.01231 | 0.01302 |
| validation | 0.01057 | 0.00580 | 0.00308 | -0.00046 | -0.00691 |
| robustness | 0.00829 | 0.00637 | 0.01021 | 0.00373 | -0.00319 |

Spread 读数也支持同一结论。validation 的 mean top-decile minus bottom-decile matched-delta spread 在 H1/H3 约为 +0.14%，H5 只剩 +0.02%，H10/H20 已经转负。

| split | H1 mean spread | H3 mean spread | H5 mean spread | H10 mean spread | H20 mean spread |
|:--|--:|--:|--:|--:|--:|
| train | 0.110% | 0.246% | 0.174% | 0.277% | 0.608% |
| validation | 0.138% | 0.141% | 0.020% | -0.087% | -0.382% |
| robustness | 0.125% | 0.063% | 0.086% | -0.025% | -0.031% |

这解释了 R05 的 H10 困境：R05 固定 H10 训练和评价 composite，但 R06 的 family-level evidence 显示 H10 已经不是信息最集中的位置。

## 5. Train-only horizon selection

R06 的 family primary horizon 完全由 train split 冻结，不使用 validation / robustness 结果。每个 family 进入候选前还要求同号年份与单年贡献约束。

| family | selected horizon | train mean oriented RankIC | same-sign years | single-year IC contribution | positive train dates | quality |
|:--|:--|--:|--:|--:|--:|--:|
| close_location | H20 | 0.02057 | 4 / 5 | 39.41% | 64.41% | 0.00972 |
| composite_price_volume | H20 | 0.01890 | 5 / 5 | 27.76% | 72.07% | 0.01310 |
| other_gtja191 | H20 | 0.02033 | 4 / 5 | 30.33% | 64.86% | 0.00978 |
| range_volatility | H1 | 0.00833 | 4 / 5 | 41.89% | 54.42% | 0.00319 |
| rank_ts_rank_structure | H3 | 0.03459 | 5 / 5 | 37.01% | 60.62% | 0.01835 |
| volume_price_correlation | H3 | 0.01816 | 5 / 5 | 54.67% | 55.75% | 0.00905 |
| volume_surge_money_flow | H3 | 0.01625 | 5 / 5 | 26.96% | 66.37% | 0.01036 |
| vwap_deviation | H3 | 0.01351 | 5 / 5 | 26.21% | 60.62% | 0.00770 |

Train 选择本身没有使用未来信息，但它暴露了一个重要风险：多个 family 在 train 中把 H20 选为最强 horizon，可是 validation/robustness 中 H20 明显衰减或反转。也就是说，train-only discipline 避免了验证集调参，但不能保证 train 中最强 horizon 可迁移。

## 6. Train-selected Family 回放

下面只看 train-selected horizon，而不是事后挑 validation 最好 horizon。结论很直接：H20 族在 validation 大面积失效；H3 量价族保留弱正信息，但不干净。

| family | horizon | val RankIC | val spread | val positive dates | robust RankIC | robust spread | main readout |
|:--|:--|--:|--:|--:|--:|--:|:--|
| close_location | H20 | -0.02814 | -1.124% | 38.30% | -0.01325 | -0.143% | train H20 完全反转 |
| composite_price_volume | H20 | 0.00003 | -0.208% | 44.68% | 0.00223 | -0.108% | RankIC 近零，spread 转负 |
| other_gtja191 | H20 | -0.01758 | -0.925% | 39.36% | -0.01230 | -0.189% | validation/robustness 均负 |
| range_volatility | H1 | -0.00677 | -0.006% | 50.00% | -0.00287 | -0.086% | H1 弱且不稳定 |
| rank_ts_rank_structure | H3 | 0.02162 | n/a | n/a | 0.00977 | n/a | 单因子 family，不满足 family spread 可评价 |
| volume_price_correlation | H3 | 0.01331 | 0.333% | 61.22% | 0.01773 | 0.170% | 有弱信息，但不 clean |
| volume_surge_money_flow | H3 | 0.00900 | 0.238% | 57.14% | 0.00815 | 0.101% | 有弱信息，但不 clean |
| vwap_deviation | H3 | 0.00375 | 0.225% | 59.18% | 0.00508 | 0.071% | 有弱信息，但不 clean |

最有价值的三条线索都集中在 H3：

| family | H3 validation RankIC | H3 validation matched-delta spread | H3 validation net-return spread | H3 robustness matched-delta spread | cost survival |
|:--|--:|--:|--:|--:|--:|
| volume_price_correlation | 0.01331 | 0.333% | 0.331% | 0.170% | 98.90% |
| volume_surge_money_flow | 0.00900 | 0.238% | 0.256% | 0.101% | 98.90% |
| vwap_deviation | 0.00375 | 0.225% | 0.217% | 0.071% | 98.90% |

这些不是强到足以交易的结果，但足以说明 Alpha191 中仍有局部短周期信息。问题是这类信息不能被解释成 clean residual edge。

## 7. Validation Spread Readout

如果只看 validation 的 top-bottom matched-delta spread，排名靠前的读数确实来自短 horizon 的量价结构。

| family | horizon | matched-delta spread | net-return spread | monotonicity | positive date share |
|:--|:--|--:|--:|--:|--:|
| volume_price_correlation | H3 | 0.33% | 0.33% | 0.031 | 61.22% |
| volume_surge_money_flow | H5 | 0.27% | 0.27% | 0.017 | 54.64% |
| volume_price_correlation | H1 | 0.25% | 0.25% | 0.072 | 61.22% |
| vwap_deviation | H10 | 0.24% | 0.25% | 0.015 | 56.25% |
| volume_surge_money_flow | H3 | 0.24% | 0.26% | 0.086 | 57.14% |
| vwap_deviation | H1 | 0.23% | 0.22% | 0.080 | 58.16% |
| vwap_deviation | H3 | 0.22% | 0.22% | 0.058 | 59.18% |
| volume_price_correlation | H20 | 0.21% | 0.22% | 0.039 | 55.32% |
| volume_surge_money_flow | H1 | 0.19% | 0.20% | 0.065 | 61.22% |
| volume_price_correlation | H10 | 0.16% | 0.17% | 0.048 | 48.96% |

但这些 readout 不能被当成 strategy evidence。第一，表中不少 horizon 不是 train-selected primary horizon；第二，monotonicity 分数远低于 0.60；第三，style 与 persistent-name clean gates 没有通过。

## 8. Monotonicity Gate

R06 要求 decile monotonicity，而不是只看 top-bottom spread。所有 train-selected family 的 `family_monotonicity_positive` 都是 false。

| family | horizon | train monotonicity | validation monotonicity | robustness monotonicity |
|:--|:--|--:|--:|--:|
| close_location | H20 | 0.152 | -0.149 | 0.023 |
| composite_price_volume | H20 | 0.165 | -0.052 | 0.057 |
| other_gtja191 | H20 | 0.145 | -0.172 | -0.042 |
| range_volatility | H1 | 0.031 | 0.008 | -0.018 |
| volume_price_correlation | H3 | 0.061 | 0.031 | 0.055 |
| volume_surge_money_flow | H3 | 0.109 | 0.086 | 0.018 |
| vwap_deviation | H3 | 0.065 | 0.058 | 0.040 |

这里的含义是：即使 top decile 比 bottom decile 有小幅 spread，排序并没有形成从低分位到高分位的稳定单调结构。这对后续策略非常关键，因为没有单调性时，top/bottom spread 很容易来自少数分位、少数日期或少数股票。

## 9. Persistent-name Audit

R05 的核心失败之一是 selected-week 集中度过高。R06 继续验证这个问题：多个 family 的 top bucket 长期由少数股票占据。

Validation top-decile：

| family | horizon | top1 signal-week share | top5 union share | persistent ratio | rank turnover | new name share | clean |
|:--|:--|--:|--:|--:|--:|--:|:--|
| close_location | H20 | 53.19% | 94.68% | 32.85% | 67.15% | 51.39% | False |
| composite_price_volume | H20 | 51.06% | 96.81% | 27.41% | 72.59% | 57.59% | False |
| other_gtja191 | H20 | 54.26% | 95.74% | 35.13% | 64.87% | 48.79% | False |
| range_volatility | H1 | 25.51% | 74.49% | 13.87% | 86.13% | 76.14% | True |
| volume_price_correlation | H3 | 27.55% | 64.29% | 7.90% | 92.10% | 85.60% | True |
| volume_surge_money_flow | H3 | 37.76% | 87.76% | 27.70% | 72.30% | 57.33% | False |
| vwap_deviation | H3 | 38.78% | 82.65% | 18.91% | 81.09% | 68.71% | False |

Validation top-quintile：

| family | horizon | top1 signal-week share | top5 union share | persistent ratio | rank turnover | new name share | clean |
|:--|:--|--:|--:|--:|--:|--:|:--|
| close_location | H20 | 77.66% | 98.94% | 42.55% | 57.45% | 40.69% | False |
| composite_price_volume | H20 | 76.60% | 100.00% | 36.25% | 63.75% | 47.19% | False |
| other_gtja191 | H20 | 77.66% | 100.00% | 46.51% | 53.49% | 36.70% | False |
| range_volatility | H1 | 39.80% | 86.73% | 23.46% | 76.54% | 62.32% | False |
| volume_price_correlation | H3 | 38.78% | 76.53% | 15.13% | 84.87% | 73.98% | False |
| volume_surge_money_flow | H3 | 51.02% | 94.90% | 34.41% | 65.59% | 49.13% | False |
| vwap_deviation | H3 | 62.24% | 96.94% | 29.53% | 70.47% | 54.78% | False |

重要细节是：`volume_price_correlation` 的 top-decile persistence 看起来干净，但 top-quintile 已经失败，`top5 union share = 76.53%`，略高于 75% 门槛。R06 的 family-level persistent gate 要求 top-decile 和 top-quintile 同时干净，因此它不能被声明为 clean residual family。

## 10. Style Exposure Audit

所有 train-selected family 的 style-exposure clean gate 都是 false。原因有两层：

- style evaluable dates 在 validation/robustness 中只有 10 到 13 个，不足以支持 clean gate；
- validation 的 style-explained score R2 普遍高于 0.35，说明 family score 与 industry/liquidity/beta/volatility/money 分组关系较强。

| family | horizon | validation style dates | validation R2 | validation spread share | neutralized spread retention | style clean |
|:--|:--|--:|--:|--:|--:|:--|
| close_location | H20 | 10 | 0.667 | 180.76% | 0.07% | False |
| composite_price_volume | H20 | 10 | 0.528 | -32.41% | 45.79% | False |
| other_gtja191 | H20 | 10 | 0.606 | 13.38% | 177.84% | False |
| range_volatility | H1 | 10 | 0.484 | -70.92% | -53.76% | False |
| volume_price_correlation | H3 | 10 | 0.490 | 60.72% | -34.63% | False |
| volume_surge_money_flow | H3 | 10 | 0.445 | -92.56% | -102.29% | False |
| vwap_deviation | H3 | 10 | 0.649 | 32.87% | 83.41% | False |

这并不等于说所有弱 spread 都完全由 style 解释，但足以说明本次不能把它们报告为干净 residual information。换句话说，R06 找到了局部信号痕迹，但没有证明这些痕迹脱离了风格、流动性、beta、波动或 money exposure。

## 11. Cost Sensitivity

R06 同时输出 gross 和 net。validation/robustness 中没有出现“gross positive 但 net negative”的 family-horizon 行；H3 弱正 family 的成本存活率为 98.90%。

| family | horizon | validation gross spread | validation net spread | cost drag | cost survival |
|:--|:--|--:|--:|--:|--:|
| volume_price_correlation | H3 | 0.335% | 0.331% | 0.004% | 98.90% |
| volume_surge_money_flow | H3 | 0.259% | 0.256% | 0.003% | 98.90% |
| vwap_deviation | H3 | 0.219% | 0.217% | 0.002% | 98.90% |

所以 R06 的失败不是“交易成本完全吃掉信号”。更准确的说法是：成本之后仍有很小的弱正 spread，但它没有单调性，也没有通过 persistent-name 和 style clean gates。

## 12. Final Gate Replay

| family | horizon | information | monotonicity | persistent clean | style clean | cost survives | supported | tradeable candidate |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| close_location | H20 | False | False | False | False | False | False | False |
| composite_price_volume | H20 | False | False | False | False | False | False | False |
| other_gtja191 | H20 | False | False | False | False | False | False | False |
| range_volatility | H1 | False | False | False | False | False | False | False |
| rank_ts_rank_structure | H3 | False | False | False | False | False | False | False |
| volume_price_correlation | H3 | True | False | False | False | True | False | False |
| volume_surge_money_flow | H3 | True | False | False | False | True | False | False |
| vwap_deviation | H3 | True | False | False | False | True | False | False |

Decision replay 中 `rule_07` 命中：

```text
r06_decay_information_exists_but_not_tradeable
```

`rule_05 = r06_factor_family_information_supported` 没有命中，`rule_06 = r06_relative_information_only` 也没有命中，因为没有 clean residual family。

## 13. R06 与 R05 的关系：对失败形态的解释

R05 H10 validation 的关键形态是：弱正 mean matched delta、负 median matched delta、2023 反转、persistent-name concentration 极高。R06 对它的解释如下。

H10 validation 中，少数 family 还能给出正 top-bottom spread：

| family | H10 validation RankIC | H10 matched-delta spread | H10 net spread | monotonicity | positive date share |
|:--|--:|--:|--:|--:|--:|
| vwap_deviation | -0.00108 | 0.244% | 0.248% | 0.015 | 56.25% |
| volume_price_correlation | 0.00973 | 0.160% | 0.168% | 0.048 | 48.96% |
| volume_surge_money_flow | 0.00560 | 0.109% | 0.132% | -0.016 | 51.04% |
| composite_price_volume | 0.00234 | 0.017% | 0.024% | -0.016 | 43.75% |
| other_gtja191 | -0.00744 | -0.241% | -0.222% | -0.084 | 38.54% |
| range_volatility | -0.00720 | -0.264% | -0.270% | -0.039 | 42.71% |
| close_location | -0.01149 | -0.633% | -0.586% | -0.131 | 40.62% |

这说明 R05 的 H10 弱正均值大概率来自局部量价 / vwap family 的小幅 spread，而不是来自整个 Alpha191 库的稳定排序能力。与此同时，`close_location`、`other_gtja191`、`range_volatility` 在 H10/H20 上拖累明显。

更关键的是，H10 正 spread family 的 monotonicity 很低，positive date share 不稳定，且 R06 的 persistent-name 与 style gates 均没有支持 clean residual 解释。因此 R05 的弱正 mean 不能被拿来救回 R05 composite，也不能被解释为 long-only alpha。

## 14. 研究判断

R06 后，Alpha191 在当前 EP5 short-horizon 框架下的状态应被理解为：

```text
有局部短周期信息痕迹；
没有可交易的 clean residual family；
不能进入 broad Alpha191 strategy requirement；
若继续，只能做更窄的诊断或 hedged-only 论证。
```

不建议下一步继续做：

- 换 top fraction；
- 用 validation 最好的 horizon 回填策略；
- 对 H3 family 做 validation-driven factor selection；
- 用 persistent-name filter 事后修补；
- 用 right-tail / big-winner readout 救回结论。

如果要继续研究，唯一合理方向是重新定义一个更窄的问题，例如：

```text
H3 量价 / vwap family 的 matched-delta 信息，
在剥离 persistent-name 与 style exposure 后是否仍存在。
```

但这已经不是 R06 的通过结论，也不能直接授权 R07 long-only strategy。

## 15. Requirement 必答问题

1. R06 是否避免构造策略或 top20% exposure unit？是。R06 只做 factor / family / horizon 信息审计。
2. GTJA191 因子纳入和剔除数量是多少？source 191，included 125，excluded 66。
3. 因子如何映射到 family？使用公式文本、字段名和预声明 taxonomy 形成 8 个 primary families；不使用 R04/R05 性能证据。
4. Alpha191 是否仍有短周期横截面信息？有局部弱信息，主要在 H1/H3/H5；但不是 clean tradeable information。
5. H1/H3/H5/H10/H20 的 RankIC decay curve 是什么？validation mean family RankIC 分别为 0.01057、0.00580、0.00308、-0.00046、-0.00691，H10/H20 明显衰减。
6. 哪些 horizon 的 train evidence 最强？family mean RankIC 在 train 中 H3/H5/H20 较强，但 validation 只支持更短 horizon，H20 外推失败。
7. 哪些 family horizon 由 train-only 选中？`close_location H20`、`composite_price_volume H20`、`other_gtja191 H20`、`range_volatility H1`、`rank_ts_rank_structure H3`、`volume_price_correlation H3`、`volume_surge_money_flow H3`、`vwap_deviation H3`。
8. 哪些 family 保留 validation information？`volume_price_correlation H3`、`volume_surge_money_flow H3`、`vwap_deviation H3` 通过 information-positive。
9. 哪些 family 保留 robustness information？上述三个 H3 family 在 robustness 中仍为正 spread，但幅度下降，且 clean gates 不通过。
10. 哪些 family 失败于 monotonic decile spread？所有 train-selected family 都失败，`family_monotonicity_positive = true` 的数量为 0。
11. 哪些 family gross-positive 但 net-negative？validation/robustness 中没有这种主失败形态。成本不是主要问题。
12. 哪些 family 是 persistent-name driven？`close_location H20`、`composite_price_volume H20`、`other_gtja191 H20`、`volume_surge_money_flow H3`、`vwap_deviation H3` 明显失败；`volume_price_correlation H3` top-decile 干净但 top-quintile 失败，因此 family-level 仍不干净。
13. 哪些 family 是 industry/liquidity/beta/volatility/money exposure driven？所有 train-selected family 的 style clean gate 都是 false，不能声明为风格剥离后的 residual information。
14. 是否有 family 在 style neutralization 后显示 residual information？没有达到 R06 clean residual 门槛。
15. 是否有 family 支持后续 R07 strategy requirement？没有。`family_tradeable_research_candidate = true` 的数量为 0。
16. 如果允许 R07，应是 long-only 还是 hedged / relative only？本次不授权 R07。若另立新问题，也只能从 H3 matched-delta / hedged-only 诊断开始，不能从 H1/H3 gross evidence 推出 long-only。
17. 如果 R06 失败，Alpha191 short-horizon 方向是否应暂停？若目标是 broad Alpha191 short-horizon strategy，应暂停；若目标改成更窄的量价 family 残差信息诊断，需要新 requirement。
18. R06 是否解释了 R05 H10 validation 的弱正均值、负中位数、2023 反转与 persistent-name 集中？是。弱正均值主要来自量价 / vwap family 的局部 spread，但这些 spread 不单调、不过 persistent/style clean gates，无法救回 R05。

## 16. Validator

`validation_status = passed`; failed gates = `0`。

本报告为基于已生成 R06 artifacts 的中文详细报告更新，未重跑实验代码，也未修改 runner、validator 或 requirement。
