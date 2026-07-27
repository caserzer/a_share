# Episode 23 Research Plan：用 PIT Universe 近似复现 R&D-Agent(Q)

> 文档状态：`active_project_adaptation`
>
> 生成日期：2026-07-27
>
> Episode ID：`23_rdagent_quant_pit_replication_v0`
>
> 论文：Li et al. (2025), *R&D-Agent-Quant: A Multi-Agent Framework for
> Data-Centric Factors and Model Joint Optimization*
>
> 本地论文：`2505.15155v2.pdf`
>
> 论文 SHA256：
> `5df0919520ec1a9d556f6a20bc10e9d2d1dc11cada2e6913b871239df63a2df2`
>
> 官方实现 checkout：`/home/xiaolv/code/RD-Agent`
>
> checkout commit：`4f9ecb00`
>
> Python 环境：只使用 `uv`，不创建或调用 conda environment

## 0. 一页结论

EP23 不把论文表 1 的数值当作本地验收阈值，也不把在另一个 universe、另一个时期、
另一个 LLM backend 上重新运行官方代码称为 exact replication。EP23 回答：

> 在项目 close-observed、next-session executable 的 PIT 大盘股 universe 中，
> R&D-Agent(Q) 的 factor、model 和 joint factor-model 三种搜索流程，是否相对固定
> Alpha20/LightGBM 基线产生稳定、非冗余、成本后仍有意义的横截面收益排序增量？

复刻身份固定为：

```text
paper_protocol_grounded_pit_universe_project_adaptation
```

禁止声明：

```text
exact_replication
paper_table_1_reproduced
paper_csi300_result_reproduced
autonomous_alpha_confirmed
production_strategy_authorized
```

论文可复刻的核心协议：

1. Alpha20 为初始 factor library；
2. `R&D-Factor` 固定 LightGBM，只搜索 factor；
3. `R&D-Model` 固定 Alpha20，只搜索 model；
4. `R&D-Agent(Q)` 在 factor/model 两个 action 间联合搜索；
5. joint primary scheduler 使用 contextual Thompson sampling；
6. factor 与现有 SOTA library 的平均横截面相关性达到 `0.99` 时去重；
7. 比较 IC、ICIR、RankIC、RankICIR、ARR、IR、MDD、Calmar；
8. 论文主预算为 factor 6 小时、model 6 小时、joint 12 小时；
9. 基线模型使用 5 个随机种子，ARR 报告中位数；
10. 论文 Qlib execution template 使用 Alpha20、LightGBM、Top50、drop5、
    `open_cost=0.0005`、`close_cost=0.0015`、涨跌停阈值 `0.095`。

本地必须改变：

- 论文主实验的 CSI300 和 `2008-2020` 数据不可由当前 PIT provider 重建；
- 本地使用动态 `pit_largecap_main_chinext`，不能改成当前静态成分股；
- 本地覆盖为 `2017-01-03` 至 `2026-05-29`；
- 论文主实验旧切分改为本地 `2017-2021 / 2022-2023 / 2024-2026-05`；
- 论文交易叙述写“t+1 open”，官方 YAML 却使用 `deal_price: close`；
- 官方 checkout 把 Qlib runtime 写死为 conda/docker，EP23 必须用 uv 适配；
- 论文使用的 Wind 基本面、分析师和资金流字段本地并不齐全，primary 只允许
  OHLCV/factor 可观测字段，缺失数据不得由当前值或事后值填充。

因此实验分为两个 score lane：

```text
PAPER_PROXY:
    score at close t
    label = close(t+2) / close(t+1) - 1
    与官方 Qlib template 对齐，用于比较 agent loop

EXECUTABLE_BRIDGE:
    score at close t
    enter at next executable open t+1
    return = open(t+2) / open(t+1) - 1
    用于项目可执行性诊断
```

两条 lane 必须并列报告，`PAPER_PROXY` 不能冒充 next-open 可执行收益。

当前 runtime 体检结论：

```text
PIT Qlib provider              ready
Alpha20 fields/label smoke     ready
uv project environment         ready
RD-Agent source checkout       ready
LLM chat configuration         ready: OpenRouter route verified
embedding configuration        ready: OpenRouter route verified
Docker                         unavailable in current WSL
official conda runtime         intentionally disallowed
single-loop factor/model smoke ready and completed
```

这不阻止 uv adapter 上的 autonomous loop。所有 agent-generated factor/model
仍必须与相同输入、相同标签、相同执行模拟器比较。

---

## 1. 论文实验档案

### 1.1 主实验

| 项目 | 论文设定 |
|---|---|
| market | CSI300 |
| train | 2008-01-01 至 2014-12-31 |
| validation | 2015-01-01 至 2016-12-31 |
| test | 2017-01-01 至 2020-08-01 |
| factor start | Alpha20 |
| factor optimizer comparator | LightGBM |
| model optimizer input | Alpha20 |
| R&D-Factor budget | 6 hours |
| R&D-Model budget | 6 hours |
| joint budget | 12 hours |
| implementation attempts/task | at most 10 |
| implementation timeout | 600 seconds |
| validation timeout | 3600 seconds |
| factor redundancy threshold | mean cross-sectional correlation `>= 0.99` |
| portfolio | Top50, drop5 |
| costs | buy 5 bps, sell 15 bps, min fee CNY 5 |
| reported agent backends | GPT-4o, o3-mini |

论文还报告 CSI500/NASDAQ100 的新切分实验：

```text
train 2008-2021
validation 2022-2023
test 2024-2025H1
```

EP23 的本地切分采用这个较新的时间结构，但训练起点受本地数据约束改为 2017。

### 1.2 三个主要 estimand

```text
E_factor:
    fixed LightGBM 下，agent factor set 相对 Alpha20 的增量

E_model:
    fixed Alpha20 下，agent model 相对 frozen LightGBM 的增量

E_joint:
    joint search 相对独立 factor/model search 的增量及 scheduler 效率
```

每个 estimand 都必须同时报告：

- predictive：IC、ICIR、RankIC、RankICIR；
- economic proxy：gross/net ARR、IR、MDD、Calmar、turnover；
- robustness：seed 分布、年度/半年稳定性、stock/date concentration；
- search accounting：total/valid/selected loop 数、wall time、token/cost；
- morphology：右尾捕获、左尾负担和 winner episode bridge。

论文数字仅作数量级 sanity check，不作为本地 pass/fail gate。

---

## 2. PIT 数据与时点合同

### 2.1 Universe

Primary market：

```text
provider:
  data/qlib/cn_data_pit_largecap

instrument:
  pit_largecap_main_chinext

membership:
  close-observed membership_date D
  -> usable_trade_date = next session
```

当前 provider inventory：

| 项目 | 当前值 |
|---|---:|
| sessions | 2281 |
| calendar | 2017-01-03 至 2026-05-29 |
| price-provider instruments | 4597 |
| historical PIT-eligible instruments | 862 |
| instrument interval rows | 5697 |
| fields | open/high/low/close/volume/factor/money/turnover_rate |

这些是运行前 inventory，不替代 23A 生成的 hash 和 coverage audit。

### 2.2 Split

```text
warmup:
    2017-01-03 .. 2017-03-31

train:
    decision dates 2017-04-03 .. 2021-12-29
    target end <= 2021-12-31

validation:
    decision dates 2022-01-04 .. 2023-12-27
    target end <= 2023-12-29

historical_test:
    decision dates 2024-01-02 .. 2026-05-27
    target end <= 2026-05-29
```

边界按真实交易日解析，不允许简单按自然日 `-2`。train/valid/test 的 target
不能跨越下一 split。

由于该 topic 已反复观察 2017-2026 历史，`historical_test` 的证据身份是：

```text
design_contaminated_historical_real_market_evidence
```

它可以比较论文协议在本地是否可运行、排除明显无效方案并冻结 forward candidate，
但不能被提升为 true OOS support。

### 2.3 Alpha20

EP23 使用论文附录和 RD-Agent `rdagent/utils/qlib.py` 一致的 20 个表达式。23A
必须校验：

- 20 个表达式名称与公式一一对应；
- 每个表达式仅访问 decision close `t` 及更早数据；
- 所有 rolling windows 的左侧 warmup 足够；
- qfq `$volume` 与原始成交量语义差异被记录；
- `$factor` 仅作复权 lineage，不作为 agent 可直接窥视的未来字段；
- 输出 index 唯一为 `(datetime, instrument)`。

### 2.4 Fundamental fields

论文附录列出 Wind 基本面、估值、分析师、资金流和订单字段，但没有公开完整的
as-reported timestamp/revision contract。本地 primary：

```text
allowed = OHLCV + factor + money + turnover_rate
fundamental_or_analyst_field_without_PIT_lineage = forbidden
```

若后续增加基本面，必须单独建立首次公告时间、修订版本、可用时点和 coverage audit。

---

## 3. RD-Agent uv 适配合同

### 3.1 不修改科研语义的 runtime 改动

uv adapter 只允许改变环境启动方式：

```text
conda run -n rdagent4qlib ...
    ->
uv run --project <ep23 runtime project> ...
```

禁止借 runtime 适配改变：

- factor/model prompt；
- Alpha20 公式；
- scheduler；
- dedup threshold；
- split；
- label；
- validation metrics；
- loop acceptance logic。

### 3.2 必须参数化的官方硬编码

官方 checkout 中以下值不能原样用于 EP23：

| 官方默认 | EP23 |
|---|---|
| `~/.qlib/qlib_data/cn_data` | EP23 PIT composite provider |
| `csi300` | `pit_largecap_main_chinext` |
| `SH000300` in same provider | 独立 benchmark bridge 或明确无 benchmark lane |
| 2008/2014/2016/2020 split | 2017/2021/2023/2026 split |
| conda `rdagent4qlib` | uv environment |
| Docker fallback | disabled |

适配应通过 EP23 overlay/launcher 完成，官方 checkout 保持 pinned、clean，便于区分：

```text
upstream code
ep23 runtime-only adapter
agent-generated experiment code
```

### 3.3 凭据边界

`.env` 不进入 Git。最少需要：

```text
CHAT_MODEL
EMBEDDING_MODEL
对应 provider 的 API key/base
```

任何运行清单只记录 model identifier、endpoint host 的脱敏形式、temperature、token
上限和调用统计，不记录 key。

---

## 4. 实验阶段

### 23A：paper/data/runtime preflight

交付：

- source hash 与 RD-Agent commit；
- PIT calendar/instrument/field coverage；
- Alpha20 表达式 smoke；
- label/feature finite ratio；
- uv、Docker、chat、embedding readiness；
- exact-replication gap registry；
- `ready_for_deterministic_baseline` 与 `ready_for_agent_loop` 分开裁决。

23A 不调用 LLM，不训练模型。

### 23B：deterministic Alpha20/LightGBM baseline

目的：先冻结 agent 的共同 comparator。

Primary：

```text
features = Alpha20
model = LightGBM
seeds = [20260723, 20260724, 20260725, 20260726, 20260727]
selection = validation IC then deterministic tie-break
test report = all seeds + median strategy metrics
```

预处理与官方 template 对齐：

- train-only robust z-score + clip；
- feature missing fill 0；
- label 按日横截面 z-score 供 MSE 训练；
- predictive metric 对 raw return 每日计算；
- 不用 test 选择 seed 或 hyperparameter。

先允许一个 seed 的 smoke；正式 23B 必须完成 5 seeds。

### 23C：R&D-Factor

```text
fixed_model = frozen 23B LightGBM
initial_library = Alpha20
budget = 6h primary
smoke_budget = 1 successful loop
```

factor 必须通过：

- 实现可执行；
- 输出 index/column/finite coverage 合法；
- 无未来字段；
- 相对 SOTA correlation `< 0.99`；
- validation 改善；
- test 在 loop 完成与 candidate freeze 前不可访问。

### 23D：R&D-Model

```text
fixed_factors = Alpha20
budget = 6h primary
smoke_budget = 1 successful loop
```

model input/output interface保持官方 contract。模型复杂度、参数量、训练时间和推理延迟
必须记录，防止用无限资源比较。

### 23E：joint R&D-Agent(Q)

```text
actions = [factor, model]
primary_scheduler = contextual_thompson_sampling
budget = 12h
comparators = random, llm_scheduler
```

主比较必须在相同 wall-clock 或相同 valid-loop budget 上分别报告，不能把两种预算混用。

### 23F：固定候选的 PIT 执行与 Big Winner bridge

对 23B-23E 的冻结 score 做：

- paper proxy Top50/drop5；
- next-open executable Top50/drop5；
- project Top30 sensitivity；
- blocked fill、涨跌停、停牌、现金和成本；
- 与 SH000300、全 A 和 universe equal-weight 对比；
- winner episode recall、right-tail exposure days、false-positive exposure days；
- utility gate 与 morphology independence。

23F 不因 ARR 为正自动授权策略。

---

## 5. 比较与裁决

### 5.1 Primary comparisons

```text
C1: R&D-Factor vs Alpha20-LightGBM
C2: R&D-Model vs Alpha20-LightGBM
C3: R&D-Agent(Q) vs best frozen single branch
C4: bandit vs random vs LLM scheduler
C5: PAPER_PROXY vs EXECUTABLE_BRIDGE
```

### 5.2 最低可解释 gate

一个 agent candidate 只有同时满足以下条件，才可标记
`historical_forward_freeze_candidate`：

1. validation primary metric 改善；
2. historical test IC/RankIC 方向一致；
3. 不由单一年或少数股票贡献；
4. 5 seeds 中至少 3 个方向一致；
5. 相对 baseline 的净收益增量不是纯 turnover/cost artifact；
6. executable bridge 不发生符号反转；
7. search accounting 完整；
8. 代码、prompt、config、数据 hash 可重放；
9. factor 不违反 PIT 字段白名单；
10. 对 Big Winner 的增量效用不以不可接受的左尾/暴露日负担换取。

失败时允许的结论：

```text
runtime_blocked
data_contract_blocked
agent_loop_not_reproducible
factor_branch_only_supported
model_branch_only_supported
joint_scheduler_no_increment
paper_proxy_only
historically_falsified
unstable
historical_forward_freeze_candidate
```

---

## 6. 当前 claim ceiling

截至 23F：

```text
paper protocol extracted
PIT adaptation designed
23A ready_for_agent_loop passed
deterministic Alpha20 baseline completed
corrected one-loop R&D-Factor smoke completed
matched-seed factor marginal attribution completed
frozen factor library = Alpha20 + momentum20 + volume_surprise20 + volatility20
one-loop R&D-Model smoke completed; candidate rejected as cost artifact
three-seed controlled model attribution completed
attention pooling rejected; last-state GRU retained for formal five-seed attribution
formal five-seed model attribution completed
last-state GRU next-open executable bridge = positive without sign reversal across 5/5 seeds
primary executable net ARR = 9.10%, below SH000300, all-A and PIT-universe equal weight
Big Winner episode recall = 291/545
right-tail exposure enrichment = 0.872x; Big Winner incremental utility gate failed
morphology coverage and severe-left-tail burden gates passed
23F decision = model_branch_only_supported
joint scheduler remains pending
```

当前只允许声明：

```text
model_branch_supported_in_design_contaminated_PIT_sample
executable_sign_preserved
Big_Winner_incremental_utility_not_supported
```

不能声明 `historical_forward_freeze_candidate`、生产 alpha、自动交易系统或
真实未来有效。23F 的正绝对收益不能覆盖相对 PIT universe 的负增量，也不能覆盖
right-tail exposure enrichment `< 1`。

---

## 7. 运行入口

从 `topics/02_AFML_BIG_WINNER` 执行：

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23a_rdagent_pit_preflight.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

deterministic baseline：

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23b_alpha20_lgbm_baseline.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml \
  --seeds 20260723
```

正式 5-seed 运行省略 `--seeds`，使用 config 的冻结列表。

23F：

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23f_pit_execution_big_winner_bridge.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

Agent loop 入口只有在 23A 的 `ready_for_agent_loop=true` 后才可执行；缺少聊天或
embedding 配置时必须 fail closed，不能静默退化成没有 agent 的普通调参。
