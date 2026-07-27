# EP23 Runbook

所有 Python 命令从 `topics/02_AFML_BIG_WINNER` 运行，并使用当前项目的 uv
environment。不要创建 `rdagent4qlib` conda environment。

## 已可执行

```bash
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23a_rdagent_pit_preflight.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml

uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23b_alpha20_lgbm_baseline.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

验证：

```bash
uv run pytest -q experiments/pending/23_rdagent_quant_pit_replication_v0/tests
uv run ruff check experiments/pending/23_rdagent_quant_pit_replication_v0/src experiments/pending/23_rdagent_quant_pit_replication_v0/tests
```

## RD-Agent loop 当前状态

当前 `/home/xiaolv/code/RD-Agent` checkout：

- `.venv` 已由 uv 建立，Python 为 3.11；
- chat/embedding 已配置为 OpenRouter 上的
  `openai/gpt-5.6-sol` / `openai/text-embedding-3-small`；
- uv runtime adapter、PIT template 和 composite Qlib provider 已就绪；
- 23A 当前给出 `ready_for_agent_loop=true`；
- 23C3 已完成携带 23C2 固定核心库的 corrected Loop 0 baseline 和
  combined-factor Qlib 回测；
- 23D 已完成固定 Alpha20 的单轮 R&D-Model smoke；候选
  `CompactAttentiveGRU128` 未进入 SOTA；
- runner 对新因子与 SOTA 因子的同名冲突采取 `SOTA-first`，避免新公式静默覆盖
  已接受因子。

MLflow 新版本默认拒绝文件型 tracking backend，因此每次运行必须显式设置
`MLFLOW_ALLOW_FILE_STORE=true`。RD-Agent CLI 未指定 `--loop-n` 时会持续循环；
单轮实验必须显式传入 `--loop-n 1`。

模型 feedback adapter 已修复两项问题：移除一次重复 LLM 调用，并把 non-quant
fallback 从 factor system prompt 改回 model system prompt。正式模型复跑前必须
重新执行 23A，以当前 `config.yaml` 中的 adapter diff hash 为准。

## 单轮 factor experiment

```bash
cd /home/xiaolv/code/RD-Agent
MLFLOW_ALLOW_FILE_STORE=true \
QLIB_FACTOR_EVOLVING_N=1 \
PYTHONUNBUFFERED=1 \
.venv/bin/rdagent fin_factor \
  --loop-n 1 \
  --base-features-path \
  /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/23_rdagent_quant_pit_replication_v0/rdagent_base_features_23c2
```

不得把 key 写入 EP23 artifact 或日志。正式 agent run 前重新运行 23A，并检查
`.env` 权限为 `0600`。

`rdagent_base_features_23c2` 目录故意不包含 `base_factors.json`：RD-Agent
继续使用默认 Alpha20 expression library，同时加载该目录中的 momentum 和
volume 两个静态 Python 核心因子。

如果 Agent 提出与静态核心同名但公式不同的因子，runner 会拒绝新因子并保留
SOTA；如果名称不同但横截面平均相关性达到 `0.99`，仍按相关性规则去重。

## Loop-0 受控因子消融

原始 Loop 0 的 baseline/combined preprocessing 不一致，因此先运行配置匹配的
五 seed 归因实验：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23c1_controlled_factor_ablation.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

该步骤不调用 LLM；它固定 LightGBM、split、train-only normalization、Top50/drop5
和费用，仅改变新增因子集合。

## Loop-0 因子交互隔离

23C1 完成后，用 canonical factor order 检查 momentum/volume 核心组合以及
reversal/close-location 的条件贡献：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23c2_factor_interaction_isolation.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

LightGBM 开启 `colsample_bytree` 时，特征列顺序会影响抽样轨迹。23C2 因此强制
所有变体按照 `FACTOR_NAMES` 的 canonical order 排列，并对 23C1 四因子组执行
容差复现审计。

## Corrected Loop-0 新因子边际归因

23C3 的 corrected RD-Agent loop 联合加入 `reversal_5d`、
`volatility_20d`、`intraday_range_1d` 后，运行五 seed single-addition、
pair interaction 和 leave-one-out：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23c4_new_factor_marginal_attribution.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

23C4 的正式裁决：

- 保留 `volatility_20d`；
- `intraday_range_1d` 有单因子证据，但与 volatility 联合后 executable
  增量为负，作为未入库备选；
- 拒绝 `reversal_5d`；
- 当前 frozen factor library 为 Alpha20 + `close_momentum_20d` +
  `volume_surprise_20d` + `volatility_20d`。

复现门包括核心因子逐值一致，以及核心指标相对 23C2 的容差复现。LightGBM
20 线程重复运行存在约 `1e-7` 量级数值抖动，因此指标审计冻结为
`rtol=1e-6, atol=5e-7`；因子值审计仍要求零容差完全一致。

完整运行顺序：

```text
23A ready_for_agent_loop
  -> one-loop R&D-Factor smoke
  -> one-loop R&D-Model smoke
  -> frozen 23C 6h factor run
  -> frozen 23D 6h model run
  -> frozen 23E 12h joint bandit run
  -> matched-budget random/LLM scheduler ablation
  -> 23F executable and Big Winner bridge
```

任何一次 loop 都要记录 RD-Agent commit、EP23 adapter hash、prompt/config hash、
LLM model identifier、token/cost、wall time、成功/失败尝试和被选入 SOTA 的原因。

## 单轮 model experiment

预检查与 CLI dry-run：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23a_rdagent_pit_preflight.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml

cd /home/xiaolv/code/RD-Agent
MLFLOW_ALLOW_FILE_STORE=true \
PYTHONUNBUFFERED=1 \
.venv/bin/rdagent fin_model --loop-n 0
```

单轮 smoke：

```bash
cd /home/xiaolv/code/RD-Agent
MLFLOW_ALLOW_FILE_STORE=true \
QLIB_MODEL_EVOLVING_N=1 \
PYTHONUNBUFFERED=1 \
.venv/bin/rdagent fin_model --loop-n 1
```

23D Loop 0 的正式裁决是 `do_not_promote`。候选毛超额 ARR 相对
Alpha20-LightGBM 恶化 `1.1517 pp`；净超额 ARR 的 `0.4174 pp` 表面改善由
成本拖累减少 `1.5691 pp` 完全解释。下一步只能做固定 seed 的 matched
MLP / last-state GRU / attentive GRU 归因，不能直接把更复杂 attention 模型
作为 SOTA 延续。

## 23D1 受控模型归因

三 seed smoke：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23d1_controlled_model_attribution.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml \
  --mode smoke
```

runner 固定 Alpha20 × 20 timesteps，并以相同 seed 比较容量近似匹配的
flattened MLP、last-state GRU 和 attentive GRU。每个 variant/seed 的权重、
预测、训练曲线与 metadata 会写入 `outputs/local_cache/23d1_*`，重复命令会
恢复缓存并重新生成汇总文件。

23D1 三 seed 裁决：

- 拒绝 attention pooling：相对 last-state GRU，validation IC 中位数下降
  `0.010603`，3/3 seed 均下降；毛 ARR 中位数下降 `11.5047 pp`；
- 保留 last-state GRU 作为正式五 seed 候选：相对 MLP，validation IC、
  historical-test IC/RankIC 和毛 ARR 均为 3/3 seed 改善；
- last-state 相对 MLP 的毛 ARR 中位增量为 `11.0752 pp`，净 ARR 中位增量为
  `10.0856 pp`，turnover 仅增加 `0.003772`，不是成本伪影；
- 当前仍是 `controlled_model_attribution_smoke_only`，不得晋级 SOTA。

当前 GeneralPTNN early-stop 没有 minimum-delta；`1e-5` 量级的 loss 改善也会
重置 patience。正式五 seed 前必须先冻结继续沿用该规则还是引入 minimum-delta，
不能在不同 variant/seed 间混用。

## 23D2 正式五 seed 模型归因

为与 23D1 已完成的前三个 seed 保持严格可比，23D2 沿用无 minimum-delta 的
GeneralPTNN early-stop。attention 已被拒绝，不追加正式预算；只补齐
flattened MLP 与 last-state GRU：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23d1_controlled_model_attribution.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml \
  --mode formal
```

23D2 正式裁决为 `last_state_gru_formal_candidate_pending_23F`：

- 相对容量匹配 MLP，validation IC、test IC、test RankIC 分别为 5/5 seed
  改善；
- 毛 ARR 为 4/5 seed 改善，中位增量 `11.0752 pp`；
- 净 ARR 为 3/5 seed 改善，中位增量 `10.0856 pp`；
- turnover 中位仅增加 `0.005156`，毛收益改善不是较低成本造成；
- EXECUTABLE_BRIDGE IC 为 5/5 seed 改善，毛 ARR 为 3/5 seed 改善；
- 相对 Alpha20-LightGBM，validation IC 5/5、test IC 4/5、毛/净 ARR 4/5
  改善。

该结果完成模型分支正式归因，但 historical test 已设计污染，且尚未经过 23F
完整执行状态机和 Big Winner utility/morphology gate，因此不得直接标记生产
SOTA 或 `historical_forward_freeze_candidate`。

## 23F PIT 执行与 Big Winner bridge

23F 不再训练模型。主 seed 只按 23D2 validation PAPER_PROXY IC 最大选择，
并列时取较小 seed；其余四个正式 seed 仅用于执行方向稳定性审计：

```bash
cd /home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER
uv run python \
  experiments/pending/23_rdagent_quant_pit_replication_v0/src/run_23f_pit_execution_big_winner_bridge.py \
  --config experiments/pending/23_rdagent_quant_pit_replication_v0/config.yaml
```

正式裁决为 `model_branch_only_supported`：

- 主 seed `20260725` 的 PAPER_PROXY Top50/drop5 净 ARR 为 `10.60%`；
- next-open 状态机 Top50/drop5 净 ARR 为 `9.10%`，没有符号反转；
- 五个 seed 的 executable net ARR 均为正；
- 主路径实际观察到停牌/缺 bar、涨停买入阻塞和跌停卖出阻塞；
- 同期 SH000300、全 A 指数和 PIT universe equal-weight ARR 分别为
  `17.97% / 18.81% / 22.21%`，主路径没有形成 universe 增量；
- 捕获 `291 / 545` 个 EP15 path-defined up50 episodes，但实际持仓
  right-tail exposure enrichment 只有 `0.872x`；
- severe-left-tail exposure 低于 eligible universe，morphology coverage
  也不集中于单一路径，但不能抵消 right-tail 增量效用 gate 的失败。

因此 23F 只确认“模型信号经现实成交约束后仍为正”，不支持
Big Winner selector 或 `historical_forward_freeze_candidate`。详细结果位于
`outputs/23F_pit_execution_big_winner_bridge/`。
