# Episode 23 Research Plan 2：多因子库深度复刻与 RD-Agent 进化

> 文档状态：`draft_preflight_required`
>
> 生成日期：2026-07-27
>
> Episode ID：`23_rdagent_quant_pit_replication_v0`
>
> 研究阶段：Phase 2
>
> 上一阶段计划：`research_plan.md`
>
> 上一阶段报告：`EP23_rdagent_quant_pit_replication_full_report_cn.md`
>
> 论文：Li et al. (2025), *R&D-Agent-Quant: A Multi-Agent Framework for
> Data-Centric Factors and Model Joint Optimization*
>
> 本地论文：`2505.15155v2.pdf`
>
> 论文 SHA256：
> `5df0919520ec1a9d556f6a20bc10e9d2d1dc11cada2e6913b871239df63a2df2`
>
> RD-Agent checkout：`/home/xiaolv/code/RD-Agent`
>
> Python 环境：只使用 `uv`，不创建或调用 conda environment

## 0. 一页结论

第一阶段只以 Alpha20 为起始库，完成了环境、PIT 数据、单轮 factor/model、
受控归因和执行桥验证，但还没有复刻论文最关键的“多因子库比较”和
“Alpha20/Alpha158 双起点连续进化”。

第二阶段的主问题改为：

> 在完全相同的 PIT universe、标签、LightGBM、时间切分和执行器下，
> Alpha20、Alpha101、Alpha158、Alpha360 等静态因子库各自提供多少有效信息；
> RD-Agent 从 Alpha20 和 Alpha158 出发连续进化后，是否能稳定提高自身起点，
> 同时用更紧凑、低冗余的因子集合改善可执行收益与 Big Winner 右尾暴露？

研究分为三层，禁止混报：

```text
L1 PAPER_PROTOCOL_REPLICATION:
    静态 Alpha20/101/158/360 + 固定 LightGBM
    R&D-Factor(Alpha20) vs R&D-Factor(Alpha158)
    R&D-Model(Alpha20)

L2 LOCAL_PIT_EXTENSION:
    相同因子库进入 next-open 执行器
    成本、换手、停牌/涨跌停、Big Winner 和左尾负担

L3 CONDITIONAL_JOINT_EVOLUTION:
    只有 factor/model 独立分支通过后
    才比较 bandit / random / LLM scheduler
```

本计划不把“因子数更多”预设为更好。论文 Figure 7 明确比较了
`R&D-Factor(20)` 和 `R&D-Factor(158)`，并指出 Alpha158 起点的进化表现更强，
但 Alpha20 起点的进化也可超过 Alpha360；因此本阶段的核心 estimand 是
“进化相对各自起点的增量”和“单位有效因子的效率”，而不是简单做
20/158/360 维度排名。

当前运行时冻结为：

```text
chat model:
    OpenRouter route = openrouter/openai/gpt-5.6-sol-pro
    OpenRouter model = openai/gpt-5.6-sol-pro

embedding model:
    OpenRouter route = openrouter/openai/text-embedding-3-small
    OpenRouter model = openai/text-embedding-3-small

network:
    OpenRouter only
    required HTTP/HTTPS proxy

runtime:
    uv only
```

2026-07-27 已完成最小真实 chat smoke：

```text
HTTP status    200
resolved model openai/gpt-5.6-sol-pro
response       OK
```

凭据不得进入本计划、实验配置、trace、输出或 Git。

---

## 1. 为什么需要第二阶段

### 1.1 第一阶段回答了什么

23A–23F 已支持：

- RD-Agent 能在本地 uv + OpenRouter + PIT Qlib 环境运行；
- Agent 生成的因子和模型必须经过 matched-seed 独立归因；
- Alpha20 上的部分动量、量能和波动因子获得初步支持；
- last-state GRU 相对 flattened MLP 有稳定模型结构增量；
- 该模型更像左尾规避器，而不是 Big Winner selector；
- joint scheduler 尚未运行。

当前总裁决是：

```text
model_branch_only_supported
```

### 1.2 第一阶段没有回答什么

第一阶段没有回答：

1. Alpha20 是否只是一个过弱的起点；
2. Alpha158/Alpha360 的静态信息是否已覆盖 Agent 新因子；
3. RD-Agent 的收益来自“增加更多因子”，还是来自去冗余和重组；
4. 从 Alpha158 出发是否仍有稳定进化空间；
5. Alpha101 在当前 Qlib/PIT provider 上能否忠实实现；
6. AutoAlpha 是否有足够公开定义支持可审计复刻；
7. factor/model 独立分支成熟后，bandit 调度是否真的提高有效循环效率；
8. 预测指标改善能否转化为 next-open 成本后收益和 Big Winner 右尾增量。

因此第二阶段不能直接启动 12 小时 joint run。必须先建立多因子库的同口径静态
基线，再做 Alpha20/Alpha158 双起点连续进化。

---

## 2. 论文事实与本地复刻边界

### 2.0 23G 执行修订：VWAP 路由

23G 实测发现当前 PIT Qlib provider 没有 `$vwap` 字段。其直接影响是：

```text
Alpha158: VWAP0 全空
Alpha360: VWAP59 ... VWAP0 共 60 列全空
```

仓库既有 EP21 的 qfq/raw VWAP 审计也没有授权把 `money / volume` 静默提升为
完整 Qlib `$vwap`。因此 Phase 2 正式路线修订为：

```text
A20_RDAGENT_PINNED
A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION
A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION
```

完整 Alpha158/Alpha360 保留谱系和物化失败证据，裁决为
`replication_blocked_by_missing_vwap`。后文简写的 Alpha158/Alpha360 进化，
执行时均指带完整 adaptation ID 的 A157/A300 路线；报告不得省略这一差异。

### 2.1 论文中的静态因子库

| 因子库 | 论文定义 | 本地初始可行性 | Phase 2 身份 |
|---|---|---|---|
| Alpha20 | 论文/RD-Agent 固定的 20 个起始因子 | 已实现 | primary |
| Alpha101 | WorldQuant 101 个公式化价量因子 | 尚无完整本地实现 | lineage-first |
| Alpha158 | Qlib 的 158 个多窗口技术指标 | Qlib 原生可生成 158 列 | primary |
| Alpha360 | Qlib 的 360 个历史归一化价量序列特征 | Qlib 原生可生成 360 列 | primary |
| AutoAlpha | LLM 驱动、融合文本/数值/图像的动态结构化因子库 | 论文未给出可固定的完整静态 artifact | conditional/blocked |

论文表格数值只用于数量级和方向 sanity check，不是本地 gate：

| Library | IC | ICIR | RankIC | RankICIR | ARR | IR | MDD | Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Alpha101 | 0.0308 | 0.2588 | 0.0331 | 0.2749 | 0.0512 | 0.5783 | -0.1253 | 0.4085 |
| Alpha158 | 0.0341 | 0.2952 | 0.0450 | 0.3987 | 0.0570 | 0.8459 | -0.0771 | 0.7393 |
| Alpha360 | 0.0420 | 0.3290 | 0.0514 | 0.4225 | 0.0438 | 0.6731 | -0.0721 | 0.6074 |
| AutoAlpha | 0.0334 | 0.2656 | 0.0361 | 0.2967 | 0.0400 | 0.4288 | -0.1225 | 0.3266 |

本地 universe、数据期、字段、LLM 和执行语义都不同，禁止用本地指标宣称
复现了上述绝对数字或排序。

### 2.2 论文中的进化实验

论文 Figure 7 的直接可复刻结构是：

```text
fixed predictor = LightGBM

branch A:
    initial library = Alpha20
    optimizer = R&D-Factor

branch B:
    initial library = Alpha158
    optimizer = R&D-Factor
```

论文还报告：

- Alpha20 起点可较快达到 Alpha158/Alpha360 的 IC 水平；
- Alpha158 起点进一步改善，部分时期 IC/RankIC 超过 `0.07`；
- 进化库以更少的有效因子取得更高信息和资本效率；
- 因子冗余可能使更大的静态库表现更不稳定；
- factor/model 各运行 6 小时，joint 运行 12 小时。

本地只检验这些结构性命题，不以 `0.07` 或 NAV `5.1` 作为门槛。

### 2.3 数据边界

论文因子挖掘还使用 Wind 基本面、估值、分析师、情绪和资金流字段。本地当前
primary provider 只有：

```text
open, high, low, close, volume, factor, money, turnover_rate
```

本阶段采用三层字段合同：

| Lane | 字段 | 状态 |
|---|---|---|
| M0 | PIT OHLCV + money + turnover_rate | primary |
| M1 | 有首次公告时间和版本链的 PIT 基本面 | future conditional |
| M2 | 分析师、订单流、文本、图像 | blocked until timestamped source |

任何没有 as-reported timestamp、revision lineage 和历史 coverage 的字段不得进入
正式训练。当前值回填历史、最终修订值回填历史或静态成分股回填均为硬失败。

---

## 3. 因子库注册表与实现合同

每个 library 必须有唯一 `library_id`、公式/代码来源、列顺序、内容 hash、
最大 lookback、字段依赖和可用性报告。

### 3.1 `A20_RDAGENT_PINNED`

来源：

- 本地 `config.yaml:alpha20`；
- RD-Agent `rdagent/utils/qlib.py:ALPHA20`；
- 论文附录 Alpha20。

验收：

- 正好 20 个唯一列；
- 本地配置与固定 RD-Agent commit 的公式逐项一致；
- 公式、名称、顺序分别 hash；
- 不允许用第一阶段 Agent 新因子污染静态 Alpha20。

### 3.2 `A158_QLIB_PINNED`

来源：

```text
qlib.contrib.data.loader.Alpha158DL.get_feature_config()
```

已确认当前 Qlib 环境返回 158 个表达式和 158 个名称。正式 preflight 仍需：

- 固定 Qlib package/version/commit；
- 固定 expression/name 顺序；
- 输出 158 列覆盖率、有限值率、常数率；
- 报告每列最大 lookback；
- 检查与 Alpha20 的同名和高相关重合；
- 禁止人工挑选后仍命名为完整 Alpha158。

### 3.3 `A360_QLIB_PINNED`

来源：

```text
qlib.contrib.data.loader.Alpha360DL.get_feature_config()
```

已确认当前 Qlib 环境返回 360 个表达式和 360 个名称。正式 preflight 需额外检查：

- `CLOSE59...CLOSE0` 等归一化价格序列的分母和复权语义；
- `VOLUME59...VOLUME0` 的成交量归一化与 qfq volume 语义；
- 长 lookback warmup 是否导致早期横截面大量缺失；
- 相邻 lag 的高冗余簇；
- 360 维输入下固定 LightGBM 是否受到容量或正则化约束。

### 3.4 `A101_CANONICAL_REBUILT`

Alpha101 当前没有可直接调用的本地完整实现。它必须遵守：

1. 固定 canonical 101 公式及来源版本；
2. 建立 operator compatibility matrix；
3. 每个公式分类为：

```text
exact_qlib_expression
exact_python_adapter
definition_blocked
```

4. 任一 `definition_blocked` 存在时，不得把子集命名为 Alpha101；
5. Python adapter 必须与参考实现做小样本数值对拍；
6. rank、decay、signed power、rolling regression 等算子的横截面/时间维语义必须
   显式测试；
7. 只有 101/101 通过公式、时点、shape 和数值测试后，才进入正式 benchmark。

若无法达到 101/101，则输出：

```text
A101_REPLICATION_BLOCKED
```

并可另建：

```text
A101_IMPLEMENTABLE_SUBSET_N_OF_101
```

但它只作诊断，不进入论文基线排名。

### 3.5 `AUTOALPHA_EXACT_ARTIFACT`

论文将 AutoAlpha 描述为动态、多模态、LLM 驱动的因子库，但没有给出当前本地
可冻结的完整公式集、生成 trace、数据快照和 hash。正式规则：

- 先查找论文引用实现、版本、因子 artifact 和数据合同；
- 若不能固定完整 artifact，则裁决 `definition_blocked`；
- 不允许把 RD-Agent 本地生成因子重命名为 AutoAlpha；
- 可以创建独立 comparator：

```text
LOCAL_AGENT_DYNAMIC_LIBRARY_SOLPRO
```

但报告必须明确它是项目扩展，不是 AutoAlpha 复刻。

---

## 4. RD-Agent 因子库注入与运行时合同

### 4.1 代码接口

当前 RD-Agent `QuantRDLoop` 默认把：

```python
self.plan["features"] = ALPHA20
```

传入每个 factor/model experiment。Qlib YAML 虽使用 `Alpha158DL` loader shell，
实际 feature 列由：

```text
feature_expressions = exp.base_features.values()
feature_names       = exp.base_features.keys()
```

决定。

因此 Alpha158/Alpha360 进化不能只改 YAML 中的 loader class；必须建立显式的
library registry/loader，将固定表达式字典注入 `plan["features"]`，并在 trace 中
记录：

```text
initial_library_id
initial_library_hash
initial_feature_count
current_sota_library_hash
current_feature_count
```

不得修改第一阶段 sealed output。Phase 2 的 runtime adapter、配置和输出使用新的
子目录与 hash。

### 4.2 模型冻结

所有 Phase 2 新实验固定：

```text
LITELLM_CHAT_MODEL=openrouter/openai/gpt-5.6-sol-pro
LITELLM_EMBEDDING_MODEL=openrouter/openai/text-embedding-3-small
```

同时保留兼容/health-check 值：

```text
CHAT_MODEL=openai/gpt-5.6-sol-pro
EMBEDDING_MODEL=openai/text-embedding-3-small
```

每次正式 run 的 manifest 必须记录模型名、provider、temperature、reasoning effort、
max tokens、stream、代理是否启用和 smoke 时间；不记录 key。

不能照抄论文 GPT-4o/o3-mini 的 temperature/token 配置。23G 先用一次结构化输出
smoke 验证：

- system/user role 兼容；
- response schema 兼容；
- streaming 兼容；
- JSON 可解析率；
- 最大输出长度；
- timeout/retry；
- embedding 维度和缓存一致性。

只有 smoke 通过后才冻结 `sol-pro` 的正式参数。

### 4.3 公平预算

主比较使用相同 wall-clock budget：

```text
R&D-Factor(A20)   6h
R&D-Factor(A158)  6h
R&D-Model(A20)    6h
R&D-Agent(Q)      12h, conditional
```

同时报告：

- total loops；
- valid loops；
- accepted/SOTA loops；
- implementation attempts；
- wall time；
- input/output tokens；
- API cost；
- CPU/GPU peak；
- cache hit rate。

wall-clock 是论文主 estimand；`per valid loop` 和 `per accepted factor` 是效率诊断。
不能用更多 loop 或复用另一分支已看过的 hypothesis 给某一分支隐性加预算。

---

## 5. 数据、切分与防泄漏设计

### 5.1 Primary universe

```text
provider:
    data/qlib/cn_data_pit_largecap

market:
    pit_largecap_main_chinext

membership:
    close-observed membership date D
    usable from next trading session
```

### 5.2 固定外层切分

```text
warmup:
    2017-01-03 .. 2017-03-31

train:
    2017-04-03 .. 2021-12-29

validation:
    2022-01-04 .. 2023-12-27

historical_test:
    2024-01-02 .. 2026-05-27
```

`historical_test` 已在第一阶段被观察，继续固定为：

```text
design_contaminated_historical_real_market_evidence
```

### 5.3 进化期内层选择

为避免 Agent 反复读取完整 validation 后再选择，23I 将 validation 分成两个时间
块：

```text
evolution_feedback:
    2022

selection_confirmation:
    2023
```

23I smoke 发现 RD-Agent 原生 feedback 实际读取 Qlib `test` 段。为保证 2023
confirmation 和 2024–2026 historical-test 均不进入 Agent，正式运行冻结为：

```text
train:             2017-04-03 .. 2020-12-30
early-stop valid:  2021-01-04 .. 2021-12-29
Agent feedback:    2022-01-04 .. 2022-12-28
confirmation:      2023-01-03 .. 2023-12-27
historical-test:   2024-01-02 .. 2026-05-27
```

2023 confirmation 由运行后的独立评估器执行。此前使用 2024–2026 test 的两条
单轮 smoke 仅验证运行链路，标记 `smoke_design_contaminated`，不得进入正式
候选或性能结论。

### 5.4 标签

```text
PAPER_PROXY:
    score at close t
    label = close(t+2) / close(t+1) - 1

EXECUTABLE_BRIDGE:
    score at close t
    return = open(t+2) / open(t+1) - 1
```

Agent feedback primary 只读 `PAPER_PROXY` validation 指标；不得看到 historical-test、
Big Winner taxonomy 或 next-open bridge 结果。后两者只在最终冻结后揭示。

---

## 6. 研究问题与 estimands

### RQ1：静态因子库是否存在稳定差异

```text
E_static_library(L):
    fixed LightGBM
    fixed data/split/label/preprocessing
    library L in {A20, A101, A158, A360}
```

比较预测、经济、冗余、稳定性和资源占用，不只比较最高 IC。

### RQ2：Alpha20 起点能否被持续进化

```text
E_evolve20:
    R&D-Factor(A20, sol-pro, 6h)
    minus static A20
```

### RQ3：Alpha158 起点是否仍有边际进化空间

```text
E_evolve158:
    R&D-Factor(A158, sol-pro, 6h)
    minus static A158
```

### RQ4：进化是否提高因子效率而非单纯堆维度

重点报告：

```text
IC per retained factor
RankIC per retained factor
net ARR per retained factor
effective rank
mean/max pairwise correlation
correlation cluster count
accepted factor marginal contribution
```

### RQ5：模型进化是否依赖因子库

论文 faithful lane：

```text
R&D-Model(A20, sol-pro, 6h)
```

项目 sensitivity lane 只有在 winning evolved library 冻结后运行：

```text
R&D-Model(best_frozen_library, sol-pro, 6h)
```

两条 lane 分开报告，后者不能冒充论文原实验。

### RQ6：joint scheduler 是否提高搜索效率

只有 23I 的 factor 分支和 23K 的 model 分支达到预设 gate，才执行：

```text
bandit vs random vs LLM scheduler
```

主比较使用相同 12 小时；补充比较使用相同 valid-loop 数。两种比较不能混成一个
结论。

### RQ7：Big Winner 项目效用

```text
E_right_tail:
    evolved library/model
    minus own frozen static baseline
```

至少报告：

- winner episode recall；
- right-tail exposure rate/enrichment；
- severe-left-tail exposure；
- morphology capture；
- early/middle/late lifecycle coverage；
- 成本后收益和 benchmark-relative return。

若只改善左尾而不改善右尾，应降级为 risk overlay、participation filter 或
meta-label，不得称为 Big Winner selector。

---

## 7. 实验路线

### 23G：因子库 lineage、物化和运行时 preflight

目标：

- 冻结 sol-pro/embedding 的有效运行配置；
- 生成 A20/A158/A360 的表达式与名称注册表；
- 完成 Alpha101 operator compatibility matrix；
- 查明 AutoAlpha 是否有可复刻 artifact；
- 证明各库在 PIT provider 上可按相同 index 物化。

主要输出：

```text
outputs/23G_factor_library_preflight/
    runtime_model_smoke.json
    factor_library_registry.json
    factor_library_lineage.csv
    alpha101_operator_compatibility.csv
    autoalpha_artifact_audit.md
    library_materialization_coverage.csv
    library_hash_manifest.json
    preflight_verdict.json
```

Gate：

```text
A20   == 20/20 valid
A158  == 158/158 valid
A360  == 360/360 valid
A101  == 101/101 valid OR excluded as replication_blocked
AutoAlpha exact artifact fixed OR excluded as definition_blocked
no forbidden PIT field
no target/index leakage
```

### 23H：静态多因子库 matched benchmark

固定 LightGBM、五个 seed、相同处理器和相同执行参数，运行：

```text
A20
A158
A360
A101, only if 23G exact gate passes
```

主模型超参数完全相同，复刻论文“固定 predictor”的控制。另做一个
`capacity_sensitivity`：

- 只在 train/validation 调整共同的容量/正则化网格；
- 不为每个 library 单独人工挑最优 test 参数；
- 明确区分 `fixed_model_primary` 与 `capacity_sensitivity_secondary`。

输出静态 predictive、portfolio、turnover、冗余、资源和年度稳定性。

### 23I：R&D-Factor Alpha20/Alpha158 双起点进化

先运行 1 个 loop smoke：

```text
23I0_A20_smoke
23I0_A158_smoke
```

确认 feature registry、SOTA merge、去重、trace、恢复点和缓存正确后，再运行：

```text
23I1_RDFactor_A20_solpro_6h
23I2_RDFactor_A158_solpro_6h
```

两分支必须：

- 使用相同模型、prompt contract、最大实现尝试、timeout 和预算；
- 使用独立 cache namespace；
- 不共享 accepted hypothesis/result；
- 共享纯代码修复经验时必须显式记录，不能共享市场结果；
- 每 loop 保存 proposed hypothesis、代码 hash、运行状态、反馈、接受决定；
- 每个 accepted candidate 都做新增因子的 matched marginal attribution；
- `mean cross-sectional correlation >= 0.99` 时去重；
- 对高维 A158 起点额外做 cluster-aware redundancy audit。

### 23J：进化路径和因子效率分析

不再只看最终 SOTA。对所有 loop 构建：

```text
proposal -> implementation attempts -> executable -> valid
-> marginal attribution -> accepted/rejected -> retained library
```

将 hypothesis 按语义 embedding 聚类，检验论文描述的：

```text
refine
shift
reuse
```

并报告：

- hypothesis cluster 数；
- cluster 内尝试和成功率；
- 从修复到成功的 pass@k；
- 重复/近重复 hypothesis 比例；
- factor family 覆盖；
- 每个 accepted factor 的边际 IC、RankIC、ARR；
- 被后续淘汰因子的生命周期；
- A20/A158 分支的探索差异。

### 23K：R&D-Model 进化与因子库依赖

主 lane 固定 Alpha20，复刻论文 R&D-Model 控制：

```text
23K1_RDModel_A20_solpro_6h
```

只有 23I 中某一 evolved library 同时通过预测、执行和冗余 gate，才运行：

```text
23K2_RDModel_best_frozen_library_solpro_6h
```

任何 Agent 模型都要与容量匹配基线做 matched-seed 归因。结构变化、优化器、
loss、scheduler、clip 和输入窗口必须以实际 runtime 为准，不能只引用生成 spec。

### 23L：next-open 执行和 Big Winner bridge

只允许接收 23H/23I/23K 在不读取 historical-test 下冻结的候选。复用 23F 状态机，
并统一：

- next-session membership；
- 停牌、ST、上市状态；
- 涨跌停可买/可卖；
- TopK/dropout；
- 佣金、印花税、最低佣金、滑点；
- benchmark 和 PIT universe 等权；
- Big Winner episode/taxonomy。

每个 evolved branch 必须对自己的 static start 做 matched comparison。

### 23M：条件式 joint scheduler

启动条件：

```text
factor_branch_pass == true
model_branch_pass == true
runtime_trace_complete == true
```

若条件成立，固定同一起始 factor/model，比较：

```text
contextual linear Thompson sampling
random
LLM-directed action selection
```

bandit context 严格使用论文八维状态：

```text
[IC, ICIR, RankIC, RankICIR, ARR, IR, -MDD, SR]
```

必须冻结 reward 定义、prior、连续同方向探索上限和更新时点。若代码实现与论文
伪代码不一致，先形成差异清单，不能静默近似。

---

## 8. 统一指标

### 8.1 Predictive

- IC / ICIR；
- RankIC / RankICIR；
- 每年和每半年 IC；
- seed 中位数、范围和改善 seed 数；
- 日横截面数量和 coverage；
- prediction concentration。

### 8.2 Economic

- gross/net ARR；
- IR/Sharpe；
- MDD；
- Calmar；
- turnover；
- holding count；
- trade count；
- benchmark-relative ARR；
- 下单失败和不可成交率。

### 8.3 Library quality

- nominal factor count；
- retained factor count；
- finite coverage；
- constant/near-constant count；
- pairwise correlation distribution；
- effective rank；
- correlation cluster count；
- marginal contribution；
- IC/RankIC/net ARR per retained factor；
- compute/memory/inference latency。

### 8.4 Evolution efficiency

- total/valid/accepted loops；
- pass@k；
- median implementation attempts；
- time to first valid/accepted loop；
- token/API cost per valid loop；
- token/API cost per accepted factor；
- cache hit rate；
- hypothesis duplicate rate。

### 8.5 Big Winner morphology

- episode recall；
- signal exposure enrichment；
- severe-left-tail rate；
- winner lifecycle phase；
- morphology capture share；
- single morphology concentration；
- winner vs non-winner score separation。

---

## 9. Gate 与裁决

### 9.1 Library integrity gate

必须同时满足：

- 列数和注册表一致；
- 公式/代码 hash 固定；
- 无未来字段和 split crossing；
- index 唯一且排序一致；
- train-fit processor 不读取 validation/test；
- coverage 达到预注册阈值；
- 结果可从 manifest 重建。

### 9.2 Static benchmark gate

静态库不设“必须超过 Alpha20”的先验。它的 gate 是结果可比较、可复现和
五 seed 完整。弱库仍保留为合法负结果。

### 9.3 Evolution gate

R&D-Factor 分支要获得 `evolution_supported`，必须相对自己的静态起点：

1. validation IC 或 RankIC 中位数改善；
2. 至少 4/5 attribution seeds 同方向；
3. selection-confirmation 不发生符号反转；
4. 最终库没有仅靠高度冗余列堆出改善；
5. next-open net ARR 或风险收益至少一项改善，且另一项没有重大恶化；
6. 改善不是单一股票、日期或因子簇驱动。

### 9.4 Big Winner gate

若要称为 `big_winner_selector_increment_supported`，必须：

- right-tail enrichment `> 1.0`；
- winner recall 相对静态基线有正增量；
- severe-left-tail 不超过预注册容忍；
- 覆盖不集中在单一 morphology；
- next-open 成本后结果不符号反转。

否则根据结果降级：

```text
risk_overlay_candidate
participation_filter_candidate
meta_label_candidate
no_incremental_utility
```

### 9.5 Joint gate

bandit 不能只凭最终 IC 获胜。至少同时报告：

- 同 wall-clock 下 valid/accepted loop；
- 同 valid-loop 下最终表现；
- action balance；
- posterior/reward 更新完整性；
- 是否由某一次异常 loop 主导。

### 9.6 Terminal verdicts

```text
deep_replication_supported
factor_evolution_only_supported
model_evolution_only_supported
joint_scheduler_efficiency_supported
static_library_only_supported
paper_claim_direction_not_reproduced
replication_blocked_by_factor_definition
replication_blocked_by_data_lineage
runtime_blocked
```

任何裁决仍受以下证据身份限制：

```text
design_contaminated_historical_real_market_evidence
not production authorization
```

---

## 10. 预期 artifacts

```text
requirements/
    requirement_23g_factor_library_lineage_and_materialization_preflight.md
    requirement_23h_static_factor_library_matched_benchmark.md
    requirement_23i_rdagent_a20_a158_factor_evolution.md
    requirement_23j_evolution_dynamics_and_factor_efficiency.md
    requirement_23k_rdagent_model_evolution.md
    requirement_23l_factor_library_execution_big_winner_bridge.md
    requirement_23m_conditional_joint_scheduler_replication.md

outputs/
    23G_factor_library_preflight/
    23H_static_factor_library_benchmark/
    23I1_rdfactor_a20_solpro_6h/
    23I2_rdfactor_a158_solpro_6h/
    23J_evolution_dynamics/
    23K1_rdmodel_a20_solpro_6h/
    23K2_rdmodel_best_library_solpro_6h/
    23L_factor_library_execution_big_winner_bridge/
    23M_joint_scheduler_replication/
```

每个 formal output 至少包含：

```text
config.resolved.yaml
input_manifest.json
environment_manifest.json
library_hash_manifest.json
run_manifest.json
seed_metrics.csv
annual_metrics.csv
search_accounting.csv
verdict.json
report.md
```

Agent run 还必须包含可恢复 checkpoint 和逐 loop trace；只保留最终模型或最终
metrics 不满足复刻要求。

---

## 11. 成本、恢复和停止规则

### 11.1 正式运行前

- 先做 1 loop；
- 验证日志不含 key；
- 验证 checkpoint 可恢复；
- 验证缓存 namespace 不跨 A20/A158 分支；
- 验证模型实际解析为 `openrouter/openai/gpt-5.6-sol-pro`；
- 验证 embedding 实际解析为
  `openrouter/openai/text-embedding-3-small`；
- 生成预算上限和预计 API cost。

### 11.2 自动停止

发生以下任一情况立即停止对应 run：

- key/secret 写入日志或 artifact；
- test/Big Winner 结果进入 Agent feedback；
- library hash 漂移；
- 连续三次相同 runtime failure 且无新诊断；
- 输出 index 重复或时间越界；
- 代理绕过；
- 模型路由与冻结模型不一致；
- 超过 wall-clock/token/cost 上限；
- checkpoint 无法恢复且继续运行会丢失审计链。

### 11.3 失败仍要保留

失败 run 也必须保留：

- 配置和输入 hash；
- 最后 checkpoint；
- error taxonomy；
- 已消耗时间/token/cost；
- 可恢复性结论；
- `blocked` 或 `failed` verdict。

不得只保留成功候选。

---

## 12. 执行顺序

严格顺序：

```text
23G factor-library/runtime preflight
    ↓
23H static matched benchmark
    ↓
23I A20/A158 dual-start R&D-Factor evolution
    ↓
23J evolution dynamics and factor efficiency
    ↓
23K R&D-Model evolution
    ↓
23L executable and Big Winner bridge
    ↓
23M conditional joint scheduler
```

下一步不是直接开始 6 小时进化，而是先生成并评审：

```text
requirement_23g_factor_library_lineage_and_materialization_preflight.md
```

23G 必须先解决两个真实 blocker：

1. Alpha101 是否能够 101/101 忠实实现；
2. AutoAlpha 是否存在可冻结、可审计的完整 artifact。

Alpha158 和 Alpha360 已有本地 Qlib 原生定义，可优先完成预检查和静态 benchmark；
Alpha101/AutoAlpha 的 blocker 不应阻止已可复刻分支继续，但不得用近似名称补齐论文
表格。

---

## 13. 允许与禁止的最终声明

若全部通过，允许：

```text
paper_protocol_grounded_multi_library_pit_replication
alpha20_alpha158_dual_start_evolution_supported
factor_library_efficiency_supported
conditional_joint_scheduler_efficiency_supported
```

始终禁止：

```text
exact paper reproduction
paper Table 1 reproduced
AutoAlpha reproduced without exact artifact
true OOS support
production alpha confirmed
production deployment authorized
```
