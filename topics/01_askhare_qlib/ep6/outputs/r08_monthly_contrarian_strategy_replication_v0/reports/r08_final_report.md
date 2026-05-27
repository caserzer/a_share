# R08 月度反向策略复现 V0 详细报告

## 1. 最终结论

`final_decision = ep6_monthly_contrarian_validation_only_not_robust`

`authorized_strategy_requirement = false`

本轮复现把 Shi/Jiang/Zhou (2015) 的月度反向策略转成一个本地可执行的 PIT mcap500 mainboard/Qlib 代理实验。它不是 RESSET 1997-2012 全 A 股样本的精确复刻。当前本地样本的结论很明确:

- validation 阶段支持月度反向: 主决策簇 L-W 月均 `+1.478%`，Newey-West t=`1.6045`，after-cost 月均 `+1.140%`。
- robustness 阶段不支持月度反向: 主决策簇 L-W 月均 `-0.761%`，Newey-West t=`-0.7581`，after-cost 月均 `-1.138%`。
- 数据充分性不是失败原因: validation 和 robustness 的 primary local decision cells 均为 `18/18`，超过 gate 要求的 `15`。
- 失败的直接原因是 2024-2026 robustness 中 winner leg 继续跑赢 loser leg: robustness loser 月均 `+0.735%`，winner 月均 `+1.496%`，L-W 因此转负。
- loser long-only after-cost 在两个 OOS split 都为正: validation `+0.302%`，robustness `+0.554%`。这说明“买入过去输家”本身有正收益，但它不是论文式 L-W 反向 spread 的稳健证据。

核心判断: 本地 PIT500 主板样本中，2022-2023 有反向 spread，但 2024-2026 的稳健性断裂。不能把该结果升级为策略授权；它更适合作为“局部 regime 诊断”和“loser long-only 候选信号”的线索。

## 2. 实验边界

| 项目 | 当前设置 |
|:--|:--|
| 本地 provider | `data/qlib/cn_data_pit` |
| PIT universe | `data/universe/pit_mcap500_mainboard_daily.csv` |
| provider end | `2026-04-30` |
| 月度交易日历 | 2017-01 到 2026-04，共 `112` 个自然月端点 |
| PIT 有成员的月端点 | 2017-07 到 2026-04，共 `106` 个端点 |
| 最新 PIT 成员数 | 2026-04 月末 `296` 只 |
| 月末 PIT 成员数区间 | 首个 PIT 月末 `143`，样本内最大 `308` |
| price adjustment | `provider_ohlc_already_adjusted`，不重新套用 `factor.day.bin` |
| 主排序变量 | `close(M_t) / close(M_{t-J}) - 1` |
| PIT 成员资格 | 信号月必须是 PIT 成员；`M_{t-J}` 可以早于 PIT 入选，只要 provider price 存在 |
| 中间月价格覆盖 | 至少 `ceil(J * 0.5)` 个中间月 close 有效 |
| 主决策簇 | `J in {18,24,30,36,42,48}`，`K in {1,6,12}`，decile，no-skip |
| 成本 | buy `30` bps，sell `80` bps，round trip `110` bps |
| overlap vintage 权重 | calendar month 内对 active vintage target weights 等权平均 |

本地输入可用性:

| input | 状态 | 本地处理 |
|:--|:--|:--|
| monthly adjusted stock returns | available full | 使用 provider adjusted close 月收益 |
| exchange split | available full | 使用 SH/SZ 静态映射 |
| full all-A-share universe | blocked | 本地只能使用 PIT mcap500 mainboard |
| IPO first-month exclusion | partial proxy | PIT universe 已有 `listing_age_trading_days >= 120` |
| market state | available full | 使用 SH000300 prior return state |
| one-month skip | available full | 只做 `J=K` diagonal skip1 |

IPO/listing-age 审计显示，三个 split 都没有 `listing_age_trading_days < 120` 的 PIT 样本行:

| split | date range | row count | instrument count | min listing age | median listing age | rows < 120 |
|:--|:--|--:|--:|--:|--:|--:|
| train | 2018-07-02 到 2021-12-31 | 159,785 | 398 | 120 | 842 | 0 |
| validation | 2022-01-04 到 2023-12-29 | 109,722 | 323 | 120 | 1,419 | 0 |
| robustness | 2024-01-02 到 2025-12-31 | 110,419 | 342 | 120 | 1,913 | 0 |

## 3. Gate Replay

最终 gate 不是样本不足，也不是成本回放不可用，而是 robustness 主信号失败。

| gate | pass | value | threshold |
|:--|:--:|:--|:--|
| data inputs available | True | True | True |
| execution replay available | True | cost contract matched | calendar returns non-empty |
| validation primary cells | True | 18 | >= 15 |
| robustness primary cells | True | 18 | >= 15 |
| validation L-W mean > 0 | True | `+1.478%` | > 0 |
| validation L-W t > 0 | True | `1.6045` | > 0 |
| validation loser > winner | True | `+0.473% > -1.005%` | loser > winner |
| robustness L-W mean > 0 | False | `-0.761%` | > 0 |
| robustness L-W t > 0 | False | `-0.7581` | > 0 |
| robustness loser > winner | False | `+0.735% < +1.496%` | loser > winner |
| validation decile >= tertile | True | `+1.621% >= +1.100%` | decile >= tertile |
| robustness decile >= tertile | False | `-0.666% < -0.555%` | decile >= tertile |
| validation after-cost L-W > 0 | True | `+1.140%` | > 0 |
| robustness after-cost L-W > 0 | False | `-1.138%` | > 0 |
| validation loser long-only after-cost > 0 | True | `+0.302%` | diagnostic only |
| robustness loser long-only after-cost > 0 | True | `+0.554%` | diagnostic only |

## 4. 主决策簇总览

主决策簇按 calendar month 聚合，先在每月平均所有 primary cells，再做 split-level 统计。

| split | months | L-W mean | annualized mean | NW t | after-cost mean | loser mean | winner mean | loser long-only after-cost |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|
| train | 52 | -0.319% | -3.830% | -0.2746 | -0.652% | +0.774% | +1.093% | +0.615% |
| validation | 35 | +1.478% | +17.736% | +1.6045 | +1.140% | +0.473% | -1.005% | +0.302% |
| robustness | 28 | -0.761% | -9.130% | -0.7581 | -1.138% | +0.735% | +1.496% | +0.554% |

主簇 replay 规模:

| split | calendar rows | unique months | active vintage sum | complete vintage rows | mean buy turnover | mean sell turnover |
|:--|--:|--:|--:|--:|--:|--:|
| train | 557 | 52 | 2,869 | 2,869 | 0.302 | 0.302 |
| validation | 528 | 35 | 2,736 | 2,736 | 0.310 | 0.310 |
| robustness | 480 | 28 | 2,196 | 2,196 | 0.338 | 0.338 |

解释:

- validation 的正收益主要来自 winner leg 为负: loser 月均只有 `+0.473%`，但 winner 月均 `-1.005%`，L-W 因此扩大到 `+1.478%`。
- robustness 的 loser leg 仍为正，但 winner leg 更强: loser `+0.735%`，winner `+1.496%`，L-W 被反转为 `-0.761%`。
- 成本不是唯一解释。validation 扣成本后仍为正；robustness gross 已经为负，扣成本只是扩大亏损。
- loser long-only after-cost 连续为正，说明“过去输家池”在本地样本中可能是一个 long-only 方向线索，但不能证明论文式 L-W 反向 spread 可交易。

## 5. Primary Decile 逐 J/K 明细

### 5.1 Validation: 2022-2023 first holding vintages

| J | K | months | L-W mean | NW t | after-cost | loser | winner | loser-only after-cost |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 18 | 1 | 24 | +1.340% | +0.900 | +0.546% | -0.818% | -2.158% | -1.188% |
| 18 | 6 | 29 | -0.221% | -0.158 | -0.530% | -1.144% | -0.923% | -1.298% |
| 18 | 12 | 35 | +0.103% | +0.096 | -0.126% | -0.210% | -0.313% | -0.321% |
| 24 | 1 | 24 | +1.784% | +1.371 | +1.094% | -0.687% | -2.472% | -1.031% |
| 24 | 6 | 29 | +0.182% | +0.131 | -0.105% | -0.807% | -0.989% | -0.953% |
| 24 | 12 | 35 | +1.035% | +0.932 | +0.815% | +0.172% | -0.863% | +0.061% |
| 30 | 1 | 24 | +2.869% | +2.262 | +2.233% | +0.445% | -2.425% | +0.139% |
| 30 | 6 | 29 | +0.933% | +0.609 | +0.667% | -0.101% | -1.034% | -0.236% |
| 30 | 12 | 35 | +1.457% | +1.408 | +1.255% | +0.459% | -0.999% | +0.355% |
| 36 | 1 | 24 | +2.688% | +1.935 | +2.106% | +0.454% | -2.234% | +0.182% |
| 36 | 6 | 29 | +1.323% | +0.891 | +1.068% | +0.078% | -1.245% | -0.049% |
| 36 | 12 | 35 | +1.909% | +1.953 | +1.714% | +0.765% | -1.144% | +0.666% |
| 42 | 1 | 24 | +2.805% | +2.137 | +2.246% | +0.577% | -2.228% | +0.312% |
| 42 | 6 | 29 | +1.442% | +1.139 | +1.201% | +0.210% | -1.233% | +0.089% |
| 42 | 12 | 35 | +2.029% | +2.507 | +1.842% | +0.976% | -1.053% | +0.881% |
| 48 | 1 | 24 | +3.137% | +2.149 | +2.591% | +0.533% | -2.604% | +0.283% |
| 48 | 6 | 29 | +2.048% | +1.542 | +1.814% | +0.518% | -1.530% | +0.399% |
| 48 | 12 | 35 | +2.314% | +2.982 | +2.140% | +1.045% | -1.269% | +0.958% |

Validation insight:

- `J >= 30` 明显更强，尤其 `J=48` 三个 K 都为正，after-cost 也全部为正。
- `J=18` 和 `J=24` 的 `K=6` 表现偏弱，说明不是所有中长 horizon 都稳定。
- positive spread 很大程度来自 winner leg 下跌，而不是 loser leg 大幅上涨。这个结构对市场 regime 很敏感。

### 5.2 Robustness: 2024-2025 first holding vintages

| J | K | months | L-W mean | NW t | after-cost | loser | winner | loser-only after-cost |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 18 | 1 | 24 | -0.599% | -0.354 | -1.358% | +0.400% | +0.998% | +0.047% |
| 18 | 6 | 28 | -2.017% | -1.812 | -2.318% | +0.211% | +2.227% | +0.075% |
| 18 | 12 | 28 | -1.385% | -1.981 | -1.626% | +0.319% | +1.704% | +0.208% |
| 24 | 1 | 24 | -0.853% | -0.531 | -1.519% | +0.346% | +1.199% | +0.040% |
| 24 | 6 | 28 | -1.891% | -1.439 | -2.173% | +0.160% | +2.051% | +0.036% |
| 24 | 12 | 28 | -1.108% | -1.241 | -1.338% | +0.256% | +1.363% | +0.150% |
| 30 | 1 | 24 | -1.496% | -0.917 | -2.165% | +0.384% | +1.880% | +0.077% |
| 30 | 6 | 28 | -2.132% | -1.489 | -2.401% | +0.052% | +2.185% | -0.072% |
| 30 | 12 | 28 | -0.529% | -0.545 | -0.755% | +0.851% | +1.380% | +0.743% |
| 36 | 1 | 24 | -0.423% | -0.298 | -1.067% | +0.958% | +1.381% | +0.648% |
| 36 | 6 | 28 | -0.767% | -0.688 | -1.039% | +0.817% | +1.584% | +0.686% |
| 36 | 12 | 28 | -0.226% | -0.260 | -0.447% | +1.002% | +1.228% | +0.892% |
| 42 | 1 | 24 | +0.131% | +0.105 | -0.440% | +1.102% | +0.971% | +0.838% |
| 42 | 6 | 28 | -0.242% | -0.220 | -0.508% | +1.099% | +1.340% | +0.969% |
| 42 | 12 | 28 | +0.134% | +0.193 | -0.085% | +1.216% | +1.082% | +1.106% |
| 48 | 1 | 24 | +1.616% | +1.401 | +1.001% | +2.177% | +0.561% | +1.883% |
| 48 | 6 | 28 | -0.212% | -0.224 | -0.483% | +1.531% | +1.743% | +1.397% |
| 48 | 12 | 28 | +0.009% | +0.012 | -0.206% | +1.375% | +1.366% | +1.262% |

Robustness insight:

- 失败最集中在 `J=18/24/30`，尤其 `K=6/12`，winner leg 月均经常达到 `+1.3%` 到 `+2.2%`。
- `J=48` 在 robustness 中相对最好，`K=1` gross 和 after-cost 都为正，但 `K=6/12` 仍不能维持 after-cost 正收益。
- loser leg 在几乎所有 robustness cells 都为正，说明过去输家没有系统性崩坏；真正的问题是 winner leg 没有回落，反而延续上涨。

## 6. 分组分辨率

主决策簇按分组方式聚合:

| split | grouping | cells | L-W mean | after-cost mean | min months |
|:--|:--|--:|--:|--:|--:|
| validation | decile | 18 | +1.621% | +1.254% | 24 |
| validation | quintile | 18 | +1.375% | +1.065% | 24 |
| validation | tertile | 18 | +1.100% | +0.834% | 24 |
| robustness | decile | 18 | -0.666% | -1.051% | 24 |
| robustness | quintile | 18 | -0.597% | -0.923% | 24 |
| robustness | tertile | 18 | -0.555% | -0.840% | 24 |

逐 cell 的分辨率通过数:

| split | cells | decile >= tertile | decile >= quintile | quintile >= tertile |
|:--|--:|--:|--:|--:|
| validation | 18 | 17 | 16 | 17 |
| robustness | 18 | 9 | 6 | 9 |

解释:

- validation 中排序分辨率很符合论文方向: decile > quintile > tertile 大体成立。
- robustness 中更细分组没有增强信号。decile 平均值反而比 tertile 更差，说明 tail spread 在新样本中不是稳定放大器。
- 这也是 gate 里 `robustness_decile_mean_ge_tertile_mean = False` 的原因之一。

## 7. 成本与持仓结构

成本回放使用 combined signed stock weights:

`combined_weight_{i,h} = active_vintage_count^{-1} * sum_active signed_leg_weight_{i,s,h}`

vintage 进入和退出都会形成 turnover；最后一个 active month 也计入清仓到 0 的 terminal settlement turnover。

| split | gross L-W | after-cost L-W | cost drag | loser long-only after-cost |
|:--|--:|--:|--:|--:|
| train | -0.319% | -0.652% | -0.332% | +0.615% |
| validation | +1.478% | +1.140% | -0.338% | +0.302% |
| robustness | -0.761% | -1.138% | -0.377% | +0.554% |

成本层面的判断:

- 成本 drag 在三个 split 约 `0.33%` 到 `0.38%` 月均，量级稳定。
- validation spread 足够大，扣成本后仍为正。
- robustness gross spread 已为负，after-cost 失败不是成本导致的假阴性，而是信号方向本身在该 split 失败。
- loser long-only after-cost 连续正收益值得保留为后续研究入口，但它不是本需求的主 gate。

## 8. Skip-One-Month 诊断

skip1 只覆盖 `J=K` diagonal。它用于检查短期反转或月末微结构影响是否污染主结果。

| split | J=K | months | L-W mean | NW t | after-cost | loser | winner |
|:--|--:|--:|--:|--:|--:|--:|--:|
| validation | 1 | 24 | +1.267% | +1.022 | -0.679% | -0.782% | -2.049% |
| validation | 6 | 29 | -0.790% | -1.141 | -1.197% | -1.432% | -0.642% |
| validation | 12 | 35 | -0.356% | -0.393 | -0.607% | -0.469% | -0.113% |
| validation | 18 | 41 | +0.172% | +0.254 | -0.028% | -0.379% | -0.550% |
| validation | 24 | 47 | +1.215% | +3.054 | +1.046% | +0.806% | -0.409% |
| validation | 30 | 52 | +0.960% | +1.242 | +0.822% | +0.623% | -0.336% |
| validation | 36 | 52 | +1.521% | +1.760 | +1.408% | +0.860% | -0.661% |
| validation | 42 | 52 | +1.488% | +1.561 | +1.392% | +0.905% | -0.583% |
| validation | 48 | 52 | +1.436% | +2.066 | +1.366% | +0.671% | -0.765% |
| robustness | 1 | 24 | -0.433% | -0.409 | -2.395% | +1.208% | +1.641% |
| robustness | 6 | 28 | -1.214% | -1.223 | -1.622% | +1.038% | +2.251% |
| robustness | 12 | 28 | -1.244% | -1.630 | -1.499% | +0.679% | +1.923% |
| robustness | 18 | 28 | -1.567% | -2.469 | -1.774% | +0.448% | +2.016% |
| robustness | 24 | 28 | -0.926% | -0.958 | -1.068% | +0.834% | +1.760% |

skip1 insight:

- validation 中长 horizon `J=K>=24` 仍明显为正，说明 validation 的一部分反向效应不是纯月末短反转。
- robustness skip1 全部为负，且 `J=18` t=-2.47，强化了 robustness 失败的可信度。
- skip1 没有拯救 OOS 稳健性，反而支持“2024-2026 winner leg 延续”这一解释。

## 9. 市场状态诊断

市场状态用 SH000300 prior return 在 train split 的 33/67 分位划分。以下是主决策簇 calendar aggregation 的状态条件收益。

| split | window | state | months | L-W mean | NW t | after-cost | positive month share |
|:--|--:|:--|--:|--:|--:|--:|--:|
| validation | 12 | down | 31 | +1.384% | +1.364 | +1.071% | 51.6% |
| validation | 12 | middle | 4 | +2.210% | +1.275 | +1.673% | 75.0% |
| validation | 24 | down | 27 | +1.104% | +1.088 | +0.824% | 48.1% |
| validation | 24 | middle | 8 | +2.739% | +1.329 | +2.205% | 75.0% |
| robustness | 12 | down | 9 | -0.662% | -0.280 | -1.075% | 33.3% |
| robustness | 12 | middle | 16 | -0.680% | -0.595 | -1.058% | 43.8% |
| robustness | 12 | up | 3 | -1.489% | -2.527 | -1.754% | 0.0% |
| robustness | 24 | down | 18 | -0.901% | -0.648 | -1.251% | 27.8% |
| robustness | 24 | middle | 6 | -0.599% | -0.295 | -1.167% | 50.0% |
| robustness | 24 | up | 4 | -0.373% | -0.420 | -0.587% | 50.0% |

状态 insight:

- validation 的正收益不是只来自单一 up/down 状态，12m/24m down 和 middle 都为正。
- robustness 中三个状态都不理想。12m up 的 L-W `-1.489%` 最弱，但样本只有 3 个月，不能过度解释。
- 状态诊断更像 regime stability warning: 反向 spread 在 2024-2026 普遍失效，而不是只在某一类市场状态失效。

## 10. 交易所诊断

| split | exchange | months | L-W mean | NW t | loser | winner |
|:--|:--|--:|--:|--:|--:|--:|
| validation | SHSE | 35 | +1.256% | +1.259 | +0.629% | -0.627% |
| validation | SZSE | 35 | +1.752% | +1.830 | +0.199% | -1.553% |
| robustness | SHSE | 28 | -0.502% | -0.491 | +0.790% | +1.292% |
| robustness | SZSE | 28 | -0.838% | -0.878 | +1.091% | +1.929% |
| train | SHSE | 52 | -0.135% | -0.117 | +0.827% | +0.962% |
| train | SZSE | 40 | -0.702% | -0.543 | +1.249% | +1.951% |

交易所 insight:

- validation 中 SHSE 和 SZSE 都支持反向，SZSE 更强，主要因为 winner leg 更负。
- robustness 中 SHSE 和 SZSE 都转负，SZSE 更弱。不是单一交易所导致全局失败。
- 这降低了“交易所结构偏差”作为主解释的可能性。

## 11. 数据充分性与 provider end

Provider end 对长 K 的限制很明显，因此主决策簇只用 `K in {1,6,12}`。完整 K 标签可评估的 first holding month 数:

| split | K=1 | K=6 | K=12 | K=18 | K=24 | K=30 | K=36 | K=42 | K=48 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| validation | 24 | 24 | 24 | 24 | 24 | 23 | 17 | 11 | 5 |
| robustness | 24 | 23 | 17 | 11 | 5 | 0 | 0 | 0 | 0 |

Primary J/K signal-history 可评估性:

| split | primary cells | min evaluable first-holding months | max evaluable first-holding months | min signal eligible instruments | min intermediate close coverage |
|:--|--:|--:|--:|--:|--:|
| validation | 18 | 24 | 24 | 186 | 54.3% |
| robustness | 18 | 17 | 24 | 176 | 66.0% |

解释:

- robustness 的 primary cells 虽然可评估月数低于 validation，但仍满足每 cell 最低 `12` 个月和总 cell `>=15` 的 gate。
- 长 K 在 robustness 中不可作为主 gate，是 provider end 限制，不是策略选择。
- 对 `J=48` 的历史分母，validation 起点需要 2018 年价格，robustness 起点需要 2020 年价格；本地 provider 支持这类历史读取，但 instrument-month 缺价会被阻断。

## 12. 与论文结论的映射

| paper claim | local mapping | 本地支持情况 |
|:--|:--|:--|
| 长 horizon contrarian profits | PIT500 monthly decile L-W, `J=18..48`, `K=1/6/12` | validation 支持，robustness 不支持 |
| 更细分组增强信号 | decile >= tertile gate | validation 基本支持，robustness 不支持 |
| 扣成本后仍盈利 | 30/80 bps overlap vintage replay | validation 支持，robustness 不支持 |
| long-short 组合可交易 | A 股本地约束下仅作 diagnostic | 不授权 |
| RESSET 全 A 1997-2012 | 本地 PIT500 mainboard 2017-2026 | 结构性不等价 |

## 13. Findings

1. **这不是“成本杀死了策略”。** validation gross `+1.478%` 到 after-cost `+1.140%`，robustness gross `-0.761%` 到 after-cost `-1.138%`。成本只改变幅度，不改变 validation/robustness 的方向差异。

2. **2024-2026 的核心断裂来自 winner leg。** robustness loser 月均仍有 `+0.735%`，但 winner 月均 `+1.496%`。过去赢家没有回落，反而继续上涨，L-W 反向 spread 因此失败。

3. **`J=48` 是 robustness 中相对最好的长 horizon。** `J=48,K=1` gross `+1.616%`，after-cost `+1.001%`，但 `K=6/12` after-cost 转负。这提示最强信号可能是很长 lookback 加很短 holding，而不是论文式一整片中长 K 稳定盈利。

4. **validation 的强信号依赖 winner leg 为负。** 多数 validation 正 cell 的 winner leg 是负收益。若后续 market regime 让赢家延续，这类 L-W 结构会快速失效。

5. **loser long-only 是单独的候选方向。** 两个 OOS split 的 loser long-only after-cost 都为正，这和 L-W 失败并不矛盾。它说明“过去输家池”可能有均值回复或风险补偿，但 short winner leg 在 robustness 中是拖累。

6. **分组分辨率不能作为稳健证据。** validation 中 decile 相对 tertile 基本成立；robustness 只有 9/18 个 primary cells 满足 decile >= tertile，说明更细 tail sort 在新样本中没有稳定放大反向收益。

7. **市场状态和交易所都不是单一解释。** robustness 在 SHSE/SZSE 都为负，按 12m/24m 市场状态分组也普遍为负。因此失败更像样本 regime 或 universe 结构变化，而不是某个状态桶或交易所局部污染。

## 14. Research Insight

本地结果更接近下面这个解释链:

1. PIT500 mainboard 是更成熟、更大市值、更高流动性的股票池，不等价于论文全 A 股 1997-2012 样本。
2. validation 2022-2023 中，过去赢家出现明显回落，形成正的 contrarian spread。
3. robustness 2024-2026 中，过去赢家延续上涨，尤其在 `J=18/24/30` 的 `K=6/12` 上非常明显，导致 L-W 反向组合失败。
4. 过去输家并没有整体失败，甚至 long-only after-cost 为正；问题在于 short winner leg 的方向和 A 股可交易性。
5. 因此，本需求不应继续围绕“论文式 long-short contrarian 直接可复现”推进。更合理的后续方向是拆开腿部:
   - loser long-only 是否能在风险、行业、市值、流动性控制后保留正收益；
   - winner leg 是否在特定市场状态下才应被 short 或回避；
   - `J=48,K=1` 这类长 lookback 短 holding 是否只是偶然样本，还是可被独立稳健性检验支持。

## 15. 结论动作

当前 requirement 的 gate 应保持失败状态: `validation_only_not_robust`。不要把它提升为策略需求。

可承接但必须重新定义目标的方向:

- long-only loser reversal diagnostic: 以 loser leg after-cost 为主目标，不再用 L-W spread 作为主 gate。
- long-horizon short-holding probe: 聚焦 `J=42/48, K=1`，但需要更严格的多 split 或 rolling OOS。
- winner continuation guard: 研究 winner leg 什么时候从“可 short 的反向腿”变成“应回避的强 momentum 腿”。

本报告只解释当前 artifact，不改变代码、配置、requirement 或 gate 定义。
