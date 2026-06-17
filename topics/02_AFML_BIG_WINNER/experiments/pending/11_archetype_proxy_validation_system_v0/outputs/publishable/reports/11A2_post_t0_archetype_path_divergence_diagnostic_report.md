# 11A2 t0 后 archetype 路径分离诊断报告

## 1. 结论摘要

本轮 11A2 的最终状态为：

`11A2_post_t0_archetype_path_divergence_separation_detected_tradable`

核心读数是：在 `risk_on ∩ strict PIT-valid` 的 4,665 条 evaluated rows 中，C1 主对比（`class_big_winner` vs `class_big_failure_proxy_nonwinner`）在 full-cohort 口径下形成了双通道 Tier3 confirmed onset，确认窗口为 `K*=3` 个交易日。tradability lag 显示，winner 组在 K=3 时的 `ep_mfe_to_Kstar / mfe_120_recomputed` 中位数为 `4.331%`，明显低于 50% ceiling，因此该分离不是在大部分后续有利波动已经兑现后才出现。

更直接地说：11A1 显示 t0 当天 winner 与 failure proxy 纠缠；11A2 的当前数据表明，这种纠缠在 t0 后第 3 个交易日已经出现可观测解耦。这个结论只说明 “post-t0 early-path divergence 存在且出现得足够早”，不等于策略有效，也不授权 routing / 建仓 / 平仓 / 替代 10C。

## 2. 样本、scope 与数据完整性

与 11A1 的 denominator 对账完全一致：

| split | 11A2 pre-PIT rows | 11A1 pre-PIT rows | 11A2 PIT-valid rows | 11A1 PIT-valid rows | drift | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| all | 11,293 | 11,293 | 4,665 | 4,665 | 0.0000% | ok |
| train | 5,836 | 5,836 | 1,708 | 1,708 | 0.0000% | ok |
| validation | 1,898 | 1,898 | 865 | 865 | 0.0000% | ok |
| robustness | 3,559 | 3,559 | 2,092 | 2,092 | 0.0000% | ok |

价格锚点对账也通过：`event_window_anchor_date` 的 anchor date match rate 在 all/train/validation/robustness 四个 split 均为 `100.00%`，`anchor_status=ok`。full-cohort 在所有 K 上 eligible rate 都是 `100.00%`，没有 filename-derived fallback rows。

这意味着本轮结论不是由 denominator drift、价格锚点错位、qfq 覆盖不足或 post-t0 路径缺失造成的。

## 3. outcome class 分布

全样本分布如下：

| class | rows | instruments | rate |
| --- | ---: | ---: | ---: |
| `class_big_winner` | 446 | 187 | 9.56% |
| `class_big_failure_proxy_nonwinner` | 1,533 | 515 | 32.86% |
| `class_neutral_chop` | 2,684 | 453 | 57.53% |
| `subclass_fast_fail` | 436 | 296 | 9.35% |
| `subclass_false_repair_only` | 1,097 | 461 | 23.52% |
| `class_unresolved` | 2 | 2 | 0.04% |

split 级别上，train 和 robustness 的 C1 两侧样本满足 power guard：

| split | winner rows | C1 negative rows | winner instruments | negative instruments | status |
| --- | ---: | ---: | ---: | ---: | --- |
| train | 151 | 626 | 64 | 277 | ok |
| robustness | 279 | 625 | 134 | 348 | ok |
| validation | 16 | 282 | 11 | 196 | contrast_underpowered |

validation 的 winner 样本只有 16 条、11 个 instrument，因此它只能作为 readout，不能作为推翻 train/robustness confirmed onset 的主证据。

## 4. C1 主对比：t0 后第 3 个交易日出现双通道解耦

C1 的 primary channels 是：

- return channel: `ep_ret_t0_to_K`
- structure channel: `ep_max_drawdown_to_K`

full-cohort C1 的关键读数如下：

| channel | split | K | winner n | negative n | Cliff's delta | CI low | CI high | direction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| return | train | 1 | 151 | 626 | 0.2360 | 0.0810 | 0.3910 | winner_higher |
| return | robustness | 1 | 279 | 625 | 0.2294 | 0.1152 | 0.3436 | winner_higher |
| return | train | 3 | 151 | 626 | 0.3768 | 0.2291 | 0.5246 | winner_higher |
| return | robustness | 3 | 279 | 625 | 0.3310 | 0.2203 | 0.4418 | winner_higher |
| structure | train | 1 | 151 | 626 | 0.1730 | 0.0159 | 0.3301 | winner_higher |
| structure | robustness | 1 | 279 | 625 | 0.1231 | 0.0067 | 0.2396 | winner_higher |
| structure | train | 3 | 151 | 626 | 0.2889 | 0.1362 | 0.4416 | winner_higher |
| structure | robustness | 3 | 279 | 625 | 0.1928 | 0.0776 | 0.3079 | winner_higher |

解释：

- return channel 在 K=1 已经通过 train/robustness confirmed。
- structure channel 在 K=1 的方向为 winner_higher，但 CI 尚未越过 null band；到 K=3 时 train 与 robustness 同向且均越过阈值。
- 因此 dual-channel confirmed onset 被定为 K=3，而不是 K=1。

这个 timing 很重要：winner 与 failure proxy 并不是只能在 10 日或 20 日后才分开；在严格 PIT、full-cohort、双通道要求下，K=3 已经出现稳定解耦。

## 5. 各 contrast 的 onset 结构

| contrast | full-cohort confirmed onset | return Tier3 | structure Tier3 | 解释 |
| --- | ---: | ---: | ---: | --- |
| C1 winner vs big failure proxy | 3 | 1 | 3 | 主结论，双通道成立 |
| C2 winner vs false repair only | 3 | 3 | 3 | false-repair 子类同样可在 K=3 分离 |
| C3 winner vs fast fail | 5 | 3 | 5 | fast-fail 子类结构通道更晚，到 K=5 才确认 |
| C4 winner vs neutral | none | none | 10 | return 与 structure 方向不构成双通道确认 |
| C5 winner vs all nonwinner | none | 10 | none | all-nonwinner 聚合后 structure channel 不稳定 |

我的判断是：C1/C2/C3 的存在说明 “失败 proxy 内部” 确实存在 post-t0 path divergence；但 C4/C5 的失败也说明这不是一个简单的 winner vs everything 线性排序。尤其 C5 把 failure proxy 与 neutral chop 混在一起后，return channel 仍可分离，但 structure channel 塌缩，这提示后续 11C 不应把所有 nonwinner 当成一个同质负类。

## 6. 双通道不是独立证据，而是强相关的 corroboration

C1 full-cohort 在 K=3 的两个通道方向组合为：

`return_direction_at_confirmed = winner_higher`

`structure_direction_at_confirmed = winner_higher`

同时：

- `channel_rank_corr = 0.7742`
- `channel_direction_agreement_rate = 1.0000`
- `dual_channel_collinearity_flag = dual_channel_collinear_readout`

这表示 return path 与 drawdown path 在本数据中高度同向。它们不是两份完全独立证据，更接近 “两个相关视角确认同一个价格路径事实”：winner 在 t0 后更早上涨、同时更少向下破坏路径。

这不阻断 final status，但应该影响后续设计：11C 如果继续做 two-stage policy，不应把 return 与 drawdown 当成独立 alpha source 相加，而应把它们视作一个早期路径质量维度的两个投影。

## 7. tradability lag：K=3 时并未兑现大部分后续路径

C1 full-cohort confirmed K* 为 3。tradability lag 表显示：

| item | value |
| --- | ---: |
| confirmed K* | 3 |
| tradability basis eligible winners | 414 |
| tradability basis excluded winners | 32 |
| median `ep_mfe_to_Kstar / mfe_120_recomputed` | 0.04331 |
| median `ep_ret_to_Kstar / forward_return_120d` | 0.002248 |
| status | tradable_window_open |

解读：

- K=3 时 winner 组只实现了其 120 日可重算最大有利波动的约 `4.33%`。
- 这说明分离不是发生在行情已经大部分走完之后。
- 但 K=3 的 median realized return fraction 只有 `0.2248%`，也意味着 K=3 的用途更像 “二阶段确认窗口”，不是已经能单独说明交易收益的窗口。

因此，11A2 支持进入 11C 验证 “t0 小仓试探 -> t0+3 再决策” 这类结构，但不提供带成本、容量、滑点和组合约束后的策略 EV。

## 8. bootstrap 稳定性

C1 instrument-block bootstrap：

| metric | value |
| --- | ---: |
| bootstrap_n | 1,000 |
| confirmed onset hit rate | 1.000 |
| onset p25 / median / p75 | 3 / 3 / 5 |
| onset distribution | K1=53, K3=597, K5=289, K10=61 |
| tier2 onset hit rate | 1.000 |
| return channel Tier3 hit rate | 1.000 |
| structure channel Tier3 hit rate | 1.000 |
| point-vs-bootstrap median drift | 0 |
| bootstrap stable | true |

C1 event-block sensitivity：

| metric | value |
| --- | ---: |
| secondary event-block bootstrap_n | 200 |
| confirmed onset hit rate | 1.000 |
| median onset day | 3 |
| episode_block_onset_conflict | false |

关键 channel metric bootstrap 读数：

| channel/split/K | median Cliff's delta | p05 | p95 | P(direction and > null band) |
| --- | ---: | ---: | ---: | ---: |
| return / train / K1 | 0.2349 | 0.1381 | 0.3164 | 1.000 |
| return / robustness / K1 | 0.2271 | 0.1546 | 0.3097 | 0.998 |
| structure / train / K3 | 0.2857 | 0.1906 | 0.3800 | 1.000 |
| structure / robustness / K3 | 0.1912 | 0.1160 | 0.2709 | 0.999 |

这组 bootstrap 结果非常关键：K=3 不是单次切分下的偶然点估计，而是在 instrument-block 与 event-block 两种重采样下都稳定落在 K=3 附近。

## 9. multiple-comparison audit

多重比较审计使用 `split + event_year_quarter + source_family_id` cell 内的 stratified label permutation，并用 cached weighted Cliff's delta 重算 null 分布。

| item | value |
| --- | ---: |
| total tested cells | 2,160 |
| actual significant cells | 1,009 |
| null_simulation_n | 500 |
| null expected significant cells | 22.356 |
| null significant cells p95 | 66.15 |
| actual exceeds null p95 | true |
| status | actual_exceeds_null_p95 |

这说明当前观测到的路径分离不是简单由 feature × K × contrast 的多重扫描造成的。实际显著 cell 数远高于置换标签下的 p95。不过，这也说明路径特征在本样本中存在大面积结构差异，后续 11C 需要防止把许多高度相关的 path features 当成独立证据重复计数。

## 10. survivorship 与 delist haircut

survivorship audit 输出 480 rows，其中：

| delist_haircut | survivorship_flag | conflict flag | rows |
| ---: | --- | --- | ---: |
| 1.0 | none | false | 240 |
| 0.0 | none | false | 240 |

同时 full-cohort fill audit 显示本轮所有 split/K 的 primary fill reason 都是 `complete_path`。这意味着：

- 当前 denominator 下没有由退市、停牌或 qfq 路径缺失导致的 full-cohort dropout。
- `delist_haircut=1.0` 与 `0.0` 两端点没有推翻结论。
- 该分离不是 survivorship-only 结果。

这个结论比只看 survivors-only 更强，因为 final status 是由 full-cohort confirmed K* 决定的。

## 11. EP8B label-overlap audit

fast-fail barrier touch 只进入 label-overlap audit，不进入 primary onset / tradability / final status。

全样本 label-overlap 读数：

| K | fast_fail positives | touch by K | overlap | touch_given_fast_fail |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 466 | 4 | 4 | 0.86% |
| 3 | 466 | 63 | 63 | 13.52% |
| 5 | 466 | 164 | 164 | 35.19% |
| 10 | 466 | 466 | 466 | 100.00% |
| 15 | 466 | 466 | 466 | 100.00% |
| 20 | 466 | 466 | 466 | 100.00% |

洞察：

- 到 K=10，EP8B touch 已经与 fast-fail 标签完全重合，因此任何把该 touch 当成 primary path feature 的做法都会引入 label tautology。
- 本轮 primary C1 onset 是 K=3，且 EP8B 被排除在 primary curve 之外；因此 C1 K=3 结论不是由 fast-fail label touch 直接构造出来的。
- 但 C3 winner vs fast_fail 的 confirmed onset 在 K=5，且 K=5 时已有 35.19% fast-fail touch overlap，因此后续解释 fast-fail 子类时要特别谨慎：越靠后的 fast-fail 分离越容易和 label 定义重叠。

## 12. MFE basis 与 touch coordinate 质量

MFE basis 对账：

| basis_status | rows |
| --- | ---: |
| ok | 4,559 |
| mfe_basis_mismatch | 106 |

tradability status 中 winner 组有 414 条进入 basis eligible，32 条被排除。被排除样本没有进入 tradability lag status 的判定，因此 `tradable_window_open` 没有直接依赖 basis mismatch rows。

fast-fail touch coordinate policy：

| coordinate_status | rows |
| --- | ---: |
| ok | 27,990 |

没有 touch 坐标不可解析导致的 statistics_incomplete ceiling。

## 13. multivariate secondary readout

C1 full-cohort 的 multivariate grouped cross-fit AUC 随 K 增强：

| split | K1 | K3 | K5 | K10 | K15 | K20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 0.631 | 0.698 | 0.749 | 0.824 | 0.867 | 0.884 |
| train | 0.591 | 0.694 | 0.752 | 0.827 | 0.865 | 0.902 |
| robustness | 0.634 | 0.720 | 0.754 | 0.819 | 0.846 | 0.854 |
| validation | 0.651 | 0.559 | 0.707 | 0.881 | 0.958 | 0.982 |

这个 secondary readout 与主结论方向一致：路径信息随 K 增强。但 validation 的 winner 样本极少，所以 validation AUC 的高值不能被当作强验证证据。真正可靠的是 train 与 robustness 在 K=3 后同步增强。

## 14. 主要发现

1. C1 主对比在 t0 后第 3 个交易日形成双通道稳定分离。return channel 更早，K=1 已确认；structure channel 到 K=3 确认，因此 dual-channel onset 是 K=3。

2. 分离方向一致：winner 在早期 return path 上更强，同时 drawdown path 更少受损。两个 channel 的方向一致率为 1.0，但秩相关 0.7742，说明它们是相关证据，不是独立证据。

3. 该分离不是 survivorship 造成的。full-cohort 与 survivors-only 没有分离方向冲突，`delist_haircut=1.0/0.0` 两端点均无 conflict。

4. 该分离不是 late readout。K=3 时 winner 组只实现了后续可重算最大有利波动中位数的 4.331%，因此不是 “行情走完后才看出来”。

5. C2 与 C3 支持 failure-proxy 内部存在路径差异，但 timing 不同：false-repair-only 在 K=3 分离，fast-fail 到 K=5 才形成双通道确认。

6. C4 与 C5 的失败提醒我们，不能把所有 nonwinner 混成一个负类。neutral chop 与 failure proxy 的路径行为不同；all-nonwinner 聚合会稀释 structure channel。

7. multiple-comparison null audit 显示观测分离显著超过标签置换下的随机结构，但也暴露出 path features 之间高度相关，后续模型不能简单堆叠这些读数。

## 15. 研究洞察与后续含义

11A2 的最重要洞察不是 “某个 t0 特征更强”，而是 post-t0 的 3 个交易日路径已经把 11A1 中纠缠在一起的 winner 与 failure proxy 部分解开。这个解耦有明确的时间顺序：return channel 先出现，structure channel 随后确认。换句话说，winner 并不是单纯 “跌得少”，也不是单纯 “涨得多”；在 K=3 时，它们开始同时表现为更好的早期收益路径和更少的下行路径破坏。

这对 11C 的启发是：如果继续推进 two-stage policy，应该围绕 `K*=3` 做验证，而不是任意选择 K=5/10/20。一个自然候选结构是：t0 只保留小规模 readout 或轻仓试探，在 t0+3 用 early-path state 重新分层。但这仍然只是待验证结构，11C 必须单独计算交易成本、滑点、可成交性、组合容量、资金占用与 false-positive 代价。

需要特别强调的是，`dual_channel_collinear_readout` 使这组证据更像 “路径质量的一致确认”，而不是两个独立 alpha 的加法。后续如果把 return、drawdown、recovery、EMA reclaim、volume structure 等特征一起进模型，必须控制同源路径信息的重复计数，否则会高估分离的有效自由度。

## 16. 边界声明

11A2 是 diagnostic-only readout：

- 不授权 routing。
- 不授权建仓或平仓。
- 不替代 10C。
- 不声明策略 EV。
- 只回答：t0 后路径是否、以及多早，把 11A1 中纠缠的 winner 与 failure proxy 解耦。

## 17. 验证命令

本报告基于当前已生成 CSV / manifest，不重新运行代码生成器。最近一次完整验证记录为：

- `python -m pytest experiments/pending/11_archetype_proxy_validation_system_v0/tests/test_post_t0_archetype_path_divergence_diagnostic.py -q`
- `python -m pytest experiments/pending/11_archetype_proxy_validation_system_v0/tests -q`
- `python experiments/pending/11_archetype_proxy_validation_system_v0/src/run_11a2_post_t0_archetype_path_divergence_diagnostic.py --config experiments/pending/11_archetype_proxy_validation_system_v0/configs/config_11a2_post_t0_archetype_path_divergence_diagnostic.yaml`

本次仅更新中文报告叙事与 manifest 中对应 report hash，不更新代码。
