# EP23 23D RD-Agent Model Loop 0 Smoke

## 裁决

```text
agent_loop = completed
fixed_input = Alpha20
candidate = CompactAttentiveGRU128
rdagent_recorded_decision = false
local_research_decision = do_not_promote
claim_ceiling = model_loop_smoke_cost_artifact_only
evidence = design_contaminated_historical_real_market_evidence
```

首个 `R&D-Model` 循环已经完整跑通，证明 OpenRouter、uv runtime adapter、
模型生成、PyTorch/Qlib 训练、预测、Top50/drop5 回测和反馈记录链路可用。
但这个候选不能进入 SOTA：它的毛超额收益比 Alpha20-LightGBM 更差，净收益
表面改善完全由较低的成本拖累解释，直接违反研究计划中的非成本伪影 gate。

## 同协议比较

两侧使用相同的 PIT provider、Alpha20、label、train/validation/historical-test
切分、`RobustZScoreNorm + Fillna`、Top50/drop5、沪深 300 benchmark 和交易费用。
比较基线采用 23C 原始循环中配置正确的 Alpha20-LightGBM baseline；该基线侧
没有 23C candidate 的 preprocessing 混杂。

| metric | Alpha20-LightGBM | Attentive GRU | delta |
|---|---:|---:|---:|
| IC | 0.008419 | 0.004131 | -0.004288 |
| ICIR | 0.088050 | 0.019124 | -0.068927 |
| Rank IC | 0.005548 | 0.023586 | +0.018039 |
| Rank ICIR | 0.051577 | 0.098539 | +0.046961 |
| gross excess ARR | -1.4083% | -2.5601% | -1.1517 pp |
| net excess ARR | -6.1473% | -5.7300% | +0.4174 pp |
| net excess IR | -0.837240 | -0.565221 | +0.272019 |
| net excess MDD | -23.1698% | -19.5606% | +3.6093 pp |

Rank IC 有改善，但普通 IC 约减半，ICIR 从 `0.0881` 降至 `0.0191`，毛收益和
净收益仍均为负。单次无固定 seed 的 Rank IC 改善不足以支持模型有效性。

## 成本归因

```text
baseline cost drag = -6.1473% - (-1.4083%) = -4.7390%
candidate cost drag = -5.7300% - (-2.5601%) = -3.1699%

net delta = gross delta + cost-drag delta
          = -1.1517 pp + 1.5691 pp
          = +0.4174 pp
```

候选的净收益增量不是预测 alpha：毛超额 ARR 恶化 `1.1517 pp`，仅因成本拖累
减少 `1.5691 pp` 才得到 `0.4174 pp` 的净改善。因此本轮的正确标签是
`cost_artifact_smoke_only`，不是 `model_branch_only_supported`。

## 模型与训练审计

候选是 20 日 Alpha20 序列上的两层单向 GRU：

- GRU hidden size `128`、层间 dropout `0.15`；
- LayerNorm 后用 `128 -> 64 -> 1` additive attention 对 20 个 timestep 聚合；
- context 经 `128 -> 64` GELU、dropout `0.10` 和标量 head；
- 参数量 `173,569`，FP32 参数字节数 `694,276`；
- train/validation/test 样本分别为 `154,121 / 118,860 / 190,388`；
- epoch 0 即取得最优 validation loss `0.993943`，随后没有稳定改善，epoch 12
  触发 early stop；
- Qlib runner 阶段耗时 `186.244s`，其中 qrun 约 `184.739s`。

batch `256 × 20 × 20` 的独立推理基准：

| device | compute-only median / p95 | candidate forward median / p95 |
|---|---:|---:|
| CPU | 8.374 / 10.541 ms | 9.924 / 11.394 ms |
| CUDA:0 | 0.945 / 1.243 ms | 0.927 / 1.348 ms |

GPU 数值受短基准和异步调度影响，只用于资源量级记录，不用于候选晋级。

## 协议缺口

1. Agent spec 声明 AdamW、gradient norm clip `1.0`，以及 patience `4`、
   minimum LR `1e-5` 的 `ReduceLROnPlateau`。当前 `GeneralPTNN` 实际运行
   Adam + MSE、`clip_grad_value_=3.0`，并使用 patience `5`、minimum LR
   `1e-6`、threshold `1e-5` 的 `ReduceLROnPlateau`。评价必须以实际 runtime
   为准。
2. `seed=None`，仅有一次随机运行，不满足五 seeds 至少三次方向一致的 gate。
3. “attention 优于最后状态”的假设没有 last-state GRU matched ablation，
   因此即使指标更好也无法归因给 attention。
4. 候选 `forward()` 每次都会写 `output.pth`；这是 coder 测试契约泄漏到正式
   训练/推理中的副作用，必须在受控复跑前移除。
5. 本轮结束时模型 feedback 的非 quant fallback 错接到了 factor system
   prompt，原始响应使用了 factor schema。checkpoint 最终记录
   `decision=False`，未误升 SOTA；重复 LLM 调用和 prompt route 已在
   RD-Agent adapter 中修复，下一轮 preflight 将冻结新的 adapter hash。

## Search accounting 与复现信息

- RD-Agent commit：`4f9ecb005881cddc08df0124a2e894c018007679`
- run adapter diff：`ba997af11bd0fab7a47aef4a08d4e680abcdfd4acf025683345014f63e2da4e7`
- post-audit adapter diff：`fb6f2054aec9117673a5fff3bf761e9ece74de37d67224195ed3a2a627d93b15`
- trace：`/home/xiaolv/code/RD-Agent/log/2026-07-27_11-40-14-788344`
- candidate workspace：`be94349cede4457ea2548b2c469a6d19`
- Qlib workspace：`15ab765d9d154e40a93f69a4c04a1b4d`
- experiment / recorder：`320792307570494031` /
  `d421c5fc00fb4c5ab79574ab424aa1f4`
- Loop stages 合计 `246.953s`；6 次 chat 调用共计 prompt `15,410`、
  completion `2,306`、合计 `17,716` tokens。
- LiteLLM 没有该 OpenRouter model 的价格映射，成本为 unavailable，不能写成
  `$0`。
- 正式 trace 与 candidate workspace 的 OpenRouter key 扫描命中均为 `0`。

## 下一步

下一实验应是 `23D1 controlled model attribution`，而不是直接沿用 Agent
提出的更复杂 gated attention：

1. 固定可重放 seed，并用至少 3 seeds 做 smoke、5 seeds 做正式裁决；
2. 固定 Alpha20、20 日窗口和当前全部 Qlib/backtest 配置；
3. matched 比较 tabular MLP、last-state GRU 和 attentive GRU；
4. 完整冻结 runtime 实际使用的 optimizer、loss、scheduler 和 clip 参数；
5. 同时报 gross/net、成本拖累、IC/RankIC、训练时间、参数量和推理延迟；
6. 只有 validation、毛收益和跨 seed 稳定性共同改善时，才允许进入模型分支
   候选池。

本报告的 Qlib 指标是单次运行、相对沪深 300 的超额收益，不能与 23B 的五 seed
绝对组合收益直接比较。historical test 已被用于设计审计，仍属于
`design_contaminated_historical_real_market_evidence`，不构成 true OOS 或
生产 alpha。
