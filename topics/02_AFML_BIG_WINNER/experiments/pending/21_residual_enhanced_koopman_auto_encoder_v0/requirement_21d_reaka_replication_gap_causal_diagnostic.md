# Requirement 21D-GAP：REAKA 论文差距因果诊断与修复候选再验证

> 文档状态：`revised_requirement_pending_human_rereview`
>
> 生成日期：2026-07-17
>
> Experiment ID：`21_residual_enhanced_koopman_auto_encoder_v0`
>
> Phase ID：`21D_REAKA_REPLICATION_GAP_CAUSAL_DIAGNOSTIC`
>
> Run ID：`21D_reaka_replication_gap_causal_diagnostic`
>
> Requirement version：`21D_GAP_v2`
>
> 上游密封结果：`21C_FULL_v4 / 21C_FULL_r2_direction_not_supported`
>
> Claim ceiling：`design_contaminated_mechanism_diagnostic_and_forward_candidate_generation_only`
>
> 当前执行授权：`false`

## 0. 一页执行结论

21C_FULL_v4 已经证明当前 full REAKA local adaptation 在完整、无 historical-holdout access 的执行链上失败：

```text
validation_early ensemble RankIC = +0.015658
validation_late ensemble RankIC  = -0.002304
R2 - M1 late paired delta        = -0.021898
R2 - M3 late paired delta        = -0.012987
cross-seed daily rank correlation ≈ 0
late Top30 overlap               ≈ random expectation
late target turnover             = 93.82%
```

本 requirement 不再重复“同配置再跑一次”，而是验证以下失败链是否成立：

```text
raw-return reconstruction has an easy near-zero solution
    -> latent / decoder / score amplitude contracts
    -> unscaled diffusion objective dominates useful forecast learning
    -> high-temperature soft selector is evaluated as hard argmax
    -> finite stochastic DDPM draws scramble a weak cross-sectional score
    -> early-selected apparent signal does not survive late readout
```

本阶段保持以下内容完全不变：

```text
v4 retained PIT instrument set
train / validation_early / validation_late row keys
157-feature order and normalized feature cache
raw qfq source-return and label source
T = 10
model seeds = 20260713|20260714|20260715
minimum cross-section N = 100
daily RankIC implementation
M1/M3 comparator identities
historical holdout prohibition
```

唯一允许变化的是预注册的 return-path transform、loss-gradient scaling、selector train semantics、residual arm 和 inference draw
aggregation。每项变化必须由单因素 arm 隔离；不得在看到 validation_late 后增加新 arm、替换 seed、修改 threshold 或选择 best seed。

### 0.1 这是 ex-post 机制诊断，不是新的独立 OOS 验证

本 requirement 的假设由 21C_FULL_v4 的 validation_late 结果生成，因此：

```text
2018-2023 train/validation evidence role = design_contaminated_mechanism_diagnostic
validation_late role                     = paired_diagnostic_readout_only
paper_result_reproduced claim            = false
historical OOS claim                     = false
forward support claim                    = false
```

即使某个修复 arm 在原 validation_late 上转正，也只能生成一个待 seal 的 forward candidate，不能写成“已修复”或“已复现论文”。
可信确认必须另立 `21F` requirement，在最终候选 seal 之后从第一个新 exchange session 开始累计。

### 0.2 当前文档只授权生成实现草案，不授权执行

执行前必须由人工审阅并提供外部 authorization，绑定：

```text
approved_requirement_sha256
approved_config_sha256
approved_runner_sha256
approved_test_sha256
approved_upstream_21c_manifest_sha256
approved_upstream_21c_output_hashes_sha256
approved_upstream_21b_v5_manifest_sha256
approved_upstream_21b_v5_output_hashes_sha256
approved_upstream_21b_v6_manifest_sha256
approved_upstream_21b_v6_output_hashes_sha256
approved_replay_compatibility_profile
approved_dependency_lock_sha256
approved_device_fingerprint_sha256
```

Authorization JSON top-level keys exact：

```text
schema_version,run_id,requirement_version,approved_requirement_sha256,
approved_config_sha256,approved_runner_sha256,approved_test_sha256,
approved_upstream_21c_manifest_sha256,approved_upstream_21c_output_hashes_sha256,
approved_upstream_21b_v5_manifest_sha256,approved_upstream_21b_v5_output_hashes_sha256,
approved_upstream_21b_v6_manifest_sha256,approved_upstream_21b_v6_output_hashes_sha256,
replay_implementation_mode,approved_replay_compatibility_profile,
allowed_runtime_field_differences,approved_dependency_lock_sha256,
approved_device_fingerprint_sha256,approved_by,approved_at_utc
```

`allowed_runtime_field_differences` 是 sorted unique string array；`EXACT_RUNTIME_V1` 时必须 `[]`。禁止 unknown keys、wildcard、
`latest`、null hash 或 runner 自动回填。`approved_by` 不得是 runner/process identity。

requirement 不得通过自写 `approved=true`、读取当前文件 mtime 或自动接受最新文件来获得执行权。

### 0.3 与原 research plan 21C/21D 路线的关系

原 research plan 要求先做 `K1/K1C/K2`，再做 `R1/R2` nested attribution；21C_FULL_v4 经人工 scope restart 跳过了该链，直接运行
full R2。本 requirement 是失败后的 corrective diagnostic，不得伪装成原路线已经完成：

```text
original 21C adaptive Koopman attribution = not completed
original 21D diffusion-specific attribution = not completed
this requirement = post-21C full-model failure diagnostic
```

`D5/D6/D0` 只能补回最小的 `K2 -> R1 -> R2` residual path，不能支持 single-vs-adaptive operator 归因。若本轮结果显示 K2 值得继续，
仍需另行实现 `K1_SINGLE_KOOPMAN_AE` 与 `K1C_STATE_INDEPENDENT_MULTI_OPERATOR_CONTROL`，不能从 D5 推导 adaptive selector有效。

### 0.4 Execution stage IDs

本文中 execution stage 只用 `E*`，artifact profile 只用 `P*`，不得混用：

```text
E0_PREAUTH_AND_PREFLIGHT
E1_SEALED_CHECKPOINT_INFERENCE
E2_TRAINING_AND_EARLY_SELECTION
E3_PRE_LATE_SEAL
E4_FRESH_LATE_READOUT
E5_FINALIZE
```

---

## 1. 冻结输入、路径与血缘

### 1.1 上游 immutable pins

本节所有 `outputs/...` 相对路径均以以下目录为唯一解析基准：

```text
experiment_root = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0
```

禁止相对当前工作目录、`latest` symlink或glob解析。

```text
21C v4 manifest:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4/manifest_21c_full_reaka_pit_proxy_replication.json
  sha256 = b4537b99086c1c89c0f10d494a99aa8fb89434ea12b3557710cba29cfdda1529

21C v4 output hashes:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4/output_hashes_21c_full_reaka_pit_proxy_replication.json
  sha256 = bb56098ce915e64870a0f1b231c77c1190d4557ddd20c380b66ae23567cb2cc9

21C v4 decision:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4/21C_full_reaka_pit_proxy_replication_decision.csv
  sha256 = 0eaaed6f2ec80fc8db0ca3588bf26ca6d0d4f48400eabdb198702461603ef664
  expected stage_decision = 21C_FULL_r2_direction_not_supported

21C v4 detailed companion report, hypothesis source only:
  path   = outputs/21C_full_reaka_pit_proxy_replication_v4_detailed_report_cn.md
  sha256 = 1b0e0d8dd910202d85616706089b4f97745f07a1761df9753564d4bda0cf1d70

21C v4 approved implementation, D0 replay identity:
  runner path   = src/run_21c_full_reaka_pit_proxy_replication.py
  runner sha256 = fc57a05cb9ed9ef16149000137bef965fd1a768a253b5bd790cf51808d3f36a7
  config path   = configs/config_21c_full_reaka_pit_proxy_replication.yaml
  config sha256 = 55347efd5aaa4e1132b075fb07e65b46df1e47689dafbb66a724b1ff1d591f7b
  test path     = tests/test_21c_full_reaka_pit_proxy_replication.py
  test sha256   = 13a9dafbc0eb70b52115f9761556b86eb34787289c51f8388c025f7428f48699
  resolved config sha256 = e42344507e84143ef144ce6ab777306bc551558e46c02f0cd64ee178b183bf19
  initialization contract sha256 = 0cfa6396dd0092c4257775c8eabe90490adc605f8fdb218fb6179ea4a8b08d5a
  ordered parameter names sha256 = ec20a64e5f363ea1cf4202a96c7bead9e1898cca3e3dbee2d73031fbd457af8f
  v4 device fingerprint sha256 = 4c6f9920f77f29f963ef9a37283c8012e3814d0838ae77abb719f0bcc939155b
  seed-level training curves sha256 = 40925a6e6456bf173764aec5abfa4934cb690ef44f2b0b1d4eb9deee06b9fa57
  early score semantic/byte sha256 = 5718ebdd5e5bb905850de7cb8742df90dc7c3fe1748a4c57abeb5537aebb81e5
  late score semantic/byte sha256 = a65f17c25de09117dc376e45c7c48a1456545a43371b38931c152ab988914a7c

  seed 20260713:
    selected epoch = 8
    selected early RankIC = 0.005949575429699258
    checkpoint byte sha256 = 1517fd270a76c5041cb61fb209ef5b0805e7ed203ed0e85463a8f701b6ee85c2
    model semantic sha256 = cd82c881c535500e1c6f4b93184605f0a8a5fa24f3de15ed0df698a832ce31cd
  seed 20260714:
    selected epoch = 16
    selected early RankIC = 0.009829404192532967
    checkpoint byte sha256 = 37f50e7ec7f7793752ea7e6964baa7e30913b4e5d1565473e6bb25e6757c443d
    model semantic sha256 = e1678f1f31fb6837cc0d7449a64b08b65f2fbe48411d2b6843acaf6a1218fcfd
  seed 20260715:
    selected epoch = 3
    selected early RankIC = 0.008025732739492664
    checkpoint byte sha256 = c8a7f85cdeaf1393b2658a101d7b8e7517926c2cfc7dc38eb16d00b74f23bb4b
    model semantic sha256 = ff28f8c6ba815dbddec63e3ab2242bf1be3d91e77f408e3b61c3e997f64c16a8

21B v5 model-input manifest, exact D0-D6 training source:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v5/manifest_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = d5ca5c5997c4cce5019e73c0dd0e0fa06c4747a43d323f483c4de29131478d85

21B v5 model-input output hashes:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v5/output_hashes_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = e20f2ac9e5e49f51494373feaacb93c4e0ea609bb3b563e44fd98a4523db7552

21B v6 comparator-score manifest only:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v6/manifest_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = 443c0cee3dd247596e2150c22c9f2e1cdeb5d3629f59853cfe655d0069f42917

21B v6 comparator-score output hashes only:
  path   = outputs/21B_alpha158_sequence_baseline_benchmark_v6/output_hashes_21b_alpha158_sequence_baseline_benchmark.json
  sha256 = e219b2416c0e413979919d51ec8c8c4481db9404a3c4b50625d5832ec7ed02d9
```

Companion report 只用于登记推测来源，不得替代 sealed CSV/Parquet 证据。任何数值必须从上游密封 artifact 重算并记录输入 hash。
21B v5 的 `sequence_sample_index` 和 fold panels 是 D0-D6 唯一 composite model-input source，再按 v4 exclusion registry/retained
row keys 机械过滤。21B v6 只允许读 Section 7.4 的 M1/M3 row-level comparator scores，不得替换 D0-D6 panel；
v5 不得用作 M1/M3 comparator score source。

### 1.2 预期实现路径

```text
requirement = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/requirement_21d_reaka_replication_gap_causal_diagnostic.md
config      = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/configs/config_21d_reaka_replication_gap_causal_diagnostic.yaml
runner      = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21d_reaka_replication_gap_causal_diagnostic.py
test        = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21d_reaka_replication_gap_causal_diagnostic.py
authorization = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/references/21d_gap_v2/execution_authorization.json
output_root = experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/outputs/21D_reaka_replication_gap_causal_diagnostic_v2
```

禁止覆盖或追加写入 21A、21B、21C 的任何 output、checkpoint、manifest 或 report。

### 1.3 固定样本与 universe

使用 21C_FULL_v4 已密封的 retained row keys：

| Fold | Rows | Complete days | Retained date range | Role |
|---|---:|---:|---|---|
| train | 335,393 | 842 | 2018-01-02..2022-12-14 | diagnostic training |
| validation_early | 51,932 | 107 | 2023-01-04..2023-06-30 | checkpoint selection |
| validation_late | 50,167 | 103 | 2023-07-03..2023-12-13 | contaminated paired diagnostic readout |

```text
exclusion registry path = references/21c_full_v3/pit_universe_exclusion_registry.csv
exclusion registry sha256 = 3c3d903821ee56a49f1ea0d83327606b58f87826ae317d6f95e5a5d4236aef11
train retained instrument n = 860
train retained row-key sha256 = d1d22a89e6b8096645f1f91b7941f22cd30670aabfbb37d3e388ca324daf6e4e
validation_early retained instrument n = 625
validation_early retained row-key sha256 = 633f2bf154e826a5228c8e73c3bc361812c52fd63d3379ccd01966c80dbb8ba8
validation_late retained instrument n = 592
validation_late retained row-key sha256 = 1f46023e27b72e67afd10e01eb10daff7192c39f4be0d72846cc0ff4906e5adc
```

必须 exact-match：

```text
instrument exclusion registry SHA256
retained fold row-key hashes
feature cache content hash
feature expression/order hash
normalization contract hash
source-return panel hash
teacher-extension row-key hash
label materialization hash
```

本 requirement 不得新增或删除 instrument，不得恢复被 v4 排除的 instrument，不得改变某日 denominator，也不得将 PIT universe
差异作为本轮解释变量。

---

## 2. 推测登记：observations、hypotheses 与 falsifiers

`hypothesis_registry.csv` 必须在任何新 score、loss 或 validation readout 生成前写入并进入 pre-execution seal。以下文本是唯一
authorized hypothesis family。

### H01：raw-return MSE 诱导 near-zero representation collapse

```text
hypothesis_id = H01_RAW_RETURN_ZERO_SOLUTION
prior_strength = high
status_at_requirement_time = suspected_not_proven
```

Draft-time observations：

- train raw one-step return median约为 `0`，标准差约为 `0.028`；
- 按当前 reduction，zero-output `L_rec` 约为 `0.001559`；
- 三个 selected checkpoints 的 `L_rec` 约为 `0.001500`，只比 zero-output 改善约 4%；
- selected checkpoints 的 decoder weight norm 约为 `0.012-0.026`；
- late score standard deviation 约为 `1.5e-4-2.0e-4`。

这些 draft-time 数值不是 gate evidence。`E1_SEALED_CHECKPOINT_INFERENCE` 必须从密封 memmap、training curves 和 checkpoints 独立复算。

支持 H01 的预注册形态：

```text
zero_solution_improvement = 1 - selected_L_rec / zero_output_L_rec
decoder_norm_ratio = selected_decoder_weight_l2 / initialization_decoder_weight_l2
latent_effective_rank_ratio = latent_covariance_effective_rank / 64
decoded_source_std_ratio = decoded_source_std / raw_source_std

primary_zero_solution_flag = median_seed(zero_solution_improvement) <= 0.10
primary_score_contraction_flag = median_seed(score_std / raw_label_std) <= 0.05
additional_collapse_flag_n =
    count_true(
      median_seed(decoder_norm_ratio) <= 0.25,
      median_seed(latent_effective_rank_ratio) <= 0.25,
      median_seed(decoded_source_std_ratio) <= 0.10
    )

H01 direct morphology support =
    primary_zero_solution_flag
    AND primary_score_contraction_flag
    AND additional_collapse_flag_n >= 2
```

H01 direct morphology 只使用三个 `SEALED_V4_R2` selected checkpoints；D0 用于 exact replay consistency，D1 只作为
intervention readout。不得从 D1 改善后反向重定义 sealed collapse threshold。

上述 ratio 一律在 canonical train audit sample 上按 seed 先算，再取 seed median；初始化 norm 必须来自该 seed 首个
optimizer step 之前的 state。latent per-dimension variance 与 constant-score proximity 作为连续 readout 发布，但不得在执行后
再临时设 threshold。单独一个权重 norm 不得决定 H01。
任一 ratio denominator `<=1e-12`、non-finite 或 audit sample 不完整时 H01 为 `not_evaluable`，不得用 floor 代替。

反证条件也固定为：`median_seed(zero_solution_improvement) >= 0.25` AND
`median_seed(latent_effective_rank_ratio) > 0.25` AND `median_seed(decoded_source_std_ratio) > 0.10`，且
return-path-normalized arm 不改善 primary score contraction。其余组合只能记为 `mixed`。

### H02：diffusion objective 的数值/梯度尺度压过 forecast learning

```text
hypothesis_id = H02_DIFFUSION_GRADIENT_DOMINANCE
prior_strength = high
status_at_requirement_time = suspected_not_proven
```

已观察到 selected checkpoint 的 `L_diff / L_total` 约为 `97.5%-98.6%`，但 loss value 不能替代 gradient evidence。

支持条件必须同时使用 train-only gradient audit：

```text
g_j = global L2 norm of gradient from loss j over the exact ordered parameter set
share_diff = g_diff / (g_rec + g_koop + g_diff)
```

H02 的 direct gradient dominance 只由 gradient evidence 决定：

```text
global_dominance = median_batch(share_diff) >= 0.80
module_dominance_n = count_module(median_batch(module_share_diff) >= 0.80)
direct_gradient_dominance = global_dominance AND module_dominance_n >= 4 of 6
```

六个 module exact 为 `encoder|gate|selector|koopman_codebook|decoder|residual_corrector`；对当前 arm 不存在的 module
记为 structural zero，不进入 `module_dominance_n` denominator，R2 必须有六个。support 映射固定为：

```text
direct_gradient_dominance AND D2 material improvement -> strongly_mechanism_consistent
direct_gradient_dominance AND NOT D2 material improvement -> mechanism_consistent
NOT direct_gradient_dominance AND D2 material improvement -> mixed
NOT direct_gradient_dominance AND NOT D2 material improvement -> not_supported
```

必须同时报告 module-specific gradient norm 和 gradient cosine；不得由 loss 数值比例或 intervention improvement
单独宣布 gradient dominance。

### H03：高温 soft selector 与 hard-argmax inference 错配

```text
hypothesis_id = H03_SELECTOR_SOFT_HARD_MISMATCH
prior_strength = high
status_at_requirement_time = suspected_not_proven
```

密封 curves 显示 selected checkpoint tau 为 `0.928/0.856/0.973`，而 inference 使用 hard argmax。

支持条件：

```text
direct_selector_mismatch =
    mean_daily_spearman(hard_score, deterministic_soft_mixture_score) < 0.90
    OR mean hard-vs-soft Top30 overlap < 24 of 30
```

必须报告 operator share、selector entropy、effective operator count、switching rate和跨 seed assignment agreement。若 selector 在
selected checkpoint 已经接近 one-hot 且 hard/soft score高度一致，则 direct mismatch 不支持。support 映射固定为：

```text
direct_selector_mismatch AND D3 material improvement -> strongly_mechanism_consistent
direct_selector_mismatch AND NOT D3 material improvement -> mechanism_consistent
NOT direct_selector_mismatch AND D3 material improvement -> mixed
NOT direct_selector_mismatch AND NOT D3 material improvement -> not_supported
```

### H04：有限 DDPM draws 的 Monte Carlo noise 主导弱 score

```text
hypothesis_id = H04_DDPM_MONTE_CARLO_RANK_NOISE
prior_strength = high
status_at_requirement_time = suspected_not_proven
```

当前证据是 seed 排名相关接近零、Top30 overlap 接近随机、目标换手 93.82%；这些形态也可能来自优化不稳定，不能单独证明 sampling noise。

`E1_SEALED_CHECKPOINT_INFERENCE` 必须对每个密封 checkpoint 生成 exact `256` draws，并将 draw `0..255` 固定分为 32 个不重叠 8-draw blocks。定义：

```text
score_ref_256 = mean(draw_0 ... draw_255)
score_block8_b = mean(draw_8b ... draw_8b+7)
mc_noise_var_of_mean8 = mean_row(sample_var(draw_scores, ddof=1)/8)
cross_section_signal_var = mean_day(var_i(score_ref_256, ddof=1))
mc_noise_fraction = mc_noise_var_of_mean8 /
                    (mc_noise_var_of_mean8 + cross_section_signal_var)
rho_block8_ref(seed,day,b) = spearman_i(score_block8_b, score_ref_256)
overlap_block8_ref(seed,day,b) = |Top30(score_block8_b) intersect Top30(score_ref_256)|
```

支持条件：

```text
median_{seed,day,b}(rho_block8_ref) < 0.90
OR median_{seed,day,b}(overlap_block8_ref) < 24
OR mc_noise_fraction > 0.25
```

median 的 denominator exact 为三个 seeds、该 fold 全部 complete days、32 个 blocks；任一 seed/day/block 缺失或 N `<100`
使该 fold 的 H04 readout `not_evaluable`，不得 drop-null 后继续。`mc_noise_fraction` 先在 row/day 层计算两项
variance 的算术平均，再代入比率；不得取 row-level fraction 的 median。
两项 variance 必须 finite/non-negative；分母 `<=1e-18` 时 readout `not_evaluable`，不得写0。
主 H04 support 使用 validation_late；validation_early 作为同定义 descriptive replication，不得在两个 fold 中挑选更差的一个。

RankIC 改善不是识别 sampling noise 的必要条件；即使 256-draw RankIC仍为负，只要排名不收敛，也可支持“8 draws不够稳定”。
`score_ref_256` 只是预注册 high-draw internal reference，不是 DDPM expectation 的解析真值；结论不得写成
256 draws 已完全收敛。

在 retraining 完成后，`E4_FRESH_LATE_READOUT` 还必须对 `D0_R2_RAW_EXACT_REPLAY` 与 `D4_R2_REPAIR_COMBINED_V1` 的三个
selected checkpoints在 validation_early/late 上运行同一 256-draw reference，并从同一 draw prefix 计算 8/64/256 score。
否则 D4 candidate stability gate为 `not_evaluable`，不得用 sealed v4 checkpoint的收敛结果替代。

### H05：paper/local return path 与 preprocessing 语义不等价

```text
hypothesis_id = H05_RETURN_PATH_PREPROCESSING_MISMATCH
prior_strength = medium_high
status_at_requirement_time = paper_pipeline_unknown
```

论文没有披露 normalization；本地使用 train median/IQR features、raw qfq return path、无 return-path CS normalization、无 day-balanced loss。
本地 Alpha route 还是 157-feature registered adaptation，不是 exact Alpha158 materialization。

本 requirement 只验证“完整 return-path 的 decision-cross-section scale 是否解释本地退化”，不得反向声称论文使用了
Qlib `CSZScoreNorm`，也不得将 source-input reparameterization 和 forecast-target scaling 分开归因。即使 CS normalization arm
改善，也只能写：

```text
local failure is sensitive to a project-defined full return-path decision-cross-section transform
```

### H06：论文未披露 architecture/search choices 造成 residual gap

```text
hypothesis_id = H06_UNDISCLOSED_IMPLEMENTATION_AND_SEARCH
prior_strength = medium_high
status_at_requirement_time = not_identifiable_without_external_source
```

operator count、latent width、LSTM depth、GateNet、Gumbel schedule、DDPM schedule、optimizer、batch、seed selection和 inference
sampling均未完整披露。没有官方 code/config/search log 时，本 requirement 不得把 H06 判为 true 或 false；只能在其他可检验假设被反证后保留为
`residual_unresolved_explanation`。

### H07：样本时期和短 late window 的 regime/domain shift

```text
hypothesis_id = H07_PERIOD_REGIME_SHIFT
prior_strength = medium
status_at_requirement_time = descriptive_only
```

论文 test 是 2019-2020，本地 late 只有 2023H2 的 103 日。月度、LOMO和 regime slice 可以描述异质性，但由于没有相同模型在论文数据
上的可比运行，本阶段不能识别 period 的独立因果贡献。

### H08：early checkpoint selection 适配而非可迁移 alpha

```text
hypothesis_id = H08_EARLY_SELECTION_ADAPTATION
prior_strength = high
status_at_requirement_time = observed_pattern_not_isolated
```

early ensemble 为正、late 转负，selected epochs 为 `8/16/3`。本 requirement 为保持单因素可比性，不改变 primary checkpoint rule；只记录
early-to-late gap、seed dispersion和 checkpoint-path morphology。新的 checkpoint-selection rule 必须另立 requirement，不得在本 run 中事后替换。

---

## 3. 数据 transform 与 anti-leakage contract

### 3.1 RAW_RETURN_CURRENT_V1

完全继承 v4：

```text
y_source = raw qfq close-to-close one-step returns
y_teacher_shifted = raw qfq close-to-close one-step returns
forecast_y = qfq_close(t+1)/qfq_close(t)-1
evaluation label = same raw return, ranked cross-sectionally only at metric time
```

### 3.2 DECISION_CS_ZSCORE_RETURN_PATH_V2

这是只依赖 sealed composite panel 的 project diagnostic transform，不得命名为 paper exact preprocessing 或 Qlib exact
`CSZScoreNorm`。它不再尝试从 sample panel 反推历史 `U_d_decision`，也不授权重读 raw qfq、membership、calendar、
metadata 或 name history。

对每个已密封 `(fold, decision_date=t)`，以 v4 retained row keys 形成唯一 `R_t_v4`。对 source lag
`j=0..9` 以及 train-only forecast target `j=10`，直接在该 decision date 的完整 retained rows 上计算：

```text
r_i,t,j = sealed return_and_label_panel value at row i, decision date t, position j
N_t = count(R_t_v4)
mu_t,j = mean_{i in R_t_v4}(r_i,t,j)
sd_t,j = std_{i in R_t_v4}(r_i,t,j, ddof=1)
z_i,t,j = (r_i,t,j - mu_t,j) / sd_t,j
```

规则：

- `R_t_v4` 必须与 v4 retained decision rows exact，`N_t` 必须与 sequence index 的当日行数 exact；不得按
  某个 lag 或 label 的 availability 逐股缩小 denominator；
- panel 全部为 finite float32；`sd_t,j <= 1e-12`、`N_t <100` 或 denominator 不完整时整日 fail closed；
- 不 winsorize、不 clip、不拟合跨日统计；每个 `mu_t,j/sd_t,j` 仅用同一 decision date 和 lag position的截面；
- `mu/sd/z` 用 float64 累加和 ddof=1 计算，最终 model tensor cast 为 little-endian float32；回算后必须满足
  `abs(transformed_mean)<=1e-5` 且 `abs(transformed_std_ddof1-1)<=1e-5`，否则整日 fail closed；
- 同一 `(instrument, raw_return_date, raw_return)` 在不同 decision sample 中可因 `R_t_v4` 不同而得到不同 z-score；
  这是预注册的 sample-position transform，不是 return-date universe transform；
- train teacher 最后一个未来 return 复用 `j=10` 的 train decision-date transform，不以未来 membership
  重定义 denominator；
- train `j=10` 只用于 loss target；它的 value、`mu_t,10`、`sd_t,10` 不得进入 source tensor、sample
  selection 或 validation inference；
- validation 只对 `j=0..9` 构造 source transform；validation `j=10` 不生成 z-score，metric 仍对 sealed raw
  label rank 计算；
- `E2` 只允许为 train/validation_early 生成 transform audit；selection worker 和任何 pre-late process 不得 open/mmap
  validation_late panel；
- `E4` fresh late worker 才为 validation_late `j=0..9` 生成 transform audit，并与 pre-late train/early audit 在
  `.building` 中重建完整 final file；不得原地 append；
- `return_path_transform_audit.parquet` 必须按 `(fold,decision_date,position)` 发布 `N/mu/sd/row_key_hash`；
  train/early semantic hash 进入 pre-late seal，三 fold final semantic hash 进入 final manifest。

Transformed tensor semantic hash 对每 fold 按 original `fold_panel_row_idx` 升序、position 升序的 little-endian float32
C-contiguous bytes 计算，hash preimage 还必须包含 schema ID、shape 和 dtype。不得对 Parquet byte serialization 本身作为
transformed value semantic hash。

这一路径仅验证“完整 return path 改用 decision-cross-section scale 后，本地退化是否敏感”，不能分开识别
source-input 和 forecast-target 的贡献，也不能证明论文使用了同一路径。

---

## 4. Mandatory arms 与单因素识别

全部 learned arms 使用三个冻结 seeds。禁止 best seed、额外 seed、joint grid或 failed-arm replacement。

| Arm ID | Return path | Loss scaling | Selector train | Residual | Inference | Role |
|---|---|---|---|---|---|---|
| `D0_R2_RAW_EXACT_REPLAY` | raw | 1:1:1 | soft Gumbel | DDPM | 8-draw mean | exact retrain control |
| `D1_R2_RETURN_PATH_CSZ_ONLY` | full return path decision-CS z-score | 1:1:1 | soft Gumbel | DDPM | 8-draw mean | H01/H05 bundled-path factor |
| `D2_R2_GRADBAL_ONLY` | raw | train-calibrated frozen | soft Gumbel | DDPM | 8-draw mean | H02 single factor |
| `D3_R2_ST_HARD_ONLY` | raw | 1:1:1 | straight-through hard | DDPM | 8-draw mean | H03 single factor |
| `D4_R2_REPAIR_COMBINED_V1` | full return path decision-CS z-score | train-calibrated frozen | straight-through hard | DDPM | 64-draw mean | predeclared operational bundle |
| `D5_K2_RAW_NO_RESIDUAL` | raw | 1:1 | soft Gumbel | none | deterministic | diffusion removal diagnostic |
| `D6_R1_RAW_MLP_RESIDUAL` | raw | 1:1:1 | soft Gumbel | matched MLP | deterministic | generic residual comparator |

`arm_order` exact 为 `SEALED_V4_R2=-1`、`D0..D6=0..6`、`M1_LIGHTGBM=101`、`M3_GATED_LSTM=103`。
Learned arm registry 只包含 D0-D6；M1/M3 是 pinned comparator，SEALED 是 inference-only identity。

D0-D4 是 paired interventions。对同一 model seed，它们必须共用 v4 的 weight initialization、dataloader order、Gumbel U、
diffusion-train noise 和 inference draw preimage；除 Section 4 显式变量外，shared parameter 的 initialization tensor 必须
byte-equivalent。D5/D6 与 D0 的 shared modules 也必须 byte-equivalent 初始化；D6 新增 MLP 只使用
`sha256("21D_D6_MLP|<model_seed>|<parameter_name>")` 的独立 stream。arm ID 不得隐式改变 shared RNG。

### 4.1 Exact replay control

`D0` 的 module topology、initialization、optimizer、batch、epoch、patience、tau、RNG、loss、draw和 selection 必须 exact 等于 v4。
实现可复用已 pin 的 21C module，或在 21D runner 中重实现；两种方式都必须在 authorization 中固定
`replay_implementation_mode=import_pinned_21c|reimplemented_with_semantic_equivalence`，不得执行时切换。
D0 的 initialization、dataloader、Gumbel、diffusion-train 和 inference 全部 RNG channel 必须继续使用
`seed_run_id=21C_full_reaka_pit_proxy_replication`、`seed_arm_id=R2_REAKA_DIFFUSION`；`D0_*` 只是输出元数据身份，
不得进入任何 seed preimage。

`replay_runtime_fingerprint.json` 必须在加载 checkpoint 前生成，至少绑定 Python、PyTorch、CUDA/runtime、cuDNN、
NumPy、device name/capability、deterministic flags、CUBLAS workspace、dependency-lock SHA256 与 Section 1.1 的 v4 device fingerprint。
authorization 只允许：

```text
approved_replay_compatibility_profile = EXACT_RUNTIME_V1
OR approved_replay_compatibility_profile = PREDECLARED_SEMANTIC_COMPATIBILITY_V1
```

`EXACT_RUNTIME_V1` 要求 checkpoint semantic hash、selected epoch、early score、curves 和 draws `0..7` exact。
`PREDECLARED_SEMANTIC_COMPATIBILITY_V1` 必须由外部 authorization 在执行前列出唯一 allowed runtime field differences，且至少满足：

```text
same selected epoch per seed
max abs early score difference <= 1e-7
same daily rank ordering
same late RankIC within 1e-10
```

没有外部预授权 compatibility profile 时不得从 exact 自动降级到 tolerance。Exact replay gate失败时，不得解释其他
retrained arm；只能保留 `E1` sealed-checkpoint inference diagnostics。

### 4.2 Train-calibrated fixed gradient scaling

只使用 train、每 seed 初始化后的 exact 32 个 stable-hash temporal-stratified batches，不访问 validation。
抽样算法固定为：

1. 对 train 的 unique decision dates 升序排列，按日期个数用 `numpy.array_split(...,4)` 形成四个连续 temporal strata；
2. 对每个 stratum 内的 row 计算
   `sha256("21D_GRAD_CAL_V2|<model_seed>|<decision_date>|<instrument>")`；
3. 按 `(hash,decision_date,instrument)` 升序，每 stratum 取前 `8 * 256 = 2048` rows，严格切为 8 个 batch；
4. 四个 strata 合计 `32 batches / 8192 unique rows`；不足 2048 rows 的 stratum fail closed；
5. 发布每个 stratum/batch 的 row-key hash、min/max date 和 row count，不得用最早 row-key prefix 代替。

对每个 batch 固定同一次 forward 产生的 Gumbel/diffusion noise，用 `torch.autograd.grad`分别计算
`L_rec/L_koop/L_diff` 到 exact ordered parameter set；每项重算不得消耗 RNG。未参与某 loss 的 parameter gradient视为0。所有 norm
必须在 gradient clipping、weight decay、optimizer state update 之前计算；校准阶段不得调用 `optimizer.step()`。定义：

```text
g_j = median_batch(global_gradient_l2(loss_j))
u_j = 1 / max(g_j, 1e-12)
w_j_raw = u_j / mean(u_rec,u_koop,u_diff)
w_j = clip(w_j_raw, 0.05, 20.0)
w_j = w_j / mean(w_rec,w_koop,w_diff)
module_share_diff_m = g_diff_m / max(g_rec_m + g_koop_m + g_diff_m, 1e-12)
```

三项 weight 按 seed 独立校准，随后整个训练冻结；禁止每 epoch自适应、读取 validation后改权重或用 late RankIC选择 weight。必须发布原始
batch-level gradient norms、聚合值、clip前后权重和 module-specific gradients。

Gradient batch registry identities exact 为 `SEALED_V4_R2|D0_R2_RAW_EXACT_REPLAY|D2_R2_GRADBAL_ONLY|D4_R2_REPAIR_COMBINED_V1`，
每 identity/seed exact 32 batches，总行数 `4*3*32=384`。`SEALED_V4_R2` 和 D0 在 selected checkpoint 做 `phase=audit`；
D2/D4 在 optimizer step 0 做 `phase=calibration`，并在 selected checkpoint 再做 `phase=audit`。H02 的
`direct_gradient_dominance` 只使用 `SEALED_V4_R2, phase=audit`；D0 用于 replay consistency，D2/D4 只用于 intervention
mechanism readout。

### 4.3 Straight-through hard selector

保持 v4 logits、Gumbel U、tau schedule和 RNG draw order，只改变 selector forward：

```text
y_soft = softmax((logits + gumbel_noise)/tau)
y_hard = one_hot(argmax(y_soft))
selector = y_hard - stop_gradient(y_soft) + y_soft
```

forward 使用 one-hot，backward 使用 soft relaxation。Inference 仍为 deterministic `argmax(logits)`。不得同时改变 tau schedule。

### 4.4 K2 与 R1

`D5` exact 使用 21A `K2_ADAPTIVE_KOOPMAN_AE` graph：

```text
Z_hat_shifted = K_selected @ Z_source
decoded_shifted = Decoder(Z_hat_shifted)
L_total = L_rec + L_koop
score = decoded_shifted[:,T-1,0]
```

`D6` exact 使用 21A `R1_AKS_MLP_RESIDUAL` graph和 parameter-matched residual MLP：

```text
R_hat_mlp = Linear(64,160) -> SiLU -> Linear(160,160) -> SiLU -> Linear(160,64)
Z_tilde_mlp = Z_hat_shifted + R_hat_mlp(Z_source)
L_total = L_rec_mlp + L_koop + L_residual_mlp
score = Decoder(Z_tilde_mlp)[:,T-1,0]
```

21A 已冻结 `primary_R1_hidden_width=160`、R1 residual parameters=`46,464`、R2 denoiser parameters=`45,376`，relative delta
`0.0239774321`。实现必须复算并 exact-match；不得重新遍历 candidate widths或按 validation结果选择。

---

## 5. Sealed-checkpoint inference-only diagnostics

`E1_SEALED_CHECKPOINT_INFERENCE` 在任何 retraining 前对三个 v4 checkpoints执行，禁止修改 checkpoint。

### 5.1 Selector readouts

对每 row/seed同时生成：

```text
hard_score = current hard argmax selector + current 8 draws
deterministic_soft_mixture_score = softmax(logits / selected_checkpoint_tau) operator mixture + same draw schedules
```

两路必须使用相同 residual noise，从而把差异限制在 operator mixture。输出 daily Spearman、Top30 overlap、score delta、operator entropy、
operator share和 switching rate。

`deterministic_soft_mixture_score` 是 no-Gumbel diagnostic，不等于 train-time Gumbel-soft sample 的期望，不得命名为
`soft_expectation_score`，也不得替换 sealed v4 primary result。

### 5.2 Draw convergence

对每个 `(fold,row,seed)` 生成 draws `0..255`，seed formula继承 v4并把 draw_id 扩展到255。Sealed v4 checkpoint diagnostics和
`D0` exact replay必须使用原 identity：

```text
seed_run_id = 21C_full_reaka_pit_proxy_replication
seed_arm_id = R2_REAKA_DIFFUSION
```

从而 draws `0..7` exact重放 v4。D1-D4 也使用相同 `seed_run_id/seed_arm_id`，形成 common-random-number
paired draws；它们的 21D arm ID 只写入 artifact metadata，不进入 seed preimage。不得让文件路径、batch position或新
runner 名称隐式进入 seed。每个 arm 的 metadata identity 和 RNG identity 必须分别写入 resolved config/draw manifest。

物理保存的 256-draw identities exact 为：

```text
SEALED_V4_R2: 3 seeds x validation_early|validation_late
D0_R2_RAW_EXACT_REPLAY: 3 seeds x validation_early|validation_late
D4_R2_REPAIR_COMBINED_V1: 3 seeds x validation_early|validation_late
```

共 `18` 个 shard。每个 shard 一行对应一个 decision row，用 `fixed_size_list<float32>[256]` 保存所有 draws；不得
用重复 instrument/date 的 long-form 2.35 亿行格式。预期：

```text
draw_shard_n = 18
draw_sample_row_n = 918891
draw_scalar_n = 235236096
raw_draw_float_bytes = 940944384
```

从 shard 必须可 exact recompute：

```text
per-draw final scalar score
8-draw block means
32-draw prefix mean
64-draw prefix mean
128-draw prefix mean
256-draw reference mean
```

不得只保存聚合后 RankIC；必须保留能重算 row-level draw variance和 block stability的证据。shard 路径、schema、
sort key、compression 与 row count 见 Section 10；大型 Parquet 按仓库 Git LFS 规则处理。

### 5.3 Koopman-only checkpoint surgery diagnostic

同一 v4 checkpoint额外输出：

```text
score_koopman_only = Decoder(Z_hat_shifted)[:,T-1,0]
```

它只回答“当前 joint-trained checkpoint 的 residual path是否改变排序”，不是公平的 no-diffusion trained ablation。公平归因必须使用 `D5/D6/D0`。

---

## 6. 训练、selection 与 fresh-process readout

### 6.1 训练参数

除 arm table 指定差异外，全部 exact 继承 v4：

```text
latent_dim = 64
lstm_layers = 1
n_operator = 4
diffusion_steps = 20
beta = linear 1e-4 .. 2e-2
optimizer = AdamW(lr=0.001, weight_decay=1e-5)
batch_size = mechanically inherited v4 selected 256
max_epochs = 100
patience = 10
precision = fp32
deterministic_algorithms = true
day_balanced_loss = false
```

不得为 decision-CS normalized return path 改 learning rate、gradient clip、epoch或 patience。

### 6.2 Checkpoint selection

每 arm/seed 只按 `validation_early_mean_daily_RankIC` 选择；tie 取最早 epoch。Validation early inference使用该 arm冻结的 inference
语义：D4 固定64 draws，其余R2为8 draws，K2/R1 deterministic。

Selection worker不得打开 validation_late，也不得打开 `E1` 中任何基于 validation_late 的 draw/selector/surgery/
metric artifact；selected checkpoints、early scores、curves和 config进入 pre-late seal。`E1` 完成后必须退出，`E2`
使用新 process 且其 access whitelist 由 pre-execution config hash 固定。

### 6.3 Late readout process

必须在 pre-late seal 完成后启动 fresh inference-only process：

- 不持有 optimizer、train loader、validation_early labels或 Python model state；
- 只读 eligible checkpoint、validation_late source tensor和冻结 draw contract；
- 不允许重新选择 checkpoint、seed或 arm；
- 输出 late prediction score后立即写 worker exit record；
- finalize在另一个只读 process中计算 metrics。

此 process isolation 保证机械一致性，但不改变 validation_late 已被设计污染的证据角色。

### 6.4 Job accounting、resource 与 restart contract

Learned job set 在 authorization 前固定：

```text
learned_arm_n = 7
model_seed_n = 3
planned_learned_job_n = 21
planned_primary_job_n = 21
planned_sensitivity_job_n = 0
maximum_attempt_n_per_job = 1
failed_job_replacement_n = 0
extra_search_job_n = 0
```

`model_search_accounting_manifest.csv` 必须在训练前生成 exact 21 rows，按 `(arm_order,model_seed)` 排序。工程中断只能从
同一 job 的密封 resumable state 继续，`attempt_n` 仍为1；不允许换 seed、换 batch、重置初始化或将中断 job
当作新 attempt。若无 exact optimizer/RNG/dataloader state，则该 job fail closed，整个 training profile blocked。

Resource probe 只验证冻结 `batch_size=256`，不得使用 128/64/32/16 fallback ladder。必须在训练前使用最大图 R2、
64-draw inference 和一个 256-draw shard writer 通过 forward/backward/optimizer/inference/write probe。预注册上限：

```text
total_gpu_wall_seconds_cap = 86400
canonical_output_root_bytes_cap = 17179869184
draw_dataset_bytes_cap = 4294967296
minimum_free_disk_before_training = 34359738368
draw_shard_n = 18
```

任一 cap 预估或实际超限时停止后续 job，terminal state 为 `21D_gap_training_or_replay_blocked`；已完成的部分 arm
不得进入 hypothesis/candidate interpretation。调高 cap 需要新 requirement hash 和新的外部 authorization。

---

## 7. 必须输出的诊断

### 7.1 Zero-solution 与 representation morphology

每 arm/seed/epoch至少输出：

```text
zero_output_L_source_rec
zero_output_L_shifted_observed_rec
zero_output_L_forecast
zero_output_L_rec
actual_L_rec
zero_solution_improvement
initialization_decoder_weight_l2
decoder_weight_l2
decoder_norm_ratio
decoder_bias_abs
latent_dimension_variance_quantiles
latent_covariance_effective_rank
latent_effective_rank_ratio
decoded_source_std
raw_source_std
decoded_source_std_ratio
forecast_score_std
raw_label_std
score_to_label_std_ratio
additional_collapse_flag_n
```

Zero-output loss exact 继承 v4 reduction：

```text
zero_output_L_source_rec = MeanValid(y_source^2)
zero_output_L_shifted_observed_rec = MeanValid(y_teacher_shifted[:,0:9]^2)
zero_output_L_forecast = MeanBatch(forecast_y^2)
zero_output_L_rec = 0.5*(zero_output_L_source_rec + zero_output_L_shifted_observed_rec)
                    + zero_output_L_forecast
actual_L_rec = train epoch aggregate L_rec recorded by the same v4 reduction
```

`MeanValid` 是 element 均值后对 valid batch/time cells 加权的全样本均值，不是 batch-mean 的无权均值；最后不满 batch
必须按实际 element count 进入 denominator。D1/D4 使用各自 transformed tensors 复算 zero output，其余 arm 使用 raw。
H01 direct gate 使用 sealed v4 selected epoch 的 `actual_L_rec` 和 raw zero output；不得使用 D1/D4 的 z-score 量纲值
替代。

`effective_rank = exp(entropy(normalized_eigenvalues))`，covariance只在 canonical train audit sample上计算。Audit sample必须由 stable hash按 row
key选取，不能按 outcome挑选。

Canonical morphology audit sample 对所有 arm/seed 共用：train dates 按 Section 4.2 分为四个 temporal strata，每 row
计算 `sha256("21D_MORPH_AUDIT_V2|<decision_date>|<instrument>")`，每 stratum 取最小 2048 hashes，共 8192 rows。
按 `(stratum,hash,decision_date,instrument)` 排序，row-key hash 写入每个 collapse row。Latent covariance 对每 row 的
`Z_source[:,T-1,:]` 计算 float64 sample covariance/ddof=1；eigenvalues `<0` 且 absolute value `<=1e-12` 才因数值误差 clip
到0，更小的负值 fail closed。Normalized eigenvalues denominator `<=1e-12` 时 H01 `not_evaluable`。

`decoded_source_std/raw_source_std` 分别对 morphology sample 的 `8192*10` decoded/raw return scalar 用 float64 ddof=1 计算。
`forecast_score_std` 是 validation_late 每 complete day 对 primary score 做截面 float64 ddof=1 std 后的 day median；
`raw_label_std` 以同样方式对 raw label 计算。`score_to_label_std_ratio` 是两个 day-median std 之比，不得将全 fold
rows 直接 pool 后计算。

### 7.2 Loss 与 gradient

```text
loss values by epoch
global gradient L2 by loss term
module gradient L2 by loss term
pairwise gradient cosine by loss terms
gradient clip activation rate
optimizer update norm / parameter norm
```

必须分别覆盖 encoder、gate、selector、K codebook、decoder和 residual corrector。不得用 aggregate total gradient掩盖某 module没有收到
forecast gradient。

### 7.3 Selector/Koopman morphology

```text
operator selection share
selector entropy
effective operator count
daily operator switching rate
operator transition matrix
cross-seed assignment agreement
pairwise K Frobenius distance
spectral radius per K
hard-vs-soft score rank correlation
hard-vs-soft Top30 overlap
```

跨 seed operator label 必须先对齐，否则 raw operator index 可任意置换。每 arm 以 seed `20260713` 为 reference，对其他 seed
枚举 n_operator=4 的 24 个 permutation，最小化 selected-checkpoint `sum_k ||K_ref[k]-K_seed[perm(k)]||_F`；
cost 在 float64 中计算，tie 容差 `1e-12` 内取 lexicographically smallest permutation。同一 permutation 用于该 arm 所有
fold/day 的 assignment/share/transition readout。必须同时发布 raw 与 aligned agreement；candidate 解释只能使用 aligned
agreement。K spectral radius 使用 complex eigenvalue absolute maximum，禁止用 matrix norm 代替。

### 7.4 Predictive morphology

每 arm/seed和 ensemble：

```text
daily RankIC / RankICIR
positive-day rate
monthly RankIC
leave-one-month-out RankIC
early-to-late delta
cross-seed same-day score Spearman
cross-seed Top30 overlap
adjacent-day Top30 turnover
score autocorrelation
Top30-minus-equal-weight raw-label spread
```

Top30 的唯一排序为 `(score DESC, instrument ASC)`；同分不得依赖 input order。RankIC 使用 average-rank ties、
Pearson correlation of ranks；任一侧 constant 时该日 status=`undefined_constant_vector`，不得写0。Top30 raw-label spread 是
当日 Top30 的 raw label 算术平均减完整 denominator raw label 算术平均，不是可执行组合收益。

```text
fold mean RankIC = arithmetic mean of all complete-day RankIC
RankIC std = sample std across complete days, ddof=1
RankICIR = fold mean RankIC / RankIC std
positive-day rate = count(day RankIC > 0) / complete_day_n
monthly RankIC = arithmetic mean of complete-day RankIC inside calendar month
LOMO(month m) = arithmetic mean of complete-day RankIC after excluding month m
```

RankIC std `<=1e-12` 时 RankICIR undefined。Validation_late LOMO months exact 为 `2023-07..2023-12`，必须每个 series 生成 6 个
LOMO rows；`positive LOMO` 指其中 `mean_rankic>0` 的行数。Validation_early 按其实际 calendar months 同定义发布，
不进入 `5/6` candidate gate。

M1/M3不重训。Row-level score唯一来源是 pinned 21B v6：

```text
training/selection/validation_early_prediction_scores.parquet
training/readout/validation_late_prediction_scores.parquet
```

Finalize必须按 v4 retained row keys和 exclusion registry机械过滤，并证明重算后的 M1/M3 late daily RankIC、paired delta与21C v4已密封
readout exact一致。21C v4没有发布独立的 M1/M3 row-level score parquet，因此不得声称从21C目录直接读取这些 rows，也不得用 summary
CSV反推 row score。

### 7.5 Paired contrasts

以下均为 contaminated diagnostic contrasts，使用 paired daily delta、stationary bootstrap 5,000次、mean block length 20：

```text
C01 = D1_RETURN_PATH_CSZ_ONLY@8 - D0_RAW_EXACT_REPLAY@8
C02 = D2_GRADBAL_ONLY - D0_RAW_EXACT_REPLAY
C03 = D3_ST_HARD_ONLY - D0_RAW_EXACT_REPLAY
C04A = D4_REPAIR_COMBINED@8 - D0_RAW_EXACT_REPLAY@8
C04B = D4_REPAIR_COMBINED@64 - D4_REPAIR_COMBINED@8
C04C = D0_RAW_EXACT_REPLAY@64 - D0_RAW_EXACT_REPLAY@8
C04D = D4_REPAIR_COMBINED@64 - D0_RAW_EXACT_REPLAY@64
C04E = D4_REPAIR_COMBINED@64 - D0_RAW_EXACT_REPLAY@8
C05 = D0_RAW_REAKA - D5_K2_RAW_NO_RESIDUAL
C06 = D0_RAW_REAKA - D6_R1_RAW_MLP_RESIDUAL
C07 = D6_R1_RAW_MLP_RESIDUAL - D5_K2_RAW_NO_RESIDUAL
C08 = D4_REPAIR_COMBINED@64 - M1_LIGHTGBM
C09 = D4_REPAIR_COMBINED@64 - M3_GATED_LSTM
```

C01-C03 是单因素机制 family，Holm correction；C05-C07 是 residual attribution family，Holm correction；C08-C09 是 repair candidate
ordering family，Holm correction。C04A-C04E 是预注册的 combined/draw decomposition，单独报告且不做 Holm family；
C04A 仍包含三项 training intervention 与 D4 的64-draw checkpoint-selection semantics，只叫
`combined_training_and_selection_bundle_scored_at_8draw`，不得解释为单一机制或纯 training effect。
C04B/C04C 分别识别同 checkpoint 上的 draw uplift，C04D 是 fixed-64 combined difference，C04E 是实际候选 bundle 相对
v4-style control 的 operational effect。不得从 C01-C03 中挑选最佳 arm。
各 Holm family 内按 `(raw_p_value ASC, contrast_order ASC)` 排序，使用标准 step-down `min(1,(m-k+1)*p_k)` 并做
cumulative maximum 保证 adjusted p 单调；非 Holm family 的 `holm_p_value` 必须 null。

Bootstrap 实现 exact 为 circular stationary bootstrap：day keys 按 exchange date 升序，每个新 block 概率 `p=1/20`，非新 block
使用前一 index `+1 mod day_n`。唯一 RNG 为 `numpy.random.Generator(PCG64(20260717))`，先生成 exact
`5000 x day_n` index matrix，然后对全部 contrasts 复用同一 matrix；禁止每 contrast 重置seed。Two-sided p-value
使用 centered paired-delta series `delta-observed_mean`，exact 为
`(1 + count(abs(bootstrap_centered_mean) >= abs(observed_mean))) / 5001`。CI 使用 uncentered bootstrap mean 的
linear 2.5%/97.5% quantile。

---

## 8. Hypothesis readout 与 falsification rules

`causal_hypothesis_readout.csv` 每 hypothesis必须输出：

```text
hypothesis_id
prior_strength
direct_observation_status
single_factor_intervention_status
falsifier_status
support_level
supporting_artifact_paths
contradicting_artifact_paths
allowed_statement
forbidden_statement
```

`support_level` 只允许：

```text
not_evaluable
not_supported
mixed
mechanism_consistent
strongly_mechanism_consistent
unresolved_external_implementation_gap
descriptive_only
```

禁止使用 `causally_proven`、`paper_pipeline_identified` 或 `paper_false`。

### 8.1 Material improvement 的统一定义

对 C01-C03 和 C04A/C04D/C04E 的“改善”必须同时满足：

```text
late paired mean RankIC delta >= +0.005
AND at least 2 of 3 seed deltas > 0
AND collapse_reduction >= 0.25
AND left_cross_seed_mean_daily_spearman >= right_cross_seed_mean_daily_spearman
```

```text
collapse_abs(series) = abs(early_mean_daily_RankIC(series) - late_mean_daily_RankIC(series))
collapse_reduction = 1 - collapse_abs(left_series) / max(collapse_abs(right_series), 1e-12)
```

left/right series exact 由 contrast ID 中的 score variant 决定。Seed delta 先按相同 model seed 配对，ensemble 不进入
`positive seed` count。cross-seed mean 是三个 seed-pair daily Spearman 先对 complete days 算术平均，再对三个
seed pairs 算术平均；任一 undefined 则 material improvement `not_evaluable`。

由于同一 late 已被观察，这个 threshold只用于机制一致性和候选生成，不是统计确认。

### 8.2 Primary repair candidate gate

只有 `D4_R2_REPAIR_COMBINED_V1` 可生成 forward candidate。必须 conjunctive 满足：

```text
late ensemble RankIC > 0
positive late seeds >= 2/3
positive LOMO >= 5/6
D4@64 - D0@8 paired delta (C04E) >= +0.005
D4@64 - D0@64 paired delta (C04D) >= +0.005
D4@64 - M3 paired delta (C09) > 0
D4@64 - M1 paired delta (C08) > 0
mean cross-seed daily Spearman >= 0.25
mean cross-seed Top30 overlap >= 6 of 30
adjacent-day Top30 turnover <= 0.80
median_{seed,late_day} Spearman_i(D4 score_prefix64, D4 score_ref256) >= 0.95
no H01 zero-solution collapse flag
all coverage/integrity/firewall gates pass
```

Candidate gate 中所有 D4 predictive/morphology metric 都使用 `score_prefix64`；D0 默认使用 `score_prefix8`，只有
C04D 显式使用 `D0@64`。stability 的 exact denominator 是 `3 seeds x 103 validation_late complete days = 309`
daily Spearman values，每个 Spearman 在当日完整 retained rows 上使用 average-rank ties 计算，然后对 309 个值用
ordinary sample median。任一 seed/day 缺失、N `<100`、constant vector 或 non-finite 都使 candidate gate
`not_evaluable`，不得 drop 后重算。

`mean cross-seed daily Spearman/Top30 overlap` 的 denominator exact 为 `3 seed pairs x 103 days = 309`，直接对 309 个
daily values 算术平均。`adjacent-day Top30 turnover` 使用 D4@64 ensemble，对 103 个 complete days 的 102 个相邻
transition 计算 `1-|Top30_t intersect Top30_t-1|/30`，再算术平均。任一 component undefined 都使对应
conjunct `not_evaluable`。

这些 morphology thresholds 是 ex-post diagnostic candidate rules；即使全通过，终态只能是：

```text
21D_gap_repair_candidate_ready_for_forward_seal_review
```

不得称为 alpha supported。

### 8.3 Negative decision interpretation

- 只有 D1改善：full return-path decision-CS scale sensitivity，不能分开归因 source input 或 forecast target，也不能归因于 Koopman或diffusion；
- 只有 D2改善：optimization-scale sensitivity；
- 只有 D3改善：selector discretization sensitivity；
- 256 draws稳定但RankIC仍负：反证 H04 为主因，但不反证H01-H03；
- K2/R1优于R2：residual/diffusion stack is harmful under local raw pipeline；
- R2优于K2但仍为负：residual path改善 reconstruction不等于产生 alpha；
- D4改善但仍落后M1/M3：只能保留 representation repair diagnostic，关闭 forward candidate；
- 所有 intervention均失败：本地可检验机制不足以解释/修复差距，H06/H07保持 unresolved。

### 8.4 Exhaustive support mapping

若任一 hypothesis 所需 artifact/gate 缺失，首先取 `not_evaluable`。否则按下表 first-match，不得人工改级：

| Hypothesis | Condition | support_level |
|---|---|---|
| H01 | direct morphology support AND C01 material improvement | `strongly_mechanism_consistent` |
| H01 | direct morphology support only | `mechanism_consistent` |
| H01 | C01 improvement only or non-falsifier conflict | `mixed` |
| H01 | registered falsifier true AND C01 not improved | `not_supported` |
| H01 | all remaining evaluable cases | `not_supported` |
| H02 | Section H02 four-way mapping | exact mapped level |
| H03 | Section H03 four-way mapping | exact mapped level |
| H04 | 8-draw support condition true AND median rho64-ref256 `>=0.95` | `strongly_mechanism_consistent` |
| H04 | 8-draw support condition true | `mechanism_consistent` |
| H04 | validation_late support condition false | `not_supported` |
| H05 | C01 material improvement | `mechanism_consistent` for local sensitivity only |
| H05 | C01 not materially improved | `not_supported` for this transform; paper pipeline remains unknown |
| H06 | always, absent official implementation | `unresolved_external_implementation_gap` |
| H07 | always | `descriptive_only` |
| H08 | early-to-late sign reversal in `>=2/3` seeds | `descriptive_only`, pattern present |
| H08 | otherwise | `descriptive_only`, pattern absent |

H04 的 `median rho64-ref256` 按 draw identity/fold 分开报告；strong level 要求 `SEALED_V4_R2`、D0、D4 在
validation_late 都满足，任一不满足只能 `mechanism_consistent`。H08 是未隔离的 ex-post adaptation morphology，
不允许使用 mechanism-level 语言，也不允许新的 checkpoint rule。

---

## 9. Gate order、terminal states 与授权边界

### 9.1 Gate order

```text
execution_authorization_gate
upstream_hash_and_file_set_gate
upstream_21c_terminal_state_gate
input_panel_integrity_gate
retained_universe_exact_match_gate
hypothesis_preseal_gate
historical_holdout_zero_access_gate
sealed_checkpoint_replay_gate
zero_solution_recompute_gate
inference_draw_schedule_gate
inference_sampling_audit_gate
arm_registry_exact_gate
return_path_transform_firewall_gate
gradient_calibration_train_only_gate
architecture_shape_gate
teacher_isolation_gate
seed_determinism_gate
resource_probe_gate
training_completion_gate
exact_retrain_control_gate
pre_late_bundle_hash_gate
fresh_late_readout_gate
score_coverage_gate
metric_implementation_gate
hypothesis_falsification_gate
repair_candidate_gate
finalize_transaction_gate
output_manifest_hash_gate
failure_bundle_integrity_gate
```

`repair_candidate_gate` 的 status 只能是 `research_candidate_pass|research_candidate_fail`；两者都算 engineering pass，
不触发 first failing gate。`research_candidate_fail` 是研究结果，不是工程完整性失败。其他 gate 不得使用这两个
status。
发生 first failure 后，中间 domain gates 按 `not_run_due_to_prior_gate:<gate_id>` 记录，但独立 terminalizer 仍必须写出对应
blocked profile，然后执行 `failure_bundle_integrity_gate`。P5 只表示 primary finalize/output-manifest path 失败但 fallback
terminalizer 成功。若 `failure_bundle_integrity_gate` 本身 fail，禁止提交 canonical root，只保留 sibling `.building`
作为非密封工程现场，runner non-zero exit；此情形不得声称任何 terminal state/profile 已完成。

### 9.2 Mutually exclusive terminal states

优先顺序：

```text
1  21D_gap_execution_not_authorized
2  21D_gap_upstream_or_input_blocked
3  21D_gap_inference_diagnostic_blocked
4  21D_gap_training_or_replay_blocked
5  21D_gap_late_readout_blocked
6  21D_gap_finalize_blocked
7  21D_gap_mechanisms_not_supported
8  21D_gap_mechanisms_mixed_no_repair_candidate
9  21D_gap_repair_observed_but_baselines_not_beaten
10 21D_gap_repair_candidate_ready_for_forward_seal_review
```

Terminal state 与 artifact profile exact 映射：`1->P0`、`2->P1`、`3->P2`、`4->P3`、`5->P4`、`6->P5`、
`7..10->P6`。Terminal state 10 只允许生成新的 forward requirement 草案；
`next_requirement_execution_authorized=false`。

Engineering gates 全部通过后，7..10 按以下 first-match 决定：

```text
if repair_candidate_gate == research_candidate_pass:
    state = 10
elif C04E material_improvement
     AND D4@64 late ensemble RankIC > 0
     AND all repair-candidate conjuncts except C08/C09 are true
     AND (C08 mean_rankic_delta <= 0 OR C09 mean_rankic_delta <= 0):
    state = 9
elif H01..H05 support_level all equal not_supported
     AND C01|C02|C03|C04A|C04D|C04E material_improvement all false:
    state = 7
else:
    state = 8
```

任一 material-improvement 字段 null 时，state 7 的 `all false` 不成立，因此进入 state 8；不得把 `not_evaluable`
当作机制反证。

### 9.3 明确禁止

本 requirement 不授权：

```text
historical_design_holdout access
2024-2026 outcome-driven model selection
paper exact replication claim
paper result reproduced claim
best-seed reporting as primary
post-late hyperparameter search
Top30 executable replay
portfolio optimization
policy training
deployment
rolling retrain
forward outcome access before final candidate seal
```

---

## 10. 输出契约

### 10.1 Required final artifacts

```text
21D_reaka_replication_gap_causal_diagnostic_report.md
21D_reaka_replication_gap_causal_diagnostic_decision.csv
hypothesis_registry.csv
causal_hypothesis_readout.csv
gate_evidence_21d_gap.csv
stage_status_registry.csv
artifact_profile_registry.csv
historical_design_holdout_access_audit.csv
preflight/execution_authorization_audit.csv
preflight/upstream_pin_and_file_set_audit.csv
preflight/retained_universe_exact_match_audit.csv
preflight/resolved_config.yaml
preflight/replay_runtime_fingerprint.json
diagnostics/return_path_transform_audit.parquet
diagnostics/raw_return_zero_solution_audit.csv
diagnostics/checkpoint_parameter_collapse_audit.csv
diagnostics/gradient_calibration_batch_registry.parquet
diagnostics/loss_gradient_scale_audit.parquet
diagnostics/selector_semantics_score_comparison.parquet
diagnostics/selector_semantics_audit.csv
diagnostics/operator_usage_and_stability_audit.csv
diagnostics/inference_draw_convergence_summary.csv
diagnostics/checkpoint_surgery_score_comparison.parquet
training/model_search_accounting_manifest.csv
training/resource_probe_audit.csv
training/training_run_registry.csv
training/seed_level_training_curves.csv
training/gradient_calibration_weights.csv
training/checkpoint_manifest.json
training/checkpoint_eligibility_manifest.json
training/pre_late_checkpoint_bundle_manifest.json
training/selection_worker_exit_record.json
training/late_readout_worker_exit_record.json
predictions/validation_early_prediction_scores.parquet
predictions/validation_late_prediction_scores.parquet
daily_rankic_readout.csv
monthly_lomo_stability.csv
cross_seed_morphology.csv
paired_rankic_comparison.csv
stationary_bootstrap_pair_diagnostic.csv
semantic_reproducibility_manifest.json
manifest_21d_reaka_replication_gap_causal_diagnostic.json
output_hashes_21d_reaka_replication_gap_causal_diagnostic.json
```

上述清单是 `P6_FULL_DIAGNOSTIC_FINALIZED` 的 non-sharded paths。另有两类 exact expansion：

```text
checkpoint paths =
  training/checkpoints/<arm_id>/seed_<model_seed>/state_dict.pt
  where arm_id in exact ordered D0..D6 arm list
    and model_seed in 20260713|20260714|20260715
  exact path n = 21

draw paths =
  diagnostics/inference_draw_scores/<draw_identity>/<fold>/seed_<model_seed>.parquet
  where draw_identity in SEALED_V4_R2|D0_R2_RAW_EXACT_REPLAY|D4_R2_REPAIR_COMBINED_V1
    and fold in validation_early|validation_late
    and model_seed in 20260713|20260714|20260715
  exact path n = 18
```

`<...>` 仅表示上述有限笛卡尔展开，不是 glob。实现必须在 resolved config 中写出 21+18 个完整路径，
禁止 `latest`、目录发现或 glob。
Temporary writes 只允许在 sibling `outputs/21D_reaka_replication_gap_causal_diagnostic_v2.building/`；canonical root 不存在时
才能用单次 atomic rename 提交。无论 success/blocked，canonical root 内禁止 `.building|tmp|partial`额外路径；
已存在 canonical root 时禁止覆盖、append 或 merge。

以下 failure evidence 只能在对应 blocked profile 出现，P6 全部 forbidden：

```text
preflight/preflight_failure_evidence.csv
diagnostics/inference_diagnostic_failure_evidence.csv
training/training_failure_evidence.csv
training/late_readout_failure_evidence.csv
finalize_failure_evidence.csv
```

### 10.2 Canonical serialization

全部最终 artifact 必须满足：

```text
CSV      = UTF-8, LF, exact header order, no index, RFC4180 quoting, float %.17g
Parquet  = pyarrow logical schema below, zstd level 9, use_dictionary=false
JSON     = UTF-8, sort_keys=true, separators=(",",":"), allow_nan=false, trailing LF
YAML     = UTF-8, LF, safe types only, top-level key order follows schema below
date     = YYYY-MM-DD
datetime = UTC ISO-8601 with Z
boolean  = lowercase true|false
```

CSV/JSON 中禁止 `NaN|Inf|-Inf`。只有下面显式标注 `nullable` 的字段可为 CSV empty/Arrow null/JSON null。
`*_paths_json`、`*_json` CSV 字段必须是 canonical compact JSON。Parquet metadata exact 包含
`schema_version,row_count,sort_key,semantic_content_sha256`；semantic hash 对按 sort key 排序后的 logical values 计算，不包含
Parquet writer metadata。
所有 sort key 都是逐列 ascending，string 按 UTF-8 bytewise，nulls last；未显式列入 sort key 的列不得作为隐式
tie-breaker。Unique-key duplicate 一律 fail closed，不得 keep-first/last。

### 10.3 Exact logical schemas

下文 `string{a|b}` 是闭集 enum；`json` 是 canonical compact JSON string；未标 `nullable` 的字段不得为空。

#### 10.3.1 Terminal、registry 与 preflight CSV

```text
S_DECISION_V2
run_id:string,requirement_version:string,artifact_profile_id:string,
terminal_state:string,evidence_role:string,first_failure_gate:string(nullable),
mechanism_summary_status:string,repair_candidate_status:string,
next_requirement_execution_authorized:bool,decision_reason:string
row_n=1; sort=run_id

S_HYPOTHESIS_REGISTRY_V2
hypothesis_order:int16,hypothesis_id:string,prior_strength:string,
status_at_requirement_time:string,direct_evidence_rule:string,
intervention_rule:string,falsifier_rule:string,allowed_statement:string,
forbidden_statement:string,registered_before_any_new_score:bool,
registry_row_sha256:string
row_n=8; sort=hypothesis_order

S_HYPOTHESIS_READOUT_V2
hypothesis_order:int16,hypothesis_id:string,prior_strength:string,
direct_observation_status:string,single_factor_intervention_status:string,
falsifier_status:string,support_level:string{not_evaluable|not_supported|mixed|mechanism_consistent|strongly_mechanism_consistent|unresolved_external_implementation_gap|descriptive_only},
decision_metrics_json:json,supporting_artifact_paths_json:json,
contradicting_artifact_paths_json:json,allowed_statement:string,
forbidden_statement:string
row_n=8; sort=hypothesis_order

S_GATE_EVIDENCE_V2
gate_order:int16,gate_id:string,stage_id:string,
status:string,check_n:int32,pass_n:int32,fail_n:int32,
evidence_paths_json:json,first_failure_reason:string(nullable)
row_n=29; sort=gate_order
status in pass|fail|research_candidate_pass|research_candidate_fail|not_run_due_to_prior_gate:<gate_id>;
research statuses only permitted for repair_candidate_gate and do not define first failure

S_STAGE_STATUS_V2
stage_order:int16,stage_id:string,status:string,
started_at_utc:string(nullable),ended_at_utc:string(nullable),
first_failure_gate:string(nullable),worker_exit_code:int32(nullable),
artifact_group_id:string
row_n=6; sort=stage_order
stage_id in E0_PREAUTH_AND_PREFLIGHT|E1_SEALED_CHECKPOINT_INFERENCE|
E2_TRAINING_AND_EARLY_SELECTION|E3_PRE_LATE_SEAL|E4_FRESH_LATE_READOUT|E5_FINALIZE

S_ARTIFACT_PROFILE_V2
profile_order:int16,profile_id:string,required_paths_json:json,
forbidden_paths_json:json,conditional_row_scope_json:json,
registry_contract_sha256:string
row_n=7; sort=profile_order

S_ACCESS_AUDIT_V2
process_order:int16,process_role:string,access_scope:string,
open_attempt_n:int64,successful_open_n:int64,read_row_n:int64,
forbidden_open_attempt_n:int64,first_forbidden_path:string(nullable),status:string
sort=process_order,access_scope

S_AUTHORIZATION_AUDIT_V2
authorization_path:string,exists:bool,authorization_sha256:string(nullable),
requirement_sha256_match:bool,config_sha256_match:bool,runner_sha256_match:bool,
test_sha256_match:bool,upstream_pin_match:bool,replay_profile_match:bool,
dependency_lock_match:bool,device_fingerprint_match:bool,status:string,reason:string(nullable)
row_n=1

S_PIN_AUDIT_V2
pin_order:int16,pin_id:string,path:string,expected_sha256:string,
observed_sha256:string(nullable),expected_size_bytes:int64(nullable),
observed_size_bytes:int64(nullable),file_set_status:string,hash_status:string,
overall_status:string,reason:string(nullable)
sort=pin_order

S_RETAINED_UNIVERSE_V2
fold_order:int8,fold:string,decision_date:date32(nullable),
expected_row_n:int64,observed_row_n:int64,expected_row_key_sha256:string,
observed_row_key_sha256:string(nullable),denominator_exact_match:bool,status:string,
reason:string(nullable)
sort=fold_order,decision_date; rows=three fold summaries plus one row per retained date; row_n=1055

S_FAILURE_EVIDENCE_V2
failure_order:int16,stage_id:string,gate_id:string,failure_code:string,
failure_reason:string,evidence_paths_json:json,worker_exit_code:int32(nullable),
created_at_utc:string
sort=failure_order
```

File-to-schema mapping exact：

| File | Schema |
|---|---|
| `21D_reaka_replication_gap_causal_diagnostic_decision.csv` | `S_DECISION_V2` |
| `hypothesis_registry.csv` | `S_HYPOTHESIS_REGISTRY_V2` |
| `causal_hypothesis_readout.csv` | `S_HYPOTHESIS_READOUT_V2` |
| `gate_evidence_21d_gap.csv` | `S_GATE_EVIDENCE_V2` |
| `stage_status_registry.csv` | `S_STAGE_STATUS_V2` |
| `artifact_profile_registry.csv` | `S_ARTIFACT_PROFILE_V2` |
| `historical_design_holdout_access_audit.csv` | `S_ACCESS_AUDIT_V2` |
| `preflight/execution_authorization_audit.csv` | `S_AUTHORIZATION_AUDIT_V2` |
| `preflight/upstream_pin_and_file_set_audit.csv` | `S_PIN_AUDIT_V2` |
| `preflight/retained_universe_exact_match_audit.csv` | `S_RETAINED_UNIVERSE_V2` |
| 五个 `*failure_evidence.csv` | `S_FAILURE_EVIDENCE_V2` |

#### 10.3.2 Diagnostic schemas

```text
S_RETURN_PATH_TRANSFORM_V2 (Parquet)
fold_order:int8,fold:string,decision_date:date32,position:int8,
position_role:string{source|train_forecast_target},row_n:int32,
raw_mean:float64,raw_std_ddof1:float64,transformed_mean:float64,
transformed_std_ddof1:float64,raw_row_key_sha256:string,
transformed_value_semantic_sha256:string,status:string
sort=fold_order,decision_date,position
P4 row_n=842*11+107*10=10332
P5/P6 row_n=10332+103*10=11362

S_ZERO_SOLUTION_V2 (CSV)
arm_order:int8,arm_id:string,model_seed:int64,epoch:int16,audit_role:string,
sample_row_n:int64,zero_output_L_source_rec:float64,
zero_output_L_shifted_observed_rec:float64,zero_output_L_forecast:float64,
zero_output_L_rec:float64,actual_L_rec:float64,
zero_solution_improvement:float64,audit_sample_row_key_sha256:string
sort=arm_order,model_seed,epoch,audit_role

S_CHECKPOINT_COLLAPSE_V2 (CSV)
arm_order:int8,arm_id:string,model_seed:int64,fold:string,
selected_epoch:int16,initialization_decoder_weight_l2:float64,
decoder_weight_l2:float64,decoder_norm_ratio:float64(nullable),decoder_bias_abs:float64,
latent_variance_q00:float64,latent_variance_q25:float64,
latent_variance_q50:float64,latent_variance_q75:float64,latent_variance_q100:float64,
latent_covariance_effective_rank:float64,latent_effective_rank_ratio:float64(nullable),
decoded_source_std:float64,raw_source_std:float64,decoded_source_std_ratio:float64(nullable),
forecast_score_std:float64,raw_label_std:float64,score_to_label_std_ratio:float64(nullable),
additional_collapse_flag_n:int8(nullable),h01_direct_morphology_support:bool(nullable),
checkpoint_semantic_sha256:string,audit_sample_row_key_sha256:string,status:string
sort=arm_order,model_seed,fold

S_GRAD_BATCH_REGISTRY_V2 (Parquet)
arm_order:int8,arm_id:string,model_seed:int64,temporal_stratum:int8,
batch_index:int16,row_n:int32,min_decision_date:date32,max_decision_date:date32,
row_key_sha256:string,sampling_contract_sha256:string
sort=arm_order,model_seed,temporal_stratum,batch_index
identities exact=SEALED_V4_R2|D0|D2|D4; exact 32 rows per identity/seed; total row_n=384

S_LOSS_GRADIENT_V2 (Parquet)
arm_order:int8,arm_id:string,model_seed:int64,phase:string{audit|calibration},
temporal_stratum:int8,batch_index:int16,loss_term:string{rec|koop|diff},
module_id:string{global|encoder|gate|selector|koopman_codebook|decoder|residual_corrector},
loss_value:float64,gradient_l2:float64,gradient_share:float64,
cosine_rec_koop:float64(nullable),cosine_rec_diff:float64(nullable),
cosine_koop_diff:float64(nullable),gradient_clip_applied:bool,
optimizer_step_applied:bool,ordered_parameter_name_list_sha256:string,
row_key_sha256:string
sort=arm_order,model_seed,phase,temporal_stratum,batch_index,loss_term,module_id
row_n=(SEALED audit 1 + D0 audit 1 + D2 calibration/audit 2 + D4 calibration/audit 2)
      * 3 seeds * 32 batches * 3 loss terms * 7 module_id values = 12096

S_SELECTOR_SCORE_V2 (Parquet)
fold_order:int8,fold:string,model_seed:int64,decision_date:date32,
instrument:string,row_key:string,hard_score:float32,
deterministic_soft_mixture_score:float32,score_delta:float32,
raw_label:float32,shared_noise_schedule_sha256:string
sort=fold_order,model_seed,decision_date,instrument

S_SELECTOR_AUDIT_V2 (CSV)
fold_order:int8,fold:string,model_seed:int64,decision_date:date32,
row_n:int32,daily_spearman:float64(nullable),top30_overlap:int16,
mean_abs_score_delta:float64,selector_entropy_mean:float64,
effective_operator_count_mean:float64,switching_rate:float64,status:string
sort=fold_order,model_seed,decision_date

S_OPERATOR_AUDIT_V2 (CSV, long form)
arm_order:int8,arm_id:string,model_seed:int64,fold:string,
aggregation_key:string,metric_id:string,operator_i:int8(nullable),
operator_j:int8(nullable),alignment_permutation_json:json(nullable),
metric_value:float64(nullable),observation_n:int64,status:string
sort=arm_order,model_seed,fold,aggregation_key,metric_id,operator_i,operator_j
metric_id in selection_share|selector_entropy|effective_operator_count|switching_rate|
transition_share|cross_seed_assignment_agreement_raw|cross_seed_assignment_agreement_aligned|
k_frobenius_distance|spectral_radius

S_DRAW_SHARD_V2 (Parquet)
fold_order:int8,fold:string,draw_identity:string,model_seed:int64,
decision_date:date32,instrument:string,row_key:string,
draw_scores:fixed_size_list<float32>[256],draw_schedule_sha256:string
sort=fold_order,decision_date,instrument
row_n exact=51932 for validation_early; 50167 for validation_late

S_DRAW_SUMMARY_V2 (CSV)
draw_identity:string,model_seed:int64,fold:string,summary_scope:string,
decision_date:date32(nullable),block_id:int8(nullable),row_n:int32,
spearman_block8_ref256:float64(nullable),top30_overlap_block8_ref256:int16(nullable),
spearman_prefix8_ref256:float64(nullable),spearman_prefix64_ref256:float64(nullable),
mc_noise_var_of_mean8:float64(nullable),cross_section_signal_var:float64(nullable),
mc_noise_fraction:float64(nullable),status:string
sort=draw_identity,model_seed,fold,summary_scope,decision_date,block_id

S_SURGERY_SCORE_V2 (Parquet)
fold_order:int8,fold:string,model_seed:int64,decision_date:date32,
instrument:string,row_key:string,joint_r2_score:float32,
koopman_only_score:float32,score_delta:float32,raw_label:float32,
checkpoint_semantic_sha256:string
sort=fold_order,model_seed,decision_date,instrument
```

Diagnostic file mapping exact：

| File | Schema |
|---|---|
| `diagnostics/return_path_transform_audit.parquet` | `S_RETURN_PATH_TRANSFORM_V2` |
| `diagnostics/raw_return_zero_solution_audit.csv` | `S_ZERO_SOLUTION_V2` |
| `diagnostics/checkpoint_parameter_collapse_audit.csv` | `S_CHECKPOINT_COLLAPSE_V2` |
| `diagnostics/gradient_calibration_batch_registry.parquet` | `S_GRAD_BATCH_REGISTRY_V2` |
| `diagnostics/loss_gradient_scale_audit.parquet` | `S_LOSS_GRADIENT_V2` |
| `diagnostics/selector_semantics_score_comparison.parquet` | `S_SELECTOR_SCORE_V2` |
| `diagnostics/selector_semantics_audit.csv` | `S_SELECTOR_AUDIT_V2` |
| `diagnostics/operator_usage_and_stability_audit.csv` | `S_OPERATOR_AUDIT_V2` |
| 18 draw shard Parquet files | `S_DRAW_SHARD_V2` |
| `diagnostics/inference_draw_convergence_summary.csv` | `S_DRAW_SUMMARY_V2` |
| `diagnostics/checkpoint_surgery_score_comparison.parquet` | `S_SURGERY_SCORE_V2` |

#### 10.3.3 Training、prediction 与 metric schemas

```text
S_SEARCH_ACCOUNTING_V2 (CSV)
arm_order:int8,arm_id:string,model_seed:int64,config_id:string,
planned:bool,primary_or_sensitivity:string{primary},attempt_n:int8,
selected_batch_size:int32,job_status:string,checkpoint_produced:bool,
failure_reason:string(nullable)
row_n=21; sort=arm_order,model_seed
job_status in planned|complete|failed|not_run_due_to_prior_gate:<gate_id>

S_RESOURCE_PROBE_V2 (CSV)
probe_order:int8,probe_id:string,arm_id:string,batch_size:int32,
device_fingerprint_sha256:string,forward_pass:bool,backward_pass:bool,
optimizer_state_step_pass:bool,inference_64draw_pass:bool,
draw_shard_write_pass:bool,oom_observed:bool,peak_reserved_memory_bytes:int64,
estimated_gpu_wall_seconds:int64,estimated_output_bytes:int64,
free_disk_bytes:int64,status:string,reason:string(nullable)
sort=probe_order

S_TRAINING_RUN_V2 (CSV)
arm_order:int8,arm_id:string,model_seed:int64,config_sha256:string,
train_row_n:int64,validation_early_row_n:int64,selected_batch_size:int32,
started_at_utc:string,ended_at_utc:string,final_evaluated_epoch:int16,
selected_epoch:int16,selection_metric:float64,selection_status:string,
checkpoint_path:string,checkpoint_sha256:string,
model_state_semantic_sha256:string,parameter_count:int64,
initialization_contract_sha256:string,ordered_parameter_name_list_sha256:string,
actual_optimizer_step_n:int64,peak_cpu_rss_mib:float64,
peak_gpu_memory_mib:float64,training_wall_seconds:float64,
run_status:string,failure_reason:string(nullable)
row_n=21; sort=arm_order,model_seed

S_TRAINING_CURVE_V2 (CSV, long form)
arm_order:int8,arm_id:string,model_seed:int64,epoch:int16,
split_role:string{train|validation_early},metric_id:string,
metric_value:float64,observation_n:int64,optimizer_step_n:int64,
tau:float64,checkpoint_selected:bool
sort=arm_order,model_seed,epoch,split_role,metric_id

S_GRADIENT_WEIGHT_V2 (CSV)
arm_order:int8,arm_id:string,model_seed:int64,loss_term:string,
median_gradient_l2:float64,inverse_gradient_raw:float64,
weight_before_clip:float64,clip_applied:bool,weight_after_clip:float64,
final_normalized_weight:float64,batch_registry_sha256:string
sort=arm_order,model_seed,loss_term
arm_id exact=D2_R2_GRADBAL_ONLY|D4_R2_REPAIR_COMBINED_V1; row_n=18

S_PREDICTION_V2 (Parquet)
fold_order:int8,fold:string,arm_order:int8,arm_id:string,
model_seed:int64(nullable),is_ensemble:bool,score_variant:string{primary|prefix8|prefix64|ref256},
draw_n:int16,decision_date:date32,instrument:string,row_key:string,
score:float32,raw_label:float32,checkpoint_semantic_sha256:string(nullable)
sort=fold_order,arm_order,is_ensemble,model_seed,score_variant,decision_date,instrument
one complete retained row set per declared arm/seed-or-ensemble/score_variant; no partial day

S_DAILY_RANKIC_V2 (CSV, long form)
fold_order:int8,fold:string,arm_order:int8,arm_id:string,
model_seed:int64(nullable),is_ensemble:bool,score_variant:string,
aggregation_role:string{day|fold_summary},decision_date:date32(nullable),
metric_id:string{rankic|mean_rankic|rankic_std_ddof1|rankicir|positive_day_rate},
metric_value:float64(nullable),row_n:int32,status:string
sort=fold_order,arm_order,is_ensemble,model_seed,score_variant,aggregation_role,decision_date,metric_id
day rows only permit metric_id=rankic and non-null decision_date;
fold_summary rows require null decision_date and the four non-rankic metric ids
P6 row_n=52*(107+103)+52*2*4=11336

S_MONTHLY_LOMO_V2 (CSV)
fold:string,arm_order:int8,arm_id:string,model_seed:int64(nullable),
is_ensemble:bool,score_variant:string,aggregation_role:string{month|leave_one_month_out},
month:string,row_n:int64,day_n:int32,mean_rankic:float64(nullable),status:string
sort=fold,arm_order,is_ensemble,model_seed,score_variant,aggregation_role,month
months per fold=6; row_n=52 series*2 folds*6 months*2 aggregation roles=1248

S_CROSS_SEED_V2 (CSV, long form)
fold:string,arm_order:int8,arm_id:string,score_variant:string,
aggregation_role:string{seed_pair|seed|ensemble},seed_a:int64(nullable),
seed_b:int64(nullable),decision_date:date32,
metric_id:string{daily_score_spearman|top30_overlap|adjacent_day_top30_turnover|score_autocorrelation},
metric_value:float64(nullable),row_n:int32,status:string
sort=fold,arm_order,score_variant,aggregation_role,seed_a,seed_b,decision_date,metric_id
seed_pair only permits daily_score_spearman|top30_overlap;
seed|ensemble only permits adjacent_day_top30_turnover|score_autocorrelation
for turnover/autocorrelation decision_date is the later date of the adjacent pair;
arm-score-variant combination n=13;
row_n=13*((6*107+8*106)+(6*103+8*102))=38012

S_PAIRED_COMPARISON_V2 (CSV)
contrast_order:int8,contrast_id:string,family_id:string,fold:string,
left_arm_id:string,left_score_variant:string,right_arm_id:string,
right_score_variant:string,paired_day_n:int32,mean_rankic_delta:float64(nullable),
median_rankic_delta:float64(nullable),positive_seed_n:int8(nullable),raw_p_value:float64(nullable),
holm_p_value:float64(nullable),material_improvement:bool(nullable),status:string
sort=contrast_order,fold
contrast_n=13; folds=2; row_n=26

S_BOOTSTRAP_V2 (CSV)
contrast_order:int8,contrast_id:string,fold:string,replicate_n:int32,
mean_block_length:int16,bootstrap_seed:int64,observed_mean_delta:float64(nullable),
ci_lower_025:float64(nullable),ci_upper_975:float64(nullable),p_value_two_sided:float64(nullable),
day_key_sha256:string,status:string
sort=contrast_order,fold
contrast_n=13; folds=2; row_n=26
```

对上述带 `status` 的 metric schema，nullable metric 只能在 `status != pass` 时为 null；`status=pass` 时必须 finite
non-null。当 `status!=pass` 时，所有依赖该 undefined metric 的派生字段必须同时 null，不得填0。

Prediction series 闭集 exact：

```text
D1|D2|D3|D5|D6: primary x (3 seeds + 1 equal-weight ensemble) = 20 series
D0: prefix8|prefix64|ref256 x (3 seeds + 1 equal-weight ensemble) = 12 series
D4: prefix8|prefix64|ref256 x (3 seeds + 1 equal-weight ensemble) = 12 series
M1|M3 pinned comparators: primary x (3 seeds + 1 equal-weight ensemble) = 8 series
total series per fold = 52
validation_early prediction row_n = 52 * 51932 = 2700464
validation_late prediction row_n  = 52 * 50167 = 2608684
```

`D0 primary` 是 `prefix8` 的 config alias，`D4 primary` 是 `prefix64` 的 config alias，不额外写重复 `primary` rows。
M1/M3 rows 必须按 Section 7.4 从 pinned 21B v6 row-level scores 过滤，并与 v4 metric exact-match。Ensemble score 是三个
seed score 的 row-wise 算术平均，不是 rank 的平均。

Metric file mapping：

| File | Schema |
|---|---|
| `training/model_search_accounting_manifest.csv` | `S_SEARCH_ACCOUNTING_V2` |
| `training/resource_probe_audit.csv` | `S_RESOURCE_PROBE_V2` |
| `training/training_run_registry.csv` | `S_TRAINING_RUN_V2` |
| `training/seed_level_training_curves.csv` | `S_TRAINING_CURVE_V2` |
| `training/gradient_calibration_weights.csv` | `S_GRADIENT_WEIGHT_V2` |
| `predictions/validation_early_prediction_scores.parquet` | `S_PREDICTION_V2` |
| `predictions/validation_late_prediction_scores.parquet` | `S_PREDICTION_V2` |
| `daily_rankic_readout.csv` | `S_DAILY_RANKIC_V2` |
| `monthly_lomo_stability.csv` | `S_MONTHLY_LOMO_V2` |
| `cross_seed_morphology.csv` | `S_CROSS_SEED_V2` |
| `paired_rankic_comparison.csv` | `S_PAIRED_COMPARISON_V2` |
| `stationary_bootstrap_pair_diagnostic.csv` | `S_BOOTSTRAP_V2` |

#### 10.3.4 JSON/YAML contracts

`preflight/resolved_config.yaml` top-level keys exact：

```text
schema_version,run_id,requirement_version,paths,authorization,upstream_pins,
replay_identity,splits,retained_rows,return_path_transform,hypotheses,arms,
training,gradient_calibration,inference_draws,metrics,resources,gates,
artifact_universe
```

`arms` exact 7 entries，`gates` exact Section 9 order，`artifact_universe` 必须写出全部 non-sharded paths、21 checkpoint
paths、18 draw paths 和 5 conditional failure paths。禁止 unknown top-level key。

`preflight/replay_runtime_fingerprint.json` keys exact：

```text
schema_version,python_version,pytorch_version,numpy_version,cuda_runtime_version,
cudnn_version,device_name,device_capability,device_total_memory_bytes,
device_fingerprint_sha256,v4_device_fingerprint_sha256,
dependency_lock_path,dependency_lock_sha256,
deterministic_algorithms,cublas_workspace_config,replay_compatibility_profile,
fingerprint_semantic_sha256
```

21 个 `state_dict.pt` 的 top-level payload exact 为 ordered `parameter_name -> CPU contiguous Tensor` mapping，与 v4 plain
state-dict format 一致；禁止外包 metadata dict、optimizer、scheduler、dataloader、validation score、Python callable 或 arbitrary
pickle object。Key order 必须与该 arm 的 `ordered_parameter_names` exact，arm/seed/epoch/config 元数据只写入 checkpoint
manifest。Semantic hash 按 parameter name UTF-8 bytes、dtype、shape 和 little-endian contiguous tensor bytes 依次更新
SHA256。D0 在 `EXACT_RUNTIME_V1` 中还必须与 Section 1.1 的 v4 checkpoint byte/semantic hashes exact；
compatibility profile 只可放宽 byte hash，不得放宽 semantic hash。

`checkpoint_manifest.json` 与 `checkpoint_eligibility_manifest.json` 共用 entry keys：

```text
arm_order,arm_id,model_seed,checkpoint_path,checkpoint_sha256,
model_state_semantic_sha256,selected_epoch,selection_metric,
ordered_parameter_name_list_sha256,eligible,eligibility_reason
```

两者 top-level keys exact `schema_version,run_id,requirement_version,entry_n,entries,entries_semantic_sha256`，entries exact 21。
`pre_late_checkpoint_bundle_manifest.json` keys exact：

```text
schema_version,run_id,requirement_sha256,resolved_config_sha256,
hypothesis_registry_sha256,arm_registry_sha256,return_transform_train_early_sha256,
gradient_calibration_sha256,model_search_accounting_sha256,
checkpoint_manifest_sha256,checkpoint_eligibility_manifest_sha256,
early_prediction_semantic_sha256,bundle_semantic_sha256,sealed_at_utc
```

两个 worker exit record keys exact：

```text
schema_version,run_id,process_role,pid,started_at_utc,ended_at_utc,
exit_code,input_paths_json,input_hashes_json,output_paths_json,
forbidden_open_attempt_n,optimizer_object_n,train_loader_object_n,
python_model_object_n,status,reason
```

`semantic_reproducibility_manifest.json` keys exact：

```text
schema_version,run_id,requirement_sha256,resolved_config_sha256,
replay_runtime_fingerprint_sha256,upstream_semantic_hashes,
retained_row_key_hashes,return_transform_semantic_hash,
hypothesis_registry_sha256,arm_registry_sha256,
gradient_calibration_semantic_hash,checkpoint_semantic_hashes,
draw_schedule_semantic_hashes,prediction_semantic_hashes,
metric_semantic_hashes,semantic_payload_bundle_hash
```

P6 中上述所有 scalar hash 必须 non-null，map 必须 non-empty。P0-P5 中，只有由 first failing gate 之后尚未产生的
scalar hash 可 JSON null，对应 map 必须 `{}`；已经产生的 hash 不得为 null。这是 JSON 的唯一 blocked-profile
nullability exception，且必须与 `stage_status_registry.csv` first failure exact 一致。
`schema_version/run_id/requirement_sha256/semantic_payload_bundle_hash` 在所有有效 profile 中始终 non-null。

Final manifest keys exact：

```text
schema_version,run_id,requirement_version,artifact_profile_id,terminal_state,
requirement_sha256,config_sha256,runner_sha256,test_sha256,
authorization_sha256,upstream_pins,replay_identity,
artifact_profile_registry_sha256,semantic_reproducibility_manifest_sha256,
output_hashes_path,output_hashes_excluded_self_path,artifact_n,artifacts,
report_sha256,finalized_at_utc
```

P0 中 authorization 文件不存在时 `authorization_sha256` 可 null；其余 profile 必须 non-null。`upstream_pins`
每个 entry 都必须保留 expected hash，未观测的 observed hash 只能在 P0/P1 为 null。

`artifacts` entry keys exact `path,size_bytes,sha256,schema_version,row_count(nullable),role`，按 path bytewise 升序。
`output_hashes` keys exact `schema_version,run_id,excluded_paths,entries`，entry keys exact `path,size_bytes,sha256`，按 path bytewise
升序。无环 finalization 集合方程 exact 为：

```text
U = active artifact profile required path set
M = manifest_21d_reaka_replication_gap_causal_diagnostic.json
H = output_hashes_21d_reaka_replication_gap_causal_diagnostic.json

manifest.artifacts paths = U - {M,H}
output_hashes.excluded_paths = [H]
output_hashes.entries paths = U - {H}
```

因此 manifest 不存储 M/H 的 byte hash，只存储 `output_hashes_path=H`；output-hashes 在 manifest 完成后生成，包含 M 的
byte hash 但不包含 H 自身。`output_hashes.entries` 中除 M 外的 entries 必须与 `manifest.artifacts` exact 一致。

### 10.4 Artifact profiles

至少定义：

```text
P0_PREAUTHORIZATION_BLOCKED
P1_UPSTREAM_BLOCKED
P2_INFERENCE_DIAGNOSTIC_BLOCKED
P3_TRAINING_BLOCKED
P4_LATE_READOUT_BLOCKED
P5_FINALIZE_BLOCKED
P6_FULL_DIAGNOSTIC_FINALIZED
```

定义 exact path groups：

```text
G_TERMINAL =
  21D_reaka_replication_gap_causal_diagnostic_report.md
  21D_reaka_replication_gap_causal_diagnostic_decision.csv
  gate_evidence_21d_gap.csv
  stage_status_registry.csv
  artifact_profile_registry.csv
  historical_design_holdout_access_audit.csv
  semantic_reproducibility_manifest.json
  manifest_21d_reaka_replication_gap_causal_diagnostic.json
  output_hashes_21d_reaka_replication_gap_causal_diagnostic.json

G_PRE =
  preflight/execution_authorization_audit.csv
  preflight/upstream_pin_and_file_set_audit.csv
  preflight/retained_universe_exact_match_audit.csv
  preflight/resolved_config.yaml

G_HYP_PLAN =
  hypothesis_registry.csv
  training/model_search_accounting_manifest.csv

G_INF =
  preflight/replay_runtime_fingerprint.json
  diagnostics/raw_return_zero_solution_audit.csv
  diagnostics/checkpoint_parameter_collapse_audit.csv
  diagnostics/loss_gradient_scale_audit.parquet
  diagnostics/selector_semantics_score_comparison.parquet
  diagnostics/selector_semantics_audit.csv
  diagnostics/operator_usage_and_stability_audit.csv
  diagnostics/inference_draw_convergence_summary.csv
  diagnostics/checkpoint_surgery_score_comparison.parquet
  six SEALED_V4_R2 draw paths from the exact expansion

G_TRAIN =
  diagnostics/return_path_transform_audit.parquet
  diagnostics/gradient_calibration_batch_registry.parquet
  training/resource_probe_audit.csv
  training/training_run_registry.csv
  training/seed_level_training_curves.csv
  training/gradient_calibration_weights.csv
  training/checkpoint_manifest.json
  training/checkpoint_eligibility_manifest.json
  training/pre_late_checkpoint_bundle_manifest.json
  training/selection_worker_exit_record.json
  predictions/validation_early_prediction_scores.parquet
  all 21 checkpoint paths from the exact expansion
  six validation_early D0/D4 draw paths from the exact expansion

G_LATE =
  training/late_readout_worker_exit_record.json
  predictions/validation_late_prediction_scores.parquet
  daily_rankic_readout.csv
  monthly_lomo_stability.csv
  cross_seed_morphology.csv
  paired_rankic_comparison.csv
  stationary_bootstrap_pair_diagnostic.csv
  causal_hypothesis_readout.csv
  six validation_late D0/D4 draw paths from the exact expansion

F_PRE   = preflight/preflight_failure_evidence.csv
F_INF   = diagnostics/inference_diagnostic_failure_evidence.csv
F_TRAIN = training/training_failure_evidence.csv
F_LATE  = training/late_readout_failure_evidence.csv
F_FINAL = finalize_failure_evidence.csv
```

`diagnostics/raw_return_zero_solution_audit.csv`、`checkpoint_parameter_collapse_audit.csv`、
`loss_gradient_scale_audit.parquet`、`operator_usage_and_stability_audit.csv` 在 `G_INF` 中至少包含
`SEALED_V4_R2` rows；P4/P5/P6 在同一 finalization transaction 中增加已完成 D0-D6 rows。不得在 canonical root
原地 append；必须从 `.building` 生成完整新文件后 atomic replace。

Profile 集合方程 exact：

| Profile | Required | Forbidden |
|---|---|---|
| `P0_PREAUTHORIZATION_BLOCKED` | `G_TERMINAL + execution_authorization_audit + F_PRE` | universe minus required |
| `P1_UPSTREAM_BLOCKED` | `G_TERMINAL + G_PRE + F_PRE` | universe minus required |
| `P2_INFERENCE_DIAGNOSTIC_BLOCKED` | `G_TERMINAL + G_PRE + G_HYP_PLAN + F_INF` | universe minus required |
| `P3_TRAINING_BLOCKED` | `G_TERMINAL + G_PRE + G_HYP_PLAN + G_INF + F_TRAIN` | universe minus required |
| `P4_LATE_READOUT_BLOCKED` | `G_TERMINAL + G_PRE + G_HYP_PLAN + G_INF + G_TRAIN + F_LATE` | universe minus required |
| `P5_FINALIZE_BLOCKED` | `G_TERMINAL + G_PRE + G_HYP_PLAN + G_INF + G_TRAIN + G_LATE + F_FINAL` | universe minus required |
| `P6_FULL_DIAGNOSTIC_FINALIZED` | `G_TERMINAL + G_PRE + G_HYP_PLAN + G_INF + G_TRAIN + G_LATE` | all five failure paths |

`conditional_row_scope_json` exact：

```text
P0|P1|P2 = {}
P3 = {
  "diagnostic_identity_scope":["SEALED_V4_R2"],
  "sealed_fold_scope":["validation_early","validation_late"]
}
P4 = {
  "diagnostic_identity_scope":["SEALED_V4_R2","D0_R2_RAW_EXACT_REPLAY","D1_R2_RETURN_PATH_CSZ_ONLY","D2_R2_GRADBAL_ONLY","D3_R2_ST_HARD_ONLY","D4_R2_REPAIR_COMBINED_V1","D5_K2_RAW_NO_RESIDUAL","D6_R1_RAW_MLP_RESIDUAL"],
  "retrained_fold_scope":["train","validation_early"],
  "return_transform_fold_scope":["train","validation_early"],
  "draw_path_scope":["SEALED_V4_R2:validation_early|validation_late","D0_R2_RAW_EXACT_REPLAY|D4_R2_REPAIR_COMBINED_V1:validation_early"]
}
P5|P6 = {
  "diagnostic_identity_scope":["SEALED_V4_R2","D0_R2_RAW_EXACT_REPLAY","D1_R2_RETURN_PATH_CSZ_ONLY","D2_R2_GRADBAL_ONLY","D3_R2_ST_HARD_ONLY","D4_R2_REPAIR_COMBINED_V1","D5_K2_RAW_NO_RESIDUAL","D6_R1_RAW_MLP_RESIDUAL"],
  "retrained_fold_scope":["train","validation_early","validation_late"],
  "return_transform_fold_scope":["train","validation_early","validation_late"],
  "draw_path_scope":["SEALED_V4_R2|D0_R2_RAW_EXACT_REPLAY|D4_R2_REPAIR_COMBINED_V1:validation_early|validation_late"]
}
```

P0 的 `F_PRE` gate exact 为 `execution_authorization_gate`；P1 的 `F_PRE` 必须记录真实 first failing preflight gate。
P0/P1 中 `G_PRE` 的未运行 audit rows 使用 `not_run_due_to_prior_gate:<gate_id>`，不允许省略文件或伪造 pass。
`artifact_profile_registry.csv` 在实现时必须将上述 group 展开为 full sorted path arrays，不得只写 group name。
下游 `not_run_due_to_prior_gate:<gate_id>` 不得抢在真实 first failing gate之前。

### 10.5 Hash closure

Final manifest必须绑定：

```text
requirement/config/runner/test/authorization hashes
all upstream pins
feature/panel/row-key hashes
hypothesis preseal hash
arm registry hash
gradient calibration hash
checkpoint semantic hashes
prediction semantic hashes
metric table hashes
report hash
all substantive final artifact byte hashes under the explicit M/H acyclic exclusion
```

`output_hashes` 不自我包含；必须按 Section 10.3.4 的集合方程执行，不得在实现时另选 exclusion。

---

## 11. 测试与静态验收

实现前后至少覆盖：

1. Section 1.1 所有上游和 D0 implementation SHA256 exact-match；
2. v4 retained fold row keys与counts exact；
3. 任何 instrument/universe变化 fail closed；
4. zero-output loss fixture与手算一致；
5. raw-return panel path/shape/dtype/hash 与 v4 retained row index exact；
6. CS z-score 按 `(fold,decision_date,position)` 使用完整 retained rows、ddof=1，禁止回读 membership/raw qfq；
7. validation label transform不进入 score或metric denominator；
8. gradient calibration只打开train，四个 temporal strata 各32个batches/8192行 exact；
9. gradient weight公式、clip和renormalization fixture一致；
10. ST-hard forward one-hot、backward gradient finite；
11. D0 original runner/config/test/runtime identity 与 exact replay selected epoch/score/hash gate；
12. draw 0..255 seed与batch/order无关；
13. 32个8-draw blocks exact不重叠；
14. 8/32/64/128/256 prefix mean fixture一致；
15. hard/deterministic-soft-mixture comparison使用相同 residual noise，且不命名为 Gumbel expectation；
16. Koopman-only surgery不修改checkpoint；
17. K2/R1/R2 graph、parameter set与loss exact；
18. 7 arms × 3 seeds = 21 learned jobs exact，无额外job/retry/replacement；
19. selection worker不能 open validation_late 或 E1 late-derived diagnostics；
20. late worker fresh process且不能持有optimizer/train state；
21. historical holdout access counters全0；
22. daily RankIC average-rank tie和minimum N fixture一致；
23. paired bootstrap unit是day而非stock-row；
24. hypothesis support enum和falsifier路径完整；
25. repair candidate gate是conjunctive，禁止partial pass；
26. terminal state first-match唯一；
27. P0-P6 required/forbidden path expansion exact，first failure 不被 downstream `not_run`掩盖；
28. 21 checkpoint paths、18 draw shard paths、每 shard row count与235,236,096 scalar count exact；
29. Section 10 全部 CSV/Parquet/JSON/YAML schema、sort key、nullability和enum exact；
30. resource cap、disk cap、GPU wall cap 和batch=256 no-fallback fixture一致；
31. D0/D4 同 checkpoint 8/64/256 score 与 C04A-C04E contrasts exact；
32. candidate stability denominator exact 309，任一 undefined 必须 not_evaluable；
33. output artifact set exact，无未登记文件；
34. manifest/output-hashes无self-hash cycle；
35. D0-D4 shared initialization/dataloader/Gumbel/diffusion noise byte-equivalent，arm ID 不进入 shared seed preimage；
36. terminal state 1..10 与 profile P0..P6 映射唯一；
37. Markdown fence balance、authorization key唯一、gate order一致。

建议静态验证：

```bash
python -m py_compile experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21d_reaka_replication_gap_causal_diagnostic.py
pytest -q experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21d_reaka_replication_gap_causal_diagnostic.py
ruff check experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/src/run_21d_reaka_replication_gap_causal_diagnostic.py experiments/pending/21_residual_enhanced_koopman_auto_encoder_v0/tests/test_21d_reaka_replication_gap_causal_diagnostic.py
git diff --check
```

---

## 12. 报告必须回答的问题

最终中文报告必须按以下顺序回答，不能只给 pass/fail：

1. 上游失败和本 requirement 的污染边界是什么；
2. zero-output baseline是否几乎解释了 reconstruction loss；
3. latent/decoder/score是否发生可测量收缩；
4. diffusion是数值主导还是梯度主导；
5. hard/soft selector差异是否足以改变排名；
6. 8 draws的排名是否相对256-draw reference收敛；
7. full return-path decision-CS transform 是否改善退化，以及为何不能分开归因 source/target；
8. gradient balancing是否单因素改善；
9. ST-hard是否单因素改善；
10. K2、R1、R2谁首次引入改善或恶化；
11. combined repair是否同时通过seed、month、fold、TopK连续性和本地基线；
12. 每条推测最终是 mechanism-consistent、mixed、not-supported/falsifier-triggered还是 unresolved；
13. 哪些差距仍只能归因于论文未披露实现或时期差异；
14. 是否值得生成21F forward seal requirement。

必须把 ex-post diagnosis 与 ex-ante confirmation 分开。报告结尾固定声明：

```text
本阶段所有2018-2023结果均为设计污染后的机制诊断；任何修复候选只有在最终seal之后的新decision dates上，才能形成可信支持。
```

---

## 13. 当前 requirement decision

```text
requirement_generation_status = complete
requirement_review_status = revised_after_review_pending_human_rereview
implementation_authorized = false
execution_authorized = false
upstream_bundles_mutable = false
historical_holdout_authorized = false
forward_outcome_access_authorized = false
next_action_if_approved = implement config/runner/tests, run static closure review, then request external execution authorization
```
