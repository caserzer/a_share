# Requirement 21F：REAKA 语义修复与排序稳定性验证

> 文档状态：`draft_repaired_pending_human_review`
>
> 生成日期：2026-07-19
>
> Experiment ID：`21_residual_enhanced_koopman_auto_encoder_v0`
>
> Phase ID：`21F_REAKA_SEMANTIC_REPAIR_AND_STABILITY_VALIDATION`
>
> Run ID：`21F_reaka_semantic_repair_and_stability_validation`
>
> Requirement version：`21F_SEMANTIC_REPAIR_v4`
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
Step B  只使用2018–2022 retained train，按 label_source_date purge 后建立2021/2022两个 expanding inner folds；
Step C  训练5个受控 training-semantics arms；T0/T1/T2/T4 epoch 由 Q2 score_mean256_ref 选择，T3 Phase A/Phase B 分别由 Q6/Q2 选择；
Step D  在已冻结 inner checkpoints 上识别 Predictor estimator，先过收敛 gate，再按最差 inner fold 排序；
Step E  用选中的 estimator 选择 training arm，并按内部 epoch 规则在2018–2022 refit 3 seeds；
Step F  所有选择与 checkpoint hash 完成后，fresh worker 首次读取2023 value-bearing panels；
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
  sha256 = 40b468038cef897dd7d2b1f95b1b3c82d1852aed1bf1da8cf08359e0bf4b87fb

panel_manifest:
  path = outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/model_input_panel_manifest.json

label_audit:
  path = outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/decision_universe_and_label_resolution_audit.parquet
  sha256 = 145c03b596cff7980a289fdb29b8f27d89000dbc09e47addf408d8d2e25bee9a

train_value_panel:
  path = outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/panels/train/return_and_label_panel.f32.memmap
  sha256 = a24283e63f2f238bcc270148f98c3648a89cd60169d5e3cf6821f1951fbe38f8

design_early_value_panel:
  path = outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/panels/validation_early/return_and_label_panel.f32.memmap
  sha256 = a6dee1f2293ebe77f23be859e1353bbc38651067801b738365d298933b1a693b

design_late_value_panel:
  path = outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/panels/validation_late/return_and_label_panel.f32.memmap
  sha256 = e1e3b6fb241cdb63f49ea2add7b51b529c02408ac8f8ac5b9c79f7c486289147
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

21F 不重写 21C checkpoint 语义；Q0 exact replay 必须复用其 3 个 sealed checkpoint 和 draw identity（上游 21E 对同一 identity 使用名称 P0）。

21F 新训练的 optimizer、初始化、dataloader、Gumbel clamp 和 CUDA deterministic runtime 必须以以下 exact source 为基底；21F 明示覆盖的字段优先，其余字段不得漂移：

```text
config:
  path   = configs/config_21c_full_reaka_pit_proxy_replication.yaml
  sha256 = 55347efd5aaa4e1132b075fb07e65b46df1e47689dafbb66a724b1ff1d591f7b
runner:
  path   = src/run_21c_full_reaka_pit_proxy_replication.py
  sha256 = fc57a05cb9ed9ef16149000137bef965fd1a768a253b5bd790cf51808d3f36a7
test:
  path   = tests/test_21c_full_reaka_pit_proxy_replication.py
  sha256 = 13a9dafbc0eb70b52115f9761556b86eb34787289c51f8388c025f7428f48699
```

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

以下 row set 从 21B `fold=train` 中删除 exact 396 instruments，再按 `decision_date,instrument` mergesort。hash preimage exact 为排序后 `row_key_hash` 字符串数组的 UTF-8 bytes：

```python
json.dumps(row_key_hash_list, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
```

fit split 必须满足 `max(label_source_date) < selection.date_min`；不得只按 decision date 切分。21B 已确认 `2020-12-31 -> 2021-01-04`、`2021-12-31 -> 2022-01-04`，因此两个年末 decision dates 必须 purge。

| split_id | role | date_min | date_max | max_label_source_date | row_n | complete_day_n | instrument_n | row_key_sha256 |
|---|---|---|---|---|---:|---:|---:|---|
| `I0_FIT_2018_2020_PURGED` | inner fold 0 fit | 2018-01-02 | 2020-12-30 | 2020-12-31 | 173734 | 475 | 662 | `0edb8a86295e9af78ba2b29b50252d7ab79aba1e46a4e20c025d609b0ba5850e` |
| `I0_SELECT_2021` | inner fold 0 selection | 2021-01-04 | 2021-12-31 | 2022-01-04 | 79007 | 186 | 586 | `ffd8ecf9977be0d0b56b6b2972a1890f9c5350fb70dd28f11a5db765d6195ef2` |
| `I1_FIT_2018_2021_PURGED` | inner fold 1 fit | 2018-01-02 | 2021-12-30 | 2021-12-31 | 252710 | 661 | 756 | `33cb139bd7e4ddfe14b25bfc739733cd74b8bc40926d84441633a121dc5f9641` |
| `I1_SELECT_2022` | inner fold 1 selection | 2022-01-04 | 2022-12-14 | 2022-12-15 | 82244 | 180 | 607 | `be1cfdbc9234268450ee528e22d1654469ad4d6282917331fbdf609b1ff654a8` |
| `REFIT_2018_2022` | selected arm refit | 2018-01-02 | 2022-12-14 | 2022-12-15 | 335393 | 842 | 860 | `d1d22a89e6b8096645f1f91b7941f22cd30670aabfbb37d3e388ca324daf6e4e` |

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

在 `preflight/pre_2023_complete.json` 写入之前，任何 training/selection process 对第 2.3 节 restricted value paths 的 open attempt 都必须为 0。2023 worker 必须是 fresh process，且：

```text
optimizer_object_n = 0
autograd_enabled = false
train_loader_object_n = 0
checkpoint_write_n = 0
```

### 2.3 文件级 2023 value firewall

21B 的 `sequence_sample_index.parquet` 是多 fold 共享 metadata container。E0 只允许一个无模型类、无 optimizer、无 metric 计算的 `metadata_splitter` 读取它，并原子写出：

```text
preflight/pre_2023_row_index.parquet
preflight/design_2023_row_index.parquet
preflight/metadata_splitter_exit_record.json
```

`metadata_splitter` 只可投影 `fold,decision_date,instrument,fold_panel_row_idx,x_cache_row_indices,source_dates,row_key_hash`，不得打开任何 return/label panel、prediction、draw shard 或 checkpoint。写出并 hash-register 后进程必须退出。其后所有 training/selection workers 禁止打开共享 `sequence_sample_index.parquet`，只能打开 `pre_2023_row_index.parquet` 与 train value panel。

restricted value paths exact 为：

```text
outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/panels/validation_early/return_and_label_panel.f32.memmap
outputs/21B_alpha158_sequence_baseline_benchmark_v5/materialized/panels/validation_late/return_and_label_panel.f32.memmap
outputs/21C_full_reaka_pit_proxy_replication_v4/predictions/
outputs/21D_reaka_replication_gap_causal_diagnostic_v2/predictions/
outputs/21D_reaka_replication_gap_causal_diagnostic_v2/diagnostics/inference_draw_scores/
outputs/21E_reaka_predictor_drc_implementation_identification_v0/predictions/
```

E0 hash-only integrity worker 可以顺序读取 restricted files 计算 byte SHA256，但不得解析内容，且必须与 training/selection workers 物理分进程、无 IPC payload。访问审计必须区分：

```text
metadata_open_attempt_n
hash_only_byte_read_n
value_parse_open_attempt_n
label_value_materialized_n
score_value_materialized_n
```

worker role allowlist exact 为 `METADATA_SPLITTER,HASH_ONLY_INTEGRITY,EXACT_REPLAY,INNER_TRAIN,SELECTION_COORDINATOR,REFIT,FRESH_2023,FINALIZE,TEST`；access mode allowlist exact 为 `metadata_projection,hash_only,value_parse,checkpoint_read,artifact_write`。每个 process 只能声明一个 worker role，PID/role mapping 在首次 open 前冻结。

在 `preflight/pre_2023_complete.json` 前，training/selection worker 的后三项必须全部为 0。fresh 2023 worker 只允许打开两份 21B design value panels 与 `preflight/design_2023_row_index.parquet`；21C–21E 2023 outputs 只供 E1 exact replay worker 使用，不得进入 estimator、epoch 或 arm selection process。

E1 exact replay worker 必须独立进程运行并在读取 21C–21E outputs 后退出。selection coordinator 只能接收 `replay_id,status,source_sha256,observed_semantic_sha256`，不得接收 replay score、RankIC 或 contrast value。replay acceptance exact：

```text
21C Q0 prediction scores and row order = byte/bitwise equal
21D D4 prefix64 aggregate scores and row order = byte/bitwise equal
21E decision/paired-contrast/gradient-audit source files = registered SHA256 equal
21E registered scalar replay max_abs_error <= 1e-12
```

任何 replay fail 是 technical failure；不得通过重新训练、改变 tolerance 或把 prior 数值输入 selection 来修复。

---

## 3. 预注册因果假设

| order | hypothesis_id | 可证伪陈述 | 主要 intervention | falsifier |
|---:|---|---|---|---|
| 1 | `H21F01_RETURN_SCALE_NECESSARY` | decision-CS z-score 在相同 graph/shared loss weights 下改善两个 inner folds | T1−T0 | `M_H01` 未通过 |
| 2 | `H21F02_GRADIENT_GRAPH_MATERIAL` | stopgrad reconstruction 比 coupled 有稳定增量 | T2−T1 | `M_H02` 未通过 |
| 3 | `H21F03_TWO_STAGE_REPAIR` | modular two-stage 比 joint stopgrad 更稳定 | T3−T2 | `M_H03` 未通过 |
| 4 | `H21F04_DECODER_ROLE_MATERIAL` | decoder topology/training role materially改变排序 | T4−T2 | `M_H04` 未通过 |
| 5 | `H21F05_PREDICTOR_ESTIMATOR_UNSTABLE` | ordinary 64-draw score mean 在 T1 reference checkpoints 上不是稳定 point estimator；Q0 current8 只作上游 replay context | Q1 vs Q2 convergence | `M_H05` 未通过 |
| 6 | `H21F06_DRC_INCREMENTAL_VALUE` | repaired DRC 相对同 backbone Koopman-only 有稳定正增量 | selected DRC−K0 | 2023 late delta <0.005、少于2/3 seeds同向或 morphology失败 |
| 7 | `H21F07_SELECTION_POLICY_DIFFERENCE` | worst-fold + morphology selection 会排除 mean-only 偏好的不稳定 arm | selected vs mean-only shadow selection | `M_H07` 未通过 |
| 8 | `H21F08_AUTHOR_CODE_REMAINS_UNKNOWN` | 无官方代码时仍不能识别作者实现 | 全证据 | 只有外部官方 source 才可解除 |

所有 hypothesis registry rows 必须在任何新训练或新 score 前生成并 hash-register。allowed conclusion exact 为 `design_contaminated_semantic_repair_diagnostic_only`。

materiality/falsifier registry exact：

```text
M_H01:
  C01 ensemble RankIC delta > 0 in both inner folds
  min_fold_delta >= 0.005
  selected-estimator convergence pass in both arms
  morphology_nonworse = true

M_H02:
  C02 ensemble RankIC delta > 0 in both inner folds
  min_fold_delta >= 0.003
  same_direction_seed_n >= 2 of 3 in both folds
  morphology_nonworse = true

M_H03:
  C03 min_fold ensemble RankIC delta >= 0.003
  C03 delta > 0 in both folds
  worst-fold cross-seed Spearman delta >= 0
  worst-fold Top30 overlap delta >= 0
  additional_collapse_flag_n = 0

M_H04:
  min(abs(C04 fold0 ensemble RankIC delta),abs(C04 fold1 ensemble RankIC delta)) >= 0.005
  sign(C04 fold0 delta) = sign(C04 fold1 delta)
  same_direction_seed_n >= 2 of 3 in both folds
  and at least one morphology condition:
    abs(cross-seed Spearman delta) >= 0.05
    abs(Top30 overlap delta) >= 2
    abs(adjacent-day Top30 turnover delta) >= 0.10

M_H05:
  supported iff Q1_SCORE_MEAN64 fails any one of the three convergence conditions
  on at least one of the 6 T1 selection-reference checkpoints
  otherwise unsupported

M_H07:
  selected_arm_id != mean_rankic_only_shadow_arm_id
  selected arm passes all arm eligibility gates
  shadow arm fails at least one morphology gate
```

`morphology_nonworse=true` exact 表示 cross-seed Spearman delta、Top30 overlap delta 均 `>=0`，turnover delta `<=0`，且 additional collapse 不增加。用于 H01/H02 时两个 inner folds 必须分别通过；用于 DRC incremental gate 时只在 DESIGN_LATE_2023 对 selected DRC−K0 计算。未达到 materiality rule 一律读作 hypothesis unsupported，不得用 p-value 单独翻转结论。

`same_direction_seed_n` exact 为 seed-level mean daily RankIC delta 与 ensemble delta 严格同号的 seed 数；delta 等于 0 不计同向。若 ensemble delta 等于 0，则 same_direction_seed_n exact 为 0。

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

evaluation label identity exact 为 21B `Y_rank_primary`：train/design value panel column index 10，`label_value=next_session_qfq_close/decision_date_qfq_close-1`，其 `label_source_date` 来自 pinned label audit。不得替换为 sequence last return、可交易日收益或 CS-normalized label。

每个 date/position 的 `mu,sigma,row_n,row_key_sha256` 必须输出审计。任何 `sigma < 1e-6` 必须以 `sigma_floor_applied=true` 登记，不得静默改公式；此时 `transformed_std_ddof0` 按实际结果记录，不要求等于 1。

### 4.3 Shared train-only calibrated loss weights

为使 T1−T0 与 T2−T1 保持单因素，每个 `(fold_id,model_seed)` 只允许生成一组 shared weights。calibration anchor exact 为 T0 raw return path、coupled graph、共同 initial state；该组 weights 原样供 T0/T1/T2/T4 使用，不得按 arm 重新 calibration。

```text
contract_id = 21F_SHARED_GRAD_CAL_V1
losses = L_rec, L_koop, L_diff
calibration rows = corresponding purged inner fit split only
temporal_strata_n = 4, sorted unique decision dates np.array_split into 4 contiguous strata
rows_per_stratum = 2048
batches_per_stratum = 8
batch_size = 256
batches_per_seed = 32
rows_per_seed = 8192 unique rows
sampling_hash = sha256("21F_SHARED_GRAD_CAL_V1|fold_id|model_seed|decision_date|instrument")
within-stratum order = sampling_hash,decision_date,instrument mergesort; take first 2048
gradient scope = exact ordered list of all trainable parameters
aggregate = per-loss median of 32 global gradient L2 values
inverse weight clip = [0.05,20.0]
renormalize = w_rec+w_koop+w_diff = 3
```

T3 Phase A 使用 `w_rec,w_koop` 后重归一化到 sum=2；Phase B 只有 `L_diff`，其 scalar weight exact 为 1。selection/2023 不得参与 calibration。shared weights、ordered parameter names hash、32 batch row hashes必须在 optimizer 第一步前写入并 hash-freeze。

REFIT 不重新 calibration。对每个 refit model seed，分别取该 seed 在两个 inner folds 的 shared weight arithmetic mean，再统一 renormalize 到 sum=3；这三个 refit weight vectors 必须在任何 refit optimizer step 前写入 `gradient_calibration_audit.parquet`。T3 refit 仍按上述 phase normalization 使用同一 refit vector。

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
precision=fp32
amp=false
optimizer=AdamW
learning_rate=0.001
weight_decay=0.00001
adam_betas=[0.9,0.999]
adam_eps=1e-8
adam_amsgrad=false
adam_foreach=false
adam_fused=false
scheduler=none
model_seeds=[20260713,20260714,20260715]
gradient_clip_global_l2=1.0
gradient_clip_foreach=false
gradient_clip_error_if_nonfinite=true
zero_grad_set_to_none=true
max_epochs=100
early_stopping_patience=10
early_stopping_min_delta=0.0
evaluate_every_epochs=1
train_shuffle_each_epoch=true
dataloader_drop_last=false
dataloader_num_workers=0
dataloader_pin_memory=false
sample_weight=1.0
day_balanced_loss=false
gumbel_tau_start=1.0
gumbel_tau_end=0.1
gumbel_anneal=linear_by_planned_optimizer_step
gumbel_clamp=[1e-10,0.9999999999]
deterministic_algorithms=true
cublas_workspace_config=:4096:8
default joint-arm and T3 Phase-B epoch-selection predictor=Q8 epoch_score_mean8_crn
```

straight-through exact 为 `hard_one_hot - soft.detach() + soft`，其中 `soft=softmax((logits+gumbel)/tau)`；forward 必须是 hard one-hot，backward 只沿 soft branch。`planned_optimizer_steps=max_epochs*ceil(fit_row_n/batch_size)`，即使 early stop 也不得重算 tau denominator。

初始化和 RNG role exact 复用 21C：`numpy/model/dataloader/weight_init/gumbel/diffusion` seed offsets 分别为 `11/23/37/53/71/89`。T0/T1/T2/T3 在相同 `(fold,seed)` 的完整 initial state 必须 byte-identical；T4 与 T2 的共同 parameter-name intersection 必须 byte-identical。初始化必须先按 21C ordered common parameter names，再按 lexicographically sorted T4-only decoder parameter names 使用同一 weight-init generator；该 ordered-name hash 写入 audit。optimizer state 不共享。

不得在 21F 重测 100 diffusion steps 或 ResBlock；21E 已把两者降为低优先级。

| arm_order | arm_id | return path | loss weights | reconstruction→denoiser | training phases | decoder | role |
|---:|---|---|---|---|---|---|---|
| 0 | `T0_RAW_COUPLED_LINEAR` | raw | fold/seed shared-anchor calibrated | coupled | joint | shared linear | scale control and calibration anchor |
| 1 | `T1_CSZ_COUPLED_LINEAR` | decision-CS z-score | exact same values as T0 | coupled | joint | shared linear | return-scale intervention |
| 2 | `T2_CSZ_STOPGRAD_LINEAR` | decision-CS z-score | exact same values as T0 | detached for `L_rec` only | joint | shared linear | primary graph repair |
| 3 | `T3_CSZ_TWO_STAGE_LINEAR` | decision-CS z-score | shared values phase-normalized per §4.3 | no reconstruction path in phase 2 | two-stage | shared linear, frozen phase 2 | modularity repair |
| 4 | `T4_CSZ_STOPGRAD_POINTWISE_MLP` | decision-CS z-score | exact same values as T0 | detached for `L_rec` only | joint | 21E exact pointwise MLP | decoder sensitivity control |

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
  active losses = normalized_shared_w_rec*L_rec + normalized_shared_w_koop*L_koop
  denoiser optimizer_object_n = 0
  denoiser forward_call_n = 0
  reconstruction_latent = Z_teacher_shifted
  epoch selector = Q6_KOOPMAN_ONLY on selection fold

Phase B:
  freeze encoder + selector + Koopman + decoder
  train denoiser only
  active loss = L_diff
  checkpoint writes include phase-A and phase-B semantic hashes
  epoch selector = Q8_EPOCH_SCORE_MEAN8_CRN on selection fold
```

Phase-A loss exact：

```text
Z_source,Z_hat_shifted = source encoder/selector/Koopman forward
Z_teacher_shifted = same encoder on shifted teacher sequence, fully differentiable
decoded_source = decoder(Z_source)
decoded_shifted = decoder(Z_teacher_shifted)
L_rec = 0.5*(MSE(decoded_source,y_source)+MSE(decoded_shifted[:,:9],y_teacher[:,:9]))
        + MSE(decoded_shifted[:,9,0],forecast_y)
L_koop = MSE(Z_teacher_shifted,Z_hat_shifted)
```

Phase A 不构造 diffusion timestep/epsilon/x_s/x0_hat。teacher latent 只在 fit split 训练中使用，属于训练 target；inference 和 selection score 不得直接 decode teacher latent。Phase B 从 selected Phase-A state 恢复，冻结其全部参数，以 `target=stop_gradient(Z_teacher_shifted-Z_hat_shifted)` 训练 denoiser 的 21C exact `L_diff=MSE(epsilon_hat,epsilon)`；Phase B 不计算 L_rec/L_koop gradient。

Phase A 与 Phase B 分别使用 `max_epochs=100,patience=10,first maximum epoch`。Phase B 必须从已选择的 Phase-A checkpoint 开始；不得对 Phase-A epoch 与 Phase-B epoch 做二维事后搜索。Phase B predictor 始终使用 frozen Phase-A decoder。一个 T3 fold/seed 两阶段合计仍计为一个 planned training job，但 registry 必须有两条 phase rows。

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
seed_preimage = f"{run_id}|{model_seed}|{row_key_hash}|{draw_idx}".encode("utf-8")
seed = int.from_bytes(sha256(seed_preimage).digest()[:8],"big",signed=False) % 2**63
generator = torch.Generator(device="cpu").manual_seed(seed)
noise_schedule = torch.randn((20,10,64),dtype=torch.float32,device="cpu",generator=generator)
x_T = noise_schedule[0]
reverse step noise order = noise_schedule[1],...,noise_schedule[19]
one CPU tensor generation followed by one device transfer
draw prefix identity: prefix8 ⊂ prefix32 ⊂ prefix64 ⊂ prefix128 ⊂ ref256
draw reduction = torch.float64 accumulation in ascending draw_idx, divide once, cast score to float32 only at output
```

### 6.1 v2 Epoch selector 计算可行性修复（已被 v3 替代）

21F v1 的首个 formal inner job 在 `Q2_SCORE_MEAN256_REF` epoch readout 中达到 10800 秒 timeout，且未完成任何 checkpoint。失败回溯定位在每个 epoch 对完整 selection fold 重复生成 256 个 row-keyed schedules；不是训练 loss、GPU OOM 或结果阈值失败。由于 v1 没有产生 checkpoint、epoch curve 或模型比较结果，v2 在观察任何研究结果前冻结以下计算可行性修复：

```text
joint arms 与 T3 Phase-B epoch selector = Q1_SCORE_MEAN64
T3 Phase-A epoch selector             = Q6_KOOPMAN_ONLY（保持不变）
Q1 仍使用与 Q2 相同的 row-keyed RNG、DDPM 20 steps、逐 draw decode 与 float64 accumulation
Q1 exact 为 Q2 的前 64 draws，epoch readout 理论成本为 v1 的 1/4
```

Q2 不被删除或降级：所有 selected checkpoints 在 estimator convergence、candidate selection、shadow readout、refit 与 fresh-2023 阶段仍必须完整计算 `Q2_SCORE_MEAN256_REF`。禁止根据 Q1/Q2 的研究结果再次更换 epoch selector。该修复改变 checkpoint-selection estimator，必须使用 v2 requirement/config/runner/test 新 hashes 重新人工授权；v1 授权不得继承。

Estimator convergence 必须按 common-prefix 单 pass 计算：ordinary route 一次升序执行 draws `0..255`，在 draw 64/128/256 截取 float64 accumulator；antithetic route一次执行 128 pairs，在 draw 64/256 截取。缓存 key exact 为 `(fold_id,arm_id,model_seed,antithetic)`，只缓存 CPU float32 score arrays，不缓存或跨 checkpoint 共享 latent/model output。Q1/Q2 及后续 selected-arm readout 必须复用同一 cached ref256，禁止为同一 key 重复生成相同 prefix。单 pass prefix 必须与各 draw_n 独立执行达到 bitwise equality。

### 6.2 v3 Selector-only 8-draw 性能修复（由 v4 原样继承）

v2 formal run 完成 T0 的 3 个 seeds 后，`T1_CSZ_COUPLED_LINEAR/20260713` 仍达到 10800 秒 timeout。失败时没有写出 `inner_training_run_registry.csv`、epoch curve、T1 checkpoint 或任何 RankIC/模型选择结果；可见信息仅为 wall-time 与 3 个 T0 checkpoint 文件存在。v3 对全部 joint arms 与 T3 Phase-B 统一冻结：

```text
epoch selector id       = Q8_EPOCH_SCORE_MEAN8_CRN
draw_n                  = 8
seed preimage           = 21F run_id/model_seed/row_key_hash/draw_idx frozen formula
reverse path            = exact 20-step DDPM
decode/reduction        = per-draw decode, ascending float64 accumulation, divide once, float32 output
noise reuse over epochs = same row/draw CRN，禁止把 epoch 加入 seed
early stopping          = max_epochs=100, patience=10, first maximum，保持不变
```

`Q8_EPOCH_SCORE_MEAN8_CRN` 是 selector-only execution identity，不加入 8 个 Predictor estimator candidates，不参与 estimator convergence、candidate eligibility、研究对比或论文 claim。它与 Q0 的区别是 Q0 属于 21C frozen exact-replay control，而 Q8 使用 21F run-id 的 common schedule。所有 selected checkpoints 后续仍完整执行 Q1/Q2/Q3/Q4 convergence，Q2/ref256 不得省略。epoch readout 理论 draw 成本为 v2 的 `1/8`、v1 的 `1/32`。v2 授权不得继承到 v3。

### 6.3 v4 双 lane 隔离执行合同（当前冻结合同）

v3 formal run 在 E2 启动后由人工暂停，以评估单张 RTX 4070 SUPER 上的两路执行：暂停前单 worker 资源快照约为 GPU memory 2.2 GiB / 12.3 GiB、GPU utilization 42%、RSS 3.8 GiB，主机 available RAM 约 22 GiB。该快照只证明双路具有资源可行性，不构成吞吐保证，也不允许两个 worker 共享写入同一 build root。v4 不改变模型、数据、loss、Q8 selector、seed、epoch、timeout、研究 gate 或最终 artifact profile，只冻结以下 execution-only repair：

```text
maximum concurrent GPU training jobs = 2
lane_n                              = 2
partition                           = inner_fold_order
lane_0                              = I0 的 5 arms × 3 seeds = 15 jobs / 18 phase rows
lane_1                              = I1 的 5 arms × 3 seeds = 15 jobs / 18 phase rows
lane writable root                  = canonical.building/.state/inner_lanes/lane_{0,1}
shared writable files               = 0
coordinator merge order             = global job_order ascending，必须 exact 1..30
```

每个 lane 只能写自己的 checkpoint、epoch curve、calibration、collapse、prediction、access audit、completion marker 和日志。两个 lane 可只读相同 pinned upstream files；禁止直接写 canonical build 的 checkpoint、registry、audit 或 stage marker。coordinator 是唯一允许执行以下动作的进程：

1. 在启动前创建两个空 lane roots，并复制/硬链接只读 `pre_2023_row_index.parquet`；
2. 同时启动 exact 两个 CUDA worker，任一路 nonzero 时终止另一 worker，E2 技术失败且不得合并部分结果；
3. 验证 lane job sets 互斥、并集 exact `1..30`、每 lane 15 checkpoints/18 phase rows/105 calibration rows；
4. 按 global `job_order` 合并，重算 checkpoint byte hash/semantic hash，生成与 v3 相同的最终表结构及 30-checkpoint artifact profile；
5. 合并 lane-local access events 后重新分配单调 `event_order`；合并完成后 lane roots 仍仅位于 `.state`，seal 前随 `.state` 一起删除。

正式双路训练之前必须并发执行两个短资源探针。探针分别实例化 `T1_CSZ_COUPLED_LINEAR` 与 `T4_CSZ_STOPGRAD_POINTWISE_MLP`，打开与正式 worker 相同的 fold/value/feature inputs，并完成至少一个真实 forward/backward/optimizer step。两探针均须在 600 秒内 exit 0、finite loss、无 CUDA OOM；coordinator 必须写出 `training/parallel_resource_probe.json`，记录每路 elapsed、RSS、CUDA peak allocated/reserved、设备总显存及保守峰值显存和。探针失败时禁止启动正式 lane。

两 lane 的 GPU wall time 按 process elapsed 之和计入 144-hour cap，不得用 coordinator elapsed 冒充。并发不放宽单 job timeout；若资源争抢导致任一 job timeout，视为 v4 技术失败，不得改变模型或研究结论。v3 authorization 不得继承到 v4；requirement/config/runner/test hashes 与设备 fingerprint 必须重新人工授权。

common schedule 不含 arm_id/estimator_id，因此相同 `(row_key_hash,model_seed,draw_idx)` 在所有 arms 完全相同。Q0 exact replay 例外：它必须使用 21C frozen run-id/seed preimage，而不是 21F seed preimage；Q0 不进入新 estimator selection。

| order | estimator_id | 定义 | candidate eligible | claim restriction |
|---:|---|---|---|---|
| 0 | `Q0_CURRENT_SCORE_MEAN8` | 前8 draws逐draw decode last score后mean | false | exact replay control |
| 1 | `Q1_SCORE_MEAN64` | 前64 draws逐draw decode last score后mean | true | local point estimator |
| 2 | `Q2_SCORE_MEAN256_REF` | 256 draws逐draw decode last score后mean | true | compute-heavy reference |
| 3 | `Q3_ANTITHETIC_SCORE_MEAN64` | 32个base schedules及其完整负值 `u,-u`，包括 `x_T` 与全部reverse-step noise，逐draw decode后mean | true | variance-reduction candidate |
| 4 | `Q4_DDIM_ETA0_SCORE` | `x_T=noise_schedule(draw_idx=0)[0]`，same beta schedule、DDIM eta=0且不再注入step noise | true | row/seed deterministic candidate, not paper-defined |
| 5 | `Q5_ZERO_NOISE_REVERSE_PROXY` | 21E exact zero-noise proxy | false | 不得称 conditional mean |
| 6 | `Q6_KOOPMAN_ONLY` | 不调用 denoiser，decode Koopman forecast | false | residual-attribution control |
| 7 | `Q7_LATENT_MEAN256_THEN_DECODE` | 先对256 corrected latents取mean，再decode last score | false | shared-linear时必须与Q2通过commutation fixture；非线性decoder上只作敏感性诊断 |

Q4 DDIM update exact，`alpha_bar_0=1`，按 `t=20,...,1`：

```text
epsilon_hat = denoiser(x_t,t,condition)
x0_hat = (x_t-sqrt(1-alpha_bar_t)*epsilon_hat)/sqrt(alpha_bar_t)
x_{t-1} = sqrt(alpha_bar_{t-1})*x0_hat + sqrt(1-alpha_bar_{t-1})*epsilon_hat
```

不得 clip `x0_hat`，不得 subsample timesteps，且 `t=1` 输出 `x_0=x0_hat`。Q5 保持 21E DDPM posterior-mean zero-noise proxy，两者不得合并。

### 6.1 Predictor convergence gates

convergence comparison exact：

```text
Q1: ordinary prefix64 vs ordinary Q2 ref256
Q2: ordinary prefix128 vs ordinary ref256
Q3: antithetic32-pair mean vs antithetic128-pair reference
Q4: same-batch repeated run bitwise equal; inference_batch_size 1024 vs 256 max_abs_error<=1e-6
    and median daily score Spearman>=0.999999; plus finite/coverage pass
```

对 stochastic comparison 的每个 checkpoint、selection fold、seed：

```text
median_daily_spearman(left_estimate,reference_estimate) >= 0.95
median_daily_top30_overlap(left_estimate,reference_estimate) >= 24
abs(mean_daily_rankic(left_estimate)-mean_daily_rankic(reference_estimate)) <= 0.003
```

Q4 只有 repeated-run bitwise determinism、cross-batch tolerance、finite/coverage 都通过才算 convergence pass；不得仅因 `eta=0` 自动 pass。Q7 在线性 decoder 下只做 algebraic/bitwise fixture，不重复计入 estimator family 的多重比较。

### 6.2 Predictor selection

Predictor selection reference exact 为 `T1_CSZ_COUPLED_LINEAR` 的 6 个 inner checkpoints；estimator 必须在这 6 个 checkpoints 全部 convergence/finite/coverage pass 才有 selection eligibility。不得跨 training arms 聚合后选择 estimator，以免 estimator 与 training graph 循环适配。删除任何 fail 或 `candidate eligible=false` estimator 后，剩余 estimator 按以下 lexicographic 规则选择：

```text
1. 最大化 min(I0_SELECT_2021 ensemble RankIC, I1_SELECT_2022 ensemble RankIC)
2. 最大化两fold中较小的 mean cross-seed daily Spearman
3. 最大化两fold中较小的 mean cross-seed Top30 overlap
4. 最小化 inference draw-equivalent compute
5. estimator_order 最小
```

不得使用 2023、论文表中 `0.064` 或 21D D4 的 2023 数值 tie-break。

若没有 estimator eligible，registry 必须记录 `research_estimator_selected=false`，并以 `Q2_SCORE_MEAN256_REF` 作为固定 `diagnostic_fallback_estimator` 继续 arm readout/refit；fallback 不得生成 repair candidate。

estimator identity 冻结后，必须在 T0/T1/T2/T3/T4 各自 6 个 inner checkpoints 上重新执行该 estimator 的对应 convergence/finite/coverage comparison。该 arm 任一 checkpoint fail 时写 `selected_estimator_arm_convergence_pass=false`，不得进入 arm eligibility；不得回头选择第二名 estimator。

---

## 7. Epoch、arm 与 refit 选择

### 7.1 Inner epoch selection

每个 arm/fold/seed 独立训练。v4 原样继承 v3：T0/T1/T2/T4 joint phase 与 T3 Phase B 的 epoch selection 固定使用 selector-only `Q8_EPOCH_SCORE_MEAN8_CRN`；T3 Phase A 使用 `Q6_KOOPMAN_ONLY`。它们都不是最终选中的 Predictor estimator：

```text
primary = selection-fold mean daily RankIC
eligibility = finite coverage + no collapse + no firewall violation
tie break = first maximum epoch
evaluation cadence = every epoch
early stop = 10 consecutive evaluated epochs without primary > best + 0.0
```

不得跨 seed 选 best seed。所有三个 seeds 均保留并参与后续 ensemble/morphology。epoch registry 必须保留每个 evaluated epoch 的 predictor identity、draw count、RankIC、coverage、collapse flag、checkpoint semantic hash 和 selection reason。

### 7.2 Arm eligibility

使用已选择 Predictor estimator 重读 30 个 inner checkpoints。每个 arm 必须在两个 selection folds 同时满足：

```text
selected_estimator_arm_convergence_pass = true
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

shadow candidate pool 只删除 non-finite、coverage fail、firewall violation 和 `additional_collapse_flag_n>0` arms，故意忽略 seed-rho、Top30 overlap、turnover 与 LOMO gates。shadow exact selection 为：

```text
1. 最大化 mean(I0 ensemble RankIC,I1 ensemble RankIC)
2. 最大化 min(I0 ensemble RankIC,I1 ensemble RankIC)
3. arm_order 最小
```

若 pool 为空，`shadow_arm_id=null,shadow_selection_status=no_finite_candidate,reason_code=no_finite_shadow_arm`。不得用 morphology 或 2023 值改变 shadow identity。

若没有 arm eligible，registry 必须记录 `research_arm_selected=false`，并以 `T2_CSZ_STOPGRAD_LINEAR` 作为固定 `diagnostic_fallback_arm` 完成3个 refit jobs与2023机制 readout；fallback 不得生成 repair candidate。这样所有终态仍保持 exact 33 jobs和统一 artifact profile。

### 7.4 Refit epoch

对于 T0/T1/T2/T4，selected arm 的 6 个 inner selected epochs 排序，`refit_epoch_n = lower_median`，即第 3 个 order statistic。

若 selected/fallback arm 为 T3，分别对 6 个 `phase_a_selected_epoch` 与 6 个 `phase_b_selected_epoch` 取 lower median，生成 exact tuple：

```text
refit_phase_a_epoch_n
refit_phase_b_epoch_n
```

3 个 refit seeds 使用同一固定 integer 或 T3 tuple，不做 early stopping，不读取 2023。T3 refit 必须先完成固定 Phase A，再冻结并完成固定 Phase B。

refit 在 `REFIT_2018_2022` 上从 deterministic initial state 重新训练，不得继续 inner checkpoint optimizer state。

---

## 8. 2023 final mechanism readout

只有以下对象全部 hash-register 后才允许 fresh worker 打开 2023：

```text
hypothesis_registry.csv
training_semantics_arm_registry.csv
predictor_estimator_registry.csv
preflight/metadata_splitter_exit_record.json
preflight/pre_2023_row_index.parquet
preflight/design_2023_row_index.parquet
preflight/value_access_audit.csv pre-2023 snapshot hash
gradient_calibration_audit.parquet
training/inner_checkpoint_manifest.json with 30 entries
training/selected_predictor_estimator.json
training/selected_training_arm.json
predictor_draw_convergence.csv per-arm verification rows
training/mean_rankic_only_shadow_selection.json
training/refit_checkpoint_manifest.json with 3 entries
training/refit_epoch_contract.json
preflight/pre_2023_complete.json
```

fresh worker 对 selected arm 输出：

```text
selected DRC estimator scores: 3 seeds + ensemble
same backbone Koopman-only:     3 seeds + ensemble
Q0 current8 replay control
Q2 ref256 convergence reference
```

E4 的 Q0 必须从 pinned 21C checkpoints、21C seed preimage 和当前两份 21B design panels重新计算，不得复制或打开 21C–21E prediction files；其 row order/score semantic hash 必须与 E1 replay audit 登记 identity 一致。

分别报告 `DESIGN_EARLY_2023`、`DESIGN_LATE_2023`，禁止把两者合并后作为唯一结论。

`same backbone Koopman-only` exact 为同一个 refit state_dict、相同 encoder/selector/Koopman/decoder、相同 hard selector与 batch order，仅 bypass denoiser 并直接 decode Koopman forecast；不得重新训练 K0、重新初始化 decoder 或换 checkpoint。selected DRC 与 K0 必须逐 seed、逐 row 配对。

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

### 8.2 Rank-repair floor

`rank_repair_floor_pass=true` exact 为 DESIGN_LATE_2023 同时满足：

```text
ensemble mean daily RankIC >= 0.030
selected - Q0_CURRENT_SCORE_MEAN8 ensemble mean daily RankIC delta >= 0.020
```

这里 Q0 exact 指 21C sealed checkpoints + 21C frozen 8-draw readout，不是 selected arm 的 8-draw variant。该 contrast 衡量“完整本地修复相对 sealed current implementation”的总改善，不得解释为纯 Predictor effect。

### 8.3 Full stability candidate gate

生成 repair candidate 必须在 DESIGN_LATE_2023 同时满足：

```text
research_estimator_selected = true
research_arm_selected = true
rank_repair_floor_pass = true
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

报告 arithmetic mean、sample std (`ddof=1`)、`RankICIR=mean/std`、`positive_day_rate=count(RankIC_d>0)/complete_day_n`、paired-day delta。std=0 时 RankICIR 必须为 null 且 status=`not_evaluable`，不得写 0。registered complete date 任一 prediction/label 缺失必须触发 coverage fail，不得静默删日。不得在 metric 前对 label 做 CS z-score 后改变 row order；CS z-score 只影响 model return path。

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

Top30 exact 为每个 date 按 `score descending,instrument ascending` mergesort 取前30；cross-section 少于30是 coverage fail。两集合 overlap 为交集 cardinality，adjacent turnover exact 为 `1-overlap_n/30`。quarter-LOMO 对每个 inner selection year 的四个 calendar quarters逐一删除并在剩余 complete days重算 mean RankIC；DESIGN_LATE 的 six-month LOMO 对 2023-07 至 2023-12 六个月逐一删除。不得把单月 RankIC 误写为 LOMO。

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

exact inference families：

```text
F_INNER_2021 = [C01,C02,C03,C04] on I0_SELECT_2021, Holm m=4
F_INNER_2022 = [C01,C02,C03,C04] on I1_SELECT_2022, Holm m=4
F_DESIGN_LATE = [C10,C11] on DESIGN_LATE_2023, Holm m=2
DESIGN_EARLY_2023 = descriptive only, no inferential gate and no Holm family
```

所有 contrasts 先按共同 complete decision dates 做 paired daily delta。stationary bootstrap exact 为 circular indices、expected block length 10、每一步以概率 `0.1` 重新从 `[0,paired_day_n)` uniform restart，否则取前一 index+1 modulo n；`replicate_n=5000`。base seed=`21070031`，每个 `(family_order,contrast_order)` 使用 `base+100*family_order+contrast_order` 的 NumPy `PCG64`。

unadjusted two-sided p exact 为 `min(1,2*min(mean(bootstrap_mean<=0),mean(bootstrap_mean>=0)))`；Holm 按 `(p_unadjusted,contrast_order)` 稳定排序并执行 step-down monotone adjustment。不得跨 fold 合并，也不得把 DESIGN_EARLY p-value 输入任何 gate。

`mean_rankic_only_shadow_selection` 只进入 `selection_policy_difference_audit.csv`，比较 selected identity、inner-fold RankIC 与 morphology gate vector；它不是同一 checkpoint 上的 paired score contrast，不得伪造 C12 或 p-value。

---

## 10. 机械终态与决策顺序

全部 technical gates 通过后，按 first-match 生成唯一终态：

```text
1. research_estimator_selected = false
   -> 21F_predictor_semantics_unresolved

2. research_estimator_selected = true and research_arm_selected = false
   -> 21F_no_stable_training_repair

3. both research selections true and rank_repair_floor_pass = false
   -> 21F_no_rank_repair

4. rank_repair_floor_pass = true and DRC incremental-value gate fails
   -> 21F_repaired_rank_without_drc_increment

5. DRC incremental value passes but full stability candidate gate fails
   -> 21F_mean_rank_repair_unstable

6. all candidate gates pass
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

即使第 6 项通过，也只能由人工另立 fresh-session forward requirement；21F runner 不得自动创建或执行下一阶段。

---

## 11. 执行阶段与 gates

### E0 PREAUTH_AND_PREFLIGHT

1. `execution_authorization_gate`
2. `paper_and_upstream_hash_gate`
3. `upstream_terminal_state_gate`
4. `artifact_profile_contract_gate`
5. `retained_universe_exact_match_gate`
6. `inner_fold_purge_and_metadata_split_gate`
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

正式执行前 authorization key set 必须与下列列表 exact 相等，不允许额外字段或缺失字段：

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
approved_schema_registry_contract_sha256
allowed_runtime_field_differences
approved_by
approved_at_utc
```

runner 不得生成或补写 authorization。`approved_by` 必须是 human identity；`allowed_runtime_field_differences=[]`。authorization validation 必须使用 `set(payload.keys()) == AUTH_KEYS`，不得采用 subset check。

### 12.3 Resource contract

```text
GPU required = CUDA
maximum concurrent GPU training jobs = 2（仅 E2 的两个 inner-fold lanes；refit 仍单路）
batch_size = 256
model_seeds = 3
planned_training_jobs = 33
minimum free disk before run = 25 GiB
total GPU wall-time cap = 144 hours
per-joint-inner-job hard timeout = 3 hours
per-T3-two-stage-inner-job hard timeout = 6 hours
per-joint-refit-job hard timeout = 4 hours
per-T3-two-stage-refit-job hard timeout = 8 hours
combined E1/E3/E4 non-training GPU inference cap = 12 hours
```

worst-case static upper bound `24*3+6*6+3*8+12=144` GPU-process-hours 必须通过资源一致性检查；并发只缩短 coordinator elapsed，不减少 GPU-process-hours。OOM 只允许按 `[1024,512,256,128,64]` 顺序降低 inference batch size，不得改变 training batch size、draw count、dtype、模型或样本；Q4 batch-size invariance 仍固定比较 1024 与 256，不受实际 fallback 影响。

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
preflight/pre_2023_row_index.parquet
preflight/design_2023_row_index.parquet
preflight/metadata_splitter_exit_record.json
preflight/value_access_audit.csv
preflight/pre_2023_complete.json
exact_replay_audit.csv
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
schema_registry_21f.json
stage_status_registry.csv
semantic_reproducibility_manifest.json
manifest_21f_reaka_semantic_repair_and_stability_validation.json
output_hashes_21f_reaka_semantic_repair_and_stability_validation.json
```

inner checkpoint paths exact expansion 为：

```text
training/inner_checkpoints/{fold_id}/{arm_id}/seed_{model_seed}/state_dict.pt

fold_id allowlist = [I0_FIT_2018_2020_PURGED,I1_FIT_2018_2021_PURGED]
arm_id allowlist = [T0_RAW_COUPLED_LINEAR,T1_CSZ_COUPLED_LINEAR,T2_CSZ_STOPGRAD_LINEAR,T3_CSZ_TWO_STAGE_LINEAR,T4_CSZ_STOPGRAD_POINTWISE_MLP]
model_seed allowlist = [20260713,20260714,20260715]
```

按上述 allowlists 的 Cartesian product 展开 exact 30 paths；实际 path 必须使用完整 fold_id 与 arm_id，不得使用缩写 token。refit checkpoint 使用与 arm identity 无关的 exact 3 paths，arm identity 写入 manifest：

```text
training/refit_checkpoints/seed_20260713/state_dict.pt
training/refit_checkpoints/seed_20260714/state_dict.pt
training/refit_checkpoints/seed_20260715/state_dict.pt
```

config 与 artifact profile 必须逐项列出 exact 33 paths，manifest 不接受 glob。21F 不持久化 draw-level tensors；推理必须 streaming aggregation，只输出 aggregate score 与 convergence audits。因此不存在未冻结的 conditional draw-shard profile。

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
failure/failure_record.json
```

Top30 overlap/turnover 是 score morphology diagnostic，不是 portfolio backtest，因此允许输出；不得包含收益或成本列。

### 13.1 大文件 Git 规则

canonical bundle 本地必须完整。单文件 `size_bytes > 20 MiB` 时，Git 发布必须用 exact path 加入 `.gitignore`，其余文件正常发布；不得删除、截断或使用 placeholder。报告必须列出所有 local-only artifact exact paths 和 sizes。

`outputs/21F_reaka_semantic_repair_and_stability_validation_v0.failure_history/` 无论大小均为 local-only，并必须以 exact root 加入 `.gitignore`；它不是成功证据 profile 的替代物。

### 13.2 Technical-failure building profile

任一 technical gate fail 时，`.building` 必须至少保留：

```text
failure/failure_record.json
stage_status_registry.csv
gate_evidence_21f.csv
preflight/value_access_audit.csv
historical_design_holdout_access_audit.csv
```

stage/gate/access/historical 四类 registries 必须在 E0 初始化；未执行 gates 写 `evaluation_status=not_run`。`failure/failure_record.json` 只在 technical failure 时创建，成功路径必须不存在。failure record exact keys 为：

```text
schema_version,run_id,failed_stage_id,failed_gate_id,error_type,error_message,
worker_exit_code,last_complete_stage_id,value_access_audit_sha256,
historical_holdout_access_audit_sha256,created_at_utc
```

technical failure 禁止生成 success decision、success manifest、output hashes 或 canonical。重跑前必须先验证 failure record 与已完成 stage hashes，再将 `failure/` 及当时四类 registry snapshots 原子归档到 sibling local-only root：

```text
outputs/21F_reaka_semantic_repair_and_stability_validation_v0.failure_history/attempt_{attempt_n}/
```

`attempt_n` 从1连续递增，不得覆盖或删除；随后才可复用同一 `.building`。最终 semantic manifest 必须登记 `prior_failure_history_hashes`，但 failure-history root 不进入 canonical artifact profile，也不得 Git 发布。

---

## 14. Closed schema 与数值完整性

config/test 只能逐字转录本节 schema，不得自行新增列。记号：`!`=non-null，`?`=nullable；`date`=Arrow date32/CSV ISO `YYYY-MM-DD`；`sha256`=lowercase 64-hex string；所有枚举必须由 config exact allowlist 冻结。

### 14.1 Exact tabular schemas

| artifact | exact columns（按此顺序） | primary key / row-count contract |
|---|---|---|
| `21F_reaka_semantic_repair_and_stability_validation_decision.csv` | `schema_version:string!,run_id:string!,terminal_state:string!,evidence_role:string!,research_estimator_selected:bool!,selected_estimator_id:string?,research_arm_selected:bool!,selected_arm_id:string?,rank_repair_floor_pass:bool!,drc_incremental_value_pass:bool!,full_stability_candidate_pass:bool!,paper_exact_claim_allowed:bool!,author_implementation_claim_allowed:bool!,forward_support_claim_allowed:bool!,next_requirement_execution_authorized:bool!,reason_code:string!` | `run_id`; exact 1; four claim/authorization booleans must all be false |
| `preflight/pre_2023_row_index.parquet` | `fold_id:string!,decision_date:date!,instrument:string!,fold_panel_row_idx:int64!,x_cache_row_indices:list<int64>[10]!,source_dates:list<date>[10]!,row_key_hash:sha256!` | `fold_id,decision_date,instrument`; exact 923088 rows, with overlap represented by distinct fold_id |
| `preflight/design_2023_row_index.parquet` | same as pre-2023 index | `fold_id,decision_date,instrument`; exact 102099 rows |
| `preflight/value_access_audit.csv` | `event_order:int64!,worker_role:string!,process_id:string!,stage_id:string!,path:string!,access_mode:string!,metadata_only:bool!,value_parsed:bool!,label_value_materialized_n:int64!,score_value_materialized_n:int64!,event_time_utc:string!,status:string!,reason_code:string?` | `event_order`; one row per instrumented open/read event, no aggregation-only replacement |
| `exact_replay_audit.csv` | `replay_order:int16!,replay_id:string!,source_path:string!,source_sha256:sha256!,comparison_role:string!,expected_semantic_sha256:sha256!,observed_semantic_sha256:sha256!,max_abs_error:float64!,bitwise_equal:bool!,status:string!,reason_code:string?` | `replay_id,comparison_role`; exact 7 rows: Q0 early/late, D4 early/late, 21E decision/contrast/gradient |
| `hypothesis_registry.csv` | `hypothesis_order:int8!,hypothesis_id:string!,statement:string!,intervention_id:string!,materiality_rule_id:string!,falsifier:string!,allowed_conclusion:string!,status:string!` | `hypothesis_id`; exact 8 |
| `training_semantics_arm_registry.csv` | `arm_order:int8!,arm_id:string!,return_transform:string!,loss_weight_contract:string!,gradient_graph:string!,phase_contract:string!,decoder_id:string!,candidate_role:string!,status:string!` | `arm_id`; exact 5 |
| `predictor_estimator_registry.csv` | `estimator_order:int8!,estimator_id:string!,definition_id:string!,draw_n:int16!,reference_draw_n:int16!,candidate_eligible:bool!,selection_reference_arm_id:string!,claim_restriction:string!,status:string!` | `estimator_id`; exact 8 |
| `contrast_registry.csv` | `contrast_order:int8!,contrast_id:string!,left_id:string!,right_id:string!,family_id:string!,metric_id:string!,materiality_rule_id:string!,claim_restriction:string!,status:string!` | `contrast_id`; exact 6 |
| `inner_fold_registry.csv` | `fold_order:int8!,split_id:string!,role:string!,date_min:date!,date_max:date!,max_label_source_date:date!,row_n:int64!,complete_day_n:int32!,instrument_n:int32!,row_key_sha256:sha256!,status:string!` | `split_id`; exact 5 |
| `return_transform_audit.parquet` | `split_id:string!,decision_date:date!,position:int8!,row_n:int32!,raw_mean:float64!,raw_std_ddof0:float64!,sigma_floor_applied:bool!,transformed_mean:float64!,transformed_std_ddof0:float64!,raw_row_key_sha256:sha256!,transformed_value_sha256:sha256!,status:string!,reason_code:string?` | `split_id,decision_date,position`; split allowlist=5 pre-2023+2 design splits, position=0..10, exact `(475+186+661+180+842+107+103)*11=28094` rows; `sigma_floor_applied == (raw_std_ddof0 < 1e-6)` |
| `gradient_calibration_audit.parquet` | `record_type:string!,fold_id:string!,model_seed:int64!,temporal_stratum:int8?,batch_index:int8?,loss_term:string?,row_n:int32?,decision_date_min:date?,decision_date_max:date?,row_key_sha256:sha256?,gradient_median_l2:float64?,loss_weight:float64?,ordered_parameter_names_sha256:sha256!,status:string!,reason_code:string?` | `record_type,fold_id,model_seed,temporal_stratum,batch_index,loss_term`; 210 inner rows plus 9 refit-weight rows |
| `gradient_graph_and_collapse_audit.parquet` | `fold_id:string!,arm_id:string!,model_seed:int64!,phase_id:string!,epoch:int16!,module_id:string!,loss_term:string!,gradient_l2:float64!,gradient_share:float64!,zero_solution_improvement:float64!,latent_std:float64!,decoder_output_std:float64!,additional_collapse_flag:bool!,checkpoint_semantic_sha256:sha256!,status:string!,reason_code:string?` | `fold_id,arm_id,model_seed,phase_id,epoch,module_id,loss_term` |
| `training/inner_training_run_registry.csv` | `job_order:int16!,fold_id:string!,arm_id:string!,model_seed:int64!,phase_id:string!,fit_row_n:int64!,planned_max_epochs:int16!,executed_epoch_n:int16!,selected_epoch:int16!,selector_estimator_id:string!,phase_selected_semantic_sha256:sha256!,checkpoint_path:string?,checkpoint_sha256:sha256?,checkpoint_semantic_sha256:sha256?,job_status:string!,reason_code:string?` | `fold_id,arm_id,model_seed,phase_id`; exact 36 rows; checkpoint fields non-null on joint/final-phase rows only while planned job_n remains 30 |
| `training/refit_training_run_registry.csv` | `job_order:int8!,arm_id:string!,model_seed:int64!,phase_id:string!,fit_row_n:int64!,fixed_epoch_n:int16!,phase_selected_semantic_sha256:sha256!,checkpoint_path:string?,checkpoint_sha256:sha256?,checkpoint_semantic_sha256:sha256?,job_status:string!,reason_code:string?` | `model_seed,phase_id`; exact 3 rows, or 6 iff T3 selected/fallback; checkpoint fields non-null on final-phase rows only |
| prediction parquet | `stage_id:string!,fold_id:string!,arm_id:string!,estimator_id:string!,score_variant:string!,model_seed:int64?,is_ensemble:bool!,decision_date:date!,instrument:string!,row_key_hash:sha256!,score:float32!,label:float32!` | `stage_id,fold_id,arm_id,estimator_id,score_variant,model_seed,is_ensemble,decision_date,instrument`; seed null iff ensemble=true; rows exact equal registered row keys × registered score identities |
| `predictor_draw_convergence.csv` | `fold_id:string!,arm_id:string!,estimator_id:string!,model_seed:int64!,comparison_id:string!,paired_day_n:int32!,median_daily_spearman:float64!,median_daily_top30_overlap:float64!,mean_daily_rankic_left:float64!,mean_daily_rankic_reference:float64!,rankic_abs_delta:float64!,repeated_run_bitwise_equal:bool!,cross_batch_max_abs_error:float64!,coverage_pass:bool!,convergence_pass:bool!,reason_code:string?` | `fold_id,arm_id,estimator_id,model_seed,comparison_id` |
| `daily_rankic_readout.csv` | `stage_id:string!,fold_id:string!,arm_id:string!,estimator_id:string!,score_variant:string!,model_seed:int64?,is_ensemble:bool!,decision_date:date!,cross_section_n:int32!,rankic:float64!,status:string!,reason_code:string?` | score identity + `decision_date` |
| `paired_semantic_contrasts.csv` | `family_id:string!,fold_id:string!,contrast_id:string!,left_id:string!,right_id:string!,paired_day_n:int32!,mean_daily_rankic_left:float64!,mean_daily_rankic_right:float64!,mean_daily_rankic_delta:float64!,same_direction_seed_n:int8!,p_unadjusted:float64!,p_holm:float64!,materiality_pass:bool!,status:string!,reason_code:string?` | `family_id,fold_id,contrast_id` |
| `cross_seed_morphology.csv` | `stage_id:string!,fold_id:string!,arm_id:string!,estimator_id:string!,seed_a:int64!,seed_b:int64!,paired_day_n:int32!,mean_daily_score_spearman:float64!,mean_daily_top30_overlap:float64!,status:string!,reason_code:string?` | score identity + `seed_a,seed_b`; require seed_a<seed_b |
| `top30_overlap_and_turnover.csv` | `stage_id:string!,fold_id:string!,arm_id:string!,estimator_id:string!,model_seed:int64?,is_ensemble:bool!,decision_date:date!,previous_decision_date:date?,top30_n:int8!,adjacent_overlap_n:int8?,adjacent_turnover:float64?,status:string!,reason_code:string?` | score identity + `decision_date` |
| `monthly_quarter_lomo_stability.csv` | `stage_id:string!,fold_id:string!,arm_id:string!,estimator_id:string!,model_seed:int64?,is_ensemble:bool!,lomo_unit_type:string!,omitted_unit_id:string!,retained_day_n:int32!,mean_daily_rankic:float64!,positive:bool!,status:string!,reason_code:string?` | score identity + `lomo_unit_type,omitted_unit_id` |
| `selection_policy_difference_audit.csv` | `selected_arm_id:string?,shadow_arm_id:string?,identity_differs:bool!,selected_worst_fold_rankic:float64?,shadow_mean_fold_rankic:float64?,selected_gate_vector_json:string!,shadow_gate_vector_json:string!,h21f07_materiality_pass:bool!,status:string!,reason_code:string?` | exact 1 row |
| `hypothesis_readout.csv` | `hypothesis_order:int8!,hypothesis_id:string!,materiality_rule_id:string!,materiality_pass:bool!,falsifier_triggered:bool!,evidence_ids_json:string!,conclusion:string!,claim_ceiling:string!,status:string!,reason_code:string?` | `hypothesis_id`; exact 8 |
| `gate_evidence_21f.csv` | `gate_order:int8!,gate_id:string!,stage_id:string!,evaluation_status:string!,research_status:string?,evidence_paths_json:string!,observed_value_json:string!,threshold_json:string!,reason_code:string?` | `gate_id`; exact 42 |
| `historical_design_holdout_access_audit.csv` | `stage_order:int8!,stage_id:string!,resource_id:string!,open_attempt_n:int64!,row_materialized_n:int64!,status:string!,reason_code:string?` | `stage_id,resource_id`; exact 6 rows, one `HISTORICAL_DESIGN_HOLDOUT` row per stage |
| `artifact_profile_registry.csv` | `profile_id:string!,terminal_state:string!,required_paths_json:string!,forbidden_paths_json:string!,exact_checkpoint_paths_json:string!,schema_registry_contract_sha256:sha256!,status:string!` | `profile_id,terminal_state`; exact 6 terminal rows |
| `stage_status_registry.csv` | `stage_order:int8!,stage_id:string!,status:string!,started_at_utc:string!,ended_at_utc:string?,worker_exit_code:int32?,required_artifact_n:int32!,observed_artifact_n:int32!,reason_code:string?` | `stage_id`; exact 6 |

### 14.2 Exact JSON key contracts

```text
selected_predictor_estimator.json =
  schema_version,selection_status,research_estimator_selected,selected_estimator_id,
  diagnostic_fallback_estimator_id,selection_reference_arm_id,lexicographic_key,
  eligible_estimator_ids,registry_sha256,created_at_utc

selected_training_arm.json =
  schema_version,selection_status,research_arm_selected,selected_arm_id,
  diagnostic_fallback_arm_id,selected_estimator_id,lexicographic_key,
  eligible_arm_ids,registry_sha256,created_at_utc

mean_rankic_only_shadow_selection.json =
  schema_version,shadow_selection_status,shadow_arm_id,candidate_pool_arm_ids,
  lexicographic_key,noncontrolling,created_at_utc

refit_epoch_contract.json =
  schema_version,arm_id,phase_contract,inner_epoch_values,
  refit_epoch_n,refit_phase_a_epoch_n,refit_phase_b_epoch_n,
  lower_median_rule,created_at_utc
```

non-T3 的 phase-A/B fields 必须为 null；T3 的 scalar `refit_epoch_n` 必须为 null。checkpoint manifests 必须 exact keys：`schema_version,run_id,checkpoint_entries,entry_n,entries_semantic_sha256`；每个 entry exact keys：`job_order,fold_id,arm_id,model_seed,final_phase_id,path,size_bytes,sha256,semantic_sha256,phase_a_semantic_sha256,selected_epoch,phase_a_selected_epoch`。non-T3 的 phase-A fields 必须为 null。

`training/inner_checkpoint_manifest.json entry_n=30`，`training/refit_checkpoint_manifest.json entry_n=3`；两者的 entries 必须按 `job_order` 升序且 exact cover 第 13 节路径，不得含额外 checkpoint。

其余 JSON exact keys：

```text
metadata_splitter_exit_record.json =
  schema_version,worker_role,process_id,source_index_sha256,
  pre_2023_index_sha256,design_2023_index_sha256,projected_columns,
  return_panel_open_attempt_n,label_value_materialized_n,
  score_value_materialized_n,worker_exit_code,completed_at_utc

pre_2023_complete.json =
  schema_version,run_id,inner_checkpoint_manifest_sha256,
  selected_predictor_estimator_sha256,selected_training_arm_sha256,
  shadow_selection_sha256,refit_checkpoint_manifest_sha256,
  refit_epoch_contract_sha256,value_access_audit_snapshot_sha256,
  restricted_value_parse_open_attempt_n,completed_at_utc

semantic_reproducibility_manifest.json =
  schema_version,run_id,requirement_version,implementation_hashes,upstream_pins,
  fold_hashes,rng_contract,training_contract,selected_objects,prior_failure_history_hashes,
  terminal_state,semantic_payload_sha256

manifest_21f_reaka_semantic_repair_and_stability_validation.json =
  schema_version,run_id,requirement_version,terminal_state,artifact_profile_id,
  artifact_n,artifacts,requirement_sha256,config_sha256,runner_sha256,test_sha256,
  authorization_sha256,paper_pdf_sha256,upstream_pins,decision_sha256,report_sha256,
  semantic_reproducibility_manifest_sha256,output_hashes_path,
  output_hashes_excluded_self_path,finalized_at_utc

output_hashes_21f_reaka_semantic_repair_and_stability_validation.json =
  schema_version,run_id,entries,entry_n,entries_semantic_sha256,excluded_self_path

schema_registry_21f.json =
  schema_version,contract_id,tabular_schemas,json_schemas,status_allowlists,
  reason_code_allowlists,contract_sha256
```

manifest `artifacts` entry exact keys：`path,role,schema_version,row_count,size_bytes,sha256`；output-hashes entry exact keys：`path,size_bytes,sha256`。`output_hashes` 不得包含自身，manifest 可以进入 output-hashes；manifest 只登记 output-hashes path、不登记其 SHA256，从而禁止 hash cycle。

`schema_registry_21f.json` 必须把本节所有 schema 机械编码并计算 `schema_registry_contract_sha256`；authorization 绑定该 hash。config/test 只能验证一致性，不能成为新增 schema 的权威来源。

为消除自哈希循环，`semantic_payload_sha256` exact 为对 `semantic_reproducibility_manifest.json` 删除该字段后、按 UTF-8 canonical JSON（键排序、紧凑分隔符、禁止 NaN）序列化所得 bytes 的 SHA256；`contract_sha256` 对 `schema_registry_21f.json` 使用同一规则删除自身字段后计算。任何其他字段、数组顺序或值均进入对应 preimage。

### 14.3 全局完整性 invariants

```text
decision_date = ISO date / Arrow date32
instrument = canonical provider symbol
all score,label,RankIC,gradient finite where status=pass
no duplicate primary key
no NaN/Inf silently converted to zero
all prediction rows exact match registered retained row keys
is_ensemble=true  <=> model_seed is null
is_ensemble=false <=> model_seed in [20260713,20260714,20260715]
status/reason_code must come from closed allowlists
```

exact status allowlists：

```text
evaluation_status = [pass,fail,not_run]
research_status = [pass,fail,not_applicable]
row_status = [pass,fail,not_evaluable]
job_status = [planned,complete,fail]
stage_status = [pending,running,complete,fail]
selection_status = [selected,diagnostic_fallback,no_finite_candidate]
registry_status = [pre_registered,eligible,ineligible,selected,diagnostic_fallback,complete]
artifact_role = [substantive_evidence,audit,checkpoint,report,manifest]
```

exact `reason_code` allowlist：

```text
NA
authorization_invalid
upstream_drift
hash_mismatch
schema_mismatch
row_key_mismatch
outcome_date_purge_fail
firewall_violation
worker_nonzero
timeout
oom_no_fallback
non_finite
coverage_fail
insufficient_paired_days
convergence_fail
collapse_detected
no_eligible_estimator
no_eligible_arm
no_finite_shadow_arm
rank_repair_floor_fail
drc_increment_fail
morphology_fail
research_threshold_fail
```

CSV nullable reason uses empty field only when semantic value is null；decision/gate terminal rows必须使用非空 reason code，成功时为 `NA`。

---

## 15. 中文报告必须回答的问题

1. 哪些字段论文明确、哪些仍未披露？
2. 21D/21E 先验与 21F direct evidence 如何分栏？
3. outcome-date purge 是否通过，且在 shared loss weights 下 CS z-score 是否在两个 inner folds 一致改善？
4. 64/128/256、antithetic、DDIM 和 latent-mean estimator 是否按 exact RNG/x_T 合同收敛？
5. 为什么被选 estimator 胜出，是否依赖 RankIC tie-break？
6. coupled、stopgrad、two-stage 的 gradient 与 RankIC 差异是什么，T3 Phase-A/B epochs 如何确定？
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

以下命令 cwd exact 为第 1 节 `experiment_root`：

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
fit label_source_date purge and max-outcome-date boundary
metadata splitter projected-column and restricted-value zero-open contract
E1 replay-worker IPC allowlist excludes score/RankIC/contrast values
2023 zero-open firewall before pre_2023_complete
historical holdout zero-open throughout
21C Q0 and 21D D4 exact replay
decision-CS z-score fixture and sigma floor
train-only gradient calibration
shared loss-weight identity across T0/T1/T2/T4
T1/T2 common initial state and stopgrad-only difference
T3 two-phase epoch selection, refit tuple, phase freeze and optimizer ownership
common-random-number prefix identity
antithetic full-noise tensor pairing
DDIM eta=0 exact x_T and batch-size determinism
selected-estimator convergence on every candidate arm
linear-decoder Q2/Q7 commutation
30 inner + 3 refit job cardinality
epoch/estimator/arm lexicographic first-match
mean-only shadow selection noncontrolling
fresh 2023 worker no optimizer/autograd/checkpoint writes
RankIC/morphology/LOMO exact fixtures
Holm family correction
terminal-state first-match
explicit no-rank-repair terminal coverage
portfolio artifact absence
requirement-defined exact schemas, row formulas and finite values
manifest/hash exact closure
manifest/output-hashes no-cycle fixture
failed technical validation remains .building
retry archives immutable failure history outside canonical
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
- [ ] 确认 outcome-date-purged inner fold hashes、33 jobs 和 T3 refit epoch tuple。
- [ ] 确认 T0/T1/T2/T4 共用 fold/seed shared loss weights。
- [ ] 确认 Predictor RNG、antithetic schedule 和 DDIM initial x_T exact semantics。
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
