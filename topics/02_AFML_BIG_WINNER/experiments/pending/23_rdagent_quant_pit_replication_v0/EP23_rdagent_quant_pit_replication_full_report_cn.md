# EP23：R&D-Agent-Quant PIT Universe 复刻与初步验证完整报告

> Episode：`23_rdagent_quant_pit_replication_v0`
>
> 报告日期：2026-07-27
>
> 论文：Li et al. (2025), *R&D-Agent-Quant: A Multi-Agent Framework for
> Data-Centric Factors and Model Joint Optimization*
>
> 本地论文：[2505.15155v2.pdf](2505.15155v2.pdf)
>
> 证据身份：`design_contaminated_historical_real_market_evidence`
>
> 当前总裁决：`model_branch_only_supported`
>
> 部署授权：`false`

---

## 1. 执行摘要

EP23 的目标不是机械复现论文表格中的 CSI300 数值，而是检验：

> 在本项目 close-observed、next-session executable 的动态 PIT 大盘股
> universe 中，R&D-Agent-Quant 的因子生成、模型生成与归因流程，能否相对
> 固定 Alpha20/LightGBM 基线产生稳定、非冗余、成本后仍有意义，并对
> Big Winner 有增量效用的横截面信号。

截至 23F，初步验证得到以下结论。

### 1.1 已经验证成立

1. OpenRouter、uv、RD-Agent、Qlib、PyTorch、PIT provider 和自动反馈链路能够
   完整运行。
2. Agent 能生成可执行因子和模型代码，但候选必须经过独立、matched-seed
   归因；不能直接接受 Agent 自身给出的替换结论。
3. 因子分支中，`close_momentum_20d`、`volume_surprise_20d` 和
   `volatility_20d` 获得不同程度支持。
4. 模型分支中，20 日时序的 last-state GRU 相对容量匹配的 flattened MLP
   存在稳定增量：

   - validation IC：5/5 seeds 改善；
   - historical-test IC、RankIC：5/5 seeds 改善；
   - 毛 ARR：4/5 seeds 改善；
   - 净 ARR：3/5 seeds 改善。

5. last-state GRU 的正绝对收益在完整 next-open 执行状态机中没有符号反转，
   五个正式 seed 的 executable net ARR 全部为正。

### 1.2 没有验证成立

1. Attention pooling 没有增量，不能把“更复杂模型”解释为更优模型。
2. 主 GRU 策略虽然有正绝对收益，但没有战胜同期沪深 300、全 A 指数或
   PIT universe 等权。
3. 模型没有形成 Big Winner 增量：

   - winner episode recall 为 `291 / 545 = 53.39%`；
   - right-tail exposure enrichment 只有 `0.872x`；
   - 模型实际低配了 winner episode 区间。

4. 当前结果不能标记为 `historical_forward_freeze_candidate`，更不能解释为
   生产 alpha 或真实未来有效。

### 1.3 最重要的研究解释

last-state GRU 学到的更像是：

```text
短周期平均收益排序 + 明显的左尾规避
```

而不是：

```text
Big Winner 右尾发现或右尾水库选择
```

它将严重左尾暴露率从 eligible universe 的 `4.59%` 降至 `1.13%`，但同时把
right-tail exposure rate 从 universe 的 `55.55%` 降至 `48.44%`。因此它更适合
作为防御型 participation filter、风险 overlay 或 meta-label 候选，而不是直接
作为 Big Winner selector。

---

## 2. 研究身份与复刻边界

### 2.1 本项目复刻什么

EP23 复刻论文的研究协议和控制结构：

- 初始因子库为 Alpha20；
- R&D-Factor 固定 LightGBM，只搜索因子；
- R&D-Model 固定 Alpha20，只搜索模型；
- joint agent 计划在 factor/model action 之间调度；
- 因子与 SOTA 平均横截面相关性达到 `0.99` 时去重；
- 采用 IC、ICIR、RankIC、RankICIR、ARR、IR、MDD、turnover 等指标；
- 采用 Top50/drop5 与买卖成本代理；
- 使用多 seed 和 matched comparison，而不是依赖一次随机运行。

本地复刻身份固定为：

```text
paper_protocol_grounded_pit_universe_project_adaptation
```

### 2.2 本项目不复刻什么

论文和本地实验存在不可消除的差异：

| 维度 | 论文 | EP23 |
|---|---|---|
| universe | CSI300 | 动态 `pit_largecap_main_chinext` |
| 数据期 | 2008–2020 主实验 | 2017–2026-05 |
| 数据源 | 含 Wind 扩展字段 | OHLCV、money、turnover、factor |
| LLM backend | GPT-4o、o3-mini | OpenRouter / GPT-5.6-sol |
| runtime | 官方 conda/docker 路径 | uv adapter |
| 交易叙述 | t+1 open，但模板存在 close 语义 | paper proxy 与 next-open bridge 分开 |
| test 身份 | 论文 OOS | 项目已反复观察的历史诊断样本 |

因此禁止以下声明：

```text
exact_replication
paper_table_1_reproduced
paper_csi300_result_reproduced
autonomous_alpha_confirmed
production_strategy_authorized
```

---

## 3. 环境、模型和凭据配置

### 3.1 RD-Agent

| 项目 | 当前值 |
|---|---|
| checkout | `/home/xiaolv/code/RD-Agent` |
| commit | `4f9ecb00` |
| environment | uv / Python 3.11 |
| Docker | 不可用，但非本项目必要条件 |
| adapter diff SHA256 | `fb6f2054aec9117673a5fff3bf761e9ece74de37d67224195ed3a2a627d93b15` |
| adapter diff match | true |

### 3.2 OpenRouter

| 角色 | 模型 |
|---|---|
| chat | `openai/gpt-5.6-sol` |
| embedding | `openai/text-embedding-3-small` |
| provider route | OpenRouter |
| HTTP proxy | 已配置并通过实际调用验证 |

凭据只保存在 RD-Agent 本地 `.env`，未写入 EP23 配置、报告、trace 或 Git。
正式 workspace 和日志的 key 扫描命中数为 0。

### 3.3 已修复的 runtime 问题

本轮发现并处理了以下官方 runtime 与本地合同差异：

1. 官方 Qlib runtime 对 conda/docker 存在硬编码，已增加 uv adapter。
2. 模型 feedback 曾发生重复 LLM 调用，已移除。
3. non-quant model feedback fallback 曾错误使用 factor system prompt，已修正。
4. Agent 模型 spec 声明的优化器/clip/scheduler 与 GeneralPTNN 实际运行不一致；
   正式归因以实际 runtime 为准。
5. Agent 候选 `forward()` 写出 `output.pth` 的副作用已在受控归因中移除。
6. 因子同名覆盖风险已改为 SOTA-first，并在最终合并前再次检查重复列。

---

## 4. PIT 数据与时点合同

### 4.1 数据清单

| 项目 | 值 |
|---|---:|
| calendar | 2017-01-03 至 2026-05-29 |
| sessions | 2,281 |
| historical PIT-eligible instruments | 862 |
| instrument interval rows | 5,697 |
| price-provider instruments | 4,597 |
| missing PIT feature directories | 0 |
| primary fields | open/high/low/close/volume/factor/money/turnover_rate |

Universe membership 采用 close-observed 语义：

```text
membership observed at close D
-> usable from next session
```

不能用当前静态指数成分股回填历史。

### 4.2 时间切分

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

目标收益终点不得跨越下一 split。由于本项目已经多次观察历史 test，其证据等级
固定为：

```text
design_contaminated_historical_real_market_evidence
```

### 4.3 双标签 lane

论文交易文字和官方 Qlib template 的价格语义并不完全一致，因此 EP23 不把两者
混为一谈。

```text
PAPER_PROXY:
    score observed at close t
    return = close(t+2) / close(t+1) - 1

EXECUTABLE_BRIDGE:
    score observed at close t
    return = open(t+2) / open(t+1) - 1
```

前者用于与论文模板和 Agent loop 对齐；后者用于判断从 close proxy 转向
next-open 后是否发生方向翻转。23F 进一步使用状态机逐笔模拟真实约束。

---

## 5. 实验路径和当前完成度

| 阶段 | 内容 | 状态 | 当前裁决 |
|---|---|---|---|
| 23A | paper/data/runtime preflight | 完成 | ready |
| 23B | Alpha20/LightGBM 五 seed baseline | 完成 | weak comparator |
| 23C | 单轮 R&D-Factor smoke | 完成 | 需受控归因 |
| 23C1 | 四因子 matched ablation | 完成 | momentum/volume 有支持 |
| 23C2 | 因子交互隔离 | 完成 | momentum+volume 核心 |
| 23C3 | 修正后的 Agent factor Loop 0 | 完成 | 联合包改善 |
| 23C4 | 新因子边际归因 | 完成 | retain volatility |
| 23D | 单轮 R&D-Model smoke | 完成 | attention 候选拒绝 |
| 23D1 | 三 seed 模型结构归因 | 完成 | retain last-state GRU |
| 23D2 | 五 seed 正式模型归因 | 完成 | pending 23F |
| 23E | joint factor/model scheduler | 未执行 | 不作成败结论 |
| 23F | 完整 PIT 执行与 Big Winner bridge | 完成 | model branch only |

23E 尚未执行，因此本报告不能评价 contextual Thompson sampling 是否优于 random
或 LLM scheduler。

---

## 6. 23A：预检查结果

23A 当前裁决：

```text
ready_for_deterministic_baseline = true
ready_for_agent_loop             = true
claim_ceiling                    = paper_protocol_grounded_pit_agent_loop_ready
```

已通过：

- 论文 SHA256；
- RD-Agent commit 和 adapter diff；
- PIT calendar、instrument、feature inventory；
- Alpha20 smoke；
- PAPER_PROXY / EXECUTABLE_BRIDGE label smoke；
- uv、chat model、embedding model 和 provider credential 静态就绪检查。

这只授权启动实验，不代表论文结果或 alpha 已被复现。

详细证据：
[23A 报告](outputs/23A_rdagent_pit_preflight/23A_rdagent_pit_preflight_report.md)。

---

## 7. 23B：Alpha20/LightGBM 基线

### 7.1 预测能力

selected seed 只由 validation PAPER_PROXY Pearson IC 选择：

| split / lane | IC | ICIR | RankIC | RankICIR |
|---|---:|---:|---:|---:|
| validation / PAPER_PROXY | 0.012372 | 0.108351 | 0.008676 | 0.073573 |
| validation / EXECUTABLE_BRIDGE | 0.010386 | 0.095240 | 0.009542 | 0.083656 |
| historical test / PAPER_PROXY | 0.008618 | 0.072712 | 0.010504 | 0.084241 |
| historical test / EXECUTABLE_BRIDGE | 0.010332 | 0.085726 | 0.009849 | 0.078584 |

Alpha20 存在弱正排序信息，但 IC 和 ICIR 都不高。

### 7.2 Top50/drop5 代理

| lane | gross ARR | net ARR | universe EW ARR | active IR | MDD |
|---|---:|---:|---:|---:|---:|
| PAPER_PROXY | 19.37% | 13.13% | 20.70% | -0.768 | -19.17% |
| EXECUTABLE_BRIDGE | 21.17% | 14.84% | 22.21% | -0.722 | -20.78% |

五个 seed 的两条 lane active IR 全部为负。基线具有正绝对收益，但没有战胜
PIT universe beta，是 Agent 后续必须超过的弱 comparator，不是成功策略。

此外，冻结的强正则 LightGBM 在 selected seed 上 best iteration 仅为 6，
说明 comparator 可能偏欠拟合。后续模型增量必须同时与容量匹配控制比较，不能
只战胜该 LightGBM 就认定成功。

详细证据：
[23B 报告](outputs/23B_alpha20_lgbm_pit_baseline/23B_alpha20_lgbm_pit_baseline_report.md)。

---

## 8. 23C：因子分支

### 8.1 为什么不能直接接受 Agent Loop 结果

原始因子 loop 存在两类混杂：

1. baseline 与 candidate preprocessing 不一致；
2. Agent 新生成的 `volume_surprise_20d` 与冻结核心因子同名，旧 runner 在最终
   合并时让新列覆盖了 SOTA 列。

因此原始一次性改善不能解释为新增因子的边际贡献。修复后采取：

- matched train-only robust z-score；
- 相同 split、LightGBM、seed、Top50/drop5 和成本；
- SOTA-first 同名保护；
- correlation 去重；
- single-addition、interaction 和 leave-one-out 归因。

### 8.2 第一批因子消融

五 seed 中位数：

| 变体 | PAPER IC | PAPER net ARR | executable net ARR |
|---|---:|---:|---:|
| Alpha20 | 0.007892 | 13.13% | 14.84% |
| + close_momentum_20d | 0.009726 | 18.15% | 19.42% |
| + close_reversal_5d | 0.010603 | 12.08% | 13.11% |
| + daily_close_location_value | 0.004115 | 7.35% | 10.09% |
| + volume_surprise_20d | 0.008331 | 14.85% | 16.32% |
| + all four | 0.006669 | 17.14% | 21.14% |

结论：

- `close_momentum_20d` 是最明确的单因子贡献者；
- `volume_surprise_20d` 是较弱的条件贡献者；
- `close_reversal_5d` 出现 IC 增加但组合收益下降；
- `daily_close_location_value` 单独显著拖累。

### 8.3 交互隔离

| 变体 | PAPER net ARR | executable net ARR |
|---|---:|---:|
| Alpha20 | 13.13% | 14.84% |
| + momentum | 18.15% | 19.42% |
| + volume | 14.85% | 16.32% |
| + momentum + volume | 20.02% | 22.49% |
| + core + reversal | 15.43% | 18.71% |
| + core + close-location | 17.12% | 21.95% |
| + all four | 17.14% | 21.14% |

四因子联合不如 `momentum + volume`。23C1 中“弱因子可能通过交互提供贡献”的
假设被否定。

第一版核心库冻结为：

```text
Alpha20
+ close_momentum_20d
+ volume_surprise_20d
```

### 8.4 修正后的 Agent 因子 Loop 0

Agent 新提出：

- `reversal_5d`
- `volatility_20d`
- `intraday_range_1d`

修正后的 Qlib 单次比较：

| metric | fixed-core baseline | joint candidate | delta |
|---|---:|---:|---:|
| IC | 0.008419 | 0.013214 | +0.004795 |
| RankIC | 0.005548 | 0.011929 | +0.006381 |
| net excess ARR | -6.15% | 3.93% | +10.08 pp |
| net excess IR | -0.837 | 0.473 | +1.310 |
| net excess MDD | -23.17% | -19.19% | +3.98 pp |

这只能授权“联合包进入边际归因”，不能证明三个因子都有效。

### 8.5 新因子边际归因

| 因子 | PAPER paired ΔARR | executable paired ΔARR | action |
|---|---:|---:|---|
| reversal_5d | +1.19% | -1.19% | reject |
| volatility_20d | +3.79% | +1.72% | retain primary |
| intraday_range_1d | +4.24% | +3.29% | supported alternative |

虽然 `intraday_range_1d` 单独有证据，但与 volatility 联合后 executable
增量为负，且直接比较没有支持把二者同时加入。

最终冻结因子库：

```text
Alpha20
+ close_momentum_20d
+ volume_surprise_20d
+ volatility_20d
```

`intraday_range_1d` 保留为不与 volatility 同时使用的备选；
`reversal_5d` 被拒绝。

详细证据：

- [23C1 报告](outputs/23C1_controlled_factor_ablation/23C1_controlled_factor_ablation_report.md)
- [23C2 报告](outputs/23C2_factor_interaction_isolation/23C2_factor_interaction_isolation_report.md)
- [23C3 报告](outputs/23C3_corrected_rdagent_evolution_loop_0/23C3_corrected_rdagent_evolution_loop_0_report.md)
- [23C4 报告](outputs/23C4_new_factor_marginal_attribution/23C4_new_factor_marginal_attribution_report.md)

---

## 9. 23D：模型分支

### 9.1 Agent 原始 Attentive GRU smoke

首个 R&D-Model loop 生成 `CompactAttentiveGRU128`。单次 Qlib 比较：

| metric | Alpha20-LightGBM | Attentive GRU | delta |
|---|---:|---:|---:|
| IC | 0.008419 | 0.004131 | -0.004288 |
| RankIC | 0.005548 | 0.023586 | +0.018039 |
| gross excess ARR | -1.41% | -2.56% | -1.15 pp |
| net excess ARR | -6.15% | -5.73% | +0.42 pp |

净结果表面改善 `0.42 pp`，但毛收益恶化 `1.15 pp`；净改善完全来自成本拖累减少
`1.57 pp`。因此正确标签是：

```text
cost_artifact_smoke_only
```

而不是模型有效。

### 9.2 三 seed 结构归因

在完全相同的 Alpha20 × 20 timesteps、seed、processor、Adam/MSE、scheduler、
gradient clip 和组合规则下比较：

| 模型 | 参数量 | validation IC | test IC | test RankIC | gross ARR | net ARR |
|---|---:|---:|---:|---:|---:|---:|
| flattened MLP | 163,809 | 0.006268 | 0.005260 | 0.012580 | 16.63% | 10.62% |
| last-state GRU | 165,249 | 0.023038 | 0.015957 | 0.028426 | 35.44% | 28.09% |
| attentive GRU | 173,569 | 0.012212 | 0.012455 | 0.025172 | 16.82% | 11.41% |

last-state GRU 相对 MLP 的三 seed paired median：

| metric | delta | positive seeds |
|---|---:|---:|
| validation IC | +0.016547 | 3/3 |
| test IC | +0.011655 | 3/3 |
| test RankIC | +0.019124 | 3/3 |
| gross ARR | +11.08 pp | 3/3 |
| net ARR | +10.09 pp | 2/3 |

Attention 相对 last-state GRU：

| metric | delta | positive seeds |
|---|---:|---:|
| validation IC | -0.010603 | 0/3 |
| test RankIC | -0.008316 | 1/3 |
| gross ARR | -11.50 pp | 1/3 |
| net ARR | -10.23 pp | 1/3 |

由此拒绝 attention pooling，但保留 recurrent backbone。

### 9.3 五 seed 正式归因

| 模型 | validation IC | test IC | test RankIC | gross ARR | net ARR | turnover |
|---|---:|---:|---:|---:|---:|---:|
| flattened MLP | 0.004530 | 0.005260 | 0.011854 | 16.74% | 10.73% | 0.1054 |
| last-state GRU | 0.023038 | 0.015957 | 0.028426 | 35.44% | 28.09% | 0.1112 |

last-state GRU 相对 MLP：

| metric | median delta | positive seeds |
|---|---:|---:|
| validation IC | +0.021732 | 5/5 |
| test IC | +0.011655 | 5/5 |
| test RankIC | +0.018183 | 5/5 |
| gross ARR | +11.08 pp | 4/5 |
| net ARR | +10.09 pp | 3/5 |
| turnover | +0.005156 | — |

增量不能由更低换手或更低成本解释。模型分支因此进入 23F，但尚未获得策略授权。

详细证据：

- [23D smoke 报告](outputs/23D_rdagent_model_loop_0_smoke/23D_rdagent_model_loop_0_smoke_report.md)
- [23D1 报告](outputs/23D1_controlled_model_attribution/23D1_controlled_model_attribution_report.md)
- [23D2 报告](outputs/23D2_formal_last_state_gru_attribution/23D2_formal_last_state_gru_attribution_report.md)

---

## 10. 23F：完整 PIT 执行验证

### 10.1 主 seed 冻结

主 seed 只按 validation PAPER_PROXY IC 最大选择，并列时取较小 seed：

```text
primary_seed = 20260725
selection_uses_historical_test = false
```

该 seed 在 historical-test ARR 上并不是五个 seed 中最佳值，避免了用 test 收益
挑 seed 的乐观偏差。

### 10.2 执行状态机

23F 不再把 `open-to-open` label 直接当成可成交收益，而是：

- decision close 后下一交易日开盘下单；
- raw price 用于涨跌停判断；
- qfq price 用于持仓连续计值；
- 涨停买入阻塞；
- 跌停卖出阻塞并在后续交易日重试；
- 停牌/缺 bar 保留现金或锁定原持仓；
- 买入按整手规则向下取整；
- 处理佣金最低额、卖出印花税、过户费和 5bps 单边滑点；
- 不借款、不加杠杆、不做空；
- 未分配资金保留为现金。

主路径共观察到 46 次 blocked order：

| 原因 | 次数 |
|---|---:|
| suspended / missing bar | 40 |
| limit-up blocked buy | 4 |
| limit-down blocked sell | 2 |

### 10.3 PAPER_PROXY 与 executable 结果

| lane | gross ARR | net ARR | IR | MDD | one-way turnover |
|---|---:|---:|---:|---:|---:|
| PAPER_PROXY Top50/drop5 | 16.67% | 10.60% | 0.685 | -15.58% | 0.1064 |
| EXECUTABLE Top50/drop5 | 14.83% | 9.10% | 0.549 | -15.82% | 0.1007 |
| EXECUTABLE Top30/drop5 | 10.89% | 1.84% | 0.188 | -19.48% | 0.1674 |

结论：

- 从 paper proxy 转到现实 next-open 执行后，收益下降但没有符号反转；
- 五个 seed 的 Top50 executable net ARR 全部为正；
- Top30 显著恶化，说明集中持仓没有增强信号，反而放大了换手和组合噪声。

### 10.4 同期基准

| comparator | ARR | IR | MDD |
|---|---:|---:|---:|
| last-state GRU executable net | 9.10% | 0.549 | -15.82% |
| SH000300 | 17.97% | 0.884 | -19.15% |
| 全 A / SH000985 | 18.81% | 0.817 | -17.27% |
| PIT universe equal-weight | 22.21% | 0.956 | -20.47% |

GRU 的最大回撤小于三个股票基准，但收益也明显更低。它体现了风险压缩，不体现
相对 universe 的 alpha：

```text
strategy net ARR - PIT universe ARR
= 9.10% - 22.21%
= -13.11 percentage points
```

因此 `universe_equal_weight_increment_gate = FAIL`。

---

## 11. Big Winner utility 与 morphology

### 11.1 定义

Big Winner 使用 EP15 path-defined `up50pct` episode，而不是简单地把任意未来
120 日上涨 50% 的单日样本当作独立 winner。

- right-tail exposure day：实际持仓日落在 up50 episode interval；
- false-positive exposure day：实际持仓日不落在任何 up50 interval；
- episode recall：至少被实际持仓覆盖一次的 episode 占比；
- severe left tail：持仓开盘后 20 个交易日内最低 qfq low 相对当前 qfq open
  不高于 `-20%`；
- morphology independence：检查捕获是否只来自单一路径类型。

这些都是 ex-post utility attribution，不能回灌到训练特征。

### 11.2 总体结果

| 指标 | 结果 |
|---|---:|
| eligible up50 episodes | 545 |
| captured episodes | 291 |
| episode recall | 53.39% |
| holding exposure days | 28,936 |
| right-tail exposure days | 14,017 |
| false-positive exposure days | 14,919 |
| strategy right-tail exposure rate | 48.44% |
| universe right-tail exposure rate | 55.55% |
| right-tail enrichment | 0.872x |
| strategy severe-left-tail rate | 1.13% |
| universe severe-left-tail rate | 4.59% |
| left-tail excess | -3.46 pp |

episode 区间本身较宽，因此 eligible universe 有 `55.55%` 的 stock-day 位于
episode interval。23F 对策略和 universe 使用完全相同的 interval、日期和股票
分母。`0.872x` 不是分母错位，而是模型确实低配右尾区间。

### 11.3 Morphology 分解

| morphology | eligible | captured | recall |
|---|---:|---:|---:|
| jump repricing | 42 | 19 | 45.24% |
| late rescue | 193 | 70 | 36.27% |
| slow grind | 104 | 85 | 81.73% |
| smooth trend | 33 | 17 | 51.52% |
| stair step | 7 | 6 | 85.71% |
| unclassified mixed | 155 | 94 | 60.65% |
| unclassified short | 11 | 0 | 0.00% |

通过的 morphology gates：

- 至少 10 episodes 的 material morphology 中，`83.33%` 至少捕获一次；
- 最大 captured morphology share 为 `32.30%`，低于 `70%` 上限。

因此捕获并非完全由单一路径形态驱动。但 morphology independence 只能排除
“单一形态垄断”的解释，不能覆盖 right-tail enrichment `< 1`。

### 11.4 AFML 裁决

```text
episode capture                    PASS
morphology coverage               PASS
morphology concentration          PASS
left-tail burden                   PASS
right-tail exposure enrichment     FAIL
```

该模型减少左尾的能力是真实且显著的，但它没有形成 right-tail reservoir。

详细证据：
[23F 报告](outputs/23F_pit_execution_big_winner_bridge/23F_pit_execution_big_winner_bridge_report.md)。

---

## 12. 总 gate 矩阵

| Gate | 结果 | 核心证据 |
|---|---|---|
| paper/data/runtime readiness | PASS | 23A ready |
| deterministic baseline | PASS | 23B 五 seed 完成 |
| factor implementation/PIT | PASS | 因子索引、覆盖、未来字段审计通过 |
| factor marginal support | PARTIAL | momentum、volume、volatility 保留 |
| attention increment | FAIL | validation IC 0/3 改善 |
| recurrent backbone increment | PASS | IC/RankIC 5/5 |
| non-cost-artifact model gain | PASS | 毛收益改善，turnover 增量小 |
| executable sign preservation | PASS | 5/5 executable net ARR 为正 |
| blocked-fill materialization | PASS | 三类阻塞均实际出现 |
| PIT universe increment | FAIL | 9.10% vs 22.21% |
| Big Winner episode capture | PASS | 291/545 |
| right-tail enrichment | FAIL | 0.872x |
| severe-left-tail burden | PASS | 1.13% vs 4.59% |
| morphology independence | PASS | 最大形态占比 32.30% |
| joint scheduler increment | NOT RUN | 23E 未执行 |
| true-forward support | NOT RUN | 无独立未来期 |
| deployment | FAIL CLOSED | authorized=false |

最终裁决：

```text
model_branch_only_supported
```

---

## 13. 因果诊断：为什么模型 IC 改善，但策略和 Big Winner gate 失败

### 13.1 训练目标与项目目标不一致

模型训练目标是下一期横截面标准化收益的 MSE，选择指标以 validation IC 为主。
该目标更重视：

- 大量普通 stock-day 的平均排序；
- 小幅正负收益的整体相关性；
- 对高频常见状态的拟合。

Big Winner 目标关注：

- 稀疏右尾 episode；
- 长期路径形态；
- 右尾捕获是否足以支付左尾和持仓暴露成本。

因此 IC 提升不自动意味着右尾增益。

### 13.2 GRU 形成了防御性，而不是右尾凸性

最直接的证据是：

```text
severe left tail: 4.59% -> 1.13%
right-tail exposure: 55.55% -> 48.44%
```

模型同时削弱了两端的极端暴露，更像风险压缩器。它可能通过避开高波动、状态不稳
或短期反转股票改善平均 MSE/IC，却牺牲了 Big Winner 必需的正向凸性。

### 13.3 本地样本具有强 beta

PIT universe 等权 ARR 为 `22.21%`，明显高于主策略的 `9.10%`。在该历史期，
保持广泛股票暴露本身具有较高收益。GRU 通过降低风险和集中于更稳定股票减少回撤，
但付出了较大的 beta/upside participation 代价。

### 13.4 Top30 结果否定“提高集中度即可修复”

Top30 净 ARR 只有 `1.84%`，低于 Top50 的 `9.10%`，同时：

- turnover 从 `0.1007` 上升至 `0.1674`；
- MDD 从 `-15.82%` 恶化至 `-19.48%`。

因此问题不是 Top50 过度稀释；简单提高集中度会放大信号误差和交易成本。

### 13.5 validation 选择没有使用 test，但目标仍不对齐

主 seed `20260725` 由 validation IC 选择，而不是 test ARR。它在五个 seed 中的
historical-test 策略收益并不突出。这说明流程避免了明显的 test cherry-pick，
但也进一步表明：

> validation IC 最大，并不等于执行收益最大，更不等于 Big Winner utility 最大。

正确修复方向应是重新定义研究目标和多目标 gate，而不是换一个 test 表现更好的
seed。

---

## 14. 已验证、已否证和仍未回答的问题

### 14.1 已验证

- 官方 RD-Agent 可以通过 uv adapter 在本项目环境运行；
- OpenRouter chat/embedding 能支持真实 Agent loop；
- Agent factor/model 代码能进入 Qlib 训练和回测；
- SOTA-first、相关性去重和 matched attribution 是必要保护；
- momentum/volume/volatility 因子具有局部支持；
- last-state GRU 时序主干相对 MLP 有稳定预测增量；
- paper proxy 到完整 next-open 执行没有符号翻转；
- 模型具有明显的严重左尾规避能力。

### 14.2 已否证

- 更复杂的 attention pooling 自动优于 last-state 表示；
- 单次 Agent `Replace Best` 足以证明每个新增因子有效；
- 正 ARR 足以授权策略；
- IC/RankIC 改善自动转化为 universe alpha；
- 当前 GRU 是 Big Winner selector；
- 把 Top50 收缩至 Top30 可以修复 Big Winner 效用。

### 14.3 仍未回答

- contextual Thompson sampling 是否比 random/LLM scheduler 更高效；
- factor/model joint search 是否优于最好的单分支冻结候选；
- GRU 作为 participation/meta-label 是否能改善一个独立 right-tail reservoir；
- 重新设计为 tail-aware objective 后是否仍能保持左尾优势；
- 在真正未观察的未来期是否继续有效；
- 盘口排队、分钟级涨跌停打开、容量和冲击成本下是否可执行。

---

## 15. 研究局限

1. historical test 已被多次观察，不能视为 true OOS。
2. 本地 universe、数据期和字段集与论文 CSI300/Wind 实验不同。
3. 基础 LightGBM comparator 偏强正则且可能欠拟合。
4. PAPER_PROXY 和正式执行语义不同，虽然 23F 已补充状态机，仍缺少分钟级盘口。
5. Big Winner episode 是 ex-post path-defined label，不能直接用于实时决策。
6. EP15 episode interval 较宽，必须始终与 matched universe 分母比较。
7. 当前模型目标是一日收益 MSE，不是 right-tail utility。
8. 23E 尚未执行，无法评估论文 joint scheduler 的核心主张。
9. LiteLLM 缺少当前 OpenRouter 模型价格映射，因此 token 可记录，美元成本不可用；
   不得把 unavailable 记为 0。
10. RD-Agent checkout 含项目 adapter 改动，不是 clean upstream；已通过 commit 和
    adapter hash 分开记录。

---

## 16. 下一阶段建议

### 16.1 不建议立即扩大 23E 预算

当前 factor/model 两个分支都没有通过 universe 增量和 Big Winner utility gate。
直接运行完整 12 小时 joint scheduler，很可能只是在错误目标上扩大搜索预算。

在运行 23E 前，应先冻结新的多目标 acceptance contract：

```text
validation predictive gain
+ executable gross/net gain
+ PIT universe active gain
+ right-tail enrichment
+ left-tail budget
+ turnover/cost budget
```

### 16.2 将 GRU 降级为 participation/meta-label 候选

建议检验：

```text
independent right-tail reservoir signal
    -> GRU risk filter / abstention overlay
    -> compare right-tail retention vs left-tail removal
```

GRU 只有在保留足够 right-tail exposure 的同时减少左尾，才具有 AFML utility。

### 16.3 单独建立 tail-aware selector

下一模型不应继续只优化一日 MSE。可考虑：

- episode-aware sample weighting；
- asymmetric payoff loss；
- top-tail contribution objective；
- winner recall 与 false-positive exposure 的多目标约束；
- morphology-balanced validation；
- horizon ensemble，而不是单一 next-day label；
- 把普通 alpha 排序与 Big Winner selector 明确拆成两个模型。

### 16.4 进入 true-forward freeze 的最低条件

只有同时满足以下条件，才应冻结新的 forward candidate：

1. validation predictive improvement；
2. 五 seed 至少 3 个方向一致；
3. executable bridge 不反转；
4. net return 超过 PIT universe 或明确的经济 hurdle；
5. right-tail enrichment `> 1`；
6. 左尾下降不以不可接受的 right-tail sacrifice 换取；
7. morphology 不集中于单一路径；
8. search accounting、代码、配置和数据 hash 完整；
9. candidate 冻结后再开启独立、未观察的 true-forward 期。

---

## 17. 复现入口

以下命令从 `topics/02_AFML_BIG_WINNER` 执行。

### 17.1 Preflight

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23a_rdagent_pit_preflight.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

### 17.2 Alpha20 baseline

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23b_alpha20_lgbm_baseline.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

### 17.3 因子归因

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23c1_controlled_factor_ablation.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml

uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23c2_factor_interaction_isolation.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml

uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23c4_new_factor_marginal_attribution.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

### 17.4 模型归因

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23d1_controlled_model_attribution.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml \
  --mode formal
```

### 17.5 完整执行与 Big Winner bridge

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23f_pit_execution_big_winner_bridge.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

### 17.6 验证

```bash
uv run pytest -q \
  experiments/pending/23_rdagent_quant_pit_replication_v0/tests

uv run ruff check \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src \
  experiments/pending/23_rdagent_quant_pit_replication_v0/tests
```

当前验证结果：

```text
pytest: 12 passed
ruff: passed
preflight: ready_for_agent_loop=true
23F registered output hash mismatches: 0
credential scan: clean
```

---

## 18. 关键产物索引

| 产物 | 路径 |
|---|---|
| research plan | [research_plan.md](research_plan.md) |
| runbook | [runbook.md](runbook.md) |
| config | [config.yaml](config.yaml) |
| 23A report | [23A](outputs/23A_rdagent_pit_preflight/23A_rdagent_pit_preflight_report.md) |
| 23B report | [23B](outputs/23B_alpha20_lgbm_pit_baseline/23B_alpha20_lgbm_pit_baseline_report.md) |
| 23C1 report | [23C1](outputs/23C1_controlled_factor_ablation/23C1_controlled_factor_ablation_report.md) |
| 23C2 report | [23C2](outputs/23C2_factor_interaction_isolation/23C2_factor_interaction_isolation_report.md) |
| 23C3 report | [23C3](outputs/23C3_corrected_rdagent_evolution_loop_0/23C3_corrected_rdagent_evolution_loop_0_report.md) |
| 23C4 report | [23C4](outputs/23C4_new_factor_marginal_attribution/23C4_new_factor_marginal_attribution_report.md) |
| 23D smoke | [23D](outputs/23D_rdagent_model_loop_0_smoke/23D_rdagent_model_loop_0_smoke_report.md) |
| 23D1 report | [23D1](outputs/23D1_controlled_model_attribution/23D1_controlled_model_attribution_report.md) |
| 23D2 report | [23D2](outputs/23D2_formal_last_state_gru_attribution/23D2_formal_last_state_gru_attribution_report.md) |
| 23F report | [23F](outputs/23F_pit_execution_big_winner_bridge/23F_pit_execution_big_winner_bridge_report.md) |
| 23F gate audit | [gate_audit.csv](outputs/23F_pit_execution_big_winner_bridge/gate_audit.csv) |
| 23F executable summary | [executable_summary.csv](outputs/23F_pit_execution_big_winner_bridge/executable_summary.csv) |
| 23F Big Winner readout | [big_winner_utility_readout.csv](outputs/23F_pit_execution_big_winner_bridge/big_winner_utility_readout.csv) |

---

## 19. 最终结论

EP23 已证明，R&D-Agent-Quant 的自动因子/模型研究链路可以在本项目 PIT universe
中通过 uv 和 OpenRouter 运行，并能产生需要认真归因的候选。自动研发框架本身
具有工程可行性，last-state GRU 也确实比容量匹配的 MLP 提供了稳定的短周期预测
增量。

但策略层面的结论不同：

```text
正绝对收益                         已观察
相对 MLP 的模型增量                得到支持
paper-to-executable sign            保持
相对 PIT universe 的收益增量        未得到支持
Big Winner right-tail 增量          未得到支持
左尾风险压缩                        得到支持
生产或 true-forward 授权            不允许
```

因此最准确的当前表述是：

> R&D-Agent 模型分支在设计污染的 PIT 历史样本中获得局部支持；last-state GRU
> 具有可执行的正绝对收益和明显左尾规避能力，但没有战胜 universe beta，也没有
> 形成 Big Winner 右尾富集。该候选应降级为 participation/meta-label 研究对象，
> 而不是作为 Big Winner selector 或生产策略晋级。
