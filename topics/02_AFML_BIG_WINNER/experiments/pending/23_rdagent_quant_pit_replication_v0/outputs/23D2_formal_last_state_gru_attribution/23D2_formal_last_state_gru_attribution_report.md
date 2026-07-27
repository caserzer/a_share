# EP23 23D2 Formal Last-State GRU Attribution

## 裁决

```text
run_kind = formal_5_seed
fixed_input = Alpha20 x 20 timesteps
candidate = last_state_gru
capacity_matched_control = flattened_mlp
decision = last_state_gru_formal_candidate_pending_23F
evidence = design_contaminated_historical_real_market_evidence
```

23D1 已用三 seed 拒绝 attention pooling。本阶段不再为被拒绝结构追加预算，
而是在完全相同的 GeneralPTNN runtime contract 下补齐 MLP 与 last-state GRU
的五 seed 正式归因。前三个 seed 复用冻结预测，新增训练仅为
`20260726 / 20260727`。

## 五 seed 中位数

| variant | validation IC | test IC | test RankIC | gross ARR | net ARR | turnover |
|---|---:|---:|---:|---:|---:|---:|
| flattened_mlp | 0.004530 | 0.005260 | 0.011854 | 16.74% | 10.73% | 0.1054 |
| last_state_gru | 0.023038 | 0.015957 | 0.028426 | 35.44% | 28.09% | 0.1112 |

## Last-state GRU 相对 MLP

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | +0.021732 | 5/5 |
| historical-test PAPER_PROXY IC | +0.011655 | 5/5 |
| historical-test PAPER_PROXY RankIC | +0.018183 | 5/5 |
| historical-test PAPER_PROXY gross ARR | +11.0752 pp | 4/5 |
| historical-test PAPER_PROXY net ARR | +10.0856 pp | 3/5 |
| mean one-way turnover | +0.005156 | — |

逐 seed：

| seed | validation IC delta | test IC delta | test RankIC delta | gross ARR delta | net ARR delta |
|---:|---:|---:|---:|---:|---:|
| 20260723 | +0.022196 | +0.011655 | +0.010801 | +24.5473 pp | +23.0423 pp |
| 20260724 | +0.016547 | +0.015081 | +0.019124 | +11.0752 pp | +10.0856 pp |
| 20260725 | +0.013601 | +0.007426 | +0.020329 | +0.0437 pp | -0.0142 pp |
| 20260726 | +0.021732 | +0.000134 | +0.018183 | -1.8576 pp | -2.0516 pp |
| 20260727 | +0.022254 | +0.015869 | +0.015723 | +19.9511 pp | +18.4430 pp |

晋级要求以 validation IC、historical-test IC 和毛收益至少 3/5 seed 同向改善为主；
净收益单独改善不能覆盖成本伪影。turnover 与 gross/net 的联合归因决定该候选是否
只是在换手上改变了成本。

## 相对 Alpha20-LightGBM

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | +0.014944 | 5/5 |
| historical-test PAPER_PROXY IC | +0.008693 | 4/5 |
| historical-test PAPER_PROXY gross ARR | +12.5535 pp | 4/5 |
| historical-test PAPER_PROXY net ARR | +11.5940 pp | 4/5 |

EXECUTABLE_BRIDGE 上，last-state GRU 相对 MLP 的 IC 中位增量为
`+0.012483`（5/5 为正），
毛 ARR 中位增量为 `+11.2742 pp`
（3/5 为正）。

## 资源与边界

- 沿用 23D1 的 Adam/MSE、`clip_grad_value_=3.0`、
  `ReduceLROnPlateau` 和无 minimum-delta 的 early-stop，以保证五个 seed
  可直接合并；本阶段没有中途修改规则。
- 这是策略绝对收益代理，不与 23D 单次 Qlib 超额收益直接比较。
- historical test 是设计污染证据。即使本轮通过，也只能进入 23F executable
  与 Big Winner bridge，不能直接声明生产 alpha。
- 五 seed 累计模型训练耗时 `2040.65` 秒；本次
  invocation（含缓存恢复与新增训练）耗时 `773.48` 秒。
