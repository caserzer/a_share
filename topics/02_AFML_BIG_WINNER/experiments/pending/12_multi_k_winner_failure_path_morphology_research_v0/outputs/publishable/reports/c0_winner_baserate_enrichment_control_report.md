# 12A7f C0 Winner Base-rate Enrichment Control Diagnostic

## 裁决

`12A7f` 的最终状态是：

```text
decision_state = 12A7f_c0_winner_enrichment_weak_or_horizon_dependent
c0_winner_enrichment_status = weak_or_horizon_dependent_enrichment
recommended_internal_followup = winner_label_form_revision_with_c0_fitness_recheck
```

这个结果的含义不是“C0 完全不富集 winner”，而是更窄：C0 在部分右尾 barrier 上有正向 enrichment，但未同时通过两个 primary direct-entry big-winner horizon。因此它不能被标成强 `c0_winner_enriched_event_supported`。下一步应回到 winner label 形态与 C0 适配性，而不是直接继续堆 stage-2 selector 容量。

## Scope And Matching

| item | value |
|---|---:|
| C0 primary scope rows | 15113 |
| C0 distinct instruments | 1310 |
| control eligible rows before sampling | 420264 |
| control eligible distinct instruments | 1546 |
| canonical control sample rows | 15113 |
| canonical control sample instruments | 1272 |
| matched cells | 128 |
| control_short cells | 0 |
| control_zero cells | 0 |
| matched_c0_entry_coverage | 1.0000 |

配对是 clean 的：所有 `split x board_bucket x calendar_month x risk_on` cell 都能构造同量控制组，没有因控制组不足触发 fallback。控制组使用 `control_decision_date = source_membership_date` 派生 split/month/regime，使用 `control_entry_date = usable_trade_date` 的 qfq open 作为 entry reference，因此没有把 event close 与 next open 的时间轴混用。

Label source audit 也完整：C0 与 control 的 direct-entry label 都由 12A7f 在同一 qfq 日线上重算；C0 的 post-survivor continuation 复用 12A6c `stage_2_reference_pos` 口径，control 的 post-survivor continuation 用 `entry_pos + 21` 重算。所有 label family 的 horizon completeness rate 都是 1.0000。

## Primary Readout: Direct-entry Unconditional

Primary 裁决只看 `label_family = direct_entry`、`readout_view = unconditional`。也就是从 event 入场点直接问：C0 入场后是否比同 cell 控制组更容易先触达 upper barrier。

| split | barrier | c0_n | C0 rate | control rate | diff | CI95 | status |
|---|---|---:|---:|---:|---:|---|---|
| all | +10% / 20d | 15113 | 0.3823 | 0.3543 | 0.0279 | [0.0107, 0.0464] | positive |
| train | +10% / 20d | 8303 | 0.4191 | 0.3961 | 0.0230 | [-0.0002, 0.0465] | uncertain |
| validation | +10% / 20d | 2151 | 0.2762 | 0.2390 | 0.0372 | [-0.0132, 0.0986] | uncertain |
| robustness | +10% / 20d | 4659 | 0.3655 | 0.3331 | 0.0324 | [-0.0000, 0.0628] | uncertain |
| all | +15% / 20d | 15113 | 0.2446 | 0.2241 | 0.0204 | [0.0042, 0.0357] | positive |
| train | +15% / 20d | 8303 | 0.2760 | 0.2647 | 0.0113 | [-0.0109, 0.0349] | uncertain |
| validation | +15% / 20d | 2151 | 0.1511 | 0.1199 | 0.0311 | [0.0025, 0.0585] | positive |
| robustness | +15% / 20d | 4659 | 0.2316 | 0.1998 | 0.0318 | [0.0066, 0.0560] | positive |
| all | +20% / 20d | 15113 | 0.1650 | 0.1452 | 0.0198 | [0.0080, 0.0310] | uncertain |
| train | +20% / 20d | 8303 | 0.1928 | 0.1766 | 0.0163 | [0.0005, 0.0330] | uncertain |
| validation | +20% / 20d | 2151 | 0.0790 | 0.0711 | 0.0079 | [-0.0138, 0.0290] | uncertain |
| robustness | +20% / 20d | 4659 | 0.1552 | 0.1236 | 0.0316 | [0.0109, 0.0522] | positive |
| all | +20% / 40d | 15113 | 0.2442 | 0.2279 | 0.0162 | [0.0028, 0.0305] | uncertain |
| train | +20% / 40d | 8303 | 0.2729 | 0.2653 | 0.0076 | [-0.0099, 0.0260] | uncertain |
| validation | +20% / 40d | 2151 | 0.1446 | 0.1241 | 0.0205 | [-0.0079, 0.0497] | uncertain |
| robustness | +20% / 40d | 4659 | 0.2389 | 0.2093 | 0.0296 | [-0.0000, 0.0597] | uncertain |

关键点：

1. Robustness 的 `+20% / 20d` 是明确正向：C0 15.52%，control 12.36%，diff +3.16pp，CI 下沿 +1.09pp。
2. Robustness 的 `+20% / 40d` 也是正向，但 CI 下沿贴近 0，不能作为强支持。
3. `+15% / 20d` 比 `+20% / 40d` 更稳定：robustness diff +3.18pp，CI [0.66pp, 5.60pp]。
4. `all` 样本上的 +20% barrier 虽然 CI 多数为正，但 diff 没过 `+2pp` material gate，因此仍标为 uncertain。这是方法学纪律：弱幅度不升级成强结论。

## Fast-fail Contrast

| split | C0 entry_n | C0 survivor_n | control survivor_n | C0 fast-fail | control fast-fail | diff |
|---|---:|---:|---:|---:|---:|---:|
| all | 15113 | 9481 | 10102 | 0.3727 | 0.3316 | 0.0411 |
| train | 8303 | 4827 | 5133 | 0.4186 | 0.3818 | 0.0369 |
| validation | 2151 | 1420 | 1459 | 0.3398 | 0.3217 | 0.0181 |
| robustness | 4659 | 3234 | 3510 | 0.3059 | 0.2466 | 0.0592 |

这是本次诊断最重要的结构性发现：C0 原始 event 相对控制组不只是右尾更厚，左尾 fast-fail 也更厚。Robustness 中 C0 fast-fail 比控制组高 5.92pp。也就是说，C0 更像“尾部放大器”或“波动机会集合”，而不是天然的 winner-only event。

这也解释了为什么 12A7e 中 X=0.30 的 downside defense 仍有价值：如果不先做 stage-1 防守，C0 event 本身会引入额外左尾风险。Winner enrichment 与 downside control 必须拆开看。

## Survivor-conditional Readout

在 no-fast-fail survivor 内，C0 的 winner enrichment 更明显。这说明 stage-1 防守过滤掉左尾后，C0 的右尾信息才更干净。

| split | barrier | C0 survivor_n | C0 rate | control rate | diff | CI95 | status |
|---|---|---:|---:|---:|---:|---|---|
| all | +20% / 20d | 9481 | 0.2506 | 0.2092 | 0.0407 | [0.0248, 0.0579] | positive |
| train | +20% / 20d | 4827 | 0.3139 | 0.2755 | 0.0358 | [0.0114, 0.0633] | positive |
| validation | +20% / 20d | 1420 | 0.1176 | 0.1001 | 0.0209 | [-0.0099, 0.0558] | uncertain |
| robustness | +20% / 20d | 3234 | 0.2146 | 0.1575 | 0.0567 | [0.0304, 0.0830] | positive |
| all | +20% / 40d | 9481 | 0.3768 | 0.3329 | 0.0431 | [0.0230, 0.0641] | positive |
| train | +20% / 40d | 4827 | 0.4516 | 0.4191 | 0.0296 | [0.0019, 0.0597] | positive |
| validation | +20% / 40d | 1420 | 0.2169 | 0.1782 | 0.0434 | [0.0048, 0.0906] | positive |
| robustness | +20% / 40d | 3234 | 0.3352 | 0.2712 | 0.0631 | [0.0287, 0.0984] | positive |

Insight：如果问题改成“已经活过 20d fast-fail 的 C0 survivor 是否更容易继续走右尾”，答案明显更偏 positive。但这不是 primary event-level 裁决，因为它把 stage-1 防守作为前置条件了。它支持“C0 + 防守过滤 + 重新定义 winner label/continuation”的路线，而不是支持裸 C0 event 可直接部署。

## Post-survivor Continuation Reconciliation

这个视角使用 12A6c stage-2 reference-point：从 survivor 后的 `stage_2_reference_pos` 起算 continuation，不与 direct-entry 混用。

| split | continuation barrier | C0 n | C0 rate | control rate | diff | CI95 | status |
|---|---|---:|---:|---:|---:|---|---|
| all | U10/L10/H2/20 | 9481 | 0.3551 | 0.3177 | 0.0365 | [0.0172, 0.0556] | positive |
| robustness | U10/L10/H2/20 | 3234 | 0.3528 | 0.2986 | 0.0507 | [0.0141, 0.0847] | positive |
| all | U15/L10/H2/20 | 9481 | 0.2200 | 0.1947 | 0.0254 | [0.0088, 0.0421] | positive |
| robustness | U15/L10/H2/20 | 3234 | 0.2180 | 0.1806 | 0.0359 | [0.0058, 0.0662] | positive |
| all | U20/L10/H2/20 | 9481 | 0.1383 | 0.1225 | 0.0159 | [0.0026, 0.0299] | uncertain |
| robustness | U20/L10/H2/20 | 3234 | 0.1345 | 0.1094 | 0.0239 | [0.0003, 0.0475] | positive |
| all | U20/L10/H2/40 | 9481 | 0.2130 | 0.1994 | 0.0135 | [-0.0040, 0.0307] | uncertain |
| robustness | U20/L10/H2/40 | 3234 | 0.2319 | 0.2003 | 0.0288 | [-0.0009, 0.0581] | uncertain |

Post-survivor 对账与 direct-entry 的结论方向一致：C0 在 survivor 后有 continuation enrichment，但越往 big-winner / long-horizon 推，CI 越贴近 0。它支持“event 不是完全选错”，但仍不支持“stage-2 selector 已经有强可部署信号”。

## Stability Slices

### Board

| board | barrier | C0 n | control n | C0 rate | control rate | diff | direction |
|---|---|---:|---:|---:|---:|---:|---|
| chinext | +20% / 20d | 3115 | 3115 | 0.2276 | 0.2128 | 0.0148 | positive |
| chinext | +20% / 40d | 3115 | 3115 | 0.2957 | 0.2873 | 0.0083 | positive |
| main_board | +20% / 20d | 11998 | 11998 | 0.1488 | 0.1277 | 0.0211 | positive |
| main_board | +20% / 40d | 11998 | 11998 | 0.2308 | 0.2125 | 0.0183 | positive |

Board 上没有方向反转，但 chinext 的 +20% enrichment 较弱，main_board 的 +20% / 20d 更接近 material threshold。C0 的富集不是由单一 board 完全驱动，但强度并不均匀。

### Calendar Year

| year | +20% / 20d diff | +20% / 40d diff | note |
|---:|---:|---:|---|
| 2018 | 0.0145 | 0.0000 | long horizon flat |
| 2019 | 0.0078 | 0.0014 | weak |
| 2020 | 0.0178 | 0.0019 | weak |
| 2021 | 0.0216 | 0.0201 | both near material |
| 2022 | 0.0027 | 0.0067 | weak |
| 2023 | 0.0107 | 0.0278 | 40d stronger |
| 2024 | 0.0343 | 0.0231 | strong recent enrichment |
| 2025 | 0.0294 | 0.0347 | strong recent enrichment |

年度切片显示，右尾 enrichment 近年更强：2024/2025 的两个 primary horizon 都为正且幅度较大；2018-2020 较弱，2022 也弱。这提示固定 +20% barrier 可能存在 regime/time variation，后续 label 层不应只做一个全样本固定 threshold。

## Interpretation

本诊断把 12A7e 之后的疑问拆成两个层次：

1. C0 event 是否完全选错人群？
2. 如果没完全选错，为什么 stage-2 winner selector 仍然失败？

当前证据更支持第二种解释。C0 相对控制组确实有右尾 enrichment，尤其在 robustness 的 +20% / 20d、+15% / 20d，以及 survivor-conditional / post-survivor continuation 视角里。但 C0 同时显著增加 fast-fail，且 +20% / 40d 没有过强支持门槛。这说明裸 C0 event 不是一个干净的 winner selector，而是把左右两侧尾部都放大了。

这与前序结果是连贯的：

- 12A7e 看到 stage-1 X 更像 participation throttle，不是 winner separator。
- 12A7f 进一步显示，C0 原始 event 的右尾信息存在，但左尾风险也更高。
- 因此，问题不应简化为“C0 选错了”或“stage-2 模型容量不够”。更准确的说法是：C0 提供了一个高波动、高机会、高风险的候选池；需要先用 defense overlay 清掉左尾，再重新定义右尾 label / continuation target。

## Decision Logic

`enriched_event_supported` 要求 robustness 下两个 primary direct-entry big-winner barrier 都 positive：

```text
direct_entry_win_up_20_h20 = positive_for_barrier
direct_entry_win_up_20_h40 = positive_for_barrier
```

实际结果是：

```text
direct_entry_win_up_20_h20 = positive_for_barrier
direct_entry_win_up_20_h40 = uncertain_for_barrier
direct_entry_win_up_15_h20 = positive_for_barrier
```

所以最终只能落在：

```text
12A7f_c0_winner_enrichment_weak_or_horizon_dependent
```

这个状态保留 C0，但不允许把 C0 直接升级成强 big-winner event。后续应优先做：

1. winner label 形态重审：固定 +20% / -10% / H20-H40 可能过粗，且存在年度/regime 漂移。
2. C0 fitness recheck：确认 C0 是不是更适合“survivor 后 continuation”而不是“entry 后 naked winner”。
3. 架构拆分：stage-1 defense 与 winner-capture objective 分离，不再要求同一个 X 同时承担防守与右尾捕获。
4. 暂不把本诊断解释成 stage-2 selector 支持；它只证明 event-level / survivor-level base-rate enrichment 的存在与边界。
