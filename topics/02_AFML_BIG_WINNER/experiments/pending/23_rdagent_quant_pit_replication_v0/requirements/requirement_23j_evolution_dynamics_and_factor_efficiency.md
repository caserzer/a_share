# Requirement 23J：进化路径、搜索效率与因子效率分析

> 状态：`implementation_authorized`
>
> 上游：23I 两条 raw run 均到达终态并完成 trace 采集

## 1. 目标

对 23I 的全部 loop（包括实现失败、可运行但拒绝、Agent 接受以及 EP23
confirmation 失败）重建：

```text
hypothesis
-> implementation attempts
-> executable
-> 2022 feedback
-> Agent decision
-> 2023 five-seed confirmation
-> redundancy decision
-> retained/rejected
```

不以最终 SOTA 代替搜索路径，不删除负结果，不把 LLM 自述当作实际接受状态。

## 2. 状态真值

- LLM 原始文本与 checkpoint 解析值分列保存；
- Agent acceptance 以修复后 checkpoint `feedback.decision` 为真值；
- EP23 predictive acceptance 以 2023 matched five-seed attribution 为真值；
- executable 以 factor `result.h5` 可读取、index 合法和有限覆盖为真值；
- retained library 由 confirmation + redundancy gate 决定；
- invalidated schema-bug run 单独报告成本和失败机制，不进入成功率分母。

## 3. Hypothesis embedding 与聚类

使用：

```text
openrouter/openai/text-embedding-3-small
proxy = frozen EP23 HTTP/HTTPS proxy
```

只发送 hypothesis/reason 文本，不发送因子值、收益序列、密钥或历史 test。
保存 embedding model、维度、文本 hash、响应状态和向量 hash；向量本体保存到本地
cache，不进入聊天报告。

聚类必须预注册并固定参数。至少输出：

- hypothesis cluster 数；
- cluster size；
- 分支覆盖；
- accepted/confirmed success rate；
- 重复或近重复比例；
- cluster 内从失败到成功的路径。

## 4. `refine / shift / reuse` 分类

相邻 loop 的路径类型由可审计规则产生：

```text
reuse:
    factor name/formula/code hash 与既有候选重复，或 embedding cosine >= 0.95

refine:
    与前一 hypothesis cosine >= 0.80 且 factor family 主体一致，
    但名称/窗口/公式/code hash 至少一项改变

shift:
    cosine < 0.80 或 factor family 主体改变
```

边界敏感性至少报告 cosine `0.75/0.80/0.85`；headline 固定 `0.80`。
LLM 对自身行为的描述只作辅助标签，不能覆盖规则标签。

## 5. 搜索与实现指标

分 A20/A157 及合计报告：

- total/completed/valid/accepted/confirmed loops；
- generated/implemented/accepted/confirmed factors；
- implementation attempt artifact 数；
- pass@1、pass@3、pass@5、pass@10；
- runtime failure taxonomy；
- wall time/valid loop；
- provider USD/valid loop；
- prompt token estimate/valid loop；
- cost/Agent-accepted factor；
- cost/EP23-confirmed factor；
- checkpoint completeness；
- schema/route/timeout/retry异常。

## 6. 因子库效率

每个静态、Agent-chain 和 EP23-retained state 至少报告：

- nominal/usable factor count；
- IC、RankIC、ICIR、RankICIR；
- IC 和 RankIC per retained factor；
- net ARR per retained factor（23L 后补全）；
- effective rank；
- effective rank / nominal factor；
- median/max absolute pairwise correlation；
- correlation cluster count；
- `abs corr >= 0.99` 数；
- 每个 accepted factor 的边际指标；
- 被后续淘汰因子的生命周期。

## 7. 必须输出

```text
outputs/23J_evolution_dynamics/
    config.resolved.yaml
    input_manifest.json
    loop_funnel.csv
    hypothesis_embeddings.parquet
    embedding_manifest.json
    hypothesis_clusters.csv
    transition_classification.csv
    family_coverage.csv
    failure_taxonomy.csv
    search_efficiency.csv
    factor_lifecycle.csv
    library_efficiency.csv
    branch_comparison.csv
    verdict.json
    report.md
```

## 8. Gate 与裁决

23J 是诊断实验，不要求 RD-Agent 必须优于静态库。完成 gate：

```text
all formal loops accounted for
invalidated loops excluded with explicit reason
checkpoint and LLM decision reconciliation complete
embedding requests all use frozen model/proxy
no historical-test metric used
search cost reconciles with 23I run manifests
factor lifecycle reconciles with retained libraries
secret scan hits == 0
```

允许终态：

```text
evolution_dynamics_complete
evolution_dynamics_complete_with_cost_caveat
trace_incomplete
embedding_runtime_blocked
```
