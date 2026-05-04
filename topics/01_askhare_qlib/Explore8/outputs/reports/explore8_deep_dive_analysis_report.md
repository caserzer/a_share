# Explore8 深度诊断分析报告

## 分析边界

本报告基于 Explore8 已生成的结构化输出和本轮回放明细，目的是给出诊断洞察，不是生成可交易候选。
- Provider mode: `pit_primary`。
- 2017-2024 coverage-ok 年份数: `8`。
- 历史结果 CSV 用于计算: `False`；2025-2026 用于选择: `False`。

核心边界先写在前面：本轮 PIT provider 覆盖已经通过，年度规则排序可以做 retrospective diagnostic；但 Explore8 仍是诊断实验，不直接产出可交易候选。

## 1. 数据可信边界

- 2017-2024 合计缺失 `0` 个 `date + instrument` required-field 行。
- 最弱年份是 `2017`，required-field coverage `100.00%`；最高年份是 `2017`，coverage `100.00%`。
- 所有研究年份均为 `coverage_ok`，年度规则排序的主要风险已经从数据缺口转为规则形态、市场状态和仓位约束解释。

### 覆盖缺口的行业结构
| Year | Status | Required coverage | Missing rows | Top missing industries |
| --- | --- | --- | --- | --- |
| 2017 | coverage_ok | 100.00% | 0 |  |
| 2018 | coverage_ok | 100.00% | 0 |  |
| 2019 | coverage_ok | 100.00% | 0 |  |
| 2020 | coverage_ok | 100.00% | 0 |  |
| 2021 | coverage_ok | 100.00% | 0 |  |
| 2022 | coverage_ok | 100.00% | 0 |  |
| 2023 | coverage_ok | 100.00% | 0 |  |
| 2024 | coverage_ok | 100.00% | 0 |  |
洞察：此前 `56,337` 行 required-field 缺失来自 fallback provider 的 instrument 覆盖不足；补齐 PIT provider 后，行业缺口不再驱动结论，后续应把注意力转向年度 regime、信号密度和仓位利用率。

## 2. 市场状态与信号密度

| Year | HS300 return | HS300 MDD | Width avg | Trend days | Industry sync | Breakout | Pullback | Breakdown repair |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | 20.60% | -6.07% | 65.77% | 97.56% | 32.24% | 162 | 42 | 1230 |
| 2018 | -26.34% | -31.88% | 35.94% | 11.11% | 9.95% | 75 | 8 | 589 |
| 2019 | 37.95% | -13.49% | 61.26% | 59.02% | 28.39% | 208 | 46 | 2701 |
| 2020 | 25.51% | -16.08% | 57.38% | 72.02% | 34.39% | 382 | 65 | 3269 |
| 2021 | -6.21% | -18.19% | 51.20% | 26.34% | 36.88% | 164 | 26 | 1830 |
| 2022 | -21.27% | -28.65% | 40.53% | 11.62% | 20.99% | 78 | 30 | 782 |
| 2023 | -11.75% | -21.51% | 46.49% | 22.73% | 20.41% | 163 | 44 | 1966 |
| 2024 | 16.20% | -14.41% | 61.14% | 50.41% | 29.60% | 274 | 141 | 2704 |

- Breakout 信号最高是 `2020` 的 `382` 次；pullback 信号最高是 `2024` 的 `141` 次。
- 市场 trend-day ratio 低于 25% 的年份为 `2018, 2022, 2023`。这些年份即使某些诊断版本回撤较小，也很可能是高现金/低交易带来的防守效果，而不是规则有 alpha。
- 2024 的信号密度明显恢复；在 provider coverage 已通过后，它更适合作为高活跃 regime 的规则形态对比年份，而不是被数据缺口排除。

## 3. 规则族表现：方向性而非排名

| Rule version | Positive years | Active years | Trades | Median return | Best | Worst | Avg cash | Net PnL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | 5 | 8 | 1492 | 0.44% | 3.51% | -1.35% | 74.80% | 43,114 |
| ema_state_ema60_base__fixed_w05 | 4 | 8 | 340 | 0.47% | 51.82% | -11.31% | 44.20% | 430,590 |
| breakdown_repair_layered_diag__risk_unit_w03_ind20 | 4 | 8 | 829 | 0.35% | 3.66% | -4.58% | 73.23% | -5,312 |
| ema_state_ema60_base__risk_unit_w03_ind20 | 4 | 8 | 369 | 0.26% | 24.26% | -5.95% | 70.21% | 224,930 |
| ema_state_stop_time_base__risk_unit_w03_ind20 | 4 | 8 | 605 | 0.00% | 18.92% | -6.01% | 73.54% | 115,409 |
| ema_state_stop_time_base__fixed_w05 | 4 | 8 | 594 | -1.87% | 29.08% | -9.46% | 51.46% | 34,759 |
| pullback_strict_trend_layered__risk_unit_w03_ind20 | 3 | 5 | 90 | -0.00% | 1.61% | -1.12% | 97.83% | 4,228 |
| pullback_top_score_layered__risk_unit_w03_ind20 | 3 | 5 | 96 | -0.00% | 1.61% | -1.11% | 97.72% | -2,176 |
| pullback_strict_trend_layered__risk_unit_w05_ind25 | 3 | 5 | 90 | -0.04% | 2.80% | -2.00% | 96.27% | 3,970 |
| pullback_top_score_layered__risk_unit_w05_ind25 | 3 | 5 | 96 | -0.04% | 2.80% | -2.01% | 96.09% | -7,403 |
| breakout_fast_failure_diag__risk_unit_w03_ind20 | 3 | 8 | 718 | -1.47% | 2.25% | -5.11% | 84.74% | -118,076 |
| breakout_layered_base__risk_unit_w03_ind20 | 3 | 8 | 553 | -1.55% | 6.36% | -5.87% | 82.07% | -43,857 |

### Entry family 汇总

| Entry family | Versions | Trades | Net PnL | Median ret | Best | Worst | Cash | Stop/time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ema_state_baseline | 4 | 1908 | 805,688 | -0.29% | 51.82% | -11.31% | 59.85% | 34.99% |
| breakdown_repair_diagnostic | 2 | 2321 | 37,802 | 0.44% | 3.66% | -4.58% | 74.02% | 31.28% |
| pullback_original | 6 | 1550 | -8,888 | -1.58% | 30.19% | -5.21% | 89.98% | 62.61% |
| pullback_top_score | 2 | 192 | -9,579 | -0.00% | 2.80% | -2.01% | 96.91% | 43.64% |
| pullback_strict_trend | 3 | 277 | -12,374 | -0.05% | 2.80% | -2.00% | 97.70% | 39.19% |
| pullback_strict_money | 2 | 186 | -78,777 | -0.52% | 1.99% | -2.04% | 98.03% | 60.43% |
| breakout_core | 7 | 3815 | -290,205 | -3.00% | 21.98% | -10.62% | 73.19% | 70.48% |

洞察：
- `ema_state_baseline` 的诊断收益最好，但它更像宽松趋势暴露底座，不证明 entry trigger 本身有效。
- `breakout_core` 总净 PnL 为正，但 median return 为负，说明 breakout 对年份/退出方式非常敏感，需要配合更好的失败退出和持有逻辑。
- `pullback_original` 和 `pullback_strict_money` 都偏弱；`pullback_strict_trend` / `pullback_top_score` 虽然方向较好，但 active 年份少、现金比例极高，暂时只能说明“更强趋势确认可能有帮助”，不能说明 pullback 已修复。
- `breakdown_repair_diagnostic` 交易数多但净值接近零，说明它像高噪声诊断形态，不能直接进入候选。

## 4. 入场与退出贡献

| Entry type | Trades | Net PnL | Gross PnL | Win rate | Avg return/trade | Avg hold |
| --- | --- | --- | --- | --- | --- | --- |
| ema_state | 1908 | 805,688 | 954,125 | 27.04% | 1.43% | 30.7 |
| breakdown_repair | 2321 | 37,802 | 167,589 | 33.13% | -0.00% | 12.0 |
| pullback | 2205 | -109,618 | 55,968 | 25.53% | -0.08% | 13.3 |
| breakout | 3815 | -290,205 | -27,119 | 24.48% | -0.15% | 19.1 |

### Exit reason 总贡献

| Exit reason | Trades | Net PnL | Win rate | Avg hold |
| --- | --- | --- | --- | --- |
| time_stop | 4095 | -5,115,586 | 5.47% | 13.0 |
| stop_loss | 1243 | -3,435,960 | 0.00% | 5.3 |
| fast_relative_failure | 345 | 50,655 | 46.38% | 6.0 |
| fast_ema20_failure | 359 | 296,359 | 50.97% | 12.5 |
| fast_industry_failure | 711 | 335,104 | 59.77% | 13.2 |
| research_end_forced_close | 247 | 480,923 | 53.44% | 13.6 |
| trailing_stop | 1323 | 3,900,198 | 61.83% | 22.2 |
| ema60_exit | 1926 | 3,931,975 | 43.61% | 35.6 |

洞察：
- `time_stop` 和 `stop_loss` 是主要亏损来源，分别对应趋势没有延续和入场后快速破坏。
- `trailing_stop` 与 `ema60_exit` 是主要正贡献来源，说明真正有价值的交易需要趋势尾部，而不是短期均值回归式退出。
- fast-failure 的若干 exit reason 单项为正，但整个 `fast_failure_exit_diagnostic` family 仍偏弱，提示早退出可能减少部分损失，同时也容易切断尾部收益。

### 年度 Entry PnL 分解

| Year | EMA state | Breakout | Pullback | Breakdown repair |
| --- | --- | --- | --- | --- |
| 2017 | -123,092 | -1,929 | -6,327 | 14,208 |
| 2018 | 183,144 | -99,208 | -25,748 | 30,233 |
| 2019 | -13,868 | -387,081 | -183,487 | -10,210 |
| 2020 | 357,138 | 66,242 | 553,155 | -67,944 |
| 2021 | 1,096,216 | 585,248 | 299,200 | 111,036 |
| 2022 | -461,160 | -574,165 | -294,721 | -36,206 |
| 2023 | -380,809 | -272,943 | -259,444 | 1,043 |
| 2024 | 148,119 | 393,633 | -192,247 | -4,357 |

### 正收益交易集中度

| Entry | Winning trades | Positive PnL | Top5 winner share |
| --- | --- | --- | --- |
| breakdown_repair | 769 | 1,480,179 | 7.01% |
| breakout | 934 | 4,740,173 | 6.38% |
| ema_state | 516 | 4,196,795 | 8.80% |
| pullback | 563 | 2,467,477 | 8.44% |

## 5. 仓位与风险形态

| Sizing | Family | Trades | Net PnL | Median ret | Avg MDD | Avg cash | Positive year cells |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_w05 | fixed_weight | 2484 | 403,981 | -2.06% | -11.00% | 66.31% | 18 |
| risk_unit_w03_ind20 | risk_unit_with_industry_cap | 6185 | 169,500 | -0.45% | -4.47% | 86.13% | 40 |
| risk_unit_w05_ind25 | risk_unit_with_industry_cap | 1580 | -129,814 | -0.92% | -5.21% | 86.50% | 16 |
洞察：固定权重贡献最高但平均回撤最深；risk-unit + industry cap 明显压低回撤，但现金比例长期在 87%-88% 左右，说明风险控制有效但资金利用不足。下一轮不宜只扩大 entry 搜索，也要单独校准 risk budget、单票 cap、行业 cap 和 daily-new cap。

## 6. 行业归因与集中风险

| Worst industry | Trades | Net PnL | Win rate |
| --- | --- | --- | --- |
| 非银金融 | 1108 | -1,036,118 | 16.16% |
| 银行 | 1034 | -694,543 | 21.86% |
| 煤炭 | 180 | -381,719 | 11.67% |
| 计算机 | 401 | -226,218 | 22.69% |
| 家用电器 | 415 | -223,665 | 21.45% |
| 公用事业 | 281 | -193,930 | 24.91% |
| 钢铁 | 147 | -162,019 | 8.16% |
| 建筑装饰 | 196 | -157,001 | 22.45% |
| 交通运输 | 320 | -108,137 | 26.25% |
| 房地产 | 283 | -77,857 | 31.10% |
| 建筑材料 | 153 | -32,382 | 20.92% |
| 机械设备 | 150 | -30,468 | 26.67% |

### 正贡献行业

| Best industry | Trades | Net PnL | Win rate |
| --- | --- | --- | --- |
| 食品饮料 | 1317 | 1,101,557 | 28.93% |
| 基础化工 | 455 | 666,604 | 32.53% |
| 汽车 | 493 | 519,023 | 32.86% |
| 电力设备 | 476 | 452,638 | 33.40% |
| 国防军工 | 191 | 259,574 | 24.08% |
| 有色金属 | 457 | 199,426 | 38.07% |
| 医药生物 | 547 | 180,089 | 35.28% |
| 通信 | 139 | 167,946 | 51.08% |
| 社会服务 | 99 | 140,522 | 27.27% |
| 石油石化 | 167 | 89,057 | 38.92% |
| 农林牧渔 | 137 | 43,899 | 45.26% |
| 轻工制造 | 64 | 2,585 | 21.88% |

洞察：非银金融、银行、煤炭等是明显拖累；食品饮料、基础化工、汽车、电力设备贡献更强。由于 provider 覆盖已补齐，这些差异更值得进入后续行业暴露/风险预算诊断，但仍不能直接简化成行业白名单或黑名单。

## 7. 失败交易切片

| Entry | Exit | Loss trades | Net PnL |
| --- | --- | --- | --- |
| breakout | time_stop | 2148 | -3,145,205 |
| ema_state | ema60_exit | 555 | -2,007,473 |
| pullback | stop_loss | 835 | -1,845,996 |
| breakout | stop_loss | 343 | -1,360,329 |
| ema_state | time_stop | 790 | -1,215,415 |
| breakdown_repair | ema60_exit | 420 | -475,725 |
| breakdown_repair | time_stop | 537 | -444,664 |
| pullback | time_stop | 396 | -372,204 |
| breakout | ema60_exit | 73 | -196,410 |
| pullback | trailing_stop | 290 | -192,325 |
| breakdown_repair | fast_industry_failure | 258 | -176,303 |
| breakout | trailing_stop | 161 | -123,201 |
| breakout | fast_ema20_failure | 61 | -120,810 |
| ema_state | stop_loss | 20 | -116,342 |

### 趋势分数 / 成交额 / 初始风险

| Trend score | Money ratio | Initial risk | Loss trades | Net PnL |
| --- | --- | --- | --- | --- |
| top10 | gt120 | risk_gt12 | 1063 | -2,536,167 |
| top20 | gt120 | risk_gt12 | 759 | -1,336,801 |
| top20 | gt120 | risk_8_12 | 691 | -1,153,209 |
| top10 | gt120 | risk_8_12 | 539 | -998,795 |
| top10 | gt120 | risk_4_8 | 342 | -598,085 |
| top20 | gt120 | risk_4_8 | 453 | -596,473 |
| top20 | 080_100 | risk_4_8 | 291 | -580,959 |
| top20 | 060_080 | risk_4_8 | 239 | -431,107 |
| top10 | 080_100 | risk_4_8 | 229 | -397,769 |
| top10 | 100_120 | risk_gt12 | 112 | -331,546 |
| top10 | 060_080 | risk_4_8 | 202 | -314,663 |
| top10 | 080_100 | risk_gt12 | 124 | -313,080 |
| top50 | gt120 | risk_gt12 | 175 | -227,550 |
| top50 | gt120 | risk_4_8 | 305 | -223,323 |

洞察：亏损最大的切片不是低分股票，而是 `top10/top20 + money_ratio gt120 + high initial risk`。这说明当前 trend_score 本身不足以过滤失败交易；高成交额突破也可能是高波动追高，下一轮需要把入场日风险距离、gap、ATR/close 和上影线后的失败概率放进规则解释，而不是只提高 trend_score 门槛。

## 8. 我的判断

1. 数据阻断已经解除：PIT universe、PIT industry 和 PIT provider 现在可以支撑 2017-2024 的 retrospective 诊断。
2. 规则层面最值得继续拆解的是 breakout + layered/EMA 尾部持有，而不是 original pullback。Breakout 的总贡献为正，但 `time_stop` 是大亏损源，说明问题不只是入场，也包括失败交易如何尽早识别、趋势交易如何不要过早截断。
3. Pullback 的原始定义不应直接继续优化成候选。严格趋势/Top-score 版本有一些方向性改善，但主要靠低交易和高现金，下一轮应重写 pullback 形态，而不是只把阈值调严。
4. 风控不是越保守越好。risk-unit 和 industry cap 降低回撤，但现金过高；补齐 provider 后仍出现高现金，说明仓位利用率需要单独诊断。
5. 行业结论可以进入复验队列，但不能直接规则化。食品饮料、基础化工、汽车等正贡献明显，非银金融/银行拖累明显，下一步应看是否来自行业 beta、个别大票还是规则入场时点。
6. 下一阶段建议顺序：基于 coverage-ok 年份做 retrospective cluster -> 拆 breakout time-stop 亏损 -> 重写 pullback 形态 -> 做仓位利用率和行业暴露约束诊断。
7. 2025 reference 当前 comparison allowed=`True`，原因是 `nan`；所以 2025 只能作为背景画像，不能参与相似度排序。
