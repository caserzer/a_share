# Requirement 23M：条件式 Joint Scheduler 复刻

> 状态：`conditional_not_authorized_until_gate`
>
> 上游：23I factor、23K model、23L execution 三类证据

## 1. 启动 Gate

只有以下条件全部为真才执行付费 joint runs：

```text
factor_branch_pass == true
model_branch_pass == true
runtime_trace_complete == true
factor/model frozen artifacts mutually compatible == true
```

其中 factor/model pass 均需包含 2023 predictive confirmation 和 23L
next-open economic gate。任一为假时，23M 必须生成
`not_run_by_preregistered_gate` 终态与完整 gate evidence，不得为了“做完实验”
强行运行。

## 2. Matched arms

从完全相同的 frozen factor/model state 启动：

```text
contextual linear Thompson sampling
random action selection
LLM-directed action selection
```

主比较每 arm 12 小时 wall-clock；补充比较截断为相同 valid-loop 数。三条 arm
使用独立 trace/workspace/cache，不能共享 hypothesis、feedback、accepted
artifact 或市场结果。

## 3. 时间与信息边界

与 23I/23K 相同：

```text
train:            2017-04-03 .. 2020-12-30
early-stop valid: 2021-01-04 .. 2021-12-29
Agent feedback:   2022-01-04 .. 2022-12-28
confirmation:     2023-01-03 .. 2023-12-27
historical-test:  2024-01-02 .. 2026-05-27
```

joint scheduler 运行时不得读取 confirmation、historical-test 或 Big Winner。

## 4. Bandit 忠实性

context 固定论文八维：

```text
[IC, ICIR, RankIC, RankICIR, ARR, IR, -MDD, SR]
```

正式运行前必须输出 paper-vs-code diff，冻结：

- context 标准化；
- reward 定义；
- prior；
- posterior update；
- update 时点；
- action eligibility；
- 连续同方向探索上限；
- warm start；
- failed/invalid loop reward；
- missing metric policy；
- random seed；
- tie breaking。

代码与论文伪代码不一致时必须命名为 registered adaptation，不能静默近似。

## 5. Runtime preflight

- `fin_quant --base-features-path` CLI 参数真实生效；
- factor/model feedback 双 schema 均可解析；
- bandit/random/llm action selector 逐一 1-loop smoke；
- action 与 checkpoint/trace 一致；
- context/reward/posterior 每轮可重建；
- sol-pro、embedding、proxy、uv 与前序一致；
- secret scan hits 为 0；
- provider cost 可通过 key usage delta 对账。

## 6. 指标

同 wall-clock主表：

- total/valid/accepted loops；
- factor/model action balance；
- accepted factor/model 数；
- final 2023 IC/RankIC/ARR/IR/MDD；
- provider USD；
- tokens；
- wall time/valid loop；
- accepted artifact/USD；
- failure/timeout/retry；
- posterior/reward completeness；
- 是否由单次异常 loop 主导。

同 valid-loop补充表必须使用共同的最小 valid-loop 截断点，且不能与 wall-clock
headline 混报。

## 7. Gate 与裁决

`joint_scheduler_efficiency_supported` 不能只凭最终 IC。至少要求：

1. bandit 的 valid/accepted loop 效率优于 random 与 LLM-directed 中至少一个；
2. 同 valid-loop 下最终表现不劣；
3. posterior/reward 更新 100% 可重建；
4. action balance 不由实现 bug 或单次异常驱动；
5. 2023 confirmation 不发生方向反转；
6. 23L next-open 经济结果不符号反转。

否则根据证据裁决：

```text
joint_scheduler_efficiency_not_supported
joint_runtime_blocked
not_run_by_preregistered_gate
```

## 8. 必须输出

```text
outputs/23M_joint_scheduler_replication/
    gate_evidence.json
    paper_code_scheduler_diff.md
    config.resolved.yaml
    input_manifest.json
    arm_registry.json
    loop_trace.csv
    action_trace.csv
    context_reward_trace.csv
    posterior_trace.parquet
    search_accounting.csv
    wallclock_matched_metrics.csv
    valid_loop_matched_metrics.csv
    confirmation_seed_metrics.csv
    execution_metrics.csv
    secret_scan.json
    verdict.json
    report.md
```

三条付费 arm 不运行时，仍生成 gate_evidence、config、input manifest、verdict 和
report。
