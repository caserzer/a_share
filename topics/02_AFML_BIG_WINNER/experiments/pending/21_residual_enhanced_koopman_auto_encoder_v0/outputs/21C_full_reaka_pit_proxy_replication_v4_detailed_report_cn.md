# 21C Full REAKA PIT Proxy 复现实验详细中文报告与研究解读

## 0. 文档定位与密封边界

本文是 `21C_FULL_v4` 密封结果的中文 companion report。原始 v4 输出目录已经完成 `43/43` 文件哈希闭环，因此本文不修改原报告、manifest、决策表、模型、配置或代码，也不加入密封输出目录。

- 密封原报告：`21C_full_reaka_pit_proxy_replication_v4/21C_full_reaka_pit_proxy_replication_report.md`
- 原报告 SHA256：`44ba67dc5cd2d7cd7cfaa482b6e77cf4797e859b4ba7aa828bd3e4fb75c44b02`
- 密封决策：`21C_FULL_r2_direction_not_supported`
- 本文新增的月度、seed 相关性、Top30 路径和目标换手统计均由密封 CSV/Parquet 复算，只用于解释，不是新的 gate evidence，也不改变原决策。

## 1. 执行摘要

本实验成功完成了工程执行、PIT universe 修复、三 seed 训练、early selection、独立 late readout 和最终哈希封存；失败的是研究假设，而不是运行完整性。

最重要的结果如下：

1. R2 在 `validation_early` 的 ensemble RankIC 为 `+0.015658`，到未参与选模的 `validation_late` 变为 `-0.002304`，下降 `0.017962`。这是明显的 early-to-late 泛化坍塌。
2. 三个 seed 在 late fold 只有 `1/3` 为正，ensemble 正 RankIC 日占比仅 `49.51%`；六个 leave-one-month-out 结果只有 `1/6` 为正。
3. R2 相对 M1 LightGBM 和 M3 Gated LSTM 的 late 日度配对 RankIC 差分别为 `-0.021898` 和 `-0.012987`，并不是“与基线接近但统计功效不足”，而是点估计明确落后。
4. 三个 seed 的同日横截面排序几乎互不相关，平均 Spearman 约为 `0`；不同 seed 的 Top30 平均只重合约 `1.8–2.0` 只，与随机抽取的期望重合 `1.85` 只基本一致。这说明模型没有形成跨初始化可复现的选股结构。
5. R2 的相邻交易日 Top30 等权目标组合换手近似值为 `93.82%`，显著高于 M1 的 `75.52%` 和 M3 的 `71.24%`。即使不计成本，R2 Top30 gross 路径已经最差；加入真实交易约束只会进一步恶化可执行性。
6. 因此，R2 不应作为 primary alpha、组合优化输入或部署候选。现有证据也不足以把它降级为 meta-label 或 participation filter；后两者仍需要独立的条件增益检验。

## 2. 数据范围、PIT universe 修复与 estimand 变化

### 2.1 样本影响

| Fold | 原始行数 | 排除行数 | 保留行数 | 原始 instrument | 排除 instrument | 保留 instrument |
|---|---:|---:|---:|---:|---:|---:|
| train | 396,207 | 60,814 | 335,393 | 1,256 | 396 | 860 |
| validation_early | 51,932 | 0 | 51,932 | 625 | 0 | 625 |
| validation_late | 50,167 | 0 | 50,167 | 592 | 0 | 592 |

训练样本被排除 `15.35%`，训练 instrument 被排除 `31.53%`。排除规则是对 train、validation-early、validation-late 统一删除整只 instrument 历史，而不是只删除缺键行或进行填补。排除注册表包含 `396` 个 instrument，SHA256 为：

`3c3d903821ee56a49f1ea0d83327606b58f87826ae317d6f95e5a5d4236aef11`

### 2.2 对结果解释的含义

这次修改修复的是 teacher branch 对严格同 instrument `t+1` approved feature-cache key 的可构造性。由于这 396 个 instrument 在两个 validation fold 中本来就没有出现，验证集的行数、日期和横截面没有变化；变化发生在训练分布和训练 universe。

因此不能把本次结果解释成“删除坏股票后性能下降”或“排除操作改善了验证结果”。v2 在 teacher materialization 阶段已经失败，没有形成可比较的训练结果；v4 只能回答修改后的 estimand 是否支持 R2，而不能识别排除操作的因果效果。

## 3. 模型、搜索预算与训练成本

R2 使用双 LSTM、shared gate、4-operator AKS、20-step DDPM 和 8 次推断 draws。特征维度为 `157`，参数量为 `140,741`；只运行冻结的三个 primary seeds，没有额外 sensitivity 或超参数搜索。

| Seed | 选中 epoch | 最终评估 epoch | early 选模 RankIC | optimizer steps | 审计训练秒数 | 峰值 GPU MiB | 状态 |
|---:|---:|---:|---:|---:|---:|---:|---|
| 20260713 | 8 | 18 | 0.005950 | 23,598 | 824.59 | 552 | early stopped |
| 20260714 | 16 | 26 | 0.009829 | 34,086 | 1,118.05 | 530 | early stopped |
| 20260715 | 3 | 13 | 0.008026 | 17,043 | 575.38 | 530 | early stopped |

合计执行 `74,727` 次 optimizer step、`57` 个 data passes，`training_wall_seconds` 合计 `2,518.03` 秒，即约 `41.97` 分钟。三个 seed 的选中 epoch 分别为 `8/16/3`，差异较大，已经提示优化路径对初始化敏感。

v4 的工程优化包括进程内共享 RAM feature cache、`1024` validation inference batch，以及每个 row/draw 一次生成 20 个 CPU noise tensors 后一次传入 GPU。它没有减少训练数据、epoch、patience、draw 数或 optimizer step。v3 未完成首 seed，因此不能计算完整 run-to-run 加速比；可确认的是 v4 首个 checkpoint 的进程区间约 `14分38秒`，而 v3 运行约 `32分钟` 时仍为 `0/3` checkpoint。

## 4. RankIC：early selection 到 late readout 的泛化变化

### 4.1 Seed 级结果

| Seed/组合 | Early RankIC | Early 正日率 | Late RankIC | Late RankICIR | Late 正日率 | Early→Late 变化 |
|---|---:|---:|---:|---:|---:|---:|
| 20260713 | 0.005950 | 57.94% | -0.002090 | -0.0435 | 44.66% | -0.008039 |
| 20260714 | 0.009829 | 61.68% | -0.003712 | -0.0885 | 47.57% | -0.013542 |
| 20260715 | 0.008026 | 59.81% | 0.001616 | 0.0346 | 52.43% | -0.006410 |
| 三 seed ensemble | 0.015658 | 65.42% | -0.002304 | -0.0559 | 49.51% | -0.017962 |

Early fold 有 `107` 个完整交易日，日横截面约 `480–489` 只；late fold 有 `103` 个完整交易日，日横截面约 `484–490` 只。所有日的 score/label coverage 完整，因此 late 变差不能归因于覆盖缺失。

### 4.2 关键发现

三个 seed 在 early fold 都为正，ensemble 甚至高于所有单 seed；但到 late fold，两个 seed 转负，ensemble 也转负。由于 checkpoint 正是依据 early fold 选择，这说明 early fold 的正值含有明显的选择适配成分，不能与 late fold 合并后再声称模型整体有效。

密封结果中的 `validation_full` ensemble RankIC 为 `+0.006848`，但它混合了用于 checkpoint selection 的 early 数据和真正的 late readout。该数值适合做完整路径描述，不适合作为泛化或部署证据；决策必须以 late fold 为主。

## 5. 更深的 seed 稳定性诊断

### 5.1 同日横截面排序相关性

以下统计由两个密封 prediction-score Parquet 逐日复算：

| Seed pair | Early 平均 Spearman | Late 平均 Spearman | Late Top30 平均重合数 |
|---|---:|---:|---:|
| 20260713 vs 20260714 | -0.0011 | 0.0003 | 1.87 |
| 20260713 vs 20260715 | -0.0020 | 0.0044 | 1.76 |
| 20260714 vs 20260715 | -0.0066 | 0.0039 | 1.96 |

在约 487 只股票中独立抽取两个 Top30，随机期望重合约为 `30×30/487≈1.85` 只。实际重合与该基准几乎相同，且 seed 间 RankIC 排序相关性也接近零。这不是普通的“参数略有差异”，而是三个训练结果给出了接近独立的横截面排序。

### 5.2 Ensemble 不是稳定共识

Late score 的总体标准差分别约为：seed 20260713 `2.04e-4`、seed 20260714 `1.49e-4`、seed 20260715 `1.53e-4`。当前 ensemble 对 raw score 做算术平均，因此 ensemble 排名与三个 seed 的平均逐日 Spearman 分别约为 `0.672/0.489/0.502`，对高离散度的 seed 20260713 更敏感。

这意味着当前 ensemble 更像对三个不一致排序进行 scale-sensitive 混合，而不是提取三者共同确认的信号。seed 20260713 在 late fold 的 RankIC 为负，因此 raw-score 尺度差异可能加剧 ensemble 的不稳定；这是一项设计风险推断，不是已经由 ablation 证明的单一根因。

可在未来独立 requirement 中比较 raw-score mean、日内 rank-normalized mean 和 seed-consensus filter，但不得用事后替换 ensemble 的方式重写本次结果。

## 6. 月度稳定性与 LOMO

### 6.1 Late 月度 RankIC

| 月份 | 完整日数 | R2 RankIC | M1 RankIC | M3 RankIC |
|---|---:|---:|---:|---:|
| 2023-07 | 18 | -0.011537 | -0.015590 | 0.018078 |
| 2023-08 | 23 | -0.014280 | 0.055722 | 0.040423 |
| 2023-09 | 20 | 0.013236 | 0.055269 | -0.014960 |
| 2023-10 | 17 | 0.008498 | -0.014893 | -0.011273 |
| 2023-11 | 18 | -0.007605 | 0.017374 | 0.017015 |
| 2023-12 | 7 | 0.003784 | -0.021105 | 0.004247 |

R2 为 `3` 个正月、`3` 个负月，但月度正负对总均值的贡献并不对称。8 月是最差月份；9 月和 10 月是主要正贡献月份。

### 6.2 Leave-one-month-out

| 被移除月份 | 剩余日数 | LOMO RankIC |
|---|---:|---:|
| 2023-07 | 85 | -0.000349 |
| 2023-08 | 80 | 0.001139 |
| 2023-09 | 83 | -0.006049 |
| 2023-10 | 86 | -0.004439 |
| 2023-11 | 85 | -0.001182 |
| 2023-12 | 96 | -0.002748 |

只有移除 8 月后结果勉强转正，幅度也只有 `0.001139`；其余五个 LOMO 均为负。late fold 的最大绝对月贡献占比为 `29.63%`，没有单月超过三成。这说明失败虽有月份集中性，但不能简单归结为一个可删除的异常月；相反，9 月和 10 月一旦移除，结果会更差。

## 7. R2 与本地基线的配对比较

| 模型 | Late mean RankIC | RankICIR | 正 RankIC 日率 | R2 对该模型配对差 | R2 优于该模型的日占比 |
|---|---:|---:|---:|---:|---:|
| M1 LightGBM | 0.019594 | 0.1753 | 55.34% | -0.021898 | 47.57% |
| M3 Gated LSTM | 0.010682 | 0.1250 | 57.28% | -0.012987 | 45.63% |
| R2 REAKA | -0.002304 | -0.0559 | 49.51% | — | — |

配对比较覆盖相同的 `103` 个 late 交易日。stationary bootstrap 使用 `5,000` 次复制、平均 block length `20`；R2 相对 M1/M3 优势的一侧 p 值分别为 `0.9334/0.8942`，Holm 调整后均为 `1.0`。

这里的含义不是“R2 可能有效但未显著”，而是观察到的优势方向本身为负。M1 在同一市场、同一 late fold 上取得正 RankIC，说明本地数据并非完全没有横截面可预测性；复杂 R2 没有把这种可预测性转化为稳定增益。

## 8. Top30 gross morphology：收益、相对收益与目标换手

### 8.1 密封摘要指标

| 模型 | 103 日累计 gross | 年化 gross | 无风险利率为 0 的年化 Sharpe | Top30-EW 日均差 | 正收益日率 |
|---|---:|---:|---:|---:|---:|
| M1 LightGBM | -5.12% | -12.06% | -0.67 | +5.38 bp | 48.54% |
| M3 Gated LSTM | -1.41% | -3.42% | -0.08 | +9.27 bp | 44.66% |
| R2 REAKA | -14.15% | -31.14% | -2.82 | -4.55 bp | 44.66% |

三条 absolute gross 路径均未计入 next-open、涨跌停、停牌、成本或连续 NAV，因此不能视为可执行 PnL。M1/M3 虽然 absolute gross 为负，但相对等权仍为正；R2 连相对等权差也为负，说明其问题不只是 late 市场整体偏弱。

### 8.2 R2 月度路径

| 月份 | R2 Top30 gross | R2 Top30-EW 日均差 | R2 月均 RankIC |
|---|---:|---:|---:|
| 2023-07 | 1.04% | -9.19 bp | -0.011537 |
| 2023-08 | -6.63% | -4.06 bp | -0.014280 |
| 2023-09 | -2.66% | -4.94 bp | 0.013236 |
| 2023-10 | -2.64% | 3.27 bp | 0.008498 |
| 2023-11 | -1.22% | -1.53 bp | -0.007605 |
| 2023-12 | -2.78% | -19.92 bp | 0.003784 |

7 月出现“absolute gross 为正但 RankIC/相对等权为负”，9–10 月则出现“RankIC 为正但 absolute gross 为负”。这说明市场共同收益与横截面排序质量是两个不同维度，不能用 Top30 absolute return 替代 RankIC gate，也不能用单月盈利证明 alpha 有效。

### 8.3 Companion 路径统计

由 `paper_proxy_top30_daily.csv` 复算：R2 Top30 路径最大回撤约 `-15.32%`，M1/M3 分别约 `-10.70%/-10.30%`。R2 最好单日为 `+2.01%`，最差单日为 `-2.33%`。

按相邻交易日等权 Top30 名单计算 `1-|Top30_t∩Top30_{t-1}|/30`，R2 平均目标换手约 `93.82%`，中位数 `93.33%`；M1/M3 分别约 `75.52%/71.24%`。该指标只描述名单更替，不包括实际成交、价格漂移或冲击成本。它仍清楚表明 R2 排名的时间连续性非常弱。

## 9. 论文数值与本地结果的正确关系

论文表中的 CSI300 REAKA RankIC/RankICIR 为 `0.064/0.568`，S&P500 为 `0.061/0.541`；本地 R2 late 为 `-0.002304/-0.0559`。两者市场、样本期、特征、标签、交易制度和实现细节不同，密封表已明确 `numerically_comparable=false`。

因此可以得出的结论只是：当前 paper-grounded local adaptation 没有在本地 PIT proxy 上复现方向稳定性。不能声称论文错误，也不能将差值解释成“复现损失百分比”。同样，本地 M1 的正 RankIC 只能证明本地验证集存在某些可学习结构，不能证明其达到论文可比水平。

## 10. Gate、访问与复现完整性

`27` 个 gate 中：

- `25` 个通过，包括执行授权、上游 lineage、runtime、PIT panel、train/validation firewall、teacher materialization、架构 shape、seed deterministic、GPU memory、训练完成、late-readout process、score coverage、RankIC 实现和 output manifest hash；
- `r2_direction_stability_gate` 为唯一失败的因果 gate；
- `failure_bundle_integrity_gate` 因本次属于正常 P5 finalized success profile 而为 `not_run`。

Historical holdout access 为 `0`。因此结果不是由于流程不完整、标签泄漏、分数缺失或文件漂移而被判失败，而是在完整可信的 validation-only 流程下，R2 的方向稳定性本身未通过。

## 11. Findings：失败发生在哪里

### 11.1 Ex-post 诊断

1. **主要失败是泛化，不是运行。** Early ensemble `+0.015658` 到 late `-0.002304`，所有 coverage/integrity gate 均通过。
2. **模型没有形成 seed 共识。** 三 seed 排序相关接近零，同日 Top30 重合接近随机期望。这比单纯的均值波动更严重，说明选股形态对初始化高度敏感。
3. **时间连续性不足。** R2 Top30 每日约更换 `28.1/30` 只股票；这种形态很难在真实市场中承受成本和交易限制。
4. **复杂度没有转化成相对优势。** R2 同时落后于树模型 M1 和较简单的序列模型 M3，且 bootstrap 优势检验完全不支持 R2。
5. **失败不是单一月份造成。** 仅移除 8 月后略为正，其余 LOMO 仍为负；9–10 月反而是支撑总结果的正贡献月份。
6. **绝对收益与排序质量需要分开。** Top30 gross 受市场共同方向影响，R2 的 Top30-EW 也为负才是更直接的相对选股警告。

### 11.2 不能从本实验直接确认的因果解释

本次 scope restart 明确跳过 nested ablation，因此不能把失败唯一归因于 AKS、diffusion、teacher residual、LSTM、Gumbel gate 或某个特定 loss。下面只能作为下一轮待检验假设：

- diffusion draw 和独立初始化可能放大了弱信号下的排序方差；
- raw-score ensemble 在 seed score scale 不一致时可能偏向高离散度 seed；
- 训练 universe 缩减 `31.53%` 的 instrument 后，复杂模型的有效样本多样性可能不足；
- early checkpoint selection 可能挑中了局部时期特征，而不是跨半年稳定结构。

这些假设必须通过同 universe、同 seed、同训练预算的受控 ablation 才能成立，不能据本次 full model 结果写成机制结论。

## 12. AFML 研究决策与下一步建议

### 12.1 当前决策

- **Primary alpha：拒绝。** late RankIC、seed 稳定性、LOMO 和相对基线均未通过。
- **Meta-label：暂不接受。** 当前没有证据表明 R2 能在 M1/M3 的某些条件子集上稳定提供增量信息。
- **Participation filter：暂不接受。** 尚未验证 R2 是否能预测“何时参与”，而不是仅在 ex-post 月份上表现不同。
- **Historical holdout、组合优化、policy training、部署：不授权。** 先解决 validation morphology，避免把不稳定排序带入更昂贵阶段。

### 12.2 若另行授权新 requirement，优先顺序

1. **先做 seed-consensus 诊断。** 冻结相同数据和预算，加入 seed 间日度 rank correlation、TopK overlap、目标换手和 ensemble scale exposure gate。
2. **比较 ensemble 语义。** 预注册 raw-score mean、日内 rank-normalized mean、median rank 和 consensus-only selection；只做 sensitivity，不回写本次主结果。
3. **做最小 nested ablation。** 以 M3 为基点，依次加入 teacher residual、AKS、diffusion，确认哪个组件首次导致 late 改善或恶化。
4. **提高 checkpoint 选择约束。** 除 early mean RankIC 外，加入 seed agreement、月度最差值、early LOMO 和 turnover ceiling，避免选择“均值正但形态不稳定”的 checkpoint。
5. **最后再讨论交易桥接。** 只有 RankIC、seed、月份和 TopK 连续性通过后，才值得加入 next-open、涨跌停、停牌和成本模型。

## 13. 最终研究洞察

本次最有价值的结论不是“复杂模型 RankIC 为负”这一单点结果，而是完整证据链显示：R2 在 early fold 能形成表面上更高的 ensemble RankIC，但其三个 seed 几乎没有共同排序，late fold 立即失效，Top30 又具有接近完全重置的日度形态。换言之，early 的提升更像对多个不一致弱排序的样本内聚合，而不是可迁移的共同 alpha。

从 AFML 决策角度，真正需要修复的不是再增加模型容量，而是建立更严格的 **morphology independence gate**：一个候选信号必须同时证明跨 seed、跨月、跨 fold 和相邻日期的结构一致性。R2 当前连这一步都没有通过，因此继续做历史回测或成本优化只会把研究问题转化为更复杂的回测问题。

## 14. 主要证据文件

- `21C_full_reaka_pit_proxy_replication_v4/21C_full_reaka_pit_proxy_replication_decision.csv`
- `21C_full_reaka_pit_proxy_replication_v4/daily_rankic_readout.csv`
- `21C_full_reaka_pit_proxy_replication_v4/rankic_stability_and_concentration_audit.csv`
- `21C_full_reaka_pit_proxy_replication_v4/paired_rankic_comparison.csv`
- `21C_full_reaka_pit_proxy_replication_v4/stationary_bootstrap_pair_diagnostic.csv`
- `21C_full_reaka_pit_proxy_replication_v4/paper_proxy_top30_summary.csv`
- `21C_full_reaka_pit_proxy_replication_v4/paper_proxy_top30_daily.csv`
- `21C_full_reaka_pit_proxy_replication_v4/training/training_run_registry.csv`
- `21C_full_reaka_pit_proxy_replication_v4/training/selection/validation_early_prediction_scores.parquet`
- `21C_full_reaka_pit_proxy_replication_v4/training/readout/validation_late_prediction_scores.parquet`
- `21C_full_reaka_pit_proxy_replication_v4/preflight/pit_universe_exclusion_impact.csv`
- `21C_full_reaka_pit_proxy_replication_v4/gate_evidence_21c_full.csv`
