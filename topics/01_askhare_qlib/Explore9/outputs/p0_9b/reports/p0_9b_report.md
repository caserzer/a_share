# Explore9 P0.9B 行业 LGBM 到手工 Primitive 转写 Probe 报告

生成口径：本报告只解释 `Explore9/outputs/p0_9b/reports/` 下已经生成的 P0.9B 结构化证据，不引入新的模型选择、参数选择、score bucket 或交易规则。P0.9B 仍然是 diagnostic-only 阶段。

## 1. 核心结论

本轮结论是：**停止，不进入 P0.9C primitive 候选**。

正式 recommendation enum 为 `stop_due_to_null_or_placebo_collapse`。8 个预注册 manual primitive candidate 中，允许进入 P0.9C 的数量为 0；`p0_9b_primitive_to_p0_9c_requirement_map.csv` 为空表。这不是因为样本权重 cap 或 cache/manifest 失败，而是因为“LGBM 诊断信号”无法稳定、去伪、低集中度地转写成可手工执行的 primitive。

最重要的发现有三点：

1. 汽车 launch 模型有最像信号的一组诊断读数，但转写后的三个 launch primitive 全部变成零支持、one-fold-only/one-slice-only、null 下坍缩，说明当前预注册 token rule 太窄，或者 LGBM 学到的不是可直接手工公式化的局部条件。
2. 汽车 failure 的两个 warning primitive 有 4 个 core fold 支持，但 null/placebo 明显压不过，且 instrument/year 集中度过高；它们更像少数股票年份贡献出来的可解释故事，不够资格升级为规则。
3. 电子 launch/failure 不构成正向证据。launch 聚合 AUC 低于随机，failure 只是 weak-signal placebo stress 的负控材料；电子 failure 的 negative-control primitive 被正确拦截为 `placebo_only`。

我的判断：**当前 P0.9B 已经完成了它该完成的工作：证明“行业 T1 LGBM 的若干树路径可以被解释，但不能被安全地翻译成 P0.9C primitive”。下一步不应放松 gate 来挤出候选，而应回到 primitive seed 的定义层，重新预注册更宽或更接近模型路径的可观察 token，再作为新一版 P0.9B 重跑。**

## 2. 执行范围与硬边界

本轮只覆盖主行业 `汽车` / `电子`，任务为：

| 行业 | task | core fold 可训练性 |
|---|---|---:|
| 汽车 | launch winner | 3/4，`fold_2020` no-fit |
| 汽车 | failure reject | 4/4 |
| 电子 | launch winner | 3/4，`fold_2020` no-fit |
| 电子 | failure reject | 4/4 |

`fold_2024` 只作为 robustness appendix evidence，不允许给 primitive support count 做贡献。`电力设备` 未进入主结论，只保留 appendix-only 边界。

禁止结论保持有效：

- 无 selected model。
- 无 selected score bucket。
- 无 P1 refine 推荐。
- 无 Explore10 backtest 推荐。
- 无 freeze strategy。
- 无 actionable trade rule。

## 3. Artifact 与 guardrail 状态

`p0_9b_run_manifest.json` 记录了 29 个 required report artifact、2 个 required cache artifact；required report 缺失数为 0。cache 只在 `Explore9/outputs/p0_9b/cache/` 下保存 row/model panel，并且 `git_check_ignore_pass=True`、`tracked_by_git=False`。

两个 cache 文件：

| cache | rows | cols | size |
|---|---:|---:|---:|
| locked T1 train/eval panel | 54,029 | 240 | 4,173,694 bytes |
| locked T1 prediction panel | 12,354 | 244 | 1,951,614 bytes |

样本权重 guardrail 是本轮可以解释但不能升级的前提之一。20 个 fold-scope row 中：

| scope | rows | cap pass | signal interpretation | primitive output | max top IY share | max HHI |
|---|---:|---|---|---|---:|---:|
| main scope | 16 | pass | allowed | allowed | 0.057139 | 0.043264 |
| robustness appendix | 4 | pass | blocked | blocked | 0.036845 | 0.018860 |

主范围 cap 是 `cap_recomputed_pass`，且没有 formal waiver。也就是说，P0.9B 的停止不是因为 sample-weight guardrail 阻断，而是在 primitive translation 的后续 gate 上被阻断。

## 4. Anti-Leakage 与审计口径

需要区分两个口径：

1. 决策/特征口径：`observed_reference_decision_feature_overlap_eligible_count=0`，所有行业任务均无 eligible decision-feature overlap。这支持“模型诊断没有明显用到同日或未来可执行信息”的解释。
2. label measurement 口径：部分 core OOF 行存在 `observed_reference_label_measurement_overlap_core_oof_count`，因此对应 row 的 `observed_reference_overlap_audit_pass=False`。

label measurement overlap 的聚合如下：

| 行业 | task | decision-feature overlap | label measurement overlap | failed audit rows |
|---|---|---:|---:|---:|
| 汽车 | failure reject | 0 | 186 | 4 |
| 汽车 | launch winner | 0 | 0 | 0 |
| 电子 | failure reject | 0 | 735 | 4 |
| 电子 | launch winner | 0 | 152 | 4 |

这个结果不应被误读为 feature leakage。它更准确的含义是：标签测量窗口与 observed-reference 口径仍有重叠标记，尤其在 failure 与电子 launch 上会削弱“机制解释可升级”的可信度。由于本轮没有任何 primitive 被允许进入 P0.9C，这个 caveat 没有造成错误升级；但如果未来想要 promotion，这一项必须被收紧。

其他纪律项：

- `feature_asof_leakage_audit`：20/20 无 feature as-of violation。
- `walk_forward_purge_audit`：20/20 purge pass。
- `metric_nonselection_audit`：没有用 metric 排名选择 contract、参数、feature、bucket、行业或 task；primitive eligibility 只按预注册 pass/fail gate。
- forbidden recommendation self-check：11/11 pass。

## 5. Locked T1 模型诊断读数

核心 OOF 指标如下：

| 行业 | task | OOF events | positive | base rate | AUC | logloss | Brier | calibration slope | pred std | rank corr | core folds |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 汽车 | failure reject | 2,750 | 1,084 | 0.3942 | 0.5743 | 0.6849 | 0.2452 | 0.0793 | 0.1573 | 0.1258 | 4/4 |
| 汽车 | launch winner | 701 | 114 | 0.1626 | 0.7216 | 0.4276 | 0.1409 | 0.0815 | 0.2042 | 0.2832 | 3/4，缺 `fold_2020` |
| 电子 | failure reject | 4,586 | 2,359 | 0.5144 | 0.5132 | 0.9091 | 0.3318 | 0.0120 | 0.1892 | 0.0229 | 4/4 |
| 电子 | launch winner | 1,212 | 94 | 0.0776 | 0.4752 | 0.6003 | 0.2101 | -0.0047 | 0.2197 | -0.0230 | 3/4，缺 `fold_2020` |

分 fold 看，汽车 launch 是唯一有明显诊断价值的模型：

- 汽车 launch：`fold_2021` AUC 0.6726，`fold_2022` 0.6863，`fold_2023` 0.8454；但 `fold_2024` robustness 只有 0.3772，不能作为 primitive support。
- 汽车 failure：core fold AUC 从 0.4766 到 0.7113 摆动，聚合 0.5743 只是弱信号；`fold_2024` 0.4475。
- 电子 launch：`fold_2021` AUC 0.2836，`fold_2022` 0.5665，`fold_2023` 0.7101，聚合低于随机；这更像 regime/fold 方向不稳定，而不是可转写规则。
- 电子 failure：聚合 0.5132，fold 内也没有稳定方向，是弱信号负控更合适。

我的解读：**P0.9B 不应该用 AUC 最高的汽车 launch 直接找规则。AUC 只说明 locked T1 在某些 fold 有排序能力，不说明预注册 primitive mask 能抓住同一批 OOF 事件。报告中所有后续 primitive gate 都在验证这个差异，结果是否定的。**

## 6. Feature-family 与树路径解释

按 family gain share 聚合，四个 contract 的前四位如下：

| 行业 | task | rank 1 | rank 2 | rank 3 | rank 4 |
|---|---|---|---|---|---|
| 汽车 | failure reject | repair_quality 0.4042 | stock_rank 0.1443 | industry_relative_strength 0.1218 | volatility_expansion 0.1217 |
| 汽车 | launch winner | repair_quality 0.4398 | volatility_expansion 0.1802 | industry_breadth 0.1281 | stock_rank 0.1008 |
| 电子 | failure reject | repair_quality 0.3204 | market_regime 0.2161 | volatility_expansion 0.1867 | industry_relative_strength 0.1010 |
| 电子 | launch winner | repair_quality 0.3646 | volatility_expansion 0.2591 | industry_breadth 0.1197 | stock_rank 0.1084 |

这里有一个明显模式：`repair_quality` 在四个 contract 中都是第一 family，且汽车 launch/failure 的 dropout 后 metric delta 分别为 -0.1022 / -0.0613，是最重要的解释来源。树路径中也频繁出现 `atr20_pct`、`prelaunch_drawdown_120d`、`industry_breadth_20d`、`ret_rank_20d_market`、`launch_gain_from_recent_low_60d/120d` 的组合。

这带来两个相反含义：

- 正向含义：LGBM 不是完全黑箱噪声；它反复使用“修复质量、波动扩张、行业宽度、行业内 rank、前期回撤/低位反弹”这些可观察 family。
- 负向含义：dominant family 太集中在 repair/price-path 上，容易形成“事后能讲通”的路径解释；转成手工 primitive 时，一旦要求 fold 支持、null 超额、低集中度，就暴露出支持不足或集中度过高。

所以 feature-family 证据只能支持“这些方向值得重新设计 seed”，不能支持“已有 primitive 可以执行”。

## 7. Manual Primitive 候选结果

8 个候选全部被拒绝：

| primitive | 行业/task | support folds | null status | stability | concentration | 结论 |
|---|---|---:|---|---|---|---|
| auto_industry_relative_strength_repair | 汽车 launch | 0 | collapsed_under_null | one_fold_only | uninterpretable | 拒绝 |
| auto_volatility_expansion_not_destructive | 汽车 launch | 0 | collapsed_under_null | one_fold_only | uninterpretable | 拒绝 |
| auto_industry_breadth_support | 汽车 launch | 0 | collapsed_under_null | one_fold_only | uninterpretable | 拒绝 |
| auto_destructive_high_vol_rank_evaporation | 汽车 failure | 4 | collapsed_under_null | pass | fail_top1 | 拒绝 |
| auto_industry_breadth_failure | 汽车 failure | 4 | collapsed_under_null | pass | fail_top1 | 拒绝 |
| electronics_breadth_rank_persistence | 电子 launch | 0 | collapsed_under_null | one_fold_only | uninterpretable | 拒绝 |
| electronics_non_late_acceleration_strength | 电子 launch | 0 | collapsed_under_null | one_fold_only | uninterpretable | 拒绝 |
| electronics_failure_null_stress | 电子 failure | 4 | placebo_only | pass | fail_top1 | 拒绝 |

关键不是“没有任何模型信号”，而是“信号没有以预注册 primitive 的形式稳定出现”。汽车 launch 的三个 primitive 支持数为 0，这是最值得回头看的失败：模型诊断较强，但 token mask 没有覆盖到有效 OOF 事件。汽车 failure 的两个 primitive 支持数为 4，但被 null 与 concentration 拦住，说明它们不能只靠稳定性通过。

## 8. Null / Placebo 是本轮 stop 的主因

null/placebo 共 40 行，每个 primitive 至少 300 次 repeat，failure/negative-control 为 400 次 repeat。

launch primitive 的 real metric 全为 0，null p95 也为 0，empirical p=1.0。这不是“安全通过”，而是没有可解释支持，属于 collapsed/uninterpretable。

failure primitive 的 real metric 有数值，但不够强：

| primitive | real metric | null p95 范围 | empirical p 范围 | 解释 |
|---|---:|---:|---:|---|
| auto_destructive_high_vol_rank_evaporation | 0.6437 | 1.7236-2.1376 | 0.7125-0.7600 | 真实效果低于 null 95%，无法证明不是随机/重排产物 |
| auto_industry_breadth_failure | 0.8700 | 1.6087-1.6718 | 0.5250-0.6150 | 同样压不过 null |
| electronics_failure_null_stress | 1.3061 | 1.3627-1.8829 | 0.0800-0.1450 | 有一点表面强度，但任务本身是 negative-control，最终为 placebo_only |

我的判断：**null 结果比 raw lift 更有解释权。只看 real metric 会倾向于保留汽车 failure 和电子 failure；但放到 label permutation、instrument-year shuffle、year shuffle、dropout placebo、weak-signal placebo 后，它们都不够干净。**

## 9. Stability 与集中度

stability 单独看会误导。两个汽车 failure primitive 与一个电子 failure negative-control 都有 4 个 core fold 支持，且支持年数/切片数足够。但 instrument/year concentration 直接否决：

| primitive | top1 instrument | top5 instruments | top instrument-year | IY HHI | concentration |
|---|---:|---:|---:|---:|---|
| auto_destructive_high_vol_rank_evaporation | 0.4092 | 0.7550 | 0.3498 | 0.1494 | fail_top1 |
| auto_industry_breadth_failure | 0.3772 | 0.8221 | 0.3290 | 0.1414 | fail_top1 |
| electronics_failure_null_stress | 0.2217 | 0.5743 | 0.1667 | 0.0572 | fail_top1 |

这说明 failure primitives 的“稳定”很可能不是广泛横截面机制，而是少数 instrument 或 instrument-year 贡献过多。对于手工规则来说，这个问题很严重：规则一旦落地，会暴露在新的股票年份组合上，不能依赖少数历史贡献点。

## 10. Failure 专项与 false reject

failure primitive 还需要检查是否会误杀真正的 launch winner。聚合 false-reject 结果如下：

| primitive | events | launch 50/120 false reject | launch 100/240 false reject | baseline false reject | penalty | caution pass rows |
|---|---:|---:|---:|---:|---:|---:|
| auto_destructive_high_vol_rank_evaporation | 111 | 0.3337 | 0.1703 | 0.2288 | 0.1215 | 1/4 |
| auto_industry_breadth_failure | 112 | 0.1679 | 0.1412 | 0.2288 | 0.0003 | 4/4 |
| electronics_failure_null_stress | 196 | 0.1876 | 0.0856 | 0.1712 | 0.0652 | 2/4 |

`auto_industry_breadth_failure` 的 false-reject penalty 很低，这是它最有价值的一点；但它仍然被 null 和 concentration 阻断。`auto_destructive_high_vol_rank_evaporation` 的误杀压力更明显，只有 1/4 caution rows pass，更不适合作为下一阶段候选。

## 11. 研究判断与下一步建议

本轮最有信息量的不是“8 个都失败”，而是失败形态很清楚：

1. **汽车 launch 是最值得继续研究的方向，但不是当前 primitive。** Locked T1 的 OOF AUC/rank correlation 明显高于其他任务，树路径也有可解释 family；问题在于当前三条 launch seed 没有产生 core OOF 支持。下一版应先检查 token mask 覆盖率、分位桶边界和事件 denominator，而不是直接调模型或放松 gate。
2. **汽车 failure 可作为风险语言素材，但不能直接变成 reject rule。** 它有支持 fold 和较低 false-reject 的局部证据，尤其 `auto_industry_breadth_failure`，但 null 不过、集中度不过，说明现在还只是“故事候选”，不是规则候选。
3. **电子方向应暂时降级。** launch 聚合方向不稳，failure 近似负控。继续在电子上做 primitive 转写，优先级低于重做汽车 launch seed。
4. **不要把 feature importance 当作 primitive 选择器。** repair_quality 统治四个 contract，说明模型会抓住价格路径；但价格路径容易和标签结构、样本窗口、个股年份集中度混在一起。P0.9B 的 gate 正是在防止这种“解释看起来合理，但 out-of-fold/null 不稳”的升级。
5. **label measurement overlap 是未来 promotion 的硬问题。** 当前没有候选升级，所以它没有造成实际污染；但若未来想把 failure 或电子 launch 变成候选，必须先把 observed-reference label measurement overlap 的残留行处理干净。

建议的下一步不是进入 P0.9C，而是启动一个新的预注册修订：

- 只围绕汽车 launch 重做 primitive seed，不扩大到所有行业任务。
- 先做 token coverage audit：每个候选 primitive 在 trainable core OOF 中必须有足够 denominator 和 event support，再谈 lift。
- seed 应从树路径的共同结构出发，例如 `repair_quality + prelaunch_drawdown/low-recovery + industry_breadth + rank persistence/ATR`，但必须在 config/requirement 中预注册，不能从 validation 里临时挑公式。
- failure 方向只保留为 appendix diagnostic，除非 null 与 concentration 同时改善。

## 12. 最终状态

最终状态：

- recommendation：`stop_due_to_null_or_placebo_collapse`
- primitive candidates：8
- P0.9C allowed primitives：0
- P0.9C requirement map：0 rows
- main-scope sample-weight guardrail：pass，`cap_recomputed_pass`
- robustness `fold_2024`：appendix only，不参与 support
- metric nonselection：pass
- forbidden recommendation self-check：pass
- cache tracking：pass，cache ignored and untracked

本报告的研究结论是：**行业 LGBM 可以提供 diagnostic clues，但本轮证据不足以翻译成手工 primitive。当前最正确的动作是停止升级，并把后续工作限定为新的汽车 launch seed 预注册与覆盖率审计。**
