# EP23 23D1 Controlled Model Attribution

## 裁决

```text
run_kind = smoke_3_seed
fixed_input = Alpha20 x 20 timesteps
variants = flattened_mlp, last_state_gru, attentive_gru
decision = reject_attention_retain_last_state_for_formal_attribution
evidence = design_contaminated_historical_real_market_evidence
```

本阶段移除了 23D 候选 `forward()` 写 `output.pth` 的副作用，并以完全相同的
seed、Qlib dataset、processor、Adam/MSE、scheduler、gradient clip、训练预算
和 Top50/drop5 代理比较三个模型。MLP 参数量与 last-state GRU 近似匹配；
attentive GRU 只比 last-state GRU 多 attention pooling。

## 三 seed 中位数

| variant | validation IC | test IC | test RankIC | gross ARR | net ARR | turnover |
|---|---:|---:|---:|---:|---:|---:|
| flattened_mlp | 0.006268 | 0.005260 | 0.012580 | 16.63% | 10.62% | 0.1051 |
| last_state_gru | 0.023038 | 0.015957 | 0.028426 | 35.44% | 28.09% | 0.1089 |
| attentive_gru | 0.012212 | 0.012455 | 0.025172 | 16.82% | 11.41% | 0.0945 |

## Recurrent backbone 的 matched-seed 增量

last-state GRU 相对容量近似匹配的 flattened MLP：

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | +0.016547 | 3/3 |
| historical-test PAPER_PROXY IC | +0.011655 | 3/3 |
| historical-test PAPER_PROXY RankIC | +0.019124 | 3/3 |
| historical-test PAPER_PROXY gross ARR | +11.0752 pp | 3/3 |
| historical-test PAPER_PROXY net ARR | +10.0856 pp | 2/3 |
| mean one-way turnover | +0.003772 | — |

毛收益中位数增加 `11.0752 pp`，而 turnover 只增加
`0.003772`；净收益中位数仍增加
`10.0856 pp`。因此 recurrent backbone 的 smoke 增量
不是较低成本造成的伪影。第三个 seed 的净增量接近零，所以仍需正式五 seed
确认，不在本阶段晋级 SOTA。

相对同 seed 23B Alpha20-LightGBM：

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | +0.014944 | 3/3 |
| historical-test PAPER_PROXY IC | +0.008693 | 3/3 |
| historical-test PAPER_PROXY gross ARR | +12.5535 pp | 2/3 |
| historical-test PAPER_PROXY net ARR | +11.5940 pp | 2/3 |

EXECUTABLE_BRIDGE 上，last-state GRU 相对 MLP 的 IC 中位增量为
`+0.012483`（3/3 为正），
毛 ARR 中位增量为 `+11.2742 pp`
（2/3 为正），没有发生预测方向翻转。

## Attention 的 matched-seed 增量

| metric | median delta | positive seeds |
|---|---:|---:|
| validation PAPER_PROXY IC | -0.010603 | 0/3 |
| historical-test PAPER_PROXY RankIC | -0.008316 | 1/3 |
| historical-test PAPER_PROXY gross ARR | -11.5047 pp | 1/3 |
| historical-test PAPER_PROXY net ARR | -10.2254 pp | 1/3 |

Attention 是否得到支持以 validation IC 与毛收益的 matched-seed 同向改善为主；
净收益不能单独决定晋级，以避免重复 23D 的成本伪影。本轮 attention 的
validation IC 三个 seed 全部下降，test IC 也全部下降；毛/净收益中位数同步
恶化，因此拒绝 attention pooling，而不是拒绝 GRU 时序主干。

## 冻结 runtime contract

- 训练：Adam + MSE，learning rate `0.001`，weight decay `0.0001`；
- batch `256`，最多 100 epochs，early stop `12`；
- `clip_grad_value_=3.0`；
- `ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-6,
  threshold=1e-5)`；
- train/validation processor 与 23D 一致；
- 每个 variant/seed 开始前重置 Python、NumPy、Torch 和 CUDA seed，并启用
  deterministic algorithms。
- 当前 early-stop 没有 minimum-delta，约 `1e-5` 量级的 validation loss
  改善也会重置 patience，导致部分 GRU 运行延长到 26–32 epochs。正式五 seed
  前应冻结 minimum-delta 或保留本轮规则并明确资源代价，不能中途混用。

## 解释边界

- `smoke` 运行使用 seeds `[20260723, 20260724, 20260725]`；只有正式五 seed 结果才可进入模型候选池。
- historical test 已被反复观察，仅用于设计污染样本内的归因诊断。
- portfolio 是本地 equal-weight Top50/drop5 成本代理，完整 executable bridge
  仍留给 23F。
- 本报告是策略绝对收益代理；不能与 23D 单次 Qlib 相对沪深 300 的超额收益
  数值直接比较。
- 单模型逐 seed 训练曲线、参数量、GPU memory、推理延迟和 matched delta 均已
  写入同目录结构化文件。

九个 matched run 的累计模型训练耗时为
`2060.50` 秒；本次汇总 invocation 耗时
`17.02` 秒。断点恢复不会把缓存命中误写成原始训练耗时。
