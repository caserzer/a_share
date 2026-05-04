# Explore8 PIT EMA 同源规则族逐年诊断报告

## 结论摘要

- PIT universe authority: `Explore7/data/universe/pit_mcap500_mainboard_daily.csv`；静态 `mcap500_mainboard_20251231` 交易资格使用标记为 `False`。
- Provider mode: `pit_primary`；coverage-limited diagnostic: `False`。
- 历史 result CSV 用于计算: `False`；2025-2026 用于选择: `False`。
- 可进入 retrospective leaderboard / cluster 的年份: `2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024`。非 coverage-ok 年份只保留覆盖诊断。
- 覆盖缺口总量 `0` 行；2017-2024 研究年份 required-field coverage 均为 `100.00%`。
- 本轮已跑完 `26` 个 `rule_version_id`、`208` 个年度规则样本；coverage gating 已通过，可做 retrospective 年度比较，但仍不是生产候选选择。

## Provider 覆盖 gating

| Year | Status | Readable | Required fields | Missing rows | Disabled conclusions |
| --- | --- | --- | --- | --- | --- |
| 2017 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2018 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2019 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2020 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2021 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2022 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2023 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2024 | coverage_ok | 100.00% | 100.00% | 0 |  |
| 2025 | coverage_ok | 100.00% | 100.00% | 0 |  |

### 覆盖缺口行业分布

| Year | Missing rows | Top missing industries |
| --- | --- | --- |
| 2017 | 0 |  |
| 2018 | 0 |  |
| 2019 | 0 |  |
| 2020 | 0 |  |
| 2021 | 0 |  |
| 2022 | 0 |  |
| 2023 | 0 |  |
| 2024 | 0 |  |

## Warmup 与有效交易日

| Year | Warmup partial | First eligible | Data start | Data end |
| --- | --- | --- | --- | --- |
| 2017 | True | 2017-07-31 | 2017-07-04 | 2017-12-29 |
| 2018 | False | 2018-01-02 | 2018-01-02 | 2018-12-28 |
| 2019 | False | 2019-01-02 | 2019-01-02 | 2019-12-31 |
| 2020 | False | 2020-01-02 | 2020-01-02 | 2020-12-31 |
| 2021 | False | 2021-01-04 | 2021-01-04 | 2021-12-31 |
| 2022 | False | 2022-01-04 | 2022-01-04 | 2022-12-30 |
| 2023 | False | 2023-01-03 | 2023-01-03 | 2023-12-29 |
| 2024 | False | 2024-01-02 | 2024-01-02 | 2024-12-31 |

## 年度规则诊断

| Year | Rule version | Entry | Exit | Trades | Return | MDD | Cash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | ema_state_ema60_base__fixed_w05 | ema_state_baseline | ema60_exit_only | 30 | 5.55% | -11.55% | 26.09% |
| 2018 | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | breakdown_repair_diagnostic | fast_failure_exit_diagnostic | 65 | 1.22% | -3.43% | 89.64% |
| 2019 | ema_state_ema60_base__fixed_w05 | ema_state_baseline | ema60_exit_only | 63 | 12.12% | -12.21% | 31.97% |
| 2020 | ema_state_ema60_base__fixed_w05 | ema_state_baseline | ema60_exit_only | 49 | 51.82% | -20.37% | 24.43% |
| 2021 | breakdown_repair_layered_diag__risk_unit_w03_ind20 | breakdown_repair_diagnostic | layered_exit | 94 | 3.66% | -8.08% | 73.86% |
| 2022 | pullback_strict_trend_fast_failure_diag__risk_unit_w03_ind20 | pullback_strict_trend | fast_failure_exit_diagnostic | 7 | -0.60% | -0.64% | 99.68% |
| 2023 | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | breakdown_repair_diagnostic | fast_failure_exit_diagnostic | 137 | 0.88% | -3.99% | 75.53% |
| 2024 | breakout_layered_base__fixed_w05 | breakout_core | layered_exit | 88 | 10.56% | -10.27% | 57.26% |

### 年度诊断最高/最低收益版本

下表是 coverage-ok 年份内的 retrospective 诊断排序；它可以比较规则形态和风险形态，但仍不等同于生产候选选择。
| Year | Diagnostic best | Return | Trades | Cash | Diagnostic worst | Return | Trades |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | ema_state_ema60_base__fixed_w05 | 5.55% | 30 | 26.09% | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | -0.37% | 248 |
| 2018 | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | 1.22% | 65 | 89.64% | breakout_layered_base__fixed_w05 | -6.61% | 28 |
| 2019 | ema_state_ema60_base__fixed_w05 | 12.12% | 63 | 31.97% | breakout_layered_base__fixed_w05 | -7.41% | 84 |
| 2020 | ema_state_ema60_base__fixed_w05 | 51.82% | 49 | 24.43% | breakdown_repair_layered_diag__risk_unit_w03_ind20 | -3.39% | 187 |
| 2021 | breakdown_repair_layered_diag__risk_unit_w03_ind20 | 3.66% | 94 | 73.86% | ema_state_stop_time_base__fixed_w05 | -7.69% | 75 |
| 2022 | pullback_strict_trend_fast_failure_diag__risk_unit_w03_ind20 | -0.60% | 7 | 99.68% | ema_state_ema60_base__fixed_w05 | -11.31% | 32 |
| 2023 | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | 0.88% | 137 | 75.53% | ema_state_stop_time_base__fixed_w05 | -9.46% | 75 |
| 2024 | breakout_layered_base__fixed_w05 | 10.56% | 88 | 57.26% | pullback_original_stop_time_base__fixed_w05 | -4.32% | 74 |

### 规则族横向汇总

| Entry family | Versions | Trades | Net PnL | Median return | Best return | Avg cash | Stop/time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ema_state_baseline | 4 | 1908 | 805,688 | -0.29% | 51.82% | 59.85% | 34.99% |
| breakdown_repair_diagnostic | 2 | 2321 | 37,802 | 0.44% | 3.66% | 74.02% | 31.28% |
| pullback_original | 6 | 1550 | -8,888 | -1.58% | 30.19% | 89.98% | 62.61% |
| pullback_top_score | 2 | 192 | -9,579 | -0.00% | 2.80% | 96.91% | 43.64% |
| pullback_strict_trend | 3 | 277 | -12,374 | -0.05% | 2.80% | 97.70% | 39.19% |
| pullback_strict_money | 2 | 186 | -78,777 | -0.52% | 1.99% | 98.03% | 60.43% |
| breakout_core | 7 | 3815 | -290,205 | -3.00% | 21.98% | 73.19% | 70.48% |

### 仓位套件汇总

| Sizing suite | Sizing family | Trades | Net PnL | Median return | Avg MDD | Avg cash |
| --- | --- | --- | --- | --- | --- | --- |
| fixed_w05 | fixed_weight | 2484 | 403,981 | -2.06% | -11.00% | 66.31% |
| risk_unit_w03_ind20 | risk_unit_with_industry_cap | 6185 | 169,500 | -0.45% | -4.47% | 86.13% |
| risk_unit_w05_ind25 | risk_unit_with_industry_cap | 1580 | -129,814 | -0.92% | -5.21% | 86.50% |

## 年度市场画像

| Year | HS300 Return | HS300 MDD | Width avg | Trend days | Breakout signals | Pullback signals |
| --- | --- | --- | --- | --- | --- | --- |
| 2017 | 20.60% | -6.07% | 65.77% | 97.56% | 162 | 42 |
| 2018 | -26.34% | -31.88% | 35.94% | 11.11% | 75 | 8 |
| 2019 | 37.95% | -13.49% | 61.26% | 59.02% | 208 | 46 |
| 2020 | 25.51% | -16.08% | 57.38% | 72.02% | 382 | 65 |
| 2021 | -6.21% | -18.19% | 51.20% | 26.34% | 164 | 26 |
| 2022 | -21.27% | -28.65% | 40.53% | 11.62% | 78 | 30 |
| 2023 | -11.75% | -21.51% | 46.49% | 22.73% | 163 | 44 |
| 2024 | 16.20% | -14.41% | 61.14% | 50.41% | 274 | 141 |

### 信号密度与市场状态发现

| Year | Breakout | Pullback | Breakdown repair | Industry sync | Money median | Weak-money PB | Top5 industry PnL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2017 | 162 | 42 | 1230 | 32.24% | 0.88 | 54.76% | {"医药生物": 43724.30769739151, "商贸零售": 43682.995394778256, "电子": 81596.13355715273, "社会服务": 42291.48063955307, "食品饮料": 150582.25944232944} |
| 2018 | 75 | 8 | 589 | 9.95% | 0.88 | 25.00% | {"医药生物": 23375.99723262788, "社会服务": 142593.22388534548, "通信": 43367.93176460266, "非银金融": 41076.492964625366, "食品饮料": 156074.8667333603} |
| 2019 | 208 | 46 | 2701 | 28.39% | 0.91 | 45.65% | {"传媒": 44886.93405334949, "农林牧渔": 133048.8050101757, "房地产": 114538.4068430662, "电子": 67693.72344402077, "食品饮料": 99670.75420808786} |
| 2020 | 382 | 65 | 3269 | 34.39% | 0.91 | 60.00% | {"医药生物": 382385.0007536411, "国防军工": 124462.60236396789, "电力设备": 331145.0582727909, "电子": 162871.2342590809, "食品饮料": 543923.0763303756} |
| 2021 | 164 | 26 | 1830 | 36.88% | 0.90 | 50.00% | {"基础化工": 720138.5560435295, "有色金属": 311278.38300901646, "汽车": 610330.3562713623, "电力设备": 326642.39750070573, "食品饮料": 426624.1347477913} |
| 2022 | 78 | 30 | 782 | 20.99% | 0.88 | 53.33% | {"农林牧渔": 1313.8352292060874, "房地产": 908.0082143783562, "煤炭": 70.50053110122326, "石油石化": -1128.5989708900452, "轻工制造": 948.2022045135491} |
| 2023 | 163 | 44 | 1966 | 20.41% | 0.89 | 56.82% | {"医药生物": 242.2941190719671, "国防军工": -62.81399817466881, "石油石化": 81390.38999676706, "计算机": 63552.47652111052, "通信": 170114.72903931144} |
| 2024 | 274 | 141 | 2704 | 29.60% | 0.91 | 51.06% | {"国防军工": 317333.0861759186, "有色金属": 207200.67910832167, "汽车": 201390.36281995775, "石油石化": 106974.88779480458, "计算机": 101865.20052514075} |
- 信号密度最高的年份集中在 `2020` 的 breakout `382` 次和 `2024` 的 pullback `141` 次；这说明 2024 的规则活跃度高，但它仍被 provider coverage 限制在诊断层。

## 入场与退出贡献

| Entry type | Trades | Net PnL | Gross PnL | Win rate | Avg return/trade | Avg hold |
| --- | --- | --- | --- | --- | --- | --- |
| ema_state | 1908 | 805,688 | 954,125 | 27.04% | 1.43% | 30.7 |
| breakdown_repair | 2321 | 37,802 | 167,589 | 33.13% | -0.00% | 12.0 |
| pullback | 2205 | -109,618 | 55,968 | 25.53% | -0.08% | 13.3 |
| breakout | 3815 | -290,205 | -27,119 | 24.48% | -0.15% | 19.1 |

### 亏损最大的入场/退出组合

| Entry | Exit | Trades | Net PnL | Win rate | Avg hold |
| --- | --- | --- | --- | --- | --- |
| breakout | time_stop | 2265 | -3,122,960 | 5.17% | 13.8 |
| pullback | stop_loss | 835 | -1,845,996 | 0.00% | 4.0 |
| breakout | stop_loss | 343 | -1,360,329 | 0.00% | 5.6 |
| ema_state | time_stop | 834 | -1,206,897 | 5.28% | 15.5 |
| breakdown_repair | ema60_exit | 459 | -449,103 | 8.50% | 5.4 |
| breakdown_repair | time_stop | 571 | -438,100 | 5.95% | 13.1 |
| pullback | time_stop | 425 | -347,629 | 6.82% | 12.0 |
| ema_state | stop_loss | 20 | -116,342 | 0.00% | 4.1 |
| breakdown_repair | stop_loss | 45 | -113,293 | 0.00% | 13.1 |
| pullback | fast_ema20_failure | 33 | -10,945 | 21.21% | 7.2 |
| pullback | fast_industry_failure | 7 | 7,860 | 100.00% | 26.3 |
| pullback | fast_relative_failure | 26 | 11,214 | 65.38% | 5.3 |
| breakout | fast_relative_failure | 68 | 12,758 | 52.94% | 7.1 |
| breakdown_repair | fast_relative_failure | 251 | 26,682 | 42.63% | 5.5 |

### 正收益交易集中度

| Entry | Winning trades | Positive PnL | Top5 winner share |
| --- | --- | --- | --- |
| breakdown_repair | 769 | 1,480,179 | 7.01% |
| breakout | 934 | 4,740,173 | 6.38% |
| ema_state | 516 | 4,196,795 | 8.80% |
| pullback | 563 | 2,467,477 | 8.44% |

## 失效归因

| Year | Rule | Entry | Exit | Industry | Trades | Net PnL | Stop/time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 电子 | 2 | -22,997 | 0.00% |
| 2020 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 汽车 | 2 | -22,262 | 0.00% |
| 2023 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 银行 | 2 | -20,599 | 0.00% |
| 2023 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 非银金融 | 3 | -19,835 | 0.00% |
| 2024 | ema_state_ema60_base__fixed_w05 | ema_state | research_end_forced_close | 非银金融 | 3 | -18,653 | 0.00% |
| 2021 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 基础化工 | 1 | -17,903 | 0.00% |
| 2023 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 建筑装饰 | 1 | -16,756 | 0.00% |
| 2023 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 电子 | 1 | -16,739 | 0.00% |
| 2023 | ema_state_stop_time_base__fixed_w05 | ema_state | ema60_exit | 电子 | 2 | -15,890 | 0.00% |
| 2022 | ema_state_stop_time_base__fixed_w05 | ema_state | time_stop | 公用事业 | 3 | -15,652 | 100.00% |
| 2021 | ema_state_stop_time_base__fixed_w05 | ema_state | ema60_exit | 基础化工 | 1 | -15,014 | 0.00% |
| 2020 | ema_state_ema60_base__fixed_w05 | ema_state | ema60_exit | 石油石化 | 1 | -15,007 | 0.00% |
- Pullback 的 `stop_loss + time_stop` 亏损合计为 `-2,218,200`；该值用于判断 pullback 问题是否来自入场质量和失败退出。
- Breakout 交易总数 `3815`，需结合现金比例判断它是低暴露还是可扩展趋势启动信号。

### 失败切片汇总

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

### 亏损行业集中

| Industry | Loss trades | Net PnL |
| --- | --- | --- |
| 食品饮料 | 936 | -1,514,948 |
| 非银金融 | 929 | -1,396,902 |
| 电子 | 573 | -1,181,582 |
| 银行 | 808 | -1,067,773 |
| 电力设备 | 317 | -625,601 |
| 基础化工 | 307 | -617,032 |
| 计算机 | 310 | -603,228 |
| 汽车 | 331 | -594,799 |
| 有色金属 | 283 | -572,779 |
| 医药生物 | 354 | -517,019 |

### 趋势分数 / 成交额 / 初始风险切片

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

## 跨年聚类与 2025 reference

| Year | Cluster | Best rule | Evidence |
| --- | --- | --- | --- |
| 2017 | pullback_failure_year | ema_state_ema60_base__fixed_w05 | best=ema_state_ema60_base__fixed_w05; return=5.55%; trades=30; cash=26.09% |
| 2018 | industry_concentration_year | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | best=breakdown_repair_fast_failure_diag__risk_unit_w03_ind20; return=1.22%; trades=65; cash=89.64% |
| 2019 | pullback_failure_year | ema_state_ema60_base__fixed_w05 | best=ema_state_ema60_base__fixed_w05; return=12.12%; trades=63; cash=31.97% |
| 2020 | industry_concentration_year | ema_state_ema60_base__fixed_w05 | best=ema_state_ema60_base__fixed_w05; return=51.82%; trades=49; cash=24.43% |
| 2021 | industry_concentration_year | breakdown_repair_layered_diag__risk_unit_w03_ind20 | best=breakdown_repair_layered_diag__risk_unit_w03_ind20; return=3.66%; trades=94; cash=73.86% |
| 2022 | pullback_failure_year | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | best=breakdown_repair_fast_failure_diag__risk_unit_w03_ind20; return=-1.35%; trades=73; cash=81.82% |
| 2023 | pullback_failure_year | breakdown_repair_fast_failure_diag__risk_unit_w03_ind20 | best=breakdown_repair_fast_failure_diag__risk_unit_w03_ind20; return=0.88%; trades=137; cash=75.53% |
| 2024 | pullback_failure_year | breakout_layered_base__fixed_w05 | best=breakout_layered_base__fixed_w05; return=10.56%; trades=88; cash=57.26% |
- 2025 reference comparison allowed: `True`；disabled reason: `nan`；similarity year: `2017`。

## 下一步判断

- 若 coverage-ok 年份显示 `trend_continuation_year`，下一阶段优先做 breakout coverage 和 layered exit 验证。
- 若亏损主要来自 pullback + stop/time，应禁用或重写 pullback，而不是继续用 2025 表现外推。
- 若多数有效规则高现金/低交易，应报告 no-edge / high-cash regime，不强行交易。
