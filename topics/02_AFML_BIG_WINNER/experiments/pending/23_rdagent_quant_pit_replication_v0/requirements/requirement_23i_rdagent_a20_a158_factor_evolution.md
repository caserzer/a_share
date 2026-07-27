# Requirement 23I：RD-Agent A20/A157 双起点因子进化

> 状态：`implementation_authorized`
>
> 上游：23G `ready_for_primary_static_benchmark`；23H
> `static_library_benchmark_complete`

## 1. Estimand

在相同 PIT universe、模型、prompt、实现重试、超时和 6 小时 wall-clock
预算下，分别测量：

```text
R&D-Factor(A20_RDAGENT_PINNED, sol-pro, 6h) - static A20
R&D-Factor(A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION, sol-pro, 6h) - static A157
```

完整 Alpha158 因缺失 `$vwap` 保持
`replication_blocked_by_missing_vwap`，不得把 A157 适配路线简称为完整 Alpha158
复刻。

## 2. 时间与反馈隔离

RD-Agent 原生 feedback 读取其 Qlib `test` 段，而不是 `valid` 段。为避免
historical-test 被 Agent 反复观察，正式运行覆盖环境变量为：

```text
train:                 2017-04-03 .. 2020-12-30
early_stop_valid:      2021-01-04 .. 2021-12-29
agent_feedback:        2022-01-04 .. 2022-12-28
selection_confirmation:2023-01-03 .. 2023-12-27
historical_test:       2024-01-02 .. 2026-05-27
```

Agent 运行中只能读取前三段。2023 confirmation 在 6 小时运行结束、候选冻结后
由独立受控评估器运行；2024–2026 historical-test 只允许在 confirmation 决策
完成后由 23L 揭示。

此前 `23I0_A20_smoke` 和 `23I0_A157_smoke` 使用了完整 2022–2023 validation
及 2024–2026 test，只用于验证 base-library 注入、代码生成、Qlib 拼接、回测和
checkpoint 链路；它们标记为 `smoke_design_contaminated`，不得进入正式
候选、SOTA、效率或收益结论。

## 3. 公平运行合同

- chat 固定 `openrouter/openai/gpt-5.6-sol-pro`；
- embedding 固定 `openrouter/openai/text-embedding-3-small`；
- OpenRouter 请求必须经过冻结的 HTTP/HTTPS proxy；
- `uv` 环境，禁止 conda；
- 每次 generation 固定 `QLIB_FACTOR_EVOLVING_N=1`；
- 每分支 wall-clock 固定 6 小时；
- 两分支使用独立 `LOG_TRACE_PATH`、`WORKSPACE_PATH` 和
  `PICKLE_CACHE_FOLDER_PATH_STR`；
- 禁止共享 hypothesis、feedback、accepted candidate 或市场结果；
- 相同 RD-Agent adapter diff、prompt、temperature、重试数和 Qlib 参数；
- 每个 loop 保存五步 checkpoint；失败和拒绝 loop 不得删除；
- 运行中检测 secret、模型路由、时间边界和 library hash 漂移；
- LiteLLM 无 sol-pro 价格映射时，API cost 标记
  `provider_cost_unavailable`，不得伪造为 0。

## 4. Smoke gate

两条 smoke 都必须证明：

```text
base feature count:
    A20  = 20
    A157 = 157
provider_uri == EP23 PIT provider
generated factor code executable
Qlib combined-factor run completes
feedback JSON parseable
five-step checkpoint complete
secret scan hits == 0
```

Smoke 的盈利、IC 和接受决定不作为 formal gate。

## 5. Formal run 与恢复

正式路径：

```text
outputs/23I1_rdfactor_a20_solpro_6h/raw_rdagent_trace/
outputs/23I2_rdfactor_a158_solpro_6h/raw_rdagent_trace/
```

若进程中断，从最后一个完整 `__session__/<loop>/<step>` 恢复；恢复计入同一
6 小时预算，不重新获得完整预算。连续三次相同 runtime failure 且没有新诊断时
停止对应分支并保留 `runtime_blocked`。

## 6. 每个候选的受控归因

RD-Agent 的 `Decision=true` 只是 2022 feedback 下的搜索决定，不等于 EP23
接受。对每个 Agent-accepted candidate 必须：

1. 冻结代码、名称、公式和 hash；
2. 与接受前 library 做五个 matched seed；
3. 仅在 2023 selection-confirmation 比较 IC、RankIC、ARR、IR、MDD；
4. 检查至少 4/5 seeds 同方向；
5. 检查平均横截面相关绝对值 `< 0.99`；
6. 检查单股、单日和单 factor cluster 集中度；
7. 通过后才进入 evolved frozen library；
8. 2024–2026 与 Big Winner 指标在 23L 前保持不可见。

## 7. 必须输出

每个分支至少包含：

```text
config.resolved.yaml
input_manifest.json
environment_manifest.json
library_hash_manifest.json
run_manifest.json
smoke_manifest.json
loop_trace.csv
hypothesis_trace.jsonl
candidate_inventory.csv
implementation_attempts.csv
feedback_metrics.csv
search_accounting.csv
confirmation_seed_metrics.csv
matched_marginal_attribution.csv
retained_library.json
annual_metrics.csv
secret_scan.json
verdict.json
report.md
raw_rdagent_trace/
```

若 RD-Agent 原生日志不能提供 provider cost，仍必须输出 input/output token
accounting，并明确 cost 缺失原因。

## 8. Gate 与终态

分支获得 `evolution_supported` 必须相对自己的静态起点同时满足：

1. 2023 confirmation IC 或 RankIC 的五 seed 中位数改善；
2. 至少 4/5 attribution seeds 同方向；
3. 2022 feedback 到 2023 confirmation 不发生改善方向反转；
4. 改善不依赖相关度 `>= 0.99` 的冗余列；
5. 后续 23L 的 next-open 净 ARR 或风险收益至少一项改善且另一项无重大恶化；
6. 改善不由单一股票、日期或因子簇驱动。

在 23L 完成前允许的中间裁决为：

```text
predictive_evolution_candidate
no_predictive_evolution
runtime_blocked
```

23I 无论结果强弱都必须实验完成并保留全部负结果。
