# Requirement 23K：RD-Agent 模型进化与因子库依赖

> 状态：`implementation_authorized_after_23j`
>
> 上游：23J `evolution_dynamics_complete*`

## 1. Lanes

论文结构主 lane：

```text
23K1_RDModel_A20_solpro_6h
base factors = A20_RDAGENT_PINNED
budget = 6h
```

项目 sensitivity lane 仅当某个 23I evolved library 已通过 predictive、
redundancy 和 23L execution gate 后运行：

```text
23K2_RDModel_best_frozen_library_solpro_6h
```

23K2 不得冒充论文原实验。若 gate 未通过，必须输出正式
`not_run_by_preregistered_gate`，而不是留空目录。

## 2. 时间隔离

与 23I 使用相同 nested segments：

```text
train:                 2017-04-03 .. 2020-12-30
early_stop_valid:      2021-01-04 .. 2021-12-29
Agent feedback:        2022-01-04 .. 2022-12-28
selection confirmation:2023-01-03 .. 2023-12-27
historical-test:       2024-01-02 .. 2026-05-27
```

Agent 运行时只能读取前三段。2023 由独立五 seed attribution 使用；
2024–2026 只在 23L 冻结后揭示。

## 3. Runtime preflight

正式运行前必须：

- `fin_model --base-features-path` CLI 参数真实传入；
- A20 正确加载 20 个表达式因子；
- model feedback prompt 与 parser 同时兼容 `Decision` 和
  `Replace Best Result`；
- 1-loop smoke 完成五步 checkpoint；
- 生成模型代码可执行；
- actual runtime architecture/optimizer/loss/scheduler/clip/window 可抽取；
- 模型/embedding/proxy/uv 与 23I 完全一致；
- secret scan hits 为 0；
- 使用独立 trace/workspace/cache。

若 LLM 文本决定与 checkpoint 决定不一致，立即终止并按 schema bug 封存。

## 4. 正式归因

Agent acceptance 不等于 EP23 acceptance。每个 Agent-accepted 模型必须与：

```text
frozen LightGBM
flattened MLP
last-state GRU
attentive GRU
capacity-matched neural baseline
```

做 matched five-seed 归因。不得只比较单 seed 或 Agent 自己的当前 SOTA。

实际 runtime 为真值：

- parameter count；
- input layout 和 lookback；
- final state/flatten/attention 语义；
- optimizer、learning rate、weight decay；
- loss；
- batch size、epochs、early stop；
- scheduler；
- gradient clipping；
- device 和 dtype；
- seed；
- 训练时长与 peak GPU/CPU memory。

## 5. Gate

模型获得 `model_evolution_supported` 必须：

1. 2023 confirmation IC 或 RankIC 中位数改善；
2. 至少 4/5 seeds 同方向；
3. 2022 feedback 到 2023 confirmation 不符号反转；
4. 相对容量匹配 baseline 仍有增量；
5. 23L next-open 净 ARR 或风险收益至少一项改善且另一项无重大恶化；
6. 改善不由单一 seed、股票、日期或 regime 驱动。

23L 前允许中间裁决：

```text
predictive_model_evolution_candidate
no_predictive_model_evolution
runtime_blocked
```

## 6. 必须输出

```text
outputs/23K1_rdmodel_a20_solpro_6h/
    config.resolved.yaml
    input_manifest.json
    environment_manifest.json
    library_hash_manifest.json
    run_manifest.json
    loop_trace.csv
    hypothesis_trace.jsonl
    candidate_inventory.csv
    actual_runtime_configs.jsonl
    model_code/
    implementation_attempts.csv
    feedback_metrics.csv
    search_accounting.csv
    confirmation_seed_metrics.csv
    matched_model_attribution.csv
    annual_metrics.csv
    secret_scan.json
    verdict.json
    report.md
    raw_rdagent_trace/
```

23K2 同结构；不运行时至少包含 config、input manifest、gate evidence、
verdict 和 report。
