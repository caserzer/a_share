# EP23 23B Alpha20 / LightGBM PIT Baseline

## 裁决

```text
run_kind = formal_5_seed
selected_seed = 20260723
selection = validation PAPER_PROXY Pearson IC only
evidence = design_contaminated_historical_real_market_evidence
claim_ceiling = deterministic_baseline_complete
```

本阶段建立了 RD-Agent factor/model/joint loop 的共同 deterministic comparator。
它不是 R&D-Agent(Q) 主实验结果，也不是 true OOS 证据。

## Selected-seed predictive readout

| split / lane | IC | ICIR | RankIC | RankICIR |
|---|---:|---:|---:|---:|
| validation / PAPER_PROXY | 0.012372 | 0.108351 | 0.008676 | 0.073573 |
| validation / EXECUTABLE_BRIDGE | 0.010386 | 0.095240 | 0.009542 | 0.083656 |
| historical test / PAPER_PROXY | 0.008618 | 0.072712 | 0.010504 | 0.084241 |
| historical test / EXECUTABLE_BRIDGE | 0.010332 | 0.085726 | 0.009849 | 0.078584 |

## Selected-seed Top50/drop5 proxy

| lane | gross ARR | net ARR | universe EW ARR | net ARR - universe | active IR | MDD | turnover |
|---|---:|---:|---:|---:|---:|---:|---:|
| PAPER_PROXY | 0.193670 | 0.131308 | 0.206966 | -0.075657 | -0.768101 | -0.191685 | 0.106955 |
| EXECUTABLE_BRIDGE | 0.211693 | 0.148394 | 0.222087 | -0.073693 | -0.721896 | -0.207817 | 0.106955 |

这里的 portfolio 是可复现的 equal-weight Top50/drop5 代理，不含 EP19 的停牌、
blocked fill、现金和逐笔最小费用状态机；完整可执行裁决留给 23F。

## Findings

- 5 个 seed 的 historical-test PAPER_PROXY IC 全部为正，但范围仅为
  `0.007264` 至
  `0.009114`，属于弱排序信息。
- selected seed 的 PAPER_PROXY 净 ARR 为
  `0.131308`，同期动态 universe 等权 ARR 为
  `0.206966`；active IR 为
  `-0.768101`。
- next-open bridge 没有发生 IC 符号翻转，但 selected seed 的净 ARR 仍低于动态
  universe 等权，active IR 为
  `-0.721896`。
- 两条 lane 的 5 个 seed active IR 全部为负。因此当前正的绝对 ARR 主要不能解释为
  Alpha20 排序已经战胜本地大盘股 beta；它只是 agent loop 必须超过的弱基线。
- frozen 官方 LightGBM 强正则参数下 best iteration 仅为
  `6`，后续 agent comparison 必须保留这一事实，
  并另列参数预算匹配 sensitivity，不能把一个欠拟合 comparator 当作成功证据。

## 解释边界

- `PAPER_PROXY` 与官方标签一致，但不是论文文字所说的 t+1 open execution。
- `EXECUTABLE_BRIDGE` 使用 next-open-to-next-open return，用来检测时点桥接是否翻转。
- historical test 已被本项目多次观察，只能用于本地诊断。
- agent-generated candidate 必须在完全相同的 split、label 和成本代理上比较。
- 5-seed 中位数摘要已写入 manifest 生成上下文；逐 seed 数值见 `seed_metrics.csv`。

运行耗时：`8.50` 秒。
