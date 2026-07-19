# Requirement 21E：REAKA Predictor / Dynamic Residual Corrector 实现识别实验

> 文档状态：`implemented_pending_human_authorization_and_execution`
>
> 生成日期：2026-07-18
>
> Experiment ID：`21_residual_enhanced_koopman_auto_encoder_v0`
>
> Phase ID：`21E_REAKA_PREDICTOR_DRC_IMPLEMENTATION_IDENTIFICATION`
>
> Run ID：`21E_reaka_predictor_drc_implementation_identification`
>
> Requirement version：`21E_IMPL_ID_v0`
>
> 上游终态：`21D_gap_mechanisms_mixed_no_repair_candidate`
>
> Claim ceiling：`design_contaminated_predictor_drc_implementation_identification_only`
>
> 当前执行授权：`false`

## 0. 一页执行结论

本 requirement 假设论文报告为真，不再把 21C 的单一 project-frozen REAKA 实现等同于论文作者实现。目标是逐步回答：

```text
论文未披露的 Predictor / DRC 实现选择中，哪些选择足以实质改变本地 RankIC、
跨 seed 形态和 Monte Carlo 稳定性？
```

论文明确冻结的只有：

```text
R = Z_plus - Z_hat_plus
x_s = sqrt(alpha_bar_s) * R + sqrt(1-alpha_bar_s) * epsilon
epsilon_theta condition = Z
Z_tilde_plus = Z_hat_plus + R_hat
forecast = last element of decoded shifted sequence
```

论文没有冻结：

```text
diffusion step count
beta schedule endpoints / schedule family
denoiser topology
training reconstruction 是否通过 x0_hat 向 denoiser 回传
Predictor 使用单个 residual sample、sample mean、median 或 deterministic proxy
Equation (27) 中 Decoder(Z_plus) 是否为 Decoder(Z_tilde_plus) 的排版错误
decoder topology
seed aggregation
portfolio rebalance frequency
```

21C/21D 已观察到以下实现敏感性，作为本 requirement 的先验而不是 gate evidence：

```text
21C exact 8-draw late RankIC                 = -0.002304
21D D0 Koopman-only late RankIC              = +0.016196
21D D4 prefix8 / prefix64 / ref256 RankIC    = +0.018835 / +0.037315 / +0.050016
21D exact DRC - no-residual paired delta     = -0.018500
```

因此 21E 按以下顺序运行：

```text
Step A: 固定 21C checkpoints，只改变 Predictor point-readout 语义；
Step B: 冻结当前 DRC 拓扑，只改变 reconstruction 与 DRC 的训练梯度连接；
Step C: 冻结 Step B 选择，只改变 denoiser step/topology 或 decoder topology；
Step D: 全部 checkpoint 完成并进入 hash-registered `pre_late_complete` working state 后，fresh worker 统一读取 validation_late；
Step E: 只做机制识别，不产生 forward candidate，不授权下一 requirement 执行。
```

### 0.1 明确不测试每日再平衡

论文 Section 4.5 只披露 `TopK=30` 和 “at each rebalancing date”，没有披露再平衡频率、成交时点、持有期或成本。21E 不生成 TopK
收益、AR、Sharpe、换手、回撤或 execution ledger；这些指标不得参与 Predictor/DRC 实现选择。

本 requirement 只保留 daily cross-sectional RankIC/RankICIR，因为它们直接评价模型 score，不依赖组合再平衡频率。未来若验证投资模拟，必须另立
requirement 并由人工给出或预注册 `rebalance_every_n_sessions`，不得从 Figure 4 的日度净值横轴反推每日调仓。

### 0.2 证据角色与污染边界

21C/21D 已读取 2023 validation_early 和 validation_late 并据此形成当前假设，因此：

```text
train / validation_early / validation_late = design_contaminated_mechanism_diagnostic
historical design holdout                  = forbidden
paper exact implementation claim           = forbidden
paper result reproduction claim            = forbidden
forward support claim                       = forbidden
```

即使某个 arm 在 validation_late 达到论文表中 RankIC，也只能表述为“tested implementation materially changes the local diagnostic”；不得表述为
“找到论文代码”“复现论文”或“修复完成”。

### 0.3 执行授权

当前只授权 requirement 文件生成和人工评审，不授权 config、runner、test、训练或输出生成。正式执行前必须存在人工 authorization，绑定：

```text
schema_version
run_id
requirement_version
approved_requirement_sha256
approved_config_sha256
approved_runner_sha256
approved_test_sha256
approved_paper_pdf_sha256
approved_upstream_21b_v5_manifest_sha256
approved_upstream_21b_v5_output_hashes_sha256
approved_upstream_21c_manifest_sha256
approved_upstream_21c_output_hashes_sha256
approved_upstream_21d_manifest_sha256
approved_upstream_21d_output_hashes_sha256
approved_dependency_lock_sha256
approved_device_fingerprint_sha256
approved_replay_compatibility_profile
replay_implementation_mode
approved_artifact_profile_id
approved_artifact_profile_registry_contract_sha256
allowed_runtime_field_differences
approved_by
approved_at_utc
```

`allowed_runtime_field_differences` 必须是 sorted unique string array；`EXACT_RUNTIME_V1` 时必须为 `[]`。runner 不得生成或补写 authorization，
`approved_by` 不得是 runner/process identity。`approved_artifact_profile_id` 必须 exact 为
`P1_FULL_IMPLEMENTATION_IDENTIFICATION`。

### 0.4 生命周期与密封

遵守项目原则 `Seal Only After the Complete Run`：

```text
working
  -> preflight_checked
  -> predictor_early_complete
  -> training_complete
  -> pre_late_complete
  -> late_readout_complete
  -> post_run_validation_complete
  -> sealed
```

canonical output root 在最后一步前不得存在。任何 preflight、训练、late readout、schema、hash 或报告验证失败，均保留同一 `.building` working
lineage、记录失败并 non-zero exit；不得把 partial/failure bundle 密封为正式结果。

---

## 1. 冻结输入与 immutable pins

所有相对路径以：

```text
experiment_root = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0
```

为唯一解析基准。禁止 `latest`、symlink、glob 选择最新版本或相对当前 shell cwd 解析。

### 1.1 论文原文

```text
path   = paper/Residual-Enhanced_Adaptive_Koopman_Autoencoder_A_Deep_Latent_Dynamics_Model_for_Stock_Prediction.pdf
sha256 = 1041d8693c5ef80fcafc613d77f09bf3ec2a2df673f468785255da27d7d9a472
source = IEEE ICASSP 2026 version of record
```

必须从 PDF 逐项登记 Section 3.3、3.4、3.5、3.6 和 Equations (16)-(31)。不能用 companion report 替代论文原文。

### 1.2 21B v5 model-input pins

21E 训练直接读取 21B v5 的 frozen model-input materialization，因此不能只依赖 21C/21D 的传递性声明：

```text
manifest:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v5/manifest_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = d5ca5c5997c4cce5019e73c0dd0e0fa06c4747a43d323f483c4de29131478d85

output hashes:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v5/output_hashes_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = e20f2ac9e5e49f51494373feaacb93c4e0ea609bb3b563e44fd98a4523db7552
```

`replay_implementation_mode` 必须 exact 为 `import_pinned_21c_21d_with_21b_v5_materialization`。21E 不读取 21B v6 comparator
outputs，也不借此改变 M1/M3 或 row keys。

### 1.3 21C v4 pins

```text
manifest:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4/manifest_21c_full_reaka_pit_proxy_replication.json
  sha256 = b4537b99086c1c89c0f10d494a99aa8fb89434ea12b3557710cba29cfdda1529

output hashes:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4/output_hashes_21c_full_reaka_pit_proxy_replication.json
  sha256 = bb56098ce915e64870a0f1b231c77c1190d4557ddd20c380b66ae23567cb2cc9

expected decision = 21C_FULL_r2_direction_not_supported
```

21C three selected checkpoint byte hashes：

```text
20260713 = 1517fd270a76c5041cb61fb209ef5b0805e7ed203ed0e85463a8f701b6ee85c2
20260714 = 37f50e7ec7f7793752ea7e6964baa7e30913b4e5d1565473e6bb25e6757c443d
20260715 = c8a7f85cdeaf1393b2658a101d7b8e7517926c2cfc7dc38eb16d00b74f23bb4b
```

21C runner/config/test 只允许 hash-pinned import，不得 copy/paste 后静默漂移：

```text
runner sha256 = fc57a05cb9ed9ef16149000137bef965fd1a768a253b5bd790cf51808d3f36a7
config sha256 = 55347efd5aaa4e1132b075fb07e65b46df1e47689dafbb66a724b1ff1d591f7b
test sha256   = 13a9dafbc0eb70b52115f9761556b86eb34787289c51f8388c025f7428f48699
```

### 1.4 21D pins

```text
manifest:
  path   = outputs/21D_reaka_replication_gap_causal_diagnostic_v2/manifest_21d_reaka_replication_gap_causal_diagnostic.json
  sha256 = 8fb9398aebd8586eaccb85fb9c9e72de571bf063b2ad94d12b6e7fcb1b8781e6

output hashes:
  path   = outputs/21D_reaka_replication_gap_causal_diagnostic_v2/output_hashes_21d_reaka_replication_gap_causal_diagnostic.json
  sha256 = 4edd2b6689ed1274f605eba220219ee7ee5ffd231c8c3305838f0ddb1edbc9d4

decision:
  path   = outputs/21D_reaka_replication_gap_causal_diagnostic_v2/21D_reaka_replication_gap_causal_diagnostic_decision.csv
  sha256 = 410c4742afacce6a688781e4c616ccad61847df72fca683d440fd1ce375b6347

expected terminal_state     = 21D_gap_mechanisms_mixed_no_repair_candidate
expected artifact_profile   = P6_FULL_DIAGNOSTIC_FINALIZED
```

21D `inference_draw_scores` 只允许用于 E1 的固定 checkpoint predictor readout；它们不得成为新训练 target、feature 或 checkpoint-selection
input。若本地缺少被 Git ignore 的大文件，preflight 必须以 `missing_local_upstream_artifact` 失败，不得从 output hash registry 伪造空文件或自动重算后冒充
21D 原 artifact。

### 1.5 数据、row keys 和基础模型冻结

沿用 21C/21D：

```text
lookback                         = 10
feature_dim                      = 157
latent_dim                       = 64
operator_n                       = 4
model_seeds                      = [20260713,20260714,20260715]
minimum_complete_cross_section_n = 100
train                            = 2018-01-01..2022-12-31
validation_early                 = 2023-01-01..2023-06-30
validation_late                  = 2023-07-01..2023-12-31
```

必须 exact 复用 v4 retained row keys、instrument/date order、source/teacher sequence、157-feature order、return/label definitions、M1/M3 identities 和
daily RankIC implementation。不得改变 universe、缺失值、归一化、label horizon、seed、epoch budget、optimizer 或 checkpoint-selection metric。

---

## 2. 论文歧义与假设登记

`paper_predictor_drc_ambiguity_registry.csv` 必须在任何模型 outcome 读取前生成，exact schema：

```text
ambiguity_order,ambiguity_id,paper_page,paper_section,paper_equation,
paper_text_semantics,paper_defined,paper_internal_conflict,
21c_project_choice,21d_observation,test_stage,test_arm_ids_json,
allowed_conclusion,forbidden_conclusion,status
```

必须精确包含以下九行：

| ambiguity_id | 论文状态 | 21C 选择 | 21E 处理 |
|---|---|---|---|
| A01_RESIDUAL_TARGET | 已定义 | full shifted latent residual | exact replay |
| A02_DRC_CONDITION | 已定义为 Z | source Z | exact replay |
| A03_DIFFUSION_STEPS_SCHEDULE | 未披露 | 20-step linear β | 20 vs 100 |
| A04_DENOISER_TOPOLOGY | 未披露 | concat MLP | concat MLP vs residual blocks |
| A05_REC_GRADIENT_COUPLING | 未披露 | single-timestep x0_hat enters L_rec | G0/G1/G2 |
| A06_CORRECTED_LATENT_NOTATION | Eq. 21/26 与 Eq. 27 冲突 | Decoder(Z_tilde_plus) | corrected vs Koopman-only control |
| A07_POINT_PREDICTOR_AGGREGATION | 未披露 | 8 draw score mean | P0-P6 |
| A08_DECODER_TOPOLOGY | 未披露 | shared pointwise linear | linear vs pointwise MLP |
| A09_REBALANCE_FREQUENCY | 未披露 | daily Top30 proxy | out_of_scope，不产生组合指标 |

`paper_defined=false` 的行不得把任何 21E arm 命名为 `paper_exact`、`author_implementation` 或 `correct_implementation`。

### 2.1 预注册假设

`hypothesis_registry.csv` exact schema：

```text
hypothesis_order,hypothesis_id,family_id,hypothesis_statement,
direct_falsifier,required_contrast_ids_json,allowed_conclusion,
forbidden_conclusion,status
```

必须在 E0 生成以下 exact 6 rows；`required_contrast_ids_json` 必须 sorted unique，且只能引用 Section 7.5 已冻结 contrasts。

| hypothesis_id | 假设 | 直接 falsifier |
|---|---|---|
| H21E01_POINT_AGGREGATION_MATERIAL | 单样本/均值/中位数/确定性 proxy 实质改变排序 | P0-P6 late RankIC range < 0.005 且互相日度 rho ≥ 0.95 |
| H21E02_CURRENT_DRC_HARMS_SCORE | 当前 DRC 比 Koopman-only 更差 | P3-P5 delta ≥ 0 且至少 2 seeds 同方向 |
| H21E03_REC_GRADIENT_PATH_MATERIAL | L_rec 通过 x0_hat 回传导致训练失衡 | G1/G2 相对 G0 无 material delta 且 gradient/collapse 不改善 |
| H21E04_DENOISER_OR_SCHEDULE_MATERIAL | 20-step concat MLP 是主要识别缺口 | A1/A2 相对 A0 无 material delta |
| H21E05_DECODER_TOPOLOGY_MATERIAL | shared linear decoder 限制 Predictor | A3 相对 A0 无 material delta |
| H21E06_UNDISCLOSED_CODE_REMAINS | 测试包络后仍存在外部实现识别缺口 | 至少一个非 oracle family 相对 control 形成 coherent material improvement，且 late ensemble RankIC 增量 ≥ 0.020、至少 2 seeds 同方向 |

假设表必须在 preflight hash 中；不得在看到 early/late 后增删或改写 falsifier。

`hypothesis_readout.csv` exact schema：

```text
hypothesis_order,hypothesis_id,fold,required_contrast_ids_json,
direct_test_complete,falsifier_triggered,material_evidence_n,
directional_evidence_n,conflicting_evidence_n,evidence_paths_json,
readout_status,allowed_conclusion
```

exact `6 hypotheses × 2 folds = 12 rows`。`falsifier_triggered` 和 `readout_status` 只允许由 frozen registry、closed metrics 和 Section 7.6
materiality mechanical derive；报告不得另造人工标签。

---

## 3. Step A：固定 checkpoint Predictor 读出

Step A 不训练任何参数。每个 P arm 必须使用相同 21C checkpoint、相同 hard selector、相同 `Z_source`、`Z_hat_plus`、decoder 和 row-keyed noise
schedule。唯一变化是 residual point prediction 定义。

### 3.1 Predictor arm registry

| arm_id | point predictor | draws | 说明 |
|---|---|---:|---|
| P0_CURRENT_SCORE_MEAN8 | mean of 8 decoded scores | 8 | 21C exact control |
| P1_SINGLE_DRAW0 | decoded score from draw 0 | 1 | 论文 singular sample literal control |
| P2_SCORE_MEAN64 | mean of decoded scores 0:63 | 64 | reduced-MC point estimator |
| P3_SCORE_MEAN256_REF | mean of decoded scores 0:255 | 256 | reference point estimator |
| P4_ZERO_NOISE_REVERSE_PROXY | x_T=0 and every ξ=0 | 0 | deterministic proxy，不得称 conditional mean |
| P5_KOOPMAN_ONLY | Decoder(Z_hat_plus) | 0 | Equation (27) literal / no-residual control |
| P6_SCORE_MEDIAN256 | median of decoded scores 0:255 | 256 | robust point estimator，非论文定义 |

P0/P1/P2/P3/P6 必须从 21D sealed D0 draw arrays机械派生；P4/P5 必须由 fresh inference-only worker 读取相同 checkpoint 生成。P0 必须与
21C v4 prediction score bitwise/semantic exact，否则 `exact_predictor_replay_gate=fail`。

P4 必须在 registry 中固定：

```text
initial_x_T = all_zero
reverse_step_noise = all_zero
posterior_mean_claim_allowed = false
label = zero_noise_reverse_path_proxy
```

### 3.2 Step A 禁止项

- 不得用 late RankIC 选择 draw count；
- 不得生成新的随机 seed；
- 不得对 score 做 rank-normalization、z-score 或 volatility scaling；
- 不得把 P4 称为 DDPM conditional expectation；
- 不得把 P5 称为论文 w/o DRC ablation 的 exact 实现；
- 不得用 Top30 收益或换手评价 P0-P6。

### 3.3 Predictor materiality

对同一 fold/seed/day 做 paired RankIC delta。`predictor_semantics_material=true` 必须同时满足：

```text
max(ensemble_mean_RankIC among P0..P6)
  - min(ensemble_mean_RankIC among P0..P6) >= 0.010

存在一个相对 P0 的 pre-registered contrast：
  abs(mean_daily_RankIC_delta) >= 0.005
  same_direction_seed_n >= 2
  median_daily_score_spearman_vs_P0 < 0.95
```

只满足其中部分必须为 `directional_only`，不能写 `material`。

---

## 4. Step B：DRC training-graph 受控实验

Step B 使用 21C current denoiser topology、20-step schedule、shared linear decoder 和 64-draw evaluation predictor。除指定梯度路径外，模型、初始化、
optimizer、batch、epoch、patience、loss top-level weights、Gumbel schedule 全部不变。

### 4.1 Training-graph arms

| arm_id | shifted reconstruction latent | DRC receives L_rec gradient | 角色 |
|---|---|---:|---|
| G0_CURRENT_X0_COUPLED | Z_hat_plus + x0_hat(single random s) | true | 21C exact retrain control |
| G1_STOPGRAD_X0_RECON | Z_hat_plus + stopgrad(x0_hat) | false | test rec-gradient coupling |
| G2_TEACHER_LATENT_RECON_ORACLE | Z_teacher_plus | false | non-deployable decoder/latent oracle control |

所有 arms 的 `L_diff` 均保持标准 epsilon prediction；`R_target=Z_teacher_plus-Z_hat_plus` 不变。G1 只在进入 `L_rec` 前 detach `x0_hat`，不得 detach
`L_diff`、`Z_hat_plus` 或 decoder。G2 的 inference 仍使用正常 DDPM；它只能回答 decoder/latent upper-bound，不得晋级为部署实现。

### 4.2 Exact replay gate

G0 的三个 seed 必须从相同 initialization、batch order、noise/Gumbel streams 重训，并重现 21C：

```text
selected_epoch exact
checkpoint semantic hash exact
validation_early per-row score semantic hash exact at P0_CURRENT_SCORE_MEAN8
```

任一不一致必须在进入 G1/G2 outcome comparison 前 fail；不得放宽为 approximate tolerance。

### 4.3 Step B checkpoint selection

每个 arm/seed 独立训练；checkpoint 只由 validation_early mean daily RankIC 选择，first-max tie break。禁止跨 seed 选择 best seed。

所有 G/A trainable arms 的 epoch selection predictor 固定为 `P0_CURRENT_SCORE_MEAN8`。不得因 Step A 显示 64/256 draws 更好而修改训练期
checkpoint-selection predictor。checkpoint 选定后才生成 64-draw primary diagnostic。G0 的 epoch selection 必须与 21C 逐 epoch 8-draw
score exact，保证 exact replay gate 有定义。

Step C 使用的 training-graph winner 只可从 `G0` 或 `G1` 选择，G2 永远不可晋级。选择规则按顺序：

1. training/checkpoint/schema 全部 pass；
2. validation_early 三个 seed 至少 2 个 finite；
3. raw-return zero-solution/collapse 指标不得比 G0 同时恶化；
4. 最大 ensemble validation_early mean daily RankIC；
5. 差值绝对值 `<0.002` 时选择更简单的 G1（较少 rec-to-denoiser gradient）；
6. 全部不合格时固定 G0 并记录 `no_training_graph_promoted`。

该选择在 validation_late worker 启动前写入 `training_graph_selection.json` 并参与 pre-late hash。

---

## 5. Step C：DRC topology / schedule / decoder 受控实验

Step C 复用 Step B 已完成并登记 working hash 的 selected training graph。A0 是被选 G arm 的 checkpoint alias，不重复训练；A1-A3 各训练
3 seeds。

| arm_id | denoiser | diffusion | decoder | 变化 |
|---|---|---|---|---|
| A0_SELECTED_GRAPH_CONTROL | concat MLP 160-128-128-64 | linear β, 20 | Linear(64,1) | alias control |
| A1_MLP_100_STEP | concat MLP 160-128-128-64 | linear β, 100 | Linear(64,1) | step count only |
| A2_RESBLOCK_20_STEP | exact residual-block denoiser | linear β, 20 | Linear(64,1) | topology only |
| A3_POINTWISE_MLP_DECODER | concat MLP 160-128-128-64 | linear β, 20 | 64-64-1 MLP | decoder only |

所有 schedule 均固定 `beta_start=1e-4, beta_end=2e-2`。A1 只改变 step count，不同时改 β family/endpoints。

A2 exact topology：

```text
u = concat[x_s(64), Z_source(64), sinusoidal_time_embedding(32)]
h = SiLU(Linear(160,128)(u))
for block in [1,2]:
    r = Linear(128,128)(SiLU(Linear(128,128)(h)))
    h = LayerNorm(h + r)
epsilon_hat = Linear(128,64)(h)
```

A3 exact pointwise decoder：

```text
DecoderMLP(z) = Linear(64,1)(SiLU(Linear(64,64)(z)))
```

它对每个 time position 共享参数，仍输出 shifted sequence；最终 score 仍是最后一个 position。不得引入 attention、cross-stock layer、额外 feature
head 或 sequence flattening。

### 5.1 初始化与参数顺序

21C 已有参数必须完全复用 21C ordered initialization contract。新增参数冻结如下：

```text
A2 residual-block Linear weights = 与 21C 相同 keyed Xavier-uniform generator route
A2 residual-block Linear biases  = zero
A2 LayerNorm weights             = one
A2 LayerNorm biases              = zero
A3 decoder hidden/output weights = 与 21C 相同 keyed Xavier-uniform generator route
A3 decoder hidden/output biases  = zero
```

每个 arm 必须在 outcome access 前写 `ordered_parameter_names_sha256`、`initial_state_semantic_sha256` 和逐参数 shape。不得依赖 PyTorch module
construction 的偶然遍历顺序；新增参数 key 必须由 `(run_id,arm_id,model_seed,parameter_name)` 确定。

### 5.2 资源与公平性

- A1 允许较长 wall time，但 optimizer steps/epoch budget 与其他 arms 相同；
- resource probe 必须为各 topology 找到共同 batch size；若共同 batch 不成立，全部 arms 使用最小可行 batch；
- 不得只为某一 arm 使用 gradient accumulation、AMP、compile 或不同 early-stopping patience；
- 参数量、FLOPs、peak VRAM、wall seconds 必须记录，但不能作为 outcome 后删除 arm 的理由。

### 5.3 推断 readout

G0-G2、A1-A3 的 primary point predictor 固定为 `score_mean64`。在 validation_early 完成后，按 Step B 规则选择的 training graph control和
validation_early 最优的一个 `A1-A3` 非-control arm额外生成 `score_mean256_ref`。选择结果必须在 late 前进入 hash-registered
`pre_late_complete` working state；同一次成功 run 启动 late worker 后不得改写。若后续验证失败，可在同一 `.building` lineage 修复并从 late 前
状态重跑，不得把该 working checkpoint称为 sealed artifact。其余 arms 不因 late 结果追加 256 draws。

---

## 6. Worker firewall 与 stage 顺序

Execution stage IDs exact：

```text
E0_PREAUTH_AND_PREFLIGHT
E1_PREDICTOR_EARLY_READOUT
E2_DRC_TRAINING_AND_EARLY_SELECTION
E3_PRE_LATE_COMPLETE
E4_FRESH_LATE_READOUT
E5_FINALIZE_AND_SEAL
```

### 6.1 E0

- 验证 authorization、paper/21B v5/21C/21D pins、exact file sets；
- 验证 21D 本地大 draw artifacts 存在且 hash 正确；
- 写 ambiguity/hypothesis/arm/contrast registries；
- 冻结所有 arms、seeds、thresholds、schemas 和 expected artifact universe；
- 不读取任何 prediction outcome。

### 6.2 E1

- inference-only worker；
- 只读取 21C checkpoint、21D D0 draw arrays、validation_early input；
- 生成 P0-P6 validation_early scores；
- 不读取 validation_late；
- 不创建 optimizer/autograd/train loader。

### 6.3 E2

- training worker 运行 G0-G2、A1-A3 共 `6 arms × 3 seeds = 18 jobs`；
- train loader 只能读取 train；
- validation_early 只用于 epoch selection、training-graph selection和唯一 256-draw promoted readout selection；
- training process 不得打开 validation_late 路径或 21D late draw shards。

### 6.4 E3

parent 必须验证：

```text
18/18 jobs completed
18/18 selected checkpoints present
G0 exact replay passed
training_graph_selection complete and hash-registered
promoted_ref256_selection complete and hash-registered
all early predictions complete
worker exit records pass
late access count = 0
checkpoint/pre-late manifest and hashes exact
```

此阶段只是 pre-late complete working state，不创建 canonical sealed output。

### 6.5 E4

fresh late-readout worker：

- 只读已完成 checkpoint bundle 和 validation_late；
- 禁止 optimizer、autograd、train loader；
- 对所有 P/G/A identities 生成预注册 readout；
- 不得改变 checkpoint、draw count、arm、threshold、ensemble 或 promoted identity；
- 成功退出后由 parent 写 worker exit record。

### 6.6 E5

只读 finalized working artifacts，生成 paired metrics、hypothesis readout、decision、中文报告、manifest/hash；完成全部 post-run validation 后才允许
atomic rename `.building -> canonical`。

---

## 7. Metrics 与比较合同

### 7.1 Primary metrics

每个 `(fold, arm_id, score_variant, seed/ensemble)` 必须生成：

```text
mean_daily_RankIC
std_daily_RankIC_ddof1
RankICIR = mean / std
positive_RankIC_day_rate
complete_day_n
score_std
```

ensemble 固定为三个 seed raw score arithmetic mean；同时报告日内 rank-normalized seed mean 作为 diagnostic-only，不得替换 primary。

### 7.2 Morphology metrics

```text
pairwise_seed_daily_score_spearman
pairwise_seed_top30_overlap_n
ensemble_to_seed_daily_score_spearman
adjacent_day_top30_turnover_proxy
score_to_label_std_ratio
score_collapse_flag
```

Top30 overlap/turnover只用于 score morphology，不得生成收益或声称论文再平衡频率。

### 7.3 Draw metrics

P0-P6：

```text
daily_score_spearman_vs_P0
top30_overlap_vs_P0
daily_RankIC_delta_vs_P0
prefix1/8/64_vs_ref256 score spearman
prefix1/8/64_vs_ref256 top30 overlap
MC variance fraction
```

### 7.4 Gradient/collapse metrics

G/A arms 在同一 train-only calibration batches 记录：

```text
L_rec, L_koop, L_diff
gradient_l2_by_loss_and_module
global_diff_gradient_share
decoder_output_std
latent_std
zero_solution_improvement
score_to_label_std_ratio
additional_collapse_flag_n
```

calibration batch row keys必须在 E0 冻结，不得使用 validation。

### 7.5 Pre-registered contrasts

| contrast_id | left | right | family |
|---|---|---|---|
| C01 | P1_SINGLE_DRAW0 | P0_CURRENT_SCORE_MEAN8 | predictor aggregation |
| C02 | P2_SCORE_MEAN64 | P0_CURRENT_SCORE_MEAN8 | predictor aggregation |
| C03 | P3_SCORE_MEAN256_REF | P0_CURRENT_SCORE_MEAN8 | predictor aggregation |
| C04 | P4_ZERO_NOISE_REVERSE_PROXY | P3_SCORE_MEAN256_REF | deterministic proxy |
| C05 | P5_KOOPMAN_ONLY | P3_SCORE_MEAN256_REF | corrected-latent notation / DRC contribution |
| C06 | P6_SCORE_MEDIAN256 | P3_SCORE_MEAN256_REF | robust aggregation |
| C10 | G1_STOPGRAD_X0_RECON | G0_CURRENT_X0_COUPLED | rec-gradient coupling |
| C11 | G2_TEACHER_LATENT_RECON_ORACLE | G0_CURRENT_X0_COUPLED | oracle upper bound |
| C20 | A1_MLP_100_STEP | A0_SELECTED_GRAPH_CONTROL | diffusion steps |
| C21 | A2_RESBLOCK_20_STEP | A0_SELECTED_GRAPH_CONTROL | denoiser topology |
| C22 | A3_POINTWISE_MLP_DECODER | A0_SELECTED_GRAPH_CONTROL | decoder topology |

每个 contrast 在 early/late 分开计算 paired daily delta、three seed deltas、stationary bootstrap p-value。Holm adjustment 只在同一 family/fold 内进行。

### 7.6 Materiality

除 Step A 专用定义外，G/A arm 相对 control 的 `material_change=true` 必须四项同时满足：

```text
abs(late ensemble mean daily RankIC delta) >= 0.005
same-direction seed_n >= 2
median paired-day score Spearman < 0.95
cross-seed stability or collapse metric 至少一项改善且另一项不恶化超过 10%
```

`material_change` 是历史机制诊断，不是 candidate gate。

---

## 8. Closed schemas

### 8.1 `implementation_arm_registry.csv`

```text
arm_order,arm_id,stage_family,training_required,checkpoint_source,
training_graph_id,denoiser_topology,diffusion_steps,beta_schedule,
decoder_topology,point_predictor_id,draw_n,seed_n,oracle_control,
paper_defined_fields_json,project_choice_fields_json,selection_role,status
```

exact rows：`P0-P6,G0-G2,A0-A3`，共 14 行。

### 8.2 `predictor_readout_registry.csv`

```text
readout_order,point_predictor_id,residual_source,initial_x_T_role,
reverse_noise_role,aggregation_domain,aggregation_function,draw_start,
draw_stop_exclusive,draw_n,deterministic,conditional_mean_claim_allowed,
paper_defined,score_index,status
```

exact 7 rows，对应 P0-P6。`score_index` 对所有行均为 `last_shifted_position`。

### 8.3 Prediction parquet

```text
fold_order,fold,arm_order,arm_id,model_seed,is_ensemble,
score_variant,draw_n,decision_date,instrument,row_key,score,raw_label,
checkpoint_semantic_sha256,predictor_semantic_sha256
```

Schema exact；`raw_label` 只允许 late worker/finalize读取，不得出现在 train worker IPC payload。每个 complete row key 必须且只能出现一次。

### 8.4 `daily_rankic_readout.csv`

```text
fold_order,fold,arm_order,arm_id,score_variant,model_seed,is_ensemble,
decision_date,row_n,RankIC,score_std,label_std,metric_day_status,
checkpoint_semantic_sha256,predictor_semantic_sha256
```

### 8.5 `contrast_registry.csv` 与 `paired_implementation_contrasts.csv`

`contrast_registry.csv`：

```text
contrast_order,contrast_id,family_id,left_arm_id,left_score_variant,
right_arm_id,right_score_variant,primary_metric,materiality_rule_id,
oracle_involved,allowed_conclusion,forbidden_conclusion,status
```

exact 11 rows C01-C06、C10-C11、C20-C22。

`paired_implementation_contrasts.csv`：

```text
contrast_order,contrast_id,family_id,fold,left_arm_id,left_score_variant,
right_arm_id,right_score_variant,paired_day_n,mean_rankic_delta,
median_rankic_delta,same_direction_seed_n,raw_p_value,holm_p_value,
material_change,status
```

### 8.6 `predictor_draw_stability.csv`

```text
fold,model_seed,decision_date,predictor_left,predictor_right,row_n,
score_spearman,top30_overlap_n,rankic_left,rankic_right,rankic_delta,
mc_variance_fraction,draw_schedule_sha256,status
```

### 8.7 `cross_seed_morphology.csv`

```text
fold,arm_order,arm_id,score_variant,aggregation_role,seed_a,seed_b,
decision_date,metric_id,metric_value,row_n,status
```

`metric_id` exact enum：

```text
daily_score_spearman
top30_overlap
ensemble_to_seed_spearman
adjacent_day_top30_turnover_proxy
score_to_label_std_ratio
score_collapse_flag
```

### 8.8 `training_run_registry.csv`

```text
job_order,arm_id,model_seed,attempt_n,status,selected_epoch,
selected_validation_early_rankic,optimizer_step_n,data_pass_n,
batch_size,parameter_n,peak_vram_bytes,wall_seconds,
checkpoint_path,checkpoint_byte_sha256,checkpoint_semantic_sha256,
selection_worker_exit_record_sha256
```

exact 18 rows；中断后只允许 same job/same state resume，禁止换 seed/batch/init 后仍记 `attempt_n=1`。

### 8.9 `loss_gradient_and_collapse_audit.parquet`

```text
arm_id,model_seed,checkpoint_role,batch_id,module_id,loss_id,
gradient_l2,global_gradient_share,latent_std,decoder_output_std,
zero_solution_improvement,score_to_label_std_ratio,
additional_collapse_flag_n,batch_row_key_sha256,status
```

### 8.10 Access / stage registries

`historical_design_holdout_access_audit.csv`：

```text
stage_id,process_role,artifact_path,open_attempt_n,successful_open_n,
bytes_read_n,first_opened_at_utc,last_opened_at_utc,status
```

所有 outcome process 的 historical rows 必须为零访问。

`stage_status_registry.csv`：

```text
stage_order,stage_id,status,started_at_utc,ended_at_utc,
worker_exit_code,required_artifact_n,observed_artifact_n,
late_access_allowed,status_reason
```

### 8.11 `artifact_profile_registry.csv`

```text
profile_order,artifact_profile_id,required_paths_json,forbidden_paths_json,
conditional_paths_json,registry_contract_sha256,status
```

exact 1 row；`artifact_profile_id = P1_FULL_IMPLEMENTATION_IDENTIFICATION`。`required_paths_json` 必须在 config freeze 时展开为
Section 10 的全部静态文件和 18 个 exact checkpoint paths，不得保留 glob；`conditional_paths_json` 必须为 `{}`。成功 decision、manifest 与 registry
必须使用同一 profile id。

### 8.12 `gate_evidence_21e.csv`

```text
gate_order,gate_id,stage_id,status,check_n,pass_n,fail_n,
evidence_paths_json,first_failure_reason
```

### 8.13 Decision CSV

```text
run_id,requirement_version,artifact_profile_id,terminal_state,evidence_role,
predictor_semantics_status,drc_training_graph_status,drc_architecture_status,
decoder_status,unresolved_external_gap_status,next_requirement_execution_authorized,
decision_reason
```

`next_requirement_execution_authorized` 必须恒为 `false`。

---

## 9. Gates 与终态

Gate order exact：

```text
01 execution_authorization_gate
02 paper_and_upstream_hash_gate
03 upstream_terminal_state_gate
04 retained_universe_exact_match_gate
05 ambiguity_and_hypothesis_registry_gate
06 historical_holdout_zero_access_gate
07 predictor_arm_exact_gate
08 exact_predictor_replay_gate
09 predictor_draw_schedule_gate
10 predictor_early_completion_gate
11 training_arm_exact_gate
12 common_resource_contract_gate
13 training_completion_gate
14 exact_g0_retrain_gate
15 gradient_and_collapse_audit_gate
16 early_selection_firewall_gate
17 pre_late_complete_gate
18 fresh_late_worker_gate
19 prediction_coverage_gate
20 metric_implementation_gate
21 paired_contrast_gate
22 hypothesis_falsification_gate
23 portfolio_output_absence_gate
24 historical_holdout_zero_access_finalize_gate
25 report_decision_consistency_gate
26 artifact_profile_gate
27 output_manifest_hash_gate
28 post_run_validation_gate
29 finalize_transaction_gate
```

只允许以下成功终态：

```text
21E_predictor_semantics_material
21E_drc_training_graph_material
21E_drc_architecture_material
21E_decoder_topology_material
21E_multiple_implementation_ambiguities_material
21E_no_tested_implementation_explains_gap
21E_evidence_mixed_external_implementation_gap_unresolved
```

终态选择：

1. 恰好一个 family material -> 对应单一终态；
2. 两个或以上 family material -> `multiple_implementation_ambiguities_material`；
3. 全部不 material 且结果 finite/complete -> `no_tested_implementation_explains_gap`；
4. material/direct/falsifier互相冲突 -> `evidence_mixed_external_implementation_gap_unresolved`。

任一执行或 validation gate失败均不得生成上述成功终态或 canonical bundle；保留 `.building` 并 non-zero exit。

---

## 10. Artifact universe

Canonical root：

```text
outputs/21E_reaka_predictor_drc_implementation_identification_v0
```

Building root：

```text
outputs/21E_reaka_predictor_drc_implementation_identification_v0.building
```

成功 bundle 必须包含：

```text
21E_reaka_predictor_drc_implementation_identification_report.md
21E_reaka_predictor_drc_implementation_identification_decision.csv
artifact_profile_registry.csv
paper_predictor_drc_ambiguity_registry.csv
hypothesis_registry.csv
hypothesis_readout.csv
implementation_arm_registry.csv
contrast_registry.csv
predictor_readout_registry.csv
predictor_draw_stability.csv
daily_rankic_readout.csv
paired_implementation_contrasts.csv
cross_seed_morphology.csv
loss_gradient_and_collapse_audit.parquet
training/training_run_registry.csv
training/training_graph_selection.json
training/promoted_ref256_selection.json
training/checkpoint_manifest.json
training/checkpoints/<G0-G2,A1-A3>/<seed>/state_dict.pt
training/selection_worker_exit_record.json
training/late_readout_worker_exit_record.json
predictions/validation_early_prediction_scores.parquet
predictions/validation_late_prediction_scores.parquet
preflight/execution_authorization_audit.csv
preflight/upstream_pin_and_file_set_audit.csv
preflight/retained_universe_exact_match_audit.csv
preflight/replay_runtime_fingerprint.json
preflight/resolved_config.yaml
historical_design_holdout_access_audit.csv
stage_status_registry.csv
gate_evidence_21e.csv
semantic_reproducibility_manifest.json
manifest_21e_reaka_predictor_drc_implementation_identification.json
output_hashes_21e_reaka_predictor_drc_implementation_identification.json
```

Checkpoint directories exact：`6 trainable arms × 3 seeds = 18`；A0 是 alias，不允许复制出第二套 checkpoint bytes。

禁止存在：

```text
paper_proxy_top30_daily.csv
portfolio_*.csv
execution_*.csv
annualized_return*.csv
sharpe*.csv
turnover*.csv
historical_holdout_predictions*
best_seed*
post_late_added_arm*
```

Output hashes 文件排除自身；manifest 包含其他全部 artifact；semantic manifest、report、decision、artifact set 和 byte hashes 必须双向闭合。

### 10.1 Manifest 自引用合同

`semantic_reproducibility_manifest.json` exact top-level keys：

```text
schema_version,run_id,requirement_sha256,resolved_config_sha256,
paper_pdf_sha256,upstream_semantic_hashes,retained_row_key_hashes,
ambiguity_registry_sha256,hypothesis_registry_sha256,arm_registry_sha256,
contrast_registry_sha256,hypothesis_readout_sha256,initial_state_semantic_hashes,
checkpoint_semantic_hashes,predictor_semantic_hashes,
draw_schedule_semantic_hashes,metric_semantic_hashes,
semantic_payload_bundle_hash
```

`manifest_21e_reaka_predictor_drc_implementation_identification.json` exact top-level keys：

```text
schema_version,run_id,requirement_version,requirement_sha256,
config_sha256,runner_sha256,test_sha256,authorization_sha256,
paper_pdf_sha256,upstream_pins,replay_identity,artifact_profile_id,
artifact_profile_registry_sha256,
terminal_state,artifact_n,artifacts,report_sha256,decision_sha256,
semantic_reproducibility_manifest_sha256,
output_hashes_path,output_hashes_excluded_self_path,finalized_at_utc
```

闭包顺序固定：

1. 生成并验证所有数据、metrics、decision、report 和 semantic manifest；
2. manifest 的 `artifacts` 列出除 manifest 自身与 output-hashes 自身外的 exact artifact set；
3. 写 manifest；
4. output-hashes `entries` 列出除 output-hashes 自身外的全部文件，因此包含 manifest；
5. 独立重算 path set、size 和 SHA-256；
6. 删除 working-only state/failure logs；
7. 原子 rename 到 canonical root。

不得把 output-hashes 自身 hash 写回自身，也不得在 manifest 写入尚未生成的 output-hashes byte hash。

### 10.2 大文件发布边界

canonical bundle 在本地必须完整，manifest/hash 必须覆盖大文件；但 Git 发布遵守仓库现行规则：任何单文件 `size_bytes > 20 MiB` 必须以 exact
path 加入 `.gitignore`，不得进入 Git index，其余文件正常发布。不得用删除大文件、截断 parquet 或改写空 placeholder 的方式让 artifact profile
通过；报告必须注明哪些 canonical artifacts 因体积只保留在本地。

---

## 11. 中文报告必须回答的问题

1. 论文明确给出的 Predictor/DRC 语义和未披露项分别是什么？
2. 21C 的哪些选择只是 project choice？
3. 单样本、8/64/256 mean、median、zero-noise proxy、Koopman-only 的排序差异有多大？
4. 当前 DRC 相对 Koopman-only 是增益还是伤害？是否跨 seed 一致？
5. `L_rec -> x0_hat -> denoiser` 梯度连接是否导致 gradient dominance/collapse？
6. 100 steps、residual-block denoiser、MLP decoder 哪些变化 material？
7. 哪些结果只是 oracle/diagnostic，不可作为 inference implementation？
8. 为什么本实验不能声称找到论文作者实现？
9. 为什么不报告组合收益，以及再平衡频率为何仍未识别？
10. 外部官方代码/作者说明仍缺失时，剩余不可识别项是什么？

报告必须把 `论文原文`、`21C project choice`、`21D prior observation`、`21E direct evidence` 四类证据分栏，不得混写。

---

## 12. 实现与静态验收命令

实现包包含：

```text
configs/config_21e_reaka_predictor_drc_implementation_identification.yaml
src/run_21e_reaka_predictor_drc_implementation_identification.py
tests/test_21e_reaka_predictor_drc_implementation_identification.py
references/21e_impl_id/execution_authorization.json
```

在正式执行前至少通过：

```bash
uv run python -m py_compile src/run_21e_reaka_predictor_drc_implementation_identification.py
uv run ruff check src/run_21e_reaka_predictor_drc_implementation_identification.py tests/test_21e_reaka_predictor_drc_implementation_identification.py
uv run pytest -q tests/test_21e_reaka_predictor_drc_implementation_identification.py
uv lock --check
```

测试必须覆盖：

- authorization exact keys/hash binding；
- canonical root 在 finalize 前不存在；
- P0 exact score replay；
- P4 零噪声路径定义；
- P5 不调用 denoiser；
- P0-P6 不创建 optimizer；
- G0 checkpoint/early score exact replay；
- G1 只有 x0-to-Lrec gradient 被 detach；
- G2 永不可晋级；
- A1 只改变 steps；
- A2 exact residual-block topology；
- A3 exact pointwise decoder；
- train/early/late access firewall；
- 18/18 jobs与 checkpoint cardinality；
- late worker禁止 optimizer/autograd/train loader；
- portfolio artifact absence；
- closed schemas、NaN/Inf、row-key uniqueness；
- materiality四项 conjunction；
- terminal-state first-match；
- manifest/hash exact closure；
- failed validation 保持 `.building` 且不得 seal。

---

## 13. 人工评审清单

- [ ] 接受本阶段只做 implementation identification，不做论文复现宣称
- [ ] 接受 2023 全部结果为 design-contaminated diagnostic
- [ ] 接受不读取 historical design holdout
- [ ] 接受不输出组合收益/AR/Sharpe/再平衡结论
- [ ] 确认 P0-P6 predictor point definitions
- [ ] 确认 G0-G2 gradient-path definitions
- [ ] 确认 A1-A3 topology/schedule/decoder definitions
- [ ] 确认 G2 oracle 不可晋级
- [ ] 确认所有 arms 在运行前冻结，late 后不得新增
- [ ] 确认 18 个训练 jobs 的预算
- [ ] 确认 exact replay gates 不使用 tolerance 放宽
- [ ] 确认 materiality 是四项 conjunction
- [ ] 确认任何成功终态也不授权下一 requirement 执行
- [ ] 确认只有完整运行和 post-run validation 后才能密封
- [ ] 评审后另行生成并 hash-bind config/runner/test/authorization
