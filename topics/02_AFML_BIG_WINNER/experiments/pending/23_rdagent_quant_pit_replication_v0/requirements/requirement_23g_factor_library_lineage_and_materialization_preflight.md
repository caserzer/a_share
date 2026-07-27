# Requirement 23G：因子库谱系、运行时与物化预检

> 状态：`implementation_authorized`
>
> 上游：`research_plan_2_deep_factor_library_replication_and_rdagent_evolution.md`
>
> 配置：`config_phase2.yaml`

## 1. 目标

在任何 Phase 2 正式训练或 Agent 长跑前，冻结：

- `gpt-5.6-sol-pro` 和 embedding 的真实 OpenRouter 路由；
- Alpha20、Alpha158、Alpha360 的名称、表达式、顺序和 hash；
- `$vwap` 缺失时的注册 adaptation 路由与 exact-replication blocker；
- Alpha101 的 101/101 实现可用性；
- AutoAlpha 是否存在可冻结的完整因子 artifact；
- 三个 primary 静态库在本地 PIT Qlib provider 上的可物化性。

## 2. 授权边界

允许：

- 读取本地论文、Qlib、RD-Agent 和 EP23 artifacts；
- 通过已配置代理进行一次最小 chat 和 embedding smoke；
- 在 EP23 下写入 23G outputs、Phase 2 base-feature registry 和报告。

禁止：

- 将 key 写入命令输出、日志、配置或 artifact；
- 修改第一阶段 outputs；
- 用 Alpha101 子集冒充完整 Alpha101；
- 用本地 Agent 生成库冒充 AutoAlpha；
- 在 preflight 中训练正式模型或读取 Big Winner 结果。

## 3. 输入

- `config.yaml`
- `config_phase2.yaml`
- `2505.15155v2.pdf`
- RD-Agent checkout 与本地 `.env`
- Qlib `Alpha158DL` / `Alpha360DL`
- PIT provider `data/qlib/cn_data_pit_largecap`

## 4. 必须输出

```text
outputs/23G_factor_library_preflight/
    runtime_model_smoke.json
    factor_library_registry.json
    factor_library_lineage.csv
    alpha101_operator_compatibility.csv
    autoalpha_artifact_audit.md
    library_materialization_coverage.csv
    library_feature_coverage.csv
    library_hash_manifest.json
    preflight_verdict.json
    23G_factor_library_preflight_report.md
```

同时生成：

```text
rdagent_base_features_phase2/
    alpha20/base_factors.json
    alpha158/base_factors.json
```

## 5. 验收

Primary gate：

```text
A20 exact names == expressions == unique names == 20
A158 exact registry count == 158
A360 exact registry count == 360
A157 no-VWAP adaptation count == 157
A300 no-VWAP adaptation count == 300
smoke rows >= 1000
smoke dates >= 20
smoke instruments >= 100
finite ratio >= 0.50
effective LiteLLM model == openrouter/openai/gpt-5.6-sol-pro
effective embedding model == openrouter/openai/text-embedding-3-small
chat smoke == HTTP 200
embedding smoke == HTTP 200 and non-empty vector
secret scan hits == 0
```

Alpha101 只有 101/101 且通过参考数值对拍才能进入 23H；否则输出
`A101_REPLICATION_BLOCKED`。AutoAlpha 只有固定完整 artifact、数据快照、公式/
代码和 hash 才能进入；否则输出 `AUTOALPHA_DEFINITION_BLOCKED`。

若 provider 没有 `$vwap`，完整 Alpha158/360 必须标记
`replication_blocked_by_missing_vwap`。已注册的 A157/A300 no-VWAP adaptation
可进入 23H，但不得在报告中省略 adaptation 后缀。

Alpha101/AutoAlpha 或完整 Alpha158/360 被阻塞，不阻塞
A20/A157-adaptation/A300-adaptation 的 23H。

## 6. Terminal states

```text
ready_for_primary_static_benchmark
blocked_by_runtime
blocked_by_primary_library_materialization
blocked_by_secret_leak
```
