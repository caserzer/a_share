# R07 短周期择时与失败归因审计报告

## 1. 结论摘要

`final_decision = r07_insufficient_state_cell_sample_blocked`，触发规则为 `rule_03`：

```text
Q1_pocket_cell_count > 0
and
state_cell_sample_majority_blocked = true
```

这不是“没有短周期相对信息”的结论。R07 实际看到 `14` 个 Q1 relative-pocket cell，其中 `11 / 14` 在 robustness 上仍有类似的正向 pocket 形态。问题在于：这些 pocket 在无状态条件下无法通过 clean-attribution gates；进入 3x3 状态切片后，`112 / 126 = 88.89%` 的 Q3 state cells 被样本地板挡住，剩余可评价 cell 也没有任何一个通过五门、non-deterioration 与样本门的联合约束。

核心读法：

- Q1：局部短周期 pocket 存在，主要在 H1/H3，少数在 H5/H10。
- Q2：`0 / 14` 个 pocket 是 unconditioned clean cell。monotonicity、persistent-clean、style-clean 三个 gate 全部 `0 / 14`。
- Q3：`0 / 126` 个 state cell 稳定；`14 / 126` 个 state cell 通过样本门，但这些可评价 cell 的 validation spread 平均并不强，且 gate count 远未达到 5/5。
- 交易成本不是主因。Q2 cost gate 通过 `12 / 14`；Q3 validation cost-survives 通过 `77 / 126`，robustness 通过 `84 / 126`。失败主要来自排序形态不单调、风格/常驻名解释未清除，以及状态切片后的样本不足。

因此 R07 不授权任何 downstream requirement。更准确地说，R07 将 EP5 short-horizon line 停在“状态归因无法诚实完成，且已有 pocket 也没有 clean 到足以继续”的位置，而不是停在“完全没有信息”的位置。

## 2. 实验契约与数据边界

R07 沿用 R06/R05 的本地 PIT mcap500 mainboard universe、weekly close-observed signal、next-open execution、matched comparator 和 110bps round-trip cost。R07 没有构造策略、没有 top-N/top-fraction basket、没有回测曲线、没有 online data。

Family scope 为 R06 的 8 个 primary families；horizon grid 为 `{H1, H3, H5, H10}`，H20 被排除。

| family | R06 train-selected primary horizon | included factor count |
|:--|:--|--:|
| close_location | H20 | 18 |
| composite_price_volume | H20 | 62 |
| other_gtja191 | H20 | 17 |
| range_volatility | H1 | 3 |
| rank_ts_rank_structure | H3 | 1 |
| volume_price_correlation | H3 | 3 |
| volume_surge_money_flow | H3 | 15 |
| vwap_deviation | H3 | 6 |

两个状态轴均为 train-only frozen：

| axis | definition | train bin edges | frozen before validation |
|:--|:--|:--|:--|
| axis_market_regime | CSI300 close-to-close 20-day return at signal date | `[-0.016355494658152267, 0.025384704271952285]` | True |
| axis_stock_short_momentum | stock close-to-close 10-day return at signal date | `[-0.021958351135253917, 0.02976942062377924]` | True |

状态空间为 `3 x 3 = 9` cells。R07 总 Q3 denominator 为：

```text
Q1_pocket_cell_count * state_cell_count = 14 * 9 = 126
```

## 3. Q1 路径分解：pocket 在哪里

R07 在 validation 上识别出 `14 / 32` 个 family-horizon cell 为 Q1 pocket。按 horizon 分布：

| horizon | Q1 pocket 数 | 解释 |
|:--|--:|:--|
| H1 | 7 | pocket 最宽，说明短端确实有残余信息痕迹 |
| H3 | 4 | pocket 最有经济含义，尤其是量价相关 family |
| H5 | 2 | 局部存在，但 robustness 稳定性分化 |
| H10 | 1 | 只剩 `volume_surge_money_flow`，不是主线 |

按 family 分布：

| family | Q1 pocket 数 | 读法 |
|:--|--:|:--|
| volume_surge_money_flow | 4 | H1/H3/H5/H10 都出现，覆盖最广 |
| rank_ts_rank_structure | 2 | H1/H3 有 pocket，但 family 只有 1 个 included factor，解释力较弱 |
| composite_price_volume | 2 | H1/H3 有 pocket，但 family 很宽，容易混入风格/流动性 |
| volume_price_correlation | 2 | H1/H3 最值得关注，spread 和 robustness 都较好 |
| vwap_deviation | 2 | H1/H5 有 pocket，H5 的 state spread 局部很高但样本薄 |
| close_location | 1 | 只有 H1 |
| other_gtja191 | 1 | 只有 H1 |

Q1 pocket 的跨 split 明细如下。`robust-like` 是一个报告内辅助读法：robustness 同时满足 spread >= 5bps、RankIC >= 0、positive date share >= 50%。它不是 R07 决策 gate。

| family | H | train spread | validation spread | robustness spread | validation RankIC | robustness RankIC | validation 正 spread 日期 | robustness 正 spread 日期 | robustness 类似通过 |
|:--|:--|--:|--:|--:|--:|--:|--:|--:|:--|
| volume_price_correlation | H3 | 0.358% | 0.333% | 0.170% | 0.927% | 1.751% | 61.22% | 52.94% | True |
| volume_surge_money_flow | H5 | 0.317% | 0.274% | 0.038% | 1.148% | 0.864% | 54.64% | 50.00% | False |
| volume_price_correlation | H1 | 0.151% | 0.247% | 0.095% | 2.581% | 1.684% | 61.22% | 57.28% | True |
| volume_surge_money_flow | H3 | 0.431% | 0.238% | 0.101% | 1.700% | 0.771% | 57.14% | 53.92% | True |
| vwap_deviation | H1 | 0.122% | 0.230% | 0.089% | 1.321% | 1.675% | 58.16% | 56.31% | True |
| rank_ts_rank_structure | H1 | 0.119% | 0.229% | 0.047% | 2.445% | 1.005% | 60.20% | 55.34% | False |
| volume_surge_money_flow | H1 | 0.136% | 0.194% | 0.207% | 2.435% | 2.702% | 61.22% | 62.14% | True |
| composite_price_volume | H3 | 0.446% | 0.121% | 0.138% | 0.780% | 1.516% | 54.08% | 59.80% | True |
| close_location | H1 | 0.055% | 0.121% | 0.173% | 0.352% | 1.297% | 59.18% | 58.25% | True |
| vwap_deviation | H5 | 0.175% | 0.115% | 0.123% | 0.897% | 1.603% | 58.76% | 51.96% | True |
| volume_surge_money_flow | H10 | 0.415% | 0.109% | 0.125% | 0.781% | 1.235% | 51.04% | 54.46% | True |
| composite_price_volume | H1 | 0.218% | 0.109% | 0.258% | 2.097% | 3.361% | 55.10% | 65.05% | True |
| rank_ts_rank_structure | H3 | 0.417% | 0.098% | -0.104% | 1.836% | -0.663% | 53.06% | 44.12% | False |
| other_gtja191 | H1 | 0.096% | 0.073% | 0.138% | 1.365% | 1.290% | 51.02% | 57.28% | True |

**发现 1：R07 的 Q1 不是空的，而且不是单点偶然。** `11 / 14` 个 Q1 pockets 在 robustness 上仍有类似正向形态，说明 R06 所说的 short-horizon weak information residue 是真实存在的。

**发现 2：最像“信息”的 cell 是 H3 的 `volume_price_correlation`。** 它的 validation spread 为 `0.333%`，robustness spread 为 `0.170%`，两个 split 的 RankIC 都为正。这个 cell 是后续所有讨论中最强的正例。

**发现 3：pocket 不是 H10 主导。** H10 只有 `volume_surge_money_flow` 一个 Q1 pocket，且 R06 已经显示 H10/H20 是 decay tail。R07 支持“信息前置在 H1/H3，少数延伸到 H5”的判断。

## 4. Q2 无状态 clean attribution：为什么 pocket 不能直接用

Q2 只在 14 个 Q1-pocket cells 上评价 R06 五门。结果：

| gate | 通过数 | 失败数 | 解释 |
|:--|--:|--:|:--|
| information | 9 / 14 | 5 / 14 | 不是所有 pocket 都有足够跨 split 信息支撑 |
| monotonicity | 0 / 14 | 14 / 14 | 最大硬伤，top-bottom spread 没有稳定单调排序形态 |
| persistent-clean | 0 / 14 | 14 / 14 | 常驻名单解释没有被清除 |
| style-clean | 0 / 14 | 14 / 14 | 风格/行业/流动性/beta/money 解释没有被清除 |
| cost-survives | 12 / 14 | 2 / 14 | 成本不是主要失败来源 |
| Q2 unconditional clean | 0 / 14 | 14 / 14 | 没有任何 cell 能在无状态层面 clean |

Q2 明细：

| family | H | info | monotonic | persistent | style | cost | Q2 clean | 失败集合 |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| close_location | H1 | True | False | False | False | True | False | monotonicity; persistent; style |
| composite_price_volume | H1 | True | False | False | False | True | False | monotonicity; persistent; style |
| composite_price_volume | H3 | False | False | False | False | True | False | information; monotonicity; persistent; style |
| other_gtja191 | H1 | False | False | False | False | True | False | information; monotonicity; persistent; style |
| rank_ts_rank_structure | H1 | True | False | False | False | False | False | monotonicity; persistent; style; cost |
| rank_ts_rank_structure | H3 | False | False | False | False | False | False | information; monotonicity; persistent; style; cost |
| volume_price_correlation | H1 | True | False | False | False | True | False | monotonicity; persistent; style |
| volume_price_correlation | H3 | True | False | False | False | True | False | monotonicity; persistent; style |
| volume_surge_money_flow | H1 | True | False | False | False | True | False | monotonicity; persistent; style |
| volume_surge_money_flow | H3 | True | False | False | False | True | False | monotonicity; persistent; style |
| volume_surge_money_flow | H5 | False | False | False | False | True | False | information; monotonicity; persistent; style |
| volume_surge_money_flow | H10 | False | False | False | False | True | False | information; monotonicity; persistent; style |
| vwap_deviation | H1 | True | False | False | False | True | False | monotonicity; persistent; style |
| vwap_deviation | H5 | True | False | False | False | True | False | monotonicity; persistent; style |

失败解释计数：

| failure explanation | count |
|:--|--:|
| monotonicity_fail | 14 |
| style_clean_fail | 14 |
| persistent_clean_fail | 14 |
| information_fail | 5 |
| cost_survival_fail | 2 |

**发现 4：成本不是主矛盾。** 如果成本是主因，应该看到 gross positive 但 net 被吃掉；但 Q2 cost-survives 通过 `12 / 14`。R07 的失败更接近“有一点 spread，但排序形态和归因都不干净”。

**发现 5：Q2 对 R05 的解释比对 R01 更直接。** R05 的失败形态是弱均值、负中位数、2023 reversal 和 persistent-name concentration。R07 这里看到所有 Q1 pockets 都无法通过 persistent-clean 和 style-clean，因此 R05 不是被一个更好 horizon 或更好 state 简单救回。

## 5. Q3 状态稳定性：为什么 rule_03 先触发

Q3 把每个 Q1 pocket 切到 9 个 state cells，总计 `126` 个 state cells。

样本门结果：

| item | count |
|:--|--:|
| Q3 denominator | 126 |
| state_cell_sample_pass | 14 |
| state_cell_sample_blocked | 112 |
| blocked share | 88.89% |

具体短缺来自哪里：

| sample floor 失败项 | 失败 cells | 占比 |
|:--|--:|--:|
| train_event_count < 200 | 0 / 126 | 0.00% |
| validation_event_count < 80 | 0 / 126 | 0.00% |
| robustness_event_count < 60 | 0 / 126 | 0.00% |
| validation_date_count < 20 | 42 / 126 | 33.33% |
| robustness_date_count < 20 | 0 / 126 | 0.00% |
| validation_min_state_date_cross_section_count < 30 | 84 / 126 | 66.67% |
| robustness_min_state_date_cross_section_count < 30 | 84 / 126 | 66.67% |

**关键解释：不是事件总数不够，而是状态切片后每个 signal date 的横截面太薄。** R07 的 state axis 把 universe 分成 9 份，很多 state 在某些周只剩个位数或十几只股票。对 top-tercile vs bottom-tercile spread、style OLS、persistent-name turnover 来说，这种 per-date cross-section 不足会让结论不诚实。

每个 Q1 pocket 下 9 个 state cells 的样本通过情况：

| family | H | 样本通过 | 样本阻断 | 最高 validation spread | 最高 robustness spread |
|:--|:--|--:|--:|--:|--:|
| vwap_deviation | H5 | 1 | 8 | 0.768% | 0.615% |
| rank_ts_rank_structure | H1 | 1 | 8 | 0.526% | 0.403% |
| volume_surge_money_flow | H10 | 1 | 8 | 0.448% | 0.680% |
| rank_ts_rank_structure | H3 | 1 | 8 | 0.408% | 0.343% |
| other_gtja191 | H1 | 1 | 8 | 0.363% | 0.248% |
| volume_price_correlation | H3 | 1 | 8 | 0.355% | 0.394% |
| composite_price_volume | H1 | 1 | 8 | 0.346% | 0.387% |
| volume_price_correlation | H1 | 1 | 8 | 0.345% | 0.289% |
| composite_price_volume | H3 | 1 | 8 | 0.306% | 0.599% |
| volume_surge_money_flow | H1 | 1 | 8 | 0.284% | 0.269% |
| volume_surge_money_flow | H5 | 1 | 8 | 0.282% | 0.847% |
| volume_surge_money_flow | H3 | 1 | 8 | 0.261% | 0.518% |
| vwap_deviation | H1 | 1 | 8 | 0.201% | 0.245% |
| close_location | H1 | 1 | 8 | 0.185% | 0.273% |

看起来每个 pocket 都有一个 state cell 通过样本门，但这 14 个通过样本门的 state cell 全部是同一个状态：`market_flat|stock_flat`。它们的明细如下：

| family | H | state | validation spread | robustness spread | validation gates | robustness gates | nondet validation | nondet robustness | Q3 stable |
|:--|:--|:--|--:|--:|--:|--:|:--|:--|:--|
| vwap_deviation | H1 | market_flat\|stock_flat | 0.186% | 0.134% | 2 | 2 | False | False | False |
| rank_ts_rank_structure | H1 | market_flat\|stock_flat | 0.135% | 0.068% | 1 | 2 | False | False | False |
| volume_surge_money_flow | H10 | market_flat\|stock_flat | 0.099% | 0.142% | 1 | 2 | False | False | False |
| volume_price_correlation | H1 | market_flat\|stock_flat | 0.040% | -0.124% | 1 | 0 | False | False | False |
| composite_price_volume | H1 | market_flat\|stock_flat | -0.005% | 0.113% | 0 | 2 | False | True | False |
| rank_ts_rank_structure | H3 | market_flat\|stock_flat | -0.021% | -0.012% | 0 | 0 | False | False | False |
| volume_surge_money_flow | H3 | market_flat\|stock_flat | -0.066% | 0.061% | 0 | 1 | False | False | False |
| close_location | H1 | market_flat\|stock_flat | -0.082% | 0.123% | 0 | 2 | False | False | False |
| volume_surge_money_flow | H1 | market_flat\|stock_flat | -0.128% | 0.054% | 0 | 2 | False | True | False |
| composite_price_volume | H3 | market_flat\|stock_flat | -0.170% | 0.002% | 0 | 1 | False | False | False |
| volume_price_correlation | H3 | market_flat\|stock_flat | -0.190% | -0.189% | 0 | 0 | False | False | False |
| other_gtja191 | H1 | market_flat\|stock_flat | -0.202% | -0.054% | 0 | 0 | False | True | False |
| vwap_deviation | H5 | market_flat\|stock_flat | -0.204% | -0.251% | 0 | 0 | False | False | False |
| volume_surge_money_flow | H5 | market_flat\|stock_flat | -0.401% | -0.236% | 0 | 0 | False | False | False |

**发现 6：通过样本门的状态恰好不是 pocket 最强的状态。** `market_flat|stock_flat` 是唯一足够厚的状态，但它的 validation spread 在 14 个 cells 中只有 3 个为正且超过 10bps，多数为负或接近零。真正高 spread 的状态往往样本不过关。

高 validation spread 的 state cells 如下。这些是最像“状态条件可能有用”的地方，但它们都没有通过样本门。

| family | H | state | 样本 | validation spread | robustness spread | validation 最小横截面 | robustness 最小横截面 | validation gates | robustness gates | Q3 stable |
|:--|:--|:--|:--|--:|--:|--:|--:|--:|--:|:--|
| vwap_deviation | H5 | market_flat\|stock_up | False | 0.768% | 0.523% | 4 | 23 | 2 | 3 | False |
| rank_ts_rank_structure | H1 | market_down\|stock_up | False | 0.526% | -0.047% | 9 | 6 | 3 | 1 | False |
| volume_surge_money_flow | H10 | market_flat\|stock_down | False | 0.448% | 0.680% | 18 | 19 | 2 | 2 | False |
| volume_surge_money_flow | H10 | market_up\|stock_flat | False | 0.428% | -0.665% | 67 | 1 | 2 | 0 | False |
| rank_ts_rank_structure | H3 | market_flat\|stock_up | False | 0.408% | 0.343% | 4 | 23 | 3 | 3 | False |
| vwap_deviation | H5 | market_down\|stock_flat | False | 0.401% | -0.301% | 25 | 40 | 2 | 0 | False |
| other_gtja191 | H1 | market_down\|stock_up | False | 0.363% | 0.248% | 9 | 6 | 3 | 2 | False |
| volume_price_correlation | H3 | market_down\|stock_flat | False | 0.355% | 0.084% | 25 | 40 | 3 | 2 | False |
| composite_price_volume | H1 | market_down\|stock_up | False | 0.346% | 0.387% | 9 | 6 | 3 | 3 | False |
| volume_price_correlation | H1 | market_down\|stock_up | False | 0.345% | 0.289% | 9 | 6 | 3 | 3 | False |
| composite_price_volume | H3 | market_flat\|stock_up | False | 0.306% | 0.086% | 4 | 23 | 2 | 1 | False |
| volume_surge_money_flow | H1 | market_up\|stock_up | False | 0.284% | 0.202% | 41 | 34 | 2 | 2 | False |

状态维度的聚合也说明同一个问题：

| state_cell | 样本通过数 | 平均 validation spread | 平均 robustness spread | 平均 validation gates | 平均 robustness gates | 平均 validation 最小横截面 | 平均 robustness 最小横截面 |
|:--|--:|--:|--:|--:|--:|--:|--:|
| market_flat\|stock_down | 0 | 0.137% | 0.251% | 1.21 | 1.93 | 18.5 | 19.5 |
| market_down\|stock_flat | 0 | 0.131% | 0.005% | 1.57 | 1.00 | 25.0 | 40.0 |
| market_down\|stock_up | 0 | 0.130% | 0.322% | 2.07 | 2.64 | 9.1 | 6.2 |
| market_down\|stock_down | 0 | 0.108% | 0.161% | 1.64 | 1.50 | 24.0 | 15.5 |
| market_flat\|stock_up | 0 | 0.096% | 0.169% | 1.64 | 1.93 | 4.0 | 23.5 |
| market_up\|stock_up | 0 | 0.016% | -0.064% | 0.93 | 0.64 | 41.0 | 34.0 |
| market_up\|stock_flat | 0 | 0.006% | -0.077% | 1.07 | 0.71 | 67.0 | 1.0 |
| market_flat\|stock_flat | 14 | -0.072% | -0.012% | 0.36 | 1.00 | 39.0 | 60.1 |
| market_up\|stock_down | 0 | -0.202% | 0.014% | 1.00 | 1.71 | 12.0 | 1.0 |

**发现 7：状态条件的正向读数与样本可评价性错位。** 有正 spread 的状态主要是 `market_flat|stock_down`、`market_down|stock_flat`、`market_down|stock_up`、`market_flat|stock_up`，但这些状态全部样本通过数为 0。唯一样本通过的 `market_flat|stock_flat` 平均 validation spread 是 `-0.072%`。

## 6. Q3 五门与 non-deterioration

所有 `126` 个 state cells 的 gate 统计：

| gate | validation 通过 | robustness 通过 | 解释 |
|:--|--:|--:|:--|
| information | 57 / 126 | 67 / 126 | 局部信息存在，但不稳定到足以单独支撑 |
| monotonicity | 0 / 126 | 0 / 126 | 全局硬失败 |
| persistent-clean | 27 / 126 | 32 / 126 | 局部状态能缓解常驻名，但远不足以整体 clean |
| style-clean | 0 / 126 | 0 / 126 | 全局硬失败 |
| cost-survives | 77 / 126 | 84 / 126 | 成本多数情况下能存活 |
| non-deterioration | 27 / 126 | 44 / 126 | 很多正 spread cell 相对 train 仍恶化 |
| train information positive | 88 / 126 | n/a | train 内不是完全没信号 |
| sample pass | 14 / 126 | n/a | 决定性 blocker |
| Q3 stable | 0 / 126 | n/a | 无授权 cell |
| long-only absolute candidate gate | 0 / 126 | n/a | 没有 long-only 候选 |

Gate count 分布：

| passed gate count | validation cells | robustness cells |
|:--|--:|--:|
| 0 / 5 | 38 | 36 |
| 1 / 5 | 29 | 19 |
| 2 / 5 | 45 | 49 |
| 3 / 5 | 14 | 22 |
| 4 / 5 | 0 | 0 |
| 5 / 5 | 0 | 0 |

**发现 8：没有任何 cell 接近“差一点通过”。** 最多只有 3/5 gates，没有 4/5，更没有 5/5。即使忽略样本门，状态条件也没有形成 clean-stable pocket。

**发现 9：monotonicity 与 style 是两个不可绕过的硬障碍。** 这两个 gate 在 validation 和 robustness 都是 `0 / 126`。这说明 R07 没有找到“状态条件下的干净排序结构”，也没有找到“状态条件下的非风格解释”。

## 7. Hedged preflight

Hedged preflight 没有触发：

```text
trigger_satisfied = false
skipped_reason = no_Q3_stable_relative_trigger
preflight_conclusion = not_triggered_skipped
```

原因很直接：R07 没有任何 Q3-stable cell，因此不存在需要 read-only hedge feasibility 检查的触发对象。R07 也没有使用 online hedge/margin/financing data。

## 8. First-match rule replay

| rule | 原始条件 | first-match 触发 | decision |
|:--|:--|:--|:--|
| rule_01 | False | False | r07_audit_scope_violation_blocked |
| rule_02 | False | False | r07_no_relative_pocket_in_scope |
| rule_03 | True | True | r07_insufficient_state_cell_sample_blocked |
| rule_04 | False | False | r07_state_stable_clean_pocket_supported |
| rule_05 | False | False | r07_relative_pocket_clean_but_not_state_stable |
| rule_06 | False | False | r07_relative_pocket_clean_but_not_state_stable |
| rule_07 | True | False | r07_relative_pocket_explained_by_style_or_persistent_name |

注意：`rule_07` 的原始条件也为 true，但因为 R07 是 first-match replay，`rule_03` 先触发，所以最终 decision 是 `r07_insufficient_state_cell_sample_blocked`，不是 `r07_relative_pocket_explained_by_style_or_persistent_name`。

这个差异很重要：R07 的最终结论不是“已经证明 pocket 完全由 style/persistent-name 解释”，而是“在当前 contract 下，状态归因样本多数不可评价；同时无状态 clean attribution 已经失败，因此不能继续写 downstream requirement”。

## 9. 对 R01 / R05 / R06 的归因回答

### Q11. 相比 R01 的 relative pocket，R07 找到它在哪里了吗？

找到了大致位置：pocket 不集中在一个 H10 answer，而是主要在 H1/H3，尤其是 `volume_price_correlation H3`、`volume_surge_money_flow H3/H1`、`vwap_deviation H1/H5`。这说明 R01 的弱 residual mean 不是完全孤立现象，但 R07 没有把它变成 clean state-stable evidence。

### Q12. 相比 R05 的 H10 pocket，R07 是否确认 persistent-name 是主解释？

R07 在无状态层面支持这个解释：Q2 persistent-clean 为 `0 / 14`。但由于最终 rule_03 是样本阻断，R07 不声称“每个状态条件下都证明 persistent-name 是唯一解释”。更严谨的说法是：

```text
R05 的 persistent-name 风险没有被 R07 消除；
R07 也没有找到一个样本足够、状态稳定、clean 的反例。
```

### Q13. 相比 R06 的 H3 information-positive families，R07 是否确认 style exposure 是主解释？

R07 确认 style-clean 是硬 blocker：Q2 style-clean 为 `0 / 14`，Q3 validation/robustness style-clean 都是 `0 / 126`。这比 persistent-name 更硬，因为它在无状态和状态条件下都没有任何通过 cell。

但同样需要精确表述：R07 不是证明所有 spread 都等于 style exposure；R07 证明的是，在当前数据、状态轴、样本门和 style-clean gate 下，没有足够证据把这些 spread 报告为 clean residual edge。

## 10. 是否授权 downstream requirement

不授权。

```text
downstream_authorization_scope_recorded = false
Q3_stable_cell_count = 0
Q3_stable_short_horizon_cell_count = 0
long_only_absolute_candidate_gate_count = 0
hedged_preflight_trigger = false
```

R07 没有给出：

- long-only research candidate；
- hedged research candidate；
- relative research candidate；
- family/horizon/state-cell narrowed downstream scope。

## 11. 主要发现与研究判断

### 发现 A：Alpha191 short-horizon 不是“完全没信息”

Q1 有 `14` 个 pocket，且 `11` 个在 robustness 上仍像 pocket。最强的是：

```text
volume_price_correlation H3:
  validation spread = 0.333%
  robustness spread = 0.170%
  validation RankIC = 0.927%
  robustness RankIC = 1.751%
```

所以如果 EP5 final report 需要一句话总结 R07，不应该写成“R07 没找到任何信息”。更准确的说法是：

```text
R07 找到了短周期相对信息残留，但没有找到可归因、可稳定、可授权的 clean pocket。
```

### 发现 B：pocket 的有效部分更像 H1/H3 timing residue，而不是 H10 exposure

H1 pocket count = 7，H3 = 4，H5 = 2，H10 = 1。这个形态与 R06 的 decay curve 一致：信息在短 horizon 更明显，越往 H10/H20 越像 decay tail。

这也解释了为什么 R05 的 H10 composite 不能通过：H10 不是没有任何读数，但已经不是信息最干净、最集中的位置。

### 发现 C：成本不是失败主因

R07 的 cost gate 大部分通过：

- Q2 cost-survives：`12 / 14`
- Q3 validation cost-survives：`77 / 126`
- Q3 robustness cost-survives：`84 / 126`

因此不能把 EP5 short-horizon 的失败归因写成“110bps 太高”。更准确的失败链条是：

```text
weak spread exists
-> cost often survives
-> monotonicity fails
-> persistent/style clean fails
-> state conditioning creates severe per-date sample thinning
-> no Q3-stable clean cell
```

### 发现 D：状态轴没有救回信号，反而暴露了样本不可评价性

最值得注意的不是“所有状态都差”，而是：

- 高 spread 的状态 sample 不过关；
- sample 过关的 `market_flat|stock_flat` 状态平均 spread 反而偏弱；
- 没有任何 state cell 达到 4/5 或 5/5 gates；
- style 和 monotonicity 在状态层面仍是 0 pass。

这说明“加状态条件”没有把 pocket 从风格/常驻名解释中分离出来。更可能的情况是，pocket 来自若干局部市场状态或股票状态下的拥挤/风格暴露，但这些局部状态太薄，无法在当前 contract 下做成诚实的可评价单元。

### 发现 E：R07 的 stop 是方法论 stop，不是市场预测 stop

`r07_insufficient_state_cell_sample_blocked` 的含义是：当前 R07 contract 不能继续往下写策略或下一阶段 requirement。它不是说未来任何数据、任何 universe、任何 cadence 下都没有 Alpha191 短线信息。

但在 EP5 当前边界内，继续调状态轴、放松样本门、放松 monotonicity/style gate，都会变成 post-hoc search。R07 明确禁止这样做。

## 12. 对 EP5 后续的建议

1. EP5 short-horizon line 应该按 R07 stop case 关闭，不再新写同 contract 下的 short-horizon requirement。
2. EP5 final report 应把结论写成“weak information residue exists but cannot be cleanly attributed or state-stabilized”，不要写成“Alpha191 完全无信息”。
3. 如果后续仍要研究 Alpha191，必须换问题定义，而不是在 R07 内继续调参。例如只能作为更长周期、不同 universe、或纯归因研究的背景材料；不能在当前 EP5 short-horizon execution contract 下继续推进。
4. R07 的最强正例 `volume_price_correlation H3` 可以在 final report 中作为“为什么我们没有说完全无信息”的证据；但它不能作为 downstream strategy seed，因为 Q2/Q3 clean gates 均未通过。

## 13. Artifact 对照

主要证据文件：

| artifact | 用途 |
|:--|:--|
| `artifacts/r07_path_decomposition.csv` | Q1 pocket 识别、H1/H3/H5/H10 path decomposition |
| `artifacts/r07_clean_attribution.csv` | Q2 五门、failure explanation set |
| `artifacts/r07_state_stability.csv` | Q3 state-cell 样本、五门、non-deterioration、absolute candidate gate |
| `artifacts/r07_final_decision_inputs.csv` | final decision 计数输入 |
| `artifacts/r07_final_decision_replay_audit.csv` | first-match rule replay |
| `artifacts/r07_hedged_preflight.csv` | hedged preflight trigger 与 skip 原因 |
| `artifacts/r07_state_axis_definition.csv` | train-frozen state bin edges |
| `manifests/r07_validation.json` | validator status |

Validator 状态：

```text
validation_status = passed
gate_count = 26
passed_gate_count = 26
failed_gate_count = 0
```
