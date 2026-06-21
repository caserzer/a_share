# 12A6b C0 Risk-on Fast-fail Survival Uplift Audit Report

## 1. 结论

12A6b 的结论是：

```text
decision_state = 12A6b_c0_fast_fail_survival_uplift_partial
primary_label = no_fast_fail_L10_H20
next_allowed_requirement = requirement_12a6c_fast_fail_scope_or_threshold_revision.md
```

核心判断：

1. C0 risk_on 不是一个已经成立的 fast-fail survival filter。以 primary label `L=-10%, H=20` 计算，C0 的 fast-fail rate 在 train / validation / robustness 都高于 matched random p50。
2. C0 相对 R-core 的 fast-fail rate 更低，说明 C0 比高重复、压力池性质的 R-core 更干净，但这不足以证明 C0 本身有 risk_on survival edge。
3. C0 的 no-fast-fail cohort 明显富集 continuation。也就是说，C0 不像“少输过滤器”，更像“高波动 continuation opportunity”：留下来的样本更容易继续涨，但进入 no-fast-fail 之前的失败率并不低。
4. 90-session dedup 敏感性会显著降低 C0 密度，并把 C0 相对 random p50 的 fast-fail 劣势从 +4.34 pp 压到约 +2.1 至 +2.5 pp；但劣势没有消失，尤其 robustness split 仍明显差于 random。
5. 因此不能直接进入 12A7 fast-fail meta-label training 的 supported 路径。下一步应先写 12A6c，重新讨论 fast-fail scope、barrier、短窗口定义，或者把 C0 作为 continuation source，而不是 survival source。

## 2. 分母与 Baseline 质量

12A6b 只在 `risk_on` scope 内做 headline 判断。

| population | event_n / row_n | entry status | 说明 |
|---|---:|---|---|
| C0 risk_on | 15,113 | 15,113 executable, 0 blocked | 12A2 C0 canonical risk_on primary 分母，计数与需求一致 |
| R-core risk_on | 30,737 | 30,266 executable, 471 blocked | R-core registry headline next-open 后，用 global regime calendar 取 risk_on；存在 471 个 PIT membership missing |
| matched random risk_on | 1,511,300 sampled draws | 1,511,300 executable, 0 blocked | 100 seeds，每 seed 15,113 sampled draws |
| random candidate pool | 415,258 | executable PIT candidates | 按 split / board / month / risk_on 匹配，排除 exact C0 key |

Global regime calendar 通过：真实交易日行 1,911，非日期汇总行 1，regime conflict date 0，multi-regime date 0。

Random baseline 质量较好：100 个 seeds、12,800 个 seed-cell 全部 `ok`，无 replacement，最大 replacement rate = 0。这个 baseline 是本次判断的关键参照，因为它控制了 risk_on、split、board、calendar month 和 PIT executable universe。

R-core baseline 需要谨慎使用：R-core headline next-open 计数 47,849 与需求一致，`47,914 - 47,849 = 65` 的对账也成立；但进入 risk_on 后有 471 个 entry 因 PIT membership 缺失被阻断，所以报告中的 C0 vs R-core 是可用但 degraded 的 diagnostic baseline。

## 3. Primary Fast-fail 结果

Primary label 固定为：

```text
no_fast_fail_L10_H20:
  lower_barrier_pct = -10%
  horizon_sessions = 20
  fast_fail = entry 后 20 sessions 内 low <= entry_price * 0.90
```

### 3.1 Split 读数

| split | C0 n | C0 fast-fail | random p05 / p50 / p95 | R-core fast-fail | C0 - random p50 | C0 - R-core |
|---|---:|---:|---:|---:|---:|---:|
| train | 8,303 | 41.86% | 37.32% / 38.03% / 38.91% | 45.92% | +3.83 pp | -4.05 pp |
| validation | 2,151 | 33.98% | 29.75% / 31.26% / 32.73% | 35.05% | +2.72 pp | -1.07 pp |
| robustness | 4,659 | 30.59% | 23.54% / 24.40% / 25.24% | 35.02% | +6.18 pp | -4.43 pp |

这里的方向非常清楚：C0 比 R-core 少 fast-fail，但比 matched random 多 fast-fail。因为本需求的 survival 主问题是“是否排除 10d/20d fast-fail”，所以 C0 没有通过 support gate。

### 3.2 Retention

| slice | C0 complete_n | fast-fail | no-fast-fail retention |
|---|---:|---:|---:|
| all risk_on | 15,113 | 37.27% | 62.73% |
| train | 8,303 | 41.86% | 58.14% |
| validation | 2,151 | 33.98% | 66.02% |
| robustness | 4,659 | 30.59% | 69.41% |
| chinext | 3,115 | 48.92% | 51.08% |
| main_board | 11,998 | 34.24% | 65.76% |

Retention gate 本身是通过的，所有 headline split 都高于 50%。问题不是 C0 太激进，而是 matched random 在同样 risk_on / board / month 条件下保留得更多。

### 3.3 Fast-fail 不是只发生在 entry 当日

`L=-10%, H=20` 下，C0 all risk_on fast-fail 的 median time-to-fast-fail 是 8 sessions，p75 是 13 sessions。对照 random p50 是 median 9 / p75 14，R-core 是 median 8 / p75 13。

这说明 fast-fail 风险不是一个“开仓当天是否极端下杀”的问题，而是 20d 窗口中的持续下行风险。12A6b 的 no-fast-fail label 捕捉的是短周期持有稳定性，不只是 entry-bar 风险。

## 4. Barrier Grid

在全 risk_on 分母上，C0 对 random 的 fast-fail 劣势跨所有 tested lower barrier 都存在。

### 4.1 H=10

| lower | C0 fast-fail | random p50 | R-core | C0 - random p50 | C0 - R-core |
|---:|---:|---:|---:|---:|---:|
| -6% | 44.59% | 39.30% | 48.69% | +5.29 pp | -4.10 pp |
| -8% | 32.36% | 27.47% | 36.13% | +4.88 pp | -3.78 pp |
| -10% | 22.95% | 19.09% | 26.40% | +3.86 pp | -3.45 pp |
| -12% | 15.87% | 13.16% | 18.73% | +2.72 pp | -2.86 pp |
| -15% | 9.19% | 7.45% | 11.04% | +1.74 pp | -1.84 pp |
| -20% | 3.45% | 2.72% | 4.25% | +0.73 pp | -0.80 pp |

### 4.2 H=20

| lower | C0 fast-fail | random p50 | R-core | C0 - random p50 | C0 - R-core |
|---:|---:|---:|---:|---:|---:|
| -6% | 58.10% | 53.57% | 61.80% | +4.53 pp | -3.70 pp |
| -8% | 47.02% | 42.36% | 50.67% | +4.66 pp | -3.65 pp |
| -10% | 37.27% | 32.93% | 40.89% | +4.34 pp | -3.62 pp |
| -12% | 29.23% | 25.19% | 32.40% | +4.05 pp | -3.17 pp |
| -15% | 19.80% | 16.54% | 22.14% | +3.26 pp | -2.34 pp |
| -20% | 9.53% | 7.32% | 10.72% | +2.21 pp | -1.19 pp |

Insight：如果只是调整 lower barrier，不能把 C0 变成 random-uplift 的 survival filter。barrier 越宽，fast-fail rate 会自然下降，但 C0 相对 random 的劣势仍然存在。

## 5. Conditional Continuation

虽然 C0 的 fast-fail 风险高于 random，但一旦进入 `no_fast_fail_L10_H20` cohort，C0 的 continuation 明显强于 random。

### 5.1 全 risk_on

| upper | total upper touch | given no-fast-fail | random p50 given no-fast-fail | R-core given no-fast-fail | conditional uplift vs total |
|---:|---:|---:|---:|---:|---:|
| +10% | 41.12% | 53.64% | 47.56% | 57.62% | 1.30x |
| +15% | 26.45% | 36.20% | 31.32% | 40.31% | 1.37x |
| +20% | 17.79% | 25.06% | 20.69% | 27.99% | 1.41x |
| +25% | 12.12% | 17.47% | 14.03% | 19.44% | 1.44x |
| +30% | 8.47% | 12.40% | 9.79% | 13.46% | 1.46x |

no-fast-fail 后 continuation 的确被富集：upper 越高，conditional uplift vs total 越大。这是 12A6b 得到 partial 而不是 no-uplift 的主要原因。

### 5.2 Split 读数

| split | upper | C0 given no-fast-fail | random p50 | random p05 | R-core |
|---|---:|---:|---:|---:|---:|
| train | +10% | 62.17% | 55.97% | 54.74% | 67.29% |
| train | +15% | 43.73% | 39.32% | 38.22% | 50.00% |
| train | +20% | 31.39% | 27.07% | 26.20% | 35.75% |
| validation | +10% | 38.24% | 32.96% | 30.95% | 39.77% |
| validation | +15% | 21.97% | 17.33% | 16.12% | 23.05% |
| validation | +20% | 11.76% | 9.51% | 8.56% | 13.19% |
| robustness | +10% | 47.68% | 41.66% | 40.53% | 52.13% |
| robustness | +15% | 31.20% | 25.59% | 24.51% | 34.50% |
| robustness | +20% | 21.46% | 16.05% | 15.19% | 23.81% |

C0 的 conditional continuation 在 train / validation / robustness 都优于 random，但仍低于 R-core。这说明 C0 的优势不是“比 R-core 更会抓后续上涨”，而是“比 R-core 少一些快速失败，同时又保留了一部分 continuation 结构”。

## 6. Board / Year / Family 结构

### 6.1 Board

| board | C0 n | C0 fast-fail | random p50 | R-core | C0 - random p50 | C0 - R-core |
|---|---:|---:|---:|---:|---:|---:|
| chinext | 3,115 | 48.92% | 44.45% | 51.29% | +4.48 pp | -2.37 pp |
| main_board | 11,998 | 34.24% | 29.92% | 38.13% | +4.32 pp | -3.89 pp |

Chinext 的 fast-fail 明显更高，但 no-fast-fail 后 continuation 也更强：+10% conditional continuation 为 72.03%，+15% 为 54.05%，+20% 为 41.42%。Main board 对应为 49.94%、32.60%、21.76%。

Insight：C0 的 board 差异更像波动率/弹性差异，而不是 survival 质量差异。Chinext 既更容易失败，也更容易在幸存后继续上冲。

### 6.2 Year

`L=-10%, H=20` 下：

| year | C0 n | C0 fast-fail | random p50 | R-core | C0 - random p50 | C0 - R-core |
|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 344 | 73.26% | 75.87% | 73.23% | -2.62 pp | +0.02 pp |
| 2019 | 2,189 | 32.66% | 28.23% | 35.52% | +4.43 pp | -2.86 pp |
| 2020 | 3,083 | 43.43% | 37.71% | 46.82% | +5.72 pp | -3.39 pp |
| 2021 | 2,687 | 43.54% | 41.72% | 50.96% | +1.82 pp | -7.42 pp |
| 2022 | 749 | 41.39% | 36.58% | 40.91% | +4.81 pp | +0.48 pp |
| 2023 | 1,402 | 30.03% | 28.60% | 31.39% | +1.43 pp | -1.36 pp |
| 2024 | 2,039 | 35.65% | 30.31% | 39.74% | +5.35 pp | -4.09 pp |
| 2025 | 2,620 | 26.64% | 19.89% | 31.28% | +6.76 pp | -4.64 pp |

2018 是唯一 C0 低于 random 的年份，但样本只有 344，且几乎不优于 R-core。2025 的 fast-fail 绝对水平最低，但相对 random 的劣势最大。说明市场环境改善会降低所有 population 的 fast-fail，但 C0 相对 random 的 survival edge 没有自然出现。

### 6.3 Family Diagnostic

Family slice 是 C0-only diagnostic，不与 random / R-core 做 headline uplift。

| family | C0 n | fast-fail | no-fast-fail | median / p75 time-to-fast-fail |
|---|---:|---:|---:|---:|
| B1 | 1,990 | 38.39% | 61.61% | 8 / 12 |
| B2 | 1,946 | 28.98% | 71.02% | 9 / 13 |
| B3 | 1,417 | 30.20% | 69.80% | 10 / 14 |
| B4 | 307 | 58.96% | 41.04% | 5 / 10 |
| B5 | 6,286 | 37.97% | 62.03% | 9 / 14 |
| B6 | 989 | 45.20% | 54.80% | 7 / 13 |
| B8 | 2,178 | 39.53% | 60.47% | 8 / 13 |

B2 / B3 的 fast-fail 最低，B4 明显最差，但 B4 样本只有 307，且 requirement 已规定 per-family 不能参与 headline gate。下一步如果做 12A6c，可以把 B2/B3 作为机制假设，但不能在本阶段事后选择 family 作为支持结论。

## 7. 90-day Dedup Sensitivity

本节是 post-run sensitivity，不替代 12A6b 的 predeclared headline gate。口径为同一 `instrument` 触发 C0 后，在 cooldown 窗口内不再接受后续 C0；matched random p50 按 dedup 后的 split / board / calendar-month cell count 重新对齐样本量。

这里保留两个 trading-session 口径：

- `risk_on-only 90-session dedup`：只在 risk_on C0 分母内部做同 instrument 90 个交易 session cooldown；
- `all-C0 stream 90-session dedup then risk_on`：先对全 regime C0 信号流做 cooldown，再取 risk_on 子集；这个口径更接近真实信号占用，因为 transition / risk_off 的早期 C0 也会占用后续 risk_on cooldown。

### 7.1 Headline Readout

| 口径 | C0 n | retained vs original risk_on | C0 fast-fail | matched random p50 | C0 - random p50 | no-fast-fail | +10% given no-fast-fail | random p50 | +20% given no-fast-fail | random p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| original risk_on no dedup | 15,113 | 100.0% | 37.27% | 32.93% | +4.34 pp | 62.73% | 53.64% | 47.56% | 25.06% | 20.69% |
| risk_on-only 90-session dedup | 6,624 | 43.8% | 34.10% | 31.60% | +2.50 pp | 65.90% | 53.52% | 48.54% | 25.75% | 21.40% |
| all-C0 stream 90-session dedup then risk_on | 4,479 | 29.6% | 36.79% | 34.72% | +2.08 pp | 63.21% | 52.49% | 47.83% | 25.11% | 21.00% |

Dedup 的作用很清楚：它主要去掉同一股票上的密集重复触发，使 risk_on 分母从 15,113 降到 6,624，或者在全 C0 信号流 cooldown 后降到 4,479。fast-fail 劣势也随之收窄，但没有反转。C0 仍高于同 cell 匹配的 random p50，因此 dedup 只能解释一部分 fast-fail 劣势，不能把 C0 改写成 standalone survival filter。

同时，dedup 后 continuation 价值仍然保留。risk_on-only 90-session dedup 下，`+10% given no-fast-fail` 为 53.52%，仍高于 random p50 的 48.54%；`+20% given no-fast-fail` 为 25.75%，也高于 random p50 的 21.40%。这说明 cooldown 更像 density hygiene，而不是 survival edge 的充分条件。

### 7.2 Split Readout

| 口径 | split | C0 n | C0 fast-fail | matched random p50 | C0 - random p50 | +10% given no-fast-fail | random p50 |
|---|---|---:|---:|---:|---:|---:|---:|
| risk_on-only 90-session dedup | train | 3,544 | 36.65% | 35.10% | +1.55 pp | 61.74% | 56.92% |
| risk_on-only 90-session dedup | validation | 1,146 | 31.85% | 30.98% | +0.87 pp | 38.67% | 31.79% |
| risk_on-only 90-session dedup | robustness | 1,934 | 30.77% | 25.65% | +5.12 pp | 48.39% | 44.51% |
| all-C0 stream 90-session dedup then risk_on | train | 2,572 | 41.02% | 40.14% | +0.87 pp | 59.39% | 55.60% |
| all-C0 stream 90-session dedup then risk_on | validation | 605 | 33.06% | 33.22% | -0.17 pp | 38.52% | 34.32% |
| all-C0 stream 90-session dedup then risk_on | robustness | 1,302 | 30.18% | 24.73% | +5.45 pp | 47.19% | 41.28% |

Split 层面，dedup 对 train / validation 的改善最明显：risk_on-only 口径下，train 劣势从 +3.83 pp 缩到 +1.55 pp，validation 从 +2.72 pp 缩到 +0.87 pp；all-C0 stream 口径下，validation 甚至略低于 random p50。但 robustness 仍差 5 pp 以上，说明后期样本中的 fast-fail 劣势不是单纯由同股票重复触发造成的。

### 7.3 Board And Family Readout

| 口径 | board | C0 n | C0 fast-fail | matched random p50 | C0 - random p50 | +10% given no-fast-fail | random p50 |
|---|---|---:|---:|---:|---:|---:|---:|
| risk_on-only 90-session dedup | chinext | 1,337 | 47.42% | 43.42% | +4.00 pp | 72.12% | 67.35% |
| risk_on-only 90-session dedup | main_board | 5,287 | 30.74% | 28.61% | +2.13 pp | 49.95% | 44.86% |
| all-C0 stream 90-session dedup then risk_on | chinext | 892 | 48.99% | 44.67% | +4.32 pp | 71.65% | 65.91% |
| all-C0 stream 90-session dedup then risk_on | main_board | 3,587 | 33.76% | 32.27% | +1.49 pp | 48.82% | 44.20% |

Board 结构没有被 dedup 改写。Chinext 仍然是高 fast-fail、高 continuation 的弹性池；main_board 的 fast-fail 劣势更容易被 cooldown 压低，但仍没有稳定转正。

Primary family 的 risk_on-only 90-session dedup 读数如下：

| family | C0 n | fast-fail | +10% total upper | +10% given no-fast-fail | both -10% and +10% | median min low | median max high |
|---|---:|---:|---:|---:|---:|---:|---:|
| B4 | 126 | 65.08% | 50.00% | 88.64% | 19.05% | -13.80% | 9.87% |
| B6 | 314 | 42.36% | 40.76% | 53.04% | 10.19% | -8.34% | 7.70% |
| B8 | 907 | 38.26% | 44.10% | 58.39% | 8.05% | -7.98% | 8.31% |
| B1 | 712 | 34.97% | 41.71% | 53.56% | 6.88% | -7.33% | 8.09% |
| B5 | 2,824 | 34.49% | 43.27% | 55.35% | 7.01% | -6.79% | 8.32% |
| B3 | 784 | 27.42% | 42.22% | 53.78% | 3.19% | -5.52% | 7.44% |
| B2 | 957 | 27.06% | 35.42% | 42.41% | 4.49% | -5.02% | 6.93% |

Family 层面，B2 / B3 在 dedup 后仍是相对更干净的 family，B4 / B6 / B8 仍偏高波动。B5 是最大样本来源，dedup 后 fast-fail 从原始 37.97% 降至 34.49%，但它仍不是低失败 family；更合理的解释是 B5 提供了大量 continuation opportunity，同时也带来明显的 path volatility。

### 7.4 90 Calendar-day Sensitivity

如果把“90天”解释为 90 个自然日，而不是 90 个交易 session，结论仍一致。

| 口径 | C0 n | retained vs original risk_on | C0 fast-fail | matched random p50 | C0 - random p50 | +10% given no-fast-fail | random p50 | +20% given no-fast-fail | random p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| risk_on-only 90-calendar-day dedup | 7,791 | 51.6% | 34.48% | 31.73% | +2.75 pp | 51.40% | 47.04% | 23.66% | 20.33% |
| all-C0 stream 90-calendar-day dedup then risk_on | 5,909 | 39.1% | 35.98% | 33.62% | +2.36 pp | 52.15% | 47.07% | 24.29% | 20.52% |

自然日 cooldown 保留的样本更多，所以 fast-fail 劣势略大于 90-session 口径。但方向不变：dedup 是必要的密度控制和评估卫生，不是足以通过 support gate 的 survival 修复。

## 8. Findings

1. C0 的 primary survival uplift 不成立。C0 在 `L=-10%, H=20` 下比 random p50 多 4.34 pp fast-fail；train、validation、robustness 分别多 3.83、2.72、6.18 pp。
2. C0 比 R-core 更少 fast-fail。全 risk_on 少 3.62 pp，train 少 4.05 pp，robustness 少 4.43 pp。这证明 C0 比 R-core 这个高重复 stress pool 干净，但不能替代 random baseline 的结论。
3. no-fast-fail 后 continuation 很强。全 risk_on 下，+10%、+15%、+20% conditional continuation 分别为 53.64%、36.20%、25.06%，均高于 random p50。
4. C0 的问题是“先活下来”而不是“活下来之后没有机会”。这与 12A6 的 upper-first 读数相吻合：upper-first 结构存在，但 survival 主标签不能直接用 upper-first 替代。
5. 90-session dedup 能显著降低密度和部分 fast-fail 劣势，但不能改变 support gate。risk_on-only dedup 后 C0 仍比 random p50 多 2.50 pp fast-fail；all-C0 stream dedup 后仍多 2.08 pp。
6. Board 和 year 的结构说明 C0 更像高弹性买点。Chinext 更容易 fast-fail，也更容易在幸存后 continuation；2025 绝对 fast-fail 低，但 random 更低。
7. R-core baseline degraded，但不改变主判断。C0 vs random 是独立且高质量的 matched baseline；即使完全忽略 R-core，C0 也没有通过 fast-fail support gate。

## 9. Insight

12A6b 把问题拆清楚后，C0 的角色更明确了：

```text
C0 is not a standalone short-horizon survival filter.
C0 is a continuation-opportunity source that still needs a fast-fail rejector.
```

如果后续建模目标是“10d/20d 内不要快速失败”，不能只拿 C0 event 本身当 positive source。更合理的方向是：

1. 保留 C0 作为 candidate source；
2. 在 C0 内训练或设计一个 fast-fail rejector，目标是降低 `L=-10%, H=20` 的 early failure；
3. 引入同 instrument cooldown / event dedup 作为密度卫生，但不能把它当成 survival edge 的替代证据；
4. 只在 no-fast-fail / low-fast-fail-risk cohort 内读取 continuation；
5. 12A7 不能直接承接为 supported meta-label training，必须先走 12A6c 修订 threshold / scope / rejector framing。

换句话说，12A6 的 upper-first 结果不是错，而是回答了另一个问题：C0 中有 continuation morphology。12A6b 证明的是：这个 morphology 不能被误读成“C0 自带 survival uplift”。

## 10. 下一步

建议下一步进入：

```text
requirement_12a6c_fast_fail_scope_or_threshold_revision.md
```

12A6c 应重点评估：

1. 是否把 primary fast-fail label 从 `L=-10%, H=20` 改成更短的 `H=10` 或更宽/更窄的 lower barrier；
2. 是否把同 instrument cooldown / dedup 纳入正式候选生成或评估 hygiene，但仍用 matched random 做独立 support gate；
3. 是否单独建 fast-fail rejector，而不是继续寻找一个 C0-only survival definition；
4. 是否把 B2/B3、main_board、特定年份作为 diagnostic hypotheses，而不是 headline selection；
5. 是否把 continuation readout 从 support gate 中拆出来，作为 C0 candidate source 的二阶段价值证明。

当前阶段不建议进入 `requirement_12a7_c0_fast_fail_survival_meta_label_feasibility.md` 的 supported 路径。
