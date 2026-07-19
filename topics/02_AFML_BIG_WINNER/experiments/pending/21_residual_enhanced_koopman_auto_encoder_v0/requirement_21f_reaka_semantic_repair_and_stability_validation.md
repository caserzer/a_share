# Requirement 21F：REAKA 语义修复与排序稳定性验证

> 文档状态：`draft_pending_human_review`
>
> 生成日期：2026-07-19
>
> Experiment ID：`21_residual_enhanced_koopman_auto_encoder_v0`
>
> Phase ID：`21F_REAKA_SEMANTIC_REPAIR_AND_STABILITY_VALIDATION`
>
> Run ID：`21F_reaka_semantic_repair_and_stability_validation`
>
> Requirement version：`21F_SEMANTIC_REPAIR_v0`
>
> 上游终态：`21E_multiple_implementation_ambiguities_material`
>
> Claim ceiling：`design_contaminated_semantic_repair_candidate_only`
>
> 当前执行授权：`false`

## 0. 一页执行结论

本 requirement 假设论文报告为真，且不再把 21C 的实现选择等同于论文作者代码。目标不是继续任意增加模型容量，而是按证据优先级解决以下问题：

```text
P1  return path / label scale 与论文实现可能不等价；
P2  DDPM point predictor 的概率读出语义未识别且 Monte Carlo 排序未收敛；
P3  reconstruction gradient 可能错误地训练 DRC denoiser；
P4  joint training、two-stage training 与 decoder training role 未识别；
P5  early mean RankIC 选模会选择跨 seed、跨时期不稳定的排序。
```

21D/21E 的直接观察冻结为先验，不作为 21F 新鲜证据：

```text
21C current 8-draw validation_late RankIC             = -0.002304
21D decision-CS-zscore-only delta                     = +0.019889
21D combined repair@64 validation_late RankIC         = +0.037315
21D combined repair@64 - current@8 delta              = +0.039619
21E Koopman-only - current P0                         = +0.013519
21E stopgrad - coupled C10                            = +0.007245, 3/3 seeds同向
21E 100-step / ResBlock                               = not_material
21E pointwise-MLP decoder C22                         = material but negative
```

21F 的机械流程为：

```text
Step A  exact replay 21D D4@64 与 21E关键 contrasts；
Step B  只使用2018–2022 retained train，建立2021/2022两个 expanding inner folds；
Step C  训练5个受控 training-semantics arms，所有 epoch 统一由 score_mean256_ref 选择；
Step D  在已冻结 inner checkpoints 上识别 Predictor estimator，先过收敛 gate，再按最差 inner fold 排序；
Step E  用选中的 estimator 选择 training arm，并按内部 epoch 规则在2018–2022 refit 3 seeds；
Step F  所有选择与 checkpoint hash 完成后，fresh worker 首次读取2023 early/late；
Step G  只有 DRC 对 Koopman-only 有稳定增量且 morphology 全通过，才生成 design-contaminated repair candidate。
```

### 0.1 本阶段不回答的问题

以下全部 out of scope：

```text
historical design holdout
论文精确复现声明
作者实现声明
forward support
组合收益 / AR / Sharpe / 换手 / 回撤
每日或非每日再平衡选择
交易成本、停牌、涨跌停、next-open execution
```

再平衡频率不会参与任何 RankIC、arm 或 estimator 选择。若未来做投资模拟，必须另立 requirement，并人工冻结 `rebalance_every_n_sessions`、成交时点和持有期。

Alpha158 特征集合、本地 A 股市场、PIT proxy universe、样本区间和 next-return 标签期在 21F 中同样保持冻结。21F 即使通过，也只能说明本地语义修复候选成立；剩余论文差距仍可能来自这些外部边界，不得由本阶段结果反推为已排除。

### 0.2 证据污染边界

21C–21E 已读取 2023 并据此形成 21F，因此：

```text
2018–2022 inner folds = model-selection evidence, 但 arm family 已受既往研究启发
2023 early/late       = design-contaminated final mechanism readout
historical holdout    = forbidden, open_attempt_n 必须为 0
```

2023 不得用于：

```text
epoch selection
Predictor estimator selection
training arm selection
seed selection
threshold调整
增加或删除arm
```

### 0.3 当前授权边界

当前只授权创建和评审本 requirement。禁止创建 config、runner、test、authorization、训练 checkpoint 或 output bundle。用户后续明确要求 `impl it` 才能实现；实现完成后仍需单独人工 authorization 才能正式执行。

---

## 1. 冻结输入与 immutable pins

所有相对路径以：

```text
experiment_root = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0
```

为唯一解析基准。禁止 `latest`、symlink、glob 选最新版或依赖 shell cwd。

### 1.1 论文原文

```text
path   = paper/Residual-Enhanced_Adaptive_Koopman_Autoencoder_A_Deep_Latent_Dynamics_Model_for_Stock_Prediction.pdf
sha256 = 1041d8693c5ef80fcafc613d77f09bf3ec2a2df673f468785255da27d7d9a472
source = IEEE ICASSP 2026 version of record
```

runner 必须逐项登记 Section 3.3–3.6、Equations (16)–(31) 中 paper-defined 与 undisclosed 字段。companion report 不得替代 PDF。

### 1.2 21B v5 model-input pins

```text
manifest:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v5/manifest_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = d5ca5c5997c4cce5019e73c0dd0e0fa06c4747a43d323f483c4de29131478d85

output_hashes:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v5/output_hashes_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = e20f2ac9e5e49f51494373feaacb93c4e0ea609bb3b563e44fd98a4523db7552

sequence_index:
  path = outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/sequence_sample_index.parquet

panel_manifest:
  path = outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/model_input_panel_manifest.json
```

21F 必须复用 21C v4 的 exact PIT exclusion registry：

```text
path   = references/21c_full_v3/pit_universe_exclusion_registry.csv
sha256 = 3c3d903821ee56a49f1ea0d83327606b58f87826ae317d6f95e5a5d4236aef11
scope  = all_folds_entire_instrument_history
instrument_n = 396
```

不得修改 universe、填补缺失 teacher key 或恢复被排除 instrument。

### 1.3 21C exact-replay pins

```text
manifest:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4/manifest_21c_full_reaka_pit_proxy_replication.json
  sha256 = b4537b99086c1c89c0f10d494a99aa8fb89434ea12b3557710cba29cfdda1529

output_hashes:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4/output_hashes_21c_full_reaka_pit_proxy_replication.json
  sha256 = bb56098ce915e64870a0f1b231c77c1190d4557ddd20c380b66ae23567cb2cc9
```

21F 不重写 21C checkpoint 语义；P0 exact replay 必须复用其 3 个 sealed checkpoint 和 draw identity。

### 1.4 21D causal-diagnostic pins

```text
manifest:
  path   = outputs/21D_reaka_replication_gap_causal_diagnostic_v2/manifest_21d_reaka_replication_gap_causal_diagnostic.json
  sha256 = 8fb9398aebd8586eaccb85fb9c9e72de571bf063b2ad94d12b6e7fcb1b8781e6

output_hashes:
  path   = outputs/21D_reaka_replication_gap_causal_diagnostic_v2/output_hashes_21d_reaka_replication_gap_causal_diagnostic.json
  sha256 = 4edd2b6689ed1274f605eba220219ee7ee5ffd231c8c3305838f0ddb1edbc9d4

decision:
  path   = outputs/21D_reaka_replication_gap_causal_diagnostic_v2/21D_reaka_replication_gap_causal_diagnostic_decision.csv
  sha256 = 410c4742afacce6a688781e4c616ccad61847df72fca683d440fd1ce375b6347
```

21D D4 只用于 exact replay 与 prior registry，不作为 21F inner-fold checkpoint。

### 1.5 21E implementation-identification pins

```text
manifest:
  path   = outputs/21E_reaka_predictor_drc_implementation_identification_v0/manifest_21e_reaka_predictor_drc_implementation_identification.json
  sha256 = 848c9941ac0f247f84b83182bf95b4b71a3dedbe3064530f4e6a21fc9c04d63e

output_hashes:
  path   = outputs/21E_reaka_predictor_drc_implementation_identification_v0/output_hashes_21e_reaka_predictor_drc_implementation_identification.json
  sha256 = 155e086c131807c1bdae77f287969c3e1ba45db89573082d5493f4752851a1e6

decision:
  path   = outputs/21E_reaka_predictor_drc_implementation_identification_v0/21E_reaka_predictor_drc_implementation_identification_decision.csv
  sha256 = 84008392494df09091eddc414037cac7566d16e76a89227035e7f995c34e0b5f

paired_contrasts:
  path   = outputs/21E_reaka_predictor_drc_implementation_identification_v0/paired_implementation_contrasts.csv
  sha256 = eecf8cb2ca3ebe52317b8608316884866e856571117961989d4be9ab9b647ced

gradient_audit:
  path   = outputs/21E_reaka_predictor_drc_implementation_identification_v0/loss_gradient_and_collapse_audit.parquet
  sha256 = ddffd84c4d1d1d6a2b1067c4b75012b30e466bdccbf11480b494d27c4bff69d2
```

21F preflight 必须验证 21D/21E terminal state、artifact profile、manifest closure、registered hashes 和 forbidden historical-holdout access。

---

## 2. 冻结 folds 与时间防火墙

### 2.1 Retained train 内部 expanding folds

以下 row set 从 21B `fold=train` 中删除 exact 396 instruments，再按 `decision_date,instrument` mergesort。row hash 定义为 canonical JSON string array 的 SHA256。

| split_id | role | date_min | date_max | row_n | complete_day_n | instrument_n | row_key_sha256 |
|---|---|---|---|---:|---:|---:|---|
| `I0_FIT_2018_2020` | inner fold 0 fit | 2018-01-02 | 2020-12-31 | 174142 | 476 | 668 | `b6d808e80d0b87e5f44b4e046983448d8f0aff81d4ce0d3d2af6a69288525e3b` |
| `I0_SELECT_2021` | inner fold 0 selection | 2021-01-04 | 2021-12-31 | 79007 | 186 | 586 | `ffd8ecf9977be0d0b56b6b2972a1890f9c5350fb70dd28f11a5db765d6195ef2` |
| `I1_FIT_2018_2021` | inner fold 1 fit | 2018-01-02 | 2021-12-31 | 253149 | 662 | 762 | `eac96c35bcc99fe516a0647f225ccaae4fd0197f77201331d8597398e79ff85f` |
| `I1_SELECT_2022` | inner fold 1 selection | 2022-01-04 | 2022-12-14 | 82244 | 180 | 607 | `be1cfdbc9234268450ee528e22d1654469ad4d6282917331fbdf609b1ff654a8` |
| `REFIT_2018_2022` | selected arm refit | 2018-01-02 | 2022-12-14 | 335393 | 842 | 860 | `d1d22a89e6b8096645f1f91b7941f22cd30670aabfbb37d3e388ca324daf6e4e` |

`I0_SELECT_2021` 与 `I1_SELECT_2022` 只允许 epoch、estimator 和 arm selection；不得 optimizer update。

### 2.2 2023 design readout folds

```text
DESIGN_EARLY_2023:
  date_min = 2023-01-04
  date_max = 2023-06-30
  row_n = 51932
  complete_day_n = 107
  instrument_n = 625
  row_key_sha256 = 633f2bf154e826a5228c8e73c3bc361812c52fd63d3379ccd01966c80dbb8ba8

DESIGN_LATE_2023:
  date_min = 2023-07-03
  date_max = 2023-12-13
  row_n = 50167
  complete_day_n = 103
  instrument_n = 592
  row_key_sha256 = 1f46023e27b72e67afd10e01eb10daff7192c39f4be0d72846cc0ff4906e5adc
```

在 `pre_2023_complete.json` 写入之前，任何 training/selection process 对上述路径的 open attempt 都必须为 0。2023 worker 必须是 fresh process，且：

```text
optimizer_object_n = 0
autograd_enabled = false
train_loader_object_n = 0
checkpoint_write_n = 0
```

---

## 3. 预注册因果假设

| order | hypothesis_id | 可证伪陈述 | 主要 intervention | falsifier |
|---:|---|---|---|---|
| 1 | `H21F01_RETURN_SCALE_NECESSARY` | decision-CS z-score 在相同 graph/weights 下改善最差 inner-fold RankIC 且不恶化 morphology | T1−T0 | 两个 inner folds 任一负向，或 morphology 变差 |
| 2 | `H21F02_GRADIENT_GRAPH_MATERIAL` | stopgrad reconstruction 比 coupled 有稳定增量 | T2−T1 | 两个 inner folds不同向或增量小于阈值 |
| 3 | `H21F03_TWO_STAGE_REPAIR` | modular two-stage 比 joint stopgrad 更稳定 | T3−T2 | worst-fold RankIC、seed rho 或 collapse 任一更差 |
| 4 | `H21F04_DECODER_ROLE_MATERIAL` | decoder topology/training role materially改变排序 | T4−T2 | delta、score morphology 和跨 seed均未过 conjunction |
| 5 | `H21F05_PREDICTOR_ESTIMATOR_UNSTABLE` | 当前8/64 draw score mean 不是稳定 point estimator | Q0–Q7 convergence | 64/128/256 prefix排序收敛且 estimator间排序一致 |
| 6 | `H21F06_DRC_INCREMENTAL_VALUE` | repaired DRC 相对同 backbone Koopman-only 有稳定正增量 | selected DRC−K0 | 2023 late delta <0.005、少于2/3 seeds同向或 morphology失败 |
| 7 | `H21F07_SELECTION_POLICY_DIFFERENCE` | worst-fold + morphology selection 会排除 mean-only 偏好的不稳定 arm | selected vs mean-only shadow selection | 两种规则选择相同 arm，或 shadow arm 同样通过全部 morphology gates |
| 8 | `H21F08_AUTHOR_CODE_REMAINS_UNKNOWN` | 无官方代码时仍不能识别作者实现 | 全证据 | 只有外部官方 source 才可解除 |

所有 hypothesis registry rows 必须在任何新训练或新 score 前生成并 hash-register。allowed conclusion exact 为 `design_contaminated_semantic_repair_diagnostic_only`。

---

## 4. Return path 与 loss geometry 合同

### 4.1 Raw path

`raw_return_path` exact 复用 21C：不得额外 winsorize、rank、normalize 或按日重加权。

### 4.2 Decision-CS z-score path

exact 复用 21D `decision_cs_zscore_return_path`：

```text
对每个decision_date和每个sequence position：
  mu_d   = retained decision cross-section float64 mean
  sigma_d = retained decision cross-section float64 population std, ddof=0
  z = (r - mu_d) / max(sigma_d, 1e-6)
```

source path、teacher shifted path、reconstruction target 和 diffusion residual target 必须使用同一 transform identity；evaluation label 保持 raw next return，仅在 RankIC 时横截面排名。不得只 normalize label 或只 normalize source。

每个 date/position 的 `mu,sigma,row_n,row_key_sha256` 必须输出审计。任何 `sigma < 1e-6` 必须登记，不得静默改公式。

### 4.3 Train-calibrated loss weights

exact 复用 21D train-only gradient calibration：

```text
losses = L_rec, L_koop, L_diff
calibration rows仅来自对应inner fit split
每个 temporal stratum 固定32 batches，每batch 256 rows
先计算各loss对exact ordered parameter set的global gradient L2 median
inverse-gradient weights按21D公式clip并renormalize到sum=3
```

selection/2023 不得参与 calibration。weights 在 optimizer 第一步前写入并 hash-freeze。

---

## 5. Training-semantics arms

共同冻结：

```text
lookback=10
feature_dim=157
latent_dim=64
operator_n=4
denoiser=21C concat MLP
diffusion_steps=20
beta_schedule=linear 1e-4..2e-2
selector_train=straight_through_hard
batch_size=256
model_seeds=[20260713,20260714,20260715]
gradient_clip_global_l2=1.0
primary epoch-selection predictor=score_mean256_ref
```

不得在 21F 重测 100 diffusion steps 或 ResBlock；21E 已把两者降为低优先级。

| arm_order | arm_id | return path | loss weights | reconstruction→denoiser | training phases | decoder | role |
|---:|---|---|---|---|---|---|---|
| 0 | `T0_RAW_COUPLED_LINEAR` | raw | train-calibrated | coupled | joint | shared linear | scale control |
| 1 | `T1_CSZ_COUPLED_LINEAR` | decision-CS z-score | train-calibrated | coupled | joint | shared linear | return-scale intervention |
| 2 | `T2_CSZ_STOPGRAD_LINEAR` | decision-CS z-score | train-calibrated | detached for `L_rec` only | joint | shared linear | primary graph repair |
| 3 | `T3_CSZ_TWO_STAGE_LINEAR` | decision-CS z-score | phase-specific | no reconstruction path in phase 2 | two-stage | shared linear, frozen phase 2 | modularity repair |
| 4 | `T4_CSZ_STOPGRAD_POINTWISE_MLP` | decision-CS z-score | train-calibrated | detached for `L_rec` only | joint | 21E exact pointwise MLP | decoder sensitivity control |

### 5.1 Stop-gradient exact semantics

T2/T4 只允许：

```text
L_rec decoder input = stop_gradient(x0_hat)
L_diff path         = unchanged and fully differentiable
L_koop path         = unchanged
```

不得 detach `Z_source`、Koopman forecast、epsilon prediction 或 forecast score。fixture 必须证明 T1/T2 initial state、draw tensors 和非目标 gradients exact 一致。

### 5.2 Two-stage exact semantics

T3：

```text
Phase A:
  train encoder + selector + Koopman + shared-linear decoder
  active losses = L_rec + L_koop
  denoiser optimizer_object_n = 0

Phase B:
  freeze encoder + selector + Koopman + decoder
  train denoiser only
  active loss = L_diff
  checkpoint writes include phase-A and phase-B semantic hashes
```

Phase A/Phase B 各自 epoch 不得由 2023 决定。Phase B predictor 始终使用 frozen Phase-A decoder。

### 5.3 Training job cardinality

```text
inner jobs = 5 arms × 3 seeds × 2 expanding folds = 30
refit jobs = 1 selected arm × 3 seeds             = 3
total planned jobs                                 = 33
```

所有 inner checkpoints 必须完成后才能选择 estimator/arm。禁止以 wall time、单 seed 结果或部分 checkpoint 提前淘汰 arm。

---

## 6. Predictor estimator arms

所有 stochastic variants 使用 common random numbers：

```text
noise_key = sha256(run_id,row_key_hash,model_seed,draw_idx,diffusion_step,tensor_role)
draw prefix identity: prefix8 ⊂ prefix32 ⊂ prefix64 ⊂ prefix128 ⊂ ref256
dtype and reduction order固定
```

| order | estimator_id | 定义 | candidate eligible | claim restriction |
|---:|---|---|---|---|
| 0 | `Q0_CURRENT_SCORE_MEAN8` | 前8 draws逐draw decode last score后mean | false | exact replay control |
| 1 | `Q1_SCORE_MEAN64` | 前64 draws逐draw decode last score后mean | true | local point estimator |
| 2 | `Q2_SCORE_MEAN256_REF` | 256 draws逐draw decode last score后mean | true | compute-heavy reference |
| 3 | `Q3_ANTITHETIC_SCORE_MEAN64` | 32对完整reverse-noise tensors `u,-u`，逐draw decode后mean | true | variance-reduction candidate |
| 4 | `Q4_DDIM_ETA0_SCORE` | same beta schedule, DDIM eta=0 deterministic path | true | deterministic candidate, not paper-defined |
| 5 | `Q5_ZERO_NOISE_REVERSE_PROXY` | 21E exact zero-noise proxy | false | 不得称 conditional mean |
| 6 | `Q6_KOOPMAN_ONLY` | 不调用 denoiser，decode Koopman forecast | false | residual-attribution control |
| 7 | `Q7_LATENT_MEAN256_THEN_DECODE` | 先对256 corrected latents取mean，再decode last score | false | shared-linear时必须与Q2通过commutation fixture；非线性decoder上只作敏感性诊断 |

### 6.1 Predictor convergence gates

对每个 inner checkpoint、selection fold、seed：

```text
median_daily_spearman(prefix64,ref256) >= 0.95
median_daily_top30_overlap(prefix64,ref256) >= 24
abs(mean_daily_rankic(prefix64)-mean_daily_rankic(ref256)) <= 0.003
```

Q3 使用 antithetic32-pair 对 antithetic128-pair reference；Q4 deterministic 自动满足 draw convergence，但仍需跨 seed morphology。Q7 在线性 decoder 下只做 algebraic/bitwise fixture，不重复计入 estimator family 的多重比较。

### 6.2 Predictor selection

Predictor selection reference exact 为 `T1_CSZ_COUPLED_LINEAR` 的 6 个 inner checkpoints；不得跨 training arms 聚合后选择 estimator，以免 estimator 与 training graph 循环适配。先删除 convergence fail、non-finite、coverage fail 或 `candidate eligible=false` estimator。剩余 estimator 按以下 lexicographic 规则选择：

```text
1. 最大化 min(I0_SELECT_2021 ensemble RankIC, I1_SELECT_2022 ensemble RankIC)
2. 最大化两fold中较小的 mean cross-seed daily Spearman
3. 最大化两fold中较小的 mean cross-seed Top30 overlap
4. 最小化 inference draw-equivalent compute
5. estimator_order 最小
```

不得使用 2023、论文表中 `0.064` 或 21D D4 的 2023 数值 tie-break。

若没有 estimator eligible，registry 必须记录 `research_estimator_selected=false`，并以 `Q2_SCORE_MEAN256_REF` 作为固定 `diagnostic_fallback_estimator` 继续 arm readout/refit；fallback 不得生成 repair candidate。

---

## 7. Epoch、arm 与 refit 选择

### 7.1 Inner epoch selection

每个 arm/fold/seed 独立训练。epoch selection 固定使用 Q2 `score_mean256_ref`，不是最终选中的 estimator：

```text
primary = selection-fold mean daily RankIC
eligibility = finite coverage + no collapse + no firewall violation
tie break = first maximum epoch
```

不得跨 seed 选 best seed。所有三个 seeds 均保留并参与后续 ensemble/morphology。

### 7.2 Arm eligibility

使用已选择 Predictor estimator 重读 30 个 inner checkpoints。每个 arm 必须在两个 selection folds 同时满足：

```text
ensemble mean daily RankIC > 0
positive seed_n >= 2 of 3
mean pairwise cross-seed daily score Spearman >= 0.25
mean pairwise cross-seed Top30 overlap >= 6
ensemble adjacent-day Top30 turnover <= 0.80
quarter-LOMO positive_n >= 3 of 4
additional_collapse_flag_n = 0
```

### 7.3 Arm selection

eligible arms 按：

```text
1. 最大化两个inner folds的worst-fold ensemble RankIC
2. 最大化worst-fold cross-seed Spearman
3. 最大化worst-fold Top30 overlap
4. 最小化worst-fold turnover
5. arm_order最小
```

同时生成 `mean_rankic_only_shadow_selection.json`，用于检验 H21F07；shadow selection 不得控制任何训练或 2023 readout。

若没有 arm eligible，registry 必须记录 `research_arm_selected=false`，并以 `T2_CSZ_STOPGRAD_LINEAR` 作为固定 `diagnostic_fallback_arm` 完成3个 refit jobs与2023机制 readout；fallback 不得生成 repair candidate。这样所有终态仍保持 exact 33 jobs和统一 artifact profile。

### 7.4 Refit epoch

selected arm 的 6 个 inner selected epochs 排序，`refit_epoch_n = lower_median`，即第 3 个 order statistic。3 个 refit seeds 使用同一固定 epoch，不做 early stopping，不读取 2023。

refit 在 `REFIT_2018_2022` 上从 deterministic initial state 重新训练，不得继续 inner checkpoint optimizer state。

---

## 8. 2023 final mechanism readout

只有以下对象全部 hash-register 后才允许 fresh worker 打开 2023：

```text
hypothesis_registry
arm_registry
estimator_registry
30 inner checkpoint manifest
selected_estimator.json
selected_training_arm.json
mean_rankic_only_shadow_selection.json
3 refit checkpoint manifest
refit_epoch_contract.json
pre_2023_complete.json
```

fresh worker 对 selected arm 输出：

```text
selected DRC estimator scores: 3 seeds + ensemble
same backbone Koopman-only:     3 seeds + ensemble
Q0 current8 replay control
Q2 ref256 convergence reference
```

分别报告 `DESIGN_EARLY_2023`、`DESIGN_LATE_2023`，禁止把两者合并后作为唯一结论。

### 8.1 DRC incremental-value gate

selected DRC 相对 same-backbone Koopman-only 在 DESIGN_LATE_2023 必须同时满足：

```text
mean_daily_rankic_delta >= 0.005
same_direction_seed_n >= 2 of 3
paired_day_n >= 100
morphology_nonworse = true
Holm-adjusted p <= 0.10
```

若不满足，最多结论为“return/predictor repair improved ranking but DRC incremental value unresolved”。不得把 Koopman-only 的增益归因给 DRC。

### 8.2 Full stability candidate gate

生成 repair candidate 必须在 DESIGN_LATE_2023 同时满足：

```text
research_estimator_selected = true
research_arm_selected = true
ensemble mean daily RankIC >= 0.030
selected - Q0_CURRENT_SCORE_MEAN8 delta >= 0.020
positive seed_n >= 2 of 3
mean pairwise cross-seed daily score Spearman >= 0.25
mean pairwise cross-seed Top30 overlap >= 6
ensemble adjacent-day Top30 turnover <= 0.80
six-month LOMO positive_n >= 5 of 6
selected estimator convergence gates all pass
DRC incremental-value gate pass
additional_collapse_flag_n = 0
historical holdout open_attempt_n = 0
```

`0.030` 是本地预注册 research-candidate floor，不是论文复现阈值，也不得解释为接近论文的百分比。

---

## 9. 指标与统计合同

### 9.1 Daily RankIC

对每个完整 decision date：

```text
RankIC_d = Spearman(score_i, raw_next_return_i)
minimum cross-section n = 100
ties = scipy rankdata(method='average') exact equivalent
```

报告 arithmetic mean、sample std、RankICIR、positive-day rate、paired-day delta。不得在 metric 前对 label 做 CS z-score 后改变 row order；CS z-score 只影响 model return path。

### 9.2 Morphology

必须报告：

```text
daily score std
cross-seed daily Spearman
cross-seed Top30 overlap
adjacent-day Top30 turnover
prefix convergence Spearman/Top30 overlap
monthly and quarter LOMO
zero-solution improvement
latent std / decoder output std / label std ratio
```

### 9.3 Multiple comparisons

预注册 primary contrast family：

```text
C01 = T1 - T0       return scale
C02 = T2 - T1       stopgrad
C03 = T3 - T2       two-stage
C04 = T4 - T2       decoder topology
C10 = selected DRC - same-backbone Koopman-only
C11 = selected - Q0 current8
```

每个 family/fold 使用 paired daily stationary bootstrap，block length=10 sessions，replicate_n=5000，seed 固定。Holm correction 在 exact family 内执行，不跨 fold 合并。

`mean_rankic_only_shadow_selection` 只进入 `selection_policy_difference_audit.csv`，比较 selected identity、inner-fold RankIC 与 morphology gate vector；它不是同一 checkpoint 上的 paired score contrast，不得伪造 C12 或 p-value。

---

## 10. 机械终态与决策顺序

全部 technical gates 通过后，按 first-match 生成唯一终态：

```text
1. no Predictor estimator passes convergence/eligibility
   -> 21F_predictor_semantics_unresolved

2. Predictor selected but no training arm passes inner stability
   -> 21F_no_stable_training_repair

3. final selected rank improves but DRC incremental-value gate fails
   -> 21F_repaired_rank_without_drc_increment

4. DRC incremental value passes but full stability candidate gate fails
   -> 21F_mean_rank_repair_unstable

5. all candidate gates pass
   -> 21F_design_contaminated_semantic_repair_candidate
```

所有终态：

```text
evidence_role = design_contaminated_semantic_repair_diagnostic
paper_exact_claim_allowed = false
author_implementation_claim_allowed = false
forward_support_claim_allowed = false
next_requirement_execution_authorized = false
```

即使第 5 项通过，也只能由人工另立 fresh-session forward requirement；21F runner 不得自动创建或执行下一阶段。

---

## 11. 执行阶段与 gates

### E0 PREAUTH_AND_PREFLIGHT

1. `execution_authorization_gate`
2. `paper_and_upstream_hash_gate`
3. `upstream_terminal_state_gate`
4. `artifact_profile_contract_gate`
5. `retained_universe_exact_match_gate`
6. `inner_fold_exact_hash_gate`
7. `hypothesis_registry_gate`
8. `historical_holdout_zero_access_gate`

### E1 EXACT_REPLAY_AND_FIXTURES

9. `21c_q0_exact_replay_gate`
10. `21d_d4_prefix64_exact_replay_gate`
11. `21e_contrast_and_gradient_replay_gate`
12. `return_transform_fixture_gate`
13. `common_random_number_prefix_gate`
14. `gradient_graph_fixture_gate`

### E2 INNER_TRAINING

15. `training_arm_exact_gate`
16. `planned_30_inner_jobs_gate`
17. `train_only_gradient_calibration_gate`
18. `inner_epoch_selection_gate`
19. `checkpoint_semantic_hash_gate`
20. `training_collapse_audit_gate`

### E3 ESTIMATOR_ARM_SELECTION_AND_REFIT

21. `predictor_convergence_gate`
22. `predictor_selection_first_match_gate`
23. `arm_stability_eligibility_gate`
24. `arm_selection_first_match_gate`
25. `shadow_selection_noncontrolling_gate`
26. `planned_3_refit_jobs_gate`
27. `pre_2023_complete_gate`

### E4 FRESH_2023_READOUT

28. `fresh_2023_worker_gate`
29. `prediction_coverage_gate`
30. `daily_rankic_metric_gate`
31. `paired_contrast_gate`
32. `drc_incremental_value_gate`
33. `full_stability_candidate_gate`
34. `portfolio_output_absence_gate`
35. `historical_holdout_zero_access_finalize_gate`

### E5 FINALIZE_AND_SEAL

36. `terminal_state_first_match_gate`
37. `report_decision_consistency_gate`
38. `closed_schema_gate`
39. `artifact_profile_gate`
40. `manifest_hash_closure_gate`
41. `post_run_validation_gate`
42. `finalize_transaction_gate`

任一 technical execution/validation gate fail：non-zero exit，保留 `.building`，不得生成 canonical。第32、33项必须区分 `evaluation_status` 与 `research_status`：公式、coverage和证据完整时 `evaluation_status=pass`，而阈值未满足写 `research_status=fail`。Research candidate fail 不是技术失败；仍可密封完整诊断，但终态必须按第 10 节降级。

---

## 12. 生命周期、授权与资源上限

### 12.1 Seal only after complete run

```text
working
  -> preflight_complete
  -> replay_complete
  -> inner_training_complete
  -> estimator_and_arm_selection_complete
  -> refit_complete
  -> pre_2023_complete
  -> fresh_2023_readout_complete
  -> post_run_validation_complete
  -> sealed
```

canonical root：

```text
outputs/21F_reaka_semantic_repair_and_stability_validation_v0
```

working root：

```text
outputs/21F_reaka_semantic_repair_and_stability_validation_v0.building
```

只有 `os.replace(building,canonical)` 可以创建 canonical，且源代码中 exact 出现一次。

### 12.2 Human authorization binding

正式执行前 authorization exact keys 至少包含：

```text
schema_version
run_id
requirement_version
approved_requirement_sha256
approved_config_sha256
approved_runner_sha256
approved_test_sha256
approved_paper_pdf_sha256
approved_upstream_21b_manifest_sha256
approved_upstream_21b_output_hashes_sha256
approved_upstream_21c_manifest_sha256
approved_upstream_21c_output_hashes_sha256
approved_upstream_21d_manifest_sha256
approved_upstream_21d_output_hashes_sha256
approved_upstream_21e_manifest_sha256
approved_upstream_21e_output_hashes_sha256
approved_dependency_lock_sha256
approved_device_fingerprint_sha256
approved_artifact_profile_id
approved_artifact_profile_registry_contract_sha256
allowed_runtime_field_differences
approved_by
approved_at_utc
```

runner 不得生成或补写 authorization。`approved_by` 必须是 human identity；`allowed_runtime_field_differences=[]`。

### 12.3 Resource contract

```text
GPU required = CUDA
maximum concurrent GPU training jobs = 1
batch_size = 256
model_seeds = 3
planned_training_jobs = 33
minimum free disk before run = 25 GiB
total GPU wall-time cap = 48 hours
per-job hard timeout = 3 hours
```

OOM 只允许按预注册顺序降低 inference batch size，不得改变 training batch size、draw count、dtype、模型或样本。

---

## 13. 输出 artifact profile

Artifact profile ID：

```text
P1_FULL_SEMANTIC_REPAIR_DIAGNOSTIC
```

最低 required artifacts：

```text
21F_reaka_semantic_repair_and_stability_validation_decision.csv
21F_reaka_semantic_repair_and_stability_validation_report.md
hypothesis_registry.csv
training_semantics_arm_registry.csv
predictor_estimator_registry.csv
contrast_registry.csv
inner_fold_registry.csv
return_transform_audit.parquet
gradient_calibration_audit.parquet
gradient_graph_and_collapse_audit.parquet
training/inner_training_run_registry.csv
training/inner_checkpoint_manifest.json
training/selected_predictor_estimator.json
training/selected_training_arm.json
training/mean_rankic_only_shadow_selection.json
training/refit_epoch_contract.json
training/refit_training_run_registry.csv
training/refit_checkpoint_manifest.json
predictions/inner_selection_prediction_scores.parquet
predictions/design_2023_prediction_scores.parquet
predictor_draw_convergence.csv
daily_rankic_readout.csv
paired_semantic_contrasts.csv
cross_seed_morphology.csv
top30_overlap_and_turnover.csv
monthly_quarter_lomo_stability.csv
selection_policy_difference_audit.csv
hypothesis_readout.csv
gate_evidence_21f.csv
historical_design_holdout_access_audit.csv
artifact_profile_registry.csv
stage_status_registry.csv
semantic_reproducibility_manifest.json
manifest_21f_reaka_semantic_repair_and_stability_validation.json
output_hashes_21f_reaka_semantic_repair_and_stability_validation.json
```

Checkpoint paths 必须在 config 中展开为 exact 33 paths；manifest 不接受 glob。draw-level shards 可以作为 conditional local-only artifacts，但必须进入 artifact profile 和 hash closure。

禁止 artifact path/token：

```text
portfolio
sharpe
annualized_return
turnover_cost
execution_ledger
historical_holdout_predictions
best_seed
post_2023_added_arm
paper_exact_replication
```

Top30 overlap/turnover 是 score morphology diagnostic，不是 portfolio backtest，因此允许输出；不得包含收益或成本列。

### 13.1 大文件 Git 规则

canonical bundle 本地必须完整。单文件 `size_bytes > 20 MiB` 时，Git 发布必须用 exact path 加入 `.gitignore`，其余文件正常发布；不得删除、截断或使用 placeholder。报告必须列出所有 local-only artifact exact paths 和 sizes。

---

## 14. Closed schema 与数值完整性

所有 CSV/Parquet 必须 closed schema：exact columns、dtype、nullable contract、主键和 row count 由 config/test 冻结。至少满足：

```text
decision_date ISO date
instrument canonical provider symbol
arm_id / estimator_id / seed / fold 非空
score / label / RankIC / gradient finite where status=pass
no duplicate primary key
no NaN/Inf silently converted to zero
all prediction rows exact match retained row keys
```

Prediction primary key：

```text
stage_id,fold_id,arm_id,estimator_id,score_variant,model_seed,is_ensemble,decision_date,instrument,row_key_hash
```

Training registry primary key：

```text
fold_id,arm_id,model_seed
```

Refit registry primary key：

```text
arm_id,model_seed
```

---

## 15. 中文报告必须回答的问题

1. 哪些字段论文明确、哪些仍未披露？
2. 21D/21E 先验与 21F direct evidence 如何分栏？
3. CS z-score 在两个 inner folds 是否一致改善？
4. 64/128/256、antithetic、DDIM 和 latent-mean estimator 是否收敛？
5. 为什么被选 estimator 胜出，是否依赖 RankIC tie-break？
6. coupled、stopgrad、two-stage 的 gradient 与 RankIC 差异是什么？
7. decoder sensitivity 是否产生可用修复，还是仅证明实现歧义？
8. morphology selection 与 mean-only shadow selection 是否发生不同选择？
9. selected DRC 相对 same-backbone Koopman-only 是否有稳定增量？
10. 2023 early/late 是否仍发生 sign reversal？
11. 为什么即使 candidate gate 通过也不是论文复现或 forward support？
12. 为什么不报告组合收益，以及再平衡频率仍需另立合同？
13. 哪些大文件只保留在本地 canonical？

报告必须分栏：`论文原文`、`21D/21E prior`、`21F inner-fold evidence`、`21F 2023 contaminated readout`。不得混写。

---

## 16. 实现包与静态验收

未来实现包 exact：

```text
configs/config_21f_reaka_semantic_repair_and_stability_validation.yaml
src/run_21f_reaka_semantic_repair_and_stability_validation.py
tests/test_21f_reaka_semantic_repair_and_stability_validation.py
references/21f_semantic_repair/execution_authorization.json
```

正式执行前至少通过：

```bash
uv run python -m py_compile src/run_21f_reaka_semantic_repair_and_stability_validation.py
uv run ruff check src/run_21f_reaka_semantic_repair_and_stability_validation.py tests/test_21f_reaka_semantic_repair_and_stability_validation.py
uv run pytest -q tests/test_21f_reaka_semantic_repair_and_stability_validation.py
uv lock --check
```

测试至少覆盖：

```text
authorization exact keys and hash binding
upstream file-set/hash closure
exact PIT exclusion and inner-fold row hashes
2023 zero-open firewall before pre_2023_complete
historical holdout zero-open throughout
21C Q0 and 21D D4 exact replay
decision-CS z-score fixture and sigma floor
train-only gradient calibration
T1/T2 common initial state and stopgrad-only difference
T3 phase freeze and optimizer ownership
common-random-number prefix identity
antithetic full-noise tensor pairing
DDIM eta=0 determinism
linear-decoder Q2/Q7 commutation
30 inner + 3 refit job cardinality
epoch/estimator/arm lexicographic first-match
mean-only shadow selection noncontrolling
fresh 2023 worker no optimizer/autograd/checkpoint writes
RankIC/morphology/LOMO exact fixtures
Holm family correction
terminal-state first-match
portfolio artifact absence
closed schemas and finite values
manifest/hash exact closure
failed technical validation remains .building
canonical only created by final os.replace
```

---

## 17. 人工评审清单

- [ ] 接受 21F 仍是 design-contaminated semantic repair，不是论文复现。
- [ ] 接受 2023 不参与任何 selection，只做最终机制 readout。
- [ ] 接受 historical design holdout 完全禁止。
- [ ] 接受不重测 100 steps / ResBlock，把预算集中到 scale、Predictor 和 training graph。
- [ ] 确认 5 个 training arms 的单因素关系。
- [ ] 确认 8 个 Predictor estimator/control 的候选资格。
- [ ] 确认 inner fold hashes、33 jobs 和 refit epoch 规则。
- [ ] 确认 DRC 必须相对 same-backbone Koopman-only 提供增量，不能只靠 backbone/normalization 提升。
- [ ] 确认 morphology gates 与 mean-only shadow selection。
- [ ] 确认 candidate 通过后仍不自动授权 forward requirement。
- [ ] 确认当前 requirement review 不构成执行授权。

---

## 18. Definition of Done

本 requirement 文件完成且通过人工评审后，只表示 21F 规格可进入实现阶段。正式实验完成必须同时满足：

```text
all 42 execution/validation gates evaluation_status pass
all 33 planned training jobs accounted
2023 firewall and historical-holdout firewall pass
unique mechanical terminal state generated
Chinese report answers all 13 questions
manifest/output hashes exact closure
canonical atomically sealed only after post-run validation
```

任何 research gate 的 research_status 失败都必须如实形成降级终态，不得修改阈值、补 arm 或重新选择 seed；任何 execution/validation gate 的 evaluation_status 失败都不得密封。
