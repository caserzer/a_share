# P4 Learned Monotonic Ranking：事件型 Regime 失效补充诊断

> 文档性质：sealed bundle 之外的事后研究补充报告
> 对应主报告：[20B_P4_learned_monotonic_return_ranking_diagnostic_report.md](20B_P4_learned_monotonic_return_ranking_diagnostic_v1/20B_P4_learned_monotonic_return_ranking_diagnostic_report.md)
> 对应机器决策：[20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv](20B_P4_learned_monotonic_return_ranking_diagnostic_v1/20B_P4_learned_monotonic_return_ranking_diagnostic_decision.csv)
> 主报告 sealed SHA256：`6dda37bcec645689480774372c29d9a16f6b658135b45d52ccbffb85f20a5f8d`
> 研究日期：2026-07-14

## 1. 审计边界

本文件不修改 sealed output bundle，也不改变原机器决策：

```text
decision_state = 20B_P4_MLRANK_metric_materialization_blocked
metric_materialization_gate = false
validation_selection_gate = true
determinism_gate = true
```

本补充诊断是在看到 robustness 异常月份之后进行的 post-hoc 分析，只用于解释失败结构。事件月份不进入重新选模、调参、删样本或 terminal gate；leave-five-out 结果不得表述为可部署或 true-forward 成功证据。

## 2. 结论摘要

原报告中 Full M1 的 aggregate failure 并非均匀分布于21个 robustness 月份，而是高度集中在五个事件型月份。把 decision month 映射到实际承担收益的 label month 后，这五个月分别对应政策刺激与复市波动、DeepSeek 科技重估、流动性/反内卷行情、AI科技行情延续，以及地缘冲突后的 relief rotation。

更重要的是，五个事件月没有同时破坏原始 P4：

- 原始 P4 在五个事件月的 aggregate bucket Spearman 为 `+0.9394`，D10-D1 为 `+4.05%`；
- A2 cross-signals 在同五个月的 Spearman 为 `-0.9515`，D10-D1 为 `-11.63%`；
- Full 模型为 `-1.0000` 和 `-11.94%`。

因此，本轮失败不应简化为“事件冲击使 residual momentum 无效”。更准确的诊断是：

> 静态 P0/P1/P6 cross-signal overlay 在事件驱动的高波动 risk-on rotation 中方向性失效，并压过了仍然有效的原始 P4 排序。

## 3. 月份语义：decision month 不是收益发生月

原月表的 `decision_date=t` 表示在月末形成分桶，D10-D1 使用的是 `label_month=t+1` 的收益。因此事件归因必须按下表理解：

| decision date | label month | Full D1 | Full D10 | D10-D1 | 对应市场环境 |
|---|---|---:|---:|---:|---|
| 2024-09-30 | 2024-10 | +6.23% | -5.95% | **-12.18%** | 刺激政策后的国庆复市、FOMO 与快速反转 |
| 2025-01-27 | 2025-02 | +6.68% | -2.22% | **-8.90%** | DeepSeek 驱动的中国科技股重估 |
| 2025-07-31 | 2025-08 | +22.74% | +0.87% | **-21.87%** | 反内卷、流动性与 A 股补涨行情 |
| 2025-08-29 | 2025-09 | +5.23% | -3.75% | **-8.98%** | AI/科技行情延续与高弹性板块扩散 |
| 2026-03-31 | 2026-04 | +12.25% | +4.49% | **-7.76%** | 伊朗战争/油价冲击后的 relief rally 与科技成长反弹 |

这里的 D1/D10 return 来自 sealed `historical/model_bucket_monthly_returns.csv.gz`；D10-D1 与同月 centered-return 差完全相同。

## 4. 五次异常具有相同的暴露结构

Full M1 refit 的三个主要 cross-signal 系数为：

```text
p0_rank_t = -0.00609
p1_rank_t = -0.01810
p6_rank_t = -0.02727
```

其中 P6 是过去36个月月收益波动率的横截面 rank；rank 越高代表历史波动率越高。负系数使低 P6 rank 更容易得到较高 model score。因此，Full 模型的 D10 带有明显低波动倾向，而 D1 集中高波动股票。

五个事件月的桶暴露如下：

| decision date | D1 P1 rank | D10 P1 rank | D1 P6 rank | D10 P6 rank | D1 P4 rank | D10 P4 rank |
|---|---:|---:|---:|---:|---:|---:|
| 2024-09-30 | 0.821 | 0.179 | 0.892 | 0.094 | 0.273 | 0.858 |
| 2025-01-27 | 0.901 | 0.180 | 0.876 | 0.075 | 0.389 | 0.753 |
| 2025-07-31 | 0.890 | 0.186 | 0.858 | 0.129 | 0.469 | 0.707 |
| 2025-08-29 | 0.894 | 0.198 | 0.869 | 0.098 | 0.568 | 0.631 |
| 2026-03-31 | 0.822 | 0.170 | 0.843 | 0.315 | 0.350 | 0.799 |

五次事件的共同结构非常稳定：

```text
D1 = 高 P1 rank + 高历史波动率 + 较低 P4
D10 = 低 P1 rank + 低历史波动率 + 较高 P4
```

事件月不是随机伤害若干股票，而是反复触发同一种横截面 rotation：高波动、高弹性或主题型股票大幅跑赢低波动股票。Full 模型被冻结的 defensive cross-signal 权重在这种 regime 中方向相反。

## 5. 失败集中度：event-only 与 leave-five-out

### 5.1 Full 模型

| 样本 | 月数 | aggregate bucket Spearman | adjacent order rate | mean Rank IC | D10-D1 |
|---|---:|---:|---:|---:|---:|
| 全部 robustness | 21 | -0.7333 | 0.3333 | +0.0440 | -1.54% |
| 五个事件月 | 5 | **-1.0000** | — | **-0.2323** | **-11.94%** |
| 其余月份 | 16 | **+0.9394** | 0.6667 | **+0.1303** | **+1.70%** |

这说明 aggregate failure 高度集中在事件型月份。不过，“其余16个月”是看到结果后的条件样本，不得作为新的正式 OOS 指标。

### 5.2 五个事件月的模型对照

| scored model | aggregate bucket Spearman | mean Rank IC | D10-D1 |
|---|---:|---:|---:|
| B0：原始 P4 | **+0.9394** | +0.0741 | **+4.05%** |
| A1：P4 path only | +0.2242 | -0.0008 | -0.18% |
| A2：P0/P1/P6 cross only | **-0.9515** | **-0.2730** | **-11.63%** |
| S0：Full | **-1.0000** | **-0.2323** | **-11.94%** |

Full 与 A2 几乎完全一致，而 B0 原始 P4 在相同事件月方向正确。因此，五个月的失败归因明确指向 cross-signal overlay，不支持“P4 被事件共同摧毁”的说法。

### 5.3 去掉五个月后的模型对照

| scored model | aggregate bucket Spearman | mean Rank IC | D10-D1 |
|---|---:|---:|---:|
| B0：原始 P4 | -0.1758 | -0.0327 | -0.46% |
| A1：P4 path only | +0.6000 | +0.0178 | +0.50% |
| A2：P0/P1/P6 cross only | +0.8303 | +0.1419 | +1.87% |
| S0：Full | +0.9394 | +0.1303 | +1.70% |

该表只能说明模型具有明显的 conditional morphology，不能授权删除事件月。若把异常月份定义建立在 realized D10-D1 上，再删除这些月份，会产生直接的 outcome-conditioned selection bias。

## 6. 公开事件与本地形态的对应

### 6.1 2024年10月：刺激政策、国庆复市与快速退潮

2024年9月24日，中国公布大规模刺激措施，股票和商品迅速上涨；国庆休市后，A 股于10月8日高开，但市场很快因进一步财政刺激细节不足而降温。Reuters 报道指出复市行情在高开后快速失去动能，并记录了随后深圳与创业板的极端波动：

- [Reuters：China stock rally fizzles as stimulus optimism fades](https://www.investing.com/news/economy-news/china-stocks-soar-to-2year-peaks-on-stimulus-hopes-3652311)
- [Reuters：China's stock rally hits speed bump](https://www.investing.com/news/economy-news/china-stocks-fall-sharply-set-to-snap-winning-streak-3654504)

本地数据中，高波动 D1 月收益为 `+6.23%`，低波动 D10 为 `-5.95%`，符合高弹性股票在政策/FOMO冲击下与 defensive 组合发生大幅相对偏离的形态。

### 6.2 2025年2月：DeepSeek 科技重估

DeepSeek 在春节前后触发中国 AI 与科技资产重新定价，资金集中涌入 AI 相关股票：

- [Reuters：DeepSeek fever fuels patriotic bets on Chinese AI stocks](https://www.investing.com/news/stock-market-news/deepseek-fever-fuels-patriotic-bets-on-chinese-ai-stocks-3852706)
- [Reuters：China's markets return from holiday to trade war and DeepSeek rally](https://www.investing.com/news/stock-market-news/china-markets-return-from-holiday-facing-trade-war-and-ai-rally-3849285)

该月 D1 为 `+6.68%`、D10 为 `-2.22%`。这更像主题/科技 risk-on rotation，而不是全市场普跌时的防御失效。

### 6.3 2025年8—9月：流动性补涨与 AI 扩散

Reuters 报道显示，2025年8月境内 A 股获得显著资金流入，上证指数月内约上涨12%、CSI300约上涨9%；8月成为近11个月最强月份之一。随后9月科技行情延续，STAR50 在8月上涨约28%后，9月继续上涨约12%：

- [Reuters：China stocks on course for best hedge-fund inflows in six months](https://www.investing.com/news/economy-news/china-stocks-on-course-for-best-hedge-fund-inflows-in-6-months-morgan-stanley-says-4211835)
- [Reuters：China stocks post biggest monthly gain in 11 months](https://www.nst.com.my/business/corporate/2025/08/1267544/china-stocks-post-biggest-monthly-gain-11-months)
- [Reuters：China and Hong Kong stocks eye fifth monthly gain on AI boost](https://www.tradingview.com/news/reuters.com%2C2025%3Anewsml_L2N3VH03V%3A0-china-hong-kong-stocks-eye-fifth-monthly-gain-on-ai-boost/)

2025年8月是本轮最极端的单月：D1 平均 `+22.74%`，D10 仅 `+0.87%`。模型没有错判市场绝对方向，而是在强 risk-on 牛市中配置到了错误的横截面风格。

### 6.4 2026年4月：地缘冲突后的 relief rotation

2026年4月全球市场围绕伊朗战争、油价和停火预期剧烈摆动；Reuters 记录了中国与香港股票随停火谈判预期出现 relief rally。CIIS 的4月市场汇总显示，STAR Composite 月涨幅约 `20.50%`，高于 CSI300 的 `8.03%`：

- [Reuters：China and Hong Kong stocks join global relief rally](https://www.sahmcapital.com/news/content/china-hong-kong-stocks-join-global-relief-rally-on-news-us-iran-talks-will-resume-2026-04-15)
- [CIIS：April 2026 market overview](https://www.ciis.com.hk/hongkong/en/uploadfiles/202605/06/2026050613495376580038.pdf)

本地 D1 为 `+12.25%`、D10 为 `+4.49%`，仍然体现高弹性组合跑赢低波动组合，而非简单的 market beta 下跌。

外部事件资料只证明这些月份存在明确的政策、主题、流动性或地缘冲击；“这些冲击通过高波动 rotation 导致本模型失败”是结合本地桶暴露和收益形成的研究推断，不是外部新闻直接给出的因果结论。

## 7. 对原失败解释的修正

原报告确认了 Full 模型未能通过 robustness ordering gate；本补充诊断进一步把原因从笼统的“时间非平稳”收窄为：

1. Full 模型的 score 长期由 P0/P1/P6 cross component 主导；
2. cross component 隐含显著的低波动/防御倾向；
3. 五个事件月都出现高波动、高弹性或主题股的 risk-on rotation；
4. A2 在这些月份几乎严格反单调，并把 Full 一起拉成反单调；
5. 原始 P4 在相同事件月仍保持正向排序，因此失败不是 P4 本身的统一崩溃；
6. security Rank IC 对收益幅度不敏感，少数尾部损失足以令 aggregate D10-D1 失败，而全样本平均 IC 仍略为正。

因此，当前证据最支持的因果链是：

```text
静态负向 P1/P6 权重
    -> D10 持续偏向低波动/防御股票
    -> 事件型 risk-on regime 中高波动 D1 暴涨
    -> cross-only 反单调
    -> Full 覆盖并破坏原始 P4 的正向排序
```

## 8. 现金/国债并非直接修复

这五个月多数不是全市场 risk-off，而是高弹性股票上涨远快于低波动股票。简单加入现金或国债可能降低风险，但也可能在事件型 risk-on 月份错过上涨，并不能自动修复股票之间的相对排序。

本结果更直接支持的是 expert switching，而不是单纯 cash timing：

```text
P4 expert
cross-signal expert
abstain/cash expert
        ↑
只由 decision time 可见的 regime state 进行选择或缩放
```

其中 cash/abstain 只应处理预期风险收益不利或不可判定状态；对本轮五个 risk-on 事件月，更关键的是关闭错误的低波动 overlay 或回退到原始 P4。

## 9. 下一步可证伪研究方向

下一轮不应把五个月登记成可删除的 exception list，也不应使用事件结果或新闻标签做 retrospective switch。可研究的 PIT regime feature 应只来自 decision date 当时已知的信息，例如：

- 全市场成交额及其1/3个月加速度；
- 上涨家数占比、涨停扩散与横截面收益离散度；
- 高波动减低波动、成长减防御、小盘减大盘的当月 spread；
- 指数短期趋势、跳空、月内反转与 realized volatility；
- P4 expert 与 cross-signal expert 的过去已实现、严格滞后一月 morphology；
- regime 不确定度与 abstain threshold。

严谨验证至少需要：

1. 在任何 robustness outcome 读取前冻结 regime feature、threshold 与 expert mapping；
2. 保留全部21个月，包括本次五个事件月；
3. 与 `always P4`、`always cross`、`always full` 和 `hash/null switch` 做 paired comparison；
4. 单独报告 event-like months，但不得让它们参与阈值选择；
5. 以月为统计单位，并继续报告桶 Spearman、adjacent rate、Rank IC、D10-D1 与 block-bootstrap；
6. 不把 cash/国债 participation 与股票横截面排序混为同一个 gate。

在完成这种 outcome-free、PIT-frozen 验证以前，当前最强结论仍然只是：静态 Full 模型存在可定位、事件集中且经济上可解释的 regime fragility。
