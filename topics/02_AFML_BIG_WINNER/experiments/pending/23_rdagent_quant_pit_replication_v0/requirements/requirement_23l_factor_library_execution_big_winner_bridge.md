# Requirement 23L：因子/模型进化的 Next-Open 与 Big Winner Bridge

> 状态：`implementation_authorized_after_23k`
>
> 上游：23H 静态候选、23I evolved candidates、23K model candidates 均已在
> 不读取 historical-test 的条件下冻结

## 1. Estimand

每个 evolved branch 只与自己的 frozen start 做 matched comparison：

```text
evolved A20 factors - static A20
evolved A157 factors - static A157 adaptation
evolved A20 model - frozen A20 model baseline
conditional evolved-library model - its own frozen model baseline
```

禁止跨起点挑选对自己有利的 baseline。23L 首次揭示
2024-01-02..2026-05-27 historical-test，因此结果身份固定为：

```text
design_contaminated_historical_real_market_evidence
not production authorization
```

## 2. 输入冻结

候选必须在 2023 confirmation 后已经冻结，并包含：

- feature/model code hash；
- library hash；
- five-seed confirmation metrics；
- seed selection rule；
- model runtime config；
- score 文件 schema；
- 冻结时间早于 23L historical-test 读取时间。

23L 不允许根据 historical-test 或 Big Winner 结果更换候选、seed、阈值、
TopK/dropout、成本或 taxonomy。

## 3. 执行语义

复用 23F 状态机和冻结参数：

- close t 形成 score；
- next tradable open 执行；
- next-session dynamic membership；
- 停牌、ST、上市/退市状态；
- 涨跌停可买/可卖；
- TopK/dropout；
- 买卖佣金、印花税、最低佣金、滑点；
- benchmark 和 PIT universe 等权；
- 订单失败、延迟成交、持仓延续；
- turnover 与 capacity proxy。

任何语义差异必须形成 adapter diff 和 reconciliation，不得静默近似。

## 4. Economic metrics

五 seed 分列与中位数至少报告：

- gross/net ARR；
- IR/Sharpe/Calmar；
- MDD；
- turnover；
- total cost；
- fill/fail/delay rate；
- win rate；
- top/bottom contribution concentration；
- rolling/annual stability；
- benchmark excess；
- PIT universe equal-weight excess。

gate 使用 matched seed delta，不使用挑选 seed 的单点结果。

## 5. Big Winner metrics

复用项目冻结 episode/taxonomy，至少输出：

- winner episode recall；
- right-tail exposure rate；
- right-tail enrichment；
- severe-left-tail exposure；
- winner/non-winner score separation；
- early/middle/late lifecycle coverage；
- morphology capture share；
- single-morphology concentration；
- missed winner 与 false-positive episode 清单；
- score decile 的 right/left-tail 条件分布。

如果信号不适合作 standalone selector，按证据降级为：

```text
risk_overlay_candidate
participation_filter_candidate
meta_label_candidate
no_incremental_utility
```

## 6. Gate

`big_winner_selector_increment_supported` 必须同时满足：

1. right-tail enrichment `> 1.0`；
2. winner recall 相对自身静态 baseline 正增量；
3. severe-left-tail 不超过预注册容忍；
4. 覆盖不集中在单一 morphology；
5. next-open 成本后结果不符号反转；
6. 改善至少 4/5 seeds 同方向；
7. 不由单股、单日或单 episode 主导。

`evolution_supported` 的经济部分要求 next-open 净 ARR 或风险收益至少一项改善，
且另一项无重大恶化。

## 7. 必须输出

```text
outputs/23L_factor_library_execution_big_winner_bridge/
    config.resolved.yaml
    input_manifest.json
    frozen_candidate_registry.json
    execution_reconciliation.json
    seed_metrics.csv
    matched_seed_deltas.csv
    annual_metrics.csv
    portfolio_daily.csv
    order_event_audit.csv
    turnover_cost_decomposition.csv
    big_winner_episode_metrics.csv
    big_winner_morphology_metrics.csv
    big_winner_score_deciles.csv
    concentration_audit.csv
    verdict.json
    report.md
```

预测大表保存在 `outputs/local_cache/phase2/`，manifest 记录 hash。
